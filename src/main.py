"""Orchestrates scheduled trending crawl and alerting."""

from __future__ import annotations

import logging

from src import config
from src.crawler import get_trending_skills
from src.notifier import notify_if_new
from src.storage import get_connection, init_db, list_new_skills, upsert_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)


def run_job() -> int:
    webhook_url = config.get_webhook_url()
    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL is not set or invalid")
        return 1

    conn = get_connection()
    init_db(conn)

    try:
        skills = get_trending_skills()
    except Exception as exc:  # pragma: no cover - network-level errors tested separately
        logger.exception("Failed to crawl trending page: %s", exc)
        return 2

    if not skills:
        logger.info("No skills parsed from trending page")
        return 0

    try:
        new_skills = list_new_skills(conn, skills)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed checking duplicates: %s", exc)
        return 3

    if new_skills:
        try:
            inserted, skipped, _ = upsert_skills(conn, new_skills)
            logger.info(
                "Detected %s new skill(s); inserted=%s skipped=%s",
                len(new_skills),
                inserted,
                skipped,
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to persist skills: %s", exc)
            return 4

        # inserts happen first, then notification.
        # this prevents duplicate sends for retry-safe runs.
        try:
            notify_if_new(
                new_skills,
                webhook_url,
                retries=config.get_webhook_retry_attempts(),
                backoff_seconds=config.get_webhook_retry_backoff_seconds(),
            )
            logger.info("Discord webhook sent (%s skill(s))", len(new_skills))
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to send webhook: %s", exc)
            return 5
    else:
        logger.info("No new skills discovered")

    return 0


def main() -> int:
    return run_job()


if __name__ == "__main__":
    raise SystemExit(main())
