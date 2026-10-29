"""A SAM site that deploys with its own generator does not live off the grid.

A Patriot battery brings an EPP-III, a SAMP/T an MGE, an S-300 its 5I57A diesels
(§85). Range wiring gave every land SAM a power-station dependency, so bombing the
nearest substation switched these off too. Ported from juanjux/dcs-escalation
(``brings_its_own_power``, ``tests/test_iads_self_powered.py``, LGPL-3.0).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from game.data.units import UnitClass
from game.server.iadsnetwork.models import IadsConnectionJs
from game.server.leaflet import LeafletPoint
from game.theater.iadsnetwork.iadsnetwork import IadsNetwork, brings_its_own_power
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.player import Player


def _unit(name: str, unit_class: UnitClass | None, alive: bool = True) -> Any:
    unit_type = None if unit_class is None else SimpleNamespace(unit_class=unit_class)
    return SimpleNamespace(
        alive=alive, unit_type=unit_type, unit_name=name, is_static=True
    )


def _group(role: IadsRole, name: str, *units: Any) -> Any:
    ground_object = SimpleNamespace(
        name=name,
        coalition=SimpleNamespace(player=Player.BLUE),
        is_friendly=lambda other: other is Player.BLUE,
    )
    group = SimpleNamespace(
        iads_role=role,
        group_name=name,
        units=list(units),
        ground_object=ground_object,
        alive_units=lambda: sum(u.alive for u in units),
    )
    ground_object.groups = [group]
    ground_object.units = list(units)
    return group


def _battery(*, generator: bool, generator_alive: bool = True) -> Any:
    units = [
        _unit("str", UnitClass.SEARCH_RADAR),
        _unit("ln", UnitClass.LAUNCHER),
    ]
    if generator:
        units.append(_unit("epp", UnitClass.POWER, alive=generator_alive))
    return _group(IadsRole.SAM, "SAM-1", *units)


def _exported(sam: Any) -> dict[str, list[str]]:
    power = _group(IadsRole.POWER_SOURCE, "power-1", _unit("power-1", None))
    comms = _group(IadsRole.CONNECTION_NODE, "comms-1", _unit("comms-1", None))
    network = IadsNetwork(True, [])
    network.nodes = [
        SimpleNamespace(group=sam, connections={1: power, 2: comms})  # type: ignore[list-item]
    ]
    game = SimpleNamespace(iads_considerate_culling=lambda tgo: False)
    [node] = network.iads_nodes(game)  # type: ignore[arg-type]
    return dict(node.connections)


def test_a_site_without_a_generator_depends_on_the_power_station() -> None:
    assert _exported(_battery(generator=False))["PowerSource"] == ["power-1"]


def test_a_site_with_a_live_generator_has_no_power_station_dependency() -> None:
    connections = _exported(_battery(generator=True))
    assert connections.get("PowerSource", []) == []
    # Its comms link is untouched: a generator makes power, not a radio net.
    assert connections["ConnectionNode"] == ["comms-1"]


def test_killing_the_generator_puts_the_site_back_on_the_grid() -> None:
    connections = _exported(_battery(generator=True, generator_alive=False))
    assert connections["PowerSource"] == ["power-1"]


def test_a_generator_in_another_group_of_the_site_counts() -> None:
    sam = _battery(generator=False)
    support = SimpleNamespace(units=[_unit("5i57", UnitClass.POWER)])
    sam.ground_object.groups.append(support)
    sam.ground_object.units = sam.units + support.units
    assert brings_its_own_power(sam.ground_object)


def test_a_unit_whose_type_no_longer_resolves_reads_as_no_generator() -> None:
    assert not brings_its_own_power(
        SimpleNamespace(units=[_unit("gone", None)])  # type: ignore[arg-type]
    )


def test_the_map_draws_no_power_line_to_a_self_powered_site() -> None:
    def lines(sam: Any) -> list[bool]:
        power = _group(IadsRole.POWER_SOURCE, "power-1", _unit("power-1", None))
        for go, category in ((sam.ground_object, "aa"), (power.ground_object, "power")):
            go.category = category
            go.id = uuid4()
            go.hidden_on_player_map = lambda viewer: False
            go.known_for = lambda viewer: True
            go.position = SimpleNamespace(latlng=lambda: LeafletPoint(lat=0, lng=0))
        node = SimpleNamespace(group=sam, connections={uuid4(): power})
        return [
            c.is_power
            for c in IadsConnectionJs.connections_for_node(node)  # type: ignore[arg-type]
        ]

    assert lines(_battery(generator=False)) == [True]
    assert lines(_battery(generator=True)) == []
    assert lines(_battery(generator=True, generator_alive=False)) == [True]


def test_the_generators_are_classed_power() -> None:
    """The feature reads the unit class, not a list of ids: if one of these loses
    its class, its site silently goes back on the grid."""
    units = Path(__file__).resolve().parents[2] / "resources/units/ground_units"
    classed = {
        path.stem
        for path in units.glob("*.yaml")
        if "class: Power" in path.read_text(encoding="utf-8")
    }
    assert {"Patriot EPP", "SAMPT_MGE", "generator_5i57"} <= classed
