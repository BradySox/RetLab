# Design notes

The index of this folder. `CLAUDE.md` points here. Read the matching note before editing
a campaign or a feature: each carries the design rationale, the flown-test findings and
the deferred work. Add a new note to this list in the same change that adds the file.

## Campaign notes

Read before touching a campaign's `.yaml`, `.miz` or build tool.

| Campaign | Note |
|---|---|
| Germany — Red Tide | `retlab-red-tide-campaign-notes.md` (+ `retlab-red-tide-supply-routes-notes.md`, `retlab-red-tide-c2-real-buildings-HANDOFF.md`) |
| Operation Baltic Fury | `retlab-baltic-fury-campaign-notes.md` |
| Marianas — Second Island Chain 2027 | `retlab-marianas-2027-campaign-notes.md` |
| Marianas — Operation Forager (1944) | `retlab-marianas-wwii-terrain-notes.md` (the terrain note owns it) |
| Syria — Anatolian Reach (2004) | `retlab-anatolian-reach-campaign-notes.md` — **Akrotiri stays support-only**; read the note first |
| Iraq — Umm al-Ma'arik (Desert Storm) | `retlab-desert-storm-campaign-notes.md` |
| Falklands — Mount Pleasant 2032 | `retlab-mount-pleasant-2032-campaign-notes.md` — built by `tools/build_mount_pleasant_2032_miz.py`; defensive, plays both ways with Invert Sides |
| Falklands — Operation Corporate 1982 | `retlab-corporate-1982-campaign-notes.md` — built by `tools/build_corporate_1982_miz.py`; plays both ways with Invert Sides |
| Iraq — Desert Aladeen: The H-3 Front | `retlab-desert-aladeen-h3-campaign-notes.md` — built by `tools/build_desert_aladeen_h3_miz.py`; Starfire's original stays untouched |
| Iraq — Operation Inherent Resolve | `retlab-inherent-resolve-campaign-notes.md` |
| Germany — Fulda Gap 1985 | `retlab-fulda-gap-1985-campaign-notes.md` — the `.miz` is the DM's hand laydown, no build tool; SAM sites from Carsten's framework; Gutersloh is a rear base with no road |
| Afghanistan — Red Bear 1985 | `retlab-red-bear-1985-campaign-notes.md` — the `.miz` is the DM's hand laydown, no build tool; Camp Bastion is a rear base with no road |
| Afghanistan — Enduring Resolve (COIN) | `retlab-coin-HANDOFF.md` — **start here for COIN** |
| Caucasus — Iron Gate | `retlab-iron-gate-campaign-notes.md` |
| Nevada — Red Flag 81-2 | `retlab-red-flag-81-campaign-notes.md` |
| Kola — Northern Flank 1985 | `retlab-northern-flank-campaign-notes.md` — Sweden and Finland hold nothing; Luostari has no jet stands |
| Vietnam set | `retlab-vietnam-retribution-HANDOFF.md`, `retlab-vietnam-retribution-notes.md`, `retlab-vietnam-ops-notes.md`, `retlab-vietnam-red-tempo-notes.md` |
| Iraq map 2.9.28 content | `retlab-iraq-map-2928-notes.md` — authoring plan, not yet built |

## System notes

One line each; the status is the note's own. Read the note, not this line, before editing.

