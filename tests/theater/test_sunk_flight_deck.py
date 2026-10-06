"""A sunk carrier or LHA takes no squadrons, even with its escorts afloat.

Ported from juanjux/dcs-escalation#501 (the deck half).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from dcs.mapping import Point
from dcs.ships import PERRY
from dcs.terrain import Terrain

from game.theater.controlpoint import (
    Carrier,
    Essex,
    EssexCarrier,
    LHA_Tarawa,
    Lha,
    Stennis,
)
from game.theater.player import Player
from game.theater.theatergroundobject import GenericCarrierGroundObject

_CAPABLE = SimpleNamespace(carrier_capable=True, lha_capable=True)


def _cp(cls: Any) -> Any:
    return cls("Fleet", Point(0, 0, MagicMock(spec=Terrain)), None, Player.BLUE)


def _fleet(cls: Any, hull: Any) -> Any:
    cp = _cp(cls)
    tgo = MagicMock(spec=GenericCarrierGroundObject)
    tgo.groups = [
        SimpleNamespace(
            units=[
                SimpleNamespace(type=hull, alive=False),
                SimpleNamespace(type=PERRY, alive=True),
            ]
        )
    ]
    cp.connected_objectives = [tgo]
    return cp


@pytest.mark.parametrize(
    "cls,hull", [(Carrier, Stennis), (Lha, LHA_Tarawa), (EssexCarrier, Essex)]
)
def test_escorts_do_not_replace_a_sunk_flight_deck(cls: Any, hull: Any) -> None:
    cp = _fleet(cls, hull)
    assert not cp.can_operate(_CAPABLE)
    cp.find_main_tgo().groups[0].units[0].alive = True
    assert cp.can_operate(_CAPABLE)
    assert not cp.can_operate(SimpleNamespace(carrier_capable=False, lha_capable=False))


@pytest.mark.parametrize("cls", [Carrier, Lha, EssexCarrier])
def test_a_fleet_with_no_ship_group_yet_still_takes_squadrons(cls: Any) -> None:
    # Turn-0 squadron assignment runs before the ships are generated.
    assert _cp(cls).can_operate(_CAPABLE)
