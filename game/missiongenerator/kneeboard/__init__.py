"""Generates kneeboard pages relevant to the player's mission.

The player kneeboard includes the following information:

* Airfield (departure, arrival, divert) info.
* Flight plan (waypoint numbers, names, altitudes).
* Comm channels.
* AWACS info.
* Tanker info.
* JTAC info.

Things we should add:

* Flight plan ToT and fuel ladder (current have neither available).
* Support for planning an arrival/divert airfield separate from departure.
* Mission package infrastructure to include information about the larger
  mission, i.e. information about the escort flight for a strike package.
* Target information. Steerpoints, preplanned objectives, ToT, etc.

For multiplayer missions, a kneeboard will be generated per flight.
https://forums.eagle.ru/showthread.php?t=206360 claims that kneeboard pages can
only be added per airframe, so PvP missions where each side have the same
aircraft will be able to see the enemy's kneeboard for the same airframe.
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
