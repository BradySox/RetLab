# Iran's air defense deployment — research for campaign layouts

**Status (2026-09-27):** research, for laying Iran out in campaigns. Built from it so far: the
third-party missile-mod support in §6 (temporary, DM call). Nothing else is applied yet.

An analysis of three documents the DM supplied, checked against each other, against the DCS maps
and against what RetLab can field. Read it before placing an Iranian IADS in a campaign. The
unit contract and the numbers for the RetLab pack's own units stay in
[`retlab-iran-air-defense-pack-notes.md`](retlab-iran-air-defense-pack-notes.md) (§105).

## 1. The sources

| | Source | Date | Method | Use it for | Not for |
|---|---|---|---|---|---|
| **A** | Air Power Australia, *Strategic SAM Deployment in Iran*, APA-TR-2010-0102 (Sean O'Connor). Text: the DM's `Strategic SAM Deployment in Iran.txt`; maps: ausairpower.net | Jan 2010, updated Apr 2012 | Google Earth imagery, 2009 | Where the legacy fixed sites were; site make-up; the EW chain; empty prepared sites | Anything after 2012 |
| **B** | Washington Institute, *Major Iranian Air Defense Missile Systems, 2023* (table, POL3813) | Nov 2023 | A table of mostly Iranian claims | Which systems exist, their missiles, battery make-up, claimed ranges | Where anything is, or how many (it has neither); ranges at face value |
| **C** | *Estimated Iranian SAM Deployment by System* (an image the DM supplied; publisher unknown) | 2020s — it lists Bavar-373 and Khordad-15 | Unknown; labelled "estimated" | Rough unit counts, and which regions each system defends | Anything precise |

A's maps are the only place its site locations appear; they were read off
`IRANOVERVIEWUPDATE2`, `IRBANDARABBASUPDATED`, `IREWCOVERUPDATE` and `IREMPTYUPDATE2` on
ausairpower.net, so every position below is approximate. A's companion page on S-200 site
layouts (`APA-Rus-SAM-Site-Configs-A.html`) supplies the two-rail detail in §3.

## 2. What the three agree on

- **Iran defends points, not the country.** A calls the coverage "sporadic, yet still
  potentially effective"; C's deployment column names the same handful of places.
- **The defended points:** Tehran, Esfahan and Natanz (the nuclear complex), Bushehr (reactor
  and air base), Bandar Abbas (the navy and the Strait of Hormuz), and air bases.
- **The long-range systems sit at those points,** in 2009 (A: S-200 at Tehran, Esfahan, Bushehr,
  Bandar Abbas) and in the 2020s (C: S-300PMU2 at Tehran, Esfahan, Fordow, Bushehr; Bavar-373
  at Tehran, Esfahan/Natanz, Bandar Abbas).
- **HAWK is the most numerous system** in both A (22 active sites) and C (~19 Mersad units).
- **Fighters carry the area defense.** A's conclusion: Iran leans on its F-14 force because the
  SAM network cannot cover the country.

## 3. What changed between them

Units differ: A counts sites it could see, C counts battalions or batteries, B counts nothing.

| System | A (2009 imagery) | C (2020s estimate) | B (2023) |
|---|---|---|---|
| S-200 (SA-5) | 7 active sites, each **one 5N62 Square Pair and two 5P72 rails** | 3 | Talash-3: an S-200 with a new radar and missiles |
| HQ-2 (SA-2) / Sayyad-1 | 7 active of 21 prepared | ~4 (Tehran, Natanz) | — |
| HAWK / Mersad | 22 active, about half the prepared sites | ~19, country-wide (Dezful, Chabahar, Esfahan named) | Mersad-1/2 (2010), Qader truck version, Mersad-16 (2021) |
| 2K12 Kub (SA-6) | 2 batteries (Tehran, Natanz) | 2, limited use | Its 3M9 also arms Raad-1 and Tabas |
| Tor-M1 (SA-15) | 4 TELARs at Natanz | 2, at nuclear sites | Dezful (2021): a Tor-M1 on a truck |
| S-300PMU2 | — | 4 (Tehran, Esfahan, Fordow, Bushehr) | — |
| Bavar-373 | — | 4-6 (Tehran, Esfahan/Natanz, Bandar Abbas) | Up to six launchers × four canisters; radar 320 km detection, 260 km tracking |
| Raad / 3rd Khordad | — | 2-4, mobile (Bandar Abbas, Tehran, the west) | Raad-1: five TELs and a fire-control unit. 3rd Khordad: TELs and TELARs, Bashir search radar, "reportedly" the RQ-4 shoot-down over the Strait (2019) |
| Talash / Sayyad-2 | — | 3-4 (Tehran, central Iran) | Talash-1 to -4 and the IRGC's Sayyad |
| Khordad-15 | — | 2-3 (strategic sites, air bases) | Najm-802 radar; fielded Nov 2021 |

B also lists short-range systems C does not: Ya Zahra-3 (a Chinese FM-80, itself a Crotale
copy), Herz-e Nohom, Raad-2, Tabas, 9th of Dey, Madjid, Zoobin, Misagh-3 (a QW-1 copy) and
"Item 358" (a loitering anti-aircraft missile).

### Make-up worth carrying into a layout

- **Iranian S-200:** one Square Pair and two rails per site (A and its companion page, which
  names Hamadan). A's reading: Iran bought or kept few rails, and a Square Pair engages one
  target at a time anyway.
- **Bavar-373:** command vehicle, search radar, engagement radar, up to six launchers with four
  rounds each (B). The RetLab layout already matches.
- **Raad-1:** five TELs and a fire-control unit (B).
- **3rd Khordad:** a mix of TELs and TELARs; a heavier four-canister TEL shown in Sep. 2022 (B).
- **9th of Dey:** four launchers of up to eight missiles (B). **Tabas:** eight missiles at four
  targets (B).

### The early-warning chain and the empty sites (A, 2009)

- **24 EW sites,** mostly on the border; a third along the Gulf coast. On A's map the Gulf ones
  sit around Bushehr and Khark, the Kangan–Asaluyeh coast, the Bandar Lengeh–Kish stretch,
  Bandar Abbas (two), Jask and Chabahar.
- **31 prepared, empty sites** (HQ-2 and HAWK patterns): dispersal sites or storage for batteries
  held back. In the Gulf: Lavan and Abu Musa (HAWK pattern), two near Shiraz, and three around
  Bushehr.

### Bandar Abbas in 2009 (A)

One HQ-2 west of the city by the naval base, one HAWK north near the airport, one S-200 to the
north-east. The rings cover Qeshm's east end, Hormuz and Larak.

## 4. What lands on a DCS map

Measured 2026-09-27: airfields from pydcs, and RetLab's landmaps (`resources/theaters/*/landmap.p`)
for everything else. A landmap is modelled land, not proof of detailed terrain (it misses
Jask, which has an airfield), so check a landmap-only place in the Mission Editor before
building on it.

| Map | Iranian places | Evidence |
|---|---|---|
| Persian Gulf | Bandar Abbas and Havadarya, Qeshm, the Tunbs, Abu Musa, Sirri, Kish, Lavan, Bandar Lengeh, Lar, Shiraz, Kerman, Jiroft, Jask | airfields |
| Persian Gulf | Minab, Bam | landmap only |
| Iraq | Kharg (Iran's only airfield on this map) | airfield |
| Iraq | Bushehr, Genaveh, Kangan, Asaluyeh, Khuzestan (Ahvaz, Dezful, Abadan, Omidiyeh), Shiraz, Esfahan, Natanz, Hamadan, Kermanshah, Tehran | landmap only |
| Neither | Chabahar, Konarak | — |

- **The Persian Gulf map holds one of the five defended points:** Bandar Abbas, with the Strait
  islands and the southern air bases.
- **The Iraq map's land data holds the other four** — Tehran, Esfahan/Natanz, Bushehr — plus
  Hamadan's S-200 and Dezful's HAWKs. It is the only DCS map that could carry Iran's heartland
  defense, if the terrain holds up in the editor. No campaign uses it for Iran yet.

## 5. Iran's systems in RetLab

What the three Iranian factions (`iran_1988`, `iran_2015`, `CH_iran_2020`) can field today.

| Iranian system | RetLab preset or unit | Fielded by | Fit |
|---|---|---|---|
| S-200 | `SA-5/S-200` (2 Square Pairs, 6-8 rails); `SA-5/S-200 (Single Radar)` (1 radar, 6 rails) exists, unused | 2015, 2020 | No layout has Iran's one radar and two rails |
| HQ-2 / Sayyad-1 | `HQ-2` (High Digit SAMs launcher), `SA-2/S-75` | all three | Good |
| HAWK / Mersad | `Hawk` (1 SR, 2 TR, PCP, 6 LN; no CWAR) | all three | Good |
| 2K12 Kub | `SA-6` | 2015, 2020 | Good |
| Tor-M1 | `SA-15 Tor` (SHORAD unit) | 2015, 2020 | Good |
| S-300PMU2 | `SA-20B/S-300PMU-2` (High Digit SAMs) exists | none | Gap: C counts four battalions |
| Bavar-373, -II | `Bavar-373`, `Bavar-373-II` (RetLab pack) | 2020 | Good |
| 3rd Khordad | `3rd Khordad` (RetLab pack) | 2015, 2020 | Good |
| Raad-1 / Raad-2 / Tabas | `SA-11`, `SA-17` are the nearest stand-ins (Buk-type) | 2015, 2020 | Iran fields no Buk; keep them only as that stand-in |
| Talash, Sayyad, Khordad-15 | none | — | No DCS model |
| Ya Zahra-3 (FM-80) | `HQ-7` (the same Chinese family) exists, unused | none | Stand-in |
| Rapier | `Rapier` | all three | Iran's Rapiers date from the 1970s; unlikely after 2000 |
| AAA | `KS-19/SON-9`, ZU-23, ZSU-23-4, ZSU-57-2 | all three | Good |
| EW radars | 1L13, 55G6, P-14 (with the SA-5 preset), Matla ul-Fajr (RetLab pack); P-37 in 1988 | — | No EWR preset: an EWR site takes any EWR unit the faction has |
| MANPADS | Igla | all three | Misagh is a QW-1 copy; the Igla stands in |

## 6. Missile sites

The only Iranian ballistic missile DCS ships is the Scud-B. The RetLab pack carries five more
launchers (2026-09-29). They replaced the third-party mods RetLab supported from 2026-09-27
(the PG Iran IRBM Pack, the PG Iran Air Defense Pack's Shahed-238 and the Kheibar TEL), as the
DM called it: support them, then build our own, then drop them.

| Unit id | Range | Iran factions |
|---|---|---|
| `IRAD_Sejjil_TEL` | 1,080 NM | 2015, 2020 |
| `IRAD_Emad_TEL` | 918 NM | 2020 |
| `IRAD_Kheibar_TEL` | 1,080 NM | 2020 |
| `IRAD_Fattah2_TEL` | 756 NM | 2020 |
| `IRAD_Shahed238_TEL` | 540 NM | 2020 |

- **Gate:** the pack's own `iranairdefensepack` toggle.
- **Left out:** the Musudan (the only evidence of Iranian service is one leaked-cable claim; DM
  call); the Fattah-2's glide phase (the pack flies it on DCS's default ballistic arc).
- **How a site behaves:** it spawns at a campaign's Scud marker and, with missile-site fire
  tasks on, fires once per mission at a random enemy base inside its range. At these ranges that
  is every blue base on the map.
- **Preseeded in:** `scenic_merge` (2020, 31 red missile markers), `operation_noisy_cricket` and
  `WRL_Operation_Noisy_Cricket_Redux` (2019, two each). Not in the 2005 Scenic Routes, which
  predate every launcher here, nor in campaigns where Iran is the player.

## 7. Applying the layout, campaign by campaign

The campaigns that field Iran as the enemy are all upstream Persian Gulf campaigns. None has a
long-range SAM marker at Bandar Abbas, where both dated sources put Iran's long-range SAM on this
map.

| Campaign | Date, red faction | What the sources put on this map then | Change to make |
|---|---|---|---|
| `scenic_merge` (the fork's reference flown campaign) | 2020-06-29, `[CH] Iran 2020` | Bavar-373 at Bandar Abbas (C); 3rd Khordad mobile around Bandar Abbas (C); HAWK/Mersad at air bases and islands (A, C); maybe the S-200 (3 left, C); the coastal EW chain (A) | LORAD markers sit at Kerman and near Lavan: add one at Bandar Abbas pinned to Bavar-373. Pin the two Bandar Abbas MERAD markers to 3rd Khordad and the island ones to Hawk. Preseed the CH Iran pack (its description already asks for it) and the RetLab pack |
| `operation_noisy_cricket`, `WRL_Operation_Noisy_Cricket_Redux` | 2019-07-13, `Iran 2015` | Three weeks after the RQ-4 shoot-down over the Strait: 3rd Khordad around Bandar Abbas and the Strait (B); the S-200 at Bandar Abbas (A, C); HAWK on the islands and air bases (A, C). C puts no S-300 on this map | LORAD markers sit at Kerman and Shiraz (Redux adds Jiroft): add one at Bandar Abbas as SA-5. Redux pins SA-10 and SA-10B at two LORAD markers; `Iran 2015` has no S-300, so both pins fail to a random group. Re-pin them, or give the faction `SA-20B` with High Digit SAMs preseeded. Preseed the RetLab pack for the 3rd Khordad |
| `scenic_route`, `scenic_inland` | 2005, `Iran 2015` | A's picture (2009 imagery): S-200, HQ-2 and HAWK at Bandar Abbas; empty prepared HAWK sites on Abu Musa and Lavan; the coastal EW chain. A dates the Natanz Tor and Kub deployments to 2006-2009 | `Iran 2015` fields 2014-and-later kit (3rd Khordad) and non-Iranian Buks. A legacy-only Iran 2005 faction would fit both |
| A new Iraq-map campaign | any | Tehran, Esfahan/Natanz, Bushehr, Hamadan, Dezful — the heartland (§4) | Check the terrain in the editor first; Kharg is the only Iranian airfield |

Not Iran-as-enemy, left alone: `battle_of_abu_dhabi` and `TheValleyOfRotary` (Iran is the
player), `WRL_PG_Wargames` (fictional factions).

## 8. Problems found on the way

- `iran_2015` and `CH_iran_2020` field `SA-11` and `SA-17`; Iran has no Buk.
- No Iranian faction fields an S-300PMU2 (`SA-20B`), though C counts four battalions.
- `iran_1988` lists `"Rapier"`, which matches no unit, so the loader drops it; its requirements
  are empty though it uses High Digit SAMs content (P-37, SA-7, the `HQ-2` preset).
- No Persian Gulf campaign preseeds the CH Iran pack or the RetLab pack.

## 9. Cautions

- C is unsourced and "estimated"; B is mostly Iranian claims; A is 2009 imagery.
- Positions read off A's maps are approximate, to about 10 km.
- No source places Iran's missile bases. The missile markers in these campaigns are the
  campaigns' own choice.
- §79's decoy zones are removed; A's empty prepared sites are not a mechanic to rebuild.
- A new layout with one guidance radar (Iran's two-rail S-200) needs "Single Radar" in its name,
  or `tests/armedforces/test_sam_radar_redundancy.py` fails it.
- A stand-in must be a real unit; nothing here licenses a phantom one.
