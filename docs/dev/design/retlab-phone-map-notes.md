# Phone map (§115)

The campaign map on a phone, over home Wi-Fi, view-only. Brady's call 2026-10-19
(project thread "Retribution mobile app"): a phone-friendly web page over the existing
map client, not a store app; turn pings to ntfy; home Wi-Fi first, away-from-home by the
user's own Tailscale with no RetLab change.

## Plan

1. **Server and link** (built): File > Phone link, a view-only phone key, a QR code.
2. **Phone layout** (not built): map, an ATO list, a kneeboard and briefing viewer;
   Add to Home Screen.
3. **Turn ping** (not built): an ntfy topic in the preferences gets the SITREP when a
   turn ends.

## How it works

- The map server always listens on `server_bind_address` (`::1`). With **Let my phone
  see the map** ticked at launch, `Server._sockets` also binds `0.0.0.0` on the same
  port, IPv4, because a phone on Wi-Fi is handed an IPv4 address. A failed bind is
  logged and the PC's own map still comes up.
- `PhoneGate` (`game/server/phone.py`) wraps the app. A request from loopback passes
  untouched. Any other request:
  - is refused when phone access is off (turning it off holds at once; the socket stays
    open until restart, refusing everything);
  - may fetch `/phone/*`, the built client (`client/build`), without a key;
  - otherwise must carry the phone key (header or `token=` query), must be GET or HEAD,
    and never reaches `/retribution-ai/*` or `/openapi.json`;
  - is then rewritten to carry the map key, so the routes' own key checks stay the only
    ones they have.
- The phone key lives in the preferences file (`phone_key`), not per run, so a
  home-screen link survives a restart. **New link** replaces it at once.
- The QR link is `http://<lan>:<port>/phone/index.html?server=<lan>:<port>&key=<phone key>`;
  the client reads `server` and `key` exactly as it does from Qt.
- `lan_address` asks the OS which interface it would route through (a UDP connect sends
  nothing).

## Constraints

- **The phone never writes.** Every mutation route is non-GET; the gate refuses non-GET
  before the app sees it. If a GET route ever gains a side effect, it is open to the phone.
- **The PC's map key never leaves the PC.** A request from another device carrying it is
  refused; only the phone key works from outside.
- **A stale client build** (`ApiKeyManager.map_sends_key` false) opens the map routes to
  loopback only; the gate still demands the phone key from outside.
- **One event loop.** The phone shares the PC's uvicorn server and so its event stream
  (`EventStream` is one asyncio queue). Never run the phone on a second server in another
  thread.
- No public tunnel: the server was never built to face the internet.

## Files

- `game/server/phone.py`: `PhoneAccess`, `PhoneGate`, `lan_address`, `phone_url`.
- `game/server/server.py`: the second socket; the app wrapped in `PhoneGate`.
- `qt_ui/liberation_install.py`: `phone_access`, `phone_key` preferences.
- `qt_ui/windows/PhoneLinkDialog.py`: the dialog and QR code (`segno`).
- `qt_ui/main.py`: `PhoneAccess.configure` before the server starts.
- `tests/server/test_phone_gate.py`.

## Later, not planned

Squadron planning in the browser and human red vs blue were discussed 2026-10-19. Both
stand on this gate. Planning needs the Qt planning windows rebuilt as web screens plus
edit locking; red vs blue also needs fog that hides blue from a red viewer and a red key.
