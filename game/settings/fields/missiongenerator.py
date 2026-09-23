"""Mission generator: gameplay, kneeboards and RetLab feature toggles."""

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING


from ..booleanoption import boolean_option
from ..boundedintoption import bounded_int_option
from ..choicesoption import choices_option
from ..minutesoption import minutes_option
from ...ato.starttype import StartType

if TYPE_CHECKING:
    pass
from ..enums import (
    AiRadioBehavior,
    CarrierDeckPolicy,
    CombatResolutionMethod,
    DatalinkPolicy,
    DefaultPlayerLaserCode,
    FastForwardStopCondition,
    TargetIntelPrecision,
)
from ..layout import GAMEPLAY_SECTION, KNEEBOARD_SECTION, MISSION_GENERATOR_PAGE


@dataclass
class MissionGeneratorSettings:
    # Mission Generator
    # Gameplay
    fast_forward_stop_condition: FastForwardStopCondition = choices_option(
        "Fast forward until",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=FastForwardStopCondition.PLAYER_STARTUP,
        choices={
            "No fast forward": FastForwardStopCondition.DISABLED,
            "Player startup time": FastForwardStopCondition.PLAYER_STARTUP,
            "Player taxi time": FastForwardStopCondition.PLAYER_TAXI,
            "Player takeoff time": FastForwardStopCondition.PLAYER_TAKEOFF,
            "Player at IP": FastForwardStopCondition.PLAYER_AT_IP,
            "First contact": FastForwardStopCondition.FIRST_CONTACT,
            "Manual": FastForwardStopCondition.MANUAL,
        },
        detail=(
            "Determines when fast forwarding stops: "
            "No fast forward: disables fast forward. "
            "Player startup time: fast forward until player startup time. "
            "Player taxi time: fast forward until player taxi time. "
            "Player takeoff time: fast forward until player takeoff time. "
            "Player at IP: fast forward until a player flight reaches its IP, where "
            "it spawns in the air; AI-only combat on the way resolves without stopping. "
            "First contact: fast forward until first contact between blue and red units. "
            "Manual: manually control fast forward. Show manual controls with --show-sim-speed-controls."
        ),
    )
    combat_resolution_method: CombatResolutionMethod = choices_option(
        "Combat encountered during fast-forward",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=CombatResolutionMethod.PAUSE,
        choices={
            "Pause": CombatResolutionMethod.PAUSE,
            "Resolve (WIP)": CombatResolutionMethod.RESOLVE,
            "Skip": CombatResolutionMethod.SKIP,
        },
        detail=(
            "Pause stops fast-forward so the combat can be flown. Resolve uses the "
            "rudimentary campaign simulation and can cause heavy losses. Skip ignores "
            "the combat. This may stop fast-forward before the selected stop condition."
        ),
    )
    supercarrier: bool = boolean_option(
        "Use supercarrier module",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
    )
    supercarrier_deck_crew: bool = boolean_option(
        "Use supercarrier deck-crew",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        enabled_when="supercarrier",
        default=True,
    )
    carrier_deck_decorations: bool = boolean_option(
        "Carrier deck decorations (parked gear & crew)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Dress each Nimitz-class carrier deck with static deck equipment "
            "and crew linked to the moving ship: tow tractors, a P-25 crash "
            "truck, a forklift and deck hands along the island, plus the LSO "
            "platform crew aft. Layouts are curated from installed DCS "
            "campaigns and keep every parking spawn spot and all four "
            "catapults usable; the arrangement rotates each turn."
        ),
    )
    generate_portable_tacans: bool = boolean_option(
        "Place portable TACAN beacons at blue airfields",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Automatically places a portable TACAN beacon at blue-captured "
            "airfields that don't already have a built-in TACAN from the "
            "terrain data. An unused X-band channel is assigned to each."
        ),
    )
    generate_marks: bool = boolean_option(
        "Put objective markers on the map",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )
    target_intel_precision: TargetIntelPrecision = choices_option(
        "Player target location precision",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        choices={
            "Exact target coordinates": TargetIntelPrecision.EXACT,
            "Approximate target area": TargetIntelPrecision.APPROXIMATE,
        },
        default=TargetIntelPrecision.EXACT,
        detail=(
            "Approximate mode offsets player-facing target steerpoints into a nearby "
            "search area, suppresses objective F10 map marks, and removes exact "
            "target coordinates from strike/SEAD kneeboards."
        ),
    )
    datalink_policy: DatalinkPolicy = choices_option(
        "Datalink (EPLRS task)",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={policy.value: policy for policy in DatalinkPolicy},
        default=DatalinkPolicy.ERA_CORRECT,
        detail=(
            "DCS calls the group datalink switch EPLRS whatever the aircraft "
            "actually carries -- Link 16 on a Hornet or Viper, SADL on an A-10C. "
            "Without it the jet's terminal never comes up and the SA page stays "
            "empty. Era-correct gives it only to airframes whose datalink existed "
            "by the campaign date; Always on is the old behavior and is "
            "anachronistic in a Cold War or Gulf War campaign; Never disables "
            "datalink for everyone."
        ),
    )
    generate_dark_kneeboard: bool = boolean_option(
        "Generate dark kneeboard",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Dark kneeboard for night missions. This will likely make the kneeboard on "
            "the pilot leg unreadable."
        ),
    )
    generate_target_recon_kneeboard: bool = boolean_option(
        "Generate target recon kneeboard pages",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Generate target/airfield reconnaissance pages for player flights with "
            "air-to-ground tasks, showing aimpoints, threat rings, and target area "
            "context over satellite imagery. Off by default until the imagery "
            "alignment has had an in-game pass."
        ),
    )
    generate_all_packages_kneeboard: bool = boolean_option(
        "Generate friendly packages kneeboard page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Append page(s) listing every friendly package with its TOT (strike "
            "tasks) or patrol window (CAP, tanker, AWACS), for cross-package "
            "coordination. Off by default: adds a Friendly Packages section to the "
            "Mission Info page plus a package-targets map, which can spill onto "
            "continuation pages on busy theaters."
        ),
    )
    generate_threat_intel_kneeboard: bool = boolean_option(
        "Generate threat intel brief kneeboard page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=True,
        detail=(
            "Append a Threat Intel Brief page: the enemy air-defense laydown "
            "(SAM/EWR system, engagement range, HARM ALIC code, bullseye cue and "
            "live/degraded/dead status), modeled on the per-system threat cards in "
            "professional campaign intelligence briefings. Recon-fog aware — an "
            "undiscovered site shows only its intel-tier band ('Unidentified MERAD') "
            "until you engage it. On by default."
        ),
    )
    enable_package_code_words: bool = boolean_option(
        "Package code words",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=False,
        detail=(
            "Give each package three SRS code words (push / success / abort) and surface "
            "them so a briefing can be built before generation: a package tooltip in the "
            "ATO list and a 'PUSH' tag naming the push word on the join waypoint, plus "
            "the code words "
            "on the kneeboard (the flight's own words in the Mission Info BLUF and the "
            "side-wide table on the Support Info page). Human comms aids only — nothing "
            "scripts off them. Off by default."
        ),
    )
    generate_sitrep_kneeboard: bool = boolean_option(
        "Campaign SITREP band on the briefing page",
        MISSION_GENERATOR_PAGE,
        KNEEBOARD_SECTION,
        default=True,
        detail=(
            "Add a short 'what happened last turn' band to the Mission Info "
            "kneeboard page: both sides' losses (enemy as claimed), bases captured or "
            "lost, and downed pilots recovered. Hidden on turn 1 and after a quiet "
            "turn. On by default."
        ),
    )
    never_delay_player_flights: bool = boolean_option(
        "Spawn player flights immediately (keep planned TOT)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Spawns every player aircraft at mission start, even one whose start "
            "time is more than 10 minutes in. <strong>Your TOT does not change: the "
            "player simply waits on the ground.</strong> A multiplayer option that "
            "keeps every player slot selectable from mission start; a mission with "
            "fewer than two player slots ignores it and spawns the flight at its "
            "planned start time (cold starts at engine start, hot starts at taxi or "
            "takeoff). Should not be used if players have runway or in-air starts."
        ),
    )
    untasked_opfor_client_slots: bool = boolean_option(
        "Convert untasked OPFOR aircraft into client slots",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Warning: Enabling this will significantly reduce the number of "
            "targets available for OCA/Aircraft missions."
        ),
    )
    default_start_type: StartType = choices_option(
        "Default start type for AI aircraft",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in StartType},
        default=StartType.COLD,
        detail=(
            "Warning: Options other than Cold will significantly reduce the number of "
            "targets available for OCA/Aircraft missions, and OCA/Aircraft flights "
            "will not be included in automatically planned OCA packages."
        ),
    )
    default_start_type_client: StartType = choices_option(
        "Default start type for player flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in StartType},
        default=StartType.COLD,
        detail="Default start type for flights containing Player/Client slots.",
    )
    opfor_air_start: bool = boolean_option(
        "Enemy (OPFOR) aircraft start in the air",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail=(
            "When enabled, every AI OPFOR (red) flight spawns airborne regardless of "
            "the AI start type, so the enemy holds the air from mission start and "
            "can't be caught on the ramp. Player and OWNFOR flights are unaffected. "
            "A base that forces a specific start type (e.g. a carrier) still wins."
        ),
    )
    support_air_start: bool = boolean_option(
        "Support aircraft (AWACS/tankers) start in the air",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail=(
            "When enabled, AWACS and tanker flights spawn airborne and on-station "
            "from mission start instead of spending the first several minutes taxiing "
            "and climbing. Applies to both coalitions' AI support flights; "
            "player-crewed flights keep the player start type."
        ),
    )
    csar_start_type: StartType = choices_option(
        "Default start type for CSAR flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in StartType},
        default=StartType.WARM,
        detail=(
            "Start type for combat search and rescue flights, overriding the "
            "default start types for AI aircraft and player flights."
        ),
    )
    csar_hover_extraction: bool = boolean_option(
        "CSAR hover extraction",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Controls how an AI rescue helicopter recovers a downed pilot. "
            "Checked (default): the helicopter holds a low hover over the pickup and "
            "the pilot is extracted by script, as though hoisted. Unchecked: the "
            "helicopter lands and the pilot walks aboard."
        ),
    )
    csar_rescue_ai_pilots: bool = boolean_option(
        "CSAR rescues AI-controlled downed pilots",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "If set, Ops.CSAR will register AI downed pilots in the mission for "
            "player flights, not only player-flown ejections."
        ),
    )
    csar_player_hover_height: int = bounded_int_option(
        "Player hover pickup height (m)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=20,
        min=5,
        max=100,
        detail=(
            "How low a player has to hover over a survivor to winch them up. "
            "Ops.CSAR's rescuehoverheight. Player pickups only."
        ),
    )
    csar_player_hover_distance: int = bounded_int_option(
        "Player hover pickup distance (m)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=10,
        min=5,
        max=200,
        detail=(
            "How close to the survivor a player has to hold that hover. "
            "Ops.CSAR's rescuehoverdistance. Player pickups only."
        ),
    )
    csar_require_open_doors: bool = boolean_option(
        "Require cabin door open",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "If set, a survivor will not climb aboard a player's helicopter until "
            "its cabin door is open, and will not get out again until it is opened. "
            "Player flights only."
        ),
    )
    default_player_laser_code: DefaultPlayerLaserCode = choices_option(
        "Default laser code for Player flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in DefaultPlayerLaserCode},
        default=DefaultPlayerLaserCode.ALLOCATE_OWN,
        detail=(
            "Allocate own gives every newly-created player flight a unique TGP/"
            "weapon laser code. Default (1688) leaves the code unset so bombs "
            "and the cockpit TGP fall back to 1688. Affects newly-created "
            "flights only; existing flights are unchanged."
        ),
    )
    switch_baro_fix: bool = boolean_option(
        "Use AMSL helicopter waypoints over water (DCS workaround)",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=True,  # TODO: set to False or remove this when DCS is fixed?
        detail=(
            "Works around DCS treating over-water AGL altitude as relative to the sea "
            "floor, which can send low-flying helicopters below the surface."
        ),
    )
    ai_radio_behavior: AiRadioBehavior = choices_option(
        "AI wingman radio behavior in player flights",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={behavior.value: behavior for behavior in AiRadioBehavior},
        default=AiRadioBehavior.LIMITED,
        detail=(
            "Controls AI wingmen in flights containing human slots. Normal keeps "
            "standard DCS calls; Suppress contact reports removes target-detection "
            "spam; Radio silence suppresses all AI calls. AWACS flights are unaffected."
        ),
    )
    use_ai_combat_landing: bool = boolean_option(
        "Use AI combat landing waypoint task",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=False,
        detail="Turns the combat landing flag on in the landing waypoint task.",
    )
    # Mission specific
    desired_player_mission_duration: timedelta = minutes_option(
        "Desired mission duration",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=timedelta(minutes=60),
        min=30,
        max=150,
    )
    max_frontline_width: int = bounded_int_option(
        "Maximum frontline width (km)",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=80,
        min=1,
        max=100,
    )
    game_masters_count: int = bounded_int_option(
        "Game Master slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=1,
        min=0,
        max=10,
        detail=(
            "The number of game master slots to generate for each side. "
            "Game masters can see, control & direct all units in the mission."
        ),
    )
    tactical_commander_count: int = bounded_int_option(
        "Tactical Commander slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=3,
        min=0,
        max=10,
        detail=(
            "The number of tactical commander slots to generate for each side. "
            "Tactical commanders can control & direct friendly units."
        ),
    )
    jtac_count: int = bounded_int_option(
        "JTAC slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=3,
        min=0,
        max=10,
        detail=(
            "The number of JTAC controller slots to generate for each side. "
            "JTAC operators can only control friendly units."
        ),
    )
    observer_count: int = bounded_int_option(
        "Observer slots per coalition",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        default=0,
        min=0,
        max=10,
        detail=(
            "The number of observer slots to generate for each side. "
            'Use this to allow spectators when disabling "Allow external views".'
        ),
    )
    ground_start_ai_planes: bool = boolean_option(
        "AI fixed-wing aircraft can use roadbases / bases with only ground spawns",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "If enabled, AI can use roadbases or airbases which only have ground spawns. "
            "AI will always air-start from these bases (due to DCS limitation)."
        ),
    )
    ground_start_scenery_remove_triggers: bool = boolean_option(
        "Generate SCENERY REMOVE OBJECTS ZONE triggers at roadbase first waypoints",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Can be used to remove lightposts and other obstacles from roadbase runways. "
            "Might not work in DCS multiplayer."
        ),
    )
    ground_start_trucks: bool = boolean_option(
        "Spawn supply trucks at ground starts instead of FARP statics",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Applies to both airbases and roadbases. "
            "Might have a negative performance impact."
        ),
    )
    ground_start_ground_power_trucks: bool = boolean_option(
        "Spawn ground power trucks at ground starts",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Applies to both airbases and roadbases. Needed to cold-start some "
            "aircraft types. Might have a performance impact."
        ),
    )
    ground_start_airbase_statics_farps_remove: bool = boolean_option(
        "Remove ground spawn statics, including invisible FARPs, at airbases",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "Ammo and fuel statics and invisible FARPs should be unnecessary when creating "
            "additional spawns for players at airbases. This setting will disable them and "
            "potentially grant a marginal performance benefit."
        ),
    )
    ai_unlimited_fuel: bool = boolean_option(
        "AI flights have unlimited fuel",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=(
            "AI aircraft have unlimited fuel applied at start, removed at join/racetrack start,"
            " and reapplied at split/racetrack end for applicable flights."
        ),
    )
    dynamic_slots: bool = boolean_option(
        "Enable dynamic player slots",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=False,
        detail=(
            "Enables dynamic slots. Please note that losses from dynamic slots won't be registered."
        ),
    )
    dynamic_slots_hot: bool = boolean_option(
        "Allow hot starts in dynamic slots",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        enabled_when="dynamic_slots",
        default=True,
        detail=("Enables hot start for dynamic slots."),
    )
    dynamic_slots_templates: bool = boolean_option(
        "Dynamic slots inherit a player flight's route and radios",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        enabled_when="dynamic_slots",
        default=True,
        detail=(
            "A dynamic-slot jet spawns blank: stock loadout, no route, no radio "
            "presets. With this on, each base's dynamic spawns of a type are built "
            "from a player flight of that type already fragged there (DCS's "
            "Dyn.SPAWN Template), so the jet carries that flight's waypoints, comm "
            "card, loadout and properties. Types with no player flight at the base "
            "still spawn blank. Times on target are the template's and go stale."
        ),
    )
    dynamic_cargo: bool = boolean_option(
        "Enable DCS dynamic cargo",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
        detail=("Enables dynamic cargo for airfields, ships, FARPs & warehouses."),
    )
    carrier_deck_policy: CarrierDeckPolicy = choices_option(
        "Carrier six-pack usage",
        page=MISSION_GENERATOR_PAGE,
        section=GAMEPLAY_SECTION,
        choices={v.value: v for v in CarrierDeckPolicy},
        default=CarrierDeckPolicy.LAST_RESORT,
        detail=(
            "The six-pack (the first-filled carrier deck spots) sits in the taxi "
            "lane to the bow catapults, so AI taxiing to launch jam against a "
            "slow-starting player parked there. Last resort spawns player flights "
            "one second after mission start, which makes DCS park them clear of "
            "the six-pack; the six-pack then only fills once the rest of the deck "
            "is full. AI carrier flights always spawn clear of the six-pack."
        ),
    )
    use_auto_fog: bool = boolean_option(
        "Use DCS' automatic fog setting",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        default=True,
    )
    base_battle_damage: bool = boolean_option(
        "Battle damage at depleted bases (fires, smoke, wreckage)",
        MISSION_GENERATOR_PAGE,
        GAMEPLAY_SECTION,
        detail=(
            "A base's ground strength drives how battered it looks: a besieged, ground-down "
            "field gets scattered fires, smoke and destroyed-building wreckage so it reads as "
            "under siege, while staying fully operational (cosmetic only -- the runway is "
            "untouched). Costs some FPS; turn off if a heavily-hit base impacts performance."
        ),
        default=True,
    )
