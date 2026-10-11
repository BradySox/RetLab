"""A wing with no land field still gets a tanker and an AEW&C station.

Since the land anchors stopped handing back ships, a side holding only ships got
a station only over a carrier that based the aircraft itself. A tanker or AWACS
based off-map then had nowhere to go.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain.caucasus import Caucasus

from game.commander.theaterstate import _aewc_targets, _refueling_targets
from game.theater.player import Player

TERRAIN = Caucasus()


def _cp(name: str, x: float, *, fleet: bool, squadrons: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        name=name,
        position=Point(x, 0, TERRAIN),
        is_fleet=fleet,
        is_carrier=fleet,
        squadrons=squadrons or [],
    )


def _squadron(location: Any, untasked: int = 2) -> Any:
    return SimpleNamespace(
        location=location, capable_of=lambda task: True, untasked_aircraft=untasked
    )


def _finder(cps: list[Any], squadrons: list[Any], land_anchor: Any = None) -> Any:
    air_wing = SimpleNamespace(iter_squadrons=lambda: iter(squadrons))
    return SimpleNamespace(
        is_player=Player.BLUE,
        game=SimpleNamespace(
            coalition_for=lambda player: SimpleNamespace(air_wing=air_wing)
        ),
        friendly_control_points=lambda: iter(cps),
        front_lines=lambda: iter([]),
        tanker_land_anchor=lambda: land_anchor,
        aewc_land_anchor=lambda: land_anchor,
        forward_aewc_land_anchor=lambda: land_anchor,
    )


def test_off_map_support_flies_over_the_nearest_friendly_ship() -> None:
    off_map = _cp("Off-map", 0, fleet=False)
    near = _cp("CVN near", 100_000, fleet=True)
    far = _cp("CVN far", 900_000, fleet=True)
    finder = _finder([far, near], [_squadron(off_map)])
    assert _refueling_targets(finder) == [near]
    assert _aewc_targets(finder) == [near]


def test_no_station_when_nothing_can_fly_it() -> None:
    boat = _cp("CVN", 100_000, fleet=True)
    off_map = _cp("Off-map", 0, fleet=False)
    assert _refueling_targets(_finder([boat], [])) == []
    assert _aewc_targets(_finder([boat], [_squadron(off_map, untasked=0)])) == []


def test_a_land_station_is_never_joined_by_the_fallback() -> None:
    field = _cp("Field", 0, fleet=False)
    boat = _cp("CVN", 100_000, fleet=True)
    finder = _finder([boat, field], [_squadron(field)], land_anchor=field)
    assert _refueling_targets(finder) == [field]
    assert _aewc_targets(finder) == [field]
