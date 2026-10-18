import logging
from typing import Optional

from PySide6.QtWidgets import QComboBox

from dcs.liveries.livery import Livery
from dcs.liveries.liverycache import LiveryCache

from game.dcs.aircrafttype import AircraftType
from game.squadrons import Squadron

LIVERY_SET_TEXT = "Use livery-set from squadron's yaml"
LIVERY_OVERRIDES_TEXT = "Use livery overrides"

#: Aircraft we already rescanned the liveries for, so a mod that genuinely ships no
#: liveries doesn't trigger a full rescan every time its squadron dialog is opened.
_rescanned_aircraft: set[str] = set()

#: Set once a rescan turns up nothing new anywhere, at which point further rescans are
#: just wasted disk I/O for the rest of the session.
_rescan_is_futile = False


def _livery_count() -> int:
    return sum(len(liveries) for liveries in LiveryCache.cache().values())


def dcs_liveries_for(aircraft_type: AircraftType) -> set[Livery]:
    """The liveries DCS offers for an aircraft.

    The livery scan is a one-shot, process-wide cache built during startup. An aircraft
    mod that was installed, re-enabled or moved while Retribution was already running is
    therefore missing from it, and the aircraft looks like it has no liveries at all for
    the rest of the session. Rescan once per aircraft before believing an empty result.
    """
    global _rescan_is_futile

    liveries = set(aircraft_type.dcs_unit_type.iter_liveries())
    if liveries:
        return liveries

    key = aircraft_type.variant_id
    if _rescan_is_futile or key in _rescanned_aircraft:
        return liveries
    _rescanned_aircraft.add(key)

    logging.info(
        "No liveries cached for %s (livery name %s), rescanning DCS liveries",
        aircraft_type,
        aircraft_type.dcs_unit_type.livery_name,
    )
    before = _livery_count()
    try:
        # pydcs has no public way to invalidate the scan.
        LiveryCache._cache = None
        _rescan_is_futile = _livery_count() == before
    except Exception:
        logging.exception("Rescanning DCS liveries failed")
        _rescan_is_futile = True
        return liveries
    return set(aircraft_type.dcs_unit_type.iter_liveries())


class SquadronLiverySelector(QComboBox):
    """
    A combo box for selecting a squadron's livery.
    The combo box will automatically be populated with all available liveries.
    """

    def __init__(self, squadron: Squadron, update_squadron: bool = True) -> None:
        super().__init__()
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.squadron = squadron
        self.aircraft_type = squadron.aircraft
        selected_livery = squadron.livery

        if update_squadron:
            self.currentTextChanged.connect(self.on_change)

        liveries = set()
        # The squadron's own nation, not the faction's: Anatolian Reach's
        # Israeli squadrons in a USA faction lost their ISR-only paint here.
        faction_cc = squadron.coalition.faction.country.shortname
        country = getattr(squadron, "country", None)
        cc = country.shortname if country is not None else faction_cc
        aircraft_liveries = dcs_liveries_for(self.aircraft_type)
        if len(aircraft_liveries) == 0:
            logging.info(f"Liveries for {self.aircraft_type} is empty!")
        for livery in aircraft_liveries:
            valid_livery = livery.countries is None or cc in livery.countries
            if valid_livery or faction_cc in ["BLUE", "RED"]:
                liveries.add(livery)
        faction = squadron.coalition.faction
        overrides = [
            x
            for x in faction.liveries_overrides.get(self.aircraft_type, [])
            if x in [y.id.lower() for y in liveries]
        ]
        if selected_livery and selected_livery.lower() not in [
            livery.id.lower() for livery in liveries
        ]:
            # squadron livery not found, or incompatible with faction
            # => attempt to use the unit's default-livery as a fallback
            selected_livery = None
        if squadron.livery_set:
            self.addItem(LIVERY_SET_TEXT, userData=None)
        if len(overrides) > 0:
            self.addItem(LIVERY_OVERRIDES_TEXT, userData=None)
        if (
            selected_livery is None
            and not squadron.livery_set
            and squadron.aircraft.default_livery
        ):
            selected_livery = squadron.aircraft.default_livery
        for livery in sorted(liveries):
            self.addItem(livery.name, userData=livery.id)
            if selected_livery is not None and not squadron.livery_set:
                if selected_livery.lower() == livery.id:
                    self.setCurrentText(livery.name)
        if len(liveries) == 0:
            self.addItem("No available liveries (using DCS default)")
            self.setEnabled(False)
        self.default_index = self.currentIndex()

    def select_livery(self, livery: Optional[str], use_livery_set: bool) -> None:
        """Show a flight member's saved choice, else the squadron default."""
        index = -1
        if livery is not None:
            for i in range(self.count()):
                data = self.itemData(i)
                if isinstance(data, str) and data.lower() == livery.lower():
                    index = i
                    break
        else:
            text = LIVERY_SET_TEXT if use_livery_set else LIVERY_OVERRIDES_TEXT
            index = self.findText(text)
        self.setCurrentIndex(index if index >= 0 else self.default_index)

    @property
    def using_livery_set(self) -> bool:
        return self.currentText() == LIVERY_SET_TEXT

    def on_change(self, text: str) -> None:
        self.squadron.livery = self.currentData()
        if text == LIVERY_SET_TEXT:
            self.squadron.use_livery_set = True
        else:
            self.squadron.use_livery_set = False
