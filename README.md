# Skills Trending Monitor

A lightweight tool that:

1. Crawls `https://skills.sh/trending`
2. Stores discovered skills in SQLite with deduplication
3. Notifies new skills via Discord webhook
4. Runs daily at 09:00 KST

## Project Layout

- `src/crawler.py` – fetch + parse trending page
- `src/storage.py` – SQLite storage with duplicate-safe insert
- `src/notifier.py` – Discord webhook formatting and delivery
- `src/main.py` – orchestrates daily run
- `src/config.py` – configuration/env helpers
- `tests/` – pytest coverage
- `cronjobs/` – cron file templates
- `data/` – local sqlite db location

## Setup

```bash
cd /path/to/projects/skills-trending-monitor
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Required env var:
- `DISCORD_WEBHOOK_URL`

Optional env vars:
- `DB_PATH` (default: `./data/trending.db`)
- `SKILLS_TRENDING_URL` (default: `https://skills.sh/trending`)
- `WEBHOOK_RETRY_ATTEMPTS` (default: `3`)
- `WEBHOOK_RETRY_BACKOFF_SECONDS` (default: `1.0`)

## Runtime environment file (recommended)

Create `.env` at project root (not committed) and load it in cron:

```bash
cp .env.example .env
chmod 600 .env
```

Example:
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DB_PATH=./data/trending.db
WEBHOOK_RETRY_ATTEMPTS=3
WEBHOOK_RETRY_BACKOFF_SECONDS=1.0
```

## Manual run

```bash
cd /path/to/projects/skills-trending-monitor
source .venv/bin/activate
source .env
python -m src.main
```

## Cron setup

Use `cronjobs/skills-trending-monitor-cron` as a template.

```cron
0 9 * * * shkim cd /path/to/projects/skills-trending-monitor && \
  set -a && [ -f /path/to/projects/skills-trending-monitor/.env ] && source /path/to/projects/skills-trending-monitor/.env || true && set +a && \
  /path/to/projects/skills-trending-monitor/.venv/bin/python -m src.main >> /path/to/projects/skills-trending-monitor/logs/run.log 2>&1
```
