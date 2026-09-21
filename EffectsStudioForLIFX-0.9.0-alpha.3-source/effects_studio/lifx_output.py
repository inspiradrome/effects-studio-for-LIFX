"""Resilient live effect output for a LIFX Tube."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from photons_app.executor import library_setup
from photons_messages import TileEffectType

from effects_studio.device_lease import DeviceLease
from effects_studio.effect_spec import validate_effect_spec
from effects_studio.renderer import render_effect
from effects_studio.t10_probe import TUBE_PRODUCT_IDS
from probe_t10 import TubeState, inspect_tube, set_firmware_effect, set_frame, set_power

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TubeOutputConfig:
    serial: str
    ip: str
    brightness: float = 0.72
    timeout: float = 5.0
    frame_seconds: float = 0.42


def device_settings_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.cwd()))
    return base / "LIFXEffectsStudio" / "device.json"


def device_lease_path(serial: str, settings_path: Path | None = None) -> Path:
    settings_directory = (settings_path or device_settings_path()).parent
    return settings_directory / f"tube-{serial.lower()}.lock"


def load_saved_config(path: Path | None = None) -> TubeOutputConfig | None:
    try:
        return decode_config((path or device_settings_path()).read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, ValueError):
        return None


def save_config(config: TubeOutputConfig, path: Path | None = None) -> None:
    settings_path = path or device_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = settings_path.with_suffix(".tmp")
    temporary_path.write_text(encode_config(config), encoding="utf-8")
    temporary_path.replace(settings_path)


def encode_config(config: TubeOutputConfig) -> str:
    return json.dumps(
        {"serial": config.serial, "ip": config.ip, "brightness": config.brightness}, indent=2
    )


def decode_config(contents: str) -> TubeOutputConfig:
    payload = json.loads(contents)
    return TubeOutputConfig(
        serial=str(payload["serial"]).lower(),
        ip=str(payload["ip"]),
        brightness=float(payload.get("brightness", 0.72)),
    )


async def discover_tubes(timeout: float = 5.0) -> list[dict[str, object]]:
    """Broadcast on the current LAN and return compatible Tube devices."""

    previous_hardcoded = os.environ.pop("HARDCODED_DISCOVERY", None)
    collector: Any = None
    try:
        loop = asyncio.get_running_loop()
        collector = library_setup(config_filename=None, photons_modules=["control"])
        collector.configuration["photons_app"].loop = loop
        asyncio.set_event_loop(loop)
        target = collector.resolve_target("lan")
    finally:
        if previous_hardcoded is not None:
            os.environ["HARDCODED_DISCOVERY"] = previous_hardcoded

    devices: list[dict[str, object]] = []
    try:
        async with target.session() as sender:
            plans = sender.make_plans("address", "state", "capability", "chain")
            reference = collector.reference_object(None)
            async for serial, complete, info in sender.gatherer.gather_per_serial(
                plans, reference, find_timeout=timeout, message_timeout=timeout
            ):
                if not complete:
                    continue
                product = info["capability"]["product"]
                if product.pid not in TUBE_PRODUCT_IDS:
                    continue
                address = info["address"]
                ip = str(address[0]) if isinstance(address, tuple) else str(address).split(":")[0]
                chain = info["chain"]["chain"]
                devices.append(
                    {
                        "serial": serial,
                        "ip": ip,
                        "label": str(info["state"]["label"]),
                        "product": product.name,
                        "matrix": " + ".join(f"{part.width}x{part.height}" for part in chain),
                    }
                )
    finally:
        if collector is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(collector.stop_photons_app(), timeout=timeout)
    return sorted(devices, key=lambda device: (str(device["label"]), str(device["serial"])))


class StudioOutput:
    """Render a selected effect and restore the latest prior LIFX state."""

    def __init__(self, config: TubeOutputConfig, *, settings_path: Path | None = None) -> None:
        self.config = config
        self.settings_path = settings_path
        self.connected = False
        self.message = "Connecting to Tube"
        self.tube: TubeState | None = None
        self._original: TubeState | None = None
        self._effect: dict[str, Any] | None = None
        self._playing = False
        self._effect_started_at = time.monotonic()
        self._effect_elapsed = 0.0
        self._collector: Any = None
        self._target: Any = None
        self._session_context: Any = None
        self._sender: Any = None
        self._task: asyncio.Task[None] | None = None
        self._has_taken_control = False
        self._lease = DeviceLease(device_lease_path(config.serial, settings_path))
        self._management_lock = asyncio.Lock()
        self._output_lock = asyncio.Lock()

    def status(self) -> dict[str, object]:
        return {
            "mode": "lifx",
            "connected": self.connected,
            "message": self.message,
            "serial": self.config.serial,
            "ip": self.config.ip,
            "label": self.tube.label if self.tube else None,
            "playing": self._playing,
        }

    async def start(self) -> None:
        if self._task is None:
            if not self._lease.acquire():
                self.connected = False
                self.message = "Tube already in use by another Effects Studio"
                return
            self._task = asyncio.create_task(self._run(), name="lifx-effects-output")

    async def set_effect(self, spec: dict[str, Any]) -> None:
        self._effect = validate_effect_spec(spec)
        self._effect_elapsed = 0.0
        self._effect_started_at = time.monotonic()
        self._playing = True
        if self.connected:
            await self._update_output()

    def update_effect(self, spec: dict[str, Any]) -> None:
        """Apply edited parameters without restarting a sequence."""

        self._effect = validate_effect_spec(spec)

    async def pause(self) -> None:
        if self._playing:
            self._effect_elapsed += time.monotonic() - self._effect_started_at
        self._playing = False

    def set_brightness(self, brightness: float) -> None:
        if not 0 < brightness <= 1:
            raise ValueError("brightness must be greater than 0 and no more than 1")
        self.config = TubeOutputConfig(
            serial=self.config.serial,
            ip=self.config.ip,
            brightness=brightness,
            timeout=self.config.timeout,
            frame_seconds=self.config.frame_seconds,
        )

    async def resume(self) -> None:
        if self._effect is None:
            raise ValueError("Choose an effect first.")
        if not self._playing:
            self._effect_started_at = time.monotonic()
        self._playing = True

    async def restore_native(self) -> None:
        self._playing = False
        self._effect = None
        self._effect_elapsed = 0.0
        await self._restore_original()

    async def reconfigure(self, config: TubeOutputConfig) -> None:
        async with self._management_lock:
            effect, playing = self._effect, self._playing
            await self.stop()
            self.config, self.tube, self._original, self._target = config, None, None, None
            self._lease = DeviceLease(device_lease_path(config.serial, self.settings_path))
            self._has_taken_control = False
            self._effect, self._playing = effect, playing
            self.message = "Connecting to Tube"
            await self.start()

    async def reconnect(self) -> None:
        await self.reconfigure(self.config)

    async def stop(self) -> None:
        try:
            if self._task:
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task
                self._task = None
            await self._restore_original()
            await self._disconnect()
            if self._collector is not None:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(
                        self._collector.stop_photons_app(), timeout=self.config.timeout
                    )
                self._collector = None
        finally:
            self._lease.release()

    async def _run(self) -> None:
        while True:
            if not self.connected:
                try:
                    await self._connect()
                except Exception as error:
                    self.connected = False
                    self.message = f"Tube unavailable; retrying ({type(error).__name__})"
                    log.warning("Could not connect to Tube: %s", error)
                    await self._disconnect()
                    await asyncio.sleep(2.5)
                    continue
            try:
                await self._update_output()
            except Exception as error:
                self.connected = False
                self.message = f"Tube connection lost; retrying ({type(error).__name__})"
                log.warning("Could not update Tube: %s", error)
                await self._disconnect()
            await asyncio.sleep(self.config.frame_seconds)

    async def _connect(self) -> None:
        if self._collector is None:
            os.environ["HARDCODED_DISCOVERY"] = json.dumps(
                {self.config.serial.lower(): self.config.ip}
            )
            loop = asyncio.get_running_loop()
            self._collector = library_setup(config_filename=None, photons_modules=["control"])
            self._collector.configuration["photons_app"].loop = loop
            asyncio.set_event_loop(loop)
            self._target = self._collector.resolve_target("lan")
        reference = self._collector.reference_object(self.config.serial.lower())
        self._session_context = self._target.session()
        self._sender = await self._session_context.__aenter__()
        self.tube = await asyncio.wait_for(
            inspect_tube(self._sender, reference, self.config.timeout, allow_active_effect=True),
            timeout=self.config.timeout * 3,
        )
        self.connected = True
        self.message = f"{self.tube.label} connected"
        with contextlib.suppress(OSError):
            save_config(self.config, self.settings_path)

    async def _disconnect(self) -> None:
        session = self._session_context
        self._session_context = self._sender = None
        self.connected = False
        if session is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(
                    session.__aexit__(None, None, None), timeout=self.config.timeout
                )

    async def _update_output(self) -> None:
        async with self._output_lock:
            if (
                not self._playing
                or self._effect is None
                or self.tube is None
                or self._sender is None
            ):
                return
            if not self._has_taken_control:
                reference = self._collector.reference_object(self.config.serial.lower())
                self._original = await asyncio.wait_for(
                    inspect_tube(
                        self._sender, reference, self.config.timeout, allow_active_effect=True
                    ),
                    timeout=self.config.timeout * 3,
                )
                self.tube = self._original
                if (
                    self._original.original_effect
                    and self._original.original_effect["type"] != TileEffectType.OFF
                ):
                    await asyncio.wait_for(
                        set_firmware_effect(self._sender, self.tube.serial, None),
                        timeout=self.config.timeout,
                    )
                await asyncio.wait_for(
                    set_power(self._sender, self.tube.serial, True), timeout=self.config.timeout
                )
                self._has_taken_control = True
            frame = render_effect(
                self._effect,
                self.tube.width,
                self.tube.height,
                brightness=self.config.brightness,
                now=self._effect_elapsed + time.monotonic() - self._effect_started_at,
            )
            await asyncio.wait_for(
                set_frame(
                    self._sender,
                    self.tube,
                    frame,
                    duration=min(0.36, self.config.frame_seconds * 0.85),
                ),
                timeout=self.config.timeout,
            )

    async def _restore_original(self) -> None:
        async with self._output_lock:
            if (
                not self._has_taken_control
                or self._original is None
                or self._sender is None
                or self.tube is None
            ):
                return
            await asyncio.wait_for(
                set_frame(self._sender, self.tube, self._original.original_colors, duration=0.3),
                timeout=self.config.timeout,
            )
            await asyncio.wait_for(
                set_firmware_effect(self._sender, self.tube.serial, self._original.original_effect),
                timeout=self.config.timeout,
            )
            await asyncio.wait_for(
                set_power(self._sender, self.tube.serial, self._original.original_power > 0),
                timeout=self.config.timeout,
            )
            self._has_taken_control = False
            self._original = None
