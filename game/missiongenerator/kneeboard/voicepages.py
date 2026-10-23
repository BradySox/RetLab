"""Cards for the voice controllers (§116-§119): the ABCCC, SkyEye's AWACS, Vacuum, ATC.

Each card is the frequency, then the common calls the bot recognizes, each with its answer.
No prose on what a call does (user call, 2026-10-22).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from game.ato.flighttype import FlightType
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
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
        self.controller = controller
        self.strike = strike
        self.callsign = callsign
        self.dark_kneeboard = dark_kneeboard

    def write(self, path: Path) -> None:
        w = KneeboardPageWriter(dark_theme=self.dark_kneeboard)
        c, me = self.controller, self.callsign
        w.title(f"Talking to {c} (ABCCC)")
        w.text(f"STRIKE: {self.fmt(self.strike)}", fill=w.col_nav)
        w.rule()
        w.heading("Calls")
        _lines(
            w,
            [
                f'"{c}, {me}, checking in."',
                f'  {c}: "Radar contact. Cleared direct hold, angels 20. Push time 1432."',
                f'"{c}, {me}, ready."',
                f'  {c}: "Copy ready. Push time 1432."',
                f'"{c}, {me}, ready to push."',
                f'  {c}: "Push."  (or "Negative ... Push time 1432.")',
                f'"{c}, {me}, say push time."',
                f'  {c}: "Push time 1432."',
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
    ) -> None:
        #: How a frequency prints: with its preset channel when the generator knows it.
        self.fmt = fmt
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
        _lines(
            w,
            [
                f'"{a}, {me}, radio check."',
                f'  {a}: "5 by 5."',
                f'"{a}, {me}, picture."',
                f'  {a}: "2 groups. Group bullseye 090/40, 20 thousand, hostile ..."',
                f'"{a}, {me}, bogey dope."',
                f'  {a}: "Group BRAA 270/25, 20 thousand, hot, hostile."  (or "Clean")',
                f'"{a}, {me}, declare 090 20 15 thousand."',
                f'  {a}: "Hostile."  (or "Friendly", "Bogey", "Clean")',
                f'"{a}, {me}, spiked 270."',
                f'  {a}: "Spike range 25, 20 thousand, hot, hostile."  (or "Clean 270")',
                f'"{a}, {me}, alpha check."',
                f'  {a}: "Contact, alpha check bullseye 090/40."',
                f'"{a}, {me}, vector to tanker."',
                f'  {a}: "Nearest tanker, Texaco 1, BRA 180/40."',
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
        # The "You:" lines are the readbacks Strict radio discipline asks for.
        if out is not None:
            o, r = out.name, out.runway
            w.rule()
            w.heading("Going out")
            _lines(
                w,
                [
                    f'"{o} Ground, {me}, radio check."',
                    f'  ATC: "{o} Ground, read you 5 by 5."',
                    f'"{o} Ground, {me}, request taxi."',
                    f'  ATC: "Taxi to runway {r}, hold short, contact Tower '
                    f'{_spoken_freq(out.tower)}."',
                    f'  You: "Hold short {r}, {me}."',
                    f'"{o} Tower, {me}, holding short runway {r}, ready."',
                    f'  ATC: "Runway {r}, wind, altimeter, cleared for takeoff."',
                    f'  You: "Cleared for takeoff {r}, {me}."',
                    f'"{o} Tower, {me}, airborne."',
                    '  ATC: "Frequency change approved."',
                ],
            )
        if home is not None:
            h, r = home.name, home.runway
            w.rule()
            w.heading("Coming home")
            _lines(
                w,
                [
                    f'"{h} Tower, {me}, 5 miles, full stop."',
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
VACUUM_TASKS = frozenset({FlightType.SEAD, FlightType.SEAD_ESCORT, FlightType.DEAD})


class VacuumPage(KneeboardPage):
    """Vacuum's calls (§118): for SEAD, SEAD Escort and DEAD players when one flies."""

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
