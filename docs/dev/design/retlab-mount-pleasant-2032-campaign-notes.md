# Falklands — Mount Pleasant 2032

**Status: BUILT 2026-10-17, headless-verified (a fresh turn 0 generates, both ways). In-game
pass is checklist row B242. New game required.**

Owner: this note. CI lock: `tests/retlab/test_mount_pleasant_2032.py`.

| | |
|---|---|
| Files | `resources/campaigns/mount_pleasant_2032.yaml` + `.miz` |
| Build tool | `python tools/build_mount_pleasant_2032_miz.py` — **never hand-edit the `.miz`** |
| Routes | `python tools/supply_route_geo.py mount_pleasant_2032` |
| Factions | `UK-US Falklands Garrison 2032` (stock + CurrentHill UK), `Argentina 2032` (stock + community A-4E) |
| Checklist row | B242 |

## Why it exists

Every shipped Falklands campaign is an offensive. This one is the only defensive one: the
garrison holds and throws a landing back. It is the 2030s half of the 2026-10-17 South
Atlantic brainstorm; the 1982 half is `retlab-corporate-1982-campaign-notes.md`.

## The DM's calls (2026-10-17)

- **The UK garrison plus a US detachment.** DCS has no Typhoon, so the fighters are the US
  F-16CM and F-15E. The UK side uses the CurrentHill UK pack: Sky Sabre, Stormer, Ajax,
  Warrior, Challenger 3, Type 45, Type 26.
- **Argentina starts ashore** at Goose Green and San Carlos, so there is a ground front on
  turn 1.
- **Islands only, defensive.** The war ends when Goose Green and San Carlos are taken; the
  mainland fields have no road to the islands and cannot be taken.
- **Argentina flies F-16A and A-4E**: the F-16s it bought from Denmark in 2024, and the
  A-4AR. Mi-17s, Hueys, KC-130s and Hercules.
- **HQ-7 and guns** at the lodgement: fictional Chinese supply, short range only.
- **November 2032**: southern spring.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| Blue | **Mount Pleasant** | 55th FS F-16CM 12, 336th FS F-15E 8, No. 18 Sqn CH-47F 2, No. 1312 Flight C-130J-30 2 |
| Blue | **Port Stanley** | 656 Sqn AAC AH-64D 6 |
| Blue | **Ascension Island** (off-map) | 960th AAC E-3A 1, 18th ARS KC-135 2, No. 10 Sqn KC-135 MPRS 1 |
| Red | **Goose Green** | Batallón 601 UH-1H 4 |
| Red | **San Carlos FOB** | VII Brigada Mi-17 4 |
| Red | **Rio Gallegos** | Escuadrón I F-16A 12, Grupo 1 KC-130 2 |
| Red | **Rio Grande** | Escuadrón II F-16A 7 |
| Red | **San Julian** | Grupo 5 A-4E 9 |
| Red | **Ushuaia** | Grupo 1 C-130J-30 2 |

**Roads**: Mount Pleasant – Goose Green and Stanley – San Carlos (the northern track) are
the two fronts. Mount Pleasant – Stanley and Goose Green – San Carlos are each side's own.
On the mainland, Ruta 3 as in Corporate 1982. Nothing joins the mainland to the islands.

**Air defence**: Sky Sabre (the LORAD marker) and two Stormer at Mount Pleasant, a Stormer
at Stanley, the Mount Kent radar head; HQ-7, guns and an FPS-117 at Goose Green, HQ-7 and
guns at San Carlos.

**Sea**: a Type 45 group east of Stanley, a patrol ship off Mare Harbour, the Argentine
escort in Falkland Sound.

**Economy**: factories at Mount Pleasant and Goose Green (the landing's supply dump).

## Constraints

- **Mission range is 440 NM**, as in Corporate 1982: the mainland fields reach Mount
  Pleasant and Stanley.
- **Blue can still strike the mainland.** The range cap is shared by both sides and there
  is no campaign fence. A host who wants the US jets to leave it alone turns on Region
  priorities (§93) and marks the four mainland bases Ignored.
- **Every red point carries the invert flag**, so Invert Sides plays the landing.
- **The blue faction's country is the joint task force**, because it fields UK and US
  squadrons; each squadron flies under its own flag through its preset.
- **Without the CurrentHill UK pack** the blue SAMs, ships and modern vehicles are
  stripped; the faction keeps stock FV510 Warrior and Challenger 2 so a front still forms.

## Stand-ins

F-16A for the F-16AM/BM; A-4E for the A-4AR; Mi-17 for the Mi-171E; Leopard 1A3 for the TAM;
Marder 1A3 for the VCTP; C-130J-30 for the C-130H and the A400M; KC-135 MPRS for the
Voyager; AH-64D for the AH-64E; FPS-117 for the Mount Kent and Argentine radars; Castle
class for the Gowind patrol ships.

## Not verified

Measured headless only. Nothing has been flown. Row B242 covers the first flight. The
2032 order of battle is fiction built on 2026 facts (the Danish F-16 sale, the Sky Sabre
deployment); the basing is a choice, not a forecast.
