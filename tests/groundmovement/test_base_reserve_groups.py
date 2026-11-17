"""Base stock becomes one counted, persistent and combat-capable detachment."""

from __future__ import annotations

from itertools import count
from dataclasses import replace
import pickle
from types import SimpleNamespace
from typing import Any

from dcs import Point
import pytest
from shapely.geometry import MultiPolygon, Point as MapPoint, box

from game.dcs.groundunittype import GroundUnitType
from game.groundmovement.base import (
    dispatch_base_movement,
    formation,
    preview_base_movement,
)
from game.groundmovement.dispatch import (
    advance_armor,
    dispatch_armor,
    rehome_before_capture,
    stop_armor,
)
from game.groundmovement.orders import (
    DestinationKind,
    GroundPosition as P,
    MovementSource,
)
from game.groundmovement.planning import movement_destination
from game.sim.gameupdateevents import GameUpdateEvents
from game.theater.player import Player
from tests.groundmovement.test_armor_movement_dispatch import native
from tests.groundmovement.test_armor_movement_planning import world  # noqa: F401
from tests.groundmovement.test_armor_movement_planning import landmap


def faction_for(player: Player) -> Any:
    return SimpleNamespace(
        ground_units={
            GroundUnitType.named(n)
            for n in ("M1A2 Abrams", "Truck Ural-375", "AAA ZU-23 Emplacement")
        }
    )


def has_path(*args: Any) -> bool:
    return True


def network_for(owner: Player) -> Any:
    return SimpleNamespace(has_path_between=has_path)


@pytest.fixture
def stock(world: Any) -> Any:
    world.a.base.commission_units(
        {world.units[7]: 4, world.units[5]: 3, world.units[1]: 2}
    )
    world.a.coalition.transfers = []
    world.b.coalition.transfers = []
    world.game.next_unit_id = count(1000).__next__
    world.game.next_group_id = count(100).__next__
    world.game.faction_for = faction_for
    world.game.transit_network_for = network_for
    return world


def send(w: Any) -> Any:
    return dispatch_base_movement(
        w.game,
        w.a.id,
        Player.BLUE,
        {w.units[7]: 1, w.units[1]: 1},
        P(80, 10),
        GameUpdateEvents(),
    )


def test_preview_is_read_only_and_adds_owned_tractors(stock: Any) -> None:
    before = pickle.dumps(stock.game)
    result = preview_base_movement(
        stock.game, stock.a.id, Player.BLUE, {stock.units[1]: 2}, P(80, 10)
    )
    assert dict(result.units) == {
        stock.units[1].variant_id: 2,
        stock.units[5].variant_id: 2,
    }
    assert dict(result.automatically_added) == {stock.units[5].variant_id: 2}
    assert len(result.manifest.towing) == 2
    assert pickle.dumps(stock.game) == before


def test_reserve_departure_uses_access_outside_excluded_base_marker(stock: Any) -> None:
    w = stock
    terrain = w.game.theater.terrain
    w.a.convoy_routes[w.b] = (Point(20, 0, terrain), w.b.position)
    w.b.convoy_routes[w.a] = tuple(reversed(w.a.convoy_routes[w.b]))
    w.game.theater.landmap = landmap(box(-5, -5, 5, 5))
    preview = preview_base_movement(
        w.game, w.a.id, Player.BLUE, {w.units[7]: 1}, P(80, 10)
    )
    assert preview.route.segments[0].start == P(20, 0)
    transit = dispatch_base_movement(
        w.game, w.a.id, Player.BLUE, {w.units[7]: 1}, P(80, 10), GameUpdateEvents()
    )
    moving = w.game.db.tgos.get(transit.detachment_id)
    assert (moving.position.x, moving.position.y) == (20, 0)
    w.game.turn += 1
    advance_armor(w.game, GameUpdateEvents())
    assert transit.finished
    assert (moving.position.x, moving.position.y) == (80, 10)


