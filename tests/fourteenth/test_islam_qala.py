"""Afghanistan - Islam Qala laydown guards.

The US in the east at Bagram and Kabul against an Iranian expeditionary force
holding the west, October 1998. Design note:
``docs/dev/design/414th-islam-qala-campaign-notes.md``.

Four properties are load-bearing and nothing else in the tree catches them:

* **The carrier is support-only.** It is 599 nm from Herat and 422 from Kandahar.
  Base a combat squadron there and the auto-planner has a second airfield to
  compare against Kabul; the point of the boat is that a 347 nm war has fuel, not
  that it has somewhere else to launch from. Same reasoning as Akrotiri in
  Anatolian Reach, arrived at from the opposite direction.
* **Kandahar and Camp Bastion are deliberately absent.** Kandahar is 250 nm from
  Herat against Kabul's 347 and has 316 stands. As a blue base it would win every
  auto-planner comparison and bench the eastern airhead; as a red base it would
  put Iran 340 nm past its own border with no line of communication home. It
  appears only as an intermediate waypoint on the southern supply route, which
  never changes what a route binds to.
* **Squadrons fit their ramps.** Chaghcharan has 3 stands and Bamyan 5. Both are
  positional, not basing, and a squadron authored past the stand count cannot
  generate. Re-check after any DCS parking rework (checklist B100).
* **No blue base carries an AAA marker.** ``usa_1990``'s air defence is the
  FPS-117, the Avenger and the M48 Chaparral -- it has no gun AAA at all, so an
  AAA marker on a blue field raises "USA 1990 has no access to SAM AAA" at
  generation and produces nothing. That is asserted against the build tool's
  table rather than the miz, because the table is what a future edit touches.

Validated at ``load_theater`` depth, the fork's campaign-test convention.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
import yaml

from game import persistency
from game.campaignloader.campaign import Campaign
from game.theater import ConflictTheater, Player

YAML = Path("resources/campaigns/islam_qala.yaml")
BUILD_TOOL = Path("tools/build_islam_qala_miz.py")

BLUE_CPS = {"Bagram", "Kabul", "Bamyan", "Ghazni Heliport", "CVN-74 John C. Stennis"}
RED_CPS = {
    "Herat",
    "Shindand",
    "Shindand Heliport",
    "Qala i Naw",
    "Chaghcharan",
    "Farah",
    "Tarinkot",
    "FOB Yakawlang",
}

#: Fields that must never become control points here. See the module docstring.
EXCLUDED_FIELDS = {
    "Kandahar",
    "Kandahar Heliport",
    "Camp Bastion",
    "Camp Bastion Heliport",
}

CARRIER = "CVN-74 John C. Stennis"

#: What the boat may fly. Anything else is a combat type for the guard below.
CARRIER_SUPPORT_ONLY = {"A-6E Tanker", "E-2C Hawkeye"}

#: The two blue-red adjacencies that make the campaign a ground war rather than a
#: pair of unconnected pockets.
REQUIRED_FRONTS = (("Bamyan", "FOB Yakawlang"), ("Ghazni Heliport", "Tarinkot"))

AIRFIELD_IDS = {
    "Bagram": 16,
    "Kabul": 17,
    "Bamyan": 18,
    "Ghazni Heliport": 21,
    "Herat": 1,
    "Shindand": 3,
    "Shindand Heliport": 14,
    "Qala i Naw": 6,
    "Chaghcharan": 5,
    "Farah": 2,
    "Tarinkot": 9,
}


def _data() -> dict[str, Any]:
    with YAML.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
        return data


def _theater(tmp_path: Path) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def _build_tool() -> Any:
    spec = importlib.util.spec_from_file_location("islam_qala_build", BUILD_TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_campaign_loads_with_expected_control_points(tmp_path: Path) -> None:
    _, theater = _theater(tmp_path)
    names = {cp.name for cp in theater.controlpoints}
    assert names == BLUE_CPS | RED_CPS


def test_ownership(tmp_path: Path) -> None:
    """Read ``starting_coalition``, never ``captured``.

    ``captured`` resolves through ``self.coalition``, which is only wired inside
    ``Game.__init__``; at ``load_theater`` depth it raises "ControlPoint not
    fully initialized". It is also a ``Player``, and both members are truthy, so
    ``if cp.captured`` reads BLUE for everything.
    """
    _, theater = _theater(tmp_path)
    by_name = {cp.name: cp for cp in theater.controlpoints}
    for name in BLUE_CPS:
        assert by_name[name].starting_coalition is Player.BLUE, f"{name} must be BLUE"
    for name in RED_CPS:
        assert by_name[name].starting_coalition is Player.RED, f"{name} must be RED"


def test_the_southern_hinges_are_not_control_points(tmp_path: Path) -> None:
    """Kandahar as a base breaks the campaign either way. See the docstring."""
    _, theater = _theater(tmp_path)
    names = {cp.name for cp in theater.controlpoints}
    assert not (
        names & EXCLUDED_FIELDS
    ), "these fields must stay out of the laydown: " + ", ".join(
        sorted(names & EXCLUDED_FIELDS)
    )


def test_carrier_flies_no_combat_aircraft() -> None:
    """The one constraint the reach design rests on."""
    squadrons = _data()["squadrons"][CARRIER]
    offenders = [
        aircraft
        for entry in squadrons
        for aircraft in entry["aircraft"]
        if aircraft not in CARRIER_SUPPORT_ONLY
    ]
    assert not offenders, (
        "The Stennis must stay tankers and AEW&C only; found combat aircraft: "
        + ", ".join(sorted(set(offenders)))
    )


def test_both_fronts_exist(tmp_path: Path) -> None:
    """Without these two adjacencies there is no ground war to fly over."""
    _, theater = _theater(tmp_path)
    by_name = {cp.name: cp for cp in theater.controlpoints}
    for blue_name, red_name in REQUIRED_FRONTS:
        neighbours = {cp.name for cp in by_name[blue_name].connected_points}
        assert red_name in neighbours, (
            f"{blue_name} must connect to {red_name}; it connects to "
            f"{sorted(neighbours) or 'nothing'}"
        )


@pytest.mark.parametrize("base", sorted(AIRFIELD_IDS))
def test_squadrons_fit_the_ramp(tmp_path: Path, base: str) -> None:
    """Chaghcharan has 3 stands and Bamyan 5. Read the count, do not assume it."""
    persistency.setup(str(tmp_path), False, 0)
    from dcs.terrain.afghanistan import Afghanistan

    stands = len(Afghanistan().airports[base].parking_slots)
    authored = sum(
        entry.get("size", 0)
        for entry in _data()["squadrons"].get(AIRFIELD_IDS[base], [])
    )
    assert (
        authored <= stands
    ), f"{base}: {authored} aircraft authored against {stands} stands"


def test_no_blue_base_carries_an_aaa_marker() -> None:
    """usa_1990 has no gun AAA; an AAA marker on a blue field generates nothing."""
    module = _build_tool()
    offenders = [
        base
        for base, kinds in module.AIR_DEFENCE.items()
        if module.AIRFIELDS[base] == module.BLUE and "aaa" in kinds
    ]
    assert not offenders, (
        "blue bases must use 'shorad', not 'aaa' -- USA 1990 has no gun AAA: "
        + ", ".join(sorted(offenders))
    )


def test_every_air_defence_base_is_a_control_point() -> None:
    """A typo here would place a site at a field that is not in the campaign."""
    module = _build_tool()
    unknown = set(module.AIR_DEFENCE) - set(module.AIRFIELDS)
    assert not unknown, "AIR_DEFENCE names a field that is not a control point: " + str(
        sorted(unknown)
    )


def test_period_settings_are_preseeded() -> None:
    """1998 kit. Without the date gate the Vipers carry JDAM and JSOW (both 1999)."""
    settings = _data()["settings"]
    assert settings["restrict_weapons_by_date"] is True
    assert settings["restrict_props_by_date"] is True
    # A host's saved settings layer sits UNDER campaign preseeds, so a Default.zip
    # with these off would strip the tanker bridge a 347 nm campaign needs.
    for key in (
        "autoplan_tankers_for_strike",
        "autoplan_tankers_for_oca",
        "autoplan_tankers_for_dead",
    ):
        assert settings[key] is True, f"{key} must be preseeded true"
