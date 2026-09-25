# RetLab — Claude Code Guide

**RetLab** — a development fork of DCS Retribution, a turn-based dynamic
campaign generator for DCS World, plus RetLab's air-defense, electronic-warfare,
recon, frontline, and assets-pack features on top of upstream.

- Base: upstream `dcs-retribution/dcs-retribution` `dev` @ `dce851ea`.
- GitHub (this fork): https://github.com/BradySox/RetLab
- Read this before touching anything. The human-friendly overview is [`README.md`](README.md).

---

## Session Startup & Documentation Hygiene

**GitHub:** https://github.com/BradySox/RetLab

**At the start of every new thread**, sync with GitHub before touching any code or docs:

```powershell
git fetch origin
git pull
git log origin/main -5 --oneline   # scan for new commits since last session
```

If the current branch is behind `main`, merge or rebase before editing anything — a branch
cut from a stale base produces exactly the duplicate-work + conflict mess that sinks a PR.
Never derive the state of the codebase from memory; always read the current files.

**Keeping docs in sync** — when a feature lands or changes, update in this order:

1. Relevant `docs/dev/design/` file — design rationale and technical details
2. Matching section in `docs/dev/retlab-features.md` — engineering deep-dive, file paths, gotchas
3. `README.md` — if the change is player-visible
4. `CLAUDE.md` — if the tech stack, architecture patterns, or feature list changed
5. `AGENTS.md` — sync to mirror `CLAUDE.md` (see Conventions)
6. `docs/dev/retlab-ingame-pass-checklist.md` — add a row for any feature with runtime behavior that CI can't exercise
7. **If a feature's RULE changed (not just its internals): grep the docs for the phrases the
   change falsified.** Steps 1-6 cover the feature's own faces; they do not cover the other
   notes that merely mention it. `§3` is named in **50 doc files** — the 2026-08-18 rework
   updated 16 and left **8 stale claims**, two of them on the published wiki. Grep for the old
   rule in its own words ("until scouted", "BDA lag", the removed setting name), not for the
   `§N`. Audited in `docs/dev/design/retlab-doc-mass-notes.md`.

   **Run the audit rather than the grep** — `python tools/audit_stale_docs.py` checks every
   published file (README and `docs/wiki/`) against a table of removed
   features and exits non-zero on a hit. **CI runs it** in `lint.yml` (job *Published docs*),
   so a stale published page fails the build. It is only as good as that table: **when you
   remove a feature, add its `Removed` row in the same change.** The table now self-checks —
   exit 2 means a row's own pattern is inert and has been guarding nothing, which three rows
   silently were until 2026-09-07 (a word-boundary escape stored as the backspace byte). The 2026-08-07 CSAR replacement is
   why it exists — the design note was updated and five published pages, one of them
   sidebar-linked and written in the present tense, went on briefing a package that no
   longer existed for thirteen days.

A push that moves code past its docs is a broken push.

---

## Project Docs

This file is the map. The territory is `docs/`. Read the relevant note **before** editing a
feature — each carries the design rationale, the flown-test findings, and the deferred work.

### Standing policies

- **Everything is upstreamable** (2026-07-19). "Clean and correct" is the bar; there is no
  permanent fork-only category. The one named exception is the Splash Damage tuning (see PINNED).
- **Upstream PR freeze is IN FORCE** until upstream's next beta. Updating existing PRs is fine;
  new PRs are not. **Only the DM lifts it** — never infer the lift from upstream commit activity.
- **Red Tide's feature lock was LIFTED 2026-08-03.** It takes new work on the same terms as any
  other campaign. Two exclusions survive as separate calls, not lock consequences: the §71 F-4E
  pack stays un-preseeded. §57 minefields were shelved and are now removed outright.
- **Campaign ownership**: every fork-authored campaign has an owning design note and a CI lock.
- **A generated `.miz` is never hand-edited** where a build tool owns it. Edit the tool.

### Tracking docs — start here

| Doc | What it is |
|---|---|
| [retlab-features.md](docs/dev/retlab-features.md) | **The deep dive.** Every feature with file paths, gotchas, tests, deferred work. |
| [retlab-feature-index.md](docs/dev/retlab-feature-index.md) | Generated catalog of every feature with its plugin and `Settings` wiring. |
| [retlab-ingame-pass-checklist.md](docs/dev/retlab-ingame-pass-checklist.md) | Every "needs an in-game pass" item with a pass criterion and fail signature. Find a row: `grep -n "^### B55 "`, then Read ~15 lines from there. Never search a bare row ID. |
| [flycards/WATCH.md](docs/dev/flycards/WATCH.md) | The standing opportunistic watch list — rows to adjudicate on any flight. |
| [flycards/LOCAL.md](docs/dev/flycards/LOCAL.md) | The rolling local test card for contrived conditions. |
| [retlab-early-systems-decision-ledger.md](docs/dev/retlab-early-systems-decision-ledger.md) | The 2026-07-18 deep-audit verdicts on the early-systems core, with self-play evidence. |
| ~~414th-feature-debt-register.md~~ | **DELETED 2026-08-25** — the Aug-1 wave it planned is long spent, and it was still triaging §21 CSAR, §53/§54 and §46, all since removed. Its own header said to archive it once that wave was processed. In git history: `git show bb8d019c6:docs/dev/414th-feature-debt-register.md`. The live successors are the checklist and `docs/dev/flycards/`. |
| [retlab-upstreaming-inventory.md](docs/dev/retlab-upstreaming-inventory.md) | The upstreaming queue, priority-ordered, with readiness marks. Also carries the **upstream issue ledger** — the standing triage of upstream's open issues, first swept 2026-08-20. |
| [retlab-community-contribution-roadmap.md](docs/dev/retlab-community-contribution-roadmap.md) | The long view: community-value × carve-difficulty across every feature. |
| [retlab-retribution-long-view.md](docs/dev/design/retlab-retribution-long-view.md) | Structural read of the engine (2026-08-17): what Retribution is, measured, and the seven seams that follow. **1 (mission→campaign reporting) and 4 (the front line) are BUILT** as §91 and §90; **2 (the intel model) and 5 (time between turns) are accepted, not started**; 3 is analysis only; 6 is scoped in its own note. **Seam 7 (the enemy) is DROPPED** — three framings, three Phase 0s, no observable defect found; read §8 and [retlab-red-brain-phase0-notes.md](docs/dev/design/retlab-red-brain-phase0-notes.md) before proposing anything about red, because §55 tried the obvious shape and the analytic route has now failed three times. |
| [retlab-campaign-architecture-notes.md](docs/dev/design/retlab-campaign-architecture-notes.md) | **Direction note (2026-08-20, DM call): the one-substrate architecture.** The graveyard's shared diagnosis (private numbers, no substrate), five pillars (flow-network substrate, mission-as-transaction, event-driven turns, red legibility, command-by-weight), the four admission rules, and rungs R0–R7 with gates and falsifiers. Nothing built; no tombstone lifted — each rung lands on its own call. |

### Campaign notes — `docs/dev/design/`

Read before touching a campaign's `.yaml`, `.miz` or build tool.

| Campaign | Note |
|---|---|
| Germany — Red Tide | `retlab-red-tide-campaign-notes.md` (+ `-supply-routes-`, `-c2-real-buildings-HANDOFF`) |
| Operation Baltic Fury | `retlab-baltic-fury-campaign-notes.md` |
| Marianas — Second Island Chain 2027 | `retlab-marianas-2027-campaign-notes.md` |
| Marianas — Operation Forager (1944) | `retlab-marianas-wwii-terrain-notes.md` (the terrain note owns it) |
| Syria — Anatolian Reach (2004) | `retlab-anatolian-reach-campaign-notes.md` — **Israel + US vs a Turkey–Russia bloc.** The subject is range: 250–400 nm to every target. **Akrotiri is support-only and must stay that way** — it is closest to seven of the nine Turkish fields, so a combat squadron there benches Israel and the campaign silently stops being about anything. Enemy faction is **inline** (one faction per coalition); SAM presets are period-gated **by hand** because `restrict_weapons_by_date` never gates them |
| Iraq — Umm al-Ma'arik (Desert Storm) | `retlab-desert-storm-campaign-notes.md` |
| Iraq — Operation Inherent Resolve | `retlab-inherent-resolve-campaign-notes.md` |
| Afghanistan — Enduring Resolve (COIN) | `retlab-coin-HANDOFF.md` — **start here for COIN** |
| Caucasus — Iron Gate | `retlab-iron-gate-campaign-notes.md` |
| Nevada — Red Flag 81-2 | `retlab-red-flag-81-campaign-notes.md` |
| Vietnam set | `retlab-vietnam-retribution-HANDOFF.md`, `-notes.md`, `-ops-notes.md`, `-red-tempo-notes.md` |
| Iraq map 2.9.28 content | `retlab-iraq-map-2928-notes.md` — authoring plan, not yet built |

### System notes — `docs/dev/design/`

- **IADS / air defense** — `retlab-skynet-return-notes.md` (**start here** — Skynet is the
  engine again as of 2026-09-12; the MANTIS bridge, its three notes and the MIST shim are
  gone), `retlab-sam-site-realism-notes.md`,
  `retlab-air-defense-planning-notes.md`, `retlab-qra-player-manning-notes.md`,
  `retlab-sam-magazines-notes.md` (**scoping only, nothing built** — cross-turn SAM missile
  stock on the §81 architecture; the IADS/ROE seam is verified clean and the off-mission
  drain hook found, so it is buildable on a decision)
- **EW / ISR / comms** — `retlab-c130-ew-isr-notes.md`,
  `retlab-gps-jamming-notes.md`,
  `retlab-iads-c2-consequences-notes.md`
