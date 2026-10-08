from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus, Terrain
from dcs.vehicles import Armor
from unittest.mock import MagicMock

from game.ato.flight import Flight
from game.ato.flightplans.bai import BaiFlightPlan
from game.ato.flightplans.formationattack import (
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from game.ato.flightplans.strike import StrikeFlightPlan
from game.ato.flighttype import FlightType
from game.data.groups import GroupTask
from game.dcs.groundunittype import GroundUnitType
from game.missiongenerator.motorpoolpopulator import MotorpoolPopulator
from game.theater import TheaterGroundObject
from game.theater.controlpoint import ControlPoint
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import MotorpoolGroundObject
from game.utils import Heading, meters
from game.ato.flightwaypoint import FlightWaypoint
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.package import Package
from game.utils import Speed, knots


class _StubPackage:
    def __init__(self, formation_speed: Speed | None) -> None:
        self._formation_speed = formation_speed

    def formation_speed(self, is_helo: bool) -> Speed | None:
        return self._formation_speed


class _StubFlight:
    def __init__(self, package: Package) -> None:
        self.package = package
        self.is_helo = False


class _FormationAttackUnderTest(FormationAttackFlightPlan):
    """Minimal concrete flight plan exercising ``speed_between_waypoints``.

    The real collaborators (package, flight, formation speed) are stubbed so the
    test focuses on how the target-area segment is priced.
    """

    def __init__(self, formation_speed: Speed | None, fallback_speed: Speed) -> None:
        package = cast(Package, _StubPackage(formation_speed))
        self.flight = cast(Flight, _StubFlight(package))
        self._fallback_speed = fallback_speed

    @property
    def best_flight_formation_speed(self) -> Speed:
        return self._fallback_speed


@pytest.fixture(name="target_waypoint")
def target_waypoint_fixture() -> FlightWaypoint:
    terrain: Terrain = Caucasus()
    return FlightWaypoint(
        "TARGET AREA",
        FlightWaypointType.TARGET_GROUP_LOC,
        Point(0, 0, terrain),
    )


def test_uses_package_formation_speed_at_target_when_available(
    target_waypoint: FlightWaypoint,
) -> None:
    formation_speed = knots(400)
    plan = _FormationAttackUnderTest(formation_speed, fallback_speed=knots(500))

    speed = plan.speed_between_waypoints(target_waypoint, target_waypoint)

    assert speed == formation_speed


def _leg(name: str, kind: FlightWaypointType, north_nm: float) -> FlightWaypoint:
    return FlightWaypoint(name, kind, Point(0, north_nm * 1852, Caucasus()))


def test_the_leg_out_of_the_target_carries_the_time_over_it() -> None:
    # The locked split time charges 45 s per target point. The forward chain
    # that times every waypoint after the split sums total_time_between_waypoints
    # leg by leg, so the same dwell has to ride the last-target -> split leg or
    # the chain runs ahead of the split by the whole dwell (measured: a 4-target
    # DEAD timed its refuel 27 s before its split).
    plan = _FormationAttackUnderTest(
        formation_speed=knots(400), fallback_speed=knots(500)
    )
    targets = [_leg(f"T{i}", FlightWaypointType.TARGET_POINT, 0.0) for i in range(3)]
    split = _leg("SPLIT", FlightWaypointType.SPLIT, 10.0)
    join = _leg("JOIN", FlightWaypointType.JOIN, -10.0)
    plan.layout = cast(
        Any,
        SimpleNamespace(
            hold=None,
            ingress=join,
            join=join,
            split=split,
            targets=targets,
            ingress_nav=[],
            egress_nav=[],
            pre_push_refuel=None,
        ),
    )

    between_targets = plan.total_time_between_waypoints(targets[0], targets[1])
    out_of_target = plan.total_time_between_waypoints(targets[-1], split)

    assert between_targets == timedelta(0)
    # 10 nm at 400 kt with the 5% pad, plus 3 x 45 s over the target.
    travel = timedelta(hours=10 / 400 * 1.05)
    assert out_of_target == travel + timedelta(minutes=2.25)
    assert plan.time_at_target == timedelta(minutes=2.25)


def test_falls_back_to_flight_speed_when_package_has_no_formation_speed(
    target_waypoint: FlightWaypoint,
) -> None:
    fallback_speed = knots(250)
    plan = _FormationAttackUnderTest(
        formation_speed=None, fallback_speed=fallback_speed
    )

    speed = plan.speed_between_waypoints(target_waypoint, target_waypoint)

    assert speed == fallback_speed


def test_slow_tag_along_is_capped_at_its_own_speed(
    target_waypoint: FlightWaypoint,
) -> None:
    # The TARPS drone excluded from Package.formation_speed faces a package
    # speed faster than it can fly; its own legs stay at its own capability.
    own_speed = knots(169)
    plan = _FormationAttackUnderTest(knots(400), fallback_speed=own_speed)

    speed = plan.speed_between_waypoints(target_waypoint, target_waypoint)

    assert speed == own_speed


class _SpeedOnlyPlan(FormationAttackFlightPlan):
    """FormationFlightPlan stand-in exposing only a formation speed."""

    def __init__(self, speed: Speed) -> None:
        self._speed = speed

    @property
    def best_flight_formation_speed(self) -> Speed:
        return self._speed


def _package_flight(flight_type: FlightType, speed: Speed) -> Flight:
    from types import SimpleNamespace

    return cast(
        Flight,
        SimpleNamespace(
            flight_type=flight_type,
            is_helo=False,
            flight_plan=_SpeedOnlyPlan(speed),
        ),
    )


def _package_with(*flights: Flight) -> Package:
    package = Package(target=cast(Any, None), db=cast(Any, None))
    package.flights = list(flights)
    return package


def test_package_formation_speed_ignores_the_tag_along_tarps_bird() -> None:
    # The auto-added TARPS/BDA drone rides the package on its own ToT offset;
    # it must not drag a Hornet DEAD package's formation legs to MQ-9 pace.
    package = _package_with(
        _package_flight(FlightType.DEAD, knots(519)),
        _package_flight(FlightType.SEAD, knots(422)),
        _package_flight(FlightType.TARPS, knots(169)),
    )
    speed = package.formation_speed(is_helo=False)
    assert speed == knots(422)


def test_recon_package_still_paces_to_its_primary_tarps_bird() -> None:
    # A package whose *primary* is TARPS (a recon package) keeps the recon
    # bird in the formation-speed minimum so its escort stays with it.
    package = _package_with(
        _package_flight(FlightType.TARPS, knots(169)),
        _package_flight(FlightType.ESCORT, knots(517)),
    )
    speed = package.formation_speed(is_helo=False)
    assert speed == knots(169)


def test_empty_motorpool_strike_uses_target_area_waypoint(monkeypatch: Any) -> None:
    terrain = Caucasus()
    control_point = cast(ControlPoint, SimpleNamespace())
    target = MotorpoolGroundObject(
        "Motorpool",
        PresetLocation("Garage", Point(0, 0, terrain), Heading.from_degrees(0)),
        control_point,
        GroupTask.MOTORPOOL,
    )
    package = cast(
        Package,
        SimpleNamespace(
            target=target,
            waypoints=SimpleNamespace(
                join=FlightWaypoint(
                    "JOIN", FlightWaypointType.JOIN, Point(0, 0, terrain)
                ),
                ingress=FlightWaypoint(
                    "INGRESS", FlightWaypointType.INGRESS_STRIKE, Point(0, 0, terrain)
                ),
                split=Point(0, 0, terrain),
            ),
        ),
    )
    flight = cast(
        Flight,
        SimpleNamespace(
            package=package,
            flight_type=FlightType.STRIKE,
            is_helo=False,
            departure=SimpleNamespace(position=Point(0, 0, terrain)),
            arrival=SimpleNamespace(position=Point(0, 0, terrain)),
            divert=None,
        ),
    )
    builder = cast(Any, object.__new__(StrikeFlightPlan.builder_type()))
    builder.flight = flight
    builder._hold_point = lambda: Point(0, 0, terrain)
    builder._get_split = lambda: Point(0, 0, terrain)
    builder._build_refuel = lambda _builder: None
    builder._sam_detours = lambda *_args: ([], [])

    class FakeWaypointBuilder:
        get_combat_altitude = cast(Any, None)

        def __init__(self, _flight: Flight, _targets: object) -> None:
            pass

        def __getattr__(self, _name: str) -> Any:
            return lambda *_args: FlightWaypoint(
                "TARGET AREA", FlightWaypointType.TARGET_GROUP_LOC, target.position
            )

    monkeypatch.setattr(
        "game.ato.flightplans.formationattack.WaypointBuilder", FakeWaypointBuilder
    )

    layout = builder.layout()
    plan = StrikeFlightPlan.__new__(StrikeFlightPlan)
    plan.flight = flight
    plan.layout = layout

    assert len(layout.targets) == 1
    assert plan.tot_waypoint is layout.targets[0]


def _motorpool_with_groups(
    terrain: Terrain, groups: list[Any]
) -> MotorpoolGroundObject:
    target = MotorpoolGroundObject(
        "Motorpool",
        PresetLocation("Garage", Point(0, 0, terrain), Heading.from_degrees(0)),
        cast(ControlPoint, SimpleNamespace()),
        GroupTask.MOTORPOOL,
    )
    target.groups = cast(Any, groups)
    return target


def _populate_motorpool(target: MotorpoolGroundObject, count: int) -> None:
    from game.theater.player import Player

    unit_type = next(GroundUnitType.for_dcs_type(Armor.M_1_Abrams))
    control_point = target.control_point
    control_point.base = cast(Any, SimpleNamespace(armor={unit_type: count}))
    cast(Any, control_point).captured = Player.BLUE
    control_point.connected_points = []
    cast(Any, control_point).ground_objects = [target]
    unit_ids = iter(range(1, 1000))
    group_ids = iter(range(1, 1000))
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[control_point]),
        settings=SimpleNamespace(motorpool_enabled=True, motorpool_spawn_cap=10),
        next_unit_id=lambda: next(unit_ids),
        next_group_id=lambda: next(group_ids),
    )
    MotorpoolPopulator(cast(Any, game)).populate()


