from __future__ import annotations

import math
import random
from datetime import timedelta
from typing import List, Optional, TYPE_CHECKING, Tuple

from dcs import Mission
from dcs.action import AITaskPush
from dcs.condition import GroupLifeLess, Or, TimeAfter, UnitDamaged
from dcs.country import Country
from dcs.mapping import Point, Vector2
from dcs.point import PointAction
from dcs.task import (
    AFAC,
    AttackGroup,
    ControlledTask,
    FAC,
    FireAtPoint,
    GoToWaypoint,
    Hold,
    OrbitAction,
    SetImmortalCommand,
    SetInvisibleCommand,
)
from dcs.triggers import Event, TriggerOnce
from dcs.unit import Skill, Vehicle
from dcs.unitgroup import VehicleGroup

from game.callsigns import callsign_for_support_unit
from game.data.units import UnitClass
from game.dcs.aircrafttype import AircraftType
from game.dcs.groundunittype import GroundUnitType
from game.ground_forces.ai_ground_planner import (
    CLUSTER_DEPTH_OFFSET,
    CombatGroup,
    CombatGroupRole,
    DISTANCE_FROM_FRONTLINE,
    WEDGE_ROLES,
)
from game.ground_forces.frontline_clustering import even_slot_centers
from game.ground_forces.combat_stance import CombatStance
from game.naming import namegen
from game.radio.radios import RadioRegistry
from game.theater.controlpoint import ControlPoint, Player
from game.theater.frontbattles import BattleSite, battles_for
from game.unitmap import UnitMap
from game.utils import Heading
from .aircraft.aircraftpainter import AircraftPainterJtac
from .frontlineconflictdescription import FrontLineConflictDescription
from .groundforcepainter import GroundForcePainter
from .missiondata import JtacInfo, MissionData, FrontlineUnitGroupsInfo
from ..ato import FlightType

if TYPE_CHECKING:
    from game import Game

FRONTLINE_CAS_FIGHTS_COUNT = 16, 24
FRONTLINE_CAS_GROUP_MIN = 1, 2
FRONTLINE_CAS_PADDING = 12000

RETREAT_DISTANCE = 20000
BREAKTHROUGH_OFFENSIVE_DISTANCE = 35000
AGGRESIVE_MOVE_DISTANCE = 16000

FIGHT_DISTANCE = 3500

RANDOM_OFFSET_ATTACK = 250

INFANTRY_GROUP_SIZE = 5
INFANTRY_FORWARD_OFFSET = 400
INFANTRY_SCATTER_RADIUS = 150

# Maximum lateral (along-frontline) jitter applied to a wedge and all its cluster
# members.  Members share their anchor's jitter so the cluster stays laterally
# aligned; each independent group gets its own random value in [-JITTER, JITTER].
CLUSTER_LATERAL_JITTER = 150


def frontline_offsets(groups: list[CombatGroup], size: int) -> dict[int, float]:
    """Along-front offset (metres from one end) for each group.

    Armor wedges are spread evenly across the front. Each clustered member shares
    its anchor wedge's offset (so the cluster stays together). Unclustered groups
    (artillery/logi, or members whose cluster has no wedge) are spread across
    their own even slots.
    """
    wedges = [g for g in groups if g.anchor is None and g.role in WEDGE_ROLES]
    offsets: dict[int, float] = {}
    for wedge, center in zip(wedges, even_slot_centers(len(wedges), size)):
        offsets[id(wedge)] = center
    for g in groups:
        if g.anchor is not None and id(g.anchor) in offsets:
            offsets[id(g)] = offsets[id(g.anchor)]
    leftover = [g for g in groups if id(g) not in offsets]
    for g, center in zip(leftover, even_slot_centers(len(leftover), size)):
        offsets[id(g)] = center
    return offsets