@pytest.mark.parametrize(
    "selection", [{}, {"unknown": 1}, {7: 1}, {"tank": True}, {"tank": -1}, {"tank": 5}]
)
def test_bad_selection_does_not_consume_stock_or_ids(
    stock: Any, selection: dict[Any, Any]
) -> None:
    selected = {stock.units[7] if k == "tank" else k: v for k, v in selection.items()}
    before = pickle.dumps(stock.game)
    with pytest.raises(ValueError):
        dispatch_base_movement(
            stock.game, stock.a.id, Player.BLUE, selected, P(80, 10), GameUpdateEvents()
        )
    assert pickle.dumps(stock.game) == before


def test_no_trucks_enemy_destination_and_disabled_plugin_are_rejected(
    stock: Any,
) -> None:
    stock.a.base.armor.pop(stock.units[5])
    with pytest.raises(ValueError, match="tractors"):
        preview_base_movement(
            stock.game, stock.a.id, Player.BLUE, {stock.units[1]: 1}, P(80, 10)
        )
    with pytest.raises(PermissionError):
        preview_base_movement(
            stock.game, stock.a.id, Player.BLUE, {stock.units[7]: 1}, P(195, 10)
        )
    with pytest.raises(PermissionError):
        preview_base_movement(
            stock.game, stock.a.id, Player.RED, {stock.units[7]: 1}, P(80, 10)
        )
    stock.game.settings.ground_movement = False
    with pytest.raises(ValueError, match="is off"):
        preview_base_movement(
            stock.game, stock.a.id, Player.BLUE, {stock.units[7]: 1}, P(80, 10)
        )


def test_stock_debit_arrival_layout_and_combat_posture_survive_reload(
    stock: Any,
) -> None:
    initial = stock.a.base.total_armor
    transit = send(stock)
    order = stock.game.ground_movements.orders[transit.order_id]
    tgo = stock.game.db.tgos.get(transit.detachment_id)
    assert order.source_kind is MovementSource.BASE
    assert initial - stock.a.base.total_armor == 3 == len(list(tgo.units))
    assert all(u.id >= 1000 for u in tgo.units)
    assert tgo.in_transit and tgo.reserve_from_base
    moving, _ = native(stock, transit)
    assert len(moving.units) == 2  # Loaded ZU-23 shares the Ural's identity/loss.
    assert len(moving.points) > 1
    del stock.game.iads_considerate_culling
    stock.game = pickle.loads(pickle.dumps(stock.game))
    stock.a = next(cp for cp in stock.game.theater.controlpoints if cp.id == stock.a.id)
    transit = stock.game.ground_movements.transits[transit.order_id]
    stock.game.turn += 1
    advance_armor(stock.game, GameUpdateEvents())
    tgo = stock.game.db.tgos.get(transit.detachment_id)
    assert transit.finished and not tgo.in_transit and len(list(tgo.units)) == 3
    assert stock.a.base.total_armor == initial - 3
    coords = {(u.position.x, u.position.y) for u in tgo.units}
    assert len(coords) == 3
    for x, z in coords:
        assert stock.game.theater.landmap.inclusion_zones.covers(MapPoint(x, z))
        assert not stock.game.theater.landmap.exclusion_zones.intersects(MapPoint(x, z))
    stationary, _ = native(stock, transit)
    assert len(stationary.units) == 3
    # RetLab leaves reserves on DCS AUTO like every ground group (no forced RED).


def test_cargo_loss_and_stop_do_not_refund_or_duplicate_stock(stock: Any) -> None:
    initial = stock.a.base.total_armor
    transit = send(stock)
    tgo = stock.game.db.tgos.get(transit.detachment_id)
    next(u for u in tgo.units if u.unit_type == stock.units[5]).alive = False
    stop_armor(stock.game, transit.order_id, Player.BLUE, GameUpdateEvents())
    assert sum(u.alive for u in tgo.units) == 1
    assert stock.a.base.total_armor == initial - 3
    assert not tgo.in_transit
    stop_armor(stock.game, transit.order_id, Player.BLUE, GameUpdateEvents())
    assert stock.a.base.total_armor == initial - 3


def test_finished_remote_group_is_not_deleted_with_origin_base(stock: Any) -> None:
    transit = send(stock)
    stock.game.turn += 1
    advance_armor(stock.game, GameUpdateEvents())
    tgo = stock.game.db.tgos.get(transit.detachment_id)
    assert transit.finished
    rehome_before_capture(stock.game, stock.a, GameUpdateEvents())
    stock.a.depopulate_uncapturable_tgos()
    assert tgo.control_point is stock.b and len(list(tgo.units)) == 3


