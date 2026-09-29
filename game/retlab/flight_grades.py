"""§108: a report card per blue flight, graded from what the mission recorded.

Reads §91's sortie records against the flight plan: timing at the TOT waypoint,
the package target, weapons, losses, and a human pilot's fuel on landing.
Computed at results commit, while the flown ATO still exists, and shown in the
debrief. Nothing reads a grade back; it never changes the campaign.
docs/dev/design/retlab-flight-report-cards-notes.md.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Iterable, Optional, Sequence

from game.ato.flighttype import FlightType

if TYPE_CHECKING:
    from game import Game
    from game.ato import Flight
    from game.debriefing import AirLosses, Debriefing
    from game.sortierecord import SortieRecord

#: A flight "reached the target" when a track sample falls inside this.
ARRIVAL_RADIUS_M = 5 * 1852.0
#: On time within this; the 30 s sample interval is inside it.
ON_TIME_S = 150.0
#: Late (or early) past ON_TIME_S but within this is a note, not a fault.
LATE_FAULT_S = 300.0
#: Landing reserve as a share of internal fuel for an airframe with no measured
#: `min_safe`. The measured Hornet and Viper reserves are about 18% and 14%.
FALLBACK_RESERVE = 0.15
KG_PER_LB = 0.45359237

#: Tasks graded on the package's ground target.
ATTACK_TASKS = frozenset(
    {
        FlightType.STRIKE,
        FlightType.BAI,
        FlightType.DEAD,
        FlightType.SEAD,
        FlightType.ANTISHIP,
        FlightType.OCA_RUNWAY,
        FlightType.OCA_AIRCRAFT,
        FlightType.ARMED_RECON,
    }
)
#: Tasks graded on air kills.
AIR_TASKS = frozenset(
    {
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.ESCORT,
        FlightType.SWEEP,
        FlightType.INTERCEPTION,
    }
)
#: Being on station early is fine; only late is graded.
STATION_TASKS = frozenset(
    {
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.AEWC,
        FlightType.REFUELING,
        FlightType.JAMMING,
    }
)


class Grade(Enum):
    UNSAT = "Unsat"
    BELOW_AVERAGE = "Below average"
    AVERAGE = "Average"
    ABOVE_AVERAGE = "Above average"


def grade_for(score: int) -> Grade:
    if score >= 2:
        return Grade.ABOVE_AVERAGE
    if score >= 0:
        return Grade.AVERAGE
    if score >= -2:
        return Grade.BELOW_AVERAGE
    return Grade.UNSAT


@dataclass(frozen=True)
class FlightFacts:
    """Everything the grader needs, gathered from the game and the debriefing."""

    name: str
    task: str
    aircraft: str
    player: bool
    size: int
    lost: int = 0
    ejected: int = 0
    shots: int = 0
    hits: int = 0
    air_kills: int = 0
    ground_kills: int = 0
    naval_kills: int = 0
    graded_on_target: bool = False
    graded_on_air_kills: bool = False
    early_is_fine: bool = False
    #: Seconds after mission start; None when the plan has no timed TOT.
    planned_tot: Optional[float] = None
    #: First sample inside ARRIVAL_RADIUS_M; None when it never got there.
    arrival: Optional[float] = None
    #: Closest sampled approach to the TOT waypoint; None with no track.
    closest_approach_m: Optional[float] = None
    target_name: str = ""
    target_total: int = 0
    target_killed: int = 0
    #: Lowest internal-fuel share among human jets that landed; None for AI.
    landed_fuel: Optional[float] = None
    #: Internal fuel capacity and measured landing reserve, in pounds.
    fuel_capacity_lb: Optional[float] = None
    reserve_lb: Optional[float] = None


@dataclass(frozen=True)
class FlightCard:
    name: str
    task: str
    aircraft: str
    player: bool
    grade: Grade
    lines: tuple[str, ...]
    faults: tuple[str, ...]

    @property
    def title(self) -> str:
        return f"{self.name}: {self.task}, {self.aircraft}"


def _minutes(seconds: float) -> str:
    whole = int(round(abs(seconds) / 60.0))
    return f"{whole} min"


def grade_flight(facts: FlightFacts) -> FlightCard:
    score = 0
    lines: list[str] = []
    faults: list[str] = []

    if facts.planned_tot is not None and facts.closest_approach_m is not None:
        if facts.arrival is None:
            nm = facts.closest_approach_m / 1852.0
            faults.append(f"Never reached the target area (closest {nm:.0f} NM).")
            score -= 2
        else:
            delta = facts.arrival - facts.planned_tot
            late = delta > 0
            off = delta if late else (0.0 if facts.early_is_fine else -delta)
            if off <= ON_TIME_S:
                lines.append("On time at the target.")
                score += 1
            else:
                word = "late" if late else "early"
                text = f"At the target {_minutes(off)} {word}."
                if off <= LATE_FAULT_S:
                    lines.append(text)
                else:
                    faults.append(text)
                    score -= 1

    if facts.graded_on_target and facts.target_total > 0:
        text = (
            f"Package target {facts.target_name}: {facts.target_killed} of "
            f"{facts.target_total} destroyed."
        )
        if facts.target_killed * 2 >= facts.target_total:
            lines.append(text)
            score += 1
        elif facts.target_killed > 0:
            lines.append(text)
        else:
            faults.append(f"Package target {facts.target_name} untouched.")
            score -= 1

    kills = []
    for count, kind in (
        (facts.air_kills, "air"),
        (facts.ground_kills, "ground"),
        (facts.naval_kills, "naval"),
    ):
        if count:
            kills.append(f"{count} {kind}")
    if kills:
        lines.append(f"Kills: {', '.join(kills)}.")
    if facts.graded_on_air_kills and facts.air_kills > 0:
        score += 1

    if facts.shots:
        hits = "hit" if facts.hits == 1 else "hits"
        lines.append(f"{facts.shots} weapons released, {facts.hits} {hits}.")
        if facts.graded_on_target and facts.shots >= 2 and facts.hits == 0:
            faults.append(f"Released {facts.shots} weapons with no hits.")
            score -= 1

    if facts.lost:
        faults.append(f"Lost {facts.lost} of {facts.size} aircraft.")
        score -= 2 if facts.lost * 2 >= facts.size else 1
    if facts.ejected:
        lines.append(f"{facts.ejected} ejected.")

    if facts.landed_fuel is not None:
        capacity = facts.fuel_capacity_lb
        if capacity and facts.reserve_lb is not None:
            reserve = facts.reserve_lb
            landed = facts.landed_fuel * capacity
            text = f"Landed with {landed:,.0f} lb (reserve {reserve:,.0f} lb)."
        else:
            reserve = FALLBACK_RESERVE
            landed = facts.landed_fuel
            percent = int(round(landed * 100))
            text = f"Landed with {percent}% fuel (reserve {int(reserve * 100)}%)."
        if landed < reserve:
            faults.append(text)
            score -= 1
        else:
            lines.append(text)

    return FlightCard(
        name=facts.name,
        task=facts.task,
        aircraft=facts.aircraft,
        player=facts.player,
        grade=grade_for(score),
        lines=tuple(lines),
        faults=tuple(faults),
    )


def _arrival(
    records: Sequence[SortieRecord], x: float, y: float
) -> tuple[Optional[float], Optional[float]]:
    arrival: Optional[float] = None
    closest: Optional[float] = None
    for record in records:
        for sample in record.track:
            distance = math.hypot(sample.x - x, sample.y - y)
            if closest is None or distance < closest:
                closest = distance
            if distance <= ARRIVAL_RADIUS_M and (
                arrival is None or sample.time < arrival
            ):
                arrival = sample.time
    return arrival, closest


def _target_counts(flight: Flight, debriefing: Debriefing) -> tuple[str, int, int]:
    from game.theater.theatergroundobject import TheaterGroundObject

    target = flight.package.target
    if not isinstance(target, TheaterGroundObject):
        return "", 0, 0
    killed = {
        id(mapping.theater_unit)
        for mapping in debriefing.ground_object_losses
        if mapping.theater_unit.ground_object is target
    }
    killed |= {
        id(mapping.ground_unit)
        for mapping in debriefing.scenery_object_losses
        if mapping.ground_unit.ground_object is target
    }
    alive = {id(unit) for unit in target.units if unit.alive}
    return target.name, len(alive | killed), len(killed)


def _landed(record: SortieRecord) -> bool:
    """Seen on the ground on a sweep after its last airborne one."""
    return (
        record.last_airborne is not None
        and record.last_airborne >= 0
        and record.last_seen > record.last_airborne
    )


def _fuel_capacity_lb(flight: Flight) -> Optional[float]:
    try:
        kg = float(flight.unit_type.dcs_unit_type.fuel_max)
    except (AttributeError, TypeError, ValueError):
        return None
    return kg / KG_PER_LB if kg > 0 else None


def _reserve_lb(flight: Flight) -> Optional[float]:
    consumption = getattr(flight.unit_type, "fuel_consumption", None)
    return None if consumption is None else float(consumption.min_safe)


def _task_name(flight: Flight) -> str:
    try:
        return str(flight.task_display_name)
    except Exception:
        return flight.flight_type.value


def facts_for(
    flight: Flight,
    records: Sequence[SortieRecord],
    debriefing: Debriefing,
    mission_start: Optional[datetime],
) -> FlightFacts:
    # getattr: mypy cannot infer Debriefing.air_losses through the import cycle.
    air_losses: AirLosses = getattr(debriefing, "air_losses")
    lost = len([loss for loss in air_losses.losses if loss.flight is flight])
    killed = set(debriefing.state_data.killed_aircraft)
    human_survivors = [
        record
        for record in records
        if record.player and not record.ejected and record.unit not in killed
    ]
    fuel = [
        record.fuel_at_end
        for record in human_survivors
        if record.fuel_at_end is not None and _landed(record)
    ]

    planned_tot: Optional[float] = None
    arrival: Optional[float] = None
    closest: Optional[float] = None
    try:
        waypoint = flight.flight_plan.tot_waypoint
        tot = flight.flight_plan.tot_for_waypoint(waypoint)
        if tot is not None and mission_start is not None:
            planned_tot = (tot - mission_start).total_seconds()
            arrival, closest = _arrival(
                records, waypoint.position.x, waypoint.position.y
            )
    except Exception:
        logging.debug("No TOT to grade for %s", flight, exc_info=True)

    graded_on_target = flight.flight_type in ATTACK_TASKS
    target_name, target_total, target_killed = (
        _target_counts(flight, debriefing) if graded_on_target else ("", 0, 0)
    )

    return FlightFacts(
        name=records[0].group,
        task=_task_name(flight),
        aircraft=f"{flight.count} x {flight.unit_type}",
        player=any(record.player for record in records),
        size=flight.count,
        lost=lost,
        ejected=sum(1 for record in records if record.ejected),
        shots=sum(record.shots for record in records),
        hits=sum(record.hits for record in records),
        air_kills=sum(record.air_kills for record in records),
        ground_kills=sum(record.ground_kills for record in records),
        naval_kills=sum(record.naval_kills for record in records),
        graded_on_target=graded_on_target,
        graded_on_air_kills=flight.flight_type in AIR_TASKS,
        early_is_fine=flight.flight_type in STATION_TASKS,
        planned_tot=planned_tot,
        arrival=arrival,
        closest_approach_m=closest,
        target_name=target_name,
        target_total=target_total,
        target_killed=target_killed,
        landed_fuel=min(fuel) if fuel else None,
        fuel_capacity_lb=_fuel_capacity_lb(flight),
        reserve_lb=_reserve_lb(flight),
    )


def _blue_flights(
    records: Iterable[SortieRecord], debriefing: Debriefing
) -> dict[int, tuple[Flight, list[SortieRecord]]]:
    by_flight: dict[int, tuple[Flight, list[SortieRecord]]] = {}
    for record in records:
        if record.coalition != 2:
            continue
        flying = debriefing.unit_map.flight(record.unit)
        if flying is None:
            continue
        entry = by_flight.setdefault(id(flying.flight), (flying.flight, []))
        entry[1].append(record)
    return by_flight


def flight_cards(game: Game, debriefing: Debriefing) -> list[FlightCard]:
    """One card per blue flight that got airborne, human-crewed flights first."""
    from game.sim.missionstart import mission_start_time

    records = getattr(debriefing.state_data, "sortie_records", ())
    if not records:
        return []
    try:
        mission_start: Optional[datetime] = mission_start_time(game)
    except Exception:
        logging.exception("Could not work out mission start for flight grades")
        mission_start = None

    cards = []
    for flight, flight_records in _blue_flights(records, debriefing).values():
        if not any(record.flew for record in flight_records):
            continue
        try:
            facts = facts_for(flight, flight_records, debriefing, mission_start)
        except Exception:
            logging.exception("Could not grade %s", flight)
            continue
        cards.append(grade_flight(facts))
    cards.sort(key=lambda card: (not card.player, card.name))
    return cards
