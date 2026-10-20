"""Voice AWACS on SRS (§116): the SkyEye frequency, callsign and briefing line."""

from __future__ import annotations

from pathlib import Path

import pytest
from dcs.task import Modulation
from jinja2 import Environment

from game.radio.radios import MHz, RadioFrequency
from game.retlab.voiceawacs import (
    VoiceAwacsInfo,
    parse_voice_awacs_frequency,
    voice_awacs_for,
)
from game.settings import Settings

TEMPLATES = Path("resources/briefing/templates")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("251.0 AM", MHz(251)),
        ("251", MHz(251)),
        ("251.25 am", MHz(251, 250)),
        ("133.000 MHz AM", MHz(133)),
        ("30.0 FM", MHz(30, 0, Modulation.FM)),
    ],
)
def test_a_frequency_reads_in_mhz_with_its_modulation(
    text: str, expected: RadioFrequency
) -> None:
    assert parse_voice_awacs_frequency(text) == expected


@pytest.mark.parametrize("text", ["", "SkyEye", "251,0", "2510.0 AM", "251.0 SSB"])
def test_an_unreadable_frequency_is_none(text: str) -> None:
    assert parse_voice_awacs_frequency(text) is None


def test_off_by_default() -> None:
    assert Settings().voice_awacs is False
    assert voice_awacs_for(Settings()) is None


def test_on_gives_the_default_skyeye_line() -> None:
    settings = Settings()
    settings.voice_awacs = True
    assert voice_awacs_for(settings) == VoiceAwacsInfo("Sentinel", MHz(251))


def test_a_bad_frequency_falls_back_to_251_and_a_blank_callsign_to_sentinel() -> None:
    settings = Settings()
    settings.voice_awacs = True
    settings.voice_awacs_frequency = "two fifty one"
    settings.voice_awacs_callsign = "  "
    assert voice_awacs_for(settings) == VoiceAwacsInfo("Sentinel", MHz(251))


@pytest.mark.parametrize("lang", ["EN", "CN", "FR"])
def test_every_briefing_lists_skyeye_above_the_silent_awacs(lang: str) -> None:
    # Only the AWACS block: the whole template needs a full game to render.
    source = (TEMPLATES / f"briefingtemplate_{lang}.j2").read_text(encoding="utf-8")
    block = source[source.index("{%- if awacs|length > 0 or voice_awacs %}") :]
    block = block[: block.index("{% endfor %}") + len("{% endfor %}")]
    text = (
        Environment()
        .from_string(block + "{% endif %}")
        .render(awacs=[], voice_awacs=VoiceAwacsInfo("Sentinel", MHz(251)))
    )
    assert "Sentinel (SkyEye)" in text
    assert "251.0 AM" in text