def spread_indices(count: int, battle_count: int) -> list[int]:
    """`count` battle indices spread evenly from end to end, the middle for one.

    With at least as many as there are battles, they are dealt out in turn.
    """
    if count >= battle_count:
        return [index % battle_count for index in range(count)]
    if count == 1:
        return [battle_count // 2]
    return [round(i * (battle_count - 1) / (count - 1)) for i in range(count)]


def battle_slots(
    groups: list[CombatGroup], battle_count: int
) -> dict[int, tuple[int, float]]:
    """Which battle each group joins, and where across it (0 to 1).

    Armor wedges are dealt out across the battles in turn; a side with fewer
    wedges than battles spreads them end to end, so the bigger side sets the
    number of pockets (§111). A clustered member joins its
    wedge's battle; everything else is dealt across the side's own battles.
    """
    slots: dict[int, tuple[int, float]] = {}

    def deal(dealt: list[CombatGroup], battles: list[int]) -> None:
        per_battle: dict[int, list[CombatGroup]] = {}
        for group, index in zip(dealt, spread_indices(len(dealt), len(battles))):
            per_battle.setdefault(battles[index], []).append(group)
        for battle, members in per_battle.items():
            for place, group in enumerate(members):
                slots[id(group)] = (battle, (place + 0.5) / len(members))

    every = list(range(battle_count))
    deal([g for g in groups if g.anchor is None and g.role in WEDGE_ROLES], every)
    for g in groups:
        if g.anchor is not None and id(g.anchor) in slots:
            slots[id(g)] = slots[id(g.anchor)]
    own = sorted({battle for battle, _ in slots.values()}) or every
    deal([g for g in groups if id(g) not in slots], own)
    return slots


def pick_battles(sites: tuple[BattleSite, ...], count: int) -> list[BattleSite]:
    """`count` battles spread evenly along the border, ends included."""
    if count >= len(sites):
        return list(sites)
    if count <= 1:
        return [sites[len(sites) // 2]]
    return [sites[round(i * (len(sites) - 1) / (count - 1))] for i in range(count)]


def follower_advance_distance(stance: CombatStance) -> Optional[int]:
    """Metres an anchored cluster member advances toward the enemy for ``stance``.

    Mirrors the armor wedge's per-stance push so the whole cluster keeps its
    shape: every member advances the *same* distance from its own (already
    offset, per Spec A) spawn, so recon stays ahead and SHORAD/ATGM stay behind.
    ``None`` means add no advance waypoint — DEFENSIVE/AMBUSH hold in place, and
    RETREAT is handled by the universal fallback block in plan_action_for_groups.
    """
    if stance in (CombatStance.AGGRESSIVE, CombatStance.ELIMINATION):
        return AGGRESIVE_MOVE_DISTANCE
    if stance == CombatStance.BREAKTHROUGH:
        return BREAKTHROUGH_OFFENSIVE_DISTANCE
    return None


_MOVE_FORMATION_BY_ROLE: dict[CombatGroupRole, PointAction] = {
    # Armor wedge (TANK/IFV/APC) advances in a Vee — pydcs has no "wedge".
    CombatGroupRole.TANK: PointAction.Vee,
    CombatGroupRole.IFV: PointAction.Vee,
    CombatGroupRole.APC: PointAction.Vee,
    # ATGM standoff pair spreads into a line (pydcs LineAbreast == DCS "Rank").
    CombatGroupRole.ATGM: PointAction.LineAbreast,
}


def move_formation_for_role(role: CombatGroupRole) -> Optional[PointAction]:
    """``move_formation`` for a combat group's role, or ``None`` to keep the
    ``vehicle_group`` default (``OffRoad``). Recon scatters off-road, single-unit
    SHORAD needs no formation, and artillery/logi are unchanged.
    """
    return _MOVE_FORMATION_BY_ROLE.get(role)


class FlotGenerator:
    # Replaced in __init__. The empty defaults keep an instance built without it
    # on the single line across the road.
    battle_sites: list[BattleSite] = []
    _local: dict[str, Tuple[Point, Heading]] = {}

    def __init__(
        self,
        mission: Mission,
        conflict: FrontLineConflictDescription,
        game: Game,
        player_planned_combat_groups: List[CombatGroup],
        enemy_planned_combat_groups: List[CombatGroup],
        player_stance: CombatStance,
        enemy_stance: CombatStance,
        unit_map: UnitMap,
        radio_registry: RadioRegistry,
        mission_data: MissionData,
    ) -> None:
        self.mission = mission
        self.conflict = conflict
        self.enemy_planned_combat_groups = enemy_planned_combat_groups
        self.player_planned_combat_groups = player_planned_combat_groups
        self.player_stance = player_stance
        self.enemy_stance = enemy_stance
        self.game = game
        self.unit_map = unit_map
        self.radio_registry = radio_registry
        self.mission_data = mission_data
        # §111: one battle per sector along the shared border, or None for the
        # single line across the road between the two bases.
        battles = battles_for(game.theater, conflict.front_line)
        self.battle_sites: list[BattleSite] = []
        if battles is not None:
            self.battle_sites = pick_battles(
                battles.sites,
                self._battle_count(
                    player_planned_combat_groups, enemy_planned_combat_groups
                ),
            )
        # Group name -> (its point on the border, its own forward heading).
        self._local: dict[str, Tuple[Point, Heading]] = {}
        self._battle_groups: dict[int, int] = {}

    @staticmethod
    def _battle_count(blue: list[CombatGroup], red: list[CombatGroup]) -> int:
        """As many battles as the side with more wedges can fill. The thinner
        side holds some of them; one wedge on each side used to make a single
        pocket for the whole front (Iraq, 2026-10-13)."""
        counts = [
            sum(1 for g in groups if g.anchor is None and g.role in WEDGE_ROLES)
            for groups in (blue, red)
        ]
        return max(max(counts), 1)

    def _local_for(self, dcs_group: VehicleGroup) -> Optional[Tuple[Point, Heading]]:
        if not self._local:
            return None
        return self._local.get(str(dcs_group.name))

    def _forward(self, dcs_group: VehicleGroup, default: Heading) -> Heading:
        local = self._local_for(dcs_group)
        return default if local is None else local[1]

    def generate(self) -> None:
        # Create player groups at random position
        player_groups = self._generate_groups(
            self.player_planned_combat_groups, is_player=Player.BLUE
        )

        # Create enemy groups at random position
        enemy_groups = self._generate_groups(
            self.enemy_planned_combat_groups, is_player=Player.RED
        )

        # TODO: Differentiate AirConflict and GroundConflict classes.
        if self.conflict.heading is None:
            raise RuntimeError(
                "Cannot generate ground units for non-ground conflict. Ground unit "
                "conflicts cannot have the heading `None`."
            )

        self.wpt_pointaction = (
            PointAction.OnRoad
            if self.game.settings.perf_frontline_units_prefer_roads
            else PointAction.OffRoad
        )

        # Plan combat actions for groups
        self.plan_action_for_groups(
            self.player_stance,
            player_groups,
            enemy_groups,
            self.conflict.heading.right,
            self.conflict.blue_cp,
            self.conflict.red_cp,
        )
        self.plan_action_for_groups(
            self.enemy_stance,
            enemy_groups,
            player_groups,
            self.conflict.heading.left,
            self.conflict.red_cp,
            self.conflict.blue_cp,
        )

        self._generate_front_line_jtac()

        # Record frontline group membership (group name -> unit type) for
        # MFD-hiding. Always populated, independent of whether a JTAC was
        # generated above.
        for vehicle_group, combat_group in player_groups:
            self.mission_data.player_frontline_groups.append(
                FrontlineUnitGroupsInfo(
                    group_name=vehicle_group.name, unit_type=combat_group.unit_type
                )
            )

        for vehicle_group, combat_group in enemy_groups:
            self.mission_data.enemy_frontline_groups.append(
                FrontlineUnitGroupsInfo(
                    group_name=vehicle_group.name, unit_type=combat_group.unit_type
                )
            )

    def _generate_front_line_jtac(self) -> None:
        """Spawn the front-line JTAC: an invisible, immortal FAC orbiting the FLOT,
        lasing for CAS.

        This is Retribution's standard model and, since the packaged-drone JTAC was
        stripped on 2026-08-05, the only one -- gated on nothing but whether the
        faction fields a JTAC, as upstream intends.
        """
        if not self.game.blue.faction.has_jtac:
            return

        position = FrontLineConflictDescription.frontline_position(
            self.conflict.front_line, self.game.theater, self.game.settings
        )
        if self._battle_groups:
            # Over the busiest battle, where CAS is most likely to be needed.
            busiest = max(self._battle_groups, key=self._battle_groups.__getitem__)
            site = self.battle_sites[busiest]
            position = (
                Point(site.x, site.y, self.game.theater.terrain),
                position[1],
            )

        freq = self.radio_registry.alloc_uhf()
        # fc3LaserCode forces every JTAC to 1113 so Su-25/A-10A can lase; otherwise
        # the front line carries its own allocated code.
        if self.game.settings.plugins.get("ctld.fc3LaserCode"):
            code = self.game.laser_code_registry.fc3_code
        else:
            code = self.conflict.front_line.laser_code

        utype = self.game.blue.faction.jtac_unit
        if utype is None:
            utype = AircraftType.named("MQ-9 Reaper")

        country = self.mission.country(self.game.blue.faction.country.name)
        jtac = self.mission.flight_group(
            country=country,
            name=namegen.next_jtac_name(),
            aircraft_type=utype.dcs_unit_type,
            position=position[0],
            airport=None,
            altitude=5000,
            maintask=AFAC,
        )
        AircraftPainterJtac(self.game.blue.faction, utype, jtac).apply_livery()
        cs = jtac.units[0].callsign_dict
        assert type(cs[1]) == int
        assert type(cs[2]) == int
        jtac.points[0].tasks.append(
            FAC(
                callsign=cs[1],
                number=cs[2],
                frequency=int(freq.mhz),
                modulation=freq.modulation,
            )
        )
        jtac.points[0].tasks.append(SetInvisibleCommand(True))
        jtac.points[0].tasks.append(SetImmortalCommand(True))
        jtac.points[0].tasks.append(
            OrbitAction(5000, 300, OrbitAction.OrbitPattern.Circle)
        )
        frontline = (
            f"Frontline {self.conflict.blue_cp.name}/{self.conflict.red_cp.name}"
        )
        self.mission_data.jtacs.append(
            JtacInfo(
                group_name=jtac.name,
                unit_name=jtac.units[0].name,
                callsign=callsign_for_support_unit(jtac),
                region=frontline,
                code=str(code),
                blue=Player.BLUE,
                freq=freq,
            )
        )

    def gen_infantry_group_for_group(
        self,
        group: VehicleGroup,
        is_player: Player,
        side: Country,
        forward_heading: Heading,
    ) -> None:
        # Lead the wedge: seed the infantry ~400m toward the enemy, then scatter.
        in_front = group.points[0].position.point_from_heading(
            forward_heading.degrees, INFANTRY_FORWARD_OFFSET
        )
        infantry_position = self.conflict.find_ground_position(
            in_front.random_point_within(INFANTRY_SCATTER_RADIUS, 50),
            500,
            forward_heading,
            self.conflict.theater,
        )

        faction = self.game.faction_for(is_player)

        # Disable infantry unit gen if disabled
        if not self.game.settings.perf_infantry:
            if self.game.settings.manpads:
                # 50% of armored units protected by manpad
                if random.choice([True, False]):
                    manpads = list(faction.infantry_with_class(UnitClass.MANPAD))
                    if manpads:
                        u = random.choices(
                            manpads, weights=[m.spawn_weight for m in manpads]
                        )[0]
                        vg = self.mission.vehicle_group(
                            side,
                            namegen.next_infantry_name(side, u),
                            u.dcs_unit_type,
                            position=infantry_position,
                            group_size=1,
                            heading=forward_heading.degrees,
                            move_formation=PointAction.OffRoad,
                        )
                        vehicle = vg.units[0]
                        GroundForcePainter(faction, vehicle).apply_livery()
                        vg.hidden_on_mfd = True
            return

        possible_infantry_units = set(faction.infantry_with_class(UnitClass.INFANTRY))
        if self.game.settings.manpads:
            possible_infantry_units |= set(
                faction.infantry_with_class(UnitClass.MANPAD)
            )
        if not possible_infantry_units:
            return

        infantry_choices = list(possible_infantry_units)
        units = random.choices(
            infantry_choices,
            weights=[u.spawn_weight for u in infantry_choices],
            k=INFANTRY_GROUP_SIZE,
        )
        vg = self.mission.vehicle_group(
            side,
            namegen.next_infantry_name(side, units[0]),
            units[0].dcs_unit_type,
            position=infantry_position,
            group_size=1,
            heading=forward_heading.degrees,
            move_formation=PointAction.OffRoad,
        )
        vehicle = vg.units[0]
        GroundForcePainter(faction, vehicle).apply_livery()
        vg.hidden_on_mfd = True

        for unit in units[1:]:
            position = infantry_position.random_point_within(55, 5)
            vg = self.mission.vehicle_group(
                side,
                namegen.next_infantry_name(side, unit),
                unit.dcs_unit_type,
                position=position,
                group_size=1,
                heading=forward_heading.degrees,
                move_formation=PointAction.OffRoad,
            )
            vehicle = vg.units[0]
            GroundForcePainter(faction, vehicle).apply_livery()
            vg.hidden_on_mfd = True

    def _earliest_tot_on_flot(self, player: Player) -> timedelta:
        tots = [
            x.time_over_target
            for x in self.game.ato_for(player).packages
            if x.primary_task == FlightType.CAS
        ]
        return (
            timedelta(seconds=random.randint(150, 900))
            if len(tots) == 0
            else min(
                [
                    x.time_over_target - self.mission.start_time
                    for x in self.game.ato_for(player).packages
                    if x.primary_task == FlightType.CAS
                ]
            )
        )

    def _set_reform_waypoint(
        self,
        dcs_group: VehicleGroup,
        forward_heading: Heading,
        hold_duration: timedelta = timedelta(),
    ) -> None:
        """Setting a waypoint close to the spawn position allows the group to reform gracefully
        rather than spin
        """
        reform_point = dcs_group.position.point_from_heading(
            forward_heading.degrees, 50
        )
        rp = dcs_group.add_waypoint(reform_point)
        hold = ControlledTask(Hold())
        # total_seconds(), not .seconds: a negative timedelta normalises to a negative
        # day plus a positive remainder, so a -60s hold became 86340s -- the group sat
        # out the whole mission. Hold is a running task, so neither red alert nor a
        # manual attack order dislodges it. (juanjux/dcs-retribution#79.)
        hold.stop_after_duration(max(0, int(hold_duration.total_seconds())))
        rp.add_task(hold)

    def _plan_artillery_action(
        self,
        stance: CombatStance,
        gen_group: CombatGroup,
        dcs_group: VehicleGroup,
        forward_heading: Heading,
        target: Point,
    ) -> bool:
        """
        Handles adding the DCS tasks for artillery groups for all combat stances.
        Returns True if tasking was added, returns False if the stance was not a combat stance.
        """
        self._set_reform_waypoint(dcs_group, forward_heading)
        if stance != CombatStance.RETREAT:
            hold_task = Hold()
            hold_task.number = 1
            dcs_group.add_trigger_action(hold_task)

        # Artillery strike random start
        artillery_trigger = TriggerOnce(
            Event.NoEvent, "ArtilleryFireTask #" + str(dcs_group.id)
        )
        artillery_trigger.add_condition(TimeAfter(seconds=random.randint(1, 45) * 60))
        # TODO: Update to fire at group instead of point
        fire_task = FireAtPoint(target, gen_group.size * 10, 100)
        fire_task.number = 2 if stance != CombatStance.RETREAT else 1
        dcs_group.add_trigger_action(fire_task)
        artillery_trigger.add_action(AITaskPush(dcs_group.id, len(dcs_group.tasks)))
        self.mission.triggerrules.triggers.append(artillery_trigger)

        # Artillery will fall back when under attack
        if stance != CombatStance.RETREAT:
            # Hold position
            dcs_group.points[1].tasks.append(Hold())
            retreat = self.find_retreat_point(
                dcs_group, forward_heading, int(RETREAT_DISTANCE / 3)
            )
            dcs_group.add_waypoint(
                dcs_group.position.point_from_heading(forward_heading.degrees, 1),
                self.wpt_pointaction,
            )
            dcs_group.points[2].tasks.append(Hold())
            dcs_group.add_waypoint(retreat, self.wpt_pointaction)

            artillery_fallback = TriggerOnce(
                Event.NoEvent, "ArtilleryRetreat #" + str(dcs_group.id)
            )
            for i, u in enumerate(dcs_group.units):
                artillery_fallback.add_condition(UnitDamaged(u.id))
                if i < len(dcs_group.units) - 1:
                    artillery_fallback.add_condition(Or())

            hold_2 = Hold()
            hold_2.number = 3
            dcs_group.add_trigger_action(hold_2)

            retreat_task = GoToWaypoint(to_index=3)
            retreat_task.number = 4
            dcs_group.add_trigger_action(retreat_task)

            artillery_fallback.add_action(
                AITaskPush(dcs_group.id, len(dcs_group.tasks))
            )
            self.mission.triggerrules.triggers.append(artillery_fallback)

            for u in dcs_group.units:
                u.heading = (forward_heading + Heading.random(-5, 5)).degrees
            return True
        return False

    def _plan_tank_ifv_action(
        self,
        stance: CombatStance,
        enemy_groups: List[Tuple[VehicleGroup, CombatGroup]],
        dcs_group: VehicleGroup,
        forward_heading: Heading,
        to_cp: ControlPoint,
    ) -> bool:
        """
        Handles adding the DCS tasks for tank and IFV groups for all combat stances.
        Returns True if tasking was added, returns False if the stance was not a combat stance.
        """
        duration = timedelta()
        if stance == CombatStance.AGGRESSIVE:
            # Stepping off under air cover is an attacker's concern. Holding a
            # DEFENSIVE group until the enemy's CAS TOT -- half an hour is ordinary --
            # meant it stood still and did not return fire until then.
            # (juanjux/dcs-retribution#79.)
            duration = self._earliest_tot_on_flot(to_cp.coalition.player.opponent)
        self._set_reform_waypoint(dcs_group, forward_heading, duration)
        if stance == CombatStance.AGGRESSIVE:
            # Attack nearest enemy if any
            # Then move forward OR Attack enemy base if it is not too far away
            target = self.find_nearest_enemy_group(dcs_group, enemy_groups)
            if target is not None:
                rand_offset = Vector2(
                    random.randint(-RANDOM_OFFSET_ATTACK, RANDOM_OFFSET_ATTACK),
                    random.randint(-RANDOM_OFFSET_ATTACK, RANDOM_OFFSET_ATTACK),
                )
                target_point = self.conflict.theater.nearest_land_pos(
                    target.points[0].position + rand_offset
                )
                dcs_group.add_waypoint(target_point)
                dcs_group.points[2].tasks.append(AttackGroup(target.id))

            if (
                to_cp.position.distance_to_point(dcs_group.points[0].position)
                <= AGGRESIVE_MOVE_DISTANCE
            ):
                attack_point = self.conflict.theater.nearest_land_pos(
                    to_cp.position.random_point_within(500, 0)
                )
            else:
                # We use an offset heading here because DCS doesn't always
                # force vehicles to move if there's no heading change.
                offset_heading = forward_heading - Heading.from_degrees(2)
                attack_point = self.find_offensive_point(
                    dcs_group, offset_heading, AGGRESIVE_MOVE_DISTANCE
                )
            dcs_group.add_waypoint(attack_point, self.wpt_pointaction)
        elif stance == CombatStance.BREAKTHROUGH:
            # In breakthrough mode, the units will move forward
            # If the enemy base is close enough, the units will attack the base
            if (
                to_cp.position.distance_to_point(dcs_group.points[0].position)
                <= BREAKTHROUGH_OFFENSIVE_DISTANCE
            ):
                attack_point = self.conflict.theater.nearest_land_pos(
                    to_cp.position.random_point_within(500, 0)
                )
            else:
                # We use an offset heading here because DCS doesn't always
                # force vehicles to move if there's no heading change.
                offset_heading = forward_heading - Heading.from_degrees(1)
                attack_point = self.find_offensive_point(
                    dcs_group, offset_heading, BREAKTHROUGH_OFFENSIVE_DISTANCE
                )
            dcs_group.add_waypoint(attack_point, self.wpt_pointaction)
        elif stance == CombatStance.ELIMINATION:
            # In elimination mode, the units focus on destroying as much enemy groups as possible
            targets = self.find_n_nearest_enemy_groups(dcs_group, enemy_groups, 3)
            for i, target in enumerate(targets, start=1):
                rand_offset = Vector2(
                    random.randint(-RANDOM_OFFSET_ATTACK, RANDOM_OFFSET_ATTACK),
                    random.randint(-RANDOM_OFFSET_ATTACK, RANDOM_OFFSET_ATTACK),
                )
                target_point = self.conflict.theater.nearest_land_pos(
                    target.points[0].position + rand_offset
                )
                dcs_group.add_waypoint(target_point, self.wpt_pointaction)
                dcs_group.points[i + 1].tasks.append(AttackGroup(target.id))
            if (
                to_cp.position.distance_to_point(dcs_group.points[0].position)
                <= AGGRESIVE_MOVE_DISTANCE
            ):
                attack_point = self.conflict.theater.nearest_land_pos(
                    to_cp.position.random_point_within(500, 0)
                )
                dcs_group.add_waypoint(attack_point)

        if stance != CombatStance.RETREAT:
            self.add_morale_trigger(dcs_group, forward_heading)
            return True
        return False

    def _plan_apc_atgm_action(
        self,
        stance: CombatStance,
        dcs_group: VehicleGroup,
        forward_heading: Heading,
        to_cp: ControlPoint,
    ) -> bool:
        """
        Handles adding the DCS tasks for APC and ATGM groups for all combat stances.
        Returns True if tasking was added, returns False if the stance was not a combat stance.
        """
        duration = timedelta()
        if stance == CombatStance.AGGRESSIVE:
            # Stepping off under air cover is an attacker's concern. Holding a
            # DEFENSIVE group until the enemy's CAS TOT -- half an hour is ordinary --
            # meant it stood still and did not return fire until then.
            # (juanjux/dcs-retribution#79.)
            duration = self._earliest_tot_on_flot(to_cp.coalition.player.opponent)
        self._set_reform_waypoint(dcs_group, forward_heading, duration)
        if stance in [
            CombatStance.AGGRESSIVE,
            CombatStance.BREAKTHROUGH,
            CombatStance.ELIMINATION,
        ]:
            # APC & ATGM will never move too much forward, but will follow along any offensive
            if (
                to_cp.position.distance_to_point(dcs_group.points[0].position)
                <= AGGRESIVE_MOVE_DISTANCE
            ):
                attack_point = self.conflict.theater.nearest_land_pos(
                    to_cp.position.random_point_within(500, 0)
                )
            else:
                attack_point = self.find_offensive_point(
                    dcs_group, forward_heading, AGGRESIVE_MOVE_DISTANCE
                )
            dcs_group.add_waypoint(attack_point, self.wpt_pointaction)

        if stance != CombatStance.RETREAT:
            self.add_morale_trigger(dcs_group, forward_heading)
            return True
        return False

    def _plan_follower_action(
        self,
        stance: CombatStance,
        dcs_group: VehicleGroup,
        forward_heading: Heading,
        to_cp: ControlPoint,
    ) -> bool:
        """Tasks an anchored cluster member (recon leading, SHORAD/ATGM trailing)
        to maneuver with its wedge: advance the wedge's per-stance distance from
        this group's own offset position, preserving lead/trail spacing.

        Returns True if tasking was added; False for RETREAT, where the universal
        fallback block in plan_action_for_groups adds the retreat waypoints (so we
        must NOT double-add them or attach a morale trigger here).
        """
        duration = timedelta()
        if stance == CombatStance.AGGRESSIVE:
            # Stepping off under air cover is an attacker's concern. Holding a
            # DEFENSIVE group until the enemy's CAS TOT -- half an hour is ordinary --
            # meant it stood still and did not return fire until then.
            # (juanjux/dcs-retribution#79.)
            duration = self._earliest_tot_on_flot(to_cp.coalition.player.opponent)
        self._set_reform_waypoint(dcs_group, forward_heading, duration)

        distance = follower_advance_distance(stance)
        if distance is not None:
            if (
                to_cp.position.distance_to_point(dcs_group.points[0].position)
                <= distance
            ):
                attack_point = self.conflict.theater.nearest_land_pos(
                    to_cp.position.random_point_within(500, 0)
                )
            else:
                attack_point = self.find_offensive_point(
                    dcs_group, forward_heading, distance
                )
            dcs_group.add_waypoint(attack_point, self.wpt_pointaction)

        if stance != CombatStance.RETREAT:
            self.add_morale_trigger(dcs_group, forward_heading)
            return True
        return False

    def plan_action_for_groups(
        self,
        stance: CombatStance,
        ally_groups: List[Tuple[VehicleGroup, CombatGroup]],
        enemy_groups: List[Tuple[VehicleGroup, CombatGroup]],
        forward_heading: Heading,
        from_cp: ControlPoint,
        to_cp: ControlPoint,
    ) -> None:
        if not self.game.settings.perf_moving_units:
            return

        side_heading = forward_heading
        for dcs_group, group in ally_groups:
            forward_heading = self._forward(dcs_group, side_heading)
            if group.role == CombatGroupRole.ARTILLERY:
                if self.game.settings.perf_artillery:
                    target = self.get_artillery_target_in_range(
                        dcs_group, group, enemy_groups
                    )
                    if target is not None:
                        self._plan_artillery_action(
                            stance, group, dcs_group, forward_heading, target
                        )

            else:
                # PR #823 cohesive maneuver.
                if group.role in [
                    CombatGroupRole.TANK,
                    CombatGroupRole.IFV,
                    CombatGroupRole.APC,
                ]:
                    # APC joins the armor wedge (WEDGE_ROLES): full per-stance
                    # advance + engage, not the old soft-follow cap, so an
                    # APC-led wedge stays cohesive with its followers.
                    self._plan_tank_ifv_action(
                        stance, enemy_groups, dcs_group, forward_heading, to_cp
                    )
                elif group.role in [
                    CombatGroupRole.ATGM,
                    CombatGroupRole.SHORAD,
                    CombatGroupRole.RECON,
                ]:
                    if group.anchor is not None:
                        # Clustered: maneuver with the wedge.
                        self._plan_follower_action(
                            stance, dcs_group, forward_heading, to_cp
                        )
                    else:
                        # Unanchored spare: today's generic per-stance advance.
                        self._plan_apc_atgm_action(
                            stance, dcs_group, forward_heading, to_cp
                        )

            if stance == CombatStance.RETREAT:
                # In retreat mode, the units will fall back
                # If the allied base is close enough, the units will even regroup there
                if (
                    from_cp.position.distance_to_point(dcs_group.points[0].position)
                    <= RETREAT_DISTANCE
                ):
                    retreat_point = from_cp.position.random_point_within(500, 250)
                else:
                    retreat_point = self.find_retreat_point(dcs_group, forward_heading)
                reposition_point = retreat_point.point_from_heading(
                    forward_heading.degrees, 10
                )  # Another point to make the unit face the enemy
                dcs_group.add_waypoint(retreat_point, self.wpt_pointaction)
                dcs_group.add_waypoint(reposition_point, self.wpt_pointaction)

    def add_morale_trigger(
        self, dcs_group: VehicleGroup, forward_heading: Heading
    ) -> None:
        """
        This adds a trigger to manage units fleeing whenever their group is hit hard, or being engaged by CAS
        """

        if len(dcs_group.units) == 1:
            return

        # Units should hold position on last waypoint
        dcs_group.points[len(dcs_group.points) - 1].tasks.append(Hold())

        # Force unit heading
        for unit in dcs_group.units:
            unit.heading = forward_heading.degrees
        dcs_group.manualHeading = True

        # We add a new retreat waypoint
        dcs_group.add_waypoint(
            self.find_retreat_point(
                dcs_group, forward_heading, int(RETREAT_DISTANCE / 8)
            ),
            self.wpt_pointaction,
        )

        # Fallback task
        task = ControlledTask(GoToWaypoint(to_index=len(dcs_group.points)))
        task.enabled = False
        dcs_group.add_trigger_action(Hold())
        dcs_group.add_trigger_action(task)

        # Create trigger
        fallback = TriggerOnce(Event.NoEvent, "Morale manager #" + str(dcs_group.id))

        # Usually more than 50% casualties = RETREAT
        fallback.add_condition(GroupLifeLess(dcs_group.id, random.randint(51, 76)))

        # Do retreat to the configured retreat waypoint
        fallback.add_action(AITaskPush(dcs_group.id, len(dcs_group.tasks)))

        self.mission.triggerrules.triggers.append(fallback)

    def find_retreat_point(
        self,
        dcs_group: VehicleGroup,
        frontline_heading: Heading,
        distance: int = RETREAT_DISTANCE,
    ) -> Point:
        """
        Find a point to retreat to
        :param dcs_group: DCS mission group we are searching a retreat point for
        :param frontline_heading: Heading of the frontline
        :return: dcs.mapping.Point object with the desired position
        """
        desired_point = dcs_group.points[0].position.point_from_heading(
            frontline_heading.opposite.degrees, distance
        )
        if self.conflict.theater.is_on_land(desired_point):
            return desired_point
        return self.conflict.theater.nearest_land_pos(desired_point)

    def find_offensive_point(
        self, dcs_group: VehicleGroup, frontline_heading: Heading, distance: int
    ) -> Point:
        """
        Find a point to attack
        :param dcs_group:  DCS mission group we are searching an attack point for
        :param frontline_heading: Heading of the frontline
        :param distance: Distance of the offensive (how far unit should move)
        :return: dcs.mapping.Point object with the desired position
        """
        desired_point = dcs_group.points[0].position.point_from_heading(
            frontline_heading.degrees, distance
        )
        if self.conflict.theater.is_on_land(desired_point):
            return desired_point
        return self.conflict.theater.nearest_land_pos(desired_point)

    @staticmethod
    def find_n_nearest_enemy_groups(
        player_group: VehicleGroup,
        enemy_groups: List[Tuple[VehicleGroup, CombatGroup]],
        n: int,
    ) -> List[VehicleGroup]:
        """
        Return the nearest enemy group for the player group
        @param player_group Group for which we should find the nearest ennemies
        @param enemy_groups Potential enemy groups
        @param n number of nearby groups to take
        """
        sorted_list = sorted(
            enemy_groups,
            key=lambda group: player_group.points[0].position.distance_to_point(
                group[0].points[0].position
            ),
        )
        # Slicing returns the n nearest groups, or all of them when fewer than n are
        # available (it never returns an empty list just because n exceeds the count).
        return [group[0] for group in sorted_list[:n]]

    @staticmethod
    def find_nearest_enemy_group(
        player_group: VehicleGroup, enemy_groups: List[Tuple[VehicleGroup, CombatGroup]]
    ) -> Optional[VehicleGroup]:
        """
        Search the enemy groups for a potential target suitable to armored assault
        @param player_group Group for which we should find the nearest ennemy
        @param enemy_groups Potential enemy groups
        """
        min_distance = math.inf
        target = None
        for dcs_group, _ in enemy_groups:
            dist = player_group.points[0].position.distance_to_point(
                dcs_group.points[0].position
            )
            if dist < min_distance:
                min_distance = dist
                target = dcs_group
        return target

    @staticmethod
    def get_artillery_target_in_range(
        dcs_group: VehicleGroup,
        group: CombatGroup,
        enemy_groups: List[Tuple[VehicleGroup, CombatGroup]],
    ) -> Optional[Point]:
        """
        Search the enemy groups for a potential target suitable to an artillery unit
        """
        # TODO: Update to return a list of groups instead of a single point
        rng = getattr(group.unit_type.dcs_unit_type, "threat_range", 0)
        if not enemy_groups:
            return None
        for _ in range(10):
            potential_target = random.choice(enemy_groups)[0]
            distance_to_target = dcs_group.points[0].position.distance_to_point(
                potential_target.points[0].position
            )
            if distance_to_target < rng:
                return potential_target.points[0].position
        return None

    @staticmethod
    def get_artilery_group_distance_from_frontline(group: CombatGroup) -> int:
        """
        For artillery group, decide the distance from frontline with the range of the unit
        """
        rg = group.unit_type.dcs_unit_type.threat_range - 7500
        if rg > DISTANCE_FROM_FRONTLINE[CombatGroupRole.ARTILLERY][1]:
            rg = random.randint(
                DISTANCE_FROM_FRONTLINE[CombatGroupRole.ARTILLERY][0],
                DISTANCE_FROM_FRONTLINE[CombatGroupRole.ARTILLERY][1],
            )
        elif rg < DISTANCE_FROM_FRONTLINE[CombatGroupRole.ARTILLERY][1]:
            rg = random.randint(
                DISTANCE_FROM_FRONTLINE[CombatGroupRole.TANK][0],
                DISTANCE_FROM_FRONTLINE[CombatGroupRole.TANK][1],
            )
        return rg

    def get_valid_position_for_group(
        self, distance_from_frontline: int, spawn_heading: Heading, along_offset: float
    ) -> Point:
        assert self.conflict.heading is not None
        assert self.conflict.size is not None
        theater = self.conflict.theater
        # Lateral position along the front comes from the caller (#823 even-slot
        # spread + cluster alignment), clamped to the clipped front bounds. This
        # point lies on the front-line trace, so it is valid land. (The fork's
        # perpendicular-step anti-stacking below is preserved on top.)
        clamped = max(0, min(int(along_offset), self.conflict.size))
        if self.conflict.bounds is not None:
            # Rung E: follow the bowed front, so a sector facing open ground sits
            # further forward than one backed against terrain it cannot cross.
            # With no sector depths this returns the same point as the chord.
            shifted = self.conflict.bounds.point_at(clamped)
        else:
            shifted = self.conflict.position.point_from_heading(
                self.conflict.heading.degrees, clamped
            )
        return self._step_back(
            shifted,
            distance_from_frontline,
            spawn_heading,
            self.conflict.size,
            self.conflict.heading,
        )

    def _step_back(
        self,
        shifted: Point,
        distance_from_frontline: int,
        spawn_heading: Heading,
        search_size: int,
        search_heading: Heading,
    ) -> Point:
        """Walk back from `shifted` on the front toward the group's depth."""
        theater = self.conflict.theater
        if not theater.is_on_land(shifted):
            # Degenerate front (e.g. air-only campaign with an arbitrary route).
            # Fall back to the lateral search rather than risk an off-map spawn.
            desired_point = shifted.point_from_heading(
                spawn_heading.degrees, distance_from_frontline
            )
            return FrontLineConflictDescription.find_ground_position(
                desired_point,
                search_size,
                search_heading,
                theater,
            )
        # Step back from the front toward the requested depth, keeping the lateral
        # position fixed. The old code snapped the off-map point *along* the front
        # via find_ground_position, which collapsed every group whose depth ran
        # past the playable zone onto the same valid patch and stacked the units on
        # top of each other. Stepping perpendicular preserves the lateral spread.
        step = 250
        valid_point = shifted
        reached_depth = 0
        distance = step
        while distance <= distance_from_frontline:
            candidate = shifted.point_from_heading(spawn_heading.degrees, distance)
            if not theater.is_on_land(candidate):
                break
            valid_point = candidate
            reached_depth = distance
            distance += step
        # If the perpendicular path off the front ran into water/off-map almost
        # immediately, `valid_point` is still on (or right on top of) the FLOT --
        # which would drop rear-area groups (artillery, logistics) into direct
        # contact. Rather than spawn them on the front, search laterally around the
        # intended-depth point so the group keeps its depth (and spreads along the
        # front instead of stacking).
        if reached_depth == 0:
            # We couldn't step off the front at all (e.g. spawning right next
            # to a coastline) -- valid_point is still sitting on the FLOT
            # itself. Only NOW fall back to the front-axis search. Doing this
            # for any depth shortfall (not just a total one) is what caused
            # the original stacking bug: the front-axis search finds the
            # single nearest valid point to a *target* position, so several
            # groups with different lateral offsets but similar depth
            # shortfalls all collapse onto that same point. Once we've
            # reached ANY perpendicular depth, valid_point is unique to this
            # group's own lateral offset and can never collapse that way, so
            # it's always preferred over the front-axis search below.
            desired_point = shifted.point_from_heading(
                spawn_heading.degrees, distance_from_frontline
            )
            fallback = FrontLineConflictDescription.find_ground_position(
                desired_point,
                search_size,
                search_heading,
                theater,
            )
            if theater.is_on_land(fallback):
                return fallback
        return valid_point

    def _battle_point(
        self, site: BattleSite, place: float, jitter: int, is_player: Player
    ) -> Tuple[Point, Heading]:
        """A group's point on the border in its battle, and its forward heading."""
        x, y = site.point_along((place - 0.5) * site.width + jitter)
        point = Point(x, y, self.conflict.theater.terrain)
        blue_forward = Heading.from_degrees(site.blue_forward)
        return point, blue_forward if is_player.is_blue else blue_forward.opposite

    def _generate_groups(
        self, groups: list[CombatGroup], is_player: Player
    ) -> List[Tuple[VehicleGroup, CombatGroup]]:
        """Finds valid positions for planned groups and generates a pydcs group for them"""
        positioned_groups = []
        assert self.conflict.heading is not None
        spawn_heading = (
            self.conflict.heading.left
            if is_player.is_blue
            else self.conflict.heading.right
        )
        country = self.game.coalition_for(is_player).faction.country
        country = self.mission.country(country.name)

        assert self.conflict.size is not None
        along = frontline_offsets(groups, self.conflict.size)
        slots = (
            battle_slots(groups, len(self.battle_sites)) if self.battle_sites else {}
        )

        # Pass 1: pre-compute depth and lateral jitter for every wedge. This
        # removes the implicit ordering dependency: members no longer need to
        # follow their anchor wedge in the list.
        wedge_depth: dict[int, int] = {}
        wedge_jitter: dict[int, int] = {}
        for wg in groups:
            if wg.anchor is None and wg.role in WEDGE_ROLES:
                wedge_depth[id(wg)] = random.randint(
                    DISTANCE_FROM_FRONTLINE[wg.role][0],
                    DISTANCE_FROM_FRONTLINE[wg.role][1],
                )
                wedge_jitter[id(wg)] = random.randint(
                    -CLUSTER_LATERAL_JITTER, CLUSTER_LATERAL_JITTER
                )

        # Pass 2: place every group using the pre-computed values where available.
        for group in groups:
            if group.role == CombatGroupRole.ARTILLERY:
                depth = self.get_artilery_group_distance_from_frontline(group)
                jitter = random.randint(-CLUSTER_LATERAL_JITTER, CLUSTER_LATERAL_JITTER)
            elif group.anchor is not None and id(group.anchor) in wedge_depth:
                # Cluster member: share anchor's depth+offset and lateral jitter.
                depth = wedge_depth[id(group.anchor)] + CLUSTER_DEPTH_OFFSET.get(
                    group.role, 0
                )
                jitter = wedge_jitter[id(group.anchor)]
            elif id(group) in wedge_depth:
                # Wedge: use its pre-computed depth and jitter.
                depth = wedge_depth[id(group)]
                jitter = wedge_jitter[id(group)]
            else:
                # Unclustered/orphan group.
                depth = random.randint(
                    DISTANCE_FROM_FRONTLINE[group.role][0],
                    DISTANCE_FROM_FRONTLINE[group.role][1],
                )
                jitter = random.randint(-CLUSTER_LATERAL_JITTER, CLUSTER_LATERAL_JITTER)

            on_border: Optional[Point] = None
            forward = spawn_heading.opposite
            if slots:
                battle, place = slots[id(group)]
                self._battle_groups[battle] = self._battle_groups.get(battle, 0) + 1
                on_border, forward = self._battle_point(
                    self.battle_sites[battle], place, jitter, is_player
                )
                final_position = self._step_back(
                    on_border,
                    depth,
                    forward.opposite,
                    int(self.battle_sites[battle].width),
                    Heading.from_degrees(self.battle_sites[battle].left_to_right),
                )
            else:
                final_position = self.get_valid_position_for_group(
                    depth, spawn_heading, along_offset=along[id(group)] + jitter
                )

            g = self._generate_group(
                is_player,
                country,
                group.unit_type,
                group.size,
                final_position,
                heading=forward,
                # None (recon/SHORAD/arty/logi) keeps the OffRoad default.
                move_formation=move_formation_for_role(group.role)
                or PointAction.OffRoad,
            )
            if is_player == Player.BLUE:
                g.set_skill(Skill(self.game.settings.player_skill))
            else:
                g.set_skill(Skill(self.game.settings.enemy_vehicle_skill))
            positioned_groups.append((g, group))
            if on_border is not None:
                self._local[str(g.name)] = (on_border, forward)

            if group.role in [CombatGroupRole.APC, CombatGroupRole.IFV]:
                self.gen_infantry_group_for_group(g, is_player, country, forward)

        return positioned_groups

    def _generate_group(
        self,
        player: Player,
        side: Country,
        unit_type: GroundUnitType,
        count: int,
        at: Point,
        heading: Heading,
        move_formation: PointAction = PointAction.OffRoad,
    ) -> VehicleGroup:
        cp = self.conflict.front_line.control_point_friendly_to(player)
        faction = self.game.faction_for(player)

        name = namegen.next_unit_name(side, unit_type)

        group = self.mission.vehicle_group(
            side,
            name,
            unit_type.dcs_unit_type,
            position=at,
            group_size=count,
            heading=heading.degrees,
            move_formation=move_formation,
        )
        group.hidden_on_mfd = True

        self.unit_map.add_front_line_units(group, cp, unit_type)

        for c in range(count):
            vehicle: Vehicle = group.units[c]
            vehicle.player_can_drive = True
            GroundForcePainter(faction, vehicle).apply_livery()

        return group
