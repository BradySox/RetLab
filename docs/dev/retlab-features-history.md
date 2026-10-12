# RetLab features — history

Text moved out of [`retlab-features.md`](retlab-features.md) on 2026-10-12, unchanged.
The features doc keeps one line per entry and points here. Open this file when that
line is not enough: each entry carries the rule, the files and the tests.

Add to this file only by moving text out of the features doc.

## §6 — Front-anchored support-orbit placement (AEW&C + tanker) (2026-06-22) — REMOVED 2026-08-09

The design as it stood before the 2026-08-09 revert, and the failure modes of upstream's
placement that it fixed. What replaced it is in the features doc §6.

**Symptom (fresh Red Tide save, AI-generated turn):** the AI's AWACS and tanker racetracks
were placed nonsensically. Red AWACS targeting a far-north CP (Kastrup) was generated
**~326 NM behind the front and ~175 NM off-axis** (out over the Baltic); the red tanker sat
only ~28 NM behind the FLOT (exposed); a blue tanker whose nearest-friendly target was its own
departure field could clamp **onto the home runway**. Brady hand-moved them to sane,
front-centered positions — that edit is the spec this reproduces.

**Root cause.** `aewc.py` and `theaterrefueling.py` independently anchored the orbit on
`package.target` (a CP — *nearest* friendly for tankers, **farthest** friendly for AWACS) and
offset it along the bearing from that CP to the nearest enemy threat-zone boundary. For a
rear/flank CP that bearing is unstable (it swings as the front shifts), so the orbit flung
off-axis; the blue tanker also had a `max(0, …)` clamp that pinned it to the anchor when the
field was within the buffer of the front.

**Fix** (`game/ato/flightplans/supportorbit.py`, new shared helper used by both builders):
`support_orbit_anchor()` anchors on the **FLOT center** of the active front nearest the
supported area, then pushes the orbit into friendly airspace along the **stable enemy→friendly
axis** (`friendly_cp → enemy_cp` heading) until it is at least the configured buffer from the
enemy threat zone (`threat_zones.distance_to_threat` / `threatened`). Result: centered on the
front, on the coalition's own side, at a sane standoff, no forward/clamp special-casing. Falls
back to the old target-anchored standoff when there is no active front (opening turn). Buffers
unchanged: `aewc_threat_buffer_min_distance` (80 NM) / `tanker_threat_buffer_min_distance`
(70 NM).

**Depth asymmetry (`AI_SUPPORT_DEPTH_FACTOR`, default 2.5):** the *player* coalition holds
forward at 1x the buffer behind the FLOT (coverage); the *AI* coalition holds deep at
`factor x buffer` so red tankers/AWACS don't loiter near the front. Both are then pushed
further if needed to clear the enemy threat zone. Tying depth to the threat zone alone left red
right on the FLOT when the player had no forward SAMs reaching the front; the factor decouples
"how deep the AI sits" from "how strong the player's threat is." With a campaign buffer of 40
NM this puts red ~100 NM back and blue ~50 NM; at the default 80/70 buffers red is ~200/175 NM
deep. Verified by recomputing the broken save: red AWACS `+326/−175 NM → centered, ~100 NM
behind`, blue forward-but-centered. Tests: `tests/test_support_orbit.py`. Upstream-core
flight-plan code, so an upstream-PR candidate. **Lua-free; in-game pass ☑ VERIFIED 2026-06-24 (C1/C2).**

