"""The enums Settings fields hold, and the table that (de)serializes them."""

from enum import Enum, unique
from typing import TYPE_CHECKING

from dcs.forcedoptions import ForcedOptions

from ..ato.starttype import StartType
from ..ground_forces.combat_stance import CombatStance

if TYPE_CHECKING:
    pass


Views = ForcedOptions.Views


@unique
class AutoAtoBehavior(Enum):
    Disabled = "Disabled"
    Never = "Never assign player pilots"
    Default = "No preference"
    Prefer = "Prefer player pilots"


@unique
class CloudPresetPack(Enum):
    """A community cloud-preset weather mod whose presets the mission generator may
    use. Only one can be active at a time: the packs share the same preset keys
    (Preset35+) but map them to different clouds, so they must not be mixed."""

    NONE = "None (stock DCS presets)"
    BANDIT = "Bandit's Cloud Presets"
    WEATHER2 = "Weather 2.0 (Bandit)"
    ATMOSX = "ATMOS-X"


@unique
class NightMissions(Enum):
    DayAndNight = "nightmissions_nightandday"
    OnlyDay = "nightmissions_onlyday"
    OnlyNight = "nightmissions_onlynight"


@unique
class FastForwardStopCondition(Enum):
    DISABLED = "Fast forward disabled"
    FIRST_CONTACT = "First contact"
    PLAYER_TAKEOFF = "Player takeoff time"
    PLAYER_TAXI = "Player taxi time"
    PLAYER_STARTUP = "Player startup time"
    PLAYER_AT_IP = "Player at IP"
    MANUAL = "Manual fast forward control"

    @property
    def player_preflight_phase(self) -> int | None:
        """Ordering of the player pre-flight stop conditions, earliest first.

        A player flight should halt the sim at the *earliest* pre-flight state it
        actually occupies whose phase is at or after the configured stop condition.
        This matters when the flight's start type skips earlier phases: a WARM
        (hot-ramp) flight enters at Taxi, so under the PLAYER_STARTUP condition it
        must halt at Taxi rather than fast-forwarding into the air (which would make
        its spawn_type IN_FLIGHT and spawn the player airborne).

        Returns None for conditions that are not player pre-flight phases.
        """
        return {
            FastForwardStopCondition.PLAYER_STARTUP: 0,
            FastForwardStopCondition.PLAYER_TAXI: 1,
            FastForwardStopCondition.PLAYER_TAKEOFF: 2,
        }.get(self)


@unique
class CombatResolutionMethod(Enum):
    PAUSE = "Pause simulation"
    RESOLVE = "Resolve combat"
    SKIP = "Skip combat"


@unique
class TargetIntelPrecision(Enum):
    EXACT = "Exact target coordinates"
    APPROXIMATE = "Approximate target area"


@unique
class AiRadioBehavior(Enum):
    FULL = "Normal callouts"
    LIMITED = "Suppress contact reports"
    SILENT = "Radio silence"


@unique
class DatalinkPolicy(Enum):
    """Who gets the DCS ``EPLRS`` task -- the group's datalink-enable switch.

    DCS reused the EPLRS name generically: the task is what makes a group take
    part in datalink at all, whether that is Link 16 on a Hornet, SADL on an
    A-10C, or a ground unit's own net. Without it the jet's terminal never comes
    up, which reads in the cockpit as an empty SA page.

    The old boolean could not be right for a fork that ships both 1988 and 2027
    campaigns: on gave Desert Storm Hornets Link 16 a decade early, off cost the
    modern campaigns their datalink entirely (flown 2026-08-16 -- 1 of 23 blue
    plane groups carried the task, against 16 of 18 in a hand-built modern
    mission). ERA_CORRECT reads each airframe's ``datalink_introduced`` year, the
    same way the payload-editor properties are gated (§24).
    """

    ERA_CORRECT = "Era-correct (recommended)"
    ALWAYS = "Always on"
    NEVER = "Never"


@unique
class CarrierDeckPolicy(Enum):
    """How the carrier six-pack (the first-filled deck spots) is used.

    DCS offers no mission-level control over deck parking beyond spawn timing:
    groups spawning at mission start fill the six-pack first, and anything that
    spawns even one second later is placed elsewhere on deck (the
    dcs_liberation#1309 placement trick the generator already uses to keep AI
    off the six-pack). The six-pack sits in the taxi lane to the bow catapults,
    so a slow-starting player parked there jams every AI jet taxiing to launch.
    """

    SIXPACK_FIRST = "Players spawn on the six-pack"
    LAST_RESORT = "Six-pack is overflow parking (last resort)"


@unique
class DefaultPlayerLaserCode(Enum):
    DEFAULT_1688 = "Default (1688)"
    ALLOCATE_OWN = "Allocate own (unique per flight)"


class IadsEngine(Enum):
    """Save-compat stub. The 2026-06 engine selector persisted this enum in
    campaign saves; the enum is kept *solely* so those saves still unpickle, and
    ``_migrate_legacy_settings`` then drops the orphan value. Skynet is the only
    engine again (2026-09-12) and no setting reads this."""

    SKYNET = "skynet"
    MANTIS = "mantis"


SERIALIZABLE_ENUM_TYPES = (
    AutoAtoBehavior,
    CloudPresetPack,
    NightMissions,
    FastForwardStopCondition,
    CombatResolutionMethod,
    TargetIntelPrecision,
    AiRadioBehavior,
    CarrierDeckPolicy,
    DatalinkPolicy,
    DefaultPlayerLaserCode,
    IadsEngine,
    CombatStance,
    StartType,
    Views,
)
SERIALIZABLE_ENUM_TYPES_BY_NAME = {
    enum_type.__name__: enum_type for enum_type in SERIALIZABLE_ENUM_TYPES
}
