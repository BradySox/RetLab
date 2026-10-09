"""Whether a tanker this flight could actually plug into is in the ATO.

The planner's refuel waypoint used to be gated on "does this coalition OWN a
tanker-capable squadron anywhere in theater", which is a question about the air
wing rather than about this turn. A flight got the waypoint whether or not a
tanker was flying, and the in-app fuel readout then credited a top-off from it.

This asks the narrower question the generated mission already asks (see
``game/missiongenerator/refuelrendezvous.py``, which resolves the same waypoint
against the tankers that exist in the .miz). Asking it at plan time as well
keeps the planning UI and the mission in agreement.

Deliberately NOT a fuel-need test. Whether the sortie needs the gas is what the
reverted §46 decided, and re-opening it would re-open the planner divergence the
2026-08-09 re-convergence closed.

Safe to call while a flight plan is being built: ``TheaterSupport`` is the first
method ``PlanNextAction`` yields, so tankers are in the ATO before any offensive
package is planned, and this reads ``flight_type``/``unit_type`` only -- never
another flight's ``flight_plan``, which would risk recursion.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional, TYPE_CHECKING

from game.ato.flighttype import FlightType

if TYPE_CHECKING:
    from dcs import Point

    from game.ato.flight import Flight


def serviceable_tanker_planned(flight: "Flight") -> bool:
    """Whether this coalition has a tanker planned that ``flight`` can use.

    ``FlightType.RECOVERY`` is excluded by construction rather than by a check:
    a recovery tanker is its own flight type, and it works the boat's pattern
    rather than servicing passing traffic.
    """
    ato = getattr(getattr(flight, "coalition", None), "ato", None)
    if ato is None:
        # Lightweight test doubles carry no ATO. Read as "yes" so nothing is
        # dropped on a guess -- the generation-time pass is the backstop.
        return True
    for package in ato.packages:
        for tanker in package.flights:
            if tanker.flight_type is not FlightType.REFUELING:
                continue
            if flight.unit_type.can_refuel_from(tanker.unit_type):
                return True
    return False


def early_refuel_point(flight: "Flight", planned: "Point") -> Optional["Point"]:
    """Where on a theater tanker's track ``flight`` tanks on its way out, or None.

    For the stop before a push or a CAP station. A package's own tanker is timed
    to arrive after the strike, so it is not a candidate. Lightweight test doubles
    with no ATO keep the planned point.
    """
    from game.missiongenerator.refuelrendezvous import (
        planned_tankers,
        refuel_rendezvous,
    )

    tankers = planned_tankers(flight)
    if tankers is None:
        return planned
    return refuel_rendezvous(
        flight.unit_type, flight.blue.is_blue, planned, tankers, theater_only=True
    )


def post_refuel_shortfall(flight: "Flight", layout: Any) -> Optional[float]:
    """Pounds under its reserve the flight lands if it skips its second tanker stop.

    None when the stop is not needed, or the route lacks one of the two stops (the
    one before the push or station, and the one after). DM 2026-10-07: the second
    stop is kept only when the first top-off does not get the jet home.
    """
    from game.retlab.fuel_brief import fuel_brief_for

    post = getattr(layout, "refuel", None)
    if post is None or getattr(layout, "pre_push_refuel", None) is None:
        return None
    layout.refuel = None
    try:
        brief = fuel_brief_for(flight)
    finally:
        layout.refuel = post
    if brief is None or brief.margin_lbs >= 0:
        return None
    return -brief.margin_lbs


def post_refuel_unneeded(flight: "Flight", layout: Any) -> bool:
    """Whether the stop after the strike or station can be dropped."""
    if getattr(layout, "refuel", None) is None:
        return False
    if getattr(layout, "pre_push_refuel", None) is None:
        return False
    return post_refuel_shortfall(flight, layout) is None


def auto_tanking_minutes(flight: "Flight") -> int:
    """The package tanker's own figure: 4 min a jet, plus 1."""
    return 4 * flight.roster.max_size + 1


def tanking_time(flight: "Flight") -> timedelta:
    """Time on the boom at the stop before the push or station.

    The player's minutes when set on the Waypoints tab, else the automatic figure.
    """
    minutes = getattr(flight, "tanking_minutes", None)
    if minutes is None:
        minutes = auto_tanking_minutes(flight)
    return timedelta(minutes=minutes)
