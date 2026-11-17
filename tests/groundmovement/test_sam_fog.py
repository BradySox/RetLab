"""§131 stage 5: a SAM battery that moves loses its standing intel (§3)."""

from __future__ import annotations

from typing import Any


from tests.groundmovement.test_armor_movement_planning import world  # noqa: F401
from tests.groundmovement.test_sam_movement import make_site, move


def test_a_moved_battery_is_no_longer_a_prepared_fixed_site(world: Any) -> None:
    site = make_site(world)
    move(world)
    assert site.relocated and not site.is_fixed_sam_site


def test_a_blue_battery_keeps_what_it_knows(world: Any) -> None:
    site = make_site(world)
    site.discovered_by_player = True
    move(world)
    assert site.discovered_by_player
