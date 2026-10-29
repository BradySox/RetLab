# RetLab — Claude Code Guide

**RetLab** — a development fork of DCS Retribution, a turn-based dynamic
campaign generator for DCS World, plus RetLab's air-defense, electronic-warfare,
recon, frontline, and assets-pack features on top of upstream.

- Forked from upstream `dcs-retribution/dcs-retribution` `dev` at `dce851ea`; later upstream
  fixes are adopted by hand (last sync #999, 2026-08-30).
- GitHub (this fork): https://github.com/BradySox/RetLab
- Read this before touching anything. The human-friendly overview is [`README.md`](README.md).

---

## Session Startup & Documentation Hygiene

**At the start of every new thread**, sync with GitHub before touching any code or docs:

```powershell
git fetch origin
git pull
git log origin/main -5 --oneline   # scan for new commits since last session
```

If the current branch is behind `main`, merge or rebase before editing anything — a branch
cut from a stale base produces duplicate work and conflicts. Never derive the state of the
codebase from memory; always read the current files.

**Keeping docs in sync** — when a feature lands or changes, update in this order. A push that
moves code past its docs is a broken push.

1. Relevant `docs/dev/design/` file — design rationale and technical details
2. Matching section in `docs/dev/retlab-features.md` — engineering deep-dive, file paths, gotchas
3. `README.md` — if the change is player-visible
4. `CLAUDE.md` — if the tech stack, architecture patterns, or feature list changed
5. `AGENTS.md` — sync to mirror `CLAUDE.md` (see Conventions)
6. `docs/dev/checklist-rows/<ID>.md` — add a row for any feature with runtime behavior that CI can't exercise (one file per row; see the table below)
7. **If a feature's RULE changed (not just its internals), grep the docs for the phrases the
   change falsified**, in the old rule's own words ("until scouted", the removed setting
   name), not the `§N`. `python tools/audit_stale_docs.py` checks every published file
   (README and `docs/wiki/`) against a table of removed features; CI runs it in `lint.yml`
   (job *Published docs*). **When you remove a feature, add its `Removed` row to that table
   in the same change.** Exit 1 = a published page still briefs a removed feature; exit 2 =
   a row's own pattern is inert.

**Parallel PRs must not collide (STANDARD, 2026-09-29).** Several threads run at once, and
nearly every PR used to conflict in the same five places. Each now has a rule:

| Adding | Do this | Never |
|---|---|---|
| A checklist row | `python tools/claim_id.py row` prints the next free `B###`, reserved on GitHub, and writes its stub `docs/dev/checklist-rows/B###.md`; fill that file in | pick the number by reading the file, or add the row to the end of `retlab-ingame-pass-checklist.md` |
| A features-doc `§N` | `python tools/claim_id.py section` | the same |
| A changelog line | a new file `changelog.d/<slug>.feature.md` or `<slug>.fix.md` (see its README) | edit `changelog.md` |
| A What's New entry | a new file `resources/whatsnew/<date>-<slug>.yaml`, one entry | append to someone else's file |
| The outstanding count or summary table | nothing: `python tools/checklist_board.py` prints both from the row headings | write a count into the checklist |

