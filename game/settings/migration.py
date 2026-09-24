"""Old save and settings-file state, rewritten into the current fields."""

from typing import Any, Optional, TYPE_CHECKING


from ..ato.starttype import StartType

if TYPE_CHECKING:
    pass
from .enums import (
    AiRadioBehavior,
    CarrierDeckPolicy,
    CloudPresetPack,
    CombatResolutionMethod,
    DatalinkPolicy,
    FastForwardStopCondition,
)


def migrate_legacy_settings(state: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(state)

    # The per-base-type ground-start truck toggles were consolidated: the old
    # roadbase-specific options folded into the single airbase+roadbase
    # toggles. Preserve intent -- a save that had trucks enabled at *either*
    # base type keeps them enabled. The obsolete roadbase keys are dropped
    # in the obsolete-key sweep below.
    if "ground_start_trucks_roadbase" in migrated:
        migrated["ground_start_trucks"] = bool(
            migrated.get("ground_start_trucks", False)
            or migrated.get("ground_start_trucks_roadbase", False)
        )
    if "ground_start_ground_power_trucks_roadbase" in migrated:
        migrated["ground_start_ground_power_trucks"] = bool(
            migrated.get("ground_start_ground_power_trucks", True)
            or migrated.get("ground_start_ground_power_trucks_roadbase", True)
        )

    # The EPLRS boolean became the DatalinkPolicy enum. The save's explicit
    # choice is preserved rather than silently promoted to ERA_CORRECT: a
    # campaign that deliberately turned datalink off must stay off, and one
    # that had it on must not lose it mid-campaign because an airframe's
    # `datalink_introduced` postdates the campaign. ERA_CORRECT is the
    # default for NEW games only. The old key is dropped in the sweep below.
    if "datalink_policy" not in migrated and "eplrs_enabled" in migrated:
        migrated["datalink_policy"] = (
            DatalinkPolicy.ALWAYS if migrated["eplrs_enabled"] else DatalinkPolicy.NEVER
        )

    # The carrier six-pack boolean became the CarrierDeckPolicy enum (§64).
    # ON exempted player flights from the off-six-pack placement delay (so
    # they filled the six-pack); OFF already behaved like the last-resort
    # policy. Preserve whichever the save had; the old key is dropped in the
    # obsolete-key sweep below.
    if "carrier_deck_policy" not in migrated and "player_flights_sixpack" in migrated:
        migrated["carrier_deck_policy"] = (
            CarrierDeckPolicy.SIXPACK_FIRST
            if migrated["player_flights_sixpack"]
            else CarrierDeckPolicy.LAST_RESORT
        )

    # Pre-pack saves carried a boolean "use Bandit's clouds"; the packs are now
    # a choice (several mods ship presets under the same Preset35+ keys, so only
    # one may be injected). Keep whichever the save had; the old key is dropped
    # in the obsolete-key sweep below.
    if "cloud_preset_pack" not in migrated and "use_bandit_clouds" in migrated:
        migrated["cloud_preset_pack"] = (
            CloudPresetPack.BANDIT
            if migrated["use_bandit_clouds"]
            else CloudPresetPack.NONE
        )

    if "ai_radio_behavior" not in migrated:
        silence_ai_radios = migrated.get("silence_ai_radios", False)
        limit_ai_radios = migrated.get("limit_ai_radios", True)
        if silence_ai_radios:
            behavior = AiRadioBehavior.SILENT
        elif limit_ai_radios:
            behavior = AiRadioBehavior.LIMITED
        else:
            behavior = AiRadioBehavior.FULL
        migrated["ai_radio_behavior"] = behavior

    # A save from before the scatter band carried only the symmetric
    # max_plane_altitude_offset. Mirror it into the new minimum so the
    # legacy +/-max spread is preserved exactly: a flat -2 default would
    # re-enable scatter on a save that had set max to 0, and shrink the
    # downward half of a wider band.
    if (
        "min_plane_altitude_offset" not in migrated
        and "max_plane_altitude_offset" in migrated
    ):
        migrated["min_plane_altitude_offset"] = -migrated["max_plane_altitude_offset"]

    for obsolete_key in (
        "limit_ai_radios",
        "silence_ai_radios",
        "prefer_squadrons_with_matching_primary_task",
        "pretense_num_of_cargo_planes",
        "pretense_maxdistfromfront_distance",
        "pretense_controllable_carrier",
        "pretense_carrier_steams_into_wind",
        "pretense_carrier_zones_navmesh",
        "pretense_extra_zone_connections",
        "pretense_sead_flights_per_cp",
        "pretense_cas_flights_per_cp",
        "pretense_bai_flights_per_cp",
        "pretense_strike_flights_per_cp",
        "pretense_barcap_flights_per_cp",
        "pretense_ai_aircraft_per_flight",
        "pretense_player_flights_per_type",
        "pretense_ai_cargo_planes_per_side",
        "nevatim_parking_fix",
        "only_player_takeoff",
        "generate_dtc",
        # Removed once the IADS engine became the SAM-emissions owner: it sets
        # each networked SAM's alarm state at runtime, so a global "SAM starts
        # in red alert" toggle just fought the engine. Non-IADS groups now fall
        # to DCS AUTO.
        "perf_red_alert_state",
        # The 2026-06 IADS-engine selector. Skynet is the only engine again;
        # drop the persisted value (the IadsEngine stub only exists so the old
        # enum still unpickles before this pop).
        "iads_engine",
        # Consolidated into the single airbase+roadbase ground-start truck
        # toggles (value already merged above).
        "ground_start_trucks_roadbase",
        "ground_start_ground_power_trucks_roadbase",
        # The SCAR mis-ID budget penalty died with the SOF capture economy
        # (dead code removed 2026-07-01; nothing wrote scar_misid since the
        # armor-hunt plugin was deleted).
        "scar_misid_penalty",
        # Consolidated into the CarrierDeckPolicy enum (value already
        # migrated above).
        "player_flights_sixpack",
        # Tuning knobs folded into constants 2026-09-23 (simplification pass).
        "gps_jamming_default_reach_nm",
        "gps_jamming_miss_radius_m",
        "qra_gci_max_radius_nm",
        "qra_defense_depth_nm",
        "qra_engagement_range_nm",
        "max_carrier_simultaneous_barcaps",
        "max_simultaneous_recovery_tankers",
        "target_recon_extra_threat_search_nmi",
        # Replaced by the DatalinkPolicy choice so a 1988 campaign and a 2027
        # one can both be right (value already migrated above).
        "eplrs_enabled",
        # Replaced by the CloudPresetPack choice, so several community cloud
        # mods are selectable (value already migrated above).
        "use_bandit_clouds",
        # Feature §46 (route-aware fuel-tank planning) was reverted to upstream
        # behavior in the 2026-08-09 auto-planner re-convergence. Nothing fits
        # tanks at plan or generation time any more, so both gates are dead.
        "auto_range_fuel_tanks",
        "fuel_tanks_over_jammers",
        # §89 living battlespace, ABANDONED 2026-09-07 -- all five slices.
        # P4 (the synthesized blue voice net) had already gone on 2026-08-18.
        "living_battlespace_voice_net",
        "living_battlespace_preroll",
        "living_battlespace_preroll_cap",
        "living_battlespace_reactive_red",
        # §72's two phase tiers, REMOVED 2026-08-20: the round-down E-2C and
        # the bow respot are gone, leaving the island street and LSO crew
        # standing for both cycles. Nothing swaps dressing any more.
        "carrier_deck_decorations_aircraft",
        "carrier_deck_decorations_recovery",
        # §49's coastal opt-in, REMOVED 2026-08-21: the vanilla Silkworm
        # battery is a fixed emplacement (hy_launcher and Silkworm_SR are
        # both immobile), so the coastal scoot had nothing left to drive.
        "coastal_missile_relocation",
        # §51 enemy comms jamming, ABANDONED 2026-09-07.
        "enemy_comms_jamming",
        # §70 COMINT, ABANDONED 2026-09-07 -- the collection tiers, the tasking
        # leak, the concealed-site reveal and the audible red net all together.
        "comint_collection",
        "red_comms_net",
        "red_net_max_stations",
        # §57 air-droppable minefields, ABANDONED 2026-09-07. Shelved since
        # 2026-07-30 and never resumed; the plugin, the cross-turn persistence
        # and the auto-planned mining sortie are all gone.
        "air_droppable_minefields",
        "auto_plan_minefields",
        # §104's gate, on PR #1078 only; the runway queue is always on.
        "queue_aware_ground_ops",
    ):
        migrated.pop(obsolete_key, None)

    return migrated


def migrate_legacy_fast_forward(state: dict[str, Any]) -> None:
    """Map pre-#684 fast-forward settings onto the current enums.

    Before #684 fast-forward was three separate fields::

        fast_forward_to_first_contact: bool          # was it enabled
        player_mission_interrupts_sim_at: Optional[StartType]
            # None=Never, COLD=startup, WARM=taxi, RUNWAY=takeoff
        auto_resolve_combat: bool

    #684 replaced them with ``fast_forward_stop_condition`` /
    ``combat_resolution_method``. Translate old saves so the user keeps an
    equivalent setting instead of crashing on load, and normalize the legacy
    "Never"/None sentinel (which has no enum member) to "no fast forward".
    """
    legacy_ff = state.pop("fast_forward_to_first_contact", None)
    legacy_interrupt = state.pop("player_mission_interrupts_sim_at", None)
    legacy_auto = state.pop("auto_resolve_combat", None)

    if "fast_forward_stop_condition" not in state and legacy_ff is not None:
        if not legacy_ff:
            state["fast_forward_stop_condition"] = FastForwardStopCondition.DISABLED
        else:
            interrupt = _resolve_start_type(legacy_interrupt)
            if interrupt is None:
                state["fast_forward_stop_condition"] = (
                    FastForwardStopCondition.FIRST_CONTACT
                )
            else:
                state["fast_forward_stop_condition"] = {
                    StartType.COLD: FastForwardStopCondition.PLAYER_STARTUP,
                    StartType.WARM: FastForwardStopCondition.PLAYER_TAXI,
                    StartType.RUNWAY: FastForwardStopCondition.PLAYER_TAKEOFF,
                }.get(interrupt, FastForwardStopCondition.FIRST_CONTACT)

    if "combat_resolution_method" not in state and legacy_auto is not None:
        state["combat_resolution_method"] = (
            CombatResolutionMethod.RESOLVE
            if legacy_auto
            else CombatResolutionMethod.PAUSE
        )

    # A "none"/"Never"/None value stored directly under the new key has no
    # matching enum member; treat that family as "no fast forward".
    ff = state.get("fast_forward_stop_condition")
    if ff is None and "fast_forward_stop_condition" in state:
        state["fast_forward_stop_condition"] = FastForwardStopCondition.DISABLED
    elif isinstance(ff, str) and ff.strip().lower() in {"none", "never", ""}:
        state["fast_forward_stop_condition"] = FastForwardStopCondition.DISABLED


def _resolve_start_type(value: Any) -> Optional[StartType]:
    """Coerce a serialized legacy value to a StartType member, or None."""
    if isinstance(value, StartType):
        return value
    if isinstance(value, str):
        name = value.rsplit(".", 1)[-1]
        for member in StartType:
            if name == member.name or value == member.value:
                return member
    return None
