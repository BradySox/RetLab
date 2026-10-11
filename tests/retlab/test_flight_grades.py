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

    assert card.faults == ("Never reached the target (closest 40 NM).",)
    assert card.grade is Grade.BELOW_AVERAGE


def test_firing_from_range_is_not_failing_to_arrive() -> None:
    harpoons = replace(
        BASE,
        graded_on_target=True,
        place="the ingress point",
        planned_tot=1800.0,
        closest_approach_m=15 * 1852.0,
        shots=4,
    )

    card = grade_flight(harpoons)
    assert card.faults == ()
    assert card.lines == ("4 weapons released, 0 hits.",)
    assert grade_flight(replace(harpoons, shots=0)).faults == (
        "Never reached the ingress point (closest 15 NM).",
    )


def test_a_mission_that_ends_before_the_tot_is_not_graded_on_timing() -> None:
    card = grade_flight(
        replace(
            BASE,
            planned_tot=6095.0,
            closest_approach_m=94 * 1852.0,
            mission_end=4920.0,
        )
    )

    assert card.faults == ()
    assert card.lines == ("Mission ended before its time on target.",)
    assert card.grade is Grade.AVERAGE


def test_timing_names_where_it_was_measured() -> None:
    on_station = replace(
        BASE, place="its station", planned_tot=1800.0, closest_approach_m=0.0
    )

    assert grade_flight(replace(on_station, arrival=1800.0)).lines == (
        "On time at its station.",
    )
    assert grade_flight(replace(on_station, arrival=2400.0)).faults == (
        "At its station 10 min late.",
    )


def test_a_ship_sunk_lifts_an_anti_ship_flight() -> None:
    card = grade_flight(
        replace(BASE, graded_on_naval_kills=True, naval_kills=1, shots=4, hits=3)
    )
    assert card.grade is Grade.AVERAGE
    on_time = replace(
        BASE,
        graded_on_naval_kills=True,
        naval_kills=1,
        planned_tot=1800.0,
        arrival=1800.0,
        closest_approach_m=0.0,
    )
    assert grade_flight(on_time).grade is Grade.ABOVE_AVERAGE
    # Not for a task that is not graded on it.
    assert grade_flight(replace(on_time, graded_on_naval_kills=False)).grade is (
        Grade.AVERAGE
    )


def test_a_ground_kill_lifts_a_cas_flight() -> None:
    cas = replace(
        BASE,
        graded_on_ground_kills=True,
        planned_tot=1800.0,
        arrival=1800.0,
        closest_approach_m=0.0,
    )

    assert grade_flight(cas).grade is Grade.AVERAGE
    assert grade_flight(replace(cas, ground_kills=3)).grade is Grade.ABOVE_AVERAGE


def test_the_result_is_credited_once() -> None:
    both = replace(
        BASE,
        graded_on_target=True,
        graded_on_naval_kills=True,
        target_name="Ship group",
        target_total=2,
        target_killed=2,
        naval_kills=2,
    )

    assert grade_flight(both).grade is Grade.AVERAGE


def test_sead_is_not_faulted_when_the_site_survives() -> None:
    sead = replace(
        BASE,
        graded_on_target=True,
        target_may_survive=True,
        target_name="SA-6",
        target_total=6,
        shots=4,
    )

    quiet = grade_flight(sead)
    assert quiet.faults == ()
    assert "Package target SA-6: 0 of 6 destroyed." in quiet.lines
    assert quiet.grade is Grade.AVERAGE
    one_radar = replace(
        sead,
        target_killed=1,
        hits=1,
        planned_tot=1800.0,
        arrival=1800.0,
        closest_approach_m=0.0,
    )
    assert grade_flight(one_radar).grade is Grade.ABOVE_AVERAGE


def test_no_hits_is_a_fault_only_for_a_task_graded_on_hits() -> None:
    bombs = replace(BASE, graded_on_target=True, graded_on_hits=True, shots=4)

    missed = grade_flight(bombs)
    assert missed.faults == ("Released 4 weapons with no hits.",)
    assert missed.lines == ()
    # Standoff tasks, and any flight with a kill to show for it.
    assert grade_flight(replace(bombs, graded_on_hits=False)).faults == ()
    killed = grade_flight(replace(bombs, ground_kills=1))
    assert killed.faults == ()
    assert "4 weapons released, 0 hits." in killed.lines


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
            graded_on_hits=True,
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


