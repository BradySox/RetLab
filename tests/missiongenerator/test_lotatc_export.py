"""LotATC draws blue's GCI only the red air defenses blue has found."""

from __future__ import annotations

from typing import Optional

from game.missiongenerator.luagenerator import lotatc_exports
from game.theater.player import Player


class _Site:
    def __init__(self, known_to_blue: bool) -> None:
        self.known_to_blue = known_to_blue

    def known_for(self, viewer: Optional[Player] = None) -> bool:
        assert viewer is Player.BLUE
        return self.known_to_blue


def test_an_unfound_red_site_is_not_exported() -> None:
    assert not lotatc_exports(_Site(known_to_blue=False), blue_owned=False)  # type: ignore[arg-type]


def test_a_found_red_site_is_exported() -> None:
    assert lotatc_exports(_Site(known_to_blue=True), blue_owned=False)  # type: ignore[arg-type]


def test_every_blue_site_is_exported() -> None:
    assert lotatc_exports(_Site(known_to_blue=False), blue_owned=True)  # type: ignore[arg-type]
