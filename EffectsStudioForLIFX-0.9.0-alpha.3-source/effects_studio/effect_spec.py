"""Validated, data-only descriptions of animated Tube effects."""

from __future__ import annotations

import copy
import re
from typing import Any

SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSIONS = {1}
LAYER_TYPES = {"wave", "ribbon", "sparkles", "gradient", "pulse", "chase", "ripple"}
AXES = {"x", "y", "diagonal"}
HUE_MOTION_MODES = {"fixed", "oscillate", "rotate"}
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")


class EffectSpecError(ValueError):
    """An effect description is unsafe, malformed, or outside renderer limits."""


def validate_effect_spec(value: Any) -> dict[str, Any]:
    """Return a defensive copy of a validated effect specification.

    The intentionally small vocabulary is suitable for local presets and for
    future model-generated JSON. Nothing in a spec is evaluated as code.
    """

    if not isinstance(value, dict):
        raise EffectSpecError("Effect must be a JSON object.")
    spec = copy.deepcopy(value)
    _only_keys(
        spec,
        {
            "schema_version",
            "id",
            "name",
            "description",
            "speed",
            "background",
            "layers",
            "duration",
            "transition",
            "scenes",
        },
        "effect",
    )
    if spec.get("schema_version") not in LEGACY_SCHEMA_VERSIONS | {SCHEMA_VERSION}:
        raise EffectSpecError(f"schema_version must be 1 or {SCHEMA_VERSION}.")
    spec["schema_version"] = SCHEMA_VERSION
    if not isinstance(spec.get("id"), str) or not _ID_PATTERN.fullmatch(spec["id"]):
        raise EffectSpecError("id must use lowercase letters, numbers, dashes, or underscores.")
    for key, limit in (("name", 60), ("description", 240)):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise EffectSpecError(f"{key} must be non-empty text.")
        if len(spec[key]) > limit:
            raise EffectSpecError(f"{key} is too long (maximum {limit} characters).")
    spec["speed"] = _number(spec.get("speed", 1.0), "speed", 0.0, 3.0)
    spec["background"] = _color(spec.get("background"), "background")

    layers = spec.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 6:
        raise EffectSpecError("layers must contain between 1 and 6 layers.")
    spec["layers"] = [_layer(layer, index) for index, layer in enumerate(layers)]
    scenes = spec.get("scenes")
    if scenes is not None:
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 7:
            raise EffectSpecError("scenes must contain between 1 and 7 additional scenes.")
        spec["duration"] = _number(spec.get("duration", 6), "duration", 0.5, 120)
        spec["transition"] = _transition(spec.get("transition", 1), spec["duration"], "transition")
        spec["scenes"] = [_scene(scene, index) for index, scene in enumerate(scenes)]
    elif "duration" in spec or "transition" in spec:
        raise EffectSpecError("duration and transition are only used with scenes.")
    return spec


def effect_json_schema() -> dict[str, Any]:
    """JSON Schema for a future OpenAI Structured Outputs integration."""

    color = {
        "type": "object",
        "additionalProperties": False,
        "required": ["hue", "saturation", "brightness"],
        "properties": {
            "hue": {"type": "number", "minimum": 0, "maximum": 360},
            "saturation": {"type": "number", "minimum": 0, "maximum": 1},
            "brightness": {"type": "number", "minimum": 0, "maximum": 1},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "id",
            "name",
            "description",
            "speed",
            "background",
            "layers",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,47}$"},
            "name": {"type": "string", "maxLength": 60},
            "description": {"type": "string", "maxLength": 240},
            "speed": {"type": "number", "minimum": 0, "maximum": 3},
            "background": color,
            "layers": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {"type": "object"},
            },
            "duration": {"type": "number", "minimum": 0.5, "maximum": 120},
            "transition": {"type": "number", "minimum": 0, "maximum": 5},
            "scenes": {
                "type": "array",
                "minItems": 1,
                "maxItems": 7,
                "items": {"type": "object"},
            },
        },
    }


