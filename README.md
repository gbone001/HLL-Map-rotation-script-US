
# Hell Let Loose – Automated Weekly Map Rotation

This package contains everything needed to run an automated HLL map rotation system using:
- CRCON HTTP API (preferred)
- RCON TCP fallback
- Railway hosting
- Warfare-only weekly rotation with S-tier nights mixed intelligently
- Calendar visuals for admin reference

---

## 📌 Features
- Off-Peak (00:00–14:30): 4× S-tier (day) + 1× A-tier  
- Peak (14:31–23:59): 2× S-tier + 2× A-tier + 1× B-tier  
- **One S-tier night map per day**  
- **Remagen moved to B-tier (day only)**  
- A/B tiers use **day variants only**  
- S-tier uses both **day + night** variants

---

## 📦 Included Files
- `README.md` — this file  
- `weekly_rotation.json` — the complete rotation dataset  
- `rotation_enforcer.py` — Railway-ready automation script  
- Images:
  - `hll_weekly_calendar.png`
  - `hll_weekly_calendar_clean2.png`
  - `hll_weekly_calendar_bigtext.png`

---

## 🖼️ Example Calendar
Below is one of the included image files:

![Weekly Calendar](hll_weekly_calendar_bigtext.png)

---

## 🚀 Deployment (Railway)

### 1. Add the files to your repo
Place everything in the root of your GitHub repo.

### 2. Create a new Railway service
Select "Deploy from GitHub Repo".

### 3. Set environment variables
```
WEEKLY_ROTATION_PATH=./weekly_rotation.json
TIMEZONE=UTC
SERVICE_MODE=loop
ROTATION_ENFORCE_INTERVAL_SECONDS=600

# CRCON HTTP
CRCON_HTTP_BASE_URL=https://YOUR-CRCON-URL
CRCON_HTTP_BEARER_TOKEN=YOUR-TOKEN
CRCON_HTTP_VERIFY=false
CRCON_HTTP_TIMEOUT=15

# RCON FALLBACK
RCON_HOST=xxx.xxx.xxx.xxx
RCON_PORT=xxxxx
RCON_PASSWORD=xxxxxxxx
```

### 4. Railway Start Command
```
python rotation_enforcer.py
```

---

## 🎯 What the Script Does
- Identifies your current weekday & hour  
- Selects the correct map rotation block (off_peak or peak)  
- Executes:
  - `rotlist`
  - `rotdel …`
  - `rotadd …`
- **Tries CRCON HTTP first**
- **Falls back to TCP RCON** if HTTP fails

Continuous enforcement keeps the server honest even if an admin manually changes the rotation.

---

## 🔧 Modifying the Rotation
Edit `weekly_rotation.json` and redeploy.  
The enforcer will adapt automatically based on the updated config.

---

## 🛡 Notes
- Never store RCON passwords in code. Use Railway env vars.  
- Token-based HTTP calls are safer and logged in CRCON.  
- Rotation JSON versioned for clarity.

---

If you want a second ZIP containing the full repo structure scaffold (GitHub-ready), just ask.
