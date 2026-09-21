"""Local web application for designing and playing LIFX Tube effects."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import time
from pathlib import Path

from sanic import Sanic
from sanic.exceptions import InvalidUsage, ServiceUnavailable, WebsocketClosed
from sanic.request import Request
from sanic.response import file
from sanic.response import json as json_response

from effects_studio.ai_generator import AIGeneratorError, AIRecipeGenerator
from effects_studio.effect_spec import EffectSpecError, validate_effect_spec
from effects_studio.generator import draft_effect
from effects_studio.library import EffectLibrary
from effects_studio.lifx_output import StudioOutput, TubeOutputConfig, discover_tubes
from effects_studio.presets import PRESETS
from effects_studio.renderer import render_effect

STATIC_DIR = Path(__file__).with_name("static")
DEFAULT_UI_CLOSE_GRACE = 3.0
SERVER_STOP_SETTLE_DELAY = 1.0


def create_app(
    output_config: TubeOutputConfig | None = None,
    *,
    library_file: Path | None = None,
    ai_generator: AIRecipeGenerator | None = None,
    ui_close_grace: float = DEFAULT_UI_CLOSE_GRACE,
    server_stop_settle_delay: float = SERVER_STOP_SETTLE_DELAY,
) -> Sanic:
    # A unique name keeps isolated app instances from colliding in tests and
    # when a stopped development server is relaunched in the same interpreter.
    app = Sanic(f"lifx_effects_studio_{time.monotonic_ns()}")
    app.config.TOUCHUP = False
    app.ctx.output = StudioOutput(output_config) if output_config else None
    app.ctx.effect = validate_effect_spec(PRESETS["aurora"])
    app.ctx.library = EffectLibrary(library_file)
    app.ctx.ai_generator = ai_generator or AIRecipeGenerator()
    app.ctx.playing = False
    app.ctx.effect_started_at = time.monotonic()
    app.ctx.effect_elapsed = 0.0
    app.ctx.brightness = output_config.brightness if output_config else 0.72
    app.ctx.discovered_devices = []
    app.ctx.discovery_lock = asyncio.Lock()
    app.ctx.ui_clients = 0
    app.ctx.ui_close_grace = ui_close_grace
    app.ctx.server_stop_settle_delay = server_stop_settle_delay
    app.ctx.ui_shutdown_task = None
    app.ctx.stopping = False
    app.static("/static", STATIC_DIR)

    def current_payload() -> dict[str, object]:
        frame = render_effect(
            app.ctx.effect,
            5,
            11,
            brightness=app.ctx.brightness,
            now=_playback_time(app),
        )[:55]
        return {
            "effect": app.ctx.effect,
            "frame": frame,
            "playing": app.ctx.playing,
            "brightness": app.ctx.brightness,
            "library": {
                "items": _library_items(app.ctx.library),
                "custom_ids": sorted(app.ctx.library.effects),
                "favorites": sorted(app.ctx.library.favorites),
            },
            "device": app.ctx.output.status()
            if app.ctx.output
            else {
                "mode": "simulation",
                "connected": False,
                "message": "Preview only",
                "playing": app.ctx.playing,
            },
            "devices": app.ctx.discovered_devices,
            "generator": app.ctx.ai_generator.status(),
        }

    @app.before_server_start
    async def start_output(_: Sanic) -> None:
        if app.ctx.output:
            await app.ctx.output.start()

    @app.after_server_stop
    async def stop_output(_: Sanic) -> None:
        app.ctx.stopping = True
        shutdown_task = app.ctx.ui_shutdown_task
        if shutdown_task and shutdown_task is not asyncio.current_task():
            shutdown_task.cancel()
        if app.ctx.output:
            await app.ctx.output.stop()

    @app.get("/")
    async def index(_: Request):
        return await file(STATIC_DIR / "index.html")

    @app.get("/api/state")
    async def state(_: Request):
        return json_response(current_payload())

    @app.post("/api/effect/preset")
    async def choose_preset(request: Request):
        preset_id = str((request.json or {}).get("id", ""))
        if preset_id not in PRESETS:
            raise InvalidUsage("Choose a recognised preset.")
        await _select_effect(app, PRESETS[preset_id])
        return json_response(current_payload())

    @app.post("/api/effect/select")
    async def choose_effect(request: Request):
        effect_id = str((request.json or {}).get("id", ""))
        spec = PRESETS.get(effect_id) or app.ctx.library.effects.get(effect_id)
        if spec is None:
            raise InvalidUsage("Choose an effect from the library.")
        await _select_effect(app, spec)
        return json_response(current_payload())

    @app.post("/api/effect/draft")
    async def make_draft(request: Request):
        payload = request.json or {}
        description = str(payload.get("description", ""))
        accepted_language = str(payload.get("accepted_language", payload.get("language", "global")))
        output_language = str(payload.get("output_language", "English"))
        try:
            if app.ctx.ai_generator.configured:
                try:
                    spec = await app.ctx.ai_generator.draft(
                        description,
                        accepted_language=accepted_language,
                        output_language=output_language,
                    )
                except AIGeneratorError as error:
                    if accepted_language != "global":
                        raise ServiceUnavailable(str(error)) from error
                    app.ctx.ai_generator.last_message = "OpenAI unavailable · made locally instead"
                    spec = draft_effect(description)
            elif accepted_language != "global":
                raise InvalidUsage("Connect OpenAI to use a restricted language profile.")
            else:
                spec = draft_effect(description)
            await _select_effect(app, spec)
        except (ValueError, EffectSpecError) as error:
            raise InvalidUsage(str(error)) from error
        return json_response(current_payload())

    @app.post("/api/generator/configure")
    async def configure_generator(request: Request):
        payload = request.json or {}
        try:
            app.ctx.ai_generator.configure(
                enabled=bool(payload.get("enabled", False)),
                api_key=str(payload.get("api_key", "")),
                model=str(payload.get("model", "")),
                remember=bool(payload.get("remember", False)),
            )
        except ValueError as error:
            raise InvalidUsage(str(error)) from error
        return json_response(current_payload())

    @app.post("/api/generator/forget")
    async def forget_generator_key(_: Request):
        try:
            app.ctx.ai_generator.forget_saved_key()
        except ValueError as error:
            raise InvalidUsage(str(error)) from error
        return json_response(current_payload())

    @app.post("/api/transcribe")
    async def transcribe_voice(request: Request):
        upload = request.files.get("audio") if request.files else None
        if upload is None:
            raise InvalidUsage("Record something first.")
        try:
            language = str(request.form.get("language", "global"))
            transcript = await app.ctx.ai_generator.transcribe(
                upload.body,
                filename=upload.name or "voice.webm",
                content_type=upload.type or "audio/webm",
                language=language,
                language_name=str(request.form.get("language_name", "the selected language")),
            )
        except ValueError as error:
            raise InvalidUsage(str(error)) from error
        except AIGeneratorError as error:
            raise ServiceUnavailable(str(error)) from error
        return json_response({"text": transcript})

    @app.post("/api/language/generate")
    async def generate_language(request: Request):
        payload = request.json or {}
        try:
            translations = await app.ctx.ai_generator.translate_ui(
                str(payload.get("language_name", "")),
                str(payload.get("locale", "")),
                payload.get("strings", {}),
            )
        except ValueError as error:
            raise InvalidUsage(str(error)) from error
        except AIGeneratorError as error:
            raise ServiceUnavailable(str(error)) from error
        return json_response(
            {
                "language_name": " ".join(str(payload.get("language_name", "")).split())[:60],
                "locale": str(payload.get("locale", "")).strip().lower(),
                "translations": translations,
            }
        )

    @app.post("/api/effect/spec")
    async def load_spec(request: Request):
        try:
            await _select_effect(app, validate_effect_spec((request.json or {}).get("spec")))
        except EffectSpecError as error:
            raise InvalidUsage(str(error)) from error
        return json_response(current_payload())

    @app.post("/api/effect/edit")
    async def edit_spec(request: Request):
        try:
            app.ctx.effect = validate_effect_spec((request.json or {}).get("spec"))
        except EffectSpecError as error:
            raise InvalidUsage(str(error)) from error
        if app.ctx.output:
            app.ctx.output.update_effect(app.ctx.effect)
        return json_response(current_payload())

    @app.post("/api/library/save")
    async def save_to_library(request: Request):
        payload = request.json or {}
        try:
            saved = app.ctx.library.save_effect(
                app.ctx.effect,
                name=str(payload["name"]) if "name" in payload else None,
                force_new=bool(payload.get("force_new", False)),
            )
            await _select_effect(app, saved)
        except (EffectSpecError, ValueError) as error:
            raise InvalidUsage(str(error)) from error
        return json_response(current_payload())

    @app.post("/api/library/import")
    async def import_effect(request: Request):
        try:
            saved = app.ctx.library.save_effect((request.json or {}).get("spec"), force_new=True)
            await _select_effect(app, saved)
        except (EffectSpecError, ValueError) as error:
            raise InvalidUsage(str(error)) from error
        return json_response(current_payload())

    @app.post("/api/library/favorite")
    async def favorite_effect(request: Request):
        payload = request.json or {}
        effect_id = str(payload.get("id", ""))
        if effect_id not in PRESETS and effect_id not in app.ctx.library.effects:
            raise InvalidUsage("Choose an effect from the library.")
        app.ctx.library.set_favorite(effect_id, bool(payload.get("favorite", True)))
        return json_response(current_payload())

    @app.post("/api/library/delete")
    async def delete_effect(request: Request):
        effect_id = str((request.json or {}).get("id", ""))
        try:
            app.ctx.library.delete_effect(effect_id)
        except KeyError as error:
            raise InvalidUsage(str(error.args[0])) from error
        if app.ctx.effect["id"] == effect_id:
            await _select_effect(app, PRESETS["aurora"])
        return json_response(current_payload())

    @app.post("/api/playback/<action:str>")
    async def playback(_: Request, action: str):
        if action == "play":
            if not app.ctx.playing:
                app.ctx.effect_started_at = time.monotonic()
                app.ctx.playing = True
                if app.ctx.output:
                    if app.ctx.effect_elapsed == 0:
                        await app.ctx.output.set_effect(app.ctx.effect)
                    else:
                        await app.ctx.output.resume()
        elif action == "pause":
            if app.ctx.playing:
                app.ctx.effect_elapsed = _playback_time(app)
                app.ctx.playing = False
                if app.ctx.output:
                    await app.ctx.output.pause()
        elif action == "native":
            app.ctx.playing = False
            app.ctx.effect_elapsed = 0.0
            if app.ctx.output:
                await app.ctx.output.restore_native()
        else:
            raise InvalidUsage("Unknown playback action.")
        return json_response(current_payload())

    @app.post("/api/tune")
    async def tune(request: Request):
        payload = request.json or {}
        try:
            speed = float(payload.get("speed", app.ctx.effect["speed"]))
            brightness = float(payload.get("brightness", app.ctx.brightness))
        except (TypeError, ValueError) as error:
            raise InvalidUsage("Speed and brightness must be numbers.") from error
        if not 0 <= speed <= 3 or not 0.05 <= brightness <= 1:
            raise InvalidUsage("Speed must be 0–3 and brightness 0.05–1.")
        app.ctx.effect = {**app.ctx.effect, "speed": speed}
        app.ctx.brightness = brightness
        if app.ctx.output:
            app.ctx.output.set_brightness(brightness)
            if app.ctx.playing:
                app.ctx.output.update_effect(app.ctx.effect)
        return json_response(current_payload())

    @app.post("/api/device/discover")
    async def discover_devices(_: Request):
        try:
            async with app.ctx.discovery_lock:
                app.ctx.discovered_devices = await discover_tubes()
        except Exception as error:
            raise ServiceUnavailable("The LAN scan failed. Check Wi-Fi and try again.") from error
        return json_response(current_payload())

    @app.post("/api/device/connect")
    async def connect_device(request: Request):
        payload = request.json or {}
        serial, ip = str(payload.get("serial", "")).lower(), str(payload.get("ip", ""))
        _validate_device_address(serial, ip)
        config = TubeOutputConfig(serial=serial, ip=ip, brightness=app.ctx.brightness)
        if app.ctx.output:
            await app.ctx.output.reconfigure(config)
        else:
            app.ctx.output = StudioOutput(config)
            await app.ctx.output.start()
        if app.ctx.playing:
            await app.ctx.output.set_effect(app.ctx.effect)
        return json_response(current_payload())

    @app.post("/api/device/reconnect")
    async def reconnect_device(_: Request):
        if not app.ctx.output:
            raise InvalidUsage("Choose or discover a Tube first.")
        await app.ctx.output.reconnect()
        return json_response(current_payload())

    @app.websocket("/ws")
    async def live_state(_: Request, websocket):
        _ui_connected(app)
        try:
            while True:
                await websocket.send(json.dumps(current_payload()))
                await asyncio.sleep(0.12)
        except asyncio.CancelledError:
            raise
        except (ConnectionError, WebsocketClosed):
            return
        finally:
            _ui_disconnected(app)

    return app


def _ui_connected(app: Sanic) -> None:
    """Register a browser UI and cancel a pending close-after-reload shutdown."""
    app.ctx.ui_clients += 1
    shutdown_task = app.ctx.ui_shutdown_task
    if shutdown_task and not shutdown_task.done():
        shutdown_task.cancel()
    app.ctx.ui_shutdown_task = None


def _ui_disconnected(app: Sanic) -> None:
    """Release the Tube and stop the hidden server after the final UI closes."""
    app.ctx.ui_clients = max(0, app.ctx.ui_clients - 1)
    if app.ctx.ui_clients == 0 and not app.ctx.stopping:
        app.ctx.ui_shutdown_task = asyncio.create_task(_shutdown_after_ui_close(app))


async def _shutdown_after_ui_close(app: Sanic) -> None:
    try:
        await asyncio.sleep(app.ctx.ui_close_grace)
        if app.ctx.ui_clients:
            return

        app.ctx.playing = False
        app.ctx.effect_elapsed = 0.0
        if app.ctx.output:
            await app.ctx.output.restore_native()

        if not app.ctx.ui_clients:
            app.ctx.ui_shutdown_task = None
            # On Windows, Sanic keeps a small signal-wakeup task alive. Marking
            # shutdown first lets that task finish normally before app.stop()
            # closes the loop, avoiding a stray "Task was destroyed" warning.
            if hasattr(app, "state"):
                app.state.is_stopping = True
            # Let this task return before Sanic stops the event loop; otherwise
            # asyncio reports the task itself as having been destroyed mid-flight.
            asyncio.get_running_loop().call_later(
                app.ctx.server_stop_settle_delay, _stop_if_ui_still_closed, app
            )
    except asyncio.CancelledError:
        return


def _stop_if_ui_still_closed(app: Sanic) -> None:
    if not app.ctx.ui_clients and not app.ctx.stopping:
        app.stop(terminate=True)


async def _select_effect(app: Sanic, spec: dict[str, object]) -> None:
    app.ctx.effect = validate_effect_spec(spec)
    app.ctx.effect_elapsed = 0.0
    app.ctx.effect_started_at = time.monotonic()
    app.ctx.playing = True
    if app.ctx.output:
        await app.ctx.output.set_effect(app.ctx.effect)


def _playback_time(app: Sanic) -> float:
    if not app.ctx.playing:
        return float(app.ctx.effect_elapsed)
    return float(app.ctx.effect_elapsed) + time.monotonic() - float(app.ctx.effect_started_at)


def _validate_device_address(serial: str, ip: str) -> None:
    if len(serial) != 12:
        raise InvalidUsage("The Tube serial must contain 12 hexadecimal characters.")
    try:
        int(serial, 16)
    except ValueError as error:
        raise InvalidUsage("The Tube serial must contain 12 hexadecimal characters.") from error
    try:
        parsed_ip = ipaddress.ip_address(ip)
    except ValueError as error:
        raise InvalidUsage("Enter a valid IPv4 address.") from error
    if parsed_ip.version != 4:
        raise InvalidUsage("Enter an IPv4 address.")


def _library_items(library: EffectLibrary) -> list[dict[str, object]]:
    items = []
    for built_in, effects in ((True, PRESETS), (False, library.effects)):
        for spec in effects.values():
            items.append(
                {
                    "id": spec["id"],
                    "name": spec["name"],
                    "description": spec["description"],
                    "builtin": built_in,
                    "favorite": spec["id"] in library.favorites,
                    "scene_count": 1 + len(spec.get("scenes", [])),
                    "uses_palette": _uses_palette(spec),
                }
            )
    return sorted(items, key=lambda item: (not item["favorite"], not item["builtin"], item["name"]))


def _uses_palette(spec: dict[str, object]) -> bool:
    scenes = [spec, *spec.get("scenes", [])]
    return any("palette" in layer for scene in scenes for layer in scene["layers"])
