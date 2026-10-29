# DCS update 2026-10-28 - what it does to the fork

Triage of the late-October 2026 DCS patch against this tree (`main` at #1410, pydcs pin
`beb3763`). Read from the published patch notes and our own files; the install has not
been read yet (section 2 was later settled from the install). The format follows `retlab-dcs-update-2026-08-26-notes.md`.

## 1. Taken

- **MiG-25RBT in both Iraq factions.** The patch adds the MiG-25RBT, IL-76MD and
  MiG-23MLD to DCS's Iraq country list. All three were already in pydcs and in
  `resources/units/aircraft/`. The IL-76MD was already in both Iraq factions. Iraq flew
  MiG-25RBs, so `iraq_1991` and `iraq_2000` gain the MiG-25RBT. Both factions already fly
  the MiG-23MLD: DCS has one Flogger, and `MiG-23MLD.yaml` names it "MiG-23ML Flogger-G" as
  a variant, which is the name the Iraq factions use.
- pydcs's `Iraq` country class lacked the two jets. Nothing in RetLab reads country
  unit lists (factions name the types), so this was cosmetic; section 2's pin bump adds them.

## 2. Done: eight new built-in CurrentHill units

The pin moved to `BradySox/pydcs@06d9047` (branch `dcs-2.9.31-currenthill`), cut from the
old pin `beb3763`, so the fork gets exactly pin + this delta. Each unit has a yaml in
`resources/units/ground_units/`. No faction uses them yet.

| Unit | DCS id | pydcs class |
|---|---|---|
| ZTQ-15 light tank | `CHAP_ZTQ15` | Armor |
| BMD-2 IFV | `CHAP_BMD2` | Armor |
| AMN-2 Atlet MRAP | `CHAP_Atlet` | Armor |
| PGZ-09 SPAAG | `CHAP_PGZ09` | AirDefence |
| ZU-23-2 on Ural 4320 | `CHAP_Ural4320_ZU232` | AirDefence |
| Ural Typhoon-U MRAP | `CHAP_UralTyphoon` | Unarmed |
| ZIL-131 truck | `CHAP_ZIL131` | Unarmed |
| ZIL-131 Kung C2 | `CHAP_ZIL131_Kung` | Unarmed |

- **Source: the install's own Lua, no export run.** Each unit is one file in
  `<DCS>/CoreMods/tech/Currenthill Assets Pack/Database/Vehicles/` on 2.9.31.29434. The
  class fields follow `pydcs_export.lua`'s own rules (`DisplayName`, `DetectionRange`,
  `ThreatRange`, `airWeaponDist` falling back to the threat range, `EPLRS`). The public
  `Quaggles/dcs-lua-datamine` dump of the same build (`72ea893c4`) agrees field for field.
- The same branch adds the MiG-25RBT, MiG-23MLD and IL-76MD to pydcs's `Iraq` country,
  as the patch's country list does. The patch also put the new vehicles in several
  country lists (Russia, China, CJTF and others). Those were not carried: nothing in
  RetLab reads country unit lists.
- Three units have mod-pack twins in `pydcs_extensions/` (`CH_BMD2`, `CH_PGZ09`,
  `CH_ZTQ_15`). Those still need the CurrentHill mod; the `CHAP_` ones do not.
- Check on the next export: diff these eight classes and the Iraq lists against a
  full-install export.

## 3. Fixes that change our runtime for free

Nothing to build. Row `B295` watches the first two.

- **CAP not working when AI starts as Uncontrolled.** Every cold-start AI flight is
  spawned uncontrolled and started by a `StartCommand` push at its startup time
  (`waypointgenerator.py` `set_startup_time`). QRA alert jets (§1) are started the same
  way by `Controller:setCommand`. Cold-start BARCAPs and alert jets should now engage.
- **S_EVENT_KILL missing in some cases, wrong coalition on static kills.** The base
  plugin's `kill_events`, the §91/§96 sortie recorder and the §109 kill causes all read
  S_EVENT_KILL. `sortie_recorder_on_kill` drops a kill whose two sides match, so static
  kills misattributed to the killer's side were never credited. They now should be.
- **AH-64D DTC "Do not upload" fix.** §74's Apache cartridge has no workaround that
  depended on the old behaviour.
- **F-16C JDAM PRE is now pure GPS to the uploaded point.** A PRE drop goes to the
  cartridge coordinate, so target heights matter; they come from the terrain height grid
  (#1096). Under §5's Approximate precision a PRE drop lands on the offset point, as
  intended. §86 GPS jamming is our own Lua and is unaffected.
- **E-2D carrier landing fix.** Our E-2D is a variant of the E-2C entry.
- **Strela-10 no longer re-targets after a cancelled launch.** SA-13 under Skynet.

## 4. Checked, no effect

- **Ship "fire at point" honours altitude.** §34 and §63 call MOOSE `TaskFireAtPoint`
  with no altitude, so no `altitude` param is written.
- **Static B-1B now blocks dynamic spawn.** We put no static aircraft on parking spots;
  §72's deck dressing is guard-tested clear of every spot.
- **AI Runway Line Up option fix.** We never set the option.
- **C-802 RCS lower, Kh-22 profile.** Weapon data; red's §78 coastal batteries get a
  little harder to intercept.
- F-14B(U) historical mode and Link 4 for more carriers (§65 sets Link 4 per hull), F-4E
  new ME failures, piston fuel burn, La-7 radio band, MB-339, AJS37 fuel system, CH-47F
  cargo doors, helicopter damage reactions, tracer colours, track dust, M113 medical
  livery names, Prepare Mission radio presets, the mission-save nil fix.
