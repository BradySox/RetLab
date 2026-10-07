from __future__ import annotations

from typing import Optional, cast
from unittest.mock import MagicMock

from dcs.country import Country

from game.ato.flight import Flight
from game.ato.flighttype import FlightType
from game.naming import NameGenerator


def _fake_flight(
    flight_type: FlightType, custom_name: Optional[str], target_name: str
) -> Flight:
    flight = MagicMock()
    flight.custom_name = custom_name
    flight.flight_type = flight_type
    flight.unit_type.variant_id = "F-16CM Fighting Falcon (Block 50)"
    flight.unit_type.dcs_id = "F-16C_50"
    flight.package.target.name = target_name
    return cast(Flight, flight)


def _fake_country(country_id: int) -> Country:
    country = MagicMock()
    country.id = country_id
    return cast(Country, country)


def test_next_aircraft_name_uses_target_and_task() -> None:
    NameGenerator.reset_numbers()
    name = NameGenerator.next_aircraft_name(
        _fake_country(5), _fake_flight(FlightType.STRIKE, None, "Tiyas")
    )
    assert name == "Tiyas Strike|1|F-16C_50|"


def test_next_aircraft_name_custom_name_keeps_task() -> None:
    # A custom name must still carry the task type so the Moose QRA filter (and
    # debrief attribution) can classify the flight from its group name. Before
    # the fix, a custom name dropped the task entirely.
    NameGenerator.reset_numbers()
    name = NameGenerator.next_aircraft_name(
        _fake_country(6), _fake_flight(FlightType.BAI, "Alpha", "Tiyas")
    )
    assert name == "Alpha BAI|1|F-16C_50|"


def test_next_aircraft_name_has_no_moose_alias_separator() -> None:
    # MOOSE cuts a group name at "#"; the pydcs " Pilot #N" suffix is the only one.
    NameGenerator.reset_numbers()
    name = NameGenerator.next_aircraft_name(
        _fake_country(2), _fake_flight(FlightType.DEAD, None, "MANTIS")
    )
    assert "#" not in name
