"""Shipped presets named for a ground-attack task are fits the planner can pick.

Liberation filled every task name with a fit, so pure fighters listed an "ANTISHIP" fit
of four air-to-air missiles (MiG-25PD), and jets that never fly a task kept a fit for it.
Neither was ever planned; both only cluttered the payload tab's Loadout list.
"""

import re
from pathlib import Path
from typing import Any

import dcs.helicopters
import dcs.planes
import pytest
from dcs.lua.parse import loads
from dcs.weapons_data import weapon_ids

from game import persistency
from game.ato.loadouts import Loadout
from game.dcs.aircrafttype import AircraftType

GROUND_TASK_NAMES = frozenset(
    {
        "STRIKE",
        "CAS",
        "CAS MAVERICK F",
        "ANTISHIP",
        "SEAD",
        "DEAD",
        "BAI",
        "OCA",
        "RUNWAY_ATTACK",
        "RUNWAY_STRIKE",
    }
)
# Air-to-air missiles, plus stores that carry no weapon at all.
NOT_GROUND_ATTACK = re.compile(
    r"AAM|AIM-|Sidewinder|Sparrow|AMRAAM|Phoenix|K-13|R-(?:3[RS]|2[347]|33|37|40|60|73"
    r"|77|98)|Magic|MICA|Super 530|R550|PL-\d|Python|Derby|Shafrir|IRIS-T|Meteor"
    r"|Mistral|Aspide|Skyflash|ASRAAM|AA-\d+|[Ff]uel|[Tt]ank|PTB|ECM|Sorbtsiya|Eclair"
    r"|<CLEAN>|[Ss]moke"
)


@pytest.fixture(scope="module", autouse=True)
def _persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(
        str(tmp_path_factory.mktemp("saved_games")),
        prefer_liberation_payloads=False,
        port=16889,
    )


def _shipped() -> list[tuple[str, Any]]:
    shipped = []
    for path in sorted(Path("resources/customized_payloads").glob("*.lua")):
        text = path.read_text(encoding="utf-8")
        body = text.replace("local unitPayloads", "unitPayloads")
        try:
            shipped.append((path.name, loads(body.split("return unitPayloads")[0])))
        except Exception:
            continue
    return [(name, data["unitPayloads"]) for name, data in shipped]


def _store_name(clsid: str) -> str:
    weapon: Any = weapon_ids.get(clsid)
    return weapon["name"] if weapon else clsid


def test_ground_attack_presets_carry_a_ground_attack_store() -> None:
    air_to_air_only: list[str] = []
    for name, data in _shipped():
        for payload in data["payloads"].values():
            if payload["name"] not in GROUND_TASK_NAMES:
                continue
            stores = [_store_name(p["CLSID"]) for p in payload["pylons"].values()]
            if stores and all(NOT_GROUND_ATTACK.search(s) for s in stores):
                air_to_air_only.append(f"{name}: {payload['name']}")
    assert not air_to_air_only, air_to_air_only


def test_ground_attack_presets_belong_to_a_task_the_airframe_flies() -> None:
    unreachable: list[str] = []
    for name, data in _shipped():
        unit = dcs.planes.plane_map.get(data["unitType"]) or (
            dcs.helicopters.helicopter_map.get(data["unitType"])
        )
        variants = list(AircraftType.for_dcs_type(unit)) if unit else []
        if not variants:
            continue
        reachable = {
            loadout
            for variant in variants
            for task in variant.task_priorities
            for loadout in Loadout.default_loadout_names_for(task)
        }
        for payload in data["payloads"].values():
            if payload["name"] in GROUND_TASK_NAMES - reachable:
                unreachable.append(f"{name}: {payload['name']}")
    assert not unreachable, unreachable
