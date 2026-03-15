"""Discord webhook formatting and delivery."""

from __future__ import annotations

import logging
import time
from typing import List, Mapping, Sequence

import requests

logger = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 1800  # below Discord 2000-byte payload limit
MAX_ITEMS_PER_MESSAGE = 15


def build_discord_payload(new_skills: Sequence[Mapping[str, str]], start_index: int = 1) -> dict:
    """Build one Discord content payload.

    Args:
      start_index: numbering start for human-readable list index.
    """
    if not new_skills:
        return {"content": "", "username": "Skills Trending Monitor"}

    lines = ["새로운 trending skill이 감지되었습니다."]
    for idx, skill in enumerate(new_skills, start=start_index):
        name = skill.get("name", "(unknown)")
        source = skill.get("category", "")
        url = skill.get("url", "")
        lines.append(f"{idx}. **{name}**")
        if source:
            lines.append(f"   - source: `{source}`")
        if url:
            lines.append(f"   - {url}")
        lines.append("")

    return {
        "content": "\n".join(lines).strip(),
        "username": "Skills Trending Monitor",
    }


def _content_len(payload_content: str) -> int:
    # safer against multibyte characters (Discord has byte-ish payload constraints)
    return len(payload_content.encode("utf-8"))


def _split_skills(skills: Sequence[Mapping[str, str]]) -> List[List[Mapping[str, str]]]:
    batches: List[List[Mapping[str, str]]] = []
    current: List[Mapping[str, str]] = []

    for skill in skills:
        candidate = current + [skill]
        if not current:
            current = [skill]
            if _content_len(build_discord_payload(current)["content"]) > MAX_MESSAGE_CHARS:
                # Rare: if one record itself is too long, keep as single-item batch.
                batches.append(current)
                current = []
            continue

        candidate_payload_len = _content_len(build_discord_payload(candidate)["content"])
        if len(candidate) > MAX_ITEMS_PER_MESSAGE or candidate_payload_len > MAX_MESSAGE_CHARS:
            batches.append(current)
            current = [skill]
            if _content_len(build_discord_payload(current)["content"]) > MAX_MESSAGE_CHARS:
                batches.append(current)
                current = []
        else:
            current = candidate

    if current:
        batches.append(current)

    return batches


def send_to_discord(
    webhook_url: str,
    payload: dict,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> requests.Response:
    """Send once with retry + exponential backoff."""
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(webhook_url, json=payload, timeout=15)
            response.raise_for_status()
            return response
        except Exception as exc:  # broad by design for network/transient faults
            last_exc = exc
            if attempt >= retries:
                break
            sleep_for = backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Discord send failed (attempt %s/%s). retrying in %.1fs: %s",
                attempt,
                retries,
                sleep_for,
                exc,
            )
            if sleep_for > 0:
                time.sleep(sleep_for)

    if last_exc is not None:
        raise last_exc


def notify_if_new(
    new_skills: Sequence[Mapping[str, str]],
    webhook_url: str,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> None:
    if not new_skills:
        return

    index = 1
    for batch in _split_skills(new_skills):
        payload = build_discord_payload(batch, start_index=index)
        if not payload.get("content"):
            continue
        send_to_discord(webhook_url, payload, retries=retries, backoff_seconds=backoff_seconds)
        index += len(batch)
