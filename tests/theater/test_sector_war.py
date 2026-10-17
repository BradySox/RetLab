"""Sector war step 2: sectors decide the fight (§111).

Built on Abchazian Blitz, like test_sectors.py.
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from game import persistency
from game.campaignloader.campaign import Campaign
from game.factions import FACTIONS
from game.game import Game
from game.settings import Settings
from game.sim import GameUpdateEvents
from game.sim.missionresultsprocessor import MissionResultsProcessor, sectors_won
from game.theater.player import Player
from game.theater.sectors import (
    BLUE,
    RED,
    land_control_points,
    sector_map_for,
    territory_for,
)
from game.theater.sectorwar import SectorWar, sector_neighbours, war_of
from game.theater.start_generator import GameGenerator, GeneratorSettings, ModSettings

NM = 1852.0


def _new_game() -> Any:
    persistency.setup(tempfile.mkdtemp(), False, 0)
    campaign = Campaign.from_file(Path("resources/campaigns/Abchazian Blitz.yaml"))
    theater = campaign.load_theater(campaign.advanced_iads)
    settings = Settings()
    if campaign.settings:
        settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    game = GameGenerator(
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
    game.begin_turn_0(squadrons_start_full=True)
    return game


@pytest.fixture(scope="module")
def game() -> Any:
    return _new_game()


def _base_sector(game: Any, cp: Any) -> str:
    sector = sector_map_for(game.theater).sector_at(cp.position.x, cp.position.y)
    assert sector is not None and sector.control_point_id == cp.id
    return sector.name


def _side_at(game: Any, war: SectorWar, x: float, y: float) -> Any:
    sector = sector_map_for(game.theater).sector_at(x, y)
    return None if sector is None else war.owners.get(sector.name)


def test_a_new_game_starts_the_war_with_every_base_on_its_side(game: Any) -> None:
    war = war_of(game)
    assert war is not None
    assert BLUE in war.owners.values() and RED in war.owners.values()
    for cp in land_control_points(game.theater):
        if cp.captured.is_neutral:
            continue
        expected = BLUE if cp.captured.is_blue else RED
        assert war.owners[_base_sector(game, cp)] == expected, cp.name
    assert war.fallen_bases(game.theater) == []


def test_the_front_sits_where_the_route_enters_red_sectors(game: Any) -> None:
    war = war_of(game)
    assert war is not None
    for front in game.theater.conflicts():
        progress = front._blue_route_progress
        behind = front.point_along_route_from_blue(max(progress - 0.5 * NM, 0))
        ahead = front.point_along_route_from_blue(
            min(progress + 0.5 * NM, front.route_length - 1)
        )
        assert _side_at(game, war, behind.x, behind.y) == BLUE, front.name
        assert _side_at(game, war, ahead.x, ahead.y) == RED, front.name


def test_win_sizes() -> None:
    assert sectors_won(0.5, winner_attacked=False) == 2
    assert sectors_won(0.3, winner_attacked=False) == 1
    assert sectors_won(0.1, winner_attacked=True) == 1
    assert sectors_won(0.1, winner_attacked=False) == 0


def test_a_win_takes_the_nearest_enemy_sectors_on_the_border(game: Any) -> None:
    war = war_of(game)
    assert war is not None
    saved = dict(war.owners)
    front = next(iter(game.theater.conflicts()))
    sector_map = sector_map_for(game.theater)
    neighbours = sector_neighbours(sector_map)
    by_name = {sector.name: sector for sector in sector_map.sectors}
    before = front._blue_route_progress
    try:
        taken = war.take_sectors(front, Player.BLUE, 1)
        assert len(taken) == 1
        sector = by_name[taken[0]]
        assert saved[sector.name] == RED
        assert any(
            saved.get(sector_map.sectors[other].name) == BLUE
            for other in neighbours[sector.id]
        )
        assert war.owners[sector.name] == BLUE
        front.update_position()
        assert front._blue_route_progress >= before
    finally:
        war.owners = saved
        war.version += 1
        front.update_position()


def test_a_base_falls_with_its_sector() -> None:
    game = _new_game()
    war = war_of(game)
    assert war is not None
    front = next(iter(game.theater.conflicts()))
    red_cp = front.red_cp
    war.set_owner(_base_sector(game, red_cp), BLUE)
    processor = MissionResultsProcessor(game)
    processor.commit_sector_war(
        SimpleNamespace(base_captures=[]), GameUpdateEvents()  # type: ignore[arg-type]
    )
    assert red_cp.captured.is_blue
    assert war.fallen_bases(game.theater) == []


def test_a_side_with_no_front_line_units_takes_no_sectors(game: Any) -> None:
    war = war_of(game)
    assert war is not None
    front = next(iter(game.theater.conflicts()))
    saved = dict(war.owners)
    red_armor = dict(front.red_cp.base.armor)
    processor = MissionResultsProcessor(game)
    try:
        front.red_cp.base.armor.clear()
        processor.take_sectors(front.red_cp, front.blue_cp, 0.5, True)
        assert war.owners == saved
        tank = next(iter(game.red.faction.frontline_units))
        front.red_cp.base.armor[tank] = 4
        assert front.red_cp.base.total_frontline_units > 0
        processor.take_sectors(front.red_cp, front.blue_cp, 0.5, True)
        assert war.owners != saved
    finally:
        front.red_cp.base.armor.clear()
        front.red_cp.base.armor.update(red_armor)
        war.owners = saved
        war.version += 1


def test_shapes_follow_the_owners_not_the_change_count(game: Any) -> None:
    # A reloaded save re-flown differently reaches the same version with other
    # owners; the module caches outlive the game and must not serve the old shape.
    war = war_of(game)
    assert war is not None
    front = next(iter(game.theater.conflicts()))
    saved = dict(war.owners)
    version = war.version
    try:
        war.take_sectors(front, Player.BLUE, 1)
        first = territory_for(game.theater)
        war.owners = dict(saved)
        war.version = version
        war.take_sectors(front, Player.RED, 1)
        assert war.version == version + 1
        assert territory_for(game.theater) is not first
    finally:
        war.owners = saved
        war.version += 1


def test_a_base_taken_in_the_mission_takes_its_sector(game: Any) -> None:
    war = war_of(game)
    assert war is not None
    front = next(iter(game.theater.conflicts()))
    name = _base_sector(game, front.red_cp)
    saved = dict(war.owners)
    blue_cp = front.blue_cp
    try:
        war.owners[name] = BLUE
        war.claim_base(game.theater, front.red_cp)
        assert war.owners[name] == RED
        war.claim_base(game.theater, blue_cp)
        assert war.owners[_base_sector(game, blue_cp)] == BLUE
    finally:
        war.owners = saved
        war.version += 1


def test_the_setting_off_puts_the_front_back_on_strength(game: Any) -> None:
    front = next(iter(game.theater.conflicts()))
    try:
        game.settings.sector_war = False
        assert war_of(game) is None
        assert front._sector_war_progress() is None
    finally:
        game.settings.sector_war = True


def test_a_save_from_before_keeps_the_old_front_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings()
    assert settings.sector_war
    monkeypatch.setattr(Game, "on_load", lambda self: None)
    restored = Game.__new__(Game)
    restored.__setstate__({"settings": settings, "laser_code_registry": None})
    assert restored.settings.sector_war is False
    assert restored.sector_war is None


def test_a_road_through_enemy_sectors_carries_no_convoys(game: Any) -> None:
    from game.theater.sectorwar import road_is_cut
    from game.theater.transitnetwork import TransitConnection, TransitNetworkBuilder

    war = war_of(game)
    assert war is not None
    pairs = [
        (cp, other)
        for cp in game.theater.player_points()
        for other in cp.connected_points
        if other.captured.is_blue and not cp.is_fleet and not other.is_fleet
    ]
    assert pairs, "no blue road link to cut"
    a, b = pairs[0]
    assert not road_is_cut(game.theater, a, b)
    saved = dict(war.owners)
    sector_map = sector_map_for(game.theater)
    route = list(a.convoy_route_to(b))
    middle = route[len(route) // 2]
    sector = sector_map.sector_at(middle.x, middle.y)
    assert sector is not None
    try:
        war.owners[sector.name] = RED
        war.version += 1
        assert road_is_cut(game.theater, a, b)
        network = TransitNetworkBuilder(game.theater, Player.BLUE).build()
        assert (
            not network.has_link(a, b)
            or network.link_type(a, b) != TransitConnection.Road
        )
    finally:
        war.owners = saved
        war.version += 1
