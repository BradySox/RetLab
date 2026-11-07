"""List the stock DCS liveries that no squadron preset names.

Reads the liveries shipped in a DCS install (Bazar, CoreMods and Mods; never
Saved Games, whose liveries are personal) and the presets in resources/squadrons.
Read-only. Use it after a DCS update to find new skins worth a preset; the
matching rules are in docs/dev/design/retlab-stock-livery-squadrons-notes.md.

    python tools/stock_livery_survey.py "E:/DCS World"            # counts
    python tools/stock_livery_survey.py "E:/DCS World" --list F-15ESE
"""

from __future__ import annotations

import argparse
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
NAME = re.compile(r'^\s*name\s*=\s*"([^"]*)"', re.M)
COUNTRIES = re.compile(r"countries\s*=\s*\{([^}]*)\}", re.S)


def livery_roots(dcs: Path) -> list[Path]:
    roots = [dcs / "Bazar" / "Liveries"]
    for base in (dcs / "CoreMods" / "aircraft", dcs / "Mods" / "aircraft"):
        if base.is_dir():
            roots += [
                m / "Liveries" for m in base.iterdir() if (m / "Liveries").is_dir()
            ]
    return roots


def description(path: Path) -> str:
    try:
        if path.is_dir():
            lua = path / "description.lua"
            return lua.read_text("utf-8", "ignore") if lua.exists() else ""
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                if member.lower().endswith("description.lua"):
                    return archive.read(member).decode("utf-8", "ignore")
    except (OSError, zipfile.BadZipFile):
        pass
    return ""


def stock_liveries(dcs: Path) -> dict[str, dict[str, tuple[str, str]]]:
    """unit type (lower) -> livery id (lower) -> (id, "name | countries")."""
    found: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    for root in livery_roots(dcs):
        for unit in (u for u in root.iterdir() if u.is_dir()):
            for livery in unit.iterdir():
                if livery.is_file() and livery.suffix.lower() != ".zip":
                    continue
                livery_id = livery.stem if livery.is_file() else livery.name
                text = description(livery)
                name = NAME.search(text)
                countries = COUNTRIES.search(text)
                label = " | ".join(
                    [
                        name.group(1) if name else "",
                        (
                            ",".join(re.findall(r'"([^"]+)"', countries.group(1)))
                            if countries
                            else ""
                        ),
                    ]
                )
                found[unit.name.lower()][livery_id.lower()] = (livery_id, label)
    return found


def preset_liveries() -> tuple[dict[str, set[str]], dict[str, int]]:
    variant_to_id: dict[str, str] = {}
    for path in (REPO / "resources/units/aircraft").glob("*.yaml"):
        data = yaml.safe_load(path.read_text("utf-8")) or {}
        for variant in data.get("variants") or {}:
            variant_to_id[variant] = path.stem.lower()
    used: dict[str, set[str]] = defaultdict(set)
    count: dict[str, int] = defaultdict(int)
    for path in (REPO / "resources/squadrons").glob("*/*.yaml"):
        data = yaml.safe_load(path.read_text("utf-8")) or {}
        unit = variant_to_id.get(data.get("aircraft", ""))
        if unit is None:
            continue
        count[unit] += 1
        for livery in [data.get("livery")] + list(data.get("livery_set") or []):
            if livery:
                used[unit].add(str(livery).lower())
    return used, count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dcs", type=Path, help="DCS World install folder")
    parser.add_argument("--list", metavar="UNIT", help="list one unit type's liveries")
    args = parser.parse_args()

    stock = stock_liveries(args.dcs)
    used, count = preset_liveries()
    rows = []
    aircraft = {
        p.stem.lower() for p in (REPO / "resources/units/aircraft").glob("*.yaml")
    }
    for unit, liveries in stock.items():
        if unit not in aircraft:
            continue
        missing = {k: v for k, v in liveries.items() if k not in used.get(unit, set())}
        rows.append((unit, len(liveries), missing, count.get(unit, 0)))

    if args.list:
        for unit, _, missing, _ in rows:
            if unit == args.list.lower():
                for livery_id, label in sorted(missing.values()):
                    print(f"{livery_id}\t{label}")
        return
    print(f"{'unit type':28} {'stock':>5} {'no preset':>9} {'presets':>7}")
    for unit, total, missing, presets in sorted(rows, key=lambda r: -len(r[2])):
        if missing:
            print(f"{unit:28} {total:5} {len(missing):9} {presets:7}")


if __name__ == "__main__":
    main()
