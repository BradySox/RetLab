# RetLab In-Game Pass Checklist

> Test paths shown ~~struck through~~ were deleted along with the feature they covered. They are left visible because the citation is part of the record; do not go looking for the file. Audited 2026-08-17.

Most RetLab features are validated by careful reading + Python tests, but their
**runtime behavior cannot be exercised in CI** — the Lua plugins, the planner's
spatial placement, and the MOOSE dispatcher only show their true colors in a
live DCS mission. The engineering doc
([retlab-features.md](retlab-features.md)) tags these as *"needs an in-game
pass."* This file is the **tracker** that turns those scattered tags into a
verdict-producing protocol: one row per outstanding check, each with an
observable pass criterion and the failure signature to watch for.

Update a row's **Status** when you fly it. Don't mark `VERIFIED` on a hunch —
it means *"I watched for the fail signature and it did not occur,"* ideally with
a Tacview/log reference and a date. When a row reaches `VERIFIED`, also drop the
*"needs an in-game pass"* tag from the matching section of `retlab-features.md`
so the two docs don't drift.

**New rows do not go in this file.** From 2026-09-29 each new row is its own file,
[`checklist-rows/<ID>.md`](checklist-rows/), written by `python tools/claim_id.py row`,
so two PRs adding rows never meet at the end of this one. Rows already here stay here
until they are settled.

**Settled rows are in the archive.** A row that owes no flight (verified, retired,
removed or closed) moves to
[`retlab-ingame-pass-checklist-archive.md`](retlab-ingame-pass-checklist-archive.md)
with `python tools/checklist_rows.py archive`, text unchanged. The test write-ups for
tests 24 to 47 and the closed 2026-08-05 work orders are there too. The board and the
tests read this file, the archive and the row files.

> **Headless queue status (2026-06-27):** the desk-adjudicable work is **exhausted**. The
> Python/Lua-logic layer behind every outstanding row is test-covered and was re-verified **green on
> branch** (227 backing tests + `test_late_init`), so the remaining items are gated on a live cockpit
> pass, not further headless analysis. Don't re-run the test sweep expecting a status flip — ☑ VERIFIED
> requires watching the fail signature in DCS.

## Outstanding rows at a glance

Not kept by hand, so two PRs grading different rows never collide here. Print it
from the row headings:

```
python tools/checklist_board.py          # outstanding rows, with the count
python tools/checklist_board.py --all    # every row
```

`☐` untested · `◐` flown but not
under the conditions that stress it · `✗` fail signature reproduced in-game.

**Adding a row:** claim its id first with `python tools/claim_id.py row` (prints
the next free `B###`, reserved on GitHub so no other branch can take it), then fill
in the stub it writes, `checklist-rows/<ID>.md`.

---

## Status legend

| Mark | Meaning |
|---|---|
| ☐ UNTESTED | Built; no in-game observation yet |
| ◐ PARTIAL | Flown, but not under the conditions that stress the fix |
| ☑ VERIFIED | Watched for the fail signature in-game; did not occur (note date/Tacview) |
| ✗ REGRESSED | Fail signature reproduced in-game — reopen the fix |
| ⊘ RETIRED | Feature dormant/removed — the scenario no longer runs; not a pending test |
| ✖ REMOVED | The feature was deleted; the row is kept so old notes stay readable |
| ✅ CLOSED | No pass is owed — the feature was removed, reverted or answered elsewhere |

---

## A. Air-to-air / QRA

---

## B. Planner placement / target logic (Lua-free Python)

### B6 — Command-center decapitation degrades enemy planning · §52 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** `c2_decapitation_effects` has been on in every campaign since test 1 (all seven saves read True except `Maybe 414`), but no save carries a dead command centre, so the effect has never had a chance to show. Needs a struck HQ and the turns after it.

