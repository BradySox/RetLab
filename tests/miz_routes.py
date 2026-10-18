"""Supply routes and shipping lanes as a campaign .miz draws them.

Routes are M-113 path groups and lanes HandyWind groups (``MizCampaignLoader``),
read here from the miz so a test can check a campaign's road net.
"""

from __future__ import annotations

from pathlib import Path

from dcs.mission import Mission

from game.campaignloader.mizcampaignloader import MizCampaignLoader

CAMPAIGNS = Path("resources/campaigns")

Path_ = list[tuple[int, int]]


def miz_paths(miz_name: str) -> tuple[list[Path_], list[Path_]]:
    """(roads, lanes) drawn in ``resources/campaigns/<miz_name>``, as rounded XY."""
    mission = Mission()
    mission.load_file(str(CAMPAIGNS / miz_name))
    roads: list[Path_] = []
    lanes: list[Path_] = []
    for country in (
        mission.country(MizCampaignLoader.BLUE_COUNTRY.name),
        mission.country(MizCampaignLoader.RED_COUNTRY.name),
    ):
        if country is None:
            continue
        for group in country.vehicle_group:
            if group.units[0].type == MizCampaignLoader.FRONT_LINE_UNIT_TYPE:
                roads.append(
                    [(round(p.position.x), round(p.position.y)) for p in group.points]
                )
        for ship in country.ship_group:
            if ship.units[0].type == MizCampaignLoader.SHIPPING_LANE_UNIT_TYPE:
                lanes.append(
                    [(round(p.position.x), round(p.position.y)) for p in ship.points]
                )
    return roads, lanes
