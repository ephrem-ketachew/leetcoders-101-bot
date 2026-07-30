export interface Env {
  TELEGRAM_BOT_TOKEN: string;
  GITHUB_PAT: string;
  GITHUB_REPO: string;
  TELEGRAM_WEBHOOK_SECRET: string;
  TELEGRAM_CHAT_ID?: string;
  COMMANDS_ENABLED?: string;
}

function commandsEnabled(env: Env): boolean {
  const value = env.COMMANDS_ENABLED?.trim().toLowerCase();
  return value === "true" || value === "1";
}

interface TelegramMessage {
  message_id: number;
  chat: { id: number; type: string };
  text?: string;
}

interface TelegramUpdate {
  message?: TelegramMessage;
}

const HELP_TEXT = `LeetCoders 101 Bot commands:
/today - Generate today's progress report
/stats - Show current streaks (from saved state)
/help  - Show this message

Daily report runs automatically at 3:00 AM EAT.`;

function parseCommand(text: string): string | null {
  const first = text.trim().split(/\s+/)[0]?.toLowerCase();
  if (!first || !first.startsWith("/")) {
    return null;
  }
  const command = first.split("@")[0];
  if (command === "/today" || command === "/stats" || command === "/help") {
    return command;
  }
  return null;
}

async function sendTelegramMessage(
  env: Env,
  chatId: number,
  text: string,
): Promise<void> {
  const response = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        disable_web_page_preview: true,
      }),
    },
  );

  if (!response.ok) {
    const body = await response.text();
    console.error(`Telegram send failed: ${response.status} ${body}`);
  }
}

async function dispatchGitHub(env: Env, eventType: string): Promise<void> {
  const response = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "leetcoders-101-worker",
      },
      body: JSON.stringify({
        event_type: eventType,
        client_payload: {},
      }),
    },
  );

  if (response.status !== 204) {
    const body = await response.text();
    console.error(`GitHub dispatch failed: ${response.status} ${body}`);
    throw new Error(`GitHub dispatch failed: ${response.status}`);
  }
}

async function handleWebhook(request: Request, env: Env): Promise<Response> {
  const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
  if (!secret || secret !== env.TELEGRAM_WEBHOOK_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  let update: TelegramUpdate;
  try {
    update = (await request.json()) as TelegramUpdate;
  } catch {
    return new Response("Bad Request", { status: 400 });
  }

  const message = update.message;
  if (!message?.text) {
    return new Response("OK");
  }

  const chatType = message.chat.type;
  if (chatType !== "group" && chatType !== "supergroup") {
    return new Response("OK");
  }

  if (env.TELEGRAM_CHAT_ID && String(message.chat.id) !== env.TELEGRAM_CHAT_ID) {
    return new Response("OK");
  }

  const command = parseCommand(message.text);
  if (!command) {
    return new Response("OK");
  }

  if (!commandsEnabled(env)) {
    console.log(`Ignored disabled command: ${command}`);
    return new Response("OK");
  }

  try {
    if (command === "/help") {
      await sendTelegramMessage(env, message.chat.id, HELP_TEXT);
      return new Response("OK");
    }

    if (command === "/today") {
      await sendTelegramMessage(
        env,
        message.chat.id,
        "Generating report... This usually takes under a minute.",
      );
      await dispatchGitHub(env, "on-demand-report");
      return new Response("OK");
    }

    if (command === "/stats") {
      await sendTelegramMessage(
        env,
        message.chat.id,
        "Fetching stats...",
      );
      await dispatchGitHub(env, "stats-only");
      return new Response("OK");
    }
  } catch (error) {
    console.error(error);
    await sendTelegramMessage(
      env,
      message.chat.id,
      "Something went wrong. Please try again later.",
    );
  }

  return new Response("OK");
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return new Response("OK");
    }

    if (request.method === "POST" && url.pathname === "/webhook") {
      return handleWebhook(request, env);
    }

    return new Response("Not Found", { status: 404 });
  },
};
