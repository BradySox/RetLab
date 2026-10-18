# Custom Loadouts

Retribution picks a weapon loadout for each flight based on its mission type. RetLab takes
those loadouts only from the payload files it ships. This page explains where they come from,
how to change one flight's pylons, and the CLSID pitfall that silently breaks a loadout.

![The Edit flight Payload tab: flight-member and same-loadout/same-livery toggles, the assigned TGP laser code with a preset-code selector, an internal-fuel slider, the named-loadout dropdown, and the per-pylon station list](https://raw.githubusercontent.com/BradySox/RetLab/main/docs/wiki/img/edit-flight-payload.png)

*The flight payload editor. The named-loadout dropdown (here an `IRON` profile) is where a `Retribution <mission type>` loadout gets picked up; tick **Use custom loadout** to set pylons by hand. Laser code and internal fuel are set on the same tab.*

## Changing a loadout

### One flight

In *Edit flight → Payload*, tick **Use custom loadout** and set each pylon by hand. The change
applies to that flight only. The named-loadout dropdown also lists every stock DCS loadout for
the aircraft.

### Loadouts saved in the Mission Editor are not read

**RetLab:** upstream Retribution also reads `Saved Games/DCS/MissionEditor/UnitPayloads`, so a
Mission Editor loadout named `Retribution <mission type>` replaces the shipped one. RetLab
removed this on 2026-10-17. Such a loadout replaced the shipped fit for both sides in every
campaign, and an old weapon on it stayed old in a modern campaign. Your files are not deleted;
the Mission Editor still uses them.

### Shipped payload files

The fork ships curated default payloads as Lua files under
`resources/customized_payloads/`, one per aircraft type (e.g. `F-14B.lua`, `F-16C_50.lua`).
Each file is a table of named profiles keyed by the same `Retribution <mission type>`
convention, with pylons listing weapons by **CLSID**:

```lua
{
  ["displayName"] = "Retribution Strike",
  ["name"]        = "Retribution Strike",
  ["pylons"]      = {
      [3] = { ["CLSID"] = "{GBU-12}", ["num"] = 3 },
      -- ...
  },
}
```

A preset should carry the newest weapon the aircraft can mount. When **Restrict weapons by campaign
date** is on, a weapon newer than the campaign date steps down to an older one in its family
(an AIM-120C becomes an AIM-120B, then an AIM-7). A preset built with old weapons cannot step
up, so a change to a shipped preset uses the newest store.

## The fork's TARPS payload (worked example)

RetLab treats TARPS as a real player task (see [Fog of War and
Reconnaissance](Fog-of-War-and-Reconnaissance)), so the F-14 payload files add a
`Retribution TARPS` recon profile alongside the usual BARCAP/TARCAP/Escort/Strike entries.
It mounts a reconnaissance camera pod on the Tomcat's belly recon station — for example, in
`F-14B.lua`:

```lua
["displayName"] = "Retribution TARPS",
["name"]        = "Retribution TARPS",
["pylons"]      = {
    [4] = { ["CLSID"] = "{F14-TARPS}", ["num"] = 6 },
    -- ...
},
```

The same `Retribution TARPS` profile is present across the F-14A/F-14B variant files so
the photo-recon task is available whichever Tomcat a squadron flies.

## Per-aircraft flight defaults (fuel & aircraft options)

The loadout covers the *pylons* — but the Payload tab's other knobs (**Internal Fuel**,
Aircraft Condition, Wear & Tear, Spawn Type, and any other property-editor value) used to reset
to engine defaults on every new flight. The tab now has a **"Save as default"** button (plus
"Clear default") that remembers the current fuel + properties **per airframe**:

- Every **new** flight of that type opens pre-configured — if your F/A-18Cs always spawn hot at
  80% fuel, set it once and save.
- It applies to fresh **blue** flights only (never enemy AI, never an existing flight you're
  editing), fuel is clamped to the airframe's tank, and it covers blue AI flights of the type
  too — it's "the default for this aircraft."
- Stored on disk at `Saved Games/Retribution/flight_defaults.json`;
  no setting to enable — saving a default is the switch.

A player Heatblur F-4E or A-6E spawns at **Aircraft Condition 90**, Heatblur's standard
service jet, or 75 in a campaign set before 1980. The module's own default of 100 is a
showroom jet. A value you set on the tab, or save as a default, wins.

## CLSID currency — the gotcha that bites

A pylon's `CLSID` is the exact weapon identifier DCS uses internally. These strings change
when ED renames, splits, or removes a store across DCS updates. If **any** CLSID in a
named loadout is stale, **DCS rejects the entire loadout** — the aircraft spawns with the
fallback, not your payload, and there's no obvious error message.

So when you add or edit a loadout:

- Copy CLSIDs from a current DCS install or a freshly-saved Mission Editor loadout, not
  from memory or an old guide.
- After a DCS update, re-verify the payloads for any aircraft whose stores changed.
- If a custom loadout "isn't taking," suspect a stale CLSID before anything else — verify
  the offending profile in the Mission Editor for that aircraft.

Keeping CLSIDs current is the single most important discipline for custom loadouts.

## Date-gated stores and properties

With **Restrict weapons by campaign date** on (a difficulty setting — off by default, on for the
Veteran/Ace presets), the payload editor hides stores **and properties** that postdate the campaign:
modern munitions drop out of the lists, and era-defining options like the **JHMCS** helmet sight are
removed and clamped to the baseline visor for a pre-2003 mission. The generator is authoritative —
even a *defaulted* JHMCS is degraded at generation — so a period campaign stays period-correct
without hand-editing every loadout. See [Custom Factions](Custom-Factions) for the unit/weapon side
of date gating.

## See also

- [Custom Factions](Custom-Factions) — which aircraft a side can field
- [Custom Campaigns](Custom-Campaigns) — where mission types come from
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance) — why TARPS matters
- [Mission planning](Mission-planning) — assigning flights and tasks
