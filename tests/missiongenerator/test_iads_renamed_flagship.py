from __future__ import annotations

from typing import cast

from dcs import Mission

from game import Game
from game.missiongenerator.luagenerator import LuaGenerator
from game.missiongenerator.missiondata import MissionData
from game.theater.iadsnetwork.iadsnetwork import IadsNode
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.player import Player


def _node(name: str) -> IadsNode:
    return IadsNode(name, Player.BLUE, IadsRole.EWR)


def test_renamed_flagship_joins_the_iads_under_its_dcs_name() -> None:
    # Test 47: Skynet was told "0798 | CVN-71 Theodore Roosevelt", but the
    # flagship spawns as "CVN-71 Theodore Roosevelt", so the boat never joined.
    data = MissionData()
    data.renamed_units["0798 | CVN-71 Theodore Roosevelt"] = "CVN-71 Theodore Roosevelt"
    generator = LuaGenerator(cast(Game, None), Mission(), data)

    assert (
        generator.iads_dcs_name(_node("0798 | CVN-71 Theodore Roosevelt"))
        == "CVN-71 Theodore Roosevelt"
    )


def test_unrenamed_unit_keeps_its_name() -> None:
    generator = LuaGenerator(cast(Game, None), Mission(), MissionData())

    assert generator.iads_dcs_name(_node("0437 | EWR")) == "0437 | EWR"
