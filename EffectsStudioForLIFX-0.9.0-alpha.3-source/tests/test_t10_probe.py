import pytest

from effects_studio.t10_probe import (
    axis_length,
    countdown_colour,
    make_bands,
    make_marker,
    make_timer_frame,
    pad_set64,
)
from probe_t10 import (
    ProbeError,
    _configure_direct_discovery,
    _validate_write_args,
    build_parser,
)


def active_colors(colors):
    return [color for color in colors if color["brightness"] > 0]


def test_bands_fill_52_cell_matrix_and_pad_set64_payload():
    colors = make_bands(4, 13, axis="rows", brightness=0.7)

    assert len(colors) == 64
    assert len(active_colors(colors)) == 52
    assert {color["hue"] for color in active_colors(colors)} == {2, 42, 125}
    assert all(color["brightness"] == 0 for color in colors[52:])


def test_bands_can_run_along_columns():
    colors = make_bands(13, 4, axis="columns", brightness=0.7)

    first_row_hues = [color["hue"] for color in colors[:13]]
    assert first_row_hues[0] == 125
    assert 42 in first_row_hues
    assert first_row_hues[-1] == 2


def test_marker_has_bright_line_and_dim_field():
    colors = make_marker(4, 13, axis="rows", position=6, brightness=0.8)
    active = active_colors(colors)

    assert len(active) == 52
    assert sum(color["brightness"] == 0.8 for color in active) == 4
    assert max(color["brightness"] for color in active[: 6 * 4]) < 0.8


def test_timer_frame_crossfades_marker_and_changes_phase_color():
    halfway = make_timer_frame(
        5,
        11,
        axis="rows",
        progress=0.55,
        phase="warning",
        brightness=0.8,
    )

    active = active_colors(halfway[:55])
    assert {color["hue"] for color in active} == {42}
    assert max(color["brightness"] for color in active) < 0.8
    assert max(color["brightness"] for color in active) > 0.4


def test_expired_timer_frame_pulses_whole_matrix_evenly():
    colors = make_timer_frame(
        5,
        11,
        axis="rows",
        progress=1,
        phase="expired",
        brightness=0.2,
    )

    assert {color["brightness"] for color in colors[:55]} == {0.2}
    assert {color["hue"] for color in colors[:55]} == {2}


def test_axis_length_uses_selected_dimension():
    assert axis_length(4, 13, "rows") == 13
    assert axis_length(4, 13, "columns") == 4


def test_invalid_geometry_and_brightness_are_rejected():
    with pytest.raises(ValueError, match="64-cell"):
        make_bands(8, 9, axis="rows", brightness=0.7)
    with pytest.raises(ValueError, match="brightness"):
        make_marker(4, 13, axis="rows", position=0, brightness=0)
    with pytest.raises(ValueError, match="position"):
        make_marker(4, 13, axis="rows", position=13, brightness=0.7)


def test_pad_set64_rejects_too_many_colors():
    with pytest.raises(ValueError, match="at most 64"):
        pad_set64([{"brightness": 0}] * 65)


def test_write_commands_accept_direct_ip(monkeypatch):
    monkeypatch.delenv("HARDCODED_DISCOVERY", raising=False)
    args = build_parser().parse_args(["sweep", "d073d5000001", "--ip", "192.0.2.10"])

    _configure_direct_discovery(args.serial, args.ip)

    assert args.ip == "192.0.2.10"
    assert "192.0.2.10" in __import__("os").environ["HARDCODED_DISCOVERY"]


def test_invalid_direct_ip_is_rejected():
    args = build_parser().parse_args(["sweep", "d073d5000001", "--ip", "not-an-ip"])

    with pytest.raises(ProbeError, match="valid IPv4"):
        _validate_write_args(args)


def test_one_minute_timer_defaults_and_phases():
    args = build_parser().parse_args(["timer", "d073d5000001", "--ip", "192.0.2.10"])

    _validate_write_args(args)

    assert args.duration == 60
    assert countdown_colour(0) == (125, "green")
    for progress, expected_hue, expected_name in (
        (0.4, 125, "green"),
        (1 / 2, 60, "green to yellow"),
        (2 / 3, 42, "amber"),
        (5 / 6, 25, "amber to orange"),
        (0.95, 2, "red"),
        (1, 2, "red"),
    ):
        hue, name = countdown_colour(progress)
        assert hue == pytest.approx(expected_hue)
        assert name == expected_name


def test_countdown_colour_blends_around_stage_boundaries():
    before_first, _ = countdown_colour(0.48)
    after_first, _ = countdown_colour(0.52)
    before_second, _ = countdown_colour(0.81)
    after_second, _ = countdown_colour(0.86)

    assert 60 < before_first < 125
    assert 42 < after_first < 60
    assert 25 < before_second < 42
    assert 2 < after_second < 25


def test_countdown_colour_rejects_invalid_progress_and_transition():
    with pytest.raises(ValueError, match="progress"):
        countdown_colour(1.1)
    with pytest.raises(ValueError, match="transition_fraction"):
        countdown_colour(0.5, transition_fraction=0.5)