def test_landing_under_the_measured_reserve_is_a_fault() -> None:
    hornet = replace(BASE, fuel_capacity_lb=10_800.0, reserve_lb=2_000.0)

    short = grade_flight(replace(hornet, landed_fuel=0.13))
    assert short.faults == ("Landed with 1,404 lb (reserve 2,000 lb).",)
    assert short.grade is Grade.BELOW_AVERAGE

    fine = grade_flight(replace(hornet, landed_fuel=0.25))
    assert fine.faults == ()
    assert fine.lines == ("Landed with 2,700 lb (reserve 2,000 lb).",)


def test_an_unmeasured_airframe_falls_back_to_a_share_of_internal_fuel() -> None:
    assert grade_flight(replace(BASE, landed_fuel=0.10)).faults == (
        "Landed with 10% fuel (reserve 15%).",
    )
    assert grade_flight(replace(BASE, landed_fuel=0.30)).faults == ()


class _Hornet:
    dcs_unit_type = SimpleNamespace(fuel_max=4900.0)
    fuel_consumption = SimpleNamespace(min_safe=2000)

    def __str__(self) -> str:
        return "F/A-18C"


def _flight(flight_type: FlightType, tot: datetime | None) -> Any:
    waypoint = SimpleNamespace(position=SimpleNamespace(x=100_000.0, y=0.0))
    plan = SimpleNamespace(tot_waypoint=waypoint, tot_for_waypoint=lambda waypoint: tot)
    return SimpleNamespace(
        flight_type=flight_type,
        task_display_name=flight_type.value,
        count=2,
        unit_type=_Hornet(),
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
        last_airborne=2370.0,
        shots=2,
        hits=1,
        air_kills=1,
    )

    facts = facts_for(flight, [lead], _debriefing([]), start)

    assert facts.planned_tot == 1800.0
    assert facts.arrival == 1830.0
    assert facts.graded_on_air_kills
    assert facts.landed_fuel == 0.2
    assert facts.reserve_lb == 2000.0
    assert facts.fuel_capacity_lb is not None
    assert round(facts.fuel_capacity_lb) == 10803
    assert (facts.shots, facts.hits, facts.air_kills) == (2, 1, 1)


def test_a_dead_or_ejected_human_has_no_fuel_to_grade() -> None:
    flight = _flight(FlightType.BARCAP, None)
    dead = _record(
        "Enfield 1-1", _sample(0.0, 0.0, fuel=0.01), player=True, last_airborne=100.0
    )
    ejected = _record(
        "Enfield 1-2",
        _sample(0.0, 0.0, fuel=0.02),
        player=True,
        ejected=True,
        last_airborne=100.0,
    )

    facts = facts_for(
        flight, [dead, ejected], _debriefing(["Enfield 1-1"], flight), None
    )

    assert facts.landed_fuel is None
    assert facts.lost == 1
    assert facts.ejected == 1
    assert facts.planned_tot is None


def test_an_ai_flight_never_grades_fuel() -> None:
    """AI can fly on unlimited fuel, so its fuel field is not a fuel state (§91)."""
    flight = _flight(FlightType.BARCAP, None)
    anchor = _record("Enfield 1-1", _sample(0.0, 0.0, fuel=1.0))

    assert facts_for(flight, [anchor], _debriefing([]), None).landed_fuel is None


def test_a_human_still_airborne_at_mission_end_has_no_landing_fuel() -> None:
    flight = _flight(FlightType.BARCAP, None)
    airborne = _record(
        "Enfield 1-1",
        _sample(0.0, 0.0, fuel=0.4),
        player=True,
        last_seen=3600.0,
        last_airborne=3600.0,
    )

    assert facts_for(flight, [airborne], _debriefing([]), None).landed_fuel is None


def test_a_card_leads_with_the_job_and_names_the_squadron() -> None:
    card = grade_flight(
        replace(BASE, squadron='VFA-103 "Jolly Rogers"', package_target="Senaki")
    )
    assert card.headline == f"{BASE.task} · Senaki"
    assert card.detail == f'VFA-103 "Jolly Rogers" · {BASE.aircraft}'


def test_a_card_from_an_older_save_still_has_a_title() -> None:
    card = grade_flight(BASE)
    old = object.__new__(type(card))
    old.__dict__.update(
        {k: v for k, v in card.__dict__.items() if k not in ("squadron", "target")}
    )
    assert old.headline == BASE.task
    assert old.detail == f"{BASE.name} · {BASE.aircraft}"


def test_facts_carry_the_squadron_and_the_package_target() -> None:
    flight = _flight(FlightType.BARCAP, None)
    flight.squadron = "VF-103"
    flight.package.target = SimpleNamespace(name="Kutaisi")
    record = _record("Enfield 1-1", _sample(0.0, 0.0))
    facts = facts_for(flight, [record], _debriefing([]), None)
    assert (facts.squadron, facts.package_target) == ("VF-103", "Kutaisi")


