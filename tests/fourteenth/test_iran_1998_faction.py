"""Iran 1998 faction guards.

The IRIAF and Iranian air-defence force at the end of the 1990s, written for
*Afghanistan - Islam Qala*. Three of its properties are load-bearing and none of
them is protected by anything else in the tree:

* **Every roster string must resolve.** ``_resolve_named_set`` skips an unknown
  unit name with a ``WARNING`` and keeps the rest of the faction, which is the
  right behaviour -- one typo can no longer brick a whole faction -- but it means
  a renamed unit silently thins the roster instead of failing. Nothing surfaces
  that to a player. The count comparison below is the only thing that catches it.
* **No tanker and no AEW aircraft.** Iran operated neither: its 1998 tanker was
  the Boeing 707-3J9C, which DCS does not have, and it had no AEW aircraft at
  all. ``iran_2015`` -- the file this was derived from -- rosters an IL-78M and
  an A-50, so the obvious "fix" for a faction that looks short is to add them
  back. That would delete the campaign's central asymmetry: blue has the KC-135
  bridge and can reach anywhere, Iran cannot leave its own airspace far, and its
  entire air picture is ground radar.
* **The SAM belt is period-gated by hand.** ``restrict_weapons_by_date`` gates
  weapons but never preset groups, so nothing except this test stops an SA-17
  (Buk-M2, 2008) or an SA-15 (Tor; Iran bought them in 2005-07) being added.
  Both were in ``iran_2015`` and both were removed on purpose.

Design note: ``docs/dev/design/414th-islam-qala-campaign-notes.md``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from game import persistency
from game.factions.faction import Faction

FACTION_FILE = Path("resources/factions/iran_1998.json")

#: Systems that postdate 1998 or that Iran never operated. Matched as
#: case-insensitive substrings against preset-group and AD-unit names.
ANACHRONISTIC = (
    "SA-11",  # Buk-M1 -- Iran fielded no Buk in 1998
    "SA-17",  # Buk-M2, service 2008
    "SA-15",  # Tor; Iran bought 29 Tor-M1 in 2005-07
    "Tor",
    "Buk",
    "S-300",
    "SA-10",
    "SA-20",
    "SA-21",
    "SA-22",
    "Pantsir",
)

#: Roster keys in the JSON paired with the attribute they resolve into.
ROSTERS = (
    ("aircrafts", "aircraft"),
    ("awacs", "awacs"),
    ("tankers", "tankers"),
    ("frontline_units", "frontline_units"),
    ("artillery_units", "artillery_units"),
    ("logistics_units", "logistics_units"),
    ("infantry_units", "infantry_units"),
    ("air_defense_units", "air_defense_units"),
    ("naval_units", "naval_units"),
    ("missiles", "missiles"),
    ("preset_groups", "preset_groups"),
)


@pytest.fixture(scope="module", autouse=True)
def _saved_games(tmp_path_factory: pytest.TempPathFactory) -> None:
    """``Faction.from_dict`` resolves preset groups, which reach persistency."""
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


@pytest.fixture(scope="module")
def raw() -> dict[str, Any]:
    with FACTION_FILE.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


@pytest.fixture(scope="module")
def faction(raw: dict[str, Any]) -> Faction:
    return Faction.from_dict(raw)


@pytest.mark.parametrize(("key", "attr"), ROSTERS)
def test_every_roster_name_resolves(
    raw: dict[str, Any], faction: Faction, key: str, attr: str
) -> None:
    """A renamed unit thins the roster with only a log line to say so."""
    want = len(set(raw.get(key, [])))
    got = len(getattr(faction, attr))
    assert got == want, (
        f"{key}: {want - got} name(s) in iran_1998.json did not resolve and were "
        f"silently dropped. Run the faction load with logging at WARNING to see "
        f"which; the message names the unit."
    )


def test_load_emits_no_warnings(raw: dict[str, Any]) -> None:
    """The direct form of the check above -- catches whatever counts miss."""
    records: list[str] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.levelno >= logging.WARNING:
                records.append(record.getMessage())

    handler = Capture()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        Faction.from_dict(raw)
    finally:
        root.removeHandler(handler)

    offenders = [m for m in records if "Iran 1998" in m]
    assert not offenders, "Iran 1998 load emitted warnings:\n" + "\n".join(offenders)


def test_no_tanker_and_no_awacs(faction: Faction) -> None:
    """The campaign's central asymmetry. See the module docstring."""
    assert not faction.tankers, (
        "Iran 1998 must roster no tanker -- it had none, and blue's exclusive "
        "reach is the point of the Islam Qala laydown."
    )
    assert not faction.awacs, (
        "Iran 1998 must roster no AEW aircraft -- it had none, which is what "
        "makes its early-warning radar chain worth attacking."
    )


def test_has_a_ground_early_warning_radar(faction: Faction) -> None:
    """With no AWACS, the EWRs are the whole of Iran's air picture.

    Drop these and the faction is not merely handicapped, it is blind: §1 makes
    detection the IADS network alone, and there is no airborne backup to fall
    through to.
    """
    ewrs = [u for u in faction.air_defense_units if u.display_name.startswith("EWR ")]
    assert ewrs, "Iran 1998 must roster at least one EWR"


def test_sam_presets_are_period_correct_for_1998(faction: Faction) -> None:
    named = [g.name for g in faction.preset_groups]
    named += [u.display_name for u in faction.air_defense_units]
    offenders = [
        f"{name} (matched {word})"
        for name in named
        for word in ANACHRONISTIC
        if word.lower() in name.lower()
    ]
    assert (
        not offenders
    ), "Post-1998 or never-Iranian air defence in iran_1998: " + ", ".join(
        sorted(set(offenders))
    )


def test_no_aircraft_postdates_1998(faction: Faction) -> None:
    """``year_introduced`` is a string and is ``"No data."`` for some types.

    Only types carrying a parseable year are checked; the rest are a hand call.
    The IL-76MD is the one such type in this roster and entered service in 1974.
    """
    offenders = []
    for aircraft in faction.aircraft:
        try:
            year = int(str(aircraft.year_introduced))
        except (TypeError, ValueError):
            continue
        if year > 1998:
            offenders.append(f"{aircraft.display_name} ({year})")
    assert not offenders, "Aircraft postdating 1998: " + ", ".join(sorted(offenders))


def test_doctrine_is_coldwar(faction: Faction) -> None:
    """Iran in 1998 flew ground-controlled intercepts with no datalink."""
    assert faction.doctrine.name == "coldwar"


def test_satnav_is_restricted(faction: Faction) -> None:
    """Iran fielded no satellite-guided weapon in 1998."""
    assert not faction.unrestricted_satnav
