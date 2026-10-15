"""Locks which maneuver each frontline role gets from PR #823's cohesive
maneuver: wedges advance as armor, clustered members follow their wedge, and
unanchored spares take the generic per-stance advance.

See docs/dev/design/retlab-pr823-frontline-merge-notes.md (Bucket C).
"""

from unittest.mock import MagicMock

from game.ground_forces.ai_ground_planner import CombatGroup, CombatGroupRole
from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.flotgenerator import FlotGenerator


def _gen() -> FlotGenerator:
    gen = FlotGenerator.__new__(FlotGenerator)
    gen.game = MagicMock()
    gen.game.settings.perf_moving_units = True
    gen.game.settings.perf_artillery = True
    # Stub every action method so we can assert which one fires.
    gen._plan_tank_ifv_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_apc_atgm_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_follower_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_artillery_action = MagicMock()  # type: ignore[method-assign]
    return gen


def _call(gen: FlotGenerator, group: CombatGroup) -> None:
    gen.plan_action_for_groups(
        CombatStance.AGGRESSIVE,
        ally_groups=[(MagicMock(), group)],
        enemy_groups=[],
        forward_heading=MagicMock(),
        from_cp=MagicMock(),
        to_cp=MagicMock(),
    )


def _grp(role: CombatGroupRole) -> CombatGroup:
    return CombatGroup(role, MagicMock(), 5)


def test_tank_takes_the_wedge_action() -> None:
    gen = _gen()
    _call(gen, _grp(CombatGroupRole.TANK))
    gen._plan_tank_ifv_action.assert_called_once()  # type: ignore[attr-defined]


def test_anchored_member_uses_follower_action() -> None:
    gen = _gen()
    atgm = _grp(CombatGroupRole.ATGM)
    atgm.anchor = _grp(CombatGroupRole.TANK)
    _call(gen, atgm)
    gen._plan_follower_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_apc_atgm_action.assert_not_called()  # type: ignore[attr-defined]


def test_unanchored_member_uses_apc_atgm() -> None:
    gen = _gen()
    atgm = _grp(CombatGroupRole.ATGM)  # anchor is None
    _call(gen, atgm)
    gen._plan_apc_atgm_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_follower_action.assert_not_called()  # type: ignore[attr-defined]


def test_apc_joins_wedge_branch() -> None:
    # APC maneuvers as armor (WEDGE_ROLES).
    gen = _gen()
    _call(gen, _grp(CombatGroupRole.APC))
    gen._plan_tank_ifv_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_apc_atgm_action.assert_not_called()  # type: ignore[attr-defined]
