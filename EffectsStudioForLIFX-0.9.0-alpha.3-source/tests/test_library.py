import json

import pytest

from effects_studio.effect_spec import EffectSpecError
from effects_studio.library import EffectLibrary
from effects_studio.presets import PRESETS


def test_personal_effect_survives_a_restart(tmp_path):
    path = tmp_path / "effects.json"
    library = EffectLibrary(path)
    saved = library.save_effect(PRESETS["aurora"], name="My Aurora")
    library.set_favorite(saved["id"], True)

    reloaded = EffectLibrary(path)

    assert reloaded.effects[saved["id"]]["name"] == "My Aurora"
    assert saved["id"] in reloaded.favorites


def test_duplicate_gets_a_distinct_stable_id(tmp_path):
    library = EffectLibrary(tmp_path / "effects.json")
    first = library.save_effect(PRESETS["ocean"], name="Sea")
    second = library.save_effect(first, name="Sea", force_new=True)

    assert first["id"] == "custom-sea"
    assert second["id"] == "custom-sea-2"


def test_only_personal_effects_can_be_deleted(tmp_path):
    library = EffectLibrary(tmp_path / "effects.json")

    with pytest.raises(KeyError, match="personal"):
        library.delete_effect("aurora")


def test_corrupt_or_untrusted_entries_do_not_break_startup(tmp_path):
    path = tmp_path / "effects.json"
    path.write_text(
        json.dumps({"version": 1, "effects": [{"id": "custom-bad", "python": "run()"}]}),
        encoding="utf-8",
    )

    assert EffectLibrary(path).effects == {}


def test_unsafe_recipe_is_rejected_before_writing(tmp_path):
    library = EffectLibrary(tmp_path / "effects.json")
    unsafe = {**PRESETS["aurora"], "command": "format c:"}

    with pytest.raises(EffectSpecError):
        library.save_effect(unsafe)
    assert not library.path.exists()
