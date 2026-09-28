# Package route and Insert NAV point (§106)

**Built 2026-09-27, not flown.** Rows B150 (Insert NAV), B151 (package route).

Two reports from the DM on 2026-09-27, with screenshots:

- "Allow better flight path editing." A Strike flight's Waypoints tab, the NAV point after
  the Join selected, Insert NAV point: *Could not insert a new waypoint given the currently
  selected waypoint.*
- "There should be a package waypoint edit."

## 1. What was wrong

**Insert NAV point knew two legs.** `StandardLayout.add_waypoint` picked a list by the
selected waypoint's type: takeoff or hold went to the head of `nav_to`, split / refuel /
patrol / egress to the head of `nav_from`, and a NAV only if it was already in one of
those two lists. Everything a strike flies between its join and its split lives in other
lists (`ingress_nav`, `egress_nav`, the line-up) or in none, so the whole of the attack
package's own route refused an insert.

It was also wrong where it did answer:

- Takeoff with a hold: the point went to the head of `nav_to`, which is *after* the hold,
  positioned halfway between the field and the hold. The route zigzagged back through it.
  juanjux found the same defect independently (his #248).
- Split with a tanker: the point went to the head of `nav_from`, after the refuel,
  positioned halfway between the split and the refuel. Same zigzag.

**No edit belonged to the package.** Join to IP and target to split are flown by every
formation flight together: the join time is computed back from the IP along
`[join, *ingress_nav, ingress]`. A NAV point on one flight's copy of that leg lengthens
its leg alone, so it reaches the join at a different time and the package does not form
up. The only package-wide edit was dragging the primary flight's join, IP, split or
refuel on the map.

## 2. Insert NAV point — `game/ato/flightplans/navinsert.py`

- Every layout lists the lists a NAV point may go in: `Layout.nav_sequences()`.
  Standard: `nav_to`, `nav_from`, `custom_waypoints`. Formation attack adds
  `ingress_nav` and `egress_nav`; airlift adds `nav_to_drop_off`.
- A candidate is tried in place and kept only if the new point lands **next to the
  selected waypoint in the route**. After it first; then before it.
- So the rule is one check for every layout, not a table of waypoint types, and a list
  whose place in the route is elsewhere can never be picked. Both zigzags above are gone.
- The point goes halfway along the leg it lands in, at the higher of its two neighbours'
  altitudes (`WaypointBuilder.nav_midpoint`, unchanged).
- Refused, with a reason: the attack run (IP to target, target to target), a leg pinned to
  the waypoint beside it (takeoff to hold, line-up to IP, split to refuel), the bullseye and
  divert.
- The reported case: the NAV after the Join was the strike's **line-up** (upstream's
  10 NM run-in point, Raffson 2023). Nothing fits between it and the IP, so the point now
  goes on the leg before it, between the join and the line-up.
- Move Up / Move Down use the same lists (`Layout.move_waypoint`, now one generic
  version); a strike's detour points could not be reordered before.

## 3. The package route — `game/ato/packageroute.py`

**The route** is the way in (JOIN to IP) and the way out (target to SPLIT).

**Who flies it:** every flight whose plan is a formation attack plan, except helicopters
(they join at the IP and fly their own low-level legs) and air assault (its route leaves
both legs out). None, unless the primary flight flies it. Patrols, CAS and custom plans
fly their own way.

**Where the points live:** `PackageWaypoints.ingress_nav` / `egress_nav`, a list of
positions per leg.

