# Splash Damage — the RetLab build

Why `resources/plugins/splashdamage3/Splash_Damage_3.4.2_RetLab.lua` is pinned. Moved out of
`CLAUDE.md`'s PINNED block on 2026-10-08, which now carries only the rule; the text below is as
it stood there. The MIST shim it mentions was removed 2026-09-12; `getAGL` is still defined
nowhere, in upstream's MIST either.


**`resources/plugins/splashdamage3/Splash_Damage_3.4.2_RetLab.lua`** — RetLab's
buddy-tuned Splash Damage build (`overall_scaling=0.6`, `rocket_multiplier=0.8`,
`static_damage_boost=1`, shaped-charge rocket flags, `game_messages=true`). Do NOT overwrite
it from upstream. Settings are LOCKED by design: `plugin.json` has no `specificOptions` and
`sd3-config.lua` was removed. Don't reintroduce the config layer. (The *values* are an
upstream candidate — inventory item 21. **That carve is OVER: PR #880 was CLOSED 2026-08-06
on the DM's call — "it's a preference we use, not everyone else."** The tuning is a RetLab
preference, not a bug fix owed upstream, so it lives here permanently. This is a deliberate,
named exception to the everything-upstreamable policy; do not re-carve it without a fresh
call. The two genuine *bugs* found alongside it — see below — are a different matter.)
**Audited against upstream's `Splash_Damage_3.4.2_Standard_Retribution.lua` + the wiki's
Plugin-Options page 2026-08-06** — all 33 exposed options agree with our locked values (the
percent options map through upstream `sd3-config`'s `/100`: `overall_scaling` 60→0.6, rocket
80→0.8, dynamic blast 100→1), and the value drift is the documented tuning. Two
upstream-authored blocks are absent from our copy, both **deliberately dropped** by the
bake-in commit `6f3fc284b` (2026-06-11), which names them: **`shipRadarDamageEnable`**
(HARM → ship radar), dropped because it works by `obj:enableEmission(false)`, then held to be
a crash cause (that rule was lifted 2026-09-28; restoring the block is its own call) — and
**`oca_aircraft_damage_boost`** (3000×,
parked aircraft, "so OCA/Aircraft missions are viable"), **RESTORED 2026-08-06 on the DM's
call**. The two were one contiguous region of the same function, so the OCA half reads as
collateral to the crash-risk removal; restoring it costs OCA/Aircraft strikes nothing and
buys back the kill probability upstream added it for.
⚠️ **Upstream's own copy of the OCA block is broken and ours is not a verbatim copy**: it
calls `getAGL(obj)`, a helper defined **nowhere** — not in the script, `Moose.lua`, or the
MIST shim (grep the tree: zero definitions) — so it raises "attempt to call a nil value" for
every object past `cascade_damage_threshold`, inside the `world.searchObjects` `ifFound`
callback. The fork's port computes AGL inline (`getPoint().y - land.getHeight`) and only for
aircraft. Do NOT "resync" this block from upstream until they fix it.

---
