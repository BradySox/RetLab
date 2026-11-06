"""Copy real SAM and radar sites from the Levant SAM template into a Syria campaign miz.

The template (`tools/data/levant_sam_template.json`, extracted from DCS user file
3321812, freeware, unlimited distribution; it builds on Pikes' Syrian Air Defence
Network 2012) draws every site on the Syria map unit by unit, in the emplacements
Ugra Media's terrain models. Each picked site is written to the CJTF Red block as a
`FIXED <template name>` group, so New Game keeps it as drawn (features doc §122).

- A site is picked when its first unit is within `--radius-nm` of a red airfield and
  its template country is in `--countries`; `--drop` names template kinds to skip.
- The group's first unit is a launcher a stock Retribution marker reader knows, so a
  build without §122 still puts a stock site there instead of dropping it.
- A drawn unit on a runway strip or a parking stand is left out: any ground unit there
  holds every AI taxi at the field (CLAUDE.md hard constraints, §1). A site with
  nothing left is not placed.
- A SAM or radar marker within `--clear-nm` of a picked site is removed, and
  FIXED groups an earlier run wrote are replaced, so the tool can be re-run.
Design note: docs/dev/design/retlab-real-sam-sites-notes.md.

Usage: python tools/place_levant_sam_sites.py anatolian_reach --radius-nm 40 --drop SA10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.vehicles import vehicle_map

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from game.theater.airfieldclearance import field_under

TEMPLATE = REPO / "tools/data/levant_sam_template.json"
RED_COUNTRY = "Combined Joint Task Forces Red"
BLUE_COUNTRY = "Combined Joint Task Forces Blue"
NM = 1852.0

#: Upstream's marker launcher types, longest range first: the first one found leads
#: the group so a build without FIXED support reads it as a marker of that band.
STOCK_MARKER_LEADS = [
    "Patriot ln",
    "S-300PS 5P85C ln",
    "S-300PS 5P85D ln",
    "Hawk ln",
    "S_75M_Volhov",
    "5p73 s-125 ln",
    "NASAMS_LN_B",
    "NASAMS_LN_C",
    "M1097 Avenger",
    "rapier_fsa_launcher",
    "2S6 Tunguska",
    "Strela-1 9P31",
    "flak18",
    "Vulcan",
    "ZSU-23-4 Shilka",
    "1L13 EWR",
]

#: First-unit types of the SAM and radar markers a picked site replaces. Guns are left
#: alone: the template draws no AAA, so a gun marker is never the same site.
MARKER_TYPES = set(STOCK_MARKER_LEADS) - {"flak18", "Vulcan", "ZSU-23-4 Shilka"} | {
    "Kub 2P25 ln",
    "SA-11 Buk LN 9A310M1",
    "Osa 9A33 ln",
    "Tor 9A331",
    "Strela-10M3",
    "S-200_Launcher",
    "55G6 EWR",
    "FPS-117 Dome",
}


def is_fixed(name: str) -> bool:
    upper = name.upper()
    return upper.startswith("FIXED") and not upper[5:6].isalnum()


def kind_of(name: str) -> str:
    """`RSAM-SA2-Damascus-4` -> `SA2`; `REW-1L13-YE56` -> `1L13`."""
    parts = name.split("-")
    return parts[1] if len(parts) > 1 else name


def lead_first(units: list[list[Any]]) -> list[list[Any]]:
    for lead in STOCK_MARKER_LEADS:
        for index, unit in enumerate(units):
            if unit[0] == lead:
                return [unit] + units[:index] + units[index + 1 :]
    return units


def pick_sites(
    mission: Mission, radius_nm: float, countries: set[str], drop: set[str]
) -> list[dict[str, Any]]:
    red_fields = [a.position for a in mission.terrain.airports.values() if a.is_red()]
    groups = json.loads(TEMPLATE.read_text(encoding="utf-8"))["groups"]
    picked = []
    for group in groups:
        if group["country"] not in countries or kind_of(group["name"]) in drop:
            continue
        _, x, y, _ = group["units"][0]
        here = Point(x, y, mission.terrain)
        if min(here.distance_to_point(f) for f in red_fields) > radius_nm * NM:
            continue
        site = clear_of_airfields(mission, group)
        if site["units"]:
            picked.append(site)
    return picked


def clear_of_airfields(mission: Mission, site: dict[str, Any]) -> dict[str, Any]:
    units = []
    for unit in site["units"]:
        field = field_under(mission.terrain.airports.values(), unit[1], unit[2])
        if field is None:
            units.append(unit)
        else:
            print(f"{site['name']}: {unit[0]} left out, on {field}'s runway or apron")
    return {**site, "units": units}


def place(mission: Mission, sites: list[dict[str, Any]], clear_nm: float) -> int:
    red = mission.country(RED_COUNTRY)
    assert red is not None
    for country_name in (RED_COUNTRY, BLUE_COUNTRY):
        country = mission.country(country_name)
        if country is not None:
            country.vehicle_group = [
                g for g in country.vehicle_group if not is_fixed(g.name)
            ]
    anchors = [
        Point(s["units"][0][1], s["units"][0][2], mission.terrain) for s in sites
    ]
    removed = 0
    for country_name in (RED_COUNTRY, BLUE_COUNTRY):
        country = mission.country(country_name)
        if country is None:
            continue
        keep = []
        for g in country.vehicle_group:
            if g.units[0].type in MARKER_TYPES and any(
                g.position.distance_to_point(a) <= clear_nm * NM for a in anchors
            ):
                removed += 1
                continue
            keep.append(g)
        country.vehicle_group = keep
    for site in sites:
        units = lead_first(site["units"])
        name = f"FIXED {site['name']}"
        type_id, x, y, heading = units[0]
        group = mission.vehicle_group(
            red,
            name,
            vehicle_map[type_id],
            Point(x, y, mission.terrain),
            heading=heading,
            group_size=1,
        )
        for index, (type_id, x, y, heading) in enumerate(units[1:], start=2):
            unit = mission.vehicle(f"{name} #{index}", vehicle_map[type_id])
            unit.position = Point(x, y, mission.terrain)
            unit.heading = heading
            group.add_unit(unit)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("campaign", help="campaign file name without .miz")
    parser.add_argument("--radius-nm", type=float, default=40.0)
    parser.add_argument("--clear-nm", type=float, default=1.8)
    parser.add_argument(
        "--countries",
        default="Syria,Turkey,Combined Joint Task Forces Red",
        help="template countries whose sites red owns, comma-separated",
    )
    parser.add_argument("--drop", default="", help="template kinds to skip, e.g. SA10")
    args = parser.parse_args()

    path = REPO / "resources/campaigns" / f"{args.campaign}.miz"
    mission = Mission()
    mission.load_file(str(path))
    sites = pick_sites(
        mission,
        args.radius_nm,
        set(args.countries.split(",")),
        {d for d in args.drop.split(",") if d},
    )
    removed = place(mission, sites, args.clear_nm)
    mission.save(str(path))
    kinds: dict[str, int] = {}
    for site in sites:
        kind = kind_of(site["name"])
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"{path.name}: {len(sites)} FIXED sites {kinds}; {removed} markers removed")


if __name__ == "__main__":
    main()
