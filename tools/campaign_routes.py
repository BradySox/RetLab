"""Draw a campaign's supply routes and shipping lanes in its .miz.

Routes are drawn the way upstream campaigns draw them: an M-113 group per road and a
HandyWind group per sea lane, whose first and last waypoints sit on the two control
points (``MizCampaignLoader.add_supply_routes`` / ``add_shipping_lanes``). The
yaml ``supply_routes:`` / ``shipping_lanes:`` lists are RetLab-only and are being
retired (DM call, 2026-10-18).

    python tools/campaign_routes.py <campaign stem> [...]

moves a campaign's yaml lists into its .miz: the groups are inserted into the raw
mission table (no pydcs re-serialization, so mod units are untouched), a .miz path
group that a yaml entry overrode is dropped, the yaml block is removed, and the
loaded theater's convoy routes and shipping lanes are checked to be identical.

Build scripts that regenerate a .miz call ``carry_route_groups`` so the drawn routes
of the current .miz survive a rebuild.
"""

from __future__ import annotations

import io
import logging
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import dcs  # noqa: E402
from dcs import lua  # noqa: E402
from dcs.point import PointAction  # noqa: E402
from dcs.ships import HandyWind  # noqa: E402
from dcs.vehicles import Armor  # noqa: E402

CAMPAIGNS = REPO / "resources" / "campaigns"
ROUTE_TYPE = Armor.M_113.id
LANE_TYPE = HandyWind.id
#: A rail line is a train drawn on the track (features doc §123).
RAIL_TYPE = "Train"

Waypoints = list[tuple[float, float]]


# --- pydcs side: used by the build scripts --------------------------------------


def route_groups(mission: dcs.Mission) -> list[tuple[str, str, Waypoints]]:
    """(kind, name, waypoints) for every route and lane group in ``mission``."""
    found = []
    for side in ("blue", "red"):
        for country in mission.coalition[side].countries.values():
            for group in country.vehicle_group:
                if group.units[0].type in (ROUTE_TYPE, RAIL_TYPE):
                    found.append(
                        (
                            "route" if group.units[0].type == ROUTE_TYPE else "rail",
                            group.name,
                            [(p.position.x, p.position.y) for p in group.points],
                        )
                    )
            for ship in country.ship_group:
                if ship.units[0].type == LANE_TYPE:
                    found.append(
                        (
                            "lane",
                            ship.name,
                            [(p.position.x, p.position.y) for p in ship.points],
                        )
                    )
    return found


def draw(
    mission: dcs.Mission, country: Any, kind: str, name: str, points: Waypoints
) -> None:
    first = dcs.mapping.Point(points[0][0], points[0][1], mission.terrain)
    if kind == "route":
        group = mission.vehicle_group(country, name, Armor.M_113, first, group_size=1)
        group.points[0].action = PointAction.OnRoad
        for x, y in points[1:]:
            group.add_waypoint(
                dcs.mapping.Point(x, y, mission.terrain), PointAction.OnRoad
            )
    elif kind == "rail":
        from game.missiongenerator.traingenerator import draw_rail_line

        draw_rail_line(mission, country, name, points)
    else:
        ship = mission.ship_group(country, name, HandyWind, first)
        for x, y in points[1:]:
            ship.add_waypoint(dcs.mapping.Point(x, y, mission.terrain))


def carry_route_groups(mission: dcs.Mission, current_miz: Path) -> None:
    """Re-draw the routes and lanes of ``current_miz`` into a freshly built mission.

    The .miz is where routes are authored, so a rebuild keeps whatever is drawn there.
    """
    current = dcs.Mission()
    current.load_file(str(current_miz))
    # MizCampaignLoader reads path groups from this one country only.
    name = dcs.countries.CombinedJointTaskForcesBlue.name
    country = mission.coalition["blue"].country(name) or mission.coalition[
        "blue"
    ].add_country(dcs.countries.CombinedJointTaskForcesBlue())
    existing = {name for _, name, _ in route_groups(mission)}
    for kind, name, points in route_groups(current):
        if name not in existing:
            draw(mission, country, kind, name, points)


# --- raw side: converting a hand-authored campaign ------------------------------


