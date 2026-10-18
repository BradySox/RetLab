# RetLab In-Game Pass Checklist: archive

Rows that owe no flight: verified, retired, removed or closed. Moved here from
`retlab-ingame-pass-checklist.md` by `python tools/checklist_rows.py archive`, text
unchanged. A row that regresses is moved back by hand and re-marked.

## WORK ORDERS — 2026-08-05 DM review pass · ALL SIX CLOSED

> **Read this first.** These came out of a single review pass by the DM on 2026-08-05
> (session `units-runway-generation-bf755e`) and are recorded here — at the top of the file the
> session-start hook reads — specifically so a later agent does not lose them. Each has a
> matching row further down carrying the full detail; this is the index, not the record.
>
> **All six are closed as of 2026-08-25. Nothing here is owed.** Four were worked and closed in
> the days after the review; orders 5 and 6 closed on their own rows and this index never caught
> up — G31 was **retired 2026-08-07** when §21/§15 CSAR were deleted for upstream #929 (nothing
> the order describes still exists), and H11 was **verified 2026-08-17** on the DM's call. Keep
> the block for the history; **do not start work from it.** If the fuel-estimate over-read
> resurfaces it is a fresh report against H11, not this order.

| # | Order | Row | State | Blocking question |
|---|---|---|---|---|
| 1 | ~~**Strip the packaged-drone JTAC**~~ | G26 · G27 · G32 | ✅ **DONE 2026-08-05** — full rip. Both settings, `game/retlab/jtac_drone.py`, `_maybe_configure_jtac` + `_JTAC_PACKAGE_PRIMARIES`, the `configure_default_air_wing` hook, both COIN preseeds and both test files are gone; zero live references remain. JTAC is now upstream's, unmodified — **verified line-by-line against `upstream/dev`** (same gate / blue-only scope / `str(code)` / `Player.BLUE` / same `frontline_position`). New `tests/missiongenerator/test_front_line_jtac.py` covers the FAC, which had **no test of its own before this**. Gates: black + mypy + 3714 tests green. | Answered: full rip. |
| 2 | ~~**§72 carrier deck decor — position drift + a floating static**~~ | B25 | ✅ **CLOSED 2026-08-06 by non-reproduction** — WATCH item 4, DM verdict "Passing": gear on the deck, nothing floating, nothing out of place. No code changed; the diagnosis in the row stands as the record. **Caveat kept:** one session on an unrecorded hull/variant (6 rotate), and the ~10 m aft / ~5 m outboard `CORRAL_SHIFT` drift from raw campaign A is **accepted, not fixed** — do not re-seat on raw campaign A without re-validating `KNOWN_PARKING_SPOTS`. | Answered: it looks right now. If a float ever resurfaces, note WHICH hull + WHICH static. |
| 3 | ~~**G2 TARS BDA bridge rework**~~ | G2 · G19 | ✅ **DONE 2026-08-05** — rebuilt as ONE plugin (`recon`) covering player AND AI, replacing the `tars` + `airecon` pair. MOOSE `Ops.TARS` cut. Sensor/altitude/weather-shaped capture; cue held until landing. black + mypy + 3725 tests green. | Answered: the whole system, fresh. |
| 4 | ~~**I2 civilian air traffic rebuild**~~ | I2 | ✅ **DONE 2026-08-05** — both named issues fixed in Python; RAT stays retired. Region-appropriate fleets/operators/cruise levels (`civilianfleet.py`), single long airway transits instead of 5-leg milk runs, widened endpoint pool. Found + fixed in passing: **modern civil traffic was flying over 1944 Normandy and The Channel** — both now field nothing. black + mypy + 3737 tests green. | Answered: stay in Python. |
| 5 | ~~**G31 pilot recovery surge never appears.**~~ DM: "non existant as far as I can tell." | G31 | ✅ **CLOSED 2026-08-07 by removal** — the row is ⊘ RETIRED. The fork's §21/§15 CSAR was deleted and upstream dcs-retribution#929 adopted in its place, so `plan_pilot_recovery_surge`, its five gates and its tests are all gone. **The triage below was never needed and must not be started.** Upstream's CSAR carries its own rows (B71/B73/G33/G36/H14). | Moot — the feature it reported on no longer exists. |
| 6 | ~~**H11 fuel estimate over-reads.**~~ "Generating too much fuel for aircraft in cases" — flatters the jet, which is the dangerous direction. | H11 | ✅ **CLOSED 2026-08-17 — H11 is ☑ VERIFIED** on the DM's call, clearing the REGRESSED mark. Note the §46 tanker coupling named in the original order **no longer applies**: §46's planner half was reverted 2026-08-09, so the estimate is kneeboard-scoped only. | Answered on the row. A fresh over-read is a new report against H11, not this order. |

---

> **CSAR rows (added 2026-08-07).** The fork's own §21/§15 CSAR was deleted and upstream
> dcs-retribution#929 adopted in its place (merged as RetLab#805). The rows below are that
> feature's ENTIRE in-game coverage — it has ~139 passing unit tests and **zero flown
> observation**. The old §21 rows (G8–G13, G20–G23, G28, G29, G31, H3) were voided with the
> code they described.
>
> **Two shipped defects were already found and fixed while writing these rows** — both by
> reading, neither by flying, and both now guarded by tests: the survivor beacon transmitted
> `l10n/DEFAULT/beacon.ogg`, a file that **exists nowhere in the tree** and that nothing packed
> into the .miz (`tests/test_plugin_resource_files.py`); and the CSAR pickup waypoint briefed a
> 100 ft hover against MOOSE's 20 m winch ceiling, so a player flying the waypoint exactly could
> never hoist (`tests/missiongenerator/test_csar_hover_altitude.py`). Assume more of this class
> is present. A row that fails is doing its job.
>
> **Setup facts that apply to every row below.** `csar_ejection_chance` defaults to **40**, so
> most losses produce NO survivor — expect to lose 2–3 aircraft before one appears, and do not
> read "nothing happened" as a failure until you have. Set it to 100 while testing.
> `csar_hover_extraction` defaults **ON**, so the *landing* pickup path is NOT what ships by
> default — turn it off to exercise that half. **Dynamic-slot aircraft are untracked and their
> pilots can never go MIA**, so always eject from an ordinary ATO jet. The `opscsar` plugin is
> `defaultValue: true` with `skipUI: true`, so no campaign preseed is needed — but a stored
> `plugin.opscsar = false` in a personal settings blob would kill it with no UI to reveal it.

## Test 24 — what it reached, and what it could not (2026-08-29)

Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278, one client
Hornet. Nearly every RetLab feature was enabled, so the rows below are recorded as **not
exercised** rather than untested-because-nobody-looked — each names the reason, so nobody
re-runs the same campaign expecting a different answer.

| Row | Why test 24 could not answer it |
|---|---|
| B11 | `perf_ground_ai_sleep` off (the `aisleep` plugin was on; the setting is the gate) |
| B19 | Weather was "Summer, clean sky", 80 km visibility, no cloud or precipitation — nothing for the planner to react to |
| B23, S4 | The `rednet` and `commsjam` plugins were both off, whatever their settings said |
| B29 | `alternate_victory_attrition` and `alternate_victory_domination` both 0 — no alternate ending configured |
| B31, B52 | `GROWLER|: no growler node emitted -- plugin inert`; the campaign fields no EA-18G or EA-6B |
| B32 | Zero ship TGOs, so no cargo-ship convoy and no coastal battery |
| B45 | `gps_jamming` was on but no site exists in this campaign, so no `gpsJamming` node is emitted at all |
| B48 | Zero ship TGOs — see the row |
| B56, B60 | `living_battlespace_preroll` and `living_battlespace_reactive_red` both off |
| G30 | MANTIS armed the SHORAD link on 11 red point-defence groups, but of 8 HARM shots only 2 had any red SHORAD launch within 120 s, both at 34–36 km — too far to attribute to the HARM |
| H10 | One client flight, so no shared-airframe index to build |
| B107–B109 | The `.miz` was generated four seconds before #997 merged onto the branch |

**pydcs's parking data predates the 2026-08-26 rework on every map.** `airports.py` was last
regenerated 2026-06-16 for Syria, 2025-09-20 for Caucasus, and 2022 for Nevada. The rework's own
claim is that slot counts went **up** for large aircraft, so a stale count under-reports and costs
ramp rather than overflowing it — Mineralnye Vody reads 0 large-capable slots, which is why its
A-50 and IL-78M air-start. Re-exporting is a capacity question, not a correctness one; nothing in
test 24 shows a count that is too high.

**A gotcha for whoever parses the next ACMI.** Tacview's `Coalition` field is unreliable here —
a Russian T-90 records as `Coalition: Allies` with `Color: Red`. Use `Color`. Object positions are
also relative to `ReferenceLatitude=38 / ReferenceLongitude=36`, not absolute.

## Test 32 — what it reached, and what it could not (2026-09-15)

Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot (watched from the
spectator seat at acceleration), 2 h 14 min of sim in 46 wall-minutes, `Tacview-20260915-174631`,
DCS 2.9.29.27468, build `fd04b4a66` (the `.miz` was generated at 17:42; `main` took #1020 at
18:34). The fight: blue 13 air-to-air kills (10 AIM-54, one each AIM-7, AIM-9, AIM-120) plus 15
Shahed-136s and 3 SCUDs shot down, for no air-to-air losses; red SAMs killed 12 blue jets (11
SA-11, 1 SA-15), five of them one DEAD package that never fired — see G42. Rows moved: **B107
VERIFIED**, **B122 PARTIAL**; evidence added to B48, B70, B99, B97, G42, G30, B39, B111, B121,
B17, B32. One planner change came out of it: detectors before opportunistic SAMs in
`DegradeIads` (doctrine row 8, minimal shape); its flown pass is **B126**.

| Row | Why test 32 could not answer it |
|---|---|
| B120, G36, H14, B106, B117, B119 | No player slot, so nothing that needs a human happened |
| B121 | No AI flight crossed a neutral border in 2 h 14 min; the polygons were read out of the `.miz` and checked |
| G30 | Skynet paired one red point defence (POODLE) and no HARM was fired at its parent |
| B108, B103 | No front line on this map, so no TIC formation |
| B63 | 16 scenery objectives known, none struck |
| C9 | Only two flights recovered to CVN-71, 90 s apart |
| B111 | No Hornet striker; the measurement is recorded in the row |
| B32 | Three Silkworm groups stood; no blue ship came in range |

## Test 33 — what it reached, and what it could not (2026-09-15)

Syria — Operation Peace Spring turn 2, a multiplayer listen host with two humans in the
MAVERICK Viper strike package, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468,
build `611eedfcd`. The turn-3 save (`91526.retribution`) is the auto-planner's untouched frag
on the same build. The fight: blue 16 air-to-air kills for one F-15C lost to an R-73 and one
more Eagle down late; the players flattened all four Tabqa Dam objectives. Rows moved: **B63,
B113, B114 PARTIAL**; evidence on B70, B107, B122, B125, G42, B121, B108, B39, B48. Two
defects found and fixed the same day: a stale dynamic-spawn template link (B125) and a second
human in one group going unsampled by the recorder (B70, B113, B114). The turn-3 save also
re-ran the #1023 question: red fragged DEADs at two blue EWRs, but the old ordering gives the
identical frag on this save, so B126 stays untested.

| Row | Why test 33 could not answer it |
|---|---|
| B125 | Both humans took the fragged slots, so no dynamic jet was spawned |
| B120 | Nobody crossed a neutral border |
| B108 | No stuck-unit line; the log's bulk is DCS's own event echo, not a TIC retry |
| B63 cause 1 | Nobody quit and relaunched, so the snapshot warning had no reason to fire |
| B48 | Only the carrier group was inside the host's recording bubble |
| B126 | Both orderings frag the same targets on this save |

Also measured after the DM's verdicts on 2026-09-16: the escorts of the 1,200 km MAVERICK
package released at the split (B78) and then ran dry — the F-15C ejected at 0.04 fuel, the
Hornets diverted to a Lebanese field at 0.08, the Viper on tanks came home with 0.72. See B78.

### 2026-09-16 — test 34: Yankee Station turn 1 on the halved laydown

Caucasus, 1968 Yankee Station turn 1, 62 min, no player, `Tacview-20260916-204511`, DCS
2.9.29.27468. The DM's report was "Maykop is stuck": four groups there (two Phantom pairs,
four B-52s) activated between t=1334 and t=1733 and never moved. The read is under **L8**:
the Vietnam airbase harassment barrage lands on Maykop and Sochi-Adler and DCS holds every
fixed-wing launch there for the rest of the mission; the same signature is in tests 24, 31
and 33. Rows moved: **L8 REGRESSED**, notes on B96, B100 and G33 (all nine blue beacons on
260 kHz, in-mission ejections included).

| Row | Why test 34 could not answer it |
|---|---|
| B100 | Nothing at Maykop was a stand problem; the ramp was shelled |
| B11, B45 | Setting off / no GPS weapon released |

### 2026-09-16 — test 35: Long Road to H3 turn 1, flown while the DM was locked out

Syria, Long Road to H3 turn 1, 78 min, no player, `Tacview-20260916-215945`, DCS
2.9.29.27468, harassment still armed (four fields). The read is under **B100**: Al Qusayr
launched none of its seven groups and was not shelled; the timeline says eighteen hot jets
activating on one apron inside five minutes jammed it, with the garrison armor 300 m off the
runway as the unproven second candidate. Tabqa, which was shelled, launched five of seven,
which is the one mixed reading on the L8 evidence. Blue launched everything at Incirlik,
including four flights after t=1338, but only because the DM hand-moved Incirlik's EWR group
before flying: the campaign miz authors that marker 1,437 m down the runway axis and 266 m off
its centreline, on the south-west taxiway, and it was blocking taxi. That is the §1 collision
class on an upstream campaign, and it puts Al Qusayr's armor (293 m off its runway) in the same
band. Three blue in-mission ejections keyed 260 kHz (G33).

**Both fixes landed the same night.** The Incirlik EWR marker is deleted from the campaign
file on the DM's call (it was red's marker at a blue field, and blue's QRA detects on two other
FPS-117 sites, three ships and both Patriots); Al Qusayr's armor is moved 1,029 m off the
centreline (was 329) and Gaziantep's EWR 900 m off (was 38 m: that marker sat on the runway
itself, which the guard found). A New
Game guard (`game/theater/airfieldclearance.py`) logs `Airfield clearance:` for every ground
object inside a 300 m band along a runway (1.6 km each way) or within 80 m of a stand, warn only. Run on this
campaign it also names a Tunguska at Bassel Al-Assad (301 m), Aleppo (317 m) and Tabqa
(160 m) and Tabqa's armor (264 m); those fields launched in test 35, so the band's edge is a
watch, not a verdict. NEW game required for the marker moves.

| Row | Why test 35 could not answer it |
|---|---|
| B120, B121 | No player; no neutral-border event |
| B11, B45 | Setting off / no GPS weapon released |

### 2026-09-17 — test 36: Long Road to H3 turn 2, and the carrier that launched two flights

Syria, Long Road to H3 turn 2, 71 min, no player (the COUGAR SEAD Escort Viper slot went
unmanned), `Tacview-20260917-181958`, DCS 2.9.29.27468. Blue took Aleppo. Rows moved:
**B17 ✗ REGRESSED**. Evidence on B70, B85, B111, G42, S3.

**The headline, and it causes three of the four things the DM reported.** The auto-planner
fragged **50 aircraft in 24 groups onto CVN-71's deck**, all `TakeOffParkingHot`, activating
between t=2 s and t=1233 s. Counted off the ACMI object declarations: **17 of the 50 ever
existed**. The deck accepted spawns up to t=233 s (14 airframes placed) and from t=281 s
onward **every carrier group silently failed to spawn** — 14 whole groups, 33 aircraft, no
DCS log line, no crash, nothing in `state.json` but a record with two identical samples at
the boat's reference point and `alt = -1`. Of the 14 that were placed, **two groups launched**
(`CVN-71 BARCAP|2|43` at t=2 s, `Incirlik BARCAP|2|41` at t=103 s); the rest sat hot on the
deck at 22 m for the full 71 minutes, drifting 25 km with the ship.

This is the B17 fail signature written down in 2026-07-17 ("a boat carrying two air wings loses
its delayed packages to gridlock"), except this is an **upstream-authored campaign and the
planner's own frag**, not a merged-campaign quirk. The spawn path has no deck-capacity check:
`flightgroupspawner.py`'s `NoParkingSlotError` retry is gated on `isinstance(cp, Airfield)`, so
a carrier never reaches the runway-start or air-start fallback.

**The knock-on: five escorts ended the mission parked in red airspace.** An escort's `Escort`
task is a `ControlledTask` whose ONLY stop condition is the primary flight's
`split-<id>` user flag, set by a `DoScript` on the primary's SPLIT waypoint. When the primary
never flies, the flag never fires and the escort holds its ESCORT HOLD anchor until the mission
ends. Measured at t=4260 s, distance from the anchor / from home:

| Escort | at anchor | from home | primary |
|---|---|---|---|
| COUGAR Escort (F-16CM) | 3.1 km | 310 km | COUGAR BAI — on deck, never launched |
| PUMA Escort (F-16CM) | 1.5 km | 272 km | PUMA BAI — on deck, never launched |
| PUMA SEAD Escort (F-16CM) | 0.9 km | 273 km | PUMA BAI |
| HORNET Escort (F-15E) | 4.7 km | 168 km | HORNET DEAD — never spawned |
| SCORPION Escort (F-15E) | 4.7 km | 169 km | SCORPION BAI — never spawned |

The anchor itself is placed correctly (`get_initial_point`, 7–9 NM short of the target;
COUGAR's measured 16.2 km = 8.75 NM). The defect is that release has no fallback — not a
timeout, not a check that the escorted group is alive or airborne.

**Three more defects found in the same capture, none of them a checklist row:**

1. **§74's Viper cartridge overwrites the jet's bullseye.** `viper.py` sets
   `MAX_STEERPOINTS = 25` and puts the support anchors on 21–25. The F-16C EA guide p324–325:
   *"The steerpoint normally used for Bullseye is steerpoint 25 and is automatically configured
   as such when a mission is loaded."* The DM's DED photo shows STPT 25 at N37°39.652′
   E035°11.144′ = **x 295171, y −53681**, which is this mission's `AWACS WIZAR` anchor to the
   metre, while the kneeboard's bullseye reads Aleppo (36°10′50″N 37°13′28″E = x 125570,
   y 123132, matching the miz's own `coalition.blue.bullseye` at x 125576.86, y 123125.30).
   §95 is correct; the cartridge clobbers it. Fix is to cap at 24.
2. **§45's drawn support racetrack is narrower than the turn the aircraft flies.**
   `SUPPORT_ORBIT_RADIUS_M = 3704.0` is a fixed 2 NM half-width. Measured on-station points
   outside the drawn capsule: Texaco 8 (KC-135) 75 of 121, worst 14.0 km beyond the outline;
   Arco 9 83 of 122, worst 15.3 km; Wizard 5 (E-3A) 66 of 126, worst 10.1 km; Overlord 3
   (E-2C) worst 5.2 km; Dodge 2 (A-6E) worst 2.9 km. A 30°-bank turn at the KC-135's 411 kt
   orbit speed is ~7.9 km radius on its own. The box needs to be sized off the orbit speed.
3. **The REFUEL waypoint is not gated on needing fuel.** `_build_refuel` says so in its own
   comment. The B-1B flew its egress to x 286162, y −13261 — 66 km PAST Incirlik — arriving at
   t=4200 s with **fuel 0.894**, and its SPLIT waypoint had already set `SetUnlimitedFuel` true,
   so the leg cost it nothing to gain nothing and it was still out there at mission end. The
   `ControlledTask` on that waypoint is also a window, not a low-fuel trigger: it starts when
   every unit is **above** 0.20 and stops when every unit is above 0.50, so a flight below 0.20
   never refuels at all.

| Row | Why test 36 could not answer it |
|---|---|
| B120, B121, B125, B104, B110, B113, B114, B77, H10, H14–H16, G36, B106, B117, B119 | No human flew; the one client slot went unmanned |
| B11, B45 | Setting off / no GPS weapon released |
| B32, B39, B16 | `cruise_missiles_state` and `naval_magazines_state` both empty — no raid, no anti-ship release |
| L-rows, M6 | `Vietnam Ops plugin - no VietnamOps data; skipping` |
| P-rows | Not a COIN campaign |
| B126 | Blue's two DEAD packages never spawned, so the ordering was never exercised |

### 2026-09-16 — the line-by-line audit of every open row against tests 1–33

Every open row was read against the 33 captures on the desk (`dcs.log`, `.miz`, `state.json`,
Tacview where it exists), the seven saves on the machine, and the plugin sources. Verdicts are
under each row with a `2026-09-16, line-by-line audit` paragraph. What moved:

| Row | Verdict | Decided by |
|---|---|---|
| B79 | ☑ VERIFIED | 232 takeoff/landing points on six mizzes match the field elevation; only ramp-parked one-point groups read 0 |
| B99 | ☑ VERIFIED | `measure_tot_past_mission_window.py` on `91526` and `CSAR`: 59 packages, 0 late; tests 24/30/32 |
| B109 | ☑ VERIFIED | the launch error is absent from nine launches since test 25; the folder migrated on the DM's install |
| C9 | ☑ VERIFIED | DM call; no recurrence in 30 recordings |
| B15 | ☑ VERIFIED | Tomcat liveries in the miz: CAG bird once, line jets cycling (Iron Gate, test 24, Scenic Route) |
| B52 | ☑ VERIFIED | test 17's jammers on threat-gated strike packages; no both-flavour package on 16 mizzes |
| B31 | ☑ VERIFIED | 323 hold pulses and 14 spoofs logged across four missions; player F10 toggle unflown |
| G33 | ◐ PARTIAL | briefed survivors key 260 kHz; in-mission ejections take MOOSE's random channel |
| G42 | ◐ PARTIAL | LEOPARD fought through two HARM flights on test 32 |
| B104 | ◐ PARTIAL | test 33's cartridge carries the correct 48-row ATDT |
| B115 | ◐ PARTIAL | one L1 polyline of 12 points, single-front campaign |
| B111 | ◐ PARTIAL | the authored Hornet value reaches the jet; nothing else authored |
| B108 | ◐ PARTIAL | zero stuck retries in four post-fix missions |
| B121 | ◐ PARTIAL | no AI stray in three missions; batteries never moved |
| P7 | ◐ PARTIAL | Inherent Resolve played to turn 2 and a full turn captured with the COIN feed live |
| B124 | ✗ REGRESSED | reproduced headless: a hand-fragged DEAD opens on `Retribution BARCAP` when the date gate drops the DEAD preset |
| S5 | ✗ REGRESSED | three of fifteen columns parked for the whole mission (tests 17, 28, 31) |

Every other open row carries a paragraph saying what was checked and why the captures cannot
move it. Two plugins log nothing when they work (`gpsjamming` on a degraded weapon,
`neutralborder` on an AI stray by design), which is why B45 and B121 have no evidence either
way after 33 missions.

## Test 37 — what it reached, and what it could not (2026-09-21)

Syria — Long Road to H3 turn 1 of a new game (archive
`syria_the_long_road_to_h3_turn01_20260921-194101.miz`), 65 min, one human in the Pontiac 5
OCA/Runway Viper out of Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build
`5a11efa13` (main at #1038), TIC off, `profiler` on. Artifacts in `Desktop\New test\37`. The
mission: 870 units, 313 aircraft in the recording (99 blue, 200 red, 14 neutral civil), 656
weapons. Blue lost 15 aircraft in combat; red lost about 45. Removals at deck or field height
with no weapon near are landings, not losses. The human's package put 2 GBU-31 on Aleppo's
runway and came home with all four Vipers; the OCA/Aircraft Eagles alongside lost three of four
to MiG-25s and a Tunguska.

**Corrected 2026-09-22 on a second look.** The first write-up named the campaign Anatolian
Reach and the build `93c8128e8` (a branch commit made after the flight); matched weapons on
5-second samples, which put missile terminals up to 5 km from their targets; and credited the
SA-11's destruction to the wrong package. Weapon attributions below are from full-resolution
tracks.

Rows moved (evidence under each heading): **B131** ☐ → ☑ (the setup is exactly this turn);
**B76** ✗ → ◐ (one tanker per method, 31 km apart); **S5** ✗ → ◐ (all four columns drove
22–35 km); **B123** ☐ → ◐ (the Armed Recon package was shot down before its TOT by a
neighbouring SA-11, nothing fired); **B129**, **B130**, **B77**, **H14** ☐ → ◐ (one half
each); **B132** ☐ → ◐ (the profiler works; its stall log had a blind spot, fixed — see the
freeze note).

Evidence recorded without a status change: **B70/B113** (the recorder credited 22 min of AI
flying to the vacated human seat — fixed), **B97** (first attrition number for the §94
falsifier: 8 of 15 blue losses to SAMs, six of them to one SA-11 in 44 s), **B126** (the
package that died transited that SA-11 while it was live; the SEAD that killed it arrived
later and was not planned against it), **G30** and **G42** (four HARMs at the SA-11 fell
2.3 km short; its paired point defence fired nothing), **G33** (28 beacons keyed at
260000 Hz, needle still owed), **B39** (stagger released eight groups ~112 s apart;
`PENGUIN` logged a second `under attack` release after it was already free — cosmetic).

| Row | Why test 37 could not answer it |
|---|---|
| B108, B103 | TIC was off (left off after the freeze isolation flight) |
| B120 | Nobody crossed a neutral border; 8 zones drawn, 5 defended, no hail |
| G30 | Four HARMs went at MAVERICK, which has a paired point defence (0127: ZU-23 + Strela-1). The PD fired nothing — it has no radar SAM to answer a HARM with — and the HARMs fell 2.3 km short. Evidence under the heading; the row needs a radar-SHORAD pairing |
| G25 | Not the COIN campaign; the Armed Recon package flew 2 F-15E + escorts, no drone |
| H15 | Online, imagery present, no OFFLINE banner — the row's condition is the offline path |
| H16 | The packages map drew the coastline fallback, not `syria.gif`; extent Cyprus → H3 (~600 km). Whether the raster should have covered it needs the `coverage_for` check, not a verdict from the page |
| H10 | One client flight; no index drawn, correctly, but the 2+ case was not present |
| B111 | No Hornet in the package. Measurement: F-16C striker 485 kt / 18,600 ft, M-2000C escort 508 kt / 31,700 ft on join → ingress; separation 3.9 → 46.9 km by TOT — but the striker was the human, so the pace reading is his, not the planner's |
| B128, B85, B61 | No primary failed to fly; no unreachable TOT; no role mismatch |
| B125 | The human took the fragged slot; the template link was written (1 flagged) |
| B110, B104, B105, B115 | Not a SEAD jet; ROE tab, Apache TSD and the front-line shape are cockpit reads |
| B117, B119, B106, G36, B71, B73, B122 | No CSAR flight fragged; 28 survivors on the map for next turn |
| B6, B19, B20, B29, B54, B65, B66, B80, B94, B95, B112, B114, B124 | App-side or multi-turn; a flight does not reach them |
| B11, B45, B32, G41, G19, G40 | Setting off, no GPS weapon, no sea lane, no power-station strike, no TARPS |
| B100, B101, B102, B118, B96, B92 | Wrong campaign or airframe (no F-4E, no Super Hornet, not Iron Gate) |
| L5, L6, L9, L11, M6, O1, P1–P8 | Vietnam, COIN and map-tile rows; not this campaign |

Also seen: a neutral civil IL-76 (`CEDAR AIR 673`) crashed 66 s in, and DCS logged `Wujah Al
Hajar: No parking place for 'Yak-40'` — the civil-traffic spawner overfilled a small field;
MOOSE AIRBOSS logged `EventData.IniUnit=nil in event CRASH!` 96 times, once per crash event,
upstream's handler; the sim ran at 55–80 % real time for 28 min of the battle (the freeze
note has the numbers).

## Test 38 — what it reached, and what it could not (2026-09-22)

Syria — Long Road to H3 turn 2 (archive `syria_the_long_road_to_h3_turn02_20260922-195036.miz`), 37 min, one human in the SPARROW SEAD Viper lead out of Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048) pulled two minutes before generation, RetLab planner suite on, `profiler` on (t+900 s for 600 s). Artifacts in `Desktop\New test\38`. A card flight: LOCAL items 4 and 5, not a full sweep of the outstanding rows.

Rows moved: **B130** ◐ → ☑ (the DED read). New row **G43** (◐): a crashed aircraft stalled blue's Skynet for 31 minutes; fixed.

Evidence recorded without a status change: **B134** (the ATO read before flying: the deep half passes), **B77** (+12:53 against +12 briefed, as on test 37), **B132** (Lua cleared in the window; the slow stretch follows the human and does not lift on F10), **B70** (the vacated-seat fix holds), **B113** (flight time counted the ramp; fixed).

## Test 39 — what it reached, and what it could not (2026-09-23)

Afghanistan — Graveyard of Empires turn 1 (new game), 89 min of sim, one human (Flash) in the PIG Strike F-15E (Suite 4+) lead out of Kandahar, cold start, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069). The `.miz` was written at 19:14; #1070 (§69 SAM routing) merged at 19:48 and is not in it. TIC and the profiler were off. Artifacts in `Desktop\New test\39`; the turn-2 save is `asdasd.retribution` (20:29).

Objectives destroyed (`Objective destroyed` in `dcs.log`): the Herat Motor Pool's four buildings (MONKFISH's two F-14s, eight GBU-31s, t=2889–2912), the Malan Bridge (QUAGGA) and Gazar-gahe Sharif's four (HORNBILL). Hashemi Bridge, PIG's target, was never attacked — both PIG jets were down before the IP.

The fight: blue lost 36 aircraft — 26 to ground fire, 4 air-to-air, 6 crashes with no weapon near. Red lost 19 — 17 air-to-air, 2 Ka-52 crashes. One S-350, `0012 | PORCUPINE (SAM)`, killed 10 blue aircraft between t=2317 and t=2672. `PORCUPINE DEAD` killed its three radars with AGM-65G at t=2716–2761, 51–96 s before the DEAD's own TOT. Flash was one of the 10: a 9M96D launched at t=2512 hit him at t=2622, 56.5 NM from the site, on the NAV → INGRESS leg, 7 min before PIG's TOT. His wingman went down 50 s later. SABERTOOTH (Buk-M3), whose ring covers none of the targets, killed four F-15C escorts 40–47 km from the site — the B141 case, one build before its fix.

Rows moved: **G43** ◐ → ☑ (56 crash events, no Skynet error, the guard is in the flown file); **B76** ◐ → ☑ (the negative case: probe receivers, boom tankers only, one KC-135 on turn 1 and turn 2); **B128** ☐ → ◐ (PIG's and HORNBILL's strikers were shot down on ingress; their escorts turned home within 40 s and recovered at their own fields).

Evidence recorded without a status change: **G30** (the first HARM at a site paired with a HARM-capable Tor; the Tor had fired all eight rounds at aircraft before the HARM arrived), **B122** (18 of 18 ejections landed; each is exactly where the next turn puts its survivor), **B70** (kill totals match the recording on both sides), **B113**, **B114** (the second-campaign half, in the store), **B77** (the F-15E: first move +12:20, airborne +14:26, against +11:29 briefed), **B97** (attrition), **B129**, **B126**, **B141** (the pre-fix baseline), **S3**, **S5**, **G33**, **H14**, **H16**, **B138**, **G42**.

Found, not rows:

1. **The BLUF's air-threat line names aircraft red does not own.** Page 1 reads `Su-33 Flanker-D / J-11A Flanker-L CAP likely near the front`. `_brief_air_threats` (`game/missiongenerator/kneeboard/generator.py`) ranks the enemy faction's whole type list by BARCAP priority. Red's air wing here is Su-27 (6), MiG-29A (10) and JF-17 (4) — the types that actually flew. **Fixed the same day:** the line ranks the squadrons the enemy owns (`test_air_threat_line_names_only_squadrons_the_enemy_owns`).
2. **A survivor with no ejection record is placed near his package's target, not where his jet fell.** `missionresultsprocessor.py` rolls the survival chance and calls `csar.fallback_position_for(flight)`; its comment calls that "the only position we have for AI/simulated losses". A flown loss now has a §91 track. Nine of the 21 blue survivors in the turn-2 save took that path and sit 23–42 km from the nearest loss of their type. Turn 2 fragged a UH-60 CSAR at one of them (Andrew Clay, F-14, 41 km off). The §91 track alone would not cover it: only a group's lead and humans are recorded, and 15 of the 36 blue losses were wingmen with no record. **Fixed the same day:** `dcs_retribution.lua` writes `crash_positions` on `S_EVENT_CRASH`, and a survivor with no ejection is placed at his aircraft's crash point, else its last track sample, else the target as before. Unflown; row **B142**.
3. **§69 orders TOTs at the target; the S-350 reaches the strikes earlier.** PORCUPINE's TOT led the Herat strikes by 2–4 min. Eight blue flights were inside 60 NM of the S-350 between t=2449 and t=2599, before the DEAD's first radar kill at t=2716. Not a defect in §69 as written; a question for the DM.
4. Six blue aircraft crashed with no weapon within 1.5 km in their last 6 s, four of them into terrain at speed (HORNBILL Strike, QUAGGA Strike, BULLSHARK Strike #2, FALCON Escort #2). All are in `crash_events`. Two were strikers that had just delivered: QUAGGA's F-14 released four GBU-31s at t=2982 and hit terrain at t=3026, and its bombs dropped the Malan Bridge at t=3041 (4–11 m off); HORNBILL's surviving F-15E released two GBU-31(V)3Bs on Gazar-gahe Sharif at t=3031 and hit terrain at t=3065.
5. The civil-traffic spawner overfilled four fields (`No parking place` at Chaghcharan, Bamyan, Nimroz and one more), as at Wujah Al Hajar on test 37.

| Row | Why test 39 could not answer it |
|---|---|
| B108, B103 | TIC was off (`tic` is not in the `.miz`) |
| B132 | The profiler was off |
| B141 | The build is one merge before #1070; this flight is the baseline, recorded under the heading |
| B120, B121 | 8 border zones drawn, 7 defended; nobody crossed, no hail, no neutral unit fired |
| B125 | The human took the fragged slot; PIG Strike carried the template flag |
| B126 | The one DEAD was the reactive tier (the S-350 covering the Herat strikes); no opportunistic DEAD on turn 1 or turn 2 |
| S3 | The blue column was still 23.5 km from `Convoy ambush 1` at mission end |
| H16 | No Afghanistan raster ships, so the flat fill is correct |
| H10 | One client flight |
| B138 | No pinned numbers; the one F-14 squadron has a single livery, so there is no CAG bird to misapply |
| B19 | Clear sky, 7+ SM; nothing for the planner to react to |
| B61, B85, B111 | Not examined this pass |
| B11, B45, B32, B39, G41, G19, G40 | Setting off / GPS jamming inert (no site) / landlocked / no power station struck / no TARPS |
| B17, B100, B96, B101, B102, B118, B104, B105, B110, B115, B135, B136, B137 | Wrong campaign or airframe, or a cockpit read on a jet without a DTC |
| L-rows, M6, P-rows | Vietnam and COIN rows; `coin` is not in the `.miz` |
| B6, B20, B29, B54, B65, B66, B80, B92, B94, B95, B112, B124, B139, B140, O1 | App-side or multi-turn |

## Test 40 — what it reached, and what it could not (2026-09-23)

Afghanistan — Graveyard of Empires turn 2, 55 min, no player (spectator), `Tacview-20260923-212225`, DCS 2.9.29.27468. The `.miz` was written at 21:21 and carries #1073's `dcs_retribution.lua` (`crash_positions`). TIC and the profiler were off. Artifacts in `Desktop\New test\40`.

The sim ran 3,264 s of mission in 3,314 s of wall time (98.5 %) with nobody in a jet.

Objectives destroyed: five at the bridge target (`Tobj Bridge …`, t≈2743), by SARDINE Strike's second F-14B(U) with four GBU-31s. Its lead was lost to SLUG at t=2487.

The fight: blue lost 18 aircraft — 13 to SAMs, 4 air-to-air, 1 UH-60 with no weapon near. Red lost 13, all air-to-air. One SA-11, `0030 | SLUG (SAM)`, killed 8: the whole SARDINE TARCAP F-15C four-ship at t=1659–1670, SARDINE Strike's lead at t=2487, and three A-10Cs at t=2795–2835. SARDINE destroyed SLUG at t=2669–2979 (three HARMs, two GBU-38s, six AGM-65Ds and a GBU-38). `0040 | SABERTOOTH (SAM)` (Buk-M3) killed both FOB Delaram II BARCAP F-14s. `0029 | ARAPAIMA (PD)`'s Tor killed an F-16 and a Hornet, and ARAPAIMA's Kub a second Hornet.

Rows moved: **G30** ◐ → ☑ (a paired Tor killed seven HARMs aimed at its Kub parent); **B142** ☐ → ◐ (32 of 32 crashes recorded where the jets fell; placement needs turn 3); **I2** ☑ → ◐ (the departure stagger never worked; fixed, new row **B146**).

Evidence recorded without a status change: **B111** (no Hornet striker; the escort lagged, then caught up), **B70** (blue air kills in the sortie records: 12; in the recording: 13 — the FOB Delaram II F-14s show 3 of their 4 AIM-54 kills).

Found, not rows:

1. **A TARCAP reaches the target 17 minutes before its package.** **Fixed the same day** behind `tarcap_behind_sead` (DM call); row **B147**. `TarCapFlightPlan.patrol_start_time` is the package's `escort_start_time` (the JOIN TOT) minus 2 min, but the racetrack is on the target. SARDINE's racetrack end sat 5 NM from SLUG, the target of its own SEAD. The F-15Cs arrived at t≈1650; the SEAD sweep's TOT was t=2771. Upstream's rule, unchanged; `retlab-mission-planning-wiki-rework.md` already calls TARCAP a poor choice near SAMs. A DM call.
2. **FOB Delaram II's BARCAP orbits inside SABERTOOTH.** The racetrack end is 56 km from the Buk-M3; both F-14s died there (t=1615, 1806). On test 39 the same site killed four F-15C escorts. B141 routes package legs only, not CAP orbits.
3. **Red captured FOB Delaram II with one SA-19.** `unit|81|24|SA-19 Grison (2K22 Tunguska)|` sat inside the 3 km capture zone at t=1197–1640 with no blue ground unit there; `base_capture_events` carries `…||1||FOB Delaram II`. Its front-line attack leg (`flotgenerator.find_offensive_point`) passes 2.6 km from the FOB centre. Upstream's capture rule. Watch whether turn 3 flips the FOB.
4. **Every delayed civil departure left in the first 81 s** (seven, delays 10–6,129 s). DCS rewrites each group's `start_time` from its first waypoint's ETA when it loads a mission (`MissionEditor/modules/me_mission.lua`, `check_mission`); the spawner wrote only `start_time`. Test 37's `CEDAR AIR 673` (delay 1,605 s) left at once too, and crashed at 66 s. **Fixed the same day**; row **B146**.
5. **A civil IL-76 out of Bamyan flew into terrain at 88 s.** `ARIANA 131` left the ~2,590 m field, climbed ~10 m and hit the valley. Second civil IL-76 lost in the first 90 s (test 37). **Fixed the same day** (DM call): an IL-76 whose departure field is above 2,000 m air-starts en route instead (Ghazni, Sharana, Chaghcharan, Gardez, Bamyan on this map; Kabul and Bagram still ground-start). Rides row B146.
6. **OpsCSAR took the red Ka-52 flying CAS for a rescue helicopter.** It passed low near its downed wingman from turn 1: red smoke popped (t≈2101) and `still reports as present 420s` fired (t≈2527). `rescue_helo_near` matches any same-side helicopter under `PICKUP_MAX_AGL`. Cosmetic; no false rescue.
7. Both blue CSAR hoists completed (Curtis Thomas t≈2091, Andrew Clay t≈2181) and both are in `csar_rescued`. Thomas's UH-60 crashed at t=3068 on the way home, no weapon near; the rescue had already been credited.

| Row | Why test 40 could not answer it |
|---|---|
| B77, B135, B136, B143, B144, B125 | No player |
| B108, B132 | TIC and the profiler were off |
| B141 | No package leg needed a detour: SARDINE's JOIN → INGRESS passed 87 km from SABERTOOTH, and SLUG was its own target |
| B128 | Every primary flew |
| B6, B20, B29, B54, B65, B66, B80, B139, B140 | App-side or multi-turn |

## Test 47 — what it reached, and what it could not (2026-09-29)

Persian Gulf turn 1, 59 min, Flash leading `MOLLY SEAD Escort` (4 F-16C from Al Minhad) for three F-15Es striking `0104 | MOLLY (Command Center)`. `Tacview-20260928-205338`, DCS 2.9.29.27468. Red flew vanilla Iranian kit (F-14A, Mirage F1EQ, SA-5, SA-11, SA-6, Tor); no `[IRAD]` unit spawned.

The uploaded `.miz` is a regeneration of the same turn, written about 4 min after the flown one loaded: same plan, but callsigns, radios and carrier TACANs differ from the briefing in the Tacview. Readings taken from the `.miz` are the plan, not the flown file.

The build carries the tanker box (#1091, #1093) but not #1094, #1095 or #1097: the briefing picture is upstream's `splash_screen.png`, and the F-16 cartridge draws the tanker box the pre-#1097 way.

The sim ran 3,546 s of mission in 3,604 s of wall time (98.4 %). No Lua error in `dcs.log`.

The fight: blue lost 4 aircraft, red 3.
- Flash's three wingmen left him after the merge at t≈2700 on his "Engage bandits" call and flew 70 NM west after the only bandits they saw, over `0019 | MONKEY (SAM)` (SA-11). Two died to its 9M38s (t=3173, t=3236), the third to a Mirage F1's Super 530F (t=3319). The planned route never came within 26 NM of MONKEY.
- `MOLLY Escort` lost a Hornet to an F-14's AIM-9P (t=2854).
- Flash killed an F-14 with an AIM-120 (t=2782). A wingman's AIM-120 killed a Mirage (t=3234). A Hornet's AIM-9X killed the other F-14 (t≈2868; the crew ejected).
- Flash's GBU-31 landed 30 m from MOOSE's track radar (t=3456); its two S-200 track radars, its P-19 and two trucks died over the next 41 s.
- Blue's Patriots shot down all six Scuds red fired. PORPOISE used six MIM-104 (t=424–453) against BARRACUDA's volley at Khasab; WEEVIL used three (t=897–903) against RATTLESNAKE's at Al Minhad. The Scuds died at 5.3–16.1 km altitude.

Rows moved: **B153** ☐ → ◐ (both tankers flew the box and looped; the cockpit box is the pre-#1097 fail signature); **B146** ☐ → ◐ (the civil ground departures were staggered; the flown `.miz` is gone, so the ETAs cannot be matched).

Evidence recorded without a status change: **B142** (7 crashes, 7 `crash_positions`, 3 ejections), **B70** (red air kills 2 in the records and 2 in the recording; blue 2 against 3, the missing one a wingman with no record), **G43** (7 crashes, no Skynet error), **A-rows** (the Kish and Kerman alert four-ships scrambled at t=2230 and t=2620; all eight survived).

Found, not rows:

1. **A carrier's TACAN changed on every generation.** Flown: CVN-71 69X, Tarawa 40X. Regenerated 4 min later: 72X and 41X. `initialize_tacan_registry` reserved every control point's stored channel before generation, carriers included. A carrier's auto channel is then re-derived, finds its own last value taken, and walks to the other side of the curated one. On Persian Gulf 71X is a map beacon, so CVN-71 alternated 72X/69X and Tarawa 41X/40X. **Fixed the same day**: a carrier's auto channel is no longer reserved (`keeps_stored_tacan`); a channel chosen in the base dialog still is. Row **B156**.
2. **The MOLLY command center did not die.** One GBU-31(V)3B landed 11 m from `0594 | Command Center` (t=3289) and four more 42–56 m from it. `state.json` has no death for it; one ATZ-5 beside it died. The other seven F-15E JDAMs fell 0.35–2.55 km off, several near MOOSE. Check the turn-2 map: if it still stands, one 2,000 lb bomb at 11 m does not kill this static, which matters for §52 (row B6).
3. The F-16 cartridge carries one tanker box, the KC-135's. By design: `usable_tanker_tracks` drops the probe-only A-6E for a boom jet.
4. Three `dcs.log` lines added to `retlab-dcs-log-noise-notes.md`: AIRBOSS `EventData.IniUnit=nil in event CRASH`, `water_relocate: no land within 2000m for CSAR_PILOT_*`, and `SplashDamage: <weapon> missing from script`. None is a fault.
5. **No carrier or LHA joined Skynet.** `dcs.log` (also tests 43 and 46): `you have added an EW
   Radar that does not exist ... 0798 | CVN-71 Theodore Roosevelt`, and the same for the LHA.
   §65 spawns the flagship under its hull name; the IADS data sent the id-prefixed one.
   **Fixed the same day.** Row **B157**.
6. **The SA-5s held fire.** `0101 | MOOSE (SAM)` sat 1 km from the package target. Eleven blue
   jets were 9-60 km from it at 17,500-19,000 ft for about six minutes (t≈3110-3456), inside
   the 5V28's 17-240 km and 300-40,000 m envelope. It fired nothing; the Tor and SA-6 800 m
   away fired 12 missiles. `0099 | ADDER (SAM)` fired one 5V28 (t=3172) that died after 14 s
   with no blue aircraft within 120 km. Across the 11 kept Tacviews with an SA-5 on the map,
   5 missiles in total. Not explained offline: Skynet runs the SA-5 as SAM-as-EWR, which
   keeps it emitting and weapons-free; the launcher reports its missile to `getAmmo`; no
   RetLab plugin holds it. Next: one flight with the Skynet plugin's debug option on for
   red, which logs each site's ACTIVE and HAS AMMO state every cycle.

| Row | Why test 47 could not answer it |
|---|---|
| B154, B155 | Not in the build (#1094 and #1095 merged after this mission was generated) |
| B148, B149 | Red had no `[IRAD]` unit and no Iranian missile mod site |
| B152 | Neither tanker had a set orbit speed |
| B17 | Ten carrier aircraft; nothing near the deck limit |
| B141, B147 | No detour was needed and there was no TARCAP |
| B6, B20, B29, B65, B66, B139, B140 | App-side or multi-turn |

## Settled rows

### A1 — QRA air-spawn profile · §1 · ☑ VERIFIED

**History:** 2026-06-24, Tacview
- **Verified (2026-06-24, GermanyCW Red Tide turn 1, Tacview):** the red `Intercept`
  reserve scrambled in two waves and each MiG-29A pair air-spawned at ~750 m AGL and
  240–510 kt, climbing/cruising under control — no stall, no ground-clawing dive. The
  fail signature did not occur. (Note: the current `AI_A2A_DISPATCHER` QRA **air-spawns**
  at altitude rather than ground-scrambling, so the old `SCRAMBLE_SPEED_KT`/`SCRAMBLE_AGL_M`
  ground path is effectively superseded.)
- **Pass:** Scrambled jets spawn at a sane speed and a terrain-relative LOW
  altitude, then climb/turn to intercept under control.
- **Fail signature:** Jets air-spawn stalled (~0 kt) and dive clawing for
  airspeed (the Su-27-nearly-hit-the-ground-at-Vaziani case, Tacview
  2026-06-20). Check `SCRAMBLE_SPEED_KT` / `SCRAMBLE_AGL_M` in
  `intercept-config.lua` if seen.

### A2 — QRA base-defense doctrine · §1 · ☑ VERIFIED

**History:** 2026-06-24
- **Setup:** Default doctrine (QRA scramble radius 60 NM, engagement range 38 NM; constants since 2026-09-23).
- **Pass:** QRA scrambles only when a raid closes within ~60 NM and interceptors
  don't chase far past the FLOT — they screen their own base, not the front line.
- **Fail signature:** QRA pushing forward over the FLOT (the pre-tuning
  behavior that prompted lowering the radii).

### A3 — Player-manned QRA alert flight · §1 · ☑ VERIFIED

**History:** 2026-07-01, user pass — "A3 good"
- **Verified (2026-07-01, user in-app/in-game pass):** the player-manned QRA alert flight generated and
  behaved per the pass criteria — no double-spawn, no depleted-pool error, the alert flight held over its
  own field. Fail signature did not occur.
- **Setup:** A BARCAP-capable, player-flyable squadron at an airfield; set its
  "…of which player-manned" spinbox (under QRA reserve) ≥ 1. Take the turn and generate.
- **Pass:** A cold-start BARCAP package named "QRA Alert (<squadron>)" appears in the player
  ATO, parked on the alert pad, flyable, orbiting **over its own field** (not pushed forward);
  the AI QRA dispatcher for that base fields the reserve **minus** the manned airframes (no
  duplicate jet both parked-as-player and air-spawned). Losses reconcile correctly at debrief.
- **Fail signature:** the alert flight's racetrack pushed forward toward the FLOT; the same
  airframe both manned and air-spawned by the dispatcher (double-spawn); a depleted-pool error
  on generation; or the AI dispatcher count not dropping when the player mans some.

### A4 — Player QRA scramble cue · §1 · ☑ VERIFIED

**History:** 2026-07-01, user pass — "A4 good"
- **Verified (2026-07-01, user in-game pass):** the scramble cue fired as designed — no missing message,
  no spam, sane BRA. Fail signature did not occur.
- **Setup:** A player-manned QRA base (A3 setup); fly/trigger an enemy air raid toward it.
- **Pass:** as a bandit closes inside the cue radius (the AI GCI radius + ~30 NM lead, so it
  fires *before* the AI would scramble), a coalition text "QRA SCRAMBLE — <base>: bandits
  <brg> for <rng> nm, angels <N>" appears; the call repeats no more often than ~2 min; the
  bearing/range/altitude roughly match the inbound contact. It never auto-launches the player.
- **Fail signature:** no message (PLAYER_ALERT records absent, or `coalition.getGroups`/
  `AIRBASE:FindByName` wrong); message spam (debounce broken); wildly wrong BRA (north/east
  axis or `atan2` argument order wrong); a Lua error in `dcs.log` from the scan.

### A5 — QRA forward defense (rear bases answer the front) · §1 · ☑ VERIFIED

**History:** **call made 2026-08-07**, on the DM's instruction to resolve this row after it aged out unassigned. Verdict: **the 2026-07-11 fly is sufficient**, because the one thing it did not demonstrate is not a threshold. **The fail signature WAS watched for and did not occur** — the feature armed, closest-first launch order held, and a rear Su-27 transited front-ward with zero fail signatures. The row was held at PARTIAL only because the *marquee* full-length 147 NM transit wasn't seen end-to-end, i.e. on distance alone. **Distance is not a special case, and the code proves it:** `interceptluadata.py` computes `disengage_nm = max(gci_max_radius_nm, QRA_FORWARD_REACH_NM) + engagement_range_nm + DISENGAGE_MARGIN_NM` — the Moose disengage leash is **derived from** the scramble reach with positive margin, never set independently. The documented failure mode (Moose aborts a defender once `DistanceFromHomeBase > DisengageRadius`, default ~162 NM) is therefore **structurally unreachable**: a defender cannot be leashed short of the radius it was launched to cover, at 147 NM or any other distance. A 147 NM transit differs from the observed one in magnitude, not in mechanism. **The one residual, stated honestly:** Moose may still RTB a defender on **fuel** during a genuinely long transit — that is a *degradation*, not the defect this row tracks, it is not governed by the leash math, and it self-reports the same way (rear fields visibly fail to help). **Deliberately NOT invented: a new "SHIPPED UNVERIFIED (accepted)" marker.** The verification-cadence note proposes that state but leaves *whether it should exist at all* as an open squadron call, so resolving it here to file one row would have settled a design question sideways. This is marked with the existing vocabulary and its scope stated in full instead — overrule it in one word if the fuel residual is worth its own row) (was ◐ PARTIAL — 2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`, Tacview `Tacview-20260711-171935`: armed cleanly, closest-first launch order held, one rear Su-27 transited front-ward, zero fail signatures — but the marquee full-length 147 NM rear→front transit wasn't demonstrated end-to-end
The emitter geometry, the reach/disengage arithmetic, the ambush-wins rule and the narrow player cue
are unit-tested (`tests/missiongenerator/test_qra_defense_zones.py`,
`tests/missiongenerator/test_interceptluadata.py`, `tests/test_vietnam_doctrine.py`), and the plugin
parses on Lua 5.1. What no test can cover: whether Moose's accept-zone filter actually *releases* an
already-engaged defender when its target leaves the zone, and whether a 150 NM transit really flies.
- **2026-07-17 night fly (Scenic Route Merged, session `tacview-test-analysis-5bb161`),
  consistent-with:** Bandar Abbas QRA F-5Es launched against the QUAIL Armed Recon raid working
  Bandar-e-Jask (~118 NM from BA) — the rear-base-answers-a-forward-CP shape under the opened
  reach + accept zones (see the A7 bullet for the same event). The transit never completed (all
  4 F-5s died to Phoenix en route), so the full-length demonstration is still owed.
- **2026-07-11 flown evidence (Red Tide M1 "with Mags happy", ~125-min MP, 12 player flights):** load
  line present — `Intercept: RED defends 9 zone(s); scramble radius 200 NM` (9 = red's non-neutral CP
  count on this save). **Closest-first held:** the front base answered first — Haina's own QRA (4×
  MiG-23MLD, t≈1240–1360) flew 43–66 km W/SW into the blue push and all four died fighting over the
  front. **Rear launch observed:** Sperenberg (147 NM back, ~30 km S of Berlin) scrambled 3 Su-27s at
  t≈5110–5200; #003 transited **52 NM out on bearing 246°** — near-exactly the bearing to the Fulda
  front (237°) — and was killed en route ~45 NM from base; #001/#002 stayed local (~8 NM, base
  defense). Fail signatures (a)–(e): **none occurred** — no turn-around-at-~162-NM, no chase deep
  into blue, not every base launched at once, no `SetBorderZone`/`ZONE_RADIUS` Lua error. **Still
  owed for VERIFIED:** an observed full-length rear→front transit (the one front-ward Su-27 died a
  third of the way there), the accept-zone *release* of an engaged defender, and the Vietnam
  ambush-leash regression check below.
- **Setup:** Red Tide, `qra_forward_defense` ON (default), red QRA reserve ≥ 2/squadron. Fly a blue
  package to the Fulda/Haina front. Confirm at load: `dcs.log` has
  `DCSRetribution|Intercept: RED defends N zone(s); scramble radius 200 NM` (N = red's non-neutral
  CP count; 9 on the flown M1 save).
- **Pass:** red interceptors launch from **rear** fields (Sperenberg / Schonefeld / Wittstock /
  Hamburg / Templin — 127–168 NM back) and transit to fight over Haina, *after* Haina's own MiG-23s
  answer first. Peenemunde (226 NM) and Kastrup (290 NM) never launch for this raid. Then egress
  west: red **breaks off** rather than following you to Frankfurt/Hahn/Ramstein (outside red's zones).
  Fulda (42 NM from Haina) is inside red's airspace, so a fight there is expected and correct.
- **Fail signature:** *(a)* rear fields launch and then turn around ~162 NM out ⇒
  `SetDisengageRadius` not applied (check `disengageRadiusNm` on the Intercept records); *(b)* red
  chases deep into blue ⇒ `SetBorderZone` never called (no "defends N zone(s)" log line) or the
  Vec2 axes are swapped in `defense_zones_for`; *(c)* red QRA never launches at all ⇒ zones too
  small / wrong coalition bucket, i.e. the accept-zone filter is eating its own airspace; *(d)*
  every base launches at once ⇒ Moose is not picking the closest squadron (would contradict the
  read of its GCI loop); *(e)* a `ZONE_RADIUS`/`SetBorderZone` Lua error in `dcs.log`.
- **Vietnam regression check:** on 1968 Yankee Station, red MiGs must still scramble **late** (40 NM)
  and break off at 50 NM from home — the ambush leash must not have been widened.
- **2026-07-16 detection-escape addendum (fold into this fly):** the PR #782 drift port escaped the
  Lua-pattern magic chars in the EWR detection prefixes (`intercept-config.lua`
  `lua_pattern_escape`) — before it, every parenthesized IADS group name ("0041 | LION (EWR)")
  failed Moose's `FilterPrefixes` pattern match, so QRA detection rode the paren-free
  `QRA_Backstop_*` base EWRs ONLY. All prior A1–A5 evidence was flown on backstop-only detection.
  When flying A5, also confirm the wide-area net: approach from a direction only a *forward EWR
  site* covers and confirm the rear fields still see it. Fail signature: detection behaves
  exactly base-local (scrambles only once a raid is nearly on top of an alert field) despite an
  alive forward EWR network, or `dcs.log` shows an empty detection set for a coalition with live
  `(EWR)` groups.
- **2026-08-06 backstop-removal addendum (fold into this fly, and it RAISES A5's stakes):** the
  per-base backstop EWR is **gone** — it was a real vehicle at the airbase reference point +
  300 m NE, and DCS has no non-colliding ground unit, so a 55G6 mast stood in the taxiway network
  and broke AI taxi routing (flown Red Tide at Sperenberg; upstream PR #782 removed it for the
  same reason). **Detection is now the IADS EWR/SAM-as-EWR network alone**, which means the
  escape addendum above is no longer a nice-to-have — if it ever regresses, QRA detection is
  *empty*, not merely base-local. Two things to confirm on this fly:
  *(1)* **No object stands on any alert base's ramp/taxiways.** Walk (or F10) an alert field at
  mission start — Sperenberg is the known-bad case — and confirm AI flights taxi out without
  stopping, weaving around an obstacle, or piling up. Fail signature: an EWR/radar model sitting
  ~420 m NE of the airfield reference point, or AI holding on a taxiway for no visible reason.
  *(2)* **QRA still scrambles with the backstop gone.** Any alert base whose coalition has a live
  EWR/SAM network must still launch. Fail signature: `dcs.log` shows
  `"no detection sources for <coalition>; QRA will not scramble"` on a side that visibly has live
  `(EWR)` / SAM groups — that is a broken IADS publish, not the intended no-radar case.
  **Deliberately not a bug:** a side with its radar network genuinely wiped out no longer
  scrambles at all. That is the accepted trade (no radar, no GCI), upstream's behaviour too.

### A6 — Escort pre-join ROE: ReturnFire at spawn, OpenFire at JOIN · §8 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "A6 is good") (was ☐ UNTESTED, built 2026-07-12 from the flown Red Tide M1 finding — the user-observed "locked until the package forms at join" behavior, code-confirmed: escorts spawned OptROE=OpenFire(2) = "engage ONLY designated targets" with their one designating task attaching at JOIN, so the whole hold/transit window had an EMPTY legal-target set — mechanically unable to return fire (TOAD Escort's MiG-29s died at t=2056/2078 with JOIN ETA 2055, merged at gun range, silent; SCARAB Escort fired post-join only). The spawn ROE for both escort types, the JOIN OptROE(OpenFire) escalation, and the non-escort no-op are unit-tested in `tests/missiongenerator/test_escort_prejoin_roe.py` — whether the DCS AI actually returns fire pre-join and escorts identically post-join is DCS-only
- **What CI cannot exercise:** whether a pre-join escort under attack now actually returns fire (vs the old evade-only death), whether ReturnFire keeps it on its hold/join timeline (never freelancing at detected contacts), and whether post-join escort behavior is genuinely unchanged (engages fighters threatening the escorted flight at the doctrine range).
- **Setup:** any campaign with escorted packages on both sides (Red Tide M1 regenerated works). Watch (or Tacview) an enemy escort flight that gets engaged during its hold/transit-to-join phase, and another after join.
- **Pass:** an escort attacked pre-join defends itself with weapons (returns fire at its attacker) instead of evading silently to death; it does NOT chase targets that haven't engaged it; after JOIN it escorts exactly as before (commits on fighters near the escorted flight); the miz shows ReturnFire at waypoint 0 and an OpenFire option at JOIN for ESCORT/SEAD_ESCORT.
- **Fail signature:** a pre-join escort still dying without firing under direct gun/missile attack (ReturnFire not honored — would point back at the DCS-side employment issue, see the repro miz); an escort abandoning its hold to chase a detected contact pre-join (ReturnFire semantics drifted); post-join escorts NOT engaging (the JOIN OptROE order vs the ControlledTask broke); the same silent-death on an On-station BARCAP is NOT this row — that's the DCS R-27 employment issue (repro miz in `missions/red-tide/`).

### A7 — QRA react-task filter (AI QRA ignores sweeps/BARCAP/DEAD/Air Assault) · §1 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "A7 good") (was ◐ PARTIAL, 2026-07-17 night fly: behavior consistent with the filter — red QRA sat through 20+ min of blue fighter presence and scrambled only once A/G packages pushed; not conclusive on intent
- **2026-07-17 night fly (Scenic Route Merged turn 1, Tacview `Tacview-20260717-214932`, session
  `tacview-test-analysis-5bb161`), consistent-with evidence:** blue F-14B BARCAPs held near the
  strait from ~t=600 with **no red scramble**; the Bandar Abbas QRA F-5Es ("Intercept|Bandar Abbas
  Intl|…") launched only ~t=1450+, when the QUAIL Armed Recon/SEAD packages were working the
  Jask-area targets (Armed Recon IS in the react list; DEAD flights were also up but excluded
  types can't disprove — an included type was present). Also consistent with **A5**: Bandar Abbas
  answering a raid at Bandar-e-Jask (~118 NM away) is the rear-base-answers-forward shape under
  the opened reach + accept zones. The scrambled F-5s died 4-for-4 to a Khasab-BARCAP F-14B's
  AIM-54Cs before reaching the raid. Still owed for a clean pass: a *pure* fighter push pressed
  close against an alert base with zero A/G packages in the zone.
- **What CI cannot exercise:** whether the wrapped evaluators are actually what Moose's GCI loop
  calls at runtime (a Moose refactor renaming them would silently restore scramble-at-everything),
  and that a cluster's Set membership at evaluation time reflects the raid composition.
- **Setup:** any campaign with QRA reserves on both sides (Red Tide works). Fly (or watch) a pure
  blue fighter sweep/BARCAP push toward a red alert base, then a strike package on the same axis.
- **Pass:** the AI QRA sits through the pure fighter sweep (no scramble however close it presses),
  scrambles when the strike/BAI/OCA package closes, and still scrambles against an ESCORTED strike
  (any react-type member triggers the cluster). The player-manned scramble cue (A4) still fires for
  the sweep — it is deliberately task-blind.
- **Fail signature:** red QRA launching against a pure fighter sweep (the filter never engaged —
  check the group-name parse against the namegen convention and that the Evaluate wrap survived a
  Moose update); or QRA never launching against a clean strike package (over-filtering: the task
  suffix match broke, e.g. a namegen format change).

### B1 — Forward-CAP / FLOT depth on coastal fronts · §6 · ☑ VERIFIED

**History:** 2026-06-25
- **Verified (2026-06-25, in-game):** deep ground roles spawned at depth and spread on a
  coastal/narrow-land front — the perpendicular-walk-into-water stacking fail signature did
  not occur.
- **Setup:** A campaign on a **coastline / river / narrow-land** front.
- **Pass:** Deep ground roles (artillery, logistics) spawn at depth and spread,
  not in direct contact.
- **Fail signature:** Deep groups stacked in contact at depth 0 because the
  perpendicular walk hit water/off-map (the bug the lateral fallback fixes).

### B2 — DEAD reachability gate on follow-on strikes · § DEAD · ☑ VERIFIED

**History:** 2026-06-24
- **Setup:** A target behind an intact SAM belt that blue wants to strike.
- **Pass:** Blue still tasks the DEAD (with SEAD escort) but **defers the deep
  strike** until the belt is actually down.
- **Fail signature:** Blue sends the follow-on strike into a live belt because
  it trusted an optimistic DEAD clear.

### B3 — Threat-weighted BARCAP orbit placement · §6 · ✖ REMOVED

**History:** 2026-08-09) — the threat-weighted volume and orbit forward-bias were reverted to upstream (planner re-convergence work order D); no pass owed. (Was ☑ VERIFIED 2026-06-25 before removal.

### B4 — TARCAP planned on CAS / A2A escort on forward packages · §6 · ✖ REMOVED

**History:** (2026-08-09) — the `air_engagement` escort-reach zone was deleted with the §6 revert, so escort need is back on upstream's clamped orbit zone; no pass owed. (Was ☑ VERIFIED 2026-06-24 before removal.) **Note for whoever next reads this:** the failure this row proved fixed — CAS spawning with no TARCAP, forward DEAD/BAI flying unescorted — is upstream behavior again by design. It is a known upstream defect queued as a post-freeze carve, not a regression to re-diagnose.

### B5 — Red forward-middle BARCAP layer (large maps) · §6 · ✖ REMOVED

**History:** 2026-08-09) — the forward-middle BARCAP layer was deleted with the §6 revert; no pass owed. (Was ☑ VERIFIED 2026-06-25 before removal.

### B7 — Red Intent: adaptive enemy posture · §55 · ✖ REMOVED

**History:** (2026-07-21) — the adaptive-posture feature was dropped (symmetric with the §40 removal); no pass owed.

### B8 — Strikeable motorpool depots: strike the reserve, force a repurchase · §56 · ☑ VERIFIED

**History:** adopted from upstream PR dcs-retribution#859, 2026-07-08; the reserve split (`reserve_armor_for` == `plan_groundwar`), the populator cap/round-robin/idempotence, the generator's parked/weapon-hold/no-datalink render + offset depot, the 1:1 `base.armor` decrement, and the motorpool-vs-front-line loss separation are unit-tested across `tests/**/test_motorpool_*.py` + `tests/ground_forces/test_reserve_armor.py`; **Red Tide now authors a depot near Haina** — headless-verified to bind to Haina/RED + materialise one `MotorpoolGroundObject` (`tests/retlab/test_red_tide_motorpool.py`), so the map/in-mission render is finally flyable

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — VERIFIED.** The save carries five motorpool TGOs, all on red bases (SANDFLY/Anapa-Vityazevo 5 alive, SQUIRREL/Maykop-Khanskaya **0 alive**, CRANE/Sochi-Adler 10, SALAMANDER + OSPREY/Sukhumi-Babushara 4 and 3), and the blue ATO carries a **BAI package tasked against SALAMANDER**. So the depots populate, render on the red side, get planned against by the auto-planner, and take losses to zero — the user's read on the night ("B8 spawned red and the AI tried to plan a strike against the motorpool") is confirmed from the save. Not yet watched: the 1:1 `base.armor` decrement forcing a visible repurchase, which is a multi-turn economy observation.
- **What CI cannot exercise:** whether the authored depot actually renders (the maintenance-facility icon on the map; the in-mission `Garage_A` building + the grid of parked reserve vehicles), whether killing a parked vehicle decrements the owner's `base.armor` and forces a repurchase next turn *without* shifting the front line, whether the spawn cap holds, and whether the debrief shows the motorpool losses.
- **Setup:** fly **Germany — Red Tide** (authors the Haina depot; `motorpool_enabled` on by default). The depot renders at Haina from turn 1, but its parked vehicles only appear once red has procured armor (`base.armor` is the purchase stock, empty at turn 0), so **play a couple of turns** before expecting vehicles; then strike some and end the turn. (Or author a `Garage_A` in any other campaign's ME.)
- **Pass:** the depot shows as a present maintenance-facility marker (never "destroyed"); in-mission it's a Garage A building + parked, non-firing, non-moving vehicles; each killed vehicle drops the owner's reserve by one (visible as a repurchase next turn) and appears on the debrief as "Motorpool units lost" / "`<type>` from motorpool"; the front line does **not** move from depot kills; the per-turn vehicle count respects `motorpool_spawn_cap`; a save with an authored depot loads with the motorpool injected.
- **Fail signature:** the depot renders "destroyed"/absent when empty (the `sidc_status` PRESENT pin broke); parked vehicles move or return fire (the passivate/alarm-green broke); a depot kill shifts the front line (the loss leaked into the front-line category — check `commit_motorpool_losses` vs `commit_front_line_losses`); `base.armor` double-decrements on a multi-motorpool CP (the shared-reserve round-robin broke); the per-turn count ignores `motorpool_spawn_cap` (the populator trim broke).
- **Interim evidence (2026-07-15, headless Red Tide self-play probe):** the reserve stock **actually
  accumulates** — Haina's `base.armor` marched 0 → 20 by turn 1 → 59 by turn 14 as red procurement banked
  undeployed armor — so the depot has vehicles to render within a couple of turns of a new game, exactly as
  this row's setup assumes (and well past the `motorpool_spawn_cap` 10, so the cap is live from early on).
  The render / kill / 1:1-decrement / debrief legs stay DCS-only.
- **Upstream drift sync (2026-07-16):** the parking grid + depot now rotate with the authored garage
  heading (upstream `401fbceda`) — when flying this row, also eyeball that the parked lot follows the
  `Garage_A`'s facing instead of sitting in a world-axis N/E grid (Haina's garage is authored at
  heading 0, where the rotation is a no-op — an ME-authored angled garage is what shows it plainly).
- **Upstream drift sync (2026-07-26, #899/#895 — adopted over the fork's shape):** placement inverted
  — the **depot static now renders exactly on the authored `Garage_A` marker** and the *vehicle grid*
  moves clear instead (`_GRID_OFFSET_M` 45.72 m / 150 ft into the building's local +x/+y corner,
  still heading-rotated); the old opposite-corner `_DEPOT_OFFSET_M` is gone. **Add to this row's pass
  criteria:** the Garage A building sits on the spot the author placed it (previously it drifted
  ~70 m diagonally off the marker), with the parked lot offset beside it rather than wrapped around
  it. Also new: `PlanMotorpoolAttack` now refuses a depot whose reserve pool is empty — on a fresh
  game (`base.armor` empty at turn 0) the ATO should contain **no** BAI/Strike package against the
  Haina depot until red has actually banked reserve armor, where before it fragged one at a
  guaranteed-empty target. Fail signature: an opening-turn ATO strike on an empty depot, or the
  garage rendering offset from its marker. No save migration — population is ephemeral.

### B9 — Air-droppable minefields: mine a road, kill a convoy, carry the field across the turn · §57 · ⊘ RETIRED

**History:** ⛔ REMOVED 2026-09-07 -- the feature was abandoned: the plugin, both settings, the cross-turn persistence and the map layer are deleted, so this row can never be run again. Previously: SHELVED 2026-07-30 — dropped from active use by user call, not deleted; every gate defaults OFF and Red Tide's preseed was removed, so nothing runs in any current campaign. Not a pending test while shelved; code/tests untouched (`tests/lua/test_minefields_runtime.py`, `tests/retlab/test_minefields.py`, `tests/missiongenerator/test_minefieldluadata.py`). Re-open as ☐ UNTESTED if the feature is ever resumed.
- **2026-07-11 flown Red Tide M1 (`csar-snatch-toggle-question-dfdb7a`): armed cleanly, nothing laid.**
  Load log `Minefields armed (dispenser 'CBU_99', radius 200m, 6 charges/field, power 100)`, zero Lua
  errors across ~125 min, `minefields_state: []` at exit — no CBU-99 was released this mission (none in
  the Tacview weapons log), so the drop→lay→kill→persist loop is still owed a deliberate mining sortie.
- **What CI cannot exercise:** the exact `CBU_99` runtime type string (the whole detection hinges on it), whether the tracked dispenser resolves to a sensible ground impact, whether the scripted explosion actually kills the crossing convoy vehicles and the loss lands as a convoy loss at debrief, the friendly-only F10 marks, and — across two turns — whether a field left undisturbed is re-laid at the same spot with the same charges and disappears once spent.
- **Setup:** enable **"Air-droppable minefields"** in Plugin Options (and, for persistence, the `air_droppable_minefields` setting). Fly an **A-7E / F/A-18C / AV-8B** with the **"Aerial Minefield"** loadout; drop a CBU-99 on a road a RED convoy uses. For persistence, end the turn without the convoy reaching the field, then start the next mission. For **auto-plan**, play **Red Tide** (preseeds `auto_plan_minefields` + the Hornet) and check the ATO for a fragged mining sortie against a red convoy.
- **Pass:** the drop lays a field (an F10 "Minefield (laid)" mark appears for your side); a RED convoy crossing it takes losses that show as convoy losses at debrief; with the setting on, an un-driven field is re-laid next mission at the same spot with the same charges, depletes as convoys hit it over turns, and vanishes once exhausted; the enemy never sees the field. **Auto-plan:** the ATO carries a Hornet BAI mining sortie targeting a red convoy, loaded with the "Aerial Minefield" CBU-99 loadout, and flying it (AI or player) drops the dispenser on the convoy's road and lays a field there.
- **Fail signature:** nothing detonates (the `CBU_99` type string is wrong, or the drop wasn't tracked to impact); a non-CBU-99 drop or a red drop lays a field (the weapon/coalition gate broke); the field detonates at t=0 (the grace broke); a field is lost across the turn or never depletes/disappears (the `minefields_state` channel or `reconcile_minefields` broke); the enemy sees the field.

### B10 — Mission-start briefing popup: the slot-in cards · §58 · ☑ VERIFIED

**History:** 2026-07-15, user pass — the reworked cards + beep work, "just fine, no issues"; by-design limitation confirmed in the same report: a DCS **dynamic-slot** pilot gets no briefing — dynamic-slot jets aren't player-crewed ATO flights, so the emitter carries no record for them) (was ✗ REGRESSED on the first MP fly — 2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`: **the fail signature occurred — NO card or beep was ever noticed by any pilot** (user eyewitness report, same session), despite `BRIEFING|: armed for 12 player flight(s)` at load and zero briefing-related Lua errors across ~125 min of MP with genuine slot-ins and re-slots. First-ever MP/dedicated-server fly of the feature. Built 2026-07-11, extended with the taxi card + raw-turn number; the emitter shape (shared header with the raw-turn mission number + one record per player-crewed flight, AI-only excluded, gated off) is unit-tested in `tests/missiongenerator/test_briefingluadata.py`, and the runtime (briefing card with every field + right group id/duration, the **taxi card flashing `DURATION` s later** with the callsign + ground freq, the `groundFreq` override, the mission-start sweep, AI/unknown/absent no-ops, the birth+sweep debounce) is harness-tested in `tests/lua/test_briefing_runtime.py`. The harness models no DCS UI, so whether the text actually renders on screen is DCS-only.
- **Root cause (2026-07-11, adversarially cross-checked from dcs.log + the flown miz + the plugin source + DCS API
  research):** two compounding causes, no crash. **(1) Paused-server time compression** — the dedicated server sat
  PAUSED at frozen sim t=0 for ~33 min while all 8 pilots slotted in (wall 00:00–00:17); `timer.getTime()` is frozen
  during a pause, so every card was scheduled for sim t=5 and they ALL fired in one 12-s window right at unpause
  (00:19:40), 2–19 minutes after each pilot sat down, amid startup workload. The cards were almost certainly
  *delivered* (timers scheduled during the pause provably fired at unpause — water_relocate/MANTIS did; the un-pcall'd
  card closures produced zero timer errors; every pilot was seated at fire time) — nobody was looking, because
  **(2) the beep was silently dead**: the plugin passed the bare basename `briefing-beep.wav` to `outSoundForGroup`,
  but the wav lives at `l10n/DEFAULT/` inside the miz and DCS resolves in-miz sounds ONLY with that archive-path
  prefix — a wrong path fails without an error (the code's own comment promised the fallback but never implemented
  it; this row's own pass text predicted exactly this failure). Eliminated with evidence: the flown load DID arm the
  current #573 plugin (extracted byte-identical from the flown miz), BIRTH+`getPlayerName` provably worked for every
  join (Moose logged each by name), no dropped trigger, no timer error. **Residual (~30%):** the post-unpause
  re-slot/late-join cards were NOT compressed and should have painted normally — unverifiable because the plugin had
  zero per-card logging (its designed blind spot).
- **Rework applied (2026-07-11, same session):** (1) the beep path fixed to `l10n/DEFAULT/briefing-beep.wav`;
  (2) every card/taxi fire now logs `BRIEFING|: card -> <group> gid=<id> t=<time>` (and `card skipped (group gone)`)
  so the next fly discriminates "sent but unseen" from "never sent" straight from dcs.log; (3) a skipped fire (pilot
  left the seat before t+5) clears the debounce stamp so their next slot-in still gets the card; (4) a nil
  `getPlayerName` at the BIRTH instant in a briefing-listed group gets one +2 s re-check before being written off as
  AI (the documented MOOSE #806 event-timing race). Harness tests extended to pin all four
  (`tests/lua/test_briefing_runtime.py`, 13 green). The paused-server compression itself is **intended behavior**
  (the sandbox has no wall clock; nothing can fire during a pause) — with a working beep, "cards + beeps ~5 s after
  unpause" is the correct squadron-night contract, now documented in the plugin header.
- **Re-fly pass:** on a dedicated server (paused pre-start joins, then unpause), each pilot gets their own card +
  an audible beep ~5 s after unpause, the taxi card + beep ~12 s later, and dcs.log carries one `BRIEFING|: card ->`
  line per pilot; a mid-mission re-slot gets its cards ~5 s after slotting. **If the log shows the `card ->` lines
  while a watching pilot still sees nothing, escalate to the delivery investigation** (DCS MT/dedicated-server
  message-rendering regressions — forum topics 321287/369258) with the log as proof.
- **☑ VERIFIED (2026-07-15, user pass, session `gallant-panini-5485e7`):** the reworked popup was observed
  working — "our changes make it work just fine, no issues." One accepted limitation from the same report,
  **by design, not a bug:** a pilot who takes a DCS **dynamic slot** gets no briefing — dynamic-slot jets are
  not player-crewed ATO flights, so the emitter has no record for them (consistent with the wider
  dynamic-slots model gap: those airframes are invisible to the campaign layer).
- **What CI cannot exercise:** whether `trigger.action.outTextForGroup` actually paints the card on the pilot's screen, that it reads correctly (campaign / Mission N / date / time / callsign / aircraft / task / field), that the **taxi card follows it** (`<callsign> — Get started up, Contact ground @ 249.50 when ready to taxi`) and each clears after its duration, and — the two paths — that it fires both at mission start in single-player (the sweep) and on a mid-mission slot-in / rejoin on a server (the birth handler), each exactly once.
- **Setup:** leave **"Mission-start briefing popup"** on (default). Generate and fly any mission with a player flight; watch the screen the instant you take the slot, then ~12 s later for the taxi card. For the server path, join a running mission and slot in mid-flight.
- **Pass:** ~5 s after slot-in (not instantly) the briefing card appears for ~12 s (campaign name, `Mission N` matching the kneeboard's turn number, date + time, your callsign / aircraft / task / departure field) with a **short beep**; ~12 s later the taxi card flashes with your callsign + `Contact ground @ 249.50` (and its own beep); each shows once (no double-print), and a re-slot after the debounce re-shows them. (The beep is `briefing-beep.wav`, played by `outSoundForGroup` — if it's silent, the sound resource didn't resolve by basename; try the `l10n/DEFAULT/` path.)
- **Fail signature:** no card appears (the node wasn't emitted, or the birth handler + sweep both missed the slotting); the card double-prints on a single slot-in (the debounce broke); the taxi card never follows (the scheduleFunction broke) or shows the wrong freq; the mission number is turn+1 again (mismatches the kneeboard); an AI-only flight's pilot slot shows a card for a flight that isn't theirs (the group match broke).

### B11 — Ground AI sleep: distant garrisons stop thinking, wake on approach · §59 · ⊘ RETIRED (removed 2026-09-23, DM: killed)

**2026-09-23 — REMOVED on the DM's call.** The plugin, the emitter and both settings are deleted, so this row can never be run again.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not dropped, and never observed doing its job.** The `aisleep` plugin and `perf_ground_ai_sleep` are both still in the tree. The plugin armed in every mission of tests 1–16 (Vectron's Claw, Caucasus 1995, Desert Trident, Sinai, Noisy Cricket; `AISLEEP|: managing N garrison group(s)`, up to 8 loads in test 7) because the DM's August campaigns carried the setting on (`test 1`, `brady` and the 13th-test saves all read `perf_ground_ai_sleep = True`); it has not armed since test 17 because the September campaigns carry it off (the `91526`, `CSAR` and `Maybe 414` saves all read False). The plugin logs only at arming and on a poll error, so a wake has never been visible in any log and never will be until a wake line exists. Nothing in 33 captures can move this row; to close it, turn the setting on in the current campaign and add a `AISLEEP|: woke <group>` line first, or the flight proves nothing either way.

**2026-08-22, test 14 — armed, never observed waking.** `AISLEEP|: managing 53 garrison group(s),
wake radius 15 NM, poll 30s` on both loads, then **no wake line for the rest of the mission**,
including a player BAI run onto TURTLE. Not a fail: the plugin may only log at arming. Before
calling this a defect, confirm whether the wake path logs at all — a silent wake and a broken
wake look identical here, which is the "prefer a loud failure" rule biting.

**History:** built 2026-07-12 off the MP-performance complaint; the emitter's positive list (garrisons in; air defense / missiles / ships / buildings / the concealed scripted movers / dead groups out; gated off) is unit-tested in `tests/missiongenerator/test_aisleepluadata.py`, and the runtime (sleep after grace, wake on approach, parked aircraft never wakes, hysteresis never flaps, a hit wakes a sleeper immediately, dead groups stop the poll, no node = no-op) is harness-tested in `tests/lua/test_aisleep_runtime.py`. The harness models no DCS AI, so what sleep actually buys — and that it's invisible — is DCS-only. **First live arming evidence 2026-08-16** (Baltic Fury turn-3 spectator watch, session `c86c58dd`): dcs.log `AISLEEP|: managing 9 garrison group(s), wake radius 15 NM, poll 30s` — the emitter→plugin chain runs on a real modern campaign; the wake-on-approach and no-regression clauses remain the DCS-only part.
- **What CI cannot exercise:** whether `Controller:setOnOff(false)` measurably reduces server load on a dense mission (the whole point), whether a slept group is visually indistinguishable (renders, killable, death recorded at debrief), whether the wake on approach is seamless (a garrison's embedded SHORAD is live before you're inside its envelope), and that MANTIS SAMs, TIC formations, convoys, SCUDs and the COIN/ambush movers are visibly untouched.
- **Setup:** enable **"Distant ground AI sleeps until aircraft approach"** (RetLab Features → Performance; default off) on a dense campaign (Red Tide — not preseeded). Check the log for `AISLEEP|: managing N garrison group(s)`. Fly toward a rear enemy base garrison, kill a slept unit, watch the debrief; compare server frame/CPU on a heavy turn against the same turn with the setting off.
- **Pass:** the arm line lists a plausible garrison count (not 0, not the whole world); a rear garrison behaves normally when you arrive (embedded SHORAD engages inside its envelope); a unit killed while slept records at debrief like any other; SAM/EWR sites, the FLOT firefight, convoys and every scripted mover behave exactly as with the setting off; a heavy mission runs measurably smoother server-side.
- **Fail signature:** `managing 0 group(s)` on a garrison-rich map (the emitter filter is too tight, or group names don't match the .miz); a SAM site or EWR goes blind (a non-armor TGO leaked into the list); a COIN cell / HVT convoy / VBIED / ambush team / SCUD stops moving (a concealed/map_hidden mover leaked); a garrison never reacts even at close range (the wake poll or the hit-wake broke — check `aiOnOff` semantics against the DCS controller); kills on slept units missing from the debrief (would falsify the setOnOff-keeps-death-events assumption — pull the feature back to default-off and re-scope).
- **AAA gun sites** (`perf_aaa_site_sleep`, added 2026-07-19 off the "10 fps on the ground" report — Yankee Station measured 2–4× every other campaign, AAA 4–12×, while the emitter managed 16 of 121 groups): **Setup** — enable it *and* the master toggle on **1968 Yankee Station** (the AAA-doctrine laydown; the flown turn-1 miz is in the §66 archive for a before/after). Expect the arm line to jump from ~16 to ~50+ groups. Fly the same profile twice, setting off vs on, and compare frame time on the ramp (the reported symptom was 10 fps parked at an *empty* field, so the ramp is the measurement point, not the target area). **Pass:** frame time visibly recovers; flak belts still open up on the same pass and at the same range they always did (the sensor guard's whole claim is that a 5 km gun is awake long before you're inside 5 km); the §33 flak-gauntlet bursts still appear; MANTIS logs no change in resolved SAM/EWR counts. **Fail signature:** guns that never fire, or fire late (the wake radius is too tight against real DCS detection — raise `wakeRadiusNm`, it is always safe); MANTIS resolving fewer EWR groups with the toggle on (an EWR-role site that MANTIS actually needed went dark — tighten `AAA_SLEEP_MAX_DETECTION`); no measurable frame-time change (the AAA was never the sink — re-measure with the probe method in the §59 features-doc section before tuning further).

### B12 — SAM guidance-radar redundancy: a site survives its first HARM · §60 · ✖ REMOVED

**Removed 2026-09-29** (DM call): every SAM site is back to one guidance radar. No pass owed.

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B12 is good") (was ☐ UNTESTED, built 2026-07-12 off the Red Tide finding "a single HARM kills the entire site"; the layout contract — every SAM layout asks for 2 guidance radars AND its .miz template carries ≥ 2 positions for the slot, across all 31 layout/slot pairs incl. the SA-6's 1S91, the mixed site's both channels, and the NASAMS/Sky Sabre search-slot engagement radars — is CI-locked in `tests/armedforces/test_sam_radar_redundancy.py`, and generation was probe-verified end-to-end (every preset spawns 2 radars of the right type). CI can't exercise DCS's actual guidance logic.
- **What CI cannot exercise:** whether a site with one dead track radar actually keeps engaging in DCS (the second TR picks up guidance — the whole point), whether MANTIS keeps treating the half-decapitated site correctly (alive, in the network, threat rings honest), and whether AI SEAD re-targets the surviving radar instead of calling the site dead.
- **Setup:** NEW game on any SAM-rich campaign (Red Tide: SA-2/3/5/6 belts + the S-300s). Confirm on the map/intel card that a site shows 2 track radars. Fly SEAD (or let an AI SEAD flight shoot), kill exactly one TR, then press the site with a second aircraft.
- **Pass:** the site keeps launching after the first TR dies (guidance passes to the second radar); it only goes silent after BOTH are dead; MANTIS behaves (no Lua errors, the site stays networked while alive); the second radar sits far enough from the first that one HARM impact never kills both.
- **Fail signature:** a site with one dead TR stops engaging entirely (DCS group guidance doesn't fail over — would gut the feature, re-scope toward splitting radars across DCS groups); both radars die to one missile (positions too close — re-space the template); a LayoutException at generation (`unit_count` vs template positions drifted — the CI test should have caught it); MANTIS misclassifying the site after the first radar kill.

### B13 — Red Tide rear S-300 hubs are 3-battalion regiments · Red Tide (SAM-belt STANDARD) · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B13 is good") (was ☐ UNTESTED, built 2026-07-12 — a pre-lock Red Tide change, recorded at the time as a feature-lock override; the marker laydown — 3 clustered LORAD battalions + a shared EWR at Sperenberg/Kastrup/Schönefeld — and the single-radar contract (fork faction `Russia 1980 (Red Tide)` LORAD presets → single-radar S-300/SA-5 layouts; base `S-300 Site` still §60-doubled) are CI-locked in `tests/retlab/test_red_tide_sam_regiments.py`, and the loader assignment (3 `long_range_sams` preset locations per hub CP) + single-radar generation were headless-verified. CI can't exercise MANTIS netting or DCS terrain.
- **What CI cannot exercise:** whether the three battalions + EWR at a hub actually net into **one** MANTIS regiment (shared early warning, graceful degradation), whether the new battalion spots are **open ground** (pydcs has no GCW surface query — a spot could be forest/water), and whether the regiment now survives a SEAD pass instead of dying in one turn like the old single site.
- **Setup:** NEW game on Red Tide, **keep the recommended enemy faction `Russia 1980 (Red Tide)`** (single-radar only applies with the fork). Fly toward Sperenberg / Kastrup / Schönefeld; check the map shows 3 separate S-300 sites + an EWR per hub, each site with **one** track radar. Run a SEAD/DEAD pass and see how much of the regiment survives.
- **Pass:** each hub shows 3 dispersed single-radar LORAD fire units + a shared EWR, all one networked IADS (MANTIS); killing one battalion's radar drops that battalion but the regiment keeps engaging; the belt takes several sorties to roll back (not one HARM / one turn); every new battalion sits on open ground; front MERAD screen still shows its §60 two-radar sites. **Battalion composition (leaned 2026-07-12 after the generated-save review):** S-300 battalion = 1 search radar + C2 + 1 track radar + 4 TELs (+PD); SA-5 battalion = Tin Shield + Square Pair + 6 launchers (+PD), no battalion-level P-19/P-14 — the shared EWR is the regiment's early warning. A hub mixing S-300 and SA-5 battalions is expected (the loader fills LORAD markers with a random faction LORAD preset), not a fail.
- **Fail signature:** a battalion spawns in forest/water or on a building (re-place that marker in the ME); the three battalions don't net (spacing > comms range, or an EWR missing — check the F10 IADS view); a hub shows 2-radar S-300 sites (the fork faction wasn't selected, or §60 leaked into the single-radar layout); the regiment still evaporates turn 1 (too few battalions / netting broke); `Russia 1980 (Red Tide)` missing from the faction dropdown (faction JSON didn't load).
- **2026-07-12 in-app catch (user):** the fork's third single-radar preset `SA-10A/S-300PT (Single Radar)` was all High Digit SAMs units and showed in a no-mod game's buy menu (the mod-off strip matches preset *names* only). Preset removed; `apply_mod_settings` gained a provenance backstop + `Game.on_load` heals pickled `ArmedForces`; guards in `tests/retlab/test_faction_mod_presets.py`. The buy menu at a red CP should now offer only vanilla-unit groups.

### B14 — Host red scramble: the F10 bandit spawner feeds the flight · §61 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B14 is good"; the host-only scoping question asked in the same pass is CONFIRMED IN CODE: with `redscramble.hostPlayers` set (Red Tide preseeds `Flash`) the menu is attached per-group via `missionCommands.addCommandForGroup` and every scramble message goes out through `announce(requester_gid, …)` → `trigger.action.outTextForGroup`, so ONLY the host sees the menu and the messages. `addCommandForCoalition` / `outTextForCoalition` are the fallbacks used only when no `hostPlayers` is configured — the plugin logs `REDSCRAMBLE|: no hostPlayers configured -- menu visible to ALL BLUE clients` in that case, so the log line tells you which mode armed) (was ☐ UNTESTED, built 2026-07-12 off the M1 debrief "once the first wave was over it felt quiet"; the emitter contract (gated, red airfields nearest-front first, templates best-interceptor first, no-template/no-base = no node) is unit-tested in `tests/missiongenerator/test_redscrambleluadata.py`, and the runtime (host-name menu gating incl. the pre-seated sweep, coalition fallback, spawn at the picked base with the QRA air profile, weapons-free + host announce, the AttackGroup vector onto the nearest airborne blue player, no re-task while the target holds, unique repeat clones, the 9-base menu cap) is harness-tested in `tests/lua/test_redscramble_runtime.py`. Whether the DCS AI actually presses the intercept is DCS-only.
- **What CI cannot exercise:** whether the MOOSE `SpawnAtAirbase` air-spawn clone comes off the field flying (not stalled — the QRA InitSpeed lesson), whether the `AttackGroup` task makes the bandits genuinely commit to the players (and re-commit when re-vectored to a new target), whether the F10 menu renders per-group for only the named host in real MP, and that the armed template actually carries an A2A loadout (the pydcs default-task payload path).
- **Setup:** Red Tide preseeds the setting + plugin + `hostPlayers: Flash` (a **substring** match — the host's static name tag covers the changing `"<flight> 1-x | Flash"` prefix; empty = every BLUE client sees the menu). Generate, fly with at least one blue jet airborne, open F10 → Other → **HOST: Red Scramble**, press a base → `MiG-29S x2`, and separately the **EMERGENCY** command.
- **Pass:** only your slot sees the menu (a squadmate confirms theirs is clean); within seconds of the press the announce card appears and 2 armed bandits appear over/at the chosen base (log: `REDSCRAMBLE|: spawned ...`); they turn toward the nearest airborne blue fighters, commit, and shoot; the EMERGENCY press launches from the base nearest the airborne players; a second press spawns a fresh flight; killing them all ends it (no respawn) and nothing changes at the turn boundary.
- **Fail signature:** no menu for the named host (fragment mismatch — the match is a case-insensitive substring of the in-game name, so check the tag really appears in it; or the node wasn't emitted — check the setting + `REDSCRAMBLE|` arm line); everyone sees the menu despite a configured name (option didn't reach the miz — the §36 plugin-preseed lesson); a non-host sees the menu (their name contains the tag — pick a more distinctive fragment); bandits spawn stalled/diving (InitSpeedKnots didn't take — QRA history); bandits spawn then orbit ignoring the players (`AttackGroup` via `setTask` rejected — re-scope the vector push to a Mission-route task, the §15 combatsar lesson); a spawn press does nothing with `spawn failed` in the log on hot/runway mode (ramp congestion — use the default air mode); red QRA dispatcher errors right after a clone (alias collision with the `Intercept|` templates — rename).

### B15 — Squadron-sequenced Hornet/Tomcat board numbers · §62 · ☑ VERIFIED (2026-09-16, audit)

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED: the Tomcat half is proven in the generated missions, three campaigns.** VF-103 on Iron Gate (the 08-23 turn and test 24): the squadron's first jet of the mission wears `aa100` (the CAG bird) once, and the line jets cycle `aa101`, `aa103`, `aa105` across the Escort pairs and TARPS singletons, so every pair shows two different painted numbers. VF-143 on Scenic Route (test 30): the CAG livery on the first BARCAP lead, then the two low-vis liveries alternating, which is the two-livery case the row predicts. A squadron whose DCS livery set has one entry (the VMF-29 line on Iron Gate's F-14B, VF-142 on Noisy Cricket, Iran's F-14A) paints one number on every jet, which no allocator can change. The livery is the paint, so a different `livery_id` in the miz is a different number in the F2 view. The Hornet half was confirmed visually 2026-07-16.

**2026-08-23 — the Tomcat half was falsified and this row is re-opened.** No F-14 livery
declares a board-number material, so DCS paints nothing on a Tomcat; its visible modex is the
livery texture. Control: Su-27, MiG-29A, F-15C, Su-25 and FA-18C all name the material in their
livery `description.lua`, and 0 of 47 stock F-14 liveries do. The 2026-07-16 pass read VF-32
F-14Bs whose livery set is numbered 100/101/102/103 while §62 had stamped `onboard_num`
100/101/102/103 on the same jets — the two agreed by coincidence. **The Hornet half stands**
(its liveries carry the material). Fixed by `LiveryAllocator`: a squadron's first jet of the
mission wears the first entry of its `livery_set` (the X00 CAG bird), the rest cycle the line
jets. See §62.
- **What CI cannot exercise (the new half):** whether a Tomcat squadron's jets actually show
  different painted numbers in the F2 view.
- **Setup (Tomcat):** any campaign fielding an F-14B(U) squadron — `clash_of_the_titans`,
  `red_sea_rising`, `operation_desert_trident`. **Start a NEW campaign**; squadron liveries are
  pickled, so an in-flight save keeps its old single livery. Generate a turn with at least a
  4-ship, then F2 through the flight.
- **Pass (Tomcat):** on VF-103 or VF-32 the four jets wear four different board numbers, the
  first the squadron's X00 CAG bird (AA100 / AC100), and a second flight of the same squadron
  continues into the line jets without a second CAG bird. VF-101, VF-11 and VF-143 have only two
  liveries in the DCS distribution, so they alternate — two numbers, not four.
- **Fail signature (Tomcat):** all four identical (the allocator wasn't reached — check the three
  `apply_livery` sites pass `self.livery_allocator`); the CAG bird on jet 2/3/4 (preset set is
  not ordered lowest-modex-first — `tests/test_squadron_livery_sets.py` locks this); two CAG
  birds in one squadron (an un-plumbed caller fell back to the random round-robin); a livery
  missing entirely from the rotation (an old save's drained `_livery_pool` — `ordered_livery_set`
  rejoins it).

**History:** 2026-07-16 (user visual confirmation on the flown Scenic Route turn-3 test — a US Navy 2005 carrier campaign fielding both Hornets and Tomcats: *"The Modex on our fork is 100% working I watched it with the last test. Everyone's modex looked accurate."* This settles the row's one DCS-only unknown — **DCS does paint the mission's `onboard_num` on the airframe**, and it clears the specific doubt below about the Heatblur F-14's livery-driven BORT rendering ignoring it (8 Tomcats were airborne on that test). Built 2026-07-12 off the user finding "board/modex numbers are completely random"; the per-squadron 100/200/300 blocks, the cross-flight X00/X01/… sequence, Tomcats-before-Hornets block order, per-coalition blocks, the non-modex no-op, the whole-block country reservation, the nine-squadron wrap, and the pydcs id guard are unit-tested in `tests/missiongenerator/test_modex.py`.)
- **Scope of the confirmation:** a coarse visual pass ("everyone's looked accurate"), not a block-by-block audit — it establishes the *mechanism* (`onboard_num` → painted number), which is what every downstream design rests on. Not yet separately confirmed: a nine-squadron wrap, and any airframe outside `MODEX_AIRCRAFT_IDS` (moot today — the set is the whole feature; it matters only if upstream [#863](https://github.com/dcs-retribution/dcs-retribution/issues/863) per-pilot pins land, since a pin deliberately bypasses the id set and would apply to e.g. the A-4E-C).
- **What CI cannot exercise:** the rendered board number on the jet skin / in the F2 view — in particular the Heatblur F-14, whose BORT number rendering is livery-driven and may ignore the mission's `onboardNum`.
- **Setup:** Any campaign fielding a Hornet or Tomcat squadron (Red Tide fields the Hornet). Generate a mission with at least two flights from the same squadron; check the board numbers in the F2 view / mission editor (or open the `.miz` and read each unit's `onboard_num`).
- **Pass:** every jet of the squadron wears its block in sequence (first flight 100/101, the next flight continues 102/103, …); a second Hornet/Tomcat squadron wears a different hundred block; F-14 squadrons hold the 100/200 blocks when sharing a wing with Hornets; non-Hornet/Tomcat aircraft are unaffected.
- **Fail signature:** random three-digit numbers on a Hornet/Tomcat (allocator not reached — check the four `modex_allocator.assign` sites in `aircraftgenerator.py`); two squadrons sharing a block (air-wing iteration order unstable); a same-country non-Navy jet wearing a number inside a squadron block (the block reservation didn't take); the F-14 model showing a number different from the miz's `onboard_num` (Heatblur livery limitation — document, don't chase).

### B16 — Ship-launched cruise missile raids · §63 · ☑ VERIFIED

**History:** 2026-07-16 flown Persian Gulf "Scenic Route" test, session `dcs-test-results-001fd7` — the scripted FireAtPoint push fires the exact commanded quantity, on BOTH vanilla hulls, and the whole magazine loop closed end-to-end
- **2026-07-16 evidence (dcs.log + DCS debrief.log + the flown `retribution_nextturn.miz` + headless `test.retribution` dump):** auto raid `CRUISEMISSILES|: 0158 | GOSHAWK (Naval Two Ship) fired 6 at PADEMELON (10 left this mission)` at **+254 s** — inside the new [240, 900] s stagger window (#607); exactly **6 `shot` events, weapon `BGM-109C Tomahawk`, initiator `TICONDEROG`** — the hull the row called *least certain* fires cleanly (2×8 = the 16 magazine, validating the hull table); 7 `hit` events on the target `.Command Center` (killed — in the Qt debrief loss list) + a Tomahawk `kill` on a Ural-375 recorded **natively**; the raid target was the **C2 TGO** (C2-first pick) and the post-commit save already re-plans next turn's raid onto **INSECT, the next command center** (re-targeting after the kill); the state mirror round-tripped — Qt debrief row "**6 fired, 10 remaining**" and the save's `cruise_missile_magazines` reads `GOSHAWK: 16→10` (no rearm, no orphaned keys); an earlier same-night mission (separate save) also flew the **player F10 marker call-for-fire** (`0124 | BUFFALO (Escort) fired 4 at your F10 marker`) and a Burke-group auto raid (96→86) — both fire paths + both vanilla hulls demonstrated; zero plugin/script errors in either mission.
- **First ground-AD cruise-missile intercept observed (2026-07-17 flown Scenic Route Merged, Tacview `Tacview-20260717-172716`):** a red Tor killed one of the 6 raid BGM-109s ~12.7 km short of the aimpoint — INSIDE the 8 NM defender-wake ring — and 5/6 impacted the target. Suggestive of the wake working but **not conclusive**: the same mission's Tors were also engaging JSOW glide bombs at their own sites (5 intercepts), which makes them hot without §63's help. A raid against a quiet (un-bombed) defended target is still the clean wake test.
- **Observed gap (user-watched live, 2026-07-16): NO defender engages a cruise raid — the SHORAD-intercept half of §63 FAILED.** The target's point defense (`0011 | SLUG (SHORAD)`, 2× SA-15 Tor + Dog Ear SR, ~250 m from the impact point) sat **alive and idle** through the whole 6-missile salvo. Root cause, code-confirmed: SLUG ran **vanilla** (red MANTIS managed only the 3 "(SAM)" groups; red's SHORAD link armed **zero** PD groups — the bridge wraps only `IadsRole.POINT_DEFENSE` escorts hanging off SAM nodes, and SLUG is a standalone SHORAD TGO guarding a C2 site) with no alarm-state option in its miz group ⇒ DCS default **ALARM STATE AUTO, which never goes weapons-hot for a weapon object** (a cruise missile is not an "aircraft threat" to the auto-wake). The *managed* paths are equally blind by construction: MANTIS EMCON wakes off MOOSE `Detection` (scans **units**, never weapons), and the SHORAD link wakes only off `SHORAD.Harms`/`SHORAD.Mavs` (ARMs + Mavericks — **no BGM_109/Kalibr entry**) or MANTIS SEAD suppression. So no defender anywhere in the stack could wake for a cruise raid unless already hot for another reason. The B16 core-loop verdict stands (intercept was an explicit "CI cannot exercise" unknown, not a pass criterion).
- **Defender wake VERIFIED in the air (2026-07-17 night fly, Tacview `Tacview-20260717-214932`,
  session `tacview-test-analysis-5bb161`):** the launch logged `CRUISEMISSILES|: defender wake --
  7 AD group(s) near the aimpoint held RED` + `0048 | FERRET (Naval Two Ship) fired 6 at
  WATERBUCK (42 left this mission)` at sim t≈480 (inside the stagger window), and the woken Tors
  **killed all 6 BGM-109s** (Tor 9M330 terminals matched each TLAM terminal 52–240 m, 5–6 km
  short of the aimpoint). Conclusive this time — the raid ran t=500–1060, before any other blue
  weapon was in that area (Mavericks from t≈1387, HARMs from t≈3240), so the Tors had no other
  reason to be hot. Both pass criteria met (wake log + visible 9M331/9M330 engagement); the
  stand-down half wasn't disprovable from Tacview but nothing engaged abnormally later. **Balance
  observation:** a 6-missile raid against a woken 3-Tor defense = 0 leakers — with the wake live,
  small raids against intact PD are free intercepts; saturation (bigger `#N` salvos) or
  SEAD-first is now the real doctrine, which is the realistic outcome.
- **Fix BUILT same session (now flown, see above): the defender launch wake.** Every launch (raid + F10 call share `fireCruise`) now sets the opposing side's ground AD groups within `defenderWakeRadiusNm` (8 NM) of the **aimpoint** to **alarm state RED** — alarm state only, `enableEmission` untouched (the crash-history constraint) — held ~estimated missile arrival + `defenderWakeExtraS` (300 s), then restored to AUTO (per-group `wakeUntil` bookkeeping; overlapping launches extend the hold; a MANTIS-managed site keeps its own EMCON loop). Options `defenderWake`/`defenderWakeRadiusNm`/`defenderWakeExtraS`; harness-pinned (wake, stand-down, far/friendly/non-AD selectivity, kill switch) in `tests/lua/test_cruisemissiles_runtime.py`. **Re-fly pass:** the launch logs `CRUISEMISSILES|: defender wake -- N AD group(s) near the aimpoint held RED` and the SA-15 visibly engages the inbounds (Tacview: 9M331 launches at BGM-109s). **Fail signature:** the wake log fires but the Tor still never shoots (residual gap = DCS's own Tor-vs-TLAM engagement logic, not alarm state); or defenders stuck RED long after the raid (stand-down broke).
- **Second flown test, 2026-07-16 (turn 3, PRE-wake build — PR #610 unmerged when flown; Tacview `Tacview-20260716-014958`):** the raid re-targeted **INSECT** exactly as the post-commit save predicted, from the debited magazine (`fired 6 at INSECT (4 left)`), and a same-turn re-fly logged the identical `4 left` — **flown proof the debit is turn-boundary-only** (regeneration never double-counts, the §54 rule). Salvo fate: **2 of 6 killed by red NAVAL SAMs** — a Krivak pair (`0115 | NAUTILUS`) parked in the flight path fired 13 SA-N-4s (`SA9M33`), two Tomahawk removals matching the missile terminals to the second — **ship AD engages cruise missiles natively** (no alarm-state model afloat), so the saturation game is real wherever a defender can shoot; **1 terrain loss** descending through 1256 m over the interior mountains (no shot correlates — DCS's FireAtPoint route doesn't terrain-follow); **3 arrived** (two within 60 m of INSECT, one at 257 m). Meanwhile the target's own PD — `0122 | DINGO (PD)`, a **SHORAD-linked** Tor held dark (this laydown armed red's link: "3 point-defense group(s) held dark") — fired nothing: the **linked-PD variant of the gap is now flown-confirmed** (turn 2 confirmed the vanilla-AUTO variant). Launch at sim t≈736 s — inside the [240, 900] stagger window (wall-clock deltas were shorter; the user ran time acceleration). Bonus fix-coverage fact: the bridge builds SHORAD with `useEmOnOff = false`, so linked PD is darkened by **alarm GREEN** — the wake's alarm-RED override reaches it (no emission toggling needed).
- **Residual (minor):** the `#N` marker-text salvo sizing untested (default salvo 4 used); the CH `*_LACM` Kalibr hulls + a red-side raid unflown; full magazine exhaustion → "ship goes silent" untested.
- **What CI cannot exercise:** whether a scripted `PushTask(FireAtPoint, weaponType=CruiseMissile)` makes the ship AI fire exactly the commanded quantity (the ME-authored task is community-proven; the scripted push is the same task table but unflown); which curated hulls honor it — the vanilla `USS_Arleigh_Burke_IIa` is the near-certain case, the vanilla `TICONDEROG` Tomahawk fit the least certain, the CH `*_LACM` hulls per their mod's fits; DCS Tomahawk/Kalibr flight over terrain at range; and whether MANTIS/SHORAD (Tor/Pantsir/Patriot) actually engages the inbound missiles.
- **Setup:** any campaign whose `.miz` authors a ship TGO with a curated LACM hull in range of enemy ground (or drop-spawn one, §20). Turn ON `cruise_missile_strikes` + `cruise_missile_auto_raids` (Mission Generation → Naval strike; the `cruisemissiles` plugin defaults ON). Fly (or spectate) past the raid delay (default 240 s); separately place an F10 marker on a shore target and press F10 → Cruise Missile Strike → "Fire at last F10 map marker", then "Magazine status"; repeat with a marker whose text is just `2` (or `#2`) — the salvo should be exactly 2.
- **Pass:** at ~4 min the launching side gets "CRUISE MISSILES AWAY — N missile(s) from <ship> inbound to <target>" and the defender only "LAUNCH WARNING — enemy cruise missile launch detected" (log: `CRUISEMISSILES|: <group> fired N`); missiles visibly launch, cruise to the planned building/C2 target and impact (Tacview: BGM-109/Kalibr tracks); the F10 call lands a salvo near the marker (a `#N` marker text fires exactly N); "Magazine status" counts down by exactly what fired; next turn the debrief shows the killed TGO units as ordinary ground losses, and the following mission's magazine reads the debited stock (fire the whole magazine over 2-3 missions → the ship goes silent, menu answers "no ship with missiles in range").
- **Fail signature:** cue fires but no missile leaves the rail (the ship AI rejected the scripted FireAtPoint or the hull carries no cruise missiles — check the hull against the encyclopedia, drop it from `LACM_SHIP_DCS_IDS` if the fit is wrong); guns fire instead of missiles (weaponType flag ignored — re-check 2097152 reached the task table); the full VLS ripples ignoring `expendQty` (quantity not honored — cap the magazine emit as the only guard and note it); magazine never decrements across turns (`cruise_missiles_state` missing from the state json — the §57 dirty_state path); a raid fragged inside a ROE zone on a Vietnam/COIN campaign (the §40 gate didn't hold); missiles vanish into a ridge every time at max range (shorten `MAX_RAID_RANGE_M`).

### B18 — Curated carrier comms: the CV Operations Data page reads like a boat card · §65 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B18 is good") (was ☐ UNTESTED, built 2026-07-16 off the user complaint about the DCS-generated page ("Callsign: 0796 | CVN-71 …, TACAN 1X, Link 4 255.0"); the curated table invariants, the stored-wins / taken-degrades-to-neighbor precedence for all four resolvers, the shared-pool ICLS allocator, and the flagship-name collision guard are unit-tested in `tests/test_carrier_comms.py`, and the whole path is headless-verified through the real GameGenerator → MissionGenerator pipeline on Enduring Resolve (miz carries `CVN-74 John C. Stennis`, 73X `STN`, ICLS 14, Link 4 336.4, ATC 308.000). Whether DCS renders and radiates it is DCS-only.
- **What CI cannot exercise:** the actual DCS kneeboard render of the auto-generated CV Operations Data page, and whether the boat's TACAN/ICLS/Link 4 beacons radiate on the curated channels for a real Hornet/Tomcat recovery (the ActivateBeacon/ICLS/Link4 commands are the same pydcs tasks as before — only the values changed — so the risk is low).
- **Setup:** any campaign with a vanilla carrier (Enduring Resolve fields the Stennis; any Caucasus CVN campaign works). Generate, slot a Hornet (or open the kneeboard as any deck aircraft), find the CV Operations Data page.
- **Pass:** the Callsign line reads the bare hull name (no `NNNN | ` prefix); TACAN reads the hull-flavored channel + boat ident (Stennis: 74X STN, or the nearest neighbor where the map owns the hull channel — 73X on Afghanistan since Bagram is 74X); ILS reads the hull-keyed channel (Stennis 14); Link 4 reads 320.x (336.x before 2026-10-10, see B213); ATC reads the stable 30x.000; the boat's TACAN needle/DME, ICLS bars, and ACLS lock actually work on those numbers; the same numbers come back on the next turn's mission.
- **Fail signature:** the id-prefixed name on the Callsign line (flagship naming didn't reach the unit — check `_flagship_name` / the duplicate guard); TACAN 1X with a changing ident (curated path not taken — the hull id isn't in `CARRIER_COMMS_PLANS`, e.g. a mod boat, which is by-design legacy); a dead TACAN needle on the curated channel (channel collision with a map beacon that `Beacons.iter_theater` doesn't know — mark it and re-pick the hull's channel); numbers changing between turns (persistence to the control point didn't stick — check `frequency`/`link4`/`icls_channel` on the CP in the save).

### B21 — Cross-package SEAD-before-strike coordination · §69 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-07-17; the pure window math and the scheduler wiring — ring matching, latest-provider windows, player/ASAP immunity, provider read-only, massing, the gate — are unit-tested in `tests/test_sead_strike_coordination.py`; whether the flown timeline actually reads "SEAD first, then the push" is Tacview-level
- **What CI cannot exercise:** a real generated mission where an AI strike package tasked into a defended area arrives AFTER the SEAD/DEAD package servicing that SAM is on station (Tacview timeline: HARMs/suppression first, bombers 2–10 min behind), instead of the old random spread that could send the bombers in half an hour early.
- **Setup:** any campaign where the AI plans SEAD/DEAD + strikes into the same defended area (`sead_strike_coordination` default ON). Generate a turn with a red SAM covering a strike target; check package TOTs in the ATO, then fly/spectate and read the Tacview.
- **Pass:** the ATO shows the strike/BAI/OCA packages targeting SAM-covered objectives with TOTs ~2–10 min after their covering SEAD/DEAD package's TOT (several strikes may share one window — the push); packages against undefended targets keep the random spread; a player package's TOT is never moved by this (and a player-flown SEAD still has AI strikes timed behind it).
- **Fail signature:** a strike still arriving before its SEAD with both AI (the ring match missed — check the SAM TGO's `max_threat_range` and that the SEAD's target is the TGO); strike TOTs pushed absurdly late (the window should clamp to `earliest_tot` — check `coordinated_strike_tot`); player packages rescheduled (the movability gate broke); mass mid-airs at the shared TOT (packages route separately, but if seen, widen `SEAD_WINDOW_LEAD` spacing per client or stagger within the window).

### B22 — COMINT collection: the campaign take (tiering + leak + reveal) · §70 · ⊘ RETIRED

**History:** built 2026-07-18; the tier gating incl. dead-net-beats-collector, the OFF exact no-op, the survivor requirement, drone eligibility, leak determinism, the reveal's range/known/`map_hidden` rules + re-init idempotence are unit-tested in `tests/retlab/test_comint.py` — the kneeboard render + the map snap are app-level
- **What CI cannot exercise:** the rendered COMINT block on a real Mission Info kneeboard page, and the map experience of a Tier-2 reveal (an amber suspected-activity circle replaced by the exact enemy symbol at turn start). An in-APP pass (no DCS flight needed beyond generating/ending turns).
- **Setup:** a COIN campaign (Enduring/Inherent Resolve — insurgent spawns are both sources and reveal candidates) with `comint_collection` ON (Campaign Management → Campaign features). Plan a drone or C-130J JAMMING sortie, end the turn with it surviving, open the next turn's kneeboard + map. Then kill every red comms/CC node (or on COIN, clear the concealed spawns) and end another turn.
- **Pass:** turn A (net up, no collector): the kneeboard COMINT block reads "Enemy net active … ambient take only". Turn B (collector survived): the block adds "Collection sortie banked a full take", an "Intercepted tasking traffic: …" line naming a real red package/objective with a ±30 min window, and — when an eligible concealed site sat within 60 km of a source — a "Transmissions localized: …" line with that circle now an exact symbol on the map (one site only). With `red_comms_net` also on, the block additionally lists the **active nets** (fixed C2 stations by name + frequency + area; each concealed spawn as "suspected clandestine net @ <freq> — <area> area" — NEVER the cell's identity or type; ≤5 lines + a "+N more" tail). Net dead: the block reads "Enemy C2 net silent — no COMINT take."
- **Fail signature:** a COMINT block while the net is dead (source walk broke); two circles snapping in one turn or a snap repeating after a cheat-capture/TGO-purchase re-init (the `comint_reveal_turn` stamp broke); a §50 convoy-ambush team appearing on the map (the `map_hidden` exclusion broke — nothing may telegraph those); the leak naming a different package after a mission re-generation (determinism broke); any COMINT output with the setting OFF.

### B23 — Red comms net: audible + DF-able enemy C2 · §70 · ⊘ RETIRED

**History:** 2026-08-05, user report `units-runway-generation-bf755e` — **the audible half is PROVEN**: "someone on saturday heard morse code". That is the CW clip keying from a live red C2 node through a cockpit radio, which is the leg no harness can model. **But it was heard on the PRE-band-discipline build** — the DM's own framing, "before we changed it off player freqs" — i.e. the net was audible partly *because* it was colliding with a briefed mission channel, which is exactly the defect the 2026-08-02 band-discipline change fixed (the 100 kHz `NET_GUARD_HZ` guard band + the `red_net_max_stations` cap). So this row does NOT carry over to the current build: the open question is now the opposite one — with the nets moved off every allocated frequency, **is the morse still findable when a pilot goes looking for it**, and does it stay off the briefed channels. Re-check = tune a DF-capable jet (F-4E / F-14 ARC-182 / F/A-18C UFC ADF / F-5E) across the UHF band, confirm the CW is audible and homes, and confirm no briefed channel carries it) (was ☐ UNTESTED, built 2026-07-18; the emitter's frequency plan — x.500 off-grid, GUARD skip, registry reservation, cross-mission determinism, collision probing — and the runtime invariants — grace, per-node stagger, loop+stop windows, `node_dead`, clean no-op — are pinned in `tests/missiongenerator/test_rednetluadata.py` + `tests/lua/test_rednet_runtime.py`; audibility, per-module DF needle behavior against a scripted transmission, and power reach are DCS-only
- **What CI cannot exercise:** actual cockpit audio (is the CW clip clearly receivable at the emitted power from realistic ranges), each module's ADF/DF needle behavior against a scripted looped transmission, and whether the windowed cadence reads as traffic rather than a beacon.
- **Setup:** any campaign with red `comms`/`commandcenter` TGOs (Red Tide post-lock is ideal — its 9-node C2 net). Turn ON `red_comms_net` (Mission Generation → Battlefield life; the "Red comms net" plugin ships enabled). Generate, then read the assigned freqs from dcs.log (`REDNET|: armed -- N net(s), first window in 180s: <name> @ 271.500 AM; …`). Fly a UHF-DF airframe (F-4E ADF mode / F-14 ARC-182 "V/UHF 2" DF / F/A-18C UFC ADF / F-5E radio-1 DF) toward the front and tune a listed frequency.
- **Pass:** morse beeps audible on the tuned freq during a window (~45 s roughly every 4–5 min per node) and silence between windows; the DF needle points at the node while it transmits and drops when the window closes; two nodes never key up in the same moment (stagger); killing the node ends its windows for the rest of the mission (`REDNET|: <name> is off the air` in the log); nothing ever transmits on a briefed blue channel. **The clandestine hunt (C2, a COIN campaign):** each concealed insurgent spawn transmits SHORT windows (~20 s) with LONG silence (~8 min), tagged "(clandestine)" in the arm log; a needle cut caught during a window points inside that spawn's dashed suspected-activity circle; killing the cell ends its net.
- **Fail signature:** total silence (check dcs.log for `REDNET|: armed` — absent = the setting/plugin gate; present but inaudible = the `l10n/DEFAULT` path or power too low — raise `powerW`, it is range not loudness, §51); a net on a briefed blue channel (the x.500 offset broke — check the emitted mhz values); the needle still pointing between windows (`stopRadioTransmission` failed — the loop never ended); all nodes keying simultaneously (the stagger broke); a dead node still transmitting all mission (the `node_dead` walk broke — check the unit names vs the `<name> object` static convention); a §50 convoy-ambush team transmitting or listed on the kneeboard (the `map_hidden` exclusion broke — nothing may telegraph those); a kneeboard nets line naming a concealed cell's identity (the clandestine label broke).

### B24 — Expanded F-4E Weapons Pack: ARM Weasel fits · §71 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B24 good") (was ☐ UNTESTED, built 2026-07-18; the (XW) selection incl. the AGM-78B preference, the editor-only HARM fit, the Shrike fallback, the editor hiding, and the 1988 era-gate tripwires are unit-tested in `tests/retlab/test_f4e_expanded_weapons.py` and the Red Tide no-preseed is pinned — whether DCS itself mounts and employs the injected ARMs on the Heatblur F-4E is mod/DCS-only
- **What CI cannot exercise:** the modded jet in DCS — whether the installed mod build actually accepts the AGM-78B/AGM-88C on stations 1/3/11/13 as generated (a mod update can rename/renumber stores), whether an AI Phantom employs them against emitters (the AGM-78 is a mod-defined missile — its seeker/guidance behavior is entirely the mod's), whether the AGM-78's per-target seeker-band `target_overrides` reach the miz, and the mod-off failure mode (stores stripped at spawn).
- **Setup:** a personal NEW game (any campaign whose blue faction carries the F-4E-45MC — e.g. a personal Red Tide) with the Mods-page "Expanded F-4E Weapons Pack" box **checked by hand** (preseeded nowhere — it is the DM's personal option, never the squadron build) and DSplayer's mod installed in that DCS. Add an F-4E-45MC squadron via the air-wing dialog (none is authored) and plan it on SEAD; confirm the Payload tab defaults to "Retribution SEAD (XW)" with 4 AGM-78B Standards and offers "Retribution SEAD HARM (XW)" (4 AGM-88C) in the list; fly or spectate it against an emitting red SAM.
- **Pass:** the Phantom spawns carrying 4 AGM-78Bs (rearm screen shows them mounted), SEAD/SEAD Escort/SEAD Sweep all default to their Standard-ARM (XW) fits, swapping to the HARM (XW) fit in the editor mounts 4 AGM-88Cs, an AI-flown flight launches its ARMs at emitters, and §54 scarcity debits the same `arm` family the Hornets draw from. On an otherwise-identical game with the box UNCHECKED: the same flight defaults to "Retribution SEAD" (Shrikes) and the payload editor lists no (XW) fits.
- **Fail signature:** Phantom spawns with EMPTY ARM stations (DCS stripped the stores — mod missing on the server, or a mod update changed the pylon acceptance; re-verify against the installed mod's lua, the §41 HDS drill); an (XW) fit selected in a mod-off game (the pylon gate broke — check `Loadout.pylons_allow` and that `eject_F4E` ran via `apply_mod_settings`); the AGM-78 flying dumb/never guiding (mod-side seeker behavior or the seeker-band settings never landed — check the unit's payload `settings` in the generated miz); AI SEAD Phantoms holding fire inside range (distinct from simply not being tasked — the F-4E's SEAD task priority is a deliberate 120, so it flies SEAD on frag/overflow, not first pick).

### B25 — Carrier deck decorations: campaign A deck dressing · §72 · ☑ VERIFIED

**History:** **capacity half CLOSED 2026-08-20** (DM verdict, LOCAL card 2 retired): the 2026-08-18 Syria turn parked 24 jets on CVN-72 plus 8 on LHA-1 with the decorations ON and every one launched, six-pack path never used — well past the 16 spots the follow-on worried about, so the decorations-off control run is moot. The `KNOWN_PARKING_SPOTS` gap below survives as a note, not a test. (was **capacity half never run — see LOCAL card 2**, added 2026-08-07: this row closed on the *appearance* symptoms only; the criterion's "a max-density cold spawn still fills every spot vs a decorations-off control" clause was not exercised, and `KNOWN_PARKING_SPOTS` is now known to hold 11 of the Supercarrier guide's 16 spots — 63.2 m of starboard deck under 52 of the 67 street placements has no table entry. Not a reopen.)) (2026-08-06, WATCH item 4, DM verdict "Passing" — **the 2026-08-05 symptom did not reproduce**: the street gear and LSO team sat on the deck, nothing floating, nothing visibly out of place. That closes DM work order #2 by non-reproduction, and it closes BOTH halves as *observed symptoms*. **Two honest caveats, neither of which reopens the row.** (1) **Scope** — one session, and the hull + street variant were not recorded, so this is 1 of 6 rotating `(carrier, turn)` variants seen; a float that is variant-specific could still be out there, and the standing ask if it ever resurfaces is unchanged: note WHICH hull and WHICH static. (2) **The code-level position drift is real and remains** — `CORRAL_SHIFT` is ~10 m aft / ~5 m outboard of the raw campaign A offsets and the two surviving geometry commits compound, so today's placement is deliberately NOT the raw campaign A reference. That was never observable in a single fly; the DM's verdict says it now *looks right*, so the drift is **known and accepted** rather than fixed. Do not "restore the raw campaign A offsets" on the strength of this row — both shifts were bought with a real interpenetration fix and re-seating would need re-validating against `KNOWN_PARKING_SPOTS`) (was ◐ PARTIAL — **SUSPECTED REGRESSION, reported 2026-08-05 `units-runway-generation-bf755e`** — the DM: "we had it nailed and its been slightly fucked up since". The feature's full commit history, oldest first, so the regression can be bisected against the state that was known good: **`957d04d46`** 2026-07-18 the original dressing (#648 — the "nailed it" build) · **`19b68e2ed`** 2026-07-18 launch-phase E-2C struck below before recovery (#649) · **`1821c4373`** 2026-07-18 flown falsification, cut the permanent static aircraft + harden the astern cone (#650) · **`3ad3a8e04`** 2026-07-18 astern cone v2, ship-relative closing + outbound roster (#651) · **`37de4c8e9`** 2026-07-21 remove the port junk row, it clipped a spawning Hornet on a flown CVN-71 (#722) · **`e40ee54fb`** 2026-07-27 pull the deck street gear back to the island, red→blue (#732). **Prime suspects, in order:** `e40ee54fb` is the most recent and the only one that MOVES the surviving gear (`CORRAL_SHIFT` (+30,−6) → (+9,−1), ~10 m aft / ~5 m outboard, `ISLAND_STREET_ENVELOPE` → (−65,−30,10,25)) and is therefore the likeliest cause of a "slightly off" look; `37de4c8e9` is the only one that REMOVES a placement. **DM's symptom, given 2026-08-05: "wrong place, floating in one case, just shifted out of place really from the original miz's we investigated."** That is TWO distinct defects and they need separating, because only one of them is a regression: **(1) POSITION DRIFT — the real regression.** The gear no longer sits where the campaign A extraction put it. Both surviving geometry commits moved it and the moves COMPOUND: `1821c4373`/`3ad3a8e04` era shifted the cluster +30 m forward off the raw campaign A offsets to clear the angled-deck foul line, then `e40ee54fb` pulled it back to `CORRAL_SHIFT` (+9,−1) — so today's placement is ~10 m aft / ~5 m outboard of raw campaign A, i.e. deliberately NOT the reference the DM is comparing against. `e40ee54fb` is the prime suspect and the fix is a decision, not a bisect: the shifts were each bought with a real clipping fix, so re-seating on the raw campaign A offsets must be re-validated against `KNOWN_PARKING_SPOTS` or it re-opens the interpenetration the shifts were for. **(2) FLOATING — probably NOT a positioning bug at all.** A static sitting off the deck is a LINK defect, not an offset one: §72 serializes links at three levels (`linkUnit` on the route point, `linkOffset` on the group, `offsets` on the unit), and a static that renders airborne usually means the vertical/link half resolved wrong rather than the x/y corral shift being off. Chase it separately from (1) — and get WHICH static and WHICH hull, since the decor rotates 6 street variants per (carrier, turn) crc32 seed, so a float that appears on one deck and not another is variant-specific. `git diff 957d04d46 HEAD -- game/missiongenerator/carrierdeckdecor.py` is the whole geometry delta) (was ◐ PARTIAL, built 2026-07-18; the parking-spot guard over every variant, the safe-envelope integrity, the hull gate + per-turn rotation determinism, and the three-level linked-static serialization are unit-tested in `tests/missiongenerator/test_carrier_deck_decor.py`; the dressing half flew — 22 statics registered per load across four 2026-07-18 loads, no further interpenetration after the permanent-aircraft cut — but the corridor respot false-tripped twice more and is reworked; re-fly owed on the v2 cone
- **What CI cannot exercise:** the linked statics actually riding the steaming carrier (offsets are re-derived per frame by DCS — a wrong link would leave gear floating in the wake), DCS's parking allocator with the dressing present (does a max-density cold spawn still fill every spot), and AI recovery taxi behavior around the island-street gear (the wiki says AI clips through statics, but "slowed taxi past the Patio→El 1 zone" is a documented near-miss).
- **Setup:** any carrier campaign (Scenic Route or a fresh PG naval game). Leave `carrier_deck_decorations` ON (Mission Generation → Carrier, the default). Generate a mission with several carrier cold-start flights (client + AI — the §64 deck policy fills spots), take off, and watch the boat through a recovery cycle. For the capacity check, plan enough carrier cold starts to demand the deep spots (6+ fixed-wing).
- **Pass:** tow tractors / P-25 / forklift / crane / deck hands visible in the corral forward of the island (NOT on the landing-area foul line) and the 4 LSO figures on the port-aft platform, all riding the deck as the boat steams (no gear left behind in the water, none sliding); every cold-start flight spawns at a real parking spot exactly as without the feature (no "flight delayed" that a decoration-off regen doesn't also show); AI recoveries taxi and park normally; next turn the street arrangement differs (variant rotation). **FIRST FLOWN 2026-07-18 (CVN-73, 30 late-activated deck starts): two FAILs, both root-caused + fixed same day** — (1) late-activated A-6s spawned INTO the then-permanent Seahawk statics (the SC manual's "blocked spot is skipped" claim is FALSE for late activations ⇒ the permanent static-aircraft class was REMOVED outright; positions kept as learned spot anchors); (2) the corridor E-2 was struck below at ~5 min (launch traffic turning back past the boat false-tripped the astern cone ⇒ hardened: 1000 ft ceiling + closing ≥30 kt + 2-poll debounce). **SECOND FLOWN (2026-07-18 night, session `c492faed`): the astern cone FALSIFIED AGAIN on both boats** — the 21:58 Scenic Route t3 flight (generated 32 min before the #650 merge, so it flew the PRE-hardening cone) struck GW's set at t+74 s (the first poll after grace), and the 22:42 Dust-to-Dust flight on the HARDENED build (armed line confirms 1000 ft) struck TR's at t+171 s. Tacview forensics on the GW flight: the qualifiers were the **aft parking rows themselves** — parked jets ride the steaming boat 130–170 m astern of the ship's pivot, DCS reports moving-deck units as `inAir()`, and world-frame closing = boat speed (22 kt on GW, under the 30 kt gate by 8 kt of luck; TR wasn't lucky). ⇒ **hardened v2 same night**: SHIP-RELATIVE closing + a 400 m deck-stamp floor (replaces the out-ranged 100 m) + a 600 s outbound roster (a unit seen on/over this deck cannot read as recovery traffic — a fresh launcher's low closing turnback is its own traffic); 4 new harness pins. **Re-fly owed on the v2 build.** Footnote: the Scenic Route save baked `coneAltFt: 3000` from the pre-#650 plugin.json (plugin option values persist per save) — reset in the plugin options UI or ignore; the v2 gates don't depend on the ceiling. **THIRD FLOWN 2026-07-21 (CVN-71 SKINK): the launch-phase PORT JUNK ROW clipped a spawning Hornet** — Tacview forensics on the flown miz measured a port-quarter parking spot at (−108,−34) (not previously known) and the port junk-row tractor stood 8.7 m from a Hornet spawned there. Root cause: the junk row was launch-phase in NAME but sat forward/port of the recovery-corridor keep-out box, in the port-quarter parking row. ⇒ **port junk row REMOVED**; launch-phase invariant tightened to "must fall INSIDE `LANDING_AREA_KEEP_OUT`" (guard-locked); (−108,−34) added to `KNOWN_PARKING_SPOTS`. Launch-phase is now the round-down E-2 only. **Same session, second finding — the STREET GEAR was out of position** (user annotated screenshot: circled the corral, X'd the gear): campaign A's by-the-island offsets (x −40..−74) rendered on the angled-deck foul-line strip. ⇒ the whole campaign A arrangement was **translated forward into the corral** (`CORRAL_SHIFT (+30,−6)` → x −11..−43, y +7..+20, ≥7 m clear of every spot; `ISLAND_STREET_ENVELOPE` moved to the corral, position confirmed against a top-down deck map built from the lua geometry). **Re-fly owed.** **The launch-cycle and recovery-cycle sets were REMOVED 2026-08-20** (DM call), with the `deckdecor` plugin. Nothing is struck below, nothing is spawned forward, and there is no round-down E-2C. The dressing you see at mission start is the dressing that is there when you come back to the ramp. **Fail signatures:** anything standing in the landing area or on the round-down at all (a data regression -- the keep-out is guard-tested); a static vanishing mid-mission (nothing should remove one now).
- **Fail signature:** gear floating at the mission-start anchor while the boat sails away (the linkUnit id didn't match the hull — check the route-point `linkUnit` against the carrier's `unitId` in the miz); a cold-start spawn missing/delayed vs a decoration-off control (a static ate a spot — re-measure `KNOWN_PARKING_SPOTS`, the envelope claim is broken); statics half-sunk in the deck or clipped into the island (offset frame error — check the offsets sign convention against an campaign A miz); AI recovery taxi jamming against street gear it should clip through.

### B26 — Single player ignores "Spawn player flights immediately" · §64 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B26 good") (was ☐ UNTESTED, built 2026-07-18 off the user call — the setting is a multiplayer option, so a mission with fewer than two player slots now ignores it: the lone player flight is delayed to its planned start time, and a delayed cold player flight late-activates at its planned engine-start time instead of idling uncontrolled from t=0; the decision matrix — cold/warm/runway late activation, the ten-minute rule, the MP and AI no-changes — is unit-tested in `tests/missiongenerator/test_carrier_deck_policy.py`. How DCS seats the SP pilot in a late-activated Player-skill flight is DCS-only.
- **What CI cannot exercise:** the DCS single-player experience around a late-activated Player-skill group — where the player waits until activation (map/spectator view), whether they are seated in the cockpit the moment the group materializes, and that the §58 briefing card + beep fire on that late birth.
- **Setup:** any campaign, exactly one player slot in the mission (one client seat, cold start), `never_delay_player_flights` left ON (the default). Plan the package so the flight's start time lands ≥ 15 min after mission start (a mission with other packages does this naturally — check the flight's startup time in the package dialog). Take off and note the miz clock when you reach the cockpit. Re-fly warm/runway variants if convenient; regenerate with a second player slot as the control.
- **Pass:** the mission runs from its start time without the player's jet existing; the player is placed in the pit when the group activates at the flight's planned startup time (matching the package dialog, not t=0) with enough time to start up and make the planned takeoff; the §58 briefing card fires on the late slot-in; the two-player-slot control generation spawns everyone at mission start exactly as before.
- **Fail signature:** the SP pilot stuck with no way into the mission until (or even after) activation — blocked at role select or stranded spectating with no seat handoff (if so, the cold branch of the SP bypass must fall back to the uncontrolled spawn path); the player in the pit at t=0 anyway (the `use_client` thread into `WaypointGenerator` broke); the flight never activating at all (activation trigger missing, or the `CoalitionHasAirdrome` guard false because the departure field flipped); the player materializing with too little time to cold-start before the planned takeoff (the WaitingForStart hold would be takeoff-relative rather than startup-relative — needs a startup lead).

### B27 — Dialogs clamped to the screen + Edit Flight dead space · §28 · ☑ VERIFIED

**History:** 2026-08-05, user app pass `pr-merge-code-audit-7e8b4c` — "B27 is good") (was ☐ UNTESTED, built 2026-07-19 off the "windows are clipping / UI scaled screwed up" report, screenshot showing the Edit Flight tab bar flush against y=0 with no title bar; the pure fit geometry, the over-tall-minimum relaxation, and the already-fits no-op are unit-tested in `tests/test_screenfit.py`, and the whole path was verified offscreen against the reported 1706x928 display — every Edit Flight dialog 1115 → 835-893 px fully on screen, and a deliberately 3000 px dialog clamped through the real `ScreenFitFilter`. `qt_ui` is not CI type-checked and Qt's window-frame metrics only exist on a live desktop, so the visual result is app-only.
- **What CI cannot exercise:** real window-frame/chrome sizes (the offscreen platform reports no frame, so the chrome subtraction inside `fit_to_available_screen` never runs against a real title bar); per-monitor DPI when the two displays are scaled differently (the fit happens on **show** only — a dialog dragged to the other monitor is deliberately not re-fitted); and whether any dialog now opens visibly *smaller* than it should on a large display.
- **Setup:** on the monitor where the clipping happened, open **Edit flight** (double-click a flight) and look at the title bar. Then walk the other dialogs — Settings, Air Wing, Air Wing Configuration, Package, Base menu, Ground object, Transfers, Intel — on **both** monitors. Inside Edit flight, switch General → Payload → Waypoints.
- **Pass:** every dialog opens with its title bar and its bottom edge on screen, on both monitors; the Edit Flight General tab no longer shows a wide empty band under Custom Name; switching to Payload/Waypoints keeps every control reachable (the pylon list may compress, but nothing may be cut off with no way to reach it); no dialog opens comically small; and `dcs.log` carries no `cannot fit the available screen area` warning — if it does, that dialog's *layout minimum* genuinely exceeds the display and needs a scroll area, so note which one (the warning names the class).
- **Fail signature:** a dialog still opening off the top (the fit did not fire — confirm `ScreenFitFilter` is installed; non-`QDialog` windows are skipped by design); a dialog opening far smaller than its content with controls unreachable and no scrollbar (the clamp bit below the layout minimum — the log warning names it); the Edit Flight window jumping size when you switch tabs (the `sizeHint` override must not force a resize); a dialog that used to be resizable refusing to grow (the minimum relaxation is one-way within a session — reopening restores it, but note it).
- **Follow-up landed 2026-07-19 (same day, off the re-flown report "you prefer tall over wide" with the payload rows visibly clipped):** the clamp fired but bit below the Payload tab's layout minimum — exactly the fail signature above — because the tab was one tall column (F-15E: 962 px wanted, **901 px minimum**, 880 available). It is now two columns with a scrolling pylon list and width-bounded dropdowns: **1553 px wide × 332–552 tall, min 346–360**, measured across every airframe in the reporter's save. Re-check on the app: the Payload tab reads as two side-by-side columns; a full loadout is visible without scrolling; **no store name is clipped top or bottom** (the original symptom); the store dropdown still shows full weapon names when opened; and the dialog is not noticeably wider than before.

- **Follow-up landed 2026-08-23 (report: "the new campaign popup renders off screen", screenshot of the New Game wizard with the Back/Next/Cancel row under the taskbar):** the filter fits a dialog on **Show**, and a `QWizard` is at its smallest then. New Game showed the 500x461 intro page, was fitted and centred at that size, then grew to 1409x963 on the theater page keeping the same top-left — 36 px past the bottom of a 2560x1392 usable area. `NewGameWizard.resizeEvent` now re-fits on every resize once visible; measured page by page on the real display, 5 pages off-screen → 0. Re-check on the app: open **New Game**, click Next through all six pages and back again, on **both** monitors — the Back/Next/Cancel row and the title bar stay visible the whole way, the campaign names in the theater list are not truncated, and the window does not jitter or shrink as you page. This is the general blind spot, so watch for it on any dialog that grows after it opens (Air Wing Configuration when a squadron list loads is the likely next one).

### B28 — Native DTC data pre-population (F/A-18C + F-16C) · §74 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ◐ PARTIAL, 2026-08-05, user pass `units-runway-generation-bf755e` — "I do not notice any issues yet", so nothing is broken in normal use, but a clean flight is weak evidence for this row: the cartridge is only *observable* when you go looking at it, and the genuine unknown was never the happy path. **Still owed, specifically:** does `AutoLoad` fire on the two §64 spawn paths that differ from a plain ramp start — an **uncontrolled carrier client** and a **late-activated delayed flight** (the reference mission this was reverse-engineered from used plain ramp starts, so those two are unproven) — and does the DTC route's target/landing steerpoint altitude match the miz rather than re-floating to track altitude (the C10 tie-in). Plus an in-app eyeball of the DTC tab's per-flight overrides) (was ☐ UNTESTED, built 2026-07-19 by replicating the mechanism of a hand-built MP mission flown 2026-07-18 that pre-loaded the user's Hornet with zero pilot action — in-miz `DTC/*.dtc` JSON + per-unit `DTC.Cartridges`/`AutoLoad`; the cartridge shapes are locked against the ME's own DTC editor schemas in `tests/missiongenerator/test_dtc.py`, and the whole chain was headless-verified on the flown Red Tide saves — 3 cartridges bound to 10 client units, recon fog holding: 0 threat rings on turn 1, exactly the 5 TARPS-confirmed sites on the flown turn-2 save
- **What CI cannot exercise:** whether the jet's **AutoLoad actually fires on our §64 spawn paths** — the reference mission's jets were plain ramp starts, ours include uncontrolled-at-t=0 carrier clients, late-activated delayed flights, and air starts — and how each cartridge section renders in the cockpit (the schema is editor-exact, but the jet's own loader is compiled and unverifiable outside DCS).
- **Setup:** any campaign with blue client Hornets and/or Vipers (Red Tide is ideal — carrier + land fields, BARCAP waves, two tankers + AWACS). Leave `dtc_data_cartridges` ON (RetLab Features → Cockpit & kneeboard, the default). Plan a player Hornet package (and a Viper one if fielded), generate, and slot in cold on the ramp; re-fly once as a carrier cold start and once TOT-delayed if the §64 paths are in play.
- **Pass:** with **no MUMI/DTC-page interaction**: COMM1/COMM2 presets carry the mission freqs with names matching the kneeboard comm plan (flight callsign, MAGIC/ARCO/SHELL, DEP); the flight's steerpoints are loaded with names and the route sequence shows the planned ETAs; on a carrier flight the TACAN/ICLS/ACLS are pre-tuned to the §65 boat card; the SA page (Hornet) shows the FLOT line, friendly CAP + tanker/AWACS racetracks, and MEZ rings only for sites the campaign map shows exactly; the Viper HSD shows the FLOT GEO line and threat rings, and the extra steerpoints carry the tanker/AWACS/CAP anchors. MP: a second client gets the same pre-load with no file distribution beyond the server's mission download.
- **Fail signature:** the jet spawns with stock defaults and the DTC page lists the cartridge un-loaded (AutoLoad didn't fire on that spawn path — note which §64 path; if only late-activated/uncontrolled spawns fail, the fix direction is a spawn-type carve-out, not a format change); the cartridge missing from the DTC page entirely (the unit block or the `DTC/` file didn't survive — check the generated miz zip for `DTC/Retribution <callsign>*.dtc` and the unit's `["DTC"]` block); a section loading garbled (schema drift vs a DCS patch — re-diff `CoreMods/aircraft/<type>/DTC` against the design note); SA/HSD elements invisible despite loading (the `Default_*` style indices — must be 1, not the NONE index); an exact enemy SAM ring for a site the map only shows as a suspected circle (fog leak — the `known_for` filter regressed, fix before anything else).
- **CJS Super Hornet bullet — CLOSED 2026-08-22 (feature removed).** The Super Hornets no longer take a cartridge: their descriptor has no SA table, and the comm presets and route already reach them through the miz. Nothing to check.
- **FLOWN 2026-08-19, session `dtc-work-retrospective-c1328a` — the Viper HSD picture is confirmed good.** Screenshot from the cockpit shows the route line drawn through its steerpoints with a triangle at the target, and the Destination steerpoints rendering as white 3-character labels (`FOB`, `FO2`, `FO3`, `FO4`, `SHA`, `GHA`, `KOB`, `BAG`) — so `MPD.DEST` loads, the labels fit, and the collision suffix works. The DM's verdict on the Viper and Hornet cartridge changes together: "good and confirmed they look great". **Still owed on this row:** the Zulu push-time check below (that fix landed after this flight, so it needs a regenerated mission) and the Viper CMDS check. The Hornet A/A waypoint was confirmed separately the same day — see its bullet. **Looked at and left alone (DM call, same day):** several bases named `FOB <x>` reduce to the same first three characters, so they read `FOB`/`FO2`/`FO3`/`FO4` rather than naming the place. The labels are unique and correct and the full name rides the `note` field, so this is not worth a naming heuristic. Do not re-raise it.
- **Push times read Zulu (added 2026-08-19, the reported TOT defect):** this is the one to check first on any DTC flight. On a client Hornet or Viper, the cartridge's steerpoint ETA/TOS must match the jet's own clock — Hornet: the TOT on the HSI/DATA page against Zulu time in the bottom left of the HUD; Viper: the CRUS TOS DED page, where desired TOS sits beside System Time and the required ground speed should read sane rather than pegged. Cross-check against the kneeboard: the Hornet-family kneeboards already print Zulu (`utc_kneeboard`), so those two should now agree exactly. Both jets' cards now carry **both** clocks (`utc_kneeboard`), so the Zulu figure and the cockpit should agree exactly while the local figure still matches a non-Zulu wingman's card. **Check the flight-plan table, not just the BLUF** — until 2026-08-20 only the BLUF's TOT converted, and the two blocks on the same page read a whole map offset apart. Tables stack Zulu under local, the BLUF and the package TOT parenthesise it, and the tanker/AWACS cells indent it under the TOT. A Hornet or Viper card showing a bare `15:12:14` anywhere means the annotation stopped reaching that block again. Fail signature: ETA/TOS off by a whole number of hours equal to the map's offset (the conversion regressed or was applied twice — Caucasus +4, Syria +3, Marianas +10, Nevada −8); a required ground speed pegged at max or the TOS field blank (negative/invalid TOS, meaning the value landed behind the jet's clock).
- **Hornet COMM section dropped (2026-09-13, the fork reflects upstream #966):** the
  F/A-18C cartridge no longer carries COMM1/COMM2; the presets come from the mission's
  own Radio table, which is the same frequencies on the same channels, without the
  callsign names. Expected: the mission frequencies on the kneeboard's channel numbers
  with the jet's stock channel names. Fail signature: empty or default presets. The
  named-preset half of the Pass line above is history.
- **Viper COMM section dropped (2026-08-22):** the F-16C cartridge no longer carries
  COMM1/COMM2; the presets come from the mission's own Radio table, which is the same
  data. Expected: no change in the cockpit. Fail signature: empty or default presets
  on a Viper, which would mean the miz Radio table stopped reaching the jet — a
  channel-allocator problem, not a cartridge one.
- **Own orbit only (changed 2026-08-22, UNTESTED):** the SA page's CAP points are now
  the flight's OWN orbit first — its racetrack, or a stand-in at the hold point when it
  flies none — then the tankers and AWACS. No other flight's CAP station appears. On a
  strike Hornet, CAP point 1 should sit on the briefed hold and be the one selected at
  spawn; on a BARCAP Hornet it is your own station. Viper: STPT 21 is the same point.
  Fail signature: a CAP point on another flight's station, or none at all on a flight
  whose plan has a hold.
- **The Viper DEST page shows the enemy field you are working over (added 2026-08-22,
  UNTESTED):** on an OCA or strike Viper against a target within 10 NM of a red
  airfield, DEST 82 (right after the divert) is that field. Fail signature: it is
  missing, or it displaced the briefed divert from DEST 81.
- **Hornet A/A waypoint — VERIFIED 2026-08-19**, session `dtc-work-retrospective-c1328a`: "Hornet a/a is confirmed". The bullseye is designated at slot-in with no cockpit interaction. Original criterion, kept for regressions (from the FA-18C EA guide p158): on a client Hornet or Super Hornet, with no cockpit interaction, the A/A waypoint should already be designated at the bullseye — check the HSI/DATA/WYPT page shows A/A WP boxed on the bullseye's steerpoint number, and that the A/A radar format draws the bullseye symbol with A/A-waypoint-to-ownship bearing/range at the bottom centre. A diamond means the bullseye is also the selected waypoint; a circle means it is not — both are correct. Fail signature: no A/A WP designated (the `AA_Waypoint` block was rejected, or the plan carried no BULLSEYE waypoint — check the kneeboard's post-landing rows first); the A/A WP pointing at a route steerpoint instead of the bullseye (the number tracking in `_build_wypt` regressed); or a bullseye symbol at the map origin (designated against an empty slot, which is what leaving the stock 59 enabled would do).
- **Viper cockpit checks (added 2026-08-18, from the F-16C EA guide + the live descriptor):** five things to look at on a client Viper, none of which CI can reach. All five close in one sortie. **(1) CMDS.** Guide p126 warns the CMDS MODE knob must be in STBY before an MPD upload "to prevent erroneous data entry into the CMDS settings" — `AutoLoad` fires with no pilot action, and our steerpoints live in MPD (`data.MPD.CMDS` is a real section we deliberately leave empty). Pass: the CMDS page reads ED's stock values — **BINGO chaff 10, flares 10, other 0/0, with FDBK, REQCTR and BINGO all on; MAN1 chaff and flare both burst qty 1 / burst interval 0.020 / salvo qty 10 / salvo interval 1.0** (`MPD/CMDS_defs.lua`) — and the DTE page carries no advisory. Fail signature: altered CMDS programs, or a DTE advisory naming the MPD partition — the fix direction is then to stop shipping an MPD partition we do not fully own, not to change the steerpoint format. **(2) Steerpoint sub-types.** The HSD should draw the target steerpoint as a triangle and the ingress point as a square, transit points as circles. Fail: every point a circle (the `type` field was rejected — re-diff `NAV_PTS_Types` in `CoreMods/aircraft/F-16C/DTC/MPD/NAV_PTS.lua`). **(3) Destinations.** The DEST page should list the friendly recovery fields with the briefed divert first, three-character labels (`KUT`, `BAT`), and each field's real elevation; the HSD draws them as white 3-character text. Fail: an empty DEST list (the section was rejected — note that ED's own example cartridges nest CMDS at `data.CMDS` rather than `data.MPD`, so a nesting mismatch is the first thing to suspect), a red-held or cratered field offered as an alternate, or labels longer than three characters. **(4) Push times.** The CRUS TOS DED page should show a desired TOS matching the kneeboard exactly (both are Zulu as of 2026-08-19) and a required ground speed in a sane band rather than pegged. **Requires a mission regenerated after that fix** — cartridges are baked at generation, so an existing .miz still carries the old local times. **(5) Route cap.** A route longer than 20 legs now stops at STPT 20 on purpose (the jet auto-sequences only from 1-20, guide p223); the tanker/AWACS/CAP anchors must still be present from 21 up. Fail: a long route that swallowed the anchors, or steerpoints past 20 that the jet will not sequence to.
- **App-side (the planner controls, added same day):** open Edit Flight on a Hornet/Viper flight — a **DTC tab** appears (and does NOT appear on an F-14/other airframe); the master combo reads "Follow the Pre-load DTC data cartridges setting (currently on/off)" matching the real setting; picking "No cartridge for this flight" greys the contents group; re-open the dialog and the choices survived (they pickle with the save). Then generate: a "No cartridge" flight's jet has no cartridge, a section unticked (e.g. threat rings) is absent from the cockpit while the rest load, and "Build a cartridge" wins over the campaign toggle OFF. Fail signature: the tab on an unsupported airframe (the `CARTRIDGE_BUILDERS` gate broke); choices reset on dialog re-open (the options aren't reaching the Flight); an unticked section still loading (the builder omission regressed — `tests/missiongenerator/test_dtc.py` should have caught it).

### B30 — CTLD paratroopers (fixed-wing air assault: player + AI C-130 paradrop) · §76 · ☑ VERIFIED

**History:** 2026-08-11, user pass `civilian-traffic-stalling-1f2eba` — "Confirmed working, the AI drop works and the troop capture/land in the correct area". **Both legs are now proven.** The AI leg was chased with in-plugin diagnostics after a first flight where an AI C-130 overflew its zone without releasing: the mission-file side was ruled out (paradrop flag, target zone, preload all correct, `ASSAULT` waypoint 0 m from the zone centre at 304.8 m RADIO), and the instrumented re-fly showed the gates progressing cleanly — plan armed for all 4 units → `reads as on the ground` → preload → release. The DCS-native capture event fired at FOB Nawa with a blue `Soldier M4 GRG` as initiator, so the dropped stick genuinely took the objective. **Three defects the flight exposed, all fixed in [#834](https://github.com/BradySox/RetLab/pull/834):** the diagnostic throttle compared whole messages so the live-distance `inbound` line logged every poll (thousands of lines under time acceleration); `ctld.checkAIStatus` re-loaded any empty AI transport parked in a pickup zone every 2 s, so a spent C-130 announced "loaded troops" to the whole coalition forever; and fixed-wing assaults fragged two-ship when one paradrops the entire stick. **Still open, tracked separately:** the capture did not commit to the campaign — `state.json` carried `…||2||FOB Nawa` and replaying it through the parser yields the correct `BaseCaptureEvent`, but the live `commit_captures` ran empty, apparently against a stale debriefing from a hung session. Watch for that on the next pass) (was ◐ PARTIAL 2026-08-05, user pass `units-runway-generation-bf755e` — "Human it works, have not tested AI"; was ☐ UNTESTED, built 2026-07-19 off the "add paratroopers via CTLD" ask; the planner gate + both layout shapes are unit-tested in `tests/ato/flightplans/test_airassault.py`, and the whole Lua runtime — player jump via the stock Unload menu, descent-delayed ground spawn at the velocity-projected point, the 3,000 ft player ceiling, ground/helo fall-through to stock CTLD, the AI one-shot zone release, and the late-activation preload retry — is harness-pinned in `tests/lua/test_ctld_paradrop.py` (9 cases). What no test can model is the DCS AI actually flying the run-in and the dropped infantry behaving

### B33 — Decoy suspected-activity zones · §79 · ✅ CLOSED (feature removed 2026-08-18) (was ☐ UNTESTED

The recon rework removed §79 outright. Decoys only worked because real field forces were
also drawn as suspected-activity circles; real forces now draw exact markers, so a lone
circle would obviously be fake. Nothing to fly. See features doc §79 and §3.

### B34 — Campaign filter & sort in the New Game wizard · §28 · ☑ VERIFIED

**History:** 2026-08-05, user app pass `pr-merge-code-audit-7e8b4c` — functional, no defects reported; user's read of the feature itself: "kinda useless really" — a value judgment on the upstream #908 adoption worth remembering if it ever grows, not a fail) (was ☐ UNTESTED, adopted 2026-07-26 from upstream PR dcs-retribution#908, taken over the fork's bespoke era plumbing; the game-side predicate `Campaign.matches_era` is unit-tested and the Qt modules import clean, but `qt_ui` is not in the CI mypy path and the campaign-list item build needs the DCS install dir, so the whole wizard page is app-only
- **What CI cannot exercise:** that the "Filter && Sort Campaigns" group renders and lays out sanely on the Theater page, that the Version/Map dropdowns are populated from the loaded campaigns (and that a `(0, 0)` unknown version is skipped), that each of the three sorts reorders the list, that the filters **compose** rather than clobber one another, and — the real risk — that pressing through the wizard starts the campaign actually highlighted, now that upstream removed the `selectedCampaign` wizard field and `accept()` reads `campaignList.selected_campaign` directly.
- **Setup:** open **New Game** → Theater page. Exercise Version, Map, Sort by, and "Show incompatible campaigns" individually and in combination. Then pick a campaign that is *not* first in the list, press through, and confirm the game that starts is the one selected. Separately, take the Introduction page's **Vietnam** card (checklist L5) and re-enter the Theater page each time.
- **Pass:** the group renders without clipping the campaign list (§28's screen-fit work applies); each filter narrows the list and each sort reorders it; combining filters ANDs them and none resets another; the Vietnam card's era filter survives touching the other controls; and the campaign that starts is always the highlighted one.
- **Fail signature:** the wizard starts the wrong campaign (the `selectedCampaign` field removal mis-wired — this silently falls back to `campaigns[0]`); changing the "show incompatible" checkbox resetting the version/map/era criteria (something bypassed `on_filter_changed`); the Vietnam card listing non-Vietnam campaigns after touching a dropdown (the era criterion isn't surviving `set_filters`); an empty list selecting nothing and the page erroring (upstream guards the first-row selection on `rowCount() > 0` — a regression here would throw).

### B35 — Air-defense class rows are filters of the "Air defences" master · §19 · ☑ VERIFIED

**2026-08-17 — VERIFIED on the DM's call ("B35 good").** WATCH item 2, pulled from the parking lot the same day and closed on the first look. The panel render, the class-row greying and the stored-state migration are the parts CI cannot reach, and they behave.

**History:** built 2026-07-29 off a flown report that read as a §3 fog bug — "with reveal fog of war on, SAM sites are showing nothing at the actual location, and the only way you can see it on the map is by hovering on the circle". Root cause was NOT fog: the campaign save carried `airDefenses: false` with all four class rows false, and those five were the only layers drawing an air-defense marker, so 54 AD sites and 25 §3 concealed circles went undrawn while *Enemy SAM threat range* — a separate layer over the same TGO slice — kept drawing the rings. Recon fog + the reveal overview were both verified CORRECT headlessly on the reported save. The filter semantics are unit-tested in `client/src/components/tgoslayer/TgosLayer.test.tsx` (5 cases: all-classes, narrowed, task-less exclusion, category enforcement, exclude flag) and the client passed tsc + the full jest suite locally — but the panel render, the greying, and the stored-state migration are app-only. **Needs the CI client rebuild.**
- **What CI cannot exercise:** that the four class rows visibly grey out and refuse clicks while "Air defences" is unchecked; that a stored layer blob which ticked a class row with the master off comes back with the master ON (`normalizeAirDefenseFilters`) rather than an empty map; and that no site ever draws two stacked markers.
- **Setup:** load any campaign with air defenses (Red Tide). Open the map layers panel → **Air defences** group. (a) Untick **Air defences** — then tick **Enemy SAM threat range** in *Enemy intel*. (b) Re-tick **Air defences**, leave all four class rows unticked. (c) Tick **LORAD** only, then **LORAD + SHORAD**. (d) With LORAD ticked, untick the master. (e) Hover one SAM site's icon and its threat ring.
- **Pass:** (a) no air-defense icons *and* the four class rows are greyed/unclickable; (b) every air-defense site draws exactly ONE icon; (c) only LORAD sites, then only LORAD + SHORAD sites; (d) rows grey again and the icons vanish; (e) one tooltip per hover, and the ring-hover highlight blob sits under the site's icon, not on empty ground. Also confirm the §3 concealed "suspected activity" circles for `aa` sites appear with the master on and fog intact.
- **Fail signature:** two identical markers (or a doubled tooltip) on a class-filtered site — the master and a row are both rendering a layer again; a class row still clickable with the master off; ticking a class row showing *nothing* (the task string no longer matches `task[0]`, i.e. the `GroupTask` tuple serialization changed); a known task-less air-defense site appearing while a class filter is active (a site blue has not engaged carries no class and shows under every filter, by design since 2026-10-11); or the map coming back empty on first load after upgrade (the normalize migration mis-wired).

### B36 — Super Hornet Navy bomb case: the re-authored all-Navy strike load · payload data · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "b36 good") (was ☐ UNTESTED, built 2026-08-02 off the "the carrier should be using the navy version of bombs" ask. The audit found the fork's fits already Navy-correct everywhere else — the player Hornet and the Bombcat ship `GBU_31_V_2B`/`_V_4B`, the Harrier ships `GBU_32_V_2B`, and DCS models no service split at all for GBU-10/12/16, GBU-38 or Mk-82/83/84 — so the only offenders were the CJS Super Hornet's `Retribution Strike` + `Retribution OCA/Runway`, which flew 4× **GBU-31(V)3/B** (Air Force, green case). CJS clears the Navy `(V)4/B` on **only its two midboard stations** (verified against the installed mod's own `FA-18EFG_HARDPOINTS_V2.lua:479,753`), so a straight 4× swap is impossible; the fits are re-authored to 2× GBU-31(V)4/B on the midboards (STA 03/09) + 2× GBU-32(V)2/B on the outboards (STA 02/10) — same weapon count, all white case, 6000 lb vs the old 8000 lb. The station math, the pylon legality of all four stores, and the fork-wide "no AF case where the Navy twin fits" sweep are unit-tested in `tests/retlab/test_navy_bomb_variants.py` (the sweep was confirmed to fail on the pre-fix data). Both stores keep the surrounding fits' `MDRN_B_A_PGM_TAILONLY` / `FMU139CB_LD` settings block unchanged.
- **What CI cannot exercise:** whether DCS/CJS actually hangs all four stores. The pylon tables and the mod's `forbidden` lists were both checked in each direction (the midboard `(V)4` forbids only the *midboard* BRU-55 GBU-32 pairs, not the outboard singles), but CJS drives several physical stations from more than one pydcs pylon index, so a station collision is the live risk — and DCS strips an illegal store **silently**, leaving a naked jet with no error anywhere.
- **Setup:** a game with the `fa_18efg` mod on and a Super Hornet squadron. Plan (or let the AI plan) a **Strike** and an **OCA/Runway** package off the boat. Open the payload editor on one to eyeball the fit, then fly/observe the spawned jet.
- **Pass:** the jet spawns carrying **2× GBU-31(V)4/B** (white case, 2000 lb, midboard) **+ 2× GBU-32(V)2/B** (1000 lb, outboard) — four bombs, all white — with the AI able to release them on the target.
- **Fail signature:** fewer than four bombs on the jet (a store was stripped — station collision or a stale CLSID after a CJS release); any green-cased bomb still present (a fit was missed, or the DM's own `Saved Games/.../UnitPayloads` overrides the shipped preset, which takes priority — check there first); the jet spawning clean (both midboard stores collided); or the AI carrying but never releasing (the carried-over `NFP` fuze settings don't apply to these stores — drop the `settings` block and retest).

### B37 — Navy white bomb casing across the carrier air wing · payload data · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "b37 is the same as b36", i.e. passed on the same look; the two rows are halves of one ask and the white casing is visible on the same jets) (was ☐ UNTESTED, built 2026-08-02, second half of the same ask — "I still want white 500 and 1000". The white body is NOT a store: it is the per-loadout visual setting `NFP_VIS_DrawArgNo_57` (1 = Navy white, 0 = green) written by the ME's weapon-settings panel. Mechanism confirmed two ways — ED's own `CoreMods/aircraft/F14/UnitPayloads/F-14BU.lua` sets `1` on every Bombcat bomb, and a DM-built test miz carried the same `{BRU55_2*GBU-38}` twice at `1` and `0`, which also proved the **Hornet and the CJS Super Hornet both honour it**. Applied to every bomb entry on the US Navy/USMC strike jets: `FA-18C_hornet`, `FA-18E`/`F`, `AV8BNA`, `A6E`, `A-7E`, `F-14A-135-GR`/`Early`/`F-14B`, `F-14BU`. **Only the casing key is written** (DM call — "keep everything default besides the color"): an entry with an existing settings block gets the one key set/inserted and nothing else touched, an entry with none gets a block containing only that key, so fuze type, arm/function delay and preset id all stay at the DCS default. A first cut that authored full ME-style blocks per preset was reverted for silently introducing fuzing settings onto airframes that never had any. Excluded on purpose: `F-14A-95-GR` (Export/Iranian Tomcat), the VSN/VWV mods (wrong nation; the coating postdates Vietnam), cluster munitions (Mk-20/CBU-* declare `Get_Fuze_GUISettings_Preset` — fuze only, no visual section), and `{BRU-32 GBU-24}` (no observed exemplar). Guards in `tests/retlab/test_navy_bomb_variants.py`: the key may be absent but never `0` on a Navy jet, plus a floor list pinning the jets this was asked for — both confirmed to fail when reverted.
- **What CI cannot exercise:** the only thing that matters here is what the bomb *looks like* hanging on the jet, which no test can see. Also unmodelled: whether a settings block containing **only** the casing key is honoured on stores that previously had no block at all (the alternative — authoring a full block — was rejected as a behaviour change, so "setting ignored, bomb stays green" is the accepted downside), and whether the CJS mod stores honour the key on the *specific* GBU-31(V)4/GBU-32 stations B36 introduced (the DM's miz proved CJS honours it on its GBU-12 and GBU-38 racks, not these).
- **Setup:** spawn each Navy jet on a bombed-up preset — Hornet Strike/OCA, Super Hornet Strike/OCA, Harrier, A-6E, A-7E, and a Tomcat with GBU-12/16 — and look at the ordnance externally. Then drop at least one bomb per airframe on a target.
- **Pass:** every bomb hangs in the **white** thermally-protected body, and each one still fuzes and detonates normally on release.
- **Fail signature:** a green-bodied bomb on any of those jets (either the store has no visual section, or a key-only settings block isn't enough for that store — remove it, or fall back to a full ME-written block for that one store); a bomb that hangs correctly but **fails to detonate or arms wrong** (unexpected, since no fuze key is written — but if it happens, delete the added `settings` block, which restores the pre-2026-08-02 state exactly); a weirdly-deformed or half-drawn store (draw arg 57 means something else on that model — the AIM-9 seeker case, which is why the pass is gated to bomb CLSIDs only); or the setting silently ignored after a DCS/CJS update (re-check the store's declaration for `Get_Combined_` vs `Get_Fuze_`).

### B38 — Mixed-hull ship groups · §80 · ☑ VERIFIED

**History:** 2026-08-05, flown Marianas 2027, Tacviews `Tacview-20260805-190738` + `-203549`, session `pr-merge-code-audit-7e8b4c`: **20 of 26 naval groups generated MIXED** — e.g. `WEEVIL (Escort)` = PERRY ×2 + TICONDEROG + Arleigh Burke IIa, `GROUPER (Escort)` = CH_Type054B ×2 + Type052D + Type_054A, `WORM (Escort)` = CH_Arleigh_Burke_IIA + PERRY + Burke ×2 — while every carrier/LHA group stayed **uniform**, which is the designed single-unit flagship slot, and **no patrol boat, submarine or second carrier leaked into a surface screen** (the family restriction held). **The DCS-only unknown is ANSWERED: a mixed-class group sails as one formation.** The widest gap between any two hulls of the same group was measured at t=300/1500/2800 s and is **constant to 2 decimal places** across the whole 48-min mission — 1.80–2.16 km for the §87 racetrack groups, 2.89–2.90 km for 2-ship escorts, 16.96–17.00 km for the 4-ship carrier screens (their authored ring geometry) — so no drift, no bunching, no stragglers, and every unit of each group logged an identical path length. Mixed hulls at mixed top speeds held station exactly as uniform ones did.) (was ☐ UNTESTED, built 2026-08-02 off the "ship preset layouts are very basic — stop them generating as all one single hull type" ask. A layout slot picked ONE unit type and stamped it into every position, so a carrier screen was four identical Burkes whatever the faction's roster held. The per-slot type dealing, the family restriction (a boat never pairs with a cruiser, two carriers never share a slot), the `MAX_MIXED_UNIT_TYPES` cap, the single-hull degrade and the naval-only gating are unit-tested in `tests/armedforces/test_naval_hull_mixing.py` (9 cases), and generation was headless-verified end to end on Tanker War 1988 / Pacific Repartee / Velvet Thunder. What no test can model is how DCS sails the resulting group.
- **§87 evidence note:** the station-keeping numbers quoted above (the 1.80–2.16 km §87 racetrack
  spacing, the identical per-unit path lengths) are **B38's** measurements of *formation keeping*.
  They are cited by **B48** but do not close it — B48's own contract is displacement from the
  campaign anchor, which this session did not measure. Keep the two rows distinct.
- **What CI cannot exercise:** whether a **single DCS group containing several ship classes** behaves — formation keeping and turn behaviour at mixed top speeds (a Perry is a knot slower than a Burke), station-keeping on the layout's positions with different hull lengths, and whether the group's waypoint/speed handling still works when the group leader is now a different class than before. Also unmodelled: the visual read of the screen from the cockpit, and the mixed group's threat behaviour (each hull brings its own SAM fit, which is the point).
- **Setup:** any campaign with a carrier and a navy fielding more than one hull of a class — Tanker War 1988 (US CVN + Iranian navy) or Pacific Repartee (PLAN Type 052B/052C/054A) are the fastest. Start a **NEW game** (this is generation-time; existing saves keep their already-generated groups), then look at the carrier screen and any "Naval Group"/"Naval Two Ship" objective on the map and in the mission. Fly (or fast-forward) a turn and watch a group under way.
- **Pass:** the carrier screen is a **mix** of hulls (e.g. Burkes + a Perry + a Ticonderoga) rather than four of one; the group sails as one formation at the slowest hull's speed without collisions, bunching or stragglers; the flagship of a carrier objective is still the carrier; and no group mixes a patrol boat or submarine into a surface combatant screen.
- **Fail signature:** still four identical hulls (the faction genuinely fields one hull of that class — check its roster before suspecting code; or the layout's slot declares explicit `unit_types:`); a speedboat/submarine/second carrier inside a surface screen (the family restriction regressed); ships colliding or drifting apart under way (mixed hull lengths against layout positions authored for Burkes — a template-spacing problem, fixable in the layout `.miz`); a carrier objective whose flagship resolves to an escort (`find_carrier_unit` takes `groups[0].units[0]` — the carrier slot must stay single-unit); or a SAM site / armor group suddenly fielding mixed types (mixing leaked past `NavalLayout`).

### B63 — A destroyed strike target is recorded in the campaign · §8 · ☑ VERIFIED (2026-09-16, DM, test 33)

**2026-09-16, DM verdict in chat (session `9148a88a`)** — **VERIFIED.** "B63 should have been proven last night with the save, and test I gave you" — and it was: test 33's log carries the `Scenery objectives` line and four `Objective destroyed` lines for the Tabqa Dam objectives, and the turn-3 save carries all four dead, which is the whole thing the row exists to check. The quit-and-relaunch reproduction of cause 1 is not owed separately; the snapshot fix has a unit test and the ordinary path is what the DM flies. Off the LOCAL card.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — **cause 2 verified end to end; cause 1 not exercised.** The log carries `Scenery objectives: 128 known, 0 already destroyed, match radius 30 m` at start, then four `Objective destroyed` lines at 01:46:24 for the MAVERICK package's Tabqa Dam objectives (Control at 1 m from the hit, Visitor Centre, Power Station and Engineering at 28–29 m), all four the package's own targets, under the players' six JDAMs. The turn-3 save carries all four units `alive=False`. No `state.json on disk carries` warning in `retribution.log`, because nobody quit and relaunched; that half still needs the LOCAL card's contrived run. Also answers the 27468 question this row raised on test 30: a JDAM'd building does raise `S_EVENT_DEAD` on this build; the 3,887 numeric ids in `unit_lost_events` are the front line's clutter, which raises KILL and not DEAD, and the app logged them as untracked.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, DCS 2.9.29.27468) — **not
exercisable here, and a pattern to read before the next attempt.** The campaign has no
scenery objectives (`RETRIBUTION_SCENERY_ZONES` is absent from the `.miz`), so cause 2 cannot
fire. But `state.json` carries 12 scenery ids in `kill_events` (buildings flattened by the four
Harriers going in and by SA-15 missiles) and **zero** entries in `destroyed_objects_positions`,
which the `S_EVENT_DEAD` handler fills for any scenery death whether or not a zone exists.
The same asymmetry holds in tests 26, 27 and 29 (32 / 32 / 1 scenery kills against 0 / 0 / 0
scenery deaths), all on 2.9.29.27468, while test 24 on 2.9.29.27278 recorded 282 scenery
deaths and 96 positions. No script error in any of those logs. Read: on the current DCS build
a scenery kill raises `S_EVENT_KILL` and not `S_EVENT_DEAD`. If that holds, the #957 matcher
never runs, and a destroyed building renders intact on the next turn because the destruction
zone is fed from the same list. Check on the next scenery strike: with the building flattened,
grep the log for `Objective destroyed`; if it is absent, the credit has to move to the
`S_EVENT_KILL` branch (target category SCENERY).

**History:** opened 2026-08-16 from the user's flown report ("Bombs hit and destroyed the target but it was not tracked in retribution"), session `c86c58dd`. **Root cause found and fixed the same day — it was never the scenery-tracking path.** The player aborted a ~100-second run of the turn-2 mission; DCS wrote `state.json` with `mission_ended`, `PollDebriefingFileThread` consumed it, logged "Mission end detected; stopping poll" at 14:05:24 and broke out permanently (its only staleness guard is an mtime newer than the `.miz`, which an aborted run of that same `.miz` satisfies). The real 49-minute sortie followed; at 14:58:41 the turn committed that two-minute snapshot. Three Tuapse dock buildings (`TARANTULA`) were destroyed and recorded by zone name in the final `state.json`, and stood untouched in the save. Rebuilding a `Debriefing` from that same file credits all three and committing it flips them dead — which is what proves the snapshot, not the matching, was at fault. Fixed in `game/finaldebriefing.py` (the commit re-reads `state.json`); `tests/test_final_debriefing.py`; forensics in `retlab-scenery-kill-tracking-notes.md` §0.

**2026-08-30 — a SECOND cause was found and fixed, and this row now covers both.** Upstream
[#957](https://github.com/dcs-retribution/dcs-retribution/pull/957) (adopted; open upstream, not
merged) found that an objective whose zone also holds indestructible scenery could never be
credited: the `MapObjectIsDead` trigger needs *every* object in the polygon dead, and a
`WOODPILE_01` reports a life of `1e38`. Measured on one Kola mission at 978 scenery deaths, with
three objectives recording nothing across three turns while being levelled each time. Deaths are
now matched to the nearest objective by position in `dcs_retribution.lua` (30 m, measured), and
the triggers are gone. Our own note had ruled a position matcher out — correctly, for the
*Python-side* table it measured; the Lua-side match was never tested. See
`retlab-scenery-kill-tracking-notes.md` §8.6.

Needs a flight to confirm the fix end to end. The cheap version deliberately reproduces the trap:

1. Generate a turn with a strike on a **map-scenery** target (a port, factory or terminal drawn as white zones — not a spawned static).
2. **Launch the mission, quit to the menu after ~1 minute, then relaunch and fly it properly.** That is the exact condition that broke it.
3. Destroy the target late in the sortie, land, accept the results.

- **Pass (cause 1, the snapshot):** the target reads destroyed on the next turn's map, and `retribution.log` carries the new warning `state.json on disk carries N recorded events but the last polled debriefing had only M — committing the fresh read`.
- **Pass (cause 2, the matcher):** `dcs.log` carries `Scenery objectives: N known, M already destroyed, match radius 30 m` at mission start, and one `Objective destroyed: '<zone name>' (D m from the hit)` per building you flatten. Every credited zone name appears in `state.json`'s `dead_events`. Pick a target whose zone sits in clutter — a dockside or built-up objective, not an isolated one — because a zone with no indestructible neighbour would have passed before this fix too.
- **Fail signatures:**
  1. **Target still standing** — the fresh read did not happen or was rejected; check whether the log instead says the fresh read had *fewer* events (the shrink guard fired, meaning `state.json` was mid-write or already replaced).
  2. **No warning line at all and the target IS recorded** — fine, that is the ordinary case where the watcher never stopped early.
  3. **Results double-counted** (a kill charged twice) — the fresh read and the polled snapshot both committed; stop and re-read `_process_turn`.
  4. **`Objective destroyed` fires for a building you did NOT hit** — the 30 m radius is catching collateral. It was measured at 29 m hit / 31 m collateral, so report the distance in the log line before changing it; do not lower it below 30.
  5. **No `Scenery objectives:` line at all** — `RETRIBUTION_SCENERY_ZONES` never reached the mission. Check the `Building objectives (positions)` TriggerStart survived generation; a dead plugin can get a mission-start trigger dropped.

### B64 — The datalink era gate: the SA page populates when it should · datalink · ☑ VERIFIED

**2026-08-17 — VERIFIED on the DM's call ("B64 is good"), opened and closed the same day.** This also closes the manual step the feature shipped owing: the policy is now set to Era-correct in the save and in the settings baseline, so new campaigns no longer inherit the migrated `Never`. The terminal comes up.

**History:** opened 2026-08-17 alongside the feature (#858). Built from a flown finding: a generated Caucasus mission carried the DCS `EPLRS` task on **1 of 23** blue plane groups against **16 of 18** in a hand-built modern mission on the same install, because the old single boolean sat off in the saved-settings baseline. The rule (`game/datalinkera.py`), the 14 authored `datalink_introduced:` dates and the `True→ALWAYS / False→NEVER` migration are unit-tested in `tests/test_datalink_era.py`. Whether the terminal actually comes up in the cockpit is DCS-only. Design note `retlab-datalink-era-notes.md`.

- **What it is:** DCS reuses the EPLRS name generically — the task on a group is what makes that group take part in datalink at all (Link 16 on a Hornet or Viper, SADL on an A-10C). pydcs gives every capable airframe the task at group creation and Retribution's `configure_behavior` clears it; `configure_eplrs` is the only thing that puts it back. So the policy decides whether we **restore** a capability the sim already granted, and `NEVER` actively strips it.
- **⚠ Setup, and it is the whole point:** the old boolean migrates to **Never**, so an existing save and the settings baseline both read as off. Set **Settings → Mission Generator → Gameplay → Datalink → Era-correct** in the current save **and** again with no campaign loaded, or every new campaign inherits the off state and this row reads as failing when the feature is fine.
- **Pass:** on a 2000s-or-later campaign the SA page shows friendly PPLI and surveillance tracks — your flight, the AWACS, the tanker. On a 1991-or-earlier campaign it is empty, and that is the feature working, not a fault.
- **Fail signatures:**
  1. **Empty SA page on a modern campaign** — check the policy actually saved before suspecting the gate; an unmigrated `Never` is indistinguishable from the bug this replaced. Then grep `dcs.log` for the group's `EPLRS` task.
  2. **A Desert Storm Hornet with a live SA page** — the date table is not being consulted, or the policy is on `Always`.
  3. **An airframe you expected to be gated behaving as though it has no date** — absent reads as permissive by design; check whether that airframe is one of the 14 authored ones before treating it as a bug.

### B40 — The Wing Grows: scheduled squadron arrivals · ⊘ RETIRED

**History:** retired 2026-08-16 — §82 was removed on the DM's call ("it doesn't add much except in very specific campaigns"), so the scenario this row tracked no longer runs. It was never flown. See `retlab-features.md` §82 for what was removed.

### B41 — SP Pilot Mode: the pre-turn card + the aircraft-first board · §83 · ⊘ RETIRED (removed 2026-10-12, DM: stripped)

**2026-10-12 — REMOVED on the DM's call.** Verified below on 2026-08-05, then never switched on: off in his default settings and in all ten of his saves. The button, the board, the pre-turn card and the setting are deleted, so this row can never be run again.

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "B41 is working and awesome", upgraded from the same day's "half good" first look once the board was actually driven) (was ◐ PARTIAL, 2026-08-05, user app pass `pr-merge-code-audit-7e8b4c` — "half good": the dialog looked good at first pass; still owed = the end-to-end leg — take a sortie through the board, Take off, and confirm the generated mission carries exactly that flight with one client slot, plus the pre-turn card sections against a campaign with real MIA/victory/arrival data) (was ☐ UNTESTED, built 2026-08-03 — an app-side pass, not an in-game one. Both data cores are fully unit-tested (`tests/retlab/test_sp_pilot_mode.py` 20, `tests/retlab/test_pre_turn_briefing.py` 16: the airframe list is not filtered by the ATO, the ladder resolves rung 1 before rung 2, a flight that already carries a client is never offered, seating claims exactly one PLAYER pilot, a join offers only roles the package lacks, and every briefing section is individually guarded). What CANNOT be checked here is the dialog itself — `qt_ui` is not CI type-checked and the container has no GL, so no Qt test could be run against it.

- **Setup:** turn ON **SP Pilot Mode** (RetLab Features → Single-player flow; default off). Play any campaign's turn 1 and end the mission.
- **Pass criterion:** the debrief window shows **"Accept results & fly next"** beside the normal button. Pressing it processes the turn exactly as before and opens a dialog that (a) lists the pre-turn reasons — at minimum the victory/arrival lines on a fresh campaign, and a named evader with a capture percentage if anyone went down — and (b) shows every airframe in your wing on the left, with sorties for the selected one on the right. Selecting a commander-planned sortie and pressing **Take this sortie** reports the seat taken; closing the dialog and pressing **Take off** generates a mission in which **that flight is yours and carries exactly one client slot**.
- **Fail signature:** the button missing with the setting on (or present with it off); the dialog opening empty on a campaign that has an ATO; an airframe list that only shows types the commander fragged (the filter bug the whole design exists to avoid); a seat that produces `client_count` > 1 or displaces an existing client; a briefing line that renders raw punctuation or an unformatted number; or the turn failing to process at all — which would mean the `_process_turn` extraction broke the ordinary **Accept results** path, the one regression risk in this change.
- **Also worth a look:** picking an airframe with no sortie should say so plainly rather than showing an empty list, and picking a **join** option should say joining is not wired yet rather than appearing to work.

### B46 — Settings surface: search · Features page · advanced disclosure · §28 · ☑ VERIFIED

**History:** 2026-08-05, user app pass `pr-merge-code-audit-7e8b4c` — "B40 is good" [tested under its former duplicate id]; renumbered B40 → B46 same day because §82 The Wing Grows already owned B40) (was ☐ UNTESTED, built 2026-08-03 off "do you ever feel like the whole settings interface is bloated?". The audit found the surface at **213** fields with **zero** dead ones and **41** gates on never-flown features, so nothing was retired — the three changes are presentational. `tests/test_settings_filter.py` drives the real Qt widgets offscreen for the filter, the disclosure, the Features-page move and the campaign badge (17 cases), and `tests/test_settings_dependencies.py` covers the cross-page greying. `qt_ui` is not CI type-checked and nothing offscreen proves the thing *reads* right, which is the whole point of the change — so this is an in-app pass, not an in-game one.
- **What CI cannot exercise:** whether the dialog is actually easier to use — how the filter bar looks at the real window width, whether the advanced disclosure link is discoverable or reads as clutter, whether the `● SET BY CAMPAIGN` badge is legible against the theme (it is a hardcoded `#4ec9b0`, the one colour in this change not drawn from the theme tokens), and whether the Features page's eleven sections are the right grouping once you see them all at once. Also unmodelled: layout reflow when rows are hidden (Qt grid rows collapse, but the group box does not re-lay-out its neighbours until shown/hidden), and the New Game wizard path, which renders the same widget through a `QWizardPage`.
- **Setup:** open **Settings** in a loaded campaign (ideally Red Tide or a COIN campaign, which preseed a lot, so the badges have something to show). Then start **New Game** and step to the Campaign options page with two different campaigns selected in turn.
- **Pass:** typing in the search box narrows every page live and the category list shows per-page counts with empty pages greyed; clearing it restores the plain page names; **Only changed** on a fresh campaign shows just what the campaign preseeded plus anything you edited; each preseeded option carries the badge, and switching campaigns in the wizard moves the badges; every section with knobs shows "▸ Show N advanced options" and expands/collapses; searching reveals advanced rows without needing the link; the **RetLab Features** page lists every fork feature's toggle in themed sections; and toggling a feature gate there greys its knobs on the topical page **live** (the cross-page case — `motorpool_enabled` on Features vs `motorpool_spawn_cap` on Performance is the cheapest pair to check).
- **Defect found after this row was signed off (2026-08-10, fixed same day, session `f-14bu-task-generation-da0fc7`).** The user reported the flight-size weights "lost". They were not — `AutoSettingsGroup.apply_filter()` hid a section whenever its *shown* row count was zero, and the disclosure link lives inside that box, so **every section where the mechanical rule marks all fields advanced rendered as nothing at all**: 13 sections / 47 options, incl. all seven Air Doctrine knob groups and Campaign Management's Commander economy + Flight-planner automation (the 2/3/4-ship weights). Only the search bar reached them, and only if you already knew the name. Visibility now counts shown + folded rows, and an all-advanced section starts expanded. Pinned offscreen by `test_all_advanced_sections_show_their_knobs` + `test_collapsing_an_all_advanced_section_leaves_it_reachable`. **Re-check on the next app pass:** Air Doctrine and Campaign Management show every section, and Flight-planner automation shows its four spinners without a click.
- **Fail signature:** a whole section missing from a page (the all-advanced-visibility regression above — check `apply_filter` still counts folded rows); the badge invisible or illegible in one of the themes (hardcoded colour vs the theme's background — swap it for a token); the advanced link showing "Show 0 advanced options"; a section left visibly empty instead of hiding when filtered out; a feature's knobs **not** greying when its gate is toggled from the Features page (the `SettingsDependencyHub` broadcast regressed — check the control is in `dependency_masters()`); an option appearing on two pages or vanishing entirely (the `_LAYOUT_SPEC` lift dropped it — `test_every_field_survives_the_features_page_move` should have caught this, so suspect a field added since); or the New Game wizard failing to badge anything (the wizard calls `record_campaign_preseeds` — a campaign with no `settings:` block correctly badges nothing).

### B62 — A CSAR package actually reaches the ATO after a real ejection · CSAR · ☑ VERIFIED

**History:** adopted 2026-08-07; the target finder, the per-side cap, the reachability skip and the package build are unit-tested in `tests/test_csar.py`. Whether the commander frags one in a real campaign turn is app-level

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — VERIFIED.** After real ejections the save holds **3 blue downed pilots** (Peter Chapman/F-14B(U), Greg Davis/E-2C, Alan Cooper/KC-135) and **2 CSAR packages in the blue ATO** — this row's pass criterion exactly. 18 ejection events were recorded in `state.json`, so the path from ejection to tasking works end to end. Red holds 5 downed pilots and 0 CSAR packages, consistent with the per-side scope. Not watched: whether a CSAR package flown to completion actually recovers the pilot.
- **What CI cannot exercise:** the end-to-end planning arc — a survivor exists at turn start, the commander notices, and a CSAR package appears in the ATO with a sane airframe, route and TOT. **This is the cheapest possible check on the whole adoption** and should be the first thing anyone does.
- **Setup:** eject from an ordinary ATO jet, end the mission, pass the turn, open the ATO. **~20 min, no flying.**
- **Pass:** a CSAR package exists, tasked at the survivor, crewed by a helo, with a route that reaches it and returns; `max_csar_flights` (2) is respected with several survivors down.
- **Fail signature:** no package at all with a survivor clearly on the map — walk the gates in order rather than guessing: is `csar_enabled` on for that side, does the wing field a CSAR-capable helo squadron, is the survivor reachable at all. The old §21 surge row (G31) went four weeks unfalsifiable precisely because it had five silent early-returns and nobody knew which had fired; if this row fails, **say which gate**, and if the code cannot tell you, that is itself the finding.

### B50 — The auto-planner never picks the King for a rescue · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, **FAILED IN THE FIELD 2026-08-16 (5th test), and worse than this row predicted.** The planner fragged the King and `CsarFlightPlan` refused to build for a fixed-wing flight; the `PlanningError` came out through `pass_turn` into the UI, so the campaign could not be advanced at all. Priority was never the guarantee — `best_squadrons_for` sorts the candidates but returns whatever it finds, so the King wins by default whenever it is the only CSAR squadron in range, however low its number. Fixed 2026-08-17 by `FlightType.requires_helicopter`, checked in `Squadron.can_auto_assign_mission` (auto-planning only), plus a `PlanningError` catch in `plan_mission` so an unbuildable flight plan scrubs one package instead of the turn. Re-test owed.
- **What it is:** upstream restricts CSAR to helicopters because the DCS AI `Land` task is helicopter-only — an AI fixed-wing rescuer just orbits the survivor. The fork overrides that for the C-130J so the King can be **player-flown**, and pins it at priority 5 so the planner always reaches for a helo first.
- **What CI cannot exercise:** the actual pick, in a wing that fields both a King and rescue helos.
- **Setup:** a campaign whose wing has both a C-130J-30 squadron and at least one rescue-helo squadron. Create a survivor, pass the turn, read the ATO. ~20 min, no flying. **Also run the harder case: a survivor in range of the King's base but out of range of every helo** — that is the shape that crashed, and the correct outcome is now no CSAR package at all.
- **Pass:** the CSAR package is crewed by a helo, or is absent. The King is never auto-fragged for CSAR. The turn passes.
- **Fail signature:** an AI King fragged for the rescue — it will fly to the survivor, orbit, and never pick anyone up, so the rescue silently fails and the pilot goes MIA. Or the turn refuses to pass with `PlanningError: CSAR pickups are only usable by helicopters`, which means the capability gate is not being consulted. (Since 2026-08-26 a fixed-wing CSAR flight dispatches to `KingFlightPlan` instead, so that raise would now mean the dispatch broke too — see B106.)

### B51 — The rescue package is not planned into threat it cannot survive · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, the SAM-avoidance gate is unit-tested; whether the resulting route is actually survivable is a flown judgement
- **What CI cannot exercise:** a helo at 130 kt routed near a live SAM or across a contested front dies before it arrives, and the campaign quietly loses both the survivor and the rescue crew. Upstream claims it will not send helos into a live SAM ring; nobody has watched it choose.
- **Setup:** create a survivor **behind the lines**, inside or near a live red SAM ring. Pass the turn and read the planned route on the map; then fly or spectate the package. ~45 min.
- **Pass:** either no package is planned (correctly refusing an unreachable pilot), or the route avoids the threat rings and the helo survives to the survivor.
- **Fail signature:** a package routed straight through a MERAD/LORAD ring; a helo shot down en route, which per the cascade below manufactures **more** survivors than it rescues.

### C1 — AWACS/tanker orbit front-anchor · #84 · ✅ CLOSED (reverted 2026-08-09)

- **Closed by the planner re-convergence (work order D).** `support_orbit_anchor` and
  `supportorbit.py` were deleted by `c2065db12`; nothing in `aewc.py` or
  `theaterrefueling.py` consults a front line, so "support racetracks anchor on the FLOT"
  describes code that no longer exists. Found still marked VERIFIED during the test 36
  AWACS audit (2026-09-17).
- Was ☑ VERIFIED 2026-06-24; the finding is preserved in git history.

**History:** 2026-06-24
- **Setup:** Any campaign with AWACS + tanker support.
- **Pass:** Support racetracks anchor on the FLOT, behind the front.
- **Fail signature:** Red AWACS flung far off-axis (the ~175 NM case #84 fixed).

### C2 — Support orbit depth behind FLOT · #86 · ☑ VERIFIED · ⚠ PARTLY SUPERSEDED (2026-08-09)

- **2026-09-17 — half of this row no longer describes the code.** "Deep behind the FLOT"
  and the AI depth asymmetry (`AI_SUPPORT_DEPTH_FACTOR`) went with `supportorbit.py` in
  the §6 revert (`c2065db12`, work order D). **The other half still holds:** `aewc.py`
  stations the orbit `aewc_threat_buffer_min_distance` (default 80 NM) outside the threat
  zone and the tanker builder does the same at 70 NM, so "clear of forward SAM reach" is
  still what the code does.

**History:** 2026-06-24
- **Setup:** As C1; watch where the orbit actually sits relative to threats.
- **Pass:** Orbits hold **deep** behind the FLOT, clear of forward SAM/CAP reach.
- **Fail signature:** Support orbit placed within enemy engagement depth.

### C3 — Tanker racetrack speed estimate · ☑ VERIFIED

**History:** 2026-06-26, planner/data + live-save confirmed — in-sim tanking not eyeballed
- **Headless adjudication (2026-06-26):** Loaded every tanker via `AircraftType` and
  computed `RefuelingFlightPlan.patrol_speed` directly (no flight). Found the F/A-18E/F
  buddy tankers riding the **estimate fallback at 509 KTAS (~335 KIAS)** — their
  hand-tuned `patrol:` block was mis-nested under `fuel:` in `FA-18ET.yaml` /
  `FA-18FT.yaml`, so the loader (`AircraftType._variant_from_dict`, top-level
  `data.get("patrol")` at aircrafttype.py:626) never saw it and the tuned 320 KTAS was
  dead data. **Fixed:** de-indented `patrol` to top level in both files. Every tanker now
  carries an explicit, sane orbit speed — buddy (A-6E / F/A-18E/F / S-3B) 320 KTAS
  (~242–266 KIAS), KC-130 370, KC-135 / MPRS 445/440 (~303/305 KIAS), KC-10 405, IL-78M
  400, and KC-130J an intentional 180 KTAS (~125 KIAS, the documented slow helo tanker).
  No tanker rides the estimate path anymore, and the Mach-at-altitude fallback is itself
  sane. **Residual (still in-sim only):** receivers physically joining and taking fuel
  without S-turning.
- **Setup:** Plan a package that takes fuel from a **buddy tanker** (the F/A-18E/F or
  A-6E tanker). All buddy and dedicated tankers now define an explicit `patrol:` speed;
  the `preferred_patrol_speed(preferred_patrol_altitude)` estimate is now only a fallback
  for an untagged tanker.
- **Pass:** Tanker flies its racetrack at a sane, steady speed and receivers
  rendezvous and take fuel without falling behind or overrunning.
- **Fail signature:** Tanker orbit speed too slow/fast for receivers to join (e.g.
  fighters S-turning to stay behind, or unable to close). If seen, revisit
  `RefuelingFlightPlan.patrol_speed` in `game/ato/flightplans/refuelingflightplan.py`
  (and check the airframe's `patrol:` block is at top level, not nested under `fuel:`).
- **Live-save confirmation (2026-06-26):** Loaded the actual flown campaign save
  (`autosave.retribution`, GermanyCW turn 1) headless and read each planned tanker's
  `flight_plan.patrol_speed`: BLUE KC-135 = **445 kt TAS**, RED IL-78M = **400 kt TAS**
  (both `TheaterRefuelingFlightPlan`). Sane, airframe-appropriate orbit speeds on a real
  ATO — matches the data-table adjudication. Still in-sim only: receivers physically joining.

### C4 — A-6E attack/tanker split · ☑ VERIFIED

**History:** 2026-06-25
- **Verified (2026-06-25, in-game):** both A-6E variants load and behave — the Intruder is
  never auto-tasked for refueling/recovery and the Tanker orbits/refuels as a carrier tanker
  without picking up strike tasks. Data loaded correctly in the packaged app.
- **Setup:** A-6E now loads as two squadron-selectable types from `A6E.yaml`:
  "A-6E Intruder" (attack tasks only) and "A-6E Tanker" (Refueling/Recovery only,
  `max_group_size: 1`, carrier tanker patrol). Buy/auto-plan each and confirm both
  appear and behave. **Could not be load-tested in CI** — the A-6 unit isn't in the
  CI/dev pydcs build, so confirm the data actually loads in the packaged app first.
- **Pass:** The Intruder is never auto-tasked for refueling/recovery; the Tanker is
  never auto-tasked for strike/CAS/etc. and orbits/refuels as a carrier tanker.
- **Fail signature:** Either type missing from the airframe list (the A6E unit id may
  differ in the shipped pydcs, or variant-level `tasks` override didn't take); or the
  Tanker still picks up strike tasks / the Intruder still gets tanker tasking. Check
  that both variants resolve in `AircraftType` and that the A6E unit supports AI
  air-refueling in the build's pydcs.

### C5 — Boom/probe refuel-method compatibility · ☑ VERIFIED

**History:** 2026-06-26, planner/data + live-save confirmed — in-sim tanking not eyeballed
- **Headless adjudication (2026-06-26):** Exercised the matching logic on real loaded
  types (no flight). `can_refuel_from` is correct on representative pairs (boom receiver ×
  boom tanker = yes; boom × drogue = blocked; probe × boom = blocked; probe × drogue =
  yes), `tankerdemand.best_tanker_service_point` routes a boom tanker to the boom demand
  cluster and a probe tanker to the probe cluster (and `_compatible` matches
  `can_refuel_from` for the method dimension). Data audit: 11 tankers all tagged
  (KC-135 = boom, KC-135 MPRS / KC-130 / KC-130J / S-3B / IL-78M / A-6E / F/A-18E/F buddy =
  probe; the KC-10 is split into two selectable variants — `KC-10 Extender` boom and
  `KC-10 Extender (Drogue)` probe — which resolves the flagged "KC-10 boom-vs-drogue
  mis-tag" risk); receivers tagged boom=27 / probe=71 (USAF fixed-wing = boom, Navy / NATO /
  Russian = probe — textbook), with untagged airframes permissive by design. **Residual
  (still in-sim only):** receivers physically plugging in, plus the faction-composition
  caveat below (a faction with only a boom tanker starves its probe receivers — by design;
  permissive matching can only over-restrict, never crash).
- **Setup note (2026-06-25):** the faction flown in the 2026-06-25 session
  did **not** carry both a boom and a drogue tanker, so there was no method split to observe.
  Requires a faction with **both** a boom (KC-135) and a drogue (KC-135 MPRS / KC-130 / S-3B
  Tanker) tanker to exercise this row.
- **Live-save finding (2026-06-26) — single-tanker planner gap:** Loaded the flown
  campaign save (`autosave.retribution`, GermanyCW turn 1) headless. The BLUE air wing
  **does** carry both tankers (KC-135 boom ×2 *and* KC-135 MPRS drogue ×2; RED has IL-78M
  probe), and the compatibility logic is correct on the live ATO (RED IL-78M↔Su-27 both
  probe = OK). **But the auto-planner frags only ONE theater tanker** —
  `TheaterState` seeds exactly one refueling target
  (`theaterstate.py:325 closest_friendly_control_point()`) → `PlanRefueling` proposes
  1 REFUELING + 2 ESCORT. For that *dedicated* tanker package,
  `PackageBuilder._required_refuel_methods` sees no in-package receivers (real receivers
  live in other packages), so the single tanker is selected **unconstrained** → priority-first
  = boom KC-135, and RetLab `reposition_theater_tankers` then parks it on the strongest
  **boom** demand cluster. Result on this turn: the 5 BLUE **probe** types (F-14B, F/A-18C,
  A-6E, Mirage-F1EE, Tornado IDS) got **no theater tanker** — the probe Mirage colocated in
  the boom KC-135's package shows as incompatible (the refusal is working as designed). This
  is **not** a bug in the C5 matching machinery (all correct); it is a missing capability —
  **multi-method theater-tanker fragging** (one tanker per distinct receiver method present
  in the ATO).
- **Fix landed (2026-06-26) — per-method theater-tanker fragging:** `TheaterState` now seeds one
  refueling target **per servable receiver method** (`seed_refueling_targets`), threaded
  `RefuelingTarget.method` → `PlanRefueling.method` → `ProposedFlight.refuel_method` →
  `PackageBuilder._required_refuel_methods`, so a mixed boom+probe fleet frags one tanker for each
  method (each planned in its own `plan_missions` pass, then repositioned onto its own demand
  cluster). Falls back to a single unconstrained tanker for untagged / permissive / no-matching-tanker
  cases (never fewer than legacy). Tests: ~~`tests/test_refueling_targets.py`~~. **In-game re-test
  target:** a mixed boom+probe BLUE ATO should now show **two** tankers, and each method's receivers
  should tank from the compatible one. See the features-doc section "Per-method theater-tanker
  fragging".
- **Setup:** Aircraft now carry an `air_refuel_type` (boom/probe) and tankers a
  `tanker_refuel_types`; the planner only assigns a tanker that provides the package
  receivers' method, and `PackageRefuelingFlightPlan.patrol_duration` only counts
  compatible receivers. Plan a **boom** package (e.g. F-16/F-15) and a **probe**
  package (e.g. F/A-18/Su-27) in a faction that has both boom (KC-135) and drogue
  (KC-135 MPRS / KC-130 / S-3B Tanker) tankers. The classification data is an initial
  high-confidence pass and is **opt-in / permissive** — untagged airframes refuel from
  anything, so this can only *over-restrict* a mis-tagged aircraft, never crash.
- **Pass:** Boom packages get a boom tanker; probe packages get a drogue tanker;
  helicopters only get a slow (KC-130) tanker; mixed/untagged packages still get a
  tanker. Receivers actually plug in and take fuel in-mission.
- **Fail signature:** A package that should have a compatible tanker gets none (a
  mis-tagged receiver, or a faction lacking the right tanker type), or a receiver is
  matched to a tanker it can't physically use. Fixes are data-only: the airframe's
  `air_refuel_type` or the tanker's `tanker_refuel_types` in
  `resources/units/aircraft/*.yaml`. KC-10 boom-vs-drogue and any exotic/mod airframe
  are the likeliest mis-tags to review first.

- **Per-method theater-tanker fragging REVERTED 2026-08-09 (planner re-convergence,
  work order B).** `seed_refueling_targets` / `RefuelingTarget` / `ProposedFlight.
  refuel_method` are deleted; the HTN seeds one unconstrained theater tanker at the
  closest friendly CP again, so the mixed-fleet gap this row's fix closed is back. The
  **matching machinery this row actually verifies is untouched** — `can_refuel_from`,
  the tanker/receiver boom-probe tags, and `PackageBuilder._required_refuel_methods`
  for same-package buddy tankers all still work as verified. The row stays ☑ VERIFIED
  for that scope.

### C6 — Fuel-driven pre/post-vul tanking · ☑ VERIFIED

**History:** 2026-06-25
- **Verified (2026-06-25, in-game):** short sorties launched with no tanker; deep sorties got
  a refuel waypoint on the correct side and reached the tanker with fuel to spare; kneeboard
  bingo/joker read sanely past the tanker. The kg-`max_fuel`-vs-lb fuel-unit handling that
  couldn't be checked in CI held up. Fail signatures (need-gas-got-none / awkward pre-vul
  backtrack / flameout before tanker) did not occur.
- **Setup:** Formation/attack and escort flights no longer get a tanker waypoint
  unconditionally. `FormationAttackBuilder._refuel_tasking` estimates the sortie burn
  (ingress at cruise + the ingress→target→split vul at combat + egress home, plus the
  climb-out) vs usable internal fuel and inserts a refuel waypoint **only** when short:
  pre-vul (routed on the ingress nav, before the join) if it can't fight through the
  vul, otherwise post-vul (after the split). A sortie too long for even a full top-off
  to cover gets **both** a pre- and post-vul tanker. The fuel estimators credit the
  refuel point, so the kneeboard/sim fuel reads correctly past the tanker. Fly a
  **short** sortie (expect no tanker), a **long-egress** sortie (expect post-vul), a
  **very deep** target (expect pre-vul), and a **very long-range** sortie (expect
  both), in a faction with a compatible tanker.
- **Pass:** Short sorties launch with no tanker tasking; deep sorties get a refuel
  waypoint on the correct side (or both for the longest ranges); the flight reaches the
  tanker with fuel to spare and completes the sortie; kneeboard bingo/joker look sane
  after tanking.
- **Fail signature:** Flights that clearly need gas get none (or vice versa); pre-vul
  detour backtracks awkwardly; a flight flames out before the tanker. The burn now
  walks the real route at the actual per-leg climb/combat/cruise rates
  (`sortie_fuel_split`), so the remaining unknown is the **fuel unit handling (kg
  `max_fuel` vs lb consumption), which couldn't be validated in CI** — tune
  `_refuel_tasking` in `game/ato/flightplans/formationattack.py` if the pre/post/none
  split looks off.

### C7 — Theater tanker placed on receiver demand · ✅ CLOSED (reverted 2026-08-09)

- **Closed by the planner re-convergence (work order B).** The post-planning reposition
  pass `game/commander/tankerdemand.py` is deleted, so there is nothing left to fly. A
  theater tanker keeps the orbit its flight plan gives it.
- Was ☑ VERIFIED 2026-06-25; the finding is preserved in git history if the pass is ever
  rebuilt.

### C8 — AI helicopter terrain clearance (cruise AGL + terrain anchors + AGL air starts) · §8 · ☑ VERIFIED

**History:** built 2026-07-12 from the flown Red Tide M1 CFIT pattern; the cruise-setting return, the ≤5 NM leg subdivision with speed-locked RADIO "TERRAIN" points, the racetrack/BARO/short-leg/human exclusions, and the unit-record alt_type stamp in both air-start paths are unit-tested in `tests/ato/flightplans/test_helo_cruise_altitude.py` + `tests/missiongenerator/test_helo_terrain_anchors.py` + `tests/missiongenerator/test_airstart_unit_alt_type.py` — whether the DCS helo AI actually clears the ridges on the anchored profile is DCS-only. **First fail signature already caught + fixed 2026-07-12, same day:** the first generated Red Tide M2 hit the DCS mission-start rejection "waypoints ... has both unlocked speed and time and not surrounded by waypoints with locked time" on all three subdivided-RTB helo flights — the anchors inserted both-unlocked; they now insert speed-locked with the existing conflict resolver unlocking any anchor bracketed by TOT locks, and a full-route lock-flag sweep of a regenerated M2 shows 0 violations

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — VERIFIED on the user's call ("C8 I think is good").** No CFIT pattern in either recording. The Caucasus is not the Harz/Sauerland terrain that produced the original defect, so this is a clean-flight confirmation rather than a stress test of the terrain anchors.
- **What CI cannot exercise:** whether an AI Mi-8/Mi-24 flying the anchored route actually clears the Harz/Sauerland ridge lines (DCS's RADIO-altitude interpolation between the 5 NM anchors), whether the extra Turning Points upset formation/escort behavior or ETA timing, and whether an air-started helo now spawns at a sane height over high-terrain FARPs.
- **Setup:** Red Tide (GermanyCW), NEW mission generation with red Air Assault fragged (Bienenfarm-class targets across the Harz are the stress case — the flown M1 killed 3 Mi-8s + 1 Mi-24 to terrain in exactly this geometry). Optionally bump `heli_combat_alt_agl` back to the 200 ft default (the flown save ran 100).
- **Pass:** the generated miz shows helo transit waypoints at the *cruise* AGL (500 ft default, not 100-200) with "TERRAIN" points every ≤5 NM on long legs, and air-start helo units carry `alt_type=RADIO`; in-game, the assault Mi-8s cross the Harz and deliver their troops (the H FRG 12-style clean run becomes the norm), no helo CFITs into ridge lines, racetrack orbits fly normally, human helo flights see no extra waypoints.
- **Fail signature:** a helo still flies a straight low line into a ridge between anchors (DCS not honoring the RADIO re-anchoring — would need tighter spacing); formation escorts breaking at the inserted points; DCS rejecting the route at start (a locked-speed/time conflict from the inserted points — they are emitted unlocked, so this would be an engine surprise); an air-started helo spawning at 500 m MSL below terrain (the unit stamp not honored).

### C9 — Carrier-recovery stagger (same-boat package landings spaced) · §8 · ☑ VERIFIED (2026-09-16, audit)

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED on the DM's call ("c9 seems fine").** The record agrees: one midair ever (Scenic Route turn 3, 2026-07-16, the sortie that built the stagger), none in the 30 recordings since, two Caucasus recoveries in test 16 arriving in two groups 1.8 min apart, and the row's own recurrence signature (unexplained AI losses at the boat) absent from every debrief. The 5-minute spacing itself was never read off an ATO; the DM's call stands on the absence of the failure it exists to prevent.

**Setup card:** [flycards/REGRESSED-SWEEP.md](flycards/REGRESSED-SWEEP.md) — one Starfire campaign (`operation_desert_trident`) clears this alongside C9 and B48.

> **Test 9 flown 2026-08-18** (Syria `operation_desert_trident`, `Tacview-20260818-214946` + `dcs.log` + `state.json` + the generated `.miz`) — **not adjudicated.** The carrier flew and the deck-dressing sequence
> ran, but recovery timings were not pulled from this recording. No claim either way; the row
> is unchanged.

**History:** **assessed a one-off and taken OFF the WATCH list 2026-08-06, DM call** — "I think a one off issue, unless you see otherwise lets drop it". Evidence checked before agreeing: **exactly one** carrier-recovery midair on record, ever — the 2026-07-16 Scenic Route turn 3 below — with no other collision report anywhere in this checklist, and the fix is live (`MissionScheduler._deconflict_carrier_recoveries`, called at line ~244) and test-covered. The part that is deterministic and headless-testable — ≥5 min TOT spacing, fixed player/CAP/ASAP entries — is exactly the part the tests pin. **The honest caveat, recorded so this is not mistaken for a pass: the one-off is the BUG, not the FIX.** The stagger shipped the same day the midair was found and **has never been observed working in DCS**; the row therefore stays ☐ UNTESTED rather than being closed. What makes dropping it acceptable is that a recurrence **self-reports** — two AI aircraft colliding at the boat shows up as unexplained AI losses in the debrief without anyone watching for it. **If that ever appears, widen `CARRIER_RECOVERY_INTERVAL`** and put this back on the list) (built 2026-07-16 from the flown Scenic Route turn-3 midair — an OX S-3B and a CATERPILLAR Hornet from two different packages converged co-altitude at ~1,000 ft in the DCS overhead and collided 2.7 NM from CVN-71; the slotting math, the fixed-entry behavior for player/CAP/AEW&C/SCAR/ASAP packages, the recovery-tanker-ETA re-collection ordering, and the helo/shore exclusions are unit-tested in `tests/test_carrier_recovery_stagger.py` + `tests/test_missionscheduler.py` — whether 5-minute arrival spacing actually keeps DCS's pattern AI from converging is DCS-only

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — PARTIAL, consistent with the feature.** Turn 2's recovery onto CVN-71 arrived in two groups rather than one clump: 2 aircraft down at **T+47.4 m**, 5 more at **T+49.2 m**. That is spacing rather than a pile-up, but a single 2-minute gap on one boat is weak evidence for a stagger mechanism, and this row was already assessed a one-off and taken off the WATCH list. Recorded so the observation is not lost, not to claim the mechanism.
- **Pass:** on a carrier mission with several AI packages recovering to the same boat, arrivals reach the overhead one package at a time (Tacview: no two packages' flights co-altitude within ~1 NM in the pattern); the generated ATO shows same-boat landing times ≥5 min apart for AI packages; a player package's TOT is unchanged from what the plan would otherwise assign.
- **Fail signature:** two AI packages still converging co-altitude in the overhead within a minute of each other (the DCS pattern ignores the spacing — consider widening `CARRIER_RECOVERY_INTERVAL`), or strike TOTs visibly piling up late in the mission window (over-aggressive delays on a crowded deck).

### C10 — Player CAS steerpoints mark the ground · §8 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "C10 is good"; covers the 2026-07-19 widening too, i.e. every target type and landing type marks ground, not just the CAS FLOT case that opened the row) (was ☐ UNTESTED, built 2026-07-16 from a user-reported flown Hornet CAS deck — "sometimes target waypoints generate in the air and are unable to be found", FLOT start/end both reading 22000. The CAS FLOT boundaries are planned at `get_combat_altitude` and stamped RADIO, i.e. ~22,000 ft **AGL** — correct for the AI, whose waypoint *is* the track, but a human's steerpoint diamond floats 22,000 ft over the terrain with nothing under it. Every other target waypoint already ships at `meters(0)`; `cas()`'s `meters(1000)` is a FLOOR so it never pulled it down, and `FlightWaypointType.CAS` has no generator dispatch entry so no generation pass touched it. The fix lifts the pre-existing client-zeroing in `PydcsWaypointBuilder.build()` out of its `if self.waypoint.flyover:` nesting onto a shared `FlightWaypoint.marks_ground_for_player`, and the kneeboard derives from the same predicate (it reads the planning model, so a generation-only fix would print 22000 against a grounded steerpoint). The predicate, the kneeboard Alt column, and the flyover non-regression are unit-tested in `tests/ato/test_flightwaypoint_ground_marked.py` + `tests/missiongenerator/test_kneeboard_cas_altitude.py` — whether the cockpit steerpoint actually lands on the deck and a pod will slave to it is DCS-only. **Widened 2026-07-19** off the flown DS91 escort deck ("Target area 22000" beside Land 0; follow-up call: "all Target and landing waypoints, not just escorts"): every target type (`TARGET_GROUP_LOC`/`TARGET_POINT`/`TARGET_SHIP`) and landing type (`LANDING_POINT`/`CARGO_STOP`) now marks ground — keyed on waypoint semantics, never row position or flight type; the escort TARGET was the one still planned at track altitude, the rest are pinned structurally — and the §74 DTC cartridge emits the same zeroed altitude instead of the planning altitude, so the AutoLoad no longer floats a grounded steerpoint back up. Pass criterion additions: a client **escort** flight's target steerpoint sits on the deck (kneeboard row 0, jet + DTC route agree), and a Hornet/Viper DTC route's CAS/target/landing steerpoint altitudes match the .miz after AutoLoad. Fail signature: target diamond at ~22,000 ft over the objective, or the DTC route re-floating a steerpoint the miz had grounded
- **What CI cannot exercise:** whether the 0-AGL steerpoint renders on the deck in the cockpit and a TGP/weapon will actually slave to it, and whether zeroing the FLOT waypoints changes anything about how a *player* flight's route reads or flies (the AI path is untouched by construction).
- **Setup:** Any campaign with a front line; frag a **player-crewed CAS** flight (the observed case was an F/A-18C off Bandar-e-Jask). A second, **AI-crewed** CAS flight in the same mission is the control.
- **Pass:** the player flight's FLOT START/FLOT END steerpoints sit **on the terrain** — the HUD/HSI diamond marks ground you can look at, a TGP slaves to it, and the kneeboard Flight Plan prints **0** in the Alt column for those rows (not 22000). The AI CAS flight is **unchanged**: its generated waypoints still carry the combat altitude and it flies its normal track, not a dive at the dirt.
- **Fail signature:** the diamond still floats (the client zeroing didn't fire — check `client_count > 0` at generation, i.e. that the flight really is player-crewed and not a dynamic slot); the kneeboard and the cockpit **disagree** on the altitude (the two consumers drifted apart); or — the one that would matter — an **AI** CAS flight descending toward the ground over the FLOT (the predicate leaking to AI; would mean `client_count` is non-zero for an AI flight, or the layout got the split baked in after all).
- **Note:** a dynamic-slot pilot isn't a player-crewed ATO flight, so their jet won't get the grounded steerpoint — same limitation as the §58 briefing card.

### C11 — Front-less AEW&C stations forward · §8-adjacent (support orbits) · ☑ VERIFIED

**History:** 2026-07-17 night fly — all three halves confirmed in the air; one follow-up observation on the support-escort attrition inside the west S-200 MEZ) · ⚠ PARTLY SUPERSEDED (2026-08-09
- **2026-08-09 — the placement half of this row no longer describes the code.** The §6
  revert (planner re-convergence work order D) deleted `support_orbit_anchor`, so orbits
  no longer face the nearest enemy CP or stand a buffer behind their anchor; they use
  upstream's target anchor + nearest-threat-boundary stepping again. The
  "parked between two enemy fields" failure this row proved fixed is therefore possible
  again. **The two squadron/target halves are KEPT and still live** (U13's front-less
  target pick, U14's basing-aware squadron preference, both in `game/commander/`), so
  the E-3-flies-the-land-station / E-2-stays-with-the-boat result stands.
- **2026-07-17 night fly (fresh Scenic Route Merged turn 1, Tacview `Tacview-20260717-214932`,
  session `tacview-test-analysis-5bb161`): every coded half worked.** Squadron preference: the
  **E-3A flew the Khasab land station from Al Dhafra** and the **E-2C stayed 26 NM off the CVN**
  (no E-2 dragged to the land station, no idle E-3s). Placement: the blue E-3A/KC-135/S-3B stack
  orbited the **southwest gulf** (the #635 save-verified position), on the friendly side, never in
  the Jask pocket; the **red A-50 held ~86 NM behind Havadarya** (vs 424 NM from the fleet
  pre-fix) and the red IL-78 even deeper — neither red HVU was ever engaged. **Follow-up
  observation (not a C11 fail):** the SW-gulf stations sit ~100–123 NM from a west-side S-200
  site (Kish area) whose paper MEZ reaches them; the HVUs survived the whole mission (the SA-5
  preferred fighters) but **5 support-escort jets died to that site one by one** while nothing
  ever tasked SEAD/DEAD against it (its 4 Square Pair radars alive at end, 13 launches, 6–7
  kills — the mission's deadliest red asset). Whether that's an escort-orbit placement question
  or an auto-planner threat-priority question (service the S-200 whose MEZ covers friendly
  support stations) is a separate item. — 424 NM from the enemy fleet, orbiting its own rearmost base. The #613 no-front fix correctly stopped the runaway depth march (the orbit holds AT its anchor), which exposed the OTHER half: `theaterstate.aewc_targets` picked `farthest_friendly_control_point()` — the rear-safe choice that only makes sense when a front exists for the orbit geometry to work against. On a front-less theater the non-carrier AEW&C target is now `closest_friendly_control_point()` — the friendly field nearest the enemy. Fronted campaigns byte-identical; carrier targets untouched. Unit-tested in `tests/test_aewc_targets.py`; where the orbit actually ends up is DCS-only)
- **Placement half (found 2026-07-17 on the user's first look at the fixed build):** the forward anchor exposed the no-front nearest-threat-boundary bearing in `support_orbit_anchor` — from an anchor inside a big fighter zone it threads the gap BETWEEN enemy fields; the blue E-2/tanker stack was placed 27–45 NM from Bandar-e-Jask's Tomcat ramp (the flown KC-135 died to an Iranian AIM-54 in exactly that pocket). Fixed: with enemy land CPs the orbit faces the **nearest enemy CP** and stands **one buffer** behind the anchor for both sides (no 2.5× AI depth on a front-less map); the boundary bearing survives only for carrier orbits and no-enemy-land theaters. Save-verified placements: blue support southwest gulf 206/183 NM from Bandar Abbas; red A-50 78 NM behind Havadarya. Tests ~~`tests/test_support_orbit.py`~~.
- **Squadron-preference half (found 2026-07-17, user nitpick on the same game):** with 2 E-2 (boat) + 2 E-3 (Al Dhafra), the plan double-tasked the E-2s (one dragged 160 NM to the land station) while both E-3s sat idle — the generic ranking measures base-to-*target* distance, and the CVN sat closer to Khasab (126 NM) than Al Dhafra did (147 NM). `PlanAewc._preferred_aewc_type` now pins basing: a **carrier** station is covered by that boat's own squadron, a **land** station by the nearest **land-based** AWACS squadron; no matching squadron with untasked jets ⇒ None (generic ranking — an all-carrier wing still covers the land station with an E-2). Save-verified: Khasab station → E-3A. Tests in `tests/test_aewc_targets.py`.
- **Setup:** a front-less campaign with a land-based AWACS on either side (Scenic Route Merged is the reference case, both sides). NEW game or a replan (aewc targets are re-derived each plan pass).
- **Pass:** the red A-50 orbits ~80 NM behind its forward field (Havadarya area), facing the strait, feeding MANTIS (`CheckLoop` climbing while it's airborne); the blue E-2/tankers orbit on the FRIENDLY side of their anchor (southwest gulf), never in the pocket between Bandar Abbas and Jask; nobody inside a threat ring.
- **Fail signature:** the AWACS still orbiting a deep-rear field 300+ NM out (the target pick not taking effect — check `front_lines()` actually yields nothing on this laydown); a support orbit parked between two enemy fields again (the enemy-CP bearing not engaging — check the theater actually has enemy land CPs); or an AWACS INSIDE a threat ring (the clearance floor failing).

### D1 — Player-despawn loss suppression · §8 · ☑ VERIFIED

**History:** 2026-06-24
- **Setup:** Player despawns/jumps seat mid-mission (not an ejection, not a
  shootdown), then the mission ends.
- **Pass:** Airframe + pilot are NOT logged lost; a real shootdown and a real
  ejection still DO count.
- **Fail signature:** Surviving player jet logged lost (the GERBIL F-14 case).
- **Residual to watch:** if the engine tears the mission down without
  per-player `PLAYER_LEAVE_UNIT` events, despawn-crashes aren't caught —
  land/despawn before ending remains the belt-and-suspenders.

### G2 — Recon BDA bridge (one plugin, player + AI) · §12 · ✅ CLOSED (bridge removed 2026-08-18) (was ☐ UNTESTED

**Closed by the recon rework:** engaging a site is the only reveal now, so a recon
overflight — player or AI — changes no campaign state and there is no BDA fog left for it
to lift. **The open call was answered 2026-08-20: the plugin is deleted, `FlightType.TARPS`
stays.** It was still popping a "confirmed BDA" cue on landing for a mechanic that no longer
existed, and scanning every red ground and ship unit to produce the number in it. TARPS keeps
its own job — the command-post find, G40, which is planner-side Python. Nothing here needs a
flight test. See features doc §12. The pass description below is kept for reading old sessions.

**History:** **REBUILT 2026-08-05** `units-runway-generation-bf755e`, from the DM's "the system as a whole needs a fresh look". The old split — MOOSE `Ops.TARS` event callbacks for the player, a geometric overflight check for the AI — was two unrelated implementations of one question that could not agree by construction, which is why "is TARS broken" was unanswerable. **MOOSE `Ops.TARS` is cut.** All it contributed was a unit NAME scraped off a `Snapshot` whose schema was never confirmed (`snap.name or snap.unitName or snap.UnitName`, under a comment saying the one-time dump existed so the schema "can be confirmed in-game") — if all three guesses were wrong the player path recorded nothing, silently, forever, while the AI path kept working. **PASS:** fly a player TARPS sortie over a fogged enemy site, land, and confirm (a) the "RECON: … confirmed BDA on N target(s)" cue appears **only after touchdown**, not over the target, and (b) the site is un-fogged at debrief; repeat with an AI-flown recon flight and confirm identical behaviour. Then fly one pass HIGH (≥40,000 ft) and one at a normal recon altitude over comparable sites and confirm the high pass banks fewer targets. **FAIL signatures:** the cue firing over the target (the landing gate broke); a player sortie confirming nothing while an AI one works, or vice versa (the two paths have diverged again — the exact defect the rebuild removes); nothing ever confirming (check the `DCSRetribution|Recon armed for N recon flight(s)` line at load); or altitude/cloud making no difference at all. NOTE the deliberate asymmetry — the CAPTURE happens on overfly and is **not** gated on landing, because missions routinely end before flights land; only the cue waits. Emitter + runtime are covered by `game/missiongenerator/tests/test_reconluadata.py` (16) and `tests/lua/test_recon_runtime.py` (13), which pin the landing-held cue, the capture surviving a flight that never lands, and both degradation curves) (was ✗ REGRESSED 2026-08-05 — "G2 needs reworking"; was ☑ VERIFIED 2026-06-24 as the MOOSE TARS bridge
- **Setup:** Fly an F-14 TARPS recon pass over enemy targets.
- **Pass:** Captured-target snapshots feed back into Retribution's BDA
  fog-of-war (confirmed composition/damage after the pass).
- **Fail signature:** Film menu never unlocks, or captures don't reach the
  debrief / don't update BDA.

### G3 — TIC ambient fire / dynamic fronts · §9 · ☑ VERIFIED

**History:** 2026-06-24
- **Setup:** Fly over an active front, including where terrain (towns/ridges)
  blocks line-of-sight between combatants.
- **Pass:** The front looks **alive from the air** — tracers/impacts around real
  enemy positions even where LOS is blocked (ambient area-fire), without aimed
  lethality spikes.
- **Fail signature:** Front goes silent/dead-looking where LOS is blocked.
  Note: with StormTrooper AI on (default), TIC cloaks managed groups — known
  limitation, not a bug.

### G4 — C-130J EW/ISR mission systems · §2 · ☑ VERIFIED

**History:** 2026-06-24
- **Setup:** Fly the C-130J-30 JAMMING slot (static slot, player-only).
- **Pass:** EW (area/directional/spot jamming, missile spoof, pod loadout) and
  ISR (passive detection, ELINT map marks, SIGINT reports, crew handoff) work
  per `C-130J-30 Mission Systems Overview.txt`.
- **Fail signature:** Menu missing/erroring (would now be caught earlier by the
  Lua syntax gate), or any of the documented EW/ISR actions not firing.

### G5 - Retired generic EW/Jammer Script stays gone - §2 - ☑ VERIFIED

**History:** 2026-06-25
- **Verified (2026-06-25, in-game):** no generic Jammer/`EWJamming` F10 menu on the fighter
  and the generated mission carried no `ewrj`/`startEWjamm`/`startIAdefjamming` actions; the
  C-130J JAMMING slot kept its own `c130j` menu. Fail signature did not occur.
- **Setup:** Generate a mission with a player F-16C carrying its ALQ-184 pod and
  an AI SEAD/DEAD package that would previously have been eligible for `ewrj`.
- **Pass:** No generic "Jammer menu" / `EWJamming` F10 commands appear on the
  fighter, no `startEWjamm` / `startIAdefjamming` waypoint actions are present
  in the generated mission, and the C-130J JAMMING slot still uses only the
  `c130j` Mission Systems menu.
- **Fail signature:** The old generic jammer menu appears on fighters, or the
  generated mission references `ewrj`, `EWJamming`, `startEWjamm`, or
  `startIAdefjamming`.

### G6 — MANTIS IADS engine (phase 1: core networking) · MANTIS migration · ☑ VERIFIED

> **Superseded 2026-09-12.** The MANTIS bridge is removed; Skynet is the engine again
> (`retlab-skynet-return-notes.md`). Kept as the record of what was flown. The live row is **G42**.

**History:** 2026-06-25
- **Verified (2026-06-25, in-game, zone-node map):** the C2-regression re-fly passed — red SAM
  radars came up on RWR at start (no spurious decapitation from the scenery-node `node_dead`
  fix) and bombing a comms mast / power hub still degraded its dependent SAMs. Combined with the
  2026-06-24 routing/network-build/C2-degradation pass below, MANTIS phase 1 is confirmed.
- **⚠️ Regression found + fixed 2026-06-24 (GermanyCW):** many IADS comms/power/
  command-center nodes are destructible **scenery** (comms masts, power hubs, VOR/DME,
  beacons) — NOT placed statics — so `StaticObject.getByName(name .. " object")` never
  finds them. The old `static_dead` read "not a static" as "destroyed" → mass-decapitated
  the whole network on the first poll → all SAMs offline → **empty RWR.** Fix
  (`mantis-config.lua`, `node_dead`): a node counts as dead only on **positive** evidence —
  a placed static of that name existed and no longer `:isExist()`, **or** its name is in the
  global **`dead_events`** table (the S_EVENT_DEAD / scenery-trigger record Retribution
  already keeps; matched with the `"id | "` prefix stripped, since scenery is recorded by
  bare name). This keeps the bomb-the-comms feature working for scenery targets while
  killing the false decapitation. **Re-fly needed:** GermanyCW campaign — (1) red SAM
  radars come up on RWR at start (no spurious decapitation); (2) bombing a comms mast /
  power hub still degrades its dependent SAMs (`MANTIS C2 - comms/power '…' lost`).
- **Result (2026-06-24):** PASSED on engine routing, network build, and C2
  degradation — the high-risk parts. Confirmed from `dcs.log` + the
  `retribution_nextturn.miz` marker + a Tacview (`Tacview-20260624-160553`):
  - **Routing/build:** `Skynet … engine is 'mantis' … skipping` + MANTIS built
    both coalitions (`RED 14 SAM/19 EWR`, `BLUE 3 SAM/4 EWR`), MANTIS v0.9.34 +
    INTEL/DLINK started clean, **C2 watchers armed for RED and BLUE**. No Lua errors.
  - **C2 events fire:** comms kill → `MANTIS C2 - comms '…' lost; degrading 1 SAM(s)`;
    power kill → `MANTIS C2 - power '0378 | Repair workshop' lost; 13 SAM(s) offline`.
  - **Degradation sticks (the #1 risk):** the degraded *networked radar* SAMs
    (SA-3/5/6) stayed offline against live AI blue targets — **MANTIS did NOT
    re-enable them** on its detection cycle. The only late Tacview launches were
    autonomous SHORAD (SA-8 Osa, 2S6 Tunguska), which are out of C2 scope by design
    (`IadsRole.participate` excludes `POINT_DEFENSE`/`NO_BEHAVIOR`; standalone SHORAD
    maps to `SAM` and is only networked if within power/comms range). So the revival
    bug the handoff flagged **did not occur**.
  - **Caveats / remaining:** (a) observation was AI-vs-AI; the **emissions-control
    "dark until in range" path flown by a human is not yet eyeballed** (lower risk —
    minor follow-up). (b) Tacview *corroborates* but can't fully *isolate* C2-silence
    from blue SEAD also killing the SA-3/5/6 radars by 37:37 — the decisive evidence
    is the direct observation that degraded SAMs stayed down. (c) **13-of-14 red SAMs
    hung off one power node** — almost certainly a **per-campaign power-source placement**
    artifact (SAMs auto-connect to any power source within 35nm, `IadsRole.connection_range`),
    not an IADS-generator bug. Revisit as a campaign-`.miz` layout check only if the
    over-concentration recurs across other campaigns.
- **Setup:** In settings, set **IADS engine → MANTIS (experimental)** (Mission
  Generator → Gameplay), generate a mission with red SAMs + EWRs, and fly into the
  IADS. Confirm via `dcs.log` that `mantis-config.lua` built
  the network ("building Retribution-RED-IADS (N SAM, M EWR group names)") and that
  `skynetiads-config.lua` logged "engine is 'mantis' ... skipping".
- **Pass:** SAM radars stay dark (emissions control) until a target is in range,
  then go active and engage; EWRs cue the network; both coalitions build if present;
  with the default Skynet engine the mission is byte-for-byte unchanged (MANTIS
  bridge logs "engine is 'skynet' ... skipping").
- **Fail signature:** No SAM activity at all (FilterPrefixes matched nothing — check
  generated group names vs the names in `dcsRetribution.IADS`), or *every* coalition
  group goes active as EWR (an empty set collapsed into a match-all — the `NO_MATCH`
  guard failed), or both bridges run / neither runs (engine-marker plumbing), or a
  group name that is a strict prefix of another double-registers.
- **Phase-4 tuning to watch:** SAM engagement range / max-active-SAMs / detection
  interval take effect (compare engagement ranges vs the options); with EWR
  auto-relocate on, mobile EWRs reposition over time.
- **Phase-5 C2 (advanced_iads campaign only) — the highest-risk part:** kill a comms
  tower → its dependent SAM should go autonomous (alarm RED) within the poll interval;
  kill a power source → dependent SAM goes offline (AI off, radar dead); kill all
  command centers → the whole coalition's SAMs degrade. Watch `dcs.log` for
  `MANTIS C2 - ...` lines. **Key fail signature:** a SAM the watcher disabled comes
  back to life on MANTIS' next detection cycle (MANTIS re-enabling it) — degradation
  doesn't "stick." If seen, the watcher must remove the SAM from MANTIS' set, not just
  toggle the group.

### G7 — MIST → MOOSE shim (`mist_moose_shim.lua`) · MIST retirement · ☑ VERIFIED

> **Superseded 2026-09-12.** The shim is deleted and upstream's `mist_4_5_126.lua` loads again.

**History:** 2026-06-25 (GermanyCW)
- **Result (2026-06-25):** PASSED. With `base/plugin.json` loading the shim instead of
  `mist_4_5_126.lua`, a full GermanyCW session logged **zero `mist_moose_shim` errors** —
  MANTIS built, CTLD spawned crates (shim `dynAddStatic`), intercept QRA configured (shim
  `dynAdd`, after the `_resolve_group_category` fix), core glue ran. The two crashes seen
  during testing were **pre-existing** bugs unrelated to the shim (civ-helo RAT sim crash;
  CTLD smoke-zone string/number format), both fixed in #166.
- **Follow-up (2026-06-26):** A later GermanyCW pass still hit a native DCS
  `wSimCalendar::DoActionsUntil` crash during fixed-wing `RAT_CIV_C130` landing/respawn
  churn. Civilian traffic now runs as one-shot scenery: RAT ATC is disabled and flights do
  not respawn after landing. Re-test by leaving civilian traffic enabled for a Combat SAR
  pass and watching for any new `RAT_CIV_*` crash lead-up.
- **Pass:** No `mist_moose_shim.lua:<n>` errors in `dcs.log`; CTLD sling-load (load/drop
  troops, sling+unpack a crate, build a FOB), SCAR capture + CSAR, intercept/QRA, and core
  state-write/messages all behave as on MIST.
- **Fail signature:** any `mist_moose_shim.lua` Lua error (a consumer hit an unimplemented/
  wrong-shaped symbol). **Final cleanup DONE (2026-07-10):** `mist_4_5_126.lua` deleted after
  weeks of clean flights across campaigns — rollback is now `git checkout <pre-deletion-sha> --
  resources/plugins/base/mist_4_5_126.lua` + re-pointing `base/plugin.json`'s `"mist"`
  work-order back at it.

### G8 — Combat SAR pilot rescue (`combatsar` / MOOSE CSAR) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · Combat SAR Phase 2 · ☑ VERIFIED (2026-06-28, audience in-game pass — user: "pilot rescue attempted looks good")

</details>
- **In-game (2026-06-28, audience pass — user verdict "looks good"):** a Combat SAR pilot rescue was flown/attempted and behaved correctly — the SAR ran as designed with no Lua error. As with J1/J2 this is the user's eyes-on "looks good," not a deeply-isolated audit of the pickup→deliver→`combat_sar_rescues`-increment loop (that precise count is the G11 scoring row). Don't re-mark UNTESTED without flying it.
- **Live-log confirmation (2026-06-27, GermanyCW Fulda/Haina, `dcs.log`):** the plugin armed
  clean — `CSAR (Blue) | Started (1.0.34)` then `DCSRetribution|Combat SAR plugin - CSAR started
  with 1 rescue helo group(s), 1 King(s), template 'Combat SAR Downed Pilot', enableForAI=false`.
  So: the `Combat SAR Downed Pilot` template **resolved** (the "missing template" fail signature
  is absent), the rescue-helo group and King both registered, **no `combatsar-config.lua` Lua
  error** anywhere in the run, and `enableForAI=false` (correct, setting off — the "AI ejection
  spawns a pilot" leak can't occur). **Residual (still in-cockpit):** the actual pickup→deliver→
  count loop — and note that loop needs a **player in the rescue helo**: in this sortie the CH-47F
  is an **AI group** and the only player client is the C-130J-30 King, so flying the King alone
  does not exercise the pickup.
- **Setup:** A campaign with a blue **CH-47** squadron; plan a **Combat SAR** flight (CH-47) near
  the FLOT (optionally a C-130 Combat SAR "King" too). Fly it, then have a **human** pilot eject in
  the area (a second slot, or eject yourself from a separate fighter).
- **Pass:** On the human ejection a downed pilot spawns with a radio beacon; the CH-47's F10 CSAR
  menu shows the active SAR; the helo hovers/lands within pickup range, boards the pilot, and
  delivers to a friendly airfield/FARP (rescue count increments). `dcs.log` clean. The C-130 "King"
  just flies its orbit (never lands). The existing SOF-recovery CSAR (SCAR loop) is undisturbed.
- **Fail signature:** any `combatsar-config.lua` Lua error; the downed pilot never spawns
  (missing `Combat SAR Downed Pilot` template, or `SPAWN:NewWithAlias` nil); an **AI** ejection
  spawns a pilot (means `enableForAI` leaked true); a non-CH-47 helo gets the rescue menu (rescue
  set mis-bound); or double event-handling with the SOF CSAR. If the helo can't deliver anywhere,
  check `allowFARPRescue` / that a friendly airfield is in range.

### G9 — Combat SAR AI on-demand rescue (`auto_combat_sar`) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §21 · ◐ PARTIAL (2026-07-17 flown PG "Scenic Route Merged", Tacview `Tacview-20260717-172716`, session `dcs-mission-test-040ece`: **both spawn paths fired live** — the fly-critical parked-first path WORKED (3 of the 4 Khasab ramp UH-60As started in place ~7 min after the first ejections and flew 95–113 km toward the correct survivors; the closest ended the mission 3.0 km from its survivor) and the clone fallback spawned for the later survivors ("CombatSAR Rescue 6", a real flying UH-1H). **Zero pickups completed** — not a code failure but geometry: survivors 115–140 km (land, deep Iran) and ~370 km (the fleet survivors vs the clone's rear-field spawn) from the rescue sources, so a 130 kt helo arrives as the mission ends ("after 1.4 h the rescue helos are just getting to the pilots" — the finding that drove the §21 pilot-recovery surge, G31). **Open items:** "CombatSAR Rescue 8" spawned and was removed within 1 s (a failed clone spawn — one lost rescue); NO enemy snatch party spawned all mission despite 3 land survivors (3× ~50% rolls all missing is possible but unlucky — watch it next fly; the 3 sea survivors can't draw one by construction); and the actual OPSTRANSPORT pickup+delivery loop is still unexercised because nothing ever got close enough. REWORKED 2026-07-06 — the standing orbit is retired; `auto_combat_sar` spawns an on-demand rescue **parked-first / clone-fallback** when a pilot goes down and no player CSAR package is up. The gate + parked/clone emit are unit-tested (~~`tests/missiongenerator/test_combat_sar_sandy_luadata.py`~~ + `test_combat_sar_templates.py`). The old orbit's 2026-06-28 "good" verdict below is moot — NEW model)

</details>
- **What changed (2026-07-06 on-demand rework, §21):** the auto-fragged orbit (`PlanCombatSar`) is deleted; when a pilot goes down with no player CSAR/SCAR package fragged, the combatsar runtime rescues from, in order, **(1) a real rescue helo parked cold on the ramp** (`parkedHelos` — `commandeerParkedHelo` + `StartUncontrolled`; a *tracked* `UnitMap` airframe, loss recorded) or **(2) a cold clone template** (`heloTemplate`) when the ramp is bare. Both fly the OPSTRANSPORT pickup — a *parked* start replaces the retired commandeer of an *airborne* helo. **Pass:** with `auto_combat_sar` ON and NO CSAR package fragged, eject near the front → `dcs.log` cue "a rescue helo is launching from the ramp" (or "an AI rescue helo has launched" for a clone) + an OPSTRANSPORT to a friendly field + a delivered survivor spared at debrief; a killed parked rescue helo is a **recorded** loss; with a player CSAR package fragged, NO auto spawn (`autoSpawn=false`). **Fail:** the parked helo is commandeered but never starts/moves (the `StartUncontrolled` path — the fly-critical unknown; if so, make the clone primary), never reaches the survivor, or a spawn happens despite a fragged player package (the gate broke). The historical orbit-era notes below are retained for context only.
- **Gate NARROWED (2026-07-15, squadron call — the resolved "AI-rescue off" investigation):** the flown
  M1 log's `AI-rescue off` was this row's suppression gate firing on a **bare player Sandy** (`0 King(s),
  1 Sandy(s)` — a SCAR escort with no helo counts as "a player package"), which left the mission with zero
  rescue capability. The gate now counts only **rescue-capable** flights: a player CSAR **helo** suppresses
  the AI spawn; a bare Sandy/King **draws** the AI helo and escorts/tracks it
  (`tests/missiongenerator/test_combat_sar_sandy_luadata.py::test_bare_sandy_does_not_suppress_autospawn`
  / `::test_bare_king_does_not_suppress_autospawn`). The **Pass** line above updates accordingly: with a
  player *Sandy-only* plan, expect `autoSpawn=true` + the AI helo launching alongside the Sandy.
- **Player-package AI rescue helo now actively flies the pickup (2026-07-30 flown fix):** the earlier gaps left a hole — with `autoSpawn=false` (the player fragged a rescue-capable **helo**) the ONLY rescue path was the geometry pickup (`findBoardingHelo`), which merely *detects* a helo a human already flew low+slow onto the survivor. So an **AI-crewed** rescue helo in the player's own package was never routed anywhere: flown 2026-07-30 (a CH-47D + AH-1W + C-130 King package, King flown by the player), the AI CH-47 flew its planned CSAR orbit and **never got closer than 23 km** to the downed pilot (Tacview). Fix (`combatsar-config.lua`): `dispatchAIRescue` now commandeers an AI-crewed rescue helo from `cfg.rescueHelos` FIRST (before parked/clone), and the tick's dispatch gate fires when `autoSpawn` is on **or** an AI-crewed rescue helo is available — so a player package with an AI helo gets an active OPSTRANSPORT pickup. A **player-crewed** rescue helo is untouched (the human flies it; geometry credits it). Delivery-field resolution no longer needs `cfg.farp` (absent for a player package) — nearest resolvable friendly field. Harness-locked in ~~`tests/lua/test_combatsar_ai_rescue_dispatch.py`~~ (AI helo IS commandeered, player helo is NOT). **Pass:** frag a package with an **AI-crewed** rescue helo + fly the King yourself; on an ejection the AI helo breaks off, flies to the survivor, lands/loads (OPSTRANSPORT) and delivers to a friendly field. **Fail:** the AI rescue helo keeps flying its orbit and never approaches the survivor (the commandeer/OPSTRANSPORT didn't take — the airborne-commandeer risk, cf. G21), or a *player-crewed* helo gets yanked off the human's control.
- **Generation-crash HOTFIX (2026-07-07, found on the first in-game generation attempt):** `spawn_combat_sar_templates` crashed the whole miz generation with `ValueError: 'Jolly' is not in list`. Root cause: the cold clone-template flight was built as a `COMBAT_SAR` flight, which carries the fork-custom **'Jolly'** role callsign; when the helo squadron's helipads were full the spawner fell through to the airfield path, where pydcs `_assign_callsign` can't resolve 'Jolly'. Fixed: build the template flight as a **BARCAP** (airfield-valid callsign — exactly what `_spawn_unused_for`/QRA templates use), and wrap template creation in a broad `except` so an optional rescue template can **never** break generation (it degrades to the parked-ramp helos). Regression tests in ~~`tests/missiongenerator/test_combat_sar_templates.py`~~. The G9 fly can now proceed.
- **Re-fly PASSED (2026-06-28, audience pass — user verdict "good"):** the eject-trigger fix (`aicsar.UseEventEject=true` + the AI-eject bridge that calls `aicsar:_EventHandler` on a blue AI ejection) cleared the earlier 2026-06-28 FAIL recorded below — the AI standing-alert rescue now triggers and behaves in-cockpit. This flip assumes the flown build carried the fix (per the user, it did). The original FAIL root-cause is retained below for history.
- **In-game pass 2026-06-28 (session `f08e522b`) — AI rescue did NOT trigger; root-caused + fixed; re-fly owed.**
  Flew the C-130 King with `auto_combat_sar` ON (GermanyCW Fulda/Haina, turn 1). A **blue AI ejected**
  near the front (Tacview: 2 `Country=de`/`Color=Blue` chutes at ~3 km). Plugin armed correctly —
  `CSAR (Blue) Started`, `AICSAR ... armed (helo template ..., FARP 'Frankfurt')`, `enableForAI=true`,
  King `TACAN 39Y, LARS menu attached`. **No rescue launched; LARS showed no survivor.** Root cause
  (read from `Moose.lua`): stock **AICSAR dispatches only on `S_EVENT_LANDING_AFTER_EJECTION`** — the
  pilot must touch down (~8–9 min under canopy from ~3 km) and that DCS event is unreliable for AI; its
  eject fast-path is player-only (`IniPlayerName`). The mission ended **57 s after the ejection** (pilot
  still at ~3 km in Tacview), so nothing could have started even on a clean run. **Fix landed
  (`combatsar-config.lua`):** `aicsar.UseEventEject=true` (landing handler no-ops → dedup) + an ejection
  bridge that calls `aicsar:_EventHandler(event, true)` the instant a blue AI ejects → survivor spawns
  under the ejection point + helo launches immediately. **Re-fly owed:** AI ejects in range → an AI helo
  spawns from the FARP within seconds and recovers; `dcs.log` shows
  `Combat SAR - AI eject rescue dispatched for '<unit>'`. **Secondary finding (not fixed here):** the
  King's **LARS never lists AI survivors** (player CSAR runs `enableForAI=false`) — follow-up if humans
  should be able to cue AI rescues. **Don't re-mark this UNTESTED without flying the fix.**
- **Live-save + branch re-verify (2026-06-27, headless session `78eae772`):** loaded the live
  `autosave.retribution` (Nevada/Tonopah, turn 1) headless with `auto_combat_sar` **ON** — the blue ATO
  frags **both** Combat SAR airframes (`CH-47F Block I` + `C-130J-30` King) and **red frags zero**, so
  the blue-gate holds on a real auto-planned ATO (the "CSAR planned for red" fail signature did not
  occur). `test_combat_sar_planning.py` + the scoring/placement suite re-ran **green on this branch**.
  **Residual unchanged (cockpit only):** the AI helo actually **spawning from the FARP and flying the
  rescue** (MOOSE `AICSAR` runtime) — not headless-provable.
- **AI rescue re-wired to MOOSE `AICSAR` 2026-06-26 (PR pending in-game pass):** the 2026-06-26
  playtest showed the AI rescue helo just orbited and never recovered anyone — MOOSE CSAR's
  `enableForAI` only *tracks* AI ejections, it never flies an AI helo. The AI path now uses
  `AICSAR` (spawns its own rescue helo from the FARP base on a pilot-down event). Pass criteria
  below updated to match: watch for a helo **spawning from the home base**, not the orbiting
  flight diverting.
- **Orbit-placement fix 2026-06-25 (found in-game, fixed — re-observe):** the standing-alert orbit
  used to **mirror the AWACS** (it reused the AEW&C builder → 80 NM standoff + 60 NM racetrack), so a
  CH-47 could never reach an ejection. Combat SAR now flies a **dedicated forward hold**
  (`game/ato/flightplans/combatsar.py`): front-anchored, **15 NM** threat buffer, **5 NM** racetrack
  half-length. Re-observe that the planned CSAR orbit now sits **near the FLOT**, not back at AWACS depth.
- **Placement adjudicated headless (2026-06-27):** Measured the real anchor the planner computes on the
  live `autosave.retribution` (GermanyCW, Fulda/Haina front) by calling `support_orbit_anchor` for the
  Combat SAR 15 NM buffer and contrasting with the 80 NM AEW&C buffer it replaced. Result: CSAR orbit
  centre **25.2 NM** from the FLOT (auto-pushed back from the 15 NM nominal only as far as needed to clear
  the red threat ring) vs the AWACS-depth anchor at **90.3 NM** — **65 NM further forward**. Orbit centre
  **and both racetrack endpoints test clear of the red threat zone** (`threatened()=False`), and the
  racetrack is a tight **10.0 NM** hold (not the 60 NM AEW&C track). So the placement fail signatures —
  "orbit again at AWACS depth / mirrors the AWACS racetrack" and "orbit inside an enemy threat ring" — do
  **not** occur on this campaign; the forward-hold fix is structurally in effect. **Residual (cockpit
  only):** the AI helo actually **spawning from the FARP and flying the rescue** (the MOOSE `AICSAR`
  runtime) and the package appearing in the ATO with `auto_combat_sar` ON — neither is headless-provable.
- **Setup:** Enable **Automatic Combat SAR** (HQ automation settings; default OFF). Campaign with a
  blue **CH-47** squadron + budget. Auto-plan turn 1 (observe-only, don't fly the CSAR).
- **Pass:** A blue **AI** `Combat SAR` package appears in the ATO, **holding a tight racetrack near an
  active front** (one per front, capped by available CH-47s) — clearly forward of the AWACS/tanker
  orbits, clear of enemy threat rings. The generator logs `enableForAI=true`. When a pilot ejects in
  range, a rescue helo **spawns from the FARP home base** (AICSAR), flies to the survivor,
  lands/hovers to recover, and RTBs — with no human in any helo (AICSAR `autoonoff` stands down if a
  player crews a rescue helo). `dcs.log` shows `AICSAR AI standing alert armed (helo template ..., FARP ...)`.
  Known v1 gaps to note (not fail): no spare-pilot scoring credit for AICSAR rescues; a fixed-wing
  player ejection with no human helo up double-spawns (CSAR + AICSAR).
- **Placement fail signature:** the CSAR orbit again sits at AWACS depth / mirrors the AWACS racetrack
  (the dedicated `CombatSarFlightPlan` didn't take — check `flightplanbuildertypes.py` maps
  `COMBAT_SAR` to `CombatSarFlightPlan`, not `AewcFlightPlan`); or the orbit lands inside an enemy
  threat ring (15 NM buffer too tight for that campaign's FLOT SAMs).
- **Fail signature:** no CSAR package planned with the setting on + a CH-47 squadron present (HTN/
  fulfiller gap — check `combat_sar_targets` populates and a CH-47 is purchasable); a CSAR planned
  for **red** (blue-gate leaked); the AI helo orbits but never diverts to a downed pilot
  (`enableForAI` not reaching the engine, or MOOSE AI-rescue routing vs. Retribution's flight plan);
  or the AI rescue routing fights the despawn/RTB logic. **Off-state regression check:** with the
  setting OFF, confirm no CSAR is auto-planned and `enableForAI=false` is logged.
- **Off-state confirmed in live log (2026-06-27, GermanyCW, `dcs.log`):** with `auto_combat_sar`
  OFF, the plugin logged `... CSAR started with 1 rescue helo group(s), 1 King(s), ...
  enableForAI=false` — i.e. the standing-alert AI path is correctly dormant (no AICSAR spawn, no
  AI pilot tracking). The **AI-ON** path (helo spawns from FARP, flies the rescue) still needs its
  own run with the setting on.

### G10 — Combat SAR King TACAN beacon + LARS · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · Combat SAR Phase 4 · ◐ PARTIAL (2026-07-02 flown Trail 2 session `wonderful-chatterjee`: the 2026-06-30 activation fix WORKED — `dcs.log` shows the mission-start miss falling back cleanly ("not found/alive at mission-start; will retry") and then "activated … via birth (TACAN 37Y, LARS menu attached)" when the player boarded the King C-130; zero combatsar errors. Still owed = a wingman actually tuning 37Y to confirm the beacon radiates + an in-mission LARS menu use)

</details>
- **2026-07-06 (Inherent Resolve session `jovial-gates-574c9c`): the OTHER activation path re-verified** —
  an AI-flown King alive at t=0 activated directly via mission-start ("Combat SAR King - activated
  'Front line Balad Airbase/Tikrit Combat SAR|2|21|C-130J-30|' via mission-start (TACAN 37Y, LARS menu
  attached)"), zero errors. Both activation paths (mission-start and birth-on-player-board) have now each
  passed in a flown session; the tune-37Y + LARS-use items are still the open half of this row.
- **Regression (2026-06-30, flown session — user: "c130 had no F10 menu for LARS"):** the player-flown
  King's LARS menu, previously cockpit-confirmed 2026-06-27, did **not** appear this session.
  `dcs.log` shows **zero** `Combat SAR King - activated` lines across ~80 minutes and two mission
  loads, despite the player successfully joining the King's cockpit both times
  (`Player 'Wizard 1-4 | Flash 402' joined unit '...C-130J-30| Pilot #1'` at `00:10:27` and again at
  `00:18:02` after a mission reload) and the generated `.miz`'s `dcsRetribution.CombatSAR.kings`
  table carrying the **exact correct** group name (`Front line Kutaisi/Senaki-Kolkhi Combat SAR|2|18|
  C-130J-30|`, verified byte-for-byte against the DCS client-registration log line) — so this was not
  a group-name mismatch. **Root cause (best available without a Lua interpreter — CLAUDE.md prohibits
  running/compiling Lua here, so this is read-diagnosed):** `activateKing()`'s early-return guards
  (not-alive / no-unit / not-found) were all silent (no logging), and the only two activation paths —
  a one-shot mission-start scan and the `Birth`/`PlayerEnterAircraft`/`PlayerEnterUnit` event handlers
  — both had single points of failure: the mission-start scan never retries if the King isn't queryable
  yet (e.g. during the pre-"sim running" briefing/slot-selection pause — this session's log shows the
  sim didn't reach `state=ssRunning` until `00:18:30`, well after the player joined the King at
  `00:18:02`), and the event path resolves the group via `EventData.IniGroup`/`IniGroupName`, both of
  which can be unpopulated for `PlayerEnterAircraft`/`PlayerEnterUnit` (confirmed via `Moose.lua`:
  `IniUnit` is populated far more reliably than `IniGroup`/`IniGroupName` for these event types).
- **Fix applied (2026-06-30, `resources/plugins/combatsar/combatsar-config.lua`):** (1) every early-return
  in `activateKing()` now logs why (`Combat SAR King - '<name>' not yet alive/has no unit #1 (<reason>)`),
  turning a future silent failure into something diagnosable in `dcs.log`; (2) `activateKingFromEvent`
  now falls back to `EventData.IniUnit:GetGroup()` when `IniGroup`/`IniGroupName` are both absent; (3) a
  new periodic **retry sweep** (`retryUnactivatedKings`, piggybacked on the existing 5 s `POLL` cadence)
  re-tries `GROUP:FindByName` for any King not yet in `activatedKings` every 5 s until it succeeds, so no
  single missed mission-start/event moment can permanently block activation for the rest of the mission.
  Lua syntax read-checked (balanced blocks verified by hand — no local interpreter available).
  **Needs a re-fly** to confirm the LARS menu now appears and `Combat SAR King - activated` shows in
  `dcs.log`.
- **Cockpit-confirmed (2026-06-27, user in-game pass — session `suspicious-goldberg`/`1ca51fbf`):**
  the player-flown King's **F10 → Combat SAR → LARS menu works** ("F10 LARS good") — the #196
  player-King menu-attach fix is verified live. The remaining PARTIAL is only the **AI-King scripted
  TACAN beacon** (player King has no AI controller, so it dials TACAN in-cockpit by design — not a
  fault). *(This confirmation was given in-game and dropped — PR #226 recorded only the headless
  evidence, not the three cockpit wins; recovered here.)*
- **Setup:** Plan a player **C-130** Combat SAR ("King") alongside a **CH-47** Combat SAR. Fly the
  King; have a human pilot eject in the area. **For the scripted TACAN path, the King must be AI**
  (e.g. `auto_combat_sar` standing alert) — a player-flown King sets TACAN in-cockpit (see below).
- **Pass:** An **AI** King radiates its TACAN (rescue helo can tune + home, and it **tracks the moving
  orbit** — bearing/range stay sane as the King flies its racetrack). The King's F10 **Combat SAR →
  LARS** lists each active survivor with position and bearing/range from the King, sorted nearest-first;
  "no active survivor radios" when none. (ADF dropped — TACAN is the only homing aid.) Generator logs
  `... %d King(s) ...`.
- **Fail signature:** any `combatsar-config.lua` Lua error; **`ALERT ... AI::Controller exception: No
  executor for command "ActivateBeacon"`** followed by a CTD (`ACCESS_VIOLATION` in
  `wSimCalendar::DoActionsUntil` / `CommandsTraceDiscreteIsOn`) — this was the **2026-06-25 crash**
  when the King was player-flown; **now guarded** (`activateKing()` skips `ActivateTACAN` unless
  `unit:IsAlive() and unit:GetPlayerName() == nil`). AI-King fail: TACAN absent (no channel allocated,
  or `ActivateTACAN` not firing) or **frozen at the spawn point** instead of tracking; LARS empty when
  survivors exist (`csar.downedPilots` not read) or duplicated F10 entries
  (birth/start-sweep/player-enter dedup failed); King menu missing on a player client-slot,
  delayed, or AI King (activation handler not attaching).
- **Note (player King):** A human-flown King has no AI controller, so the scripted beacon is **skipped
  by design** — the crew dials the planned channel manually in the cockpit. Re-test target: confirm an
  **AI** King still lights its TACAN and no CTD recurs with a player King.
- **Player-King F10 menu fix (PR #196, `c09ffc512`, 2026-06-25):** The King's F10 **Combat SAR → LARS**
  menu was only attached on `EVENTS.Birth` + mission-start, which **races DCS's F10-menu creation for a
  player client slot** — so a player-flown King got **no F10 menu**. Fix adds
  `PlayerEnterAircraft`/`PlayerEnterUnit` handlers plus a **1 s deferred retry**, nil/dead/no-unit guards,
  and an `env.info` line `Combat SAR King - activated '<name>' via <reason> (... LARS menu attached)` so
  the attachment is now visible in `dcs.log`. **The 2026-06-25 flight (player King, no F10 menu) predated
  this fix** — the flown build was generated `21:43`, two minutes after #196 merged at `21:41`, so its
  binary could not have contained it (it also still carried the FlightControl plugin removed later in #200).
  Re-test on a build containing #196: the player King's LARS menu appears (immediately or within ~1 s) and
  the new `... LARS menu attached` line shows in the log.

### G11 — Combat SAR rescue scoring (pilot spared at debrief) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · Combat SAR Phase 4 · ☑ VERIFIED (2026-06-30, `414TH.retribution` save + `state.json` — user confirmed "rescue worked")

</details>
- **Verified (2026-06-30, headless save load — `414TH.retribution`, turn 5):** `game.last_sitrep`
  reads `Sitrep(turn=4, ..., pilots_recovered=3)` — the SITREP the debrief itself computed from
  `commit_air_losses`, matching `state.json.combat_sar_rescues`'s 3 entries exactly and the debriefing
  screenshot's loss counts (10 USA / 7 Vietnam aircraft) verbatim. This is the Python-side confirmation
  the prior PARTIAL note was waiting on — the delivered pilots were genuinely spared, not just logged
  by the Lua bridge. User cockpit-confirmed the same thing independently ("rescue worked"). Fail
  signature did not occur.
- **Partial (2026-06-30, flown session — `state.json`):** `combat_sar_rescues` came back non-empty with
  **3** real, well-formed unit names (`Kutaisi_AJS37_475-1`, `Kutaisi_UH-1H_536-1`,
  `Kutaisi_AH-64D BLK.II_928-1`) — direct proof the Lua `OnAfterRescued` → `combat_sar_rescues` bridge
  fired for 3 separate live deliveries this session, and the names are self-consistent with
  `crash_events` (e.g. `Kutaisi_UH-1H_534-1`/`_630-1` crashed — unrescued — while `_536-1` did not, i.e.
  it was picked up before loss). This directly answers the row's flagged residual (whether the Lua's
  `originalUnit` name actually matches what DCS reports). **Not confirmed from these artifacts:**
  whether `commit_air_losses` on the Python side actually spared these 3 pilots at debrief (that only
  shows up in the processed campaign save / squadron roster after Retribution ingests this
  `state.json`, which we don't have here) — check the next turn's squadron roster or debrief log to
  close this out.
- **Headless adjudication (2026-06-26):** the Python scoring is verified by
  ~~`tests/test_combat_sar_scoring.py`~~ (passing): `commit_air_losses` spares exactly the
  rescued pilot (`pilot.kill` not called) while still attriting the airframe
  (`owned_aircraft` drops), an un-rescued pilot is still killed, and an empty
  `combat_sar_rescues` falls back to "everyone dies" (the safe default). State parsing
  tolerates malformed/empty input. **Residual (in-sim only):** that the `originalUnit`
  name the Lua writes actually matches the name DCS reports in kill/crash events (the
  unit-map resolve) — the test uses identity matching, not real event names.
- **Setup:** Fly a CH-47 Combat SAR (or AI standing alert). Have a **known** human pilot eject near
  the FLOT, pick them up, and **deliver them to a friendly airfield/FARP**. End the mission and run
  the debrief.
- **Pass:** The delivered pilot's **airframe is still counted lost** (squadron `owned_aircraft` drops),
  but **the pilot is NOT killed** — they remain on the squadron roster with their experience. `dcs.log`
  shows `Combat SAR - pilot of <unit> delivered home`; the Retribution log shows
  `Combat SAR recovered the pilot of …`. A pilot picked up but **not** delivered (helo shot down with
  them aboard) is **not** spared.
- **Fail signature:** rescued pilot still killed at debrief (`combat_sar_rescues` empty in `state.json`,
  or the `originalUnit` name doesn't match what DCS reported in kill/crash events — check the unit-map
  resolve in `commit_air_losses`); or a *non*-delivered pickup wrongly spared (`OnAfterRescued` firing
  without delivery). Empty list ⇒ pre-scoring behaviour (everyone dies) — that is the safe fallback,
  not a separate bug.

### G12 — Combat SAR extracts a stranded SOF team · Combat SAR + SCAR · ⊘ RETIRED (2026-07-01 — the dormant SOF capture economy was removed; nothing can strand a team, so there is nothing to extract)
- The whole channel this row tested (`sofTeams` emission → `SOFRESCUE` CASEVAC → `combat_sar_sof_recoveries`
  → `commit_sof_recoveries` refund) was deleted with the rest of the dead commander-capture loop
  (features doc §15). The scoring layer had been headless-adjudicated 2026-06-26 but the path was
  unreachable in a normal campaign since the armor-hunt plugin was removed (#266). Do not re-fly.

### G13 — Combat SAR airframes: armed Chinook + flyable King · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · Combat SAR · ☑ VERIFIED (2026-06-28, audience in-game pass — King wing-tank render OK; EW/ISR-clean + door guns previously confirmed)

</details>
- **Cockpit-confirmed (2026-06-27, user in-game pass — session `suspicious-goldberg`/`1ca51fbf`):**
  the C-130J-30 King flies **clean of the EW/ISR menu** ("Kings no EW ISR") — the `EwExcludedGroups`
  per-group deny-list works in-cockpit. Combined with the **CH-47 door M60D guns confirmed 2026-06-25**
  ("loadout good"), the only residual on this row is the King's external **wing tanks visibly rendering
  on the model** (payload added 2026-06-25; user can eyeball it on the ground — they fly the King, not
  the CH-47). *(The EW-clean confirmation was given in-game and dropped — PR #226 captured only the
  headless/live-log evidence; recovered here.)*
- **Data re-confirmed headless 2026-06-26:** the `Retribution Combat SAR` payloads resolve —
  CH-47Fbl1 mounts the door guns (`{CH47_PORT_M60D}`/`{CH47_STBD_M60D}`) and C-130J-30 mounts
  the two wing tanks (`{C130J_Ext_Tank_L}`/`{C130J_Ext_Tank_R}`); both YAMLs carry a
  `Combat SAR` task; the `C-130 → C-130J-30` migrator alias is present
  (`aircrafttype.py`). **Residual (in-sim only):** the King visibly rendering the wing tanks
  and flying **clean of the EW/ISR menu** (EW per-group deny-list `EwExcludedGroups`).
- **Live-save airframe confirm (2026-06-27):** the flown `autosave.retribution` (GermanyCW) blue wing
  actually carries **both** Combat SAR airframes as real squadrons — `CH-47Fbl1` (5th Battalion 159th
  Aviation) and `C-130J-30` (910th Airlift Wing) — and both report `capable_of(COMBAT_SAR)=True`, while
  the legacy `C-130`/`CH-47F` ids are absent (the migrator left no stragglers). So this campaign can frag
  Combat SAR on both airframes today with no edits; the load succeeded with no `C-130` migrator crash.
- **Live-mission registration confirmed (2026-06-27, `dcs.log`):** the generated GermanyCW mission
  registered both — the rescue helo as an AI group (`Front line Fulda/Haina Combat SAR | CH-47F Block I`,
  2 ships) and the King as a **player client** (`Register Client: ... C-130J-30 | Pilot #1`) — and the
  plugin then reported `1 rescue helo group(s), 1 King(s)`. So both airframes frag + register with no Lua
  error; the C-130J-30 cockpit cold-started fine. **Still in-cockpit:** door-guns/wing-tanks visible on
  the model and the King clean of the EW/ISR menu.
- **In-game 2026-06-25:** tasking offered on **both** airframes ✅; CH-47Fbl1 spawns with its
  **door M60D guns** ✅ ("loadout good"). **Found:** the C-130J-30 King spawned with **no loadout /
  no wing tanks** — the documented removable-pylon case. **Fixed 2026-06-25:** added a
  `Retribution Combat SAR` payload for the C-130J-30
  (`resources/customized_payloads/C-130J-30.lua`) mounting the two external wing tanks
  (`{C130J_Ext_Tank_L}` Pylon 1 + `{C130J_Ext_Tank_R}` Pylon 2; CLSIDs validated against the module).
  **Re-observe:** the King now spawns with visible underwing tanks. **Still to verify:** the King
  flies **clean of the EW/ISR menu** (the other half of this row — EW per-group deny-list `EwExcludedGroups`).
- **Setup:** A blue faction with **CH-47Fbl1** and **C-130J-30** squadrons. Plan a **Combat SAR**
  flight in each. (The stock AI C-130 is retired — C-130J-30, the Airplane Simulation Company
  module, is the only C-130; a fresh game and an in-progress save with an old "C-130" squadron must
  both load and show the C-130J-30.)
- **Pass:** The CH-47Fbl1 is taskable **Combat SAR** and spawns with its **port + starboard door
  M60D guns** mounted (the `Retribution Combat SAR` payload). The C-130J-30 is taskable Combat SAR as
  the **King** and shows its external underwing **fuel tanks** (part of the official module), and
  flies clean of the EW/ISR menu (the `c130j` plugin is suppressed when a King is up). Both are
  player-flyable.
- **Fail signature:** Combat SAR not offered for CH-47Fbl1/C-130J-30 (yaml `tasks` entry missing); the
  Chinook spawns **clean / no door guns** (payload name not matched — `Retribution Combat SAR` must
  resolve, else it falls back to empty; check the door-gun CLSIDs `{CH47_PORT_M60D}`/`{CH47_STBD_M60D}`
  are valid for the installed module); the King has no visible wing tanks (then they are a removable
  pylon on the C-130J-30 module, not model-default — needs the module's tank CLSID added to a King
  payload); the King wears the EW/ISR menu (the `EwExcludedGroups` deny-list didn't exclude it); an
  old save with a "C-130" squadron fails to load (the `C-130 → C-130J-30` migrator alias is missing).

### G14 — C-130J jamming vs MANTIS IADS (no EMCON interference) · §2 / MANTIS migration · ☑ VERIFIED

> **Superseded 2026-09-12.** Under Skynet the engine re-asserts ROE itself, so the jammer's
> `WEAPON_HOLD` / `OPEN_FIRE` writes are self-healing (the pre-June state, flown in G4).

**History:** 2026-06-28, audience in-game pass — EW jamming works, no MANTIS EMCON interference
- **Invariant verified by reading 2026-06-26:** the "must never happen" failure mode (an
  `ALARM_STATE`/emission write creeping into the jammer) is structurally precluded.
  `suppressSAMRoe`/`restoreSAMRoe` (`c130j/c130j_mission_systems.lua:645-659`) are nothing but
  a nil-guarded `setOption(ROE, WEAPON_HOLD)` / `setOption(ROE, OPEN_FIRE)`, and a plugin-wide
  search finds **zero** `enableEmission`/`ALARM_STATE` writes (only comments forbidding them).
  So the jammer composes with MANTIS by construction. **Residual (in-sim only):** that a jammed
  SAM actually holds fire while its radar stays up under MANTIS, resumes when the window expires,
  and that MANTIS-dark SAMs don't wake on the OPEN_FIRE restore.
- **Why:** The jammer suppresses RED SAMs on the **ROE** axis only (`suppressSAMRoe()` /
  `restoreSAMRoe()`); MANTIS (now the default engine) drives SAMs on the **ALARM_STATE** axis and
  never writes ROE. The two are intended to compose cleanly, but the human-flown interaction under
  MANTIS has not been eyeballed (G4 predates the default flip; G6's emissions path was AI-vs-AI).
- **Setup:** A new campaign (so **IADS engine = MANTIS**) with red SAMs/EWRs. Fly the C-130J-30
  JAMMING slot toward the IADS; use Area/Spot jamming on a live red SAM that MANTIS has brought up.
- **Pass:** A jammed SAM **holds fire** while suppressed even though its radar stays up under MANTIS
  (RWR shows the radar but it doesn't shoot / "Suppressed: <type> — clear to engage" banner); when
  the jam window expires the SAM **resumes firing** (ROE returned to OPEN_FIRE). SAMs MANTIS is
  keeping **dark for EMCON do not wake up** as a side effect of the jam restore. `dcs.log` clean.
- **Fail signature:** jamming has no effect (SAM keeps firing while held — ROE write not landing);
  a jammed SAM stays permanently dead after the window (restore not firing — under MANTIS nothing
  else lifts the hold); or a SAM MANTIS wanted dark starts emitting/firing after a jam cycle (an
  `ALARM_STATE`/emission write crept into the jammer — must never happen; check `suppressSAMRoe`/
  `restoreSAMRoe` are still ROE-only).

### G15 — MANTIS SAM range/band override (SEAD) · §2 / MANTIS migration · ☑ VERIFIED

> **Superseded 2026-09-12.** Skynet classifies sites from its own `samTypesDB`; the band
> override went with the bridge. Coverage of that database is audited in the return note §4.

**History:** 2026-06-27 (GermanyCW — bands + detection + engagement; HARM-evasion sub-check & AWACS-less caveat below remain to watch)
- **VERIFIED (2026-06-27, post AWACS-fold fix):** re-fly over the Haina SAMs **drew fire**. `dcs.log`
  confirmed RED `CheckLoop` climbing **0 → 27 → 36–38** as the A-50 got airborne (was `0` × 492 before),
  off a post-fix RED build showing **6 EWR group names** (was 5 — the A-50 now folds in). Bands were
  already correct (override loaded, ASP/FIREFLY/LLAMA→LONG etc.); the blocker was detection, now closed.
  **Still worth a glance on a future pass:** a HARM shot triggering SEAD evasion (radar drop / scoot),
  and an **AWACS-less faction** (relies on dedicated EWR coverage — see the 5th-pass caveat).
- **Bug (found in-game 2026-06-27, GermanyCW):** under MANTIS nearly every Retribution SAM was typed
  **POINT** — confirmed SA-6/SA-10/SA-11/SA-2/SA-3 all POINT (SA-8 wrongly MEDIUM) — so the IADS only
  engaged at ~point-blank range, nothing emitted at standoff, and **SEAD had no targets** ("SAMs never
  engaged / stayed GREEN"). Root cause: MANTIS classifies a SAM by scanning the group's unit type-names
  against its built-in `SamData` table, breaking on the first match; Retribution's multi-radar sites
  (search + track + launchers + a co-located "Dog Ear" EWR) make it pick the wrong radar. The fix
  (`mantis-config.lua`) overrides `MANTIS._GetSAMRange` to band each SAM by **Retribution's own threat
  range** (`dcsRetribution.{Red,Blue}AA[].range`, the planner's MEZ), falling back to MANTIS' native
  logic for anything it can't resolve. Pure-Lua bridge change, no MOOSE-source edit.
- **Active-SAM density (2026-06-27, 3rd pass — "flew over a SAM, no shot"):** with the bands now
  correct, the IADS came alive (Tacview: SA-5 + SA-2 launched, up to 4 SAMs RED), but the
  `Max active SAMs` caps (2 mid / 1 long) meant only a couple of the strategic SAMs were hot at once
  — so an overflown SA-6 site that didn't get a "turn" stayed GREEN. Changed the defaults so
  **medium + long are uncapped (`0 = unlimited`)** — the whole strategic belt engages — while
  **short + point keep a rolling cap (2 / 6)** so the SHORAD layer doesn't all light up on a low
  ingress. `0` is the new "unlimited" sentinel (`uncap()` in `mantis-config.lua`). Watch in-game that
  flying into a medium/long ring now draws fire (mind the overhead dead-zone) and the low SHORAD
  still rolls rather than swarming.
- **EMCON starves detection — the real engagement bug (2026-06-27, 4th pass):** a 23-min flight
  drew **no fire at all** despite correct bands + uncapped actives. `dcs.log`: RED `CheckLoop 0`
  for the whole flight = MANTIS' **detection set was empty**, so `_CheckLoop` had nothing to
  engage. Cause (read in `Moose.lua`): MANTIS detection feeds from two `INTEL` sources — EWRs
  (`IntelOne`) **and the SAMs themselves** (`IntelTwo`) — but with **Emissions Control ON** MANTIS
  forces every SAM radar dark (`EnableEmission(false)`), so `IntelTwo` is empty and detection
  collapses onto the ~5 dedicated EWRs, which miss a low/forward target → blind network → no SAM
  ever fires. **Fix: default Emissions Control OFF** (`useEmOnOff` default → `false`) so the SAMs
  (and SAM-as-EWRs) search on their own radars, feed detection, and engage what's in range — an
  RWR-visible, reliably-engaging IADS. **Re-fly:** flying into a ring should now draw fire promptly;
  re-enable EMCON only on campaigns with proven EWR coverage.
- **AWACS never reached the detection net — the actual blind-RED bug (2026-06-27, 5th pass):** even
  with EMCON **off**, a re-fly over 3 SAMs at Haina still drew **no fire**. `dcs.log` was decisive:
  RED `CheckLoop 0` × **492** (detection set empty the entire flight) while **BLUE `CheckLoop 6`**
  (blue detection fine) — a RED-specific detection failure, not a wake failure. Cause: this corrects
  the 4th-pass note above — in **both** EMCON and AlarmState a SAM is held **passive until cued**
  (it never self-detects; SAM-as-EWRs are dark too), so detection rides entirely on the **always-on
  sensors: dedicated EWRs + the AWACS**. RED's A-50 (`Kastrup AEW&C`) **ground-starts**, so it was not
  a spawned group when the bridge built at T0 — and `add_awacs` gated on a live `Group.getByName`,
  which returned nil and **silently dropped it**. BLUE's E-3A **air-starts**, resolved, and fed
  detection — exactly why blue saw 6 and red saw 0. With no dedicated-EWR coverage at Haina either,
  RED had **zero eyes**. **Fix:** `add_awacs` now folds each AWACS **by name** using a `coalition`
  field newly emitted into the `AWACs` Lua table (`luagenerator.py`), instead of inspecting a live
  group. MANTIS' EWR `SET_GROUP` is dynamic (`dynamic=true → FilterStart`), so the name added at T0
  is matched the moment the A-50 taxis airborne and starts radiating. (`SetAwacs()`/
  `StartAwacsDetection()` were the wrong lever — `StartAwacsDetection` is **dead code, never called**
  in our MOOSE.) **Caveat:** this only restores detection for factions that **have** an AWACS; an
  AWACS-less RED still depends on dedicated EWR coverage (SAM-as-EWRs stay dark) — a separate
  always-on-EWR question if a future campaign proves blind without an AWACS.
- **AWACS-less caveat now instrumented + audited (2026-06-28):** the caveat above is now caught
  automatically — a per-coalition **"blind network" warning** fires when a side has radar SAMs but
  **zero always-on detectors** (dedicated EWR + AWACS), at generation (`luagenerator.py`,
  `logging.warning`) and at runtime (`mantis-config.lua` `env.warning` in `build()`). A scan of all
  64 bundled campaigns (reusing `MizCampaignLoader`) found **3 genuinely BLIND** (Vietnam 1970/1965,
  Egypt 1973 — radar SAMs, no EWR markers, faction has no AWACS) and **18 AMBER** (radar SAMs, no EWR
  markers, but the faction has an AWACS, so detection hangs entirely on it). Dedicated EWRs come ONLY
  from `.miz` `1L13` markers via the `Early-Warning_Radar` layout — SAM layouts don't bundle one — and
  the faction must field an EWR-class unit, so a campaign needs both. **Red Tide fixed (G18).** See
  `retlab-red-tide-campaign-notes.md`.
- **Refinement (found in-game 2026-06-27, 2nd pass):** the override loaded (`SAM range override active
  (57 …)`) but several `(SAM)` sites still came up POINT and an **SA-5 (255 km!) site read POINT**. Cause:
  a Retribution SAM **site has multiple groups under one codename** (the main SAM + a co-located
  point-defense SA-9/SA-13/SA-8), each emitted to `RedAA`; the override indexed range **by codename and
  kept the last-seen**, so the short escort overwrote the real SAM. Fixed by keeping the **MAX** range per
  codename (`index_aa`), so a site bands by its longest reach (ASP/FIREFLY/LLAMA → LONG, DRAGONFLY/ZEBRA →
  MED, etc.). **Known residual:** the point-defense group of a multi-group site inherits the site band
  (slight over-activation; it still only *shoots* at its own range). Per-group precision would need range
  emitted per IADS group, not per codename — deferred.
- **Setup:** New campaign (MANTIS engine) with a layered SAM threat incl. at least one medium/long SAM
  (SA-6/SA-11/SA-10). `dcs.log` should show `... SAM range override active (N AD group range(s) ...)`.
  Fly a **striker into a SAM ring** (not a C-130 in friendly air) and bring a SEAD/HARM shooter.
- **Pass:** an SA-10/SA-6/SA-11 goes **active on RWR at its true range** (tens of NM, not ~3 NM), the
  MANTIS status shows SAMs flipping to **RED** when you press a ring (not stuck 0/all-GREEN), and a HARM
  shot triggers the SAM's **SEAD evasion** (radar drops / shoot-and-scoot). With MANTIS debug on, the
  `SAM ... is type LONG/MEDIUM` traces match the real SAM types. No `mantis-config.lua` Lua error.
  **Detection check (5th-pass fix):** with a RED AWACS airborne, `dcs.log` RED **`CheckLoop` should go
  non-zero** as you ingress (not 492× `CheckLoop 0`); a ground-starting A-50 must still wake the net.
- **Fail signature:** medium/long SAMs still typed POINT or still only engage at point range (override
  not resolving the group — check the `... range override active` count is non-zero and that codenames
  in `dcsRetribution.RedAA` match the group names); a SAM banded too high/low (tune `BAND_*_M`
  thresholds); SHORAD/AAA wrongly promoted out of POINT; or SAMs never go RED even pressed at true range
  (a deeper detection issue beyond this fix — re-open M2).

### G16 — LotATC export plugin restored · Plugin hygiene · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — user: "good"
- **In-game (2026-06-28, audience pass — user verdict "good"):** the restored `lotatc` export plugin works — the export is written and red AA threat circles render on the LotATC scope with no Lua error. The blank per-ring NATO-name labels remain a known limitation (not a fail), see below.
- **Context:** The `lotatc` plugin (export RED/BLUE anti-air threat circles + symbols to LotATC
  scopes) was silently dropped from the active plugin list during the QRA-reserve integration and
  is now restored, plus a cross-wired config option fixed ("Export anti-air symbols" was driving the
  "Export BLUE anti-air" flag).
- **Setup:** Enable **LotATC Export** on the Lua Plugins page, set `LOTATC_DRAWINGS_DIR` (or rely
  on the Saved Games default), desanitize `MissionScripting.lua` (needs `lfs`/`io`/`os`), generate +
  run a mission with red SAM/AAA sites, then open the export in LotATC.
- **Pass:** `threatZones.json` (+ `threatSymbols.json` when symbols enabled) appear under the export
  path and red AA threat circles render on the LotATC scope; toggling "Export anti-air symbols" off
  actually suppresses the symbol file (the bug just fixed); `dcs.log` shows the
  `DCSRetribution|LotATC Export plugin - writing …` lines with no Lua error.
- **Fail signature:** No export files written; a Lua error in `dcs.log`; or the symbols toggle has no
  effect. **Known limitation (not a fail):** per-ring NATO-name labels stay blank — that enrichment
  read the removed Skynet `redIADS`/`blueIADS` globals; circles/symbols still export, labelled by
  unit name + class.

### G17 — BigEye EWR plugin restored · Plugin hygiene · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass
- **Context:** `bigeye` (MOOSE `Ops.INTEL` early-warning radar that broadcasts text BRA / picture /
  bogey-dope calls to players) is the documented successor to the retired `ewrs` script, but had
  itself been silently dropped during the QRA-reserve integration — so players had no EW picture
  calls. Restored to the active plugin list (off by default). Independent of MANTIS (player-comms
  only; does not feed the IADS).
- **Setup:** Enable **BigEye EWR** on the Lua Plugins page, generate + run a mission with a player
  flight and airborne enemy contacts; use the F10 BigEye radio menu to enable reports.
- **Pass:** BigEye F10 menu present; periodic text threat reports list contacts with BRA + aspect,
  honoring the report-interval / max-units options; NCTR/NATO-name options behave as set.
- **Fail signature:** No BigEye F10 menu; no reports; a Lua error in `dcs.log`; or option values
  (intervals, max units, sensor flags) ignored.

### G18 — Blind-IADS warning + Red Tide red EWR coverage · MANTIS migration / Red Tide · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — Red Tide red EWR coverage confirmed
- **Context:** MANTIS detection rides only on dedicated EWRs + AWACS (SAMs and SAM-as-EWRs are held
  dark), so a campaign with radar SAMs but no EWR markers and no AWACS has a blind red net. Two
  changes: (1) a per-coalition **blind-network warning** — generation-time `luagenerator.py`
  (`logging.warning`) + runtime `mantis-config.lua` (`env.warning` in `build()`, via
  `count_entries`/`count_awacs`); (2) **Red Tide** went from 0 dedicated red EWRs (entirely
  A-50-dependent) to 4 — added `EWR 1L13` to the **Russia 1980** faction (`EWR-FG` 0→1, era-OK for
  1988) and 4 red `1L13` EWR markers to `red_tide.miz` near the long/medium SAM belt.
- **Setup:** (a) generate any campaign and read the app log for `IADS: <side> ... NO always-on
  detection source` on a known-blind one (e.g. Operation Gazelle / Egypt 1973); (b) generate + fly
  **Red Tide** with the A-50 left on the ground / not fragged.
- **Pass:** (a) the warning fires for a blind coalition and stays silent for a covered one; (b) in
  Red Tide, `dcs.log` shows the RED build resolving **≥4 dedicated EWR group names** and RED
  `CheckLoop` climbing **before** the A-50 is airborne — red SAMs draw fire even with no AWACS up.
- **Fail signature:** warning never fires on a blind campaign (or false-fires on a covered one); Red
  Tide red still shows 0 EWR groups (faction EWR date-gated out at 1988, or markers not placed); a
  `mantis-config.lua` Lua error; or `1L13` EWRs spawn in blue/contested territory (placement off).

### G20 — Combat SAR enemy snatch party (correct coalition + dispersed teams) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §15 · ☑ VERIFIED (2026-06-30, `dcs.log`/`state.json`/Tacview — "Vietnam v2.miz" session)

</details>
- **Verified (2026-06-30, flown session — `Vietnam v2.miz` / `dcs.log` / `state.json` /
  `Tacview-20260630-171831-DCS-Host-Vietnam v2.zip.acmi`):** `state.json.combat_sar_captures` recorded
  a genuine **BLUE** aircrew captured (`Front line Kutaisi/Senaki-Kolkhi CAS|2|27|A-1H Skyraider|
  Pilot #1`) — a snatch party can only capture a survivor it is hostile to, so this alone proves the
  party spawned on the **correct (enemy) coalition**, not the friendly/wrong-side bug. `dead_events`/
  `kill_events` also show at least **20 independently-numbered** `CSAR Snatch Party <N> U1..U10` groups
  (parties 1, 2, 3, 4, 8, 13, 14, 15, 16, 19, 20, 21, 23, 24, 25, 27, 30, 31, 37, 48 all appear as
  distinct 9–10-unit groups converging on different survivors across the session) — **dispersed small
  teams**, not the old one-column bug. Both fail signatures (wrong-coalition, single column) did not
  occur.
- **User note (2026-06-30):** "blue csar snatch party?" — the user also saw a **blue-coalition**
  snatch party. This session's generated `.miz` carries `dcsRetribution.CombatSAR` for **both**
  coalitions (`red.rescueHelos` is populated too — a red Mi-8MTV2 Combat SAR flight), so a blue party
  hunting a downed **red** pilot is the expected mirror image of the red-vs-blue capture already
  verified above, not a bug — `red.pending_pow_recoveries` came back empty from the headless save load
  (no red pilot was ultimately held), consistent with either no capture completing or a rescue beating
  it. Flag if what was actually seen was a *friendly-colored* party menacing a **blue** survivor
  instead (that would be the pre-fix bug reappearing) — the report as written reads as the symmetric,
  working case.
- **Bug (user report, 2026-06-29, screenshot):** the capture-race snatch party rendered on the map as
  **friendly/green** (wrong coalition) and as **one long marching column** ("AK74" line) rather than
  enemy ground forces. Root cause: the `combatsar` plugin hardcoded `country.id.CJTF_RED`/`CJTF_BLUE`
  for the enemy ground spawn, but in a Vietnam/CH-faction `.miz` those CJTF countries are **not
  registered** on either coalition (the factions use real/CH nations), so `coalition.addGroup` placed
  the party on the wrong side; and all `partySize` soldiers spawned as a single group routed on one
  waypoint, forming a column.
- **Fix (2026-06-29):** Python now emits `enemyCountry` = the opposing side's faction country id
  (`coalition.opponent.faction.country.id`, always registered on the enemy coalition) and the plugin
  spawns the party under it (CJTF constant kept only as a fallback). `spawnSnatchParty` now spawns
  **several small teams** (`captureTeams`, default 3) ringed around the survivor on different bearings,
  each its own group converging independently; `advanceCapture` tracks the list (neutralized only when
  every team is dead; any team holding on the pilot runs the capture clock). Lua syntax read-checked;
  Black/mypy/pytest green.
- **Setup:** A campaign whose factions use **real/CH nations** (e.g. Khe Sanh / a Vietnam Ops
  campaign), `captureEnabled` on. Eject a blue pilot near the FLOT and let the capture roll hit.
- **Pass:** The snatch party shows **RED/enemy** on the F10 map (not green) and appears as **3 small
  dispersed teams** converging from different directions (not one column). Killing all teams clears the
  capture (`Capture party neutralized` cue); letting one team dwell on the survivor still results in
  `CAPTURED` → POW.
- **Fail signature:** snatch party still friendly/neutral-coloured (the `enemyCountry` emit didn't
  reach the plugin, or `addGroup` fell back to an unregistered CJTF country — check the emitted
  `dcsRetribution.CombatSAR(.red).enemyCountry`); still one long column (teams not splitting); or the
  capture never fires because `advanceCapture` lost track of the multi-group party (all teams reported
  dead while alive).

### G21 — Combat SAR AI rescue commandeers an on-station helo (no duplicate spawn) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §21 · ✗ SUPERSEDED by the 2026-07-06 on-demand rework — the commandeer path (and the standing orbit it commandeered from) is RETIRED. The bug this row tracked (a commandeered airborne helo RTBs instead of rescuing) is designed out: the runtime now clones a cold template *into* the mission (the path that always worked). Re-verify as G9. Kept for history.

</details>
- **2026-07-06 flown Inherent Resolve session (`jovial-gates-574c9c`, dcs.log + Tacview trace):** two
  ejections (CROW Su-25 t≈1096, JELLYFISH M-2000C t≈3009), zero `combatsar:` errors. **The preference
  finally showed itself:** ejection #1 produced **no clone** (the planned
  `Front line Balad Airbase/Tikrit Combat SAR|2|20|UH-60A|` was alive and idle → commandeered), and only
  ejection #2 — with the planned helo now committed — spawned `CombatSAR Rescue 3#001` (which air-spawned
  at the planned helo's FLOT-station template anchor). That is exactly the designed commandeer-first /
  clone-on-busy order. **But the commandeered helo never executed the rescue:** it kept its planned
  racetrack for ~11 min after dispatch, then transited to **Balad** (its `SetHomebase`) and loitered there
  to file end — distance to its survivor 97→140 km, never closing. Best read of
  `dispatchAIRescue`: `FLIGHTGROUP:New` over an **airborne, already-routed** group + `AddOpsTransport`
  doesn't preempt the group's current route — it finishes/abandons the racetrack and goes to the homebase
  instead of the pickup zone (the fresh-clone path, AICSAR's proven shape, activates into the transport
  mission directly, which is why clones historically worked). **Next step is a code decision, not a
  re-fly:** either cancel/clear the commandeered group's current mission-queue before `AddOpsTransport`
  (MOOSE-risky, needs a fly), or drop the commandeer and always clone (reverses this row's design intent
  but uses the only proven path). The survivor stand-in rendering as a **2B11 mortar** (the INFANTRY-class
  pick on OIR) was also caught here and fixed same day (`LuaGenerator.survivor_unit_type`).
- **Re-fly (2026-07-01, flown Yankee Station session `intelligent-dubinsky` — `dcs.log` + Tacview):** the
  "table index is nil" dispatch error did **not** reproduce — zero `combatsar: AI dispatch error` lines across
  **5** AI rescue dispatches (`CombatSAR Rescue 4/5/9/11/13`, Mi-8s red + CH-53Es blue — the ledger ran
  coalition-generically on 4 separate ejections, 16 snatch parties spawned on both sides). The 2026-07-01 fix
  held. **Still unproven:** the commandeer preference — blue clones 11/13 spawned while the planned
  `Front line … Combat SAR|2|43|CH-53E` was still alive; it may have been legitimately busy with the earlier
  AH-1W-crew survivors (the artifacts can't distinguish busy from skipped), and red's planned Mi-8 died at
  t≈109 s so red's clones were correct fallback. No rescue *completed* inside the 33-min window
  (`combat_sar_rescues`/`combat_sar_captures` both empty at mission end — races still running), so watch a
  longer session for the divert message + a delivery. **Caveat:** this flight predates
  [#407](https://github.com/BradySox/RetLab/pull/407) — red-side Combat SAR (the red dispatches 4/5/9 and
  the blue snatch parties racing red ejections observed here) has since been removed by squadron call;
  future sessions will only show the blue rescue/capture loop. The dispatch-fix evidence stands (same code
  path).
- **Partial (2026-06-30, flown session — `dcs.log`/`state.json`):** Two findings, one good and one a
  genuine open bug:
  - **Clone-fallback confirmed working as designed:** `dcs.log` shows `OPSTRANSPORT [UID=6] | Carrier
    OPSGROUP CombatSAR Rescue 15#001 dead!` — i.e. `spawnIndex` had reached **≥15** clones from the
    FARP. This session's blue helo losses were heavy (multiple `Front line … Combat SAR|…|Mi-8MTV2`
    and `Kutaisi_UH-1H_*` crashes in `crash_events`), so on-station helos were frequently dead/unavailable
    — exactly the documented condition under which falling back to a fresh clone is *correct*, not a bug.
  - **The row's own anticipated fail signature reproduced:** this row's text explicitly flags
    `combatsar: AI dispatch error` in `dcs.log` — "the live-group `FLIGHTGROUP` wrap is the risk to
    watch" — as the fail signature for a failed *commandeer* attempt. `dcs.log` shows exactly that
    warning **9 times** across the session (`combatsar: AI dispatch error (continuing):
    [string "l10n/DEFAULT/Moose.lua"]:11714: table index is nil`). Moose.lua:11714 is
    `self.Templates.ClientsByID[UnitTemplate.unitId]=UnitTemplate` inside `_RegisterGroupTemplate`,
    firing when a `Client`/`Player`-skill unit template has a **nil `unitId`** — i.e. commandeering (or
    cloning) is triggering a Moose DATABASE template re-scan that trips over some unit's malformed
    template elsewhere in the mission. It's `pcall`-guarded so it doesn't crash and 3 rescues still
    completed (G11), but that specific dispatch attempt aborts, so it's worth root-causing rather than
    dismissing — **reopen candidate**, not yet a clean pass. `combat_sar_rescues` (3 entries) proves
    *some* dispatches complete; we can't tell from these artifacts whether any of the 9 errored attempts
    correspond to a survivor who was never rescued.
- **Bug (user report + Tacview, 2026-06-29):** with `auto_combat_sar` on, every AI ejection made
  `dispatchAIRescue` clone a brand-new `CombatSAR Rescue N` helo from the FARP instead of using the
  Combat SAR flight already orbiting the FLOT. Tacview from `…retribution_nextturn` shows 8+
  `CombatSAR Rescue N` CH-53E/Mi-8 clones spawned **co-located with** the idle
  `Front line … Combat SAR` helos at the same field — "the AI prefers to spawn a group instead of
  commandeering the ones already on the front lines."
- **Fix (2026-06-29):** `dispatchAIRescue` now calls `commandeerRescueHelo` first — picks the nearest
  alive, idle, **AI-crewed** rescue helo from `cfg.rescueHelos` (skips player-crewed via
  `groupHasPlayer`), wraps it in a `FLIGHTGROUP`, `AddOpsTransport`s the survivor pickup, marks it
  busy (`busyHelos`), and frees it on delivery so it cycles to the next ejection. It only clones a
  fresh `CombatSAR Rescue N` from `heloTemplate` when every planned rescue helo is dead or already
  committed. Lua syntax read-checked.
- **Setup:** Khe Sanh / any campaign with `auto_combat_sar` on so a COMBAT_SAR helo orbits the FLOT.
  Down several AI pilots near the front over a few minutes and watch the rescue dispatch (Tacview).
- **Pass:** When a pilot ejects, an **already-orbiting** `Front line … Combat SAR` helo **diverts** to
  the survivor (message "a Combat SAR helo on station is diverting…"), boards, and delivers to the
  FARP — **no** new `CombatSAR Rescue N` clone appears while a planned helo is available. A fresh
  clone only spawns once all orbiting rescue helos are dead/busy. The delivered pilot is spared at
  debrief (G11).
- **Fail signature:** a `CombatSAR Rescue N` clone still spawns while an idle `Front line … Combat SAR`
  helo orbits (commandeer not firing — check `cfg.rescueHelos` is populated and `FLIGHTGROUP:New` on a
  live AI group takes the OpsTransport); the commandeered helo never diverts / errors on takeover
  (`combatsar: AI dispatch error` in `dcs.log` — the live-group `FLIGHTGROUP` wrap is the risk to
  watch); a human's rescue helo gets hijacked by the AI (the `groupHasPlayer` guard failed); or a
  helo stays stuck `busy` and never serves a later ejection (free-on-`OnAfterUnloaded` not firing).
- **Root-cause fix applied 2026-07-01 (the "dispatch error / table index is nil" leg).** Traced the
  `Moose.lua:11714: table index is nil` to `DATABASE:_RegisterGroupTemplate` doing
  `Templates.ClientsByID[unit.unitId] = unit` for every Client/Player-skill unit — which throws when a
  client slot's template has a **nil `unitId`**. The Combat SAR rescue helos are player-flyable (Client
  skill), and the crash is on the **clone** path (`SPAWN(cfg.heloTemplate):Spawn()` →
  `DATABASE:Spawn` → `_RegisterGroupTemplate`; the commandeer path goes through `_RegisterDynamicGroup`,
  which never touches line 11714). Three changes in `combatsar-config.lua`:
  1. **Root cause — init sweep** (`sanitizeClientTemplates`): at plugin init, backfill a synthetic,
     collision-safe `unitId` (≥ 9000001) on any Client/Player template carrying a nil one, so
     registration never indexes a nil. `pcall`-guarded; only touches already-broken templates.
  2. **Bounded retry:** `dispatchAIRescue` now returns success; the caller only latches `e.dispatched`
     once it actually succeeds, retrying a *failed* dispatch up to 3× with a 20 s backoff (was: latch
     before dispatch, so one error abandoned the survivor forever).
  3. **Leak-proof commandeer:** the `busyHelos` mark now happens only on the success path, so a
     mid-dispatch error can't strand a commandeered helo as permanently busy (it stays available for the
     retry).
  Lua syntax gate green. **Needs a re-fly** to confirm the 11714 error is gone from `dcs.log` and every
  errored survivor now gets rescued (was 9 errored attempts / 3 completed).

### G22 — Captured-pilot POW recovery raid: planning crash + map marker · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §15 · ✗ RETIRED (2026-07-03 CSAR rescope — the POW recovery raid is SHELVED: the `CSAR` raid flight type, the `CapturedPilotGroundObject` map objective, and `commit_pow_recoveries` are removed, so there is no raid to plan and nothing to re-fly. The held-POW model — freed by field capture, killed on the 4-turn clock, draining will — stays and is CI-tested in ~~`tests/test_pow_recovery.py`~~. See `retlab-csar-notes.md`.)

</details>
- **Bug (user report, 2026-06-30 — screenshot of "An unexpected error occurred"):** planning a
  recovery flight against a captured-pilot POW objective (F10 "save pilot at airbase") crashed with
  `AssertionError` in `AirAssaultFlightPlan.Builder.layout()` (`assert self.package.waypoints is not
  None`), raised from `ibuilder.py`'s `_generate_package_waypoints_if_needed` while computing the ATO
  list's `sizeHint`. **Root cause:** `CapturedPilotGroundObject` is deliberately flagged
  `is_friendly()==True` (§15 design: it's *our* POW, so it renders/tasks as a friendly recovery
  objective) even though it's physically positioned at the enemy airfield holding the POW — but
  `_generate_package_waypoints_if_needed`'s "friendly target → skip offensive routing" shortcut used
  that same flag to decide whether the package needed an ingress route, so `package.waypoints` was
  never populated and the CSAR-only builder's unconditional assertion tripped. **Confirmed exactly
  this scenario exists in the user's own save:** loading `414TH.retribution` headless finds a live
  `CapturedPilotGroundObject` at Batumi offering `FlightType.CSAR` to blue with `is_friendly==True` —
  the precise repro condition.
- **Fix (2026-06-30, `game/ato/flightplans/ibuilder.py`):** `_generate_package_waypoints_if_needed` now
  always generates package waypoints for `FlightType.CSAR` regardless of the friendly flag (CSAR's only
  legal target is always physically enemy territory by construction). Covered by a new focused unit
  test (~~`tests/ato/flightplans/test_ibuilder_package_waypoints.py`~~, 3 cases: CSAR still routes against a
  friendly-flagged target, a non-CSAR type still skips for a friendly target, a genuinely offensive
  target still routes). Black/mypy/pytest green.
- **2nd bug (user report, 2026-06-30):** "captured pilot box shows on the map as intended but it needs
  to be offset from the base so you can click it" — the POW marker rendered exactly on top of the
  holding airfield's own icon (`pow_objectives.py` positioned it at `holding_cp.position` with zero
  offset), making it unclickable.
- **Fix (2026-06-30, `game/pow_objectives.py`):** the marker is now offset `_MARKER_OFFSET_M` (900 m)
  toward the friendly anchor, clearing the airfield's icon while still reading as "held at this
  airfield." Recovery is matched by airframe name, not position (`commit_pow_recoveries`), so the
  offset is purely cosmetic. ~~`tests/test_pow_objectives.py`~~ updated to assert the offset instead of
  exact-position equality; all green.
- **Setup:** A campaign with a `PendingPowRecovery` on the map (a captured pilot from the Combat SAR
  capture race, §15/G20). Open the map, confirm the POW marker sits clear of the holding airfield's
  icon and is clickable, then plan a CSAR recovery flight against it.
- **Pass:** The marker is clickable without zooming past the airfield icon; planning the CSAR flight
  does not crash, and the flight gets a real offensive-style ingress route into enemy territory (not a
  degenerate/local-only route).
- **Fail signature:** the `AssertionError` recurs; the flight plans with no real ingress (routes
  straight through threat zones with no IP); the marker still overlaps the airfield icon.

### G23 — Sandy AI dynamic retasking toward a live ejection · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §15 · ✗ REGRESSED → rework applied 2026-07-02 (root-caused; needs a re-fly). **FROZEN, pass-or-delete (2026-07-03 CSAR rescope):** this re-fly is the divert's last chance — pass and it stays as-is (frozen, no further iteration); fail and the divert is deleted rather than reworked a third time (a player Sandy is untouched either way). **NOTE (2026-07-06 on-demand rework):** with the standing orbit retired, this divert now only applies to an **AI-crewed Sandy inside a PLAYER-fragged package** (there is no AI-spawned Sandy in v1 — that's the §21 v2). So it's only exercisable when the player frags a package with an AI Sandy seat. **SCOPE CLARIFIED (2026-07-15, squadron call): this is a SINGLE-PLAYER feature** — the AI-crewed-Sandy-in-a-player-package configuration is exactly how a solo player runs CSAR (they fly one seat, the AI flies the Sandy); RetLab's own events are MP DM-style (the user builds, the squadron crews the seats), so an MP event was never this row's natural arbiter. The pass-or-delete rule stands, but the arbiter is an **SP re-fly** whenever one happens — do NOT delete it for lack of MP-event exercise.

</details>
- **Fail signature reproduced (2026-07-02 flown Trail 2 session `wonderful-chatterjee`, user-confirmed):**
  an F-4E ejection at t=1118 registered a survivor (2 snatch parties spawned 2 s later ~11 km from
  Gudauta), the **"SANDY … is diverting to hold over the downed pilot" message fired** (user saw it),
  the A-1H Sandys closed to **24.2 NM** — inside the 30 NM `sandyMaxRangeNm` gate — yet Tacview shows
  **no Sandy ever left the racetrack** toward the survivor. No "Sandy dispatch error" lines: the Lua
  call succeeded, the sim ignored the task.
- **Root cause:** `dispatchSandy` used `SetTask(TaskCombo{ EnRouteTaskEngageTargetsInZone, Orbit })` —
  `EngageTargetsInZone` is an **en-route** task, which the DCS controller silently rejects inside a
  main-task ComboTask. Message-then-no-movement is exactly that signature.
- **Rework (2026-07-02, same session):** divert is now a **route push** — transit waypoint → hold
  waypoint over the survivor (450 m AGL) carrying the orbit + the en-route engage as *waypoint* tasks
  (the stock MOOSE transit-then-orbit pattern), so the flight physically transits; release routes the
  Sandy back to its recorded station (`entry.sandyReturn`) instead of a bare `ClearTasks()` (which
  would leave it flying a straight line, since the divert replaced its planned route).
- **Re-fly pass:** an AI Sandy visibly leaves the racetrack, flies to the survivor, orbits/engages
  there, and returns to station once the survivor resolves. **Fail:** message with no transit (again),
  a `combatsar: Sandy dispatch error` line, or the released Sandy wandering off in a straight line.
- **Context (user request, 2026-06-30):** after G21/G22, the user asked to build the AI Sandy
  retasking that G21's investigation found was designed-but-never-built (the code's own comment
  called it "a combatsar runtime follow-up for the AI"; a 2026-06-30 in-game report — "Sandy's did
  nothing but fly their orbit path" — was consistent with that gap, not a bug at the time).
- **Built (2026-07-01):** `luagenerator.py` now buckets `FlightType.SCAR` flights per coalition into
  `dcsRetribution.CombatSAR(.red).sandys` (group names, alongside the existing `kings`/`rescueHelos`
  — Sandy was previously **absent** from the CombatSAR data table entirely, so the runtime had no way
  to know which groups were Sandys). `combatsar-config.lua` builds `sandyByName`, and on every tick a
  survivor is `"down"`, `dispatchSandy` finds the nearest alive, idle, **non-player** Sandy within
  `sandyMaxRangeNm` (default 30 NM; imperial-unit rename 2026-07-01, was `sandyMaxRangeM`) and pushes
  a combo task — `TaskOrbitCircleAtVec2` (hold near the survivor, inheriting the Sandy's own current
  altitude/speed) + `EnRouteTaskEngageTargetsInZone` (actively hunts `"Ground Units"` within
  `sandyEngageRadiusNm`, default 3 NM) — replacing its planned racetrack task. Commits one Sandy per
  survivor (`busySandy`), retries every 5s `POLL` until one frees up, releases it (`ClearTasks()`,
  resuming its own planned route) once the survivor is rescued/captured/dead. A player-flown Sandy is
  never retasked (`groupHasPlayer` guard, same pattern as rescue-helo commandeering). Two new plugin
  options: `sandyMaxRangeNm`, `sandyEngageRadiusNm`.
- **Test coverage:** the Python bucketing/emission is unit-tested
  (~~`tests/missiongenerator/test_combat_sar_sandy_luadata.py`~~ — a SCAR flight lands in `sandys`, never
  `rescueHelos`/`kings`; red/blue route to the right node; empty when no Sandy present). **The Lua
  runtime is entirely unflown** — no local Lua interpreter (CLAUDE.md constraint), read-verified only
  (balanced blocks, correct Moose API signatures cross-checked against `Moose.lua` — `TaskOrbitCircleAtVec2`,
  `EnRouteTaskEngageTargetsInZone`, `TaskCombo`, `SetTask`, `ClearTasks`, `GetVelocityMPS` all confirmed
  to exist with the parameter orders used). The Lua 5.1 syntax gate (CI, blocking) passed on the PR.
- **Setup:** A campaign with an AI-crewed Sandy (SCAR) flight in a Combat SAR package — `auto_combat_sar`
  on for the safety-net package, or a player-fragged package with an AI Sandy wingman/second flight.
  Eject an AI or player pilot near the FLOT within Sandy's `sandyMaxRangeNm`.
- **Pass:** Within one `POLL` (5s) of the ejection, the AI Sandy breaks from its racetrack, holds near
  the survivor's position, and actively engages any snatch party / hostile ground unit that enters its
  engage radius — visibly more assertive than passively orbiting its old box. A coalition message
  ("SANDY \<name\> is diverting…") announces the divert. Once the survivor is rescued/captured/dead, the
  Sandy resumes its normal patrol. A **player-flown** Sandy is completely unaffected (still just files
  its planned racetrack, no forced retask).
- **Fail signature:** no divert at all (Sandy stays on its old racetrack — check
  `dcsRetribution.CombatSAR.sandys` is populated in the generated `.miz` and `combatsar: Sandy dispatch
  error` in `dcs.log`); a **player-flown** Sandy gets yanked off its route (the `groupHasPlayer` guard
  failed); the Sandy never returns to patrol after release (`ClearTasks()` didn't resume the route); two
  survivors fight over the same Sandy (`busySandy` bookkeeping broken); a Lua error in `dcs.log`
  (`combatsar-config.lua` around `dispatchSandy`/`findFreeSandy`/`releaseSandy`).
- **Re-fly 2026-07-30 (flown PG/Vietnam "Recovery: Jason Rogers" package; Tacview `Tacview-20260730-182637`) — INCONCLUSIVE + weapons-free added:** the player fragged a full package (CH-47D rescue helo + AH-1W Sandy + C-130 King, flew the King). Both AH-1W Sandys **oscillated in a racetrack 13–31 km from the survivor and never held over it** (the same "never leaves the racetrack" fail signature as 2026-07-02, so the route-push rework's first actual re-fly did **not** visibly work). BUT the flight is **confounded**: the survivor was a persistent evader and **no snatch party spawned** near it (one ~50% roll missed), so there was nothing at the survivor to fight — "flew straight and level without fighting back" is partly expected here. A clean adjudication needs a re-fly WITH a snatch party (set `combat_sar_test_force_capture` to guarantee one). **Additive fix (not a routing rework — respects pass-or-delete):** a diverted Sandy is now set **WEAPON_FREE** (`setAirWeaponsFree`, Air ROE) so it actually engages the snatch party / threats — SCAR generates with ROE Open Fire (engage *designated* only), which would not return fire at an attacker outside its zone. **Next re-fly:** force-capture ON, watch whether the Sandy (a) leaves its racetrack and holds over the survivor (the still-unconfirmed routing — pass-or-delete) and (b) engages the snatch party once holding (the weapons-free add). See `retlab-csar-notes.md` "Packaged AI-helo auto-pickup + weapons-free Sandy".

### G39 — Engaging a site reveals it completely; recon does not · §3 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, replaces G24 (concealed field forces), closed by removal 2026-08-18. The
reveal rule and the no-lag guarantee are unit-tested (`tests/test_recon_reveal_rule.py`,
`tests/test_recon_intel_fog.py`); what no test covers is the map read across a real turn
cycle and whether the fog still reads as fog when every site carries an exact marker.
- **What CI cannot exercise:** the client map actually redrawing a site from "unknown" to
  its full symbol + rings at debrief (client is not CI-type-checked), whether an
  un-engaged theater feels informative or blank, and whether losing recon as a reveal
  makes any campaign unplayable (nothing to fly against because nothing is known).
- **Setup:** a NEW campaign with `recon_intel_fog` on (default). On turn 0, note that
  every enemy site has an exact marker with no composition, no rings and no unit list.
  Frag a Strike or DEAD package at one site and a TARPS/recon flight at a *different*
  one. Fly or fast-forward the turn.
- **Pass:** the struck site comes back fully known — unit types, counts, threat and
  detection rings — **and** its damage is correct immediately, with no second recon pass
  needed. The recon-only site is still unknown. A site an offensive package reached but
  scored no kills on is also revealed. Known sites stay known across turn boundaries and
  a save/load.
- **Fail signature:** a struck site still showing "?" composition at debrief (the reveal
  path broke); a struck site revealed but reading undamaged, or damage appearing only
  after a later flight (a BDA lag has come back — `alive_at_last_recon` was reintroduced);
  the recon-only site revealing (recon is back in the reveal set); any enemy site drawing
  a dashed uncertainty circle other than a COIN IED/HVT/cell (the category concealment is
  back); a fresh campaign where nothing is ever knowable because no ground-attack task in
  the package set reaches `attacked_tgos_this_turn`.

### G26 — Packaged drone is a lasing JTAC (autolase + smoke for the shooters) · §3 · ⊘ RETIRED

**History:** **STRIPPED 2026-08-05 — landed**;, DM call `units-runway-generation-bf755e` — "G26, 27 need stripped from the build, leave G32 as its default behavior". The packaged-drone JTAC model is dropped; the stock front-line FAC (G32) becomes the only JTAC model, unconditionally. No pass is owed on a feature being removed — this row closes when the strip lands) (was ☐ UNTESTED, built 2026-07-05, RetLab call; **COIN-scoped 2026-08-02** — now behind `coin_packaged_jtac_drone`, so the setup below MUST be a COIN campaign; the qualification gate + laser-code choice are unit-tested in ~~`tests/missiongenerator/test_drone_jtac.py`~~ — the actual runtime lasing needs a fly
- **What it is:** on a campaign with `coin_packaged_jtac_drone` on, an AI-flown flight of the faction's `jtac_unit` (the MQ-9/Predator) in an A/G package (Armed Recon / CAS / BAI / Strike) is emitted as a `JtacInfo` → `dcsRetribution.JTACs` → CTLD `JTACAutoLase` (autolase + smoke default ON). So the packaged drone lazes + smoke-marks ground targets for the shooters and shows on the kneeboard/radio like a JTAC — the COIN substitute for the stock front-line JTAC, which a front-less COIN laydown can't use. Blue + AI only; a real asset (not invisible/immortal).
- **Setup:** NEW "Iraq - Operation Inherent Resolve (COIN)" (preseeds `coin_packaged_jtac_drone`, fields the MQ-9/Predator, CTLD on). Let the planner build a turn with an Armed Recon (or CAS/BAI/Strike) package that includes a drone; fly it and watch the drone over the target area.
- **Pass:** the drone appears on the kneeboard JTAC card with a laser code + radio; in-mission it autolases ground targets in the package's target area and drops smoke on them; the AI shooters (or you) can attack the lased/marked targets; the drone is killable (not immortal). A JTAC radio menu is present (CTLD). **No front-line FAC is also present** (the two are mutually exclusive).
- **Fail signature:** no JTAC on the kneeboard (the `JtacInfo` didn't emit — check `coin_packaged_jtac_drone` is on, and the flight is the faction's `jtac_unit`, AI, blue, in an A/G package; or CTLD autolase is off); the drone never lases (CTLD `autolase` option off, or the moving/overflying drone never dwells near a target long enough — this is the **loiter question**: if a single overflight can't sustain a useful lase, the drone needs an orbit/loiter profile over the target); every drone lases even in non-A/G packages (the `_JTAC_PACKAGE_PRIMARIES` gate broke); a red or player drone lases (the blue/AI gate broke); **two JTACs on the kneeboard** (a front-line FAC + the drone — the mutual exclusion broke).

### G27 — Auto-fielded JTAC drone squadron on a COIN campaign with no drone · §3 · ⊘ RETIRED

**History:** **STRIPPED 2026-08-05 — landed**;, DM call `units-runway-generation-bf755e` — stripped together with G26, which it exists solely to feed: the auto-fielded drone squadron's only purpose was to guarantee a drone for the packaged JTAC on a COIN campaign that authored none, so with G26 gone it has no reason to exist. No pass owed) (was ☐ UNTESTED, built 2026-07-05, RetLab call; **COIN-scoped 2026-08-02**; the gate + rear-base pick are unit-tested in ~~`tests/retlab/test_jtac_drone.py`~~, the gate is verified to qualify real modern factions — the fielded-and-fragged loop needs a fly
- **What it is:** at New Game on a campaign flying the COIN packaged drone JTAC, a blue side whose faction declares a drone `jtac_unit` (MQ-9/Predator) and doesn't already field one gets a small (2-ship) TARPS-tasked drone squadron auto-added at its rear-most airfield, so the drone-JTAC (G26) has an airframe to frag. Gated first by `coin_packaged_jtac_drone`, then by `auto_jtac_drone` (default ON); skips campaigns that hand-place drones (OIR untouched); blue-only; **era-gated** (a 1988 campaign like Red Tide never gets a Reaper — service-year floor).
- **Setup:** NEW game on a **modern** campaign with `coin_packaged_jtac_drone` ticked that does **not** list an MQ-9 squadron. Check the blue ATO/air wing.
- **Pass:** a 2-ship MQ-9 Reaper (or Predator) squadron exists at a rear blue airfield that didn't have one in the campaign yaml; the auto-planner frags it into an A/G package (TARPS/overwatch), it reaches the target area, lases (G26), and films (drone-always-films). On OIR (already fields drones) **no second** drone squadron is auto-added. Turning `auto_jtac_drone` off — or leaving `coin_packaged_jtac_drone` off, as every non-COIN campaign does — yields the campaign's authored air wing exactly.
- **Fail signature:** no drone squadron appears (gate: `coin_packaged_jtac_drone` on, `has_jtac`/`jtac_unit` a drone/TARPS-capable, setting on, campaign year ≥ the drone's service year — check the faction JSON + start date); **a drone squadron auto-fielded on an ordinary front-line campaign** (the COIN gate broke — this was the pre-2026-08-02 behavior); a **second** drone squadron on a campaign that already fields one (the existing-drone skip broke); the drone based at the front line or an inoperable field (rear/`can_operate` pick broke); a red drone squadron auto-fielded (blue-only gate broke); **an anachronistic MQ-9 on a Cold-War campaign** (the era gate broke — Red Tide 1988 must stay drone-free); the drone sits idle and never frags (no A/G packages that turn, or the auto-recon hook off — `auto_add_tarps_recon`).

### G32 — Stock front-line JTAC is the ONLY JTAC model, on every campaign · §3 · ☑ VERIFIED

**History:** **scope widened 2026-08-05**, DM call `units-runway-generation-bf755e` — "leave G32 as its default behavior": with G26/G27 stripped, the stock front-line FAC is no longer one of two mutually-exclusive models, it is simply how JTAC works, gated only on `faction.has_jtac` as upstream intended. That SIMPLIFIES this row — the mutual-exclusion half of the test disappears with the setting that created it, and what remains is the plain question of whether the restored invisible/immortal FLOT FAC actually lases. Note the exclusion tests in `test_drone_jtac.py` / `test_jtac_drone.py` go with the strip; keep whatever still covers the front-line FAC itself) (was ☐ UNTESTED, built 2026-08-02; the mutual-exclusion gate is unit-tested in ~~`tests/missiongenerator/test_drone_jtac.py`~~ + ~~`tests/retlab/test_jtac_drone.py`~~ — the restored FAC's runtime lasing needs a fly

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — VERIFIED on the user's call ("G32 is good").** The front-line JTAC is the only JTAC model in play and behaved.
- **What it is:** the fork had deleted upstream's front-line JTAC outright when it built the packaged drone-JTAC. That JTAC — an **invisible, immortal** `jtac_unit` FAC orbiting the FLOT at 5,000 ft, lasing for CAS on the front line's own laser code — is restored verbatim (`FlotGenerator._generate_front_line_jtac`) and is again the **default for every campaign**. It is suppressed only where `coin_packaged_jtac_drone` is on (the two COIN campaigns).
- **Setup:** NEW game on any ordinary front-line campaign whose blue faction has `has_jtac` (Red Tide is the obvious RetLab one). Frag/fly a CAS mission at the front line.
- **Pass:** a JTAC appears on the kneeboard with a callsign, UHF freq and laser code, orbiting near the FLOT; it lases front-line targets for your CAS run; it is invisible + immortal (that is the intended stock behavior here, unlike the COIN drone); exactly **one** JTAC per front line and no packaged drone JTAC alongside it.
- **Fail signature:** no JTAC at all (the restore didn't fire — check `has_jtac` on the blue faction, and that `coin_packaged_jtac_drone` is OFF); the FAC spawns somewhere other than the front-line center (the `frontline_position` call drifted); a crash on generation naming/livery/callsign (the restored block's `AircraftPainterJtac` / `callsign_dict` asserts); **two JTACs** (the COIN drone also emitted — the mutual exclusion broke).

### G28 — POW mechanics: captured pilot benched, held, surfaced, brought home · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §21 · ☐ UNTESTED (built 2026-07-06; the POW status transitions, the 4-turn hold clock, invulnerable-player-respecting write-off, Homecoming, SITREP lines, and the §51 compromise expiry are unit-tested in ~~`tests/test_pow_recovery.py`~~ + `tests/squadrons/test_squadron_pilots.py` + `tests/test_sitrep.py` + `tests/missiongenerator/test_commsjamluadata.py` — the multi-turn campaign feel + the roster/SITREP read need a played campaign. The will-coupled indefinite hold was REMOVED 2026-07-21 — the hold is now always the 4-turn clock.)

</details>
- **What CI cannot exercise:** whether a captured pilot genuinely disappears from the schedulable roster next turn and reads as "POW" in the squadron dialog; whether the SITREP band names the POW + holding field + clock each turn; whether recapturing the holding field returns the pilot; whether a win brings held POWs home (Homecoming) and a loss writes them off; and whether an invulnerable-player POW is returned rather than killed at clock expiry.
- **Setup:** lose the Combat SAR race (eject + get captured) on any campaign (the 4-turn hold clock is now universal). Note the pilot name. Advance turns watching the squadron roster + the next mission's kneeboard SITREP band; recapture the holding field in one run and ride the clock/war-end in another. **Fast test (thumb on the scale):** tick `[TEST] Combat SAR: force every downed pilot to be captured` (Campaign Management → HQ Automation) so you don't have to lose the race by chance — any ejection near the front becomes a POW in seconds.
- **Pass:** the captured pilot shows **POW** in the squadron dialog and is never fragged while captive; the SITREP band carries a "POW: <name> — held at <field> (N turns left / held)" line each turn; recapturing the holding field returns the pilot to Active (and clears the line); the pilot is written off at the 4-turn clock (or, with invulnerable player pilots on, a *player* POW returns instead of dying); a **win repatriates every held POW** (Homecoming) while a loss writes them off; §51 jamming from a held POW stops after ~4 turns even if the POW is still held.
- **Fail signature:** the captured pilot flies again next turn (status not flipped / `active_pilots` still includes POWs); no POW line in the SITREP (the `pows_held` wiring); recapturing the field doesn't free them (`repatriate` / holding-cp match); a player POW killed at clock expiry despite invulnerable-player-pilots (the `_write_off` gate); no Homecoming on a won campaign (the `process_win_loss` hook); §51 jams forever off a held POW (the `COMMS_COMPROMISE_TURNS` window / `captured_turn` stamp).

### G29 — Persistent evaders + the always-run snatch race · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §21 · ◐ PARTIAL — **SCHEDULED** (**call made 2026-08-07**, on the DM's instruction to resolve this row after it aged out unassigned. Verdict: **schedule it**, not accept-unverified and not delete — the opposite call to its long-time twin A5, for two reasons. **(1) The untested half is the campaign-visible half.** The Lua half is already proven live (the no-asset path armed instead of bailing and `combat_sar_survivors` was written); what has never been seen is the Python turn-boundary arc — MIA flip → SITREP band / squadron roster / orange map marker → next-mission evader respawn at the last known position. That is a chain of *player-facing* consequences, so failure is silent and expensive: a downed pilot simply dies and the whole §21 rescue economy quietly does nothing. Accepting that unverified buys nothing. **(2) It is not actually opportunistic, and treating it as such is why it sat here for four weeks.** It has a cheap deterministic forcing move — in an ordinary ATO jet (**never** a dynamic slot, which by design can never go MIA), eject deep over enemy ground, end the mission with no rescue, pass the turn. **~10 minutes.** That is a *contrived condition*, which per the WATCH rules disqualifies it from the standing watch list and belongs on a local card — so it spent four weeks parked on the one surface that structurally could not close it. **Scheduled on [`docs/dev/flycards/LOCAL.md`](flycards/LOCAL.md)**, the first local card, which the session-start hook now prints) (was ◐ PARTIAL — 2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`: the always-run half is proven live — the no-asset path armed instead of bailing (`Combat SAR - blue has no rescue asset this mission; capture race only` → `survivor ledger started (1 coalition(s), 0 King(s), 1 Sandy(s), capture on, AI-rescue off)`; the old "skipping" line is gone) and `combat_sar_survivors` WAS written (1 unresolved entry at exit; ~20 other ejections were resolved in-mission as their pilot units despawned). **Caveat found:** the one surviving entry was a **DCS dynamic-slot** jet — a player self-spawned a MiG-29A at blue Frankfurt (`dynamic_slots` was ON at generation; DCS names these `<Airbase>_<type>_<n>`) and ramp-ejected to leave (Tacview shows no shoot-down, the jet removed 723 m from its spawn AT the field). `record_downed_pilots` discards it correctly (`unit_map.flight() is None` → "not an airframe this campaign tracks"), so no phantom MIA — but note a dynamic-slot pilot can never go MIA/POW by design. The MIA flip → SITREP/roster → next-mission evader respawn arc still needs a real tracked-airframe shoot-down. Built 2026-07-10, squadron call; the always-emit node, the no-rescue-capability ledger start, the eject → `combat_sar_survivors` sync → snatch spawn, the evader respawn, the MIA record/retire, the depth-weighted turn roll, and the SITREP/roster surfaces are unit-tested in ~~`tests/lua/test_combatsar_ledger.py`~~ + ~~`tests/retlab/test_downed_pilots.py`~~ + ~~`tests/test_combat_sar_scoring.py`~~ + ~~`tests/missiongenerator/test_combat_sar_sandy_luadata.py`~~ — the in-DCS snatch spawn without any rescue asset, the evader respawn feel, and the multi-turn evade/capture arc need a fly)

</details>
- **2026-07-17 night fly (fresh Scenic Route Merged turn 1, Tacview `Tacview-20260717-214932`,
  session `tacview-test-analysis-5bb161`): the at-scale live run — MIA banking + ledger hygiene
  VERIFIED, and a NEW finding: the snatch race resolves by infantry ballistics, never by the
  capture clock.** 10 survivor groups spawned across the mission's ejections; 12 CSAR Snatch
  Parties spawned (the ~50% roll firing repeatedly); state.json flushed clean with
  `combat_sar_survivors: 8` — the persistent-evader mirror banked every unresolved pilot,
  **including the player's own** (Flash, killed by the CHICKEN SA-17 TELAR at t=3625, evader at
  the death point deep in Iran) — and the two resolved survivors were correctly dropped (10−2=8,
  no leak). **But `combat_sar_captures` = 0 across 12 parties:** the capture dwell never
  completed because DCS infantry gunfights pre-empt it both ways — the **M249-armed survivor
  outguns the AK teams** (parties 1–3 all died 276–677 m into their 1.4 km march on Survivor 5,
  who is alive in the MIA ledger; blue air working the same area may have helped), and when
  teams DID close, **the survivor was shot dead instead of captured** (Survivors 9 + 15 killed
  on the ground → the `dead`-state reap, which worked). **FIX BUILT next session (unflown):**
  `setNonCombatant` in the plugin now spawns both the survivor group and every snatch team
  **ROE weapons-hold + alarm-green** (the survivor via the MOOSE spawn's real `#001` group
  name), so the capture clock + airpower against the party decide the race, never small arms;
  garrison units near the ejection still kill evaders by design. Pinned in
  `tests/lua/test_combatsar_ledger.py::test_survivor_and_snatch_teams_spawn_weapons_hold`;
  design note §"Non-combatant capture race" in `retlab-csar-notes.md`. **Re-fly pass:** a
  snatch team closes under fire without stopping to shoot, the survivor never fires, a
  completed dwell yields "CAPTURED … now a POW" + a `combat_sar_captures` entry. **Fail
  signature:** a survivor still mowing down teams (the `#001` name resolution missed — check
  dcs.log for the spawn alias) or a team shooting the survivor dead at contact (ROE not
  applied to `mist.dynAdd` spawns). Zero rescues again (all 10 on-demand clones spawned at Al Dhafra,
  115–300+ km from the survivors; closest approach 2.8 km at mission end) — exactly the transit
  problem G31 exists for, and this save is now the ready-made G31 test.
- **What it is:** the survivor ledger runs whenever the CombatSAR node exists — **no rescue capability no longer skips the plugin** (the flown 2026-07-10 gap: auto-CSAR off + Sandy-only package = no snatch AI, comms jam never armed). An un-rescued, un-captured pilot goes **MIA** (`combat_sar_persistent_pilots`, default ON): re-spawns at his position next mission (fresh smoke + snatch race, "EVADER" cue), walks home if on friendly ground at turn end, else rolls a **depth-weighted capture** each turn (10% near the front → 90% at 40 NM deep; no death clock). Capture = the normal POW chain (G28 + S4).
- **Setup:** auto-CSAR **off**, no CSAR/SCAR flights fragged, `[TEST] force capture` **on**; get a blue pilot down near the front. Then a second run with force-capture **off**: leave the survivor unresolved, end the mission, advance the turn, and generate the next mission.
- **Pass:** run 1 — the snatch party spawns and captures despite zero rescue assets (dcs.log shows "capture race only", the MAYDAY reads "no rescue assets available"), the POW + comms jam fire. Run 2 — the debrief spares the pilot (roster shows **MIA**, SITREP shows "MIA: <name> — evading near <CP> (downed this turn)"), the next mission re-spawns the survivor at the same spot with red smoke + the EVADER message, and the on-demand AI rescue (if re-enabled) or a player package can still recover him; a deep evader left alone converts to POW within a turn or two (message "Evader captured"), a near-front one keeps evading.
- **Fail signature:** dcs.log still shows "no rescue helos/template; skipping" (the old bail; stale plugin) or "dcsRetribution.CombatSAR not present" (the emitter early-return resurfaced); no snatch with force-capture on (G20 regression); the un-rescued pilot dies at debrief with the toggle on (the `_combat_sar_mia_unit_ids` sparing / `combat_sar_survivors` state never written — check state.json); no re-spawn next mission (`persistentSurvivors` missing from the miz's CombatSAR node); the same evader duplicated in the ledger (turn_downed reset); an evader stranded MIA forever after toggling the setting off mid-campaign (the always-resolve contract broke); a capture roll that never fires even 40 NM deep (`resolve_downed_pilots` not hooked in `finish_turn`).

### G30 — Skynet point defence: the paired SHORAD answers the HARM shot · Skynet return · ☑ VERIFIED (2026-09-23, test 40; was ◐ PARTIAL)

**2026-09-23, test 40** (Afghanistan — Graveyard of Empires turn 2, 55 min, no player, `Tacview-20260923-212225`, `Desktop\New test\40`) — **the missing link: a paired PD knocks down HARMs aimed at its parent.** `0028 | ARAPAIMA (SAM)` is a Kub (SA-6), which cannot engage a HARM; Skynet paired `0029 | ARAPAIMA (PD)`, a Tor-M2 and a 2S38. SARDINE SEAD Sweep's Hornets fired six AGM-88s at ARAPAIMA from 28–53 km (t=2532–2743), SARDINE SEAD Escort one from 80 km (t=2491). The Tor killed all seven, 2.3–11 km short of the site, each within 10–41 m of a 9M338K in the same second (t=2640–2786). It also killed an AGM-65D and three GBU-38s aimed at the site. ARAPAIMA survived and killed a Hornet at t=3123. Contrast: SLUG (SA-11) had only a 2S38 gun as PD; the three HARMs at it hit, and its first launcher died at t=2669.

**2026-09-23, adjudicated against the test history (session `c2acb521`, at the DM's request)** — **what the tests settle, and the one link they do not.** Under Skynet a paired PD is also an ordinary network site: it engages aircraft like any other (TURKEY's Tor on test 39), and `pointDefencesGoLive` switches it to its HARM job only when the parent goes dark to evade a HARM (`goDark` with `harmSilenceID` set). A parent that can engage HARMs itself (`shallIgnoreHARMShutdown`) never goes dark, so its PD is never switched. What the evidence covers: only HARM-capable PDs are paired (`test_only_a_harm_capable_point_defence_is_paired`, and test 39's log dropping BLOODHOUND's and TETRA's); a Tor intercepts a HARM under native DCS AI (test 32: five of eight HARMs, terminal 38–95 m); the parent stays live when it can defend itself (test 39, TURKEY's HQ-7B passing 30 m from the HARM). What no test has shown: a paired PD knocking down a HARM aimed at its parent. Test 37's PD could not (guns and IR); test 39's Tor had fired all eight rounds at aircraft first. The pass criterion below is MANTIS-era: under Skynet the PD is not held silent on ingress.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **a HARM at a site whose PD can answer it, and the PD had nothing left.** `FALCON SEAD Escort` fired an AGM-88 at t=2796 that hit an HQ-7 launcher of `0006 | TURKEY (SAM)` at t=2935. Skynet paired `0007 | TURKEY (PD)`: a Tor 9A331 and two Shilkas. The Tor fired all eight of its 9M330s between t=2665 and t=2863, at aircraft (it killed a PORCUPINE DEAD F-16 and a BULLSHARK F-15E); its closest missile passed 11 km from the HARM. The HQ-7 stayed live, as Skynet intends for a site that can engage a HARM itself, and its own HQ-7B passed 30 m from the HARM at t=2909 without killing it. The log also shows the 2026-09-22 guard working: `0080 | BLOODHOUND (PD) cannot engage a HARM; not paired` and the same for `0069 | TETRA (PD)`. Still owed: a HARM at a paired site whose Tor has rounds left.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`; corrected 2026-09-22 from full-resolution tracks) — **a HARM at a paired site, and the pairing could not answer.** `FERRET SEAD Escort` fired four AGM-88 at `0126 | MAVERICK (SAM)` (SA-11) at t=2419–2437, from 70–75 km. Skynet had paired it with `0127 | MAVERICK (PD)`: two ZU-23 and two Strela-1 — guns and an IR missile, nothing that can engage a HARM. The PD fired nothing; the HARMs fell 2.2–2.4 km short at t=2563–2572. The row's pass needs a radar SHORAD (Tor, Tunguska, Pantsir) as the PD; this pairing is the fail-by-construction case, and worth checking in the Skynet config that IR-only groups are not being paired as point defence. **Checked and fixed 2026-09-22:** they were, and Skynet then held the parent SAM live on the PD's ammo count alone (`shallIgnoreHARMShutdown` never asks whether a PD can engage a HARM). Only 1 of test 37's 5 red PDs (SPARROW's Tor) could. The bridge now pairs only a PD Skynet rates HARM-capable; see `retlab-skynet-return-notes.md` §5. Unflown.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised through Skynet in any capture.** Test 32 is the only Skynet mission with HARM shots (8), and none was fired at a site with a paired point defence (POODLE never woke). The MANTIS-era test 14 evidence is now irrelevant. Needs a deliberate HARM at a site whose `(PD)` group Skynet holds dark.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — **not exercised through Skynet; the intercept itself is proven.** Skynet paired one red point defence, `0114 | POODLE (PD)`, and no HARM was fired at its parent, so it never woke. Five of the eight HARMs were still intercepted by SA-15 Tors in the coastal Silkworm groups and the airfield SHORAD groups (terminal 38–95 m from a 9M330, same second), under native DCS AI; the other three hit LEOPARD's two launchers and DOG's Silkworm search radar. The row still needs a shot at a site whose PD Skynet holds dark.

> **Re-pointed 2026-09-12.** The MANTIS `AddShorad` link is gone. Skynet pairs each site's
> `PD` groups to it natively (`addPointDefence`, from the same emitted arrays) and wakes them
> when a HARM is detected against the parent. Same pass criterion; the history below is MANTIS's.

**2026-08-22, test 14 — armed, no wake observed.** `Retribution-RED-IADS SHORAD link armed:
1 point-defense group(s) held dark, waking 600s on HARM/Maverick` (blue: 3). No wake event
followed. Whether a HARM was fired at the dark group was not established, so this is not evidence
either way — the row needs a shot deliberately taken at a site that has point defence.

**History:** built 2026-07-12 off the "which MANTIS features aren't we using?" audit; the bridge plumbing — PD-name collection/dedupe from the per-SAM `PD` arrays, Lua-pattern prefix escaping, one SHORAD per coalition defending `mantis.SAM_Group`, `autoshorad=false` captured AT `Start()` time, option threading, and the off/no-PD no-ops — is harness-tested in `tests/lua/test_mantis_shorad_link.py` with recording MANTIS/SHORAD fakes. The fake models no DCS AI: the actual sleep/wake and the intercept are DCS-only.
- **What it is:** each SAM site's co-located PD escorts (the "… (PD)" Tor/Tunguska/Avenger groups) are now wrapped in a MOOSE SHORAD object linked to MANTIS (`shoradLink` plugin option, default ON). The PD **sleeps** (alarm green / dark) until a **HARM or Maverick launch** against a defended SAM — or a MANTIS SEAD suppression within ~13.5 NM — **wakes it for 600 s** to engage the incoming shot while the big radar hides, then it goes back to sleep. OFF restores the old always-alert PD.
- **What CI cannot exercise:** whether the woken Tor/Tunguska actually shoots down the inbound HARM (the whole point), whether the sleeping PD is genuinely dark on ingress (no radar emission before the wake), whether it re-sleeps after the wake window, and that the PD still records kills/losses natively.
- **Setup:** any MANTIS campaign with PD-escorted SAMs. **Red Tide is the testbed since 2026-07-12:** the fork faction gained the **SA-15 Tor + SA-19 Tunguska** (era-correct '86/'82; user call off the roster audit — before that red's SHORAD was IR-only SA-9/13 + the Osa, none of which DCS tasks against missiles, so G30 would have been a red no-op; guarded in `tests/retlab/test_red_tide_faction_era.py`). Gen-probed: the S-300 regiment battalions draw Tor PD. NEW game required for the Tor (faction is generation-time); the SHORAD link itself is runtime-only. Check dcs.log for `SHORAD link armed: N point-defense group(s)`. Ingress on a site with an RWR: confirm no Tor emission while inbound (IR PD like SA-9/13 has no RWR signature — judge those by fire discipline, not emissions). Fire a HARM at the site from inside ~10 NM; watch the PD.
- **Pass:** the arm line shows a plausible PD count; the PD is silent on ingress (no SA-15 RWR nails before any shot); on the HARM launch the PD wakes (RWR lights up) and engages the missile — a HARM intercepted mid-flight is the marquee proof; after ~10 min without triggers the PD goes quiet again; a killed PD unit shows in the debrief like any other loss.
- **Fail signature:** `SHORAD link armed: 0` on a PD-rich campaign (the PD arrays stopped being emitted, or the prefix escaping broke — same class as the G6 zero-resolve bug); the PD radiates/engages strikers all mission with the link ON (autoshorad overwrite — the MOOSE Start() ordering broke); the PD never wakes on a HARM shot (SHORAD's shot watch not seeing the launch — check DefendHarms and the weapon name patterns); a SAM's OWN radar staying dark after its PD woke is fine (separate systems), but the PD staying asleep while its SAM dies to the HARM is the feature failing at its one job.

### G31 — Pilot recovery surge (next-turn "drop everything" rescue package) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §21 · ✗ REGRESSED (2026-08-05, user report `units-runway-generation-bf755e` — "G31 is non existant as far as I can tell": no recovery package has ever been observed in the ATO. **Investigate in gate order — `plan_pilot_recovery_surge` has FIVE independent early-returns and four of them are silent**, so "nothing appeared" does not yet distinguish a bug from a correctly-unmet precondition: (1) BLUE only; (2) `combat_sar_surge` ON — note it is `enabled_when=combat_sar_persistent_pilots`, so if that master is off the surge can never fire and the greyed child is easy to miss; (3) **an un-surged evader must already exist**, i.e. a pilot has to have gone MIA on a PREVIOUS turn and been banked into `game.downed_pilots` — a campaign where nobody has been shot down and left un-rescued produces no surge and that is correct behaviour, which is the single most likely explanation and should be ruled out FIRST; (4) no rescue package already planned; (5) the wing must field a rescue-capable HELO squadron — this one at least logs `Pilot recovery surge: no rescue-helo squadron available`. **Cheapest discriminator:** confirm a real MIA entry exists (SITREP band "MIA: … evading near …", the orange downed-pilot marker on the map, or the squadron roster) BEFORE the turn you expect the surge; if an evader is banked, the gate is on and nothing frags, that is a genuine bug. Worth adding an explicit log line to gates 1–4 either way, since four silent returns is why this row is unfalsifiable today) (was ☐ UNTESTED, built 2026-07-17 off the flown Scenic Route Merged finding "after 1.4 h the rescue helos are just getting to the pilots" — same-mission rescue can't beat helo transit time, so the NEXT turn opens with the recovery op already airborne. `plan_pilot_recovery_surge` (`game/retlab/csar_surge.py`, hooked in `Coalition.plan_missions` BEFORE the commander) frags one coordinated package at a `PilotRecoveryZone` centred on the MIA evaders: required Jolly rescue helo + optional second Jolly / King C-130 / 2-ship Sandy SCAR / A2A escort, ASAP TOT, `ignore_range` — and the existing `PackageBuilder` rule air-starts AI COMBAT_SAR flights, so the op is on station at mission start. **Gate:** once per downed pilot (`DownedPilot.surge_turn` stamp); gated `combat_sar_surge` (default ON, requires `combat_sar_persistent_pilots`). Guards/gate/composition unit-tested in ~~`tests/retlab/test_csar_surge.py`~~; the fulfiller build, the air-start position, and the runtime pickup are DCS-only.)

</details>
- **What CI cannot exercise:** whether the air-started Jolly actually spawns near its recovery hold (not at the departure field), whether the combatsar ledger dispatches the PACKAGE helo onto the re-spawned evader (`persistentSurvivors`) promptly, whether the pickup + delivery complete inside a normal mission, and whether the surge package suppresses the on-demand clone (`autoSpawn=false` when the surge helo is fragged).
- **READY-MADE TEST STATE (2026-07-17 night fly, session `tacview-test-analysis-5bb161`):** the
  fresh Scenic Route Merged turn-1 mission ended with **8 MIA evaders banked** in state.json —
  including the **player's own pilot** (Flash, down ~40 NM deep near the CHICKEN site → the
  depth-weighted roll runs ~90% capture, racing the surge) and **5 evaders over west-gulf
  water** (watch how `resolve_downed_pilots`' walks-home/depth roll treats water positions on a
  front-less theater). Process that turn and the next mission is the G31 exercise: expect ONE
  Recovery package air-started at the evader cluster, `surge_turn` stamps preventing re-surges,
  and the on-demand clone suppressed by the package helo.
- **Setup:** any campaign with a rescue-helo squadron; get a blue pilot down behind the lines (easiest: `combat_sar_test_easy_rescue` off + fly a jet into a SAM), end the mission un-rescued (pilot goes MIA), advance the turn. The ATO should show a "Recovery: <pilot>" package; the campaign log the "Pilot recovery surge" message.
- **Pass:** next mission opens with the Jolly airborne near the evader, the evader re-spawns (~30 s), the helo is dispatched onto them within minutes, pickup + delivery complete, the pilot returns to the roster at debrief, and no second surge is fragged on later turns for the same evader.
- **Fail signature:** the surge package exists but the helo spawns at its field and transits (air-start not applying — check `required_aircraft_start_type` on the departure), the helo orbits its hold and never dives to the survivor (the ledger not adopting package helos for persistent survivors), or a surge re-frags every turn for the same pilot (the `surge_turn` stamp not persisting).

### G34 — AI landing pickup: touchdown, embark, and the rescue reported back · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, adopted 2026-08-07; the Python halves — the embark task, the pickup waypoint, the landing-zone clear-of-survivor and clear-of-water placement, the rescue crediting and the two-turn recovery — are unit-tested across `tests/test_csar.py`. The DCS side has no harness coverage at all: there is no ~~`tests/lua/test_opscsar_runtime.py`~~
- **What CI cannot exercise:** the native-embark chain runs entirely inside DCS and fires no event. The survivor carries `EmbarkToTransport` in a 300 m zone; the rescue flight's pickup waypoint carries `Embarking`; DCS walks the survivor aboard and deletes the group silently. `OpsCSAR.lua` *infers* the pickup from a landing with a nil `place` plus 20 s on the ground. Whether the AI sets down inside the zone, holds it long enough, and whether the survivor walks at all are DCS behaviours.
- **Setup:** **`csar_hover_extraction` OFF** — this is not the shipped default, and without turning it off you are testing G35 instead. `csar_ejection_chance` 100. Eject over friendly-side ground near the front, end the mission, pass the turn. Next turn the planner frags a CSAR helo; fly any slot in the package or start-and-quit and read the log. ~45 min.
- **Pass:** `dcs.log` carries, in order, `has landed to collect <uuid>`, then `lifted from the pickup after Ns` with N ≥ 20, then `Pilot <uuid> embarked on <helo>`. Blue smoke is visible at the survivor while the helo is in the zone. After the turn passes the pilot is in the roster **Recovering**, not MIA.
- **Fail signature:** `still reports as present 420s after <helo> reached the embark zone` — the helo arrived but the embark never fired; the touchdown fell outside the 300 m `EMBARK_ZONE_RADIUS`, or the `Embarking`/`EmbarkToTransport` pair did not pair. **No `has landed to collect` line despite a helo visibly on the ground** — the `S_EVENT_LAND` carried a non-nil `place`, i.e. DCS classed the LZ as an airfield/FARP. **`too brief to have loaded anyone`** — the AI is not holding the LZ; the `Embarking` task's hold is the real fault, not the 20 s constant. In all three the pilot goes MIA despite a helo having reached him.

### G35 — AI hover hoist completes and releases the flight, including over water · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, adopted 2026-08-07 — **this is the shipped default**, `csar_hover_extraction` defaults ON. The hover geometry and the water branch are unit-tested in `tests/test_csar.py`; a DCS AI helo holding a zero-speed circle is not modellable headless
- **What CI cannot exercise:** under hover extraction there is no native mechanic — the plugin runs the whole pickup. It pushes a DCS Orbit/Circle at speed 0 and `surface + hover_altitude`, destroys the survivor after 30 s, then pops the task so the flight resumes its route. Whether a DCS AI helo holds a zero-speed circle at all, holds it stably for 30 s, and resumes cleanly on `popTask` is DCS-only. Over water the reference surface is the sea, not the seabed — a wrong reference puts the helo underwater or hundreds of feet high.
- **Setup:** defaults (hover ON), `csar_ejection_chance` 100. Run it **twice**: once with the survivor on land, once ditched over open water ≥ 5 NM offshore. ~40 min for both.
- **Pass:** `dcs.log` shows the hover start, the hoist 30 s later, and the flight resuming its route to a friendly field; the helo visibly holds a stable hover over the survivor at roughly the briefed height; over water the helo hovers just above the surface, not at altitude and not in it.
- **Fail signature:** the helo arrives and **orbits forever without hoisting** — the hover task was rejected or the 30 s timer never armed; the flight never RTBs and the mission ends with the survivor still down. The helo **hovers at a wildly wrong height over water** — the surface reference resolved to the seabed. The helo hoists but then **flies its original route as if nothing happened**, never delivering — `popTask` restored the wrong task. A hung hover also burns the airframe: it will run itself out of fuel.

### G37 — Multiplayer: a non-lead client can run the rescue · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, **nobody has looked at this at all** — the adoption's 139 tests are all single-player-shaped, and this is a squadron fork whose events are crewed by several humans
- **What CI cannot exercise:** MOOSE registers the CSAR F10 menu against a group's **first alive unit**. In a multi-crew squadron event the rescue helo may be flown by a client who is not that unit, and a second client may join a slot mid-mission. Whether the menu appears for them, whether the survivor boards *their* aircraft, and whether the rescue credits to the campaign are all untested and all plausible failure points.
- **Setup:** a two-client MP session on a generated mission with a live survivor. Client A takes the helo's lead slot, client B a second seat or a second helo. Have **B** attempt the rescue. Also have a client join the helo slot *after* mission start and check the menu appears for them. ~40 min plus a second person.
- **Pass:** both clients see the CSAR F10 menu; the survivor boards whichever aircraft actually performed the pickup; the rescue credits once, to the campaign, regardless of who flew it; a late-joining client gets the menu.
- **Fail signature:** the menu is missing for the non-lead client (the group-first-unit registration); the survivor boards but the rescue never credits (the delivery detection keyed on the wrong unit); the rescue credits **twice**; a late joiner never gets the menu even after respawning.

### G38 — `csar_rescue_ai_pilots` ON spawns a survivor for every AI ejection · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, default ON. The Python side only creates a `DownedPilot` for tracked airframes, but MOOSE's own ejection handler is a separate path with its own spawning
- **What CI cannot exercise:** with `csar_rescue_ai_pilots` ON, MOOSE's ejection handler runs for **every** AI ejection on both sides, not just the ones the campaign tracks. On a busy mission that is potentially dozens of survivor groups, each with a beacon and a MAYDAY, none of which the campaign knows about. This is exactly the "never spawn phantom units" line the fork holds elsewhere, and nothing has counted them.
- **Setup:** a mission with a heavy air battle (a large BARCAP engagement or a Vietnam-style furball). Fly or spectate to the end, then count survivor groups in Tacview and grep `dcs.log` for the registration lines. ~30 min.
- **Pass:** the survivor count is bounded and matches what the campaign tracked; performance is unaffected; no runaway MAYDAY spam on the radio.
- **Fail signature:** dozens of survivor groups and a wall of MAYDAY calls; a measurable framerate drop late in a heavy mission (the §L TIC lesson — too many ground units); survivors on the map the campaign has no record of, which then vanish at turn end with no explanation.

### H1 — Folded-list overflow pagination · §4 · ☑ VERIFIED

**History:** 2026-06-25
- **Verified (2026-06-25, generated kneeboard):** a long Friendly Packages / Airfield
  Directory flowed onto a `(cont.)` continuation page with nothing clipped at the bottom
  edge. Fail signature did not occur.
- **Logic-reviewed 2026-06-25 (de-risked, not flown):** the row-fit math is correct and
  conservative. `remaining_table_rows` computes `(image_height - page_margin - y) //
  line_height`, subtracts tabulate's 2 lines of header chrome, and leaves **one row of slack**
  (`max(0, capacity - 1)`) so a table never kisses the bottom edge; `line_height` is **measured
  empirically** from a one-line-vs-two-line `textbbox` delta (matches PIL's real multiline
  layout, not font metrics). Both folded lists (`BriefingPage` "Friendly Packages",
  `SupportPage`/Airfield "Airfield Directory") probe with `_render`, then push the overflow into
  a `TableKneeboardPage(..., continued=True).paginate()` — and `paginate()` **re-splits**
  recursively with `capacity = max(1, remaining_table_rows(...))`, so a continuation page can
  neither overflow nor infinite-loop, and the probe/`write()` cursor match (the `(cont.)` suffix
  changes heading text, not line count). **Residual flight risk:** only that PIL's runtime
  rendered line-height + `courbd.ttf` load match the measured estimate on the DCS-side image —
  environment, not logic.
- **Setup:** Generate a mission on a **busy theater** (many friendly packages
  and/or many BLUE airfields with ATIS) for a client flight with a long flight
  plan. Open the generated kneeboard in DCS.
- **Pass:** The Mission Info "Friendly Packages" list and the Support Info
  "Airfield Directory" never run off the bottom edge; rows that don't fit appear
  on a following "Friendly Packages" / "Airfield Directory" continuation page
  (later pages marked "(cont.)"). Small theaters show no extra pages.
- **Space-utilisation pass (2026-06-25, see §4):** light restyle — bold heading + thin
  underline rule + content, sections spread with whitespace (no boxes). When the Friendly
  Packages list is long enough to overflow one column it renders in **two side-by-side columns**
  filling the right half of the page, and the common case no longer spills a near-empty
  continuation page. The **Support Info** page's Package / AEW&C / Tankers / JTAC sections use
  the same heading+rule treatment, spaced to fill the page. **Pass:** two-column packages line
  up (each column has its own header row, no overlap between columns, no text clipped at the
  right edge); Support sections span the page without huge dead space. **Fail signature:**
  columns overlapping or the right column clipped at the page edge (lower `col_gap` math in
  `table_two_column_paginated()`), or an underline rule drawn over text.
- **Fail signature:** Table text clipped at the page bottom with rows missing, an
  empty continuation page, or a continuation page whose rows still overflow.
  Check `table_paginated()` / `remaining_table_rows()` row-height math in
  `kneeboard.py` if seen.

### H2 — Combat SAR task kneeboard · Combat SAR Phase 4 · ☑ VERIFIED

**History:** 2026-06-25
- **Verified (2026-06-25, in-game):** both kneeboard task pages render correctly — the role-aware
  briefs (CH-47 pickup vs. C-130 King on-scene-command), beacon tables, and F10 `CSAR` reference
  showed as designed with no clipping. Fail signature did not occur.
- **Setup:** Plan a player **CH-47** Combat SAR flight (and, separately, a player **C-130** Combat
  SAR). Open each flight's kneeboard in DCS.
- **Pass:** Each flight has a "Combat SAR" task page. The CH-47's shows the **pickup** procedure
  (ROLE = rescue helo; hover/land at the beacon, deliver to a friendly field/FARP) plus a **KING
  BEACON** table with each King's callsign + TACAN to home on; the C-130's shows the
  **on-scene-command** brief (ROLE = HC-130 "King"; hold overhead, don't land) plus **YOUR BEACON**
  (its TACAN + the LARS hint). Both reference the F10 `CSAR` menu. Text wraps inside the page, no
  clipping. **Layout (2026-06-25, §4):** light style — each section is a heading + thin underline
  rule + larger body text, with the leftover height spread as capped even gaps so the page
  breathes top-to-bottom (no boxes, no blank bottom two-thirds). **Fail signature here:** an
  underline rule drawn over text, or sections bunched at the top with dead space below (the
  `section_gap` distribution math in `CombatSarTaskPage.write`).
- **Fail signature:** wrong role brief for the airframe (helo gets the King text or vice-versa), a
  KING BEACON TACAN that doesn't match what the King actually radiates in-game, text running off the
  page edge, or no Combat SAR page at all (`generate_task_page` branch).

### H3 — SCAR task kneeboard (Phase 4) · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §15 / PR #189 · ☑ VERIFIED (2026-06-26, user in-game pass)

</details>
- **Headless adjudication (2026-06-26):** the flight↔tasking matching that drives the
  TARGET SIGNATURE is verified by `tests/missiongenerator/test_kneeboard_task_pages.py`
  (passing): `_scar_tasking_for` links a SCAR flight to its tasking by package-target
  identity (the right signature on the right page), and a non-matching / no-target flight
  gets `None`. **Residual (in-sim only):** the rendered page itself — section text wraps
  without clipping and the on-page guidance matches in-mission behaviour (smoke→target
  timing, laser-only-with-King).
- **Setup:** Plan a player **SCAR** flight; open its kneeboard in DCS.
- **Pass:** A "SCAR" task page with **TASK** (hold the box, service the designated armor, kills count
  natively), **TARGET SIGNATURE** (this flight's own HVT signature, e.g. "1x SA-9 + 1x command vehicle
  + 2x truck", + decoy/mis-ID warning; a SCUD tasking reads "mobile SCUD launcher (TEL)"), **FIND + ID**
  (decoys + mis-ID cost; GREEN box smoke → RED target after ~2 min), and **DESIGNATION** (smoke colours,
  King laser code 1688, the "say again" F10). Text wraps, no clipping. The signature must **match the
  real picture** in the box (it's the same data the MAGIC call uses) and carry **no exact target coords**
  (finding it is the task).
- **Fail signature:** no SCAR page (`generate_task_page` branch); **no TARGET SIGNATURE section** (the
  flight didn't match its tasking — `_scar_tasking_for` / `target_id`, or `mission_data.scar_taskings`
  empty); a signature that doesn't match what's in the box (wrong tasking matched); text off the page
  edge; or guidance that contradicts the in-mission behaviour (e.g. claims a laser with no King).

### H4 — Custom kneeboard import (UI) · §4 · ☑ VERIFIED

**History:** 2026-06-26, user in-game pass
- **Headless adjudication (2026-06-26):** the scope-routing + persistence are verified by
  `tests/missiongenerator/test_custom_kneeboards.py` (passing): `_inject_custom_kneeboards`
  keys an unscoped page to `""` (all client flights) and an airframe-scoped page to that
  unit-type id only (mirroring the DCS loose-folder convention), and `game.custom_kneeboards`
  round-trips through pickle with `__setstate__` defaulting pre-feature saves to `[]`.
  **Residual (in-sim/UI only):** the Qt import dialog (PNG-normalisation in
  `QCustomKneeboardsWindow.add_kneeboard`) and the page actually appearing on the right
  airframe in DCS.
- **Setup:** With a campaign loaded, open **Kneeboards** (toolbar/menu). Add an image scoped to
  **All flights**, add a second scoped to a **specific airframe**, then save the campaign, reopen
  it (verify the entries persisted), generate a mission, and open the kneeboards in DCS.
- **Pass:** The "All flights" image appears in **every** client flight's kneeboard; the
  airframe-scoped image appears **only** on that airframe's flights. Entries survive a
  save/reload (stored in the `.retribution` file). Removing an entry drops it from the next
  generated mission.
- **Fail signature:** imported page missing in-game, appearing on the wrong airframe, not
  persisting across save/reload (`game.custom_kneeboards` not pickled / `__setstate__` default),
  or a corrupt image (PNG-normalisation in `QCustomKneeboardsWindow.add_kneeboard`). Note DCS
  kneeboards are per-airframe — two flights of the same type necessarily share pages.

### H5 — Threat Intel Brief kneeboard · §4 · ☑ VERIFIED

**History:** 2026-06-26, user in-game pass
- **Setup:** Enable **Generate threat intel brief kneeboard page** (Mission Generator →
  Kneeboard). On a campaign with several enemy SAM/EWR types — some already discovered
  (struck/scouted/TARPS) and some not — generate a mission for a player flight and open the
  kneeboards in DCS. Compare the dossier against the F10 map's enemy air-defense picture.
- **Pass:** A "Threat Intel Brief" page shows **one card per enemy system** — system name, a
  curated Guidance + Ceiling line, the live MEZ / Detection / HARM ALIC, live/dead site counts,
  bullseye cues, and a **DEFEAT:** tactics note. **Undiscovered** sites collapse into per-band
  "Unidentified MERAD" cards (no system/range/HARM/defeat) and the intro counts them. Live,
  longest-range systems sort to the top; more cards than fit flow onto `(cont.)` pages. The page
  is absent when the setting is off or the enemy has no air defenses. Spot-check that a card's
  curated text (guidance/ceiling/defeat) matches the actual system.
- **Fail signature:** a fogged site leaking its exact system/range/HARM/defeat (recon-fog
  regression in `build_threat_intel_cards`); friendly AD listed; wrong system→reference mapping
  (e.g. an SA-6 card showing SA-10 defeat text — check `game/data/threat_reference.py` keys);
  garbled bullseye cue or MEZ; a card overrunning the page bottom instead of paginating; the page
  appearing for the **enemy** side's same-airframe flight with BLUE air defenses (known
  per-airframe DCS limitation — note, not a bug).

### H6 — Mission code words + Comms & Brevity card · §4 · ☑ VERIFIED

**2026-10-12 — the code words half was REMOVED on the DM's call** (verified below, off in his defaults and every save). The setting, the BLUF line, the Support Info block and the ATO table are deleted. Whatever else this row covers is unchanged.

**History:** (2026-06-26, user in-game pass) — **surface superseded 2026-07-13**: the Comms & Brevity card + brevity crib are deleted in the back-to-upstream rework; the code words live in the Mission Info BLUF + a Support Info block (re-check under H12). The planner panel/tooltip/JOIN-tag checks below remain valid.
- **Setup:** Enable **Package code words** (Mission Generator → Kneeboard) on
  an ATO with a mix of tasks (e.g. a SEAD, a STRIKE, and a CAP package). In the planner, read the
  **persistent code-word panel** under the package list, **hover a package** (tooltip), and **open
  a flight's plan** (find the JOIN waypoint). Note the table. Regenerate the mission a couple of
  times **without re-planning the turn**, then generate and open the kneeboards in DCS.
- **Pass:** The planner panel shows a **`Code words — <theme>`** table with a **push word per task
  present** (SEAD / STRIKE / CAP …) + `SUCCESS` / `ABORT` (and `STOP JAM` only if an EW/jamming
  flight is in the ATO). A package's tooltip shows that package's push word + the events; its
  flight's JOIN waypoint reads `Join — PUSH <word>` matching the panel's row for that task. The
  in-cockpit **Comms & Brevity** page shows the **same full table** with the flight's own task row
  marked `(you)`, plus a brevity crib **matching the task** (SEAD → MAGNUM/SPIKE/MUD…; CAP →
  FOX/COMMIT/TALLY…). **The words do NOT change** across regenerations of the same turn; a **new
  turn** yields a fresh themed set. With the setting off: no panel, no tooltip, no `PUSH` tag on
  JOIN, no Comms & Brevity page.
- **Fail signature:** a task's push word differing between the panel, the tooltip, the JOIN
  waypoint, and the kneeboard (the `Coalition.code_words` single-source contract broke); words
  rerolling within a turn or NOT refreshing on a new turn (turn-stamp logic); the `PUSH` tag
  leaking onto a target/DTC steerpoint (should only ever be on JOIN); STOP JAM showing without an
  EW flight; brevity crib not matching the task; the feature appearing with the toggle off.

### H7 — Fuel ladder kneeboard card · §4 · ☑ VERIFIED

**History:** 2026-06-26, user in-game pass) — **surface superseded 2026-07-05**: the standalone page + `generate_fuel_ladder_kneeboard` are deleted; the ladder rides in the flight plan as a `Fuel` column + RTB-margin line (re-check under H12
- **Setup:** Enable **Generate fuel ladder kneeboard page** (Mission Generator → Kneeboard).
  Generate a mission for a player flight — ideally one with a tanker (REFUEL) leg — and open the
  kneeboards in DCS. Cross-check the Fuel Ladder against the flight-plan page's Min-fuel column and
  the jet's actual fuel at a couple of steerpoints.
- **Pass:** A "Fuel Ladder" page lists each steerpoint with **Plan** (planned fuel remaining) and
  **Min** (minimum to RTB, matching the flight-plan page) and **Margin** (Plan − Min). Plan
  **descends** leg by leg and **jumps back up at the tanker** waypoint; Min matches the existing
  flight-plan column; Margin goes **negative** only where the plan genuinely can't make it home.
  Bingo/Joker show at the bottom. Numbers are in the airframe's kneeboard mass unit (lbs/kg). With
  the setting off, no Fuel Ladder page.
- **Fail signature:** Plan not decreasing (or not resetting at the tanker); Plan wildly off vs. the
  jet's real fuel (burn-model/units error — check `flight.fuel × KG_TO_LBS`); Min disagreeing with
  the flight-plan page's Min-fuel column; Margin sign wrong; the page appearing with the toggle off
  or absent for an aircraft that has fuel-consumption data.

### H8 — Kneeboard de-duplication · §4 · ☑ VERIFIED

**History:** 2026-06-26, user in-game pass) — the Min-fuel-column half is obsolete since 2026-07-05 (the flight plan always carries the folded `Fuel` column; there is no Fuel Ladder page to de-dup against
- **Setup:** Two passes. **(a)** Generate with the recon, fuel-ladder, and all-packages kneeboards
  **all ON** for a ground-start SEAD/Strike flight in EXACT intel. **(b)** Generate the same flight
  with those three **OFF**.
- **Pass:** With options ON — Mission Info has **no weather block** (it's on the Departure page) and
  **no Min-fuel column** in the flight plan (it's on the Fuel Ladder page); the Friendly Packages
  list is its **own page** (not folded into Mission Info's bottom); there is **no standalone SEAD/
  Strike Target Info page** (the recon Detail page carries the emitters + ALIC). With options OFF —
  the deck is **identical to before**: Mission Info shows weather + Min-fuel column, the packages
  list folds into Mission Info, and the SEAD Target Info page is present. In **APPROXIMATE** intel,
  the SEAD Target Info page is **kept** even with recon on (no exact-coord leak).
- **Fail signature:** any datum still on two pages with options on (weather, Min fuel, the packages
  list); the SEAD page dropped in Approximate intel (coord-fuzzing regression); the deck changing
  when all three options are off (a default-path regression — the omit flags must default to keep);
  Mission Info's flight-plan column count wrong (uom row mismatched with headers).

### H9 — Compact 3-4 page kneeboard deck · §4 · ⊘ RETIRED

**History:** 2026-07-05, back-to-basics rework; was ☑ VERIFIED 2026-06-26
- **What happened:** the compact folding machinery (`compact_kneeboard`, the composite
  P2/P3/flex pages, `_draw_section_if_fits`) was deleted in the kneeboard back-to-basics rework.
  The 2026-07-13 back-to-upstream rework then retired the Brief Sheet + cover page too (§30/§31);
  the colour palette and the threat-intel cards (default ON) survive on the upstream-shaped deck.
  The current deck shape is checked under **H12**.

### I1 — Per-squadron DCS country / nation voiceovers · §23 · ☑ VERIFIED

**History:** 2026-06-26, user in-game pass
- **Headless adjudication (2026-06-26):** Exercised `CountryAssigner` directly (no
  mission). The realistic CJTF case (blue USA+Greece vs red Russia+Iran with red also
  flying a US squadron) resolves correctly — each squadron under its own country, the
  red US squadron falls back to Russia, no cross-coalition overlap, and the
  canonical-instance discipline holds (`for_squadron` returns the very instance
  registered on the coalition); the single-nation faction is a true no-op. Covered by
  `tests/missiongenerator/test_country_assigner.py` (now 6 passing). **Bug found + fixed:**
  the cross-side guard protected red squadrons from blue but **not** a blue squadron whose
  country equals *red's faction country* — that nation got registered on **both**
  coalitions (the "illegal .miz" fail signature). Added the symmetric reservation (a blue
  squadron sharing red's faction country falls back to blue's faction country) + a
  regression test. **Residual (in-sim only):** the AI radio actually playing the per-nation
  voice (follows from the now-verified country assignment).
- **Setup:** Start a campaign for a **CJTF (coalition) faction** whose air wing draws squadrons
  from more than one nation (e.g. a Blue CJTF with both a US and a Greek viper squadron). Auto-plan
  a turn so flights from at least two nations are tasked, generate the mission, and either inspect
  it in the DCS Mission Editor (group → Country) or fly/observe AI flights and listen to AI radio.
- **Pass:** Each flight's group is set to **its squadron's own country** (US squadron → USA, Greek
  squadron → Greece), each coalition lists all the nations its squadrons use, and AI comms play the
  **per-nation voice** rather than one shared faction voice. A single-nation faction is byte-for-byte
  unchanged (all groups on the faction country).
- **Fail signature:** all groups collapse onto one country (no per-nation voice); a country appears
  under **both** coalitions (illegal `.miz` — the cross-side conflict rule failed); groups silently
  missing from the saved mission (canonical-instance discipline broken — a duplicate `Country`
  instance was passed at spawn vs. registered on the coalition).

### I3 — Date-gated helmet cueing (JHMCS) · §24 · ☑ VERIFIED

**History:** 2026-06-26, user in-game pass
- **Reworked 2026-07-15 (no re-fly needed):** the data moved into each aircraft's own yaml
  (`date_gated_properties` → `AircraftType.property_date_gate`) and the gate now rides its **own
  `restrict_props_by_date` toggle** instead of the weapons one; the clamp path is unchanged and
  fully re-unit-tested (registry gates exactly the four `HelmetMountedDevice` airframes + a pydcs
  label pin). SURA Visor was dropped (mod-only airframe); the A-10C II HMCS (2012) and MiG-29 HMS
  (1983) gates are new data. When re-flying anything here, use the NEW setting.
- **Headless adjudication (2026-06-26):** The gate is pure, table-driven logic covered by
  `tests/dcs/test_aircraftproperties.py` against real pydcs `FA_18C_hornet`/`F_16C_50` props —
  JHMCS (id 1) gated before 2003, baseline (0) and NVG (2) always available, `period_correct_value`
  clamps the JHMCS default to the baseline pre-2003, and the Soviet "SURA Visor" (same id 1, Su-30/
  Su-35) is **not** gated because the table keys on the label. The generation clamp
  (`flightgroupconfigurator.degrade_props_for_date`) resolves against the unit-type default, so the
  defaulted-JHMCS case is handled, not just explicit selections. **Residual (in-sim only):** that the
  generated `.miz` actually spawns the baseline helmet option in-cockpit pre-2003.
- **Setup:** Start a campaign **before 2003** with `Restrict weapons by campaign date` **ON** and an
  F/A-18 or F-16 squadron. Open a flight's payload → the helmet-device dropdown should not list
  JHMCS. Generate and open the `.miz` (or fly) and check the aircraft's mission options.
- **Pass:** Pre-2003, JHMCS is absent from the dropdown and the generated mission shows the baseline
  helmet option (Not installed / Visor Only); NVG stays available in every era; with the setting OFF
  (or in a 2003+ campaign) JHMCS is offered and applied normally. Soviet jets keep their SURA Visor.
- **Fail signature:** JHMCS still selectable/applied in a pre-2003 campaign with the setting on; NVG
  or the Soviet SURA Visor wrongly removed; the dropdown shows nothing selected; a non-helmet
  property (laser code, datalink) changed by the gate.

### I4 — Frontline clustered laydown + default stance (PR #823 adoption) · §9 · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — front clustered along the line
- **Why:** Adopted PR #823's proportional mixed armor clusters + even-spread placement
  (`ai_ground_planner.py`, `frontline_clustering.py`, `flotgenerator._generate_groups`), with
  #823's DCS-task cohesive maneuver TIC-guarded behind `not self.tic_enabled`. Composition /
  placement is unit-tested and the TIC guard is locked by
  `tests/missiongenerator/test_flotgenerator_tic_guard.py`; only the in-sim *look* of the laydown
  needs eyeballing. Two builds to watch: TIC-on (default) and TIC-off.
- **Setup:** Generate a campaign mission with a populated armor front. (a) TIC ON (default):
  inspect/fly the front. (b) TIC OFF: regenerate and inspect to exercise the #823 maneuver path.
- **Pass (TIC on):** frontline armor spawns in evenly-spread clusters (no bunching at one offset),
  mixed/alternating armor types, SHORAD/ATGM/recon positioned around each wedge (recon ahead,
  SHORAD/ATGM behind), nothing stacked on the FLOT; movement is still the TIC scripted firefight,
  SHORAD/RECON static. **Pass (TIC off):** clusters maneuver cohesively (wedge advances, followers
  keep formation; APC-led wedges don't split in BREAKTHROUGH). **Default stance:** with auto-stance
  OFF, a new campaign / freshly captured player CP starts on the configured stance.
- **Fail signature:** units bunched at one along-front offset or stacked on the FLOT; single-type
  monoculture groups (composition not applied); on a TIC build, armor/ATGM driving via DCS AI tasks
  or SHORAD/RECON maneuvering (the #823 maneuver leaked past the TIC guard — should be impossible,
  test-locked); on a TIC-off build, clusters splitting apart in BREAKTHROUGH; the default-stance
  setting ignored at new-game/capture.

### I5 — Nation-aware pilot names · §23 · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — names match squadron nationality; live-save confirmed 2026-06-27
- **Live-save confirmation (2026-06-27):** Loaded the actual flown campaign
  (`autosave.retribution`, GermanyCW turn 2, Blufor Late Cold War vs Russia 1980) headless and
  resolved every squadron's `faker` against its `country`. The blue wing is a genuine **4-nation
  CJTF** and each squadron draws its **own** nation locale even though the blue faction's
  `locales` is `None` (so there is no shared-faction locale to fall back to): USA squadrons →
  `en_US`, JaboG 31 / GAF JG 74 → `de_DE`, IAF 69 FS → `he_IL`, Ala 14 (Mirage F1) → `es_ES`;
  every red squadron → `ru_RU`. Countries used: blue `[Germany, Israel, Spain, USA]`, red
  `[Russia]` — **no cross-coalition country overlap** (the illegal-`.miz` fail signature). This
  is a stronger real case than the unit tests (4 live nations). **Residual (in-sim only):** the
  AI radio actually *playing* the per-nation voice — the country-assignment half of that is I1,
  already VERIFIED in-game 2026-06-26.
- **Headless adjudication (2026-06-26):** the country→locale resolver is fully covered by
  `tests/squadrons/test_pilotnames.py` (mapped country → its own-locale Faker; unmapped /
  multinational / `None` → faction fallback; locale cache independent of fallback; **every**
  mapped locale is gender-aware so a typo'd/non-gendered locale fails CI rather than shipping; a
  squadron recruits non-empty named pilots from its country locale). Sample rosters per nation
  read right (Greek, Persian, Russian surname-first + patronymic, Japanese, Hebrew). **Residual
  (UI/in-sim only):** the names actually rendering in the squadron/roster UI and, if shown,
  in-cockpit — non-Latin scripts in particular.
- **Setup:** A mixed-nation CJTF campaign (e.g. a Blue side with a US and a Greek squadron). Open
  the air-wing / squadron roster and read the pilot names; optionally generate a mission.
- **Pass:** Each squadron's roster carries names in its **own** nation's convention (US squadron →
  US names, Greek → Greek, etc.); a single-nation faction is unchanged; the CJTF / UN /
  Insurgent "countries" fall back to the faction names (no crash, no blanks).
- **Fail signature:** a squadron's pilots all share one nation's names regardless of country (the
  `Squadron.faker` wiring didn't take); blank/garbled names; or a recruitment crash on a locale
  with no gendered names (guarded + test-locked — should be impossible).

### I6 — Squadron country surfaced (dialog selector + campaign `country:` pin) · §23 · ☑ VERIFIED

**History:** 2026-07-20, user in-game pass, session `dcs-mission-gspd-fuel-222a42`: "896 is flown and good" — the selector + DS `country: USA` pins flown same day they were built; blanket pass, sub-criteria not itemized. NOTE: upstream draft #896 is deliberately HELD as a draft despite the pass — DM call, "don't flip it just in case it was after the lock", the lock being the upstream no-new-PRs freeze until the next beta (~2026-07-25/26 weekend; #896 was opened the day the freeze was learned) — un-draft only on a fresh explicit call once the freeze lifts. Built from the flown Desert Storm finding: Israeli/Greek-voiced F-16s wearing the 23rd TFS name, because an airframe-name squadron pick is a random.choice across every nation's presets under a CJTF faction
- **Headless adjudication (2026-07-20):** the config parse, the same-nation-only preset filter
  (falls through to the def generator rather than hijacking a wrong-nation preset), the
  override stamp (valid/unknown/unset), and the selector's live write / replace-with-preset
  re-point / unlisted-country display are covered by `tests/test_squadron_country_pin.py` +
  `tests/test_airwing_country_selector.py` (offscreen Qt); the 13 DS pins are locked by
  `test_desert_storm_us_squadrons_pin_their_nation`. **Residual (app/in-sim only):** the
  selector rendering in the real dialog, and the DS voices actually playing American.
- **Setup:** New Game → Umm al-Ma'arik (Desert Storm 1991) → Air Wing Configuration. Check each
  US squadron's new **Country:** selector reads USA (the pin); flip one squadron to another
  nation and back; use **Replace with preset** once and confirm the selector tracks the new
  squadron; note the preset dropdown entries now read `Name (Nickname) [Nation]`. Start the
  campaign, fly/observe a US flight.
- **Pass:** US flights check in with **American** AI voices (the flown Israeli/Greek roulette is
  gone); the squadron roster names are American; a country picked in the dialog sticks after
  Accept Changes and shows on the generated mission's groups (ME: group → Country); Save
  Config → Load Config keeps the country.
- **Fail signature:** a US-named squadron still spawns under Israel/Greece (pin not applied — the
  filter or override didn't take); a dialog country change silently reverts on Accept (live-write
  wiring broken); after Replace with preset the country/livery edits land on the discarded
  squadron (the re-point fix regressed); New Game crashes on a campaign with `country:` (the
  unknown-name degrade failed).

### H11 — Estimated fuel figures for dataless airframes · §4 · ☑ VERIFIED

**2026-08-17 — VERIFIED on the DM's call**, clearing the REGRESSED mark. Supporting evidence from the same day's rendered kneeboard: the flight-plan table carried a Fuel column populated at every waypoint plus a Bingo/Joker block (8,800 / 9,800 lb). That page was an F/A-18C, which HAS measured data, so it corroborates the ladder rendering rather than the dataless fallback this row is named for.

**History:** 2026-08-05, user report `units-runway-generation-bf755e` — "H11 is generating too much fuel for aircraft in cases": the ESTIMATE over-reads, so the kneeboard `Fuel` column and the derived RTB margin flatter the jet — the dangerous direction, since an over-generous estimate tells a pilot they can make it home when they cannot, and the same numbers feed the §46 tanker decision, so an inflated figure can also suppress a tanker pass the sortie actually needed. **Needs the specific airframes** — the estimate only applies to types with no `fuel:` block in their yaml, so the fix is either a better model or real per-airframe data for the offenders, and which it is depends on whether the over-read is uniform or type-specific. `tests/dcs/test_estimated_fuel_consumption.py` sanity-bands the estimate but the band is evidently too loose to catch this) (was ☐ UNTESTED, estimate sanity-banded in `tests/dcs/test_estimated_fuel_consumption.py`, 2026-06-27; the surface moved 2026-07-05 — the figures now render in the flight plan's `Fuel` column on Mission Info, not a Fuel Ladder page
- **Deferred (2026-06-28, user: "update after kneeboard update"):** revisit once the pending kneeboard changes land — re-check the C-130J King / helo Fuel Ladder against the current deck so the estimate is validated against the updated kneeboard rather than the old one.
- **What it is:** `AircraftType.estimated_fuel_consumption` synthesises a rough `FuelConsumption` from
  the airframe's `fuel_max` (bucketed helicopter / heavy-transport / combat) so the Fuel Ladder card
  renders for airframes with **no** hand-measured `fuel:` block — the **C-130J "King"**, helicopters,
  warbirds, etc. Kneeboard-scoped: planner tanker tasking + in-flight sim are untouched.
- **Setup:** frag a player flight in an airframe with no measured fuel data — ideally the
  **C-130J King** (the reported case) and a helicopter — and open the Mission Info kneeboard page.
  Cross-check against an airframe that *does* have measured data (e.g. F/A-18C).
- **Pass:** the King / helo flight plan's **`Fuel` column renders a descending ladder** with the RTB
  margin call-out under the table, instead of all-blank cells. Numbers are plausible planning
  figures (the King cruises ~16 lb/NM, full ~43k lb, so it should *not* read negative-margin on a
  normal sortie). Measured-data airframes are unchanged.
- **Fail signature:** an all-`-`/blank Fuel column for the King/helo (no planned figures —
  `flight.fuel` missing or the estimate not engaging); wildly implausible numbers (e.g. the King
  reading ~80 lb/NM, a sign the heavy bucket isn't being picked — check `_is_heavy_airframe`); any
  change to a measured-data airframe's figures (the estimate must never override a real `fuel:`
  block); planner suddenly fragging tankers for the King (the fallback must stay out of
  `unit_type.fuel_consumption`).

### H12 — Back-to-upstream kneeboard deck (upstream pages + folded RetLab info) · §31 / §30 · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "H12 is good") (was ☐ UNTESTED, reworked 2026-07-13; the 2026-07-05 back-to-basics render pass covered the now-retired cover/Brief-Sheet deck
- **What it is:** the 2026-07-13 back-to-upstream rework (user markup pass on a flown Scenic Route Merged
  deck) — the cover page, Brief Sheet and Comms & Brevity card are **deleted**; the deck is
  upstream's page set with the kept RetLab info folded in. Per flight: **Mission Info** (BLUF —
  task/TOT, push words, JAM BACKUP, compact THREATS AIR/SAM, LOADOUT, SAR if-down — then airfield
  table, flight plan with Fuel column + RTB margin, upstream's `Bullseye:` line, weather,
  bingo/joker, laser, and the SITREP section at the bottom) → **Support Info** (comm ladder /
  AEW&C / tankers / JTAC / airfield directory + the colour-keyed **Code Words block** when
  `enable_package_code_words` is on) → Notes/task page → the setting-gated extras (threat cards
  default ON). A **flight index** page fronts the airframe deck only when 2+ client flights share
  the type (H10).
- **Headless adjudication (2026-07-13):** deck composition + BLUF lines + code-words block covered by
  `tests/missiongenerator/test_kneeboard_bluf.py`, `test_kneeboard_index.py`,
  `test_threat_intel_kneeboard.py`, `test_flightplan_fuel_column.py`; full suite green.
  **Residual (in-sim only):** the in-cockpit read of the reworked Mission Info page (BLUF density,
  SITREP fitting under the flight plan) and the Support page's code-words block.
- **Setup:** generate a mission with a client Strike/SEAD flight on defaults (code words ON for the
  Support block); open the kneeboard on turn 2+ so a SITREP exists.
- **Pass:** the flight's deck opens on Mission Info (no cover, no Brief Sheet); BLUF shows task,
  threats, loadout, SAR; the Bullseye line sits under the flight plan; the SITREP section renders at
  the bottom without clipping; Support Info shows the code-words block; no Comms & Brevity page.
- **Fail signature:** a cover/Brief-Sheet page still generated (stale build); the SITREP clipped off
  the page bottom on a long flight plan; TOP THREAT prose back in the BLUF; the code-words block
  missing with the toggle ON; threat cards absent on defaults.

### H13 — Target recon kneeboard: markers line up on the satellite tiles · kneeboard_recon alignment fix · ☑ VERIFIED

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "H13 good". NOTE: `generate_target_recon_kneeboard` was left default **OFF** pending exactly this pass — now that the alignment is confirmed, whether to flip the default ON is an open call worth making deliberately) (was ☐ UNTESTED, fixed 2026-07-18, the maintenance-day flesh-out-or-kill call on the default-OFF pipeline; two measured causes closed — (1) the dominant DCS-vs-real-world terrain georeference offset (~350 m median on Caucasus/GermanyCW, ~740 m Normandy — tens of page px at detail scale) was only corrected on airbase-anchored pages, and target/corridor/overview pages now apply the robust regional offset of the nearest measured airports (`airport_imagery.offset_near`: median-of-3, 2 km outlier cap, 250 km relevance limit); (2) the whole-page bilinear QUAD warp's interior curvature residual (up to ~5 page px / ~1.9 km ground on a 300 km overview, measured on real terrains) is removed by an n×n MESH warp whose cell corners are each projected exactly (`_mesh_cell_count`: 1 cell ≤ 40 km — detail pages byte-identical — up to 8). Anchor-airport precedence, the offset lookup's gates, the mesh selection/tiling, and the QUAD/MESH wiring are unit-tested in the kneeboard_recon suite (189 green), and the whole path is headless-verified on real Caucasus — the no-anchor regional offset near Anapa lands ~333 m, right on the terrain median. The setting `generate_target_recon_kneeboard` stays default OFF pending this pass.
- **What CI cannot exercise:** the actual visual overlay — whether the aimpoint triangles/threat rings/runway markers sit ON the imagery features in a rendered page (the imagery itself is fetched live from Esri, which CI never touches).
- **Setup:** any Caucasus or GermanyCW campaign (the offset-heavy maps) with `generate_target_recon_kneeboard` ON and network up. Plan a Strike package + open the generated deck's recon pages: the airbase page, a target detail page, and the corridor overview.
- **Pass:** on the detail page the aimpoint markers sit on the target buildings/revetments in the imagery (within a marker-width, not hundreds of meters off); the airbase page's runway/threshold markers lie on the imaged runway; on the overview the route/threat rings track the imaged coastline/terrain rather than floating a few pixels off mid-page; a no-network run still degrades to the OFFLINE banner fallback.
- **Fail signature:** detail-page markers still displaced by a consistent regional shift (offset_near returned None or picked junk — log `airport_imagery`; check the terrain JSON has measured `imagery_offset_deg` entries near the target); mid-page-only drift on the overview with corners fine (the mesh didn't engage — `_mesh_cell_count` span read); a visible seam/discontinuity at mesh cell boundaries (cell corner projection mismatch — should be impossible since shared corners project identically; if seen, check PIL MESH box rounding); pages crash/blank on a terrain without an imagery JSON (must degrade to no offset, not fail). · §26 · ☑ VERIFIED (2026-06-28, audience in-game pass — user "good, I think"; off-mission auto-resolve looked right, not deeply scrutinized)
- **Headless adjudication (2026-06-26):** `tests/test_combat_resolution_capability.py` covers the
  scoring (A2A strength = best A2A `task_priority` × count; win = strength share; survivor loss scales
  with margin, clamped ≤ legacy 0.5; SAM death halved for SEAD, stacked by site count, clamped). 39
  combat/sim regression tests stay green. **Residual (in-sim only):** that auto-resolved attrition over
  several turns *reads* believably.
- **Setup:** Auto-plan a few turns with **combat resolution = Resolve** (or Skip) so AI-vs-AI
  engagements auto-resolve; watch the losses on both sides over the turns.
- **Pass:** modern fighters beat obsolete ones more often than not; numbers still tell (a pair can
  beat a lone jet); a SEAD/SEAD-capable flight survives SAMs better than a striker; no side wins or
  loses every single time.
- **Fail signature:** outcomes feel random (elite jets routinely lost to obsolete ones), or one side
  always wins; SEAD no better off than a bomber against SAMs.

### J2 — "Player at IP" fast-forward spawns at the IP · §26 · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — spawns at the IP
- **Headless adjudication (2026-06-26):** `tests/test_player_at_ip_fast_forward.py` covers the gate
  (AI-only combat does not pause a PLAYER_AT_IP fast-forward; a player-involving combat still does;
  other stop conditions / `force_continue` unchanged). **Residual (in-sim only):** the actual spawn
  position after a real fast-forward.
- **Setup:** Fast-forward stop condition = **"Player at IP"**, combat resolution = **default (Pause)**,
  a **ground-started** (Cold/Hot/Runway) player flight with an IP. Generate the mission.
- **Pass:** the player spawns **airborne at/near their IP**, not on the ramp, even with AI fights
  happening elsewhere; if the player's *own* flight is engaged en route the sim still pauses there.
- **Fail signature:** player spawns at their configured ground start (the bug returns); or the sim
  never stops / the player ends up far past the IP.

### J3 — Per-group C-130J EW de-confliction (JAMMING + SOF/King coexist) · §2 / §15 · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — EW jet + SOF/King C-130J coexist; non-EW C-130J has no EW menu
- **Headless adjudication (2026-06-26):** `tests/missiongenerator/test_ew_deconfliction.py` covers
  `_ew_excluded_c130j_groups` (only `SOF`/`COMBAT_SAR` C-130J-30 group names, not the JAMMING jet or
  non-C-130J helos) and the `c130j` plugin wiring (reads `dcsRetribution.EwExcludedGroups`,
  `isEligible` rejects an excluded group). **Residual (in-sim only):** the runtime attach decision.
  Supersedes the old mission-wide skip verified under F3.
- **Setup:** Frag **both** a JAMMING C-130J-30 **and** a SOF-insert or Combat SAR King C-130J-30 in
  the **same** mission (the case the old whole-plugin skip broke). Generate and fly/inspect.
- **Pass:** the JAMMING jet keeps its full `c130j` EW/ISR menu; the SOF/King C-130J flies **clean**
  (no EW menu). With no SOF/King fragged, every C-130J-30 still gets EW (unchanged baseline).
- **Fail signature:** the JAMMING jet loses its EW menu when a SOF/King is present (the old
  mission-wide skip regressed); the SOF/King wears the EW menu (deny-list not applied / group-name
  mismatch); or a Lua error in the `c130j` `isEligible` path.

### K1 — Settings IA reorg + difficulty presets · §28 · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass
- **Headless adjudication (2026-06-27):** `tests/settings/test_field_layout.py` locks the reorg
  (FIELD_LAYOUT covers every user field exactly once, the UI walk emits each once, the six pages are
  in the designed order, no section > 13 settings) and `tests/settings/test_difficultypreset.py`
  locks the engine (Normal == Settings defaults, apply→detect round-trips for all four presets,
  unrelated fields untouched, presets mutually distinct). An **offscreen Qt build** confirmed the full
  `QSettingsWidget` constructs with all six pages, the preset bar tops Difficulty & Realism, and
  applying Ace flips labels→Off / invuln→False / enemy_skill→Excellent with the "Current:" label
  tracking. **Residual (UI eyeball only):** the visual feel / readability in the running app.
- **Setup:** Open **Settings** in a campaign and the **New Game** wizard's options page.
- **Pass:** Six content pages — **Difficulty & Realism / Air Doctrine / Campaign Management /
  Mission Generation / Kneeboards / Performance** — each with focused sections (no 30-item wall);
  every page has its icon. The **Difficulty preset** bar tops Difficulty & Realism; clicking
  **Casual / Normal / Veteran / Ace** updates the controls below and the "Current: …" readout;
  hand-editing a control afterward still works; **Normal** restores stock values. No setting is
  missing from the dialog.
- **Fail signature:** a setting absent from every page (FIELD_LAYOUT gap — should be impossible,
  test-locked); a page/section empty or mis-ordered; the preset bar missing or not refreshing the
  controls; a preset not flipping the expected fields; a blank page icon; a console error opening
  the dialog.
- **Second IA pass (2026-07-05), re-opens the UI-eyeball leg for the wizard.** The New Game wizard
  audit moved the world-shaping generator options onto the **Theater** page ("Forces & Budget" group,
  re-seeded per campaign on select) and made the old Generator page a grouped **Mods** page; plus the
  legacy sweep (Vietnam card text, "Advanced IADS (MANTIS)", sorted time periods with a named default,
  `Default.zip` subtitle, `SettingNames.py` deleted, OH-6 relabel) and the section regroup ("Campaign
  features" + "Commander economy" on Campaign Management, "Battlefield life" on Mission Generation,
  the Air Doctrine threat wall split into 4 sections). All walk-verified headless (7 pages, 174
  fields) + the wizard files compile. **In-app re-check:** run the wizard end-to-end — the Theater
  page shows and re-seeds Forces & Budget when switching campaigns (e.g. Red Tide 800/400), the Mods
  page reads in its three groups, a generated game honors the checkboxes/budgets exactly as before
  (`accept()` reads the same field names), the Vietnam card lists the right campaigns, and the time
  preset defaults to Mid-90s Summer. **Fail:** a wizard field silently unregistered (game generates
  with defaults — budgets ignored is the tell), the Theater page overflowing at 1080p, campaign
  switching not re-seeding the group, or the settings dialog missing any of the new sections.

### K2 — Campaign SITREP band on its own kneeboard page · §29 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, surface moved TWICE; the cover-page host it was ☑ VERIFIED on 2026-06-28 is retired. **Title corrected 2026-08-06** — this row still said "on the Mission Info page", which was true only between 2026-07-13 and 2026-07-19; the band then moved again to its **own "SITREP — Turn N" page after Support Info**, because a flown busy-turn deck clipped the POW/MIA list at the page edge. Look for the standalone page, not a block on Mission Info
- **History:** the SITREP band shipped on the briefing page, moved to the §30 cover page (where this
  row was VERIFIED 2026-06-28 — numbers across turns OK, "Kneeboards look fantastic"), and returned
  to the **bottom of the Mission Info page** when the 2026-07-13 back-to-upstream rework retired the
  cover. The model/capture/gating are unchanged; only the render surface moved, so the residual is
  the new placement's in-cockpit read.
- **Headless adjudication (2026-06-27, re-valid 2026-07-13):** `tests/test_sitrep.py` covers the
  SITREP model + formatting (side split, captured/lost by side, Combat SAR count, "claimed" enemy
  phrasing, singular/plural) and `sitrep_for_kneeboard` gating (off / no prior turn / quiet turn);
  `tests/missiongenerator/test_kneeboard_index.py` covers the generator's `_briefing_sitrep` gate.
  `record_sitrep` is wired into `commit()` (asserted in `COMMIT_STEPS`).
- **Setup:** Generate a mission (and fly a turn so turn 2 has a prior-turn SITREP); open the Mission
  Info kneeboard page.
- **Pass:** a **"SITREP — Turn N-1"** section renders at the bottom of Mission Info from turn 2 on
  (friendly + enemy-claimed losses, bases captured/lost, pilots recovered, matching the previous
  turn), fitting under the laser-code table. **Turn 1 / a quiet turn / toggle off** → no SITREP
  section.
- **Fail signature:** SITREP present on turn 1 or after a quiet turn (gating wrong); numbers not
  matching the debrief; enemy losses not "claimed"; the section clipped off the page bottom on a
  long flight plan; a stale SITREP from two turns ago (capture not running each `commit`).

### K3 — UI audit follow-up: settings greying + web map discoverability/legend · §28 audit · ☑ VERIFIED

**History:** built 2026-07-10

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — VERIFIED on the user's call ("K3 good").**
- **Headless adjudication (2026-07-10):** `tests/test_settings_dependencies.py` locks the greying
  engine — every `enabled_when` master is a real setting, all ~21 pairs verified same-page/same-section
  (so the live refresh fires), and offscreen-Qt tests prove a child control + label grey on open and
  un-grey live when the master toggles, including the inverse `default_front_line_stance ←
  (automate_front_line_stance, False)` pair. The web half (palette tokens, legend, right-click hints)
  is jest-covered for render (all 12 suites green) but its look/interaction is client-runtime only.
  **Residual (UI eyeball only):** the in-app feel of both halves.
- **Setup:** Open **Settings** in a campaign (Qt), then the web map on a campaign with enemy TGOs, a
  front line, and enemy supply routes (Red Tide works).
- **Pass:** *Qt:* children grey with their masters (e.g. the four `red_intent_*` knobs grey until
  **Red intent** is ticked; **Default front stance** greys while automation is ON) and come back live;
  long setting details read as one summary line with the full text on hover. *Web:* the bottom-right
  **Legend** button expands to the colour key and doesn't block map clicks under it; the concealed
  "suspected activity" circle reads **amber** (dashed red = ROE only); front lines / enemy supply
  routes show a pointer cursor + a hover hint naming the right-click action, and right-click still
  frags the package (front line) / interdiction (enemy route); a friendly route offers no
  interdiction hint; a user-placed TGO's tooltip says right-click **removes** it (and it does).
- **Fail signature:** a child stuck greyed after its master is enabled (or greyed on the wrong
  master); a truncated detail with no hover full-text; the legend swatches disagreeing with the
  drawn overlay colours (token drift); the invisible front-line/route hit-band swallowing
  left-clicks meant for markers under it; a right-click hint shown where the action 404s.

### L1 — Arc Light heavy-bomber Strike carpet · §32 · ☑ VERIFIED

**History:** 2026-06-28, audience in-game pass — user: "good"
- **In-game (2026-06-28, audience pass — user verdict "good"):** the Arc Light carpet works — a heavy bomber's STRIKE walks a carpet of explosions across the target box at the run-in, no Lua error and no reported FPS hit. Power/density read acceptable to the user (no tuning requested).
- **Default retune 2026-07-01 (imperial-unit options):** release range moved **8 → 3 NM** (`arcLightReleaseNm`)
  so the carpet lands with the bomber nearly overhead (matching the ~2.5–3 NM ballistic forward throw from
  ~30k ft) instead of firing a full minute early; carpet defaults re-expressed as 6,000×1,500 ft / 660 lb
  (≈ the verified 1700×500 m / 300 kg). Mechanics unchanged — the VERIFIED verdict stands; just note the
  carpet now appears later on the run-in.
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the Python
  emitter — only a heavy-bomber (`HEAVY_BOMBER_DCS_IDS`) `STRIKE` produces an `arcLight` record, the
  toggle off emits no `VietnamOps` node, and a non-bomber Strike emits no record. The carpet itself
  (`resources/plugins/vietnamops/vietnamops-config.lua`) is Lua and can only be exercised in a live mission.
- **Setup:** A campaign with the **Vietnam Ops → Arc Light** setting **on** and a **B-52 STRIKE** fragged
  against a ground target (e.g. Khe Sanh with `vietnam_arc_light: true`). Watch the B-52 run in.
- **Pass:** As the B-52 closes inside the release range (~8 NM) of its target, a **walking carpet** of
  explosions marches across the target box, oriented along the run-in, with a coalition "ARC LIGHT inbound"
  message. Ground units in the box take damage (flows to debrief). A B-52 shot down *before* the run-in
  fires **no** carpet. A non-bomber (F-4/A-4) Strike behaves normally (single aimpoint). `dcs.log` clean.
- **Fail signature:** no carpet despite a healthy B-52 reaching the target; carpet fires for a tactical
  striker; carpet on a dead/destroyed bomber; explosions stacked at one point (no walk / bad heading);
  `land.getHeight`/`explosion` Lua error in `dcs.log`; FPS hit from over-dense impacts (tune
  `arcLightBlastPower`/length/width down).

### L2 — AAA flak gauntlet · §33 · ☑ VERIFIED

**History:** 2026-07-01 flown Yankee Station session `intelligent-dubinsky`, user pass: bursts "light but fairer" after the 2nd softening — the too-accurate/lethal fail signature did not recur; player death that mission was a MiG gun kill, not flak. If it now reads *too* light, raise `flakPower`/narrow the miss band
- **Second softening applied 2026-07-01 (L2 tuning owed from the 2026-06-28 pass).** The lethality that
  remained was the close **"tracking" round firing every 2.5 s tick** once a jet held a steady line for ~10 s
  (`factor > 0.8`), reading as a hard-kill rather than pressure. Changes (`vietnamops-config.lua` + matched
  `plugin.json` defaults): base misses **widened** `MIN_MISS` 110→**150** m / `MAX_MISS` 250→**320** m; the
  tracking round is now **occasional not constant** — gated behind a sustained steady run (`factor > 0.85`,
  was 0.8) **and** a per-tick probability (`TRACKING_CHANCE = 0.3`), and softened (`miss ×0.55→×0.75`,
  `blast ×2.0→×1.5`). Net: a predictable line now draws bursts ~90–210 m (was ~66–154 m) with only the
  *occasional* ~85–160 m close round instead of one every tick; jinking stays loose. `BLAST` unchanged (6).
  Lua syntax gate + `plugin.json` parse green. **Re-fly owed** to confirm the feel is right (pressure to
  manoeuvre, no hard-kill) — this is why the row stays PARTIAL.
- **⚠️ Config-mismatch finding (2026-06-30, `dcs.log`):** the flown session's plugin options were
  **`ceiling 5000m, power 8`** — but the *current* `plugin.json` defaults (post-2026-06-28 softening,
  confirmed by reading `vietnamops-config.lua` + `plugin.json` today) are `flakCeilingM=4500` /
  `flakBlastPower=6`. `power=8` is the exact **pre-softening** value (`BLAST 8→6`); `ceiling=5000` was
  never a documented value either way. This means this session's flak lethality was **not** exercised
  against the current softened tuning — either this `.miz`'s plugin options are a stale campaign-side
  override that predates the 2026-06-28 fix, or someone deliberately dialed it back up. Blue took heavy
  losses this session (whole 3-ship BLOODHOUND Strike A-6E flight, whole 3-ship Kutaisi BARCAP A-4E
  flight, both TARPS RF-101Bs, several SCAR/CAS helos — 29 `crash_events` total), which is *consistent*
  with an over-tuned flak gauntlet but wasn't isolated from SAM/MiG kills (scripted `explosion()` calls
  don't leave a Tacview object or a per-burst log line, so per-kill attribution needs deeper Tacview
  geometry work this pass didn't do). **Before re-flying this row:** check the campaign's saved Vietnam
  Ops plugin options (or regenerate) and confirm `flakBlastPower`/`flakCeilingM` are actually reading
  the current 6/4500 defaults, not a stale 8/5000. **RESOLVED BY THE 2026-07-01 IMPERIAL RENAME:** the
  flak options are now `flakRangeNm`/`flakCeilingFt`/`flakMinMissFt`/`flakMaxMissFt`/`flakBurstPower`
  (2.5 NM / 15,000 ft / 500 ft / 1,000 ft / 6) — the old metric keys are ignored, so every campaign
  re-seeds the softened defaults and the stale-`8/5000` mismatch can't recur. Re-fly on the new defaults.
- **In-game (2026-06-28, audience pass — user: "too accurate but working very well"):** the gauntlet mechanic is confirmed working (AAA discovery, engagement geometry, predictability ramp all behave) — but the bursts land **too close / kill too reliably**, reading more like a hard-kill threat than the intended mostly-visual pressure. The lethal lever is the close **"tracking" round** (`flakBurst`: `miss = MIN_MISS*0.35` ≈ 24 m at `blast = BLAST*2.5` = 20, fired once `factor > 0.66`) on top of the tight `MIN_MISS = 70` floor. **Tuning APPLIED 2026-06-28 (recommended softening):** `MIN_MISS` 70→**110** m, tracking round `miss ×0.35→×0.55` + `blast ×2.5→×2.0` and rarer (`factor > 0.66→0.8`), `BLAST` 8→**6** — in both `vietnamops-config.lua` and the `plugin.json` defaults (`flakMinMissM` 70→110, `flakBlastPower` 8→6). Net: predictable bursts ~42–98 m@8 → ~66–154 m@6; the close tracking puff ~15–34 m@20 → ~36–85 m@12. **Re-fly owed** to confirm the feel is right (still pressure, no hard-kill).
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the on-marker
  emission (flak node only when the setting is on, independent of Arc Light). The flak itself — AAA discovery
  by attribute, the engagement geometry, and the predictability ramp — is runtime Lua, exercisable only live.
- **Setup:** A campaign with **Vietnam Ops → AAA flak gauntlet** on and enemy **AAA guns** (ZSU/Shilka/airfield
  guns) near a target. Fly through their range below ~4500 m AGL: first a steady, predictable run, then jinking.
- **Pass:** Flying within range/below ceiling draws **barrage flak bursts** around the aircraft. A **steady**
  heading+altitude **tightens** them (and a sustained steady run draws the occasional close round); **jinking /
  changing altitude widens** them. Out of range / on the deck (<120 m) / above the ceiling → no flak. Both
  sides' AAA behave symmetrically. `dcs.log` clean; no FPS collapse.
- **Fail signature:** no flak despite flying over live AAA in range; flak with **no** AAA nearby; flak that
  ignores predictability (always tight or always loose); flak so dense/lethal it reads as a hidden SAM
  (dial `flakBlastPower` / miss / range down); `getVelocity`/`hasAttribute`/`explosion` Lua error in
  `dcs.log`; FPS hit on a dense mission.

### L3 — Naval gunfire support · §34 · ☑ VERIFIED

**History:** 2026-07-04, user pass — "L3 good") (was ☐ UNTESTED: emitter test-covered; both runtime modes are Lua, need a cockpit pass. 2026-07-02 Trail 2 session `wonderful-chatterjee`: armed cleanly — 2 BLUE gun ships, auto on, zero errors — but the carriers' escorts sat 40+ NM offshore, no red ground within the 10 NM gun range and no player F10 fire mission called, so **zero ship gun events**: the coastal-by-construction no-op behaved correctly, the firing legs remain unflown. To exercise it, drop an F10 mark on coastal red within ~10 NM of an escort
- **Inconclusive session (2026-06-30, Tacview):** `dcs.log` confirms the emitter armed 2 blue
  gun ships (`Naval gunfire armed (2/0 gun ship(s) blue/red, range 20000m, ...)`) — 2× VWV
  `DE-1052 USS Knox` escorting a carrier strike group. But scanning every `Projectile+Shell` object in
  the Tacview ACMI (34k+ shell events) found **no naval-caliber shell type** (only tank/AAA-caliber
  ammo like `M68_105_HE`, `KS19_100HE`, etc. — nothing matching the Knox's 5" mount), and the ship
  group's recorded position is well offshore of the active front (Kutaisi/Senaki-Kolkhi, well inland).
  That's consistent with the documented **"coastal only by construction"** limitation (no enemy ground
  in the ships' 20 km range ⇒ nothing fires) rather than a bug — but it means this row **still wasn't
  actually exercised**. To close it out: fly (or auto-plan) a campaign whose front sits within ~20 km
  of the coast, or manually reposition a gun ship group near enemy ground and either wait for the auto
  cadence or use **radio → Naval Fire Mission → Fire on last F10 map marker**.
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the gun-ship
  emission (CRUISER/DESTROYER/FRIGATE incl. the New Jersey, carrier excluded, coalition carried; off /
  no-gun-ship = no node). The F10 menu, marker read, ship/target selection, and `TaskFireAtPoint` are runtime
  Lua, exercisable only live.
- **Setup:** A **coastal** campaign with **Vietnam Ops → Naval gunfire** on and a friendly **gun ship**
  (New Jersey / cruiser / destroyer) offshore within ~20 km of enemy coastal ground. Place an F10 map marker
  on a coastal target and use **radio menu → Naval Fire Mission → Fire on last F10 map marker**. Also just
  wait for the automatic bombardment.
- **Pass:** The F10 call lands shells on the marker from the nearest in-range ship (with a "SHOT" message);
  out of range gives "no gun ship in range." With auto on, ships periodically shell the nearest in-range
  enemy coastal ground without input. **Inland** missions (no ship in range) produce **no** fire. `dcs.log`
  clean.
- **Fail signature:** F10 menu absent despite an owned gun ship; marker call does nothing / errors; ship
  fires far inland (range gate wrong); auto bombardment never fires or fires every tick (cadence wrong);
  `TaskFireAtPoint`/`getMarkPanels`/`missionCommands` Lua error in `dcs.log`; an escort wandering off station.

### L4 — Vietnam compressed-theater support-orbit standoff · PR #314 · ✖ REMOVED

**History:** (2026-08-09) — the front-anchored standoff this row measured was reverted to upstream's target-anchor placement (planner re-convergence work order D). The campaign's buffer preseeds still apply, but they now step off the nearest threat boundary rather than setting a depth behind the FLOT, so the "~40–50 miles behind the front" figure below no longer predicts where the orbit lands. Re-read on a live Vietnam turn if the standoff matters. (Was ☑ VERIFIED

**History:** 2026-07-01 before the revert.)
- **Verified (2026-07-01, user in-app map read):** the AEW&C/tanker orbit reads "fine" on the planner map —
  sits ~**40–50 miles** (≈65–80 km) behind the front, matching the headless calc (83/74 km at the 25/20 NM
  buffer) and clear of the map edge. The fail signature (orbit ~150 km back / flung to the edge) did not
  occur — the PR #314 tightening is confirmed applied on a live campaign.
- **⚠️ Tuning question (user, 2026-07-01): "40–50 miles seems pretty long."** This is the tightened value
  *working as designed* — but the user still finds it far for a compressed Vietnam theater. If we want it
  closer, the lever is the per-campaign `aewc_threat_buffer` / `tanker_threat_buffer` (currently 25/20 NM);
  dropping them further pulls the orbit in, at the cost of less standoff from forward threats. **Not a bug —
  a balance call.** Left VERIFIED (the fix works); a follow-up buffer-tune is optional. NB the orbit also
  carries a racetrack half-length on top of the buffer, so the *near* end sits closer than the buffer figure
  alone.
- **Headless adjudication:** `game/ato/flightplans/supportorbit.py::support_orbit_anchor` on the live Khe Sanh
  save: at 25/20 NM the AEW&C/tanker orbit sits **83/74 km** behind the front (vs 148 km at the old 60 NM),
  still 37-46 km clear of the threat. Guard test `tests/test_vietnam_content.py::test_vietnam_campaign_tightens_support_orbits`
  pins the 3 campaign values + the untouched 80/70 defaults.
- **Setup:** Start a **NEW** Khe Sanh / Yankee Station / Velvet Thunder game (existing saves bake the old
  buffer in) and auto-plan a turn.
- **Pass:** On the planner map the AEW&C and tanker racetracks hug the front (~75-90 km back), not flung to
  the map edge; their escorts no longer sprawl across the theater. Large (non-Vietnam) campaigns are unchanged.
- **Fail signature:** orbits still ~150 km back / at the map edge; a tanker sitting inside a SAM ring (buffer
  too low); the buffer not applied (check Air Doctrine page shows 25/20 after campaign-select).

### L7 — Right-click supply-route interdiction · §35 · ☑ VERIFIED

**History:** 2026-07-04, user pass — "L7 good") (was ☐ UNTESTED after 2026-07-01: "still nothing" root-caused to a STALE LOCAL CLIENT BUILD, not a code bug — client rebuilt, needs a re-test
- **2026-07-01 — "still nothing" is a build problem, not the feature.** The user right-clicked an enemy
  supply route and nothing happened (same as the prior session). Root cause confirmed: the local checkout's
  `client/build/static/js/main.9ba023ba.js` was dated **June 23** and contained **zero** occurrences of
  `create-package/supply-route` — i.e. the compiled client predates the feature (merged in #349/#351). The
  **source** on `main` is correct (`SupplyRoute.tsx` `contextmenu` → `useOpenNewSupplyRoutePackageDialogMutation`;
  the hook + endpoint in `_liberationApi.ts`), it was just never compiled into what the user runs
  (`run_retribution.bat` serves the local `client/build`, not a CI build). **Fix applied 2026-07-01:** rebuilt
  the client (`cd client && CI=false npm run build`) → new bundle `main.c050b70d.js` **does** contain the
  endpoint; the stale bundle is replaced. **Re-test after restarting the app** (or run the fresh `latest`
  release, which ships a CI-built client). This is the same stale-`client/build` trap as the
  [[local-client-rebuild-for-react-features]] memory — any React feature needs a client rebuild the local run
  won't do automatically.
- **Headless adjudication (unchanged):** the server resolution is test-covered
  (`tests/server/test_supply_route_interdiction.py`); only the React `contextmenu` → Qt dialog path needs the
  in-app pass — now unblocked by the rebuild.
- **Headless adjudication:** `interdiction_target_for_route_id` is unit-tested
  (`tests/server/test_supply_route_interdiction.py` — resolves the `"<cp_a_id>:<cp_b_id>"` route id to the
  enemy end, prefers the contested CP, returns None for a friendly/malformed route). The **client
  right-click → `POST /qt/create-package/supply-route/{id}` → Qt package dialog** path is React/Qt and can't
  be exercised headless.
- **Setup:** Load any campaign with a visible enemy supply route (enable the Supply Routes map layer). The
  visible line is thin and sent to the back, so the route carries a **wide invisible hit-line** — right-click
  anywhere along the coloured line. **Must be a build that includes this change** (the client is rebuilt by
  CI on merge; a stale `client/build` won't have the handler).
- **Pass:** right-clicking an **enemy** supply route opens the new-package dialog targeting the road's enemy
  end, with the add-flight dialog auto-opened and **Armed Recon pre-selected** — pick aircraft and it frags.
  Right-clicking a fully-**friendly** route does nothing (server 404, no dialog).
- **Fail signature:** right-click does nothing on an enemy route (the hand-added
  `useOpenNewSupplyRoutePackageDialogMutation` hook or the `contextmenu` handler is wrong); a JS error in the
  client console; the dialog opens on the wrong CP. Needs the CI client rebuild (hand-edited generated API).

### L8 — Airbase harassment (rocket/mortar siege) · §36 · ✅ CLOSED (feature removed 2026-09-16) (was ✗ REGRESSED

**Removed on the DM's call the same day the test-34 read below landed.** The barrage grounded
every AI fixed-wing launch at the field it shelled; the two settings, the plugin options, the
emitter, the Lua block and the preseeds are gone. Nothing to fly. The paragraphs below are the
evidence, kept.

**2026-09-16, test 34** (Caucasus — 1968 Yankee Station turn 1 on the halved laydown, 62 min, no player, `Tacview-20260916-204511`, DCS 2.9.29.27468) — **the barrage freezes every AI fixed-wing launch at the field it lands on, for the rest of the mission.** Harassment armed for 8 fields, Maykop-Khanskaya and Sochi-Adler among them (the Vietnam siege reach is theatre-wide, and with no player nothing was excluded). At Maykop the Phantom pair that activated at t=341 taxied and flew; CATFISH BAI (t=1334), ALBATROSS Strike (three B-52s, t=1385), ALBATROSS Escort (t=1466) and PUFFIN Strike (t=1733) activated hot and never moved a metre in the 33–40 minutes left. At Sochi-Adler the two groups activated before t=200 flew and the two after (ANTELOPE BAI at t=553, the OV-10 CAS at t=727) sat. Mineralnye Vody and Krymsk, not in the list, launched everything (t=653, 1280, 1295, 1599). The first barrage lands at grace 300 s plus 120–360 s, which is exactly where the taxiing stops. Nothing else was on either ramp: with the recording's axes read correctly, Maykop's only object inside 2.5 km is the field's own static soldier 1.5 km off and Sochi-Adler's are a convoy and depot statics 1–1.5 km off, and no weapon object landed at either (the barrage leaves none, as this row already notes). Test 35 (Long Road to H3, 2026-09-16) is the one mixed reading: at harassed Tabqa the L-39 pair activated at t=424 sat, but the Flogger pair at t=605 flew, inside the first-barrage window; Aleppo's t=474 pair flew too. The same shape holds in every earlier mission with harassment armed: test 33 (Damascus harassed: the H-6J strike at t=1369 and the CAS at t=2680 sat, while Tiyas launched flights at t=5064), test 24 (Batumi harassed: both F-15C BARCAPs at t=1080 and 1136 sat, Tbilisi's t=72–319 flights got out before the grace) and test 31 (Anapa harassed: the t=629 package sat, the t=161–168 ones flew). Helicopters at harassed fields still lift (Gudauta's Mi-8 BAI at t=924, test 34): they need no taxi clearance, which points at DCS holding ground traffic on a field under attack and the four-minute cadence never letting it clear. Ten fixed-wing groups across four missions, zero counter-examples. This is the feature's cost, not its cue: on Yankee Station it grounds the Ubon wing and the Da Nang wing after the first ten minutes. Fix is a design call (shell only fields with no planned fixed-wing departures, or make the barrage visual), not made in this read.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the generic artillery mode armed in many captures, the Vietnam siege in none.** `Airbase harassment armed for N field(s)` appears on tests 1–33 wherever a front was inside the reach (Iron Gate, Inherent Resolve with 4 fields, Afghanistan, Hornet's Nest); the impacts leave no Tacview object, so the visual confirm this row has owed since July is still owed. No Vietnam campaign was flown. Unchanged.

**History:** 2026-07-01 flown Yankee Station session `intelligent-dubinsky`: armed for 4 fields, user saw the "Incoming — standoff fire on …" cue in-mission → the barrage loop fires past the grace period; the impacts themselves + the player-spawn-field exclusion not yet visually confirmed. 2026-07-02 Trail 2 session `wonderful-chatterjee`: armed for 3 red fields (Sukhumi/Gudauta/Senaki) with all 5 blue player fields excluded in the emitted data, zero errors across a 90-min mission — the Python-side exclusion held by construction; the visual impact confirm still owed
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the emitter — a
  forward, occupied airfield/FARP is emitted; a rear / neutral / carrier / off / no-front field yields no node;
  a **lone client-spawn field yields no node** and a client-spawn field alongside an enemy field is excluded
  from the targets but listed under `excludedFields`. The scheduled per-field loop, the grace period, the
  randomized cadence, and the `trigger.action.explosion` placement are runtime Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Airbase harassment** on and a forward, **AI-occupied**
  enemy airfield/FARP within ~200 km of the front (Da Nang / Khe Sanh laydowns qualify). Fly (or fast-forward)
  past the startup grace period (default 5 min) and watch the enemy ramp.
- **Pass:** After the grace period, small dispersed explosion barrages land near the enemy field's parking area
  on a sporadic cadence, with an "Incoming — standoff fire on <field>" cue to the owning side. **Your own spawn
  field(s) are never touched.** `dcs.log` shows "Airbase harassment armed for N field(s)" and no Lua errors.
- **Fail signature (the #1 watch-item): ANY impact on or near a client-spawn field** — the anti-grief guarantee
  is broken. Also: fire during the grace window; a steady metronome instead of a sporadic cadence; impacts
  wildly off the ramp (centroid/dispersion wrong); too lethal to parked jets (dial power/dispersion down, as
  §33 flak needed); a `trigger.action.explosion` / `land.getHeight` / `timer.scheduleFunction` Lua error.
- **Generic artillery mode (added 2026-07-05, needs its own pass):** the new `artillery_base_harassment`
  setting drives this same emitter+runtime with the tight `ARTILLERY_FRONT_REACH_M` (35 km) — **Red Tide
  preseeds it**, so on a NEW Red Tide game the **Fulda forward FARP** and red's **Haina** (both on the
  Fulda↔Haina front) should draw sporadic artillery harassment after the grace, while Ramstein/Spangdahlem/
  Hahn (100+ km back) stay silent. **Pass:** fire only on the frontline fields; a player cold-starting at
  Fulda is NEVER shelled (the spawn exclusion — cold-start there to prove it); the emitted `fields` list in
  the mission Lua holds only front-adjacent fields. **Fail:** a rear field shelled (the 35 km reach not
  applied — check the Vietnam toggle isn't also on, which widens the reach by design); any impact on a
  player-spawn field; harassment on a campaign with the setting off. Tests:
  `tests/missiongenerator/test_vietnamops_harassment.py`.
  **2026-07-10 flown Red Tide turn 1 (session `gallant-panini-5485e7`): found silent no-op BY GEOMETRY →
  FIXED, needs a re-fly.** The generated miz carried `VietnamOps = {}` — nothing emitted — because the
  turn-1 Fulda↔Haina front sits at the route midpoint, putting **Fulda ~39.3 km and Haina ~39.6 km from the
  FLOT, both ~4 km past the old 35 km `ARTILLERY_FRONT_REACH_M`** (distances read off the emitted QRA-zone
  radii: grown radius − 25 NM). Fix (user call: make it tunable + bump Red Tide): the reach is now a
  campaign-tunable setting **`artillery_harassment_reach_km`** (default 35, unchanged for every other
  campaign; `enabled_when=artillery_base_harassment`), and **Red Tide preseeds 42 km** so both fields fall
  inside from turn 1 (WP BM-27 Uragan MRLs reach ~35 km, so ~42 km is period-honest). Emitter reads
  `settings.artillery_harassment_reach_km * 1000` for the generic mode; the Vietnam siege keeps its
  theater-wide reach. Guard `test_artillery_reach_is_campaign_tunable`. **Re-fly pass:** on a NEW Red Tide
  game, Fulda + Haina both draw harassment after the grace; a player cold-starting at Fulda is still never
  shelled (spawn exclusion); Ramstein/Spangdahlem/Hahn (100+ km back) stay silent.
  **2026-07-11 flown Red Tide M1 (`csar-snatch-toggle-question-dfdb7a`): the 42 km reach emitted; the
  spawn exclusion held by construction.** Load log `Vietnam Ops - Airbase harassment armed for 1 field(s)
  (every ~240s, 5 rounds, dispersion 259m, power 8, grace 300s)` — the 1 field is **Haina** (red);
  **Fulda AND Frankfurt were this mission's client-spawn fields**, so both landed in `excludedFields`
  (confirmed in the emitted miz node), and the intended "shell both Fulda and Haina" correctly collapses
  to Haina-only whenever players base at Fulda — the anti-grief rule doing its job, not a reach failure.
  Zero Lua errors across ~125 min. Still owed: eyes on the **Haina ramp** for the actual impacts/cadence
  (the visual confirm this row has owed since `intelligent-dubinsky`) — note `trigger.action.explosion`
  barrages leave no Tacview objects, so this can only be observed live (or via the "Incoming" cue on red's
  side, which no human can see on Red Tide).

### L10 — FAC(A) willie-pete target marking · §38 · ☑ VERIFIED

**History:** 2026-07-02 flown Trail 2 session `wonderful-chatterjee` — user confirmed the named FAC(A) F10 map mark appeared at the target; the mark is unambiguously the plugin's, since the Bronco's own WP rockets make no F10 mark. Armed cleanly in `dcs.log`, zero Lua errors; the OV-10s worked the front ~23 min before being shot down at t=1382. Earlier ambiguity from `intelligent-dubinsky` — smoke that might have been the AI's own rockets — resolved by the 2026-07-02 findability pass's named mark
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the `fac` on-marker
  (emitted when `vietnam_fac_marking` is on, independent of the other suite features; off = no node). The
  runtime OV-10 discovery, the nearest-enemy scan, and `trigger.action.smoke` placement are runtime Lua,
  exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → FAC(A) marking** on and a friendly **OV-10 Bronco**
  airborne over the front within ~3 NM of enemy ground (the campaigns field OV-10 CAS squadrons). Fly near a
  Bronco working the battle area and watch for the smoke.
- **Pass:** the Bronco periodically drops **white** smoke on the largest enemy ground concentration in range
  **and** a named **F10 map mark** appears there (e.g. "FAC(A): BTR-60 x6 — willie pete, cleared hot"), with a
  "FAC: … marked — see F10, cleared hot" cue to its coalition; `dcs.log` shows "FAC(A) marking armed". The F10
  mark refreshes as the FAC re-marks and is the tell that distinguishes the feature from the Bronco's own WP
  rockets (rockets leave no map mark).
- **Fail signature:** smoke lands on friendlies or empty ground (wrong side / no nearest-enemy gate); no smoke
  despite an OV-10 over enemy ground (type-name mismatch — confirm `Bronco-OV-10A` is the mod's DCS type, or
  set `facType`); wrong smoke colour; a `trigger.action.smoke` / `land.getHeight` / `getTypeName` Lua error;
  the mark cadence is far too frequent (smoke spam) or never fires.

### M1 — Political will pacing & feed weights (campaign layer W1+W2) · §48 · ✖ REMOVED

**History:** (2026-07-21) — the political-will economy was dropped (the campaign-economies drop); no pass owed.

### M2 — Static front holds the band (campaign layer W2b) · Vietnam campaign layer · ✖ REMOVED

**History:** 2026-07-21) — the static-front layer was dropped with the will economy; no pass owed. (Was ☑ VERIFIED 2026-07-04 before removal.

### M3 — Campaign phase arc & planner emphasis · §40 · ✖ REMOVED

**History:** (2026-07-21) — the campaign-phase feature was dropped (the ROE-mechanic drop); no pass owed.

### M4 — ROE escalation arc (zones, target release, will coupling) · §40 · ✖ REMOVED

**History:** (2026-07-21) — the ROE escalation layer was dropped; no pass owed.

### M5 — GCI-ambush MiGs: late scramble, one slash, home (campaign layer W5) · §1 · ☑ VERIFIED

**History:** 2026-07-02 flown Trail 2 session `wonderful-chatterjee` — the 40 NM late-launch trigger measured in Tacview: Sukhumi 4-ship scrambled with the nearest BLUE at **37.6 NM**, Senaki 4-ship at **31.5 NM**, both inside the 40 NM cap; slash + leash already VERIFIED 2026-07-01 `intelligent-dubinsky`
- **Verified (2026-07-02, flown multiplayer session `wonderful-chatterjee` — `Tacview-20260702-171945-…-Trail 2`):**
  both red GCI scrambles launched **late**, exactly per the W5 design: the Sukhumi ambush 4-ship spawned at
  t=460 s with the nearest BLUE aircraft (the front-line TARCAP F-4E) **37.6 NM** from the field; the
  Senaki 4-ship at t=1150 s with the nearest BLUE (HIPPO Escort F-8E) **31.5 NM** out — no launch at the
  100 NM setting border. All 8 MiG-17Fs fought close (37mm gun events in `dcs.log`, no BVR) and were
  progressively lost t=1064–3594 — the posture works; MiG survivability is a balance observation, not a
  mechanism failure. No `intercept-config.lua` errors.
- **Partial (2026-07-01, flown session — Tacview `Tacview-20260701-225522-…retribution_nextturn` + `dcs.log`):**
  a red `Intercept|Sukhumi-Babushara|…` MiG-17F pair launched at t≈460 s, ran a **close** intercept into the
  Gudauta fight (~25 NM from its base), and **gunned down the player's F-4E** (Flash, Gudauta Armed Recon) at
  ~1,150 m with the MiG inside ~1–2 km — a slashing merge, no BVR duel. The lead was traded (killed by a GAR-8
  at t≈876 s); the survivor **broke off** after the fight, climbed to ~4,500 m and egressed SE toward home
  plate — no chase-to-map-edge, no fight-to-destruction, no `intercept-config.lua` error in `dcs.log`. The
  leash behaviour (one slash, disengage, RTB at altitude) is exactly the W5 design. **Not yet measured:** the
  40 NM late-scramble trigger (couldn't reconstruct which raid the dispatcher launched against, so the launch
  radius is unconfirmed) and blue-side parity.
- **Headless adjudication:** `Doctrine.gci_ambush` (Vietnam-only), the `dispatcher_tuning` radii math
  (engage → 22 NM cap range, scramble capped at 40 NM, tighter settings still win), the `ambushPosture`
  record serialization, and the W4 sanctuary-basing fallout (an airfield inside a zone can't be OCA'd) are
  all locked in tests. What CI *cannot* adjudicate: the actual Moose defender behaviour under the leash
  (`SetDisengageRadius` 50 NM + fuel threshold 0.35).
- **Setup:** a NEW Vietnam campaign; fly a BLUE strike package toward a red QRA field (with the Rolling
  Thunder sanctuary active, the MiG base itself is un-OCA-able — the classic problem). Watch `dcs.log` /
  the F10 map for the red scramble.
- **Pass:** MiGs scramble **late** (raid inside ~40 NM of the field, not at the 100 NM border), run a
  **close** intercept (engage ≤ ~22 NM — a slashing merge, not a BVR duel), **break off** rather than chase
  beyond ~50 NM from their base, and RTB early on fuel — the raid gets hit once, hard, and the MiGs live to
  ambush again next mission; blue QRA (same doctrine) behaves alike; a modern campaign's QRA is byte-for-byte
  unchanged (settings pass through).
- **Fail signature:** MiGs still launch at the full setting radius (tuning not reaching the record — check
  `dispatcher_tuning` wiring / `ambushPosture` in the generated `dcsRetribution.Intercept`); defenders chase
  to the map edge or fight to destruction (leash not applied — the records[1] read or the
  `SetDisengageRadius`/`SetDefaultFuelThreshold` calls); no scramble at all (backstop/detection regression —
  unrelated to W5, see A2); a Lua error in `intercept-config.lua` (the `AMBUSH_*` locals are file-scope,
  defined before build_dispatcher — verify load order if edited). Knobs: `AMBUSH_GCI_RADIUS_NM`
  (interceptluadata.py), `AMBUSH_DISENGAGE_NM` / `AMBUSH_FUEL_THRESHOLD` (intercept-config.lua).

### M7 — ROE zone shapes (box/corridor F10/ME map + from_drawing) · §40 · ✖ REMOVED

**History:** (2026-07-21) — the ROE-zone layer was dropped; no pass owed.

### M8 — COIN positive-control valleys (no-strike ROE) · §40 · ✖ REMOVED

**History:** 2026-07-21) — the ROE-zone layer was dropped; no pass owed. (Was ☑ VERIFIED 2026-07-04 before removal.

### M9 — Commitment ceiling: will-coupled war budget draws down · §48 · ✖ REMOVED

**History:** (2026-07-21) — the commitment ceiling was dropped with the will economy; no pass owed.

### N1 — High Digit SAMs Ultimate Compilation units in-game · §41 · ☑ VERIFIED

**History:** 2026-07-04, user pass — "n1 good") (was ☐ UNTESTED, built 2026-07-01; unit data read from the installed mod, factions/presets/layouts headless-verified
- **Headless adjudication:** every new unit name resolves, all presets/layouts load, and all 25+ touched
  factions parse and strip correctly with the toggle both ways (the id-correct `remove_vehicle` fix verified
  headless). What CI *cannot* adjudicate is DCS itself accepting the unit type ids at spawn and the runtime
  behavior of the new sites.
- **Setup:** the Ultimate Compilation (v1.4.3+) installed; a NEW campaign vs. a modern Russia faction
  (russia_2020 / redfor_current) with the "High Digit SAMs - Ultimate Compilation" toggle ON. For the period
  layer, a Vietnam campaign with the toggle ON (the P-37 Bar Lock EWR; for SA-7 launches use a 70s
  Middle-East red like syria_1973 — the Vietnam factions deliberately carry no SA-7).
- **Pass:** S-400 / S-300V4 / SAMP-T / S-300PT sites generate and the mission loads without a "unit type not
  found" DCS error; their threat rings render at the new ranges; MANTIS resolves them into the IADS (the
  "resolved N/M SAM" dcs.log line counts them) and they engage at standoff; Pantsir-SM fills SHORAD slots;
  SA-7 infantry actually launch (syria_1973 etc.); the P-37 feeds MANTIS EWR detection on period red factions; insurgent
  ZU-23 technicals spawn at AAA sites.
- **Fail signature:** DCS refuses the mission / silently drops a group (a type-id typo — cross-check the id
  against the mod's `entry.lua` unit list); MANTIS logs "Could not match radar data" AND the site never
  wakes (the banding override failed — check `dcsRetribution.RedAA` emits the group); a 40N6E site
  dominates a small map absurdly (keep the `SA-21/S-400` preset out of small campaigns); SA-7 teams never
  fire (manpad class/attribute mismatch).

### P2 — Long-range carrier ops: the boat joins the war · §44 · ☑ VERIFIED

**History:** 2026-07-04, user pass — "p2 good") (was ☐ UNTESTED, built 2026-07-03; the deterministic package is engine-probe verified on the real COIN save — Hornet Strike x2 + A-6E Refueling + E-2C AEW&C off the boat, valid flight plans + shared TOT, plus the commander flying spare Hornets on SEAD — the played feel needs a campaign
- **Headless probe:** on the user's 2026-07-03 Enduring Resolve save, `plan_carrier_strike` fragged
  `PKG → target = F/A-18C Strike x2 + A-6E Refueling x1 + E-2C AEW&C x1`, all departing the carrier, with valid
  flight plans (13/5/7 waypoints) and a shared TOT; the range-gate preseed (`max_mission_range_planes: 600`)
  made the carrier air assignable so the commander also flew spare Hornets on SEAD. What CI cannot exercise is
  the **in-mission behaviour** — the A-6 actually giving gas on ingress/egress/recovery and the E-2 holding a
  useful AEWC orbit at that standoff.
- **Buddy-tanker routing (added 2026-07-03):** the commander's carrier SEAD Sweep/Escort Hornets used to get a
  refuel waypoint ~560 km from the A-6 (a dry tank). `route_carrier_flights_to_buddy_tanker` now pins them onto
  the A-6 orbit — probe-verified on the same save: both carrier SEAD Hornets' REFUEL waypoints moved from ~560 km
  away to 0 km from the A-6 orbit center, land-based flights untouched. In-mission tanking still needs a fly.
- **Setup:** NEW campaign "Afghanistan - Operation Enduring Resolve (COIN)" (`long_range_carrier_ops` preseeds
  on). Generate turn 1 and inspect the ATO / fly the carrier package.
- **Pass:** exactly one carrier strike package appears each turn — a Hornet strike section off the boat onto an
  enemy target (a cache when one is legal), with the A-6E tanking the package (launch join + egress/recovery)
  and the E-2 airborne on station; the land air still fights the rest of the war and spare Hornets show up on
  SEAD. The Hornets reach the target and RTB to the boat with the A-6's help, **and the carrier SEAD Hornets
  tank from that same A-6** (their refuel point is on the A-6 orbit, not up-range dry).
- **Fail signature:** carrier still idle (range preseed didn't take / `long_range_carrier_ops` off — check the
  campaign `settings:` block survived); Hornets launch but the A-6/E-2 don't (they pruned — confirm they are
  primary flights, not refuel escorts); two carrier packages a turn (the `_already_planned_from` guard broke);
  the package fragged into a population ring (ROE filter bypassed); Hornets can't make it home (TOT/fuel math
  off at the 400-500 NM standoff — the tanker orbit isn't being used).

### O2 — Downed-pilot map overlays: both coalitions, the fog, and the countdown · CSAR · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, adopted 2026-08-07. Upstream ships blue and red overlays; the fork wired them into its own §19 grouped layers panel rather than upstream's inline list, so the integration seam is fork-specific and unflown
- **What CI cannot exercise:** whether the markers render at all through the fork's §19 panel, whether the blue and red rows toggle independently, whether the countdown in the tooltip is actionable, and — the interesting one — whether an **enemy** downed pilot is visible to the player at all. The fork runs a viewer-aware fog layer (§3) that hides enemy assets; upstream's CSAR predates any knowledge of it, so a red survivor may simply bypass the fog and hand the player free intel about where enemy aircraft went down.
- **Setup:** a campaign with survivors on **both** sides (`csar_enabled_red` defaults ON). Open the map, find the layers panel, toggle both downed-pilot rows, hover a marker. ~20 min, no flying.
- **Pass:** blue survivors render and toggle; red survivors render and toggle independently; the tooltip countdown matches the SITREP and the actual expiry turn; the rows survive a layer-preset switch.
- **Fail signature:** no markers at all despite survivors existing (the overlay is orphaned — it was, before 2026-08-07, because taking the fork's side of the map conflict left upstream's layer unrendered); the red row missing; the countdown off by one against the SITREP, which makes every rescue-planning decision wrong; enemy survivors visible with fog on, which is a **fog leak** and needs a call on whether it is wanted.

### Q2 — Default loadout for an airframe+task, and the payload-tab cleanup · §73 · ☑ VERIFIED

**History:** 2026-08-05, user app pass `pr-merge-code-audit-7e8b4c` — "Q1 and Q2 are good") (was ☐ UNTESTED, built 2026-07-19; name resolution + the file writer/remover are fully unit-tested, the buttons and the read-the-screen changes are Qt UI
- **Headless adjudication:** `tests/retlab/test_loadout_defaults.py` drives the real pydcs
  airframes with the scratch dir registered as pydcs's *preferred* payload directory and the repo's
  `customized_payloads` behind it — the production arrangement — and pins the end-to-end claim:
  saving an override makes `Loadout.default_for_task_and_aircraft` return it, clearing hands the slot
  back to the shipped fit. Also pinned: the resolved name always equals what the task resolves to, a
  re-save replaces rather than duplicates, clearing leaves a hand-made payload in the same file
  alone, a new entry never lands on a live key, an unparseable file is left byte-identical, and the
  first write backs the file up. What CI can't exercise is the buttons and whether the screen now
  reads correctly.
- **Setup (defaults):** open a flight's **Edit flight → Payload** tab, tick *Use custom loadout*, build
  a loadout, then click **Set as default for &lt;task&gt;** and accept the confirm. Plan a *new* package
  with a flight of the **same airframe and task** and open its Payload tab.
- **Pass:** the new flight opens carrying the saved loadout. **Clear default** on any flight of that
  airframe+task returns new flights to the stock fit. The confirm dialog names the payload it will
  write (e.g. `Retribution CAS`).
- **Fail signature:** the new flight still gets the stock fit (the override missed the resolved name
  — check what `override_name_for` returned against the payload actually loaded), or **other saved
  payloads for that airframe disappear** from the loadout dropdown (the writer clobbered the file
  instead of editing one entry — the backup is in `UnitPayloads/_retribution_backups`).
- **Also eyeball (same-pass cleanups):** on a loadout with **no laser-guided weapon and no pod** (e.g.
  an F-4E on Snakeyes + Rockeyes) the *Assigned TGP laser code* and *Preset laser code for weapons*
  rows should be **absent**; on the stock F-4E CAS fit (Pave Spike + GBU-12) they should be
  **present**. With *Use custom loadout* ticked the Loadout box should read `(customised)` beside the
  preset name. The fuel spinner should match the internal figure in the fuel-plan line below it
  (they disagreed by ~2 lb). Hovering a truncated store name should show the full name. Stepping the
  **Flight member** spinner across members must not silently replace a member's custom loadout. The
  window title should name the flight.

### Q1 — Per-aircraft flight defaults save + apply · §43 · ☑ VERIFIED

**History:** 2026-08-05, user app pass `pr-merge-code-audit-7e8b4c` — "Q1 and Q2 are good") (was ☐ UNTESTED, built 2026-07-02; store/apply fully unit-tested, the button + the "new flight opens pre-configured" behaviour is Qt UI
- **Headless adjudication:** the store round-trips (save → reload from disk), `apply_flight_defaults` seeds
  fuel + `member.properties` for a BLUE fresh flight, skips RED, no-ops with no saved entry, clamps fuel to
  the airframe tank, and stays silent when persistency isn't set up — all in
  `tests/retlab/test_flight_defaults.py`. What CI can't exercise is the Qt button and the "the box opens
  already set the way I want" experience.
- **Setup:** any campaign; open a flight's **Edit flight → Payload** tab. Change Internal Fuel (e.g. to 80%),
  Aircraft Condition, Wear & Tear, and/or Spawn Type; click **Save as default**. Then create a *new* package
  with a flight of the **same airframe** and open its Payload tab.
- **Also eyeball (2026-07-06 layout cleanup):** the tab now reads as grouped sections — *Flight members* /
  *Aircraft settings* (laser codes + properties scrolling, fuel + defaults pinned below) / a labeled
  *Loadout:* row + the pylon editor. The property list should no longer cut off mid-row on a normal window.
  The bold AI-loadout warning appears only while "Use same loadout for all flight members" is unchecked. On
  an **AI-crewed** flight (e.g. an AI F-4E escort) the *Aircraft settings* box should be **compact** — its
  aircraft-property list is player-only so it renders empty, and the box no longer leaves a big blank gap
  between the laser rows and the fuel slider (2026-07-06 follow-up 1). The **weapons loadout at the bottom
  must show all/most pylons, not be crushed into a few** — the pylon list is a natural full-height grid (no
  inner scroll), so the dialog opens tall enough to show every station (2026-07-06 follow-up 2, after a
  player F-16 came up showing only ~5 of 12). Offscreen-instantiation smoke passed headlessly (AI F-4E
  settings-box h=66 vs player F-4E h=288; F-16 lays out all 12 pylons); the visual proportions are the
  in-app question.
- **Pass:** the new flight's Payload tab already shows the saved fuel + property values (no re-entry); **Clear
  default** is enabled once a default exists and, after clicking it, a further new flight of that airframe is
  back to stock values; the store lives at `Saved Games\Retribution\flight_defaults.json` and survives an app
  restart / a New Game; a *different* airframe is unaffected; enemy (RED) flights are never altered.
- **Fail signature:** new flights still open at stock fuel/condition (apply not firing — confirm the flight is
  BLUE and freshly created, not a clone; check `flight_defaults.json` wrote); a saved sub-full fuel default
  never appears (fuel stored in kg — a unit mixup would show a clamped-to-max value); a crash on flight
  creation (the apply path must be a silent no-op on any error — it is wrapped, so a stack trace means the
  guard was bypassed); RED flights changing (the `coalition.player.is_blue` gate failed).

### Q3 — Bulk waypoint altitude moves every flown leg · §4 (flight altitude editing) · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-08 on upstream review of dcs-retribution#920, which reported that "Apply to all" left the CAS FLOT boundaries alone. The filter rule — deck stays, altitude moves — and the AGL/MSL normalisation are unit-tested in `tests/test_bulk_waypoint_altitude.py`; what is left is an **app pass**, not a flight, because the change is entirely in the Edit Flight dialog
- **Pass:** open Edit Flight → Waypoints on a **CAS** flight, set 20,000 ft, *Apply to all*. FLOT start
  and FLOT end move with the rest of the route and their Alt Type column reads **MSL**. Repeat on a
  **helicopter** flight and on a Vietnam **low-level** CAS/BAI flight, where the button previously did
  nothing at all: every leg moves, and at or below 5,000 ft the column stays **AGL**. On any flight with a
  tanker leg, the refuel waypoint moves too. On any flight, takeoff, landing, target and bullseye rows stay
  at 0. On an air-assault or CSAR helo, the pickup/dropoff/CSAR rows keep their approach altitude.
- **Fail signature:** the FLOT rows still read the old altitude (the filter did not take); a route that comes
  out half AGL and half MSL (normalisation skipped a leg — the Alt Type column is read-only, so this is
  unrecoverable in-app and the flight is at two real altitudes); an LZ row jumping to cruise (a landing zone
  fell out of `BULK_ALTITUDE_SKIP_TYPES`); the spin box accepting 0 ft; a target row leaving 0 ft.

### R1 — Support-package F10 orbit markers render + labelled · §45 · ☑ VERIFIED

**History:** 2026-07-04, user pass — "looks great" on COIN; NOT COIN-only — `generate_support_orbits` is called unconditionally in `DrawingsGenerator.generate`, gated only on blue REFUELING/AEWC flights existing, so every campaign with a blue tanker/AWACS gets the markers) (was ☐ UNTESTED, built 2026-07-03; the emitter — racetrack-end pick, blue/support filter, group-name label match, oblong/circle draw — is locked in `tests/missiongenerator/test_support_orbit_drawings.py` and a real `.miz` `drawings.dict()` serialize probe passed; the on-map render needs an in-cockpit eyeball
- **Headless adjudication:** `generate_support_orbits` draws a labelled racetrack for a blue `REFUELING`/`AEWC`
  flight, skips non-support + RED + `mission_data=None`, and the label carries callsign/type/freq/TACAN (AWACS
  without TACAN drops it) — all in `tests/missiongenerator/test_support_orbit_drawings.py`. A probe confirmed
  the `add_oblong` capsule + `add_text_box` serialize into the `.miz` drawings table. What CI *cannot*
  adjudicate: whether DCS renders the racetrack + label on the F10 map and whether it sits over the actual
  tanker/AWACS orbit.
- **Setup:** any campaign with a blue tanker and/or AWACS package; generate the mission, then open the `.miz`
  in the ME (or fly it and open the F10 map).
- **Pass:** each blue tanker/AWACS shows a cyan dashed **racetrack** at its orbit with a **label** reading
  `<callsign>  <type>` over `<freq>  TCN <tacan>` (AWACS shows no TCN); the racetrack sits where the flight
  actually orbits; no marker for enemy or non-support flights.
- **Fail signature:** no markers at all (the flight-plan has no `PATROL_TRACK`/`PATROL` pair, or `mission_data`
  wasn't threaded into `DrawingsGenerator` — check `missiongenerator.py`); a marker in the wrong place (the
  racetrack-end waypoint pick); a blank/partial label (the `group_name` match to `TankerInfo`/`AwacsInfo`
  failed — freq/TACAN come from there, not `FlightData`); a red tanker marked (the `friendly.is_blue` gate).
  Knobs: `TANKER_ORBIT_LINE`/`AEWC_ORBIT_LINE`/`CAP_ORBIT_LINE`/`SUPPORT_LABEL_*` (drawingsgenerator.py).
  The look changed 2026-10-06 (outline only, colour per job): B185 owns that pass.

### S1 — Route-aware fuel-tank planning (fuel-first) · §46 · ✅ CLOSED (feature reverted 2026-08-09) (was ◐ PARTIAL

**History:** (original gen-time top-up ☑ VERIFIED 2026-07-04, user pass — "S1 good I think", tentative; the **2026-07-12 fuel-first rework** — tank-aware tanker decision + the plan-time jammer-pod trade — is ☐ UNTESTED and needs its own pass))
> ⛔ **CLOSED 2026-08-09 — the feature was reverted, so there is nothing left to fly.**
> §46 reverted outright to upstream behavior as work order C of the auto-planner
> re-convergence (`docs/dev/design/retlab-autoplanner-upstream-divergence-audit.md`, DECIDED
> block). Tanker tasking is upstream's again and no code fits tanks. The text below is the
> record of what was built and what was adjudicated; **do not open a pass against it.**

- **Headless adjudication (original top-up):** `top_up_for_route` fills an empty tank station on a far route,
  is a no-op on a short route / empty / custom loadout / setting-off, and **never removes or replaces an
  existing store** (asserted on the Hornet pylon tables). A before/after script showed the COIN Hornet Strike
  going 2→3 tanks on the empty centerline with zero swaps, the Hornet BAI staying 1 tank (no empty station,
  Mavericks untouched), and the short route unchanged.
- **Headless adjudication (2026-07-12 fuel-first rework):** the pre/post-vul tanker decision now counts
  external-tank fuel, `plan_sortie_fuel` fits tanks at plan time (empties first, then the JAMMER-typed pod on
  a tank-capable station when the extra bag strictly saves a tanker pass — or on any shortfall when no tanker
  exists), custom loadouts/shared-object members/idempotence all pinned in
  `tests/retlab/test_range_fuel.py` + the Viper BOTH→POST_VUL end-to-end in
  ~~`tests/ato/flightplans/test_fuel_first_tanking.py`~~. What CI *cannot* adjudicate: whether the AI actually
  flies the single planned pass sensibly in-sim, whether the drag-free burn model leaves enough margin on a
  three-bag jet, and how often the pod trade fires across real campaigns (it should be the exception, not the
  norm).
- **Setup:** a campaign whose strike/SEAD legs outrun internal fuel with a tanker in theater (Red Tide or the
  COIN campaigns); plan a turn, open a SEAD/Strike F-16 package with `auto_range_fuel_tanks` +
  `fuel_tanks_over_jammers` ON (defaults).
- **Pass:** a Viper that used to plan pre+post-vul refueling now shows **3 bags** (centerline tank in the
  payload editor, ALQ-184 gone) and only **one** REFUEL waypoint (or none); its HARMs/AMRAAMs are untouched;
  the kneeboard flight plan's fuel column/RTB margin reads consistent with the bags (no "-short, tank or
  divert" on a sortie the bags cover); a jet whose extra bag would NOT save a pass keeps its jammer; a
  hand-edited (custom) loadout is never touched.
- **In-APP pass (the §46 fuel-plan readout, no DCS needed):** open Edit flight → Payload on any planned
  jet — a "Fuel plan: burns ~X · carries Y (… internal + N tanks …) · N tanker pass(es) · RTB margin ±Z"
  line sits under the fuel slider; drag the fuel slider down / clear a bag pylon and watch the margin fall
  (amber + "short of getting home" when negative); switch members and loadouts and it follows; "(estimated)"
  shows on airframes with no measured fuel block. Fail signature: the line contradicting the kneeboard
  ladder for the same flight (they share the walk — a divergence means the loadout/fuel inputs differ), a
  frozen line after a pylon edit (the `pylon_changed` hook), or a huge phantom burn (the walk failed to stop
  at the landing point and priced the bullseye leg).
- **Fail signature:** a pod traded with no pass saved (the pass-count gate broken); ordnance/TGP/decoy missing
  (the JAMMER-type filter broken — only `type: JAMMER` yaml pods may ever be displaced); a jet with bags still
  planned through two refuel passes (`flight_external_fuel_lbs` not reaching the decision); the fuel ladder
  contradicting the tanker plan (waypointgenerator's external-fuel term); tanks piling up across plan rebuilds
  (idempotence broken). Knobs: `auto_range_fuel_tanks`, `fuel_tanks_over_jammers` (Mission Generation →
  Loadouts).

### S3 — Friendly convoy ambush (a chance, never telegraphed) · §50 · ⊘ RETIRED (removed 2026-10-11, DM: stripped)

**2026-10-11 — REMOVED on the DM's call.** The seeding, the trigger generator and the setting are deleted, so this row can never be run again. The spring was never seen to fire in any flown test: the DM flies with **Disable land convoys** ticked, and the two flights that had a convoy were blocked by S5.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **not reached.** The trigger was armed (`Convoy ambush 1`, radius 6 km, on `Convoy 001`, blue), and the team (`0093 | KANGAROO`, Tigr-M and AK infantry) stood 69 m from the zone centre. The column drove 51 km and was still 23.5 km from the zone at mission end.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the native triggers are authored and the spring is still blocked by S5.** `Convoy ambush N` zones exist in four captures (test 8: 3, test 17: 4, tests 19 and 20: 1 each). On test 17 both blue columns the teams were keyed to never moved (S5), so nothing could enter a zone. Unchanged until S5 is fixed.

**History:** 2026-07-06 flown Inherent Resolve session `jovial-gates-574c9c`: the whole chain up to the spring VERIFIED — but the spring itself was blocked by the S5 parked-blue-convoy bug
- **2026-07-11 flown Red Tide M1 (`csar-snatch-toggle-question-dfdb7a`): quiet mission — inconclusive
  by design.** The blue column (`Convoy 001`, M-113/VAB ×6) drove its full 61 km corridor untouched and
  no "TROOPS IN CONTACT" cue fired; with the 50 % per-convoy roll (and the ≤4-team theater cap) a quiet
  run is an expected outcome, so this neither passes nor fails the row. The light-raider-kit + cap
  re-fly criteria from the 2026-07-09 tuning still stand.
- **Tuned 2026-07-09 (flown Red Tide test — "excessive, and should be light not MBTs"):** the ambush teams spawned as **front-line armor (MBT groups)** and **too many** (a 2-convoy turn maxed to 12 teams). Two fixes: (1) the teams now use a **light raider kit** (`coin.ambush_unit_types` — an armed gun-truck + riflemen from the faction's own roster, `CELL_SIDC` infantry symbol) instead of `GroupTask.FRONT_LINE` armor; (2) `MAX_AMBUSHES_PER_ROUTE` 6→3 **plus** a theater-wide `MAX_TOTAL_AMBUSHES` (4) so several convoys losing the roll on one turn can never swarm the backline. Tests in `test_convoy_ambush.py` + `test_coin_units.py`.
- **Pass (still owed):** an ambush springs with "TROOPS IN CONTACT" and the contact is a handful of **light** vehicles/infantry (not a tank platoon); the theater never shows more than ~4 hidden teams; and the spring fires once a convoy actually reaches it (blocked before by S5).
- **⚠ THE SPRING IS NOW NATIVE DCS TRIGGERS, NOT A PLUGIN (2026-08-05 — re-read before flying).** The `convoyambush` plugin is deleted; `ConvoyAmbushGenerator` authors a hidden 6 km trigger zone on each ambush point plus a `TriggerOnce` (`TimeAfter` 120 s **AND** `PartOfGroupInZone(<that convoy's group>, zone)`) that raises a per-ambush user flag, and each team carries flag-gated `ControlledTask`s flipping it to alarm-red/weapons-free. **There is no `CONVOYAMBUSH|` log line any more** — do not read its absence as the feature being off. Verify instead by opening the generated miz in the ME: the ambush triggers are visible under Triggers (named "Convoy ambush N") with their zones. **The one DCS-only unknown this introduces:** whether DCS honours a **start condition on an ROE/alarm *option*** (a `ControlledTask` wrapping a `WrappedAction`). The serialized structure is correct and the mirror-image `stop_if_user_flag` is flown daily by the escort split, but the start form on an option is unproven here. **Fail signature specific to it:** the "TROOPS IN CONTACT" cue and the F10 mark appear on schedule (so the trigger fired) **but the team never actually shoots** — that isolates the failure to the option's start condition, and the fallback is to author the team's dug-in state as `GroupAIOff` at start and flip it with the native `GroupAIOn` trigger action instead. If the cue never appears either, the trigger/zone/condition is what to look at, not the ROE.
- **2026-07-06 flown evidence (dcs.log + miz + Tacview):** `CONVOYAMBUSH|: armed 2 ambush(es)`, and the miz
  carries the exact pairing — hidden teams `0104 | OKAPI` (4× tt_KORD, 17.7 km up the Baghdad→Balad corridor)
  and `0105 | WALRUS` (4× tt_DSHK, 46 km up) both keyed to blue `Convoy 003`, a genuine 2-contact gauntlet on
  the real highway. **The hiding contract held in the flown mission:** both teams sat alive, silent, and
  never fired for 52 minutes (alarm-green dug-in, nothing telegraphed — the player flew the whole session
  unaware, which is the design). **The spring never fired because the convoy never drove** (see S5 — blue
  `Convoy 003` sat parked at its Baghdad spawn all mission, so nothing ever entered the 6 km trigger). The
  S3 fly re-runs for free once S5's parked-column bug is fixed.
- **Build/rework history (2026-07-05/06):** the ambush is a per-convoy chance roll seeding 1..6 fully map-hidden teams along the route, the escort auto-frag is DELETED, and a team its convoy never reaches stays silent; the blue convoy top-up, the chance roll + gauntlet placement, the `map_hidden` contract (client/SSE/planner) + every guard are in `tests/retlab/test_convoy_ambush.py`, the emit shape/gates in ~~`tests/missiongenerator/test_convoyambushluadata.py`~~, and the plugin's grace/spring-on-close/silent-without-convoy/dead-team/no-node in ~~`tests/lua/test_convoyambush_runtime.py`~~ — the actual firefight and the spring feel need a mission. **2026-07-05 flown attempt (session `practical-germain`, pre-merge Shattered Dagger COIN save): NOT a pass of the mechanic** — the save predated the preseeds so the feature was correctly gated off (adjudicated from dcs.log + the flown miz + a headless save load: no node, no plugin line, clean no-op) — but it EXPOSED the blue→blue-road prerequisite gap: both COIN campaigns shipped all-red supply graphs, so even a new game could never field the escort convoy. Fixed same day: geo-authored blue rear corridors (ER Kandahar↔Bastion; IR Baghdad↔Balad + Baghdad↔Al-Taquddum) + the `test_preseeded_campaigns_have_a_blue_to_blue_road` CI guard.
- **What CI cannot exercise:** whether the DCS ground AI ambush actually engages the passing convoy and grinds it down; whether the spring reads as an ambush (fires when the column is close, not at max range); whether a multi-team roll reads as a gauntlet of separate contacts down the road; whether flying to the TIC call and clearing a team actually saves the rest of the column; and whether convoy losses + ambush losses both land in the debrief.
- **Setup:** any road-bearing campaign (the `ROAD_BEARING_CAMPAIGNS` inventory in `tests/retlab/test_convoy_ambush.py` — since the 2026-07-06 standardization both `convoy_ambush` and `ambient_supply_convoys` default ON for a **NEW game**; the flagship four — COIN Enduring/Inherent Resolve, 1968 Yankee Station, Red Tide — additionally preseed the `convoyambush` plugin ON over any saved-off default). Advance a turn; on the F10 map find a friendly convoy moving between two blue bases (it looks like any other convoy — there is deliberately NO ambush marker and NO escort package in the ATO). Fly anything, and decide on the TIC call whether to divert. May take a few turns to catch a hit roll (~50 % per convoy; `dcs.log` "CONVOYAMBUSH|: armed N ambush(es)" > 0 confirms a live one without spoiling positions).
- **Pass:** the convoy drives its road; NOTHING about the ambush shows anywhere beforehand (no map marker, no uncertainty circle, no ATO package, no F10 mark); when the column closes on a hidden team, it springs (a "TROOPS IN CONTACT" cue + an F10 mark at the fight) and engages; on a multi-team roll the column is hit again further down the road; diverting air onto the mark and killing the team lets the convoy drive on, ignoring the call grinds it down (fewer/no units delivered); the debrief records the dead convoy units (never arrive) AND the dead ambushers (real red ground loss); some turns the road is simply quiet ("armed 0 ambush(es)" / no node).
- **Fail signature:** no friendly convoy ever appears (blue corridor/road missing — check the campaign has a blue→blue `supply_routes` road and `ambient_supply_convoys` is on); an ambush team is visible on the campaign map / web map / F10 before it springs, or a "suspected activity" circle appears on the road (the map_hidden contract broken — check `TgoJs.all_in_game`, the SSE filter in `GameUpdateEventsJs.from_events`, and `triggergenerator._gen_markers`); a BAI package targeting the ambush appears in the ATO (the `BattlePositions` skip broken); a team fires at max range the instant the mission loads (grace/spring broken); a TIC cue with no convoy anywhere near (the removed max-hold fallback resurrected, or trigger radius huge); every convoy every turn is ambushed (the chance roll broken); a `CONVOYAMBUSH|: setup error` in dcs.log; ambushers or convoy losses missing from the debrief (a phantom-spawn regression — both must be real, tracked units).

### S4 — Enemy comms jamming: capture the intel, then the C2 belt steps on the radios · §51 · ⊘ RETIRED

**⚠️ Re-scope needed (2026-08-21 audit) — the capture half of this row no longer exists.**
`comms_jam_requires_capture`, the `combatsar` plugin, `combat_sar_captures` and
`Coalition.pending_pow_recoveries` all went with §21 on 2026-08-07. `plan_comms_jam` now gates
on `enemy_comms_jamming` + a live comms/command-center node + at least one briefed blue
frequency, and nothing else. Fly only the jamming half: bursts arrive on briefed channels, the
JAM BACKUP is clean, and killing the node silences it. Drop every criterion below that starts
with a capture. Whether the gate should come back on upstream #929's POW ledger is an open
decision **and it was decided on 2026-08-21: the jamming stays unconditional.** The orphan
`captureReactionS` plugin option went with that call; `coalition.py`'s `pending_pow_recoveries`
save drop stays, because that pop IS the cleanup for old saves.

**REMOVED 2026-09-07** — §51 was abandoned; the plugin, the setting, the JAM BACKUP line and both campaign preseeds are deleted, so this row can never be run.

**History:** 2026-07-11 flown Red Tide M1 `csar-snatch-toggle-question-dfdb7a`: the dormant leg observed — `COMMSJAM|: intel gate armed -- 18 C2 jammer(s), 3 channel(s), dormant until an aircrew capture` at load, radios stayed clean all ~125 min with zero captures, no Lua errors. Correct behavior, but silence-while-dormant can't distinguish "correctly gated" from "broken and silent", so the status stays UNTESTED until a capture→jam moment is heard — use the `[TEST] force capture` toggle. Built 2026-07-06, intel gate added same day; the plan ordering / GUARD filter / cap / backup collision re-roll / intel-gate flags / emit shape are in `tests/missiongenerator/test_commsjamluadata.py`, and the plugin's grace / burst-stop-rotation / dead-jammer silence (both death paths) / ceased cue / intel-gate dormancy + live-capture + POW-story + watch-bail / no-node no-op in `tests/lua/test_commsjam_runtime.py` — whether the static is audible on a tuned radio, the falloff feel, the capture→jam moment, and the kill-to-silence loop need a mission

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — PARTIAL ("S4 did something", user).** `red_comms_net` was on and the red net emitted, but the channel was not sat on long enough to call it. Needs a deliberate listen on a briefed channel inside the C2 belt.
- **What CI cannot exercise:** whether `trigger.action.radioTransmission` static is actually audible on a cockpit radio tuned to a jammed channel (and through SRS, which tunes off the cockpit); whether the power falloff reads (loud near the C2 belt, faint near home plate); whether the duty cycle pressures but never fully denies coordination; whether the live capture→compromise→jamming sequence lands dramatically (the real combatsar plugin appending `combat_sar_captures` mid-mission — the harness fakes it); and whether killing the comms node silences it with the "ceased" cue.
- **Setup:** Red Tide, **NEW game** (`enemy_comms_jamming` + the `commsjam` plugin preseeded ON; the intel gate `comms_jam_requires_capture` defaults ON). Note the JAM BACKUP line on the Mission Info kneeboard page (BLUF, next to the code words). **Intel-gate leg:** with no POW held, fly with clean radios; get a pilot ejected + captured (lose the Combat SAR race). **POW leg:** advance the turn with the POW still held and fly the next mission. **Ambient leg (optional):** untick the intel gate and confirm the v1 always-on behavior. **Fast test (thumb on the scale):** tick `[TEST] Combat SAR: force every downed pilot to be captured` (Campaign Management → HQ Automation) so any ejection near the front is seized in seconds → guaranteed POW; advance the turn and the next mission opens jammed (or hear it same-mission after the exploitation delay). To just hear jamming with no capture at all, untick the intel gate.
- **Pass:** radios stay clean while no capture has happened (dormant, `dcs.log` "COMMSJAM|: intel gate armed … dormant until an aircrew capture"); on a capture, an "AIRCREW CAPTURED — assume the comms plan is compromised" cue fires and static bursts begin ~2 min later (the exploitation delay) on the briefed intra-flight/AWACS channels (worse closer to red's C2 belt); with a POW held, the NEXT mission opens with the "COMMS COMPROMISED: enemy interrogation of captured aircrew" cue and jams from the grace; freeing the POW (or the 4-turn clock expiring) returns clean missions; GUARD 243.0, ATC and the JAM BACKUP channel always stay clean; switching to the backup escapes the noise; striking the emitting comms mast/command bunker stops the bursts and (once all emitted nodes are dead) cues "comms jamming has ceased".
- **Fail signature:** jamming before any capture with the intel gate on (`captureOnly` flag not emitted/read); no jamming ever after a confirmed capture (the `combat_sar_captures` global name/shape drifted between the combatsar and commsjam plugins — check both, and that a CombatSAR node was emitted at all: no blue rescue helo = no capture race); the POW leg opens clean (`pending_pow_recoveries` not read — check `plan_comms_jam`); no static ever plays on a jammed channel (sound file missing from the miz — check `commsjam-noise.wav` landed in `l10n/DEFAULT`, or radioTransmission Hz/modulation wrong); static on GUARD/ATC/the backup (the Python positive-list broken); continuous unbroken noise on every channel at once (duty cycle/rotation broken — check `burstSec`/`intervalSec`/`maxFreqsPerBurst` plugin options); jamming continues after the node is confirmed destroyed (death detection — the static `" object"` suffix or the `dead_events` ledger path); a `COMMSJAM|: setup error` in dcs.log; bursts before the startup grace.

### S5 — Ambient supply convoys: both sides' roads have randomized traffic · §50 · ☑ VERIFIED (2026-09-23, tests 37 and 39; was ◐ PARTIAL)

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **both sides drive, on a second map.** Turn 1: `Convoy 001` (blue) 51 km and `Convoy 002` (red) 49.5 km; turn 2 plans one column a side again. The red column's loss reached the debrief (`Convoy 002 Unit #5` in `dead_events` and `kill_events`). With test 37's four columns on Syria, the parked-column signature from tests 17, 28 and 31 has not reproduced since the distinct-road change.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **both columns drove.** `Convoy 001` (blue: HIMARS, Stryker ATGM, MaxxPro) 51 km; `Convoy 002` (red: Tunguska, BTR-80, BMD-4, Smerch) 49.5 km, one vehicle lost to a HARM at t=2934. TIC was off.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **all four columns drove.** Off the recording: red `Convoy 001` 23–24 km, `Convoy 002` 22 km, `Convoy 004` 27 km; blue `Convoy 003` (VAB Mephisto, MLRS, MCV-80, HMMWV) 35 km. No column parked. TIC was off this flight, so this is the stock mover path. The parked-column signature from tests 17, 28 and 31 did not reproduce on this map; those captures stand, so the row goes to PARTIAL, not VERIFIED.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **REGRESSED: columns still park, and not only blue.** Every capture with convoys was measured off the recording (path length per unit over the mission). Drove: red on Vectron's Claw, Iron Gate (three columns, 5–46 km), Hornet's Nest, Caucasus 2026, Noisy Cricket (85 km) and Peace Spring (57 km); blue on Hornet's Nest (test 28, 12.7 km) and Noisy Cricket (test 32, 4 km). **Parked for the whole mission:** both blue columns on Inherent Resolve test 17 (Convoy 003, LAV-25/Bradley/HMMWV/MLRS/MRAP, and Convoy 004, M1A2/M6, each with a 5–7 point on-road route in the miz), the blue column on Caucasus 2026 test 31 (eight T-64BV, 41 min), and red Convoy 002 on Hornet's Nest test 28 (ten vehicles, 22 min). The 2026-07-07 distinct-road fix did not remove the failure, and the Inherent Resolve re-fly this row was waiting for reproduced it. Three of fifteen columns across seven missions; mixed tracked/wheeled columns dominate the parked set but the T-64 column is single-type, so that lead is not the whole story. This also blocks S3 (test 17's four ambush zones were keyed to the two parked blue columns).

**History:** post-fix flown evidence on Red Tide is clean — 2026-07-11 M1 `csar-snatch-toggle-question-dfdb7a`: BOTH sides' columns drove their full corridors end-to-end (blue `Convoy 001` M-113/VAB 61 km, red `Convoy 002` BTR-80/Grad 65 km, one real transfer per corridor, ~125 min); the original fail signature was Inherent-Resolve-specific (the Baghdad mega-column), so promoting fully off this row still needs the IR re-fly where it actually failed. Was ✗ REGRESSED: 2026-07-06 flown Inherent Resolve session `jovial-gates-574c9c` — red's ambient columns drove their roads, but the BLUE column sat PARKED at its Baghdad spawn for the entire 52-minute mission, the "columns don't drive" fail signature, blue-side
- **2026-07-09 Red Tide test: convoys DROVE fine here** (Tacview: 62 ground units moved >2 km, top columns 23–26 km, BOTH NATO and Soviet). So the parked-convoy bug is **not** universal — it may be Inherent-Resolve-specific (a coalesced/oversized transfer on a shared corridor — the S5 distinct-road fix). NOTE: ambient convoys are native `coalition.transfers` groups with a real `.miz` route, **not** the `mist.goRoute` movers, so the SCUD/COIN 2-WP fix (S2) does NOT touch this. Re-check on Inherent Resolve after the distinct-corridor sampling.
- **2026-07-06 flown evidence (Tacview + miz):** red ambient convoys worked — `Convoy 001` (Tikrit, drove
  21.6 km), `Convoy 002` (Shirqat FOB, drove 13.4 km down the corridor until the player killed it), `Convoy
  004` (NE belt, drove 18.8 km). **Blue `Convoy 003` — 24 mixed vehicles (MRAPs, Strykers, LAVs, Bradleys,
  Abrams) — spawned at the Baghdad corridor start (x=-142, y=160) and never moved an inch** (one ACMI
  position sample at t=0, max movement 0.0 km over 52 min), despite a well-formed On-Road route in the miz
  (waypoints marching up the corridor at 40 km/h, same shape as the red convoys that drove). Two leads:
  **(1) the merge** — the ambient top-up rolled ≥3 blue columns onto the same Baghdad→Balad corridor and the
  transfer system merged them into ONE 24-vehicle column (3×`AMBIENT_CONVOY_UNITS`=24 ✓); a 24-unit mixed
  tracked/wheeled group line-spawned into unauthored positions (no `convoy_spawns` at Baghdad — the
  ConvoyGenerator "convoy may experience issues at mission start" path) is exactly the form-up-deadlock
  shape. **(2) the spawn terrain** — Baghdad's corridor start may leave part of the line off-road/in scenery
  where the lead can't path. Red's columns were 8–10 light trucks at open-desert FOBs. **Next step:** cap or
  split same-corridor ambient transfers (distinct-road preference like the §35 `exclude_sources`, or one
  transfer per corridor per turn) so no mega-column forms, and/or verify the Baghdad route start sits on the
  highway; then re-fly (which also unblocks S3's spring). NOTE: this also blocked the S3 ambush spring this
  session — the teams were in place but nothing ever drove into them.
- **2026-07-07 (PR follow-up — root cause fixed, needs a re-fly):** two changes landed. **(1) Skim-only**
  (the economy-honesty design call): ambient columns now skim existing rear units instead of
  `commission_units`-ing free ones. **(2) Distinct-road (the S5 fix itself):** the convoy map keys transports
  by `(origin, destination)` (`TransportMap.add`), so the 3 same-corridor blue transfers were coalescing into
  ONE 24-vehicle column that line-spawned into unauthored positions and deadlocked. `_top_up_side` now samples
  **distinct** corridors (`_RNG.sample`, one column per road, capped at the road count), so no mega-column can
  form — the exact lead this row identified. This **trades away** the sketched "some columns share a road"
  texture, which the merge made unachievable anyway (a shared road was one parked blob, not two columns). The
  parked-column root cause is addressed in code; **the re-fly is what promotes this off REGRESSED** (confirm
  both sides' columns drive, and the S3 ambush spring unblocks).
- **What CI cannot exercise:** whether the columns actually drive their roads in-mission on both sides (the engine's own `ConvoyGenerator` path, but now exercised on ~27 campaigns instead of a handful); whether the turn-to-turn variation (1–3 per side, on distinct roads) reads as ambient life rather than a scripted parade; and whether red's ambient columns surface naturally as Armed Recon/BAI targets.
- **Setup:** any road-bearing campaign (`ROAD_BEARING_CAMPAIGNS`), **NEW game**, `ambient_supply_convoys` ON (default). Advance 2–3 turns without flying, checking the map each turn; then fly a mission and find the columns on the F10 map.
- **Pass:** blue AND red convoys appear on their own roads most turns (counts varying, occasionally two columns sharing a road, occasionally a quiet side); columns drive rear→front; red's columns can be right-clicked/fragged as ordinary Armed Recon/BAI targets and their kills count at debrief; a side with no same-side road (e.g. an island map) simply shows none, with no errors.
- **Fail signature:** no convoys ever on a campaign listed in `ROAD_BEARING_CAMPAIGNS` (corridor enumeration or the setting gate broken); the exact same number of convoys on the exact same roads every turn (the RNG not driving); convoys stacking unboundedly (existing convoys not counted toward the target); columns driving front→rear (orientation inverted); convoy units appearing from nowhere at debrief or kills not recorded (a phantom-spawn regression — every column must be a real `coalition.transfers` transfer).

### S6 — Tanker fragged for a no-`fuel:`-block airframe on a long sortie · §46 · ✅ CLOSED (feature reverted 2026-08-09) (was ☐ UNTESTED

**History:** (built 2026-07-08 from a player F-4E report — a −4259 lb OCA/Runway RTB margin with no tanker; `_refuel_tasking` now falls back to `estimated_fuel_consumption`; the fallback / measured-wins / no-tanker-squadron / helo / no-fuel-data gates are locked in ~~`tests/ato/flightplans/test_refuel_tasking_estimate_fallback.py`~~, but whether the tanker + rendezvous actually close the RTB margin in-mission needs a flight))
> ⛔ **CLOSED 2026-08-09 — the feature was reverted, so there is nothing left to fly.**
> §46 reverted outright to upstream behavior as work order C of the auto-planner
> re-convergence (`docs/dev/design/retlab-autoplanner-upstream-divergence-audit.md`, DECIDED
> block). Tanker tasking is upstream's again and no code fits tanks. The text below is the
> record of what was built and what was adjudicated; **do not open a pass against it.**

- **What CI cannot exercise:** whether the fragged pre/post-vul tanker + the AI rendezvous actually get the F-4E home (the planning is unit-tested; the flying isn't), and whether the estimate's threshold reads right across mod airframes (too eager → tankers on hops that internal + drop tanks already cover; too shy → still short).
- **Setup:** a campaign with an F-4E-45MC squadron **and** a tanker in the wing (e.g. **Germany — Red Tide**, KC-135MPRS), `auto_ato_behavior_tankers` ON. Auto-plan a long-legged OCA/Runway or Strike for the F-4E against a deep target; open the flight's kneeboard flight-plan page.
- **Pass:** the F-4E package now carries a **REFUEL** waypoint (pre- or post-strike) routed to a tanker, and the RTB-margin line reads **+N lb** (or at least far less negative) instead of the old bare −4259 lb "tank or divert". A short-hop F-4E is unchanged (no spurious tanker). A campaign with **no** tanker still shows the −N lb warning (correct — nothing to frag).
- **Fail signature:** a long F-4E sortie still fragged with no tanker while the kneeboard shows a large negative RTB margin (the fallback didn't fire — check `_refuel_tasking` reads `fuel_consumption or estimated_fuel_consumption` and that `can_auto_plan(REFUELING)` is true for the wing); tankers appearing on short hops that internal fuel covers (the estimate's `cruise_nm` bucket is too hungry — `AircraftType.estimated_fuel_consumption`); a measured-fuel airframe's behaviour changed (the `or` should never reach the estimate when measured data exists).
- ⚠️ **Premise moved 2026-08-07:** the F-4E-45MC now ships a **measured** `fuel:` block (adopted from DCS Liberation — see S7), so this row's own reported airframe no longer exercises the estimate fallback at all. The fallback path is unchanged and still applies to the ~217 airframes with no block; when flying S6, pick one of those (e.g. a Fulcrum or Flanker) rather than the F-4E, or fly the F-4E to adjudicate **S7** instead.
- ⚠️ **The estimate itself moved the same day:** the combat bucket's cruise constant went **520 → 700 NM**, re-derived once the twelve adoptions took the calibration set from 2 references to 9. Unmeasured combat jets now estimate **~25% lower burn** than when this row was written (a Fulcrum 14.3 → 10.6 ppm, a Flanker 39.9 → 29.6). That directly moves this row's threshold: **a tanker that used to be fragged for a mid-length sortie may no longer be.** Both fail signatures below still apply, but "tankers appearing on short hops" is now the *less* likely half — watch harder for the other one (a long sortie fragged with no tanker). The constant is deliberately conservative rather than best-fitting, and two CI invariants stop it being tuned optimistic; the reasoning is in `AircraftType.estimated_fuel_consumption`'s docstring. Helicopters and heavies are unaffected.

### T1 — Continuous clock marches + weather evolves across turns · §47 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-07-04; the march-forward-within-3–7 h band, time-of-day-derived-from-clock, midnight date-roll, and previous-turn weather bias are locked in `tests/weather/test_continuous_campaign_clock.py`; the multi-turn *feel* needs a play session
- **Headless adjudication:** `Conditions.advance` steps `start_time` forward 3–7 whole hours each turn, derives
  time-of-day from the marched clock, and rolls the date at midnight; `generate_weather(previous=...)` biases
  the seasonal draw toward the previous rung on the Clear→Cloudy→Rain→Storm ladder while still honouring a
  zero seasonal chance — all in `tests/weather/test_continuous_campaign_clock.py`. What CI *cannot* adjudicate:
  whether several turns in a row *read* as one continuous timeline (believable clock progression, weather that
  builds and clears rather than flickers) and whether the 3–7 h pacing feels right.
- **Interim evidence (2026-07-15, headless Red Tide self-play probe — 15 turns):** the marched clock held
  the contract on every advance — steps of 3–7 whole hours (07-13 10:00 → 16:00 → 19:00 → 07-14 02:00 → …
  → 07-15 20:00; ~2.4 game-days over 14 turns), dates rolling only at midnight — and the weather **evolved
  as systems, not draws**: ClearSkies → Cloudy (2 turns) → Raining (4 turns) → Cloudy (6 turns), adjacent-rung
  moves with multi-turn persistence, zero clear↔storm teleports. What's left for the fly is only the *read*
  (does it feel like one timeline from the cockpit/briefing).
- **Setup:** any day-and-night campaign with `continuous_campaign_clock` ON (default). Note the mission
  start date/time on turn 1, then pass ~5–6 turns without flying, checking the mission clock + weather each turn.
- **Pass:** the clock advances a few hours each turn and never jumps backward; the date increments only when the
  clock crosses midnight (not every 4 turns); time-of-day (dawn/day/dusk/night) follows the actual clock;
  weather trends between adjacent states over turns (e.g. clear → cloudy → rain → clearing) rather than
  teleporting clear↔storm. With the setting OFF, the stock behaviour returns (slot rotation + random weather).
- **Fail signature:** the clock jumps by a random large amount or goes backward (the advance interval / the
  `continuous_clock_active` gate — check `night_day_missions` isn't forcing day/night-only, which falls back by
  design); the date ticks every 4 turns regardless of the clock (`current_day` not reading `conditions`);
  weather still flickers with no correlation (the `previous=` bias not being passed from `Conditions.advance`).
  Knobs: `MIN/MAX_TURN_ADVANCE_HOURS`, `_WEATHER_PERSISTENCE_KERNEL` (`game/weather/conditions.py`).

### T2 — Persian Gulf "The Tanker War (1988)" campaign plays · ⊘ RETIRED

**History:** retired 2026-08-16 — the campaign was deleted on the DM's call ("Scrap T2"), so the scenario this row tracked no longer exists. It was never flown past the headless Phase 1–3 verification. The design note `retlab-tanker-war-campaign-notes.md` is kept as a record; do not author against it.

### T3 — Iraq "Umm al-Ma'arik (Desert Storm 1991)" campaign plays · Desert Storm campaign · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-07-19 — the DM's homemade DS91 campaign fixed + modernized + promoted; **laydown v2 same day, the DM's call**: blue = the seized H-3 complex + the off-map Saudi rear (the map has ZERO 60×60 heavy stands west of Baghdad — the E-3/KC-135 wing parked nowhere; slot_version-2 dimension resolution, the legacy `large` flag is zero map-wide), Al-Asad reverts to red as Qadessiya (the real Foxbat home), the campaign climbs the pipeline-road capture ladder H-3 → H-2 → Al-Asad, red gains Balad (al-Bakr) + Mosul (Firnas), the Fulcrum reserve moves off Al-Kut's helipad farm to Al-Sahra/Tikrit. Headless-verified end-to-end (17 CPs, the front exactly H-3 Main ↔ H-2, 40 squadrons resolve exactly, **every squadron dimensionally fits its parking** — a new standing guard, 104-node KARI net, arc + will parse); CI-locked in `tests/retlab/test_desert_storm.py` (8 tests incl. the parking-fit invariant); design note `retlab-desert-storm-campaign-notes.md`
- **What CI cannot exercise:** the played campaign — the KARI net actually degrading as the ADOC/SOCs die (MANTIS range-mode wiring on a real laydown), the off-map support wing actually flying its orbits from the Saudi rear (tanker/AWACS on-station reliability from an `OffMapSpawn` home), the front-line ladder ADVANCING when H-2 falls (the second M-113 leg becoming the active front), the night-one 0300 start feel, the Baghdad no-strike circle pricing CDE into Coalition cohesion, red's GCI-alert posture off the QRA reserve, and the renamed 1991 target set (Saad 16 / Baba Gurgur / Daura) reading right on the building cards.
- **Setup:** New Game → "Iraq - Umm al-Ma'arik (Desert Storm 1991)" (NATO Desert Storm vs Iraq 1991, start 1991-01-17 03:00). Generate turn 1; fly or spectate the western front out of the H-3 strips.
- **Pass:** generates + loads clean; blue's wing stands at the three H-3 strips with the E-3/tankers flying from "Coalition Rear (Saudi Arabia)"; the front reads H-3 Main ↔ H-2; the will meters read "Coalition cohesion" / "the regime's resolve"; the ribbon shows Instant Thunder with the Baghdad no-strike circle on the map; blue packages get F-15C escorts; the SAM rings light up under the KARI EWR chain and go autonomous (not dark) when a SOC dies; Scud sites relocate between missions; the A-10C/CH-47F squadrons carry era-clamped loadouts (no JDAM-era stores at a 1991 date); capturing H-2 advances the front to the H-2 ↔ Al-Asad leg and opens the H-3↔H-2 road to blue convoys.
- **Fail signature:** any squadron flying a substituted airframe (a faction/variant string regressed — `test_desert_storm.py` should have caught it); support flights failing to materialize from the off-map spawn (the OffMapSpawn planner path); the front not advancing after the H-2 capture (the M-113 ladder legs mis-bound); the will meters reading "Washington's patience" (the `will:` parse degraded to Vietnam framing); no phase on the ribbon (arc parse degraded); SAMs dark or crashing when C2 dies (the MANTIS wiring — check the trio statics bound to the right CPs); Wadiyan names on a building card (a zone rename regressed).

### T4 — DCS 2.9.28 Iraq map pass: dam destructibility + the ED airfield fixes · Desert Storm / Inherent Resolve · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, opened 2026-07-26 off the 2.9.28.26283 changelog; design note `retlab-iraq-map-2928-notes.md`. This row is the **gate on authoring the nine new dams as `power` scenery targets** — everything else in that plan is blocked on step 1 below.
- **What CI cannot exercise:** whether ED's new unique 3D dam models are *destructible* map objects (a `SceneryGroup` white zone must sit on a destroyable object — an indestructible model makes the whole dam-target plan void); whether ED's "fixed aircraft traffic problems on Mosul and H-3 Northwest airfields" actually clears the AI taxi behaviour at the fork's two most load-bearing Iraq fields; and whether the 2.9.28 airfield churn moved any parking slot out from under a based squadron.
- **Setup:** DCS 2.9.28 + Iraq map. (1) ME → navigate to **Fallujah Barrage** (map x ≈ 10 558 / y ≈ −42 682, 15 km from Al-Taquddum) and try to bind its structures as scenery-object zones; repeat on **Haditha Dam** (x ≈ 107 161 / y ≈ −171 435) as the second sample. (2) Generate an Inherent Resolve turn and a Desert Storm turn; watch AI departures at **Mosul** and **H-3 Northwest**. (3) Re-run `tests/retlab/test_desert_storm.py` against the bumped pydcs pin.
- **Pass:** the dam structures accept scenery-object zones and carry real `OBJECT ID` properties (⇒ authoring is green, proceed with the campaign split in the design note); AI at Mosul and H-3 Northwest taxi and depart without the previous jams; the DS91 parking-fit invariant still holds.
- **Fail signature:** the ME offers no bindable object over a dam, or the object binds but never registers damage (⇒ indestructible — **abandon the dam plan, do not work around it**); AI still deadlocking on the Mosul or H-3 NW ramps (ED's fix did not cover the case the fork hits); the parking-fit test failing on a squadron whose slot shrank in 2.9.28 (re-home the squadron, the Kola slot-shrink pattern).
- **Before committing an authored miz:** run `python tools/check_scenery_targets.py resources/campaigns/<campaign>.miz`. It mirrors the loader's pairing rules and catches the half-finished-authoring footgun (a blue zone with no white zones inside raises `SceneryGroupError` and the **campaign fails to load**). Baseline 2026-07-26: 71 campaigns · 712 objectives · **0 errors** · 21 pre-existing orphan warnings. CI guard: `tests/retlab/test_scenery_targets.py`.
- **The new airfields ARE usable** (design note "Using the new airfields"): unfinished surroundings constrain *how* a field is used, not whether. Undetailed terrain only bites where a campaign puts **ground** on it — a front line, `supply_routes:` convoys needing real roads, or low-level CAS/armed recon — none of which follow from merely basing aircraft there. **Tromso** (Kola, 72 km from Bardufoss, already in `the_anvil_of_war`'s belt) and **Zaranj** (Afghanistan, 19 km from existing Nimroz, in `graveyard_of_empires`' western belt) sit on mature maps and need no caveat at all. **Kharg** is air/naval-only — it is an island, so its surroundings are water; give it no front and no supply routes and the detail question disappears. Kharg's real blocker is **reach** (565 km from Al-Kut, so no current campaign gets near it) plus the pydcs pin bump, not terrain.
- **Deliberately not in scope:** rail interdiction (§35 is road-graph-only; new engine work).

### T5 — Marianas "Second Island Chain (2027)" campaign plays · Marianas 2027 campaign · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-02 — the fork's modern-day China campaign, forked from Fuzzle's Pacific Repartee laydown after a headless audit found that one loads clean but cannot be modernized in place (red airframes are hardcoded, so a `China 2020` swap upgrades ground/naval and leaves **J-7B** flying; no red AEW&C; 165 red vs 62 blue because six carrier blocks omitted `size:`; no `missile` TGO anywhere; zero feature preseeds). Guam is inverted to BLUE (Andersen's 194-slot ramp is the only one on the map that bases a heavy wing), two dormant NEUTRAL airfields are activated, and three PLARF sites are authored. Headless-verified end-to-end (18 CPs — BLUE 5 / RED 13 — 110 TGOs / 572 units, all 38 squadrons resolve, 164 blue vs 98 red airframes, the 3 missile TGOs binding Rota/Tinian/Saipan); CI-locked in `tests/retlab/test_marianas_2027.py` (23 tests incl. the parking-fit, tanker-boom/drogue-compatibility, ground_forces pin-band-match, no-blue-behind-the-chain, explicit-`size:` and mod-free-carrier-squadron invariants); design note `retlab-marianas-2027-campaign-notes.md`. Miz is GENERATED by `tools/build_marianas_2027_miz.py` — never hand-edit it. NEW game required.
- **First flown evidence 2026-08-05** (Tacviews `Tacview-20260805-184424` / `-190738` / `-200950` / `-203549`, session `pr-merge-code-audit-7e8b4c`) — the campaign loads and fights, and four things were learned:
  - **The authored "hunt the launchers" mechanic does not exist.** §49 was removed 2026-08-29 after never relocating a site in three flown attempts, so the three PLARF sites are stationary targets. They are still worth striking; they are not a hunt.
  - **§80 mixed hulls verified** (see B38); **§87 station-keeping partially verified** (see **B48**) on this laydown: pre-§87 generation had every authored naval group parked at 0.1 km; post-§87 the same groups sail 12–24 km on station with formation spacing unchanged. *That measures distance travelled, not displacement from the campaign anchor, which is §87's actual contract — B48 stays PARTIAL until a ≥90 min mission measures position-vs-anchor.*
  - **A blue anti-ship package flew with no escort, CAP, tanker or AEW&C airborne and lost 4 of 8 F/A-18F** to red QRA (Su-30s from Rota, JF-17s from Tinian — §1 working). Worth a look at how that package was planned.
  - **Red's planned air force never launched**: 15 airframes (J-11A ×6, H-6J ×6, **KJ-2000 ×2**) spawned `uncontrolled` on the Saipan ramp and only QRA scrambles flew, so red fought with zero AEW&C airborne and no standing BARCAP — undercutting the GCI posture the campaign is built around.
- **What CI cannot exercise:** whether the DF-21D/CJ-10 kit renders and fires from a `missile` TGO here at all; whether Andersen's heavy squadrons fit their stands *dimensionally* (the parking-fit test counts slots, not the slot_version-2 dimensions the DS91 audit needed); whether the AI flies Air Assault captures across 90–200 km of open water; and the frame rate with three PLAN carrier groups up.
- **Setup:** NEW game, "Marianas - Second Island Chain (2027)", USA 2020 vs **China 2027**, with the **Chinese Military Assets Pack**, **High Digit SAMs**, the **CJS Super Hornet** pack and the **F-22A Raptor** mod ticked (all arrive ticked — the campaign preseeds them). Fly or fast-forward two turns. Watch (1) a PLARF site across a turn boundary, (2) an Air Assault package sent at Rota, (3) the carrier-group magazine after a cruise-missile raid.
- **Pass:** the three PLARF sites relocate **and stay on their island**; their launchers are China-pack DF-21D/CJ-10/YJ-12B rather than Soviet substitutes; §3 draws them as suspected-activity circles until reconned; Andersen's B-1B/KC-135/E-3A all spawn on real stands without clipping; an Air Assault package reaches and takes Rota; the §63 magazine debits and does not rearm; **Tinian fields an S-300PMU-2 and Rota an HQ-22** (the two pinned batteries) with no SA-2/SA-6/HQ-2 anywhere; the map reads as one south→north axis with nothing blue north of Guam; **every PLAN task group is screened by Type 055/052D** (250 km HHQ-9) rather than 4-8 km missile boats and corvettes; the carrier's EA-18G det and F/A-18E tanker spawn, and the Growler is auto-fragged into the §77 Escort Jammer slot ahead of a strike package.
- **Fail signature:** a `missile` TGO spawning empty or with Soviet Scuds (China pack not applied); a heavy squadron spawning inside another aircraft at Andersen (dimensional parking fit, not slot count); Air Assault packages never planned across water; red flying a J-7B (a faction/campaign regression the yaml test should have caught first); the Super Hornet squadrons spawning empty or substituting (CJS pack not installed/ticked) while the legacy F/A-18C squadron still fields normally.
- **Known and deliberate:** the northern islands (Anatahan, Pagan, Agrihan, Uracus) are `is_in_sea` in the Marianas landmap — a pre-existing terrain-data property inherited from Repartee, which is why no missile site is authored north of Saipan. North West Field stays NEUTRAL (zero runways). Red fields no ambient convoys because no two red bases share an island.
- **Added 2026-08-03 — the auto-planner fix rides this row.** The first flown turn came out **100% defensive** (33 packages, 28 BARCAP, zero strike/SEAD/DEAD/anti-ship) because BARCAP demand — doubled per fleet CP, and this laydown has four — consumed all 66 fighters, so every offensive package scrubbed for want of its escort; plus the stock 150 NM range gate put the northern half of red out of reach in a 421 NM theatre. Was fixed by `MODERN_DOCTRINE.strike_escort_reserve` 0 → 8 (**fork-wide**) plus campaign preseeds `max_mission_range_planes: 400` and `desired_barcap_mission_duration: 60`. Headless-verified BLUE 2 → **25 offensive flights** (74 → 143 aircraft tasked, BARCAP 22 → 14). **Pass:** the turn-1 ATO contains real strike/SEAD/DEAD/anti-ship packages against the PLAN groups and island SAMs, escorted, with CAP still covering both carriers and Andersen. **Fail signature:** an all-BARCAP ATO again (the preseeds did not land — check Settings shows 400 NM and a 60-minute BARCAP station), or the opposite, CAP so thin that red's Badgers reach the boat unopposed. **Watch fork-wide:** the doctrine change touches *every* modern campaign — Baltic Fury and Inherent Resolve should show slightly fewer BARCAP flights and more escorted strikes; Red Tide is Cold War doctrine and must be unchanged. **⚠ The doctrine half was REVERTED 2026-08-09** by the planner re-convergence (work order B): `MODERN_DOCTRINE.strike_escort_reserve` is back to 0 fork-wide, so this row's all-BARCAP fail signature is live again on Marianas until the campaign preseeds RetLab planner suite or a per-campaign doctrine fork restores the reserve. The two campaign preseeds (`max_mission_range_planes: 400`, `desired_barcap_mission_duration: 60`) are untouched. Vietnam keeps its reserve of 4.

### T6 — The survival clock leaves exactly one flyable rescue window · CSAR · ☑ VERIFIED

**2026-08-21, DM call — closed, the clock stays as upstream wrote it.** The survival numbers
are not the fork's: `csar_survival_turns` (3) and `csar_survival_turns_hostile` (2) arrived on
2026-08-07 with fork PR #805, the adoption of upstream's open CSAR PR dcs-retribution#929, and
are read by `game/squadrons/csarservice.py`. The fork tracks #929 phase by phase, so changing
the numbers here means re-reconciling them on every future phase. Left alone.

**History:** the clock arithmetic is unit-tested; whether the window is long enough to actually fly a rescue is the design question, and only a played campaign answers it
- **What it is:** a survivor lasts `csar_survival_turns` (3), or `csar_survival_turns_hostile` (2) behind the lines, then goes MIA for good.
- **What CI cannot exercise:** whether 2 turns is a real chance or a formality. The old §21 model died on exactly this: a flown session found "after 1.4 h the rescue helos are just getting to the pilots" — a 130 kt helo cannot cross a theatre inside one mission. If the clock expires before any helo can plausibly arrive, the whole feature is decorative and the number needs changing, not the code.
- **Setup:** create a survivor deep behind the lines. Pass turns and watch the countdown on the map tooltip and the SITREP. Track whether a rescue package is planned, whether it launches, and whether it arrives before the clock runs out. ~60 min across several turns.
- **Pass:** a hostile-territory survivor is rescuable at least once with a genuine chance of success — a package is planned on the turn after the ejection and reaches him inside the window.
- **Fail signature:** the clock expires before any package can physically arrive at typical theatre distances (the number is wrong — raise `csar_survival_turns_hostile`, do not patch code); or the countdown shown to the player is off by one against the actual expiry, which makes every planning decision wrong.

### T7 — The rescue cascade: a failed rescue makes more survivors than it saves · CSAR · ☑ VERIFIED

**History:** nobody has modelled this; it is an emergent property of the feature, not a coded behaviour

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — VERIFIED on the user's call ("K3 good, along with T7").** Supporting evidence from the save: 3 blue downed pilots against 2 CSAR packages, and 18 ejection events — a rescue effort that is not itself generating a growing pile of survivors.
- **What CI cannot exercise:** a rescue helo shot down near the front produces **its own** downed pilots, which the planner then tries to rescue, which sends more helos. On paper that is a runaway. Whether it actually spirals — or self-limits on `max_csar_flights` (2) and the survival clock — can only be seen in a played campaign.
- **Setup:** a campaign with an active, contested front and CSAR on for both sides. Play 4–6 turns without micromanaging rescues. Track the downed-pilot count per turn. ~45 min on top of normal play.
- **Pass:** the survivor population stays bounded across turns; losing a rescue does not visibly compound; the helo squadrons are not drained by rescue attrition.
- **Fail signature:** a rising survivor count turn on turn; a rescue-helo squadron ground down to nothing by CSAR losses; the ATO increasingly dominated by rescue packages. If this shows up, the lever is `max_csar_flights` and the reachability gate, not the feature.

### U1 — Water/land relocate scripts run on the MIST shim · base plugin · ✅ CLOSED

> **Closed 2026-09-12.** The shim is deleted; the scripts run on upstream's MIST as they do upstream.

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, adopted from upstream 2026-07-05 with the upstream/dev merge; upstream #767/#838 run on full MIST — the fork's shim needed a new `mist.getGroupData` (43rd symbol), contract pinned in `tests/lua/test_mist_shim_getgroupdata.py`
- **Headless adjudication:** both scripts parse on Lua 5.1, register after `mist_moose_shim.lua` in the base
  plugin work orders (`tests/missiongenerator/test_*_relocate_plugin.py`), and the shim's `getGroupData`
  returns a dynAdd-shaped mission-table entry (units x/y/name, route, country, category) with fresh copies
  and nil for unknown groups (`tests/lua/test_mist_shim_getgroupdata.py`). What CI *cannot* adjudicate:
  whether `mist.dynAdd`'s `coalition.addGroup` same-name re-add actually swaps the beached group in live DCS
  without firing loss events, and whether the relocated positions are sane (ships in open water, ground
  units on land).
- **Setup:** any campaign whose generation beaches a naval escort or drops a ground unit in water (island
  maps are the natural stress; a carrier parked near shore beaches escorts).
- **Pass:** within the first minute, `dcs.log` shows `land_relocate:` / `water_relocate:` info lines for the
  moved groups and no script errors; the moved ships sit in open water under their original names; the
  campaign's kill/loss tracking still works for a relocated unit (kill one, it shows in the debrief).
- **Fail signature:** `attempt to call field 'getGroupData'` (shim symbol regression) or an error inside
  `run()` in either script; a relocated group vanishing or duplicating (the same-name addGroup swap not
  behaving); a relocated unit's kill missing from the debrief (name not preserved). Knobs: constants at the
  top of `resources/plugins/base/land_relocate.lua` / `water_relocate.lua`.

### B42 — Old-stock loadout attrition · §84 · ⊘ RETIRED

**History:** (**FEATURE REMOVED 2026-08-06** — flown, disliked, and ripped the same day. WATCH item 1 put eyes on it for the first time and the DM's verdict was *"I've seen and disliked, revert or rework"*, resolved to a **full rip**; the specific objection was **turn 1 already downgraded**.

**Why that objection kills the feature rather than re-tuning it.** §84 shipped twice. The first cut had `stock_attrition_start` at **0 %** — turn 1 fully supplied, mixing only as the war wore on, which is exactly the shape the DM has now asked for. It was then deliberately re-aimed to **20 %** because the first cut's own measurement (*"turns 1 and 5 all six flights identical"*) was read as the symptom the feature existed to fix, and the roll moved from per-flight to **per-station** so one jet carries a mixed magazine — both changes made on the DM's explicit ask at the time (*"what I'm looking for is mixing and matching on the same flight"*). So the two shipped configurations are the only two on offer, the DM has now seen and rejected the second, and the first is the one already judged to be doing nothing. Turning the knob back to 0 % would restore a version whose stated problem was that turn 1 is uniformly best-equipped — which is the property the DM now wants. There was no third setting left to try.

**What was removed** (everything but the registry tombstone that keeps §84 a resolvable section number, matching §11/§20/§40/§53–§55): `game/retlab/stock_attrition.py`, the `FlightMembers.from_roster` / `resize` hooks, all four settings (`stock_attrition`, `_start`, `_per_turn`, `_max`), the §84 feature-registry entry, ~~`tests/retlab/test_stock_attrition.py`~~ (36), and `WeaponGroup.category` — the load-bearing family guard, added by §84 and read by nothing else. **Save-safe**: the four removed setting keys land as dead `__dict__` entries via `deserialize_state_dict` (the §20/§55 precedent), and a pickled `WeaponGroup` carrying a stale `category` attribute is inert.

**If it is ever rebuilt, three guards were expensive to get right and must come back with it** — they are the reason this row is worth reading rather than deleting: (1) **never-an-upgrade** — `fallback` answers *"what do I use instead"*, which is a **date-gating** answer and is **not monotonic in year**; 18 same-category fallbacks in the shipped data point at a **newer** weapon (`2xAIM-120B` 1994 → `AIM-120C` 2018), so an unguarded walk hands out *better* stores the longer the war runs, and date gating cannot save you because it is a ceiling, not an ordering. (2) **category** — `WeaponType` cannot express a weapon family (a Sidewinder and a JDAM are both `UNKNOWN`) and `AN/ASQ-228 ATFLIR → AIM-120C` is a real shipped fallback, so without it the walk hangs a missile on the targeting-pod station. (3) **store family** — a mod that models its own pylons inherits the stock entries into the same pydcs table, so a stock store passes `can_equip` on a mod jet without being mountable and **the pylon spawns empty**.) (was ☐ UNTESTED, built 2026-08-03)

### B43 — SAM battery support section (refuellers + power) · §85 · ☑ VERIFIED

**History:** 2026-08-06, WATCH item 3, DM verdict "Passing" — the support section renders on SAM sites in a post-2026-08-04 game; no bare-launcher-and-a-jeep site and no bowser-instead-of-truck displacement) (was ☐ UNTESTED, built 2026-08-04

**Setup:** a NEW game on any campaign whose red side fields an S-300 family site (Red Tide is
the reference — 7 of them). No setting to flip; the support section is unconditional layout
data. Generate the mission and look at any SA-10/SA-20/S-400 site in the Mission Editor, then
fly on it.

**Pass criterion:** the site renders like the DM's training-server reference — radars, C2 and
six launchers as before, **plus** a cargo truck, 1–2 fuel bowsers (ATZ-5/ATZ-10/ATMZ-5/ATZ-60/
TZ-22) and 1–2 **Diesel Power Station 5I57A**, dispersed off the flanks rather than stacked on
the battery. Killing them must record as ordinary ground kills at debrief. Separately, generate
a campaign with a **Sky Sabre** battery and confirm it now spawns SHORAD point defence (it
never has).

**Fail signatures to watch for:**
- Support vehicles **overlapping or clipping** a launcher/radar (the template positions clear
  everything by ≥50 m, but only DCS can confirm the models fit).
- A site generating **two bowsers and no generator** (or vice versa) — the fuel and power slots
  were merged; a unit group fields exactly one type.
- The site's **existing** units having MOVED relative to earlier saves — the new groups were
  appended so the template origin is unmoved; if the battery shifted, the origin moved.
- Fuel bowsers appearing **at a front line** in numbers that look wrong. Expected: they ride
  along with cargo trucks like the existing Urals/M818s. A **5I57A at a front line is a bug**
  (`UnitClass.POWER` must never be deployable).
- Any S-300 site generating **no** support at all — check the faction actually fields the
  S-300 preset group, since access comes from the preset, not the faction's `logistics_units`.

### B44 — Support kit at legacy SAM sites + fuel convoys · §85 · ☑ VERIFIED

**History:** 2026-08-06, WATCH item 3, DM verdict "Passing" — legacy sites field trucks **and** a bowser, i.e. the slot-displacement bug this wiring was built to fix did not reproduce) (was ☐ UNTESTED, built 2026-08-04

**Setup:** a NEW game on Red Tide (or Desert Storm / Yankee Station). No setting; the wiring is
layout/preset/faction data. Headless baseline on a fresh Red Tide: 11 of 17 legacy SAM sites
rolled a refuelling section (the roll is per-site, so expect *most* but not all).

**Pass criterion:** legacy SA-2/SA-3/SA-5/SA-6 sites field trucks OR a fuel bowser in their
logistics spots (one type per site — the mixed truck+fuel+power spread is S-300-only by design);
on Yankee Station, an HQ-2 site renders the **ZIL-131 KUNG** C2 truck; **EWR sites render their
support section** (Red Tide: radar + KUNG + 1–2 diesel power stations + trucks — headless showed
all 6; a western FPS-117 site renders the ECS shelter instead, never the Soviet kit);
**layout-generated economy buildings are furnished** (a generated fuel farm / ammo depot /
factory / warehouse fields 1–2 trucks or a bowser beside the statics; hand-authored named targets
— DS91's CENTAF set, RT's authored factories — stay bare **by design**, and any authored building
cluster having MOVED from earlier saves is the origin-shift fail signature);
**the C2 compounds render and their kill semantics hold** (Desert Storm is the showcase: all 13
KARI comms relays + 4 command centers field vans/GCI shelters/generators/trucks; RT's
scenery-authored network stays as authored; **verify a §51 comms node keeps jamming after the
tower dies while its van survives, and stops when the compound is dead** — that is the accepted
§51/§52 semantics change, not a bug; a §52 decap now requires the vehicles dead too); and over a
few turns a supply convoy is seen carrying a refueller (blue M978 / red ATZ family / a COIN
campaign's civilian ATZ-5 on the ratline); **the do-them-all closure renders** (a legacy SA-2/3/5/6
site fields trucks AND a bowser — DS91 headless showed 46/46; an S-300/HQ-22 site renders the
deterministic textbook spread of 2 trucks + 2 bowsers + 2 power stations; Marianas' Tinian
HQ-22 fields the Soviet fuel kit; a modern HDS campaign's SA-20+ site places the **Gazetchik-E
decoy** — THE fly question: does an ARM actually get seduced by it, and does it show as a
separate killable unit; a modern US comms/CC compound renders the Trojan Spirit / fire-control
bunker / Predator GCS). Kills record as ordinary ground losses.

**Fail signatures to watch for:**
- A bowser or the KUNG **clipping** launcher/radar models (positions are the templates' existing
  Logistics/CP spots, but only DCS confirms the model footprints).
- The KUNG at an SA-11/SA-17/Hawk site (those keep their organic C2 — a KUNG there means the
  preset edit leaked).
- ATZ-10/ATMZ-5 at a **Vietnam-era** site (the shared layouts deliberately carry only the
  1965–67 trio; the 80s pair should only appear via Red Tide / Iraq 1991 faction fill at
  *generic*-layout sites and in convoys).
- Legacy sites that previously rolled trucks now **never** rolling trucks (the whitelist
  addition must widen the roll, not displace it).

### B47 — Missile battery support section + priced launchers · §85 · ☑ VERIFIED

**History:** 2026-08-06, WATCH item 3, DM verdict "Passing" — missile batteries render the transport/transload/fuel/command section rather than three launchers and a jeep. Verified the **same day it was built**, so the composition was seen on a genuinely fresh game) (was ☐ UNTESTED, built 2026-08-06

**Setup:** a NEW game (the composition is generated at campaign start, so an existing save keeps its
old three-launchers-and-a-jeep sites). Best coverage in one pass: **Desert Storm** (9 authored Scud
batteries, the Great Scud Hunt) or **Red Tide** (2, plus the C2 kit its faction rosters). No setting
— the wiring is layout + unit data.

**Pass criterion:** a missile site renders as a **battery**, not three launchers and a jeep — 3
launchers + **2 cargo trucks** + a transporter/loader + a fuel bowser + (on Red Tide / Iraq 1991) a
**ZIL-131 KUNG**, **Ural-375 PBU** or **GCI station** command vehicle, all within ~60 m of the
launcher line and ≥20 m apart. On USA 2020 the same site reads in NATO kit (M818/M1083 trucks, a
HEMTT M977 as the loader, an M978 bowser, a Trojan Spirit or fire-control bunker). Germany 1944's
V-1 site fields an Opel Blitz pair + an Sd.Kfz.7 and **no** bowser or C2 (correct — that faction has
neither). Killing support units records as ordinary ground losses.

**Second half — the buy menu.** Open a base's ground-object purchase for a missile or coastal site
and confirm the launchers now **cost money** (Scud-B 40, Iskander-M 70, CJ-10 75, DF-21D 85, Silkworm
30 …) instead of being free, and that repairing a killed launcher is charged at the same price.

**Fail signatures to watch for:**
- Support vehicles **clipping** a launcher model (spacing is ≥25 m in the template, but only DCS
  confirms the footprints), or spawning on a slope/in water at a campaign's authored site.
- A **fuel bowser standing in as the transporter/loader**, or a site that fields a bowser and *no*
  cargo truck — both are the displacement bug this change fixed, returning.
- An S-300-style **diesel power station** at a missile site (deliberately excluded — it would pin
  the scoot; if one appears, the S-300 slots leaked into this layout).
- **Any campaign's authored missile site having MOVED** from where it sat before — the template
  anchor must not have shifted (guarded by a test, but the map is the proof).
- A missile site the AI can no longer afford to rebuild, or an economy visibly distorted by the new
  prices (they are ~135 for a full SCUD battery against ~230 for an S-300 site).

### B49 — Carrier recovery-phase deck dressing · §72 · ✅ CLOSED (feature removed 2026-08-20) (was ◐ PARTIAL

Both §72 phase tiers were cut on the DM's call: the launch-phase round-down E-2C, the
recovery-phase bow respot, and the `deckdecor` plugin that swapped them. Deck dressing is now
one tier — island street gear plus the LSO team — standing for the whole mission, so there is
no respot to watch and nothing to enable. Nothing to fly.

**What this row had established, kept because it is evidence, not status.** Test 9
(2026-08-18, Syria `operation_desert_trident`) showed the plugin running its full sequence on
CVN-72 (`spawned 3 recovery-phase static(s) forward`, `struck 1 launch-phase static(s) below`)
after the `LuaData.serialize` scalar-drop was fixed in RetLab#847 — so the emit path worked.
Test 11 (2026-08-19) then measured why the tier could not keep static aircraft: **14 aircraft
late-activated onto the CVN-71 deck between t=2340 and t=3913**, 9 to 35 minutes after the
recovery set spawned, five onto the six-pack row. That is the hard constraint that outlived
the tier, and it is guard-tested in `game/data/carrier_deck_decor.py`. Two things were never
answered and no longer need to be: whether spawned gear rides a steaming deck, and what tripped
the astern cone on 2026-08-16 with nothing in it.

**The bow spots are still unmeasured.** `KNOWN_PARKING_SPOTS` holds 16 entries after the
2026-08-17 pass; the Supercarrier guide implies more forward. Nothing in the fork places
anything there now, so this is a note, not a task. See
[retlab-carrier-deck-decor-notes.md](design/retlab-carrier-deck-decor-notes.md), *The phase tiers
are cut*.

### B48 — Naval station-keeping racetracks · §87 · ☑ VERIFIED (2026-09-16, DM)

**2026-09-16, DM verdict in chat (session `9148a88a`)** — **VERIFIED.** "B48 should have been checked already vs the last 10 tests that include ships." The record agrees: five campaigns measured off the ACMI (Marianas 2027, Baltic Fury, Syria Desert Trident, Persian Gulf Scenic Route, Persian Gulf Noisy Cricket), every authored non-carrier group on its oval, red included on test 32, and the carrier groups excluded by §88 as designed. Closed on the DM's call; off the WATCH card.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — only the Forrestal group is in the recording: 48–60 km straight under §88, by design. The red BABIRUSA pair was outside the host's recording bubble.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — **first red evidence, on a mod hull.** MOSQUITO, the two Iranian FACs from the CurrentHill pack, sailed 13.5–14.0 km inside a 5.3 km box over 134 min on the 5-waypoint 15.9 km oval the `.miz` gives them, at a 10 kt commanded speed. CVN-71, LHA-1 and their six Burkes ran 62–84 km on the 2-waypoint 100 km route, §88 by design. The second red group, TARANTULA, was armed by the magazine plugin but is not in the `.miz` (see B39).

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, `Tacview-20260913-125128`, 59 min
of sim, DCS 2.9.29.27468) — **holds up, fourth campaign, both authored ship groups.**
ALBATROSS (Ticonderoga + Perry) sailed 14.9 / 20.9 km for 2.5 / 1.9 km of net drift.
DIREWOLF (Burke + Ticonderoga) sailed 14.6 / 22.1 km for 2.5 / 1.9 km. Both groups turned
through eight or more headings, which is the oval. The CVN-71 and LHA-1 groups ran 36–41 km
straight on 300° under §88, excluded by design. The red navy (MONSTER, SHOEBILL, HORNBILL)
was not in the `.miz` at all — see B39 — so nothing is known about red this turn. Nothing in
this row names what is still owed after four campaigns; closing it is a DM call.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **not exercised; do not read the drift as a failure.** This campaign
has **zero ship TGOs** — the only naval object is the CVN-73 carrier control point, which §87
deliberately excludes (carriers keep `steam_into_wind`). The carrier and its escorts do travel
22–26 NM in a straight line over the 72 minutes with no heading change beyond 30°, which looks
like station-keeping failure and is not: it is §88 steaming for wind down the angled deck,
working as designed. The row still needs a campaign with an authored ship group.

**Setup card:** [flycards/REGRESSED-SWEEP.md](flycards/REGRESSED-SWEEP.md) — one Starfire campaign (`operation_desert_trident`) clears this alongside C9 and B48.

> **Test 9 flown 2026-08-18** (Syria `operation_desert_trident`, `Tacview-20260818-214946` + `dcs.log` + `state.json` + the generated `.miz`) — **holds up, third campaign.** Measured off the ACMI, the two
> well-sampled escorts kept station: PERRY sailed **22.9 km for 2.8 km of net drift** (1,478
> frames) and an Arleigh Burke **9.9 km for 2.5 km** (601 frames) — the same shape as the
> 2026-08-16 Baltic Fury numbers. CVN-72's 11.4 km drift is expected and not a failure:
> carriers steam for wind under §88 and are excluded by design. The remaining hulls logged
> 6–44 frames, where sailed distance equals net drift exactly — that is sparse Tacview
> sampling, not a track, and is not evidence either way.

**History:** 2026-08-05, flown Marianas 2027, Tacviews `Tacview-20260805-190738` / `-203549`, session `pr-merge-code-audit-7e8b4c`. **Strengthened 2026-08-16** (Baltic Fury spectator watch, `Tacview-20260816-104955`, session `c86c58dd`): all five red naval groups held anchored loops over 95 min — 21–28 km sailed, net drift only 2.6–4.0 km, 7–10 kt, headings cycling — station-keeping exactly as designed on every non-carrier group observed. **New watch question from the same track:** the blue carrier's ESCORT group sailed its own dead-straight authored leg (191°, 45.8 km flown) while the carrier sailed a different one (authored 166°) — whether the screen stays with its boat over a full mission is a §87/§44/§88 interplay item, not yet a verdict

> **Row created 2026-08-06.** §87 landed 2026-08-05 (PR #780) and shipped **without a row of its
> own** — `CLAUDE.md` pointed it at **B46**, which is the §28 settings-surface row, and its only
> recorded evidence sat inside **B38**'s prose. The pointer is corrected to B48. This is exactly the
> drift the proposed features↔checklist CI test would catch
> (`docs/dev/design/retlab-verification-cadence-notes.md`, Part 2).

**What the flown evidence DOES establish.** Pre-§87 generation had every authored naval group parked
at **0.1 km**; post-§87 the same groups **sail 12–24 km** over a 48-min mission, and the widest gap
between any two hulls of a group — measured at t=300/1500/2800 s — is **constant to two decimal
places** (1.80–2.16 km for the §87 racetrack groups), with every unit of each group logging an
identical path length. So: DCS accepts the authored route, naval groups actually get under way on it,
and a §80 mixed-hull group holds formation while doing so. Generation-side coverage is separate and
already measured — marianas_2027 11/11 · pacific_repartee 21/21 · tanker_war_1988 2/2 ·
1968_Yankee_Station 2/3 groups put on station, the one miss being the designed safe degrade.

**Why this is PARTIAL and not VERIFIED — the load-bearing contract is the one thing not measured.**
§87's guarantee is a hard **~1.6 NM (≈3 km) ceiling on displacement from the campaign anchor**: the
racetrack is centred *on* the marker precisely so the group's mean position stays there, keeping the
map, the drawn threat rings and the turn model honest. What was measured is **path length travelled**
and **inter-hull spacing** — different quantities. A group sailing 24 km in a straight line off
station would produce identical numbers. Nothing yet confirms the ships stayed near their markers.

**Second unproven leg: the `SwitchWaypoint` loop.** At the design's 10 kt on a 3 × 1 NM track a lap is
~8 NM ≈ 15 km, and 48 min of steaming is ≈ 14.8 km — so the observed 12–24 km is **0.8–1.6 laps**. The
upper end must have come round; the lower end may never have reached waypoint 0 again. Whether DCS
*restarts* a naval group's circuit is the row's stated DCS-only unknown and it remains inferred, not
observed.

**Setup:** any naval campaign (Marianas 2027, Tanker War 1988, Pacific Repartee), a mission of **≥90
min** so at least two laps are possible, Tacview on. No setting — §87 is always-on generation
behaviour, the §80 precedent.

**Pass criterion:**
1. **Displacement, not distance.** Pick 3–4 naval groups; note each group's anchor from the campaign
   map, then measure its position in the Tacview at ~4 points across the mission. Every sample is
   within **~3 km** of the anchor.
2. **The circuit repeats.** A group's track is a closed oval walked more than once, not a one-way
   transit that straightens out and continues.
3. **Nobody beaches.** No group runs aground or ends up in shallows — the per-leg 1 NM landmap
   sampling is what should have prevented it.

**Fail signatures to watch for:**
- **A group steadily walking away from its anchor** — the loop is not firing, so it flies the route
  once and then holds the last heading. This is the primary failure mode and the reason the row
  exists; the documented fallback if DCS won't loop is to author enough waypoints to outlast the
  mission.
- **A group still parked at ~0.1 km.** The feature no-op'd. Every §87 failure path degrades to
  stationary **silently** — no landmap, no clear orientation among the 12 candidate bearings, or a
  spawn the landmap won't confirm as open water. A harbour-authored marker legitimately produces
  this, so check the campaign's other groups before calling it a bug.
- **A hull aground, or a group threading a strait it clearly shouldn't fit through.**
- **Threat rings visibly not over the ships** — the map draws the ring at the marker, so a group far
  off station makes the whole displayed threat picture wrong. This is the consequence that makes
  criterion 1 matter rather than being pedantry.
- **§63 / §81 interaction:** a cruise-missile `FireAtPoint` or a naval-magazine ROE change that
  **wipes** the route instead of popping back to it. §87 deliberately uses ME waypoints + a
  `SwitchWaypoint` action rather than a scripted `mist.goRoute` (a `setTask`) specifically so a
  pushed fire task pops back — the §49 fire-then-scoot clobber, avoided by construction. If a ship
  fires a §63 raid or hits winchester under §81 and then goes dead in the water, that assumption is
  wrong and both features are implicated.

**What CI cannot exercise:** everything above. The generation side (orientation choice, land
sampling, the anchor-centred geometry, the safe degrades) is covered by
`tests/missiongenerator/test_naval_station_keeping.py` (11 cases) and the envelope is guard-tested
against ship threat rings — but whether DCS's naval AI *loops* a group on `SwitchWaypoint`, and how
far it actually wanders doing it, only a mission shows.

### B53 — AI flights no longer push early for a tanker stop they never fly · §46 · ✅ CLOSED (the dwell it fixed was deleted 2026-08-09) (was ☐ UNTESTED

**History:** , built 2026-08-09)
> ⛔ **CLOSED 2026-08-09 — the feature was reverted, so there is nothing left to fly.**
> §46 reverted outright to upstream behavior as work order C of the auto-planner
> re-convergence (`docs/dev/design/retlab-autoplanner-upstream-divergence-audit.md`, DECIDED
> block). Tanker tasking is upstream's again and no code fits tanks. The text below is the
> record of what was built and what was adjudicated; **do not open a pass against it.**


> **The nine minutes nobody spends.** Found from a player report — the escorted strike was ahead
> of the kneeboard timetable — and confirmed against the generated `.miz` before any code was
> touched. The 2026-07-01 receiver-dwell budget (§46, PR #399) charges
> `refuel_service_time(size)` = `4 × size + 1` minutes to the leg leaving a `REFUEL` waypoint, and
> `FormationFlightPlan.push_time` releases the flight from its hold that much earlier so it can
> tank and still make the join. Humans spend it. **AI never does:** `RefuelPointBuilder` stops the
> Refueling task the moment every jet is at 50% fuel — already true on arrival at a pre-vul stop —
> and `ai_unlimited_fuel` (on by default, and switched off only at the JOIN) pins AI fuel across
> that leg regardless. So the hold released the AI early and nothing consumed the difference.
> Measured on one WILDCAT package: strike (2× F-15E, tanker) **9.02 min early** at the join, TARPS
> (1× F-14, tanker) **5.00 min**, escort (2× F-14, **no** tanker) **0.00** — the error equals
> `4 × size + 1` exactly, and the flight without a refuel waypoint is the control. Fix:
> `FlightPlan.refuel_duration` returns zero for a flight with no clients, so an AI receiver's
> takeoff, hold push and chained ETAs all stop carrying the phantom dwell. The package tanker
> still reserves service time per receiver (`PackageRefuelingFlightPlan.patrol_duration`) —
> overlapping is harmless and keeps gas on station. Pinned in
> ~~`tests/ato/flightplans/test_refuel_timing.py`~~ (the AI dwell exemption and the AI push time, each
> against its player counterpart).

Plan a package where the strike takes a pre-vul tanker and a player flies the escort — the
kneeboard's Refuel→Join leg shows a GSPD far below cruise (~180–280 kt) when a stop is budgeted.
Fly it and tank as briefed.

- **Pass:** the AI strike reaches the join and the IP at the times printed on your kneeboard, and
  its weapons go down inside your TOT window rather than minutes before you arrive. A package mate
  with no refuel waypoint is unchanged.
- **Fail signatures:**
  1. **The strike is still early by `4 × size + 1` minutes.** The dwell is still being charged —
     check `client_count` on that flight (a flight with a human in it *should* still be charged).
  2. **The strike is now LATE.** The dwell was load-bearing for something else on that route; look
     at `_travel_time_to_waypoint` and the takeoff time, which both shift with this property.
  3. **The AI arrives at the tanker before it is on station.** `patrol_start_time` reads the
     receiver's `chained_tot_for_waypoint(refuel_pre)`, which now falls ~9 min later for AI — the
     window should have moved with it.
  4. **A player flight is early too.** Different bug: the human skipped or short-cycled the boom.
     Expected behaviour, not a planner fault.

**What CI cannot exercise:** whether DCS's AI actually flies the leg at the planned speed. The
budget arithmetic is unit-tested; the arrival time is a mission.

### B55 — Carrier steams for wind down the angled deck · §88 · ☑ VERIFIED

**2026-08-17 — VERIFIED, computed from the flown `.miz` rather than eyeballed.** CVN-72 steams BRC **249** at 17.7 kt; the mission wind is from **220 at 8 kt** (the kneeboard's own weather line agrees). Vector sum of ship and air motion gives **25.0 kt of relative wind arriving from 240.1°** — **8.9° off the port bow**, straight down a ~9° angled deck, and 25 kt is exactly what §88 targets. The emitted `deckDecor.brc` field carries the same 249, so the plugin and the ship agree. Cross-check: LHA-1 Tarawa steams **220**, i.e. bow-straight into wind, which is correct for a deck with no angle — so the offset is being applied per hull rather than globally.

⚠ **Recorded a day late.** The computation was done and reported on 2026-08-17 and never written into this row, so the fly card kept asking for a result that already existed. Same failure as G32. See the cadence note's authoring rules.

**History:** adopted 2026-08-09 from geofffranks' `12d71346`, upstream issue dcs-retribution#865. **Desk finding 2026-08-16** (Baltic Fury spectator generation, session `c86c58dd`): the authored PORPOISE carrier leg was **166.0° at 16.4 kt** under save wind `direction=11, 4.73 m/s`, but `solve_carrier_cruise(11, 4.73, 9.0)` returns **135.1° at 22.0 kt** with no input combination reproducing 166/16.4. **RESOLVED 2026-08-16** (session `bd15b892`, desk — miz + solver cross-check): the 166/16.4 discrepancy was in the repro call's units, not the pipeline — `steam_into_wind` feeds the solver **knots** (`mps(wind.speed).knots`; 4.7257 m/s = 9.19 kt, matching the solver's 25 kt target units), and `solve_carrier_cruise(11, 9.186, 9.0)` = 165.8°/16.38 kt, rounded to **166** by integer `Heading.from_degrees` — byte-for-byte the authored leg (confirmed from the miz: `0077 | PORPOISE (Carrier)` 166.0°/16.4 kt/100.0 km). All three suspects acquitted: the sea probe only shortens the leg (100→20 km, never a new heading; the 100.0 km leg proves attempt 0 passed), the miz weather block carries the save's at_0m verbatim, and `max(0.0, ·)` never engaged. The escort leg (`0078 | PORPOISE (Escort)` 191.0°/15.8 kt) is the **same solver at deck 0** — escorts have no `landing_deck_angle` — i.e. plain bow-into-wind, confirming at_0m follows DCS blows-to (the `atis.py` empirically-verified convention). **The investigation then found the real §88 defect: the solver's deck-angle sign was inverted** — it solved to the starboard mirror (`wind_from − offset`), putting the felt wind at `BRC + deck` instead of down the port landing area at `BRC − deck`: felt wind from 175 vs the 157 landing area = **+7.7 kt crosswind, double the ~3.9 kt bow-into-wind residual the feature was adopted to remove**. Fixed same day (`wind_from + offset`, both EXACT and the high-wind clamp), pinned by a 60-case apparent-wind invariant test + the Baltic regression numbers; this save's wind now authors **216°/16.4 kt** (felt wind from 207 = exactly down the landing area, 0.0 kt crosswind). Features doc §88 "The B55 desk finding" has the full mechanism. The fly clause below is still owed — on the ball is the one thing the desk cannot measure

> The boat used to point its bow straight into the wind, leaving a permanent ~9° crosswind
> across the landing area, and wrote a **negative** carrier speed above 25 kt of ambient wind.
> `solve_carrier_cruise` now picks heading + speed for ~25 kt down the angled deck with zero
> crosswind, per-hull from `landing_deck_angle` in the ship yamls. The three solver modes, the
> yaml parsing guards, the per-hull angles, and the generator's use of the result are pinned in
> `tests/flightplan/test_carriercruisesolver.py`, `tests/dcs/test_shipunittype.py` and
> `tests/missiongenerator/test_ship_sail_waypoint.py`. What CI cannot exercise is whether a
> Case I recovery actually flies better behind it.

Needs a flight: generate a NEW mission with a carrier and a steady wind of ~10–20 kt, then fly a
Case I recovery.

- **Pass:** the ship's heading sits **clockwise** of the wind reciprocal by `asin(25·sin(deck) /
  wind_kt)` — ~25° at 9 kt of wind, ~9° at 25 kt (never counterclockwise: that is the pre-fix
  mirror); on the ball, the relative wind is straight down the angled deck with no drift to
  fight; BRC on the kneeboard and the CV Operations Data page matches the ship's actual heading.
- **Fail signatures:**
  1. **Crosswind is worse, not better** — the felt wind sits `2·deck` off the landing area: the
     sign inversion is back (solver-side now pinned by
     `test_apparent_wind_runs_down_the_port_angled_deck`; if the test is green, suspect a
     negative `landing_deck_angle` in that hull's yaml — every shipping hull is port-offset, so
     the value should be positive).
  2. **The carrier sits dead in the water** — ambient wind exceeded 25 kt and the solver hit
     `HIGH_WIND_SPEED_CLAMP`. Wind over deck is still satisfied; note the wind speed and whether
     a motionless boat is acceptable.
  3. **BRC on the kneeboard disagrees with the ship** — `add_runway_data` is getting a stale
     heading rather than the solver's.
  4. **The carrier is on land or never moves at all** — the 5-attempt sea probe rejected every
     candidate point and `steam_into_wind` returned None (pre-existing behavior, and the
     2026-08-16 sign fix moves the probed bearing by ~2× the solver offset — 166 → 216 on the
     Baltic save — so coastlines that cleared before may not clear now).

### B56 — Living battlespace pre-roll: mid-cycle mission start · §89 · ⊘ RETIRED

**History:** 2026-08-16, spectator Game Master watch, Baltic Fury turn 3, Tacview `Tacview-20260816-104955`, session `c86c58dd`; 3 of 4 pass clauses verified — **38 aircraft airborne at spawn** both sides (CAPs mid-station at 31k ft, escorts mid-route, the pre-roll-launched strike already enroute at 21k ft), war clock read 00:40 (the ACMI ReferenceTime), first recovery T+22.6m, zero parking-overflow symptoms in dcs.log. Outstanding: the SEATED clause — player startup at the briefed time with full ground ops after the auto pre-roll (the qt_ui launch wiring) — needs the flown sortie from the app) (was ☐ UNTESTED, built 2026-08-15

> With `living_battlespace_preroll` on, player packages are seated a phase-aware distance into
> the turn's cycle (0 min on the first turn, 15 on the next two, then the cap, default 40) and
> the launch flow marches the existing mission sim to the player's startup before generating.
> The curve, the pinning math and the launch trigger are pinned in
> `tests/retlab/test_living_battlespace.py`, and the design note's headless probe generated
> a correct mid-cycle miz from this same machinery. What CI cannot exercise: the Qt launch
> wiring (`qt_ui` is not type-checked) and the feel of the world at spawn.

Needs a flight: enable the gate on any campaign, reach turn 3+ (or fly turn 1 for the 15-minute
version), take off normally.

- **Pass:** at spawn, multiple AI flights are already airborne mid-route (F10 map), at least
  one flight recovers at a friendly field within ~20 minutes, your own startup happens at the
  briefed time with full ground ops, and the DCS mission clock reads mission start plus the
  pre-roll.
- **Fail signatures:**
  1. **The whole war is on the ramp with you** — the pre-roll never ran (the launch-flow
     branch didn't fire; check the stop-condition borrow in `QTopPanel.launch_mission`).
  2. **You spawn mid-air or past your startup** — the PLAYER_STARTUP halt fired late
     (`AtDeparture.should_halt_sim` ordering).
  3. **Repeated "No room on runway or parking slots" air-promotes** — mid-cycle generation
     overflowing parking (probe finding F7; once is the known fallback, a pattern is a bug).
  4. **Flights you expected are missing** — they completed or died during the pre-roll; check
     the debrief carries their results. Pre-roll losses are real by design (measured ~5 of 35
     flights per 40 min); if that rate reads as carnage in play, the combat policy is open
     calls 2–3 in the design note.
  5. **Turn 0 differs at all from gate-off** — the curve's zero is not gating; the expectation
     is byte-identical.

### B57 — Living battlespace P2: ramp residue + clean-wing returners · §89 · ⊘ RETIRED

**2026-08-17 — VERIFIED on the DM's call.** Note for anyone re-reading this: the 2026-08-17 Syria mission (`Test 6`) is NOT evidence either way — its `.miz` contains no parked residue at all (every blue group carries a flown route), so nothing on that mission could have shown this working or broken.

**History:** — **was ✗ REGRESSED; the structural gap is FIXED 2026-08-16 (session `adoring-jepsen-b63803`), awaiting a flight.** The gap, found by the dedicated 2026-08-16 desk check (session `c86c58dd`): **the residue path was starved by construction.** `AircraftSimulation` removes a package from the ATO when it completes (`game/sim/aircraftsimulation.py` → `ato.remove_package`), and `_spawn_completed_residue` iterated the ATO's packages at generation — so a completed flight only rendered as ramp residue in the narrow window where its package still held an uncompleted sibling. The common case (a solo-flight CAP package finishing its cycle) left the ATO entirely and never reached the generator: marches of 40/75/88/150 minutes all produced **zero** ATO `Completed` flights at generation (the ATO census visibly shrank 38 → 18 across the 150-minute march). The earlier "condition never arose" reading was this same gap seen from the other side. The unit tests faked the generator's input and could not see the sim's removal — the third fake-blind §89 finding of that day. **The fix** took the ledger option: the removal site records (flight, arrival-frozen-at-completion) into a transient ledger (`record_completed_residue` in `game/retlab/living_battlespace.py`; cleared at `begin_simulation`, never pickled, `fogofwar.py` pattern) and `generate_flights` parks ledger flights after the tasked walk. Recorded-means-removed keeps ledger and ATO walk disjoint, and the generation-time synthetic `Completed` flights (idle ramp, QRA, red-scramble) never pass the removal site, so the "excluding the idle synthetics" caveat is now structural rather than a counting rule. The arrival is frozen because `Squadron.arrival` follows a live relocation order. **A second defect surfaced while testing the fix:** removal returns the airframes to `untasked_aircraft`, so `spawn_unused_aircraft` rendered the same jets again as idle filler — `_spawn_unused_for` now debits `idle_spawn_count(untasked, parked)`. The P3 briefing's `recovered` count reads the ledger too (same blindness — it is why B58's watch showed `recovered 0`). New tests model the removal the old fakes were blind to: ledger/walk disjointness, gate-off both ways, the arrival freeze, coalition filtering, the brief count and the idle debit. Re-test: any turn-3+ pre-roll long enough that the briefing block reports `recovered ≥ 1`, or a flown full sortie. Clean-wing returners (the W3 half) was never affected — it reads in-flight states — but stays unobserved pending a run where an egressing striker is inspectable

> With the same `living_battlespace_preroll` gate on, three P2 behaviors join the pre-roll:
> flights whose whole cycle predates your startup park their jets uncontrolled at their
> arrival field (registered in the unit map, so strafing them records real losses) — carried
> from the sim to generation by the residue ledger, since completed flights leave the ATO
> mid-march; strike-family flights spawned past their target fly a **clean wing plus pods**
> (v1 strips AAMs and tanks too — no weapon taxonomy to keep them by, recorded deviation);
> and AI units spawned en route carry burned-down fuel instead of full tanks. The gating,
> strip rule, fuel rule and ledger are pinned in `tests/retlab/test_living_battlespace.py`.

Needs a flight: same setup as B56 (gate on, turn 3+), plus a look at the F10 map and a ramp.

- **Pass:** at least one returned flight's jets sit parked at a friendly field they weren't
  parked at in a gate-off generation; an egressing strike-family AI flight shows no bombs or
  missiles on racks (pods may remain); no flood of "No parking for returned flight" log lines.
- **Fail signatures:**
  1. **A returner with full racks** — the strip's task/waypoint condition missed it (check
     `stores_expended`'s task set vs the flight's actual type).
  2. **Duplicate airframes** — the same flight appears both airborne and parked (the
     Completed-vs-InFlight branch split broke, or a flight got into both the ledger and the
     ATO walk; recorded-means-removed is the invariant, a flight takes exactly one path).
     The other shape of this: **a squadron shows more parked jets than it owns**, because
     the removal returned the airframes to the untasked pool and the idle-filler spawn
     rendered them a second time — check `idle_spawn_count` is debiting
     `AircraftGenerator.residue_airframes` (this failed on the first cut of the ledger).
  3. **Parking exhaustion pattern** — residue crowding out tasked flights' slots at a small
     field (residue spawns after tasked flights by construction; if tasked flights lose slots
     anyway, the generation order changed).
  4. **Residue on a carrier deck** — the naval guard leaked (§64/§72 interplay is deferred by
     design).
  5. **A mid-route AI flight with full fuel** — `use_estimated_fuel_for_ai` isn't reaching
     `setup_fuel` (check the state's `in_flight` property for that flight class).
  6. **Briefing says `recovered ≥ 1` but no residue anywhere** — the ledger seam broke
     (record at the sim's removal site → `residue_flights_for` at generation; both gate on
     `living_battlespace_preroll`, and the ledger clears at `begin_simulation`).
  7. **Residue at the wrong field after a mid-pause relocation order** — the arrival freeze
     broke (the ledger records the arrival at completion time precisely so an order placed
     while the sim is paused cannot teleport already-landed jets).

### B58 — Living battlespace P3: follow-on waves + pre-roll briefing · §89 · ⊘ RETIRED

**History:** 2026-08-16, spectator watch, Tacview `Tacview-20260816-104955`, session `c86c58dd` — the briefing block rendered with plausible counts ("Friendly: airborne 4, recovered 0, lost 3 / Enemy: airborne 8, lost 3 (assessed)", carried in the ACMI's own Comments field); waves activated AND flew at T+10.6m (carrier escorts), T+21.1m (a red Tu-95 3-ship) and T+32m (Hinds); activity continuous through the 96-minute watch; no parking exhaustion (0 overflow lines in dcs.log). The deep tail past a player egress follows from the same timers) (was ☐ UNTESTED, built 2026-08-15) (**2026-08-16 addendum, session `adoring-jepsen-b63803`:** that watch's `recovered 0` was the B57 structural starvation, not a real count — completed flights leave the ATO mid-march, so the walk-only count read 0 no matter what finished; the count now also reads the residue ledger, test-pinned. The rendering verification stands; the recovered figure re-checks itself on the next B57 pass

> With the gate on, the AI TOT spread extends past the desired mission length by the same
> phase-aware minutes as the pre-roll, so packages keep launching as/after the player
> recovers (both sides). The mission briefing gains "The air war so far today" — per-side
> airborne/recovered/lost counts at generation time. The widened window is pinned in
> `tests/test_missionscheduler.py::test_living_battlespace_widens_the_spread_window`; the
> briefing builder in `tests/retlab/test_living_battlespace.py`. What CI cannot see:
> whether the waves actually activate and launch in DCS, and parking behavior over the
> longer occupation (COLD waves sit uncontrolled on the ramp from t=0 until their push).

Needs a flight: gate on, turn 3+, fly a full sortie and stay on the ramp a few minutes after
shutdown (or watch the F10 map / Tacview tail).

- **Pass:** at least one AI package starts up and launches after your recovery; the DCS
  briefing screen shows the air-war block with plausible counts; fields still have parking
  for every tasked flight.
- **Fail signatures:**
  1. **The sky still dies behind you** — waves never activate (the silent-gate class: check
     the miz for `FlightLateActivationTrigger`/`FlightStartTrigger` entries with times past
     your egress; if present in the miz but nothing launches, the trigger conditions are the
     suspect — e.g. the hostile-airbase guard).
  2. **Parking exhaustion** — "No room on runway or parking slots" warnings clustering at
     one field, or tasked flights air-promoted because waves ate their slots.
  3. **The briefing block appears on turn 0 or with the gate off** — the empty-suppression
     broke.
  4. **Counts read absurd** (more airborne than the ATO has flights) — the state census is
     double-counting (a state class rename would do it; the census matches by name).

### B59 — Living battlespace P4: the voice net · §89 · ⊘ RETIRED

**Retired 2026-08-18** — the feature was removed on the DM's call ("the AI already uses the radio"), so there is nothing left to fly. It never got an in-game pass; it armed 48 scheduled calls on the 2026-08-17 Syria mission and whether any of them played was never established. See `retlab-features.md` §89 P4.

### B60 — Living battlespace P5: reactive red · §89 · ⊘ RETIRED

**Test 12 flown 2026-08-20 (Persian Gulf turn 1, `Tacview-20260820-203540` + `retribution_nextturn.miz` + `state.json`, session `a6e32389`) — the reaction can never launch: the generated group is uncontrolled, not late-activated, and `Group.activate()` is a no-op on it.** Everything upstream of the launch worked. Two alert flights were fragged and emitted (`Reaction Alert Bandar Abbas Intl BARCAP|34|45|F-5E Tiger II|`, `Reaction Alert Shiraz Intl BARCAP|34|44|F-4E Phantom II|`), six objectives were watched, and three of them lost units well inside the mission — MEERKAT's Shilka at t≈1360, KATYDID's whole SA-2 site at t≈1374, DUCK's Fire Can at t≈1413. With `reactionDelaySec = 420` the first launch was owed at t≈1780 and the mission ran to t=2580. **Neither alert flight moved one metre; both sit in the Tacview at their ramp position with a single t=0 sample.**

The launch path cannot work as built. `plan_red_reactions` parks the flight by pushing its TOT eight hours out, and its docstring assumes that "generates a late-activation group whose own trigger never matters — the plugin's early `activate()` is the only way it flies." It does not. A cold-start AI flight at an airfield fails every branch of `WaypointGenerator.should_activate_late()` (not non-COLD, no clients, not a fleet departure), so generation takes the `set_startup_time` path instead: `uncontrolled = True` plus a `StartCommand` trigger action fired by an `AITaskPush` at T+8 h. The miz confirms it — both reaction groups carry `["uncontrolled"]=true` and **no `lateActivation` key at all**, while 38 other groups in the same miz do have one. `activate()` only activates a late-activation group, so the plugin's one power is spent on a group that is already in the world with its engines off.

**Both fixed the same day, plugin-side.** `wake()` now tries `activate()` (late-activation groups) and `Controller:setCommand({id = "Start"})` (uncontrolled ones) and treats either succeeding as a launch, so generation is untouched and neither shape can be the one that silently fails. The harness gained `Controller:setCommand` and an `uncontrolled` group spec whose `activate()` is the no-op it is in DCS, and `test_an_uncontrolled_alert_flight_is_started_not_just_activated` pins the shape that was broken.

**Second, independent defect found in the same read: a static target's watched name never matches.** The emitter wrote JAGUAR's units as `0522 | Oil platform` … `0525 | Oil platform`, but the miz names those statics `0525 | Oil platform object` and that is the name the DEAD event carries. JAGUAR was struck first (B-1B carpet at t≈460, 13 minutes before any other watched objective) and the plugin could not have seen it. Vehicle-group names match exactly, so the watch works for SAM and armour targets and is dead for every scenery/static one. **Fixed** by watching both spellings in the plugin (the MANTIS `dcs_name_for_group` convention `commsjam` and `rednet` already resolve the same way), pinned by `test_a_static_target_death_is_watched_under_its_object_name`.

**Re-fly criterion, unchanged from the row's Pass below but now reachable:** strike any red objective your ATO is tasked against and stay ~10 minutes. `dcs.log` should carry `REACTRED|: armed`, then `<objective> struck; alert launch in 420 s`, then `<group> scrambling over <objective>` and `<group> on station over <objective>`. A `could not wake <group>` line means neither start path took and the fix is wrong; silence after `struck` means the schedule died.

**History:** built 2026-08-15; **2026-08-16 watch: double no-test** — the flown miz predated the package-custom-name fix (#842), so the plugin logged `nothing emitted; plugin idle`; AND the watched objective took zero losses anyway (the 2-ship F-14 strike was killed at its TOT by the site's HQ-7 + Shilka point defense, site untouched), so even the fixed plugin would not have triggered. Both emitter fixes are merged and verified emitted in the current cut. Next attempt: watch a softer objective (ammo/factory, not a PD-heavy SAM) or send a properly escorted/SEAD-supported strike so a watched unit actually dies

> With `living_battlespace_reactive_red` on (under the master gate), up to two REAL red
> alert flights (claimed inventory, tracked, losses count — deliberately not the §61
> untracked-freebie path) sit parked past the mission. When a red objective that blue's ATO
> actually targets loses a unit, one alert flight starts up after a ~7-minute tasking delay
> and flies a defensive patrol orbit over the struck objective. Positive-list discipline
> both ways; the fragged pool is the hard cap. The launch chain, one-shot latch, cap,
> airborne-gated orbit push and no-op are pinned in `tests/lua/test_reactivered_runtime.py`;
> the planner/emitter halves in `tests/retlab/test_living_battlespace.py`.

Needs a flight: both gates on, turn 3+, strike a red objective your ATO is tasked against,
stay in the area ~10 minutes.

- **Pass:** dcs.log shows `REACTRED|: armed`, then `<objective> struck; alert launch in N s`
  after your hits; ~7 min later a red pair starts up at its field and establishes an orbit
  over the struck objective (F10/Tacview); striking a second listed objective after the pool
  is spent logs exhaustion and launches nothing.
- **Fail signatures:**
  1. **No reaction ever** — `armed` absent (emitter gates/no watched objective: was your
     target actually a red TGO on the blue ATO?) vs `armed` present but no launch (the
     death-event name match — unit names vs the emitted list).
  2. **A reaction from an unlisted group, or over an unlisted point** — the positive list
     leaked (the positive-list safety invariant; treat as a stop-ship).
  3. **The alert flight launches at mission start** — its parked TOT/late-activation broke
     (check the 8 h TOT and the activation trigger time in the miz).
  4. **A wedged takeoff** — the orbit push hit a taxiing flight (the airborne poll gate
     broke; the §61 lesson).
  5. **Red flying offensive taskings from this path** — impossible by construction (the
     task is a home-area orbit), but if seen, stop and re-read the posture boundary.

### B67 — The front line counts the forces present · §90 rung C · ☑ VERIFIED

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **PASSES.** Kutaisi 0.75 morale × 883 armour value = 662;
Khashuri FOB 1.00 × 970 = 970. That predicts the line at 40.6 % of the way from Kutaisi; it
actually sits at **38.9 %** of the 98.2 km straight line (the residual is §90's terrain weighting
and salients, both also on). The line is displaced toward the weaker side, which is the whole
claim. Neither fail signature occurred: the front did not start somewhere unexpected, and this is
not an air-only campaign.

**History:** built 2026-08-17, session `629c250f`.

> Front position multiplies morale by `total_armor_value` instead of using morale alone.
> Two full-strength bases no longer meet in the middle when one is far better equipped.
> Locked by `tests/theater/test_front_line_weight.py`, including the air-only fallback.

An app check, not a flight. Load a campaign, compare the front-line position on the map
against each side's ground inventory.

- **Pass:** the line sits toward the weaker side where one CP holds materially more armour;
  campaigns where both sides are evenly equipped look unchanged from before.
- **Fail signatures:**
  1. **The front starts somewhere unexpected on turn 0** — a campaign author placed the
     front by tuning strength, and the armour weighting now overrides that intent. Note
     which campaign; it may need its inventory rebalanced or the setting off for it.
  2. **An air-only campaign pins the front to blue's doorstep** — the both-sides-zero
     fallback is not firing.

### B68 — Terrain slows the front line · §90 rung D · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-17, session `629c250f`.

> Front-line route segments crossing ground vehicles cannot occupy cost up to four times as
> much advantage per metre. An even fight still sits at the midpoint whatever the terrain.
> Locked by `tests/theater/test_front_line_terrain.py`.

An app check across several turns, on a map with real chokepoints — Caucasus mountain
passes or the Kola fjords.

- **Pass:** an advance visibly slows crossing a pass and speeds up in open ground; a front
  that starts at the midpoint stays there while the fight is even.
- **Fail signatures:**
  1. **The front start moved on an existing campaign** — the midpoint pinning is broken.
     This is the regression the design specifically guards against; compare turn-0 positions
     against a save from before.
  2. **Every segment reads difficulty 1.0** — the landmap is missing, or the route runs
     entirely inside the inclusion zone so the probe never finds bad going. Check on a map
     with water crossings.
  3. **A front sticks and never moves again** — 4.0 is too steep for a route that is mostly
     impassable. Lower `MAX_TERRAIN_DIFFICULTY`.

### B69 — The front bulges instead of running straight · §90 rung E · ☑ VERIFIED

**History:** built 2026-08-17, session `629c250f`.

> The FLOT is a bowed polyline with seven lateral samples, ground groups placed along it and
> the F10 map drawing it. Locked by `tests/missiongenerator/test_front_line_salients.py`.

Generate any front-line mission and look at the F10 map, then at where the ground units
actually are.

- **Pass:** the drawn front line has a visible bend, ground units sit on the bend rather
  than on a straight chord, and CAS runs still find them.
- **Fail signatures:**
  1. **Units spawn off the playable area or stacked** — the bowed point escaped the
     inclusion zone and the perpendicular-step fallback did not recover it. This is the
     highest-risk failure; note the campaign and the lateral offset.
  2. **The line is drawn bowed but the units are on the chord** — `conflict.bounds` is None
     on the path that placed them.
  3. **CAS flights orbit off the end of the front** — the CAS patrol legs read
     `left_position`/`right_position`, which should be untouched; if they moved, the
     endpoint pinning in `polyline` regressed.
  4. **The bulge is invisible** — every sector found the same room ahead. Expected on flat
     open maps; not a failure unless it is also absent on broken terrain.

### B70 — Sortie records reach the campaign · §91 · ☑ VERIFIED (2026-09-23, test 39; was ◐ PARTIAL)

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **every pass item and fail signature read.** The turn-2 SITREP carries `53 sorties, 34.9 hours airborne, 100 shots for 54 hits`. The kill counts match the recording exactly on both sides (17 blue, 4 red). `state.json` is 632 KB after 89 minutes with 136 records, so the 240-sample cap holds. No recorder error in `dcs.log`. Frame rate was not measured with the recorder off; tests 37 and 38's profiler runs cleared Lua of the slowdown.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the kill counts are right.** 136 records, 115 with a track. Blue's records credit 17 air kills and the recording shows 17 (8 Su-27, 5 JF-17, 2 Mi-8, 2 Mi-24), matching per shooter: Camp Bastion BARCAP 4, BULLSHARK Escort 4, the TARCAP 5, PORCUPINE Escort 2, QUAGGA SEAD Escort 1, FALCON Strike 1. Red's records credit 4 and the recording shows 4. The human's record (`PIG Strike … Pilot #1`, Flash) runs first_airborne 870 to 2610, 0 shots, `player_left` 2640 — he was shot down at t=2622. The wingman's record starts at 2640, when he took the group's anchor, as designed.

**2026-09-22, test 38** (Syria — Long Road to H3 turn 2, 37 min, one human in the SPARROW SEAD Viper lead from Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048), `Desktop\New test\38`) — **the vacated-seat fix holds.** The human went to spectator at t=1903 (`relinquished`). The record (`SPARROW SEAD|2|30|… Pilot #1`, Flash) stops at `last_seen` 1890 with `player_left` 1920, 49 samples; the AI that flew the jet on is not credited. Pilot #2 took the group's anchor at t=1920, as designed. The two-humans-in-one-group re-fly is still owed.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **270 records, one defect.** The human's record (`Aleppo OCA/Runway|2|30|… Pilot #1`, Flash) has 114 samples, 2 shots, 2 hits, and runs to t=3900 — but the seat was vacated at t≈2601 (`Player 'Flash' left`, spectator slot taken) and the jet flew on under AI to 0 fuel at 494 m near Aleppo. The recorder kept sampling it as an anchor with `player` still true, so §96 credits ~65 min for ~43 flown. **Fixed the same day:** the sweep now freezes a `player` record whose unit is neither named by `getPlayerName` nor listed by `coalition.getPlayers` (`player_left`), counts nothing for it, and resumes on a reconnect; harness-pinned, unflown. 42 records carry an empty track (parked airframes, by design).

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** the two-humans-in-one-group re-fly is still owed. On the WATCH card.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — **136 records; the host's own record is complete and the second human's is empty.** `King 1 | Flash`: 297 samples, 4 shots, 3 hits, 92.5 min, folded into both logbooks. `SMR|Maj Redneck|90-824`, in the same Viper group: `player: true` and his name from the shot events, 4 shots, 3 hits, 1 air kill, but `first_seen −1` and no track — the sweep never sampled him. The harness already passes four humans in one group, so this is a live-DCS difference: his unit answered `getPlayerName` inside the shot and hit events but not inside the sweep's `group:getUnits()` walk, and with the host holding the group's anchor he was treated as the AI wingman. Consequence: `record_mission` needs a track, so he got no lifetime profile (B114). Fixed the same day: the sweep now also takes `coalition.getPlayers` as the list of humans and treats a record already marked `player` as human, and the first event that carries the name fills it in (`tests/lua/test_sortie_recorder_runtime.py`). Re-fly with two humans in one group. Everything else reconciles: 16 blue air kills in the recording (14 AIM-120, 2 AIM-9) against the records' claims, and both §61 bandits are among them.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — **92 records, and the numbers reconcile with the recording.** Blue records claim 28 air kills; the recording shows 14 red aircraft and 13 Shahed-136s shot down by fighters, and the drones count as air kills, so 27 against 28 is the recorder and Tacview reading the same fight. The eight HARM shots sit on the four WEKA DEAD Vipers at two each. `state.json` is 672 KB. Three shapes to read a SITREP with: a wingman that never became the group's anchor carries `first_seen −1`, no track and only its events (`game/sortierecord.py` folds that to a 0 s duration); parked alert jets, the late-activated §61 templates and the Abu Musa Su-25Ts all get the two-sample stub; and the last sample of a jet that landed and shut down reads `fuel 0` (MUSK Strike, WOLFHOUND, MARLIN SEAD), which is DCS after shutdown, not a leak.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, no player, 59 min of sim) — **the
two-point question is answered by the recorder's own code, and the numbers are believable.**
134 records: 26 moved, 108 sat. A record whose aircraft never moves keeps two rows by design:
`sample_unit` overwrites the tail of a stationary run (`STATIONARY_M`), so every parked
squadron jet and every group that never taxied shows `first=30 last=3510` with two samples.
That is the test-14 and test-24 "stub", and it is correct, not a lost track. The 26 that moved
match the Tacview flight for flight. Shots 0 / hits 0 is right: no aircraft fired all mission
(20 SA-15 missiles from ground units, nothing from the air). Two shapes to know when reading a
SITREP: an AI group whose lead dies re-keys under the next unit (GIBBON Escort 23 shows
5.5 min under Pilot #2 after 52 min under Pilot #1), and a group DCS activates late still gets
a record from t=30 because `coalition.getGroups` returns it before activation. WATCH slot 2's
fail signature 1 ("idle ramp jets counted as flights") is therefore decided on the campaign
side, by counting records that moved rather than records.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **the test-14 defect reproduces on a second campaign and terrain.** 206
flights recorded. The player's own record is again complete and correct (52 track points, fuel
1.177 → 0.000, 7 shots / 2 hits, `ejected: true` matching the ejection event). But **122 of 206
tracks carry exactly two points, and 120 of those span more than 20 minutes** — the same
first-and-last reduction test 14 found, at 59 % instead of 73 %. A further 22 flights have no track
at all. 45 flights recorded shots (135 shots / 81 hits across both sides). Stays PARTIAL: the
question is still why a flight alive for forty minutes keeps two samples.

**2026-08-22, test 14 — the record arrives, but 77 % of it is a stub.** 158 flights written.
The player's own record is everything the feature promises: 76 track points, fuel 1.684 → 0.504
(above 1.0 at start because of external tanks, which is correct), 3 shots / 1 hit, `ejected: true`
matching the ejection event. **But 115 of 158 flights carry exactly two track points and 7 carry
none** — and the two are the endpoints of a full mission (`first=30 last=2490 t0=30 t1=2490`), so
these are not short-lived flights, they are flights whose track was reduced to first-and-last.
Ten flights recorded shots at all (24 shots / 12 hits across both sides). Stays PARTIAL: the
question is why a flight alive for 41 minutes keeps two samples.

**History:** built 2026-08-17, session `629c250f`.

> The base plugin samples every airborne flight every 30 s and counts shots, hits and
> ejections; the campaign SITREP reports the day's flying. Locked headlessly by
> `tests/lua/test_sortie_recorder_runtime.py` and `tests/test_sortie_records.py`, which
> model no DCS AI, physics or frame budget.

Fly any mission with several AI packages up, then read the next turn's SITREP.

- **Pass:** the SITREP carries a sortie line whose numbers are plausible — sortie count
  matches the packages that flew, hours are in the right order of magnitude, shots and hits
  are non-zero on a mission where something was fired.
- **Fail signatures:**
  1. **No sortie line at all** — the recorder never started. Check `dcs.log` for a Lua error
     at load; check `sortie_recorder.lua` is in the base plugin's work order ahead of
     `dcs_retribution.lua`.
  2. **Frame-rate drop on a dense mission** — the 30 s sweep is too expensive at this group
     count. Measure before and after with the recorder disabled; raise
     `SAMPLE_INTERVAL_S` rather than removing the feature. Dense TIC campaigns are the risk
     case (see the GLSCO framerate finding).
  3. **`state.json` grows very large** — the 240-sample cap is not holding, or a long mission
     has far more flights than expected. Check the file size after a three-hour mission.
  4. **Counts are wildly wrong** — shots counted per unit rather than per flight, or hits
     attributed to the wrong group. Only the group lead is sampled; shots and hits come from
     the event initiator's group.

> **Test 7 (2026-08-17) partial read.** The records reached `state.json` and the counters
> were sane, but `flights` also carried every AAA piece and Avenger that shot at the
> package, plus one entry keyed `""` whose type was `weapons.shells.Rh202_20_HE` — the
> shot/hit handlers recorded whatever DCS named as the initiator. `record_for` now creates
> a record only for a named unit whose `getDesc().category` is AIRPLANE or HELICOPTER; an
> existing record keeps counting either side of a kill. Add a fifth fail signature: **ground
> units or blank keys in the sortie list.**

> **Test 8 (2026-08-18) second read — the SITREP claimed a 359% hit rate.** The line read
> `93 sorties, 119.2 hours airborne, 106 shots for 381 hits`. Both counts were individually
> right and not comparable: DCS raises one `S_EVENT_SHOT` per weapon released but one
> `S_EVENT_HIT` per **impacting object**, and a cluster weapon's submunitions are different
> objects from the one that left the rail — two CBU-105 releases scored 68 hits on one
> Su-24MU. Only 1 record of 114 had hits with no shots, so this was never the
> guns-raise-no-shot-event problem it looks like. A hit is now counted only against a weapon
> the recorder saw fired, and only on that weapon's first impact, so `hits <= shots` always
> and the line is a real hit rate. Gun hits are no longer counted at all — there is no shot
> event to rate them against. Sixth fail signature: **hits exceeding shots, or a strike
> sortie reporting zero hits where it clearly destroyed something.**

> **Test 12 (2026-08-20) third read — the records are clean, and two thirds of `state.json` is parked scenery.** (Persian Gulf turn 1, session `a6e32389`.) Both earlier defects stay fixed: 158 records, no ground units, no blank keys, and `hits <= shots` on every one. The player's own record is exactly what the feature promises — F-16CM, 42.5 min, 343 NM, 4 shots for 4 hits, fuel 1.642 → 0.760, recovered. Two new findings:
>
> 1. **Idle-ramp jets are recorded as flights.** `_spawn_unused_for` parks a squadron's untasked airframes as 1-ship `Completed` BARCAP groups, so the recorder's sweep sees them as airborne-category groups and anchors one per group. 82 of the 158 records are aircraft that never moved — 20 Su-24M and 12 Mirage F1EQ at Kish, 16 F-4E-45MC and 6 F-5E at Bandar Abbas, 8 Su-25T at Abu Musa, 4 IL-76MD at Shiraz, 12 helicopters at Qeshm — each carrying 86 identical track points. **`state.json` was 1.18 MB, of which `sortie_records` was 99% and the stationary tracks alone were 68%.** That is fail signature 3 arriving by a route the row did not anticipate: not the sample cap, the population. Cheapest fix is to drop a track sample that has not moved since the last one, which also collapses a real flight's holding pattern; the surgical one is to skip units whose flight state is `Completed` at generation.
> 2. **The `fuel` column is a constant wherever `ai_unlimited_fuel` is on.** 101 of 143 tracked flights logged one unchanging value end to end, including an F-14A that flew 280 NM at 9,144 m on a flat 1.000. Not a recorder fault: the setting writes `SetUnlimitedFuel(True)` at `group.points[0]` (142 occurrences in this miz), turned off again at the join point and racetrack start — which is exactly why the 42 flights that did burn are the ones between those waypoints. Nothing to fix in the recorder, but a consumer must not present that number as a fuel state, and the SITREP should not average it.
>
> Also confirmed by design, worth writing down because it looks like a bug: a wingman that shoots or ejects gets a record with `first_seen = -1` and an empty track (only one AI jet per group is anchored). 13 records here. Any consumer computing hours airborne must skip `first_seen < 0` rather than treat it as t=0.
>
> **Both fixed the same day, and the fixes were replayed against this mission's own `state.json`.** The recorder collapses a stationary run to its two endpoints (`STATIONARY_M = 25`) and `SortieRecord.flew` requires `MIN_SORTIE_DISTANCE_M = 1000` of sampled track before a record is a sortie or contributes hours; `sorties_flown` and `sortie_summary` both read it. On test 12's file that is **1,183,550 → 377,377 bytes** and a SITREP line of **"46 sorties, 28.0 hours airborne, 84 shots for 26 hits"** in place of "145 sorties, 96.7 hours". Pinned by `test_a_parked_aircraft_collapses_to_the_run_endpoints`, `test_a_parked_aircraft_that_takes_off_records_normally_again` and `test_a_parked_airframe_is_not_a_sortie`. **Seventh fail signature: a sortie count in the same order of magnitude as every aircraft in the mission, ramp included.**
>
> **Re-fly criterion:** the next turn's SITREP sortie count should be close to the number of packages that flew, not to the theatre's aircraft count, and `state.json` should be a few hundred KB rather than over a megabyte.

### B78 — The escorts let go of a package the player is leading · planner shape · ☑ VERIFIED (2026-09-16, DM, test 33)

**2026-09-16, DM verdict in chat (session `9148a88a`)** — **VERIFIED.** "B78 is good and proven in the multiplayer test" — test 33, the DM leading the MAVERICK Viper strike with an F-15C escort and a Hornet SEAD escort on a listen host. Measured off the recording afterwards: from the join at t≈1800 to the split at t≈4500 the three escorts stayed 0.2–9 km off the DM's jet through the target run, then at t=4800 they were 82–125 km away and by t=5100 160–200 km, while the DM recovered at Ramat David. Neither fail shape (formating home, or breaking off at the join) occurred. Off the WATCH card.

**What the same measurement also showed, which is not this row:** the escorts did not reach their own recovery. The package's route was 1,036–1,296 km. The F-15C (internal fuel only, no tanks fitted, a `REFUEL` waypoint after the split that AI does not fly) ran from 0.61 at t=3600 to 0.04 at t=4920 and its lead ejected near Wujah Al Hajar; the Hornets (one centreline tank) landed at Rene Mouawad with 0.08, a Lebanese field that is not a control point in this campaign, on DCS's own bingo divert. The DM's Viper, on external tanks, came home with 0.72. This is the §46 revert's accepted consequence (re-convergence work order C: tanker tasking is upstream's, nothing fits tanks; do not re-litigate), recorded here as the first measured instance on a long-range package.

**History:** built 2026-08-18, from test 7 (Sinai turn 1, `retribution_nextturn.miz` +
its Tacview and `state.json`).

> Escort release is a user flag, and the only thing that raised it was a `RunScript` on the
> package primary flight's SPLIT waypoint. DCS does not run route tasks for a
> client-occupied group, so when the human leads the package the flag never rose, the
> escorts' `Escort` ControlledTask never stopped, and they formated on the player past his
> split. Measured on that mission: both EA-18Gs were briefed to recover on CVN-71 and
> instead followed the player's F-16 to Ramon Airbase (final §91 track points 80301/328863
> and 80237/328483 against the boat's landing waypoint). The mission-level backstop only
> fires if the primary flight *dies*, and its `AITaskPush` list omitted `ESCORT_JAMMER`
> entirely. Fix: a hidden 15 km trigger zone on the primary's SPLIT point plus a
> planned-split + 15 min time backstop raises the same flag from a mission trigger, which
> runs whoever is in the cockpit; the push list is now `is_escort_type`. Pinned in
> `tests/missiongenerator/aircraft/test_split_release.py`; verified in a regenerated `.miz`
> as `c_part_of_group_in_zone(273, 69) or c_time_after(5670)` → `a_set_flag("split-...")`.

**2026-08-21 — that fix REPRODUCED the opposite failure and has itself been fixed.** Two
flown sessions: the SEAD escort broke off at the JOIN and called its own SPLIT index on the
radio ("passing waypoint 4"). Cause: `PackageWaypoints.create` derives join AND split from a
single `join_point`, perturbed ≤1 nm each, so the primary flies the release zone twice and
the inbound pass released the escorts before the package had ingressed. Measured in the
supplied `retribution_nextturn.miz` (Iraq): zone 41 r=15000 at the SPLIT (105186, 23140),
primary JOIN at (104377, 24261) — **0.75 nm from the centre**; trigger 105
`c_part_of_group_in_zone(234, 41)` → `a_set_flag` → trigger 106 `a_ai_task(235, 1);
a_ai_task(236, 1)` → each escort's `SwitchWaypoint goToWaypointIndex 5`, and wp4 on
ARMADILLO SEAD Escort is SPLIT. No radius is small enough to fix this — the two points are
the same point. The zone now ANDs with `split_release_gate`, the midpoint of the planned
join→split leg (774 s / 2257 s → 1515 s on that mission), which the inbound pass cannot
reach. An ungateable release drops the zone and keeps only the backstop.

**Affects AI-flown packages too.** The trigger is emitted whenever the primary flight has
client SLOTS, not whether a human occupies one, so a player-slotted flight the AI ended up
flying got the same early release. A package whose primary has no client slots was never
affected — it releases from the `RunScript` on the SPLIT waypoint, which is route-order
based and has always been correct.

Lead a package that has an escort or escort jammer on it and fly the whole profile home.

- **Pass:** at the split point the escorts break off and route to their own recovery field.
- **Fail signatures:**
  1. **They still follow you home.** The zone was missed and the backstop had not elapsed —
     check the `.miz` for a `SplitRelease<n>` trigger at all; a package whose primary is AI
     deliberately gets none.
  2. **They leave at the JOIN, calling their own split waypoint number.** This is the
     2026-08-21 regression above: the release zone fired on the inbound pass. Check the
     `.miz` trigger for a `c_time_after` gate ANDed to the `c_part_of_group_in_zone`, not
     `or`-ed to it. Do NOT answer this by shrinking the zone — join and split are the same
     base point.
  3. **They leave far too early on a slow sortie.** The time backstop fired. It is 15 min
     past the *planned* split, so a very long delay on station will trip it.
  4. **The escort jammer keeps a SAM in weapons-hold long after the strike.** §77 pulses only
     while the jammer is within 40 NM — an unreleased escort parks it there. Read with B31.

### B79 — Ground-level waypoints read the field's elevation · §8 · ☑ VERIFIED (2026-09-16, audit)

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED off six generated missions, both coalitions.** Every routed flight in tests 24, 26, 30, 31, 32 and 33 carries its takeoff and landing points at the field's elevation from `resources/airport_imagery` (Beslan 524 m, Tbilisi-Lochini 480 m, Mineralnye Vody 320 m, Kerman 1,751 m, Gaziantep 699 m, Damascus 612 m, Incirlik 48 m, Ramat David 41 m, all within 5 m), 232 waypoints checked against the table. The only zeros left are the one-point parked-ramp groups (the untasked squadron jets and the QRA templates, which never fly) and the neutral civilian traffic, which never enter `WaypointGenerator`, exactly the row's third fail signature. The AI landed on those fields in every recording (test 24: 26 landings; test 33: 19). The cockpit half is the DM's B90 verdict: the DED reads the field's elevation on the Viper's steerpoints. Off the WATCH card.

**History:** built 2026-08-18, from test 7. Upstream-inherited, not a fork regression:
`WaypointBuilder.land()` is byte-identical to `upstream/dev`.

> Every takeoff, landing and divert waypoint was written at 0 — RADIO for landing and divert,
> BARO for takeoff, where 0 is sea level. 105 of the flown mission's 192 air waypoints sat at
> 0. The number reaches the cockpit through the kneeboard card and the DTC steerpoint, so a
> field like Ramon Airbase (619 m) read as below the jet's own nav solution. They now carry
> the OSM/DEM field elevation from `resources/airport_imagery/<terrain>.json` (the table the
> ATIS already uses for QFE) as BARO. Carriers, FARPs and FOBs stay at 0 MSL by decision —
> a deck is within ~20 m of sea level and there is no elevation record for the rest.
> Repaired at generation time as well as plan time, because the flight-plan layout is pickled
> into the save and a campaign in progress would otherwise keep the old 0 forever.
> Verified by regenerating a live Sinai save: Ovda 437 m, Ramon Airbase 619 m, Melez 306 m,
> Wadi Abu Rish 300 m, Wadi al Jandali 228 m, Ramon International 69 m, carrier 0.

Fly any sortie off a field that is not at sea level and read the waypoint list.

- **Pass:** the takeoff and landing steerpoints show the field's real elevation in the jet,
  on the kneeboard and in the ME. The target waypoint still reads 0 AGL — that one is
  deliberate, it is what lets a player slave a pod to the mark.
- **The landing half did not work until 2026-08-20 and is the thing to check first.**
  `LANDING_POINT` was listed in `GROUND_MARKED_WAYPOINTS`, so every client flight had its
  landing steerpoint zeroed after the planner wrote the field elevation — kneeboard, .miz
  and DTC alike, while the AI flew the real number. Flown that day off Al Minhad: the card
  read `Takeoff 191` over `Land 0`, same field. Fixed by removing it from the tuple.
  Fail signature: Takeoff and Land disagree at the same airfield.
- **Fail signatures:**
  1. **Still 0 at a field above sea level.** No entry for that airport in the terrain's
     imagery JSON. GermanyCW is the weakest coverage (135 of 227).
  2. **The AI will not land.** The landing waypoint moved from 0 RADIO to field-elevation
     BARO; the airdrome id is unchanged, so this should not happen, but it is the thing to
     watch on the first pass.
  3. **A QRA intercept or red scramble jet still reads 0.** Known and not fixed — those
     groups are spawned outside `WaypointGenerator` and never reach a kneeboard.

> **Follow-on found the same day, before any flight.** Moving these off 0 broke the bulk
> altitude setter. `bulk_editable` decides what "Apply to all" moves by asking whether the
> waypoint was planned above the deck, and its own comment recorded the assumption that
> takeoff, landing and divert are "planner-seeded at 0 ft". They are not any more, so at any
> field above sea level the setter would have overwritten the field elevation with the cruise
> altitude — corrupting exactly the steerpoint this row exists to fix. Takeoff and landing are
> now named in `BULK_ALTITUDE_SKIP_TYPES`; divert is conditional, because an *off-map* divert
> is an exit vector planned at cruise and moving it is the point, so it is separated by its
> control point rather than by altitude. Pinned in `tests/test_bulk_waypoint_altitude.py`.
> Read this row with **Q3**.

### B81 — SEAD-evasion scoot distance is a campaign setting · MANTIS · ✅ CLOSED

> **Closed 2026-09-12.** The setting was a MANTIS plugin option and went with the bridge.
> Skynet's shoot-and-scoot distances are its own `actMobile*` options, unchanged from upstream.

**History:** built 2026-08-18, off the test 8 measurements.

> When a HARM is inbound, MOOSE puts the SAM alarm-green and drives it. The distance was
> hardcoded at 100–300 m inside `SEAD:onafterManageEvasion` with no setter, so a campaign
> could not ask for real dispersal. `seadScootRadiusM` (100–1000 m, default **300** = MOOSE's
> own value) now overrides it. The bridge wraps the shared `CONTROLLABLE` method and rewrites
> the radius only for the SEAD signature; MANTIS' own HQ/EWR relocation and the other
> Diamond caller are matched out and left alone, pinned by
> `tests/lua/test_mantis_sead_scoot_radius.py`.

> **What test 8 measured, for calibration.** The BUK-M3 site took its first HARM at
> 15:01:16; the first unit had moved 25 m by 15:02:01. That 44 s is not the reaction time —
> it includes DCS route acceptance and the ~5 s of driving 25 m takes at MOOSE's 20 km/h, so
> the switch-off was a few seconds earlier. The site is **High** skill, whose MOOSE reaction
> band is **20–40 s** (`SEAD.TargetSkill`), and the measurement sits at the top of it. It
> moved 233–518 m, and fired **11 missiles before the scoot and 25 after**.
> The stock 300 m is not costing a site its engagement, so raise this only for a campaign
> that wants the site genuinely hard to re-find.

Set it on a campaign with a radar SAM the AI will actually HARM, then watch one site.

- **Pass:** the site drives visibly further than the stock ~300 m, and still comes back up
  and engages afterwards.
- **Fail signatures:**
  1. **The site is still shooting while strung out mid-drive.** The suppression window and
     the drive are decoupled — alarm goes red when the window ends whether or not the move
     finished. At MOOSE's 20 km/h, 300 m takes ~55 s against a window of roughly 1.5–2 min,
     so anything much above ~600 m will still be moving when it goes weapons-free. This is
     the reason for the 1000 m cap, not a bug.
  2. **EWRs or the HQ start wandering further too.** The signature match caught the wrong
     caller — the tests cover this, so suspect a MOOSE version bump.
  3. **Nothing changes at all.** MOOSE changed the hardcoded 300, so the match no longer
     fires. `dcs.log` carries a `SEAD scoot radius` line the first time it rewrites; no line
     means it never matched. Degrading to stock is deliberate.

### B82 — The AWACS orbits at a field it can actually fly from · planner shape · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-19 from test 9 (Syria, `operation_desert_trident`, save
`test.retribution`).

> #879 made the land AEW&C anchor prefer a field that hosts an AWACS, but only on the
> **fronted** branch. A theater with **no front line** takes the other branch —
> `closest_friendly_control_point()`, the CP nearest the enemy — which asked nothing about
> basing. Reproduced off the save: blue had **0 front lines**, the anchor took **Ben Gurion**
> (hosts no AWACS), and the wing's only land AEW&C squadron was an **E-3A at Akrotiri
> 182 NM away**, which flew that each way to reach its own orbit. Both anchors now share
> `ObjectiveFinder._aewc_hosting_anchor(forward=...)`: same walk over unthreatened land CPs
> hosting a usable AWACS, rear-most with a front, forward-most without. Measured on that save,
> the E-3A's transit goes **182.2 NM → 0.0 NM**. Falls back to the stock pick when nothing
> hosts one, so an all-carrier wing is unchanged.

> **The trade, stated rather than hidden.** The orbit moves back to the field the aircraft
> flies from, so its coverage centre moves back too — here from Ben Gurion to Cyprus. What is
> bought is on-station time; what is given up is forward radar reach. If a campaign wants the
> orbit forward of its AWACS base, this is the knob that made that impossible and the row to
> reopen.

Play a turn on a **front-less** campaign whose AWACS is not at the field nearest the enemy.

- **Pass:** the AEW&C package launches and orbits at or near the field it took off from; the
  transit is short.
- **Fail signatures:**
  1. **A long transit again.** The anchor fell back to the stock pick — check whether any
     unthreatened field hosts an AEW&C squadron with untasked aircraft.
  2. **The AWACS orbits far behind the fight.** The forward pick found only a rear hosting
     field. Working as written; note the campaign, because it is the trade above biting.
  3. **A fronted campaign changes.** It should not — only the front-less branch moved.

### G43 — A crash in a radar's view never stalls a Skynet network · Skynet return · ☑ VERIFIED (2026-09-23, test 39; was ◐ PARTIAL)

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the pass criterion holds on a crash-heavy flight.** `state.json` carries 56 `crash_events`, many inside red Skynet coverage (the S-350, Buk and Kub sites around Shindand and Herat), and `dcs.log` has zero `doesn't exist` lines. The flown `skynet-iads-compiled.lua` carries the guard (`if target.object and target.object:isExist() then`).

**2026-09-22, test 38** (Syria — Long Road to H3 turn 2, 37 min, one human in the SPARROW SEAD Viper lead from Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048), `Desktop\New test\38`) — **found from the log; fixed and harness-tested the same day.** A red Mi-24P crashed at t=347. From t=349 to mission end `dcs.log` carries `MIST|doScheduledFunctions … skynet-iads-compiled.lua:2770: Static doesn't exist` 174 times, about every 10 s. A blue radar kept reporting the wreck. Skynet's `getDetectedTargets` skips a nil `target.object`, but the wreck is non-nil and gone, so `getTypeName` raised and aborted `SkynetIADS.evaluateContacts` part-way through every cycle. For 31 minutes no early-warning radar on that side cued a SAM site, and no site ran its end-of-cycle go-dark. Upstream Skynet (`walder/Skynet-IADS`, master and develop) has the same line.

- **Fix:** `target.object and target.object:isExist()`, a second fork line in the compiled build (`retlab-skynet-return-notes.md` §4). `tests/lua/test_skynet_engine.py` runs the real method: a wreck is skipped and the live contacts after it are still returned. Both tests fail without the guard.
- **Setup:** none. Any mission in which an aircraft crashes inside a Skynet radar's coverage.
- **Pass:** `dcs.log` has no `Static doesn't exist` from `skynet-iads-compiled.lua`.
- **Fail signature:** the line returns from another line number — another object Skynet reads before the guard. Record the line.

### B84 — Front-line groups move and return fire instead of holding · §8 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-19 from juanjux/dcs-retribution#79, verified live in our tree
before fixing. Two causes: a negative hold normalising to 23h59m, and defenders being held
until the *enemy's* CAS TOT.

- **What CI cannot exercise:** whether the groups actually manoeuvre and shoot in DCS. The
  emitted hold duration is unit-tested; the behaviour is not.
- **Setup:** any campaign with an active front. Fly or fast-forward a turn and watch a
  front-line sector, ideally one where the enemy has a CAS package fragged (that is the case
  that used to freeze the defenders).
- **Pass:** front-line groups reform, advance per their stance, and return fire when engaged.
  A defending group that is shot at shoots back promptly.
- **Fail signatures:**
  1. **Groups sit on their spawn all mission.** Check the generated `.miz` for a `Hold` task
     with a large `stopCondition.duration` — 86340 is the old bug's signature.
  2. **Defenders idle while attackers move.** The stance gate regressed.
  3. **Attackers step off before their own CAS arrives.** The `AGGRESSIVE` wait was removed
     too — that one is intended behaviour, not a bug.

### B88 — Tankers orbit at their own base, and each carrier gets one · planner shape · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-19, the tanker half of the B82 defect.

> `refueling_targets` was a single element — `closest_friendly_control_point()`, the CP
> nearest the enemy — with no basing awareness and, unlike AEW&C, **no front/no-front
> branching at all**. Measured on the flown save (`test.retribution` turn 2, Caucasus, which
> HAS a front line): both tankers stationed on **UNOMIG Sector HQ**, a sector HQ, with the
> KC-135 **151 NM** away and the carrier's A-6E **173 NM** off its own boat.
>
> Now one station per friendly carrier plus one land station, the shape AEW&C already used.
> The land anchor prefers the most forward field that hosts a tanker, via the same
> `_support_hosting_anchor` #899 added. Re-planned on that save both transits go to
> **0.0 NM**, and the generated mission puts BOOM receivers (B-52H, F-22A, F-15C, F-16CM,
> F-15E) on the KC-135 and PROBE receivers (F/A-18C, EA-18G, F-14B) on the A-6E.

> **One trap found while building it, kept as a test.** Giving the land station its own
> per-method fan-out made it reach for the carrier's A-6E for the probe slot and drag it
> **314 NM** off the boat — worse than the defect being fixed. The land station now only
> fans out over methods a **land** tanker can serve; the boat's own station covers the rest.

Play a turn on a wing with both a land tanker base and a carrier.

- **Pass:** one tanker package per carrier plus one ashore; each tanker orbits near the base
  it launched from; boom receivers route to a boom tanker and probe to a probe tanker.
- **Fail signatures:**
  1. **A tanker crossing the theater again.** The land anchor fell back to the stock pick —
     check whether any unthreatened field hosts a tanker squadron with untasked aircraft.
  2. **A carrier tanker at the land station.** The land fan-out's basing filter is not
     holding; that is the 314 NM trap above.
  3. **More tanker packages than you want.** One per carrier is the design. On a two-boat
     wing that is three packages, and their escorts are threat-gated (#879) so an
     unthreatened station should not consume fighters.
  4. **Probe receivers with no tanker.** The wing owns no probe tanker ashore and has no
     carrier; the method is skipped rather than filled badly.

### B72 — A pilot down beside a base is resolved without a rescue flight · CSAR (#929 Phase 5) · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, adopted 2026-08-17 from upstream `82b3ab10`. Never flown.
- **What it is:** a pilot who comes down within `csar_control_point_radius` (default **15 nm**) of any control point never becomes a rescue target. Inside a friendly one they walk back and go straight into recovery; inside an enemy one they are captured and held at that base.
- **What CI cannot exercise:** whether 15 nm is the right number on a real map. This is the setting most likely to be wrong by feel rather than by logic — on a dense map with closely spaced fields, a 15 nm circle around every control point can cover most of the theater and quietly delete CSAR from the campaign.
- **Setup:** set `csar_ejection_chance` to 100. Eject **twice**: once ~10 nm from a friendly field, once ~10 nm from an enemy one. Pass the turn and read the messages and the roster. Then count how much of your campaign map falls inside 15 nm of *something* — if it is most of it, lower the setting and say so here. ~25 min, no flying needed.
- **Pass:** the friendly-side pilot is in recovery with no CSAR package fragged. The enemy-side pilot is MIA and held at the enemy base. Neither appears on the map as a rescue target.
- **Fail signature:** a rescue package fragged for a pilot sitting 8 nm from his own runway. Or the opposite and worse: no CSAR packages appear anywhere all campaign, because every ejection is inside somebody's 15 nm circle.

### B74 — The briefed hover follows the player hover-height setting · CSAR (#929 Phase 5) · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, this is the second time this exact defect has been in front of us. On adoption (2026-08-07) the pickup waypoint briefed 100 ft against MOOSE's 20 m winch ceiling, so a crew flying the waypoint exactly could never hoist and DCS said nothing. Fixed by pinning 50 ft. Phase 5 then turned that ceiling into a setting spanning 5–100 m, which reopens the same gap at the bottom of the range — the guard test would have kept passing, because it was watching MOOSE's constant rather than the setting. `briefed_hover_altitude()` now clamps to 80 % of the setting.
- **What CI cannot exercise:** that the winch actually fires. The test proves the numbers are ordered correctly; only a hoist in the cockpit proves MOOSE agrees.
- **Setup:** three runs, `csar_hover_extraction` ON, flying the rescue yourself. Leave `csar_player_hover_height` at 20 and hoist. Set it to 5 and hoist. Set it to 100 and hoist. Fly the briefed waypoint altitude each time, do not eyeball it. ~30 min.
- **Pass:** the winch runs at all three settings when the helicopter is at the briefed altitude.
- **Fail signature:** the hoist never starts and no message explains why — the same silent failure as the original defect. Note which setting it failed at: a failure only at 5 m means the 80 % clamp is not margin enough at the bottom; a failure at 100 m means something else caps the hover.

### B75 — The ATO stops spending its escorts on the wrong packages · planner shape · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-17, from a live save (`brady.retribution`, Sinai turn 1, Blufor
Current vs Redfor China 2020) whose ATO the DM flagged as badly shaped.

> Four planner defects found by dumping that ATO, all in upstream code. **(1)** `PlanCas`
> proposed `SEAD_SWEEP` with no `escort_type`, and `PlanAewc`/`PlanRefueling` proposed
> `ESCORT` the same way. An untagged proposal is fulfilled as a *primary* flight: never
> threat-gated, never prunable, and an unfillable one scrubs the whole package — so every
> CAS package mandatorily consumed a Growler flight, and a tanker with no free fighter
> would have taken the tanker down with it. All twelve of the wing's EA-18Gs were spent
> this way while the one DEAD package, against an EWR, flew with no support at all.
> **(2)** No package-level cap on suppression flavours — see B52. **(3)** The land AEW&C
> anchor was picked purely on distance-from-threat, choosing a field 1.1 NM safer than the
> one the wing's single E-3A actually flew from and sending it 245 NM to orbit beside a
> third field; `ObjectiveFinder.aewc_land_anchor` now prefers an unthreatened field that
> hosts an AEW&C squadron, falling back to the stock pick. **(4)** Naval BARCAP rounds
> chained on raw station-departure while land rounds subtract `barcap_overlap_time`, so
> carrier and LHA CAP had a hole between every round (measured 60 min against 45 on land,
> both coalitions). Separately, heavy bombers lost the `CAS` lane — a B-52 fragged onto a
> front line is a danger-close carpet — extending the existing Armed Recon exclusion;
> `BAI` and the §32 Arc Light carpet (a Strike target) are untouched.
>
> Measured on that save, re-planning the same turn before and after: blue flew one more
> package with six fewer aircraft and **two more shooters**, the E-3A's transit fell from
> 245.2 NM to 31.3 NM, packages carrying more than one suppression flight went 5 → 0, and
> the Growler moved onto the DEAD package. Pinned in `tests/commander/test_single_sead_flavour.py`,
> `tests/test_aewc_targets.py`, `tests/test_missionscheduler.py`, `tests/test_aircraft_tasking_roles.py`.

Only (2) is gated (`single_sead_escort_flavour`, planner suite, default OFF); (4) is a
no-op at the stock `barcap_overlap_time` of 0. The rest are unconditional bug fixes. Play a
turn on a wing with a small dedicated-jammer squadron and read the ATO before flying.

- **Pass:** No AEW&C or tanker package carries an escort unless the route is genuinely
  threatened. The AWACS orbits near the field it launched from. DEAD packages against live
  radar SAMs get the suppression flight before a vehicle-group BAI does. Carrier CAP rounds
  overlap rather than leaving a gap. No heavy bomber appears on a front line.
- **Fail signatures:**
  1. **Fewer packages planned than before.** Making an escort prunable should free jets, not
     cost packages — if the count drops, a package is scrubbing on a missing *primary*.
  2. **No AWACS at all.** The escort is now threat-gated; if the AEW&C package itself
     vanished, the cause is upstream of this change.
  3. **The AWACS still transits the theater.** Its home field is threatened, so the helper
     fell through to the stock rear pick. Working as written; note the campaign.
  4. **SEAD cover feels thin.** Same trade as B52 — the answer is to reinstate the sweep for
     specific callers, not to ungate the trim.

### B76 — A mixed boom/probe wing gets a tanker of each · U15 reinstated · ☑ VERIFIED (2026-09-23, test 39; was ◐ PARTIAL)

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the negative case passes.** Blue owns two KC-135 squadrons (boom only) and flies probe receivers (VMFA-251 Hornets, the F-14B(U) squadron, IV (AC) Squadron Harriers) beside boom ones. Turn 1 fragged exactly one tanker (`Camp Bastion Refueling`, KC-135), the package intact; the turn-2 save's ATO has the same single KC-135, and no probe flight on either turn carries a REFUEL leg. With test 37's positive case (one tanker per method, 31 km apart), both halves are observed.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **the positive case held.** The one `Incirlik Refueling` support package carried two flights, `|2|1|` KC-135 MPRS (probe) and `|2|2|` KC-135 (boom), on separate racetracks: orbit centres 37.58N 35.22E and 37.85N 35.11E off the recording, 31 km apart, both north of Incirlik and clear of the belt. Texaco 3 and Arco 3 on the kneeboard, one TACAN each. The negative case (a single-method wing still gets exactly one) is not exercised, so the row moves off REGRESSED to PARTIAL rather than VERIFIED.

**2026-09-17 — the fail signature, reproduced headless on two real saves.** Long Road to H3,
`autosave` turn 1 and `brady` turn 3, blue replanned read-only through the full planner: the
land station got **two boom KC-135s and no probe tanker**. The wing counts probe 8 / boom 3, so
the methods list is `[probe, boom]`; the first tanker was unconstrained and took the best
squadron (the boom KC-135), and the loop then proposed `needed[1:]` -- boom again. The KC-135
MPRS was never asked for, leaving the Incirlik Mirage 2000Cs without a land tanker. **The
08-21 VERIFIED below was a batch call and never exercised this**: the row's own history says it
was never flown in either shape. Fixed on branch `claude/u15-probe-tanker` -- every tanker is
constrained to one method, the first included; the type is the one the planner ranks best at
the station; and a second tanker is ranked from the station, not the first tanker's field.
Replayed on all 8 saves x both sides: the bug was live on 4 (every mixed wing with a land probe
tanker), each now boom + probe, and nothing else changed. Needs this
row re-run in-game to go back to VERIFIED.

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-06-26, reverted 2026-08-09 with the rest of work order B, reinstated 2026-08-17 on a fresh call in a different shape. Never flown in either shape.
- **What it is:** the coalition's squadrons are counted by refuelling method; one theater tanker is proposed per method a land tanker can serve, every one constrained to its method (the first too, since 2026-09-17). The first is mandatory, the rest optional; when no method qualifies the single unconstrained pre-U15 tanker is proposed, so nothing regresses when the data is missing. Extra tankers step 15 NM further back from the threat so they do not share a racetrack.
- **What CI cannot exercise:** whether the second tanker ends up somewhere a receiver can actually reach, and whether two orbits 15 NM apart read as separated in the cockpit and on the F10 map. The tests prove the proposals and the slot arithmetic, nothing about the geometry being flyable.
- **Setup:** a campaign whose blue wing flies **both** boom and probe receivers and owns a tanker for each — a mixed USAF/USN wing is the natural case (Vipers and Eagles on the boom, Hornets and Tomcats on the drogue). Pass a turn, read the ATO, then look at the two orbits on the map. ~20 min, no flying needed for the first read. **Also run the negative case:** a wing with probe receivers but only a boom tanker. ~30 min total.
- **Pass:** two `Refueling` flights in the one support package, one serving each method, on visibly separate racetracks both outside the threat rings. In the negative case, still exactly one tanker and the package intact.
- **Fail signature:** two tankers of the *same* method, which means a proposal went out without its method or the constraint is not reaching `best_squadron_for` (before 2026-09-17 the unconstrained first flight did exactly this). Or a second tanker launching far from the station while one of its method sits there, which means it is being ranked from the first tanker's field. Or two tankers stacked on one racetrack, which means the orbit slot is not being applied. Or the package gone entirely in the negative case, which means the extra flight is not actually optional.

### B77 — A player's ramp allowance matches the airframe · #214 startup times · ☑ VERIFIED (2026-09-27, DM)

**2026-09-27, DM verdict in chat, while flying (session `519de343`)** — **VERIFIED.** "b77 is good": the ramp time given matched the airframe started. The airframe was not named and the capture folder was not made yet; the §104 runway queue (2026-09-23) was in the build, so this is the first start with the taxi-clearance wait modelled. Closed on the DM's call; off the WATCH card.

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **three human starts now, all late.** F-16C (`startup_minutes: 4`): airborne +13.0 against +12 briefed (test 37), +12:53 against +12 (test 38). F-15E (`startup_minutes: 3`): first moved at +12:20, airborne +14:26, against +11:29 (test 39). The row says a stopwatch figure replaces the arithmetic; whether these starts were unhurried is the DM's to say. **DM, same day: the wait was for taxi clearance.** So the late minutes are the ATC queue, not the start: at Kandahar the AI queued the same way (32 jets spawned inside 3.5 min, median 16.2 min spawn → airborne against 8.5 planned, the last pair at +22.8). `startup_minutes` stays; the queue is being modelled in the ground-ops allowance instead.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the F-15E half, a measurement.** Authored `startup_minutes: 3`. The card briefed Takeoff 18:11:30 against an 18:00:01 start (+11:29). The human lead first moved at t=740 (+12:20) and was airborne at t=866 (+14:26); the AI wingman moved at +8:40 and was airborne at +14:56. Whether the start was unhurried is the DM's to say.

**2026-09-22, test 38** (Syria — Long Road to H3 turn 2, 37 min, one human in the SPARROW SEAD Viper lead from Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048), `Desktop\New test\38`) — **the same answer as test 37.** The card briefed Takeoff 14:13L against a 14:01 start (+12 min); the human was airborne at +12:53 (`takeoff` at t=773). Test 37 read +13.0 against +12. Time acceleration ran on the ramp (18–25 wall seconds per 30 s of model time between t=330 and t=570), so the start's own wall-clock length is not measured. The F-4E and Hornet halves are still unflown.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **the Viper half, a measurement.** Authored `startup_minutes: 4`; the card briefed Takeoff 05:15Z against a 05:03:06Z start, a 12-minute ramp allowance including the Incirlik taxi. Off the recording the human lead was airborne at +13.0 min and the AI wingmen at +13.5, +14.1 and +14.7. One minute late on the lead; whether the start was unhurried is the DM's to say. No F-4E flown.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from a capture** (the allowance is read off the briefing card). Unchanged, on the WATCH card.

**History:** built 2026-08-17 against upstream issue #214, open since 2023. Never flown.
- **What it is:** `startup_minutes:` on an aircraft yaml overrides the campaign-wide `player_startup_time` for player cold starts. Four airframes carry a sourced value — F-16C 4, F-15E/F-15ESE 3, F-4E 9 — every other airframe falls back to the 10-minute setting, and AI flights keep their flat 2 minutes. Derivations are in `docs/dev/design/retlab-startup-times-notes.md`.
- **What CI cannot exercise:** whether the shorter allowance leaves a human enough time. The tests prove the number reaches the schedule; they say nothing about whether you can actually get a Viper started, aligned and to the hold-short inside 4 minutes.
- **Setup:** frag a player cold-start F-16C and a player cold-start F-4E in the same turn. Read each package's takeoff time against its TOT, then actually fly both starts with a stopwatch — **stored heading**, which is what the numbers assume. ~40 min for both. Also confirm an airframe with no value (a Hornet) is unchanged at 10 minutes.
- **Pass:** you make the briefed taxi time on a normal unhurried start in all three. The Phantom's 9 minutes should feel close but sufficient — its gyros alone eat most of it.
- **Fail signature:** you are still in the chocks when the package is due to taxi, which means the number is too tight and the note's inferred ~2-minute systems window is wrong. Record the stopwatch figure — a measurement replaces the arithmetic outright. The opposite signature also matters: arriving at the hold-short with minutes to spare means the value is generous and the whole exercise bought nothing.

### B91 — The F-14B(U) spawns with its cartridge loaded · §74 · ☑ VERIFIED

**History:** built 2026-08-22. Fork-only — upstream ships no DTC. Mined from
`CoreMods/aircraft/F14/DTC/F-14BU_DTC.lua`; design note
`retlab-dtc-cartridge-notes.md`, "F-14B(U) — the Tomcat schema".

> The Tomcat is the first §74 airframe whose schema is not the Hornet's, and the
> first whose navigation plan 1 already belongs to the mission route — so the
> cartridge carries references, pre-planned JDAM points and the TIS list rather
> than steerpoints.

**VERIFIED in the cockpit 2026-08-23, DM: "F14 data cart is confirmed good and
loading."** The squadron also supplied the vocabulary that confirms the central
design call: **"Route 1 should be the mission editor route. Route 2 is the first
one we can mess with."** That is exactly the split the builder was written to —
plan 1 left to the miz route, plan 2 ours — arrived at from the descriptor
(`updateNAVPlanEditability` greys plan 1's fields) and an authored cartridge, and
now confirmed by the people who fly it.

**Still unobserved, and worth a glance on any later Tomcat sortie** — none of it
blocks the row, and each is listed under "Watch for" below: the HUD pentagon
(`XST`), the A2A bullseye readout (`XB`), the threat axis (`XHA`), a CAP's
defended point (`XDP`), the priority slots (`X1`-`X7`), and whether the single
altitude field wants the ground or the planned height.

**Already done, on paper:** the emitted JSON was diffed against a hand-authored
F-14B(U) cartridge (the training-night package) and every section's key set matches,
with an unused JDAM slot byte-identical.

**ME import — DONE 2026-08-22, one defect found and fixed.** The DM loaded a cartridge
generated from the Iraq autosave: NAV imported outright (plan 2 route with TOTs, the
front line as line 2, the `XB` references) and so did the JDAM data, but the
post-import refresh died in `init_CMDS` because the first cut omitted the `CMDS`
section — JDAM grid blank until a tab switch, cartridge name stuck on `DEFAULT`.
Fixed the same day: every section is always written, CMDS as ED's defaults.
**Re-import VERIFIED 2026-08-22, DM:** the regenerated file loads with the cartridge
name reading the flight's callsign, the JDAM grid filled on load (TARGETAR on every
station, hdg 0, 20000 ft), the coordinates reading Iraq on an Iraq mission, and no
descriptor error in `dcs.log`. ED's importer accepts our JSON end to end. What remains
is the cockpit.

**Cheapest remaining check, and it needs no flying:** open the generated `.miz` in the
Mission Editor, open the DTC manager, and load the flight's `DTC/*.dtc`. If the ME
draws the reference points, the front line and the JDAM targets on its own panels,
our file survives ED's importer. Do this before spending a sortie.

Then fly one: F-14B(U) client flight on a campaign that fields it
(`clash_of_the_titans`, `red_sea_rising`, `operation_desert_trident`…), cold start.

- **Pass:** the CDNU cartridge label reads the flight callsign; the bullseye and
  divert appear as reference points with their `XB`/`XD` names; the tanker, AWACS
  and CAP anchors are there; the JDAM page shows the flight's target on STA 3-6
  PP1 with a sensible run-in heading and a LAR that draws; the TIS send-to list
  carries the package's other flights.
- **Fail signature — the whole cartridge is absent:** the file is in the miz but
  nothing loads. Check `type` reads exactly `F-14BU` in both the top level and
  `data` — `setData` refuses any other value outright.
- **Fail signature — a section missing from the file:** any of `NAV`/`JDAM`/`CMDS`/
  `TIS` absent crashes the descriptor's refresh (`dcs.log`: `attempt to index field
  ... (a nil value)` in `F-14BU_DTC.lua`). All four must always be present.
- **Fail signature — points are in the sea, or 3.28x off:** the coordinate pair
  the jet reads is not the one we favour. NAV elevations are feet and JDAM
  elevations are metres; a systematic 3.28 ratio means one of the two got the
  other's unit.
- **Answered 2026-08-23:** plan 1 is the mission editor's route and plan 2 is the
  first one the crew can edit — the squadron's own words. The builder's split is
  correct and is not to be revisited.
- **Watch for — the HUD and TID codes:** with the cartridge loaded, the first
  target should be highlighted with a pentagon on the HUD (`XST`), and in A2A the
  bullseye's bearing and range should show on the HUD (`XB`, carried on an
  additional point the way the authored cartridge does it). The threat axis should
  point from the bullseye at the top-ranked SAM site (`XHA`); on a CAP the
  defended point should sit on the asset the package covers (`XDP`). If the
  pentagon is missing, the code may need to be on a different point.
- **Watch for — the priority codes, the one guessed literal:** plain route points
  carry `X1`-`X7` in route order (`HOLDX1`, `JOINX2`, `SPLITX3`) so they rank with
  the coded ones on the PTID's 18-item display. **That literal is a reading of the
  NAV tab's `X#1`-`X#7` help text, not an authored cartridge** — every other code
  we emit has one behind it. On the PTID, check whether those points show as
  priority waypoints P1-P7 or merely as points named `...X1`. If the latter, the
  literal is wrong: try `X#1`, and say which worked in the design note.
- **Answered 2026-08-23 — there is no seven-waypoint route cap.** The CDNU stores
  twelve flight plans of fifty waypoints; the *PTID displays* eighteen at a time
  and ranks them (`FP, IP, HB, DP, HA, ST, Priority 1-3`, then `Generic 4-7`).
  A strike's extra target points are off the route because they crowd that
  display, not because anything overflowed.
- **Watch for — the one real unknown:** a Tomcat waypoint has a *single* altitude
  field where the Hornet and Viper have two, so it cannot separate "the ground
  under this point" from "the height to fly this leg". We write the planned
  altitude en route and the field elevation at the ends, which is how the
  authored cartridge in hand reads. If the CDNU turns out to want terrain height
  there, flip `_waypoint_elevation()` and say so in the design note.
- **Watch for:** whether the reference points' elevation being 0 matters in the
  cockpit. That is B90's open half, and this is a second place to observe it.

### B90 — A steerpoint's elevation is the ground under it · §74 · ☑ VERIFIED (2026-09-16, DM)

**2026-09-16, DM verdict in chat (session `9148a88a`)** — **VERIFIED.** "B90 is good" — the Viper's DED STPT page reads the planned altitude on the transit points, flown by the DM since the 2026-09-13 fix (#1019). Off the WATCH card.

**2026-09-13, flown (Caucasus, Flight 105 F-16C, DED read)** — **the cockpit read
arrived and failed the en-route half.** STPT 1 (the hold, planned 22,000 ft) read
**ELEV 131 FT** — the nearest field's elevation, which is what the cartridge had in
`alt` (`routeAltitude` was 22,000 ft). So the DED shows `alt`, not `routeAltitude`,
and the 08-22 reading below was wrong. Fixed the same day: `alt` now carries the
planned altitude on an en-route point and the ground estimate on a ground-marked
one, both fields the same number. **Still PARTIAL** — the fix is unflown. Next
Viper: STPT 1's ELEV should read the kneeboard's Alt for that row.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **the generation half is verified; the cockpit read is still
owed.** In the Hornet cartridge (`Retribution Ford 6 FA-18C_hornet.dtc`) the two fields the fix
split apart are both populated and different: `NAV_PTS[].alt` matches `nearest_field_elevation()`
on 8 of 9 steerpoints (the ninth is the landing point at 0.0), and `NAV_ROUTE[].alt` separately
carries the 6,096 m fly-to altitude. The fail signature — an en-route steerpoint reading ~2000 m
of elevation because `alt` went missing — does not occur. **Small open item:** the landing
steerpoint writes 0.0 where `nearest_field_elevation()` returns 18.0. Worth a look, but it is the
recovery point, not a target. Still needs a DED/DTC-panel read to close.

**History:** built 2026-08-20, from the cockpit. Fork-only — upstream ships no DTC.

> Reported while flying: the DEAD steerpoint does not sit at 0 AGL, it sits at
> **0 MSL**. `client_altitude()` returned one number and both cartridges wrote it into
> the point's `alt` and into the route entry, which are different things: ED fills
> `alt` from terrain (`getAltitude(x, y)`) and the height to fly rides `routeAltitude`
> / `NAV_ROUTE[].alt` with `altitudeType`. So a target's ground read as sea level, and
> every ordinary waypoint told the jet its ground was at cruise altitude. Split into
> `steerpoint_elevation()` and `leg_altitude()`; design note
> `retlab-dtc-cartridge-notes.md`.

Fly a Viper or Hornet on a regenerated mission and read the steerpoint pages.

- **Pass:** on the Viper's DED STPT page, an en-route steerpoint's ELEV reads the
  altitude the kneeboard plans for that row (a hold at 22,000 ft reads 22000), and
  a target steerpoint's ELEV reads the nearest airfield's elevation rather than 0.
  On the Hornet the HSI WYPT data shows the same numbers. (The DED shows the
  point's `alt`, flown 2026-09-13; `routeAltitude` is the DTC Manager's planning
  copy and is shown nowhere in the jet.)
- **Fail:** an en-route ELEV at field elevation (the 2026-09-13 defect), or 0 on
  a target.
- **Estimated, not exact (2026-08-22):** a target steerpoint's elevation is now the
  nearest airfield's, because that is the only height data the campaign carries.
  The DM's generated Viper cartridge had every steerpoint but the landing at 0
  before this. **Check this one specifically**: if a pod slaved to a target on high
  ground behaves, the estimate is good enough. If it still aims short, the route to
  close it is a DCS-side `Terrain.GetHeight` dump per terrain — not the SRTM table
  that was built and reverted on 2026-08-20.
- **Fail signature:** an en-route steerpoint reading 2000 m of elevation means `alt`
  went missing entirely rather than being written as 0 — that is the Viper loader's
  default for an absent field.

### B89 — Region priorities: the CP-dialog control shifts the ATO · §93 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-20 — upstream #686's map-control idea reworked to BMS's PAK
weighting (design note `retlab-region-priorities-notes.md`).
**2026-08-20 app pass: FAILED on IGNORED, fixed the same day.** Flown on
`test.retribution` turn 2 (Caucasus — Vectron's Claw): a red carrier set IGNORED still drew
an anti-ship package plus escort on the next turn. The dialog, the persistence and the
factor were all correct — `planning_factor` returned the drop — but `AttackShips` and
`AttackBattlePositions` read `TheaterState` lists nothing gated. Both now call
`auto_planning_skips`; verified by replanning that same save, where the package
disappears and no other package changes. **The EMPHASIZED/DEPRIORITIZED half is still
unflown.**

> The planner half is headless-verified (`tests/retlab/test_region_priorities.py`: the
> factor reorders, IGNORED drops, rescues exempt, red never weighted). What only an app pass
> can check: the combo on an enemy base dialog shows and persists with the setting on, the
> web tooltip carries the non-NORMAL line, and a turn generated with an EMPHASIZED axis
> visibly shifts the ATO toward it against a NORMAL baseline of the same save.
>
> **Pass:** set a far enemy CP EMPHASIZED and a near one IGNORED, regenerate the turn; the
> ATO gains packages toward the far CP and auto-plans nothing at the ignored one, while a
> hand-built package against the ignored CP still works. **Fail signature:** the combo
> missing on enemy bases with the setting on, a rescue dropping because its region was
> deprioritized, or any red package pattern change.

**2026-08-20, second pass — the feature grew a second axis.** Two more things to check
now, both on the same enemy target:

- **Per-target override.** An enemy target's own dialog carries a five-entry priority combo
  (Inherit plus the four). Pass: setting one target IGNORED at an otherwise NORMAL base
  stops packages against that target only; and with the BASE set IGNORED, setting one
  target back to NORMAL gets it planned again. That second half is the point of the
  override — if it does not work, the feature only subtracts.
- **Target Priorities window** (toolbar). Seven families with live enemy counts. Pass: a
  family set IGNORED stops every package against that kind theater-wide, including at an
  EMPHASIZED base and including a target explicitly marked NORMAL — kind is absolute.
  Fail signature: a count of 0 beside a family the map plainly has, or a change that does
  nothing because `region_priorities` is off (the window warns when it is).

### B87 — A stand-off shooter starts its run at its own launch range · §8 · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-19 from juanjux's OPFOR playbook, which documents the failure in
detail from an LLM commanding red through the player's own API.

> The attack task does not activate until a flight reaches the ingress point, and the
> doctrine ingress bound is weapon-agnostic — 45 nm on modern doctrine, for a dumb bomb and
> a 270 nm Kh-22 alike. So a stand-off shooter was dragged from its launch range into the
> target's defenses without shooting. A weapon yaml may now declare `range:` in nautical
> miles and the package's ingress is widened to its shortest shooter's reach, capped at 60%
> of the departure-to-target leg so the route cannot invert.

- **What CI cannot exercise:** whether the DCS AI actually launches from the moved ingress.
  The bound, the minimum-across-shooters rule, the escort exclusion and the cap are
  unit-tested; the release is not, and **the release distance is DCS's own** — this buys the
  flight a run that starts outside the defenses, not brochure range.
- **Setup:** a campaign where one side fields a long-range stand-off shooter against a
  defended target — a Tu-22M3/Kh-22 or an H-6 against a fleet is the clean case, an F/A-18
  with Harpoons against a SAM-armed group also works. Frag the package and fly or
  fast-forward. Compare against an older save's route for the same pairing if you have one.
- **Pass:** the ingress waypoint sits well out from the target (roughly the weapon's
  authored range, or 60% of the leg if that is shorter), the flight turns in there, and it
  **launches**. Tacview shows a release rather than a fly-in.
- **Fail signatures:**
  1. **The flight still flies to ~45 nm.** The package's shortest shooter has no authored
     range — check every flight in it, since the minimum sets the number. A short-legged
     strike flight mixed into a bomber package is the likely culprit and is a real planning
     mistake, not only a data gap.
  2. **The ingress sits behind the join point** and the route doubles back. The 60% cap
     failed; capture the leg length and the authored range.
  3. **The flight turns in at the right distance and still does not shoot.** That is DCS's
     release doctrine, not this fix — note the type and the distance, because it bounds what
     any authored number can ever buy.
  4. **A package that used to work now routes oddly** — an authored range on a weapon that
     is not the package's actual attack weapon. `range:` is for air-to-ground stand-off
     weapons only.

### B86 — Retribution survives DCS taking over the GPU (Qt 6.8) · app / Qt · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, PySide6/Qt bumped 6.4.2 to 6.8.3 on 2026-08-19. Diagnosis and the in-game NVIDIA
verification are juanjux's (his fork's #52); the pin bump is the whole change.

> On 6.4.x QtWebEngine composites the embedded map through the **native desktop-OpenGL** driver,
> whose context cleanup can deadlock (`nvoglv64.dll!DrvValidateVersion` /
> `WaitForSingleObjectEx` during `NtUserDestroyWindow`) while a fullscreen GPU application holds
> the card. 6.8 composites via **Direct3D 11**, so that context is never created. `QT_OPENGL=angle`
> never helped because ANGLE was removed in Qt6.

- **What CI cannot exercise:** any of it. CI never launches the window, never renders the map, and
  never has a GPU under contention. Static checking got as far as it can — all 132 dotted Qt call
  paths the app uses resolve identically on 6.4.2 and 6.8.3, and no application code changed.
- **Setup:** open Retribution on a loaded campaign, leave the map visible, then launch DCS and let
  it go fullscreen. Alt-tab back. Then, separately, open a settings dialog over the map and move it.
- **Pass:** Retribution stays responsive through both. The map still renders and pans, and the
  campaign is still usable after DCS exits.
- **Fail signatures:**
  1. **The window goes "Not Responding" when DCS takes the GPU.** The bump did not help on this
     hardware; capture which GPU and driver, because the deadlock is driver-specific.
  2. **The map is blank or renders in software** (visibly slow panning). 6.8 fell back off D3D11 —
     a different problem from the one being fixed, and worse.
  3. **The app will not start after a rebuild.** pyinstaller 6.19 / hooks-contrib 2026.0 are
     already pinned and are the versions reported to bundle 6.8 correctly, so look at the build log
     rather than the pins.
  4. **Any widget renders wrong** — spacing, delegates, the two-column rows. No Qt API our code
     touches changed, so this would be a styling or metrics difference, not a break.
- **Rollback:** revert the four pins in `requirements.txt` and rebuild. Nothing else moved.

### B83 — ATMOS-X live weather: the turn flies a real observation · ATMOS-X live weather · ☑ VERIFIED

**History:** 2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — "all of these are good") (was ☐ UNTESTED, built 2026-08-19, adopting upstream #927's second commit. Never flown. Design
note: [retlab-atmosx-live-weather-notes.md](design/retlab-atmosx-live-weather-notes.md).
**2026-08-20 — this row's own setup crashed New Game and is now fixed.** Leaving the station
box blank (which the Setup below tells you to do) sent the picker at `theater.player_points()`
while `Game.__init__` was still running, before the control points had coalitions:
`RuntimeError: ControlPoint not fully initialized`, campaign generation dead. The picker now
reads `starting_coalition`, and `live_weather_for` swallows and logs anything else. **Retest
from a fresh New Game, not a save** — a save never took this path.
- **What it is:** with the ATMOS-X cloud pack selected, the turn's weather is a real METAR
  observation fetched through the ATMOS-X CLI instead of a generated one. The mission keeps its
  own date and time and takes only the sky.
- **What CI cannot exercise:** the CLI is a third-party executable that talks to the network.
  Every test stops at its edge — reading what it writes, picking the station, copying the
  result onto a mission. Nothing has ever run it.
- **Setup:** ATMOS-X installed (it is, under Program Files, with `dcs_icao.csv` beside
  `atmosx-cli.exe`) **and activated in DCS** — run `atmosx-cli activate` first. As of
  2026-08-19 it is installed but **not activated**, and the CLI does not fail on that: it
  warns on its own stdout, which Retribution only logs on failure, then serves real METAR
  numbers with no ATMOS-X clouds. That is the likeliest cause of a "the weather is right but
  the sky is stock" reading. **Mission Generation → Weather**:
  pack = **ATMOS-X**, tick **Use ATMOS-X live weather**, leave both text boxes blank. Any
  terrain ATMOS-X covers — Syria is the densest. Generate two turns in a row. ~20 min, most of
  it generation.
- **Pass:** the **turn display's weather**, the **kneeboard QNH and surface wind**, and what
  you see out of the canopy all agree with the real METAR for the station the log names — and
  with each other. The mission's date and time are the campaign's, not today's. **Turn 2 is a
  fresh observation, not a generated sky.**
- **Fail signatures, in the order worth checking:** log says `keeping the generated weather`
  (the CLI was not found or the station reported nothing — the reason is on that line; this is
  the designed fallback, not a defect on its own) · real on turn 1 and generated from turn 2 on
  (the `Conditions.advance` hook did not take — test-pinned, so in game it means settings are
  not reaching `advance`) · the turn *after* a live-weather turn fails to generate (the §47
  weather ladder rejected a `LiveWeather` — also test-pinned) · kneeboard QNH disagrees with
  the turn display (the observation reached the `.miz` but not the game model) · mission save
  fails on a cloud base error (the base clamp did not fire for that preset).
- **Worth noting while you are there** (not pass/fail): which station it picked. The fallback
  is nearest-that-reports, which on a big map can be far off — a Syria turn from a Lebanese
  field taking Larnaca is expected, taking something in Turkey is worth recording.

### B97 — One salvo, and only the targeted flight breaks · §94 · ☑ VERIFIED (2026-09-23, DM + tests 24, 32, 37, 39; was ◐ PARTIAL)

**2026-09-23, DM verdict (session `c2acb521`)** — **fine, checked against the tests.** Test 39's population metric: 84 red SAM launches, blue jets within 60 km turning more than 90° within 60 s — median 0, mean 1.2 (tests 24 and 32: median 1, mean 1.21). The seven launches where 5–8 jets in 4–5 groups turned all fall at t=2813–2913, the Herat strikes' target run (TOT t=2932) and PIG's escort release — route turns, not reactions. The on-screen DEBUG line was never read in any test.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **another falsifier number.** Blue lost 36 aircraft: 26 to ground fire (10 to one S-350, 5 to Buk-M3s, 5 to 2S38 AAA, 3 to Tors, 2 to a Kub, 1 to a Strela-10), 4 air-to-air, 6 crashes with no weapon near. DEBUG was off. The S-350 killed from 30 to 60+ NM, where a turn away is not a defence, so this flight says little about reaction discipline either way.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`; corrected 2026-09-22 from full-resolution tracks) — **the pre-registered falsifier has its first number.** No DEBUG line: the toggle worked in this build (#1038 moved the script to a config work order) and was simply off, so the pass criterion is unread. Attrition: 15 blue aircraft lost in combat, 8 to SAMs — six to one SA-11 (`0126 | MAVERICK (SAM)`), which fired 13 9M38M1 from t=2399 to t=2470 and killed both `Kharab Ishk Escort` F-14As, both `Kharab Ishk Armed Recon` F-15Es and both `Kharab Ishk SEAD Escort` AV-8Bs between t=2431 and t=2475 (terminals 206–750 m from each victim, each removed within 0.1 s); one M-2000C to an SA-5 (5V28) at 13,500 m; one F-15E to a Tunguska. Six to air-to-air (four to MiG-25 R-40s, two to MiG-29s), one Apache to a tank ATGM. Whether Evade Fire would have saved the Kharab Ishk six is unknowable from one flight; a package lost whole to one MERAD is the shape the design note's falsifier names. A decision for the DM, not a tuning.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** no capture since test 32 had `DEBUG` on. The population metric is the same shape on test 33 (no red SAM salvo turned more than a handful of jets).

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`, DEBUG off) — **the population metric repeats; one package did not react at all.** `AIReaction| Smart Threat Reaction loaded` is in the log. Across 53 red SAM launches (32 SA-11, 20 SA-15, 1 SA-5) with 6–16 blue aircraft inside 60 km, the number turning more than 90° within 60 s was median 1, mean 1.21, maximum 5 — test 24's shape. The exception is KIWI: the SA-11 site fired eight missiles at the DEAD four-ship and its Mirage escort between t=4425 and t=4507, none of the five turned more than 90°, and all five died (t=4471–4541). With DEBUG off there is no way to tell a tag that never landed from an `AttackGroup` run that ignored `EVADE_FIRE`. Loss count for the falsifier: 12 blue AI to SAMs this turn (11 SA-11, 1 SA-15), none to red fighters. Re-fly with DEBUG; see G42 for why the DEAD flight was in the envelope at all.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **strong supporting evidence; one setting short of closing.**
`AIReaction| Smart Threat Reaction loaded (DEBUG=false)` is in the log, so fail signature 1 (the
plugin never loaded) is ruled out. Across **83 red SAM launches**, each with 13–14 blue aircraft
airborne inside 60 km, the number turning more than 90° within the next 60 s was **median 2, mean
1.86, maximum 6** — so 7–12 jets in the threat volume held formation on every launch. That is the
shape the pass criterion describes and it rules out fail signature 2 (the count climbing into the
dozens). It is not proof: a hard turn is not necessarily a defensive break, and with DEBUG off
there is no ground truth for which flight was tagged. **Re-fly with `ai_reaction.DEBUG` ticked and
this closes.**

**Setup.** Any campaign with a long-range SAM belt or a defended ship group, and at least
two blue packages airborne near it at the same time. `Smart threat reaction` is on by
default; tick its `DEBUG` option for this pass only — it prints every tagged shot on screen.
~20 min.

**Pass.** A SAM or naval launch tags one flight. The on-screen line names one group and the
count stays low (`[1 flights evading]`, occasionally 2-3 on a real multi-shot engagement).
Packages that were not shot at keep formation and keep flying their route. When the missile
is gone the tagged flight returns to route within ~10 s.

**Fail signatures, and what each means:**

- **Nothing ever prints and every jet still scatters** — the plugin did not load. Check
  `dcs.log` for `AIReaction| Smart Threat Reaction loaded`; absent means the DoScriptFile
  trigger was dropped (the known DCS behaviour with a dead plugin), not that the logic is
  wrong.
- **The count climbs into the dozens on one salvo** — `weapon:getTarget()` is resolving to
  aircraft it should not, or the release path is not firing. Capture the log.
- **Blue AI dies noticeably more than the campaign's baseline** — this is the trade §94 names,
  not a bug. Record the loss count against a previous turn on the same campaign before
  reacting; the design note's falsifier is written against exactly this observation.
- **§61 bandits stop maneuvering after ~10 s** — the `aiReactionExempt` claim broke. Grep
  `claim_exempt` in `redscramble-config.lua`.

**Cheap secondary read:** an anti-ship salvo should produce *no* on-screen spam at all, because
ship-targeted shots are dropped at the event. If a naval battle floods the screen, the
`notair` early return is not working and the perf fix that made this adoptable is gone.

### B93 — The front line sits on ground the armour can hold · §90 · ☑ VERIFIED

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **PASSES on the front this fix was built from.** The
Kutaisi/Khashuri FOB front position sits on drivable ground, inside a drivable band running
−14 km to +6 km across the trace — against the pre-fix measurement of 20.00 km one way, 0.00 km
the other and 0 % of the trace drivable. In the generated mission the two sides met: 62 blue and
62 red ground units within 25 km of the front point, closest blue↔red combat pair **2,634 m**
apart at spawn, and the TIC firefight ran. The 15 km stand-off on opposite ridges that opened this
row did not recur.

**History:** built 2026-08-23, from the DM's own `Maybe 414.retribution` on
`Caucasus - Northern Russia` — the app map showed the FLOT hanging entirely off
one side of the supply route, and the mission put blue and red ~15 km apart on
opposite edges of the same ridge.

> `frontline_bounds` cast one ray each way from the centre and stopped at the
> first inclusion-zone boundary. `find_ground_position` hands it a centre sitting
> **on** that boundary whenever the route crosses the edge of the drivable zone,
> so the ray toward the usable ground stopped at ~0 m and the ray into ground no
> vehicle can enter never met a boundary and took the full half-width. Measured
> on Kutaisi/Khashuri FOB, turn 1: 20.00 km left, 0.00 km right, **0 % of the
> trace on drivable ground**, with the real drivable run (+0.0 to +6.2 km)
> entirely on the side that got nothing. `usable_reach` now measures the drivable
> interval instead. Same front after the fix: 0.00 / 6.15 km, 98 % drivable.
> `tests/missiongenerator/test_front_line_usable_reach.py` pins the edge case and
> the open-country parity.

**What CI cannot exercise** is whether the resulting fights read well. A front
pinned into a mountain pass is now legitimately narrow — 6 km where the setting
says 40 — and that is rung D's intent, not a bug. Whether a 6 km front produces a
good CAS mission is a judgment only a flight makes.

Needs a campaign whose front crosses broken ground, not a specific flight.
Caucasus - Northern Russia (Kutaisi → Khashuri FOB) is the reference; any
mountain or coastal front will do.

- **Pass:** the orange FLOT on the app map straddles or runs alongside the supply
  route into passable ground, not away from it. In the mission, blue and red
  ground groups face each other across the front instead of bunching in two
  blobs with impassable terrain between them.
- **Fail signatures:**
  1. **The FLOT still hangs off one side into terrain** — check
     `usable_reach` picked the run holding the centre. A centre that is a
     boundary point is expected; `_room_around_center` falls back to the nearest
     run for exactly that.
  2. **The front is absurdly short (< 2 km) and the fight is a knife fight** —
     the drivable run really is that narrow, or the supply route crosses a ridge
     on a long straight segment. Check the route waypoints before touching the
     code: Northern Russia's wp3→wp4 is a 41 km chord over mountains, which is
     campaign data, not engine behaviour.
  3. **Groups still stack in one blob** — that is `flotgenerator`'s
     degenerate-front fallback, which means `is_on_land` is still false along the
     trace. Measure the trace before assuming the bounds are wrong.
  4. **The front line between two affected bases jumps** — ownership feeds base
     strength, so an 8-object swing is worth a look on Desert Trident's Jordan
     sector specifically.

### B124 — A hand-fragged Harrier DEAD opens the New Flight dialog on the DEAD preset, not a stock Snakeye fit · New Flight dialog · ✅ CLOSED (2026-09-23, DM: an era issue; was ✗ REGRESSED)

**2026-09-23, DM verdict (session `c2acb521`, reviewing the board after test 39)** — **an era issue, not a dialog bug.** Consistent with the 2026-09-16 audit below: on a 2005 campaign the date gate drops the DEAD preset from the dialog's list, so the combo keeps its first entry. Left open by this close: the same audit found the planner's `default_for_task_and_aircraft` still resolved `Retribution DEAD` for the AV-8B on that campaign, so the dialog and the planner disagree about what the era allows. Reopen as its own row if that matters.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **reproduced headless, and the mechanism is wider than the Harrier.** The New Flight dialog was driven offscreen on the DM's Scenic Route save (`CSAR.retribution`, turn 5) against a red SAM site with DEAD pre-selected: the aircraft combo offered the F/A-18C and the loadout combo opened on **`Retribution BARCAP`**. The dialog fills the combo from `Loadout.iter_for_aircraft` and then looks for the task's default names (`Retribution DEAD (XW)`, `Retribution DEAD`, `Liberation DEAD`, `DEAD`, then the BAI and CAS names); on this 2005 campaign none of them is in the Hornet's list (the payload file carries `Retribution DEAD`, so the date gate dropped it), the lookup finds nothing, and the combo stays on its first entry, which `create_flight` writes onto every member. That is the test-30 Harrier shape with a different first entry. The fix is in the dialog: when no default name is listed, fall back to the planner's `default_for_task_and_aircraft` (which resolved `Retribution DEAD` for the AV-8B on the same campaign) instead of index 0. Not built in this audit.

**History:** found 2026-09-13 on test 30 (Persian Gulf — Scenic Route turn 1). The AUROCHS
package was hand-created (`POST /qt/create-package/tgo/...` at 12:41 and 12:43, after New Game
at 12:40 and Pass Turn at 12:41). Its four-ship AV-8B DEAD flew DCS's stock
`Interdiction (H-L-L-H): AIM-9Mx2, Mk-82SEx8, Jammer Pod, GAU-12`, and both archived
generations (12:46, 12:50) already carried it. The DM did not pick that fit. Everything on
the generation side was checked and clears: `Loadout.default_for_task_and_aircraft(DEAD,
AV8BNA)` resolves `Retribution DEAD` (2 Sidearm, 4 AGM-65F, Litening) with the app's payload
directories; all three weapons predate 2005 and the faction has no year overrides; no
Harrier file exists in `Saved Games/DCS/MissionEditor/UnitPayloads`, no weapon injection,
no pinned §73 default; no name chain for any task reaches a stock preset; the configurator
writes `member.loadout` verbatim. The one surface that lists stock presets and writes the
combo's selection onto every member is `QFlightCreator.create_flight`
(`member.loadout = self.current_loadout()`), and `on_task_changed` does not refresh the
loadout combo, so a task change that leaves the aircraft selection in place keeps whatever
the combo showed before. Index 0 of the Harrier's list is `H-L-H: Mk-82SEx6, GAU-12`, not
the flown fit, so a stale index 0 does not explain it either. What the Harriers flew with
decided the mission: Snakeye is a low-level delivery, so the AI let down to 68 m at the
ingress point and ran 80 km on the deck into three SA-15 batteries; all four were lost
without releasing.

- **Setup:** on any campaign with a Harrier squadron, right-click an AAA site, Create
  Package, add a flight, set the task to DEAD and the aircraft to the AV-8B. ~1 min, no
  flying. Try it both ways: DEAD first then aircraft, and aircraft first then DEAD.
- **Pass:** the loadout combo reads `Retribution DEAD` before Create is pressed, in both
  orders, and the created flight's payload tab shows Sidearms and Mavericks.
- **Fail signatures:**
  1. **The combo shows a DCS stock name** — note which task was selected when the dialog
     opened and the order of clicks; that is the repro, and the fix is a loadout re-init in
     `on_task_changed`.
  2. **The combo reads `Retribution DEAD` but the created flight carries something else** —
     the write path, not the dialog; dump the flight from the save before generating.

### B99 — AI packages arrive inside the mission, not after it · §8 · ☑ VERIFIED (2026-09-16, audit)

**2026-09-16, headless read of the DM's Yankee Station turn-1 save (`Vietnam tes.retribution`, 60-min mission)** — **a residual on this campaign.** The row's tool over two re-planned turns: 72 spread-scheduled packages, 15 timed past the 60-minute window, of which 10 are unavoidable (transit longer than the window: Hueys from Khe Sanh to Ban Dong at 2 h, carrier Intruders and Maykop Phantoms to the trail) and **5 BAI packages are avoidably late by a median 3–4 min, worst 8–10 min**, which is past the ±5 min jitter the row accepts. 6.9 % sits between the tool's own thresholds (defect at 10 %, row dies under 5 %). The save's own ATO has TOTs at 13:01, 13:02, 13:08, 13:13, 13:18, 13:27 and 14:04 against a 13:00 end. The bigger lever is the 60-minute mission on a map whose transits run 50 min; the smaller one is the BAI overshoot, recorded here and not tuned.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED with the row's own instrument on the two live saves, and by three flown missions.** `tools/measure_tot_past_mission_window.py` re-planned two turns each of `91526.retribution` (Peace Spring) and `CSAR.retribution` (Scenic Route): 59 spread-scheduled packages, 0 late, maximum effective offset 34–62 min of a 100-min window, which is the "roughly half the window" the row asks for. Flown: tests 24, 30 and 32 timed nothing past the end and kept the second half of the mission populated (BARCAP waves, both AEW&Cs, both tankers up at 2 h on test 32). Fail signature 1 (several packages sharing one end-of-cycle TOT) did not appear in any of them.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — same shape. Five packages with TOTs from 15:44 to 16:16 on a 15:00 start (MUSK, WOLFHOUND, WEKA, MARLIN, KIWI); all five were airborne between t=967 and t=2633 and over their targets by t≈4600. The second half of the 2 h 14 min still had three BARCAP waves, both Hawkeyes and both tankers up, and a red F-5E pair launched at t=6536. Nothing was timed past the end. The cycle length itself still needs the app.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, no player, 59 min of sim) — 26
flights moved; every blue package was airborne inside the first ten minutes, the AV-8B DEAD
reached its target at t≈1530 and the Hornet Armed Recon flights were over theirs at
t≈1700–1920. The second half still had the BARCAPs, both AEW&Cs, both tankers and the Armed
Recon flights up. No package was timed past the end. Same shape as test 24; the TOT spread
itself still needs the app's ATO.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **the defect this fixed does not recur; the spread question is
half-answered.** Of 206 recorded flights, 154 got airborne, and **none first went airborne in the
last 10 % of the mission** — no package was timed past the end, which is what the clamp exists to
prevent. 126 flights were still alive in the second half, so the sky did not die. What the data
also shows is heavy bunching at the *start*: 131 of 154 were airborne inside the first 7 minutes.
That is takeoff time rather than TOT, and Retribution launches on a common push and spreads
arrivals by transit, so it is not the metric this row asks about — measuring the TOT spread itself
needs the ATO read off the app, which was not captured.

**History:** built 2026-08-24, planner doctrine-mining row 2. The non-CAP spread bounded the
random **offset** by the cycle and then added transit on top, so a long-transit package was
timed past the end of the mission. The share this affected was first measured against
hand-edited saves and was overstated; those numbers are withdrawn, and the fix stands on the
code being wrong. Instrument: `tools/measure_tot_past_mission_window.py`, driven from
`tools/_campaign_game.py`.

- **What CI cannot exercise:** whether the compressed arrivals still *read* as a spread in the
  air. The clamp is unit-tested and the population is counted headless; "the packages arrived
  in a sensible order, and the sky was not empty for the second half" is a flying observation.
- **Setup:** any campaign with long transits — a large map with the front far from the rear
  fields. Fly a full-length turn and watch the ATO, or generate the turn and read the TOTs off
  the app before flying.
- **Pass:** every AI package's TOT falls inside the mission cycle, arrivals stay spread across
  it rather than bunching, and the second half of the mission still has traffic in it.
- **Fail signatures:**
  1. **Several packages share one TOT at the very end of the cycle** — that is the clamping
     behaviour the scaling exists to avoid; check `_spread_arrival` was not simplified to a
     `min()`.
  2. **Everything arrives in the first third and the sky dies** — the scaling pulled too hard.
     Compare `max effective offset` from the tool before and after; it should still reach
     roughly half the window, not a fifth of it.
  3. **A package still lands past the end** — re-run the tool on that save. Two residual cases
     at ≤4 min are expected (later passes nudge a TOT), and are inside the generator's own
     ±5 min jitter margin.
- **Not a fail:** arrivals bunching late on a campaign where *every* target is near the far edge
  of the cycle. If the whole ATO is 90 minutes out in a 100-minute cycle there are only 10
  minutes of spread to distribute, and the alternative is the half of it that used to fall
  outside the mission. Check the transits before calling it a regression.

### B98 — The bullseye is the same place it was last mission · §95 · ☑ VERIFIED

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **PASSES.** The turn-1 `.miz` carries blue's bullseye at
`-294059.76572586 / 781603.93994526`; the turn-2 save reads `-294059.77 / 781603.94` — the same
point after a flown mission and a turn roll. `bullseye_pinned` is true on both sides,
`bullseye_moved_on_turn` is None, and the anchors are land control points (blue on Khashuri FOB,
red on Kutaisi), not a fleet or an off-map spawn. The cockpit half — whether the drawn point and
the AWACS calls against it read as a usable reference — is still unobserved, but the campaign-side
contract this row exists for is met.

**History:** built 2026-08-24. Replaces upstream's per-turn re-derivation. Design note
[`retlab-bullseye-notes.md`](design/retlab-bullseye-notes.md).

> Upstream re-derived both bullseyes inside every `initialize_turn`, so the point a
> squadron memorizes moved whenever the nearest opposing pair did — and on a Marianas
> save blue's bullseye was a red carrier in open water. It is now pinned for the
> campaign and the anchor can never be a fleet or an off-map spawn.

**Headless-verified already, so do not re-run it:** the anchor filter, the drift hold,
both migration paths and the boats-only fallback are pinned in
`tests/theater/test_bullseye.py` (10 tests), and the change was replayed against four
real saves — the three land campaigns re-anchor in place, Marianas moves 61.4 NM off
the Kuznetsov onto FOB Agrihan, and all four hold across five further turn inits.

**What only a cockpit can answer:** whether the pinned point is a *usable* reference —
DCS draws it on the F10 map and its own AWACS calls contacts against it, and neither is
exercised by any test here.

- **Setup:** any campaign, two consecutive turns. Read the kneeboard `Bullseye:` line on
  turn N, fly, pass the turn, read it again on turn N+1. Free — it is two kneeboards.
- **Pass:** the line names the control point before the coordinates
  (`Bullseye: King Abdullah II — 32°00'20"N 36°13'25"E`); the two turns carry the same
  line; the F10 map's bullseye ring sits on that field; and an AWACS bullseye call places
  a contact where you expect it.
- **Fail signature — no name, just coordinates:** `bullseye_anchor_name` did not reach the
  page. Expected exactly once, on a save made before 2026-08-24 and read before its first
  turn init; anything else means the kwarg is not being passed.
- **Fail signature — it moved anyway:** check `retribution.log` for
  `bullseye re-anchored on <cp>`. If the line is there, the front genuinely carried it
  past `MAX_DRIFT` (80 NM) and the kneeboard should be reading
  `** MOVED THIS TURN **` — that is the feature working. If the line is absent and it
  still moved, the pin is not persisting; check `bullseye_pinned` survived the save.
- **Fail signature — the banner cries wolf:** `** MOVED THIS TURN **` on a bullseye whose
  coordinates match last turn's. `anchor_bullseye` compares positions before recording a
  move, so that means something re-anchored to a *different* point of the same name.
- **Fail signature — it is over water:** the anchor filter did not run. The bullseye
  should be on a land control point unless one whole side owns nothing but ships.
- **Watch for:** a bullseye that is now *too far* to be useful — calls running past
  150 NM on every contact. `MAX_DRIFT` is a module constant in
  `game/theater/bullseye.py`, not a setting; if 80 NM is wrong for a real campaign, say
  which one and it becomes a knob.
- **Watch for — the one this did not fix:** a package fragged against the anchor base
  itself calls "bullseye 000 for 0". Standing the point off the field was considered and
  declined (it would stop being a findable landmark). If the degenerate calls actually
  bite in the air, that decision reopens.

### B102 — A low ingress against an SA-2/SA-3 belt is still flyable · DCS 2026-08-26 SAM guidance · ☑ VERIFIED (2026-09-23, DM; was ☐ UNTESTED)

**2026-09-23, DM verdict (session `c2acb521`, reviewing the board after test 39)** — **good, flown long ago.** The DM's call from earlier flying; no capture is cited.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised;** no capture flew a low ingress against an SA-2/SA-3 belt on the new guidance. Unchanged.

SA-2's V755 and SA-3's 5V27 gained the missing K-method of guidance (half-lead, elevated
by a constant) specifically for low-level targets, and the SA-8's 9M33 moved to a new
CFD-derived flight model with CLOS guidance enabled. Nothing in this tree changes —
threat rings come from pydcs sensor data and guidance method is not in it — so this row
exists to find out whether a campaign profile that used to work still does.

**Setup.** Red Tide, Vietnam or Desert Storm — any campaign whose front is screened by
legacy MERAD. Fly one strike at the altitude the squadron normally ingresses at, against
a defended target. Do not change the campaign. ~25 min.

**Pass.** Going low still trades radar exposure for a survivable run, and the fork's own
numbers are unaffected: the threat rings on the kneeboard match what actually engages,
and a site's threat ring still matches what engages.

**Fail signatures, and what each means:**

- **Low ingress is now simply lethal where it was survivable** — this is a DCS balance
  change, not a fork defect, and the fix is doctrine rather than code. Say so on the fly
  card before anyone re-tunes a campaign's SAM belt to compensate.
- **The kneeboard's threat ring no longer predicts where you get shot at** — the ring is
  drawn from sensor detection range, and the change was to missile guidance, so the two
  should still agree. If they do not, the export is stale.

**Watch for.** The Patriot's DLZ was corrected against ballistic targets in the same
patch. That only matters where a campaign fields both Patriot and mobile theatre
missiles — Desert Storm — and nobody has looked at it.

### B107 — The log stops repeating a MOOSE event error thousands of times · vendored `Moose.lua` · ☑ VERIFIED (2026-09-15, test 32)

**2026-09-15, test 33** (Syria, a 93-minute multiplayer host with a front line and TIC) — holds on the second build: `EVENTMETA` 0. The log is 19 MB anyway, and 66,000 of its 80,000 lines are DCS's own `event:type=group change option` echo of the same TIC option churn, written by the sim's multiplayer event logger, not by MOOSE; see the log-noise note.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — **the guard holds.** The flown `.miz` was unpacked and its `Moose.lua` carries the `RetLab patch (event 61 spam)` row; `grep -c "EVENTMETA data for event ID" dcs.log` returns 0 over 46 wall-minutes, against 1,282 on test 30 and ~10,300 on the 09-13 Iraq turn. CTLD, CSAR (both sides), Skynet and the threat-reaction plugin printed their banners; no TIC was on this map. The whole log holds one MOOSE error: AIRBOSS `_GetWire` compares a number with nil when an AI aircraft lands on the LHA (`Moose.lua` line 64544 chains `~=` with `or`, which is always true, so the Tarawa path looks up wires it does not have). It fired once, for the rescue helo, and skips only that landing's `_RecoveredElement`. The 90 `ANTIFREEZE` stalls came under time acceleration and are not a signal.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, 59 min of sim at ~2.4×
acceleration, no player slot, DCS 2.9.29.27468, build `78085dfd7`) — **not exercised: the
flown build predates #1016.** The `.miz` was generated at 12:50 and `main` was fast-forwarded
to `1a981f5e4` at 13:23 (the main checkout's reflog). Its `Moose.lua` carries the #997 rows at
line 7245 and no `Event.id ~= 61` guard. The warning fired 1,282 times in 25 wall-minutes with
no TIC formation on the map, rising from 6/min at mission start to 109/min under acceleration,
so the event is not TIC-specific. Re-fly on a mission generated after 13:23 on 2026-09-13.

**2026-09-13** (Iraq, ~25 min, FA-18C, DCS 2.9.29.27468, build `78085dfd7`) — **the fail
signature occurred on the first build that carried #997: ~10,300 occurrences in 20 minutes**
(108 written, 10,222 collapsed by DCS's dedup). The flown `.miz` was unpacked and its
`Moose.lua` carries the `RetLab patch` rows, so the patch was present and inert: it keyed
`UnitTaskComplete` (id 49), and 61 is a new 2.9.29 event upstream MOOSE describes as
"something like option changed". Re-fixed the same day with upstream's `if Event.id ~= 61`
guard in `EVENT:onEvent`. **Re-fly on a build after 2026-09-13.** The same log had 29
`ANTIFREEZE` stalls at an irregular cadence with 35 TIC formations and 895 units; the spam
is a symptom of TIC's option churn, not the cause of the stalls.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **could not be tested: the flown build predates the fix.** The `.miz`
was generated at 16:22:11, four seconds before the merge that brought #997 onto the branch at
16:22:15, so its bundled `Moose.lua` carries the two `civilian_traffic` patches but not the
event-61 row. **Baseline captured, and it is larger than the Afghanistan sample:** the flown
mission alone suppressed **63,338** copies of `EVENT.onEvent ... Could not get EVENTMETA data for
event ID=61`, plus 18,106 messages lost to buffer overflow, against 18,338 written lines. A second
terrain confirming the diagnosis. Re-fly on a build that contains #997.

DCS 2.9.29 raises an undocumented event 61 on every controller option change, and
MOOSE's `EVENT:onEvent` logged an error for each one — 6,807 times in one 7-minute
Afghanistan turn, 11,861 in an archived Germany Cold War log. The else-branch now skips
id 61, as upstream develop does. Nothing here is testable headlessly: the harness fakes
the DCS sandbox and never raises event 61.

**Setup.** Zero. Fly anything, then open `Saved Games/DCS/Logs/dcs.log`. ~1 min.

**Pass.** `grep -c "EVENTMETA data for event ID" dcs.log` returns 0. Every MOOSE
feature still behaves — CTLD, CSAR, MANTIS INTEL and TIC all report their startup
banners as before.

**Fail signatures, and what each means:**

- **Still thousands of `event ID=61`** — the guard was lost. Grep `Moose.lua` for
  `RetLab patch (event 61 spam)`; a bundle bump drops it silently, and the `.miz` must be
  generated after the fix (unpack it and grep). See
  `docs/dev/design/retlab-moose-bundle-patches-notes.md`.
- **A *different* unknown event ID now spams** — DCS added another event MOOSE does
  not carry. Same fix, one more row.
- **MOOSE plugins stop starting** — the row broke the table. Revert the nine lines;
  the spam is cosmetic and not worth a dead plugin.

### B109 — Payload backups leave `UnitPayloads` and the launch error stops · §73 · ☑ VERIFIED (2026-09-16, audit)

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED.** The launch error `Can't open file '...UnitPayloads//_retribution_backups'` appears exactly twice in every log through test 24 (2026-08-29) and zero times in the nine launches since (tests 25–33). On the DM's install `MissionEditor\UnitPayloads\_retribution_backups` no longer exists and `Retribution\PayloadBackups` holds the migrated files (AH-64D, B-52H, the four Tomcat marks, the Strike Eagle, the Viper), dated 08-17 to 08-29. Off the parking lot.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **could not be tested: the flown build predates the fix** (see B107).
The old signature is still present and still exactly twice per DCS launch: `Can't open file
'...\MissionEditor/UnitPayloads//_retribution_backups' from real path fs.`

§73 backed payload files up into `MissionEditor/UnitPayloads/_retribution_backups`.
DCS enumerates that folder expecting only payload `.lua` files and logged
`ERROR EDCORE: Can't open file '...' from real path fs` twice on every launch. The
store moved to `Saved Games/DCS/Retribution/PayloadBackups`, with a one-time
migration. The migration is unit-tested; what is not tested is DCS's reaction.

**Setup.** With an existing `_retribution_backups` folder in place, open any flight's
Payload tab (that alone calls `payloads_dir` and migrates). Then start DCS. ~10 min.

**Pass.** `Retribution/PayloadBackups` holds the old backups plus the new one, the
`_retribution_backups` folder is gone, and `grep _retribution_backups dcs.log`
returns nothing on the next launch.

**Fail signatures, and what each means:**

- **The old folder survives with files in it** — the rename hit an `OSError`; look
  for the `Could not migrate legacy payload backups` warning in the app log.
- **The old folder survives and is empty except for a subdirectory** — working as
  designed. The migration refuses to delete anything it did not put there; remove it
  by hand.
- **Backups stop being written at all** — `Retribution/PayloadBackups` was not
  creatable. §73 refuses the write rather than modifying a file it could not back up.

### B111 — A package's escort holds the striker's pace instead of running ahead · §8 cruise mach · ☑ VERIFIED (2026-09-27, DM)

**2026-09-27, DM verdict in chat, while flying (session `519de343`)** — **VERIFIED.** "b111 is good": the escort held the striker's pace after the join. The package and airframes were not named and the capture folder was not made yet. Closed on the DM's call; off the WATCH card. The test 39 F-15C measurement below stands as the lever if an unauthored escort runs ahead again.

**2026-09-23, test 40** (Afghanistan — Graveyard of Empires turn 2, no player, `Desktop\New test\40`) — **no Hornet striker; the escort lagged, then caught up.** SARDINE: an F-14B(U) striker with an F/A-18C SEAD escort. The striker reached JOIN at t=2053 (planned 2024), the escort at t=2146. They were 14–20 km apart until t=2200; the escort closed at 550–570 kt and was 0.3 km off at t=2320. From t=2380 the striker ran at 527 kt while the escort slowed to 217–302 kt firing HARMs; 11.8 km apart at t=2440. The escort did not run ahead.

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **a measurement: the F-15C escorts run ahead.** Join → ingress ground speed, lead jets: F-14B(U) strikers 455–460 kt; their F/A-18C SEAD escorts 464, 504, 520 kt; their F-15C escorts 576–636 kt (FALCON: striker 458, escort 622). The F-15E packages: strikers 563–664 kt, F-15Cs 600–644. Only the Hornet is authored (M0.78). Authoring the F-15C is the lever if the DM wants the escorts on the strikers.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the authored value demonstrably reaches the jet; the row cannot pass until more airframes carry one.** Test 32's three Hornet-escort legs read 20–50 kt slower than their Viper strikers at the same altitude, which is M0.78 against M0.85 and exactly what one authored airframe among unauthored ones produces. Test 33's package (Viper striker, Eagle and Hornet escorts) has the same shape. The pass criterion (escort within ~15 kt of the striker) is reachable only once the F-16C, F-15C and the rest have `cruise_mach:` values; the measurements are the input to that authoring, which is why this row now sits on the WATCH card as a reading, not a verdict.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`, no Hornet striker, so the row does not move) — **first measurement, off the recording.** Join→ingress leg, ground speed and altitude: WEKA SEAD Escort (F/A-18C: AGM-88C, 2×GBU-38, AAQ-28, centreline tank) 548–566 kt at 22,000 ft against WEKA DEAD (F-16CM: AGM-88C, AGM-65G, HTS, ALQ-184) 577–590 kt at 22,000; MARLIN SEAD Escort (same Hornet fit) 393–440 kt at 22,000 against MARLIN Strike (F-16CM, GBU-31) 412–494; MUSK SEAD Escort 449–459 kt at 19,000–20,000 against MUSK Strike 436–441 at 19,000 and MUSK Escort (clean F-16CM) 442–475. The Hornet escort read 20–50 kt slower than its Viper striker on two legs and matched on the third; no escort ran ahead. Wind aloft is unknown, so these are ground speeds, not Mach.

**Live for Hornet packages, a measurement row for everything else.** The mechanism landed
2026-09-01 with **one authored airframe, the F/A-18C at M0.78**. A package pairing a Hornet
striker with any unauthored escort is now exercisable; a package with no Hornet in it still
commands one mach for everyone and cannot move this row.

**Setup.** Any package with both a strike/DEAD flight and an escort. After the join, before
the ingress, open F10 and read **ground speed AND altitude together** off each unit. Record
the loadout with each number — store weight was already shown not to predict the answer
(see the note), so the loadout is context, not the variable. ~5 min, on a flight you were
flying anyway.

**Pass, once values are authored.** Escort and striker read within ~15 kt of each other on
the join→ingress leg, at the striker's pace.

**The measured baseline this replaces** (Syria, Syrian Shield turn 2): F-16CM SEAD Escort
542 kt at 22,000 ft (M0.89) against F/A-18C Strike 478 kt at 21,000 ft (M0.78), both
commanded ~M0.85.

**Fail signatures, and what each means:**

- **Both still read their commanded ~M0.85 band (517–525 kt)** — neither flight is an
  authored airframe. Expected for a non-Hornet package, not a defect.
- **A clean CAP Hornet reads ~M0.78 and feels sluggish** — working as authored, and the
  known cost of an airframe-wide knob. Record the reading: a clean Hornet measuring near
  M0.85 is the evidence that reopens the value.
- **They match, but the whole package is slower than the striker manages** — the authored
  value is too low. It is airframe-wide, so a clean CAP Hornet pays a loaded striker's price;
  that trade is recorded in the note and may need revisiting.
- **A planned speed below 486.5 kt appears with no authored value** — impossible from
  `GroundSpeed.for_flight`; something else wrote it. Read the note's ladder.
- **Fuel figures moved on strike packages** — the `combat_speed_waypoints` override was lost
  and the ingress leg is being charged combat burn.

Design note: [design/retlab-cruise-mach-notes.md](design/retlab-cruise-mach-notes.md).

### B112 — The wind you set is the wind the panel shows, and the box stops at 97 kt · wind override / live weather · ☑ VERIFIED (2026-09-23, DM; was ☐ UNTESTED)

**2026-09-23, DM verdict (session `c2acb521`, reviewing the board after test 39)** — **good.** The DM's app read; no capture is cited.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side.** Unchanged.

**An app pass, not a flight.** Nothing here needs DCS running; it is all in the Retribution
window. ~3 min.

**Setup.** Open **Time & Weather Conditions**. Note the three wind rows on the top panel
(At GL / FL08 / FL26). In the dialog, change a speed and a direction on any layer, then
Accept.

**Pass.**
1. The speed spinboxes stop at **97**, not 200. Typing a larger number is refused.
2. After Accept, the top panel's At GL / FL08 / FL26 labels show what you set, immediately,
   without passing a turn.
3. Accepting with nothing changed leaves each layer within ~1 kt of where it was. It will
   not be identical — the boxes are integer knots, so a layer can shift by up to ~0.3 m/s.

**Fail signatures, and what each means:**

- **The box accepts 150.** `MAX_WIND_SPEED` is not reaching `_make_speed_spin`. DCS models
  no more than 97, so anything above it is written into the `.miz` and ignored there.
- **The panel still reads the old wind after Accept.** The `updateWinds()` call is missing
  from `_apply_clock_and_weather`. Display only — the generated mission has the right wind,
  which is what makes this one easy to miss.
- **Accepting an untouched dialog moves the wind a lot.** More than ~1 kt per layer means
  something other than the integer round-trip is at work; before this fix, Accept re-rolled
  the wind outright, so a large jump means the override is not being applied at all.

**The live-weather half is not checkable this way.** It needs a real observation over 97 kt
at 8,000 m, which is a jet stream you cannot arrange. It is pinned by
`tests/weather/test_atmosx_live_weather.py::test_a_jet_stream_is_clamped_to_what_dcs_will_fly`
instead. If you ever do see a kneeboard wind above 97 kt on a live-weather turn, that test
is lying and this row fails.

### B114 — Your lifetime logbook survives starting a new campaign · §97 · ☑ VERIFIED (2026-09-23, test 39; was ◐ PARTIAL)

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **all six items, the window driven offscreen on a copy of the real store** (`QT_QPA_PLATFORM=offscreen`, the store copied to a temp Saved Games; the real `pilot_profiles.json` was hashed before and after, unchanged). 1: `PilotProfilesDialog` opens with no campaign loaded and lists `Flash`, `New callsign`, `King 1 | Flash`. 2–3: 8 sorties across five campaigns, Graveyard of Empires and the F-15ESE added. 4: one flight row per mission. 5: Rename to `Flash (renamed)` changes `display_name` and keeps the key `Flash`, which `record_mission` files against. 6: the store is readable JSON.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the second-campaign half passes in the store.** `pilot_profiles.json` (20:28) holds Flash across five campaigns, now including Afghanistan — Graveyard of Empires: 8 sorties, with the new entry `F-15ESE Strike, 29.0 min` and the F-15ESE row added to the per-aircraft table beside the F-16C and the Hornet. 8 sorties against 8 logged missions: one per mission, not one per jet in the flight. Not read: the Pilot Logbook window with no campaign loaded.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** the second-campaign half is still owed.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — **the store works, with two shapes to know.** `pilot_profiles.json` holds `King 1 | Flash` with this sortie (92.5 min, 4 shots, 3 hits, task Strike, campaign and turn named) and two older profiles from other campaigns, so the file outlives a campaign as designed. First shape: the key is the DCS name, so a renamed pilot starts a new profile — `Flash` (5 sorties, three campaigns) and `King 1 | Flash` are two people to the store. Second: the host did NOT record everyone this time — `SMR|Maj Redneck|90-824` flew and shot and has no profile, because the fold requires a record that moved and his had no track (B70). Fixed in the recorder, unflown since; the second-campaign half of this row is still owed.

**Needs two campaigns and one flown mission in each.** ~50 min, or split across two sessions.

**Setup.** `lifetime_pilot_profiles` on (it is by default). Open **Pilot Logbook** on the
toolbar — with no campaign loaded, which is half the test. Fly one mission in any campaign,
accept results, reopen it. Then start a **different** campaign, fly one mission there, accept
results, and reopen it again.

**Pass.**
1. The button opens the window with no campaign loaded, and after the first mission your DCS
   player name is listed.
2. Sorties went up by one per mission flown, not by the size of your flight.
3. After the second campaign the totals are the **sum of both**, both campaigns are named,
   and both aircraft appear in the per-aircraft table.
4. The flights list shows one row per mission with the right campaign, aircraft and task.
5. Rename works, and the profile keeps accumulating under the new display name.
6. `<Saved Games>\DCS\Retribution\pilot_profiles.json` exists and is readable JSON.

**Fail signatures, and what each means:**

- **The second campaign started the totals over.** The store is being written into the save,
  or the file path is being derived per campaign. It must be one file for the whole install.
- **A profile named "Player".** Not a failure — that is the DCS name your install is set to.
  Rename the display name, or change your name in DCS.
- **Sorties double-counted after accepting results twice, or after reloading and re-accepting
  a turn.** The `Game.stable_uid()` guard is not holding. This one matters more than the
  campaign version: there is nothing to recompute the store from, so a double count is
  permanent.
- **Replaying a campaign from turn 1 records nothing.** The opposite failure — the guard is
  keyed on the campaign name rather than the game.
- **Everyone in a multiplayer event lands in one profile.** The recorder is reporting the
  boolean and not the name; check `player_name` in `state.json`.
- **The window is empty after a mission you definitely flew.** Either the slot was AI (you
  did not occupy it) or the jet never moved far enough to count as a sortie.

### B115 — The cockpit front line is one continuous boundary, bowed where the map is bowed · §74 / §90 · ☑ VERIFIED (2026-09-23, DM; was ◐ PARTIAL)

**2026-09-23, DM verdict (session `c2acb521`)** — **good.** The DM's cockpit read; no capture is cited.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the cartridge carries one continuous L1 front line; the shape and the cockpit draw are unverified.** Test 33's Viper cartridge holds `GEO_LINES` with 12 `FLOT` points, all on L1, and `DEST` with the four usable fields. Peace Spring has a single front (Ramat David/Damascus), so this proves the single-line half only; the chaining of several fronts and the salient shape against the F10 drawing need a two-front campaign and a screenshot pair, as the setup says.

**Built 2026-09-10** from a paid F-16C campaign's own cartridge (design note
`retlab-dtc-cartridge-notes.md`, the 2026-09-10 section). Two changes: the DTC front line
now follows `FrontLineBounds.polyline` — the bowed trace the F10 drawing and the web map
already read — instead of the straight chord, and several fronts are chained into one
continuous boundary instead of one disconnected stub per line set.

- **What CI cannot exercise:** whether the HSD/SA/TSD actually draws the chained trace as
  one line, and whether the straight joins between front bars read as a border or as
  obvious nonsense crossing ground nobody is fighting over.
- **Setup:** any campaign with **two or more active fronts** and `front_line_salients` on
  (Red Tide or Germany are ideal; a single-front theater proves only half of it). Generate
  a turn with a client Viper, Hornet, F-14B(U) or AH-64D and leave the DTC tab's "Front
  line (FLOT)" section on. Before flying, screenshot the F10 map's front-line drawing.
- **Pass:** the cockpit line has the same shape as the F10 drawing — the salient bulges
  the same way and to the same side — and it runs as **one** line across the theater rather
  than several short dashes. Viper: all the points are on L1 and the HSD draws one
  polyline. Hornet: the SA page's FLOT lines meet end to end. Apache TSD and F-14B(U) plot
  line likewise.
- **Fail signature:** a straight cockpit line against a bowed map line (the `polyline`
  change did not reach that builder — check its `red_land_boundary` call); the line visibly
  breaking into pieces with gaps (consecutive runs are not sharing their meeting vertex);
  a join cutting a long straight diagonal across obviously rear-area ground between two
  fronts (the gap-filling approximation is the cause and is known — judge whether it is
  worse than the stubs were, because the alternative needs a territorial model the campaign
  does not have); only part of the front drawn on a theater with many fronts (the point
  budget thinned it — note how many fronts were active).
- **The support boxes land on the same flight — and the Hornet half is now PARTIAL
  (2026-09-13, DM screenshot):** the SA page drew **one** box, FAOR line 1, and it was the
  AWACS. So only FAOR 1 displays (the selected line, like the CAP point), and the boxes are
  now the tankers this jet can refuel from, nearest to its target first — no AWACS box on
  any airframe. Re-check: the one box on the Hornet is your tanker; Viper GEO L2-L4, Tomcat
  closed plot lines and Apache TSD lines carry the usable tankers only. Pass = the box sits
  around the tanker you join, drawn **without selecting anything**. Fail = an open C shape (the closing corner was dropped);
  a box square to the map on an angled orbit (the course rotation is wrong); a box nowhere
  near the aircraft (the orbit leg was read off the wrong waypoints — these are the WP2-WP3
  leg, not the spawn point); or, on the Viper, a front line so thinned it is unreadable,
  which is the deliberate trade and the thing to judge.
- **Tied to B28:** the Viper's CMDS section also landed on 2026-09-10, **default OFF**. The
  F-16C guide warns the CMDS MODE knob must be STBY before an MPD upload and `AutoLoad`
  fires on a cold jet, so the check B28 already owes is: tick "Countermeasure programs" on
  one flight, spawn, and read the CMDS page. Pass = MAN 1 dispenses flares only, MAN 5
  chaff only, the bingo counts read 10/10 and nothing else on the page is disturbed. Fail =
  any garbled or zeroed program, which is the erroneous-data-entry the guide warns about;
  revert the default and record it.

### B127 — A crowded carrier deck launches everything it parks, and the rest start airborne · §64 · ✖ REMOVED

**History:** removed 2026-09-18 with the deck cap it tested (DM call); no pass owed. The
cap air-started every carrier flight past 16 per mission. What it taught is in features doc
§64. Was ☐ UNTESTED.

The fix for test 36's silent loss of 33 carrier aircraft (see the test 36 section). The
deck ceiling is the Supercarrier guide's 16 parking spots; the overflow air-starts rather
than waiting on a hangar deck that never clears, and client flights are never moved.

- **Setup:** a carrier campaign where the boat's squadrons can frag well past 16 airframes
  in one turn — Long Road to H3 turn 2 did 50 — with at least one client flight on the
  deck. Generate, open the miz, count the groups spawning at the carrier. ~15 min, plus a
  fly if you want the launch half.
- **Pass:** no more than 16 aircraft are parked on the boat at mission start; every flight
  beyond that is in the air at its first waypoint; the client flight is on the deck; every
  planned flight exists in the mission. In the fly: the parked flights all get airborne.
- **Fail signatures:** a group in the ATO with no aircraft anywhere in the mission (the
  old signature — check `state.json` for a record with two identical samples at the boat
  and `alt = -1`); a client flight air-started; more than 16 on deck; aircraft parked on
  deck that never taxi, which means 16 is still too many for that mix and the F-14
  footprint rule needs modelling after all.

### B130 — The Viper's STPT 25 is the bullseye the kneeboard names · §74 · ☑ VERIFIED (2026-09-22, test 38; was ◐ PARTIAL)

**2026-09-22, test 38** (Syria — Long Road to H3 turn 2, 37 min, one human in the SPARROW SEAD Viper lead from Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048), `Desktop\New test\38`) — **the cockpit half passes.** DM's read on the ramp: STPT 25 on the DED is the Aleppo bullseye the kneeboard names (`Bullseye: Aleppo — 36°10'50"N 37°13'28"E`). The cartridge (`Retribution Ford 5 F-16C_50.dtc`) again writes 24 NAV_PTS and leaves 25 to the miz, as on test 37. The HSD readout was not read separately; it references the bullseye steerpoint, and nothing here moves it off 25.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **the cartridge half.** `Retribution Pontiac 5 F-16C_50.dtc` holds 13 NAV_PTS: the route on 1–6, the route's own Bullseye point as STPT 7 at x=125577 y=123125 (the miz's blue bullseye, to the metre), and the six support anchors on 8–13. Nothing is written at 25, so DCS fills it from the miz — the same point. The kneeboard names it (`Bullseye: Aleppo — 36°10'50"N 37°13'28"E`). The DED read and the HSD readouts are the cockpit half and are still owed.

- **Setup:** any campaign turn with a client F-16C and DTC on. Slot in, read the kneeboard
  Bullseye line, then select STPT 25 on the DED.
- **Pass:** the two agree, and the HSD bullseye readouts reference that point.
- **Fail signature:** STPT 25 holds a tanker or AWACS anchor (test 36's DED read the AWACS
  orbit), or the cartridge writes fewer anchors than it used to and one you wanted is gone.

### B131 — The land AWACS orbit sits over land, and two AWACS never share a racetrack · support orbits · ☑ VERIFIED (2026-09-21, test 37; was ☐ UNTESTED)

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`; corrected 2026-09-22 from full-resolution tracks) — **the setup exactly: Long Road to H3, turn 1 of a new game.** Off the recording, t=1200–3900: `Incirlik AEW&C` E-3A orbit centre 37.71N 35.11E, inland Turkey ~80 km north of Incirlik; `CVN-71 AEW&C` E-2C 36.54N 33.41E over the sea by the boat; 108 NM apart. Both land tankers off Incirlik, not Gaziantep; the A-6E on the carrier. No orbit centred on the LHA. Every pass item holds. The optional spacing check (a hand-fragged second AWACS) was not flown.

The fix for the three overlapping orbits in the test 36 follow-up (2026-09-17). With
every blue field inside red's threat zone, the land AEW&C anchor fell back to a generic
pick that filtered only off-map spawns, and came back LHA-1 Tarawa, 3.29 NM from CVN-71:
the carrier's one E-2C squadron flew two racetracks 14.9 NM apart, beside the carrier
tanker. The anchor is now land-only (`is_fleet`), a threatened host is taken only when
every land field is threatened, a repeated target is never planned twice, and each
further AWACS on one station steps 20 NM back from the threat (the tanker's pattern; the
August sideways spread was reviewed and not restored). Replayed on `autosave.retribution`:
AEW&C `[CVN-71, LHA-1]` 3.29 NM apart →
`[CVN-71, Incirlik]` 81.8 NM apart, and the land tanker station Gaziantep (hosts no
tanker) → Incirlik (hosts the KC-135s).

- **Setup:** Long Road to H3 on a turn where every blue field is threatened — turn 1 of
  a NEW game, or `autosave.retribution`. Generate, then look at the F10 support boxes.
  ~5 min, no fly needed.
- **Pass:** one AEW&C orbit over the carrier and one inland off Incirlik, clearly
  separate; the land tanker orbit off Incirlik, not Gaziantep; no orbit centred on a ship
  that is not a carrier.
- **Optional, for the spacing:** hand-frag a second AWACS onto a station that already has
  one. Pass: the new one sits 20 NM further from the threat, parallel, the first unmoved.
  Then delete the first and frag another: it should take the freed spot, not stack on the
  survivor.
- **Fail signatures:** two AEW&C racetracks side by side near the boat (the land anchor
  is still a ship); an AWACS orbit centred on the LHA; a land orbit anchored on a field
  that hosts no AWACS or tanker while one that does sits threatened and unused; a
  hand-fragged second AWACS stacked on the first, or stepped toward the threat.

### B142 — A survivor with no ejection comes down where his jet crashed · CSAR (#929 adoption) · ☑ VERIFIED (2026-10-11, test 55; was ◐ PARTIAL)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **both halves pass.** `state.json` has 13 `crash_positions` for 13 `crash_events`, the same names. In the turn-2 save the one survivor with no ejection (a Su-33 destroyed on the Kuznetsov's deck when the ship sank) sits on that jet's crash position to the metre, in the water at the sinking point. The other survivor ejected and sits 1.2 km from his recorded chute landing. Neither is on a package target.

**2026-09-23, test 40** (Afghanistan — Graveyard of Empires turn 2, 55 min, no player, `Desktop\New test\40`) — **the recording half passes; the placement half needs turn 3.** `state.json` carries 32 `crash_positions` for 32 `crash_events`, the same names. Each sits 0–5.1 km from where Tacview shows that group's aircraft hit; the gap is the fall. The survivors on this turn's map were placed by the turn-2 debrief, which ran on the build before #1073, so they still sit where test 39 left them (six F-15E crew 21–27 km from the nearest recorded loss). Open turn 3's map to finish the row.

Built 2026-09-23 from test 39. A loss with no ejection event rolls `csar_ejection_chance`, and the
survivor used to be scattered round his package's target: nine blue survivors sat 23–42 km from
their jets, and turn 2 fragged a CSAR helicopter 41 km from an F-14's crash. `dcs_retribution.lua`
now writes `crash_positions` on `S_EVENT_CRASH`; the survivor is placed there, else at the last §91
track sample, else at the target as before. Harness- and unit-tested.
- **Setup:** any AI-heavy turn that loses several jets without ejections (a SAM belt does it).
  Keep the turn's `state.json`, accept results, open the next turn's map.
- **Pass:** `state.json` has a `crash_positions` entry for every name in `crash_events`; every
  new survivor on the map sits within a few km of a crash point, none on a package's target.
- **Fail signatures:** `crash_positions` absent or empty with crashes present (the handler's
  `getPoint` failing — check `dcs.log`); a survivor still on a target (the unit-map lookup
  missing the crashed unit's name); a survivor for a player who despawned to spectator (the
  despawn guard is shared with `crash_events`, so this would be a new bug).

### B149 — Iranian missile sites spawn and fire (third-party missile mods) · §105 · ✅ CLOSED (2026-09-29, the third-party support was removed; the pack's own launchers are B166; was ☐ UNTESTED)

Built 2026-09-27 on the DM's call, until the RetLab pack carries its own launchers: the PG Iran
IRBM Pack's Sejjil-2, Emad and Fattah-2 TELs, the PG Iran Air Defense Pack's Shahed-238 launcher
and the Kheibar TEL, behind the `iranmissilemods` toggle. `[CH] Iran 2020` fields all five as
missile sites, `Iran 2015` the Sejjil-2. Unit-tested; never loaded in DCS through RetLab.
- **Setup:** the three mods installed; New Game with `[CH] Iran 2020` as red on a campaign with
  red missile-site markers, Iranian missile mods ticked on the Mods page, and missile-site fire
  tasks on (Settings, Performance).
- **Pass:** red missile sites spawn with these launchers, and each fires once at a blue base;
  Tacview shows the missile and its impact near a blue field.
- **Fail signatures:** a missile site with no vehicles (a type id that does not match the mod;
  `dcs.log` names it); `Couldn't setup missile site to fire` in the Retribution log (no blue base
  inside the launcher's `threat_range`); a launcher that deploys but never fires (the mod's own
  fire logic, not RetLab's); a crash to desktop when a TEL moves (the Kheibar author fixed a
  chassis `trace_width` crash in theirs; the PG IRBM TELs are not known to carry that fix).

### B153 — A theater tanker flies and tanks around its four-point box · tanker box · ✖ REMOVED

**History:** removed 2026-10-09 (DM call) after the tanking half failed in flight. Kola, KC-135 at 20,000 ft and about 375 kt, a human F-16 on the boom (Tacview `Tacview-20261009-190403-DCS-Host-Cost of Living Adjustment`):
- The KC-135 banked 45 degrees alone, 25 with a jet joined up and 15 with a jet in contact. At 15 degrees it needs about 8 NM a corner, so it overshot the 30 x 15 NM box's corners and S-turned back.
- The receiver was close aboard for 8 minutes. The tanker was wings level for under a minute of that; the last 6 minutes 15 seconds were one continuous turn (left, right, left).
- The loop and the corners worked as built (three laps). Leaving for home was again not reached.
- Theater tankers fly a 40 NM racetrack again; the pass owed is row B206. Was ◐ PARTIAL (2026-09-29, test 47).

**2026-09-29, test 47** (Persian Gulf turn 1, 59 min, a build before #1097) — **the flight half passes; the cockpit shows the fail signature #1097 fixed.**
- Both theatre tankers flew the box: the KC-135 (Al Dhafra, 40 x 20 NM) and the carrier's A-6E. Each passed every corner in order, cutting each by 4–5 km, and went round about three times (KC-135: BOX 2 at t=786, 1754, 2729). The SwitchWaypoint loop fired every lap.
- The F10 markers are boxes around the flown route.
- The F-16 cartridge drew the KC-135's box as a 7 x 5 NM square at BOX 1 (`GEO_LINES` 13 x 9 km). This build predates #1097.
- Not reached: nobody tanked, and the on-station end (t=7,786 and 7,204) is past the 3,546 s mission, so leaving for home was not seen.
- Still owed: tank on a straight leg and through a corner, the cockpit box on a post-#1097 build, and a mission long enough to see the tanker leave.
- 2026-09-29: the box was shrunk to 30 x 15 NM after this flight (DM). The owed items are flown on the smaller box.


Built 2026-09-28 from the DM's ask for a tanker box instead of a two-point racetrack, as an
experimental per-flight option (Payload tab); since 2026-09-29 every theater tanker flies it
and the option is gone (row B170). The tanker flies BOX 1-4 and BOX END as a route with the Tanker task
on, and a SwitchWaypoint at BOX END loops it to BOX 2 while mission time is under its
on-station end. Unit-tested (`test_tanker_box.py`) and headless-generated; never flown.
Design: `docs/dev/design/retlab-tanker-box-notes.md`.

- **Setup:** any campaign with a KC-135 theater tanker. Its flight → Payload → tick **Fly a
  box (experimental)** (the tanker replans), then generate.
- **Pass (map):** the tanker's route on the app map and its F10 marker are the box.
  Dragging any box point moves the whole box, and the F10 marker follows it.
- **Pass (cockpit, added 2026-09-29):** in a Viper (HSD) or Hornet (SA), the tanker's
  box is the same size and place as its F10 marker, and the tanker flies inside it. Fail:
  a small square near BOX 1 (the 7 x 5 NM defect reported that day).
- **Pass (flight):** the tanker flies all four corners, not a racetrack. You can tank on a
  straight leg and through a corner. It goes round more than once. After its on-station
  time (plus at most one lap) it leaves for home instead of starting another lap.
- **Fail signatures:** the tanker orbits at BOX 1 or flies BOX 1-END once and goes home (loop
  not firing); it never leaves (condition never false); it refuses contacts after BOX 1 (the
  Tanker task did not persist along the route); it races back toward BOX 1 at top speed.

### B165 — Two QRA scrambles from one field in the same second do not collide · §1 · ☑ VERIFIED (2026-10-11, test 55; was ☐ UNTESTED)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **passes.** Red QRA scrambled two pairs from Sochi-Adler. The first pair appeared 30 s apart and the second in the same second (12:48:10) at the same point; both times one jet was at 2,584 ft and the other at 3,076 ft. No jet was lost at spawn: the first pair flew 8 minutes before SM-2s killed them at 32,000-35,000 ft, and the second pair was alive at mission end.

Built 2026-09-29 after test 48 (Kerman: two F-14 wingmen air-started on the same spot and collided). Harness-tested (`tests/lua/test_intercept_filter.py`); never flown.

- **Setup:** any campaign where red QRA scrambles a pair or more from one base. Watch in Tacview.
- **Pass:** groups launched from one base inside a minute appear about 500 ft apart in altitude; no QRA jet dies within seconds of spawning.
- **Fail signatures:** two jets spawning at the same altitude and position; a QRA loss with no shot fired at it in its first seconds.

### B170 — Every theater tanker flies the box, with no box to tick · tanker box · ✖ REMOVED

**History:** removed 2026-10-09 with the box itself (row B153); no pass owed. The orbit speed's place on the Waypoints tab is row B152, and a save made with a box loading as a racetrack is row B206. Was ☐ UNTESTED.

Built 2026-09-29 on the DM's ask: the box stops being a setting, and the orbit speed moves
from the Payload tab to the Waypoints tab. The Payload tab's **Fly a box (experimental)** is
gone; `TheaterRefuelingFlightPlan` always lays out `TankerBoxLayout`. An old save's
`tanker_box` flag is dropped on load, and an old saved default's `tanker_box` key is
ignored. Unit-tested (`test_tanker_box.py`, `test_flight_defaults.py`); never run in the app.
Design: `docs/dev/design/retlab-tanker-box-notes.md`.

- **Setup:** open a save from before 2026-09-29 that has a theater tanker, and start a new
  campaign with one.
- **Pass:** both load; each new turn's theater tankers show BOX 1-4 and BOX END on their
  Waypoints tab; the Waypoints tab has Set orbit speed and the Payload tab has neither control.
- **Fail signatures:** an old save failing to load or a tanker window erroring on open; a
  theater tanker with a two-point racetrack on a new turn; a package or recovery tanker
  flying a box.

### B31 — Escort jamming (Growler / Prowler + growler plugin) · §77 · ⊘ RETIRED (removed 2026-10-12, DM: stripped)

**2026-10-12 — REMOVED on the DM's call.** Verified below by the 2026-09-16 audit; the plugin was off in his default settings and in all ten of his saves. The plugin and the Escort Jammer task are deleted, so this row can never be run again.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED for the AI runtime, from four missions' logs; the player F10 toggle is the one thing not flown.** Vectron's Claw (tests 1, 2 and 10) and Sinai (test 7) carried `GROWLER|: armed -- N escort jammer(s)` and then the plugin doing its job: 323 `holding down <site> for N s` pulses across SAM, SHORAD, PD, radar-AAA and armor groups carrying a track radar (the eligibility rule is any group with a `SAM TR` unit, so a Shilka or Tunguska inside an armor group is a legitimate target), and 14 `spoofed <missile> (best bubble <jammer>, pk N)` lines, the defensive bubble taking radar missiles off the package. Every jammer flight in every miz is an EA-18G or EA-6B (test 17's Prowlers armed but had nothing in range). The recovery window is visible as the pulses re-arming after their hold. Not seen: a human in the jammer seat turning it on from F10. The old MANTIS alarm-state fail signature no longer applies.

**History:** built 2026-07-21 as graduated tiers, then reduced to dedicated-jammers-only per user call — "only Growlers and Prowlers, no Harriers or anything else with a jammer"; the graduated tiers + the escort_jamming_loose setting are removed. The planner role, the Growler+Prowler-only roster (the two airframes that declare the Escort Jammer task), and the whole Lua policy — grace, spoof bubble, WEAPON_HOLD pulse + OPEN_FIRE restore, radar-SAM-only eligibility, friendly-fire guard, player-off + F10 menu — are pinned in tests/retlab/test_escort_jammer.py + tests/missiongenerator/test_growlerluadata.py + tests/lua/test_growler_runtime.py (incl. an AI-Prowler-pulses-a-SAM case). PASS: an **AI Growler** (fa_18efg mod on) rides a strike package into a radar-SAM ring and a radar missile aimed at a package member disappears mid-flight without an explosion at the launcher (defensive bubble) AND the SAM visibly checks fire in pulses (offensive); repeat with an **AI Prowler** (ea6b mod on) and confirm identical behavior — the plugin is airframe-agnostic; a player jammer sees the F10 "Growler jamming" menu and jamming stays dark until toggled ON; no Harrier/Hornet/Viper/Tomcat/A-10 is ever fragged as an escort jammer. FAIL signatures: any non-Growler/Prowler airframe fragged as an escort jammer (roster gate broken), an AI Prowler that never jams while a Growler does (airframe-specific code path crept in), a SAM never firing at all (hold stuck — restore path broken), the jammer orbiting away from the package (escort plan regression), a friendly missile vanishing (guard broken), or MANTIS alarm-state weirdness near the pulsed site. **Balance:** effects don't stack — a missile faces the single strongest bubble (rolled once, deterministically pinned that a 2nd identical jammer doesn't raise the spoof rate), a suppressed SAM gets a mandatory recoverySec shoot-back window before any jammer can re-hold it (pinned via the hold→release→hold cycle), and a per-side max_escort_jammers cap (default 4, 0=off) counts ATO jammers in can_plan_escort. PASS additions: fly a mass of jammers into a dense IADS and confirm the SAMs still fire in windows (not permanently dead) and every missile isn't spoofed; confirm no more than max_escort_jammers jammer flights are fragged in a turn. FAIL additions: SAMs permanently silent under many jammers (recovery window broken), near-100% missile spoof under overlapping bubbles (stacking not fixed), or more than the cap fragged

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — PARTIAL: airframes and tasking confirmed, the jamming effect is not provable from a Tacview.** Both recordings carry a full Growler presence flying the right taskings — turn 1 had **14 EA-18G airframes** across `Escort Jammer`, `SEAD Escort` and `SEAD Sweep` packages, turn 2 had 12. They generate, launch and hold station (most flew 35–51 km of track over 70+ minutes, i.e. an orbit; TARANTULA's Escort Jammer pair transited 231 km and left station at T+56 m). What a Tacview cannot show is the spoof bubble itself — no emitter state is recorded — so the non-stacking bubbles and the SAM weapons-hold pulses still need a watched pass with `dcs.log` open.

### B52 — Escort-jammer distribution + the one-SEAD-flavour escort set · §77 · ⊘ RETIRED (removed 2026-10-12, DM: stripped)

**2026-10-12 — REMOVED on the DM's call, the jammer half.** The Escort Jammer task is deleted. The one-SEAD-flavour half (`single_sead_escort_flavour`) is live and unchanged, and is now filed under §69.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **VERIFIED: the distribution half is settled by the only post-fix mission with a jammer wing, and the escort-set rules hold on 16 mizzes.** Test 17 (Inherent Resolve, 2026-08-25, four days after the fix) fragged both EA-6B Escort Jammer pairs onto strike-type packages that carried a threat-gated SEAD Escort (TAURUS BAI and the HVT Mullah Nasir BAI), none onto anything helo-led, and the wing's `max_escort_jammers` cap of 4 was spent there rather than on transports. Across tests 17–33 no package carries both a SEAD Escort and a SEAD Sweep, front-line CAS still gets its own SEAD Sweep (Iron Gate twice, Caucasus 2026, Peace Spring), and DEAD packages take a SEAD Escort only. Not seen: a DEAD package on a jammer-fielding wing (test 17 planned none), which is the cap's territory. The one-SEAD-flavour half was the DM's 2026-08-21 verdict.

**2026-08-21, DM pass `sead-escort-waypoint-bug-548af6` — the ONE-SEAD-FLAVOUR half is good.**
The jammer-distribution half (does the auto-planner put a Growler on the right package) is
still open and is what keeps this row from closing.

**History:** built 2026-08-07; the one-SEAD-flavour half **reverted 2026-08-09** by planner
re-convergence work order B (`c5e7a4f48`, which restored upstream's `SEAD_SWEEP` proposal),
rebuilt 2026-08-17 behind `single_sead_escort_flavour`. The jammer-distribution half was
never reverted. Read B75 with this row: the rebuild moved the trim from the proposer to
the fulfiller, so it now also catches `PlanDead`'s extra `SEAD` flight, and the ungated
default is upstream's stacking.

> **Where the jammers actually go.** B31 covers whether the §77 runtime works; this row covers
> whether the auto-planner puts one on the right package. Found by dumping a live save's ATO
> (Afghanistan, turn 1, `brady.retribution`): blue fragged exactly two Escort Jammer flights and
> **both went to CH-47F air assaults** — the Growlers launched from Kabul, 89 nm from the assault
> base, joined ~15 min behind the helos at 21,000 ft, and split for home on the same second as
> the drop. Meanwhile all seven DEAD packages, the tasking whose whole point is penetrating a
> live radar-SAM ring, flew with none, because `PlanDead` does not use `propose_common_escorts`
> and never proposed one. Four changes: `PlanAirAssault` opts out (`propose_common_escorts(jammer=False)`);
> `PlanDead` opts in; the formation-escort guard in `Squadron.can_auto_assign_mission` now reads
> `task.is_escort_type` so `ESCORT_JAMMER` inherits the helo/LHA rule that already covered
> `ESCORT`/`SEAD_ESCORT` (a Growler is carrier-capable but **not** LHA-capable, so no helo-led
> package — CSAR included — can pull one); and `propose_common_escorts` asks for **one** SEAD
> flavour (`SEAD_ESCORT`, the one that rides the package's join→split) instead of also asking for
> `SEAD_SWEEP`, generalising the trim `PlanDead` already had. A fifth, separate bug fixed
> alongside: `ESCORT_JAMMER` was missing from the escort set a package may lose without being
> scrubbed (now `PRUNABLE_ESCORTS`), so under COIN/Vietnam doctrine — which allow the tasking
> **and** fly unescorted — an unavailable Growler killed the whole strike. All five are pinned in
> `tests/retlab/test_escort_jammer.py` (28), ~~`tests/test_dead_planning.py`~~,
> `tests/commander/test_motorpool_targeting.py`. What CI cannot judge is the resulting ATO shape.

Play a turn on a Growler- or Prowler-fielding wing against a campaign with several radar SAMs
(Marianas 2027 or Red Tide), then read the ATO before flying anything.

- **Pass:** Escort Jammer flights sit on DEAD/strike packages that route into a SAM ring. No air
  assault, CSAR or other helo-led package has one. No package carries both a SEAD Escort and a
  SEAD Sweep. Front-line CAS still gets its SEAD Sweep (`PlanCas` proposes that one directly).
  Package sizes look proportionate — no six escort aircraft around a two-ship helo insert.
- **Fail signatures:**
  1. **A helo package still has a jammer.** The guard did not take — check the airframe is not
     LHA-capable (an AV-8B legitimately still escorts helo packages; that is the guard working).
  2. **DEAD packages still have none while the wing has spare Growlers.** Either
     `max_escort_jammers` (Air Doctrine, default 4) is already spent by earlier packages, or the
     route was not judged radar-SAM-threatened — the proposal is still threat-gated.
  3. **Fewer packages get planned than before.** The one-SEAD-flavour trim frees jets; if the
     count went *down*, look for a package scrubbing on a missing escort.
  4. **SEAD support feels thin against a dense IADS.** Halving the SEAD flavours is the trade this
     row is for — if one SEAD Escort per package is not enough cover, that is the finding, and the
     answer is to reinstate the sweep for specific callers rather than for all of them.

### B103 — BMP-3s in a firefight still fire like armour, not infantry · §9 TIC · ⊘ RETIRED (removed 2026-10-15, DM: TIC removed)

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the units were in the fight, the rate was not measurable.** BMP-3 groups stood on the live front on Iron Gate (tests 24 and 26, two groups each) and Caucasus 2026 (test 31, six groups) after the 08-26 patch; a recording does not carry ground gunfire per round, so salvo rate needs eyes. Unchanged; parked on the WATCH lot.

DCS 2.9.29 folded the CurrentHill pack into core. `CHAP_BMP3.lua` keeps the vanilla id
`BMP-3` but renames its DisplayName to `IFV BMP-3 [CH]`. TIC keys its per-unit profile
table by DisplayName (`TIC_v1.1.lua:512` → `:2300`) and swallows a miss with `or {}`, so
the BMP-3 entry's `SalvoQty = 1` silently reverted to the generic profile — BMP-3s
started firing at the infantry salvo rate. Fixed by falling back to the name with a
trailing vendor suffix stripped; verified on Lua 5.1 that both spellings resolve.

The id is unchanged, so no layout or unit yaml was ever at risk and
`tests/test_layout_unit_types.py` stays green. Detail in
[retlab-dcs-update-2026-08-26-notes.md](design/retlab-dcs-update-2026-08-26-notes.md) §2.1.

**Setup.** Any campaign whose red order of battle fields the BMP-3 with TIC enabled —
Red Tide is the readiest. Fly a CAS or TIC sortie over a contested front section and
watch a BMP-3 group engage. ~20 min.

**Pass.** BMP-3 groups fire in single aimed shots, visibly slower than a BTR-80 or
BTR-82A group in the same firefight. The distinction between IFV and APC fire is
audible and visible from the cockpit.

**Fail signatures, and what each means:**

- **BMP-3s pour fire like APCs** — the fallback did not match. Check the live
  DisplayName with `getDesc().displayName`; if ED used a different suffix shape than
  ` [CH]`, the pattern `%s*%[%u+%]$` needs widening.
- **No unit fires at its profile rate any more** — the fallback broke the exact-match
  path. That would mean the `or` chain is returning the wrong table; revert to
  `profile[self:GetDisplayName()] or {}` and re-test.
- **The T-90 behaves oddly too** — `CHAP_T90A.lua` also claims a vanilla id (`T-90`,
  DisplayName `MBT T-90A [CH]`). TIC does not key it today, so this would mean something
  else keys by DisplayName. Grep the plugin tree before assuming it is this fix.

**Note.** TIC has no headless harness coverage — `tests/lua/` covers `vietnamops` only.
Nothing catches the next DisplayName rename, which is the general risk this row stands
for.

### B108 — A stuck TIC unit names itself, and the retries are spread not concentrated · §9 TIC · ⊘ RETIRED (removed 2026-10-15, DM: TIC removed)

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **measured: no stuck retry at all since the fix.** The anonymous line fired 629, 487, 509 and 90 times in tests 1–2, 17, 21 and 24 (all on the pre-fix TIC copy). In the four post-fix missions with a live front and TIC running (tests 25, 26, 31 and 33: Syria 2024, Iron Gate turn 2, Caucasus 2026, Peace Spring) the named line never fired, because nothing got stuck. So the distribution question has no data, the storm is gone from the logs, and the pass line has not yet been seen printed. Stays on the WATCH card for the first mission that produces one.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — no stuck-unit line in 93 min of a live front, so nothing to adjudicate. Two things the same log does show: 51 `MIST|getGroupData ... TIC:unit|... not found in MIST database` errors in one second at mission start, one per TIC unit, before MIST's database has seen the groups TIC just spawned (the fight went on, so it is noise until shown otherwise); and DCS's multiplayer event logger echoing every controller option change TIC makes, 66,000 lines in 93 min.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **could not be tested: the flown build predates the fix** (see B107
for the four-second miss). The bundled `TIC_v1.1.lua` is the 2026-08-26 copy.

`OnBeforeArrived` re-issues a move with roads prohibited whenever a combatant made
no progress since the last tick. It fired 846 times in 7 minutes and named no unit,
so nobody could tell thirty units recovering twice from one unit wedged all mission
— and those want opposite fixes. The line now carries the combatant name and a
per-combatant count. **This row is a measurement, not a pass/fail on behaviour.**

**Setup.** Any campaign with an active front and TIC on. Fly a normal turn of ~15
minutes, then read `dcs.log`. ~20 min including the read.

**Pass.** The line reads `... [<unit name>] (retry N)`. Then answer the actual
question: `grep -oP 'stuck.*?\[\K[^]]+' dcs.log | sort | uniq -c | sort -rn`.
A long tail of distinct names with low counts means DCS ground pathing on that
terrain — the answer is fewer or simpler routes. A handful of names
with counts in the hundreds means a wedge — the answer is a retry ceiling that parks
the unit. Record which, in `retlab-tic-dynamic-fronts-notes.md`.

**Fail signatures, and what each means:**

- **The name prints as `nil`** — `combatant:GetName()` is unsafe at that point in the
  FSM; wrap it or use the group name.
- **`ANTIFREEZE ENABLED` still clusters on the retry peak** — the correlation holds
  and this is a framerate problem, not just log noise. That escalates the row.

### B121 — Neutral border: AI intruders are never engaged · §98 · ☑ VERIFIED (2026-10-18, test 62; was ◐ PARTIAL)

**2026-10-18, test 62** (Syria — Anatolian Reach turn 2, Brady in SLOTH Strike (F/A-18C), 42 min, `Tacview-20261018-180758`, main `0507d6680`, `Desktop\New test\62`) — **the field half passes; verified on Brady's call.** Ten AI aircraft were inside Lebanon with `engageAi=false`: red's SQUIRREL DEAD, SEAD Escort and Escort flights up to 9.3 mi deep, and blue's Ramat David BARCAP F-14s up to 7.7 mi deep. The log has no neutral-border line after `8 border zone(s) drawn, 4 defended`. The Lebanese SA-3 stayed neutral and fired nothing.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the rate half is answered, the reaction half is unreachable until a stray happens.** Three AI-only or player missions on two maps (tests 30, 32, 33) put 12, 11 and 3 neutral batteries on the map for the whole mission, none fired, none changed colour, and in test 32 every aircraft track was tested against the polygons: no AI aircraft was ever inside a neutral country. Strays are rare, which is the fail signature the row was worried about in reverse. The never-engaged invariant stays harness-pinned; the field half closes on the first mission where an AI flight visibly crosses a shaded border and nothing happens.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — `8 border zone(s) drawn, 3 defended; warn 30s, engage 180s`; no hail or warn line in 93 min with two humans and 30 blue AI aircraft up. Not exercised beyond that; tracks were not tested against the polygons this time.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`, `engageAi` off) — **consistent, still not closed, and the polygon question is answered this time.** The zone table was read out of the flown `.miz` (Pakistan ×2, Saudi Arabia and Qatar neutral; UAE and Oman blue; Iran red) and every aircraft track in the recording was tested against it: no blue or red aircraft sample was inside a neutral country at any point in 2 h 14 min, and the neutral batteries (Saudi Patriot, Qatar SA-3, Pakistan SA-11 and SA-3) fired nothing. No stray happened, so the row cannot move; it needs a turn where one does.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, `Tacview-20260913-125128`, no
player, DCS 2.9.29.27468, `engageAi=false`) — **consistent, not closed.** Twelve batteries
stood from t=0 across the UAE (3 Hawk), Oman (2 Hawk, 1 Rapier), Saudi Arabia (2 Patriot),
Qatar (SA-3) and Pakistan (SA-11, SA-3); every one was still there and still neutral at
mission end, and no neutral weapon was fired all mission (the two neutral-coloured objects at
t=1540 were an AV-8B's ordnance cooking off at its crash site). The log reads `9 border
zone(s) drawn, 7 defended; warn 30s, engage 180s`, and no hail or warn line fired, which is the
AI-only expectation. What the capture cannot show is whether an AI flight actually crossed a
border: the closest approach was the Kish A-50 at 47.6 km from the second UAE Hawk and
50.8 km from the Oman Rapier, and without the drawn polygon in hand that is not a crossing.
Needs a map look on a turn with a red or blue AI flight visibly inside a shaded border.

**REWRITTEN TWICE.** The 2026-09-07 rewrite dropped the scramble's
`shadowHoldNm`/`maxShadows` language, which was right, but it then described the
four-ship patrol — deleted the same week — and said an AI stray "gets the radio
calls". **That is wrong and always was**: `hail` and `warn` are both gated on
`state.is_player` (`neutralborder-config.lua`), so an AI stray draws **nothing at
all**. Corrected 2026-09-09.

**What this row now asks.** A country that refuses transit stands SAM batteries
inside its own border for the whole mission. An **AI** flight that strays across
gets **no reaction of any kind** — no radio call, no coalition swap, no SAM. Only
a player earns those. The invariant is harness-covered; what needs eyes is that it
holds in a real mission, and that AI strays happen at a believable rate rather
than constantly.

**Tick `engageAi` to watch the ladder run without flying it** (plugin options,
default off, added 2026-09-10). It holds AI to the player's rules, so one
generated turn exercises the hail, the dwell, the whole-country swap and the
engagement. Use it to adjudicate **B120**, then untick it — this row is the
default behaviour and must be checked with the option **off**.

**Setup.** Any campaign with `neutral_border_defense` on —
Into the Hornet's Nest (Lebanon) or Enduring Resolve (Pakistan, Iran) are the
worked cases. Fly a normal mission and watch the F10 map for red or blue **AI**
crossing a shaded border. You do not need to cross one yourself; if you do, that
is B120's ladder, not this row.

**Pass.**

* An AI stray draws nothing. No radio call reaches you, and the batteries keep
  their neutral colour on the F10 map.
* No neutral battery goes weapons-free or alarm-red for an AI intruder.
* Every battery the country stood is still there, still neutral, when the AI
  leaves.

**Fail signatures.**

* The patrol turns hostile — its F10 colour flips to a coalition — with no player
  inside the border. That is the players-only gate leaking.
* A neutral SAM fires on an AI flight.
* AI strays on every mission. That is a campaign-authoring problem, not a defect:
  the border sits on the AI's routes, and the author should raise the altitude
  floor or accept the theatre.
* The patrol chases the AI out of its own airspace. It should not move.

**Also record, because nothing else will:** whether a patrol on a **contested or
already-aligned** country ever appears. It should not — only an uninvolved
country that refuses transit gets one.

**History:** built 2026-08-24 on the DM call that everyone trips the border and
only players are ever engaged. Flown 2026-08-28 against the scramble: the
never-engaged half held, and the alert pair was killed by the intruder's BARCAP
in all four cases — the finding that helped kill the scramble. Superseded by the
standing patrol; see the design note.