- `None` means the planner's: each flight carries the SAM detour
  `formationattack.package_route_points` computes (§69's `route_around_sams`).
- The first edit of a leg seeds it from the **primary flight's** current points, which is
  the route the package actually flies, then applies the edit.
- The planner reads the package's points whenever they are set, so a flight added to the
  package later, or recreated, flies the player's route.
- An old save reads `None` from the dataclass default; no migration.

**How an edit lands** (`_commit`):

- A flight whose point count matches the package's takes the edit itself. It keeps its own
  altitudes and names.
- A flight that does not match (it carries a point of its own on that leg) is rebuilt from
  the package's points at the planner's altitude. **Its own point is dropped.**
- Either way every flight's positions end up the package's.
- A new point is flown at each flight's own height: the higher of its neighbours in that
  flight's route. An escort's is `only_for_player`, as the escort builder makes them.

**Three ways in:**

| Where | What |
|---|---|
| Package window → **Package route** | The route as a table: join, way in, IP, target, way out, split. Insert NAV point (after the selected row; the IP and split take it on the leg before), Delete, Move Up / Down, Reset to planned route. |
| A flight's Waypoints tab | Insert NAV point or Delete on the way in or out asks **Whole package / This flight only / Cancel**, when more than one flight flies the route. |
| The map | Dragging a way-in or way-out point on the **primary** flight moves it for every flight. |

Each edit redraws the package's flights on the map and re-runs ASAP for the package.

## 4. Decisions made without the DM — review these

1. **The window is a button on the package dialog, not a tab.** The package dialog is one
   column with no tabs; a separate window keeps it that way.
2. **The window is not modal**, so the map stays usable to drag points; it re-reads the
   package when it is next active.
3. **Map drags move the package from the primary flight only.** That is upstream's rule for
   the join, IP, split and refuel; an escort's point dragged alone moves the escort alone.
4. **The flight tab asks every time** rather than picking a default. A point on one flight's
   shared leg is sometimes wanted (a player flight's own IP run-in) and usually not.
5. **Positions are edited on the map, not typed.** The window shows coordinates in the
   campaign's format.

## 5. Gotchas

- `FlightWaypoint` is a dataclass, so `==`, `in` and `list.index` compare by value. Two NAV
  points at one place are equal. Every lookup here is by identity (`identity_index`).
- `dcs.mapping.Point` equality is exact `x`/`y`. The package's positions are copied into
  each waypoint (`new_in_same_map`), so the match holds.
- The strike line-up is not on the package route: it is per-flight, strike only, and the
  join time does not count it (upstream's `join_time` uses `[join, *ingress_nav, ingress]`).
  Unchanged.
- A flight's index along a leg maps to the package's by skipping points the package does
  not have (`package_index`), so a flight with its own extra point still inserts in the
  right place.

## 6. Also fixed in the same change

- **Pick a point inside a country's airspace (§102).** §98 draws every country as a filled
  polygon, interactive for its hover tooltip, and the picker leaves any click on an
  interactive shape to that shape. With neutral border defense on it answered only over the
  sea. The border polygons now carry `map-area` (hover only), which the picker treats as
  bare map.
- **ASAP recursion (§104).** The runway queue reads each takeoff from the package TOT, so
  one ASAP estimate depended on the TOT it was taken at and flipped between two times. The
  package dialog saved each redraw back through `timeChanged`, which re-ran ASAP:
  `RecursionError` from `save_tot`. `TotEstimator.earliest_tot` now climbs from the
  no-queue floor to a TOT that covers its own queue, and the dialog's redraw blocks the
  spinner's signals. Recorded in `retlab-startup-times-notes.md`.

## 7. Tests

- `tests/ato/flightplans/test_nav_insert.py` — the insert rule on a strike and a custom
  plan, both zigzags, identity, move.
- `tests/ato/test_package_route.py` — who flies the route, insert / delete / move / drag /
  reset on every flight, seeding from the primary, rebuilding a flight out of step, index
  mapping, the planner reading the package's points, the map-drag hook, an old save.
- `tests/test_package_route_dialog.py` — the window, offscreen.

## 8. Deferred

- Inserting from the map (alt-click on a leg, a right-click waypoint menu): juanjux's #235
  and #238 did this for single flights. Not adopted here.
- Typed coordinates for a point.
- Keeping a flight's own point across a package edit.
- Moving the join, IP or split from the window (they move by dragging on the map today).

Everything here is upstreamable. The insert rule is a clean upstream bug fix (the two
zigzags are upstream's); the package route is a feature and waits for the freeze to lift.
