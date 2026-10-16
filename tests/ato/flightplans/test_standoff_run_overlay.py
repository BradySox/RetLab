from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.sead import SeadFlightPlan
from game.ato.flightplans.seadsweep import SeadSweepFlightPlan
from game.ato.flightplans.tacticaloverlay import (
    TacticalOverlayDisplay,
    standoff_run_overlay,
)
from game.ato.flightplans.uizonedisplay import UiZoneDisplay
from game.utils import nautical_miles


def _p(x: float, y: float) -> Point:
    return Point(x, y, Caucasus())


def test_bubble_on_engagement_center() -> None:
    target = _p(50000, 0)
    overlay = standoff_run_overlay(
        path=[_p(0, 0), _p(20000, 0), _p(0, 5000)],
        engagement_center=target,
        engagement_range=nautical_miles(30),
        target_position=target,
    )
    assert len(overlay.reach) == 1 and overlay.reach[0].filled
    minx, _, maxx, _ = overlay.reach[0].geometry.bounds
    assert (minx + maxx) / 2 == 50000  # bubble centered on engagement_center
    assert overlay.targets[0].position == target


def test_the_path_is_the_run_not_an_orbit_ring() -> None:
    # Neither SEAD nor SEAD Sweep has an orbit task, so the map draws the run it
    # flies: ingress, search or sweep point, split.
    run = [_p(0, 0), _p(20000, 0), _p(0, 5000)]
    overlay = standoff_run_overlay(
        path=run,
        engagement_center=run[1],
        engagement_range=nautical_miles(20),
        target_position=_p(50000, 0),
    )
    assert overlay.actual_path == run


def test_sead_family_are_overlay_and_uizone_displays() -> None:
    for cls in (SeadFlightPlan, SeadSweepFlightPlan):
        assert issubclass(cls, TacticalOverlayDisplay)
        assert issubclass(cls, UiZoneDisplay)
