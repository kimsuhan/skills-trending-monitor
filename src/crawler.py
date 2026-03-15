"""Fetch and parse trending skills from skills.sh."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from src import config


def fetch_trending_html(url: str | None = None, timeout: int = 20) -> str:
    """Fetch HTML from trending page."""
    target = url or config.get_trending_url()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; SkillsTrendingMonitor/0.1; +https://skills.sh)"
    }
    response = requests.get(target, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def _normalize_url(raw_url: str, base_url: str) -> str:
    if not raw_url:
        return ""
    raw_url = raw_url.strip()
    if raw_url.startswith("/"):
        return f"https://skills.sh{raw_url}"
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url
    return f"{base_url.rstrip('/')}/{raw_url.lstrip('/')}"


def _parse_embedded_initial_skills(html: str) -> List[Dict[str, str]]:
    """Extract initialSkills from inline Next.js payload if present."""
    pattern = re.compile(r'self.__next_f\.push\(\[1,"16:\[\"\$\",\"\$L1e\",null,\{\"initialSkills\":(.*?)\]\)\)')
    match = pattern.search(html)
    if not match:
        pattern = re.compile(r'"initialSkills":(\[[\s\S]*?\])', re.MULTILINE)
        match = pattern.search(html)
    if not match:
        return []

    raw_json = match.group(1)
    try:
        skills_raw = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    normalized: List[Dict[str, str]] = []
    for item in skills_raw or []:
        if not isinstance(item, dict):
            continue
        source = (item.get("source") or "").strip()
        skill_id = (item.get("skillId") or "").strip()
        name = (item.get("name") or "").strip() or skill_id
        url = _normalize_url(f"/{source}/{skill_id}".rstrip("/"), "https://skills.sh")
        normalized.append(
            {
                "id_key": hashlib.sha1(url.lower().encode("utf-8")).hexdigest(),
                "name": name,
                "url": url,
                "category": source,
                "description": "",
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "raw": json.dumps(item, ensure_ascii=False),
            }
        )
    return normalized


def _parse_a_tag_rows(html: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    result: List[Dict[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href.startswith("/"):
            continue
        if not href.count("/") >= 2:
            continue
        if href.startswith("/search") or href.startswith("/docs"):
            continue

        h3 = anchor.find("h3")
        p = anchor.find("p")
        name = (h3.get_text(strip=True) if h3 else "").strip()
        if not name:
            continue
        category = (p.get_text(strip=True) if p else "").strip()
        rank_span = anchor.find("span")
        url = _normalize_url(href, "https://skills.sh")
        result.append(
            {
                "id_key": hashlib.sha1(url.lower().encode("utf-8")).hexdigest(),
                "name": name,
                "url": url,
                "category": category,
                "description": "",
                "discovered_at": datetime.now(timezone.utc).isoformat(),
                "raw": anchor.decode(),
            }
        )

    return result


def parse_skill_items(html: str) -> List[Dict[str, str]]:
    """Parse trending skills from HTML."""
    extracted = _parse_embedded_initial_skills(html)
    if extracted:
        return extracted
    return _parse_a_tag_rows(html)


def get_trending_skills(url: str | None = None) -> List[Dict[str, str]]:
    html = fetch_trending_html(url=url)
    return parse_skill_items(html)
