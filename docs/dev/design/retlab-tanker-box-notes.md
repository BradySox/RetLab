# Tanker box and tanker orbit speed

**Status:** BUILT 2026-09-28; the box flew in test 47. The speed is per flight, on a tanker
flight's Waypoints tab, and saved per airframe by the Payload tab's **Save as default**. Off
by default and never a campaign setting (DM 2026-09-28). **The box is no longer a setting**
(DM 2026-09-29): every theater tanker flies it. It started as an experimental per-flight
tick box on the Payload tab. Rows B152 (speed), B153 (box) and B170 (always on).

## Tanker orbit speed (upstream #869)

- **Per flight, never a campaign setting** (DM 2026-09-28: "never a theatre option. Per
  airframe in the waypoint/loadout setting menu"). `Flight.orbit_speed_kias`, None = the
  aircraft's own speed. Set on the tanker flight's Waypoints tab (`QTankerOrbitSpeed`,
  100-350 KIAS; on the Payload tab until 2026-09-29). **Save as default** stores it per airframe in §43's store
  (`orbit_speed_kias`), so every new flight of that type starts with it.
- The KIAS is converted to true airspeed at the track altitude: `Speed.from_calibrated`,
  ISA atmosphere with the compressible pitot relation. DCS waypoint and orbit speeds are TAS.
- Applies to theater and package tankers (`RefuelingFlightPlan.patrol_speed`).
- **Not** the carrier recovery tanker: its speed comes from the `RecoveryTanker` task
  (`honors_orbit_speed = False`).
- No helicopter-tanker floor: the first cut skipped anything under 200 KIAS, but a
  per-airframe choice is the user's, and 120-130 KIAS is how a KC-130J serves helicopters.
- Capped at the airframe's pydcs `max_speed`. The legacy KC-130 tops out at 335 KTAS, which is
  under 270 KIAS at 20,000 ft, so it flies at its top speed.

## Tanker box

DCS's Orbit task has two patterns, Circle and Race-Track. A box is therefore a **route**, not
an orbit: the tanker flies its corners with the Tanker task active and a `SwitchWaypoint`
loops the lap.

- **Every theater tanker** (`TheaterRefuelingFlightPlan`) flies the box; there is no
  racetrack branch left in that builder. Until 2026-09-29 it was `Flight.tanker_box`, a
  Payload tab tick box saved per airframe. `Flight.__setstate__` drops the old flag, and
  §43 ignores an old store's `tanker_box` key, so neither needs a migration step.
- **Package tankers keep the racetrack.** Their station time is 5 min + (4 × jets + 1) per
  receiver flight, often shorter than one 90 NM lap.
- **Geometry.** The front leg is `TANKER_BOX_LENGTH` (30 NM, across the threat axis), centred
  where the racetrack sat. The box extends `TANKER_BOX_DEPTH` (15 NM) away from the threat. A
  second tanker steps back `TANKER_ORBIT_SPACING + TANKER_BOX_DEPTH` (30 NM), so the boxes
  never overlap. Shrunk from 40 x 20 NM on 2026-09-29 (DM: "downsized a little", after test
  47 showed it working); the cockpit box is drawn from the route, so it follows.
- **Route.** `BOX 1` (PATROL_TRACK, the patrol start) → `BOX 2`, `BOX 3`, `BOX 4` (NAV corners)
  → `BOX END` (PATROL, on BOX 1's position) → home. Layout: `TankerBoxLayout`.
- **Loop.** `BOX END` carries `ControlledTask(SwitchWaypoint(END → BOX 2))` with the start
  condition `timer.getTime() < patrol_end`. The loop goes to BOX 2, not BOX 1: BOX 1's ETA is
  locked, and a locked ETA that has already passed sends the AI chasing it.
- **Overstay.** The loop is checked once per lap, so the tanker leaves up to one lap (about
  15-18 min) after `patrol_end_time`. That overlaps the relief rather than leaving a gap.
- **Speed.** BOX 2 to BOX END carry the patrol speed. A DCS waypoint speed is the speed flown
  toward that point.
- **Moving it.** Dragging any of the five box points on the app map moves the whole box
  by the same offset (`move_box`, called from the map's `set_position` endpoint; DM
  2026-09-28). The package TOT is recomputed as for any drag.
- **Unlimited fuel.** `BOX END` does not re-enable it, because the loop passes BOX END every lap.
  With `ai_unlimited_fuel` on, a box tanker flies home on its own fuel.

### Timing and fuel

The planner and the turn simulator both charge a racetrack's whole station time to the leg
from patrol start to the next waypoint. The box keeps that shape:

- `total_time(BOX 1, BOX 2)` = station time − travel time of the other three legs. The four legs
  sum to the station time, so `BOX END` still falls on `patrol_end_time`.
- Fuel is the same: the first leg carries the station distance minus the other legs.
- The simulator's `RaceTrack` state reads that first-leg time for a box.
- Side effect: the kneeboard ETAs for BOX 2-4 are those of the **last** lap, not the first.

### What reads the two racetrack points, and what the box does there

| Reader | Box behavior |
|---|---|
| Receiver refuel rendezvous (`refuelrendezvous.py`) | Meets on the front leg (`orbit_leg_end` → BOX 2) |
| `TankerInfo` orbit (kneeboard, rendezvous) | Front leg, same helper |
| F10 support-orbit marker (`drawingsgenerator.py`) | Draws the box, buffered by the turn radius |
| DTC cockpit box (`dtc/common.py` `support_boxes`) | Draws the four corners, pushed out by the F10 marker's half-width; the track is the front leg (fixed 2026-09-29, it had drawn a 7 x 5 NM square at BOX 1) |
| App map | Shows the route, which is the box |
| `RaceTrackBuilder` | Tanker task, TACAN and TOT at BOX 1; no Orbit |

### Refuel before the push (2026-10-07)

A receiver can tank at the box before its package pushes: the Waypoints tab's
**Refuel before the push** (features doc, Refuelling). Only a theater tanker is
used, because a package tanker comes on station after the strike. Row B189.

### Verified

- `tests/ato/flightplans/test_tanker_box.py`: geometry, route order, timing sum, fuel, the
  loop's indices and condition, the F10 drawing.
- Headless generation on a Persian Gulf save: three theater tankers boxed, loop at DCS index
  6 → 3, BOX 1 alone ETA-locked, box polygons drawn.
- **Not flown.** Whether DCS's AI keeps tanking through the corners and actually exits on the
  condition is row B153.
