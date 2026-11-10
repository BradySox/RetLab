"""Weather wording shared by the top-bar strip and the Time & Weather window.

Both views say the same thing in the same words and imperial units.
"""

from __future__ import annotations

from collections import Counter
from functools import cache
from typing import Any, Optional

from dcs.cloud_presets import CLOUD_PRESETS
from dcs.weather import CloudPreset

from game.utils import meters
from game.weather.atmosphericconditions import AtmosphericConditions

# The three DCS wind levels (0, 2,000 and 8,000 m), rounded to the nearest 100 ft.
WIND_LEVEL_LABELS = ("Ground", "6,600 ft", "26,200 ft")


def _description(preset: CloudPreset) -> str:
    # "08 ##Two Layer Scattered/Broken High Altitude \nMETAR:..." -> the words.
    first = preset.description.splitlines()[0]
    words = first.split("##", 1)[-1].split()
    return " ".join(w[:1].upper() + w[1:] for w in words)


@cache
def _shared_descriptions() -> frozenset[str]:
    counts = Counter(_description(p.value).lower() for p in CLOUD_PRESETS.values())
    return frozenset(d for d, n in counts.items() if n > 1)


def cloud_preset_label(preset: CloudPreset) -> str:
    """DCS's long description; the short name is added where two presets share it."""
    description = _description(preset)
    if description.lower() in _shared_descriptions():
        return f"{description} ({preset.ui_name})"
    return description


def custom_cloud_label(density: int) -> str:
    if not density:
        return "Clear"
    if density < 3:
        return "Partly Cloudy"
    if density < 5:
        return "Mostly Cloudy"
    return "Totally Cloudy"


def feet_text(altitude_m: float) -> str:
    """An altitude in feet, as the window's Cloud Base box shows it."""
    return f"{round(meters(altitude_m).feet):,} ft"


def clouds_text(clouds: Any) -> str:
    """Cloud cover and base, as in "Two Layer Scattered, base 17,913 ft"."""
    if clouds is None:
        return "Clear"
    if clouds.preset is not None:
        label = cloud_preset_label(clouds.preset)
    else:
        label = custom_cloud_label(clouds.density)
        if not clouds.density:
            return label
    return f"{label}, base {feet_text(clouds.base)}"


def visibility_text(fog: Any, dust: Any, auto_fog: bool) -> str:
    if auto_fog:
        return "Fog set by DCS"
    if fog is not None:
        return f"Fog {fog.visibility.nautical_miles:.1f} NM"
    if dust is not None:
        return f"Dust storm {dust.visibility.nautical_miles:.1f} NM"
    return "No fog"


def air_text(atmospheric: Optional[AtmosphericConditions]) -> str:
    """Temperature and altimeter, as in "63°F · 29.54 inHg"."""
    if atmospheric is None:
        return ""
    fahrenheit = round(atmospheric.temperature_celsius * 9 / 5 + 32)
    return f"{fahrenheit}°F · {atmospheric.qnh.inches_hg:.2f} inHg"


def wind_text(speed_kts: float, direction: int) -> tuple[str, str]:
    # Rounded, as the window's Speed (kts) box rounds it.
    return f"{round(speed_kts)} kts", f"{direction:03d}°"
