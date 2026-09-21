"""Discover and safely exercise the 52-zone LIFX Tube over the local network."""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

from photons_app.executor import library_setup
from photons_control.planner import Skip
from photons_messages import LightMessages, TileEffectType, TileMessages
from photons_transport.errors import FailedToFindDevice

from effects_studio.t10_probe import (
    TUBE_PRODUCT_IDS,
    ProbeError,
    axis_length,
    countdown_colour,
    make_bands,
    make_marker,
    make_timer_frame,
)


@dataclass(slots=True)
class TubeState:
    serial: str
    name: str
    firmware: str
    label: str
    address: str
    width: int
    height: int
    original_colors: list[Any]
    original_power: int
    original_effect: dict[str, Any] | None = None

    @property
    def zone_count(self) -> int:
        return self.width * self.height


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover and safely test a LIFX T10/Tube matrix.",
        epilog=(
            "Run 'discover' first. Write tests restore the prior colours and power state. "
            "If a pattern forms vertical slices, repeat it with --axis columns."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=8,
        help="network discovery timeout in seconds (default: 8)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("discover", help="find devices and report Tube geometry; read-only")

    bands = subparsers.add_parser("bands", help="show green/amber/red bands, then restore")
    _add_write_arguments(bands)
    bands.add_argument(
        "--seconds",
        type=float,
        default=6,
        help="how long to display the pattern (default: 6)",
    )

    sweep = subparsers.add_parser("sweep", help="sweep the planned bright marker, then restore")
    _add_write_arguments(sweep)
    sweep.add_argument(
        "--step-seconds",
        type=float,
        default=0.65,
        help="delay between marker positions (default: 0.65)",
    )

    timer = subparsers.add_parser(
        "timer",
        help="run a one-minute countdown with phase changes, then restore",
    )
    _add_write_arguments(timer)
    timer.add_argument(
        "--duration",
        type=float,
        default=60,
        help="countdown duration in seconds (default: 60)",
    )
    timer.add_argument(
        "--end-signal-seconds",
        type=float,
        default=4,
        help="duration of the pulsing red end signal (default: 4)",
    )
    timer.add_argument(
        "--frame-seconds",
        type=float,
        default=0.5,
        help="interval between smooth marker frames (default: 0.5)",
    )
    return parser


def _add_write_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("serial", help="12-character serial printed by the discover command")
    parser.add_argument(
        "--ip",
        help=(
            "send directly to this IPv4 address instead of relying on broadcast discovery; "
            "use the address printed by discover"
        ),
    )
    parser.add_argument(
        "--axis",
        choices=("rows", "columns"),
        default="rows",
        help="matrix direction to test (default: rows)",
    )
    parser.add_argument(
        "--brightness",
        type=float,
        default=0.72,
        help="test brightness from greater than 0 through 1 (default: 0.72)",
    )


async def run_probe(args: argparse.Namespace, target: Any, reference_factory: Any) -> None:
    if args.command == "discover":
        await discover(target, reference_factory(None), args.timeout)
        return

    _validate_write_args(args)
    reference = reference_factory(args.serial.lower())
    async with target.session() as sender:
        tube = await inspect_tube(sender, reference, args.timeout)
        print_tube(tube)
        print(f"Testing the {args.axis} axis; the original lamp state will be restored.")

        try:
            await set_power(sender, tube.serial, True)
            if args.command == "bands":
                colors = make_bands(
                    tube.width,
                    tube.height,
                    axis=args.axis,
                    brightness=args.brightness,
                )
                await set_frame(sender, tube, colors, duration=0.35)
                await asyncio.sleep(args.seconds)
            else:
                if args.command == "sweep":
                    count = axis_length(tube.width, tube.height, args.axis)
                    for position in range(count):
                        colors = make_marker(
                            tube.width,
                            tube.height,
                            axis=args.axis,
                            position=position,
                            brightness=args.brightness,
                        )
                        await set_frame(
                            sender,
                            tube,
                            colors,
                            duration=args.step_seconds * 0.72,
                        )
                        print(f"  marker {position + 1}/{count}")
                        await asyncio.sleep(args.step_seconds)
                else:
                    await run_countdown(sender, tube, args)
        finally:
            print("Restoring the previous colours and power state...")
            await set_frame(sender, tube, tube.original_colors, duration=0.35)
            await set_power(sender, tube.serial, tube.original_power > 0)

    if args.command == "bands":
        print("Test complete. Did the coloured regions appear as horizontal bands?")
    elif args.command == "sweep":
        print("Test complete. Did the marker descend smoothly along the Tube?")
    else:
        print(f"{args.duration:g}-second timer routine complete.")


async def run_countdown(sender: Any, tube: TubeState, args: argparse.Namespace) -> None:
    """Run a monotonic-clock countdown and a short pulsing expiry signal."""

    started = time.monotonic()
    next_frame_at = started
    last_printed_second: int | None = None
    last_colour_name: str | None = None

    while True:
        now = time.monotonic()
        elapsed = now - started
        remaining = max(0.0, args.duration - elapsed)
        if remaining <= 0:
            break

        progress = min(1.0, elapsed / args.duration)
        hue, colour_name = countdown_colour(progress)
        colors = make_timer_frame(
            tube.width,
            tube.height,
            axis=args.axis,
            progress=progress,
            phase="normal",
            brightness=args.brightness,
            hue_override=hue,
        )
        await set_frame(
            sender,
            tube,
            colors,
            duration=min(0.45, args.frame_seconds * 0.85),
        )

        displayed_second = int(remaining + 0.999)
        if displayed_second != last_printed_second or colour_name != last_colour_name:
            minutes, seconds = divmod(displayed_second, 60)
            print(f"  {minutes:02d}:{seconds:02d}  {colour_name}")
            last_printed_second = displayed_second
            last_colour_name = colour_name

        next_frame_at += args.frame_seconds
        await asyncio.sleep(max(0.0, next_frame_at - time.monotonic()))

    print("  00:00  expired")
    pulse_started = time.monotonic()
    pulse_index = 0
    while time.monotonic() - pulse_started < args.end_signal_seconds:
        pulse_brightness = args.brightness if pulse_index % 2 == 0 else min(0.18, args.brightness)
        colors = make_timer_frame(
            tube.width,
            tube.height,
            axis=args.axis,
            progress=1,
            phase="expired",
            brightness=pulse_brightness,
        )
        await set_frame(sender, tube, colors, duration=0.18)
        pulse_index += 1
        await asyncio.sleep(0.45)


async def discover(target: Any, reference: Any, timeout: float) -> None:
    found_any = False
    found_tube = False
    async with target.session() as sender:
        plans = sender.make_plans("address", "state", "capability", "chain")
        async for serial, complete, info in sender.gatherer.gather_per_serial(
            plans,
            reference,
            find_timeout=timeout,
            message_timeout=timeout,
        ):
            found_any = True
            if not complete:
                print(f"? {serial}: found, but some details did not respond")
                continue

            capability = info["capability"]
            product = capability["product"]
            firmware = capability["firmware"]
            state = info["state"]
            chain = info["chain"]["chain"]
            dimensions = ", ".join(f"{part.width}x{part.height}" for part in chain)
            marker = "TUBE" if product.pid in TUBE_PRODUCT_IDS else "other LIFX"
            if product.pid in TUBE_PRODUCT_IDS:
                found_tube = True
            print(
                f"[{marker}] {serial}  {product.name}  label={state['label']!r}  "
                f"firmware={firmware.version_major}.{firmware.version_minor}  "
                f"matrix={dimensions}  address={_format_address(info['address'])}"
            )

    if not found_any:
        raise ProbeError("No LIFX devices responded to local discovery.")
    if not found_tube:
        print(
            "\nNo T10/Tube was identified. Finish onboarding and confirm both devices share a LAN."
        )
    else:
        print("\nUse the serial shown above with the 'bands' or 'sweep' command.")


async def inspect_tube(
    sender: Any,
    reference: Any,
    timeout: float,
    *,
    allow_active_effect: bool = False,
) -> TubeState:
    plans = sender.make_plans("address", "state", "capability", "firmware_effects")
    results = []
    try:
        async for serial, complete, info in sender.gatherer.gather_per_serial(
            plans,
            reference,
            find_timeout=timeout,
            message_timeout=timeout,
        ):
            if complete:
                results.append((serial, info))
    except FailedToFindDevice as error:
        raise ProbeError(
            "The Tube did not answer discovery. Retry once; if that still fails, add "
            "'--ip ADDRESS' using the address printed by the discover command."
        ) from error

    if len(results) != 1:
        raise ProbeError(f"Expected exactly one responding device; received {len(results)}.")

    serial, info = results[0]
    capability = info["capability"]
    product = capability["product"]
    if product.pid not in TUBE_PRODUCT_IDS:
        raise ProbeError(
            f"Refusing to write to {product.name} (product {product.pid}); expected Tube 217/218."
        )
    if not capability["cap"].has_matrix:
        raise ProbeError("The discovered Tube does not report matrix capability.")

    effect = info["firmware_effects"]
    if not allow_active_effect and effect is not Skip and effect["type"] != TileEffectType.OFF:
        raise ProbeError(
            f"The lamp is running firmware effect {effect['type'].name}. "
            "Turn the effect off in the LIFX app and retry."
        )

    chain_packets = []
    async for packet in sender(
        TileMessages.GetDeviceChain(),
        reference,
        message_timeout=timeout,
    ):
        if packet | TileMessages.StateDeviceChain:
            chain_packets.append(packet)
    if len(chain_packets) != 1 or chain_packets[0].tile_devices_count != 1:
        raise ProbeError("Expected the Tube to report one matrix device.")

    part = chain_packets[0].tile_devices[0]
    width, height = int(part.width), int(part.height)
    if not 0 < width * height <= 64:
        raise ProbeError(f"Unsupported matrix geometry reported: {width}x{height}.")

    color_packets = []
    async for packet in sender(
        TileMessages.Get64(tile_index=0, length=1, x=0, y=0, width=width),
        reference,
        message_timeout=timeout,
    ):
        if packet | TileMessages.State64:
            color_packets.append(packet)
    if len(color_packets) != 1:
        raise ProbeError(f"Expected one colour-state packet; received {len(color_packets)}.")

    firmware = capability["firmware"]
    state = info["state"]
    return TubeState(
        serial=serial,
        name=product.name,
        firmware=f"{firmware.version_major}.{firmware.version_minor}",
        label=str(state["label"]),
        address=_format_address(info["address"]),
        width=width,
        height=height,
        original_colors=list(color_packets[0].colors),
        original_power=int(state["power"]),
        original_effect=None if effect is Skip else effect,
    )


async def set_frame(
    sender: Any,
    tube: TubeState,
    colors: list[Any],
    *,
    duration: float,
) -> None:
    message = TileMessages.Set64(
        tile_index=0,
        length=1,
        x=0,
        y=0,
        width=tube.width,
        duration=duration,
        colors=colors,
        target=tube.serial,
        ack_required=True,
        res_required=False,
    )
    await sender(message, tube.serial, limit=2)


async def set_power(sender: Any, serial: str, on: bool) -> None:
    message = LightMessages.SetLightPower(
        level=65535 if on else 0,
        duration=0.2,
        target=serial,
        ack_required=True,
        res_required=False,
    )
    await sender(message, serial, limit=2)


async def set_firmware_effect(
    sender: Any,
    serial: str,
    effect: dict[str, Any] | None,
) -> None:
    """Set a matrix firmware effect without implicitly changing lamp power."""

    effect_type = TileEffectType.OFF if effect is None else effect["type"]
    options = {} if effect is None else dict(effect.get("options", {}))
    palette = list(options.pop("palette", []))
    message = TileMessages.SetTileEffect(
        type=effect_type,
        palette_count=len(palette),
        palette=palette,
        target=serial,
        ack_required=True,
        res_required=False,
        **options,
    )
    await sender(message, serial, limit=2)


def print_tube(tube: TubeState) -> None:
    if (tube.width, tube.height) == (5, 11):
        zone_note = "55 matrix positions containing 52 physical zones"
    elif tube.zone_count == 52:
        zone_note = "52 physical zones"
    else:
        zone_note = "unexpected geometry; please report this"
    print(f"Tube: {tube.name} ({tube.serial})")
    print(f"  label: {tube.label}")
    print(f"  address: {tube.address}")
    print(f"  firmware: {tube.firmware}")
    print(f"  matrix: {tube.width}x{tube.height} = {tube.zone_count} cells ({zone_note})")


def _format_address(address: Any) -> str:
    if isinstance(address, tuple) and len(address) >= 2:
        return f"{address[0]}:{address[1]}"
    return str(address)


def _validate_write_args(args: argparse.Namespace) -> None:
    if len(args.serial) != 12:
        raise ProbeError("The serial must contain exactly 12 hexadecimal characters.")
    try:
        int(args.serial, 16)
    except ValueError as error:
        raise ProbeError("The serial must contain exactly 12 hexadecimal characters.") from error
    if not 0 < args.brightness <= 1:
        raise ProbeError("--brightness must be greater than 0 and no more than 1.")
    if getattr(args, "seconds", 1) <= 0:
        raise ProbeError("--seconds must be greater than zero.")
    if getattr(args, "step_seconds", 1) <= 0:
        raise ProbeError("--step-seconds must be greater than zero.")
    if args.command == "timer":
        if args.duration <= 0:
            raise ProbeError("--duration must be greater than zero.")
        if args.end_signal_seconds < 0:
            raise ProbeError("--end-signal-seconds cannot be negative.")
        if not 0.2 <= args.frame_seconds <= 5:
            raise ProbeError("--frame-seconds must be between 0.2 and 5 seconds.")
    if args.ip:
        try:
            parsed_ip = ipaddress.ip_address(args.ip)
        except ValueError as error:
            raise ProbeError("--ip must be a valid IPv4 address.") from error
        if parsed_ip.version != 4:
            raise ProbeError("--ip must be an IPv4 address.")


def _configure_direct_discovery(serial: str, ip: str | None) -> None:
    if ip:
        # Photons reads this process-local setting while constructing its LAN target.
        os.environ["HARDCODED_DISCOVERY"] = json.dumps({serial.lower(): ip})


def main() -> int:
    args = build_parser().parse_args()
    if args.timeout <= 0:
        print("Error: --timeout must be greater than zero.", file=sys.stderr)
        return 2

    try:
        if args.command != "discover":
            _validate_write_args(args)
            _configure_direct_discovery(args.serial, args.ip)
        collector = library_setup(config_filename=None)
        target = collector.resolve_target("lan")
        collector.run_coro_as_main(
            run_probe(args, target, collector.reference_object),
            catch_delfick_error=False,
        )
    except (ProbeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