def _max_ids(node: Any, found: dict[str, int]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("groupId", "unitId") and isinstance(value, (int, float)):
                found[key] = max(found[key], int(value))
            else:
                _max_ids(value, found)


def _group_tables(
    terrain: Any, entries: list[tuple[str, str, Waypoints]]
) -> list[tuple[str, dict[Any, Any]]]:
    scratch = dcs.Mission(terrain)
    country = scratch.coalition["blue"].add_country(
        dcs.countries.CombinedJointTaskForcesBlue()
    )
    out = []
    for kind, name, points in entries:
        draw(scratch, country, kind, name, points)
    for group in country.vehicle_group:
        out.append(("vehicle", group.dict()))
    for group in country.ship_group:
        out.append(("ship", group.dict()))
    return out


def _renumber(table: dict[Any, Any], ids: dict[str, int]) -> None:
    ids["groupId"] += 1
    gid = ids["groupId"]
    table["groupId"] = gid
    for unit in table["units"].values():
        ids["unitId"] += 1
        unit["unitId"] = ids["unitId"]
    for point in table["route"]["points"].values():
        for task in point.get("task", {}).get("params", {}).get("tasks", {}).values():
            action = task.get("params", {}).get("action", {}).get("params")
            if isinstance(action, dict) and "groupId" in action:
                action["groupId"] = gid


def _strip_yaml_block(text: str, key: str) -> str:
    """Remove a top-level ``key:`` block and the comment lines right above it."""
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.rstrip() == f"{key}:")
    end = start + 1
    while end < len(lines) and (
        lines[end].startswith((" ", "\t", "#")) or not lines[end].strip()
    ):
        if (
            lines[end].startswith("#")
            and end + 1 < len(lines)
            and re.match(r"^\w", lines[end + 1])
        ):
            break
        end += 1
    # A trailing run of top-level comments belongs to the next key; keep it.
    while end > start + 1 and lines[end - 1].startswith("#"):
        end -= 1
    head = start
    while head > 0 and lines[head - 1].startswith("#"):
        head -= 1
    del lines[head:end]
    out = re.sub(r"(\r?\n){3,}", lambda m: m.group(1) * 2, "".join(lines))
    return out.rstrip() + ("\r\n" if "\r\n" in out else "\n")


def _without_paths(table: dict[Any, Any]) -> dict[Any, Any]:
    """The mission table with every route and lane group taken out."""
    import copy

    out = copy.deepcopy(table)
    for side in ("blue", "red"):
        for country in out["coalition"][side].get("country", {}).values():
            for category, unit_types in (
                ("vehicle", (ROUTE_TYPE, RAIL_TYPE)),
                ("ship", (LANE_TYPE,)),
            ):
                if category not in country:
                    continue
                groups = country[category].get("group") or {}
                kept = [
                    g
                    for g in groups.values()
                    if g["units"][1]["type"] not in unit_types
                ]
                if kept:
                    country[category]["group"] = {i + 1: g for i, g in enumerate(kept)}
                else:
                    # A category holding only path groups (or one this tool
                    # created) compares as absent.
                    del country[category]
    return out


def _theater_routes(
    stem: str, saved_games: str
) -> tuple[dict[Any, Any], dict[Any, Any]]:
    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(saved_games, False, 0)
    campaign = Campaign.from_file(CAMPAIGNS / f"{stem}.yaml")
    theater = campaign.load_theater(campaign.advanced_iads)
    roads, lanes = {}, {}
    for cp in theater.controlpoints:
        for other, path in cp.convoy_routes.items():
            roads[(cp.name, other.name)] = [(round(p.x), round(p.y)) for p in path]
        for other, path in cp.shipping_lanes.items():
            lanes[(cp.name, other.name)] = [(round(p.x), round(p.y)) for p in path]
    return roads, lanes


def _binding(theater: Any, points: Waypoints) -> frozenset[str]:
    a = theater.closest_control_point(dcs.mapping.Point(*points[0], theater.terrain))
    b = theater.closest_control_point(dcs.mapping.Point(*points[-1], theater.terrain))
    return frozenset((a.name, b.name))


MizEntries = list[tuple[zipfile.ZipInfo, bytes]]


def _read_miz(miz_path: Path) -> tuple[MizEntries, int, dict[Any, Any]]:
    entries: MizEntries = []
    with zipfile.ZipFile(miz_path) as z:
        # pydcs once wrote "theatre" twice; keep the first of each name.
        for info in z.infolist():
            if info.filename not in {e.filename for e, _ in entries}:
                entries.append((info, z.read(info.filename)))
    index = next(i for i, (info, _) in enumerate(entries) if info.filename == "mission")
    table = lua.loads(entries[index][1].decode("utf-8"))["mission"]
    return entries, index, table


