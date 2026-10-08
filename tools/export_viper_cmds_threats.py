"""Export the F-16C's CMDS threat table from a DCS install (§74).

The Viper cartridge's ``CMDS_Avionics_Threat_Table`` is what the jet's DTC
editor compiles from ``threat_base.lua`` (each threat's type codes) and
``CMDS_defs.lua`` (each threat's category, auto program and thresholds). A
cartridge that carries an empty table leaves the jet with no auto program for
any threat, so the builder writes the module's own table, taken from here.

Run after a DCS update that touches the F-16C DTC folder:

    python tools/export_viper_cmds_threats.py "E:\\DCS World"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import lupa

OUTPUT = Path(__file__).resolve().parent.parent / "resources/dtc/f16c_cmds_threats.json"
DTC_DIR = Path("CoreMods/aircraft/F-16C/DTC")


_UNLISTED = {
    "program": 1,
    "thresholds": [{"label": "SEARCH", "index": 1}],
    "default_threshold": {"label": "SEARCH", "index": 1},
}


def _to_python(value: Any) -> Any:
    if lupa.lua_type(value) == "table":
        keys = list(value.keys())
        if keys and all(isinstance(k, int) for k in keys):
            return [_to_python(value[k]) for k in sorted(keys)]
        if not keys:
            return []
        return {str(k): _to_python(value[k]) for k in keys}
    return value


def export(install: Path) -> dict[str, Any]:
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    root = str(install).replace("\\", "/")
    # The cockpit scripts dofile() paths relative to the install root.
    lua.execute(f"""
        local root = "{root}/"
        local raw_dofile = dofile
        dofile = function(path) return raw_dofile(root .. path) end
        """)
    lua.execute(f'dofile("{(DTC_DIR / "threat_base.lua").as_posix()}")')
    lua.execute(f'dofile("{(DTC_DIR / "MPD/CMDS_defs.lua").as_posix()}")')
    g = lua.globals()
    base = _to_python(g.threats_base)
    programs = _to_python(g.CMDS.CMDSPrograms)
    categories = list(_to_python(g.threats_categories))

    table = []
    for threat in base:
        name = threat["group_name"]
        # The editor's own fallback (CMDS.lua makeCMDSTable): a threat with no
        # CMDS_defs entry gets NONE at SEARCH.
        category = next((c for c in categories if name in programs.get(c, {})), None)
        settings = programs[category][name] if category else _UNLISTED
        table.append(
            {
                "category": category,
                "group_name": name,
                "hint": threat["hint"],
                "program": settings["program"],
                "thresholds": settings["thresholds"],
                "default_threshold": settings["default_threshold"],
                "threats": [
                    {
                        "displayName": t.get("displayName", ""),
                        "unit_type": t.get("unit_type", ""),
                        "wstype": t.get("wstype", []),
                    }
                    for t in threat["threats"]
                ],
            }
        )
    return {
        "delayBetweenPrograms": programs["delayBetweenPrograms"],
        "threats": table,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("install", type=Path, help="DCS install folder")
    args = parser.parse_args()
    data = export(args.install)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data['threats'])} threats -> {OUTPUT}")


if __name__ == "__main__":
    main()
