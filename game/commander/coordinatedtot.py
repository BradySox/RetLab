"""Coordinated TOT: a hand-planned package timed behind its SEAD (§114).

The player's own packages used to be ASAP or a typed TOT, so a strike went in
whenever it could get there, ahead of the SEAD package hitting the SAM over its
target. Coordinated starts from ASAP and waits for the same window the AI's
strikes use (§69). With no window to make, it flies ASAP and says why.
docs/dev/design/retlab-coordinated-tot-notes.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Optional, TYPE_CHECKING

from game.ato.flighttype import FlightType
from game.ato.traveltime import TotEstimator
from game.theater.fogofwar import fog_intact
from game.theater.theatergroundobject import IadsGroundObject, TheaterGroundObject
from .missionscheduler import MissionScheduler, coordinated_strike_tot

if TYPE_CHECKING:
    from game import Game
    from game.ato import Package
    from game.theater import MissionTarget
    from game.theater.player import Player

SUPPRESSION_TASKS = frozenset({FlightType.SEAD, FlightType.DEAD})

#: A package carrying one of these brings its own suppression to the target.
ORGANIC_SUPPRESSION = frozenset(
    {FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.SEAD_SWEEP}
)


@dataclass
class CoordinatedTot:
    tot: datetime
    #: The SEAD/DEAD packages the TOT waits behind.
    behind: list[Package] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _clock(time: datetime) -> str:
    return f"{time:%H:%M}"


def _viewer(package: Package) -> Optional[Player]:
    # Only the blue map is fogged; red planning reads ground truth.
    player = package.flights[0].coalition.player
    return player if player.is_blue else None


def _known(tgo: TheaterGroundObject, viewer: Optional[Player]) -> bool:
    # fog_intact: the reveal overview is a display toggle and must not move a TOT.
    with fog_intact():
        return tgo.known_for(viewer)


def _ring_covers(site: MissionTarget, target: MissionTarget) -> bool:
    threat_range = getattr(site, "max_threat_range", None)
    if threat_range is None:
        return False
    ring = threat_range().meters
    return ring > 0 and site.position.distance_to_point(target.position) <= ring


def _covering_sams(
    package: Package, viewer: Optional[Player]
) -> list[IadsGroundObject]:
    owner = package.flights[0].coalition.player
    sams = []
    for cp in package.flights[0].coalition.game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if not isinstance(tgo, IadsGroundObject) or tgo.is_friendly(owner):
                continue
            if cp.captured.is_neutral:
                continue
            if tgo.is_dead() or not tgo.has_live_radar_sam:
                continue
            if _ring_covers(tgo, package.target) and _known(tgo, viewer):
                sams.append(tgo)
    return sams


def plan_coordinated_tot(
    package: Package,
    packages: Iterable[Package],
    now: datetime,
    mission_length: timedelta,
) -> CoordinatedTot:
    """The package's Coordinated TOT, never earlier than ASAP."""
    earliest = TotEstimator(package).earliest_tot(now)
    if (
        not package.flights
        or package.primary_task not in MissionScheduler.COORDINATED_STRIKE_TYPES
    ):
        return CoordinatedTot(earliest)
    viewer = _viewer(package)
    suppression = [
        p
        for p in packages
        if p is not package and p.flights and p.primary_task in SUPPRESSION_TASKS
    ]
    providers = [
        p
        for p in suppression
        if _ring_covers(p.target, package.target)
        and (not isinstance(p.target, TheaterGroundObject) or _known(p.target, viewer))
    ]
    result = CoordinatedTot(earliest)
    if providers:
        provider_tots = [p.time_over_target for p in providers]
        window_start = max(provider_tots) + MissionScheduler.SEAD_WINDOW_LEAD
        window_end = window_start + MissionScheduler.SEAD_WINDOW_DURATION
        moved = coordinated_strike_tot(
            earliest,
            earliest,
            provider_tots,
            MissionScheduler.SEAD_WINDOW_LEAD,
            MissionScheduler.SEAD_WINDOW_DURATION,
        )
        if moved is not None and moved > now + mission_length:
            result.warnings.append(
                f"The SEAD window opens at {_clock(window_start)}, after the "
                "mission ends. Flying ASAP."
            )
        elif moved is not None:
            result.tot = moved
            result.behind = providers
        elif earliest > window_end:
            result.warnings.append(
                f"The SEAD window closes at {_clock(window_end)}, before this "
                f"package can get there ({_clock(earliest)}). Flying ASAP."
            )
        else:
            result.behind = providers
    if not any(f.flight_type in ORGANIC_SUPPRESSION for f in package.flights):
        suppressed = {id(p.target) for p in suppression}
        for sam in _covering_sams(package, viewer):
            if id(sam) not in suppressed:
                result.warnings.append(
                    f"{sam.name}'s SAM ring covers the target and no SEAD or DEAD "
                    "package is planned against it."
                )
    return result


def apply_tot_mode(
    package: Package,
    packages: Iterable[Package],
    now: datetime,
    mission_length: timedelta,
) -> Optional[CoordinatedTot]:
    """Re-run the package's ASAP or Coordinated TOT; None for a typed TOT."""
    if package.auto_coordinated:
        plan = plan_coordinated_tot(package, packages, now, mission_length)
        package.time_over_target = plan.tot
        return plan
    if package.auto_asap:
        package.set_tot_asap(now)
    return None


def retime_coordinated_packages(game: Game) -> None:
    """Re-run every Coordinated package at Take Off, so later packages count.

    Suppression packages go first: a Coordinated SEAD package flies ASAP, and
    the strikes behind it need its final TOT.
    """
    for coalition in (game.blue, game.red):
        packages = list(coalition.ato.packages)
        timed = [
            p
            for p in packages
            if getattr(p, "auto_coordinated", False)
            and p.flights
            and p.all_flights_waiting_for_start()
        ]
        timed.sort(key=lambda p: p.primary_task not in SUPPRESSION_TASKS)
        for package in timed:
            apply_tot_mode(
                package,
                packages,
                game.conditions.start_time,
                game.settings.desired_player_mission_duration,
            )
