# My aircraft and saved points (§102)

One window for the seat the player is flying this turn: the aircraft, the points they
saved for it, its loadout and its data cartridge. Built 2026-09-22. Not flown yet; row
**B134** owns the verdict.

Source: juanjux/dcs-escalation, LGPL-3.0, same licence as this tree. Ported with credit
in the file headers and commit messages. Everything below that differs from his tree is
deliberate.

## 1. What it is

- **My aircraft** — a button beside Air Wing on the top bar. Lists every flight a player
  sits in this turn. The right-hand side is three tabs:
  - **Saved points** — his window: rename, copy, paste between aircraft, add a typed or
    pasted position, show on the map, delete.
  - **Loadout** — the Edit Flight dialog's `QFlightPayloadTab`, unchanged.
  - **DTC** — the Edit Flight dialog's `QFlightDtcTab` (§74), unchanged. Airframes with no
    cartridge get a one-line note instead.
- **Saved points** — a spot on the map written into the player's own aircraft, not the
  flight plan. Added from the map's GPS picker (the crosshair button at top left) or from
  the window's Add button.
- They are kept on the **squadron**, not the flight, so cancelling and re-planning a
  flight does not lose them.

## 2. Where a point ends up

| Airframe | In the cockpit | Number |
|---|---|---|
| F/A-18C | §74 cartridge `WYPT`, after the route, `R2` (sequence 2) | route length + 1 … 57 |
| F-16C | §74 cartridge `NAV_PTS`, after the route, `R2`, before the support anchors | route length + 1 … 24 |
| A-10C / A-10C II | `Avionics/<type>/<unit id>/CDU/SETTINGS.lua` inside the miz, flight plan `EXTRA` | his `numbers_for` |
| Everything else | kneeboard only | the next number after the kneeboard's route rows |

Every airframe also gets a kneeboard page, **"<callsign> extra points"**, numbered with the
same numbers the cockpit uses. One function answers both:
`game/missiongenerator/dtc/savedpoints.py:kneeboard_numbers`. A point that did not fit in
the cockpit prints `-` and must be keyed in by hand.

## 3. Differences from his tree

- **His DTC is not ours.** He wrote a separate cartridge writer (`dtc.py`, his #342). The
  injection was rewritten against §74's `hornet.py` and `viper.py`; his file was not taken.
- **The capacity table lists only what this tree loads.** His includes the CJS Super
  Hornets; §74 has no cartridge for them, so here they are kneeboard-only.
- **Viper: 24, not 25.** STPT 25 is the bullseye (§74, B130). Saved points go before the
  tanker and AWACS anchors, so the anchors lose room first. The player chose the points;
  the anchors are automatic.
- **Points ride with the Route section.** If the flight's cartridge is off, or its Route
  section is unticked, the points are kneeboard-only. The window says so, and updates when
  the DTC tab changes.
- **No coordinate-format setting.** His campaign setting was not ported. Everything uses
  degrees and decimal minutes; the picker still shows every format and copies any of them.
- **Show on map pans, it does not zoom.** It uses the existing `reset_on_map_center`
  event rather than porting his `fly_to` event and client slice.
- **Not ported: his #348 Qt half** — coordinates beside a unit in his redesigned intel
  dialog, with a right-click save. Our intel dialog is a different surface.
- **Not ported: his UI restyle.** The window's palette and three styled controls are
  copied into `qt_ui/windows/playable/style.py` instead of taking his `cards.py` and
  `controls.py`.

## 4. The elevation lookup reaches the network

`game/elevation.py` fetches Mapzen terrarium tiles from AWS open data (no key, no
account) to pre-fill a point's elevation. It is the **real world's** height, not DCS's,
and the two can differ by metres on a ridge. Offline, it returns nothing and the player
types the number. Only tile indices are sent. His design, kept as he wrote it.

## 5. Constraints — do not undo

- **Keep points on the squadron.** A flight is rebuilt several times a turn; his #369 is
  the bug that taught this.
- **The kneeboard number must come from `kneeboard_numbers`.** Two numbering rules drifted
  apart once already in his tree (#362).
- **Never offer a kind the airframe cannot be handed.** No airframe here takes a
  markpoint, so none is offered; the kneeboard still prints `MK` if one exists.

## 6. Needs an in-game pass — B134

Headless coverage: `tests/missiongenerator/test_dtc.py` (Hornet, Viper, Route off),
`tests/test_saved_points.py`, `tests/test_a10cdu.py`, `tests/test_playable_*.py`, and the
client's `coordinatepicker` suites. What only a flight answers:

- the Hornet's `R2` points are on sequence 2 in the jet with our explicit `NAV_ROUTE` for
  sequence 1 (his cartridge left `NAV_ROUTE` empty; ours fills route 1 and leaves 2 empty);
- the Viper's points show on the HSD with the anchors after them;
- the A-10's CDU shows the EXTRA plan with ground elevations.

## 7. Deferred

- F-14B(U) and AH-64D: both cartridges have room (Tomcat plans, Apache WPTHZ 1-50). Not
  wired; kneeboard-only for now.
- The coordinate-format setting, and a zoom on Show on map.
