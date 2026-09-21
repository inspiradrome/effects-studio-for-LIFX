"""Optional OpenAI-backed generator for safe, data-only effect recipes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from typing import Any

from effects_studio.credential_store import (
    CredentialStoreError,
    CredentialStoreProtocol,
    WindowsCredentialStore,
)
from effects_studio.effect_spec import LAYER_TYPES, validate_effect_spec

DEFAULT_MODEL = "gpt-5.6-luna"
RESPONSES_URL = "https://api.openai.com/v1/responses"
TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
DEFAULT_TRANSCRIPTION_MODEL = "gpt-transcribe"
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,2}$")
_TRANSLATION_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,63}$")


class AIGeneratorError(RuntimeError):
    """The remote generator could not produce a usable effect."""


class AIRecipeGenerator:
    """Create validated effect recipes through the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        requester: Callable[[dict[str, Any], str], dict[str, Any]] | None = None,
        transcriber: Callable[[bytes, str, str, str, str, str], dict[str, Any]] | None = None,
        credential_store: CredentialStoreProtocol | None = None,
    ) -> None:
        self._environment_key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
        self._session_key = ""
        self._credential_store = credential_store or WindowsCredentialStore()
        self._credential_error = ""
        try:
            self._saved_key = (self._credential_store.load() or "").strip()
        except CredentialStoreError as error:
            self._saved_key = ""
            self._credential_error = str(error)
        self.model = _validate_model(
            model or os.environ.get("LIFX_EFFECTS_OPENAI_MODEL", DEFAULT_MODEL)
        )
        self.transcription_model = _validate_model(
            os.environ.get("LIFX_EFFECTS_TRANSCRIBE_MODEL", DEFAULT_TRANSCRIPTION_MODEL)
        )
        self.enabled = bool(self._saved_key or self._environment_key)
        self.last_message = ""
        self._requester = requester or _post_response
        self._transcriber = transcriber or _post_transcription

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self._active_key())

    def configure(
        self,
        *,
        enabled: bool,
        api_key: str = "",
        model: str = "",
        remember: bool = False,
    ) -> None:
        if model.strip():
            self.model = _validate_model(model.strip())
        key = api_key.strip()
        if key:
            if len(key) > 512:
                raise ValueError("The API key is unexpectedly long.")
            if remember:
                try:
                    self._credential_store.save(key)
                except CredentialStoreError as error:
                    raise ValueError(str(error)) from error
                self._saved_key = key
                self._session_key = ""
            else:
                self._session_key = key
        if enabled and not (key or self._active_key()):
            raise ValueError("Enter an API key, or configure OPENAI_API_KEY first.")
        self.enabled = bool(enabled)
        self.last_message = ""

    def forget_saved_key(self) -> None:
        try:
            self._credential_store.delete()
        except CredentialStoreError as error:
            raise ValueError(str(error)) from error
        self._saved_key = ""
        self._session_key = ""
        self.enabled = False
        self.last_message = "Saved API key forgotten"

    def status(self) -> dict[str, object]:
        if self.configured:
            message = self.last_message or f"OpenAI ready · {self.model}"
            return {
                "mode": "openai",
                "configured": True,
                "model": self.model,
                "transcription_model": self.transcription_model,
                "saved": bool(self._saved_key),
                "message": message,
            }
        return {
            "mode": "offline",
            "configured": bool(self._active_key()),
            "model": self.model,
            "transcription_model": self.transcription_model,
            "saved": bool(self._saved_key),
            "message": self.last_message or self._credential_error or "Local idea generator",
        }

    async def draft(
        self,
        description: str,
        *,
        language: str = "global",
        accepted_language: str | None = None,
        output_language: str | None = None,
    ) -> dict[str, Any]:
        cleaned = " ".join(description.split())[:160]
        if not cleaned:
            raise ValueError("Describe the effect first.")
        accepted = _language_code(accepted_language or language)
        output = _safe_language_name(
            output_language or ("Russian" if accepted == "ru" else "English")
        )
        if accepted == "ru" and not _looks_russian(cleaned):
            raise ValueError("Говори или пиши по-русски — тогда волшебство сработает!")
        if not self.configured:
            raise AIGeneratorError("OpenAI is not configured.")
        key = self._active_key()
        try:
            response = await asyncio.to_thread(
                self._requester,
                _request_payload(cleaned, self.model, accepted, output),
                key,
            )
            draft = json.loads(_output_text(response))
            if accepted != "global" and draft.get("language_match") is not True:
                raise AIGeneratorError(f"Please use {output} for this language profile.")
            result = _normalise_recipe(draft, cleaned)
        except AIGeneratorError:
            raise
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise AIGeneratorError(
                "OpenAI returned an effect recipe the app could not use."
            ) from error
        self.last_message = f"Made with OpenAI · {self.model}"
        return result

    async def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "voice.webm",
        content_type: str = "audio/webm",
        language: str = "global",
        language_name: str = "the selected language",
    ) -> str:
        language = _language_code(language)
        language_name = _safe_language_name(language_name)
        if not self.configured:
            raise AIGeneratorError("Connect OpenAI before using voice input.")
        if not audio:
            raise ValueError("The recording was empty.")
        if len(audio) > 5 * 1024 * 1024:
            raise ValueError("The recording is too large. Keep it under 20 seconds.")
        try:
            response = await asyncio.to_thread(
                self._transcriber,
                audio,
                _safe_audio_filename(filename, content_type),
                content_type,
                self.transcription_model,
                language,
                self._active_key(),
            )
        except AIGeneratorError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise AIGeneratorError("OpenAI returned a transcript the app could not use.") from error
        text = " ".join(str(response.get("text", "")).split())[:160]
        if not text:
            raise AIGeneratorError("I couldn't hear any words. Please try again.")
        if language != "global":
            detected = response.get("languages", [])
            codes = {
                item.get("code") for item in detected if isinstance(item, dict) and item.get("code")
            }
            if not _detected_language_matches(codes, language) or (
                language == "ru" and not _looks_russian(text)
            ):
                if language == "ru":
                    raise AIGeneratorError(
                        "Я понимаю здесь только русскую речь. Попробуй ещё раз по-русски!"
                    )
                raise AIGeneratorError(f"That did not sound like {language_name}. Try again.")
        return text

    async def translate_ui(
        self,
        language_name: str,
        locale: str,
        strings: dict[str, str],
    ) -> dict[str, str]:
        """Translate a fixed UI catalogue as validated, inert string data."""
        language_name = _safe_language_name(language_name)
        locale = _language_code(locale)
        source = _validate_translation_source(strings)
        if locale == "global":
            raise ValueError("Enter a language code such as ja, fr, or pt-BR.")
        if not self.configured:
            raise AIGeneratorError("Connect OpenAI before generating a translation.")
        try:
            response = await asyncio.to_thread(
                self._requester,
                _translation_payload(language_name, locale, source, self.model),
                self._active_key(),
            )
            translated = json.loads(_output_text(response))
            return _validate_translation_result(source, translated)
        except AIGeneratorError:
            raise
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise AIGeneratorError(
                "OpenAI returned a translation pack the app could not use."
            ) from error

    def _active_key(self) -> str:
        return self._session_key or self._saved_key or self._environment_key


