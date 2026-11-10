"""The top-bar strip and the Time & Weather window describe weather in one voice."""

from __future__ import annotations

from dcs.cloud_presets import CLOUD_PRESETS
from dcs.weather import Weather as PydcsWeather

from game.utils import inches_hg, nautical_miles
from game.weather.atmosphericconditions import AtmosphericConditions
from game.weather.clouds import Clouds
from game.weather.dust import Dust
from game.weather.fog import Fog
from game.weather.weathertext import (
    WIND_LEVEL_LABELS,
    air_text,
    cloud_preset_label,
    clouds_text,
    visibility_text,
    wind_text,
)


def test_preset_label_is_the_long_description() -> None:
    preset = CLOUD_PRESETS["Preset8"].value
    assert cloud_preset_label(preset) == "Two Layer Scattered/Broken High Altitude"


def test_every_preset_label_is_unique() -> None:
    labels = [cloud_preset_label(p.value) for p in CLOUD_PRESETS.values()]
    assert len(labels) == len(set(labels))
    assert "Three Layer Overcast (Overcast 4)" in labels


def test_clouds_text_gives_the_base_in_feet() -> None:
    clouds = Clouds(
        base=5460,
        density=0,
        thickness=0,
        precipitation=PydcsWeather.Preceptions.None_,
        preset=CLOUD_PRESETS["Preset8"].value,
    )
    assert clouds_text(clouds) == (
        "Two Layer Scattered/Broken High Altitude, base 17,913 ft"
    )
    assert clouds_text(None) == "Clear"


def test_visibility_text() -> None:
    fog = Fog(visibility=nautical_miles(1.5), thickness=250)
    dust = Dust(visibility=nautical_miles(1.0))
    assert visibility_text(None, None, auto_fog=False) == "No fog"
    assert visibility_text(fog, None, auto_fog=False) == "Fog 1.5 NM"
    assert visibility_text(None, dust, auto_fog=False) == "Dust storm 1.0 NM"
    assert visibility_text(fog, None, auto_fog=True) == "Fog set by DCS"


def test_air_and_wind_text() -> None:
    air = AtmosphericConditions(
        qnh=inches_hg(29.54), temperature_celsius=17.2, turbulence_per_10cm=8
    )
    assert air_text(air) == "63°F · 29.54 inHg"
    assert wind_text(19.6, 5) == ("20 kts", "005°")
    assert WIND_LEVEL_LABELS == ("Ground", "6,600 ft", "26,200 ft")
