"""IADS rebuilds under a config, and ships off the shore grid.

Ported from juanjux/dcs-escalation#452 and #453.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game import migrator as migrator_module
from game.migrator import Migrator
from game.theater.iadsnetwork.iadsnetwork import IadsNetwork
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.theatergroundobject import ShipGroundObject
from tests.theater.test_iads_unnamed_sites import _connections, _power, _sam, _site


def _events() -> Any:
    return SimpleNamespace(
        delete_iads_connection=lambda cid: None, update_iads_node=lambda node: None
    )


def _ship(name: str, x_km: float) -> Any:
    return _site(ShipGroundObject, name, "ship", IadsRole.EWR, x_km)


def _migrator(network: IadsNetwork, ground_objects: Any = ()) -> Migrator:
    m = Migrator.__new__(Migrator)
    m.game = SimpleNamespace(  # type: ignore[assignment]
        campaign_name="Test",
        theater=SimpleNamespace(
            iads_network=network, ground_objects=list(ground_objects)
        ),
    )
    return m


def test_an_unnamed_site_keeps_its_grid_when_it_is_rebuilt() -> None:
    named, unnamed, power = _sam("NAMED", 0), _sam("UNNAMED", 10), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, unnamed, power]))

    network.update_tgo(unnamed, _events())

    assert _connections(network, "UNNAMED") == {"POWER"}
    # Reading the defaultdict used to insert an empty entry for it.
    assert "UNNAMED" not in network.iads_config


def test_a_named_site_is_still_rebuilt_from_the_config() -> None:
    named, power = _sam("NAMED", 0), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, power]))

    network.update_tgo(named, _events())

    assert _connections(network, "NAMED") == set()


def test_a_rebuild_removes_every_old_node_of_the_site() -> None:
    sam, power = _sam("SAM", 0), _power("POWER", 12)
    network = IadsNetwork(True, [])
    network.initialize_network(iter([sam, power]))
    # Two nodes for one site: removing while iterating skipped the second.
    network.nodes.append(network.nodes[0].__class__(sam.groups[0]))
    old = list(network.nodes)

    network.update_tgo(sam, _events())

    [rebuilt] = network.nodes
    assert all(rebuilt is not n for n in old)


def test_stray_empty_entries_are_dropped_and_authored_ones_kept() -> None:
    network = IadsNetwork(True, ["AUTHORED", {"WIRED": ["POWER"]}])
    network.iads_config["STRAY"]  # what the old defaultdict read did
    assert network.drop_config_entries_not_in({"AUTHORED", "WIRED"}) == ["STRAY"]
    assert set(network.iads_config) == {"AUTHORED", "WIRED"}


def test_the_migrator_drops_stray_entries_then_wires_the_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    named, unnamed, power = _sam("NAMED", 0), _sam("UNNAMED", 10), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, unnamed, power]))
    # An old save: the rebuild left the site unwired and named by a stray entry.
    network.iads_config["UNNAMED"]
    [node] = [n for n in network.nodes if n.group.ground_object is unnamed]
    node.connections.clear()
    monkeypatch.setattr(
        migrator_module, "_campaign_iads_config_names", lambda name: {"NAMED"}
    )
    m = _migrator(network, [named, unnamed, power])

    m._drop_stray_iads_config_entries()
    m._wire_iads_sites_that_arrived_late()

    assert "UNNAMED" not in network.iads_config
    assert _connections(network, "UNNAMED") == {"POWER"}


def test_the_migrator_keeps_everything_when_the_campaign_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    network = IadsNetwork(True, ["NAMED"])
    network.iads_config["STRAY"]
    monkeypatch.setattr(migrator_module, "_campaign_iads_config_names", lambda n: None)
    _migrator(network)._drop_stray_iads_config_entries()
    assert set(network.iads_config) == {"NAMED", "STRAY"}


def test_a_ship_is_not_range_wired_to_the_shore() -> None:
    ship, power = _ship("FLEET", 0), _power("POWER", 5)
    network = IadsNetwork(True, [])
    network.initialize_network(iter([ship, power]))
    assert _connections(network, "FLEET") == set()

    network._update_network(power, _events())
    network.update_tgo(ship, _events())
    assert _connections(network, "FLEET") == set()
    assert network.enrol_sites_that_arrived_late(iter([ship, power])) == []


def test_old_saves_take_range_wired_ships_off_the_grid() -> None:
    loose, kept, power = _ship("LOOSE", 0), _ship("KEPT", 0), _power("POWER", 5)
    network = IadsNetwork(True, [{"KEPT": ["POWER"]}])
    network.initialize_network(iter([loose, kept, power]))
    [loose_node] = [n for n in network.nodes if n.group.ground_object is loose]
    loose_node.add_connection_for_tgo(power)

    _migrator(network)._unwire_iads_ships()

    assert _connections(network, "LOOSE") == set()
    assert _connections(network, "KEPT") == {"POWER"}
    assert network.unwire_ships() == []
