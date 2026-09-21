import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sanic.exceptions import InvalidUsage

from effects_studio.server import (
    _ui_connected,
    _ui_disconnected,
    _validate_device_address,
    create_app,
)


class FakeAIGenerator:
    configured = True
    last_message = ""

    def status(self):
        return {
            "mode": "openai",
            "configured": True,
            "model": "test-model",
            "message": "Ready",
        }

    async def draft(self, description, **_kwargs):
        from effects_studio.generator import draft_effect

        return {**draft_effect(description), "name": "AI Draft"}

    async def transcribe(self, audio, **_kwargs):
        assert audio == b"recorded voice"
        return "purple comet with green sparkles"

    async def translate_ui(self, language_name, locale, strings):
        assert language_name == "日本語"
        assert locale == "ja"
        return {key: f"訳: {value}" for key, value in strings.items()}

    def configure(self, **_kwargs):
        pass

    def forget_saved_key(self):
        pass


def test_device_address_accepts_tube_serial_and_ipv4() -> None:
    _validate_device_address("d073d5000001", "192.0.2.10")


@pytest.mark.parametrize(
    ("serial", "ip", "message"),
    (
        ("not-a-serial", "192.0.2.10", "12 hexadecimal"),
        ("d073d5000001", "not-an-ip", "valid IPv4"),
        ("d073d5000001", "::1", "IPv4"),
    ),
)
def test_device_address_rejects_invalid_values(serial: str, ip: str, message: str) -> None:
    with pytest.raises(InvalidUsage, match=message):
        _validate_device_address(serial, ip)


@pytest.mark.asyncio
async def test_personal_library_api_round_trip(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json")

    _, saved = await app.asgi_client.post("/api/library/save", json={"name": "Test Aurora"})
    effect_id = saved.json["effect"]["id"]
    assert effect_id == "custom-test-aurora"
    assert effect_id in saved.json["library"]["custom_ids"]

    _, favorite = await app.asgi_client.post(
        "/api/library/favorite", json={"id": effect_id, "favorite": True}
    )
    assert effect_id in favorite.json["library"]["favorites"]

    _, deleted = await app.asgi_client.post("/api/library/delete", json={"id": effect_id})
    assert effect_id not in deleted.json["library"]["custom_ids"]


@pytest.mark.asyncio
async def test_invalid_import_is_rejected(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json")

    _, response = await app.asgi_client.post(
        "/api/library/import", json={"spec": {"python": "run()"}}
    )

    assert response.status == 400


@pytest.mark.asyncio
async def test_visual_edit_preserves_playback_clock(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json")
    await app.asgi_client.post("/api/effect/select", json={"id": "ocean"})
    started_at = app.ctx.effect_started_at
    edited = {**app.ctx.effect, "name": "My Ocean", "speed": 0.8}

    _, response = await app.asgi_client.post("/api/effect/edit", json={"spec": edited})

    assert response.status == 200
    assert response.json["effect"]["name"] == "My Ocean"
    assert app.ctx.effect_started_at == started_at
    assert app.ctx.playing is True


@pytest.mark.asyncio
async def test_description_uses_configured_ai_generator(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json", ai_generator=FakeAIGenerator())

    _, response = await app.asgi_client.post(
        "/api/effect/draft", json={"description": "gentle blue sparks"}
    )

    assert response.status == 200
    assert response.json["effect"]["name"] == "AI Draft"


@pytest.mark.asyncio
async def test_voice_upload_returns_transcript_without_changing_effect(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json", ai_generator=FakeAIGenerator())
    original_effect = app.ctx.effect

    _, response = await app.asgi_client.post(
        "/api/transcribe",
        files={"audio": ("voice.webm", b"recorded voice", "audio/webm")},
    )

    assert response.status == 200
    assert response.json == {"text": "purple comet with green sparkles"}
    assert app.ctx.effect == original_effect


@pytest.mark.asyncio
async def test_language_translation_api_returns_inert_string_pack(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json", ai_generator=FakeAIGenerator())

    _, response = await app.asgi_client.post(
        "/api/language/generate",
        json={"language_name": "日本語", "locale": "ja", "strings": {"save": "Save"}},
    )

    assert response.status == 200
    assert response.json == {
        "language_name": "日本語",
        "locale": "ja",
        "translations": {"save": "訳: Save"},
    }


@pytest.mark.asyncio
async def test_paused_sequence_holds_the_exact_preview_frame(tmp_path):
    app = create_app(library_file=tmp_path / "effects.json")
    await app.asgi_client.post("/api/effect/select", json={"id": "storybook_sky"})
    _, paused = await app.asgi_client.post("/api/playback/pause")
    await asyncio.sleep(0.02)
    _, later = await app.asgi_client.get("/api/state")

    assert paused.json["frame"] == later.json["frame"]


@pytest.mark.asyncio
async def test_last_ui_disconnect_restores_native_state_and_stops_server() -> None:
    output = SimpleNamespace(restore_native=AsyncMock())
    app = SimpleNamespace(
        ctx=SimpleNamespace(
            ui_clients=1,
            ui_close_grace=0,
            server_stop_settle_delay=0,
            ui_shutdown_task=None,
            stopping=False,
            playing=True,
            effect_elapsed=12.0,
            output=output,
        ),
        stop=Mock(),
    )

    _ui_disconnected(app)
    await app.ctx.ui_shutdown_task
    await asyncio.sleep(0)

    output.restore_native.assert_awaited_once()
    app.stop.assert_called_once_with(terminate=True)
    assert app.ctx.playing is False
    assert app.ctx.effect_elapsed == 0.0


@pytest.mark.asyncio
async def test_ui_reconnect_during_grace_period_cancels_shutdown() -> None:
    output = SimpleNamespace(restore_native=AsyncMock())
    app = SimpleNamespace(
        ctx=SimpleNamespace(
            ui_clients=1,
            ui_close_grace=0.02,
            server_stop_settle_delay=0,
            ui_shutdown_task=None,
            stopping=False,
            playing=True,
            effect_elapsed=0.0,
            output=output,
        ),
        stop=Mock(),
    )

    _ui_disconnected(app)
    _ui_connected(app)
    await asyncio.sleep(0.03)

    output.restore_native.assert_not_awaited()
    app.stop.assert_not_called()
