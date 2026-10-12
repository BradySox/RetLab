# Sector war

Status: **step 1 built 2026-10-12** (territory and sectors drawn, row B229), plus
**battles along the border** (row B230). Steps 2 and 3 agreed, not built. Features doc §111.

## Where it came from

A Reddit screenshot of a DCS F10 map (Caucasus, the Sukhumi front) filled each side's whole
territory, orange-brown for red and blue-grey for blue, with the front as the edge between
them. A second set showed hand-drawn "BATTLE MAP" CAS kneeboard cards built per named sector
(WHISKEY-14 attack, XRAY-3 defence). The script behind the map was not identified.

## Brady's choices (2026-10-12, decision cards)

| Question | Answer |
|---|---|
| Drawing only, or a sector war | Full sector war |
| How deep | Sectors decide the fight; ground units still live at their bases |
| Sector shape | Shaped by the ground, not a square grid |
| Sector size | About 10 NM |
| Base capture | A base falls with its sector |
| Which games | New games, setting on by default (step 2) |

## Build steps

| Step | What | Rules change |
|---|---|---|
| 1 | Sectors made and named; territory drawn on the F10 map and the app map, worked out from today's bases and fronts | No |
| 2 | Battles take sectors; a front sits on the sector edge; a base falls with its sector; supply runs through your own sectors | Yes, new-game setting, on by default |
| 3 | A CAS battle-map kneeboard card per front | No |
| 4 | Ground units live in sectors (its own call; not agreed) | Yes |

## Step 1: how it works

`game/theater/sectors.py`.

- **The war region** is the land within 60 NM of the outermost land bases, clipped to the
  landmap's inclusion zones, minus the sea and minus any §98 country holding no base on
  either side. Off-map spawns and ships are not land bases.
- **The grid** is 1 NM cells. A cell costs 1 to cross on drivable ground and 4
  (`MAX_TERRAIN_DIFFICULTY`, §90 rung D) inside an exclusion zone.
- **Sectors** grow from seeds by multi-source shortest path over that grid, so an edge
  settles where the driving cost from two seeds is equal: along ridges and around rough
  ground. Every land base seeds its own sector. The rest are one per 10 NM square, jittered
  by up to 35% of the spacing with a random generator seeded by the square, so the same
  campaign always gets the same sectors. Without the jitter, open ground grew plain squares.
- **Names** are a phonetic row counted from the north and a column counted from the west,
  per 10 NM square: WHISKEY-14. Past 26 rows the words repeat with a lap number
  (CHARLIE2-35). Two seeds in one square get a letter (WHISKEY-14B).
- **Territory** uses the same growth with two labels. Sources are each side's land bases,
  the convoy route on each side of the front's position, and the front's bowed trace (§90
  rung E) offset 1.2 NM to each side. That pins the border to the front line already drawn
  on the F10 map.
- **Shapes** are the cells joined row by row, smoothed by a one-cell close and open,
  clipped to the coast (simplified to 250 m), then simplified as one coverage so the two
  sides share a single edge. Islets under 2 NM² are not drawn.
- **Sector ownership** for display is whoever holds most of a sector's cells.

Built on demand and cached: the sectors while the bases stay put, the territory while no
base changes hands and no front moves. Measured on the cloud box: Abchazian Blitz 0.5 s,
Red Tide 2.0 s, Iraq Desert Storm 1.4 s, Syria full map 0.7 s for sectors plus territory.
The sector edges for the app map take 1.8 s on Red Tide, once.

### F10 map

`DrawingsGenerator.generate_territory`, first, so every other drawing sits on top. Blue
layer. A DCS drawing has no holes, so a territory with a pocket inside it is cut into
pieces through the pocket (`hole_free_pieces`); the edge is drawn as separate closed lines
so the cuts do not show. Every drawing gets its own name, because MIST drops a repeated one.

### App map

`/game` carries `territory` (each side's polygons, pockets as holes) and `sectors` (the
edges between sectors as lines, and each sector's name, owner and seed). Layers: Territory
(on by default) and Sectors (a sub-row, off by default; names show from zoom 9).

## Battles along the border

Brady, 2026-10-12: "frontline units spread across the entire shared border so that it feels
like a push instead of one single 10nm front line battle." Two calls on decision cards:

| Question | Answer |
|---|---|
| How units sit along the border | A battle per sector (not an even thin line) |
| How much border a front fills | Up to Maximum frontline width (not the whole border) |

Before this, a front's units stood on one straight line across the road between its two
bases, clipped wherever the line met undrivable ground. Measured at turn 0: Red Tide
(Fulda) 2.4 NM, Abchazian Blitz (Sukhumi) 4.3 NM, Iraq Desert Storm (H-3) 43 NM.

`game/theater/frontbattles.py`:

- The shared border is where the two sides' territory shapes meet, merged into lines.
- A front takes the line nearest its position and the stretch of it centred there, as long
  as Maximum frontline width (80 km by default) measured along the border. Where the line
  ends first, the stretch slides to keep its length.
- The stretch is sampled every quarter mile. A sample counts if it is on drivable ground
  (inclusion zones minus exclusion and sea) and nearer this front than any other front.
- Each sector the counted samples pass through holds one battle, on its longest unbroken
  run, if that run is at least 1 NM. The battle's centre is the run's middle; blue's forward
  heading is the normal to the border that points into red's ground.
- A battle's groups spread along the run, following the border, up to 5 NM.

`FlotGenerator`:

- Picks as many battles as the side with fewer armor wedges, evenly from end to end.
- Deals wedges out across the battles in turn; a cluster member joins its wedge; artillery
  and the rest are dealt the same way. Each group then steps back to its depth along its
  own battle's heading, and keeps that heading for every order (TIC and vanilla).
- Measured with a test force on Red Tide: the two sides' spread went from 2.7 NM to 20 NM
  across 3 battles. Iraq: 29 NM to 36 NM. Abchazian Blitz: 1 or 2 battles in the 6 NM of
  drivable coast.

The F10 and app-map front line follows the stretch from the first battle to the last.
Built and cached with the territory; a few milliseconds per front after it.

## What step 1 does not do

- No rule changes. The front still slides along the road between two bases, and the
  battle result is still one result per front, whatever happens in each battle.
- No rivers: the landmap has no river data, so a sector edge follows a river only where
  the river is inside an exclusion zone.
- Sectors are not saved. They are rebuilt from the bases and the landmap, so a change to
  this file can rename every sector of a running campaign. Step 2 must store them.

## Step 2 notes (not built)

- The `FrontLine` object stays the interface: 26 files read it (CAS and BAI planning,
  both commanders, kneeboards, the DTC, the briefing, the web map, the outside AI link).
  Only its position should come from the sector border.
- Bases are captured today only by ground units driving into the 3 km zone in a mission
  (`triggergenerator.py`). Brady chose "falls with its sector", so that path is replaced for
  sector-war games, not added to.
- §90's rung A supply tiers become "is there a road to the rear through your own sectors".
  The warning in `supply.py` still applies: the transit network links every airfield pair.

## Not checked

- How large filled drawings look and perform on the DCS F10 map. Red Tide's largest piece
  is about 1,650 corners. Row B229.
