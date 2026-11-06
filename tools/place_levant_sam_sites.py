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

Swap mode (`--swap`, the default for every Syria campaign but Anatolian Reach, DM call
2026-11-06) keeps a campaign's balance: each SAM or radar marker is replaced by the nearest
unused template site of the same band within `--swap-nm` (10 NM) whose owner's faction
fields everything in it but `SUPPORT_UNITS`; markers with none stay.
A site is skipped if the campaign starts before the system reached that country
(`IN_SERVICE`).

Usage: python tools/place_levant_sam_sites.py anatolian_reach --radius-nm 40 --drop SA10
       python tools/place_levant_sam_sites.py syria_full_map --swap
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
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


#: Template kind -> the marker band it can stand for.
KIND_BANDS = {
    "SA5": "LORAD",
    "SA10": "LORAD",
    "Patriot": "LORAD",
    "SA2": "MERAD",
    "SA3": "MERAD",
    "SA6": "MERAD",
    "SA11": "MERAD",
    "Hawk": "MERAD",
    "SA8": "SHORAD",
    "Roland": "SHORAD",
    "Rapier": "SHORAD",
    "1L13": "EWR",
    "55G6": "EWR",
    "AN117": "EWR",
}

#: Drawn radars a faction may lack although it fields the system (the value, a unit
#: it must field; None for any): swap mode accepts a site missing only these, and the
#: campaign's faction gains them.
SUPPORT_UNITS: dict[str, str | None] = {
    "Hawk cwar": "Hawk ln",
    "FPS-117 Dome": "FPS-117",
    "FPS-117 ECS": "FPS-117",
    "Roland Radar": "Roland ADS",
    "p-19 s-125 sr": None,
}

#: (template country, kind) -> first year it stood there. Syria's S-300s are 2018.
IN_SERVICE = {("Syria", "SA10"): 2018}


def marker_band(type_id: str) -> str | None:
    from game.campaignloader.mizcampaignloader import MizCampaignLoader as L

    if type_id in L.LONG_RANGE_SAM_UNIT_TYPES:
        return "LORAD"
    if type_id in L.MEDIUM_RANGE_SAM_UNIT_TYPES:
        return "MERAD"
    if type_id in L.SHORT_RANGE_SAM_UNIT_TYPES:
        return "SHORAD"
    if type_id == L.EWR_UNIT_TYPE:
        return "EWR"
    return None


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


