"""A depot's owner at New Game is the owner a reload gives it (§56, #960).

New Game bound depots through the campaign loader's rule and every load re-homed
them to the nearest land base, so Abchazian Blitz's Static Garage A-16 and A-17
started blue at Sukhumi and turned red on the first reload.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from game import persistency
from game.campaignloader.campaign import Campaign
from game.factions import FACTIONS
from game.migrator import Migrator
from game.missiongenerator.motorpoolpopulator import MotorpoolPopulator
from game.settings import Settings
from game.theater.start_generator import (
    GameGenerator,
    GeneratorSettings,
    ModSettings,
)
from game.theater.theatergroundobject import MotorpoolGroundObject

CAMPAIGNS = Path("resources/campaigns")


def _new_game(name: str) -> Any:
    campaign = Campaign.from_file(CAMPAIGNS / f"{name}.yaml")
    theater = campaign.load_theater(campaign.advanced_iads)
    settings = Settings()
    if campaign.settings:
        settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    settings.motorpool_enabled = True
    return GameGenerator(
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


def _owners(game: Any) -> dict[str, str]:
    return {
        tgo.original_name: cp.name
        for cp in game.theater.controlpoints
        for tgo in cp.connected_objectives
        if isinstance(tgo, MotorpoolGroundObject)
    }


def test_abchazian_blitz_depots_keep_their_owner_on_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(persistency, "_dcs_saved_game_folder", str(tmp_path))
    game = _new_game("Abchazian Blitz")

    at_new_game = _owners(game)
    assert at_new_game

    # What a load does to depots: Migrator._ensure_motorpool_tgos, then re-home.
    migrator = Migrator.__new__(Migrator)
    migrator.game = game
    migrator._ensure_motorpool_tgos()
    MotorpoolPopulator(game)._rehome_motorpools()

    assert _owners(game) == at_new_game
