"""Configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from urllib.parse import urlparse

DEFAULT_URL: Final = "https://skills.sh/trending"
ALLOWED_WEBHOOK_HOSTS: Final = {"discord.com", "discordapp.com", "discordapp.net"}


def _is_valid_webhook_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    if parsed.hostname is None:
        return False
    host = parsed.hostname.lower()
    return any(host == h or host.endswith(f".{h}") for h in ALLOWED_WEBHOOK_HOSTS)


def get_db_path() -> str:
    db_path = os.getenv("DB_PATH", "./data/trending.db")
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def get_webhook_url() -> str:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return ""
    if not _is_valid_webhook_url(webhook_url):
        # fail closed: if URL is malformed or not expected domain
        return ""
    return webhook_url


def get_trending_url() -> str:
    return os.getenv("SKILLS_TRENDING_URL", DEFAULT_URL).strip()


def get_webhook_retry_attempts() -> int:
    try:
        return max(1, int(os.getenv("WEBHOOK_RETRY_ATTEMPTS", "3").strip()))
    except ValueError:
        return 3


def get_webhook_retry_backoff_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("WEBHOOK_RETRY_BACKOFF_SECONDS", "1.0").strip()))
    except ValueError:
        return 1.0


def get_log_file() -> str:
    return os.getenv("LOG_FILE", "./logs/run.log").strip()


def get_log_max_bytes() -> int:
    try:
        return max(1024, int(os.getenv("LOG_MAX_BYTES", "5242880").strip()))
    except ValueError:
        return 5 * 1024 * 1024


def get_log_backup_count() -> int:
    try:
        return max(1, int(os.getenv("LOG_BACKUP_COUNT", "3").strip()))
    except ValueError:
        return 3

def get_trending_limit() -> int:
    try:
        return max(1, int(os.getenv("SKILLS_TRENDING_LIMIT", "400").strip()))
    except ValueError:
        return 400
