# RetLab — UI consistency audit (2026-09-22)

Every settings page (the 8 generated pages, Cheat Menu, Lua Plugins, Lua Plugin Options), the
New Game wizard, every other Qt window, the React map client, all 26 plugin manifests, and the
published docs that describe the UI. Method: a dump of all 226 settings' labels and descriptions,
read-only auditors in parallel, a diff against `upstream/dev`, and every "this is stale" claim
checked against the code before anything was changed.

## House style for UI text

| Rule | Guard |
|---|---|
| US English: behavior, defense, armor, theater, modeled, flavor, color, meters (DM call 2026-09-22). Field names keep their spelling | `tests/settings/test_settings_text.py`, `tests/test_plugin_option_descriptions.py` |
| A description renders in full: no hover-only text on a settings option | `test_settings_text.py` |
| A description names another setting by its label, in quotes; never "above" or "below" | same |
| Nautical miles are `NM` | same (labels) |
| Setting text is rich-text safe: no raw newlines, backticks, `&#` entities or unknown tags | same |
| Section names are sentence case | same |
| No setting, published page or plugin text presents a removed feature as live | `tools/audit_stale_docs.py` (CI); the settings test reuses its table |
| Plugin option descriptions render under the label, as on the generated pages | `tests/test_plugin_option_descriptions.py` |
| A mod a shipped campaign preseeds has a New Game toggle | `tests/test_mod_toggles.py` |
| A plugin loop period (`…IntervalS`, `…RepathS`, `…StepS`, `tickSec`) has a positive `minimumValue` | `tests/test_plugin_option_timers.py` |
| Units are a trailing parenthetical: `(NM)`, `(km)`, `(m)`, `(ft)`, `(%)`, `(minutes)` | review |
| A setting whose runtime is a plugin names that plugin by its display name | review |

The settings dialog is a published surface: a feature removal adds one `Removed` row to
`tools/audit_stale_docs.py`, and that row now guards the README, the wiki, the release notes and
every setting's text.

## Decisions (DM, 2026-09-22)

| Question | Call |
|---|---|
| Mods campaigns preseed but the wizard had no toggle for | Toggles restored: UH-60L (13 campaigns), OH-6 Cayuse (Yankee Station, Velvet Thunder), JAS 39, Frenchpack, Spanish Naval Assets |
| CAS / Armed Recon engagement range, 15 / 10 NM since the 2026-06 bump | Upstream's 10 / 5 by default; the RetLab planner suite sets 15 / 10 (divergence-audit amendment) |
| Spelling | US English |
| CSAR knobs filed under "Altitudes" and "Aircraft start types" | New **CSAR flights** section beside **Combat search & rescue**; the CSAR start type stays with the other start types |
| Motorpool cap alone in "Campaign features" | Moved to **Performance → World detail** |
| "Naval strike" holding only the cargo-convoy cap | Section **Sea supply convoys** |
| "LUA Plugins" / "LUA Plugins Options" | **Lua Plugins** / **Lua Plugin Options** |

## What the audit fixed

**Settings text that described removed or changed behavior** (all verified in code first):

| Setting | Was | Now |
|---|---|---|
| Auto-plan cruise missile raids | "respect the campaign ROE zones" (§40, removed) | skips targets hidden from your map and regions set to Ignore — `cruise_raids.py:352-360` |
| Price-weighted AI ground purchases (was "AI procurement reads the strategic picture") | budget shifts by Red Intent / campaign phases (§55/§40, removed) | the only behavior left is the price-weighted buy — `procurement.py:163` |
| SP Pilot Mode | pre-turn brief shows "scheduled squadron arrivals" (§82, removed) | dropped |
| Threat intel brief page | "until a TARPS overflight identifies it" | "until you engage it" — the page itself says "engage them to ID" |
| Auto-planner adds a recon flight | "post-strike BDA pass" (§12, removed) | the flight reveals hidden command posts within 3 NM of the target — `missionresultsprocessor.py:526` |
| GPS jamming | "stand off outside the bubble"; briefed "once recon has found the site" | stand-off still misses by ≥35 % (`gpsjamming-config.lua:41`); briefed once engaged (`gps_jamming.py:163`) |
| COIN IED / HVT / re-infiltration / dispersed cells | "drains your mandate", "will profile", "population ring", "find (TARPS/ISR)" | the will meter went 2026-07-21 (`coin_ied.py:19`, `coin_hvt.py:17`); concealed spawns show as search circles until engaged |
| Altitude scatter | "AI flights are nudged" | every airplane flight is, player flights included — `flight.py:216` |
| Command-center kills, sea supply convoys, single-flight CSAR, squadron randomization, pilot limits, CSAR start type | pointed at other settings by position ("above", "below") | name the setting |
| Spawn player flights immediately | half its explanation was a hover tooltip | merged into the visible description |

