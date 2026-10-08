"""Per-flight planner controls for the native DTC cartridge (§74).

Lives in ``game.ato`` because it pickles with the :class:`Flight` (the Edit
Flight dialog writes it, the campaign save carries it, and the next
generation's ``DtcGenerator`` honors it). Deliberately a plain dataclass of
builtins so old saves unpickle trivially (``Flight.__setstate__`` defaults a
missing field to ``DtcOptions()``, which reproduces pre-feature behavior).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Optional

from game.ato.flighttype import FlightType

#: How far from the route a site's ring may sit and still be drawn on a flight
#: that is passing through the threat, not there to fight it.
ROUTE_RING_RADIUS_NM = 40
#: The narrowest ring a CAP flight is shown: the systems that reach a fighter
#: at altitude, not the short-range point defense.
LONG_RANGE_RING_NM = 15

#: Every known site: these flights are there to fight the SAMs.
_ALL_RING_TASKS = frozenset(
    {
        FlightType.SEAD,
        FlightType.DEAD,
        FlightType.SEAD_ESCORT,
        FlightType.SEAD_SWEEP,
    }
)
_LONG_RANGE_RING_TASKS = frozenset(
    {
        FlightType.BARCAP,
        FlightType.TARCAP,
        FlightType.INTERCEPTION,
        FlightType.SWEEP,
    }
)
_ROUTE_RING_TASKS = frozenset(
    {
        FlightType.STRIKE,
        FlightType.BAI,
        FlightType.CAS,
        FlightType.OCA_RUNWAY,
        FlightType.OCA_AIRCRAFT,
        FlightType.ANTISHIP,
        FlightType.ARMED_RECON,
        FlightType.ESCORT,
    }
)
#: The front line is drawn on CAS alone (DM call, 2026-10-08).
_FRONT_LINE_TASKS = frozenset({FlightType.CAS})


@dataclass
class DtcOptions:
    """What (if anything) this flight's cartridge should carry.

    ``enabled`` is a tri-state: ``None`` follows the campaign-wide
    ``dtc_data_cartridges`` setting, ``True``/``False`` override it for this
    flight alone. The section flags select cartridge contents; a section that
    is off is omitted entirely, leaving the jet's own defaults untouched.
    """

    enabled: Optional[bool] = None
    #: Hornet channel names; the F-14B(U)'s TIS send-to list.
    comms: bool = True
    #: The flight's steerpoints + route sequence (ETAs, leg speeds).
    route: bool = True
    #: Recovery aids: TACAN/ICLS/ACLS pre-tune + FPAS home waypoint (Hornet).
    nav_aids: bool = True
    #: The active front line(s) (SA FLOT lines / HSD GEO lines).
    flot_and_zones: bool = True
    #: Land borders near the route (§98 geometry; HSD GEO lines, Viper only).
    borders: bool = True
    #: Friendly CAP stations + tanker/AEW&C orbits (SA racetracks; Viper
    #: anchor steerpoints).
    friendly_orbits: bool = True
    #: Known enemy SAM threat rings (recon-fogged).
    threat_rings: bool = True
    #: Friendly recovery fields as Destination steerpoints (Viper only -- the
    #: Hornet descriptor has no equivalent section).
    destinations: bool = True
    #: Pre-planned target points on the weapon stations (F-14B(U) only).
    jdam_targets: bool = True
    #: The ROE tab's Air Target Data Table, derived from the campaign's own
    #: order of battle (F-16C only -- blue-only families FRIENDLY, red-only
    #: HOSTILE, shared or unflown UNKNOWN).
    roe_table: bool = True
    #: Countermeasure dispenser programs and the bingo counts (F-16C only).
    #: Default OFF: the F-16C guide warns the CMDS MODE knob must be STBY
    #: before an MPD upload, and AutoLoad fires on a cold jet with the knob
    #: elsewhere. Checklist B28 carries the flown check that would flip this.
    countermeasures: bool = False
    #: The player's saved points (§102): the route's second sequence, the
    #: Tomcat's plan 3.
    saved_points: bool = True
    #: The player's own lines and areas (§102), on each jet's free drawing slots.
    drawings: bool = True
    #: Known SAM sites within this many nm of the route; None writes every one.
    threat_ring_radius_nm: Optional[int] = None
    #: Only sites whose ring is LONG_RANGE_RING_NM or wider.
    long_range_rings_only: bool = False
    #: Load at spawn. Off (the default, DM 2026-09-29) binds the cartridge but
    #: leaves loading to the pilot, so the Viper crew can set CMDS to STBY first (B28).
    auto_load: bool = False
    #: FlightWaypointType names left out of the cartridge's route. The kneeboard
    #: prints "-" for them, so its numbers still match the jet.
    skipped_waypoints: list[str] = field(default_factory=list)

    def __setstate__(self, state: dict[str, object]) -> None:
        """A field added after a save was written unpickles to its default."""
        self.__dict__.update(DtcOptions().__dict__)
        self.__dict__.update(state)

    @classmethod
    def for_task(cls, flight_type: FlightType) -> DtcOptions:
        """The starting ticks for a new flight of this task (DM call, 2026-10-08).

        The DTC tab shows them, so any flight can still be changed by hand.
        """
        options = cls()
        options.flot_and_zones = flight_type in _FRONT_LINE_TASKS
        if flight_type in _LONG_RANGE_RING_TASKS:
            options.long_range_rings_only = True
        elif flight_type in _ROUTE_RING_TASKS:
            options.threat_ring_radius_nm = ROUTE_RING_RADIUS_NM
        return options

    def saved_fields(self) -> dict[str, Any]:
        """What "Save as my default" keeps: everything but the on/off override,
        which stays with the campaign setting."""
        return {
            f.name: getattr(self, f.name) for f in fields(self) if f.name != "enabled"
        }

    def apply_saved(self, saved: dict[str, Any]) -> None:
        """Overlay a saved default; unknown or mistyped keys are skipped."""
        for f in fields(self):
            if f.name == "enabled" or f.name not in saved:
                continue
            value = saved[f.name]
            current = getattr(self, f.name)
            if f.name == "threat_ring_radius_nm":
                if value is None or (
                    isinstance(value, int) and not isinstance(value, bool)
                ):
                    self.threat_ring_radius_nm = value
            elif f.name == "skipped_waypoints":
                if isinstance(value, list) and all(isinstance(v, str) for v in value):
                    self.skipped_waypoints = list(value)
            elif isinstance(current, bool) and isinstance(value, bool):
                setattr(self, f.name, value)

    def resolve_enabled(self, campaign_default: bool) -> bool:
        """The effective on/off for this flight."""
        if self.enabled is None:
            return campaign_default
        return self.enabled

    @property
    def any_content(self) -> bool:
        """Whether any section would make it into the cartridge."""
        return any(
            (
                self.comms,
                self.route,
                self.nav_aids,
                self.flot_and_zones,
                self.borders,
                self.friendly_orbits,
                self.threat_rings,
                self.destinations,
                self.jdam_targets,
                self.roe_table,
                self.saved_points,
                self.drawings,
            )
        )
