from collections.abc import Iterator

from game.commander.tasks.primitive.packagecontrol import PlanPackageControl
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class PlanPackageControlSupport(CompoundTask[TheaterState]):
    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for target in state.package_control_targets:
            yield [PlanPackageControl(target)]
