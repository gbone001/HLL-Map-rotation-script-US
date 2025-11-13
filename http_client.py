import logging
from typing import Iterable, List, Optional

import requests

from config import get_setting

log = logging.getLogger(__name__)


class CrconHttpError(Exception):
    """Raised when the HTTP CRCON backend cannot execute a command."""


class CrconApiClient:
    def __init__(self):
        self.base_url = get_setting("CRCON_HTTP_BASE_URL", "CRCON_HTTP_BASE_URL")
        if not self.base_url:
            raise CrconHttpError("CRCON_HTTP_BASE_URL is required for HTTP CRCON")

        token = get_setting("CRCON_HTTP_BEARER_TOKEN", "CRCON_HTTP_BEARER_TOKEN")
        if not token:
            raise CrconHttpError("CRCON_HTTP_BEARER_TOKEN is required for HTTP CRCON")

        self.timeout = float(get_setting("CRCON_HTTP_TIMEOUT", "CRCON_HTTP_TIMEOUT", "10"))
        verify_raw = get_setting("CRCON_HTTP_VERIFY", "CRCON_HTTP_VERIFY", "true").lower()
        self.verify = verify_raw not in ("false", "0", "no", "off")
        self.api_root = get_setting("CRCON_HTTP_API_ROOT", "CRCON_HTTP_API_ROOT", "/api").strip("/")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

        log.info("Initialized HTTP CRCON API client for %s/%s", self.base_url.rstrip("/"), self.api_root or "")

    def _build_url(self, endpoint: str) -> str:
        base = self.base_url.rstrip("/")
        parts = [base]
        if self.api_root:
            parts.append(self.api_root.strip("/"))
        parts.append(endpoint.lstrip("/"))
        return "/".join(parts)

    def _request(self, endpoint: str, method: str = "POST", json_payload=None, params=None):
        url = self._build_url(endpoint)
        try:
            response = self.session.request(
                method,
                url,
                json=json_payload,
                params=params,
                timeout=self.timeout,
                verify=self.verify,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            resp = getattr(exc, "response", None)
            body = resp.text if resp is not None else ""
            status = resp.status_code if resp is not None else "request"
            log.debug("HTTP CRCON %s failure: %s", endpoint, exc, exc_info=True)
            raise CrconHttpError(f"{method} {endpoint} failed ({status}): {body or str(exc)}") from exc

        try:
            return response.json()
        except ValueError:
            return {"result": response.text}

    def get_map_rotation(self) -> List[str]:
        data = self._request("get_map_rotation", method="GET")
        payload = data.get("result") if isinstance(data, dict) else data
        if payload is None:
            return []
        if isinstance(payload, dict) and "rotation" in payload:
            payload = payload["rotation"]
        if not isinstance(payload, list):
            return []
        return [
            name
            for entry in payload
            for name in (self._extract_map_name(entry),)
            if name
        ]

    def _extract_map_name(self, entry):
        if isinstance(entry, str):
            return entry
        if not isinstance(entry, dict):
            return None
        for key in ("name", "layer_name", "map_name", "pretty_name"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                return value
        layer = entry.get("layer")
        if isinstance(layer, dict):
            for key in ("name", "layer_name", "map_name", "pretty_name"):
                value = layer.get(key)
                if isinstance(value, str) and value:
                    return value
        return None

    def add_maps_to_rotation(self, map_names: Iterable[str]) -> None:
        names = [name for name in map_names if name]
        if not names:
            return
        self._request("add_maps_to_rotation", json_payload={"map_names": names})

    def remove_maps_from_rotation(self, map_names: Iterable[str]) -> None:
        names = [name for name in map_names if name]
        if not names:
            return
        self._request("remove_maps_from_rotation", json_payload={"map_names": names})


_client: Optional[CrconApiClient] = None


def _get_client() -> CrconApiClient:
    global _client
    if _client is None:
        _client = CrconApiClient()
    return _client


def get_map_rotation() -> List[str]:
    return _get_client().get_map_rotation()


def add_maps_to_rotation(map_names: Iterable[str]) -> None:
    _get_client().add_maps_to_rotation(map_names)


def remove_maps_from_rotation(map_names: Iterable[str]) -> None:
    _get_client().remove_maps_from_rotation(map_names)
