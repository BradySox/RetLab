# Squadron presets for stock DCS liveries

Status: built 2026-11-07. Survey tool: `tools/stock_livery_survey.py`.

## What was done

A survey of a full DCS install (2026-11-07) found about 1,850 stock liveries
across 119 aircraft types RetLab knows, and about 1,540 that no squadron preset
named. Upstream `dev` had no preset RetLab lacked.

About 220 new presets and 34 extended ones now cover the useful part of that.
A preset names the livery folder only; no livery file is copied, so a player
without the module sees default paint.

## What counts as useful

Brady's call (2026-11-07), from three options:

- **Real units a faction uses.** A preset reaches a campaign only when a faction
  of the same country flies that aircraft (`SquadronDefLoader`). About 730 stock
  liveries are for a country no faction flies the jet for (a Kuwaiti Hornet, a
  Spanish Phantom), so they were left out.
- **Not junk.** Demo teams, airshow, test and trials aircraft, "fictional" paints,
  aggressor fun schemes, anniversary and heritage specials, single-pilot nose art,
  and plain national paint with no unit named were left out.
- **One preset per unit, its skins as a set.** Tail-number skins of one squadron
  go in its `livery_set` (the 492nd FS got 11). A unit that already had a preset
  had the new skins added to that preset's set.
- **Nicknames only from the livery.** A nickname is written only where the livery
  names one.

## Rules a rerun must keep

- **Tomcat sets are ordered lowest modex first and never repeat a modex** (§62:
  the allocator hands entry 0 to the CAG bird, and the F-14 paints its modex from
  the livery). Existing Tomcat presets were not extended: the new skins repeated a
  modex or mixed a 1976 scheme into a 1999 squadron.
- **A preset with more than one skin carries `livery_set` only**, no `livery:`.
- **`mission_types:` is not read** by `SquadronDef.from_yaml`; tasks come from
  the aircraft. New presets omit it.
- **Never name a Saved Games livery.** Those are personal and render only on the
  machine that has them.

## Left for later

- Faction gaps: Norway, New Zealand and Iraq C-130J-30; South Korea F-4E;
  Bulgaria, Croatia, Hungary, Poland and Serbia MiG-21bis; France F-100D. The
  presets come for free once a faction of that country flies the jet.
- Upstream: nothing in the presets is fork-specific, so they can be offered
  upstream as one data PR.