def test_concurrent_arrivals_do_not_reserve_overlapping_parking(stock: Any) -> None:
    first = send(stock)
    second = dispatch_base_movement(
        stock.game,
        stock.a.id,
        Player.BLUE,
        {stock.units[7]: 1},
        P(80, 10),
        GameUpdateEvents(),
    )
    assert first.arrival_positions is not None
    assert second.arrival_positions is not None
    a = set(first.arrival_positions.values())
    b = set(second.arrival_positions.values())
    assert not a & b
    assert all((p.x - q.x) ** 2 + (p.z - q.z) ** 2 >= 225 for p in a for q in b)


def test_formation_checks_occupied_diagonal_corners(stock: Any) -> None:
    stock.game.theater.landmap = replace(
        stock.game.theater.landmap,
        inclusion_zones=MultiPolygon([box(584, 584, 586, 586)]),
    )
    unit = next(iter(stock.source.units))
    unit.position.x = unit.position.y = 585
    with pytest.raises(ValueError, match="Not enough safe ground"):
        formation(stock.game, P(0, 0), 1)


def test_red_stock_can_deploy_and_disabled_orders_resume(stock: Any) -> None:
    stock.a._coalition.player = stock.b._coalition.player = Player.RED
    transit = dispatch_base_movement(
        stock.game,
        stock.a.id,
        Player.RED,
        {stock.units[7]: 1},
        P(80, 10),
        GameUpdateEvents(),
    )
    initial = stock.a.base.total_armor
    stock.game.settings.ground_movement = False
    stock.game.turn += 1
    advance_armor(stock.game, GameUpdateEvents())
    assert not transit.finished and transit.journey.travelled_distance == 0
    assert transit.pause_reason == "Ground movement is off in the campaign settings"
    stock.game.settings.ground_movement = True
    stock.game.turn += 1
    advance_armor(stock.game, GameUpdateEvents())
    resumed = stock.game.ground_movements.transits[transit.order_id]
    assert resumed.finished and resumed.pause_reason is None
    assert stock.a.base.total_armor == initial


def test_variant_identity_is_preserved_when_delivered_back_to_stock(
    stock: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    variant = replace(stock.units[7], variant_id="Reserve test variant")
    monkeypatch.setitem(GroundUnitType._by_name, variant.variant_id, variant)
    stock.a.base.commission_units({variant: 1})
    transit = dispatch_base_movement(
        stock.game, stock.a.id, Player.BLUE, {variant: 1}, P(80, 10), GameUpdateEvents()
    )
    tgo = stock.game.db.tgos.get(transit.detachment_id)
    assert next(iter(tgo.units)).unit_type is variant
    stop_armor(stock.game, transit.order_id, Player.BLUE, GameUpdateEvents())
    destination = movement_destination(
        stock.game, Player.BLUE, DestinationKind.BASE, base_id=stock.b.id
    )
    returning = dispatch_armor(
        stock.game,
        tgo.id,
        Player.BLUE,
        [u.id for u in tgo.units],
        destination,
        GameUpdateEvents(),
    )
    stock.game.turn += 1
    advance_armor(stock.game, GameUpdateEvents())
    assert returning.finished and stock.b.base.armor[variant] == 1


def test_gps_preview_rejects_unsafe_formation_before_spending_stock(stock: Any) -> None:
    from shapely.geometry import MultiPolygon, box

    stock.game.theater.landmap = replace(
        stock.game.theater.landmap,
        exclusion_zones=MultiPolygon([box(50, -1000, 1000, 1000)]),
    )
    before = pickle.dumps(stock.game)
    with pytest.raises(ValueError):
        send(stock)
    assert pickle.dumps(stock.game) == before


def body(w: Any) -> dict[str, Any]:
    ll = Point(80, 10, w.game.theater.terrain).latlng()
    return {
        "units": {w.units[7].variant_id: 1, w.units[1].variant_id: 1},
        "position": {"lat": ll.lat, "lng": ll.lng},
    }
