# Afghanistan — Islam Qala (campaign notes)

**Status: BUILT and generating. Never flown.** The faction, the `.miz`, the
campaign yaml and both guard tests are in, and a headless turn 1 plans on both
sides. No in-game pass has been done and `performance:` is a provisional guess.

- Theater: `Afghanistan` (both halves — the campaign spans 62°E to 69°E)
- Setting: October 1998, one point of divergence from real events
- Blue: USA 1990 (USAF/USN/USMC expeditionary), east, based Bagram + Kabul
- Red: Iran 1998 (new faction file), west, based Herat + Shindand, with a
  spearhead already at Chaghcharan
- Scale: **13 control points — 5 blue / 8 red**
- Owner: 414th Joint Fighter Group

---

## Why this exists rather than one of the shipped Afghanistan campaigns

Four campaigns already use this map: Starfire's `clash_of_the_titans`,
`graveyard_of_empires` and `operation_shattered_dagger`, plus the fork's
`coin_enduring_resolve`. Between them they use **13 of the map's 26 airfields**.

Untouched by all four: Zaranj, Nimroz, Qala i Naw, Dwyer, Bost, Maymana,
**Chaghcharan**, **Bamyan**, Urgoon, Gardez, Khost, FOB Salerno, Jalalabad.
The entire central highlands and the whole northwest arc are unused.

Both Starfire campaigns are also single-axis:

| | Clash of the Titans | Graveyard of Empires |
|---|---|---|
| Date · CPs | 2006 · 14 (4 blue / 10 red) | 2002 · 10 (4 blue / 6 red) |
| Blue | Bagram, Kabul, Sharana, Ghazni Heli | Kandahar, Camp Bastion (+2 heliports) |
| Red | Kandahar, Bastion, Tarinkot + 5 FOBs | Herat, Shindand, Farah + 2 FOBs |
| Axis | east ↔ south, ~250 nm | south ↔ west, ~215 nm |
| Mods | CH Russia + China + USA | CH Russia + USA |

This campaign takes **blue's laydown from Clash of the Titans and red's from
Graveyard of Empires**, and puts the central highlands between them.

Clash of the Titans' red laydown is the wrong template for Iran on its own
terms: Kandahar is 244 nm east of Herat and roughly 340 nm from the Iranian
border, with no line of communication back. Graveyard of Empires is the campaign
that already puts a western enemy where a western enemy can be.

## The premise

Real, documented, all 1998:

- **7 Aug** — al-Qaeda bombs the US embassies in Nairobi and Dar es Salaam.
- **8 Aug** — the Taliban take Mazar-i-Sharif and kill eight Iranian diplomats
  and an IRNA journalist at the Iranian consulate.
- **20 Aug** — Operation Infinite Reach: Tomahawks off ships in the Arabian Sea
  strike the al-Qaeda camps near Khost.
- **Sept–Oct** — Iran masses c. 200,000 troops on the Afghan border and
  publicly threatens to cross. It stands down in November.

**The divergence, one sentence: Iran does not stand down.** In October the IRGC
crosses at Islam Qala, takes Herat, Shindand and Farah in eleven days, and pushes
a mechanised column up the Hari Rud into the central highlands. The US, already
committed on the ground in the east after Infinite Reach escalated into a
campaign against the camps, finds an Iranian spearhead at Chaghcharan — 195 nm
from Bagram.

Everything before that sentence happened. Nothing after it needs a second
divergence.

## Scale, and how it was chosen

Upstream's 68 shipped campaigns run a **median of 8 airfields**; Syria's 17 run a
median of 9 with a max of 17. Anatolian Reach's first laydown proposed 41 and was
cut to 14 airfields / 17 CPs on that audit.

**13 control points, 5 blue / 8 red.** Sits between Graveyard of Empires (10) and
Clash of the Titans (14).

## The laydown

### Blue — 5

