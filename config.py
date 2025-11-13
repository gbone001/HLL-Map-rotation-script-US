import json
import logging
import os
from pathlib import Path

try:
    import json5 as _json5
except ImportError:  # pragma: no cover
    _json5 = None

LOGGER = logging.getLogger(__name__)

CONFIG_PATH = Path(os.environ.get("CONFIG_PATH", "/app/config.jsonc"))


def _load_config(path: Path):
    if not path.exists():
        return {}
    try:
        if _json5 is not None:
            with path.open("r", encoding="utf-8") as fh:
                LOGGER.info("Loaded configuration from %s", path)
                return _json5.load(fh)
        with path.open("r", encoding="utf-8") as fh:
            LOGGER.info("Loaded configuration from %s", path)
            return json.loads(fh.read())
    except Exception:  # pragma: no cover
        LOGGER.exception("Failed to load configuration from %s", path)
    return {}


def _resolve_config():
    candidates = [CONFIG_PATH, Path.cwd() / "config.jsonc"]
    for candidate in candidates:
        cfg = _load_config(candidate)
        if cfg:
            return cfg
    LOGGER.info("No configuration file found; falling back to environment variables")
    return {}

CONFIG = _resolve_config()


def get_env(name: str, default=None):
    return os.environ.get(name, default)


def get_setting(env_key: str, json_key: str, default=None):
    return os.environ.get(env_key) or CONFIG.get(json_key, default)


def setup_logging():
    raw = get_env("LOG_LEVEL", "INFO").upper()
    if raw not in ("DEBUG", "INFO", "WARN", "ERROR"):
        raw = "INFO"
    logging.basicConfig(
        level=getattr(logging, raw),
        format="[%(asctime)s] [%(levelname)s] %(message)s"
    )


setup_logging()
