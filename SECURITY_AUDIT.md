# Security Audit Report

## Scope
- src/* (runtime), cron template, README, .gitignore
- Focused on secret leakage, webhook abuse, input integrity, scheduler safety

## Findings & status

1) Secret leakage risk via repo/source code (HIGH)
- Status: **MITIGATED**
- Action: removed hardcoded webhook usage from code and cron examples.
- Added `.env.example` with placeholders and `.gitignore` entries for `.env*`.

2) Unvalidated webhook endpoint (MEDIUM)
- Status: **MITIGATED**
- Action: added webhook URL validation in `src/config.py` to allow only HTTPS and expected Discord hosts.
- `main.py` treats invalid/missing webhook as hard fail.

3) Discord payload / API error due oversized content (MEDIUM)
- Status: **MITIGATED**
- Action: `_split_skills()` now enforces item- and byte-length limits (`MAX_MESSAGE_CHARS = 1800`) and sends in safe batches.

4) Transient webhook failures causing missed alerts (LOW)
- Status: **MITIGATED**
- Action: added exponential-backoff retries via env-configurable `WEBHOOK_RETRY_ATTEMPTS/BACKOFF_SECONDS`.

5) Operational path leakage / brittle manual docs (LOW)
- Status: **MITIGATED**
- Action: replaced absolute paths in README with placeholders to avoid exposing personal paths.

## Residual risks
- Running as cron with shell `source .env` can be sensitive if shell environment is compromised.
  - Remediation: secure host permissions (least-privilege cron user), file permission `chmod 600 .env`, and monitor logs.
- DB file (`data/trending.db`) remains on local disk.
  - Recommendation: restrict permissions on project directory and backup/rotate as needed.

## Follow-up Audit (Path Hygiene)

### Check: template portability
- `cronjobs/skills-trending-monitor-cron` no longer hardcodes user home paths.
- Template now uses placeholders for project path and cron user for safer copy/paste across machines.

### Check: runtime docs
- `README.md` and `cronjobs` template now avoid embedding user-specific absolute paths.
