"""Safe renderer for the small EffectSpec animation vocabulary."""

from __future__ import annotations

import math
from typing import Any

from effects_studio.effect_spec import validate_effect_spec
from effects_studio.t10_probe import Color, make_color, pad_set64


def render_effect(
    untrusted_spec: dict[str, Any],
    width: int,
    height: int,
    *,
    brightness: float = 0.72,
    now: float = 0.0,
) -> list[Color]:
    """Render one matrix frame. Validation happens at this trust boundary."""

    if width <= 0 or height <= 0 or width * height > 64:
        raise ValueError("Matrix dimensions must contain between 1 and 64 cells.")
    if not 0 < brightness <= 1:
        raise ValueError("brightness must be greater than 0 and no more than 1")
    spec = validate_effect_spec(untrusted_spec)
    moment = now * spec["speed"]
    if "scenes" not in spec:
        return _render_scene(spec, width, height, brightness, moment)

    scenes = [spec, *spec["scenes"]]
    elapsed = moment % sum(float(scene["duration"]) for scene in scenes)
    scene_index = 0
    for index, scene in enumerate(scenes):
        duration = float(scene["duration"])
        if elapsed < duration:
            scene_index = index
            break
        elapsed -= duration
    scene = scenes[scene_index]
    outgoing = _render_scene(scene, width, height, brightness, moment)
    transition = float(scene["transition"])
    if transition <= 0 or elapsed < float(scene["duration"]) - transition:
        return outgoing
    incoming = _render_scene(
        scenes[(scene_index + 1) % len(scenes)], width, height, brightness, moment
    )
    amount = (elapsed - (float(scene["duration"]) - transition)) / transition
    amount = amount * amount * (3 - 2 * amount)
    return _blend_frames(outgoing, incoming, amount)


def _render_scene(
    scene: dict[str, Any], width: int, height: int, brightness: float, moment: float
) -> list[Color]:
    base = scene["background"]
    colors: list[Color] = []
    for row in range(height):
        y = row / max(1, height - 1)
        for column in range(width):
            x = column / max(1, width - 1)
            hue = base["hue"]
            saturation = base["saturation"]
            level = base["brightness"]
            for layer in scene["layers"]:
                weight = _layer_weight(layer, x, y, moment, width, height)
                if weight <= 0:
                    continue
                color = _layer_color(layer, x, y, moment, weight)
                layer_hue = color["hue"] + _hue_offset(layer["hue_motion"], moment)
                contribution = weight * layer["intensity"]
                hue = _mix_hue(hue, layer_hue, min(1, contribution))
                saturation += (color["saturation"] - saturation) * min(1, contribution)
                level = min(1, level + color["brightness"] * contribution)
            colors.append(make_color(hue % 360, saturation, min(brightness, level * brightness)))
    return pad_set64(colors)


def _layer_color(
    layer: dict[str, Any], x: float, y: float, moment: float, weight: float
) -> dict[str, float]:
    if "palette" not in layer:
        return layer["color"]
    if layer["type"] == "gradient":
        axis_position = {"x": x, "y": y, "diagonal": (x + y) / 2}[layer["axis"]]
        position = (axis_position + moment * layer["speed"] * 0.06 + layer["phase"]) % 1
    else:
        position = (x * 0.32 + y * 0.68 + moment * layer["speed"] * 0.05 + weight * 0.1) % 1
    return _sample_palette(layer["palette"], position)


def _sample_palette(palette: list[dict[str, float]], position: float) -> dict[str, float]:
    scaled = max(0.0, min(1.0, position)) * (len(palette) - 1)
    left_index = min(int(scaled), len(palette) - 2)
    amount = scaled - left_index
    left, right = palette[left_index], palette[left_index + 1]
    return {
        "hue": _mix_hue(left["hue"], right["hue"], amount),
        "saturation": left["saturation"] + (right["saturation"] - left["saturation"]) * amount,
        "brightness": left["brightness"] + (right["brightness"] - left["brightness"]) * amount,
    }


