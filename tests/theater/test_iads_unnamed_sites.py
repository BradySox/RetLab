"""What belongs in the IADS network, whichever way the campaign built it.

A campaign with an ``iads_config`` got its network from that config, and only the
keys of it became nodes. A site the author never named -- an anonymous Ground-N
slot, a SAM the faction fielded that the author did not foresee -- was outside the
network entirely: never exported to Skynet, so nothing cued it and bombing the
power station beside it changed nothing. Found in juanjux/dcs-escalation#336.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from dcs.mapping import Point
from dcs.terrain import Terrain

from game.migrator import Migrator
from game.point_with_heading import PointWithHeading
from game.theater.iadsnetwork.iadsnetwork import IadsNetwork
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.player import Player
from game.theater.theatergroundobject import (
    BuildingGroundObject,
    IadsBuildingGroundObject,
    SamGroundObject,
    ShipGroundObject,
)
from game.theater.theatergroup import IadsGroundGroup
from game.utils import Heading

_ids = iter(range(1, 10_000))


def _site(
    kind: Any, name: str, category: str, role: IadsRole, x_km: float, blue: bool = True
) -> Any:
    """One objective with one group, built without running the constructors.

    The network reads the class, the category, the position, the side and the
    group's role, and nothing else.
    """
    site = kind.__new__(kind)
    site.name = name
    site.original_name = name
    site.category = category
    site.position = Point(x_km * 1000.0, 0.0, MagicMock(spec=Terrain))
    site.control_point = SimpleNamespace(
        captured=SimpleNamespace(is_neutral=False),
        is_friendly=lambda player: (player is Player.BLUE) == blue,
    )
    group = IadsGroundGroup(
        next(_ids),
        name,
        PointWithHeading.from_point(site.position, Heading.from_degrees(0)),
        [SimpleNamespace(alive=True)],  # type: ignore[list-item]
        site,
    )
    group.iads_role = role
    site.groups = [group]
    return site


def _sam(name: str, x_km: float, blue: bool = True) -> Any:
    return _site(SamGroundObject, name, "aa", IadsRole.SAM, x_km, blue)


def _power(name: str, x_km: float, blue: bool = True) -> Any:
    return _site(
        IadsBuildingGroundObject, name, "power", IadsRole.POWER_SOURCE, x_km, blue
    )


def _connections(network: IadsNetwork, name: str) -> set[str]:
    (node,) = [n for n in network.nodes if n.group.ground_object.name == name]
    return {g.ground_object.name for g in node.connections.values()}


def test_an_air_defence_site_belongs() -> None:
    assert IadsNetwork._belongs_in_the_network(_sam("SAM", 0))


def test_a_fleet_belongs() -> None:
    assert IadsNetwork._belongs_in_the_network(
        _site(ShipGroundObject, "FLEET", "ship", IadsRole.EWR, 0)
    )


def test_a_command_centre_belongs_and_other_infrastructure_does_not() -> None:
    cc = _site(IadsBuildingGroundObject, "CC", "commandcenter", IadsRole.NO_BEHAVIOR, 0)
    assert IadsNetwork._belongs_in_the_network(cc)
    # Comms and power are connections of a node, never nodes.
    assert not IadsNetwork._belongs_in_the_network(_power("POWER", 0))
    factory = BuildingGroundObject.__new__(BuildingGroundObject)
    factory.category = "factory"
    assert not IadsNetwork._belongs_in_the_network(factory)


def test_a_site_the_config_never_named_joins_the_network_by_range() -> None:
    named, unnamed, power = _sam("NAMED", 0), _sam("UNNAMED", 10), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, unnamed, power]))

    assert {n.group.ground_object.name for n in network.nodes} == {"NAMED", "UNNAMED"}
    assert _connections(network, "UNNAMED") == {"POWER"}


def test_the_config_is_still_honoured_exactly_for_the_sites_it_names() -> None:
    # The named site sits 12 km from the power station, well inside the 35 nm
    # range wiring would use, and the config gave it nothing. Nothing is what it gets.
    named, power = _sam("NAMED", 0), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, power]))
    assert _connections(network, "NAMED") == set()


def test_an_unnamed_site_is_wired_only_to_its_own_side() -> None:
    unnamed, red_power = _sam("UNNAMED", 0), _power("RED POWER", 5, blue=False)
    network = IadsNetwork(True, ["ELSEWHERE"])
    network.initialize_network(iter([unnamed, red_power]))
    assert _connections(network, "UNNAMED") == set()


def test_a_site_that_arrived_after_the_network_was_built_is_wired_on_load() -> None:
    named, power = _sam("NAMED", 0), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, power]))
    late = _sam("LATE", 10)

    assert network.enrol_sites_that_arrived_late(iter([named, power, late])) == ["LATE"]
    assert _connections(network, "LATE") == {"POWER"}
    # Idempotent: a wired node is left alone on the next load.
    assert network.enrol_sites_that_arrived_late(iter([named, power, late])) == []


def test_a_basic_network_is_left_alone() -> None:
    # Basic mode has no comms or power at all, so there is nothing to wire to.
    sam, power = _sam("SAM", 0), _power("POWER", 12)
    network = IadsNetwork(False, [])
    network.initialize_network(iter([sam, power]))
    assert network.enrol_sites_that_arrived_late(iter([sam, power])) == []
    assert _connections(network, "SAM") == set()


def test_the_migrator_runs_the_late_wiring_against_the_theater() -> None:
    named, power = _sam("NAMED", 0), _power("POWER", 12)
    network = IadsNetwork(True, ["NAMED"])
    network.initialize_network(iter([named, power]))
    late = _sam("LATE", 10)
    m = Migrator.__new__(Migrator)
    m.game = SimpleNamespace(  # type: ignore[assignment]
        theater=SimpleNamespace(
            iads_network=network, ground_objects=[named, power, late]
        )
    )
    m._wire_iads_sites_that_arrived_late()
    assert _connections(network, "LATE") == {"POWER"}
