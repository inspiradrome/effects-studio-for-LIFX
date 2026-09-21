"""Offline description-to-effect draft generator.

This is intentionally deterministic. A later OpenAI implementation can return
the same EffectSpec shape, pass it through validation, and use the same renderer.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from effects_studio.effect_spec import validate_effect_spec
from effects_studio.presets import color

PALETTES = {
    "ocean": (218, 182),
    "water": (218, 182),
    "forest": (128, 78),
    "jungle": (136, 54),
    "fire": (5, 38),
    "sunset": (330, 28),
    "space": (264, 196),
    "magic": (288, 176),
    "candy": (330, 178),
    "ice": (205, 178),
}


def draft_effect(description: str) -> dict[str, Any]:
    """Create a safe local draft from a short phrase, with no network calls."""

    cleaned = " ".join(description.split())[:160]
    if not cleaned:
        raise ValueError("Describe the effect first.")
    lower = cleaned.lower()
    chapters = [part.strip() for part in lower.split(" then ") if part.strip()][:4]
    primary, accent = _palette_for(chapters[0] if chapters else lower)
    seed = int.from_bytes(hashlib.sha256(cleaned.encode("utf-8")).digest()[:2], "big") % 10000
    gentle = any(word in lower for word in ("slow", "soft", "calm", "gentle", "sleepy"))
    lively = any(word in lower for word in ("fast", "party", "excited", "wild", "dance"))
    speed = 0.38 if gentle else 1.35 if lively else 0.72
    sparkle_count = (
        9 if any(word in lower for word in ("sparkle", "star", "firefly", "twinkle")) else 4
    )
    slug = re.sub(r"[^a-z0-9]+", "-", lower).strip("-")[:32] or "my-effect"
    words = cleaned.split()
    name = " ".join(words[:5]).title()
    layers: list[dict[str, Any]] = [
        {
            "type": "wave",
            "axis": "y",
            "color": color(primary, 0.88, 0.54),
            "frequency": 1.25,
            "speed": 0.62,
            "intensity": 0.68,
            "seed": seed,
        },
        {
            "type": "ribbon",
            "axis": "diagonal",
            "color": color(accent, 0.78, 0.72),
            "frequency": 1.65,
            "speed": -0.44,
            "phase": 0.35,
            "intensity": 0.55,
            "seed": seed + 1,
        },
    ]
    if any(word in lower for word in ("rainbow", "colourful", "colorful")):
        layers[0] = {
            "type": "gradient",
            "axis": "y",
            "color": color(primary, 0.9, 0.68),
            "speed": 0.7,
            "hue_motion": {
                "mode": "rotate",
                "amplitude": 0,
                "speed": 0.9,
                "phase": 0,
            },
            "intensity": 0.75,
            "seed": seed,
        }
    if any(word in lower for word in ("ring", "ripple", "sonar")):
        layers[1] = {
            "type": "ripple",
            "color": color(accent, 0.76, 0.8),
            "frequency": 2,
            "center_x": 0.5,
            "center_y": 0.5,
            "speed": 0.75,
            "intensity": 0.85,
            "seed": seed + 1,
        }
    elif any(word in lower for word in ("chase", "comet", "march")):
        layers[1] = {
            "type": "chase",
            "axis": "y",
            "color": color(accent, 0.72, 0.86),
            "frequency": 2,
            "width": 0.26,
            "speed": 0.9,
            "intensity": 0.9,
            "seed": seed + 1,
        }
    if any(word in lower for word in ("pulse", "breathe", "breathing", "heartbeat")):
        layers.append(
            {
                "type": "pulse",
                "color": color((accent + 20) % 360, 0.42, 0.62),
                "frequency": 0.75,
                "speed": 0.55,
                "intensity": 0.66,
                "seed": seed + 3,
            }
        )
    layers.append(
        {
            "type": "sparkles",
            "color": color((accent + 35) % 360, 0.48, 0.92),
            "count": sparkle_count,
            "speed": 1,
            "drift": 0.2,
            "intensity": 0.65,
            "seed": seed + 2,
        }
    )
    spec = {
        "schema_version": 2,
        "id": f"draft-{slug}"[:48].rstrip("-"),
        "name": name,
        "description": f"An offline draft inspired by: {cleaned}",
        "speed": speed,
        "background": color(primary, 0.84, 0.08),
        "layers": layers,
    }
    if len(chapters) > 1:
        spec["duration"] = 6
        spec["transition"] = 1.5
        spec["scenes"] = [
            _draft_scene(chapter, seed + 10 + index) for index, chapter in enumerate(chapters[1:])
        ]
    return validate_effect_spec(spec)


def _palette_for(description: str) -> tuple[int, int]:
    return next((palette for word, palette in PALETTES.items() if word in description), (194, 304))


def _draft_scene(description: str, seed: int) -> dict[str, Any]:
    primary, accent = _palette_for(description)
    return {
        "name": " ".join(description.split()[:4]).title(),
        "duration": 6,
        "transition": 1.5,
        "background": color(primary, 0.84, 0.08),
        "layers": [
            {
                "type": "gradient",
                "axis": "y",
                "color": color(primary, 0.86, 0.62),
                "palette": [
                    color(primary, 0.86, 0.62),
                    color(accent, 0.76, 0.72),
                    color((primary + 64) % 360, 0.7, 0.66),
                ],
                "speed": 0.45,
                "intensity": 0.78,
                "seed": seed,
            }
        ],
    }
