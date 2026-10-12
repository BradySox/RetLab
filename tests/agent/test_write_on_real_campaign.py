"""The outside AI's writes against a real campaign: what they leave behind.

``test_write_api`` pins the gates on fakes. These run the planner and the purchase
adapters on the shared ``campaign_game`` and check the three things a fake cannot:
that every aircraft and pilot a failed plan claimed is handed back, that the live
map is told about each change, and that a buy reports what it really bought. Each
test puts the campaign back as it found it.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterator

import pytest

from game.agent import planner, schemas, views
from game.ato.flight import Flight
from game.purchaseadapter import GroundUnitPurchaseAdapter, TransactionError
from game.server import EventStream
from game.theater.player import Player


@pytest.fixture
def pushed(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Every event the write path sends to the map."""
    events: list[Any] = []
    monkeypatch.setattr(EventStream, "put_nowait", staticmethod(events.append))
    return events


@pytest.fixture
def game(campaign_game: Any, pushed: list[Any]) -> Iterator[Any]:
    """The campaign with the AI planning red, and red's scripted plan set aside so a
    test's own packages are the only ones in the ATO."""
    red = campaign_game.red
    scripted = list(red.ato.packages)
    budget = red.budget
    red.ato.packages[:] = []
    campaign_game.settings.outside_ai_plans_red = True
    try:
        yield campaign_game
    finally:
        for package in list(red.ato.packages):
            red.ato.remove_package(package)
        red.ato.packages[:] = scripted
        red.budget = budget
        campaign_game.settings.outside_ai_plans_red = False


def _holdings(game: Any) -> tuple[int, int, int]:
    """Red's free aircraft, free pilots and flights on the books."""
    squadrons = list(game.red.air_wing.iter_squadrons())
    return (
        sum(s.untasked_aircraft for s in squadrons),
        sum(s.number_of_available_pilots for s in squadrons),
        len(game.db.flights.objects),
    )


def _red_base(game: Any) -> Any:
    return next(
        cp
        for cp in game.theater.controlpoints
        if cp.captured == Player.RED and list(cp.squadrons)
    )


def _barcap(game: Any, count: int = 2) -> schemas.PackageSpec:
    return schemas.PackageSpec(
        target_id=str(_red_base(game).id),
        flights=[schemas.FlightSpec(task="BARCAP", count=count)],
        ignore_range=True,
    )


def _create(game: Any) -> Any:
    result = planner.create_packages(game, "red", [_barcap(game)])[0]
    assert result.ok, result.error
    return game.red.ato.packages[-1]


