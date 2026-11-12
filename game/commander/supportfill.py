"""Fill support (§130): add the escorts a hand-built package's route calls for.

The player builds the main flight; this runs the auto-planner's own escort check
(``PackageFulfiller.check_needed_escorts``) on that package and adds a 2-ship
fighter escort and one 2-ship suppression flight where the route needs them.
Design: ``docs/dev/retlab-features.md`` §130.

- The SAM check counts only sites the player knows (the map's own rings), with
  the overview toggle ignored, so an added SEAD flight never hints at a hidden site.
- Free jets in range only. It never places a purchase order.
- Keep what fits: a flight it cannot fill is reported, never fatal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from game.ato.closestairfields import ObjectiveDistanceCache
from game.ato.flightplans.planningerror import PlanningError
from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType, ProposedFlight
from game.commander.packagebuilder import PackageBuilder
from game.commander.packagefulfiller import PackageFulfiller
from game.theater.fogofwar import fog_intact
from game.threatzones import ThreatZones

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight, Package
    from game.coalition import Coalition

#: Size of every support flight, as the auto-planner proposes them.
SUPPORT_FLIGHT_SIZE = 2

#: Flights that already give the package fighter cover.
A2A_COVER = frozenset({FlightType.ESCORT, FlightType.TARCAP})

#: Flights that already suppress for the package.
SEAD_COVER = frozenset({FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP})

#: Suppression flavours tried in order; the first a squadron can fill is added.
SEAD_FLAVOURS = (FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP)


@dataclass
class SupportFillResult:
    """What Fill support did to a package."""

    added: list[Flight] = field(default_factory=list)
    #: One plain line per needed flight that was not added.
    not_added: list[str] = field(default_factory=list)
    #: Covers the route already had, or needed none, per escort kind.
    already_covered: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines: list[str] = []
        if self.added:
            names = ", ".join(
                f"{f.count}x {f.unit_type} {f.flight_type.value}" for f in self.added
            )
            lines.append(f"Added: {names}.")
        lines.extend(self.not_added)
        lines.extend(self.already_covered)
        if not lines:
            lines.append(
                "Nothing added: the route crosses no enemy fighter cover and no "
                "SAM ring on your map."
            )
        return "\n".join(lines)


def player_threat_zones(coalition: Coalition) -> ThreatZones:
    """The enemy threat as this side's map shows it: known SAM sites only."""
    with fog_intact():
        return ThreatZones.for_faction(
            coalition.game, coalition.opponent.player, viewer=coalition.player
        )


def _a2a_task(package: Package) -> FlightType:
    # PlanCas covers CAS with TARCAP, not an escort tied to the attackers.
    primary = package.primary_task
    return FlightType.TARCAP if primary is FlightType.CAS else FlightType.ESCORT


def fill_package_support(
    game: Game,
    coalition: Coalition,
    package: Package,
    threat_zones: Optional[ThreatZones] = None,
) -> SupportFillResult:
    """Adds the support flights the package's route needs, in place."""
    result = SupportFillResult()
    if not package.flights:
        return result
    if threat_zones is None:
        threat_zones = player_threat_zones(coalition)

    fulfiller = PackageFulfiller(
        coalition,
        game.theater,
        game.db.flights,
        game.settings,
        threat_zones=threat_zones,
    )
    builder = PackageBuilder(
        package.target,
        ObjectiveDistanceCache.get_closest_airfields(package.target),
        coalition.air_wing,
        coalition.laser_code_registry,
        game.db.flights,
        coalition.player.is_blue,
        game.settings.default_start_type,
        package.auto_asap,
    )
    # Plan straight into the player's package rather than a new one.
    builder.package = package

    needed = fulfiller.check_needed_escorts(builder)
    present = {f.flight_type for f in package.flights}
    doctrine = coalition.doctrine

    wanted: list[tuple[str, tuple[FlightType, ...]]] = []
    if not needed[EscortType.AirToAir]:
        result.already_covered.append("No fighter escort needed on this route.")
    elif present & A2A_COVER:
        result.already_covered.append("Fighter cover is already in the package.")
    else:
        wanted.append(("fighter escort", (_a2a_task(package),)))
    if not needed[EscortType.Sead]:
        result.already_covered.append("No SEAD needed: no SAM ring on your map.")
    elif present & SEAD_COVER:
        result.already_covered.append("SEAD is already in the package.")
    else:
        wanted.append(("SEAD", SEAD_FLAVOURS))

    for label, tasks in wanted:
        allowed = tuple(t for t in tasks if doctrine.allows(t))
        if not allowed:
            result.not_added.append(
                f"No {label} added: this era's doctrine flies none."
            )
            continue
        flight = _plan_first(builder, allowed)
        if flight is None:
            result.not_added.append(
                f"No {label} added: no free {label} jets in range this turn."
            )
        else:
            result.added.append(flight)
    return result


def _plan_first(
    builder: PackageBuilder, tasks: tuple[FlightType, ...]
) -> Optional[Flight]:
    package = builder.package
    for task in tasks:
        before = list(package.flights)
        if not builder.plan_flight(
            ProposedFlight(task, SUPPORT_FLIGHT_SIZE), ignore_range=False
        ):
            continue
        flight = next(f for f in package.flights if f not in before)
        try:
            flight.recreate_flight_plan()
        except PlanningError:
            package.remove_flight(flight)
            continue
        return flight
    return None
