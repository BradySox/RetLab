"""Cards for the voice controllers (§116-§119): the ABCCC, SkyEye's AWACS, Vacuum, ATC.

Each card is the frequency, then the common calls the bot recognizes, each with its answer.
No prose on what a call does (user call, 2026-10-22).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Callable, Optional

from game.radio.radios import RadioFrequency
from game.retlab.voice_atc import AtcField, station_name
from ..kneeboard_page import KneeboardPage
from .writer import KneeboardPageWriter


def _freq(frequency: RadioFrequency) -> str:
    return f"{frequency.mhz:.3f} {frequency.modulation.name}"


def _spoken_freq(frequency: RadioFrequency) -> str:
    """``262.0`` or ``270.45``: a frequency as ATC says it."""
    label = f"{frequency.mhz:.3f}".rstrip("0")
    return label + "0" if label.endswith(".") else label


def _example_point(field: AtcField, exit: bool) -> str:
    """A chart point to show in the sample calls, or the generated one."""
    for point in field.routes.points if field.routes else ():
        if point.exit if exit else bool(point.entry_runways):
            return point.name
    return "10 miles"


def _altitude(field: AtcField, elevation_m: Optional[float]) -> str:
    """The chart's arrival/departure altitude, else the field elevation plus 2,000 ft, as
    the plugin gives it."""
    if field.routes is not None:
        return f"{field.routes.max_altitude_ft:,}"
    if elevation_m is None:
        return "2,000 above the field"
    return f"{math.ceil((elevation_m * 3.28084 + 2000) / 100) * 100:,}"


def _turn_for(field: AtcField, exit_name: str) -> Optional[str]:
    """``turn right heading 280``: the SOP turn off the field's runway for this exit."""
    number = field.runway.rstrip("LRC")
    for turn in field.routes.departure_turns if field.routes else ():
        if turn.runway.rstrip("LRC") == number and exit_name in turn.exits:
            return f"turn {turn.direction} heading {turn.heading:03d}"
    return None


def _lines(writer: KneeboardPageWriter, lines: list[str]) -> None:
    for line in lines:
        writer.text(line, wrap=True)