def _write_miz(
    miz_path: Path, entries: MizEntries, index: int, table: dict[Any, Any]
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
        for i, (info, payload) in enumerate(entries):
            if i == index:
                payload = lua.dumps(table, "mission", 1).encode("utf-8")
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(zi, payload)
    miz_path.write_bytes(buffer.getvalue())


def _insert(
    table: dict[Any, Any], terrain: Any, wanted: list[tuple[str, str, Waypoints]]
) -> None:
    ids = {"groupId": 0, "unitId": 0}
    _max_ids(table, ids)
    # MizCampaignLoader reads path groups from this one country only.
    cjtf = dcs.countries.CombinedJointTaskForcesBlue
    blue = table["coalition"]["blue"].setdefault("country", {})
    target = next((c for c in blue.values() if c["name"] == cjtf.name), None)
    if target is None:
        target = {"id": cjtf.id, "name": cjtf.name}
        blue[len(blue) + 1] = target
    for category, group in _group_tables(terrain, wanted):
        _renumber(group, ids)
        groups = target.setdefault(category, {}).setdefault("group", {})
        groups[len(groups) + 1] = group


def draw_into_miz(
    miz_path: Path, terrain: Any, wanted: list[tuple[str, str, Waypoints]]
) -> None:
    """Add route ("route"), rail ("rail") and lane ("lane") groups to a campaign .miz.

    Only the mission table changes, and only by the added groups.
    """
    entries, index, table = _read_miz(miz_path)
    untouched = _without_paths(table)
    _insert(table, terrain, wanted)
    if _without_paths(table) != untouched:
        raise SystemExit(f"{miz_path.name}: something other than route groups changed")
    _write_miz(miz_path, entries, index, table)


def convert(stem: str, saved_games: str) -> None:
    """Move a campaign's yaml ``supply_routes:``/``shipping_lanes:`` into its .miz."""
    import yaml

    from game import persistency
    from game.campaignloader.campaign import Campaign

    yaml_path = CAMPAIGNS / f"{stem}.yaml"
    raw_yaml = yaml_path.read_bytes().decode("utf-8")
    data = yaml.safe_load(raw_yaml)
    miz_path = CAMPAIGNS / data["miz"]
    before = _theater_routes(stem, saved_games)

    persistency.setup(saved_games, False, 0)
    campaign = Campaign.from_file(yaml_path)
    theater = campaign.load_theater(campaign.advanced_iads)

    def closest(point: tuple[float, float]) -> str:
        return theater.closest_control_point(
            dcs.mapping.Point(*point, theater.terrain)
        ).name

    wanted: list[tuple[str, str, Waypoints]] = []
    overridden: set[frozenset[str]] = set()
    for kind, key in (("route", "supply_routes"), ("lane", "shipping_lanes")):
        for entry in data.get(key) or []:
            points = [(float(x), float(y)) for x, y in entry["waypoints"]]
            suffix = "Route" if kind == "route" else "Lane"
            wanted.append(
                (kind, f"{closest(points[0])}-{closest(points[-1])} {suffix}", points)
            )
            overridden.add(_binding(theater, points) | {kind})

    entries, index, table = _read_miz(miz_path)
    untouched = _without_paths(table)

    # Drop the .miz path groups a yaml entry replaced (the yaml ran last and won).
    dropped = 0
    for side in ("blue", "red"):
        for country in table["coalition"][side].get("country", {}).values():
            for category, kind, unit_type in (
                ("vehicle", "route", ROUTE_TYPE),
                ("ship", "lane", LANE_TYPE),
            ):
                groups = country.get(category, {}).get("group", {})
                for gkey in list(groups):
                    group = groups[gkey]
                    if group["units"][1]["type"] != unit_type:
                        continue
                    points = [
                        (p["x"], p["y"]) for p in group["route"]["points"].values()
                    ]
                    if _binding(theater, points) | {kind} in overridden:
                        del groups[gkey]
                        dropped += 1
                if groups:
                    country[category]["group"] = {
                        i + 1: g for i, g in enumerate(groups.values())
                    }

    _insert(table, theater.terrain, wanted)
    if _without_paths(table) != untouched:
        raise SystemExit(f"{stem}: something other than route groups changed")

    original_miz = miz_path.read_bytes()
    _write_miz(miz_path, entries, index, table)
    new_yaml = raw_yaml
    for key in ("supply_routes", "shipping_lanes"):
        if data.get(key):
            new_yaml = _strip_yaml_block(new_yaml, key)
    yaml_path.write_bytes(new_yaml.encode("utf-8"))

    after = _theater_routes(stem, saved_games)
    if after != before:
        miz_path.write_bytes(original_miz)
        yaml_path.write_bytes(raw_yaml.encode("utf-8"))
        changed = [k for k in before[0] if before[0].get(k) != after[0].get(k)]
        raise SystemExit(f"{stem}: routes differ, reverted: {changed[:6]}")
    print(f"{stem}: {len(wanted)} drawn, {dropped} replaced groups dropped, identical")


def main(argv: Optional[Iterable[str]] = None) -> None:
    import tempfile

    logging.disable(logging.CRITICAL)
    args = list(argv if argv is not None else sys.argv[1:])
    with tempfile.TemporaryDirectory() as saved_games:
        for stem in args:
            convert(stem, saved_games)


if __name__ == "__main__":
    main()