Also: typos (`pilotsavailable`, `).Real`, `opened.Player Flights Only`), `(nm)`/`(nmi)` → `(NM)`,
a `<word>` that Qt swallowed, raw `\n` and `&#10;` that rendered as spaces, backticks, the
"Player at IP" stop missing from its own description, "Recon & SCAR planning" → "Recon planning",
the planner-suite bar's intro (it listed 7 of the 9 gates it sets), the fast-forward choices
("Resolving combat" → "Resolve") matched to their description, 31 UK spellings across settings,
Qt, the map client and plugin text.

**New Game wizard:** the Campaign options page never ran the legacy-key migration a save load
runs, so a campaign preseeding a renamed key (`eplrs_enabled`) kept the new default; its subtitle
names Default.zip again (Save Settings writes `settings.json`, which the default loader reads).

**Plugin pages:** option descriptions (`descriptionInUI`) were never read by the loader, so 10
written descriptions rendered nowhere; text and dropdown options showed a stale value after a
campaign switch in the wizard (redscramble's preseeded "Flash" showed empty). Stale manifest text:
Growler named only the EA-18G, COIN cited the political mandate, TIC's jitter label said ±25 %
(the code does ±45 % plus a per-group tempo), intercept pointed at "Campaign Doctrine". The
soundhandler's Tomahawk call referenced a sound it never packed.

**Plugin option behavior (same-day follow-up):** Skynet's "Exclude SA-15" was a no-op (an inner
`local` shadowed the list; upstream carries it too, inventory item 39) and its 12 dependent
options now gray out with their master; MooseAtis lost "Debug Mode" (never read) and "Announce
Field Name" (needs `ATIS:SetReportName`, absent from the bundled MOOSE); nine loop periods got a
positive minimum, so 0 no longer reschedules a loop on every pass.

**Qt windows — text that said something false:** closing Air Wing Configuration discards (the
text said it accepts); the time/date warning said changing it re-initializes the turn (ACCEPT
keeps and re-times the plans); the sell tooltip said "buy"; the results-file picker said "game
file"; the "missing pilots" dialog printed raw objects; the mission start page named a setting
by its old label; the package TOT tooltip; broken `</>`, `</label>` and stray `</p>` tags; the
wizard's "Yom Kippour" and "6 days war"; three hard line breaks forcing a wrap mid-sentence; the
"Change squadron" dialog had no title; the weather dialogs called the 2,000 m and 8,000 m wind
layers "FL080", "FL08" and "FL26" (2,000 m is FL066) and used "º" (an ordinal) as a degree sign.

**Map client:** "fly recon to localize" (recon no longer localizes); two legend rows for symbols
nothing draws since §21 (removed with their colors); "it will intercept" for neutral airspace
(SAMs only since 2026-09-07); "nm" → "NM"; the flight tooltip's TOT carried a "Z" but is
mission-local time.

**Map client behavior (follow-up, same day):**

- The LORAD/MERAD/SHORAD/AAA rows now gray out while "Air defenses" is off; `<Row>` never received `enabledWhen`.
- "Hide all overlays" turns every layer off. It used to run the Clean preset.
- Presets no longer touch display options ("Highlight radar emitter on hover") or the fog overview.
- Every preset keeps "Neutral airspace" and "Downed pilots" on.
- SEAD shows "Other ground objects", where the EWRs, command centers and power plants the IADS lines end at are drawn.
- An enemy downed pilot shows the enemy's rescue window, no CSAR hint, and no right-click dialog. `mission_types` offers nothing for a pilot you do not own.
- The carrier drag tooltip no longer prints "-51.70°S". It shares `controlpoints/destinationFormat.ts` with the ship marker.
- The events feed hides a body with no letter or digit, such as the 40-hyphen rule on upstream's "Game Start" and "End of turn #N".