class AbcccPage(KneeboardPage):
    """The ABCCC's calls on STRIKE (§117)."""

    def __init__(
        self,
        controller: str,
        strike: RadioFrequency,
        callsign: str,
        dark_kneeboard: bool,
        fmt: Callable[[RadioFrequency], str] = _freq,
        push_time: Optional[str] = None,
        hold_angels: Optional[int] = None,
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        self.controller = controller
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard
        #: The package's planned push ("1432") and this flight's hold angels, when known.
        self.push_time = push_time
        self.hold_angels = hold_angels

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        c, me = self.controller, self.callsign
        # The mission's own numbers; one not known is left out, never made up.
        push = f" Push time {self.push_time}." if self.push_time else ""
        hold = (
            f" Cleared direct hold, angels {self.hold_angels}."
            if self.hold_angels is not None
            else ""
        )
        w.title(f"Talking to {c} (ABCCC)")
        w.text(f"STRIKE: {self.fmt(self.strike)}", fill=w.col_nav)
        w.rule()
        w.heading("Calls")
        _lines(
            w,
            [
                f'"{c}, {me}, checking in."',
                f'  {c}: "Radar contact.{hold}{push}"',
                f'"{c}, {me}, ready."',
                f'  {c}: "Copy ready.{push}"',
                f'"{c}, {me}, ready to push."',
                f'  {c}: "Push to join."  (or "Negative ...{push}")',
                f'"{c}, {me}, say push time."',
                f'  {c}: "Push time {self.push_time or "<time>"}."',
                f'At the join point, {c}: "Execute."',
                f'"{c}, {me}, off target."',
                f'  {c}: "Copy off, cleared egress."',
            ],
        )
        w.write(path)


class SkyEyeAwacsPage(KneeboardPage):
    """SkyEye's AWACS calls (§116)."""

    def __init__(
        self,
        awacs: str,
        frequency: RadioFrequency,
        strike: Optional[RadioFrequency],
        callsign: str,
        dark_kneeboard: bool,
        fmt: Callable[[RadioFrequency], str] = _freq,
        tanker: Optional[str] = None,
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        #: The callsign of the tanker that can refuel this jet, when one flies.
        self.tanker = tanker
        self.awacs = awacs
        self.frequency = frequency
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        a, me = self.awacs, self.callsign
        w.title(f"Talking to {a} (AWACS)")
        w.text(f"{a}: {self.fmt(self.frequency)}", fill=w.col_nav)
        if self.strike is not None:
            w.text(f"Also on STRIKE: {self.fmt(self.strike)}", fill=w.col_nav)
        w.rule()
        w.heading("Calls")
        # No "checking in": SkyEye answers it by asking radio check or alpha check.
        # Live numbers are placeholders: fixed figures read as mission data.
        tanker = f" {self.tanker}," if self.tanker else ""
        _lines(
            w,
            [
                f'"{a}, {me}, radio check."',
                f'  {a}: "5 by 5."',
                f'"{a}, {me}, picture."',
                f'  {a}: "<n> groups. Group bullseye <brg>/<rng>, <alt> thousand, hostile ..."',
                f'"{a}, {me}, bogey dope."',
                f'  {a}: "Group BRAA <brg>/<rng>, <alt> thousand, hot, hostile."  (or "Clean")',
                f'"{a}, {me}, declare <brg> <rng> <alt> thousand."',
                f'  {a}: "Hostile."  (or "Friendly", "Bogey", "Clean")',
                f'"{a}, {me}, spiked <brg>."',
                f'  {a}: "Spike range <rng>, <alt> thousand, hot, hostile."  (or "Clean <brg>")',
                f'"{a}, {me}, alpha check."',
                f'  {a}: "Contact, alpha check bullseye <brg>/<rng>."',
                f'"{a}, {me}, vector to tanker."',
                f'  {a}: "Nearest tanker,{tanker} BRA <brg>/<rng>."',
            ],
        )
        w.write(path)


class AtcPage(KneeboardPage):
    """Voice ATC (§119): the field frequencies and the calls in order."""

    def __init__(
        self,
        callsign: str,
        departure: Optional[AtcField],
        arrival: Optional[AtcField],
        dark_kneeboard: bool,
        divert: Optional[AtcField] = None,
        preset: Optional[Callable[[RadioFrequency], Optional[str]]] = None,
        wind: Optional[str] = None,
        altimeter: Optional[str] = None,
        elevations_m: Optional[dict[str, float]] = None,
        spot: Optional[str] = None,
        exit_name: Optional[str] = None,
    ) -> None:
        self.callsign = callsign
        #: The lead's spawn spot ("42") and the chart exit its route leaves by.
        self.spot = spot
        self.exit_name = exit_name
        #: The briefed surface wind ("230 at 8") and altimeter ("29.92"); the controllers
        #: read the live wind, so it can drift in flight.
        self.wind = wind
        self.altimeter = altimeter
        self.elevations_m = elevations_m or {}
        self.departure = departure
        self.arrival = arrival
        self.divert = divert
        #: The preset a frequency sits on in the flight's jets ("COMM2 Ch 2"), or None.
        self.preset = preset or (lambda _: None)
        self.dark_kneeboard = dark_kneeboard

    def _station(self, name: str, frequency: RadioFrequency) -> str:
        """``Tel Nof Ground: COMM2 Ch 2, 130.600 AM``, or the frequency alone when not preset."""
        channel = self.preset(frequency)
        return f"  {name}: {channel + ', ' if channel else ''}{_freq(frequency)}"

    def _fields(self) -> list[tuple[str, AtcField]]:
        """Each field once: home, then a different arrival, then the divert."""
        out: list[tuple[str, AtcField]] = []
        for role, f in (
            ("home", self.departure),
            ("arrival", self.arrival),
            ("divert", self.divert),
        ):
            if f is not None and all(f.name != seen.name for _, seen in out):
                out.append((role, f))
        return out

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        me = self.callsign
        out, home = self.departure, self.arrival or self.departure
        w.title("Talking to ATC")
        for role, f in self._fields():
            w.text(f"{f.name} ({role}), runway {f.runway}", fill=w.col_nav)
            w.text(
                self._station(station_name(f.name, "ground"), f.ground), fill=w.col_nav
            )
            w.text(
                self._station(station_name(f.name, "tower"), f.tower), fill=w.col_nav
            )
            for position, frequency in (
                ("departure", f.departure),
                ("approach", f.approach),
            ):
                if frequency is not None:
                    w.text(
                        self._station(station_name(f.name, position), frequency),
                        fill=w.col_nav,
                    )
            if f.routes is not None:
                w.text(f"  Entry and exit points ({f.routes.chart} chart):")
                for row in f.route_lines:
                    w.text(f"    {row}")
            elif f.approach is not None:
                w.text("  No chart: Approach gives an entry 10 NM out.")
        # The "You:" lines are the readbacks; any readback, or none, is accepted.
        wind = f"wind {self.wind}" if self.wind else "wind"
        alt = f"altimeter {self.altimeter}" if self.altimeter else "altimeter"
        flight_name = me.rsplit("-", 1)[0] + " flight"
        from_spot = f"from spot {self.spot}, " if self.spot else ""
        if out is not None:
            o, r = out.name, out.runway
            t = _spoken_freq(out.tower)
            departure_freq = out.departure or out.approach
            climb = _altitude(out, self.elevations_m.get(out.name))
            if departure_freq is not None:
                takeoff = f"contact Departure {_spoken_freq(departure_freq)}."
                if out.routes is not None:
                    exit_name = self.exit_name or _example_point(out, exit=True)
                    turn = _turn_for(out, exit_name)
                    lead = f"{turn}, " if turn else ""
                    clearance = (
                        f"{lead}climb and maintain {climb}, depart via {exit_name}"
                    )
                    report = exit_name
                else:
                    clearance = f"depart on present heading, climb and maintain {climb}"
                    report = "10 miles"
                departure = [
                    f'"{o} Departure, {me}, airborne."',
                    f'  ATC: "{me}, {o} Departure, radar contact, {clearance}, '
                    f'report {report}."',
                    f'"{me}, {report}."',
                    f'  ATC: "{me}, frequency change approved."',
                ]
            else:
                takeoff = "frequency change approved."
                departure = []
            w.rule()
            w.heading("Going out")
            _lines(
                w,
                [
                    f'"{o} Ground, {me}, radio check."',
                    f'  ATC: "{me}, {o} Ground, read you 5 by 5."',
                    f'"{o} Ground, {me}, flight of two, taxi."',
                    f'  ATC: "{flight_name}, {o} Ground, {from_spot}taxi to runway {r}, '
                    f'{alt}, hold short, contact Tower {t}."',
                    f'  You: "Taxi {r}, hold short, {me}."',
                    f'"{o} Ground, {me}, flight of two, taxi, have the numbers."',
                    f'  ATC: "{flight_name}, {o} Ground, {from_spot}taxi to runway {r}, '
                    f'hold short, contact Tower {t}."',
                    f'"{o} Tower, {me}, holding short {r}, ready for takeoff."',
                    f'  ATC: "{me}, runway {r}, {wind}, cleared for takeoff, {takeoff}"',
                    f'  You: "Cleared for takeoff, {me}."',
                    *departure,
                ],
            )
        if home is not None:
            h, r = home.name, home.runway
            hold = _altitude(home, self.elevations_m.get(home.name))
            if home.approach is not None:
                if home.routes is not None:
                    entry = _example_point(home, exit=False)
                    clearance = f"enter via {entry}"
                    report = entry
                else:
                    clearance = "proceed 10 miles north of the field"
                    report = "10 miles"
                arrival = [
                    f'"{h} Approach, {me}, 30 miles north, inbound, full stop."',
                    f'  ATC: "{me}, {h} Approach, radar contact, runway {r}, {clearance}, '
                    f'maintain {hold}, report {report}."',
                    f'"{me}, {report}."',
                    f'  ATC: "{me}, contact Tower {_spoken_freq(home.tower)}."',
                    f'"{h} Tower, {me}."',
                    f'  ATC: "{me}, {h} Tower, runway {r}, {wind}, report initial."',
                ]
            else:
                arrival = [
                    f'"{h} Tower, {me}, 10 miles, full stop."',
                    f'  ATC: "{me}, runway {r}, {wind}, report initial."',
                ]
            w.rule()
            w.heading("Coming home")
            _lines(
                w,
                [
                    *arrival,
                    f'"{h} Tower, {me}, 10 miles, request straight-in."',
                    f'  ATC: "{me}, runway {r}, {wind}, make straight-in, report 3-mile final."',
                    f'"{me}, initial."',
                    f'  ATC: "{me}, roger."',
                    f'"{me}, base, gear down, full stop."',
                    f'  ATC: "{me}, runway {r}, {wind}, cleared to land."',
                    f'  You: "Cleared to land, {me}."',
                    f'"{h} Tower, {me}, clear of runway {r}."',
                    f'  ATC: "{me}, taxi to parking'
                    + (f', spot {self.spot}."' if self.spot and home is out else '."'),
                    f'"Mayday, mayday, mayday, {me}, engine failure."',
                    f'  ATC: "{me}, {h} Tower, roger mayday, cleared to land any runway."',
                ],
            )
        w.write(path)


#: The player tasks that get the Vacuum card (user call, 2026-10-21).
class VacuumPage(KneeboardPage):
    """Vacuum's calls (§118): for every player flight when one flies."""

    def __init__(
        self,
        frequency: RadioFrequency,
        strike: Optional[RadioFrequency],
        callsign: str,
        dark_kneeboard: bool,
        fmt: Callable[[RadioFrequency], str] = _freq,
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        self.frequency = frequency
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        me = self.callsign
        w.title("Talking to Vacuum (ELINT)")
        w.text(f"Vacuum: {self.fmt(self.frequency)}", fill=w.col_nav)
        if self.strike is not None:
            w.text(f"Also on STRIKE: {self.fmt(self.strike)}", fill=w.col_nav)
        w.rule()
        w.heading("Calls")
        _lines(
            w,
            [
                f'"Vacuum, {me}, checking in."',
                '  Vacuum: "Two awake, one asleep, nearest SA-6 awake, bullseye '
                '090/25, tight."',
                f'"Vacuum, {me}, say emitters."',
                '  Vacuum: "SA-6 awake 270, 35, tight; SA-11 asleep 245, 50, loose."',
                f'"Vacuum, {me}, request target status."',
                '  Vacuum: "Target area, SA-6 awake, bullseye 095/22, loose."',
                f'"Vacuum, {me}, mud 270."',
                '  Vacuum: "Mud 270 is SA-6 awake, bullseye 090/25, tight."',
                f'"Vacuum, {me}, say again."',
                "  Vacuum: its last call to you, again.",
            ],
        )
        w.rule()
        # Vacuum hears only radiating radars; "blank" must never read as "safe" (§118).
        w.text(
            "A SAM that keeps its radar off is invisible to Vacuum. "
            '"Blank" does not mean safe.',
            fill=w.col_caution,
            wrap=True,
        )
        w.write(path)