**History:** built 2026-07-06, **A2 package throttle added 2026-07-17**; the health fraction, the linear unpredictability bonus, the off/intact/C2-less no-ops, the shuffler coupling, the SITREP line, and the A2 cap math + HTN-root gating are unit-tested in `tests/retlab/test_c2_decapitation.py` + `tests/test_planner_unpredictability.py` + `tests/test_sitrep.py` — whether red's *played* target selection visibly loosens and its offensive tempo visibly thins after its HQs are bombed needs a multi-turn campaign
- **What CI cannot exercise:** whether a red side that has lost its command centers actually plans a visibly different/less-repetitive set of opportunistic offensive targets turn-over-turn (the shuffle is proven; the *felt* effect on a real ATO is not), whether its offensive package count visibly thins after heavy decapitation (the A2 throttle: red's ATO should carry fewer strike/BAI/OCA packages but keep planning BARCAP/defense and never drop to zero offense), and whether the SITREP band reads the enemy C2 status correctly across turns.
- **Setup:** **Germany — Red Tide** is now the reference case — its advanced_iads laydown fields a 9-node red command-center network and **preseeds `c2_decapitation_effects: true`** (2026-07-07), so a NEW Red Tide game exercises this directly. Play a few turns noting red's offensive targets, then bomb red's command center(s) and play a few more.
- **Pass:** with red's HQs intact, red's offensive target selection is its usual (near-)deterministic set; after the command centers are destroyed, red's opportunistic offensive targets visibly loosen (it services lower-priority strikes/OCA/BAI it wouldn't have before), while its **reactive defense is unchanged** (BARCAP/DEAD-response still deterministic); the next kneeboard SITREP shows "Enemy C2 degraded: N/M known command posts operational", where M counts only the command posts on blue's map. Turning the setting off restores the stock deterministic planner exactly.
- **Fail signature:** red plans identically before and after the HQ kill (the bonus isn't reaching the shuffler — check `_unpredictability_for` and that the campaign actually has `commandcenter` TGOs); red's *defensive* tasking changes too (the §17 boundary broke — only opportunistic tiers pass through `shuffled_by_priority`); the SITREP line never appears or shows wrong counts (`c2_status_line` / `red_c2_status` wiring); any change at all with the setting off (the gate broke).

### B17 — Carrier deck spawn policy (six-pack last resort + MP slot timing) · §64 · ✗ REGRESSED (2026-09-17, test 36)

**2026-10-07, test 54 — player carrier slots were unflyable; the six-pack setting is removed.**
Its default late-activated player carrier groups at t=1 s, so in MP their slots showed a
delayed start and the CPY pilots moved to dynamic slots. Player carrier flights now spawn
at mission start. Next MP carrier fly: every fragged boat slot joins from mission start.

**2026-09-18 — the fix is removed (DM call).** The deck cap (#1032) and the Tomcat spawn
delay (#1020) were both taken out, so every carrier flight parks on the deck again and the
test 36 failure below can recur on a boat fragged past its deck. Row stays ✗ REGRESSED.

**2026-09-17, test 36 — the fail signature reproduced, and worse than the 2026-07-17 reading.**
Long Road to H3 turn 2 fragged **50 aircraft in 24 groups onto one CVN-71**, all
`TakeOffParkingHot`. **17 of 50 ever existed** in the ACMI; the deck took spawns up to t=233 s
(14 airframes) and every carrier group activating from t=281 s on failed silently — no log
line, no error, a `state.json` record with two identical samples at the boat reference and
`alt = -1`. Two groups launched; twelve more sat hot on deck for 71 minutes. Five escorts
based ashore were stranded at their ESCORT HOLD anchors because their carrier primaries never
flew. Full write-up in the test 36 section above.

**The engine has no deck-capacity check.** `flightgroupspawner.py:370` gates the
`NoParkingSlotError` retry (runway start, then air start) on `isinstance(cp, Airfield)`, so the
carrier path at line 269 (`_generate_at_group` on the carrier `ShipGroup`) has no fallback at
all — pydcs places the unit and DCS quietly declines. The remedy this row's own fail-signature
note already names applies: exempt overflow flights at generation, because the deck count is
knowable. Test 9's "full deck" was 24 on CVN-72 and launched clean, so the ceiling sits between
24 and this capture's 50; the observed placement cutoff here was 14.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **partial, one more data point.** Test 32's six CVN-71 BARCAP Hornets activate at 1 s (the LAST_RESORT trick) and all launched; the Tomcat 2-s rule from #1020 (removed 2026-09-18) has not generated yet (no carrier Tomcats since 09-14: test 33's CVN-62 flew Hornets only). Six-pack overflow and MP slot timing still unobserved.

**2026-09-15, test 32** — six Hornets (three BARCAP pairs), the E-2D and the A-6E tanker were on CVN-71 at T0; all six Hornets were assigned catapults and airborne inside the first four minutes, none stuck. No Tomcat on the deck, and the build predates #1020.

> **Test 9 flown 2026-08-18** (Syria `operation_desert_trident`, `Tacview-20260818-214946` + `dcs.log` + `state.json` + the generated `.miz`) — **the six-pack was never needed on a genuinely full deck.** Read off
> the generated `.miz`: **24 deck spawns on CVN-72** (8 BARCAP + 16 SWIFT BAI) plus 8 on
> LHA-1 Tarawa, **all 32 `TakeOffParkingHot`**, with `carrier_deck_decorations` on. The DM's
> read: *"All aircraft on the carrier launched without issue on a full deck / 6 pack was never
> used."* That is the last-resort path staying unused at a deck load well past the 16 spots ED
> documents.

**History:** built 2026-07-16 off the user finding "AI taxi into me on the supercarrier / get stuck between me and the catapult"; the placement/hold split — AI always ≥1s late-activated, player flights taking the 1s placement activation under LAST_RESORT and keeping the six-pack under SIXPACK_FIRST, the delayed-client uncontrolled+StartCommand path, the WARM/RUNWAY/airfield no-ops, and the boolean→enum save migration — is unit-tested in `tests/missiongenerator/test_carrier_deck_policy.py` + `tests/settings/test_carrier_deck_policy.py`. How DCS actually places and taxis the deck is DCS-only.

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — PARTIAL.** Turn 2 recovered **7 aircraft onto CVN-71** (4 F-14B(U), 3 F/A-18C; final positions 20–77 m from the boat), so deck spawning did not wedge the recovery cycle and nothing was stuck. Turn 1 ended with every flight still airborne at 104 minutes, so it says nothing either way. Not observed: the six-pack last-resort path specifically, or MP slot timing.
**2026-08-16 5th test — a jet that never taxied, and it is the port quarter.** The DM reported "Enfield 2-2 never taxied". In the recording, `CVN-71 Theodore Roosevelt Escort|2|4` spawned as a pair at t+803: Pilot #1 on the six-pack row at ship-frame (−13.0, +33.8) taxied 237 m and launched; **Pilot #2 at (−85.4, −33.4) — the port-quarter spot — moved 10.8 m in the following 20.6 minutes and never left**. It was not alone there: `Kutaisi Escort|2|2` Pilot #2 had spawned 11 m away at t+297 and took until t+1445 (19 minutes) to get off the deck. Every flight spawned at or before t+803 launched *except* that one; every flight spawned at t+1447 or later (the whole PUFFERFISH package, 11 jets) was still parked when the recording ended 590 s later, which is inside a normal Hornet cold-start and so proves nothing. **Read:** the port-quarter row looks like a queue that can dead-end, not a §72 decoration collision — the port junk row was removed 2026-07-21 and nothing §72 places is on that side. Worth a deliberate look on the next carrier fly: park two AI pairs onto the port quarter and watch whether the second ever moves.
- **What CI cannot exercise:** the two deliberate unknowns — (1) whether DCS genuinely overflows delayed spawns *into* the six-pack once the other deck spots are full (the literal "last resort" semantics; the 1-second trick is only proven to move spawns *off* it), and (2) deck crowding/behavior with several client flights parked uncontrolled from mission start (the reason upstream late-activated carrier flights). Plus the core payoff: does an AI flight still jam against the player now that the player is parked clear of the cat 1/2 taxi lane.
- **Thinned-deck data point (2026-07-17 night fly, fresh turn 1 post-#633 deck cut, session
  `tacview-test-analysis-5bb161`):** big improvement — every planned carrier package launched
  (Khasab BARCAP F-14Bs, E-2C, S-3B all flew; no lost SEAD/DEAD packages) and recoveries produced
  no crashes. Residual: **4 late-alert BARCAP jets despawned on deck** (the Stennis BARCAP F-14B
  pair at t=2061 and the "LHA-2 Saipan BARCAP" Hornet pair at t=2445, same-second pair removals
  at deck level, briefed departures 2:33–3:18 h — stuck-alert cleanup, not gridlock). **Flags found in passing (both resolved next session):** the
  "LHA-2 Saipan BARCAP" Hornets on the CVN deck were a MIS-READ — Retribution group names lead
  with the package TARGET, so those were CVN-based Hornets flying BARCAP *over* the Saipan CP
  (basing was always correct; no campaign edit needed). The real defect was the **CP-name/hull
  mismatch** (CP "CVN-74 John C. Stennis", hull CVN-71 Theodore Roosevelt + 71X card): the
  supercarrier upgrade keys on the CP name and "CVN-74" fell through its else-branch to CVN_71.
  **FIXED engine-side (new games):** `hull_consistent_carrier_name` deals a supercarrier game
  only upgrade-mapped names (the name picks WHICH supercarrier) and otherwise prefers the
  hull's own display name (free Stennis = CVN-74, Tarawa = LHA-1); existing saves keep their
  boat via the legacy CVN-71 fallback. Tests `tests/test_carrier_naming.py`; features doc §65.
- **Deck over-capacity data point (2026-07-17 flown Scenic Route Merged, AI-only):** the merged campaign bases **39 fixed-wing on the one CVN-71** (16 F-14B + 23 Hornets — two carriers' wings merged onto one boat). Consequences observed in the Tacview + log: the delayed CARACAL SEAD (2-ship) + CARACAL DEAD (4-ship) packages activated on deck at t≈18 min, **never taxied, and were silently despawned by DCS's stuck-AI cleanup** 53–58 min later (whole groups removed in the same second, no crash/ejection events — the mission simply lost its SEAD and DEAD), and **3 Stennis-Escort Hornets crashed during recovery** (real CRASH events + crew ejections → the sea survivors that drove the CSAR findings). Not a §64 bug — LAST_RESORT only moves spawns off the six-pack — but the campaign-authoring lesson is a deck-capacity ceiling: a boat carrying two air wings loses its delayed packages to gridlock and its recoveries to a fouled deck. Watch both signatures (same-second group despawns of never-taxied deck jets; landing crashes with ejections at the boat) on any crowded-carrier fly.
- **Setup:** a carrier campaign with a player Hornet flight + at least two AI carrier flights (cold starts). Leave `carrier_deck_policy` on its default (Six-pack is overflow parking); set `never_delay_player_flights` OFF and give one player flight a package TOT ≥ 15 min out to exercise the MP slot fix. Generate for multiplayer, slot in, start up slowly, watch the deck.
- **Pass:** the player jet spawns somewhere other than the six-pack (fantail/island/elevator spots); AI flights spawn elsewhere too, taxi to the cats, and launch without deadlocking on the player; the late-TOT player flight's slots are pickable from ~mission start (jet parked cold, engines off) and its AI members only crank at the planned push time; flipping the setting to "Players spawn on the six-pack" puts the player back on the six-pack.
- **Fail signature:** the player still spawns on the six-pack under last resort (the 1s activation didn't fire — check `FlightLateActivationTrigger<gid>` exists in the miz triggers); a delayed player flight's slots missing until push time (the uncontrolled path didn't take — check the group is `uncontrolled` with a `FlightStartTrigger<gid>`); AI wingmen of the delayed flight crank at mission start (StartCommand push not holding); aircraft spawning stacked/inside each other when the deck is heavily loaded (DCS refused to overflow gracefully — fall back to exempting overflow flights at generation, we know the deck count); a client slot unenterable in MP after the 1s activation (late-activated client groups misbehaving — revert clients to spawn-at-start and accept the six-pack in that mode).

### B19 — Weather-aware auto-planning · §67 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from the captures.** Three turns ran on a Raining preset (tests 6 and 7 on Desert Trident and Sinai, test 20 on Afghanistan), but the ATO is not in a capture and the recon-suppression clause has no control: Desert Trident's clear-sky test 9 planned no recon flight either (the campaign fielded none), and the September campaigns carry `auto_add_tarps_recon` off. Needs the app open on a rain turn.

**History:** built 2026-07-17; the sky classifiers, the recon-suppression gate, the storm demotion's order preservation + factory-name lock, and the HTN integration are unit-tested in `tests/retlab/test_weather_planning.py` + `tests/test_armed_recon_planning.py` — whether a real stormy turn's ATO visibly reads different is app-level
- **What CI cannot exercise:** a real campaign turn whose §47 weather rolled Raining/Thunderstorm producing an ATO with no auto-added TARPS/drone recon flights (rain+storm) and the CAS/BAI/interdiction packages planned after the strike/OCA/IADS ones (storm only) — and a clear-sky turn reading exactly like pre-feature.
- **Setup:** any campaign with `weather_aware_planning` ON (default). Ride turns until the SITREP/briefing weather shows rain or a storm (or force it by re-rolling turns); open the ATO.
- **Pass:** on a rain/storm turn no Strike/DEAD/Armed Recon package carries the optional TARPS/recon add-on flight (player-planned recon still plannable by hand); on a thunderstorm turn the offensive plan leads with strikes/OCA/IADS and the front-line CAS/BAI packages sit later in the plan (they still exist if jets remain); on a clear turn the ATO is indistinguishable from the setting OFF.
- **Fail signature:** recon birds fragged into a thunderstorm (the gate didn't reach `_maybe_plan_tarps_recon` — check `recon_suppressed` reads the right game); CAS vanishes entirely in a storm (demotion should reorder, never remove — check `demote_weather_hostile_methods` keeps the set); a clear-sky ATO differs with the setting toggled (the no-op contract broke); a crash on an old save without conditions (the getattr guards).

### B20 — Adaptive procurement: SAM repair + price-weighted choice · §68 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised in any capture.** `auto_repair_air_defenses` has been on in every save since test 1, so red has been rebuilding sites all along, but the effect is a turn-over-turn map read the app must show; a mission capture holds only the site as it was at generation. Needs a struck site watched across two or three turns in the app.

**History:** built 2026-07-17; the posture/phase budget-split coupling was REMOVED 2026-07-21; the repair's gate/cap/priority/budget/exclusions/wreck-cleanup and the weighted-choice gate are unit-tested in `tests/retlab/test_adaptive_procurement.py` — the felt economy needs a multi-turn campaign
- **What CI cannot exercise:** red visibly rebuilding a struck SAM site over following turns (`auto_repair_air_defenses` ON): launchers/radar coming back alive at the same site a couple of units per turn, the site's threat ring re-growing, no duplicate wreck models under the repaired units.
- **Setup:** a campaign with a red SAM belt (Red Tide post-lock, or any modern laydown). Turn ON `auto_repair_air_defenses` (Campaign Management → Commander economy; `adaptive_procurement` is already default ON). DEAD a red SA-10/SA-2's radar + a launcher, end turn a few times, watch the site on the map/intel and red's Finances-visible behavior.
- **Pass:** the struck site regains ~2 units per turn (radar first) while red's budget shows the spend; a fully-dead site only rebuilds after the partially-alive ones; command centers/comms nodes never come back; with the toggle OFF the site stays dead forever (pre-feature behavior).
- **Fail signature:** the whole site back in one turn (the cap broke); a repaired unit standing next to its own wreck model (`_clear_wreck_near` didn't fire); C2/comms nodes regenerating (category filter broke — §51/§52 must stay permanent); threat rings not re-growing after repair (`invalidate_threat_poly` not reached); blue money spent on repairs when the player manages repairs manually (the `manage_runways` coupling broke).

### B29 — Custom victory conditions (VICTORY chip + alternate endings) · §75 · ◐ PARTIAL

**2026-10-12 — the two generic sliders were REMOVED on the DM's call** (both 0 in his defaults and every save). Only an authored campaign `victory:` block can end a war this way now.

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **the off half again, headless.** Both knobs 0 and no campaign `victory:` block; `victory_sitrep_lines` returns nothing on the turn-2 save. The knob-on half is an app pass.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side; both knobs are 0 in every save**, so no alternate ending has ever been configured. Nothing for a capture to show.

**History:** 2026-08-05, user pass `units-runway-generation-bf755e` — "shows in the UI": the **render half is confirmed**, i.e. the green VICTORY chip + the live-value condition checklist draw on the web ribbon, which needed the CI client rebuild to be exercised at all. **Still owed = the ending itself** — no shipped campaign authors a `victory:` block, so the chip has only ever been shown against the two generic knobs; drive `alternate_victory_domination` or `alternate_victory_attrition` to an actual met condition and confirm the war ENDS, announces once via the `victory_announced` latch, and reports through the SITREP digest rather than the stock territory default) (was ☐ UNTESTED, built 2026-07-19 off the Discord thread — Ramius007's victory CPs/domination + Starfire's HVT-destruction/strength-attrition/air-denial asks; the whole condition engine, the AND-within-entry semantics, loss precedence, the no-vacuous-win guards, the announce latch, and the real `check_win_loss` branch order are unit-tested in `tests/retlab/test_victory.py` (30 tests), and the client block passed tsc + the full jest suite locally — but the app render and a knob-driven ending end-to-end are app-only
- **What CI cannot exercise:** the ribbon VICTORY chip + expander block actually rendering (the client is not CI-type-checked; needs the CI client rebuild to even ship), the Qt settings page showing the new "Victory conditions" section, the Victory!/Defeat! dialog firing off a knob-met condition on a real game, and the SITREP band line on the next turn's kneeboard.
- **Setup (app pass, no DCS needed):** any small campaign. Set Campaign Management → Victory conditions → "Domination victory" to a value just above your current base share (the expander shows the live percentage). Play or skip turns until a capture crosses the threshold. Separately: load any campaign with the knobs at 0 and confirm no VICTORY chip renders anywhere.
- **Pass:** with a knob set, the green VICTORY chip appears on the ribbon; clicking it unfolds "Victory conditions — Any one of these ends the war:" with live values that update as bases change hands; crossing the threshold at a turn boundary pops the standard Victory! dialog AND the events feed carries "Victory condition met: Hold N% of the bases"; the next turn's SITREP (web LAST TURN + kneeboard band) would have carried the "Victory: …" line; with both knobs 0 and no authored block, no chip, no block, no SITREP line — byte-identical behavior. (The will/supply meter conditions + the absorbed negotiation ending were REMOVED 2026-07-21 with the will/war economy, so only the territorial/destroy/strength/air-denial conditions remain to exercise.)
- **Fail signature:** a win/loss firing at turn 0 or on load with a threshold below the starting share (working as designed — but if it fires with the knob at 0, the gate broke); the chip present with nothing configured (the overview leaked); a "Victory condition met" banner repeating every check (the `victory_announced` latch broke); the territory win firing while neutral bases are counted in the denominator (the `_territory` filter broke); an authored-campaign block win firing for a condition whose live prose shows unmet (AND semantics regressed to OR).

### B32 — Sea-supply convoys + coastal anti-ship engagement · §78 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **never exercised, and it cannot be on any campaign flown so far.** Silkworm batteries stood in two missions (Noisy Cricket, tests 12 and 32: six groups each) and no blue ship came within their reach either time; no other capture had a coastal battery at all. No cargo-ship group exists in any of the 26 readable mizzes, so no sea transfer has ever been generated in a test, with `cargo_ship_convoys` on in every save. The row needs a campaign with a shipping lane inside a red battery's range and a ground transfer ordered across it; none of the flown campaigns has that geometry.

**2026-09-15, test 32** — three Silkworm coastal groups (DOG, PELICAN, DEER) stood on the red coast; no blue ship came within their range and none fired. A HARM killed DOG's search radar. Not exercised.

**2026-08-21, DM call — the coastal shoot-and-scoot is dead, this row is not.**
`coastal_missile_relocation` (§49's coastal opt-in) was removed: "it doesn't work and was
proven." The vanilla Silkworm battery is a fixed emplacement — `hy_launcher` and
`Silkworm_SR` are both in `IMMOBILE_UNIT_IDS` on flown evidence — so the setting could only
route a mod launcher nobody fields. A coastal battery now always stays where the campaign
put it, which is the geometry this row's engagement check assumes anyway. Nothing below
changes.

**History:** (built off the "increase the cargo ships / use the anti-ship batteries" ask; the convoy partition sizing/cap/conservation, the OFF single-hull path, the proportional and overlapping-type commit, and the coastal-ROE gate (on/off/non-coastal) are unit-tested in `tests/retlab/test_cargo_ship_convoy.py` (11 cases). What no test can model is DCS naval AI: whether a coastal Silkworm on weapons-free actually acquires and hits a moving 12-kt cargo ship, and the convoy's behaviour running the coast).
- **What CI cannot exercise:** whether a `hy_launcher` (Silkworm) coastal battery set weapons-free + red alarm autonomously fires on a passing enemy cargo-ship group and scores hits at sea-lane range (DCS coastal-missile-vs-moving-ship AI is the unknown); whether the multi-hull ship group sails the lane in formation without beaching or bunching; and whether proportional losses read correctly in the debrief when only some hulls are sunk.
- **Setup:** a campaign with a live sea lane whose route passes near an enemy coastal battery. Tanker War 1988 is the target once its strait lanes are authored; otherwise any campaign with a `shipping_lanes` lane routed within Silkworm range of an opposing `hy_launcher` site. Order a ground-unit transfer across the lane (or let the AI), then fly (or fast-forward) the turn and watch the convoy transit the coast.
- **Pass:** the shipment spawns as **several** cargo ships (not one) sailing the lane in formation; a coastal battery on the enemy shore engages them as they pass within range; and if some ships are sunk, the debrief records **only those hulls'** share of the reinforcement lost (the rest arrive at the destination CP), not the whole transfer.
- **Fail signature:** still a single cargo ship despite `cargo_ship_convoys` on (the manifest path didn't take — check the shipment actually travels by sea, not road); the coastal battery sits idle as the convoy passes in range (weapons-free/alarm not applied, or the lane is out of the battery's reach — geometry, not code); sinking one ship of a convoy wipes the whole reinforcement (proportional commit regressed) or sinking every ship still delivers units (kill mapping missed a hull); ships spawning on land / stuck at the lane origin (waypoint[0] not in water — an authoring issue, not §77).

### B39 — Cross-turn naval magazines · §81 · ◐ PARTIAL

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **the release half passes again; the carry-over cannot be read.** Seven groups armed. Weapons-free came 131 s to 815 s into the mission, one group at a time. ROACH (Kuznetsov) and its escort each fired 6 P-700s and logged `salvo complete (6 this mission) -- holding`. When the Harpoon raid arrived both logged `under attack -- released weapons-free` and fired the rest: 12 and 20, matching the recording and `naval_magazines_state`. Both ships sank, so there is no next-turn count to check.

**2026-09-23 — new leg: the SITREP line.** `winchester_lines` is now wired. **Pass:** after a mission where a blue group fires anti-ship missiles, the next turn's SITREP (kneeboard band, web LAST TURN, Qt debrief) reads `<group>: N anti-ship missile(s) fired, M left`, or `WINCHESTER` at zero. **Fail:** no line, or a red group listed.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged.** Every mission since test 11 released on schedule and fired no anti-ship missile, so the salvo cap has still not been exercised; Vectron's Claw turn 3 remains the mission that would.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — BABIRUSA (red, Naval Two Ship) released at +318 s, the Forrestal group at +708 s and +1098 s; no anti-ship shot all mission, `naval_magazines_state` empty. Same shape as tests 24, 30 and 32.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — the test-30 shape again: `0132 | TARANTULA (Naval Two Ship)` released weapons-free at +118 s with 12 rounds in the magazine table, and is not in the `.miz`; MOSQUITO is. Six groups released between +66 s and +326 s, 52 s apart. No anti-ship shot all mission; `naval_magazines_state` empty.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1) — the plugin armed on groups
that were not in the mission. `NAVALMAGAZINES|: 0061 | MONSTER (Naval Two Ship) released
weapons-free` (then SHOEBILL and HORNBILL) logged between +153 s and +228 s, but the `.miz`
holds only the six blue ship groups; the three red groups exist in the campaign and were not
generated (culling is the likely reason; the save was not captured). `naval_group_magazines`
lists every live naval group rather than every spawned one, so the release is a no-op on a
name `Group.getByName` cannot find. Harmless this turn. When the plugin is next touched, skip
groups the mission does not hold, so the log describes what the mission did.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **release and stagger work; the salvo cap is still unexercised.**
`NAVALMAGAZINES|: armed -- 2 naval group(s), stagger true (120s-900s), metered true, salvo cap 6`,
then the carrier released weapons-free at +137 s and the escort at +951 s, so the stagger is real
and separated the two. No `WINCHESTER`, no `salvo complete ... holding`, and
`naval_magazines_state` came back **empty** — nothing was debited, because no anti-ship shooting
happened. The row's outstanding item is unchanged: it still needs a *loaded* group that fires,
stops at 6, and logs the cap.

> **Test 11 (2026-08-19, `Tacview-20260819-203334`) — the turn-2 carry-over PASSES; a new hole
> opened and is fixed.** Turn 2 of the same Vectron's Claw save, with the salvo cap shipped:
>
> - `NAVALMAGAZINES|: armed -- 7 naval group(s), stagger true (120s-900s), metered true, **salvo cap 6**`
> - `0079 | CARACAL (Carrier) stays ReturnFire at release (magazine dry)` — **the last leg this
>   row owed.** The Kuznetsov spent its 8 rounds on turn 1 and opened turn 2 empty, so the
>   debit persists across the turn boundary and a fired magazine does not refill.
>
> **But the cap still has not been exercised**, and the reason is the defect this test found:
> the only anti-ship fire all mission came through the one path that bounded nothing. Blue put
> 16 AGM-84D into the Kuznetsov group at t=1296; the attack rule freed it; and being *already
> dry*, it returned to the `dry` branch on every shot — which exits before the salvo check and
> never drops an attacked group to ReturnFire. It fired **12 P-700 over 336 s against a cap of
> 6**, and called `WINCHESTER` four times doing it. Both fixed 2026-08-19: an empty group may
> answer an attack for one `salvoPerMission` past empty and then holds even under fire, and the
> winchester call is latched to once per group.
>
> **Still owed:** a mission where the cap actually bites — a *loaded* group firing, stopping at
> 6, and logging `salvo complete (6 this mission) -- holding`. Vectron's Claw turn 3 with
> DRAGONFLY (28 rounds left) in range would do it.

> **UNBLOCKED and largely passed, 2026-08-19.** The "no Starfire campaign has a red navy" block
> below was wrong: **Caucasus — Vectron's Claw** (Starfire, USA 2005 vs Russia 2010) fields a
> Kuznetsov, a Slava and two escort groups against a CVN-71 CSG and an LHA ARG. Flown turn 1
> (`Tacview-20260819-180629` + its `dcs.log` + `state.json`), and it exercised every leg the row
> had left open **except** the turn-2 carry-over:
>
> | Pass criterion | Result |
> |---|---|
> | One release per group, spread across the window, not all at t≈120 | **PASS** — `armed -- 7 naval group(s), stagger true (120s-900s), metered true`, then five scheduled releases at separate times plus two attack releases (`0087 \| BLOODHOUND (Carrier) under attack` and `0088 \| BLOODHOUND (Escort) in the attacked formation`, same second — the formation rule firing in the field) |
> | Anti-ship launches spread across the mission, not one opening ripple | **FAIL** — the Kuznetsov spread 8 P-700 over 208 s, but the Slava-led group put **all 16 P-500 up in 36 s** (t=274.2–310.2). This is what the salvo cap was built for; re-fly to confirm |
> | A spent group logs `WINCHESTER` and stops launching | **PASS** — `0079 \| CARACAL (Carrier) WINCHESTER anti-ship` after its 8th round, no further launches |
> | A held/spent group still fights aircraft | **PASS** — the released blue CSG answered with 23 SM-2ER, 7 SM-2, 11 RIM-116, 2 Sea Sparrow; one P-500 leaked and killed `0419 \| FFG Oliver Hazard Perry` |
> | The debrief debit matches Tacview | **PASS, exactly** — `naval_magazines_state` reported 16 (DRAGONFLY) + 8 (CARACAL Carrier); the ACMI holds exactly 16 P-500 and 8 P-700 |
> | Turn 2 opens with the reduced stock | **STILL OWED** — turn 1 only |
>
> **What is left:** generate turn 2 of the same save and confirm the emitted `remaining` starts
> at 28 for DRAGONFLY and 0 for CARACAL (Carrier), and that the Slava's launches now stop at
> `salvoPerMission` instead of running to 16.

**History:** → emitter fix applied, rework decision open (2026-08-05 first fly, session `pr-merge-code-audit-7e8b4c`, two Marianas 2027 Tacviews `Tacview-20260805-184424` + `-190738`: **(1) the switches never reached the runtime** — both missions logged `NAVALMAGAZINES|: armed -- 29 naval group(s), stagger false (3600s-3600s), metered false` despite the settings being on, because `LuaData.serialize` silently DROPS a node's `add_key_value` entries whenever the node also has child items (the magazines list survived, `stagger`/`metered` vanished from the miz; plugin options were unaffected — the user's 3600s window edit took). Fixed same day: the switches are now named child items (`add_item().set_value()`, the flown CombatSAR `autoSpawn` pattern) + a serialization-level regression test; an AST audit found NO other emitter mixes the two shapes. **(2) The load-bearing unknown is ANSWERED, BADLY** — generation-side ReturnFire worked (that half doesn't ride the emitter), so both missions accidentally ran a pure held-fleet experiment: in the big test blue Super Hornets fired 13 AGM-84D at the SUGARGLIDER Type 071 LHA group (t=2162–2232), the LHA sank at t=2675, and its HHQ-16 escorts a few km away **never fired a single shot** at the missiles — across both missions (110 min, 63+ ship units) ZERO ship weapon launches of any kind, and an F-22 loitered at 24.9 km from an 054A/052B group unengaged. Contrast the 2026-08-03 WeaponFree fly (99 SM intercept shots): **a DCS ship on `ReturnFire` mounts no missile defense at all** — a held or winchester group is a defenseless one, the exact fail case §81's note flagged. **Rework decided + BUILT same day (DM call: release-on-attack):** the first ENEMY weapon aimed at (SHOT target) or landing on (HIT) a managed group releases it to weapons-free immediately — held OR winchester; a friendly shot never releases (§77 guard); an attacked winchester group is never re-dropped to ReturnFire and its overshoot stays counted for the debit; handler now registers under either tier. 5 new harness cases + the serialization regression test. **Re-fly same day (`Tacview-20260805-200950`) — "sorta… CIWS fired but no SAMs": the plumbing PASSED** (`stagger true … metered true` at load; `0057 | SUGARGLIDER (LHA) under attack -- released weapons-free` in the log; the released LHA fired AK-630 CIWS at t=2644.6, its first shots of the mission, dying at t=2668) **but exposed the next layer — releasing the TARGETED group is not enough.** A carrier/LHA objective is **two DCS groups** and the area-defence SAMs ride the **escorts**: the 16 AGM-84D were aimed at the Type 071 (whose whole AAW fit is that CIWS), while the HHQ-16 escort group **1.91 km away** was never targeted, never released, and watched. Fixed same day — an attack now frees every managed friendly group within `formationReleaseKm` (default **15 km**, plugin option, 0 = targeted-only), **one hop, never a cascade**; the flown geometry makes the radius safe (screen 1.91 km, next task force 59.02 km). 4 more harness cases (escort freed + far group not, no-cascade A→B→C, enemy formation never freed, switch-off). **Re-fly #2 (`Tacview-20260805-203549`) — THE RELEASE FIRES; the shooting is another matter.** Log: `0057 | SUGARGLIDER (LHA) under attack` + `0058 | SUGARGLIDER (Escort) in the attacked formation -- released weapons-free`, **same second**. Full chronology, re-verified against the raw ACMI (3,509 frames, zero backward time jumps): first AGM-84D away **t=2146.8** (105+ km out) → escort's first HHQ-16FE **t=2154.9** → 4 more through t=2214 → the LHA's AK-630s open up **t=2638.9** (1,273 rounds) → **first Harpoon arrives t=2644.2** → escort terminal defence **t=2645–2693** (5 × HHQ-10 + 194 CIWS) → **LHA sinks t=2687**. **Proven:** the escort was weapons-free and firing **eight minutes before any missile reached the fleet**, so it cannot have been reacting to a hit — the release fired on the *launch*, and in the previous fly that same escort sat silent throughout. **NOT proven, the honest read:** the five early HHQ-16FE shots were **wasted** — no enemy aircraft came within **106.3 km** of the escort all mission, beyond the missile's reach, so the AI reflex-fired at an unreachable target; the only effective layer was terminal HHQ-10/CIWS, and all 16 Harpoons reached terminal (0.2–2.5 km, none intercepted en route). 16 AShM against two escorts is a genuine saturation strike, so a lost amphib is a fair outcome — but "the escorts defended their flagship" would overstate it. **Open follow-up, not a §81 defect:** a released ship burning long-range SAMs outside their envelope and only defending at ~3 km is DCS naval-AI behaviour; its own investigation if it matters. **Still owed (the N1/N2 legs, NOT the defense one):** the fly carried leftover diagnostic plugin options `releaseMinS/MaxS = 3600`, so no group was ever released on schedule in a 48-min mission and **no ship fired a single anti-ship missile — the magazine was never exercised**. Re-fly #3 with the options back at **120/900**: pass = AShM launches spread across the mission, a `WINCHESTER` line, the debrief debit matching Tacview, and turn 2 opening with the reduced stock. Evidence the stagger itself fires: a separate smaller mission the same evening (5 naval groups, 120s–900s) logged `0001 | PIG (Naval Two Ship) released weapons-free` on schedule.) (was ☐ UNTESTED, built 2026-08-03 off the flown Marianas 2027 Tacview — 374 weapon launches, essentially all inside the first five minutes — and the DM's read: "in real life they would not dump the entire Chinese fleet's magazines in the opening shots of the war." Ships now generate `ReturnFire` and are released to weapons-free one group at a time across a window (N1), and every anti-ship missile fired is charged against a persisted per-group campaign stock that never rearms, dropping a spent group back to `ReturnFire` (N2). The seeding/idempotence, the debrief-report-is-the-only-debit-site rule, the clamp at zero, the dry-group-still-emitted rule and the §63 weapon-set disjointness are unit-tested in `tests/retlab/test_naval_magazines.py`; the emitted shape in `tests/missiongenerator/test_navalmagazineluadata.py`; and the release stagger, the shot metering, the winchester ROE drop and the no-node no-op in `tests/lua/test_navalmagazines_runtime.py`.)

**2026-08-16 flights (session `c86c58dd`, two Caucasus turns; Tacview + dcs.log + state.json + the flown save) — the 2026-08-05 root-cause claim was wrong, and the real fix has now landed.** This row's history records the `LuaData.serialize` scalar-drop being worked around (`add_item().set_value()`) and states that "an AST audit found NO other emitter mixes the two shapes." **Two others did** — `deckdecorluadata` and `reactiveredluadata` — and both shipped broken in the field for the eleven days since. The serializer itself is now fixed (RetLab#847), so the workaround is no longer load-bearing (leave it; it is correct either way). **Positive evidence for this row from these flights:** turn 1's `state.json` recorded `naval_magazines_state: [{'fired': 8, 'group': '0079 | MANTIS (Carrier)'}]`, matching the Tacview exactly — the red Admiral Kuznetsov put **8 P-700 Granit** into the blue CSG between T+11.1 m and T+15.8 m (~40 s apart), the CSG answered with 18 SM-2ER, and nothing sank on either side. Turn 2, the same hull fired **zero**. So the debit persists and a fired magazine does not refill. Still owed from the N1/N2 legs: the release stagger on real options (the earlier fly carried leftover 3600 s diagnostics) and a `WINCHESTER` line.
- **What CI cannot exercise:** **the load-bearing unknown — whether a DCS ship on `ReturnFire` engages an inbound aircraft that has not yet fired at it.** DCS ROE is per *group*, not per weapon type (there is no "no more anti-ship missiles but keep shooting SAMs"), so `ReturnFire` is what both a pre-release ship and a winchester ship sit on. If DCS does not honour it that way, a spent ship is also a defenceless one — acceptable perhaps, but it must be a deliberate call. **Check this before trusting either tier.** Also unmodelled: whether the harness's ROE option id (0) and value (3) are what the DCS naval controller actually accepts, whether real `S_EVENT_SHOT` weapon `typeName`s match the pattern list on the hulls a campaign actually fields (the CurrentHill PLAN ships especially — the whole magazine silently never depletes if they don't), and whether a staggered fleet still produces a *fight* rather than a fleet that never quite engages.
- **Setup:** Marianas 2027 (the campaign this came from — modern PLAN vs a US CSG, both sides' missiles out-ranging the map). Enable **both** settings plus the "Naval magazines & weapons release" plugin, start a **NEW game**, and fly two consecutive turns of a naval engagement with Tacview running. On turn 1 note the `NAVALMAGAZINES|` lines in `dcs.log` (armed count, each release, each winchester); after the debrief, check the save's `naval_magazines` for the debit; then generate turn 2 and confirm the emitted `remaining` starts where turn 1 ended.
- **Pass:** the log shows one release per group spread across the window rather than all at t≈120; the Tacview shows anti-ship launches **spread across the mission** instead of a single opening ripple; a group that empties its tubes logs `WINCHESTER` and stops launching missiles **but still engages aircraft with its SAMs**; the debrief debit matches what Tacview shows fired; and turn 2 opens with the reduced stock (so a 20-turn campaign cannot re-dump).
- **Fail signature:** every group releasing in the same second (the even spread regressed, or `releaseMaxS` ≤ `releaseMinS`); ships that **never** open fire at all (the release ROE option isn't reaching the naval controller — try the literal `ROE_ID`/`ROE_WEAPON_FREE` values, or DCS wants `AI.Option.Naval` specifically); **a winchester or pre-release ship sitting passive while aircraft attack it** (the load-bearing unknown resolved badly — the honest options are to accept it or to abandon N1's hold, since per-weapon ROE does not exist); magazines never depleting despite launches (the fired weapon's `typeName` doesn't match `ASHM_WEAPON_PATTERNS` — read the real name out of `dcs.log`/Tacview and extend the pattern list, but **never** with a land-attack family); a magazine that debits *twice* per shot or moves at generation time (the §63 double-count or the regeneration-safety rule broke); or §63 cruise-missile raids suddenly costing anti-ship stock (a land-attack family leaked into the pattern list).


---

## C. Support flights

---

## D. Loss accounting (upstream-core)

---

## E. SOF insert generation · #85 · ☑ VERIFIED (2026-06-24)
- **Setup:** A SCAR commander-capture campaign that plans a SOF C-130 insert.
- **Pass:** The SOF C-130 **ground-starts** (incl. the runway fallback when no
  parking is free) and the **EW (`c130j`) plugin is skipped** on that airframe.
- **Fail signature:** SOF C-130 air-spawns, or the EW menu/behavior bolts onto
  the SOF insert because the airframe matched `eligibleTypeNames`.

---

## F. SCAR — CLOSED (no passes outstanding)

> **Collapsed 2026-08-05** (DM call: "clean up all of F"). Every row in this section is closed,
> so it tracked nothing. The full pass criteria and per-row verification notes are preserved in
> git history — `git log -p -- docs/dev/retlab-ingame-pass-checklist.md` before 2026-08-05, or
> `git show 767d42a94:docs/dev/retlab-ingame-pass-checklist.md`.
>
> **Verified, and still live features:** F1 HVT movement + capture loop (2026-06-23) ·
> F2 command-post intel fog (2026-06-24) · F3 player-flown SOF insert + C-130 EW exclusion
> (2026-06-23, per-group mechanism re-confirmed via J3 2026-06-28) · F4 results bridge
> round-trip (2026-06-17/18) · F6 SCAR auto-planning appears in the ATO (2026-06-24).
>
> **Retired, and deliberately never to be re-flown:** F5 mis-ID budget penalty · F7 loiter/static
> hold · F8 inverted SOF capture · F9 King talk-on gate · F10 King laser/IR designation ·
> F11 designation polish. All six died with the **armor-hunt SCAR scenario**, which the
> survivor-rescue rework (SCAR → "Sandy" rescue escort) retired on 2026-06-27:
> `ScarPlugin.generate_plugin_data()` clears `scar_taskings`, so `scar_414_init.lua` never
> injects and the scenario does not run. The dormant SOF capture economy was then removed
> outright on 2026-07-01.
>
> The rescue rework's own runtime — capture race, POW recovery, Sandy escort — is tracked under
> **G8–G13** and the CSAR rows, NOT here. Design source of truth:
> `docs/dev/design/retlab-csar-notes.md` (which supersedes the earlier SCAR/CSAR notes) and
> features §15.


---

## G. Plugin runtime (Lua, not CI-runnable)

### G19 — TARPS recon birds fly the recon leg (RF-101B / RA-5C / Su-24MR) · §3 · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** The captures carry TARPS flights only on the F-14B(U) (Anatolian Reach, Iron Gate) and the RQ-1A (Inherent Resolve); no RF-101B, RA-5C or Su-24MR was ever fragged, because no Vietnam campaign and no Russia-2020 recon turn was flown. Unchanged.

**Re-scoped 2026-08-21, executing the 2026-08-18 banner.** TARPS reveals nothing any more
(§3's rework: a site is revealed by engaging it), and the §12 recon engine that turned an
overflight into a capture was removed 2026-08-20 along with the `airecon` plugin, its
emitter and the `tars_recon_captures` ledger. Everything this row used to check on the
capture side is gone; the airecon flown evidence and root-cause trace went with it. What is
left is narrow and still real: the two Vietnam recon airframes must be taskable and fly a
sane profile.

**History:** the airframes' TARPS capability gates are unit-tested in
`tests/test_tarps_recon.py`; the flown profile is not.

- **What CI cannot exercise:** whether an RF-101B or RA-5C fragged on TARPS actually flies
  the recon leg — reaches its target area, overflies it, and comes home — rather than
  aborting, orbiting, or being deleted for having no task DCS understands.
- **Setup:** 1968 Yankee Station (RF-101B at Da Nang, RA-5C on the carriers, both tasked
  `primary: TARPS` in `resources/campaigns/1968_Yankee_Station.yaml`). Frag one of each and
  watch the Tacview.
- **Setup (Su-24MR, added 2026-08-23):** red-side, so you cannot frag it — it is the only
  recon airframe on this row you have to *observe*. Russia 2020 fields it; switch on
  **Campaign Doctrine → "Auto-planner adds a recon flight to Strike/DEAD/Armed Recon
  packages"** (off by default since the re-convergence), take a turn where red frags a
  Strike/DEAD package in clear weather, and look for a single Su-24MR trailing it in the
  Tacview. Its own fail signature is spawning **clean** — no Shpil-2, no ETHER, no R-60M —
  which means the `Retribution TARPS` loadout name stopped matching.
- **Pass:** both airframes launch, fly the planned recon route, overfly the target area and
  recover. Nothing is expected to be revealed on the map — that is no longer what recon does.
- **Fail signature:** the flight never leaves the ramp or is dropped from the mission (the
  TARPS task did not resolve for that airframe); it flies to the target but never overflies
  it (route shape); or a kneeboard/briefing line still promises intelligence from the
  sortie (a stale §3 claim — grep for it, do not re-add the capture).

### G20b — Combat SAR snatch-party safety cap + ledger dead-reference cleanup · ⊘ RETIRED

**History:** (2026-08-07)** — the fork's §21 Combat SAR / §15 SCAR were removed and replaced by upstream dcs-retribution#929. Nothing this row describes still exists; there is nothing to fly. Upstream's CSAR needs its own rows. Kept for history.

<details><summary>historical record</summary>

 · §15 · ☐ UNTESTED (fix 2026-07-09, root-caused from a user `dcs.log` hang)

</details>
- **Root cause:** a heavy Red Tide (Germany Cold War) mission **hung** ~13 min in — the log stopped
  mid-flood of MOOSE `UNIT.GetVec3` / `GROUP.GetCoordinate` errors with **no crash dump** (a
  scripting/sim-thread hang, not a CTD; the 20-core/130 GB rig was never the limit). The capture race
  had spawned **80 infantry** (8 parties × 10) across two ejections because a **saved plugin-option
  override** (~40/4) was in force vs the 5/3 default — the dominant dynamic spawn on top of
  MANTIS-over-62-groups + TIC/GLSCO + SplashDamage + airbase harassment + TARS.
- **Fix (CI-tested):** `capturePartySize`/`captureTeams` **hard-clamped at load** (≤ 12 / ≤ 4, warned
  once) so no config can pile enough units on to freeze the sim; the survivor ledger **prunes dead
  teams** out of `entry.party` each cycle + reads positions via `firstAliveCoord` (never
  `GetCoordinate` on a dead lead unit) + **reaps a ground-killed pilot** via the designed-but-unused
  `dead` state — together ending the dead-object poll flood. Behavioral cap test:
  ~~`tests/lua/test_combatsar_capture_cap.py`~~ (runs the real plugin under Lua 5.1).
- **Pass:** on a heavy Red Tide game with the capture race on, several ejections over a long mission do
  **not** bog/hang; `dcs.log` shows a one-time `combatsar: capture party clamped …` line if a saved
  override exceeds the cap, and **no** sustained `GetVec3`/`GetCoordinate` flood after snatch
  teams/survivors die.
- **Fail signature:** the `GetVec3`/`GetCoordinate` flood returns (a poll path still reads a dead
  object), or the mission still hangs with the capture race on (another unbounded spawn/scheduler —
  count dynamic units in `dcs.log`).

### G40 — TARPS recon finds a hidden enemy command post · §3 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from the captures.** TARPS flights flew on tests 17, 18, 24 and Iron Gate, but the reveal happens at debrief in the campaign and none of those turns' next saves were kept. Stays with the LOCAL card's KA-99 measurement.

**History:** built 2026-08-18 alongside the recon rework, to close the hole it opened —
a hidden command post has no marker, so engagement (the only other reveal) cannot reach
it, and the auto-planner was the sole remaining path. The geometry, the radius, the
TARPS-only gate and the §50 exclusion are unit-tested in
`tests/test_recon_reveal_rule.py`; what no test covers is whether 3 NM off the package
target is actually enough reach in a real laydown, and whether the message lands.
- **What CI cannot exercise:** whether a command post is close enough to a plannable
  target for a recon package to reach it on a real map (the whole feature is dead if
  command posts habitually sit further than 3 NM from anything you can frag at), the
  campaign message firing at debrief, and the site drawing correctly once revealed.
- **Setup:** a NEW campaign with `recon_intel_fog` and **Hidden enemy command posts**
  both on (defaults). Confirm no enemy command posts are on the map. Frag a TARPS
  package at an enemy base you believe holds one — pick the target closest to where the
  HQ should be — and fly or fast-forward the turn.
- **Pass:** at debrief a "RECON: enemy command post located" message names the site, and
  the command post appears on the map with exact coordinates and is plannable. Nothing
  else about the reconned area changes: un-engaged sites there keep their composition
  fog.
- **Fail signature:** no message and no reveal after a recon pass that clearly overflew
  the base (the 3 NM radius is too tight for real layouts — the lever is
  `TARPS_POD_RADIUS_NM`, but widening it is a design call, not a tuning one); a command
  post revealed by a *non*-recon sortie (the TARPS-only gate broke); an ordinary site
  revealed by the recon pass (scout-to-reveal is back — this is the serious one); a §50
  convoy-ambush team appearing on the map (the `map_hidden` exclusion broke); **a command
  post that turns up already destroyed, or revealed without a recon pass** — blue's auto
  raids (§63) and carrier strike (§44) are fog-gated as of 2026-08-18, so either the gate
  regressed or the auto-planner reached it (see the scoping note; the planner path is a
  known, unfixed leak).

### B126 — An AI DEAD gets its shot: the EWR is fragged first, and the site it covered is live the turn after · doctrine row 8 · ☐ UNTESTED

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **not the tier this row tests.** The one turn-1 DEAD, `PORCUPINE DEAD` (4× F-16C), was fragged at the S-350 covering the Herat strikes — the reactive tier. It fired: AGM-65Gs killed the 96L6 and both 50N6s at t=2716–2761, 51–96 s before its TOT, for two of its four jets (one to the S-350, one to TURKEY's Tor). No opportunistic DEAD on turn 1 or turn 2 (turn 2: DEAD at SKINK and PORCUPINE again), so the EWR ordering was not exercised.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`; corrected 2026-09-22 from full-resolution tracks) — **not the EWR ordering, but the same doctrine seam.** The SA-11 `0126 | MAVERICK (SAM)` was live when `Kharab Ishk Armed Recon` (TOT 05:46Z) transited, and killed six aircraft of that package. What eventually killed it was unplanned against it: `FERRET SEAD Escort` (2× F/A-18C, escorting a BAI) fired four AGM-88 at it from 70–75 km at t=2419–2437, 21 s after the site opened fire; all four fell 2.2–2.4 km short at t=2563–2572. The same flight's GBU-38s then killed the four TELARs and two ZU-23s at t=2710–2715. `RAVEN SEAD Escort` GBU-38s killed the Strelas and a tanker truck at t=3272–3276. The site's own DEAD, `MAVERICK DEAD` (TOT 06:07Z), arrived to a dead site; its JSOW submunitions most likely took the search radar at t=3849 (no single weapon within 150 m). The fragged suppression for that site came 21 min after the package that had to cross it.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged: no turn in the captures follows an EWR kill.** Test 32's WEKA shot at LEOPARD is the closest thing seen (a lit site, lit because the SEAD escort ahead of it drew fire), which is the row's second fail signature working as intended, not the ordering. Needs the turn after an EWR dies.

**2026-09-15, headless check on the DM's CSAR save (Persian Gulf, turn 5) — the ordering is inert on this campaign.** Blue re-planned in memory on the merged code produced the same three DEAD packages as the save (KIWI, SNAIL, FRINGEHEAD), all from the reactive tier: 24 red SAMs sit in `threatening_air_defenses`, since a site counts as threatening once its ring touches any planned route, and that tier spends every DEAD squadron before the detector tier is reached. The detector tier would not have helped either: the eight red EWRs run 162–216 nm, so each red site is covered by two to six of them plus one to four big SAMs acting as EW (KIWI: five EWRs and three SAMs), and Skynet needs every parent gone before a site goes autonomous. Killing EWRs stacks, as the DM said. The only cuttable node on this map is the command-centre pair (SLOTH, TURTLE): `isCommandCenterUsable` is false once both are dead, and then every red site goes autonomous and live (the vanilla default; only 21 CurrentHill unit yamls set `autonomous_behaviour`). No planner task prefers command centres today. Left as is, on the DM's call; nothing further built.

**History:** built 2026-09-15 off test 32, minimal shape of doctrine-mining row 8. `DegradeIads`
offers the detector tier before the opportunistic LORAD/MERAD tier; the reactive tier (a SAM
threatening a planned strike) is unchanged. Skynet holds a netted site dark until its target is
in the kill zone, and DCS AI fires a HARM only at an emitter, so on test 32 a DEAD four-ship at a
dark SA-11 died without a shot while the same fit at a lit SA-11 killed two launchers. Once the
EWR covering a site is dead, Skynet runs the site autonomous and live from T0.

- **What CI cannot exercise:** that a site whose covering EWR died last turn is actually live at
  mission start, and that the AI DEAD then fires at it. The ordering is pinned by
  `tests/test_dead_net_order.py`; the runtime half is Skynet's.
- **Setup:** any campaign with a red EWR covering a radar SAM the planner wants (Red Tide's rear
  hubs, or this Persian Gulf save). Generate a turn with an AI DEAD or two and read the ATO.
- **Pass:** the ATO's opportunistic DEAD targets name the EWR before the SAM it covers. On the
  turn after the EWR dies, the SAM it covered is radiating from mission start (RWR nail on
  ingress, no `SKYNET` go-live wait) and the AI DEAD at it fires.
- **Fail signatures:**
  1. **The EWR is fragged but the SAM still sits dark next turn** — another parent still covers
     it (a SAM-as-EWR, an AWACS), or the site still has C2, comms and power; that is the full
     rule's territory, not a defect here.
  2. **A DEAD at a SAM that threatens a planned strike still dies without a shot** — expected;
     the reactive tier was left alone on purpose.

### G25 — Armed Recon package: recon drone + SEAD Viper escort + 4-ship sweep · §3 · ◐ PARTIAL

**2026-10-12 — the recon drone half was REMOVED on the DM's call.** The planner no longer adds a TARPS flight to any package (`auto_add_tarps_recon` is deleted), so an auto-planned Armed Recon package is the sweep and its escorts. A hand-fragged TARPS flight still flies.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the drone and the SEAD escort are seen; the fixed 4-ship is not what the planner builds now.** Inherent Resolve test 17: `Tikrit Armed Recon` and `Bayji Armed Recon` are each a Mirage 2000C pair plus an RQ-1A TARPS singleton, and the auto-planned Armed Recon flights on Anatolian Reach, Iron Gate (twice) and Desert Trident are pairs too, each with a SEAD Escort where a radar SAM sits on the route. The only four-ship Armed Recon flights in any capture are the DM's hand-built AUROCHS package on test 30. The 4-ship primary in this row's text predates the 2026-08-09 planner re-convergence and reads as stale; re-check the proposer before treating the pair as a fail.

**History:** drone-in-package + TARPS-vs-CP + the convoy hunt VERIFIED in a 2026-07-06 flown session; the auto-planner 4-ship + SEAD-escort composition and the post-standoff AI hunt still owed
- **Flown evidence (2026-07-06, Inherent Resolve turn 1, session `jovial-gates-574c9c`, Tacview + dcs.log):**
  the player's "Shirqat Armed Recon" package (player F/A-18C 2-ship + MQ-9 Reaper) worked end-to-end — the
  TARPS-vs-CP drone flew, overflew the target CP at 0.4 km, and banked a 22-unit `airecon` capture (G19); the
  §50 red convoy (10 gun trucks) departed the FOB down the corridor and the flight found and destroyed all 10
  (Mavericks + a gun pass); no generation errors. NOT yet shown: the auto-planner's fixed 4-ship primary + the
  threat-gated 2-ship SEAD Viper escort composition in a planned (non-player-built) package.
- **Same session's finding → fix to re-verify:** the ARMED RECON fly-over waypoint sat **dead-centre on the
  Shirqat FOB** (SA-13/ZU-23 garrison) — the player had to improvise a ~4 km offset and standoff Mavericks.
  Fixed 2026-07-06: `Builder._stand_off_search_point` pulls the point back along the ingress bearing (target's
  longest threat ring + 2 NM, floor 5 NM, capped at the engage-zone radius / ingress distance); the hunt zone
  re-centres on the moved point. **Next fly:** confirm the steerpoint sits off the FOB and the AI flight still
  finds/engages the corridor traffic from the offset point.
- **What it is:** each auto-planned Armed Recon package now composes as **1 recon drone + 2 SEAD Vipers + 4 armed recon** on a UAV-fielding faction (OIR). The primary is a fixed 4-ship; the SEAD escort (`propose_common_escorts`, 2-ship, threat-gated) resolves to the F-16CM; and the auto-recon hook (`auto_add_tarps_recon`, default ON) frags one TARPS flight — which on OIR is a Predator/Reaper, since the drones are the faction's TARPS birds. The drone is optional (drops if none free, never scrubs the package) and the SEAD is pruned when no radar-SAM threat sits on the route.
- **Setup:** NEW "Iraq - Operation Inherent Resolve (COIN)" (has the drones + the SA-6/8 crust + Viper SEAD). Let the auto-planner build a turn; open an Armed Recon package in the ATO.
- **Pass:** an Armed Recon package shows a 4-ship recon primary + a 1-ship drone (Predator/Reaper) recon flight; where a radar SAM threatens the route, 2 F-16CM SEAD ride too; the drone overflies the swept corridor (TARPS-against-a-CP flies, no `InvalidObjectiveLocation`) and its overflight confirms BDA on the area next turn; a package with no TARPS bird free still plans (drone just omitted).
- **Fail signature:** the drone never appears (`auto_add_tarps_recon` off, or no TARPS-capable squadron — the drones need their `TARPS: 700` from the #491 unit data); the package errors on generation with `InvalidObjectiveLocation` (the TARPS-vs-CP widening didn't take); armed recon plans a 2/3-ship instead of 4; the drone flies TARPS but never reaches the corridor (range/TOT — the drone cruise is slow, check the +2 min offset holds it under the escort window).

---

### G33 — Survivor ADF beacon: the pinned 260 kHz drives a real needle · CSAR (upstream #929 + RetLab pin) · ◐ PARTIAL

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — 18 `Added Radio Beacon 260000 Hertz` lines, red and blue. No human was down to tune an ADF, so the needle is still owed.

**2026-09-16, test 35** (Syria — Long Road to H3 turn 1, 78 min, no player, `Tacview-20260916-215945`, DCS 2.9.29.27468) — three blue beacons, three on 260 kHz, all in-mission ejections (no survivor was pre-placed). Six of six across tests 34 and 35 now.

**2026-09-16, test 34** (Caucasus — 1968 Yankee Station turn 1 on the halved laydown, 62 min, no player, `Tacview-20260916-204511`, DCS 2.9.29.27468) — **the log half is fully proven now: nine blue beacons, nine on 260 kHz, in-mission ejections included** (LORIKEET BAI's two Skyhawk crews at t≈31 and 34 min among them), on a build carrying the in-mission pin. The needle in a cockpit is the one thing left.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the log half is proven for briefed survivors and exposes a gap for the rest; the needle is still unflown.** Every survivor Retribution places at mission start keys 260 kHz: tests 2, 11, 16 and 32 carry `Added Radio Beacon 260000 Hertz` for the uuid-named groups (ten of them on test 32). But a pilot who ejects **during** the mission is registered by MOOSE's own `CSAR:_AddCsar`, which the pin does not reach, so he keys a random channel from the stock pool: test 33's two blue survivors got 620 and 820 kHz, test 24's eighteen blue beacons (including the DM's own `Flash` at 300 kHz) never touched 260, and the red side is random everywhere. The kneeboard's 260 is therefore right for the rescue it briefs and wrong for a same-mission pickup, which the MAYDAY call still announces. **Fixed the same day:** the plugin now overrides `_GenerateADFFrequency` on each Ops.CSAR instance to return the pinned channel, so MOOSE's own `_AddCsar` path keys 260 kHz too (`tests/test_plugin_resource_files.py` guards the override). Re-check on the next mission with an in-mission ejection: every `Added Radio Beacon` line on the blue side should read 260000. The row still needs an ADF set in a cockpit.

**History:** adopted 2026-08-07. `tests/missiongenerator/test_csarbeacon.py` pins 260 kHz to MOOSE's 10 kHz grid, inside its 200–999 kHz band, clear of every navaid `UTILS.GenerateVHFrequencies` skips, and receivable by all three ADF sets; `tests/test_plugin_resource_files.py` proves the tone ships. Whether DCS produces a carrier a needle can home is cockpit-only
- **What it is:** MOOSE `Ops.CSAR` beacons each survivor with a looped `trigger.action.radioTransmission` in the NDB band. Stock MOOSE draws a **random** channel per survivor, which cannot be briefed because the kneeboard renders before the mission runs — so the fork pins one channel for the whole mission (`game/missiongenerator/csarbeacon.py` → `luagenerator` emits `beaconHz` → `OpsCSAR.lua` substitutes it for the random draw) and the kneeboard SAR line carries it.
- **What CI cannot exercise:** whether a real ADF needle in a real cockpit swings to the survivor. The fork asserted this from the DCS C-130J manual and the MOOSE source, never from a flight. **This was already broken once:** MOOSE hardcodes `radioSound = "beacon.ogg"` and no such file exists in this repo, so before 2026-08-07 the beacon keyed a filename the mission did not contain. The plugin now ships `csar-beacon.wav` and overrides `radioSound`; this row confirms that fix actually reaches the cockpit.
- **Setup:** any campaign, `csar_enabled` ON, `csar_ejection_chance` 100. Eject from an ordinary ATO jet over land, end the mission, pass the turn (~15 min). Next mission, slot a **UH-1H** (ARN-83) or **Mi-8MT** (ARK-9), read the beacon channel off the kneeboard SAR line, set the ADF to it in ADF/COMP mode with the audio up, and fly toward the survivor from ~20 NM. ~25 min total.
- **Pass:** the needle swings to the survivor's bearing from at least 15 NM and tracks the cut as you turn; the swept beacon tone is audible on ADF audio; `dcs.log` carries `Added Radio Beacon 260000 Hertz`; the kneeboard number and the tuned number are the same.
- **Fail signature:** **the `Added Radio Beacon 260000 Hertz` line is present but the needle is dead and there is no tone** — the audio file is not reaching `l10n/DEFAULT/`; check the generated .miz actually contains `csar-beacon.wav` and that `otherResourceFiles` survived in `resources/plugins/opscsar/plugin.json`. **No `Added Radio Beacon` line at all** — the pin never arrived; check `beaconHz` in the emitted `dcsRetribution.CSAR` table, since `OpsCSAR.lua`'s `tonumber(cfg.beaconHz) or 0` silently reverts to MOOSE's random pool. **A channel that is not 260** — the fallback fired, so every survivor is on a different random channel and the kneeboard is lying. **No `=== CSAR starting` banner** — the plugin never loaded.

### G36 — Player rescue end to end: F10 menu, the hoist at the briefed height, delivery, roster · CSAR · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no human has flown a rescue helicopter in any capture** (players flew Vipers, Hornets and the King seat). Unchanged.

**History:** adopted 2026-08-07; **this is the only path a human actually flies**, and it is gated by MOOSE's own winch logic rather than the fork's script. `tests/missiongenerator/test_csar_hover_altitude.py` guards the altitude contract
- **What CI cannot exercise:** the whole player experience — the F10 menu appearing on the right group, "List Active CSAR" (this adoption's LARS) reading correctly, the winch actually starting, the survivor riding home, and the rescue crediting when you land.
- **Setup:** with a survivor down, slot a CSAR-capable helo yourself. Read the SAR line, tune the beacon, fly to the survivor, **hover at the briefed altitude the pickup waypoint gives you**, hold it, then fly home and land at a friendly field. ~50 min.
- **Pass:** the F10 "CSAR" menu is present with List Active CSAR / Check Onboard / Request Signal Flare / Request Smoke / Request IR Strobe; the list names the live survivor with a plausible bearing and range; hovering at the briefed height starts the winch within ~10 s and the survivor boards; Check Onboard confirms him; landing at a friendly field credits the rescue and the roster shows him Recovering next turn.
- **Fail signature:** **you hover exactly as briefed and the winch never starts.** This was a real shipped defect — the waypoint briefed 100 ft against MOOSE's 20 m ceiling, so a crew flying the mission correctly could not hoist, with no cockpit message at all. It is fixed (50 ft), but the failure mode is silent, so if the winch does not start, **descend and see if it starts lower** before concluding anything else: that immediately distinguishes an altitude-contract regression from a genuine plugin fault. Other shapes: no F10 menu at all (the client group never registered — MOOSE registers on the group's first unit, so check you are in the lead slot); the survivor boards but landing credits nothing (the delivery detection missed the field).

## H. Kneeboards

---

### H14 — The kneeboard SAR line is accurate, and the rescue crew gets a usable card · CSAR · ◐ PARTIAL (2026-09-21, test 37; was ☐ UNTESTED)

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the striker line again.** The F-15E's page 1 carries the four-line `SAR 260 kHz ADF` block, no overflow. Turn 2's ATO frags two UH-60L CSAR flights (`Downed pilot: Curtis Thomas`, `Downed pilot: Andrew Clay`), so the rescue crew's card is reachable on the next turn.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **the striker-card half.** Page 1 carries `SAR 260 kHz ADF — If down: your beacon keys automatically — squawk 7700, voice on GUARD …`, four lines, no overflow, and every survivor this mission keyed that channel: 28 `Added Radio Beacon 260000 Hertz` lines in `dcs.log`. No CSAR flight was fragged, so the crew's card is still owed.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** Test 33's Viper kneeboard (eight pages, read off the miz) carries no SAR line because no survivor was on the map at generation; no capture had a CSAR package with a kneeboard to read. Unchanged.

**History:** the beacon number is unit-tested and the SAR line renders; the page fit and the rescue crew's own card are visual
- **What CI cannot exercise:** whether the SAR line fits its page on a busy theatre, whether the briefed beacon channel matches what the survivor actually transmits, and what the **CSAR crew's own** kneeboard says — every other kneeboard row is about what the *other* flights are told.
- **Setup:** generate a mission on a busy campaign with a live survivor and a CSAR package. Read the SAR line on an ordinary striker's card, then read the CSAR flight's own card. ~10 min, no flying.
- **Pass:** the SAR line fits without overflow and names a beacon channel that matches the one the survivor keys; the CSAR crew's card carries the pickup point and the beacon.
- **Fail signature:** the SAR line overflows or truncates on a busy page; the briefed channel does not match the transmitted one (the pin fell back to MOOSE's random draw — see G33); the CSAR crew's card carries no beacon at all. **Also worth knowing:** the SAR line is printed on **every** flight's card including dynamic-slot aircraft, whose pilots can never go MIA and can never have a beacon — so a dynamic-slot pilot is briefed a rescue that structurally cannot come. That is a real mismatch, not a rendering bug, and if it bothers the squadron the fix is in the card, not the plugin.

### H15 — Offline recon pages: imagery under the symbology, or none at all · §22 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the offline path was never taken.** Every recon page in the captures is the online Esri render (test 33's DEPARTURE, RECON OVERVIEW and RECON DETAIL pages all carry the Esri attribution and the imagery sits under the markers correctly), so the raster fallback this row exists for has not been exercised. Needs a generation with the network blocked.

**Raised in value 2026-08-26.** These pages are the whole of recon candidate C, and the TARPS bird now gets them too (C.1). `generate_target_recon_kneeboard` cannot come off default-off until this row and H16 are flown, so this is the gate on the feature, not a cosmetic check.

**History:** added 2026-08-22 with the `gif_georef` fix. The old path georeferenced the shipped theater raster by `terrain.bounds` and clamped the crop to the image, so an extent the raster could not cover was stretched to fill the page — every Syria crop collapsed to a one-pixel-tall strip, and a Batumi page landed 116 km east. The crop now refuses instead of clamping and drops to the landmap renderer.
- **What CI cannot exercise:** whether the *real* raster crop lines up with the drawn symbology on a rendered page. The tests use synthetic rasters to pin the world-to-pixel mapping; they cannot tell you the imagery looks right under the markers.
- **Setup:** `generate_target_recon_kneeboard` ON, **network down or blocked** so the Esri tile path fails and the OFFLINE banner appears. Generate on Syria and on Caucasus, then open the DEPARTURE / RECON OVERVIEW / RECON DETAIL pages. ~15 min, no flying. Worth doing on Syria specifically with a package fragged at **Tabqa** (in frame) and one at **King Abdullah II** (off frame).
- **Pass:** the in-frame page shows terrain imagery whose coastline and features sit under the markers, at the requested area rather than a smear. The off-frame page shows the plain tan landmap with the grid — no imagery — and the markers are still correctly placed on it. Both carry the red OFFLINE banner.
- **Fail signature:** imagery that is a vertical smear of one pixel row (the raster was georeferenced by `terrain.bounds` again); markers floating tens of km off the coastline they should follow (the coverage rect drifted — re-run `test_gif_georef.py`); a Cyprus page showing open water under an airbase (the `unrendered` hole stopped being consulted); a blank or crashed page where the landmap fallback should have drawn (the refusal path returned None all the way up instead of falling through).

### H16 — Package Targets Map: terrain behind the packages, and it lines up · §22 · ☐ UNTESTED

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **not reachable on this map.** The page drew the flat fill with a grid and every package placed (PIG, BULLSHARK, HORNBILL, PORCUPINE, MONKFISH, QUAGGA, FALCON, the front, FOB Delaram II). No Afghanistan raster ships in `resources/`, so the fill is the correct behaviour.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the page renders on a real turn; the terrain backdrop is not there.** Test 33's Package Targets Map (page 7 of the Viper deck) shows every package and field on a flat tan landmap with the coastline and grid, correctly placed (Akrotiri, CVN-62, Ramat David, MAVERICK, the front), with no imagery behind it. Syria is inside the shipped raster's coverage per the row's own history, so either the padded extent fell outside `COVERAGE` or the raster path was not taken; the row's fail signature ("a flat tan fill where the raster should have reached") is what is on the page. Not adjudicated further; check the extent before calling it.

**History:** added 2026-08-22. The page drew a flat tan fill with a coastline; it now draws the shipped theater raster where `gif_georef` says it reaches. The swap had been tried and reverted in `7cc256f5c` (#945) because the georeference was broken — that is fixed, so it is made. Rendered on real Syria and Caucasus coordinates during development and it looked right; this row is the check on a real generated turn.
- **What CI cannot exercise:** whether the imagery reads as a useful orientation map at whatever extent a real turn's packages happen to produce, and whether the labels stay legible over photographic terrain rather than a flat fill. Both are judgements about a picture.
- **Setup:** `generate_all_packages_kneeboard` ON (it defaults OFF — it adds pages). Generate a turn on Syria and one on Caucasus, open the Package Targets Map. **No network needed and none should be used.** ~10 min, no flying. Try a dark-kneeboard turn too.
- **Pass:** the backdrop is terrain, and coastal airfields sit **on** the imaged shoreline rather than near it. The packages may sit off-centre on the page — that is the slide buying imagery with margin it did not need, and every package is still drawn — Batumi, Kobuleti, Gudauta and Sochi-Adler on Caucasus are the quick read. Orange target dots and their white-plated names stay legible over the imagery. On a dark kneeboard the terrain is dimmed and the labels still read.
- **Fail signature:** markers consistently offset from the coastline (georeference drift — H15's fail signatures apply); a flat tan fill where the raster should have reached (check the extent against `COVERAGE` — remember `aspect_correct` runs first, so the padded extent must fit, not just the packages); labels washing out over busy terrain; any network access during generation (the backdrop is offline by construction and a test pins it — if this happens, something re-wired it to the tile path). Any package missing from the page entirely (the slide is meant to refuse rather than crop — that would be a real bug). A theater-wide spread showing the flat fill is **correct behaviour**, not a failure.


## I. Mission generation

### I2 — Civilian background air traffic (region fleets + airways) · ◐ PARTIAL (2026-09-23, test 40; was ☑ VERIFIED)

**2026-09-23, test 40** (Afghanistan — Graveyard of Empires turn 2, no player, `Desktop\New test\40`) — **the departure stagger never worked, and two IL-76s have crashed at the start.** Every ground-started civil flight with a delay (seven, 10–6,129 s) was on its runway at t=0 and airborne by t=81 s. DCS rewrites each group's `start_time` from its first waypoint's ETA when it loads a mission (`MissionEditor/modules/me_mission.lua`, `check_mission`); the spawner wrote the delay to `start_time` only. Test 37's `CEDAR AIR 673` (delay 1,605 s) left at once and crashed at 66 s. Here `ARIANA 131`, an IL-76 out of Bamyan (~2,590 m), climbed ~10 m and hit terrain at 88 s. **The delay is fixed the same day** (row B146). The high-field IL-76 is not.

**2026-08-17 — CLOSED FROM TACVIEW, no flight required.** The DM asked whether the re-look could
be settled from a recording instead of the cockpit. It can, across all six recordings on disk —
**52 fixed-wing civil tracks**:
- **They reach their assigned level.** Peak altitude is FL200, FL259 or FL308 — exactly the three
  authored cruise levels, nothing between them and nothing lower. 31 of 52 spend ≥40 % of the
  track at or above FL180; several are level for 100 % of it.
- **The climb case works**, so the missing waypoint-between-takeoff-and-landing fix took: tracks
  starting at FL0–1 reach FL200–259.
- **Nothing falls.** 40 of 52 have a descent moment steeper than 6,000 fpm, which reads alarming
  until you check the speed at that moment: every one is **295–406 kt ground speed**, a powered
  arrival. The actual 2026-08-08 defect — a spawn below stall — is under 100 kt and decaying.
  Every track survives to the end of its recording and there are **no civil wrecks** in any of
  the six.
- **Thread, not a defect:** `ARKTIKA 134` (An-30M) shows 78 kt ground speed in one 10-second
  window while level at FL200, against 222–303 kt for every other An-26/An-30 sample. One window
  proves nothing; if a slow civil contact ever appears on the F10 map, start here.
- **Density is still a taste call and still does not need a flight.** The count is **16 civil
  aircraft per mission** (12 fixed-wing + 4 rotary) on Caucasus. The 2026-08-05 rebuild left this
  open deliberately; the number is now available to judge it without flying.

**History:** re-look owed on the 2026-08-08 speed fix — see the bullet at the end of this row; was ☑ VERIFIED 2026-08-06, WATCH item 2, DM verdict "looks good" — the first eyes on the rebuild: traffic reads region-plausible and civil, no fail signature. Note the rebuild's own honest caveat still stands — the third complaint, "too little / it disappears", was deliberately NOT separately fixed, so if density still feels thin that is a *separate* judgement to make on this build, not a regression of this row) (was ☐ UNTESTED, **REBUILT 2026-08-05** `units-runway-generation-bf755e`. Opened as "I think RAT is the real answer" and closed the other way: RAT was never cut on taste — `civiliantraffic.py`'s header records that it CRASHED the sim (`woCharacterHuman` / GermanyCW-FARP, from RAT resolving an unresolvable heliport id, which is why the rotary layer had to be disabled outright; respawn churn was a second crash path) — and it fixes neither real issue. Pressed on the symptom the DM named those as **civil identity** and **airways vs milk runs**; RAT addresses neither, and its one differentiator (ATC / living airfield) was explicitly not among the complaints. **(1) Civil identity is now a data table** (`game/missiongenerator/civilianfleet.py`): fleet, operator names and cruise levels per region. The old roster was applied GLOBALLY, so Antonovs and Hips flew over Nevada and the Marianas — the Soviet set was never wrong, it was wrong *everywhere else*. **Found in passing and worse: the WWII maps had modern civil traffic on them** — Normandy and The Channel now field nothing at all, which is the honest answer for a 1944 combat theatre. Groups are named `AEROFLOT 412`, not `CIV_An-26B_3`, since that name is what the F10 map shows. **(2) Airways, not milk runs**: a fixed-wing route is one long transit at a real flight level (FL200–FL310), not five short rear-area legs; the meander existed only to keep aircraft airborne without a respawn loop. Helicopters deliberately stay on short local hops — a helo does not fly an airway. The endpoint pool widened (neutral fields preferred, any field as fallback) because for an overflight the endpoints are only direction anchors. **PASS:** fly any mission and confirm the traffic (a) is region-plausible — no Antonovs over Nevada, nothing at all over Normandy — (b) reads as civil on the F10 map by operator name, and (c) crosses the map high and straight rather than pottering at low level between rear fields. **FAIL signatures:** an empty sky on a mapped theatre (check the `Civilian traffic: N flights (N airway, N rotary) from an N-field pool` log line); traffic at the old flat ~16,000 ft; a civil flight inside the front keep-out; or any civil aircraft appearing over a WWII map. **The third complaint — "too little / it disappears" — was NOT separately fixed and that is deliberate**: low traffic pottering between rear fields is invisible to a player at altitude, so the felt sparsity is expected to be substantially a visibility problem that high straight transits fix on their own. Judge density on this build before adding a concurrency scheduler. Tests `tests/test_civilian_traffic.py` (22), incl. a guard that every `REGIONS` key is a real `Terrain.name` — the campaign yamls carry DISPLAY names ("Persian Gulf", "Sinai", "The Channel") while the table is keyed on `Terrain.name` ("PersianGulf", "SinaiMap", "TheChannel"), and a typo'd key fails SILENTLY into the Soviet fallback. All 13 shipped theatres verified to resolve MAPPED) (was ✗ REGRESSED / ☑ VERIFIED 2026-06-26

- **Speed fix 2026-08-08 — needs a re-look, and it explains the density complaint.** Reported as
  "our civilian traffic is spawning stalling", diagnosed as a unit error at the pydcs boundary:
  every pydcs speed argument (`flight_group_inflight`, `FlyingGroup.add_waypoint`,
  `ShipGroup.add_waypoint`) is **km/h** and divides by 3.6 internally, while this module plans in
  m/s and passed the raw number — so a third of every intended speed was written. The air-start
  path is the one that bites: DCS takes the spawn velocity from the **unit** record, so the
  transits materialised at cruise altitude below stall (An-26 65 kt at FL200, IL-76 108 kt at
  FL310, Yak-40 81 kt at FL260), dropped the nose and lost thousands of feet, and the slowest did
  not recover. Structurally identical to the QRA scramble's ~0 kt Moose air-spawn
  (`intercept-config.lua`, `SCRAMBLE_SPEED_KT`) — same failure, different cause. Also hit the
  rotary legs (27 kt) and the ambient boats (0.8 kt vs a 3 kt hull speed). Fixed by converting
  with `mps(...).kph` at all three call sites; `CRUISE_PROFILE` stays in m/s.
  **This retro-qualifies the 08-06 verdict**: ~70% of fixed-wing traffic air-starts, so most of
  the sky was falling down while the ground-started remainder carried the "looks good" read — and
  it is a live candidate for the "too little / it disappears" complaint that was explicitly left
  unfixed, since a stalled transit really does disappear. **PASS:** air-started transits hold
  their flight level and cruise speed from mission start (Tacview, or F10-map track a
  `AEROFLOT`/`INTERFLUG`-style contact for a few minutes); boats make way at a walking pace rather
  than sitting still. **FAIL:** a civil contact descending steeply from its spawn altitude, or
  civil wrecks on the map with no one having shot at them. **Judge density again on this build
  before adding a concurrency scheduler** — the earlier "judge density on this build" call was
  made against traffic that was falling out of the sky. Regression pins:
  `tests/test_civilian_traffic.py` builds a real pydcs mission and asserts the written unit /
  waypoint speeds, plus a floor guard on the air-start-eligible `CRUISE_PROFILE` rows (all three
  speed pins verified failing without the fix).
- **Flight-level fix 2026-08-08 — same change, found while fixing the stall.** "Airways, not
  milk runs" removed the intermediate legs and nothing replaced them: a two-field route's
  `chain[1:-1]` is empty, so a **ground-started** transit was written as takeoff → `land_at`
  with **no waypoint carrying the cruise altitude at all** (headless: the group came out with
  exactly 2 points). DCS flies the shallow takeoff-to-touchdown V that implies, so the ~30% of
  fixed-wing traffic that departs from a field never climbed to the per-region flight level the
  rebuild exists to assign — and the air-start half had nothing holding it level either, only
  the spawn point and the landing. Two-field routes now get synthesised top-of-climb /
  top-of-descent waypoints (`CRUISE_ENTRY_FRAC` 0.25 / `CRUISE_EXIT_FRAC` 0.9); air starts are
  already at cruise and take only the descent point. **The rotary layer is deliberately
  untouched** — it routes through real intermediate fields, and straightening those would
  remove the meander that makes local rotary work read as local. **PASS:** a civil contact that
  departs a field climbs out to FL200–FL310, holds it across the map, and descends near its
  destination. **FAIL:** a departing civilian that levels off low and stays there, or one that
  never levels at all. Note the entry fraction sets where DCS *wants* the aircraft level, not
  the gradient it can manage — an An-26 needs ~90 km to make FL200 and will keep climbing
  toward the next waypoint, which is at the same altitude, so a late level-off is expected and
  is not a fail. Pins: `test_a_ground_started_transit_climbs_to_its_flight_level` and
  `test_an_air_started_transit_holds_its_level_before_descending` (both verified failing
  without the fix), plus a guard that `AIR_START_FRAC_RANGE` stays below `CRUISE_EXIT_FRAC` so
  an air start is never told to fly backwards up its own airway.

### H10 — Shared-airframe kneeboard index · §27 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** No capture has two client flights of one airframe (every test with players had exactly one client flight), so the index page never had a reason to exist. Unchanged.

**History:** standalone page again since the 2026-07-13 back-to-upstream rework; condition not met in the 2026-06-28 pass
- **Not exercised (2026-06-28, audience pass — user confirmed the condition wasn't set up):** the mission did **not** have 2+ client flights of the same airframe, so the index had nothing to render — no observation either way, **not** a fail.
- **Surface history:** briefly a section on the §30 cover page; the 2026-07-13 back-to-upstream
  rework retired the cover and the index is a **standalone conditional page** again
  (`KneeboardIndexPage`, only when 2+ client flights share the airframe). Page-math + lone-flight
  no-index regression in `tests/missiongenerator/test_kneeboard_index.py`.
- **Headless adjudication (2026-06-26, re-valid 2026-07-13):** the tests cover the
  start-page math (index is page 1, blocks start at 2 and advance by block size), callsign grouping +
  sort, and the index page render. **Residual (in-sim only):** the index actually appears in-cockpit
  and its page numbers line up with the stacked deck DCS builds.
- **Setup:** Frag **2+ client flights of the same airframe** (e.g. two F/A-18 flights) in a mission;
  generate and open the kneeboard. Also frag a single flight of another type as the control.
- **Pass:** page 1 of the shared airframe is an index listing each flight's callsign / task / start
  page; flipping to a listed page lands on that flight's deck; the single-flight type has **no** index.
- **Fail signature:** no index when 2+ share a type; wrong start pages; an index wrongly added for a
  lone flight; flights out of the listed order.

---

## K. Settings UI

---

## L. Vietnam Ops

### L5 — New-Game "Vietnam" card · Vietnam mode P2 shell · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side; no capture can show the New Game wizard.** Unchanged.

**History:** verified 2026-06-28, but **re-plumbed 2026-07-26** onto upstream #908's filter framework — the era filter runs through a different code path now and needs a re-check
- **⚠️ Re-verify (2026-07-26 sync):** upstream #908 added version/map/performance filters + sort to the
  same Theater page, so the fork **dropped its bespoke era plumbing and adopted theirs**. The era is
  now a criterion inside `QCampaignList._filter_campaign` (`current_era_filter`, set via
  `set_filters(version, map, era)`), `_set_mode` repopulates through the shared `on_filter_changed()`,
  and the `selectedCampaign` wizard field is gone (`accept()` reads
  `campaignList.selected_campaign`). **Re-check on the app:** the Vietnam card still lists only the
  `era: vietnam` campaigns; picking one and pressing through still starts *that* campaign (the field
  removal is the risk — a mis-wire would silently start `campaigns[0]`); the era filter **composes**
  with the new Version/Map/Sort controls instead of one clobbering the other; and going back to the
  Introduction page and switching to "included" restores the full list. `qt_ui` is not in the CI mypy
  path and the campaign-list build needs the DCS install dir, so none of this is headless-checkable.
- **In-game (2026-06-28, audience pass — user: "works but needs more added"):** the New-Game **Vietnam** card works as specified — the radio appears on the Introduction page and the Theater page filters to the Vietnam campaigns. The "needs more added" is a **content** follow-up (more Vietnam campaigns/options surfaced on the card), tracked separately — not a fail of the P2 shell.
- **Headless adjudication:** the filter predicate `Campaign.matches_era` is unit-tested
  (`tests/test_vietnam_content.py::test_matches_era_drives_the_vietnam_card_filter`) and the Qt modules import
  clean. The radio/field render + the `vietnamMode`→list-filter path can't be exercised headless (the
  campaign-list item build needs the DCS install dir).
- **Setup:** Open **New Game**. On the Introduction page, "Campaign type" now has a third option, **Vietnam**.
- **Pass:** Selecting **Vietnam** → the next (Theater) page is titled "Vietnam" and lists **only** the
  `era: vietnam` campaigns (1968 Yankee Station, Velvet Thunder, Red Flag 81-2); selecting one still pre-loads its settings +
  recommended factions. Going **back** and choosing "Play an included campaign" restores the full list.
  The "Show incompatible campaigns" toggle keeps the Vietnam filter applied.
- **Fail signature:** no Vietnam radio; Vietnam shows all campaigns (filter not applied) or an empty list;
  switching back to "included" stays filtered; the "show incompatible" toggle drops the era filter; a crash
  arriving on the Theater page.

### L6 — Convoy interdiction (Steel Tiger) · §35 · ◐ PARTIAL

**2026-09-16, headless read of the DM's Yankee Station turn-1 save (`Vietnam tes.retribution`, 60-min mission)** — **the trail convoys are planned.** Red's pending transfers are two 15-vehicle columns on distinct roads (FOB Tchepone → Gudauta: ZSU-57-2, T-55A, PT-76, ZU-23 trucks; FOB Ky Son → Sukhumi: ASU-85, PT-76, ZU-23 trucks, T-55A), which is `MAX_CONVOY_UNITS` 10 × the turn-1 `trail_surge` 1.5 under `BASE_MAX_CONVOYS` 2. The planner did not frag Armed Recon onto either corridor by name (its 13 Armed Recon flights sit on FOBs and airfields); the runtime and debrief legs are still the flown part.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no Vietnam campaign in the 33 captures.** The July flown evidence stands as written. Unchanged.

**History:** 2026-07-02 flown Trail 2 session `wonderful-chatterjee`: the reworked real-convoy runtime leg PASSED — `Convoy 001` (2× PT-76 + Grad-URAL, real force-model units) drove the trail road, the player Armed Recon Phantoms found it and killed all 3 with Mk-82 Snakeyes (Tacview removals t=3195/3609/3610); still owed = the debrief leg — next-turn processing must record the loss as `enemy_convoy` so the units never arrive. ⚠ blocked on the REAL server-side `state.json` — the dedicated host wrote it to its **TEMP fallback**: `dcs.log` says "The state.json file will be created in TEMP : (C:\Users\admin.dcs\AppData\Local\Temp\state.json)" (no `RETRIBUTION_EXPORT_DIR` set on the server + the client installPath doesn't exist there); the local `Missions\state.json` the user first pulled is a stale Jun-20 file from a different campaign. Fetch the TEMP file to process the turn, and set `RETRIBUTION_EXPORT_DIR` on the server for a stable path going forward
- **Sizing/variety rework (2026-07-03), re-opens the runtime leg.** Player feedback off the above flight
  ("only 3 vehicles, only 1 convoy") drove a rework in `game/retlab/vietnam_convoy.py`: a
  concurrent-convoy **budget** (`BASE_MAX_CONVOYS` 1→2, `SURGE_MAX_CONVOYS` 2→3 under `trail_surge` ≥ 2.0)
  replaces the old "is one already flowing" check, and `_pick_trail_corridor` gained `exclude_sources` so
  filling the budget **prefers distinct roads** — several campaigns (Yankee Station/Steel Tiger's full
  trail network, Khe Sanh's two rear feeders, Red Flag 81-2's aggressor corridors) genuinely have more
  than one opfor-opfor road to spread onto. A single-corridor map still caps at one convoy (no regression).
- **Root cause found + fixed same day: the real gate was an empty rear economy, not the cap.** A headless
  engine load found every rear opfor CP's `Base.armor` at **zero at turn 0** across all 4 land Vietnam
  campaigns — it's the coalition's production/income stock, not a garrison, so turn 1 (when the flown
  session above found only 3 vehicles) genuinely had almost nothing to skim regardless of
  `MAX_CONVOY_UNITS`. `_seed_trail_source` now tops a picked source to a standing stock (2× a convoy load,
  same bound as the pre-existing COIN ratline) before every skim — from the coalition's real
  `Faction.frontline_units` roster outside COIN, framed as external logistics support (the Ho Chi Minh
  Trail's actual historical character — matériel from China/the USSR, not local production).
  `MAX_CONVOY_UNITS` also raised 4→10 now that it's the real constraint. **Verified with a real engine
  load** (turn 1): Yankee Station spawned 2 convoys of 10 units each on 2 distinct roads (20 vehicles
  total, vs. the old 3-vehicle single column); Khe Sanh spawned 2 convoys of 10 on its 2 rear feeders. 19
  unit tests updated/added (`tests/retlab/test_vietnam_convoy.py`, `tests/retlab/test_red_tempo.py`),
  all green; mypy/black clean; full suite green (1433 passed).
  **Re-fly pass:** confirm more than one convoy can be on the map at once on a multi-corridor campaign
  (Yankee Station/Steel Tiger/Khe Sanh/Red Flag 81-2), each on a visibly different road, each carrying up
  to 10 vehicles — a visibly bigger trail than the original single 3-4 vehicle column.
- **Known gap, flagged not fixed:** `operation_velvet_thunder.yaml` has **no `supply_routes` block at
  all** — its theater (Marianas islands: Guam/Rota/Tinian/Saipan) has no roads between the separate
  islands for a convoy to drive, so `vietnam_convoy_interdiction: true` is a silent no-op there. Either
  drop the toggle from that campaign or design an island-appropriate reinterpretation (naval convoy?) —
  out of scope for this session.
- **What changed:** the convoy is no longer a `vietnamops`-plugin `coalition.addGroup` phantom (a free,
  unrecorded unit). It is now a **real, tracked enemy convoy** created in the force model
  (`game/retlab/vietnam_convoy.py` `ensure_enemy_trail_convoy`, run once per turn from `finish_turn`):
  it skims a few of the opfor's real rear units and moves them toward the front via a real `TransferOrder`,
  so interdicting it denies real reinforcements and the loss is recorded as `enemy_convoy`. The prior
  2026-06-30 runtime-cycle verification no longer applies (there is no runtime spawn to verify).
- **Headless adjudication:** `tests/retlab/test_vietnam_convoy.py` locks the corridor pick (nearest
  opfor→opfor road, ignores the opfor→friendly front), the unit skim (fraction cap), the guards (setting off /
  convoy already flowing / turn 0 → no-op), and that a real `TransferOrder` of skimmed rear units is created.
  `test_vietnamops_luadata.py` asserts the emitter never emits a `convoy` node. The end-to-end convoy spawn +
  BAI-objective + loss-recording is engine behaviour that only a flown turn exercises.
- **Setup:** Start a **NEW** game with **Vietnam Ops → Convoy interdiction** on (a Vietnam campaign with an
  enemy supply road behind the front — Khe Sanh). Advance a turn so `finish_turn` runs, then inspect the map.
- **Pass:** a **real red convoy** is present on a road behind the front (visible on the map, and offered as an
  **Armed Recon / BAI objective**); flying the Armed Recon and destroying it registers an **enemy_convoy loss**
  at debrief and those units **do not arrive** at their destination CP (the source CP's armour dropped by the
  skimmed count when the convoy was created). Right-clicking the enemy supply route still frags Armed Recon
  onto that corridor (L7).
- **Fail signature:** no convoy ever appears despite the opfor having rear armour and a road corridor (corridor
  pick / transfer creation broken); the convoy isn't a targetable objective; killing it records nothing at
  debrief (it wasn't a real `Convoy` — check `arrange_transport` took the Road leg); the source CP is gutted
  (skim cap wrong).

### L9 — Super Gaggle hilltop resupply · §37 · ◐ PARTIAL

**2026-09-16, headless read of the DM's Yankee Station turn-1 save (`Vietnam tes.retribution`, 60-min mission)** — **the gaggle is committed at turn 1.** `super_gaggle_commitment` names FOB Khe Sanh as the outpost, launches from 12 km south-west of it, and commits two UH-1H (`SuperGaggle-T1-Helo-1/2`) with two F-4E-45MC suppressors (`SuperGaggle-T1-Sandy-1/2`), drawn from real squadrons. The 600-s launch delay, the run and the loss charge-back remain the flown part.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no Vietnam campaign in the captures.** Unchanged.

**History:** 2026-07-01 `intelligent-dubinsky` runtime run PASSED; **2026-07-02 Trail 2 session `wonderful-chatterjee`: second clean run — both CH-53Es closed to 140 m of FOB Khe Sanh at t≈306, returned, landed and shut down; BOTH F-4E suppressors (`SuperGaggle-T1-Sandy-1/-2`) were shot down (t=973 — its wreck also killed a friendly soldier — and t=2897), so the loss-accounting leg is finally armed**: after the turn is processed with the real server `state.json`, the next-turn debrief must charge 2 F-4E airframes to the suppressor squadron and 0 CH-53s — that check is what remains
- **Launch-delay rework (2026-07-03), re-opens the runtime leg.** The flown pass above found the whole
  run over by t≈306 s — the helos spawn at t=0 (mission-config load, before anyone can plausibly be
  airborne). `resources/plugins/vietnamops/vietnamops-config.lua`'s Super Gaggle block now wraps the
  entire spawn (helos, suppressors, cue, F10-mark tick) in a local `spawnGaggle()` and fires it via
  `timer.scheduleFunction(..., timer.getTime() + DELAY)` instead of immediately; `DELAY` defaults to
  **600 s** (new plugin option `gaggleDelaySec`). The "armed … launching in Ns" log line still fires at
  config time so ops get immediate confirmation; only the spawn itself is deferred.
  **Re-fly pass:** confirm nothing spawns before `DELAY` elapses, the delayed run then behaves exactly
  like the already-verified 2026-07-02 pass (delivery, losses charged), and a `dcs.log` warning appears
  (not a silent failure) if the deferred `spawnGaggle` call ever errors.
- **Partial (2026-07-01, flown session — Tacview + `dcs.log`):** `dcs.log` shows `Super Gaggle armed
  (outpost FOB Khe Sanh, 2x CH-53E, single run)`; `SuperGaggleHelos` (2× CH-53E, the committed real-squadron
  airframes by name) + `SuperGaggleSandy` (2× F-4E suppressors) spawned **once** at t≈73 s. Tacview: the helo
  pair launched from Sochi-Adler, flew the 13 km run and **overflew FOB Khe Sanh at t≈300 s** (~180 m), then
  returned, loitered and **landed back at the launch field** — no re-roll, no respawn, no `coalition.addGroup`
  error. The Sandys escorted the run window (Sandy-1 landed + despawned at ~1,076 s). **Unexercised:** both
  helos survived, so the debrief charge-back (`reconcile_super_gaggle`) and the outpost ground-strength credit
  weren't stressed — the row's key check still needs a session where a gaggle helo is shot down.
- **What changed:** the gaggle is no longer a phantom, unbounded-respawn `coalition.addGroup` spawn. It is
  planned once per turn from **real BLUE squadrons** (`game/retlab/super_gaggle.py` `plan_super_gaggle`),
  spawns **exactly** the committed airframes (by name) **once** (no respawn), and a shot-down committed airframe
  is charged back to its squadron at debrief (`reconcile_super_gaggle`). The **key new check** is the loss
  accounting, not the spawn.
- **Headless adjudication:** `tests/retlab/test_super_gaggle.py` locks the plan (draws real squadron
  airframes, counts capped by `owned_aircraft`, clears when off / no outpost / no helo squadron) and the
  reconcile (charges only killed committed names, floors at 0, **losses-only — no delivery strength credit**
  (2026-07-07 design call), clears the commitment). `test_vietnamops_luadata.py` locks the emitter (serializes the commitment; no commitment → no
  node). The runtime helo spawn + routing + the single-run cue are Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Super Gaggle** on and a **friendly forward FOB/FARP** near
  the front plus a friendly rear airfield/FARP to launch from (Khe Sanh laydown qualifies), and a BLUE
  helicopter squadron with airframes. Advance a turn (so `plan_super_gaggle` runs), then fly/fast-forward.
- **Pass:** a helo gaggle drawn from the real helo squadron (its own aircraft type) spawns over the launch
  field, flies to the outpost, and announces "SUPER GAGGLE inbound … Marked on the F10 map" then "delivered" on
  arrival — **once, no re-roll**. A **live F10 map mark** tracks the gaggle the whole way (moves with the lead
  helo, disappears on delivery/loss) so it's findable and escortable from anywhere on the map. `dcs.log` shows
  "Super Gaggle armed (outpost …, Nx …, single run)". **Critically:** a shot-down gaggle helo shows up at
  debrief as a **real airframe loss to that squadron** (its `owned_aircraft` drops). **Losses-only
  (2026-07-07 design call):** a clean run gives **no** garrison-strength boost — there is no runtime
  "delivered" signal, so "survived" can't be told from "never spawned"; the gaggle costs only the airframes
  it actually loses.
- **Choreography:** a fast-mover suppression flight (the committed attack squadron's airframes) spawns with the
  gaggle, flies over the outpost, and its losses are likewise charged back. The suppressors spawn with their
  squadron aircraft's default loadout — confirm whether they actually attack the AAA or are visual-only. A
  suppressor spawn failure must NOT affect the helo run (guarded); the cue then omits the "fast movers" line.
- **Fail signature:** no gaggle despite a helo squadron + outpost + launch (plan/commitment broken); the gaggle
  **re-rolls** (respawn not removed); a killed gaggle helo is **not** charged to the squadron at debrief (the
  loss-accounting failed — its unit name didn't reach the debrief killed lists, or the squadron-id lookup
  missed); the outpost isn't bolstered on a clean run; a `coalition.addGroup` / `Group.getByName` Lua error in
  `dcs.log`; the squadron owned count goes negative (floor failed).

### L11 — Snake and nape (napalm CAS) · §39 · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no Vietnam campaign in the captures.** Unchanged.

**History:** **player leg VERIFIED** 2026-07-02 flown Trail 2 session `wonderful-chatterjee`: 4 real player Snakeye deliveries, zero plugin errors, and the user confirmed the split exactly matched the gate — Toxic's two in-gate passes (≈119 m and ≈111 m AGL at 153/274 m/s vs the 152 m / 93 m/s gate) bloomed the fire walls ("it was awesome"), Bulldog's two above-ceiling passes (≈213 m and ≈177 m AGL) correctly drew none. Still owed = the **AI leg**: an AI CAS/BAI flight pressing to the §P1c 500 ft deck and tripping the release gate itself
- **Detonation-anchored (2026-07-02 rework — this row tests the NEW trigger):** fire now keys off a **real
  eligible-bomb release** (weapon type name vs the `napeWeaponPatterns` option, default `SNAKEYE`; Mk-77 cans
  excluded — Splash Damage owns real napalm) made from a low + fast **release profile**, with each weapon
  tracked to impact and one fire node + bite laid **at the real impact point**. A dry pass lays nothing; a
  miss burns where it missed; the swath is your actual ripple.
- **AI leg (2026-07-02 — the doctrine low-level attack profile, supersedes the "player-only in practice"
  note):** the 2026-07-01 diagnosis (AI attack flights never fly the deck — the session's A-1s sat at
  6,400 m, so AI could never pass the release gate) is now addressed in the planner:
  `Doctrine.low_level_attack_altitude` (Vietnam = 500 ft, = the `napeCeilingFt` default) presses Vietnam
  **CAS/BAI/Armed Recon** plans onto the deck (RADIO/AGL legs; Strike/helos/heavies exempt — §39 features
  note). Gate helper + waypoint clamp are unit-tested; **the flown question** is whether the DCS AI's own
  `AttackGroup` delivery then releases ≤ 500 ft AGL or climbs to dive-bomb anyway. Watch an AI Interdiction/
  CAS A-1/A-4 with Snakeyes over the front: **pass** = it runs in low and its impacts lay §39 fire; **fail
  signature** = the flight presses in at ~500 ft AGL but pops to altitude at the attack and no fire lays
  (next levers: `altitude=` on the BAI `AttackGroup` task, or raise `napeCeilingFt`). Needs a NEW game
  (doctrines pickle by value). Terrain check rides along: no AI CFIT on the low legs in Caucasus valleys.
- **Headless adjudication:** `game/missiongenerator/tests/test_vietnamops_luadata.py` locks the `snakeNape`
  on-marker (emitted when `vietnam_snake_and_nape` is on, independent of the other suite features; off = no
  node). The `S_EVENT_SHOT` matching, the release-profile gate, the weapon tracking/`land.getIP` impact
  resolution, and the `effectSmokeBig`/`explosion` placement are runtime Lua, exercisable only live.
- **Setup:** A Vietnam campaign with **Vietnam Ops → Snake and nape** on. **Fly it yourself** in anything
  carrying **Mk-82 (or Mk-81) Snakeyes** (A-4/A-1/F-4 etc. — no aircraft-type gate any more): ripple a pair+
  off a **low, fast** delivery (≤500 ft AGL, ≥180 kts ground speed at release) onto enemy ground. Also fly
  one **control**: a dry low pass (no release) and, if flying the A-4E-C, one **Mk-77** drop.
- **Pass:** each Snakeye impact point erupts in a smoke-and-fire node a beat after release (at the bombs'
  fall line — the ripple draws the wall of fire), nearby soft targets take the extra bite, and one
  "SNAKE AND NAPE — napalm on the deck" cue appears per salvo (not per bomb); the fires burn ~90 s then stop;
  the dry pass lays **nothing**; a deliberate miss burns at the miss point, not on the target; a Mk-77 drop
  shows only the Splash Damage napalm (no doubled §39 fire on top); `dcs.log` shows "Snake and nape armed
  (release gate …, ordnance 'SNAKEYE' …)" with no Lua error.
- **Fail signature:** no fire despite a low/fast Snakeye release (the **weapon type name doesn't match the
  pattern list** — the #1 suspect, esp. mod-pack Snakeyes; check `dcs.log`, widen `napeWeaponPatterns`); fire
  at the release point or the aircraft instead of the impacts (tracking/`land.getIP` bug); fire on a dry pass
  (release gate broken); a doubled effect on Mk-77 (exclusion broken); fires never stop (permanent infernos —
  `stopEffect` failing); a cue per bomb instead of per salvo; an `S_EVENT_SHOT` handler error in `dcs.log`
  (the handler is pcall-wrapped — any "snake-and-nape shot handler error" line counts); it triggers from
  altitude or at low speed (the release ceiling/speed gate wrong); the bite far too strong/weak
  (`napeBlastPower`).

### M6 — Red tempo: turn-windowed trail surge, ground-offensive pulse (campaign layer W6, rehomed 2026-07-21) · campaign layer · ☐ UNTESTED

**2026-09-16, headless read of the DM's Yankee Station turn-1 save (`Vietnam tes.retribution`, 60-min mission)** — **the turn-1 window is live.** Yankee Station's `red_tempo` reads Rolling Thunder from turn 1 (`trail_surge` 1.5), the Bombing Halt from turn 8 (2.0) and Linebacker from turn 11 (`ground_offensive` 3); `trail_surge_multiplier` returns 1.5 and `ground_offensive_active` False on this save, and the two 15-vehicle trail columns are the surge applied (see L6). The multi-turn feel is still the flown part.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no capture spans a `red_tempo:` window.** Unchanged.

**History:** built 2026-07-01, rehomed 2026-07-21 to a top-level turn-windowed `red_tempo:` schedule — last-window-wins by `from_turn`, authored on 6 campaigns; parse/window/stance/convoy-surge all unit-tested, the multi-turn campaign feel needs a played arc. The `resolve_regen` lever was dropped 2026-07-21 with the will economy.
- **Headless adjudication:** the `red_tempo:` parse, the ground-offensive window math, the raise-only
  stance pulse, the end-to-end convoy surge (second column + doubled skim),
  and the 6 campaigns' authored schedules are all locked in `tests/retlab/test_red_tempo.py`. What CI cannot
  adjudicate: the multi-turn *feel* — whether the surge window reads as a logistics push and the
  ground-offensive window reads as an Easter-Offensive pulse.
- **Setup:** a NEW campaign with a `red_tempo:` schedule (Yankee Station, Velvet Thunder, Desert Storm,
  Inherent Resolve, Enduring Resolve, or Red Flag 81-2); play (or fast-forward) into a `trail_surge` window
  and across a `ground_offensive` window.
- **Pass:** during a `trail_surge` window, up to TWO trail convoys flow at once with bigger loads (Armed
  Recon has visibly more trail targets); on a `ground_offensive` window, red front stances go aggressive for
  the window (the front presses BLUE — pressure, not sweep-captures) with the trail surging alongside; after
  the window red reverts to the commander's own stance choices; a campaign with no `red_tempo:` block shows
  zero change.
- **Fail signature:** red stances stuck aggressive after the window (the raise should stop applying — check
  `ground_offensive_active` window math); three+ convoys stacking (the `max_convoys` cap); a campaign with no
  schedule surging (only campaigns with a `red_tempo:` schedule are affected — the window in effect is the last one whose `from_turn` is reached).
  Knobs: the top-level `red_tempo:` schedule window values; `GROUND_OFFENSIVE_MIN_SURGE` (red_tempo.py).

## N. Mod support

## O. Client map

### O1 — Local DCS chart base layer renders + aligns · §42 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side; no capture can show the map layers panel.** Unchanged.

**History:** built 2026-07-01; routes test-covered, tiles generated locally; needs an in-app pass + the CI client rebuild
- **What CI covers:** the `/map-tiles` listing/serving routes (meta parse, malformed-meta skip, 404s,
  traversal guard) are unit-tested, and the tiler ran clean over Flappie's Caucasus GeoTIFF. What CI cannot
  adjudicate is the chart actually rendering in the app and *aligning* with the campaign overlays.
- **Setup:** tiles installed at `Saved Games\Retribution\MapTiles\caucasus_flappie` (slice with
  `tools/tile_geotiff.py` if absent); any **Caucasus** campaign loaded; a client build that includes the
  base-map button.
- **Pass:** a "DCS Caucasus chart" button appears in the map layers panel's base-map row; selecting it swaps
  the basemap to the chart with no gray holes inside the theater at zooms ~6-12; control points / front
  lines / TGO markers sit on the chart exactly where they sat on Esri imagery (spot-check an airfield: the
  CP marker on its chart runway symbol); the choice survives a reload; on a machine/dir without tiles the
  button simply doesn't appear.
- **Fail signature:** markers visibly offset from the chart (georeference/tiling math bug — check one tile's
  bounds against the TIFF's ModelTiepoint); gray tiles inside the theater (pyramid gaps — re-run the tiler);
  the button never appears with tiles present (GET `/map-tiles/` — malformed `tileset.json` is skipped with
  a server-log warning); the map goes blank after selecting (tile URL/port mismatch — the layer URL must ride
  `HTTP_URL` like every other backend call).

---

### P1 — COIN Enduring Resolve: the living insurgency in play · COIN C-series · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the Afghanistan captures did not run COIN.** Tests 20–23 (Afghanistan, 08-28 and 08-29) registered no IED, HVT, cell or cache group and printed no `COIN|` line at all; only Vietnam Ops harassment armed. Whether those games were Enduring Resolve with the plugin unticked (the §36 lesson) or another Afghanistan campaign is not recorded; either way nothing here was exercised. Inherent Resolve (test 17) did run the stack, see P7.

**History:** built 2026-07-02; the whole stack headless-verified on the real campaign — regen/revival, cache throttle to the 0.25 floor, will profile, 3-phase arc — the played feel needs a campaign
- **Headless adjudication:** the campaign loads through the real `GameGenerator` pipeline (probe 2026-07-02):
  13 insurgent strongholds each carry their authored ammo caches (28 total), `coin_state` anchors all 13
  (garrison + eligible-cell caps + cache totals), killing cells revives at 2/turn toward the anchor and never
  past it, killing both of a stronghold's caches drops its regen to the 0.25 floor, `will_profile_for`
  resolves "The Coalition's mandate"/"the insurgency's momentum" with `red_cache_lost` 4.0, and the
  Disrupt → Clear and Hold → Break the Momentum arc parses with the coordinate-anchored Lashkar Gah/Herat
  population-center rings. What CI cannot adjudicate is the **played loop**.
- **Setup:** NEW campaign "Afghanistan - Operation Enduring Resolve (COIN)" (all COIN toggles preseed on).
  Play 5+ turns: strike a stronghold's cells one turn WITHOUT touching its caches; recon it two turns later.
  Then kill both its caches and repeat.
- **Pass:** the cleared cells come back within ~2 turns while caches stand (and the recon-fog picture shows
  them dead until re-reconned — "it's shooting again"); after the caches die the same stronghold visibly
  stops refilling (floor trickle only); the will message reads mandate vs momentum with cache kills as
  labeled "ammo caches xN destroyed" movers; trail convoys flow (the ratline); FOB standoff fire lands on
  forward fields; the phase ribbon opens on "Disrupt the Network"; a strike near the Lashkar Gah ring draws
  the ROE warning in the package dialog and a violation drains the mandate.
- **Fail signature:** strongholds never refill (regen dead — check `coin_insurgency` survived the preseed and
  `coin_state` anchors exist / anchor caps are 0); refill continues at full rate with all caches dead
  (throttle broken); revived units invisible in the next mission (TGO revival not reaching the generated
  miz); the will message shows Washington/Hanoi (profile lookup failed — name mismatch degrades to defaults);
  the arc opens on a Tier-0 phase (authored parse failed); zone rings missing from the map (x/y anchor bug).

### P3 — COIN re-infiltration: the insurgency retakes ground · COIN C1.5 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised; see P1.** Unchanged.

**History:** built 2026-07-03; the staged pipeline / eligibility / conservation bound / stage machine / flip + will handoff are fully unit-tested with fakes, and the campaign preseed + module wiring are headless-verified — the real TGO spawn + engine capture flip + the played feel need a campaign
- **Fiction-kit note (2026-07-04):** the infiltration cell now shares the P4/P5/P6 unit retype (`_spawn_cell` → `cell_unit_types`) — an armed technical + infantry rather than the faction front-line armor. First-fly should confirm the seeded cell reads as an insurgent element.
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a red cell/cache near a blue/neutral target (attached to the source stronghold, per the allegiance constraint), the engine-native `ControlPoint.capture` flip, and the reparent of the seeded cell+cache onto the flipped CP. The design note itself flags this as in-play-only (timers need tuning against real Shattered Dagger geometry).
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_reinfiltration` preseeds on). Clear an insurgent stronghold's approach and take a nearby base, then **leave it ungarrisoned** (≤ 4 ground units) while the source stronghold still has healthy caches. Play ~5+ turns watching the info feed.
- **Pass:** an intel line "infiltration reported near {base}" appears; a real red cell shows up near that base on the next mission; ~2 turns later "a supply cache has been located" + a cache TGO; ~2 turns after that the base **flips to red** with a small garrison and one cache, and the mandate drops with a labeled "strongholds re-infiltrated x1" will mover. Each stage is strikeable: killing the cell aborts (+cooldown), killing the cache reverts a stage, garrisoning the base above 4 units aborts it, and killing the source stronghold's caches stops new attempts. The total red base count never exceeds turn 0.
- **Fail signature:** the cell/cache render **blue** (allegiance/reparent bug — they must attach to the red source stronghold); an attempt starts against a garrisoned/player-spawn/out-of-range base (eligibility gate); the red base count grows past turn 0 (conservation broken); a flip fires with no warnings (stage timers skipped); the mandate doesn't move on a flip (`consume_reinfiltration_flips` / will handoff not wired); the flipped CP comes back at full strength instead of the weak re-anchor.
- **Concealed "in here somewhere" areas (covers P3–P6, added 2026-07-05):** an **un-reconned** hidden insurgent object (re-infiltration cell P3, roadside IED/VBIED P4, HVT convoy P5, dispersed cell P6) no longer draws an exact marker at all — the web map shows a **dashed amber uncertainty circle** (~4 km, centre jittered off the true position server-side; the true coordinates never reach the client; amber since the §28 UI audit — dashed red is ROE-only) with a "Suspected insurgent activity — fly recon to localize" tooltip. The circle is clickable/right-clickable like a marker (frag TARPS/CAS onto it); once TARPS/attack discovers the TGO it **snaps to the exact symbol** at the real position. Caches and the stronghold garrisons stay exact (infrastructure). Needs an **in-app pass + the CI client rebuild**: on Enduring/Inherent Resolve confirm new IEDs/HVTs/cells appear as circles (not diamonds), the object is NOT at the circle centre, the circle doesn't wander across refreshes/turns, recon snaps it to the marker, and the fog-overview reveal shows everything exact. **Fail:** a circle centred dead-on the object (jitter not applied / seed broken), the marker AND circle both drawn, the circle jumping between refreshes (non-deterministic seed), a revealed/killed object still circled (`known_for` not consulted), or caches/garrisons circled (concealed flag leaked to non-hidden spawns).
- **Map symbology (covers P3–P6, added 2026-07-03):** insurgent contacts must read on the map as an insurgency, not an armor park. Two observables: **(a) suspect-until-reconned** — an un-reconned insurgent contact shows as a **SUSPECT** track (yellow frame); after TARPS/strike confirms it, it flips to **HOSTILE** (red). **(b) real NATO symbol** once confirmed — infantry for a re-infiltration cell (P3) / dispersed cell (P6) / a stronghold's standing militia, the IED activity glyph for a roadside IED (P4), the dismounted individual-leader glyph for an HVT (P5); ammo caches keep the cache symbol and the fixed radar-SAM crust keeps its air-defense symbol. All the SIDCs (hostile + suspect framings) were render-verified in the pinned milsymbol 3.0.4 (distinct valid glyphs), so this is a look-right confirm, not an unknown. **Fail:** a confirmed contact still draws the hostile-armor diamond (`sidc_entity_override` didn't reach the TGO / the garrison pass didn't run), an un-reconned contact shows hostile-red immediately (suspect framing not applied — check `recon_intel_fog` is on), the SAM crust or a friendly unit turns into infantry (composition scope leaked), or any contact draws an empty "unknown" frame (wrong entity code for the pinned lib).

### P4 — COIN roadside IEDs: sweep the trail or pay · COIN · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised; see P1.** No IED or VBIED group was generated in any capture (the `SVBIED` names in tests 21–23 are map trigger zones, not units). Unchanged.

**History:** 2026-07-04, user pass — "good but needs reworked"; **REWORK APPLIED 2026-07-04** in two parts: fiction-kit retype + IED-vs-mobile-VBIED variety with an in-mission suicide-vehicle drive (see the two rework bullets); **REWORKED AGAIN 2026-07-05** — the static variant is now a static-object emplacement + security team (third rework bullet) — needs a re-fly to confirm the static emplacement reads right AND the VBIED variant drives at a friendly base and is interceptable) (was ☐ UNTESTED, built 2026-07-03; the fuse state machine / clear-vs-detonate / concurrent cap / road-nearest-the-front placement / mandate feed are fully unit-tested with fakes, and the campaign preseed + red-red ratline are verified — the real emplacement spawn + recon-fog visibility + played feel need a campaign
- **Rework (2026-07-04) — fiction-appropriate unit kit.** The COIN objects were generated as trimmed FRONT_LINE force groups with only the *map symbol* overridden, so the metal underneath was the faction's armor (a BMP-1 wearing an IED icon on a conventional faction; a plain technical on Toyota). `spawn_red_ground_at` now takes a `unit_types` list and `_retype_units` (`game/retlab/coin.py`) re-points the trimmed units' DCS *types* (+ names) to kit drawn from the red faction's own roster: an **IED = a lone soft supply truck** (`ied_unit_types`), an **HVT = a leader's jeep + a 2-rifle escort** (`hvt_unit_types`), a **cell = an armed technical + infantry** (`cell_unit_types`). On the Enduring Resolve Toyota Al Gaib faction that resolves to Ural-375 / UAZ-469 + 2× Insurgent AK-74 / DShK gun-truck + Insurgent AK-74 (verified headless). Selection reads only the faction's resolved roster (never a hardcoded, possibly-unregistered id) and no-ops to the old generated group if the faction can't fill the roles. Covered by `tests/retlab/test_coin_units.py`. **Re-fly = confirm the IED now reads as a suspicious truck (not a combat vehicle) and is still findable+killable.**
- **Rework (2026-07-04, part 2) — static IED vs mobile suicide VBIED + in-mission movement.** Each plant now deterministically alternates a **static roadside IED** (buried, `FUSE_TURNS` 3) and a **mobile VBIED** — a suicide vehicle that drives for the nearest friendly base (`_nearest_blue_cp`) on a shorter `VBIED_FUSE_TURNS` (2). Same fuse→detonation→`ied_detonations`→mandate consequence; distinct "intercept it before it arrives" / "VBIED reached {base}" messaging (`game/retlab/coin_ied.py`, tested in `test_coin_ied.py`). The **driving** is COIN's first Lua runtime: `game/missiongenerator/coinluadata.py` emits each mobile VBIED's DCS group name + target base as `dcsRetribution.coin.vbieds`, and the new `resources/plugins/coin/` plugin routes it via `mist.goRoute` (`tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py`). **Movement only** — kill it en route and it's recorded natively as intercepted; let it reach the turn end and the fuse resolves against the mandate. **Re-fly (Lua, cockpit-only) = watch a VBIED actually drive toward a friendly field, kill one before it arrives (see "intercepted"), and let one run (see the mandate hit); confirm a static IED sits still.**
- **Rework (2026-07-05) — the static IED is a static-object emplacement with guys around it.** User call ("change the IED back to the proposed static object but spawn some guys around it"): the *static* variant is no longer a lone supply truck — `ied_emplacement_unit_types` (`game/retlab/coin.py`) builds an emplaced **device** (a vanilla `Fortification.Oil_Barrel` static — faction-independent, never degrades) guarded by **two riflemen** from the faction's own infantry (Toyota Al Gaib → 2× Insurgent AK-74, real-roster verified); the mixed static+infantry group splits correctly at mission generation (statics and vehicles are already generated separately per unit). **Clearing is device-anchored** (`_ied_intact` in `coin_ied.py`): destroy the barrel and the IED is cleared even if the team survives (they melt away); killing the team alone leaves the fuse ticking. The VBIED keeps the lone-truck kit; pre-rework saves' truck emplacements (no static in the group) keep the old any-unit-alive clearing. A rifle-less faction gets the bare device sized to 1 unit (never cycled barrel copies). Covered by `tests/retlab/test_coin_units.py` + `test_coin_ied.py`. **Re-fly = confirm the emplacement reads as a small roadside object with dismounts around it (not a parked truck), that killing the barrel clears it, and that strafing only the team does NOT clear it.**
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a red emplacement on a ratline waypoint (attached to the forward red stronghold for allegiance), the retyped static actually rendering/dying as a destroyable object in DCS, whether it reads as a recon-fogged Armed-Recon/CAS target, and whether an AI Armed Recon flight auto-services it.
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_ied` preseeds on). Watch the info feed for "IED activity reported on the road near {stronghold}"; TARPS that trail segment to ID the emplacement, then frag CAS/Armed Recon on it.
- **Pass:** up to 2 hidden IED emplacements sit on the insurgent supply roads (recon-fogged until TARPS'd); striking one within ~3 turns clears it ("Roadside IED … cleared") with no mandate hit; ignoring one past the fuse detonates ("IED detonation … coalition casualties") and drops the mandate with a labeled "IED detonations xN" will mover; a cleared/detonated IED is replaced on the next turn (staying at the cap), and two IEDs never sit on the same road segment.
- **Fail signature:** IEDs render **blue** (allegiance bug — must attach to the red stronghold); none appear (no red-red `convoy_routes` — the ratline didn't build, or the faction has no FRONT_LINE group); the emplacement is fully visible with no recon fog (TGO fog not applying); a detonation doesn't move the mandate (`blue_ied_detonation` weight 0 / `consume_ied_detonations` not wired); IEDs pile onto one road (the used-road de-dup broke); the count runs away past the cap.

### P5 — COIN high-value targets: hunt the leadership · COIN · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **one data point.** Inherent Resolve test 17 surfaced a named HVT (`Mullah Nasir`) and the auto-planner fragged a BAI package on him with a SEAD Escort and a jammer; whether he moved, whether he died and what the mandate did are not in the capture. The stale ROE-zone signature stands corrected by the 08-21 note.

**⚠️ Stale reference (2026-08-21 audit):** a fail signature below blames "the ROE zones
aren't covering him". §40's ROE zones were removed 2026-07-21 — there are no zones to cover
anybody. An in-ring kill that charges momentum but not the mandate is now a wiring question in
the HVT feature itself, not a zone-overlap one.

**History:** 2026-07-04, user pass — "same as above"; **REWORK APPLIED 2026-07-04** in two parts: fiction-kit retype (a small convoy, not 3 BTR-80s) + an in-mission random patrol you have to run down (see the two rework bullets) — needs a re-fly) (was ☐ UNTESTED, built 2026-07-03; the window state machine / kill-vs-escape / nearest-front pick / cooldown / momentum feed are fully unit-tested with fakes, and the campaign preseed + wiring are verified — the real named-emplacement spawn + recon-fog + the in-ring CDE interaction + played feel need a campaign
- **Rework (2026-07-04) — fiction-appropriate unit kit.** Same change as P4 (`_retype_units` + `hvt_unit_types` in `game/retlab/coin.py`): the HVT group's DCS unit types are re-pointed from the faction's front-line armor to a **command team** — a leader's jeep (`UAZ-469` on Toyota Al Gaib) plus two riflemen (`Insurgent AK-74`), drawn from the faction roster. Verified headless. Covered by `tests/retlab/test_coin_units.py`. **Re-fly = confirm the HVT now reads as a small leadership element (a jeep + escort) rather than an APC platoon.**
- **Rework (2026-07-04, part 2) — the HVT convoy moves in-mission.** The HVT is now a small **convoy** (`HVT_UNITS` 3→4: leader jeep + armed technical + 2 rifles) that **patrols a slow random loop around its area** rather than sitting parked, so you have to find and run it down — the old armor-hunt movement fused with the new HVT. COIN's first Lua runtime drives it: `game/missiongenerator/coinluadata.py` emits the live HVT's DCS group name + centre as `dcsRetribution.coin.hvt`, and `resources/plugins/coin/` routes it via `mist.goRoute` (alarm-green) to a fresh `mist.getRandPointInCircle` destination within `hvtPatrolRadiusM` each cadence, after a startup grace (`tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py`). **Movement only** — killing the convoy inside the window is still the turn-boundary `hvt_kills` momentum blow (a decapitated convoy just stops being routed); the CDE dilemma (a kill inside a §40 ring also charges the mandate) is unchanged. **Re-fly (Lua, cockpit-only) = confirm the convoy actually drives a wandering patrol in its area, that you can track + kill it on the move, and that it stops moving once dead.**
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a named 3-unit HVT group near the forward stronghold, whether it reads as a recon-fogged strike target, and — crucially — the **CDE interaction**: an HVT sitting inside a population ring should make his kill *both* an `hvt_kills` momentum blow *and* a §40 `count_roe_violations` mandate hit (the dilemma is emergent from the existing ROE machinery, not special-cased here).
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_hvt` preseeds on). Watch the info feed for "Intel: HVT {name} located near {stronghold} — a window to strike"; engage to ID him (recon reveals nothing since the 2026-08-18 §3 rework), then decide whether to take the shot (note if he's inside a town ring).
- **Pass:** one named HVT surfaces near the most-contested stronghold, recon-fogged, live for ~4 turns; killing him inside the window drops the insurgency's **momentum** with a labeled "HVT leaders xN killed" will mover ("HVT … eliminated"); killing him **inside a population ring** *also* drains the **mandate** via the ROE-violation charge (the dilemma); letting the window pass with no kill just closes it ("gone to ground") with no penalty; a new HVT surfaces after the cooldown; only one HVT is ever live at a time.
- **Fail signature:** the HVT renders **blue** (allegiance bug); none appears (no red strongholds, or the faction has no FRONT_LINE group); no recon fog on the emplacement; a kill doesn't move red momentum (`red_hvt_killed` weight 0 / `consume_hvt_kills` not wired); an in-ring kill charges *only* momentum and not the mandate (the ROE zones aren't covering him — a placement/zone-overlap issue, not this feature); two HVTs live at once (the active-guard broke); a missed window drains will (escape must be free).

### P6 — COIN dispersed cells: patrol the countryside · COIN C4 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised; see P1.** Unchanged.

**History:** built 2026-07-03; the seed/attrite/coalesce state machine, one-cell-per-stronghold spread, the open-field placement gate, and the coalesce-revives-a-dead-cache hook are fully unit-tested with fakes, and the campaign preseed + wiring are verified — the real field spawn + recon-fog + the played feel need a campaign
- **Fiction-kit note (2026-07-04):** the field cell now shares the P4/P5 unit retype — `cell_unit_types` re-points it to an **armed technical + infantry** (a DShK gun-truck + Insurgent AK-74 on Toyota Al Gaib) instead of the faction front-line armor. First-fly should confirm the cell reads as an insurgent fire team, not an armor group.
- **What CI cannot exercise:** the real `ForceGroup.generate` spawn of a 2-unit red cell out in the open field (on the stronghold→coalition line, ≥ 12 km from every CP), whether it reads as a recon-fogged Armed-Recon/CAS target you can find by patrolling, and the coalesce's cache-revival actually re-opening C1 regen in the *next* mission.
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" (`coin_dispersed_cells` preseeds on). Watch the info feed for "insurgent activity reported in the countryside near {stronghold}"; **first destroy a stronghold's caches** (to starve its regen), then leave the field cells alone for a few turns and watch whether that stronghold's cache — and its regen — comes back. Contrast with a run where you hunt the field cells down.
- **Pass:** up to 3 recon-fogged cells sit out in the countryside (one per stronghold, not stacked, ≥ ~12 km off every base); killing one is ordinary attrition and denies the resupply; leaving one ~3 turns coalesces it into its home stronghold and brings a **dead ammo cache back online** ("a supply cache is back in operation") — visibly re-opening that stronghold's C1 regeneration next turn; a stronghold with no dead cache instead gets a small garrison reinforce (bounded by its anchor) or the cell just "melts in"; cells reseed to the cap each turn.
- **Fail signature:** cells render **blue** (allegiance bug); cells spawn on top of a base (< 12 km — the open-field gate broke) or all stack at one spot (the one-per-stronghold spread broke); no recon fog; the coalesce doesn't revive the cache (the cache-revival path not firing / anchor read wrong); a coalesce grows a stronghold **past** its turn-0 anchor (the militia-revive cap broke — must never exceed `tgo_cap`); cells never appear (no red↔blue geometry, or the faction has no FRONT_LINE group).

### P7 — Iraq "Operation Inherent Resolve" (Mosul) COIN campaign plays · Iraq COIN campaign · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the campaign loads and plays; the COIN feed fired in the one captured mission.** Inherent Resolve was played to turn 2 by 2026-08-21 (the 13th-test `autosave.retribution`, Iraq) and test 17 (2026-08-25) is a full turn of it: the drone wing is fragged (two RQ-1A TARPS singletons on Tikrit and Bayji, three MQ-9 BAI flights), a named HVT surfaced and the auto-planner built a package on him (`HVT Mullah Nasir BAI` with a SEAD Escort and an EA-6B jammer), four `Convoy ambush` zones were authored, Vietnam Ops harassment armed for 4 fields, and `COIN|: in-mission liveliness armed`. Not seen: the Mosul/Old City CDE boxes on the map, the front moving, and whether the FOB furnishing reads right, which are app and multi-turn observations. The stale preseed names in the setup stand corrected by the 08-21 note.

**⚠️ Stale setup (2026-08-21 audit), two items.** The preseed list below names
`vietnam_political_will` and `campaign_phases`; both settings were removed 2026-07-21 (§48/§40)
and only a registry tombstone survives, so do not go looking for them in the wizard. And the
drone/TARPS line says the `airecon` plugin banks AI overflights as confirmed BDA, which is what
localizes the concealed IED/cell circles — that plugin and the whole capture ledger were removed
2026-08-20 with §12. Nothing localizes a circle by overflight now; a site is revealed by being
engaged. The rest of the campaign check stands.

**History:** built 2026-07-04; the whole laydown is headless-verified — the from-scratch generator loads to 18 CPs with caches/garrisons/the SA-6/8/9/13 crust/the southern front all binding, and the will profile + 3-phase arc parse — CI-locked in `tests/retlab/test_inherent_resolve.py`; the played feel needs a flown campaign
- **What CI cannot exercise:** whether the DCS Iraq map + the generated `iraq_inherent_resolve.miz` actually load and play in-app; whether the two new factions (`CJTF-OIR 2016`, `Islamic State 2016`) cast sensible squadrons; whether the single southern front (Q-West → Hammam al-Alil) grinds; whether the COIN mechanics (VBIEDs, caches, HVTs, the ratline west to Tal Afar) surface as in the Enduring Resolve P-series; and whether the Mosul / Old City positive-control CDE boxes read on the F10/ME map and price into the mandate. Design note `docs/dev/design/retlab-inherent-resolve-campaign-notes.md`.
- **Drone wing added (2026-07-05, from the installed-inventory audit):** Baghdad now hosts the OIR-signature UAVs — **RQ-1A Predator ×4 on TARPS** (the persistent ISR orbits; the `airecon` plugin banks their AI overflights as confirmed BDA, so the drones are what localize the concealed IED/cell circles) and **MQ-9 Reaper ×4 on BAI** (armed overwatch of the ratline). Unit data gained `TARPS: 700` + honest `max_range` (800/400 NM — the 150 NM default gated them out of Balad→Mosul). **Pass addition:** drone flights appear on the ATO (Predators fragged/paired onto recon, Reapers on interdiction), reach the Mosul area, and an AI Predator overflight flips a suspected-activity circle to a confirmed symbol next turn. **Fail:** drones never planned (faction strings dropped — check the loader log), or they frag but never arrive (range/speed — the slow cruise may need the TOT window checked in play). NEW game required.
- **Setup:** a **NEW** "Iraq - Operation Inherent Resolve (COIN)" game (all COIN toggles + `vietnam_political_will`/`campaign_phases`/`high_digit_sams` preseed on). Requires the DCS Iraq map. Check the New Game list shows it; open the F10/ME map for the Mosul + Old City restricted boxes; fly a turn off Qayyarah West.
- **Pass:** the campaign appears and starts; **6 airfields total** (not a ton) — RED holds 3 (Mosul + SA-6, Erbil, Kirkuk + SA-6) + **10 FOBs** filling the corridor + belt (Tikrit, Bayji, Shirqat, Qayyarah, Hammam al-Alil, Bartella, Tal Afar, Hawija, Makhmur, Gwer — no 100 km empty gaps between towns), **each furnished** (2 garrisons of technicals/gun-trucks + AAA + SHORAD + a strongpoint + caches, not a lone marker); the ME-authored towns sit on the real terrain (the base miz) and the generator-added in-between towns are roughly placed (nudge in the ME if needed); BLUE bases from the south only — **Balad the forward player field (Q-West is gone)**, Al-Taquddum strike, Baghdad support; **one front** sits partway up the Balad → Tikrit (Highway 1) axis and moves under pressure; the COIN feed (caches / IEDs / VBIEDs / emirs / dispersed cells) fires as on Enduring Resolve; SEAD has a job (SA-6 at Mosul + Kirkuk) while SA-8/9/13 + ZU-23 punish the deck; a fixed strike inside the Mosul box costs mandate.
- **Fail signature:** campaign hidden from New Game (version gate) or errors on load; a FOB/airfield in water or off-map; a squadron fragged from a dropped/red field (Qayyarah id 6, Erbil id 4); the front never forms (Balad↔Tikrit route missing) or captures a base by sweep; the crust never fills (faction SAM presets dropped) so SEAD has nothing; red strongholds still read barebones (furnishing not applied); the will meters/phases don't move; the ISIS spawns read as US armor (fiction-kit retype not applied).

### P8 — COIN in-mission liveliness: cell movers + insurgent indirect fire on the FOBs · COIN · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the plugin armed on Inherent Resolve test 17 (`COIN|: in-mission liveliness armed`); movers and barrages were not measured.** Nothing on Afghanistan (P1). Unchanged.

**History:** built 2026-07-05, the "systems feel static" part 3; the emitter shapes/gates/player-field exclusion and the Lua grace + double-guard + mover routing are covered in `tests/missiongenerator/test_coinluadata.py` + `tests/lua/test_coin_runtime.py` — the real DCS driving, the barrage look/feel, and whether the pressure reads need a campaign
- **90-minute mover pacing (2026-07-05, user rule — "sometimes it takes guys a long time to get up in the air"):** the one-way drives (VBIED, infiltrator creep) are **paced** so arrival lands no earlier than `minJourneyS` (default 5,400 s / 90 min) after mission start — every repath recomputes speed = remaining distance / remaining window, capped at the configured speed, floored at a 5 km/h crawl; past the window the configured speed applies. Continuous pacing, not a proximity trigger (the user rejected range-based starts as "lazy and not immersive"). Loop movers (HVT patrol, cell wander) never end, so they already comply. Harness-pinned (`test_coin_runtime.py` pacing tests). **Pass addition:** a VBIED spawned at mission start is still on the road (interceptable) at T+60–80 min, visibly driving the whole time. **Fail:** a VBIED parked at its target base inside the first hour, or a mover teleport-sprinting after the window flips over.
- **What CI cannot exercise:** whether the DCS ground AI actually drives the dispersed-cell wander and the infiltrator creep (the harness models routing calls, not movement); whether the mortar barrages *look* like insurgent IDF (dispersion/power feel) and land clear of parked aircraft; and whether the pressure changes how the campaign feels between stronghold fights.
- **Setup:** NEW "Afghanistan - Operation Enduring Resolve (COIN)" or "Iraq - Operation Inherent Resolve (COIN)" (`coin_harassment` preseeds on; the movers ride the existing `coin_dispersed_cells`/`coin_reinfiltration` preseeds). Fly (or time-accelerate over) a base within ~40 km of a live stronghold; separately, TARPS a dispersed-cell uncertainty circle twice a few minutes apart.
- **Pass:** after the ~5-minute grace, a base near a stronghold draws occasional small impact clusters ("Incoming — insurgent indirect fire on {base}") that are noise/smoke pressure, not aircraft-killers; a player-spawn field is NEVER shelled (cold-start on the nearest base to a stronghold to prove it); a found dispersed cell is *moving* (not parked where the circle was an hour ago); the re-infiltration cell measurably creeps toward its target base over the mission; killing a mover stops its movement (no ghost routing errors in dcs.log).
- **Fail signature:** a barrage lands on a field the player spawns at or recovers to (the exclusion walk missed a package type — check `excludedBases` in the emitted config); fire before the grace expires; barrages on a base with no living stronghold in reach (the 40 km gate broke); every base in the theater shelled (blue filter broke); cells sit motionless all mission (`cells`/`infiltrators` node missing — check the toggles emitted, or `mist.goRoute` errors in dcs.log); `COIN|: setup error` in dcs.log.

---

## Q. Planner / payload UI

## R. Mission map / F10 drawings

### S7 — Measured fuel data adopted from DCS Liberation drives tanker + bingo for 12 airframes · §46 · ☐ UNTESTED

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **not reachable from an AI flight.** With `ai_unlimited_fuel` on, AI fuel is real only between JOIN and SPLIT; the records show every AI jet's fuel frozen from its SPLIT, and landed jets read 0.00. The human's F-15E has no `fuel:` block. The row needs a human in a measured airframe (F-14, F-15C, A-10C, F-4E …) reading the gauge against the card.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from a capture.** The measured `fuel:` blocks drive the kneeboard readouts only since §46's revert; whether the ladder reads plausibly against the cockpit gauge is a cockpit observation nobody has reported. Unchanged.

**History:** adopted 2026-08-07 from the DCS Liberation research pass — twelve `fuel:` blocks copied verbatim for A-10A/A-10C/A-10C_2/A-4E-C/AV8BNA/F-100D/the four F-14 marks/F-15C/F-4E-45MC, fanning out to 16 variants; measured coverage 22 → 40 aircraft types. All 16 pinned in `tests/dcs/test_estimated_fuel_consumption.py`
- **What CI cannot exercise:** the numbers are now *correct on paper* — what no test can say is whether the resulting sortie flies. Adopting a block promotes these twelve out of the kneeboard-only estimate fallback and onto measured `unit_type.fuel_consumption`, which drives **tanker tasking** (`formationattack`) and the **in-flight fuel sim** (`inflight.py`). That is the intended design ("a real `fuel:` block always wins"), but it is a behavior change for twelve airframes landing at once.
- **Setup:** a campaign fielding the Tomcat, the Hog or the Phantom (**Red Tide** for the F-4E/F-15C, **Yankee Station** for the A-4E/F-100D, any modern laydown for the F-14/A-10). Auto-plan a long-legged sortie for one of them and open the kneeboard flight-plan page. The F-14 and F-15C are the sharpest test — their estimate was ~2.4× the measured burn.
- **Pass:** the kneeboard fuel ladder and RTB margin read plausibly against what the jet actually burns in the cockpit, and tankers are fragged for genuinely long legs rather than routine ones. A Tomcat sortie that previously drew a tanker on a medium hop should no longer need one.
- **Fail signature:** the opposite error to the one this fixes — tankers now fragged **too rarely** and jets landing dry, or an RTB margin that reads comfortably positive while the cockpit gauge says bingo. Either means the measured cruise figure is optimistic for how the fork's AI actually flies the profile (Liberation measured a clean cruise at 25,000 ft / M0.85; a low-level Vietnam-doctrine CAS profile burns far more — see the §32-39 low-level attack profile). If that shows up, the fix is a fork-side re-measure per `docs/modding/fuel-consumption-measurement.md`, **not** reverting to the estimate, which was worse in the other direction.

## T. Campaign flow

## U. Upstream-sync runtime adoptions

## Drain order — batch the queue into ~5 flight sessions

**Policy: new feature work is frozen until this queue drains.** The rows are not
24 separate chores — one campaign setup exercises a whole cluster, and the first
session needs *no flying at all* (just auto-plan a turn and read the map). Work
top-down; each session is ordered so the highest-blast-radius, lowest-effort
checks come first.

### Session 1 — Standard land-front, auto-plan turn 1, **observe only** (no sortie)
Highest leverage: planner/placement bugs affect *every* campaign, and you verify
them by inspecting the ATO + map, not by flying.
- A2 (QRA base-defense doctrine), A3 (player-manned QRA alert flight appears in the
  ATO + dispatcher debit), B2 (DEAD reachability gate), B3 (threat-weighted
  BARCAP orbit), B4 (TARCAP/escort reach), C1 + C2 (AWACS/tanker front-anchor +
  depth), F6 (SCAR auto-plan appears in ATO), I4 (frontline clustered laydown —
  inspect the front-line armor spread on the map).
- Setup needs: active land front, enemy airbase ≈90 NM from FLOT, an armor
  concentration near the front, AWACS+tanker support, `scar_autoplan` ON, and a
  player-flyable BARCAP squadron with its "…of which player-manned" spinbox ≥ 1 (A3).

### Session 2 — Fly a strike package off that campaign
- A1 (QRA scramble profile — trigger a raid, include a high-elev alert base),
  A4 (player QRA scramble cue — sit a player-manned alert base and confirm the
  "SCRAMBLE" call fires as the raid closes), C3 (tanker speed), C5 (boom/probe
  match), C6 (fuel-driven pre/post-vul tanking), C4 (A-6E attack/tanker split —
  buy both), H1 (kneeboard overflow on a busy theater), D1 (player-despawn loss —
  land/despawn then end).

### Session 3 — SCAR commander-capture campaign
- F2 (capture → permanent reveal carryover across turns), F5 (mis-ID penalty —
  kill a decoy), E (SOF C-130 insert ground-starts + EW skipped), G2 (TARS BDA
  bridge via an F-14 TARPS pass).

### Session 4 — Plugin-runtime sweep, fly over an active front
- G3 (TIC ambient fire / LOS-blocked positions), G4 (C-130J EW/ISR — fly the
  JAMMING slot).

### Session 5 — Coastal front
- B1 (forward-CAP / FLOT depth on a coastline/river front).

Mark each row's **Status** as you go. A cluster of **☑ VERIFIED** Lua-free Python
rows (B, C, D, E) then becomes the upstream-PR carve-out batch.

---

## How this feeds the other threads

- A row that reaches **✗ REGRESSED** is a concrete bug to fix.
- A cluster of **☑ VERIFIED** Lua-free Python rows (B, C, D, E) are the
  upstream-PR candidates — verify in-game, then carve them out (see the
  upstreaming inventory).


### B45 — GPS jamming (satellite-guided weapons go long) · §86 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **armed once, never exercised, and the runtime is silent when it works.** The plugin armed on Vectron's Claw (tests 1 and 2, 2 sites) and Caucasus 2026 (test 31, BUTTERFLY: two `GPS_Spoofer_Red` and a Tunguska); no blue GPS-guided weapon was released in any of the three recordings. The plugin logs its arming and nothing on a degraded weapon, so even a JDAM that went long would leave no line; add one before the next attempt or the flight can only be judged off Tacview impact points.

**History:** built 2026-08-04

**Setup:** Operation Baltic Fury preseeds this — two jamming sites at `GPSJAM-1` (Copenhagen
approach, ~5 km from Kastrup) and `GPSJAM-2` (Rostock). `gps_jamming` ON (RetLab Features →
Electronic & command warfare); the `gpsjamming` plugin has no checkbox since 2026-10-15.
Fly a strike with
JDAMs at a target within **15 nm** of a site.

Note the bubble is a denied **target** area, not a denied release area: a weapon aimed at
anything inside it flies through it whatever range you released from, so do NOT expect standing
off to help. Laser/TV delivery and killing the jammer are the counters.

**Pass criterion:** the JDAM releases, flies its whole normal profile, and detonates ~200 m off
the aimpoint instead of on it — and the target survives. The firing flight gets ONE
"GPS DENIED" cue on its first spoofed weapon. A laser weapon (GBU-12) dropped on the same pass
hits normally. After killing the jammer, the very next JDAM hits normally — in the same
mission. The kneeboard's `GPS` line appears only once recon has identified the site.

**Fail signatures to watch for:**
- **A bomb that detonates ON target AND produces a second explosion off it** — the predictive
  terminal gate lost the race against a real JDAM's terminal profile (the top risk; the harness
  flies a constant-rate descent, DCS does not). Raise `terminalAglFt` or shorten the script's `TRACK_STEP`.
- **Nothing happens at all** — check the plugin is enabled and that a live jammer is actually
  in the mission (`DCSRetribution|GPSJamming: armed` vs `inert` in dcs.log).
- **A laser, TV, IR or anti-radiation weapon missing** — the pattern list leaked; this is the
  one that turns the feature into a bug report.
- The weapon **visibly vanishing** rather than reading as a bomb that went long (a
  `Weapon:destroy()` legibility problem, not a logic one).
- Your OWN side's weapons being degraded by your OWN jammer.
- The cue firing once per bomb instead of once per flight.
- An un-scouted jammer appearing on the kneeboard (a recon-fog leak).

**Second half of the pass — the site is a STRIKE target, not a SEAD target.** The jammer emits
nothing an RWR or ARM can see, by design (a real GPS jammer is L-band). Confirm:
- The site does **not** appear on your RWR and a HARM will **not** lock it. That is correct.
- You find it by **recon** — it surfaces as a §3 contact, and the kneeboard briefs the area once
  scouted — and kill it with bombs.
- **Killing the jammer trucks restores accuracy** on the very next GPS weapon.
- Every campaign that does not pin a jamming preset still generates its ordinary sites unchanged.


### B54 — Planner behavior bar switches the suite in the settings UI · re-convergence · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side; no capture can show the settings page.** Unchanged, on the WATCH card.

**History:** built 2026-08-09, app pass not flight.
**2026-08-20 app pass: FAILED, root-caused and fixed the same day.** The bar never
rendered. `QSettingsWindow` prepends it only when the page name equals
`CAMPAIGN_DOCTRINE_PAGE` ("Campaign Doctrine"), and `Settings.pages()` never yields
that name -- the dialog's eight pages are Difficulty & Realism, Air Doctrine, Campaign
Management, Mission Generation, Kneeboards, Vietnam Ops, Performance and RetLab
Features. No error: the branch simply never fired and `planner_suite_bar` stayed None,
guarded everywhere it is read. The bar is now bound to `PLANNER_SUITE_PAGE` on the
**RetLab Features** page, which holds five of the eight fields it switches, and
`test_plannersuite` pins both preset bars against `Settings.pages()`. **Retest on
RetLab Features, not Air Doctrine.**

> First slice of the 2026-08-09 re-convergence decision (see the divergence audit's DECIDED
> block): the eight planner gates ship at stock/upstream values, and a **Planner behavior** bar
> atop the Campaign Doctrine settings page applies "Stock (upstream)" / "RetLab suite" in one
> click (`game/settings/plannersuite.py`; bar in `qt_ui/windows/settings/QSettingsWindow.py`,
> which CI does not type-check). Apply/detect and the stock-defaults contract are pinned in
> `tests/settings/test_plannersuite.py`; the Qt wiring is not.

App pass, no flight needed: open Settings → Campaign Doctrine in a game.

- **Pass:** the bar shows "Current: Stock (upstream)" on a fresh game; clicking "RetLab suite"
  updates the eight controls below (overlap 15, jammers 4, the six checkboxes on) and the label
  reads "Current: RetLab suite"; clicking "Stock (upstream)" restores them; hand-changing one
  control flips the label to "Current: Custom".
- **Fail signatures:**
  1. **The bar is missing** — the `CAMPAIGN_DOCTRINE_PAGE` attach branch never matched the page
     name.
  2. **Clicking a button changes the label but not the controls below** —
     `update_from_settings` is not refreshing the auto-generated page.
  3. **A fresh game shows "Custom"** — a Settings default drifted from
     `PLANNER_SUITE_VALUES`' stock column (the `test_fresh_settings_are_stock` guard should
     have caught it first).

### B61 — Task-role degrade: mismatched-role AI flights still fly their mission · §8 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from a capture** (the degrade warning is in the app log, which no test folder holds). Unchanged.

**History:** built 2026-08-16, session `c86c58dd`.

> `configure_task` no longer raises when an AI flight's tasking maps to a pydcs task the
> airframe doesn't export — it degrades the DCS group *role* to the airframe's
> `task_default` and generates (a Tu-160 DEAD flies as role "Pinpoint Strike"). The
> fleet audit found 21 such (airframe, task) pairs across 13 airframes, all upstream or
> mod-registration data; before the fix any one of them auto-planned killed the whole
> mission generation (reproduced on Mozdok-to-Maykop: blue's auto-ATO handed a Tu-160
> squadron DEAD). The degrade + Tu-160 pin are locked by
> `tests/test_aircraft_task_generation.py`; what CI can't see is whether DCS's AI
> executes the waypoint attack normally under the mismatched role.

Needs a watch (no flight): any mission where a degraded flight generates — the Mozdok
light rig injects a Tu-160 DEAD pair ("Iron Hand") deliberately. Watch it run its target
leg in Tacview/F10.

- **Pass:** the degraded flight taxis, cruises its route, and executes its attack tasking
  at the target waypoint (weapons employed or an attack profile flown against the
  objective); dcs.log/generation log shows the "Flying the … tasking with group role"
  warning, no generation error.
- **Fail signatures:**
  1. **Generation still crashes** — a task claim outside the mapped set (extend the lock
     test's `TASK_MAPPING`).
  2. **The flight spawns but never attacks** — orbits or overflies the target with weapons
     retained: DCS's role gating is stronger than assumed for that role pair; record which
     (role, tasking) pair failed and consider a curated fallback for it in
     `configure_task` instead of `task_default`.
  3. **The flight attacks the wrong class of target** (e.g. a Reconnaissance-role OH-6
     strafing armor it was never tasked against) — role-default AI behavior leaking past
     the waypoint tasking.


### B65 — Reinforcement follows the supply lines · §90 rung A · ◐ PARTIAL

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **not reached.** Red took FOB Leimbach by air assault and blue took FOB Delaram II, but no base was cut off: the turn-2 save reads every base on both sides SUPPLIED.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** the multi-turn half needs the app, and no capture is a second turn of the same road cut.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **the tiering does bite in a real campaign.** With
`supply_gated_reinforcement` on, blue's Kutaisi reads **AIRLIFTED** while Batumi, Kobuleti, Turkey
and the carrier all read SUPPLIED, and every red base reads SUPPLIED. That answers the row's first
fail signature — "everything reads SUPPLIED because a road route survives everywhere in practice"
— in the negative, on a shipped campaign nobody authored for this. The multi-turn half (cut the
road, watch strength stop climbing, retake it and watch recovery resume) still needs two or three
turns.

**History:** built 2026-08-17, session `629c250f`.

> The per-turn base strength top-up used to apply unconditionally. It now scales by the
> kind of route back to a rear area: road or shipping recovers in full, airfield-only at a
> quarter, cut off at nothing. `tests/theater/test_supply_status.py` locks the tiering, the
> airlift-backfill trap and the no-rear-area guard. What CI cannot see is whether a real
> campaign's topology actually produces the three tiers, or whether every base always reads
> SUPPLIED because a road route survives everywhere in practice.

Needs a campaign, not a flight. Any front-line campaign with a capturable CP between a
front base and the rear — Red Tide's Fulda corridor is the reference.

- **Pass:** cut the road (let red take the intervening CP), pass a turn, and the isolated
  base's strength does not climb. Retake it and recovery resumes at full rate. The
  front-line position responds over two or three turns.
- **Fail signatures:**
  1. **Nothing ever changes** — every base reads SUPPLIED because the transit network keeps
     a road link the capture should have removed. Check `Coalition.end_turn` ran before the
     gate; log `supply_statuses()` for the coalition.
  2. **Everything reads ISOLATED** — the no-rear-area guard is not firing, or
     `has_active_frontline` is true for bases that should be rear. Campaigns with a small
     CP count are the risk case.
  3. **Blue never recovers at all and stalls out** — 0.25 for the airlift tier is too harsh
     for a campaign that genuinely depends on air resupply. Tune the multiplier, do not
     disable the gate.

---

### B66 — Attacking costs more than defending · §90 rung B · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from a capture.** Unchanged.

**History:** built 2026-08-17, session `629c250f`.

> The battle result was a straight swap. An attacking winner now banks 60% of what the
> loser gives up; a defending winner banks the lot. `tests/sim/test_assault_cost.py` locks
> the arithmetic and the stance set. What CI cannot see is whether the resulting fronts
> feel like fronts.

Needs three or four turns of a ground campaign with the stance left on aggressive.

- **Pass:** a front pushed on repeatedly moves, but each push costs the attacker ground it
  cannot immediately re-spend. A front left defensive holds. Over several turns the line
  does not slide back and forth across the same ground.
- **Fail signatures:**
  1. **Fronts stop moving entirely** — 0.4 is too steep; attacks never accumulate. Lower
     `ASSAULT_COST_FRACTION`.
  2. **No visible difference from before** — check the stance actually reaching
     `apply_battle_result`; a campaign with `automate_front_line_stance` on may never pick
     an offensive stance.
  3. **Red gains ground it should not** — the red-side branch reads
     `enemy_cp.stances.get(cp.id)`, which defaults to DEFENSIVE. If red's stances are
     unpopulated, red is never charged the assault cost and blue always is.

---

---

---

---



> **VERIFIED 2026-08-18** from test 8 (Caucasus, `retribution_nextturn.miz`), measured off
> the generated mission rather than by eye. The drawn front line is a **7-point polyline**
> bowing **1.64 km off a 27.3 km chord** (6.0%); signed profile in km is
> `0.0, -0.82, -1.42, -1.64, +0.49, -0.09, 0.0`, i.e. an S-bend, not a smooth arc. FLOT
> ground units follow it: median **2.98 km from the drawn line against 3.90 km from the
> straight chord**.
>
> **Read the unit measurement per group kind or it inverts.** Across all 127 front-line
> units the numbers say the opposite (3.08 km from the drawn line, 2.80 km from the chord)
> because 107 of them are §9 TIC units, which are placed in depth on both sides and are not
> meant to sit on the line at all. Only the 13 `unit|` FLOT groups are what this row is
> about. Anyone re-measuring this must split by group-name prefix first.
>
> Caveats kept deliberately: 13 FLOT units is a small sample, and the residual ~3 km is the
> intended lateral spread, not error.
>
> Same mission, **B67 is consistent but NOT proven**: the front-line centre sits 108.9 km
> from Anapa-Vityazevo and 107.6 km from Maykop-Khanskaya — the 50% midpoint — with 62 blue
> against 65 red ground units committed. An even fight at the midpoint is the designed null
> result, so nothing is misbehaving, but an even fight cannot demonstrate the armour
> weighting. That row needs a lopsided pair.
### B80 — String plugin options can actually be edited · §14 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side.** Unchanged.

**History:** built 2026-08-18. An app check, not a flight.

> The plugin settings page chose its widget from the option's declared default type and
> handled bool and int/float only, so all seven string options the fork ships rendered a
> label beside an empty cell — visible in the page, and impossible to change. A `choices`
> list now renders a dropdown; without one the option gets a free-text field, which is what
> a comma-separated weapon-pattern list needs. A shipped default outside its own `choices`
> is rejected at load, and a tree sweep pins that no plugin can ship a bad pair.

Open **Settings → Plugins** and find the five plugins with string options: `briefing`
(ground frequency), `minefields`, `navalmagazines`, `vietnamops` (two pattern lists plus the
FAC type) and `redscramble` (spawn mode).

**2026-08-20 app pass, partial:** `vietnamops`' two options render as editable text fields
carrying their defaults, so the empty-cell bug is cleared there. The other five are still
unchecked. Same day, on the DM's call, the FAC(A) aircraft became a **dropdown** — an
exact DCS type name is not something to retype, and a typo silently meant no FAC.

- **Pass:** every string option has a control beside its label. Two are dropdowns:
  `redscramble`'s spawn mode offers exactly air / hot / runway, and `vietnamops`' FAC(A)
  aircraft offers `Bronco-OV-10A` and `vwv_o-1`. The remaining five are text fields
  carrying their current value. An edit survives closing and reopening the dialog, and
  reaches the generated mission's Lua config table.
- **Fail signatures:**
  1. **Still an empty cell.** The option's `defaultValue` is not a string in `plugin.json` —
     check the type, not the widget.
  2. **The dropdown is empty or missing a mode.** `choices` did not parse; the option falls
     back to free text, so the value is still reachable.
  3. **An edit does not reach the mission.** The widget writes through `option.set_value`
     like every other control; if only string options fail to persist, look at
     `PluginSettings`, not at this branch.
  4. **New Game aborts on a plugin load error.** The new guard fires when a shipped
     `defaultValue` is outside its `choices`. That is the guard working — fix the json.

### G42 — Skynet is the engine again · Skynet return · ◐ PARTIAL

**2026-10-18, test 62** (Syria — Anatolian Reach turn 2, Brady in SLOTH Strike (F/A-18C), 42 min, `Tacview-20261018-180758`, main `0507d6680`, `Desktop\New test\62`) — **no change to the HARM clause.** Both IADS built, with no Skynet error in 42 min. Blue fired no HARM.

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **no crash, and the one HARM case was a site that defends itself.** 89 minutes, no Skynet error, the two unhandled SHORAD groups logged (`TORTOISE`, `PRONGHORN`). Of four HARMs, one went at a Skynet site (TURKEY, HQ-7), which stays live by design because it can engage a HARM itself. Dark-on-ingress needs an RWR read; the recording carries no emission state.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the network fought as one.** Red and blue IADS built (`creating red IADS` / `creating blue IADS`, the E-3A added to blue); two SHORAD groups Skynet cannot handle were logged and left standalone (`0060 | TORTOISE`, `0066 | PRONGHORN`). No Skynet error in 89 minutes with 56 crashes. Engagement shape: the S-350 opened at t=1728 and fired 36 rounds; SABERTOOTH 16 Buk-M3 rounds.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`; corrected 2026-09-22 from full-resolution tracks) — **consistent with the HARM defence, not proof of it.** The SA-11 `MAVERICK` fired its last missile at t=2470; four HARMs launched at it t=2419–2437 fell 2.2–2.4 km off the site 90 s later. A site that goes dark on HARM detection produces exactly that miss, but the recording carries no emission state, so it cannot be told apart from the HARMs losing the radar for another reason.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **three of the four pass clauses seen; the HARM clause was measured and did not happen.** Loads and runs to full length with no `enableEmission` fault on tests 30, 32 and 33 (25 min, 2 h 14 min, 93 min). Sites dark until cued (KIWI's SA-11 held fire until the DEAD four-ship was inside 30 km). Unhandled sites named (OKAPI, WATERBUCK). The one site that took HARMs, LEOPARD (SA-11, test 32), did **not** go dark: WEKA fired two AGM-88 at t=4157 and t=4165, LEOPARD launched at t=4165, 4170, 4177 and 4197 while the HARMs were in the air, lost two launchers at t=4250 and t=4256, and launched again at t=4294 and t=4305. Skynet's HARM defence is a per-site detection roll, so one site is not a verdict, but on the only measurable case the site fought through the shot rather than shutting down. Recorded, not tuned; the HARM clause stays open.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — 93 min, no crash, no `enableEmission` fault. One rejection: `0092 | WATERBUCK (PD)` is a point-defence group Skynet cannot classify; its parent SA-10 was still fragged and the turn-3 auto-planner still targets it.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — **ran the full 2 h 14 min, no crash, no `enableEmission` fault; two findings.** Both nets built, and the test-30 flat-top EWR rejection did not recur. **(1) A mauled site comes back outside the net.** `0002 | OKAPI (SAM)` was rejected as a site Skynet cannot handle: it is an SA-11 site regenerated as four launchers after losing its search radar and command post on turn 1, so `setupElements` finds no search radar, it is cleaned up, and it fights as plain DCS AI, radiating from T0. Its eight launches killed three Al Minhad BARCAP Tomcats 60–64 km from the nearest intact site. Any radar SAM that loses its search radar will come back this way. **(2) The sites-dark half works, and it costs AI DEAD flights their shots.** KIWI DEAD (four F-16CM with AGM-88C and AGM-65G) flew at a Skynet-held SA-11 that stayed dark until they were inside 30 km; it then fired ten, the Vipers fired nothing, and all four plus the Mirage escort were lost. WEKA DEAD, same fit, flew at LEOPARD, an SA-11 that had already lit up to shoot the SEAD escort Hornets ahead of it; the Vipers put eight HARMs on it, killed two launchers, and came home. DCS AI only shoots a HARM at an emitter, and a Skynet site emits only once its target is inside the envelope, so an AI DEAD flight against a disciplined site never gets a shot off. Whether that is the accepted trade of the return, a `goLiveRange` setting, or a planner rule (no AI DEAD against a Skynet-held site without something lighting it first) is a DM call.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, the first flight on the Skynet
return, build `78085dfd7`) — **loads and runs; one name defect.** Skynet `baron-branch
16.05.2023` started, built both nets, took the Kish A-50 as an early-warning radar, and no
`enableEmission` fault appears in 25 wall-minutes. The blue net's EWR list names both
flat-tops and Skynet rejected them: `SKYNET: you have added an EW Radar that does not exist
... 0156 | CVN-71 Theodore Roosevelt` and `0159 | LHA-1 Tarawa`. The unit in the `.miz` is
`CVN-71 Theodore Roosevelt` in group `0156 | GIBBON (Carrier)`, so the emitted name matches
neither. Ship radars never join the blue net until the IADS node's name for a ship is the unit
name. Not the crash class this row guards against; the sites-dark and HARM halves were not
exercised (no SEAD flown, no player).

**Built 2026-09-12** (`retlab-skynet-return-notes.md`). The MANTIS bridge and the MIST shim are
gone; upstream's Skynet and MIST are back, with the HDSUC profiles from #956 and the CurrentHill
profiles from HFXLegion's fork compiled in.
- **What CI cannot exercise:** the engine itself. The harness pins only the bridge's two
  additions (dead C2 stand-ins, the deferred AWACS add).
- **Setup:** any campaign with a red radar-SAM belt and an EWR (Red Tide is the reference).
  Watch `dcs.log` for `Skynet-IADS plugin - creating red IADS` and the per-site `ADDED:` lines.
- **Pass:** red SAM radars are dark on ingress and come up when an EWR or AWACS has you;
  a HARM shot makes the targeted site go dark; a site with a profile in the database engages
  (an `SAM site that Skynet IADS can not handle` line names one that does not); the mission
  runs its full length with no crash.
- **Fail signature:** every red radar radiating from T0 (the bridge did not run, or
  `createRedIADS` is off); a DCS crash-to-desktop in a mission with a busy IADS (the
  `enableEmission` concern from the C-130 line — record the log and stop, do not tune around it);
  a modded site named as unhandled (add its profile to the compiled build).

### G41 — A bombed power station keeps its SAMs down on the NEXT turn · Skynet bridge, DeadC2 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised, and the row's log lines are MANTIS's.** No save on the machine carries a dead command centre, comms node or power station (`dead_c2_names` is empty on `91526`, `CSAR`, `Maybe 414`, `test 1` and the three August saves; the only damaged node anywhere is the ARGALI EWR in the Vectron's Claw turn-3 save, 3 of 5 units dead), so the next-turn half has never had a turn to run on. The `MANTIS C2 - power '<name>' lost` line in the pass criterion no longer exists; the runtime half now announces itself as `DCSRetribution|Skynet-IADS plugin - <name> is destroyed; registering a dead stand-in` at mission start, and the `DeadC2` array is what `luagenerator.py` emits from `dead_c2_names`. Read those two, not the MANTIS line, when a strike on a C2 node finally lands.

> **Re-pointed 2026-09-12.** The Python fix (dead C2 nodes stay in the graph) is unchanged. The
> runtime half is now the Skynet bridge's dead stand-in (`retlab-skynet-return-notes.md` §5,
> harness-pinned in `tests/lua/test_skynet_bridge.py`). Same pass criterion.

**History:** built 2026-08-19. The C2 layer worked for exactly one mission and nobody
noticed, because the mission it worked on is the one you fly right after the strike.

> `IadsNetwork.iads_nodes` dropped any node or connection whose units were all dead, so from
> the turn *after* a comms mast or power station died the dependency was absent from the
> exported graph and `setup_c2` had nothing to watch. The SAMs behind it came back fully
> operational. Worse for command centres: kill them all and `#cc_names == 0` trips the
> empty-graph early return, so the coalition gets perfect command back instead of being
> decapitated — while §52 kept reporting degraded enemy C2 on the campaign side.

- **What CI cannot exercise:** whether MANTIS actually re-applies the degradation on a later
  turn. The graph contents and the `DeadC2` list are unit-tested; the runtime behaviour is not.
- **Setup:** an `advanced_iads` campaign (Red Tide is the reference). Find a red power station
  feeding several SAM sites — the IADS link layer draws it. Strike it, finish the mission, pass
  the turn, then fly **the next** turn against the same SAMs.
- **Pass:** on the following mission the dependent SAMs are still offline. `dcs.log` carries
  `MANTIS C2 - power '<name>' lost; N SAM(s) offline` on that turn too, not only the turn of
  the strike.
- **Fail signatures:**
  1. **The log line appears on the strike turn and never again**, and the SAMs engage normally
     next mission — the graph is dropping the node again.
  2. **No log line at all on either turn** — check the node is a real IADS `PowerSource` and
     the campaign is on advanced IADS; this is the pre-existing C2 wiring, not the fix.
  3. **A scenery C2 node never reads dead.** The `DeadC2` array is the path for those (a
     scenery object has no static to look up); check it is present in the generated
     `dcsRetribution.IADS.RED` table.
  4. **Every SAM in the coalition goes autonomous at mission start.** The decapitation branch
     fired when it should not — the command-centre list is being mis-read as all-dead.

### B85 — A flight with an unreachable TOT flies instead of orbiting · §8 · ◐ PARTIAL

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **not exercised.** No negative `stopCondition.time` in the `.miz`. PORCUPINE's flights departed at mission start (`departing in 0:00:00`) and still reached the S-350 96 s before their TOT, so no TOT was unreachable.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** tests 26–33 carry no negative `stopCondition.time` either (the miz scan), the in-game release still unobserved.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **the `.miz` check this row names comes back clean.** The
generated mission carries 50 `stopCondition.time` values, minimum 0.0, maximum 9361.0, and
**none negative** — the exact artefact the row says to look for. The in-game half (a held flight
actually releasing and flying) was not observed, so this stays PARTIAL rather than closing.

**History:** built 2026-08-19 from juanjux/dcs-retribution#100. His repro was a DEAD package
given a TOT 5 minutes out from a base 29 minutes away; the mission shipped
`stopCondition.time = -865` on four aircraft that then achieved nothing.

- **What CI cannot exercise:** that DCS releases the hold. The clamp is unit-tested; the
  in-game release is not.
- **Setup:** frag a package at a target far enough away that its TOT cannot be made — the
  planner warns about past start times when you have it. Fly the turn.
- **Pass:** the flight leaves its hold and flies the mission. It will be late; that is expected.
- **Fail signature:** the flight orbits the hold point for the whole mission. Check the
  generated `.miz` for any negative `stopCondition.time` — there should be none.

### B71 — Several survivors come out on one lift · CSAR (#929 Phase 5) · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** Clustered ejections happened (test 32's F-14B crew, test 33's Damascus pair) but the next turns' packages were not captured. Unchanged.

**History:** adopted 2026-08-17 from upstream `82b3ab10`. Never flown.
- **What it is:** survivors within `csar_cluster_radius` (default 1000 m) are collected by one rescue flight instead of one flight each. The planner takes the whole cluster off the board when it frags the package, the survivors' embark zone stretches to reach the furthest member, and OpsCSAR.lua rebuilds the cluster at runtime so a mate who was already killed or collected is not credited.
- **What CI cannot exercise:** whether the other survivors actually *walk* to the landing zone. The stretched `EmbarkToTransport` radius is the only thing making them move, and DCS infantry pathing over 1 km of broken ground is not something a unit test can speak to. The hoist half has the opposite risk: it credits the whole cluster on one winch cycle regardless of where they are standing.
- **Setup:** set `csar_ejection_chance` to 100. Get two or three aircraft killed within ~500 m of each other behind the lines — a flight caught by the same SAM is the natural way. Pass the turn and confirm **one** CSAR package is fragged, not three. Fly or watch the pickup. Run it twice: once with `csar_hover_extraction` OFF (landing) and once ON (hoist). ~40 min.
- **Pass:** one package. On landing, every survivor in the cluster boards and all of them are credited at the debrief. On the hoist, all of them are credited and their groups are removed from the map.
- **Fail signature:** a package per survivor, which means the planner is not clustering. Or one pilot recovered and the rest still standing on the map at mission end — the embark radius did not stretch, or they could not path to the LZ. Or the reverse on the hoist: pilots credited as rescued while their groups are still visibly on the ground 900 m away, which is the cluster being trusted rather than checked.

### B73 — Taking a base frees the prisoners held there · CSAR (#929 Phase 5) · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** No capture spans a base capture with a prisoner held there. Unchanged.

**History:** adopted 2026-08-17 from upstream `82b3ab10`. Never flown.
- **What it is:** a captured pilot is held at a specific control point (`Pilot.held_at`, persisted). Capturing that base releases them into recovery and back to their squadron. Losing a base does not free anyone, and a base taken by the side already holding the prisoners changes nothing.
- **What CI cannot exercise:** the interaction with a real base capture in a real campaign, across a save/load. `held_at` is a new persisted field on `Pilot`; old saves default it to `None`, which means pilots captured before this change stay missing forever with no base to take. That is correct but worth seeing.
- **Setup:** get a pilot captured (B72's enemy-side case is the fastest route — eject near an enemy field). Note which base holds them. Save, reload, and confirm they are still held there. Then take that base. ~45 min, mostly the ground campaign.
- **Pass:** the "Prisoner of war freed" message names the pilot and the base, and they return to their squadron after the recovery turns.
- **Fail signature:** the base changes hands and nothing happens — check `held_at` survived the save. Or prisoners freed by the *wrong* capture, e.g. losing a base releasing the enemy's prisoners held in it.

---

### B96 — Iron Gate's fields fill without an aircraft losing its stand · Iron Gate · ◐ PARTIAL

**2026-09-16, test 34** (Caucasus — 1968 Yankee Station turn 1 on the halved laydown, 62 min, no player, `Tacview-20260916-204511`, DCS 2.9.29.27468) — **one more Iron Gate data point, and it is L8's.** Test 24's two Batumi F-15C BARCAPs (activated t=1080 and 1136) never moved, and Batumi was one of the five fields the artillery harassment armed for that mission. Not a stand problem; see L8.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** Iron Gate turn 2 (test 26, 09-07) generated clean with no parking line at all, and the Mineralnye Vody spawner from test 24 did not recur.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, 72 min, `Tacview-20260829-162330`, DCS 2.9.29.27278) — **Batumi answered, and a red field failed instead.** Batumi, the
field this row said to look at first, generated with **9 F-15C on 10 stands** and fits. But
`Mineralnye Vody: No parking place for 'Su-24M'` appears **4 times** in the log — that base is
authored at **28 aircraft on 28 stands**, zero slack, and four more Su-24M were sent to it than it
can hold — but at t+57 min, not at load, and the field has no Su-24M squadron. See **B100**: this
is a runtime spawner, not the parking rework, and generation itself was clean.

**VERIFIED 2026-08-23** (`Tacview-20260823-181233`, 62 min of sim, 1,091 units, 238
aircraft, `autosave.retribution` now on turn 2).

No field exceeded its stands and every aircraft got a slot. The Turkey off-map spawn
produced air-started KC-135s, both FOBs parked their Hind squadron on pads, and the
Hercules sat on one of Kutaisi's large stands. The nested-stand arithmetic held against a
real mission.

**The laydown changed after this flight (2026-08-23, DM call) and one field in it is
unflown.** Batumi came back as a third blue field, the Warthogs moved Kutaisi -> Kobuleti and
the Eagles Kobuleti -> Batumi. Kutaisi and Kobuleti were both flown at equal or greater
occupancy than they now carry, so this row stands for them. **Batumi has never been
generated** — ten stands, ten F-15Cs, zero slack, which is the tightest field in the campaign.
`test_iron_gate.py` proves the arithmetic; only a generated turn proves the stands. Look at
Batumi first on the next pass.

**A false alarm worth recording, because the next reader will hit it too.** Red appears to
fly 5 sorties out of 159 aircraft, and `CRANE DEAD` (Su-24M, Mozdok) records a track span of
**0.0 NM** across 30–3750 s. Neither means what it looks like:

- **~150 of those aircraft were never tasked.** Red's ATO was **8 flights**. The rest is
  squadron inventory parked on the ramp — expected, and the reason `sortie_records` shows 183
  entries when only 30 aircraft moved (see B70).
- **`CRANE DEAD` activated at 3629 s into a mission that ended at 3750 s.** Two minutes to
  start engines and taxi. Its 30–3750 s "seen" window is the recorder watching the group
  object, not the aircraft being airborne.

Seven of red's eight flights activated inside the window and four flew. **Ramp occupancy was
not implicated** — an earlier reading of this data that blamed 90 %-full ramps for blocking
taxi was wrong, and the 62 %/73 % "break" was an artifact of which fields happened to hold
the early-activating flights.

**The long ATO is settled: one setting, and it is measured.** Blue's activations ran out to
**13,517 s** against ~62 min flown, so 8 of blue's 37 and 1 of red's 8 never fired. A fleet
control point **doubles** the BARCAP round count, and `max_carrier_simultaneous_barcaps` is
what turns the extra rounds into pairs on station rather than waves in sequence — at **1** it
never stacks, so each wave advances the handover instead of joining it.

Re-planning blue on `Maybe 414.retribution` (turn 1, 100-min mission, overlap 0, 19 packages)
at each value:

| value | carrier BARCAPs | last TOT | past the mission |
|---|---|---|---|
| **1** (that save) | 4 singles at 4/64/124/184 min | 184 min | **3 of 19** |
| **2** (default) | two pairs at 3/4/64/64 min | **95 min** | **0 of 19** |
| 3 | 3/3/4/64 min | 102 min | 1 of 19 |

Every non-carrier package finishes by 95 min at any value, so this setting is the whole
effect. Overlap multiplies it when non-zero — the flown mission ran 15 min, which is why its
ATO reached 225 rather than 184 — but is not the cause. Nothing to fix in the campaign; the
two setting descriptions that hid this are fixed in this branch.

**History:** the campaign is new; see
[retlab-iron-gate-campaign-notes.md](design/retlab-iron-gate-campaign-notes.md).

> DCS stands are nested — one that takes a Hind also takes a Huey, not the reverse — so a
> base's slot count is not the binding constraint. Sizing against it overfills the big
> stands silently. It bit four times during the build, including 28 helicopters into
> Kutaisi's 25 helicopter-capable spots.

**What CI cannot exercise:** the numbers are arithmetic over pydcs stand data, which models
DCS rather than being it. Whether every aircraft actually gets a stand is a
mission-generation question.

- **Setup:** New Game on **Caucasus - Iron Gate**, generate turn 1, open the .miz in the
  Mission Editor. Check Kutaisi, Kobuleti, Beslan and Tbilisi-Lochini, then **both red FOBs** —
  Nigniy Pasanauri and Khashuri each base a four-ship Hind squadron, the only place the
  campaign puts a squadron on helicopter pads rather than an airfield.
- **Pass:** every squadron has its aircraft on a stand, nothing on a taxiway or overlapping;
  the Hercules at Kutaisi is on a large stand; the tankers and E-3A start **airborne** out of
  the Turkey spawn rather than on a ramp anywhere.
- **Fail signature:** a squadron shows fewer aircraft than its `size:`, or DCS logs a parking
  error. Report which airframe and which field — the fix is per stand class, not a blanket trim.
- **Free while you are there:** blue has **36** land-based fighters at Kobuleti. Worth a note on whether
  that is enough to contest the pass, and whether Kobuleti's transit leaves useful fuel.
### B94 — Editing a faction mid-campaign reaches the buy menus · juanjux #953 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side.** Unchanged.

**History:** ported 2026-08-23 from juanjux's upstream #953, after verifying all three
defects live here. See [retlab-juanjux-fork-watch-notes.md](design/retlab-juanjux-fork-watch-notes.md).

> `ArmedForces` is built from the faction once, in `Coalition.__init__`, so a mid-campaign
> faction edit was invisible to everything downstream. The rebuild hung off a signal only
> preset-group adds emitted. Adding a unit now rebuilds too, entries get a working remove
> button gated on an `in_use` check, and both lists sort by the displayed name.

**What CI cannot exercise:** upstream's test covers the rebuild, not the dialog. The unknowns
are whether the rebuilt `ArmedForces` is what the purchase menu actually reads mid-campaign,
and whether the `in_use` refusal catches a unit that is deployed but flown by no squadron.

- **Setup:** load a save mid-campaign, Air Wing → Faction OPFOR. Add an early-warning radar
  the faction lacks, close, then open the ground-unit purchase menu at a red base.
- **Pass:** the new radar is offered. Then reopen the tab, press ✕ on a unit type nothing
  fields — it disappears; press ✕ on one a squadron flies — a popup names the squadrons and
  refuses.
- **Fail signature:** the added unit never appears in the buy list (the rebuild did not reach
  the menu's model); or ✕ removes something the map still has deployed, leaving the game
  holding materiel its faction no longer admits.
- **Free while you are there:** the aircraft/unit/ship/preset combo boxes should read
  alphabetically. They used to be ordered by internal DCS id.
### B95 — Saving the air wing keeps both coalitions · air wing config · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **app-side.** Unchanged.

**History:** reported by the DM 2026-08-23, with the file it happened to — `Northen
russia.yaml` held the blue wing, a Red-tab save replaced it, and there was nothing in
the file to say either version was one side of a pair.

> `_build_air_wing` read `self.tab_widget.currentWidget()`, so Save wrote only the tab
> in front and Load applied a file to whichever tab was in front. Save now writes both
> coalitions under `coalitions:`; a file holding both asks on load whether to restore
> both or only the open side. Files without that key are legacy and still load into the
> current tab. `tests/retlab/test_air_wing_file_format.py` pins the detection both
> ways, including a control point named `coalitions`.

**What CI cannot exercise** is the dialog itself: the tests cover format detection, not
whether `configure_default_air_wing` applied to a tab that is *not* in front redraws that
tab and survives Accept Changes. A squadron restored into the background tab could look
right in the file and never reach the game.

- **Setup:** New Game, open Air Wing Configuration, change something on Blue **and**
  something on Red, Save Config. Reopen, change both again, Load Config, choose **Both**.
- **Pass:** both tabs show what was saved, Accept Changes sticks, and the first mission
  generates with those squadrons. Then repeat choosing **<side> only** and confirm the
  other tab is untouched.
- **Fail signature:** the background tab still shows the old wing after a Both load (the
  `w.revert()` did not reach it); or Accept Changes drops the background tab's squadrons.
- **Legacy check, free:** load one of the DM's existing files (`Northen russia red.yaml`,
  no `coalitions:` key) with the Red tab open. It must load exactly as it did before.
### B92 — A rescued marker belongs to the base it sits next to · campaign loading · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not decidable from a capture** (the placement warning is in the app log). The Desert Trident captures (tests 6, 9, 14–16) predate the 08-22 fix. Unchanged.

**History:** built 2026-08-22, from the DM's own `test.retribution` on
`operation_desert_trident` — the placement warning listed seven groups on King
Abdullah II's doorstep.

> A marker outside every influence zone used to fall back to the nearest control
> point **with no zone at all**, so a base whose zone hugs its runway could not
> adopt its own outlying markers. Six armour groups and a fuel depot 15–25 km
> from red King Abdullah II were blue Ben Gurion's, 110–140 km away. A nearby
> zoned base now adopts a stranded marker: within `ADOPT_ZONED_WITHIN` (25 km),
> and only when the fallback would put it past `STRANDED_BEYOND` (50 km).
> `tests/test_miz_marker_binding.py` pins both bounds, each with a test that
> fails without it.

**Already measured, so do not re-derive it:** across every shipped campaign 16 of
7,653 bindings move, none ends up farther from its owner, and Desert Trident's
warning goes 7 → 0. Eight campaigns move at least one marker: clash_of_the_titans,
crossing_the_rubicon, operation_desert_trident, operation_gazelle,
operation_vectrons_claw, red_sea_rising, red_tide, the_anvil_of_war.

**What CI cannot exercise** is what the rebound objects *do* once they are the
other base's. King Abdullah II goes from 6 ground objects to 13; Ben Gurion drops
26 → 19. That changes who defends them, who is tasked against them, and where the
front line between those bases sits.

Needs a new game on one of the eight, not a flight. Desert Trident is the
reference — it carries 8 of the 16 moves.

- **Pass:** no placement warning on load; the moved groups render in the *near*
  base's colour on the F10 map; the ATO frags against them from the correct side.
- **Fail signatures:**
  1. **The warning still lists them** — the adoption did not fire. Check the two
     bounds against the real distances before touching the rule; a marker 26 km
     out, or one whose old owner was 45 km away, is outside the guard by design.
  2. **A marker moved to a base it is NOT nearest to** — the rule is
     nearest-zoned-only, so this would mean the eligible set is wrong. Stop.
  3. **A campaign that was fine now looks reshuffled** — markers hopping between
     neighbouring fields is the failure `STRANDED_BEYOND` exists to prevent, and
     Marianas (Velvet Thunder) is the campaign that showed it. Re-measure before
     assuming the bound is too loose.

---

### B120 — Neutral border: warned, then the battery engages if you press · §98 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **never exercised.** Across all 30 logs the `neutralborder` plugin printed only its arming line; no hail, no warn, no swap. Players flew on tests 24, 28, 29, 31 and 33 (Iron Gate, Into the Hornet's Nest twice, Caucasus 2026, Peace Spring) and never crossed a shaded border; `engageAi` was off on every mission. This row needs one deliberate crossing by a human, or one AI-only turn with `engageAi` ticked.

**2026-09-15, test 32** — not exercised: no player slot, `engageAi` off.

**2026-09-13, test 30** — not exercised: the mission had no player slot and `engageAi` was
off. The batteries were up for the whole mission (see B121).

**REOPENED 2026-09-07.** This row closed on 2026-09-01 against the standing
fighter patrol, and the patrol was dropped the same week (DM call: scope is the
SAM). None of that evidence transfers — there is no aircraft in the feature any
more.

**What defends now.** Live SAM batteries, neutral and on the map from `t=0`,
sized to the country (SA-3 or Hawk for a small one, S-300 or Patriot for a large
one) and **counted off it too** — roughly one per 200 NM of war-facing frontier,
capped at six, spread along the stretch of border the war is near, each deep
enough that its envelope just reaches the frontier. A single battery covered
3.5 % of Pakistan's border on the Afghanistan map, which is why there are now
several (2026-09-09).

**Setup.** Any campaign with `neutral_border_defense` on.
Into the Hornet's Nest (Lebanon) is the worked case.

**Pass.**

* The battery is **findable before you cross** — it is emitting, so it paints on
  RWR and shows on the F10 map as a neutral ground group. This is the whole
  premise; if there is nothing there until you trip it, the feature failed.
* Cross and you are hailed at once, then warned again at the dwell.
* Stay past the engage timer, or drop something inside the border, and the
  battery **changes coalition and shoots at you**.
* Its envelope actually reaches the border you crossed — you should not be able
  to loiter just inside the frontier untouched.
* **A large country has several, and they are spread out** — on Afghanistan,
  Pakistan should show 5-6 and Uzbekistan 1. Look at the F10 map before you fly.
* **The whole country escalates.** After you are declared hostile, the batteries
  elsewhere along that border are hostile too — fly at a second one and it should
  engage without a fresh warning.

**Fail signatures.**

* Nothing on the map inside a shaded border at mission start.
* The battery swaps and never fires — check it went weapons-free and alarm-red.
* The neutral country's **airbase changes hands** when the battery swaps. Deep
  placement is supposed to prevent that; if it happens, the site was on a field.
* A country smaller than its system's reach (Bahrain, the two Persian Gulf
  slivers) shooting well outside its own border. Known and accepted, but record
  how far.
* **Clutter.** The count was picked off measurement, not off a flight: ~17 sites
  on an Afghanistan campaign, ~68 vehicles. If the RWR or the F10 map reads as an
  authored IADS rather than a border, say so and the spacing goes up.
* Two batteries stacked on top of each other, or one outside the border.

**History:** built 2026-08-24 as a scramble, rebuilt 2026-08-29 as a standing
four-ship patrol, closed 2026-09-01 on test 25 (five patrols, 23 of 24 aircraft
never leaving their airspace, the swap and the SA-6 both proven), and rescoped to
the SAM alone 2026-09-07. Full history in the design note.


### B122 — A survivor lands where his own chute came down, not where another crew's did · CSAR (#929 adoption) · ◐ PARTIAL

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **passes again.** Four ejections. Three chutes landed on land and `state.json` carries each touchdown to the metre against the recording. The fourth was still under canopy when the mission stopped and kept its ejection point, with no `landed` flag.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **both halves hold for every ejection.** 18 `ejection_events`, all `landed`, 0.3–14.7 km from where the aircraft's track ended; one two-seat F-15E among them. In the turn-2 save every survivor from an ejection sits on his landing point (0–750 m). Separate from this row: nine blue survivors had no ejection record and were placed by the survival roll near their package's target, 23–42 km from the nearest loss of their type — see the test 39 summary.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** the per-crew match is still not built and no capture since test 33 exists.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — **19 land ejections all matched, one of them probably to the wrong crew.** Every land ejection got `landed: true` and the recording confirms the touchdowns it covers to the metre (three Abu al-Duhur intercept chutes, the MiG-29 at 9.4 km of drift from 5 km, the civilian crews, the MAVERICK Escort Eagle at 33 m). The `HOSTILE SCRAMBLE MiG-21bis #001-01` record is the exception: its recorded touchdown is 19.4 km from the nearest ejection point of any crew and further from its own, when every measured chute drifted under 10 km. The two §61 MiG-21s and the two HS25 Mirages went down within minutes and within 20 km of each other near Damascus, which is exactly where the nearest-open-ejection rule can wire one crew's landing onto another's record; the recording's bubble did not reach those chutes to prove it. A per-crew match would settle it: DCS's ejection event carries the pilot object as `event.target`, and the landing event's `initiator` is that same object, so keying on its id instead of on distance needs no geometry at all. Not built.

**2026-09-15, test 32** (Persian Gulf — WRL Operation Noisy Cricket Redux turn 2, no player slot, 2 h 14 min of sim at acceleration, `Tacview-20260915-174631`, DCS 2.9.29.27468, build `fd04b4a66`) — **the matcher held on 13 ejections; the two-seater-over-land case did not occur.** One ejection came down on land: the Bandar Abbas F-5E at t≈2996, whose chute the recording tracks from 3,990 m to touchdown at x=−63788 z=−57751, 4,478 m from its ejection point. `state.json` records exactly that touchdown as `landed`, and the next-nearest open ejection was 46 km away. The other 12 (three Iranian intercept pairs, five blue Hornets and Tomcats, the Khasab F-14B crew) went into the water and kept their ejection point, and nothing was written onto another crew's record. The F-14B pair ejected last, over the sea, so the land two-seater case the setup asks for was not produced, and the next-turn map was not checked (the save was not captured). **A shape to know:** MOOSE CSAR spawns the in-mission survivor at the *ejection* point (`csarUsePara` is false), so the F-5E pilot's beacon sat at x=−59382 z=−56953 while the campaign will place him at the touchdown 4.5 km away. A high land ejection drifts that far.

**History:** found 2026-09-13 on test 30 (Persian Gulf — Scenic Route turn 1). `state.json`
recorded AUROCHS DEAD Pilot #4 (AV-8B, down in the Strait of Hormuz at x=−60040 z=159481 per
the CSAR beacon line) as `landed` at x=110389 z=−76 — 170 km away, 200 m from where the
GIBBON Escort F-4E crashed. DCS raises one `S_EVENT_LANDING_AFTER_EJECTION` per crew member;
the handler wrote the Phantom's second landing onto the most recent open ejection, which was
the Harrier's. Upstream #929 (head `12e340f7`) carries the same loop. Fixed the same day: a
landing is matched to the nearest open ejection within 20 km and one that matches nothing is
dropped (`landing_ejection_for` in `dcs_retribution.lua`, pinned by
`tests/lua/test_dcs_retribution_runtime.py`).

- **What CI cannot exercise:** that DCS's landing event arrives one per crew member as the
  harness assumes, and that a chute from a high ejection stays inside 20 km of the ejection
  point.
- **Setup:** a mission where a two-seat aircraft (F-4E, F-14, Su-24) and a single-seat one both
  go down over land, the two-seater last. An AI-only Scenic Route turn reproduces the shape;
  ~1 h at acceleration.
- **Pass:** every `ejection_events` entry's `landed` position is within a few km of its own
  unit's ejection point, and the next turn's map puts each survivor where he came down.
- **Fail signatures:**
  1. **A survivor 100+ km from his aircraft's loss** — the match reached the wrong ejection;
     compare the `state.json` positions with the `_AddBeaconToGroup ... Position` lines in
     `dcs.log`.
  2. **A land ejection with no `landed` at all** — the landing fired more than 20 km from the
     ejection record, or never fired; the survivor stays at the ejection point, which is also
     what a water landing has always done.

### B123 — An Armed Recon flight engages a gun-defended target instead of overflying the search point · §35 · ◐ PARTIAL (2026-09-21, test 37; was ☐ UNTESTED)

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`; corrected 2026-09-22 from full-resolution tracks) — **fail signature 2's outcome, before the zone logic was reached.** `Kharab Ishk Armed Recon` (2× F-15E, 6 GBU-38, TOT 05:46:35Z = t=2609) fired nothing in 33 min airborne and both jets were shot down at t=2449 and t=2458, 2.5 min before TOT, by the SA-11 `0126 | MAVERICK (SAM)`. Its own SEAD escort was two AV-8Bs carrying AGM-122 Sidearm and AGM-65F — no weapon that reaches a Buk — and both were shot down too, with the package's F-14A escort. The row's question (does the flight engage instead of overflying) was not reached; the loss says the package had no suppression that could touch the threat on its route. Recorded under B126.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised since the fix.** Tests 31–33 fragged no Armed Recon flight at all; test 30 is the pre-fix failure. Unchanged.

**History:** found 2026-09-13 on test 30 (Persian Gulf — Scenic Route turn 1). Three Hornet
Armed Recon flights were fragged on the AUROCHS AAA site (KS-19 100 mm, 20 km ring in pydcs).
The standoff rule pushed the fly-over point out to the 10 NM cap, and the 10 NM
`EngageTargetsInZone` centred on that point left the guns 80 m outside the rim. Each flight
flew to the point at 20,000 ft, 14–15 km short of the guns, found nothing in its zone, and
turned for the split: zero shots from twelve Mavericks-armed Hornets. Fixed the same day:
`search_zone_radius` grows the zone to the search point's distance plus 2 NM whenever that
exceeds the doctrine range, so the target always sits inside (`armedrecon.py`,
`armedreconingress.py`; `tests/test_armed_recon_planning.py`).

- **What CI cannot exercise:** that DCS's AI prosecutes a unit that is inside the zone but
  outside the fly-over point's own detection reach, and that the Hornets' Mavericks can be
  employed from the standoff without the flight pressing into the guns.
- **Setup:** frag Armed Recon on an AAA- or SAM-defended site (Scenic Route's AUROCHS, or any
  FOB with a SA-13/KS-19 garrison). Watch the flight from the F10 map. ~40 min at
  acceleration.
- **Pass:** the map's search ring covers the site with margin; the flight closes past the
  fly-over point and employs against units at the site, and the sortie record carries shots.
- **Fail signatures:**
  1. **The flight overflies the point and turns home with nothing fired** — either the zone is
     still short (dump the `.miz` and measure the `EngageTargetsInZone` centre against the site)
     or the AI will not enter the ring for a target it cannot see; in the second case the
     answer is a lower search altitude, not a bigger zone.
  2. **The flight presses into the guns and dies** — the standoff was the point; the zone is now
     wide enough to draw the AI in. Compare losses against the pre-fix 0-shot outcome before
     calling that worse.

### B100 — The ramp still holds the squadrons authored against it · DCS 2026-08-26 parking rework · ◐ PARTIAL

**2026-09-16, test 35** (Syria — Long Road to H3 turn 1, 78 min, no player, `Tacview-20260916-215945`, DCS 2.9.29.27468) — **Al Qusayr launched nothing, and it was not shelled.** Seven red groups (eight Fitters in two anti-ship four-ships, WALLABY's four Fitters, four MiG-21 escort pairs) activated hot between t=93 and t=372 and every one sat to mission end; the field was not on the harassment list (Gaziantep, Aleppo, Tabqa, Kharab Ishk were), no weapon landed within 2.5 km, and the log carries no parking line. The timeline says apron pile-up: WALLABY's four taxied 350–470 m across the north-east apron and stopped at t=175–225, the moment HEDGEHOG's eight Fitters and four Fishbeds activated hot on the same apron (t=171–176); WARTHOG (t=244) and PADDLEFISH (t=372) then joined the jam. Eighteen hot jets from one field inside five minutes is the scheduling shape that produced test 30's Bandar Abbas Fencers and the carrier gridlock in B17, and it is worth its own lever (stagger activations per field) before any stand table is blamed. The second candidate is the §1 collision class: the field's garrison armor group PORPOISE (five T-55, two ZSU-57-2) sits 300 m south of the runway inside the perimeter, at the campaign miz's authored armor marker. Made likelier by the DM's own report from the same mission: Incirlik's EWR group had to be hand-moved before flying because it blocked taxi, and the campaign miz authors that marker 1,437 m down the runway axis, 266 m off the centreline, on the south-west taxiway. Not proven for Al Qusayr, because Tabqa has the same shape (WOLFHOUND, four T-55, 265 m off the runway) and launched five of its seven flights; whether a group 270–300 m off the centreline blocks depends on where that field's taxiway actually runs, which pydcs does not carry. The lever that covers both fields is a generation-time check of every ground object against the runway strip and the parking slots, warning or nudging the layout off them. Tabqa's two that sat, the L-39 Armed Recon pair (t=424) and the second SEAD Sweep Fitter (t=624), each moved about 700 m and stopped; Tabqa was on the harassment list, so those sit under L8's evidence, with the Flogger pair that activated at t=605 and flew as the one counter-example on record.

**2026-09-16, test 34** (Caucasus — 1968 Yankee Station turn 1 on the halved laydown, 62 min, no player, `Tacview-20260916-204511`, DCS 2.9.29.27468) — **the test-30 Fencers are not the harassment case.** Test 30's mission carried no harassment node at all (the only capture with stuck jets that did not), so Bandar Abbas's nine hot jets that never taxied keep their own cause. Everywhere else a stuck ramp coincides with a harassed field; see L8.

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** Noisy Cricket test 32's only routed group out of Bandar Abbas (the F-5E pair) taxied and flew, and the sixteen F-4Es there were untasked ramp jets, so it neither reproduces nor clears test 30's nine stuck Fencers. The large-aircraft clause still waits on the pydcs re-export.

**2026-09-13, test 30** (Persian Gulf — Scenic Route turn 1, `Tacview-20260913-125128`, 59 min
of sim, DCS 2.9.29.27468, build `78085dfd7`) — **generation clean; nine fragged red jets never
taxied at Bandar Abbas Intl.** Three of GIBBON Anti-ship 20's four Fencers (stands F02–F04),
all four of GIBBON Anti-ship 21 (F13–F16) and both Bandar-e-Jask BARCAP 24 F-4Es (J05–J06,
activated t=292) sat hot on their stands to mission end. The lead on F01 taxied and flew, the
QRA F-4Es on J07–J12 flew, and BARCAP 18 (J01–J02) and 19 (J03–J04, activated t=3100) never
moved either. No stand is double-booked in the `.miz` (102 parked units, 0 collisions by
airport and number), nothing red or blue sits within 2.5 km of the F row, and `retribution.log`
carries no parking line. The pattern is the one recorded for this campaign family in July
(Fencers "spawned on deck, never taxied"), now on a land field. What decides it: whether
pydcs's Bandar Abbas stand list (Persian Gulf export 2025-11-30) still matches the ramp that
2.9.29.27468 lays down — the stand-list dump in `retlab-dcs-update-2026-08-26-notes.md` §9 is
the tool. Consequence this turn: the anti-ship package against CVN-71 launched with one
striker, its four F-4E escorts orbited 185 km short of the boat for 50 minutes, and one flamed
out on final at Havadarya (7.4 km out, 300 m, wingman already on the ground) and its crew
ejected.

**2026-08-29, test 24** (Caucasus — Iron Gate turn 1, DCS 2.9.29.27278) — **generation passes;
the parking rework is NOT implicated.** Every squadron on both sides came up with the aircraft its
campaign file asks for, and **mission load produced no parking failure at all**. Generation placed
exactly 28 aircraft at Mineralnye Vody against pydcs's 28 slots and DCS accepted all 28.

**A correction, because the first read of this was wrong.** Four
`Mineralnye Vody: No parking place for 'Su-24M'` lines do appear — but at **t+57 and t+60 minutes**,
in two-ship pairs, long after load, and with an uninitialised group name in the log
(`'¿'`). **No Su-24M is homed at Mineralnye Vody in the `.miz`** — all 19 Su-24M groups
are at Mozdok or Tbilisi-Lochini, and the field's own QRA templates are MiG-31/MiG-29S/Su-27. So
this is a **runtime spawner adding aircraft to a field generation had already filled to exactly
100 %**, not a stand-count mismatch and not the 2026-08-26 rework. The spawner was not identified;
`intercept`, `redscramble` and `neutralborder` were all on and none of their templates is a Su-24M.
Worth its own row if it recurs.

**What this row still owes.** The large-aircraft clause is unresolved: pydcs reports
**0 large-capable slots** at Mineralnye Vody, so its A-50 and IL-78M air-start rather than taking a
stand. Whether the rework added large slots there cannot be answered without re-exporting pydcs's
terrain data — **no map's `airports.py` has been regenerated since the patch** (newest is Syria,
2026-06-16; Nevada's is from 2022). An undercount only wastes ramp, so this is capacity, not
correctness. Northern Russia is still unchecked.

The 2026-08-26 DCS patch rebuilt AI taxiway pathing to use aircraft dimensions, and says
in its own words that this changes the placement of parking spaces and increases the
number of slots for large aircraft. Iron Gate and Northern Russia both had every
squadron's `size:` hand-fitted to a stand count within the last month, so both are
sitting on numbers that may no longer be true. Related to **B96**, which is the same
question asked before the rework.

**Setup.** Start a new game on Caucasus - Iron Gate, then again on Northern Russia. Both
are authored to fill; that is the point of the row. ~20 min for the pair.

**Pass.** Every squadron on both sides comes up with the aircraft its campaign file
asks for. `retribution.log` carries no "No parking slots available" line at generation.
A C-130J or KC-135 tasked out of a field that has large stands spawns on one rather than
falling through to a runway or air start.

**Fail signatures, and what each means:**

- **A squadron comes up empty** — the base is oversubscribed. Squadrons fill in list
  order until the ramp runs out, so the ones at the bottom get nothing and do it
  silently. This is what cost Northern Russia its only AWACS and only tanker before the
  sizes were authored. Count the base's slots in the ME and re-fit the `size:` values.
- **A large aircraft air-starts or runway-starts where it used to sit on a stand** —
  `flightgroupspawner.py:277`'s `width > 40` classification is still ours and unchanged,
  so this means the slot supply beneath it moved. Check `ground_spawns_large` for that
  control point.
- **Aircraft spawn on top of each other, or taxi into each other leaving the stands** —
  the terrain's parking data and pydcs's copy of it have diverged. That is a pin
  problem, not a campaign problem; re-export before touching any campaign file.

**Watch for — the constraint this does not lift.** §1's per-base backstop EWR stays
removed. It was cut because a ground unit sat on taxiways and broke AI taxi routing, and
the fact that the routing code was rewritten is not evidence the constraint lapsed.

### B101 — The F-4E's Shrike and gun pod are still on the jet · §71 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **one data point on the new build, on the A model.** Anatolian Reach test 18 (2.9.29.27278, 2026-08-26) fielded an F-4E-45MC SEAD Escort with `{LAU_34_AGM_45A_SWA}` on stations 3 and 11 and the recording holds two AGM-45A launches. No AGM-45B, no SUU-23 and no AGM-78 fit was generated in any capture, so the two halves this row is about (the B-model clsid collision and the pod migration) remain unexercised; the OVGME pack rebase is still the gate.

**Both halves are confirmed against the updated install (2.9.29.27278) and both fixes
are IN** -- the pydcs pin moved to `bfdbb4d` the same day and the extension was trimmed
to match. Full detail in
[retlab-dcs-update-2026-08-26-notes.md](design/retlab-dcs-update-2026-08-26-notes.md) §2.2
and §2.3.

- **AGM-45B.** Stock now declares `{LAU_34_AGM_45B}` itself
  (`CoreMods/aircraft/AircraftWeaponPack/anti-radiation missiles.lua:1252`). §71 injects
  the same clsid with AGM-45A's settings borrowed, through a bare `setattr` with no
  collision check, after import — so ours wins, against a missile whose FM this patch
  reworked from scratch.
- **SUU-23.** HB split the pod into `{SUU_23_POD_Wing}` / `{SUU_23_POD_Centerline}` and
  its migration table covers pylons 1, 7 and 13 only. §71 wires the pod to pylons **3 and
  11**, which are outside that table.

The payload Lua is **not** at risk: `resources/customized_payloads/F-4E.lua` and
`F-4E-45MC.lua` name no SUU-23 clsid at all. The earlier draft of this row said to grep
them against the export; that has been done and they are clean.

**Setup.** Any campaign fielding the F-4E-45MC — Red Tide or Desert Storm. Frag a SEAD
flight and a flight carrying the gun pod, generate, and look at both jets in the ME
before flying. ~15 min.

**Pass.** The Weasel jet carries Shrikes on the rail it is authored for and the AGM-78
fits still resolve. The gun-pod fit shows a SUU-23 on the inner wing station. In the air,
a Shrike launches and guides.

**Fail signatures, and what each means:**

- **The gun pod is missing from the inner wing** — the OVGME pack is not applied, or its
  rebased copy no longer declares the pod on 3/11. The repo side already wires
  `{SUU_23_POD_Wing}` there (it had been wiring the **Centerline** variant since the July
  sync -- pydcs's attribute shuffle, fixed 2026-08-26).
- **The Shrike is there but behaves like the old missile** — our injected dict is
  overriding the native entry. Delete the `WeaponsF4EExpanded` AGM-45B entry and keep the
  pylon wiring; it resolves natively once the pin moves.
- **The pylon rejects the store in the ME** — the LAU-34 rail's legality changed. §71's
  design rule is that fits are gated on live pylon legality, so this is a data refresh.

**The remaining blocker is the OVGME pack, not the repo.** The planner side is fixed
and test-verified; but RetLab's `Expanded_F-4E_Weapons_Pack` OVGME mod is unapplied
(the update overwrote it), so in DCS the pack's own stores do not exist until its four
files are rebased onto the new stock and re-applied. Fly this row after that rebase.

**Watch for.** RetLab's `Expanded_F-4E_Weapons_Pack` OVGME mod was overwritten by the
update and is currently unapplied. Re-enabling the July copy reverts ED's AGM-45B and
SUU-23 work — see the note's §2.4 before turning it back on.

### B104 — The Viper's ROE tab declares the campaign's own sides · §74 · ◐ PARTIAL

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **the cartridge is right in the flown mission; the tab itself is unread.** Test 33's miz carries `DTC/Retribution Rattler 1 F-16C_50.dtc` with the 48-row ATDT and `TypeSovereignty` on. Checked against the blue and red rosters in the same miz: A-6, A-10, B-1, C-130, E-2, F-15, F-16, F/A-18 and KC-135 read FRIENDLY; Il-76, Il-78, MiG-21/23/29, Mirage F1, Su-24/25, Tu-16 (the H-6J) and Tu-22 read HOSTILE; the E-3, F-4, F-5, F-14, AV-8B, Su-27 and the rest that neither side flies read UNKNOWN. That is the derivation the row describes, on a real campaign. What remains is the DM opening the ROE tab on the MMC page and seeing the same table.

The cartridge now carries `MPD.ROE`: the 48-row Air Target Data Table with
sovereignty derived from the campaign's order of battle (blue-only families
FRIENDLY, red-only HOSTILE, shared/unflown UNKNOWN). Rows ship as
`{group_name, sovereignty}` only; the jet compiles membership from its own
`threat_base.lua`. Enum settled against `ROE_defs.lua` and a DM-set cartridge.
Detail in the features doc §74 and the DCS-update note §4.

**Setup.** Any campaign with a client F-16C — Iron Gate or Northern Russia. Fly a
Viper slot, MFD → DTE page: confirm the cartridge loaded, then open the ROE tab
(MMC format page). ~10 min on the ramp, no sortie needed.

**Pass.** The ATDT shows this campaign's sides: the families blue flies read
FRIENDLY, red's read HOSTILE, and a family both fly (Northern Russia's MiG-23…
check the campaign) reads UNKNOWN. In the air, a friendly type the FCR types out
(NCTR) or a TNDL track draws the green circle without an interrogation.

**Fail signatures, and what each means:**

- **The tab shows all UNKNOWN** — the ROE section did not load. Check the DTE
  page took the cartridge at all (if the route loaded but ROE did not, the
  section name or row shape is wrong — diff a saved cartridge against ours).
- **A family reads the wrong side** — the membership mirror disagrees with the
  jet's `threat_base`. Run `test_atdt_ids_all_exist_in_pydcs` first; if green,
  the id belongs to a different family jet-side than repo-side.
- **Wrong colours in the air but the right table on the ground** — not this
  feature. The ROE tree needs two factors for Hostile and TNDL for Mode 4; on a
  pre-datalink campaign red tops out at Suspect yellow by design.

### B105 — The Apache's cartridge loads: route, targets and the front line on the TSD · §74 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no client Apache in any capture.** Unchanged.

**2026-09-22, builder changed before any flight (§102, DM call).** The editor deletes a TSD
line outside 2-4 vertices (`NAV/Lines.lua:52,241`), and the builder wrote up to 8. The
front line is now 2-4 vertex pieces, the tanker boxes are 4-corner TSD **areas**, and
route `eta` is per leg rather than a running total (`NAV/Routes.lua`). Read the front
line as a run of short lines and the tanker as an area. The manual (Dec 2025, p195)
lists TSD lines and areas as not implemented, so an empty TSD is a possible result.

`apache.py` is the fourth §74 builder: WPTHZ waypoints W01.., the ALPHA route in
the editor's own leg shape, fogged SAM sites as TGT points, the FLOT as TSD
lines. Partitions the planner computes nothing for are omitted or ship as the
ME sample's empty skeleton — **that omission is the one structural risk**: the
DTU loader indexing an absent partition would fail the whole load, and no
headless test can see it.

**Setup.** Iron Gate or COIN, a client AH-64D flight. Spawn in, let the DTU
auto-load, TSD → check waypoints/route; PLT and CPG both. ~15 min.

**Pass.** The route shows as W01.. with the briefed names on point review, the
ALPHA route sequences them with sane leg speeds/ETAs, known SAM sites appear as
T-points named for their site, and the front line draws. Nothing else about the
jet's setup regressed (radios still tune, weapons page sane).

**Fail signatures, and what each means:**

- **Nothing loads / DTU error** — the loader indexed an omitted partition. Save
  a cartridge from the ME with only NAV touched and diff its top-level keys
  against ours; add the missing empty skeleton.
- **Points load but the route is empty** — the Routes element shape drifted
  from the editor's add-point handler (`{num, alt, speed, dist, eta, fix}`).
- **Route ETAs are nonsense** — the first-leg ETA anchor (TOS seconds) or the
  kts conversion. Compare one leg by hand: dist / (kts × 0.514).
- **T-points sit on unengaged sites** — the recon fog leaked; that is a §3
  regression, not a DTC one (`known_enemy_threat_sites` gates on `known_for`).

### B106 — The C-130J King can be fragged into a rescue, and holds an orbit clear of the threat · CSAR · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no hand-fragged King in any capture** (the DM's DCS name `King 1 | Flash` is a name, not the flight). Unchanged.

A hand-fragged fixed-wing CSAR flight now builds `KingFlightPlan` (an on-scene
racetrack) instead of raising "CSAR is only usable by helicopters". Nothing about
this is exercised in DCS: the orbit geometry is pinned by
`tests/ato/flightplans/test_king.py`, but the flight still spawns under
`configure_transport` (main task `Transport`, ROE weapon-hold) and no test can say
whether a Transport-tasked C-130 actually flies a ControlledTask racetrack.

**Setup.** Any campaign with a downed pilot on the map. Right-click the survivor →
add a helo CSAR flight (AI) → add a second flight, C-130J-30, task CSAR. Fly the
King. ~25 min, and it closes G36/G33/H14 in the same mission if you crew the helo
slot too.

**Pass.** The flight creates without a dialog. The map draws a racetrack, not a
line to the survivor. The orbit sits outside every drawn threat ring. Airborne, the
jet reaches the racetrack and holds it for the on-station window rather than flying
through and going home.

**Fail signatures, and what each means:**

- **"Could not create flight: CSAR pickups are only usable by helicopters"** — the
  dispatch in `flightplanbuildertypes.py` stopped matching; the flight fell through
  to `CsarFlightPlan`. Check `flight.is_helo` on the C-130J.
- **The orbit is drawn inside a SAM ring** — `threat_zones.threatened()` read False
  for a survivor who is in fact threatened, so the plan took the hold-off branch.
  The geometry is pinned; the input is not.
- **AI King flies to the racetrack and straight home** — `RaceTrackBuilder`
  refused the plan (it requires a `PatrollingFlightPlan`) or `Transport` as the DCS
  main task blocks a ControlledTask orbit. First one logs; the second does not, and
  the fix would be a King-specific `configure_*` in `aircraftbehavior.py`.
- **The orbit sits 80+ nm off** — the survivor is deep inside a large ring, so
  `distance_to_threat + THREAT_BUFFER` is genuinely that far. Working as designed;
  move the waypoints.

---

### B110 — A SEAD jet's steerpoints are the site's emitters, and the card's STPT numbers match · §5 / §3 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** Tests 30–33 fragged SEAD Escorts and DEADs but no SEAD-tasked flight, so no target-point list was generated to check. Unchanged.

A SEAD flight used to get one `TARGET_POINT` per *unit* at the objective. Against an
SA-2 that is thirteen steerpoints, six of them the layout's Logistics/Fuel/AAA slots:
two GAZ-66, two TZ-22 bowsers, two ZU-23. The waypoint list now reads
`TheaterGroundObject.sead_targets` (radar classes + `TELAR`/`SHORAD`/`LAUNCHER`), which
is what the SEAD kneeboard already listed. DEAD is deliberately unchanged.

The kneeboard pairs its emitter rows to those waypoints **by index**, so the risk this
row exists to catch is the two lists drifting apart — a unit-test can pin the pairing
but not what the jet actually loads.

**Setup.** Any campaign with a legacy SAM belt; target intel precision on **Exact**
(Approximate collapses SEAD to one area waypoint and this row does not apply). Frag a
SEAD flight against an SA-2 or SA-3 site that has its support slots filled — check the
site in the app first, it needs trucks in it. Fly to the aircraft, open the Waypoints
tab and the SEAD Target Info kneeboard page. ~15 min.

**Pass.** The waypoint list has one target point per radar and launcher and **none for
the trucks, bowsers or ZU-23s**. Every row of the kneeboard's `# | Description | ALIC |
Location` table carries a number, and that number is the steerpoint that actually sits
on that emitter.

**Fail signatures, and what each means:**

- **Trucks still have steerpoints** — the plan came from a save generated before this
  change. Flight plans are persisted; re-plan the flight or start a new turn.
- **The card's STPT column is blank from the second row down** — `target_units` and the
  flight plan are reading different lists. That is the exact regression
  `test_sead_exact_view_numbers_stpts_from_the_emitter_waypoint_list` pins.
- **A steerpoint number points at the wrong emitter** — same cause, but the lists are the
  same length, so check ordering rather than membership.
- **An HDS S-300/S-400 site loses its radar steerpoints** — the class filter missed a mod
  unit's `class:`. The filter is class-based precisely so HDS units survive; ALIC would
  not have. Check the unit's yaml in `resources/units/ground_units/`.
- **A site with no emitters gets no steerpoints at all** — the `sead_targets` fallback to
  the full roster failed; `targets[0]` anchors the flight plan's timing math, so this
  would show up as a planning error rather than a quiet miss.
### B113 — A pilot's logbook fills in, and the kills are the ones they got · §96 · ◐ PARTIAL

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **the player half passes; AI wingmen's kills are dropped.** Player seat: sorties 1, 1,740 s, no kills, rank 2nd Lt; no `Award:` line in the SITREP. But `fold_sortie_records` skips counters-only records, and an AI wingman's record is counters-only (no track). On this flight that dropped 9 of blue's 17 air kills and 7 of 17 ground kills from every career — e.g. `Camp Bastion BARCAP … Pilot #2`, 3 air kills, landed alive, no career holds them. The docstring accepts this as "a stray shot"; here it was half the kills. Pass item 5 (AI pilots in the flight get a sortie) fails the same way for wingmen. A DM question.

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the pilot's career is right for what he did.** The turn-2 save's 334th FS player seat reads sorties 1, combat sorties 1, 1,740 s airborne (t=870–2610), 0 shots, 0 kills, 0 ejections. He was shot down without ejecting; `invulnerable_player_pilots` keeps him Active. No kill to check, so the kill half stays open.

**2026-09-22, test 38** (Syria — Long Road to H3 turn 2, 37 min, one human in the SPARROW SEAD Viper lead from Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048), `Desktop\New test\38`) — **item 2 fails on the ramp; fixed the same day.** Terry Fleming (the seat Flash flew) reads 1 sortie, 31.0 min, 3 shots, 1 hit, 0 kills. Airborne was t=773–1903, 18.8 min. `SortieRecord.duration` was `last_seen − first_seen`, and the first sample is at t=30 on the ramp, so a cold start logged its start-up and taxi. Test 37's 64.5 min carried the same 13 min. The recorder now keeps `first_airborne` / `last_airborne` (`unit:inAir()` at each sample) and flight time is that span; a `state.json` without them keeps the old figure. The SITREP's hours airborne and §97's minutes read the same property. Item 3 holds: the human's AIM-120B hit the MiG-29A at t=1653.6, Pilot #2's 1.1 s later, and DCS's `kill` event names #2. The next flown mission re-checks item 2.

**2026-09-22 — awards removed** (DM call). Item 4 checked a rank and awards; it checks the rank alone now. The `first_sortie` and `first_blood` in the test-33 entry below no longer exist. Status unchanged.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **item 2 fails for a vacated seat.** See B70: the human left the jet at t≈2601 and the record ran to t=3900 under AI control, so the flight time folded into the logbook overstates the sortie by ~22 min. Fixed the same day in the recorder (`player_left`); the next flown seat-vacate is the check. Items 1, 3 and 5 unchanged (2 GBU-31 on the runway, no unit kill, no kill column — the test-33 shape).

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** the second-human fix is unflown since test 33.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — **the host's logbook is right; the second human got nothing.** The player seat Flash flew (335 Squadron) reads sorties 1, combat 1, 92.5 min, 4 shots, 3 hits, `first_sortie` — items 1, 2 and 4 hold, and item 5 holds too: every AI pilot who flew has a sortie, the Eagle lead his three kills and `first_blood`. Item 3 is a wash: Flash's targets were the four Tabqa scenery objectives, which are not units and count as no kill in any column. The second human's seat has nothing at all, for the reason in B70 (his record carried no track); fixed there, unflown since.

**Needs one flown mission.** ~25 min including the flight.

**Setup.** Any campaign, `pilot_career_logbook` on (it is by default). Before generating,
open your squadron, select the pilot you will fly as, click **Logbook** and note the numbers
— on a fresh campaign they are all zero. Fly a mission in which you shoot something down or
destroy something on the ground, land, accept results, then reopen the same pilot's logbook.

**Pass.**
1. **Sorties went up by exactly one**, not by the size of your flight.
2. **Flight time is roughly what you flew** — within a minute or two, since the recorder
   samples every 30 s and only counts you from the first sample airborne.
3. **The kills you actually got are in the right columns.** A MiG is an air kill, a SAM
   launcher is a ground kill, a patrol boat is a naval kill.
4. **A rank renders** in the logbook heading, and the SITREP carries no `Award:` lines.
5. **AI pilots in the same flight also have logbooks** with a sortie added.

**Fail signatures, and what each means:**

- **Sorties went up by four on a four-ship.** The fold is crediting the whole flight to one
  pilot — `UnitMap.flight()` is resolving several unit names to the same pilot, which means
  the roster seats were not bound per unit.
- **Sorties went up on a turn you did not fly** (a jet that sat on the ramp). §91's
  `MIN_SORTIE_DISTANCE_M` guard is not holding; check that `SortieRecord.flew` is being
  consulted and not just `record.track`.
- **Kills are all zero after a mission you know you got one in.** `S_EVENT_KILL` is not
  reaching `sortie_recorder_on_kill`. Grep `state.json` for `air_kills` — if the field is
  there and zero, the coalition check rejected it; if the field is absent, the Lua wiring in
  `dcs_retribution.lua` is not firing.
- **You are credited with a kill on a friendly.** The coalition guard is not working; that
  is the one thing this feature must never do.
- **Flight time is wildly high** (tens of hours after one mission). Hours are being summed
  from counters-only or parked records rather than only from records that flew.
- **The page is all zeroes on a campaign carried over from an older build.** Expected, not a
  failure — pre-§96 saves have no records to fold and the page says so.

---

---

### B117 — A Sandy can be fragged onto a survivor, and covers the pickup · §99 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no Sandy fragged in any capture.** Unchanged.

**Needs a survivor on the map and one flown mission.** ~30 min.

**Setup.** Any campaign with an A-10 or an Apache squadron. Get a survivor first — fly a
turn and lose an AI aircraft, or use an existing downed pilot. Then create a **new package**
on that survivor, add a flight, and pick **Sandy** from the mission-type list. Add the
rescue helicopter to the same package or a separate one. Fly the Sandy.

**Pass.**
1. **Sandy is in the mission-type list** at the survivor, for the A-10 and the Apache and
   for nothing else in the wing.
2. **The flight plans** — no "Could not create flight" dialog — and the map shows a short
   track sitting on the survivor, not on the front line.
3. **The callsign defaults to Sandy**, numbered, and a second one numbers after it.
4. **An AI Sandy engages** ground units near the pickup and does not wander off after
   something 20 nm away.
5. **The Apache flies the same plan at helicopter altitude**, not at 10,000 ft.
6. **No Sandy appears in an auto-planned turn** — not in the ATO, not after passing a turn
   with a survivor on the map.

**Fail signatures, and what each means:**

- **"Could not create flight" after picking the squadron.** The dispatch in
  `FlightPlanBuilderTypes.for_flight` is not reaching `SandyBuilder`, or the target is not
  a `DownedPilot` — the same class of bug the King had before 2026-08-26.
- **The track is drawn along the FLOT.** The flight resolved to `CasFlightPlan`, so the
  `SANDY` entry in the builder dict is missing or shadowed.
- **The flight flies out and back through the survivor instead of across.** The leg axis is
  wrong — it should be perpendicular to the run-in, and `test_the_legs_cross_the_run_in`
  pins that headless, so this means the real `WaypointBuilder` is doing something the fake
  one does not.
- **A Sandy shows up in an auto-planned ATO.** Something now proposes the tasking. Nothing
  in the HTN should; find it before shipping, because an AI Sandy is noise at best.
- **The Apache holds 10,000 ft.** `builder.cas()` is not seeing `is_helo`, so the AGL
  handling in `nav_path` is also suspect.
- **Every jet in the wing offers Sandy.** The yaml `tasks:` gate is not the gate — check
  that no derivation in `get_task_priorities` is inferring `Sandy` from `CAS`.


### B118 — The Super Hornet still arms and its new cockpit options are there · CJS 2.4.5.260726 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **not exercised.** No capture fields the CJS Super Hornet (no Marianas 2027 or Baltic Fury turn was flown). Unchanged.

**Needs one generated mission, not a full flight.** ~10 min.

**Why this row exists.** The 2.4.5.260726 update was verified against a fresh pydcs export:
702 declared stores, their names, weights and every pylon's weapon list are identical to
260501.RC1, so nothing about the loadouts should move. What CI cannot exercise is whether the
mod still accepts the fits we write into the `.miz`, and whether the two changed properties
reach the cockpit.

**Setup.** Any campaign fielding the CJS Super Hornet — Marianas 2027 or Baltic Fury both do.
Take a player F/A-18F and a player E/A-18G if the campaign has one. Generate the mission and
slot in; there is no need to fly it.

**Pass.**
1. **The jets spawn with the loadout the payload tab showed** — in particular a Strike Rhino
   carrying 2× GBU-31(V)4/B on the midboards and 2× GBU-32(V)2/B on the outboards, which is
   the fit the Navy-case work put there.
2. **`WSO Cockpit Type (Visual Only)`** appears in the F/A-18F's properties in the payload
   tab, offering *Advanced Crew Station* (the default) and *Legacy Crew Station*, and the
   back seat matches the one selected.
3. **The E/A-18G's `Demo` property offers only `None`.** CJS retired its `Installed` value;
   a Growler still offering it means the extension did not take the update.
4. **The mods page in New Game reads `v2.4.5.260726`** for both the Super Hornet and the
   Super Hornet Tanker entries.
5. **A US Super Hornet flight is called `Hornet`, `Squid`, `Ragin`, `Roman`, `Sting` or
   similar** — not `Brutal`, `Buckshot` or `Cannon`, which are the mod's *Australian* pool and
   were what every US jet drew from before this update. An Australian squadron should get the
   Brutal/Buckshot names, and a CJTF squadron may draw from any of the four nations' pools.

**Fail signatures.**
- **`Weapon not found` or an empty pylon in the ME/mission** for any store a Retribution fit
  names — the declared weapon set moved after all and the export needs re-taking.
- **A tanker variant kills mission generation** with `RuntimeError: Datalink network not
  supported for aircraft with id 'FA-18ET'`. The export declares `networked_datalink = True`
  for FA-18ET/FA-18FT and the fork deliberately overrides it to `False`, because pydcs has no
  datalink entry for those ids. If this fires, the override was lost in a regen — it is
  guarded by `tests/retlab/test_super_hornet_datalink.py`.
- **The F/A-18F has no WSO option**, or the E/A-18G still lists `Installed` — the property
  blocks did not update.
- **Every Super Hornet flight is `Brutal`/`Buckshot` again, whatever the country** — the callsign
  pools reverted to the single mislabelled block, or a regen re-took the export's display-name
  keys, which pydcs cannot resolve. Guarded by `tests/retlab/test_super_hornet_callsigns.py`.

---

### B119 — The King DFs the survivor, sweeps the threats, and the Sandy sees the marks · §100 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **no King flown in any capture.** Unchanged.

**Needs a survivor on the map, a human in the King and a second human in a Sandy or helo.**
~40 min. Closes alongside B106 and B117 in the same mission.

**Setup.** Frag a C-130J-30 as CSAR by hand on a survivor and fly it. Put a second player in a
Sandy (A-10/Apache) or the rescue helicopter on the same survivor. Note where the survivor
actually is on the F10 map before you start (the host can use the reveal overview).

**Pass.**
1. **KING | On-Scene Commander** is on the King's F10 menu, and only the King's.
2. **One cut gives a bearing and no mark.** The message says to take another from ≥15° around.
3. **A second cut from 15°+ around drops a survivor mark within a couple of miles**, and the
   text says `+/-`. Flying further round and cutting again tightens it.
4. **Closing inside 15 nm with the survivor in view snaps it exact** — the mark reads
   `pod contact` and sits on the pilot. Behind a ridge it stays a DF cut.
5. **Threat sweep lists the nearby enemy ground as a class with bearing/range from the
   survivor**, closest first, five at most, and the marks sit near but not on the units.
6. **Pass picture to the other player puts the brief and the same marks on their F10 map**, and
   nothing appears for an AI flight.

**Fail signatures, and what each means:**

- **No menu on the King.** `rescueFlights` did not carry the King with `player = "true"` —
  check the emitted `dcsRetribution.CSAR` node — or the group had no human at the 10 s poll.
- **The first cut already drops a mark.** `MIN_CUT_SEPARATION_DEG` is being bypassed, or the
  King was inside pod range and the snap fired (which is correct — check the text).
- **Pod contact never fires with the survivor in plain view.** `land.isVisible` from altitude
  reads false in DCS; the LOS gate wants a height offset or removing.
- **The survivor mark sits exactly on the pilot from a distance.** The noise is not applied
  (the LCG seed is degenerate) — every cut intersects perfectly.
- **"No survivor on the beacon" with a pilot on the map.** `Unit.getByName(unitName)` is nil
  for a survivor DCS still shows — the unit name the emit carried does not match the spawn.
- **Marks show for the King but not for the Sandy player.** `markToGroup` to a multi-crew
  group only reaches some clients; fall back to `markToCoalition` for the brief.
- **An AI Sandy changes course after a pass.** Something pushed a task. Nothing here should;
  find it before shipping.

### B125 — A dynamic-slot jet spawns with the template's route, radios and loadout · §101 · ☐ UNTESTED

**2026-09-16, line-by-line audit against the test history (tests 1–33, session `9148a88a`)** — **unchanged;** test 33 is the only capture with a template flagged (`MAVERICK Strike`, links 141 and the stale 162 the fix now clears) and both humans took the fragged slots. On the LOCAL card.

**2026-09-15, test 33** (Syria — Operation Peace Spring turn 2, multiplayer listen host with two humans in the MAVERICK Viper strike, 93 min, `Tacview-20260915-205127-DCS-Host`, DCS 2.9.29.27468, build `611eedfcd`; the turn-3 save `91526.retribution` is the auto-planner's own frag on the same build) — **not exercised, and a generator defect found and fixed.** Both humans took the fragged MAVERICK slots (units 405 and 406, static client units), so no dynamic jet was spawned and the pass criterion was not touched. The `.miz` itself: `MAVERICK Strike|31|8` (group 141) is flagged and Ramat David's F-16C entry links 141 — correct. But Akrotiri's F-16C entry links group **162, a red H-6J Badger**. The archive shows why: the 20:40 generation had a second client flight, `LLAMA DEAD` at Akrotiri, linked as 162; the DM removed it and regenerated at 20:43 and 20:49, and the link stayed, because the pydcs `Airport` objects belong to the campaign's terrain and outlive a generation. Fixed the same day: the generator clears every `linkDynTempl` entry on every airport before writing (`_clear_stale_links`, pinned by `tests/missiongenerator/test_dynamic_spawn_templates.py`). What a stale link does to a dynamic spawn in DCS is unknown and no longer reachable.

**History:** opened 2026-09-15 as the gate on
[`retlab-dynamic-spawn-templates-notes.md`](design/retlab-dynamic-spawn-templates-notes.md);
**built the same day** (§101) on what the install's Lua could answer, so this row now flies
the generated mission, not a hand-made one. The generator marks one client flight per base
and type as DCS's **Dyn.SPAWN Template** (`dynSpawnTemplate = true` on the group) and links
the base's warehouse entry to it (`linkDynTempl = <groupId>`). The slot-select dialog reads
loadout, properties and livery off the template and hands the rest to native code, so
route and radio carry are open. The entry carries no `wsType`; the editor fills one in when
absent, the sim's loader is native, so that is open too. **2026-09-15, DM:** a template
group stays in the slot list, so the real flight is marked and there is no clone.

- **Setup:** any campaign with **Enable dynamic player slots** on and a player Hornet
  package fragged from a field or the boat. Generate the turn. Optional, 1 min: open the
  miz's `warehouses` file and confirm the field's `FA-18C_hornet` entry has
  `linkDynTempl` pointing at the fragged group's id. Open the mission and take a
  **dynamic** Hornet at that base, not the fragged slot. ~10 min.
- **Pass:** the dynamic jet carries the fragged flight's payload and properties (certain),
  and its waypoints on the HSI and its presets in the radio (the open half). The fragged
  slot is still in the slot list and still flies as itself.
- **Record, whichever way it goes:**
  1. Route carried: yes / no. Radio presets carried: yes / no.
  2. Whether the dynamic list at that base offered the type at all (a missing type is the
     `wsType` signature — see below).
- **Fail signatures:** the dynamic jet spawns stock at a base whose `warehouses` entry
  carries the link (the sim needs `wsType`: build the id table before anything else); the
  type is missing from the dynamic list at that base only when the link is present (same
  cause); the fragged slot vanished from the slot list (the template is consumed after all,
  so the build must clone). A jet with the payload but no route is not a fail — it is
  answer 1 and shrinks the feature to loadout and properties.


### B128 — An escort comes home when its primary never flies · §8 · ◐ PARTIAL (2026-09-23, test 39; was ☐ UNTESTED)

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the shot-down half passes.** Both PIG Strike F-15Es were down by t=2672 and both HORNBILL Strike F-15Es by t=3065, well before their planned SPLITs (t=4085, t=4058). The generated `Split-` trigger releases the escorts on the primary group's death as well as on the flag. PIG SEAD Escort (Hornets) turned at t=2700–2711 and landed at Camp Bastion; PIG Escort (F-15Cs) turned by t=2909 and landed at Kandahar; HORNBILL Escort turned at t=3089 and was 3 NM from Kandahar at mission end, and the surviving HORNBILL SEAD Escort Hornet landed at Camp Bastion. No escort held its anchor. The never-spawned case (the time backstop, test 36's shape) was not exercised.

- **Setup:** any package whose primary is AI and can be prevented from reaching SPLIT —
  easiest is a carrier primary on a full deck, or shoot it down yourself on the ingress.
- **Pass:** the escort turns for home within ~15 minutes of the primary's planned split
  time and recovers at its own field.
- **Fail signature:** the escort is still circling its ESCORT HOLD anchor at mission end
  (test 36: five flights, four of them 168–310 km inside red airspace).

### B129 — A flight with fuel to spare has no tanker leg · §46-adjacent · ◐ PARTIAL (2026-09-21, test 37; was ☐ UNTESTED)

**2026-09-23, test 39 re-read (session `c2acb521`, at the DM's request)** — **the drop and the keep, one each.** PORCUPINE DEAD (F-16C, Kandahar → the S-350, the longest leg) kept its REFUEL leg and both survivors took gas: 680 s and 740 s within 300 m of the KC-135. Every other flight with a REFUEL leg was shot down first. One lead to watch: FALCON Escort (F-15C, no REFUEL leg) never froze at SPLIT, burned from 1.92 to 0.11 and was 49 NM from home at mission end; its wingman hit terrain at t=4745 with no weapon near. That escort also ran 164 kt ahead of its striker (B111).

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the gate held its line.** PIG Strike (F-15E, Kandahar → Hashemi Bridge) kept its REFUEL leg with `RTB margin +3720 lb` on the card: positive, but under the 2× reserve bar the drop needs. It never reached the tanker. The turn-2 save keeps REFUEL on the Kandahar boom flights (DEAD F-16s, escort F-15Cs) and none on the Camp Bastion probe flights.

**2026-09-21, test 37** (Syria — Long Road to H3 turn 1 (new game), 65 min, one human in the Pontiac 5 OCA/Runway Viper from Incirlik, `Tacview-20260921-194148`, DCS 2.9.29.27468, build `5a11efa13` (main at #1038), `Desktop\New test\37`) — **one airframe, both halves.** Pontiac 5 (F-16C, Incirlik → Aleppo → Incirlik, 250 nm round trip) carries no Refuel row, RTB margin +6,111 lb, route Hold → Join → Ingress → Strike → Split → Land. The miz still holds 37 `REFUEL` waypoints on other flights, so the drop is per-flight, not global. Whether every flight that kept a leg genuinely needed it is not measured.

- **Setup:** any turn with tankers planned and a long-legged aircraft on a short sortie —
  a bomber or a Strike Eagle off a near field.
- **Pass:** that flight's kneeboard has no Refuel row and its route goes target → split →
  home; a flight that genuinely needs the gas still has one.
- **Fail signature:** a flight that needed a top-off is planned without one and lands
  short or diverts — record the airframe, because the 2×/3× reserve thresholds are the
  knob. Conversely a bomber still detouring past its own field means the drop did not fire;
  check whether the airframe has a measured `fuel:` block (most do not).

### B132 — The profiler names the sim-thread sink, or clears Lua of it · sim-thread freeze note · ◐ PARTIAL (2026-09-21, test 37; was ☐ UNTESTED)

**2026-09-22, test 38** (Syria — Long Road to H3 turn 2, 37 min, one human in the SPARROW SEAD Viper lead from Incirlik, `Tacview-20260922-195428`, DCS 2.9.29.27468, main `a9c756b2f` (#1048), `Desktop\New test\38`); profiler t+900 s for 600 s — **Lua cleared again; the window closed 60 s before the slow stretch.**
- **Window (t=900–1500):** the human airborne, en route to the join. Sim at 1.0× (29.0–32.4 wall seconds per 30 s) with the hook on. 16 stalls of 259–529 ms, every one at t ≡ 0–1.25 (mod 5): the 5 s lock again.
- **`Function time 142.5 %` is an accounting artefact.** Skynet raised `Static doesn't exist` 174 times (row G43). MOOSE's profiler never sees a return from a call that errors, so `getTypeName` (600 s over 300 calls) and both Skynet `create`s (35 s each) timed from one error to the next return. `GetDetectedUnitTypeName` (61 s) has the same shape. No stall in the window passed 529 ms, which a real 1.5–2 s call would have caused.
- **Slow stretch (t=1560–1890):** 32.8–36.0 wall seconds per 30 s (0.83–0.91×; test 37 0.55–0.8×), 8–17 `ANTIFREEZE` per 30 s. It runs from the human reaching the fight (AIM-120 at t=1636, S-300 shots at the human t=1815–1824) to the seat change at t=1903. The next heartbeat is 30.4 s and it stays at 30. The Lua workload does not change across a seat change.
- **F10 minute:** DM's read, "F10 felt normal". No heartbeat in the stretch came back to 30 s, so the map drew smoothly while the sim clock stayed slow. Rendering is not the sink. The human's own jet is what is left: radar, HTS, TGP, datalink against ~300 aircraft.
- **Freezes:** 23 stalls over 250 ms in 37 min; DM felt "fewer / only a few". Beside mission load (27 s) and the seat change (35 s): 2.1 s at t=131, 7.0 s at t=1567 (no log line; heap 963 MB → 488 MB across it), the rest 254–529 ms. Every stall advanced model time by 0.25 s: nothing was a freeze DCS caught up from.

PARTIAL until a flight splits the own-ship candidates (LOCAL item 4).

**Test 37 (2026-09-21, Long Road to H3 turn 1, 65 min, `Tacview-20260921-194148`):** the instrument
works end to end — armed, heartbeats every 30 s, `Profiler Started/Stopped`,
`MooseProfiler.txt` written. Verdict for the quiet phase only, because the default window
(t+60 s for 300 s) closed before the battle: Lua function time 37.4 s of 300 s (12.5 %,
hook-inflated), no function over 33 ms/call, RetLab plugins 1.6 s combined — **Lua is not
the sink there**. The Lua heap runs a 430 MB → ~950 MB sawtooth every ~150 s (3.3 MB/s
churn; the profiler cannot say what allocates it), and 17 of the 41 sub-2 s stalls sit on a visible collection drop. Re-analysed 2026-09-22 in model time: the stalls are phase-locked to a 5 s cycle (p≈0.002), not 15/30/60 s. The stall log also had a blind spot — it measured model lag, so a freeze DCS caught up from was invisible — fixed; see the freeze note.
The dominant finding is elsewhere: from t=960 to t=2640 the sim ran 30 s of model time in
37–54 s of wall clock (755 quantizer clamps), and that stretch is the battle — unprofiled.
PARTIAL until a flight profiles the battle window (delay ~900 s, duration 600 s). Ledger in
[retlab-sim-thread-freeze-notes.md](design/retlab-sim-thread-freeze-notes.md).

The measurement flight behind the 2026-09-20 freeze investigation
([retlab-sim-thread-freeze-notes.md](design/retlab-sim-thread-freeze-notes.md)). Three
flights on an 870-unit Long Road to H3 turn froze ~1 s every 15–30 s; TIC's stuck-unit
retry, the 15 s `state.json` write and §94's sweep were each accused and each cleared
(test 37's stalls are locked to a 5 s cycle, not to any of their 15/30/60 s timers, and TIC-off still froze). What is left is
either a Lua script or DCS itself choking on the size, and the log cannot tell them apart.
The `profiler` plugin (`resources/plugins/profiler/`, default off) can: MOOSE's PROFILER
for a window, and a stall log for the whole flight.

- **Setup:** Settings → Lua Plugins → tick *Lua profiler*. Regenerate the turn that
  freezes. Fly ≥ 6 min past spawn-in without pausing. Untick afterwards. ~10 min.
- **Pass (the instrument):** `dcs.log` carries `PROFILER| stall log armed`, a
  `PROFILER| alive` heartbeat every 30 s, and `Profiler Started` / `Profiler Stopped`
  around the window; `Saved Games\DCS\Logs\MooseProfiler.txt` exists with a
  `Function time … (N % of runtime game)` line and three tables.
- **The verdict it produces:** either one script dominates the total-time table (a code
  change, filed against that script), or function time is a small share while
  `PROFILER| stall` lines keep coming (native DCS; the lever is the turn's size). Write
  the number and the top five functions into the note's ledger either way.
- **Fail signatures:** no `PROFILER|` lines at all (the config work order did not load —
  check the bundled DoScriptFile trigger); `Profiler needs os/io/lfs` in `dcs.log`
  (`MissionScripting.lua` was overwritten by a DCS update — re-run the Retribution
  install fix); stalls only outside the profiling window (the hook's own overhead is
  masking them — rerun with a longer delay); the `.txt` missing after a normal mission
  end.


### B133 — A SAM the campaign never named goes dark with the power station beside it · Skynet return · ☐ UNTESTED

A campaign with an `iads_config:` block only exported the sites the block named, so a
SAM in an anonymous slot fought as a standalone DCS group: never in Skynet, never dark,
never cued, and the power station beside it protected nothing (2026-09-21,
[retlab-skynet-return-notes.md](design/retlab-skynet-return-notes.md), found in
juanjux/dcs-escalation#336). Unnamed sites are now enrolled after the config and wired by
range, on New Game and on loading an older save.

- **Setup:** a config-mode campaign (Red Tide or Iron Gate) and a red SAM that sits in a
  Ground-N slot rather than under a name in the yaml. Check the map's IADS layer first:
  the site must now draw a link to a comms tower or power station within 35 nm.
- **Pass:** the site behaves as a netted one — it is dark until the network cues it and
  the map shows the link — and after the power station beside it is destroyed, the next
  turn's mission has the site down (no emissions, no engagement) the way the named sites
  behind that station are. Loading a save from before this change logs `IADS: wired …`
  once and the link appears.
- **Fail signatures:** the unnamed site still has no link on the map (it is not an
  `IadsGroundObject`, or the campaign is basic-mode); it engages after its station is
  dead (the link exists but Skynet did not receive it — check the generated
  `skynet` config for the group); a named site gained a link it was not given (the config
  is no longer honoured exactly).

### B134 — Front-line CAS takes a Harrier SEAD escort, and no Harrier escorts a deep package · §69 · ◐ PARTIAL (2026-09-22, test 38 ATO read; was ☐ UNTESTED)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **the plan half passes on a second campaign; the flown half was not reached.** `front_line_sead_escort` on, planner behavior at its default. The one front-line CAS package (2 A-10C, UNOMIG Sector HQ/Sukhumi) carries a 2-ship AV-8B SEAD Escort from LHA-1 with Sidearms and Mavericks; red's front fields Tunguskas. The FROG strike and the anti-ship raid carry no Harrier escort. The mission stopped at 12:52 with the escort 81 NM and the A-10s 94 NM short; their TOT was 13:11.

**2026-09-23, trigger widened — needs a re-read.** Test 39 (Graveyard of Empires, `asdasd.retribution` turn 2) repeated test 38's miss: the CAS package proposed its SEAD Escort, no fixed SAM ring covered FLOT START → FLOT END, and it flew A-10s only while red's front-line SA-19s fired seven 9M311s. The escort is now also needed when the enemy control point deploys radar air defense to the front (a unit type in `UNITS_WITH_RADAR` with an anti-air class: Tunguska, Osa, Tor, Shilka, Gepard and the like; not Strela, Avenger, ZU-23 or 2S38). Re-planned headlessly on that save: the CAS package carries 2 AV-8B SEAD Escorts; no BAI, strike, OCA, DEAD or Armed Recon package carries a Harrier SEAD escort. The front half of **Pass** now reads "whose route is covered by a radar SAM, or whose enemy front carries radar air defense". Re-read the ATO on the next turn with the planner suite on, then fly it.

**2026-09-22, test 38 ATO read** (Long Road to H3 turn 2, `brady.retribution` saved 18:40, main `983ba7a52`, RetLab planner suite on) — **the deep half passes; the front half was not reached, correctly.** DM's read: looks good. From the save: all seven deep SEAD Escorts are Vipers (480th FS) or Hornets (VFA-192, VFA-37) — MOCKINGBIRD and CICADA BAI, the Kharab Ishk Armed Recon, IBIS and FANGTOOTH strikes, SPARROW and QUAGGA DEAD — and no Harrier flies anywhere; VMA-231 sits on LHA-1 with 8 of 8 untasked. The one CAS package (2 Apaches, Gaziantep/Kharab Ishk) proposes the SEAD Escort, but the planner's need check reads only the escorted leg, FLOT START → FLOT END, and no radar SAM covers it: the nearest radar-SAM zone is 10.3 km off and no red radar-SAM site is within 30 km of the front. Re-planned headlessly three times with the same result. VMA-231 is eligible for that package (196 NM, inside the 250 NM mission range). The front half needs a turn with a radar SAM over the FLOT.

Built 2026-09-22 from test 37: four Sidearm Harriers flew SEAD escort on deep packages,
fired nothing, and one pair died to an SA-11. See §69's front-line SEAD escort paragraph.

- **Setup:** a campaign with an AV-8B squadron and radar SHORAD near the front (Long Road
  to H3 has both). Turn on the RetLab planner suite (or `front_line_sead_escort`), pass a
  turn, and read the ATO. ~5 min, no fly needed; fly one CAS package for the second half.
- **Pass:** a front-line CAS package whose route is covered by a radar SAM carries a SEAD
  Escort, and it is the Harrier squadron when one is free. No BAI, strike, OCA, DEAD or
  Armed Recon package carries a Harrier SEAD escort. Flown: the Harriers stay with the CAS
  flight and fire Sidearms at the front's radar SHORAD.
- **Fail signatures:** a Harrier SEAD escort on a deep package (the eligibility rule is not
  reached — check `sead_escort_front_line_only` on the AV-8B and the setting); CAS with no
  SEAD escort under a radar SAM (the proposal or the threat trigger); a Hornet or Viper on
  the CAS escort while a Harrier sat idle (the ranking term); Harriers that join and then
  never fire (the Sidearm finds no emitter — record what radar was there).
### B135 — A saved point reaches the cockpit with the number the kneeboard gives it · §102 · ☐ UNTESTED

Saved points (2026-09-22, [retlab-my-aircraft-notes.md](design/retlab-my-aircraft-notes.md))
go into the §74 cartridge on route sequence 2 (Hornet, Viper) or the A-10's CDU EXTRA
plan, and onto a kneeboard page numbered the same way.

- **Setup:** a player Hornet or Viper with the DTC on. Map → crosshair button (top left)
  → click a spot → Save as waypoint. Or My aircraft → Add. Generate.
- **Pass (app, added 2026-09-27):** with neutral border defense on, the crosshair answers a
  click inside a country's airspace, not only over the sea. A click on a route, a base or a
  suspected-site circle still belongs to that thing.
- **Pass:** the kneeboard's "saved points" page lists the point with a number N. In the
  jet, STPT N is that point (name and position), SEQ1 is still the route, and stepping to
  SEQ2 (Hornet) shows only the saved points. Viper: the tanker/AWACS anchors now follow
  the saved points. A-10: the CDU's EXTRA plan holds the point with its elevation (the
  A-10's own row is B209).
- **Fail signatures:** the point is missing in the jet (Route section off, or the
  cartridge did not load); STPT N is a different point (the kneeboard and cartridge
  numbering drifted); the Hornet's route sequence lost its legs (our filled `NAV_ROUTE`
  and the `R2` flags disagree); the A-10 shows `EL: *****`.

### B136 — The DTC options do what the tab says: hand-load, skipped waypoints, your drawings · §102 · ☐ UNTESTED

The DTC tab was rebuilt per airframe on 2026-09-22
([retlab-my-aircraft-notes.md](design/retlab-my-aircraft-notes.md) §5).

- **Setup:** a player Viper or Hornet. DTC tab: Loading → "Pilot loads it"; untick Join in
  the waypoint list. Map: draw an area and save an orbit to the jet. Generate.
- **Pass:** the jet spawns with the cartridge in its DTC list but not loaded; loading it by
  hand works. The route has no join point, the numbers close up, and the kneeboard route
  table shows `-` on the join row. The area and the orbit show on the SA page (Hornet:
  the orbit in the CAP list) or the HSD (Viper).
- **Fail signatures:** the cartridge loads at spawn anyway (the `AutoLoad = false` flag is
  ignored); the jet's STPT numbers do not match the kneeboard after a skip; a drawing is
  missing (no free line slot, or the jet rejected the line).

### B137 — A Nevada kneeboard coordinate is the point the F10 map shows · kneeboard coordinates · ☐ UNTESTED

pydcs's `LatLng.format_dms` printed every S or W coordinate as a minus plus the
complementary minutes (115°18'W came out `-115°42'00"W`). The kneeboard now formats
with `game.coordinates.format_dms_suffix` (2026-09-22). Unit-tested; this row checks the
printed page against the map.

- **Setup:** Red Flag 81-2 (Nevada), any turn. Generate and open the kneeboard in the jet.
- **Pass:** the briefing page's `Bullseye:` line, a SEAD/DEAD target's Location column and
  a recon page's DMS column carry no minus sign and end in `N` and `W`. Hover the F10
  map (DMS readout) over the bullseye: degrees and minutes match the card's line. Same
  check on a Caucasus or Syria turn: the card reads as it did before the fix.
- **Fail signatures:** a `-` before the longitude; minutes that differ from the F10 map
  by the complement (`42'` against `18'`); `60"` in any seconds field.

### B138 — A pinned board number is the flight's, no other package wears it, and only X00 flies the CAG bird · §62 · ☐ UNTESTED

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the automatic half, and no livery choice to make.** The F-14B(U) squadron numbered 100–110 in sequence across six groups, the Hornets 200–211; no two jets shared a number. All eleven Tomcats wear `nawcwd 2000 buno 163223`, the squadron's only livery, including 100. No numbers were pinned, and a single-livery squadron has no CAG bird to misapply, so neither half the row names was tested.

The payload tab's **Set board number** pins the lead's modex; the wingmen follow in order.
Taking a number another flight has pinned moves that flight to the next free run, and generation skips pinned
numbers in every squadron sequence and re-rolls a random pydcs number that lands on one
(2026-09-23). Unit-tested; this row checks the jets in DCS.

- **Setup:** any carrier campaign with a Hornet squadron. Frag two Hornet packages. On the
  first flight, tick **Set board number** and enter 105 on a four-ship. On the second
  (a two-ship), pin 106: the tab says the first flight moved from 105 to 108. Frag a third
  Hornet flight on automatic. Generate.
- **Pass:** in the F2 view the second flight reads 106, 107 and the first 108-111. No other
  Hornet in the mission reads any of those. The automatic flight is numbered in the
  squadron block, skipping only the pinned numbers.
- **Livery half (2026-09-23 DM rule):** the Tomcat livery follows the board number, and the
  CAG / hi-vis livery is the X00 jet's alone. Frag a VF-143 F-14B(U) four-ship on automatic:
  jet 100 wears AG100, the other three AG106. Pin 103 on a VF-103 B(U) two-ship: jet 103
  wears AA103.
- **Livery names checked against the install 2026-09-23:** all 17 `livery_set` entries in
  the five F-14B(U) presets and F-14B VF-32 match a `.zip` under `CoreMods\aircraft\F14\Liveries`
  (`f-14bu`, `f-14b`). A jet in default paint is a picker fault, not a missing livery.
- **Fail signatures:** a pinned flight on random numbers; two jets sharing a number; the
  first flight still reading 105 after the second took 106; CAG paint on any jet not
  numbered X00.

### B139 — The front movement arrow points the way the line moved, and a held front has none · §90 · ☐ UNTESTED

**2026-09-23, test 39 turn 2** (Graveyard of Empires, `asdasd.retribution`, DM screenshots of the app map and the F10 map) — **no arrow, as designed.** The one front (`Camp Bastion/Shindand`) has `settled_progress` 89,864 m and `previous_progress` None: a new game's first settle has nothing to compare, so `movement_since_last_turn` is None and nothing is drawn. The row reads from turn 3.

An arrow at each front shows last turn's movement (2026-09-23). Unit-tested; this row checks
it against the saves. An app check across turns, not a flight. It is also B66's evidence.

- **Setup:** any campaign with an active front. Pass turn 1 (no arrow yet: nothing to compare).
  Set one front Aggressive and fly or skip-resolve two more turns. Note where the line sits on
  the map before each pass.
- **Pass:** from turn 3 the arrow at each front that moved points from where the line was to
  where it is, blue for a blue advance and red for a red one; the tooltip distance matches the
  shift you measured to within a mile; a front that held shows no arrow; a skipped turn clears
  the arrows. Unticking **Front lines** greys out **Front movement last turn**.
- **Fail signatures:** an arrow pointing against the line's movement; an arrow on a front that
  did not move; an arrow still showing after a skipped turn; red's stance in the tooltip.
### B140 — HQ priority targets: the panel names what a target is worth, and the planner leans to the top third · §103 · ☐ UNTESTED

Built 2026-09-23. Unit-tested; this row checks the app. An app check, not a flight.

- **Setup:** a campaign with several enemy factories or oil sites visible on the map (Red Tide or
  Anatolian Reach). Open three enemy targets you have engaged and one you have not.
- **Pass (panel):** an engaged target's **Why it matters** row gives its measure — enemy income a
  turn, front-line vehicles, the package ceiling, or equipment price — and `#N of M` among its
  kind; the unengaged one reads "Unknown (not engaged)"; a friendly target has no row.
- **Pass (planner):** with **HQ priority targets** off, note the auto-planned strike targets.
  Tick it, re-roll blue's ATO: strikes shift toward top-ranked targets of similar distance, never
  onto a site hidden on the map, and red's ATO is unchanged.
- **Fail signatures:** a price shown for an unengaged site; a hidden site in the ATO; red's ATO
  changing with the setting; a power plant pushed down the list.

### B141 — Packages route around a SAM ring that covers none of their targets · §69 · ☐ UNTESTED

**2026-09-23, test 39** (Afghanistan — Graveyard of Empires turn 1 (new game), 89 min, one human (Flash) in the PIG Strike F-15E lead from Kandahar, `Tacview-20260923-191751`, DCS 2.9.29.27468, main `44ecca53c` (#1069), `Desktop\New test\39`) — **the baseline, one build before the fix.** SABERTOOTH (Buk-M3, x=-115276 y=-298152) killed three `PORCUPINE Escort` F-15Cs at t=2199, 40–43 km from the site on ingress, and one `MONKFISH Escort` F-15C at t=3454, 47 km out at 10,900 m on egress. A re-fly on #1070 or later should show those legs bent round the ring. PIG, the human's package, is not this case: its target (Hashemi Bridge) is 14 NM from the S-350, so that ring covers the target and the package must enter it.

Built 2026-09-23 from Graveyard of Empires turn 1, where every deep package flew straight
through SABERTOOTH (Buk-M3, 38 NM) on the join-to-ingress and target-to-split legs. Replanned
headlessly: 2,349 NM inside the ring before, 113 NM after.

- **Setup:** any campaign with a SAM ring between your bases and a deeper target it does not
  cover (Graveyard of Empires: SABERTOOTH at Shindand, targets at Herat). RetLab planner suite
  on (or `route_around_sams`). Pass a turn, open a Herat strike's route.
- **Pass:** extra NAV points between JOIN and INGRESS and between the target and SPLIT take
  the route round the ring's edge. The package arrives on its TOT. Flown: the SAM does not
  engage the package on those legs.
- **Fail signatures:** the leg still cuts the ring (check the join is not deep inside it); the
  package reaches the IP late (the detour time is not in `join_time`); escorts and strikers
  split up at the detour (they should share the package's points); a detour through a
  neighboring country (the navmesh ignores borders).

### B143 — A player F-15E's JDAM CC missions match the kneeboard, and the flight radio is on the UHF radio · F-15E manual pass · ☐ UNTESTED

Built 2026-09-23 from the F-15E Manual v1.7 (5.7 radios, 13.4.7.4-5 CC missions). Unit-tested.

- **Setup:** a player F-15E Strike flight carrying GBU-38/31 against a target with more than 8
  aimpoints (a factory or oil complex), plus one waypoint added by hand in the flight plan.
  Air start or cold start. ~15 min.
- **Pass (CC):** on the Smart Weapons page, CC MEM, NEXT SET / NEXT MSN step through set 1 and
  set 2 as the planned targets; each matches the kneeboard Strike page's `(CC set/mission)`
  label. The hand-added waypoint is the first mission of the next set, not a duplicate of set 2.
- **Pass (radio):** UFC radio 1 (ARC-164) channel 1 is the flight frequency; radio 2 (ARC-210)
  carries ATC, AWACS, package and tanker presets.
- **Fail signatures:** a CC mission that will not transfer or is flagged invalid; two missions
  with the same set/mission number; a kneeboard label pointing at a different aimpoint.

### B144 — Radios, laser codes and nav points match the manuals on the Phantom, Mustang, Tomcat and Apache · manual pass · ☐ UNTESTED

Built 2026-09-23 from the module manuals. Unit-tested. Check whichever you fly; each is a ramp check.

- **F-4E:** COMM channel 1 is the flight frequency and you can transmit on it; the Pave Spike
  laser code on the Laser Coder matches the kneeboard code.
- **P-51D / P-47D:** Button B tunes the departure tower (VHF, e.g. 118.650 at Saint Pierre du
  Mont) and the tower answers; the kneeboard airfield row shows the same frequency.
- **F-14A Early / 95-GR:** ST and IP show on the TID for a Strike flight. Any Tomcat
  ground-spawned at a roadbase starts without a huffer.
- **Apache:** a data-cartridge T-point on a hill-top SAM cues TADS onto the site, not below it.
- **Fail signatures:** can't transmit on the flight frequency; pod laser 1688; a UHF frequency on
  a Mustang button; no ST/IP; a TADS cue buried in the hillside.

### B145 — A busy field's later departures spawn early enough to make their takeoff · §104 · ◐ PARTIAL (2026-10-11, test 55; was ☐ UNTESTED)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **the land half passes; the carrier deck is outside the rule.** The mission began 11:30 against a 12:00 turn clock, the 30-minute cap. Vaziani launched 14 F-22s: every lead was airborne before its planned takeoff, and the one flight queued behind the others (BARCAP|19) spawned at +6 min, its planned startup. Nothing spawned at 0:00:00 without a startup at that time. On CVN-72, 24 Hornets shared one startup (12:08:47); DCS released them to the deck over 9 minutes and the last flight was airborne 18 minutes after its planned takeoff. That is the accepted B17 deck behavior, not this row's.

Built 2026-09-23 from test 39: at Kandahar 34 jets spawned inside 10 min and the last got
off +19 min late; the human waited 12 min for taxi clearance. Always on. Unit-tested;
checked headless on a turn-2 save.

- **Setup:** a turn with many flights leaving one airfield inside a few minutes (Graveyard of
  Empires turn 1 at Kandahar, or red airdrome 7 on Syria). Open the flights at that field in
  the ATO and note their startup times.
- **Pass (app):** flights later in the departure order start earlier relative to their
  takeoff than the first one; a flight alone at its field keeps 8 min of ground ops.
- **Pass (app):** the past-start warning does not fire for a flight that needs to start up to
  30 min before the turn clock.
- **Pass (flown):** the mission clock at start is earlier than the turn clock by at most 30
  min. No group spawns at 0:00:00 unless its planned startup is that time. The lead of each
  group at the busy field is airborne within about 2 min of its planned takeoff, and
  packages reach their push points on time.
- **Pass (app, added 2026-09-27):** an ASAP package at the busy field keeps one TOT. Opening
  its package window, adding a flight or dragging a waypoint does not move the TOT back and
  forth, and Done raises no `RecursionError` (the one-shot estimate flipped between two
  times and the dialog re-saved each; unit-tested).
- **Fail signatures:** every flight at the busy field still gets 8 min; a group spawning at
  0:00:00 and flying late while the mission started less than 30 min early; the mission
  starting more than 30 min early; flights airborne well before their takeoff and holding
  (45 s per jet is too slow for that field); jets spawned early block the taxiway for flights
  ahead of them in the queue; next turn's clock or weather jumping by the shift.

### B146 — Civil departures spread across the mission instead of all leaving at the start · I2 civilian traffic · ◐ PARTIAL (2026-09-29, test 47; was ☐ UNTESTED)

**2026-09-29, test 47** (Persian Gulf turn 1, 59 min) — **staggered, but not matched to the plan.** Two civil ground starts appeared: a Mi-8 at t=8 and an SA342M at t=2139. No other civil aircraft stood on a runway at t=0; the rest were air starts. The `.miz` Brady kept is a later regeneration of the turn with different civil flights, so no departure can be checked against its own ETA. Needs a flight where the kept `.miz` is the flown one.

Built 2026-09-23 from test 40. A ground-started civil flight draws a delay of 0–6,600 s. It was
written to the group's `start_time`, which DCS overwrites from the first waypoint's ETA on load,
so every departure left in the first minute. The delay is now the first waypoint's ETA as well.
Unit-tested (`test_a_staggered_departure_is_written_where_dcs_reads_it`).
- **Setup:** any campaign with civilian traffic, a turn of 30 min or more. Spectator is fine.
- **Pass:** civil ground departures appear through the mission, each at its group's first-waypoint
  ETA; only zero-delay civil flights are on a runway at t=0.
- **Fail signatures:** every civil ground start present at t=0 again (the ETA not written);
  a delayed group that never appears (DCS rejecting a runway start with an ETA — search
  `dcs.log` for the group name).
- **Also:** no civil IL-76 takes off from a field above 2,000 m (on Afghanistan: Bamyan,
  Gardez, Chaghcharan, Sharana, Ghazni); any IL-76 routed there appears airborne en route.

### B147 — A TARCAP reaches the target with its package's SEAD, not ahead of it · §69 · ☐ UNTESTED

Built 2026-09-23 from test 40, on the DM's call. Upstream starts TARCAP 2 min before the
package's join, over the target; SARDINE's four F-15Cs sat 5 NM from an SA-11 for 17 minutes
before their SEAD and all died. With `tarcap_behind_sead` on (RetLab planner suite) the orbit
starts no earlier than the package's first SEAD/SEAD Sweep/SEAD Escort/DEAD TOT. Unit-tested.
- **Setup:** RetLab planner suite on; any turn where the planner frags a package with both a
  TARCAP and a SEAD flight (common against a SAM target). Read the ATO; a spectator run shows it.
- **Pass:** the TARCAP's patrol start time is at or after the SEAD flight's TOT; in the
  recording the TARCAP arrives over the target with or after the SEAD, not alone.
- **Fail signatures:** the TARCAP still starts before the join (the gate off, or the setting
  missing from the suite); a TARCAP that takes off so late it never reaches station before the
  package splits.

### B148 — A 3rd Khordad and a Bavar-373 site spawn, join Skynet and engage · §105 · ◐ PARTIAL (2026-09-26, dcs.log; was ☐ UNTESTED)

Repo side built 2026-09-25. The mod is its own private pack (`BradySox/RetLab-Iran-Air-Defense`),
built 2026-09-26: 12 units, 11 models with own wrecks, the three missiles. Never loaded in DCS;
its `tools/check_entry.py` runs the Lua against stubs only.
- **First load, before any flight (~10 min):** Mission Editor, place one of each `[IRAD]` unit.
  Each shows its painted model (not pink or white) in the editor and the encyclopedia; set
  one to red alert and watch the launcher erect, arrays raise, masts extend and radars turn;
  drive a truck and watch the wheels turn forward and the front axle steer; destroy one and
  get its burnt wreck, not a vanilla S-300 or Buk.
- **First-load fail signatures and where the fix is:** a part moving backwards or the wrong
  distance (the argument range in the pack's `Source/models/export_edm.py`); a Sayyad leaving
  its canister sideways (the `LAUNCH_n` connector axis, same file); a pink or white model (a
  texture missing from the pack's `Textures`); see-through or shadowless panels (the
  material setting the exporter logged errors on).
- **Setup:** the RetLab Iran Air Defense Pack installed; New Game with `[CH] Iran 2025` as red
  (the only faction with the Sayyad-4B and the Bavar-373-II since 2026-09-29) and the pack's
  toggle ticked. Buy or find one of each site, a Bavar-373-II included. Fly a Viper or Hornet with HARMs.
- **Pass:** both sites spawn with every vehicle; `dcs.log` shows Skynet adding a `3rd Khordad`
  and a `Bavar-373` site; each engages inside its range (27 NM and 81 NM, 108 NM for a
  Sayyad-4B launcher); a HARM on one STR leaves a Bavar-373 site (two STRs) still able to fire.
  The Bavar-373-II has one STR guiding all six TELARs (DM call 2026-09-27), so a HARM on it
  silences that site.
- **Fail signatures:** a vehicle missing from the site (a type id that does not match the
  mod); `dcs.log` naming an `IRAD_` type as unknown; a site that never goes live (Skynet
  entry not matched); Alam al-Hoda TELs that never fire while the TELAR is alive; a launcher
  turret facing backwards (the pack's `reference_angle_Y`, not Retribution's `reversed_heading`).
- **Result 2026-09-26 (partial, from a Retribution mission's `dcs.log`):** every unit spawned (a
  3rd Khordad battery, a Bavar-373-II battery, 3 Matla ul-Fajr, 12 Rasool); Skynet took the
  3rd Khordad as a SAM site, the Bavar-373-II as SAM-as-EWR (the S-300/Patriot treatment) and
  the Matla ul-Fajrs as EWRs; zero errors name the pack. DCS screenshots then caught two pack
  bugs, both fixed in the pack the same day: the Meraj-4's array hit box exported as a black
  slab, and both Buk-family turrets spawned facing aft (a copied vanilla `reference_angle_Y`).
- **Test 41 (2026-09-26, Tacview):** the 3rd Khordad site **engaged and killed**: 11 Taer-2B
  at F-14B BARCAPs, 5 kills (each missile ending ~500 m from an F-14 in the second it died);
  the 4 earliest shots, near the 27 NM limit, flew 22-26 NM and fell short, as they should. No
  pack unit died; no pack error in `dcs.log`. The Bavar-373-II fired nothing: no blue aircraft
  came closer than 95 NM (inside the Sayyad-4B's 108 NM only at altitude; 43 NM low), so it is
  **untested, not failed**.
- **Test 42 (2026-09-26, Tacview):** three 3rd Khordad batteries fired 19 Taer-2B, about 4
  kills. The Bavar-373-II **engaged but failed**: 26 Sayyad-4B, one every 3 s, each dead within
  6-14 s and 2.2 NM (the 14 s ones at motor burnout); the DEAD package then destroyed the site.
  Cause: the 4B was declared a plain SAM with an active seeker and no lock range. Fixed in the
  pack the same day (active-seeker fields, as HDS's working 40N6); **unflown**. No pack error in
  `dcs.log`.
  Still owed: a Bavar-373 engagement that reaches its target, and the HARM-on-one-radar check.
- **Fail signature:** Sayyad missiles dying within ~15 s of launch, one after another = the
  missile definition in the pack's `Database/irad_missiles.lua`, not the site.
- **Test 43 (2026-09-26, Tacview):** with active-seeker fields and a loft, all 24 Sayyad-4B flew
  straight up (~90,000 ft at 20 s, 1.5-7 NM downrange) to ~328,000 ft: no guidance command at all.
  The 4B is now **command-guided** in the pack, like the Sayyad-4 and ED's S-300 (DM call);
  unflown. A Sayyad that climbs vertically without turning = no guidance, not too much motor.
- **Test 44 (2026-09-26, Tacview):** command-guided, the 4B failed the same way: 24 launches, each
  dead in 6-26 s. Root cause, measured: every Sayyad salvo in tests 42 and 44 began with the target
  at **118 km**, the TELAR radar's 120 km edge and beyond its ~102 km lock, so no missile was ever
  guided. Fixed: firing range capped inside the guiding radar's lock (TELAR 95 km, 4B TEL 160 km);
  RetLab's pydcs threat ranges lowered to match (51 / 86 NM). Unflown.
- **Test 45 (2026-09-26, Tacview):** the range cap loaded (DCS started after the pack commit) and
  changed nothing: the first salvo still began at 118 km, against an F-16 closing at ~800 km/h. So
  test 44's cause was wrong. 24 Sayyad-4B from the TELARs; 18 died within 6-22 s, most at 6 s
  while still vertical (~5,000 ft, 0 NM downrange); never more than ~2-3 alive at once. The 6 that
  flew on went 54-65 NM and passed 7-18 km from F-16s; no hits. The 3rd Khordad sites fired 16
  Taer-2B from 56 km inward and killed an F-16 of the DEAD flight.
  Cause, found by diffing against ED's S-300 TR: the TELAR's mast radar had **one** target
  channel (two missile slots); ED's has six. Fixed in the pack (five inherited tracker channels,
  as the STR already had); unflown. The range cap stays.
- **Test 46 (2026-09-27, Tacview):** DCS started after the six-channel commit, and the TELARs
  failed the same way, so test 45's cause was wrong too. 24 Sayyad-4B: 19 died at 6, 10 or 14 s,
  each salvo together about 6 s after its last launch, youngest first, with no HARM in the air.
  The 5 that flew on left the canister vertically, were still climbing at ~60° at burnout (14 s,
  ~40,000 ft) and coasted to 101,000-128,000 ft. Each crossed an F-16's ground track 0.6-0.8 km
  away at ~100,000 ft and ended 3-46 km from any aircraft; no hits.
  Cause, found by diffing against ED's 48N6 (`TechWeaponPack`, `s300_s400_family.lua`):
  ModelData[13], the angle of attack available by thrust vectoring, is 1.0 there and was 0 on
  ours, so a cold-launched Sayyad could not turn over until it had airspeed. Fixed in the pack;
  the salvo deaths should go with it (the fire control abandoning missiles that cannot reach),
  to be confirmed. Also from 2026-09-27: the TELAR is a launcher the STR guides (DM call), so the
  channel fix went with its radar. Unflown.
- **Fail signature:** a Sayyad still climbing at ~60° at motor burnout (~14 s) and coasting to
  100,000+ ft = no thrust vectoring (the pack's ModelData[13]), not the radar or the range. A
  salvo dying together a few seconds after its last launch, with no HARM in the air, is most
  likely the same fault.

- **Test 48 (2026-09-30, `dcs.log` debug run):** a Bavar-373 site with six Sayyad-4 TELs was live
  and weapons free all mission (Skynet `ACTIVE: true`, up to 24 targets); its STR locked a Hornet
  from 56 NM in, closest 22 NM at ~20,000 ft, inside the Sayyad-4's 32-81 NM. No Sayyad-4 fired.
  RetLab and Skynet are cleared. DM call the same day: one Bavar-373, the TEL firing the Sayyad-4B
  (the missile that fired in tests 42-46); the Sayyad-4, the 4B TEL and the Bavar-373-II TELAR
  were removed. Unflown.
- **Test 49 (2026-09-30):** after the one-launcher change the TELs still lay in travel all
  mission. In the Mission Editor, set to red alert at spawn, they raised. RetLab now spawns a
  Bavar-373 site on red alert (`ALARM_RED_AT_SPAWN`); Skynet still keeps its radars off. Unflown.
- **Test 50 (2026-09-30):** red alert at spawn and ED's full 5P85D deploy sequence changed nothing:
  the TELs stayed down with Skynet off too. Tacview: every TEL at the site sat at 6-14 deg of
  pitch or roll on a hillside, past the 5 deg level limit copied from the 5P85D; on flat ground
  they raised. The pack now levels 15 deg (pack PR #11). **Re-run: the TELs raised to ready to**
  **fire.** Still owed: a Sayyad-4B shot that reaches its target.
- **Test 51 (2026-09-30, Tacview):** with the TELs raised the site **engaged and killed**: 24
  Sayyad-4B at Hornets of a DEAD package, one kill (the missile ended 0.03 NM from a DEAD Hornet).
  The first six launched near 55 NM, flew 94 s and never came within 22 NM; eight died 6-26 s
  after launch, as in tests 42-46. Still owed: a better hit rate, and the HARM-on-the-STR check.
- **Test 52 (2026-10-06, Tacview):** Sayyad-4B on HDS's 48N6E2 numbers: 24 fired, **4 kills**
  (the last salvo, each missile within 0.03-0.34 NM of its Hornet) and a 0.36 NM near miss. No
  shot climbed above 79,000 ft; every guided one turned down onto its target. Still owed: 15
  missiles died 6-50 s after launch while still climbing. The second salvo (11 in 33 s at
  Hornets 47 NM out) was destroyed together ~7 s after its last launch, with no blue weapon
  near it and every radar alive.
- **Test 53 (2026-10-06, logging run of test 52's mission, STR at 8 channels):** 23 Sayyad-4B, 0
  kills. Every lost missile's target went to none, then the missile was destroyed 2-4 s later; each
  loss lines up with its Hornet beaming (70-95 deg off the radar) or turning away while dumping
  chaff (171 bundles in 10 s around the first batch). Test 52's four kills came at Hornets flying
  straight in. Cause: the AI's defense breaks the STR's lock, as DCS intends. DM call 2026-10-06:
  leave it. Not Skynet and not the channel count; the pack's STR stays at 8 channels.
- **Fail signature:** Sayyads destroyed mid-flight with their target set to none = the targeted jet
  beamed or chaffed the STR off; read the jet's aspect and the chaff in Tacview before blaming the site.
- **Fail signature:** TELs that never raise = the ground tilts them past `maxDeviationPitch`/`Roll`;
  read each unit's pitch and roll in Tacview before anything else.
- **Fail signature:** a Bavar-373 site whose STR tracks a target inside 86 NM and never fires =
  the Sayyad-4B's numbers in the pack's `Database/irad_missiles.lua`, not the site.

### B150 — Insert NAV point finds a leg beside the selected waypoint · §106 · ☐ UNTESTED

Built 2026-09-27 from the DM's report: a Strike's NAV after the Join refused an insert. The old
rule knew only the transit legs; the new one tries every list and keeps a slot only if the point
lands next to the selected waypoint. Unit-tested (`test_nav_insert.py`).

- **Setup:** any turn, a player Strike flight with escorts. Edit flight → Waypoints.
- **Pass (app):** Insert NAV point with each selected, and the new row appears where named:
  Join → right after the Join; the NAV (line-up) before INGRESS → right before it; the last
  STRIKE target → right after it; Split with a Refuel after it → right before the Split; Hold
  → right after the Hold. The new row is selected. On a strike with other flights, Join and
  the target ask Whole package / This flight only first.
- **Pass (app):** INGRESS, a target that is not the last, Takeoff before a Hold, Bullseye and
  Divert say "No room for a NAV point" with the reason.
- **Pass (app):** Move Up / Move Down reorder two NAV points between the Join and INGRESS.
- **Fail signatures:** a new point on the far side of a fixed waypoint (the map route zigzags
  back through it); an insert that changes nothing in the list; the old "Could not insert a
  new waypoint" message.

### B151 — The package route moves every flight in the package · §106 · ☐ UNTESTED

Built 2026-09-27 from the DM's ask: "there should be a package waypoint edit". The package
owns its join-to-IP and target-to-split NAV points. **2026-09-28:** the DM found the window
could not move a point ("I wanna move the points on the map"); routes are now edited on the
map from any flight of the package. Unit-tested (`test_package_route.py`,
`test_route_edit.py`, `test_package_route_dialog.py`, the client's `FlightPlansLayer.test`);
never used in the app or flown.

- **Setup:** a Strike package with an Escort and a SEAD Escort (all fixed-wing). Select the
  **escort** in the ATO so its route is the one on the map.
- **Pass (map):** double-click the route between the join and the IP: a NAV point appears
  there on all three routes. Drag it off the line: all three follow. Right-click it →
  **Delete it from every flight**: gone from all three.
- **Pass (map):** double-click a transit leg (hold to join): the point is on that flight only.
  Double-click between the IP and the target: a popup says the plan flies that leg straight.
  Right-click the Join: it says to drag it instead.
- **Pass (map):** drag the escort's Join: every flight's join moves with it.
- **Pass (app):** Package window → Package route opens on the first row with Insert enabled.
- **Pass (app):** the table reads Join, the way-in NAVs, Ingress (IP), Target, the way-out
  NAVs, Split, and Flown by names the three flights. Insert NAV point after Join: every
  flight's Waypoints tab shows the new NAV between its Join and its IP, and the map draws it
  on all three routes. Delete and Move act on all three. Reset to planned route puts back the
  planner's detours.
- **Pass (app):** drag a NAV on the map and click back into the Package route window: it
  shows the new coordinates.
- **Pass (app):** with ASAP on, the TOT updates once after each edit and stays put.
- **Pass (app):** add a flight to the package after the edit: its route has the same NAV.
- **Pass (flown):** the package flies the edited route and meets at the join together; the
  escorts stay with the strikers through the added point.
- **Fail signatures:** one flight without the point (it was not counted as flying the route);
  the escorts reaching the join minutes before or after the strikers (join times out of step);
  a new flight flying the planner's detour instead of the edited route; the TOT flipping; a
  double-click that zooms the map instead of adding a point; the browser's own menu on a
  right-click.

### B152 — A tanker flies its track at the set orbit speed · upstream #869 · ◐ PARTIAL (2026-10-09, Kola Tacview; was ☐ UNTESTED)

**2026-10-09** (Kola, KC-135 at 20,000 ft, **280 KIAS** set, on the tanker box since removed) — the value reached the mission and the tanker flew it.
- The `.miz` carried 192.7 m/s on the track points: 374.6 KTAS, which is 280 KIAS at 20,000 ft.
- Tacview ground speed: 369 kt on the 325-degree leg and 384 kt on the 145-degree leg, 376 kt mean.
- Still owed: the cockpit reading beside the tanker (the pass is in KIAS), and a saved default reaching a new flight.

Built 2026-09-28 from upstream issue #869; made per flight the same day (DM: "never a
theatre option. Per airframe"). A tanker flight's Payload tab → **Set orbit speed**
replaces its own track speed with the chosen KIAS, converted to true airspeed at the track
altitude; **Save as default** stores it per airframe (§43). A carrier recovery tanker
ignores it; a tanker is capped at its top speed. Unit-tested
(`test_tanker_orbit_speed.py`, `test_flight_defaults.py`); never flown.

- **Setup:** any campaign with a KC-135 or KC-135 MPRS theater tanker. Open its flight →
  Waypoints → tick Set orbit speed, set 270 KIAS, generate the turn. (The control moved
  from the Payload tab 2026-09-29, row B170.)
- **Pass:** join the tanker; its indicated airspeed on the straight legs reads 265-275 KIAS.
- **Fail signatures:** the tanker at its old ~300 KIAS (the value not reaching the
  waypoint); a speed far off 270 (the TAS conversion is wrong for DCS's atmosphere); a new
  KC-135 flight not picking up a saved default.

### B154 — A carrier moved with the instant move cheat launches from its new spot · cheat · ☐ UNTESTED

Built 2026-09-29 on the DM's ask. Settings → Cheats → **Enable Instant Carrier and Ship
Move Cheat**: a carrier or ship dragged on the map moves as soon as it is dropped, with no
range limit, and only the destination has to be open sea. Flights from the boat, and
flights whose target is the boat or ship, are replanned; threat zones are recomputed.
Unit-tested (`test_instant_naval_move.py`, `test_tgo_movement_routes.py`); never flown.

- **Setup:** any campaign with a blue carrier. Tick the cheat, then drag the carrier about
  200 NM out to sea on the map.
- **Pass (map):** no move line or ghost marker; the carrier and its escorts sit at the new
  spot; clicking it opens its base menu; its flights' routes start there.
- **Pass (flight):** generate; the carrier group spawns at the new spot and its flights take
  off from the deck and fly the new routes.
- **Fail signatures:** the carrier snaps back or waits for turn end (the cheat did not
  apply); the marker will not open its menu until the map reloads (stale drag state); a
  flight's first waypoint at the old spot (not replanned); the escorts left behind.

### B155 — The briefing screen shows the RetLab picture, or your own briefing.png · §107 · ☐ UNTESTED

Built 2026-09-29. Unit-tested (`test_briefing_image.py`); never loaded in DCS.

- **Setup:** start RetLab. Generate any mission with no `briefing.png` in
  `Saved Games\DCS\Retribution`. Load it in DCS. Then copy a picture there as
  `briefing.png`, generate again, load it.
- **Pass:** the app's startup splash and the first load both show the dark RetLab picture
  with the F-16; the second load shows yours.
- **Fail signatures:** the old Ghost of Kyiv picture (the change is not in the build); a
  blank picture box (DCS could not read the file — try a JPEG).

### B156 — A carrier keeps the same TACAN every time the mission is generated · §65 · ◐ PARTIAL (2026-10-11, test 55; was ☐ UNTESTED)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **the same channel on two generations, on a map without the collision.** This turn was generated at 16:07 and again at 17:02: CVN-72 72X, LHA-1 41X, Kuznetsov 36X both times, ICLS and Link 4 unchanged. Caucasus has no hull channel to collide with, so the Persian Gulf and Afghanistan case is still owed.

Built 2026-09-29 from test 47. Where a map owns a carrier's hull channel, the boat's TACAN
flipped between two neighbours on every generation (CVN-71 on Persian Gulf: 69X, 72X, 69X).
The mission generator reserved the boat's own last value before re-deriving it. Unit-tested
(`test_auto_tacan_is_stable_across_generations`).
- **Setup:** Persian Gulf with CVN-71, or Afghanistan with the Stennis. Generate the turn,
  note the TACAN on the CV Operations Data page, generate again.
- **Pass:** the same channel both times (CVN-71 on Persian Gulf: 72X; Tarawa: 41X).
- **Fail signature:** the channel moves by one or two each generation.
- **Also:** a TACAN set by hand in the carrier's base dialog is kept.

### B157 — A carrier joins its side's Skynet as a radar · §65 / Skynet · ☐ UNTESTED

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **not exercised.** `dcs.log` has no `EW Radar that does not exist` line, but neither side's IADS data named a ship in this campaign (blue: one SHORAD group; red: ten EWR entries, none the Kuznetsov), so nothing reached the renamed-flagship path. Needs a campaign whose IADS network lists a carrier.

Built 2026-09-29 from test 47's `dcs.log` (the line is in tests 43 and 46 too): §65 names
the flagship by its hull, but the IADS data still sent Skynet the id-prefixed theater unit
name, so no carrier or LHA ever joined. The IADS data now uses the name the ship was
generated under. Unit-tested (`test_iads_renamed_flagship.py`).
- **Setup:** any campaign with a carrier or LHA. Generate and fly.
- **Pass:** `dcs.log` has no `EW Radar that does not exist` line naming a carrier or LHA.
- **Fail signature:** that line again = a ship renamed where the IADS data does not see it.

### B158 — The debrief grades each flight, and the grades match what happened · §108 · ☐ UNTESTED

Built 2026-09-29. Unit-tested (`test_flight_grades.py`); never read after a flown mission.

- **Setup:** fly any turn with a player strike or SEAD flight and let a few AI packages fly.
  Accept the results. Note your actual time at the target and what you hit.
- **Pass:** the debrief has a Flight report cards box, your flight first. Your card's timing
  matches when you reached the ingress point (within about a minute; the join point for an
  escort, the station for a CAP), the package target count matches the map, and shots and
  hits match what you released. A flight that fired Harpoons or HARMs from range is not
  marked "Never reached".
- **Fail signatures:** no box at all (no sortie records reached `state.json`, see §91); every
  flight "Never reached the target area" (the TOT waypoint or mission start is off, check
  §104's early start); timing out by exactly the early-start shift (planned TOT measured from
  the wrong clock).


### B159 — A target steerpoint in the hills sits on the ground · §74 · ☐ UNTESTED

Built 2026-09-29. The data cartridge gave a target steerpoint the nearest airfield's
elevation, so in hills it sat hundreds of metres above or below the target. Where a
`resources/terrain_heights/<terrain>.npz` grid ships, it now carries DCS's own
`land.getHeight`, bilinear on a grid of 100 m to 1 km by terrain. Unit- and harness-tested; the grids come
from `scripts/dcs_terrain_heights.py`. Design: `retlab-dtc-cartridge-notes.md`.

- **Setup:** Syria (the finest grid, 100 m) or any terrain whose grid ships. A Viper or Hornet flight with the cartridge on
  (DTC tab, load at spawn), fragged on a target on high ground well above the nearest
  field.
- **Pass:** the target steerpoint's ELEV is within about 30 m (100 ft) of the ground at
  the target, and a pod slaved to it looks at the target, not short or long.
- **Fail signatures:** ELEV reads the nearest field's elevation (no grid loaded: check the
  terrain name matches the .npz file name); ELEV reads 0 (point off the grid and no field
  on the map has a record).

### B160 — Every settings row reads as one line: shading, dividers and a hover band · settings UI · ☐ UNTESTED

Built 2026-09-29. Filter and disclosure tests pass with the painting in place; rendered offscreen, never looked at in the running app.

- **Setup:** open Settings with the window maximised. Visit Performance, then two other pages.
  Open a section's Show N advanced options, then type a word in the search box.
- **Pass:** every other row is shaded, a thin line sits under each row, and the row under the
  mouse lights across its full width with an accent bar on the left, whether the cursor is
  on the label, the control or the gap between them. Opening advanced options or searching
  keeps the shading alternating on the rows actually shown.
- **Fail signatures:** bands stacked at the top of a section (geometry read before layout); a
  hover band that stays lit after the mouse leaves the section; two shaded rows in a row after
  a search.

### B161 — Untasked parked aircraft spawn only at airfields a player sees · Culling settings · ☐ UNTESTED

Built 2026-09-29; made the default the same day (the two boxes now mean "at every
airfield"). Unit-tested (`test_untaskedculling.py`); never generated in DCS.

- **Setup:** Settings → Mission Generator → Culling & untasked units: leave **Disable
  untasked OWNFOR aircraft at every airfield** and **Disable untasked OPFOR aircraft at
  every airfield** unticked. Fly a player flight whose route passes one enemy airfield and
  stays well clear (more than 20 NM) of another.
- **Pass:** your departure field's ramp and the enemy field beside your route hold their
  parked aircraft; the far enemy field has none (F10 map or the Mission Editor). Tick both
  boxes and generate again: every ramp is empty.
- **Fail signatures:** every field full (the rule found no player flight — check the flight
  has a client slot, and that dynamic slots and OPFOR client slots are off); your own ramp
  empty with the boxes unticked.


### B163 — The kneeboard drops its dead lines, and LOADOUT counts what the jet carries · §22 · ☐ UNTESTED

Built 2026-09-29. Checked on a headless Long Road to H3 deck (8 player flights); never read in DCS.

- **Setup:** an Apache flight with Hellfires and rockets, any jet with drop tanks, and a
  flight with no divert field. Generate friendly packages kneeboard page on.
- **Pass:** the Apache LOADOUT line matches the payload screen (eight Hellfires read `8×`,
  not `2× AGM-114L * 1`), tanks read `fuel tank`, the SAR line is one line, Mission Info has
  no empty Divert row, and Friendly Packages has no second heading under its title.
- **Fail signatures:** a count that disagrees with the payload screen; a table cut off or a
  page that now spills (the lines removed should only free space).


### B164 — A changed livery is still selected when the flight is reopened · Payload tab · ☐ UNTESTED

Built 2026-09-29. Unit-tested offscreen (`tests/test_livery_selector.py`); never clicked in the running app.

- **Setup:** any campaign. Open a player flight → Payload, pick a livery other than the
  squadron's, close the flight window, open it again. Then generate the mission.
- **Pass:** the Payload tab shows the livery you picked; the Mission Editor (or the jet on the
  ramp) wears it on every member.
- **Fail signatures:** the tab shows the squadron's livery again (the sync is not running);
  the tab is right but the jet wears the squadron's livery (the generator is reading the
  squadron, not the member).


### B166 — The pack's own Iranian missile sites spawn and fire · §105 · ☐ UNTESTED

Built 2026-09-29: the RetLab Iran Air Defense Pack's Sejjil-2, Emad, Kheibar, Fattah-2 and
Shahed 238 launchers replaced the third-party ones (B149), behind the pack's own toggle.
`[CH] Iran 2025` fields all five as missile sites (`[CH] Iran 2020` the Sejjil-2 and Emad since
2026-09-29), `Iran 2015` the Sejjil-2. Unit-tested
(`tests/retlab/test_iran_pack_missiles.py`); the missiles have never flown in DCS.

- **Setup:** the pack installed; Scenic Route Merged or Noisy Cricket (both preseed the pack),
  or any campaign with red missile-site markers and `[CH] Iran 2025` as red with the pack
  ticked. Missile-site fire tasks on (Settings, Performance).
- **Pass:** red missile sites spawn with `[IRAD]` launchers; each fires once at a blue base;
  Tacview shows the missile reaching a blue field. A Shahed 238 flies at about 370 mph and takes
  most of the mission to arrive.
- **Fail signatures:** a missile site with no vehicles (a type id that does not match the pack;
  `dcs.log` names it); `Couldn't setup missile site to fire` in the Retribution log (no blue base
  inside the launcher's range); a launcher that erects and never fires, or a missile that falls
  far short (the pack's `Database/irad_ssm.lua`, not RetLab).
- **Test 48 (2026-09-30, Tacview):** 20 Emad and 24 Sejjil-2 fired, 108-452 NM. Each peaked at
  ~6,000 kt within 30 s, topped out at 104,000-172,000 ft and glided in at ~5° (DCS's old
  missile model), and every shape flew 90° sideways. Fixed in the pack the same day: shapes
  exported nose-forward, and the four ballistic missiles moved to ED's ballistic model with
  motors sized for 150-900 km (DM call). RetLab now fires them only at fields 81-486 NM away.
  Unflown.
- **Pass (from 2026-09-30):** a steep climb, a lofted arc, a steep dive onto the field; flight
  time 9-11 min. **Fail signatures:** a shot that still flies flat (the scheme did not load:
  `dcs.log` near the weapon name), or lands long or short (the pack's `LOFT_PITCH` and
  `LOFT_FTIME` tables).
- **Tests 49-50 (2026-09-30, Tacview):** our own motors on ED's scheme first lofted past
  2,000,000 ft, then (depressed tables) flew into the ground under power 23-73 NM out. DM call:
  fly ED's 9M723 Iskander exactly. All four now carry it field for field, 75-400 km; RetLab
  fires them at fields 40-216 NM away. Unflown.
- **Pass (from test 51):** an Iskander-like arc, Mach 5-6, landing on the field. **Fail
  signatures:** a shot into the ground short of the field, or one far above 200,000 ft (the
  pack's `Database/irad_ssm.lua` has drifted from ED's `Iskander_Unitary`).
- **Test 52 (2026-10-06, Tacview):** on ED's Iskander path, 17 Emad and 21 Sejjil-2 flew
  56-206 NM in 150-300 s, peaking near 4,000 kt and topping out at 36,000-275,000 ft, then
  dove in. Each three-round salvo landed within ~0.1 NM of itself; impacts sat 0.02-1.1 NM from
  the targeted carriers, a Patriot site and an armour group (RetLab aims at the field's spot
  plus up to 1.35 NM of scatter). **Passes.**
### B167 — Every SAM site spawns one guidance radar, and SA-5/SA-2 sites twice the launchers · §60 removal · ◐ PARTIAL (2026-10-11, test 55; was ☐ UNTESTED)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **one guidance radar on the sites this campaign has.** Two S-300 sites (one 30N6 or 40B6M each), one SA-6 (one 1S91) and three SA-11 sites (no separate track radar). No SA-5 or SA-2 in this campaign, so the doubled-launcher half is not shown, and nobody looked at the sites for a launcher inside another unit.

Built 2026-09-29 on the DM's call: §60's second guidance radar removed from every SAM layout, and
the SA-5 layouts doubled to 16 launchers (circle) or 12 (semicircle, and Red Tide's battalions),
the SA-2 Battery layouts to 8 or 12 and the mixed site's SA-2 slot to 6, on their own templates. Layout-tested; never generated in DCS.
- **Setup:** a new game with an SA-5 and an SA-2 or SA-6 site on the enemy side (Persian Gulf with
  Iran, or Red Tide). Generate a turn.
- **Pass:** each SAM site has one track radar (the Patriot keeps two STRs); an SA-5 site has 16 or
  12 launchers and an SA-2 battery 8 or 12, none inside another unit or a revetment; the SA-5 fires at a jet inside its range.
- **Fail signatures:** a launcher spawned into another unit (the extra ring is too close); an SA-5
  that still never fires at close targets (the cause was not the second Square Pair; see test 47's
  SA-5 finding).
### B168 — Naval gunfire hits your marker, and the Super Gaggle's F-4s are armed · §34 / §37 / COIN · ☐ UNTESTED

Built 2026-09-29 from the Vietnam Ops and COIN audit. Harness-tested (`tests/lua/test_vietnamops_runtime.py`, `TestNavalGunfire`, `TestSuperGaggle`); never flown.

- **Setup:** Yankee Station with Naval gunfire, FAC(A) marking and Super Gaggle on. After the gaggle launches (10 min in), place an F10 marker on a coastal target inside 10 NM of a gun ship and call Naval Fire Mission → Fire on last F10 map marker. Watch the suppressor pair over the outpost in Tacview.
- **Pass:** the shells land on your marker; the suppressors spawn with bombs and rockets on the pylons and release on the guns around the outpost.
- **Fail signatures:** the shells land on the gaggle or on a FAC's white-smoke target (the mark filter missed); the suppressors spawn clean or with no fuel (the payload did not reach `coalition.addGroup`).

### B174 — A Strike or DEAD flight has one target steerpoint per site · flight plans · ☐ UNTESTED

Built 2026-09-29 after an F-16C DEAD on an S-300PS site planned 18 target steerpoints (WP 5-22), one per unit. Strike and DEAD now plan one steerpoint at the site center; SEAD keeps one per emitter. Unit-tested; never flown.

- **Setup:** a player F-16C or F/A-18C DEAD flight on a SAM site with Target intel precision on Exact, and a player F-14B(U) Strike flight with JDAMs. Generate a turn.
- **Pass:** each flight has one target steerpoint at the site; the Strike kneeboard page lists every building with coordinates under that one STPT; the Tomcat's JDAM page still has one point per building; the briefing's waypoint times show whole seconds.
- **Fail signatures:** a steerpoint per unit (an old save's plan: re-plan the flight); the Tomcat's JDAM points all on the site center; the package arriving at the split earlier than its planned time (the dwell stopped counting units).
### B172 — A new flight's cartridge waits for the pilot to load it · §74 · ☐ UNTESTED

Built 2026-09-29 on the DM's call: new flights default to Pilot loads it. Tested offscreen (`tests/test_dtc_tab.py`); never flown.

- **Setup:** pass a turn with DTC data cartridges on, and take a player Viper or Hornet cold without touching its DTC tab.
- **Pass:** the flight's DTC tab reads Pilot loads it; in the jet the cartridge is listed on the DTC page and nothing is loaded until you load it; loading it brings in the route and the rest.
- **Fail signatures:** the cartridge loads itself at spawn (the default did not reach the unit); the cartridge is missing from the jet's list.
### B169 — Tankers, AWACS and the first BARCAP wave are on station from mission start · §6 · ◐ PARTIAL (2026-10-11, test 55; was ☐ UNTESTED)

**2026-10-11, test 55** (Caucasus — Vectron's Claw turn 1 (new game), no player slot, 82 min of sim at acceleration, `Tacview-20261011-160744`, DCS 2.9.30.28738, main `fd3809cac` (#1208), `Desktop\New test\55`; the flown mission is the archive copy stamped `20261011-160700`, the folder's `.miz` is a 17:02 regeneration) — **the first-wave half passes; no relief wave to compare.** In the save every tanker, AWACS and BARCAP package is ASAP. The mission started 30 min early (B197) and all six tankers and AWACS were on their tracks at 11:30; every first BARCAP wave was airborne by 11:40. Each station had one wave (60-minute CAPs), so the relief-wave line is not shown.

Built 2026-09-29 on the DM's call: every auto-planned tanker and AWACS package, and each station's first BARCAP wave, is an ASAP package. Tankers used to be spread at random through the mission. Unit-tested (`tests/commander/test_support_asap.py`, `tests/test_missionscheduler.py`); never flown.

- **Setup:** any campaign with a theater tanker and an AWACS. Auto-plan a turn and open the ATO before flying.
- **Pass:** the tanker, AWACS and first BARCAP packages show TOT ... (ASAP); relief BARCAP waves do not; in the mission, the tanker is on its track by the time the first strike package needs gas.
- **Fail signatures:** a tanker with a TOT late in the mission; two BARCAP waves of one station arriving together (a relief wave was pulled onto the first).
