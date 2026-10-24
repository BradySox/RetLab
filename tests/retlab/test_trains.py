"""§123 trains on drawn rail lines.

A rail line wins over the road between the same bases, its supply rides one DCS
"Train" unit, and the train dying (reported by train_losses.lua under per-cargo
names) loses the whole cargo through the ordinary convoy-loss path.
"""

from __future__ import annotations

import zipfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import lupa
from dcs import Mission
from dcs.mapping import Point
from dcs.terrain.germanycoldwar import GermanyColdWar

from game.campaignloader.mizcampaignloader import MizCampaignLoader
from game.missiongenerator.traingenerator import (
    DEFAULT_TRAIN,
    MAX_WAGONS,
    MIN_WAGONS,
    TrainGenerator,
    WWII_TRAIN,
    consist_for,
    trains_lua,
)
from game.sim.missionresultsprocessor import MissionResultsProcessor
from game.theater.player import Player
from game.theater.supply import SupplyStatus, supply_status
from game.theater.transitnetwork import TransitConnection, TransitNetwork
from game.transfers import ConvoyMap, Train, TransferOrder
from game.unitmap import UnitMap

TERRAIN = GermanyColdWar()


class _Cp:
    def __init__(self, name: str, x: float, in_contact: bool = False) -> None:
        self.name = name
        self.position = Point(x, 0, TERRAIN)
        self.captured = Player.BLUE
        self.has_active_frontline = in_contact
        self.rail_lines: dict[Any, tuple[Point, ...]] = {}

    def __repr__(self) -> str:
        return self.name


def _pair() -> tuple[Any, Any]:
    kassel, fulda = _Cp("Kassel", -312000.0), _Cp("Fulda", -401000.0)
    line = (Point(-312000, -767000, TERRAIN), Point(-401000, -768000, TERRAIN))
    kassel.rail_lines[fulda] = line
    fulda.rail_lines[kassel] = tuple(reversed(line))
    return kassel, fulda


def _train(units: dict[str, int]) -> Train:
    origin, destination = _pair()
    train = Train(origin, destination)
    train.add_units(
        TransferOrder(origin, destination, cast(Any, dict(units)), Player.BLUE)
    )
    return train


def test_rail_counts_as_ground_supply() -> None:
    front, rear = _Cp("front", 0.0, in_contact=True), _Cp("rear", 1.0)
    network = TransitNetwork()
    network.link_rail(cast(Any, front), cast(Any, rear))
    assert network.link_type(cast(Any, front), cast(Any, rear)) is (
        TransitConnection.Rail
    )
    assert supply_status(cast(Any, front), network, coalition_has_rear=True) is (
        SupplyStatus.SUPPLIED
    )


def test_a_train_runs_its_rail_line() -> None:
    train = _train({"T-72": 3})
    assert train.route_start == train.route[0]
    assert train.route_end == train.route[-1]
    assert train.name.startswith("Train ")
    assert "train" in train.description()


def test_transfers_on_one_rail_pair_share_one_train() -> None:
    origin, destination = _pair()
    convoys = ConvoyMap()
    for _ in range(2):
        convoys.add_train(
            TransferOrder(origin, destination, cast(Any, {"T-72": 2}), Player.BLUE),
            destination,
        )
    trains = list(convoys)
    assert len(trains) == 1
    assert isinstance(trains[0], Train)
    assert trains[0].size == 4


def test_consist_follows_the_era_and_the_cargo() -> None:
    def game(year: int) -> Any:
        return SimpleNamespace(
            date=date(year, 1, 1),
            theater=SimpleNamespace(terrain=SimpleNamespace(name="GermanyCW")),
        )

    assert consist_for(game(1944), 6)[0] == WWII_TRAIN[0]
    cold_war = consist_for(game(1985), 1)
    assert cold_war[0] == DEFAULT_TRAIN[0]
    assert len(cold_war) == 1 + MIN_WAGONS
    assert len(consist_for(game(1985), 99)) == 1 + MAX_WAGONS


