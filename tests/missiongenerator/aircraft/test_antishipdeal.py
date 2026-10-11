"""The anti-ship deal: which ship each flight attacks first.

The fleet below is the one from the 2026-10-11 run that prompted it: a carrier
in its own group, and a cruiser, a destroyer and two frigates in the escort
group.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from dcs.task import AttackGroup, AttackUnit, WeaponType

from game.ato.flighttype import FlightType
from game.data.units import UnitClass
from game.missiongenerator.aircraft.antishipdeal import (
    ship_order_for,
    ships_for_flight,
    ships_in_line,
)
from game.missiongenerator.aircraft.waypoints.antishipingress import (
    AntiShipIngressBuilder,
)
from game.theater import NavalControlPoint, TheaterGroundObject
from game.transfers import MultiGroupTransport
from game.utils import meters

T0 = datetime(2026, 10, 11, 12, 0)


def _ship(name: str, unit_class: UnitClass, reach_m: float, alive: bool = True) -> Any:
    return SimpleNamespace(
        name=name,
        unit_name=f"0001 | {name}",
        is_ship=True,
        alive=alive,
        unit_type=SimpleNamespace(unit_class=unit_class),
        threat_range=lambda: meters(reach_m if alive else 0),
    )


def _fleet() -> dict[str, Any]:
    return {
        "kuznetsov": _ship("kuznetsov", UnitClass.AIRCRAFT_CARRIER, 12_000),
        "rezky": _ship("rezky", UnitClass.DESTROYER, 16_000),
        "pyotr": _ship("pyotr", UnitClass.CRUISER, 190_000),
        "grisha1": _ship("grisha1", UnitClass.FRIGATE, 16_000),
        "grisha2": _ship("grisha2", UnitClass.FRIGATE, 16_000),
    }


def _tgo(ships: list[Any]) -> Any:
    tgo = MagicMock(spec=TheaterGroundObject)
    tgo.units = ships
    return tgo


def _ato(*packages: tuple[Any, datetime, list[FlightType]]) -> list[list[Any]]:
    """Builds one coalition's ATO; returns the flights of each package."""
    coalition = SimpleNamespace(ato=SimpleNamespace(packages=[]))
    result = []
    for target, tot, flight_types in packages:
        package = SimpleNamespace(target=target, time_over_target=tot, flights=[])
        for flight_type in flight_types:
            package.flights.append(
                SimpleNamespace(
                    flight_type=flight_type, package=package, coalition=coalition
                )
            )
        coalition.ato.packages.append(package)
        result.append(package.flights)
    return result


def _first_ship(flight: Any) -> str:
    name: str = ships_for_flight(flight)[0].name
    return name


def test_line_is_top_sam_ship_then_carrier_then_rest_by_reach() -> None:
    fleet = _fleet()
    line = ships_in_line(_tgo(list(fleet.values())))
    assert [ship.name for ship in line] == [
        "pyotr",
        "kuznetsov",
        "rezky",
        "grisha1",
        "grisha2",
    ]


def test_line_leaves_out_a_sunk_ship() -> None:
    fleet = _fleet()
    fleet["pyotr"] = _ship("pyotr", UnitClass.CRUISER, 190_000, alive=False)
    line = ships_in_line(_tgo(list(fleet.values())))
    assert [ship.name for ship in line] == [
        "rezky",
        "kuznetsov",
        "grisha1",
        "grisha2",
    ]


def test_carrier_leads_when_no_escort_has_a_sam() -> None:
    carrier = _ship("carrier", UnitClass.AIRCRAFT_CARRIER, 25_000)
    oiler = _ship("oiler", UnitClass.LANDING_SHIP, 0)
    assert ships_in_line(_tgo([oiler, carrier])) == [carrier, oiler]


def test_two_flights_on_each_capital_ship_then_one_per_escort() -> None:
    line = ships_in_line(_tgo(list(_fleet().values())))
    dealt = [ship_order_for(nth, line)[0].name for nth in range(8)]
    assert dealt == [
        "pyotr",
        "pyotr",
        "kuznetsov",
        "kuznetsov",
        "rezky",
        "grisha1",
        "grisha2",
        "pyotr",
    ]


def test_fallback_runs_down_the_line_from_the_dealt_ship() -> None:
    line = ships_in_line(_tgo(list(_fleet().values())))
    assert [ship.name for ship in ship_order_for(4, line)] == [
        "rezky",
        "grisha1",
        "grisha2",
        "pyotr",
        "kuznetsov",
    ]


