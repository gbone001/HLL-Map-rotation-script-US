
import json
import time
import logging
from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from config import get_env
from http_client import http_rcon, CrconHttpError
from rcon_v2 import RconV2

log = logging.getLogger(__name__)

def read_json(path: str):
    with open(path, "r") as f:
        return json.load(f)

def parse(hhmm: str):
    h, m = hhmm.split(":")
    return dtime(int(h), int(m))

def now_tz():
    tz = ZoneInfo(get_env("TIMEZONE", "UTC"))
    return datetime.now(tz)

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

def safe_rcon(command: str):
    try:
        return http_rcon(command)
    except CrconHttpError:
        log.warn("HTTP failed → fallback to RCON v2")
        return RconV2().send_cmd(command)

def get_rotation():
    raw = safe_rcon("rotlist")
    return [line.strip() for line in raw.splitlines() if line.strip()]

def enforce_block(cfg):
    weekday = now_tz().strftime("%A").lower()
    block = get_current_block(cfg)
    target = cfg["schedule"][weekday][block]

    log.info(f"Enforcing {weekday}.{block} rotation: {target}")

    current = get_rotation()
    log.debug(f"Current rotation: {current}")

    if not current:
        log.warn("No current rotation found")
        current_map = None
    else:
        current_map = current[0]

    # Step 1: remove all queued maps except the current one
    for m in current[1:]:
        safe_rcon(f"rotdel {m}")

    # Step 2: add new block after the current map
    for m in target:
        safe_rcon(f"rotadd {m}")

    log.info(f"Rotation updated for block {block}. New maps queued after current match.")

def main():
    path = get_env("WEEKLY_ROTATION_PATH", "./weekly_rotation.json")
    cfg = read_json(path)

    while True:
        enforce_block(cfg)
        nxt = get_next_transition(cfg)
        now = now_tz()
        sleep_s = (nxt - now).total_seconds()
        log.info(f"Next block transition at {nxt.isoformat()}, sleeping for {sleep_s:.0f}s")
        time.sleep(max(sleep_s, 1))

if __name__ == "__main__":
    main()