| CP | id | Stands | Role |
|---|---|---|---|
| Bagram | 16 | 187 | Fighters, heavies, AEW&C, the tanker bridge |
| Kabul | 17 | 192 | Strike, SEAD/DEAD, EW |
| Bamyan | 18 | **5** | Forward FARP, **rotary only** — 70 nm from Kabul, 110 from the spearhead |
| Ghazni Heliport | 21 | 10 | Attack helos, southern shoulder |
| CVN-72 Abraham Lincoln | — | — | Arabian Sea, **support only** |

### Red — 8

| CP | id | Stands | Role |
|---|---|---|---|
| Herat | 1 | 36 | IRIAF fighter base — F-14A, MiG-29A |
| Shindand | 3 | 52 | Strike base — Su-24MK, F-4E, Mirage F1EQ |
| Shindand Heliport | 14 | 42 | Mi-24V, AH-1J |
| Qala i Naw | 6 | 15 | F-5E — **the reach prize**, 55 nm from Herat |
| Chaghcharan | 5 | **3** | **The spearhead** — Mi-17 only, positional not basing |
| Farah | 2 | 3 | Su-25 |
| Tarinkot | 9 | 33 | Su-22M4 — southern shoulder |
| FOB Yakawlang | — | — | Central highlands, on the Bamyan–Chaghcharan road |

Optional additions if 13 proves thin: **FOB Obeh** (Hari Rud, on the
Chaghcharan–Herat road) and **FOB Delaram** (Ring Road, on the Tarinkot–Farah
corridor). Both would give the long corridors an intermediate ground objective.

## Distances — the numbers the design turns on

Measured great-circle from the pydcs airfield positions, 2026-08-28.

| From → to | nm |
|---|---|
| Kabul → Herat | **347** |
| Bagram → Herat | 351 |
| Kabul → Chaghcharan | **195** |
| Chaghcharan → Herat | **152** |
| Kabul → Bamyan | 70 |
| Qala i Naw → Herat | **55** |
| Ghazni Heli → Tarinkot | 139 |
| Carrier → Herat / Kandahar / Kabul | 599 / 422 / 642 |

**347 nm is the campaign.** It is the Anatolian Reach problem — range as the
declared subject, not an obstacle to be engineered away.

## The three axes

Each follows a real road. Per the fork's supply-line standard, the authored
`supply_routes:` waypoints trace the driveable corridor, not a straight line.
Intermediate waypoints may pass through places that are not control points
(Kandahar city on the southern corridor is the main case).

1. **Centre — the Hari Rud.** Kabul → Charikar → Ghorband valley → Shibar Pass →
   **Bamyan** → Yakawlang → Panjab → **Chaghcharan** → Obeh → Karukh → **Herat**.
   Unpaved and seasonal above Bamyan. This is the main axis.
2. **North — the flank.** Chaghcharan → **Qala i Naw** → Karukh → **Herat**.
   Short, and the only route that puts a blue fast-jet base within 55 nm of
   Iran's fighter field.
3. **South — the Ring Road.** Kabul → Maidan Shar → **Ghazni** → Qalat →
   *(Kandahar city)* → **Tarinkot** spur, then Delaram → **Farah** →
   **Shindand**. Paved, long, and the way round if the highlands stall.

### The progression this produces

Hold Bamyan → take Chaghcharan (opens the Hari Rud road) → take Qala i Naw
(**changes the air war**) → Herat → Shindand → Farah.

Chaghcharan's value is **positional, not basing** — 3 stands means blue can move a
two-ship there and nothing more. It removes the threat to Bamyan and opens the
road. Qala i Naw at 15 stands is the field that actually shortens the fast-jet
transit, from 347 nm to 55.

## The load-bearing decisions

### 1. The carrier is support-only

The boat is 599 nm from Herat, 422 from Kandahar, 642 from Kabul. It carries
**tankers (S-3B / KC-135) and an E-2C, and no combat aircraft.**

This is the Akrotiri pattern from Anatolian Reach, applied for the opposite
reason. There, the near base would have hijacked the planner; here the far base
would be a 600 nm cycle that mostly sits unused. Making it infrastructure gives
blue the fuel a 347 nm war needs without adding a base that competes with Kabul.
Lock it with a test in the shape of `test_akrotiri_flies_no_combat_aircraft`.

