import pytest

from effects_studio.presets import PRESETS
from effects_studio.renderer import render_effect


@pytest.mark.parametrize("preset", PRESETS.values(), ids=PRESETS.keys())
def test_presets_render_a_5_by_11_tube_and_pad_the_protocol_packet(preset):
    frame = render_effect(preset, 5, 11, brightness=0.72, now=12.5)

    assert len(frame) == 64
    assert all(0 < cell["brightness"] <= 0.72 for cell in frame[:55])
    assert all(cell["brightness"] == 0 for cell in frame[55:])


def test_animated_effect_changes_over_time():
    early = render_effect(PRESETS["aurora"], 5, 11, now=1)
    later = render_effect(PRESETS["aurora"], 5, 11, now=2)

    assert early != later


def test_brightness_is_a_hard_ceiling():
    frame = render_effect(PRESETS["candy"], 5, 11, brightness=0.25, now=3)

    assert max(cell["brightness"] for cell in frame) <= 0.25


@pytest.mark.parametrize(
    "preset_id",
    ("rainbow_parade", "moon_breath", "sonar", "comet_chase"),
)
def test_low_resolution_primitives_are_animated(preset_id):
    first = render_effect(PRESETS[preset_id], 5, 11, now=2)
    second = render_effect(PRESETS[preset_id], 5, 11, now=3)

    assert first[:55] != second[:55]
    assert len({round(float(cell["brightness"]), 3) for cell in first[:55]}) > 1


def test_multistop_gradient_uses_several_interpolated_hues():
    frame = render_effect(PRESETS["rainbow_parade"], 5, 11, now=0)

    hues = {round(float(cell["hue"])) for cell in frame[:55]}
    assert len(hues) >= 8


def test_sequence_crossfades_smoothly_between_scenes():
    red = {"hue": 0, "saturation": 1, "brightness": 0.1}
    blue = {"hue": 240, "saturation": 1, "brightness": 0.1}
    sequence = {
        "schema_version": 2,
        "id": "crossfade-test",
        "name": "Crossfade Test",
        "description": "Two static scenes for a transition test.",
        "speed": 1,
        "duration": 2,
        "transition": 1,
        "background": red,
        "layers": [
            {
                "type": "pulse",
                "color": red,
                "speed": 0,
                "frequency": 1,
                "phase": 0.25,
                "intensity": 1,
                "seed": 1,
            }
        ],
        "scenes": [
            {
                "name": "Blue",
                "duration": 2,
                "transition": 1,
                "background": blue,
                "layers": [
                    {
                        "type": "pulse",
                        "color": blue,
                        "speed": 0,
                        "frequency": 1,
                        "phase": 0.25,
                        "intensity": 1,
                        "seed": 2,
                    }
                ],
            }
        ],
    }

    red_frame = render_effect(sequence, 5, 11, now=1)
    middle_frame = render_effect(sequence, 5, 11, now=1.5)
    blue_frame = render_effect(sequence, 5, 11, now=2)

    assert red_frame[0]["hue"] == pytest.approx(0)
    assert middle_frame[0]["hue"] == pytest.approx(300)
    assert blue_frame[0]["hue"] == pytest.approx(240)


def test_oscillating_hue_stays_inside_its_requested_colour_family():
    blue = {"hue": 205, "saturation": 0.9, "brightness": 0.4}
    ocean = {
        "schema_version": 2,
        "id": "bounded-ocean",
        "name": "Bounded Ocean",
        "description": "Blue waves with bounded colour drift.",
        "speed": 1,
        "background": {**blue, "brightness": 0.1},
        "layers": [
            {
                "type": "pulse",
                "color": blue,
                "speed": 0,
                "frequency": 1,
                "phase": 0.25,
                "intensity": 1,
                "seed": 1,
                "hue_motion": {
                    "mode": "oscillate",
                    "amplitude": 18,
                    "speed": 0.2,
                    "phase": 0,
                },
            }
        ],
    }

    hues = {
        round(float(cell["hue"]), 4)
        for now in (0, 0.5, 1, 2, 3, 4, 5)
        for cell in render_effect(ocean, 5, 11, now=now)[:55]
    }

    assert min(hues) >= 205 - 18
    assert max(hues) <= 205 + 18