def _layer(value: Any, index: int) -> dict[str, Any]:
    where = f"layers[{index}]"
    if not isinstance(value, dict):
        raise EffectSpecError(f"{where} must be an object.")
    layer = copy.deepcopy(value)
    kind = layer.get("type")
    if kind not in LAYER_TYPES:
        choices = ", ".join(sorted(LAYER_TYPES))
        raise EffectSpecError(f"{where}.type must be one of: {choices}.")
    common = {
        "type",
        "color",
        "palette",
        "speed",
        "intensity",
        "seed",
        "hue_motion",
        "hue_shift",  # Legacy rotation rate, retained for imported version-one recipes.
    }
    fields = {
        "wave": {"axis", "frequency", "phase"},
        "ribbon": {"axis", "frequency", "phase"},
        "sparkles": {"count", "drift"},
        "gradient": {"axis", "phase"},
        "pulse": {"frequency", "phase"},
        "chase": {"axis", "frequency", "phase", "width"},
        "ripple": {"frequency", "phase", "center_x", "center_y"},
    }
    allowed = common | fields[kind]
    _only_keys(layer, allowed, where)
    layer["color"] = _color(layer.get("color"), f"{where}.color")
    if "palette" in layer:
        layer["palette"] = _palette(layer["palette"], f"{where}.palette")
    layer["speed"] = _number(layer.get("speed", 1), f"{where}.speed", -3, 3)
    layer["intensity"] = _number(layer.get("intensity", 0.7), f"{where}.intensity", 0, 1)
    layer["seed"] = int(_number(layer.get("seed", 1), f"{where}.seed", 0, 9999))
    if "hue_motion" in layer and "hue_shift" in layer:
        raise EffectSpecError(f"{where} cannot contain both hue_motion and legacy hue_shift.")
    if "hue_motion" in layer:
        layer["hue_motion"] = _hue_motion(layer["hue_motion"], f"{where}.hue_motion")
    else:
        legacy_rate = _number(layer.pop("hue_shift", 0), f"{where}.hue_shift", -180, 180)
        layer["hue_motion"] = {
            "mode": "rotate" if legacy_rate else "fixed",
            "amplitude": 0.0,
            "speed": legacy_rate / 60,
            "phase": 0.0,
        }
    if kind == "sparkles":
        layer["count"] = int(_number(layer.get("count", 5), f"{where}.count", 1, 18))
        layer["drift"] = _number(layer.get("drift", 0.25), f"{where}.drift", -2, 2)
    elif kind in {"wave", "ribbon", "gradient", "chase"}:
        if layer.get("axis", "y") not in AXES:
            raise EffectSpecError(f"{where}.axis must be x, y, or diagonal.")
        layer["axis"] = layer.get("axis", "y")
        if kind != "gradient":
            layer["frequency"] = _number(layer.get("frequency", 1), f"{where}.frequency", 0.1, 6)
        layer["phase"] = _number(layer.get("phase", 0), f"{where}.phase", -10, 10)
        if kind == "chase":
            layer["width"] = _number(layer.get("width", 0.2), f"{where}.width", 0.05, 0.8)
    elif kind == "pulse":
        layer["frequency"] = _number(layer.get("frequency", 1), f"{where}.frequency", 0.1, 6)
        layer["phase"] = _number(layer.get("phase", 0), f"{where}.phase", -10, 10)
    else:
        layer["frequency"] = _number(layer.get("frequency", 1), f"{where}.frequency", 0.1, 6)
        layer["phase"] = _number(layer.get("phase", 0), f"{where}.phase", -10, 10)
        layer["center_x"] = _number(layer.get("center_x", 0.5), f"{where}.center_x", 0, 1)
        layer["center_y"] = _number(layer.get("center_y", 0.5), f"{where}.center_y", 0, 1)
    return layer


def _scene(value: Any, index: int) -> dict[str, Any]:
    where = f"scenes[{index}]"
    if not isinstance(value, dict):
        raise EffectSpecError(f"{where} must be an object.")
    scene = copy.deepcopy(value)
    _only_keys(scene, {"name", "duration", "transition", "background", "layers"}, where)
    name = scene.get("name", f"Scene {index + 2}")
    if not isinstance(name, str) or not name.strip() or len(name) > 40:
        raise EffectSpecError(f"{where}.name must be 1–40 characters.")
    scene["name"] = name.strip()
    scene["duration"] = _number(scene.get("duration", 6), f"{where}.duration", 0.5, 120)
    scene["transition"] = _transition(
        scene.get("transition", 1), scene["duration"], f"{where}.transition"
    )
    scene["background"] = _color(scene.get("background"), f"{where}.background")
    layers = scene.get("layers")
    if not isinstance(layers, list) or not 1 <= len(layers) <= 6:
        raise EffectSpecError(f"{where}.layers must contain between 1 and 6 layers.")
    scene["layers"] = [_layer(layer, layer_index) for layer_index, layer in enumerate(layers)]
    return scene


def _palette(value: Any, where: str) -> list[dict[str, float]]:
    if not isinstance(value, list) or not 2 <= len(value) <= 8:
        raise EffectSpecError(f"{where} must contain between 2 and 8 colours.")
    return [_color(candidate, f"{where}[{index}]") for index, candidate in enumerate(value)]


def _transition(value: Any, duration: float, where: str) -> float:
    transition = _number(value, where, 0, 5)
    if transition > duration:
        raise EffectSpecError(f"{where} cannot be longer than its scene duration.")
    return transition


def _color(value: Any, where: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise EffectSpecError(f"{where} must be a colour object.")
    _only_keys(value, {"hue", "saturation", "brightness"}, where)
    return {
        "hue": _number(value.get("hue"), f"{where}.hue", 0, 360),
        "saturation": _number(value.get("saturation"), f"{where}.saturation", 0, 1),
        "brightness": _number(value.get("brightness"), f"{where}.brightness", 0, 1),
    }


def _hue_motion(value: Any, where: str) -> dict[str, float | str]:
    if not isinstance(value, dict):
        raise EffectSpecError(f"{where} must be a colour-motion object.")
    _only_keys(value, {"mode", "amplitude", "speed", "phase"}, where)
    mode = value.get("mode")
    if mode not in HUE_MOTION_MODES:
        raise EffectSpecError(f"{where}.mode must be fixed, oscillate, or rotate.")
    return {
        "mode": mode,
        "amplitude": _number(value.get("amplitude", 0), f"{where}.amplitude", 0, 180),
        "speed": _number(value.get("speed", 0), f"{where}.speed", -3, 3),
        "phase": _number(value.get("phase", 0), f"{where}.phase", -1, 1),
    }


def _number(value: Any, where: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EffectSpecError(f"{where} must be a number.")
    result = float(value)
    if not minimum <= result <= maximum:
        raise EffectSpecError(f"{where} must be between {minimum:g} and {maximum:g}.")
    return result


def _only_keys(value: dict[str, Any], allowed: set[str], where: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise EffectSpecError(f"Unknown {where} field: {sorted(extra)[0]}.")
