"""Saved loadouts: the player's own fits, kept for every campaign (§128).

The §73 version saved into DCS's ``MissionEditor/UnitPayloads`` under the name the
planner resolves, so a saved fit replaced the shipped preset for both coalitions in
every campaign. This store avoids each of its failures:

* Its own JSON file (``persistency.saved_loadouts_path``), never a pydcs payload
  directory. A saved fit is offered as ``Saved: <name>``, a name no preset carries,
  so it cannot shadow one.
* A fit flies only on a flight the player picks it for, or as one blue squadron's
  fit for one task in one save (``Squadron.saved_loadouts``). Red never uses one.
* On load, each missile steps up to the newest variant of its family the pylon
  takes (``weapon_variants``); the campaign date then steps it down as usual.
* A store the pylon cannot carry now (a weapons mod switched off) is dropped, and
  F-4E rails a rack blocks are emptied (``stationconflicts``).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from game.data.stationconflicts import conflicting_rails
from game.data.weapon_variants import newer_variant
from game.data.weapons import Pylon, Weapon

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.flighttype import FlightType
    from game.ato.loadouts import Loadout
    from game.dcs.aircrafttype import AircraftType
    from game.squadrons import Squadron

PREFIX = "Saved: "
MAX_NAME_LENGTH = 60

# {aircraft_id: {name: {"pylons": {"<num>": {"clsid": str, "settings": {...}}},
#                       "ammo_type": int | None}}}. None means not loaded yet.
_cache: Optional[dict[str, dict[str, Any]]] = None


def _load() -> dict[str, dict[str, Any]]:
    global _cache
    if _cache is not None:
        return _cache
    data: dict[str, dict[str, Any]] = {}
    try:
        from game.persistency import saved_loadouts_path

        path = saved_loadouts_path()
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = {
                    k: v
                    for k, v in loaded.get("aircraft", {}).items()
                    if isinstance(v, dict)
                }
    except Exception:
        # A missing Saved Games tree (headless tests) or a corrupt file: no fits.
        logging.warning("Could not load saved loadouts", exc_info=True)
    _cache = data
    return _cache


def _write(data: dict[str, dict[str, Any]]) -> bool:
    try:
        from game.persistency import saved_loadouts_path

        saved_loadouts_path().write_text(
            json.dumps({"version": 1, "aircraft": data}, indent=2, sort_keys=True),
            encoding="utf-8",
            newline="\n",
        )
        return True
    except OSError:
        logging.warning("Could not write saved loadouts", exc_info=True)
        return False


def reset_cache() -> None:
    """Forget the in-memory copy; the next read comes off disk."""
    global _cache
    _cache = None


def clean_name(name: str) -> str:
    """The name as stored: trimmed, without a typed ``Saved:`` prefix."""
    name = name.strip()
    if name.startswith(PREFIX):
        name = name[len(PREFIX) :].strip()
    return name[:MAX_NAME_LENGTH]


def display_name(name: str) -> str:
    return f"{PREFIX}{name}"


def is_saved_name(loadout_name: str) -> bool:
    return loadout_name.startswith(PREFIX)


def names_for(aircraft: AircraftType) -> list[str]:
    return sorted(_load().get(aircraft.dcs_unit_type.id, {}))


def exists(aircraft: AircraftType, name: str) -> bool:
    return name in _load().get(aircraft.dcs_unit_type.id, {})


def save(aircraft: AircraftType, name: str, loadout: Loadout) -> bool:
    """Store ``loadout``'s stations under ``name``, replacing a fit of that name."""
    name = clean_name(name)
    if not name:
        return False
    data = _load()
    data.setdefault(aircraft.dcs_unit_type.id, {})[name] = {
        "pylons": {
            str(number): {
                "clsid": weapon.clsid,
                "settings": dict(loadout.pylon_settings.get(number, {})),
            }
            for number, weapon in sorted(loadout.pylons.items())
            if weapon is not None
        },
        "ammo_type": loadout.ammo_type,
    }
    return _write(data)


def delete(aircraft: AircraftType, name: str) -> bool:
    data = _load()
    fits = data.get(aircraft.dcs_unit_type.id, {})
    if name not in fits:
        return False
    del fits[name]
    if not fits:
        del data[aircraft.dcs_unit_type.id]
    return _write(data)


@dataclass
class LoadedFit:
    loadout: Loadout
    #: One line per station the fit could not keep as saved, for the player.
    notes: list[str] = field(default_factory=list)


def load(aircraft: AircraftType, name: str) -> Optional[LoadedFit]:
    """The saved fit as a loadout for today's pylons, or None if there is none."""
    from game.ato.loadouts import Loadout

    entry = _load().get(aircraft.dcs_unit_type.id, {}).get(name)
    if not isinstance(entry, dict):
        return None
    notes: list[str] = []
    pylons: dict[int, Optional[Weapon]] = {}
    settings: dict[int, dict[str, Any]] = {}
    for key, station in sorted(
        entry.get("pylons", {}).items(), key=lambda kv: int(kv[0])
    ):
        number = int(key)
        clsid = station.get("clsid", "")
        weapon = Weapon.with_clsid(clsid)
        try:
            pylon: Optional[Pylon] = Pylon.for_aircraft(aircraft, number)
        except (KeyError, ValueError):
            pylon = None
        if weapon is None or pylon is None or not pylon.can_equip(weapon):
            label = weapon.name if weapon is not None else clsid
            notes.append(f"Station {number}: {label} cannot be loaded; left empty.")
            continue
        if (newer := newer_variant(pylon, weapon)) is not None:
            weapon = newer
        else:
            settings[number] = dict(station.get("settings", {}))
        pylons[number] = weapon
    for rail in conflicting_rails(aircraft.dcs_unit_type.id, pylons):
        notes.append(f"Station {rail}: emptied; the rack beside it blocks the rail.")
        del pylons[rail]
    loadout = Loadout(
        display_name(name),
        pylons,
        date=None,
        pylon_settings=settings,
        ammo_type=entry.get("ammo_type"),
    )
    return LoadedFit(loadout, notes)


def all_for(aircraft: AircraftType) -> list[Loadout]:
    """Every saved fit for the airframe, for the loadout list."""
    fits = []
    for name in names_for(aircraft):
        if (fit := load(aircraft, name)) is not None:
            fits.append(fit.loadout)
    return fits


def squadron_fit_name(squadron: Squadron, task: FlightType) -> Optional[str]:
    if not squadron.player.is_blue:
        return None
    return getattr(squadron, "saved_loadouts", {}).get(task)


def squadron_default(flight: Flight) -> Optional[Loadout]:
    """The squadron's saved fit for the flight's task, if it has one that exists."""
    name = squadron_fit_name(flight.squadron, flight.flight_type)
    if name is None:
        return None
    fit = load(flight.squadron.aircraft, name)
    if fit is None:
        return None
    return fit.loadout