def _attack_flight(flight_type: FlightType, start: datetime) -> Any:
    flight = _flight(flight_type, start + timedelta(minutes=40))
    ingress = SimpleNamespace(position=SimpleNamespace(x=50_000.0, y=0.0))
    join = SimpleNamespace(position=SimpleNamespace(x=20_000.0, y=0.0))
    times = {id(ingress): timedelta(minutes=30), id(join): timedelta(minutes=20)}
    flight.flight_plan.layout = SimpleNamespace(ingress=ingress, join=join)
    flight.flight_plan.tot_for_waypoint = lambda waypoint: (
        start + times.get(id(waypoint), timedelta(minutes=40))
    )
    return flight


def test_an_attack_flight_is_timed_at_its_ingress_point() -> None:
    start = datetime(2026, 10, 11, 8, 0)
    flight = _attack_flight(FlightType.ANTISHIP, start)
    # Fires 10 NM short of the ingress point and turns for home.
    lead = _record(
        "Enfield 1-1",
        _sample(0.0, 0.0),
        _sample(1800.0, 50_000.0 - 10 * 1852.0),
        _sample(3000.0, 0.0),
        shots=4,
    )

    facts = facts_for(flight, [lead], _debriefing([]), start, 3000.0)

    assert facts.place == "the ingress point"
    assert (facts.planned_tot, facts.arrival) == (1800.0, 1800.0)
    assert facts.graded_on_naval_kills and not facts.graded_on_hits
    assert facts.mission_end == 3000.0
    assert grade_flight(facts).lines[0] == "On time at the ingress point."


def test_an_escort_is_timed_at_the_join_point() -> None:
    start = datetime(2026, 10, 11, 8, 0)
    flight = _attack_flight(FlightType.ESCORT, start)
    lead = _record("Enfield 1-1", _sample(0.0, 0.0), _sample(1200.0, 20_000.0))

    facts = facts_for(flight, [lead], _debriefing([]), start)

    assert facts.place == "the join point"
    assert (facts.planned_tot, facts.arrival) == (1200.0, 1200.0)
    for task in (FlightType.SEAD_ESCORT, FlightType.ESCORT_JAMMER):
        jammer = facts_for(_attack_flight(task, start), [lead], _debriefing([]), start)
        assert jammer.place == "the join point"


def test_a_patrol_is_timed_at_its_station() -> None:
    start = datetime(2026, 10, 11, 8, 0)
    flight = _flight(FlightType.BARCAP, start + timedelta(minutes=30))
    lead = _record("Enfield 1-1", _sample(0.0, 0.0), _sample(1500.0, 100_000.0))

    facts = facts_for(flight, [lead], _debriefing([]), start)

    assert facts.place == "its station"
    assert grade_flight(facts).lines == ("On time at its station.",)


def test_bombs_are_graded_on_hits_and_sead_may_leave_the_site_standing() -> None:
    start = datetime(2026, 10, 11, 8, 0)
    record = _record("Enfield 1-1", _sample(0.0, 0.0))

    strike = facts_for(
        _attack_flight(FlightType.STRIKE, start), [record], _debriefing([]), start
    )
    sead = facts_for(
        _attack_flight(FlightType.SEAD, start), [record], _debriefing([]), start
    )
    cas = facts_for(_flight(FlightType.CAS, None), [record], _debriefing([]), start)

    assert strike.graded_on_hits and not strike.target_may_survive
    assert sead.target_may_survive and not sead.graded_on_hits
    assert cas.graded_on_ground_kills and not cas.graded_on_target


def test_a_flight_still_at_the_point_at_the_planned_time_was_on_time() -> None:
    start = datetime(2026, 10, 11, 8, 0)
    flight = _flight(FlightType.STRIKE, start + timedelta(minutes=30))
    # Takes off inside the radius and is still there 30 minutes later.
    holding = _record(
        "Enfield 1-1",
        _sample(0.0, 100_000.0),
        _sample(900.0, 101_000.0),
        _sample(1800.0, 100_000.0),
        _sample(2400.0, 0.0),
    )
    passing = _record(
        "Enfield 1-1",
        _sample(0.0, 0.0),
        _sample(900.0, 100_000.0),
        _sample(1800.0, 0.0),
    )

    assert facts_for(flight, [holding], _debriefing([]), start).arrival == 1800.0
    assert facts_for(flight, [passing], _debriefing([]), start).arrival == 900.0


def test_one_weapon_is_singular() -> None:
    assert grade_flight(replace(BASE, shots=1, hits=1)).lines == (
        "1 weapon released, 1 hit.",
    )
