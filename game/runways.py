"""Runway information and selection."""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from typing import Iterator, Optional, TYPE_CHECKING

from dcs.mapping import Point
from dcs.terrain.terrain import Airport, RunwayApproach

from game.atcdata import AtcData
from game.dcs.beacons import BeaconType, Beacons
from game.radio.radios import RadioFrequency
from game.radio.tacan import TacanChannel
from game.utils import Heading
from game.weather.conditions import Conditions

if TYPE_CHECKING:
    from game.dcs.beacons import Beacon
    from game.theater import ConflictTheater


@dataclass(frozen=True)
class RunwayData:
    airfield_name: str
    runway_heading: Heading
    runway_name: str
    atc: Optional[RadioFrequency] = None
    #: The tower's VHF AM frequency, for radios that cannot tune ``atc`` (UHF).
    atc_vhf: Optional[RadioFrequency] = None
    tacan: Optional[TacanChannel] = None
    tacan_callsign: Optional[str] = None
    ils: Optional[RadioFrequency] = None
    icls: Optional[int] = None
    #: The ILS ident the F10 airfield panel shows ("ISPA").
    ils_callsign: Optional[str] = None

    @classmethod
    def for_pydcs_runway_runway(
        cls,
        theater: ConflictTheater,
        airport: Airport,
        runway: RunwayApproach,
    ) -> RunwayData:
        """Creates RunwayData for the given runway of an airfield.

        Args:
            theater: The theater the airport is in.
            airport: The airfield the runway belongs to.
            runway: The pydcs runway.
        """
        atc: Optional[RadioFrequency] = None
        atc_vhf: Optional[RadioFrequency] = None
        tacan: Optional[TacanChannel] = None
        tacan_callsign: Optional[str] = None
        atc_radio = AtcData.from_pydcs(airport)
        if atc_radio is not None:
            atc = atc_radio.uhf
            atc_vhf = atc_radio.vhf_am

        for beacon_data in airport.beacons:
            beacon = cls._get_beacon(beacon_data.id, theater)
            if not beacon:
                continue
            if beacon.is_tacan:
                tacan = beacon.tacan_channel
                tacan_callsign = beacon.callsign

        ils_beacon = _ils_beacon(theater, airport, runway)

        return cls(
            airfield_name=airport.name,
            runway_heading=Heading(runway.heading),
            runway_name=runway.name,
            atc=atc,
            atc_vhf=atc_vhf,
            tacan=tacan,
            tacan_callsign=tacan_callsign,
            ils=ils_beacon.frequency if ils_beacon is not None else None,
            ils_callsign=ils_beacon.callsign if ils_beacon is not None else None,
        )

    @staticmethod
    def _get_beacon(beacon_id: str, theater: ConflictTheater) -> Optional[Beacon]:
        try:
            beacon = Beacons.with_id(beacon_id, theater)
            return beacon
        except KeyError:
            # this means pydcs found a beacon in the "standlist"
            # but isn't present in beacons.lua file, which in turn causes problems...
            logging.error(f"Could not find data for '{beacon_id}', skipping beacon...")
            return None

    @classmethod
    def for_pydcs_airport(
        cls, theater: ConflictTheater, airport: Airport
    ) -> Iterator[RunwayData]:
        for runway in airport.runways:
            yield cls.for_pydcs_runway_runway(
                theater,
                airport,
                runway.main,
            )
            yield cls.for_pydcs_runway_runway(
                theater,
                airport,
                runway.opposite,
            )


#: Probe flights (2026-10-26, 13 Syria fields): from 6 m/s (12 kt) up every AI
#: jet took off into the wind; below it many fields kept one fixed end even with
#: a tailwind. See docs/dev/retlab-features.md §119.
LIGHT_WIND_MPS = 6.0

_RUNWAY_END_RE = re.compile(r"^(0[1-9]|[12][0-9]|3[0-6])([LRC]?)$")


def opposite_runway_name(name: str) -> Optional[str]:
    """ "10R" for "28L"; None for a name that is not a runway end ("045" BRC)."""
    match = _RUNWAY_END_RE.match(name)
    if match is None:
        return None
    number = (int(match.group(1)) + 18 - 1) % 36 + 1
    side = {"L": "R", "R": "L"}.get(match.group(2), match.group(2))
    return f"{number:02}{side}"


def runway_label(runway_name: str, surface_wind_mps: float) -> str:
    """The kneeboard RWY cell: both ends in light wind, where AI may use either."""
    if surface_wind_mps >= LIGHT_WIND_MPS:
        return runway_name
    opposite = opposite_runway_name(runway_name)
    if opposite is None:
        return runway_name
    return f"{runway_name} / {opposite}"


def ils_label(runway: RunwayData) -> str:
    """The kneeboard ILS cell: "108.10 ISPA" as the F10 panel reads it, or ICLS."""
    if runway.ils is not None:
        label = f"{runway.ils.mhz:.2f}"
        if runway.ils_callsign:
            label += f" {runway.ils_callsign}"
        return label
    if runway.icls is not None:
        return str(runway.icls)
    return ""


