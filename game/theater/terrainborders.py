"""Shipped per-terrain border geometry (§98) — the automagic half.

A campaign should not have to author the shape of its neighbours: the borders of
a real-world map are a property of the *terrain*, identical for every campaign on
it. ``resources/borders/<terrain>.yaml`` carries them, and a campaign that says
nothing gets them for free.

**This is what makes the feature work on existing campaigns** (DM call,
2026-08-25): 52 of the 54 campaigns on real-world maps author no borders at all,
and hand-editing every one of them was never the plan.

Precedence is simple and total: **a campaign that declares
``neutral_border_defense:`` owns its borders completely** and this file is not
consulted. Mixing the two would make it impossible to tell where a zone came
from.

Each terrain entry carries geometry and an origin, nothing else. What a
country's airspace means — whose it is, and whether it lets you through — is
derived at run time from the airbases inside its border, so one file is correct
on every campaign that map carries. Only the airframe it scrambles comes from
the dated table (``nationalpostures``), which is the one fact no campaign can
supply for a country that holds nothing.

**Every country on the map is here, the map's own nation included.** It was
excluded until 2026-08-26 on the theory that a border round the battlefield is
noise; that deleted Russia from Kola and Iran from the Persian Gulf and left
the war itself as the one region with no line on it.

**A country that ceased to exist carries its end and its successor**
(``until``, ``successor``): the GDR is drawn for a 1985 campaign and is
Germany's for a 2027 one. :func:`borders_on` is the one place that decides.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any, Optional

import yaml

#: Relative to the install root, like every other resource read.
BORDERS_DIR = Path("resources/borders")

_cache: dict[str, list[dict[str, Any]]] = {}


#: pydcs names some terrains differently from their file: Sinai is "SinaiMap",
#: so every Sinai campaign silently got no borders (2026-10-13).
_FILE_FOR_TERRAIN = {
    "sinaimap": "sinai",
    "germanycw": "germany",
    "germanycoldwar": "germany",
}


def _terrain_key(terrain_name: str) -> str:
    key = terrain_name.strip().lower().replace(" ", "")
    return _FILE_FOR_TERRAIN.get(key, key)


def _year_month(token: Any) -> tuple[int, int]:
    year, _, month = str(token).partition("-")
    return (int(year), int(month or 1))


def borders_on(entries: list[dict[str, Any]], on: date) -> list[dict[str, Any]]:
    """The zones as they stood on ``on``.

    A zone whose country had ceased to exist by then is its successor's; its
    geometry is kept, so the line between the two is no longer a frontier.
    """
    dated = []
    for entry in entries:
        entry = dict(entry)
        until, successor = entry.pop("until", None), entry.pop("successor", None)
        if until is not None and successor is not None:
            try:
                if (on.year, on.month) >= _year_month(until):
                    entry["country"] = str(successor)
            except ValueError:
                logging.warning("Terrain borders: bad until %r.", until)
        dated.append(entry)
    return dated


def load_terrain_borders(
    terrain_name: str, directory: Optional[Path] = None, on: Optional[date] = None
) -> list[dict[str, Any]]:
    """Raw zone dicts shipped for this terrain, ready for ``from_yaml``.

    Empty for a terrain with no file (fictional maps, Nevada, the Marianas —
    anywhere there is no foreign border to draw). Never raises: a bad file costs
    the feature, never the campaign. With ``on``, dated zones are resolved
    (:func:`borders_on`); without it they come as drawn.
    """
    zones = _load(terrain_name, directory)
    return borders_on(zones, on) if on is not None else zones


def _load(terrain_name: str, directory: Optional[Path]) -> list[dict[str, Any]]:
    key = _terrain_key(terrain_name)
    if directory is None and key in _cache:
        return _cache[key]
    path = (directory or BORDERS_DIR) / f"{key}.yaml"
    zones: list[dict[str, Any]] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("zones"), list):
            zones = [z for z in raw["zones"] if isinstance(z, dict)]
        elif raw is not None:
            logging.warning("Terrain borders: %s has no zones list.", path)
    except FileNotFoundError:
        pass  # A terrain with no foreign borders is normal, not an error.
    except Exception:
        logging.warning("Terrain borders: %s unreadable.", path, exc_info=True)
    if directory is None:
        _cache[key] = zones
    return zones