def _generate(train: Train) -> tuple[Mission, UnitMap]:
    mission = Mission(TERRAIN)
    unit_map = UnitMap()
    faction = SimpleNamespace(country=SimpleNamespace(name="USA"))
    game = SimpleNamespace(
        date=date(1985, 9, 10),
        theater=SimpleNamespace(terrain=TERRAIN),
        coalitions=[SimpleNamespace(transfers=SimpleNamespace(convoys=[train]))],
        coalition_for=lambda player: SimpleNamespace(faction=faction),
    )
    TrainGenerator(mission, cast(Any, game), unit_map).generate()
    return mission, unit_map


def test_the_train_is_written_as_dcs_writes_one(tmp_path: Path) -> None:
    train = _train({"T-72": 3, "BMP-2": 2})
    mission, unit_map = _generate(train)
    out = tmp_path / "train.miz"
    mission.save(str(out))
    text = zipfile.ZipFile(out).read("mission").decode("utf-8")

    assert '["type"]="Train"' in text
    assert '["wagons"]' in text
    assert '"Locomotive"' in text
    assert text.count('"On Railroads"') == 2 * len(train.route)
    assert "retlab_trains" in text


def test_a_dead_train_loses_its_whole_cargo() -> None:
    train = _train({"T-72": 3, "BMP-2": 2})
    _, unit_map = _generate(train)
    [(train_name, cargo_names)] = unit_map.trains.items()
    assert len(cargo_names) == train.size == 5

    losses = [unit_map.convoy_unit(name) for name in cargo_names]
    MissionResultsProcessor.commit_convoy_losses(
        cast(Any, SimpleNamespace(convoy_losses=losses))
    )
    assert train.size == 0


def test_the_lua_table_parses() -> None:
    lua = lupa.lua51.LuaRuntime()
    lua.execute(trains_lua({'Train "001"-1': ["a #1", "b\\2"]}))
    table = lua.globals().retlab_trains
    assert list(table['Train "001"-1'].values()) == ["a #1", "b\\2"]


class _LoaderCp:
    def __init__(self, name: str, x: float) -> None:
        self.id = name
        self.name = name
        self.position = Point(x, 0, TERRAIN)
        self.rail_lines: dict[Any, tuple[Point, ...]] = {}

    def create_rail_line(self, to: Any, waypoints: Any) -> None:
        self.rail_lines[to] = tuple(waypoints)


class _RailLoader(MizCampaignLoader):
    def __init__(self, cps: list[_LoaderCp], xs: list[float]) -> None:
        self.control_points = {cp.id: cp for cp in cps}  # type: ignore[misc]
        self.theater = SimpleNamespace(  # type: ignore[assignment]
            closest_control_point=lambda p, allow_naval=False: min(
                cps, key=lambda cp: cp.position.distance_to_point(p)
            )
        )
        self._group = SimpleNamespace(
            name="Rail",
            points=[SimpleNamespace(position=Point(x, 0, TERRAIN)) for x in xs],
        )

    @property
    def rail_line_groups(self) -> Any:
        return iter([self._group])


def test_a_drawn_train_binds_a_rail_line_both_ways() -> None:
    a, b = _LoaderCp("A", 0.0), _LoaderCp("B", 50000.0)
    _RailLoader([a, b], [100.0, 20000.0, 49900.0]).add_rail_lines()
    assert [p.x for p in a.rail_lines[b]] == [100.0, 20000.0, 49900.0]
    assert [p.x for p in b.rail_lines[a]] == [49900.0, 20000.0, 100.0]


def test_a_train_drawn_back_onto_its_base_is_skipped() -> None:
    a, b = _LoaderCp("A", 0.0), _LoaderCp("B", 50000.0)
    _RailLoader([a, b], [100.0, 900.0]).add_rail_lines()
    assert a.rail_lines == {}
