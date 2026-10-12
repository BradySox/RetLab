"""Sectors, territory and the battles along the border (§111).

Built on Abchazian Blitz, the Sukhumi front of the Reddit map that started it.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from unittest.mock import MagicMock

import pytest
from dcs.coalition import Coalition
from dcs.mapping import Point
from dcs.mission import Mission
from shapely.geometry import LineString, Point as ShapelyPoint, Polygon

from game import persistency
from game.campaignloader.campaign import Campaign
from game.data.units import UnitClass
from game.factions import FACTIONS
from game.ground_forces.ai_ground_planner import (
    CombatGroup,
    CombatGroupRole,
    GroundPlanner,
)
from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.countryassigner import CountryAssigner
from game.missiongenerator.drawingsgenerator import DrawingsGenerator
from game.missiongenerator.flotgenerator import (
    FlotGenerator,
    battle_slots,
    pick_battles,
)
from game.missiongenerator.frontlineconflictdescription import (
    FrontLineConflictDescription,
)
from game.missiongenerator.missiondata import MissionData
from game.radio.radios import RadioRegistry
from game.server.sectors.models import SectorsJs, TerritoryJs
from game.settings import Settings
from game.theater import sectors
from game.theater.frontbattles import BattleSite, battles_for, front_battles
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
from game.unitmap import UnitMap

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


def test_battles_stand_on_the_drivable_border_one_per_sector(game: Any) -> None:
    landmap = game.theater.landmap
    territory = territory_for(game.theater)
    border = territory.blue.boundary.intersection(territory.red.boundary)
    for front in game.theater.conflicts():
        found = front_battles(game.theater, front)
        assert found.sites, front.name
        assert len({site.sector for site in found.sites}) == len(found.sites)
        alongs = [site.along for site in found.sites]
        assert alongs == sorted(alongs)
        for site in found.sites:
            point = ShapelyPoint(site.x, site.y)
            assert border.distance(point) < 10, site.sector
            assert landmap.inclusion_zone_only.contains(point), site.sector
            for offset in (-site.width / 2, 0.0, site.width / 2):
                x, y = site.point_along(offset)
                assert landmap.inclusion_zone_only.distance(ShapelyPoint(x, y)) < 10


def test_blue_attacks_into_red_ground_at_every_battle(game: Any) -> None:
    territory = territory_for(game.theater)
    raster = sector_map_for(game.theater).raster
    for front in game.theater.conflicts():
        for site in front_battles(game.theater, front).sites:
            ahead = Point(site.x, site.y, game.theater.terrain).point_from_heading(
                site.blue_forward, 2 * NM
            )
            behind = Point(site.x, site.y, game.theater.terrain).point_from_heading(
                site.blue_forward + 180, 2 * NM
            )
            assert territory.labels[raster.index_at(ahead.x, ahead.y)] == RED
            assert territory.labels[raster.index_at(behind.x, behind.y)] == BLUE


def test_a_front_fills_no_more_border_than_the_maximum_width(game: Any) -> None:
    width = game.settings.max_frontline_width * 1000
    for front in game.theater.conflicts():
        line = front_battles(game.theater, front).line
        assert LineString(line).length <= width + 1


def test_the_setting_puts_units_back_on_one_line(game: Any) -> None:
    front = next(iter(game.theater.conflicts()))
    game.settings.front_line_battles_along_border = False
    try:
        assert battles_for(game.theater, front) is None
    finally:
        game.settings.front_line_battles_along_border = True
    assert battles_for(game.theater, front) is not None


def test_front_units_are_spread_over_the_battles(game: Any) -> None:
    front = next(iter(game.theater.conflicts()))
    for cp in (front.blue_cp, front.red_cp):
        faction = cp.coalition.faction
        units: dict[Any, int] = {}
        for unit_class, count in ((UnitClass.TANK, 16), (UnitClass.IFV, 12)):
            kinds = [u for u in faction.ground_units if u.unit_class is unit_class]
            if kinds:
                units[kinds[0]] = count
        cp.base.commission_units(units)
        planner = GroundPlanner(cp, game)
        planner.plan_groundwar()
        game.ground_planners[cp.id] = planner
    mission = Mission(game.theater.terrain)
    country_assigner = CountryAssigner(game)
    mission.coalition["blue"] = Coalition("blue")
    mission.coalition["red"] = Coalition("red")
    for country in country_assigner.blue_countries:
        mission.coalition["blue"].add_country(country)
    for country in country_assigner.red_countries:
        mission.coalition["red"].add_country(country)
    generator = FlotGenerator(
        mission,
        FrontLineConflictDescription.frontline_cas_conflict(front, game.theater),
        game,
        game.ground_planners[front.blue_cp.id].units_per_cp[front.red_cp.id],
        game.ground_planners[front.red_cp.id].units_per_cp[front.blue_cp.id],
        CombatStance.AGGRESSIVE,
        CombatStance.DEFENSIVE,
        UnitMap(),
        RadioRegistry(),
        MissionData(),
    )
    generator.generate()
    assert generator.battle_sites
    for side in ("blue", "red"):
        positions = [
            group.position
            for country in mission.coalition[side].countries.values()
            for group in country.vehicle_group
        ]
        assert positions, side
        joined = set()
        for position in positions:
            nearest = min(
                range(len(generator.battle_sites)),
                key=lambda i: position.distance_to_point(
                    Point(
                        generator.battle_sites[i].x,
                        generator.battle_sites[i].y,
                        game.theater.terrain,
                    )
                ),
            )
            joined.add(nearest)
        assert joined == set(range(len(generator.battle_sites))), side


def test_wedges_are_dealt_across_the_battles() -> None:
    wedges = [CombatGroup(CombatGroupRole.TANK, MagicMock(), 1) for _ in range(5)]
    member = CombatGroup(CombatGroupRole.SHORAD, MagicMock(), 1)
    member.anchor = wedges[3]
    slots = battle_slots([*wedges, member], 2)
    assert [slots[id(w)][0] for w in wedges] == [0, 1, 0, 1, 0]
    assert slots[id(member)] == slots[id(wedges[3])]
    assert all(0 < slots[id(w)][1] < 1 for w in wedges)


def test_battles_are_picked_from_end_to_end() -> None:
    sites = tuple(BattleSite(0, 0, 0, NM, f"S{i}", along=float(i)) for i in range(7))
    assert [s.sector for s in pick_battles(sites, 3)] == ["S0", "S3", "S6"]
    assert pick_battles(sites, 9) == list(sites)
    assert [s.sector for s in pick_battles(sites, 1)] == ["S3"]
