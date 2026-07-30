# Register the Telegram webhook for the Cloudflare Worker.
#
# Usage:
#   $env:TELEGRAM_BOT_TOKEN = "..."
#   $env:TELEGRAM_WEBHOOK_SECRET = "..."
#   $env:WORKER_URL = "https://leetcoders-101-bot.yourname.workers.dev"
#   .\scripts\set_webhook.ps1

param()

if (-not $env:TELEGRAM_BOT_TOKEN) {
    Write-Error "TELEGRAM_BOT_TOKEN is required"
    exit 1
}

if (-not $env:TELEGRAM_WEBHOOK_SECRET) {
    Write-Error "TELEGRAM_WEBHOOK_SECRET is required"
    exit 1
}

if (-not $env:WORKER_URL) {
    Write-Error "WORKER_URL is required (e.g. https://leetcoders-101-bot.yourname.workers.dev)"
    exit 1
}

$webhookUrl = "$($env:WORKER_URL.TrimEnd('/'))/webhook"

$body = @{
    url = $webhookUrl
    secret_token = $env:TELEGRAM_WEBHOOK_SECRET
    allowed_updates = '["message"]'
}

$response = Invoke-RestMethod `
    -Uri "https://api.telegram.org/bot$($env:TELEGRAM_BOT_TOKEN)/setWebhook" `
    -Method Post `
    -Body $body

$response | ConvertTo-Json
Write-Host "Webhook set to: $webhookUrl"
Write-Host "Verify with: curl https://api.telegram.org/bot`${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