### 2. Iran has no tanker and no AWACS

`iran_2015` rosters an **IL-78M and an A-50**. Iran operated neither. Its 1998
tanker was the Boeing 707-3J9C, which DCS does not have, and it had no AEW
aircraft at all.

Dropping both is period-correct **and** the campaign's central asymmetry: blue
has the KC-135 bridge and can reach anywhere; Iran cannot leave its own airspace
far, and its entire air picture is ground radar. That lands directly on the
fork's §1 rule — detection is the IADS network alone, and a side with no EWR
loses GCI by design. Killing Iran's EWRs blinds it, because there is no airborne
backup.

Precedent: **42 of 144 shipped factions have no tanker.** This is not a gap.

### 3. The SAM belt is period-gated by hand

`restrict_weapons_by_date` gates weapons but **never preset groups** — the same
trap Anatolian Reach paid for. `iran_2015` rosters SA-17 (2008) and SA-11, and
nothing in the engine stops either in a 1998 campaign.

| Include (1998 Iran) | Exclude |
|---|---|
| Hawk (I-Hawk, the backbone) | **SA-17 / Buk-M2 (2008)** |
| SA-2 / S-75 | **SA-11 / Buk-M1** — Iran had no Buk in 1998 |
| SA-5 / S-200 (delivered c. 1990–92) | **SA-15 Tor** — Iran bought 29 Tor-M1 in 2005–07 |
| SA-6 | |
| HQ-2 (Chinese) | |
| Rapier (pre-revolution British) | |
| KS-19 / SON-9 (AAA) | |
| Silkworm (HY-2, from 1987) | |

The result is an IADS with **no double-digit SAM**, so the F-16CM/HARM work is
genuinely effective and the campaign is not a meat grinder. Locked by
`test_sam_presets_are_period_correct_for_1998`.

**Silkworm is kept, against the first draft of this note.** It is a coastal
battery with no use in a landlocked campaign, but it is period-correct and the
faction file is shared — a future Persian Gulf campaign would want it. Dropping
correct kit because one campaign does not need it is the wrong standard for a
global faction file. The same reasoning kept the Scud-B.

### 5. The SA-15 was the one the summary missed

`iran_2015`'s `air_defense_units` carries **`SA-15 Tor`**, which reads as generic
SHORAD and is easy to skim past — it is not in `preset_groups`, so a review that
only checks the preset list will not see it. Iran bought Tor-M1 in 2005–07. It
is excluded, and the guard test checks `air_defense_units` as well as
`preset_groups` for exactly this reason.

### 4. Both sides fly Tomcats

Iran's `F-14A Tomcat (Block 95-GR Export)` (yaml `introduced: 1976`,
`max_range: 350`) against the US `F-14B` (1987) and `F-14B(U)`. Both Heatblur,
both player-flyable. **Nothing in the fork does this**, and it is the campaign's
headline.

Iran's air force is otherwise the **1991 Iraqi defector fleet** — Su-24MK,
Mirage F1EQ, Su-22M4, MiG-29A, Su-25 — every one real, every one already in
`iran_2015`.

## Air wings

Blue (`usa_1990`, `requirements: {}`):

| Base | Squadrons |
|---|---|
| Bagram | F-15C BARCAP · F-15E Armed Recon · B-52H Strike · E-3A · KC-135 ×2 · C-130J |
| Kabul | F-16CM Blk 50 DEAD/SEAD · A-10A CAS · EA-6B SEAD Escort · F-14B Strike/TARPS · F/A-18C SEAD |
| Bamyan | AH-64A ×4 · UH-60A ×4 |
| Ghazni Heliport | AH-64A ×4 · OH-58D ×4 |
| CVN-72 | S-3B / KC-135 tanker · E-2C — **nothing else** |

