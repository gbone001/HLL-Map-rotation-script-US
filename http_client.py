
import requests
import logging
from config import get_env

log = logging.getLogger(__name__)

class CrconHttpError(Exception):
    pass

def http_rcon(command: str) -> str:
    base = get_env("CRCON_HTTP_BASE_URL")
    if not base:
        raise CrconHttpError("CRCON_HTTP_BASE_URL missing")

    token = get_env("CRCON_HTTP_BEARER_TOKEN")
    if not token:
        raise CrconHttpError("CRCON_HTTP_BEARER_TOKEN missing")

    url = base.rstrip("/") + "/api/rcon/command"
    payload = {"command": command}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    timeout = float(get_env("CRCON_HTTP_TIMEOUT", "10"))
    verify_raw = get_env("CRCON_HTTP_VERIFY", "false").lower()
    verify = verify_raw not in ("false", "0", "no")

    log.debug(f"HTTP → {url} payload={payload}")

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout, verify=verify)
    except Exception as e:
        raise CrconHttpError(str(e))

    if r.status_code != 200:
        raise CrconHttpError(f"HTTP {r.status_code}: {r.text}")

    data = r.json()
    return data.get("result") or data.get("output") or ""
