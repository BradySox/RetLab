"""Per-(airframe, task) "save as my default" for the DTC tab (§74).

A new flight starts from its task's ticks (``DtcOptions.for_task``); a default saved
here for the same airframe and task replaces them. One JSON file under the Saved
Games tree, keyed ``"<dcs id>|<task>"``, so it survives across campaigns like the
§43 flight defaults. Player side only, and a missing or broken file is a no-op.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from game.ato.flighttype import FlightType
from game.persistency import dtc_defaults_path

if TYPE_CHECKING:
    from game.ato.dtcoptions import DtcOptions
    from game.ato.flight import Flight

_cache: Optional[dict[str, Any]] = None


def _key(aircraft_id: str, task: FlightType) -> str:
    return f"{aircraft_id}|{task.value}"


def _load() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    data: dict[str, Any] = {}
    try:
        path = dtc_defaults_path()
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
    except Exception:
        logging.debug("Could not load DTC defaults store", exc_info=True)
    _cache = data
    return _cache


def _write(data: dict[str, Any]) -> None:
    global _cache
    try:
        dtc_defaults_path().write_text(
            json.dumps(data, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
        )
    except OSError:
        logging.warning("Could not write DTC defaults store", exc_info=True)
    _cache = data


def invalidate_cache() -> None:
    global _cache
    _cache = None


def has_default_for(aircraft_id: str, task: FlightType) -> bool:
    return bool(_load().get(_key(aircraft_id, task)))


def save_default_for(aircraft_id: str, task: FlightType, options: DtcOptions) -> None:
    data = dict(_load())
    data[_key(aircraft_id, task)] = options.saved_fields()
    _write(data)


def clear_default_for(aircraft_id: str, task: FlightType) -> None:
    data = dict(_load())
    if data.pop(_key(aircraft_id, task), None) is not None:
        _write(data)


def apply_dtc_defaults(flight: Flight) -> None:
    """Overlay the saved default on a fresh player-side flight's task ticks."""
    try:
        if not flight.coalition.player.is_blue:
            return
        saved = _load().get(_key(flight.unit_type.dcs_unit_type.id, flight.flight_type))
        if isinstance(saved, dict):
            flight.dtc_options.apply_saved(saved)
    except Exception:
        logging.debug("Could not apply DTC defaults", exc_info=True)
