# RetLab Iran Air Defense Pack — 3rd Khordad and Bavar-373 (§105)

**Status (2026-09-25):** repo side BUILT, unit-tested; the DCS mod itself NOT BUILT. It is
built on the DM's machine from
[`retlab-iran-air-defense-pack-HANDOFF.md`](retlab-iran-air-defense-pack-HANDOFF.md).
Row **B148** owns the flight.

Two Iranian SAM systems that DCS has no model of, chosen because the 2026 Iran war made them
the SEAD problem of the theatre. CurrentHill's Iran pack carries the Shahed-136 and the IRGCN
boats, but no SAM.

## 1. The contract

The type ids are the contract between the mod's `Database` lua and this repo. **Do not rename
one on either side alone.** The pydcs ranges are the best estimates in §3; the mod's own
missile and radar numbers must match them, or this table is updated to what the mod does.

| Type id | Display name | Class | Detection | Threat |
|---|---|---|---|---|
| `IRAD_Bashir_SR` | `[IRAD] 3rd Khordad Bashir SR` | SearchRadar | 200 km | — |
| `IRAD_3Khordad_TELAR` | `[IRAD] 3rd Khordad TELAR` | TELAR | 90 km | 50 km |
| `IRAD_AlamAlHoda_TEL` | `[IRAD] 3rd Khordad Alam al-Hoda TEL` | Launcher | — | 50 km |
| `IRAD_Meraj4_SR` | `[IRAD] Bavar-373 Meraj-4 SR` | SearchRadar | 250 km | — |
| `IRAD_Hafez_SR` | `[IRAD] Bavar-373 Hafez AR` | SearchRadar | 200 km | — |
| `IRAD_Bavar373_STR` | `[IRAD] Bavar-373 STR` | TrackRadar | 200 km | — |
| `IRAD_Bavar373_CP` | `[IRAD] Bavar-373 CP` | CommandPost | — | — |
| `IRAD_Bavar373_LN` | `[IRAD] Bavar-373 TEL (Sayyad-4)` | Launcher | — | 150 km |
| `IRAD_Bavar373_LN_4B` | `[IRAD] Bavar-373 TEL (Sayyad-4B)` | Launcher | — | 200 km |

`IRAD_` is the pack's prefix; `[IRAD]` marks the display names the way `[CH]` marks
CurrentHill's.

## 2. What the repo carries

| Piece | File |
|---|---|
| pydcs unit types | `pydcs_extensions/iranairdefensepack/` |
| New Game toggle `iranairdefensepack` | `game/theater/start_generator.py`, `qt_ui/windows/newgame/` |
| Strip when off | `game/factions/faction.py` |
| Unit data | `resources/units/ground_units/IRAD_*.yaml` |
| Presets | `resources/groups/3rd_Khordad.yaml`, `resources/groups/Bavar-373.yaml` |
| Layouts | `resources/layouts/anti_air/3rd_Khordad_Battery.yaml`, `Bavar-373_Battery.yaml` |
| Radar db | `game/data/radar_db.py` |
| Skynet | `samTypesDB['3rd Khordad']`, `samTypesDB['Bavar-373']` in `skynet-iads-compiled.lua` |
| Factions | `[CH] Iran 2020` gets both; `Iran 2015` gets 3rd Khordad only (Bavar-373 is 2019) |
| Tests | `tests/retlab/test_iran_air_defense_pack.py`, plus the two layouts in the redundancy and support-section tests |

### Layout choices

- **3rd Khordad Battery** — `6_Launcher_Circle.miz`. 1 Bashir SR, **2 TELARs in the Track Radar
  slot**, 4 Alam al-Hoda TELs. The TELAR is the guidance radar, so two of them is the §60
  anti-single-HARM rule, and a site can never roll zero (a TEL-only site is blind).
- **Bavar-373 Battery** — `S-300_Site.miz`, the HQ-22 pattern: Meraj-4 and Hafez in SR1/SR2,
  CP, 2 STRs, LN1 = 3 Sayyad-4, LN2 = 3 of either Sayyad-4B or Sayyad-4. Full §85 support
  section, Soviet kit.
- Bavar-373 is a strategic system; the §60 two-STR layout is used rather than a regiment
  layout. **Record the switch here if a campaign ever authors it regiment-style.**

## 3. Research and best estimates

Sources are listed at the end. Labels: **IR** = Iranian official claim, **W** = Western analyst
estimate, **INF** = inferred. Every best estimate leans conservative against Iranian claims.
The research agent's web fetches were blocked, so these come from search summaries of the
listed pages; re-check before treating any as settled.

### 3rd Khordad (Sevom Khordad), Raad family — unveiled 2014

| Item | Sources | Best estimate |
|---|---|---|
| TELAR | 6x6 truck, 3 Taer-2B on an inclined trainable launcher, flat X-band phased array on the same vehicle; engages alone (IR/W) | as sourced |
| Engagement radar | tracks 100, engages 4, 2 missiles per target (IR); no range published | **90 km detection** (INF: must outreach the missile) |
| Search radar | Bashir 3-D S-band, one per battalion, 350 km (IR) | **200 km** |
| Extra launchers | 2 Alam al-Hoda TELs per TELAR, electro-optical tracker, no fire-control radar (IR) | 2 per TELAR |
| Taer-2B range | 50 km; 2B claimed 75–105 km (IR) | **50 km** — the 105 km is unproven, 50 km fits the 9M317 lineage |
| Altitude | 25–30 km (IR) | **25 km** |
| Min range / altitude | not published | **3 km / 20 m** (INF, 9M317) |
| Speed | Mach 4 (IR) | **Mach 3–3.5** (INF) |
| Guidance | "active radar homing" (IR) | **command + SARH, Buk-style** (INF: TELAR illuminator architecture) |
| Warhead | 40–50 kg frag (IR/W) | **50 kg** |
| Missile size | not found | **5.5 m, 0.4 m, ~700 kg** (INF, 9M317) |
| Reaction / setup | not found | **~22 s / ~5 min** (INF, Buk) |
| DCS analogue | — | **SA-11 Buk**: same TELAR-plus-loaders-plus-3D-SR concept; analysts tie Raad to Buk-M2E |

