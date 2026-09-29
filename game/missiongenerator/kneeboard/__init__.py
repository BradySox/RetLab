"""Generates kneeboard pages relevant to the player's mission.

Each client flight gets Mission Info (BLUF, airfields, flight plan with fuel,
weather), Support Info (package, AEW&C, tankers, JTAC, code words) and, by
setting, target, threat-intel, recon, SITREP and friendly-package pages.

DCS adds kneeboard pages per airframe, not per flight, so every flight of one
type shares a stacked deck -- and in PvP each side sees the other's deck for a
shared airframe.
"""

from .briefing import BriefingPage, _brief_loadout
from .flightplan import FlightPlanBuilder
from .generator import KneeboardGenerator
from .pages import KneeboardIndexPage, SavedPointsPage, SitrepPage
from .writer import (
    KneeboardPageWriter,
    LOCAL_CELL_TOKEN,
    _labelled_time,
    format_kneeboard_time,
    format_kneeboard_time_inline,
)
from .packagesmap import PackagesMapPage
from .taskpages import SeadTaskPage, StrikeTaskPage
from .support import SupportPage, build_airfield_directory_rows
from .threatintel import (
    ThreatCard,
    ThreatIntelBriefPage,
    _brief_sam_threats,
    build_threat_intel_cards,
)

__all__ = [
    "BriefingPage",
    "FlightPlanBuilder",
    "KneeboardGenerator",
    "KneeboardIndexPage",
    "KneeboardPageWriter",
    "LOCAL_CELL_TOKEN",
    "PackagesMapPage",
    "SavedPointsPage",
    "SeadTaskPage",
    "SitrepPage",
    "StrikeTaskPage",
    "SupportPage",
    "ThreatCard",
    "ThreatIntelBriefPage",
    "_brief_loadout",
    "_brief_sam_threats",
    "_labelled_time",
    "build_airfield_directory_rows",
    "build_threat_intel_cards",
    "format_kneeboard_time",
    "format_kneeboard_time_inline",
]
