from dataclasses import replace
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.retlab.flight_grades import (
    ARRIVAL_RADIUS_M,
    FlightFacts,
    Grade,
    facts_for,
    grade_flight,
)
from game.sortierecord import SortieRecord, TrackSample

BASE = FlightFacts(
    name="Enfield 1",
    task="Strike",
    aircraft="2 x F/A-18C",
    player=True,
    size=2,
)


def _sample(time: float, x: float, fuel: float = 0.5) -> TrackSample:
    return TrackSample(time=time, x=x, y=0.0, altitude=5000.0, fuel=fuel)


def _record(unit: str, *samples: TrackSample, **overrides: Any) -> SortieRecord:
    fields: dict[str, Any] = dict(
        unit=unit,
        group="Enfield 1",
        unit_type="FA-18C_hornet",
        coalition=2,
        first_seen=0.0,
        last_seen=3600.0,
        track=tuple(samples),
        shots=0,
        hits=0,
        ejected=False,
    )
    fields.update(overrides)
    return SortieRecord(**fields)


def test_a_clean_strike_is_above_average() -> None:
    card = grade_flight(
        replace(
            BASE,
            graded_on_target=True,
            planned_tot=1800.0,
            arrival=1860.0,
            closest_approach_m=500.0,
            target_name="Senaki SAM",
            target_total=4,
            target_killed=3,
            shots=4,
            hits=3,
        )
    )

    assert card.grade is Grade.ABOVE_AVERAGE
    assert card.faults == ()
    assert "On time at the target." in card.lines
    assert "Package target Senaki SAM: 3 of 4 destroyed." in card.lines


def test_late_past_five_minutes_is_a_fault() -> None:
    card = grade_flight(
        replace(BASE, planned_tot=1800.0, arrival=2400.0, closest_approach_m=0.0)
    )

    assert card.faults == ("At the target 10 min late.",)
    assert card.grade is Grade.BELOW_AVERAGE


def test_a_few_minutes_late_is_noted_not_faulted() -> None:
    card = grade_flight(
        replace(BASE, planned_tot=1800.0, arrival=2040.0, closest_approach_m=0.0)
    )

    assert card.faults == ()
    assert card.lines == ("At the target 4 min late.",)


def test_early_is_fine_for_a_station_task_but_not_a_strike() -> None:
    early = replace(BASE, planned_tot=1800.0, arrival=900.0, closest_approach_m=0.0)

    assert grade_flight(early).faults == ("At the target 15 min early.",)
    assert grade_flight(replace(early, early_is_fine=True)).faults == ()


def test_never_reaching_the_target_names_the_closest_approach() -> None:
    card = grade_flight(
        replace(BASE, planned_tot=1800.0, closest_approach_m=40 * 1852.0)
    )

    assert card.faults == ("Never reached the target area (closest 40 NM).",)


def test_timing_is_not_graded_without_a_track_or_a_timed_tot() -> None:
    assert grade_flight(replace(BASE, planned_tot=1800.0)).lines == ()
    assert grade_flight(replace(BASE, closest_approach_m=0.0)).lines == ()


def test_losing_half_the_flight_with_the_target_untouched_is_unsat() -> None:
    card = grade_flight(
        replace(
            BASE,
            graded_on_target=True,
            target_name="Bridge",
            target_total=1,
            target_killed=0,
            shots=4,
            hits=0,
            lost=1,
        )
    )

    assert card.grade is Grade.UNSAT
    assert card.faults == (
        "Package target Bridge untouched.",
        "Released 4 weapons with no hits.",
        "Lost 1 of 2 aircraft.",
    )


def test_air_kills_lift_a_fighter_task() -> None:
    card = grade_flight(replace(BASE, air_kills=2, graded_on_air_kills=True))

    assert card.lines == ("Kills: 2 air.",)
    assert card.grade is Grade.AVERAGE


def test_fuel_is_a_fault_only_on_fumes() -> None:
    assert grade_flight(replace(BASE, lowest_fuel=0.03)).faults == (
        "Finished the sortie with 3% fuel.",
    )
    low = grade_flight(replace(BASE, lowest_fuel=0.10))
    assert low.faults == ()
    assert low.lines == ("Finished the sortie with 10% fuel.",)


def _flight(flight_type: FlightType, tot: datetime | None) -> Any:
    waypoint = SimpleNamespace(position=SimpleNamespace(x=100_000.0, y=0.0))
    plan = SimpleNamespace(tot_waypoint=waypoint, tot_for_waypoint=lambda waypoint: tot)
    return SimpleNamespace(
        flight_type=flight_type,
        task_display_name=flight_type.value,
        count=2,
        unit_type="F/A-18C",
        flight_plan=plan,
        package=SimpleNamespace(target=None),
    )


def _debriefing(killed: list[str], lost_flight: Any = None) -> Any:
    losses = [SimpleNamespace(flight=lost_flight)] if lost_flight else []
    return SimpleNamespace(
        state_data=SimpleNamespace(killed_aircraft=killed),
        air_losses=SimpleNamespace(losses=losses),
    )


def test_facts_time_the_arrival_against_mission_start() -> None:
    start = datetime(2026, 9, 29, 8, 0)
    flight = _flight(FlightType.SWEEP, start + timedelta(minutes=30))
    lead = _record(
        "Enfield 1-1",
        _sample(0.0, 0.0),
        _sample(1830.0, 100_000.0 - ARRIVAL_RADIUS_M + 10.0),
        _sample(2400.0, 0.0, fuel=0.2),
        player=True,
        shots=2,
        hits=1,
        air_kills=1,
    )

    facts = facts_for(flight, [lead], _debriefing([]), start)

    assert facts.planned_tot == 1800.0
    assert facts.arrival == 1830.0
    assert facts.graded_on_air_kills
    assert facts.lowest_fuel == 0.2
    assert (facts.shots, facts.hits, facts.air_kills) == (2, 1, 1)


def test_a_dead_or_ejected_human_has_no_fuel_to_grade() -> None:
    flight = _flight(FlightType.BARCAP, None)
    dead = _record("Enfield 1-1", _sample(0.0, 0.0, fuel=0.01), player=True)
    ejected = _record(
        "Enfield 1-2", _sample(0.0, 0.0, fuel=0.02), player=True, ejected=True
    )

    facts = facts_for(
        flight, [dead, ejected], _debriefing(["Enfield 1-1"], flight), None
    )

    assert facts.lowest_fuel is None
    assert facts.lost == 1
    assert facts.ejected == 1
    assert facts.planned_tot is None


def test_an_ai_flight_never_grades_fuel() -> None:
    """AI can fly on unlimited fuel, so its fuel field is not a fuel state (§91)."""
    flight = _flight(FlightType.BARCAP, None)
    anchor = _record("Enfield 1-1", _sample(0.0, 0.0, fuel=1.0))

    assert facts_for(flight, [anchor], _debriefing([]), None).lowest_fuel is None
