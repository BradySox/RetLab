"""Campaign settings: the ``Settings`` dataclass and its save compatibility.

Fields live in ``fields/`` (one mixin per storage page), the dialog layout in
``layout.py``, the enums in ``enums.py`` and old-state rewrites in ``migration.py``.
"""

from collections.abc import Iterable, Iterator
from dataclasses import MISSING, Field, dataclass, field, fields
from datetime import timedelta
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING

from .boundedfloatoption import BoundedFloatOption
from .boundedintoption import BoundedIntOption
from .enums import SERIALIZABLE_ENUM_TYPES_BY_NAME
from .fields.campaignmanagement import CampaignManagementSettings
from .fields.difficulty import DifficultySettings
from .fields.doctrine import DoctrineSettings
from .fields.missiongeneration import MissionGenerationSettings
from .fields.missiongenerator import MissionGeneratorSettings
from .fields.performance import PerformanceSettings
from .fields.vietnamops import VietnamOpsSettings
from .layout import (
    CAMPAIGN_PRESEED_KEY,
    FIELD_LAYOUT,
    HIDDEN_FIELDS,
    _ADVANCED_NON_NUMERIC_FIELDS,
    _ALWAYS_BASIC_FIELDS,
    _PRESET_DRIVEN_FIELDS,
)
from .migration import migrate_legacy_fast_forward, migrate_legacy_settings
from .minutesoption import MinutesOption
from .optiondescription import OptionDescription, SETTING_DESCRIPTION_KEY
from ..ato.starttype import StartType

# Re-exported: callers import these from here, and old saves pickled the enums
# under this module's name, so every enum class must stay reachable here.
from .enums import (
    AiRadioBehavior,
    AutoAtoBehavior,
    CarrierDeckPolicy,
    CloudPresetPack,
    CombatResolutionMethod,
    DatalinkPolicy,
    DefaultPlayerLaserCode,
    FastForwardStopCondition,
    IadsEngine,
    NightMissions,
    TargetIntelPrecision,
)
from .layout import (
    CAMPAIGN_DOCTRINE_PAGE,
    DIFFICULTY_REALISM_PAGE,
    FEATURES_PAGE,
    FEATURE_GATE_FIELDS,
    MISSION_GENERATION_PAGE,
    _FEATURE_GATE_NAMES,
)

if TYPE_CHECKING:
    from ..ato.flighttype import FlightType

__all__ = [
    "Settings",
    "AiRadioBehavior",
    "AutoAtoBehavior",
    "CarrierDeckPolicy",
    "CloudPresetPack",
    "CombatResolutionMethod",
    "DatalinkPolicy",
    "DefaultPlayerLaserCode",
    "FastForwardStopCondition",
    "IadsEngine",
    "NightMissions",
    "TargetIntelPrecision",
    "FIELD_LAYOUT",
    "HIDDEN_FIELDS",
    "CAMPAIGN_DOCTRINE_PAGE",
    "DIFFICULTY_REALISM_PAGE",
    "FEATURES_PAGE",
    "FEATURE_GATE_FIELDS",
    "MISSION_GENERATION_PAGE",
    "_FEATURE_GATE_NAMES",
]