- **IADS / air defense** — `retlab-skynet-return-notes.md` (**start here**: Skynet is the
  engine again since 2026-09-12; MANTIS and the MIST shim are gone),
  `retlab-sam-site-realism-notes.md`, `retlab-air-defense-planning-notes.md`,
  `retlab-qra-player-manning-notes.md`, `retlab-sam-magazines-notes.md` (scoping only),
  `retlab-iran-iads-deployment-notes.md` (research: where Iran's SAMs sit, map by map),
  `retlab-exact-site-layouts-notes.md` (§122: FIXED groups generate as drawn)
- **EW / ISR / comms** — `retlab-c130-ew-isr-notes.md`, `retlab-gps-jamming-notes.md`,
  `retlab-iads-c2-consequences-notes.md`
- **Recon** — `retlab-recon-role-scoping-notes.md` (candidate A built 2026-08-18; B and C scoping)
- **CSAR** — `retlab-csar-notes.md` (the one CSAR doc)
- **COIN** — `retlab-coin-insurgent-replenishment-notes.md`, `retlab-coin-reinfiltration-notes.md`
- **Naval** — `retlab-cruise-missile-raids-notes.md`, `retlab-naval-magazines-notes.md`,
  `retlab-carrier-deck-decor-notes.md`, `retlab-antiship-deal-notes.md` (which ship each
  anti-ship flight attacks; row B219)
- **Factions / layouts** — `retlab-modern-fob-notes.md` (HESCO FOB, FARP props, stock CurrentHill units)
- **Ground / frontline** — `retlab-pr823-frontline-merge-notes.md` (read before adopting upstream #823),
  `retlab-airlift-capacity-notes.md` (built 2026-08-26; **`cabin_size` is CTLD seats, not
  airlift**), `retlab-het-convoy-notes.md` (scoping only),
  `retlab-observer-gated-artillery-notes.md` (scoping only),
  `retlab-front-movement-arrows-notes.md` (built 2026-09-23, row B139),
  `retlab-sector-war-notes.md` (§111; Brady's 2026-10-12 choices and the build steps),
  `retlab-trains-notes.md` (§123: trains on drawn rail lines; what the probes showed)
- **Tankers** — `retlab-tanker-box-notes.md` (per-flight orbit speed, the 40 NM racetrack
  every theater tanker flies, and why the four-corner box was removed 2026-10-09; rows
  B152/B206)
- **AI behaviour** — `retlab-ai-threat-reaction-notes.md` (§94; the `aiReactionExempt`
  protocol any plugin setting reaction-on-threat must use), `retlab-ai-fill-notes.md`
  (§113; the AI twin of an empty player flight, row B234)
- **Iran air defense (§105)** — `retlab-iran-air-defense-pack-notes.md` (the unit-id contract
  and numbers), `retlab-iran-air-defense-pack-HANDOFF.md` (the private pack's local build)
- **Neutral factions** — `retlab-neutral-border-defense-notes.md` (§98; why a true neutral
  cannot fire, and the DM-locked rules), `retlab-national-postures-notes.md` (the posture
  table; consent moved to airbases 2026-08-26; the measured country-per-map table)
- **Strike targets / BDA** — `retlab-scenery-kill-tracking-notes.md` (position matcher adopted
  from upstream #957 on 2026-08-30; row B63 verified in test 33)
- **Package route / waypoint editing** — `retlab-package-route-notes.md` (§106; routes are
  edited on the map, never by typed coordinates; rows B150/B151)
- **Planning / doctrine** — `retlab-hq-priority-targets-notes.md` (§103, and §112 HQ requests),
  `retlab-coordinated-tot-notes.md` (§114: a hand-planned package timed behind its SEAD),
  `retlab-planner-doctrine-mining-notes.md` (how we teach the scripted planner; read its
  guardrails first), `retlab-llm-opfor-notes.md` (§109: the outside AI that reads red's turn;
  the 2026-10-09 DM call that reversed "no LLM runs in this fork"), `retlab-falcon-bms-campaign-notes.md` (study),
  `retlab-region-priorities-notes.md` (§93), `retlab-substrate-inventory-notes.md` (R0, done),
  `retlab-substrate-HANDOFF.md` (start here to continue the substrate work),
  `retlab-aircraft-task-rebalance-rubric.md`, `retlab-victory-conditions-notes.md`,
  `retlab-autoplanner-upstream-divergence-audit.md`
  (the full fork-vs-upstream planner diff; read before reverting or carving planner behavior),
  `retlab-cruise-mach-notes.md` (built 2026-09-01; only the F/A-18C is authored),
  `retlab-bullseye-notes.md` (§95), `retlab-flight-report-cards-notes.md` (§108, row B158),
  `retlab-coop-persistent-campaign-notes.md` (scoped, not built)
- **Cockpit / data** — `retlab-dtc-cartridge-notes.md`, `retlab-weapon-dates-proposal.md`,
  `retlab-datalink-era-notes.md` (`DatalinkPolicy`, built 2026-08-16),
  `retlab-dynamic-spawn-templates-notes.md` (§101, row B125), `retlab-my-aircraft-notes.md`
  (§102, rows B135/B136), `retlab-startup-times-notes.md` (read before adding a
  `startup_minutes:` value), `retlab-loadout-integrity-audit-notes.md`
- **Terrain / maps / weather** — `retlab-marianas-wwii-terrain-notes.md` (built 2026-08-22;
  read its traps before exporting another terrain), `retlab-atmosx-live-weather-notes.md`
  (adopted from upstream #927)
- **Framework / tooling** — `retlab-moose-ops-opportunity-map.md`,
  `retlab-moose-bundle-patches-notes.md` (**read before bumping `Moose.lua`**),
  `retlab-lua-plugin-harness-notes.md`, `retlab-splash-damage-notes.md` (why the Splash
  Damage build is pinned)
- **Structure / debt** — `retlab-doc-mass-notes.md` (the 2026-08-19 features-doc trim, and
  **how to replace a section without destroying its neighbours**)
- **Process** — `retlab-verification-cadence-notes.md` (partly built: WATCH and LOCAL; the
  session-start board was removed 2026-10-12), `retlab-sim-thread-freeze-notes.md` (**read before chasing a stutter**; test
  in model time, never wall time), `retlab-dcs-update-2026-08-26-notes.md` (that patch
  triaged, verified against the install the same day),
  `retlab-dcs-update-2026-10-28-notes.md` (the October patch; the eight new CurrentHill
  units still owe an install export), `retlab-dcs-log-noise-notes.md` (read
  before triaging a `dcs.log`), `retlab-dcs-olympus-notes.md`, `retlab-ui-redesign-directions.md`
  (+ `-mockups.html`), `retlab-ui-consistency-audit-notes.md` (the UI text house style),
  `retlab-campaign-doc-ideas-harvest.md`
- **Other forks and projects we watch** — `retlab-juanjux-fork-watch-notes.md`,
  `retlab-liberation-watch-notes.md`, `retlab-mist-author-repos-notes.md` (licence-gated),
  `retlab-fincenturion-dist-notes.md` (study only; read, never vendor)

## Superseded, draft or historical

Kept for reading old notes and saves; **do not author against them**.

`retlab-scenery-import-notes.md` (`game/campaignloader/scenerycatalog.py` points at it) ·
`turnless.md` (upstream's)
