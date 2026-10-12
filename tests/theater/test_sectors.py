"""Sectors and territory (§111, step 1: drawn only).

Built on Abchazian Blitz, the Sukhumi front of the Reddit map that started it.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from dcs.mission import Mission
from shapely.geometry import Polygon

from game import persistency
from game.campaignloader.campaign import Campaign
from game.factions import FACTIONS
from game.missiongenerator.drawingsgenerator import DrawingsGenerator
from game.server.sectors.models import SectorsJs, TerritoryJs
from game.settings import Settings
from game.theater import sectors
from game.theater.sectors import (
    BLUE,
    RED,
    build_sector_map,
    hole_free_pieces,
    land_control_points,
    sector_map_for,
    territory_for,
)
from game.theater.start_generator import (
    GameGenerator,
    GeneratorSettings,
    ModSettings,
)

NM = 1852.0


@pytest.fixture(scope="module")
def game() -> Any:
    persistency.setup(tempfile.mkdtemp(), False, 0)
    campaign = Campaign.from_file(Path("resources/campaigns/Abchazian Blitz.yaml"))
    theater = campaign.load_theater(campaign.advanced_iads)
    settings = Settings()
    if campaign.settings:
        settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    new_game = GameGenerator(
        player=FACTIONS[campaign.recommended_player_faction],
        enemy=FACTIONS[campaign.recommended_enemy_faction],
        theater=theater,
        air_wing_config=campaign.load_air_wing_config(theater),
        settings=settings,
        generator_settings=GeneratorSettings(
            start_date=datetime(2000, 1, 1),
            start_time=campaign.recommended_start_time,
            player_budget=campaign.recommended_player_money,
            enemy_budget=campaign.recommended_enemy_money,
            inverted=False,
            advanced_iads=campaign.advanced_iads,
            no_carrier=False,
            no_lha=False,
            no_player_navy=False,
            no_enemy_navy=False,
            tgo_config=campaign.load_ground_forces_config(),
            carrier_config=campaign.load_carrier_config(),
            squadrons_start_full=True,
        ),
        mod_settings=ModSettings(),
        campaign_name=campaign.name,
    ).generate()
    new_game.begin_turn_0(squadrons_start_full=True)
    return new_game


def test_every_land_base_seeds_its_own_sector(game: Any) -> None:
    sector_map = sector_map_for(game.theater)
    for cp in land_control_points(game.theater):
        sector = sector_map.sector_at(cp.position.x, cp.position.y)
        assert sector is not None, f"{cp.name} is in no sector"
        assert sector.control_point_id == cp.id, f"{cp.name} is in {sector.name}"


def test_sector_names_are_unique_and_phonetic(game: Any) -> None:
    sector_map = sector_map_for(game.theater)
    names = [sector.name for sector in sector_map.sectors]
    assert len(names) == len(set(names))
    for name in names:
        row, _, column = name.rpartition("-")
        assert row.rstrip("0123456789") in sectors.PHONETIC, name
        assert column.rstrip("ABCDEFGHIJ").isdigit(), name


def test_sectors_are_about_ten_nm_across(game: Any) -> None:
    sector_map = sector_map_for(game.theater)
    raster = sector_map.raster
    land_cells = int((raster.cost > 0).sum())
    mean_area = land_cells * raster.cell**2 / len(sector_map.sectors)
    side_nm = mean_area**0.5 / NM
    assert 7 <= side_nm <= 12, side_nm


def test_sectors_are_the_same_every_time(game: Any) -> None:
    first = build_sector_map(game.theater)
    second = build_sector_map(game.theater)
    assert [s.name for s in first.sectors] == [s.name for s in second.sectors]
    assert (first.labels == second.labels).all()


def test_each_base_stands_in_its_own_sides_territory(game: Any) -> None:
    territory = territory_for(game.theater)
    raster = sector_map_for(game.theater).raster
    for cp in land_control_points(game.theater):
        if cp.captured.is_neutral:
            continue
        index = raster.land_index_near(cp.position.x, cp.position.y)
        assert index is not None
        expected = BLUE if cp.captured.is_blue else RED
        assert territory.labels[index] == expected, cp.name


def test_the_border_runs_through_the_front(game: Any) -> None:
    territory = territory_for(game.theater)
    raster = sector_map_for(game.theater).raster
    fronts = list(game.theater.conflicts())
    assert fronts
    for front in fronts:
        route, progress = sectors._route_progress(front)
        behind = route.interpolate(max(progress - 3 * NM, 0))
        ahead = route.interpolate(min(progress + 3 * NM, route.length))
        behind_index = raster.land_index_near(behind.x, behind.y)
        ahead_index = raster.land_index_near(ahead.x, ahead.y)
        assert territory.labels[behind_index] == BLUE, front.name
        assert territory.labels[ahead_index] == RED, front.name


def test_the_two_sides_never_overlap(game: Any) -> None:
    territory = territory_for(game.theater)
    assert territory.blue.intersection(territory.red).area < NM * NM


def test_a_country_holding_no_base_is_nobodys(game: Any) -> None:
    from game.theater.neutralborder import NEUTRAL

    territory = territory_for(game.theater)
    raster = sector_map_for(game.theater).raster
    checked = 0
    for zone in game.theater.neutral_border_zones:
        if zone.posture_in(game.theater) != NEUTRAL:
            continue
        point = zone.label_point()
        if point is None:
            continue
        index = raster.index_at(*point)
        if index is None:
            continue
        assert territory.labels[index] == -1, zone.country
        checked += 1
    assert checked, "no neutral country inside the war region to check"


def test_a_pocket_is_drawn_without_holes() -> None:
    outer = Polygon([(0, 0), (0, 100), (100, 100), (100, 0)])
    hole = [(40, 40), (40, 60), (60, 60), (60, 40)]
    pieces = hole_free_pieces(Polygon(outer.exterior.coords, [hole]))
    assert len(pieces) >= 2
    assert all(not piece.interiors for piece in pieces)
    assert sum(piece.area for piece in pieces) == pytest.approx(100 * 100 - 20 * 20)


def test_the_f10_map_gets_both_sides_with_unique_names(game: Any) -> None:
    mission = Mission(game.theater.terrain)
    generator = DrawingsGenerator(mission, game)
    generator.generate_territory()
    names = [drawing.name for drawing in generator.player_layer.objects]
    assert any(name.startswith("Blue territory") for name in names)
    assert any(name.startswith("Red territory") for name in names)
    assert len(names) == len(set(names))


def test_the_web_map_gets_territory_and_sectors(game: Any) -> None:
    territory = TerritoryJs.from_game(game)
    assert territory.blue and territory.red
    sector_list = SectorsJs.from_game(game)
    assert sector_list.edges
    owners = {sector.owner for sector in sector_list.sectors}
    assert {"blue", "red"} <= owners
