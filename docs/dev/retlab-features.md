# RetLab features — deep dive

> Test paths shown ~~struck through~~ were deleted along with the feature they covered. They are left visible because the citation is part of the record; do not go looking for the file. Audited 2026-08-17.

The per-feature engineering internals for RetLab's additions on top of upstream
DCS Retribution. [`CLAUDE.md`](../../CLAUDE.md) is the clean map and points here; this
file is the deep version for the next coding session — file paths, hard-won gotchas,
tests, and the deferred work.

Design notes for individual features live under [`docs/dev/design/`](design/) and are
linked from each section below. Read those before touching the corresponding code.

---

## 1. QRA intercept reserve

Retribution now uses the upstream PR `#782` QRA path. The old RetLab ramp-scramble system
is legacy only and should not be extended.

- Squadron model: `game/squadrons/squadron.py` stores `intercept_reserve` per squadron.
  `untasked_aircraft` is now `owned_aircraft - intercept_reserve`, so the auto-planner
  leaves those aircraft available for QRA instead of fragging them.
- Reserve helpers: `game/squadrons/intercept_reserve.py` owns clamping, default seeding,
  live-campaign repropagation when coalition doctrine defaults change, and
  `qra_scramble_grouping()`.
- Distributed-QRA scramble size: `qra_scramble_grouping()` rolls **1 ship 75% / 2 ships
  25%** (`QRA_SINGLE_SHIP_PROBABILITY`) per fielded QRA squadron, carried on each
  `InterceptEntry.grouping` and applied as `SetSquadronGrouping` in `intercept-config.lua`
  (was a hardcoded 2-ship). Intent: many alert bases each putting up a *small* response so
  a raid draws interceptors from several directions, rather than one base scrambling a big
  formation. MOOSE grouping is per-squadron (fixed for the mission, re-rolled each turn),
  so the per-launch single/pair mix emerges across the theater's alert bases; true
  per-scramble variation would need a dispatcher GCI hook (deferred). Lua falls back to 2
  if an old save omits the field. Tests: `tests/squadrons/test_intercept_reserve.py`.
- Campaign doctrine: `game/settings/` exposes
  `ownfor_default_qra_reserve` and `opfor_default_qra_reserve` (the `qra_comms_enabled`
  dispatcher callouts were removed 2026-10-12).
  The radii are constants in `interceptluadata.py`, a **base-defense** posture (lowered
  after playtest feedback that QRA screened forward over the FLOT):
  `QRA_GCI_MAX_RADIUS_NM` **60** (was 100) and `QRA_ENGAGEMENT_RANGE_NM` **38** (was 60).
  The Lua fallbacks in `intercept-config.lua` match. They were settings until 2026-09-23;
  no campaign preseeded them.
- Mission generation: `game/missiongenerator/aircraft/aircraftgenerator.py`
  `spawn_intercept_templates()` emits late-activated parked template groups and
  appends `mission_data.intercept_entries`.
- Template spawn details: `game/missiongenerator/aircraft/flightgroupspawner.py`
  `create_intercept_template()` places the parked template and seeds
  `QRA_AIRSTART_SPEED_MS` onto its waypoints (en-route pace only).
- Air-spawn profile (2026-06-21): waypoint speed does NOT set the spawn-*instant*
  velocity — Moose air-spawns the cloned parking template at ~0 kt, so jets spawned
  stalled at altitude and dove ~4,600 ft clawing back airspeed (an Su-27 nearly hit
  the ground at Vaziani, Tacview 2026-06-20). `intercept-config.lua` now forces a real
  scramble speed via `SPAWN:InitSpeedKnots` (`SCRAMBLE_SPEED_KT`, applied to the
  spawned units in Moose `SpawnWithIndex`) and a terrain-relative LOW spawn altitude
  per base via `SetSquadronTakeoffInAirAltitude` (field elevation + `SCRAMBLE_AGL_M`),
  replacing the global absolute-MSL `SetDefaultTakeoffInAirAltitude` that was unsafe at
  high-elevation fields. Both are tunable; in-game pass ☑ VERIFIED 2026-06-24 (A1,
  Tacview) — scrambled MiG-29As air-spawned at ~750 m AGL / 240–510 kt and climbed
  under control, no stall or ground-clawing dive.
- Scramble stacking (2026-09-29, test 48): Moose air-starts every group on the same point
  over the field at the same altitude, so two scrambles in the same second overlap unit for
  unit. At Kerman two F-14 pairs launched together and the wingmen collided on spawn.
  `stack_air_spawns` wraps each squadron SPAWN so each scramble from a base within 60 s
  goes 150 m (~500 ft) higher, four levels, then wraps. Row B165.
- **Takeoff method — in-air, and the three that failed (all validated in-DCS).** Every
  ground spawn dies on a saturated ramp; the blocker is ground movement, not the takeoff
  method. Do **not** call `SetSquadronVisible` — it puts Moose in its `ParkDefender`
  branch, which hardcodes `SPAWN.Takeoff.Cold` and ignores `SetDefaultTakeoff*`, and it
  also clamps `ResourceCount` to free parking spots and forces `Grouping=1` (losing both
  the reserve and 2-ship flights). Non-visible `ParkingHot` scrambled warm but never
  taxied out of congested ramps (Tiyas, packed with OCA + ~30 rotary BARCAP) while the
  same code launched fine from uncluttered H3. `SetDefaultTakeoffFromRunway` had the same
  split — fine at H3, dumped into hangars at Tiyas. In-air is the only method that
  escapes the ground.
- **The Moose air-spawn monkeypatch, and when to drop it.** In-air spawn was blocked by a
  Moose bug: `BASE:CreateEventTakeoff` is mis-scheduled, so `self` arrives as a plain
  table, `self:F()` crashes and defenders never activate. `intercept-config.lua`
  monkeypatches `BASE.CreateEventTakeoff` rather than editing the vendored `Moose.lua`.
  Filed upstream as **MOOSE PR #2595** (`Core/Spawn.lua`: pass the args as varargs, not a
  single table). **Delete the monkeypatch once that lands in the vendored `Moose.lua`.**
- `SetSquadronGci` speed arguments are **km/h**, not m/s — Moose's `WaypointAir` divides
  by 3.6. 900/1200 km/h ≈ 485/648 kt.
- Lua/config path: `game/missiongenerator/interceptluadata.py` populates
  `dcsRetribution.Intercept`, and `resources/plugins/intercept/intercept-config.lua`
  instantiates Moose `AI_A2A_DISPATCHER` behavior from that table.
- Results/debrief: `resources/plugins/base/dcs_retribution.lua` writes
  `intercept_survivors`; `game/debriefing.py` and
  `game/sim/missionresultsprocessor.py` reconcile those survivor counts back into
  squadron aircraft and pilot losses.
- UI touchpoints: QRA reserve editing and display now live in
  `qt_ui/windows/AirWingConfigurationDialog.py`,
  `qt_ui/windows/SquadronDialog.py`,
  `qt_ui/windows/basemenu/airfield/QAircraftRecruitmentMenu.py`,
  `qt_ui/windows/basemenu/QBaseMenu2.py`, and the debrief/settings windows.

### Player-manned QRA (2026-06-29)

A human pilot can man part of a squadron's QRA reserve instead of leaving it all to the AI
dispatcher (design note `docs/dev/design/retlab-qra-player-manning-notes.md`; in-game pass A3).
The AI QRA is a runtime MOOSE air-spawn with no ATO flight to take a slot on, so the player
share is fragged as a **real ATO flight** at planning instead — a cold-start, home-field
base-defense BARCAP the player sits on the pad and scrambles at will.

- Model: `Squadron.qra_player_manned` (per squadron, default 0, `__setstate__` migrates old
  saves) records how many of `intercept_reserve` the player flies. It only re-labels reserve
  airframes — `untasked_aircraft` already excludes the whole reserve, so the planner pool is
  untouched.
- Accounting (`game/squadrons/intercept_reserve.py`): `qra_player_manned_count()` clamps the
  setting to the reserve and owned airframes; `ai_qra_resource_count()` carves the manned
  airframes out of both the reserve and owned pool before the usual `qra_resource_count`
  clamp, so the AI dispatcher fields only the player's leftovers (no double-spawn). The
  available-pilot cap is *not* re-reduced — the alert flight already claimed its pilots at
  planning. Both the generator and the debrief baseline call `ai_qra_resource_count` so the
  AI count and its loss reconciliation always agree. Tests in
  `tests/squadrons/test_intercept_reserve.py`.
- Home-field orbit: `HomeBaseDefenseZone` (`game/theater/missiontarget.py`) is the package
  target; `CapBuilder.cap_racetrack_for_objective` (`game/ato/flightplans/capbuilder.py`) lays
  a short racetrack **straddling the base** (oriented toward the nearest enemy field) instead
  of pushing forward like a control-point BARCAP.
- Generation hook: `Coalition._plan_player_qra()` (`game/coalition.py`), called from
  `plan_missions` **BLUE only** after scheduling, frags one `HomeBaseDefenseZone` BARCAP
  package per eligible squadron (airfield-based, BARCAP-capable, flyable) with `manned`
  cold-start airframes, `claim_inv=False` (the airframes come from the reserve, not the
  untasked pool), every member marked a player slot, a normal flight plan + ASAP TOT. Because
  it's a real ATO flight it gets the full loadout/kneeboard/debrief treatment and is editable.
- Dispatcher debit: `spawn_intercept_templates()` now seeds the `InterceptEntry.resource_count`
  from `ai_qra_resource_count`, so the runtime dispatcher launches the reserve minus the
  player's share.
- UI: a dependent "…of which player-manned" spinbox under the QRA reserve in
  `qt_ui/windows/SquadronDialog.py`, bounded by the reserve and synced when it changes.
- Scramble cue (Phase 3): `spawn_intercept_templates` also emits a `PlayerAlertEntry`
  (`game/missiongenerator/interceptluadata.py`, `dcsRetribution.Intercept.PLAYER_ALERT`) per
  blue manned base; `resources/plugins/intercept/intercept-config.lua` runs a periodic scan
  that calls the player to scramble (`outTextForCoalition`, "QRA SCRAMBLE — base: bandits
  BRG/range, angels N") when a hostile aircraft closes inside the **cue radius** = the AI GCI
  radius **+ `PLAYER_SCRAMBLE_LEAD_NM`** (default 30 NM), so a cold start has spool-up + taxi
  time. Player-facing only — it never launches anything; the human decides. Debounced per base
  (`PLAYER_ALERT_REPEAT`). In-game pass DONE (A4).
- AI-wingman crewing: `Squadron.qra_player_ai_wingman` (default False) flips how the alert
  flight is crewed without touching its size or the dispatcher debit —
  `qra_player_client_slots()` returns the whole flight (every airframe a client slot, co-op
  alert) when off, or just the lead (rest fly as AI wingmen, single-player section) when on.
  `Coalition._plan_player_qra` marks `member.pilot.player` per slot accordingly. UI: a "Fly
  lead, rest are AI wingmen" checkbox under the spinbox.
- Runtime (cold alert spawn + flight plan + scramble cue) **verified in-game 2026-07-01** (checklist
  A3/A4 — user pass "A3/A4 good").

Legacy note: the old ramp-scramble system has been fully retired — the upstream PR #782
dispatcher above is the only live QRA path. Both the `reactive_scramble.lua` script and the
`FlightType.SCRAMBLE` enum (plus its `Scramble:` aircraft-task weights and `- Scramble`
squadron mission-type entries in `resources/units|squadrons|campaigns/*.yaml`) have been
removed. SCRAMBLE always behaved as a BARCAP, so old saves are migrated SCRAMBLE -> BARCAP
in one place: `FlightType._missing_`'s `_LEGACY_FLIGHT_TYPE_VALUES` table (runtime lookups);
the unpickler (`persistency.py` `_handle_flight_type`) routes legacy values through
`FlightType(value)` → `_missing_`, so it no longer duplicates the remap.
`FlightType.INTERCEPTION` is the only remaining legacy A2A type and is kept for upstream save
compatibility.

### QRA forward defense — rear bases answer raids at the front (2026-07-09)

`qra_forward_defense` (Air Doctrine → Air defense & QRA, **default ON**; the kill switch) +
`QRA_DEFENSE_DEPTH_NM` (60, `interceptluadata.py`; a setting until 2026-09-23). Checklist **A5**.

The problem: `SetGciRadius` is **one radius per coalition, measured from every base**
(`AirbaseDistance <= self.GciRadius`, Moose's GCI loop). At the stock 60 NM a rear field never
scrambles for a raid at the front — on Red Tide, five of red's six fighter squadrons sit 126–290 NM
from Haina, so 20 of red's 24 alert airframes only ever defended Berlin. But simply widening the
radius so Sperenberg reaches Haina *also* lets Haina's own alert chase 200 NM the other way, deep
into blue.

The two are separated by giving each dispatcher a **border zone**:

- **`SetBorderZone(zones)` → `Detection:SetAcceptZones(zones)`.** Moose drops any detected object
  outside every accept zone, so the dispatcher cannot see — cannot scramble against, cannot keep
  engaging — a target beyond the defended airspace. This decides **where** a side may fight.
- **`SetGciRadius`** then decides only **how far a base will launch** to get there, and opens to
  `QRA_FORWARD_REACH_NM` (200). Safe, because geography is now bounded independently.
- **`SetDisengageRadius`** must open with it (`reach + engage + DISENGAGE_MARGIN_NM`): Moose aborts a
  defender once `DistanceFromHomeBase > DisengageRadius` (default 300 km ≈ 162 NM), so a base at the
  far edge of its reach would otherwise launch and turn around mid-transit. This is the non-obvious
  half — without it the feature silently does nothing for the farther fields.

**A raid draws at most 4 defenders** (`MAX_DEFENDERS_PER_RAID`, 2026-10-18, test 62). Moose's GCI
loop keeps the squadron with the shortest *intercept* distance among those inside `GciRadius`, and
reaches back to a farther one once the closer squadron's alert is spent — an echelon: the front field
answers, the rear fields backfill. Moose sizes the launch at one defender per attacker in the
detected cluster, escorts included, so without the cap a wide reach does mass-launch (see below).

Zones are built by `defense_zone_entries` (`interceptluadata.py`): one circle per non-neutral,
non-`OffMapSpawn` control point, radius `qra_defense_depth_nm`; a CP anchoring an active front is
**grown to `distance(cp, front) + FRONT_FORWARD_MARGIN_NM` (25 NM)** so the contested airspace is
always defended however far back the anchor sits. That margin is the *only* place a side's airspace
crosses the line. Emitted per coalition under `dcsRetribution.Intercept.ZONES`; an empty bucket ⇒ the
Lua skips `SetBorderZone` ⇒ pre-feature behaviour.

Non-regressive by construction: with `depth == QRA_GCI_MAX_RADIUS_NM` (both 60), the set of
raids that used to trigger a GCI (within that radius of *some* base) is exactly the union of the
circles.

Interactions: **an ambush doctrine wins outright** — `dispatcher_tuning` returns the Vietnam W5 radii
unchanged and `disengage_nm = 0`, because the late, close GCI slash is the whole point of that
posture and forward defense must not widen it. The **player scramble cue** keeps the narrow radius
(`min(tuning.scramble_nm, setting)`), since the human's alert flight defends its own field — cueing
it for a raid 200 NM away would be constant false alarms, and `min` also preserves the ambush
doctrine's *shrunk* cue.

Red Tide, verified against a live save: red's airspace covers Haina, the FLOT and Fulda (42 NM, the
blue front base) but excludes Frankfurt (94 NM), Hahn, Spangdahlem and Ramstein; the 200 NM reach
brings Sperenberg/Schonefeld/Wittstock/Hamburg/Templin while Peenemunde (226) and Kastrup (290) stay
home. Tests: `tests/missiongenerator/test_qra_defense_zones.py`,
`tests/missiongenerator/test_interceptluadata.py`, `tests/test_vietnam_doctrine.py`.

### GCI-ambush posture (Vietnam campaign layer W5)

The Vietnam adaptation of the QRA dispatcher (will-note §6; checklist **M5**). `Doctrine.gci_ambush`
(True only on `VIETNAM_DOCTRINE`) flips a side's dispatcher from the modern stand-and-fight duel to the
era's GCI hit-and-run:

- **Python** (`dispatcher_tuning` in `game/missiongenerator/interceptluadata.py`, called per side in
  `spawn_intercept_templates`): the engage radius shrinks to the doctrine's `cap_engagement_range`
  (22 NM — the P1c close-fight number) and the scramble (GCI) radius caps at `AMBUSH_GCI_RADIUS_NM`
  (40 NM) so the MiGs launch **late** and slash the strike package near its target instead of meeting
  the sweep at the border. A tighter user setting always wins (min). The `ambush` flag rides each
  `InterceptEntry` (`ambushPosture` in the Lua table).
- **Lua** (`intercept-config.lua`): an ambush coalition's dispatcher gets the hit-and-run leash —
  `SetDisengageRadius(50 NM)` (Moose aborts the engagement when the defender is that far from home) and
  `SetDefaultFuelThreshold(0.35)` (one slash, then RTB to re-arm) versus Moose's 162 NM / 0.15 defaults.
- **Sanctuary basing** rode the W4 restricted zones (an airfield inside an active zone couldn't be OCA'd), which were REMOVED 2026-07-21 with §40; the GCI-ambush posture itself (the late scramble + hit-and-run leash) is unaffected.
- Symmetric by doctrine (a Vietnam-doctrine blue side gets the same posture); every other doctrine
  passes the QRA settings through untouched (test-locked in `tests/test_vietnam_doctrine.py` +
  `tests/missiongenerator/test_interceptluadata.py`).

### Upstream PR #782 drift port (2026-07-16)

Four upstream fixes the fork's QRA had drifted behind, ported with the fork couplings intact:

- **EWR detection-prefix escape** (upstream `861829b2`): Moose `SET_GROUP:FilterPrefixes`
  matches names with Lua-pattern semantics (`string.find`, only `-` pre-escaped), and every
  Retribution IADS group name carries parens (`"0041 | LION (EWR)"`) that read as pattern
  captures — so the wide-area EWR half of QRA detection matched **zero** groups and the
  dispatchers were detecting on the paren-free `QRA_Backstop_*` base EWRs **only**.
  `intercept-config.lua` now escapes the `detection_prefixes` list with the same `gsub` the
  fork already proved in the (since removed) MANTIS bridge's `escape_prefix` (everything except `-`, which
  Moose's own gsub handles). This expanded real detection from base-local backstops to the
  whole IADS EWR network — fold verifying it into the A5 forward-defense fly. Pinned in
  `tests/lua/test_intercept_filter.py` (the plugin's chunk-return test hook + a recording
  MOOSE fake). (The backstops themselves are gone as of 2026-08-06 — see below — so the
  escape is now the *only* thing standing between the dispatcher and an empty detection set.)
- **The per-base backstop EWR is removed** (2026-08-06, flown Red Tide at Sperenberg: *"the
  QRA invisible EWR is offset from the runway and causing collision issues on the taxiways"*).
  The fork spawned a "hidden/invisible/immortal" EWR at every alert base with `mist.dynAdd`,
  at the **airbase reference point + 300 m NE**, so QRA had a guaranteed detection source even
  with the IADS network dead. The premise is unachievable: **DCS has no non-colliding ground
  unit.** mist's `hidden` only suppresses the F10 map symbol, and `SetCommandInvisible` only
  blinds the AI's *sensors* — the model and its collision box remain. A `55G6 EWR` is a large
  lattice mast, and 300 m NE of a reference point lands squarely in the taxiway/apron network
  of a real field, where AI taxi routing has no way around it. **Upstream PR #782 deleted the
  same mechanism for the same reason** — its header reads *"we no longer spawn a per-base
  backstop EWR, which DCS placed on runways/taxiways at the airbase reference point and broke
  AI taxi routing"* — so the fork adopts upstream's shape rather than inventing a third
  placement rule (any scheme that puts an object on an operating airfield has this bug; moving
  it far enough away to be safe is just the IADS network with extra steps).
  Detection is now the IADS `Ewr`/`SamAsEwr` network alone. `ewr_group_names` was already
  present and already the primary source, so the change is a **pure subtraction**: the
  `spawn_backstop_ewr` + `protect_group` helpers, the per-base spawn loop, and the merge of
  `backstop_names` into `detection_prefixes` are gone, along with `DEFAULT_BACKSTOP_EWR_TYPE`,
  `InterceptEntry.backstop_ewr_type`, `InterceptEntry.country_id` and the `backstopEwrType` /
  `countryId` emits (upstream emits neither — both existed solely to feed the backstop).
  **The by-design consequence, accepted upstream and here: a coalition whose EWR/SAM-as-EWR
  network is wiped out loses GCI detection and stops scrambling** — no radar, no GCI. With no
  detection source the plugin logs and builds no dispatcher rather than erroring.
  **Since 2026-10-11 the side's own AWACS counts as a detection source** (DM call after
  test 55): `ewr_group_names` appends each `dcsRetribution.AWACs` group of the dispatcher's
  coalition. Test 55's blue had two E-2Cs and no ground radar, logged `no detection sources
  for BLUE`, and its eight alert jets at Vaziani could not scramble. A side with neither a
  radar nor an AWACS still stops scrambling. Row B222. Runtime +
  generation only, so **existing saves are fixed by the next regeneration** — no new game.
  Tests: `tests/lua/test_intercept_filter.py` gained a `mist.dynAdd` recorder asserting the
  plugin spawns **nothing** and a wiped-out-network case asserting it builds no dispatcher and
  raises no error; `tests/missiongenerator/test_interceptluadata.py` pins that neither
  `backstopEwrType` nor `countryId` is ever emitted again.
- **React-task filter** (upstream `5e565bb5` + `f0bd1b63`): the dispatcher no longer
  scrambles against ANY airborne enemy — each per-coalition dispatcher's
  `EvaluateGCI`/`EvaluateENGAGE` is wrapped to skip a detection cluster with no
  air-to-ground member. React list (final): **Strike, BAI, OCA/Runway, OCA/Aircraft,
  Anti-ship, Armed Recon** — NO DEAD, NO Air Assault; CAP/sweep/escort/SEAD/CAS/support
  are ignored. The task is parsed from the namegen group name's first `|`-field
  (suffix-match `" "..task`), so non-ATO enemy air never reacts. A cluster reacts if ANY
  member is a react type (escorted strikes still trigger). `next_aircraft_name`
  (`game/naming.py`) now appends the flight type for custom-named flights too, so they
  stay classifiable (`tests/test_naming.py`). The §1 player-manned **PLAYER_ALERT cue
  stays deliberately task-blind** — it informs; the human judges whether a closing sweep
  is worth scrambling for.
- **Live reserve accounting** (upstream `55b26078` + `fdd90469` + `0e1184df`): editing a
  squadron's QRA reserve now updates `untasked_aircraft` immediately via
  `Squadron.set_intercept_reserve` (delta-adjust, floored at 0, capped at
  `owned - new_reserve` so attrition can't inflate the pool), routed through ALL FIVE
  writers (SquadronDialog, QAircraftRecruitmentMenu, `AirWing.repropagate_qra_reserve`,
  AirWingConfigurationDialog `update_max_size` + `apply`); the SquadronDialog and
  base-menu QRA spinners cap at `max_intercept_reserve` (= untasked + reserve, the
  unplanned airframes). Fork coupling: `set_intercept_reserve`
  re-clamps `qra_player_manned` to the new reserve so lowering the reserve can't leave a
  phantom manned alert flight. (The former §53 `fuel_readiness` clamp on the pool was removed
  2026-07-21 with the war economy.) Tests merged into
  `tests/squadrons/test_intercept_reserve.py` / `test_squadron_inventory.py` /
  `test_airwing_qra_propagation.py`.
- **Cratered-runway gate** (upstream `edb14d94`): `spawn_intercept_templates` skips a
  control point whose `runway_is_operational()` is false (no QRA templates, no
  `InterceptEntry`, and — correctly — no §1 `PlayerAlertEntry` cue); the base card's
  "QRA alert" count reads 0 while the runway is down. Suppression lifts when the runway
  repairs. Accepted limitation: `Coalition._plan_player_qra` is deliberately unguarded —
  the `generate_flights` runway check already stops the alert flight spawning, so the
  residual is a phantom package in the planning UI only.
- **Alert templates carry the BARCAP fit (2026-10-12, test 56).** The AI alert template
  and the §61 host-scramble template are built by
  `FlightGroupSpawner.create_intercept_template`, which never passes through
  `FlightGroupConfigurator`, so each kept the payload pydcs picks for the type's default
  task (`maintask=None`). In test 56 that was four inert practice bombs and a captive
  Sidewinder on the F-15E pair, two AIM-9X on the F-22 pair, two PL-5 on the JF-17s and
  empty pylons on the Mirage F1s; every scramble clone copies the template.
  `_arm_alert_template` now loads each unit with its flight member's loadout (the
  squadron's BARCAP preset), degraded for the campaign date
  when `restrict_weapons_by_date` is on. An airframe with no BARCAP preset keeps the
  pydcs default. The template's DCS task is unchanged. Tests:
  `tests/missiongenerator/test_alert_template_loadout.py`. Row **B227**.
- **Alert templates wear the squadron's paint (2026-10-18, test 62).** For the same reason
  (no `FlightGroupConfigurator`), the alert and §61 templates were never painted: Israeli
  and Turkish alert F-16s and F-4Es launched in stock paint. Both now run `AircraftPainter`
  after the board numbers, as a fragged flight does. Checked on Brady's Anatolian Reach
  save: every alert template carries its squadron's livery. Test:
  `tests/missiongenerator/test_alert_template_paint.py`. Row **B246**.
- **A shot-down alert jet is not handed back to the pool (2026-10-12, test 56).** Red's
  JF-17 alert squadron launched 8 single-ship jets from a reserve of 4. The plugin sets
  `SetDefaultLandingAtEngineShutdown`, so Moose's `OnEventEngineShutdown` returns a
  defender to the squadron when `not DefenderUnit:InAir()`. DCS raised engine-shutdown
  for four of the jets milliseconds after they were killed, with the Unit already gone;
  `UNIT:InAir()` is `nil` then, the test passed, and `RemoveDefenderFromSquadron` put
  each back (`ResourceCount + 1`). The next 30 s detection cycle launched it again.
  `debrief.log` shows each relaunch 20 to 30 s after one of those events. The plugin now
  wraps that handler per dispatcher and passes the event on only when `InAir()` is
  exactly `false`. A real landing is unchanged. Grouping 1 is the worst case; in a pair
  only the last jet to die was credited. Upstream MOOSE has the same handler and has
  since deleted the class.
- **A base's second alert squadron launches when the first is spent (2026-10-12, test
  56).** Kirkuk held a JF-17 and a MiG-29 alert squadron, 4 jets each; the MiG-29s never
  launched. Moose's `onafterGCI` picks the squadron nearest the intercept point without
  reading `ResourceCount`, two squadrons at one base tie and the first in `pairs` order
  wins, and when `CanGCI` then refuses the empty pick the loop breaks instead of trying
  another. The plugin wraps `onafterGCI` per dispatcher: for the length of the call it
  takes the `Gci` table off every squadron with `ResourceCount <= 0` or `Captured`, so
  the pick falls to one that can launch, then puts it back (also when Moose raises). A
  pick that takes a squadron's last jet still stops there; the next 30 s detection cycle
  asks again and reaches the other squadron. Tests for both:
  `tests/lua/test_intercept_filter.py`. Row **B228**.
- **One raid draws at most 4 alert jets (2026-10-18, test 62).** Anatolian Reach: red
  launched 32 alert jets from 10 of its 13 squadrons in 15 minutes. Moose's `EvaluateGCI`
  asks for `attackers - engaged` defenders, a 30 km `DETECTION_AREAS` cluster counts a
  package's escorts and SEAD as attackers, and the spent-squadron hiding above lets every
  30 s cycle reach the next base inside the 200 NM `GciRadius`. The plugin's `EvaluateGCI`
  wrap recounts against `min(attackers, MAX_DEFENDERS_PER_RAID)` (4, Brady's pick); the
  reach stays 200 NM. A defender lost or sent home drops out of `engaged` and is replaced up
  to the cap. Test: `tests/lua/test_intercept_filter.py`. Row **B251**.

---

## 2. JAMMING flight type — C-130J EW/ISR

A ~1,950-line script (`c130j_mission_systems.lua`) turning the C-130J into an
EC-130H Compass Call (EW) + RC-130H Rivet Joint (ISR) platform. EW: area,
directional, and spot jamming, plus range-banded per-tick missile spoofing (with
a ~3 nm arming distance so it never spoofs a missile still next to its launcher).
ISR: altitude-gated radar detection, up to 3 simultaneous ELINT tracks with
progressive lock (60-360 s by range), F10 map marks, Bullseye reporting, and an
ELINT-Lock coalition alert. COORD: an EW/ISR handoff brief deliverable to any
selected friendly group.

- Enum: `game/ato/flighttype.py` (`FlightType.JAMMING` ->
  `AirEntity.ELECTRONIC_COMBAT_JAMMER`).
- Behavior: `game/missiongenerator/aircraft/aircraftbehavior.py` `configure_jamming()`
  -- AWACS task + `AewcFlightPlan` standoff racetrack outside the threat zone +
  `WEAPON_HOLD` ROE. Runtime EW/ISR is driven by the Lua, not the planner.
- Spawn fallback: `game/missiongenerator/aircraft/flightgroupspawner.py` tries RUNWAY
  start when no parking is available.
- Script loading: registered as a normal plugin (`c130j` in `plugins.json`,
  `scriptsWorkOrders` in `resources/plugins/c130j/plugin.json`) since the
  2026-06-11 refactor.
- Plugin script: `resources/plugins/c130j/c130j_mission_systems.lua` (+ `plugin.json`).
- Loadout/package wiring: `game/ato/loadouts.py`, `game/ato/package.py`,
  `game/theater/missiontarget.py`.
- Design note: `docs/dev/design/retlab-c130-ew-isr-notes.md`.

**Retired generic EW plugin:** the old `ewrj` / "EW Jammer Script 2.1" plugin
was removed. The C-130J JAMMING flight supersedes it for the RetLab scripted EW.
Do not re-add `ewrj` to `resources/plugins/plugins.json` or restore the old
`EWJamming` / `startEWjamm` / `startIAdefjamming` Python hooks. F-16/A-10 ECM
pods should not create the old generic F10 "Jammer menu"; only the C-130J
Mission Systems plugin owns RetLab scripted jamming now. Legacy saved `ewrj`
settings are purged on load in `game/settings/migration.py`. **In-game pass ☑ VERIFIED
2026-06-25** (G5): no generic Jammer F10 menu on fighters, no `ewrj`/`EWJamming`/`startEWjamm`/
`startIAdefjamming` in the generated mission.

**C-130 EW hard constraints (carried over from the standalone ME script):** suppression is
ROE WEAPON_HOLD, not emissions (the old "`enableEmission` crashes DCS" rule was lifted
2026-09-28, see `retlab-skynet-return-notes.md` §6; changing this is its own call); the burn-through model intentionally RAISES jam probability with distance; spot
jamming has flat altitude-independent range; the missile-spoof curve is intentionally steep
at close range. Don't "fix" these.

**IADS-engine compatibility:** every SAM-state write the jammer makes is
funnelled through two helpers — `suppressSAMRoe()` / `restoreSAMRoe()` — which touch **only**
the group ROE (`WEAPON_HOLD` to jam, `OPEN_FIRE` to un-jam) and never `ALARM_STATE` or
emissions. The script makes **no `mist.*` calls**. Under **Skynet** (the engine again since
2026-09-12) the engine re-asserts ROE itself, so the writes stay self-healing; under the
2026-06 to 2026-09 MANTIS bridge the `OPEN_FIRE` restore was the only thing that lifted the
hold. The one regression to avoid is adding any `ALARM_STATE`/emission write to the jammer —
that fights whichever engine owns the radar. See the design note's "IADS engine interaction"
section.

**`perf_red_alert_state` removed (2026-06-27):** because the IADS engine sets each
networked SAM's `ALARM_STATE` at runtime, the legacy global "SAM starts in red alert mode" toggle
only fought the engine — it wrote `OptAlarmState(RED/GREEN)` at spawn, which the engine immediately
overrode (the log even shows `Setting SAM Start States`), so flipping it changed nothing for
networked SAMs and confused players (it looked like the SAMs ignored "red alert"). The setting and
both its writers (`tgogenerator.set_alarm_state`, `flotgenerator`) are removed; **non-IADS** ground
groups (frontline armor, ships, autonomous SHORAD, any unmatched SAM) now fall to DCS `AUTO`. Old
saves drop the field via `_migrate_legacy_settings`.

---

## 3. Recon intel fog (was: TARPS photo-reconnaissance + BDA fog-of-war)

### The 2026-08-18 rework — engagement reveals, and reveals completely

**Read this before anything below it.** Most of this section documents the model that
was replaced; it is kept for reading old notes and saves. The rules that hold now:

| | Before | Now |
|---|---|---|
| What lifts a site's fog | struck, overflown by an offensive sortie, **or scouted by recon/TARPS** | struck, or overflown by any ground-attack sortie. Recon reveals **only** hidden command posts. |
| After the fog lifts | composition known, but damage still lagged behind a recon pass (`alive_at_last_recon`) | total ground truth, permanently — damage included |
| Un-engaged field forces | dashed "suspected activity" circle offset from the true position | exact marker; only composition is fogged |
| Decoy circles (§79) | optional fake contacts | removed |

**Fixed SAM sites are always known (2026-09-29, DM call).** SA-2, SA-3, SA-5, SA-10/20, S-400, Patriot and Hawk sites
report `KNOWN` for every viewer from turn one, map and §74 DTC rings alike. The rule is
`TheaterGroundObject.is_fixed_sam_site`, keyed on the fire-control radar or launcher type id
(`_FIXED_SAM_TYPE_PREFIXES`); the mobile S-300V, SA-6, SA-11 and SHORAD stay fogged. It is
computed, not stored, so it applies to existing saves too. A test checks every prefix
matches a real pydcs id. Row B176.

**Vacuum reveals (2026-10-22, Brady's call).** A red site whose radar a §118 Vacuum heard is
`discovered_by_player` after the turn, contents and rings included, like an engaged site
(`MissionResultsProcessor.reveal_vacuum_fixes`). The map marker was exact already. Row B273.

The DM's call, verbatim: *"Hidden until scouted is wrong, it should be hidden until
struck, then you should be omniscient like it was before we touched any fog of war
setting."*

What went, concretely:

- **The BDA damage lag.** `TheaterUnit.alive_at_last_recon`, `sync_confirmed_status`
  (unit/group/TGO), `alive_for()`, and `MissionResultsProcessor.update_confirmed_bda`
  are all deleted. Every accessor that only took a `viewer` to serve that lag lost the
  parameter: `alive_units`, `alive_unit_count`, `is_dead`, `dead_units`,
  `display_name`/`short_name` (the `_for` twins are gone), `threat_range`,
  `detection_range`, `max_threat_range`, `max_detection_range`, `sidc_status`. The
  `has_factory_for` / `ammo_depot_count_for` / `active_ammo_depots_count_for` twins on
  `ControlPoint` went with them — they were identical to the truth versions.
- **The category concealment.** `concealed_enemy_forces` and the `_concealed_radius`
  category branch (armor / missile / mobile-SAM) in `game/server/tgos/models.py`.
  `FIELD_FORCE_RADIUS_M` and `_CONCEALABLE_SAM_TASKS` went with it.
- **Recon as a reveal key.** `reconned_tgos_this_turn`, `_reconned_tgos_from_ato` and
  `tars_reconned_tgos` in `missionresultsprocessor.py`. The `tars_recon_captures`
  debrief channel and the `recon` plugin that wrote it were removed on 2026-08-20, once
  it was clear nothing had consumed a capture since this rework (see §12).

**One leak this opened, fixed 2026-08-19.** Collapsing `sidc_status_for(viewer)` into a plain
property left `sidc_for(viewer)` shipping the **operational-condition digit** as ground truth —
and milsymbol draws that digit as the bar under the map icon, so every un-engaged air-defence
site advertised itself as fully capable (and a destroyed one as destroyed). `sidc_for` now falls
back to `Status.PRESENT` when `known_for(viewer)` is False. Pinned by
`test_the_map_symbol_does_not_leak_condition_while_fogged`. The other client-facing fields
(`units`, `threat_ranges`, `detection_ranges`, `dead`) were gated correctly throughout; `task`
and `category` are shown on purpose (the air-defence band is not fogged), and a TGO's `name`
comes from the campaign author's own miz marker.

What stayed viewer-aware: `visibility_for` / `known_for` / `hidden_on_player_map`
(composition fog + the `scar_command_post_intel` command-post hiding),
`standard_identity_for` (COIN's suspect-until-engaged
symbol), and the fog-overview reveal toggle (§18), which now short-circuits two leaves
instead of three. COIN's intrinsic `concealed` flag is untouched — localizing an IED or
an HVT convoy is the point of those features and has nothing to do with §3.

Because `attacked_tgos_this_turn` is now the *only* non-kill reveal for an ordinary site,
its flight-type set was widened from `{STRIKE, DEAD, SEAD, ANTISHIP}` to every ground-attack
task (`+ SEAD_SWEEP, SEAD_ESCORT, BAI, CAS, ARMED_RECON`). A task missing from that set would
be a site the player could never learn about short of destroying it.

#### Recon's one remaining job: the command posts

`reveal_scouted_command_posts` (same file) is the single exception, and it exists because the
rework opened a hole. Enemy command posts are hidden from the map **outright**
(`hidden_on_player_map`, gated `scar_command_post_intel`), and `_command_post_revealed()` keys
on `captured_commander or discovered_by_player`. Both had become dead ends for a hand-planner:
`captured_commander` is **never set True anywhere in the tree** (the capture mechanic went
2026-07-01, only the flag survived), and `discovered_by_player` now needs engagement — which
you cannot frag at a target with no marker. The only surviving path was the auto-planner,
which enumerates strike targets on ground truth (`ObjectiveFinder.strike_targets`,
`viewer=None`) and will happily frag at a post the player cannot see. So delegating planning
found them and planning by hand never did.

The rule: a surviving `FlightType.TARPS` flight reveals any hidden enemy command post within
`TARPS_POD_RADIUS_NM` (3 NM, reused from `reconluadata` rather than a fresh number) of its
package target, with a campaign message. This cannot become scout-to-reveal by construction —
it only reaches sites that are not on the map at all, and every ordinary site already carries
a marker.

Note this is **planner-side geometry**: it keys on the flight's package target and on the
flight surviving, never on what the aircraft actually photographed. The §12 plugin that did
the photographing was removed 2026-08-20. The design alternatives that were weighed and not taken are in
[retlab-recon-role-scoping-notes.md](design/retlab-recon-role-scoping-notes.md).

Tests: `tests/test_recon_reveal_rule.py` (the reveal rule, the no-lag guarantee, and the
command-post reveal),
`tests/test_recon_intel_fog.py` (the `known_for` gate), `tests/retlab/test_coin_concealment.py`
(now a regression guard that no *category* earns a circle).

**Checklist:** G24 and B33 are closed by removal; **G39** covers the new reveal rule and
**G40** the command-post find; **G25** needs re-scoping against the new rule before it is
flown.

### The original implementation (historical from here down)

**The automatic recon flight was removed 2026-10-12 (DM call): `auto_add_tarps_recon`, `PackageFulfiller._maybe_plan_tarps_recon` and the §67 rain gate `recon_suppressed`. TARPS is hand-fragged. What follows is the record of how the add-on worked.**

`FlightType.TARPS` adds player-flown F-14 recon. All F-14 variants carry the
`{F14-TARPS}` pod on station 6 (editor-verified). The auto-planner appends a single
TARPS sortie to Strike / DEAD packages when `auto_add_tarps_recon` is enabled and a
TARPS-capable squadron is available. The flight type is **airframe-agnostic** — it is
gated purely by the `TARPS` task in the airframe's `tasks:` table, not hard-coded to the
F-14 — so the Vietnam-era recon birds carry it too (see below).

**Recon drone in each Armed Recon package (2026-07-05, RetLab call).** The auto-recon
hook (`PackageFulfiller._maybe_plan_tarps_recon`) now also frags a recon flight into
**Armed Recon** packages, not just Strike/DEAD. Two supporting changes: `TarpsFlightPlan`
was widened to accept a `ControlPoint` target (an armed-recon sweep targets a CP corridor,
not a TGO — the base `recon_area` overflight already handles any `MissionTarget`), and the
armed-recon hook skips the `warrants_recon` TGO gate (a swept corridor always warrants an
overwatch pass). It stays **optional** (drops silently if no TARPS bird is free — never
scrubs the package) and gated by the same `auto_add_tarps_recon` setting. Because the recon
bird is whatever is `TARPS`-capable in the faction, on a **UAV-fielding faction (OIR:
Predator/Reaper carry `TARPS`) this frags a drone into every armed recon package** — and
the `airecon` plugin banks that AI drone overflight as confirmed BDA, so the drone is what
localizes the swept area's concealed contacts (§3 concealment loop). Alongside, the
threat-gated SEAD escort (`propose_common_escorts`, 2-ship) resolves to the Viper
on OIR/Red Tide — so a full armed recon package reads **1 drone + 2 SEAD Vipers + the
sweep**. The Armed Recon primary itself was a fixed 4-ship until the 2026-08-09 planner
re-convergence reverted it to the stock 2–4 `get_flight_size()` roll
(`game/commander/packagefulfiller.py`, `game/ato/flightplans/tarps.py`,
`game/commander/tasks/primitive/armedrecon.py`; tests `tests/test_armed_recon_planning.py`;
checklist G25 — the in-mission composition needs a fly).

**The tag-along never paces the package (2026-07-19 fix, the flown Scenic Route kneeboard
finding "times and speeds are getting weird").** `Package.formation_speed` is the minimum
`best_flight_formation_speed` over every `FormationFlightPlan` flight — and `TarpsFlightPlan`
is one, so the auto-added recon **drone dragged the whole package's formation legs to MQ-9
pace**: a 4-Hornet DEAD package planned its join/target/split legs at 169 kt (kneeboard GSPD
161), stretched the egress-to-split to 34 minutes, and — because the backward structural
chain prices the direct ingress→target leg at package speed while the forward takeoff chain
walks the real route at mixed speeds — blew ~5 minutes of drift through the schedule, eating
the hold dwell (hold departure 15 s *before* arrival) and inverting nav/join (a **−725 kt**
kneeboard row). Three-part fix, headless-verified against the flown save: (1)
`Package.formation_speed` **skips a TARPS flight unless it is the package's primary** (the
tag-along BDA/overwatch bird flies the package route on its own role-aware ToT offset and
never sets the shooters' pace; a pure recon *package* still paces its escort to the drone);
(2) both formation `speed_between_waypoints` sites **cap each flight's formation-leg speed at
its own capability** (`min(package, own)`) so the excluded drone keeps its own achievable
169 kt schedule — a strict no-op for every flight that participates in the package minimum;
(3) the kneeboard `_ground_speed` guards a **zero-or-negative leg time** with "-" instead of
printing a negative speed (residual structural-vs-chained drift is now sub-minute and absorbed
by the hold dwell, but custom/manually-timed plans can still degenerate). On the flown save
the DEAD package re-plans at 422 kt (the AV-8B — the slowest *real* member), the hold dwell
returns positive (~4:35), every row is monotonic, and the Hornets land 21 minutes earlier
with the package TOT untouched. Follow-up same day ("why are we giving times for bullseye"):
the kneeboard's **divert/bullseye reference rows drop Time/Departure/GS/Mach entirely**
(`FlightPlanBuilder.REFERENCE_WAYPOINT_TYPES`) — they ride the jet's route as steerpoints,
but the chained ETA past the landing point is by construction "when you'd get there if you
kept flying after landing", and the Fuel column already blanked exactly these rows.
**The split ran on a different clock from everything after it (fixed 2026-09-15).** The
locked `split_time` charges 45 s per target point over the target; the forward chain that
times every non-structural waypoint after it (refuel, RTB legs, landing) summed
`total_time_between_waypoints` per leg and never charged that dwell, so the chain ran ahead
of the split by the whole dwell. Measured on a 4-target Syria DEAD: split locked 20:14:13,
refuel chained 20:13:46 — the tanker ETA 27 s before the jet leaves the target; on the card
that is one slow leg (the split row swallows the dwell) followed by one impossible one (the
next row hands it back — the 771 kt / Mach 1.25 leg on a flown F-16 card). Fixed the way
`PatrollingFlightPlan` charges its on-station time: `FormationAttackFlightPlan.
total_time_between_waypoints` adds `time_at_target` on the leg into `layout.split`, and
`split_time` is now that same sum, so the two clocks agree by construction
(`tests/ato/flightplans/test_formationattack.py`).
(`game/ato/package.py`, `game/ato/flightplans/formation.py`,
`game/ato/flightplans/formationattack.py`, `game/missiongenerator/kneeboard/`; tests
`tests/ato/flightplans/test_formationattack.py` +
`tests/missiongenerator/test_flightplan_fuel_column.py`.) The same machinery gained the
join→ingress leg on 2026-09-01 — see §8 and
[retlab-cruise-mach-notes.md](design/retlab-cruise-mach-notes.md).

**JTAC is upstream's, unmodified (packaged-drone model STRIPPED 2026-08-05).** The fork briefly
ran two mutually-exclusive JTAC models — upstream's front-line FAC, and a RetLab packaged drone
that rode air-to-ground packages and lased from there. The drone model is **removed** on a DM
call ("G26, 27 need stripped from the build, leave G32 as its default behavior"; the target
state being upstream's own behaviour — "it fields an AI drone for each faction over the front
line period thats it").

There is now **exactly one JTAC model, and no setting governs it**:
`FlotGenerator._generate_front_line_jtac` spawns an **invisible, immortal** `jtac_unit` FAC
orbiting the FLOT at 5,000 ft, on the front line's own laser code (forced to 1113 under
`ctld.fc3LaserCode` so FC3 receivers can lase), gated on nothing but `faction.has_jtac`,
**blue-side**, defaulting to the **MQ-9 Reaper** when a faction declares no `jtac_unit`.

**Checked line-by-line against `upstream/dev`.** The fork's extracted method is behaviourally
identical to upstream's inline `# Add JTAC` block: same gate, same blue-only scope, same
`str(code)` / `Player.BLUE` / `callsign_for_support_unit(jtac)`, and the `position` the method
recomputes is the *same* `FrontLineConflictDescription.frontline_position` call that upstream
reads out of the enclosing scope. **One divergence is deliberate and stays:** upstream records
`player_frontline_groups` *inside* its `has_jtac` block, so a blue side without a JTAC reports
no frontline groups at all — an upstream bug, not JTAC behaviour, and it must not be
"restored" in the name of fidelity.

**Removed by the strip:** the `coin_packaged_jtac_drone` and `auto_jtac_drone` settings (and
their Insurgency layout entries), `game/retlab/jtac_drone.py` (`ensure_jtac_drone_squadron`
— the auto-fielded rear ISR drone squadron that existed only to guarantee the packaged JTAC a
drone), `AircraftGenerator._maybe_configure_jtac` with `_JTAC_PACKAGE_PRIMARIES`, the
`Coalition.configure_default_air_wing` hook, the `coin_packaged_jtac_drone: true` preseeds in
both COIN campaigns, and ~~`tests/retlab/test_jtac_drone.py`~~ +
~~`tests/missiongenerator/test_drone_jtac.py`~~.

Removed settings are **save-safe**: `Settings.deserialize_state_dict` looks each stored key up
against a fresh `Settings()` and passes unknown values straight through, so an old save's two
keys survive as inert `__dict__` entries — the same path the §20 and §53–§55 removals took.

**Coverage note worth keeping.** The two deleted test files covered the *drone* side and the
mutual exclusion; nothing anywhere tested the front-line FAC itself, so the strip would have
left the build's only JTAC model with zero coverage.
`tests/missiongenerator/test_front_line_jtac.py` replaces it: the `has_jtac` gate both ways
(using a sentinel raised from `frontline_position` to prove the body is reached), plus a guard
that the two stripped settings are really gone rather than left dead for someone to re-wire.
The full generator body still is not exercised — it builds a real pydcs flight group, resolves
a livery and needs theater geometry — so the FAC actually lasing remains checklist **G32**.

- Enum + behavior: `game/ato/flighttype.py`, `game/missiongenerator/aircraft/aircraftbehavior.py`
  `configure_tarps()` — a single flyover of the target area, ReturnFire ROE, no offensive
  stores. It sets the recon *behavior*; the *timing* lives in the flight plan (below).
- **Role-aware TOT** (`TarpsFlightPlan.default_tot_offset`): the recon bird does two different
  jobs and they want opposite timing. On a **Strike/DEAD** package it is a **post-strike BDA**
  pass — overfly **+2 min** after the shooters to photograph the damage (tight so it stays
  under the escort window, G19). On an **Armed Recon** package (or a standalone recon mission)
  there is no strike moment to trail, so it is a **find/overwatch** pass — **0 offset**, on
  station with the package to scout/localize, not two minutes behind an event that never
  happens. (This replaced a flat +2 min that was BDA-only reasoning applied to every package —
  the 2026-07 recon-rework de-jumble.)
- Flight plan: `game/ato/flightplans/tarps.py` uses `FlightWaypointType.INGRESS_RECON`
  (NOT `INGRESS_STRIKE`) so the weaponless recon bird gets **no Bombing tasks** on its
  ingress — `INGRESS_STRIKE` dumped one Bombing task per target-group unit onto the
  ingress, making the AI fly an aborting attack pattern and never cleanly overfly.
  `INGRESS_RECON` → `ReconIngressBuilder` (no attack tasks,
  `game/missiongenerator/aircraft/waypoints/reconingress.py`); the target waypoint is a
  **flyover** (`WaypointBuilder.recon_area`, `flyover=True`) so the AI actually crosses
  the target instead of turning back at the IP. (Player-only target waypoints are
  filtered for AI, so without the flyover the AI never reaches the target.)
- Auto-planner: `game/commander/packagefulfiller.py` `_try_add_tarps_recon()` with
  explicit debug logging for every skip reason.
- Aircraft: `TARPS: 700` task priority in `resources/units/aircraft/F-14*.yaml`;
  payloads in `resources/customized_payloads/F-14*.lua`. The `Retribution TARPS` payload
  carries `{F14-TARPS}` on station 6 (station 5 clean) plus a per-variant self-defense
  fit, verified from the `Aerial-1/2/3` groups in `Tues test 1.miz`: F-14B = AIM-54A
  (Mk60 L / Mk47 R), F-14A-135-GR-Early = AIM-54A (Mk47 L/R), F-14A-135-GR = AIM-7M, all
  with AIM-9L wingtips. **CLSIDs must be current** — stale ones (`{SHOULDER AIM-7MH}`,
  `{LAU-138 wtip - AIM-9M}`) made DCS reject the whole loadout on load and silently drop
  the TARPS pod with it. The vanilla `F-14A.lua` still uses the old GUID-form loadout.
- **Vietnam-era recon birds (VWV mod):** the dedicated tactical photo-recon ships —
  **RF-101B Voodoo** (`vwv_rf101b`, USAF land-based) and **RA-5C Vigilante** (`vwv_ra-5`,
  USN carrier) — carry `TARPS: 700` as their **primary** task (their old `Armed Recon` is
  kept as a lower-priority fallback so a squadron is never idle). They are unarmed camera
  ships with built-in cameras (no external pod), so their `Retribution TARPS` payload is a
  clean, weaponless fit — empty pylons, matched by name; the runtime recon task is set by
  `configure_tarps`, so the payload's `tasks` tag is only ME role-menu placement.
  Files: `resources/units/aircraft/vwv_{rf101b,ra-5}.yaml` +
  `resources/customized_payloads/vwv_{rf101b,ra-5}.lua`. The **1968 Yankee Station** campaign
  fields both (RF-101B at Da Nang, RA-5C on the carriers), tasked `primary: TARPS`
  (`resources/campaigns/1968_Yankee_Station.yaml`).
- Tests: `tests/test_tarps_recon.py` (Tomcat + Vietnam-recon TARPS-capability gates).

**AI recon BDA capture (the `airecon` plugin) — REMOVED 2026-08-20 with §12.** An `airecon`
plugin closed the capture-side gap where the MOOSE TARS film engine was player-only, so an
AI-flown recon flight banked nothing. The 2026-08-18 reveal rework removed both jobs a
capture could do, so the plugin, its emitter (`aireconluadata.py`), the `tars_recon_captures`
ledger and every test went with §12. Nothing films anything now; a site is revealed by being
engaged. See §12 for the removal and `git show c89f27dcc` for what came out.

**Visibility / recon fog** — one viewer-aware layer drives two player-facing fog rules.
AI planning and threat math always use ground truth (`viewer=None`); only the human
(BLUE) map/UI are fogged.

The unified layer (replaced the old sprawling `_for_player`/`_for` method twins — collapse
finished, do not reintroduce twins):
- `TheaterUnit.alive_for(viewer=None)` — `None`/friendly → truth; enemy → `alive_at_last_recon`
  (post-strike BDA damage lag). `sync_confirmed_status()` snaps it to truth.
- `TheaterGroundObject.known_for(viewer=None)` — `None`/friendly → True; enemy → the sticky
  `discovered_by_player` flag (gated by the `recon_intel_fog` setting).
- Every accessor takes `viewer: Optional[Player] = None` (truth by default): unit
  `threat_range`/`detection_range`, group `alive_units`/`max_threat_range`/`max_detection_range`,
  TGO `is_dead`/`dead_units`/`alive_unit_count`/`max_threat_range`/`max_detection_range`/
  `sidc_status_for`/`sidc_for`. `display_name`/`short_name` keep a truth `@property` that
  delegates to the `*_for(viewer)` worker (they had too many truth callers to convert).
  Files: `game/theater/theatergroup.py`, `game/theater/theatergroundobject.py`.

*Two fog rules on that layer:*
1. **BDA damage lag** (`alive_for`): struck *enemy* units keep showing alive until recon
   confirms the kill. `game/sim/missionresultsprocessor.py` applies true kills, then
   `sync_confirmed_status()` only on friendly TGOs and enemy TGOs reconned this turn
   (TARPS package targets + actual TARS captures).
2. **Recon intel-fog** (`known_for`): a new *enemy* site shows on the map as a targetable
   marker (position/category/allegiance) but its composition + threat/detection rings stay
   hidden until **attacked, scouted, or destroyed**. `discovered_by_player` is flipped
   (sticky, enemy-only) by `reveal_discovered_sites()` in `missionresultsprocessor.py` from
   the struck / reconned / TARS / attacked sets. `__setstate__` migrates old saves to
   `discovered_by_player=True` (existing campaigns stay revealed; the fog is felt on new
   campaigns). Master switch: `recon_intel_fog` setting (default ON, Campaign Doctrine).

- Consumers gate at the edge: `game/server/tgos/models.py` emits a fogged payload (empty
  rings, hidden units) when `not known_for(BLUE)`; `qt_ui/windows/groundobject/QGroundObjectMenu.py`
  + `QBuildingInfo.py` pass `self.viewer` and show "Not yet scouted — composition unknown".
- Tests: `tests/test_bda_tarps_reveal.py` (damage lag), `tests/test_recon_intel_fog.py`
  (discovery gate, migration, setting).

A third gate rides the same viewer-aware layer: `TheaterGroundObject.hidden_on_player_map(viewer)`
fully hides enemy command posts for the SCAR commander-capture feature (gated by
`scar_command_post_intel`, default ON for new campaigns) — see
[§15](#15-scar--strike-coordination-and-reconnaissance-flight-type--scenario-plugin).

**Concealed field forces — "in here somewhere" uncertainty areas (2026-07-05).** The recon
intel-fog above hides *composition* but the marker still X-marks the exact spot, so "finding"
a hidden site was fiction. A fourth rule fixes the *position* half: while `known_for(BLUE)`
is False, a qualifying TGO's map presence is a dashed amber **uncertainty circle** (amber
since the §28 UI audit — dashed red now exclusively means an ROE off-limits zone) instead of
an exact marker — centred on a **deterministically jittered** point (seeded from the TGO id
so it never wanders between refreshes; offset 15–60 % of the radius so the truth always sits
inside) with the true coordinates **never sent to the client** while concealed. Two ways in:
- **COIN intrinsic** — the hidden insurgent spawns (roadside IED/VBIED, HVT convoy,
  dispersed/re-infiltration cells) carry `TheaterGroundObject.concealed = True` from
  `spawn_red_ground_at(concealed=True)`, independent of any setting (it's their identity);
  caches + stronghold garrisons stay exact.
- **`concealed_enemy_forces` setting** (Difficulty & Realism, default **ON**; only meaningful
  while `recon_intel_fog` is on since discovery funnels through `known_for`) — enemy **field**
  forces qualify by kind: mobile SAM sites (`category == "aa"` with task MERAD/SHORAD/AAA —
  the Weasel hunt), deployed vehicle groups (`"armor"`, tighter 3 km circle), and missile
  sites (`"missile"` — the SCUD hunt). **Fixed infrastructure stays exact**: LORAD strategic
  sites, EWRs (they emit — passively geolocatable), buildings, ships, and airfields.

**Road-pinned variant (2026-07-05, user call):** a TGO carrying
`TheaterGroundObject.concealed_route` (a polyline of `(x, y)` map coordinates — the roadside-IED
layer stores its supply road at plant time) slides its suspected-activity centre **far ALONG that
route** (5–25 km, deterministic, clamped/bounced at the road's ends — `_route_jitter` in
`game/server/tgos/models.py`) instead of the radial offset: "we know what highway it's on, not
which street." Deliberately, the truth may sit **outside** the drawn circle here — the road itself
is the search domain (sweep the highway), and the radial invariant (truth always inside) applies
only to non-route concealment. A degenerate route (< 2 points / zero length, or a pre-feature
save) falls back to the radial jitter.

The circle keeps the marker's click/right-click contract (plan TARPS/strike against the
suspected area); discovery (attacked/scouted/TARPS — the same `discovered_by_player` gate),
recon fog off, or the overview reveal snaps it to the exact symbol. Two consequences by
design: a killed-but-not-reconned concealed site keeps its circle until BDA confirms it (the
recon loop), and auto-planned routes still bend around SAMs the map claims are un-located
(threat math is ground truth — the standing §3 rule, just more visible now). Known accepted
leak: a package planned against a concealed TGO puts its steerpoint at the true position
(that IS the localization mission; §5 Approximate precision covers player steerpoints).
Implementation: `concealed_uncertainty`/`_concealed_radius` in `game/server/tgos/models.py`
(both the `/game` pull and the SSE `updated_tgos` path go through it),
`client/src/components/tgos/Tgo.tsx` (`ConcealedTgo`), `Tgo.uncertainty_radius_m` in the API
model. Tests: `tests/retlab/test_coin_concealment.py`. Checklist **P3** — its "concealed
'in here somewhere' areas" and "map symbology" bullets cover P3–P6 — needs an in-app pass + the
CI client rebuild. (This cited **G24** until 2026-08-25. G24 was *concealed field forces*, closed
by removal 2026-08-18 and replaced by G39; the COIN suspect-until-engaged concealment described
here survived that rework, so its pass rides P3.)

**Overview reveal toggle ("show the real picture").** A single runtime switch that forces
every player-facing fog rule above to resolve to ground truth, for whoever is looking. It
exploits the fact that all three player-facing fog rules funnel through exactly three leaf
methods, so it is implemented as a one-line short-circuit in each rather than re-threading
viewers through ~15 call sites:

- Flag: `game/theater/fogofwar.py` — `fog_revealed()` / `set_fog_revealed()` over a
  process-global `bool`. **Transient by design**: never pickled, so a save can never carry a
  god-view, and a shared campaign can't leak one. The module imports nothing (cycle-free) so
  the theater layer can pull it in freely.
- Chokepoints: `TheaterUnit.alive_for`, `TheaterGroundObject.known_for`, and
  `hidden_on_player_map` each gained `or fog_revealed()` in their `viewer is None …` guard.
  Because `display_name_for`/`short_name_for`, unit `threat_range`/`detection_range`, group
  `alive_units`/`max_threat_range`/`max_detection_range`, TGO `is_dead`/`dead_units`/
  `sidc_status_for`, and `ThreatZones.for_faction` (`known_for` gate + `max_threat_range`) all
  delegate to those three leaves, the toggle un-fogs the **entire** map render path
  (`TgoJs`, the red `ThreatZonesJs`, `IadsConnectionJs`) **and** the intel dialogs at once —
  with **zero server-model changes**, since those still pass `Player.BLUE` and the leaves
  short-circuit internally. AI/planner/threat math pass `viewer=None` and are unaffected.
- UI: a **"Reveal fog of war"** checkbox in the custom map layers panel
  (`client/src/components/maplayers/MapLayersControl.tsx`, "Enemy intel" group; see §18), not
  the Qt chrome. It is driven by a state `useEffect`, **not** a Leaflet `add`/`remove` layer —
  that approach proved unreliable: on unmount react-leaflet tears the layer down without firing
  `remove`, so unchecking left the overview stuck on. The effect `PUT`s
  `/fog-of-war/reveal?revealed=…` (`game/server/fogofwar/routes.py`, registered in
  `game/server/app.py`) then calls `reloadGameState(dispatch, true)` — a **no-recenter** full
  re-pull of `/game`, whose `tgos`/`iads_network`/`threat_zones` are rebuilt through the (now
  short-circuiting) fog paths, so composition, rings, and hidden command posts appear — and
  re-hide when unchecked, because `TgoJs.all_in_game` re-applies the `hidden_on_player_map`
  filter. Defaults off; the panel persists other layer choices to the campaign save (and a
  localStorage cache; see §18) but deliberately excludes the fog overview, so it is never
  restored on load.
- Note: it lives entirely in the React client, so it needs the rebuilt bundle — CI's
  `npm run build` ships it in the `latest` release. The Python chokepoints + the
  `/fog-of-war/reveal` endpoint are covered by the existing fog tests
  (`tests/test_recon_intel_fog.py`, `tests/test_bda_tarps_reveal.py`) and a route test
  (`tests/server/test_fogofwar_route.py`). The client panel has no JS test (the project ships
  none for the map layers).

---

## 4. UI transparency improvements

Several player-facing dialogs were reworked to surface planner reasoning instead of
just raw data.

### Map and dialog panels

**Target Intel panel** (`qt_ui/windows/groundobject/QGroundObjectMenu.py`):
Every ground-object dialog now opens with a read-only `Target Intel` group showing
target type, allegiance, mission types valid against it, known live/destroyed unit
counts, detection/threat range, IADS membership, hide-on-MFD flag, and
capturable/purchasable status.

**Mission Impact summary** (`qt_ui/windows/QDebriefingWindow.py`):
Debrief prepends a `Mission Impact` group above the casualty tables: mission
end-state, bases captured/lost, runway damage, and loss counts for both sides.
Since 2026-10-11 the window is two columns (row B218): the summary boxes and the two
lost-units lists side by side on the left, §108's report cards on the right. Only the
lost-units lists (past 10 rows) and the cards scroll; `ContentSizedScrollArea` is what
stops Qt shrinking them to two rows. The banner picture is gone.

**Package context bar** (`qt_ui/windows/mission/QPackageDialog.py`):
The package summary line now renders primary task, flight count, player slots,
actual TOT (e.g. `TOT: 15:32:00 (ASAP)`), and departure bases in one line.

**Flight-creation context** (`qt_ui/windows/mission/flight/QFlightCreator.py`,
`qt_ui/windows/mission/flight/SquadronSelector.py`):
A live summary explains what the selected task/aircraft/squadron choice means.
Squadron hover text shows primary role, auto-assignability, spare aircraft, base,
and distance to target.

**Building card cleanup** (`qt_ui/windows/groundobject/QBuildingInfo.py`):
`SceneryUnit.icon` always returns `"missing"`, so every scenery building previously
loaded `missing.png` (which contains the literal text "Missing Recon Picture").
Cards now skip the image widget when no real icon exists and show a compact
name + value layout instead.

### Flight altitude editing

**Flight altitude editing** (`qt_ui/windows/mission/flight/waypoints/QFlightWaypointTab.py`,
`QFlightWaypointList.py`):
Changing a flight's cruise altitude used to mean editing every waypoint's `Alt (ft)`
cell one at a time, and that cell's spin box stepped by the `QDoubleSpinBox` default of
**1 ft** — useless arrows. Two fixes: (1) an `Altitude` block at the top of the
Waypoints tab's action column — a 1000-ft-step spin box + **Apply to all** that writes one
altitude onto every flown waypoint at once (`on_apply_bulk_altitude()`). (2) the
per-waypoint `Alt (ft)` cell editor now steps by 1000 ft and drops decimals. Per-waypoint
editing is untouched, so a low-level ingress leg can still be hand-tuned after a bulk set.
UI-only; no save-format or planner change. Upstreamed as
[dcs-retribution#805](https://github.com/dcs-retribution/dcs-retribution/pull/805).

**Which waypoints the bulk set moves** — reworked 2026-08-08 on upstream review of
[#920](https://github.com/dcs-retribution/dcs-retribution/pull/920), which reported that
the CAS FLOT boundaries never moved. The original filter was a skip-list of 13 waypoint
types plus `alt_type != "RADIO"`, and that last rule was the defect: `waypointbuilder.cas()`
hardcodes `RADIO` at any altitude, so the FLOT legs were always skipped — and since the
planner marks **everything at or below `AGL_TRANSITION_ALT` (5,000 ft) RADIO, plus every
helicopter leg**, `Apply to all` did nothing at all on a helo or a Vietnam low-level plan.
The replacement (`bulk_editable()`) reads the waypoint's own planned altitude, which is the
reviewer's suggested shape:

- **Planned on the deck → stays on the deck.** Takeoff, landing, cargo stop, bullseye, an
  on-map divert field and all three `TARGET_*` types are planner-seeded at 0 ft, so they
  need no entry in any list.
- **Planned at an altitude → moves.** Including the CAS FLOT legs, every AGL leg, and the
  refuel / recovery-tanker legs (which is what #920's proposed opt-in checkbox existed to
  arrange, so the checkbox was dropped).
- `BULK_ALTITUDE_SKIP_TYPES` survives with **three** entries — `PICKUP_ZONE`,
  `DROPOFF_ZONE`, `CSAR_PICKUP` — the ground points that carry a *non-zero* planned
  altitude (the helo approach into an LZ). A type only needs naming there if its planned
  altitude is non-zero.
- **`alt_type` is normalised on write** (`bulk_alt_type()`), following waypointbuilder's own
  rule: AGL at or below 5,000 ft and on helicopters, MSL above. Required, not cosmetic — the
  `Alt Type` column is read-only (`QFlightWaypointList.py`), so leaving a route half AGL and
  half MSL puts the flight at two real altitudes with no way for the player to reconcile it.
- The spin box floors at **1,000 ft** (`BULK_ALTITUDE_FLOOR_FT`); 0 ft was reachable and
  dropped the whole route to sea level. A helo's sub-1,000 ft cruise is set per-waypoint.

Pinned in `tests/test_bulk_waypoint_altitude.py` (the two filter helpers are module-level
functions so the rule is testable without building the widget).

### Kneeboards

**Dead-line sweep (2026-09-29, row B163).** Read against a headless Long Road to H3 deck. Removed: the empty Divert row when a flight has no divert; the "Friendly Packages" heading repeating its own page title; the Apache's AN/APG-78 radar on the LOADOUT line (a sensor, dropped like the TGP); a UTF-8 dash that printed as `â€”` on the QFE storm-cell line. The LOADOUT line now counts stores from the launcher's own name (`_launcher_stores`): pydcs group names carry a count suffix that is wrong for the M299 (`AGM-114L * 1` on four rounds), and rocket pods have no group. Cluster bombs are excluded so bomblets are never counted. Drop tanks read `fuel tank`; the SAR line is one line. The SITREP and friendly-packages setting descriptions and `docs/wiki/Kneeboards.md` no longer describe the pre-split layout, the old SAR drill, a `Flight` row or scouting as the threat-card reveal.

**Kneeboard package layout (2026-09-23).** `kneeboard.py` (3,650 lines) was split into a package, one module per page family: `writer` (page writer, time formats, `TableKneeboardPage`), `flightplan`, `briefing`, `support`, `taskpages`, `threatintel`, `pages` (saved points, notes, SITREP, index), `packagesmap`, `generator` (`KneeboardGenerator`). `__init__` re-exports the old public names. Imports run one way: everything depends on `writer`, nothing depends on `generator`.

**Kneeboard consolidation + overflow pagination** (`game/missiongenerator/kneeboard/`,
`kneeboard_page.py`): kneeboards are built once per `.miz` by `KneeboardGenerator.generate()`,
which buckets pages per **airframe** (DCS can't do per-group kneeboards) and writes each
`KneeboardPage` to a PNG. PR #73 folded the standalone Airfield Directory into the bottom of
the Support Info page and the Friendly Packages list into the bottom of the Mission Info page
to cut page count — but **neither host page paginated**, so on busy theaters those folded
tables ran off the bottom edge and the rows were simply lost. The fix: a `paginate()` hook on
`KneeboardPage` (default `[self]`, flattened in `generate()`) plus a `KneeboardPageWriter`
that can measure remaining vertical space (`remaining_table_rows()`) and render only the rows
that fit (`table_paginated()`, returning the overflow). `BriefingPage`/`SupportPage` render
the rows that fit inline and spill the remainder onto an auto-paginating generic
`TableKneeboardPage` continuation page (titled "… Friendly Packages" / "… Airfield Directory",
later pages marked "(cont.)"). The folded inline list is unchanged when everything fits, so
small theaters see no extra pages. The Friendly Packages list + package-targets map are gated
by `generate_all_packages_kneeboard`, now **default OFF** (it adds pages and can paginate on
busy theaters); the Airfield Directory still folds in whenever ATIS is present. Covered by
`tests/test_airfield_directory_page.py::test_support_page_spills_long_airfield_directory_to_continuation`.
The satellite-imagery recon pages ship gated OFF by `generate_target_recon_kneeboard`; the
marker/tile geometry bug that kept them off was root-caused and **fixed 2026-07-18** — the
dominant error was the DCS-vs-real-world terrain georeference offset (~350 m median on
Caucasus/GermanyCW), previously corrected only on airbase-anchored pages: every page now
applies the robust regional offset of the nearest measured airports
(`airport_imagery.offset_near`), and the secondary whole-page-QUAD interior curvature
residual (~5 page px on a 300 km overview) is removed by a subdivided MESH warp
(`tile_compositor`). Default stays OFF pending the in-game pass (checklist H13).

**The offline basemap placed its imagery by `terrain.bounds`, which does not bound the map
(fixed 2026-08-22).** When `render_tiles` returns None — no network, ToS refusal, or a terrain
with no projection — `_render_legacy_fallback` crops the shipped theater raster
(`resources/syria.gif`, `caumap.gif`, …) and draws the same symbology over it. `_crop_from_gif`
georeferenced that crop with `extent.terrain.bounds` and then **clamped** the crop rectangle to
the image, so an extent the raster could not cover was silently stretched to fill the page
rather than failing. The page looked correct and the markers were on the wrong ground.

`terrain.bounds` is not a georeference and must never be used as one. Measured: it leaves **24
of Syria's 224 airfields outside itself** — the whole Jordanian corner and the Negev, including
King Abdullah II, Muwaffaq Salti, Nevatim and Hatzerim — plus 23 of Normandy's 89, 4 of Persian
Gulf's 29 and 2 of Nevada's 17. pydcs also declares Syria, Normandy and PersianGulf with
`top < bottom`, inverting its own `Rectangle` contract, so the north-south scale came out
negative and the clamp collapsed **every** Syria crop to a one-pixel-tall strip stretched over
the whole page. The damage was not confined to the out-of-bounds corner: a Tabqa page, well
inside the raster, drew ground centred 215 km south and 58 km east of what it asked for, and a
Batumi page came out 116 km east over a 38×33 km crop where 80×80 km was requested.

`gif_georef.py` replaces it with a **measured** world rect per raster, taken from the two
per-theater reference airports the pre-2021 Qt map used to georeference these same images
(`git show 30f6220c3^:game/theater/conflicttheater.py`) and re-derived against each GIF's
current pixel size. Validated independently against the airfields: 0 of Caucasus's 21 and 0 of
Nevada's 17 project onto sea pixels, and 29/29 Persian Gulf fields sit in frame. Coverage and
resolution:

| Theater | Raster | m/px E, N | Note |
|---|---|---|---|
| Caucasus | `caumap.gif` 2464×1400 | 282.0, 336.7 | Anapa sits ~6 km off the west edge |
| Nevada | `nevada.gif` 1192×1008 | 537.3, 578.9 | all 17 fields in frame |
| Normandy | `normandy.gif` 2158×2500 | 130.5, 135.5 | predates Normandy 2.0; London and Paris off-frame (28/89 fields) |
| PersianGulf | `persiangulf.gif` 1870×3552 | 292.3, 294.7 | all 29 fields in frame |
| Syria | `syria.gif` 2059×1370 | 439.6, 451.7 | predates the Jordan/Israel expansion; Cyprus never drawn |

Two rules follow, both of which the old code broke:

- **Refuse, never clamp.** `coverage_for()` returns None for a theater with no measured rect and
  for a raster that is not the pixel size the rect was measured on (a replaced asset invalidates
  the numbers). `can_render()` then requires the extent to fit **entirely** inside the rect.
  Any refusal drops to `_draw_landmap_only`, which is plain but placed correctly.
- **A hole is a refusal too.** syria.gif draws flat sea over Cyprus even though the island is
  inside its frame — all 25 Cyprus airfields (Akrotiri, Larnaca, Paphos, Ercan, Gecitkale,
  Kingsfield, Lakatamia, Pinarbashi and the HC/HMed helipads) project onto sea pixels, in an
  island-shaped arrangement that confirms the georeference is right and the imagery is missing.
  `GifCoverage.unrendered` records it as a world rect and refuses any extent that touches it.

**The Package Targets Map draws terrain (2026-08-22).** Found while investigating why that page
drew land as a flat fill: switching it to the raster had been tried and reverted for exactly the
georeference defect above (`7cc256f5c`, upstream-of-fork PR #945). With the defect fixed the swap is safe, and it is made
here. `PackagesMapPage` now calls `render_theater_basemap` instead of `render_landmap_basemap`
— the shipped raster where `gif_georef` says it reaches, the filled-coastline landmap otherwise.
Markers, labels and the label-placement rules are untouched.

- **Offline by construction.** This page is generated for every mission, not just the gated recon
  deck, so the backdrop must never cost a network round-trip. `render_theater_basemap` does not
  call `render_tiles` at all, pinned by a test.
- **The extent is aspect-corrected first, then offered to the raster.** The padded extent is what
  gets drawn, so it is what has to be covered. A theater-wide spread usually exceeds the raster
  and falls back — which is right, and the fallback is the more complete picture in that case
  anyway: the landmap draws Cyprus, which syria.gif does not.
- **Dark kneeboards dim the raster** by `_DARK_RASTER_DIM` (0.45). There is no dark variant of a
  daylight satellite render; 0.45 sits it near the dark landmap's own land fill and keeps the
  white label plates and haloes high-contrast.

**Past the landmap's edge is land, and frontiers are drawn (2026-10-16).** The landmap fallback
used to paint everything that was not an inclusion zone as sea. The Iraq landmap stops about
35 km short of the map's west and north edges, so Desert Aladeen's page drew an ocean over
Jordan, Syria and Turkey. Any page reaching past a landmap's outer edge did the same
(Caucasus's Turkey corner, Syria's south, the Gulf's Saudi side, Nevada, Sinai, Kola).

- `_load_sea_polygons` builds the water once per terrain: the inclusion and sea zones together,
  gaps under 8 km closed (`_FOOTPRINT_CLOSE_M`), minus the land. Inside that outline the page
  reads as before, estuaries and shoreline gaps included; outside it is land fill. DM call:
  land, not a grey "off the map" fill, accepting open ocean drawn as land in the few corners
  past a landmap's edge. Inside the hull of the terrain's §98 border countries, ground no country
  covers is open sea (pieces under 30 km across dropped: the files' simplified clip edge leaves a
  20 km sliver under Iraq's northern frame), so the Falklands' ocean and Iraq's Caspian stay blue.
- `_landmap_path_for_terrain` also matches a theater's `info.yaml` `pydcs_name`. By folder name
  alone Sinai ("SinaiMap") and Marianas WWII ("MarianaIslandsWWII") found no landmap, so their
  page had no water at all.
- `_draw_land_borders` draws the §98 terrain border file's frontiers over either backdrop: only
  edges two countries share, the rule `land_border_runs` uses, so no coast or clip edge.

Independent confirmation the georeference is right, from the rendered pages: on Caucasus every
coastal field — Sochi-Adler, Gudauta, Sukhumi-Babushara, Kobuleti, Batumi — sits on the imaged
shoreline, and only Batumi is a reference point. On northern Syria the raster's coastline traces
the landmap's coastline, two unrelated data sources agreeing.

**How often it actually fires: 9 of the 42 shipped campaigns on a raster theater.** Measured by
loading every campaign and running its real control points through the page's own extent
maths. The limit is the rasters, not the code — they were authored for smaller maps than DCS
now ships. syria.gif covers 619 × 905 km of a theater whose airfields span 763 × 709 km, so any
campaign spread across Syria loses. The winners are the compact ones: `WRL_AleppoInsurgency`,
`WRL_Battle4SyriaNorth`, `WRL_Battle4Georgia`, `northern_russia`, `red_flag_81_2`,
`exercise_vegas_nerve`, `WRL_Battle4area51`, `scenic_route`, `WRL_PG_Wargames`. Nevada is the
best-served theater (3 of 3) because its raster outruns its map.

**The slide takes that 9 to 15.** `aspect_correct` pads symmetrically about the extent centre,
so when the padding pushes one edge off the raster there is normally slack on the opposite
edge. `GifCoverage.slide_to_cover` spends it: the extent is **translated, never resized**, so
the page keeps its scale and aspect and all that moves is where the area of interest sits.
Recovered: `golan_heights_lite`, `Caucasus_Multi_Georgia`, `TblisiGap`, `WRL_Kutaisi2Vaziani`,
`mozdok_to_maykop`, `caen_to_evreux`.

Three guards, each with a test:

- **The packages never move off the page.** `slide_to_cover` takes the pre-padding extent as
  `must_contain` and refuses any slide that would push part of it out. Trading centring for
  imagery is fine; trading a target for imagery is not.
- **The hole is re-checked after the slide, not only before.** `IntotheHornetsNest` and
  `WRL_AssaultonDamascus` are the two that still fall back, and neither is a slide failure —
  the slide succeeds and lands them on Cyprus, so the `unrendered` rect vetoes it.
- **The backdrop and the symbology share one extent.** `align_extent_to_theater_raster` runs in
  the page *before* both the render and the `Projector`, because rendering the raster for the
  slid extent while projecting markers into the unslid one would reintroduce the original
  defect one layer up. `test_backdrop_and_markers_share_one_extent` fails on exactly that
  mistake — and its fixture is itself guarded by `test_the_sliding_fixture_actually_slides`,
  because the first version of both tests used an extent that never slid and passed vacuously.

**The slide costs no labels.** Crowding the markers toward one edge could in principle leave
a name nowhere legible to sit, which is the failure `7cc256f5c` fixed. Counted across all six
recovered campaigns, every name drawn without the slide is still drawn with it. Pinned by
`test_the_slide_costs_no_labels` on a 15-field fixture — the 3-field one cannot show this,
since a sparse page never runs out of room.

**Also found, not changed:** `sinai.gif` and `marianasislands.gif` ship but are unreachable —
`_theater_gif_path` normalises `SinaiMap` → `sinaimap` and `MarianaIslands` → `marianaislands`,
neither of which matches its filename, so those theaters have always taken the landmap
renderer. No reference points were ever authored for them, so they are left out of `COVERAGE`
rather than guessed; wiring them up needs a measurement pass first.

Tests: `game/missiongenerator/kneeboard_recon/tests/test_gif_georef.py` re-derives every rect
from its reference airports (a typo'd metre fails), pins each raster's pixel size, pins the
`terrain.bounds` counter-evidence so nobody reaches for it again, and checks the Jordan/Negev
and Cyprus refusals against real airfield coordinates. `test_basemap.py` adds a quadrant test
that paints one corner of a stand-in raster and asserts the crop returns that corner — the
world-to-pixel mapping, not just "some image came back". The two pre-existing GIF-path tests
were rewritten: they used a 200×200 placeholder and a Caucasus extent at y 0..30 km, ~250 km
outside the theater, and asserted `len(colors) > 5`, which the tan-landmap fallback also
satisfies. Their own docstring had flagged that risk; they were passing while covering nothing.

**Recon pages are JPEG; everything else stays PNG (2026-07-16).** A kneeboard page is written
by `KneeboardPage.write` and lands in the miz under its own filename (pydcs writes `page.name`
verbatim), so the *suffix* is the whole of the format decision. Every page used to be `.png` —
correct for the line-art pages (text, tables, rules: 20–100 KB each, and JPEG would ring on the
glyphs) and badly wrong for the recon pages, which render a **photographic** Esri satellite
basemap. PNG is lossless, so one 768×1024 recon page cost ~1.2 MB, and with the setting on the
recon pages became **~90% of the whole mission**: 16.5 MB of a fully-crewed 22 MB Red Tide MP
event mission, re-downloaded by every pilot and re-loaded by the server every turn.

`KneeboardPage.image_suffix` (a `ClassVar`, defaulting to `.png`) now names the format and
`_RecordingPage` — the base of every recon page — overrides it to `.jpg`; the write loop names
the file `page{idx:02}{page.image_suffix}`. All seven save sites funnel through one
`save_kneeboard_image` helper (`kneeboard_page.py`) that applies the encoder rules JPEG needs
and PNG doesn't: convert to RGB (JPEG has no alpha) and set `JPEG_QUALITY`. **Quality 85 is
measured, not guessed** — on a real recon page it is 1212 KB → 206 KB with a ~1.4% mean pixel
difference and no visible ringing even on the title bar's white-on-black text; q92 costs ~40%
more bytes for no visible gain at kneeboard size. A fully-crewed mission drops **22.4 MB → 9.0
MB (60%) with no page removed**. DCS has taken JPEG kneeboards all along — a scan of 2,945
shipped campaign missions found **7,971 `.jpg` pages vs 2,542 `.png`** (at least one
paid FA-18C campaign ships `.jpeg`), so this is the format the rest of the ecosystem already uses.

Byte-identical no-op when `generate_target_recon_kneeboard` is off (its default) — no recon
pages, no JPEG pages. Tests: `game/missiongenerator/tests/test_kneeboard_image_format.py`
(format split, suffix-picks-encoder, the alpha case, the size win, the quality pin) +
`game/missiongenerator/kneeboard_recon/tests/test_page_image_format.py` (a *real* rendered
recon page through the generator's own naming path).

**Space-utilisation pass (light headings + two-column lists).** Sparse pages used to leave
the bottom (and right) two-thirds of the image blank. The fix uses a deliberately *light*
style (no heavy boxes): a bold heading, a thin underline `rule()`, then the content, with
sections spread by whitespace (`vspace()`) so the page breathes top-to-bottom. Two small
`KneeboardPageWriter` primitives were added — `rule()` (a hairline separator under a heading)
and `vspace()` (vertical breathing room) — plus `table_two_column_paginated()`. Three pages
were reworked: (1) **`CombatSarTaskPage`** — each guidance section (ROLE / HOW IT WORKS /
PICKUP|ON-SCENE COMMAND / BEACON) is a heading + rule + larger body text, with the leftover
height distributed as capped even gaps so a short brief doesn't yawn; (2) **`SupportPage`** —
the Package / AEW&C / Tankers / JTAC tables get the same heading+rule treatment, spaced to
span the page (gap grows when there's no Airfield Directory below; otherwise a fixed gap
leaves room for the directory and its pagination); (3) the Friendly Packages list renders in
**two side-by-side columns** once it would overflow a single column, using the wasted right
half of the page (only > ~2× a column's capacity still paginates). The recon pages are
untouched (still golden-tested). This is a visual change CI can't exercise — see in-game-pass
row **H1**/**H2**. **H1 (overflow pagination) in-game pass ☑ VERIFIED 2026-06-25**; H2 still
pending.

**Right-edge clipping fit.** Wide content that used to run off the right edge (and silently lose
data) is now fitted to the page: `KneeboardPageWriter.table()` measures `tabulate`'s *actual*
rendered width and, when it overruns, passes `maxcolwidths` (via `_fit_col_widths`, shrinking the
widest column first to a legibility floor) so the over-wide column **word-wraps** instead of
clipping — the Comms & Coordination support ladders were losing FREQ / Departure / TOT when a
package sat on three radio channels. A table that already fits returns `None` (byte-identical
output, so every narrow table is unchanged). Alongside it: the `SupportPage` package FREQ/TOT
header line splits FREQ and TOT onto separate lines when the one-line form would overrun, and the
`ThreatIntelBriefPage` bullseye **cue lists** (drawn with the non-wrapping `text_runs`) truncate to
the pixels left on the line via `_fit_cues` (unidentified cards keep the count-withholding "…";
identified keep "+N"). Tests: `tests/missiongenerator/test_kneeboard_bluf.py` (table wraps/​leaves-fitting-untouched),
`tests/missiongenerator/test_threat_intel_kneeboard.py` (cue width truncation).

**Kneeboard de-duplication pass.** With every optional page enabled the deck printed the same
data several times; a single-home-per-datum pass fixes it, each change conditional on the
*other* page existing (so a deck with options off is byte-identical to before):
- **Weather** (temp / QNH / QFE / winds / clouds / sunrise-sunset) is dropped from the always-on
  **Mission Info** (`BriefingPage`, `omit_weather`) when the recon **Departure** page is generated
  for the flight (`_should_emit_departure`), which already carries the field-weather grid.
  **QNH (with the departure QFE) and the surface wind stay on Mission Info either way
  (2026-10-25)**: the altimeter is set and the takeoff wind read off that page
  (`_altimeter_lines`, `_surface_wind_line`; `test_kneeboard_qnh_wind.py`).
- The flight-plan fuel column: originally a Min-fuel column that was dropped when the Fuel Ladder
  page was enabled; since 2026-07-05 the ladder is **folded into the flight plan** (see the fuel
  ladder block below), so there is one home by construction — a `Fuel` column + a one-line RTB
  margin call-out on Mission Info, and no separate page.
- **The flight plan's speed reads in Mach too (2026-09-15).** Each leg row carries `GS` (the
  derived ground speed in the airframe's unit) and `M` (that speed via `Speed.mach()` at the
  row's printed altitude, so a ground-marked row reads at sea level; still air, no wind). The
  racetrack-end row converts the patrol speed; reference rows and dashed legs stay blank/dashed.
  The ninth column fit only because tabulate pads every header by two characters: `GSPD` →
  `GS` and `Departure` → `Dep` bought it, and the worst-case row now sits 12 px inside the
  page (`tests/missiongenerator/test_flightplan_table_width.py` pins that; a wrap here would
  double every long steerpoint name). `FlightPlanBuilder._leg_speed` is the one derivation
  both cells read.
- **The `Brg` column is back (2026-10-25).** Dropped 2026-06-27 (#244) as clutter, restored on
  request: the true course of the leg into each row, three digits, upstream's
  `heading_between_point`, the coalesced target-points row included. Ten columns fit the worst
  case only at 15 pt, so `FLIGHT_PLAN_FONT_SIZE` went 16 → 15 rather than cutting the 25-char
  action names; `FLIGHT_PLAN_HEADERS` and the width test share the constants.
- **Daytime paper tone (2026-10-25).** The light text pages went 210 → 185 grey and the recon
  light palette from near white (250) to 205, with the ATIS panel and diagram badges matched; the
  inks were darkened with the paper so each stays at 4.5:1 or better
  (`test_kneeboard_paper_tone.py`). The dark kneeboard is unchanged.
- The **Friendly Packages** list moved out of the bottom of Mission Info to its own
  `FriendlyPackagesPage` (still two-column + paginating), so the list isn't split across Mission
  Info and a near-empty spill page; the package targets **map** stays as the spatial complement.
- The standalone **SEAD/Strike Target Info** page is suppressed when the recon **Detail** page
  covers the same target — that page already lists the emitters + role + HARM **ALIC** over a
  satellite view — **but only in EXACT intel** (the recon page shows exact coords while the task
  page intentionally fuzzes them in Approximate mode, §5, so the fold never leaks a fuzzed target).
The wiring lives in `KneeboardGenerator.generate_flight_kneeboard`. Visual change → in-game pass
**H8 ☑ VERIFIED 2026-06-26**.

**Custom kneeboard import (UI, stored in the save).** DCS kneeboards are per-**airframe**, not
per-flight, so to add your own kneeboard page to a fleet of player flights you'd otherwise
hand-edit each `.miz`. The **Kneeboards** toolbar/menu action (`QCustomKneeboardsWindow`) lets
the campaign owner import an image once — normalised to PNG bytes and stored in the campaign
save as `game.custom_kneeboards` (a list of `CustomKneeboard` = name + bytes + optional
`airframe_id`) — and have it injected into every client flight's kneeboard at generation, or
scoped to a single airframe (the finest grain DCS allows). Injection is
`KneeboardGenerator._inject_custom_kneeboards()`: bytes → temp PNG → `mission.custom_kneeboards`
(the `""` key = all client flights, an airframe id = that type only), mirroring the existing
global `Saved Games/.../Retribution/Kneeboards` folder loader but **per-campaign** (no
cross-campaign leakage). Old saves migrate via a `__setstate__` `setdefault`. Covered by
`tests/missiongenerator/test_custom_kneeboards.py`; the Qt dialog itself: in-game pass ☑ VERIFIED 2026-06-26 (H4).

**Threat Intel Brief kneeboard (auto-generated enemy AD dossier).** A `ThreatIntelBriefPage`
(`game/missiongenerator/kneeboard/`) auto-generates the enemy air-defense dossier for a player
flight as **one card per system** (sites aggregated), modelled on the per-system threat cards in
professional campaign Intelligence Briefings (design note `retlab-campaign-doc-ideas-harvest.md`).
`build_threat_intel_cards()` groups enemy `SamGroundObject` / `EwrGroundObject` by system and each
card pairs the **live** campaign numbers — engagement range, search-radar range, live/dead site
counts, and bullseye cues — with a catalog entry from `game/data/threat_reference.py`
(`ThreatReference` = NATO name, guidance, ceiling, RWR symbol, and a "how to beat it" line), keyed by
the DCS unit ids of the system's radars and launchers.
**Rebuilt 2026-10-07** after a flown page briefed an SA-10 as a heat-seeker: the catalog lacked
the Flap Lid-B, so the old scan borrowed the stats of the site's SA-13 guard; the HARM ALIC code
came from whichever radar was listed first; four hand-typed ceilings were wrong. Now: ceilings are
each missile's `H_max` from `CoreMods\tech\TechWeaponPack\Database\Weapons`; RWR symbols replace
the HARM code and come from `AN_ALR_SymbolsBase.lua`; the "how to beat it" lines follow the
squadron's Soviet SAMs guide, and a system that guide does not cover (the Western SAMs) carries no
line. Only units in a site's best identity tier may identify it, highest-ceiling system wins, and
an uncatalogued best tier borrows nothing. The Hawk's 131,000 ft is DCS's own `H_max`. Row B190.
A card's **name and
reference** come from `_system_identity()`, which ranks a site's units by `_CARD_IDENTITY_PRIORITY` so
the **weapon system** (track radar / TELAR / launcher — the HARM-targetable shooter) is what names and
describes the card, *not* the co-located search / acquisition / EW radar whose DCS display name reads
"… SR". This is deliberately the inverse of the recon-map ring's `_greatest_alive_threat` (which keys
on the lethal radar to size the engagement ring): a SEAD/DEAD brief should read "SA-5 S-200 Square Pair
TR", not "ST-68U Tin Shield SR" — and it fixes a real bug where an SA-5 site pulled the weaponless EWR
reference ("No weapons") from its acquisition radar despite a 138 nm MEZ. A bare radar site (nothing
lethal co-located) still honestly names itself. **Recon-fog aware** (§3): a site the player has not identified
(`known_for(player)` False) contributes only to a per-band "Unidentified MERAD" card — system,
ring, RWR symbol and how-to-beat line withheld until the site is engaged. The unidentified cards
also **withhold the count**: how many unidentified (often mobile) sites are in theatre is intel we
wouldn't realistically have, so they drop the "N site(s)" headline and the intro's running total, and
their detected-contact bearings overflow to an ellipsis (`_unknown_cues_text`) rather than a "+N" total
that would leak the count. Cards sort live-most-lethal → unidentified and pack down the
page; overflow flows onto `(cont.)` continuation pages via the page's own card-packing
`paginate()`. Gated by `generate_threat_intel_kneeboard` (default OFF); covered by
`tests/missiongenerator/test_threat_intel_kneeboard.py`. In-game pass ☑ VERIFIED 2026-06-26 (H5). *(Per-system
photos were evaluated and deferred — DCS ships only `.dds` model textures, not portraits; reading
+ converting them at gen-time is fragile for marginal value on a 960px page.)*

**Package code words were removed 2026-10-12 (DM call): the setting, `game/ato/codewords.py`, `Coalition.code_words`, the BLUF line, the Support Info block, the ATO panel table and tooltip, and the PUSH tag on the join waypoint. `game.ato.codewords` is in `REMOVED_MODULES` and `Coalition.__setstate__` drops the saved table. Verified working (row H6) and off in the DM's defaults and every save. What follows is the record.**

**Mission code words + Comms & Brevity card.** A squadron-grown idea, modelled on the Red Flag
81-2 kneeboards: the whole side shares **one mission-wide code-word table** — a **push word per
task** (`STRIKE / SEAD / OCA / CAS / ANTISHIP / CAP / EW`) plus the event words `SUCCESS` /
`ABORT` (+ `STOP JAM` only when an EW/jamming flight is in the ATO) — so a single call ("Cobalt")
tells everyone SEAD is pushing (`game/ato/codewords.py`: `MissionCodeWords`, `PushCategory`,
`push_category_for`). It's owned by the **`Coalition`** (a `code_words` property generated once per
turn from a randomly chosen *themed* word pool, stored so it's stable while a planner briefs and
regenerates the mission, and pickled; `getattr` migrates old saves), so one table feeds everything
and a new turn draws a fresh themed set. The pools are deliberately **short single words** (metals,
colors, stone, animals — `Steel / Spectrum / Bedrock / Pack`) chosen to be quick and unambiguous over
the radio, with no two-word phrases and nothing that collides with a stock DCS callsign or brevity term. Because **planners brief off it before the `.miz`
exists**, it's surfaced pre-generation as a **persistent code-word panel** in the ATO package list
(`qt_ui/widgets/ato.py` `QPackagePanel.refresh_code_words`, an HTML table refreshed on
`layoutChanged`), a per-package **tooltip** (`AtoModel` `ToolTipRole`, that package's push word +
events), and a **`PUSH <word>` tag echoed on the JOIN waypoint** for the flight's task
(`WaypointBuilder._join_pretty_name` — JOIN is the package commit point and never a `TARGET_POINT`,
so it can't leak into DTC slot tags). In-cockpit, the words live on the stock pages since the
2026-07-13 back-to-upstream rework: the flight's own PUSH/SUCCESS/ABORT in the **Mission Info BLUF**,
and the full push table (the flight's own task row marked `(you)`) + events as a **Code Words block
on the Support Info page** (`CodeWordsBlock` / `SupportPage._render_code_words`). *(The standalone
Comms & Brevity card and its task-filtered brevity crib — `BrevityCard`,
`game/data/brevity_reference.py` — were struck in that rework's markup pass and are deleted.)* All of
it is a *human* comms aid — nothing scripts off the words (multiplayer missions, not the
single-player campaigns the idea came from). One toggle, `enable_package_code_words` (default OFF),
gates the panel, tooltip, waypoint echo, and kneeboard surfaces together. Covered by
`tests/ato/test_codewords.py` + `tests/missiongenerator/test_kneeboard_bluf.py`; in-game /
planner-UI pass ☑ VERIFIED 2026-06-26 (H6, pre-rework surface).

**Fuel ladder — folded into the flight plan (2026-07-05).** The flight-plan table on Mission Info
carries a **`Fuel` column**: the **planned fuel remaining** at each RTB steerpoint
(`FlightWaypoint.fuel_planned`, the forward pass `WaypointGenerator._estimate_planned_fuel_for`
that subtracts each leg's burn from the starting load `flight.fuel × KG_TO_LBS − taxi`, topping
back up at a tanker `REFUEL` waypoint). It deliberately does **not** print the old Plan/Min/Margin
trio: the per-waypoint margin (Plan − Min) is **constant across the whole route by construction**
(start fuel − total burn − reserve, since the two figures are walked from opposite ends with the same
per-leg burn), and Min is just Plan minus that constant — so both repeated the same number on every
row. They collapse to a single **RTB margin** call-out under the table (`+N` spare, or an
amber `−N` "tank or divert" warning), computed as the worst-case `min(fuel_planned − min_fuel)` so a
tanker leg's reset is still caught (`FlightPlanBuilder._format_fuel` / `fuel_margin_line`).
Post-landing reference points (e.g. the bullseye, which carry a forward-burn `fuel` but no
min-to-RTB) get a blank cell. The burn model is approximate (it's the same estimate that drives
`min_fuel`), so treat the figures as planning numbers. **History:** this began as a standalone
`FuelLadderCard` page (gated `generate_fuel_ladder_kneeboard`, in-game ☑ VERIFIED 2026-06-26, H7 —
one of the three kneeboard ideas harvested from the campaign-doc study,
`retlab-campaign-doc-ideas-harvest.md`); the back-to-basics pass exposed it as a near-empty page, so
per the user's call ("why can you not build the fuel table into the flight plan?") the page + the
setting were deleted and the column always rides in the flight plan. Model covered by
`tests/missiongenerator/test_fuel_ladder.py`; the column + margin semantics by
`tests/missiongenerator/test_flightplan_fuel_column.py`.

*Estimated-fuel fallback for dataless airframes.* The ladder originally only rendered for the ~22
airframes that ship a hand-measured `fuel:` block (`AircraftType.fuel_consumption`); everything else —
including the **C-130J "King"**, the helicopters, and the warbirds — showed *"No fuel estimate available
for this aircraft."* `AircraftType.estimated_fuel_consumption` (`game/dcs/aircrafttype.py`) now
synthesises a rough `FuelConsumption` from the airframe's internal capacity (`fuel_max`) scaled by an
assumed still-air cruise endurance, bucketed **helicopter / heavy-transport / combat** (heavy detected
by pydcs default task — Transport/Refueling/AWACS/Reconnaissance — or airframe length ≥ 28 m). The
combat bucket is calibrated against the measured references (F/A-18C ~22 ppm, F-16C ~12 ppm; the
estimate lands at ~21 for the Hornet) and the heavy bucket against the C-130J (~16 ppm); climb/combat
are multiples of cruise. It is **kneeboard-scoped on purpose** — the waypoint generator's two estimate
passes (`_estimate_min_fuel_for` / `_estimate_planned_fuel_for`) resolve `fuel_consumption or
estimated_fuel_consumption` and thread the chosen one through `FlightPlan.fuel_consumption_between_points`
(now taking an optional `consumption` override), but **`unit_type.fuel_consumption` is left `None`**, so
the flight planner's tanker tasking (`formationattack`) and the in-flight fuel sim (`inflight.py`) keep
using measured data only and gain no new blast radius. A real `fuel:` block always wins. Covered by
`tests/dcs/test_estimated_fuel_consumption.py`.

*Measured `fuel:` data adopted from DCS Liberation (2026-08-07).* Liberation — which Retribution
forked from, and which is **still actively developed** (see *Repo & Branch Layout* in `CLAUDE.md`) —
ships hand-measured blocks for twelve airframes the fork had none for. All twelve were adopted
verbatim, provenance comments included: **A-10A, A-10C, A-10C_2, A-4E-C, AV8BNA, F-100D,
F-14A-95-GR, F-14A-135-GR, F-14A-135-GR-Early, F-14B, F-15C, F-4E-45MC**. Measured-data coverage
went **22 → 40 aircraft types** (the twelve files fan out to 16 variants; the rest is inheritance).
The estimate these replace overshot the measured cruise burn badly on exactly the airframes the
squadron flies most:

| Airframe | Estimated cruise | Measured | Error |
|---|---|---|---|
| F-14A / F-14B | 31.2 ppm | 13 | +140% |
| F-15C | 25.9 ppm | 11 | +135% |
| A-10A / A-10C | 21.3 ppm | 12 | +78% |
| A-4E-C | 10.5 ppm | 7.7 | +36% |
| AV-8B | 14.9 ppm | 11 | +35% |

Two consequences, and the second is the one to watch. The kneeboard bingo ladder for those jets was
reading ~2.4× pessimistic and is now right. But adopting a real block also promotes them out of the
kneeboard-only fallback and onto measured `unit_type.fuel_consumption`, which **does** drive tanker
tasking (`formationattack`) and the in-flight fuel sim (`inflight.py`) — the intended design ("a real
`fuel:` block always wins"), but a genuine behavior expansion for twelve airframes at once. Tracked
as an in-game-pass row. The F-4E block is the best-sourced of the set — Dash-1 Supplemental Data and
the Heatblur manual's mission-planning section, with drag index and gross weights in the comments,
rather than a stopwatch run. `tests/dcs/test_estimated_fuel_consumption.py` pins all 16 variants
against their cruise values so the data cannot silently regress; the same file's fallback test was
re-pointed from the A-10C (which now *has* a block) to the MiG-29A.

The remaining ~217 airframes still fall back to the estimate. The measurement procedure for closing
that gap is already in the tree at `docs/modding/fuel-consumption-measurement.md`.

*Combat-bucket constant retuned 520 → 700 NM (2026-08-07).* Adopting the twelve blocks took the
calibration set from **two** references (F/A-18C, F-16C) to **nine independent** ones, which made it
worth re-deriving the constant. An earlier draft of this section called the resulting overshoot a
"weakness"; that was wrong and is corrected here. **The overshoot was the deliberate price of a
conservative calibration**: 520 sat just above the thirstiest reference (the Hornet, implying 489 NM),
so the model treated every unmeasured airframe as a Hornet and almost never under-estimated.

The error is asymmetric, and that governs the choice. Over-estimating burn draws a pessimistic bingo
ladder and frags a tanker that may not be needed — annoying, safe. Under-estimating draws an
optimistic one and frags nothing — the jet lands dry. So the constant is picked to stay conservative,
**not** to minimise average error:

| Constant | Worst error | Optimistic (unsafe) references |
|---|---|---|
| 520 (was) | +140% (F-14) | 1 of 9 |
| **700 (now)** | **+78%** | **2 of 9** |
| 875 (best fit) | +42% | 6 of 9 — rejected |

700 is the *median* implied endurance across the nine references (spread 489–1246 NM). It roughly
halves the worst overshoot while keeping 7 of 9 on the conservative side. Two invariants in
`tests/dcs/test_estimated_fuel_consumption.py` lock that posture — no reference may be more than 35%
optimistic, and at least 7 of 9 must stay conservative — and both were verified to **fail** at 875
before being committed, so a future "improvement" toward best-fit trips CI rather than silently
flipping the safety bias.

Two things were tested and rejected on the way, recorded so they are not re-tried: a **linear fit**
(`ppm = 7.53 + 0.000512 × fuel_lb`) scores only 41% worst error against the constant's 42%, so it buys
nothing for the added complexity; and **`max_range` as the input** is worse still (77%) because the
yaml field is an authored *tasking* radius, not a physical one — the AV-8B is capped at 100 NM and the
A-10C at 150 NM by doctrine, not fuel. Capacity is a weak predictor and no single constant will fix
that; the real answer is measured data. The helicopter and heavy buckets are independent and were not
touched — the C-130J "King" still estimates ~16 ppm.

*Not every "measured" block is measured (audit, 2026-08-07).* The blocks carry test-condition
comments — the taxi route, the climb profile, the cruise mach and leg length — precisely so a number
is reproducible. Auditing them turned up **seven airframes wearing another jet's numbers with the
donor's comments attached**: the six `VSN_F35*` files carry the F/A-18C's values (`170 / 44.25 /
22.1 / 27.5 / 2000`) and `Tornado_ADV` carries the F-16C's (`200 / 28.33 / 12 / 26 / 1000`), each
including a `# Parking A1 to RWY 32 at Akrotiri` / `# Parking 44 to RWY 06L at Anderson AFB` line
describing a sortie never flown in that aircraft. **This is inherited, not fork-authored** — upstream
`dcs-retribution/dcs-retribution` `dev` carries the identical blocks and comments, and DCS Liberation
has no fuel block for either file. The **values are left alone** (they are the only figures anyone
has, and reverting them to the capacity estimate would be worse); only the comments were rewritten to
say `NOT MEASURED for this airframe`, name the donor, and point at the measurement procedure. Carve
candidate for upstream once the PR freeze lifts.

Deliberately **not** touched by that audit: same-family reuse, which is defensible and partly
Liberation's own choice. `FA-18E`/`FA-18F`/`FA-18ET`/`FA-18FT`/`F_A-18C`/`EA-18G` share the Hornet
block (Liberation itself ships the Super Hornet and Growler that way), and the `F-16D_*`/`F-16I`
marks share the F-16C block. The F-35 and the Tornado are different airframes entirely, which is why
they are the clear-cut cases.

**Compact 3-4 page kneeboard deck — RETIRED (2026-07-05, the back-to-basics rework).** The compact
folding machinery (`compact_kneeboard`, `_compact_kneeboard_pages`, the `CombatIntelPage`/
`CommsCoordPage`/`FlexReferencePage` composites, `_draw_section_if_fits`, the adaptive flex page and
the fuel-ladder backfill) was the fork's biggest source of `kneeboard.py` churn against upstream and
the most fragile part of the deck. It is **deleted**.

**Back-to-upstream deck rework (2026-07-13).** A user markup pass on a flown Scenic Route Merged deck went
further: back to **upstream's page set**, with the RetLab info the markup kept folded into those
pages. The cover page (§30) and Brief Sheet + Comms & Brevity card (§31) are deleted; the per-flight
deck is now upstream's **Mission Info → Support Info → Notes → task page** plus the setting-gated
extras. What the deck keeps, and where:

- **Mission Info** leads each flight's block (upstream order), with the **BLUF block** — task/TOT,
  push words (code-words toggle), §51 JAM BACKUP, the compact **THREATS AIR/SAM** lines, **LOADOUT**,
  and the **SAR** if-down line — then the stock airfield table (+ATIS), the flight plan with the
  **Fuel column + RTB margin**, upstream's `Bullseye:` line, weather, bingo/joker, laser codes, and
  the §29 **SITREP** section at the bottom.
- **Support Info** keeps the comm ladder / AEW&C / tankers / JTAC / airfield directory and gains the
  **Code Words block** (gated by `enable_package_code_words`).
- The **shared-airframe flight index** (§27) is a standalone conditional page again.
- The **Threat Intel Brief** page (`generate_threat_intel_kneeboard`) stays default **ON**; the other
  optional pages (target recon imagery, friendly packages + map) are unchanged.

BLUF composition is covered by `tests/missiongenerator/test_kneeboard_bluf.py`. The old H9 checklist
row is superseded by these retirements; H12 tracks the reworked deck's in-game pass.

---

## 5. Player target location precision

`TargetIntelPrecision` enum (`EXACT` / `APPROXIMATE`) in `game/settings/enums.py`
controls four behaviors together when set to Approximate:

- Player-only target steerpoints are offset to a randomised area within 1–3 NM of
  the real target rather than placed exactly on it. The waypoint is renamed
  `TARGET AREA`. AI attack logic is unaffected.
  (`game/ato/flightplans/waypointbuilder.py` `_player_visible_target_area_position()`)
- DEAD and SEAD flights drop the per-emitter `TARGET_POINT` waypoints entirely and
  fly a single fuzzed target-area waypoint instead — mobile SAMs relocate between
  intel updates, so handing the player an exact fix per launcher/radar defeats the
  "go find it" intent. The `Builder.layout()` of both flight types passes the
  per-unit list only under Exact intel, falling back to the area waypoint otherwise
  (`game/ato/flightplans/dead.py`, `sead.py`). **Strike is deliberately exempt**:
  its targets are fixed installations (buildings, bunkers, bridges) whose
  coordinates are reliable, so `strike_point()` always emits exact per-unit points
  regardless of the setting (`waypointbuilder.py` `_target_point(..., approximate=False)`).
- Objective F10 map marks are suppressed even if `generate_marks` is on.
  (`game/missiongenerator/triggergenerator.py`)
- Strike / SEAD / DEAD kneeboard target pages omit exact coordinates. The Strike
  page cues the player to search the target area; the SEAD/DEAD page (`SeadTaskPage`)
  in **cue mode** (DEAD always, or Approximate intel) shows **one consolidated cue**:
  a heading line with a single **rough bullseye** for the **center of the site**
  (`Bullseye <brg> for <nm>`, ~1 NM accurate) plus the single **target-area STPT** (the
  per-target waypoint nearest the site center), then a `Description | ALIC` table of the
  site's emitters. This replaced a per-unit bullseye on every row, which was cluttered.
  In **exact** mode (SEAD with Exact intel) the page keeps the per-emitter
  `STPT | Description | ALIC | Location` table with precise coords; that STPT pairs each
  target to its `TARGET_POINT` waypoint **by order** (not position), so it stays
  populated even when Approximate intel offsets the waypoint.
  (`game/missiongenerator/kneeboard/`)
- **Emitters only, not the whole site.** Both tables list only the **HARM-targetable emitters**
  — units with an **ALIC** code (radars and self-contained TELs) via `_emitter_units` — not the
  launchers, command trucks and AAA guns that pad `strike_targets`. The cue table additionally
  **dedupes by type** (one row per `Description | ALIC`), so it neither enumerates every launcher
  nor publishes exact unit counts. A site with no coded emitter (a pure AAA/launcher group) falls
  back to the full unit list so the page is never blank. The exact view keeps one row per emitter
  (distinct coords) and preserves the by-order STPT pairing via the unit's original index.
- **A SEAD flight's steerpoints are emitters too** (2026-09-01). The waypoints did not follow the
  kneeboard until this change: `SeadFlightPlan` called `strike_targets_for`, so a jet fragged
  against an SA-2 got a `TARGET_POINT` per *unit* — search radar, both §60 track radars, every
  launcher, and the layout's Logistics/Fuel/AAA slots (two GAZ-66, two TZ-22 bowsers, two ZU-23).
  A HARM shooter loitering at standoff cannot use a bowser steerpoint, and the enumeration
  published the composition and exact unit counts this page is written to withhold.
  `TheaterGroundObject.sead_targets` now narrows `strike_targets` to
  `SEAD_TARGET_UNIT_CLASSES` (`game/data/units.py`: the radar classes, plus `TELAR`, `SHORAD`
  and `LAUNCHER`), and `FormationAttackBuilder.sead_targets_for` builds the waypoints from it.
  **DEAD is unchanged** — it kills individual launchers, so it keeps the full per-unit list.
  Three constraints, each with a test:
  - **The filter is class-based, never ALIC-based.** `game/data/alic.py` is a hand-curated
    vanilla table, so an ALIC filter would drop every HDS radar (§41). A unit whose type is
    unregistered (`unit_type` raising `StopIteration`) is **kept** — unknown is not absent.
  - **`sead_targets` falls back to the full roster when nothing matches**, so a SEAD flight
    hand-fragged onto an emitterless site still gets `targets[0]` for the timing math.
  - **`SeadTaskPage.target_units` must read the same list the flight plan built from**, because
    `_emitter_units` pairs to `_target_point_numbers()` **by index**. Leaving it on
    `strike_targets` while the waypoints shrank ran the index off the end of the shorter
    waypoint list and printed a blank STPT for every emitter after the first support vehicle.
- **Recon-fog redaction (§3).** Both the cue and exact views only list the emitters once the
  site is **identified**: `SeadTaskPage._target_identified` gates on
  `TheaterGroundObject.known_for(viewer)`, and an un-discovered site is redacted to its
  **intel-tier band** + a bullseye cue + "Composition not yet identified — fly TARPS recon…",
  withholding the emitter breakdown and HARM codes until the site is scouted/struck/photographed
  (the same way the Threat Intel Brief redacts unknown sites). Without this the SEAD target list
  handed over the full composition of any un-recon'd site, defeating recon's purpose. *Known gap:*
  the experimental recon **Detail** page still draws the composition from satellite imagery
  regardless of `known_for` — a deeper question for that page (it IS a recon product), tracked
  separately; the standalone SEAD page is the one fixed here.

---

## 6. Air-defense planning rework — GEOMETRY REVERTED TO UPSTREAM (2026-08-09)

> **Status.** The planning *geometry and volume* half of §6 was reverted to upstream
> behavior on 2026-08-09 as work order D of the planner re-convergence decision
> (`docs/dev/design/retlab-autoplanner-upstream-divergence-audit.md`, DECIDED block).
> The DM's call was that default planner behavior returns to upstream regardless of
> how deliberate each divergence was. Reverted outright, not re-gated — recover from
> git history if any of it is ever wanted again.
>
> **Removed:** front-anchored support-orbit placement and the AI depth asymmetry
> (U29) · AWACS/tanker lateral orbit spreads (U30; AEW&C got a step-back spacing
> instead on 2026-09-17, see the next section) · the red forward-middle BARCAP
> layer (U17) · the front-anchor defense guarantee and the seeded per-CP
> aggressiveness roll (U1) · threat-weighted BARCAP volume and orbit forward-bias
> (U2, U37) · the FLOT navmesh hazard capsule and the `air_engagement` escort zone
> (U42, taking the U10 escort-reach gate with it).
>
> Deleted with them: `game/ato/flightplans/supportorbit.py`,
> `game/ato/flightplans/airspacegeometry.py`,
> `game/commander/tasks/primitive/forwardbarcap.py`, `ForwardBarcapZone`,
> `ObjectiveFinder.air_threat_score` / `normalized_air_threat` /
> `FRONT_LINE_AIR_THREAT` / `_offensive_roll`, `ThreatZones.air_engagement` /
> `aircraft_engagement_range` / `_front_line_threat_zone` /
> `FRONT_LINE_THREAT_BUFFER`.
>
> **Kept** (each independent of the reverted geometry): the overlapping CAP waves
> below (byte-parity with upstream at `barcap_overlap_time == 0`) · the
> `cap_orbit_distance_band` band-collapse fix (U36, a genuine upstream bug) · the
> strike-escort reserve trim, now doctrine-gated and Vietnam-only · the
> viewer-aware fog threading in `threatzones.py` (§3 plumbing) · `HomeBaseDefenseZone`
> (§1 player QRA) · the front-line spawn-stacking fix.

What remains of §6:

Design notes: `docs/dev/design/retlab-air-defense-planning-notes.md` (read this for intent).
- Overlapping CAP waves: `game/commander/missionscheduler.py` (uses
  `barcap_overlap_time`); rounds math in `game/commander/theaterstate.py`.
  **Land CPs only** schedule overlapping waves; carriers keep the legacy
  simultaneous-stacking behavior. The first wave (a carrier's first stack) is an
  ASAP package; relief waves chain behind it and are never flagged ASAP, because
  the package editor re-runs ASAP on every edit and would pull a relief wave onto
  the first. The first-wave jitter (up to 5 min) was removed 2026-09-29, when
  support packages went ASAP (DM call). With `barcap_overlap_time == 0` this
  reproduces the old back-to-back schedule exactly.
- Support packages are ASAP (2026-09-29, DM call): theater and carrier tankers
  (`PlanRefueling.asap`) and every AEW&C station (`PlanAewc.asap`, which the
  planner had ignored; only the first AWACS was ASAP). Tankers had been on the
  random strike spread, so a tanker could arrive 50 min into a 60 min mission.
- Climb-out floor (2026-10-09, row B205): the leg out of the TAKEOFF waypoint of a
  ground-started patrol plan (`PatrollingFlightPlan`: BARCAP, TARCAP, AEW&C, tanker,
  King) takes at least `JOIN_UP_TIME` (2 min) plus the climb to the next waypoint at
  `CLIMB_RATE_FT_PER_MIN` (3,000), in `game/ato/flightplans/patrolling.py`. Upstream
  times every leg as distance over speed, so a CAP over its own field was on station
  6 seconds after takeoff (Anatolian Reach turn 1). A floor, not an addition: a long
  first leg is unchanged. Formation and strike plans are untouched (DM call). The
  numbers are an estimate, erring early; B205 measures them. `InFlight` spends the
  same leg time so the turn simulation keeps pace.
- BARCAP volume is upstream's flat allocation: `2 * barcap_rounds` for a fleet CP,
  `barcap_rounds` otherwise, over `ObjectiveFinder.vulnerable_control_points()`
  (upstream's airfield-proximity rule with its unseeded per-call aggressiveness roll).
- Strike-escort reserve trim (`trim_rounds_for_escort_reserve`,
  `game/commander/theaterstate.py`): when `Doctrine.strike_escort_reserve > 0` the
  planner gives up BARCAP rounds so ~reserve airframes stay untasked for the strike
  escorts planned later in the same run. **Why it exists:** the M4 Vietnam flight
  observed *every* strike escort being pruned at Linebacker tempo — BARCAP consumed the
  fighters first and the strikes went out bare. Only Vietnam sets a non-zero reserve (4), so
  this is a no-op everywhere else. The companion fence is
  `PackageFulfiller.escort_reserve_withholds`. Trim order is the planner's own CP
  order — it used to rank by air threat, but that field went with the revert; the
  number of jets freed is unchanged. Tests:
  `tests/commander/test_escort_reserve_trim.py`, `tests/commander/test_escort_reserve_fence.py`.
- CAP orbit band (`cap_orbit_distance_band`, `game/ato/flightplans/capbuilder.py`):
  when the defended point sits inside the enemy threat zone the old
  `min(cap_*, distance_to_no_fly)` drove both band bounds onto a sub-minimum (often
  negative) value, placing the racetrack *behind* the defended point and killing all
  placement jitter. Falls back to the full doctrine band instead. This is an upstream
  bug and is queued as a post-freeze carve. Tests:
  `tests/ato/flightplans/test_cap_orbit_distance_band.py`.
- Engagement-range bumps: `cas_engagement_range_distance` 10 -> 15 NM,
  `armed_recon_engagement_range_distance` 5 -> 10 NM. **Planner suite only since 2026-09-22**:
  the defaults are upstream's 10 / 5 and the suite sets 15 / 10 (divergence audit, amendment).
- Cruise/patrol altitude doctrine (Campaign Doctrine page, all default to **no behavior
  change**, settable per campaign so the squadron tunes altitude to taste rather than the
  hardcoded ~24k Hornet CAP):
  - **Altitude scatter band** — replaced the single symmetric `max_plane_altitude_offset`
    (rolled `randint(0,max) * +/-1`) with a `[min_plane_altitude_offset,
    max_plane_altitude_offset]` band (x1000 ft, defaults -2/+2 = the old +/-2k spread).
    Equal bounds disable scatter (0/0 = none); an asymmetric band biases it (0/+4 =
    climb-only). The roll is the pure, tested `roll_plane_altitude_offset(low, high)` in
    `game/ato/flight.py` (used by `Flight.__init__`).
  - **Minimum patrol altitude** (`min_patrol_altitude`, x1000 ft, default 0 = off) — floors
    CAP/patrol legs to at least this altitude *after* the scatter, capped by the doctrine's
    `max_combat_altitude`; flights already higher are untouched, helos exempt. Pure helper
    `apply_patrol_altitude_floor()` called from `WaypointBuilder.get_patrol_altitude`
    (`game/ato/flightplans/waypointbuilder.py`).
  - On old saves, `_migrate_legacy_settings` mirrors the legacy symmetric
    `max_plane_altitude_offset` into the new minimum (`min = -max`), so every existing
    save keeps its exact band — including `max = 0` (scatter deliberately off) and
    widened bands like `max = 5` (a flat `-2` default would have re-enabled or reshaped
    those). Fields render on the Campaign Doctrine page (no UI wiring). Tests:
    `tests/test_flight_altitude_settings.py`. Mirrored on upstream PR #806.
- ~~Route around the front line~~ — **REMOVED 2026-08-09** (U42, see the status banner
  above). The active front is no longer a navmesh routing hazard; `ThreatZones.all` is
  upstream's `airbases ∪ air_defenses` again, and transit routing no longer knows the
  FLOT is there.
- Front-line units no longer stack: `game/missiongenerator/flotgenerator.py`
  `get_valid_position_for_group()` steps perpendicular from the (valid) front toward the
  requested depth instead of snapping laterally via `find_ground_position()` — the old
  lateral snap collapsed every off-map group onto the same patch, piling units on one tile
  (worst for deep roles: artillery/logistics at 16-20 km).

### Jank fixes (2026-06-21)

A consumer-level audit of the above (everything except QRA/scrambling, §1) found four real
problems; all four are fixed:

- **HIGH — FLOT units spawned *on* the front line.** `flotgenerator.py`
  `get_valid_position_for_group()` returned the depth-0 point the instant the first 250 m
  perpendicular step hit water/off-map, so on coastal/river/narrow-land fronts deep roles
  (artillery, logistics) spawned in direct contact — the same stacking class the rework was
  meant to fix, relocated to depth 0. Now, if the perpendicular walk can't reach at least
  half the requested depth, it falls back to a lateral `find_ground_position` search around
  the **intended-depth** point so the group keeps its depth (and spreads instead of
  stacking). **Lua-free; in-game pass ☑ VERIFIED 2026-06-25 (checklist B1, coastline map).**
- **MEDIUM — red's defensive posture flickered.** The per-CP "plan offensively instead of
  defending" decision in `vulnerable_control_points()` was an **unseeded** `randint` re-rolled
  every planning pass, so red defended a base one pass and abandoned it the next for identical
  board state. Now `ObjectiveFinder._offensive_roll(cp)` seeds a `random.Random` per
  `(turn, cp.name)`: stable across all passes within a turn (coherent posture), still varies
  turn to turn.
- **MEDIUM — threat score counted the wrong aircraft.** `air_threat_score` summed **all**
  present fixed-wing (bombers/tankers/transports included), so a non-fighter base stole BARCAP
  waves from a sector facing actual fighters. Now counts only BARCAP/TARCAP-capable types.
- **MEDIUM — front-line-only sectors got no volume boost** (the two flagship pieces were
  decoupled). A CP vulnerable *only* via `has_active_frontline` scored 0 and never earned
  extra waves. Now such CPs get a `FRONT_LINE_AIR_THREAT` floor (additive with any nearby-
  airbase score), so a contested front earns roughly half the threat bonus even with no enemy
  airbase in range. (Intent confirmed by the maintainer: hot fronts *should* get more waves.)
- **Capsule clipping (from the same audit):** the navmesh front-line hazard now uses the
  land-clipped FLOT bounds instead of the full nominal 80 km width centered on the raw
  strength-derived point, so the ~117 km × 37 km band no longer spills across water/empty
  flanks or sits laterally offset from the actual battle (see the route-around bullet above).

Tests: `tests/test_objectivefinder_barcap.py`, `tests/test_barcap_threat_weighting.py`,
`tests/test_front_line_threat_zone.py`. Remaining LOW audit items (e.g. no clamp on
`barcap_rounds` when `barcap_overlap_time` ≥ mission duration, one-sided lateral spread,
250 m magic step) are deferred.

### Front-anchored support-orbit placement (AEW&C + tanker) (2026-06-22) — REMOVED 2026-08-09

> **Removed** by work order D of the planner re-convergence (U29/U30). `aewc.py` and
> `theaterrefueling.py` are back on upstream's geometry: anchor on the package target,
> step off the nearest threat boundary by the configured buffer, no front anchoring, no
> player-forward / AI-deep depth asymmetry, no lateral spread between multiple orbits.
> `supportorbit.py` is deleted. The failure modes it fixed are upstream's again — they are
> real, and the tests that pinned them are gone. The removed design and those failure
> modes are in [`retlab-features-history.md`](retlab-features-history.md) under §6.
>
> **2026-09-17 — AEW&C spacing and a land-only anchor, on a fresh DM call; U29 did not
> come back.**
> 1. **AEW&C on one station step back from the threat, ungated.** `aewc.py` is
>    deterministic in its target, so two AWACS on one station flew the identical racetrack,
>    and the revert left AEW&C with no spacing while the tanker got `TANKER_ORBIT_SPACING`.
>    The August sideways spread was reviewed and **not** restored: with the target list
>    deduped it only fires on a hand-fragged second AWACS, and there the first -- laid out
>    alone, never again -- stayed put while the newcomer moved 30 NM, so two 60 NM tracks
>    shared 30 NM of line; it also shifted with no threat check (8 of 101 track samples
>    inside red's zone on `brady.retribution`) and shared a turn point. Each further AWACS
>    now steps `AEWC_ORBIT_SPACING` (20 NM) back from the threat, the tanker's pattern,
>    taking the nearest step clear of where the AWACS already on that station actually
>    orbit (read from their existing plans, never built). A first version counted the
>    AWACS ahead of it in ATO order; a second review showed that collides when an AWACS is
>    added to an earlier package, or one is deleted and another fragged, because a plan
>    already laid out never moves -- all three reproduced at 0.0 NM, now 20.0 NM. 20 NM, not the
>    tanker's 15: an E-3A flew 13.8 km off its leg on test 36 and its drawn box is 15.6 NM
>    wide. JAMMING shares the builder and never takes part. Probed on the real saves with
>    the first AWACS left un-replanned: 0/101 samples inside the zone, tracks 20.0 NM apart,
>    no shared turn point. Tests `tests/ato/flightplans/test_aewc_orbit_spread.py`.
> 2. **The tanker's step goes the right way on a threatened anchor.** It always subtracted,
>    which is "back" only when the anchor is clear; a threatened anchor's orbit sits past
>    the zone edge, so subtracting walked each extra tanker back toward the zone. On
>    `autosave.retribution` the second tanker went from 55 NM clear to 85 NM. Both builders
>    now call `patrolling.step_back_from_threat`.
> 3. **The land support anchor is land again (a bug fix, not U29).** Test 36's follow-up
>    showed three overlapping support bands near CVN-71. With every blue field inside
>    red's threat zone, `_support_hosting_anchor` returned None and both fallbacks --
>    which filtered only off-map spawns -- handed back a ship: the "land" AWACS anchored
>    on **LHA-1 Tarawa, 3.29 NM from CVN-71**, and the carrier's one E-2C squadron flew
>    two racetracks 14.9 NM apart beside its own tanker. Three causes, three fixes in
>    `objectivefinder.py`: `Lha` never overrides `is_carrier`, so the filter is now
>    `is_fleet`; `distance_to_threat` is unsigned (inside the zone it is *depth*), so the
>    old rear pick among threatened fields chose the one **deepest** in enemy airspace --
>    now ranked in two tiers, unthreatened first, then shallowest; and a threatened host is
>    taken **only when every land field is threatened**, so Incirlik's E-3A is no longer
>    skipped on turn 1 while a clear field still wins whenever one exists. The target
>    lists dedupe by identity, closing a latent path where the fallback returned a carrier
>    already in the list (seen on `brady.retribution` turn 3, hidden only by the hosting
>    walk finding Incirlik first). A wing with no land field gets no land anchor rather
>    than a phantom one on its own boat.
>    Replayed read-only on `autosave.retribution`: AEW&C `[CVN-71, LHA-1]` 3.29 NM apart
>    → `[CVN-71, Incirlik]` 81.8 NM apart; the land tanker station Gaziantep, which hosts
>    no tanker and sat 17.6 NM from the threat edge → Incirlik, which hosts the KC-135s.
>    `brady.retribution` (nothing threatened) is unchanged. Tests
>    `tests/test_aewc_targets.py`; in-game row B131.
>    **Known gap, pre-existing and unchanged:** an off-map spawn is not a station, so a
>    wing whose only land-side tanker lives off-map gets no theater tanker station
>    (RetakeTheFalklands blue: the KC-135 at "From US" flies neither before nor after;
>    before, the carrier was listed twice instead).
>    **A carrier with no AEW&C or tanker aboard gets no station of its own (2026-10-10,
>    DM call).** Each carrier was a target whether or not it based the aircraft, so a red
>    carrier's station was flown from the nearest land field, beside that field's own
>    land station. Read across the 76 bundled campaigns: five doubled up (Retake the
>    Falklands' two A-50 tracks started 0.1 NM apart; Caucasus Multi Russia flew two A-50s
>    and two IL-78s within 25 NM). `_carriers_flying_their_own` in `theaterstate.py` keeps
>    a carrier only when a squadron aboard is `capable_of` the task; the land station
>    covers the rest. A carrier that bases an E-2 or a tanker is unchanged.
>    **Known limitation of the step:** it moves along the line to the NEAREST zone edge
>    only, so in built-up multi-lobe geometry a later slot can step into a second lobe.
>    Reviewed 2026-09-17 and not acted on: it needs a station whose slot 0 already fails
>    its own buffer, the planner never puts two AWACS on one station, and no real save
>    reaches it.
>
> Two things did NOT come back: the theater-tanker demand reposition
> (`game/commander/tankerdemand.py`, still overrides the anchor — see the next section)
> and the U13/U14 AEW&C target/squadron picks in `game/commander/`, which are kept
> failure fixes and independent of the orbit math.

### Theater tanker placement from receiver demand (2026-06-25)

> **REVERTED 2026-08-09 (planner re-convergence, work order B).** The post-planning reposition pass (`game/commander/tankerdemand.py`) and the `Flight.refueling_service_point` it fed are gone; a theater tanker keeps the orbit its flight plan gives it.
> The code is deleted; rebuild it from git history if it is ever wanted again. See
> [the divergence audit](design/retlab-autoplanner-upstream-divergence-audit.md).

### Per-method theater-tanker fragging (2026-06-26, reverted 2026-08-09, REINSTATED 2026-08-17)

> **REINSTATED 2026-08-17 on a fresh DM call**, reversing work order B's revert of U15 for
> this item only. The rest of the 2026-08-09 re-convergence stands. Recorded in the
> [divergence audit](design/retlab-autoplanner-upstream-divergence-audit.md)'s DECIDED block.

Boom and probe are physically incompatible, so a wing flying both needs a theater tanker of
each. Retribution planned exactly one, ever — which is upstream issue
[#243](https://github.com/dcs-retribution/dcs-retribution/issues/243), open since 2024. The
recovery-tanker half was fixed upstream in 2025; the theater half was not.

**This is not the 2026-06-26 code rebuilt from history.** That version seeded several entries
into `TheaterState.refueling_targets`, producing one package per method. This one keeps the
single target and states the constraint at the proposal instead:

- `ProposedFlight.refuel_methods` carries an explicit tanker constraint, and
  `PackageBuilder._required_refuel_methods` prefers it over the set derived from the package's
  own receivers. A theater tanker has no receivers to infer from, so it has to say.
- `PlanRefueling` counts the refuel methods the coalition's squadrons actually take, ordered by
  how many take each, and proposes one tanker per method.
- **Every tanker is constrained to one method, the first included** (changed 2026-09-17, see
  below). The first is mandatory, so a wing short of any tanker still places a purchase order;
  every further one is `optional`, so a wing flying probe receivers without owning a drogue
  tanker still gets the boom tanker it can field rather than losing the package. A method
  counts only if a **land** tanker that dispenses it can actually be assigned to this station,
  and the type asked for is the one **the planner itself ranks best** there
  (`AirWing.best_squadrons_for`, the list the fill picks from) -- an untagged tanker passes
  that filter but covers no method. When no method qualifies (nothing declares one, or no
  fitting tanker can come) the single unconstrained tanker from before U15 is proposed. Never
  fewer than before, by construction.
- **Every tanker is ranked from the station.** Upstream's `PackageBuilder.plan_flight` ranks
  every flight after the first from the primary flight's departure field, so a tanker's
  escort launches near the tanker. A further tanker only exists because of U15 and serves the
  station, so a REFUELING flight in a REFUELING-led package keeps `package.target`; escorts
  are unchanged.
- `theaterrefueling.py` steps each further tanker `TANKER_ORBIT_SPACING` (15 NM) back from the
  threat. Without it both tankers get the same racetrack at the same altitude.

Tests: `tests/commander/test_theater_tanker_methods.py` (20),
`tests/commander/test_packagebuilder_tanker_location.py` (2). In-game row **B76**.

**2026-09-17 — the first tanker took the wrong method, and the second repeated it.** Found by
an adversarial review of the AWACS-anchor fix and reproduced on two real saves (Long Road to
H3, `autosave` turn 1 and `brady` turn 3): blue's land station got **two boom KC-135s and no
probe tanker** -- B76's fail signature word for word. The wing counts probe 8 / boom 3, so
`needed_refuel_methods` is `[probe, boom]`. The first tanker was left unconstrained on
purpose and took the wing's best squadron, which was the boom KC-135; the loop then proposed
`needed[1:]`, i.e. boom again, and the same squadron filled it. The loop assumed the free
first pick had covered `needed[0]`; nothing made it. The KC-135 MPRS (probe, two untasked at
Incirlik) was never asked for, so the land-based probe receivers -- the Mirage 2000Cs of
Escadron de chasse 1/30 -- had no land tanker. (Seven of the eight probe squadrons sit on
CVN-71 / LHA-1, which the carrier's own station covers.)

The first tanker is now constrained to the most-needed method too. Constraining it to
`needed[0]` alone would have been wrong: it is the mandatory flight, so a probe tanker that
exists but cannot reach the station would scrub a package that fills today. Hence the
assignability test above. The same fix stops a mixed wing with a single boom squadron being
asked for boom twice. Replayed read-only through the full planner on both saves: land
station **KC-135 boom + KC-135 boom → KC-135 boom + KC-135 MPRS probe**; the carrier's A-6E
station is unchanged. The regression test fails on the old code and passes on the new.

**Two more defects, found by an adversarial review of that fix before it shipped**, both
introduced by pinning the first tanker:
- The type came from the first match in **wing order**, not the planner's ranking. Reproduced
  as a direct regression on a single-method wing: with a KC-10 added at the station, the old
  code flew it from 0 NM and the pinned version a KC-135 from 160 NM. Now taken from the
  ranking.
- The second tanker was **ranked from the first one's field**, because of the upstream escort
  rule above. On `Vietnam tes` the probe KC-130 comes from Maykop, 134 NM out (the wing's only
  land probe tanker), and the boom KC-135 was then picked from Krymsk, **223 NM** out, while
  the station's own KC-135 sat at 0 NM. The unit-test fake ignored location, which is why the
  tests passed; `tests/commander/test_packagebuilder_tanker_location.py` now pins it.

Replayed read-only, origin/main in full vs the fix, **all 8 saves x both sides** (16 cases):
12 unchanged -- every red side among them -- and 4 blue changed, each from two boom tankers to
boom + probe (`autosave`, `brady`, `Vietnam tes`, and Red Tide's `test`). The bug was live on
every save with a mixed wing and a land probe tanker. No package lost, no method duplicated,
no boat's tanker pulled ashore, and on `Vietnam tes` the boom tanker now launches from the
station at 0 NM.

One defect found writing it: the orbit slot used `list.index`, which matches the first flight
that compares *equal* rather than the flight itself. Two tankers would have shared a slot the
moment `Flight` gained an `__eq__`. It compares by identity now.

### Refuel stops budgeted into flight-plan timing (2026-07-01)

**Symptom (player report, screenshot of a DEAD flight's waypoint list).** A flight with a
pre-vul tanker stop had under three minutes between its `REFUEL` waypoint and the join — the
schedule budgeted **zero** time on the boom. The tanker's own plan already budgeted service time
per receiver (`4 min × flight size + 1`), but the receiver's timeline treated `REFUEL` as a plain
nav point, so a tanking flight was always late to the join/TOT. Worse, the package tanker's
on-station window (`patrol_start_time`) was anchored **post-vul only** (TOT + egress legs), so a
pre-vul receiver reached the track long before the tanker existed there.

**Fix — both sides of the rendezvous budget the same stop** (shared
`refuel_service_time(flight_size)` in `game/ato/refueltasking.py`):

- **Receiver dwell** — `FlightPlan.total_time_between_waypoints` adds `refuel_duration`
  (= the tanker's per-receiver budget) to any edge leaving a `REFUEL` waypoint. Because takeoff
  time and the chained waypoint ETAs sum this method per leg, everything before the tanker
  (takeoff included) shifts earlier and everything after keeps its time.
- **Hold push through the tanker** — `FormationFlightPlan.push_time` now follows the actual
  route from the hold to the join (nav legs + the pre-vul stop) instead of the straight
  hold→join line, so the flight departs the hold early enough to tank and still make the join.
- **Sim sync** — the fast-forward sim (`flightstate/inflight.py`) spends the planned stop on the
  `REFUEL` leg too, so simulated positions don't run minutes ahead of the DCS-written ETAs.
- **Tanker window opens pre-vul** — `PackageRefuelingFlightPlan.patrol_start_time` is
  `min(post-vul anchor, earliest pre-vul receiver arrival − 1.5 min)` (receiver arrival via its
  `chained_tot_for_waypoint(refuel_pre)`), and `patrol_duration` stretches by the early opening
  so `patrol_end_time` still covers the post-vul service.

Also fixed in passing: the stale `FormationAttackLayout.refuel_pre` comment ("at most one is
set" — `BOTH` tasking sets pre- *and* post-vul points).

Tests: `tests/ato/flightplans/test_refuel_timing.py` (dwell on the refuel edge, per-size service
time, push time with/without a pre-vul stop, tanker window post-vul-only vs early-open).

#### The dwell is charged to player flights only (2026-08-09)

**Symptom (player report).** An AI strike the player was escorting ran ahead of the kneeboard
timetable — it reached the target before the escort, which was timed against the same package ToT.

**Root cause — AI never spends the boom time the dwell budgets.** Two independent mechanisms, both
in the generated `.miz`:

- `RefuelPointBuilder` stops the Refueling task as soon as every jet is at 50% fuel
  (`stop_if_lua_predicate(0.5)`). At a pre-vul stop that is already true on arrival, so the task
  ends the moment it starts and the flight flies through.
- `ai_unlimited_fuel` (on by default) writes `SetUnlimitedFuel(True)` at waypoint 0 and only
  `SetUnlimitedFuel(False)` at the JOIN, so AI fuel is pinned across the refuel leg regardless.

`push_time` still released the flight from its hold `refuel_service_time` early to pay for the
stop, and nothing consumed the difference. Measured on one package: strike (2× F-15E, tanker)
9.02 min early at the join, TARPS (1× F-14, tanker) 5.00 min, escort (2× F-14, no tanker) 0.00 —
the error is `4 × size + 1` exactly, and the flight without a refuel waypoint is the control.

**Fix.** `FlightPlan.refuel_duration` returns zero when `flight.client_count` is zero, so an AI
receiver's takeoff time, hold push and chained ETAs all stop carrying a dwell it never flies.
The package tanker still reserves service time per receiver
(`PackageRefuelingFlightPlan.patrol_duration`) — overlapping the tanker is harmless, and it keeps
gas on station for an AI flight that does come up thirsty.

In-game pass: checklist **B53**.

### Tanker tasking falls back to the fuel estimate (2026-07-08)

**Symptom (player report, F-4E-45MC kneeboard).** An F-4E OCA/Runway strike on Hamburg was
fragged with **no tanker** and a kneeboard RTB margin of **−4259 lb** ("short of getting home as
planned; tank or divert"). The theater could crew a tanker; the planner just never considered
one for this sortie.

**Root cause — the deficit and the tanker decision read different fuel sources.** The
kneeboard fuel ladder / RTB margin (§46, `waypointgenerator._estimate_planned_fuel_for`) falls
back to `AircraftType.estimated_fuel_consumption` when an airframe ships no hand-measured `fuel:`
block, so it *computes and prints* the deficit. But `FormationAttackBuilder._refuel_tasking`
(`game/ato/flightplans/formationattack.py`) read **only** the measured `unit_type.fuel_consumption`
and returned `RefuelTasking.NONE` the moment it was absent — so the whole strike family
(OCA/Runway, OCA/Aircraft, Strike, BAI, DEAD, SEAD/SEAD Sweep, Anti-ship, Armed Recon, Escort,
TARPS, Air Assault) never fragged a pre- or post-vul tanker for a no-`fuel:`-block airframe,
however long the leg. The `F-4E-45MC.yaml` (a Heatblur mod jet) has no `fuel:` block, so its
tanker decision was permanently blind while its ladder screamed.

**Fix — one source for both.** `_refuel_tasking` now reads
`fuel_consumption or estimated_fuel_consumption`, mirroring the ladder/bingo fallback: if we
trust the estimate enough to warn the player "you won't make it home," we trust it enough to
frag the tanker the theater can already crew. Deliberately narrow — `fuel_consumption` itself is
unchanged, so the in-flight fuel sim keeps using measured data only (no new blast radius, per
the `estimated_fuel_consumption` docstring's contract). The decision stays gated by
`can_auto_plan(FlightType.REFUELING)`, so it is a no-op when the campaign fields no tanker
(the −N lb margin is then a genuine "divert" situation), and helos / airframes with no fuel
capacity at all are still skipped. Short hops are unaffected — the estimate over a short route
resolves to `NONE`, exactly as measured data would. A hand-measured `fuel:` block for the
F-4E-45MC (needs in-game measurement) would give tighter numbers still, but is a separate
follow-up; this closes the *inconsistency* for every mod airframe at once.

Tests: `tests/ato/flightplans/test_refuel_tasking_estimate_fallback.py` (no-measured-fuel tanks
from the estimate; measured data still wins; no tanker squadron / helo / no-fuel-data stay
hands-off). Shares the pure decision coverage in `tests/ato/test_refuel_tasking.py`. Needs an
in-game pass (the F-4E OCA case now shows a pre/post-strike tanker + a non-negative RTB margin).

### CAS decoupled from the ground-stance decision (2026-06-28)

> **REVERTED 2026-08-09 (planner re-convergence, work order B).** `PlanFrontLineCas` is deleted from the HTN root. CAS is reachable only through `CaptureBase → DestroyEnemyGroundUnits` again, so a side winning the ground war plans no CAS — upstream's behaviour.
> The code is deleted; rebuild it from git history if it is ever wanted again. See
> [the divergence audit](design/retlab-autoplanner-upstream-divergence-audit.md).

### DEAD reachability gate — no more bombers tasked into a live belt (2026-06-22)

> **REVERTED 2026-08-09 (planner re-convergence, work order B).** `TheaterState.dead_can_reach`, `unreachable_air_defenses`, `initial_radar_sam_rings` and `ThreatZones.radar_sam_rings` are deleted. `PlanDead.apply_effects` optimistically clears its target again, so dependent strikes are no longer deferred behind a live belt.
> The code is deleted; rebuild it from git history if it is ever wanted again. See
> [the divergence audit](design/retlab-autoplanner-upstream-divergence-audit.md).

### No BARCAP over an LHA beside a carrier (2026-10-07)

Upstream treats every friendly ship as vulnerable and gives it `2 * barcap_rounds` of BARCAP. A carrier and an LHA
sailing together therefore drew two stacks over nearly one point (DM report, 2026-10-07).
`lha_covered_by_carrier` in `game/commander/theaterstate.py` drops an LHA from `barcaps_needed` when a friendly
carrier is within `LHA_CARRIER_CAP_COVER` (80 NM, DM call 2026-10-08; first set at 25 NM). A lone LHA keeps its BARCAP; the LHA's Harriers are
untouched and can still be picked for the carrier's CAP. Tests: `tests/commander/test_lha_barcap_cover.py`. Row B188.

### BARCAP stations fill nearest the enemy first (2026-10-10)

Upstream fills `barcaps_needed` in campaign-file order and stops when the fighters run out. With a long list of
threatened bases (Airbase threat range above the stock 100 NM) the front fields could get nothing: Crossing the
Rubicon flew CAP 214 and 271 NM behind the front and none over Haina or Fulda, and across the 76 bundled
campaigns 17 of 53 put no CAP over any front base (read 2026-10-10, DM call the same day).
`barcap_order` in `game/commander/theaterstate.py` puts carriers and LHAs first, then land bases nearest an enemy
base first. The number of stations and rounds is unchanged, and `trim_rounds_for_escort_reserve` now thins the
farthest base first. Tests: `tests/commander/test_barcap_order.py`.

## 7. Auto-hide mobile SAMs on MFD

- Task-level (`game/armedforces/forcegroup.py`): `hide_on_mfd` field,
  `_MOBILE_TASKS = {SHORAD, AAA}`, propagated through `for_layout()` /
  `from_preset_group()` / `create_ground_object_for_layout()`. `hide_on_mfd` is a
  per-task default that YAML can override explicitly (`data.get("hide_on_mfd", ...)`).
- Unit-level (`game/missiongenerator/tgogenerator.py` `GroundObjectGenerator`):
  `hidden_on_mfd` is a group-level DCS property, so the task-based flag missed
  SHORAD/AAA/MANPAD escorts generated *inside* a non-air-defense group (armor or
  missile site) -- they stayed on the datalink. `_contains_mobile_air_defense()`
  now also hides a generated vehicle/ship group when it contains a unit of class
  `MOBILE_AIR_DEFENSE_UNIT_CLASSES = {AAA, SHORAD, MANPAD}` (`game/data/units.py`).
  TELAR and radar/launcher classes are excluded on purpose, so standalone mobile
  MERAD/LORAD sites (SA-6/11, SA-2/3/5/10) stay visible/targetable for SEAD.

---

## 8. Robustness / crash fixes

Grouped by subsystem 2026-08-19. Each is a defect that reached a build, most of them
found by flying.

**Entries from before 2026-09-15 are one line each.** The full entry, with the rule,
the files and the tests, is under the same heading in
[`retlab-features-history.md`](retlab-features-history.md). Read it before changing
that code.

### Flight plans and routing

- **A stand-off shooter flew past its own launch range and died at the target (2026-08-19).**
- **The planner map drew plain SEAD and SEAD Sweep orbiting at their search point (2026-10-16).**
  The orbit ring came from upstream #772's loiter-and-react SEAD, adopted 2026-06-18 and
  reverted 2026-08-09 by the planner re-convergence (U39); the drawing survived the revert, and
  neither flight has an orbit task. `standoff_run_overlay` draws the run instead (ingress,
  search or sweep point, split) with the same reach circle. The same pass took the reverted
  loiter, the -3 min SEAD offset and the deleted DEAD reachability gate (U7) off the wiki, and
  added both removals to `tools/audit_stale_docs.py`.
- **Escorts held at the IP while their stand-off shooters launched far outside it (2026-10-16).**
  Desert Trident turn 1: a Patriot DEAD's two escort flights held 7 NM from the Patriot while
  its Kh-59M shooters turned 62 NM out. `PackageWaypoints.escort_hold_point` puts the escort
  hold at the shortest launch range among the flights of the package's primary task, capped
  at the ingress. Escorts' own weapons do not count (a SEAD escort's HARM says nothing about
  where bombers release), and one attacker with no ranged weapon keeps the IP. It matters for a
  player escort's route and for an escort whose primary never flies, which holds its anchor
  (the test 36 entry below). Tests: `tests/ato/test_escort_hold_standoff.py`.
- **A SEAD package's escorts held on the ingress, 60-80 NM out (2026-10-17).** The HARM's
  authored 80 NM range set the hold. SEAD and SEAD Sweep primaries now use their SEAD Search
  point (`WaypointBuilder.sead_search_point`), where the flight plan actually works from.
- **AI leads held slow and low after takeoff until the flight joined (2026-10-17).** DCS's
  close default formation kept a 4-ship lead at 250-270 kt and 1,700 ft AGL for about
  4.5 min; a carrier Hornet lead sagged to about 140 kt and 200 ft. The 2026-10-06 call was
  to leave it; on 2026-10-17 the DM asked for an experiment.
  `AircraftBehavior.configure_takeoff_formation` gives every ground-start fixed-wing flight
  of two or more a loose trail at its takeoff point; HOLD and JOIN still set the package
  formation. A flight with a player seat gets no trail (2026-10-21): DCS never runs a human
  lead's later waypoint options, so his wingmen kept the trail all mission. Unproven until flown (row B245). If it does nothing, remove it. Tests:
  `tests/missiongenerator/test_takeoff_formation.py`.
- **A hold was never told to release when the TOT was unreachable (2026-08-19).**
- **Front-line groups were held in place and never fought (2026-08-19).**
- Flight-combat-exit `IndexError`: `game/ato/flightstate/inflight.py` guards in
  `__init__` and `next_waypoint_state()`.
- **"Mission cannot be saved due to errors" — locked speed on the second of two adjacent TOTs (the recurring generated-mission rejection, fixed 2026-08-03).**
- **Spurious "past start times" warning for player CAP.**
- **Player CAS steerpoints floating at the combat altitude (user-reported, fixed 2026-07-16).**
- **Hold points placed across the map (fixed 2026-08-16).**
- **Ground-level waypoints written at sea level (test 7, fixed 2026-08-18).**
- **Escorts released at the JOIN instead of the SPLIT (test 7 follow-on, fixed 2026-08-21).**
- **An escort whose primary never flew held its anchor until the mission ended (fixed
  2026-09-17).** The backstop above was installed only for a **client-led** package, on the
  reading that an AI primary always runs its own `RunScript`. It does not when it never
  reaches SPLIT. Test 36: five escorts — COUGAR, PUMA ×2, HORNET, SCORPION — sat within
  5 km of their escort-hold anchors at mission end, four of them 168–310 km inside red
  airspace, because their carrier primaries were either wedged on the deck or never spawned
  at all (see §64). Nothing raised the flag, and the `Escort` `ControlledTask`'s only stop
  condition is that flag. `create_player_split_release_trigger` is now
  `create_split_release_trigger` and runs for **every** primary, with a `zone_release`
  argument that keeps the 15 km zone for the human case only: for an AI primary the
  `RunScript` is still the normal release and the `TimeAfter(split + 900 s)` backstop is
  only the net under it. Setting a flag that is already true costs nothing, so the normal
  case is byte-unchanged in behaviour. Covers the shot-down primary too, which had the same
  hole. Same test file.
- **AI packages were timed to arrive after the mission ended (2026-08-24).**

---

### Refuelling

- **Theater tanker track (2026-10-09, DM call; row B206).** Every theater tanker flies a
  40 NM racetrack (`TANKER_TRACK_LENGTH`, `theaterrefueling.py`) on DCS's own Orbit task.
  The four-corner tanker box that flew from 2026-09-28 was removed: a KC-135 banks 45
  degrees alone, 25 with a jet joined up and 15 with one on the boom, so in contact it
  overshot the 30 x 15 NM box's corners and never flew level. On the app map the track's
  first point moves the whole track and its second swings it around the first
  (`move_track`); the tooltip says which. A save made with a box loads as a racetrack
  (`TankerBoxLayout` survives as a loader only). Tankers of different packages stay
  2,000 ft apart. Measurements and the retry conditions:
  `design/retlab-tanker-box-notes.md`.
- **Air-started support spawns on its track (2026-10-10, DM call; row B208).** With
  *Support aircraft (AWACS/tankers) start in the air* on, an AI AEW&C or theater tanker
  spawns 3 NM short of its track start at track altitude (`_on_station_spawn`,
  `flightgroupspawner.py`) instead of over its own field, on both sides. The plan side is
  `PatrollingFlightPlan.starts_on_station` (`support_spawns_on_station`, `patrolling.py`):
  the legs out to the track cost no time and no fuel, so ASAP timing puts the flight on
  station at mission start, and the route-out waypoints are left off the mission
  (`WaypointGenerator.points_flown_before_spawn`). Read off a Kola turn: an A-50 and an
  IL-78 spawned over Severomorsk-1 and Olenya and were on station 31 and 34 minutes in.
  A package's own tanker, a carrier recovery tanker, a jammer and a player-crewed flight
  are unchanged. Tests `tests/ato/flightplans/test_support_on_station.py`.
  The station time is not extended for the flight out it skips (DM call): it stays the
  two settings, and *Desired tanker on-station time* now goes to 300 minutes like the
  AWACS one, so a longer stay is set by hand. The carrier recovery tanker reads the same
  setting for where its station sits (20 kt times the minutes) and keeps the old
  150-minute bound (`recovery_station_time`, `shiprecoverytanker.py`). The bound also
  covers its planned duration, its DCS stop condition and the scheduler's spacing
  between recovery tankers (2026-10-11).
- **Support tracks stay out of neutral airspace (2026-10-10, DM call; row B208).** An
  AEW&C or theater tanker track that touches a country §98 would have intercept its side
  slides along its own length, the smallest move either way that clears the border by
  8 NM, never into a threat zone it was clear of, at most 60 NM
  (`slide_clear_of_neutral_airspace`, `patrolling.py`). Along the track, not back toward
  the anchor: on Kola the line home runs through Finland, so back needed 110 to 120 NM
  where along needed 5 and 22. Off with the border setting. Routes are not rerouted:
  strikers and the tanker's own flight home still cross neutral airspace. Tests
  `tests/ato/flightplans/test_support_track_neutral_airspace.py`.
- **Airframes that cannot refuel (2026-10-10, DM call).** `air_refuel_type: none` marks an
  airframe DCS gives no way to take fuel in the air (`AircraftType.cannot_air_refuel`).
  No tanker serves it, the planner gives it no REFUEL waypoint, and it adds no tanker
  demand. An unset tag still means "takes any tanker", which is what sent a fuel-short
  Su-25 to an IL-78 track. 84 base-DCS airframes carry it, each one whose DCS unit data
  has no `Refuelable` attribute; 12 of them had been tagged `probe` (Su-27, Su-30,
  Tu-22M3, the MiG-29s, J-11A, four Mirage F1s). Modded airframes were not audited.
  Tests `tests/dcs/test_air_refuel_compatibility.py`.
- **Refuel before the push (built 2026-10-07, DM call, not flown — row B189).** A
  per-flight box on the Waypoints tab (`Flight.refuel_before_push`, default off) puts a
  REFUEL waypoint between Hold and Join (`FormationAttackLayout.pre_push_refuel`, strike-
  family and escort plans that hold). It sits on the nearest **theater** tanker's track
  (`pre_push_refuel_point`, `refuel_rendezvous(theater_only=True)`): a package tanker is
  timed to arrive after the strike, so it is never a candidate, and with no theater tanker
  that serves the jet there is no stop and the box is greyed out. Timing: the leg out of
  the stop carries `4 x size + 1` minutes, the package tanker's own figure, or the
  player's **Minutes on the tanker** (`Flight.tanking_minutes`, 1-60, None = automatic;
  2026-10-09, row B202; it moves only the clock, so no route rebuild), and
  `push_time` walks Hold → stop → Join, so Hold departs early and the TOT does not move.
  The stop after the strike is dropped when the fuel walk with only the early top-off
  lands above the reserve (`tankeravailability.post_refuel_unneeded`, a second build);
  otherwise both stay, and the tab names the shortfall in lb under the tick box
  (`post_refuel_shortfall`, row B200). Generation never drops the early stop as unneeded (the player asked
  for it), only when no theater tanker resolves; `WaypointGenerator.dropped_refuels`
  replaced the all-or-nothing `refuel_dropped` flag. AI: the refuel task stops at **0.9**
  on the early stop instead of 0.5, because every jet is above half before the push and
  would otherwise never plug in. Dragging the early stop moves only that flight, not the
  package's refuel point. Tests `tests/ato/flightplans/test_refuel_before_push.py`.
  `Flight.clone_flight` copies the box and the minutes (2026-10-17): a cloned package kept
  the stop in its copied layout with the box off.
- **Refuel before station (built 2026-10-08, DM call, not flown — row B191).** The same
  flag on a BARCAP or TARCAP shows as **Refuel before station** and puts the stop between
  Takeoff and Race-track start (`BarCapLayout`, `TarCapLayout.pre_push_refuel`, built by
  `barcap.station_refuel` from a point 75% of the way to station). The leg out of it
  carries the tanking time in `PatrollingFlightPlan`, so takeoff moves earlier and the
  station times do not move. Station time is not stretched (DM unsure, kept). TARCAP drops
  its after-station stop by the same fuel rule as the strike's (2026-10-09, DM call; it
  had kept it unconditionally), through the same second build in `tarcap.Builder`. `early_refuel_point` and `tanking_time` moved to
  `tankeravailability.py` for both. Tests `test_refuel_before_station.py`.
- **A refuel waypoint on a flight that does not need gas (fixed 2026-09-17, DM call).** The
  planner still emits a REFUEL waypoint whenever the coalition owns a tanker-capable
  squadron anywhere in theater, and `_build_refuel` says in its own comment that it is not
  a fuel-need test. Test 36: a B-1B that had burned 11% of its fuel flew **66 km past
  Incirlik** to reach the tanker, arrived at **0.894** with `SetUnlimitedFuel` already true
  from the split, and was still out there when the mission ended. Generation now drops the
  waypoint when `WaypointGenerator.gets_home_without_the_tanker()` says the sortie closes
  without it — §46's *planning* decision is untouched, the same seam as the two drops below.
  The test is the **dry** margin from `fuel_brief_for` (the burn walk with no top-off
  applied), against the airframe's own landing reserve: **2×** the reserve on measured fuel
  data, **3×** on a synthesised model, because the number is a guess and the cost of being
  wrong is a flight that does not reach its field. No model at all leaves the waypoint
  alone. The argument is one-way — dropping the waypoint only shortens the route, so the
  margin after the drop can only be larger than the one tested. Applies to every airframe,
  not just the bombers. Tests `tests/missiongenerator/aircraft/test_refuel_fuel_gate.py`.
  The `ControlledTask` on the waypoint is still upstream's and is still a *window* rather
  than a low-fuel trigger — it starts when every unit is **above** 0.20 and stops above
  0.50, so a flight below 0.20 never refuels. Untouched; it is upstream's call to make.
- **Refuel waypoints on flights with no tanker to meet (fixed 2026-08-16).**
- **The refuel waypoint was planned whether or not a tanker was flying, and the fuel readout believed it (fixed 2026-08-17).**
- **The refuel waypoint pointed at a place no tanker was (fixed 2026-08-17).**

### Support orbits and radios

- AWACS orbit stacking + direction: `game/ato/flightplans/aewc.py`.
- Tanker orbit placement/deconfliction: `game/ato/flightplans/theaterrefueling.py`.
- **Support flights sharing one radio channel (the flown "I can't talk to the A-6 tanker", fixed 2026-08-02).**

### Carrier deck and recovery

- **Carrier-recovery stagger (the flown Scenic Route midair, fixed 2026-07-16).**
- **The carrier respotted for recovery mid-launch (fixed 2026-08-16).**
- **The launch-cycle hold outlasted the mission (fixed 2026-08-17).**
- **The astern cone fired with nothing in it, and now says what tripped it (instrumented 2026-08-17).**
- **The deck-spot table was blind where the decorations stand (fixed 2026-08-17).**

### Airfield parking

- **Four F-15Cs ejected on the Hatzerim ramp as they began to taxi (2026-10-17).** Syria
  test: every jet on stands 131-134 lost its pilot within 2 s of first moving, with nothing
  else within 150 m and no weapon near. pydcs lists them as ordinary 21 x 15 m stands.
  `game/theater/blockedparking.py` holds those stand names, and
  `AircraftGenerator.clear_parking_slots` marks them taken every generation, so no aircraft
  spawns there. Add a field's stands to `BLOCKED_STANDS` only from a flown loss. Tests:
  `tests/theater/test_blocked_parking.py`.
- **One more F-15C ejected on the Hatzerim ramp, from stand 116 (test 60, 2026-10-18).** The
  wingman lost its pilot 13 s after spawning, as its lead began to taxi. It had not moved and
  nothing else was within 200 m. Stand 116 joins the blocked list.
- **The stand survey (test 61, 2026-10-18).** One AI F-15C on each of Hatzerim's 53
  Eagle-sized stands: 116, 131-134 and 158 ejected, the other 47 launched. The jet on 134
  spawned clipped into the revetment wall, so these stands sit too close to a wall for an
  Eagle. Stand 158 joins the blocked list. The probe is `Missions\RetLab probes\hatzerim_stand_survey.miz`.
- **Two Su-27s ejected on the Diyarbakir ramp (2026-10-18).** Anatolian Reach: both jets of
  a red BARCAP lost their pilots about 15 s after spawning on stands 116 and 117, without
  moving. They are the field's only two 24 x 15 m stands, side by side in front of a hangar.
  Both join the blocked list. A survey of every fighter stand at the nine Turkish fields is
  `Missions\RetLab probes\turkey_stand_survey.miz` (row B253).
- **The Turkish stand survey (test 63, 2026-10-19).** One AI jet on each of the 496 fighter
  stands at the nine Turkish fields: Diyarbakir 79, 116 and 117 ejected 17-19 m into their
  taxi, every other stand launched. Stand 79 joins the blocked list.
- **Flight parking clusters: a four-ship froze nose to nose on the Spangdahlem ramp (test 64,
  2026-10-24).** pydcs gave AI flight Dodge 8 the next four free stands by name, 48-51: the
  lead south of the main junction, the wingmen 200-270 m north-east of it. On activation the
  wingmen drove the wrong way down the taxiway to fall in behind the lead, met it nose to nose,
  and all four sat there for the mission, trapping Ford 6 and a BARCAP pair behind them.
  `game/missiongenerator/aircraft/parkingcluster.py` now picks a ground-start fixed-wing
  flight's stands in `FlightGroupSpawner._generate_at_airfield` (AI, players and QRA
  templates alike):
  - Candidates are pydcs's own `free_parking_slots` list, so the fit filter, stands already
    taken and the blocked stands above all still apply.
  - Each candidate anchors a cluster of itself and its nearest free neighbours; the tightest
    cluster wins, ties to pydcs's order. Stands are tried tier by tier in pydcs's
    (helicopter, width) order, so a fighter takes a transport stand only when no smaller
    stand cluster fits.
  - The lead gets the stand nearest the threshold of the runway the flight briefs
    (`active_runway`, wind-chosen); wingmen follow by distance. pydcs has no threshold
    positions, so the threshold is 1,600 m from the field's reference point along the
    takeoff heading, as in `airfieldclearance.py`.
  - A single ship, a runway start, a helicopter, or no cluster within 150 m keeps pydcs's
    own pick. Carriers, FARPs, FOB ground spawns and helipads are untouched.
  - Fulda Gap turn 5, headless: Spangdahlem pairs went from 85-268 m apart to 43-73 m; the
    one four-ship in the plan (Allstedt MiG-27K DEAD) from 165 m to 117 m. A synthetic eight
    four-ships at Spangdahlem: 153-350 m before, 62-118 m after.
  - Unflown (row B288). Tests: `tests/missiongenerator/test_parking_cluster.py`.

### Helicopters

- **AI helicopter terrain CFIT (the flown Red Tide M1 Harz/Sauerland pattern, fixed 2026-07-12).**

### Loadouts and module data

- Malformed mod payload Lua (CJS Super Hornet v2.4 uses local-var table indices that the
  pydcs Lua parser rejects with `ValueError`): patched loader in `qt_ui/main.py`
  (`_patch_pydcs_payload_loader()`), plus the offending files are skipped with a warning.
- **Loadout integrity (jets flying clean / wrong ordnance).**
- **Datalink era gating — the EPLRS boolean became a policy (2026-08-16).**
- **Switching the flight member on the payload tab wiped that member's pylon settings
  (2026-10-17).** `QPylonEditor.set_from` now sets the store with the combo's signals
  blocked, so showing a member's loadout no longer counts as a store change.
- **The Shrike seeker head was matched to the target only with the date rule on, and
  wiped the rest of the pylon's settings (2026-10-22).** Upstream #632 ran the weapon
  `target_overrides` inside `degrade_for_date`, so with `restrict_weapons_by_date` off
  (the default) no head was ever matched. When it ran, it replaced the whole table,
  losing a hand-set head, Attack Profile and WP Marker. `Weapon.settings_for_target` now
  fills a setting only while it is at its default and writes the full table (DCS reads
  an absent key as not fitted); `setup_payload` applies it after the date rule, for AI
  always and for players under `apply_target_overrides_to_loadouts`. The payload
  editor's Weapon Settings window shows the matched head, and saving it unchanged
  stores the default, so it keeps following the target (`strip_target_settings`).
  Known edge: picking the default head (Mk 22) by hand counts as automatic.
  Table changes: Fan Song gets Mk 25 (DCS's Fan Song head, was the broad Mk 50), Fire
  Can joins Mk 23, and a target no rule names gets Mk 50 (`target_overrides_fallback`,
  was Mk 22). The AGM-78A and AGM-78B lost their tables: each has one head in DCS, and
  the 78A's rules set head ids it does not have. Tests:
  `tests/test_weapon_target_settings.py`.

### Ground movement

- **Supply convoys spawning on the runway (2026-08-02, the flown Baltic Fury report "why are units generating on the runway").**
- **The runway guard's two escape hatches (2026-08-06, the flown Caucasus - Slava Ukraini report "tanks drove on the runway and broke the AI taking off").**

### Campaign and save robustness

- **New Game crash on an authored-but-empty `aircraft:` key (2026-07-01).**
- **A task removed from a unit yaml kept being auto-planned in old saves (2026-10-17).** #1218
  took BAI and DEAD off the Tu-160 and H-6J, but the saved auto-assign sets kept them. The
  migrator now drops tasks the airframe cannot fly on every load, not only Liberation saves.
- **A campaign's SA-15 pick fell back to a random SHORAD (2026-10-17).** The Dog Ear that
  `_add_dog_ear_if_needed` forces into Soviet SHORAD presets (2026-06-13) failed the
  `ground_forces` override check for any faction that lists no Dog Ear: 20 sites across
  Assault on Damascus, Battle for Georgia and Noisy Cricket (Redux). The check reads
  `ForceGroup.units_a_faction_must_own`. Test: `tests/armedforces/test_shorad_dog_ear.py`.
- **Player-despawn counted as a combat loss (2026-06-20).**
- **Task-claim generation crash — group-role degrade instead of raise (fixed 2026-08-16).**
- **A CSAR flight the AI cannot fly took the whole turn down (fixed 2026-08-17).**
- **Changing a transport flight's squadron crashed the ATO (fixed 2026-10-10).**
  `QFlightSlotEditor._change_squadron` built the replacement flight with the old flight's
  cargo, then removed the old flight, and `Package.remove_flight` cleared the cargo's
  transport. Removing a flight re-times the package, which builds the new flight's plan,
  and `AirliftFlightPlan` raised `TransferOrder.next_stop called with no transport
  assigned`. Reproduced on the fork's code before fixing. `reassign_cargo`
  (`game/transfers.py`) now puts the cargo on the new flight first, trimmed with the
  lift-slot rule (`units_fitting_in`, `airlift_capacity`); what does not fit is split off
  and waits for the next transport, and the dialog says how many vehicles stayed. A
  squadron whose aircraft cannot lift the next vehicle is refused. `remove_flight` only
  clears a transport that is the flight being removed. `split_transfer` keeps the split
  part at the cargo's current position instead of its origin. Ported from
  rmac7664/dcs-retribution (`fix/transport-squadron-change`), whose capacity rule was
  upstream's one-per-helicopter, two-per-plane. Not taken: its CTLD-zone change for
  helicopter airlifts to a carrier, LHA or off-map base, which no fork transfer reaches.
  Tests: `tests/test_transport_squadron_change.py`.
- **Four UI fixes ported from CleeeCATCH/dcs-retribution (2026-10-10).** All four were
  upstream bugs the fork shared.
  - New game wizard: the start-date calendar was disabled while *Use preset* was ticked,
    but the stylesheet draws a disabled calendar like an enabled one, so a click did
    nothing. It is never disabled now, and a day picked by click or keyboard unticks
    *Use preset* (the keyboard since 2026-10-11; `bind_start_date`).
  - New game wizard: adding a unit to a faction rebuilt the tick boxes all ticked.
    `QFactionUnits.updateFaction` keeps the ticks when it rebuilds the same faction.
  - A mod installed while the app is open reported "No available liveries" until restart,
    because pydcs scans liveries once. `dcs_liveries_for` rescans once per aircraft before
    believing an empty list, and stops once a rescan finds nothing new.
  - *Clean* (pylon fitted, nothing on it) was listed only on a pylon whose shown preset
    already used it. `QPylonEditor` lists it on every pylon, which is what
    `Pylon.can_equip` already accepted; pydcs carries no per-pylon data for `<CLEAN>`.
    What DCS does with it on a pylon that cannot be removed is row **B214**.
  Tests: `tests/test_wizard_faction_ticks.py`, `test_livery_selector.py`,
  `test_loadout_training_filter.py`.
- **The planner never targeted enemy convoys or cargo ships (fixed 2026-10-10).**
  `ObjectiveFinder.convoys()` and `cargo_ships()` asked the planner's *own* coalition for
  transports heading to the enemy's front-line base, which is always empty, so
  `InterdictReinforcements` had nothing to plan for either side. Both now read the
  opponent's transfers, and `cargo_ships()` honours `perf_disable_cargo_ships` as
  `convoys()` honours its twin. The bug is upstream's and Liberation's too. Three fixes
  rode with it: `AntiShipIngressBuilder` had no branch for a cargo ship (a
  `MultiGroupTransport`, whose mission group carries its name), so an anti-ship flight
  sent at one got no attack task; `CargoStopBuilder` wrote an airfield id for a carrier or
  LHA stop, where a ship is landed on by unit id as `LandingPointBuilder` does; and buying
  or selling a ground object red was targeting re-planned both sides, because
  `QGroundObjectMenu` passed a `Player` (always truthy) as `for_red` / `for_blue`.
  Ported from rmac7664/dcs-retribution (`fix/upstream-airlift-refunds`); its refund and
  transfer-label fixes were already ours (PR #395). Tests:
  `tests/commander/test_enemy_transport_targets.py`,
  `tests/missiongenerator/aircraft/test_cargostop.py`, `test_antishipingress.py`. Row
  **B212**.
  A transport bound for a base on two front lines was listed once per front and could
  draw two packages; both lists now hold each transport once (2026-10-11).
  Blue plans before red arranges the turn's transports, so blue sees only the red
  transports made at turn end (a delivered ground order, a §35 or §50 convoy). Red plans
  after blue and sees all of blue's.
- **An anti-ship flight flew on to the fleet after its last missile (changed 2026-10-11,
  DM call).** Four B-52Hs fired from about 83 NM and ended 9 NM from the Kuznetsov.
  `configure_anti_ship` now sets `OptRTBOnOutOfAmmo(All)`, as DEAD does. `All` and not
  `ASM`, because a bombs-only fallback fit would count as out of missiles at spawn. A
  flight that keeps a weapon (a Hornet's Sidewinders) still flies the route. Notes:
  `retlab-antiship-deal-notes.md`. Test: `test_antiship_rtb_winchester.py`. Row B225.
- **Every anti-ship flight attacked the same ship (changed 2026-10-11, DM call).** Each
  flight got `AttackGroup` on the target's DCS groups, the carrier's own group first, and
  the AI picks one hull at a time; a 2026-10-11 run put 128 of 160 Harpoons at one carrier
  and none at three of its four escorts. `game/missiongenerator/aircraft/antishipdeal.py`
  now deals the coalition's anti-ship flights across the living ships of a sea group, and
  `AntiShipIngressBuilder` writes one `AttackUnit` task per ship ahead of the old group
  tasks, starting at the flight's own ship.
  - Line: the escort with the longest-reach SAM, each carrier, then the rest by SAM reach.
  - The top SAM ship and each carrier take 2 flights, every other ship 1, then wrap.
  - Dealt across every package on that sea group, ordered by package TOT. Both sides.
  - A cargo ship target is unchanged.
  Rationale, the run's numbers and what is not addressed (launch timing, the §108 grade for
  a standoff shooter): `docs/dev/design/retlab-antiship-deal-notes.md`. Tests:
  `tests/missiongenerator/aircraft/test_antishipdeal.py`. Row **B219**.

### Debrief and reporting

- **Destroyed strike targets never reaching the campaign — the results commit used a stale snapshot (fixed 2026-08-16).**
- **A building objective sharing its zone with indestructible scenery was never credited (fixed 2026-08-30).**
- **The Lua bridge dropped every scalar on a mixed item (fixed 2026-08-16).**
- **Kneeboard: the package table named the reader "Flight", and the targets map was unreadable (fixed 2026-08-17).**

**The join→ingress leg is paced by the package, and cruise mach is per airframe (2026-09-01,
from a flown F10 reading).** A Syria package's SEAD escort read **542 kt** on the F10 map after
the join while the Hornet it was escorting read **478 kt** — M0.89 against M0.78. The planner
was not at fault: the two are coordinated to 2 knots and 2 seconds, wind was 23 kt on a shared
052° track, and every waypoint is `BARO`. **Store weight does not explain it either** — the
faster Viper carried the *larger* store fraction (4,400.8 kg on 3,249 kg internal, against the
Hornet's 4,693.4 kg on 4,900 kg), so any drag model keyed on stores predicts the wrong sign.
What is left is airframe transonic drag, which this tree has no data for. Two changes: (1)
**`cruise_mach:`**, an optional per-airframe yaml key on the same footing as `cruise_altitude:`,
which wins outright in `GroundSpeed.for_flight` — unauthored is unchanged
(`DEFAULT_CRUISE_MACH = 0.85` supersonic, `max_speed.mach() × 0.85` subsonic, `× 0.7` helo);
(2) **`ingress` added to `FormationAttackFlightPlan.package_speed_waypoints`**, the one transit
leg that had no package harmonisation and the exact leg the divergence was measured on.
`combat_speed_waypoints` is **pinned to the old set** (join, split, targets) because it defaults
to `package_speed_waypoints` and drives fuel burn — without the override every strike package
would start charging combat consumption from the join. **One airframe is authored: the F/A-18C
at M0.78**, verified end to end (476.4 kt at FL210 against the measured 478; the F-16C
unchanged at 517.1). Every other airframe is unauthored and unchanged. The caveat is on the
record: that airframe's own hand-flown `fuel:` block is measured at `0.85 mach for 100NM`, and
the knob is airframe-wide with no per-loadout axis, so BARCAP and TARCAP Hornets now transit at
the loaded-strike figure too. (`game/dcs/aircrafttype.py`,
`game/ato/traveltime.py`, `game/ato/flightplans/formationattack.py`; tests
`tests/ato/flightplans/test_package_cruise_speed.py`; design note
[retlab-cruise-mach-notes.md](design/retlab-cruise-mach-notes.md); checklist B111, verified
2026-09-27 on the DM's call.)

- **No SEAD tasking for a jet the date left without an ARM (2026-10-12, test 56).**
  `Squadron.can_auto_assign_mission` refuses SEAD, SEAD Escort and SEAD Sweep when
  `restrict_weapons_by_date` is on, the task's default fit carries an anti-radiation
  missile and the dated fit carries none (`_date_strips_every_arm`). The case: Iraq
  2012, a JF-17 pair escorting a BAI package as SEAD with a jammer pod and two PL-5,
  its LD-10s (dated 2013) removed with no fallback. Auto-planning and the AI link's
  package builder only; a hand-fragged flight is not checked. A fit with no ARM by
  design is left alone. About 0.25 ms a call. Recorded as an ungated planner
  divergence in `retlab-autoplanner-upstream-divergence-audit.md`. Tests:
  `tests/squadrons/test_sead_needs_an_arm.py`.

- **A SAM site in an AAA slot keeps its search radars on load (2026-10-12).**
  `TheaterGroundObject.__setstate__` strips search radars from a site whose task is
  AAA, to heal sites generated before 2026-06 with a stray radar. The task is the map
  slot's, not the layout's, so a missile system can sit in an AAA slot. The case: a
  Bavar-373 battery at an AAA slot lost its Meraj-4 and Hafez on load, its command post
  had nothing to cue from, and it never fired with a jet at 2.7 NM. The strip now skips
  any site holding a launcher, TELAR, track radar or search-track radar
  (`_holds_sam_system`). A save written after the strip stays stripped. Tests:
  `tests/theater/test_aaa_radar_migration.py`.

- **The app closed with no error 20-40 s after a mission ended (2026-10-21; row B265).**
  15 crashes from 2026-10-17, each Windows event 1000 in `pyside6.abi3.dll` (0xc0000005,
  offset 0x14394); the minidumps fault in PySide's signal code. The cause is inferred, not
  proven: three paths emitted Qt signals carrying Python objects from non-Qt threads. The
  debrief poll ran on a `threading.Thread`; it is now `DebriefingFilePoller`
  (`game/debriefingfilepoller.py`, Qt-free, one check per `poll()`) driven by a GUI-thread
  `QTimer` (`DebriefingPollTimer`, `qt_ui/simcontroller.py`), same 2 s interval and retry.
  The game loop ticks on a `threading.Timer`; `SimController._on_loop_update` queues its
  events under a lock and a payload-free queued signal flushes them in order on the GUI
  thread, completion last. The saved-point routes run on uvicorn's thread;
  `GameUpdateSignal.notify_saved_points_changed` relays the notice the same way. On the GUI
  thread all three still emit at once. The waiting window disconnects from the shared
  debrief signal in `done()`/`closeEvent` and is `WA_DeleteOnClose`; before, every Take off
  left a hidden dialog connected. `qt_ui/main.py` `enable_fault_log` turns on
  `faulthandler` (all threads) into `logs/faulthandler.log` before logging starts, a header
  per start, restarted past 1 MB; the next crash's stack confirms or refutes the cause.
  Windows also logs some handled access violations there, so a stack without a crash is not
  a crash. PySide6 stays 6.8.3. Tests: `tests/qt_ui/test_main_thread_handoff.py`,
  `tests/qt_ui/test_fault_log.py`.

- **The campaign map held ~4 GB of video memory while DCS flew (2026-10-21; row B267).**
  On a 16 GB card, the Retribution process (`python.exe`) held 2.8 to 4 GB of dedicated
  VRAM next to DCS, and SkyEye's speech recognition ran short. QtWebEngine's GPU thread runs
  in the app's own process (`QtWebEngineProcess.exe` held under 100 MB), so the map's
  textures count against `python.exe`. The first fix (#1354) hid the map while the mission
  window was open; measured mid-mission, `python.exe` still held 3,981 MB, so it was
  removed. #1356 then rendered the map in software (`--disable-gpu`, `QT_QUICK_BACKEND=software`);
  panning crawled (and its first session had a one-off native crash at New Game), so it was reverted 2026-10-22.
  The map is on the GPU again, and `qt_ui/widgets/map/mappanel.py` `MapPanel` destroys the
  `QLiberationMap` web view (and its page) while the mission runs, then builds a new one.
  - **The mission status is in the main window (2026-10-24, user call; row B277).** Upstream's
    "Waiting for mission completion" dialog is `qt_ui/widgets/missionstatuspanel.py`
    `MissionStatusPanel`, shown in the map's slot (`MapPanel.release(status)`) by
    `QLiberationWindow.begin_mission` on `QTopPanel.mission_launched`. Its `finished` signal
    (Accept results or Abort) rebuilds the map. The menu, toolbar, ATO, info and top panels
    are disabled meanwhile, as the modal dialog blocked them. The debrief stays a window.
  - The per-process "Dedicated GPU memory" figure for `python.exe` is not the app's share of the
    card: it climbed to 20 GB (above the 16 GB card) while the whole card read ~5 GB, and closing
    the app freed 0.6 GB (2026-10-24). The 4 GB and 13 GB readings above were this counter.
    Measure the card total (`GPU Adapter Memory`) before and after closing the app; row B267.
  - The rebuilt map may open at the campaign's starting view rather than where it was left.
  - A map page that loads with the game already in place renders its layers before the map has a
    center; any layer reading `getBounds` then must tolerate the throw (`SectorsLayer` blanked the page, 2026-10-22).
  Tests: `tests/qt_ui/test_map_panel.py`, `tests/qt_ui/test_mission_status_panel.py`.

- **Tornado bomb fits flew with only Sidewinders before 1999 (2026-10-24, user call).** The
  GR4's Strike, CAS, BAI, OCA and DEAD fits carried GBU-12 or GBU-16 with a Litening pod,
  dated 1999. With weapon dates restricted the pod dropped, `replace_lgbs_if_no_tgp` then
  removed the laser bombs, and the GR4 cannot hang the Mk-82 fallback, so Fulda Gap 1985 and
  Desert Storm flew GR4s with tanks, pods and two AIM-9s. Both Tornado yamls now set
  `has_built_in_target_pod` (DCS unit data: `laserEquipment.laserDesignator`), and the GR4 and
  IDS presets are the stock DCS fits per task: 2 GBU-16 for Strike and DEAD, 4 BL755 (GR4) or
  4 Mk-82 (IDS) for CAS, BAI and OCA/Aircraft, 4 ALARM (GR4) or 4 HARM (IDS) for SEAD, Sea
  Eagle or Kormoran for anti-ship. The old IDS Strike hung Mk-82s on stations 4 and 9, which
  DCS does not allow. Before 1990 the GR4 has no ARM; the SEAD skip above already keeps it off
  auto-planned SEAD, so a hand-fragged GR4 SEAD flight before 1990 still flies unarmed. The
  Tornado ADV (a mod) is untouched. Tests: `tests/retlab/test_tornado_presets.py`.

## 9. TIC — Troops In Contact frontline battle sim — REMOVED (2026-10-15)

**Removed 2026-10-15 (DM call).** The `tic` plugin (default on) ran Grendel's TIC v1.1 (MIT,
Lua globals `GLSCO*`) on the front line: TANK/IFV/APC/ATGM groups were named `TIC:<name>`,
late-activated, respawned by the script as single-unit clones, and fought scripted firefights
from orders encoded in waypoint names, with RetLab's ambient suppressive fire on top.

**Why it went:** the DM's call during the 2026-10-15 test day. It was already off in his Red
Tide game, and the front fought with DCS's own ground AI in test 58 as intended. It cost frame
rate on dense fronts, and it was the only plugin that needed the late-init pass.

**What went:** `resources/plugins/tic/`, `game/plugins/tic.py`, the late-init pass
(`LuaPlugin.late_init_*`, `should_late_init`, `inject_late_init`,
`LuaGenerator.inject_late_plugin_scripts`), `mission_data.tic_groups`, the TIC branches in
`flotgenerator.py` (`TIC_*` constants, `TicStanceProfile`, `_plan_tic_action` and its helpers,
the `TIC:` naming and late activation), `UnitMap.front_line_groups` and
`front_line_unit_from_tic_clone`, the design note `retlab-tic-dynamic-fronts-notes.md`, the
wiki page, and rows B103 and B108. Old saves load; their `tic.*` plugin keys are dropped on
load. `tools/apply_state_json.py` still parses `TIC:` names, which older test captures carry.

**What stays:** PR #823's frontline laydown and cohesive maneuver
(`frontline_clustering.py`, `plan_action_for_groups`), now the only movement path for every
role, and the **default front-line stance** setting. See
`docs/dev/design/retlab-pr823-frontline-merge-notes.md`.

**Constraints learned from flown tests:**
- TIC's ROE cycling raised DCS's undocumented event 61 about ten times a second; the
  `RetLab patch (event 61 spam)` guard in the bundled `Moose.lua` stays, since any option change
  raises it.
- Scripted near-miss fire never moved a front; the campaign front moves on player kills.

**To bring it back:** `git show bc0284448:resources/plugins/tic/TIC_v1.1.lua` (and
`tic_retlab_init.lua`, `game/plugins/tic.py`), and
`git show bc0284448:docs/dev/design/retlab-tic-dynamic-fronts-notes.md` for the stance design.

---

## 10. CurrentHill Iran assets pack

- Unit defs: `pydcs_extensions/iranmilitaryassetspack/` (Shahed-136 `CH_Shahed136`,
  `IranFAC_MG`, `IranFAC_MG_AShM`), re-exported from `pydcs_extensions/__init__.py`.
- Radar DB: `game/data/radar_db.py`. Mod removal logic: `game/factions/faction.py`.
- New-game toggle: `game/theater/start_generator.py` (`iranmilitaryassetspack` field),
  `qt_ui/windows/newgame/...` wizard pages.
- Faction: `resources/factions/CH_iran_2020.json` (`[CH] Iran 2020`).

---

## 11. Native DCS DTC cartridge export — RETIRED (2026-06-26)

**Removed as a half-baked feature.** The native DCS Data Transfer Cartridge export
(`generate_dtc` setting + `game/missiongenerator/dtc/` package + the captured ME
templates under `resources/dtc/`) never worked end-to-end: ED's mission-start pre-load
did not fire on the shipping DCS build, so the player had to open the DTC manager and
manually load the cartridge once per sortie, and the mirrored Saved Games library write
did not distribute over multiplayer. With ED building a native DTC of their own, the
fork's reverse-engineered export was dead weight and has been deleted. Do **not** restore
it; revisit only if ED's native cartridge ships and a thin, reliable export is worth
rebuilding from scratch.

**That condition was met 2026-07-19** — ED's in-miz cartridge + `AutoLoad` shipped and
was proven in MP (a hand-built mission pre-loaded the user's Hornet with zero pilot
action). The rebuilt-from-scratch export is **§74** (`game/missiongenerator/dtc/`),
which shares nothing with this retired implementation.

(The F-15E smart-weapon CC mission labels on the strike-task kneeboard — `(CC 1/1)`,
numbered by `game/missiongenerator/f15ecc.py` — are an unrelated upstream feature and remain.
They were `DTC M1.1` until the 2026-09-23 manual pass: the jet shows `CC set/mission`.)

---

## 12. Recon → BDA engine (`recon` plugin) — REMOVED (2026-08-20)

**The plugin, its emitter and the capture ledger are deleted.** The 2026-08-18 reveal rework
(§3) removed both jobs a capture could do: an un-engaged site's composition is no longer
revealed by scouting, and an engaged one carries no BDA lag to confirm. From that day the
plugin scored captures nothing read.

**It was not inert while it sat there.** On landing it popped a blue-coalition cue reading
`RECON: <callsign> confirmed BDA on N target(s) at <target>` — a claim about a mechanic that no
longer existed — and to produce that N it scanned every RED ground and ship unit in the
mission. The six Lua Plugin Options rows tuned only that scan.

The MOOSE Ops.TARS engine this section originally described was cut on 2026-08-05
(`7eb247659`). Its design note `414th-tars-recon-notes.md` was deleted 2026-08-20 with the
17 other dead notes, recoverable from git before `5db34150f`.

Removed:

- `resources/plugins/recon/` (`recon-config.lua`, `plugin.json`) and its `plugins.json` entry.
- The six plugin options (`triggerRangeNm`, `captureCap`, `pollS`, `optimalAltFt`,
  `ceilingAltFt`, `minAltitudeFactor`). Old saves drop the keys in the retired-plugin purge in
  `Settings.__setstate__`.
- `game/missiongenerator/reconluadata.py` (`dcsRetribution.Recon`) and its `luagenerator.py` call.
- `tars_recon_captures`: the global and `write_state()` entry in `dcs_retribution.lua`, and
  `StateData.tars_recon_captures` + `parse_tars_captures` in `game/debriefing.py`.
- Tests `game/missiongenerator/tests/test_reconluadata.py`, `tests/lua/test_recon_runtime.py`,
  `tests/test_tars_bda_bridge.py`.

**What recon still does**: `MissionResultsProcessor.reveal_scouted_command_posts` (§3) — a
surviving TARPS flight reveals a hidden enemy command post within `TARPS_POD_RADIUS_NM` (3 NM)
of its package target. Planner-side Python, keyed on the package target and on survival. That
constant moved to `game/sim/missionresultsprocessor.py`; it was the only symbol outside the
plugin path that read `reconluadata`.

**Reviving this starts with statics.** `captureAt` covered ground groups and ships only, and a
command post generates as statics — so the capture loop could never have seen the one site the
reveal cares about. The runtime, including the sensor × altitude × cloud degradation model, is
at `git show da9f19246:resources/plugins/recon/recon-config.lua`. The candidates for a new recon
job are in [retlab-recon-role-scoping-notes.md](design/retlab-recon-role-scoping-notes.md);
neither open one (B, re-fixing moved naval groups; C, a kneeboard imagery card) would use this
ledger.

**History.** The MOOSE Ops.TARS engine this section used to describe was cut 2026-08-05
(`7eb247659`), together with the AI-side `airecon` plugin, and replaced by the single `recon`
plugin removed here. `docs/dev/design/414th-tars-recon-notes.md` documents that implementation —
historical only, do not author against it. In-game pass G2 was ☑ VERIFIED 2026-06-24 under the
MOOSE engine and is closed.

---

## 13. Flight Control ATC — RETIRED (2026-06-26)

**Removed as a half-baked feature.** The players-only MOOSE **FLIGHTCONTROL** ATC plugin
(`resources/plugins/flightcontrol/`, the `_inject_flightcontrol_script()` /
`_flightcontrol_airbase_entries()` injection in `luagenerator.py`, and the
`flightcontrol` registry entry) tower-sequenced human players at friendly land airbases.
It added taxi/takeoff/landing comms but needed constant care to keep AI flow pass-through
(generous taxi/landing limits + orphan-parking reconciliation to silence MOOSE
parking-spot spam), and never earned its keep. It has been deleted.

Save migration: `Settings.__setstate__` drops the `flightcontrol` plugin option keys on
load (alongside the other retired plugins) and no longer force-enables it; the one-time
recon-plugins-default migration now flips only TARS. Do **not** restore the plugin.

---

## 14. Plugin Options UI — section descriptions + label/default pass

- **String options were uneditable (fixed 2026-08-18).** The settings page picks its widget
  from the option's declared default type and handled `bool` and `int`/`float` only, so a
  string option rendered its label beside an empty cell. All seven the fork ships were
  affected: the taxi-card ground frequency (`briefing`), four comma-separated weapon-pattern
  lists (`minefields`, `navalmagazines`, `vietnamops` ×2), the FAC(A) aircraft type
  (`vietnamops`) and the red-scramble spawn mode (`redscramble`). A new optional `choices`
  list on the option renders a `QComboBox`; without it a string option gets a `QLineEdit`,
  which is the right answer for a pattern list that has no enumerable values. A default
  outside its own `choices` is rejected at load — the dropdown would otherwise open on a
  value it cannot offer and lose it the moment the user touches the control. `redscramble`'s
  `takeoff` is the first to declare a set (`air` / `hot` / `runway`, which is exactly what
  `redscramble-config.lua` branches on). Checklist B80; tests
  `game/plugins/tests/test_string_options.py`.

A polish pass over the **Lua Plugin Options** page (named LUA Plugins Options until 2026-09-22) so every plugin explains itself.
- New `descriptionInUI` field on `plugin.json` (optional, top-level). Parsed in
  `game/plugins/luaplugin.py` (`LuaPluginDefinition.description` +
  `LuaPlugin.description`) and rendered as an italic, word-wrapped line spanning the
  group-box header in `qt_ui/windows/settings/plugins.py` (`PluginOptionsBox` now drives
  its own `row` counter so the description sits above the option grid). Backward
  compatible: a plugin without the field renders no description. Documented in
  `resources/plugins/_doc/plugins_readme.md`.
- Section descriptions + clearer option labels added to all 15 options-bearing
  `plugin.json` files (RetLab + upstream): typo fixes (`Scipt`→`Script`,
  `Multipler`→`Multiplier`, BigEye's unclosed paren), unit/casing consistency
  (`NM`, `minutes`, `seconds`, `MHz`), and sentence-case wording. **Mnemonics and
  defaults were untouched except** the TARPS defaults below — so saved settings are
  unaffected (labels/descriptions are display-only; mnemonics are the settings keys).
- TARPS defaults re-seeded to match playtest usage (new campaigns only):
  `scoring` true→false, `restrictToNamed` false→true, `srs` false→true. See the TARS
  section above.
- Note: `AGENTS.md` is a byte-identical mirror of `CLAUDE.md` (the authoritative source);
  resync it after editing CLAUDE.md.

### Option dependencies — `enabledWhen` (2026-08-11)

`Settings` fields have had `enabled_when` for a while (27 uses; a child greys out when its
master is off, live across pages via `SettingsDependencyHub`). The 207 options that plugins
expose had no equivalent, which is the same trap in a different box: a spinbox that reads
as live while the script consuming it never runs. §60's own `shoradTime` /
`shoradRadiusNm` / `shoradActDistanceNm` are the example — all three are dead when
`shoradLink` is off, and nothing said so.

- **`enabledWhen` on a `specificOptions` entry**, either `"mnemonic"` (enabled when that
  option is truthy) or `["mnemonic", value]` for an explicit match. Mirrors the Settings
  shorthand. Parsed by `normalize_plugin_enabled_when` into a plugin-qualified
  `(master_identifier, expected)` pair on `LuaPluginOption.enabled_when`.
- **Siblings only, one level.** The master must be an option of the same plugin — a
  plugin's options are only meaningful when that plugin is ticked, and the plugin toggle
  already gates the whole box. A test also pins that no master is itself a dependant:
  chains would render fine (every row refreshes from stored values) but signal that the
  plugin's options want restructuring, and nothing in the tree needs one.
- **Unknown or self-referential masters raise `PluginOptionDependencyError` at load.**
  A typo'd mnemonic would otherwise grey its option out forever — the master never
  resolves, so it never matches — which is indistinguishable from a broken feature.
- **Greying is presentation only.** A greyed option keeps its stored value and still goes
  into the mission's Lua data table exactly as before. The plugin scripts already guard on
  their own master option; making the UI change what is emitted would rewrite behaviour on
  a cosmetic change.
- **The rule is a pure function** — `plugin_option_is_enabled(option, settings)` — so it is
  tested without standing up Qt. `PluginOptionsBox` only passes its answer to `setEnabled`,
  greying the label as well as the control. A master's own control refreshes the box after
  its value is stored (slots fire in connection order, so the refresh is connected second).
  A master missing from an old save leaves the dependant live rather than greying on absent
  data.

**The 13 dependencies declared, each verified against the plugin's own Lua** — this is the
part that rots, so it was checked line by line rather than inferred from names:

| Plugin | Dependants | Master | Why it is inert |
|---|---|---|---|
| ~~`mantisiads`~~ | (five options) | | gone with the MANTIS bridge, 2026-09-12; Skynet's options declare no dependencies |
| `ctld` | `jtacsmoke`, `fc3LaserCode` | `autolase` | not even read unless `autolase` is true |
| `cruisemissiles` | `defenderWakeRadiusNm`, `defenderWakeExtraS` | `defenderWake` | used only past `if not DEFENDER_WAKE then return` |
| `airboss` | `useUH60mod`, `rescueDuration`, `rescueZoneRadius` | `enableRescueHelo` | used only inside `AddRescueHelo` (lines 67–204) |
| `vietnamops` | `ngfsAutoIntervalS` | `ngfsAuto` | only scheduled under `if AUTO then` |

**Three candidates were checked and rejected**, which is why the list is 13 and not more:

- `airboss.rescueHeloDistance` *looks* like a rescue-helo knob and is not — it feeds
  `SetCarrierControlledArea` in `SetupAirboss`, which runs whether or not the rescue helo
  is enabled. Greying it would have hidden a live setting. Since 2026-10-15 its label says
  so: "Carrier controlled area radius (NM)".
- `bigeye.defaultEnableReportPreference` is a per-player *default* that players toggle in
  the radio menu; the report-frequency options still apply once reports are on.
- `gpsjamming.missPower` / `missPowerScalePct` are a fallback and a scale that coexist,
  not a master and a dependant. `missPower` left the options page 2026-10-15.

Files: `game/plugins/luaplugin.py`, `qt_ui/windows/settings/plugins.py`, and the 5
`plugin.json` files above. Tests: `tests/test_plugin_option_dependencies.py` (45).
No runtime change, no save migration, no new setting.

**Options audit (2026-10-15).** Every option of all 24 plugins was checked against the Lua
that reads it. None was dead and none was left from the 2026-10-12 removals. What changed:

- **One switch.** `gpsjamming`, `cruisemissiles`, `navalmagazines`, `briefing`,
  `redscramble` and `neutralborder` are `skipUI`: each runs only a setting, so the setting
  is the one switch (CLAUDE.md hard constraints). Their campaign preseeds are gone;
  `redscramble.hostPlayers` stays. `coin` keeps its checkbox.
  `tests/retlab/test_campaign_plugin_preseed.py::test_no_setting_has_a_second_switch`.
- **Skynet's F10 menus off.** `includeRedInRadio` / `includeBlueInRadio` were on and gave
  every player a "SKYNET IADS RED" menu printing the network's status and contacts. They are
  now `radioMenuRed` / `radioMenuBlue`, default off; the rename makes old saves take the new
  default.
- **Imperial units.** Skynet's scoot distances are in feet (`...ScootDistanceFt`, converted
  in `skynetiads-config.lua`), the naval formation release in NM (`formationReleaseNm`), and
  COIN's converted numbers are rounded (2 NM, 14 kt, 800 ft).
- **LotATC** exports a red site only once blue knows it (`lotatc_exports` in
  `luagenerator.py`, the §3 fog). Blue sites are always exported; red is never fogged.
- **Engineer knobs off the page:** `gpsjamming.missPower`, `trackStepS`, `maxTrackS`,
  `briefing.startGraceS`, `coin.vbiedRepathS`, `infilRepathS`. The Lua still reads them, so
  the harness tests can set them; a mission always gets the script default.
- **Limits and words.** Every number option has a maximum, labels are US English with
  imperial units, and the long plugin descriptions are two or three sentences.
  `tests/test_plugin_option_descriptions.py` guards the maximums and the units.
- **Saves shed dead keys.** `LuaPluginManager.prune_settings` drops any stored key no
  plugin or option declares, replacing the hand-kept list of retired plugins in
  `Settings.__setstate__`.
- MarkerOps' radius commands (SmokeZone, RTB, Refuel, Immortal, Mortal) ignored the typed
  radius: a shadowing `local n`. Fixed.

---

## §15 — SCAR — RESCAP "Sandy" rescue escort — REMOVED (2026-08-07)

Removed together with §21. The fork's whole rescue stack was replaced by upstream
[dcs-retribution#929](https://github.com/dcs-retribution/dcs-retribution/pull/929) — the call
was to adopt upstream's shape rather than carry two rescue systems. The `scar` plugin,
`scarluadata.py`, `PlanScarHunts`/`PlanScar`, the `scar_autoplan*` settings and both test
suites are gone.

`FlightType.SCAR` did **not** survive: it is a `_LEGACY_FLIGHT_TYPE_VALUES` entry mapping to
`CAS`, and this section claimed otherwise until 2026-09-11.

The **Sandy rescue-escort role came back 2026-09-11 as [§99](#99--sandy-rescue-escort)**, on a
different architecture — a flight plan and a yaml task, no plugin and no scenario runtime.
The armor-hunt scenario this section's feature replaced is still gone and is not coming back.

Two things outlived the feature: the command-post intel fog still rides the
`scar_command_post_intel` setting (re-homed to §3 — the field keeps its `scar_` prefix so old
saves resolve), and the blue-only survivor rule is **dead**. `retlab-csar-notes.md` is the one
CSAR document and supersedes everything this section used to say.

## 16. Settings semantic cleanup and audit

The core settings model and every active plugin definition received a consumer-level
audit (2026-06-18). UI work is intentionally separate; the full grouping/dependency
handoff lives in [`docs/dev/settings-qol-audit.md`](settings-qol-audit.md).

- **Removed four dead/duplicate fields** (`game/settings/`): unused
  `prefer_squadrons_with_matching_primary_task`, duplicate `pretense_num_of_cargo_planes`,
  permanently-disabled `nevatim_parking_fix` (plus its Nevatim/Ramon restricted-slot code
  in `flightgroupspawner.py` and the `Migrator` force-off line), and the hidden legacy
  `only_player_takeoff`.
- **Consolidated the AI-radio booleans** (`limit_ai_radios` + `silence_ai_radios`) into the
  `AiRadioBehavior` enum (`FULL`, `LIMITED`, `SILENT`). `Settings.__setstate__` runs
  `_migrate_legacy_settings` to map every old boolean combination deterministically and
  strip the retired keys, so existing campaign/settings files load without carrying dead
  state forward. The new enum is registered in `SERIALIZABLE_ENUM_TYPES` so the hardened
  enum-deserialization path accepts it. Covered by `tests/settings/test_settings_qol_migration.py`.
- **Plugin wording**: `descriptionInUI` added to the QRA `intercept` and `splashdamage3`
  plugins (the latter notes its tuning is locked by design). Splash Damage values and the
  tuned script are unchanged.
- **Consolidated the ground-start truck toggles** (2026-06-28). The "Ground start" section
  had four near-identical booleans — supply trucks and ground-power trucks each split across
  *airbase* and *roadbase* variants. Folded each pair into one airbase+roadbase toggle
  (`ground_start_trucks`, `ground_start_ground_power_trucks`); the two `*_roadbase` fields are
  removed from `Settings`, `_LAYOUT_SPEC`, and the runtime consumers (`tgogenerator.py`,
  `flightgroupspawner.py`). `_migrate_legacy_settings` OR-merges an old save's per-base-type
  values (enabled at *either* base type stays enabled) and drops the retired keys. Covered by
  `tests/settings/test_settings_qol_migration.py`.

---

## 17. Auto-planner target unpredictability

The theater commander's HTN (`game/commander/theatercommander.py`) is a deterministic,
strict-priority planner: given the same campaign state it picks the same targets in the
same order every turn, which reads as "scripted" in game (the enemy hits the same things
on the same cadence). This feature adds an opt-in, tunable amount of randomness to which
*opportunistic* offensive targets get serviced first, without ever deferring a real
defensive threat response.

- **The lever** is `game/commander/tasks/targetorder.py` `shuffled_by_priority(items, state)`.
  It takes an already-priority-sorted candidate list and reorders it with
  Efraimidis–Spirakis weighted sampling (weight `decay**rank`, `decay = strength/100`). At
  strength 0 it returns the list unchanged (strict priority); as strength rises, lower-rank
  targets become progressively more likely to be picked first, while the top target stays
  the single most likely pick at any non-extreme setting.
- **Two settings** (`game/settings/`, Campaign Doctrine / General):
  `ownfor_planner_unpredictability` and `opfor_planner_unpredictability` (0–100, **default 0**).
  The helper reads the knob for the planning coalition's side. Default 0 preserves the exact
  deterministic planner, so existing campaigns and tests are unchanged.
- **Wired into the opportunistic compound tasks only**: `AttackBuildings` (strike),
  `AttackShips` (anti-ship), `AttackAirInfrastructure` (OCA), `AttackBattlePositions` (BAI),
  and the **non-threatening** tiers of `DegradeIads` (detector suppression first, then
  opportunistic DEAD — detectors lead since 2026-09-15, because a Skynet-held SAM stays dark
  until its target is in the kill zone and AI fires HARMs only at an emitter, so the EWR
  covering a site has to die before an AI DEAD at that site can shoot; test 32, doctrine
  note row 8, `tests/test_dead_net_order.py`). The reactive `DegradeIads` tier (`state.threatening_air_defenses` — SAMs
  actually threatening a planned target) is left strictly deterministic on purpose, as are
  BARCAP wave scheduling, escort sizing, and the QRA dispatcher. Variety never delays a
  threat response.
- **Tests**: `tests/test_planner_unpredictability.py` (identity at 0, correct-side knob,
  permutation invariant, top-priority favored).

This is the low-risk, in-Python alternative to a runtime MOOSE `Ops.Chief` rewrite of red
planning: it makes red's offensive target selection feel less repetitive while keeping the
campaign economy, attrition, and BDA coupling intact and unit-testable.

---

## Still in flight / deferred

- Aircraft task-priority rebalance: a **conservative, intent-preserving outliers pass**
  landed 2026-06-15 (20 files, 31 changes) driven by a documented role-band rubric —
  `docs/dev/design/retlab-aircraft-task-rebalance-rubric.md` + `tools/rebalance_aircraft_tasks.py`.
  It excludes discarded-mod airframes, only tightens over-high secondary roles (never adds
  roles or inflates deliberate suppressions). The **full "tighten everywhere" rebalance
  remains held** until in-game scramble/CAP validation. Earlier targeted fixes also landed
  (Tu-22M3 anti-ship 815, M-2000C A2A).
- Reactive scramble is **retired** — the old RetLab ramp-scramble system (border trigger
  -> cold start -> takeoff -> intercept) was replaced by the upstream PR #782 QRA
  dispatcher (see [§1 QRA intercept reserve](#1-qra-intercept-reserve) above), and
  `reactive_scramble.lua` + `FlightType.SCRAMBLE` were removed. The live A2A path to
  validate in-game is now the Moose `AI_A2A_DISPATCHER` QRA flow, not ramp-scramble.

---

## 18. Unified map layers panel

The two stock react-leaflet layer controls (a flat 23-item white box top-right, plus a
second top-left box for threat zones / navmesh / terrain) are replaced by one custom,
dark-themed control: `client/src/components/maplayers/MapLayersControl.tsx` (+ `.css`).

- It is a Leaflet `L.Control` that `createPortal`s a React panel onto the map and owns the
  visibility of every overlay. Each layer is conditionally rendered from state instead of
  via `LayersControl.Overlay`, so the panel can group, theme, collapse, and preset freely.
- **Collapsible groups** (Friendly & shared / Air defences / Enemy intel / Allied & flight
  plans / Threat zones / Navmesh & terrain). The advanced groups start collapsed so the list
  stays short; group + layer + base-map choices persist to the **campaign save** (with a
  `localStorage` cache, `fjg.mapLayers.v1` → bumped to `…v2`), except the fog overview (see §3).
  The panel `GET`s `/game/map-layers` on mount (the save wins over the localStorage seed) and
  `PUT`s the same blob back, debounced, on change; it is stored opaquely on
  `Game.client_map_layers` (`game/game.py`, `__setstate__` defaults it for old saves) and
  carried by the per-turn autosave, so choices survive turns and reopening the app (QtWebEngine
  drops `localStorage` on reload). Server side: `game/server/game/routes.py` (`MapLayersJs`).
- **Preset views** — Default / SEAD / Recon / Clean, plus a "Hide all overlays" button that
  turns every layer off. A preset sets layers only: it leaves the fog overview and the Display
  options group alone (`PRESET_EXEMPT`), and every preset keeps Neutral airspace and Downed
  pilots on (`ALWAYS_ON`). SEAD includes Other ground objects, where the EWRs and C2 nodes
  its IADS lines end at are drawn.
- **Air-defense class rows are FILTERS, not layers** (reworked 2026-07-29 off a flown report
  that read as a fog bug — "with reveal fog of war on, SAM sites show nothing at the actual
  location, just a blank circle you can only find by hovering"). The row group was five
  *independent* `TgosLayer`s ("Air defences" + LORAD/MERAD/SHORAD/AAA), which made two states
  reachable that both look like defects:
  - **master off + rows off ⇒ no air-defense marker at all**, while *Enemy SAM threat range*
    (a separate layer reading the same TGO slice) kept drawing the rings — a ring anchored to
    nothing, identifiable only by hovering it. This was the reported "bug": the campaign save
    had `airDefenses: false` with all four class rows false, so 54 air-defense sites and 25
    §3 concealed "suspected activity" circles were silently undrawn. **Recon fog and the
    reveal overview were both working correctly** (verified headlessly: reveal flips
    `uncertainty_radius_m` to `None`, populates threat ranges + units, and surfaces the
    hidden command posts).
  - **master on + a row on ⇒ two stacked identical markers** on that site (duplicate icon and
    tooltip).
  Now `airDefenses` is the single master layer (`AIR_DEFENSE_TASK_ROWS`): off ⇒ no
  air-defense icons and the four rows grey out (`RowDef.enabledWhen` + `.ml-row-disabled` —
  the §28 settings `enabled_when` convention applied to the map panel); on with no row ticked
  ⇒ every class; on with rows ticked ⇒ only those. `normalizeAirDefenseFilters` flips the
  master on when a stored blob ticked a class row while the master was off, so a pre-rework
  layer choice keeps showing what it used to instead of emptying the map on upgrade.
  `TgosLayer` took `tasks?: string[]` (was a single `task?: string`) and now checks
  **category first, task second, both required** — the old filter returned on the task check
  alone, so a task-less TGO fell through to the category check (one task-less `aa` site drew a
  duplicate marker in all four class layers) and a task match never had its category enforced.
  Note `task` serializes as `[name, role]` — `GroupTask` is a tuple-valued enum — hence
  `task[0]`. Tests `client/src/components/tgoslayer/TgosLayer.test.tsx`.
  **§3 fog (2026-10-11):** `TgoJs.task` is sent only when `known_for(Player.BLUE)`, and
  `TgoJs.known` says which. A site with `known: false` passes every class filter, so it
  draws whenever the master is on and the class rows cannot sort it. A known site with no
  task is still left out of a class filter.
- **Folded in the old top-left control**: threat zones render via the existing
  `ThreatZonesLayer` (+ `ThreatZoneFilter`) and navmesh via `NavMeshLayer` (both already raw);
  terrain and culling gained raw-layer exports (`Inclusion/Exclusion/SeaZonesLayer`,
  `CullingExclusionLayer`) so they render without a `LayersControl`. The hard-disabled
  waypoint join/hold debug zones were dropped.
- **Side-effect toggles** (fog reveal, radar-emitter highlight) are driven by `useEffect` on
  their checkbox state, NOT by Leaflet `add`/`remove` — unmount does not reliably fire
  `remove`, which previously left the fog overview stuck on. The old `FogOfWarToggle` /
  `EmitterHighlightToggle` components were removed.
- **Clickable air-defense rings** (upstream PR #808, adopted): a TGO-backed threat/detection
  ring mirrors its emitter icon's clicks — left-click opens the TGO info dialog, right-click
  starts a new package against it — so a SAM site whose icon is buried under another marker
  stays reachable; carrier/LHA control-point rings (a CP id, no TGO behind them) stay
  hover-only (`AirDefenseRangeLayer.tsx`; the §28 right-click-discoverability direction;
  needs the CI client rebuild).
- Client-only (TS/CSS); needs the rebuilt bundle (CI `npm run build`). `LiberationMap.tsx`
  now mounts just `MapLayersControl` (plus scale + ruler).
- Cleanup done: the orphaned `CoalitionThreatZones` / `WaypointDebugZonesControls`
  components were removed, and `TerrainZonesLayers`/`CullingExclusionZones` now export only
  the raw-layer variants the panel uses (no dead default exports). The remaining
  `getDebugHoldZones`/`getDebugJoinZones` names are generated API bindings, not UI.

---

## §20 — Drop-spawn: Map Right-Click Unit Placement — REMOVED (2026-08-02)

**REMOVED (2026-08-02).** The map right-click unit-placement cheat is fully ripped
out: `game/theater/unitplacement.py`, `QPlaceUnitGroupDialog`, the
`MapContextMenu.tsx` handler, the `POST /qt/place-unit-group` +
`DELETE /tgos/{id}` routes, the `enable_unit_placement` /
`enable_free_unit_placement` settings, and the `user_placed` / `respawn_enabled` /
`pending_deploy` TGO fields are all gone. The shared SSE `delete_tgo` /
`deleted_tgos` plumbing stays (COIN uses it). Do not restore.

---

## §21 — Combat SAR — pilot rescue — REMOVED (2026-08-07)

Removed with §15 and replaced by upstream
[dcs-retribution#929](https://github.com/dcs-retribution/dcs-retribution/pull/929), which is
an **open PR, not merged** — the fork re-adopts its phases by hand (Phase 5 landed
2026-08-17). Read the adoption log in `retlab-csar-notes.md` before touching anything here,
especially the hover height.

### A landing belongs to the nearest open ejection (2026-09-13)

`dcs_retribution.lua` records an ejection with the aircraft's position and refines it when
`S_EVENT_LANDING_AFTER_EJECTION` arrives. That event carries no unit name and fires once per
crew member. The adopted #929 code matched it to the most recent ejection without a landing,
so a two-seat crew's second touchdown was written onto whichever other survivor had none:
test 30 recorded an AV-8B pilot down in the Strait of Hormuz as landed 170 km away at an
F-4E's crash site, which is where the campaign would have placed him. `landing_ejection_for`
now takes the nearest open ejection within `LANDING_MATCH_M` (20 km) and drops a landing
that matches nothing. Pinned by `tests/lua/test_dcs_retribution_runtime.py`, which is also
the first harness coverage of the base script. In-game pass owed: **B122**. Upstream #929
carries the same loop; inventory item 38.

### A survivor with no ejection comes down where his jet crashed (2026-09-23)

A loss with no ejection event rolls `csar_ejection_chance`; #929 then scatters the survivor
round his package's target (`CsarService.fallback_position_for`). On test 39 that put nine
blue survivors 23–42 km from their jets and fragged a CSAR 41 km from an F-14's crash.
`dcs_retribution.lua` now writes `crash_positions` (`{unit, x, z}`) on `S_EVENT_CRASH`,
`StateData` parses it, and `Debriefing.loss_positions` maps each pilot to the crash point,
else the last §91 track sample (leads and humans only), else nothing — the target scatter
remains for simulated turns. Tests: `tests/test_csar.py`, `tests/lua/test_dcs_retribution_runtime.py`.
In-game pass owed: **B142**. Inventory item 41.

### The King — fixed-wing CSAR (2026-08-26)

The C-130J's yaml `CSAR: 5` made the "King" on-scene commander plannable, and
`CsarFlightPlan.Builder` made it impossible: it raised for any non-helo, so the hand-fragged
King died on "Could not create flight" alongside the auto-planned one the raise was written to
stop. Fixed-wing CSAR now dispatches to `KingFlightPlan` (`game/ato/flightplans/king.py`), a
`PatrollingFlightPlan` racetrack anchored on the survivor — 15 nm off on the away side, pushed
clear of any ring the survivor sits inside. `CsarFlightPlan` stays helicopter-only and still
raises; the King never reaches it. The auto-planner gates (`FlightType.requires_helicopter`,
`Squadron.can_auto_assign_mission`) are untouched, so an AI King still cannot be fragged.
Tests: `tests/ato/flightplans/test_king.py`. In-game pass owed: **B106**. Full rationale in
`retlab-csar-notes.md`.

## §23 — Per-squadron DCS country (nation-specific voiceovers)

Implements the upstream request [dcs-retribution/dcs-retribution#627](https://github.com/dcs-retribution/dcs-retribution/issues/627):
let each squadron's units spawn under their own DCS *country* so a coalition (CJTF) side flying
liveries from several nations gets that nation's voiceovers/comms, instead of every unit on a
side sharing one faction country's radio voice.

### The change (the "last mile")

The data already existed — squadrons carry a `country` (`game/squadrons/squadrondef.py`, set by
preset YAML `country:` and inherited from the faction by auto-generated squadrons in
`game/campaignloader/squadrondefgenerator.py`). The gap was purely in mission generation, which
collapsed every group on a side onto the single faction country. This feature routes the squadron
country through the spawn path.

- **`game/missiongenerator/countryassigner.py` — `CountryAssigner`** is the resolver. At
  construction it walks `game.blue.air_wing.iter_squadrons()` / `game.red...`, and builds, per
  side, the set of canonical `dcs.country.Country` instances to register on the coalition plus a
  `for_squadron(squadron)` lookup. `primary_blue`/`primary_red` are the faction countries (the
  fallback). Exposes `blue_countries`, `red_countries`, `belligerent_ids`.
- **Conflict rule (the one real constraint):** a DCS country may belong to only **one** coalition
  in a `.miz`. **Blue claims its squadron countries first**; any red squadron whose country is
  already claimed by blue falls back to `primary_red`. (The common case — both sides on distinct
  CJTF primaries with non-overlapping real-nation squadrons — never hits this.)
- **Canonical-instance discipline:** pydcs attaches spawned groups to the `Country` instance via
  `country.add_aircraft_group` and only serializes countries reachable from the coalition, so the
  **same instance** must be both registered on the coalition (`add_country`) and passed at spawn.
  `CountryAssigner` interns one instance per id (`_instances`) and hands that same object to both
  paths. Passing a duplicate-id instance would silently drop its groups on save.

### Wiring

- `game/missiongenerator/missiongenerator.py` builds `self.country_assigner` in `__init__`
  (`p_country`/`e_country` are now `primary_blue`/`primary_red`), registers **all** per-side
  countries in `setup_mission_coalitions()`, and uses `belligerent_ids` to exclude belligerents
  from the neutrals pool.
- `game/missiongenerator/aircraft/aircraftgenerator.py` takes the assigner in its constructor and
  resolves the country **per flight/squadron** in `generate_flights`, `spawn_unused_aircraft`, and
  `spawn_intercept_templates` (these methods no longer take coalition-level country params).
  `FlightGroupSpawner` is unchanged — it already spawns under whatever country it's handed, and
  callsign generation (`namegen.next_aircraft_name`) flows from the same value.

### No-op for single-nation factions

For a non-CJTF faction the squadron loader (`game/squadrons/squadrondefloader.py`) already
restricts squadrons to the faction country, so every resolved country equals the faction country
and the generated mission is unchanged. The behavior only diverges for mixed-nation/CJTF sides —
exactly the intent.

### Files & tests

| Area | Path |
|---|---|
| Resolver | `game/missiongenerator/countryassigner.py` |
| Coalition registration | `game/missiongenerator/missiongenerator.py` (`setup_mission_coalitions`, `generate_air_units`) |
| Per-squadron spawn | `game/missiongenerator/aircraft/aircraftgenerator.py` |
| Tests | `tests/missiongenerator/test_country_assigner.py` (no-op, mixed-nation, cross-side collision, mirror-match distinct primaries, unknown-id skip, belligerent ids, instance identity) |

### Gotchas / deferred

- **Ground units stay on the faction country.** TGOs, statics, convoys, and the player helo group
  still spawn under `p_country`/`e_country` (`tgogenerator.py`, etc.) — harmless, since ground
  units have no nation voice comms. Only air units carry the per-squadron nation today.
- **Review hardening (upstream PR #854 feedback).** Four edge-case fixes carried back from the
  upstream carve review: (1) **mirror match** — when both factions share a country id, `primary_red`
  gets its *own* instance (not the interned blue one), so each side registers a distinct object under
  the shared id instead of adding one object to both coalitions (an unloadable `.miz`); (2)
  **unknown country id** — a squadron country pydcs doesn't know (version drop / uninstalled mod) is
  skipped with a debug log and falls back to the faction country, never a `KeyError` that aborts
  generation; (3) **`Game.neutral_country`** now excludes belligerents **by country id** (pydcs
  `Country` has identity equality, so the old instance-set membership never matched) and spans every
  squadron's country, so a CJTF side fielding a Swiss/UN squadron can't also hand that nation to the
  neutral coalition; (4) `for_squadron`'s faction-primary fallback logs at debug like every other
  skip. Plus perf: the squadron `faker` is resolved once per recruit batch, not once per pilot, and
  the pilot-name locale table is cross-checked against pydcs in a test so a stale key fails CI.

### Surfaced in the UI + campaign yaml (2026-07-20)

The country was **preset-yaml-only**: a campaign block naming an airframe (not a preset) got a
`random.choice` over every nation's presets under a CJTF faction — the flown Desert Storm finding
was Israeli/Greek-voiced F-16s wearing the 23rd TFS name — and the only fix was hand-authoring a
preset yaml (which nobody does). Both authoring layers now surface it (also the upstream Discord
ask — Starfire's yaml pin, Toad's under-the-livery dropdown):

- **Campaign yaml `country:`** (`SquadronConfig.country`, `campaignairwingconfig.py`): pins the
  squadron's DCS nation by pydcs country name (e.g. `country: USA`). The pick becomes
  deterministic in nation — `find_squadron_for_airframe`/`find_squadron_for_task` accept **only**
  same-nation presets (`resolve_config_country` in `defaultsquadronassigner.py`), and with no
  same-nation preset the pick falls through to the def generator rather than dragging a
  wrong-nation preset's livery/authored roster along; `override_squadron_defaults` stamps the
  pinned country either way (that stamp is what a generated def and a name-bound preset receive).
  Unpinned configs are byte-identical to before (the filter only exists when `country:` is
  authored, and an unpinned squadron keeps the picked def's own country — the stock random
  behavior); an unknown name is a campaign authoring error that **aborts New Game** with a clear
  message (`resolve_config_country` raises, per the upstream #896 review — signal the bad name
  loudly rather than silently flying the wrong nation).
  **Desert Storm pins all 13 US squadrons** (`country: USA`; the RAF/French units bind
  nation-countried presets by name and need no pin) — guard
  `test_desert_storm_us_squadrons_pin_their_nation`.
- **Air Wing Configuration dialog "Country:" selector** (`SquadronCountrySelector`, under the
  Livery selector — Toad's spot): opens on the squadron's current nation, **writes
  `squadron.country` live** (the livery-selector pattern), and a country pydcs doesn't list (mod)
  is inserted and shown faithfully. **The list is the full DCS country list** (the operator-trimmed
  variant — `game/dcs/operatorcountries.py` + the operator-derived default for unpinned CJTF
  squadrons — was **removed 2026-07-31 per the upstream #896 review**: the maintainer flagged the
  curated per-airframe tables as "a massive burden when adding a new aircraft module" and asked to
  allow yaml country specs without changing default behavior). Pilot names follow automatically —
  the New Game wizard shows the dialog *before* `populate_for_turn_0` recruits the roster, and
  `Squadron.faker` reads `squadron.country` live (mid-campaign changes affect newly recruited
  pilots only). The preset dropdowns (`SquadronDefSelector`) now suffix each preset with its
  nation (`VF-103 (Sluggers) [USA]`), and **Save/Load Config round-trips the country**
  (`_build_air_wing` exports `country:`, the loader's `SquadronConfig` applies it — previously a
  reload rerolled the nation). Fixed in passing: after **Replace with preset**, the livery
  selector kept writing to the *discarded* squadron object (`bind_data` now re-points it, and the
  country selector's `set_squadron` does the same by design).

| Area | Path |
|---|---|
| Config field + pick preference | `game/campaignloader/campaignairwingconfig.py`, `game/campaignloader/defaultsquadronassigner.py` |
| Dialog selector + yaml round-trip | `qt_ui/windows/AirWingConfigurationDialog.py` |
| Desert Storm pins | `resources/campaigns/iraq_desert_storm.yaml` |
| Tests | `tests/test_squadron_country_pin.py`, `tests/test_airwing_country_selector.py` (offscreen Qt), `tests/retlab/test_desert_storm.py` |

**I6 VERIFIED 2026-07-20** (user in-game pass the day it was built: "896 is flown and good" —
the selector + the DS pins flown; blanket pass). **Carved upstream same day as draft
[#896](https://github.com/dcs-retribution/dcs-retribution/pull/896)** (the generic core — yaml pin,
selector, round-trip, livery re-point fix, game-side tests; the DS pins and the offscreen-Qt test
stay fork-side). **Trimmed 2026-07-31 to the maintainer's request** (Druss99 request-changes): the
curated operator tables + the operator-derived unpinned default were dropped (both fork and carve),
the selector shows the full country list, and an unknown `country:` name aborts New Game instead of
degrading — reducing the PR to "allow country specs in the campaign yaml, don't change default
behavior." Deferred: filtering the livery list by the squadron country under CJTF (livery
filtering still keys off the *faction* country).
- **Review hardening round 2 (2026-07-15, upstream #854 feedback).** Two more carried back: (1)
  **`Game.neutral_country`'s final fallback was the bug it guarded against** — with USAF Aggressors
  as the red faction and a blue CJTF fielding UN and Swiss squadrons, all three preferred neutrals
  are claimed, and the old tail `return USAFAggressors()` handed a claimed country to the neutral
  coalition anyway (one country on two coalitions, an unloadable `.miz`). It now scans the full
  pydcs country list for any unclaimed nation; `tests/test_game_neutral_country.py` covers the
  preferred pick, the squadron-claimed fall-through, and the all-claimed scan. (2) **Faker
  construction consolidated** — `Coalition.faker` and `Game.faker_for` (zero callers) are deleted;
  `Squadron.faker`'s fallback now builds from the faction's own locale list through the cached
  `faker_for_locales` in `pilotnames.py` (right next to `faker_for_locale` — exactly one
  construction path), which also stripped the faker plumbing out of `Coalition.__init__`/
  `__getstate__` and deleted `Coalition.on_load` entirely (the faker was its whole job). No save
  impact — the faker was never persisted.
- **In-game pass ☑ VERIFIED 2026-06-26 (I1).** Confirmed in flight — a mixed-nation CJTF side plays
  the per-nation voiceovers; the headless `CountryAssigner` adjudication held up live.

### Nation-aware pilot names (completes §23)

The country half landed first; the **roster** half completes it. Pilots were named by a single
per-coalition `Faker(self.faction.locales)` (`game/coalition.py`), so once §23 let a Greek
squadron fly under the Greek flag with Greek voiceovers, its *pilots* were still "John Smith" —
the faction locale, not the squadron's nation.

`game/squadrons/pilotnames.py` adds a curated **DCS country → Faker locale** table
(`COUNTRY_FAKER_LOCALES`, keyed by the exact pydcs `Country.name`) and `faker_for_country()`;
`Squadron.faker` now returns the squadron's own-country Faker, falling back to a faker built from
the faction's locale list (the cached `faker_for_locales` — since the 2026-07-15 consolidation the
one construction path; the old per-`Coalition` Faker instance is gone). So a
Greek squadron rosters with Greek names, an Iranian one with Persian names, a Russian one with
surname-first patronymics, etc. — the same nation the §23 country/voiceover already targets.

Design notes:
- **Opt-in / permissive, never breaks generation.** Any unmapped country — including the
  multinational/irregular "countries" (the CJTFs, Insurgents, UN Peacekeepers) — falls back to
  the coalition's faction-locale Faker, so a roster is always produced. This can only *improve* a
  name. Single-nation factions are unchanged (their squadrons already equal the faction country).
- **Gender-aware guard.** The pilot generator needs `name_male()`/`name_female()` (for
  `female_pilot_percentage`), and a few shipped locales (e.g. `es_AR`) have no gendered name
  provider. `_faker_for_locale` validates this once (cached) and returns `None` → fallback if a
  locale can't do it, so a bad map entry degrades gracefully instead of crashing recruitment. The
  parametrised test asserts **every** mapped locale is usable, so a typo'd/non-gendered locale
  fails CI rather than shipping.
- **Pickle-safe.** Every Faker — per-locale and per-faction-locale-list alike — lives in a
  module-level `lru_cache`, not on the pickled `Squadron`/`Coalition` (which since 2026-07-15
  carries no Faker at all; it was never persisted). No save migration needed.
- **Non-Latin names are intended** and consistent with the pre-existing Russian-locale behaviour
  (Qt + DCS are UTF-8). Faker's `name_male()` can occasionally include a title ("Herr …", "Dr.
  …") — that's a pre-existing quirk of the same call the old code used, not new.

| Area | Path |
|---|---|
| Country → locale table + resolver | `game/squadrons/pilotnames.py` |
| Wiring | `game/squadrons/squadron.py` (`Squadron.faker`) |
| Tests | `tests/squadrons/test_pilotnames.py` (mapped→own locale, unmapped/None→fallback, locale-cache, every mapped locale is gender-aware, squadron recruits named pilots) |

In-game pass row I5 (UI/roster eyeball only — the logic is fully unit-tested).

## §24 — Date-gated aircraft properties (helmet-mounted cueing)

Extends campaign date-gating from *weapons* to the per-airframe **properties** shown in the
payload editor (the "mission options" block: helmet device, datalink, etc.). Weapons already
disappear from the loadout when they postdate the campaign (`restrict_weapons_by_date` +
`Weapon.available_on`); a sibling toggle — **`restrict_props_by_date`**, independent so users can
enforce either or both — restricts the era-defining property options. The curated gates cover
**JHMCS** (F/A-18C + F-16C, fielded ~2003), the **Scorpion HMCS** (A-10C II, ~2012), and the
**Shchel-3UM HMS** (MiG-29, 1983): a pre-2003 campaign no longer offers — or silently ships —
JHMCS.

This is a deliberately small, curated layer. Properties carry **no** introduction date in pydcs
(unlike weapons, which carry `WeaponGroup.introduction_year`), so each aircraft's own data file
supplies the years, not bulk data. Only genuinely period-bound cueing systems are gated; everything
else (rate-of-fire, laser codes, fuel, NVG, the baseline visor) is left untouched.

### The data layer (per-aircraft, reworked 2026-07-15 off the upstream #843 review)

The era data lives in each aircraft's own file — a `date_gated_properties` block in
`resources/units/aircraft/<type>.yaml` mapping a property identifier to `{value label:
introduction year}` — and loads into **`AircraftType.property_date_gate`**, a frozen
**`PropertyDateGate`** (`game/dcs/aircraftproperties.py`, now one class with zero globals:
`from_data`, `value_available_on`, `available_value_ids`, `period_correct_value`, `gated_props`).
Lookup is a direct attribute access on the airframe being configured — no shared module table, no
cross-airframe iteration (Druss's review suggestion, which also kills the old id-collision worry
by construction: data scoped to one airframe cannot leak onto another's same-numbered value).
Exactly four airframes carry the block — the four pydcs confirms expose `HelmetMountedDevice`:
`FA-18C_hornet`, `F-16C_50` (JHMCS 2003), `A-10C_2` (HMCS + "HMCS + NVG" 2012), `MiG-29 Fulcrum`
(HMS 1983). Two design choices matter:

- **Keyed by the value *label*, not the numeric id.** The label pins the gate to what the option
  actually *is*: if a DCS/pydcs update renumbers or renames a value, a label key degrades to "not
  gated" instead of gating the wrong option — and the label-pin test fails CI on the rename so the
  degradation is caught rather than shipped.
- **Scoped by property identifier inside one airframe's data**, so the gate can never touch an
  unrelated property that happens to share a gated label.

The period-correct fallback is the first still-available value, which on every affected airframe is
the baseline "no modern cueing" option (`Not installed` / `Visor Only`, id `0`).

### Two enforcement points (mirrors weapons)

- **UI (`qt_ui/.../payload/propertycombobox.py`).** When `restrict_props_by_date` is on, the
  dropdown lists only `gate.available_value_ids(...)`, and a gated stored/default selection
  displays its `gate.period_correct_value(...)` instead. Like the weapon editor, **storage is not
  mutated** — the player's choice is preserved and only the display + generated mission are
  clamped. `PropertyComboBox` now takes the `AircraftType` (handed down by `PropertyEditor` from
  `flight.unit_type`) so it reads the airframe's own gate.
- **Generation (authoritative — `flightgroupconfigurator.py::degrade_props_for_date`).** Called from
  `setup_props` when the setting is on; iterates only `gate.gated_props(...)` — the curated
  identifiers, not every property. Crucially it resolves each gated prop against the unit type's
  **default**, because an unset helmet device still defaults to JHMCS in the `.miz` — so only
  inspecting `member.properties` would miss the (common) defaulted case. Force-sets the fallback
  when the effective value is too modern.

### Files & tests

| Area | Path |
|---|---|
| Gate class | `game/dcs/aircraftproperties.py` (`PropertyDateGate`) |
| Per-aircraft data | `resources/units/aircraft/{FA-18C_hornet,F-16C_50,A-10C_2,MiG-29 Fulcrum}.yaml` (`date_gated_properties`) |
| Registry wiring | `game/dcs/aircrafttype.py` (`AircraftType.property_date_gate`) |
| Setting | `game/settings/` (`restrict_props_by_date`, Difficulty & Realism → Realism & restrictions) |
| Generation clamp | `game/missiongenerator/aircraft/flightgroupconfigurator.py` (`degrade_props_for_date`) |
| UI filter | `qt_ui/windows/mission/flight/payload/propertycombobox.py`, `propertyeditor.py`, `QFlightPayloadTab.py` |
| Tests | `tests/dcs/test_aircraftproperties.py` (registry gates exactly the four airframes, pydcs label pin, JHMCS gated pre-2003, baseline/NVG always available, clamp-to-baseline, empty gate on ungated airframes, per-airframe HMS/HMCS years, non-gated property untouched) |

### Gotchas / deferred

- **Extend by data, not code.** Add another era-bound option by giving that aircraft's yaml a
  `date_gated_properties` block — the plumbing is generic. Claim only what the module has: **SURA
  Visor was deliberately dropped** in the 2026-07-15 rework because no pydcs airframe exposes that
  label (the Su-30 is a mod); it returns as a two-line data edit to the Su-30 files if the mod's
  label is confirmed.
- **Own setting since 2026-07-15.** `restrict_props_by_date` (default OFF) is independent of
  `restrict_weapons_by_date` — a save that relied on the weapons toggle also gating the helmet
  must flip the new toggle once.
- **No faction override.** Unlike weapons (`weapons_introduction_year_overrides`), the property gate
  uses a single global year. Add per-faction overrides only if a campaign needs them.
- **In-game pass ☑ VERIFIED 2026-06-26 (I3).** Confirmed in flight — a pre-2003 generated mission
  shows the baseline helmet option (not JHMCS) on an F/A-18/F-16; NVG untouched. The 2026-07-15
  rework moved the data model + toggle only; the clamp path is unchanged, no re-fly needed.

### Sibling gate — date-gated ground-support vehicles (FARP / airfield)

The same date-gating philosophy now also reaches the **ground-support trucks** spawned at FARP and
airfield ground-starts (the fuel tanker, ammo truck, and ground-power APA). Previously
`farp_truck_types_for_country` (`game/missiongenerator/tgogenerator.py`) was date-blind — a 1968
mission could spawn 1985 M978 HEMTT tankers on the ramp. The picker was also a ~155-line
`if country_id in [...]` chain.

The 2026-06-28 modernization pass made it **data-driven + date-aware**:

- The country→doctrine-bloc membership moved to module-level `frozenset`s
  (`_SOVIET_PATTERN_COUNTRIES`, `_WESTERN_PATTERN_COUNTRIES`, `_AXIS_PATTERN_COUNTRIES`) and the
  vehicle pools to module-level lists. Behavior is identical to the old chain (same countries, same
  pools) absent date-gating.
- A hand-authored `_GROUND_SUPPORT_INTRO_YEAR` table (pydcs carries no vehicle service dates, same
  as properties) drives `_support_vehicles_in_service(pool, year)`, which filters each pool to types
  in service by the mission year. It **rides the existing `restrict_weapons_by_date` toggle** — no
  new setting — with the year passed from `game.date.year` at the two call sites.
- **Fail-safe fallback:** an emptied pool falls back to its single oldest member, so generation
  never fails for want of a period-correct vehicle. This matters because vanilla DCS has **no**
  Vietnam-era US logistics truck — the M978 HEMTT (1985) is the oldest US tanker and stays the
  fallback, while the red/NVA side gets genuinely period-correct GAZ-66 (1964) / Ural-375 (1961).
- Covered by `tests/missiongenerator/test_farp_truck_dates.py` (filter keeps only in-service types,
  empty-pool fallback, Vietnam-era red is period-correct, US falls back without crashing, no-year =
  legacy behavior). Generic — a clean upstream-carve candidate alongside the §24 property gate.

## §26 — Off-mission combat fidelity + PLAYER_AT_IP fast-forward

The simulation auto-resolves the engagements the player does **not** fly — the AI-vs-AI fights that
happen while you fast-forward to first contact / your IP. Two coupled improvements.

### Capability-weighted abstract combat (was: coin flips)

The old resolution was numbers-only: in A2A the side with more flights won outright (ties 50/50) and
each survivor then died on a second 50/50; a SAM engagement was a flat 50% loss. So an obsolete jet
beat a modern one and SEAD's whole purpose was ignored.

`game/sim/combat/capability.py` weights the odds with data the planner already carries:
- **A2A strength** = best A2A `AircraftType.task_priority` (BARCAP/TARCAP/sweep/escort/intercept) ×
  number of airframes, with a floor so a non-fighter is weak but not auto-dead. Win probability is the
  strength share (`air_combat_win_probability`); winner survivor-loss scales with the margin
  (`air_combat_survivor_loss_chance`, clamped ≤ the legacy 0.5 so a winner is never *more* fragile than
  before — dominance only ever reduces losses).
- **SAM survival** (`sam_death_chance`) anchors at the legacy 0.5 for a generic flight vs one site,
  **halves** for a SEAD-role or SEAD-capable flight, **stacks** with each extra engaging site, clamped
  to [0.05, 0.95].

`aircombat.py` / `defendingsam.py` call these instead of `random.random() >= 0.5`. Deliberately coarse
— a campaign abstraction, not a DCS dogfight; `SKIP` is untouched and the player's flown missions are
still resolved by DCS.

### PLAYER_AT_IP actually reaches the IP

`FastForwardStopCondition.PLAYER_AT_IP` should spawn the player airborne at their IP. It was silently
defeated by `combat_resolution_method` defaulting to `PAUSE`: the fast-forward ended at the first
combat *anywhere* in the theater (`AircraftSimulation.on_game_tick`), which beats a ground-started
player flight to its IP, so generation spawned it at its configured start (`flightgroupspawner` reads
the sim state, which was still AtDeparture).

Fix: `AircraftSimulation._combat_pauses_fast_forward` — under `PLAYER_AT_IP`, an AI-only combat no
longer stops the fast-forward (it keeps ticking and resolves via the capability path above); only a
combat that **involves a player flight** still pauses (you fly that one). Applied to both stop-guards
in `on_game_tick`. Other stop conditions and `force_continue` are unchanged.

**Air-start player flights (2026-10-12).** `GameLoop.run_to_first_contact` skips the fast-forward
when every player flight is already airborne, because an air start has no pre-flight state to stop
at. Under `PLAYER_AT_IP` that skip left an In Flight start at its takeoff point; the skip no longer
applies to `PLAYER_AT_IP`. Found from a save (two In Flight DEAD flights, log line "all player
flights are hot-spawn"): with the skip lifted the sim ran 14 min 16 s and the generated mission
spawned the first flight at its IP.

### Files & tests

| Area | Path |
|---|---|
| Capability scoring | `game/sim/combat/capability.py` |
| A2A / SAM resolve | `game/sim/combat/aircombat.py`, `game/sim/combat/defendingsam.py` |
| Fast-forward gate | `game/sim/aircraftsimulation.py` (`_combat_pauses_fast_forward`), `game/sim/gameloop.py` (`run_to_first_contact`) |
| Tests | `tests/test_combat_resolution_capability.py`, `tests/test_player_at_ip_fast_forward.py` |

### Gotchas / deferred

- **Pilot experience not folded in yet** — capability is airframe + numbers + role only.
- **`task_priority` is a planner *suitability* score**, not a pure A2A rating, so the spread is
  compressed (≈480 MiG-21 → 665 F-15C). It orders matchups correctly; sharpen with an exponent or a
  dedicated rating only if outcomes feel too flat.
- **Needs an in-game pass:** confirm auto-resolved attrition reads believably, and that
  `PLAYER_AT_IP` + the default PAUSE resolution now spawns the player at the IP.

## §27 — Shared-airframe kneeboard index (co-op orientation)

> **Surface history:** the standalone `KneeboardIndexPage` was folded into the §30 cover page in June;
> the **2026-07-13 back-to-upstream kneeboard rework** (which retired the cover, §30) restored it as a
> standalone conditional page. The grouping + start-page math were preserved throughout.

DCS scopes kneeboards per *airframe*, not per group, so every pilot of a type sees all of that type's
flight decks stacked together (see the `client_flights_by_airframe` note). A 4-ship-of-Hornets
squadron flips through four decks to find theirs.

`KneeboardGenerator.generate` keeps each flight's pages a **contiguous block** in deterministic
(callsign-sorted) order, and prepends a one-page **index** (`KneeboardIndexPage`) — callsign (+ custom
name), task, and start page per flight — **only when 2+ client flights share the airframe**. A lone
flight's deck is unchanged (no extra page). Start pages account for the index page itself (block 1
starts on page 2) and for `paginate()` expanding a flight's block. `pages_by_airframe()` became
`client_flights_by_airframe()` (grouped + sorted flights); `_build_index_page` builds the page.

### Files & tests

| Area | Path |
|---|---|
| Index page + generate | `game/missiongenerator/kneeboard/` (`KneeboardIndexPage`, `generate`, `client_flights_by_airframe`, `_build_index_page`) |
| Tests | `tests/missiongenerator/test_kneeboard_index.py` |

### Gotchas / deferred

- **DCS limit, mitigated not removed.** Still no per-group kneeboard and no per-pilot ordering (every
  pilot of the type sees the same stack); the index just makes the stack navigable.
- **Needs an in-game pass:** confirm the index appears with correct start pages when 2+ client flights
  of one type are fragged, and is absent for a single flight.

## §28 — Settings IA reorg + difficulty presets

**Package layout (2026-09-23).** `settings.py` (4,326 lines) was split. `Settings` itself (fields not on a page, the plugin store, save loading, the dialog queries) is ~460 lines and inherits one field mixin per storage page from `fields/` (`difficulty`, `doctrine`, `campaignmanagement`, `missiongenerator`, `missiongeneration`, `vietnamops`, `performance`). The dialog layout is `layout.py`, the enums `enums.py`, the legacy-state rewrites `migration.py`. `settings.py` re-exports every enum because old saves pickled them under that module name. Verified: all 227 fields, defaults, metadata and the 51-section dialog layout identical before and after, and two real saves load.

Two coupled UX wins on the settings surface (the in-game **Settings** dialog and the **New Game**
wizard both render from the same `QSettingsWidget`), plus the 2026-08-03 surface rework below.

### The 2026-08-03 surface rework (search · Features page · advanced disclosure)

**Start with the audit, because it changed the plan.** The question was "is the settings
interface bloated?" — a census of every user-visible field said:

| | |
|---|---|
| User-visible fields | **213** (the §28 reorg's own doc still claimed 174; §81 landed mid-change → **215**) |
| Fields with **zero** consumers anywhere in the tree | **0** |
| Inherited from upstream @`e9b2387e` / added by the fork | **121 / 92** |
| Fork-added gates on features that have **never been flown** | **41** |
| Gates qualifying as "verified + default-ON → make unconditional" | **2** |

So there was nothing to retire. A kill switch on unverified runtime Lua is doing exactly its
job, and the two that *did* qualify (§49 `mobile_missile_relocation`, §58
`mission_briefing_popup`) are both defensible as real choices. The honest conclusion:
**the settings surface is a mirror of the in-game-pass backlog** — 92 outstanding checklist
rows keep 41 toggles alive, and it will keep growing until the fly queue drains. Field-by-field
deletion is not the lever; how the surface is *presented* is. Nothing was deleted.

Three composing changes, all in the metadata-driven layer — no field declarations moved, no
values or defaults changed, no save migration:

**1. The filter bar** (`SettingsFilter`, spanning the top of the dialog)

- A search box matching **label + detail + tooltip + field name**. Every whitespace-separated
  term must hit, so `carrier deck` narrows rather than widening the way substring search would.
- **"Only changed"**, built on the new `Settings.is_default(name)` — which reports `True` for
  an unknown or unreadable field, so the filter can never hide a row by erroring on it.
- Per-page **match counts** on the category list (`Air Doctrine  (2)`), with zero-match pages
  greyed, so you can see *where* the matches are without clicking through eight pages.
- A **`● SET BY CAMPAIGN`** badge on every option the selected campaign pre-seeded. Recorded by
  the New Game wizard (`Settings.record_campaign_preseeds`, called *before* the plugins merge
  so it captures what the campaign author actually authored) and read back via
  `campaign_preseeded_fields()`. Stored as a plain `__dict__` key (`CAMPAIGN_PRESEED_KEY`)
  rather than a dataclass field **on purpose**: `_user_fields()` only yields fields carrying an
  option descriptor, so it rides along in the save without ever becoming a setting itself. The
  badge is re-rendered in `update_from_settings`, because the wizard swaps campaigns underneath
  an already-built dialog.

**2. The `RetLab Features` page**

The **41** boolean per-feature gates move off the topical pages into eleven themed sections.
The split is a deliberate mental model:

> the Features page answers **"what is running"**; the topical pages answer **"how it behaves"**.

A feature's on/off switch moves here; its tuning knobs stay next to the subject they tune. This
is the root-cause fix — new features now have an obvious home instead of landing on whichever
doctrine page looked closest.

- `FEATURE_GATE_FIELDS` is a **literal** in `settings.py`, not an import of
  `game/retlab/features.py`: `game/__init__` already imports settings, so the import would
  be circular. `tests/test_settings_filter.py::test_feature_gate_list_matches_the_registry`
  pins the two together — the same registry-plus-test discipline as the feature index.
- **The Vietnam Ops page keeps its own eight gates.** It is already exactly a scoped features
  page; emptying it to re-list the same toggles here would be churn without a reader benefit.
- The lift is done by rebuilding `_LAYOUT_SPEC` (`_LAYOUT_SPEC_WITHOUT_GATES` →
  `_EFFECTIVE_LAYOUT_SPEC`), dropping any section the lift leaves empty rather than rendering
  an empty group box. `FIELD_LAYOUT` is display-only, so **campaign preseeds are unaffected** —
  they key on the field name.

**3. Basic / advanced disclosure**

`OptionDescription.advanced` (keyword-only, exactly like `enabled_when`, so the frozen
subclasses' positional fields are undisturbed) plus a per-section **"▸ Show N advanced
options"** link. The bulk classification is **one mechanical rule** rather than 213 judgment
calls:

> **advanced == a numeric tuning knob** (int / float / duration).

A number answers "how much" about a behaviour you already chose; booleans and choices answer
"whether" or "which", and those are the decisions that shape a campaign. Two explicit exception
lists carry the cases the rule gets wrong: `_PRESET_DRIVEN_FIELDS` (the economy dials the
difficulty preset bar drives — the preset and the page must never disagree about what matters)
and `_ADVANCED_NON_NUMERIC_FIELDS`, four expert/debug booleans. That last list is where the
**CSAR test toggles** (`combat_sar_test_force_capture` / `combat_sar_test_easy_rescue`) went;
they had been sitting in Campaign Management next to real gameplay settings.

Search deliberately **bypasses** the disclosure: if you typed a knob's name, "it is behind a
link" would be a worse answer than showing it. The disclosure hides itself while a query is
active for the same reason.

Result: **144 basic / 71 advanced**, and Air Doctrine reads **48 → 9** options by default.

**Row bands (2026-09-29).** A label sits at the left edge and its control at the right, so on a
wide window nothing tied the two together. `AutoSettingsGroup.paintEvent` shades alternate shown rows,
draws a divider under each, and lights the hovered row with an accent bar. Bands come from
`AutoSettingsLayout.row_bands()`, built from the row widgets' own geometry — `QGridLayout.cellRect()`
read empty there and stacked every band at the top. Hover is an Enter filter on each row widget plus
the group's own mouse move for the gaps. Row **B160**.

**The all-advanced-section hole (fixed 2026-08-10).** `AutoSettingsGroup.apply_filter()` hid the
whole group box when its *shown* row count was zero — which is every section where the mechanical
rule marks every field advanced. The disclosure lives inside that box, so it went down with it and
there was no link left to click. **13 sections / 47 options were unreachable outside the search
bar**: all seven Air Doctrine knob groups (CAP & support timing, Auto-planner behavior, Altitudes,
Engagement ranges, SEAD standoff, Support-orbit standoff, Mission range limits), Campaign
Management's Campaign features / Victory conditions / Commander economy / **Flight-planner
automation** (the 2/3/4-ship weights), and Mission Generation's Comms war / Naval strike. Nothing
was lost from the model — `Settings.fields()` returned them all along and the planner kept reading
them; they just never rendered. Two changes: visibility now counts the rows a section *offers*
(shown + folded), so a collapsed section keeps its disclosure, and a section whose every field is
advanced **starts expanded** — folding it would leave a bare title, so there is nothing to gain.
Mixed sections are unchanged. Pinned by `test_all_advanced_sections_show_their_knobs` and
`test_collapsing_an_all_advanced_section_leaves_it_reachable`.

**The defect this surfaced.** `enabled_when` greying was wired *per section*, which worked only
because a master and its dependants happened to be declared together. Moving the gates broke
the live re-enable — `motorpool_enabled` is now on Features while `motorpool_spawn_cap` stayed
on Campaign Management. `SettingsDependencyHub` fixes it: every layout registers, and any
control that is somebody's master (`dependency_masters()`, computed once from the field
metadata) broadcasts to all of them. Greying is now correct across page and section boundaries,
which it never actually was — the old code just never had a cross-section pair to get wrong.

Tests: `tests/test_settings_filter.py` (19, driving the real Qt widgets under the offscreen
platform) and the rewritten cross-page case in `tests/test_settings_dependencies.py`.
`qt_ui` is not CI type-checked, so this needed an in-app eyeball — checklist **B46**, ☑ VERIFIED.
(This pointed at **B39** until 2026-08-25; B39 is §81's naval magazines, an unrelated row that is
still owed. Nothing is owed here.)

### The information-architecture reorg

The settings dialog is **100% metadata-driven**: `QSettingsWindow` builds every page → section →
control by walking `Settings.pages()` → `Settings.sections(page)` → `Settings.fields(page, section)`.
Historically those three yielded in raw **field-declaration order**, which had scattered ~150 settings
and left two grab-bag sections — `Campaign Doctrine / General` (34 settings) and
`Mission Generator / Gameplay` (37) — that no one could navigate.

The reorg introduces a single source of truth for the layout: **`FIELD_LAYOUT`** in
`game/settings/layout.py` (built from the readable `_LAYOUT_SPEC`), an *ordered* map of
`field name → (page, section)`. The three classmethods now resolve each field's group via
`_effective_layout` (FIELD_LAYOUT, falling back to the field's own `page=`/`section=` metadata so
nothing is ever dropped) and emit in FIELD_LAYOUT order via `_ordered_user_fields`. Net effect:

- **No field declarations moved, no behaviour change** — field names, values, and defaults are
  untouched, so there is **no save migration**. Only the UI grouping/order changes.
- The grab-bags are gone; the six content pages are **Difficulty & Realism · Air Doctrine ·
  Campaign Management · Mission Generation · Kneeboards · Performance**, each with focused sections
  (largest is the 13-item engagement-distance table). Difficulty-relevant settings that were
  scattered across pages (weapons-by-date, target-intel precision, recon fog, unlimited fuel,
  pilot/airframe limits) are **centralised onto Difficulty & Realism** so the preset has one home.
- Page icons for the renamed/new pages are aliased in `qt_ui/uiconstants.py` (and the page label is
  now `"Mission Generation"`, which matches its existing icon key — fixing a latent miss).

`tests/settings/test_field_layout.py` locks the invariants: FIELD_LAYOUT covers **every** user field
exactly once (a typo or omission fails CI), the UI walk emits each field once, the page order is the
designed order, and **no section exceeds 13 settings** (the anti-grab-bag guard).

### Difficulty presets

`game/settings/difficultypreset.py` adds a `DifficultyPreset` enum (**Casual / Normal / Veteran /
Ace**) and `PRESET_VALUES` — each preset sets the same 12 difficulty-defining fields (enemy skill ×2,
income ×2, pilot invulnerability, MANPADS, labels, map visibility, external views, easy comms, BDA,
weapons-by-date). `apply_preset(settings, preset)` sets just those fields; everything else is the
player's. **Normal mirrors the Settings defaults exactly** (a clean reset to stock), asserted in
`tests/settings/test_difficultypreset.py`. `detect_preset(settings)` returns the matching preset (or
`None` for a custom mix) to drive the "Current: …" readout.

The UI is a `DifficultyPresetBar` (`qt_ui/windows/settings/QSettingsWindow.py`) injected above the
auto-generated sections of the Difficulty & Realism page only: four buttons + a "Current:" label.
A click calls `apply_difficulty_preset` → `apply_preset` → `update_from_settings` (refreshes every
control from the mutated settings and re-highlights the bar) → `applySettings`. Player aids stay
fully editable afterward; the preset is a *starting point*, not a lock. Player coalition skill (AI
wingman quality, not a difficulty lever) is deliberately left alone by every preset.

### Files & tests

| Area | Path |
|---|---|
| Layout source of truth | `game/settings/layout.py` (`_LAYOUT_SPEC`, `FIELD_LAYOUT`, `_effective_layout`, `_ordered_user_fields`) |
| Preset engine | `game/settings/difficultypreset.py` (`DifficultyPreset`, `PRESET_VALUES`, `apply_preset`, `detect_preset`) |
| UI | `qt_ui/windows/settings/QSettingsWindow.py` (`DifficultyPresetBar`, page injection), `qt_ui/uiconstants.py` (icons) |
| Tests | `tests/settings/test_field_layout.py`, `tests/settings/test_difficultypreset.py` |

### Gotchas / deferred

- **The legacy per-field `page=`/`section=` kwargs are kept** as the fallback for any field absent
  from FIELD_LAYOUT; they no longer drive display. Leave them — they're the safety net.
- **The "Current:" highlight is best-effort.** It updates on preset click and on settings load, not
  live as the player hand-edits an individual control, so it can read "Custom" / stale until the next
  refresh. Acceptable for v1; wiring every difficulty control to re-detect is the follow-up.
- **Needs an in-game pass (UI eyeball):** open Settings and the New Game wizard, confirm the six
  pages/sections read cleanly, the preset bar tops Difficulty & Realism, each preset flips the
  expected controls, and "Current:" tracks. The build + apply flow is offscreen-smoke-verified and
  the logic is unit-tested; only the visual feel is unexercised by CI.

### The 2026-07-05 New Game wizard + section pass

A full audit of every New Game page and setting (user call: "complete reorder — there is legacy
we are overlooking") landed a second IA pass on both surfaces:

- **Wizard flow**: the old *Generator settings* page's world-shaping options — the four no-carrier/
  no-navy checkboxes, "Squadrons start at full capacity", and both budget sliders — moved onto the
  **Theater** page as a "Forces & Budget" group (re-seeded from each campaign on select, exactly as
  before; field names unchanged so `accept()` is untouched), and the remainder became a dedicated
  **Mods** page: three groups (Aircraft modules / Asset packs / Air defense), alphabetized, in two
  columns. The wizard is now Intro → Theater (world) → Factions → Mods → Campaign options → Finish.
- **Legacy sweep**: the Intro "Vietnam" card no longer advertises the deleted Khe Sanh campaign
  (now 1968 Yankee Station / Velvet Thunder / Red Flag 81-2); "Advanced IADS **(WIP)**" is relabeled
  **(Skynet)** with a real tooltip (the label read MANTIS from June to 2026-09-12); the
  Campaign-options subtitle no longer tells players to overwrite `Default.zip` (the save path writes
  `Default.json`); `TIME_PERIODS` is chronologically sorted (the stranded "Gulf War – Fall [1990]"
  and the unsorted scenario tail fixed) with the default selected **by name** instead of positional
  index 21; the dead `SettingNames.py` (zero imports) is deleted; the OH-6 pack checkbox is
  relabeled "ground objects" (the OH-6A helicopter left every faction 2026-06-30 — the toggle now
  gates only the pack's `vap_*` ground objects); the Theater page's docs links lead with RetLab
  wiki. The mod list stays the curated 16-of-~50 `ModSettings` (the hidden rest are deliberately
  retired/scrubbed content) — now stated in the Mods page docstring so the subset is a decision,
  not an accident. **Corrected 2026-09-22:** the subset missed five flags campaigns preseed, so
  their units were stripped from every new game — `uh_60l` (13 campaigns; the 2026-07-26 un-cut
  relied on a toggle this trim had removed), `oh_6` (Yankee Station, Velvet Thunder; the OH-6A
  never left the five US Vietnam factions), `jas39_gripen`, `frenchpack`, `spanishnavypack`.
  Toggles restored; `tests/test_mod_toggles.py` fails CI when a campaign preseeds a mod with no
  toggle. The subtitle names `Default.zip` again: Save Settings writes `settings.json`, which
  `load_default_settings` reads, so saving over `Default.zip` does set the default.
- **Section regroup** (FIELD_LAYOUT-only, no field moved, no save impact): Campaign Management's
  three one-field orphan sections merged into a **"Campaign features"** opener
  (phases/clock/carrier-ops) and "Economy & reserves" renamed **"Commander economy"**; Mission
  Generation's "World & systems" split out a **"Battlefield life"** section (base battle damage,
  artillery harassment, mobile missile relocation); Air Doctrine's 13-field "Threat & engagement
  distances" wall split into **Engagement ranges / SEAD standoff / Support-orbit standoff / Mission
  range limits**. Still 7 pages, all 174 fields accounted for (walk-verified).

### Dependency greying + detail summarisation (2026-07-10, the settings UI audit follow-up)

The metadata-driven renderer gained the **dependent-setting greying** the §16 QOL audit deferred, plus
a declutter pass:

- **`enabled_when` dependency greying.** `OptionDescription` gained a keyword-only
  `enabled_when: (master_field, enabled_value)` (a bare `"master"` is shorthand for
  `("master", True)`; normalized by `normalize_enabled_when`). Keyword-only so adding it to the frozen
  base never disturbed the subclasses' positional fields (`invert`, `min`/`max`, `choices`). Every
  `*_option` factory threads it. `AutoSettingsLayout` now stores each field's **label** (not just its
  control) and, after building a section, wires every master's change signal to `refresh_enabled_states`
  — which greys a child's **control + label** whenever `settings.<master> != enabled_value`. All ~21
  wired pairs are same-section, so greying is live; the initial pass sets state on open, and
  `update_from_settings` re-applies it after a difficulty preset. Wired: the four `red_intent_*` ←
  `red_intent`, the `coin_*` family ← `coin_insurgency`,
  `motorpool_spawn_cap` ← `motorpool_enabled`, `comms_jam_requires_capture` ← `enemy_comms_jamming`,
  `perf_culling_distance` ← `perf_culling`,
  `perf_smoke_spacing` ← `perf_smoke_gen`, `dynamic_slots_hot` ← `dynamic_slots`,
  `supercarrier_deck_crew` ← `supercarrier`, the two squadron-limit knobs ← `enable_squadron_pilot_limits`,
  and the **inverse**
  `default_front_line_stance` ← `("automate_front_line_stance", False)` (editable only when automation
  is off). A guard test (`tests/test_settings_dependencies.py`) fails CI if any `enabled_when` master
  isn't a real setting, plus offscreen-Qt tests prove a child greys/ungreys live with its master.
- **Detail summarisation — REVERTED 2026-07-20.** The 2026-07-10 pass made a `detail` longer than
  150 chars render only its first sentence inline (`_summary_line`) with the full text on hover.
  Flown with the §75 victory knobs, the user called it back ("I wanna go back to having it fully
  show" — reading a setting must not require hovering it): every `detail` renders in full inline
  again, the summariser (`INLINE_DETAIL_MAX`/`_summary_line`/`_word_cut`) is deleted, and an
  authored `tooltip` still shows on hover where set. Guarded by
  `test_long_detail_renders_fully_inline` (offscreen Qt, on the Victory conditions section whose
  details exceed the old limit). **Same-day follow-up (the dead-space screenshot):** the fixed
  55-char `textwrap` is gone too — labels `setWordWrap(True)` and the grid's label column takes
  all spare width (`setColumnStretch(0, 1)`), so a description flows across the whole row at the
  window's real width instead of stacking a tall, narrow text column beside an empty middle.

### UI audit bug fixes (2026-07-10)

The same audit surfaced correctness defects across the Qt UI + web client, fixed alongside: the
end-of-campaign dialog branched on the enum member `TurnState.WIN` (always truthy) so a **defeat showed
"Victory!"** (`QLiberationWindow.onEndGame`); the Air Wing **player-slots caption was inverted** for a
valid blue+flyable squadron (`AirWingConfigurationDialog`); every auxiliary window shared one
`self.dialog` reference so opening a second could **garbage-collect the first** (distinct attributes
now); the repair routine **mutated the list it iterated** and skipped nearby wrecks (`QGroundObjectMenu`,
iterate a copy); the web **TGO markers keyed by `tgo.name`** (not unique) → key by `tgo.id`
(`TgosLayer`); Help/About/repo/**Releases links pointed at upstream** instead of the RetLab fork
(`uiconstants` + About); and a dead `EmitterHighlightToggle` component + duplicate `.air-defense-ring-hit`
/ unused `.ml-collapse` CSS were removed. The full 56-finding audit is tracked separately.

### Web map: discoverability + a shared palette (2026-07-10, audit tracks 3+4)

The web client's overlays each hardcoded their own colours (so "red" meant six things and two dashed
circles read alike), and the map's core planning actions were invisible right-clicks with no affordance.

- **Shared semantic palette.** `client/src/theme/mapColors.ts` is the single source of truth — named
  tokens (`friendly`/`enemy`/`flot`, `suspected`/`offLimits`/`weaponsFree`, `supplyOk`…`supplyCritical`,
  `route*`). The overlays (threat zones, front line, supply layer + routes, the concealed TGO) import from it instead of inline hexes. Two deliberate reconciliations:
  the **concealed "suspected activity" circle moved off red onto amber** so it no longer looks like the
  red ROE off-limits circle (finding #2), and the near-invisible navy **friendly supply route was lifted
  to a legible blue** (finding #10).
- **A map legend.** `components/legend/MapLegend` — a compact, collapsible bottom-right key decoding the
  allegiance / ROE / supply / suspected-activity colours + shapes (dark-panel styled, clears the other
  corners).
- **Right-click discoverability.** The interactive vectors (front line, supply route) and the suspected-
  activity circle now carry a **`cursor: pointer`** (via a `.map-interactive` Leaflet class) and a **hover
  hint** ("Right-click: plan a mission here" / "frag interdiction"; TGO/tooltip gets "Left-click: intel ·
  Right-click: plan a package") so the otherwise-hidden fragging actions are findable. Client-only;
  type-checked (`tsc`) + the `FrontLine` test mock extended; the full `react-scripts` build/test runs in
  CI. Deferred: a full right-click *context menu* and theming the light Leaflet tooltips.
- **The 2026-07-18 SITREP-parity wave (audit wave 2)**: (1) the ribbon gains a **"LAST TURN"
  chip** expanding an app-side SITREP panel — `CampaignStatusJs.sitrep_turn`/`sitrep_lines`
  carry `game.last_sitrep.kneeboard_lines()` verbatim (the SAME renderer as the cockpit band,
  so the two surfaces cannot drift), putting losses/POWs/MIA/rescues/will-movers in front of
  the between-turns host for the first time; (2) an amber **HVT window chip** ("HVT Mullah
  Nasir · 3 turns", `coin_hvt.active_hvt_status`) — the 4-turn strike window was an invisible
  clock on every surface; existence + name are already-announced intel so nothing positional
  leaks; (3) Qt: the **debrief renders `game.last_sitrep`** as a "Campaign consequences" box
  (`QDebriefingWindow` — the audit found NO qt_ui file imported the Sitrep the engine computes
  every turn), and (4) the Qt **info panel drops the wall-clock prefix** for a `[T<turn>]`
  stamp + full-text tooltips (`QInfoItem`; the dead never-imported `QInfoWidget` deleted).
- **The 2026-07-18 map-coherence batch** (the UI-representation audit — "the systems aren't
  represented well"): (1) the **campaign ribbon wraps instead of clipping** — the old
  nowrap/hidden/ellipsis combo silently swallowed the strip's tail, which is the enemy
  posture/supply/C2/resolve cluster, on a busy campaign (`CampaignStatusBar.css` flex-wrap; the
  phase chip is now a real `<button>` for keyboard access); (2) **one supply banding** — the ribbon
  chips banded at 35/50 (red-intent thresholds) while the map's supply nodes banded at 85/60/50, so
  identical hues meant different numbers; both now ride the shared `supplyBand`/`supplyBandColor`
  helpers in `mapColors.ts` (4 bands, `.supply-critical` added to the ribbon); (3) the **SAM
  detection-ring colors joined `mapColors`** (`detectionFriendly`/`detectionEnemy` — they were
  hardcoded one-offs in `AirDefenseRangeLayer.colorFor`) and the **legend caught up** with the map:
  rows for detection-vs-threat rings, downed pilots, minefields, the three convoy-route states, and
  the supply-producer ring (it documented roughly half the live layers); (4) the **layers panel
  de-grab-bagged** — a new **Logistics** group (the near-identically-named "Supply routes"/"Supply
  status" renamed to "Convoy routes"/"Supply readiness"), ROE zones moved out of "Enemy intel" into
  their own **Rules of engagement** group, and `emitterHighlight` (a hover behavior, not a layer)
  demoted to a **Display options** footer group; (5) **blue flight paths advertise their click**
  ("Left-click: select this flight" in the tooltip — the one clickable overlay the §28 pass missed).
  Validated with `tsc --noEmit` + the full client jest suite (scratchpad-copy workaround).
- **The 2026-07-19 suspected-circle contrast pass** ("these UI circles are really hard to see" — a
  flown Inherent Resolve screenshot showed the amber concealment circles vanishing into the Iraq
  desert imagery; amber-on-tan has almost no luminance separation, and the cluster density cloud is
  deliberately stroke-less so it read as terrain discoloration): (1) the lone "suspected activity"
  ring gains a **contrast casing** — a wider dark dash (`mapColors.strokeCasing`, weight 6 at 0.75)
  drawn under the amber ring (weight 2 → 2.5), same geometry + `dashArray` so the dashes align; the
  dark edge carries the ring on light terrain, the amber core on dark, the classic cartographic
  halo — the casing circle is `interactive: false` so the amber ring keeps the click/tooltip
  contract; (2) **fills raised**: lone 0.18 → 0.25, cluster member 0.12 → 0.16 (density ramp now
  3 ≈ 0.41, 6 ≈ 0.65, 9 ≈ 0.79). The **cluster cloud stays stroke-less** — that was a flown
  squadron decision (the nine-ring klaxon) and is not re-litigated here; the amber hue also stays
  (`#dd9a3a` — pushing it toward orange would collide with the FLOT's `#fe7d0a`).
- **The family-wide stroke-signature system (same day, the "unique looks for each … area, zone
  and exact target" call):** the casing generalized to the whole dashed-overlay family, and each
  category now carries a **unique dash pattern + weight** so hue is never the only channel (desert
  imagery and colour-blindness both collapse hues): `StrokeSignature`/`mapStrokes` in
  `mapColors.ts` — suspected **area** = medium dash "6 6" w2.5 · **minefield** = tick marks "2 8" ·
  **pilot MIA** = solid · **POW** = short dash "3 5" — every one drawn by the shared
  `CasedCircle`/`CasedPolygon`/`CasedCircleMarker` components (`components/map/CasedShapes.tsx`;
  casing never interactive, the top shape keeps the tooltip/click contract). Consumers refactored:
  `Tgo.tsx` (lone ring), `MinefieldsLayer`, `DownedPilotsLayer`. The **legend renders the real signatures**
  — `StrokeSwatch` draws each row's actual cased dash as a mini SVG (true `dashArray` + casing),
  replacing the generic CSS "dashed" swatch, with the labels renamed to the taxonomy ("Suspected
  area", "ROE off-limits zone", "Weapons-free zone (ROE)"). **Exact targets and buildings need no
  new look** — they already carry unique APP-6/SIDC icons per type (the §3 marker system); the map
  grammar is now: icon = exact object, cased medium-dash amber = suspected area, cased long-dash =
  authored zone, ticks = hazard, solid/short-dash pixel marker = a person. Threat/detection rings
  (solid, numerous) deliberately uncased — doubling a hundred rings is noise, and they were
  legible already. Client-only (`mapColors.ts`, `components/map/CasedShapes.tsx`, `Tgo.tsx`,
  `RestrictedZonesLayer.tsx`, `MinefieldsLayer.tsx`, `DownedPilotsLayer.tsx`, `MapLegend.tsx/.css`);
  `tsc` + jest green; rides the existing P3 concealment checklist bullet + the CI client rebuild.

### Dialogs are clamped to the screen (2026-07-19, the "windows are clipping" report)

The Edit Flight dialog opened with its **title bar above the top of the display** (screenshot: the
tab bar flush against y=0, no window chrome) and carried a ~260 px band of dead space under the
form. Both symptoms came from Qt sizing dialogs purely from their content, measured offscreen
against the reporter's save on a 1440p panel at 150 % scaling (**928 logical px** usable):

| Tab | Height demanded |
|---|---|
| General Flight settings (visible) | 856 px |
| **Payload** (hidden) | **1080 px** |
| Waypoints (hidden) | 878 px |
| **Dialog opened at** | **1115 px** |

Two independent causes, two fixes:

- **`QTabWidget.sizeHint()` expands over *every* page**, so the dialog was sized for its tallest
  *hidden* tab — the General tab rendered 856 px of form inside a 1115 px window, hence the dead
  space. `QFlightPlanner.sizeHint()` now substitutes the **current** page's height, keeping the base
  width and the tab-bar/frame chrome. Setting the hidden pages' size policy to `Ignored` is the
  usual recipe and **does not work** — verified with a standalone Qt probe: `QTabWidget::sizeHint`
  expands over the pages regardless of policy (only `minimumSizeHint` honours it). Only the hint
  changes; nothing forces a resize, so switching tabs never yanks a window the user has sized.
  Worst case across every flight in the save: **1119 px → 899 px**.
- **Nothing in the app was screen-aware.** Of 34 `QDialog` subclasses exactly two consulted
  `availableGeometry` (the main window, and `QSettingsWindow`, which had grown its own ad-hoc clamp
  for this same complaint); the rest could open at any size, and several declare minimums that
  cannot fit a small display at all (`AirWingConfigurationDialog` asks for **1024x768** — impossible
  on 1080p at 150 %, which leaves 672 px). New `qt_ui/screenfit.py`: `fitted_geometry` (a pure
  shrink-then-move, unit-tested without a display) + `fit_to_available_screen` (relaxes an
  over-tall **minimum size** first, or Qt silently ignores the resize; accounts for window chrome;
  logs a warning when even the layout minimum cannot fit, so the residual case is diagnosable rather
  than mysterious) + `ScreenFitFilter`, an application event filter installed once in `main.py` that
  fits every dialog on show. No per-dialog wiring, and a no-op for the dialogs that already fit.

End-to-end verified offscreen against the reported display: every flight's Edit Flight dialog now
lands at 835–893 px fully inside 1706x928 (was 1115–1119, overflowing), and a deliberately 3000 px
dialog is clamped fully on-screen through the real filter. Tests `tests/test_screenfit.py` (pure
geometry incl. the negative-origin second monitor and the title-bar-off-the-top case, plus offscreen
Qt for the minimum-size relaxation and the already-fits no-op).

**Deliberately not done:** retro-wrapping *every* dialog's content in scroll areas — the log warning
marks the spot if a display ever needs it (and the payload tab immediately did; see below). The
stylesheet's 139 `px`-valued rules (10 distinct `font-size: Npx`) were also left alone — Qt scales
them by the device pixel ratio, so they are a font-preference wart rather than the clipping cause.

### The payload tab goes wide (2026-07-19, the same report re-flown: "you prefer tall over wide")

The clamp above got the window back on screen but exposed what it was clamping: the assumption that
"every dialog's layout minimum fits once clamped" was **wrong for the Payload tab**. Measured
offscreen against the reporter's save, the F-15E's payload tab asked for **962 px with a 901 px
layout minimum** against 880 px usable — and `fit_to_available_screen` *relaxes* a minimum to get a
window on screen, so the shortfall was taken out of the pylon rows, which is why the store names in
the screenshot were clipped top and bottom.

The tab was one tall column — flight members, aircraft settings, fuel, loadout, then every pylon —
stacked in a dialog that was already **1508 px wide**, so it demanded height it did not have while
leaving ~600 px of width empty. Three changes, all in the tab:

- **Two columns** (`QFlightPayloadTab`): the aircraft knobs on the left, the loadout on the right.
  They are independent, so the tab is now as tall as the taller column instead of as tall as both.
- **The pylon list scrolls** (`QLoadoutEditor`) instead of being squeezed, so the clamp can never
  crush a row again. The catch — and the reason an earlier attempt at this was reverted for "opening
  showing only a few rows" — is that **`QScrollArea::sizeHint` is hard-capped at 24 font-heights**
  (~360 px): a scroll can never *ask* for a tall list whatever its size-adjust policy, it can only
  grow into space something else claimed. `AdjustToContents` keeps the hint tracking content up to
  that cap and the column's stretch does the rest, so a full loadout is still visible at a glance.
- **Dropdowns stop demanding the width of their longest entry** (`qt_ui/widgets/dropdownwidth.py`).
  Store names run to "BRU-42 with 3 x Mk-82 SNAKEYE - 500lb GP Bomb HD", and with two columns a full
  pylon list pushed the dialog past **2269 px** — wider than the panel. `bound_dropdown_width` caps
  the *hint* while pinning the popup to the width its entries actually need, so nothing is harder to
  read. Same treatment for the loadout, livery and laser-code boxes; the two wrapping labels get
  `Ignored` horizontal policy with height-for-width so they wrap rather than widen.

Result across every airframe in the save: the payload tab went from **up to 2269x962 (min 901)** to
a uniform **1553 px wide, 332–552 px tall, min 346–360** — no crush anywhere, ~300 px of headroom on
the reported display, and the dialog's own width unchanged. Tests
`tests/test_payload_tab_layout.py` drive the real `QLoadoutEditor` against real pydcs pylon data
(picking the longest pylon list by measurement, so a new module is covered the day it lands).

### The New Game wizard grows after it is fitted (2026-08-23, "the new campaign popup renders off screen")

`ScreenFitFilter` fits a dialog on **Show**, once. That is the wrong moment for a `QWizard`, which
is sized by whichever page is current: New Game shows the intro page, so the filter measures a
500x461 window that fits any display, and `NewGameWizard._center_on_screen` centres that same small
window. Clicking Next loads the theater page and the wizard nearly doubles in height, keeping the
intro page's top-left. Nothing re-fits it.

Measured on the reported display (2560x1392 usable, a 4K panel at 150 %): centred at **1030,465**,
grown to **1409x963**, so the frame ran to y=1427 and the Back/Next/Cancel row sat 36 px under the
taskbar. All five pages after the intro were off-screen; paging back did not recover it.

`NewGameWizard.resizeEvent` now calls `fit_to_available_screen(self)` on every resize once the
wizard is visible, so the fit follows the growth instead of preceding it. Verified page by page
against the real wizard on the real display: **5 pages off-screen → 0**, and the same for paging
back down. A class-level `_fitting` re-entry guard is required, not an `__init__` one — Qt resizes
the wizard from *inside* `__init__` (`setWizardStyle`), before any instance attribute exists.

- **Clamp, do not re-centre.** `_center_on_screen` runs on first show only, deliberately, so a
  wizard the user dragged somewhere is not yanked back. `fitted_geometry` moves the window the
  minimum distance needed, which preserves that.
- **The theater page's minimum width is pinned by one unwrapped label** — the docs line under the
  campaign list measures ~1356 px and is the widest thing on the page. `setWordWrap(True)` on it
  cuts the wizard from 1409 to 1027 px wide, and was **reverted**: the narrower column truncates
  campaign names ("Afghanistan - Operation Enduring Resol"). Width was never the reported fault.
  Revisit only if a display turns up that the height clamp cannot satisfy.

Tests `tests/test_newgame_wizard_screenfit.py` — the measured overflow as pure geometry, plus the
real `resizeEvent` driven offscreen on a pageless `NewGameWizard` subclass (grow-past-the-bottom,
no resize/fit feedback loop, and a window that fits is left where the user put it). The subclass is
deliberate: lifting `resizeEvent` onto a bare `QWizard` **segfaults PySide6**, because its
zero-argument `super()` is bound to `NewGameWizard` and `self` is not one.

### 2026-09-22 consistency audit

Layout, on the DM's calls: a **CSAR flights** section beside **Combat search & rescue** takes
the seven CSAR knobs that sat under Altitudes and Aircraft start types (the CSAR start type
stays with the other start types); the motorpool cap moves to **Performance → World detail**;
the cargo-convoy cap gets its own **Sea supply convoys** section; the plugin pages are
**Lua Plugins** and **Lua Plugin Options**. Plugin option descriptions now render under their
label, and text and dropdown options refresh on a campaign switch. Settings text is US
English. The rules, the guards and the open backlog are in
`docs/dev/design/retlab-ui-consistency-audit-notes.md`.

## §29 — Campaign SITREP kneeboard band

A "what happened last turn" digest on the player's next kneeboard — a morning intel brief in the
cockpit. It reads numbers the campaign already tallies; it does not recompute the war.

### Capture (`game/sitrep.py`)

`Sitrep` is a small frozen dataclass (turn, day, friendly/enemy `SideLosses`, captured/lost control
points, pilots recovered). `Sitrep.from_debriefing` reads straight off the `Debriefing` that
`MissionResultsProcessor.commit()` already has: per-side losses from `loss_counts()` (aircraft /
front-line / site units), captures from the **cached** `base_captures` snapshot, and Combat SAR
deliveries from `state_data.combat_sar_rescues`. A new last `commit()` sub-step, `record_sitrep`,
stores it as `game.last_sitrep`.

- **Enemy losses are framed as "claimed"** — same numbers, battle-damage phrasing — to stay
  consistent with the recon-fog model (§3). The campaign already committed the real losses; the band
  is the player-facing read-off.
- **Timing:** `commit()` runs (in `missionsimulation.py`) *before* the turn increments, so
  `game.turn` / `game.current_day` are the just-played turn. The band then shows on the **next**
  turn's kneeboard. Captured bases use the pre-commit `base_captures` attribute, **not** a re-call of
  `base_capture_events()`, which would re-evaluate ownership after `commit_captures` flipped the
  bases and drop them.
- **Persistence:** `game.last_sitrep` is pickled; `__setstate__` defaults it to `None` for old saves
  (no migration). `None` on turn 1.

### Surface (its own SITREP page)

The model + capture live here; the **render surface is a dedicated "SITREP — Turn N" kneeboard
page** (`SitrepPage`, inserted after Support Info). The generator gates it with
`sitrep_for_kneeboard(game.last_sitrep, settings.generate_sitrep_kneeboard)` (returns the `Sitrep`,
or `None` when the toggle is off / there is no prior turn / the previous turn was quiet via
`Sitrep.is_empty`) — no news, no page. *(History: shipped as a band on the `BriefingPage`, was
consolidated onto the §30 cover page in June, returned to the Mission Info page bottom when the
2026-07-13 rework retired the cover, and moved to its own page 2026-07-19 after a flown busy-turn
deck — 11 losses + a POW + two MIA evaders — clipped the MIA list at the Mission Info page edge.
The §70 COMINT block stays on Mission Info.)* The same flown pass rewrote the BLUF's **SAR if-down
drill** to the real §21 CSAR model: "beacon on, squawk 7700, voice on GUARD — evade toward friendly
lines (capture risk climbs with depth); rescue tracks your last known position" (the old "get to
high ground" was generic survival copy with no campaign meaning).

### Files & tests

| Area | Path |
|---|---|
| Model + builder + gate | `game/sitrep.py` (`Sitrep`, `SideLosses`, `sitrep_for_kneeboard`) |
| Capture hook | `game/sim/missionresultsprocessor.py` (`record_sitrep`, last in `commit`) |
| Persistence | `game/game.py` (`last_sitrep` + `__setstate__` default) |
| Setting | `game/settings/` (`generate_sitrep_kneeboard`, default ON, Kneeboards page) |
| Render | `game/missiongenerator/kneeboard/` (`BriefingPage`, `_briefing_sitrep`) |
| Tests | `tests/test_sitrep.py`, `tests/missiongenerator/test_kneeboard_index.py` (gating); `COMMIT_STEPS` in `tests/test_missionresultsprocessor.py` |

### Gotchas / deferred

- **`commit` sub-step list is asserted.** `test_missionresultsprocessor.py` stubs every processor
  method and checks the exact set, so adding `record_sitrep` required adding it to `COMMIT_STEPS`.
- **v1 scope:** losses, captures, and Combat SAR rescues. **Front-line movement and the SCAR
  commander capture are deferred** — front movement needs a turn-over-turn position delta the
  debrief doesn't carry, and the SCAR signal isn't cleanly exposed at commit yet.
- **Player = BLUE** (the debrief-window convention). A RED-human setup would label sides from the
  wrong perspective; revisit if/when a campaign flips the human to red.
- **In-game pass DONE (kneeboard eyeball):** the SITREP renders as the last section of the
  Mission Info page (no fit guard, so an unusually long flight plan + weather block could push it past
  the bottom edge). Confirm on turn 2 it shows the previous turn's losses/captures, and that turn 1 /
  a quiet turn shows no SITREP section. The numbers + render are smoke-verified; only the in-cockpit
  look is the residual.

## §30 — Dedicated kneeboard cover page — RETIRED (2026-07-13)

**Retired in the back-to-upstream kneeboard rework** (user markup pass on a flown Scenic Route Merged deck:
the whole cover page was struck). `CoverPage`, `_build_cover_page` and the campaign-phase/ROE band it
carried are deleted; the deck opens straight on the stock Mission Info page like upstream. What the
cover hosted went three ways:

- **Op/turn/date header + the CAMPAIGN PHASE / ROE band — dropped from the kneeboard.** The phase and
  ROE keep their primary surfaces (the client campaign-status ribbon, the F10/ME map zone drawings,
  the Qt pre-flight ROE warning — §40); the kneeboard copy is gone.
- **SITREP (§29) — moved back to the Mission Info page** as a bottom "SITREP — Turn N" section
  (`BriefingPage`, `_briefing_sitrep`), where the band originally shipped.
- **Flight index (§27) — a standalone conditional page again** (`KneeboardIndexPage`,
  `_build_index_page`), generated only when 2+ client flights share the airframe. Start-page math
  unchanged (index page 1, first block page 2).

Do not restore the cover; if a future feature needs a kneeboard surface, fold it into an existing
stock page (the rework's rule: upstream's pages, our info folded in).

### Files & tests

| Area | Path |
|---|---|
| Successor surfaces | `game/missiongenerator/kneeboard/` (`BriefingPage` SITREP section, `KneeboardIndexPage`) |
| Tests | `tests/missiongenerator/test_kneeboard_index.py` (start-page math, SITREP gating, render) |

## §31 — One-page Brief Sheet + deck-wide colour scheme — RETIRED (2026-07-13)

**Retired in the back-to-upstream kneeboard rework.** The user's markup pass on a flown Scenic Route Merged
deck struck the Brief Sheet's MISSION/ROUTE/GAME PLAN/BULLSEYE/FIELDS/WX/LASER rows (each duplicated a
stock page) and the whole Comms & Brevity card except its code-words block; the page and the card are
deleted (`BriefSheetPage`, `BriefSheetData`, `_build_brief_sheet_data`, `BrevityCard`, the route/
mission/game-plan/laser/freq/weather/fields helpers, and `game/data/brevity_reference.py`). The
**survivors were folded into upstream's pages**:

- **BLUF lines on the Mission Info page** (`_bluf_lines`, now a list): the compact **THREATS AIR/SAM**
  picture (`_brief_air_threats` + `_brief_sam_threats` — the struck verbose TOP THREAT prose is gone),
  a one-line **LOADOUT** summary (`_brief_loadout`), and the **SAR** assets + if-down drill
  (`_brief_sar`). The task/TOT line, code-word push line and §51 JAM BACKUP line were already there;
  the BLUF's duplicate BULLSEYE line was struck — upstream's post-flight-plan `Bullseye:` line returns.
- **Code words on the Support Info page** (`CodeWordsBlock` + `SupportPage._render_code_words`,
  built by `_code_words_block`, gated by `enable_package_code_words`): one push word per ATO task
  category with the flight's own marked "(you)", + SUCCESS/ABORT/STOP JAM — the green-checked block
  from the old card. The task-filtered brevity crib and the explainer sentence are deleted.
- **The semantic colour palette + `text_runs` primitive stay** on `KneeboardPageWriter` — the threat
  cards (§4's Threat Intel Brief page), the Support-page code words, and the amber RTB-margin call-out
  still use them.

### Files & tests

| Area | Path |
|---|---|
| Surviving helpers | `game/missiongenerator/kneeboard/` (`_bluf_lines`, `_brief_air_threats`, `_brief_sam_threats`, `_brief_loadout`, `_brief_sar`, `CodeWordsBlock`, `SupportPage._render_code_words`) |
| Tests | `tests/missiongenerator/test_kneeboard_bluf.py` (BLUF lines, code-words block, helper survivors) |

## §32 — Arc Light heavy-bomber Strike carpet (Vietnam Ops suite)

The first **Vietnam Ops suite** feature (suite design note
[`retlab-vietnam-ops-notes.md`](design/retlab-vietnam-ops-notes.md); the suite lives under a "Vietnam Ops"
settings page, §28; the `vietnamops` plugin has no checkbox since 2026-09-23, so those settings are the
only gate). Retribution's modern engine never modelled the Operation Niagara **Arc Light** B-52
area strikes; this adds them as an **effect of the existing Strike task** — explicitly **not** a new
`FlightType` (the user's reframe). When a heavy bomber flies a `STRIKE`, the runtime walks a carpet of
bombs across the target at the run-in instead of dropping a single aimpoint.

### How it works (the Tier-A config bridge)

Python plans an ordinary Strike; the carpet is a runtime effect. `populate_vietnam_ops_lua`
(`game/missiongenerator/vietnamopsluadata.py`, called from `LuaGenerator.generate_plugin_data`) emits
`dcsRetribution.VietnamOps.arcLight` **only when** `Settings.vietnam_arc_light` is on, with one record per
eligible flight: a `STRIKE` whose `aircraft_type.dcs_unit_type.id` is in `HEAVY_BOMBER_DCS_IDS`
(`B-52H`/`B-1B`/`Tu-95MS`/`Tu-142`/`Tu-160`/`Tu-22M3` — vanilla DCS heavy bombers only). Each record carries
the bomber **group name** and its **target centre** (`package.target.position`, pydcs x=north / y=east).

The `vietnamops` plugin (`resources/plugins/vietnamops/vietnamops-config.lua`) watches each bomber group
on a 5 s poll; when the lead unit closes inside the release range (default 3 NM — retuned 2026-07-01 from
8 NM so the carpet lands with the bomber nearly overhead, matching the ~2.5–3 NM ballistic forward throw
from ~30k ft, instead of firing a full minute early), it fires a **one-shot carpet**: a box of
`trigger.action.explosion` impacts oriented along the bomber's **bearing to the target** (its run-in), rows
stepping along-track with a small delay so it visibly walks, columns spreading it cross-track, with
per-impact jitter. Carpet length/width/per-blast power/release-range are plugin `specificOptions`
(**imperial-unit options since 2026-07-01**; defaults 6,000×1,500 ft, 660 lb TNT, 3 NM — the Lua converts
to metric at read time). `pcall`-guarded throughout; inert with no `VietnamOps` data, so non-Vietnam
missions never load any of it.

### Why this shape

- **Losses stay native.** A bomber shot down before the run-in simply never fires its carpet, and where the
  box overlaps real ground TGOs the damage flows through the normal ground-loss path — no bespoke scoring.
- **Tactical strikers are untouched.** The heavy-bomber id gate means an F-4/A-4 Strike is an ordinary
  single-aimpoint strike.
- **Scripted carpet, not AI bombing.** AI B-52 bombing of a point target is inaccurate and unsatisfying; a
  scripted walking box over the area is both more reliable and more historical (Arc Light *boxes*).

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`populate_vietnam_ops_lua`, `HEAVY_BOMBER_DCS_IDS`) |
| Hook | `game/missiongenerator/luagenerator.py` (call in `generate_plugin_data`) |
| Plugin | `resources/plugins/vietnamops/` (`plugin.json`, `vietnamops-config.lua`) |
| Setting | `game/settings/` (`vietnam_arc_light`, "Vietnam Ops" page) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (eligibility gate, off = no node, no bombers = no record) |

### Gotchas / deferred — in-game pass ☑ VERIFIED 2026-06-28 (L1)

- **Blast power / density verified acceptable in the cockpit 2026-06-28** (checklist **L1**, audience pass,
  user verdict "good" — the carpet walks across the box, no FPS hit, no tuning requested). The knobs remain
  if a future campaign wants more/less: too weak and Arc Light underwhelms, too strong and it lags / over-kills.
- **Coordinate mapping:** pydcs Point (x=north, y=east) → DCS world vec3 `{x=north, y=alt, z=east}` is done
  Lua-side; ground height per impact from `land.getHeight`.
- **Symmetric by design:** any side's eligible heavy-bomber Strike carpets (a red Tu-95 too). Gated globally
  by the toggle; Vietnam campaign YAMLs flip it on.
- **Suite is Phase 1 of 5** — flak gauntlet, NGFS, convoy interdiction, Super Gaggle follow (see the suite
  design note).

## §33 — AAA flak gauntlet (Vietnam Ops suite)

The second **Vietnam Ops suite** feature. The fork's standing note is that the *real* Vietnam threat was
**AAA, not SAMs/MiGs**, yet Retribution's threat model is SAM/MEZ-centric and barely represents it. This adds
the AAA *atmosphere* campaign-wide: fly within range and below the ceiling of an opposing AAA gun and you draw
barrage flak; fly it predictably and the flak tightens.

### How it works

Unlike Arc Light, the flak needs **no per-mission threat data** — Python (`_populate_flak`) emits only an
on-marker `dcsRetribution.VietnamOps.flak = { enabled = "true" }` when `Settings.vietnam_flak_gauntlet` is on.
The `vietnamops` plugin does the rest:

- **AAA discovery (runtime).** Every ~30 s it sweeps both coalitions' ground units and keeps the ones with the
  DCS **`AAA`** attribute (so frontline ZSU-23/Shilka belts *and* airfield guns all contribute), grouped by
  side. No unit-name plumbing, and late-spawned guns are picked up.
- **Engagement.** Every 2.5 s, for each airborne aircraft between the floor (120 m AGL) and the ceiling
  (default 15,000 ft AGL), it counts alive **opposing** AAA guns within horizontal range (default 2.5 NM,
  capped at 3 for density) and, if any, spawns barrage bursts near the aircraft at its altitude.
- **Predictability.** A per-aircraft factor ramps up while heading (±8°) and altitude (±40 m) hold steady and
  drops fast on a jink. The barrage **miss distance** lerps from loose (1,000 ft, jinking) to tight (500 ft,
  predictable); a *sustained* predictable run (factor > 0.85) also occasionally (30 %/tick) draws one **close
  "tracking" round** (tighter miss, ×1.5 power) — the modest bite that punishes straight-and-level flight.

Bursts are `trigger.action.explosion` airbursts (small default power) — **mostly visual pressure to jink, not
a hidden hard-kill SAM**. Symmetric: both sides' AAA flak the other side. `pcall`-guarded throughout; inert
without the `flak` marker.

### Files & tests

| Area | Path |
|---|---|
| Emitter (on-marker) | `game/missiongenerator/vietnamopsluadata.py` (`_populate_flak`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (flak section) |
| Setting / options | `game/settings/` (`vietnam_flak_gauntlet`); plugin `specificOptions` (range/ceiling/miss/power) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (marker on/off, independence from Arc Light) |

### Gotchas / deferred — in-game pass ☑ VERIFIED 2026-07-01 (checklist L2): 2nd softening flown, user pass "light but fairer"

- **Lethality softened twice; re-fly owed.** The 2026-06-28 audience pass ("too accurate but working very
  well") read as a hard-kill threat rather than the intended mostly-visual pressure. The lever is the close
  **"tracking" round**. Two tuning passes since:
  - **2026-06-28:** `MIN_MISS` 70→110 m, tracking `miss ×0.35→×0.55` / `blast ×2.5→×2.0` and rarer
    (`factor > 0.66→0.8`), `BLAST` 8→6.
  - **2026-07-01 (L2):** the remaining lethality was the tracking round firing **every 2.5 s tick** once a jet
    held a steady line ~10 s. Now: base misses widened `MIN_MISS` 110→**150** / `MAX_MISS` 250→**320** m, and
    the tracking round is **occasional** — gated behind a sustained steady run (`factor > 0.85`) **and** a
    per-tick probability (`TRACKING_CHANCE = 0.3`) — and softened (`miss ×0.55→×0.75`, `blast ×2.0→×1.5`).
  Both passes changed `vietnamops-config.lua` **and** the matched `plugin.json` defaults. **The 2026-07-01
  re-fly (Yankee Station, session `intelligent-dubinsky`) confirmed the feel** — user pass: bursts "light but
  fairer", no hard-kill (the mission's player loss was a MiG gun kill, not flak) → `☑ VERIFIED`. If the
  gauntlet now reads *too* light, `flakBurstPower` / miss distances / range remain the campaign-side knobs.
- **Imperial-unit options (2026-07-01).** All flak options are now authored in imperial units and the
  mnemonics were renamed (`flakRangeNm` 2.5 NM / `flakCeilingFt` 15,000 ft / `flakMinMissFt` 500 ft /
  `flakMaxMissFt` 1,000 ft / `flakBurstPower` 6); the Lua converts to metric at read time. The rename also
  deliberately **flushes stale per-campaign saved options** — the L2 config-mismatch finding (a flown session
  still reading pre-softening `110/250/8` + `ceiling 5000`) can't recur, because the old metric keys are
  simply ignored and the softened imperial defaults seed fresh.
- **Runtime cost:** the 2.5 s sweep iterates airborne aircraft × nearby AAA (capped). Bounded and pcall-
  guarded, but watch FPS on a very dense mission.
- **Deferred polish:** tracer streams from the airstrip AAA belts (v1 is barrage puffs only); a per-pilot
  "heavy flak — jink" cue.

## §34 — Naval gunfire support (Vietnam Ops suite)

The third **Vietnam Ops suite** feature: offshore gun ships (the iconic New Jersey 16″ batteries, plus
cruisers/destroyers/frigates) deliver shore bombardment — a capability the modern engine never modelled.

### How it works

`_populate_naval_gunfire` reuses the generator's existing ship-artillery classification — naval groups whose
lead unit is class **CRUISER / DESTROYER / FRIGATE** (the VWV battleship *New Jersey* is class `Destroyer`, so
it's covered) — and emits each as `dcsRetribution.VietnamOps.navalGunfire.ships[] = { group, coalition }`
(coalition from `TheaterGroundObject.faction_color`). Targets and ranging are resolved live, so the node only
needs which ships have guns and whose side they're on.

The `vietnamops` plugin runs **two modes** off that list (both via `MOOSE GROUP:TaskFireAtPoint` + `PushTask`;
TIC has no artillery path of its own — its `TaskFireAtPoint` is combatants' direct-fire tracer shooting):

- **Player call-for-fire (F10).** Each coalition that owns gun ships gets an F10 **"Naval Fire Mission →
  Fire on last F10 map marker"** command. It reads the coalition's most recent F10 mark
  (`world.getMarkPanels`) and fires the nearest in-range friendly gun ship there (with a "SHOT"/"no ship in
  range" call back). The plugin's own FAC(A) and Super Gaggle marks (ids 970001+ and 980001+) are
  skipped: until 2026-09-29 their high ids always won, so the ships shelled the FAC's target or the
  friendly gaggle instead of the player's marker.
- **Automatic coastal bombardment.** Every cadence (default 90 s), each alive gun ship shells the nearest
  **opposing** ground target within gun range. Because ships sit offshore and the range gate is ~10 NM, this
  only ever reaches **coastal** targets — the feature is coastal-by-construction and **no-ops inland** (Khe
  Sanh), exactly as intended. Toggleable (`ngfsAuto`).

Symmetric (either side's gun ships). `pcall`-guarded; inert without the `navalGunfire` node.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_naval_gunfire`, `NAVAL_GUN_SHIP_CLASSES`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (NGFS section) |
| Setting / options | `game/settings/` (`vietnam_naval_gunfire`); plugin `specificOptions` (range/rounds/salvo/auto/cadence) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (gun-ship classification + coalition, carrier excluded, off / no-gun-ship = no node) |

### Gotchas / deferred — in-game pass done (checklist L3)

- **Coastal only.** Inland campaigns have no gun ship in range and correctly produce nothing; this is the
  historicity gate (Khe Sanh saw no naval gunfire). Keep `vietnam_naval_gunfire` **off** for inland YAMLs.
- **Gun reach is a selection gate, not a DCS truth.** `ngfsRangeNm` (default 10 NM; imperial-unit options
  since 2026-07-01) picks the ship/target; the actual round only impacts if the DCS gun can range it. Tune to
  the ship types in play during the pass (a 5″ destroyer ranges ~9 NM; the New Jersey's 16″ far more).
- **Escort ships:** tasking a gun ship `FireAtPoint` can pull an *escort* off its station. Fine for a
  dedicated NGFS ship; watch it on a screening destroyer.
- **Deferred:** JTAC auto-lase → auto fire-mission (reading CTLD's laser target couples to CTLD internals);
  the F10 marker call + auto bombardment cover the capability for v1. "Fire on my position" (needs per-group
  menus) also deferred in favour of the marker call.

---

## §35 — Convoy interdiction (Steel Tiger) (Vietnam Ops suite)

The fourth **Vietnam Ops suite** feature: a moving enemy supply column on the road behind the FLOT — the
Ho Chi Minh Trail / Operation Steel Tiger — surfaced to the player through Armed Recon.

### How it works — a *real* convoy in the force model (reworked 2026-07-01)

**The problem with the original.** v1 emitted a corridor and the `vietnamops` plugin spawned a vanilla truck
column at runtime (`coalition.addGroup`). Those trucks existed **only inside the generated `.miz`** —
Retribution's force model and debrief never knew about them (their names weren't in the `UnitMap`), so
killing the convoy **cost the enemy nothing** and the loss was never recorded. That is exactly a "free,
non-existent unit": a target with no consequence. A respawn loop made it worse (unbounded free trucks).

**The fix: use the engine's real convoy system.** Retribution already models convoys as first-class,
tracked objects — `coalition.transfers.convoys` carry **real ground units** between control points, spawn as
road-moving `VehicleGroup`s (`ConvoyGenerator`), are already **Armed-Recon / BAI objectives**
(`ObjectiveFinder.convoys`), and their destruction is recorded (`Debriefing.dead_ground_units` →
`enemy_convoy`) so the transferred units **never arrive**. So convoy interdiction no longer *invents* a
convoy — it **ensures a real one is flowing on the trail**:

- **`ensure_enemy_trail_convoy` (`game/retlab/vietnam_convoy.py`)** runs **once per turn** from
  `Game.finish_turn` (after the AI's own transfer processing, so it's idempotent — it does nothing if the
  opfor already has a convoy travelling). When `vietnam_convoy_interdiction` is on it:
  - picks the road **corridor nearest the front** on the real control-point graph — a rear opfor base with
    spare armour (`_pick_trail_corridor`) feeding the road-connected opfor base nearest the FLOT (the end
    nearer the front is the destination; opfor→friendly roads are the contested front and are skipped);
  - **skims a few real rear units** off the source base (`_skim_units`, capped at `MAX_CONVOY_UNITS` = 10 and
    never more than half the base's armour, so a source is never gutted);
  - creates a real `TransferOrder` via `coalition.transfers.new_transfer`, which **debits the units from the
    source base** (`commit_losses`) and — on a road first-leg — spawns a real, tracked `Convoy`.
- **Result:** interdicting the trail now **denies the enemy real reinforcements** (kill the convoy and those
  units never reach the line; let it through and they do), and the kill is recorded natively as an
  `enemy_convoy` loss. It is genuine force planning, not a cosmetic effect.
- **Fully guarded / no-op safe:** no front, no rear units, no road corridor, or the concurrent-convoy budget
  already full ⇒ it does nothing, and the engine's organic convoys still serve as targets. **The `vietnamops`
  plugin has no convoy runtime at all** now — the emitter (`_populate_convoy_interdiction`) and the Lua convoy
  section are deleted, and the convoy `specificOptions` are removed.

**More units, more concurrent convoys, spread across distinct roads (2026-07-03 rework).** A flown Trail 2
session found `MAX_CONVOY_UNITS` = 4 and the one-convoy rule thin — a single 3-vehicle column was the whole
hunt. The driver now keeps a **concurrent budget** (`BASE_MAX_CONVOYS` = 2, `SURGE_MAX_CONVOYS` = 3 under a
W6 `trail_surge` ≥ 2.0 — up from the old 1/2) instead of a single "is one already flowing" check. Filling
that budget isn't "spawn N more on the same road": `_pick_trail_corridor` gained an `exclude_sources`
parameter, and `ensure_enemy_trail_convoy` walks it in a loop, excluding each corridor's source as it's
committed, so **concurrent convoys prefer distinct roads** — several Vietnam campaigns actually have more
than one opfor-opfor corridor to offer (Yankee Station / Steel Tiger's full Ho Chi Minh Trail network of 8
legs, Khe Sanh's two rear feeders — Kobuleti→Senaki and Sukhumi→Senaki, Red Flag 81-2's several
aggressor-hub corridors). A campaign with only one qualifying road (or no distinct second source) simply
stays capped at one convoy that call, exactly as before the rework — never stacks a second column onto the
one road in use.

**The real gate wasn't the cap — it was an empty rear economy (same-day follow-up).** A headless engine
probe across the 4 land Vietnam campaigns found every rear opfor CP's `Base.armor` at **zero at turn 0** —
it's the coalition's turn-by-turn production/income stock, not a static garrison, so a fresh campaign's
trail was never actually gated by `MAX_CONVOY_UNITS`; it was gated by how little the rear base had
*accumulated* by turn 1. `_seed_trail_source` now tops a picked source up to a standing stock (2× a convoy
load, same bound as the pre-existing COIN ratline: "relocate, never grow") before every skim, sourced from
the coalition's real ground roster (`Faction.frontline_units` — e.g. the PT-76/ZU-23/S-60/MT-LB actually
seen in the probe below) rather than the tight COIN insurgent whitelist. Framed as **external logistics
support** (matériel from China/the USSR, not local production) — the historically accurate character of the
Ho Chi Minh Trail specifically. `MAX_CONVOY_UNITS` was also raised **6 → 10** now that it's the real
constraint rather than a number the source stock immediately clamped away. **Verified with a real engine
load** (turn 1, `ensure_enemy_trail_convoy` called directly): Yankee Station spawned 2 convoys of 10 units
each on 2 distinct roads (FOB Tchepone→Gudauta, FOB Ky Son→Sukhumi-Babushara — 20 vehicles total vs. the old
3-vehicle single column); Khe Sanh spawned 2 convoys of 10 on its 2 rear feeders
(Sukhumi-Babushara→Senaki-Kolkhi, Kobuleti→Senaki-Kolkhi).

**Velvet Thunder has no `supply_routes` block at all** (its theater is the Marianas island chain —
Guam/Rota/Tinian/Saipan — with no roads between the separate islands a truck convoy could physically
drive), so `vietnam_convoy_interdiction: true` there is a documented no-op regardless of the seeding rework
(no corridor is ever picked); the toggle should probably come off that campaign's settings, or the feature
needs an island-appropriate reinterpretation (a naval convoy?) — flagged as a follow-up, not fixed here.

**Right-click planning (added per playtest).** Rather than hunting for the corridor, the player
**right-clicks an enemy supply route** on the map to frag the interdiction package:
`SupplyRoute.tsx`'s `contextmenu` on the wide invisible hit-line → `POST /qt/create-package/supply-route/{route_id}`
→ `interdiction_target_for_route_id` (`game/server/supplyroutes/models.py`) resolves the route id — which now
encodes both CP ids as `"<cp_a_id>:<cp_b_id>"` — to the **enemy end** (preferring the contested CP), and the
Qt new-package dialog opens there with the add-flight dialog auto-opened and **Armed Recon pre-selected**. A
friendly (all-blue) route resolves to nothing and 404s. Still an Armed Recon frag — just discoverable on the
route instead of requiring the player to know where to look.

**Armed Recon is an area search — "look in the area and find them" (2026-07-05, restored).** A prior
playtest pass (#406) had replaced the classic single target waypoint with a **road-polyline sweep**
(SEARCH START / MID / END down `cp.convoy_routes`, ordered away from ingress). RetLab call reverted it:
marching a specific road wasn't a *look-in-the-area* search, and the runtime engage zone is already huge —
`armedreconingress.py` anchors an `EngageTargetsInZone` of radius `armed_recon_engagement_range_distance`
(**default 10 NM ≈ 18.5 km**), so a **single** area waypoint already blankets the whole corridor. So
`ArmedReconFlightPlan`'s builder (`game/ato/flightplans/armedrecon.py`) is back to the stock single
`armed_recon_area` overflight of the target area; the AI hunts everything in that ~18.5 km zone, and the
map's engagement ring (`ui_zone`) draws the searched area. Convoy / supply-route interdiction (§35) still
frags armed recon on the road's **enemy end** (the right-click flow); the flight now area-searches that
end instead of following the exact polyline. The road-follow overrides (`_search_track`/`_hunted_route`/
`_interdiction_route_for`) and the `armed_recon_point` waypoint helper were removed with their test file.
The AI's actual hunt behaviour rides the L7 in-game re-fly.

**The search point stands off the target area (2026-07-06).** A flown Inherent Resolve test caught the
fly-over waypoint sitting **dead-centre on the Shirqat FOB** — the armed-recon anchor is usually an enemy
control point, and `armed_recon_area` placed the steerpoint (`flyover=True`) on the CP position, i.e. on
top of the garrison's SA-13/ZU-23 (the player had to improvise a ~4 km offset and standoff Mavericks; the
plan should not route anyone over the FOB). `Builder._stand_off_search_point` (`armedrecon.py`) now pulls
the ARMED RECON point back along the target→ingress bearing after the layout builds: standoff = the
target CP's own longest TGO threat ring (`max_threat_range`, ground truth) + a 2 NM buffer, floored at
**5 NM** for an undefended area, and capped at both the engage-zone radius (so the target area always
stays inside the hunt zone, which `armedreconingress.py` centres on this waypoint — the zone shifts
toward the corridor where the convoys actually drive) and the distance to the ingress point. TOT/package
sync math is untouched (`travel_time_to_target` already measures to the package target, not the fly-over
point). Tests: the standoff cases in `tests/test_armed_recon_planning.py`.

**The hunt zone widens when the standoff hits the cap (2026-09-13).** Test 30 put three Hornet
Armed Recon flights on the AUROCHS AAA site: the KS-19 reads 20 km in pydcs, so the standoff was
capped at the 10 NM zone radius, the fly-over point sat 10 NM from the target, and the 10 NM zone
centred on it put the guns 80 m outside the rim. All three flights overflew the point, found no
ground unit in their zone, and went home without a shot. `ArmedReconFlightPlan.search_zone_radius`
(a pure function `search_zone_radius` in `armedrecon.py`) now returns the doctrine range or the
search point's distance from the target plus `SEARCH_ZONE_MARGIN` (2 NM), whichever is larger;
`armedreconingress.py` and the UI ring both read it. The standoff itself is unchanged, so any target
whose longest ring is 8 NM or more gets a 12 NM zone. In-game pass owed: **B123**.

### Files & tests

| Area | Path |
|---|---|
| Force-model convoy | `game/retlab/vietnam_convoy.py` (`ensure_enemy_trail_convoy`, `_pick_trail_corridor`, `_skim_units`) |
| Turn hook | `game/game.py` (`finish_turn`, once per turn after transfer processing) |
| Right-click server | `game/server/qt/routes.py` (`POST /qt/create-package/supply-route/{id}`), `game/server/supplyroutes/models.py` (`interdiction_target_for_route_id`, route id encodes both CP ids) |
| Right-click client | `client/src/components/supplyroute/SupplyRoute.tsx` (`contextmenu` → `useOpenNewSupplyRoutePackageDialogMutation`; hook hand-added to `_liberationApi.ts`) |
| Setting | `game/settings/` (`vietnam_convoy_interdiction`) — no plugin options (the plugin has no convoy runtime) |
| Tests | `tests/retlab/test_vietnam_convoy.py` (corridor pick incl. `exclude_sources`; unit skim respects the fraction cap; setting-off / budget-full / turn-0 no-op; tops the budget up to the deficit; concurrent convoys spread across distinct corridors; a single-corridor campaign stays capped at one; COIN seeds from the insurgent whitelist; **a non-COIN Vietnam campaign seeds an empty source from `Faction.frontline_units`**; no pool available degrades to a no-op). `tests/retlab/test_red_tempo.py` (the surge-widened budget + doubled skim, still source-fraction-clamped). `game/missiongenerator/tests/test_vietnamops_luadata.py` asserts the emitter **never** emits a `convoy` node. `tests/server/test_supply_route_interdiction.py` (route-id → enemy-end resolution). |

### Gotchas / deferred

- **The convoy is a real force change, gated behind the toggle.** Because it moves real enemy units toward
  the front, it slightly *helps* the enemy reinforce — which is the point of interdiction: the player pays
  for *not* flying the Armed Recon. It only runs when `vietnam_convoy_interdiction` is on (Vietnam campaigns),
  so the blast radius is contained.
- **Convoy leg VERIFIED (checklist L6, 2026-07-02 Trail 2 flown session `wonderful-chatterjee`, on the
  pre-rework sizing).** A real `Convoy 001` (2× PT-76 + a Grad-URAL) drove the trail, was found and fully
  killed by the player's Armed Recon Phantoms. That session's "only 3 vehicles, only 1 convoy" feedback
  drove the 2026-07-03 sizing + seeding reworks above; the debit/`enemy_convoy` debrief leg still needs
  confirming against a real (non-stale) `state.json`. The multi-corridor spread + the external-seeding
  10-unit convoys are headless-verified against a real engine load (see above) but unflown in the cockpit.
- **The external-seeding framing is a real design shift, not a bug fix, and it's a deliberate trade.** Before
  this rework the trail was gated by the coalition's own accumulated economy (a scarcity model: the player
  taxes what little the enemy has produced); now the trail always has stock to skim from, framed as external
  logistics support arriving from outside the theater. This is the historically accurate picture for the Ho
  Chi Minh Trail specifically, and it's what "many more vehicles on the trail" required — the coalition's
  turn-1 economy genuinely had nothing to skim. It also means the trail's size no longer reflects how the
  war is actually going for the enemy (it won't visibly shrink as the coalition's economy is strangled some
  other way) — a possible follow-on would be scaling the seeded stock to the coalition's own resolve/will
  state instead of a flat 2× load.
- **Velvet Thunder's missing `supply_routes` is a real gap, not fixed here.** No corridor is ever picked
  there regardless of the seeding rework (its island geography has no opfor-opfor road at all) — it may need
  a different interdiction concept entirely rather than a road.
- **Right-click path (checklist L7) needs an in-app pass + a CI client rebuild.** The server resolution is
  test-covered; the React `contextmenu` → Qt dialog path can't be exercised headless, and the client hook was
  **hand-added** to the generated `_liberationApi.ts` (codegen unavailable locally), so a stale `client/build`
  won't have it. It now frags Armed Recon onto the corridor where the **real** convoy travels.
- **Opfor is hard-picked as RED** (the human fights red in the Vietnam case). A blue-side convoy for a
  red-player campaign would be a follow-on.
- **Reliably-present, not always-present.** If the opfor has no spare rear armour or no road corridor, no
  convoy is nudged that turn (the engine's organic transfers may still produce one). Guaranteeing a target
  every single turn regardless of the enemy's stock is a possible refinement.

## §36 — Airbase harassment (rocket/mortar siege) (Vietnam Ops suite) — REMOVED 2026-09-16

**Removed on the DM's call ("drop the feature").** The barrage did what a barrage does to a
DCS airfield: it put the field into its under-attack state, and every AI fixed-wing launch at
that field was held on the ramp for the rest of the mission, because the four-minute cadence
never let the state clear. Measured on test 34 (Yankee Station: Maykop's two Phantom pairs and
four B-52s, Da Nang's Skyraider BAI and OV-10 CAS, all activated after the first barrage and
never moved; the pair that activated before it flew; the un-shelled fields launched everything)
and the same signature on tests 24 (Batumi), 31 (Anapa) and 33 (Damascus): ten fixed-wing groups
across four missions, zero counter-examples. Helicopters at shelled fields still lifted, which is
the tell (they need no taxi clearance). The generic `artillery_base_harassment` mode, the same
runtime with a 35–42 km reach, went with it, as did the two settings, the six plugin options,
the emitter, the Lua block, the Red Tide / Baltic Fury / Vietnam / COIN preseeds and the design
note. The COIN insurgent indirect fire (`coin_harassment`, §-less, `coin` plugin) is a separate
emitter and stays; it shells FOBs and FARPs only, where the hold does not bite. Airbases were in
its list until 2026-09-29 (Balad on Inherent Resolve was in reach) and are now filtered out in
`coinluadata.py`. Checklist L8 is closed.

What is worth keeping from it: the never-a-player-spawn-field exclusion walk
(`ato.packages → flights → departure/arrival/divert`) lives on in `coinluadata.py`, and the
lesson that a scripted explosion on an airfield is a mission-long ground stop for that field's
AI is now a hard constraint in CLAUDE.md.

## §37 — Super Gaggle hilltop resupply (Vietnam Ops suite)

The sixth **Vietnam Ops suite** feature (design note `retlab-vietnam-ops-notes.md`, §E). Models the Khe Sanh
"Super Gaggle": a formation of transport helos runs supplies into a cut-off forward friendly outpost while the
player can fly escort. The base engine has no besieged-outpost resupply; this makes the forward hilltops feel
supplied-under-fire the way they historically were.

### Scope decision — real squadron airframes, not the planner (reworked 2026-07-01)

The design's v1 was a **planner-template** auto-frag (suppress + cargo + escort package, self-planned like
`auto_combat_sar`), **blocked on an auto-plannable CTLD cargo run the engine lacks**. v1 shipped runtime-only
like the §35 convoy — but that spawned **phantom** helos + suppressors (`coalition.addGroup`) on an
**unbounded respawn loop**: free BLUE airframes the campaign never accounted for, whose loss was never a real
loss. The rework keeps the runtime spawn (still no CTLD dependency) but makes the airframes **real**: they are
drawn from real BLUE squadrons and their losses are charged back at debrief ("debit a squadron + track
losses").

### How it works

**Python plans the run from real squadrons once per turn (`game/retlab/super_gaggle.py`
`plan_super_gaggle`, from `finish_turn`).** It selects the besieged BLUE **FOB/FARP nearest a front** (within
`OUTPOST_FRONT_REACH_M` ≈ 150 km) + the nearest **other** BLUE helo-capable field as the launch point, a
**real BLUE helicopter squadron** (nearest the launch field, with airframes) to fly the gaggle, and a **real
BLUE attack squadron** (CAS-capable) for the suppressors. It records a `SuperGaggleCommitment` on the game
(persisted, `__setstate__` default `None`): the squadron ids, the squadrons' own aircraft types, the **exact
per-airframe unit names** the plugin will spawn (`SuperGaggle-T{turn}-Helo-N` / `-Sandy-N`), and the geometry.
Counts are `DESIRED_HELOS` (3) / `DESIRED_SUPPRESSORS` (2), each **capped by the squadron's `owned_aircraft`**.
No feature / no outpost / no launch / no helo squadron with airframes ⇒ **no commitment** (the gaggle is never
free-spawned).

**The emitter serializes the commitment (`vietnamopsluadata.py` `_populate_super_gaggle`).** It reads
`game.super_gaggle_commitment` and emits
`superGaggle = { coalition, countryId, outpost{name,x,y}, launch{x,y}, helo{type,names[]}, suppressor{type,names[]} }`.
No commitment ⇒ no node. `countryId` is the BLUE faction's DCS country (2026-07-01 audit fix): the plugin
spawns under it because `coalition.addGroup` places units on whatever coalition owns the country — the old
hardcoded USA fallback (kept only for pre-fix saves) spawned the gaggle NEUTRAL for any non-US blue faction.

**The `vietnamops` plugin spawns exactly the committed airframes, once, after a delay** (vanilla DCS
`coalition.addGroup`, `pcall`-guarded): a helo group named with the committed helo unit names (launch →
outpost → back), and the suppressor attack flight with the committed suppressor names (launch → over the
outpost on a CAS task → back). The suppressors carry their squadron's CAS fit, emitted by
`vietnamopsluadata.py` as `suppressor.payload` (pylons, fuel, flares, chaff); before 2026-09-29 they
spawned with empty pylons, because `coalition.addGroup` mounts nothing a unit does not list. **No respawn loop** — the run flies once (airframes are bounded to the
commitment), and a single tick fires the "delivered" / "down" cue then stops. The "inbound" cue notes the
suppressors when they spawned. **Launch is delayed, not immediate (2026-07-03 rework):** the whole spawn
was firing at t=0 (mission-config load), and a flown session's helos delivered by t≈306 s — the run was
over before a cold-starting player could plausibly be airborne to escort it. The plugin now defers the
entire spawn (helos, suppressors, cue, F10-mark-refresh tick loop — everything, wrapped in a local
`spawnGaggle()`) behind `timer.scheduleFunction(..., timer.getTime() + DELAY)`, `DELAY` defaulting to 600 s
(`gaggleDelaySec` plugin option) — enough for a typical cold start, taxi, and takeoff. The "armed" log line
still fires immediately (naming the delay), so ops can confirm the config without waiting; only the actual
spawn is deferred.

**Losses are charged back at debrief (`missionresultsprocessor.commit_super_gaggle` →
`super_gaggle.reconcile_super_gaggle`).** Because the spawned units aren't in the `UnitMap`, a killed gaggle
airframe's name lands in the debrief's **`killed_ground_units`** (see `Debriefing.from_json` — aircraft
classification requires a `UnitMap` flight). Reconcile counts each committed unit name found in either killed
list and debits its squadron (`owned_aircraft -= lost`, `destroyed_aircraft += lost`) — a **real airframe
loss**. Survivors cost nothing (a returning detachment — no pre-debit/return bookkeeping), and if any helo
survived the run is treated as **delivered** and the outpost gets a small `affect_strength` boost. The
commitment is then cleared (charged once). **No base-Lua / debrief-schema change** was needed — the existing
`dcs_retribution.lua` death-event capture already records the names.

### Files & tests

| Area | Path |
|---|---|
| Plan + reconcile | `game/retlab/super_gaggle.py` (`plan_super_gaggle`, `reconcile_super_gaggle`, `SuperGaggleCommitment`) |
| Turn hook / debrief | `game/game.py` (`finish_turn` → `plan_super_gaggle`; `super_gaggle_commitment` persisted), `game/sim/missionresultsprocessor.py` (`commit_super_gaggle`) |
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_super_gaggle`, reads the commitment) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (Super Gaggle section — single run, committed names) |
| Setting / options | `game/settings/` (`vietnam_super_gaggle`); plugin `specificOptions` (transit speed / altitudes / launch delay `gaggleDelaySec` — type & count come from the squadrons) |
| Tests | `tests/retlab/test_super_gaggle.py` (plan draws real squadron airframes with capped counts, clears when off / no outpost / no helo squadron; reconcile charges only killed names, floors at 0, credits delivery on survival, clears the commitment). `game/missiongenerator/tests/test_vietnamops_luadata.py` (emitter serializes a commitment's outpost/launch/helo+suppressor names; no commitment → no node). |

### Gotchas / deferred

- **Runtime run VERIFIED (checklist L9, 2026-07-02 Trail 2 flown session `wonderful-chatterjee`, on the
  pre-rework immediate-launch timing).** Both CH-53Es closed to 140 m of FOB Khe Sanh, delivered, and
  returned; both F-4E suppressors were shot down en route (one wreck also killed a friendly soldier) — the
  loss-accounting leg is now armed. The debrief charging exactly 2 F-4E airframes (and 0 CH-53s) to the
  suppressor squadron still needs confirming against a real (non-stale) `state.json`.
- **The launch-delay rework (2026-07-03) is itself unflown.** The Lua passes `luac5.1 -p`, but the deferred
  `timer.scheduleFunction` spawn hasn't been watched in a cockpit: confirm the "armed … launching in Ns" log
  line fires immediately, nothing spawns before `DELAY` elapses, and the run then proceeds exactly as the
  2026-07-02 pass already verified (helos reach the outpost, delivery/down cue fires once, losses charge back).
- **Loss accounting rides on the committed unit names appearing in the debrief.** If DCS ever failed to emit a
  death event for a runtime-spawned unit, that airframe wouldn't be charged (it would read as a survivor). The
  in-game pass should confirm a killed gaggle name lands in the state / debrief.
- **Suppressor weapons are still a tuning item.** The suppressor spawns with its squadron aircraft's *default*
  loadout (no explicit `payload`), so its effectiveness against the AAA is unverified — it may strafe or be a
  visual presence. A spawn failure stays harmless (guarded; the helo run proceeds).
- **Blue-only (symmetry deferred).** The plan hard-picks the BLUE outpost; a red-player mirror is a follow-on.
- **Losses-only — no delivery credit (2026-07-07 design call).** The earlier survival-gated
  `DELIVERY_STRENGTH_BONUS` (a clean run nudged the outpost's ground strength) is **removed**. The only signal
  the debrief carries is which committed airframes died, and an airframe's *absence* from the kill list is
  "survived and delivered" OR "never spawned at all" (e.g. the player ended the mission before the launch
  delay) — indistinguishable without a runtime "delivered" signal the plugin does not emit, and emitting one
  would need exactly the Lua/debrief-schema change this module avoids. So the gaggle costs the wing only the
  airframes it actually loses; a clean run is free. Re-introducing the credit is deferred behind a real
  delivery signal (the plugin writing a "reached the outpost" marker the debrief can read).

## §38 — FAC(A) willie-pete target marking (Vietnam Ops suite)

The seventh **Vietnam Ops suite** feature: the iconic Vietnam **forward air controller (airborne)**. An
OV-10 Bronco loitering over the battle area marks nearby enemy ground with **white-phosphorus smoke** so the
strikers — and the player — can visually acquire the target and roll in. The engine already has a **ground
JTAC** (stationary, *lases* targets for CAS); this is the distinct **airborne, smoke-marking** half that the
JTAC doesn't cover, and it's the defining Vietnam FAC image (the Bronco putting willie pete on the target).

### How it works

Same shape as §33 flak — an **on-marker + runtime discovery**, no per-mission data:
- **Python** (`vietnamopsluadata.py` `_populate_fac`) emits only
  `dcsRetribution.VietnamOps.fac = { enabled = true }` when `vietnam_fac_marking` is on.
- **The `vietnamops` plugin** discovers the FAC aircraft itself at runtime — airborne, alive friendly units
  whose DCS type matches the FAC type (default `Bronco-OV-10A`) — and, on a cadence (default 120 s, so the
  ~5 min smoke stays fresh), drops **white smoke** (`trigger.action.smoke`, willie pete) on the **nearest
  opposing ground unit** within the spot/mark range (default 3 NM) of the FAC, plus a "target marked with
  willie pete — cleared hot" cue to the FAC's coalition. Symmetric by construction (both sides scanned), but
  only OV-10 owners have FACs, so it's blue-effective in practice. No friendly OV-10 airborne over the front
  ⇒ nothing marked.
- Tunables (plugin `specificOptions`): FAC aircraft type, spot/mark range (NM, `facRangeNm` — imperial-unit
  options since 2026-07-01), mark cadence.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_fac`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (FAC section) |
| Setting / options | `game/settings/` (`vietnam_fac_marking`); plugin `specificOptions` (type/range/cadence) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (the `fac` on-marker is emitted when the setting is on, independent of the other suite features; off = no node) |

### Gotchas / deferred

- **Runtime VERIFIED (checklist L10, 2026-07-02 Trail 2 flown session `wonderful-chatterjee`).** The
  named F10 map mark appeared at the target cluster in a flown multiplayer session (user-confirmed),
  "FAC(A) marking armed" in `dcs.log`, no Lua error — the mark is unambiguously the plugin's (the
  Bronco's own WP rockets make no F10 mark).
- **Marking only — no auto-assignment (deferred).** v1 marks the target with smoke; it does **not** assign the
  target to a CAS package or coordinate a strike (that overlaps the ground-JTAC/tasking systems). The
  smoke-mark is the iconic, low-risk core; FAC→CAS coordination is a possible later increment.
- **Runtime-cosmetic.** A smoke plume, no gameplay-model change — the value is the visual target cue.
- **FAC type is a dropdown, not a typed id.** `Bronco-OV-10A` (default) or `vwv_o-1`, the two observation
  airframes in the tree — the value is matched against `getTypeName()`, so a typo silently meant no FAC at
  all. Add a light FAC to `choices` in `vietnamops/plugin.json` when one enters the tree;
  `test_string_options` pins every choice against `plane_map`.

## §39 — Snake and nape (napalm CAS) (Vietnam Ops suite)

The eighth **Vietnam Ops suite** feature: the iconic low-level napalm close-air-support delivery — **"snake
and nape"** ("snake" = Snakeye retarded/high-drag bombs, "nape" = napalm canisters), the signature Vietnam CAS
run where an attacker rolls in low and fast and lays a **wall of fire** across the enemy. DCS doesn't model
napalm as an effective AI/soft-target weapon, so this is the flavor layer that makes the on-the-deck run *do*
something visible and lethal to troops in the open. **Detonation-anchored since 2026-07-02**: the fire is
tied to real ordnance impacts, not a proximity heuristic.

### How it works

The on-marker is the §33 flak / §38 FAC shape; the runtime is **event-driven** (the Splash Damage
weapon-tracking pattern), no per-mission data:
- **Python** (`vietnamopsluadata.py` `_populate_snake_nape`) emits only
  `dcsRetribution.VietnamOps.snakeNape = { enabled = true }` when `vietnam_snake_and_nape` is on.
- **Release gate.** A `world.addEventHandler` `S_EVENT_SHOT` handler catches each release of an **eligible
  retarded bomb** — the weapon's DCS type name matched (case-insensitive plain-text, comma-separated
  patterns; default `SNAKEYE`, which catches the native `MK_82SNAKEYE` and the mod packs' Mk-81/82 Snakeye
  variants) — made from a qualifying **delivery profile at the moment of release**: the shooter airborne,
  at/below the run-in ceiling AGL (default 500 ft) and at/above the min ground speed (default 180 kts — keeps
  a loaded A-1 Skyraider run eligible). High, slow, or ineligible-ordnance releases are ignored: the ordnance
  **and** the profile are both the cost of the fire.
- **Track to detonation.** Each caught weapon joins a fast sample loop (0.1 s steps, alive only while an
  eligible weapon is in flight — a low Snakeye flies ~2–6 s) recording position/velocity. When the weapon
  stops existing it has detonated: the impact point is resolved by terrain-intersecting the final flight path
  (`land.getIP` on the last sample — the Splash Damage pattern, with a snap-to-ground fallback) and **one
  fire node** (`trigger.action.effectSmokeBig`, medium preset, auto-**stopped** after 90 s) **+ a modest
  `trigger.action.explosion` bite** (default 40 — napalm's real soft-target lethality, on top of the bomb's
  own native HE) is laid **at the real impact point**. The **wall of fire emerges from your actual ripple
  spacing** — a 6-bomb ripple burns as a 6-node line along the fall line; a dry pass lays nothing; a miss
  burns where it missed. The "SNAKE AND NAPE — napalm on the deck" cue fires once per salvo (a short
  per-shooter window), not per bomb.
- **Real napalm is excluded.** Mk-77 fire bombs (`MK77mod0/1-WPN`, the A-4E-C's cans) are skipped whatever
  the pattern list says — the bundled (locked) Splash Damage build already renders real napalm end-to-end
  (`napalm_mk77_enabled`: tracked impact fireballs, phosphor, unit damage), and double-rendering would stack
  effects. SD owns real nape; §39 owns the Snakeye stand-in.
- **Rewards, doesn't punish.** Unlike the flak gauntlet (which *thickens* against a predictable straight run),
  snake-and-nape *pays off* pressing the CAS run in on the deck — the risk of getting low is the trade for
  laying effective fire, and now the aim matters too.
- Symmetric by construction (any side's qualifying release; no aircraft-attribute gate — carrying and
  dropping the ordnance low **is** the eligibility, so a Snakeye-armed F-4 counts even though it lacks the
  `Attack airplanes` attribute the v1 scan required).
- Tunables (plugin `specificOptions`, imperial): release ceiling (ft AGL), min release speed (kts), the
  ordnance pattern list (`napeWeaponPatterns` — add e.g. `MK_82` to let plain slick low drops count),
  per-impact power.

### Files & tests

| Area | Path |
|---|---|
| Emitter | `game/missiongenerator/vietnamopsluadata.py` (`_populate_snake_nape`) |
| Runtime | `resources/plugins/vietnamops/vietnamops-config.lua` (Snake and nape section) |
| Setting / options | `game/settings/` (`vietnam_snake_and_nape`); plugin `specificOptions` (release ceiling/speed, weapon patterns, per-impact power) |
| Tests | `game/missiongenerator/tests/test_vietnamops_luadata.py` (the `snakeNape` on-marker is emitted when the setting is on, independent of the other suite features; off = no node) |

### Gotchas / deferred

- **Runtime is unflown (checklist L11).** The Lua passes the `luac5.1 -p` gate, but the `S_EVENT_SHOT`
  handler, the weapon tracking, and the `effectSmokeBig`/`explosion` placement can't be exercised headless.
  #1 thing to confirm in the cockpit: the released Snakeye's **type name actually matches the pattern list**
  across the flown modules (native + A-4E-C/mod-pack variants) — if a wanted bomb doesn't lay fire, check
  `dcs.log` for the armed line and widen `napeWeaponPatterns`. Also watch that the fire appears **at the
  impact points** (seconds after release, not at the release), that the fires **stop** after the burn time
  (no permanent infernos), and that a Mk-77 drop shows **only** the Splash Damage napalm (no doubled effect).
- **AI eligibility is now authored (2026-07-02): the doctrine low-level attack profile.** The 2026-07-01
  squadron call ("player-triggered only in practice — AI attack flights never fly the deck"; the Yankee
  Station session's A-1s sat at 6,400 m all mission) is addressed by the planner increment it named:
  `Doctrine.low_level_attack_altitude` (`game/data/doctrine.py`, Vietnam = **500 ft**, matching the
  `napeCeilingFt` default) caps the combat-altitude legs — ingress, the attack run, egress, and the attack
  plan's nav legs — of **CAS / BAI / Armed Recon** flights in `WaypointBuilder.get_combat_altitude` (+ the
  `cas()` 1,000 m track floor is bypassed), so era attackers press their runs in on the deck at RADIO/AGL
  waypoints. Strike is deliberately exempt (Alpha Strike dive deliveries + B-52 Arc Light, which rides
  Strike), as are helos (own AGL logic) and heavies (`HEAVY_BOMBER_DCS_IDS`, now shared from
  `game/data/units.py`). Gate helper `low_level_attack_altitude_for` is unit-tested
  (`tests/ato/flightplans/test_low_level_attack_profile.py`); the **flown half is still owed** — the plan
  puts the AI low, but whether the DCS AI's own `AttackGroup` delivery releases ≤ 500 ft AGL is an L11
  cockpit question (if it climbs to dive-bomb anyway, next levers: pass `altitude=` on the BAI
  `AttackGroup` task or raise `napeCeilingFt`). The §33 flak interplay (low + steady = tighter bursts) now
  applies to AI runs too — that trade is the point. NEW game required (doctrines pickle by value).
- **Detonation-anchored (2026-07-02 rework).** v1 was proximity-triggered — a 2 s poll laying a fixed swath
  on the *nearest enemy unit* whenever an `Attack airplanes`-attributed aircraft crossed a low/fast/near
  gate. That fired with **no ordnance released** (a dry low pass = a free napalm wall), made **aim
  irrelevant** (you couldn't miss — and a perfect drop just outside the scan range rendered nothing), and
  mistimed/misoriented the fire. The rework ties everything to real releases and real impacts; the retired
  options (`napeDropRangeFt`/`napeSwathLengthFt`/`napeFireNodes`, plus the per-aircraft cooldown) gave way
  to `napeWeaponPatterns` — bombs are the cost now, so no cooldown is needed.
- **The per-impact bite is real (by design).** Unlike flak's mostly-visual power, the default blast is tuned
  to hurt soft targets — that *is* the feature (napalm was devastating to infantry/trucks), stacked on the
  Snakeye's own native HE. Dial `napeBlastPower` down (or to 0) for a purely-cosmetic wall of fire.

## §40 — Campaign phases (inferred arc + planner emphasis) — REMOVED (2026-07-21)

**REMOVED 2026-07-21 (the ROE-mechanic drop).** The turn-by-turn phase classifier
(`game/fourteenth/phases.py`), its BLUE planner emphasis (the offensive-middle reorder of
`PlanNextAction`), the ROE **restricted zones / free-fire zones / target-release** layer with its
`.miz` + web + kneeboard surfaces, the campaign-status phase ribbon, and the authored
Rolling Thunder → Linebacker II arcs are all gone. The shared `PlanNextAction._offensive_order` seam
the classifier used to drive stays for §52/§67/§68. Do not restore. The three `414th-campaign-phases-*` design notes were deleted 2026-08-20, recoverable from git before `5db34150f`.

### Red tempo (survives — rehomed 2026-07-21)

The **W6 red-tempo** layer (design note
[`retlab-vietnam-red-tempo-notes.md`](design/retlab-vietnam-red-tempo-notes.md),
`game/retlab/red_tempo.py`) was NOT removed with the phases — it was **rehomed off the per-phase
blocks onto a top-level campaign `red_tempo:` schedule of turn-windows**. Each window is
`{from_turn, name?, trail_surge?, ground_offensive?}`, and the window in effect on a
given turn is the **last one whose `from_turn` has been reached** (last-window-wins). A `trail_surge`
window runs bigger, more-concurrent enemy trail convoys (`ensure_enemy_trail_convoy` reads
`trail_surge_multiplier`); a `ground_offensive` window fires a Tet/Easter stance pulse
(`apply_red_tempo` in `initialize_turn`, after the coalitions plan) that raises red's front stances to
AGGRESSIVE (raise-only) — pressure on the ground battle, never sweep-capturing. (The `resolve_regen`
lever was dropped 2026-07-21 with the will economy.) Authored on 6 campaigns — 1968 Yankee Station,
Velvet Thunder, Desert Storm, Inherent Resolve, Enduring Resolve, Red Flag 81-2; a campaign with no
block is a complete no-op. Tests: `tests/retlab/test_red_tempo.py`. In-game pass: checklist **M6**.

## §41 — High Digit SAMs "Ultimate Compilation" support

Retribution's High Digit SAMs mod support targeted the original **HighDigitSAMs v1.4.0**, a mod that has
been unmaintained for years. The fork now targets its actively-maintained successor, the
**[HighDigitSAMs Ultimate Compilation](https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation)**
(v1.4.3+ — HighDigitSAMs + SAM Pack + SAM Sites Asset Pack + IDF Assets Pack in one install). The same
`high_digit_sams` New Game toggle gates everything (relabeled in the wizard, plus a **fork-mismatch
warning** — an always-visible note under the mod list + a control tooltip naming the exact dcs-sams build
and explaining that the original Auranis mod / other forks rename units and silently break); no save
migration is needed.
All unit data was read from the **installed mod's own Database lua files** (launcher threat = missile
`distanceMax`, tracker detection = the vehicle-file tracking range), not guessed from specs.

### What changed vs. v1.4.0

- **Dropped by the mod** (DCS core now has vanilla equivalents): the HDS `KS19` / `Fire Can radar` AAA pair
  (vanilla KS-19/SON-9 and the existing `KS-19/SON-9` preset replace them — the redundant `KS-19_HDS`
  preset is deleted) and the `SA-24 Igla-S manpad` (factions re-pointed to the vanilla SA-18 Igla-S).
- **Renamed S-300PS radars**: `40B6M MAST tr` → `30N6 MAST tr`, `40B6MD MAST sr` → `76N6E sr`,
  `64H6E TRAILER sr` → `64H6E MOD sr` — the S-300 Site layout, the SA-10B preset, `radar_db.py`, and the
  Morocco faction livery map were re-pointed. The retired pydcs classes (and their unit YAMLs) are **kept
  registered for save-compat only** — do not reference them in factions/presets/layouts.
- **New families added** (38 → 80 registered units): **S-400/SA-21** (3 LN types incl. the 400 km 40N6E,
  2 TR, 3 SR, CP), **S-300V4** (3 LN incl. the 380 km 9M82MDE, TR, 2 SR, CP), the **S-300PT** launcher,
  a PMU2 mast TR, **Pantsir-SM** (SHORAD class), the **SAMP/T battery** (ARABEL/Ground Fire 300 STRs, C2,
  ECS, EPP, Block 1/1NT TELs), **SA-7/SA-7b manpads**, four **EWRs** (P-37 Bar Lock, 55G6U Nebo-U, 1L119
  Nebo-SVU, generic tower), and the **ERO pack** (ZU-23 Toyota technicals, insurgent ZU-23, SA-2 site
  props). The IDF pack the compilation bundles was already supported via the separate `irondome` toggle
  (identical unit ids).

### Wiring

- **Presets** (`resources/groups/`): new `SA-21/S-400`, `SA-23B/S-300V4`, `SA-10A/S-300PT` (all riding the
  extended S-300 Site layout), `SAMP/T` + `SAMP/T NG` (new `SAMP/T Battery` layout reusing
  `Patriot_Battery.miz` geometry), `Pantsir-SM SHORAD`, `ZU-23 Technicals (ERO)`.
- **Factions**: modern Russia/redfor get S-400 + V4 + Pantsir-SM + Nebo EWRs; russia_1980 gets the S-300PT;
  france_2005 gets SAMP/T; 70s-80s Middle-East/NK reds get SA-7/7b and Vietnam-era + Cold-War reds the
  P-37 Bar Lock (which also closes the
  "red faction has zero EWR units" blind-net gap for 16 period factions; under Skynet its
  entry sat outside `searchRadar` and it reported nothing until 2026-10-16); insurgents get the ERO
  technicals.
- **Skynet profiles (since 2026-09-12)**: the S-400 / S-300V4 / SAMP/T / Pantsir-SM `samTypesDB` entries
  ride in the vendored compiled build, taken from upstream #956 (our #851 work). Under the 2026-06 to
  2026-09 MANTIS bridge the sites were banded by Retribution's own emitted threat
  range instead, so the new units classified correctly from the pydcs
  threat ranges.
- **Bug fixed in passing**: `Faction.remove_vehicle` matches the DCS unit type **id**, but the pre-existing
  HDS strips passed display *names* — so `SAM SA-14 Strela-3 manpad`/`SA-24`/`Polyana-D4M1` were silently
  never stripped when the mod was off. All strips now use ids (upstream-carve candidate).
- **Preset-group strip is provenance-backstopped (2026-07-12)**: the mod-off preset strips are an
  exact-name list, so a renamed/new preset silently leaked mod units into a no-mod game's buy menu and
  AI procurement pool (found via Red Tide's since-removed `SA-10A/S-300PT (Single Radar)`; the same
  hole leaked the `[CH] Russian Navy` preset in three modern-Russia factions).
  `Faction.apply_mod_settings` now also strips any preset group whose units come from a disabled
  `pydcs_extensions` package (`disabled_mod_packages`, name-independent), and `Game.on_load` sweeps
  the pickled `ArmedForces` with the same predicate so existing saves self-heal. CI-locked across all
  shipped factions in `tests/retlab/test_faction_mod_presets.py` (upstream-carve candidate).

### Files & tests

| Area | Path |
|---|---|
| Unit registry | `pydcs_extensions/highdigitsams/highdigitsams.py` (new families + retired-unit tombstones) |
| Unit YAMLs | `resources/units/ground_units/` (42 new files, filename = DCS type id) |
| Radar DB | `game/data/radar_db.py` (new TRs/STRs, launcher→tracker pairs, SR/EWR radar labels) |
| Layouts / presets | `resources/layouts/anti_air/S-300_Site.yaml` (extended), `SAMPT_Battery.yaml` (new), `resources/groups/` |
| Mod gating | `game/factions/faction.py` (id-correct strip list), `qt_ui/.../QGeneratorSettings.py` (label + fork-mismatch note/tooltip) |
| Factions | 25+ `resources/factions/*.json` (fixes + era-respecting enrichment) |
| Tests | suite-wide faction/layout loading; headless smoke: all preset units resolve, all factions load with the toggle both ways |

### Gotchas / deferred

- **In-game pass DONE (checklist N1, under MANTIS).** Spawn/engagement of the new sites (S-400/V4/SAMP-T), MANTIS
  banding of the 300+ km launchers, and SA-7 infantry launches can't be exercised headless. (Per squadron
  call, the SA-7/7b are NOT wired into the 4 Vietnam factions — they keep only the P-37; the manpads stay
  on syria_1973/1982, iraq_1991, north_korea_2000, iran_1988 and remain available to custom factions.)
- Detection/threat ranges intentionally mirror the *mod's* numbers, not real-world spec sheets — a 400 km
  40N6E MEZ ring is dominating on any map; treat the `SA-21/S-400` preset as a strategic-tier buy.
- The `SAMPT_MLT` (Aster-15) and Block 2 TELs, the ZPU-2 Toyota variants, and the Gazetchik-decoy UNITS_WITH_RADAR
  entry are **not** loaded/registered — the mod's own `entry.lua` comments the first three out; match it.
- Old saves referencing retired units keep unpickling (classes + YAMLs kept), but a pre-migration campaign
  generating a mission with a retired unit id will fail against the new mod in DCS — start a new game.

## §42 — Local DCS chart base layers (map tiles)

The client map's three stock base layers are real-world Esri imagery, which does not match the terrain DCS
actually models (roads, towns, forests, even coastlines differ). This feature lets a **locally installed**
tile pyramid — e.g. one sliced from Flappie's community "accurate DCS Caucasus map" GeoTIFF, which is drawn
from the DCS terrain itself — appear as an extra base-map choice in the unified map layers panel (§19), so
the campaign map shows what the pilot will actually see in the sim.

**Purely local content, never bundled.** Tiles live under
`Saved Games/Retribution/MapTiles/<name>/{z}/{x}/{y}.png` with a `tileset.json` sidecar (display name, zoom
range, WGS84 bounds, attribution). The server advertises whatever exists there; on machines with no tiles
the panel shows only the three stock buttons and nothing else changes. Copyright is the reason for the
local-only design: community charts are redistributed at their authors' pleasure, so the repo carries the
*tooling*, not the imagery.

### Wiring

- **Tiler** — `tools/tile_geotiff.py`: standalone Pillow-only tool (no GDAL) that slices an **EPSG:3857**
  GeoTIFF into a z5..native XYZ pyramid + writes the `tileset.json`. The georeference is read from the
  TIFF's ModelPixelScale/ModelTiepoint tags; non-Web-Mercator inputs are rejected (no reprojection).
  Native zoom = finest standard zoom at least as fine as the source (Flappie's 39.1 m/px Caucasus → z12).
- **Storage** — `persistency.map_tiles_dir()` → `<Saved Games>/Retribution/MapTiles`.
- **Server** — `game/server/maptiles/`: `GET /map-tiles/` lists installed sets (malformed
  `tileset.json` is skipped with a warning, never fatal); `GET /map-tiles/{name}/{z}/{x}/{y}.png` serves a
  tile or 404s. Game-independent (no campaign loaded required). Traversal-safe: `{name}` is restricted to
  `[A-Za-z0-9_-]+` and z/x/y are typed ints.
- **Client** — `MapLayersControl.tsx`: fetches `/map-tiles/` once on mount; each set adds a segmented
  base-map button (`local:<name>`, persisted like the stock choices). Selected → a react-leaflet
  `TileLayer` pointed at the server URL with the set's bounds/min/maxNativeZoom/attribution; a persisted
  choice whose tiles are gone falls back to Clarity.

### Files & tests

| Area | Path |
|---|---|
| Tiler tool | `tools/tile_geotiff.py` |
| Storage | `game/persistency.py` (`map_tiles_dir`) |
| Server routes | `game/server/maptiles/{routes,models}.py`, registered in `game/server/app.py` |
| Client | `client/src/components/maplayers/MapLayersControl.tsx` + `.css` |
| Tests | `tests/server/test_map_tiles_routes.py` (listing, meta, malformed-meta skip, tile serving, 404s, traversal) |

### Gotchas / deferred

- **Needs an in-app pass (checklist O1):** the chart rendering/alignment over the campaign overlays can't
  be exercised headless, and the client change needs the CI client rebuild.
- The tile pyramid is ~10k PNGs (~0.5 GB) per theater at z12 — regenerate with the tiler, delete the set's
  folder to uninstall. Zooming past the native zoom upscales (maxZoom 19), which is expected to look soft.
- The base-map button appears for every installed set regardless of the loaded campaign's theater — a
  Caucasus chart on a Syria campaign just renders off-map (its `bounds` stop tile requests); switch back
  to a stock base map. Theater-aware filtering is deferred until a second theater chart exists.

## §43 — Per-aircraft flight defaults (save fuel + properties)

The Edit-flight → **Payload** tab's aircraft knobs — **Internal Fuel Quantity**, **Aircraft Condition**,
**Aircraft Wear and Tear**, **Aircraft Type On Spawn**, and any other property-editor value (HMD, ripple,
etc.) — are re-seeded from the pydcs engine defaults every time a flight is created. A player who always
wants (say) their F/A-18C to spawn hot with 80% fuel had to redo those on every package. This feature gives
that box the persistence the player laser code already has (a campaign-wide setting): a
**"Save as default"** button that remembers the current
fuel + properties **per airframe**, so every new flight of that type starts pre-configured.

**Opt-in and inert until used.** No Settings toggle — on-disk content is the switch, exactly like the DCS
`UnitPayloads` files. Until a user saves a default for an airframe, nothing changes.

### Wiring

- **Store** — `game/retlab/flight_defaults.py`: a JSON file
  (`game/persistency.py` `flight_defaults_path()` → `<Saved Games>/Retribution/flight_defaults.json`),
  keyed by DCS aircraft id → `{"fuel": <kg>, "properties": {<prop id>: <scalar>}}`. **Global** (survives
  across campaigns), **never part of a save game** — the same shape and lifetime as the `UnitPayloads`
  files. Loaded once and cached in a module global (`invalidate_cache()` for tests); the writers keep the
  cache and file in lockstep. `properties` holds only what the user actually set in the property editor (an
  untouched knob isn't stored and falls back to the engine default).
- **Apply** — `apply_flight_defaults(flight)` is called from `Flight.__init__` immediately after
  `initialize_fuel()`, but **only when `roster is None`** (a genuinely fresh flight, never a clone that
  already carries member edits) and **only for the BLUE coalition** (`coalition.player.is_blue` — a `Player`
  enum, never bare truthiness), so enemy AI is never touched. It clamps the saved fuel to the airframe's
  tank and `update()`s each member's `properties`. Everything is best-effort: a missing store (persistency
  not set up in a headless test), a malformed file, or an airframe with no entry is a silent no-op — it can
  never break flight generation.
- **Never stored: the datalink identity.** The STN and voice callsign (`DATALINK_PROPERTY_IDS`,
  `game/radio/datalink.py`) name one jet. Save and apply both drop them (2026-10-11); a stored STN was
  copied onto every member of every new flight of the type. The generator fills a blank box
  (`FlightGroupConfigurator.set_datalink`), keeps a typed STN and reserves it before any allocation
  (`AircraftGenerator._reserve_typed_datalink_identifiers`). An empty box reads "Auto".
- **UI** — `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py`: a row under the fuel slider with
  **Save as default** (captures the selected member's `properties` + `flight.fuel`) and **Clear default**
  (enabled only when a default exists, via `has_defaults_for`). Both confirm with a `QMessageBox`.
- **Payload-tab layout cleanup (2026-07-06)** — the whole tab was regrouped into labeled sections:
  a **Flight members** group (member spinner + the two "same for all" checkboxes; the bold AI-loadout
  warning now only shows while the loadout checkbox is *unchecked*), an **Aircraft settings** group
  (laser codes + property editor in the scroll area — content now top-aligned, the "pre-configured at
  mission start" explainer moved to a tooltip — with the fuel slider + this defaults row pinned below),
  and a labeled **Loadout:** preset row above the custom-loadout editor. Pure layout — no signal/logic
  changes; verified by an offscreen headless instantiation across 7/10/11/12/14-pylon airframes (member
  rebind, warning visibility, custom-loadout round-trip).
  **Follow-up 1 (same day):** the *Aircraft settings* scroll now sizes to its content
  (`AdjustToContents` + `Maximum` size policy, capped at 400px, no layout stretch) instead of taking a
  fixed share of the tab. On an **AI-crewed** flight every F-4-style aircraft property is `player_only`,
  so the property editor renders empty and the box was ballooning into a large blank gap between the
  laser rows and the fuel slider; it's now compact (scroll `sizeHint` ~66px, just the two laser rows).
  A **player** F-4E still grows to fit its 23 controls, bounded at the 400px cap so the full list scrolls
  rather than pushing the loadout off the bottom (verified headlessly: AI F-4E box h=66 vs player F-4E
  h=288, both under the cap; other airframes scale with their property count).
  **Follow-up 2 (same day) — pylon-scroll reverted:** the initial cleanup had wrapped `QLoadoutEditor`'s
  pylon list in its own `QScrollArea` (to kill a hypothetical dead-gap below the last pylon). That
  **collapsed the loadout's size hint**, so the `QEditFlightDialog` (which has no fixed size — it opens at
  its content `sizeHint`) opened shorter *and* trapped the pylons in a mini-scroll — a player F-16
  (12 stations) showed only ~5-6. The pylon grid is now laid out at its **natural full height again** (as
  before the rework), so its size hint drives a tall dialog that shows every pylon at once; the aircraft
  scroll (which *can* shrink) absorbs the squeeze on a short screen. Net: the loadout is the dominant
  element and is never crushed.
- **Display point** — the property widgets already read `member.properties.get(id, default)` (see
  `propertyspinbox.py` / `propertycombobox.py`), so a seeded value shows immediately when the tab opens for
  a new flight — the whole point of the feature.

### Heatblur condition baseline (2026-10-18)

Heatblur's F-4E and A-6E carry **Aircraft Condition** (`Quality`) and **Aircraft Wear and Tear**
(`Wear`), both player-only in DCS. The module default of 100 condition is "showroom/prototype grade"
on Heatblur's scale (F-4E manual, Mission Editor chapter, pages 1022 to 1025); 90 is a standard
service jet. `game/retlab/airframe_condition.py` `condition_defaults` gives an untouched player jet
90, or 75 when the mission date is before 1980. Any airframe with both properties qualifies
(today the F-4E, QF-4E and A-6E).

- **Generator** — `FlightGroupConfigurator.setup_props` fills the baseline only into a key the member
  left unset, and only for player members. A value from the payload tab or a saved default wins.
- **Payload tab** — `PropertyEditor` passes the baseline to `PropertySpinBox` as the shown default, so
  the box reads what will fly. Switching members no longer writes the shown value into the member
  (signals are blocked in `set_flight_member`); before, that pinned a default onto a member nobody edited.
- **Squadron wear (B250)** — `Squadron.airframe_wear` (0 to 50, saved; old saves load at 0).
  `MissionResultsProcessor.commit_squadron_wear` runs after each mission for blue squadrons
  whose airframe has the two properties: `airframe_hours_by_flight` takes each flight's
  longest airborne §91 record times its aircraft count (an AI group has one sampled record),
  and `next_wear` adds 10 per hour per owned airframe and takes 5 off. A turn with no sortie
  records (nothing flew, or an old recorder) only recovers. The payload tab shows it as the
  Wear and Tear default.
- **Not built:** Heatblur's persistent airframe (`Aircraft Type On Spawn` = Persistent with a
  `Persistent Aircraft Key`). Brady passed on it 2026-10-18: the save lives on each player's PC
  and RetLab has no per-airframe identity.
- Checklist row B249.

### Files & tests

| Area | Path |
|---|---|
| Store | `game/retlab/flight_defaults.py` |
| Heatblur condition baseline | `game/retlab/airframe_condition.py`, `tests/retlab/test_airframe_condition.py` |
| Path | `game/persistency.py` (`flight_defaults_path`) |
| Apply hook | `game/ato/flight.py` (`Flight.__init__`, after `initialize_fuel`) |
| UI | `qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py` |
| Tests | `tests/retlab/test_flight_defaults.py` (round-trip + reload, BLUE-only apply, red/no-entry no-ops, fuel clamp, clear, missing-persistency silence) |

### Gotchas / deferred

- **Applies to BLUE AI flights too, including fuel.** "Default for this aircraft" means every fresh BLUE
  flight of the type, not only the ones you fly — so a saved sub-full fuel default reduces the starting fuel
  of BLUE AI flights of that airframe as well (same as dragging the slider would). This is intended; it
  mirrors the manual slider and only ever affects your own side. Red is never touched.
- **Captures what's currently in the property editor**, i.e. the selected flight member. With "use same
  loadout for all members" on (the norm), that's uniform; per-member property divergence isn't saved.
- **Needs an in-app pass (checklist Q1):** the button + the "new flight opens pre-configured" behaviour is
  Qt UI that CI can't exercise. The store/apply logic itself is unit-tested.

---

## §44 — Long-range carrier ops

> **Fog gate (2026-08-18):** `_nearest_legal_strike_target` picks from ground truth, so
> it could frag the package at a hidden command post — naming it in the ATO and revealing
> it on the strike. It now skips `hidden_from(Player.BLUE, tgo)` (the `map_hidden` skip
> beside it went with the §50 ambush, 2026-10-11). This planner is BLUE-only by construction, so the viewer is never in
> question. Same change as §63; see there for why `fog_intact()` is part of it.

A deterministic carrier strike package for campaigns that park the carrier far beyond the auto-planner's
reach. **Operation Enduring Resolve (COIN)** stands the boat ~800 km off the Helmand AO — the real OEF
Arabian-Sea carrier cycle — and the stock planner never anticipated that standoff.

### The problem

The auto-planner gates every squadron by a plane range check: `Squadron.capable_of` compares the
distance-to-target against `max(aircraft.max_mission_range, settings.max_mission_range_planes)`. With the
carrier 400-500 NM from the Helmand targets and the default range ceiling, **every** carrier squadron is
rejected, so the Hornets, the A-6 tankers, and the E-2 all sit on the deck while the land-based air fights
the whole war. Simply raising the range ceiling gets the Hornets *assignable* to the commander's ATO, but the
theater support planner still won't crew the boat's own tanker/AEWC out there (the tanker orbit sits at the
nearest land field the probe A-6 can't reach, and the AEWC/tanker support packages prune when the
fighter-poor COIN wing can't spare their escorts).

### The fix (two parts)

1. **Range ceiling** — the campaign preseeds a wider `max_mission_range_planes` (600 in Enduring Resolve) so
   the carrier air is *assignable* to the wider war. The commander flies spare Hornets on nearer tasks (SEAD)
   once the deterministic package below has claimed its section.
2. **The deterministic package** — `plan_carrier_strike` (`game/retlab/carrier_ops.py`) frags **one**
   carrier package per plan pass from the boat's own squadrons: a Hornet **STRIKE** section
   (`STRIKE_SECTION_SIZE = 2`) + an A-6E tanker + an E-2 on AEW&C. It pins the carrier airframes via
   `ProposedFlight.preferred_type` and forces them through the range gate with `ignore_range=True`, building
   the package through the engine's own `PackageFulfiller` so it gets proper flight plans, waypoints, fuel,
   and a shared TOT. `coalition.ato.add_package(package)` adds the result.

### Wiring

- **Hook** — `game/coalition.py` `plan_missions`, inside a tracer span, calls `plan_carrier_strike`
  **before** `TheaterCommander(...).plan_missions(...)`. Ordering matters: run it first so the boat's Hornets
  are claimed for this package, then the commander flies any spares. Run *after* the commander and it finds no
  Hornets left (the commander spends them on nearer SEAD).
- **Support as PRIMARY flights, not escorts** — the tanker and the E-2 are appended as primary
  `ProposedFlight`s (`FlightType.REFUELING` / `FlightType.AEWC`), never as `EscortType.Refuel` escorts.
  `EscortType.Refuel` is a dead end: `check_needed_escorts` only ever marks `AirToAir`/`Sead` escorts
  "needed", so a refuel escort (and an AEWC escort) always prunes. As primaries the A-6 gets a tanker orbit
  off the boat (launch + recovery gas — ingress/egress/recovery tanking) and the E-2 an AEWC orbit.
- **Target choice** — `_nearest_legal_strike_target` walks the red control points' alive ground objects,
  skips anything ROE-blocked (`game.fourteenth.phases.roe_blocks_target` — the same restraint the rest of the
  BLUE planner honors, so the carrier never gets fragged into a population ring), and returns the nearest,
  **preferring ammo caches** (the COIN cache throttle — thematically the carrier's job) over other strikeable
  TGOs.
- **Selection helpers** — `_friendly_carrier` (the BLUE-owned carrier CP), `_carrier_squadron` (the biggest
  stocked carrier squadron that `capable_of` a task), `_carrier_aircraft` (its `AircraftType`), and
  `_already_planned_from` (one carrier STRIKE package per pass — a commander package that used the boat
  doesn't get doubled).

### Buddy-tanker routing for the boat's other flights

The strike package's A-6 holds one orbit on the carrier's egress corridor. But the commander separately frags
the boat's *other* carrier flights — the SEAD Sweep and SEAD Escort Hornets — in their **own** packages, and
those packages carry no tanker. The stock planner builds their `REFUEL` waypoint from the package geometry
(`RefuelZoneGeometry`, between origin and join), which for a carrier package lands ~500+ NM up-range near the
target, where **no tanker exists**. On the real COIN save the carrier SEAD Hornets' refuel points sat ~560 km
from the A-6 — a dry tank.

`route_carrier_flights_to_buddy_tanker` (run **after** `TheaterCommander.plan_missions`, so the commander
packages exist) fixes this. It finds the carrier's buddy tanker (a `REFUELING` flight off the boat whose
package is *not* a dedicated tanker package), takes its orbit center (`_orbit_center` — the midpoint of the
racetrack/patrol legs), and for every other carrier-departing flight whose package has no tanker of its own
and that carries a `REFUEL` waypoint, pins that flight's refuel point onto the A-6 orbit and rebuilds its
flight plan. Since the A-6 sits on the launch/recovery route, the Hornets now tank from the boat's own held
tanker on ingress top-off and egress recovery.

The buddy A-6 is pinned to the strike package and can't move, so the pass moves the receivers to the tanker.
(The mirror-image pass that moved a *theater* tanker to its receivers was reverted on 2026-08-09 — see
§tanker demand.)

- **The override** — `Flight.refuel_point_override` (a `Point`, default `None`, `getattr`-guarded for old
  saves) set by the pass. The three refuel-waypoint builders (`formationattack.py`, `tarcap.py`, `escort.py`)
  build their `REFUEL` waypoint at `flight.refuel_waypoint_position(package.waypoints.refuel)`, which returns
  the override when set and the shared package point otherwise — a one-line, behavior-preserving change for
  every non-carrier flight.
- **Scope guards** — BLUE only; only flights whose `departure` is the carrier; only packages **without** their
  own tanker (so the strike package's own Hornets, which tank in-package, are left alone); land-based flights
  are never touched (verified on the real save — the Kandahar/Bastion flights kept their refuel points).

### Gating

Behind `long_range_carrier_ops` (`Settings`, RetLab Features → Naval & missile strike, **default OFF**),
BLUE only, guarded at every step — no carrier, no Hornets, no legal target ⇒ silent no-op. Preseeded ON in
`resources/campaigns/coin_enduring_resolve.yaml` alongside `max_mission_range_planes: 600`; every other
campaign is byte-for-byte untouched.

### Files & tests

| Area | Path |
|---|---|
| Planner | `game/retlab/carrier_ops.py` (`plan_carrier_strike` + `route_carrier_flights_to_buddy_tanker`) |
| Hook | `game/coalition.py` (`plan_missions`: strike before `TheaterCommander`, buddy-tanker routing after) |
| Refuel override | `game/ato/flight.py` (`refuel_point_override` + `refuel_waypoint_position`); `game/ato/flightplans/{formationattack,tarcap,escort}.py` (builders honor it) |
| Setting | `game/settings/` (`long_range_carrier_ops` + `_LAYOUT_SPEC` "Carrier operations") |
| Preseed | `resources/campaigns/coin_enduring_resolve.yaml` (`settings:` block) |
| Tests | `tests/retlab/test_carrier_ops.py` (off-switch, red no-op, carrier discovery, squadron pick, already-planned guard, ROE-respecting nearest-cache target, buddy-tanker routing); `tests/retlab/test_coin.py` (the campaign preseed lock) |

### Gotchas / deferred

- **Engine-probe verified, not yet flown (checklist P2).** The full package build (Hornet strike + A-6 tanker
  + E-2, forced through the range gate) was proven on the real COIN save — `PKG → target = F/A-18C Strike x2 +
  A-6E Refueling x1 + E-2C AEW&C x1`, all off the boat, valid flight plans + shared TOT, with the commander
  also flying spare Hornets on SEAD. The unit tests lock the pure guards/selection; the package build itself
  is not something CI can exercise, so it needs an in-game pass.
- **One package a turn, by design** — `STRIKE_SECTION_SIZE = 2` and the `_already_planned_from` guard keep
  this to a single sustainable coordinated package, not the whole air wing surged off the deck.

## §45 — Support-package F10 orbit markers

At generation, each **blue tanker + AEW&C** orbit is painted onto the F10 / Mission-Editor map as a labelled
racetrack, so a pilot can find their tanker/AWACS in the cockpit. The reliable, **DTC-free** answer to
"where's my gas?" — an object on the shared F10 map every player sees in flight, no cartridge / pre-load /
per-airframe device.

### How it works

`DrawingsGenerator.generate_support_orbits` runs in the drawings pass (`missiongenerator.py`, right after
`generate_air_units`, so `MissionData` is fully populated):

- **Which flights** — `mission_data.flights` filtered to `flight_type in {REFUELING, AEWC}` and
  `friendly.is_blue`. Enemy + non-support flights are skipped.
- **The orbit** — the flight's racetrack ends come from its waypoints: `race_track_start` is emitted as a
  `PATROL_TRACK` waypoint and `race_track_end` as a `PATROL` waypoint (the waypoint builder), so the pair
  defines the leg. Drawn with `add_oblong(start, end, radius)` — a capsule that reads as a
  racetrack — or `add_circle` if the ends coincide.
- **The look** (2026-10-06) — outline only, one colour per job: tankers solid green
  (`TANKER_ORBIT_LINE`), AEW&C solid amber (`AEWC_ORBIT_LINE`), CAP stations a thinner solid cyan
  (`CAP_ORBIT_LINE`; dashed until a flown look showed it near invisible). The old cyan fill stacked into one wash over blue sea, and DCS renders
  `LineStyle.Dash` as a faint dotted hairline, so the fill was all that showed. A CAP shape
  passed no `fill` and so took pydcs's red default; every shape now passes `NO_FILL`. A text
  box's border takes its text colour, so each label is the job's colour on a dark box, at
  18 pt (CAP 14). Row B185.
- **The width** — `_support_orbit_radius` sizes the capsule off the flight's own `patrol_speed`: the
  level-turn radius at 20° of bank plus 3 NM, floored at `SUPPORT_ORBIT_MIN_RADIUS_M` (2 NM). The fixed
  2 NM half-width it replaced left the aircraft outside its own box for about half the time on station,
  because the AI turns shallow at the end of the leg and overshoots the end waypoint before rolling in.
  Measured on test 36: the two KC-135s ran 17.7 and 19.0 km off the leg centreline, the E-3A 13.8, the
  E-2C 8.9. CAP stations keep the fixed 2 NM — a CAP chases contacts and no capsule can contain it, so
  that one is a station marker, not a claim about where the flight is.
- **The label** — `add_text_box` at the racetrack start: `<callsign>  <type>` on line 1, `<freq>  TCN <tacan>`
  on line 2. Callsign/type come from the `FlightData`; freq/TACAN come from the matching `TankerInfo`/
  `AwacsInfo` (looked up by `group_name` — `FlightData` doesn't carry the advertised freq/TACAN). AWACS has no
  TACAN, so that bit drops.

`MissionData` is now threaded into `DrawingsGenerator` (was `mission` + `game` only); a `None` `mission_data`
makes the pass a no-op (so existing/other callers are unaffected).

### Gating

Always-on, like the other F10/ME map drawings (frontlines, routes, CPs, ROE zones) — no Settings toggle. A
toggle (default on) is a possible follow-up if the racetrack clutter is unwanted.

### Files & tests

| Area | Path |
|---|---|
| Painter | `game/missiongenerator/drawingsgenerator.py` (`generate_support_orbits`, `_racetrack_ends`, `_support_label`) |
| Wiring | `game/missiongenerator/missiongenerator.py` (`MissionData` passed to `DrawingsGenerator`) |
| Tests | `tests/missiongenerator/test_support_orbit_drawings.py` (tanker w/ label, AWACS w/o TACAN, non-support/enemy skip, None-data no-op) |

### Gotchas / deferred

- **Emitter-tested + serialize-probed, not yet flown (checklist R1).** The test uses a real pydcs `Mission`
  (so `add_oblong`/`add_text_box` are exercised) and a probe confirmed the drawings serialize into the `.miz`
  table; whether DCS renders the racetrack over the actual orbit needs an in-game pass.
- **Blue-only.** Enemy support isn't marked (it's not intel the player should have for free).
- **Label freq/TACAN depend on the `group_name` match.** If a support flight's `FlightData.group_name`
  doesn't match its `TankerInfo`/`AwacsInfo`, the orbit + callsign still draw but the freq/TACAN line is
  dropped rather than wrong.

## §46 — Route-aware fuel-tank planning (fuel-first) — REVERTED 2026-08-09
> **REVERTED to upstream behavior on 2026-08-09**, as work order C of the auto-planner
> re-convergence (`docs/dev/design/retlab-autoplanner-upstream-divergence-audit.md`, DECIDED block).
> The DM's call was that §46 reverts **outright**, not re-gated. Everything from here to
> "The racetrack burn" describes how the feature worked and is kept for history only —
> **do not author against it.** Rebuildable from git history if it is ever wanted back.
>
> **What upstream does now:** every non-helo flight in a formation-attack package gets a
> REFUEL waypoint whenever the wing can plan `REFUELING` (`_build_refuel`), on the egress
> leg only. There is no fuel math in the decision, no pre-vul refuel, no tank fitting at
> plan or generation time, and no dwell charged at the tanker.
>
> **What was deleted:** `game/ato/refueltasking.py` · `_refuel_tasking` and the `refuel_pre`
> layout slot · `FlightPlan.refuel_duration` and its charge in `total_time_between_waypoints`
> · `plan_sortie_fuel` / `add_range_fuel_tanks` / `top_up_for_route` and the tank-fitting
> helpers · the `auto_range_fuel_tanks` and `fuel_tanks_over_jammers` settings (pruned from
> old saves by `_migrate_legacy_settings`) · `FormationFlightPlan.push_time`'s route walk
> (back to the straight hold→join line) · the package tanker's early window opening.
>
> **What survives, and why:**
> - **The racetrack burn** (last subsection below) — U25/U34, kept failure fixes. A patrol's
>   on-station time and lap burn are still charged; that was a modeling hole, not §46.
> - **External-fuel accounting** — `game/retlab/range_fuel.py` keeps `is_fuel_tank`,
>   `tank_capacity_lbs`, `external_fuel_lbs`, `flight_external_fuel_lbs`. They only *report*
>   the tanks a loadout already carries, for the kneeboard fuel ladder and the Payload-tab
>   readout (`game/retlab/fuel_brief.py`). Nothing fits stores any more.
> - **The `estimated_fuel_consumption` fallback** and the hand-measured `fuel:` data blocks.
> - **`Flight.refuel_point_override`** — §44 long-range-carrier plumbing. `_build_refuel`
>   still routes through `refuel_waypoint_position`, so §44 keeps working.
>
> **PR #820 sequencing:** #820 (exempt AI from the receiver dwell) was already **merged**
> before this revert landed, so it could not be closed as superseded — this change deletes
> the dwell it fixed. Nothing is owed on it.

### The racetrack burn (2026-07-19) — KEPT through the §46 revert

> Audit items U25/U34, kept as failure fixes when the rest of §46 reverted on 2026-08-09.
> The patrol dwell and its lap burn were missing from the schedule and the fuel model
> everywhere, which is a modeling hole independent of fuel-driven tanker tasking.

Original note — "19 GSPD is impossible" / "should be on station until bingo":

A flown BARCAP kneeboard showed the racetrack-end row at **19 kt GSPD** and an RTB margin of **+8,488 lb** —
both artifacts of the same modeling hole. A patrol plan's `patrol_start -> patrol_end` leg carries the
**on-station dwell** in the schedule (`total_time_between_waypoints` returns `patrol_duration`; the flight
laps the track until push), but `fuel_consumption_between_points` charged the leg as its **straight-line
length** — 13.9 nm at cruise = ~300 lb for a 45-minute station — so the ladder never paid for the orbit, and
the kneeboard's derived GSPD divided the track length by the whole dwell.

- **The fuel model charges the laps.** `FlightPlan.fuel_burn_distance_between_points(a, b)` (new hook,
  straight leg by default) is overridden by `PatrollingFlightPlan` for the patrol leg: `patrol_speed ×
  patrol_duration`, floored at the track length. Every consumer inherits it — the kneeboard ladder (both the
  min-fuel and planned walks), the RTB margin, `fuel_brief`, and the sim's per-waypoint fuel estimates. The
  flown Hornet case re-runs honestly as ~8,000 lb on station and an RTB margin of **~+830 lb**: the 45-minute
  doctrine dwell was already near the fuel limit — the ladder was just lying about it. Applies to every
  patrolling family (BARCAP/TARCAP at their patrol speeds, CAS at combat rate over its track, AEW&C/tanker
  orbits). Formation-attack holds are deliberately untouched. (Originally that was so the ladder and the §46
  tanker decision walked the route the same way; since the §46 revert there is no fuel-driven tanker decision
  left to agree with, and the hold dwell stays uncharged simply because nothing has asked for it.)
- **The racetrack-end GSPD cell shows the patrol speed.** `FlightData.patrol_speed` (from
  `flight_plan.patrol_speed` when `is_patrol`) rides to the kneeboard; the `PATROL`-type row prints it (the
  Hornet reads 481) instead of distance-over-dwell, and dashes when no patrol speed exists (custom plans).
- **The on-station endurance call-out answers "until bingo".** The planner's dwell is doctrine
  (`desired_barcap_mission_duration` + the §6 wave relief schedule), not a fuel computation, so the flight
  plan now prints `On station 45 min planned; fuel supports ~50 min before bingo (RTB minimum).` under the
  RTB margin — amber when the gas cuts the planned station short. Computed from the ladder itself
  (dwell from the racetrack rows' ToTs, burn from their fuel drop, the push-time margin over `min_fuel`).
- **Deliberately NOT done:** fuel-capped patrol durations (shortening/stretching the planned dwell to the
  jet's gas) — the §6 BARCAP wave count and relief cadence key off the doctrine duration, so a per-flight
  fuel-derived dwell needs the wave scheduler to consume it; and dwell-aware `add_range_fuel_tanks` (bags
  for station time, not just route length) — a fleet-wide loadout shift that should be its own decision.
- Tests: `tests/ato/flightplans/test_patrol_timing.py` (laps burn, the track-length floor, transits
  unchanged) · `tests/missiongenerator/test_flightplan_fuel_column.py` (the PATROL row's patrol-speed GSPD +
  dash fallback, the endurance line + its short-station warning). The next S1 fly should eyeball a BARCAP
  ladder: racetrack GSPD ≈ patrol speed, push-time fuel visibly down, the endurance line rendering.

---

## §47 — Continuous campaign clock & weather

A stock turn advanced the campaign by re-rolling two things from scratch: the time-of-day rotated through a
fixed **Dawn → Day → Dusk → Night** slot cycle (one slot per turn) with the *actual* clock picked as a
**random hour inside that slot's band**, so consecutive turns teleported ~4–8 h with no continuity, and the
date only ticked once every four turns (`start_date + turn // 4`). Weather was an **independent, memoryless
draw** each turn from the season's probability table — a thunderstorm could be followed by clear skies followed
by rain, with no fronts moving through. Neither system carried any state forward, so a campaign never felt like
one continuous timeline.

This ties date, time-of-day, and weather to **one marched clock** anchored to the campaign's chosen start date,
so the war flows: the clock steps forward a believable few hours each turn, the date rolls over at midnight, and
weather systems roll in and clear over several turns — the calendar advances in step with the marched clock instead of jumping.

### The two levers

1. **Continuous clock (`Conditions.advance`).** Instead of "slot rotation + random hour," the actual
   `start_time` is carried forward from the previous turn's conditions and advanced by a jittered interval —
   `random.randint(MIN_TURN_ADVANCE_HOURS, MAX_TURN_ADVANCE_HOURS)` = **3–7 whole hours** (a sortie plus
   turnaround; whole hours keep the "missions start on the hour" property). **Time of day is then *derived*
   from the marched clock** via `daytime_map.best_guess_time_of_day_at`, and the date rolls over naturally as
   the clock crosses midnight — the season (and thus the weather table + temperature/pressure interpolation)
   updates on its own as the calendar marches through the months.

2. **Weather with memory (`Conditions._evolve_weather_type`).** The archetypes sit on a severity ladder
   `_WEATHER_LADDER = [ClearSkies, Cloudy, Raining, Thunderstorm]`. When a `previous` weather is passed, the next
   turn is a **Metropolis–Hastings** step: a *proposal* drawn from `_WEATHER_PERSISTENCE_KERNEL[distance]`
   (`{0: 3.0, 1: 1.0, 2: 0.3, 3: 0.1}`, distance = rungs from the previous archetype — a strong pull to stay,
   moderate to step one rung, small to jump), then *accepted* against the seasonal chances with probability
   `min(1, (chance_j · Z_i) / (chance_i · Z_j))` (the `Z` terms normalise the per-rung proposal; the kernel
   cancels). With no `previous` (turn 0 seed, or the legacy path) the draw is the original memoryless behaviour,
   byte-identical.

   **Why MH and not a plain reweight.** The obvious "multiply each seasonal chance by the kernel and draw"
   makes weather autocorrelated but **skews the long-run climatology** toward the calm end — a symmetric kernel
   over asymmetric seasonal weights pools probability in the common states. Measured on real Caucasus-summer
   chances (`clear 55 / cloudy 35 / rain 10 / storm 1`), the naive reweight **more than halved the rain
   frequency** (9.9% → 4.7%) and cut storms to a sixth. MH fixes the marginal exactly: the accept step gives
   the chain a stationary distribution equal to the seasonal chances, so over a long run the authored rain/storm
   frequencies are preserved (measured skew ≤ ~1pp) **and** a zero seasonal chance is still never reachable —
   while the near-rung proposal keeps transitions gradual (measured: stay-same ~75–80%, jumps ≥2 rungs ~1–3%,
   mean dwell ~4–5 turns, vs ~40% / ~14% / ~1.6 turns memoryless). The
   `tests/weather/test_continuous_campaign_clock.py` chain tests pin both properties.

### Wiring

- `Game.continuous_clock_active` gates the whole feature: `getattr(settings, "continuous_campaign_clock",
  False)` **and** `settings.night_day_missions == NightMissions.DayAndNight`. The day-only / night-only mission
  settings explicitly opt out of the natural cycle, so they fall back to the per-turn rotation; the `getattr`
  keeps pre-feature saves on the legacy path.
- `Game.current_day` / `Game.current_turn_time_of_day` become authoritative off `self.conditions` when the
  clock is active (`conditions.start_time.date()` / `conditions.time_of_day`), else the legacy `turn // 4` /
  slot-rotation formulas. Both `getattr`-guard `conditions` because it isn't built yet during the turn-0 seed
  (which reads these properties → legacy path → identical seed).
- `Game.finish_turn` calls `advance_conditions()` (→ `Conditions.advance`) instead of `generate_conditions()`
  when the clock is active, for `turn > 1` (turn 0 and 1 still share the seed, unchanged).

### Save compatibility

`Settings.__setstate__` builds a fresh `Settings()` and overlays the old state, so an existing save picks up
`continuous_campaign_clock=True` on load. This is **seamless mid-campaign**: the last conditions were generated
from `current_day` (the `turn // 4` date), so `conditions.start_time.date()` already equals that date — the
clock reads the same date and simply begins marching forward from there. No jump, no migration entry needed.

### Gating

`continuous_campaign_clock` — RetLab Features → **Campaign clock & era**, **default OFF
since the 2026-08-09 re-convergence** (the planner-suite preset turns it on). Off = the stock
per-turn rotation + memoryless weather exactly. Requires day-and-night missions (above).

### Files & tests

| Area | Path |
|---|---|
| Clock + weather | `game/weather/conditions.py` (`Conditions.advance`, the `previous=` path in `generate_weather` → `_evolve_weather_type` MH step, `MIN/MAX_TURN_ADVANCE_HOURS`, `_WEATHER_LADDER`, `_WEATHER_PERSISTENCE_KERNEL`) |
| Game wiring | `game/game.py` (`continuous_clock_active`, `advance_conditions`, `current_day`, `current_turn_time_of_day`, `finish_turn`) |
| Setting | `game/settings/` (`continuous_campaign_clock`) |
| Tests | `tests/weather/test_continuous_campaign_clock.py` (monotonic march within the 3–7 h band; time-of-day derived; date rolls at midnight; weather biased toward the previous rung; zero seasonal chance still honoured; memoryless without `previous`) |

### Gotchas / deferred (checklist T1 — in-game pass DONE)

- **Atmospheric continuity is archetype-level, not fine-grained.** Pressure/temperature/wind are still
  instantiated fresh per turn (anchored to seasonal + time-of-day averages), so they don't wildly swing while
  the archetype is stable, but a persistent low-pressure *system* carried numerically across turns is a
  possible follow-up. Archetype persistence is the dominant visual signal and is what this ships.
- **Day-only / night-only opt out.** By design — those settings mean "I don't want the natural cycle." The
  continuous clock only runs under day-and-night missions.
- **Interval is fixed-band, not a setting.** The 3–7 h advance is a module constant; exposing it as a tunable
  is a trivial follow-up if the pacing wants tuning after an in-game pass.

### The Time & Weather window (2026-10-09)

Works with or without `continuous_campaign_clock`.

- **Sun and moon.** Under the date box: sunrise and sunset in theater-local time, where the
  start falls against them, and the moon's lit fraction and phase. Measured at
  `theater_middle` (the mean of the non-off-map bases). `game/weather/daylight.py` holds
  `sun_times`, which the recon Departure kneeboard page now also uses.
  - suntime's clock time is right but its **date can slip a day** (Guam's sunset came back on
    the prior day), so `sun_times` pins both to the asked-for local date.
  - The moon is the mean-phase method from a reference new moon; under a day of drift.
- **Air & Visibility column** (`qt_ui/widgets/conditions/QAtmosphereAdjustmentWidget.py`):
  temperature (°F), altimeter (inHg, the DCS editor's 720–790 mmHg range), turbulence as
  Light/Moderate/Heavy (8/22/40 in DCS's 0.1 m/s units), fog, and a dust storm
  (`Weather.dust`, a class default so old saves load; never rolled).
- **ACCEPT keeps what was not edited.** The dialog rebuilds the weather object, which used to
  re-roll temperature, altimeter, turbulence and fog every time. Each control now hands the
  turn's own value back unless it was changed.
- **DCS's fog rules** (read from `MissionEditor/modules/me_weather.lua`, `fixFog`):
  - pydcs writes miz version 20, so the legacy `enable_fog` block is converted to manual fog
    (`fog2` mode 4). It was always written `enable_fog = false`, so Retribution's fog never
    reached a mission with automatic fog off. `EnvironmentGenerator.set_fog` now switches it on
    when automatic fog is off.
  - Dust survives only with every kind of fog off, automatic fog included. `set_dust` writes
    it only then, and the window greys both out while `use_auto_fog` is on and makes them
    exclusive. Row B203.
- Wind rows read 6,600 ft and 26,200 ft (DCS's 2,000 m and 8,000 m levels).

Tests: `tests/weather/test_daylight.py`, `tests/test_mission_fog_and_dust.py`,
`tests/qt_ui/test_atmosphere_adjustment.py`.

## §48 — Commitment ceiling (will-coupled war budget) — REMOVED (2026-07-21)

**REMOVED 2026-07-21 (the will-economy drop).** The commitment ceiling
(`game/fourteenth/commitment_ceiling.py` — the will→BLUE-budget draw-down) and the entire
political-will economy it capped are gone: the BLUE **Political Will** / RED **Regime Resolve** meters,
the `negotiation_verdict` win/loss ending, the campaign-authorable `will:` profiles + warship feed, the
per-turn will feeds/ledger, and the Vietnam campaign-layer **W1 (political will) + W2 (negotiation
ending) + W2b (static front)** pieces (`game/retlab/{political_will,static_front}.py` deleted). The
Vietnam **W5 GCI ambush** and **W6 red tempo** survive (W6 lost only its `resolve_regen` lever); §21
POWs now always run a turn-countdown clock, never an indefinite will-coupled hold. Do not restore. The design notes
`414th-vietnam-political-will-roe-notes.md` and `414th-will-generalization-notes.md` were deleted 2026-08-20, recoverable from git before `5db34150f`.

## §49 — Mobile missile relocation (the SCUD hunt) — REMOVED (2026-08-29)

**REMOVED 2026-08-29 (DM call, on the test-24 evidence).** Theatre-missile sites no longer
relocate; they generate where the campaign map puts them and stay there, which is the
pre-§49 behaviour. Deleted: `game/missiongenerator/mobilemissileluadata.py`, the
`mobilemissiles` plugin, the `mobile_missile_relocation` setting, its four campaign preseeds
(Desert Storm, Marianas 2027, Baltic Fury, Red Tide), and
`MissionData.missile_fire_missions`. Sites themselves, their §85 support sections and their
scripted `FireAtPoint` volleys are untouched. Do not restore.

**Why it went.** The feature never once relocated a site in a flown mission, across three
attempts to fix the same interaction:

- **2026-07-16** — the scoot's `setTask` clobbered the pending fire task; 12 of 13
  batteries silently lost their fire missions to the first relocation. Fixed by holding a
  group until its fire window passed.
- **2026-07-17** (Scenic Route) — a fired battery would not drive afterwards. `resetTask()`
  recovered 2 of 9 fired batteries; all 4 whose fire task never ran drove fine. Fixed by
  giving `FireAtPoint` a stop condition (`MISSILE_FIRE_WINDOW_S`) so the task completes.
- **2026-08-29** (test 24, Caucasus Iron Gate turn 1, 72 min) — both fixes in place and
  **still zero relocations across six sites**. Maximum displacement was **44.5 m** against a
  4,000 m scoot radius. Two sites (CAT, DIREWOLF) carried fire holds of 5,181 s and 5,483 s
  against a 4,344 s mission, so they were held past the end and never tried. The other four
  fired — 18 × 9M723 launched — and then refused every route push; the plugin's own
  progress check gave up on all four with `no movement across 2 route pushes`.

The stop condition stays: without it a fired battery's task never ends and the group is
locked in its deployed state for the rest of the mission. That is a property of the fire
task, not of the scoot, and it is now recorded on `MISSILE_FIRE_WINDOW_S` itself.

**Constraints lifted out before deletion**, because they apply to every scripted mover and
outlived §49:

- A mover's DCS group needs a **2-waypoint route** — current position, then destination. A
  single destination waypoint reads as "you are already there" and the group never drives.
- One **undrivable member pins a whole group**: a route push moves a DCS group as a unit, so
  a static emplacement in it produces no movement and a per-frame ground-AI levelling storm.
  This is why the §85 missile-battery support section is trucks only, and why four ground
  unit yamls carry `mobile: false` (still read by the web client's TGO movement routes).
- Any **player-interactable mover must still be moving 90 minutes in**, so a late intercept
  is possible.

The first two were previously anchored on §49; they now live on the §85 layout comment
(`resources/layouts/defenses/missile.yaml`), the unit yamls, and the hard-constraints list
in `CLAUDE.md`.

## §50 — Ambient supply convoys (the convoy ambush was removed 2026-10-11)

A few real supply columns run both sides' road networks every turn, so there is traffic to hunt and
to protect. The other half of this section, hidden ambush teams on blue's roads, was removed
2026-10-11; its record is at the end.

**The ambient-convoy layer (2026-07-06).** The squadron call: convoys
present in every miz, both sides, "a few convoys per side, some on the same route, some on different
routes, randomized — don't force numbers." `game/retlab/ambient_convoys.py` `ensure_ambient_convoys`
tops **each side's** convoy flow up to a `randint(MIN_AMBIENT_CONVOYS, MAX_AMBIENT_CONVOYS)` (1..3) target
every turn on **randomly chosen DISTINCT** same-side corridors (`_RNG.sample` — one column per road, the
count capped at the road count); organic transfers and the §35 trail convoys count toward the target, so
nothing stacks on top of existing traffic. **Distinct roads, one transfer per corridor (2026-07-07 S5 fix).**
The convoy map keys transports by `(origin, destination)` (`TransportMap.add` in `game/transfers.py`), so two
transfers on the SAME corridor **coalesce into one oversized group** that line-spawns into unauthored
positions and **deadlocks** at mission start — the flown S5 regression (a 24-vehicle blue column parked at
Baghdad the whole mission). Sampling *distinct* corridors keeps
every column a separate, driveable group; it trades away the originally-sketched "some columns share a road"
texture, which the merge made unachievable anyway (a shared road was never two columns — it was one parked
blob). Corridors are enumerated once per road and oriented rear→front off the §35 `_reference_points`
(fronts, or the opposing CPs on a front-less laydown); each column carries the real units already in its rear
base's roster. **Skim-only — no free unit seeding
(2026-07-07 design call).** Ambient columns **relocate** existing rear units (`_skim_units`) and never call
`commission_units` to invent free ones. The §35 Vietnam trail's `_seed_trail_source` external-logistics
free-seed is *right for that feature* — red-only, Vietnam-gated, the Ho Chi Minh Trail's documented
character — but generalizing it here would top up **both** sides' rear bases with un-budgeted units every
turn on **every** campaign (up to ~48 net-new free ground units/turn game-wide, permanently reinforcing
front-ward bases), which the squadron never asked for: they asked for *traffic to hunt and protect*, not a
free-reinforcement firehose. So a rear base too thin to skim (< 2 armor) simply yields no column that turn
(`new_transfer` debits the source immediately, so re-picking a source in the loop reads its live stock).
Red's ambient columns are ordinary Armed Recon / BAI targets. Gated `ambient_supply_convoys` (Mission Generation → Battlefield life, default
**ON**); a side with no same-side road (island maps, all-red graphs) is a silent no-op.

**It runs whether or not the convoys spawn.** `perf_disable_convoys` (**Disable land convoys**) only stops
`ConvoyGenerator` putting the groups in the mission. The transfers still happen in the force model, so with it
ticked each side still moves 1 to 3 columns of 8 vehicles between its own bases every turn, unseen.

### No phantom spawns (the §35/§37 lesson)

The columns are **real, tracked units** so every loss is reconciled natively — the discipline the
interdiction and Super Gaggle reworks established:

- **The convoy is a real `coalition.transfers` transfer.** Its destruction is units that never arrive:
  `MissionResultsProcessor.commit_convoy_losses` already iterates *both* coalitions' convoys and calls
  `convoy.kill_unit`, and the debrief recognizes `convoy.player_owned.is_blue`. So a blue convoy shot up on
  the road costs the player real reinforcements — no new loss plumbing.

### How it works

**Force model (from `Game.finish_turn`, in order: the §35 trail top-up → ambient convoys):**

- `ensure_ambient_convoys` (`game/retlab/ambient_convoys.py`) — both sides, the randomized top-up
  described above. Reuses the §35 coalition-generic helpers `_reference_points` + `_skim_units` (skim-only —
  it does **not** call `_seed_trail_source`, so no free units are commissioned) with its own
  `_same_side_corridors` enumeration; `AMBIENT_CONVOY_UNITS` (8) per column. The dice live in a module-level
  `_RNG` so tests script them.

### Files & tests

| Area | Path |
|---|---|
| Force model | `game/retlab/ambient_convoys.py` (`ensure_ambient_convoys`, both sides), hooked in `game/game.py` `finish_turn` |
| Settings | `game/settings/` (`ambient_supply_convoys`, Mission Generation → Battlefield life, default **ON**) |
| Tests | `tests/retlab/test_ambient_convoys.py` (the randomized both-sides top-up, same-road stacking, corridor orientation, COIN kit, every guard, the batch-2 red roads); `tests/retlab/test_blue_road_inventory.py` (the `ROAD_BEARING_CAMPAIGNS` inventory guard) |

### Gotchas / deferred

- **A blue→blue supply road is the hard prerequisite for the blue half** (found by the 2026-07-05 flown
  test): with an all-red supply graph no blue convoy can ever
  exist. Both COIN campaigns originally shipped exactly that way; their blue rear corridors are
  geo-authored (`tools/supply_route_geo.py`: ER Kandahar↔Camp Bastion up Highway 1 — the literal
  ambush alley; IR Baghdad↔Balad + Baghdad↔Al-Taquddum). The **2026-07-06 standardization survey** loaded
  all 67 shipping campaigns: **27 bound a blue→blue road** natively, and the **same-day batch-1
  corridor-authoring pass** (`BATCH1_BLUE_REAR` in `tools/supply_route_geo.py` — every route a real
  highway traced by lat/lon per the driveable-corridor standard, spliced into the campaign yamls and
  headless-verified to bind its intended blue pair) **added 21 more** across ten maps: the Tbilisi
  Kakheti-Highway hop (TblisiGap, Vectron's Claw), west Georgia's E60/S2 (Battle4Georgia,
  Kutaisi2Vaziani), Anapa↔Novorossiysk (Slava Ukraini), the Turkish O-52/E91 rear (Long Road to H3,
  Syria full map, Aleppo Insurgency, Battle4SyriaNorth), the H4↔H3 pipeline highway (Task Force
  Thunder), US-95 (Battle4area51), the UAE E11 (Noisy Cricket ×2, Scenic Merge), Israel's route 40
  (Gazelle) + the Egyptian Delta (Red Sea Rising), the Baghdad ring (Desert Aladeen), Highway 1
  Kandahar↔Bastion (Shattered Dagger), Guam's Marine Corps Drive (Velvet Thunder — the red-side §35
  no-op there is unchanged), the New Forest A-roads (Final Countdown 2), and the Swedish/Norwegian
  E10/E45/E6 chain (Anvil of War). **48 of 67 campaigns** now field the feature; the remaining **19 are
  genuine no-ops** (0–1 blue land control points, or a blue pair separated by sea/strait — the Falklands
  set, Peace Spring's Cyprus rear, Abu Dhabi/PG-Wargames' Hormuz split, Caen-to-Evreux's Channel — plus
  Caucasus_Multi_Russia and Syrian Shield, whose only blue pairs would need a corridor through the red
  heartland, deferred as a judgment call). All 48 are CI-locked as `ROAD_BEARING_CAMPAIGNS`
  (`tests/retlab/test_blue_road_inventory.py`: `test_road_bearing_campaign_keeps_its_blue_road` loads each theater;
  `test_batch1_corridor_campaigns_are_in_the_inventory` keeps the tool and the inventory in lockstep),
  so a laydown edit can't silently drop a road; when a new corridor is authored, ADD the campaign to
  the inventory.
- **A red→red road is the same prerequisite for the red half** — no red road, no red ambient convoys, and
  no columns for the player to interdict. The **batch-2 pass (2026-07-07, `BATCH2_RED_REAR` in the tool)**
  authored red rear corridors for the **nine campaigns** whose red side had none: the Aleppo belt
  (Aleppo↔Kuweires↔Jirah + the M5/Azaz legs) for WRL Aleppo Insurgency and Battle4SyriaNorth (which also
  gets its Turkish FOB line E91/O-52 chain), the Iranian mainland highways (Bandar Abbas↔Kerman via
  Sirjan, Bandar Abbas↔Shiraz via Lar/Jahrom, Shiraz↔Bushehr via Kazerun) for both Noisy Crickets,
  Cyprus's A1/A2/A5 motorways for Aegean Aegis, the Calais N43/E40 for Operation Dynamo (the tool's first
  TheChannel terrain), the **Enduring Resolve ratline reused verbatim** for Shattered Dagger (same
  laydown — ER is its fork; minus the blue Kandahar↔Bastion entry batch 1 already gave it), Saipan's
  Middle Road + Tinian's Broadway for Velvet Thunder (island-internal — so the §35 "no red trail" note
  there softens: red convoys now exist per island), and the Guam road — red-owned there — for Pacific
  Repartee. All headless-verified to bind; guarded by `test_batch2_campaign_keeps_its_red_road`
  (parametrized straight off the tool table). After both batches, **every campaign fields at least one
  side's convoys** except the few with no two same-side land bases anywhere.
- **In-game pass: checklist S5.** The ambient layer's read (columns on both sides' roads, counts
  varying turn to turn, each column driving its road) needs a flown pass with **Disable land convoys**
  unticked.

### A base is never its own corridor (the 2026-08-24 turn-pass crash)

`_top_up_side` picked `Tiyas -> Tiyas` and `Game.finish_turn` died on
`IndexError: list index out of range` at `transfers.py` `arrange_transport`'s `path[0]`. The campaign
could not pass a turn at all, from any save that reached the state.

**Why the pair existed.** `MizCampaignLoader.add_supply_routes` maps a path group's first and last
waypoint to `closest_control_point` *independently*, so a single-waypoint group — or a road drawn back
onto its own field — resolves both ends to one base and links it to itself. `operation_syrian_shield.miz`
ships both shapes: the one-point group `Suelo-5` (Tiyas) and a 38-waypoint loop (Palmyra).

**Why it is fatal rather than cosmetic.** `TransitNetwork.shortest_path_between` raises `NoPathError`
for a *disconnected* pair — loud, and `disband_uncompletable_transfers` screens for it — but returns an
**empty list** for a base-to-itself query, because the reconstruction loop exits before appending
anything. `arrange_transport` indexes that unguarded.

**Fixed at both ends.**

- `MizCampaignLoader._binds_one_control_point` warns and skips any route or lane whose two ends resolve
  to one control point, at all four creation sites (miz + yaml, supply routes + shipping lanes). This
  matches the `< 2 waypoints` warn-and-skip the yaml paths already did, and also stops the self-entry
  inflating `connected_points`, which the ground planner counts. Measured over the 73 shipped campaigns:
  4 carried one (Syrian Shield's Palmyra + Tiyas as convoy routes; Allied Sword's FOB Samandag and
  Scenic Route / Scenic Merge's Havadarya as shipping lanes — all stray single-point groups, no real
  connection lost), 0 after.
- `_same_side_corridors` (§50) and `_pick_trail_corridor` (§35) skip `other is cp`. The loader guard does
  not reach an existing save: the theater graph is pickled, so a save built before the fix keeps its
  self-link and needs the caller guard to pass a turn.

**Not carved upstream as an `arrange_transport` guard.** Upstream's own two `new_transfer` callers cannot
produce `origin == destination` — `TransferDestinationComboBox` filters `cp != origin`, and
`groundunitorders` routes a same-CP purchase into `bought_units` instead of a transfer — so the empty-path
index is latent there, and a defensive guard has no reproducible upstream failure behind it. The **loader**
half is the real upstream defect (upstream code, upstream-shipped campaign) and is the carve candidate.

Tests: `tests/campaignloader/test_self_binding_supply_route.py` (the loader guard, 3 of 5 fail unpatched),
plus the corridor guards and the empty-path contract pin in `test_ambient_convoys.py` /
`test_vietnam_convoy.py`.

### The convoy ambush — REMOVED (2026-10-11)

**Removed 2026-10-11 (DM call).** From 2026-07-05 this section's other half rolled each blue convoy
for hidden red ambush teams on its road: `map_hidden` ground objects seeded at the turn boundary,
dug in weapons-hold, and sprung by a DCS trigger when the convoy drove into a zone on them.

**Why it went:** the DM flies with **Disable land convoys** ticked, so no convoy was ever in a
mission for a team to spring on. What the feature did in practice, measured on a 2026-10-11 Iraq
save: three teams seeded 2.6 to 6.1 miles from blue bases, generated with no options (weapons-free,
no trigger), shown on the map by the fog reveal, and named in the load-time placement box. #1225
fixed those faults the same day; the removal followed.

**What went:** `game/retlab/convoy_ambush.py`, `game/missiongenerator/convoyambushgenerator.py`, the
`convoy_ambush` setting and its seven campaign presets, `Game.convoy_ambush_state`,
`coin.ambush_unit_types`, and the `map_hidden` flag with every guard that read it (the visibility
layer, both planners, the carrier strike, cruise raids, the DTC rings, the pre-turn brief). `HIDDEN`
is now reached only by an enemy command post nobody has found.

**Old saves:** `Migrator._remove_convoy_ambush_teams` deletes any team still in the save, and the
`convoy_ambush` key joins the settings migration's obsolete-key sweep.

**Constraints learned, kept for whoever builds the next thing on a road:**

- **A feature that needs another group in the mission must gate on whatever can leave that group
  out.** The ambush checked its own setting and never `perf_disable_convoys`.
- **A unit that is only safe once a generator has configured it is unsafe whenever that generator
  returns early.** The teams were ordinary red groups until `_dig_in` ran, and three early returns
  skipped it.
- **A team owned by the nearest red base, however far, is indistinguishable from a mis-bound
  campaign marker.** `ground_objects_beside_an_enemy_base` still skips `coin_spawned` objects for
  that reason.
- **A fraction of the road is not a distance.** `ROUTE_END_MARGIN` (15 %) put a team 0.4 NM from a
  base on a 3 NM road; 21 of 98 blue roads could host one inside a 1.6 NM capture circle.
- **Light kit, capped.** A flown Red Tide test (2026-07-09) called MBT teams in the backline
  excessive; a rear-area raid is gun-trucks and riflemen, four per team, four teams theater-wide.

## §51 — Enemy comms jamming (IADS comms nodes) — REMOVED (2026-09-07)

The `commsjam` plugin, `commsjamluadata.py`, the `enemy_comms_jamming` setting, the JAM
BACKUP kneeboard line and both campaign preseeds are deleted.

What it was: every alive enemy comms / command-center node transmitted duty-cycled barrage
noise on a rotating subset of BLUE's briefed channels, via `trigger.action.radioTransmission`
from the node's map position, so DCS's own power/distance falloff made it worst near the C2
belt. Audio pressure only — no force-model change; the strike that silenced it was the
ordinary IADS strike.

Constraints kept out of the deleted design note:

- **GUARD and ATC were never jammed.** Anything that transmits on a player's briefed channels
  keeps that positive-list rule — stepping on 243.0 is not a game mechanic.
- **No SRS dependency is needed.** SRS tunes off the cockpit radios, so the in-game radio path
  already reaches SRS users. Injecting into the SRS network needs a server-side install and a
  process per transmission, and buys nothing. §70's net was built on the same finding.

The intel gate that made jamming conditional on a captured aircrew's comms plan died earlier,
with §21 on 2026-08-07. In git history at
`git show c08b85de2:docs/dev/design/414th-comms-jam-notes.md`.

## §52 — Command-center decapitation degrades enemy planning

**The campaign-layer complement to §51.** §51 gave the IADS **comms** node a runtime voice; this gives
its **command center** sibling a *turn-model* consequence. A command center
(`category == "commandcenter"`, `IadsRole.COMMAND_CENTER`) had gameplay only inside the IADS engine's runtime
SAM-autonomy graph — killing it made SAMs go autonomous, but red's **planning** was untouched, so
"bomb the enemy HQ" was a strike checkbox, not a strategic move. Now a side's auto-planner quality is
coupled to its own command-network health.

### How it works

`game/retlab/c2_decapitation.py`:

- `_command_centers(coalition, theater, viewer=None)` → `(alive, total)` command-center TGOs on the
  coalition's own bases (a CC is alive while any of its units is alive — the same test the IADS emitter
  uses). With a `viewer`, posts hidden from that side's map are skipped; the planner never passes one.
- `c2_health` → the alive fraction (1.0 when the side fields no command centers — a C2-less campaign is
  unaffected).
- `unpredictability_bonus(coalition, theater, settings)` → `round((1 − health) × MAX_DECAP_UNPREDICTABILITY)`
  (60 pts at full decapitation), or **0** when the feature is off or the network is intact.

The bonus is read at plan time in `game/commander/tasks/targetorder.py` `_unpredictability_for`, added
on top of the side's base `*_planner_unpredictability` (§17) and clamped to the shuffler's 0–100 domain.
So as a side's HQs die, `shuffled_by_priority` progressively loosens its **opportunistic offensive**
target order — it services lower-priority strikes/OCA/BAI/anti-ship it wouldn't have before, and hits
the same things less reliably turn to turn.

### The §17 boundary (inviolable)

Only the offensive/opportunistic tiers pass through `shuffled_by_priority`; **reactive defensive tasking
stays strictly deterministic**. A decapitated enemy still defends itself — it just plans worse *offense*.
This is the same boundary §17 (auto-planner unpredictability) established; §52 rides the exact same lever,
just sourced from C2 health instead of a static slider.

### Legibility

The effect lands on the *enemy's* next turn, so the player is told the strike worked. `c2_status_line`
builds "1/3 known command posts operational" for three surfaces: the SITREP band line
(`Sitrep.red_c2_status` → "Enemy C2 degraded: …"), the map ribbon's C2 chip (`red_c2` in
`game/server/game/models.py`, rendered by `CampaignStatusBar.tsx`) and the pre-turn brief's
consequence item. The SITREP line **rides along with the other real news** — it never forces a SITREP
onto an otherwise-quiet turn (`is_empty` ignores it).

**The line counts only the posts on BLUE's map (2026-09-22).** With `scar_command_post_intel` on, an
enemy command post is hidden until found, and the old line counted every post over ground truth, so
the "/3" told the player how many hidden posts existed. `c2_status_line` now passes
`viewer=Player.BLUE`, and `_command_centers` skips any post `fogofwar.hidden_from` reports — never a
bare `hidden_on_player_map`, so the reveal overview cannot change the count.

- **A hidden post is left out of both numbers, dead or alive.** A hidden post that died was never on
  the player's map, so counting it as dead would leak it just as the total did. If the only dead post
  is a hidden one, the line is None.
- **`c2_health` stays on ground truth.** The planner effect still counts every post, hidden or not
  (AI planning always reads truth), so the line can read intact while red's planning is degraded.
- **"(claimed)" was dropped** from the SITREP line, the brief and the chip's hover text. It referred to
  the BDA lag, removed 2026-08-18; the count is now exact for every post the player can see.
- **The pre-turn brief read the wrong side until 2026-09-22.** `_consequence_items` passed
  `game.blue.player`, so it reported the player's own command posts as "Enemy C2 degraded". It now
  passes `game.red.player`, and its test pins the argument.

### Files & tests

| Area | Path |
|---|---|
| Core | `game/retlab/c2_decapitation.py` (`c2_health`, `unpredictability_bonus`, `offensive_package_cap`, `c2_status_line`) |
| Planner hooks | `game/commander/tasks/targetorder.py` `_unpredictability_for` (adds the bonus, clamps to 100); `game/commander/tasks/compound/nextaction.py` `_offensive_tempo_exhausted` (the A2 throttle gate on the offensive middle) |
| Legibility | `game/sitrep.py` (`red_c2_status`), `game/sim/missionresultsprocessor.py` `record_sitrep`, `game/server/game/models.py` (`red_c2`), `client/src/components/campaignstatus/CampaignStatusBar.tsx`, `game/retlab/pre_turn_briefing.py` `_consequence_items` |
| Setting | `game/settings/` (`c2_decapitation_effects`, Air Doctrine, default **OFF**) |
| Tests | `tests/retlab/test_c2_decapitation.py` (health/bonus/status/gates, hidden posts excluded from the line but counted by `c2_health`, the overview cannot change the line, + the A2 cap math and HTN gating); `tests/test_planner_unpredictability.py` (the shuffler coupling + intact/off determinism); `tests/test_sitrep.py` (the band line, rides-along); `tests/retlab/test_pre_turn_briefing.py` (the brief asks for red's network) |

### Gotchas / deferred

- **The runtime half was silently dead until 2026-08-19, and §52 was masking it.** The engine's
  C2 layer degrades SAMs whose comms/power node dies and decapitates a coalition that loses
  every command centre — but `IadsNetwork.iads_nodes` dropped any node or connection whose
  units were all dead, so from the *next* turn the dependency was simply absent from the
  exported graph and the runtime had nothing to watch. A bombed power station's SAMs came
  back fully operational, and killing every command centre restored perfect command instead
  of removing it. Dead C2 nodes and edges now stay in the graph, and a per-coalition
  `DeadC2` array names what the runtime cannot see for itself (a scenery node has no static
  to look up, and `dead_events` only records the current mission). Found by
  juanjux/dcs-retribution#97 against Skynet; see
  [retlab-juanjux-fork-watch-notes.md](design/retlab-juanjux-fork-watch-notes.md).
- **Pure turn-model.** No `.miz`, no Lua, no DCS integration — zero runtime risk. It reuses the §17
  shuffler wholesale, so at full C2 health (or feature off) the planner is byte-identical to today and all
  existing determinism tests hold.
- **Symmetric in code, red in practice.** Each side reads its own C2 health, but only a side with an HTN
  auto-planner (red, in a normal player-vs-AI game) is affected by the player's strikes. Blue's own
  auto-planned (AI-filled) slots would loosen too if the player let blue HQs die — intended and fair.
- **Phase A2 LANDED (2026-07-17) — the offensive package-count throttle.** The design note's second lever
  is in: `offensive_package_cap` shrinks a side's offensive package ceiling linearly with its dead
  command-center fraction, from `FULL_OFFENSIVE_PACKAGE_CAP` (12 — above what the HTN typically frags, so a
  barely-scratched network rarely bites) to the `MIN_OFFENSIVE_PACKAGES` floor (2 — the design's "never
  zero red out" guardrail). `PlanNextAction._offensive_tempo_exhausted` counts the coalition's planned
  packages whose primary task is in `_OFFENSIVE_PACKAGE_TYPES` (Strike/BAI/OCA/anti-ship/air
  assault/armed recon — deliberately excluding CAS and SEAD/DEAD, which are planned defensively too) and
  stops offering the offensive middle once the cap is reached: trimming, not reordering. The reactive
  prefix (TheaterSupport/ProtectAirSpace/DefendBases) and the recovery tail are never throttled (the §17
  boundary), and None (feature off / intact network / no CCs) is byte-identical to A1-only behaviour.
- **Preseeded on Red Tide (2026-07-07).** Default OFF everywhere; **Germany — Red Tide** flips it ON
  (`c2_decapitation_effects: true`) because its advanced-IADS build is one of the very few laydowns with a
  real, per-base **destroyable command-center network** (9 red Command Center cells) for §52 to key on —
  see the Red Tide design note. The B6 in-game pass now rides on that campaign.
- **NEW game not required** (no persisted state; C2 health is measured live each turn).

---

## §53 — War economy — REMOVED (2026-07-21)

Removed with §48 and §54 in the economy drop. Do not restore.
`414th-war-economy-notes.md` was deleted 2026-08-20, recoverable from git before `5db34150f`.

## §54 — Munitions availability — REMOVED (2026-07-21)

Removed with the war economy (§53). Do not restore.

## §55 — Red Intent — adaptive enemy posture — REMOVED (2026-07-21)

Removed. **Read this before proposing anything that makes red "smarter"**: §55 already tried
the obvious shape and it did not survive contact. Seam 7 of
`retlab-retribution-long-view.md` is where that conversation belongs.

## §56 — Strikeable motorpool depots

**Adopted from upstream PR [dcs-retribution#859](https://github.com/dcs-retribution/dcs-retribution/pull/859)**
(geofffranks, "Strikeable motorpool depots", closes upstream #655). Cherry-picked onto the fork
verbatim (4 commits, Geoff retained as author) plus one fork-adaptation commit; the Pretense hunk was
dropped because the fork has no Pretense. This is an *upstream-authored* capability given a RetLab §N
so it rides the same registry/checklist discipline as the fork's own features — not a RetLab-original.

### What it does

Retribution's ground war holds a **reserve**: `GroundPlanner.plan_groundwar` sends only a slice of a
control point's `base.armor` to the front (proportional to `frontline_unit_count_limit`, and *nothing*
from a CP with no connected enemy). The rest sat purely as an economy number — you could only attrit it
by meeting it at the FLOT after it deployed. This projects that **not-yet-deployed reserve** as a
**strikeable motor pool** at the CP, so a player can bomb the depot and thin the enemy's armor reserve
directly.

### Shape (Python-only; no Lua plugin)

- **`MotorpoolGroundObject`** (`game/theater/theatergroundobject.py`, category `"motorpool"`) — a
  maintenance-facility map symbol (`LandInstallationEntity.MAINTENANCE_FACILITY`), visually distinct
  from an armor group. `sidc_status` is pinned **`PRESENT`** — an empty depot is its normal resting
  state (its vehicles are a projection of the reserve, reconciled by `MotorpoolPopulator`), never
  rendered damaged/destroyed; `is_dead` is
  left intact so AI target-selection/capture/IADS logic is unaffected. `capturable`/`purchasable`/
  `should_head_to_conflict` are all `False`; `mission_types` offers **BAI** to the opponent.
- **Placement** — gated on an authored `Fortification.Garage_A` static (`MizCampaignLoader.motorpools`
  → `PresetLocations.motorpools`), materialised by `start_generator.generate_motorpools` (new games)
  and injected on load by `migrator._ensure_motorpool_tgos` (existing saves). **Red Tide authors one**
  (2026-07-08) — a `Garage_A` ~4 km NE of **Haina**, the forward Soviet base at the Fulda Gap, so the
  feature is exercised on the fork's flagship armor campaign ("bomb the motor pool before its armor
  reaches the front"). Headless-verified through the real `GameGenerator` pipeline: the static binds to
  Haina (RED) and materialises exactly one `MotorpoolGroundObject` (CI-locked in
  `tests/retlab/test_red_tide_motorpool.py`). Every other campaign is **inert until it places a
  `Garage_A`** — it changes nothing until a depot is authored.
- **A crowded package label used to walk off its own marker (fixed 2026-08-22).** `free_slot`
  stepped a label down the page until it found clear space, bounded only by the map edge, and
  nothing drew a leader line — so on a dense cluster a name landed beside an unrelated airfield
  and read as belonging to it. Measured on a Syria BAI turn: `KOMODO` **166 px** from its dot,
  `STAGHORN` 76. `MAX_LABEL_OFFSET` (90 px) bounds the walk and `LEADER_AT` (22 px) draws the
  line home past that gap; all 12 labels still place, worst drift 166 px → 110. **The fixture's
  surrounding bases are load-bearing** — with no control points every label places on its first
  try and the case proves nothing, which is how the first version of the guard test passed
  against the defect. The leader ends at the label's **near** edge and stops 3 px short: drawing
  to the far edge runs the line through the text, and "H3 Northwest" rendered as
  "H3-Northwest" when its label sat left of its marker.
- **The kneeboard briefed a dead sortie type until 2026-08-22.** Every unidentified-site
  row on the Threat Intel page read "Fly TARPS to ID." — a procedure the 2026-08-18 rework
  removed, and one the page's own intro contradicted ("engage them to ID"). It now reads
  "Engage to ID.", and the test that had been pinning the stale string asserts the opposite.
  The COIN HVT checklist row (P5) carried the same instruction and was corrected with it.
- **Two defects in the BLUF ordnance line, both found on a flown F-16CM BAI card (2026-08-22).**
  `_brief_loadout` took `weapon_group.name` in preference to `weapon.name`, but an unnamed
  group's placeholder is the literal string `"Unknown"` — truthy, so it won the `or` and was
  then dropped by the `name == "Unknown"` guard. **Both 370 gal tanks vanished** while the fuel
  ladder counted them, so the card briefed 7,163 lb of stores against a 12,121 lb ladder. And a
  rack multiplier was stripped off the name (`"2xMk 82"` → `"Mk 82"`) and discarded rather than
  applied to the count, so **a TER carrying two bombs briefed as one**. The line went from
  `2× AIM-120B · 2× AIM-9M · Mk 82 · CBU-97 · HTS` to
  `2× AIM-120B · 2× AIM-9M · 2× CBU-97 · 2× bag · 2× Mk 82 · HTS`. Pinned in
  `tests/missiongenerator/test_kneeboard_bluf.py` against that jet's exact pylons.
- **Two placement guards, opposite mistakes.** `motorpools_inside_capture_zone` catches a marker
  inside its own CP's 3 km capture radius (parked reserve blocks the base being taken).
  `ground_objects_beside_an_enemy_base` (added 2026-08-20) catches **any** authored ground object
  parked on a hostile CP's doorstep; COIN teams spawned at a turn boundary (`coin_spawned`)
  are skipped since 2026-10-11. Both warn from `QLiberationWindow._warn_motorpool_capture_zone` at
  generation and on save load; neither moves anything, because the marker is the author's call.
- **The doorstep guard is about marker BINDING, not authoring.**
  `MizCampaignLoader.objective_info` binds by influence *zone*: a point inside an authored zone
  joins that CP, and a point inside none falls back to the closest CP **that has no zone at all**.
  **Fixed 2026-08-20 for blue-block markers.** A blue-block group is an explicit ownership
  declaration, so its blue preference is now evaluated against every eligible CP rather than only
  the unzoned fallback list, and motorpools joined the marker classes that pass `prefer_blue`.
  `operation_vectrons_claw` had a blue-block `Garage_A` **617 m** outside the blue UNOMIG FOB's
  6096 m zone; it bound RED Sukhumi-Babushara **75 km** away and spawned a red motorpool beside a
  blue base. Measured across 12 campaigns and 1402 marker bindings, that change moves **exactly
  one** binding — the defect itself. `BLUE_BLOCK_MAX_DETOUR` still bounds the preference.
- **Red-block markers get no blue preference,** and that stays true. The red block is the
  coalition-agnostic default and binds by proximity; letting *it* use the blue-ownership
  preference was measured and rejected (24 of 751 markers rebind, 16 across coalitions, and all
  13 of Velvet Thunder's red air defenses move onto neutral FOBs).
- **The fallback itself now rescues a stranded marker (2026-08-22), block-agnostic.**
  `ADOPT_ZONED_WITHIN` (25 km) and `STRANDED_BEYOND` (50 km): the nearest **zoned** CP adopts a
  marker when it is within 25 km *and* the unzoned fallback would otherwise put the marker more
  than 50 km from its owner. Both bounds are load-bearing and each has a test that fails without
  it. **Measured across every campaign: 16 of 7653 bindings move, and not one ends up farther
  from its owner** — old distances 53–142 km become 9–25 km, improvements of 2.7×–11.9×.
  `operation_desert_trident`'s doorstep warning goes from 7 objects to 0.
  - **The near bound stops the rule claiming a marker in open country.** Without it a zoned
    field adopts anything it happens to be nearest to.
  - **The far bound is what separates a rescue from a reshuffle,** and it was added after
    measuring. Proximity alone moves 40 bindings, 14 of them Velvet Thunder markers hopping
    between neighbouring fields already 2.2–12.4 km away — churn in a campaign with nothing
    wrong with it, and the same outcome the blue-preference widening was rejected for.
  - Set `ADOPT_ZONED_WITHIN = None` to restore the pre-2026-08-22 unzoned-only fallback.
- **Two conditions, because either alone cries wolf:** nearer a hostile CP than its own owner (the
  mis-binding signature) **and** within `BESIDE_AN_ENEMY_BASE` (25 km) of it (the part a player
  sees). The same campaign has SKUNK 107 km from its parent but ringed by friendly fields, and
  CROCODILE/ELEPHANT/STINKBUG nearer a hostile CP but 32–107 km out in open country. None of those
  is a problem, and flagging them would train the reader to dismiss the box.
- **Population** — `MotorpoolPopulator` (`game/missiongenerator/motorpoolpopulator.py`), run once per
  mission-gen before the TGO generator, rebuilds each motorpool's vehicle groups from the CP's current
  reserve slice. `ai_ground_planner.reserve_armor_for` computes the reserve as *exactly*
  `base.armor − deployable_armor` (a `plan_groundwar`-faithful duplicate — deliberately not refactored
  to share, since `plan_groundwar` has no tests on this base), capped by `motorpool_spawn_cap`
  (largest-remainder proportional trim). Multiple motorpools on one CP round-robin the **single** shared
  reserve pool (never each render it in full, which would double-decrement `base.armor` on a strike). The
  populated groups and `motorpool_projection_keys` are a **persisted cache** on the TGO, reconciled
  on every `populate()`: an unchanged reserve keeps the same groups and unit ids. A flight plan aimed
  at a depot keeps its hand edits at Take Off; only its unit snapshot is swapped (#1205).
- **Rendering** — `MotorpoolGenerator` (`game/missiongenerator/motorpoolgenerator.py`, a
  `GroundObjectGenerator` subclass) lays the vehicles in a grid (so DCS doesn't drop overlapping spawns),
  **weapon-hold + alarm-green + `player_can_drive=False` + no EPLRS** (parked, unmanned, no datalink),
  plus an inert `Garage_A` depot static offset clear of the grid. Vehicles register into
  `UnitMap.motorpool_units` (a distinct registry), **not** as theater objects — so a theater-object
  death never touches `base.armor`.

### 1:1 grind, no economy, no front shift

A killed reserve vehicle is a **distinct loss category** end-to-end: `Debriefing.dead_ground_units`
buckets it into `player_/enemy_motorpool` (via `unit_map.motorpool_unit`), and
`missionresultsprocessor.commit_motorpool_losses` decrements `base.armor[unit_type]` by one. Because it
is *not* a front-line loss, it feeds neither `casualty_count` nor `commit_front_line_battle_impact` —
**a depot strike forces a repurchase next turn but never moves the front line**. Losses surface on the
debrief (the "Motorpool units lost" faction row + per-type "`<type>` from motorpool" rows).

### Settings & fork interactions

- Gated `motorpool_enabled` (**Campaign Management → Campaign features**, default **ON**) +
  `motorpool_spawn_cap` (default 10, 0–25 — a perf lever). Both registered in the §28 `FIELD_LAYOUT`.
- **§3 recon fog** leaves a motorpool an **exact** marker — category `motorpool` isn't in the
  concealable set (`game/server/tgos/models.py` conceals only armor/missile/concealable-SAM), so the
  depot reads like an ammo depot/building, not a dashed "suspected activity" circle. Sensible: you see
  the depot and strike it.
- **Not supported in Pretense** (no loss reconciliation there) — the fork has no Pretense, so this is
  moot here; the upstream skip hunk was dropped.

### Fork-adaptation notes (vs the upstream PR)

Two fork-only changes on top of the verbatim cherry-picks: the two new settings were registered in the
fork's `FIELD_LAYOUT` (§28 requires every user setting listed exactly once), and the loss-separation
test's fake front-line group gained a `.name` (the fork's `add_front_line_units` also records the group
by name for TIC clones, §9). All conflicts were keep-both adjacent insertions (settings block, unitmap
registries, `ai_ground_planner` helpers, the two save-compat tombstones + `MotorpoolGroundObject`,
`test_debriefing`).

Tests: the PR's suite (`tests/**/test_motorpool_*.py`, `tests/ground_forces/test_reserve_armor.py`,
`tests/campaignloader/test_motorpool_recognition.py`) rides along, plus
`tests/retlab/test_red_tide_motorpool.py` locking the authored Haina depot. **In-game pass** =
checklist B8 — fly **Red Tide** (the depot renders at Haina immediately; its parked vehicles appear
once red has procured armor, a couple of turns in, since `base.armor` is empty at turn 0 by design)
to exercise the map icon, in-mission depot + parked vehicles, the strike→decrement→repurchase grind,
the no-front-shift guarantee, and the debrief rows.

### Upstream drift sync (2026-07-16)

The #859 branch kept moving after the fork's adoption; the drift was ported back:

- **Rotation fix** (upstream `401fbceda`, cherry-picked) — the parking grid and the depot's
  opposite-corner offset now rotate about the TGO origin by the authored `Garage_A` heading, so a
  non-cardinal garage no longer produces angled vehicles in a world-axis grid. Heading 0 is a no-op.
- **Capture-zone warnings** (upstream `b17e530e3` + `042d883de`, cherry-pick + hand-applied
  `QLiberationWindow` half) — parked motorpool vehicles are live ground units that block DCS's
  `AllOfCoalitionOutsideZone` capture trigger, so a depot inside the CP's 3 km capture zone makes the
  base uncapturable by ground assault. `warn_if_motorpool_inside_capture_zone` logs at both
  TGO-creation sites (`start_generator.generate_motorpools` + `migrator._ensure_motorpool_tgos`), and
  `motorpools_inside_capture_zone`/`MotorpoolCaptureViolation` back a deferred modal `QMessageBox`
  from `QLiberationWindow` on both activation paths (`onGameGenerated` + the load-game dialog), gated
  on `motorpool_enabled`. Warn-only, never relocates. **Red Tide's Haina depot is at 4,250 m** —
  outside the 3,000 m zone, so the campaign stays silent.
- **Rename** (upstream `60aa41e2f`, cherry-picked) — `_passivate` → `_set_passive`.
- **Spawn-cap ceiling ADAPTED, not verbatim** (from upstream `f09e03f86`) — upstream raised the
  default 10 → 25 AND lowered the spinner max 50 → 25; the fork adopts **only the max 50 → 25** and
  **deliberately keeps default=10** (the MP performance posture — the TIC dense-siege framerate
  history; §59, removed 2026-09-23, existed for the same reason). The migrator backfill stays at 10.
- **The autoplanner landed after all** — upstream `2697cd0f` (the HTN strikes enemy motorpool
  reserves) was deferred here while it collided with the §40 phase / §55 red-intent
  offensive-emphasis machinery; both were removed 2026-07-21, and the 2026-07-19 sync brought the
  `AttackMotorpools` compound task + `PlanMotorpoolAttack` in, wired into the fork's offensive
  lists. BAI is the doctrinal primary with STRIKE as the fallback, and the package is sized off
  the live reserve pool (`reserve_armor_for`) rather than the stale `alive_unit_count`. **Replaced 2026-10-06 by #961:** Armed Recon from `AttackBattlePositions`; see the drift sync below.

### Upstream drift sync (2026-07-26)

Upstream [#899](https://github.com/dcs-retribution/dcs-retribution/pull/899) (geofffranks +
Druss99) and [#895](https://github.com/dcs-retribution/dcs-retribution/pull/895) (Druss99)
reworked placement and closed a planning hole. **The fork adopts upstream's shape** — our
motorpool modules were byte-identical to the adoption baseline, so these apply cleanly:

- **The `Garage_A` marker IS the anchor now.** The depot static was previously offset into the
  *opposite* local corner from the vehicle grid (`_DEPOT_OFFSET_M = 50`, rotated about the origin)
  so the two could never share a spawn point. Upstream inverted it: the depot renders **exactly at
  the authored marker** (`position=self.ground_object.position`) and the **grid** moves clear
  instead, starting at `_GRID_OFFSET_M = 45.72` m (150 ft — an authoring-friendly round number)
  in the building's local +x/+y corner and still following its heading. The practical win is
  authoring fidelity: what the campaign author places in the ME is where the garage appears, so
  the depot no longer drifts ~70 m diagonally off its marker. `_DEPOT_OFFSET_M` is gone.
- **An empty reserve pool is no longer a plannable target.** `PlanMotorpoolAttack.preconditions_met`
  now bails on `_rendered_unit_count() <= 0`, so the HTN stops fragging BAI/Strike packages at a
  depot with nothing parked in it. This matters on the fork specifically because `base.armor` is
  empty at turn 0 by design — every campaign with an authored depot was offering the planner a
  guaranteed-empty target on the opening turns.
- **The capture-zone warning names the distance in nm** ("approximately 2 nm (… meter) capture
  zone"), since `TRIGGER_RADIUS_CAPTURE` in metres told an author nothing actionable. Red Tide's
  Haina depot at 4,250 m stays outside it and silent.

`_GRID_OFFSET_M` shifts every depot's parked vehicles relative to saves generated before this. No
save migration was added. Since #959 the groups are a persisted cache: a vehicle kept by a reconcile
keeps its saved position, and only vehicles a reconcile adds use the current offset. Checklist B8 still owns the in-game pass and
should now also confirm the garage lands on its authored marker.

### Upstream drift sync (2026-10-06) — the #926 split

Geoff split his closed [#926](https://github.com/dcs-retribution/dcs-retribution/pull/926) into
five PRs, all open upstream, none merged. The fork adopts them one RetLab PR at a time, his
commits cherry-picked with him as author. **They are open PRs: re-sync if he changes them.**

- **[#960](https://github.com/dcs-retribution/dcs-retribution/pull/960) re-homing.**
  `MotorpoolPopulator._rehome_motorpools` attaches every depot to the nearest land control
  point (FARPs and FOBs included; carriers, LHAs and off-map points never), on every load and
  on every `ControlPoint.capture`, and once at the end of New Game (`GameGenerator.generate`,
  2026-10-11) so a depot's owner does not change on the first load. A depot used to stay
  with whoever owned it at New Game.
  Authored-marker identity (`motorpool_identity`: name, x, y, heading) drops depots whose
  marker left the campaign and de-duplicates a save that listed one twice. A load re-homes
  depots only; it does not repopulate them.
  - **Fork interaction:** it runs after `_ensure_motorpool_tgos` and after New Game's
    `generate_motorpools` (which both bind through the loader's blue-preference and
    stranded-marker rules) and overrides that owner with the nearest land CP. The loader's binding still decides which side's warning fires.
  - Row B180.
- **[#959](https://github.com/dcs-retribution/dcs-retribution/pull/959) inventory.**
  The populator became a projection reconciled each call: an unchanged reserve keeps the
  same groups and unit ids, so a flight plan aimed at a parked vehicle stays valid. The
  depot tooltip (`TgoTooltipContent`) lists reserve, expected next turn, unrendered reserve
  and in transit; `GameUpdateEvents.update_motorpools_at` refreshes it on every buy, sale,
  transfer and turn. An enemy depot blue has not engaged (`known: false`) lists nothing; an
  engaged one lists reserve and unrendered reserve only. Expected next turn is sent for
  blue-held depots, and in transit counts blue's transfers only. `TransferOrder` now takes its owner (`player`) and
  `PendingTransfers.new_transfer` asserts it, so the fork's convoy seeders (§35, §50) pass
  `coalition.player`.
  - **Fork decisions:** the reserve lists follow `known_for(Player.BLUE)`, the same fog as
    `units`. #959's migration-time `populate()` was dropped: #960 keeps loads free of
    generated groups and id churn, and the two PRs disagree there. The tooltip keeps the
    fork's condensed unit summary and click hint. `test_reserve_armor` reads the fork's
    `units_per_cp`, since the fork's planner has no `tank_groups`.
  - Row B181.
- **[#961](https://github.com/dcs-retribution/dcs-retribution/pull/961) auto-planner.**
  `AttackMotorpools` is gone. `AttackBattlePositions` offers `PlanMotorpoolAttack` right
  after the BAI positions and before the Armed Recon control points, and the package is
  Armed Recon plus the common escorts, not BAI or Strike. The armed recon ingress uses a
  106 m engage zone on a motorpool, so the flight works the parked grid.
  - **Fork decisions:** squashed into one commit (Geoff as author): #961's stand-in
    projection in `theatergroundobject` duplicated #959's and was dropped. Motorpools pass
    `auto_planning_skips`, so §93 Ignored regions skip them like the BAI targets beside
    them. The ingress keeps the fork's per-search-point loop and `search_zone_radius`.
  - Row B182.
- **[#962](https://github.com/dcs-retribution/dcs-retribution/pull/962) mission generation.**
  `refresh_motorpool_target_flight_plans` runs right after `MotorpoolPopulator.populate()`
  in mission generation, so plans see the vehicles actually parked. Since 2026-10-11 it
  does not re-plan: `Flight.refresh_flight_plan_targets` swaps the unit snapshot on the
  ingress and on a Strike's site waypoint, only when the parked set differs from the one
  the plan holds, so dragged and inserted waypoints survive Take Off. BAI gets one `bai_group`
  waypoint on the depot; Armed Recon one area waypoint, its engage zone centred on the
  garage and sized to a full grid plus 20 m (`motorpool_full_grid_extent_m`), replacing
  #961's 106 m. The strike ingress adds one `Bombing` per parked vehicle, re-read at
  ingress. `_set_passive` stops parked vehicles dispersing under fire.
  - **Fork decisions:** squashed into one commit (Geoff as author). A motorpool Strike keeps
    the fork's single site waypoint carrying every unit (`SITE_WAYPOINT_TASKS`), not #962's
    waypoint per vehicle; the AI still bombs each vehicle from the ingress. #962's planner
    count is #959's projection. Its armed-recon layout test was dropped: the fork's
    `ArmedReconFlightPlan` stands off and has its own tests.
  - Row B183.
- **[#958](https://github.com/dcs-retribution/dcs-retribution/pull/958) OPFOR ground forces.**
  Not motorpool itself, but split out of #926 with it. `PendingTransfers.validate_transfer`
  checks owner, origin, destination and route, and runs in `new_transfer` and in
  `TransferModel.new_transfer` before the row is inserted. `cancel_transfer` calls
  `TransferOrder.disband`, so an origin captured since the order gets nothing back. RED
  ground sales work under the buy/sell cheat (`_sale_allowed`), the cheat reads "Enable OPFOR
  Buy/Sell/Transfer Cheat", and RED's Ground Forces HQ tab needs `can_deploy_ground_units`.
  - **Fork decisions:** squashed into one commit (Geoff as author). #958 and #959 are two
    implementations of the same transfer-ownership work; #959's model stays (a hidden RED
    mutation is ignored, not raised as `PermissionError`) and #958's duplicate members were
    removed. Tests from both were fitted to the one model.
  - Row B184.

---

## §57 — Air-droppable minefields (convoy interdiction) — REMOVED (2026-09-07)

Shelved 2026-07-30, abandoned 2026-09-07. The `minefields` plugin,
`game/retlab/minefields.py`, `convoy_mining.py`, `minefieldluadata.py`, the
`minefields_state` debrief channel, the map layer and both settings are deleted.

Why it stopped: DCS has no air-droppable mine, so CBU-99 releases over a road were faked
into a mined zone that damaged convoys entering it. That works, and the fake is visible —
the cluster munition detonates normally and the mining is a separate scripted effect keyed
off the release point, so what the player sees and what the campaign records are two
different events. Thirteen months shelved settled whether it was worth fixing.

Constraint kept out of the deleted design note: the mines killed **real, tracked convoy
units** and the losses recorded natively. That is the "never spawn phantom units" rule, and
it still binds §35, §37 and §50.

Both settings are swept as obsolete keys, so an old save loads. In git history at
`git show c08b85de2:docs/dev/design/414th-minefields-notes.md`.

## §58 — Mission-start briefing popup

The professional DCS campaigns greet a pilot who slots in with a short on-screen card — campaign,
mission, time, date, callsign, field — so you always know what you are flying before you have opened
a kneeboard. This brings that to the dynamic campaign, then flashes a **second card** right after
(held the same duration): the startup/taxi instruction, `<callsign> — Get started up, Contact ground
@ 249.50 when ready to taxi` (249.50 is a fixed squadron freq — a plugin option). A **short beep
plays as each card flashes** (`outSoundForGroup` — which, unlike `outPicture*`, DOES have a per-group
variant, so the beep is per-pilot on the slot-in), from an **original** `briefing-beep.wav` bundled
with the plugin via `otherResourceFiles` — a synthesized two-blip chirp, NOT lifted from any paid
campaign (a `playSound` option mutes it). **Display only:** no gameplay-model change, no `.miz`
object, nothing persisted; the plugin owns nothing but the text (+ the one bundled sound).

**Why it is TEXT, not a styled image (a hard DCS limit).** The DCS Lua scripting API has
`outTextForGroup`/`outTextForUnit` (target one flight) but **no `outPictureForGroup`/
`outPictureForUnit`** — pictures can only be shown to *all* players or a *whole coalition*
([ED wishlist thread](https://forum.dcs.world/topic/371036-outpicturefor-lua-mission-scripting-functions/);
there are 0 `outPicture*` calls in MOOSE or any RetLab plugin, vs 31 `outTextForGroup`). So a
*per-pilot styled image card* is impossible in multiplayer — the info (callsign/task/field) differs
per flight, and only the text functions can address one flight. The pro campaigns get the image look
only because they are hand-built **single-flight** missions, where `outPicture`-to-all is that one
pilot's card (and even the best paid-campaign PNGs are *briefing-screen* images; their in-game
title is plain `outText`). Retribution missions are multi-flight, so the per-pilot card stays text.

**The Python/Lua split.** The emitter `game/missiongenerator/briefingluadata.py`
(`populate_briefing_lua`, wired into `luagenerator.py`'s `generate_plugin_data` next to the other
`populate_*` bridges) emits `dcsRetribution.briefing`:

- a shared **`header`** (the same for every flight, emitted once): `campaign` (`game.campaign_name`),
  `mission` (the **raw `game.turn`** — it reads the same number the §30 kneeboard cover shows
  ("Turn N"); `turn+1` was confusing, the card's "Mission 2" next to the kneeboard's "Turn 1". Since
  `game.turn` is 0-indexed, a brand-new campaign's first sortie reads "Mission 0" — matching the
  kneeboard SITREP's turn numbering), `date` (`game.current_day`, formatted `%A %d %B %Y`), and `time`
  (`game.conditions.start_time`, `%H:%M` + `L`). Date + clock are sourced from the same game fields the
  kneeboard uses, so the popup and the kneeboard agree. *(The popup is now the deck's only op/turn/date
  banner — the §30 cover page that used to carry one was retired 2026-07-13.)*
- a **`flights`** list — one record per **player-crewed** flight (a `FlightData` with a non-empty
  `client_units`): `group` (the `FlightData.group_name` the runtime matches on), `callsign`,
  `aircraft` (`aircraft_type.display_name`), `task` (`task_display_name`, so the Vietnam rename layer
  etc. carry through), and `airfield` (`departure.airfield_name`).

The node is emitted **only** when `mission_briefing_popup` is on **and** the mission has at least one
player-crewed flight; otherwise there is no `briefing` node and the plugin no-ops. Every field is a
**single-line string** — the Lua composes the multi-line card with real newlines, because
`escape_string_for_lua` does not escape `\n` and a literal newline inside a Lua 5.1 `"..."` literal is
a parse error. (This is why the card is *not* pre-formatted in Python.)

**The runtime (`resources/plugins/briefing/`).** `briefing-config.lua` (registered in
`plugins.json`, `defaultValue` true) builds a `group name → record` lookup and the shared header
string, then shows each pilot their own card two ways so every path to a seat is covered:

- an **`S_EVENT_BIRTH` handler** — fires whenever a pilot enters a slot (mission start in
  single-player, and any slot-in / rejoin on a server). **Players only:** `getPlayerName()` is `nil`
  for AI, so an AI birth is ignored and no AI flight is ever shown a card.
- a **one-shot mission-start sweep** after a short grace — iterates the known briefing groups and
  shows any player already seated, covering the single-player case where the player's birth fired
  *before* this script registered its handler.

The two are deduped by a small per-unit debounce (`GRACE + 5` s, comfortably above the grace so both
catch the same slotting exactly once) that is still short enough that a genuine later re-slot
re-shows the card. `trigger.action.outTextForGroup(groupId, card, DURATION, false)` shows the card to
the pilot's group; `groupId` is read live from `unit:getGroup():getID()`, so only names need
emitting. The whole sequence is delayed **`startDelayS` s (default 5) after slot-in** (a nested
`timer.scheduleFunction`) so it doesn't slam up the instant the pilot takes the seat; then the **taxi
card** (`buildTaxiCard` — the callsign + `Get started up, Contact ground @ <groundFreq> when ready to
taxi`) follows **`DURATION` s after the briefing card**, each re-fetching the group by name at fire
time so a pilot who left their seat is skipped. Symmetric in
code, but effectively BLUE-only (players are blue). pcall-guarded throughout.

**Harness.** The headless Lua harness gained `trigger.action.outTextForGroup`,
`UnitFake:getGroup()` / `getPlayerName()` (a per-unit `playerName` spec models a human slot), and a
`Harness.fireBirth(groupName)` helper (Python `fire_birth`). Tests
`tests/lua/test_briefing_runtime.py` (birth shows the briefing card with every field, the **taxi
card flashes `DURATION` s later** with the callsign + `groundFreq`, the freq option overrides it, the
sweep catches a seated player, an AI birth / unknown group / absent node show nothing) +
`tests/missiongenerator/test_briefingluadata.py` (header with the raw-turn mission number + one record
per player flight, AI-only flights excluded, gated off).

Gated `mission_briefing_popup` (Mission Generation → Battlefield life, default **ON**; the plugin's
own `defaultValue` is also ON). Card duration, the startup grace, the **slot-in delay** (`startDelayS`,
default 5), the taxi **ground frequency** (`groundFreq`, default "249.50"), and the **beep toggle**
(`playSound`, default true) are plugin options. The headless harness gained an `outSoundForGroup` stub
(a `sounds` records list). **In-game pass ☑ VERIFIED 2026-07-15 (checklist B10)** — the reworked
cards + beep confirmed working by user report ("just fine, no issues"). One by-design limitation from
the same report: a pilot in a DCS **dynamic slot** gets no card — dynamic-slot jets aren't
player-crewed ATO flights, so the emitter carries no record for them.

**Flown 2026-07-11 (Red Tide M1, MP dedicated server) — FAILED, root-caused, reworked (checklist
B10).** No pilot noticed a card or beep despite `armed for 12 player flight(s)` and zero errors.
Two compounding causes: **(1) paused-server time compression** — the server sat paused at frozen
sim t=0 while everyone slotted in, so every card (scheduled at `timer.getTime() + 5`) fired in one
window ~5 s after UNPAUSE, minutes after each pilot sat down (intended-by-physics: the sandbox has
no wall clock and nothing fires during a pause — per-group text means each pilot still only sees
their own card; the plugin header now documents this contract); **(2) the beep was silently dead**
— `outSoundForGroup` got the bare basename `briefing-beep.wav`, but an in-miz sound resolves ONLY
via its `l10n/DEFAULT/` archive path, and a wrong path fails with no error, so the one attention
cue that would make heads-down pilots look up never sounded. Fixes (same session): the beep path
prefixed; **per-card logging** (`BRIEFING|: card -> <group> gid=<id> t=<t>`, + `taxi ->` /
`card skipped (group gone)`) so dcs.log now discriminates "sent but unseen" from "never sent" —
the hunt's blocking blind spot; a skipped fire clears the debounce so the pilot's next slot-in
still shows; and a nil `getPlayerName` at the BIRTH instant in a briefing-listed group gets one
+2 s re-check before being treated as AI (the documented MOOSE #806 event-timing race). All four
pinned in `tests/lua/test_briefing_runtime.py`. **The re-fly passed 2026-07-15** (user report) — the
B10 row records the verdict.

---

## §59 — Ground AI sleep (graduated culling) — REMOVED (2026-09-23)

Built 2026-07-12, removed 2026-09-23 on the DM's call. The `aisleep` plugin,
`game/missiongenerator/aisleepluadata.py`, both settings (`perf_ground_ai_sleep`,
`perf_aaa_site_sleep`) and their tests are deleted. Checklist row B11 is closed as removed.

What it did: switched a rear-area garrison group's DCS controller off (`Controller:setOnOff(false)`)
while no aircraft was within 15 NM, and back on on approach or on a hit. The `perf_aaa_site_sleep`
extension added short-range gun sites under a detection-range guard.

Why it went: it armed in tests 1–16 and was never once observed waking or saving frame time, and
no campaign carried it after test 16.

Constraints kept out of the deleted section:

- **An AI strike or SEAD flight cannot prosecute a group whose controller is off.** Its attack task
  finds no target from the ingress point and the flight returns loaded. Measured on Desert Trident
  turn 1, 2026-08-24 (#986): 12 of 13 air-to-ground packages fired nothing with it on; the same
  turn with it off released 31 Mk-82 and 6 HARM.
- **A gun site with its controller off stops radiating**, so an anti-radiation shooter has nothing
  to home on.
- **The 1968 Yankee Station laydown is the measured sim-load outlier** (2026-07-19, turn-1 miz
  against the §66 archive): 738 ground vehicles, 367 AAA, 1,085 statics and 1,328 groups, 2–4× every
  other campaign and 4–12× on AAA. A player on an empty ramp there still hit `ANTIFREEZE`, so the
  cost is global sim load, not local scenery.

The old saves' settings keys and `aisleep` plugin options are dropped on load
(`game/settings/migration.py`, `Settings.__setstate__`).

---

## §60 — SAM guidance-radar redundancy (two track radars per site) — REMOVED 2026-09-29

**Removed on the DM's call.** Every SAM layout's guidance slot is back to `unit_count: 1`
(upstream's value): the 23 layouts in `resources/layouts/anti_air/` that §60 doubled, including
the fork-only SA-2/SA-3/SA-5/SA-6 batteries, HQ-22, S-350, NASAMS-3, Sky Sabre, 3rd Khordad and
Bavar-373. The Patriot family was never changed by §60 and keeps its two STRs. The contract test
`tests/armedforces/test_sam_radar_redundancy.py` is deleted.

What stays:
- The second radar **positions** in the shared `.miz` templates (`2_Launcher`, `6_Launcher_*`,
  `8_Launcher_Circle`, `S-300_Site`). They are inert at `unit_count: 1`; the buy menu can still
  add a second radar by hand, as upstream allows wherever a template has the room. Later §85
  support-section edits live in the same templates, so they were not rolled back.
- Red Tide's and Baltic Fury's lean regiment battalions (`S-300 Site (Single Radar)`,
  `SA-5 Legacy Site (Single Radar ...)`). They differ from the base layouts in composition, not
  only radar count.

Learned while it was live (checklist B12, 2026-08-05): with two track radars, a site that lost
one kept engaging and AI SEAD re-targeted the second. Existing saves keep the sites they were
generated with; new games and newly bought sites get one radar.

**SA-5 and SA-2 launchers doubled in the same change (DM call).** Each launcher holds one missile,
so twice the launchers is twice the missiles:
- SA-5: the full sites 16 (circle) and 12 (semicircle), Red Tide's lean battalions 12.
- SA-2 Battery: 4 → 8 and 6 → 12 launchers; the SA-2/SA-3 mixed site's SA-2 slot 3 → 6.
- New templates: `16_Launcher_Circle.miz` and `12_Launcher_Semicircle.miz` (the 8/6-launcher
  templates plus an outer launcher ring, 240 m and 200 m out) and `SA-2-SA-3_Mixed_Site.miz`
  (`S-300_Site.miz` plus three LN1 positions 230 m out). Every added position is 25 m or more
  from any other unit. The shared templates are unchanged.
- The SA-2 presets that used the shared generic launcher layouts (`SA-2_ZSU`, the HDS SA-2,
  HQ-2) moved to new copies of them with twice the launchers: `12 Launcher Site` (12 on the
  16/12-position templates) and `8 Launcher Site` (HQ-2). The shared 4/6-launcher layouts are
  unchanged for every other system.

Context: test 47/48 (2026-09-28) found SA-5 sites tracking blue jets inside their envelope and
never firing. §60's second Square Pair was one of the suspects; the removal was the DM's call, not
a proven fix. Re-check SA-5 fire on the next flight with one.
---

## §61 — Host red-interceptor scramble (F10 bandit spawner)

The game master's **"give the boys something to shoot" button**, built off the Red Tide M1
debrief: once the first wave was fought off, the session went quiet. Timing tunes helped, but the
host wanted an *emergency lever* — a way to summon a red interceptor flight from a real red base
and force it onto the blue fighters, live, mid-mission, visible only to the host.

**How it plays.** With `host_red_scramble` on, the F10 → Other menu carries **HOST: Red
Scramble**: a one-click **EMERGENCY** command (2-ship of the best red interceptor from the listed
base nearest the airborne blue players) plus a per-base submenu (up to 9 red airfields,
nearest-front first) offering each red fighter type as a `x2` / `x4` launch. A press clones the
flight at that base — by default an **air spawn low over the field at scramble speed** (the QRA
profile: field elevation + 760 m AGL, 300 kt `InitSpeedKnots`; ground spawns die on congested
ramps, the intercept-plugin history) — sets it **weapons free**, confirms to the presser, and a
GCI loop then **re-vectors every live bandit group onto the nearest airborne BLUE fighter**
(players always outrank a nearer AI flight) with a hard `AttackGroup` task each time the target
changes, until the bandits are dead. Repeat presses spawn fresh uniquely-named clones.

**Who sees the menu.** Retribution cannot know DCS multiplayer names at generation, so the gate
is the plugin's **`hostPlayers`** option — comma-separated names **or name fragments**, matched
as a case-insensitive plain **substring** of the player name (plain `string.find`, no Lua
patterns — names carry magic characters). RetLab convention is `"<flight> 1-x | Flash"` with
a changing prefix, so configuring the static tag (`Flash`) gates the menu whatever the event's
flight name; a full exact name still matches (it contains itself). Matching players get a
**per-group** menu on slot-in (`S_EVENT_BIRTH` + a periodic sweep — the §58 pattern, which also
covers the nil-`getPlayerName` birth race and a host seated before the script loads). Left
empty, the menu is **coalition-wide for BLUE** (functional out of the box; a typo'd name failing
silent would be worse — the log's `REDSCRAMBLE|` arm line says which mode is live). A DCS group
menu is visible to everyone in that group, so the host should fly their own flight or trust
their wingman.

**Untracked by design.** The clone templates are built by
`AircraftGenerator.spawn_red_scramble_templates` (`claim_inv=False`, no `UnitMap` entry — the
QRA/CSAR clone pattern, run before `spawn_unused_aircraft` so they get parking): one 2-ship cold
late-activation template per distinct red fighter type (airframe `capable_of(BARCAP)`, best
`task_priority` first, capped at 4), armed by the pydcs default-task payload path exactly like
the QRA templates. This is the **§20 drop-spawn cheat precedent, not a §35/§37 violation**: a
host-summoned bandit is deliberate event content — red pays nothing, killing it changes nothing
at the turn boundary — which is exactly why it stays behind a host action and a default-OFF
setting. Bandit kills *of* players record natively (players are real tracked units).

**Wiring.** `game/missiongenerator/redscrambleluadata.py` (`populate_red_scramble_lua`, in
`luagenerator.py`) emits `dcsRetribution.redScramble` — `templates` (group + label) and `bases`
(name, nearest-front first) — only when the setting is on and both lists are non-empty;
`resources/plugins/redscramble/` runs the menu/spawn/vector runtime (options: `hostPlayers`,
`takeoff` air/hot/runway, `vectorIntervalS`). Gated `host_red_scramble` (Mission Generation →
the new "Host & event tools" section, default **OFF**), **preseeded ON in Red Tide** (with the
`redscramble` plugin until 2026-10-15, when it lost its checkbox — and `redscramble.hostPlayers: Flash`,
the host's static name tag) ahead of the Friday 2026-07-17 regeneration.

**Tests.** `tests/missiongenerator/test_redscrambleluadata.py` (emit contract: gating, red-only
airfields, front-first ordering, no-node cases) + `tests/lua/test_redscramble_runtime.py` (the
real plugin under the harness: host-name gating incl. the pre-seated sweep, coalition fallback,
spawn/ROE/announce, the AttackGroup vector onto the airborne player, no re-task while the target
holds, unique repeat clones, the 9-base cap, clean no-op without the node). The harness models no
DCS AI — whether the bandits actually press the intercept is the in-game item.

**In-game pass DONE** (checklist B14): the air-spawn clone flies off cleanly (not stalled),
the `AttackGroup` push makes the AI commit (fallback if `setTask` is rejected: a Mission-route
task, the §15 combatsar divert lesson), the per-group menu really is host-only in MP, and the
cloned jets carry their A2A loadout.

---

## §62 — Squadron-sequenced Hornet/Tomcat board numbers (modex)

The answer to the 2026-07-12 finding: **Hornet and F-14 board numbers were completely random.**
pydcs assigns every aircraft's `onboard_num` by popping from an *unordered* Python set
(`Country.next_onboard_num` → `set.pop()` over the free 010–999 pool), so Navy jets spawned
wearing arbitrary three-digit modexes. Real Navy squadrons don't: the air wing assigns each
squadron a **modex block** (100, 200, 300, …) and numbers the squadron's jets sequentially
inside it — the first jet X00, the second X01, the third X02.

**How it works.** `ModexAllocator` (`game/missiongenerator/aircraft/modex.py`, held by
`AircraftGenerator`) pre-assigns one block per Hornet/Tomcat squadron at construction — per
coalition, in air-wing iteration order (stable per save), **Tomcats sorted ahead of Hornets**
so the F-14 squadrons take the traditional CVW 100/200 fighter blocks. Blocks run 100–900 and
wrap after nine squadrons (board numbers are three digits). `assign(squadron, group, country)`
then re-stamps every generated unit of a modex squadron with the squadron's next number, in
generation order: **tasked flights first** (they take X00 up), then the §1 QRA intercept
templates (the reserve is the squadron's own jets; MOOSE clones copy the template numbers),
then the §61 red-scramble templates, then the untasked ramp aircraft (`_spawn_unused_for`).
On first use the squadron's whole block is reserved with its pydcs `Country`
(`reserve_onboard_num`) so the random allocator can't hand a later same-country aircraft a
number inside it. Every other airframe keeps the stock pydcs number.

**Scope.** Curated to the Hornet + Tomcat families (`MODEX_AIRCRAFT_IDS`): `FA-18C_hornet`,
the AI `F/A-18A`/`F/A-18C`, the five Heatblur F-14 variants (`F-14BU` added 2026-08-23), and
the AI `F-14A` (so Iranian Tomcat squadrons sequence too — blocks are per coalition, each starting at 100). The campaign
does not model individual airframes, so numbering is **per-mission generation order** —
deterministic within a mission, not sticky to a pilot across turns. Pure generation behavior:
no setting, no plugin, no save-format change; applies to the next generated mission of any
existing campaign.

**Tests.** `tests/missiongenerator/test_modex.py`: the cross-flight X00/X01/… sequence,
distinct per-squadron blocks, Tomcats-before-Hornets block order, per-coalition blocks both
starting at 100, the non-modex no-op, the once-only whole-block country reservation, the
nine-squadron wrap, and a pydcs guard that every curated id resolves to a real plane type.

### The Tomcat's board number is its livery, not its `onboard_num` (2026-08-23)

**The 2026-07-16 verification was a false positive and B15 is re-opened.** The Hornet half
holds; the Tomcat half never worked. No F-14 livery declares a board-number material, so DCS
draws nothing on the airframe and the jet shows whatever its diffuse texture carries.

The control that settles it: every airframe that *does* paint `onboard_num` names the material
in its livery `description.lua` — Su-27 (`su27_nose_numbers`), MiG-29A (`mig-29_numbers_tail`),
F-15C (`f15_numbers`), Su-25 (`Su-25-numbers-1`), FA-18C (`f18c1_number_nose_left`). **0 of 47
stock F-14 liveries do**, across the A, B and B(U) folders, and neither does RetLab's own
VMF-29 set. Neither F-14 EDM contains a bort string. Heatblur ships four VF-32 skins differing
only in the painted number (100/101/102/103) and four VF-1 Wolfpack skins NK100–NK103 — nobody
authors that for a jet that renders the number dynamically.

**Why 2026-07-16 passed.** That Scenic Route turn flew VF-32 F-14Bs, whose `livery_set` is
literally numbered 100/101/102/103, while §62 had stamped `onboard_num` 100/101/102/103 on the
same four jets. The painted numbers and the assigned numbers agreed by coincidence, so a coarse
visual pass could not tell them apart.

**Reported by the DM, 2026-08-23: every F-14B(U) in a mission wore the same board number.** The
five F-14B(U) presets each pinned one `livery:` — so the whole squadron wore one skin and one
painted modex — while the F-14B presets already used `livery_set`. The live
`retribution_nextturn.miz` had four COBIA Escort B(U)s with four *different* `onboard_num`
values (459/597/768/976) on one livery, `vf-103 2004 aa100`.

**The fix.** `LiveryAllocator` (`game/missiongenerator/aircraft/liveryallocator.py`), held by
`AircraftGenerator` beside `ModexAllocator` and passed to `AircraftPainter` at all three
`apply_livery` sites (including through `FlightGroupConfigurator`), hands a squadron's **first
jet of the mission the first entry of its `livery_set`** — by convention the X00 CAG bird — then
cycles the line jets behind it in generation order. One CAG bird per squadron per mission, like
a real air wing. **A set of fewer than three cycles whole instead** — reserving one of two leaves
every later jet on the single survivor, which is the one-number squadron this fixes. It replaces
`Squadron.random_round_robin_livery_from_set`, which picked at
random and so put two CAG birds in an eight-jet squadron; that method is still the fallback for
any caller with no allocator. `Squadron.ordered_livery_set` rejoins `_livery_pool`, because the
old random path drained `livery_set` into it and a save taken mid-rotation would otherwise be
missing liveries.

Data side: the ten `resources/squadrons/F-14B(U) Tomcat` presets collapse to five — one per
squadron, `livery_set` ordered CAG bird first. **DCS ships only two B(U) liveries for VF-101,
VF-11 and VF-143**, so those three alternate; only VF-103 (AA100/101/103/105) and VF-32
(AC100/101/107/111) have enough to hold a CAG bird out. VF-101 and VF-11 have no X00 jet in the
distribution at all. The F-14B VF-32 set was reordered to lead with 100. **Squadron liveries are pickled, so this reaches new campaigns only** — an
in-flight save keeps its single livery.

`F-14BU` was also missing from `MODEX_AIRCRAFT_IDS` entirely, which is why its `onboard_num`
came out random (459/597/768/976) while the F-14B got the clean 100/101/102/103. Added. The F-14
ids stay in the set even though nothing paints them, so anything reading `onboard_num` sees a
coherent sequence; the cost is a reserved 100-number block per Tomcat squadron.

Tests: `tests/missiongenerator/test_livery_allocator.py` (CAG-once-then-cycle, per-squadron
sequences, the two-livery and one-livery degenerate cases, the empty-set no-op, the drained-pool
rejoin) and `tests/test_squadron_livery_sets.py` (every F-14B(U) preset carries a set, leads
with its lowest modex, and repeats no board number).

**2026-09-23 — the livery follows the board number; the CAG bird is X00's alone (DM rule).**
The two-livery rule above broke it: VF-143's AG100 flew on every second jet. `next_livery`
now takes the jet's modex (stamped before painting; the ramp path was reordered to match),
passed only when it means something — a curated modex squadron or a pinned flight. A jet
wears the livery painted with its own number if the set has one (`livery_modex` reads the
three digits that do not follow a dash, so `VF-103 … AA100` reads 100). A CAG / hi-vis
livery (`is_cag_livery`: an X00 number, or `CAG` / `Hi Vis` in the name) goes to the X00
jet and no other. Every other jet cycles the remaining line liveries; a set with no line
livery returns None and the jet takes the squadron's plain livery. Without a meaningful
number, the squadron's first jet of the mission stands in for X00. VF-143 B(U) now flies
AG100 on 100 and AG106 on every line jet. **Navy only** (DM call, 2026-09-23): the painter
hands the allocator only `MODEX_AIRCRAFT_IDS` squadrons; every other livery set keeps the
random round-robin.

**Upstream:** carried on [dcs-retribution#874](https://github.com/dcs-retribution/dcs-retribution/pull/874)
since 2026-09-23 as a second commit beside §65 (inventory item 19), without the QRA and §61 hooks.

**In-game pass: ☑ VERIFIED** (checklist B15, 2026-09-16 audit: the Tomcat livery order read from
the generated miz on three campaigns). Hornet sequencing verified 2026-07-16 on the flown
Scenic Route turn-3 test (*"The Modex on our fork is 100% working … Everyone's modex looked
accurate"*) — that reading stands for the Hornet, whose liveries do carry the number material.

### A pinned board number per flight (2026-09-23)

The Payload tab's **Set board number** (`BoardNumberSelector` in
`qt_ui/windows/mission/flight/payload/QFlightPayloadTab.py`) stores `Flight.board_number`:
the lead's number, wingmen following in order. **Navy only** (DM call, 2026-09-23): the box
shows only for `MODEX_AIRCRAFT_IDS` flights, and a pin on anything else is ignored.
The spinbox stops where the run still fits (996 on a four-ship). Taking a number another
flight of the coalition has pinned is allowed: `take_board_number` (in `modex.py`) moves
that flight to the next free run above its old one (below only if nothing above fits), and
the tab names the flight and its new number. Upward first keeps a moved flight in its own
hundred block. The moved flight keeps a pin and never lands on a third flight. Before
2026-09-23's rework the tab refused the number instead (DM: "there has to be a better way").

At generation `ModexAllocator` claims every pinned number per coalition before stamping
anything. The pinned flight wears its numbers; squadron sequences skip claimed numbers; a
random pydcs number that lands on one is re-rolled; the claims are reserved with each
country. A clash the tab could not see (a flight resized after pinning) goes to the first
flight in ATO order and the later member falls back to automatic; resizing on the flight
tab re-takes the pin, so that case needs a size change made elsewhere. On the Tomcat the
pinned number reaches the paint only where the squadron has a livery painted with it,
which the tab says.

Persisted on the flight (`__setstate__` defaults it to None). Tests: the pinned cases in
`tests/missiongenerator/test_modex.py`, and `tests/test_board_number_selector.py` (offscreen
Qt). In-game pass: checklist **B138**.

That mechanism is what any per-pilot modex work rests on — see upstream issue
[#863](https://github.com/dcs-retribution/dcs-retribution/issues/863) (per-pilot modex pins in
the squadron YAML), which §62 does **not** close: §62 numbers *slots* per mission, not *pilots*
across missions, and its curated `MODEX_AIRCRAFT_IDS` doesn't cover the filer's A-4E-C.

---

**Tomcat squadron callsigns (2026-10-10).** The 18 F-14 squadron files under
`resources/squadrons/F-14*` carry the squadron's real radio callsign in the existing
`callsign:` field (`SquadronDef.callsign`): VF-11 Ripper, VF-14 Camelot, VF-21 Freelance,
VF-32 Gypsy, VF-33 Tarbox, VF-41 FastEagle, VF-101 Gunfighter, VF-102 Dback, VF-103
Victory, VF-111 Sundowner, VF-142 Dakota, VF-143 Dog, VF-211 Nickel. Each squadron's
flights default to it, numbered in the order they are fragged, and it shows on the F10
map, labels, kneeboard and briefing. **DCS cannot voice a callsign it does not ship**, so
AWACS, ATC and AI wingmen do not say the name; Red Tide's "Voodoo" squadrons behave the
same (DM call 2026-10-10: the text matters more). One word each, because every stock DCS
callsign is one word and the name is written straight into the unit's callsign: VF-41's
"Fast Eagle" is "FastEagle". VMF-29 is left on stock callsigns. The callsign list is from
rmac7664/dcs-retribution (`feature/f14-callsigns`); its own callsign plumbing is not
taken, the fork already had the field. `tests/test_tomcat_squadron_callsigns.py`. Row
**B216**.

## §63 — Ship-launched cruise missile raids

DCS warships with land-attack cruise missiles — the vanilla Burke's Tomahawks, the
CurrentHill pack's explicit Kalibr hulls — can strike shore targets via a `FireAtPoint`
task carrying the cruise-missile weapon flag (`2097152`, the ME "fire Tomahawks at a
point" mechanism), but nothing in Retribution ever tasked them: ships were ANTISHIP
targets, carrier decks, and the §34 gun line, never shooters inland. §63 gives the
campaign real cruise missile raids, both directions.

### Blue's raids are fogged (2026-08-18)

`_enemy_raid_targets` picks from ground truth, and `commandcenter` is
`_TARGET_CATEGORY_PRIORITY` **0** — so before this gate the first blue raid of a
campaign went straight at a command post the player could not see, and the strike then
revealed it permanently. That is the exact find §3/G40 makes recon earn.

Blue's target list now skips anything `hidden_from(Player.BLUE, tgo)` returns True for
(`game/theater/fogofwar.py` — `hidden_on_player_map` wrapped in `fog_intact()`). Red is
never fogged. (A separate `map_hidden` skip for both sides sat beside it until the §50
ambush was removed on 2026-10-11.)

`fog_intact()` matters here: the reveal overview is a display toggle, and without it a
host who ticked "reveal fog of war" before passing the turn would get a *different raid
target* than one who did not. Pinned by
`tests/retlab/test_cruise_raids.py::test_the_reveal_overview_does_not_change_what_blue_shoots`.

The same gate is applied to §44's carrier strike, which had the same shape.

**The force-model contract first**: the missiles are real DCS weapons fired by a real,
tracked ship TGO. Kills record natively through the ordinary death events (no
debrief-schema change for the strikes themselves, no phantom spawns — the §35/§37
discipline), and sinking the shooter ends the raids. The plugin owns no kills and no
spawns. The "enemy point defense gets to intercept" half is carried by the **defender
launch wake** (built 2026-07-16 after the flown test showed no defender in the stack
ever wakes for a cruise raid on its own — see the B16 observed gap below): every launch
sets the opposing side's ground AD groups within `defenderWakeRadiusNm` (8 NM) of the
aimpoint to alarm-state RED (alarm state only — `enableEmission` untouched) for ~the missile flight time + `defenderWakeExtraS` (300 s),
then restores AUTO; an engine-managed site keeps its own emissions loop. Unflown — the B16
re-fly is the arbiter of whether an awake SA-15 then actually kills Tomahawks.

**Eligibility** is the curated `LACM_SHIP_DCS_IDS` set in `game/retlab/cruise_raids.py`
(the §41 curated-data pattern — DCS/pydcs expose no per-ship weapon taxonomy): the vanilla
`USS_Arleigh_Burke_IIa` + `TICONDEROG`, the CH Burkes/Ticonderogas, and the CH
`*_LACM`/`_CMP` Kalibr variants (`redfor_current`/`redfor_russia_2020`/`CH_russia_2020`
field them, so red raids exist today). The AShM-only sister hulls are deliberately absent.

**Magazines (the anti-exploit)**: DCS silently rearms every mission, so unmanaged ships
would fire a free full salvo every turn. Each launching *group* carries a persisted
campaign magazine (`game.cruise_missile_magazines`, keyed by the stable
`TheaterGroup.group_name`, seeded from the per-hull `LACM_MAGAZINE_BY_TYPE` table — Burke
24, the 8-cell Kalibr corvettes 8) that is debited **only** from what the plugin reports
actually fired, through the new `cruise_missiles_state` Lua→Python channel (the §57
minefields pattern: declared in `dcs_retribution.lua`'s `game_state`, parsed in
`game/debriefing.py`, committed by `MissionResultsProcessor.commit_cruise_missiles` →
`reconcile_cruise_missiles`). Planning/generation never debits, so re-generating a
mission is free; there is no rearm — the magazine is the war stock.

**Two fire paths share one budget** (`resources/plugins/cruisemissiles/`):

* **Auto raids** (`cruise_missile_auto_raids`): `plan_cruise_raids` — a pure function of
  game state, called by the emitter — picks at most one raid per side per turn: the ship
  whose best reachable (≤ 250 NM) enemy ground object has the highest category priority
  (commandcenter/comms first — composing with §52 decapitation — then the §53 war-economy
  power/factory/oil/fuel/ware/ammo buildings, then anything else strikeable; never ships),
  ROE-gated for BLUE via the §40 `roe_blocks_target`.
  **A target is skipped when the straight ship-to-target line enters the threat ring of an
  enemy SAM site with a live point-defense group** (`_point_defended_rings`; blue counts only
  sites it can see). Test 54: six TLAMs flew past a point-defended SA-10 and it spent 22 of
  its 24 missiles on them before the strike package arrived (DM call 2026-10-07, row B186).
  A PD group is a SAM (`IadsRole.POINT_DEFENSE`) or, beside a SAM group, AAA guns: the
  layouts' PD slot fields guns as often as a SAM, and a gun group carries Skynet's AAA role
  (`EWR`). Test 62 (2026-10-18): six TLAMs flew past an SA-3 with a Shilka, an SA-6 with two
  and a Hawk with an S-60, because only the SAM kind was counted.
  The plugin fires the salvo (`RAID_SALVO` 6, capped by the magazine) after a launch
  delay (default 240 s), cueing the launching side with the target and the defender with
  a deliberately vague "LAUNCH WARNING — enemy cruise missile launch detected".
* **Player call-for-fire**: an F10 "Cruise Missile Strike" menu per coalition that owns
  a capable ship — a salvo (default 4) onto the coalition's last F10 map marker from the
  nearest ship with stock in range (the §34 NGFS marker pattern), plus a "Magazine
  status" readout so the stock is visible before spending it. **The marker's own text
  sizes the salvo**: a marker whose text is just a number — `6`, or `#6` — fires exactly
  that many (`salvoFromMarkText`; magazine-capped, so `#99` just empties the tubes),
  while any normal target label (or a bare `#`, or `0`) falls back to the default. The
  mark panels from `world.getMarkPanels()` carry their `text` field, so no extra channel
  is needed.

**Wiring**: `game/missiongenerator/cruisemissileluadata.py` (`populate_cruise_missiles_lua`,
in `luagenerator.py` after the minefields emitter) emits `dcsRetribution.cruiseMissiles`
— `ships` ({group, coalition, remaining}: the mission's hard per-group expenditure cap)
+ `raids` ({group, coalition, target, x, y, count}) — only when `cruise_missile_strikes`
is on and a live launching group exists, so a normal mission carries no node and the
plugin no-ops. Plugin options: raid launch delay, player salvo size, player range,
impact dispersion, menu toggle, defender wake (on/off, radius, extra hold). Settings
(Mission Generation → Naval strike, both default **OFF**): `cruise_missile_strikes`
(master) + `cruise_missile_auto_raids` (`enabled_when` the master).

**Tests**: `tests/retlab/test_cruise_raids.py` (magazine seed/persist/debit-floor,
the C2-over-closer target pick, the range gate, ship/hidden/dead target skips, the
toggle gates, symmetric red raids, pre-feature state tolerance),
`tests/missiongenerator/test_cruisemissileluadata.py` (node shape + absence), and
`tests/lua/test_cruisemissiles_runtime.py` (the delay, the cruise weapon flag on the
pushed task, the magazine as a hard cap shared across raid + call-for-fire, the state
mirror + dirty flag, dead-ship no-op, marker targeting, clean no-node no-op — the
harness `TaskFireAtPoint`/`PushTask` fakes gained the `weaponType` argument).

**In-game pass — VERIFIED 2026-07-16** (checklist B16, flown Persian Gulf "Scenic Route"
test): the scripted `FireAtPoint` push with `weaponType = CruiseMissile` fires the exact
commanded quantity — 6 commanded, 6 `BGM-109C Tomahawk` shot events — and **both vanilla
hulls honor it** (the "least certain" `TICONDEROG` flew the raid; a Burke escort group flew
the F10 call-for-fire + a raid in a sibling mission). The missiles cruised to the planned
C2 target and killed it (hits + a kill recorded natively), the launch cues fired, the raid
launched inside the [240, 900] s stagger window, and the magazine loop closed end-to-end:
debrief row "6 fired, 10 remaining" → the save's `cruise_missile_magazines` debited 16→10
→ next turn's raid re-planned onto the *next* command center. **Observed gap (the
SHORAD-intercept half FAILED):** the target's point defense — 2 alive SA-15s 250 m from
the impact — sat idle through the whole salvo (user-watched). Code-confirmed root cause:
the group ran vanilla on DCS's default ALARM STATE AUTO, which never goes weapons-hot
for a *weapon* object; the managed paths are equally blind (under the MANTIS bridge, EMCON woke off MOOSE
`Detection`, which scans units, never weapons; the SHORAD link's `SHORAD.Harms`/`Mavs`
wake lists carry no BGM_109/Kalibr). **Closed same day by the defender launch wake**
(see the contract paragraph above; details + re-fly criteria in
`docs/dev/design/retlab-cruise-missile-raids-notes.md` "The intercept gap") — the wake
itself is unflown. A **second flown test the same day** (turn 3, pre-wake build,
Tacview `Tacview-20260716-014958`) confirmed the linked-PD variant in the air (a
SHORAD-linked `DINGO (PD)` Tor pair held dark at the target, zero launches), proved
**naval AD intercepts natively** (a red Krivak pair killed 2 of 6 Tomahawks with
SA-N-4s — ships are always hot, exactly the "already hot" caveat, so the saturation
game is real wherever a defender can shoot), flew the C2 re-target (INSECT, as the
save predicted) from the debited magazine with a same-turn re-fly logging the
identical remainder (turn-boundary-only debit, flown), and confirmed the bridge's
`useEmOnOff = false` means link-dark is alarm-GREEN — the wake's alarm-RED override
reaches every ground management state. Still untested (minor): the `#N` marker-text
salvo sizing, the CH Kalibr hulls, red-side raids, full-magazine exhaustion.

---

## §64 — Carrier deck spawn policy (six-pack last resort + MP slot timing)

**2026-10-07 — the six-pack setting is REMOVED (DM call, test 54).** `LAST_RESORT`
late-activated player carrier groups at t=1 s. In multiplayer that turns their slots into
a "delayed start" nobody can fly: in test 54 the CPY Hornet pilots sat in their fragged
slots and had to move to dynamic slots, and the carrier package launched 9-15 min late.
Player carrier flights now always spawn at mission start (the old `SIXPACK_FIRST`
behavior); AI carrier ground starts keep the one-second placement activation.
`carrier_deck_policy` and `player_flights_sixpack` are dropped in `migration.py`; the
`CarrierDeckPolicy` enum stays only as a save-compat stub. The rest of this section is
the history.

The 2026-07-16 supercarrier finding: AI taxiing to the catapults jam against the player
— "they get stuck between me and the catapult" — because the player is parked **on the
six-pack**, the first-filled deck spots that sit squarely in the taxi lane to the bow
cats, with a ten-minute cold start while the AI (who crank promptly and move) spawn in
the far spots and have to squeeze past. The arrangement was exactly backwards, and the
old `player_flights_sixpack` boolean (default ON) is what put the player there.

**The one placement lever DCS gives us is spawn timing.** The mission format cannot
pick deck spots (a carrier flight is just "group linked to the ship + start type");
DCS fills the six-pack from the mission-start spawn wave, and a group whose spawn is
delayed even one second is placed elsewhere on deck — the dcs_liberation#1309 trick the
generator has always used to keep **AI** off the six-pack (AI parked there deadlock the
deck). Taxi *routing* itself — deck pathfinding, taxi spacing at airfields, wingmen
tailgating the player — is engine AI with zero mission-level control (deck crew is
player-guidance only; AI never use it); the AI F-14A's forced catapult starts
(`_start_type_at_group`, upstream #1927) are the precedent for how immutable it is.

**`CarrierDeckPolicy`** (Mission Generation → Player slots; replaces the boolean, §16
enum-migration pattern — ON → `SIXPACK_FIRST`, OFF → `LAST_RESORT`, old key dropped):

* **`LAST_RESORT` (new default)** — player carrier ground starts take the same
  one-second late activation the AI always take, so DCS parks them clear of the
  six-pack; the six-pack then only fills as overflow once the rest of the deck is
  full. Nobody with a ten-minute startup sits in the AI taxi flow.
* **`SIXPACK_FIRST`** — the legacy behavior: player flights spawn with the
  mission-start wave and take the six-pack.

**The MP slot-timing fix rides along** (both modes): a TOT-delayed client carrier
flight was late-activated for its **full** delay because `should_activate_late`
force-carrier'd every cold carrier start — so in multiplayer the flight's slots did not
exist in the slot list until the push time (the "your flight is delayed to start"
complaint; airfield flights never had this, they use the uncontrolled path). Client
carrier COLD flights now spawn **uncontrolled** like their airfield counterparts —
slots live from ~mission start, jet cold on deck — with the `StartCommand` trigger
holding only the AI members to the planned push, plus the one-second placement
activation under `LAST_RESORT`. WARM/RUNWAY delayed client flights keep the full-delay
late activation (a hot jet can't wait without burning gas — same as airfields); AI
flights keep late activation entirely (deck crowding). One latent AI fix rode along:
a `WaitingForStart(0)` AI carrier flight previously got a `TimeAfter(0)` activation
(joining the mission-start fill wave); the placement delay now floors it at 1 s.

**Single player ignores the "spawn immediately" setting (2026-07-18, user call):**
`never_delay_player_flights` ("Spawn player flights immediately (keep planned TOT)",
default ON) is a **multiplayer** setting — it exists to keep every player slot
selectable from mission start — but it also applied to single-player missions, parking
the lone player on the ramp at the mission start time for a takeoff 40+ minutes out.
The delay decision now receives `AircraftGenerator.use_client` (two or more client
slots across both ATOs — the same mission-wide predicate that assigns Client rather
than Player skill): **with fewer than two player slots the setting is ignored** and the
lone player flight is delayed to its planned start time like the AI. Cold starts
additionally **late-activate** — materializing at their planned engine-start time —
instead of taking the uncontrolled-at-t=0 path, which exists purely for MP slot
availability and would still leave the lone player idling in the pit from mission
start; WARM/RUNWAY/air starts take the existing full-delay late activation (taxi /
takeoff / push time). The ten-minute rule survives (a short hold still spawns at
mission start), and AI flights and true MP missions are byte-identical.

**Removed 2026-09-18 (DM call): the deck cap (#1032) and the Tomcat spawn delay (#1020).**
Every carrier flight parks on the deck again, and every carrier group activates 1 s after its
start, Tomcats included. What the two taught, kept here because the code is gone:

- **DCS drops what a full deck cannot take, silently.** Test 36 (2026-09-17) fragged 50
  aircraft onto CVN-71. DCS placed 14 in the first 233 s and every carrier group activating
  after t=281 s never appeared: 33 aircraft, no log line, a `state.json` record at the boat
  reference with `alt = -1`. Five shore-based escorts then held their anchors inside red
  airspace; the escort release backstop (§8) stays.
- **The cap was 16 per mission, not 16 at once.** It air-started every flight after the
  first 16 however long the deck had been clear: brady turn 3 parked 15 of CVN-71's 53.
- **A deck does clear.** Tests 9 and 32 relaunched from the deck through the mission and
  every jet launched. Test 36's jam was a Tomcat pile-up: 8 F-14Bs parked in 2 s, 12 in
  233 s, 3 ever launched. Tests 9 and 32 never parked more than 4 Tomcats together.
- **Carrier launches run late.** The plan allows 2.5 min from spawn to wheels-up. Across
  23 flown groups the median was 4.5 min; busy 4-ships took 6–9 and test 9's crowded
  Tomcats 20 or more. Air starts are always on time.
- **The Tomcat delay** held F-14s to a 2 s activation so the Hornets took the port-quarter
  pair first (the DM did not want a Tomcat there). Best effort only: it needed four
  non-Tomcat jets spawning at mission start.
- A time-aware count (the deck counted as it empties, whole packages, at most 4 Tomcats:
  #1036) was built and dropped the same day over missed TOTs.

**Wiring**: `waypointgenerator.set_takeoff_time` split into the hold delay (the
WaitingForStart remaining) and `needs_deck_placement_delay()` (carrier COLD/WARM ground
starts; AI always, clients per policy); `should_activate_late` exempts client carrier
COLD flights. `FlightGroupConfigurator` threads its `use_client` flag into
`WaypointGenerator` (the `multiplayer` param), consumed by `should_delay_flight` /
`should_activate_late` for the single-player bypass. No plugin, no Lua, no miz-format
change; `game/settings/` carries the enum + `_migrate_legacy_settings`
migration.

**Tests**: `tests/missiongenerator/test_carrier_deck_policy.py` (the trigger matrix:
AI placement/push-time activation + the zero-hold floor, client placement under both
policies, the delayed-client uncontrolled+StartCommand+placement combo, warm
late-activation parity, airfield/runway no-ops, and the single-player matrix —
cold/warm/runway late activation at the planned start time, the ten-minute rule, the
MP + AI no-changes) and
`tests/settings/test_carrier_deck_policy.py` (default, boolean→enum migration both
ways, never-stomp, UI visibility).

**Needs an in-game pass** (checklist B17): whether DCS overflows delayed spawns *into*
the six-pack once the rest of the deck is full (the literal "last resort" — the 1 s
trick is only proven to move spawns off it; fallback is exempting overflow flights at
generation, the deck count is known), deck behavior with several client flights parked
uncontrolled from mission start, and the payoff itself — AI reaching the cats without
jamming on the player. What no mission-level change can fix: same-group AI wingmen
taxiing on the player's tail (engine formation taxi), and AI recovery taxi after
landing. The single-player bypass is **checklist B26**: how DCS seats the SP pilot in
a late-activated Player-skill group (and where they wait until it materializes) is
DCS-only.

**Sunk deck (2026-10-06, juanjux/dcs-escalation#501, deck half)**: `Carrier`,
`EssexCarrier` and `Lha.can_operate` also require `_has_usable_flight_deck()`, so a
sunk hull with escorts afloat takes no relocation, transfer or new squadron. A fleet
with no carrier group yet (turn-0 squadron assignment) passes, because
`find_main_tgo` raises then. Tests: `tests/theater/test_sunk_flight_deck.py`.

---

## §65 — Curated carrier comms (CV Operations Data cleanup)

The answer to the 2026-07-16 complaint: **the DCS-generated "CV Operations Data" kneeboard
page read like allocator junk.** DCS auto-renders that yellow-notepad page (and the matching
briefing screen data) straight from the mission file — it cannot be restyled, only fed better
data — and the generator fed it whatever fell out of the allocators: the boat "named"
`0796 | CVN-71 Theodore Roosevelt` (the theater-unit id prefix leaking onto the Callsign
line), TACAN channel **1X** with a `random.choice` ident that re-rolled every mission, ICLS
channel 1, Link 4 parked on a random inter-flight UHF like 255.0, and a fresh random ATC
frequency every single turn. The pro campaigns RetLab catalogs (a paid FA-18C campaign's HOMEPLATE
"Mother" card is the model) treat the boat's numbers as its identity: stable, hull-flavored,
memorable.

**The curated boat card.** `game/data/carrier_comms.py` (`CARRIER_COMMS_PLANS`, keyed by
pydcs ship type id) gives every vanilla hull a signature data set — TACAN **channel = hull
number** where that's legal for a surface transmit/receive beacon (channels 2–30 and 47–63 X
are excluded by DCS datalink constraints, so Forrestal 59 → 64X and Tarawa hull 1 → 41X) with
a **boat-name ident** (TRO/ABE/GWN/STN/HST/FID/TAR/KUZ), **hull-keyed ICLS** (CVN-71 → 11 …
CVN-75 → 15, Forrestal 9, Tarawa 1), **Link 4 at 320.1–320.9 MHz** (one per hull), and a
**stable ATC UHF** (304–312, one per hull). Mod carriers without an
entry keep the legacy allocator path end to end.

**Link 4 moved out of the 336 MHz band 2026-10-10.** The F-14's Data Link Control Panel
dials 300.0–324.9 MHz only (Heatblur manual), so a Tomcat could not tune the 336.1–336.9
the table carried, which was the mission editor's default. Each hull keeps its last digit
(Stennis 336.4 → 320.4). The fallback allocator (`RadioRegistry.alloc_link4`) and the
*Set LINK4* dialog are held to the same band. A save that stored one of the old curated
values is given the new one, at load (`Migrator`) and at generation (`_resolve_link4`,
`is_retired_curated_link4`); any other stored value still wins. Found through
red-one1/dcs-retribution's `fix/carrier-datalink-f14-frequency`, whose allocator range is
ported. Not flown: row **B213**.

**Precedence.** Values from the table are defaults, not mandates, resolved in
`GenericCarrierGenerator._resolve_{atc,tacan,link4,icls}` (`tgogenerator.py`): a value
stored on the control point — user-set from the base dialog or persisted from an earlier
turn — always wins; a curated channel some other emitter already owns falls back gracefully.
For TACAN the fallback is `TacanRegistry.alloc_near`: the map's real beacons own many
hull-number channels (Bagram is 74X on Afghanistan, Kandahar 75X), so a taken channel walks
outward to the **nearest valid free neighbor** (Stennis off Afghanistan gets 73X) instead of
falling to the bottom of the band; `alloc_for_band` now also marks what it issues so the two
allocators can't double-book. ICLS moved from a bare `iter(range(1, 21))` to an
`IclsAllocator` (claim/reserve/alloc over a shared used-set) so a curated channel and the
sequential fallback can't collide when two boats sail the same theater. **Every resolved
value is persisted back to the control point** (`frequency`, `tacan`, `tcn_name`, `link4`,
`icls_channel`) so the whole card is stable across turns — ATC, Link 4, and ICLS previously
re-rolled or re-allocated every mission.
The mission generator's up-front TACAN reservation (`keeps_stored_tacan`, `missiongenerator.py`)
skips a carrier's *auto* channel, since `_resolve_tacan` re-derives it: reserving it made the
boat walk off its own last value, so where the map owns the hull channel it flipped every
generation (CVN-71 on Persian Gulf, 69X/72X; test 47, 2026-09-29, row B156).

**Flagship naming.** The page's Callsign line prints the flagship's *unit name*, so
`_flagship_name` names the carrier unit by its hull name ("CVN-74 John C. Stennis") instead
of the `NNNN | `-prefixed theater-unit name. The name is set before
`_register_theater_unit` records it, so debrief kill-tracking keys off the same string; a
second boat of the same class keeps the unique id-prefixed name (UnitMap collision guard).
Escorts and every other ship keep the standard prefixed names.
Anything else that names the flagship must read `MissionData.renamed_units`: until
2026-09-29 the IADS data still sent Skynet the prefixed name, so no carrier or LHA ever
joined as a radar (test 47's `dcs.log`; row B157).

**CP naming follows the hull (2026-07-17 night-fly fix).** The flown Scenic Route Merged
boat exposed the other half: the carrier **CP** is named at game start from the faction's
`carrier_names` pool, and the **supercarrier upgrade is keyed by that CP name**
(`NavalControlPoint.upgrade_to_supercarrier`, now table-driven by
`STENNIS_SUPERCARRIER_UPGRADES` in `controlpoint.py`) — a pool name outside the map
("CVN-74 John C. Stennis" has no Supercarrier model) fell through the else-branch and
sailed a **CVN-71** wearing Roosevelt's flagship name and 71X TACAN while the ATO/briefing
called it the Stennis. `hull_consistent_carrier_name` (`game/theater/start_generator.py`)
closes it at naming time: with the supercarrier setting **on**, a Stennis-hull boat only
draws names the upgrade maps (the chosen name then picks *which* supercarrier — a
two-boat campaign gets two distinct, self-consistent hulls); with it **off** (or for any
unmapped hull, e.g. the LHA), the pool name matching the hull's own display name is
preferred (the free Stennis IS CVN-74, the Tarawa IS LHA-1). The pool stays the fallback,
so flavored names ("Carrier Strike Group 8") keep working, and **unmapped names keep the
legacy CVN-71 fallback in the upgrade itself** so existing saves keep the boat they've
been sailing. New-game naming only — no save migration. Tests
`tests/test_carrier_naming.py`.

**Headless-verified end-to-end** (2026-07-16, Enduring Resolve through the real
`GameGenerator` → `begin_turn_0` → `MissionGenerator` pipeline): the generated miz carries
unit name `CVN-74 John C. Stennis`, TACAN 73X `STN` (74X correctly ceded to Bagram), ICLS 14,
Link 4 336.4, group ATC 308.000 — exactly what the DCS page renders. Pure generation
behavior: no setting, no plugin, no save-format change; applies to the next generated
mission of any existing campaign (already-persisted channels on an old save win by design,
so an in-progress campaign keeps its known numbers).

**Tests.** `tests/test_carrier_comms.py`: table invariants (unique TACAN/ATC/ICLS/Link 4,
T/R-legal channels, Link 4 inside the F-14's band, 3-letter idents, ACLS-capable hulls carry full deck
data), the `IclsAllocator`, the curated → stored → fallback precedence for all four
resolvers, the nearest-neighbor TACAN degrade, and the flagship-name collision guard.

**In-game pass DONE** (checklist B18): that the CV Operations Data page renders the
curated card (clean Callsign line, 7XX TACAN, 336-band Link 4), and that the boat's TACAN /
ICLS / Link 4 actually radiate on those channels for a Hornet/Tomcat recovery.

---

## §66 — Generated-mission archive

Every turn generates to one fixed path — `Saved Games/DCS/Missions/retribution_nextturn.miz`,
hardcoded at [`QTopPanel.launch_mission`](../../qt_ui/widgets/QTopPanel.py) — so each **Take
off** silently overwrites the mission that was just flown. That is fine for flying and lossy
for everything after it. This fork routinely root-causes its in-game findings *from the flown
mission* alongside its Tacview (the escort pre-join ROE bug, the carrier-recovery midair, the
SCUD no-scoot), and the DM's own `Missions` folder had already grown the manual workaround:
`Red Tide M1.miz`, `Red Tide M1 with Mags happy.miz`, `Red Tide Backup.miz` — hand-copies made
before hosting each event.

**The fixed output does not move.** Nothing downstream ever depended on that name, which is
what makes this cheap: DCS writes `state.json` to a fixed path of its own, and
`DebriefingFilePoller` decides "is this result mine?" by comparing the file's mtime
against `MissionSimulation.miz_generated_at` — never by filename. The wiki (Dedicated Server
Guide, Your First Operation), the bug-report template and every server workflow keep naming
`retribution_nextturn.miz`, and it keeps being exactly what they say it is.

**The archive.** `game/retlab/mission_archive.py` `archive_mission` additionally copies
each generated mission to
`Missions/Retribution Archive/<campaign>_turn<NN>_<YYYYmmdd-HHMMSS>.miz` — e.g.
`germany_1980_red_tide_turn03_20260716-193205.miz`. Notes on the shape:

- **The directory is under `Missions/`**, not the `Retribution/` tree the other RetLab stores
  use (`persistency.mission_archive_dir`), because DCS's own mission browser lists `Missions`
  subfolders — so an archived turn opens straight from the game with no file shuffling.
- **The turn is the raw `game.turn`** — the same 0-indexed number the kneeboard and the §58
  briefing card show, so the filename and the deck inside it agree on which mission this is.
- **The timestamp is what stops the clobber.** Re-generating a turn while re-planning writes a
  *new* archive rather than overwriting the copy of the one that was flown.
- **Hooked in `MissionSimulation.generate_miz`** (not the Qt button) so it is engine-side,
  unit-testable, and covers any future caller.

Two properties it is built around, both tested:

- **It never breaks Take off.** Archiving is best-effort — every failure (unwritable disk,
  `persistency.setup()` never called in a headless test) is logged and swallowed. By the time
  it runs, the generated mission is already written and flyable; a failed *copy* must not cost
  the user the *original*.
- **It only ever prunes its own output.** Retention keeps the newest `KEEP_ARCHIVED_MISSIONS`
  (20) and is scoped by a regex matching only the names it generates, so a hand-named miz that
  ends up in the archive folder is never deleted. Each prune is logged.

Sizing note: a generated mission is dominated by kneeboard images, so it scales with the number
of player-crewed airframes — a solo turn is ~1 MB, a fully-crewed MP event mission ~9 MB. The
keep count is sized off the MP case, so the ring buffer stays under ~200 MB.
`KEEP_ARCHIVED_MISSIONS` is the dial. (The original 40 was sized on a 2 MB solo turn while real
event missions were 22 MB — a ~900 MB buffer. The recon-page JPEG change above cut the 22 MB to
9 MB; the keep count was corrected alongside it.)

**No `Settings` toggle** — the same call as §42 map tiles and §43 flight defaults (on-disk
content is the switch). A toggle you can forget to switch on defeats the one thing this is
for, and the cost is bounded. If the pile is ever unwelcome, `KEEP_ARCHIVED_MISSIONS` is the
dial.

Tests: `tests/retlab/test_mission_archive.py` (naming/slugging, the copy, the
no-clobber-on-regenerate property, the prune's keep-newest + never-touch-foreign-files
safety, and both non-fatal failure paths). No in-game pass needed — there is no DCS runtime
here, only a file copy.

---

## §67 — Weather-aware auto-planning

**What it is.** The theater commander reads the sky. The §47 continuous clock gave the
campaign an evolving weather system, but the planner never consulted it: it fragged TARPS
photo recon into thunderstorms and led its offensive plan with low-level visual attack in
weather that grounds it (`game/commander/` had literally zero references to weather or
time-of-day). `game/retlab/weather_planning.py` is the read — two pure classifiers over
`game.conditions.weather` plus two planner couplings, both applying to BOTH coalitions (it
is the same sky):

**Coupling 1 below was removed 2026-10-12 with the automatic recon flight it gated; coupling 2 is the whole of §67 now.**

1. **Recon stays home in the weather.** `recon_suppressed` gates
   `PackageFulfiller._maybe_plan_tarps_recon`: while it is raining or storming the optional
   auto-added recon bird (the Strike/DEAD BDA pass, the Armed Recon overwatch drone) is
   omitted — optical and IR alike photograph cloud deck, so the sortie banks nothing. Same
   non-scrubbing contract as a missing TARPS squadron; player-planned recon flights are
   never touched.
2. **Storms demote low-level visual attack.** In a `Thunderstorm`,
   `demote_weather_hostile_methods` moves the offensive HTN methods that live at low level
   under the weather — `AttackBattlePositions` and
   `InterdictReinforcements` (the `VISUAL_ATTACK_METHODS` tuple, name-coupled to
   `PlanNextAction._OFFENSIVE_FACTORIES` and lock-tested) — to the tail of the offensive
   order, AFTER the §40 phase / §55 posture emphasis is applied
   (`PlanNextAction._offensive_order` calls it on both the stock and emphasis paths). Soft
   demotion in the §40/§55 discipline: nothing is removed, the planner still services them
   if jets are left after the weather-tolerant strikes claim theirs. Rain does NOT demote
   (only the recon gate fires in rain) — DCS AI flies fine in rain; the storm is the
   grounding sky.

**Deliberately absent: night.** The model carries no per-airframe night-capability data, so
demoting night CAS would wrongly ground an A-10C II alongside an A-1. Night awareness is
blocked on that data existing, not forgotten.

Gated by `weather_aware_planning` (Air Doctrine → Auto-planner behavior, default **OFF since
the 2026-08-09 re-convergence**, the planner-suite preset turns it on —
clear skies are a byte-identical no-op, so the toggle only matters while the weather is
actually bad; every read is getattr-guarded so headless fakes and old saves degrade to
"clear"). Tests: `tests/retlab/test_weather_planning.py` (classifiers, gates, the
demotion's order-preservation + the factory-name lock, the HTN integration) + the storm
case in `tests/test_armed_recon_planning.py`. Checklist B19 — needs an in-game pass (does a
stormy turn's ATO visibly lead with strikes and drop the recon add-ons).

---

## §68 — Adaptive procurement (SAM repair + price-weighted choice)

**What it is.** The AI economy reads the war. `ProcurementAi` was the flattest brain in the
engine — a fixed air/ground budget slider, doctrine-fixed class ratios, and
`random.choice` over whatever was affordable — coupled to nothing built since. `game/retlab/adaptive_procurement.py`
adds two couplings:

1. **Air-defense site repair** (`repair_air_defenses`, its own gate): nothing ever rebuilt
   a dead SAM — the enemy IADS only decayed, so Rollback was a one-way ratchet. Each turn
   the AI commander repairs up to `MAX_AIR_DEFENSE_REPAIRS_PER_TURN` (2) destroyed units at
   surviving `aa`/`ewr` TGOs, paying the **full unit price** (the same pay-and-flip-alive
   repair the player's base card has always offered), prioritised degraded-but-alive sites
   first (restoring a blinded site's radar buys the most capability per dollar), then
   priciest unit first (radars over launchers). It mirrors `TheaterUnit.kill()`'s threat-poly
   invalidation and the Qt repair's wreck-marker cleanup (without which the repaired unit
   spawns next to its own burnt-out model). **Command centers and comms nodes are never
   repaired** — §51/§52 decapitation stays a permanent strategic payoff. Wired into
   `ProcurementAi.spend_budget` after runway repairs, inside the `manage_runways` block —
   so BLUE only auto-spends here when the player has delegated repairs
   (`automate_runway_repair`); RED is always automated. The spend shows in the Finances
   dialog as its own "SAM / EWR site repairs" row (`last_expenses["air_defenses"]`).
2. **Capability-weighted unit choice** (`ProcurementAi.affordable_ground_unit_of_class`):
   the ground-unit buy weights the roll by price — the capability proxy the model actually
   has — so the commander fields its better hardware more often than its gun trucks while
   keeping variety (a weighting, not a max).

Gating: the weighted-choice under `adaptive_procurement` (Campaign Management → Commander
economy, default **OFF since the 2026-08-09 re-convergence** — the planner-suite preset turns
it on); the site repair under `auto_repair_air_defenses` (same section, default **OFF** —
it materially changes campaign difficulty: the SAM belt regenerates unless the player keeps
pressure on it). Not preseeded anywhere (Red Tide is feature-locked). Tests:
`tests/retlab/test_adaptive_procurement.py` (the repair's gate/cap/priority/budget-skip/category-exclusions/wreck-cleanup, the weighted-choice gate). Checklist B20 — needs an in-game pass (red visibly rebuilds a
struck SAM site over following turns with the toggle on).

---

## §69 — Cross-package SEAD-before-strike coordination

**Front-line SEAD escort (2026-09-22, `front_line_sead_escort`, RetLab planner suite).**
Test 37 put four AV-8B SEAD escorts on deep packages; they carry AGM-122 Sidearm and
AGM-65F, fired no Sidearm between them, and one pair died with the Armed Recon package it
covered to an SA-11. The Harrier's job (DM call) is escorting helicopters and A-10s at the
front, but upstream's CAS package asks only for a SEAD Sweep, which the AV-8B does not
fly, and the Harrier's SEAD Escort priority (70 against 450 for the Hornet and Viper) put
it on deep packages only once the HARM shooters were used up. With the gate on:
`PlanCas` also proposes a SEAD Escort, ahead of the sweep; an airframe with
`sead_escort_front_line_only: true` (the AV-8B) may take a SEAD Escort only on a front-line
or helicopter-led package (`Squadron.can_auto_assign_mission`); and at a front line it
ranks first (`AirWing.best_squadrons_for`), which also keeps the Hornets and Vipers for
deep work. Off, planning is upstream's. `tests/retlab/test_front_line_sead_escort.py`;
row B134 owns the fly.

**Front-line radar air defense triggers the escort (2026-09-23, same gate).**
- Test 39 (Graveyard of Empires): the CAS package proposed its SEAD Escort and never got one.
- The need check read only fixed SAM rings over FLOT START → FLOT END. No ring covered them.
- Red's front-line SA-19s fired seven 9M311s. Front-line units are not TGOs, so `ThreatZones` never sees them.
- With the gate on, `PackageFulfiller.check_needed_escorts` also marks `EscortType.Sead` needed when the package targets a `FrontLine` and the enemy control point deploys radar air defense to its fronts.
- "Deploys" is `deployable_armor(cp)`, the same allocation `plan_groundwar` sends forward. It is per control point, not per front.
- "Radar air defense" is a unit type whose class is in `ANTI_AIR_UNIT_CLASSES` and whose DCS type is in `radar_db.UNITS_WITH_RADAR`. Counts: Tunguska, Osa, Tor, Roland, Shilka, Gepard, Vulcan, Pantsir. Does not count: Strela, Avenger, ZU-23, the CH 2S38 (not in `UNITS_WITH_RADAR`; its unit file lists TV/thermal tracking and a laser rangefinder, no radar, so a Sidearm has nothing to home on).
- Needed means the stock escort contract: if a SEAD-capable wing has no escort free, the CAS package is scrubbed unless the doctrine flies unescorted.
- Helpers: `has_radar_air_defense` / `deploys_radar_air_defense` in `game/ground_forces/ai_ground_planner.py`.

**Route around SAMs (2026-09-23, `route_around_sams`, RetLab planner suite).**
JOIN -> INGRESS and TARGET -> SPLIT are straight lines, and the coalition navmesh merges
overlapping rings into one blob it crosses in a straight line, so neither routes round a SAM
inside the blob. Graveyard of Empires turn 1: every deep blue package flew both legs through
SABERTOOTH, a Buk-M3 that covered none of the targets — 2,349 NM of flight time inside its
ring across the ATO. With the gate on, `FormationAttackBuilder._sam_detours` rebuilds the
navmesh without the rings the package must enter anyway (any ring covering the target, or
more than 5 NM inside at a leg's end point; joins sit on the threat edge) and routes both
legs through it (`game/flightplan/samdetour.py`). The points land in the layout's
`ingress_nav` / `egress_nav`, the ingress leg ends at the strike line-up point so every
flight in the package flies the same detour, and `join_time` / `split_time` sum the detour.
A detour more than 2× the straight leg, or no less exposed, is dropped. Same replan: 113 NM.
Not covered: SPLIT -> REFUEL (SKINK DEAD still crosses 23 NM there) and helicopters. Escort
detour points are player-only; AI escorts fly the Escort task off the join.
`tests/flightplan/test_samdetour.py`; row B141 owns the fly.

**TARCAP behind SEAD (2026-09-23, `tarcap_behind_sead`, RetLab planner suite).** Upstream starts a
TARCAP's orbit 2 min before the package's JOIN TOT (`Package.escort_start_time`), but the
racetrack is on the target. Test 40: SARDINE's F-15C TARCAP reached a racetrack 5 NM from
SLUG (SA-11), the target of its own SEAD, at t≈1650; the SEAD sweep's TOT was t=2771. All four
died in 11 s. With the gate on, `TarCapFlightPlan.patrol_start_time` is no earlier than the
earliest TOT of a SEAD, SEAD Sweep, SEAD Escort or DEAD flight in the package. Packages with
none are unchanged. `tests/ato/flightplans/test_tarcap_behind_sead.py`; row B147 owns the fly.

**What it is.** Packages were timed independently — the generic scheduler branch spreads
each package's TOT randomly across the mission window, so nothing stopped a strike from
arriving at a defended target half an hour BEFORE the SEAD package tasked against the SAM
covering it. `MissionScheduler._coordinate_sead_windows` (run inside `schedule_missions`
after the main TOT assignment, BEFORE the §8 carrier-recovery stagger and the
recovery-tanker ETA collection so both see the coordinated landings) finds, for every
movable strike-class package, the SEAD/DEAD packages whose **TGO target's threat ring
covers the strike's target** (`max_threat_range` distance test, duck-typed so a non-TGO
tasking degrades to "no window"), and retimes the strike into the window just behind the
**latest** covering suppressor: `coordinated_strike_tot` opens the window
`SEAD_WINDOW_LEAD` (2 min) after the provider TOT and holds it `SEAD_WINDOW_DURATION`
(8 min) — a naked strike ahead of its SEAD is delayed into the window, one the random
spread had left long after it is pulled back, one already inside keeps its TOT, and
physics always win (never earlier than `TotEstimator.earliest_tot`; an unreachable window
keeps the spread schedule unless that would leave the strike ahead of its SEAD). Several
strikes behind one SEAD mass into the same window — the push is the point.

**The §8 stagger discipline applies.** Movable =
`STRIKE`/`BAI`/`OCA_RUNWAY`/`OCA_AIRCRAFT`/`CAS` (`COORDINATED_STRIKE_TYPES` — Armed Recon is a
loitering sweep, AIR ASSAULT is tied to the ground war's timing; both deliberately stay
spread), AI-only, non-ASAP. **CAS was added 2026-08-24** (#973, the first gap mined out of the
planner-doctrine queue): it descends to acquire and eats MANPADS low, then climbs into the
area-SAM ring high, so a front under a live umbrella wants that umbrella down first exactly as
a strike does. Its organic `SEAD_SWEEP` escort flies the package's own TOT and so accompanies
rather than pre-suppresses. **The CAS case has not had its own in-game pass** — B21 is verified
for the strike case only. A package with a
player flight is never rescheduled — but a **player-flown SEAD still opens a window the AI
strikes push behind** (providers are read-only). The carrier stagger runs after and only
ever delays, so it can push a strike deeper into — never ahead of — its window;
best-effort by design. Symmetric (each coalition's scheduler coordinates its own ATO).

**CAS is not held past the mission length (2026-10-10, DM call).** CAS is based beside its
target, so the DEAD it waits on can be the far one. Northern Flank 1985: Su-25s 88 NM from
the front were held to minute 56 of a 45-minute mission, behind a DEAD package flying 320 NM.
Across the 76 bundled campaigns 12 of 49 CAS packages were retimed and 4 landed past the
mission length. `_holds_cas_past_the_mission` refuses a delay that ends after
`desired_player_mission_duration`; the CAS keeps its own time. Strike, BAI and OCA still
wait, since going in ahead of the SEAD is the worse outcome for them.

Gated by `sead_strike_coordination` (Air Doctrine → Auto-planner behavior, default **OFF since
the 2026-08-09 re-convergence**; the planner-suite preset turns it on).
Tests: `tests/test_sead_strike_coordination.py` (the pure window math end-to-end + the
wiring: ring matching, latest-provider windows, player/ASAP immunity, provider
read-only, massing, the gate, a dead SAM's zero ring). Checklist B21 — needs an in-game
pass (Tacview: AI strikes arrive after their SEAD is on station, not before).

---

## §70 — COMINT collection (blue-side communications intelligence) — REMOVED (2026-09-07)

All of it: the collection tiers, the tasking leak, the concealed-site reveal, the kneeboard
COMINT block and the audible/DF-able red UHF net. `game/retlab/comint.py`,
`rednetluadata.py`, the `rednet` plugin, the three settings and the Desert Storm and
Marianas 2027 preseeds are deleted.

What it was: while the enemy C2 net was emitting, blue drew an ambient take; a collection
sortie (a §2 JAMMING orbit or any drone) that came home unlocked Tier 2 next turn — one
intercepted enemy tasking and one suspected-activity circle snapped to exact. The same C2
nodes were both the intel source and a strike target, so bombing them cost you the take.

Constraints kept out of the deleted design note:

- **The reveal was player-facing only.** It flipped a site to exact on the human's map and
  planning never read it — the §3 viewer discipline. Anything that hands blue a find keeps
  that separation, and gates on the fog (`fogofwar.hidden_from`), never a bare leaf.
- **Net frequencies were held 100 kHz clear of every briefed channel.** A transmitter beside
  a briefed channel is indistinguishable from a broken comms plan.
- **Windows recur with silence between**, so a net reads as traffic rather than a beacon.
  A continuous carrier is a homing beacon, which is a different (and easier) game.

In git history at `git show c08b85de2:docs/dev/design/414th-comint-notes.md`.

## §71 — Expanded F-4E Weapons Pack (AGM-78/-88 Weasel fits)

**What it is.** The upstream Expanded-F-4E-Weapons mod support (dcs-retribution #663 +
#733 — DSplayer's community weapons pack for the Heatblur F-4E,
https://www.digitalcombatsimulator.com/en/files/3338686/), restored to the fork's curated
wizard Mods page and — unlike upstream, which only injects the pylon options for
hand-editing — actually **utilized** by the planner. Of the pack's arsenal (AGM-88C,
AGM-45B, AGM-78A/B, AIM-4D/-9D/G/H, Zuni, Litening…) **the two big ARMs are wired into
loadouts, with the AGM-78B Standard preferred** (user calls 2026-07-18: first "the only
one I actually want is the AGM88", then "include [the AGM-78] and make it the preferred
one" on realizing the pack carries it); the rest stay payload-editor-only, exactly as
upstream left them. The point is the era Weasel: an ARM-armed F-4E is the closest DCS
gets to the F-4G USAFE actually fielded in Germany. **It is the DM's personal option,
preseeded NOWHERE** (user call, same day — the real Red Tide build stays mod-free): the
wizard default is off, and the host checks the Mods-page box by hand on a personal game.

**Why it was gone.** The fork's Mods-page curation ("only mods the factions actually
consume are listed") dropped the checkbox and the `ModSettings` pass-through when nothing
consumed the pack; the `pydcs_extensions/f4e_expanded_weapons/` module, the
`ModSettings.f4e_expanded_weapons` field, and the `faction.py` inject/eject wiring were
never removed — `eject_F4E()` has in fact run on every game since (the always-False
path), which is why restoring the toggle is save-safe and the eject path is battle-tested.

**The mechanism — live pylon tables as the mod signal.** `inject_F4E()`/`eject_F4E()`
mutate the pydcs `F_4E_45MC.Pylon1..13` classes (process-global, re-applied by
`Faction.apply_mod_settings` at generation and on save load), and `Pylon.for_aircraft`
reflects them live — so pylon legality *is* the mod state, no plumbing of `ModSettings`
into the loadout layer needed. `Loadout` (`game/ato/loadouts.py`) grows the
**expanded-weapons payload convention**: a payload named with `EXPANDED_WEAPONS_SUFFIX`
(`" (XW)"`) is tried **first** for its task (`default_loadout_names_for` prepends
`"Retribution <task> (XW)"` for every task — a no-op for every airframe that ships no
such payload) but is picked **only** when `pylons_allow` verifies every store against the
current tables; otherwise selection falls through to the regular name chain, byte-identical
to pre-feature behavior. The same gate hides an (XW) fit from the payload-editor list
(`iter_for_aircraft`) while the mod is off — without it, DCS would silently strip the
un-mountable stores at spawn and the flight would fly a naked Weasel (the failure the
gate exists to prevent; `Pylon.equip` logs but does not refuse).

**The fits.** `resources/customized_payloads/F-4E-45MC.lua` adds "Retribution SEAD (XW)"
/ "SEAD Escort (XW)" / "SEAD Sweep (XW)" — the SEAD fits' skeletons (AIM-7M wells,
AIM-9M rails, 370-gal wing tanks, nothing on the centerline, ALQ-131, ALE-40) with the ARM
stations swapped to the pack's **AGM-78B Standard ARM** (`{LAU_77_AGM_78B}`, the
preferred ARM) on the injected stations: 4 Standards on 1/3/11/13 for SEAD/Sweep, 2 on
3/11 for the tanked Escort fit. The **4× AGM-88C load stays supported** as the
editor-only **"Retribution SEAD HARM (XW)"** fit (stock clsid
`{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}` — the `...C93` entry, not the Hornet-rack
`...C9C` sibling): same mod gate, one click in the payload editor, but absent from every
task's name chain so it is never auto-picked. The Maverick SEAD fits (#1320) remain the
automatic fallback, so Tanker War and any other Phantom campaign without the
mod resolve exactly as before.

**Era + economy come free.** The AGM-78A/B were already first-class weapons-DB citizens
(`resources/weapons/standoff/AGM-78{A,B}.yaml` from the upstream #663/#733 support: dated
at the 1968/1969 service entries, Shrike fallback, the mod's LAU-77 clsids listed, and
per-target seeker-band `target_overrides`, removed 2026-10-22 because each Standard has
one head in DCS; see §8 *Loadouts and module data*), the fork already dates the DCS AGM-88C at
the family's 1984 IOC with an AGM-45 fallback (`AGM-88C.yaml`), and §54 munitions
scarcity already tracks Standards, Shrikes, AND HARMs under the `arm` family. So a
July-1988 game with `restrict_weapons_by_date` on (the Red Tide setup this exists to be
flown in) keeps both ARMs — tripwired in the tests, since a future AGM-88C re-date to
the C-model's literal 1993 would silently disarm the HARM fit.

**Wiring.** Wizard: the checkbox is back on the Mods page Aircraft-modules group
(`QGeneratorSettings` — registered field, DSplayer tooltip with the user-files link,
campaign-seedable via `update_settings` like every mod key) and `QNewGameWizard.accept()`
passes it into `ModSettings` again. **No campaign preseeds it** — the same-day Red Tide
preseed was reversed by user call (it is the DM's personal option; the real Red Tide
build stays mod-free — the no-preseed is pinned in
`tests/retlab/test_campaign_plugin_preseed.py` and recorded in the Red Tide campaign
notes; no authored F-4E squadron either, the air-wing dialog is the path). The F-4E's
SEAD task priority stays the deliberate 120 — the Phantom flies Weasel when fragged by
the host or as overflow, it does not out-compete the HTS Vipers/Hornets for
auto-assignment. NEW game required (mods apply at generation). No plugin, no Lua, no
Settings field (the checkbox is `ModSettings`, the §10 asset-pack pattern).

**Tests.** `tests/retlab/test_f4e_expanded_weapons.py` (inject → every SEAD-family
task selects its (XW) fit with the AGM-78Bs on the exact stations — which doubles as the
pylon-legality pin for the payload file; the HARM fit is offered in the editor and
carries the AGM-88Cs but is never auto-picked; eject → "Retribution SEAD" Shrike
fallback; editor list tracks mod state; other airframes never see the (XW) chain; the
1988 era-gate tripwires for both ARMs) + the Red Tide **no-preseed** pin in
`tests/retlab/test_campaign_plugin_preseed.py`. Checklist B24 — needs an in-game
pass (does the installed mod actually accept the generated stations; AI ARM employment;
the mod-off stripped-stores signature).

---

## §72 — Carrier deck decorations (campaign A deck dressing)

**What it is.** Every Nimitz-family carrier (free Stennis + supercarrier CVN-71/72/73/75)
gets its deck dressed with ship-linked static deck equipment and crew — tow tractors
(AS32-31A/-32A), a P-25 crash truck, a CV-59 Hyster forklift, deck hands, and an
AS32-36A crane in the **island street** (the clear staging strip alongside the island),
plus the four-figure LSO team on the port-aft platform — so the boat reads like a working
flight deck instead of an empty parking lot. The placements are **the campaign author authoring**:
extracted from the 13 missions of campaign A
(`<DCS>\Mods\campaigns\<campaign A>`, the user's install),
which dresses the Truman's deck in every mission. campaign A's raw offsets put the cluster on
the angled-deck **foul-line strip** (rejected 2026-07-21); that fix shoved the cluster
+30 m **forward** into the corral, but the forward corral overshot — the flown feedback
(2026-07-27) was "generating in the **red** instead of the **blue**", i.e. pull it back
aft and tuck it outboard against the island. `CORRAL_SHIFT` now lands the campaign A arrangement
in the island street (~10 m aft of raw / ~5 m outboard of the old corral, preserving the
relative layout, clear of every spot by ≥12 m — the min is 12.7 m at the six-pack row).
The arrangement rotates between **ten** curated variants (missions 1 / 2 / 3 / 4 / 5 / 6 /
9 / 10 / 11 / 12, incl. the M6/M9 crane) deterministically on (carrier, turn) — crc32
seeding, the §70 pattern — so re-generating a turn is stable but consecutive turns vary.
The campaign A mining was **completed 2026-08-07**: all 13 missions re-extracted with a lupa
parser validated against the shipped literals first (12/12 offsets and angles reproduce
mission 3 exactly), 238 ship-linked statics catalogued. Missions 7 and 8 clear the guard
but were left unmined at 4 and 2 in-envelope items — too thin to read as a dressed deck,
now a five-item curation floor with a test behind it. User request
2026-07-18 ("apply them to ALL retribution carriers for flavor — BUT we need all of
the parking spots still usable").

**One tier, standing all mission (DM call, 2026-08-20).** The street gear and the LSO
team are the whole feature. They stand where a deck is never spotted, so the same dressing
is right for both the launch cycle and the recovery cycle and nothing has to be swapped.
Two phase tiers used to exist and both are **removed**, along with the runtime plugin that
swapped them:

- the **launch-phase round-down E-2C** (`carrier_deck_decorations_aircraft`) — a static
  Hawkeye on the stern round-down, struck below before recovery;
- the **recovery-phase bow respot** (`carrier_deck_decorations_recovery`) — deck gear
  spawned forward onto the bow once launches were over;
- the **`deckdecor` plugin** + its `deckdecorluadata.py` emitter, whose only job was the
  strike-below and the one sanctioned spawn.

Both settings are swept from old saves by `_migrate_legacy_settings`, and the `deckdecor`
plugin option keys with them. What that removal costs and what it buys is below, under
*What the phase tiers were, and why they are gone*.

**The hard constraint — every parking spot stays usable, and no static may stand on
one.** The SC manual claims a blocked parking location is skipped (capacity loss);
**flown evidence says worse**: for late-activated groups (Retribution's dominant §64
spawn path) DCS does NOT skip — it spawns the aircraft INTO the static (the CVN-73
A-6-in-the-Seahawks clip, 2026-07-18). So the curation is an evidence-driven filter,
not a copy, and "on a spot" is a hard never. Two envelopes are provably parking-free
and every placement lives inside them:

- **LSO platform sponson** (x −134..−126, y −25..−18): off the deck surface; aircraft
  physically cannot park there. campaign A puts the LSO crew there in all 13 missions at
  byte-identical offsets.
- **Island street** (envelope x −65..−30, y +10..+25): the strip between the landing-area
  foul line and the island, flanked by the six-pack row (y = +34) forward-inboard and the
  aft junkyard/El-3 spots (x < −98). The SC manual's 16-spot layout places no spot there,
  none was ever observed there, and campaign A dresses it in all 13 missions of a flyable
  campaign.

The keep-out evidence: parking spawn spots measured from **Tacview recordings of flown
Retribution carrier missions** (t=0-frame ship-frame transform — parked aircraft only
re-export positions on change, so only same-frame data is valid): six-pack outer row
spots at (+1, +34) and (−11.5, +34) on a 12 m pitch (extrapolated to the row's four),
port-quarter spots at (−84.5, −34) and (−96.5, −34) (the first F-14-capable spots — the
manual's "large aircraft may not be able to use some parking spots" explains the
six-pack skip), and the bow-port helo spot (+58.5, −31.4) where the rescue helo
parks. A 2026-08-17 pass added five more from five CVN-71 recordings, closing the two
holes the 2026-08-07 audit named (nothing was known forward of x = +1.0, and nothing at
all in the 63 m starboard band between x = −35.5 and x = −98.7). `KNOWN_PARKING_SPOTS`
+ a 9 m clearance floor are embedded in the data module and a guard test enforces them
against every table entry, so a future layout edit cannot silently eat a spot. The table
is a **keep-out set** — an extra entry can only reject a placement, never create one — so
two thin entries (n=1, n=2) are deliberately kept. Cats are untouched: the user allowed
blocking one, but a static on a cat is a player-taxi collision hazard while the AI clips
through it anyway (no functional block), so nothing is gained.

**No static aircraft, anywhere, ever — falsified twice.** The feature briefly shipped
campaign A's starboard-aft look as *permanent* statics (a folded-Seahawk pair on the
junkyard spots + an E-2C/S-3B accent on the El-3 shoulder) under the SC manual's "a
blocked parking location is skipped" claim — and the first flown mission **falsified that
claim for Retribution's dominant spawn path**: on a CVN-73 with 30 TOT-delayed (§64
late-activated) deck starts, DCS spawned an A-6E pair **straight into the Seahawk
statics**. The permanent aircraft class was removed the same day. The 2026-08-07 recovery
tier then re-admitted aircraft on the reasoning that they only stood once launches were
over — and **test 11 falsified that too, with measurements**: 14 aircraft late-activated
onto the CVN-71 deck between t=2340 and t=3913, 9 to 35 minutes *after* the recovery set
spawned, five of them onto the six-pack row. There is no hour of a mission at which a
static aircraft on a deck is safe. Their positions survive as **learned spot anchors** in
`KNOWN_PARKING_SPOTS` (the junkyard pair ≈ spots 7/8 + the El-3 shoulder — campaign A
parks aircraft exactly on them, which is how the lesson was bought), and a guard test
asserts no layout ever contains a Planes/Helicopters category static. The parked-aircraft
look comes from Retribution's own real deck population — which the flown decks show is
already rich.

**What the phase tiers were, and why they are gone (2026-08-20).** Both were opt-in and
default-OFF, and both existed to dress zones the permanent tier may not touch.

- The **launch-phase E-2C** stood on the stern round-down, inside `LANDING_AREA_KEEP_OUT`.
  That placement is only survivable if something removes it: the user's screenshot caught
  the first, static version within the hour ("how can planes land with the E2 there?") —
  it cleared every parking spot but stands 5.6 m tall and 17.6 m long essentially at the
  ramp crossing. The plugin's answer was to strike it below (`StaticObject:destroy`,
  silent — the elevator ride) on whichever came first: friendly fixed-wing running in low
  astern, or a fallback timer. **The detection half never became trustworthy.** The astern
  cone was falsified on 2026-07-18 and hardened twice (1 000 ft ceiling, ship-relative
  closing, two-poll debounce, a 400 m deck stamp and a 600 s outbound roster, after the
  Tacview showed the *aft parking rows themselves* were the qualifiers — deck riders read
  as `inAir()` and "close" at exactly boat speed). It still fired once on 2026-08-16 with
  **nothing in the cone**, and a faithful replay of the plugin's own logic over that whole
  recording never trips. That trip source was never identified.
- The **recovery-phase bow respot** was its mirror: gear ranged forward onto the bow once
  launches were over, spawned by the plugin via MOOSE `SPAWNSTATIC:InitLinkToUnit` because
  it must not be on the bow during the launch cycle and so could not be generated into the
  miz. It was the least-evidenced tier in the feature and shipped default-OFF for that
  reason. The one flown outing put three static Hornets in the player's taxi lane, 8.66 m
  off his track, 375 s before his own takeoff roll.

Cutting both retires the whole detection problem — no cone, no fallback deadline, no
launch-cycle floor, no sanctioned spawn, and the plugin's despawn-only invariant is moot.
**The constraint each tier was built around survives in the data module**: nothing may
stand inside `LANDING_AREA_KEEP_OUT` (the E-2's lesson, now with no exemption), and no
static aircraft may stand anywhere (the two falsifications above). Restoring either tier
means re-answering the question that closed them — not just re-adding the table.

**Mechanism.** A ship-linked static serializes across three levels of the mission
format, none fully covered by stock pydcs: `linkUnit` (carrier unit id) on the static
group's first route point, `linkOffset = true` at group level (pydcs-native), and
`offsets = {x, y, angle}` on the unit. `game/missiongenerator/carrierdeckdecor.py`
subclasses `Static`/`StaticPoint` to add the missing two and builds one single-static
group per decoration (the campaign A convention); DCS re-derives linked positions from the
offsets every frame, so the statics ride the steaming boat. World x/y are still
computed properly (ship position + rotated offset off the §65 BRC) so the miz reads
sanely in the ME. Hooked in `GenericCarrierGenerator.generate()`'s flagship block
after the §65 comms/naming pass; every static type is base-game content
(`CoreMods/tech/USS_Nimitz` gear + personnel, `CoreMods/aircraft/F14` forklift — in
every DCS install, no ownership gate). Not registered in the `UnitMap` (cosmetic, no
campaign consequence); no plugin, no Lua, no save-format change — pure generation, so
existing campaigns get it on their next mission without a new game.

**Non-Nimitz decks are deliberately excluded** (`NIMITZ_DECK_HULLS` gate): Kuznetsov,
Tarawa, Forrestal and Invincible have different deck plans with starboard-aft parking
rows where these envelopes are NOT provably safe. Dressing them needs their own
curated layouts against their own spot evidence — a follow-up, not a blind copy.
**Offered and DECLINED (user call 2026-07-18)** — they stay bare.

**Wiring.** One setting: `carrier_deck_decorations` (Mission Generation → Carrier,
default **ON** — the cosmetic-gen kill-switch pattern, §58/§49 precedent). Data:
`game/data/carrier_deck_decor.py` (layout tables + spot anchors + envelopes + keep-out +
the `deck_layout_for` rotation). Generator:
`game/missiongenerator/carrierdeckdecor.py`, called from
`game/missiongenerator/tgogenerator.py`. Tests:
`tests/missiongenerator/test_carrier_deck_decor.py` (parking-spot guard over every
variant, envelope + keep-out integrity, the no-static-aircraft rule, hull gate +
rotation determinism, three-level link serialization against a real pydcs mission).
Checklist B25 — verified 2026-08-06, capacity half closed 2026-08-20.

## §73 — Per-airframe default loadout for a task — REMOVED (2026-10-17)

**Removed 2026-10-17 (DM call), with the user payload folder it wrote to.** From 2026-07-19 a
**Set as default for &lt;task&gt;** / **Clear default** pair in *Edit flight → Payload* saved the
edited loadout into `Saved Games/DCS/MissionEditor/UnitPayloads` under the name the planner
resolves (`Retribution CAS` and so on). Upstream's **Save Payload** and **Create Backup**
buttons wrote to the same folder.

**Why it went:** a saved fit replaced the shipped preset by name for both coalitions in every
campaign. On 2026-10-17 the DM's folder held 23 such fits across 10 airframes, several carrying
AIM-9M and AIM-120B where the shipped fit has AIM-9X and AIM-120C. The era fallback only steps
*down* (`Weapon.fallbacks`), so a fit authored with old weapons stays old in a modern campaign.
The shipped presets carry the newest store the jet can mount and let the date degrade it.

**What went:** `game/retlab/loadout_defaults.py`, `persistency.payloads_dir` and the
`PayloadBackups` migration, the Save Payload / Create Backup / Set as default / Clear default
buttons, `DcsPayload`, `QFlightPayloadTab.on_saved_payload`, and `tests/retlab/test_loadout_defaults.py`.

**What stays:** per-flight editing (*Use custom loadout*), the named-preset dropdown, the §43
fuel and properties defaults, and the files on disk: RetLab never deletes them, and the Mission
Editor still reads them.

**Constraint: RetLab does not register the user's `UnitPayloads` folder** (`qt_ui/main.py`
sets only the fallback directory). Upstream registers it as preferred. Re-adding it brings back
name-shadowing of every shipped preset; a planned flight would again take whatever the user
once saved under that name.

**Saves:** a flight already in the ATO keeps the loadout it was planned with. Flights planned
from the next turn take the shipped preset.

### Payload-tab cleanup shipped with it

A read-the-screen audit of the same tab (user ask, 2026-07-19), in descending order of
teeth:

1. **The `WeaponLaserCodeSelector` AI guard was dead code.** `setDisabled(True)` for a
   non-player member was immediately undone by an unconditional `setEnabled(True)` two
   lines below, so the guard never had any effect — and the "AI does not use laser
   codes" item it added was wrong anyway. This is the *weapon* code (what an LGB seeker
   looks for), not the TGP code: an AI flight dropping LGBs on a JTAC's designation
   needs it, which is why the JTAC codes are in the list. Resolved in favour of the
   working behaviour — the dead guard and the false label are gone, the combo stays
   usable for AI. Its sibling `OwnLaserCodeInfo` *does* disable for AI, correctly (AI
   aircraft do not lase for themselves).
2. **The loadout dropdown read as the stock fit while a custom loadout was loaded.**
   With *Use custom loadout* ticked the (disabled) box showed
   `Loadout.default_for(flight).name` — "Retribution CAS" next to pylons that were not
   Retribution CAS. The selection is load-bearing (unticking the box adopts it), so it
   is **annotated, not changed**: a `(customised)` flag beside the box, with a tooltip
   saying the named preset is what unticking would load. `rebind_to_selected_member`
   also used to call `setCurrentText(member.loadout.name)` — "Custom", matching no item,
   so the previous member's selection stayed on screen — and now syncs through
   `sync_loadout_selector` **with signals blocked**, because selecting an item fires
   `on_new_loadout`, which would overwrite the member's custom loadout with the preset.
3. **Three `QMessageBox.information(QWidget(), ...)` throwaway parents** became `self` —
   the same class as the shared-`self.dialog` window-GC bug the §28 audit fixed.
4. **The laser-code rows showed unconditionally.** Nothing gated them on the loadout
   having any use for a code, so a jet on Snakeyes and Rockeyes was shown an "Assigned
   TGP laser code" row, costing two rows of a cramped scrolling list to say nothing.
   Both rows now live in one container gated on **`Loadout.uses_laser_code()`** — the
   *existing* predicate the kneeboard gates its Laser Code page on, chosen over a
   fresh `WeaponType.LGB`/`TGP` check precisely because it also catches stores whose
   laser use is only visible in their `laser_code` setting (laser Maverick, LJDAM,
   APKWS). Verified against real presets: the stock F-4E CAS fit (Pave Spike +
   GBU-12 ×2) keeps the rows; a Snakeye/Rockeye/Sparrow custom loadout loses them.
   Refreshed on every pylon edit, loadout swap and member change.
5. **Truncated store names got a tooltip.** The §28 `bound_dropdown_width` cap elides
   long names in the *closed* combo ("(Special Weapons Adapter) 2x Mk-20 Rockeye -")
   with no way to read the rest; the open popup keeps its natural width, so a
   widget-level tooltip tracking the current item covers the gap.
6. **The fuel spinner and the §46 fuel-plan line disagreed** — a flown F-4E showed
   "12147" lbs next to "12,149 internal". Two independent conversions from two
   different sources: the spinner rounded the *integer slider* through a locally
   duplicated `LBS2KGS_FACTOR`, the brief multiplied the *float* `flight.fuel` by
   `game.utils.KG_TO_LBS`. Both now convert `flight.fuel` with `KG_TO_LBS`; the
   duplicated constant is gone.
7. **The Edit Flight dialog names its flight** (`Edit flight — [CAS] 2 x F-4E ...`)
   instead of a bare "Edit flight" on every window, matching the sibling
   `QPackageDialog`/`QWeaponSettingsDialog` which already identify themselves.
   `Flight.__str__` is contractually non-raising.
8. **`on_saved_payload` was made idempotent** (saving over a name stacked a duplicate
   dropdown entry). It went with the save buttons on 2026-10-17.

**Deliberately not touched:** the `TACAN Channel Presel` typo is pydcs mirroring the
DCS module data (`planes.py`, alongside `ILS Channel Presel`) — not ours to patch.

### Training and non-combat stores hidden by default (2026-10-06)

Ported from juanjux/dcs-escalation #504 and #505. The Loadout editor has a
**Show training and non-combat stores** checkbox, unticked by default and not saved.
Unticked, each pylon's dropdown leaves out what `Weapon.is_training_or_non_combat`
(`game/data/weapons.py`) flags:

- names or CLSIDs with training, practice, captive, inert, dummy, smoke, illumination,
  ACMI/TCTS, CATM, TGM, Trg, BDU, LGTR, LUU, SAB or travel pod;
- rockets marked SM, IL or TP (smoke, illumination, target practice), and the Hydra
  70 Mk 1 practice round, which pydcs labels "Mk 1 HE". The SM/IL/TP rule only applies
  to rocket stores: TP is also the live Mk-84 AIR's chute, and SM is in missile names.

**White phosphorus is never hidden (DM call).** His #505 filtered `WP` and `Wht Phos`;
we do not, because the §38 FAC(A) marks with WP rockets. pydcs names the M156 WP round
"M156 SM", so `M156` is exempt as well. Coloured smoke marker rockets (S-8TsM, SNEB
Type 254) are still hidden.

The store already fitted on a pylon is always listed, so a preset or saved loadout with
a hidden store shows it; it drops out of the list once replaced. Rebuilding the list
blocks the combo's signals, so toggling the filter never writes the loadout or clears
pylon settings. Classified by name, not weapon group: captive and live missiles share
groups.

Tests: `tests/test_loadout_training_filter.py`, including a scan of every pydcs store
with WP, M156 or Wht Phos in its name. Checklist **B178**.

### GAU-8 ammunition on the Payload tab (2026-10-10)

Ported from juanjux/dcs-escalation #515. An A-10A, A-10C or A-10C II Payload tab has a
**GAU-8 ammunition** box: Combat Mix, HEI or Target Practice. It is enabled with
**Use custom loadout**, like the pylons.

- `game/data/gunammunition.py` — the three choices, as one-based indices into the
  `ammo_type` list in DCS's `CoreMods/aircraft/A-10/A-10A.lua` (the C models inherit it).
- `Loadout.ammo_type` — `None` means the aircraft's default. Carried through `clone`,
  `derive_custom`, `degrade_for_date` and named payloads;
  `__setstate__` supplies `None` for older saves.
- `FlightGroupConfigurator.setup_payload` writes it to the unit's `payload.ammo_type`,
  Combat Mix when unset. Other airframes are not touched.

Tests: `tests/test_gau8_ammunition.py` (one case reads the local DCS install and skips
without it), `tests/qt_ui/test_gau8_payload_editor.py`. Checklist **B210**.

## §74 — Native DTC data pre-population (F/A-18C + F-16C + F-14B(U) + AH-64D)

Design note: [`docs/dev/design/retlab-dtc-cartridge-notes.md`](design/retlab-dtc-cartridge-notes.md)
(the mined format reference — read before touching the JSON shapes). Supersedes the
retired §11: ED's native cartridge shipped, and the revisit condition in that section
("a thin, reliable export") is exactly what this is. Proven working before a line was
written: a hand-built MP mission (Operation Broken Chain, flown 2026-07-18) pre-loaded
every client Hornet/Viper with zero pilot action, and this feature replicates its
mechanism byte-for-byte.

**The mechanism (all native DCS, no Lua, no plugin):** two pieces inside the miz —

1. One pretty-printed JSON cartridge per flight at `DTC/<name>.dtc` in the zip root:
   `{"data": {…sections…}, "name": …, "type": "FA-18C_hornet"|"F-16C_50"|"FA-18E"|"FA-18F"|"EA-18G"}`.
2. A per-unit mission block: `["DTC"] = { ["Cartridges"] = {{default=true, name=…}},
   ["AutoLoad"] = true }`. `AutoLoad` makes the jet ingest the cartridge at spawn —
   nothing to do on the MUMI/DED — and because the cartridge travels inside the miz,
   MP clients get it with the mission download.

**What's in a cartridge** (per **blue client flight** — each flight gets its own route;
package-mates share the comm plan and SA picture):

- **COMM** (Hornet only) — mirrors the channels the radio allocator wrote into the
  unit's `Radio` table (`FlightData.assign_channel`) and names each after what it
  tunes (`frequency_labels`, ≤5 chars): own flight, AWACS and tankers by callsign,
  then `PKG`, `JTAC`, `DEP`, `ARR`, `DVT`. The names are the one thing the miz cannot
  carry. Dropped 2026-09-13 to match the upstream carve
  ([#966](https://github.com/dcs-retribution/dcs-retribution/pull/966)) and **restored
  2026-09-29 on the DM's call** once the names were confirmed visible in the jet; #966
  carries it again since 2026-09-30. The Viper has none: its schema has no name field (dropped
  2026-08-22). The `comms` switch drives this and the F-14B(U)'s TIS list. Row B177.
- **WYPT / MPD.NAV_PTS** — the flight's waypoints as named steerpoints (ASCII-folded
  display names), the Hornet Route-1 sequence with per-leg altitude/speed (km/h) and
  **ETA in absolute seconds-since-midnight** (the Viper carries TOS inline), the
  target waypoint flagged, DIVERT/BULLSEYE numbered but off-route.
- **NAV_SETTINGS** (Hornet) — recovery **TACAN / ICLS / ACLS pre-tuned from the §65
  boat card** (`CarrierInfo.tacan/icls_channel/link4_freq`; a land arrival uses the
  field's `RunwayData.tacan`), FPAS home waypoint = the landing steerpoint.
- **SA / MPD (the situational-awareness picture)** — the boundary with red land
  (`red_land_boundary`; Viper: a GEO_LINES set after the borders, drawings and tanker box),
  **the land borders near the route** (Viper only, 2026-09-29: see below),
  **friendly CAP stations (BARCAP/
  TARCAP) + tanker/AEW&C orbits as CAP_PTS racetracks** (Viper: named extra
  steerpoints — the jet has no orbit element), and **enemy SAM threat rings as MEZ
  threats / THREAT_PTS** ("Custom" type; radius NM on the Hornet, meters on the
  Viper; ≤3-char NATO labels derived from DCS unit ids — `Kub`→6, `S-300PS`→10).
- **The front line is one boundary, not a front per line (2026-09-10).** Two defects,
  both found by reading a paid F-16C campaign's own cartridge (campaign G, which draws
  a single 19-point 384 nm line across its theater):
  - `flot_segments` rebuilt each front from `left_position` + heading + length, which is
    the straight **chord**. §90 rung E bows the front, and `FrontLineBounds.polyline` is
    the bowed trace the F10 drawing (`drawingsgenerator.py`) and the web map
    (`server/frontlines/models.py`) both read. So the cockpit drew a ruler where the map
    the player planned on drew a salient. `flot_segments` now returns `polyline`, which
    fixes all four cartridges at once.
  - Each front went on its own line set, so a theater with several fronts drew
    disconnected 80 km stubs — a picture that cannot say which side is hostile.
    `red_land_boundary` orders the bars (nearest-neighbour from the endpoint farthest
    from their centroid), orients each to start nearest the last, and returns one
    continuous trace split only as far as the display's line budget forces. The gaps
    between bars are joined straight: nothing in the campaign model says where an
    unopposed border runs, and a straight join cannot invent a salient.
  - The Viper's `MAX_GEO_POINTS_PER_SET = 8` was invented. `GEO_LINES.lua:586` caps the
    partition at 25 points with **no per-set cap**, so the boundary takes L1 whole and
    L2-L4 are free for the zone half that nothing writes yet.
- **Viper: land borders first (2026-09-29, row B175).** The DM would rather see
  national borders than the front line, so `_build_geo_lines` fills the four sets in
  priority order: the player's drawings, then `land_border_runs` (up to 2 sets and
  `MAX_BORDER_POINTS` = 12), then the usable tanker boxes (only one beside borders),
  then the red-land boundary (`FRONT_POINTS_WITH_BORDERS` = 4 beside borders, else
  what is left). The caps are the DM's split, 2026-09-29: measured on 7 maps, borders
  near a 100-250 NM route want 16-41 points and uncapped they left the front line a
  2-point stick. **One line per border** (2026-09-29, flown the same day): a border
  that leaves the 40 NM strip and comes back used to come out as two pieces, which
  split the 12 points 10/2 and drew a straight stick with numbered tags (GR2, TU2).
  `land_border_runs` now draws each country pair's frontier from its first to its last
  edge near the route, through the gap, and the 12 points split evenly across the
  borders drawn. Borders and the front line are thinned to fit; boxes and drawings go
  in whole or not at all. **Each line is tagged on the DEST page** (DM 2026-09-29): the
  HSD writes no text on a line (EA guide p328), so a Destination steerpoint beside it
  names it -- `country_code` each side of a border's middle 3 NM out (`country_at`
  picks the side), `FLT` on the front line, the tanker's callsign in its box, the
  player's name in a drawing. `MAX_LINE_LABELS` = 8; the recovery fields keep the
  other 11, and the tags stay when Recovery fields is off. `land_border_runs` reads the §98
  zones (`theater.neutral_border_zones`, terrain file or campaign) and keeps only edges
  **two countries share** — the terrain files are one shared coverage, so an edge only
  one country has is coast or the map's clip edge. It keeps those within 40 NM of the
  route (`BORDER_CORRIDOR_M`), walks each ring into open runs, emits each shared edge
  once, and sorts runs nearest first. Its own DTC-tab switch is `DtcOptions.borders`
  ("National borders"). A map with no border file (Nevada, the Marianas, fictional
  overlays) gets the front line on L1 as before.
- **Viper: a working-area box, and an unticked front line's points (2026-10-08, row
  B193).** DM call: off a CAS flight the front line is noise; the DTC tab's starting
  ticks put Front line on CAS only (#1158), and with it unticked `_build_geo_lines` gives
  its points to the borders, uncapped. CAS, SEAD and SEAD Sweep flights get a closed
  5-point box on the zone the web map draws for them (`FlightData.work_zone`, from the
  flight plan's `ui_zone()`), drawn with the route: the engagement range either side of
  the track and past each end, tagged `CAS` or `SD`. It ranks after the borders and
  before the tanker box, and beside borders and the box the front line keeps
  `FRONT_POINTS_WITH_WORK_BOX` = 3 (DM pick). With two borders and the box, the tanker
  box is left off so the front line keeps a line set (fixed 2026-10-11). Two of the four paid F-16C campaigns
  studied draw a working area this way. The border and threat-ring searches now skip the
  bullseye and divert points, which are not on the route.
- **Tanker and AEW&C orbits as boxes (2026-09-10).** `support_boxes` draws each
  support orbit as a closed rectangle: the straight legs plus the 5 NM the turns
  need at each end, aligned to the orbit's own course. The Viper takes them on
  GEO_LINES L2-L4, the Hornet on the **FAOR lines that shipped empty every time**,
  the Tomcat as `closed: True` plot lines, the Apache as extra TSD lines. The
  orbits were already on the jets as points; a point is not an area, and on the
  Hornet's SA page only the SELECTED CAP point draws its racetrack, so the gas was
  invisible until the pilot went looking. On the Viper the 25 GEO points are shared:
  boxes are allocated first at five each, because a box missing a corner is nonsense
  where a boundary thinned by ten points is still a boundary.
  **Only the tankers this jet can use, nearest first (2026-09-13).** Flown: the
  Hornet draws one FAOR line — the selected one, like its CAP point — and it was the
  AWACS. `support_boxes` now takes the flight and boxes only the `REFUELING` orbits its
  `AircraftType.can_refuel_from` admits, ordered by distance from the flight's target
  (`usable_tanker_tracks`); the AWACS gets no box on any airframe.
- **The Hornet SA page: one item per class, one job each (2026-10-08, DM).** The
  cockpit's own `SA.lua` allocates one CAP racetrack, one corridor (14 points), one
  FAOR line and one FLOT line (7 points each) and 40 MEZ rings, so only the selected
  entry of each list draws. FAOR (dashed) is now the nearest land border within 40 NM
  of the route, else the tanker box; FLOT (solid) is the next border; the front line
  takes FLOT only on CAS. The corridor is the package's lane from the IP over the
  target to the split; a flight with no split after its IP (CAS, Sweep) gets none. `TCN` lists the friendly boats (unit id + route point 1, as the
  editor keys an `ActivateBeacon` task), the home, arrival and divert fields' ground
  TACANs, then the map's other TACANs nearest the route, to the editor's 10. That
  needed beacon positions: `resources/dcs/beacons/*.json` now carry
  `x`/`y`/`elevation` from each terrain's `beacons.lua`. Tankers cannot be listed; the
  editor takes ships and ground beacons only. Row B192. Rationale and the study of
  four paid Hornet campaigns' cartridges: design note, 2026-10-08 section.
- **CMDS (Viper, default OFF)** — `MAN1` dispenses flares only and `MAN5` chaff only, so
  one button answers an IR shot and another a radar one; the three AUTO programs and BYP
  keep the module's own values, written whole because `CMDS.lua` indexes every program
  and dispenser with no nil guard. **`CMDSPrograms` carries the module's per-threat auto
  programs in full (2026-10-08, row B193)**: AUTO 2 against every shooter, NONE against
  search radars and AWACS -- `CMDS_defs.lua`'s own values, and what all four paid F-16C
  campaigns studied ship. Until then it carried an empty `CMDS_Avionics_Threat_Table`,
  which the editor would have compiled from `threat_base.lua`; the jet reads the compiled
  table, so a ticked Countermeasures section most likely left AUTO and SEMI with nothing
  to answer. The table needs each threat's wsType codes, so it is exported from the
  install by `tools/export_viper_cmds_threats.py` into `resources/dtc/f16c_cmds_threats.json`
  (123 threats; matched a 2026 campaign's compiled table on 118 of 120). Re-run it after
  a DCS patch touches `CoreMods/aircraft/F-16C/DTC`.
  **Reverses the 2026-08-18 "no CMDS section" decision on two of its three counts** —
  campaign G's working cartridge puts the section at `data.MPD.CMDS` (settling the
  descriptor-vs-test-file disagreement) and authors two programs away from default
  (settling "it is a defaults file, not intelligence"). The third count stands: the F-16C
  guide warns the CMDS MODE knob must be STBY before an MPD upload, and `AutoLoad` fires
  on a cold jet. Hence default OFF until checklist **B28**'s CMDS check clears.
  **The Hornet cannot take this** — its descriptor has no CMDS section at all (`ALR67`,
  `COMM`, `DL`, `GPS WYPT`, `HARM`, `IFF`, `SA`, `TCN`, `WYPT`).
- **Recon-fog discipline:** threat rings pass `tgo.known_for(flight.friendly)` — the
  same leaf the threat-intel kneeboard uses — so the cartridge never leaks a site the
  player's map doesn't show exactly. Headless-verified on the flown Red Tide saves: turn 1 (nothing scouted)
  emits 0 rings; the flown turn-2 save emits exactly the 5 TARPS-confirmed sites of
  34. **The §18 reveal can no longer leak into generation** (flown 2026-07-19: a
  cartridge carried 40 exact rings on a turn with 0 of 87 sites scouted — the DM had
  the transient "Reveal fog of war" overview ticked, and `known_for` shorts to truth
  for any viewer while it is on): `MissionGenerator.generate_miz` now runs inside
  `fogofwar.fog_intact()`, so every generated artifact — DTC rings *and* the
  pre-existing threat-intel kneeboard, which had the same latent leak — sees the
  real fog whatever the display toggle says, and the toggle itself is restored
  after generation (`tests/test_fog_reveal_generation_leak.py`).
  **This is data discipline, not what the pilot sees.** The FA-18C EA guide (p205)
  is explicit that any air defence unit "placed in the mission, and not to be
  hidden" is drawn on the SA page at its true position with an engagement ring, no
  detection required, cartridge uninvolved — and `Game._reveal_merad_groups` forces
  `hide_on_mfd = False` on every MERAD. So an unscouted MERAD site is on a Hornet's
  SA page regardless. What keeps sites off that display is §7's `hide_on_mfd`, which
  exempts MERAD deliberately. §74's rings add the SHORAD/LORAD picture the jet omits.

**Editor-mined limits honored:** 59 Hornet waypoints / 25 Viper steerpoints, 9 CAP
points, 3+3 FAOR/FLOT lines × 7 points, 40 MEZ / 15 THREAT_PTS, 25 GEO line points
across 4 sets. Two further limits came from the F-16C EA guide (2026-08-18): the
Viper auto-sequences only from **STPT 1-20** (p223), so the flown route caps at 20
and the support anchors take 21-24 -- **25 is the jet's bullseye**, "automatically
configured as such when a mission is loaded" (p325), and a 25th anchor there put the
AWACS orbit under every bullseye readout on test 36; and GEO_LINES owns steerpoints **31-55** with
pre-planned threats at 56-70 (p202), so the point total is capped at 25 rather than
the 32 a fuller line source would have produced. Viper steerpoints also now carry
their HSD sub-type -- **TGT** (triangle) on target waypoints, **IP** (square) on
ingress, `STPT` (circle) elsewhere. **`MPD.DEST` landed the same day**: friendly
recovery fields as Destination steerpoints 81-99 (cap 19), red-held and
non-operational fields filtered out, the briefed divert leading and the rest by
range from the target, labelled with three uppercase alphanumerics. Its own
`destinations` section switch, default on, Viper-only. **`MPD.CMDS` was
investigated and declined** — `CMDS_defs.lua` is a defaults file rather than
intelligence, emitting `CMDSProgramSettings` would overwrite a pilot's hand-set
burst/salvo counts, and the live descriptor (`data.MPD.CMDS`) disagrees with
ED's own shipped example cartridges (`data.CMDS`), so there is no confirmed
shape to emit. Rationale in the design note. **Hornet, same day:** the A/A
(bullseye) waypoint is now designated from the cartridge. It has to BE a waypoint
in the database (FA-18C guide p158) and §74 hardcoded the jet's stock slot 59
switched off, which our routes never reach; it now points at the bullseye §74
already emits and enables it, saving three cockpit presses a sortie. No bullseye
in the plan leaves the stock 59/off. The Hornet guide has **no DTC chapter** —
zero hits for FLOT, FAOR, corridor, MEZ, CAP point or DTC across 424 pages — so
the descriptor stays the only source for the SA sections. **ETA/TOS were wrong
in every cartridge until 2026-08-19:** the ME's own DTC manager bases cartridge
times on `mission.start_time - SummerTimeDelta*3600`, and both jets read them
against a Zulu clock (Hornet TOT p123; Viper System Time p103 beside the CRUS
TOS page p107), but `seconds_of_day` emitted raw local seconds — so every push
time was out by the map's UTC offset, 4 h on Caucasus and 8 h on Nevada. Now
converted through `game.theater.timezone`, based on the mission day's Zulu
midnight so a sortie across 00:00Z still climbs. The kneeboard half was fixed
with it: `F-16C_50.yaml` gained `utc_kneeboard: true` — and **that flag is now on
the Viper and nothing else** (DM call 2026-08-21). It had been on twelve airframes
(FA-18C since 2022, the Super Hornets and EA-18G since 2023, the VSN F-35s since
2026-01) without ever reaching the flight-plan table, so making it work changed
every one of those cards at once; the reported defect was the Viper's card against
its DED, and the other eleven yamls had the line removed. Their BLUF TOT, which
used to print Zulu-only while the rest of the card printed local, is now local like
the rest of it. Upstream keeps its twelve — the divergence is which yamls set the
flag, not the code. **That change claimed the
flag already drove every kneeboard time; it did not, and the card shipped
carrying two clocks (fixed 2026-08-20).** The flag reached the BLUF's TOT and the
friendly-packages page only — the flight-plan table, the Support Info package TOT
and the AWACS/tanker station times still printed the mission clock, because
`FlightPlanBuilder` stored the converted `start_time` and never read it while
`SupportPage.start_time` was read by nothing. Flown on the Persian Gulf (+4): DED
10:38:37, BLUF `TOT 11:12:14Z`, flight-plan row 15:12:14 for that same TOT. The
dead `start_time` parameter is deleted from all three classes. **A Zulu airframe's
card now carries both clocks, not one** — upstream #949's review made the case
that a squadron flying mixed types coordinates off the local figure, so tables
stack Zulu on a second line (`format_kneeboard_time`), the flight-plan Time column
carries it compact on one line (`format_kneeboard_time_compact`, `14:28Z 17:28L`,
Zulu leading because it is the figure the DED shows
— stacking it was flown 2026-08-21 and pushed the Laser Code table off the page;
13 characters is what the column holds before `_fit_col_widths` wraps it, so the
seconds stay in prose, and both figures are labelled because marking only one made
it read as the authoritative time; the local figure is also drawn in `col_nav`
while Zulu keeps the page foreground, via a `highlight` regex on
`KneeboardPageWriter.table` that draws matched runs as separate segments —
`tabulate` renders a table as one block in one fill),
prose parenthesises it
(`format_kneeboard_time_inline`, `15:12:14 (11:12:14Z)`), and the narrow
AWACS/tanker `TOT:`/`TOS:` cells stack it indented under the time
(`_labelled_time`) — parenthesised, that cell wrapped and lost the TOT/TOS
pairing.
Elapsed-time maths still runs on the naive values, so GSPD and dwell are unchanged
(`tests/missiongenerator/test_kneeboard_zulu_times.py`). The cartridge stays
Zulu-only: it is typed into avionics, not read by a wingman.
**A steerpoint's `alt` is the altitude the miz route would have given the jet
(2026-09-13; the 2026-08-20 split was wrong).** Both jets carry two altitude
fields — the point's `alt` and the route leg's `routeAltitude` (Viper) /
`NAV_ROUTE[].alt` (Hornet) — and **the cockpit shows the first**: a Viper flown
2026-09-13 with `alt` 131 ft and `routeAltitude` 22,000 ft on its hold point read
ELEV 131 on the DED. From 2026-08-20 the fork wrote the ground estimate into
`alt` on the reading that the DED showed `routeAltitude`, so every transit
steerpoint read field elevation for three weeks. Now `steerpoint_altitude()`:
the planned altitude on an en-route point, the nearest airfield's elevation on a
ground-marked one (targets, CAS boundaries, flyovers — the miz puts those at
0 AGL for a client flight), the same number in both fields. The ground is DCS's
own `land.getHeight` from `resources/terrain_heights/<terrain>.npz`
(`game/theater/terrainheights.py`, built by `scripts/dcs_terrain_heights.py`,
2026-09-29, row B159); a terrain with no grid keeps the nearest field's
elevation (DM call 2026-08-22); `leg_altitude()` is that plus `altitudeType`, always 1 because nothing
honours the AGL tag (the editor's `transformAltitude` is a no-op). Takeoff and
landing carry B79's field elevation. The Hornet's point is clamped to
`WYPT_NAV.lua`'s -2,000..25,000 ft; the route entry keeps the real number. Orbit
anchors carry the orbit's altitude and threat points the ground estimate. ED's
DTC Manager defaults a *clicked* point to the terrain, which is a UI default, not
the jet's convention — the pre-DTC ME route always filled ELEV from the waypoint
altitude, and the cartridge is that route's mirror. Checklist B90. The .miz was
never wrong: read out of a flown mission, `DEAD on KATYDID` is `alt = 0,
alt_type = "RADIO"`, DCS's own encoding for 0 AGL.
Comm names pre-clamped to the ME's 5-uppercase-alphanumeric filter. **The Hornet's
nine CAP_PTS slots are spent priority-then-completeness** (two flown 2026-07-19
findings): the §6 BARCAP wave relief flies each station as several jittered
flights, and one-racetrack-per-*flight* filled all nine slots with duplicates and
squeezed out every tanker/AWACS orbit — so support orbits go first (the gas can
never be truncated out), then one racetrack per *station*
(`dedupe_stations`: centers within 15 km on near-parallel/reciprocal courses are
one station), then the remaining wave tracks fill whatever slots are left — the
jet draws all nine racetracks it is physically capable of whenever the ATO
overflows, and every wave when it fits (DS91 verified: 13 waves + 3 support →
9/9 slots — 2 tankers, AWACS, 4 stations, 2 extra waves). **The SA page
DISPLAYS one CAP point at a time — the selected one** (third flown finding,
same day: a 7-entry cartridge drew exactly the `Default_CAP_Point` orbit;
the entry list is a library the pilot flips through on the jet's DTC/SA CAP
selection). Two answers: `Default_CAP_Point` is now chosen per flight (a
BARCAP/TARCAP flight pre-selects its **own station**, matched by orbit
center; everyone else gets entry 1 — the first tanker, given the emit
order), and the **whole friendly orbit picture moved to the display that can
actually show it at once: the §45 F10 drawings now also paint each blue CAP
*station*** (deduped, thin racetrack + a "CAP &lt;callsign&gt;" label,
alongside the thicker tanker/AEW&C capsules;
`DrawingsGenerator._generate_cap_station_orbits`,
`tests/missiongenerator/test_cap_station_drawings.py`).

**Implementation:** `game/missiongenerator/dtc/` — `cartridge.py` (the model + the
two pydcs seams: an idempotent `FlyingUnit.dict` wrap emitting the `DTC` key for
units carrying `retribution_dtc`, and a post-save zip append for the `DTC/` files),
`common.py` (extraction helpers), `hornet.py` / `viper.py` (per-jet builders),
`generator.py` (`DtcGenerator`, wired in `missiongenerator.py` after the drawings
pass + after `mission.save`). Both hooks are best-effort — a failure logs and leaves
the pre-feature miz. The F-14B(U) (`F-14BU`, 2.9.28 — not the F-14B) is the one
remaining stock jet DCS marks DTC-capable. **CH-47F and the MiG-29 Fulcrum are
not**, whatever their descriptor folders suggest: the Chinook sets `DTC = false`
and the Fulcrum is an AI-only module with no cockpit (checked 2026-08-22, see the
design note's table). The clean first-class seams are PR'd to `dcs-retribution/pydcs`; when the
pin moves, `cartridge.py` shrinks to the model + builders.

Gated `dtc_data_cartridges` (RetLab Features → Cockpit & kneeboard, default **ON** — the
kill switch; OFF is byte-identical output). Tests
`tests/missiongenerator/test_dtc.py` (shapes, fog, mirroring, the pydcs seams, a
real miz round-trip through pydcs load). Checklist **B28** — in-game pass DONE:
AutoLoad on our §64 spawn paths (uncontrolled carrier clients, late-activated
delayed flights) is the genuine unknown; the reference mission's jets were ordinary
ramp starts.

**Planner controls (the Edit Flight → DTC tab, landed same day):** each DTC-capable
client flight carries `Flight.dtc_options` (`game/ato/dtcoptions.py` — pickled with
the save, `__setstate__`-defaulted so old saves behave pre-feature): a **tri-state
master** (follow the campaign setting / always / never for this flight — the
per-flight override beats the global toggle in both directions) plus **six section
switches** — the F-14B(U)'s TIS list, route steerpoints + push times, recovery aids
(TACAN/ICLS/ACLS + FPAS home), the front line (FLOT), friendly CAP/tanker/AWACS
orbits, and the enemy SAM rings. A section that is off is **omitted from the
cartridge entirely** (the jet's own defaults stand); all sections off builds no cartridge at all. The Edit
Flight dialog grows a **DTC tab** (`qt_ui/windows/mission/flight/QFlightDtcTab.py`,
added in `QFlightPlanner` only for airframes in `CARTRIDGE_BUILDERS`) whose combo +
checkboxes write the options live; the contents group greys whenever the resolved
state is off. Threaded `Flight → FlightData.dtc_options → DtcGenerator` (per-flight
resolve replaces the generator's global gate) and honored inside both builders.
Tests: the override/omission/pickle cases in `tests/missiongenerator/test_dtc.py` +
the offscreen widget behavior in `tests/test_dtc_tab.py`. The tab itself needs an
in-app eyeball (B28's app-side bullet).

**Pilot loads it is the default (2026-09-29, DM call):** `DtcOptions.auto_load` defaults
to `False`, so a new flight's cartridge is bound with `AutoLoad = false` and waits on the
DTC page. Load at spawn stays one choice away on the tab. Row B172.

**CJS Super Hornets — REMOVED 2026-08-22 (DM call).** FA-18E/F and EA-18G took a
cartridge from 2026-08-02 to 2026-08-22 on the Hornet's COMM/WYPT schema, because the
mod's descriptors `dofile` ED's own FA-18C implementations. Removed on the
double-work audit (design note, *What the miz already delivers*): the mod's `data`
table has no `SA`, so the cartridge could carry nothing the jet does not already get
from the miz — the radio presets are written into the unit by upstream's channel
allocator, and the route is the flight plan. The builder, its registration and its
tests are gone (`git show c67783176:game/missiongenerator/dtc/superhornet.py` to
read it); the one constraint worth keeping is that a re-add must re-mine the mod's
descriptor first, since CJS can change it between releases. Checklist B28's CJS
bullet is closed.

**F-14B(U) — the Tomcat (added 2026-08-22).** `game/missiongenerator/dtc/tomcat.py`,
registered on DCS type **`F-14BU`**. Not the Hornet schema and not a variant of it:
the descriptor (`CoreMods/aircraft/F14/DTC/F-14BU_DTC.lua`) declares four sections —
`NAV`, `JDAM`, `CMDS`, `TIS` — and a `data` table with `cartridge_name` where the
other jets have `terrain`. Only the **(U) rewrite** is capable: `F14/Entry/F-14B.lua`
sets `DTC = rewrite_settings.Name == "F-14BU"` and `setData` refuses any other
`type`, so the plain F-14B and every F-14A stay unregistered.

**Plan 1 of `data.NAV`'s twelve is not ours to write.** It is the *mission editor's*
route — the panel says so and `updateNAVPlanEditability()` greys its waypoint fields
out — and Retribution's flight plan already **is** that route. The flown route goes on
**plan 2** with `route_as_line`, waypoints carrying Zulu TOTs and names
ending in the jet's own codes (`XIP` ingress, `XHB` recovery field). Plan 1 takes the
reference layer, which plan 2 repeats:

- `lines` — the front line, one per active front (same `flot_segments` geometry as
  the Hornet's FLOT and the F10 drawing).
- `additional_points` — bullseye and divert named with the jet's own suffix codes
  (`XB`, `XD` — the NAV tab documents the grammar), then the tanker/AEW&C and CAP
  anchors, then the recon-confirmed SAM sites, capped at the descriptor's declared
  20 references.
- `JDAM.stations` — the flight's target waypoints as pre-planned aimpoints, with
  the run-in heading from the IP, the IP leg's altitude and speed as the release
  parameters, and the three cached LAR scalars. **Each station carrying a JDAM gets
  its own target as PP1** (read from the lead's loaded pylons — pydcs 4–7 are the
  jet's STA 3–6), handed out in route order and wrapping; every target stays on
  every station for a re-pick. All targets in a cluster run in from the IP.
  Strike and DEAD plan one site waypoint carrying its units (2026-09-29, row B174);
  the JDAM page expands it back to one point per unit (`_aimpoints`).
  Only **one** target reaches the route -- the surface target -- because a strike
  used to plan a waypoint per building and the PTID displays 18 at a time, ranking the
  coded points above plain ones (DM call 2026-08-23; the manual's prioritisation
  scheme is in the design note). Every remaining plain point takes a priority slot,
  `X1`-`X7` in route order, so it ranks with the coded ones; that code literal is
  read off the NAV tab's help text and is the one emitted code with no authored
  cartridge behind it.
  `JDAM_LAR_TABLE` and its bilinear lookup are ported into `tomcat.py` because the
  CDNU reads those numbers straight out of the cartridge.
- `TIS.send_to_callsigns` — the package's other flights, 6-char blank-padded.

**Two unit traps, both mined:** NAV elevations are **feet**
(`metersToFeet(getAltitude(...))`) while JDAM target elevations are **metres**; and a
waypoint carries `spd` **or** `tot`, never both. **All four sections are always
written, `CMDS` as ED's stock table verbatim** — this descriptor's post-import
refresh indexes every section, and omitting `CMDS` crashed it in the ME (the
2026-08-22 import; `dcs.log` line in the design note). An off section carries the
editor's reset state. Section toggles ride the same Edit Flight → DTC tab, with a
new **Pre-planned target points** checkbox (`DtcOptions.jdam_targets`); `nav_aids`
and `destinations` have no Tomcat equivalent and are ignored.

Unlike the Viper, the F14 descriptor ships **no `defaults/` example cartridge**, so
the shape was mined from `setData`, the element constructors and the editor panels —
then **diffed against a hand-authored F-14B(U) cartridge** (the squadron's
training-night package). Every section's key set matches, an unused JDAM slot comes
out byte-identical including all three `lar_*` floats, and the reference's own plan 1
is empty-named with zero waypoints while its route sits on plan 2 — which is where
the plan-2 behaviour and the name codes came from. Tests `tests/missiongenerator/test_dtc.py` (14 added: registration and
the F-14B exclusion, plan 1 left to the ME route, the plan-2 route with its codes
and TOTs, the front line, fogged threat points, the reference cap, the JDAM
stations and empty slots, the two elevation units and the single-field altitude
rule, the LAR corners, TIS package membership, per-section omission, generator
binding). In-game pass:
checklist **B91** — its first step is an ME import, which needs no sortie.

**The F-16C ROE table (added 2026-08-26).** The 2.9.29 patch's ROE tab reads a
per-type sovereignty table (`MPD.ROE`), and the campaign is the one thing that can
fill it: `game/missiongenerator/dtc/roedata.py` derives the 48-row Air Target Data
Table from both coalitions' air wings — a family only blue flies is FRIENDLY (1),
only red HOSTILE (2), flown by both or nobody UNKNOWN (3, the jet's own default).
The family-level collision rule is the point: one side's variant can never declare
the other side's variant of the same family friendly. Rows carry **only**
`{group_name, sovereignty}` — the jet's `make_ROE_table` compiles membership from
its own `threat_base.lua` and reads nothing else from the cartridge, which also
resolves the wsType families (F-15C, MiG-23, E-3…) jet-side. The repo's membership
mirror exists only to *derive* the verdicts and is pinned to pydcs by
`test_atdt_ids_all_exist_in_pydcs`, so a DCS rename fails loudly. The enum was
settled the day the tab shipped: DM-set rows in the ME's editor, corroborated by
`ROE_defs.lua`'s own `sovereigntyName` table. Toggle: **ROE air target table** on
the Edit Flight DTC tab (`DtcOptions.roe_table`). Pre-datalink campaigns cap red
declarations at a yellow Suspect (Mode 4 needs TNDL); the payoff there is the green
friendlies, which is the blue-on-blue half. In-game pass: checklist **B104**.

**The AH-64D cartridge (added 2026-08-26).** `apache.py`, the fourth builder on the
same pattern, from the 2.9.29 DTC (schema:
`CoreMods/aircraft/AH-64D/DTC` + an ME-saved sample; the shape audit is in the
DCS-update note §3). Emits `NAV.Mission_1`: the route as **WPTHZ** waypoints
W01–W50 (name in `note`, ground elevation, map metres), the **ALPHA route** over
them in the editor's own element shape (`{num, alt, speed kts, dist m, eta s,
fix}`, ETA anchored on the first TOS), fogged enemy SAM sites as **TGT** points
T01–T50 (site name in `note` — the TSD draws no ring, so no radius exists to
carry), and the FLOT as TSD **Lines** (`type_num` 6). Everything the planner
computes nothing for ships as the sample's empty skeleton (Zones/Areas/CTRLM) or
is omitted (Laser, Radios, Weapon, MISC, Presets, IDM) so the aircraft's defaults
stand — the Viper precedent. **ADF is deliberately empty**: the sample's `Freq`
integers carry no stated unit, so the CSAR beacon slot (G33) waits on a flown
round-trip. Old saves are safe: `DtcOptions.__setstate__` defaults any field the
pickle predates. In-game pass: checklist **B105** — the risk it exists for is the
DTU loader indexing a partition the cartridge omits.

**Ticks by task and the saved default (added 2026-10-08, DM calls).** A new flight's
`DtcOptions` comes from `DtcOptions.for_task(flight_type)`
(`game/ato/dtcoptions.py`): the front line is ticked on CAS alone; SEAD, DEAD, SEAD
Escort and SEAD Sweep write every known site; BARCAP, TARCAP, Intercept and Sweep
write only sites whose ring is `LONG_RANGE_RING_NM` (15 NM) or wider
(`long_range_rings_only`); strike, BAI, CAS, OCA, anti-ship, Armed Recon and fighter
Escort write sites within `ROUTE_RING_RADIUS_NM` (40 NM) of the route. Everything
else starts as before. `Flight.__init__` then overlays the player's saved default for
that airframe and task (`game/retlab/dtc_defaults.py`, `Retribution/dtc_defaults.json`,
keyed `"<dcs id>|<task>"`, blue fresh flights only, a broken file is a no-op), written
by the DTC tab's **Save as my default** button. The on/off override is never saved.
Flights already in a save keep their ticks. Tests `tests/retlab/test_dtc_defaults.py`,
`tests/test_dtc_tab.py`. In-game pass: checklist **B194**.

## §75 — Custom victory conditions

Design note: [`docs/dev/design/retlab-victory-conditions-notes.md`](design/retlab-victory-conditions-notes.md)
(the Discord ask — Ramius007's victory CPs / domination threshold + Starfire's three
concrete conditions — and every semantics decision). The stock win condition is
literally "the enemy owns zero control points" (`Game.check_win_loss`), which forces a
limited war ("liberate Abkhazia") into total conquest. This is the shallow, legible
alternate-endings layer over that default. (The deep authored will-meter /
negotiation-ending layer — the Vietnam W1–W2 arc — was REMOVED 2026-07-21, so §75 is now
the only alternate-endings layer over the stock territory default.)

**Two tiers, one engine** (`game/retlab/victory.py`):

- **Authored:** a campaign YAML `victory:` block (a top-level campaign YAML block) with
  `description` + `win_when`/`lose_when` condition lists. Vocabulary:
  `capture_cps` (ALL named CPs blue), `lose_cps` (ANY named CP red),
  `territory_above`/`territory_below` (fraction of non-neutral CPs),
  `destroy_targets` (ALL named TGOs fully dead; case-insensitive; a name matching
  nothing can never fire), `destroy_categories` (no red-owned TGO of the category
  alive AND the turn-0 baseline counted ≥1 — no vacuous wins on campaigns that never
  fielded the class), `enemy_air_below`/`enemy_ground_below`/`friendly_air_below`
  (strength vs the campaign-start baseline; an empty baseline never fires),
  `enemy_air_denied` (no red CP with `runway_is_operational()` — cratered fields and
  sunk carriers are denied, FOB helipads count as air power, a red off-map spawn makes
  the condition unreachable by construction), `min_turn` (guard), `label` (display
  prefix). (**The will/supply meter fields —
  `blue_will_below`/`red_resolve_below`/`enemy_supply_below`/`friendly_supply_below` —
  were REMOVED 2026-07-21** with the will/war economy; only the
  territorial/destroy/strength/air-denial conditions remain.) Parsed by `parse_victory`
  on the S5 **rederive-never-pickle** rule
  (`_PROFILE_CACHE` keyed by campaign name; any lookup/parse failure degrades to "no
  profile" with a log). Parse fails loudly (unknown keys, empty entries, bad
  fractions raise) so a broken campaign dies in tests.
- **Generic: removed 2026-10-12 (DM call).** Two opt-in sliders
  (`alternate_victory_domination`, `alternate_victory_attrition`) synthesized a domination
  and an attrition win on any campaign. Both sat at 0 in the DM's defaults and every save.
  An authored block can still express either (`territory_above`, `enemy_air_below`).

**Semantics — requirement, not trigger:** a victory entry is a
*requirement* — EVERY field set on one entry must hold (AND within the entry), and
the `win_when`/`lose_when` lists are OR (any fully-met entry ends the war). That is
what makes `min_turn` a guard instead of nonsense.

**Evaluation:** `victory_verdict` is the **single alternate-endings branch** in
`Game.check_win_loss`, ahead of the stock territory defaults (which remain for every
campaign with nothing configured — alternate conditions ADD to the stock endings,
never replace them). It evaluates the authored/knob conditions with loss precedence
throughout (a simultaneous collapse is never a cheap win). (**The W2
negotiation-verdict absorption + the will/supply meter conditions were REMOVED
2026-07-21** with the will/war economy.) Ground truth (`viewer=None`), turn
boundary only, zero planner coupling (the §17 boundary). A met
authored/knob condition is announced once (`game.message`, latched on
`game.victory_announced`) so the generic Victory!/Defeat! dialog always has a "why"
beside it in the events feed.

**Invert Sides (2026-10-17).** A block is written for its campaign's own blue side, and
New Game's Invert Sides makes that side red. `game.sides_inverted` (set by `GameGenerator`,
default False on old saves) makes every entry read for the author's side, swaps the lists
(the author's `win_when` is the player's defeat), mirrors the prose ("The enemy takes
Stanley"), and drops the authored `label` and `description`, which speak for the other side.
Before this an inverted game could end on turn 1: a `lose_cps` field the author's side held
at the start was red-owned from the first turn.

**The baseline:** `VictoryBaseline` (red/blue air, red and blue ground, red and blue per-category
TGO counts) latched unconditionally in `initialize_turn` (turn 0 for a new game; first
load for a pre-feature save — the accepted `PhaseBaseline` migration), so a knob
flipped on at turn 20 still measures against the earliest state this build saw.
Persisted on `game.victory_baseline` (getattr-guarded).

**Surfacing:** a green **VICTORY chip** on the campaign-status ribbon (renders
whenever any conditions are configured; its own expander toggle, so it works with
`campaign_phases` off) opening a "Victory conditions" block in the arc expander —
"Any one of these ends the war:" + "Defeat if:" with live-value prose per entry
("Enemy air force below 10% of start (now 62%)", "Capture Sukhumi, Gudauta (1/2
held)") in the objectives tick styling (`CampaignStatusJs.victory` /
`victory_description` → `VictoryConditionJs`; `client/src/components/campaignstatus/`).
The same prose rides the SITREP band (`Sitrep.victory_lines`, capped at 4 + a "+N
more" line, recorded by `record_sitrep`) — so the kneeboard band, the web LAST TURN
panel, and the Qt debrief box show victory progress for free (§29 parity).

**Deliberately not in v1:** raw loss-count defeat, sustained-for-N-turns qualifiers on
transient conditions, per-campaign ending prose, planner pursuit, preseeds (no shipped
campaign changes behavior). **Upstream carve:** prime candidate — Starfire has an
upstream FR for exactly this; the core (module + `check_win_loss` branch + knobs) has
zero fork couplings. Carve after the in-app pass, the §63/§65 pattern.

Files: `game/retlab/victory.py`, `game/game.py` (branch + baseline latch +
`victory_baseline`/`victory_announced` attrs), `game/settings/`,
`game/sitrep.py` + `game/sim/missionresultsprocessor.py`,
`game/server/game/models.py`, `client/src/components/campaignstatus/`,
`client/src/api/_liberationApi.ts` (hand-added types). Tests
`tests/retlab/test_victory.py` (30: parse/evaluation/verdict/precedence/latch/
overview + the real `check_win_loss` branch order driven duck-typed). Checklist
**B29** — needs an in-app pass (ribbon block + a knob-driven ending end-to-end);
needs the CI client rebuild.

## §76 — CTLD paratroopers (fixed-wing air assault)

Air Assault has been helicopter-only since the Anubis Hercules-mod purge (#53) —
the purge deleted the mod that flew fixed-wing assaults, and the C-130J-30 yaml
has carried `# Air Assault: 0 #TODO: Add once we have proper support for
paradrops` ever since. This is that support: **fixed-wing troop transports fly
Air Assault by paradrop**, for both the human C-130J-30 pilot and AI transports.
Planner/Lua split: Python decides who can jump and where; the CTLD config layer
executes the drop.

**Planner** (`game/ato/flightplans/airassault.py`): the Builder gate is now
"helicopter OR troop transport" (`unit_type.cabin_size > 0` — the CTLD cabin
capacity, so any airframe with authored cabin space qualifies; a cabin-less
fixed-wing still raises `PlanningError`). A fixed-wing flight **preloads** (no
pickup zone — it joins the carrier/LHA/off-map preload branch; `preload` was
already forced for non-helos in `LogisticsGenerator`) and keeps **no drop-off
zone**; instead the CTLD assault-area waypoint — for helos a player-only CTLD
implementation detail — becomes a **real AI run-in at 1,000 ft AGL**
(`only_for_player = False`, `alt = feet(1000)`, RADIO; the same shape the old
Hercules branch used), so the AI actually overflies the target zone the
`LogisticsGenerator` already creates (2,500 m wpZone). `tot_waypoint` for
fixed-wing was already `targets[0]` (written for the Herc, never removed).
Campaign C-130J squadrons are near-universally
`primary: Transport, secondary: any`, so on a NEW game the auto-planner can (and
will) frag C-130 airborne assaults where they out-range the helos; def-generated
squadrons auto-assign everything the airframe is capable of, same effect.

### Air Assault priorities

`priority_list_for_task` sorts these descending and the planner picks from the
top, so they decide which airframe flies an assault. Fixed-wing transports sit
below the assault helos (C-130J-30 40, An-26B 25, C-47 20, C-17A and IL-76MD 15);
range is checked separately, so a transport still wins when no helo can reach.

**One rotary value changed, 2026-08-09: `Mi-8MT` 40 → 60**, matching the UH-60A.
It is red's assault helicopter but ranked below the scout helos, so red assaults
went to whatever else was in range.

A full re-tiering of every rotary type was built and reverted the same day (user
call — overthinking). **Do not rebuild it.** The rest of the ladder is a balance
question, not a defect; if a value looks wrong, change that one value.

**Runtime** (`resources/plugins/ctld/ctld-config.lua` — the Retribution-owned
config layer; CTLD.lua itself is untouched): the emitter marks each transport
type `paradrop` (fixed-wing + `cabin_size > 0`, computed Python-side in
`luagenerator.py`) and the config builds `ctld.paradropUnitTypes` plus a
pilot→target-zone release plan from the flights it already parses.

- **Player path:** `ctld.unloadExtractTroops` is wrapped (the same
  config-override seam as the `ctld.inAir` CH-47 fix — captured at menu-build
  time, so the stock F10 **"Unload / Extract Troops"** button *is* the jump
  command): airborne + paradrop type + troops aboard → `ctld.paradropTroops`;
  grounded unload, extraction, and every helicopter path fall through to stock
  CTLD byte-identically. A **player jump ceiling** (3,000 ft AGL) refuses a
  too-high drop with a message; the AI is exempt (its run-in is planned at
  1,000 ft, and a terrain-forced high crossing must still deliver).
- **The drop itself:** the stick leaves the aircraft immediately (cargo
  cleared, `adaptWeightToCargo`, coalition "paradropped troops" call) and the
  troop group ground-spawns at the **velocity-projected drop point** (2 s
  forward throw) after a **real static-line descent delay** (AGL ÷ 6.5 m/s,
  capped at 90 s) — so a transport shot down *after* the drop still delivers,
  and one shot down *before* it never does. The landing reuses CTLD's own
  bookkeeping verbatim: `spawnDroppedGroup` (which sends troops inside an
  active wpZone marching to the zone centre — the existing air-assault capture
  behavior — and otherwise at the nearest enemy), the JTAC-stick laser start,
  the `droppedTroopsRED/BLUE` ledgers, and `processCallback`. **No phantom
  spawns**: the group comes out of the aircraft's CTLD cargo exactly like
  every helicopter unload, and its losses/kills record natively.
- **AI path:** a 5 s release loop drops an AI transport's stick when it
  crosses within 1,200 m of its own air-assault target-zone centre (min'd with
  the zone radius) — one drop per sortie, players never auto-dropped, helos
  never in the plan.
- **Preload retry:** the old one-shot `preload_troops` at t+5 s silently
  missed TOT-delayed flights (late activation, §64), so an AI C-130 could
  arrive over the zone **empty**. It now retries every 30 s until the
  transport exists (~2 h give-up), loading exactly once.

**EW de-confliction:** `_ew_excluded_c130j_groups` now denies the c130j EW/ISR
plugin to **TRANSPORT and AIR_ASSAULT** C-130J-30s alongside the Combat SAR
King — a paradrop bird (or a cargo airlifter, a pre-existing gap) flies the
CTLD menus, not the EW station; a co-present JAMMING C-130J keeps its systems.

**The rest of the hauler fleet landed 2026-08-09** (the v1 note deferred An-26B
and Il-76 as "a separate call" — this is that call). `C-47`, `An-26B`, `IL-76MD`
and `C-17A` all had the same defect: a `Transport:` task and no `cabin_size`, so
they defaulted to a zero cabin and the Builder gate rejected them. All four get
`cabin_size: 24` — CTLD's largest loadable group is `Retribution Troops (24)`, so
a smaller cabin silently caps the airframe at the 12-troop group, and all of them
carried far more in service (C-47 28, An-26 ~40, C-17 102, Il-76MD 126).

The reach is mostly red: **50 red factions field the Il-76MD**, the VDV's own jump
platform, and before this they had no fixed-wing airborne option at all. The C-47
gives the 1944 factions airborne assault for the first time — they field no
helicopters, so it is their only Air Assault platform.

**Deliberately excluded, and pinned by a test so it is not "fixed" later:** the
An-30M (glazed-nose aerial survey variant of the An-24), the C-2A Greyhound
(carrier onboard delivery) and the Yak-40 (light airliner). Each declares a
`Transport:` task, so each reads like an oversight; none carried paratroops.
Also skipped: the A400M and V-22 (fielded by no faction) and the C-5
(strategic-only in practice).

**Still not done:** chute visuals (vanilla DCS has no spawnable parachutist
object; the descent delay is the model), vehicle paradrop (LAPES), and wind drift.

**Side effect worth knowing:** `LogisticsGenerator` runs for TRANSPORT flights as
well as AIR_ASSAULT, so a positive `cabin_size` also flips these airframes to
`troops=true` in the CTLD transport table — they become troop-capable CTLD
transports on Transport missions, not only on assaults.

### The AI leg, flown 2026-08-11 — and the three defects it exposed

**Both legs are verified** (checklist **B30**). The AI drop releases over the target
zone, the stick lands in the right place, and DCS fired its own base-captured event at
FOB Nawa with a blue `Soldier M4 GRG` as initiator — the dropped troops genuinely took
the objective.

Getting there needed in-plugin diagnostics, because every gate in `check_paradrop_ai`
failed **silently**: nothing distinguished "no troops aboard" from "the loop never
armed". Each gate now names itself once per unit with a 60 s throttle, and the AI plan
(or `AI plan EMPTY`) is logged at config time. That is what made one flight sufficient.

Three defects the flight exposed, all fixed:

- **The diagnostic throttle compared whole messages**, but the `inbound` line carries a
  live distance, so no two ever matched and every poll logged — thousands of lines a
  mission under time acceleration. Throttles on a reason key now.
- **`ctld.checkAIStatus` re-loads any empty AI transport standing in a pickup zone every
  2 s.** A C-130 that has already dropped is empty and often parked in one, so it
  reloaded forever and announced each one coalition-wide. `loadTroopsFromZone` is wrapped
  to refuse for AI paradrop types — one drop per sortie, no field reload.
- **Fixed-wing assaults fragged two-ship** when one aircraft paradrops the whole stick.
  Clamped to single-ship in `assault_flight_size` once the squadron is known; helicopters
  keep multi-ship because their lift is per airframe.

**Objective range is capped** at `AIR_ASSAULT_MAX_REACH` (100 NM), measured to the
nearest friendly control point. Fixed-wing eligibility let a C-130 volunteer for
objectives across the theatre — an Afghanistan turn-2 ATO fragged Bagram→Kandahar at
269 NM, 177 NM behind the nearest friendly base. Helicopters could never reach that far,
so the unbounded list only became a problem under §76.

**The cap must not empty the ground war's table (fixed 2026-10-10).** `TheaterState`
builds `enemy_battle_positions` from the same list, and `BreakthroughAttack` looks up its
own front's enemy base in it. A front over 100 NM long (Bardufoss to Alta, 116 NM) had no
entry, so the side with 2 to 1 on the ground there raised `KeyError` and the turn could
not be planned. Nine bundled campaigns start with such a front.
`battle_position_bases` now adds every front line's enemy base; `vulnerable_control_points`
still reads only the capped list, so air assault is unchanged.
`tests/commander/test_battle_position_bases.py`.

**Still open:** the capture did not commit to the campaign. `state.json` carried
`…||2||FOB Nawa` and replaying it through `Debriefing.base_capture_events()` returns the
correct event, but the live `commit_captures` ran empty — apparently against a stale
debriefing from a hung session.

**Neutral bases capture without a fight — known, and deliberately left alone
(2026-08-11 user call).** A red base already blocks capture until all red ground leaves
the 3,000 m zone (Kandahar carries 13 live units inside it). A neutral base does not: its
defenders spawn on the NEUTRAL coalition, while the trigger computes its losing coalition
as RED and only ever tests red and blue — so neutral defenders neither block nor satisfy
anything, and one blue ground unit flips the base (FOB Zeebrugge has 5 such defenders).
FOB Nawa had none, so its capture on landing was legitimate. The fix would be an
`AllOfCoalitionOutsideZone("neutral", …)` condition on the neutral-CP triggers; it was
considered and dropped. **Do not re-propose without a fresh call.**

Files: `game/ato/flightplans/airassault.py`, `game/missiongenerator/luagenerator.py`,
`game/commander/packagebuilder.py`, `game/commander/objectivefinder.py`,
`resources/plugins/ctld/ctld-config.lua`, and the aircraft yamls
(`C-130J-30`, `C-47`, `An-26B`, `IL-76MD`, `C-17A`).
Tests: `tests/ato/flightplans/test_airassault.py` (gate + both layout shapes, cabins,
non-troop-transport exclusions), `tests/commander/test_air_assault_reach.py` (the range
cap), `tests/commander/test_packagebuilder.py` (`assault_flight_size`),
`tests/lua/test_ctld_paradrop.py` (9 runtime cases), extended
`tests/missiongenerator/test_ew_deconfliction.py`.

## §77 — Escort jamming (Growler / Prowler) — REMOVED (2026-10-12)

**Removed 2026-10-12 (DM call).** From 2026-07-19 the planner added an `Escort Jammer` flight
(`FlightType.ESCORT_JAMMER`, flown only by the EA-18G and EA-6B) to packages whose route crossed
a radar-SAM ring, and the `growler` plugin gave that flight two effects: a bubble that spoofed
radar missiles fired at the package, and weapons-hold pulses on the SAMs threatening it.

**Why it went:** the DM's slim-down pass. The plugin was off in his default settings and in all
ten of his saves, while the planner still fragged the task: three Escort Jammer flights sat in
those saves' ATOs doing nothing. Rows B31 and B52 had verified it worked (audit, 2026-09-16).

**What went:**

- `resources/plugins/growler/`, its `plugins.json` entry, `game/missiongenerator/growlerluadata.py`.
- `FlightType.ESCORT_JAMMER`, `EscortType.Jammer`, `PackageFulfiller._escort_jammer_cap_reached`,
  `AircraftBehavior.configure_escort_jammer`, the `jammer=` argument of `propose_common_escorts`.
- The `max_escort_jammers` setting and its planner-suite entry.
- Three test files; rows B31 and B52.

**What stayed, and what changed with it:**

- **The EA-18G and EA-6B are back on upstream's task weights**: SEAD Escort 550 and 460. The fork
  had demoted both to 400 so a strike fighter took the SEAD Escort slot and the jammer was free
  for the Escort Jammer lane. With no lane, the demotion only kept a dedicated EW jet out of the
  escort it is built for.
- **`single_sead_escort_flavour` stays** (one suppression flight per package). It was filed under
  §77 and is now a §69 setting.
- **`is_escort_type` is `ESCORT` and `SEAD_ESCORT`** again. The call sites that read it (the split
  trigger's release push, the helo-package formation guard) keep reading it.
- Anatolian Reach's Prowler squadron was authored `SEAD Escort`. No campaign carries a Prowler
  since 2026-10-18 (DM call); the mod toggle and the faction entries stay.

**Old saves:** `"Escort Jammer"` maps to `SEAD_ESCORT` in `_LEGACY_FLIGHT_TYPE_VALUES`, so a saved
flight, a squadron's task list and a campaign yaml all convert; the jammer flew the SEAD escort
profile with the SEAD Escort fit already. `max_escort_jammers` joins the settings obsolete-key
sweep and `growler` plugin options are dropped in `Settings.__setstate__`.

**Constraints learned, kept for whoever builds escort EW again:**

- **Escort jamming strengthens as the jammer closes; the C-130's standoff burn-through weakens.**
  Both were intentional and opposite. Do not build one from the other's curve (§2 is the C-130).
- **ROE only, never emissions.** The pulses set weapons-hold on the SAM group and always left a
  shoot-back window after release; a SAM that can never fire is a deleted SAM.
- **The effects must not stack with jammer count.** A missile faced the single strongest bubble.
  §86 GPS jamming still uses that rule.
- **A task proposed as an escort must be in `PRUNABLE_ESCORTS`.** The jammer was left out when it
  was added, so a wing with no free Growler scrubbed whole strikes under an unescorted doctrine.
- **A helo package takes no fast-jet formation escort.** A Growler 89 NM away once escorted a pair
  of Chinooks; the guard reads `is_escort_type` so the next escort task inherits it.
- **Cap a per-package proposal per side.** Proposed on every radar-SAM package, a strike-heavy
  turn put a dozen jammers up before `max_escort_jammers`.

The plugin is at `git show bab121fe7:resources/plugins/growler/growler-config.lua`.

## §78 — Sea-supply convoys + coastal anti-ship engagement

Retribution already models **sea supply routes** — a `CargoShip` transport sails a
`shipping_lane` between two friendly ports that have no road link between them (the
transit network prefers roads at 1× cost and only routes over water at 2× when there is
no land path). It was invisible and unsatisfying: a lone hull crawling at 12 kt, and the
coastal anti-ship batteries that should threaten it sat idle. §78 turns it into a real
mechanic on both counts. Pure engine — no Lua, no plugin, no save change. Both gates
default **ON**; OFF is byte-identical.

### Part 1 — convoys with proportional losses (`cargo_ship_convoys`)

The single-hull model was hard-locked: `UnitMap.add_cargo_ship` *raised* on a multi-unit
group ("Killing the one ship kills the whole transfer. If we ever want … a convoy of
ships that logic needs to change"). That gate is lifted.

- **Sizing** — `CargoShipGenerator._manifests_for` spreads a shipment of *T* units across
  `N = min(T, cargo_ship_convoy_max, ceil(T / UNITS_PER_SHIP))` hulls (`UNITS_PER_SHIP`=2,
  cap default 5; never an empty hull, so a 1-unit shipment stays one ship). The
  individual units are dealt **round-robin** into the N hulls, so each carries a mixed
  slice, then packed into a `(unit_type, count)` **manifest**.
- **The hull is the loss unit** — `add_cargo_ship(group, ship, manifests)` maps every
  hull's DCS unit name → a `CargoShipUnit(cargo_slice, ship)` (the §-convoy analogue of
  `ConvoyUnit`). At debrief, `dead_ground_units` collects the sunk **hulls**;
  `commit_cargo_ship_losses` kills **only each sunk hull's slice** (`ship.kill_unit` per
  unit, `KeyError`-guarded so overlapping types across hulls can't over-count). Sinking
  *k* of *N* hulls therefore denies ~*k/N* of the reinforcement and the surviving hulls
  still deliver — genuinely proportional, mirroring how convoys already lose vehicles
  one at a time.
- **Reporting** — `SideLossCounts.cargo_ships` now tallies **hulls** sunk (was
  transports), and `cargo_ship_losses_by_type` folds across the sunk slices.
- **OFF / one-unit shipment** — a single manifest carrying the whole transfer, so
  `commit` kills every unit exactly as the legacy `kill_all()` did. Byte-identical.

Files: `game/missiongenerator/cargoshipgenerator.py`, `game/unitmap.py`
(`CargoShipUnit`, `add_cargo_ship`, `cargo_ship_hull`), `game/debriefing.py`,
`game/sim/missionresultsprocessor.py`.

### Part 2 — coastal batteries engage ships (`coastal_batteries_engage_ships`)

A `CoastalSiteGroundObject` (Silkworm `hy_launcher` and the like) is generated through
the generic `GroundObjectGenerator`, which — unlike ships and EWRs — leaves it on DCS
**ALARM AUTO** with default ROE, the same passive state that let air defenses ignore the
§63 cruise missiles. `tgogenerator.set_coastal_engagement` (called from
`create_vehicle_group`, mirroring the ship-only `set_ship_engagement`) forces
**`OptAlarmState(2)` + `OptROE(WeaponFree)`** on coastal sites, so the battery fires
autonomously on any enemy hull that enters range. Coastal-only (an `isinstance` guard),
symmetric (both coalitions defend their waters), gated so OFF restores the passive
default.

**The trigger is geometry.** A convoy sails a *friendly* lane, so an *enemy* battery only
engages it when the lane passes within the battery's range of the enemy coast — this is
campaign authoring, not code. Tanker War 1988's Praying-Mantis strait box (Silkworm sites
ringing the Iranian islands) is the intended showcase: route blue and red lanes through
the strait and the convoys must run the coastal gauntlet.

Tests: `tests/retlab/test_cargo_ship_convoy.py` (partition sizing/cap/conservation,
the OFF single-hull path, proportional and overlapping-type commit, the coastal ROE gate
on/off/non-coastal). **Checklist B32** — needs an in-game pass: whether a DCS Silkworm on
weapons-free actually tracks and hits a moving 12-kt cargo ship is the DCS-only unknown,
plus watching a convoy run the gauntlet with proportional debrief losses.

## §79 — Decoy suspected-activity zones — REMOVED (2026-08-18)

Removed with the recon rework below (see §3, "The 2026-08-18 rework"). Decoys only
worked because *real* field forces were also drawn as suspected-activity circles, so
a fake circle was indistinguishable from a genuine one. Real forces now draw exact
markers from turn one, which would make every lone circle obviously a decoy.

Deleted: `game/retlab/decoy_zones.py`, the `finish_turn` hook in `game/game.py`,
the `decoy_zones` / `decoy_zone_count` settings, `TheaterGroundObject.is_decoy` (shed
from old saves in `__setstate__`), and `tests/retlab/test_decoy_zones.py`.
Checklist row **B33** is closed unflown.

**The suspected-circle restyle SURVIVES** — the amber dash over a dark-red casing, the
centred "?" glyph, the `suspectedCasing` token and the `casingColor` channel in
`mapColors.ts`/`CasedShapes.tsx`/`MapLegend.tsx`/`Tgo.tsx`. The COIN spawns (roadside
IED/VBIED, HVT convoy, dispersed cells) still conceal on their own intrinsic flag and
still render through it. Do not strip that rendering.

## §80 — Mixed-hull ship groups

Every ship group put to sea as N copies of one hull: four identical Arleigh Burkes ringing the
carrier, two identical corvettes as a "naval group". Not a data problem — a **generation**
one. A layout slot (`TgoLayoutUnitGroup`) picked **one** DCS unit type
(`random_dcs_unit_type_for_group`) and `generate_units` stamped that single type into every
position in the slot. Whatever the faction's roster held, the group came out uniform.

### The fix — a type per slot, not per group

`TgoLayoutUnitGroup.generate_units` now takes **one type per position** instead of
`(type, amount)`, and `ForceGroup.mixed_dcs_unit_types_for_group` deals that list:

1. The **lead** type is picked exactly as before (so the old distribution over classes is
   preserved and the change is a strict refinement, not a reroll).
2. Candidates are narrowed to the lead's own **unit family** — `layout.UNIT_FAMILIES`, today
   the single set `{Frigate, Destroyer, Cruiser}`; **every other class is its own family**. So
   a carrier screen mixes destroyers, frigates and a cruiser, while a patrol boat never turns
   up in a cruiser's slot, a submarine never surfaces in a surface action group, and two
   carriers never share a slot (which would confuse `find_carrier_unit`, whose flagship is
   `groups[0].units[0]`).
3. The distinct count is capped at `MAX_MIXED_UNIT_TYPES` (3) so a deep roster produces a
   **task group, not a one-of-everything zoo**; each chosen type appears at least once and the
   remaining slots are dealt from them, so a 4-ship screen off a 2-hull navy is not forced into
   an even 2/2 split.

A pool with no siblings (an explicit `unit_types:` list, or a faction fielding one hull of the
class) degrades to the old uniform group — **the change can only ever add variety.**

### Gating: naval only, and never the buy menu

Mixing is a **layout-kind** property, not a setting: `TgoLayout.mix_unit_types` is `False` and
`NavalLayout` overrides it to `True`, so SAM sites, EWRs, armor groups and missile sites keep
generating uniformly (a SAM battery's launchers must stay one type). A layout YAML can override
a single slot with `mix_unit_types: true|false`. The mixing parameter on
`ForceGroup.create_theater_group_for_tgo` defaults **off**, so the **buy menu** — where the
player explicitly picked a hull — is untouched and still generates exactly what was chosen.

### The layouts, while we were in there

The naval layouts were the other half of "all one hull": the carrier screen was declared
`unit_classes: [Destroyer]`, which both forced one class and locked the layout out of
frigate-only navies (hence the duplicate `Carrier Group with Frigate escort`, whose `.miz` is
byte-identical).

- **Carrier Group / LHA Group** — the screen accepts every surface combatant
  (`Destroyer, Cruiser, Frigate`), so a US CSG generates Burkes + Perrys + a Ticonderoga.
- **Carrier Strike Group 8** — the named US layout, and the one place the screen is
  *authored* rather than rolled: **3 × Ticonderoga + 1 × Arleigh Burke** (2026-08-19, DM
  call). The Ticonderoga is the CSG's area-air-defence ship, and what a modern anti-ship
  salvo is survived by is SM-2 magazine depth, not hull count. Both slots name explicit
  `unit_types`, so `dcs_unit_types_for_group` returns a single-hull pool and the mixing
  rule leaves the screen alone — the composition is deterministic. It reaches only
  factions fielding all three hulls (the US moderns); every other navy is untouched,
  which matters because "3 cruisers" written generically would hand a Kuznetsov three
  Slavas and 48 more anti-ship rounds (§81).
- **Carrier / LHA Group with Frigate escort** — kept as the deliberate **light screen**
  (frigate-led, `Frigate, Destroyer`, no cruiser) rather than a redundant copy that would
  regenerate the uniform-frigate look for single-frigate navies.
- **Naval Group** — the class split per slot is the point (a layered task group) and is kept;
  the two required slots gained `fallback_classes` so a navy missing a class can still put the
  layout to sea.

Headless-verified end-to-end on real campaigns (Tanker War 1988, Pacific Repartee, Velvet
Thunder): every multi-ship group generates mixed, carriers stay single-hull, submarine pairs
stay submarines, and riverine/patrol boats pair only with boats.

### Files & tests

- `game/layout/layout.py` — `UNIT_FAMILIES`/`unit_family`, `MAX_MIXED_UNIT_TYPES`, the
  per-slot `generate_units`, `TgoLayout.mix_unit_types` + `mixes_unit_types`,
  `NavalLayout.mix_unit_types = True`.
- `game/layout/layoutmapping.py` + `layoutloader.py` — the `mix_unit_types` YAML key.
- `game/armedforces/forcegroup.py` — `mixed_dcs_unit_types_for_group` + the
  `create_theater_group_for_tgo` parameter.
- `resources/layouts/naval/*.yaml` — the widened screens and the Naval Group fallbacks.
- Tests: `tests/armedforces/test_naval_hull_mixing.py` (9).

**Checklist B38** — in-game pass DONE: a mixed-hull group sails and fights as one DCS group
(formation, speed, station-keeping) with no beaching or bunching.

## §81 — Cross-turn naval magazines

The flown Marianas 2027 Tacview recorded **374 weapon launches, essentially all inside the
first five minutes**, and the DM's read named the problem exactly: *"in real life they would
not dump the entire Chinese fleet's magazines in the opening shots of the war — if this
campaign goes 20 turns they can't keep dumping 20+ per turn."*

### Three facts, one bad outcome

They need separating because they have different fixes:

1. **Ships fire autonomously and instantly.** `TgoGenerator.set_ship_engagement` spawns every
   ship `OptROE.WeaponFree` with alarm RED, because that is the only way DCS makes a fleet
   fight: ship weapons are **OPTION-driven**, and an `EngageTargets` task is air-only —
   feeding it to the naval AI crashed DCS (`ACCESS_VIOLATION` in
   `AI::ControllerStack::start`). So a ship shoots the moment anything enters range.
2. **Modern anti-ship missiles out-range the theatre.** The YJ-18 reaches ~540 km against a
   205 km Guam–Saipan gap, so "in range" is permanently true from t=0 and the whole fleet
   salvos in the opening minute rather than fighting a developing battle.
3. **A DCS mission is a fresh spawn.** Loadouts reset every turn, so red re-dumped a full
   magazine *every single turn*. Sinking hulls was the **only** way volume ever went down —
   there was no ammunition dimension to the naval war at all.

Hull culling (Marianas 2027, red 93 → 45 hulls) shrinks each salvo. It does nothing about
(1) or (3).

### N1 — staggered release (`naval_weapon_release_stagger`, default OFF)

The generator spawns ships **`ReturnFire`** instead of `WeaponFree`, and the `navalmagazines`
plugin releases each group to weapons-free at its own moment, **spread evenly** across
`[releaseMinS, releaseMaxS]` (120–900 s). Evenly rather than rolled independently, so a small
fleet cannot randomly land every release in the same few seconds — the §49 lesson, where
everything firing in one frame was itself a measured problem. **The manifest alternates
sides** (`naval_group_magazines`, 2026-09-21): control-point order lists one coalition's fleets
before the other's, and the stagger followed it, so one side's last release came the whole
window after the other's first. Found in juanjux/dcs-escalation#345.

**`ReturnFire`, never `WeaponHold`.** The point is to delay *initiation*, not to disarm
anybody: a holding fleet is a defenceless fleet. This is also the feature's load-bearing
unknown — see below.

Runtime only. No persisted state, no campaign coupling.

### N2 — the magazine (`naval_magazines`, default OFF)

Each naval group carries a persisted anti-ship stock on `game.naval_magazines`, keyed by the
same stable `TheaterGroup.group_name` (`"<id> | <name>"`) §63's magazines use — the
`TheaterGroup` lives in the campaign save, so the key survives mission regeneration. Capacity
comes from the curated `ASHM_MAGAZINE_BY_TYPE`, summed over the group's **alive** hulls at
first sight (default 8 for an unlisted hull; a hull that carries no anti-ship missile simply
never fires one, so the default costs nothing). Seeding is idempotent — an existing entry is
never re-upped, so expenditure persists.

The emitted `remaining` is this mission's **hard cap**. The plugin hooks `S_EVENT_SHOT`,
matches the weapon's `typeName` against `ASHM_WEAPON_PATTERNS` (plain **substring** on the
upper-cased name — never a Lua pattern, since weapon ids carry magic characters, the §70
lesson), decrements, and at zero drops the group back to `ReturnFire`: **winchester, not
disarmed**. A group that starts a mission dry is still emitted so the plugin can hold it —
otherwise a spent fleet fights on as if freshly loaded — and is never released by the stagger.

Expenditure mirrors into the new `naval_magazines_state` Lua→Python channel (the §57/§63
`f.state` pattern, `dirty_state`-flagged) and `reconcile_naval_magazines` debits at the turn
boundary. **Generation never debits**, so re-generating a mission is free (the §54 lesson).
There is no rearm.

The next turn's SITREP carries one line per **blue** group that fired: `<group>: N anti-ship
missile(s) fired, M left`, or `WINCHESTER` at zero (`winchester_lines` → `Sitrep.naval_lines`).
Red stock stays hidden. The function existed from the start but nothing called it until
2026-09-23.

### The per-mission salvo cap (`salvoPerMission` plugin option, default 6)

The first flight that exercised both tiers end to end (Vectron's Claw turn 1,
2026-08-19) showed the metering was exact — `state.json` reported 16 and 8, matching the
Tacview shot for shot — and that the fleet still emptied itself: a Slava-led group put
**all 16 P-500 into the air in 36 seconds** against a 44-round campaign pool. The
magazine cap never bit, because **the campaign stock is deeper than the ready loadout**,
and the stagger only decides when the ripple starts.

So the plugin also counts a per-mission salvo per group and drops a group that spends it
back to `ReturnFire`. **The magazine bounds the war; the salvo bounds the day.** It
applies under either tier (the counter does not depend on `metered`, and nothing extra
reaches the debrief channel when metering is off), never disarms a group the enemy is
shooting at — same rule and same flown reason as winchester, overshoot still counted —
and logs rather than announces, because falling silent for one mission is routine where
going winchester for the war is not. `0` restores magazine-only behaviour.

A plugin option rather than a `Settings` field: it is runtime tuning like
`releaseMinS`/`releaseMaxS`, needs no campaign preseed, and `initialize_plugin_option`
carries a new option's default into saves written before it existed, so a campaign
already under way picks it up on its next generation.

### The overshoot cap (2026-08-19)

The salvo cap's first flight found the one path that bounded nothing. A group that is
**empty and under attack** is deliberately never dropped to `ReturnFire` — the 2026-08-05
finding is that a ship on `ReturnFire` mounts no missile defence at all — and the `dry`
branch returned before the salvo check ran. Flown: a Kuznetsov that *started the mission
dry* was freed by the attack rule and fired **12 P-700 over 336 s** against a cap of 6.
Every anti-ship missile fired that mission came through that path, so the cap was never
exercised.

A group at zero may now answer an attack for `salvoPerMission` rounds past empty, then
holds even under fire. The point of the 2026-08-05 finding survives — a hull is not
defanged the instant it runs dry — while "defending itself" stops being unbounded.
Everything fired is still counted and debited. The `WINCHESTER` call is latched to once per
group; it was firing on every shot past zero, four times from one hull.

### No double-count with §63, by construction

§63 meters **land-attack** cruise missiles fired by a scripted `FireAtPoint`; §81 meters
**anti-ship** missiles fired autonomously. The two magazines meter **disjoint weapon sets**:
the land-attack families are absent from `ASHM_WEAPON_PATTERNS` — no `BGM_109`, no `3M14`, and
nothing as loose as `Kalibr` (which would catch the land-attack 3M14 alongside the anti-ship
3M54). A Burke legitimately appears in *both* hull tables, because it carries Tomahawks *and*
Harpoons; that is fine precisely because the weapon sets do not overlap. A guard test pins it.

**Never add a land-attack family to the pattern list.**

### The load-bearing unknown — ANSWERED 2026-08-05, BADLY

**Whether a DCS ship on `ReturnFire` engages an inbound aircraft that has not yet fired at
it.** DCS ROE is per *group*, not per weapon type — there is no way to say "no more anti-ship
missiles, but keep shooting SAMs" — so `ReturnFire` is the chosen compromise for both a
pre-release and a winchester ship. If DCS does not honour it that way, a spent ship is also a
defenceless one. That may be acceptable (it is out of the fight either way) but it must be a
deliberate call, not a surprise. **Test this first**, before trusting either tier.

**Flown answer (2026-08-05, the B39 first fly):** an emitter serialization bug (see the
design note — `LuaData.serialize` drops a node's key-values when it also has child items, so
the `stagger`/`metered` switches never reached the miz; fixed same day, switches are now
named child items pinned by a serialization-level test) kept the whole fleet on
generation-side `ReturnFire` for two full missions — and the fleet fired **nothing**. Not
one SAM in 110 minutes: an F-22 loitered unengaged at 24.9 km from an 054A/052B group, and
13 AGM-84D sank the SUGARGLIDER Type 071 LHA while its HHQ-16 escorts sat silent a few km
away (the 2026-08-03 WeaponFree fly of the same theatre scored 99 SM intercepts).
**A `ReturnFire` naval group mounts no missile defense and does not return fire even under
direct anti-ship attack.** Reworked same day (DM call): **release-on-attack** — the first
enemy weapon aimed at (SHOT target) or landing on (HIT) a managed group releases it to
weapons-free immediately, held or winchester; friendly fire never releases; an attacked
winchester group is never re-dropped to ReturnFire and its overshoot stays counted for the
debit.

**The re-fly added the other half — release the FORMATION, not the group.** On the fixed
build the release fired correctly and the targeted Type 071 LHA fought with the AK-630 CIWS
that is its entire AAW fit, and still died: a Retribution carrier/LHA objective is **two DCS
groups**, and the area-defence SAMs are on the **escort** group, which nobody had shot at.
An attack now frees every managed friendly group within `formationReleaseNm` (default
**8 NM**, plugin option, 0 = targeted-only; 15 km until 2026-10-15), same coalition, **one hop — never a cascade**.
The flown geometry makes the radius safe: the screen rode **1.91 km** off its flagship and
the next task force was **59.02 km** away. Details + harness pins in the design note.

### Symmetry, and what the plugin does not own

Symmetric: blue's Burkes are bound by exactly the same rule as red's Type 055s. The plugin
sets ROE and counts real weapon releases — **no spawns, no kills** — so hull losses record
natively as always (the §35/§37/§49 discipline).

`winchester_lines` surfaces blue expenditure for the SITREP; enemy residual stock stays
hidden, like every other magazine readout.

### Deferred

- **N3 replenishment** — magazines refill slowly, or only at a friendly port, so sustaining a
  fleet becomes a logistics decision rather than a free reset. Only worth doing once N2 is
  flown.
- **N4 unit-card readout** — remaining stock on the ground-object dialog (`tgo_magazines` is
  already written for it).

### Files & tests

- `game/retlab/naval_magazines.py` — the hull table, the weapon patterns, seeding,
  emission, reconciliation, the SITREP lines.
- `game/missiongenerator/navalmagazineluadata.py` — the emitter
  (`dcsRetribution.navalMagazines`).
- `resources/plugins/navalmagazines/` — the runtime (stagger + `S_EVENT_SHOT` metering).
- `game/missiongenerator/tgogenerator.py` — `set_ship_engagement`'s `ReturnFire` branch.
- `game/debriefing.py` — the `naval_magazines_state` channel (its parser is now shared with
  §63's, both being `{group=, fired=}`).
- `game/sim/missionresultsprocessor.py` — `commit_naval_magazines`.
- `game/game.py` — `naval_magazines` + its `__setstate__` default.
- Tests: `tests/retlab/test_naval_magazines.py`,
  `tests/missiongenerator/test_navalmagazineluadata.py`,
  `tests/lua/test_navalmagazines_runtime.py`.

**Checklist B39** — needs an in-game pass.

## §82 — The Wing Grows — REMOVED 2026-08-16

Scheduled mid-campaign squadron arrivals (`available_from_turn:` in a campaign's
squadron config, held out of the air wing until an announced turn, then joined and
announced on the SITREP).

**Removed on the DM's call** — "it doesn't add much except in very specific
campaigns." The whole feature is gone: `game/fourteenth/wing_growth.py`, the
`available_from_turn:` / `arrival_note:` config fields, the `AirWing.pending_arrivals`
list, the `Sitrep.arrivals` band, the pre-turn briefing's anticipation section, the
feature-registry entry, both test files, and the authored schedules in Baltic Fury (5)
and Red Tide (3).

**Save compatibility was half-done, and broke every pre-removal save until 2026-08-17.**
`AirWing.__setstate__` did drop the stale `pending_arrivals` key — but pickle resolves a
class in `find_class` *before* `__setstate__` runs, so the load died at
`ModuleNotFoundError: game.fourteenth.wing_growth` and never reached the pop. The
tombstone in `persistency.REMOVED_MODULES` was missing. Found by trying to load a Baltic
Fury save for an unrelated measurement; fixed, and the whole tombstone mechanism is now
locked by `tests/test_removed_module_tombstones.py`.

**Removing a module takes both halves.** The owner drops the orphan key *and* the module
gets a `REMOVED_MODULES` entry. Either one alone leaves saves unloadable.

Design note `retlab-wing-growth-notes.md` was deleted 2026-10-12; it is at
`git show 57ab9e720:docs/dev/design/retlab-wing-growth-notes.md`.

## §83 — SP Pilot Mode — REMOVED (2026-10-12)

**Removed 2026-10-12 (DM call).** From 2026-08-03 this was a single-player express lane, default
off: an *Accept results && fly next* button on the debrief that processed the turn and opened a
sortie board instead of the map. The board was aircraft-first (pick any type the wing could put
up, then a sortie in it, one seat with AI wingmen), and a pre-turn card listed the reasons the
turn mattered.

**Why it went:** flown and verified on 2026-08-05 (checklist B41), then never switched on: off in
the DM's default settings and in all ten of his saves on 2026-10-12. The DM's rule for the
slim-down pass that removed it: a feature he does not use was not worth carrying.

**What went:** `game/retlab/sp_pilot_mode.py`, `game/retlab/pre_turn_briefing.py`,
`qt_ui/windows/sp/`, the button and `process_debriefing_and_fly` in
`QWaitingForMissionResultWindow`, the `sp_pilot_mode` setting, the Features-page section
**Single-player flow** (it held nothing else), both test files, and the design note. The setting
key joins the settings migration's obsolete-key sweep. The note is at
`git show 57ab9e720:docs/dev/design/retlab-single-player-loop-notes.md`.

**What the work found, kept for whoever returns to the single-player loop:**

- **The loop dies at "now plan turn 2", not at the flying or the debrief.** In MP a player is a
  pilot; in SP one person is the DM and the pilot, and pays the whole planning cost for one
  sortie before any reward.
- **The structural lever was never pulled.** The player still flies 1 of about 25 packages. Smaller
  SP ATOs are planner work and were deliberately left out of §83.
- **Capture odds for evading aviators are computed every turn and shown nowhere else.** The
  pre-turn card was their only display.
- **The role should come from the air war.** The board offered joins into packages the planner
  already built; a private war built to order was ruled out.

## §84 — Old-stock loadout attrition — REMOVED (2026-08-06)

Removed one day after the flown look that was its whole point. Squadrons burned the good stock
first: each weapon **station** rolled its own depth and walked that far down the fallback ladder
the weapon data already declares, so a Hornet wanting four long-range missiles came out with a
couple of AMRAAMs and a couple of Sparrows. `game/retlab/stock_attrition.py`, the two
`FlightMembers` hooks, all four settings and the tests are gone.

**Why it went, and the reason not to rebuild it:** the ladder it walked is the same data the
loadout system uses to pick a fit in the first place, so the result read as the planner being
wrong rather than the stockroom being empty. A depth model needs its own inventory, not a
re-read of the fallback chain.

## §85 — SAM battery support section (refuellers + power)

**The problem** (DM finding, 2026-08-04, off a textbook SA-10 site built on the RetLab training
server): the real site carries a **refuelling section** (2× ATZ-5, an ATZ-60 MAZ) and **two 5I57A
diesel power stations** alongside its cargo trucks; Retribution generated the radars, the C2, the
six launchers — and no support at all. The trigger question was "ATZ-10 is a refuelling truck, why
are we not using it in SAM sites?" It turned out to be **three** independent causes, and the third
is the interesting one.

1. **No refueller was a registered unit.** `resources/units/ground_units/` had no yaml for
   `ATZ-10`, `ATZ-5`, `ATZ-60_Maz`, `ATMZ-5`, `TZ-22_KrAZ`, `M978 HEMTT Tanker`, or
   `generator_5i57` (the "DPS" in the DM's screenshot — DCS calls it *Diesel Power Station
   5I57A*, and pydcs files it under `AirDefence`, not `Unarmed`). No yaml ⇒ never a
   `GroundUnitType` ⇒ never in `Faction.accessible_units` ⇒ `has_access_to_dcs_type` returns
   False ⇒ **unusable by any layout**. The one place an ATZ-10 *did* appear is
   `tgogenerator.py`'s hardcoded `_SOVIET_TANKERS` FARP/airfield ground-support pool, which
   bypasses the unit registry entirely — which is exactly why it was only ever seen on a ramp.
2. **No faction listed one.** 139 factions author a `logistics_units` block; every one is cargo
   trucks and jeeps (UAZ-469 ×57, M818 ×55, Ural-375 ×47). Zero refuellers fork-wide.
3. **The S-300 family's `S-300 Site Logistics` slot was DEAD CONFIG.** The layout yaml declared
   it — with an explicit GAZ-66/KAMAZ/Ural whitelist — but **no group of that name existed in the
   shared `S-300_Site.miz`**. `LayoutLoader._load_from_miz` walks the *MIZ's* groups and looks each
   up in the mapping (`LayoutMapping.group_for_name`), so a slot the yaml names that no MIZ group
   is named after is never instantiated, **with no warning and no error**. So an
   S-300/SA-10/SA-20/S-400 site had never generated a single support vehicle, whatever the faction
   rostered.

**The fix.** Data only — no setting, no plugin, no Lua, no save change.

- **7 new unit yamls.** The five Soviet refuellers + the M978 HEMTT are `class: Logistics`
  (price 3); the 5I57A is **`class: Power`** (price 6), the class the Patriot's EPP and the
  LvS-103 Elverk already use. That class choice is load-bearing: `UnitClass.LOGISTICS` is in the
  ground planner's `_DEPLOYABLE_UNIT_CLASSES`, so the bowsers ride to the FLOT with the cargo
  trucks (realistic, and identical to the existing Ural/M818 behaviour), while `UnitClass.POWER`
  is in neither `FRONTLINE_UNIT_CLASSES` nor `_DEPLOYABLE_UNIT_CLASSES` — a diesel generator never
  marches to a front line.
- **3 new position groups in `S-300_Site.miz`** — `S-300 Site Logistics` (the slot that was dead),
  `S-300 Site Fuel`, `S-300 Site Power`, two positions each, dispersed off the flanks of the
  battery and clearing every existing unit by ≥50 m. Positions are appended, so the template origin
  (`S-300 Site AAA-0`) is unmoved and every existing offset is byte-identical. pydcs round-trips
  this template losslessly (all-vanilla units, verified before and after).
- **Fuel and Power are SEPARATE slots, and must stay separate.** A unit group fields exactly one
  type, so a single merged "support" slot would generate two bowsers *or* two generators, never one
  of each.
- **Layout yamls**: the three S-300-family layouts gain the Fuel slot (`optional: true`,
  `fill: false`, explicit `unit_types`) and — except the SA-2/SA-3 Mixed Site, since the 5I57A is
  S-300 kit — the Power slot.
- **Preset groups, not faction jsons.** The 11 S-300-family preset groups gain the cargo trucks +
  refuellers + DPS in their `units:` list, which is what makes `has_access_to_dcs_type` pass. This
  is the **Patriot precedent** — `MIM-104_Patriot_Stationary.yaml` already carries its own EPP
  (class Power) and an Oshkosh HEMTT support truck the same way — and it means **no faction json
  changed**.

**Fixed in passing — the same bug, elsewhere.** `Sky_Sabre_Battery.yaml` declared its point-defence
slot as `Point Defense` while the group in `8_Launcher_Circle.miz` is called `PD`, so **a Sky Sabre
battery has never fielded any SHORAD**. Renamed to `PD`.

**Headless-verified** end to end on Red Tide: all 7 generated S-300 sites now field a cargo truck +
a refueller + 1–2 diesel power stations, and the theater carries 26 refuellers + 12 power stations
where it previously carried none.

**Balance.** ~+18 to an S-300 site that already costs ~230 (the radars alone are 24–30 each), so
under 8 %. The support units are unarmed soft targets: they add strike value and a legible
"there is a real battery here" read, not threat. `max_threat_range` is unchanged, so SEAD/DEAD
targeting is unaffected.

Files: `resources/units/ground_units/{ATZ-10,ATZ-5,ATZ-60_Maz,ATMZ-5,TZ-22_KrAZ,M978 HEMTT
Tanker,generator_5i57}.yaml`, `resources/layouts/anti_air/{S-300_Site.miz,S-300_Site.yaml,S-300 Site
(Single Radar).yaml,SA-2-SA-3 Mixed Site.yaml,Sky_Sabre_Battery.yaml}`, `resources/groups/` (11
S-300-family presets). Tests: `tests/armedforces/test_sam_support_vehicles.py` (58 — registration,
the Power-never-deploys invariant, slot presence, template position counts, the fuel/power
separation, preset access, and a **repo-wide dead-slot guard** that fails if *any* anti-air layout
declares a slot no group in its `.miz` is named after). Checklist: **B43**.

### Missile batteries get the same treatment (2026-08-06)

**The problem** (DM question, off the 9K720 Iskander's published system list — TEL, transporter and
loader, command-and-staff vehicle, information preparation station, maintenance vehicle, life
support vehicle): a missile site generated **three launchers and a UAZ-469 jeep**. One generic
layout (`resources/layouts/defenses/missile.yaml`) is behind every SCUD / Iskander / CJ-10 / V-1 /
ATACMS site in the fork, and **33 of the shipped campaigns author missile markers** (Desert Storm 9
sites, Marianas 3, Red Tide 2, Baltic Fury 1), so it is not a rare object.

**What DCS can actually model is 3 of those 7 roles** — TEL, a transporter/loader stand-in
(`ZIL-135`, the 8×8 that carries Soviet theatre rockets; `S_75_ZIL`, a literal missile transporter;
`CH_HEMTT_M977`, the US cargo/crane truck), and a command-and-staff vehicle (the §85 kit:
`ZIL-131 KUNG` / `Ural-375 PBU` / `GCI_station_MiG29`, plus `Predator TrojanSpirit` / `fire_control`
for NATO). Information preparation, maintenance and life support are all the same KAMAZ repeated, so
they are represented by the cargo pair rather than transcribed. **Zero new unit registrations were
needed** — §85 had already registered every candidate.

**The slots** (textbook fixed counts, the §85 call — a battery renders the same park every time, so
it is recognisable from the air): 3 launchers · **2 cargo trucks** · 1 transporter/loader · 1
refueller · 1 command-and-staff vehicle · the unchanged optional AAA and SHORAD escorts. Four
positions were appended to `missile.miz`; the pre-existing offsets are byte-identical and the
template anchor (`ScudGenerator 3`, whose first unit the loader anchors on) is untouched, so no
campaign's authored site moves.

**The displacement fix, and why it was needed.** The old `Logistics` slot was class-based, and a
class slot picks **one** type from a pool that since §85 also holds fuel bowsers — so the bowser
*replaced* the cargo truck rather than joining it, which is exactly what the flown Marianas PLARF
sites showed. Cargo is now an explicit multi-national truck whitelist (with
`fallback_classes: [Logistics]` so a faction hauling with something unlisted still fills), and fuel
is its own slot. Measured: every one of the 36 missile-fielding factions fills cargo and transload;
29 also field a refueller; 11 field a command vehicle. Same trap caught once more during the build —
the transload slot's first cut used `fallback_classes: [Logistics]`, which resolved to **9 of 11
candidates being bowsers** for Russia 2020 (a second ATZ-10 as the "transloader"), so the cargo
trucks are listed explicitly there too.

**The §49 constraint shapes the section.** Every one of these shares **one DCS group** with the
launchers, `mist.goRoute` routes a group as a whole, and a single undrivable member pins the whole
battery — so the section is drivable metal only: no statics, no trailers, and deliberately **no
5I57A power station** (S-300 kit, and not in the Iskander's list anyway).
`test_no_support_unit_can_pin_the_scoot` enforces it against the unit data.

**Launchers are no longer free.** Every launcher in the fork was `price: 0` — Scud_B, Iskander-M/K,
CJ-10, Shahed-136, the V-1 ramp, and the whole coastal anti-ship family — while missile and coastal
sites *are* purchasable (`GroupRole.DEFENSES`) and the ground-object repair cost is the unit price.
So the buy menu sold theatre ballistic missiles for nothing and rebuilding a killed launcher was
free. Priced against the existing `CH_M270A1_ATACMS` (45) and the artillery scale (Uragan 40, Smerch
60, PHL-16 85): V-1 20 · Shahed-136 25 · Silkworm 30 · Scud-B 40 · RBS-15KA 55 · Bal 60 ·
Iskander-M 70 (= both 9K720 registrations) · YJ-12B 70 · Iskander-K / CJ-10 / Bastion-P 75 ·
DF-21D 85. A 3-launcher SCUD battery now costs ~135 with its support, against ~230 for an S-300 site.

Files: `resources/layouts/defenses/{missile.yaml,missile.miz}`, `resources/units/ground_units/`
(14 launcher prices + 3 `mobile:` flags), `game/dcs/groundunittype.py`,
`game/missiongenerator/mobilemissileluadata.py`,
`resources/plugins/mobilemissiles/mobilemissiles-config.lua`. Tests:
`tests/armedforces/test_missile_site_support.py` (34 — pricing and its ordering, slot shape and
fixed counts, a unit-id typo guard, both displacement guards, per-faction fill across all 36
missile-fielding factions, the drivability invariant, the `IMMOBILE_UNIT_IDS`↔unit-data lockstep,
the emitter skipping an undrivable launcher on real DCS types, template-offset preservation, and an
end-to-end battery generation). Checklist: **B47**.


## §86 — GPS jamming (satellite-guided weapons go long)

**The constraint that shapes everything.** DCS models **no GPS receiver**. No scripting API
degrades a jet's navigation, a weapon's guidance quality, or a JDAM's CEP — which is why every
earlier look at GPS/datalink jamming (see `retlab-iads-c2-consequences-notes.md`) recorded it as
*not feasible*. The way through is to stop trying to jam the aircraft and **jam the weapon**:
track the released store and make it miss. That turns out to be more honest than it sounds,
because what a GPS jammer actually does to a strike package is exactly "your satellite-guided
weapons do not hit what you aimed at."

**The mechanism** (`resources/plugins/gpsjamming/gpsjamming-config.lua`): `S_EVENT_SHOT` starts
a track on any store matching the curated satellite-guided pattern list → the first sample the
store is inside a live **enemy** jammer's reach, roll `degradeChancePct` **once** (the outcome
is remembered either way, so a long glide cannot re-roll itself into a certainty) → the store
flies its **entire normal profile** → at the terminal gate it is `destroy()`ed and a
`trigger.action.explosion` produced at a scored offset. The pilot sees the release, the fall
and the bang, just in the wrong place. Miss distance scales with jamming strength (1 at the
emitter, 0 at the bubble edge), so a store clipping the fringe is nudged and one released
overhead is thrown clear.

**The predictive terminal gate is the non-obvious half.** A plain `agl <= floor` test **fails
for fast weapons**: a store descending at 400 m/s covers 800 m in a 2 s sample step, so it can
be at 900 m AGL on one tick and already detonated on the aimpoint by the next — the jamming
silently does nothing, the worst failure mode (it reads as the feature being off). The gate
fires when the store would already be *through* the floor by the next sample
(`floor = max(terminalAgl, descentRate × trackStep × 2)`), so a coarse sample step makes the
destroy happen **higher**, never later than impact.

**No phantom spawns, no invented losses** (the §35/§37/§49 discipline). The store is a real
weapon from a real jet; the script spawns nothing and owns no kills beyond the miss explosion,
whose damage is ordinary DCS damage recorded natively. A weapon that vanishes before the gate
(it impacted, or a SHORAD killed it) is simply dropped — a degraded store that got that far hit
normally and is deliberately **not** re-detonated, since we cannot know it did not already do
its damage. The jammer is an ordinary strikeable TGO, and killing it drops it from the live-site
check on the very next weapon, so **accuracy returns inside the same mission**.

**Identification — the unit-yaml contract.** The *presence* of a `gps_jamming` block in a ground
unit's own data file is what makes it a jammer (`GpsJammingProperties`,
`game/dcs/groundunittype.py` — the §24 `date_gated_properties` precedent):

```yaml
gps_jamming:
  radius_nm: 45        # optional — falls back to the campaign setting (30 nm)
  miss_radius_m: 350   # optional — falls back to the campaign setting (200 m)
```

`gps_jamming: {}` (or `true`) is a jammer on the campaign defaults. Chosen deliberately so that
**adding a jammer is a data edit** — register the vehicle, write its yaml, add the block; no id
list in Python needs touching, so unit work and feature work never have to land together. A site
with several jammer types takes the **longest** declared reach and the **worst** declared miss.

**The curated weapon list** (`GPS_GUIDED_WEAPON_PATTERNS`, emitted to Lua so it has exactly one
home; matched as plain case-insensitive **substrings, never Lua patterns** — weapon names carry
`-` and `(`, the §70 lesson). **In:** JDAM (GBU-31/32/38), GBU-54 (Laser JDAM — its *baseline*
mode is GPS/INS and the runtime cannot see whether anyone is lasing), JSOW, JASSM, SLAM-ER, WCMD
dispensers, KAB-500S/1500S (GLONASS, so red eats its own medicine). **Out, and load-bearing:**
every laser, TV, IR and anti-radiation weapon — a Paveway that mysteriously misses is a bug
report, not a feature — plus the §63/§81 ship-launched cruise missiles, which are their own flown
features. Pinned in both directions by `tests/retlab/test_gps_jamming.py`.

**Squadron calls (2026-08-04).** *Symmetric* — a site degrades the **opposing** coalition only,
so a blue jammer works the day one is fielded (red owns them in practice). *The player is told,
both ways* — a recon-**fogged** kneeboard BLUF line (`GPS  <site> 30nm — GPS weapons unreliable
inside; use laser/TV or stand off`), so an **un-scouted jammer is not briefed** and finding it is
worth a recon sortie; plus a **one-shot in-cockpit cue** the first time a flight's weapon is
spoofed, so a failed pass reads as jamming rather than as a broken sim.

**What the player does about it:** change delivery method (laser/TV are unaffected — the
intended counter, and the reason the exclusions are load-bearing), or kill the jammer. Standing
off is NOT a counter for a covered target (see the bubble note below).

**Placement — two models, both explicit.** The design question "where does a jammer live" was
worked through on 2026-08-05 and answered *both* ways, because the two cases want different
things:

* **A standalone site** (`GPS Jamming Site` layout + the `GPS Jamming Site (Red)`/`(Blue)`
  presets) — its own marker, its own point defence, its own ARM-able radar. Put denial anywhere:
  on an objective, covering an approach, guarding a bridge.
* **An attached section** (the `S-300 Site GPS Jammer` slot on the S-300-family layouts, used by
  the `SA-20/S-300PMU-1 (GPS jamming)` preset) — puts the jammer *inside* an existing threat
  ring, which is the more interesting version: killing it means going into the S-300's envelope
  instead of strafing a soft truck in a field. It is also where a real EW company sits.

Both are `optional` + `fill: false` and preset-driven, so **every shipped site generates exactly
as before** — a campaign gets a jammer only where it pins one.

**THE BUBBLE IS A DENIED *TARGET* AREA, NOT A DENIED *RELEASE* AREA.** This is the fact that
drives placement and sizing, and it is easy to get backwards: the runtime degrades a weapon that
*flies through* a live bubble, so a weapon aimed at anything inside the bubble passes through it
**whatever range it was released from**. Standing off therefore does **not** help against a
covered target — it only changes *which* targets are covered. The radius is simply the size of
the target set that loses satellite guidance. The counters are **change delivery method**
(laser/TV are untouched) or **kill the jammer**.

That is why the reach is **15 nm**, deliberately below the 50 km (27 nm) DCS declares for the
vehicle: at 27 nm a single site denied a large share of a medium map, which switches a weapon
class off rather than posing a question. 15 nm denies a target cluster, so a campaign can field
two or three on distinct clusters and most of the theatre stays GPS-usable.

**Density: at most 3 per campaign, non-overlapping — CI-guarded.** Bubbles are large and
**invisible on the campaign map**, so a heavy hand is easy to author and hard to notice until
somebody flies it (the Marianas lesson: 13 of 30 max-radius rings "did not make the campaign
harder, it made the map unreadable"). Two tests in `tests/retlab/test_gps_jamming.py` walk
every campaign's `ground_forces` pins, resolve each preset, and fail on more than three jamming
sites or on two bubbles that overlap. Overlap is called out specifically because **effects do not
stack** — a weapon faces only the single strongest bubble covering it (the §77 non-stacking rule)
— so a second overlapping site adds no decision for the player and killing one restores nothing.

**It carries no radar, and is a STRIKE target rather than a SEAD target** (DM call 2026-08-05).
An earlier cut paired the jammer with an ARM-flagged acquisition radar so a HARM could home on
the site. That is now dropped, and dropping it is the *realistic* answer: a real GPS jammer
transmits in **L-band**, which no RWR covers and no anti-radiation seeker homes on, so making it
HARM-able was the unrealistic option. The stock jammer's own DB entry agrees — it declares
`GT_t.ws = 0` with no `GT.WS`, no `GT.Sensors`, no `searchRadarFrequencies`, i.e. DCS models it
as emitting nothing an aircraft can see.

So the site is found by **recon** (the §3 fog surfaces it as a contact; the kneeboard briefs the
area once scouted) and killed with **bombs**. Its point defence is what stops that being free —
an optional SHORAD/AAA slot filled from the owning faction, so a faction with no SHORAD (China
2027) fields an undefended site.

Dropping the radar removed two costs as well as the unrealism: a second radar in every site, and
a radar in the faction roster — where, being a `SearchRadar` class, it leaked into unrelated SAM
sites in roughly one game in five. **Only the jammer is granted now**, and its
`ElectronicWarfare` class is referenced by no layout, so it can never be faction-filled anywhere.

**Task = EarlyWarningRadar**, because `IadsRole.for_task` maps it to `EWR`, the one air-defence
role the IADS engine never holds dark. A site tasked MERAD/LORAD/SHORAD would be held dark
until cued, so it would be off the RWR and un-HARM-able for most of the mission — exactly what
the radar is there to prevent. The site consequently also contributes to its side's IADS
detection, which reads correctly (it *is* a radar site).

**Granting a faction access is what makes a pin work, and how you do it matters.** The override
gate is `all(u in faction.accessible_units for u in fg.units)`, so **one** unreachable unit
silently discards the whole pin and the marker falls back to an ordinary site. `accessible_units`
chains `preset_groups`, so registering the preset there grants access — **but it also makes the
site a `random_group_for_task` candidate**, which had unpinned EWR markers rolling jamming sites
and the campaign generating a different shape every time (measured: 2-to-4 sites across runs when
only 2 were pinned). Grant access through `air_defense_units` instead: the units become reachable,
the preset is not a random candidate, and the laydown is exactly what the campaign pins.

**Fielded in four modern campaigns** (2026-08-05), each with two sites on well-separated
RED-owned markers: **Baltic Fury** (2027), **Marianas 2027** (China), **Slava Ukraini** (2026 —
the war where GPS jamming is least surprising) and **Into the Hornets Nest** (2022). The era
filter is the jammer's own 2010 introduction, which excludes the Cold War and Desert Storm
laydowns outright. **A pin must bind to a control point owned by the side that fields the
jammer** — the override gate checks the preset against the *owning* CP's faction, so a red
preset on a blue-CP marker is silently discarded (caught when three campaigns each generated one
of their two pinned sites); a test now enforces it.

**Preseeded in Operation Baltic Fury** (2027) on two dedicated markers added by
`tools/build_baltic_fury_miz.py --gps-jamming` — `GPSJAM-1` on the Copenhagen approach (~5 km
from Kastrup, the victory objective, so the final push is "kill the jammer before you can JDAM the
prize") and `GPSJAM-2` at Rostock on the central axis. They are **their own markers, not a
modifier on the EWR net**: red's early-warning chain and its GPS-denial belt are separate
installations you attack separately. Red Tide is deliberately not a candidate — it is 1988, and
GPS-guided weapons postdate it entirely.

**Settings.** `gps_jamming` (RetLab Features → Electronic & command warfare, default **OFF**,
preseeded nowhere). A unit with no reach or miss of its own uses `DEFAULT_REACH` (15 NM) and
`DEFAULT_MISS_RADIUS` (200 m) in `game/retlab/gps_jamming.py`; both were settings until
2026-09-23. Plugin options cover the degrade
chance (85 %), terminal altitude (100 ft AGL), the shooter cue and the grace. **The
miss detonates with the store's own warhead** (`desc.warhead.explosiveMass`, scaled by
`missPowerScalePct`, default 100 %), so a 2000 lb JDAM craters like one and a 500 lb JDAM does
not; a store reporting no warhead falls back to the flat `missPower`, which is the pre-scaling
behaviour exactly. **The plugin is the runtime**; it has no checkbox since 2026-10-15, so the
setting is the one switch.

**Deliberately not done:** aircraft navigation degradation (impossible, and it would lie to the
pilot's own cockpit); a dedicated map overlay (the site is an ordinary TGO and already draws);
§74 DTC coupling (a cartridge carries steerpoints, not guidance quality); and **planner
awareness** — the auto-planner does not yet avoid jammed areas or re-pick loadouts, a real
follow-up kept out of v1 so the runtime can be flown alone.

Files: `game/retlab/gps_jamming.py`, `game/dcs/groundunittype.py`,
`game/missiongenerator/gpsjammingluadata.py`, `game/missiongenerator/luagenerator.py`,
`game/missiongenerator/kneeboard/`, `game/settings/`,
`resources/plugins/gpsjamming/`, `resources/units/ground_units/GPS_Spoofer_{Red,Blue}.yaml`,
`resources/layouts/anti_air/GPS_Jamming_Site.{yaml,miz}`,
`resources/layouts/anti_air/S-300{_Site, Site (Single Radar)}.yaml` + `S-300_Site.miz`,
`resources/groups/GPS-Jamming-Site-{Red,Blue}.yaml`,
`resources/groups/SA-20-GPS-Jamming.yaml`, `game/theater/start_generator.py`.
Tests: `tests/retlab/test_gps_jamming.py` (45) +
`tests/missiongenerator/test_gpsjammingluadata.py` (4) +
`tests/lua/test_gpsjamming_runtime.py` (12). Design note:
[`retlab-gps-jamming-notes.md`](design/retlab-gps-jamming-notes.md). Checklist: **B45**.


## §87 — Naval station-keeping racetracks

Enemy ships were stationary targets, and the reason is a single missing `else`.

`GroundObjectGenerator.generate()` gave a ship group waypoints in exactly one case: when the
campaign was **repositioning** it, via `sail_to_destination` gated on
`ShipGroundObject.target_position`. With no destination that turn — the normal state — the
group generated with a **zero-waypoint route** and sat motionless on its campaign marker for
the whole mission. Last turn's recon photo was always still good, and a coordinate written
down once stayed valid forever.

That also explains the asymmetry the DM observed, that *blue* ships seemed to move and red's
never did. Two unrelated paths move blue hulls: `steam_into_wind` turns the carrier for
recovery (`GenericCarrierGenerator` overrides `generate()` entirely), and any ship the campaign
happens to be relocating sails. Neither is a patrol, and neither ever applied to a red marker
sitting on station.

### A racetrack, not a circuit — and the anchor is at its centre

`hold_station` gives every otherwise-idle ship group a **flattened oval centred on its own
spawn position**. The centring is the design, not an implementation detail:

- A circuit drawn **around** the anchor makes the group steam a full radius clear of its
  marker and keep going — it reads as a ship *transiting off station*, i.e. fleeing.
- An oval **centred on** the anchor keeps the group's **mean position at its campaign
  position**. It holds station under way, which is what an escort, a picket or a barrier
  patrol actually does.

The second property is what keeps the rest of the game honest. The campaign map, the drawn
threat rings and the turn-boundary force model all place the group at its marker, and with the
marker at the centre of the track that stays true on average and bounded absolutely:

| knob | value | consequence |
| --- | --- | --- |
| `STATION_LEG` | 3 NM | long axis |
| `STATION_WIDTH` | 1 NM | leg separation |
| `STATION_SPEED` | 10 kt | ≈48 min per lap — visibly under way all mission |
| — | **≈1.6 NM** | hard ceiling on displacement from the marker, forever |

Corners are ordered so the circuit is two long legs joined by two short ones — four 90° turns
rather than a 180° reversal at each end.

### What sets the size — the ship's own threat ring

The first cut used an **8 × 2 NM** oval, picked by feel. It is wrong, and the thing that
proves it is the ring the map draws *at the marker*: displacement from the marker is straight
error in that ring. Measured against the air-defence radii in the DCS unit data:

| hull | AD radius | error at 4.1 NM (8 × 2) | error at 1.6 NM (3 × 1) |
| --- | --- | --- | --- |
| Molniya | 2 km (1.1 NM) | **~4× the entire ring** | 1.5× the ring |
| Albatros / Rezky | 16 km (8.6 NM) | 48% | **18%** |
| Type 054A | 45 km (24 NM) | 17% | **7%** |
| Burke / Perry / Ticonderoga | 100 km (54 NM) | 8% | **3%** |

At 8 × 2 a short-legged hull could sit **wholly outside its own drawn threat ring**. At 3 × 1
every ring that anyone plans a mission against stays substantially true. The Molniya is left
as a known limit rather than a target: a 1.1 NM ring is smaller than any useful patrol and is
not something a strike is planned around.

Real practice points the same way. A naval *station* is quoted in **thousands of yards from
the guide** — WWII carrier doctrine's "Circle Six" and "Circle Nine" are 6,000 and 9,000 yd
for the **whole screen**, with individual screen stations as close as 1,000 yd. The 1.6 NM
(≈3,200 yd) reach sits inside that band; 4.1 NM was roughly the radius of an entire carrier
screen, applied to one ship's wander.

**Collision between groups is deliberately not the governing constraint.** Measured across the
shipped campaigns, the closest two naval groups anywhere are **17 NM** apart, so tracks stay
disjoint by a wide margin at any size considered — the constraint had to come from the threat
rings instead. `test_the_station_stays_small_against_a_ship_threat_ring` pins the result (it
fails on the old 8 × 2 numbers).

### Nothing runs at runtime

The waypoints are ordinary route points and the loop is `SwitchWaypoint`, the Mission Editor's
own "go to waypoint N" action, so **DCS's naval AI sails the whole thing itself**: no plugin,
no Lua, no emitter, no scheduled task. The loop targets waypoint **2**, never 1 — waypoint 1 is
the spawn at the centre of the oval, so it is the one-time run-out onto station and must not
become a leg of the repeating circuit.

That choice is also why the feature composes instead of colliding:

- **§63 cruise-missile raids survive it.** The plugin uses `PushTask`, which pushes the
  `FireAtPoint` onto the queue and pops back to the underlying route when the salvo ends. The
  scripted alternative — `mist.goRoute`, a `setTask` — would have **wiped** the pending fire
  mission, which is precisely the §49 fire-then-scoot clobber. Here it is avoided by
  construction rather than worked around with hold deadlines.
- **§81's ROE and alarm state are untouched.** Those are tasks on `points[0]`; appending
  waypoints does not disturb them, so a staggered or winchester fleet behaves identically.
- **§80 mixed-hull groups** sail the circuit as one formation, same as any other route.

### Land is handled in Python, where the landmap already lives

DCS naval AI does **no land avoidance whatsoever**, so a bad waypoint beaches the group. Every
candidate orientation is validated with `theater.is_in_sea()` sampled every 1 NM along **every
leg**, including the run-out — two clear endpoints with an island between them would ground the
group, so endpoint checks alone are not enough. Twelve bearings (30° apart) are tried in a
**crc32-of-group-name** order, which buys four things at once:

1. A group in open water takes its first choice.
2. A group in a strait or a bay ends up oriented **along** the water it actually has — which is
   what a real station in confined water looks like.
3. Regeneration re-derives the same station instead of reshuffling the fleet (crc32 rather than
   `hash()`, which is salted per process).
4. Different groups get different orientations, so a fleet does not steam in parallel like a
   parade.

This is strictly better than doing it at runtime: the §49 scoot radius is famously **not**
landmap-checked (the open risk on the Marianas T5 row), and this version cannot inherit that.

**Every failure degrades to today's stationary behaviour** — no landmap, no clear orientation
in any of the twelve bearings, or a spawn the landmap will not confirm as open water (a marker
inside a harbour polygon). A ship authored alongside a pier simply stays put.

### Scope and measurement

Symmetric, and **carrier/LHA control points are deliberately untouched** —
`GenericCarrierGenerator` overrides `generate()`, so `steam_into_wind` and the §72 airboss keep
the boats.

**No setting**, following §80 — same file, same generation-time shape. Per the §28 audit the
settings surface is a mirror of the in-game-pass backlog, and a kill switch earns its place on
*unverified runtime Lua*; this is bounded generation behaviour that degrades safely, so a
toggle would only add to the surface.

Measured against the real landmaps, using each campaign's authored miz ship markers:

| campaign | ship markers | put on station |
| --- | --- | --- |
| `marianas_2027` | 11 | 11 (100%) |
| `pacific_repartee` | 21 | 21 (100%) |
| `tanker_war_1988` | 2 | 2 (100%) |
| `1968_Yankee_Station` | 3 | 2 (67%) |

The single miss is a hull whose spawn the landmap does not classify as sea — the safe degrade
firing, not a defect.

**NEW mission only**: generation-time, so existing saves pick it up on the next regeneration
with no new game and no save migration.

Files: `game/missiongenerator/tgogenerator.py` (`hold_station`, `_station_racetrack`,
`_racetrack_corners`, `_track_is_clear`, and the `STATION_*` constants).
Tests: `tests/missiongenerator/test_naval_station_keeping.py` (11). Checklist: **B46**.


## §88 — Angled-deck carrier recovery heading

Adopted from geofffranks' `12d71346` (his fork, 2026-07-29), answering upstream issue
[dcs-retribution#865](https://github.com/dcs-retribution/dcs-retribution/issues/865). Not
merged upstream at adoption time — see the drift note at the end.

### What was wrong

`GenericCarrierGenerator.steam_into_wind` did two things, both slightly wrong:

1. **Pointed the bow straight into the wind.** Every real carrier lands aircraft on an angled
   deck offset to port — 9° on a Nimitz, 10.5° on a Forrestal or an SCB-125 Essex, 7.95° on
   Kuznetsov. Bow-into-wind therefore puts the relative wind ~9° off the landing centreline, so
   the recovery the boat is steaming for has a permanent crosswind component it does not need.
2. **Could order a negative speed.** `carrier_speed = knots(25) - mps(wind.speed)` had no floor.
   Above 25 kt of ambient wind it wrote a negative speed into the group's route.

### The fix

`game/flightplan/carriercruisesolver.py` — `solve_carrier_cruise(wind_direction, wind_speed,
deck_angle)` returns a heading and speed putting ~25 kt **down the angled deck** with zero
crosswind. Three modes, all reachable and all tested:

| mode | when | behavior |
| --- | --- | --- |
| `EXACT` | normal wind | solves heading + speed for 25 kt on the deck axis, zero crosswind |
| `WEAK_WIND_APPROXIMATION` | ambient wind below `25 · sin(deck angle)` (~3.9 kt at 9°) | the crosswind term is unsolvable; falls back to bow-into-wind and accepts the residual |
| `HIGH_WIND_SPEED_CLAMP` | ambient wind alone exceeds 25 kt | speed clamped to 0, deck aligned with the ambient wind |

The deck angle is data, not code: `landing_deck_angle` in `resources/units/ships/*.yaml`,
top-level per class with per-variant overrides (`ara_vdm.yaml` carries 8.0 for both *Veinticinco
de Mayo* spellings and 5.5 for *HMAS Melbourne*). Loader parsing rejects non-numeric values,
booleans and anything outside ±90°. Every hull the fork classes `AircraftCarrier` or
`HelicopterCarrier` now declares one; helicopter decks and straight decks are 0.0, which
reproduces the old behavior exactly.

Positive means the landing area is offset **to port**, which is every hull in the game. A
negative value is accepted and mirrors correctly, but nothing ships one.

### The B55 desk finding (2026-08-16): the deck-angle sign was inverted

The adopted solver put the solved heading on the **counterclockwise** side of the wind
reciprocal (`wind_from - asin(25·sin(deck) / wind)`). That is the geometry for a
starboard-offset landing area: the apparent wind ended up aligned with `heading + deck` — the
mirror of the deck every hull actually has — leaving a crosswind of `25·sin(2·deck)` across the
real landing area (~7.7 kt at 9°), **double** the bow-into-wind residual (~3.9 kt) the feature
was adopted to remove. Both `EXACT` and `HIGH_WIND_SPEED_CLAMP` carried the sign; fixed
2026-08-16 to `wind_from + offset` / `wind_from + deck`.

Measured on the Baltic Fury turn-3 generation that surfaced it (wind blowing toward 011 at
9.19 kt, Stennis deck 9.0): pre-fix the solver authored BRC 166 (felt wind from 175, 18° off
the 157 landing area, +7.7 kt crosswind); post-fix it authors BRC 216 (felt wind from 207 =
exactly down the landing area, 0.0 kt). The investigation also confirmed the pipeline is
otherwise faithful: the authored route IS the raw solver output — `steam_into_wind` converts
the save's m/s wind to knots (the solver works in the units of its 25 kt target),
`Heading.from_degrees` rounds to whole degrees (165.8 → 166), the sea probe only ever shortens
the leg (100 → 20 km, never a new heading), and escorts have no `landing_deck_angle`, so their
group solves at deck 0 — plain bow-into-wind, diverging from the carrier's course by the
offset (25° in that save).

The apparent-wind alignment is now pinned as an invariant
(`test_apparent_wind_runs_down_the_port_angled_deck`, 60 parametrized cases: apparent wind
from `heading - deck`, 25 kt, in every EXACT solve) plus the Baltic numbers as a regression
case, so a future sign flip cannot pass CI.

### Consequences worth knowing

- **BRC moves.** The heading fed to `add_runway_data`, the kneeboard and the CV Operations Data
  page (§65) is now the solver's, up to ~15° off pure into-wind. That is the ship's actual
  heading, so the number is still correct — it just no longer equals wind-reciprocal.
- **The `HIGH_WIND_SPEED_CLAMP` boat sits still.** In >25 kt ambient wind the carrier makes zero
  way. Wind over deck is satisfied, but a real boat would still be making turns. Watch this in a
  storm turn.
- **NEW mission only** — generation-time, no setting, no save migration.

Files: `game/flightplan/carriercruisesolver.py`, `game/dcs/shipunittype.py`,
`game/missiongenerator/tgogenerator.py` (`steam_into_wind` + its call site), 22 hull yamls under
`resources/units/ships/`.
Tests: `tests/flightplan/test_carriercruisesolver.py` (71, incl. the 60-case apparent-wind
invariant), `tests/dcs/test_shipunittype.py` (24),
`tests/missiongenerator/test_ship_sail_waypoint.py` (+5).
Checklist: **B55**.

### Fork deltas vs the source commit

- **Pretense is removed here**, so `game/pretense/pretensetgogenerator.py` and the
  shared-`steam_into_wind` test are not carried.
- Our generator class is `GenericCarrierGenerator`, not upstream's `CarrierGenerator`; the tests
  target ours.
- **Four hulls the source commit missed** are covered here: `VINSON.yaml` (CVN-70, 9.0),
  `Essex.yaml` (USS Bennington CV-20, classed `HelicopterCarrier` → 0.0), `[VWV]IX514.yaml`
  (0.0), and the `CV_1143_5` variant override was left off as a no-op duplicate of its
  top-level value.
- **The deck-angle sign is fixed here and not in the source commit** (see the B55 desk finding
  above): `12d71346` solves to the starboard mirror. If upstream lands a shape for #865, check
  its sign against the apparent-wind invariant test before reconciling — and the finding is
  worth carrying to upstream once the PR freeze lifts.
- **Drift watch:** this is unmerged contributor work with no upstream PR open. If upstream lands
  a different shape for #865, reconcile to theirs.


## §89 — Living battlespace — REMOVED (2026-09-07)

All five slices, abandoned entire. P4 (the synthesized blue voice net) had already gone on
2026-08-18. Deleted: `game/retlab/living_battlespace.py`, `reactiveredluadata.py`, the
`reactivered` plugin, the three settings, the briefing's pre-roll block and its template
section, the recovery-residue ledger and ramp spawner, the follow-on window, the
expended-stores and AI-fuel rules, and the auto fast-forward in `QTopPanel`.

What it was: P1 seated the player's package a phase-aware distance into the turn's ATO cycle
and simulated to engine start; P2 parked recovered flights on the ramp, emptied the racks of
strikers spawned past their target and burned down the fuel of aircraft spawned en route; P3
extended the spread's tail so packages launched as the player recovered, and printed the
day's running score in the briefing; P5 held real red alert flights that scrambled a
defensive patrol over an objective blue's own ATO had struck.

Constraints kept out of the deleted design note:

- **Reactive red never spawned a phantom.** The alert flights were claimed, tracked airframes
  whose losses counted — the same rule that binds §35, §37 and §50.
- **An `uncontrolled = true` group is already in the world with its engines off, and DCS's
  `activate()` does nothing to it.** Assuming otherwise cost five days: reactive red could
  never launch. `tests/lua/dcs_stubs.lua` still models this for every other plugin.
- **Pre-roll combat resolved on the same odds as any other off-screen fight**, so its losses
  were real. Anything that advances the war before the player spawns keeps that.

What survived the removal, and must not be reverted with it: the scheduler's `spread_ceiling`
and `_spread_arrival` are **B99** work, not §89's — only the `followon_window_minutes` term
was removed from the ceiling.

In git history at `git show c08b85de2:docs/dev/design/414th-living-battlespace-notes.md`.

## §90 — Front-line model: supply, assault cost, force weight, terrain, salients

**Design note:** [retlab-retribution-long-view.md](design/retlab-retribution-long-view.md) seam 4.

Five changes to how the ground war moves, landed together 2026-08-17. Each has its own setting,
each defaults on, and with all five off the behaviour is upstream's exactly.

### What was wrong

- `game/theater/frontline.py:191` placed the front at `blue.strength / (blue + red) x route_length`,
  where `Base.strength` is a float in `[0.0, 1.0]` — a morale scalar, not a count. Two bases at full
  strength met in the middle whether one held five vehicles or five hundred.
- `game/game.py:573` applied `+0.2` strength to every blue base every turn, unconditionally. Ground
  taken drained back on a timer regardless of whether anything could reach the base.
- `game/sim/missionresultsprocessor.py:673-683` was a straight swap: winner up, loser down, same
  number. Attacking and defending cost the same.
- The FLOT was a straight chord with every ground group placed on it. A front had no shape.

`ENEMY_BASE_STRENGTH_RECOVERY = 0.05` at `game/game.py:91` is defined and **never referenced** — red
bases have never recovered strength. Left alone deliberately: wiring it up is a balance change, not a
supply rule, and rung A can only ever reduce blue's free drift.

### Rung A — reinforcement follows the supply lines

`game/theater/supply.py`. Recovery now depends on the **kind** of route back to a rear area:

| Tier | Route | Recovery |
|---|---|---|
| `SUPPLIED` | Road or shipping | Full |
| `AIRLIFTED` | Airfield-to-airfield only | A quarter |
| `ISOLATED` | None | Nothing |

**Gotcha that shapes the whole design:** `TransitNetworkBuilder` links every friendly airfield to
every other one as a last resort (`transitnetwork.py:186-195`), so a gate built on
`has_path_between` would read true almost everywhere and the feature would do nothing.

A coalition with **no rear area anywhere** reads `SUPPLIED`, not `ISOLATED` — small campaigns where
every base is in contact have nothing to model, and starving the whole side would be a balance change
wearing a supply rule's clothes. `supply_statuses()` computes that once per coalition, so an encircled
pocket is still correctly `ISOLATED` when a rear exists elsewhere.

The transit network is refreshed at `game.py:481` (`Coalition.end_turn`) before the gate reads it at
575, so it sees post-capture topology.

### Rung B — attacking costs more than defending

`MissionResultsProcessor.apply_battle_result`. The loser always yields the full delta. A winner that
was **pushing forward** (`OFFENSIVE_STANCES`: aggressive, elimination, breakthrough) banks only
`1 - ASSAULT_COST_FRACTION` of it; a winner that held banks the lot. Stances already modulated the
delta upstream of this — the change is in how it is *applied*.

### Rung C — the front counts the forces present

`Base.front_line_weight` = `strength x total_armor_value`. Price is the planner's own capability
rating for a ground unit, making price x count the ground analogue of the air-to-air weighting in
`game/sim/combat/capability.py`. **That module is A2A only** — it weights flights, not ground units;
do not expect to reuse it directly.

Falls back to morale alone when neither side has armour, so air-only campaigns are unaffected. No save
migration: it is computed from state that was already persisted.

### Rung D — terrain slows the advance

Each `FrontLineSegment` gets a going multiplier, 1.0 for open country up to `MAX_TERRAIN_DIFFICULTY`
(4.0) for ground vehicles cannot occupy, sampled 8 times per segment against
`landmap.inclusion_zone_only`.

**An even fight still sits at the midpoint whatever the terrain.** `_distance_for_effort_share` pins
`share == 0.5` to `route_length / 2` and weights only the travel away from it. An earlier version
mapped share directly to cumulative effort, which moved the neutral point and would have silently
shifted where every campaign's front starts.

Difficulties are cached on the instance via `getattr`, not stored on `FrontLineSegment`: pickled saves
restore segments without any new field, so a stored attribute would raise on every pre-feature save.

### Rung E — the front bulges

`FrontLineBounds` gains `sector_depths` (7 lateral samples), `point_at()`, `depth_at()` and
`polyline()`. Depths come from the room ahead of each sector, centred on their own mean so the front
as a whole does not move, and tapered to zero at both ends so the line still anchors between its two
control points.

Two consumers opted in: `flotgenerator` places ground groups along the bowed trace, and
`drawingsgenerator` draws the polyline so a salient is visible on the F10 map. The other four
consumers of `frontline_bounds` — CAS patrol legs, the DTC cartridge, and two kneeboard pages — read
only `left_position`, `right_position` and `length`, which are untouched. `polyline` pins its ends to
those exact points rather than the trig-walked approximations, which drift sub-micron.

### The front is measured against drivable ground (2026-08-23)

A defect in the shared base the five rungs sit on, inherited unmodified from upstream.
`frontline_bounds` cast one ray each way from the centre and stopped at the first
inclusion-zone boundary (`extend_ground_position`).

- `find_ground_position` returns the nearest point of the drivable stretch, which is a point
  **on its boundary**. `poly_contains` rejects a boundary point, so the centre reads as outside.
- From there the ray toward the usable ground meets the boundary at ~0 m and stops. The ray into
  ground no vehicle can enter never meets a boundary at all, and `extend_ground_position` read
  "no crossing" as "clear the whole way" and returned the full half-width.
- Result: the entire front drawn on the impassable side, none of it on the passable side.

Reproduced from a save on **Caucasus - Northern Russia**, Kutaisi/Khashuri FOB, turn 1
(`max_frontline_width` 40 km). The front ran 20.00 km left and 0.00 km right with **0 % of its
trace on drivable ground**. Along that axis the drivable ground was +0.0 to +6.2 km and +28 to
+40 km — all of it on the side that got nothing. `flotgenerator` then found `is_on_land` false
for nearly every lateral offset and took its degenerate-front fallback, which collapses groups
onto the nearest valid patch: blue bunched on one edge of the ridge, red on the other, ~15 km
apart with impassable ground between them.

The fix replaces the two ray casts with `usable_reach`, which intersects the front axis
(± `max_frontline_width`, so the run is found whichever side it lies on) with
`inclusion_zone_only`, picks the run holding the centre — or the nearest run, since the centre is
a boundary point — and caps each side at half the nominal width. Same axis, same centre, same
answer in open country; only an edge moves. `extend_ground_position` keeps its ray cast for
rung E's salient probes, with the `is_empty` branch now returning `initial` when the start is
off drivable ground, so a probe cannot report room it does not have.

After the fix, the same front: 0.00 km left, 6.15 km right, **98 % of the bowed trace on drivable
ground**, and both sides' rear areas at 2 km and 6 km depth clear.

Deliberately **not** done: spending a pinned flank's slack on the other side. It would have made
that front 40 km wide instead of 6.15 km, but it widens fronts in every campaign with terrain on
one flank and drags the fight off the supply crossing the two sides are contesting. The narrow
front here is rung D's intent — a pass is a chokepoint.

Upstreamable: `find_ground_position` and `extend_ground_position` are upstream's, unmodified, and
the defect is theirs.

**The route under that front was also wrong, and is fixed separately.** `northern_russia`'s miz
path group `Ground-4` reached the Likhi range in a single **41 km straight leg** and put its own
waypoint off drivable ground; every other route in that miz has 15-39 waypoints and hugs roads.
The front is placed by distance along the polyline, so a chord across a ridge puts the fight on
the ridge. A yaml `supply_routes:` override follows the E60/S1 instead — the Rioni valley through
Terjola and Zestafoni, then the Chkherimela valley and the Rikoti pass to Surami. Measured over 15
sampled front positions along the route:

| | miz `Ground-4` | yaml override |
|---|---|---|
| waypoints | 8 | 22 |
| longest leg | 40.9 km | 11.2 km |
| waypoints off drivable ground | 1 | 0 |
| drawn line on drivable ground | 75 % | 98 % |
| front positions on drivable ground | 10/15 | 15/15 |
| mean front width | 9.55 km | 10.18 km |

That override needed a loader fix to be safe at all: `add_supply_routes` (miz) and
`add_yaml_supply_routes` (yaml) both call `create_convoy_route`, whose `convoy_routes` dict
overwrites but whose `connected_points.append` did not — so a yaml route for a pair the miz
already defines **linked the two CPs twice**, and `ai_ground_planner` counts that list rather than
de-duplicating it. `create_convoy_route` is now idempotent on the connection.
`tests/theater/test_supply_route_drivability.py` locks both, and the duplicate test fails without
the guard.

### The map shows last turn's movement (2026-09-23)

An arrow at each front's centre, pointing the way the line moved last turn, blue if blue
advanced and red if red did; its length follows the distance, clamped to 3–12 km so it reads at
any zoom. None under 500 m. Tooltip: side, distance in NM, the base it moved toward, blue's own
stance. Red's stance is not shown. Display only — nothing about how the line moves changed.

- `FrontLine.settle_position()` replaces `update_position()` in `finish_turn`. It stores
  `previous_progress` and `settled_progress`, distance along the route from blue, so the
  difference is the movement the model produced. `hold_position()` runs on a skipped turn so
  a stale arrow does not linger. Pre-feature saves have neither field: no arrow until two
  turns have settled.
- A capture recreates the front, so a new front starts with no arrow.
- Direction comes from `blue_forward_heading` (the route's own bearing), not the bounds'
  left/right heading.
- Server: `FrontMovementJs` on `FrontLineJs.movement` (`game/server/frontlines/models.py`).
  Client: `FrontMovementLayer`, layer row `frontMovement`, a sub-row of Front lines, on by
  default.
- It makes B66 readable from the map. Checklist B139. Design note:
  `docs/dev/design/retlab-front-movement-arrows-notes.md`.

### Tests

`tests/theater/test_front_movement.py` (7) · `FrontMovementLayer.test.tsx` (2) ·
`tests/theater/test_supply_status.py` (13) · `tests/sim/test_assault_cost.py` (7) ·
`tests/theater/test_front_line_weight.py` (11) · `tests/theater/test_front_line_terrain.py` (10) ·
`tests/missiongenerator/test_front_line_salients.py` (10) ·
`tests/missiongenerator/test_front_line_usable_reach.py` (8) ·
`tests/theater/test_supply_route_drivability.py` (5).

### Deferred

- The `AIRLIFTED` multiplier (0.25) and `ASSAULT_COST_FRACTION` (0.4) are first guesses. Tune after a
  flown campaign, not before.
- Rung D reads passability only. Slope is the obvious second signal and there is no elevation source
  in the engine today.
- Sector depths are terrain-derived, so a salient sits in the same place every turn. Driving them
  from where forces actually are would need per-sector state that does not exist.

---

## §91 — Per-flight sortie records

**A vacated seat freezes the record (2026-09-21, test 37).** The DM went to spectator at
t=2601 and the Viper flew on under AI to dry tanks at t=3900; the record kept sampling it,
because a record once marked `player` was treated as human for good, and §96 credited
65 min for 43 flown. The sweep now re-checks the seat every pass: a `player` record whose
unit is neither named by `getPlayerName` nor listed by `coalition.getPlayers` gets
`player_left = <sweep time>`, is not sampled, is never made the group's AI anchor, and
counts no shots, hits or kills until a human is in the seat again — which clears the
mark, so a multiplayer reconnect into the same slot resumes rather than starts over.
`tests/lua/test_sortie_recorder_runtime.py` models both; rows B70 and B113 own the fly.

**Humans on a multiplayer host (2026-09-15, test 33).** The sweep found the host's own
jet by `getPlayerName` and missed the remote pilot in the same group, whose unit answered
that call only inside shot and hit events; he was filed as the AI wingman behind the
host's anchor and finished with no track. The sweep now refreshes a set of human unit
names from `coalition.getPlayers` each pass, treats a record already marked `player` as
human, and lets the first named event fill in a name the sweep could not read.
`tests/lua/test_sortie_recorder_runtime.py` models the case; row B70 owns the fly.

**Design note:** [retlab-retribution-long-view.md](design/retlab-retribution-long-view.md) seam 1.

### What was wrong

`StateData` (`game/debriefing.py:129`) was a loss ledger. Everything else about a two-hour mission was
discarded, and every feature that needed more cut its own channel through `state.json` — seven of
them: recon captures, minefields, cruise magazines, naval magazines, QRA survivors, ejections,
rescues. Each carries its own Lua writer, reconcile function, pre-feature-save clause and
double-count guard. **Seven holes in one wall is a missing schema, not seven features.**

### What it is

`resources/plugins/base/sortie_recorder.lua` samples airborne aircraft every 30 s and counts shots,
hits and ejections from the shared event handler. Per aircraft: track (time, position, altitude,
fuel), first and last seen, shots, hits, ejected, and whether a human ever occupied the slot.
`game/sortierecord.py` parses it and derives duration, distance flown, fuel at end and peak altitude. Duration is the airborne span: the recorder notes the first and last sample where `unit:inAir()` (2026-09-22, test 38); a `state.json` without them falls back to `last_seen − first_seen`.

Loads before `dcs_retribution.lua` in `resources/plugins/base/plugin.json`.

### Hard constraints

- **Vanilla DCS only. Never Tacview.** It is a paid third-party program; a feature built on its
  `.acmi` export would silently do nothing for most players. Tacview stays useful for checking that
  what the recorder reports is true, and for hand measurement (`game/data/carrier_deck_decor.py:42`).
- **Records are keyed by unit, never by group.** `group:getUnits()` returns only the *living* units,
  so a fixed index is not a fixed aircraft. The first version keyed by group and sampled `units[1]`:
  when the lead died the track teleported onto a wingman and `distance_flown` counted the jump. The
  harness stub now models the same filtering, so the regression is caught headlessly.
- **Every human-crewed slot is sampled; an AI group samples one anchor jet**, held until it dies
  rather than read off an index. Four humans in one group do not fly the same track; sixty AI in
  formation do, so paying per-unit for them buys nothing.
- **The track rides only on the final write.** `state.json` is rewritten every 15 s — 480 times over
  a two-hour mission — and a 60-group track set is ~1 MB at 70 bytes per sample. Including it in
  every write puts half a gigabyte of `json:encode` on the sim thread of a mission that already has
  no frames spare. `sortie_recorder_payload(include_track)` builds a counters-only table for the
  periodic writes. A crash therefore costs the track but keeps everything the writes carried before
  this feature existed.
- **The track holds 480 samples** — four hours at 30 s, so a tanker or AWACS orbiting a long mission
  keeps its start. Only an in-memory Lua table, because of the constraint above.
- **A record with an empty track is counters-only** — a wingman that fired but was never
  position-sampled. `sorties_flown()` excludes them, or the sortie count inflates by the group size;
  their weapons still count toward the flight.
- **A record that never moved is ramp furniture, not a sortie.** `_spawn_unused_for` parks a
  squadron's untasked airframes as 1-ship `Completed` BARCAP groups, and the sweep — which walks
  `coalition.getGroups` by category — cannot tell them from flights. Two defences, because either
  alone leaves half the problem: the recorder collapses a stationary run to its two endpoints
  (`STATIONARY_M = 25`), and `SortieRecord.flew` requires `MIN_SORTIE_DISTANCE_M = 1000` of
  sampled track before the record counts as a sortie or contributes hours. Test 12's file was
  1.18 MB of which 68% was 82 parked jets writing 86 identical samples each, and its SITREP would
  have read *"145 sorties, 96.7 hours airborne"* for a mission 46 aircraft flew. Replayed against
  that file the two fixes give 377 KB and *"46 sorties, 28.0 hours airborne"*.
- **The `fuel` field is not a fuel state when `ai_unlimited_fuel` is on.** That setting writes
  `SetUnlimitedFuel(True)` at `group.points[0]` and turns it off again only between the join point
  and the racetrack, so most AI records log one unchanging value for the whole mission (101 of 143
  in test 12, including an F-14A that flew 280 NM at 9,144 m on a flat 1.000). Nothing to fix here;
  a consumer must not present it as remaining fuel or average it.
- **Every entry point is called through `pcall`** from the event handler that also does loss
  reporting. A recorder fault must never cost a mission its results.
- Parsing degrades rather than fails: missing channel, an empty Lua table serialised as `[]`, a newer
  `version`, a malformed flight, a malformed track sample — all yield "no data" or skip the bad entry.

### First consumer

The campaign SITREP gains a sortie line: *"14 sorties, 22.5 hours airborne, 31 shots for 12 hits"*.
The first thing the campaign has ever said about a mission that is not a casualty count.

### Tests

`tests/test_sortie_records.py` (20) · `tests/lua/test_sortie_recorder_runtime.py` (16). The harness
gained `UnitFake:getFuel`, `addGroup` carries the spec's `fuel` field, and `GroupFake:getUnits` now
filters on `isExist()` to match DCS.

### Deferred

- **The seven existing channels are not collapsed yet.** This adds the general schema; migrating
  recon captures, magazines and the rest onto it is the follow-on that pays the debt back.
- No consumer reads the track itself yet. Route-quality feedback to the planner is the obvious next
  one, and it is why the track is recorded rather than just the totals.

### Test 7 (2026-08-17) — first flown read, one fix

The records reached `state.json` and the counters were sane: 165 entries, 80-point tracks,
per-unit shots and hits, and the player's own flight correctly flagged. Two things did not
belong in `flights`:

- Every AAA piece and Avenger that shot at the package, because `sortie_recorder_on_shot`
  and `_on_hit` recorded whatever DCS named as the initiator. §91 is a record of *flights*.
- One entry keyed `""` whose type was `weapons.shells.Rh202_20_HE` — a shell reaches the hit
  handler as an initiator and its `getName` is the empty string, so every cannon round in
  the mission collided into a single record.

`record_for` now rejects a blank name and, when creating, requires
`getDesc().category` to be AIRPLANE or HELICOPTER. The category check runs only on creation,
so a jet whose `getDesc` fails after it dies keeps counting on the record the sampler already
made. Pinned by `test_a_ground_unit_that_shoots_never_becomes_a_flight` and
`test_an_unnamed_initiator_never_becomes_a_flight`; the Lua harness gained `Unit.Category`
and `UnitFake:getDesc`.

### Shots and hits are commensurable (2026-08-18)

The SITREP renders the day's flying as `"N shots for M hits"`, which only reads as a hit rate
if M cannot exceed N. Test 8 reported **106 shots for 381 hits**. DCS raises one
`S_EVENT_SHOT` per weapon released and one `S_EVENT_HIT` per *impacting object*, and a
cluster weapon's submunitions are different objects from the one that was shot, so two
CBU-105 releases scored 68 hits.

`S_EVENT_SHOT` now records the weapon's key (`Weapon:getName()`, falling back to `id_`);
`S_EVENT_HIT` counts only when the impacting weapon matches one the recorder saw fired, and
clears it so only the first impact counts. Pending keys are pruned on the 30 s sweep at a
900 s TTL so a weapon that misses cannot be consumed by an unrelated later hit.

Deliberate consequence: **gun hits are no longer counted**, because DCS raises no shot event
for them and there is nothing to rate them against. An uncountable shot must not become a
free hit.

## §92 — What's New

The fork lands several player-visible changes a week, and most of them are runtime
behaviour CI cannot exercise — the whole point of the in-game-pass checklist. Knowing
*what changed* is only half of it; the other half is knowing *how to see it* on the next
flight. That was living in `docs/`, which is not open while anyone is flying.

A **What's New** button on the toolbar opens a window listing the recent changes, newest
first, each with a **Watch for** line saying what to look for in the next mission.

### The feed is its own file, not the changelog

`changelog.md` cannot answer "what changed lately". It is grouped by area
(`[Campaign]` / `[Mission Generation]` / `[UI]`), not ordered by date: two changes landing
the same afternoon get written seventy lines apart, so position carries no recency at all.
Adding a date to every historical entry to fix that would be a bigger edit than the feature.

So the feed is `resources/whatsnew/` — **one YAML file per entry**, named
`<date>-<slug>.yaml`, one per player-visible change, five fields. It was one
`whatsnew.yaml` until 2026-09-29; every parallel PR added its entry at the top of the same
list and conflicted, so it was split so no two PRs touch the same file:

| Field | |
|---|---|
| `date`, `title`, `change` | required; what changed, in the reader's terms |
| `watch` | required — **the reason the file exists**: what to look for in the next mission |
| `row` | optional in-game-pass checklist row that owns the verdict (`B39`) |
| `pr` | optional PR number, rendered as a link |

It lives in `resources/`, which PyInstaller already bundles wholesale, so it ships with no
spec change.

### Load path: never raises

The toolbar action is live **before a save is opened** — it describes the build, not the
campaign, so it sits outside `enable_game_actions` alongside nothing else. That means a
malformed data file must cost an empty window and nothing more: a missing file, bad YAML,
a file with no entry, or a single half-written entry are each logged and skipped,
and `load_whats_new` returns `[]` rather than raising into the toolbar.

Ordering is a **stable** sort on `date` descending over the files read in reverse name
order, so same-day entries sort by file name. A single file holding an `entries:` list
still loads (the tests use it), but `test_every_feed_file_holds_exactly_one_complete_entry`
keeps the shipped feed at one entry per file.

### Files & tests

- `game/retlab/whatsnew.py` — `WhatsNewEntry`, `load_whats_new`, `DEFAULT_LIMIT` (10).
- `resources/whatsnew/` — the curated feed, one file per entry.
- `qt_ui/windows/whatsnew/QWhatsNewWindow.py` — the dialog. Renders through a
  `QTextBrowser` with inline styles, because Qt's rich-text engine does not read the app's
  QSS token sheet; entries are separated by a rule, since ten stacked blocks with only
  margins between them read as one wall of text (the first render did).
- `qt_ui/uiconstants.py` — `ICONS["What's New"]`. Only the light icon set ships an `info`
  glyph and a `QPixmap` built from a missing path is silently null, so it falls back to the
  notes glyph rather than leaving the button iconless under the other three themes.
- `qt_ui/windows/QLiberationWindow.py` — the action, after a separator at the end of the
  toolbar.
- Tests: `tests/retlab/test_whatsnew.py` (9 — ordering, the cap, and every degrade
  path), `tests/test_whats_new_window.py` (6 — offscreen render, escaping, the empty feed,
  and that the icon key the toolbar asks for exists).

**No in-game pass owed.** It is a window over a data file; the offscreen render test covers
what a human would check.

## §93 — Region priorities

Per-control-point BLUE planning emphasis — upstream #686's map-control idea reworked to BMS's
PAK weighting. Design and the full rationale:
[`retlab-region-priorities-notes.md`](design/retlab-region-priorities-notes.md); the study
inputs are [`retlab-falcon-bms-campaign-notes.md`](design/retlab-falcon-bms-campaign-notes.md)
candidate 4 and red-one1's upstream draft
[#686](https://github.com/dcs-retribution/dcs-retribution/pull/686), credited as the
surface's origin.

### The rule

Every control point carries a BLUE planning priority — `EMPHASIZED` / `NORMAL` /
`DEPRIORITIZED` / `IGNORED`, default `NORMAL`. When the `region_priorities` setting is on,
the BLUE auto-planner's offensive target ordering multiplies each target's effective range
by the owning CP's factor (0.5 / 1.0 / 2.0), and an `IGNORED` CP's targets are dropped from
auto-planning. **A weight, never a fence** — manual packages, ROE and rescue tasking are
untouched, which is what keeps this clear of §40's removed ROE zones. Red never reads it
(seam 7), and it is host-set campaign state like every other doctrine control.

### Shape

- `game/retlab/region_priorities.py` — the enum, the factor table, `planning_factor()`
  (the single gate: identity when off, red, or CP-less; `None` = drop).
- `ControlPoint.blue_region_priority` — a getattr-guarded property
  (`game/theater/controlpoint.py`), so pre-§93 saves read `NORMAL` with no migration.
- `ObjectiveFinder._targets_by_range(..., weighted=True)` weights `threatening_ships`,
  `oca_targets` and `motorpool_targets`; `strike_targets` applies the same factor in its own
  inline sort (it carries a per-TGO dedup). `downed_pilots` and the ground-war CP rankings
  deliberately stay unweighted — a rescue must never rank lower for its region.
- The §63 auto raids and the §44 carrier strike honor `IGNORED` beside their existing
  fog gates (`cruise_raids.py`, `carrier_ops.py`) — auto fires obey the same courtesy.
- **Ships and battle positions are gated at the task, not the list** (fixed 2026-08-20 after
  an IGNORED red carrier still drew an anti-ship package plus escort). `state.enemy_ships` is
  threat data as well as a target list — it feeds `_rebuild_threat_zones` — so filtering it
  would route blue over the very carrier it was told to ignore. `AttackShips` and
  `AttackBattlePositions` (BAI *and* its Armed Recon leg) call `auto_planning_skips` instead.
  When adding an offensive task, gate the tasking; never the threat picture.
- Setting: `region_priorities` (Campaign doctrine page, default OFF; Auto-planner behaviour
  group on the RetLab Features page).

- **SEAD/DEAD has two tiers and only one of them is gated** (fixed 2026-08-20). The
  opportunistic tier in `DegradeIads` picks LORAD/MERAD sites off `enemy_air_defenses` — that
  is a choice of where to work, so it honors `IGNORED`. The reactive tier
  (`threatening_air_defenses`) is deliberately **not** gated: a SAM shooting at a package
  flying somewhere else is a threat response, and muting it would send flights into a ring
  nothing was allowed to suppress. `detecting_air_defenses` is reactive for the same reason.

### Two axes, added 2026-08-20

§93 shipped as one axis: a priority per control point. It now has a second, and they
multiply.

| Axis | Set where | Answers |
|---|---|---|
| **Place** | the CP dialog, or a single target's own dialog | "not that base" / "not that factory" |
| **Kind** | the **Target Priorities** toolbar window | "not factories, anywhere" |

- **Per-target override** (`TheaterGroundObject.blue_region_priority`, `None` = inherit).
  The combo carries five entries, because *Inherit* and *Normal* stop meaning the same
  thing the moment the parent is `IGNORED`: an explicit value beats the control point in
  **both** directions, so one target inside an ignored base can still be planned. Without
  that the override could only ever subtract, which is half a feature.
- **Target families** (`TARGET_FAMILIES`) group the 20 plannable categories into seven:
  Air defense, Command and control, Infrastructure, Logistics, Armor, Naval, Missile
  sites. Per-*category* control was rejected as twenty combo rows on one page — the fine
  grain is the per-target override. `fob` is deliberately absent: that TGO is the FOB
  structure and is never targetable. Stored on `Settings.blue_target_family_priorities`,
  a plain field with no option metadata so the auto settings dialog never renders it.
- **Composition:** `factor = place x kind`. An emphasized region (0.5) with deprioritized
  factories (2.0) reads as 1.0 — they cancel, which is the intuitive answer.
- **`IGNORED` is asymmetric on purpose.** A place-IGNORED is overridable per target; a
  kind-IGNORED is absolute and nothing reopens it. "No factories" is theater-wide policy;
  "not this base" is a judgement a single target can be carved out of.
- **The window shows live counts.** A priority means nothing until you can see it moves
  31 air-defence sites and one ship. Two tests pin the family table itself: every category
  in it is a real one, and no category is in two families.

### Known v1 limits

- Convoy/cargo-ship interdiction and front-line (CAS) tasking are unweighted by design —
  they follow the ground war, not the strike map.
- Friendly-CP priorities are accepted by the model but nothing reads them yet (defensive
  emphasis is a possible follow-on).

### Files & tests

- `game/retlab/region_priorities.py` · `game/theater/controlpoint.py` ·
  `game/commander/objectivefinder.py` · `game/retlab/cruise_raids.py` ·
  `game/retlab/carrier_ops.py` · `game/settings/` · server/web UI under
  `game/server/controlpoints/` + `client/src/`.
- Tests: `tests/retlab/test_region_priorities.py` (the factor gates, the ordering
  effect, the IGNORED drop, the rescue exemption, the off-gate identity).

**In-game pass owed:** none for the planner half (headless-checkable — generate a turn with
an emphasized axis and compare the ATO's target spread against a NORMAL baseline); one UI
pass row for the CP-dialog control once the web UI lands (B89).

---

## §94 — Smart threat reaction

Only the flight a missile is actually guiding on goes defensive. Design and the adoption
record: [`retlab-ai-threat-reaction-notes.md`](design/retlab-ai-threat-reaction-notes.md).
Ported from juanjux's fork
([#63](https://github.com/juanjux/dcs-retribution/pull/63)) at its post-rewrite head, not at
the PR — see **Why head, not the PR** below.

### The rule

DCS' `REACTION_ON_THREAT` option is set to Evade Fire on nearly every flight
(`game/missiongenerator/aircraft/aircraftbehavior.py`, ~18 configurations), and Evade Fire
breaks *every* aircraft that perceives a launch. One S-300 or naval salvo therefore scatters
dozens of jets from packages the missile was never aimed at.

The `ai_reaction` plugin parks every airplane at **Passive Defense** — fly the route, use
chaff and flares, hold formation — and switches to **Evade Fire** only the group that
`weapon:getTarget()` names, until that missile stops existing. The target is read from the
engine; nothing is inferred from geometry.

### Constraints

- **`REACTION_ON_THREAT` is a per-group option.** The targeted *flight* evades, not the one
  jet. That is still ~2–4 aircraft instead of ~45.
- **A sweep pays `setOption` only on a state transition**, and a shot that resolves to a
  ship or ground target is dropped at `S_EVENT_SHOT` with no re-check. The first version did
  neither and stalled the sim during an anti-ship salvo. Do not re-add a blanket
  per-airplane `setOption` pass.
- **AIRPLANE only.** Helicopters keep stock Evade Fire — they have no formation to hold.
- **§61's scrambled bandits are exempt.** `redscramble-config.lua` sets them Evade Fire on
  purpose; without the exemption the baseline stomps them back within 10 s. Any plugin can
  claim the same exemption by writing `dcsRetribution.aiReactionExempt[groupName] = true`,
  and should clear it when the group dies.
- **DEBUG is off by default here** (it ships on in juanjux's copy). On, every tagged shot
  prints on screen for all players and every untagged shot writes to `dcs.log`.
  **The toggle was inert until 2026-09-20**: the script was a `scriptsWorkOrders` file
  reading its options at file scope, before the config trigger created them. It is a
  `configurationWorkOrders` file now, and `tests/test_plugin_script_pass.py` fails any
  early-pass script that reads its own config table at file scope.

### The trade, stated plainly

This is a doctrine change, not a bug fix. A flight facing a missile whose target the engine
will not resolve — the re-check runs once at 1 s and then gives up — flies straight instead
of breaking. Against the fork's SAM density (§41 belts, §60 radar redundancy, the IADS net) that
can raise AI attrition. The plugin toggle is the whole gate: off restores stock DCS
behaviour with no other change.

### Shape

- `resources/plugins/ai_reaction/ai_reaction.lua` — the runtime. `S_EVENT_SHOT` → `tryTag`;
  a 1 s `watch` releases a flight when its missile stops existing; a 10 s `baseline` sweep
  re-parks anything clear, with a full re-assert every sixth sweep (≈1 min) to catch groups
  the engine reset to Evade Fire on activation and to prune destroyed ones.
- `resources/plugins/ai_reaction/plugin.json` — default **on**, `DEBUG` default **off**.
- `resources/plugins/redscramble/redscramble-config.lua` — `claim_exempt` on spawn,
  `release_exempt` in the bandit prune loop.

### Why head, not the PR

[#63](https://github.com/juanjux/dcs-retribution/pull/63) merged 2026-07-08 and was rewritten
2026-07-15 because it *"was stalling the sim"* during a naval missile storm: the merged
version ran a `setOption` over every airplane group every 5 s and logged every shot
unconditionally. Given §63 raids, §81 magazines and the carrier campaigns, the fork would
have hit the same wall. The file here is the rewritten one.

### Files & tests

- `resources/plugins/ai_reaction/` · `resources/plugins/redscramble/redscramble-config.lua` ·
  `resources/plugins/plugins.json` · `game/retlab/features.py`.
- No Python surface, so no pytest coverage. The `lint.yml` Lua syntax gate covers both files;
  the `tests/lua/` harness does not model `weapon:getTarget()` or controller options, so
  behaviour is an in-game question.

**In-game pass owed:** B97 — one salvo, and only the targeted flight breaks.

## §95 — Pinned bullseye

Design note: [`docs/dev/design/retlab-bullseye-notes.md`](design/retlab-bullseye-notes.md)

Built 2026-08-24. Replaces upstream's `Game.set_bullseye`. No plugin, no setting.

### What upstream did, and what was wrong with it

Upstream re-derived both bullseyes on every `initialize_turn` — which is not once a turn;
cheat capture, a front-line move and any TGO buy or sell run it too:

```python
player_cp, enemy_cp = theater.closest_opposing_control_points()
blue.bullseye = Bullseye(enemy_cp.position)
red.bullseye = Bullseye(player_cp.position)
```

Four local saves, probed headlessly 2026-08-24:

- **`autosave` (Marianas, t1): blue's bullseye was `CV 1143.5 Admiral Kuznetsov`** — a
  carrier, in open water. Fleets are in `player_points()` / `enemy_points()`, so nothing
  excluded them. A blue carrier is player-draggable, so moving your own boat moved *red's*
  bullseye.
- **`Maybe 414` (Caucasus, t1): 5 of 19 blue packages within 10 NM of the bullseye, one at
  0.0 NM** — an Armed Recon fragged against the anchor FOB itself.
- Both Syria saves: 5 of ~30 packages within 10 NM.
- Caucasus also carries a `Turkey` `OffMapSpawn`, an eligible anchor that happened not to win.

### The two rules

**The anchor cannot be a boat or an off-map spawn.** `ConflictTheater.bullseye_anchors()`
runs the same nearest-opposing-pair search over a filtered candidate list. A side with
nothing else falls back to its full list — a boat anchor beats an assertion.
`closest_opposing_control_points()` is untouched, so `AirConflictDescription` keeps
upstream's conflict centre.

**The pin is for the campaign, not the turn.** `Coalition.anchor_bullseye()` keeps the
existing point unless it has drifted more than `MAX_DRIFT` (80 NM, `game/theater/bullseye.py`)
from where it would be re-derived now. Repeated `initialize_turn` calls in one turn are
idempotent.

**The kneeboard names the place.** `Coalition.bullseye_anchor_name` carries the control
point the bullseye sits on, and `BriefingPage._bullseye_line()` renders one row with all
three facts — where, the coordinates, and whether it just moved:

```
Bullseye: King Abdullah II — 32°00'20"N 36°13'25"E
Bullseye: FOB Agrihan — 18°46'34"N 145°39'52"E   ** MOVED THIS TURN **
```

`bullseye_moved_on_turn` gates the banner. A first pin is not a move, and a re-anchor onto
the same point is not a move. **One line, not two** — the BLUF's duplicate BULLSEYE line
was struck on the brief-sheet rework (§4); put anything new on `_bullseye_line()`.

Nothing is authored per campaign — the DM's call is that the point is generated so any
future campaign works with no yaml edit.

### Save migration

`Coalition.__setstate__` defaults `bullseye_pinned` to **False**. A pre-pin save's bullseye
may be sitting on a boat, so it re-anchors once under the new rule and is pinned after that.
Measured: the three land saves re-anchor in place (0.0 NM, no banner); Marianas moves blue
61.4 NM off the Kuznetsov onto FOB Agrihan and banners once. All four stable across five
further turn inits.

### Why it matters more here than upstream

More fork surface hangs off this one point than upstream's: the Hornet A/A waypoint (§74),
the Tomcat `XB` reference and `XHA` threat axis, the kneeboard `Bullseye:` DMS line, and
every `Bullseye <brg> for <nm>` cue on the SEAD and threat-intel pages.

### Files & tests

- `game/theater/bullseye.py` (`MAX_DRIFT`, `Bullseye.drifted_from`) ·
  `game/theater/conflicttheater.py` (`bullseye_anchors`, `_closest_opposing_pair`) ·
  `game/coalition.py` (`anchor_bullseye`, pin state, migration) · `game/game.py`
  (`set_bullseye`) · `game/missiongenerator/kneeboard/` (the banner) ·
  `game/retlab/features.py`.
- `tests/theater/test_bullseye.py` — 10 tests: the fleet and off-map skips, the
  boats-only fallback, that `closest_opposing_control_points` still sees the fleet, the
  first pin, the hold inside drift, the move beyond it, both migration cases, and the
  drift threshold itself. `tests/test_briefing_page_bullseye.py` — 3 tests on the
  kneeboard row: the place before the coordinates, the unnamed fallback, and the banner.

**In-game pass owed:** B98 — the bullseye is the same place it was last mission.

## §96 — Player career logbook

Built 2026-09-08. Answers upstream issue
[#965](https://github.com/dcs-retribution/dcs-retribution/issues/965). No design note — this
section is the deep dive. Gate: `pilot_career_logbook` (RetLab Features → Pilots & careers,
default **ON**).

### What was wrong

The campaign knew who a pilot was, whether they were alive, and how many times the ATO had
put them in a seat. It never knew what any of them had **done**. `PilotRecord` was one
integer, `missions_flown`, and its only consumer was the AI skill ladder.

Meanwhile §91 records what every aircraft in a mission did — track, hours, shots, hits,
ejection — and then throws all of it away at end of turn. The two halves were one lookup
apart and nothing joined them: `UnitMap.flight(unit_name)` has returned
`FlyingUnit(flight, pilot)` since long before either feature existed.

### What it is

A permanent per-pilot career, folded once per turn when mission results are committed, and a
page that reads it.

| Field | Source |
|---|---|
| `sorties` | §91 records where `flew` is true |
| `combat_sorties` | those on an air-to-air, air-to-ground or escort task |
| `flight_seconds` | the record's `duration` — the span from the first sample in the air to the last (`first_airborne`/`last_airborne`, 2026-09-22; before that it ran from slot-in, so a cold start logged its taxi), from a record §91 freezes when the human leaves the seat (2026-09-21), so time the AI flies the vacated jet is not the pilot's |
| `shots`, `hits` | the record's counters |
| `air_kills`, `ground_kills`, `naval_kills` | **new** — `S_EVENT_KILL`, see below |
| `ejections` | the record's `ejected` flag |

`game/retlab/career.py` owns the fold and the rank walk.
`game/sim/missionresultsprocessor.py:commit_pilot_careers` calls it.
`qt_ui/windows/PilotLogbookDialog.py` renders it, opened by a **Logbook** button on the
squadron dialog.

### Kill attribution — the one new channel

`S_EVENT_KILL` is the only DCS event that names a **killer**. Every other loss channel in
`dcs_retribution.lua` records the victim, which is why the campaign has never been able to
say who shot anything down. `sortie_recorder_on_kill` counts it onto the initiator's §91
record and splits it by the target's `getDesc().category`.

### Hard constraints

- **Both coalitions must resolve and differ before a kill is credited.** A blue-on-blue is
  not an air kill, and a target whose coalition cannot be read is left uncredited rather than
  guessed at. A logbook is worth less than nothing if its numbers are generous.
- **A ground unit that kills a jet never becomes a flight.** The same rule §91's shot handler
  learned in test 7: the AAA that downed you is an initiator too, and these are records of
  *flights*.
- **Only records that flew add a sortie.** A counters-only wingman entry would add one for
  a jet that was never position-sampled — once per member of the formation — and a parked
  airframe one for a jet that never moved (§91's `MIN_SORTIE_DISTANCE_M`). A parked record
  is skipped outright. A counters-only record still folds its shots, hits, kills and
  ejection (2026-09-23): on test 39 the wingmen held 9 of blue's 17 air kills and 7 of 17
  ground kills, and until then none reached a career. AI wingmen still get no sortie or
  hours, so pass item 5 of B113 stays open for them.
- **`missions_flown` is not `sorties` and must not be merged into it.** The old field counts
  ATO *assignments*, incremented for every roster seat whether or not that jet moved, and
  `Squadron.pilot_skill` reads it. Changing it would move every AI pilot's skill tier.
- **Gun hits are still not counted**, inherited from §91: DCS raises no shot event for them,
  so there is nothing to rate them against.
- **A record, never a reward.** Nothing here unlocks an aircraft, changes availability,
  or gates a mission. That was explicit in the issue and it is what keeps the feature
  additive.
- **The resolver is wrapped.** The fold runs inside mission-results commit; a lookup fault
  costs one record, never the turn's results.

### Ranks are data

`resources/pilot_career.yaml`. The fork ships campaigns spanning many air forces and seventy
years, so a ladder hard-coded to one service would be wrong for most of them. Three ladders
(commonwealth, soviet, and a fallback used by everything else); a squadron picks the first
ladder naming its DCS country, else the fallback.

`requires:` is a "field must be at least this" map over the career record. A requirement
naming an unknown field **rejects its entry** rather than dropping the requirement — a
dropped requirement would be met by everyone on their first sortie. The rank is the highest
grade whose requirements are met, walked to the end of the ladder rather than stopping at the
first miss, so a ladder mixing requirement fields cannot strand a pilot on a low rung.

### Awards — removed 2026-09-22

DM call. Nine awards lived in the same data file, granted after each fold and never taken
back, and each one earned put an `Award: <pilot> — <names>` line on the SITREP for every
BLUE pilot, AI included. `First Sortie` needed one sortie, so a turn-1 SITREP carried one
award line per BLUE pilot who flew, below the losses it exists to report.

The constraint to keep: **a per-pilot line on the SITREP scales with the roster.** Anything
that adds one again must be capped or limited to human-flown seats.

### Save migration

`PilotRecord.__setstate__` defaults every new field. A campaign carried over from an older
build starts its careers at zero — the honest degrade, because the sortie records those turns
would have been folded from are long gone. The logbook page says so rather than showing a
wall of unexplained zeroes.

It also drops the `awards` key a pre-2026-09-22 save carries. An old save's pickled `Sitrep`
keeps its `award_lines` attribute; nothing reads it.

### Tests

`tests/test_pilot_career.py` (17) · the old-save award case in `tests/test_sitrep.py` ·
four kill cases added to `tests/lua/test_sortie_recorder_runtime.py`.

### Deferred

- **Red careers accumulate but have no surface.** The fold runs for both coalitions because
  the bookkeeping is free.
- **No per-campaign rank ladders.** A campaign yaml cannot yet name a ladder, so an era-
  specific service ladder means editing the shipped data file.
- **`missions_flown` still counts assignments.** Re-pointing the skill ladder at `sorties`
  would change AI pilot progression across every campaign and needs its own call.

## §97 — Lifetime pilot profiles

Built 2026-09-09. Gate: `lifetime_pilot_profiles` (RetLab Features → Pilots & careers,
default **ON**). No design note — this section is the deep dive.

### What was wrong

§96 gave every pilot a career and put it **inside the save**. A campaign's pilots are
generated with the campaign, so starting a new one hands you a fresh roster at zero. The
thing a person actually wants recorded — *their own flying, across everything they have
ever flown in Retribution* — had nowhere to live.

### What it is

A second destination for the same §91 sortie records: `pilot_profiles.json` under the Saved
Games tree (`game/persistency.py:pilot_profiles_path`), outside every save, the same shape as
the §43 flight-defaults store. `game/retlab/pilot_profile.py` owns it;
`commit_pilot_profiles` files a mission's human-flown sorties as results are committed.

Per profile: lifetime totals, a per-aircraft breakdown, the campaigns flown, and a rolling
list of the individual flights — date, campaign, aircraft, task, minutes, kills, ejection.

`qt_ui/windows/PilotProfilesDialog.py` renders it, from a **Pilot Logbook** toolbar button
that sits outside `enable_game_actions` so it opens with no campaign loaded. That is the
point of the feature, so the button has to work there.

### Identity is the DCS player name

The recorder already called `getPlayerName()` per slot and threw the answer away, keeping
only a boolean. It now records the name, and a profile is keyed on it.

- **No setup.** The first mission you fly creates your profile.
- **A host records everyone.** In a squadron event all eight humans get their own profile
  rather than collapsing into one, which the "one local profile" alternative would have done.
  **Test 33 (2026-09-15) found the one case this missed:** a second human in the host's own
  group answered `getPlayerName` in the shot events but not in the recorder's sweep, so he
  had no track and the fold skipped him. The recorder now also reads `coalition.getPlayers`
  (§91). Unflown since.
- **The key never moves.** Renaming sets a `display_name`; renaming the key would orphan the
  career from the seat that feeds it.

### Hard constraints

- **The store is append-only with nothing to re-derive it from.** There is no campaign to
  recompute a lifetime career from, so a bad write is permanent. Everything below follows
  from that.
- **A mission is folded exactly once, and the guard is keyed on the GAME.** `Game.stable_uid()`
  mints a uuid on first use (lazily set, persisted, `__setstate__`-defaulted, so old saves
  need no migration). Keying on campaign name plus turn would make a replay's turn 1
  indistinguishable from the playthrough already recorded, and silently drop it.
- **The guard is per profile, not per store, and decided before the fold.** A pilot who
  joined the event late has not logged that mission even though everyone else has. A pilot
  who ejected and took a second slot flew two sorties in it and logs both: only a profile
  that already had the mission on file when the fold began is skipped. The first version
  appended the guard id after the first record, so the second slot read as a replay
  (2026-09-11 audit).
- **The store is written atomically.** Encoded first, written to a sibling temp file,
  flushed to disk, then moved over the old file. The first version wrote in place, and a
  crash mid-write would have truncated every career at once (2026-09-11 audit).
- **The first human on a slot keeps the sortie.** A mid-mission handoff has no more claim on
  it than the pilot who took it off, and crediting whoever held the seat at the last sweep
  would hand a whole flight to someone who flew the last ten minutes.
- **Only records that flew, and only human-crewed ones.** An AI jet has no career; §91's
  counters-only and parked-airframe records are not sorties (`MIN_SORTIE_DISTANCE_M`).
- **A flight whose unit the campaign cannot resolve is still logged**, with a generic task.
  A human flew it; losing the sortie to a failed lookup is worse than a vague label.
- **Its own setting, separate from §96.** This one writes outside the save, and that is
  exactly the thing a player might want to decline while keeping campaign careers.
- **No ranks.** A user call: the lifetime page is numbers. A rank belongs to a service and a
  campaign, so it stays with §96.
- **Nothing here raises.** It runs inside mission-results commit and backs a window that
  opens with no game. A store that cannot be read or written is logged and skipped.

### Caps

`MAX_LOG_ENTRIES = 2000` flights per profile and `MAX_LOGGED_MISSIONS = 1000` guard ids.
Totals keep counting past the log cap; only the entry list is trimmed, oldest first. The
window lists the newest 60 and says how many older ones the store still holds.

**Do not exercise the real cap in a test.** Every fold rewrites the whole store, so folding
2,000 entries is quadratic — the first version of `test_the_log_is_capped_and_keeps_the_newest`
took 28 of the suite's 30 seconds. Monkeypatch the constant instead.

### Tests

`tests/test_pilot_profiles.py` (18) · four player-name cases in
`tests/lua/test_sortie_recorder_runtime.py`.

### Deferred

- **No export.** A CSV or printable logbook is the obvious next thing and is not built.
- **No merge or delete in the UI.** Changing your DCS name starts a second profile, and the
  only fix is editing the JSON by hand.
- **Red humans get profiles too.** Free, and harmless, but nothing surfaces the coalition.

---

## §98 — Neutral-faction border defense

Every nation on the map is drawn with its real border, the map's own nation included,
and what each one does about an intruder follows from two facts. **Alignment is
derived, never authored** — a nation hosting a RED or BLUE airfield is aligned with
that team, one hosting **both** is `contested` (the battlefield: grey, never enforcing,
claimed by neither side's QRA), and one hosting neither is the neutral. Counted over
every zone of the same country, not per polygon: Russia is two zones on Kola, and
per-piece counting drew Karelia — the largest zone on the map — as an uninvolved
neutral that intercepts you, in a campaign where Russia is the enemy. `posture:`
overrides. **Overflight is derived from the same airbases** (DM call, 2026-08-26) — a
country you fly from has let you in, one both sides use has let both in, and one
with no coalition base inside it has invited nobody and defends. `overflight:`
overrides. The dated posture table used to answer this and was dropped as the
source: it made consent a fact about the calendar rather than about the campaign
in front of you, reading Sweden and Finland `closed` in 1983 while both sides
flew combat sorties off their runways, and it cannot see a base change hands.
The research is kept and still supplies the airframe. **Altitude floors went
with it** — they came from its `contested` bucket, so a floor is now authored
only and a defending country defends at any height. **A refusing neutral stands
live SAM batteries inside its own border from mission generation** (the fighter
patrol it used to fly was dropped 2026-09-07, DM call — scope is the SAM). **The era picks the tier and the country's size picks the rung within it**
(DM call 2026-09-10). Legacy is SA-2 / SA-3 / SA-5, modern is SA-10 / SA-11,
with Hawk, Patriot and Rapier for the twelve authored western-equipped nations.
The size measure is the largest circle that fits inside the country: over 100 NM
of room takes the top rung (SA-5 legacy, SA-10 or Patriot modern), 25–100 the
middle (SA-2 or SA-11, Hawk), under 25 the bottom (SA-3, Rapier). **The top rung
is the same band in both eras** — a country large enough for an SA-5 in 1982 is
large enough for an SA-10 in 2004, which is the point of two tiers rather than
two scales. Over the 63 shipped zones that is **1982: 17 SA-2, 16 Hawk, 12 SA-3,
10 SA-5, 8 Rapier** and **2004: 17 SA-11, 12 SA-3, 11 Hawk, 10 SA-10, 8 Rapier,
5 Patriot**. **Dates are export dates, not in-service** — checked against the
1982 Falklands column, where in-service dates handed Argentina a Buk. **Two reach figures, on purpose.** `reach` is the DCS launcher's own
`threat_range`, sourced and confirmed against a stock no-mod export; the earlier
hand-picked numbers were unsourced and disagreed with it inconsistently.
`placement_reach` is **60 % of it**, and is what the siting uses (DM call
2026-09-10). The database figure equals `air_weapon_dist` exactly on every
system — a kinematic maximum against a target that does not manoeuvre — so a
battery sited at it puts the border on the very edge of the envelope. Measured
on Afghanistan 2004: an SA-10 stands 39 NM inside its frontier against a 65 NM
claim, an SA-11 16 NM against 27. **Depth changes; the count does not** — that
comes off frontier length, not reach. **The west has no legacy
long-range rung** because vanilla DCS models no Nike Hercules, so a large
pre-1995 western country tops out at Hawk. **How many is the country's own size** (DM call
2026-09-09) — roughly one per 200 NM of war-facing frontier, capped at six.
A single site was 3.5 % of Pakistan's border on the Afghanistan map, measured
2026-09-09 over 2,291 NM of real frontier, so crossing anywhere else met
nothing. Only the war-facing stretch is manned: a frontier more than 250 NM from
every airbase in the campaign is one no sortie reaches, and the map's own clip
edge is not a frontier at all. Each site sits at exactly `min(reach, room)` from
the border so its envelope just covers it: a first cut that only capped depth
left Iran's Persian Gulf battery 175 NM inside, defending nothing. Deep
placement also means no site is on an airfield, so the escalation swap cannot
hand the neutral's airbase to a belligerent. They are visible before you cross,
which is the deterrent the scramble never managed (three flown attempts, all too
slow or too far). Cross and it hails you at once, and warns again at dwell;
neither call launches anything. A player who stays past the engage timer,
releases a weapon inside, or fires on a battery turns **the whole country**
hostile in place — every one of its sites `GROUP:Respawn`s onto the intruder's
opposing coalition, the only way a "neutral" can legally fire in DCS. Swapping
only the nearest would leave the rest of the border a neutral you could keep
crossing after being declared hostile. Both sides violating one country clones
the whole set for the second intruder rather than re-swapping. **AI intruders
earn nothing at all** — no radio call, no escalation — unless the `engageAi`
plugin option is ticked, which holds them to the same ladder. That is a testing
override and ships off: a player has to fly a whole profile to trip a border
once, where AI flights stray across on their own several times a mission, so it
is the only practical way to exercise the ladder without flying it.
A red-aligned nation gets no §98 battery:
its polygon joins §1's QRA accept zones, so the enemy's existing interceptors defend
it. A contested country — both sides holding airfields inside it — is enforced by
nobody and claimed by neither QRA. A neutral with no station point at all is drawn
toothless; `can_defend` is asked by the generator **and** by the web map, which used
to disagree with it on 14 of the shipped zones and draw Cyprus closed over a mission
you could fly through. **DCS models no Turkmenistan, Uzbekistan, Tajikistan, Armenia
or Azerbaijan**, and those five zones used to be dropped from the mission outright —
border undrawn, airspace unenforced. They now borrow a neighbour's units (DM call
2026-09-09): the group is still named for the real country, the radio call still says
it, and the plugin rewrites `CountryID` on escalation anyway, so the stand-in supplies
skins and nothing else. It falls through when its first choice is already a
belligerent, which Russia is on the Caucasus map.
The web map draws each border only to the land map's extent (2026-10-19): territory and
§111 sectors stop there, and Turkey drawn on to the 29.5E clip read as ground the sector
fill missed (Syria's land map ends at 31.3E). The mission's own border zones are not cut.
Colours: red / blue / contested grey / neutral mint, shading = enforcement. Design +
the session's decisions: `docs/dev/design/retlab-neutral-border-defense-notes.md`
(incl. the DECIDED-not-built automagic direction and the national-postures research
brief).

### The engine verdict, in one line

A true-neutral unit cannot be made to fire (hostility gates weapons release, not
tasking; no runtime coalition move exists), so the batteries stand as neutrals and are
respawned in place under the intruder's *opposing* country on escalation
(`GROUP:Respawn` with a rewritten `CountryID`/`CoalitionID`). No attack task is set
and none is wanted: a SAM acquires and engages whatever enters its envelope once it is
weapons-free. Only the second-intruder case clones
(`SPAWN:InitCountry`/`InitCoalition`), because a battery already swapped is an *ally*
of the other side.

### Shape

- **Python** — `game/theater/neutralborder.py` (`NeutralBorderZone`, the campaign yaml
  contract), parsed by `MizCampaignLoader.add_neutral_border_zones` onto
  `ConflictTheater.neutral_border_zones` (persisted; `__setstate__` defaults it for old
  saves). `NeutralBorderGenerator` builds, per zone, live SAM batteries under the
  neutral country, sized and sited from the border polygon (`neutralbordersams.py`
  holds the ladder; `NeutralBorderZone.interior_room` / `.sam_sites` do the geometry,
  and the generator hands the latter the campaign's control points and the union of
  every zone so it can tell war-facing frontier from map clip), and records them on
  `MissionData.neutral_border_zones`;
  `neutralborderluadata.py` serializes that to `dcsRetribution.neutralBorder`.
- **Lua** — `resources/plugins/neutralborder/neutralborder-config.lua`: border scan
  (bbox + ray-cast point-in-polygon on terrain XY), per-group dwell, the hail → warn
  → escalate ladder, the whole-country coalition swap, exit-grace stand-down, and the
  F10 border draw
  (default on — the §86 invisible-bubble lesson). **DCS will not fill a concave
  freeform** — it draws the outline and drops the fill, and a national border is
  about as concave as a shape gets, so every zone first flew as a bare line. The
  fill is MOOSE's `ZONE_POLYGON_BASE:ReFill` triangulation (its own
  single-freeform path is dead-coded behind `if false then`, which is the
  corroboration); the plugin keeps a one-freeform outline on top for the dash
  pattern, and no longer repeats vertex one. **The fill ring must not cross
  itself** — MOOSE ear-clips and stops at the first ring it cannot split. The
  plugin's every-Nth-vertex thinning crossed Saudi Arabia on the Persian Gulf
  map (18.7 % filled) and left 9 of 63 zones under 95 %. The emitter now ships
  a `fill` ring for any border over 96 vertices, thinned by shapely's
  topology-preserving simplify (`fill_ring`, `neutralborderluadata.py`); every
  shipped zone fills >= 98 %, pinned against a port of MOOSE's triangulation.
- **A campaign needs to author nothing.** Borders ship per terrain in
  `resources/borders/<terrain>.yaml` (Afghanistan, Syria, Caucasus, Iraq, Kola,
  Persian Gulf, Sinai, Falklands, Germany — Nevada and the Marianas are all-US and
  correctly have none), built by
  `tools/build_terrain_borders.py`; only the airframe
  resolves from `national_postures.yaml` against the campaign's date. A campaign
  that declares its own `neutral_border_defense:` block overrides the terrain
  file **completely** — never merged. Saves already in progress pick the borders
  up on load, so no re-roll is needed.
- **A country that ceased to exist is dated (2026-10-24).** The Germany file draws the
  GDR as its own zone with `until: "1990-10"` and `successor: Germany`
  (`--ceased GDR:Germany:1990-10`). `terrainborders.borders_on` is the one place that
  resolves it: `Game.on_load` re-reads the theater's terrain zones at the campaign's
  start date (`ConflictTheater.date_borders`), and the kneeboard's frontier lines take
  the same date. Fulda Gap 1985 sees the inner German border; Baltic Fury (2027) sees
  one Germany. The geometry is Natural Earth 10m admin-1: the GDR is the five eastern
  states plus Berlin, so West Berlin is drawn as GDR. Amager (Kastrup) is joined to
  Zealand and the floor is 300 km² so Usedom (Peenemunde) survives. Recipe:
  `retlab-national-postures-notes.md`, *Pre-1991 geometry*.
- **The file is keyed off the pydcs terrain name, aliased.** Sinai is `SinaiMap` in
  pydcs, so until 2026-10-13 `sinaimap.yaml` was looked up and every Sinai campaign had
  no borders, no neutral defense and a §111 fill clipped to the base box.
  `terrainborders._FILE_FOR_TERRAIN` maps it; `test_terrain_borders.py` pins each file.
- **The clip box has to reach the map's own edge.** Every border is the real
  country outline clipped to a hand-passed `--clip`, and until 2026-09-10 seven
  of the eight boxes stopped *inside* the terrain — 1,273,689 km² of modelled
  land with no border on it, 45.3 % of Sinai and 15.9 % of Afghanistan. Reported
  from the F10 map ("the fill doesn't go to the edge"). **Neither the landmap nor
  `terrain.bounds` is the map's extent** — both say the Afghanistan map stops at
  28.9 °N while Enduring Resolve's own carrier sits at 24.5 °N and the F10 map
  draws ground below it. A box derived from them clipped Pakistan, Iran and
  India at 27.5 °N, which is what the DM photographed on 2026-09-10. The floor
  is **what campaigns actually place**, plus margin: somebody authored a unit
  there, so it is flyable. Only edges proven short are moved — shrinking a box
  that was already adequate drops a country a rung, measured the same day when
  a uniform re-derivation took Turkey on Syria from 114 NM to 97 and cost it its
  Patriot.
  Every map is now under 2 % undrawn except Falklands at 7.9 %, which is Chilean
  fjord islands under a deliberate area floor. It also turned up that Kola was
  missing the Kola Peninsula, that China has 72,759 km² on the Afghanistan map,
  and that Persian Gulf was running with no landmap at all.
- **Borders are real data, never hand-traced** — `tools/neutral_border_geo.py`:
  public-domain country GeoJSON → clip to the map → optional corridor cut →
  shapely simplify to a vertex budget → `Point.from_latlng` → terrain XY yaml.
  Real-world-georeferenced maps only; fictional-overlay campaigns are out of
  scope (DM call, 2026-08-24). **Always `--clip`** — a country's real outline is
  mostly off any one DCS map, and un-clipped the vertex budget is spent on
  coastline nobody can fly to.
- **The whole map is simplified as one polygon coverage**, not country by
  country, so a frontier two countries share is simplified once and drawn once.
  Independently-simplified neighbours weaved: their lines coincided 35-65 % of
  the time (Russia/Norway on Kola at 7 %) with overlaps to 12.8 % of the smaller
  country. `set_precision` to a 100 m grid → union + `polygonize` into faces →
  `shapely.coverage_simplify`. Overlaps are now **0 on every map** and 7 of 8 are
  a valid coverage; Falklands carries a 12.5 m² degenerate touch in Tierra del
  Fuego, asserted as a known exception. The budget (`--max-vertices`, 96) binds
  the worst ring on the map and is a target, not a guarantee — a landlocked
  country whose every edge is shared has a floor (Armenia ~98). It came out
  better on every axis: Norway's shape error 14.7 % → 7 %, Afghanistan 454 → 255
  vertices and 446 → 247 F10 markup shapes.
- **A zone declares a field OR a point, and either one is only an anchor now.**
  Most maps carry the neutral's own airbase (Syria has Rayak); some carry none
  at all, since the DCS Afghanistan map has 26 airfields and **every one is
  inside Afghanistan**. Those zones declare `spawn: [x, y]` instead of
  `airfield:`; the yaml requires exactly one, and both or neither skips the
  zone. Since the patrol went, neither is a launch point — the batteries are
  placed from the polygon, and the anchor only breaks ties and names the origin
  in the tooltip. That is also why `--auto-spawn` putting each piece's station
  at its own `representative_point()` no longer matters: seven shipped stations
  sat within 10 NM of their own frontier and India's within 0.6, and nothing is
  sited off them any more.
- ~~**The origin names the flight; a 25 NM stand-off decides where it comes up.**~~
  **REMOVED 2026-08-29 with the scramble** — the patrol is airborne from mission
  start, so nothing comes up on demand and there is no stand-off to pick. Kept
  because the measurement is why the scramble was abandoned. Measured on the
  first flown test (2026-08-25, Tacview): Iran's origin is the
  middle of its clipped polygon, so the pair spawned 224 NM behind an F-15E,
  closed to 127 NM in twelve minutes and gave up — a MiG-29A has ~80 kt on a
  cruising Strike Eagle, and *every* launch on a country that size was that
  launch. Inside 25 NM the origin is used as it stands, so a small country still
  scrambles off its own runway; beyond it, the flight comes up 25 NM from the
  intruder on the line toward the origin. 25 NM is ~3 min at the shadow's speed,
  which is the engage dwell. A concave border that puts that line outside the
  country falls back to the origin.
- **Every country on the map is drawn, the map's own nation included.** The host
  was excluded until 2026-08-26, which deleted Russia from Kola, Iran from the
  Persian Gulf, Georgia from the Caucasus, Egypt from Sinai and Iraq from Iraq —
  and left the war itself as the one region with no line on it. What a country's
  airspace means is decided at run time from who holds the control points inside
  it, so the geometry leaves none out. Syria was separately missing from the Iraq
  map: never excluded, just never named in `--countries`.
- **`--corridor-lon` cuts a lane**, splitting one country into the two walls of
  a flight corridor. See the Afghanistan reference below.

- **The F10 map names each border**: a two-line label at the polygon's
  representative point (shapely, so it is inside a concave country; a centroid
  is not) reading the country and what its airspace does — `friendly` /
  `enemy-held` / `contested` / `transit permitted` / `CLOSED - surface-to-air
  batteries inside the border`. Drawn in the border's own hue, which keeps it distinct from §45's
  cyan support orbits and ties the label to its line. `drawBorders` switches
  both off together.

### The planning map

The DCS F10 map draws the border at mission start, but by then the route is
flown. The decision the feature asks for — cut the corner or go around — is made
in the planner, so the border is also a **"Neutral airspace" layer** on the web
map (`client/src/components/neutralborders/`), fed by the `/game` payload like
the minefields layer and empty (a no-op) unless the feature is on. It is drawn
in APP-6 neutral green with a long boundary dash, tooltipped with the altitude
floor and the alert field, and listed in the map legend. **Never fogged** — a
national border is public knowledge, and seeing the line is the point. The
DCS-side markup uses the same green; amber was the first choice and was moved
because amber is already SUSPECTED on the planner map.

### Rules fixed by DM call (2026-08-24)

- ~~Single-flight ladder~~ **superseded 2026-09-07** — the patrol is gone and its
  shadow risk with it. The recorded fallback it named, the in-place coalition-swap
  respawn, is what shipped.
- The **country** escalates, not the site: every battery it stands swaps together
  (DM call 2026-09-09, with the count rework).
- Everyone trips the border; only players are ever engaged. The planner stays blind —
  no navmesh hazard (do not reopen the §6 revert).
- In-mission only: nothing persists past the debrief. Spawns are free, untracked event
  content (the §61 precedent).
- Escalation is ROE + tasking only; emissions are not touched.

### Reference implementations

**Into the Hornet's Nest (Syria) — the derived-alignment case.** Lebanon was authored
as the neutral and the derivation rule corrected us: Beirut sits inside its border
hosting four red squadrons, so it resolves **red-aligned** — drawn in the enemy
family, covered by red's QRA accept zone, and its authored aircraft/SAM fields are
inert. The zone's yaml is kept as-is (the border is the context the DM wanted drawn);
the campaign's §98 *interception* showcase is Enduring Resolve, not this.

**Enduring Resolve (Afghanistan) — the corridor case.** The OEF "boulevard": the
carrier sits at 24.5°N 65.0°E in the Arabian Sea, and everything it launches has to
come north across Pakistan to reach Helmand and Kandahar. Pakistan's zone is cut into
two walls with a **~225 km lane** between them (`--corridor-lon 64.0 66.3`), and Iran
is the western no-go. Measured on the authored polygons: the direct carrier routes to
Kandahar, Bastion, Bost, Dwyer and Tarinkot all thread the lane clean, while the direct
line to **Farah** (62.2°E) crosses Pakistan — the dogleg up the corridor and then west
is clear. That is the constraint the campaign exists to create, and it is real
geometry, not a scripted scold.

Three zones, all point-spawned. ~~**Only Pakistan and Iran are modelled**, and the
northern border is left undefended rather than mislabelled; do not "fix" this by
substituting Kazakhstan or Russia.~~ **OVERRULED 2026-09-09 (DM call).** DCS still has
no Turkmenistan, Uzbekistan or Tajikistan, but leaving them out was not costing the
campaign a label — it was dropping the zone entirely, so four of the eight zones on the
map had no border drawn and no airspace enforced, against the standing rule that every
bordering nation appears. They now stand their batteries under a neighbour's flag
(`COUNTRY_STAND_INS`), chosen for kit. The group keeps the real country's name and so
does the radio call, and the plugin rewrites `CountryID` on escalation anyway.

Because AI intruders are never engaged, a lane this tight costs the campaign nothing:
an AI flight that clips a wall is not fired on, and only the player is.

### Files & tests

- `game/theater/neutralborder.py` · `game/campaignloader/mizcampaignloader.py` ·
  `game/missiongenerator/neutralbordergenerator.py` · `neutralborderluadata.py` ·
  `game/settings/` (`neutral_border_defense`) ·
  `resources/plugins/neutralborder/` · `tools/neutral_border_geo.py`.
- `tests/lua/test_neutralborder_runtime.py` — 30 harness tests on real Lua 5.1: the
  hail on entry and the second call at dwell, dwell escalation, weapon-release
  escalation, AI-never-engaged, every battery in a country swapping on one escalation,
  the second set when both sides violate, a zone with no battery never claiming to
  defend, the exit stand-down, the triangulated F10 fill and the map labels.
  `tests/test_neutralborder.py` — alignment derivation, airbase-derived consent,
  overrides, malformed yaml skipped rather than raised.
  `game/missiongenerator/tests/test_neutralborder_luadata.py` — the emitter contract,
  the SAM ladder, and the placement invariants (reach ring, count from frontier
  length, the cap, war-facing only). `tests/test_terrain_borders.py` — every shipped
  map parses, no neighbour overlap, each map a valid coverage. 165 in total across six
  files.

**In-game passes owed: B120 and B121.** Nobody has flown the SAM design at all — B120
was closed against the fighter patrol, which no longer exists. B121 is the AI intruder.
## §99 — Sandy rescue escort

The armed half of a rescue package: an A-10 or an Apache working the ground around a
downed pilot while the helicopter comes in. Added 2026-09-11.

The role existed as §15 and went with the whole fork rescue stack on 2026-08-07. This is
not that feature back. §15 was a `FlightType.SCAR` with its own plugin, its own scenario
runtime and its own auto-planner tasks. This is a flight plan, a task on six aircraft
yamls, and a callsign.

### Why it needed a flight type at all

`CasFlightPlan.Builder.layout()` raises `InvalidObjectiveLocation` unless the package
target is a `FrontLine`. A rescue package's target is a `DownedPilot`. So a CAS-tasked
flight fragged at a survivor could not be planned — the player got "Could not create
flight" after picking their survivor, airframe and squadron, which is the same failure the
King had before 2026-08-26.

The alternative considered was dispatching on the target instead: a CAS flight whose
package target is a `DownedPilot` routes to a survivor plan, the way
`FlightPlanBuilderTypes.for_flight` already routes fixed-wing CSAR to the King. Rejected
because the airframe restriction is the point. Capability declared in the yaml `tasks:`
block is a hard gate (the pattern §77's Escort Jammer used until its removal); a `preferred_type` on a CAS
proposal is a preference, and any CAS jet in the wing would have been eligible.

### What runs

- **`FlightType.SANDY = "Sandy"`** (`game/ato/flighttype.py`). Air-to-ground; SIDC
  `ATTACK_STRIKE`, not `COMBAT_SEARCH_AND_RESCUE` — the map already draws the rescue helo
  as CSAR, and the Sandy is the thing on it that shoots.
- **`SandyFlightPlan`** (`game/ato/flightplans/sandy.py`) subclasses `CasFlightPlan` and
  reuses `CasLayout`. Only `Builder.layout()` is replaced, so the FLOT requirement never
  runs and everything keyed on the CAS plan keeps working — in particular
  `CasIngressBuilder`, whose `isinstance(flight_plan, CasFlightPlan)` is what emits the
  `EngageTargetsInZone` task. The builder subclasses `cas.Builder` for the same reason:
  `Type[sandy.Builder]` has to satisfy `CasFlightPlan.builder_type()`'s return type.
- **Geometry.** Ingress 5 nm out on the departure side, then a 3 nm half-length track laid
  **across** that run-in and centred on the survivor, so the circuit crosses the pickup
  twice instead of driving out and back. Engagement zone 5 nm, centred on the survivor.
  Constants are hardcoded (`TRACK_HALF_LENGTH`, `ENGAGEMENT_RANGE`, `INGRESS_DISTANCE`) —
  the flight is hand-fragged, so a player who wants a different track moves the waypoints.
  This follows the King; it is not an oversight.
- **Altitude** is the airframe's combat altitude through `builder.cas()`, which already
  carries the cloud-base and Vietnam low-level-attack handling. Helicopters navigate AGL.
- **AI behaviour** is `configure_cas` — main task CAS, ROE Open Fire, RTB winchester on
  unguided. `game/missiongenerator/aircraft/aircraftbehavior.py`.
- **Loadout** falls back to the airframe's CAS fit. A `Retribution Sandy` payload is
  preferred if one is ever authored; none is.
- **Callsign** defaults to "Sandy", numbered after any other Sandy already fragged, and is
  offered in the per-flight picker. Like "Toxic" it is not a stock DCS callsign, so
  `FlightGroupSpawner` registers it into the country pool around the spawn.

### Capability — six airframes, all secondary

`Sandy: <the airframe's own CAS weight>` in `tasks:`, and `Sandy` under `secondary_tasks:`,
on A-10A, A-10C, A-10C_2, AH-64A, AH-64D and AH-64D_BLK_II. Nothing else in the tree
declares it.

`secondary_tasks` is what keeps the checkbox unticked by default. It is belt and braces:
**nothing in the HTN proposes a `SANDY` flight**, so the auto-planner cannot frag one
whatever the squadron's auto-assignable set says. That is the gate, and it is why no
`requires_helicopter`-style property was added.

The role is reachable because `DownedPilot.mission_types` yields it — that is the only
thing that puts it in the player's mission-type dropdown at a survivor.

### Tests

`tests/ato/flightplans/test_sandy.py` (10): the dispatch both ways, the non-survivor
target, the track centred on the survivor, both legs inside the engagement zone, the
run-in not overflying the pickup, the legs crossing it, the tasking offered at a survivor,
and the six airframes capable-but-secondary with a Viper control.

Also touched: `tests/test_role_callsigns.py` (the ROLE_CALLSIGNS set) and
`tests/test_theme_tokens.py` (every FlightType needs a task chip — `SANDY` is in `_A2G`).

### Needs an in-game pass — B117

Nothing headless can say whether a two-ship holding a 6 nm track at CAS altitude actually
engages what is shooting at the pickup, or whether an Apache on the same plan behaves.

### Deferred

- **No auto-planning, by decision.** A Sandy is a coordination role and an AI one would
  orbit while the helo does the work.
- **No dedicated loadout.** The CAS fit is what an A-10 would carry anyway; an Apache's
  is less obviously right.
- **No link to the rescue flight.** The Sandy and the helicopter are planned independently
  and share only the target. There is no "Sandy cleared me in" handshake, on the map or in
  the mission.

---

## §100 — King on-scene commander

The player-flown C-130J King finds the survivor and builds a threat picture for the
rescue. Added 2026-09-12. Runtime only — a second script in the `opscsar` plugin plus one
new node in the Lua data.

### Files

- `resources/plugins/opscsar/KingOnScene.lua` — the whole runtime. Loads after
  `OpsCSAR.lua` (second `scriptsWorkOrders` entry), touches nothing of it.
- `game/missiongenerator/luagenerator.py` `generate_csar_data` — emits
  `dcsRetribution.CSAR.rescueFlights`: every CSAR and SANDY flight's group name, role
  (`king` = fixed-wing CSAR, `jolly` = helicopter CSAR, `sandy`), side, whether a human is in
  it, and the survivor id its package was fragged for.
- `tests/lua/dcs_stubs.lua` gained `trigger.action.markToGroup` and `land.isVisible`
  (a switch, `Harness.losBlocked` — the harness models no terrain).

### What it does

Registered for a `king` entry with `player == "true"` whose group has a human in it, polled
every 10 s. F10 → **KING | On-Scene Commander**:

- **Survivor status** — name, aircraft, beacon channel, fix quality, bearing and range to the fix.
- **Take DF cut on the beacon** — inside 80 nm, a bearing from the King to the survivor with
  up to ±3° of error (`DF_BEARING_ERROR_DEG`). Two cuts ≥15° apart intersect into a fix; every
  qualifying pair is intersected and averaged. The error shown is the bearing error projected
  at the last cut's range, opened up by poor separation, tightened by `√pairs`, floored at
  150 m. Inside 15 nm with line of sight (`POD_RANGE_M`, `land.isVisible`) the fix snaps to
  the true position — the pod has the survivor.
- **Threat sweep around the fix** — needs a fix and the King within 40 nm of it. Scans enemy
  ground groups within 8 nm **of the fix, not of the true survivor** — the pod looks where the
  King thinks the pilot is, so a bad fix gives a bad picture. Closest five, each as a class
  (`SAM` / `MANPADS` / `AAA` / `ARMOUR` / `TROOPS` / `VEHICLES` from `Unit:hasAttribute`)
  with bearing and range **from the fix** and a mark jittered up to 460 m.
- **Pass picture to …** — the player-crewed `sandy` and `jolly` groups on the King's side,
  rebuilt every tick, plus **All rescue flights**. Sends the brief (`outTextForGroup`) and the
  survivor + threat marks (`markToGroup`) to that group, clearing what it sent before.
- **Clear my marks.**

Mark ids start at `MARK_ID_BASE = 7100000` to stay clear of the c130j ISR marks and MOOSE's.
Randomness is a per-King LCG seeded from mission time and group id, because `math.random`
is never seeded in the DCS mission environment.

### Constraints — do not undo

- **Cues only.** No laser, no designation, no `setTask`/`pushTask` on any flight. The
  harness test asserts `controllerTasks` stays empty after a pass. The §15 divert lesson.
- **Class and rough position, never a unit type or an exact point.** The fog rule: nothing
  here names a site's composition. `THREAT_JITTER_M` is the floor on how rough.
- **The fix comes from DF, not from knowing where the pilot is.** The true position is read
  only to noise a bearing from it and to snap inside pod range with LOS.
- **Players only.** An AI King gets no menu; an AI Sandy or helicopter is never listed.

### What the King is NOT given — one or the other (DM call 2026-09-12)

A CSAR-tasked C-130J flies this menu and **not** the c130j EW/ISR menu; a JAMMING C-130J
flies EW/ISR and not this. `_ew_excluded_c130j_groups` now lists `FlightType.CSAR` with
TRANSPORT and AIR_ASSAULT, which is what the Lua comment ("Combat SAR King flies clean")
always claimed and the Python never did. Found and fixed the same day.

### Tests

`tests/lua/test_kingonscene_runtime.py` (13): no node / AI King are no-ops; menu and welcome
for a player King; one cut is a bearing; two cuts ≥15° apart fix within 4 km; close cuts do
not; pod snap inside 15 nm with LOS, and not without LOS; beacon range gate; sweep needs a
fix; class + rough + closest-first with friendlies and far groups excluded; the five cap;
pass goes to player rescue flights only, marks land on their map, no controller task.
`tests/test_csar.py::test_generate_csar_data_lists_the_rescue_flights_for_the_king` pins
the emit.

### Needs an in-game pass — B119

Whether `land.isVisible` from a King at altitude reads as expected, whether a real DCS
survivor unit keeps reporting a position for `Unit.getByName`, and whether `markToGroup` marks
show for every client in a multi-crew group.

### Deferred

- **No authentication.** A real King authenticates the survivor by radio first. Nothing here
  models it; the survivor is who the campaign says.
- **No ADF tie-in.** The cockpit ADF (G33) and this DF are independent models of the same
  beacon. They agree on the channel and nothing else.
- **No AI vectoring**, by decision (2026-09-12).
## §101 — Dynamic spawn templates

A pilot who takes a DCS dynamic slot instead of a fragged one gets a blank jet: stock
loadout, no route, no radio presets, no properties. Added 2026-09-15. At each base, one
player flight of each aircraft type is marked as DCS's **Dyn.SPAWN Template** and the
base's warehouse entry is linked to it, so the dynamic jet is built from that flight.
Design note: [`retlab-dynamic-spawn-templates-notes.md`](design/retlab-dynamic-spawn-templates-notes.md).

**Links are cleared before they are written (2026-09-15, test 33).** The pydcs `Airport`
objects belong to the campaign's terrain and outlive one generation, so a link written for
a flight the player then deleted stayed on the field: Akrotiri's F-16C entry pointed at a
red H-6J group three generations later. `_clear_stale_links` drops every `linkDynTempl`
entry on every airport first, feature on or off. Ship and heliport warehouses are rebuilt
each generation and need nothing.

### Files

- `game/missiongenerator/dynamicspawntemplates.py` — `DynamicSpawnTemplateGenerator`.
  Called at the end of `MissionGenerator.generate_warehouses`, after the air units exist
  and the ship/heliport warehouses are emitted (it needs both).
- `game/settings/` — `dynamic_slots_templates` (default on, enabled under
  `dynamic_slots`).
- `requirements.txt` — the pydcs pin moved to `BradySox/pydcs` `dyn-spawn-template`
  (`beb37634`), one commit on the DTC pin: `FlyingGroup.dyn_spawn_template`, emitted as
  `dynSpawnTemplate = true` only when set. **A pin bump: reinstall the venv.**
- `tests/missiongenerator/test_dynamic_spawn_templates.py`.

### What it does

- **Donor:** one **client** flight per (departure control point, DCS type id), over both
  coalitions' ATOs. A ground start beats an in-flight start; otherwise ATO order wins.
- **Mark:** the donor's own group gets `dynSpawnTemplate = true`. No clone — a template
  group stays in the slot list (DM, in the editor, 2026-09-15), so the fragged slot still
  flies as itself.
- **Link:** an airfield's goes on the pydcs `Airport.aircrafts` table
  (`planes`/`helicopters` by type id); a carrier's or FARP's goes on every ship/heliport
  warehouse of the control point. Entry shape is the editor's default
  (`initialAmount = 100`, `unlimited = false`) plus `linkDynTempl`; no `wsType`.
- Types with no client flight at a base stay blank, as before. Off with `dynamic_slots`.

### Constraints — do not undo

- **AI flights are never templates.** The editor clears the flag on a non-player group
  (`me_aircraft.lua:1251`); an AI donor is an untested shape.
- **Emit the group flag only when set.** Every other miz must serialize byte-identical
  across the pin bump.

### Tests

`tests/missiongenerator/test_dynamic_spawn_templates.py` — both keys reach the miz text
under the airport's id, the donor choice (ground start over air start, first in ATO
order), both gates, the helicopter category, the carrier warehouse path, and a flight
whose group is missing is skipped.

### Needs an in-game pass — B125

What the install's Lua could answer is in the design note §4. Two things only a fly
answers: whether the route and radio presets carry (the slot-select dialog reads loadout,
properties and livery off the template and hands the rest to native code), and whether the
warehouse entry needs `wsType` (the editor's own loader fills it from the database when it
is absent; the sim's loader is native).

### Deferred

- A synthesized donor (a BARCAP over the field) for types with no client flight at the
  base — needs a planned flight, and it would have to be a client slot too.
- The dynamic jet is still invisible to the campaign (no loss, no §58 card, no §74
  cartridge). Separate and larger.

## §102 — My aircraft, saved points and the DTC options

A window for the seat the player is flying this turn, the points and drawings they save for
it, and a per-airframe DTC tab. Added 2026-09-22; the window and the saved points are from
juanjux/dcs-escalation #343–#369 and #360–#363 (LGPL-3.0). Design note:
[`retlab-my-aircraft-notes.md`](design/retlab-my-aircraft-notes.md).

### Files

- `qt_ui/windows/playable/` — the window (`dialog.py`, `rows.py`, `model.py`, `style.py`).
  Opened from `QTopPanel` ("My aircraft").
- `qt_ui/windows/mission/flight/QFlightDtcTab.py` — the DTC tab, per airframe, driven by
  `game/missiongenerator/dtc/sections.py`.
- `game/ato/savedpoints.py` — `SavedPoint` (kinds, orbit heading/length),
  `SavedDrawing`, the capacity tables. Both live on the `Squadron`.
- `game/ato/dtcoptions.py` — new fields `saved_points`, `drawings`,
  `threat_ring_radius_nm`, `auto_load`, `skipped_waypoints`.
- `game/missiongenerator/dtc/savedpoints.py` — cockpit numbering for points and route
  rows, the waypoint skip, the player shapes. Shared by all four builders and the kneeboard.
- `game/missiongenerator/dtc/common.py:threat_sites_for` — the near-the-route SAM filter.
- `game/missiongenerator/a10cdu.py` — the A-10's saved points as CDU state (the route
  is left to DCS), and 3D VNAV on a player A-10's route.
- `game/coordinates.py`, `game/elevation.py`, `game/server/coordinates/`,
  `game/server/savedpoints/` — formats, the elevation lookup, the map's API.
- `client/src/components/coordinatepicker/` — the map point picker, Save with kinds, the draw
  panel (`DrawPanel.tsx`), the map layer (`SavedPointsLayer.tsx`) and its editable pins
  (`SavedPointPin.tsx`).
- `game/server/savedpoints/notifications.py` — one call that tells the map and the open
  window a point changed.

### What it does

- Points: waypoint, IP, target, hold (one pool) and orbit (its own). Each jet gets them
  where its schema has a place — the note's §2 table.
- Drawings: lines and areas on each jet's free line slots — the note's §3 table.
- DTC tab: only the sections the jet carries; load at spawn or by hand; waypoint types to
  leave out; SAM sites only near the route.
- Window: room counted in the jet, after the planned route; points carry the jet's
  numbers (`point_numbers`, the same function the kneeboard uses).
- Kneeboard: a "saved points" page with the cockpit's numbers; the route table prints
  `-` on a skipped row.
- Map pins (2026-10-10, juanjux #519): each saved point is a pin in its kind's colour.
  Click to rename or delete, drag to move; an orbit's pin moves the racetrack. The map
  and the window refresh each other. Points are edited by a persistent id. Design note
  §6a.

### Constraints — do not undo

- Points and drawings stay on the squadron (his #369).
- One numbering function for the kneeboard and the cartridges.
- Hornet/Viper/Apache points need the Flight plan section (those cartridges replace the
  whole navigation set).
- Skips are waypoint-type names, never indices.
- The A-10's CDU file holds saved points only, never the route: written there, the
  aircraft swapped planned altitudes for terrain heights and every number moved up
  one (2026-10-10, juanjux #510/#511, flown there). Design note §8.
- The picker leaves a click on an interactive shape to that shape, except a `map-area`
  one (hover-only: §98's country polygons). Without the exception, neutral border
  defense's borders cover every country and the picker answered only at sea (fixed
  2026-09-27; the first fix put the class in `pathOptions`, which react-leaflet applies
  through `setStyle` and Leaflet ignores there, so it never reached the DOM. Cased shapes
  now pass `className` as a creation prop: fixed again 2026-09-28).
- The map edits a point by its id, never its index, and every edit calls
  `publish_points_changed`. A new place that changes points must call it too, or the
  map and the window drift until the 5 s poll.

### §74 schema fixes (2026-09-22)

Four defects the schema research found in the §74 builders, fixed on the DM's call; the
design note §5a has each DCS file:line source:

- Apache: TSD lines kept to 2-4 vertices (the editor deletes others); tanker boxes are
  4-corner areas.
- Apache: route `eta` per leg, not a running total.
- Hornet: one `TGT` per route sequence.
- Tomcat: every plan held to 3 lines (route as line) or 4, and 50 points in all.

### Tests

The §102 block of `tests/missiongenerator/test_dtc.py`, `tests/test_dtc_tab.py`,
`tests/test_saved_points.py`, `tests/test_a10cdu.py`, `tests/test_coordinates.py`,
`tests/test_coordinate_parsing.py`, `tests/test_elevation.py`,
`tests/test_playable_aircraft.py`, `tests/test_playable_window.py`,
`tests/server/test_saved_point_pins.py`, `tests/qt_ui/test_saved_point_sync.py`, and the client's
`coordinatepicker` suites (`kinds.test.tsx` for kinds, orbits and drawing;
`SavedPointPins.test.tsx` for the pins).

### Needs an in-game pass — B135, B136, B209

B135: the cockpit numbering and sequence 2. B136: hand-load, skipped waypoints, and
orbits and drawings on each jet's page. B209: the A-10's route altitudes and saved
point numbers.

### Deferred

- A Tomcat generation run; times on/off; a coordinate-format
  setting; zoom on Show on map.

---

## §103 — HQ priority targets

What losing each enemy target costs the enemy, shown on the target panel and optionally used
to weight blue's auto-planner. The objective half of juanjux's High Command (his
`game/highcommand/`, #421–#429), rebuilt from our numbers; no prize, no ticket. Design note:
`docs/dev/design/retlab-hq-priority-targets-notes.md`. Built 2026-09-23, not flown.

### The measure

Each target is measured in its own kind's unit, from numbers the game already keeps. There is
no exchange rate between kinds — rule 4, no invented costs.

| Target | Measure | Source |
|---|---|---|
| Income building (`REWARDS` categories) | enemy income a turn | `REWARDS` × live buildings × `enemy_income_multiplier` |
| Ammo depot | front-line vehicles the enemy could no longer field | `deployable_front_line_units_with` with and without it |
| Motorpool | reserve vehicles | `reserve_armor_for` |
| Command post | offensive package ceiling before and after | §52's ceiling; unmeasured while §52 is off |
| Power, comms, bunkers | none | neutral |
| Everything else | equipment price | `TheaterGroundObject.value` |

### Ranking and the weight

- Ranked within its §93 family only (`family_of`). Unmeasured targets are neutral and not counted.
- A family with fewer than 3 measured targets, or all equal, is not ranked.
- Top third: sort key × 0.75. Bottom third: × 1.25. Ties share a tier. §93 uses 0.5 / 2.0, so the
  player's own emphasis outranks HQ's.
- Applied beside §93 in `ObjectiveFinder._targets_by_range(weighted=True)` and `strike_targets`:
  strike targets, threatening ships, motorpools. DEAD and BAI ordering is untouched.
- Blue only, `hq_priority_targets` on (default off). Red's planner never reads it.
- Only red targets **not** hidden on blue's map (`fogofwar.hidden_from`) are ranked; a hidden site
  is neither ranked nor weighted.

### The panel line

`QGroundObjectMenu.target_intel_rows()` adds **Why it matters** for blue looking at a red target,
whatever the setting: the measure, and `#N of M <family> targets` when ranked. An unengaged site
reads "Unknown (not engaged)" — its price would give away its composition (§3).

### Tests

`tests/retlab/test_hq_priorities.py` (16).

### Deferred

- Difficulty (route cost through threat rings, fighters, size) — the note's step 3.
- A top-few "HQ priorities" list.
- Measures for power, comms and bunkers (what an IADS node's loss switches off).

## §104 — Runway queue at busy fields

The ground-ops allowance at an airfield grows with the departures ahead of a flight, so a
crowded field's later flights spawn early enough to make their takeoff. Design, calibration
and measurements: `docs/dev/design/retlab-startup-times-notes.md`, "Runway queue". Built
2026-09-23, not flown.

**DM call 2026-09-23: always on, long-standing upstream issue at busy fields.** No setting.

- `game/ato/runwayqueue.py`: `runway_queue_wait(flight)` walks the coalition's ATO for
  parking-start fixed-wing flights leaving the same field, sorted by planned takeoff, each
  holding the runway `count × 45 s`.
- `FlightPlan.estimate_ground_ops` = 8 min + the wait. It feeds `startup_time`,
  `minimum_duration_from_start_to_tot` (TOT estimation) and the sim's `Taxi` state.
- Not queued: carriers, FOBs, off-map, runway and air starts, helicopters, unscheduled
  packages (TOT at the `datetime.min` sentinel).
- Players queue like AI; the wait adds to their startup allowance, never replaces it.
- 45 s per jet: fitted on 494 flown AI groups; groups more than 2 min late fell from 25 % to
  10 %.
- `queue_aware_ground_ops`, the gate on the first draft of PR #1078, is dropped in
  `migration.py`.

### Early mission start

- `game/sim/missionstart.py`: `mission_start_time(game)` is the turn clock minus the
  shortfall of the earliest ground-start `startup_time()` in both ATOs, at most
  `EARLY_START_CAP` (30 min).
- `MissionSimulation.begin_simulation` starts there; flight states initialise against it, so
  nobody inside the window is clamped. Past the cap, flights clamp as before.
- `conditions.start_time`, TOTs and the §47 clock and weather do not move. Only the
  simulated and generated mission start does.
- Except ASAP support: an ASAP Refueling, AEW&C or BARCAP package re-runs ASAP from the
  early start (`retime_asap_support`, every generation), so the tanker is up before a flight
  that started early to reach it. Those packages never set the start themselves.
- A station's relief BARCAP waves (not ASAP, same target as an ASAP BARCAP) move by as
  much as the first wave did, never earlier than they can fly from the mission start, so
  the scheduler's handover holds. They do not set the start either (2026-10-11).
- `settle_mission_start` takes the start again after the retime, up to four passes, and
  keeps the earlier value inside the cap: retimed support reorders a runway queue and
  moved another flight's startup up to 2.3 min ahead of the start (2026-10-11).
- The Take Off past-start warning compares against the earlier start.
- DTC ETAs count from `FlightData.mission_start`, since the start can cross Zulu midnight.
- Not §89's pre-roll: nothing is simulated or placed mid-sortie.

### Gotchas

- `takeoff_time` must never read `estimate_ground_ops`; the walk relies on that to avoid
  recursion.
- The wait depends on the package TOT, so one ASAP estimate depends on the TOT it was
  taken at. `TotEstimator.earliest_tot` climbs from the no-queue floor until the TOT covers
  its own queue, then restores the TOT it borrowed. A single estimate flipped between two
  times, and the package dialog re-saved each redraw: `RecursionError` from `save_tot`
  (fixed 2026-09-27; the dialog now blocks the spinner's signals while it redraws).
- A package with an unscheduled TOT is skipped, not read: its takeoff overflows.
- `sim.time` before `begin_simulation` is still the turn clock; planning reads it as "now".
  Only `begin_simulation` moves it.

### Tests

`tests/test_runway_queue.py` (18), `tests/test_early_mission_start.py` (7),
`tests/test_package_dialog_tot.py` (2), and the DTC midnight case in
`tests/missiongenerator/test_dtc.py`.

### Deferred

- Per-field runway rates; landing traffic.

In-game row **B145**. Upstreaming queue item 42.

## §105 — RetLab Iran Air Defense Pack (3rd Khordad, Bavar-373)

Retribution support for a RetLab-authored DCS mod carrying Iran's two SAM systems. The repo
side is built; the mod is built on the DM's machine. Design, the unit contract and the research:
`docs/dev/design/retlab-iran-air-defense-pack-notes.md`. The build instructions for the mod:
`docs/dev/design/retlab-iran-air-defense-pack-HANDOFF.md`. Built 2026-09-25; flown in tests
41-46 (row B148).

- `pydcs_extensions/iranairdefensepack/`: fifteen `IRAD_` vehicle types, the ten
  air-defense units and five surface-to-surface launchers. Their ids are the contract with the
  mod's `Database` lua.
- Gated by the `iranairdefensepack` ModSettings toggle (the Mods page, Air defense group).
  `Faction.apply_mod_settings` strips all fifteen and the two presets when it is off.
- Presets `3rd Khordad` (MERAD) and `Bavar-373` (LORAD). One Bavar-373 launcher, the TEL firing the
  Sayyad-4B, since 2026-09-30 (DM call): a Sayyad-4 site locked a Hornet at 22 NM and never fired,
  and the 4B fired in tests 42-46. The Sayyad-4, the Sayyad-4B TEL and the Bavar-373-II TELAR
  were removed; an old save loads them as the TEL (`persistency._handle_misc`).
- A Bavar-373 site spawns on red alert (`ALARM_RED_AT_SPAWN`, 2026-09-30): left on AUTO under
  Skynet its TELs never raised (tests 48-49). Skynet still owns its radar emissions.
- Factions by era (2026-09-29): `Iran 2015` fields 3rd Khordad; `[CH] Iran 2020` adds
  `Bavar-373`; `[CH] Iran 2025` adds the 2023 missiles. Faction files are not date-gated, so the era lives in which faction a campaign picks.
- `3rd Khordad Battery`: `6_Launcher_Circle.miz`, 2 TELARs in the Track Radar slot (the §60
  pair, and never zero), 4 radar-less TELs.
- `Bavar-373 Battery`: `S-300_Site.miz` on the HQ-22 pattern, six TELs and one STR, with the §85
  support section.
- Skynet: `samTypesDB['3rd Khordad']` and `samTypesDB['Bavar-373']`; the Bavar-373 CP is
  `required`, as the S-300's is. `['Matla ul-Fajr']` is an `ewr` entry.
- `IRAD_MatlaUlFajr_EWR` and `IRAD_Rasool_Comms` join the Iran factions' air-defense units. The
  Rasool is whitelisted in the C2 van slot of the comms, command-center and EWR layouts, so an
  Iranian Skynet connection node or command center fields one.
- Missile sites: the pack's Sejjil-2, Emad, Kheibar, Fattah-2 and Shahed 238 launchers
  (`IRAD_*_TEL`). `[CH] Iran 2025` fields all five; `[CH] Iran 2020` the Sejjil-2 and Emad;
  `Iran 2015` the Sejjil-2. The Fattah-2, Kheibar and Shahed 238 date from 2023. They replaced
  the third-party launchers and their `iranmissilemods` toggle on 2026-09-29 (DM call
  2026-09-27: support them, build our own, drop them); a saved setting of that name is
  ignored. Scenic Route Merged and both Noisy Crickets preseed the pack. Row B166.
  The four ballistic missiles fly ED's 9M723 Iskander exactly, 75-400 km (DM call
  2026-09-30); a missile site fires only at a field 40-216 NM away.
  Deployment research for laying Iran out in a campaign:
  `docs/dev/design/retlab-iran-iads-deployment-notes.md`.

### Gotchas

- Ranges are conservative best estimates, well under Iranian claims. If the mod's missiles
  do something else, update the pydcs values to match the mod.
- A launcher model's facing is unknown until flown; `reversed_heading` may be needed.

### Tests

`tests/retlab/test_iran_air_defense_pack.py` and `test_iran_pack_missiles.py`, plus both layouts in
`tests/armedforces/test_sam_radar_redundancy.py` and `test_sam_support_vehicles.py`.

### Deferred

- 15th Khordad.
- The DCS mod and its 3D models are a separate pack, like HDS and CurrentHill, in the
  private repo `BradySox/RetLab-Iran-Air-Defense` (DM call 2026-09-25; not public yet). All
  eleven models are built there by script, baked in Blender 5.1 and exported, each with
  its own wreck; the Taer-2B and Sayyad-4B are defined at the §3 numbers.
  This repo carries only the Retribution side.

In-game row **B148**.

## §106 — Package route and Insert NAV point

A package's way in (join to IP) and way out (target to split) are flown by every formation
flight together, so a NAV point on them belongs to the package. They are edited on the
map, from any flight of the package: drag a point, double-click the route to add one,
right-click a point to delete it. The Package route window is the overview; Insert NAV
point in a flight's Waypoints tab finds a leg beside any waypoint. Built 2026-09-27, map
editing 2026-09-28, not flown. Design note:
[`retlab-package-route-notes.md`](design/retlab-package-route-notes.md).

### Files

- `game/ato/flightplans/navinsert.py` — `nav_insert_next_to(layout, anchor)`: tries each of
  the layout's `nav_sequences()` after the anchor, then before it, and keeps a slot only if
  the point lands next to the anchor in the route.
- `game/ato/flightplans/flightplan.py` — `Layout.nav_sequences()`; one generic
  `Layout.move_waypoint` over those lists (the standard, custom and airlift overrides are
  gone, and with them `add_waypoint`).
- `game/ato/packageroute.py` — who flies the route, the route rows, insert / delete / move
  / set position / reset for every flight.
- `game/ato/packagewaypoints.py` — `ingress_nav` / `egress_nav`, `None` until the player
  edits a leg.
- `game/ato/flightplans/formationattack.py` — `package_route_points`: the package's points
  when set, else the planner's SAM detour. `_sam_detours` builds every flight's legs from it.
- `game/ato/routeedit.py` — the map's edits: `insert_nav_at` (the drawn leg nearest the
  click), `delete_nav`, `is_deletable`; a refusal is `RouteEditRefused` with the reason.
- `game/server/waypoints/routes.py` — `POST /waypoints/{flight}/insert`,
  `DELETE /waypoints/{flight}/{idx}` (409 with the reason when refused), and
  `update_package_waypoints`: a drag of a package point on any flight of the route moves
  it for all (`packageroute.moves_package`).
- `game/server/waypoints/models.py` — each waypoint tells the map `deletable` and
  `package_point`.
- `client/src/components/flightplan/FlightPlan.tsx` — double-click on the selected route;
  `waypointmarker/WaypointMarker.tsx` — the right-click menu; `waypointmarker/notice.ts` —
  a refusal said on the map.
- `qt_ui/windows/mission/QPackageRouteDialog.py` — the window; **Package route** button on
  the package dialog.
- `qt_ui/windows/mission/flight/waypoints/QFlightWaypointTab.py` — Insert NAV point and
  Delete ask Whole package / This flight only on a shared leg.

### Constraints — do not undo

- Lookups are by identity: `FlightWaypoint` compares by value.
- A NAV slot counts only if the point lands next to the anchor. The type-based table this
  replaced put the point after the hold (takeoff) and after the tanker (split), halfway
  back: a zigzag.
- The package's points are the source once set; the planner reads them for a flight added
  or recreated later.

### Gotchas

- A flight carrying its own point on a shared leg is rebuilt from the package's points on
  the next package edit; its own point is dropped.
- The strike line-up is per flight and not on the package route.
- Helicopters and air assault fly no package route; a package whose primary does not has
  none, and the button is disabled. An escort in such a package edits only itself.
- Only the selected route takes a double-click, so the others still zoom the map; while
  the ruler measures, a double-click is the ruler's.

### Tests

`tests/ato/flightplans/test_nav_insert.py` (18), `tests/ato/test_package_route.py` (28),
`tests/ato/test_route_edit.py` (9), `tests/test_package_route_dialog.py` (6), and the
client's `FlightPlansLayer.test.tsx` and `waypointmarker/notice.test.ts`.

### Needs an in-game pass — B150, B151

B150: Insert NAV point beside the join, the line-up, the last target and the split, and
the refusals. B151: the map (drag from any flight, double-click to add, right-click to
delete), the window, the flight tab's question, and a flown package on an edited route.

### Deferred

- Typed coordinates (the DM does not want them); keeping a flight's own point across a
  package edit; reordering on the map.

## §107 — Briefing screen picture

The picture on the DCS briefing screen when a generated mission loads. It used to be
upstream's startup splash (`resources/ui/splash_screen.png`). Since 2026-10-19 it is a card
drawn for each mission: campaign name, turn, date and start time, surface wind, clouds,
temperature, QNH, and the player flights (callsign, aircraft, task, target, departure).
A player can replace it by dropping `briefing.png` or `briefing.jpg` into
`Saved Games\DCS\Retribution`. Built 2026-09-29 as a fixed picture, not flown.

The briefing text changed with it (2026-10-19): each flight line leads with its callsign,
names the aircraft by its display name, labels the package target `target:` (it read as a
departure field), and ally flights list in departure order under their base. The text is no
longer HTML-escaped; `AEW&C` printed as `AEW&amp;C`.

### Files

- `game/retlab/briefing_image.py` — `briefing_image_path()`: the first of `briefing.png`,
  `briefing.jpg`, `briefing.jpeg` in the Retribution user folder, else
  `resources/ui/retlab_briefing.png`. `custom_briefing_image()` is the drop-in lookup alone.
- `game/retlab/briefing_card.py` — `build_briefing_card()` reads the game;
  `render_briefing_card()` draws the 1600 x 1067 PNG. The F-16 is lifted from
  `retlab_briefing.png`, so both pictures share one drawing.
- `game/missiongenerator/briefinggenerator.py` — `_briefing_picture()`: the drop-in, else the
  card (written to the temp folder), else `retlab_briefing.png` if drawing raises.
- `resources/briefing/templates/briefingtemplate_EN.j2` — the text.
- `tests/retlab/test_briefing_image.py`, `tests/retlab/test_briefing_card.py`.

### Constraints

- No setting: the file is the switch (the §42/§43 precedent).
- The app's startup splash (`resources/ui/splash_screen.png`) is RetLab's own too since
  2026-09-29: the same look, an F-16 drawn to scale. It has no drop-in override. The About
  box no longer credits upstream's splash artist.
- Blue only. The red briefing has no picture, as before.
- The card's fonts are Windows': Bahnschrift, else Arial. CI falls back to Pillow's own font.
- At most six flight rows; more add a "+N more player flights" line.
- Some odd-looking briefing values are DCS's own data, not bugs: Tel Nof's TACAN 87X
  transmits `AKR` (ED's Syria `Beacons.lua`), and several Syria fields share tower UHF 225.0.

## §108 — Flight report cards

After a mission, the Qt debrief shows one graded card per blue flight that got airborne,
human-crewed flights first: timing (at the ingress point for an attack flight, the join for an
escort, the station for a patrol), the package target, kills, weapons,
losses, and a human pilot's fuel on landing against the airframe's reserve. Grades are Unsat, Below average, Average and
Above average. Built 2026-09-29, not flown (row B158). A card is titled with its task and
package target, then its squadron and aircraft (2026-10-11; it was the raw DCS group name).

**Design note:** [retlab-flight-report-cards-notes.md](design/retlab-flight-report-cards-notes.md)
has the scoring table.

### Files

- `game/retlab/flight_grades.py`: gathers `FlightFacts` from §91's records and the flight
  plan, then grades them.
- `game/sim/missionresultsprocessor.py`: `record_flight_cards` stores the cards on
  `Game.last_flight_cards` at commit, while the flown ATO exists.
- `qt_ui/windows/QDebriefingWindow.py`: `FlightReportCards`, one `FlightReportCard` each.
- `tests/retlab/test_flight_grades.py`, `tests/qt_ui/test_debriefing_window.py`.

### Constraints

- Planned TOT is measured from `mission_start_time` (§104's early start), because record
  times count from mission start.
- An attack flight is timed at its ingress point and an escort at the join, within 12 NM.
  Do not move this back to the target: a standoff shooter never goes there, and test 55
  faulted 11 of 23 flights for it (2026-10-11).
- A flight whose planned time is after the mission ended gets no timing grade.
- Anti-ship and SEAD are never faulted for firing with no hits.
- Fuel is graded only after a landing, in pounds against the airframe's `min_safe`
  reserve (15% of internal fuel where none is measured).
- AI fuel is never graded. With `ai_unlimited_fuel` on it is constant (§91).
- A grade is a record. Nothing in the campaign reads it.
- No setting.

## §109 — Outside AI reads red's turn

A REST API under `/retribution-ai/*` on the map server, for an AI on the same PC (Claude
Code, for example). It reads red's turn and reports what looks wrong. With the setting
Outside AI plans red ticked (Campaign Management > HQ automation, so it is also on the new
game wizard's Campaign options page), it also plans red: packages, TOTs, front stances, buying and
selling, with notes saved in the campaign. Developer tools > Copy AI connect link copies
the URL with its token. Ported from juanjux/dcs-escalation (LGPL-3). Stage 1 built
2026-10-09 (row B201), stage 2a the same day (row B204); 2b (loadouts, waypoints,
transfers, ships, repairs, squadron moves) and MCP are agreed, not started.

**Design note:** [retlab-llm-opfor-notes.md](design/retlab-llm-opfor-notes.md) has the DM
call that reversed the 2026-08-24 "no LLM" rule, the stages and what was left out.

What the read side reports, where it differs from the raw objects (2026-10-10, after the
first live reviews on Kola):

- A flight's `weapons` are the fit the mission is built with: the weapon-date rule
  applied, by weapon name. The planned fit listed weapons the mission never loads.
- `validate` fails a plan only for an uncrewed seat or a TOT that cannot be made. A start
  the §104 early mission start covers (up to 30 minutes) is a note, as is a TOT after
  the human's mission length. The scripted planner's own plan produces both. An ASAP
  BARCAP, AWACS or tanker is never failed on its TOT: Take Off re-runs it from the
  mission start (`retime_asap_support`).
- `prev_turns.events` names the sides Blue and Red. The campaign log is written for the
  human, so red's own arrivals read "Enemy reinforcements".

### Files

- `game/agent/views.py`, `service.py`, `mapimage.py`, `planner.py`, `schemas.py`;
  briefings in `resources/agent/`.
- `game/commander/missionproposals.py`, `packagebuilder.py`, `game/squadrons/airwing.py`:
  `preferred_squadron`.
- `Settings.outside_ai_plans_red` (`game/settings/fields/campaignmanagement.py`; it was
  `Game.opfor_ai_enabled`, a Developer tools toggle, until 2026-10-10, and
  `Game.__setstate__` carries an old save's choice over), `game/game.py`
  (`opfor_ai_notes`), `qt_ui/widgets/QTopPanel.py` (Take Off fallback).
- `game/server/retributionai/routes.py`; mounted in `game/server/app.py`.
- `game/server/security.py`: token by `X-API-Key` header or `?token=`. Every route on
  the server needs one since 2026-10-11: the AI's key opens the AI's routes, and a
  separate key that Qt hands the map page opens the map's. A client bundle built before
  that leaves the map's routes open for the run, with a warning in the log
  (`tests/server/test_api_key_on_every_route.py`).
- `qt_ui/windows/QLiberationWindow.py`: `copy_ai_connect_link`.
- `tests/agent/test_read_api.py`, `tests/agent/test_write_api.py`.
- `tests/agent/test_write_on_real_campaign.py` runs the write path on the same real
  campaign: a failed plan hands back its aircraft and pilots, a create or delete reaches
  the map, and a buy reports what it bought. The 2026-10-11 audit fixes it pins are
  listed in the design note.
- `tests/agent/test_blue_plan_never_served.py` builds a real campaign
  (`tools/_campaign_game.py`, Caucasus - Northern Russia) and calls every GET route for red
  twice: once with blue's ATO swapped for a tripwire that fails on any access, once with
  marker values planted on blue's packages, flights and budget that must appear in no
  response. The routes are read from the router, so a GET added later is covered, and one
  the test cannot call fails it. The PNG map is covered by the tripwire only. Idea from
  Hussar2477/dcs-retribution (`llm-ai-opponent`), 2026-10-10.
- **Loss causes on the last-turn page (2026-10-10).** `prev_turns.last_turn` breaks each
  side's losses down by what killed them. The base plugin records the killer DCS names in
  `S_EVENT_KILL` (`kill_causes` in state.json: target, killer, killer type, weapon name);
  `StateData.kill_causes` parses it; `game/losscauses.py` looks both units up in the unit
  map and sorts the kill as `aircraft`, `sam`, `aaa`, `ship`, `ground`, `own_side` or
  `unknown`, per kind of loss (`aircraft`, `front_line`, `sites`); `Sitrep.loss_causes`
  keeps the result with the turn. Served as `blue_lost_to` / `red_lost_to`, plus
  `*_air_killers` and `*_air_weapons` (the top five type names). Both sides (DM call
  2026-10-10: the page already gives both sides' counts). A loss with no kill event (a
  crash, a collision, fuel) has no cause, so the causes can total fewer than the counts.
  The AI link only: no kneeboard, debrief or SITREP line reads it. Idea from
  Hussar2477/dcs-retribution (`llm-ai-opponent`). Tests: `tests/test_loss_causes.py`,
  `tests/lua/test_dcs_retribution_runtime.py`. Row **B217** is the in-mission half.
- **Two engine facts on the read-out (2026-10-10).** A front's `capture_blocked_by` is the
  count of living enemy ground groups inside the enemy base's capture zone
  (`BattlePositions.for_control_point(...).blocking_capture`, the rule the scripted
  planner's `BreakthroughAttack` waits on), and each of those groups is a target of kind
  `garrison` (suggested task BAI), so the AI can aim at what it is told is in the way.
  A squadron's `can_add` is how many aircraft it can still order: its base's unclaimed
  parking, then its size cap, as `AircraftPurchaseAdapter.can_buy` counts. Both are
  literal zeros when zero. The tests read them off a real campaign
  (`tests/agent/conftest.py`, `campaign_game`). Ideas from Hussar2477/dcs-retribution
  (`llm-ai-opponent`).
- **Two faults test 56 found (2026-10-11).** The target list left out the enemy armor
  groups outside a base's capture zone (`BattlePositions.defending_front_line`), which
  are what the scripted planner's `AttackBattlePositions` sends BAI at: red's plan aimed
  two packages at groups the AI could not see. They are now targets of kind `armor`
  (suggested task BAI) for every enemy base. And `validate` reported a package that
  launches with the mission (an ASAP AWACS or tanker, TOT a minute or two before the
  turn clock) as "TOT +-2 min is after the 45 min the human plans to fly": a TOT before
  the clock is inside the window, and the notes print one sign. Tests:
  `tests/agent/test_read_api.py`, `tests/agent/test_write_on_real_campaign.py`.

### Constraints

- Red only, enforced in `service.opfor_only`. Blue's ATO is never served.
- Reads never mutate game state. Writes need the toggle on (`service._writable_game`).
- The scripted planner plans and buys for red at every turn start and mid-turn re-plan,
  toggle on or off (2026-10-10; it stood down for the AI before, which left red empty
  after a re-roll and its budget unspent). The AI edits that plan. If red has no packages
  at Take Off, the scripted planner plans red's missions again.
- Only the AI routes need the token; the map server's routes are unchanged.
- No setting: the toggle is saved on the `Game`.

## §110 — Ballistic missile call-for-fire — REMOVED (2026-10-12)

**Removed 2026-10-12 (DM call), two days after it was ported and before it was flown.** The
`bmstrike` plugin (default off) gave a player an F10 radio menu to call rounds from one of
their side's own Scud, Iskander or ATACMS launchers onto a map marker. Ported 2026-10-10 from
CleeeCATCH/dcs-retribution (author virhed, LGPL-3), commit `eb892b99df`; audited and fixed in
#1202.

**Why it went:** the DM's slim-down pass of 2026-10-12. The plugin was off in his default
settings and in all ten of his saves, and its checklist row (B215) was never run.

**What went:** `resources/plugins/bmstrike/`, its `plugins.json` entry,
`luagenerator.ballistic_missile_batteries` and the `ballisticMissiles` table it emitted, both test
files, row B215, and the changelog and What's New entries from its two days. The launchers are
ordinary campaign units and are unchanged; missile sites still get their generated fire task.

**To bring it back:** `git show 57ab9e720:resources/plugins/bmstrike/BallisticMissileStrike.lua`,
and #1202 for the five faults found in the port (one menu per group, renamed marks, the round
count, a destroyed launcher, the range window).

## §111 — Sector war

The war region is cut into named sectors about 10 NM across, shaped by the ground. Step 1,
built 2026-10-12: each side's territory is drawn on the F10 map and the app map, worked out
from the bases and the fronts. A country holding a base is filled out to its border; the
first build stopped 60 NM past the outermost bases and drew a rectangle on Iraq. Not flown
(row B229).

Battles along the border, built 2026-10-12 on Brady's call: each front's ground units are
split into a battle in each sector along the shared border, out to twice Maximum frontline
width measured along the border, instead of one short line across the road. The battle result
and the front's movement are unchanged. Setting *Front line battles spread along the
border*, on by default. Not flown (row B230).

CAS follows the battle line, built 2026-10-17 on Brady's call: with battles along the border, a
CAS flight's FLOT START and FLOT END sit on the outer battles (the end nearer home first), with
up to 3 BATTLE stops on battles evenly spaced between. The AI searches its engagement range
around each stop. With the setting off or no battles, the plan is unchanged. Not flown (row B240).

Step 2, built 2026-10-12: sectors decide the fight. Each sector's owner is saved; the
front line sits where its road enters the enemy's sectors; a won battle takes 2, 1 or 0
sectors by how clear the win was; a base falls with its sector; a road through enemy
sectors carries no convoys. Setting *Sectors decide the ground war*, on for new games; a
save from before it keeps it off. Not flown (row B232).

Step 3 (a CAS battle-map kneeboard card per front) is agreed with Brady, not built.

**Design note:** [retlab-sector-war-notes.md](design/retlab-sector-war-notes.md) has the
choices, the algorithm and the step 2 notes.

### Files

- `game/theater/sectors.py`: the 1 NM grid, sector growth and names, territory, the shape
  helpers and the caches.
- `game/missiongenerator/drawingsgenerator.py`: `generate_territory`, drawn first; the
  front line is drawn along the battle stretch when there is one.
- `game/theater/frontbattles.py`: each front's stretch of border and its battle sites.
- `game/missiongenerator/flotgenerator.py`: `battle_slots`, `pick_battles`,
  `_battle_point`; each group keeps its own forward heading (`_local`).
- `game/server/frontlines/models.py`: the app map's front line follows the battle stretch.
- `game/server/sectors/models.py`: `TerritoryJs` and `SectorsJs` on `/game`.
- `game/theater/sectorwar.py`: `SectorWar` (owners, `take_sectors`, `claim_base`,
  `fallen_bases`, `route_progress`), `road_is_cut`, `ensure`.
- `game/theater/frontline.py` (`_sector_war_progress`),
  `game/sim/missionresultsprocessor.py` (`sectors_won`, `take_sectors`,
  `commit_sector_war`), `game/theater/transitnetwork.py`, `game/game.py`.
- `client/src/components/territorylayer/`, `client/src/api/territorySlice.ts`: the
  Territory and Sectors layers.
- `game/ato/flightplans/cas.py` (`battle_stop_sites`, `CasLayout.battle_stops`),
  `game/missiongenerator/aircraft/waypoints/casingress.py` (`CasStopBuilder`): CAS on the
  battle line.
- `tests/theater/test_sectors.py`, `tests/theater/test_sector_war.py`,
  `tests/ato/flightplans/test_cas_battle_line.py`,
  `client/src/components/territorylayer/TerritoryLayer.test.tsx`.

### Constraints

- A DCS drawing has no holes. A pocket is drawn by cutting the shape around it
  (`hole_free_pieces`), with the edge drawn separately.
- Every F10 drawing needs its own name: MIST drops a repeated one.
- The territory border is pinned to the front by sources 1.2 NM either side of the bowed
  trace. Without them the edge drifts off the drawn front line.
- A country holding no base on either side (§98's NEUTRAL posture) is nobody's ground.
- Sectors are rebuilt, not saved; step 2 saves their owners by name. A change to the
  seeding or naming gives a running campaign's renamed sectors back to nobody.
- The sector cache is keyed by base ids as well as names: two games of one campaign share
  names, and a stale id silently stops bases falling with their sectors.
- The territory and battle caches are keyed on the owners themselves (`owner_key`), never
  on `version`: a reloaded save re-flown differently reaches the same version with other
  owners, and the module caches outlive the game.
- A side with no front-line units at a front takes no sectors there, whatever the battle
  result says. Upstream scores an empty front as a strong defeat; under sector war that
  handed over 2 sectors a turn and the base with them.
- In a sector-war game the fronts follow the owners, never the other way round. Only turn 0
  reads owners from the fronts.
- Battles only stand on ground the landmap marks drivable. Abchazian Blitz's border near
  Sukhumi has about 6 NM of it, so that front stays short.
- There are as many battles as the side with more armor wedges can fill. The thinner side
  spreads its wedges end to end, so some pockets are one-sided pushes. Each group faces
  across the border at its own battle.
- The unit count is unchanged: *Maximum ground units deployed per frontline by faction*.
- A CAS flight on the battle line gets one search circle (*EngageTargetsInZone*) per stop.
  They are DCS en-route tasks, so each stays on for the rest of the route and the circles add
  up; one zone over the whole line would send the AI deep behind it. The JTAC orbits the
  busiest battle.
- CAS stops use every battle site, not the ones the mission fills (`pick_battles` needs the
  ground forces). The ends hold units unless the bigger side fields one wedge; a middle
  stop can land on an empty site.

## §112 — HQ requests

Each turn HQ asks the players to take out up to three enemy targets the BLUE auto-planner put no
package on: one easy, one mid and one hard to reach, each open 2 to 5 turns. Within a tier the
pick leans on IADS nodes, then strike targets (2026-10-18, row B248). No prize; the
SITREP notes the ones destroyed. The order half of juanjux's High Command (Brady, 2026-10-12).
Setting *HQ requests*, Doctrine page, on for new games; a save from before it loads with it
off (`Game.__setstate__`). Built 2026-10-12, not flown (row B231).

**Design note:** [retlab-hq-priority-targets-notes.md](design/retlab-hq-priority-targets-notes.md) §9.

### Files

- `game/retlab/hq_requests.py`: candidates, difficulty, tiers, `refresh`, `record_results`,
  and the kneeboard and panel lines.
- `game/game.py`: `hq_requests` on the game; `refresh` at the end of `initialize_turn`.
- `game/sim/missionresultsprocessor.py` + `game/sitrep.py`: `hq_request_lines`.
- `game/server/game/models.py`: `HqRequestJs` on the campaign status.
- `client/src/components/campaignstatus/`, `client/src/components/hqrequestslayer/`.
- `qt_ui/windows/groundobject/QGroundObjectMenu.py`: the HQ request row.
- `tests/retlab/test_hq_requests.py`, `client/src/components/hqrequestslayer/HqRequestsLayer.test.tsx`.

### Constraints

- Drawn once per turn, after blue's planning. A blue re-plan mid-turn never changes them.
- Never a site `hidden_from(BLUE)`; difficulty counts only rings blue knows, overview ignored.
- Motorpools are never requested: their vehicles are drawn afresh, so one never dies.
- SAM sites are "other" (1x), not IADS: the auto-planner already goes after them (Brady).
- No prize, ticket or loan. RetLab's line is a record, never a reward (§96, §108).

## §113 — AI fills empty player flights

A player flight marked **AI fills if no player** (General tab) gets a late-activated AI copy of
its player seats. If nobody is in any of those seats at the check time (5 minutes, setting), the
coalition is told and the copy starts in the air over the home base at the planned takeoff and
flies the same tasking. Settings on Mission Generation > Player slots: *AI fills empty player
flights* (each box's starting value, off), *AI fill: check player seats after*, *AI fill:
announce the takeover* (on). Brady's idea from his Northern Front 2003 campaign; built
2026-10-16, not flown (row B234).

**Design note:** [retlab-ai-fill-notes.md](design/retlab-ai-fill-notes.md).

### Files

- `game/retlab/ai_fill.py`: `offers_ai_fill`, `ai_fill_wanted`, `AiFillPair`,
  `populate_ai_fill_lua`.
- `game/missiongenerator/aircraft/aitwin.py`: `ai_twin_view`, `AiTwinSeat`, `copy_identity`.
- `game/missiongenerator/aircraft/aircraftgenerator.py`: `_spawn_ai_twin`.
- `game/missiongenerator/aircraft/waypoints/waypointgenerator.py`: `activation_by_script`.
- `resources/plugins/aifill/aifill-config.lua`: the check and the launch, always on.
- `qt_ui/windows/mission/flight/settings/QAiFillCheckbox.py`.
- `tests/retlab/test_ai_fill.py`, `tests/lua/test_aifill_runtime.py`.

A late-activated client group is checked a check delay after it appears, and a twin that
replaces a package's primary takes the package's AI escorts (2026-10-17, row B239).

### Constraints

- The twin covers only the player seats. A part-player flight's AI wingmen fly in the client
  group as they always did (Brady, 2026-10-16).
- Air start at the takeoff time, never a runway start: a late-activated runway start lands on
  a taxiway in multiplayer. Never a parking spawn: the twin would hold spots all mission.
- `ai_twin_view` must put back everything it changes, the waypoint TOTs and fuel included:
  the client flight's kneeboard reads them from the same waypoint objects.
- The twin maps to the same pilots as the seats it replaces, so a loss lands on the roster.

## §114 — Coordinated TOT

A package made from the map times itself behind the SEAD or DEAD package hitting the SAM that
covers its target: 2 to 8 minutes after it, the §69 window. With no such package, or a window
it cannot make inside the mission, it flies ASAP and the package window says why. A third TOT
mode beside ASAP and a typed TOT, ticked by default on a new package, worked out again on every
change and at Take Off (Brady's choices, 2026-10-16). No setting. Built 2026-10-16, not flown
(row B236).

**Design note:** [retlab-coordinated-tot-notes.md](design/retlab-coordinated-tot-notes.md).

### Files

- `game/commander/coordinatedtot.py`: the window, the warnings, the Take Off pass.
- `game/ato/package.py`: `auto_coordinated`; an old save loads with it off.
- `game/sim/missionsimulation.py`: the Take Off pass runs before `settle_mission_start`.
- `qt_ui/models.py`, `qt_ui/windows/mission/QPackageDialog.py`,
  `qt_ui/windows/mission/QAutoCreateDialog.py`: the tick, the TOT line, the warning line.
- `tests/commander/test_coordinated_tot.py`.

### Constraints

- Never earlier than ASAP. Only strike-class packages wait (Strike, BAI, OCA, CAS).
- A site counts only if blue knows it, overview ignored (`fog_intact`). Red reads ground truth.
- The Take Off pass times suppression packages first, so a strike waits for its SEAD's final TOT.

## §115 — Phone map — REMOVED (2026-10-21)

**Removed 2026-10-21 (DM call), two days after it was built and before it was flown.**
File > Phone link turned on a view-only copy of the campaign map for a phone on the same
Wi-Fi, behind its own phone key and a QR code. The phone had its own layout (Map, Flights,
Kneeboards), and an ntfy topic set in the same dialog got a ping when a turn's results were
in. Built in #1313 and #1314.

**Why it went:** the DM did not want it. Its row (B254) was never run.

**What went:** `game/server/phone.py` and the home-network socket in `game/server/server.py`,
`qt_ui/windows/PhoneLinkDialog.py` and its File menu entry, the phone and ntfy preferences in
`qt_ui/liberation_install.py`, `game/retlab/turn_ping.py`, `game/retlab/mission_pages.py` and
`game/server/missionpages/` (the Kneeboards tab's record), `client/src/components/phone/` and
the client's read-only switch, the `segno` requirement, the design note, three test files,
row B254, and the changelog and What's New entries. The map page keeps the RetLab name and
logo from #1314. Old preference files keep their `phone_*` and `ntfy_topic` keys; nothing
reads them.

## §117 — Airborne package control

An **ABCCC** flight type (the EC-130E ABCCC role) for the C-130J-30 only. With
**ABCCC C-130 (SkyEye)** on (RetLab Features page, off by default) the planner
adds one, optional, to each land AWACS package (`PlanAewc`). It orbits 30 NM outside
the threat rings (`ABCCC_THREAT_BUFFER` in `aewc.py`), well ahead of the AWACS's 80 NM
standoff, and the package's 2-ship escort always flies and covers the ABCCC instead of
the AWACS (`joinpoint.py`). It can also be fragged by hand. Callsigns rotate
each turn through Anvil, Ramrod, Blackjack, Crown and Sentinel.

While an ABCCC C-130 is **alive and airborne** the `pkgcontrol` plugin runs every
blue package with a player seat on **STRIKE (common)**, one UHF channel allocated per
mission and set as each of those packages' own frequency (see Presets below), listed on the
kneeboard comms as "STRIKE (Anvil)":

- **Check-in:** F10 > Package control > Check in, or spoken ("Anvil, Colt 1-1, check
  in"). The reply gives radar contact, the hold angels and the push time.
- **Ready to push / say push time:** spoken. Ready pushes early when the SEAD and escort
  are airborne, else says what is missing.
- **Airborne:** spoken ("Anvil, Colt 1-1, flight is airborne", "wheels up", "off the
  ground", "departing"). From a flight that has not checked in it is a check-in; after a
  check-in the reply is "copy airborne" (Test 64, 2026-10-24). Needs BradySox/skyeye#15;
  an older SkyEye sends it as an unreadable call and the ABCCC says "say again".
- **Push to join:** at the package push time (the earliest strike flight's HOLD departure),
  "Ford package, Blackjack, push to join."
- **Execute:** "Ford package, Blackjack, execute" once every airborne striker and escort
  (AI, or a seated player) is within 5 NM of its JOIN point. SEAD is planned ahead of the
  strikers and is not waited for. A late flight gets 3 minutes past the join time (moved by
  any hold), then "<flight>, Blackjack, not at join. Package executing without you"; with no
  striker at the join the package aborts. A package with no JOIN point executes at the push.
- **Roll call:** 3 minutes before the push, "All players, <ABCCC>, check in". Seated player
  flights answer (voice or F10) and get "copy ready"; AI flights are read out as up or not
  airborne in the same transmission (2026-10-22: sent as a second call right behind the roll
  call, the read-out was transmitted and never heard). A player still silent at the push, by
  role (user call, 2026-10-20): SEAD holds like a SEAD on the ground (two holds, then abort),
  an escort gets one hold, a striker is left behind if another striker is set (else one hold,
  then abort). Empty slots are not waited for.
- **Hold:** a SEAD or escort flight not airborne slips the push 3 minutes, at most twice.
  After that the package pushes if a SEAD is airborne (or it has none), else aborts.
- **No striker up (Test 64, 2026-10-24):** with no strike flight airborne the push holds the
  same way, naming the flights ("Hold, hold. Ford6-1 not airborne"), and after the second
  hold the package aborts "No strikers airborne" instead of pushing. Ready to push gets a
  negative naming them. On the way to the join the package aborts as soon as no striker is
  airborne. Before, it pushed with the only striker on the ramp and aborted at the join 8
  minutes later.
- **Abort:** at the push, when every target unit is dead or every SEAD flight was lost.
- **Egress:** once every live striker has been within 30 NM of the target and is opening
  past 10 NM.

Airborne AI flights in the package obey: a hold pushes a 3-minute orbit at their HOLD
point, an early push sends `SwitchWaypoint` past the HOLD, an AI striker or escort at the
JOIN before execute orbits it until execute sets the package's user flag
(`pkgcontrol_execute_<n>`, the orbit's stop condition), and an abort replaces their
route with a landing at home. Parked AI is left alone (a pushed task would replace its
takeoff).

**Presets (2026-10-21).** STRIKE is each player package's frequency for its players, so it is
the package preset and the kneeboard's FREQ line ("FREQ: STRIKE COM1 Ch 3 - UHF 289.000");
nobody dials it by hand. It is kept in the mission only (`MissionData.strike_packages`,
`MissionData.package_frequency`), never written to the package, so the save never carries
STRIKE as a package frequency. The AI flights in the package fly on STRIKE with its players
(user call, 2026-10-24; #1352 had moved them off it): `setup_radios` gives a non-player flight
with no frequency of its own STRIKE and records its group in `MissionData.strike_groups`, and
the voice-bot sweep (`_move_ai_off_voice_bots`) leaves those groups on STRIKE. Every other AI
group still moves off STRIKE, Vacuum, SkyEye, Ground and Tower. With Voice AWACS on,
SkyEye's frequency and Vacuum's take the presets the silent blue AI AWACS had
(`awacs_presets` in `game/radio/channels.py`); the AI AWACS stay on the kneeboard with no
preset. On a two-radio jet the presets follow a squadron comm card: COMM1 the support nets
(SkyEye, Vacuum, STRIKE, JTAC, tankers), COMM2 the flight on Ch 1 then each field's Ground
and Tower where COMM2 tunes UHF. An F-16's COM2 is VHF only, so its Ground and Tower go on
COM1 after the support nets. The F-15E's radios were the wrong way round (ARC-210 on COMM1);
its yaml now puts the ARC-164 support nets on COMM1 and the flight and ATC on the ARC-210.
Only the flight's own side's JTACs and tankers are preset: a red KC-135 sat on a blue F-16's
COM1 Ch 5 before. A frequency the radio cannot tune is never preset, on either radio or on a
one-radio jet.
A **Comm Card** kneeboard page after the comms page lists every preset on both radios by
name (`kneeboard/commcard.py`). Its column heads use the airframe's own radio names (COM1,
UHF, AUX) as the other pages do, and a name too long for its column is cut with "...".

**Fixed 2026-10-21: the ABCCC had no packages.** The aircraft generator cleared its package
table at the start of each side's pass, so red's pass wiped blue's: `player_packages()` was
empty, the plugin got no controllers and no packages, and every Vacuum emitter had no STRIKE
flag. Each pass now links the datalink for its own side's packages only and clears nothing.
A player flight's callsign is now its lead's seat ("Ford 5-1"), and the plugin matches
SkyEye's "ford 5 1", the flight alone ("ford 5") and a wingman ("ford 5 2") on Strict, as
`voiceatc` does. Before, only the non-Strict fallback matched. Not flown (row B266).

**Phrasing (2026-10-21, user call after a flown review).** The spoken lines read the way a
controller says them, and each `say` carries `text` and `speech` apart, as `voiceatc` sends
them: "Ford package, Blackjack, push" (was "Package Ford, ..."), push time "1410" in text and
"one four one zero" in speech, callsigns "Ford niner one", "Dodge 9 airborne" (was "up"), and
a dead target named in the text only (the say message's `text`; on screen only without
LuaSocket). The roll call names the package ("Ford package,
Blackjack, check in. Push in three minutes"), or every package due that tick in one call
("Ford and Colt packages"). After the roll call a "ready to push" from a flight that has not
answered is its check-in, never an early push. SkyEye now passes a call to the controller it
cannot read as kind `unknown`; the plugin answers "<callsign>, Blackjack, say again" in the
controller's voice, by the flight it matched or the callsign heard, else "Station calling
Blackjack, say again your callsign". SkyEye also reads a bare "ready", "with you", "on
station" and "checked in" as a check-in (`BradySox/skyeye` PR #10). The record now lists
every blue player flight (`players`: group, lead seat), and the plugin sends SkyEye a
`pilots` list in its `packages` message: each seated player's DCS name and seat, plus the
flight alone for its lead, so the AWACS finds "Ford 9-1" when the player is "Flash". Not
flown (row B271).

**Fixed 2026-10-21 (Test 63): an inactive late-activated flight read as airborne.** A
late-activation unit not yet activated reads `isExist` and `inAir` true, so `airborneUnit`
now also needs `isActive()`; a SEAD waiting for activation now holds the push.

**Execute at the join (2026-10-23, user call).** The single "push" from the HOLD became two
calls: "push to join" leaving the HOLD and "execute" with the package assembled at the JOIN
(above). Before, nothing checked that the package came together. The record carries each
flight's JOIN point, angels and due time (`joinX`, `joinY`, `joinAngels`, `joinAfter`).
Players keep saying "ready to push" and "say push time", so SkyEye's parser is unchanged.
A wait at the JOIN slips the time on target by that wait. Not flown (row B276).

With no ABCCC C-130 airborne there is no package control: nothing is said and
the push waits for one. The AWACS never stands in (user call, 2026-10-20).

**Voice.** SkyEye speaks every call through RetLab's SkyEye copy (`BradySox/skyeye`, the
mission link). The plugin talks to SkyEye over local UDP (127.0.0.1:42690, SkyEye's
`mission-link-address`) through DCS's LuaSocket. SkyEye tunes STRIKE as a listen radio,
answers to the controller callsign, passes the package calls to the mission and speaks the
mission's lines. The AWACS (SkyEye's own GCI) works STRIKE trimmed: it answers calls heard
there and repeats threat and merge calls, nothing else. The AWACS takes a random voice each
mission and the controller the other. A spoken call is never on-screen text too (2026-10-24,
user call); only without LuaSocket are the calls text to the package's players.

Built 2026-10-20 from a survey of how hand-built campaigns run packages from an AWACS
(recorded clips on scripted triggers, F10 check-in, a push-time hack). Not flown (row B258).

**Voices by country (2026-10-20).** The AWACS and the ABCCC each speak with a voice
from their own squadron's DCS country: American or British from Kokoro (`kokoro#am_eric`,
four adult voices each, picked by ear; run by sherpa-onnx's TTS tool in the Kokoro folder's
`bin`), or English read by
native Arabic and Spanish speakers (the multi-speaker `en_US-l2arctic-medium` model). Every
other country sounds British; the Asian accents were dropped (user call, 2026-10-20). The two are always opposite genders. SkyEye loads the voices
from its `voices-dir` (default `voices`, one folder per voice) and falls back to its own voice
when one is missing. L2-ARCTIC and VCTK are CC BY-NC: players download them, RetLab ships none.

### Files

- `game/retlab/package_control.py`: `dcsRetribution.packageControl`, voices, STRIKE name.
- `game/ato/flighttype.py`, `flight.py` (callsign family), `flightplans/aewc.py`,
  `game/commander/tasks/primitive/aewc.py`: the ABCCC in the AWACS package.
- `game/missiongenerator/missiongenerator.py`: STRIKE allocation and the kneeboard comm.
- `game/missiongenerator/aircraft/aircraftbehavior.py` (`configure_package_control`).
- `resources/plugins/pkgcontrol/`: the calls, the F10 menu, the SkyEye link.
- `game/retlab/skyeye_voices.py`: the voices by squadron country (below).
- `game/missiongenerator/kneeboard/voicepages.py`: the two cards after the comms page,
  "Talking to <ABCCC>" and "Talking to <AWACS>". Each card is the frequency and the common
  calls the bot recognizes, each with its answer on one line; no prose on what a call does
  (user call, 2026-10-22). The AWACS card has no check-in: SkyEye answers one by asking
  whether a radio check or an alpha check was meant.
- `tests/retlab/test_package_control.py`, `tests/lua/test_pkgcontrol_runtime.py`.

### Constraints

- Never an AWACS task on the C-130: DCS would make it a second AWACS voice.
- The C-130J EW plugin claims every C-130J-30 by airframe, so an ABCCC flight is
  on its deny-list (`_ew_excluded_c130j_groups`).
- The link needs DCS's mission scripting sandbox opened (`require`, LuaSocket),
  Retribution's own install step. Without it the calls are text only.
## §122 — Exact site layouts

A campaign `.miz` vehicle group named with the prefix **FIXED** is an air-defense site drawn
unit by unit, and New Game keeps it as drawn: each unit's type, position and heading.
Every other group stays a one-unit marker (built 2026-10-24, Brady's calls; design note
`docs/dev/design/retlab-exact-site-layouts-notes.md`).

- The task comes from the preset group the drawn units match best (trucks left out).
- If the owner's faction cannot field a drawn unit other than a truck, a stock site of that
  task generates at the group's first unit instead.
- Guns in a long or medium range site are its `(PD)` group (Skynet point defense).
- The owner's closest ForceGroup adds its layout's optional trucks and point defense.
- Repair keeps the spots; a site bought new in the base menu is a stock layout.
- Not flown (row B279).

### Files

- `game/theater/exactsite.py`, `game/theater/presetlocation.py` (`ExactSitePreset`),
  `game/campaignloader/mizcampaignloader.py` (`is_exact_site`).
- `tests/theater/test_exact_site_layouts.py`.

## §121 — Radio discipline

One campaign setting, **Radio discipline** (Mission Generator page, Cockpit & nav aids),
read by every SkyEye voice plugin as `dcsRetribution.radioDiscipline`. Default **Strict**;
a squadron that does not fly by the book picks Relaxed or Casual (user call, 2026-10-20).
Voice ATC (#1328) reads the same setting.

| | Strict | Relaxed | Casual |
|---|---|---|---|
| Roll call 3 min before the push | yes | yes | none |
| Silent player | held or aborted by role (§117) | counts as ready | counts as ready |
| Hold for a flight on the ground | SEAD or escort | SEAD or escort | SEAD only |
| Egress call | yes | yes | none |
| Call that names only the pilot on STRIKE | ignored | reaches the ABCCC | reaches the ABCCC |
| Close-enough callsign ("Colt" for Colt 1-1) | no | yes | yes |
| Vacuum | every radar | every radar | only radars over a player package |
| AWACS on STRIKE | threats, merges, answers | threats, merges, answers | threat calls only |

The ABCCC tells SkyEye `looseCalls` (off Strict) and `strikeThreatsOnly` (Casual) in its
packages message. SkyEye parses a pilot-only call heard on STRIKE for the first package
controller; with threats only it drops merges on STRIKE and answers calls heard there on
its own frequency. Built 2026-10-20. Not flown (row B263).

### Files

- `game/settings/enums.py` (`RadioDiscipline`), `fields/missiongenerator.py`.
- `resources/plugins/pkgcontrol/pkgcontrol-config.lua`, `resources/plugins/vacuum/vacuum-config.lua`.
- `tests/lua/test_pkgcontrol_runtime.py`, `tests/lua/test_vacuum_runtime.py`.
## §120 — Voice bots on Take Off

A machine preference, not a campaign setting: **File > Voice bots**, off by default. With
it on, Take off (`QTopPanel.launch_mission`) calls `start_voice_bots` on a background
thread (`game/retlab/skyeye_launcher.py`):

1. The SRS server starts minimized if it is not running (`SRS-Server.exe` under the installer's
   `HKCU\Software\DCS-SR-Standalone\SRPathStandalone`), and RetLab waits up to 60 s
   for port 5002.
2. SkyEye starts from its folder with `--config-file config.yaml`, in a hidden console
   (2026-10-24, user call, row B277; it was minimized). Its output goes to
   `skyeye-takeoff.log`, which the **SkyEye log** button shows
   (`qt_ui/windows/SkyEyeLogDialog.py`, on the mission status panel and in File > Voice
   bots). No `skyeye.exe` or no `config.yaml` means no SkyEye.
3. The SRS client starts if it is not running and is sent `127.0.0.1:5002` on UDP 5069,
   the message SRS's own DCS hook sends. The hook sends it only to a server's guests,
   never to the host, so a single-player host was never auto-connected. The client
   acts on it only with its Auto Connect option on.

Anything already running is left alone. On debrief only the SkyEye RetLab started is
stopped; SRS keeps running (user call, 2026-10-20). The folder defaults to
`Saved Games\DCS\Retribution\SkyEye`. Built 2026-10-20. Not flown (row B262).

**Which SkyEye is RetLab's (2026-10-21).** The SkyEye a Take off starts is recorded in
`%LOCALAPPDATA%\DCSRetribution\skyeye-takeoff.json`, beside the preferences: the PID of
its PowerShell console (SkyEye runs under it) and that process's creation time. A
running process with that PID and creation time is RetLab's, across a Retribution
restart; a reused PID has another creation time. Any other `skyeye.exe` is the player's.
Before this the record was in memory only, and Retribution restarted five times on
2026-10-20, each leaving a SkyEye that debrief no longer stopped.

- **Stop:** `taskkill /T` without `/F` asks the console to close, so SkyEye gets a close
  event and can sign off SRS. After 5 s it is forced with `/F`. The record is cleared.
- **One start at a time:** a Take off while a start is still waiting for SRS (up to 75 s)
  starts nothing; the start under way covers it. SkyEye is checked for again, under a
  lock, right before it is started.
- **Early quit:** a SkyEye that quits within 60 s is logged with its real run time and
  last output, unless debrief stopped it.

Row B264.

### Files

- `game/retlab/skyeye_launcher.py`, `qt_ui/windows/VoiceBotsDialog.py`,
  `qt_ui/liberation_install.py` (`skyeye_autostart`, `skyeye_dir`),
  `tests/retlab/test_skyeye_launcher.py`.

### Constraints

- Never block Take off on SRS or SkyEye: the start runs on a daemon thread.
- At most two connect messages: each can make a connected client reconnect.
- Never stop a `skyeye.exe` by name: only the recorded PID with its creation time is
  RetLab's.
- SkyEye's console is hidden (`SW_HIDE`), never absent (`CREATE_NO_WINDOW`): a taskkill
  without `/F` closes it through its window, which is what lets SkyEye sign off SRS.
## §119 — Voice ATC

**Voice ATC (SkyEye)** (RetLab Features page, off by default) gives player flights a Ground
and a Tower controller at every airfield a player flight takes off from, lands at or diverts
to (divert added 2026-10-21, user call). AI-only
fields and AI flights keep DCS's own ATC. Step 1 of three in the approved plan: Ground and
Tower. Departure, Approach, Arrival and Emergency come in step 2, polish in step 3.

- **Frequencies:** each field gets two new UHF AM channels, Ground and Tower, reserved like
  STRIKE (`allocate_atc_frequencies`). UHF, because the F-4E, the F-5E and a Tomcat pilot
  without a RIO have no VHF radio (user call, 2026-10-21; VHF AM from #1340 until then). A
  pair pinned while they were VHF is picked again on the next generate. A field's pair is **pinned for the campaign** the first time a player flight uses it
  (`Game.voice_atc_frequencies`, saved; user call, 2026-10-21), so pilots can learn it. Every
  pinned pair is reserved before anything else that turn, and a hand-set package or flight
  frequency that lands on one moves (`RadioRegistry.atc_pinned`), never the ATC pair. Old
  saves pin on their next generate.
  Never the field's DCS tower frequency: DCS's own ATC on it keeps telling a player who taxis
  without its permission to hold position (user call, 2026-10-20).
- **Presets and kneeboard:** a player jet's inter-flight presets carry the field's Ground and
  Tower in place of its DCS tower (`CommonRadioChannelAllocator`; a squadron with its own
  presets keeps them). The comms ladder lists "<field> Ground" and "<field> Tower" with
  their channels, and an ATC card
  (`AtcPage`) follows the voice controller cards (user call, 2026-10-20). Below the
  frequencies it lists the calls going out and coming home, each with ATC's answer and the
  readback (calls only, user call 2026-10-22). The card lists
  (`AtcPage`) follows the voice controller cards (user call, 2026-10-20). The card lists
  the home field, a different arrival and the divert, each Ground and Tower with its preset
  channel ("Tel Nof Ground: COMM2 Ch 2, 130.600 AM"), or the frequency alone when not preset.
  Both cards name a station as ATC's own text does (`station_name`; the comms ladder said
  "Tel Nof GROUND" until 2026-10-21). The Mission Info
  airfield table and the departure page's ATC box show "GND ... / TWR ..." with their preset
  channels in place of the DCS tower (`atc_lines`, user call 2026-10-21), for the departure,
  arrival and divert rows alike. The DCS tower shows only with Voice ATC off.
- **No squawk codes** (user call, 2026-10-22). Ground gave each player flight a code
  (4101, 4102 ...) until then, on its taxi clearance, the ATC card and the Support page's
  FREQ / TOT line; the readback had to carry it. The mission sets no jet IFF code, so nothing
  else used it. A pilot who still reads one back is not corrected (the number is ignored
  when the runway is there).
- **Runway:** the one the briefing picks (`RunwayData.runway_name`) until the first AI
  airplane takes off within 5 NM of the field; its heading then sets the runway end ATC
  gives (the briefed strip's other end first, so 28L becomes 10R). DCS's AI does not always
  take the into-wind runway: on 2026-10-21 Tower cleared 28L and the AI used 10 at Hatzerim.
  Tacview of five Syria flights with light wind (2-4 m/s) showed the AI on each field's
  first-listed runway end (Hatzerim 10, Bassel Al-Assad 17, Incirlik 05, Konya 01) whatever
  the wind, but Tel Nof broke the pattern, so the rule is not settled and the planner is
  unchanged. In 7.7 m/s (Afghanistan) the AI went into the wind. Wind is read live at the
  field (magnetic, from MOOSE's declination table); the altimeter is the mission QNH.
- **No taxiway names.** DCS gives scripts none; the terrain's `AirfieldsTaxiways` files are an
  unlabeled road graph. Every field says "taxi, hold short runway 25" (user call,
  2026-10-20).

The calls are military ones (user call, 2026-10-26; sources: FAA JO 7110.65 ch. 3 s. 7, 9
and 10, AIM ch. 4 s. 3, AFI 11-2F-16V3). The lead calls for the flight going out; each ship
gets its own landing clearance unless the lead calls for the formation. Taxi is the first
call: there is no engine-start request, since SRS radios are dead until the jet is powered
(user call, 2026-10-21). A spoken start request gets "start at your discretion, call ready to
taxi" from whichever position was called. An "airborne" call is no longer needed, since the
takeoff clearance approves the frequency change, but it is still answered "frequency change
approved".

| Position | Pilot | ATC | Readback items |
|---|---|---|---|
| Ground | request taxi | runway 25, altimeter 29.92, taxi, hold short runway 25, contact Tower 262.0 | runway |
| Tower | holding short runway 25, ready | runway 25, wind 270 at 5, cleared for takeoff, frequency change approved | runway |
| Tower | 10 miles, full stop (or request the overhead) | runway 25, wind, report initial | none |
| Tower | 10 miles, request straight-in | runway 25, wind, make straight-in, report 3-mile final | none |
| Tower | initial / break | roger (initial with another player flight in the pattern: report break) | none |
| Tower | base, gear down (3 miles, gear down; on final, gear down) | runway 25, wind, cleared to land | runway |
| Tower | (lands) | clear the runway, taxi to parking | none |
| either | Mayday, emergency fuel (or engine failure, flameout, fire) | cleared to land any runway | none |
| either | request runway in use (active runway, say active) | runway 25, wind 270 at 5 | none |

- **Formation.** A lead with live wingmen, or a lead who says "flight" ("Viper 1-1 flight",
  "flight of two"), is answered "Viper 1-1 flight" on taxi and takeoff. On landing only a
  lead who says "flight" is; that clears every player ship in the group. "Flight of two" is a
  count, never a ship number.
- **Have the numbers.** A taxi call that says it leaves the altimeter out, and the takeoff
  clearance then leaves the wind out.
- **Pattern calls need no station.** "Viper 1-1, initial" and "Viper 1-1, base, gear down"
  are heard without "Tower", as real pilots make them.
- **A "gear down" call farther than 10 NM** (`LANDING_RANGE_NM`) is misheard and answered as
  an inbound call. The old 15 NM "report 5 miles" gate and the busy-runway "enter the pattern
  at 3,000, report downwind" are gone: inbound is no longer a clearance.
- **Readback numbers.** The wind, the altimeter (29.92 or 2992) and the Tower frequency are
  optional numbers: reading one back is never a wrong number under Relaxed. Before
  2026-10-26 a Relaxed readback that included one got "negative".

"Say again" repeats the last call; "radio check" answers 5 by 5. A call to the wrong position
gets "contact Ground/Tower <freq>". An unknown callsign gets "say again your callsign".
A whole callsign matches first, then a flight alone, then a ship, so a non-Western
"flight 1 2 3" is Flight 123-1 and never ship 3 of Flight 12 (pkgcontrol reads them the same
way). A ship number is the unit's seat in its group (`Unit.getNumber`), not its place among
the live units: a lone player in slot 2 is ship 2.

**Respawn.** A player born again in the same slot starts a new sortie: that seat's pending
readback and landing clearance clear, and when no other player is in the flight its state
goes back to parked with every scolding unspent (fixed 2026-10-21; a second sortie used to
get no bust calls and start mid-sequence).

**Radio discipline.** ATC reads the shared **Radio discipline** setting (§121, default
Strict) as `dcsRetribution.radioDiscipline` and passes it to SkyEye in the `atc` message.
It replaced Voice ATC's own "Strict readbacks" (2026-10-21; a save with that unticked
migrates to Relaxed).

| | Strict | Relaxed | Casual |
|---|---|---|---|
| Readback missing an item | "readback incomplete, hold short runway 25" | fine | fine |
| Readback with a wrong number | "readback incomplete, ..." | "negative, hold short runway 25" | fine |
| Rule busts | one scolding call each | none | none |
| Call to the wrong position | "contact Ground/Tower <freq>" | the same | answered where called |
| Unprompted "clear the runway" | yes | yes | no: ATC speaks only when called |
| Callsign | must match | a misheard one is matched: the right numbers, the only flight there with that name, or the only player flight using the field (since 2026-10-26, Test 65) | the same, or none |
| SkyEye parsing | station, callsign, request | the same | the station or callsign may be left out |

ATC stays silent on a good readback, as real controllers do. Under Casual you may taxi and
take off unannounced; Departure (step 2) will still pick you up.

**Rule busts** (Strict only) get one scolding call each and never block: rolling faster than
about 6 kt before a taxi clearance ("not cleared for taxi"), a takeoff without clearance, a
landing without clearance.

**F10 menu.** "ATC" per player group makes the same requests (user call, 2026-10-20). A menu
readback is always complete. A group menu cannot tell which ship pressed it, so the top items
speak for the one player aboard, else the lead, and each wingman seat has a "Ship N" submenu
with the same items (7 calls and 3 submenus fill F1-F10 on a 4-ship). Since 2026-10-26 the
inbound items are "Tower: 10 miles, full stop" and "Tower: base, gear down"; the overhead
request item went, since overhead is the default. Until 2026-10-21 every
menu call was ship 1. Without LuaSocket the menu is the only way in and the replies
are text only.

**Voice.** SkyEye hears the calls and speaks the replies over the §117 mission link: an `atc`
message lists each field's positions and frequencies and the player flight callsigns
(`callsigns`, which SkyEye puts in its speech recognizer's prompt); SkyEye parses every call heard on one
as an ATC call and sends an `atcRequest` (kind, callsign, numbers heard, text); the plugin
answers with `say` messages carrying separate `speech` ("runway two five") so Piper
does not read numbers as amounts. Ground and Tower each get their own voice from the blue
faction's accent, never one the AWACS, ABCCC or Vacuum uses. A spoken reply is never on-screen
text too (2026-10-24, user call); only without LuaSocket is a reply text to the flight.

Built 2026-10-20. Not flown (row B261).

**Phrasing (2026-10-21, user call).** With `BradySox/skyeye` PR #10 a readback parses with
the callsign first or last, or after the station ("Tower, Ford 9, cleared for takeoff 28L" is
a readback, not a new request), and a clearance word (runway, short, hold, taxi, squawk,
cleared, tower, ground, takeoff, contact, wind, altimeter) is never a callsign. "Two ship"
and distances ("30 miles") are not ship numbers. Outbound, departing, wheels up and switching
are airborne; final and visual approach are inbound; comm check and how do you read are
radio checks; repeat is say again; pan pan is an emergency. Under Strict a clearance whose
readback never came gets one "Ford niner one, read back" 20 s later
(`READBACK_PROMPT_SECONDS`), only while it is still the flight's current clearance; before,
an unheard readback was silence. The card teaches the after-landing call as "Tower, <me>,
clear of the runway", answered "Taxi to parking". Not flown (row B271).

**Military calls (2026-10-26, user call).** `BradySox/skyeye` PR (branch
`retlab/military-atc`) sends an inbound call's `detail`: `overhead`, `straight-in`,
`initial`, `break` ("brake" without "hot"), `geardown` (base, final, "gear's down"), and
`numbers` on a taxi or ready call that says "have the numbers". A pattern report parses
with no station. Two parser bugs went with it: "airborne, switching departure" was a takeoff
request ("departure" was a ready word), and "engine failure" without "mayday" was a start
request. From Test 65 (Relaxed): "clear for takeoff 23" (clear, not cleared, either order) is
a readback, and "request runway in use" is the new `runway` kind. The ATC card shows the new calls. Not flown (row B292).

### Files

- `game/retlab/voice_atc.py`: frequencies, the plan, `dcsRetribution.voiceAtc`.
- `resources/plugins/voiceatc/`: the state machine, the readback check, the read-back
  prompt, the F10 menu.
- `game/missiongenerator/kneeboard/voicepages.py`: `AtcPage`, one per player flight.
- `tests/retlab/test_voice_atc.py`, `tests/lua/test_voiceatc_runtime.py`,
  `tests/missiongenerator/test_voice_kneeboard_pages.py`.

### Constraints

- Needs the SkyEye copy with the `atc` message (`BradySox/skyeye` branch `retlab/voice-atc`).
  SkyEye replies to each mission script by what it announced, so `pkgcontrol` and
  `voiceatc` share the link.
- SkyEye finds the field by frequency, not by the spoken name, so a misheard field name
  still works.
- Callsigns are a name and two digits; a third digit spoken right after ("Viper 1-1, 5
  miles") is not read into the callsign.

## §118 — Vacuum ELINT

An **ELINT** flight type, callsign **Vacuum**, for the C-130J-30 and the KC-135 (and
KC-135 MPRS) in any era, standing in for an RC-135. With **Vacuum ELINT (SkyEye)** on
(RetLab Features page, off by default) the planner adds one to the land AWACS package on a
turn with at least one SEAD, SEAD Escort or DEAD flight (`plan_vacuum`, run after the
theater commander). A KC-135 is picked first and a C-130J-30 only when no KC-135 is
free (user call, 2026-10-20: the KC-135 is Vacuum, the C-130 the ABCCC). It can also be
fragged by hand.
It flies the AWACS plan one 20 NM slot behind the E-3 (`STATION_TASKS` in `aewc.py`), silent
and weapons-hold like the ABCCC (`configure_package_control`).

While a Vacuum is **alive and airborne** the `vacuum` plugin watches every red ground radar
within 250 NM of it (radar unit classes only; radar-laid guns are left out). A radar that
comes on is called once: "Vacuum, SA-6 awake, bullseye 304, 60, loose." It must stay off a
full minute before it counts as a new on-cycle, so a site Skynet blinks is one call.
Calls are spaced 8 s apart.

**Awake, asleep, tight, loose (2026-10-22, Brady's design).** Vacuum remembers every radar it
has located for the whole mission, even after it lands. "Awake" is on now; "asleep" is
located earlier and off now. Each fix has a real error, always off in the same direction for
a site (a hash of its names), so repeat calls agree:

- A first fix is off by 1 NM plus 1 NM per 10 NM from Vacuum, 15 NM at most.
- It closes to the radar's spot after 20 s heard in total up close, 90 s at 150 NM or more.
  Every 10 s poll a radar is on counts, across blinks: Skynet keeps radars dark most of the
  time, so minutes of steady listening would never come.
- Hearing it again from closer restarts a fix only when that is better. Asleep, a fix stays.
- **Tight** is within 1 NM, **loose** anything wider. A loose radar that goes tight while on
  is called once more, tight. Asleep radars are never called unprompted (Brady's pick).
- Sites blue already knows (`known_fix`, fog intact) start asleep: a fixed SAM site tight,
  any other known site loose at 10 NM. Unknown sites start unlocated.

- **Own frequency:** every call, on a UHF channel allocated per mission and listed on the
  kneeboard comms as "VACUUM (ELINT)".
- **STRIKE:** only for a radar whose threat ring touches a player package's route or
  target, worked out at generation. STRIKE exists only when an ABCCC flies.
- **Silent** with no Vacuum airborne. It never jams, lases or designates.

Fixed 2026-10-21: the plugin's LuaSocket path and JSON escapes had single backslashes, which
Lua 5.1 reads as the bare character, so `require("socket")` looked in ".LuaSocket?.lua" and a
label with a backslash or a control character broke the message. They are doubled, as in
`voiceatc`. The STRIKE flags were empty until the §117 package fix the same day.

Fixed 2026-10-21 (Test 63): a late-activated air-start Vacuum exists and reads `inAir` before
it activates, so it called radars 7 minutes before it was in the sky; it now needs
`isActive()` too. Every Kub site was called "SA-2": the label came from the longest-ranged
radar, the site's P-19 "(SA-2/3)". A site is now named by its fire-control radar first
(`site_radar`), and a shared "SA-2/3" search radar alone is "search radar".

**Voice.** SkyEye speaks the calls. The plugin sends a `tune` message (Vacuum's frequency)
and one `emitter` message per call (label, status, fix, lat/lon of the called spot,
frequencies) over the §117 mission link. A SkyEye without `status` (before
BradySox/skyeye#11) says the older "new emitter" call.
SkyEye works out the bullseye from its own picture and magnetic variation, so the bearing
matches its AWACS calls. Vacuum speaks in a voice from its squadron country's accent that
neither the AWACS nor the ABCCC uses (`pick_another_voice`). Its unprompted calls are voice
only.

**Commands (2026-10-21).** Players call Vacuum callsign first, on its frequency or on STRIKE,
and it answers on the frequency it was called on. The words are MUD, AWAKE, ASLEEP, TIGHT,
LOOSE, BLANK and SAY AGAIN; "picture" stays the AWACS's, and "repeat" is never used.
Answers name every located radar still standing, awake ones first; mud names awake ones only.

| Call | Answer |
|---|---|
| "Vacuum, Ford 9, checking in." | "Ford 9, Vacuum, two awake, one asleep, nearest SA-6 awake, bullseye 090/25, tight." The nearest awake radar, else the nearest asleep one. |
| "Vacuum, Ford 9, say emitters." | The 3 nearest located radars, awake first, magnetic bearing and NM from the caller: "SA-6 awake 270, 35, tight; SA-11 asleep 245, 50, loose." None: "blank." |
| "Vacuum, Ford 9, request target status." | Located radars within their threat ring or 15 NM of the package target: "target area, SA-6 awake, bullseye 095/22, loose." None: "target area blank." |
| "Vacuum, Ford 9, mud 270." | The awake radar nearest that bearing from the caller, within 15 degrees: "mud 270 is SA-6 awake, bullseye 090/25, tight." None: "no emitter 270." |
| "Vacuum, Ford 9, say again." | Its last answer to that seat, else its last call on that frequency. |

- **SkyEye** (BradySox/skyeye#9) parses the calls apart from GCI and package calls, with
  lead-ins ("say", "request", "give me") and a repeated callsign. On Vacuum's own frequency
  a call naming no one, or ANYFACE, is for Vacuum. Each goes to the plugin as an
  `elintRequest` (kind, callsign, bearing, frequency); the plugin answers with a `say` line.
- **The plugin** finds the caller among `vacuum.flights` (each player flight's lead seat and
  its package target) as voiceatc's `findFlight` does, and measures from that seat's jet.
  Magnetic bearings use MOOSE's `UTILS.GetMagneticDeclination`, else 0; the bullseye is
  `coalition.getMainRefPoint`. Answers use every radar it tracks, under Casual too, and are
  voice only: no on-screen text (2026-10-24, user call); a request only arrives over the link. No `world.searchObjects`: it reads only the tracked units.
- The `tune` message now carries Vacuum's callsign and own frequency. An older SkyEye ignores
  both and never sends a request, so nothing is answered and nothing breaks.
- **Kneeboard:** "Talking to Vacuum" (`VacuumPage`, `voicepages.py`), after the AWACS card,
  for every player flight when a Vacuum flies (user call, 2026-10-24; SEAD, SEAD Escort and
  DEAD only until then). It
  lists the five calls, each with its answer, and one line: a SAM keeping its radar off is
  invisible to Vacuum, and "blank" does not mean safe (user call, 2026-10-22: no radar
  table, no explanations).

Built 2026-10-20. Not flown (row B260). Commands not flown (row B269). Awake and asleep not
flown (row B272).

**Fixes carry over (2026-10-22, Brady's call).** The plugin writes `{unit, error}` for every
radar it heard to the `vacuum_fixes` global; the base plugin puts it in `state.json`
(`StateData.vacuum_fixes`). At debrief `reveal_vacuum_fixes` reveals each red site (§3) and keeps
its best fix error on `TheaterGroundObject.vacuum_fix_m` (old saves: None). The next Vacuum
starts that site asleep at that error (`known_fix` returns it, the emitter carries
`knownError`): tight if it was within 1 NM. A message names the newly found sites. Not flown
(row B273).

### Files

- `game/retlab/vacuum.py`: the planner rule, the radar labels, `dcsRetribution.vacuum`.
- `resources/plugins/vacuum/`: the watch, the answers and the SkyEye link.
- `game/missiongenerator/kneeboard/voicepages.py`: `VacuumPage`.
- `resources/units/aircraft/C-130J-30.yaml`, `KC-135.yaml`, `KC135MPRS.yaml`: `ELINT` task.
- `tests/retlab/test_vacuum.py`, `tests/lua/test_vacuum_runtime.py`,
  `tests/missiongenerator/test_voice_kneeboard_pages.py`.

### Constraints

- The labels come from the unit's display name: a NATO `SA-n`/`HQ-n` code, else the system
  name, cut at its first component word ("NASAMS SR MPQ64F1" is "NASAMS") with the `SAM`
  and `AShM` prefixes dropped. An early-warning radar is "early warning radar"; the P-19 and
  the Dog Ear (`MCC-SR Sborka`, a SHORAD command-post radar) are "search radar" (Test 64,
  2026-10-24). No vanilla radar is called by its DCS name; a mod radar with neither may be.
- Needs the SkyEye copy with `tune` and `emitter` messages (`BradySox/skyeye`); the
  commands need its `elintRequest` too.
- Vacuum knows only radars radiating now. Never report a dark site: the card tells pilots a
  dark SAM is invisible, and "blank" must stay "nothing on", not "safe".

## §116 — Voice AWACS on SRS

A setting on the RetLab Features page, **Voice AWACS on SRS (SkyEye)**, off by default, for a SkyEye
GCI bot (github.com/dharmab/skyeye) running on the player's SRS server. SkyEye reads the
picture from Tacview's real-time feed and talks on its own SRS frequency; RetLab only clears
the way. With the setting on:

- Blue AEW&C flights get DCS radio silence, so the DCS voice does not talk over SkyEye.
  They keep the AWACS task, their orbit and their datalink role. Red AWACS are untouched.
- The SkyEye frequency (**SkyEye frequency**, default `251.0 AM`) is reserved before any
  flight is given a channel. The AWACS keeps its own channel, picked the normal way or set on
  the flight in the flight editor.
- **Every voice bot's frequency is AI-free (2026-10-21).** Hand-set package and flight
  frequencies on both sides are reserved first (`reserve_ato_frequencies`), then Ground and
  Tower, STRIKE and Vacuum are picked clear of every frequency pydcs gives a new aircraft
  group (124.0, 127.5, 251.0, 305.0 ...; `dcs_default_group_frequencies`). Those are held
  only while the voice bots pick, so a carrier keeps its curated 305.0. After the air units
  are built, any AI group on SkyEye's, STRIKE's, Vacuum's or a Ground or Tower frequency
  moves to another (`_move_ai_off_voice_bots`), and a hand-set frequency on one moves in
  `setup_radios`, never the bot's.
- The kneeboard support page's AEW&C table and the briefing list **SkyEye callsign**
  (default `Chainsaw`) first as "Chainsaw (SkyEye)", and each blue AWACS as "(silent)".
- A blue AEW&C flight fragged that turn takes SkyEye's callsign for the turn (Chalice, Chainsaw
  or Image), so the F10 map, the kneeboard and the voice use one name (2026-10-21).
  A flight fragged before the setting was turned on keeps its callsign.
- **Each voice bot has its own SRS name (2026-10-22).** Every `say` from `voiceatc`,
  `pkgcontrol` and `vacuum` carries `speaker`: the station label ("Hatzerim Ground"), the
  ABCCC callsign, Vacuum's callsign. A SkyEye with BradySox/skyeye#14 opens one transmit-only
  SRS client per speaker ("Hatzerim Ground [BOT]") and renames its own to "<callsign> [BOT]";
  an older SkyEye ignores the field. Row B275.

Built 2026-10-20 after a flown SkyEye test (Afghanistan, F-4E): the bot answered once the
player named themselves in the call. Not flown with the setting on (row B257). The DTC
cartridges still preset the AWACS channel, not SkyEye's.

### Files

- `game/retlab/voiceawacs.py`: the frequency parse and the kneeboard/briefing line.
- `game/settings/fields/missiongenerator.py`, `game/settings/layout.py`: the three settings.
- `game/missiongenerator/aircraft/aircraftbehavior.py` (`configure_awacs`): the silence.
- `game/ato/flight.py` (`_skyeye_callsign`): the AEW&C callsign.
- `game/missiongenerator/missiongenerator.py`: the reservation and the "(silent)" label.
- `game/missiongenerator/kneeboard/support.py`, `resources/briefing/templates/*.j2`: the line.
- `tests/retlab/test_voice_awacs.py`.

### Constraints

- SkyEye's own config (`srs-frequencies`, `callsign`) must match the two settings; RetLab
  never writes it (Brady's call, 2026-10-20).
- Player calls must start with the SkyEye callsign, then the player's seat ("Ford 2-1"). The
  kneeboard tells players to start their DCS player name with it ("Ford 2-1 | Joe").

## §123 — Trains on drawn rail lines

A **Train** group drawn in a campaign `.miz` (Combined Joint Task Forces Blue, waypoints
"On Railroads") is a rail line between the two control points nearest its first and last
waypoints. Supply between those bases goes by train. Design and probe findings:
[retlab-trains-notes.md](design/retlab-trains-notes.md).

- **Rail wins over road.** `TransitNetworkBuilder` links a rail pair before roads, so the
  road between the same bases carries no convoy. A rail line through enemy sectors is cut
  like a road (`rail_is_cut`, §111). Rail counts as ground supply (§90 rung A).
- **A train is a convoy.** `Train` subclasses `Convoy` and lives in the convoy map
  (`ConvoyMap.add_train`), so BAI and Armed Recon targeting, the debrief, the base menu and
  the map treat it as one. The planner targets trains even with **Disable land convoys**
  ticked, and `TrainGenerator` spawns them whatever that setting says.
- **A dead train loses everything.** DCS sees the whole train as one unit and fires no dead
  event when it dies. `resources/plugins/base/train_losses.lua` polls each train's health
  and, at zero, reports one `<train> cargo #N` name per unit carried; `UnitMap.add_train`
  maps those names to the cargo, so the ordinary convoy-loss path kills it all.
- **Consist:** WWII dates get the DRG Class 86 and German wagons, Nevada the ES44AH,
  everything else the CHME3T. One wagon per unit carried, 4 to 20.
- **Authoring:** `python tools/supply_route_geo.py <campaign> --rail --draw <campaign>.miz`
  draws the campaign's `RAIL_LINES` entry, one real station per waypoint. DCS paths the
  track between them and snaps a waypoint within a few hundred feet onto the rails.
  Fulda Gap 1985 has four: Frankfurt-Fulda, Frankfurt-Fritzlar, Haina-Erfurt and
  Meiningen-Erfurt (Erfurt is Bindersleben). Wurzburg-Schweinfurt and Merseburg-Leipzig
  ran away from their stations in the probe and are not drawn.
- **Ambient supply (§50)** counts rail lines as corridors.

| Area | Path |
|---|---|
| Loader | `game/campaignloader/mizcampaignloader.py` (`rail_line_groups`, `add_rail_lines`) |
| Network | `game/theater/transitnetwork.py` (`TransitConnection.Rail`), `game/theater/sectorwar.py` (`rail_is_cut`) |
| Transport | `game/transfers.py` (`Train`, `ConvoyMap.add_train`) |
| Generator | `game/missiongenerator/traingenerator.py` |
| Lua | `resources/plugins/base/train_losses.lua` |
| Tests | `tests/retlab/test_trains.py`, `tests/lua/test_train_losses_runtime.py` |
| In-game pass | B285 |
