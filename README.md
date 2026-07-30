# LeetCoders 101 Bot

Automated Telegram bot that tracks daily LeetCode progress for a group of friends. Posts a scheduled report at **3:00 AM East Africa Time** and supports on-demand commands via Telegram.

**Team:** Ephrem, Henok, Gelila, Bisrat  
**Repo:** [github.com/ephrem-ketachew/leetcoders-101-bot](https://github.com/ephrem-ketachew/leetcoders-101-bot)

---

## What it does

Every day the bot fetches recent accepted submissions from LeetCode for each tracked user, counts new solves since the last run, breaks them down by difficulty, updates streaks, and posts a formatted report to your Telegram group. On-demand commands (`/today`, `/stats`) trigger the same pipeline via a Cloudflare Worker webhook.

---

## Architecture

```mermaid
flowchart TB
  subgraph scheduled [Scheduled Path]
    Cron["GHA Cron 00:00 UTC"] --> DailyJob["Python daily job"]
  end

  subgraph ondemand [On-demand Path]
    User["User sends /today or /stats"] --> TG["Telegram"]
    TG --> Webhook["CF Worker webhook"]
    Webhook --> Dispatch["repository_dispatch to GHA"]
    Dispatch --> OnDemandJob["Python on-demand job"]
  end

  DailyJob --> LC["LeetCode GraphQL"]
  OnDemandJob --> LC
  DailyJob --> KV["Cloudflare KV state"]
  OnDemandJob --> KV
  DailyJob --> Report["Report builder"]
  OnDemandJob --> Report
  Report --> Send["Telegram sendMessage"]
```

---

## Phase status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project scaffold, config, docs | Done |
| 1 | LeetCode GraphQL client + problem cache | Done |
| 2 | Cloudflare KV state + incremental sync | Done |
| 3 | Report builder + Telegram sender | Pending |
| 4 | GitHub Actions daily cron | Pending |
| 5 | Cloudflare Worker on-demand commands | Pending |
| 6 | Retries, error handling, polish | Pending |

---

## Local setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env   # fill in as you reach each phase
```

Verify configuration:

```bash
python -m src.main config
python -m src.main --help
```

---

## Phase 1 usage (LeetCode fetch)

Build the local problem difficulty cache (first run, ~10-15 seconds):

```bash
python -m src.main cache-problems
```

Fetch recent submissions for one user:

```bash
python -m src.main fetch --user ephrem-ketachew
```

Fetch all teammates from `config/users.yaml`:

```bash
python -m src.main fetch --all
```

Refresh the cache manually:

```bash
python -m src.main cache-problems --force
```

---

## Phase 2 usage (state sync)

Preview sync without writing state (first run bootstraps in memory only):

```bash
python -m src.main sync --dry-run
```

Run sync and persist state (uses local `data/state/` when Cloudflare creds are absent):

```bash
python -m src.main sync
```

Confirm no new submissions after bootstrap:

```bash
python -m src.main sync --dry-run
```

Optional: only show submissions since the last daily report (once Phase 4 sets `last_report_at`):

```bash
python -m src.main sync --since-report
```

**Note:** Without `CF_ACCOUNT_ID`, `CF_KV_NAMESPACE_ID`, and `CF_API_TOKEN` in `.env`, state is stored locally under `data/state/`. Add those variables to use Cloudflare KV instead.

---

## CLI commands

| Command | Phase | Description |
|---------|-------|-------------|
| `python -m src.main config` | 0 | Show loaded users and schedule |
| `python -m src.main cache-problems [--force]` | 1 | Download/refresh problem difficulty cache |
| `python -m src.main fetch --user USERNAME` | 1 | Fetch recent LeetCode submissions |
| `python -m src.main fetch --all` | 1 | Fetch submissions for all configured users |
| `python -m src.main sync [--dry-run]` | 2 | Sync state from LeetCode |
| `python -m src.main report [--send]` | 3 | Generate and optionally send report |
| `python -m src.main daily [--send]` | 4 | Full daily pipeline |

---
