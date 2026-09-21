"""Persistent personal effect library stored as validated JSON."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from effects_studio.effect_spec import EffectSpecError, validate_effect_spec


def library_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.cwd()))
    return base / "LIFXEffectsStudio" / "effects.json"


class EffectLibrary:
    """Own custom recipes and favourite IDs, with atomic disk writes."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or library_path()
        self.effects: dict[str, dict[str, Any]] = {}
        self.favorites: set[str] = set()
        self.load()

    def load(self) -> None:
        self.effects = {}
        self.favorites = set()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if payload.get("version") != 1 or not isinstance(payload.get("effects"), list):
                return
            for candidate in payload["effects"]:
                try:
                    spec = validate_effect_spec(candidate)
                except EffectSpecError:
                    continue
                if spec["id"].startswith("custom-"):
                    self.effects[spec["id"]] = spec
            favorites = payload.get("favorites", [])
            if isinstance(favorites, list):
                self.favorites = {item for item in favorites if isinstance(item, str)}
        except (OSError, TypeError, ValueError):
            return

    def save_effect(
        self,
        candidate: dict[str, Any],
        *,
        name: str | None = None,
        force_new: bool = False,
    ) -> dict[str, Any]:
        spec = validate_effect_spec(candidate)
        if name is not None:
            cleaned_name = " ".join(name.split())[:60]
            if not cleaned_name:
                raise ValueError("Give the effect a name.")
            spec["name"] = cleaned_name
        if force_new or spec["id"] not in self.effects:
            spec["id"] = self._available_id(spec["name"])
        self.effects[spec["id"]] = validate_effect_spec(spec)
        self._write()
        return self.effects[spec["id"]]

    def delete_effect(self, effect_id: str) -> None:
        if effect_id not in self.effects:
            raise KeyError("Only saved personal effects can be deleted.")
        del self.effects[effect_id]
        self.favorites.discard(effect_id)
        self._write()

    def set_favorite(self, effect_id: str, favorite: bool) -> None:
        if favorite:
            self.favorites.add(effect_id)
        else:
            self.favorites.discard(effect_id)
        self._write()

    def _available_id(self, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:32] or "effect"
        base = f"custom-{slug}"
        candidate = base
        suffix = 2
        while candidate in self.effects:
            candidate = f"{base[:43]}-{suffix}"
            suffix += 1
        return candidate

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "version": 1,
                    "effects": list(self.effects.values()),
                    "favorites": sorted(self.favorites),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)