### Bavar-373 — unveiled 2016, operational 2019; upgrade and Sayyad-4B shown 2022

| Item | Sources | Best estimate |
|---|---|---|
| TEL | Zoljanah 10x10, 4 vertical cold-launch canisters; up to 6 TELs per battery (IR/W) | **4 canisters, 6 TELs** |
| Meraj-4 search | S-band rotating AESA, 350 km, later 450 km claimed (IR) | **250 km** |
| Hafez acquisition | S-band AESA, 300 km, 100 targets, Zafar 8x8 (IR) | **200 km** |
| Engagement radar | X-band AESA on a mast, 320 km, engages 6 targets with 12 missiles (IR) | **200 km detection, 6 targets** |
| Command post | Zafar 8x8 (IR) | as sourced |
| Sayyad-4 range | 200 km (IR) | **150 km** — the S-300PS-class missile it resembles is well under that |
| Sayyad-4B range | 300 km, some say 400 km (IR) | **200 km** |
| Altitude | Sayyad-4 27 km; 4B 32 km (IR) | **27 / 30 km** |
| Min range / altitude | not published | **5 km / 25 m** (INF, S-300PS) |
| Speed | Mach 5; 6–8 claimed (IR) | **Mach 5** |
| Guidance | inertial + datalink midcourse, SARH/TVM terminal; 4B active seeker (IR/W) | Sayyad-4 **TVM-style**; 4B **active terminal** |
| Warhead | 180 kg (IR/W) | **180 kg** |
| Missile size | 7.5 m, 515 mm, 2,050 kg (IR/W) | as sourced, both missiles |
| Reaction / setup | Meraj-4 emplaced in 30 min (IR) | **~12 s / ~5–30 min** (INF, S-300PS) |
| DCS analogue | — | **SA-10 S-300PS**: 4 vertical canisters, mast-mounted X-band STR, rotating 3-D SR, 6-TEL battery with a command vehicle |

### In the 2026 war

- **Neither system is confirmed as the weapon in a US loss.**
- F-15E, 3 April: US officials (NBC) say probably a Chinese-made MANPADS. The NYT names 3rd
  Khordad as possible. Iranian outlets credit a Bavar-373 with a Sayyad-4B or an upgraded 15th
  Khordad.
- A-10, 3 April, near the Strait of Hormuz during the rescue: Iran claims an unnamed SAM.
- The IDF struck a 3rd Khordad site at Kermanshah on 28 February and claims over 70 air
  defense batteries hit. On 10 March Gen. Caine said Iran's higher-end SAMs were "not
  factors". Iran claims its Bavar-373 units survived.

## 4. Deferred

- **15th Khordad** (Sayyad-3, 120 km, S-300PS-lite). The third system; not in v0.1.
- **Own 3D models.** v0.1 borrows vanilla shapes, so the sites fight right and look like
  their stand-ins.
- **An Iran 2026 faction.** `[CH] Iran 2020` stands in.
- **Iran's own short-range kit** (Majid, Herz-9). MANPADS-class threat is already covered by
  vanilla units.

## Sources

- https://en.wikipedia.org/wiki/Sevom_Khordad
- https://en.wikipedia.org/wiki/Taer_2
- https://en.wikipedia.org/wiki/Raad_(air_defense_system)
- https://en.wikipedia.org/wiki/Khordad_15_(air_defense_system)
- https://en.wikipedia.org/wiki/Bavar-373
- https://en.wikipedia.org/wiki/Sayyad-4_(missile)
- https://en.wikipedia.org/wiki/2026_United_States_F-15E_rescue_operation_in_Iran
- https://www.armyrecognition.com/military-products/army/air-defense-systems/air-defense-vehicles/khordad-3
- https://www.armyrecognition.com/military-products/army/air-defense-systems/air-defense-vehicles/bavar-373-air-defense-system
- https://www.army-technology.com/projects/bavar-373-surface-to-air-missile-system-iran/
- https://www.overtdefense.com/2022/11/14/iran-unveils-new-sayyad-4b-missile-together-with-upgraded-version-of-bavar-373-air-defense-system/
- https://www.missiledefenseadvocacy.org/other-news/irans-bavar-373-missile-system-has-vertical-launchers-commander-confirms/
- https://www.globalsecurity.org/military/world//iran//15th-khordad.htm
- https://www.nbcnews.com/news/military/us-fighter-jet-went-iran-search-rescue-mission-underway-officials-say-rcna266523
- https://theaviationist.com/2026/05/31/chinese-missile-used-to-shoot-down-f-15e/
- https://theaviationist.com/2026/04/03/a-10-thunderbolt-ii-crashed-near-the-strait-of-hormuz/
- https://www.theweek.in/news/defence/2026/04/05/how-did-iran-strike-the-us-f-15-meet-the-irgcs-third-khordad-air-defence-missile-system.html
- https://time.com/article/2026/04/04/f-15-shot-down-iran-search/
- https://defence-blog.com/israel-over-70-iranian-air-defense-systems-knocked-out/
- https://www.washingtoninstitute.org/sites/default/files/pdf/2023-iran-airdefense-systems-table-POL3813-printable.pdf (not read; worth reading for a cleaner W table)
