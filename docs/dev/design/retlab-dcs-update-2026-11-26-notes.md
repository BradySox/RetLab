# DCS update 2026-11-26 (2.9.32.30490) - what it does to the fork

Triage of the late-November 2026 DCS patch against this tree (`main` at #1541, pydcs pin
`06d9047`), checked against the install after it updated. The format follows
`retlab-dcs-update-2026-10-28-notes.md`.

## 1. Taken

The pin moved to `BradySox/pydcs@791c3e8` (branch `dcs-2.9.32-surgical`), cut from the old
pin `06d9047`, so the fork gets exactly pin + this delta.

| Change | Source |
|---|---|
| 20 new Cold War Germany airfields, parking changes at 36 existing ones | stand-list dump, `tools/airport_import.py` |
| Kola: Hasvik, Honningsvag, Vardo (2 to 3 helicopter stands each); the other 37 unchanged | same |
| A-6E: Walleye II on pylons 2 and 4, AWW-13 pod on pylon 3, two new properties | unit export |
| F-14B, F-14B(U), F-14A-135-GR and -Early: CATM-7F-3 on stations 4 and 7 | unit export |
| LAU-105 and its AIM-9 loads: lighter weights (A-10C "AIM-9 too heavy") | unit export |

In this tree:

- `resources/dcs/beacons/germanycoldwar.json` and `kola.json` regenerated.
- The A-6E Anti-ship fit is 2 Walleye II, the AWW-13 pod and 2 tanks (Brady's call; it was
  4 Harpoons). `AGM-62.yaml` falls back to Walleye I before 1972. The AWW-13 has no weapon
  yaml: no service-entry year was found, so it is not date-gated.
- `ural_atz5_civil` joins the Soviet-style FARP fuel trucks (Brady's call).
- `tools/airport_slot_census.py` now names `GermanyColdWar` and `MarianaIslandsWWII` by
  their pydcs class names; before, it skipped both maps.

## 2. Findings

- **Germany parking.** The census (`tools/airport_slot_census.py`) shows three fields lost
  one or two stands: Dedelow, Werneuchen, Weser Wumme. A fit check of every Germany campaign
  (each base's squadrons placed by pydcs's own slot test, old data against new) found **no
  campaign worse off**. Baltic Fury's Szczecin-Goleniow fits 3 more Tu-95MS and Wismar one
  more JF-17. Checklist **B349**.
- **Two Germany beacons have a type DCS never defines** (`BEACON_TYPE_AIRPORT_TACAN` at
  Nordholz, `BEACON_TYPE_VORDME` at Strasbourg Entzeim), so DCS loads them with no type.
  `resources/tools/import_beacons.py` now skips such a beacon with a warning instead of
  failing the whole run. Nordholz's TACAN 118X drops out of our data as a result.
- **The beacon importer writes `"direction": null`** on every beacon; the committed files
  leave it out. The two files here were written without it. Every other map's file would
  change on a full re-import for that reason alone.
- **No "ATZM-10" in the export.** The patch notes list it among the trucks that can now
  refuel; DCS has no unit by that name (likely ATMZ-5, already in the pool). TZ-22 and ATZ-60,
  both already in the pool, could not refuel before this patch.
- **Weight drift not taken.** The export shows 52 more weight changes (MiG-29A pylons,
  BDZ-UMK2-B racks, F-4E CBU-38/A). They are not in these patch notes, and an applied OVGME
  pack may have touched the F-4E ones, so they were left for a clean-stock export.

## 3. Export procedure, as run

Runbook in `retlab-dcs-update-2026-08-26-notes.md` section 9. As run on 2026-11-26:

1. Unit export first: hook `pydcs_export.lua` at the end of `me_mission.lua`, launch
   `bin-mt\DCS.exe`, wait for `ships.py`, kill DCS, restore the file. No clicks needed.
2. Stand-list dump second, in a separate launch: the patched `me_map_window.lua` writes
   `C:/dcs-standlist/<TheatreOfWarData.getName()>.lua` plus a `.status.txt` on the first aircraft
   placed per map. Someone has to make a new mission per map and place an aircraft.
3. Restore both Mission Editor files from their backups and `cmp` them.

## 4. No impact

Fixes that help for free: TZ-22 and ATZ-60 refuel; RGM-84 launch and skim (§63, §81); AIM-7E;
ground AI slowing before turns (§131 movers only get safer); Perform Command no longer cancels
Hold (our front line pushes tasks, the SAM transit script uses StopRoute); the Essex heading
(our carrier math uses deck angle 0 for it); C-130J crash fixes; F-4E A/A TACAN bearing; F-14 INS
alignment without Link 4; server memory leak; late-joiner destroyed models.