`F-117A Nighthawk` is in `usa_1990` and period-correct for 1998, but is AI-only
in DCS. Include as an AI Strike squadron at Bagram if wanted; it is flavour, not
a mechanic.

Red (`iran_1998`, new file derived from `iran_2015`):

| Base | Squadrons |
|---|---|
| Herat | F-14A Blk 95-GR Export BARCAP · MiG-29A Escort |
| Shindand | Su-24MK Strike/BAI · F-4E DEAD · Mirage F1EQ BAI |
| Shindand Heliport | Mi-24V · AH-1J |
| Qala i Naw | F-5E CAS / Armed Recon |
| Chaghcharan | Mi-17 Transport / Air Assault — **rotary only, 3 stands** |
| Farah | Su-25 CAS |
| Tarinkot | Su-22M4 BAI |

## Settings to preseed

Following Anatolian Reach, because a host's saved settings layer sits **under**
campaign preseeds:

```yaml
settings:
  squadron_start_full: true
  restrict_weapons_by_date: true      # 1998 kit: no JDAM (1999), no JSOW (1999)
  restrict_props_by_date: true
  autoplan_tankers_for_strike: true   # default true, preseeded — a 347 nm war
  autoplan_tankers_for_oca: true      # dies silently without them
  autoplan_tankers_for_dead: true
advanced_iads: true                   # §51 jamming, §52 decapitation, the
                                      # bombed-power-station rule
```

No mod-pack settings. `iran_2015` and `usa_1990` both ship `requirements: {}` —
unlike both Starfire Afghanistan campaigns, which need CurrentHill packs.

`version: "10.9"` — equals `CAMPAIGN_FORMAT_VERSION`, which is the ceiling. A
higher value hides the campaign from the New Game list.

## Traps to expect, lifted from campaigns already built

- **The carrier must be a Stennis hull in the editor.** `MizCampaignLoader`
  recognises `Stennis.id` and nothing else. Paint it back to a Lincoln with a
  `carriers:` block. It must also sit under **CJTF Blue**.
- **A FOB's CJTF block decides its side**, unlike SAMs and factories which the
  fork reads from both blocks.
- **Small ramps.** Chaghcharan has 3 stands and Bamyan 5. Author squadrons to fit
  and re-check after the 2026-08-26 DCS parking rework (checklist B100).
- **Ground movers need a 2-waypoint route.** A 1-waypoint `mist.goRoute` never
  drives. The highland corridors are long; movers must still be moving 90 minutes
  in.
- **A plugin toggle is a second gate.** Any feature this campaign preseeds must
  preseed its plugin too.
- **Use `landmap.inclusion_zones` for land tests**, never `inclusion_zone_only`
  and never `terrain.bounds`.

## Measured facts this note rests on

Re-measure rather than recall; all taken 2026-08-28 against this tree.

- The Afghanistan map has **26 airfields and every one is Afghan.** There is no
  Iranian, Pakistani, Turkmen, Uzbek, Tajik or Chinese base. Iran must fly from
  captured Afghan fields — which is why the premise is an invasion already
  underway.
- Map land extent: **28.92–38.77 N, 60.31–75.04 E.** The west edge clips a strip
  of Iranian soil; no airfield sits on it.
- The map reaches the Arabian Sea. The COIN campaign's boat sits at
  **24.517 N, 65.0 E**, which is where the carrier goes.
- `iran_2015` and `usa_1990` both carry `requirements: {}`.
- 42 of 144 shipped factions roster no tanker.

## The faction — BUILT 2026-08-28

`resources/factions/iran_1998.json`, derived from Khopa's `iran_2015`. Guarded by
`tests/fourteenth/test_iran_1998_faction.py` (18 tests). Black, mypy and the full
suite (4,588 tests) green.

**Dropped, with the reason.** More than the first draft of this note anticipated:

