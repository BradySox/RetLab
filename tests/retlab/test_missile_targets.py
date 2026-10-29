"""§125: a player's missile site keeps a saved, fog-gated target until it dies."""

from __future__ import annotations

import pickle
import uuid
from types import SimpleNamespace
from typing import Any

from dcs import Point

from game import missiletargets
from game.missiletargets import MissileTargetPick
from game.theater.player import Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import MissileSiteGroundObject
from game.utils import Heading

SCUD_RANGE_M = 320_000


def _point(x: float) -> Point:
    return Point(x, 0, None)  # type: ignore[arg-type]


class FakeCp:
    def __init__(self, captured: Player, x: float, name: str = "Base") -> None:
        self.id = uuid.uuid4()
        self.captured = captured
        self.position = _point(x)
        self.name = name
        self.ground_objects: list[Any] = []

    def is_friendly(self, to_player: Player) -> bool:
        return self.captured is to_player


class FakeTarget:
    def __init__(self, cp: FakeCp, x: float, name: str, hidden: bool = False) -> None:
        self.id = uuid.uuid4()
        self.control_point = cp
        self.position = _point(x)
        self.obj_name = name
        self.sea_object = False
        self.is_control_point = False
        self.dead = False
        self.hidden = hidden
        cp.ground_objects.append(self)

    def is_dead(self) -> bool:
        return self.dead

    def hidden_on_player_map(self, viewer: Player) -> bool:
        return self.hidden


def _scud_group(alive: bool = True) -> Any:
    unit = SimpleNamespace(
        alive=alive, type=SimpleNamespace(id="Scud_B", threat_range=SCUD_RANGE_M)
    )
    return SimpleNamespace(units=[unit], alive_units=lambda: 1 if alive else 0)


def _world() -> tuple[Any, MissileSiteGroundObject, FakeCp]:
    home = FakeCp(Player.BLUE, 0, "Home")
    enemy = FakeCp(Player.RED, 100_000, "Enemy")
    site = MissileSiteGroundObject(
        "Scud site",
        PresetLocation("site", _point(0), Heading(0)),
        home,  # type: ignore[arg-type]
    )
    site.groups = [_scud_group()]
    home.ground_objects.append(site)
    tgos: dict[uuid.UUID, Any] = {}
    db = SimpleNamespace(tgos=SimpleNamespace(get=lambda key: tgos[key]))
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[home, enemy]), db=db, _tgos=tgos
    )
    return game, site, enemy


def _add(game: Any, target: FakeTarget) -> FakeTarget:
    game._tgos[target.id] = target
    return target


def test_lists_enemy_bases_and_visible_sites_nearest_first() -> None:
    game, site, enemy = _world()
    _add(game, FakeTarget(enemy, 150_000, "SAM far"))
    _add(game, FakeTarget(enemy, 50_000, "Factory near"))
    _add(game, FakeTarget(enemy, 60_000, "Command post", hidden=True))
    _add(game, FakeTarget(enemy, 400_000, "Out of range"))
    names = [c.name for c in missiletargets.choices(game, site)]
    assert names == ["Factory near", "Base: Enemy", "SAM far"]


def test_a_hidden_target_never_fires_even_if_saved() -> None:
    game, site, enemy = _world()
    post = _add(game, FakeTarget(enemy, 60_000, "Command post", hidden=True))
    site.missile_target = MissileTargetPick(post.id, False)
    assert missiletargets.aim_point(game, site) is None


def test_a_pick_aims_dead_center() -> None:
    game, site, enemy = _world()
    sam = _add(game, FakeTarget(enemy, 150_000, "SAM"))
    site.missile_target = MissileTargetPick(sam.id, False)
    assert missiletargets.aim_point(game, site) is sam.position


def test_the_pick_stays_until_the_target_dies() -> None:
    game, site, enemy = _world()
    sam = _add(game, FakeTarget(enemy, 150_000, "SAM"))
    site.missile_target = MissileTargetPick(sam.id, False)
    missiletargets.release_spent_picks(game)
    assert site.missile_target is not None
    sam.dead = True
    missiletargets.release_spent_picks(game)
    assert site.missile_target is None


def test_a_captured_base_frees_the_site() -> None:
    game, site, enemy = _world()
    site.missile_target = MissileTargetPick(enemy.id, True)
    assert missiletargets.aim_point(game, site) is enemy.position
    enemy.captured = Player.BLUE
    missiletargets.release_spent_picks(game)
    assert site.missile_target is None


def test_red_sites_cannot_pick() -> None:
    game, site, enemy = _world()
    site.control_point = enemy  # type: ignore[assignment]
    assert not missiletargets.can_pick(game, site)
    site.missile_target = MissileTargetPick(enemy.id, True)
    assert missiletargets.aim_point(game, site) is None


def test_an_old_save_loads_with_no_pick() -> None:
    _, site, _ = _world()
    state = site.__getstate__()
    del state["missile_target"]
    clone = MissileSiteGroundObject.__new__(MissileSiteGroundObject)
    clone.__setstate__(state)
    assert clone.missile_target is None


def test_the_pick_pickles() -> None:
    pick = MissileTargetPick(uuid.uuid4(), False)
    assert pickle.loads(pickle.dumps(pick)) == pick