@dataclass
class Settings(
    PerformanceSettings,
    VietnamOpsSettings,
    MissionGenerationSettings,
    MissionGeneratorSettings,
    CampaignManagementSettings,
    DoctrineSettings,
    DifficultySettings,
):
    version: Optional[str] = None

    # Cheating. Not using auto settings because the same page also has buttons which do
    # not alter settings.
    enable_frontline_cheats: bool = False
    enable_base_capture_cheat: bool = False
    enable_transfer_cheat: bool = False
    enable_runway_state_cheat: bool = False
    enable_air_wing_adjustments: bool = False
    enable_enemy_buy_sell: bool = False

    # Lua plugins system
    plugins: Dict[str, bool] = field(default_factory=dict)

    #: §93 target families -> RegionPriority value. Carries no option metadata on
    #: purpose: the auto settings dialog renders declared options, and this one is
    #: owned by its own window. Absent family = NORMAL, so old saves need no
    #: migration.
    blue_target_family_priorities: Dict[str, str] = field(default_factory=dict)

    def start_type_for(self, flight_type: "FlightType", has_players: bool) -> StartType:
        """The start type a newly planned flight of this kind should default to.

        The single source of this decision. It is applied from the auto-planner
        (PackageBuilder.plan_flight) and from both places the UI recomputes a
        default (QFlightCreator and QFlightStartType), so a task with its own
        start type behaves the same however the flight came to exist.

        Callers must still let a base that dictates its own start type win --
        carriers and off-map spawns -- via
        ControlPoint.required_aircraft_start_type.
        """
        from ..ato.flighttype import FlightType

        if flight_type is FlightType.CSAR:
            # A downed pilot is on a timer, so the rescue is usually worth
            # launching sooner than the rest of the ATO. Overrides both defaults
            # below, players included: the setting exists precisely so CSAR does
            # not have to inherit them.
            return self.csar_start_type
        if has_players:
            return self.default_start_type_client
        return self.default_start_type

    @staticmethod
    def plugin_settings_key(identifier: str) -> str:
        return f"{identifier}"

    def initialize_plugin_option(self, identifier: str, default_value: Any) -> None:
        try:
            self.plugin_option(identifier)
        except KeyError:
            self.set_plugin_option(identifier, default_value)

    def plugin_option(self, identifier: str) -> Any:
        return self.plugins[self.plugin_settings_key(identifier)]

    def set_plugin_option(self, identifier: str, value: Any) -> None:
        self.plugins[self.plugin_settings_key(identifier)] = value

    def __setstate__(self, state: dict[str, Any]) -> None:
        # __setstate__ is called with the dict of the object being unpickled. We
        # can provide save compatibility for new settings options (which
        # normally would not be present in the unpickled object) by creating a
        # new settings object, updating it with the unpickled state, and
        # updating our dict with that.
        migrated_state = migrate_legacy_settings(self.deserialize_state_dict(state))
        new_state = Settings().__dict__
        new_state.update(migrated_state)
        self.__dict__.update(new_state)

        # Drop retired plugin option keys so dead configuration does not persist
        # across a load/save cycle. The obsolete Anubis "herculescargo" plugin and
        # its option keys were removed in favor of the official C-130J-30. The old
        # generic EW/Jammer Script ("ewrj") was retired in favor of the C-130J
        # JAMMING flight + c130j mission-systems plugin. The "dismounts" and "ewrs"
        # plugins were retired during the MIST -> MOOSE framework consolidation:
        # dismounts was a default-off, FPS-heavy MIST-only plugin with no MOOSE
        # successor, and ewrs is superseded by the MOOSE Ops.INTEL-based "bigeye"
        # EWR (see docs/dev/design/retlab-dismounts-decision.md and
        # retlab-ewrs-retirement-decision.md). The "flightcontrol" MOOSE
        # FLIGHTCONTROL ATC plugin was retired as a half-baked feature. The "arty"
        # (CG ArtySpotter) and "artymbot" (Mbot Call-Artillery) player fire-support
        # scripts were retired as unused: both had been silently dropped from the
        # active plugin list and their directories are now removed. The "tars"
        # (MOOSE Ops.TARS) and "airecon" plugins were retired on 2026-08-05 when the
        # two split recon implementations were replaced by the single "recon" plugin
        # (§12); that successor was itself removed on 2026-08-20, once the reveal
        # rework left its captures with no consumer. The "deckdecor" plugin went the
        # same day: it existed only to swap §72's launch- and recovery-phase deck
        # dressing, and both tiers were cut. The "minefields" plugin went on
        # 2026-09-07 with §57, abandoned rather than resumed; "aisleep" went on
        # 2026-09-23 with §59. A save made before
        # each of those still carries the keys.
        for plugin_key in [
            key
            for key in self.plugins
            if key == "herculescargo"
            or key.startswith("herculescargo.")
            or key == "tars"
            or key.startswith("tars.")
            or key == "airecon"
            or key.startswith("airecon.")
            or key == "recon"
            or key.startswith("recon.")
            or key == "ewrj"
            or key.startswith("ewrj.")
            or key == "dismounts"
            or key.startswith("dismounts.")
            or key == "ewrs"
            or key.startswith("ewrs.")
            or key == "flightcontrol"
            or key.startswith("flightcontrol.")
            or key == "arty"
            or key.startswith("arty.")
            or key == "artymbot"
            or key.startswith("artymbot.")
            or key == "deckdecor"
            or key.startswith("deckdecor.")
            or key == "minefields"
            or key.startswith("minefields.")
            or key == "commsjam"
            or key.startswith("commsjam.")
            or key == "rednet"
            or key.startswith("rednet.")
            or key == "reactivered"
            or key.startswith("reactivered.")
            or key == "aisleep"
            or key.startswith("aisleep.")
        ]:
            del self.plugins[plugin_key]

        from game.plugins import LuaPluginManager

        LuaPluginManager().load_settings(self)

    @staticmethod
    def deserialize_state_dict(state: dict[str, Any]) -> dict[str, Any]:
        # restore Enum & timedelta types
        s = Settings()
        migrate_legacy_fast_forward(state)
        for key, value in list(state.items()):
            default = s.__dict__.get(key)
            if isinstance(default, Enum):
                # Restore the stored member, falling back to the field default
                # for any value that no longer resolves to a member of this
                # field's enum -- a stale/renamed choice, or a legacy non-enum
                # value such as None or a bool. Otherwise the bad value crashes
                # the load and later the settings UI via text_for_value.
                restored = Settings._restore_enum(value, type(default))
                state[key] = restored if restored is not None else default
            elif isinstance(default, timedelta) and isinstance(value, int):
                state[key] = timedelta(minutes=value)
            elif isinstance(value, dict):
                state[key] = s.obj_hook(value)
        return state

    @staticmethod
    def _restore_enum(value: Any, enum_cls: type[Enum]) -> Optional[Enum]:
        """Resolve a serialized value to a member of enum_cls, or None if it no
        longer maps to one (stale, renamed, or a legacy non-enum value).

        Parsing goes through the safe ``_deserialize_enum`` registry (no
        ``eval``), so a crafted save cannot execute code here -- see
        ``test_object_hook_rejects_untrusted_enum_payloads``. Returning None on
        any unresolved value lets the caller fall back to the field default
        instead of crashing the load (upstream #755 robustness)."""
        if isinstance(value, enum_cls):
            return value
        # Accept the JSON form {"Enum": "EnumName.MEMBER"} and the bare
        # "EnumName.MEMBER" string; ignore anything that does not resolve to a
        # member of this field's enum.
        expr: Optional[str] = None
        if isinstance(value, dict):
            inner = value.get("Enum")
            if isinstance(inner, str):
                expr = inner
        elif isinstance(value, str):
            expr = value
        if expr is not None:
            try:
                restored = Settings._deserialize_enum(expr, expected_type=enum_cls)
            except ValueError:
                return None
            if isinstance(restored, enum_cls):
                return restored
        return None

    @classmethod
    def _field_description(cls, settings_field: Field[Any]) -> OptionDescription:
        return settings_field.metadata[SETTING_DESCRIPTION_KEY]

    @classmethod
    def _effective_layout(
        cls, name: str, description: OptionDescription
    ) -> tuple[str, str]:
        # FIELD_LAYOUT is the curated UI grouping; fall back to the field's own
        # page=/section= metadata for anything not listed there.
        return FIELD_LAYOUT.get(name, (description.page, description.section))

    @classmethod
    def is_advanced(cls, name: str, description: OptionDescription) -> bool:
        """Should the dialog fold this option behind the "advanced" disclosure?

        See the basic-vs-advanced note above ``_PRESET_DRIVEN_FIELDS``: numeric
        knobs are advanced, "whether/which" options are not, with two explicit
        exception lists. An ``advanced=True`` on the declaration always wins.
        """
        if description.advanced:
            return True
        if name in _ADVANCED_NON_NUMERIC_FIELDS:
            return True
        if name in _PRESET_DRIVEN_FIELDS or name in _ALWAYS_BASIC_FIELDS:
            return False
        return isinstance(
            description, (BoundedIntOption, BoundedFloatOption, MinutesOption)
        )

    def is_default(self, name: str) -> bool:
        """Is this field still at its declared default?

        Powers the dialog's "only show what I've changed" filter. Unknown or
        unreadable fields report True (i.e. "nothing to see") so the filter can
        never hide a field by erroring on it.
        """
        for settings_field in fields(self):
            if settings_field.name != name:
                continue
            default = settings_field.default
            if default is MISSING:
                return True
            try:
                return bool(self.__dict__.get(name) == default)
            except Exception:  # pragma: no cover - exotic __eq__
                return True
        return True

    def campaign_preseeded_fields(self) -> frozenset[str]:
        """Field names the selected campaign pre-seeded in its ``settings:`` block.

        Recorded by the New Game wizard when it layers a campaign's settings over
        the defaults, and carried in the save so the in-campaign dialog can badge
        them too. Stored as a plain ``__dict__`` key rather than a dataclass field
        precisely so it is not itself a setting: ``_user_fields`` only yields
        fields carrying an option descriptor, so this never renders.
        """
        stored = self.__dict__.get(CAMPAIGN_PRESEED_KEY)
        if isinstance(stored, (frozenset, set, list, tuple)):
            return frozenset(str(name) for name in stored)
        return frozenset()

    def record_campaign_preseeds(self, names: Iterable[str]) -> None:
        """Remember which fields a campaign set (see campaign_preseeded_fields)."""
        known = {f.name for f in fields(self)}
        self.__dict__[CAMPAIGN_PRESEED_KEY] = frozenset(
            name for name in names if name in known
        )

    @classmethod
    def _ordered_user_fields(cls) -> list[Field[Any]]:
        # Walk user fields in FIELD_LAYOUT order first (the curated layout), then
        # append any field missing from the table in declaration order so a
        # field is never dropped from the UI.
        by_name = {f.name: f for f in cls._user_fields()}
        ordered: list[Field[Any]] = []
        seen: set[str] = set()
        for name in FIELD_LAYOUT:
            settings_field = by_name.get(name)
            if settings_field is not None:
                ordered.append(settings_field)
                seen.add(name)
        for settings_field in cls._user_fields():
            if settings_field.name not in seen:
                ordered.append(settings_field)
                seen.add(settings_field.name)
        return ordered

    @classmethod
    def pages(cls) -> Iterator[str]:
        seen: set[str] = set()
        for settings_field in cls._ordered_user_fields():
            description = cls._field_description(settings_field)
            page, _section = cls._effective_layout(settings_field.name, description)
            if page not in seen:
                yield page
                seen.add(page)

    @classmethod
    def sections(cls, page: str) -> Iterator[str]:
        seen: set[str] = set()
        for settings_field in cls._ordered_user_fields():
            description = cls._field_description(settings_field)
            field_page, section = cls._effective_layout(
                settings_field.name, description
            )
            if field_page == page and section not in seen:
                yield section
                seen.add(section)

    @classmethod
    def fields(cls, page: str, section: str) -> Iterator[tuple[str, OptionDescription]]:
        for settings_field in cls._ordered_user_fields():
            description = cls._field_description(settings_field)
            field_page, field_section = cls._effective_layout(
                settings_field.name, description
            )
            if field_page == page and field_section == section:
                yield settings_field.name, description

    @classmethod
    def _user_fields(cls) -> Iterator[Field[Any]]:
        for settings_field in fields(cls):
            if settings_field.name in HIDDEN_FIELDS:
                continue
            if SETTING_DESCRIPTION_KEY in settings_field.metadata:
                yield settings_field

    @staticmethod
    def default_json(obj: Any) -> Any:
        # Known types that don't like being serialized,
        # so we introduce our own implementation...
        if isinstance(obj, Enum):
            return {"Enum": str(obj)}
        elif isinstance(obj, timedelta):
            return {"timedelta": round(obj.seconds / 60)}
        elif isinstance(obj, (set, frozenset)):
            # The campaign-preseed record is a frozenset; sorted so a saved
            # settings file is stable between runs.
            return sorted(str(item) for item in obj)
        # Never return obj unchanged: json takes a `default` that hands back its
        # own argument as a container of itself and dies with "Circular reference
        # detected", which says nothing about what actually failed. Raising the
        # TypeError json expects names the offending type instead.
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    @staticmethod
    def obj_hook(obj: Any) -> Any:
        if (value := obj.get("Enum")) is not None:
            return Settings._deserialize_enum(value)
        elif (value := obj.get("timedelta")) is not None:
            return timedelta(minutes=value)
        else:
            return obj

    @staticmethod
    def _deserialize_enum(value: Any, expected_type: type[Enum] | None = None) -> Enum:
        if not isinstance(value, str):
            raise ValueError("Serialized enum value must be a string")

        try:
            type_name, member_name = value.split(".", maxsplit=1)
        except ValueError as ex:
            raise ValueError(f"Invalid serialized enum value: {value!r}") from ex

        enum_type = SERIALIZABLE_ENUM_TYPES_BY_NAME.get(type_name)
        if enum_type is None or (
            expected_type is not None and enum_type is not expected_type
        ):
            raise ValueError(f"Unsupported serialized enum type: {type_name!r}")

        try:
            return enum_type[member_name]
        except KeyError as ex:
            raise ValueError(
                f"Unknown {enum_type.__name__} member: {member_name!r}"
            ) from ex