def ai_effect_json_schema() -> dict[str, Any]:
    """Return the strict schema used at the model boundary."""

    colour = {
        "type": "object",
        "additionalProperties": False,
        "required": ["hue", "saturation", "brightness"],
        "properties": {
            "hue": {"type": "number", "minimum": 0, "maximum": 360},
            "saturation": {"type": "number", "minimum": 0, "maximum": 1},
            "brightness": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }
    hue_motion = {
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "amplitude", "speed", "phase"],
        "properties": {
            "mode": {"type": "string", "enum": ["fixed", "oscillate", "rotate"]},
            "amplitude": {"type": "number", "minimum": 0, "maximum": 180},
            "speed": {"type": "number", "minimum": -3, "maximum": 3},
            "phase": {"type": "number", "minimum": -1, "maximum": 1},
        },
    }
    layer_properties: dict[str, Any] = {
        "type": {"type": "string", "enum": sorted(LAYER_TYPES)},
        "color": colour,
        "palette": {"type": "array", "minItems": 0, "maxItems": 8, "items": colour},
        "speed": {"type": "number", "minimum": -3, "maximum": 3},
        "intensity": {"type": "number", "minimum": 0, "maximum": 1},
        "seed": {"type": "integer", "minimum": 0, "maximum": 9999},
        "hue_motion": hue_motion,
        "axis": {"type": "string", "enum": ["x", "y", "diagonal"]},
        "frequency": {"type": "number", "minimum": 0.1, "maximum": 6},
        "phase": {"type": "number", "minimum": -10, "maximum": 10},
        "count": {"type": "integer", "minimum": 1, "maximum": 18},
        "drift": {"type": "number", "minimum": -2, "maximum": 2},
        "width": {"type": "number", "minimum": 0.05, "maximum": 0.8},
        "center_x": {"type": "number", "minimum": 0, "maximum": 1},
        "center_y": {"type": "number", "minimum": 0, "maximum": 1},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "description", "speed", "background", "layers"],
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 60},
            "description": {"type": "string", "minLength": 1, "maxLength": 240},
            "speed": {"type": "number", "minimum": 0, "maximum": 3},
            "background": colour,
            "layers": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(layer_properties),
                    "properties": layer_properties,
                },
            },
        },
    }


