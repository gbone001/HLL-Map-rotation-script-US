
# HLL Map Rotation – New Schedule (Peak 10, Off-peak 15)

This package contains an updated 2-cycle rotation for a 4-week schedule:

- **Rotation A** → Weeks 1–2
- **Rotation B** → Weeks 3–4
- Then repeat.

## Key Rules

- **Off-peak window:** 00:00–14:30
- **Peak window:** 14:31–23:59
- **Off-peak:** 15 maps per day
  - Mix of S-day, S-night (3 days per week), A-tier, B-tier
- **Peak:** 10 maps per day
  - Mix of S-day, S-night (4 days per week), A-tier, B-tier
- All tier lists are rotated **deterministically** so over time each map is used evenly.

## S-tier

S-day:
- stmariedumont_warfare
- stmereeglise_warfare
- carentan_warfare
- utahbeach_warfare
- omahabeach_warfare

S-night:
- stmariedumont_warfare_night
- stmereeglise_warfare_night
- carentan_warfare_night
- utahbeach_warfare_night
- omahabeach_warfare_night

## A-tier

- foy_warfare
- kharkov_warfare
- kursk_warfare
- purpleheartlane_warfare
- hill400_warfare
- driel_warfare
- hurtgenforest_warfare_V2
- elsenbornridge_warfare_day

## B-tier

- remagen_warfare
- mortain_warfare
- tobruk_warfare
- elalamein_warfare
- stalingrad_warfare

## S-night Weekly Pattern

- **Peak S-night:** Monday, Wednesday, Friday, Sunday
- **Off-peak S-night:** Tuesday, Thursday, Saturday

Rotation A and Rotation B each have their own S-night sequence so you get a 2-week S-night cycle that then repeats.

## JSON Structure

- `rotation_A.monday.off_peak` → list of 15 map layer names
- `rotation_A.monday.peak` → list of 10 map layer names
- Same for all days and for `rotation_B`.

You can wire this JSON directly into your rotation enforcer script to rebuild the server rotation at each block change.

## Rotation Selection

`rotation_enforcer.py` now understands the multi-rotation JSON above even without explicit `time_blocks`/`schedule` sections. When those fields are missing it will:

- fall back to the hard-coded windows (off-peak 00:00−14:30, peak 14:31−23:59 documented earlier),
- derive the active rotation (`rotation_A`, `rotation_B`, etc.) using `cycle_length_weeks` and a week-based anchor (defaults to `2025-01-01`),
- follow an optional `rotation_order` list if you need a non-alphabetic sequence,
- allow `cycle_anchor` in the JSON or the `ROTATION_CYCLE_ANCHOR` env var to change the anchor date,
- respect the `ROTATION_NAME` env var when you want to force a specific rotation regardless of the calendar.

If you prefer to keep your own schedule object, just include `time_blocks` + `schedule` in the JSON and the enforcer will use those values unchanged.

## CRCON HTTP Integration

`rotation_enforcer.py` now speaks the REST endpoints listed in `api end points.json` instead of sending raw textual commands. It still loads `config.jsonc` (copy `config.sample.jsonc` and set `CONFIG_PATH`, or override via env), but the client now:

- calls `GET /api/get_map_rotation` to read the current queue and `POST /api/remove_maps_from_rotation`/`POST /api/add_maps_to_rotation` to trim and rebuild the map order,
- keeps a persistent `requests.Session` with the bearer token plus `CRCON_HTTP_TIMEOUT`/`CRCON_HTTP_VERIFY` support, and uses `CRCON_HTTP_API_ROOT` (default `/api`) to compose the endpoint URLs,
- raises `CrconHttpError` when any HTTP interaction fails, logs the failure, and falls back to the legacy RCON v2 `rotdel`/`rotadd` path so you never drop a block change even if the REST API misbehaves.

That gives you a structured POST/GET workflow while retaining the old command fallback for reliability.

## Railway Connectivity

If you need Railway-hosted instances to reach a remote destination server on TCP port `7779`, follow these steps:

- **Determine traffic direction:**
  - If your code (running on Railway) initiates outbound connections to `destination:7779`, Railway typically allows outbound TCP. If the destination has a firewall, it must allow traffic from Railway's egress IP(s).
  - If the destination needs to connect inbound to your Railway service on `7779`, you must configure your Railway service to listen on the appropriate port and expose it — Railway usually routes HTTP(s) traffic and may require additional configuration for arbitrary TCP ports.

- **When the destination requires a fixed egress IP:**
  - Add Railway's Static IP (or equivalent) add-on in the Railway dashboard for your project. That will allocate one or more static egress IPs.
  - Give those static IP(s) to the destination server's firewall and allow inbound TCP on port `7779` from them.

- **Quick verification (manual test):**
  - There's a small helper in this repo to test TCP connectivity to a host/port: `connect_test.py`.
  - Run locally or in the Railway environment (if you have shell access) to confirm reachability:

```powershell
# From PowerShell / pwsh (repo root)
python connect_test.py <destination-host> 7779
```

- **If your Railway service must accept incoming connections on `7779`:**
  - Check Railway docs for exposing non-HTTP TCP services; you may need a specific service type or add-on.
  - Ensure your application binds to the port Railway expects (often read from the `PORT`/`PORT_HTTP` environment variable).

If you'd like, I can:

- add a small health-check endpoint that attempts an outbound connection to the destination and logs the result, or
- help prepare the exact steps to enable Railway's Static IP add-on and update your destination firewall rules (you'll need Railway dashboard access and the destination's firewall control).
