"""Cards for the voice controllers (§116-§119): the ABCCC, SkyEye's AWACS, Vacuum, ATC.

Each card is the frequency, then the common calls the bot recognizes, each with its answer.
No prose on what a call does (user call, 2026-10-22).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from game.radio.radios import RadioFrequency
from game.retlab.voice_atc import AtcField, approach_name, station_name
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


def _altitude(field: AtcField) -> str:
    return f"{field.routes.max_altitude_ft:,}" if field.routes else "field plus 2,000"


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
    ) -> None:
        self.callsign = callsign
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
            if f.approach is not None:
                w.text(
                    self._station(approach_name(f.name), f.approach),
                    fill=w.col_nav,
                )
            if f.routes is not None:
                w.text(f"  Entry and exit points ({f.routes.chart} chart):")
                for row in f.route_lines:
                    w.text(f"    {row}")
            elif f.approach is not None:
                w.text("  No chart: Approach gives an entry 10 NM out.")
        # The "You:" lines are the readbacks; any readback, or none, is accepted.
        if out is not None:
            o, r = out.name, out.runway
            t = _spoken_freq(out.tower)
            if out.approach is not None:
                takeoff = f"contact Departure {_spoken_freq(out.approach)}."
                exit_name = _example_point(out, exit=True)
                departure = [
                    f'"{o} Departure, {me}, airborne."',
                    f'  ATC: "Radar contact, depart via {exit_name}, climb and maintain '
                    f'{_altitude(out)}, report {exit_name}."',
                    f'"{o} Departure, {me}, {exit_name}."',
                    '  ATC: "Frequency change approved."',
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
                    f'  ATC: "{o} Ground, read you 5 by 5."',
                    f'"{o} Ground, {me}, request taxi."',
                    f'  ATC: "Runway {r}, altimeter, taxi, hold short runway {r}, '
                    f'contact Tower {t}."',
                    f'  You: "Hold short {r}, {me}."',
                    f'"{o} Ground, {me}, flight of two, have the numbers, request taxi."',
                    f'  ATC: "{me} flight, runway {r}, taxi, hold short runway {r}, '
                    f'contact Tower {t}."',
                    f'"{o} Tower, {me}, holding short runway {r}, ready."',
                    f'  ATC: "Runway {r}, wind, cleared for takeoff, {takeoff}"',
                    f'  You: "Cleared for takeoff {r}, {me}."',
                    *departure,
                ],
            )
        if home is not None:
            h, r = home.name, home.runway
            if home.approach is not None:
                entry = _example_point(home, exit=False)
                arrival = [
                    f'"{h} Approach, {me}, 30 miles north, inbound, full stop."',
                    f'  ATC: "Radar contact, runway {r}, enter via {entry}, maintain '
                    f'{_altitude(home)}, report {entry}."',
                    f'"{h} Approach, {me}, {entry}."',
                    f'  ATC: "Contact Tower {_spoken_freq(home.tower)}."',
                    f'"{h} Tower, {me}."',
                    f'  ATC: "Runway {r}, wind, report initial."',
                ]
            else:
                arrival = [
                    f'"{h} Tower, {me}, 10 miles, full stop."',
                    f'  ATC: "Runway {r}, wind, report initial."',
                ]
            w.rule()
            w.heading("Coming home")
            _lines(
                w,
                [
                    *arrival,
                    f'"{h} Tower, {me}, 10 miles, request straight-in."',
                    f'  ATC: "Runway {r}, wind, make straight-in, report 3-mile final."',
                    f'"{me}, initial."',
                    '  ATC: "Roger."',
                    f'"{me}, base, gear down, full stop."',
                    f'  ATC: "Runway {r}, wind, cleared to land."',
                    f'  You: "Cleared to land {r}, {me}."',
                    f'"{h} Tower, {me}, clear of the runway."',
                    '  ATC: "Taxi to parking."',
                    f'"Mayday, {me}, emergency fuel."',
                    '  ATC: "Cleared to land any runway."',
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
