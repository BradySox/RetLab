"""The Time & Weather window's air and visibility column.

ACCEPT must hand back the turn's own values for anything left alone; it used to
re-roll temperature, altimeter, turbulence and fog every time.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from game.utils import inches_hg, nautical_miles
from game.weather.atmosphericconditions import AtmosphericConditions
from game.weather.dust import Dust
from game.weather.fog import Fog


@pytest.fixture(scope="module")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _weather(fog: Fog | None = None, dust: Dust | None = None) -> Any:
    return SimpleNamespace(
        atmospheric=AtmosphericConditions(
            qnh=inches_hg(29.874), temperature_celsius=27.3, turbulence_per_10cm=11.6
        ),
        fog=fog,
        dust=dust,
    )


def _widget(weather: Any, auto_fog: bool) -> Any:
    from qt_ui.widgets.conditions.QAtmosphereAdjustmentWidget import (
        QAtmosphereAdjustmentWidget,
    )

    return QAtmosphereAdjustmentWidget(weather, auto_fog)


def test_untouched_controls_keep_the_turn_exactly(qapp: Any) -> None:
    fog = Fog(visibility=nautical_miles(1.7), thickness=310)
    weather = _weather(fog=fog)
    w = _widget(weather, auto_fog=False)
    assert w.atmospheric(weather.atmospheric) == weather.atmospheric
    assert w.fog(fog) is fog
    assert w.dust(None) is None


def test_edits_land_in_the_turn_units(qapp: Any) -> None:
    weather = _weather()
    w = _widget(weather, auto_fog=False)
    assert w.temperature.value() == 81 and w.turbulence.currentText() == "Light"
    w.temperature.setValue(50)
    w.altimeter.setValue(30.12)
    w.turbulence.setCurrentText("Heavy")
    result = w.atmospheric(weather.atmospheric)
    assert result.temperature_celsius == 10.0
    assert round(result.qnh.inches_hg, 2) == 30.12
    assert result.turbulence_per_10cm == 40
    assert weather.atmospheric.temperature_celsius == 27.3


def test_fog_and_dust_are_exclusive(qapp: Any) -> None:
    w = _widget(_weather(), auto_fog=False)
    w.fog_enabled.setChecked(True)
    w.dust_enabled.setChecked(True)
    assert not w.fog_enabled.isChecked()
    assert w.fog(None) is None
    dust = w.dust(None)
    assert dust is not None and round(dust.visibility.nautical_miles, 1) == 1.0


def test_auto_fog_locks_fog_and_dust(qapp: Any) -> None:
    fog = Fog(visibility=nautical_miles(2.0), thickness=200)
    w = _widget(_weather(fog=fog), auto_fog=True)
    assert not w.fog_enabled.isEnabled() and not w.dust_enabled.isEnabled()
    assert w.fog(fog) is fog
