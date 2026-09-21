import json

import pytest

from effects_studio.ai_generator import AIGeneratorError, AIRecipeGenerator, ai_effect_json_schema


class MemoryCredentialStore:
    def __init__(self, secret=None):
        self.secret = secret

    def load(self):
        return self.secret

    def save(self, secret):
        self.secret = secret

    def delete(self):
        self.secret = None


def model_recipe():
    colour = {"hue": 190, "saturation": 0.8, "brightness": 0.6}
    return {
        "name": "Ocean Fireflies",
        "description": "Soft cyan waves with drifting golden lights.",
        "speed": 0.55,
        "background": {**colour, "brightness": 0.08},
        "layers": [
            {
                "type": "sparkles",
                "color": colour,
                "palette": [],
                "speed": 0.4,
                "intensity": 0.7,
                "seed": 42,
                "hue_motion": {
                    "mode": "fixed",
                    "amplitude": 0,
                    "speed": 0,
                    "phase": 0,
                },
                "axis": "y",
                "frequency": 1,
                "phase": 0,
                "count": 8,
                "drift": 0.2,
                "width": 0.2,
                "center_x": 0.5,
                "center_y": 0.5,
            }
        ],
    }


def response_for(recipe):
    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(recipe)}],
            }
        ]
    }


@pytest.mark.asyncio
async def test_ai_generator_requests_strict_unstored_recipe_and_validates_it():
    captured = {}

    def requester(payload, key):
        captured.update(payload=payload, key=key)
        return response_for(model_recipe())

    generator = AIRecipeGenerator(
        api_key="test-secret", requester=requester, credential_store=MemoryCredentialStore()
    )
    result = await generator.draft("blue fireflies")

    assert captured["key"] == "test-secret"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["text"]["format"]["strict"] is True
    assert (
        "ocean request should stay among blue, aqua, cyan, and teal"
        in captured["payload"]["instructions"]
    )
    assert result["id"].startswith("ai-ocean-fireflies-")
    assert result["layers"][0]["type"] == "sparkles"
    assert "axis" not in result["layers"][0]
    assert "palette" not in result["layers"][0]


@pytest.mark.asyncio
async def test_voice_recording_is_transcribed_with_the_same_private_key():
    captured = {}

    def transcriber(audio, filename, content_type, model, language, key):
        captured.update(
            audio=audio,
            filename=filename,
            content_type=content_type,
            model=model,
            language=language,
            key=key,
        )
        return {"text": "  a calm blue ocean   with golden sparks  "}

    generator = AIRecipeGenerator(
        api_key="test-secret",
        transcriber=transcriber,
        credential_store=MemoryCredentialStore(),
    )
    text = await generator.transcribe(
        b"pretend webm", filename="unsafe name.exe", content_type="audio/webm;codecs=opus"
    )

    assert text == "a calm blue ocean with golden sparks"
    assert captured == {
        "audio": b"pretend webm",
        "filename": "unsafename.webm",
        "content_type": "audio/webm;codecs=opus",
        "model": "gpt-transcribe",
        "language": "global",
        "key": "test-secret",
    }


@pytest.mark.asyncio
async def test_russian_mode_requires_russian_description_and_requests_russian_output():
    captured = {}
    recipe = model_recipe()
    recipe["name"] = "Океанские светлячки"
    recipe["description"] = "Голубые волны и золотые огоньки."
    recipe["language_match"] = True

    def requester(payload, _key):
        captured.update(payload)
        return response_for(recipe)

    generator = AIRecipeGenerator(
        api_key="test-secret", requester=requester, credential_store=MemoryCredentialStore()
    )

    with pytest.raises(ValueError, match="по-русски"):
        await generator.draft("blue fireflies", language="ru")

    result = await generator.draft("голубые волны и золотые огоньки", language="ru")

    assert result["name"] == "Океанские светлячки"
    assert "natural Russian" in captured["instructions"]


@pytest.mark.asyncio
async def test_restricted_language_uses_structured_language_check():
    captured = {}
    recipe = {**model_recipe(), "language_match": False}

    def requester(payload, _key):
        captured.update(payload)
        return response_for(recipe)

    generator = AIRecipeGenerator(
        api_key="test-secret", requester=requester, credential_store=MemoryCredentialStore()
    )

    with pytest.raises(AIGeneratorError, match="Japanese"):
        await generator.draft("blue fireflies", accepted_language="ja", output_language="Japanese")

    schema = captured["text"]["format"]["schema"]
    assert schema["properties"]["language_match"] == {"type": "boolean"}
    assert "language_match" in schema["required"]


