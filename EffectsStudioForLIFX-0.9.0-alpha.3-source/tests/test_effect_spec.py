import pytest

from effects_studio.effect_spec import EffectSpecError, validate_effect_spec
from effects_studio.generator import draft_effect
from effects_studio.presets import PRESETS


@pytest.mark.parametrize("preset", PRESETS.values(), ids=PRESETS.keys())
def test_every_preset_is_a_valid_data_only_recipe(preset):
    validated = validate_effect_spec(preset)

    assert validated["id"] == preset["id"]
    assert validated["layers"]


def test_unknown_fields_are_rejected_instead_of_executed():
    unsafe = {**PRESETS["aurora"], "python": "open('surprise.txt', 'w')"}

    with pytest.raises(EffectSpecError, match="Unknown effect field"):
        validate_effect_spec(unsafe)


def test_offline_generator_is_deterministic_and_uses_keywords():
    first = draft_effect("a calm ocean with tiny stars")
    second = draft_effect("a calm ocean with tiny stars")

    assert first == second
    assert first["speed"] == 0.38
    assert first["background"]["hue"] == 218
    assert first["layers"][-1]["count"] == 9


def test_empty_description_is_rejected():
    with pytest.raises(ValueError, match="Describe"):
        draft_effect("   ")


@pytest.mark.parametrize(
    ("description", "expected_type"),
    (
        ("a rainbow party", "gradient"),
        ("turquoise sonar rings", "ripple"),
        ("a comet chase", "chase"),
        ("a sleepy breathing moon", "pulse"),
    ),
)
def test_description_generator_can_choose_new_primitives(description, expected_type):
    types = {layer["type"] for layer in draft_effect(description)["layers"]}

    assert expected_type in types


def test_description_with_then_builds_a_sequence():
    spec = draft_effect("a calm ocean then a warm fire then purple space")

    assert [scene["name"] for scene in spec["scenes"]] == ["A Warm Fire", "Purple Space"]
    assert spec["transition"] == 1.5


def test_palette_requires_two_colours():
    candidate = {
        **PRESETS["aurora"],
        "layers": [
            {**PRESETS["aurora"]["layers"][0], "palette": [PRESETS["aurora"]["background"]]}
        ],
    }

    with pytest.raises(EffectSpecError, match="between 2 and 8"):
        validate_effect_spec(candidate)


def test_transition_cannot_outlast_its_scene():
    candidate = {**PRESETS["storybook_sky"], "duration": 1, "transition": 2}

    with pytest.raises(EffectSpecError, match="longer"):
        validate_effect_spec(candidate)


def test_legacy_hue_shift_is_migrated_without_changing_its_rotation_rate():
    first_layer = {
        key: value
        for key, value in PRESETS["rainbow_parade"]["layers"][0].items()
        if key != "hue_motion"
    }
    legacy = {
        **PRESETS["rainbow_parade"],
        "schema_version": 1,
        "layers": [{**first_layer, "hue_shift": 42}],
    }

    validated = validate_effect_spec(legacy)

    motion = validated["layers"][0]["hue_motion"]
    assert motion == {"mode": "rotate", "amplitude": 0.0, "speed": 0.7, "phase": 0.0}
    assert "hue_shift" not in validated["layers"][0]
    assert validated["schema_version"] == 2


def test_new_colour_motion_rejects_ambiguous_legacy_field():
    candidate = {
        **PRESETS["aurora"],
        "layers": [
            {
                **PRESETS["aurora"]["layers"][0],
                "hue_shift": 10,
                "hue_motion": {
                    "mode": "oscillate",
                    "amplitude": 15,
                    "speed": 0.2,
                    "phase": 0,
                },
            }
        ],
    }

    with pytest.raises(EffectSpecError, match="both hue_motion and legacy hue_shift"):
        validate_effect_spec(candidate)