def test_a_plan_that_raises_hands_back_its_aircraft_and_says_why(
    game: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(self: Flight, dump_debug_info: bool = False) -> None:
        raise RuntimeError

    before = _holdings(game)
    monkeypatch.setattr(Flight, "recreate_flight_plan", broken)

    created = planner.create_packages(game, "red", [_barcap(game)])[0]
    assert not created.ok
    assert "RuntimeError" in (created.error or "")
    assert _holdings(game) == before

    evaluated = planner.evaluate_package(game, "red", _barcap(game))
    assert not evaluated.ok
    assert "RuntimeError" in (evaluated.error or "")
    assert _holdings(game) == before
    assert game.red.ato.packages == []


@pytest.mark.parametrize("task", ["OCA_AIRCRAFT", "AIR_ASSAULT", "STRIKE"])
def test_a_task_the_target_does_not_take_is_refused(game: Any, task: str) -> None:
    base = _red_base(game)
    spec = schemas.PackageSpec(
        target_id=str(base.id),
        flights=[schemas.FlightSpec(task=task)],
        ignore_range=True,
    )
    before = _holdings(game)
    created = planner.create_packages(game, "red", [spec])[0]
    evaluated = planner.evaluate_package(game, "red", spec)
    for result in (created, evaluated):
        assert not result.ok
        assert f"{task} is not a mission for {base.name}" in (result.error or "")
        assert "BARCAP" in (result.error or "")
    assert _holdings(game) == before


def test_an_escort_is_not_held_to_the_targets_own_tasks(game: Any) -> None:
    base = _red_base(game)
    assert planner._task_problem("red", base, planner._flight_type("SEAD"), "sead") is (
        None
    )
    assert planner._task_problem("red", base, planner._flight_type("SEAD"), None)


def test_the_scripted_plan_passes_the_task_check(campaign_game: Any) -> None:
    # The check must never refuse a flight the game's own planner would build.
    checked = 0
    for side in ("red", "blue"):
        for package in views.coalition_for_side(campaign_game, side).ato.packages:
            for flight in package.flights:
                task = flight.flight_type
                assert planner._task_problem(side, package.target, task, None) is None
                checked += 1
    assert checked > 10


def test_creating_and_deleting_a_package_tells_the_map(
    game: Any, pushed: list[Any]
) -> None:
    before = _holdings(game)
    package = _create(game)
    flight_ids = {f.id for f in package.flights}
    assert flight_ids
    assert {f.id for f in pushed[-1].new_flights} == flight_ids

    done = planner.delete_package(game, "red", 0)
    assert done.ok
    # The flights must be named: an empty event leaves them drawn until a reload.
    assert pushed[-1].deleted_flights == flight_ids
    assert _holdings(game) == before


def test_clearing_the_plan_tells_the_map_about_every_flight(
    game: Any, pushed: list[Any]
) -> None:
    before = _holdings(game)
    flight_ids = {f.id for _ in range(2) for f in _create(game).flights}
    del pushed[:]

    assert planner.clear_packages(game, "red").ok
    deleted = set().union(*(event.deleted_flights for event in pushed))
    assert deleted == flight_ids
    assert _holdings(game) == before


def test_a_tot_too_large_to_hold_changes_nothing(game: Any) -> None:
    package = _create(game)
    tot, asap = package.time_over_target, package.auto_asap
    result = planner.set_package_tot(game, "red", 0, 10**12)
    assert not result.ok and "out of range" in (result.error or "")
    assert (package.time_over_target, package.auto_asap) == (tot, asap)


def test_a_package_that_launches_with_the_mission_is_inside_the_window(
    game: Any,
) -> None:
    """Test 56: the ASAP AWACS and tanker, 2 min before the turn clock, were each
    reported as "TOT +-2 min is after the 45 min the human plans to fly"."""
    package = _create(game)
    package.time_over_target = game.conditions.start_time - timedelta(minutes=2)
    result = planner.validate_plan(game, "red")
    check = result.packages[0]
    assert check.tot_minutes_into_mission == -2
    assert check.within_window
    assert not any("is after" in note for note in result.notes or [])


def test_a_tot_past_the_window_is_still_noted_with_one_sign(game: Any) -> None:
    package = _create(game)
    window = game.settings.desired_player_mission_duration
    package.time_over_target = (
        game.conditions.start_time + window + timedelta(minutes=5)
    )
    result = planner.validate_plan(game, "red")
    assert not result.packages[0].within_window
    late = [note for note in result.notes or [] if "is after" in note]
    assert len(late) == 1 and "TOT +" in late[0] and "+-" not in late[0]


def _recruiting_base(game: Any) -> Any:
    return next(
        cp
        for cp in game.theater.controlpoints
        if cp.captured == Player.RED and cp.has_ground_unit_source(game)
    )


def _ground_unit(game: Any) -> Any:
    return sorted(game.red.faction.frontline_units, key=lambda u: u.variant_id)[0]


def test_red_buys_ground_units_without_the_enemy_buy_cheat(
    game: Any, pushed: list[Any]
) -> None:
    assert not game.settings.enable_enemy_buy_sell
    cp, unit = _recruiting_base(game), _ground_unit(game)
    orders = cp.ground_unit_orders
    held = orders.pending_orders(unit)
    budget = game.red.budget = unit.price * 10.0
    try:
        result = planner.buy_ground(game, "red", str(cp.id), unit.variant_id, 2)
        assert result.ok, result.error
        assert orders.pending_orders(unit) == held + 2
        assert game.red.budget == budget - 2 * unit.price
        assert f"ordered 2 {unit.display_name}" in (result.detail or "")
        assert pushed, "the map is told the base's orders changed"
    finally:
        orders.sell({unit: orders.pending_orders(unit) - held})

    # The human's own path for red still needs the cheat.
    with pytest.raises(TransactionError):
        GroundUnitPurchaseAdapter(cp, game.red, game).buy(unit, 1)
    assert orders.pending_orders(unit) == held


def test_a_ground_buy_the_budget_cuts_short_says_how_many_went_through(
    game: Any,
) -> None:
    cp, unit = _recruiting_base(game), _ground_unit(game)
    orders = cp.ground_unit_orders
    held = orders.pending_orders(unit)
    game.red.budget = unit.price * 2.0
    try:
        result = planner.buy_ground(game, "red", str(cp.id), unit.variant_id, 5)
        assert result.ok
        assert "only 2 of the 5" in (result.detail or "")
        assert orders.pending_orders(unit) == held + 2
        assert game.red.budget == 0

        nothing = planner.buy_ground(game, "red", str(cp.id), unit.variant_id, 1)
        assert not nothing.ok and "Cannot buy" in (nothing.error or "")
    finally:
        orders.sell({unit: orders.pending_orders(unit) - held})


def test_an_aircraft_buy_the_budget_cuts_short_says_how_many_went_through(
    game: Any,
) -> None:
    red = views.coalition_for_side(game, "red")
    squadron = next(
        s
        for s in red.air_wing.iter_squadrons()
        if s.location.captured == Player.RED
        and s.aircraft.price > 0
        and s.has_aircraft_capacity_for(2)
        and s.location.unclaimed_parking(views._all_parking()) >= 2
    )
    pending = squadron.pending_deliveries
    game.red.budget = float(squadron.aircraft.price)
    try:
        result = planner.buy_aircraft(game, "red", str(squadron.id), 3)
        assert result.ok
        assert "only 1 of the 3" in (result.detail or "")
        assert squadron.pending_deliveries == pending + 1
        assert game.red.budget == 0

        sold = planner.sell_aircraft(game, "red", str(squadron.id), 1)
        assert sold.ok and "sold 1 " in (sold.detail or "")
        assert squadron.pending_deliveries == pending
    finally:
        squadron.pending_deliveries = pending


@pytest.mark.parametrize("quantity", [0, -3])
def test_a_quantity_below_one_is_refused(game: Any, quantity: int) -> None:
    cp, unit = _recruiting_base(game), _ground_unit(game)
    squadron = next(iter(game.red.air_wing.iter_squadrons()))
    budget = game.red.budget
    results = [
        planner.buy_ground(game, "red", str(cp.id), unit.variant_id, quantity),
        planner.buy_aircraft(game, "red", str(squadron.id), quantity),
        planner.sell_aircraft(game, "red", str(squadron.id), quantity),
    ]
    for result in results:
        assert not result.ok and "1 or more" in (result.error or "")
    assert game.red.budget == budget


def test_free_parking_is_served_only_for_reds_own_bases(campaign_game: Any) -> None:
    # Free parking counts aircraft on order, and blue's orders are blue's own.
    context = views.build_turn_context(campaign_game, "red")
    by_owner: dict[str, list[Any]] = {"red": [], "blue": []}
    for cp in context.control_points:
        if cp.parking_total:
            by_owner.setdefault(cp.owner, []).append(cp.parking_free)
    assert by_owner["red"] and all(free is not None for free in by_owner["red"])
    assert by_owner["blue"] and all(free is None for free in by_owner["blue"])


def test_every_task_the_read_side_suggests_passes_the_task_check(
    campaign_game: Any,
) -> None:
    targets = views.build_turn_context(campaign_game, "red").targets
    assert targets
    for target in targets:
        task = planner._flight_type(target.suggested_task)
        resolved = planner.resolve_target(campaign_game, target.id)
        assert planner._task_problem("red", resolved, task, None) is None, target
