"""Every radar the fork can field is a radar Skynet knows.

A radar Skynet has no entry for fails quietly. An EWR is added but reports no
contacts (the FPS-117, the P-37 whose entry sat outside its searchRadar block,
both Nebos). A SAM site is switched on and left on outside the network (the
CurrentHill Patriot, Pantsir-S2 and Tor M2K, written without their CH_ prefix).
Found 2026-10-16 comparing with juanjux/Skynet-IADS.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from game.data.units import UnitClass
from game.dcs.groundunittype import GroundUnitType
from tests.lua.harness import REPO_ROOT, DcsPluginHarness

ENGINE = "resources/plugins/skynetiads/skynet-iads-compiled.lua"

RADAR_CLASSES = {
    UnitClass.EARLY_WARNING_RADAR,
    UnitClass.SEARCH_RADAR,
    UnitClass.SEARCH_TRACK_RADAR,
    UnitClass.TRACK_RADAR,
}

# DCS unit id -> why Skynet does not need it.
NOT_FOR_SKYNET = {
    "Patriot ECS": "control station, kept under 'misc' as upstream does",
    "CH_MIM104_ECS": "control station, kept under 'misc' as upstream does",
    "CH_MIM104_ECS_KAT1": "control station, kept under 'misc' as upstream does",
    "CH_MonolitB": "coastal anti-ship radar; coastal groups never enter the IADS",
    "Silkworm_SR": "coastal anti-ship radar; coastal groups never enter the IADS",
    "FuMG-401": "WWII Freya; there is no SAM for it to cue",
    "ELM2084_MMR_AD_RT": "Iron Dome and David's Sling have no Skynet profile yet",
    "ELM2084_MMR_AD_SC": "Iron Dome and David's Sling have no Skynet profile yet",
}

KNOWN_IDS = """
(function()
    local ids = {}
    for _, entry in pairs(SkynetIADS.database) do
        for _, role in ipairs({ "searchRadar", "trackingRadar", "launchers" }) do
            for id, _ in pairs(entry[role] or {}) do ids[#ids + 1] = id end
        end
    end
    return ids
end)()
"""


def _strings(value: Any, into: set[str]) -> None:
    if isinstance(value, str):
        into.add(value)
    elif isinstance(value, dict):
        for item in value.values():
            _strings(item, into)
    elif isinstance(value, list):
        for item in value:
            _strings(item, into)


def _layout_unit_types(value: Any, into: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "unit_types":
                into.update(item)
            else:
                _layout_unit_types(item, into)
    elif isinstance(value, list):
        for item in value:
            _layout_unit_types(item, into)


def _fielded_radar_ids() -> set[str]:
    names: set[str] = set()
    for path in (REPO_ROOT / "resources/factions").glob("*.json"):
        _strings(json.loads(path.read_text(encoding="utf-8")), names)
    for path in (REPO_ROOT / "resources/groups").glob("*.yaml"):
        _strings(yaml.safe_load(path.read_text(encoding="utf-8")), names)
    layout_ids: set[str] = set()
    for path in (REPO_ROOT / "resources/layouts").rglob("*.yaml"):
        _layout_unit_types(yaml.safe_load(path.read_text(encoding="utf-8")), layout_ids)

    radars = set()
    for dcs_type in GroundUnitType.each_dcs_type():
        for unit in GroundUnitType.for_dcs_type(dcs_type):
            if unit.unit_class not in RADAR_CLASSES:
                continue
            if unit.variant_id in names or dcs_type.id in layout_ids:
                radars.add(dcs_type.id)
    return radars


def _skynet_ids() -> set[str]:
    harness = DcsPluginHarness()
    harness.set_retribution_config()
    harness.load_plugin_script(ENGINE)
    return set(harness.lua.eval(KNOWN_IDS).values())


def test_every_fielded_radar_has_a_skynet_entry() -> None:
    missing = _fielded_radar_ids() - _skynet_ids() - set(NOT_FOR_SKYNET)
    assert not missing, f"Skynet has no entry for {sorted(missing)}"


def test_the_exemptions_are_still_fielded() -> None:
    # An exemption for a radar nothing fields any more hides nothing; drop it.
    assert set(NOT_FOR_SKYNET) <= _fielded_radar_ids()


def test_the_exemptions_are_still_unknown_to_skynet() -> None:
    # Once a profile lands, its exemption must go so the check covers it.
    assert not set(NOT_FOR_SKYNET) & _skynet_ids()
