# Iraq — Desert Aladeen: The H-3 Front: campaign notes

**Status: BUILT 2026-10-16, headless-verified (a fresh turn 0 generates). In-game pass is
checklist row B237. New game required.**

Files: `resources/campaigns/desert_aladeen_h3_front.{yaml,miz}`, the factions
`resources/factions/usa_2012.json` and `wadiya_1991.json`, the build tool
`tools/build_desert_aladeen_h3_miz.py`, the route mode `desert_aladeen_h3_front` in
`tools/supply_route_geo.py`, and the CI lock `tests/retlab/test_desert_aladeen_h3_front.py`.

## What it is

Starfire's `operation_desert_aladeen` with the sides reversed, on the DM's call. Starfire's
files are **not edited**: the original is upstream's and a Starfire campaign is the test
standard, so the build tool reads its miz and writes a separate one.

| | Starfire's original | The H-3 Front |
|---|---|---|
| Blue | Baghdad, Al-Salam | H-3 Main, Northwest, Southwest + off-map "Coalition Rear (Jordan)" |
| Red | Kirkuk, Erbil, Qayyarah, Sulaimaniyah | those four + Baghdad, Al-Salam, Al-Sahra, Mosul, Al-Kut, Al-Asad, Al-Taquddum, Kharg + FOB Wadi Hauran |
| Factions | USA 2020 (CurrentHill), Wadiya 2010 | USA 2012, Republic of Wadiya 1991 (both stock DCS) |

## The DM's calls (2026-10-16)

- **A new campaign beside the original**, not a replacement.
- **75-100 mi between the sides at the start.** H-2 is 57 mi from H-3, too close, so H-2
  stays unowned and red's first rung is FOB Wadi Hauran, 85 mi out on the pipeline road.
  The ladder is H-3 Main -> FOB (85 mi) -> Al-Asad (83 mi) -> Al-Taquddum -> Baghdad, as
  yaml supply routes.
- **Kharg goes to red** (a newer map field): 4 MiG-21s and its own SAM, AAA and SHORAD. It
  has no road, so no front reaches it.
- **Blue wins by taking Iraq, not Kharg** (DM call, 2026-10-17). The stock win needs zero red
  control points and Kharg can never be captured, so the yaml carries a §75 `victory:` block:
  win by capturing FOB Wadi Hauran and all 11 Iraqi airfields red holds; lose if H-3 Main
  falls. The stock loss never fires here, because the off-map rear cannot be taken.
- **Heavy north-west target set**: 10 strike targets, 6 Scud sites, 6 SAM sites (2 long,
  4 medium) around Tal Afar, Sinjar, Rabia, Badush, Ba'aj, Hatra, Al-Qaim, Rawah and Haditha.
- **About 90 more red aircraft** at the new fields (94): two squadrons at Baghdad, Al-Salam,
  Al-Sahra and Al-Asad, one at the small fields.
- **Blue: modern US with no mods.** `USA 2012` is `USA 2020` minus every unit from
  `pydcs_extensions` (F-22, Super Hornet, Growler, Prowler, UH-60L, F-16D) and every `[CH]`
  unit, so ticking a mod box cannot bring one back.
- **Red: modern stock SAMs, early-90s jets, no support assets.** `Republic of Wadiya 1991`
  flies MiG-21/23/25/29A/29S/31, Su-27, Su-22/24/25, Mirage F1, Tu-22M3 and helos, has no
  AWACS or tankers, and fields SA-10, SA-11, SA-5, SA-6, SA-8, Tor and Tunguska. Starfire's
  red squadrons were re-typed to it: Su-34 -> Su-22M4, JF-17 -> MiG-29S, the
  `MIG-29-FULCRUM` -> MiG-21bis, H-6J -> Su-24M, Mi-26 -> Mi-8; Erbil's A-50 and IL-78 were
  dropped. Kirkuk's Su-25s went 12 -> 10: Starfire's 48 airframes there over-filled its
  stands. Kirkuk's MiG-29S flies Escort: Starfire's JF-17s flew SEAD Escort, a task the
  MiG-29S cannot fly. The CI lock checks every squadron can fly its primary.
- `USA 2012` lists only what fits 2012: no F-14B, F-14B(U), F-117A, A-6E tanker, E-2D or
  M1A2C SEP v3.

## Constraints

- **No heavy stands west of Baghdad** (see the Desert Storm note). The H-3 complex has 36 +
  25 + 10 fighter-size stands and none that fit an E-3, KC-135, B-1B or C-130J, so those fly
  from the off-map rear. The CI lock checks every based squadron fits its parking.
- **The off-map rear is 10 km inside Iraq**, on the Jordan border. Jordan holds no
  campaign field, so under §98 it is a neutral, and a C-130J that spawned inside it was
  engaged after 180 s. Iraq holds fields of both sides, so it is contested and never
  enforces. The CI lock checks the spawn is in Iraq's border and no other.
- **FOB Wadi Hauran has a 6 km influence zone.** Without it the FOB is the nearest control
  point to the Al-Qaim complex 56 mi north, and capturing the first rung would depopulate
  those sites. The zone limits the FOB to its own furniture; Al-Qaim binds to Al-Asad.
- **Every marker is in the red country block**, which binds the nearest control point of
  either side. The H-3 markers sit on the side of their own strip away from the other two.
- **Placement**: every new marker is on landmap land, 250 m or more from an exclusion zone
  (towns, water), and 3.5 km or more from any airfield (1.2 km on Kharg). A SAM marker is
  also as far from an exclusion zone and the sea as the widest layout of its band reaches
  (422 m for the S-300 Site), since a layout turns about its marker. The CI lock checks all
  three. Kharg's SA-10 and SHORAD and the Al-Qaim SA-10 were moved on 2026-10-17: a Kharg
  launcher had landed in an exclusion zone.
- Starfire's markers around Baghdad and Al-Salam needed no edit: they now bind red fields
  and fill from the red faction.

## Rebuilding

Edit the tables in `tools/build_desert_aladeen_h3_miz.py`, then run it. Regenerate the
routes with `python tools/supply_route_geo.py desert_aladeen_h3_front` and paste them under
Starfire's Baghdad-Al-Salam route in the yaml. Never hand-edit the generated miz.

## Deferred

- The strike targets are `Tech combine` markers, so the game fills them with a random
  building set and names them with its own code words. Real scenery targets would need
  trigger zones on map buildings.
- Starfire's two neutral FOBs (Hamrin, Adhaim) are left as authored, inside red territory
  with no road.
