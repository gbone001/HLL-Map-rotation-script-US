
import json
import time
import logging
from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from config import get_env
from http_client import (
    CrconHttpError,
    add_maps_to_rotation,
    get_map_rotation,
    remove_maps_from_rotation,
)
from rcon_v2 import RconV2

log = logging.getLogger(__name__)

DEFAULT_TIME_BLOCKS = {
    "off_peak": {"from": "00:00", "to": "14:30"},
    "peak": {"from": "14:31", "to": "23:59"},
}
DEFAULT_CYCLE_ANCHOR = datetime(2025, 1, 1).date()

def read_json(path: str):
    with open(path, "r") as f:
        return json.load(f)

def parse(hhmm: str):
    h, m = hhmm.split(":")
    return dtime(int(h), int(m))

def now_tz():
    tz = ZoneInfo(get_env("TIMEZONE", "UTC"))
    return datetime.now(tz)

def _parse_anchor(raw):
    if not raw:
        return DEFAULT_CYCLE_ANCHOR
    try:
        return datetime.fromisoformat(raw).date()
    except (TypeError, ValueError):
        log.warning("Invalid rotation anchor %r; using %s", raw, DEFAULT_CYCLE_ANCHOR.isoformat())
        return DEFAULT_CYCLE_ANCHOR

def _normalize_rotation_key(name, rotation_names):
    if not isinstance(name, str):
        return None
    if name in rotation_names:
        return name
    candidate = name if name.startswith("rotation_") else f"rotation_{name}"
    if candidate in rotation_names:
        return candidate
    return None

def _rotation_sequence(cfg, rotation_names):
    order = cfg.get("rotation_order")
    if isinstance(order, list):
        normalized = []
        for entry in order:
            key = _normalize_rotation_key(entry, rotation_names)
            if key:
                normalized.append(key)
            else:
                log.warning("rotation_order entry %r not recognized", entry)
        if normalized:
            return normalized
    return rotation_names