| Dropped | Why |
|---|---|
| `IL-78M`, `A-50` | Iran operated neither. This is decision 2 above. |
| `Mi-24V`, `Mi-24P`, `Mi-28N` | Iran never operated Hinds or Havocs. Its attack helicopter is the AH-1J, and that asymmetry against the AH-64A is worth keeping. |
| `Su-25T` | Never fielded operationally by anyone, let alone Iran. |
| `SA-11`, `SA-17`, `SA-15 Tor` | Post-1998 or never Iranian. |
| `MQ-9 Reaper` JTAC | Wrong period **and** wrong nation. `has_jtac` is now `false` — 69 of 144 shipped factions do the same. |
| `Corvette 1124.4 Grisha`, `Corvette 1241.1 Molniya`, `Frigate 1135M Rezky` | Soviet hulls Iran never had. Only the `FAC La Combattante IIa` stays — Iran's Kaman class *is* the Combattante IIa. `cargo_ship` defaults to `Bulker Handy Wind` independently, so a thin naval list costs nothing. |
| the stale `liveries_overrides` entry | It keyed `F-14A Tomcat (Block 135-GR Late)`, which the faction does not field. Dead on arrival. |

**Added or corrected:**

| Change | Why |
|---|---|
| `EWR P-14 Tall King`, `EWR P-37 Bar Lock` alongside `EWR 1L13` | With no AWACS the EWR chain is the whole air picture. The P-14 also pairs with the S-200 site, which uses one as its search radar. |
| `Infantry AK-74` replaces `Insurgent AK-74`; `AAA ZU-23 Closed Emplacement` replaces the Insurgent variant | Iran fielded a regular army. The insurgent variants are cosmetically wrong in the UI. |
| `SAM SA-7B Strela-2M` + `SAM SA-14 Strela-3` MANPADS | Replaces the insurgent-flavoured SA-18. Both are what Iran actually held by 1998. |
| `doctrine: coldwar` | Ground-controlled intercept, no datalink. Matches `iran_1988`. |
| IIAF liveries on the F-14A, IRIAF on the F-5E | `F-14A-95-GR` ships `IIAF - 3-6001 - 160299` and `IIAF - 3-6002 - 160300`; the F-5E ships three `IR IRIAF` schemes. Iranian jets in Iranian paint rather than USN grey. No Iranian F-4E or MiG-29A livery ships — those fall back to the country default. |

**Kept as a known stand-in:** `M109A6 Paladin`. Iran had M109A1s; the A6 is a 1992
US-only variant, and it is the only Western SPG in DCS. `iran_1988` and
`iran_2015` make the same substitution.

**Not asserted:** whether Iran operated the M163 VADS. It is plausible from the
Shah-era US arms package but was not confirmed, so it was left out rather than
guessed. ZSU-23-4, ZU-23 and ZSU-57-2 already cover the AAA layer.

## The miz and the campaign — BUILT 2026-08-28

| File | What it is |
|---|---|
| `tools/build_islam_qala_miz.py` | Builds the `.miz` from an empty Afghanistan mission. Table-driven, deterministic, `--check` dry-runs it. |
| `resources/campaigns/islam_qala.miz` | 11 airfields + carrier + 1 FOB, 34 air-defence markers, 17 IADS C2 nodes, 23 economy statics, 8 armour groups, 2 Scud sites. |
| `resources/campaigns/islam_qala.yaml` | Squadrons, settings, and the twelve supply routes. |
| `tests/fourteenth/test_islam_qala.py` | 19 guards, incl. `test_carrier_flies_no_combat_aircraft`. |
| `tools/supply_route_geo.py` | Gained `ISLAM_QALA_ROUTES`; regenerate with `python tools/supply_route_geo.py islam_qala`. |

**Built from scratch, not forked from a shipped miz.** The laydown adds Bamyan,
Chaghcharan and Qala i Naw — which no campaign on this map uses — and drops
Kandahar and Camp Bastion, which all four use. Deleting more than you keep is not
a fork.

### The connection graph it produces

```
Bagram -- Kabul -- Bamyan ==== FOB Yakawlang -- Chaghcharan -- Qala i Naw -- Herat
             |                                       |                        |
       Ghazni Heliport ==== Tarinkot -- Farah -- Shindand ---------------------+
```

