"""The road inventory: campaigns that field blue supply convoys must keep the road.

The ambient convoy layer (§50) needs a blue->blue road corridor (a supply_routes
entry linking two BLUE control points) or the blue side silently no-ops. The
2026-07-05 flown test found both COIN campaigns shipping an all-red supply graph.
Every campaign that had a blue->blue road at the 2026-07-06 survey, or was given
one by the batch-1 authoring pass (tools/supply_route_geo.py BATCH1_BLUE_REAR),
must keep one, so a laydown edit cannot silently drop it. A campaign NOT listed
does not field a blue convoy (island maps and all-red graphs); when a blue rear
corridor is authored for one, ADD it here.

Lived in tests/retlab/test_convoy_ambush.py until the convoy ambush was removed
on 2026-10-11.
"""

from __future__ import annotations

from typing import Any

import pytest

#: Every shipping campaign whose theater binds at least one blue->blue supply road.
ROAD_BEARING_CAMPAIGNS = [
    "1968_Yankee_Station",
    "Caucasus_Multi_Full",
    "IntotheHornetsNest",
    "Invasion_of_Canary_Islands",
    "Northern Guardian",
    "Operation-Desert-Sabre",
    "Task Force Thunder",
    "TblisiGap",
    "WRL_AleppoInsurgency",
    "WRL_AssaultonDamascus",
    "WRL_Battle4Georgia",
    "WRL_Battle4SyriaNorth",
    "WRL_Battle4area51",
    "WRL_Kutaisi2Vaziani",
    "WRL_Operation_Noisy_Cricket_Redux",
    "black_sea",
    "clash_of_the_titans",
    "coin_enduring_resolve",
    "crossing_the_rubicon",
    "exercise_able_archer",
    "exercise_bright_star",
    "exercise_quasar",
    "exercise_vegas_nerve",
    "final_countdown_2",
    "golan_heights_lite",
    "graveyard_of_empires",
    "iraq_inherent_resolve",
    "marianas_guam_barrigada",
    "mozdok_to_maykop",
    "operation_allied_sword",
    "operation_desert_aladeen",
    "operation_dynamo",
    "operation_frostbite",
    "operation_gazelle",
    "operation_noisy_cricket",
    "operation_shattered_dagger",
    "operation_vectrons_claw",
    "operation_velvet_thunder",
    "red_flag_81_2",
    "red_sea_rising",
    "red_tide",
    "scenic_inland",
    "scenic_merge",
    "slava_ukraini",
    "syria_TheLongRoadToH3",
    "syria_full_map",
    "the_anvil_of_war",
    "tripoint_hostility",
]


def _blue_blue_road_count(theater: Any) -> int:
    roads = set()
    for cp in theater.controlpoints:
        if not cp.starting_coalition.is_blue:
            continue
        for other in cp.convoy_routes.keys():
            if other.starting_coalition.is_blue:
                roads.add(tuple(sorted((cp.name, other.name))))
    return len(roads)


def test_the_campaigns_the_roads_were_authored_for_stay_in_the_inventory() -> None:
    assert set(ROAD_BEARING_CAMPAIGNS) >= {
        "coin_enduring_resolve",
        "iraq_inherent_resolve",
        "1968_Yankee_Station",
        "red_tide",
    }


def test_batch1_corridor_campaigns_are_in_the_inventory() -> None:
    # Every campaign the batch-1 authoring pass gave a blue rear corridor must be
    # tracked by the inventory guard -- the tool and the test stay in lockstep.
    from tools.supply_route_geo import BATCH1_BLUE_REAR

    assert set(ROAD_BEARING_CAMPAIGNS) >= set(BATCH1_BLUE_REAR)


@pytest.mark.parametrize("stem", ROAD_BEARING_CAMPAIGNS)
def test_road_bearing_campaign_keeps_its_blue_road(stem: str, tmp_path: Any) -> None:
    from pathlib import Path

    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(tmp_path), False, 0)
    path = Path("resources/campaigns") / f"{stem}.yaml"
    assert path.exists(), (
        f"{stem} is in ROAD_BEARING_CAMPAIGNS but the campaign file is gone -- "
        "remove it from the inventory (or restore the campaign)."
    )
    campaign = Campaign.from_file(path)
    theater = campaign.load_theater(campaign.advanced_iads)
    assert _blue_blue_road_count(theater) >= 1, (
        f"{stem} is in the §50 road-bearing inventory but no longer binds a "
        "blue->blue supply road -- ambient blue convoys will silently never "
        "exist there. Restore the blue rear corridor (see "
        "tools/supply_route_geo.py) or remove the campaign from "
        "ROAD_BEARING_CAMPAIGNS."
    )
