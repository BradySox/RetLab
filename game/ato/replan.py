"""Keep the player's own packages through a mid-turn re-plan.

``Coalition.initialize_turn`` wipes the whole ATO and re-plans it. A mid-turn
re-plan from the top bar lifts out every package with a player seat first, puts
its aircraft and pilots back on the books after the air wing is reset, and adds
it back once the planner has run, dropping one new package with the same task
and target for each one kept (the planner never reads the ATO, so it would plan
that target again).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Hashable

if TYPE_CHECKING:
    from game.ato.airtaaskingorder import AirTaskingOrder
    from game.ato.package import Package


def _is_player_qra_alert(package: Package) -> bool:
    from game.theater.missiontarget import HomeBaseDefenseZone

    # The alert is rebuilt from the squadron's QRA settings on every plan, and its
    # airframes come from the QRA reserve rather than the untasked pool.
    target = package.target
    return isinstance(target, HomeBaseDefenseZone) and target.name.startswith(
        "QRA Alert "
    )


def is_kept_on_replan(package: Package) -> bool:
    """A package survives a re-plan when any of its flights has a player seat."""
    if _is_player_qra_alert(package):
        return False
    return any(flight.client_count > 0 for flight in package.flights)


def detach_player_packages(ato: AirTaskingOrder) -> list[Package]:
    """Take the player packages out of the ATO without releasing their crews."""
    kept = [p for p in ato.packages if is_kept_on_replan(p)]
    for package in kept:
        ato.packages.remove(package)
    return kept


def reclaim_crews(kept: list[Package]) -> None:
    """Book the kept flights' aircraft and pilots again after ``AirWing.reset``."""
    for package in kept:
        for flight in package.flights:
            squadron = flight.squadron
            take = min(flight.count, squadron.untasked_aircraft)
            if take < flight.count:
                logging.warning(
                    "Re-plan: %s has %d untasked aircraft for a kept %d-ship",
                    squadron,
                    squadron.untasked_aircraft,
                    flight.count,
                )
            squadron.untasked_aircraft -= take
            for pilot in flight.roster.iter_pilots():
                if pilot is not None and pilot in squadron.available_pilots:
                    squadron.available_pilots.remove(pilot)


def _key(package: Package) -> Hashable:
    target = package.target
    return package.primary_task, type(target), target.name


def restore_player_packages(ato: AirTaskingOrder, kept: list[Package]) -> int:
    """Put the kept packages back and drop the new duplicates. Returns the drops."""
    dropped = 0
    for package in kept:
        key = _key(package)
        for planned in ato.packages:
            if _key(planned) == key:
                ato.remove_package(planned)
                dropped += 1
                break
    for package in kept:
        ato.add_package(package)
    return dropped
