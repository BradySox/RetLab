"""Performance: culling, sleep and unit-count trims."""

from dataclasses import dataclass
from typing import TYPE_CHECKING


from ..booleanoption import boolean_option
from ..boundedintoption import bounded_int_option

if TYPE_CHECKING:
    pass
from ..layout import MISSION_GENERATOR_PAGE, PERFORMANCE_SECTION


@dataclass
class PerformanceSettings:
    # Performance
    perf_smoke_gen: bool = boolean_option(
        "Front-line smoke effects",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_smoke_spacing: int = bounded_int_option(
        "Smoke generator spacing (higher means less smoke)",
        enabled_when="perf_smoke_gen",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=1600,
        min=800,
        max=24000,
    )
    perf_artillery: bool = boolean_option(
        "Artillery strikes",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    generate_fire_tasks_for_missile_sites: bool = boolean_option(
        "Generate fire tasks for missile sites",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        detail=(
            "If enabled, missile sites like V2s and Scuds will fire on random targets "
            "at the start of the mission."
        ),
        default=True,
    )
    perf_moving_units: bool = boolean_option(
        "Moving ground units",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    convoys_travel_full_distance: bool = boolean_option(
        "Convoys drive the full distance between control points",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_disable_convoys: bool = boolean_option(
        "Disable land convoys",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_disable_cargo_ships: bool = boolean_option(
        "Disable cargo-ship convoys",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_frontline_units_prefer_roads: bool = boolean_option(
        "Front line troops prefer roads",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_frontline_units_max_supply: int = bounded_int_option(
        "Maximum ground units deployed per frontline by faction",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=60,
        min=10,
        max=300,
        causes_expensive_game_update=True,
    )
    perf_infantry: bool = boolean_option(
        "Generate infantry squads alongside vehicles",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_destroyed_units: bool = boolean_option(
        "Generate carcasses for units destroyed in previous turns",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_disable_untasked_blufor_aircraft: bool = boolean_option(
        "Disable untasked OWNFOR aircraft at airfields",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_disable_untasked_opfor_aircraft: bool = boolean_option(
        "Disable untasked OPFOR aircraft at airfields",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    # Performance culling
    perf_ground_ai_sleep: bool = boolean_option(
        "Distant ground AI sleeps until aircraft approach",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
        detail=(
            "The graduated alternative to culling: rear-area garrison vehicle groups "
            "keep existing (visible, strikeable, threat rings stay honest, kills "
            "record normally) but their AI is switched off at mission "
            "start and woken only while an aircraft -- either side's -- is within the "
            "wake radius, cutting the sim cost of hundreds of thinking ground units. "
            "Air defenses, the front line, convoys and every scripted mover are never "
            "touched. Composes with culling: sleep what you keep, cull only what you "
            "never want to exist. Runtime lives in the 'Ground AI sleep' Lua plugin "
            "(wake radius and cadence tunable there). OFF by default, and no campaign "
            "turns it on: an AI strike or SEAD flight cannot prosecute a sleeping "
            "group -- its attack task finds no target from the ingress point and the "
            "flight returns with full racks. Measured on Desert Trident turn 1, "
            "2026-08-24: sleep on, 12 of 13 air-to-ground packages fired nothing; the "
            "same turn with it off released 31 Mk-82 and 6 HARM. Only enable it when "
            "nothing is fragged against the ground it puts to sleep."
        ),
    )
    perf_aaa_site_sleep: bool = boolean_option(
        "Also sleep short-range AAA gun sites",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
        enabled_when="perf_ground_ai_sleep",
        detail=(
            "Extends the sleep to anti-aircraft gun sites, which is where the sim "
            "cost of an AAA-doctrine campaign actually lives -- a Vietnam laydown can "
            "field several hundred guns, many times any other campaign. Only guns "
            "whose detection range is well inside the wake radius are eligible, so a "
            "site is always switched back on long before anything reaches the edge of "
            "its own sensor envelope: what it contributes to the IADS picture, and "
            "when it opens fire, are unchanged. Search and track radars, dedicated "
            "early-warning sites, longer-sighted guns such as the Gepard, and every "
            "SAM or point defense Skynet actively drives are never touched. A sleeping "
            "gun site also stops radiating, so an anti-radiation shooter has nothing "
            "to home on and the SEAD half of a package goes home loaded. Turn this on "
            "only if a gun-heavy mission is stuttering and nothing is fragged at those "
            "guns; leave it off otherwise."
        ),
    )
    perf_culling: bool = boolean_option(
        "Culling of distant units enabled",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
    )
    perf_culling_distance: int = bounded_int_option(
        "Culling distance (km)",
        enabled_when="perf_culling",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=100,
        min=10,
        max=10000,
        causes_expensive_game_update=True,
    )
    perf_do_not_cull_threatening_iads: bool = boolean_option(
        "Do not cull threatening IADS",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
    )
    perf_do_not_cull_carrier: bool = boolean_option(
        "Do not cull carrier's surroundings",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=True,
        causes_expensive_game_update=True,
    )
    perf_ai_despawn_airstarted: bool = boolean_option(
        "Despawn airstarted AI over base on RTB",
        page=MISSION_GENERATOR_PAGE,
        section=PERFORMANCE_SECTION,
        default=False,
        detail=(
            "If enabled, AI flights will de-spawn over their base "
            "if the start type was manually changed to In Flight."
        ),
    )
