"""Pure frame generation and Photons helpers for the LIFX Tube probe."""

from __future__ import annotations

from collections.abc import Iterable
from itertools import pairwise
from typing import Literal

type Axis = Literal["rows", "columns"]
type Color = dict[str, float | int]
type TimerPhase = Literal["normal", "warning", "critical", "expired"]

TUBE_PRODUCT_IDS = {217, 218}
MAX_SET64_COLORS = 64
KELVIN = 3500
DEFAULT_TRANSITION_FRACTION = 0.10


class ProbeError(RuntimeError):
    """A problem that can be explained cleanly to the person running the probe."""


def make_color(hue: float, saturation: float, brightness: float) -> Color:
    return {
        "hue": hue,
        "saturation": saturation,
        "brightness": brightness,
        "kelvin": KELVIN,
    }


def make_bands(width: int, height: int, *, axis: Axis, brightness: float) -> list[Color]:
    """Make green, amber, and red regions along one matrix axis."""

    _validate_geometry(width, height)
    _validate_brightness(brightness)
    axis_length = height if axis == "rows" else width
    bands = _band_indexes(axis_length)

    colors: list[Color] = []
    for y in range(height):
        for x in range(width):
            position = y if axis == "rows" else x
            band = bands[position]
            if band == "green":
                colors.append(make_color(125, 0.92, brightness))
            elif band == "amber":
                colors.append(make_color(42, 0.96, brightness))
            else:
                colors.append(make_color(2, 0.96, brightness))
    return pad_set64(colors)


def make_marker(
    width: int,
    height: int,
    *,
    axis: Axis,
    position: int,
    brightness: float,
) -> list[Color]:
    """Make the planned green timer field with one bright progress line."""

    _validate_geometry(width, height)
    _validate_brightness(brightness)
    axis_length = height if axis == "rows" else width
    if not 0 <= position < axis_length:
        raise ValueError(f"position must be between 0 and {axis_length - 1}")

    progress = position / max(1, axis_length - 1)
    return make_timer_frame(
        width,
        height,
        axis=axis,
        progress=progress,
        phase="normal",
        brightness=brightness,
    )


def make_timer_frame(
    width: int,
    height: int,
    *,
    axis: Axis,
    progress: float,
    phase: TimerPhase,
    brightness: float,
    hue_override: float | None = None,
) -> list[Color]:
    """Make a phase-coloured field with a fractional descending marker."""

    _validate_geometry(width, height)
    _validate_brightness(brightness)
    if not 0 <= progress <= 1:
        raise ValueError("progress must be between 0 and 1")

    hue = (
        {"normal": 125, "warning": 42, "critical": 2, "expired": 2}[phase]
        if hue_override is None
        else hue_override
    )
    length = axis_length(width, height, axis)
    marker_position = progress * (length - 1)

    colors: list[Color] = []
    for y in range(height):
        for x in range(width):
            cell_position = y if axis == "rows" else x
            if phase == "expired":
                colors.append(make_color(hue, 0.96, brightness))
                continue

            marker_weight = max(0.0, 1.0 - abs(cell_position - marker_position))
            base_brightness = min(brightness, 0.14)
            cell_brightness = base_brightness + (brightness - base_brightness) * marker_weight
            saturation = 0.92 - (0.37 * marker_weight)
            colors.append(make_color(hue, saturation, cell_brightness))
    return pad_set64(colors)


def countdown_colour(
    progress: float,
    *,
    transition_fraction: float = DEFAULT_TRANSITION_FRACTION,
) -> tuple[float, str]:
    """Return a smooth 1/2 green, 1/3 amber, 1/6 red colour schedule.

    Transitions are centred on the one-half and five-sixths boundaries. Yellow
    and orange are explicit midpoint colours, rather than incidental RGB mixes.
    """

    if not 0 <= progress <= 1:
        raise ValueError("progress must be between 0 and 1")
    if not 0 < transition_fraction < 1 / 3:
        raise ValueError("transition_fraction must be greater than 0 and less than one third")

    half_transition = transition_fraction / 2
    stops = (
        (0.0, 125.0, "green"),
        (1 / 2 - half_transition, 125.0, "green"),
        (1 / 2, 60.0, "yellow"),
        (1 / 2 + half_transition, 42.0, "amber"),
        (5 / 6 - half_transition, 42.0, "amber"),
        (5 / 6, 25.0, "orange"),
        (5 / 6 + half_transition, 2.0, "red"),
        (1.0, 2.0, "red"),
    )

    for left, right in pairwise(stops):
        left_progress, left_hue, left_name = left
        right_progress, right_hue, right_name = right
        if progress <= right_progress:
            width = right_progress - left_progress
            amount = 0.0 if width == 0 else (progress - left_progress) / width
            hue = left_hue + (right_hue - left_hue) * amount
            name = left_name if left_name == right_name else f"{left_name} to {right_name}"
            return hue, name

    return 2.0, "red"


def pad_set64(colors: Iterable[Color]) -> list[Color]:
    """Pad an active matrix to the fixed 64-value Set64 payload."""

    result = list(colors)
    if len(result) > MAX_SET64_COLORS:
        raise ValueError("Set64 supports at most 64 cells")
    result.extend(make_color(0, 0, 0) for _ in range(MAX_SET64_COLORS - len(result)))
    return result


def axis_length(width: int, height: int, axis: Axis) -> int:
    _validate_geometry(width, height)
    return height if axis == "rows" else width


def _band_indexes(length: int) -> list[str]:
    if length < 3:
        raise ValueError("The selected axis needs at least three cells for three bands")

    green_end = max(1, round(length * 0.55))
    amber_end = max(green_end + 1, round(length * 0.80))
    amber_end = min(length - 1, amber_end)
    return [
        "green" if index < green_end else "amber" if index < amber_end else "red"
        for index in range(length)
    ]


def _validate_geometry(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ValueError("Matrix dimensions must be positive")
    if width * height > MAX_SET64_COLORS:
        raise ValueError(f"Matrix {width}x{height} exceeds a 64-cell Set64 payload")


def _validate_brightness(brightness: float) -> None:
    if not 0 < brightness <= 1:
        raise ValueError("brightness must be greater than 0 and no more than 1")