The checklist, the features doc, the feature index, `CLAUDE.md`, `AGENTS.md` and
`changelog.md` are `merge=union` in `.gitattributes`: on a conflict in them, run
`git merge origin/main` in the worktree (or the app's sync) and git keeps both sides. Read
the merged spot anyway: a line both sides *changed* comes out twice, and a block one side
*deleted* comes back if the other side edited it. Duplicate row ids, `§` numbers and a
returned checklist summary fail a test. A branch that added its row to the end of the main
checklist moves it out with `python tools/checklist_rows.py move B###`. Rows from before
2026-09-29 stay in the main file; every reader reads both. A generated file (the feature
index) that comes out wrong is fixed by regenerating it.

---

## Project Docs

This file is the map. The territory is `docs/`. Read the relevant note **before** editing a
feature — each carries the design rationale, the flown-test findings, and the deferred work.

### Standing policies

- **Everything is upstreamable** (2026-07-19). "Clean and correct" is the bar; there is no
  permanent fork-only category. The one named exception is the Splash Damage tuning (see PINNED).
- **Upstream PR freeze: LIFTED 2026-10-29** (DM). See *Upstream PRs — standing rules* below.
- **Red Tide's feature lock was LIFTED 2026-08-03.** It takes new work like any other
  campaign. One exclusion survives as a separate call: the §71 F-4E pack stays un-preseeded.
- **Campaign ownership**: every fork-authored campaign has an owning design note and a CI lock.
- **A generated `.miz` is never hand-edited** where a build tool owns it. Edit the tool.

### Tracking docs — start here

| Doc | What it is |
|---|---|
| [retlab-features.md](docs/dev/retlab-features.md) | **The deep dive.** Every feature with file paths, gotchas, tests, deferred work. |
| [retlab-features-history.md](docs/dev/retlab-features-history.md) | Full text of the older §8 fix entries and §6's removed orbit design. The features doc keeps one line each. |
| [retlab-feature-index.md](docs/dev/retlab-feature-index.md) | Generated catalog of every feature with its plugin and `Settings` wiring. |
| [retlab-ingame-pass-checklist.md](docs/dev/retlab-ingame-pass-checklist.md) | Every "needs an in-game pass" item with a pass criterion and fail signature. Rows added from 2026-09-29 are one file each in `docs/dev/checklist-rows/`. Settled rows (verified, retired, removed, closed) are in `retlab-ingame-pass-checklist-archive.md`; `python tools/checklist_rows.py archive` moves them. Find a row: `grep -rn "^### B55 " docs/dev/retlab-ingame-pass-checklist*.md docs/dev/checklist-rows`, then Read ~15 lines from there. Never search a bare row ID. |
| [flycards/WATCH.md](docs/dev/flycards/WATCH.md) | The standing opportunistic watch list — rows to adjudicate on any flight. |
| [flycards/LOCAL.md](docs/dev/flycards/LOCAL.md) | The rolling local test card for contrived conditions. |
| [retlab-early-systems-decision-ledger.md](docs/dev/retlab-early-systems-decision-ledger.md) | The 2026-07-18 deep-audit verdicts on the early-systems core, with self-play evidence. |
| [retlab-upstreaming-inventory.md](docs/dev/retlab-upstreaming-inventory.md) | The upstreaming queue, priority-ordered, with readiness marks, plus the **upstream issue ledger** (standing triage of upstream's open issues). |
| [retlab-upstream-pr-ledger.md](docs/dev/retlab-upstream-pr-ledger.md) | Every upstream PR we carved: status, review history, sync notes, the freeze history (lifted 2026-10-29). |
| [retlab-community-contribution-roadmap.md](docs/dev/retlab-community-contribution-roadmap.md) | The long view: community-value × carve-difficulty across every feature. |
| [retlab-retribution-long-view.md](docs/dev/design/retlab-retribution-long-view.md) | Structural read of the engine (2026-08-17) and its seven seams. 1 and 4 are BUILT (§91, §90); 2 and 5 accepted, not started; 3 analysis only; 6 scoped in `retlab-coop-persistent-campaign-notes.md`; **7 (the enemy) DROPPED** — read [retlab-red-brain-phase0-notes.md](docs/dev/design/retlab-red-brain-phase0-notes.md) before proposing anything about red. |
| [retlab-campaign-architecture-notes.md](docs/dev/design/retlab-campaign-architecture-notes.md) | Direction note (2026-08-20, DM call): the one-substrate architecture, rungs R0–R7. Nothing built; each rung lands on its own call. |

### Design notes — `docs/dev/design/`

One note per campaign and per system, indexed in
[docs/dev/design/README.md](docs/dev/design/README.md). **Find and read the matching note
before touching a campaign's `.yaml`, `.miz` or build tool, or a feature's code.** A new note
is added to that index in the same change.

The starting points that are easiest to miss:

- **IADS** — `retlab-skynet-return-notes.md`. Skynet is the engine again since 2026-09-12;
  MANTIS and the MIST shim are gone.
- **COIN** — `retlab-coin-HANDOFF.md`. **CSAR** — `retlab-csar-notes.md`.
- **Syria — Anatolian Reach** — Akrotiri stays support-only; read its note first.
- **A stutter or freeze** — `retlab-sim-thread-freeze-notes.md`. Test in model time, never
  wall time.
- **Bumping `Moose.lua`** — `retlab-moose-bundle-patches-notes.md`.
- **Reverting or carving planner behavior** — `retlab-autoplanner-upstream-divergence-audit.md`.
- **Adopting upstream #823** — `retlab-pr823-frontline-merge-notes.md`.
- **Replacing a features-doc section** — `retlab-doc-mass-notes.md`.

### Deleted design notes

18 notes on removed features were deleted 2026-08-20; they are at
`git show 5db34150f:docs/dev/design/<name>` and keep the pre-rebrand `414th-` prefix.
8 superseded notes were deleted 2026-10-12 (the EWRS and dismounts retirements, the CTLD port
scope, the mission-planning wiki draft, wing growth, framework consolidation, the MOOSE long
view, the Tanker War campaign); they are at `git show 57ab9e720:docs/dev/design/<name>`.
The TIC movement note went with TIC on 2026-10-15: `git show bc0284448:docs/dev/design/retlab-tic-dynamic-fronts-notes.md`.
**Do not keep a note for a removed feature**: record the removal in the features doc §N and
delete the note, after lifting any **constraint learned from a flown test** into the
hard-constraints list or a surviving note. The deleted debt register is at
`git show bb8d019c6:docs/dev/414th-feature-debt-register.md`.

### Other

- [README.upstream.md](README.upstream.md) — unmodified upstream README (setup, dependencies).
- [references/manuals/](references/manuals/) — official DCS manuals for 11 aircraft modules
  plus the Supercarrier guide. The PDFs are gitignored; read the folder's tracked `INDEX.md`,
  then extract only that range with `pdftotext -f N -l M <pdf> -` (the Read tool can't open
  them here). Use them for procedure and systems, **not** loadouts, weapon dates or unit stats.
  The `dcs-aircraft-manuals` skill wraps this.
- [docs/wiki/](docs/wiki/) — the player and contributor wiki, mirrored to the GitHub wiki by
  `wiki-sync.yml` on every push to `main`. **Edit pages here, never in the wiki UI.** Also
  carries the adopted upstream dev-process standards, each with **RetLab:** delta notes.
- `AGENTS.md` mirrors this file — see **Conventions**.

## Tech Stack

| Layer | Choice |
|---|---|
| Campaign engine | Python 3.11 (`game/`). Library catalog, reference only: https://github.com/vinta/awesome-python |
| UI | PyQt (`qt_ui/`) + React/Leaflet client (`client/`) — client NOT type-checked in CI |
| Mission scripting | **Lua 5.1** sandbox plugins (`resources/plugins/`) — no `os`/`io`, no `goto`, definition order matters |
| In-mission framework | **MOOSE** (bundled `Moose.lua`; some plugins vendor classes verbatim) is the standard. **MIST is upstream's `mist_4_5_126.lua`** again since 2026-09-12, and `base/plugin.json` is upstream's work-order list plus the fork's `sortie_recorder.lua` and `train_losses.lua`; a merged upstream Lua file that calls `mist.*` needs no shim work. MOOSE API docs: https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html |
| Units / mission format | pydcs; CurrentHill mod packs in `pydcs_extensions/` |
| CI gates | Black + mypy + pytest + the published-docs audit + the Lua 5.1 syntax gate (all blocking), plus advisory luacheck and dead-code report — see `docs/dev/CLAUDE-ci.md` |
| Release | PyInstaller → rolling `latest` pre-release on GitHub |

---

## Key Architecture Patterns

**Planner / Lua split.** Python plans and spawns the mission (flight plans, ROE, templates);
runtime behavior (EW, ISR, rescue) is driven by the Lua
plugins. When a feature has both, the Python side sets up and the Lua side executes — don't
move runtime logic into the planner or vice versa.

**Viewer-aware visibility layer (recon fog).** AI planning and threat math always use ground
truth (`viewer=None`); only the human (BLUE) map and UI are fogged. **One question, asked in
one place**: `TheaterGroundObject.visibility_for(viewer)` returns HIDDEN / UNKNOWN / KNOWN.
Its two leaves are `known_for` (composition and threat/detection rings, `recon_intel_fog`) and
`hidden_on_player_map` (enemy command posts, `scar_command_post_intel`). Nothing else is
viewer-aware except `standard_identity_for` (COIN's suspect-until-engaged symbol).

- **A site is revealed by engaging it** (ordnance on it, or any ground-attack sortie that
  reaches it) and is then known completely and permanently, damage included. Fixed SAM sites
  (`is_fixed_sam_site`) are always known. A site whose radar a §118 Vacuum heard is known
  after the turn. A captured enemy commander reveals every command post. Recon reveals only
  a hidden command post within 3 NM of its target.
- There is no BDA damage lag: `alive`/`is_dead`/`dead_units`/`max_threat_range` are plain
  truth. Do **not** reintroduce a viewer parameter on those, or the old `_for_player`/`_for`
  method twins.
- **Anything that picks targets FOR blue automatically must gate on the fog**: auto raids
  (§63), the carrier strike (§44), C2 decapitation (§52), HQ priorities (§103), any future
  fire mission. Use `fogofwar.hidden_from(Player.BLUE, tgo)`, never a bare
  `hidden_on_player_map`; it wraps `fog_intact()`, so a host who ticked the reveal overview
  gets the same target as one who did not. Red is never fogged.
- The **overview toggle** (`game/theater/fogofwar.py`, transient, never pickled)
  short-circuits both leaves to ground truth with no server-model change. It is a checkbox in
  `MapLayersControl` (§18). See features doc §3.

**Save migration.** Removed/renamed enum *values* migrate in **one place**:
`FlightType._missing_` (`game/ato/flighttype.py`) maps legacy persisted strings to live
members via the `_LEGACY_FLIGHT_TYPE_VALUES` table. The unpickler (`persistency.py`
`_handle_flight_type`) calls `FlightType(value)`, which routes through `_missing_`, so it
carries **no** parallel remap table — only unknown-value tolerance (degrade to BARCAP).
Other persisted state (e.g. fog) migrates in each class's `__setstate__`. When you rename a
persisted enum value, add the entry to `_LEGACY_FLIGHT_TYPE_VALUES` only.

**Lua plugin discipline.** Lua 5.1 only, vanilla DCS units only, define functions before
first use. The *Lua 5.1 syntax* job in `lint.yml` runs `luac5.1 -p` over every
`resources/plugins/**/*.lua` (parse-time errors). The **headless Lua plugin harness**
(`tests/lua/`, `retlab-lua-plugin-harness-notes.md`) runs the real plugin scripts on Lua 5.1
via `lupa` against a faked DCS sandbox inside the normal pytest run, and covers most plugins.
It catches "the script errors at runtime and the feature silently never starts" and pins
safety invariants; it models no DCS AI or physics, so real behavior still needs an in-game pass.

**Finding things in the big files.**
- `game/settings/`: a field lives in `fields/<page>.py` — `grep -rn "^    <field>:" game/settings/fields`; by UI label `grep -rn -B1 '"<Label>' game/settings/fields` (the label is on the line after the field). Dialog layout is `layout.py`, old-save rewrites `migration.py`.
- `game/missiongenerator/kneeboard/` (a package since #1066): one module per page family — `grep -rn "^class .*Page" game/missiongenerator/kneeboard` first.

---

## Features at a Glance

One line each. **Full internals — file paths, gotchas, tests, deferred work, flown-test findings
— are in [docs/dev/retlab-features.md](docs/dev/retlab-features.md) under the matching §N.** Read
that section before editing a feature; this list is an index, not a spec.
Find §N: `grep -nE "^## (§)?57[. ]"` — §1–18 are mostly headed `## N.`, the rest `## §N —`.

The generated catalog is [docs/dev/retlab-feature-index.md](docs/dev/retlab-feature-index.md); the
source of truth is the registry `game/retlab/features.py` (regenerate with
`python -m game.retlab.features`). **Register every new feature there** or CI fails.
Claim its `§N` first with `python tools/claim_id.py section`.

### Hard constraints — established by flown tests, do not undo

These cost a mission or a crash to learn. Each is recorded in full in the features doc or the
linked design note.

- **Never restore the per-base backstop EWR** (§1). DCS has no non-colliding ground unit; the
  mast sat on taxiways and broke AI taxi routing. Any authored ground object inside a runway
  strip or apron does the same (test 35: upstream's own Incirlik EWR marker). New Game logs
  `Airfield clearance:` for every ground object inside a runway band (300 m, 1.6 km) or 80 m
  of a stand (`game/theater/airfieldclearance.py`); it warns, it never moves a marker.
- **Never restore the generic `ewrj` fighter-pod jammer** (§2). Superseded by the C-130J.
- **The C-130J cues; it never lases or designates.** It carries no targeting sensor in DCS.
  Retribution has no FAC(A) task type; §38 does marking through Vietnam Ops.
- **Never add a land-attack weapon family to the §81 anti-ship pattern list.** §63 and §81 stay
  correct only because their weapon sets are disjoint.
- **GPS jamming (§86): at most 3 sites per campaign, non-overlapping.** Bubbles are large and
  invisible on the map, and effects do not stack.
- **A mover's DCS group needs a 2-waypoint route** — current position, then destination. A
  single destination waypoint reads as "already there" and the group never drives.
- **One undrivable member pins a whole group.** A route push moves a DCS group as a unit, so a
  static emplacement in it yields no movement and a ground-AI levelling storm. This is why
  §85's missile-battery support section is trucks only.
- **A tanker track is DCS's own racetrack orbit, never a waypoint route.** A KC-135 banks
  45 degrees alone, 25 with a jet joined up and 15 with one on the boom; on a 30 x 15 NM
  route box it never flew level in contact (2026-10-09). `retlab-tanker-box-notes.md`.
- **Movers must last 90 minutes.** Any player-interactable mover is paced so an intercept is
  still possible late in a mission.
- **Never spawn phantom units.** Every scripted force is a real, tracked unit whose loss records
  natively. Applies to §35, §37, §50.
- **Never script explosions on an airfield.** `trigger.action.explosion` inside a field's area
  puts it into DCS's under-attack state and every AI fixed-wing launch there is held until it
  clears; a recurring barrage never clears it (§36, removed). A one-off strike is not this.
- **A plugin that runs a setting has no checkbox.** An unticked plugin silently kills its
  setting, so such a plugin is `skipUI`, always on (`LuaPlugin.enabled`), and the setting is
  the one switch: `base`, `intercept`, `opscsar`, `vietnamops`, `gpsjamming`, `cruisemissiles`,
  `navalmagazines`, `briefing`, `redscramble`, `neutralborder`, `aifill`, `pkgcontrol`, `vacuum`, `voiceatc`. A test fails if one gains a
  checkbox again.

### Live features

1. **QRA intercept reserve** — alert jets, player-manned cold alert, forward-defense border zones.
2. **JAMMING flight type** — the C-130J as an EW + ISR platform (`c130j` plugin).
3. **Recon intel fog** — a site is unknown until engaged or heard by Vacuum, then known for good; recon finds command posts.
4. **UI transparency** — target intel panel, mission-impact debrief, package context bar.
5. **Player target location precision** — `Approximate` mode offsets steerpoints.
6. **Air-defense planning rework** — BARCAP waves; first wave, tankers and AWACS ASAP. Geometry is upstream's.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD off datalink.
8. **Robustness, crash fixes and refuelling** — the fix log; per-flight Refuel before the push / before station.
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020`.
14. **Plugin Options UI** — `descriptionInUI`, labels and defaults.
16. **Settings QOL audit** — dead-field cleanup, the `AiRadioBehavior` enum.
17. **Auto-planner target unpredictability** — opt-in reordering of opportunistic targets.
18. **Fog-of-war overview toggle** — transient reveal, never saved, fenced out of missions.
19. **Unified map layers panel** — one grouped control with presets.
22. **Kneeboard space-utilisation + custom import** — per-campaign kneeboard images.
23. **Per-squadron DCS country** — nation voiceovers and pilot names.
24. **Date-gated aircraft properties** — `restrict_props_by_date`.
26. **Off-mission combat fidelity** — capability-weighted auto-resolution.
27. **Shared-airframe kneeboard index** — one index page per shared type.
28. **Settings IA reorg + difficulty presets** — metadata layout, presets, search, the RetLab Features page.
29. **Campaign SITREP** — last-turn digest on the kneeboard, ribbon and debrief.
32. **Arc Light** — bomber carpet on a Strike target *(Vietnam Ops)*.
33. **AAA flak gauntlet** — barrage flak against predictable run-ins *(Vietnam Ops)*.
34. **Naval gunfire support** — call-for-fire and coastal bombardment *(Vietnam Ops)*.
35. **Convoy interdiction** — real trail convoys for Armed Recon *(Vietnam Ops)*.
37. **Super Gaggle** — real helos resupply a cut-off outpost *(Vietnam Ops)*.
38. **FAC(A) willie-pete marking** — an OV-10 marks the enemy concentration *(Vietnam Ops)*.
39. **Snake and nape** — napalm fire from a low fast release *(Vietnam Ops)*.
41. **High Digit SAMs Ultimate Compilation** — S-400, S-300V4, SAMP/T, Pantsir-SM.
42. **Local DCS chart base layers** — local tile pyramids as base maps.
43. **Per-aircraft flight defaults** — saved fuel and cockpit properties.
44. **Long-range carrier ops** — a standoff boat's package with its own tanker.
45. **Support-package F10 markers** — tanker, AEW&C and CAP stations on the F10 map.
47. **Continuous campaign clock & weather** — one marched clock; weather evolves.
50. **Ambient supply convoys** — a few real supply columns on both sides' roads every turn.
52. **Command-center decapitation** — a headless HQ plans worse and frags less.
56. **Strikeable motorpool depots** — the reserve armor pool, bombable 1:1.
58. **Mission-start briefing popup** — per-pilot slot-in cards.
61. **Host red-interceptor scramble** — an F10 bandit spawner.
62. **Squadron-sequenced modexes** — per-squadron board numbers; pin one per flight.
63. **Ship-launched cruise missile raids** — finite magazines, auto raids, F10 call-for-fire.
64. **Carrier deck spawn policy** — AI clear of the six-pack; players spawn at mission start.
65. **Curated carrier comms** — per-hull TACAN, ICLS, Link 4 and ATC.
66. **Generated-mission archive** — a dated copy of every generation.
67. **Weather-aware auto-planning** — storms demote low attack.
68. **Adaptive procurement** — price-weighted buys, optional SAM repair.
69. **SEAD-before-strike coordination** — strikes retimed behind their suppressor.
71. **Expanded F-4E Weapons Pack** — AGM-78 fits gated on pylon legality.
72. **Carrier deck decorations** — deck dressing clear of every parking spot.
74. **Native DTC data pre-population** — cartridges for Hornet, Viper, F-14B(U), Apache.
75. **Custom victory conditions** — authored win/lose blocks.
76. **CTLD paratroopers** — fixed-wing Air Assault by paradrop, player and AI.
78. **Sea-supply convoys + coastal anti-ship** — proportional convoy losses and batteries that actually engage.
80. **Mixed-hull ship groups** — task groups, family-bounded.
81. **Cross-turn naval magazines** — staggered release, finite anti-ship stock.
85. **SAM/missile battery support sections** — refuellers, power and transload trucks.
86. **GPS jamming** — satellite weapons land long inside the bubble.
87. **Naval station-keeping racetracks** — ships hold station under way.
88. **Angled-deck carrier recovery heading** — 25 kt down the angled deck.
90. **Front-line model** — supply lines, assault cost, force weight, terrain, movement arrows.
91. **Per-flight sortie records** — track, time airborne, fuel, shots and hits.
92. **What's New** — recent player-visible changes.
93. **Region priorities** — per-base BLUE planning weight. Never a fence.
94. **Smart threat reaction** — only the flight being guided on goes defensive.
95. **Pinned bullseye** — one per campaign, never on a ship.
96. **Player career logbook** — per-pilot record. Never a reward.
97. **Lifetime pilot profiles** — flying kept across campaigns, outside the save.
98. **Neutral-faction border defense** — real borders; a neutral hails, then turns hostile. Players only.
99. **Sandy rescue escort** — armed escort for a downed pilot. Hand-fragged only.
100. **King on-scene commander** — the player C-130J fixes the survivor. Cues only.
101. **Dynamic spawn templates** — dynamic-slot jets built from a fragged flight.
102. **My aircraft, saved points and the DTC options** — one window for your seat.
103. **HQ priority targets** — target value ranking; a blue-only planner weight.
104. **Runway queue at busy fields** — taxi allowance and early mission start. Always on.
105. **RetLab Iran Air Defense Pack** — support for RetLab's private mod.
106. **Package route and map route editing** — routes edited on the map; package legs shared.
107. **Briefing screen picture** — a per-mission card, or your own `briefing.png`.
108. **Flight report cards** — debrief grades from §91. Never a reward.
109. **Outside AI reads red's turn** — REST API under `/retribution-ai/*`; optionally plans red. Red only.
111. **Sector war** — named sectors about 10 NM across; territory fill, a battle in every border sector, and (new games) sectors deciding the fight are built; the CAS card is agreed, not built.
112. **HQ requests** — up to three targets a turn that the auto-planner left alone. No prize.
113. **AI fills empty player flights** — an AI copy launches when nobody takes a flight's player seats.
114. **Coordinated TOT** — a hand-planned package lands 2 to 8 min behind its SEAD; else ASAP with a warning.
116. **Voice AWACS on SRS** — blue AWACS go silent for a SkyEye GCI bot; its frequency held and on the kneeboard. Off by default.
117. **Airborne package control** — a C-130J-30 ABCCC runs player packages on STRIKE through SkyEye; nothing without it airborne. Off by default.
118. **Vacuum ELINT** — a KC-135 (C-130J-30 backup) calls red SAM radars by bullseye through SkyEye as they come on and answers player calls; turns with SEAD or DEAD. Off by default.
119. **Voice ATC** — Ground and Tower for player flights through SkyEye: taxi, takeoff, landing, readbacks. Off by default.
120. **Voice bots on Take Off** — Take off starts SRS, SkyEye and the SRS client, connected; SkyEye stops on debrief. Off by default.
122. **Exact site layouts** — a campaign group named `FIXED ...` generates as drawn, every unit on its spot.
123. **Trains** — a Train group drawn in the .miz is a rail line; supply between its bases goes by train. A dead train loses its whole cargo.

### Retired, removed or shelved — do not restore

Kept numbered so old notes and saves stay readable. Details and rationale in the features doc.

| § | Feature | Status |
|---|---|---|
| 11 | Native DCS DTC cartridge export (v1) | Retired 2026-06-26 — superseded by §74 |
| 12 | Recon engine (TARPS + drone BDA) | Removed 2026-08-20 — the §3 rework left its captures with no consumer |
| 13 | Flight Control ATC | Retired 2026-06-26 |
| 20 | Drop-spawn map unit placement | Removed 2026-08-02 |
| 15 | SCAR — the fork's first RESCAP "Sandy" escort | Removed 2026-08-07 — §99 is the live Sandy |
| 21 | Combat SAR (fork implementation) | Removed 2026-08-07 — replaced by upstream #929 (an open PR), re-adopted by hand phase by phase; read `retlab-csar-notes.md` before touching the hover height. The King is hand-fragged only |
| 25 | Compact 3–4 page kneeboard deck | Retired 2026-07-05 |
| 30 | Dedicated kneeboard cover page | Retired 2026-07-13 — new info folds into a stock page |
| 31 | One-page Brief Sheet | Retired 2026-07-13 — BLUF survived |
| 40 | Campaign phases, ROE zones, target release | Removed 2026-07-21 |
| 46 | Route-aware fuel-tank planning (fuel-first) | Reverted 2026-08-09 — nothing fits tanks; the external-fuel accounting helpers survive for the readouts. Tanker tasking has fork additions since (§6, §8) |
| 48 | Commitment ceiling and the political-will economy | Removed 2026-07-21 |
| 49 | Mobile missile relocation (the SCUD hunt) | Removed 2026-08-29 — never relocated a site in three flown attempts |
| 51 | Enemy comms jamming | Removed 2026-09-07 — audio pressure that never changed the force model |
| 70 | COMINT collection (and the red comms net) | Removed 2026-09-07 |
| 36 | Airbase harassment (and the frontline artillery mode) | Removed 2026-09-16 — grounded AI launches; see the airfield-explosion constraint |
| 89 | Living battlespace | Removed 2026-09-07 |
| 53 | War economy | Removed 2026-07-21 |
| 54 | Munitions availability | Removed 2026-07-21 |
| 55 | Red Intent adaptive posture | Removed 2026-07-21 |
| 57 | Air-droppable minefields | Removed 2026-09-07 |
| 59 | Ground AI sleep | Removed 2026-09-23 — never observed doing its job in a flown test |
| 60 | SAM guidance-radar redundancy (two track radars per site) | Removed 2026-09-29 — every SAM site is back to one guidance radar |
| 77 | Escort jamming (the `growler` plugin and the Escort Jammer task) | Removed 2026-10-12 — the EA-18G and EA-6B fly SEAD and SEAD Escort at upstream's weights |
| 79 | Decoy suspected-activity zones | Removed 2026-08-18 |
| 82 | The Wing Grows (scheduled squadron arrivals) | Removed 2026-08-16 |
| 83 | SP Pilot Mode | Removed 2026-10-12 — verified working 2026-08-05, never switched on since |
| 84 | Old-stock loadout attrition | Removed 2026-08-06 |
| 110 | Ballistic missile call-for-fire (`bmstrike`) | Removed 2026-10-12 — ported 2026-10-10, never flown |
| 9 | TIC — Troops In Contact (the `tic` plugin and the late-init pass) | Removed 2026-10-15 — the front fights with DCS's own ground AI |
| 73 | Per-airframe default loadout for a task (and the user `UnitPayloads` folder) | Removed 2026-10-17 — saved fits replaced shipped presets by name in every campaign and pinned old weapons; RetLab reads only the shipped payloads |
| 115 | Phone map (File > Phone link) and the ntfy turn ping | Removed 2026-10-21 — never flown; the map on a phone over home Wi-Fi was not wanted |
| 121 | Radio discipline (Strict/Relaxed/Casual) | Removed 2026-10-26 — every voice bot accepts every call |

Also removed: the blank-start campaign maker (2026-08-02), the SOF capture economy (2026-07-01),
the MOOSE MANTIS IADS bridge with its MIST shim (removed 2026-09-12), and §50's convoy ambush
with its `map_hidden` flag (2026-10-11; the ambient convoys stay). Five options went on
2026-10-12: the QRA radio callouts, cosmetic base battle damage, the planner's automatic recon
flight (TARPS is hand-fragged), §75's two generic victory sliders, and package code words.

## Repo & Branch Layout

- This repo (`BradySox/RetLab`) `main` is the consolidated, most-up-to-date RetLab build.
- Upstream is `dcs-retribution/dcs-retribution`; RetLab's PR fork is `BradySox/dcs-retribution`.

### Forks and projects we watch

- **DCS Liberation** (`dcs-liberation/dcs_liberation`, branch `develop`) — the grandparent
  project, still developed. A second upstream we take from and never carve to. Skim its
  release notes when one drops, `[Data]` first. Adoptions, the already-covered list and its
  in-tree Sphinx docs are in `retlab-liberation-watch-notes.md`.
- **juanjux's fork** (`juanjux/dcs-escalation`) — upstream's most prolific outside contributor.
  Skim its PR list, `[FIX]` first, and **verify every claim against our own files before
  acting**. His #40 reverted the FLOT-anchored support orbits, as we did independently on
  2026-08-09; do not re-litigate. Ledger: `retlab-juanjux-fork-watch-notes.md`.
- **The MIST author's repositories** — read-only. His name and handle appear nowhere in this
  repo (paid-campaign treatment, 2026-08-20). His other repos are GPL-3 or unlicensed and this
  tree is LGPL-3: read them and reimplement from the DCS API, never vendor a file or commit his
  data. The tree ships upstream's MIST, as upstream does. His published unit dump is a second
  ground truth for sensor ranges; the detection-range check was run 2026-08-20 and found no
  defect — do not re-run it. See `retlab-mist-author-repos-notes.md`.

### Upstream PRs — standing rules

The PR-by-PR record is [retlab-upstream-pr-ledger.md](docs/dev/retlab-upstream-pr-ledger.md).
Read it before opening, updating or re-offering an upstream PR, and re-verify its counts with
GitHub first.

- **The upstream PR freeze was LIFTED 2026-10-29 by the DM.** New upstream PRs may be opened
  again. They still start as drafts, one change per PR, with upstream's gates run on the
  upstream tree. The freeze history and its old exceptions are in the ledger.
- Before answering an open issue in the
  [upstream issue ledger](docs/dev/retlab-upstreaming-inventory.md#upstream-issue-ledger),
  check the issue's timeline for linked PRs first (#951 was a duplicate).
- **Do not re-carve:** the HDS support (#956 carries it), #873's culling exemption (premise
  wrong), the Splash Damage tuning (#880, a preference).
- **Fork positions a sync must not undo:** `sweden_2020` keeps the KC-135 (#946's tanker half);
  the ATMOS-X station picker reads `starting_coalition`, not `captured` (#927).
- **Coordinate before carving into:** QRA (#782), frontline (#823, #681), SEAD (#772),
  kneeboard (#754), ATC, player region control (#686). Read #674's thread before carving
  target selection.

---

@docs/dev/CLAUDE-ci.md

---

## PINNED — do not modify

**`latest` git tag** — owned by `softprops/action-gh-release@v2` inside `retlab-latest.yml`.
Do NOT delete it or manually push it — breaking it breaks the URL the squadron bookmarks.

**`retlab-latest.yml`** — the sole rolling-release mechanism. Do NOT modify it without
understanding the impact. Test in a branch and verify the `latest` release after merging.
Do NOT add Discord webhook or other org-level secrets — the workflow uses only `GITHUB_TOKEN`.

**Local Python runtime** — before deleting anything under `tmp/`, inspect `.venv/pyvenv.cfg`.
When it reads `home = ...\tmp\uv-python\cpython-3.11.15-windows-x86_64-none`, that
`tmp/uv-python` directory is the base interpreter for `.venv`, **not a disposable cache**;
deleting it breaks `run_retribution.bat` with "No Python at ...". Never recursively delete
`tmp/` without this check.

**`resources/plugins/splashdamage3/Splash_Damage_3.4.2_RetLab.lua`** — RetLab's buddy-tuned
Splash Damage build. Do NOT overwrite it from upstream, and don't reintroduce the config layer:
the values are locked by design (`overall_scaling=0.6`, `rocket_multiplier=0.8`,
`static_damage_boost=1`, `game_messages=true`). The tuning is a preference, not owed upstream
(#880 closed 2026-08-06, DM call). Upstream's `shipRadarDamageEnable` block is left out;
restoring it is its own call. The `oca_aircraft_damage_boost` block is restored, but **ours
computes AGL inline because upstream's copy calls `getAGL`, defined nowhere** — do not resync
that block until upstream fixes it. History: `retlab-splash-damage-notes.md`.

---

## Conventions

- **Anything published to GitHub is written plain (STANDARD, 2026-08-07 user call).** README,
  wiki pages, PR bodies, changelog entries, issue comments and commit messages state what
  changed and why.
  - No voiceover: no dramatic reveals, no "X isn't a Y — it's a Z", no closing flourish.
  - One fact per line. A bullet that needs three sentences is three bullets or a table.
  - Bold marks a term, not emphasis.
  - Lead with the thing the reader came for: the download, the command, the change.
  - No changelog-in-prose in a reference page; history belongs in the design note.
  - Exempt: in-fiction campaign material (briefing packs, role cards), and mirrored upstream
    wiki pages (fork deltas go in **RetLab:** notes).
  - When a feature is cut, grep the README and `docs/wiki/` for it in the same change.
- **Code comments record why, never what (STANDARD, 2026-08-11 user call).** A comment says
  what the code cannot: a constraint from a flown test, a deliberate exclusion, an upstream bug
  being worked around.
  - Cap a block at ~3 lines; longer rationale goes in the design note with a one-line pointer.
  - A plugin or module header may run to ~15 lines: purpose, the `docs/` pointer, then the
    constraints a reader could undo by accident. Reference: `resources/plugins/intercept/intercept-config.lua`.
  - A pointer must resolve; confirm the file exists before committing it.
  - Data files carry values, not essays.
  - **Compress a constraint comment, never delete it.**
- **UI text house style (STANDARD, 2026-09-22 DM call).** Every user-visible string is US
  English (field names keep their spelling); nautical miles are `NM`; a setting's description
  renders in full, names another setting by its label rather than "above"/"below", and never
  describes a removed feature as live. `tests/settings/test_settings_text.py` guards the
  settings; rules and backlog are in `retlab-ui-consistency-audit-notes.md`.
- **When the evidence contradicts the instruction, lead with that and stop (STANDARD,
  2026-08-23 user call).** If a file, manual, log or generated artifact contradicts what was
  asked, the reply opens with that finding and names the source, in two sentences, then asks.
  Do not build the thing and bury the contradiction in a note. A preference cannot be
  contradicted by evidence; taste calls stand. If the call is reaffirmed, build it in full
  and say so.
- **Ask decisions with the AskUserQuestion widget (STANDARD, 2026-07-21; reaffirmed
  2026-10-08).** Whenever you need a decision, use the widget: recommended option first,
  marked "(Recommended)", a one-line trade-off per option, `multiSelect` when choices aren't
  exclusive, at most 4 questions. Typed "1, 2, 3" lists read as low-effort.
  - It works in a project thread too (2026-10-12 DM call); use it there. Only when it truly
    cannot reach the reader: numbered questions with lettered options, recommendation marked.
  - A free-text question with no fixed options goes in its own block at the end of the
    message: `> ❓ **Need your call:** <the question>`.
  - Never build a custom widget or Artifact to ask a question.
- **Never name a paid campaign anywhere in the repo (STANDARD, 2026-08-07 user call).**
  Third-party DCS campaigns are commercial products. Studying them and extracting facts is
  fine; their **names** stay out of code, comments, commits, PR titles/bodies, docs and wiki.
  - Use stable letters (`campaign A`, `campaign B`, …), consistent across docs; publishers
    likewise. Install paths are generic: `<DCS>\Mods\campaigns\<campaign A>`.
  - Commit messages and PR metadata count; rewrite and force-push an unmerged branch to fix one.
  - Not covered: real squadron names, real operation names, and the fork's own campaign names.
  - Check against `ls "<DCS>\Mods\campaigns\"`, not memory.
- **Supply lines are drawn in the .miz and follow the driveable corridor (STANDARD,
  2026-07-03; .miz-only since 2026-10-18 DM call).** A road is an M-113 group and a sea lane
  a HandyWind group in the campaign `.miz` (Combined Joint Task Forces Blue), as upstream
  draws them; never a yaml `supply_routes:`/`shipping_lanes:` list (a test fails on one).
  Each traces the road, river valley or pass you would drive, never a straight line across a
  ridgeline. Only the first and last waypoints bind the route to its CPs, so use 3–5
  intermediates and set them "On Road". On real-world maps author them from real road
  lat/lon with `python tools/supply_route_geo.py <name> --draw <campaign>.miz`; on fictional
  overlays trace on-map roads by eye in the ME. A build script keeps the drawn routes with
  `carry_route_groups` (`tools/campaign_routes.py`).
- **Upstream dev-process standards are ours (ADOPTED 2026-07-20 user call).** The upstream
  wiki's Contributing and Core development guides are mirrored in `docs/wiki/` with
  **RetLab:** deltas: small PRs, type annotations, Black via pre-commit, the module
  checklists, and the Release process (the rolling `latest` IS the release; pinned tags are
  `v<X.Y.Z>-retlab`; never `git push --tags`). An upstream carve targets
  `dcs-retribution/dev` via the PR fork, one change per PR, with upstream's gates run locally
  on the upstream tree, a `changelog.md` note and fork-only couplings stripped. When an
  upstream page changes, refresh the mirror and re-annotate.
- **AGENTS.md sync** — `AGENTS.md` is a byte-identical mirror of this file (CLAUDE.md is
  authoritative; only line 1, the title, differs), and `tests/test_agent_guide_mirror.py`
  fails when they drift. After editing CLAUDE.md, resync: `cp CLAUDE.md AGENTS.md`, then Edit
  line 1 back to `# AGENTS.md ...` (do NOT use `sed -i`; it flattens CRLF). The imported
  `docs/dev/CLAUDE-ci.md` is shared by both.
