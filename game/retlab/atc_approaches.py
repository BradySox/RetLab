"""Voice ATC step 3 (§119): instrument approaches Approach can clear a flight for.

Kola, the Falklands and Nevada carry ILS, TACAN and LOC plates in their kneeboard folders;
their fixes live in ``resources/voice_atc/approaches/<map>.yaml``. Any other runway end with
an ILS gets a generated straight-in: start 12 NM out at the field plus 3,000 ft, final fix
5 NM out at the field plus 1,600 ft. Approach offers one in low weather or when the pilot asks
(user call, 2026-11-03). RNP, VOR and NDB plates are left out: DCS jets fly ILS, TACAN, LOC.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from game.yamlload import safe_load_yaml

from game.retlab.atc_routes import dcs_runway

if TYPE_CHECKING:
    from dcs.terrain import Airport

    from game.runways import RunwayData
    from game.weather.weather import Weather

APPROACHES_DIR = Path("resources/voice_atc/approaches")

#: The order Approach prefers when a runway has more than one approach.
KINDS = ("ILS", "TACAN", "LOC")

GENERATED_START_NM = 12
GENERATED_START_FT = 3000
GENERATED_FINAL_NM = 5
#: 5 NM on a 3 degree glideslope is about 1,600 ft above the threshold.
GENERATED_FINAL_FT = 1600

#: Below either, Approach gives an instrument approach unasked: the VFR minimums.
INSTRUMENT_CEILING_FT = 3000
INSTRUMENT_VISIBILITY_SM = 5


@dataclass(frozen=True)
class ApproachFix:
    #: The fix's name; None for an unnamed DME fix or a generated point.
    name: Optional[str]
    #: The plate's DME at the fix, or the distance out for a generated point.
    dme: Optional[float]
    feet: int

    @property
    def label(self) -> str:
        """``TAKUP``, ``8.0 DME`` or ``12 miles``."""
        if self.name:
            return self.name
        if self.dme is None:
            return ""
        return f"{self.dme:g} DME"


@dataclass(frozen=True)
class InstrumentApproach:
    kind: str
    #: The DCS runway end it lands on.
    runway: str
    course: int
    #: ``108.70`` for an ILS or LOC, ``59X`` for a TACAN.
    nav: str
    ident: str
    start: ApproachFix
    final: ApproachFix
    generated: bool = False

    def clearance(self) -> str:
        """``cleared ILS runway 25, via TAKUP, maintain 3,500 until established, at 8 DME``:
        what Approach says, as the plugin builds it."""
        head = f"cleared {self.kind} runway {self.runway}, "
        if self.generated:
            return (
                head + f"proceed to a {self.start.dme:g} mile final, maintain "
                f"{self.start.feet:,} until established, at {self.final.dme:g} miles"
            )
        return (
            head + f"via {self.start.label}, maintain {self.start.feet:,} until "
            f"established, at {self.final.label}"
        )

    def card_line(self) -> str:
        """``ILS 25 (108.70 BD): via TAKUP 3,500, Tower at 8 DME 3,000``."""
        if self.generated:
            return (
                f"{self.kind} {self.runway} ({self.nav} {self.ident}".rstrip()
                + f"): {self.start.dme:g} NM final {self.start.feet:,}, "
                f"Tower at {self.final.dme:g} NM {self.final.feet:,}"
            )
        return (
            f"{self.kind} {self.runway} ({self.nav} {self.ident}): via "
            f"{self.start.label} {self.start.feet:,}, Tower at {self.final.label} "
            f"{self.final.feet:,}"
        )


@cache
def _plate_file(terrain_name: str) -> dict[str, Any]:
    path = APPROACHES_DIR / f"{terrain_name.lower()}.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return safe_load_yaml(f) or {}


def _fix(entry: dict[str, Any]) -> ApproachFix:
    name = entry.get("name")
    dme = entry.get("dme")
    return ApproachFix(
        str(name) if name else None,
        float(dme) if dme is not None else None,
        int(entry["ft"]),
    )


def _ends(airport: Airport) -> list[str]:
    ends: list[str] = []
    for runway in getattr(airport, "runways", []):
        ends.extend([runway.main.name, runway.opposite.name])
    return ends


def charted_approaches(
    terrain_name: str, airport: Airport, runways: list[RunwayData]
) -> list[InstrumentApproach]:
    """The plates' ILS, TACAN and LOC approaches at a field; an ILS takes DCS's own
    frequency where the runway end has one, so the flight tunes what the map transmits.
    """
    approaches = []
    dcs_ils = {r.runway_name: r for r in runways if r.ils is not None}
    for entry in _plate_file(terrain_name).get(airport.name, []):
        kind = str(entry["type"])
        if kind not in KINDS:
            continue
        plate_runway, ends = str(entry["runway"]), _ends(airport)
        # Nellis's 21L is DCS's 21L; only a renumbered end goes by heading.
        end = plate_runway if plate_runway in ends else dcs_runway(plate_runway, ends)
        if end is None:
            logging.warning(
                "Voice ATC: %s plate runway %s matches no DCS runway",
                airport.name,
                entry["runway"],
            )
            continue
        nav = str(entry.get("frequency") or entry.get("channel") or "")
        ident = str(entry.get("ident", ""))
        if kind == "ILS" and (data := dcs_ils.get(end)) is not None:
            assert data.ils is not None
            dcs_nav = f"{data.ils.mhz:.2f}"
            if dcs_nav != nav:
                logging.info(
                    "Voice ATC: %s ILS %s is %s in DCS, %s on the plate",
                    airport.name,
                    end,
                    dcs_nav,
                    nav,
                )
            nav, ident = dcs_nav, (data.ils_callsign or ident).upper()
        approaches.append(
            InstrumentApproach(
                kind,
                end,
                int(entry["course"]),
                nav,
                ident,
                _fix(entry["start"]),
                _fix(entry["final"]),
            )
        )
    return approaches


def generated_approaches(
    airport: Airport, runways: list[RunwayData], elevation_ft: float
) -> list[InstrumentApproach]:
    """A straight-in ILS for each runway end with an ILS beacon."""
    approaches = []
    for data in runways:
        if data.ils is None:
            continue
        approaches.append(
            InstrumentApproach(
                "ILS",
                data.runway_name,
                round(data.runway_heading.degrees) % 360,
                f"{data.ils.mhz:.2f}",
                (data.ils_callsign or "").upper(),
                ApproachFix(
                    None,
                    GENERATED_START_NM,
                    _hundreds(elevation_ft + GENERATED_START_FT),
                ),
                ApproachFix(
                    None,
                    GENERATED_FINAL_NM,
                    _hundreds(elevation_ft + GENERATED_FINAL_FT),
                ),
                generated=True,
            )
        )
    return approaches


def field_approaches(
    terrain_name: str,
    airport: Airport,
    runways: list[RunwayData],
    elevation_ft: float,
) -> list[InstrumentApproach]:
    """The plates' approaches, plus a generated ILS for each ILS end no plate covers."""
    charted = charted_approaches(terrain_name, airport, runways)
    covered = {a.runway for a in charted}
    generated = [
        a
        for a in generated_approaches(airport, runways, elevation_ft)
        if a.runway not in covered
    ]
    return sorted(charted + generated, key=lambda a: (a.runway, KINDS.index(a.kind)))


def _hundreds(feet: float) -> int:
    return int(math.ceil(feet / 100) * 100)


def instrument_weather(weather: Weather, elevation_ft: float) -> bool:
    """A ceiling under 3,000 ft above the field or visibility under 5 miles."""
    from game.missiongenerator.kneeboard_recon.atis import (
        format_cloud_layer,
        format_visibility,
    )

    cloud = format_cloud_layer(weather.clouds).split()
    if len(cloud) >= 2 and cloud[0] in ("BKN", "OVC") and cloud[1].isdigit():
        if int(cloud[1]) - elevation_ft < INSTRUMENT_CEILING_FT:
            return True
    visibility = format_visibility(weather.fog, weather.clouds).split()[0]
    try:
        lowest = float(visibility.split("-")[0].rstrip("+"))
    except ValueError:
        return False
    return lowest < INSTRUMENT_VISIBILITY_SM
