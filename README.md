
# Hell Let Loose – Automated Weekly Map Rotation (Railway Headless Service)

This repo contains a lightweight, production-ready automated map rotation system for HLL servers.

## Features
- Uses CRCON **HTTP API first**
- Falls back to **RCON v2** (minimal XOR implementation)
- Fully controlled by `weekly_rotation.json`
- One S-tier night map per day
- A/B tiers use day-only layers
- Zero disruption: current match continues; new rotation starts next map
- Headless: no web server, no FastAPI — PERFECT for Railway

## Environment Variables
```
TIMEZONE=UTC
LOG_LEVEL=INFO        # DEBUG / INFO / WARN / ERROR

# CRCON HTTP
CRCON_HTTP_BASE_URL=https://your-crcon
CRCON_HTTP_BEARER_TOKEN=xxxxx
CRCON_HTTP_VERIFY=false
CRCON_HTTP_TIMEOUT=10

# RCON fallback
RCON_HOST=0.0.0.0
RCON_PORT=12345
RCON_PASSWORD=xxxx

# Rotation JSON
WEEKLY_ROTATION_PATH=./weekly_rotation.json
```

## Railway Deploy
1. Push repo to GitHub  
2. Create a new Railway service → Deploy from GitHub  
3. Set all environment variables  
4. Start command:
```
python rotation_enforcer.py
```

## Logs
Logging controlled via `LOG_LEVEL` env:
- DEBUG     → verbose
- INFO      → recommended
- WARN      → warnings only
- ERROR     → errors only

## Files
- `rotation_enforcer.py` – main scheduler + logic
- `http_client.py` – CRCON HTTP API binding
- `rcon_v2.py` – minimal fallback client
- `config.py` – env + logger
- `weekly_rotation.json`
- `requirements.txt`
- `railway.json`
