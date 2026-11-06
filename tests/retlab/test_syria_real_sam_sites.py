"""Every Syria campaign's drawn (FIXED) SAM sites build as drawn.

The sites come from the Levant template through `tools/place_levant_sam_sites.py`
(docs/dev/design/retlab-real-sam-sites-notes.md). A drawn shooter or radar the
owning side's faction cannot field turns the site into a stock layout with only a
log line to say so, and a drawn unit on a runway strip or stand holds every AI taxi
at that field.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml
from dcs.vehicles import vehicle_map

from game import persistency
from game.campaignloader.campaign import Campaign
from game.data.units import UnitClass
from game.factions import FACTIONS
from game.factions.faction import Faction
from game.theater.airfieldclearance import field_under
from game.theater.exactsite import classify, unit_class_of

CAMPAIGNS = sorted(
    p
    for p in Path("resources/campaigns").glob("*.yaml")
    if yaml.safe_load(p.read_text(encoding="utf-8")).get("theater") == "Syria"
)


def _faction(spec: Any) -> Faction:
    return Faction.from_dict(spec) if isinstance(spec, dict) else FACTIONS[spec]


@pytest.mark.parametrize("path", CAMPAIGNS, ids=lambda p: p.stem)
def test_drawn_sites_build_as_drawn(path: Path, tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), False, 0)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    campaign = Campaign.from_file(path)
    theater = campaign.load_theater(campaign.advanced_iads)
    fieldable = {
        side: {u.dcs_unit_type.id for u in _faction(data[key]).accessible_units}
        for side, key in (
            ("red", "recommended_enemy_faction"),
            ("blue", "recommended_player_faction"),
        )
    }
    for cp in theater.controlpoints:
        if cp.starting_coalition.is_neutral:
            continue
        side = "red" if cp.starting_coalition.is_red else "blue"
        for preset in cp.preset_locations.exact_air_defenses:
            types = [vehicle_map[u.type_id] for u in preset.units]
            assert classify(types) is not None, preset.original_name
            missing = {
                t.id
                for t in types
                if unit_class_of(t) is not UnitClass.LOGISTICS
                and t.id not in fieldable[side]
            }
            assert (
                not missing
            ), f"{preset.original_name} ({side}, {cp.name}): cannot field {missing}"
            for unit in preset.units:
                field = field_under(
                    theater.terrain.airports.values(),
                    unit.position.x,
                    unit.position.y,
                )
                assert field is None, (
                    f"{preset.original_name}: {unit.type_id} on {field}'s runway or "
                    "apron holds every AI taxi there"
                )
