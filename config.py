
import os
import logging

def get_env(name: str, default=None):
    return os.getenv(name, default)

def setup_logging():
    raw = get_env("LOG_LEVEL", "INFO").upper()
    if raw not in ("DEBUG", "INFO", "WARN", "ERROR"):
        raw = "INFO"
    logging.basicConfig(
        level=getattr(logging, raw),
        format="[%(asctime)s] [%(levelname)s] %(message)s"
    )

setup_logging()
