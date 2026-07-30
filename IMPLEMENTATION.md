# Implementation Plan — LeetCoders 101 Bot

Phased build plan for the automated LeetCode progress Telegram bot.

**Repo:** [ephrem-ketachew/leetcoders-101-bot](https://github.com/ephrem-ketachew/leetcoders-101-bot)

---

## Decisions

| Decision | Choice |
|----------|--------|
| LeetCode site | `leetcode.com`, public profiles, zero auth |
| Schedule | Daily at 3:00 AM EAT (= 00:00 UTC, cron `0 0 * * *`) |
| Hosting | GitHub Actions (scheduled) + Cloudflare Worker (commands) |
| State | Cloudflare KV |
| Quote of the Day | v2 backlog |
| Shoutout tone | Neutral, factual |

---

## Team config

| Name | Telegram | LeetCode |
|------|----------|----------|
| Ephrem | @GameOver5 | [ephrem-ketachew](https://leetcode.com/u/ephrem-ketachew/) |
| Henok | @Enoch90s | [Enoch90s](https://leetcode.com/u/Enoch90s/) |
| Gelila | @uly_blue | [DivineToad](https://leetcode.com/u/DivineToad/) |
| Bisrat | @b_isry | [BisratT](https://leetcode.com/u/BisratT/) |

---

## Phase 0 — Project scaffold and docs ✅

**Goal:** Repo skeleton, config loading, documentation. No API calls yet.

**Deliverables:**
- Directory structure with placeholder packages
- `config/users.yaml` with team data
- `src/config.py` — loads YAML + `.env`
- `src/main.py` — stub CLI (`fetch`, `sync`, `report`, `daily`, `config`)
- `README.md`, `PREREQUISITES.md`, `IMPLEMENTATION.md`
- `requirements.txt`, `.env.example`, `.gitignore`

**Acceptance criteria:**
- [x] `pip install -r requirements.txt` succeeds
- [x] `python -m src.main --help` lists commands
- [x] `python -m src.main config` prints 4 users
- [x] No secrets in git

---

## Phase 1 — LeetCode fetcher and problem cache

**Goal:** Fetch recent submissions and resolve problem difficulty.

**Files:**
- `src/leetcode/client.py` — GraphQL client
- `src/leetcode/problems.py` — difficulty cache

**Tasks:**
- `fetch_recent_submissions(username, limit=20)` via `recentAcSubmissionList`
- `fetch_user_profile(username)` — validate public profile
- Bulk-fetch problem list for slug → difficulty mapping
- CLI: `python -m src.main fetch --user ephrem-ketachew`

**GraphQL query:**
```graphql
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id title titleSlug timestamp
  }
}
```

---

## Phase 2 — State store and incremental sync

**Goal:** Persist seen submissions, streaks, and last-active dates in Cloudflare KV.

**Files:**
- `src/state/kv_store.py`
- Sync logic in `src/main.py`

**Tasks:**
- KV read/write via Cloudflare REST API
- Incremental sync: new submission IDs since last run
- Streak logic (calendar days in `Africa/Nairobi`)
- CLI: `python -m src.main sync [--dry-run]`

**KV keys:**
- `state/users/{username}` — seen IDs, streak, last_active_date
- `state/last_report_at` — ISO timestamp
- `cache/problems` — slug → difficulty map

---

## Phase 3 — Report builder and Telegram sender

**Goal:** Format daily report and send to Telegram group.

**Files:**
- `src/report/builder.py`
- `src/report/shoutouts.py`
- `src/telegram/send.py`

**Report sections:**
- Per-user solve counts (Easy / Medium / Hard)
- Problem list for the day
- Highlights (neutral rules)
- Closing line

**Shoutout rules:**
- Most problems solved today
- Any Hard problem solved
- Returned after ≥3 inactive days
- All four users solved ≥1
- Streak milestones: 7, 14, 30, 60 days

**CLI:** `python -m src.main report --dry-run` / `--send`

---

## Phase 4 — GitHub Actions (scheduled daily report)

**Goal:** Automated 3:00 AM EAT report via GitHub Actions cron.

**Files:**
- `.github/workflows/daily-report.yml` — cron `0 0 * * *`
- `.github/workflows/refresh-problem-cache.yml` — weekly cache refresh

**Secrets:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `CF_ACCOUNT_ID`, `CF_KV_NAMESPACE_ID`, `CF_API_TOKEN`

**CLI in workflow:** `python -m src.main daily --send`

---

## Phase 5 — Cloudflare Worker (on-demand commands)

**Goal:** `/today`, `/stats`, `/help` via Telegram webhook.

**Files:**
- `worker/src/index.ts`
- `worker/wrangler.toml`
- `.github/workflows/on-demand-report.yml`
- `scripts/set_webhook.sh`

**Flow:** User command → Worker ack → `repository_dispatch` → GHA runs Python → Telegram report

**Worker secrets:** `TELEGRAM_BOT_TOKEN`, `GITHUB_PAT`, `GITHUB_REPO`

---

## Phase 6 — Hardening and polish

- Retries with exponential backoff on LeetCode requests
- Graceful errors: private profile, unknown user, empty day
- Trim `seen_submission_ids` to prevent KV bloat
- `workflow_dispatch` on daily workflow for manual testing

---

## Phase 7 — v2 backlog

- Quote of the Day
- Weekly summary report
- Leaderboard / streak visualization
- `/leaderboard` command

---

## Testing strategy

| Test | How |
|------|-----|
| LeetCode fetch | CLI against real usernames |
| Report format | `report --dry-run` |
| Telegram send | `--send` to test group first |
| GHA scheduled | `workflow_dispatch` manual trigger |
| Worker webhook | Live `/today` in group |
| Streak logic | Unit tests with mocked dates |

---

## Risks

| Risk | Mitigation |
|------|------------|
| LeetCode GraphQL changes | Isolate queries in `client.py` |
| 20-submission public cap | Daily cron + incremental sync |
| GHA on-demand delay | Worker sends immediate ack |
| Telegram parse errors | Use HTML mode with escaping |
