"""Difficulty: AI skill, economy and mission restrictions."""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING


from ..booleanoption import boolean_option
from ..boundedfloatoption import bounded_float_option
from ..choicesoption import choices_option
from ..skilloption import skill_option

if TYPE_CHECKING:
    pass
from ..enums import NightMissions, Views
from ..layout import (
    AI_DIFFICULTY_SECTION,
    DIFFICULTY_PAGE,
    MISSION_DIFFICULTY_SECTION,
    MISSION_RESTRICTIONS_SECTION,
)


@dataclass
class DifficultySettings:
    # Difficulty settings
    # AI Difficulty
    player_skill: str = skill_option(
        "Player coalition skill",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        default="High",
    )
    enemy_skill: str = skill_option(
        "Enemy coalition skill",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        default="High",
    )
    enemy_vehicle_skill: str = skill_option(
        "Enemy AA and vehicles skill",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        default="High",
    )
    player_income_multiplier: float = bounded_float_option(
        "Player income multiplier",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        min=0,
        max=5,
        divisor=10,
        default=1.0,
    )
    enemy_income_multiplier: float = bounded_float_option(
        "Enemy income multiplier",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        min=0,
        max=5,
        divisor=10,
        default=1.0,
    )
    invulnerable_player_pilots: bool = boolean_option(
        "Player pilots cannot be killed",
        page=DIFFICULTY_PAGE,
        section=AI_DIFFICULTY_SECTION,
        detail=(
            "Aircraft are vulnerable, but the player's pilot will be returned to the "
            "squadron at the end of the mission."
        ),
        default=True,
    )
    # Mission Difficulty
    manpads: bool = boolean_option(
        "MANPADS on front lines",
        page=DIFFICULTY_PAGE,
        section=MISSION_DIFFICULTY_SECTION,
        default=True,
    )
    night_day_missions: NightMissions = choices_option(
        "Mission time of day",
        page=DIFFICULTY_PAGE,
        section=MISSION_DIFFICULTY_SECTION,
        choices={
            "Generate night and day missions": NightMissions.DayAndNight,
            "Only generate day missions": NightMissions.OnlyDay,
            "Only generate night missions": NightMissions.OnlyNight,
        },
        default=NightMissions.DayAndNight,
    )
    # Mission Restrictions
    labels: str = choices_option(
        "In-game labels",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices=["Full", "Abbreviated", "Dot Only", "Neutral Dot", "Off"],
        default="Full",
    )
    map_coalition_visibility: Views = choices_option(
        "Map visibility options",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices={
            "All": Views.All,
            "Fog of war": Views.Allies,
            "Allies only": Views.OnlyAllies,
            "Own aircraft only": Views.MyAircraft,
            "Map only": Views.OnlyMap,
        },
        default=Views.All,
    )
    external_views_allowed: bool = boolean_option(
        "Allow external views",
        DIFFICULTY_PAGE,
        MISSION_RESTRICTIONS_SECTION,
        default=True,
    )
    easy_communication: Optional[bool] = choices_option(
        "Easy communications",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices={"Player preference": None, "Enforced on": True, "Enforced off": False},
        default=None,
    )
    battle_damage_assessment: Optional[bool] = choices_option(
        "Battle damage assessment",
        page=DIFFICULTY_PAGE,
        section=MISSION_RESTRICTIONS_SECTION,
        choices={"Player preference": None, "Enforced on": True, "Enforced off": False},
        default=None,
    )
