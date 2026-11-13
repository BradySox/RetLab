# Idle plugins are left out of the mission

Status: BUILT 2026-11-12 (user call). Code: `game/missiongenerator/idleplugins.py`, called
from `LuaGenerator.inject_plugins`. Features doc §8, *Mission load*. Row B327.

## Why

Every enabled plugin was loaded into every mission. Airboss loaded with no carrier, CTLD
(about 450 KB with its translations) with no helicopter flights, C-130J Mission Systems with
no C-130J. The hand-trimmed `retribution_nextturn_lite.miz` removed them by hand; this does it
when the mission is written. The freezes of autumn 2026 came from AI flights spawning
mid-mission, not from scripts (`retlab-sim-thread-freeze-notes.md`), so this is a load-time
and housekeeping saving, not a freeze fix.

## The rule

A plugin is left out only when its script would stop on its own check. Leaving it out must
change nothing in the mission.

| Plugin | Left out when | The script's own check |
|---|---|---|
| airboss | no carrier or LHA in `mission_data.carriers` | sets up on the blue carriers and LHAs it finds; a deck out of action is not in that list and cannot recover anyway |
| c130j | no C-130J-30 flight outside `EwExcludedGroups` | claims only C-130J-30 units not on that list |
| opscsar | CSAR off for both sides and no CSAR or Sandy flight | no Ops.CSAR instance, no downed pilots, no King |
| skynetiads, lotatc | the IADS has no node on either side | Skynet has nothing to network; LotATC stops without `redIADS`/`blueIADS` |
| ctld | no Transport or Air Assault flight and no JTAC | CTLD menus go only to `transportPilotNames`; autolase only to `JTACs` |
| 14 settings plugins | their `dcsRetribution` table was not written | each stops on its first lines without it (gpsjamming's handler returns at once) |

Never left out: `base` (MOOSE and the state writer), Splash Damage, smart threat reaction,
QRA intercept, and the opt-in host tools (BigEye, Soundhandler, marker commands, ATIS, the
profiler). A host who ticked an opt-in tool wants it.

## Adding a rule

- Check the script for a global another plugin reads before leaving it out (2026-11-12: only
  LotATC reads another plugin's globals, Skynet's).
- A settings plugin goes in `DATA_GATED_PLUGINS` only if its table is written solely when it
  has work. `test_data_gated_plugin_reads_its_table` checks the script reads the table and
  Python writes it.