def add_site(mission: Mission, country: Any, site: dict[str, Any]) -> None:
    units = lead_first(site["units"])
    name = f"FIXED {site['name']}"
    type_id, x, y, heading = units[0]
    group = mission.vehicle_group(
        country,
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


def missing_units(site: dict[str, Any], fieldable: set[str]) -> set[str]:
    """Drawn shooters and radars, trucks aside, the owner cannot field."""
    from game.data.units import UnitClass
    from game.theater.exactsite import unit_class_of

    return {
        u[0]
        for u in site["units"]
        if u[0] not in fieldable
        and unit_class_of(vehicle_map[u[0]]) is not UnitClass.LOGISTICS
    }


def fieldable_with_support(site: dict[str, Any], fieldable: set[str]) -> bool:
    for unit in missing_units(site, fieldable):
        if unit not in SUPPORT_UNITS:
            return False
        system = SUPPORT_UNITS[unit]
        if system is not None and system not in fieldable:
            return False
    return True


def swap_markers(
    mission: Mission,
    swap_nm: float,
    start_year: int,
    fieldable: dict[str, set[str]] | None = None,
    exclude: frozenset[str] = frozenset(),
) -> list[tuple[str, str, float]]:
    """Replace each SAM/EWR marker with the nearest same-band template site.

    With `fieldable` (unit ids per side, "red"/"blue"), a site is only taken for a
    marker whose nearest airfield's owner fields everything in it but SUPPORT_UNITS.
    """
    groups = json.loads(TEMPLATE.read_text(encoding="utf-8"))["groups"]
    sites = []
    for group in groups:
        kind = kind_of(group["name"])
        band = KIND_BANDS.get(kind)
        if band is None or IN_SERVICE.get((group["country"], kind), 0) > start_year:
            continue
        if group["name"] in exclude:
            continue
        site = clear_of_airfields(mission, group)
        if site["units"]:
            sites.append((band, site))
    markers = []
    for country_name in (RED_COUNTRY, BLUE_COUNTRY):
        country = mission.country(country_name)
        if country is None:
            continue
        for g in country.vehicle_group:
            band = marker_band(g.units[0].type)
            if band is not None and not is_fixed(g.name):
                markers.append((country, g, band))
    fields = [
        (a.position, "red" if a.is_red() else "blue")
        for a in mission.terrain.airports.values()
        if a.is_red() or a.is_blue()
    ]
    pairs = []
    for mi, (_, g, band) in enumerate(markers):
        for si, (site_band, site) in enumerate(sites):
            if site_band != band:
                continue
            if fieldable is not None and fields:
                _, x, y, _ = site["units"][0]
                here = Point(x, y, mission.terrain)
                side = min(fields, key=lambda f: here.distance_to_point(f[0]))[1]
                if not fieldable_with_support(site, fieldable[side]):
                    continue
            _, x, y, _ = site["units"][0]
            nm = g.position.distance_to_point(Point(x, y, mission.terrain)) / NM
            if nm <= swap_nm:
                pairs.append((nm, mi, si))
    used_markers: set[int] = set()
    used_sites: set[int] = set()
    swaps = []
    for nm, mi, si in sorted(pairs):
        if mi in used_markers or si in used_sites:
            continue
        used_markers.add(mi)
        used_sites.add(si)
        country, g, _ = markers[mi]
        country.vehicle_group.remove(g)
        add_site(mission, country, sites[si][1])
        swaps.append((g.name, sites[si][1]["name"], nm))
    return swaps


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
        add_site(mission, red, site)
    return removed


def owner_cannot_field(
    name: str,
    campaign: dict[str, Any],
    mission: Mission,
    fieldable: dict[str, set[str]],
) -> set[str]:
    """Template names of FIXED sites the loader binds to a side that cannot field them.

    The tool guesses the owner from the nearest airfield; the loader binds to the
    nearest control point (FOBs and influence zones included), so check with it.
    """
    import shutil
    import tempfile

    from game.campaignloader.campaign import Campaign

    folder = Path(tempfile.mkdtemp())
    shutil.copy(REPO / "resources/campaigns" / f"{name}.yaml", folder)
    mission.save(str(folder / campaign.get("miz", f"{name}.miz")))
    loaded = Campaign.from_file(folder / f"{name}.yaml")
    theater = loaded.load_theater(loaded.advanced_iads)
    groups = {
        f"FIXED {g['name']}": g
        for g in json.loads(TEMPLATE.read_text(encoding="utf-8"))["groups"]
    }
    wrong = set()
    for cp in theater.controlpoints:
        if cp.starting_coalition.is_neutral:
            continue
        side = "red" if cp.starting_coalition.is_red else "blue"
        for preset in cp.preset_locations.exact_air_defenses:
            site = groups.get(preset.original_name)
            if site is not None and missing_units(site, fieldable[side]):
                wrong.add(site["name"])
    return wrong


def campaign_fieldable(campaign: dict[str, Any]) -> dict[str, set[str]]:
    """Unit ids each side's recommended faction can field."""
    import tempfile

    from game import persistency
    from game.factions import FACTIONS
    from game.factions.faction import Faction

    persistency.setup(tempfile.mkdtemp(), False, 0)
    out = {}
    for side, key in (
        ("red", "recommended_enemy_faction"),
        ("blue", "recommended_player_faction"),
    ):
        spec = campaign[key]
        faction = Faction.from_dict(spec) if isinstance(spec, dict) else FACTIONS[spec]
        out[side] = {u.dcs_unit_type.id for u in faction.accessible_units}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("campaign", help="campaign yaml name without .yaml")
    parser.add_argument("--radius-nm", type=float, default=40.0)
    parser.add_argument("--clear-nm", type=float, default=1.8)
    parser.add_argument(
        "--countries",
        default="Syria,Turkey,Combined Joint Task Forces Red",
        help="template countries whose sites red owns, comma-separated",
    )
    parser.add_argument("--drop", default="", help="template kinds to skip, e.g. SA10")
    parser.add_argument("--swap", action="store_true", help="swap markers only")
    parser.add_argument("--swap-nm", type=float, default=10.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    folder = REPO / "resources/campaigns"
    campaign = yaml.safe_load(
        (folder / f"{args.campaign}.yaml").read_text(encoding="utf-8")
    )
    path = folder / campaign.get("miz", f"{args.campaign}.miz")
    mission = Mission()
    mission.load_file(str(path))
    if args.swap:
        start = int(str(campaign.get("recommended_start_date") or "2100")[:4])
        fieldable = campaign_fieldable(campaign)
        exclude: set[str] = set()
        for _ in range(5):
            mission = Mission()
            mission.load_file(str(path))
            swaps = swap_markers(
                mission, args.swap_nm, start, fieldable, frozenset(exclude)
            )
            wrong = owner_cannot_field(args.campaign, campaign, mission, fieldable)
            if not wrong:
                break
            exclude |= wrong
        else:
            raise SystemExit(f"{path.name}: sites still bind to the wrong side")
        for marker, site_name, nm in swaps:
            print(f"  {marker} -> {site_name} ({nm:.1f} NM)")
        if swaps and not args.dry_run:
            mission.save(str(path))
        print(f"{path.name}: {len(swaps)} markers swapped for drawn sites")
        return
    sites = pick_sites(
        mission,
        args.radius_nm,
        set(args.countries.split(",")),
        {d for d in args.drop.split(",") if d},
    )
    removed = place(mission, sites, args.clear_nm)
    mission.save(str(path))
    kinds: dict[str, int] = {}
    for picked in sites:
        kind = kind_of(picked["name"])
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"{path.name}: {len(sites)} FIXED sites {kinds}; {removed} markers removed")


if __name__ == "__main__":
    main()
