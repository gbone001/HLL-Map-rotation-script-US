import logging
from typing import Optional

import requests

from config import get_env

log = logging.getLogger(__name__)


class CrconHttpError(Exception):
    """Raised when the HTTP CRCON backend cannot execute a command."""


class CrconHttpClient:
    def __init__(self):
        self.base_url = get_env("CRCON_HTTP_BASE_URL")
        if not self.base_url:
            raise CrconHttpError("CRCON_HTTP_BASE_URL is required for HTTP CRCON")

        token = get_env("CRCON_HTTP_BEARER_TOKEN")
        if not token:
            raise CrconHttpError("CRCON_HTTP_BEARER_TOKEN is required for HTTP CRCON")

        self.timeout = float(get_env("CRCON_HTTP_TIMEOUT", "10"))
        verify_raw = get_env("CRCON_HTTP_VERIFY", "true").lower()
        self.verify = verify_raw not in ("false", "0", "no", "off")
        path = get_env("CRCON_HTTP_COMMAND_PATH", "/api/rcon/command")
        self.command_url = self._normalize_url(path)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

        log.info("Initialized HTTP CRCON client for %s", self.command_url)

    def _normalize_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"

    def execute(self, command: str) -> str:
        payload = {"command": command}
        log.debug("HTTP CRCON POST %s payload=%s", self.command_url, payload)
        try:
            response = self.session.post(
                self.command_url,
                json=payload,
                timeout=self.timeout,
                verify=self.verify,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            resp = getattr(exc, "response", None)
            body = resp.text if resp is not None else ""
            status = resp.status_code if resp is not None else "request"
            log.debug("HTTP CRCON failure: %s", exc, exc_info=True)
            raise CrconHttpError(f"HTTP {status}: {body or str(exc)}") from exc

        try:
            data = response.json()
        except ValueError:
            data = {}

        return data.get("result") or data.get("output") or ""


_client: Optional[CrconHttpClient] = None


def _get_client() -> CrconHttpClient:
    global _client
    if _client is None:
        _client = CrconHttpClient()
    return _client


def http_rcon(command: str) -> str:
    return _get_client().execute(command)
