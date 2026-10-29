"""Clean (pylon removed) is offered only on the stations where DCS offers it."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.planes import F_16C_50, F_4E_45MC

from game.data.cleanpylons import CLEAN_PYLONS
from game.data.weapons import Pylon, Weapon
from tools.clean_pylons import render, scan, scan_lines


def test_table_matches_the_pydcs_export() -> None:
    """A pydcs bump that moves a <CLEAN> station needs `tools/clean_pylons.py --write`."""
    assert CLEAN_PYLONS == scan()


def test_generated_module_is_current() -> None:
    from tools.clean_pylons import OUTPUT

    assert OUTPUT.read_text(encoding="utf-8").replace("\r\n", "\n") == render(scan())


def test_scan_reads_the_comment_after_its_own_pylon() -> None:
    lines = [
        "class Jet(PlaneType):",
        '    id = "Jet"',
        "    class Pylon1:",
        "        Tank = (1, Weapons.Tank)",
        "#ERRR <CLEAN>",
        "",
        "    class Pylon2:",
        "        Bomb = (2, Weapons.Bomb)",
        "",
        "class Weapons:",
        "#ERRR <CLEAN>",
        "class Heli(HelicopterType):",
        '    id = "Heli"',
        "    class Pylon3:",
        "        Rocket = (3, Weapons.Rocket)",
        "    # ERRR <CLEAN>",
    ]
    assert scan_lines(lines) == {"Jet": {1}, "Heli": {3}}


def test_f4e_sparrow_wells_have_no_pylon_to_remove() -> None:
    # Pylon reads only dcs_unit_type; the aircraft registry needs a loaded game.
    f4e: Any = SimpleNamespace(dcs_unit_type=F_4E_45MC)
    removable = {p.number for p in Pylon.iter_pylons(f4e) if p.removable}
    assert removable == {1, 3, 9, 11, 13}
    for well in (5, 6, 8):
        assert not Pylon.for_aircraft(f4e, well).removable


def test_viper_wing_pylons_can_come_off() -> None:
    viper: Any = SimpleNamespace(dcs_unit_type=F_16C_50)
    assert Pylon.for_aircraft(viper, 3).removable
    assert not Pylon.for_aircraft(viper, 1).removable


def test_clean_still_equips_anywhere_a_loadout_puts_it() -> None:
    clean = Weapon.with_clsid("<CLEAN>")
    assert clean is not None
    assert Pylon(5, set()).can_equip(clean)
