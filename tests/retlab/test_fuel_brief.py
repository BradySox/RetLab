"""Tests for the in-app fuel-plan readout (§46 UI surfacing).

The brief must tell the same story as the kneeboard ladder and the tanker
decision: same per-leg walk, tanker top-offs applied at REFUEL waypoints, the
walk ends at the landing point (divert/bullseye reference waypoints are not
flown legs), and external fuel counts the tanks on the loadout shown.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from dcs import Point
from dcs.terrain import Caucasus

from game import persistency
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.loadouts import Loadout
from game.data.weapons import Weapon
from game.dcs.aircrafttype import FuelConsumption
from game.retlab.fuel_brief import FuelBrief, fuel_brief_for, fuel_brief_text
from game.theater.player import Player
from game.utils import KG_TO_LBS

VIPER_TANK_370 = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"
TERRAIN = Caucasus()

_FUEL = FuelConsumption(taxi=200, climb=30.0, cruise=10.0, combat=16.0, min_safe=1500)
_INTERNAL_KG = 10000.0 / KG_TO_LBS  # 10,000 lbs internal


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # Weapon.with_clsid needs the weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16887)


def _wp(kind: FlightWaypointType = FlightWaypointType.NAV) -> Any:
    return SimpleNamespace(waypoint_type=kind)


def _at(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


def _tanker(aircraft_type: Any, start: Point, end: Point) -> Any:
    return SimpleNamespace(
        flight_type=FlightType.REFUELING,
        blue=Player.BLUE,
        unit_type=aircraft_type,
        flight_plan=SimpleNamespace(
            layout=SimpleNamespace(
                patrol_start=SimpleNamespace(position=start),
                patrol_end=SimpleNamespace(position=end),
            )
        ),
    )


def _ato_with(*tankers: Any) -> Any:
    return SimpleNamespace(
        ato=SimpleNamespace(packages=[SimpleNamespace(flights=list(tankers))])
    )


def _flight(
    waypoints: list[Any],
    *,
    per_leg: float = 1000.0,
    members: Optional[list[Any]] = None,
    measured: FuelConsumption | None = _FUEL,
    estimated: FuelConsumption | None = None,
    coalition: Any = None,
    can_refuel_from: Any = None,
) -> Any:
    return SimpleNamespace(
        unit_type=SimpleNamespace(
            fuel_consumption=measured,
            estimated_fuel_consumption=estimated,
            max_fuel=_INTERNAL_KG,
            can_refuel_from=can_refuel_from or (lambda tanker: True),
        ),
        fuel=_INTERNAL_KG,
        blue=Player.BLUE,
        coalition=coalition,
        iter_members=lambda: iter(members or ()),
        flight_plan=SimpleNamespace(
            waypoints=waypoints,
            fuel_consumption_between_points=lambda a, b, consumption=None: per_leg,
            ground_fuel_lbs=lambda consumption: consumption.taxi,
        ),
    )


def _tank_loadout(count: int) -> Loadout:
    tank = Weapon.with_clsid(VIPER_TANK_370)
    assert tank is not None
    return Loadout("Ferry", {n: tank for n in range(1, count + 1)}, date=None)


def test_burn_reserve_and_margin() -> None:
    # takeoff -> nav -> landing: two legs of 1000 plus 200 taxi.
    flight = _flight(
        [_wp(FlightWaypointType.TAKEOFF), _wp(), _wp(FlightWaypointType.LANDING_POINT)]
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.burn_lbs == 200 + 2000
    assert brief.reserve_lbs == 1500
    # 10000 - 200 taxi - 2000 legs - 1500 reserve.
    assert brief.margin_lbs == pytest.approx(10000 - 200 - 2000 - 1500)
    assert brief.refuel_passes == 0
    assert not brief.is_short


def test_refuel_waypoint_tops_off_and_counts_a_pass() -> None:
    flight = _flight(
        [
            _wp(FlightWaypointType.TAKEOFF),
            _wp(FlightWaypointType.REFUEL),
            _wp(FlightWaypointType.LANDING_POINT),
        ]
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.refuel_passes == 1
    # Topped off at the tanker, one leg home: 10000 - 1000 - 1500 reserve.
    assert brief.margin_lbs == pytest.approx(10000 - 1000 - 1500)


def test_a_pass_no_tanker_can_fly_is_not_counted() -> None:
    # The planner adds the REFUEL waypoint whenever the coalition owns a tanker
    # squadron; generation drops it when no tanker on the ATO can serve the jet
    # (none flying, or a probe-only tanker for a boom receiver). The brief has to
    # walk the same route as the kneeboard, so no pass and no top-off here.
    boom_only = object()
    probe_tanker = _tanker(boom_only, _at(0, 0), _at(0, 10000))
    refuel = _wp(FlightWaypointType.REFUEL)
    refuel.position = _at(0, 5000)
    flight = _flight(
        [
            _wp(FlightWaypointType.TAKEOFF),
            refuel,
            _wp(FlightWaypointType.LANDING_POINT),
        ],
        coalition=_ato_with(probe_tanker),
        can_refuel_from=lambda tanker: tanker is not boom_only,
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.refuel_passes == 0
    assert brief.margin_lbs == pytest.approx(brief.dry_margin_lbs)


def test_a_pass_is_walked_to_the_tanker_orbit() -> None:
    # A tanker that can serve the jet moves the waypoint onto its orbit, the way
    # generation does, so the legs are burned to where the tanker really is.
    tanker = _tanker(object(), _at(0, 0), _at(0, 10000))
    refuel = _wp(FlightWaypointType.REFUEL)
    refuel.position = _at(3000, 5000)  # 3 km abeam the orbit's midpoint
    walked: list[Any] = []

    def leg(a: Any, b: Any, consumption: Any = None) -> float:
        walked.append(b)
        return 1000.0

    flight = _flight(
        [
            _wp(FlightWaypointType.TAKEOFF),
            refuel,
            _wp(FlightWaypointType.LANDING_POINT),
        ],
        coalition=_ato_with(tanker),
    )
    flight.flight_plan.fuel_consumption_between_points = leg

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.refuel_passes == 1
    assert walked[0].position == _at(0, 5000)
    assert refuel.position == _at(3000, 5000), "the plan's own waypoint is untouched"


def test_walk_stops_at_the_landing_point() -> None:
    # A trailing (bullseye-style) reference waypoint after landing must not
    # burn fuel.
    flight = _flight(
        [
            _wp(FlightWaypointType.TAKEOFF),
            _wp(FlightWaypointType.LANDING_POINT),
            _wp(FlightWaypointType.BULLSEYE),
        ]
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.burn_lbs == 200 + 1000  # taxi + the single flown leg


def test_external_tanks_count_toward_the_margin() -> None:
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF),
        _wp(),
        _wp(FlightWaypointType.LANDING_POINT),
    ]
    dry = fuel_brief_for(_flight(waypoints))
    loadout = _tank_loadout(2)
    bagged = fuel_brief_for(_flight(waypoints), loadout)

    assert dry is not None and bagged is not None
    assert bagged.tank_count == 2
    assert bagged.external_lbs == pytest.approx(2 * 370 * 6.7, rel=0.01)
    assert bagged.margin_lbs == pytest.approx(dry.margin_lbs + bagged.external_lbs)


def test_defaults_to_the_driest_member() -> None:
    # Mixed loadouts: the brief mirrors the tanker decision and uses the driest.
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF),
        _wp(FlightWaypointType.LANDING_POINT),
    ]
    members = [
        SimpleNamespace(loadout=_tank_loadout(3)),
        SimpleNamespace(loadout=_tank_loadout(1)),
    ]
    brief = fuel_brief_for(_flight(waypoints, members=members))

    assert brief is not None
    assert brief.tank_count == 1


def test_no_fuel_model_returns_none_and_estimate_is_flagged() -> None:
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF),
        _wp(FlightWaypointType.LANDING_POINT),
    ]
    assert fuel_brief_for(_flight(waypoints, measured=None, estimated=None)) is None

    estimated = fuel_brief_for(_flight(waypoints, measured=None, estimated=_FUEL))
    assert estimated is not None and estimated.estimated

    measured = fuel_brief_for(_flight(waypoints))
    assert measured is not None and not measured.estimated


def _brief(**overrides: Any) -> FuelBrief:
    values: dict[str, Any] = dict(
        internal_lbs=12149,
        external_lbs=4958,
        tank_count=2,
        burn_lbs=11034,
        reserve_lbs=2000,
        refuel_passes=0,
        margin_lbs=4073,
        dry_margin_lbs=4073,
        estimated=False,
    )
    values.update(overrides)
    return FuelBrief(**values)


def test_text_leads_with_what_the_jet_lands_with() -> None:
    assert "no fuel model" in fuel_brief_text(None)

    text = fuel_brief_text(_brief())
    # 4,073 over a 2,000 reserve is 6,073 on landing, to the nearest hundred.
    assert text.startswith("Fuel plan: lands with about 6,100 lb (reserve 2,000 lb).")
    assert "Burns about 11,000 of 17,100 lb carried." in text
    assert "anker" not in text, "no tanker on the route, no tanker words"


def test_a_tanker_pass_the_sortie_does_not_need_is_called_out() -> None:
    # The planner adds a pass whenever a tanker is up, whatever the fuel (flown
    # complaint 2026-11-16: "+4,073 margin" next to "1 tanker pass planned").
    text = fuel_brief_text(_brief(refuel_passes=1, margin_lbs=9000))
    assert "Tanker: not needed." in text
    assert "9,000" not in text, "the top-off is not counted as gas taken"


def test_a_sortie_that_needs_the_tanker_says_so() -> None:
    text = fuel_brief_text(
        _brief(refuel_passes=1, margin_lbs=3200, dry_margin_lbs=-1800)
    )
    assert text.startswith("Fuel plan: needs the tanker.")
    assert "about 1,800 lb under the 2,000 lb reserve" in text
    assert "with it, about 3,200 lb over" in text
    assert "short" not in text


def test_a_short_sortie_says_short_and_what_to_do() -> None:
    text = fuel_brief_text(
        _brief(margin_lbs=-3500, dry_margin_lbs=-3500, estimated=True)
    )
    assert text.startswith("Fuel plan: short.")
    assert "about 3,500 lb under the 2,000 lb reserve" in text
    assert "Add tanks, shorten the route, or plan a tanker." in text
    assert text.endswith("Rough estimate: no measured fuel data for this jet.")
