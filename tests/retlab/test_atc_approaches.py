"""Voice ATC step 3 (§119): the plates' approaches, the generated ILS and the weather gate."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dcs.terrain import Falklands, Kola, Nevada
from dcs.weather import Weather as PydcsWeather

from game.retlab.atc_approaches import (
    _plate_file,
    charted_approaches,
    field_approaches,
    generated_approaches,
    instrument_weather,
)
from game.runways import RunwayData
from game.utils import Heading, meters
from game.weather.clouds import Clouds
from game.weather.fog import Fog


@pytest.mark.parametrize("terrain_type", [Kola, Falklands, Nevada])
def test_every_plate_names_a_dcs_airport_and_runway(terrain_type: Any) -> None:
    terrain = terrain_type()
    plates = _plate_file(terrain.name)
    assert plates, terrain.name
    for name, entries in plates.items():
        airport = terrain.airports[name]
        approaches = charted_approaches(terrain.name, airport, [])
        assert len(approaches) == len(entries), name
        for approach in approaches:
            assert approach.kind in ("ILS", "TACAN", "LOC")
            # The final fix is lower than, or level with, the start.
            assert approach.final.feet <= approach.start.feet, (name, approach)
            assert approach.start.label and approach.final.label


def test_bodo_25_is_the_ils_via_takup() -> None:
    terrain = Kola()
    approaches = charted_approaches(terrain.name, terrain.airports["Bodo"], [])
    ils = next(a for a in approaches if a.runway == "25")
    assert (ils.kind, ils.nav, ils.ident) == ("ILS", "108.70", "BD")
    assert ils.clearance() == (
        "cleared ILS runway 25, via TAKUP, maintain 3,500 until established, at 8 DME"
    )
    assert ils.card_line() == (
        "ILS 25 (108.70 BD): via TAKUP 3,500, Tower at 8 DME 3,000"
    )


def _runway(name: str, ils: bool) -> RunwayData:
    from game.radio.radios import MHz

    return RunwayData(
        "Field",
        Heading.from_degrees(250),
        name,
        ils=MHz(110, 300) if ils else None,
        ils_callsign="IXX" if ils else None,
    )


def test_an_ils_end_without_a_plate_gets_a_generated_straight_in() -> None:
    airport = SimpleNamespace(name="Nowhere", runways=[])
    runways = [_runway("25", True), _runway("07", False)]
    approaches = generated_approaches(airport, runways, 230)  # type: ignore[arg-type]
    assert len(approaches) == 1
    ils = approaches[0]
    assert ils.generated and ils.runway == "25"
    assert (ils.start.dme, ils.start.feet) == (12, 3300)
    assert (ils.final.dme, ils.final.feet) == (5, 1900)
    assert ils.clearance().startswith(
        "cleared ILS runway 25, proceed to a 12 mile final, maintain 3,300"
    )


def test_a_plate_wins_over_the_generated_ils_on_its_runway() -> None:
    terrain = Kola()
    airport = terrain.airports["Bodo"]
    runways = [_runway("25", True), _runway("07", True)]
    approaches = field_approaches(terrain.name, airport, runways, 40)
    assert [a.generated for a in approaches] == [False, False]
    # The ILS takes the frequency DCS transmits, not the plate's.
    assert {a.nav for a in approaches} == {"110.30"}


def _weather(clouds: Any = None, fog: Any = None) -> Any:
    return SimpleNamespace(clouds=clouds, fog=fog)


def test_low_cloud_or_fog_calls_for_an_instrument_approach() -> None:
    def overcast(base_ft: int) -> Clouds:
        return Clouds(
            base=int(meters(base_ft / 3.28084).meters),
            density=9,
            thickness=500,
            precipitation=PydcsWeather.Preceptions.None_,
        )

    assert instrument_weather(_weather(overcast(2500)), 0)
    assert not instrument_weather(_weather(overcast(6000)), 0)
    # 3,000 ft above a field at 4,000 ft is 7,000 MSL.
    assert instrument_weather(_weather(overcast(6000)), 4000)
    assert not instrument_weather(_weather(), 0)
    fog = Fog(visibility=meters(3000), thickness=100)
    assert instrument_weather(_weather(fog=fog), 0)


def test_a_parallel_runway_keeps_its_own_side() -> None:
    terrain = Nevada()
    approaches = charted_approaches(terrain.name, terrain.airports["Nellis"], [])
    assert {a.runway for a in approaches} == {"21L", "03R"}