**No-front (naval-map) fix (2026-07-16, the flown Scenic Route finding).** The depth march is a
depth *behind the FLOT*; on a theater with **no front line at all** (blue = carrier groups only,
or fully disconnected islands) it marched the orbit `factor × buffer` **away from the only enemy
on the map**, stacked on an anchor (`farthest_friendly_control_point`) already chosen to be the
CP most distant from the enemy threat — the flown red A-50 orbited 233–322 NM from the fleet,
behind its own base. `support_orbit_anchor` now skips the depth march when `front is None`
(the carrier branch already did): the anchor holds and only the threat-clearance floor applies,
which still guarantees ≥ buffer outside the enemy ring. Also fixed in the same branch: an anchor
*inside* the threat zone had its `toward_enemy` inverted (heading-to-closest-boundary points OUT
of the zone from inside), so the clearance push marched it deeper in — now flipped. New tests in
`tests/test_support_orbit.py` (no-front AI hold, threat floor, inside-zone escape).
**Second half found 2026-07-17 (the flown Scenic Route Merged A-50, 424 NM out):** with the
march gone the orbit correctly *holds at its anchor* — but the anchor is the AEWC package
**target**, and `theaterstate.aewc_targets` picked `farthest_friendly_control_point()` (the
rearmost field, sane only when a front exists for the geometry to work against). On a
front-less theater the non-carrier AEWC target is now `closest_friendly_control_point()` —
the friendly field nearest the enemy — so a land-based AWACS covers the actual fight;
fronted campaigns are byte-identical (the farthest pick stands).
**Third half, same day (the user's first look at the resulting map):** the forward anchor
exposed the no-front *placement* bug — `support_orbit_anchor`'s nearest-threat-boundary
bearing finds the shortest way OUT of the threat union, which from an anchor deep inside a
big fighter zone threads the gap BETWEEN enemy fields (the blue E-2/tanker stack anchored on
Khasab was placed **27–45 NM from Bandar-e-Jask's Tomcat ramp** — clear of every ring,
parked in the enemy's lap; the flown KC-135 died to an Iranian AIM-54 in exactly that
pocket). On a front-less theater with enemy land CPs the orbit now **faces the nearest
enemy control point and stands ONE buffer behind its anchor for both sides** (the enemy
field plays the front; the 2.5× AI depth factor stays FLOT-only or it would recreate the
deep-A-50 bug from the other direction), with the threat-clearance floor unchanged. The
boundary bearing remains only for carrier orbits (hold with the boat) and theaters with no
enemy land at all. Save-verified: blue support moves to the southwest gulf (206/183 NM from
Bandar Abbas), the red A-50 holds 78 NM behind its own front field. Tests
`tests/test_support_orbit.py` (3 new no-front-geography cases; the old no-front tests keep
passing via the no-enemy-CP fallback).

**Carrier/fleet exception (2026-06-28).** Front-anchoring a support orbit makes sense for a
land-based AWACS/tanker, but it flung *carrier* AEW&C (E-2C) up to the land FLOT — covering the
fighting instead of the boat it launched from. The auto-planner already tasks one AEW&C per
carrier CP (`theaterstate.aewc_targets = [carrier CPs] + farthest-friendly CP`), so the *target*
already encodes which orbit belongs to which fleet; only the placement ignored it. Now
`support_orbit_anchor` checks `is_carrier`/`is_fleet` on the target (other `MissionTarget`s lack
the attribute → treated as land) and, for a carrier/fleet target, **anchors on the carrier and
only nudges clear of the threat zone** — no FLOT re-center, no forward/AI-deep march. So the E-2C
covers its task force while a land EC-121/E-3 still front-anchors for forward coverage, with no
map-specific tuning (purely `is_carrier`-keyed → campaign-agnostic). `aewc.py`'s lateral
anti-stack spread is also scoped to AEW&C flights sharing the **same target** (anchor), so a land
AWACS no longer shoves a carrier E-2 off its boat now that the two sit on different anchors.
Verified by recomputing the `auto gen` Caucasus save (2× E-2C + 1× EC-121, the same
headless-recompute method that VERIFIED the C1/C2 parent fix): the carrier E-2Cs went from
**~218 NM** off their carriers to **~32 NM** (centered on the boat); the EC-121 stays forward on
the front. Tests: `tests/test_support_orbit.py` (`test_carrier_target_holds_on_the_fleet`,
`test_fleet_target_also_holds_on_the_fleet`). **Lua-free; geometry change, no new in-game-pass row
(folds under the C1/C2 support-orbit item).**

## §8 — Robustness / crash fixes

### Flight plans and routing

- **A stand-off shooter flew past its own launch range and died at the target
  (2026-08-19).** The attack task does not activate until a flight reaches the ingress
  point, and `Doctrine.max_ingress_distance` is **weapon-agnostic** — 45 nm on modern
  doctrine, for a dumb bomb and a 270 nm Kh-22 alike. A package carrying anything that
  out-ranges that was therefore dragged from its launch range into the target's defenses
  without shooting: the "flew straight in and never launched" case. Applies to both
  sides, and to §63 cruise missiles, §81 anti-ship and Arc Light alike.
  - **The rule.** A weapon yaml may declare `range:` in **nautical miles**
    (`WeaponGroup.standoff_range`). `PackageWaypoints.standoff_doctrine` widens the
    ingress bound to the package's own reach. It **only ever widens** — a short-range
    authored weapon never pulls the ingress in.
  - **The package number is the MINIMUM across its shooters**, because one ingress point
    serves the whole package and it attacks together. A flight carrying nothing with an
    authored range (an escort) is **excluded, not counted as zero** — counting it would
    collapse the package back to the doctrine bound and undo the fix.
  - **Capped at 60% of the departure-to-target leg.** `JoinZoneGeometry` puts the join at
    35–36% of that leg from home, so an ingress past ~64% measured from the target would
    sit **behind** the join and invert the route. The cap is what makes a 590 nm CALCM
    safe to author.
  - **It is a planning bound, not a promise.** DCS releases at its own doctrine distance
    regardless (measured elsewhere at ~140 nm for a YJ-12, ~130 nm for a Kh-22 that
    reaches 270+). What it buys is that the flight is not inside the defenses before its
    attack task exists — not brochure range.
  - **Data is the gate.** 25 weapon groups are authored from published maximum range
    (Harpoon 67, SLAM-ER 150, HARM 80, Kh-22 270, JASSM-ER 500, CALCM 590 …); anything at
    or under 45 nm is deliberately left unauthored because it changes nothing. **`range:`
    is for air-to-ground stand-off weapons only** — an air-to-air range would drag an
    attack package's ingress out for a missile with nothing to do with the target.
  - ⚠️ **This is a planner divergence from upstream**, added after the 2026-08-09
    re-convergence. It is not one of the three reverts that decision named (§46, §6, the
    commander behaviours) — it is a new defect fix, and juanjux's fork carries the same
    one — but it is a divergence and should be called out if the re-convergence is
    re-examined. Tests `tests/ato/test_standoff_ingress.py`. Needs an in-game pass
    (checklist **B87**). Found by reviewing juanjux's fork; see
    [retlab-juanjux-fork-watch-notes.md](design/retlab-juanjux-fork-watch-notes.md).

- **A hold was never told to release when the TOT was unreachable (2026-08-19).** Flight
  plans are built backwards from the TOT, so a TOT the flight cannot physically make puts
  `push_time` before mission start. `HoldPointBuilder` passed that straight through as the
  orbit's stop-after-time and as the backing `TimeAfter` trigger, and **DCS never fires a
  trigger scheduled for a negative time** — so the flight orbited its hold for the entire
  mission. Clamped to 0 and logged; the flight still cannot make that TOT, it just flies the
  mission instead of sitting out of it. Tests
  `tests/missiongenerator/test_holdpoint_release.py`. Found by juanjux/dcs-retribution#100.

- **Front-line groups were held in place and never fought (2026-08-19).** Two independent
  causes in `FlotGenerator`, both upstream-shared. (1) `_set_reform_waypoint` fed
  `timedelta.seconds` to `stop_after_duration`: a negative delta normalises to a negative day
  plus a positive remainder, so a CAS package whose TOT landed before mission start turned a
  `-60s` hold into **86340 s — 23h59m**. Now `total_seconds()`, clamped at zero. (2) The
  hold-until-`_earliest_tot_on_flot` gate applied to `DEFENSIVE` as well as `AGGRESSIVE`, so a
  defender stood still and did not return fire until the *enemy's* CAS arrived — half an hour
  is an ordinary value. Only `AGGRESSIVE` waits now. Worth knowing for anyone debugging this
  in the ME: `Hold` is a **running task**, so neither red alert nor a manual attack order
  dislodges a group stuck this way. Tests
  `tests/missiongenerator/test_flotgenerator_hold.py`. Found by juanjux/dcs-retribution#79;
  his third cause (`perf_red_alert_state` leaving the FLOT on GREEN) does not apply here —
  the fork removed that toggle in #231 and non-IADS groups fall to DCS **AUTO**.

- **"Mission cannot be saved due to errors" — locked speed on the second of two adjacent
  TOTs (the recurring generated-mission rejection, fixed 2026-08-03).** DCS refused to load
  a generated Marianas turn-2 miz with *"All waypoints (2-2) have locked speed and
  surrounded by waypoints 1 and 2 with locked time!"* on `Kunlun Shan BARCAP|27|68|J-15
  Flanker X-2|`. The rejection rule is `verifyRouteSeg_` in DCS's own
  `MissionEditor/modules/me_route.lua`: walking the route TOT to TOT, every segment bounded
  by two ETA-locked waypoints must contain at least one waypoint with an **unlocked speed**
  in the range `(from, to]` — **inclusive of the closing waypoint**, so two *adjacent*
  ETA-locked waypoints are rejected whenever the second one is also speed-locked.
  `WaypointGenerator._resolve_locked_speed_time_conflicts` modelled the span as strictly
  interior (it only unlocked a waypoint with an ETA-locked neighbour on **both** sides), so
  the adjacent case was invisible to it. The trigger is `PydcsWaypointBuilder.set_waypoint_tot`,
  which speed-locks a waypoint whose ETA clamps to 0: an **air-started** flight whose next TOT
  has already elapsed gets an ETA-0 spawn point (`ensure_in_flight_route_has_locked_time`)
  immediately followed by an ETA-0 TOT waypoint, both speed-locked — hence the "I get this a
  lot" pattern, since it needs only a regeneration after the sim has advanced past a
  racetrack/JOIN TOT. The resolver is now a faithful port of the DCS rule (interior unlocking
  is unchanged; if the inclusive span still has no unlocked speed, the closing waypoint's
  speed lock is dropped too). Times are never touched — they sync the flight to its package
  and late activation requires the first waypoint's TOT. The `_route_is_dcs_legal` helper in
  `tests/missiongenerator/test_helo_terrain_anchors.py` was likewise carrying the old
  strictly-interior model and is now a port of `verifyRoute`. Verified by replaying the
  archived rejected route (§66 archive `marianas_second_island_chain_2027_turn02_20260803-231832.miz`)
  through the new resolver: rejected → legal. Tests
  `tests/missiongenerator/aircraft/test_waypointgenerator.py`. Upstream-shared (carve
  candidate) — no setting, no save change, existing saves fix themselves on the next
  generation.

- Spurious "past start times" warning for player CAP: a BARCAP/TARCAP is meant to be
  on-station at mission start, so a cold-start spin-up legitimately begins before mission
  start — and the scheduler reserves only the 2-min AI startup while a player-flown flight
  gets the larger `player_startup_time` allowance, so a player-occupied cold-start CAP tripped
  the warning every turn. `QTopPanel.negative_start_packages` now checks **takeoff** time (not
  startup) for DCA patrols, so a genuine "can't even take off in time" misplan still warns but
  the normal cold-start CAP does not. Tests: `tests/test_negative_start_packages.py`.

- **Player CAS steerpoints floating at the combat altitude (user-reported, fixed 2026-07-16).**
  A flown Hornet CAS deck read **22000** on both FLOT waypoints — "target waypoints generate in
  the air and are unable to be found". The CAS FLOT boundaries are planned at
  `builder.get_combat_altitude` (`cas.py`) and stamped **RADIO**, i.e. ~22,000 ft *AGL*: correct
  for the AI, whose waypoint **is** the track to fly, but a human's steerpoint diamond then floats
  22,000 ft over the terrain with nothing under it to acquire or slave a pod to. Every other target
  waypoint already ships on the deck (`_target_point`/`_target_area` both use `meters(0)`); CAS was
  the one type carrying an AI track altitude into a cockpit. Nothing caught it: the 22,000 is just
  `COMBAT_ALTITUDE_BAND_KFT = (20, 20)` (a spreadless "band" every fixed-wing airframe collapses
  onto) plus `plane_altitude_offset` scatter, `cas()`'s `meters(1000)` is a **floor** so it only
  ever raises, and `FlightWaypointType.CAS` has no entry in the generator dispatch table.
  `PydcsWaypointBuilder.build()` already zeroed waypoints for client flights with exactly this
  stated intent ("so that they can slave target pods or weapons to the waypoint") but only inside
  `if self.waypoint.flyover:`; that check is lifted out onto a shared
  `FlightWaypoint.marks_ground_for_player` (`flyover or waypoint_type in
  GROUND_MARKED_WAYPOINTS`), leaving the flyover `PointAction` assignment untouched. **AI flights
  are unaffected** — `client_count == 0` never trips it, so no AI CAS track is pushed toward the
  ground. The split lives at generation, not in the layout, because `QFlightSlotEditor` calls
  `roster.set_pilot()` without recreating the flight plan, so `client_count` can change after the
  layout is built. The **kneeboard derives from the same predicate**: it reads the planning model's
  `alt` while the `.miz` zeroes the pydcs point, so a generation-only fix would print 22000 against
  a grounded steerpoint (this also fixes the pre-existing same disagreement on flyover waypoints,
  which the kneeboard has always printed at combat altitude). Whether 20,000 ft is a sensible *AI*
  CAS track is a separate, untouched question. Tests:
  `tests/ato/test_flightwaypoint_ground_marked.py` + `tests/missiongenerator/test_kneeboard_cas_altitude.py`.
  Upstream-shared (carve candidate — upstream's own comment already asks for it). Checklist
  **C10** — in-game pass DONE. **Extended 2026-07-19 (the flown DS91 escort deck — "5 Target
  and 8 Landing should be radio alt 0", then "expand this to all Target and landing waypoints"):**
  the escort's TARGET area was the *other* waypoint type carrying an AI track altitude into the
  cockpit (`WaypointBuilder.escort()` plans it at `get_combat_altitude`, BARO — the deck read
  "Target area 22000" beside a Land row of 0). `GROUND_MARKED_WAYPOINTS` now lists **every target
  and landing type** — `TARGET_GROUP_LOC`/`TARGET_POINT`/`TARGET_SHIP` +
  `LANDING_POINT`/`CARGO_STOP` — keyed on what the waypoint IS, never its route position or the
  owning flight type. Strike/recon targets and landings are already *planned* at 0 AGL, so the
  only row that visibly moves is the escort target; for the rest the listing pins the invariant
  structurally instead of relying on each producer remembering `meters(0)`. DIVERT is deliberately
  out (an off-map divert is an exit vector flown at cruise altitude), as are pickup/dropoff zones
  (helo approach altitudes planned for CTLD). The **§74 DTC cartridge honors the same predicate**
  (`client_altitude` in `dtc/common.py`, both builders): it previously emitted the raw planning
  altitude, so an AutoLoad would have floated a zeroed steerpoint back up to the track altitude —
  the escort target, and the same latent disagreement on every CAS/flyover steerpoint since the
  original fix. Planned altitudes are untouched: the AI escort still transits at its track
  altitude, and the pure-AI route is byte-identical. Extra coverage in
  `tests/missiongenerator/test_dtc.py` (`test_cartridges_ground_marked_waypoints_like_the_miz`).

- **Hold points placed across the map (fixed 2026-08-16).** A SEAD Sweep held **205.7 nm**
  from its own runway to attack a target **23.6 nm** away — 596 nm of routing, still
  outbound when the mission ended (flown, session `c86c58dd`; group 442 of the 4th-test
  miz). Two independent faults, both in upstream-identical planner files.
  `JoinZoneGeometry.find_best_join_point()` falls back to `join = self.ip` **exactly**
  when it finds no usable geometry, so the IP-to-join separation was just the 500 ft
  `FormationAttackFlightPlan` perturbation (measured on that flight: 0.81 nm) — and
  `HoldZoneGeometry` aimed its 40° wedge down that heading, i.e. down `random.randint`.
  `find_best_hold_point()` then answers "nearest point of a zone" with **no bound**, so a
  wedge aimed anywhere strands the hold anywhere. Fix: `wedge_heading()` takes the stable
  `target → join` axis below a 1 nm separation — the same form `JoinZoneGeometry` already
  uses for its own wedge, so the two agree rather than this inventing a rule — and
  `_bounded()` keeps the hold within the doctrine hold distance (or home-to-join,
  whichever is larger), falling back to the point the preferred branch would have picked.
  Verified against the flown coordinates: **205.7 nm → 25.0 nm**, exactly the doctrine
  hold distance, with non-degenerate geometry unchanged. Intermittent by nature (1 of 40
  flights; the same squadron flew a sane 125 nm route the turn before), which is how it
  survived. Tests `tests/flightplan/test_holdzonegeometry.py` (7) — three fail without the
  fix. **Fork divergence:** both files are byte-identical to upstream, so this diverges the
  planner while the carve is frozen; carve candidate the moment it lifts.

- **Ground-level waypoints written at sea level (test 7, fixed 2026-08-18).** Takeoff,
  landing and divert waypoints all carried altitude 0 — 105 of one flown mission's 192 air
  waypoints. The number is not cosmetic: it reaches the cockpit through the kneeboard card
  and the DTC steerpoint, so Ramon Airbase (619 m) read as below the jet's own nav solution.
  `ControlPoint.field_elevation` now returns the OSM/DEM field elevation from
  `resources/airport_imagery/<terrain>.json` — the same table the ATIS uses for QFE — and
  `WaypointBuilder.takeoff/land/divert` write it as BARO. Carriers, FARPs and FOBs stay at
  0 MSL: a deck is within ~20 m of sea level and there is no record for the rest. The target
  waypoint keeps its deliberate 0 AGL/RADIO, which is what lets a player slave a pod to the
  mark. Repaired at generation time too (`WaypointGenerator.repair_ground_level_altitudes`,
  `set_ground_start_altitude`) because the flight-plan layout is pickled into the save, so a
  campaign in progress would otherwise keep the old 0 forever. Upstream-inherited —
  `WaypointBuilder.land()` was byte-identical to `upstream/dev` — so it is a carve candidate
  post-freeze. Known gap: QRA intercept and red-scramble groups spawn outside
  `WaypointGenerator` and still read 0; they never reach a kneeboard. Checklist B79; tests
  `tests/missiongenerator/aircraft/test_pydcswaypointbuilder.py`.
  **Knock-on, fixed the same day:** `bulk_editable` (the "Apply to all" altitude setter)
  decides what to move by asking whether a waypoint was planned above the deck, and its
  comment recorded takeoff/landing/divert as 0-seeded. Moving them off 0 made the setter
  eligible to overwrite a field elevation with the cruise altitude. Takeoff and landing are
  now in `BULK_ALTITUDE_SKIP_TYPES`; divert is separated by whether its control point is an
  `OffMapSpawn`, since an off-map divert is an exit vector that *should* move and altitude
  no longer distinguishes the two.
  **The landing half never actually reached the cockpit (fixed 2026-08-20).**
  `LANDING_POINT` was in `GROUND_MARKED_WAYPOINTS`, whose listing was justified by
  "land() already plans 0 AGL" — true when it was written, false after the fix above. So
  for every client flight the kneeboard row, the .miz steerpoint and the DTC cartridge all
  zeroed the field elevation the planner had just written, while the AI flew the real
  number. Flown 2026-08-20: a Viper card off Al Minhad read `Takeoff 191` over `Land 0`,
  same field. `LANDING_POINT` is out of the tuple and must not go back; `CARGO_STOP` stays,
  because `cargo_stop()` does still plan 0 AGL. The target waypoints are unaffected and keep
  their deliberate 0 AGL. Tests `tests/ato/test_flightwaypoint_ground_marked.py`,
  `tests/missiongenerator/test_kneeboard_cas_altitude.py`.

- **Escorts released at the JOIN instead of the SPLIT (test 7 follow-on, fixed 2026-08-21).**
  Escort release is the user flag `split-<package>`: raising it fires `AITaskPush` on every
  escort, whose triggered action is a `SwitchWaypoint` to its own SPLIT index. On 2026-08-18
  a hidden 15 km trigger zone on the primary's SPLIT point was added as a second source,
  because DCS never runs a client-occupied group's route tasks and the `RunScript` on that
  waypoint therefore never fired for a player-led package. **A package's JOIN and SPLIT are
  the same base point** — `PackageWaypoints.create` derives both from one `join_point` and
  perturbs each by up to 1 nm — so the primary flies that zone twice and the *inbound* pass
  released the escorts before the package had ingressed. Measured in a flown Iraq mission:
  zone r=15000 at SPLIT (105186, 23140), JOIN at (104377, 24261), **0.75 nm** apart; the
  SEAD escort turned for home at the join and announced its own split index on the radio.
  No radius fixes this. `split_release_gate` adds a time condition ANDed to the zone — the
  midpoint of the planned join→split leg (774 s / 2257 s → 1515 s there) — which the
  outbound pass cannot reach without flying the whole route at twice the planned speed.
  Ungateable (no join or no split TOT) drops the zone and keeps the backstop alone: a late
  release costs a tag-along escort, an early one costs the escort over the target. Note the
  trigger keys on the primary having client **slots**, not a human in one, so an AI-flown
  player-slotted package was hit too; a package whose primary has no client slots releases
  from the `RunScript` and was never affected. Checklist B78; tests
  `tests/missiongenerator/aircraft/test_split_release.py`.

- **AI packages were timed to arrive after the mission ended (2026-08-24).** The spread that
  staggers non-CAP packages bounds the random **offset** by the cycle length, then adds it to
  the package's earliest possible TOT: `package.time_over_target = next(start_time) + tot`.
  Offset plus transit is the arrival, and nothing bounded that, so a long-transit package was
  scheduled past the end of the mission and never serviced its target at all.
  - **⚠️ The share this affected was overstated, and the numbers are withdrawn.** They
    were measured against hand-edited saves, whose air wings, basing and laydown are curated
    rather than generated, so they described the save and not the planner. Re-run on fresh
    campaigns the effect is small. `tools/measure_tot_past_mission_window.py` still counts it
    -- drive it from `tools/_campaign_game.py`, never from a save. The fix stays on the
    strength of the code being wrong, not of a measurement.
  - **The offset now buys from the room the transit leaves**, scaled rather than clamped
    (`MissionScheduler._spread_arrival`). Clamping to the ceiling would give every over-long
    package the *same* TOT — the one arrival time a spread exists to stop packages sharing. A
    transit already past the ceiling takes no delay at all: it cannot make the cycle, so it
    goes as early as it can rather than later still.
  - **Blue was hit harder than red** (11 of 16 blue spread packages on one dense turn), so this
    is a shared-path correction, not a red buff. Ungated — a package outside the mission is
    wrong on both sides. A zero-transit package is timed exactly as before, which is what keeps
    §89's widened tail intact.
  - Found by the planner doctrine-mining queue (row 2). Tests `tests/test_missionscheduler.py`
    (2 behavioural, red/green confirmed; 2 exclusion pins). Needs an in-game pass
    (checklist **B99**).

### Refuelling

- **Refuel waypoints on flights with no tanker to meet (fixed 2026-08-16).** The planner
  emits a REFUEL waypoint whenever the coalition owns a tanker-capable squadron
  *anywhere in theater*. But when no tanker is actually flying the
  mission, the waypoint is a detour to an empty piece of sky. Flown 2026-08-16: **10 of
  40** flights carried one, including a `LHA-1 Tarawa Escort` with a **14 nm** total route
  and its refuel point 3.7 nm from the boat, and a `CVN-75 Escort` at 19 nm with one at
  7.5 nm. `WaypointGenerator` now drops the waypoint at **generation** when
  `mission_data.tankers` holds no tanker on that flight's side — so the plan, and §46's
  decision, are untouched. `mission_data.tankers` is the generated truth (the tankers that
  exist in the .miz) rather than the planner's ownership question. Absent tanker data
  (lightweight test doubles) reads as "yes" so nothing is dropped on a guess, and the side
  test compares `Player.is_blue` rather than the enum, which is always truthy — a bare
  truthiness test would have made the gate a silent no-op.
  Tests `tests/missiongenerator/test_refuel_waypoint_gate.py`.

- **The refuel waypoint was planned whether or not a tanker was flying, and the fuel readout
  believed it (fixed 2026-08-17).** Reported off the Payload tab: a Hornet burning 8,111 lb of
  the 15,225 it carried read *"1 tanker pass · RTB margin +11,680 lb"*. Two separate faults
  behind one line, and **neither was a tanker being tasked** — `PlanRefueling` walks theater
  refueling stations under `TheaterSupport` and never looks at a strike flight's fuel, so no
  flight causes a tanker to exist.
  1. **The waypoint's gate asked the wrong question.** `_build_refuel` required only
     `air_wing.can_auto_plan(FlightType.REFUELING)` — *does this coalition own a tanker
     squadron*, a question about the air wing rather than about this turn. `game/ato/
     tankeravailability.py::serviceable_tanker_planned` now additionally requires a tanker in
     the ATO this flight can actually use, which is the same question the generated mission
     already asks (`refuelrendezvous.py`). Safe at plan time because `TheaterSupport` is the
     **first** method `PlanNextAction` yields, so tankers are in the ATO before any offensive
     package is planned; and it reads `flight_type`/`unit_type` only, never another flight's
     `flight_plan`, which would risk recursion. `FlightType.RECOVERY` is its own flight type,
     so recovery tankers are excluded by construction rather than by a check. Applied to
     TARCAP too, whose refuel is doctrinal (top off coming off station) but still needs a
     tanker to exist.
  2. **The readout credited a top-off as fact.** The walk restores to a full load at each
     REFUEL waypoint, so the reported margin included fuel the sortie only gets if it actually
     plugs in: 15,225 − 8,111 − 2,000 `min_safe` = **+5,114 lb** unrefuelled against the
     **+11,680** shown, a 6,566 lb overstatement. `FuelBrief` now carries `dry_margin_lbs`
     alongside, the text **leads with the unrefuelled figure**, and the with-tanker number is
     printed only when the sortie genuinely depends on it ("does NOT get home without the
     tanker"). The module docstring also still described §46 fitting tanks and tasking tankers
     — reverted 2026-08-09 — and now says what it actually does.
  **Deliberately NOT done: gating the waypoint on fuel need.** That is what §46 decided, and
  re-opening it would re-open the planner divergence the 2026-08-09 re-convergence closed. A
  flight that carries plenty and crosses a real tanker still gets a waypoint; what it no longer
  gets is a phantom one, or a margin that counts gas it never takes. Tests
  `tests/ato/test_tanker_availability.py`, `tests/retlab/test_fuel_brief.py`.
  3. **The other two faces still credited the tanker (fixed 2026-09-15).** The rule above
     landed on the Payload-tab brief only. The kneeboard ladder's min-fuel walk reset to
     `min_safe` at the REFUEL waypoint, so its "RTB margin" was the spare *at the tanker*
     labelled "to get home" (measured on the Syria turn-2 F-16 DEAD: card **+1,920 lb**
     against the brief's **+1,124 lb** for the same sortie), and `BingoEstimator` counted a
     REFUEL waypoint as a fuel source, so bingo shrank to the fuel to reach the tanker. Both
     now follow the brief: the minimum is always the fuel home unrefuelled
     (`_estimate_min_fuel_for` no longer resets), bingo is to the recovery field only, and the
     kneeboard prints the with-tanker figure as its own amber line only when the sortie
     depends on it (`FlightPlanBuilder.tanker_line`, "Does not get home without the tanker:
     +N lb with the planned pass").
  4. **The brief counted a pass generation would drop, at a point no tanker orbits (fixed
     2026-09-15).** It walked the planner's waypoints as-is, so a boom receiver with only a
     probe tanker flying still read "1 tanker pass planned", and the legs were burned to the
     75 %-of-the-way geometric point. `refuelrendezvous.planned_tankers` builds the same
     tanker set from the ATO's REFUELING flights that generation registers as `TankerInfo`,
     and `fuel_brief._as_generated` resolves each REFUEL waypoint through the same
     `refuel_rendezvous` — dropped when no tanker can serve the jet, moved onto the orbit
     otherwise (a copy; the plan's own waypoint is untouched). All three faces now agree on
     the save: brief **+1,120 lb**, ladder **+1,120 lb**, bingo 4,000 lb to the field.

- **The refuel waypoint pointed at a place no tanker was (fixed 2026-08-17).** The
  follow-on to the gate above, and the reason the surviving waypoints sat where they did.
  The planner puts the refuel point at 75 % of the home-to-join leg (`RefuelZoneGeometry`)
  and the tanker stations `tanker_threat_buffer_min_distance` outside its own target's
  threat ring (`TheaterRefuelingFlightPlan`) — two rules with no term in common, so the
  waypoint and the tanker were independent by construction.
  `game/missiongenerator/refuelrendezvous.py` now resolves the waypoint against the
  tankers in the generated .miz: nearest point on the nearest **suitable** orbit, or the
  waypoint is dropped. Suitable excludes the other coalition, a receiver the tanker cannot
  service (`can_refuel_from` — a probe-only jet and nothing but a boom tanker up is the
  same as no tanker), and **recovery tankers**, which work the boat's pattern rather than
  passing traffic. Subsumes the 2026-08-16 gate. Three details that make it safe: the
  orbit is a 40 nm racetrack so the resolution is nearest-point-on-leg, clamped to the
  ends (its centre is 20 nm out on its own); a package tanker already orbits the package
  refuel point, so resolution there is a no-op and idempotent across re-generation; and a
  tanker registered without orbit data leaves the planned point alone rather than reading
  as "none flying". `TankerInfo` gained `orbit_start`/`orbit_end`/`recovery`, filled where
  the flight-plan class is known. Support packages already generate first
  (`_prioritized_packages` sorts them last, and the loop walks it reversed), so every
  tanker is registered before any receiver's waypoints are built. Also fixes a defect the
  2026-08-16 gate introduced: a dropped REFUEL stayed on the **kneeboard** list, so the
  card numbered a steerpoint the jet did not have and every later row was off by one
  against the cockpit — and the fuel ladder still credited a top-off that could not happen.

### Support orbits and radios

- **Support flights sharing one radio channel (the flown "I can't talk to the A-6 tanker",
  fixed 2026-08-02).** A player-flown carrier strike could not raise its own buddy tanker on
  any channel, while the theater KC-135 answered normally. Root cause is in
  `FlightGroupConfigurator.setup_radios` (`game/missiongenerator/aircraft/flightgroupconfigurator.py`):
  an AEWC/REFUELING/RECOVERY flight inherits its **package** frequency. That is correct while
  each support flight is the only one in its package (the theater tanker and AEW&C packages each
  get their own), but **§44 long-range carrier ops deliberately puts a buddy tanker *and* an E-2
  in as primary flights of the same package** (`game/retlab/carrier_ops.py`) — so both took
  the one package channel. The flown miz had `Milestone 8` (A-6E) and `Wizard 7` (E-2C) both on
  **396.0 AM**; DCS builds the comms menu per frequency, so only the AEW&C answered and the
  tanker was unreachable from the cockpit (the §74 DTC cartridge corroborated it — COMM2
  channels 3/4/5 all resolved to 396.0 and all took the AEW&C's name). `setup_radios` now routes
  the inherited channel through `dedicated_support_frequency`, which allocates a fresh UHF when
  another tanker/AEW&C flight already holds it (`support_frequencies` reads the
  `MissionData.tankers`/`awacs` registrations, so the check covers both classes and both
  coalitions). The **first** support flight in a package still keeps the package frequency, so no
  channel is wasted in the common single-support case, and an **explicitly assigned**
  `Flight.frequency` is honored as-is — only the inherited package channel is replaced.
  Generation-time ⇒ **existing saves fix themselves on the next regeneration, no NEW game.**
  Tests: `tests/missiongenerator/aircraft/test_flightgroupconfigurator.py`. Upstream-shared
  (carve candidate — `setup_radios` is upstream code; only the §44 package shape that exposes it
  is fork-side).

### Carrier deck and recovery

- **Carrier-recovery stagger (the flown Scenic Route midair, fixed 2026-07-16).** Two AI
  packages (an OX S-3B and a CATERPILLAR Hornet) recovering to CVN-71 in the same window
  converged co-altitude at ~1,000 ft and collided 2.7 NM from the boat — blue's only losses
  of the mission. Root cause is structural: Retribution authors **no approach leg at all**
  (the last waypoint is a nav point at cruise altitude, then a `Land` task ON the boat), so
  DCS's own carrier-pattern AI flies the whole descent and two flights sent into the same
  window inevitably converge in the DCS overhead; the per-flight `plane_altitude_offset`
  scatter never touches the pattern, and no recovery-time deconfliction existed. Arrival
  TIME is therefore the only lever: `MissionScheduler._deconflict_carrier_recoveries`
  (`game/commander/missionscheduler.py`, run after TOT assignment and BEFORE the
  recovery-tanker ETA collection, so tankers time against the staggered landings) spaces
  each boat's package landings ≥ `CARRIER_RECOVERY_INTERVAL` (5 min) apart by delaying
  TOTs. Only "spread" AI packages are movable; CAP waves (coverage schedule wins), AEW&C
  (handoff-chained), SCAR (on-station ASAP), ASAP taskings, and **any package with a player
  flight** are FIXED entries — they claim their slot as-is and the movable packages space
  around them, so a human's recovery is never rescheduled but AI traffic clears their
  window. The slotting core is the pure `staggered_recovery_deltas` (single sorted pass;
  delaying never breaks an earlier bound). Always-on — no setting, no plugin, no save
  change (the §62 modex precedent). Helo and shore recoveries are ignored. Tests:
  `tests/test_carrier_recovery_stagger.py`. Upstream-shared (carve candidate). Checklist
  **C9** — needs an in-game pass.

- **The carrier respotted for recovery mid-launch (fixed 2026-08-16).** §72's recovery
  tier fired at **t+79 s** of a 2,233 s mission — **375 s before the player's own takeoff
  roll** — spawning three static Hornets into his taxi lane, one **8.66 m** off his
  track (flown, session `c86c58dd`, CVN-75). The astern cone had tripped on something
  **not identifiable from the recording**: at both qualifying polls the only blue
  fixed-wing inside the cone radius were the boat's own four parked Hornets, all inside
  `DECK_STAMP_M`, and the one aircraft in the whole 37-minute recording that satisfies
  every gate appears 170 s *later* for a 2.9 s window. Rather than guess at the trip
  source, the fix bounds what a spurious trip can do: the emitter now computes
  `earliestClearS` per boat from the last departure off that deck
  (`launch_cycle_ends_at`, + a 10-minute margin for the cold-start roll) and the plugin
  refuses to respot before it — holding **both** the cone and the deadline, since an
  airboss window that opens mid-launch is itself the thing being guarded against. A deck
  that launches nothing emits 0 and keeps the old behaviour exactly. The E-2C the DM
  suspected is innocent: 138–152 m astern on the round-down, struck below correctly both
  flights. Tests in `tests/missiongenerator/test_carrier_deck_decor.py`.

- **The launch-cycle hold outlasted the mission (fixed 2026-08-17).** The mirror of the
  bug above, introduced by its fix. `departure_delay` is the whole wait until a flight's
  scheduled start, so one late package off CVN-71 held the respot to **t+11,388 s of a
  19-minute mission** — the deck never respotted at all (flown 2026-08-16, 5th test:
  `still launching, respot held until 11388s`). `launch_cycle_ends_at` now returns the
  **current** cycle: the run of departures from the first, broken by an idle gap longer
  than `LAUNCH_CYCLE_MARGIN_S`. One constant serves as both the post-launch margin and the
  cycle-ending gap, since both are "this deck is done" in seconds. It also logs the flight
  count and the resulting hold, so a long hold is visible instead of silent.

- **The astern cone fired with nothing in it, and now says what tripped it
  (instrumented 2026-08-17).** A faithful replay of `approachDetected` over the whole 4th-
  test recording **never trips**, at any poll from t+60 to t+390: the only objects ever
  inside the 4.5 nm cone were four deck Hornets inside the 400 m stamp bubble, the boat's
  own rescue helo (a rotorcraft the `Group.Category.AIRPLANE` scan cannot see, and 155–180°
  off the stern — ahead of the beam), and a Ticonderoga 129° off the stern at 3.7 km. The
  emitted BRC (138.0) matches the recorded ship heading exactly and every plugin option
  was at its default, so the geometry and the thresholds are not the explanation either.
  The trip source is therefore **still unknown**, and the plugin now logs the tripping
  unit's name, range, off-stern angle, altitude and closing rate on **every** trip poll —
  not only the one that clears — plus the pcall error if the check throws. An
  unattributable clear cost a Tacview forensics session; a named one costs a log line.
  The §72 launch-cycle floor above bounds the damage meanwhile.

- **The deck-spot table was blind where the decorations stand (fixed 2026-08-17).**
  `KNOWN_PARKING_SPOTS` held 11 of the Supercarrier guide's 16, and the 2026-08-07 audit
  named the two holes: nothing forward of x = +1.0, and a 63 m starboard band between
  x = −35.5 and x = −98.7 holding 52 of the 67 street-gear placements. Both are now
  **measured**, by the t=0 ship-frame method that produced the original 11, over five
  CVN-71 recordings: the six-pack row continues forward to **(+35.6, +36.7)** and
  **(+23.4, +35.5)** (6 sightings each, 4–5 independent missions, F-14/Hornet/EA-18G all
  parking to the same centres), the starboard mid-deck band holds **(−89.8, +26.4)** (9
  sightings, 5 missions) and **(−76.3, +26.4)**, and the port quarter continues forward to
  **(−74.6, −38.4)** on the row's own 12 m pitch. 11 → 16 entries. The new data
  immediately caught a live hazard the old table could not see: the recovery tier put a
  tow tractor **5.8 m** from a real spawn point. Rather than nudge coordinates by eye —
  the method that has failed this feature before — `RECOVERY_DECK_VARIANTS` is now the
  authored data filtered through `clears_known_spots`, dropping sets that fall below
  `MIN_RECOVERY_SET_ITEMS` (9 authored sets → 7 shipped), so a future measured spot prunes
  whatever it invalidates with no further authoring. The launch-phase street sets were
  already clear of all 16.

### Helicopters

- **AI helicopter terrain CFIT (the flown Red Tide M1 Harz/Sauerland pattern, fixed
  2026-07-12).** Three compounding upstream-shared defects put AI helos on collision
  courses with high terrain (two Mi-8s dead within 46 s of unpause, a Mi-24 escort into
  the Sauerland — while the flat-ground H FRG 12 pair flew the identical plan cleanly):
  (1) `WaypointBuilder.get_cruise_altitude` short-circuited every helo altitude to the
  *combat* AGL setting (`heli_combat_alt_agl`, 100 ft in the flown save), so all transit
  waypoints (JOIN/HOLD/REFUEL/NAV) were planned at treetop height — now returns the
  dedicated `heli_cruise_alt_agl` (500 ft default; the pattern ferry/rtb already used);
  (2) a RADIO (AGL) waypoint anchors the commanded altitude to terrain only AT the
  waypoint and DCS interpolates straight between waypoints, so 40–110 km low legs were
  commanded through ridge lines — `WaypointGenerator._insert_helo_terrain_anchors()` now
  subdivides every long RADIO leg of an AI helo route with **speed-locked** "TERRAIN"
  Turning Points every ≤5 NM (`MAX_HELO_ANCHOR_SPACING`), giving piecewise
  terrain-following without Python needing elevation data (none exists at generation);
  racetrack orbit legs and human-crewed flights are never touched. **Lock-flag fix
  2026-07-12 (the first generated Red Tide M2 tripped it):** the anchors originally
  inserted with BOTH speed and ETA unlocked, which DCS rejects at mission start on any
  leg not bracketed by TOT-locked waypoints ("has both unlocked speed and time and not
  surrounded by waypoints with locked time" on every subdivided helo RTB leg — AH-64D
  CAS + both Mi-24P BAI/Escort flights); they now insert speed-locked (the state DCS
  accepts everywhere else) and `_resolve_locked_speed_time_conflicts`, which runs right
  after in `build()`, unlocks any anchor that lands between TOT-locked waypoints (the
  inverse rejection). Verified by a full-route lock-flag sweep of a regenerated M2 miz
  (0 violations; the errored miz showed exactly the three flagged flights); (3) both air-start
  spawner paths set only `points[0].alt_type = "RADIO"` while pydcs leaves every
  *unit's* `alt_type` at "BARO" — and DCS places an in-air spawn from the unit record,
  so a 500 m-AGL intent spawned as 500 m MSL (below the ~600 m Harz FARP terrain); the
  spawner now mirrors the point's altitude reference onto every unit. Tests:
  `tests/ato/flightplans/test_helo_cruise_altitude.py`,
  `tests/missiongenerator/test_helo_terrain_anchors.py`,
  `tests/missiongenerator/test_airstart_unit_alt_type.py`. All three are upstream-shared
  (carve candidates). Checklist **C8** — in-game pass DONE.

### Loadouts and module data

- **Loadout integrity (jets flying clean / wrong ordnance).** A fleet-wide audit found two
  silent failure modes that dropped whole presets: (1) a stray empty pylon (`["CLSID"] = ""`
  / `<CLEAN>`) made `Loadout.valid_payload` reject the entire loadout (244 presets across 44
  airframes) — fixed by skipping empty stations; and (2) stale/dead CLSIDs (AJS-37 `{Rb15}`,
  the F/A-18E/F STA-02 JSOW `BRU55`→`BRU` rename) — repaired in `resources/customized_payloads`.
  Plus `ANTISHIP` gained the Strike fallback every other A2G task already had (so an anti-ship
  jet without an anti-ship preset carries iron bombs, not nothing). Guarded by
  `tests/data/test_weapons.py` (`test_valid_payload_ignores_empty_stations`,
  `test_antiship_falls_back_to_strike_loadout_names`,
  `test_customized_payload_clsids_resolve_or_are_known_stragglers` — fails on any *new* dead
  CLSID). A follow-up pass fixed the **F-14A Block 135-GR Early** (its `.lua` had the *Late*
  variant's `unitType` so its ground presets were never applied), authored a missing
  **F-14A Block 95-GR Export** payload file (iron-bomb presets — no LANTIRN), and switched the
  **Tornado IDS STRIKE** preset from TGP-less LGBs to iron Mk-82. Methodology + remaining
  residuals (mod-weapon stragglers, low-impact early-date noise):
  `docs/dev/design/retlab-loadout-integrity-audit-notes.md`.

- **Datalink era gating — the EPLRS boolean became a policy (2026-08-16).** DCS reuses
  the EPLRS name for the generic group *datalink-enable* task: Link 16 on a Hornet or
  Viper, SADL on an A-10C. Without it the terminal never comes up and the SA page reads
  empty — not as an error, which is what made it expensive to find. **pydcs already adds
  the task** (`dcs/mission.py:736`); `configure_behavior` clears WP0's task list, and
  `configure_eplrs` is the only thing that restores it. So the switch does not *add*
  datalink, it restores what the generator just deleted — which is why hand-built ME
  missions have it and generated ones did not. Flown 2026-08-16: **1 of 23** blue plane
  groups carried the task against **16 of 18** in a hand-built modern mission on the same
  install, with `eplrs_enabled = False` inherited from the saved-settings `Default.zip`.
  One boolean cannot serve a fork shipping 1981→2027: on gives Desert Storm Hornets Link
  16 a decade early, off costs the modern campaigns their datalink. Replaced by
  `DatalinkPolicy` (`ERA_CORRECT` default / `ALWAYS` / `NEVER`) reading a per-airframe
  `datalink_introduced:` in the unit files — the same shape as §24's `date_gated_properties`.
  pydcs's own `eplrs` flag cannot answer the era question: it means only "DCS lets you tick
  the box" and is true for 87 airframes including the B-47, the Tu-16 and the OV-10A. 14
  airframes authored (the ones the fork's era-split campaigns field); **absent reads as
  permissive**, so an un-authored airframe behaves exactly as before and the data set
  extends one row at a time. Ground units are unaffected by `ERA_CORRECT` — their own
  introduction dates already decide whether they exist. Saves migrate to the explicit
  choice (`True→ALWAYS`, `False→NEVER`), never silently to `ERA_CORRECT`, mirroring §64's
  six-pack boolean. **Ruled out on the way:** the DTC cartridge (DCS's own
  `FA-18C_hornet_DTC.lua` has no datalink field at all, and a missing top-level block is
  legal — the reference cartridge itself omits `GPS_WYPT` and `HARM` and flies fine), the
  Link-16 STNs, and the OVGME mods. Note the working reference's AWACS carry **no STN** and
  its Hornets **zero donors** — the one datalink-named field separating the two files was
  EPLRS. Design note `retlab-datalink-era-notes.md`; tests `tests/test_datalink_era.py`.

### Ground movement

- **Supply convoys spawning on the runway (2026-08-02, the flown Baltic Fury report "why are
  units generating on the runway").** A convoy's spawn is `Convoy.route_start` — literally
  `convoy_routes[destination][0]`, the first waypoint of the authored supply route. An
  `Airfield` control point's `position` **is** the DCS airfield reference point — pydcs uses
  that exact point for a `StartType.Runway` spawn (`_flying_group_from_airport`) — so any
  campaign that anchored a route endpoint on the control-point coordinate parked its whole
  departing convoy on the runway. Confirmed in the flown miz: `Convoy 001` (3 vehicles) at
  0.3 m from the Bremen reference and `Convoy 002` at 0.4 m from Nordholz. The de-stack
  mechanism that would otherwise have saved it — miz-authored cp-convoy spawn markers
  (`M1043_HMMWV_Armament` groups → `MizCampaignLoader._construct_cp_spawnpoints`) — was not
  authored anywhere near Bremen or Nordholz, so `_find_closest_cp_spawn` returned nothing and
  every unit piled onto waypoint 0. (**The "0 of 72 campaigns" claim originally written here
  was wrong** — 26 campaigns author them; see the 2026-08-06 entry below, where that error is
  what let the bug survive its own fix.) `ConvoyGenerator.spawn_position` now walks the spawn out
  along the **authored corridor** (never off it) to the first point ≥
  `AIRFIELD_SPAWN_CLEARANCE_M` (1500 m — clears a runway half-length plus aprons while keeping
  the convoy at the base, still BAI-targetable and inside its defensive umbrella) that is also
  on land, bounded by `MAX_SPAWN_WALK_M` (5 km) so a fouled approach never marches the convoy
  toward the enemy. Every failure mode degrades to today's behaviour: no runway (FOB/FARP/
  carrier), an already-clear endpoint, an authored spawn chain (respected wholesale — moving
  only the lead would strand it ahead of the rest), or no clear ground in budget all return the
  authored point unchanged. Generation-time, so **existing saves are fixed by the next
  regeneration** — no new game. Headless-verified on the flown save: both convoys move
  0.3/0.4 m → ~1503 m clear. Upstream-shared (upstream's miz-drawn `front_line_path_groups`
  have the same waypoint-0-at-the-CP pattern); carve candidate. The campaign-data half of the
  same report — 3 Baltic Fury ammunition depots authored at 0 m from the Hamburg/Peenemünde/
  Szczecin references — is fixed in the miz and CI-locked in `tests/retlab/test_baltic_fury.py`
  (design note `retlab-baltic-fury-campaign-notes.md`). Tests
  `tests/missiongenerator/test_convoy_spawn_clearance.py`.

- **The runway guard's two escape hatches (2026-08-06, the flown Caucasus - Slava Ukraini report
  "tanks drove on the runway and broke the AI taking off").** Eight T-80UDs (`Convoy 001`) spawned
  with their lead vehicle **on Anapa-Vityazevo's airport reference point**, strung 214 m across
  runway 22, while eight AI flights (~24 aircraft, all `TakeOffParkingHot`) taxied out. The
  2026-08-02 guard above was present in the running build and **never executed**, because
  `generate_convoy` reads `position = convoy.route_start if spawns_tuple else spawn_position(...)`
  — an authored spawn chain is respected wholesale — and this route had one. Three defects, all
  needed:
  1. **`_find_closest_cp_spawn` had no distance bound.** It returned the nearest
     `M1043 HMMWV Armament` marker *anywhere on the map*. Slava Ukraini authors 6, all serving
     other routes; the nearest to Anapa (`Ground-42`, **9.4 km** away) belongs to the Anapa→Maykop
     front route heading the opposite way. `_interpolate_points` builds its chain **starting at
     the route's endpoint** and interpolating toward the marker at 100 ft separation, so it
     produced **441 points running from the runway** — and the miz confirms the mechanism exactly:
     unit spacing 30.49 m (= 100 ft) on the precise bearing to `Ground-42`. Measured fork-wide:
     **388 route endpoints claim a marker, 308 of them within 2 km (legitimate), but 66 from
     markers 10–447 km away** (Red Tide two at ~171 km, Desert Storm one at 447 km; Novorossiysk's
     reverse leg drew a **1677-point** chain off the same 185 km marker). New
     `MizCampaignLoader.MAX_CP_CONVOY_SPAWN_DISTANCE_M` (**5 km** — comfortably covers a large
     airbase complex, and the measured legit population clusters far below it) drops the claims
     388 → 322 with a worst remainder of 4 954 m. A dropped chain is not a loss: the convoy falls
     back to an ordinary group spawn, which the clearance guard then protects.
  2. **A chain built from the endpoint begins on the runway whenever the route does**, however
     well the marker was placed. The decision is extracted to `ConvoyGenerator.spawn_plan` →
     `SpawnPlan(position, spawns, cleared)`, which **discards the chain and clears the field**
     when the spawn had to be walked out (logged as a warning naming the convoy and field). A
     *fouled* approach — no clear ground inside the walk budget — keeps the chain instead, since
     discarding it there would leave the convoy on the runway **and** stacked on one point.
  3. **`wpts.extend(route)` included `route[0]`.** Even a convoy whose spawn was walked clear had
     the authored point as its first commanded waypoint, so it drove straight back onto the runway
     — visible in the flown miz as group waypoint 1 sitting 0.4 m from the reference. The authored
     start is now skipped when the spawn was cleared (`route[1:]`); an un-cleared convoy keeps the
     full route byte-identically.
  Campaign-data half: Slava Ukraini's §50 batch-1 blue rear corridor authored **both** endpoints
  on airport reference points (`[-5412, 243129]` is Anapa's, `[-40918, 279256]` is Novorossiysk's),
  so both fields were exposed. Both moved ~2 km down the same corridor; headless-verified that each
  end still binds its own control point, sits on land, and now carries no spawn chain (441 → 0,
  1677 → 0) while the legitimate Anapa→Maykop chain (136 points) is preserved. Generation-time, so
  **existing saves fix themselves on the next regeneration** — no new game. Upstream-shared (the
  cp-convoy spawn-route feature is upstream's); carve candidate. Tests
  `tests/campaignloader/test_cp_convoy_spawn_distance.py` (6) +
  `tests/missiongenerator/test_convoy_spawn_clearance.py` (4 new).

### Campaign and save robustness

- New Game crash on an authored-but-empty `aircraft:` key (2026-07-01): a campaign-YAML
  squadron whose `aircraft:` key exists but has no entries parses as `None`, and
  `DefaultSquadronAssigner.find_squadron_for` iterated it —
  `TypeError: 'NoneType' object is not iterable` at game generation. *Northern Guardian* and
  *WRL Noisy Cricket (Redux)* both ship such squadrons, so New Game on either crashed (found
  by the campaign-phases `--engine --all` batch, which exercises the real generation pipeline
  for every campaign). `SquadronConfig.from_data` now treats it as `[]` — the existing "any
  aircraft compatible with the primary task" fallback — in
  `game/campaignloader/campaignairwingconfig.py`. Generic upstream-code fix on upstream
  campaigns (upstream-PR candidate). Test:
  `tests/test_campaignairwingconfig_empty.py::test_authored_empty_aircraft_key_reads_as_any`.

- Player-despawn counted as a combat loss (2026-06-20): a player dropping to spectator — or
  the mission ending with players still airborne — makes DCS fire `S_EVENT_CRASH`/`DEAD` for
  that jet, which `dcs_retribution.lua` recorded into `crash_events`/`dead_events`, so
  `debriefing.py` attrited the airframe + pilot even though they survived (GERBIL F-14s logged
  lost while alive at mission end; confirmed in Tacview, none in `destroyed_objects_positions`).
  The plugin now marks a unit on `S_EVENT_PLAYER_LEAVE_UNIT` and suppresses the crash/dead/lost
  that follows within `PLAYER_LEAVE_GRACE_S` (`is_player_despawn`). A real shootdown fires the
  loss event **before** the player leaves the seat, and **ejections are excluded** (an ejection
  is a real loss), so both still count. This is upstream loss-accounting (good upstream-PR
  candidate). Tests: `tests/test_debriefing.py::test_lua_suppresses_player_despawn_loss_events`.
  **Residual to watch in-game:** if the engine tears the mission down without per-player
  `PLAYER_LEAVE_UNIT` events, those despawn-crashes aren't caught — land/despawn before ending
  remains the belt-and-suspenders.

- **Task-claim generation crash — group-role degrade instead of raise (fixed 2026-08-16).**
  `AircraftBehavior.configure_task` raised `RuntimeError` at generation time when an AI
  flight's tasking mapped to a pydcs task the airframe doesn't export — killing the whole
  mission for one flight. The data ships such claims: a fleet audit found **21 (airframe,
  task) pairs** across 13 airframes, all upstream or mod-registration data the fork
  deliberately mirrors (Tu-160 `DEAD`/`BAI` → pydcs has only Pinpoint Strike, re-added by
  upstream #451 and restored by re-convergence E; SA 342/Gazelle `CSAR` → no Transport;
  A-4E/J-7B/L-39ZA/MiG-21bis `Fighter sweep`; F4U-1D/F9F/MiG-21MF `OCA/Runway`; OH-6A's
  whole ground-attack set; Su-24MR `BARCAP`; F-8E(FN) `Strike`/`Armed Recon`). Reproduced
  live: Mozdok-to-Maykop's auto-planned blue ATO handed a Tu-160 squadron DEAD and every
  generation crashed. Fix: the terminal raise becomes the same `task_default` degrade the
  method already granted client flights — the group task is only the AI's coarse role and
  the waypoint tasks carry the real mission, so the flight generates with a logged warning
  (Tu-160 DEAD flies as role "Pinpoint Strike", which is what a cruise-missile bomber
  servicing a SAM site is). Upstream's curated preferred/fallback chains are untouched.
  Upstream-shared defect; carve candidate post-freeze. Lock test
  `tests/test_aircraft_task_generation.py` walks every claimed pair (2,176) through the
  real `configure_task` and pins the Tu-160 degrade; its `TASK_MAPPING` mirrors
  `apply_to`'s dispatch — update both together.

- **A CSAR flight the AI cannot fly took the whole turn down (fixed 2026-08-17).** The quoted
  message now reads `CSAR pickups are only usable by helicopters`, and since 2026-08-26 a
  fixed-wing CSAR flight dispatches to `KingFlightPlan` and never reaches that raise at all —
  the auto-planner gate below is what still keeps the King out of the ATO.
  `PlanningError: CSAR is only usable by helicopters` came out of
  `packagefulfiller.plan_mission` → `pass_turn` → the UI: the campaign could not be
  advanced at all (flown 2026-08-16, 5th test). The C-130J declares `CSAR` so the King can
  be **flown by a player** as the on-scene commander it always was, and
  `tests/test_csar_king_priority.py` already pinned it to the lowest CSAR number in the
  fleet — but priority only orders the candidates. `best_squadrons_for` returns whatever it
  finds, so when the King's squadron is the only CSAR squadron in range it wins by default
  however low its number is, and `CsarFlightPlan` then refuses to build (the DCS AI `Land`
  task is helicopter-only). Two fixes, at different levels. `FlightType.requires_helicopter`
  makes it a capability fact, checked in `Squadron.can_auto_assign_mission` — auto-planning
  only, so a player may still frag a King by hand, which is the point of the yaml override.
  And `plan_mission` now catches `PlanningError` around `recreate_flight_plan`, releases the
  planned aircraft and scrubs that one mission: an unbuildable flight plan is one lost
  package, not a lost campaign. This is checklist row **B50** failing in the worst
  available way.

### Debrief and reporting

- **Destroyed strike targets never reaching the campaign — the results commit used a stale
  snapshot (fixed 2026-08-16).** The long-standing "I bombed it and it did not register"
  complaint. `PollDebriefingFileThread` breaks out of its loop the first time it reads a
  `state.json` carrying `mission_ended`, and its only staleness guard is an mtime newer than
  the current `.miz` — which an **aborted run of that same mission** satisfies. The results
  window then committed `self.debriefing`, whatever the watcher last delivered. Flown
  2026-08-16: the player aborted a ~100-second run, the watcher consumed that file and stopped
  at 14:05:24, the real 49-minute sortie followed, and at 14:58:41 the turn committed the
  two-minute snapshot. Three Tuapse dock buildings (`TARANTULA`) were destroyed, recorded by
  zone name in the final `state.json`, and still standing in the save. **Not a scenery-tracking
  defect** — rebuilding a `Debriefing` from that same file credits all three and committing it
  flips them dead, which is what proves the snapshot was the culprit. Fix:
  `game/finaldebriefing.py` re-reads `state.json` at commit time and uses it when it carries
  more recorded events, keeping the polled one if the fresh read is shorter (partial write, or
  a file already replaced). Map-independent. Also drops empty names in `clean_unit_list` (the
  flown file had 4), which only inflated the untracked count. Full forensics in
  `docs/dev/design/retlab-scenery-kill-tracking-notes.md` §0. Tests
  `tests/test_final_debriefing.py`. Upstream-shared; carve candidate post-freeze.

- **A building objective sharing its zone with indestructible scenery was never credited
  (fixed 2026-08-30).** Adopted from upstream
  [#957](https://github.com/dcs-retribution/dcs-retribution/pull/957) (juanjux), open not merged.
  The `MapObjectIsDead` trigger per white zone is true only once **every** map object in that
  polygon is dead, and many hold scenery with no destructible body — a `WOODPILE_01` reports a
  life of `1e38` — so those objectives read intact however often they were flattened. DCS does
  report the death, but `getName()` on scenery returns a numeric id, so the id went into
  `dead_events` and the debriefing, which resolves scenery by trigger-zone name, discarded it.
  Upstream measured one Kola mission at 978 scenery deaths, 15 of them direct hits on named
  objectives, with three objectives recording nothing across three turns while being levelled
  each time. Now `LuaGenerator._seed_scenery_objectives` emits every `SceneryUnit`'s name,
  position and alive state as `RETRIBUTION_SCENERY_ZONES`, and `dcs_retribution.lua` credits a
  numeric-named `S_EVENT_DEAD` to the nearest objective within **30 m** — a measured threshold
  (29 m hit, 31 m collateral), one-shot per zone, already-dead objectives seeded so the
  mission-start rubble replay cannot mis-credit a live neighbour. `generate_on_dead_trigger_rule`
  and its 342-per-mission triggers are deleted; unmatched scenery is dropped rather than
  appending a useless id, which also shrinks `state.json`. **This does not touch the fork's
  culling exemption** — that lives in `GroundObjectGenerator.generate`. Rationale, the answered
  objections and what stays open: `retlab-scenery-kill-tracking-notes.md` §8.6. In-game pass
  **B63**.

- **The Lua bridge dropped every scalar on a mixed item (fixed 2026-08-16).**
  `LuaData.serialize` branched either/or: `if self.objects:` emitted only the nested
  tables, `else:` only the key/values. An item holding **both** — the shape you get
  from `add_key_value(...)` followed by `add_item(...)` — silently lost all its
  scalars. Two emitters build that shape, and both were broken in every generated
  mission:
  - **§72 deck decor.** A carrier that received recovery-phase dressing emitted
    `{recoverySpawns = {...}}` and nothing else — no `group`, `unit`, `side`, `brc`
    or `clearNames`. The plugin armed ("1 boat(s), clear by 1500s"), called
    `Group.getByName("")`, hit the *boat gone* exit, set `cleared = true` and
    stopped. Silently: that exit had no log. Flown 2026-08-16 — a 103-minute
    Caucasus turn-1 sortie where the deck never respotted for recovery and the
    fallback timer, 25 minutes in, never fired. The exit now logs, because a deck
    that never respots is indistinguishable from a disabled feature.
  - **§89 reactive red.** `groups` (the reaction-flight pool) sits on the same item
    as the `objectives` table, so the pool was dropped from every mission — the
    plugin could arm on a watched objective and still have nothing to launch. The
    third emitter defect in this family after PR #842's two; unlike those, this one
    was in the shared serializer rather than the caller.
  Fix is in `LuaData.serialize` (scalars first, then nested), so it covers both and
  any future mixed item. Tests `tests/missiongenerator/test_luadata.py`, including
  the unmixed shapes to pin that the common path is untouched. Upstream-shared
  (`luagenerator.py` is upstream's); carve candidate post-freeze.

- **Kneeboard: the package table named the reader "Flight", and the targets map was unreadable
  (fixed 2026-08-17).** Four defects, all found by rendering the pages out of a flown Syria
  `.miz` rather than by flying it — the kneeboard is a PNG we generate, so what renders here is
  exactly what DCS shows, and **none of these needs an in-game pass**.
  1. **The reader's own row said `Flight`.** Every other row of the Support Info package table
     is a callsign (Enfield 8, Ford 7, Lobo 3, Python 5) and the page header already said
     "Colt 9", but `SupportPage.__init__` fell back to the literal string. Now the callsign,
     with `
(custom name)` appended exactly as the other rows do.
  2. **Labels printed on top of each other.** The placement loop stepped a colliding label
     *downward only* and gave up at the bottom edge **while still overlapping** — then drew it
     anyway, destroying both its own text and the one underneath. Flown: `DRAGONFLY` over
     `CRANE`, `King Abdullah II` over `Muwaffaq Salti`, both near the bottom of the map.
     Placement now tries right then left, and within each side steps down then **up**; if
     nothing is free the label is dropped rather than overprinted, because an overprint costs
     two labels instead of one.
  3. **Markers were drawn through labels.** Occupancy tracked labels but not the dots, so a
     package marker printed through the middle of `DOLPHIN`. Markers now go down in a pass of
     their own and seed the occupancy set before any text is placed.
  4. **A target that is also a control point was named twice** (`H3 Southwest`, once orange and
     once red). The base pass now skips a name the target pass already drew.
  Plus the map fills the page. It was sized to the area-of-interest aspect and centred, which
  letterboxed a wide, short theater into a middle band with ~390 px of dead page above and
  below. It now uses the full rectangle and lets `aspect_correct` grow the **world** extent
  instead — the padding lands on the non-binding axis, so the scale is unchanged and the area
  of interest occupies exactly the pixels it did before, with terrain where the blank was. The
  old comment was guarding against *shrinking* the map to fit both axes, which is a different
  operation. Tests `tests/missiongenerator/test_kneeboard_packages_map.py` (assert the rendered
  text calls, not internals) + `tests/test_airfield_directory_page.py`.