def _blend_frames(left: list[Color], right: list[Color], amount: float) -> list[Color]:
    blended: list[Color] = []
    for first, second in zip(left, right, strict=True):
        blended.append(
            make_color(
                _mix_hue(float(first["hue"]), float(second["hue"]), amount),
                float(first["saturation"])
                + (float(second["saturation"]) - float(first["saturation"])) * amount,
                float(first["brightness"])
                + (float(second["brightness"]) - float(first["brightness"])) * amount,
            )
        )
    return blended


def _hue_offset(motion: dict[str, Any], moment: float) -> float:
    mode = motion["mode"]
    if mode == "oscillate":
        angle = math.tau * (moment * motion["speed"] + motion["phase"])
        return float(motion["amplitude"]) * math.sin(angle)
    if mode == "rotate":
        # One speed unit is one sixth of the colour wheel per effect-time second.
        return moment * float(motion["speed"]) * 60
    return 0.0


def _layer_weight(
    layer: dict[str, Any], x: float, y: float, now: float, width: int, height: int
) -> float:
    kind = layer["type"]
    if kind == "sparkles":
        return _sparkle_weight(layer, x, y, now, width, height)
    if kind == "pulse":
        angle = math.tau * (now * layer["speed"] * layer["frequency"] * 0.18 + layer["phase"])
        return 0.12 + 0.88 * ((math.sin(angle) + 1) / 2) ** 2
    if kind == "ripple":
        distance = math.hypot(x - layer["center_x"], (y - layer["center_y"]) * 0.55)
        angle = math.tau * (
            distance * layer["frequency"] - now * layer["speed"] * 0.18 + layer["phase"]
        )
        return ((math.sin(angle) + 1) / 2) ** 5
    position = {"x": x, "y": y, "diagonal": (x + y) / 2}[layer["axis"]]
    if kind == "gradient":
        if "palette" in layer:
            return 1.0
        travel = (position + now * layer["speed"] * 0.06 + layer["phase"]) % 2
        return travel if travel <= 1 else 2 - travel
    if kind == "chase":
        center = (now * layer["speed"] * 0.12 + layer["phase"]) % 1
        repeated = (position * layer["frequency"]) % 1
        distance = min(abs(repeated - center), 1 - abs(repeated - center))
        return max(0, 1 - distance / layer["width"]) ** 2
    angle = math.tau * (
        position * layer["frequency"] + now * layer["speed"] * 0.16 + layer["phase"]
    )
    wave = (math.sin(angle) + 1) / 2
    return wave**4 if kind == "ribbon" else 0.18 + 0.82 * wave


def _sparkle_weight(
    layer: dict[str, Any], x: float, y: float, now: float, width: int, height: int
) -> float:
    strongest = 0.0
    for index in range(layer["count"]):
        seed = layer["seed"] + index * 97
        sx = (_noise(seed) + now * layer["drift"] * (0.025 + _noise(seed + 1) * 0.035)) % 1
        sy = (_noise(seed + 2) + now * layer["drift"] * (0.018 + _noise(seed + 3) * 0.025)) % 1
        dx = min(abs(x - sx), 1 - abs(x - sx)) * width
        dy = min(abs(y - sy), 1 - abs(y - sy)) * height
        distance = math.hypot(dx, dy)
        pulse = max(0, math.sin(now * (1.1 + _noise(seed + 4)) + seed)) ** 6
        strongest = max(strongest, max(0, 1 - distance) * pulse)
    return strongest


def _noise(seed: int) -> float:
    value = math.sin(seed * 12.9898 + 78.233) * 43758.5453
    return value - math.floor(value)


def _mix_hue(left: float, right: float, amount: float) -> float:
    difference = (right - left + 180) % 360 - 180
    return (left + difference * amount) % 360