`====` are the two blue/red fronts at turn 1. Everything else is one side's rear.
Shindand Heliport is co-located with Shindand and connects to nothing, which is
normal — Clash of the Titans ships four such control points.

### Verified headless, turn 1

Blue plans **8 packages / 16 flights** (DEAD, SEAD, SEAD Escort, SEAD Sweep,
Strike, Armed Recon, CAS, TARCAP, Escort, AEW&C, Air Assault). Red plans
**5–7 packages / 7–11 flights**. Blue fields 125 airframes against red's 96.

**The period gate holds in what actually spawns, not just in the faction file.**
Generated red air defence is S-200, S-75, Kub, I-Hawk, Rapier, KS-19/SON-9,
ZSU-23-4, ZSU-57-2, ZU-23, with P-14 and 1L13 EWRs. Blue gets Patriot, Hawk,
Avenger, M48 Chaparral and the FPS-117. **Post-1998 systems generated: zero.**

### Three things the build found

- **`usa_1990` has no gun AAA.** Its air defence is the FPS-117, the Avenger and
  the M48 Chaparral. An AAA marker on a blue field raises `USA 1990 has no access
  to SAM AAA` and produces nothing. Blue bases use `shorad`, which is also right
  historically — US base defence in 1998 was Avenger and Stinger, not guns.
  Locked by `test_no_blue_base_carries_an_aaa_marker`.
- **Shindand and Shindand Heliport are 1 nm apart**, and markers bind to the
  nearest control point. Shindand's SAMs, EWR, command centre and Scud site all
  bound to the heliport. `BASE_BIAS` pushes Shindand's markers south-west; the
  Scud needed its own offset flipped as well. Harmless in a fight, but it split
  one base's air defence across two control points that can change hands
  separately.
- **`iran_1988` has a pre-existing defect**, unrelated to this campaign: it lists
  `"Rapier"` — a preset-group name — in `air_defense_units`, where unit names
  belong, so it logs `skipping unknown air-defense unit 'Rapier'` on every load.
  `iran_1998` does not have this.

## Open / deferred

- **Never flown.** Everything above is headless. No in-game pass row exists yet.
- **`performance: 2` is a guess.** Rate it after a generated turn is actually
  loaded in DCS, not before. Clash of the Titans rates 1 and Anatolian Reach 3.
- **No `ground_forces` block**, so the campaign uses engine defaults and logs
  `does not define any ground_forces` at generation. Only 11 of 75 shipped
  campaigns define one, so this is a normal default rather than a gap — but it is
  the obvious lever if the front line turns out too thin or too dense.
- **The A-6E Tanker is a year late.** The real A-6E left fleet service in
  February 1997; the 1998 carrier tanker was the S-3B. The tree dates the A-6E
  1963 with no retirement model, `usa_1990` rosters it, and `coin_enduring_resolve`
  already flies it off the boat on this same map. `S-3B Tanker` exists and is
  carrier-capable but is not in `usa_1990`. Taking it would mean either editing a
  faction 20 campaigns share, or authoring a `usa_1998` — neither justified for a
  one-year gap in an alternate history.
- **Kandahar, Camp Bastion, Dwyer, Bost, Zaranj, Nimroz, Maymana, Jalalabad,
  Khost, Salerno, Gardez and Urgoon are unused.** Kandahar and Bastion are
  deliberate and test-locked; the rest are simply out of scope and are the first
  place to look if the campaign wants more depth.

## Next

1. **Fly a generated turn.** Everything above is headless; nothing here has been
   seen in DCS. Rate `performance:` from that turn and write the in-game-pass rows.
2. **Watch the two fronts.** Bamyan↔FOB Yakawlang and Ghazni Heliport↔Tarinkot
   are the only blue/red adjacencies. If ground combat does not start at both,
   the supply routes bound wrong.
3. **Watch the small ramps.** Chaghcharan (3 stands), Bamyan (5) and Farah (3)
   are the first things a DCS parking change would break — checklist B100.
