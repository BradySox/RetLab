from dcs import Point
from dcs.terrain import Caucasus
from shapely.geometry import Point as ShapelyPoint

from game.ato.flightplans.tacticaloverlay import cas_overlay, escort_overlay
from game.utils import nautical_miles


def _p(x: float, y: float) -> Point:
    return Point(x, y, Caucasus())


def test_escort_corridor_follows_route() -> None:
    overlay = escort_overlay(
        route=[_p(0, 0), _p(50000, 10000), _p(100000, 0)],
        engagement_range=nautical_miles(20),
    )
    assert len(overlay.reach) == 1 and overlay.reach[0].filled
    assert overlay.reach[0].geometry.contains(ShapelyPoint(50000, 10000))
    assert overlay.targets == []


def test_cas_corridor_spans_the_flot() -> None:
    overlay = cas_overlay(
        patrol_start=_p(0, 0),
        patrol_end=_p(40000, 0),
        engagement_range=nautical_miles(10),
    )
    assert len(overlay.reach) == 1 and overlay.reach[0].filled
    geom = overlay.reach[0].geometry
    # Corridor down the whole FLOT, not just a circle at the midpoint.
    assert geom.contains(ShapelyPoint(0, 0))
    assert geom.contains(ShapelyPoint(20000, 0))
    assert geom.contains(ShapelyPoint(40000, 0))
    assert overlay.actual_path is None


def test_escort_band_bends_through_the_package_detours() -> None:
    # 2026-10-18: the band ran straight from the join to the hold and covered the
    # SAM rings the package route goes round.
    from types import SimpleNamespace

    from game.ato import FlightType
    from game.ato.flightplans.escort import EscortFlightPlan

    def wp(x: float, y: float) -> SimpleNamespace:
        return SimpleNamespace(position=_p(x, y))

    plan = object.__new__(EscortFlightPlan)
    plan.layout = SimpleNamespace(
        join=wp(0, 0),
        ingress_nav=[wp(0, 150000)],
        initial=wp(150000, 150000),
    )
    plan.flight = SimpleNamespace(  # type: ignore[assignment]
        flight_type=FlightType.SEAD_ESCORT,
        coalition=SimpleNamespace(
            doctrine=SimpleNamespace(sead_escort_engagement_range=nautical_miles(10))
        ),
    )
    geom = plan.tactical_overlay().reach[0].geometry
    assert geom.contains(ShapelyPoint(0, 150000))
    assert not geom.contains(ShapelyPoint(75000, 75000))
