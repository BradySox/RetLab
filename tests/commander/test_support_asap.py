"""Support packages (tankers, AWACS) are planned ASAP; strike-class ones are not."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from game.commander.tasks.packageplanningtask import PackagePlanningTask
from game.commander.tasks.primitive.aewc import PlanAewc
from game.commander.tasks.primitive.barcap import PlanBarcap
from game.commander.tasks.primitive.refueling import PlanRefueling
from game.commander.tasks.primitive.strike import PlanStrike


def test_support_tasks_are_asap() -> None:
    assert PlanRefueling(MagicMock()).asap
    assert PlanAewc(MagicMock()).asap


def test_combat_tasks_are_not_asap() -> None:
    # BARCAP's first wave is flagged by the scheduler, not the task: relief waves
    # must stay chained (see test_missionscheduler).
    assert not PlanBarcap(MagicMock(), max_orders=1).asap
    assert not PlanStrike(MagicMock()).asap


def _proposed_asap(task: PackagePlanningTask[Any]) -> bool:
    state = MagicMock()
    # Not the first AWACS of the turn, so only the task's own flag can set ASAP.
    state.context.coalition.ato.has_awacs_package = True
    with patch(
        "game.commander.tasks.packageplanningtask.PackageFulfiller"
    ) as fulfiller:
        task.fulfill_mission(state)
    mission = fulfiller.return_value.plan_mission.call_args.args[0]
    return bool(mission.asap)


def test_every_tanker_is_planned_asap() -> None:
    assert _proposed_asap(PlanRefueling(MagicMock()))


def test_every_awacs_is_planned_asap_not_only_the_first() -> None:
    assert _proposed_asap(PlanAewc(MagicMock()))