def _request_payload(
    description: str,
    model: str,
    accepted_language: str = "global",
    output_language: str = "English",
) -> dict[str, Any]:
    instructions = (
        "Design one delightful animated lighting effect for a LIFX Tube used for children's "
        "entertainment. The display is only 5 pixels around by 11 pixels high, so favour bold "
        "colour, readable motion, and one to four harmonious layers; do not attempt text, "
        "faces, or detailed pictures. Layer meanings: wave is a soft repeating band, ribbon is "
        "a narrower band, sparkles are drifting points, gradient is a flowing palette, "
        "pulse is whole-scene breathing, chase is a moving trail, and ripple is an "
        "expanding ring. Use an empty palette for one colour or 2–8 colours for a blended "
        "palette. Colour fidelity is more important than surprise: preserve colours stated or "
        "strongly implied by the request, and do not introduce a contrasting colour unless the "
        "user asks for one. For example, an ocean request should stay among blue, aqua, cyan, "
        "and teal. hue_motion controls only temporal hue change. Use fixed normally. Use "
        "oscillate for gentle bounded drift around each chosen colour: amplitude is the maximum "
        "hue distance in degrees and speed is cycles per effect-time second. Keep amplitude "
        "narrow enough to stay in the requested colour family. Use rotate only when the user "
        "explicitly requests rainbow, colour cycling, or a full-spectrum change; its speed is "
        "sixty degrees per effect-time second per unit. phase offsets oscillation in cycles. "
        "Set unused hue_motion numbers to zero. Return recipe data only."
    )
    instructions += f" Write the effect name and description in natural {output_language}."
    schema = ai_effect_json_schema()
    if accepted_language != "global":
        instructions += (
            f" Decide whether the user's description is primarily in {output_language}. "
            "Set language_match to false if it is not; otherwise set it to true."
        )
        schema["required"].append("language_match")
        schema["properties"]["language_match"] = {"type": "boolean"}
    return {
        "model": model,
        "store": False,
        "instructions": instructions,
        "input": description,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "lifx_tube_effect",
                "description": "A bounded, data-only animation recipe for a 5 by 11 LIFX Tube.",
                "strict": True,
                "schema": schema,
            }
        },
        "max_output_tokens": 2200,
    }


def _translation_payload(
    language_name: str,
    locale: str,
    source: dict[str, str],
    model: str,
) -> dict[str, Any]:
    properties = {key: {"type": "string", "minLength": 1, "maxLength": 500} for key in source}
    return {
        "model": model,
        "store": False,
        "instructions": (
            f"Translate the supplied software interface strings into natural {language_name} "
            f"for locale {locale}. Keep LIFX, OpenAI, API, JSON, model IDs, symbols, and all "
            "placeholders in braces unchanged. Use concise, friendly language suitable for "
            "families. Return translated string data only."
        ),
        "input": json.dumps(source, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "lifx_ui_translation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": list(source),
                    "properties": properties,
                },
            }
        },
        "max_output_tokens": 8000,
    }


