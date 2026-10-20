"""The Time & Weather window's weather column is built from a Weather.

Randomize weather rebuilds the column from a rolled Weather, so the column has
to show that object's type, clouds and wind rather than the turn's.
"""

from __future__ import annotations

import datetime
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any, Iterator

import pytest

from game.theater.seasonalconditions import (
    Season,
    SeasonalConditions,
    WeatherTypeChances,
)
from game.timeofday import TimeOfDay
from game.utils import mps
from game.weather.weather import ClearSkies, Cloudy, Raining, Thunderstorm


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _seasonal() -> SeasonalConditions:
    chances = WeatherTypeChances(
        thunderstorm=1.0, raining=1.0, cloudy=1.0, clear_skies=1.0
    )
    return SeasonalConditions(
        summer_avg_pressure=30.0,
        winter_avg_pressure=30.0,
        summer_avg_temperature=25.0,
        winter_avg_temperature=5.0,
        temperature_day_night_difference=10.0,
        high_avg_yearly_turbulence_per_10cm=1.0,
        low_avg_yearly_turbulence_per_10cm=0.1,
        solar_noon_turbulence_per_10cm=0.5,
        midnight_turbulence_per_10cm=0.1,
        weather_type_chances={season: chances for season in Season},
    )


@pytest.mark.parametrize(
    "weather_type, label",
    [
        (ClearSkies, "Clear"),
        (Cloudy, "Clouds"),
        (Raining, "Rain"),
        (Thunderstorm, "Thunderstorm"),
    ],
)
def test_column_shows_the_weather_it_was_given(
    qapp: Any, weather_type: Any, label: str
) -> None:
    from qt_ui.widgets.conditions.QWeatherAdjustmentWidget import (
        QWeatherAdjustmentWidget,
    )

    weather = weather_type(_seasonal(), datetime.date(2020, 6, 15), TimeOfDay.Day)
    w = QWeatherAdjustmentWidget(weather)
    assert w.type_selector.currentText() == label
    assert w.type_selector.currentData() is weather_type
    assert w.wind_gl_speed.value() == round(mps(weather.wind.at_0m.speed).knots)
    assert w.wind_fl26_dir.value() == (weather.wind.at_8000m.direction or 0)


def _dialog(monkeypatch: Any) -> Any:
    from types import SimpleNamespace

    from game.theater.daytimemap import DaytimeMap
    from game.weather.conditions import Conditions
    from qt_ui.widgets import QConditionsDialog as dialog_module
    from qt_ui.widgets.conditions import QTimeAdjustmentWidget as time_module

    monkeypatch.setattr(time_module, "theater_middle", lambda _theater: None)
    monkeypatch.setattr(
        time_module.QTimeAdjustmentWidget, "update_daylight", lambda _self: None
    )
    seasonal = _seasonal()
    start = datetime.datetime(2020, 6, 15, 12)
    theater = SimpleNamespace(
        seasonal_conditions=seasonal,
        timezone=datetime.timezone.utc,
        daytime_map=DaytimeMap(
            dawn=(datetime.time(6), datetime.time(8)),
            day=(datetime.time(8), datetime.time(16)),
            dusk=(datetime.time(16), datetime.time(20)),
            night=(datetime.time(20), datetime.time(23)),
        ),
    )
    game = SimpleNamespace(
        theater=theater, settings=SimpleNamespace(use_auto_fog=False)
    )
    sim_controller = SimpleNamespace(
        current_time_in_sim=start, game_loop=SimpleNamespace(game=game)
    )
    conditions = Conditions(
        time_of_day=TimeOfDay.Day,
        start_time=start,
        weather=Cloudy(seasonal, start.date(), TimeOfDay.Day),
    )
    return dialog_module.QConditionsDialog(
        SimpleNamespace(sim_controller=sim_controller),  # type: ignore[arg-type]
        SimpleNamespace(conditions=conditions),  # type: ignore[arg-type]
    )


def test_randomize_refills_the_form_and_leaves_the_turn(
    qapp: Any, monkeypatch: Any
) -> None:
    dialog = _dialog(monkeypatch)
    turn_weather = dialog.weather.conditions.weather
    for _ in range(5):
        old_column = dialog.weather_adjuster
        old_air = dialog.atmosphere_adjuster
        dialog.randomize_weather()
        assert dialog.base_weather is not turn_weather
        assert dialog.weather_adjuster is not old_column
        assert dialog.atmosphere_adjuster is not old_air
        assert dialog.weather_column.indexOf(dialog.weather_adjuster) >= 0
        assert dialog.weather_column.indexOf(old_column) < 0
        assert dialog.columns.indexOf(dialog.atmosphere_adjuster) >= 0
        assert dialog.columns.indexOf(old_air) < 0
        assert dialog.weather_adjuster.type_selector.currentData() is type(
            dialog.base_weather
        )
        assert dialog.weather_adjuster.wind_gl_speed.value() == round(
            mps(dialog.base_weather.wind.at_0m.speed).knots
        )
    assert dialog.weather.conditions.weather is turn_weather


def test_the_window_has_no_reroll_turn_button(qapp: Any, monkeypatch: Any) -> None:
    from PySide6.QtWidgets import QPushButton

    dialog = _dialog(monkeypatch)
    labels = {b.text() for b in dialog.findChildren(QPushButton)}
    assert labels == {"Randomize weather", "REJECT", "ACCEPT"}
