# Exact site layouts (§122)

A campaign `.miz` vehicle group whose name starts with **FIXED** (`FIXED SA-6 Bad Hersfeld`,
`fixed-2`) is an air-defense site drawn unit by unit. New Game generates it as drawn: every
unit at its own position and heading. Any other group stays a one-unit marker that gets a
stock layout. Asked for 2026-10-24 so a squadron mate's hand-placed 1980s sites (every
radar, launcher and truck in its real revetment) survive into Fulda Gap 1985.

## Rules (Brady's calls, 2026-10-24)

| Question | Answer |
|---|---|
| What marks a drawn site | The name prefix `FIXED`, followed by a non-letter or the end of the name. Not unit count: an author opts in per group. |
| The site's task | The air-defense preset group (`resources/groups`) whose units match the drawn ones best, trucks left out. A tie goes to the longer-range task. No match: the group is skipped with an error in the log. |
| The owner cannot field the units | Every drawn unit that is not a truck must be in the owner's `accessible_units`. If not, a stock site of the same task generates at the group's first unit, with the same step-down a marker gets. |
| Guns inside a long or medium range site | SHORAD, AAA and MANPAD units become the site's `(PD)` group, Skynet role point defense. In a SHORAD or AAA site they are the site. |
| Extras | The owner's closest ForceGroup for the task adds its stock layout's **optional** slots, only trucks, power, SHORAD, AAA and MANPAD. They are placed by the template around the first unit, so they can land in odd spots; Brady accepted that. |

## How it works

- `MizCampaignLoader.is_exact_site` reads the prefix. The marker readers (long, medium and
  short range SAM, AAA, EWR) skip a FIXED group, so its first unit's type never makes it a
  marker as well. It binds to a control point like a SAM marker (`prefer_blue=True`).
- `ExactSitePreset` (`game/theater/presetlocation.py`) keeps each unit's type, absolute
  position and heading. The preset's own point and heading are the first unit's.
- `game/theater/exactsite.py` builds the `SamGroundObject` or `EwrGroundObject` directly.
  Units carry `fixed_pos` and `fixed_hdg`, so nothing rotates them. Group labels are the
  stock layouts' (`SAM`, `EWR`, `AAA`, `PD`) so template extras join the drawn groups.
- Repair flips a unit alive where it stands, so a repaired site keeps its spots. Selling a
  site in the base menu and buying a new one builds a stock layout.
- The threat ring and Skynet's radar handling come from the real units, as for any site.
- Only vehicle groups. A neutral control point generates nothing for a FIXED group.

## Not done

- Not flown (row B279). Fulda Gap 1985 is the first campaign to use it.
- A FIXED ship group, or FIXED for other objective classes, is not built.
- Units are not checked against the airfield-clearance bands; New Game's
  `Airfield clearance:` log line still reports any that sit on a runway or apron.

## Files

- `game/campaignloader/mizcampaignloader.py`, `game/theater/presetlocation.py`,
  `game/theater/controlpoint.py` (`PresetLocations.exact_air_defenses`),
  `game/theater/exactsite.py`, `game/theater/start_generator.py` (`generate_aa`),
  `game/armedforces/forcegroup.py` (`preset_groups`).
- `tests/theater/test_exact_site_layouts.py`: a real New Game from Abchazian Blitz with a
  drawn SA-11 and a drawn Patriot added.