def _post_response(payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise AIGeneratorError(_http_error_message(error)) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise AIGeneratorError("Could not reach OpenAI. Check the internet connection.") from error


def _post_transcription(
    audio: bytes,
    filename: str,
    content_type: str,
    model: str,
    language: str,
    api_key: str,
) -> dict[str, Any]:
    boundary = f"----lifx-effects-{uuid.uuid4().hex}"
    body = _multipart_body(
        boundary,
        fields={
            "model": model,
            "response_format": "json",
            "prompt": (
                f"A short, playful description of a LIFX Tube lighting effect in {language}."
                if language != "global"
                else "A short, playful description of a LIFX Tube lighting effect."
            ),
            **({"languages[]": language.split("-", 1)[0]} if language != "global" else {}),
        },
        file=("file", filename, content_type, audio),
    )
    request = urllib.request.Request(
        TRANSCRIPTIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise AIGeneratorError(_http_error_message(error)) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise AIGeneratorError("Could not reach OpenAI. Check the internet connection.") from error


def _multipart_body(
    boundary: str,
    *,
    fields: dict[str, str],
    file: tuple[str, str, str, bytes],
) -> bytes:
    marker = boundary.encode("ascii")
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.extend(
            [
                b"--" + marker,
                f'Content-Disposition: form-data; name="{name}"'.encode("ascii"),
                b"",
                value.encode("utf-8"),
            ]
        )
    field_name, filename, content_type, payload = file
    parts.extend(
        [
            b"--" + marker,
            (f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"').encode(
                "ascii"
            ),
            f"Content-Type: {content_type}".encode("ascii"),
            b"",
            payload,
            b"--" + marker + b"--",
            b"",
        ]
    )
    return b"\r\n".join(parts)


def _safe_audio_filename(filename: str, content_type: str) -> str:
    extension = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
    }.get(content_type.split(";", 1)[0].lower(), ".webm")
    stem = re.sub(r"[^A-Za-z0-9_-]", "", filename.rsplit(".", 1)[0])[:40] or "voice"
    return f"{stem}{extension}"


def _language_code(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned == "global":
        return "global"
    if not _LANGUAGE_PATTERN.fullmatch(cleaned):
        raise ValueError("Use a language code such as ja, fr, or pt-BR.")
    return cleaned.lower()


def _safe_language_name(value: str) -> str:
    cleaned = " ".join(str(value or "").split())[:60]
    if len(cleaned) < 2 or not all(
        character.isalpha() or character in " -()/" for character in cleaned
    ):
        raise ValueError("Enter a plain language name.")
    return cleaned


def _detected_language_matches(codes: set[str], expected: str) -> bool:
    if not codes:
        return expected == "ru"
    expected_base = expected.split("-", 1)[0]
    return any(str(code).lower().split("-", 1)[0] == expected_base for code in codes)


def _validate_translation_source(strings: dict[str, str]) -> dict[str, str]:
    if not isinstance(strings, dict) or not 1 <= len(strings) <= 180:
        raise ValueError("The interface string catalogue is invalid.")
    source = {}
    for key, value in strings.items():
        if not _TRANSLATION_KEY_PATTERN.fullmatch(str(key)) or not isinstance(value, str):
            raise ValueError("The interface string catalogue is invalid.")
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 500:
            raise ValueError("The interface string catalogue is invalid.")
        source[str(key)] = cleaned
    if sum(map(len, source.values())) > 30000:
        raise ValueError("The interface string catalogue is too large.")
    return source


def _validate_translation_result(
    source: dict[str, str], translated: dict[str, str]
) -> dict[str, str]:
    if not isinstance(translated, dict) or set(translated) != set(source):
        raise ValueError("Translation keys do not match.")
    result = {}
    for key, value in translated.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 500:
            raise ValueError("A translated interface string is invalid.")
        if set(re.findall(r"\{[A-Za-z][A-Za-z0-9]*\}", value)) != set(
            re.findall(r"\{[A-Za-z][A-Za-z0-9]*\}", source[key])
        ):
            raise ValueError("A translated string changed a required placeholder.")
        result[key] = value.strip()
    return result


def _looks_russian(text: str) -> bool:
    letters = [character for character in text if character.isalpha()]
    cyrillic = [
        character
        for character in letters
        if "\u0400" <= character <= "\u04ff" or "\u0500" <= character <= "\u052f"
    ]
    return len(cyrillic) >= 2 and len(cyrillic) / max(1, len(letters)) >= 0.6


def _http_error_message(error: urllib.error.HTTPError) -> str:
    message = f"OpenAI request failed ({error.code})."
    try:
        detail = json.loads(error.read().decode("utf-8")).get("error", {}).get("message")
        if detail:
            message = f"OpenAI: {detail}"
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        pass
    return message


def _output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
            if content.get("type") == "refusal":
                raise AIGeneratorError(
                    "OpenAI could not create that effect. Try a different description."
                )
    error = response.get("error")
    if isinstance(error, dict) and error.get("message"):
        raise AIGeneratorError(f"OpenAI: {error['message']}")
    raise AIGeneratorError("OpenAI returned no effect recipe.")


def _normalise_recipe(value: Any, prompt: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Recipe must be an object")
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    slug = re.sub(r"[^a-z0-9]+", "-", str(value.get("name", "effect")).lower()).strip("-")
    return validate_effect_spec(
        {
            "schema_version": 2,
            "id": f"ai-{slug[:34]}-{digest}"[:48].rstrip("-"),
            "name": value["name"].strip(),
            "description": value["description"].strip(),
            "speed": value["speed"],
            "background": value["background"],
            "layers": [_normalise_layer(layer) for layer in value["layers"]],
        }
    )


def _normalise_layer(value: dict[str, Any]) -> dict[str, Any]:
    kind = value["type"]
    common = {"type", "color", "speed", "intensity", "seed", "hue_motion"}
    fields = {
        "wave": {"axis", "frequency", "phase"},
        "ribbon": {"axis", "frequency", "phase"},
        "sparkles": {"count", "drift"},
        "gradient": {"axis", "phase"},
        "pulse": {"frequency", "phase"},
        "chase": {"axis", "frequency", "phase", "width"},
        "ripple": {"frequency", "phase", "center_x", "center_y"},
    }
    layer = {key: value[key] for key in common | fields[kind]}
    if len(value.get("palette", [])) >= 2:
        layer["palette"] = value["palette"]
    return layer


def _validate_model(value: str) -> str:
    if not _MODEL_PATTERN.fullmatch(value):
        raise ValueError(
            "Model names may contain letters, numbers, dots, dashes, underscores, or colons."
        )
    return value
