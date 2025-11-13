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

        # Prefer username/password login if provided (mirrors hll-discord-ping behavior).
        # Fall back to bearer token if login credentials are not supplied.
        self.username = get_setting("CRCON_HTTP_USERNAME", "CRCON_HTTP_USERNAME")
        self.password = get_setting("CRCON_HTTP_PASSWORD", "CRCON_HTTP_PASSWORD")
        token = get_setting("CRCON_HTTP_BEARER_TOKEN", "CRCON_HTTP_BEARER_TOKEN")

        self.timeout = float(get_setting("CRCON_HTTP_TIMEOUT", "CRCON_HTTP_TIMEOUT", "10"))
        verify_raw = get_setting("CRCON_HTTP_VERIFY", "CRCON_HTTP_VERIFY", "true").lower()
        self.verify = verify_raw not in ("false", "0", "no", "off")
        self.api_root = get_setting("CRCON_HTTP_API_ROOT", "CRCON_HTTP_API_ROOT", "/api").strip("/")

        self.session = requests.Session()
        # Always set JSON content-type. Authorization header is only used for token mode.
        self.session.headers.update({"Content-Type": "application/json"})

        # Initialize auth: login (preferred) or bearer token (fallback)
        if self.username and self.password:
            log.info(
                "Initialized HTTP CRCON API client (login mode) for %s/%s",
                self.base_url.rstrip("/"),
                self.api_root or "",
            )
            self._login()
        else:
            if not token:
                raise CrconHttpError("CRCON_HTTP_BEARER_TOKEN or CRCON_HTTP_USERNAME/CRCON_HTTP_PASSWORD is required for HTTP CRCON")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            log.info("Initialized HTTP CRCON API client (token mode) for %s/%s", self.base_url.rstrip("/"), self.api_root or "")


    def _build_url(self, endpoint: str) -> str:
        base = self.base_url.rstrip("/")
        parts = [base]
        if self.api_root:
            parts.append(self.api_root.strip("/"))
        parts.append(endpoint.lstrip("/"))
        return "/".join(parts)

    def _login(self) -> None:
        """Perform a login to the CRCON HTTP API and retain session cookies.

        Expects `self.username` and `self.password` to be set.
        """
        if not self.username or not self.password:
            raise CrconHttpError("CRCON_HTTP_USERNAME and CRCON_HTTP_PASSWORD are required for login-based HTTP CRCON")

        url = self._build_url("login")
        try:
            resp = self.session.post(
                url,
                json={"username": self.username, "password": self.password},
                timeout=self.timeout,
                verify=self.verify,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise CrconHttpError(f"login failed: {exc}") from exc

        log.info("HTTP CRCON login successful as %s", self.username)

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
        log.info("Requesting map rotation via HTTP API")
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
        # Attempt to normalize names to the server's canonical rotation entries
        try:
            rotation_resp = self._request("get_map_rotation", method="GET")
        except CrconHttpError:
            rotation_resp = None

        canonical = self._resolve_to_canonical(names, rotation_resp)
        try:
            self._request(
                "add_maps_to_rotation",
                json_payload={
                    "map_names": canonical,
                    "arguments": {"map_names": canonical},
                },
            )
        except CrconHttpError as exc:
            # If the server rejects some maps as not valid, bubble up unless it's the
            # specific "not in rotation" type of message; log and continue otherwise.
            msg = str(exc)
            error_text = (rotation_resp or {}).get("error") or ""
            if "not in rotation" in msg or "not in rotation" in error_text:
                log.warning("Some add_maps_to_rotation entries invalid: %s", msg)
                return
            raise

    def remove_maps_from_rotation(self, map_names: Iterable[str]) -> None:
        names = [name for name in map_names if name]
        if not names:
            return
        # Normalize requested names against current rotation entries so we send
        # the canonical identifiers the API expects (many deployments use
        # internal layer names rather than pretty display names).
        try:
            rotation_resp = self._request("get_map_rotation", method="GET")
        except CrconHttpError:
            rotation_resp = None

        canonical = [name for name in self._resolve_to_canonical(names, rotation_resp) if name]
        if not canonical:
            log.debug("Skipping remove_maps_from_rotation because no canonical names were resolved")
            return

        try:
            self._request(
                "remove_maps_from_rotation",
                json_payload={
                    "map_names": canonical,
                    "arguments": {"map_names": canonical},
                },
            )
        except CrconHttpError as exc:
            # Server may respond 400 when attempting to remove maps that are
            # already absent. Treat that as non-fatal for idempotency.
            msg = str(exc)
            error_text = (rotation_resp or {}).get("error") or ""
            msg_lower = msg.lower()
            if "not in rotation" in msg_lower or "map" in msg_lower and "not in rotation" in msg_lower or "not in rotation" in error_text.lower():
                log.warning("HTTP rotation removal failed (ignored): %s", msg)
                return
            raise

    def _resolve_to_canonical(self, requested_names, rotation_resp):
        """Map a list of requested names (pretty or layer names) to canonical
        identifiers present in the current rotation response.

        rotation_resp is the raw parsed response from `get_map_rotation` and
        may be None if the fetch failed.
        """
        # If we couldn't fetch rotation entries, return requests unchanged
        if not rotation_resp:
            return list(requested_names)

        # Extract rotation entries (may be under 'result' or 'rotation')
        payload = rotation_resp.get("result") if isinstance(rotation_resp, dict) else rotation_resp
        if isinstance(payload, dict) and "rotation" in payload:
            entries = payload["rotation"]
        elif isinstance(payload, list):
            entries = payload
        else:
            entries = []

        # Build candidate map of normalized -> canonical
        def norm(s: str) -> str:
            return "".join(c.lower() for c in s if c.isalnum())

        mapping = {}
        for entry in entries:
            if isinstance(entry, str):
                canonical = entry
                keys = [entry]
            elif isinstance(entry, dict):
                # Prefer layer_name or name as the canonical identifier
                keys = []
                for k in ("layer_name", "name", "map_name", "pretty_name"):
                    v = entry.get(k)
                    if isinstance(v, str) and v:
                        keys.append(v)
                canonical = (
                    entry.get("layer_name")
                    or entry.get("name")
                    or entry.get("map_name")
                    or entry.get("pretty_name")
                    or (keys[0] if keys else None)
                )
                if not canonical:
                    continue
            else:
                continue

            for k in keys:
                mapping[norm(k)] = canonical

        result = []
        for r in requested_names:
            if not isinstance(r, str):
                continue
            n = norm(r)
            if n in mapping:
                result.append(mapping[n])
            else:
                # no match — send original and let server decide
                result.append(r)

        return result


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
