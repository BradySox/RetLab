from collections.abc import Iterator
from dataclasses import dataclass

from game.commander.tasks.compound.defendbase import DefendBase
from game.commander.tasks.primitive.cas import PlanCas
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


@dataclass(frozen=True)
class DefendBases(CompoundTask[TheaterState]):
    plan_cas: bool = True

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for front in state.active_front_lines:
            yield [DefendBase(front, self.plan_cas)]


@dataclass(frozen=True)
class DelayedFrontLineCas(CompoundTask[TheaterState]):
    """The front-line CAS a thunderstorm held back from the lead (§67)."""

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for front in state.active_front_lines:
            yield [PlanCas(front)]
