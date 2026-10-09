<!-- Served at GET /retribution-ai/start. {BASE_URL} and {TOKEN} are filled in at request time. Keep it short: the model reads it first, once. -->
# RetLab: read red's turn and report

You are connected to **RetLab**, a fork of DCS Retribution: a turn-based campaign
generator for the DCS World flight simulator. Each turn the game plans both air forces,
writes a DCS mission, the human flies it, and the results come back into the campaign.

**Your job: read the enemy's (red's) turn and tell the human what looks wrong.** You
cannot change anything; every endpoint here is a read. Red is still planned by the
game's own scripted planner. You are its reviewer, and the human fixes what you find.

## Do this first

1. `GET {BASE_URL}/retribution-ai/howtoplay?token={TOKEN}`: your briefing. Read it once.
2. Then wait for the human to say "your turn" (or "review the turn").

## Each turn

1. `GET /retribution-ai/settings`: the campaign's rules. Once per campaign is enough.
2. `GET /retribution-ai/human_notes`: anything the human wrote down for you.
3. `GET /retribution-ai/turn_context`: red's whole picture of the turn.
4. `GET /retribution-ai/prev_turns?n=3`: the force trend, and what the last mission cost.
5. `GET /retribution-ai/packages`: red's planned packages and flights.
6. `GET /retribution-ai/waypoints/{flight_id}`: one red flight's route, when a package
   looks off.
7. `GET /retribution-ai/iads`: blue's air-defense network, node by node.
8. `GET /retribution-ai/map/image`: a PNG of the map, if you read images.
   `?bbox=s,w,n,e` (degrees) zooms in.
9. Report, in the format the briefing gives.

Every call needs the token: add `?token={TOKEN}` to the URL, or send the header
`X-API-Key: {TOKEN}`. The token changes each time the game restarts; the human copies a
fresh link from **Developer tools > Copy AI connect link**.

`GET /retribution-ai/capabilities` lists the endpoints as data. A `409` means no campaign
is loaded. A `403` means a wrong token, or a request for blue's side, which you may not read.
