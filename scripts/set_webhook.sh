#!/usr/bin/env bash
# Register the Telegram webhook for the Cloudflare Worker.
#
# Usage:
#   export TELEGRAM_BOT_TOKEN=...
#   export TELEGRAM_WEBHOOK_SECRET=...
#   export WORKER_URL=https://leetcoders-101-bot.yourname.workers.dev
#   bash scripts/set_webhook.sh

set -euo pipefail

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "TELEGRAM_BOT_TOKEN is required" >&2
  exit 1
fi

if [[ -z "${TELEGRAM_WEBHOOK_SECRET:-}" ]]; then
  echo "TELEGRAM_WEBHOOK_SECRET is required" >&2
  exit 1
fi

if [[ -z "${WORKER_URL:-}" ]]; then
  echo "WORKER_URL is required (e.g. https://leetcoders-101-bot.yourname.workers.dev)" >&2
  exit 1
fi

WEBHOOK_URL="${WORKER_URL%/}/webhook"

curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}" \
  -d 'allowed_updates=["message"]'

echo
echo "Webhook set to: ${WEBHOOK_URL}"
echo "Verify with: curl https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
