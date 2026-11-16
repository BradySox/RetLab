"""The ground movement switch and per-turn distances (§131)."""

from __future__ import annotations

from typing import Any

METERS_PER_MILE = 1609.344


def enabled(settings: Any) -> bool:
    return getattr(settings, "ground_movement", False) is True


def distance_per_turn(settings: Any, *, on_road: bool) -> float:
    """Meters a ground convoy covers in one turn."""
    miles = (
        settings.ground_movement_road_miles
        if on_road
        else settings.ground_movement_off_road_miles
    )
    return float(max(1, miles)) * METERS_PER_MILE
