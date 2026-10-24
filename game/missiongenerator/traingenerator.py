"""Trains on drawn rail lines (features doc §123).

DCS stores a train as one ``Train`` unit carrying a wagon list, and scripts see the
whole train as that one unit. It fires no dead event when killed (2026-10-24 probe),
so ``train_losses.lua`` watches its health and reports the cargo names below.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

from dcs import Mission
from dcs import unittype
from dcs.action import DoScript
from dcs.translation import String
from dcs.triggers import TriggerStart
from dcs.mapping import Point
from dcs.unit import Vehicle
from dcs.unitgroup import VehicleGroup

from game.transfers import Train
from game.unitmap import UnitMap
from game.utils import kph

if TYPE_CHECKING:
    from game import Game

#: The ME writes this as both the action and type of a rail waypoint.
RAIL_ACTION = "On Railroads"
TRAIN_SPEED = kph(50)
MIN_WAGONS = 4
MAX_WAGONS = 20

#: (locomotive, wagons cycled behind it) by era and map.
Consist = tuple[str, tuple[str, ...]]

WWII_TRAIN: Consist = (
    "DRG_Class_86",
    ("German_covered_wagon_G10", "German_tank_wagon", "DR_50Ton_Flat_Wagon"),
)
US_TRAIN: Consist = ("ES44AH", ("Boxcartrinity", "Tankcartrinity", "Wellcarnsc"))
DEFAULT_TRAIN: Consist = (
    "Locomotive",
    ("Coach cargo", "Coach cargo open", "Coach a tank blue", "Coach a platform"),
)


#: The train drawn in a campaign .miz to mark a rail line; never spawned.
DEFAULT_TRAIN_LINE = ("Locomotive", "Coach cargo", "Coach cargo")


class _TrainType(unittype.VehicleType):
    id = "Train"
    name = "Train"


class _RailAction:
    """Stands in for a pydcs PointAction, which has no rail member."""

    value = RAIL_ACTION


class TrainUnit(Vehicle):
    def __init__(self, vehicle: Vehicle, wagons: list[str]) -> None:
        super().__init__(vehicle._terrain, vehicle.id, str(vehicle.name), "Train")
        self.position = vehicle.position
        self.heading = vehicle.heading
        self.wagons = wagons

    def dict(self) -> dict[str, Any]:
        d = super().dict()
        d["wagons"] = {i + 1: wagon for i, wagon in enumerate(self.wagons)}
        return d


def consist_for(game: Game, cargo_size: int) -> list[str]:
    """The locomotive and wagons, sized to the cargo."""
    if game.date.year < 1950:
        locomotive, wagons = WWII_TRAIN
    elif game.theater.terrain.name == "Nevada":
        locomotive, wagons = US_TRAIN
    else:
        locomotive, wagons = DEFAULT_TRAIN
    count = max(MIN_WAGONS, min(MAX_WAGONS, cargo_size))
    return [locomotive] + list(itertools.islice(itertools.cycle(wagons), count))


def rail_group(
    mission: Mission, country: Any, name: str, route: list[Point], wagons: list[str]
) -> VehicleGroup:
    """A train group as the Mission Editor writes one, every waypoint on the rails."""
    group = mission.vehicle_group(country, name, _TrainType, position=route[0])
    group.units[0] = TrainUnit(group.units[0], wagons)
    group.manualHeading = True
    first = group.points[0]
    first.action = _RailAction  # type: ignore[assignment]
    first.type = RAIL_ACTION
    first.speed = TRAIN_SPEED.meters_per_second
    for point in route[1:]:
        waypoint = group.add_waypoint(point, speed=TRAIN_SPEED.kph)
        waypoint.action = _RailAction  # type: ignore[assignment]
        waypoint.type = RAIL_ACTION
    return group


def draw_rail_line(
    mission: Mission, country: Any, name: str, points: list[tuple[float, float]]
) -> VehicleGroup:
    """A campaign rail line: a short train the loader reads for its waypoints."""
    route = [Point(x, y, mission.terrain) for x, y in points]
    return rail_group(mission, country, name, route, list(DEFAULT_TRAIN_LINE))


def _lua_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def trains_lua(trains: dict[str, list[str]]) -> str:
    """The table train_losses.lua reads: train unit name -> its cargo names."""
    lines = ["retlab_trains = {"]
    for train, cargo in trains.items():
        names = ", ".join(_lua_string(name) for name in cargo)
        lines.append(f"  [{_lua_string(train)}] = {{ {names} }},")
    lines.append("}")
    return "\n".join(lines)


class TrainGenerator:
    def __init__(self, mission: Mission, game: Game, unit_map: UnitMap) -> None:
        self.mission = mission
        self.game = game
        self.unit_map = unit_map

    def generate(self) -> None:
        for coalition in self.game.coalitions:
            for convoy in coalition.transfers.convoys:
                if isinstance(convoy, Train):
                    self.generate_train(convoy)
        if self.unit_map.trains:
            trigger = TriggerStart(comment="RetLab trains")
            trigger.add_action(DoScript(String(trains_lua(self.unit_map.trains))))
            self.mission.triggerrules.triggers.append(trigger)

    def generate_train(self, train: Train) -> VehicleGroup:
        route = train.route
        country = self.mission.country(
            self.game.coalition_for(train.player_owned).faction.country.name
        )
        group = rail_group(
            self.mission,
            country,
            train.name,
            list(route),
            consist_for(self.game, train.size),
        )
        self.unit_map.add_train(group, train)
        return group