def _angle_off(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _ils_beacon(
    theater: ConflictTheater, airport: Airport, approach: RunwayApproach
) -> Optional[Beacon]:
    """The ILS serving this runway end, localizer first for its ident.

    Germany ties only the localizer to the runway end, so a glideslope-only
    lookup missed 35 of its 57 ILS ends.
    """
    found: list[Beacon] = []
    for beacon_data in approach.beacons:
        beacon = RunwayData._get_beacon(beacon_data.id, theater)
        if beacon is not None and beacon.beacon_type in _ILS_TYPES:
            found.append(beacon)
    if not found:
        return _untied_localizer(theater, airport, approach)
    return min(
        found, key=lambda b: b.beacon_type is not BeaconType.BEACON_TYPE_ILS_LOCALIZER
    )


def _untied_localizer(
    theater: ConflictTheater, airport: Airport, approach: RunwayApproach
) -> Optional[Beacon]:
    """A localizer beaming down this end that DCS tied to no runway (Marianas).

    Parallel ends are paired with beams left to right; an ambiguous match is None.
    """
    tied = {
        aid.id
        for strip in airport.runways
        for end in (strip.main, strip.opposite)
        for aid in end.beacons
    }
    beams = [
        beacon
        for bid, beacon in Beacons.for_airfield(airport.id, theater).items()
        if bid not in tied
        and beacon.beacon_type is BeaconType.BEACON_TYPE_ILS_LOCALIZER
        # Kola's Ivalo carries a 212 MHz "localizer".
        and beacon.hertz is not None
        and 108_000_000 <= beacon.hertz < 112_000_000
        and beacon.direction is not None
        and beacon.x is not None
        and beacon.y is not None
        and _angle_off((beacon.direction + 180) % 360, approach.heading) <= 30
    ]
    if not beams:
        return None
    parallel = [
        end.name
        for strip in airport.runways
        for end in (strip.main, strip.opposite)
        if _angle_off(end.heading, approach.heading) <= 30
    ]
    if len(beams) != len(parallel):
        return None
    if len(beams) == 1:
        return beams[0]
    course = math.radians(approach.heading)

    def leftward(beacon: Beacon) -> float:
        assert beacon.x is not None and beacon.y is not None
        return beacon.x * math.sin(course) - beacon.y * math.cos(course)

    sides = "LCR"
    if any(name[-1:] not in sides for name in parallel):
        return None
    parallel.sort(key=lambda name: sides.index(name[-1]))
    beams.sort(key=leftward, reverse=True)
    return beams[parallel.index(approach.name)]


_LOCALIZERS = (
    BeaconType.BEACON_TYPE_ILS_LOCALIZER,
    BeaconType.BEACON_TYPE_PRMG_LOCALIZER,
)

_ILS_TYPES = (
    BeaconType.BEACON_TYPE_ILS_LOCALIZER,
    BeaconType.BEACON_TYPE_ILS_GLIDESLOPE,
)


def runway_centerline(
    theater: ConflictTheater, airport: Airport, runway_name: str
) -> Optional[tuple[Point, float]]:
    """A point on the runway's surveyed centerline abeam the field, and its course.

    Read off a localizer at either end, so the line is the beam rather than the
    rounded pydcs heading. None when neither end has a usable localizer. Adapted
    from juanjux/dcs-escalation (LGPL-3.0).
    """
    for strip in airport.runways:
        ends = (strip.main, strip.opposite)
        approach = next((end for end in ends if end.name == runway_name), None)
        if approach is None:
            continue
        for end in (approach, *[e for e in ends if e is not approach]):
            for aid in end.beacons:
                beacon = RunwayData._get_beacon(aid.id, theater)
                if beacon is None or beacon.beacon_type not in _LOCALIZERS:
                    continue
                if beacon.x is None or beacon.y is None or beacon.direction is None:
                    continue
                # The beam bearing either way; keep the one on this approach.
                course = min(
                    (beacon.direction % 360, (beacon.direction + 180) % 360),
                    key=lambda h: abs((h - approach.heading + 180) % 360 - 180),
                )
                if abs((course - approach.heading + 180) % 360 - 180) > 30:
                    continue
                origin = Point(beacon.x, beacon.y, theater.terrain)
                if origin.distance_to_point(airport.position) > 10000:
                    continue
                north = math.cos(math.radians(course))
                east = math.sin(math.radians(course))
                along = (airport.position.x - beacon.x) * north + (
                    airport.position.y - beacon.y
                ) * east
                return (
                    Point(
                        beacon.x + along * north,
                        beacon.y + along * east,
                        theater.terrain,
                    ),
                    course,
                )
    return None


class RunwayAssigner:
    def __init__(self, conditions: Conditions):
        self.conditions = conditions

    def angle_off_headwind(self, runway: RunwayData) -> Heading:
        wind = Heading.from_degrees(self.conditions.weather.wind.at_0m.direction)
        ideal_heading = wind.opposite
        return runway.runway_heading.angle_between(ideal_heading)

    def get_preferred_runway(
        self, theater: ConflictTheater, airport: Airport
    ) -> RunwayData:
        """Returns the preferred runway for the given airport.

        Right now we're only selecting runways based on whether or not
        they have
        ILS, but we could also choose based on wind conditions, or which
        direction flight plans should follow.
        """
        runways = list(RunwayData.for_pydcs_airport(theater, airport))

        # Find the runway with the best headwind first.
        best_runways = [runways[0]]
        best_angle_off_headwind = self.angle_off_headwind(best_runways[0])
        for runway in runways[1:]:
            angle_off_headwind = self.angle_off_headwind(runway)
            if angle_off_headwind == best_angle_off_headwind:
                best_runways.append(runway)
            elif angle_off_headwind < best_angle_off_headwind:
                best_runways = [runway]
                best_angle_off_headwind = angle_off_headwind

        for runway in best_runways:
            # But if there are multiple runways with the same heading,
            # prefer
            # and ILS capable runway.
            if runway.ils is not None:
                return runway

        # Otherwise the only difference between the two is the distance from
        # parking, which we don't know, so just pick the first one.
        return best_runways[0]
