# Prerequisites — Credentials and Setup Checklist

Everything below is **free**. No LeetCode login required.

Repository: [ephrem-ketachew/leetcoders-101-bot](https://github.com/ephrem-ketachew/leetcoders-101-bot)

---

## Already configured (Phase 0)

| Item | Value |
|------|-------|
| LeetCode users | ephrem-ketachew, Enoch90s, DivineToad, BisratT |
| Timezone | Africa/Nairobi (3:00 AM daily report) |
| GitHub repo | `ephrem-ketachew/leetcoders-101-bot` |

---

## Phase 3 — Telegram send test

| Secret | Where to get it |
|--------|-----------------|
| **`TELEGRAM_BOT_TOKEN`** | [@BotFather](https://t.me/BotFather) → `/newbot` → copy token |
| **`TELEGRAM_CHAT_ID`** | Add bot to group → send a message → visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → find `"chat":{"id":-100...}` |

Tip: test in a private group first.

---

## Phase 4 — GitHub Actions (scheduled daily report)

Add as **GitHub repository secrets** (`Settings → Secrets and variables → Actions`):

| Secret | Where to get it |
|--------|-----------------|
| `TELEGRAM_BOT_TOKEN` | BotFather |
| `TELEGRAM_CHAT_ID` | getUpdates API |
| `CF_ACCOUNT_ID` | [Cloudflare Dashboard](https://dash.cloudflare.com) → Account ID (right sidebar) |
| `CF_KV_NAMESPACE_ID` | Workers & Pages → KV → create `leetcode-bot-state` → copy Namespace ID |
| `CF_API_TOKEN` | My Profile → API Tokens → Custom → **Workers KV Storage: Edit** |

Sign up at [cloudflare.com](https://cloudflare.com) (free, no domain needed).

---

## Phase 5 — On-demand `/today` and `/stats`

Cloudflare Worker secrets (via `wrangler secret put`):

| Secret | Where to get it |
|--------|-----------------|
| `TELEGRAM_BOT_TOKEN` | BotFather |
| `GITHUB_PAT` | GitHub → Settings → Developer settings → Fine-grained PAT → this repo → **Actions: Read and write** |
| `GITHUB_REPO` | `ephrem-ketachew/leetcoders-101-bot` |

Recommended:

| Item | Purpose |
|------|---------|
| `TELEGRAM_WEBHOOK_SECRET` | Random string you generate; blocks spoofed webhook calls |
| Worker subdomain | Assigned on first `wrangler deploy` (e.g. `your-name.workers.dev`) |

Set webhook after Worker deploy:

```
https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<worker>.workers.dev/webhook&secret_token=<SECRET>
```

---

## Not needed

- LeetCode password or session cookie
- LeetCode API key
- Paid hosting

---

## Local development

1. Copy `.env.example` → `.env` and fill secrets as you reach each phase.
2. Python 3.12+: `python -m venv .venv` then activate and `pip install -r requirements.txt`.
3. Verify config: `python -m src.main config`

---

## Checklist

```
Phase 0:  [x] LeetCode usernames, GitHub repo
Phase 3:  [ ] TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Phase 4:  [ ] CF_ACCOUNT_ID, CF_KV_NAMESPACE_ID, CF_API_TOKEN
Phase 5:  [ ] GITHUB_PAT, TELEGRAM_WEBHOOK_SECRET, Worker deployed
```
