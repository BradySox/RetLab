"""Hidden template groups MOOSE's CTLD copies troops and crate vehicles from.

Ops.CTLD spawns cargo by cloning late-activated groups placed in the mission, so the
generator writes one per squad and per crate vehicle type, per side, whenever a flight
carries CTLD logistics. They never activate. The squads mirror the infantry mix the old
CTLD script built (docs/dev/design/retlab-mist-removal-notes.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import logging

from dcs import Mission
from dcs.country import Country
from dcs.unitgroup import VehicleGroup
from dcs.vehicles import vehicle_map

from game.theater.player import Player

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.missiondata import MissionData

# Infantry types by role, per side (the old CTLD script's own picks).
_RIFLE = {Player.BLUE: "Soldier M4 GRG", Player.RED: "Infantry AK"}
_MG = {Player.BLUE: "Soldier M249", Player.RED: "Paratrooper AKS-74"}
_AT = {Player.BLUE: "Paratrooper RPG-16", Player.RED: "Paratrooper RPG-16"}
_AA = {Player.BLUE: "Soldier stinger", Player.RED: "SA-18 Igla manpad"}

# Retribution's own squads by size: (rifles, MGs, AT, AA, JTAC). The 24 carries a JTAC.
_RETRIBUTION_SQUADS = {
    2: (2, 0, 0, 0, 0),
    4: (4, 0, 0, 0, 0),
    6: (4, 1, 1, 0, 0),
    10: (5, 2, 2, 1, 0),
    12: (6, 2, 2, 2, 0),
    24: (12, 4, 4, 3, 1),
}

# The small stock list offered when "Use only Retribution's crates and troops" is off.
STOCK_SQUADS = {
    "Standard Group": (6, 2, 2, 0, 0),
    "Anti Air": (2, 0, 0, 3, 0),
    "Anti Tank": (2, 0, 6, 0, 0),
    "JTAC Group": (4, 0, 0, 0, 1),
}
#: (label, DCS type, crates needed) per side.
STOCK_CRATES = {
    Player.BLUE: [
        ("Humvee - MG", "M1043 HMMWV Armament", 1),
        ("Humvee - TOW", "M1045 HMMWV TOW", 2),
        ("M1097 Avenger", "M1097 Avenger", 3),
        ("M-818 Ammo Truck", "M 818", 2),
    ],
    Player.RED: [
        ("BRDM-2", "BRDM-2", 1),
        ("BTR-D", "BTR_D", 1),
        ("9K33 Osa", "Osa 9A33 ln", 3),
        ("Ural-375 Ammo Truck", "Ural-375", 2),
    ],
}


def squad_for_size(size: int) -> tuple[int, int, int, int, int]:
    """A squad of `size`: Retribution's own mix, else the old CTLD count rule."""
    if size in _RETRIBUTION_SQUADS:
        return _RETRIBUTION_SQUADS[size]
    mg = min(size, 2)
    at = min(max(size - 2, 0), 2)
    return (size - mg - at, mg, at, 0, 0)


def squad_types(player: Player, squad: tuple[int, int, int, int, int]) -> list[str]:
    rifles, mgs, ats, aas, jtacs = squad
    return (
        [_RIFLE[player]] * (rifles + jtacs)
        + [_MG[player]] * mgs
        + [_AT[player]] * ats
        + [_AA[player]] * aas
    )


@dataclass
class CtldTroopTemplate:
    side: Player
    label: str
    group_name: str
    size: int
    jtac: bool
    stock: bool = False


@dataclass
class CtldCrateTemplate:
    side: Player
    label: str
    unit_type: str
    group_name: str
    crates: int = 1
    stock: bool = False


@dataclass
class CtldTemplates:
    troops: list[CtldTroopTemplate] = field(default_factory=list)
    crates: list[CtldCrateTemplate] = field(default_factory=list)


class CtldTemplateGenerator:
    def __init__(self, mission: Mission, game: Game, mission_data: MissionData) -> None:
        self.mission = mission
        self.game = game
        self.mission_data = mission_data

    def generate(self) -> CtldTemplates:
        templates = CtldTemplates()
        logistics = self.mission_data.logistics
        if not logistics:
            return templates
        stock = not self.game.settings.plugin_option("ctld.tailorctld")
        for player in (Player.BLUE, Player.RED):
            flights = [info for info in logistics if info.blue == player]
            if not flights:
                continue
            sizes = set(_RETRIBUTION_SQUADS)
            sizes |= {info.transport.cabin_size for info in flights}
            for size in sorted(s for s in sizes if s > 0):
                squad = squad_for_size(size)
                templates.troops.append(
                    self._troops(player, f"Retribution Troops ({size})", squad)
                )
            crate_types = {cargo.unit_type for info in flights for cargo in info.cargo}
            for unit_type in sorted(crate_types):
                if unit_type not in vehicle_map:
                    logging.warning(f"CTLD: no template for crate type {unit_type}")
                    continue
                templates.crates.append(self._crate(player, unit_type, unit_type, 1))
            if stock:
                for label, squad in STOCK_SQUADS.items():
                    templates.troops.append(self._troops(player, label, squad, True))
                for label, unit_type, crates in STOCK_CRATES[player]:
                    templates.crates.append(
                        self._crate(player, label, unit_type, crates, True)
                    )
        return templates

    def _country(self, player: Player) -> Country:
        coalition = self.game.coalition_for(player)
        return self.mission.country(coalition.faction.country.name)

    def _hide(self, group: VehicleGroup) -> None:
        group.late_activation = True
        group.hidden = True
        group.hidden_on_mfd = True
        group.hidden_on_planner = True

    def _troops(
        self,
        player: Player,
        label: str,
        squad: tuple[int, int, int, int, int],
        stock: bool = False,
    ) -> CtldTroopTemplate:
        types = squad_types(player, squad)
        name = f"CTLD {player.name.lower()} {label}"
        position = self.game.theater.terrain.map_view_default.position
        group = self.mission.vehicle_group(
            self._country(player),
            name,
            vehicle_map[types[0]],
            position,
            group_size=len(types),
        )
        for unit, unit_type in zip(group.units, types):
            unit.type = unit_type
        self._hide(group)
        return CtldTroopTemplate(player, label, name, len(types), squad[4] > 0, stock)

    def _crate(
        self,
        player: Player,
        label: str,
        unit_type: str,
        crates: int,
        stock: bool = False,
    ) -> CtldCrateTemplate:
        name = f"CTLD {player.name.lower()} crate {label}"
        position = self.game.theater.terrain.map_view_default.position
        group = self.mission.vehicle_group(
            self._country(player), name, vehicle_map[unit_type], position
        )
        self._hide(group)
        return CtldCrateTemplate(player, label, unit_type, name, crates, stock)
