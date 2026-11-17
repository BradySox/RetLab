# Ground movement (port of Juan's dcs-escalation ground movement)

Status: stages 1 to 6 of 7 built (2026-11-17). Features doc §131.

Source: juanjux/dcs-escalation #561 to #726 (2026-10-26 to 2026-11-11), `game/groundmovement/`.
LGPL-3.0, ported by hand: his tree and ours split long ago.

## What it will do

- Order an armor group, or part of it, to a friendly base, a front, or a map point between
  turns. It covers a set distance a turn and keeps going over several turns; in the mission
  it is a real convoy where it has got to.
- Towed guns need one tractor each. Losses on the road come off the group.
- Spare armor in a base's stock can deploy as a reserve group. A reserve the front reaches
  joins the front.
- A whole mobile SAM battery can relocate: offline while packed, back in the IADS on arrival.
- Supply convoys keep their place across turns.

## DM calls (2026-11-16)

- Port all of it, in stages, armor first, then SAMs.
- On for new games; old saves keep it off.
- 120 miles a turn by road, 60 off-road (his defaults).
- Red moves only when the outside AI (§109) orders it; our planner never moves red.

## Stages

| # | Stage | State |
|---|---|---|
| 1 | Mobility catalog: which units drive, need a tow, or never move | **Built** |
| 2 | Supply convoys keep their place across turns; the setting and the per-turn distances | **Built** |
| 3 | Move an armor group | **Built** |
| 4 | Reserve groups from base stock; joining the front | **Built** |
| 5 | Mobile SAM battery moves (fog reset, Skynet relink) | **Built** |
| 6 | SAMs that defend on the road (Osa, Tor, Buk-M3, C-RAM) | **Built** |
| 7 | Red moves through the outside AI | — |

## Rules it must keep

- A mover gets a 2-waypoint route; one undrivable member pins a group. `mobile: false`
  (§49's flag) always means fixed, whatever `ground_mobility` says.
- Movers last 90 minutes; no phantom units; losses book natively.
- A red SAM or armor group that moves goes back to unknown on blue's map (§3) until it is
  engaged or heard again.
- A reserve that joins a front adds to that front's force weight under §90's rules, not his.
- Our Skynet is range-wired; a moved battery relinks by range on arrival. We do not rebuild
  the IADS every turn as he does.

## Stage 1: the mobility catalog

- `game/groundmovement/mobility.py`: `MobilityMode` (unknown, fixed, self_propelled, towed),
  `GroundMobility` (mode, can_tow), `movement_mobility(unit)`.
- `GroundUnitType.ground_mobility`, read from `ground_mobility:` in each
  `resources/units/ground_units/*.yaml`. 528 blocks copied from his files by filename.
- Infantry and MANPADS walk and never tow. Unreviewed units are unknown and never move:
  83 of 723 today, mostly RetLab-only mod units (the Iran pack, CurrentHill extras, fuel
  trucks). Classify them before stage 5 needs them.
- Tests: `tests/groundmovement/test_mobility.py`.

## Stage 2: convoys keep their place

- `ground_movement` (on for new games), `ground_movement_road_miles` (120),
  `ground_movement_off_road_miles` (60); old saves are switched off in `Game.__setstate__`.
- `game/groundmovement/journey.py` walks a drawn supply route by a distance budget a turn.
- `Convoy` carries the journey; `ConvoyMap.in_transit` holds columns between turns.
- Differs from his: turning the setting off lands columns on the road at once instead of
  freezing them; a convoy with no usable route stays waiting with the reason shown.
- Row B340.

## Stage 3: armor moves

- Ported his `orders`, `routing`, `offroad`, `egress`, `territory`, `planning`, `dispatch`,
  `report` and `samdefense` modules, and `armormovement.py`, almost as written.
- Model: `TheaterGroundObject.in_transit`, `reserve_from_base`; `TheaterUnit.transported_by_id`;
  `Game.ground_movements`; `UnitMap.ground_transport_cargo`. Hooks: `Game.finish_turn`
  (advance), `ControlPoint.capture` (rehome), the TGO generator, the debrief.
- Differences: our own smaller Move window, no map picker, no REST API, no repair check
  (we have no pending repairs), ground groups keep DCS AUTO alarm state.
- Row B341.

## Stage 4: reserves and the front

- Ported his `base.py` and `frontline.py`; the finish-turn hooks; his event rule that an
  absorbed group stays deleted.
- Differences: only groups ground movement made join a front (his takes any armor group the
  front sweeps); no hook in the mission results processor (fronts move in `finish_turn` here);
  no Motor Pool dependency; reserves stay on DCS AUTO; our own Deploy reserve window.
- Our transfers take units out of the base when ordered, so his "undeparted transfer still
  owns stock" rule does not apply.
- Row B342.

## Stage 5: SAM batteries

- His #634 rules: in-transit sites leave the IADS export, ranges zero while packed, GPS
  jammers off, no purchases; tests from his `test_sam_movement.py`.
- Ours: a moved site is `relocated`, wired by range on arrival instead of by the campaign
  config's names, and no longer counts as a fixed SAM site; a red one is forgotten
  (`discovered_by_player = False`) when it sets out.
- Not ported: truck purchases (#699), his IADS state map and map rings (#715-#721).
- Row B343.

## Stage 6: defending on the road

- His #642, #653 and #655 as written, with the globals renamed `RETLAB_SAM_TRANSIT`.
- `LuaGenerator` now takes the mission's `UnitMap` to find the moving batteries.
- His Realistic CAS registry hooks are left out.
- Row B344.
