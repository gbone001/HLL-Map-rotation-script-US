
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
