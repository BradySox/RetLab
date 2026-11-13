"""The hidden squad and crate templates MOOSE's CTLD clones (ctldtemplates.py)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs import Mission
from dcs.terrain import Caucasus

from game.missiongenerator.ctldtemplates import (
    CtldTemplateGenerator,
    squad_for_size,
    squad_types,
)
from game.missiongenerator.missiondata import CargoInfo, LogisticsInfo, MissionData
from game.theater.player import Player


def _game(tailor: bool) -> Any:
    terrain = Caucasus()
    country = SimpleNamespace(name="USA")
    red_country = SimpleNamespace(name="Russia")
    return SimpleNamespace(
        settings=SimpleNamespace(
            plugin_option=lambda key: tailor if key == "ctld.tailorctld" else True
        ),
        coalition_for=lambda player: SimpleNamespace(
            faction=SimpleNamespace(
                country=country if player is Player.BLUE else red_country
            )
        ),
        theater=SimpleNamespace(terrain=terrain),
    )


def _logistics(cabin: int, cargo: list[CargoInfo]) -> LogisticsInfo:
    transport = SimpleNamespace(cabin_size=cabin)
    return LogisticsInfo(
        pilot_names=["Huey 1-1"],
        transport=transport,  # type: ignore[arg-type]
        blue=Player.BLUE,
        group_name="Huey 1",
        cargo=cargo,
    )


def _generate(tailor: bool, logistics: list[LogisticsInfo]) -> tuple[Any, Mission]:
    mission = Mission(Caucasus())
    data = MissionData()
    data.logistics = logistics
    templates = CtldTemplateGenerator(mission, _game(tailor), data).generate()
    return templates, mission


def test_squads_mirror_the_old_ctld_mix() -> None:
    assert squad_for_size(24) == (12, 4, 4, 3, 1)
    assert squad_for_size(8) == (4, 2, 2, 0, 0)
    assert squad_types(Player.RED, squad_for_size(6)) == [
        "Infantry AK",
        "Infantry AK",
        "Infantry AK",
        "Infantry AK",
        "Paratrooper AKS-74",
        "Paratrooper RPG-16",
    ]
    # The JTAC counts as a rifleman (24 = 13 rifles + 4 + 4 + 3).
    assert len(squad_types(Player.BLUE, squad_for_size(24))) == 24


def test_no_logistics_writes_no_templates() -> None:
    templates, mission = _generate(True, [])
    assert templates.troops == [] and templates.crates == []
    assert not mission.country("USA").vehicle_group


def test_one_hidden_squad_per_size_and_cabin_and_one_crate_per_type() -> None:
    cargo = [CargoInfo("M1043 HMMWV Armament", "Huey 1crate_spawn", 2)]
    templates, mission = _generate(True, [_logistics(8, cargo)])
    sizes = sorted(t.size for t in templates.troops)
    assert sizes == [2, 4, 6, 8, 10, 12, 24]
    assert [t.unit_type for t in templates.crates] == ["M1043 HMMWV Armament"]
    assert all(t.side is Player.BLUE for t in templates.troops)
    groups = {g.name: g for g in mission.country("USA").vehicle_group}
    squad = groups["CTLD blue Retribution Troops (24)"]
    assert len(squad.units) == 24
    assert squad.late_activation and squad.hidden
    assert [t.jtac for t in templates.troops if t.size == 24] == [True]


def test_the_stock_list_comes_with_the_option_off() -> None:
    templates, _ = _generate(False, [_logistics(8, [])])
    stock_troops = [t.label for t in templates.troops if t.stock]
    stock_crates = [t.label for t in templates.crates if t.stock]
    assert stock_troops == ["Standard Group", "Anti Air", "Anti Tank", "JTAC Group"]
    assert stock_crates == [
        "Humvee - MG",
        "Humvee - TOW",
        "M1097 Avenger",
        "M-818 Ammo Truck",
    ]
