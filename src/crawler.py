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


def _parse_count_text(raw: str) -> int | None:
    """Parse counts like 11.4K, 1,234, 2M into integer."""
    if not raw:
        return None
    text = raw.strip().replace(",", "")
    m = re.match(r"^(\d+\.?\d*)([KkMmBb]?)$", text)
    if not m:
        return None

    number = float(m.group(1))
    suffix = m.group(2).lower()
    if suffix == "k":
        number *= 1000
    elif suffix == "m":
        number *= 1000000
    elif suffix == "b":
        number *= 1000000000

    return int(number)


def _parse_initial_skills_from_script_text(script_text: str) -> List[Dict[str, str]]:
    """Parse initialSkills list from one script tag content."""
    patterns = [
        re.compile(r'"initialSkills":(\[[\s\S]*?\])', re.MULTILINE),
    ]

    candidates = [script_text]
    try:
        candidates.append(script_text.encode("utf-8").decode("unicode_escape"))
    except Exception:
        pass

    for content in candidates:
        for pattern in patterns:
            m = pattern.search(content)
            if not m:
                continue
            raw_json = m.group(1)
            try:
                skills_raw = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            normalized: List[Dict[str, str]] = []
            for rank, item in enumerate(skills_raw or [], start=1):
                if not isinstance(item, dict):
                    continue
                source = (item.get("source") or "").strip()
                skill_id = (item.get("skillId") or "").strip()
                name = (item.get("name") or "").strip() or skill_id
                url = _normalize_url(f"/{source}/{skill_id}".rstrip("/"), "https://skills.sh")
                installs = item.get("installs")
                normalized.append(
                    {
                        "id_key": hashlib.sha1(url.lower().encode("utf-8")).hexdigest(),
                        "name": name,
                        "url": url,
                        "category": source,
                        "description": "",
                        "rank": rank,
                        "install_count": int(installs) if isinstance(installs, int) else None,
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                        "raw": json.dumps(item, ensure_ascii=False),
                    }
                )
            if normalized:
                return normalized

    return []


def _parse_embedded_initial_skills(html: str) -> List[Dict[str, str]]:
    """Extract initialSkills from inline Next.js payload if present."""
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script")
    for script in scripts:
        if not script.string:
            continue
        text = script.string
        if "initialSkills" not in text:
            continue
        parsed = _parse_initial_skills_from_script_text(text)
        if parsed:
            return parsed

    # final best-effort regex on whole html for fallback
    return _parse_initial_skills_from_script_text(html)


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

        # rank in first inline span
        rank = None
        rank_span = anchor.find("span")
        if rank_span is not None:
            txt = rank_span.get_text(strip=True)
            if txt.isdigit():
                rank = int(txt)

        # install/score usually appears as right-side number; grab final string token from row
        text_candidates = [x for x in anchor.stripped_strings]
        install_count = None
        if text_candidates:
            install_candidate = text_candidates[-1]
            if not (rank is not None and install_candidate == str(rank)):
                install_count = _parse_count_text(install_candidate)

        category = (p.get_text(strip=True) if p else "").strip()
        url = _normalize_url(href, "https://skills.sh")
        result.append(
            {
                "id_key": hashlib.sha1(url.lower().encode("utf-8")).hexdigest(),
                "name": name,
                "url": url,
                "category": category,
                "description": "",
                "rank": rank,
                "install_count": install_count,
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


def get_trending_skills(url: str | None = None, limit: int | None = None) -> List[Dict[str, str]]:
    html = fetch_trending_html(url=url)
    items = parse_skill_items(html)
    if not limit:
        limit = config.get_trending_limit()
    return items[:limit]