def _select_rotation_name(cfg, rotation_names):
    override = get_env("ROTATION_NAME")
    if override:
        key = _normalize_rotation_key(override, rotation_names)
        if key:
            log.debug("ROTATION_NAME override selects %s", key)
            return key
        log.warning("ROTATION_NAME %r is not valid, ignoring override", override)

    sequence = _rotation_sequence(cfg, rotation_names)
    if not sequence:
        sequence = rotation_names

    rotation_length_raw = cfg.get("cycle_length_weeks", 1)
    try:
        rotation_length = max(1, int(rotation_length_raw))
    except (TypeError, ValueError):
        rotation_length = 1

    anchor_raw = cfg.get("cycle_anchor") or get_env("ROTATION_CYCLE_ANCHOR")
    anchor_date = _parse_anchor(anchor_raw)
    now = now_tz()
    weeks_since_anchor = (now.date() - anchor_date).days // 7
    index = (weeks_since_anchor // rotation_length) % len(sequence)
    return sequence[index]

def _build_schedule_from_rotation(rotation):
    schedule = {}
    for day, blocks in rotation.items():
        if not isinstance(blocks, dict):
            continue
        schedule[day.lower()] = {
            "off_peak": blocks.get("off_peak") or [],
            "peak": blocks.get("peak") or [],
        }
    return schedule

def ensure_time_blocks(cfg):
    blocks = cfg.get("time_blocks")
    if isinstance(blocks, dict) and "off_peak" in blocks and "peak" in blocks:
        return
    cfg["time_blocks"] = {name: times.copy() for name, times in DEFAULT_TIME_BLOCKS.items()}
    cfg["_time_blocks_from_default"] = True
    log.info("Using default time blocks %s", DEFAULT_TIME_BLOCKS)

def ensure_schedule(cfg):
    rotation_sections = [
        key for key in cfg.keys()
        if key.startswith("rotation_") and isinstance(cfg[key], dict)
    ]

    if "schedule" in cfg and not cfg.get("_schedule_from_rotations"):
        return
    if not rotation_sections:
        if "schedule" not in cfg:
            raise KeyError("schedule")
        return

    rotation_name = _select_rotation_name(cfg, rotation_sections)
    if cfg.get("_rotation_name") == rotation_name and cfg.get("schedule"):
        return

    rotation = cfg.get(rotation_name)
    if not rotation:
        raise KeyError(f"rotation section {rotation_name} missing")

    cfg["schedule"] = _build_schedule_from_rotation(rotation)
    cfg["_rotation_name"] = rotation_name
    cfg["_schedule_from_rotations"] = True
    log.info("Using rotation section %s for current schedule", rotation_name)

def get_current_block(cfg):
    blocks = cfg["time_blocks"]
    off = blocks["off_peak"]

    n = now_tz().time()
    if parse(off["from"]) <= n <= parse(off["to"]):
        return "off_peak"
    return "peak"

def get_next_transition(cfg):
    tz = ZoneInfo(get_env("TIMEZONE", "UTC"))
    now = now_tz()
    off = cfg["time_blocks"]["off_peak"]
    pk = cfg["time_blocks"]["peak"]

    today_off = now.replace(hour=int(off["from"][:2]), minute=int(off["from"][3:]), second=0, microsecond=0)
    today_pk  = now.replace(hour=int(pk["from"][:2]),  minute=int(pk["from"][3:]),  second=0, microsecond=0)

    candidates = [today_off, today_pk]

    # If in past, schedule next day
    future = []
    for c in candidates:
        if c > now:
            future.append(c)
        else:
            future.append(c + timedelta(days=1))

    return min(future)

def _execute_rcon(command: str) -> str:
    return RconV2().send_cmd(command)

def _rotation_from_rcon() -> list[str]:
    raw = _execute_rcon("rotlist")
    return [line.strip() for line in raw.splitlines() if line.strip()]

def get_rotation():
    try:
        return get_map_rotation()
    except CrconHttpError as exc:
        log.warning("HTTP rotation fetch failed → fallback to RCON v2: %s", exc, exc_info=True)
        return _rotation_from_rcon()


def _remove_queued_maps(maps: list[str]):
    if not maps:
        return
    try:
        remove_maps_from_rotation(maps)
    except CrconHttpError as exc:
        log.warning("HTTP rotation removal failed → fallback to RCON v2: %s", exc, exc_info=True)
        for m in maps:
            _execute_rcon(f"rotdel {m}")


def _add_target_maps(maps: list[str]):
    if not maps:
        return
    try:
        add_maps_to_rotation(maps)
    except CrconHttpError as exc:
        log.warning("HTTP rotation append failed → fallback to RCON v2: %s", exc, exc_info=True)
        for m in maps:
            _execute_rcon(f"rotadd {m}")


def _apply_map_pool(current: list[str], target: list[str]):
    queued = current[1:] if current and len(current) > 1 else []
    if queued:
        _remove_queued_maps(queued)
    else:
        log.debug("No queued maps remain to remove before applying new map pool")

    if not target:
        log.info("Target map pool is empty for this block; rotation queue cleared")
        return

    _add_target_maps(target)

def enforce_block(cfg):
    ensure_schedule(cfg)
    weekday = now_tz().strftime("%A").lower()
    block = get_current_block(cfg)
    target = cfg["schedule"][weekday][block]

    log.info(f"Enforcing {weekday}.{block} rotation: {target}")

    current = get_rotation()
    log.debug(f"Current rotation: {current}")

    if not current:
        log.warning("No current rotation found")
    else:
        log.debug("Current map still playing: %s", current[0])

    _apply_map_pool(current, target)

    log.info(f"Rotation updated for block {block}. New maps queued after current match.")

def main():
    path = get_env("WEEKLY_ROTATION_PATH", "./weekly_rotation.json")
    cfg = read_json(path)
    ensure_time_blocks(cfg)
    ensure_schedule(cfg)

    while True:
        enforce_block(cfg)
        nxt = get_next_transition(cfg)
        now = now_tz()
        sleep_s = (nxt - now).total_seconds()
        log.info(f"Next block transition at {nxt.isoformat()}, sleeping for {sleep_s:.0f}s")
        time.sleep(max(sleep_s, 1))

if __name__ == "__main__":
    main()
