"""Shipped presets carry the newest variant of a missile family the pylon takes.

The date restriction only steps a weapon DOWN its fallback chain, so a preset authored
with an AIM-9L stays an AIM-9L in a 2020 campaign. Carrying the newest variant lets an
early campaign degrade it instead. Families are the clear upgrades only (2026-10-17 DM
call): not AIM-9L to AIM-9P, no seeker swaps, no mod-only missiles.
"""

import difflib
from pathlib import Path
from typing import Any

import pytest
import dcs.helicopters
import dcs.planes
from dcs.lua.parse import loads

from game import persistency
from game.data.weapons import Pylon, Weapon
from game.dcs.aircrafttype import AircraftType

FAMILIES = (
    ("AIM-9B", "AIM-9J", "AIM-9L", "AIM-9M", "AIM-9X"),
    ("2xAIM-9B", "2xAIM-9J", "2xAIM-9L", "2xAIM-9M", "2xAIM-9X"),
    ("AIM-7E", "AIM-7E-2", "AIM-7F", "AIM-7M"),
    ("AGM-65G", "AGM-65K"),
    ("R-27R", "R-27ER"),
    ("AGM-45A Shrike ARM", "AGM-45B Shrike ARM (Imp)"),
)
RANK = {
    group: (f, r) for f, family in enumerate(FAMILIES) for r, group in enumerate(family)
}
# A newer store on a different rack or adapter is not the same fit.
SAME_FIT_SIMILARITY = 0.6
# The file's own header: the mod's newer Sidewinders did not load, so it flies the 9B.
EXEMPT = frozenset({"vwv_crusader.lua"})


def _payload_files() -> list[Path]:
    return sorted(Path("resources/customized_payloads").glob("*.lua"))


def _parse(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    body = text.replace("local unitPayloads", "unitPayloads")
    return loads(body.split("return unitPayloads")[0])["unitPayloads"]


@pytest.fixture(scope="module", autouse=True)
def _persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(
        str(tmp_path_factory.mktemp("saved_games")),
        prefer_liberation_payloads=False,
        port=16888,
    )


def test_shipped_presets_carry_the_newest_variant() -> None:
    stale: list[str] = []
    for path in _payload_files():
        if path.name in EXEMPT:
            continue
        try:
            data = _parse(path)
        except Exception:
            continue
        unit = dcs.planes.plane_map.get(data["name"]) or (
            dcs.helicopters.helicopter_map.get(data["name"])
        )
        aircraft = next(AircraftType.for_dcs_type(unit), None) if unit else None
        if aircraft is None:
            continue
        for payload in data["payloads"].values():
            for entry in payload["pylons"].values():
                weapon = Weapon.with_clsid(entry["CLSID"])
                if weapon is None or weapon.weapon_group.name not in RANK:
                    continue
                family, rank = RANK[weapon.weapon_group.name]
                try:
                    pylon = Pylon.for_aircraft(aircraft, entry["num"])
                except Exception:
                    continue
                for newer in pylon.allowed:
                    newer_rank = RANK.get(newer.weapon_group.name)
                    if (
                        newer_rank is not None
                        and newer_rank[0] == family
                        and newer_rank[1] > rank
                        and difflib.SequenceMatcher(
                            None, newer.name, weapon.name
                        ).ratio()
                        >= SAME_FIT_SIMILARITY
                    ):
                        stale.append(
                            f"{path.name} [{payload['name']}] station "
                            f"{entry['num']}: {weapon.name} -> {newer.name}"
                        )
                        break
    assert not stale, "Presets carry an older variant than the pylon takes:\n" + (
        "\n".join(stale)
    )