- **Recon** — `retlab-recon-role-scoping-notes.md`
  (**scoping only, nothing built** — what job recon gets now that engaging a site is the
  only reveal; also records the command-post hole the rework opened)
- **CSAR** — `retlab-csar-notes.md` (**the one CSAR doc**; supersedes the eight earlier
  SCAR/CSAR notes, all deleted 2026-08-20)
- **COIN** — `retlab-coin-insurgent-replenishment-notes.md`, `-reinfiltration-notes.md`
- **Naval** — `retlab-cruise-missile-raids-notes.md`, `retlab-naval-magazines-notes.md`,
  `retlab-carrier-deck-decor-notes.md`
- **Ground / frontline** — `retlab-tic-dynamic-fronts-notes.md`,
  `retlab-airlift-capacity-notes.md` (**BUILT 2026-08-26** — airlift capacity was one
  constant, `1 if helicopter else 2`, times a raw vehicle count; both halves are now
  graded in ~7-tonne lift slots, cargo cost from the existing `class:` field and
  aircraft capacity from an optional `airlift_capacity`. **`cabin_size` is NOT this**
  — it is clamped CTLD infantry seats and the C-17A and An-26B both read 24. The
  fallback is the old constant, so unauthored airframes are unchanged),
  `retlab-het-convoy-notes.md` (**scoping only, nothing built** — a ground transfer
  spawns its own cargo, so ten T-90Ms road-march themselves between bases; heavy
  equipment transporters on §78's existing `ConvoyUnit.shipment` manifest model.
  Needs the 2026-08-26 patch's SLT-50/HX81, so it is gated on the pydcs re-export),
  `retlab-observer-gated-artillery-notes.md` (**scoping only, nothing built** — frontline
  artillery fires once, blind, at a stale spawn point; fire it when a TIC unit sees an
  enemy, reusing TIC's sight results, airfields excluded),
  `retlab-front-movement-arrows-notes.md` (**BUILT 2026-09-23, not flown** — display-only
  arrows for last turn's front movement; makes B66 readable, so the §90 gate did not
  block it; row B139)
- **AI behaviour** — `retlab-ai-threat-reaction-notes.md` (**§94, adopted 2026-08-24 from
  juanjux #63** — why the baseline is Passive Defense, the `aiReactionExempt` protocol any
  plugin setting reaction-on-threat must use, why we took his head and not the merged PR,
  and the pre-registered falsifier if AI attrition rises)
- **Iran air defense (§105)** — `retlab-iran-air-defense-pack-notes.md` (the unit-id
  contract, the research and best-estimate numbers; **the mod is not built yet** — the local
  build is `retlab-iran-air-defense-pack-HANDOFF.md`)
- **Neutral factions** — `retlab-neutral-border-defense-notes.md` (**§98** — the engine
  verdict on why a true neutral cannot fire, the opposing-coalition clone mechanism, the
  DM-locked rules incl. derived alignment (airfield-hosting decides the side), the
  overflight/refuses split, the accepted shadow-risk and its recorded fallback, the
  real-data border pipeline, and the DECIDED-not-built automagic direction;
  fictional-overlay campaigns are out of scope),
  `retlab-national-postures-notes.md` (**RESEARCHED 2026-08-25, data drafted, nothing
  wired** — `resources/borders/national_postures.yaml`: 47 countries, 244 dated posture
  ranges, both blocs, five buckets. Also the measured country-per-map table that
  **corrected four errors in the research brief's from-memory list** (India on the
  Afghanistan map; no Qatar/Bahrain/Saudi on the Persian Gulf map; Belgium not Germany
  on Normandy/Channel; Saudi Arabia on the Syria map), the two rules that decide the
  hard cases, and the four gaps between the data and §98 as built. **Armenia and
  Azerbaijan are not pydcs countries either** — the same hole as Turkmenistan, on the
  most-used terrain). **Answers the pre-1991 geometry blocker**: CShapes 2.0 is
  CC BY-NC-SA and historical-basemaps is GPL-3, both gated, but **GSHHG/CIA World
  Data Bank II is LGPL over US-Government public domain** and its 1972-77 vintage
  covers every boundary the fork needs — the work is assembling its line segments
  into polygons, not finding data
- **Strike targets / BDA** — `retlab-scenery-kill-tracking-notes.md` (why some scenery strike
  targets never register as killed; the M4 IADS stand-in; the proxy unit that was built and
  reverted, and the position matcher measured to have no input. **The reported failure was never
  reproduced — read §8.1 before building anything here**)
- **Planning / doctrine** — `retlab-hq-priority-targets-notes.md` (**§103, BUILT 2026-09-23,
  not flown** — juanjux's High Command objective rating without its prizes: importance per
  enemy target from our own numbers, a panel line and a blue-only planner weight; difficulty
  is not built; the whole High Command is on "watch, decide later"; row B140),
  `retlab-planner-doctrine-mining-notes.md` (**the working
  procedure for teaching the scripted planner, and the queue** — juanjux's LLM played six
  campaigns as red and wrote down what a competent commander must do; we mine that for
  things our planner *cannot express*, and build them as ordinary Python. **No LLM runs in
  this fork under this programme** — not behind a setting, not opt-in. Read its guardrails
  before proposing anything: seam 7 stays dropped, and the method changes the cost of a
  candidate, never the standard of proof. First one built is §69's CAS extension),
  `retlab-falcon-bms-campaign-notes.md` (**study note** — what the
  BMS dynamic campaign actually does, the full crosswalk to fork features, four gated
  candidates, and the tombstones it must not resurrect — §48/§53/§54 and turnless),
  `retlab-region-priorities-notes.md` (**BUILT 2026-08-20 as §93** — per-CP blue planning
  priorities: upstream #686's surface × BMS's PAK weight; the fence stays dead with §40;
  B89 app pass owed),
  `retlab-campaign-architecture-notes.md` (**direction note** — the one-substrate architecture
  and rungs R0–R7; see the tracking table),
  `retlab-substrate-inventory-notes.md` (**R0, done 2026-08-20** — every campaign quantity's
  writers/readers/cockpit path with receipts; verdict: the core is already coherent, two
  private ledgers exist (§81/§63 magazines), five couplings missing; R1 reshaped smaller),
  `retlab-substrate-HANDOFF.md` (**start here to continue the substrate work** — repo state,
  the local-only queue incl. the B65–B68 and B89 passes, R1's opening moves, reserved
  decisions, and this line's traps),
  `retlab-aircraft-task-rebalance-rubric.md`, `retlab-victory-conditions-notes.md`,
  `retlab-wing-growth-notes.md`, `retlab-single-player-loop-notes.md`,
  `retlab-autoplanner-upstream-divergence-audit.md` (**the full fork-vs-upstream planner
  diff**, 2026-08-09: every divergence classified by gate and default; read before
  reverting or carving planner behavior)
- **Cockpit / data** — `retlab-dtc-cartridge-notes.md`, `retlab-weapon-dates-proposal.md`,
  `retlab-dynamic-spawn-templates-notes.md` (**§101, BUILT 2026-09-15, not flown** — one
  client flight per base and type is marked as DCS's Dyn.SPAWN Template and the warehouse
  link written, so a dynamic-slot jet inherits that flight; the editor's own Lua reads
  loadout, properties and livery off the template, but route carry and the missing `wsType`
  are decided in native code — row `B125` owns both),
  `retlab-my-aircraft-notes.md` (**§102, BUILT 2026-09-22, not flown** — the My
  aircraft window, saved points and drawings per airframe, the per-airframe DTC
  tab; §5a: four §74 schema defects found and fixed 2026-09-22; rows `B135`/`B136`),
  `retlab-startup-times-notes.md` (**where a `startup_minutes:` value may come from** — read
  before adding one; unsourced numbers are the failure mode),
  `retlab-loadout-integrity-audit-notes.md`
- **Terrain / maps** — `retlab-marianas-wwii-terrain-notes.md` (**Marianas 1944,
  `MarianaIslandsWWII`: BUILT 2026-08-22** — 11 airfields exported and verified, the
  shared-grid proof that let the projection and landmap be lifted from the modern
  Marianas, and the traps to re-read before doing this again: the stand-list export's
  backslash and module-reload traps, the landmap-directory substring collision, the DCS
  install folder not matching the theatre id, and **Pagan sitting in the sea zone**.
  No campaign authored, so it is not reachable from the New Game wizard yet)
- **Framework / tooling** — `retlab-framework-consolidation-notes.md`,
  `retlab-skynet-return-notes.md` (**MIST is upstream's again; the shim is gone, 2026-09-12**),
  `retlab-moose-ops-opportunity-map.md`, `retlab-lua-plugin-harness-notes.md`
- **Structure / debt** — `retlab-doc-mass-notes.md` — the 2026-08-19 trim of
  `retlab-features.md` (104.3k → 95.8k words, all 91 sections and every §N anchor intact):
  what was cut, the constraints extracted out of removed features before cutting, the six
  sections still needing sub-headings, and **how to replace a section without destroying its
  neighbours** — the first attempt silently deleted four live sections.
- **Process** — `retlab-verification-cadence-notes.md` (the fly-card throttle, proposed),
  `retlab-sim-thread-freeze-notes.md` (**read before chasing a stutter** — the 2026-09-20
  evidence ledger: TIC's retry, the 15 s `state.json` write and §94's sweep were each
  accused and each cleared by a checkable test (test 37's stalls are locked to a 5 s cycle,
  not to their 15/30/60 s timers — test in model time, never wall time); the in-cockpit
  slowdown tracks the human in the jet, not the battle; the `profiler` plugin measures the
  rest — runbook and how to read `MooseProfiler.txt`),
  `retlab-dcs-update-2026-08-26-notes.md` (**the 2026-08-26 DCS patch triaged against this
  tree** — the stale pydcs pin that blocks everything, three silent-breakage candidates
  (the replaced BMP-3, the §71 AGM-45B clsid collision, the F-4E SUU-23 migration), the
  AH-64D DTC as §74's next airframe, the F-16C ROE tab whose Air Target Data Table is
  derivable from the campaign's own order of battle (**and whose shipped default marks
  blue's own JF-17 hostile on Northern Russia**), and the rows to re-run. Written from
  the patch notes alone — **nothing in it is verified against an updated install**),
  `retlab-dcs-log-noise-notes.md` (**read before triaging a `dcs.log`** — which lines are
  ED's, which are mods', and which are ours, with the evidence for each; the ATC rows
  are the cautionary case, since `INVALID ATC` fires during terrain init for helipads
  that are not in our `.miz` at all, on every map),
  `retlab-dcs-olympus-notes.md`, `retlab-ui-redesign-directions.md` (+ `-mockups.html`),
  `retlab-ui-consistency-audit-notes.md` (**the UI text house style** — US English, NM,
  descriptions visible and naming other settings rather than pointing at them — the
  2026-09-22 decisions, what the tests guard, and the open UI backlog),
  `retlab-juanjux-fork-watch-notes.md` (**the second fork we watch** — his adoption ledger,
  what is already ours, and the OPFOR-AI precedent for seam 7),
  `retlab-fincenturion-dist-notes.md` (**study note, nothing adopted** — a third party's
  tile ground war, graded per-side intel, PBEM and campaign editor, each measured against
  what this tree already decided; the intel half contradicts the 2026-08-18 §3 call and the
  editor is the blank-canvas feature we removed. Licence unknown: read, never vendor),
  `retlab-red-brain-phase0-notes.md` (**read before proposing anything about red** — seam 7
  framing 3 and its Phase 0; no headroom found, and the pre-registered card that would
  reopen it),
  `retlab-mist-author-repos-notes.md` (**the licence gate on the MIST author's repos, and the
  one worth reading** — his published in-game unit dump is a second ground truth for sensor
  ranges; MIST and SLmod are GPL-3 and his misc-scripts repo is unlicensed, so none of it may
  be vendored into this LGPL-3 tree; per the naming convention his name/handle stay out of
  this repo)

### Superseded, draft or historical

Kept for reading old notes and saves; **do not author against them**.

`retlab-ewrs-retirement-decision.md` ·
`retlab-dismounts-decision.md` · `retlab-ctld-mantis-style-port-scope.md` ·
`retlab-mission-planning-wiki-rework.md` · `retlab-scenery-import-notes.md` ·
`turnless.md`

### Deleted design notes (2026-08-20)

**18 notes, 44,910 words, whose own opening line said "do not author against this."** Each
described a feature that had already been removed, so they were a grep tax with no reader:
the whole point of the file was to tell you not to read it. **They are in git history —
`git show 5db34150f:docs/dev/design/<name>` — and that is the only place they should be.**

**Their names keep the pre-rebrand `414th-` prefix on purpose.** Every one was deleted
while the tree still carried it, so that is the only name the history has — a `retlab-`
path resolves to nothing at those SHAs.

| Notes | What they described | Feature removed |
|---|---|---|
| the eight `414th-scar-*` / `414th-combat-sar-*` notes | the fork’s own CSAR and the Sandy escort | §21/§15, 2026-08-07 |
| the three `414th-campaign-phases-*` notes | the phase classifier and ROE zone layer | §40, 2026-07-21 |
| `414th-vietnam-political-will-roe-notes.md`, `414th-will-generalization-notes.md`, `414th-war-economy-notes.md` | the will and war economies | §48/§53/§54, 2026-07-21 |
| `414th-red-intent-notes.md` | Red Intent adaptive posture | §55, 2026-07-21 |
| `414th-tars-recon-notes.md` | the MOOSE Ops.TARS recon engine | cut 2026-08-05; its `recon` successor removed 2026-08-20 (§12) |
| `414th-airwar-planner-consolidation-notes.md` | the planner consolidation | reverted 2026-08-09 |
| `414th-khe-sanh-campaign-notes.md` | the standalone Khe Sanh campaign | merged into Yankee Station |

**Do not re-add a note here when you remove a feature.** Banner-instead-of-delete is what
produced these: a removal writes a banner, the banner is never revisited, and the file
accumulates. Record the removal in the features doc §N and delete the note. The one thing a
deleted note must leave behind is any **constraint learned from a flown test** — lift those
into the hard-constraints list or the surviving design note *before* deleting.

### Other

- [README.upstream.md](README.upstream.md) — unmodified upstream README (setup, dependencies).
- [references/manuals/](references/manuals/) — the official DCS manuals for 11 aircraft
  modules plus the Supercarrier Operations Guide, copied from the local install. The PDFs are
  gitignored (843 MB); the per-folder `INDEX.md` page maps are tracked. **Read the folder's
  `INDEX.md` first, then extract only that range with `pdftotext -f N -l M <pdf> -`** — these
  run to 1,129 pages, and the Read tool cannot open them here (it renders via `pdftoppm`,
  which is not installed). Use them for procedure, systems behavior, cockpit description and
  carrier ops; **not** for loadouts (payload Lua), weapon dates (CLSID tables) or unit stats
  (pydcs export). The `dcs-aircraft-manuals` skill wraps this.
- [docs/wiki/](docs/wiki/) — the player and contributor wiki, mirrored to the GitHub wiki by
  `wiki-sync.yml` on every push to `main`. **Edit pages here, never in the wiki UI.** Also
  carries the adopted upstream dev-process standards, each with **RetLab:** delta notes.
- `AGENTS.md` mirrors this file — see **Conventions** for the sync process.

## Tech Stack

| Layer | Choice |
|---|---|
| Campaign engine | Python 3.11 (`game/`). Python library catalog (bookmark, reference-only — nothing to adopt now; browse if a new library is ever needed): https://github.com/vinta/awesome-python |
| UI | PyQt (`qt_ui/`) + React/Leaflet client (`client/`) — client NOT type-checked in CI |
| Mission scripting | **Lua 5.1** sandbox plugins (`resources/plugins/`) — no `os`/`io`, no `goto`, definition order matters |
| In-mission framework | **MOOSE** (bundled `Moose.lua`; some plugins vendor classes verbatim) — the standard. **MIST is upstream's `mist_4_5_126.lua` again** (2026-09-12): the 2026-07 MIST → MOOSE shim went with the MANTIS bridge, so `base/plugin.json` is upstream's work-order list plus the fork's `sortie_recorder.lua`. Consumers (CTLD, intercept glue, `dcs_retribution.lua`, the relocate scripts, Skynet) call real MIST; a merged upstream Lua file that calls `mist.*` needs no shim work. See `retlab-skynet-return-notes.md`. MOOSE API docs (bookmark): https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/index.html |
| Units / mission format | pydcs; CurrentHill mod packs in `pydcs_extensions/` |
| CI gates | Black + mypy + pytest + **Lua syntax gate** (`lint.yml`, blocking, gates the release) + advisory luacheck |
| Release | PyInstaller → rolling `latest` pre-release on GitHub |

---

## Key Architecture Patterns

**Planner / Lua split.** Python plans and spawns the mission (flight plans, ROE, templates);
runtime behavior (EW, ISR, frontline firefights) is driven by the Lua
plugins. When a feature has both, the Python side sets up and the Lua side executes — don't
move runtime logic into the planner or vice versa.

**Plugin script injection (the uniform late-init pass).** Most RetLab plugins are normal
work-order plugins. TIC additionally needs its main script loaded **after**
every plugin's config table exists (its init reads `dcsRetribution.plugins.<name>` / MOOSE
at file scope) — an ordering the per-plugin work-order pass can't express. It is a `LuaPlugin`
subclass (`game/plugins/tic.py`, registered in `manager.py`'s `_PLUGIN_CLASSES`; `MooseAtis` is
registered there too, but only to inject the current map's sound files)
declaring `late_init_files()` / `late_init_preamble()` / `should_late_init()`; `inject_plugins()`
runs a **second pass** that calls `inject_late_init()` after the normal config pass. A
missing/renamed init file is now caught by a test (`game/plugins/tests/test_late_init.py`)
instead of the feature silently never starting. (Replaces the old hand-injected
`_inject_*_script()` "scramble pattern".)

**Viewer-aware visibility layer (recon fog).** AI planning and threat math always use ground
truth (`viewer=None`); only the human (BLUE) map/UI are fogged. **One question, asked in one
place**: `TheaterGroundObject.visibility_for(viewer)` returns HIDDEN / UNKNOWN / KNOWN, and
`known_for` + `hidden_on_player_map` are its two leaves. `known_for` gates composition and
threat/detection rings (`recon_intel_fog`); `hidden_on_player_map` fully hides enemy command
posts (`scar_command_post_intel`) and §50's ambush teams. Nothing else is viewer-aware except
`standard_identity_for` (COIN's suspect-until-engaged symbol).
**A site is revealed by engaging it — ordnance on it, or any ground-attack sortie that reaches
it — and is then known completely and permanently, damage included.** Recon/TARPS reveals
nothing except a hidden command post within 3 NM of its target (`reveal_scouted_command_posts`
— the one thing engagement cannot reach, because a hidden post has no marker to frag at).
There is no BDA damage lag: `alive_at_last_recon` / `sync_confirmed_status` /
`alive_for` were deleted 2026-08-18 and `alive`/`is_dead`/`dead_units`/`max_threat_range`/… are
plain truth. Do **not** reintroduce a viewer parameter on those, and do **not** reintroduce the
old `_for_player`/`_for` method twins — that collapse is finished.
**Anything that picks targets FOR blue automatically must gate on the fog** — auto raids
(§63), the carrier strike (§44), any future fire mission. Use
`fogofwar.hidden_from(Player.BLUE, tgo)`, never a bare `hidden_on_player_map`: it wraps
`fog_intact()`, so a host who ticked the reveal overview before passing the turn cannot get
a different target than one who did not. Naming a site the player cannot see hands them a
find they were meant to earn, and the strike that follows makes it permanent. Red is never
fogged. Keep the §50 `map_hidden` skip separate — it applies to both sides.
A runtime **overview toggle** (`game/theater/fogofwar.py`, transient/never-pickled)
short-circuits both fog leaves to ground truth for any viewer, so the *whole* render path +
intel dialogs un-fog with **no** server-model changes. It is a checkbox in the custom map
layers panel (`MapLayersControl`, §18), driven by a state `useEffect` (not a Leaflet
add/remove layer — unmount doesn't reliably fire `remove`) that `PUT`s `/fog-of-war/reveal`
then re-pulls `/game`.
(`game/theater/theatergroup.py`, `theatergroundobject.py`; see features doc §3.)

**Save migration.** Removed/renamed enum *values* migrate in **one place**:
`FlightType._missing_` (`game/ato/flighttype.py`) maps legacy persisted strings to live
members via the `_LEGACY_FLIGHT_TYPE_VALUES` table. The unpickler (`persistency.py`
`_handle_flight_type`) calls `FlightType(value)`, which routes through `_missing_`, so it
carries **no** parallel remap table — only unknown-value tolerance (degrade to BARCAP).
Other persisted state (e.g. fog) migrates in each class's `__setstate__`. When you rename a
persisted enum value, add the entry to `_LEGACY_FLIGHT_TYPE_VALUES` only.

**Lua plugin discipline.** Lua 5.1 only, vanilla DCS units only (no HighDigitSAMs etc.),
define functions before first use. The *Lua 5.1 syntax* job in `lint.yml` runs `luac5.1 -p` over
every `resources/plugins/**/*.lua` as a blocking syntax gate — it catches parse-time errors.
On top of that, the **headless Lua plugin harness** (`tests/lua/`, design note
`retlab-lua-plugin-harness-notes.md`) runs the real plugin scripts on Lua 5.1 via `lupa`
against a faked DCS sandbox inside the normal pytest run — catching the "script errors at
runtime and the feature silently never starts" class + pinning safety invariants (grace
periods, exclusion lists, one-shot latches). First coverage: `vietnamops`. It models no DCS
AI/physics, so real behavior still needs an in-game pass (see the in-game-pass checklist).

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

### Hard constraints — established by flown tests, do not undo

These cost a mission or a crash to learn. Each is recorded in full in the features doc or the
linked design note.

- **Never toggle SAM radar emissions from a plugin.** `enableEmission(false)` caused crashes in
  the C-130 line. Suppression is ROE `WEAPON_HOLD` only. Applies to §51, §63, §77 and the
  C-130 script. Skynet's own go-live/go-dark is that same call, made by the engine on its
  own cadence; upstream has flown it for years. Row G42 watches for a recurrence.
- **Never restore the per-base backstop EWR** (§1). DCS has no non-colliding ground unit — the
  mast sat on taxiways and broke AI taxi routing. Detection is the IADS network alone; a side
  with no EWR losing GCI is by design. Second instance 2026-09-16 (test 35, Long Road to H3):
  upstream's own Incirlik EWR marker sits on the south-west taxiway and the DM had to hand-move
  it before anything would taxi. Any authored ground object inside a field's runway strip or
  apron does this, not only the fork's mast. New Game now logs `Airfield clearance:` for every
  ground object inside a runway band (300 m, 1.6 km) or 80 m of a stand
  (`game/theater/airfieldclearance.py`); it warns, it never moves a marker.
- **Never restore the generic `ewrj` fighter-pod jammer** (§2). Superseded by the C-130J
  platform.
- **The C-130J cues; it never lases or designates.** It carries no targeting sensor in DCS,
  so any laser work stays with the strike aircraft. Retribution also has no FAC(A) task
  type — §38 does the marking job through Vietnam Ops, not as a taskable role. (Lifted out
  of `414th-scar-task-spec.md` before that note was deleted 2026-08-20; it was the one
  constraint in the 18 recorded nowhere else.)
- **Never unify §77 escort jamming with the C-130's standoff model.** §77 strengthens as the
  jammer closes; the C-130's burn-through weakens. Both are intentional and opposite.
- **Never add a land-attack weapon family to the §81 anti-ship pattern list.** §63 and §81 stay
  correct only because their weapon sets are disjoint.
- **Never run §60 radar doubling and a regiment model on the same system.** Pick one per system
  and record which.
- **`powerW` is range, not loudness** (§51, §70). Do not chase audio volume with it.
- **GPS jamming (§86): at most 3 sites per campaign, non-overlapping.** Bubbles are large and
  invisible on the map, and effects do not stack.
- **A mover's DCS group needs a 2-waypoint route** — current position, then destination. A
  single destination waypoint reads as "you are already there" and the group never drives.
  Learned on §49 (removed 2026-08-29); applies to every scripted mover.
- **One undrivable member pins a whole group.** A route push moves a DCS group as a unit, so a
  static emplacement in it yields no movement and a per-frame ground-AI levelling storm. This
  is why §85's missile-battery support section is trucks only.
- **Ground movers must last 90 minutes.** Any player-interactable mover is paced so an intercept
  is still possible late in a mission.
- **Never spawn phantom units.** Every scripted force is a real, tracked unit whose loss records
  natively. Applies to §35, §37, §50.
- **Never script explosions on an airfield.** `trigger.action.explosion` inside a field's
  area puts it into DCS's under-attack state and every AI fixed-wing launch there is held until
  it clears; a recurring barrage never clears it. §36 harassment grounded whole wings this way
  (tests 24, 31, 33, 34) and was removed 2026-09-16. Helicopters are unaffected; a one-off
  strike is not this, a cadence is.
- **A plugin toggle is a second gate.** An unticked plugin silently kills its setting — campaigns
  must preseed both (the §36 lesson). A `skipUI` plugin has no checkbox and is always on
  (`LuaPlugin.enabled`), so it needs no preseed: `base`, `intercept`, `opscsar`, `vietnamops`.

### Live features

1. **QRA intercept reserve** — per-squadron alert reserve feeding the Moose `AI_A2A_DISPATCHER`, with player-manned cold alert, a scramble cue, and forward-defense border zones.
2. **JAMMING flight type** — the C-130J as an EC-130H/RC-130H EW + ISR platform (`c130j` plugin).
3. **Recon intel fog** — an enemy site's composition stays hidden until you engage it (ordnance on it, or any ground-attack sortie that reaches it); once engaged it is known completely and permanently. There is no BDA damage lag. Recon's only job is finding the enemy command posts, which are hidden from the map outright and so cannot be engaged at all.
4. **UI transparency** — target intel panel, mission-impact debrief, package context bar.
5. **Player target location precision** — `Approximate` mode offsets steerpoints and hides exact coords.
6. **Air-defense planning rework** — overlapping jittered BARCAP waves. **The geometry/volume half was REVERTED to upstream 2026-08-09** (re-convergence work order D): no forward CAP line, no threat-weighted volume or orbit bias, no front-anchor guarantee, no forward-middle layer, no front-anchored support orbits, no FLOT navmesh hazard. Kept: the overlap waves, the `cap_orbit_distance_band` fix, the Vietnam-only escort-reserve trim.
7. **Auto-hide mobile SAMs on MFD** — SHORAD/AAA/MANPAD off datalink; MERAD/LORAD stay visible for SEAD.
8. **Robustness / crash fixes** — helo CFIT, carrier-recovery stagger, convoy runway spawns, support-flight radio collisions, locked speed/time route rejection.
9. **TIC — Troops In Contact** — scripted frontline firefights with per-stance movement and ambient fire.
10. **CurrentHill Iran assets pack** — Shahed-136, IRGCN FAC, `[CH] Iran 2020` faction.
14. **Plugin Options UI** — `descriptionInUI` field plus label and default polish.
16. **Settings QOL audit** — dead-field cleanup and the `AiRadioBehavior` enum consolidation.
17. **Auto-planner target unpredictability** — opt-in per-side reordering of opportunistic offensive targets only.
18. **Fog-of-war overview toggle** — transient reveal, never persisted, and fenced out of generated missions.
19. **Unified map layers panel** — one grouped control with preset views; air-defence rows filter the master.
22. **Kneeboard space-utilisation + custom import** — per-campaign imported kneeboard images.
23. **Per-squadron DCS country** — nation-specific voiceovers and pilot names, pinnable per squadron.
24. **Date-gated aircraft properties** — era-gated payload-editor options under `restrict_props_by_date`.
26. **Off-mission combat fidelity** — capability-weighted auto-resolution plus the PLAYER_AT_IP fast-forward fix.
27. **Shared-airframe kneeboard index** — one index page when several client flights share a type.
28. **Settings IA reorg + difficulty presets** — metadata-driven layout, difficulty presets, search filter, and the RetLab Features page.
29. **Campaign SITREP** — a last-turn digest on its own kneeboard page, the web ribbon, and the Qt debrief.
32. **Arc Light** — heavy bombers walk a bomb carpet across a Strike target *(Vietnam Ops)*.
33. **AAA flak gauntlet** — barrage flak that tightens against predictable run-ins *(Vietnam Ops)*.
34. **Naval gunfire support** — call-for-fire and automatic coastal bombardment *(Vietnam Ops)*.
35. **Convoy interdiction** — real tracked trail convoys hunted via Armed Recon *(Vietnam Ops)*.
37. **Super Gaggle** — real squadron helos resupplying a cut-off outpost *(Vietnam Ops)*.
38. **FAC(A) willie-pete marking** — an OV-10 marks the largest enemy concentration *(Vietnam Ops)*.
39. **Snake and nape** — detonation-anchored napalm fire from a low fast release *(Vietnam Ops)*.
41. **High Digit SAMs Ultimate Compilation** — S-400, S-300V4, SAMP/T, Pantsir-SM, period EWRs.
42. **Local DCS chart base layers** — locally installed XYZ tile pyramids as extra base maps.
43. **Per-aircraft flight defaults** — saved fuel and cockpit properties per airframe.
44. **Long-range carrier ops** — a deterministic package off a standoff boat, routed to its own tanker.
45. **Support-package F10 orbit markers** — tanker and AEW&C racetracks drawn with callsign, freq, TACAN.
47. **Continuous campaign clock & weather** — one marched clock with weather evolving from the previous turn.
50. **Convoy ambush + ambient supply convoys** — untelegraphed ambush teams on friendly roads, authored as native DCS triggers.
52. **Command-center decapitation** — a headless HQ picks targets worse and frags fewer offensive packages.
56. **Strikeable motorpool depots** — the reserve armor pool made bombable, 1:1 with no economy.
58. **Mission-start briefing popup** — per-pilot slot-in cards with a beep and the taxi call.
60. **SAM guidance-radar redundancy** — two spaced track radars, so one HARM is not a site kill.
61. **Host red-interceptor scramble** — an F10 bandit spawner for a quiet event.
62. **Squadron-sequenced modexes** — per-squadron blocks numbered in sequence for Hornets; the Tomcat paints its number into the livery, so its squadrons fly a CAG bird and line jets instead. The Payload tab can pin a Hornet/Tomcat flight's number (wingmen follow); no other package reuses it.
63. **Ship-launched cruise missile raids** — finite no-rearm magazines, auto raids and an F10 call-for-fire, with a defender launch wake.
64. **Carrier deck spawn policy** — six-pack as last resort plus the MP slot-timing fix.
65. **Curated carrier comms** — per-hull TACAN, ident, ICLS, Link 4 and ATC feeding the CV Operations Data page.
66. **Generated-mission archive** — a dated copy of every generation, in a folder DCS lists.
67. **Weather-aware auto-planning** — rain grounds auto-recon; storms demote low-level attack.
68. **Adaptive procurement** — price-weighted buys and optional SAM site repair.
69. **SEAD-before-strike coordination** — strikes retimed behind the suppressor servicing their target.
71. **Expanded F-4E Weapons Pack** — AGM-78 Weasel fits gated on live pylon legality.
72. **Carrier deck decorations** — island-street and LSO dressing, clear of every parking spot and standing for the whole mission.
73. **Per-airframe default loadout for a task** — pin a fit for an airframe and task across campaigns.
74. **Native DTC data pre-population** — auto-loading cartridges for Hornets, Vipers and F-14B(U)s, with a per-flight DTC tab.
75. **Custom victory conditions** — authored win/lose blocks plus generic domination and attrition endings.
76. **CTLD paratroopers** — fixed-wing Air Assault by paradrop, player and AI.
77. **Escort jamming** — EA-18G and EA-6B only; non-stacking spoof bubbles and SAM weapons-hold pulses.
78. **Sea-supply convoys + coastal anti-ship** — proportional convoy losses and batteries that actually engage.
80. **Mixed-hull ship groups** — task groups instead of copies of one hull, family-bounded.
81. **Cross-turn naval magazines** — staggered weapons-free release and finite anti-ship stock, released on attack.
83. **SP Pilot Mode** — accept-and-fly-next, an aircraft-first sortie board, and a pre-turn reasons-to-continue brief.
85. **SAM/missile battery support sections** — refuellers, power and transload in the faction's own kit.
86. **GPS jamming** — satellite-guided weapons released inside the bubble land long.
87. **Naval station-keeping racetracks** — anchored ovals so ships hold station under way.
88. **Angled-deck carrier recovery heading** — the boat steams for 25 kt down the angled deck, not the bow.
90. **Front-line model** — reinforcement follows the supply lines, attacking costs more than defending, the line's position counts the forces actually present, terrain slows the advance, and the front bulges instead of running straight. The map arrows last turn's movement on each front.
91. **Per-flight sortie records** — the mission reports back what each flight did: track, time airborne, fuel, shots and hits, not just which units died.
92. **What's New** — a toolbar window listing the recent player-visible changes, each with what to look for in the next mission.
93. **Region priorities** — per-control-point BLUE planning emphasis: emphasized regions rank closer, deprioritized farther, ignored left to manual packages. A weight, never a fence.
94. **Smart threat reaction** — only the flight a missile is actually guiding on goes defensive; everything else holds formation and uses countermeasures.
95. **Pinned bullseye** — one bullseye for the campaign instead of a new one every turn, never anchored on a ship or an off-map spawn; the kneeboard names the place it sits on and flags the rare turn it moves.
96. **Player career logbook** — a permanent record per pilot: sorties, combat sorties, hours airborne, air/ground/naval kills, ejections and rank, folded from what the mission actually recorded. Ranks are data, not code. A record, never a reward — nothing here unlocks an aircraft or gates a mission. Awards were removed 2026-09-22.
97. **Lifetime pilot profiles** — your own flying kept across every campaign, not just the current one: totals, a breakdown per aircraft, and the individual flights. Identified by DCS player name, so it needs no setup and a multiplayer host records every pilot who flew. Stored outside the save, which is what lets it outlive a campaign.
98. **Neutral-faction border defense** — every nation on the map is drawn with its real border, the map's own nation included: alignment derived from who holds the airfields inside it, counted per country (both sides holding it = contested grey, claimed by neither QRA; a country in the war is outline-only; red-aligned airspace joins §1's QRA accept zones), and a country not in the war defends (overflight is derived from the same airbases: you may cross what you fly from, and what both sides fly from) — it stands live SAM batteries inside its border from mission start, in two tiers -- the era picks legacy (SA-2/3/5) or modern (SA-10/11, plus Hawk/Patriot/Rapier for the western-equipped list) and the country's room picks the rung, the top band being the same in both eras -- and counted off it too (~1 per 200 NM of war-facing frontier, capped at 6, map clip and far-from-the-war stretches unmanned), each placed well short of what its missile claims, so the frontier sits inside the envelope with margin rather than on its edge, visible before you cross, and hailing you on entry; press, and the WHOLE country turns hostile in place on your enemy's coalition and engages. Both sides violating one country gets a second set. Countries DCS does not model (Turkmenistan, Uzbekistan, Tajikistan, Armenia, Azerbaijan) borrow a neighbour's units rather than being dropped. Players only; AI is never engaged, unless the `engageAi` plugin option is ticked -- a testing override, default off, that holds AI to the same ladder. The fighter patrol was dropped 2026-09-07 -- scope is the SAM.
99. **Sandy rescue escort** — an armed escort that works the ground around a downed pilot while the helicopter comes in: a track centred on the survivor, flown by the A-10 and the Apache. Hand-fragged only — the auto-planner never adds one.
100. **King on-scene commander** — the player-flown C-130J King finds the survivor by DF cuts on the beacon (two cuts far enough apart make a fix; inside pod range with line of sight it snaps exact), sweeps the ground around the fix for threats reported as a class and a rough position, and passes the picture — text and map marks — to the player-crewed Sandy and helicopter. Cues only: it never lases, and nothing is pushed onto an AI flight.
101. **Dynamic spawn templates** — a pilot who takes a DCS dynamic slot no longer gets a blank jet: at each base, one player flight of each type is marked as DCS's Dyn.SPAWN Template and the warehouse link written, so the dynamic jet is built from that flight (loadout, properties and livery for certain; route and radio presets are decided in native code and are what row B125 flies). Client flights only, no clone, and the fragged slot still flies as itself. Types with no player flight at the base stay blank. Off with `dynamic_slots`, and its own toggle beneath it.
102. **My aircraft, saved points and the DTC options** — one window for the seat you are flying: saved points (waypoint, IP, target, hold, orbit) and drawings, the loadout and the data cartridge. Points and drawings reach the Hornet, Viper, F-14B(U), Apache and A-10 where each cockpit has a place, and a kneeboard page with the cockpit's numbers. The DTC tab shows only what the jet's cartridge carries, with load-at-spawn or by-hand, waypoint types to leave out, and SAM rings near the route. Window and points ported from juanjux/dcs-escalation.
103. **HQ priority targets** — what losing each enemy target costs the enemy, in that kind of target's own measure (income, front-line vehicles, offensive packages, equipment price), ranked within its kind. A Why it matters line on the target panel always; a blue-only planner weight, gentler than §93, when on. No prize. The objective half of juanjux's High Command.
104. **Runway queue at busy fields** — the taxi allowance at an airfield grows with the departures ahead of a flight, at 45 seconds per jet, so a crowded field's later flights spawn early enough to make their takeoff. A quiet field keeps the flat 8 minutes. The mission starts up to 30 minutes early when a flight needs it; TOTs and the campaign clock stay put. Always on, no setting (DM call).
105. **RetLab Iran Air Defense Pack** — Retribution support for a RetLab-authored mod carrying 3rd Khordad (MERAD, Buk-like) and Bavar-373 (LORAD, S-300-like) plus its 2025 Bavar-373-II with radar-carrying TELARs (SA-12-like), with Skynet entries and `[CH] Iran 2020` presets. The mod itself is built locally from the handoff note; nothing flown yet.

### Retired, removed or shelved — do not restore

Kept numbered so old notes and saves stay readable. Details and rationale in the features doc.

| § | Feature | Status |
|---|---|---|
| 11 | Native DCS DTC cartridge export (v1) | Retired 2026-06-26 — superseded by §74 |
| 12 | Recon engine (TARPS + drone BDA) | Removed 2026-08-20 — the §3 rework left its captures with no consumer |
| 13 | Flight Control ATC | Retired 2026-06-26 |
| 20 | Drop-spawn map unit placement | Removed 2026-08-02 |
| 15 | SCAR — RESCAP "Sandy" rescue escort | Removed 2026-08-07 — see §21 |
| 21 | Combat SAR (fork implementation) | Removed 2026-08-07 — replaced by upstream dcs-retribution#929, which is **an OPEN PR, not merged** (zero reviews as of 2026-08-17). We re-adopt its phases by hand; Phase 5 landed 2026-08-17. The C-130J "King" is fixed-wing CSAR and is **hand-fragged only** — it flies `KingFlightPlan`'s on-scene racetrack (2026-08-26); the auto-planner gate stays. See the adoption log in `retlab-csar-notes.md` before touching the hover height |
| 25 | Compact 3–4 page kneeboard deck | Retired 2026-07-05 |
| 30 | Dedicated kneeboard cover page | Retired 2026-07-13 — new info folds into a stock page |
| 31 | One-page Brief Sheet | Retired 2026-07-13 — BLUF and code words survived |
| 40 | Campaign phases, ROE zones, target release | Removed 2026-07-21 |
| 46 | Route-aware fuel-tank planning (fuel-first) | **Reverted 2026-08-09** — planner re-convergence work order C; tanker tasking is upstream's again and nothing fits tanks. The external-fuel *accounting* helpers survive for the fuel readouts |
| 48 | Commitment ceiling and the political-will economy | Removed 2026-07-21 |
| 49 | Mobile missile relocation (the SCUD hunt) | Removed 2026-08-29 — never relocated a site in three flown attempts; test 24 measured 44.5 m against a 4,000 m radius |
| 51 | Enemy comms jamming | Removed 2026-09-07 — abandoned; audio pressure that never changed the force model |
| 70 | COMINT collection (and the red comms net) | Removed 2026-09-07 — abandoned entire: the collection tiers, the tasking leak, the concealed-site reveal and the audible net |
| 36 | Airbase harassment (and the frontline artillery mode) | Removed 2026-09-16 — the barrage put the field into DCS's under-attack state and every AI fixed-wing launch there was held for the rest of the mission (tests 24, 31, 33, 34) |
| 89 | Living battlespace | Removed 2026-09-07 — abandoned entire: pre-roll, recovery residue, follow-on waves and reactive red (P4's voice net had already gone 2026-08-18) |
| 53 | War economy | Removed 2026-07-21 |
| 54 | Munitions availability | Removed 2026-07-21 |
| 55 | Red Intent adaptive posture | Removed 2026-07-21 |
| 57 | Air-droppable minefields | Removed 2026-09-07 — shelved 2026-07-30 and never resumed; the visible-fake problem was never worth fixing |
| 59 | Ground AI sleep | Removed 2026-09-23 — DM call; never observed doing its job in any flown test |
| 79 | Decoy suspected-activity zones | Removed 2026-08-18 — real forces no longer hide behind circles, so a lone circle would obviously be fake |
| 82 | The Wing Grows (scheduled squadron arrivals) | Removed 2026-08-16 — "doesn't add much except in very specific campaigns" |
| 84 | Old-stock loadout attrition | Removed 2026-08-06 |

Also removed: the blank-start campaign maker (2026-08-02), the SOF capture economy (2026-07-01),
and the MOOSE MANTIS IADS bridge with its MIST shim (2026-06 to 2026-09-12; Skynet and
upstream's MIST are back — see `retlab-skynet-return-notes.md`).

## Repo & Branch Layout

- This repo (`BradySox/RetLab`) `main` = the consolidated, most-up-to-date RetLab build.
- Upstream is `dcs-retribution/dcs-retribution`; RetLab's PR fork is
  `BradySox/dcs-retribution`.
- RetLab's primary "all features" working branch in the dev checkout is still named
  `414th-all-features` (a local branch; the rebrand could not rename it). `main` here =
  that + the Iran pack + a Black/mypy lint pass.

### DCS Liberation — the grandparent project, still alive (WATCH, established 2026-08-07)

Retribution forked from `dcs-liberation/dcs_liberation`, and **Liberation did not stop** — it is
actively developed on branch `develop` (792 stars; **15.0.0 released 2026-06-19**, 14.1.0 in
February, commits landing weekly). Do **not** treat it as an archive of pre-fork history. It is a
second upstream: a parallel evolution of the same codebase, with no shared PR flow and no
obligation in either direction. We take from it; we do not carve to it (upstreaming means
`dcs-retribution/dcs-retribution` — see `main-retribution-means-upstream`).

**The watch:** skim Liberation's release notes when a new version drops (`gh api
repos/dcs-liberation/dcs_liberation/releases`). Their notes are terse and tagged by area
(`[Engine]` / `[Campaign]` / `[Data]` / `[UI]`), so a pass costs minutes. Look for **`[Data]`
first** — data lands cleanly in the fork with no code change and no freeze implications, whereas
their engine/UI work usually collides with fork features that already solve the same problem.

Adopted so far:

| Date | Taken | Notes |
|---|---|---|
| 2026-08-07 | 12 hand-measured aircraft `fuel:` blocks (their 14.1.0 + earlier) | Coverage 22 → 40 aircraft types. Checklist **S7**; features doc §46. |

Checked and **already covered** — do not re-investigate without new evidence: carrier/LHA
auto-targeting, front-line spawn exclusion zones, weapons-by-date gating, turn-less mode. Their
auto-purchase model is **behind** ours (they document a fixed 30-unit front-line threshold; we have
`frontline_reserves_factor` / `reserves_procurement_target`). Genuinely open, not yet pursued:
campaign-designer control of on-road vs off-road front-line travel (15.0.0 — set on the supply
route's M-113 waypoints; we hardcode `PointAction.OnRoad` in `convoygenerator.py` +
`flotgenerator.py`), which would fit the driveable-corridor standard.

**Their docs are worth reading too.** Liberation publishes a Sphinx site at
https://dcs-liberation.readthedocs.io — and its **source is in our tree**, inherited through the
fork (`docs/*.rst`, `docs/conf.py`, `.readthedocs.yaml`). Nothing builds it here and it is stale
(`docs/index.rst` still titles the site "DCS Liberation"; `docs/game/index.rst` is an empty
toctree), but the content is live: `docs/modding/layouts.rst` is the authoritative writeup of the
layout system (`layout.miz` + `layout.yaml`, one group per unit type, the `layouts.p` pickle and
*Developer Tools → Import Layouts*), and `docs/modding/fuel-consumption-measurement.md` is the
procedure for measuring the ~217 airframes that still have no `fuel:` block.

### juanjux's fork — a second high-signal source (WATCH, established 2026-08-19)

`juanjux/dcs-escalation` (renamed from `juanjux/dcs-retribution` 2026-09; the old URL
redirects) is upstream's most prolific non-maintainer contributor's personal
fork: **64 PRs to upstream (28 merged)**, **100 of his own internal PRs**, and **954 commits /
300 files ahead of upstream `dev`** — the same scale as ours, on a different philosophy. He is
also the reviewer whose objection closed our #851.

**The watch:** skim his fork's PR list; read the `[FIX]` ones first, since those land in our
tree unchanged while his feature PRs usually collide with something we solved differently.

```
gh pr list --repo juanjux/dcs-escalation --state all --limit 60 --json number,title,state,createdAt
```

**Verify every claim against our own files before acting** — of the five defects reviewed on
2026-08-19, four were live here and one was not, and the one that was not reads identical at a
glance. The four were fixed the same day (hold-release clamp, two front-line hold causes, and
the IADS C2 graph). Open candidates, the OPFOR-AI precedent for seam 7, and the full ledger are
in [retlab-juanjux-fork-watch-notes.md](docs/dev/design/retlab-juanjux-fork-watch-notes.md).

### The MIST author's repositories — read-only, licence-gated (ASSESSED 2026-08-20)

The author of MIST and SLmod — one of DCS's longest-standing mission scripters — has 7 public
repositories, assessed in full; **one is worth reading and none may be copied.** Per the naming
convention (paid-campaign treatment, 2026-08-20 user call) his name and handle appear nowhere in
this repo, PR metadata or commit messages; the DM holds the link.

- **The licence gate is hard.** MIST and SLmod are **GPL-3.0**; `DCS-miscScripts` has **no
  licence file at all**. This tree is **LGPL-3.0**. Read his work, verify our numbers against
  it, reimplement a mechanism from the DCS API if we want it — never vendor a file, never
  commit his data. (Retiring MIST on 2026-07-10 removed the tree's only GPL-3 file.)
- **The one live repo is his misc-scripts collection** (updated Feb 2026). `ObjectDB2/everyObject.lua` is a
  published in-game dump of `getDesc()` + `getSensors()` + `getAmmo()` for 625 DCS objects — a
  **second ground truth** for sensor ranges that needs no DCS box, unlike `verify_mod_export.py`.
  `IADScript/script_iads_dev.lua` carries a 24-system SAM database with radar rotation periods,
  per-launcher magazine sizes and rearm times.
- **Detection-range candidate — CHECKED 2026-08-20, no defect found. Do not re-run it.** The
  runtime dump and the mission-editor database are not measured against the same target: across
  every unit in the note's table `database ÷ runtime` is a constant **1.4953 = 5^¼** (radar range
  scales as RCS^¼). Normalised, the **Buk SR is exact** and the "~2×" was an artifact. pydcs is
  also not stale — the DM's own 2026-07-20 export matches it on all seven units. Three units still
  disagree (64H6E sr high 33 %, 40B6MD sr low 50 %, Patriot str low 38 %) and need `getSensors()`
  run on our own install to settle; they are vanilla values faithfully mirroring the database, so
  changing them is a data divergence needing its own call, not a bug fix.
- **Corroborated, do not re-litigate:** his IADS calls `enableEmission` **zero** times — same
  conclusion as our hard constraint. And measured Dog Ear detection is 23.4 km against 1L13's
  200.6 km, which confirms Ramius007's objection that closed #887.

Full assessment, including the SAM-magazine and radar-sweep ideas Skynet lacks, is in
[retlab-mist-author-repos-notes.md](docs/dev/design/retlab-mist-author-repos-notes.md).

**He reverted one of ours and was right**: his #40 backed out the support-orbit port because
the FLOT anchoring sent AWACS and tankers over enemy ship groups. We reverted the same geometry
independently on 2026-08-09. Two forks, same verdict, different evidence — do not re-litigate.

### Upstream PRs — standing rules

The PR-by-PR record — every carve, its status, review history and sync notes — is
[retlab-upstream-pr-ledger.md](docs/dev/retlab-upstream-pr-ledger.md). Read it before opening,
updating or re-offering an upstream PR, and re-verify its counts with GitHub first.

- **The upstream PR freeze is in force.** No new PRs until upstream's next beta; updating an
  existing PR is allowed. Only the DM lifts it — commit activity has been misread as the lift twice.
- **Evidence to bring the DM** is whether `test/1.6` has had a build since 2026-07-25 (the one-line
  check is in the ledger). Use the unfiltered Actions push view; a `branch:dev` filter hides it.
- **Scoped exception:** a PR that answers an open issue in the
  [upstream issue ledger](docs/dev/retlab-upstreaming-inventory.md#upstream-issue-ledger) may be
  opened. Check the issue's timeline for linked PRs first (#951 was a duplicate). Anything else
  is the DM's call.
- **Do not re-carve:** the HDS support (#956 carries it), #873's culling exemption (premise
  wrong), the Splash Damage tuning (#880, a preference).
- **Fork positions a sync must not undo:** `sweden_2020` keeps the KC-135 (#946's tanker half);
  the ATMOS-X station picker reads `starting_coalition`, not `captured` (#927).
- **Coordinate before carving into:** QRA (#782), frontline (#823, #681), SEAD (#772),
  kneeboard (#754), ATC, player region control (#686). The planner is open again; read #674's
  thread before carving target selection.

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
The current Windows virtual environment may have
`home = ...\tmp\uv-python\cpython-3.11.15-windows-x86_64-none`; when it does,
that `tmp/uv-python` directory is the base interpreter for `.venv`, **not a disposable
cache**. Deleting it breaks `run_retribution.bat` with "No Python at ...". Either preserve
the directory or rebuild `.venv` against a permanent Python 3.11 installation first.
Cleanup scripts and agents must never recursively delete `tmp/` without this check.

**`resources/plugins/splashdamage3/Splash_Damage_3.4.2_RetLab.lua`** — RetLab's
buddy-tuned Splash Damage build (`overall_scaling=0.6`, `rocket_multiplier=0.8`,
`static_damage_boost=1`, shaped-charge rocket flags, `game_messages=true`). Do NOT overwrite
it from upstream. Settings are LOCKED by design: `plugin.json` has no `specificOptions` and
`sd3-config.lua` was removed. Don't reintroduce the config layer. (The *values* are an
upstream candidate — inventory item 21. **That carve is OVER: PR #880 was CLOSED 2026-08-06
on the DM's call — "it's a preference we use, not everyone else."** The tuning is a RetLab
preference, not a bug fix owed upstream, so it lives here permanently. This is a deliberate,
named exception to the everything-upstreamable policy; do not re-carve it without a fresh
call. The two genuine *bugs* found alongside it — see below — are a different matter.)
**Audited against upstream's `Splash_Damage_3.4.2_Standard_Retribution.lua` + the wiki's
Plugin-Options page 2026-08-06** — all 33 exposed options agree with our locked values (the
percent options map through upstream `sd3-config`'s `/100`: `overall_scaling` 60→0.6, rocket
80→0.8, dynamic blast 100→1), and the value drift is the documented tuning. Two
upstream-authored blocks are absent from our copy, both **deliberately dropped** by the
bake-in commit `6f3fc284b` (2026-06-11), which names them: **`shipRadarDamageEnable`**
(HARM → ship radar), which stays out — it works by `obj:enableEmission(false)`, the call the
C-130 constraint records as a crash cause — and **`oca_aircraft_damage_boost`** (3000×,
parked aircraft, "so OCA/Aircraft missions are viable"), **RESTORED 2026-08-06 on the DM's
call**. The two were one contiguous region of the same function, so the OCA half reads as
collateral to the crash-risk removal; restoring it costs OCA/Aircraft strikes nothing and
buys back the kill probability upstream added it for.
⚠️ **Upstream's own copy of the OCA block is broken and ours is not a verbatim copy**: it
calls `getAGL(obj)`, a helper defined **nowhere** — not in the script, `Moose.lua`, or the
MIST shim (grep the tree: zero definitions) — so it raises "attempt to call a nil value" for
every object past `cascade_damage_threshold`, inside the `world.searchObjects` `ifFound`
callback. The fork's port computes AGL inline (`getPoint().y - land.getHeight`) and only for
aircraft. Do NOT "resync" this block from upstream until they fix it.

---

## Conventions

- **Anything published to GitHub is written plain (STANDARD, 2026-08-07 user call — "I'm not
  reading 90% of your output text, you need to cleanse it of your bullshit").** README, wiki
  pages, PR bodies, changelog entries, issue comments and commit messages state what changed and
  why. They do not perform.
  - **No voiceover.** No dramatic reveals ("Some of those circles are lies"), no
    "X isn't a Y — it's a Z", no rhetorical build-ups, no closing flourish.
  - **One fact per line.** If a bullet needs three sentences to land, it is three bullets or it
    is a table. Long paragraphs are the failure mode — nobody reads a 120-word bullet.
  - **Bold marks a term, not emphasis.** If every other phrase is bold, none of it is.
  - **Lead with the thing the reader came for.** Download links, the command to run, the actual
    change — first, not after three paragraphs of context.
  - **No changelog-in-prose.** "This was reworked twice, first as X then as Y" belongs in the
    design note, not in a reference page. State what is true now.
  - **Two exemptions.** In-fiction campaign material (briefing packs, intel assessments, role
    cards) keeps its voice — it is read aloud to a squadron and the voice is the point. Mirrored
    upstream wiki pages keep upstream's wording, with fork deltas in **RetLab:** notes.
  - **A doc that describes a removed feature is worse than a wordy one.** When a feature is cut,
    grep the README and `docs/wiki/` for it in the same change.
- **Code comments record why, never what (STANDARD, 2026-08-11 user call).** A comment earns
  its place by saying something the code cannot: a constraint learned from a flown test, a
  deliberate exclusion, an upstream bug being worked around. Never narrate the next line.
  - **Cap a block at ~3 lines.** Longer rationale belongs in the feature's
    `docs/dev/design/` note; the comment becomes one line pointing at it.
  - **A plugin or module file header may run to ~15 lines** — it is the entry point for a
    reader who has no other. Shape: one line of purpose, the `docs/` pointer, then the
    constraints a reader could undo by accident, one line each. Everything else goes in the
    note. Reference: `resources/plugins/intercept/intercept-config.lua` (104 → 16 lines).
  - **A pointer must resolve.** Confirm the file exists before committing the reference — a
    dead `docs/dev/...` pointer is worse than none, and one shipped in the first draft of
    this very sweep.
  - **Data files carry values, not essays.** A unit yaml gets the number and nothing else —
    the reasoning lives in the design note. The `Air Assault:` priorities are the reference
    case: a tier scheme with per-file justifications was written and stripped the same day.
  - **Compress a constraint comment, never delete it.** The hard-constraints list above exists
    because those cost missions to learn, and most of them live in comments. Wordiness is a
    smaller failure than re-opening a settled question.
  - Measured 2026-08-11: the fork ran **8.3%** comment density against upstream's **4.8%**, and
    2.5× its rate of multi-line blocks. Re-measure before claiming a cleanup worked.
- **UI text house style (STANDARD, 2026-09-22 DM call).** Every user-visible string is US
  English (field names keep their spelling); nautical miles are `NM`; a setting's description
  renders in full, names another setting by its label rather than "above"/"below", and never
  describes a removed feature as live. `tests/settings/test_settings_text.py` guards the
  settings; the rules and the open backlog are in `retlab-ui-consistency-audit-notes.md`.
- **ADHD-friendly agent output (STANDARD, 2026-07-20).** The reader has ADHD; every agent
  reply is shaped so an ADHD brain can act on it. The rules live in the vendored
  [`i-have-adhd`](https://github.com/ayghri/i-have-adhd) skill
  (`.claude/skills/i-have-adhd/SKILL.md`, MIT, byte-identical to upstream — update by
  re-copying upstream's `skills/i-have-adhd/SKILL.md`; keep the sibling `LICENSE`). Treat it
  as **always-on**, not invoke-on-request: lead with the next action, number multi-step work,
  end with one concrete next action, defer tangents, restate state each turn ("step 3 of 5"),
  concrete time estimates, visible wins, matter-of-fact errors, lists capped at 5, no
  preamble/recap/closing pleasantries. The skill's own exceptions apply (full explanations
  when asked, confirm destructive actions, stop iterating in a debug spiral, one clarifying
  question on real ambiguity). Composes with the question convention below: a needed decision
  still lands in the ❓ block at the end — that block IS the "one concrete next action."
- **When the evidence contradicts the instruction, lead with that and stop (STANDARD,
  2026-08-23 user call — "I am very often wrong and if you find EVIDENCE that im going
  down the wrong path then speak up and say it").** If something in the tree, a manual,
  a log or a generated artifact contradicts what was asked, the reply opens with that
  finding. Do not build the thing and record the contradiction in a design note — a
  buried contradiction changes nothing and costs the work twice.
  - **The case this exists to prevent** (2026-08-23, the F-14's "7 waypoints"): the ask
    was to drop target waypoints to fit a seven-waypoint route cap. The Heatblur manual
    says the CDNU stores twelve flight plans of fifty waypoints, and that the *PTID
    displays* eighteen at a time under a priority ranking — "seven" is `Priority WP 1-3`
    plus `Generic 4-7`, a display rank, not a capacity. There was no cap to fit. The
    route was trimmed anyway and the finding went into the note.
  - **Evidence means checkable**: a file, a manual page, a measurement, a log line. Name
    the source in the same breath. A *preference* cannot be contradicted by evidence —
    taste calls stand, and "the LAR should read conservative" needs no defence.
  - **Two sentences, then the question.** Not a lecture, not a refusal. If the call is
    reaffirmed, build it in full and say plainly that it was reaffirmed.
  - This outranks agreeableness. Saying "yes" to a call the evidence has already
    answered is the expensive failure, not the polite one.
- **Ask decisions via the AskUserQuestion widget (STANDARD, 2026-07-21 user call).** Whenever
  you need a decision or a choice from the user, use the **`AskUserQuestion` tool** — the
  interactive widget with clickable options — **not** a typed "1, 2, 3" list. Lead with your
  recommended option and mark it "(Recommended)"; give each option a one-line description of what
  it means / its trade-off. Use `multiSelect` when the choices aren't mutually exclusive, and a
  short set of questions (≤4) when several independent decisions are on the table. The user
  considers typed numbered option lists low-effort ("lazy") — the widget is the actual tool for
  this, so default to it.
  - **Fallback — plain highlighted markdown** — only for a quick inline either/or where the widget
    is overkill, or for a **free-text** question with no fixed options. Never bury it mid-paragraph
    or at the tail of a wall of prose: put it in its own block at the **end** of the message, set
    off with a bold marker + blockquote, and lead with your recommended option, e.g.:
    > ❓ **Need your call:** <the question>
  - Do NOT build a custom widget/visualization (`mcp__visualize`, an Artifact) to ask a question —
    `AskUserQuestion` is the one decision surface.
- **Never name a paid campaign anywhere in the repo (STANDARD, 2026-08-07 user call).**
  Third-party DCS campaigns are commercial products. The fork studies them and extracts
  factual data from them (deck-static coordinates, kneeboard page formats, ATC command
  vocabularies), and that is fine — but their **names** do not appear in our code, comments,
  commit messages, PR titles/bodies, docs or wiki pages.
  - **Use stable letters**: `campaign A`, `campaign B`, … Letters are consistent across docs —
    A and B are the two the carrier deck-decor note uses — so a set stays traceable to a
    specific source mission (`campaign A mission 3`) and rules like "never mix sets across
    missions within a zone" stay checkable. Add the airframe when it aids reading
    (`a paid FA-18C campaign`). Publishers get the same treatment.
  - **Install paths are generic** — `<DCS>\Mods\campaigns\<campaign A>`, never the real folder.
  - **This applies to commit messages and PR metadata, not just files.** They are as public as
    the code; a rewrite + force-push on an unmerged branch is the fix.
  - **Three things are NOT covered.** Real-world squadron names and nicknames (VFA-83
    "Rampagers" is a real squadron the campaign is named *after*, not the reverse); real-world
    operation names (Inherent Resolve); and the fork's own campaign names, even where one
    collides with a paid product (our `red_flag_81_2`).
  - **Check with the installed list, not from memory** — `ls "<DCS>\Mods\campaigns\"` is the
    authoritative set of names to avoid.
- **Supply lines follow the driveable corridor (STANDARD, 2026-07-03).** Every authored
  `supply_routes:` / shipping-lane drawing must trace the corridor you would actually *drive*
  between the two points — the road, the river valley, the pass — never a straight line across a
  ridgeline. Retribution binds a route to its CPs by the **first and last** waypoint only, so
  intermediate waypoints are free: use enough of them (3–5) to follow the real corridor. On
  real-world-coordinate maps (Afghanistan, Syria, Sinai, PG, Kola, Normandy, Caucasus…) author the
  intermediates from the **real road network's lat/lon** via `tools/supply_route_geo.py`
  (`Point.from_latlng` → terrain XY; calibrated to ~1–5 km on Afghanistan). For fictional-overlay
  campaigns (e.g. Vietnam-on-Caucasus) trace the on-map roads/valleys visually instead. The tool is
  **multi-campaign** (`python tools/supply_route_geo.py [coin|red_flag_81_2|caucasus_trail_fixes]`);
  the COIN campaign (`coin_enduring_resolve.yaml`, Highway 1 / Route 611 / the Uruzgan road) and Red
  Flag 81-2 (`red_flag_81_2.yaml`, real US-95 / US-6 / the NTS interior) are the reference
  implementations. The built campaigns were audited against this standard 2026-07-03 (see the
  supply-routes design note "Roll-out to the built campaigns"): Nevada re-traced, the worst
  Caucasus-trail defects fixed, the deep-mountain trail FOBs (Yankee Station / Steel Tiger R6–R13)
  left for an in-app by-eye pass, Germany already compliant.
- **SAM belts: legacy → §60 doubling, strategic → regiment-by-authoring (STANDARD, 2026-07-12).**
  When you lay out a **new campaign's** air defenses, choose the redundancy model by system class —
  don't just drop fat single-site batteries:
  - **Legacy / mobile systems** (SA-2, SA-3, SA-6, Hawk, and the generic launcher sites) — a lone
    site is realistic and the §60 two-guidance-radar doubling already baked into their layouts is the
    right fix (defeats the single-HARM kill). Place them as normal; nothing extra to do.
  - **Strategic belts** (S-300 / S-400 / SA-10/20/21, Patriot, the long-range LORAD systems) — prefer
    the **regiment-by-authoring** pattern: place **several single-radar fire units + a shared EWR/
    acquisition site** on the CP and let Skynet net them into one IADS, rather than one doubled fat
    site. That is the historically faithful survivability model (kill one battalion's radar, the
    regiment fights on) and it's what the engine + Skynet already represent when you place multiple
    sites.
  - **Guardrail — never double-count radars.** §60 doubling and a regiment layout both add engagement
    radars. If a future engine "regiment" construct ever lands for a strategic system, revert §60's
    doubling for that system, and **record which systems are regiment-modeled vs §60-doubled** the day
    that starts. Rationale + the deferred directions (geometry, acquisition separation, decoys) live in
    [docs/dev/design/retlab-sam-site-realism-notes.md](docs/dev/design/retlab-sam-site-realism-notes.md).
  - **Reference implementation:** Red Tide's three rear S-300 hubs (2026-07-12) — 3 clustered
    single-radar S-300 battalions + a shared EWR per hub, netted by range-mode advanced IADS, with §60
    reverted only for that campaign's S-300/SA-5 via the `Russia 1980 (Red Tide)` faction fork (the
    front's legacy MERAD screen keeps §60 doubling). See `retlab-red-tide-campaign-notes.md`.
- **Upstream dev-process standards (ADOPTED as ours, 2026-07-20 user call).** The upstream wiki's
  Contributing + Core development guides are the fork's own customs and standards, mirrored with
  **RetLab:** delta notes in `docs/wiki/` (see Project Docs). In practice: follow the
  **Developer's Guide** for dev-env + PR practice (small PRs — one feature/bugfix/change per PR;
  type annotations on all new code; pre-commit runs Black), the **aircraft/terrain module
  checklists** (upstream's P0–P2 items plus the fork's additions on each page) when adding module
  support, the **QGIS shapefile guide** for landmap data, **Modded-Unit-Support** (the 11-step
  guide) for any new mod pack, **Motorpools** when authoring reserve depots into a campaign,
  **Campaign maintenance** for the campaign-ownership model (every fork-authored campaign is
  owned: design note + CI lock), and the **Release process** page for releases (the rolling
  `latest` IS the release; pinned tags are `v<X.Y.Z>-retlab`; never `git push --tags`).
  **Upstream carves ship to these same standards** — they are upstream's own, so a carve is held
  to them by construction: target `dcs-retribution/dev` via the PR fork, one focused
  feature/bugfix per PR, upstream's gates validated locally on the upstream tree before push, a
  `changelog.md` note, fork-only couplings stripped (the harness/plugin extras stay here), and
  module/campaign content meeting the relevant checklist page. When an upstream page changes,
  refresh the mirror and re-annotate the deltas rather than letting the two drift.
- Keep the doc faces in sync: when a feature lands or changes, update **both**
  [`README.md`](README.md) (player-facing) and the relevant section of
  [docs/dev/retlab-features.md](docs/dev/retlab-features.md) (engineering), plus this map if the
  shape changed. A push that moves the code past its docs is a broken push.
- Keep player-facing plugin behavior and any overview docs in sync with code changes.
- **AGENTS.md sync** — `AGENTS.md` is a byte-identical mirror of this file (CLAUDE.md is
  authoritative; only line 1, the title, differs). After editing CLAUDE.md or any `@`-imported
  file, resync it: `cp CLAUDE.md AGENTS.md` then Edit line 1 back to `# AGENTS.md ...`
  (do NOT use `sed -i`; it flattens CRLF). The imported file (`docs/dev/CLAUDE-ci.md`) is shared —
  both CLAUDE.md and AGENTS.md reference the same file.