@pytest.mark.asyncio
async def test_ui_translation_is_strict_and_preserves_placeholders():
    captured = {}
    source = {"hello": "Hello", "scenes": "{count} scenes"}

    def requester(payload, _key):
        captured.update(payload)
        return response_for({"hello": "こんにちは", "scenes": "シーン: {count}"})

    generator = AIRecipeGenerator(
        api_key="test-secret", requester=requester, credential_store=MemoryCredentialStore()
    )
    translated = await generator.translate_ui("日本語", "ja", source)

    assert translated == {"hello": "こんにちは", "scenes": "シーン: {count}"}
    schema = captured["text"]["format"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(source)


@pytest.mark.asyncio
async def test_ui_translation_rejects_changed_placeholders():
    def requester(_payload, _key):
        return response_for({"scenes": "シーン"})

    generator = AIRecipeGenerator(
        api_key="test-secret", requester=requester, credential_store=MemoryCredentialStore()
    )

    with pytest.raises(AIGeneratorError, match="could not use"):
        await generator.translate_ui("日本語", "ja", {"scenes": "{count} scenes"})


@pytest.mark.asyncio
async def test_russian_voice_mode_hints_and_enforces_russian():
    calls = []

    def transcriber(_audio, _filename, _content_type, _model, language, _key):
        calls.append(language)
        return {"text": "синие волны с золотыми искрами", "languages": [{"code": "ru"}]}

    generator = AIRecipeGenerator(
        api_key="test-secret",
        transcriber=transcriber,
        credential_store=MemoryCredentialStore(),
    )

    assert await generator.transcribe(b"audio", language="ru") == ("синие волны с золотыми искрами")
    assert calls == ["ru"]


@pytest.mark.asyncio
async def test_russian_voice_mode_rejects_non_russian_transcript():
    def transcriber(*_args):
        return {"text": "blue waves", "languages": [{"code": "en"}]}

    generator = AIRecipeGenerator(
        api_key="test-secret",
        transcriber=transcriber,
        credential_store=MemoryCredentialStore(),
    )

    with pytest.raises(AIGeneratorError, match="русскую речь"):
        await generator.transcribe(b"audio", language="ru")


@pytest.mark.asyncio
async def test_generated_profile_can_restrict_voice_to_another_language():
    def transcriber(_audio, _filename, _content_type, _model, language, _key):
        assert language == "ja"
        return {"text": "青い波と星", "languages": [{"code": "ja"}]}

    generator = AIRecipeGenerator(
        api_key="test-secret",
        transcriber=transcriber,
        credential_store=MemoryCredentialStore(),
    )

    assert (
        await generator.transcribe(b"audio", language="ja", language_name="日本語") == "青い波と星"
    )


def test_ai_schema_requires_every_declared_layer_field():
    layer = ai_effect_json_schema()["properties"]["layers"]["items"]

    assert layer["additionalProperties"] is False
    assert set(layer["required"]) == set(layer["properties"])
    assert layer["properties"]["hue_motion"]["properties"]["mode"]["enum"] == [
        "fixed",
        "oscillate",
        "rotate",
    ]


def test_configured_key_is_never_returned_in_status():
    generator = AIRecipeGenerator(
        api_key="environment-secret", credential_store=MemoryCredentialStore()
    )

    assert generator.status()["configured"] is True
    assert "environment-secret" not in json.dumps(generator.status())


def test_saved_key_is_reused_and_can_be_forgotten(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    store = MemoryCredentialStore()
    first = AIRecipeGenerator(credential_store=store)

    first.configure(enabled=True, api_key="saved-secret", remember=True)
    restarted = AIRecipeGenerator(credential_store=store)

    assert restarted.configured is True
    assert restarted.status()["saved"] is True
    assert "saved-secret" not in json.dumps(restarted.status())

    restarted.forget_saved_key()

    assert store.secret is None
    assert restarted.configured is False
    assert restarted.status()["saved"] is False


def test_enabling_ai_without_any_key_is_rejected(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    generator = AIRecipeGenerator(credential_store=MemoryCredentialStore())

    with pytest.raises(ValueError, match="Enter an API key"):
        generator.configure(enabled=True)
