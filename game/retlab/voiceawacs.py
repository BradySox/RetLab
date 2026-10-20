"""Voice AWACS on SRS (§116): a SkyEye GCI bot stands in for the blue AWACS voice.

SkyEye runs outside DCS, on the player's SRS server, and reads the picture from
Tacview's live feed. RetLab only clears the way: blue AEW&C flights go radio
silent, the SkyEye frequency is held back from the radio pool, and the kneeboard
and briefing name it. docs/dev/retlab-features.md §116.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from dcs.task import Modulation

from game.radio.radios import RadioFrequency

if TYPE_CHECKING:
    from game.settings import Settings

#: The AWACS takes the next name each turn (user call, 2026-10-20).
DEFAULT_CALLSIGNS = ("Chalice", "Chainsaw", "Image")

_FREQUENCY = re.compile(
    r"^\s*(\d{2,3})(?:\.(\d{1,3}))?\s*(?:MHz)?\s*(AM|FM)?\s*$", re.IGNORECASE
)


@dataclass(frozen=True)
class VoiceAwacsInfo:
    """The SkyEye line on the kneeboard and briefing."""

    callsign: str
    freq: RadioFrequency


def parse_voice_awacs_frequency(text: str) -> Optional[RadioFrequency]:
    """``"251.0 AM"``, ``"251"`` or ``"30.0 FM"``; None when unreadable."""
    match = _FREQUENCY.match(text)
    if match is None:
        return None
    whole = int(match.group(1))
    partial_str = match.group(2) or "0"
    khz = int(partial_str.ljust(3, "0"))
    modulation = (
        Modulation.FM if (match.group(3) or "AM").upper() == "FM" else Modulation.AM
    )
    return RadioFrequency(whole * 1_000_000 + khz * 1_000, modulation)


def callsign_for_turn(text: str, turn: int) -> str:
    """The comma-separated callsign list's name for this turn."""
    names = [n.strip() for n in text.split(",") if n.strip()] or list(DEFAULT_CALLSIGNS)
    return names[turn % len(names)]


def voice_awacs_for(settings: Settings, turn: int = 0) -> Optional[VoiceAwacsInfo]:
    """The SkyEye line for this mission, or None when the setting is off."""
    if not settings.voice_awacs:
        return None
    freq = parse_voice_awacs_frequency(settings.voice_awacs_frequency)
    if freq is None:
        logging.warning(
            "Voice AWACS: cannot read SkyEye frequency %r; using 251.0 AM",
            settings.voice_awacs_frequency,
        )
        freq = RadioFrequency(251_000_000, Modulation.AM)
    callsign = callsign_for_turn(settings.voice_awacs_callsign, turn)
    return VoiceAwacsInfo(callsign=callsign, freq=freq)
