"""A FOB owned by a faction on the modern FOB layout gets a few props by its first
helipad, never within the clearance of a pad; other factions get none."""

from types import SimpleNamespace

import dcs
from dcs.mapping import Point

from game.missiongenerator.tgogenerator import (
    _FARP_PROP_CLEARANCE_M,
    _MODERN_FARP_PROPS,
    HelipadGenerator,
)
from game.point_with_heading import PointWithHeading
from game.theater.controlpoint import Fob, Player
from game.utils import Heading


def _props(extra_layouts: list[str], pads: list[tuple[float, float]]) -> list[Point]:
    mission = dcs.Mission(dcs.terrain.Caucasus())
    fob = Fob(
        name="FOB Test",
        at=Point(0, 0, mission.terrain),
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.BLUE,
    )
    fob._coalition = SimpleNamespace(player=Player.BLUE)  # type: ignore[assignment]
    fob.helipads = [
        PointWithHeading.from_point(Point(x, y, mission.terrain), Heading(0))
        for x, y in pads
    ]
    game = SimpleNamespace(
        coalition_for=lambda _: SimpleNamespace(
            faction=SimpleNamespace(extra_layouts=extra_layouts)
        )
    )
    generator = HelipadGenerator(mission, fob, game, None, None)  # type: ignore[arg-type]
    generator._dress_modern_farp(mission.country("USA"), fob.helipads[0])
    return [
        unit.position
        for group in mission.country("USA").static_group
        if " FARP prop " in group.name
        for unit in group.units
    ]


def test_modern_faction_gets_every_prop() -> None:
    assert len(_props(["modern_fob"], [(0, 0)])) == len(_MODERN_FARP_PROPS)


def test_other_factions_get_none() -> None:
    assert _props([], [(0, 0)]) == []


def test_props_keep_clear_of_other_pads() -> None:
    # A second pad 45 m off the first pad's left side, where the tent would go.
    pads: list[tuple[float, float]] = [(0, 0), (0, -45)]
    props = _props(["modern_fob"], pads)
    assert len(props) < len(_MODERN_FARP_PROPS)
    for prop in props:
        for x, y in pads:
            assert prop.distance_to_point(Point(x, y, None)) >= _FARP_PROP_CLEARANCE_M  # type: ignore[arg-type]
