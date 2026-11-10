"""The top-bar weather strip says what the Time & Weather window says."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest
from dcs.cloud_presets import CLOUD_PRESETS
from dcs.weather import Weather as PydcsWeather, Wind

from game.timeofday import TimeOfDay
from game.utils import inches_hg, nautical_miles
from game.weather.atmosphericconditions import AtmosphericConditions
from game.weather.clouds import Clouds
from game.weather.fog import Fog


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    from qt_ui import uiconstants as CONST
    from qt_ui.liberation_theme import DEFAULT_THEME_INDEX, set_theme_index

    app = QApplication.instance() or QApplication([])
    # Not liberation_theme.init(): that writes the user's theme file.
    set_theme_index(DEFAULT_THEME_INDEX)
    CONST.load_icons()
    yield app


def test_strip_matches_the_window(qapp: Any) -> None:
    from qt_ui.widgets.conditions.QWeatherWidget import QWeatherWidget

    weather = SimpleNamespace(
        clouds=Clouds(
            base=5460,
            density=0,
            thickness=0,
            precipitation=PydcsWeather.Preceptions.None_,
            preset=CLOUD_PRESETS["Preset8"].value,
        ),
        fog=Fog(visibility=nautical_miles(1.5), thickness=250),
        dust=None,
        atmospheric=AtmosphericConditions(
            qnh=inches_hg(29.54), temperature_celsius=17.2, turbulence_per_10cm=8
        ),
        wind=SimpleNamespace(
            at_0m=Wind(212, 2), at_2000m=Wind(220, 10), at_8000m=Wind(278, 14)
        ),
    )
    conditions = SimpleNamespace(weather=weather, time_of_day=TimeOfDay.Day)
    strip = QWeatherWidget()
    strip.setCurrentTurn(1, conditions)  # type: ignore[arg-type]
    assert strip.forecastClouds.text() == (
        "Two Layer Scattered/Broken High Altitude, base 17,913 ft"
    )
    # A preset sky with fog used to read "No fog".
    assert strip.forecastRain.text() == "No rain · Fog 1.5 NM"
    assert strip.forecastAir.text() == "63°F · 29.54 inHg"
    assert [s.text() for s, _ in strip.windLabels] == ["4 kts", "19 kts", "27 kts"]
    strip.setCurrentTurn(1, conditions, auto_fog=True)  # type: ignore[arg-type]
    assert strip.forecastRain.text() == "No rain · Fog set by DCS"