def test_auto_planner_package_keeps_both_flights_on_one_ship() -> None:
    """Two flights carry too few missiles to split (32 Harpoons for Hornets)."""
    tgo = _tgo(list(_fleet().values()))
    [flights] = _ato(
        (tgo, T0, [FlightType.ANTISHIP, FlightType.ESCORT, FlightType.ANTISHIP])
    )
    assert _first_ship(flights[0]) == "pyotr"
    assert _first_ship(flights[2]) == "pyotr"


def test_deal_runs_across_packages_in_time_over_target_order() -> None:
    """A package on the carrier's control point and one on its ship group are
    the same sea group, and the earlier package is dealt first."""
    tgo = _tgo(list(_fleet().values()))
    naval_cp = MagicMock(spec=NavalControlPoint)
    naval_cp.find_main_tgo.return_value = tgo
    hornets, bombers = _ato(
        (naval_cp, T0 + timedelta(minutes=10), [FlightType.ANTISHIP] * 3),
        (tgo, T0, [FlightType.ANTISHIP]),
    )
    assert _first_ship(bombers[0]) == "pyotr"
    assert [_first_ship(flight) for flight in hornets] == [
        "pyotr",
        "kuznetsov",
        "kuznetsov",
    ]


def test_another_sea_group_is_dealt_on_its_own() -> None:
    tgo = _tgo(list(_fleet().values()))
    other = _tgo([_ship("corvette", UnitClass.BOAT, 2_000)])
    [first], [second] = _ato(
        (other, T0, [FlightType.ANTISHIP]),
        (tgo, T0 + timedelta(minutes=5), [FlightType.ANTISHIP]),
    )
    assert _first_ship(first) == "corvette"
    assert _first_ship(second) == "pyotr"


def test_cargo_ship_is_not_dealt() -> None:
    [[flight]] = _ato((MagicMock(spec=MultiGroupTransport), T0, [FlightType.ANTISHIP]))
    assert ships_for_flight(flight) == []


def _builder(flight: Any, miz_groups: dict[str, Any]) -> tuple[Any, Any]:
    builder: Any = object.__new__(AntiShipIngressBuilder)
    builder.register_special_ingress_points = MagicMock()
    builder.package = flight.package
    builder.flight = flight
    builder.mission = MagicMock()
    builder.mission.find_group.side_effect = miz_groups.get
    builder.mission_data = SimpleNamespace(
        renamed_units={"0001 | kuznetsov": "Admiral Kuznetsov"}
    )
    waypoint = MagicMock()
    waypoint.tasks = []
    return builder, waypoint


def test_ingress_tasks_each_ship_before_the_group_fallback() -> None:
    fleet = _fleet()
    tgo = _tgo(list(fleet.values()))
    tgo.groups = [
        SimpleNamespace(group_name="carrier"),
        SimpleNamespace(group_name="escort"),
    ]
    # The third flight is dealt the carrier, which the generator renamed.
    [flights] = _ato((tgo, T0, [FlightType.ANTISHIP] * 3))
    miz_groups = {
        "carrier": SimpleNamespace(
            id=63, units=[SimpleNamespace(name="Admiral Kuznetsov", id=209)]
        ),
        "escort": SimpleNamespace(
            id=64,
            units=[
                SimpleNamespace(name="0001 | rezky", id=212),
                SimpleNamespace(name="0001 | pyotr", id=210),
                SimpleNamespace(name="0001 | grisha1", id=211),
                SimpleNamespace(name="0001 | grisha2", id=213),
            ],
        ),
    }
    builder, waypoint = _builder(flights[2], miz_groups)

    builder.add_tasks(waypoint)

    attacks = [t for t in waypoint.tasks if isinstance(t, (AttackUnit, AttackGroup))]
    unit_tasks = [t for t in attacks if isinstance(t, AttackUnit)]
    # Every per-ship task comes before the first group task.
    assert attacks[: len(unit_tasks)] == unit_tasks
    assert len(attacks) > len(unit_tasks)

    with_missiles = [
        t for t in unit_tasks if t.params["weaponType"] == WeaponType.Antiship.value
    ]
    assert [t.params["unitId"] for t in with_missiles] == [209, 212, 211, 213, 210]
    assert all(t.params["expend"] == "All" for t in unit_tasks)
    assert all(t.params["groupAttack"] for t in unit_tasks)