def test_refreshed_strike_plan_snapshots_live_motorpool_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real-ordering regression: the STRIKE flight plan is built at ATO
    planning time against an EMPTY motorpool; mission generation later renders
    the parked units and refreshes motorpool-target plans. The refreshed
    layout must target one StrikeTarget per parked unit instead of keeping
    the frozen empty snapshot (which produced a single area waypoint)."""

    class _Captured(Exception):
        pass

    terrain = Caucasus()
    target = _motorpool_with_groups(terrain, [])
    from game.theater.player import Player

    cast(Any, target.control_point).captured = Player.BLUE
    flight = cast(
        Any,
        SimpleNamespace(
            **vars(cast(Any, _attack_flight(target, FlightType.STRIKE))),
            coalition=SimpleNamespace(
                player=Player.BLUE, game=SimpleNamespace(settings=SimpleNamespace())
            ),
        ),
    )
    captured: list[list[Any]] = []

    def capture(_ingress: Any, targets: list[Any]) -> Any:
        captured.append(list(targets))
        raise _Captured

    builder = StrikeFlightPlan.builder_type()(cast(Any, flight))
    monkeypatch.setattr(builder, "_build", capture)
    # Package waypoints are pre-supplied by the fixture; skip the generator,
    # which would need the full navmesh/threat stack.
    monkeypatch.setattr(
        builder, "_generate_package_waypoints_if_needed", lambda *args: None
    )

    # ATO planning time: motorpool groups empty -> frozen empty target list.
    with pytest.raises(_Captured):
        builder.get_or_build()
    assert captured[-1] == []

    # Mission generation: render the units, then refresh the plan.
    _populate_motorpool(target, 3)
    with pytest.raises(_Captured):
        builder.regenerate()

    assert len(captured[-1]) == 3


def test_refresh_flight_plan_keeps_manual_timing() -> None:
    """refresh_flight_plan regenerates the plan without the manual-timing
    wipe that recreate_flight_plan performs."""
    takeoff = object()
    flight = cast(Any, Flight.__new__(Flight))
    flight.manually_timed = True
    flight.manual_takeoff_time = takeoff
    flight._flight_plan_builder = MagicMock()

    flight.refresh_flight_plan()

    flight._flight_plan_builder.regenerate.assert_called_once_with(False)
    assert flight.manually_timed is True
    assert flight.manual_takeoff_time is takeoff


def test_refresh_targets_only_motorpool_packages() -> None:
    """Only flights in packages targeting a motorpool are refreshed."""
    from game.missiongenerator.missiongenerator import (
        refresh_motorpool_target_flight_plans,
    )

    motorpool = _motorpool_with_groups(Caucasus(), [])
    motorpool_flight = MagicMock()
    regular_flight = MagicMock()
    game = SimpleNamespace(
        coalitions=[
            SimpleNamespace(
                ato=SimpleNamespace(
                    packages=[
                        SimpleNamespace(target=motorpool, flights=[motorpool_flight]),
                        SimpleNamespace(
                            target=SimpleNamespace(), flights=[regular_flight]
                        ),
                    ]
                )
            )
        ]
    )

    refresh_motorpool_target_flight_plans(cast(Any, game))

    motorpool_flight.refresh_flight_plan.assert_called_once_with()
    regular_flight.refresh_flight_plan.assert_not_called()


def _attack_flight(target: Any, flight_type: FlightType) -> Flight:
    terrain = Caucasus()
    ingress_type = {
        FlightType.STRIKE: FlightWaypointType.INGRESS_STRIKE,
        FlightType.BAI: FlightWaypointType.INGRESS_BAI,
        FlightType.ARMED_RECON: FlightWaypointType.INGRESS_ARMED_RECON,
    }[flight_type]
    package = cast(
        Package,
        SimpleNamespace(
            target=target,
            waypoints=SimpleNamespace(
                join=FlightWaypoint(
                    "JOIN", FlightWaypointType.JOIN, Point(0, 0, terrain)
                ),
                ingress=FlightWaypoint("INGRESS", ingress_type, Point(0, 0, terrain)),
                split=Point(0, 0, terrain),
            ),
        ),
    )
    return cast(
        Flight,
        SimpleNamespace(
            package=package,
            flight_type=flight_type,
            is_helo=False,
            departure=SimpleNamespace(position=Point(0, 0, terrain)),
            arrival=SimpleNamespace(position=Point(0, 0, terrain)),
            divert=None,
        ),
    )


def _layout_with_fake_builder(
    monkeypatch: Any,
    flight: Flight,
    builder_type: type[Any],
    waypoint_builder: type[Any],
) -> FormationAttackLayout:
    builder = cast(Any, object.__new__(builder_type))
    builder.flight = flight
    builder._hold_point = lambda: flight.package.target.position
    builder._get_split = lambda: flight.package.target.position
    builder._build_refuel = lambda _builder: None
    builder._sam_detours = lambda *_args: ([], [])
    monkeypatch.setattr(
        "game.ato.flightplans.formationattack.WaypointBuilder", waypoint_builder
    )
    return cast(FormationAttackLayout, builder.layout())


def test_motorpool_bai_with_live_groups_uses_single_bai_named_waypoint(
    monkeypatch: Any,
) -> None:
    """Spec: motorpool BAI gets ONE target waypoint for the motorpool total,
    named the way other BAI flights name theirs ("ATTACK ...") — not one
    waypoint per unit-type group and not a strike-style area name."""
    terrain = Caucasus()
    group = cast(Any, SimpleNamespace(units=[object()], group_name="Armor"))
    target = _motorpool_with_groups(terrain, [group])
    flight = _attack_flight(target, FlightType.BAI)

    class FakeWaypointBuilder:
        get_combat_altitude = cast(Any, None)

        def __init__(self, _flight: Flight, _targets: object) -> None:
            pass

        def bai_group(self, target: object) -> FlightWaypoint:
            return FlightWaypoint(
                "BAI GROUP", FlightWaypointType.TARGET_POINT, Point(1, 1, terrain)
            )

        def strike_area(self, _target: object) -> FlightWaypoint:
            return FlightWaypoint(
                "STRIKE AREA", FlightWaypointType.TARGET_GROUP_LOC, Point(2, 2, terrain)
            )

        def __getattr__(self, _name: str) -> Any:
            return lambda *_args: FlightWaypoint(
                "OTHER", FlightWaypointType.TARGET_GROUP_LOC, target.position
            )

    layout = _layout_with_fake_builder(
        monkeypatch, flight, BaiFlightPlan.builder_type(), FakeWaypointBuilder
    )

    assert len(layout.targets) == 1
    assert layout.targets[0].name == "BAI GROUP"


def test_non_motorpool_bai_keeps_per_target_waypoints(monkeypatch: Any) -> None:
    """Spec: only motorpool BAI collapses to a single area waypoint; BAI
    against an ordinary TGO keeps one waypoint per target group."""
    terrain = Caucasus()
    target = MagicMock(spec=TheaterGroundObject)
    target.name = "Enemy Armor"
    target.position = Point(0, 0, terrain)
    target.groups = [SimpleNamespace(units=[object()], group_name="Armor")]
    flight = _attack_flight(target, FlightType.BAI)

    class FakeWaypointBuilder:
        get_combat_altitude = cast(Any, None)

        def __init__(self, _flight: Flight, _targets: object) -> None:
            pass

        def bai_group(self, target: object) -> FlightWaypoint:
            return FlightWaypoint(
                "BAI GROUP", FlightWaypointType.TARGET_POINT, Point(1, 1, terrain)
            )

        def strike_area(self, _target: object) -> FlightWaypoint:
            return FlightWaypoint(
                "STRIKE AREA", FlightWaypointType.TARGET_GROUP_LOC, Point(2, 2, terrain)
            )

        def __getattr__(self, _name: str) -> Any:
            return lambda *_args: FlightWaypoint(
                "OTHER", FlightWaypointType.TARGET_GROUP_LOC, target.position
            )

    layout = _layout_with_fake_builder(
        monkeypatch, flight, BaiFlightPlan.builder_type(), FakeWaypointBuilder
    )

    assert len(layout.targets) == 1
    assert layout.targets[0].name == "BAI GROUP"


def test_motorpool_strike_with_live_units_uses_one_site_waypoint(
    monkeypatch: Any,
) -> None:
    """A motorpool Strike gets the fork's site waypoint, carrying each unit."""
    terrain = Caucasus()
    units = [
        SimpleNamespace(
            alive=True,
            type=SimpleNamespace(id=f"Unit {i}"),
            position=Point(i, i, terrain),
        )
        for i in range(3)
    ]
    group = cast(Any, SimpleNamespace(units=units, group_name="Armor"))
    target = _motorpool_with_groups(terrain, [group])
    flight = _attack_flight(target, FlightType.STRIKE)
    captured_units: list[Any] = []

    class FakeWaypointBuilder:
        get_combat_altitude = cast(Any, None)

        def __init__(self, _flight: Flight, _targets: object) -> None:
            pass

        def target_site(
            self, _site: object, targets: list[Any], _task: str
        ) -> FlightWaypoint:
            captured_units.extend(targets)
            return FlightWaypoint(
                "STRIKE SITE", FlightWaypointType.TARGET_GROUP_LOC, Point(0, 0, terrain)
            )

        def strike_point(self, target: object) -> FlightWaypoint:
            return FlightWaypoint(
                f"STRIKE POINT {cast(Any, target).name}",
                FlightWaypointType.TARGET_POINT,
                Point(0, 0, terrain),
            )

        def __getattr__(self, _name: str) -> Any:
            return lambda *_args: FlightWaypoint(
                "OTHER", FlightWaypointType.TARGET_GROUP_LOC, target.position
            )

    layout = _layout_with_fake_builder(
        monkeypatch, flight, StrikeFlightPlan.builder_type(), FakeWaypointBuilder
    )

    # The fork folds a Strike into one site waypoint carrying every unit
    # (SITE_WAYPOINT_TASKS), motorpool or not.
    assert [waypoint.name for waypoint in layout.targets] == ["STRIKE SITE"]
    assert len(captured_units) == 3
