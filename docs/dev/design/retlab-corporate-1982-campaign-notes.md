# Falklands — Operation Corporate 1982

**Status: BUILT 2026-10-17, headless-verified (a fresh turn 0 generates, both ways). In-game
pass is checklist row B241. New game required.**

Owner: this note. CI lock: `tests/retlab/test_corporate_1982.py`.

| | |
|---|---|
| Files | `resources/campaigns/corporate_1982.yaml` + `.miz` |
| Build tool | `python tools/build_corporate_1982_miz.py` — **never hand-edit the `.miz`** |
| Routes | `python tools/supply_route_geo.py corporate_1982` |
| Factions | `UK Falklands Task Force 1982` (stock), `Argentina Falklands 1982` (stock + community A-4E) |
| Squadrons | 20 presets named `*1982.yaml` under `resources/squadrons/` |
| Checklist row | B241 |

## Why it exists

The four Falklands campaigns that ship (Battle for No Man's Land, Grabthar's Hammer, Gran
Polvorin, Retake the Falklands) are fictional wars from 1999 to 2006, mostly the US against
Russia or China. None is 1982, and the `Argentina 1982` faction in the repo was unused. It
flies three mods (Mirage III, Super Étendard, MB-339 mod), so this campaign has its own.

## The DM's calls (2026-10-17)

- **One campaign, both sides.** Invert Sides plays it as Argentina, so there is no separate
  Argentine campaign.
- **Start at the San Carlos beachhead**, 21 May 1982, not at sea on 1 May.
- **Argentina: stock plus the A-4E.** The Mirage F1CE stands in for the Mirage IIIEA and the
  Dagger; the MB-339A is the Navy's own MB-339A and also stands in for the Pucará; the
  Tornado IDS, which carries the Kormoran, stands in for the Super Étendard and its Exocet.
- **HMS Hermes is an LHA-1 hull.** Invincible is the R05 DCS ships.
- **The Veinticinco de Mayo is at sea**, off Rio Grande. It was in port after 2 May; it is
  here so an Argentine player has a deck.
- **Historical ratio**: 26 Harriers against 53 Argentine jets.
- **No F-16s for the UK.** Considered so the DM could fly a module he owns, then dropped.
- **Victory**: take Port Stanley; lose San Carlos and you lose.
- **The Harrier flies CAP** on four AIM-9L (RetLab #1266). Without it the UK had no fighters.

## The laydown

| Side | Base | Squadrons |
|---|---|---|
| UK | **HMS Hermes** (LHA-1) | 800 NAS AV-8B 12, No. 1(F) Sqn AV-8B 6 |
| UK | **HMS Invincible** (R05) | 801 NAS AV-8B 8, 846 NAS UH-1H 6 |
| UK | **San Carlos FOB** | 3 CBAS Gazelle AH.1 4, 18 Sqn CH-47F 1 |
| UK | **Ascension Island** (off-map) | 55 Sqn KC-135 MPRS 2, 47 Sqn C-130J-30 2 |
| ARG | **Port Stanley** | 1ra Escuadrilla MB-339A 6, Batallón 601 UH-1H 6 + CH-47D 2 |
| ARG | **Goose Green** | Grupo 3 MB-339A 6 (the Pucarás) |
| ARG | **Rio Gallegos** | Grupo 5 A-4E 10, Grupo 8 F1CE 9, Grupo 1 KC-130 2 |
| ARG | **Rio Grande** | 2da Escuadrilla Tornado IDS 5 (the Super Étendards) |
| ARG | **San Julian** | Grupo 4 A-4E 5, Grupo 6 F1CE 4 (the Daggers) |
| ARG | **Ushuaia** | Grupo 1 C-130J-30 2 |
| ARG | **Veinticinco de Mayo** | 3ra Escuadrilla A-4E 8 (the A-4Qs) |
| ARG | **Mount Kent** (FOB) | none; garrison, guns, depot |

Every other field is neutral: Chile's, and Mount Pleasant, which was built in 1985.

**Roads**: San Carlos – Goose Green (Sussex Mountains, Camilla Creek), San Carlos – Mount
Kent (Teal Inlet, Estancia), Mount Kent – Stanley, Goose Green – Stanley (Fitzroy road). Two
fronts open from San Carlos. On the mainland, Rio Gallegos – San Julian and Rio Grande –
Ushuaia (Ruta 3). The islands and the mainland are not connected.

**Sea**: the carriers sit 65 to 72 NM east of Stanley; a screen with them and a picket in
Falkland Sound ("Bomb Alley"). The Argentine carrier and its escort are 40 NM off Rio Grande.

**Economy**: factories at San Carlos and Stanley, depots at San Carlos, Stanley, Goose Green
and Mount Kent. Stanley keeps the scenery from `RetakeTheFalklands.miz`: Government House is
the command centre, plus the fuel silo and the stores.

## Constraints

- **Mission range is 440 NM** (`max_mission_range_planes`). The mainland fields are 385 to
  432 NM from Stanley, so they reach every island field. Both carriers stay 441 NM or more
  from every mainland field, so the Harriers never go to the mainland and the land-based
  strike groups cannot reach the carriers. The Veinticinco de Mayo is inside the cap of
  the carriers and they of it. A test pins all of this.
- **Every red point carries the invert flag**: the airfields' unlimited-aircraft box, the
  carrier's and the FOB's late activation. A test checks red has it and blue does not.
- **The UK faction's country is the joint task force**, not `UK`. A preferred carrier hull
  is honoured only if the faction's DCS country may sail it, and `UK` has no LHA-1. The
  squadrons fly under the UK flag through their presets.
- **The Argentine faction needs the A-4E mod.** Without it Grupos 4 and 5 and the 3ra
  Escuadrilla are dropped at New Game. The description says so.

## Stand-ins

AV-8B for the Sea Harrier FRS.1 and Harrier GR.3; UH-1H for the Sea King and Wessex; KC-135
MPRS for the Victor K.2; C-130J-30 for the C-130H and Hercules C.1; CH-47F and CH-47D for
the CH-47C; Mirage F1CE for the Mirage IIIEA and Dagger; MB-339A for the Pucará; Tornado IDS with
Kormoran for the Super Étendard with Exocet; FPS-117 for
the TPS-43; Gepard and M163 for the Oerlikon 35 mm and Rheinmetall 20 mm guns; Stinger and
SA-7 are real; M113 for the Scorpion, Scimitar and Panhard AML; Castle class for the
Argentine escorts; LHA-1 for Hermes. There is no Vulcan or Canberra, and no Exocet (pydcs cannot
load the F1's AM39).

## Not verified

Measured headless only. Nothing has been flown. Row B241 covers the first flight: parking at
the small mainland fields, A-4 fuel on a 430 NM leg, Harrier CAP, Chile's border SAMs, and
the inverted game. The 1982 basing and units are from general knowledge, not checked
against sources.