**SITREP:** evaders still awaiting pickup were labeled "MIA", the word the CSAR settings use for
a pilot who was lost. Now "Awaiting rescue:".

**Published docs:** Fast-Forward-and-Performance (settings that no longer exist, wrong page
names, a host checklist recommending Ground AI sleep ON against the measured 2026-08-24 finding,
two removed features listed as live); Lua-Plugins and Developers-Guide (MIST "retired" since it
came back 2026-09-12, 24 plugins listed of 26, MooseAtis called late-init); The-Retribution-UI
(settings page list, map panel groups); Combat-SAR (where the settings live); README (GPS jamming
"scouted"); location pointers in the features doc and checklist.

**The stale-docs audit itself:** it matched rows against raw wrapped markdown, so any phrase
split by a line wrap passed; one bullet's "removed" excused a whole list; and the MIST row was
inverted — it flagged every live mention of MIST and excused "retired". All three fixed, with
regression tests in `tests/tools/test_audit_stale_docs.py`.

## Open backlog

Found and verified, not changed here: each is behavior rather than wording, or a wider pass.

### Behavior defects

| Where | Defect |
|---|---|
| Kneeboard coordinates (`kneeboard.py`, `kneeboard_recon/coords.py`, `pages.py`) | pydcs `LatLng.format_dms()` prints a west or south component with a minus sign and the complementary minutes: `(36.2, -115.3)` → `-115°42'00"W`, true 115°18'W. Every Nevada and South Atlantic kneeboard coordinate is wrong |
| `game/retlab/c2_decapitation.py:58-80` | The C2 chip and SITREP line count every enemy command post, hidden ones included, so "1/3 operational" leaks how many exist |
| Plugin pages | Not reached by the settings search or "Only changed"; no campaign badge; unticking a plugin does not gray its options |
| `qt_ui/windows/sp/QSpPilotModeDialog.py:179,220` | Offers "join a package" sorties, then says joining "is not wired up yet" |
| COIN HVT and IED | Since the will economy went, a kill or a detonation is an announcement only; the features have no consequence |

### My aircraft window and the per-airframe DTC tab (§102, landed the same day)

Audited after the rebase; 29 findings, handed on rather than fixed here because the feature was
still moving. The ones that say something false: the header's mission-local time is marked "Z";
"no DCS data cartridge, saved points go on the kneeboard" on the A-10, whose points go into the
navigation computer; the Elev tooltip says nothing knows the ground height, which
`game/elevation.py` does; slot counts ignore the route the points are numbered after; the Viper
section text puts saved points on steerpoints 21-24 (they follow the route); "the kneeboard
prints '-'" is false on the F-14B(U). The rest is naming drift ("GPS Points", "Loadout" for the
Payload tab, `.title()` giving "Ingress Sead"), "nm", plurals and hover-only hints.

### Wider passes, not started

- **Coalition words.** Player/Enemy, OWNFOR/OPFOR, Blue/Red and Friendly/Allied/Hostile are all
  live; Qt alone has six schemes, the map panel three for our own side.
- **Button and window-title casing.** Qt titles are mostly Title Case, buttons split evenly, 10
  are ALL CAPS; the Cheat Menu labels carry colons and "Cheat"/"Cheats" at random.
- **Money format.** "{n}M", "${n}M", "$ {n} M" and "${n}" all appear (the New Game budget
  reads "$2000" for 2000M).
- **Hover-only wording.** Tooltips carrying information shown nowhere else — the DTC tab's
  per-airframe notes, mod requirements and download links on the Mods page, QRA and purchase
  rules in the squadron and air wing dialogs, frequency/TACAN/ICLS conflict explanations, the
  base menu's deployable-limit formula.
- **Missing descriptions.** 45 settings have none: 17 of 19 on the Performance page, 12 on
  Difficulty & Realism, 7 in HQ automation, the engagement ranges, both Supercarrier options.

### Against upstream

Diffed against `upstream/dev` 49e8067f6 for the settings system, the dialog, the wizard and the
shared plugins. Nothing destructive: every upstream field is shown, or removed or migrated with a
written record, and an upstream settings file loads into the fork with no stray keys. The three
real gaps — the missing mod toggles, the unratified engagement defaults and the wizard's skipped
migration — are fixed above.
