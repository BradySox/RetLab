"""The launcher list the Lua generator hands to the bmstrike plugin.

The plugin reads ``dcsRetribution.artilleryGroups.ballisticMissiles``. Missile
launchers are UnitClass.MISSILE, not ARTILLERY, so they get their own list; an
empty one leaves the plugin with an empty radio menu. Ported from
CleeeCATCH/dcs-retribution.
"""

from types import SimpleNamespace
from typing import Any

from game.data.units import UnitClass
from game.missiongenerator.luagenerator import ballistic_missile_batteries


def _unit_type(unit_class: UnitClass, threat_range: int) -> Any:
    return SimpleNamespace(
        unit_class=unit_class,
        display_name="Launcher",
        dcs_unit_type=SimpleNamespace(threat_range=threat_range),
    )


def _ground_object(name: str, unit_type: Any) -> Any:
    return SimpleNamespace(
        groups=[
            SimpleNamespace(
                group_name=f"0001 | {name}",
                name=name,
                units=[SimpleNamespace(unit_type=unit_type)],
            )
        ]
    )


def test_a_missile_launcher_is_listed_with_its_range() -> None:
    site = _ground_object("SCUD SITE", _unit_type(UnitClass.MISSILE, 285000))
    assert ballistic_missile_batteries([site], []) == [
        ("0001 | SCUD SITE", "SCUD SITE", 285000)
    ]


def test_a_launcher_with_no_firing_range_is_left_out() -> None:
    # The V-1 ramp has threat_range 0 and cannot be tasked in DCS.
    site = _ground_object("V-1 SITE", _unit_type(UnitClass.MISSILE, 0))
    assert ballistic_missile_batteries([site], []) == []


def test_artillery_is_not_a_missile_battery() -> None:
    guns = _ground_object("GUNS", _unit_type(UnitClass.ARTILLERY, 20000))
    assert ballistic_missile_batteries([guns], []) == []


def test_a_frontline_missile_group_is_listed() -> None:
    group = SimpleNamespace(
        group_name="0042 | ATACMS", unit_type=_unit_type(UnitClass.MISSILE, 300000)
    )
    assert ballistic_missile_batteries([], [group]) == [
        ("0042 | ATACMS", "Launcher", 300000)
    ]


def test_two_batteries_with_one_name_get_distinct_callsigns() -> None:
    unit_type = _unit_type(UnitClass.MISSILE, 285000)
    sites = [_ground_object("SCUD SITE", unit_type) for _ in range(2)]
    callsigns = [entry[1] for entry in ballistic_missile_batteries(sites, [])]
    assert callsigns == ["SCUD SITE", "SCUD SITE 2"]
