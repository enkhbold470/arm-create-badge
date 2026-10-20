// Badge wall: anyone with the link sends a short message, the badge polls for
// new ones with its token and scrolls them across the screen.
//
//   GET  /                 the page with the form
//   POST /api/send         {name, text} from the page, rate limited per sender
//   GET  /api/inbox?after  messages newer than an id, for the badge (token)
//   POST /api/hide         {id} drops a message from the badge (token)
//
// BADGE_TOKEN is a Worker secret: `wrangler secret put BADGE_TOKEN`. The same
// value goes in the badge's secrets.py as WALL_TOKEN.

import { DurableObject } from "cloudflare:workers";

const OWNER = "Inky";
const NAME_MAX = 20;
const TEXT_MAX = 80;            // what fits the badge at a readable size
const SENDER_GAP_S = 15;        // between two messages from one sender
const SENDER_HOURLY = 10;
const GLOBAL_HOURLY = 300;      // so a flood can't bury the badge
const INBOX_PAGE = 20;

// Shown on a stranger's badge in a public place, so the obvious words are
// refused outright; the owner hides anything else from the badge itself.
const BLOCKED = [
  "fuck", "shit", "cunt", "bitch", "nigg", "fag", "retard", "whore", "slut",
  "rape", "porn", "pussy", "nazi",
];

function refused(text) {
  const flat = text.toLowerCase().replace(/[^a-z]/g, "");
  if (BLOCKED.some((word) => flat.includes(word))) return "Let's keep it friendly.";
  if (/https?:|www\.|\.(com|net|io|ai|xyz|ru)\b/i.test(text)) return "No links, sorry.";
  return null;
}

function clean(value, max) {
  return String(value ?? "")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, max);
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

function authorised(request, env) {
  const given = (request.headers.get("authorization") || "").replace(/^Bearer /, "");
  const want = env.BADGE_TOKEN || "";
  if (!want || given.length !== want.length) return false;
  let diff = 0;
  for (let i = 0; i < want.length; i++) diff |= given.charCodeAt(i) ^ want.charCodeAt(i);
  return diff === 0;
}

export class Wall extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL, text TEXT NOT NULL, ts INTEGER NOT NULL,
      sender TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0)`);
    this.sql.exec("CREATE INDEX IF NOT EXISTS by_sender ON messages (sender, ts)");
  }

  send(name, text, sender) {
    const now = Math.floor(Date.now() / 1000);
    const [mine] = this.sql.exec(
      "SELECT COUNT(*) AS n, MAX(ts) AS last FROM messages WHERE sender = ? AND ts > ?",
      sender, now - 3600).toArray();
    if (mine.last && now - mine.last < SENDER_GAP_S) {
      return { error: "Slow down a little, try again in a few seconds." };
    }
    if (mine.n >= SENDER_HOURLY) return { error: "That's plenty for this hour, thank you!" };
    const [all] = this.sql.exec("SELECT COUNT(*) AS n FROM messages WHERE ts > ?",
                                now - 3600).toArray();
    if (all.n >= GLOBAL_HOURLY) return { error: "The badge is swamped right now, try later." };

    const [row] = this.sql.exec(
      "INSERT INTO messages (name, text, ts, sender) VALUES (?, ?, ?, ?) RETURNING id",
      name, text, now, sender).toArray();
    return { ok: true, id: row.id };
  }

  inbox(after) {
    const messages = this.sql.exec(
      "SELECT id, name, text, ts FROM messages WHERE id > ? AND hidden = 0 ORDER BY id LIMIT ?",
      after, INBOX_PAGE).toArray();
    return { messages };
  }

  hide(id) {
    this.sql.exec("UPDATE messages SET hidden = 1 WHERE id = ?", id);
    return { ok: true };
  }
}

async function sha(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].slice(0, 12)
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const wall = env.WALL.get(env.WALL.idFromName("main"));

    if (url.pathname === "/" && request.method === "GET") {
      return new Response(PAGE, {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    if (url.pathname === "/api/send" && request.method === "POST") {
      let body;
      try {
        body = await request.json();
      } catch {
        return json({ error: "Bad request." }, 400);
      }
      const name = clean(body.name, NAME_MAX) || "Someone";
      const text = clean(body.text, TEXT_MAX);
      if (!text) return json({ error: "Write something first." }, 400);
      const why = refused(name + " " + text);
      if (why) return json({ error: why }, 400);
      // senders are kept as a hash of their address, never the address itself
      const sender = await sha((request.headers.get("cf-connecting-ip") || "?") + env.BADGE_TOKEN);
      const result = await wall.send(name, text, sender);
      return json(result, result.ok ? 200 : 429);
    }

    if (url.pathname === "/api/inbox" && request.method === "GET") {
      if (!authorised(request, env)) return json({ error: "Not your badge." }, 401);
      const after = parseInt(url.searchParams.get("after") || "0", 10) || 0;
      return json(await wall.inbox(after));
    }

    if (url.pathname === "/api/hide" && request.method === "POST") {
      if (!authorised(request, env)) return json({ error: "Not your badge." }, 401);
      const { id } = await request.json().catch(() => ({}));
      return json(await wall.hide(parseInt(id, 10) || 0));
    }

    return json({ error: "Not found." }, 404);
  },
};

const PAGE = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Message ${OWNER}'s badge</title>
<style>
  :root { --bg: #0b0b10; --card: #16161f; --text: #f2f2f5; --muted: #9a9aa8;
          --accent: #ff9d2e; --accent2: #f26419; --ok: #95d600; --line: #2a2a36; }
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--text);
         font: 17px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         display: flex; align-items: center; justify-content: center; padding: 24px 16px; }
  main { width: 100%; max-width: 420px; }
  .badge { font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }
  h1 { font-size: 28px; line-height: 1.15; margin: 8px 0 6px; }
  p.lede { color: var(--muted); margin: 0 0 22px; }
  form { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 18px; }
  label { display: block; font-size: 14px; color: var(--muted); margin: 0 0 6px; }
  input, textarea { width: 100%; background: var(--bg); color: var(--text); border: 1px solid var(--line);
                    border-radius: 10px; padding: 12px; font: inherit; }
  input:focus, textarea:focus { outline: 2px solid var(--accent); border-color: transparent; }
  textarea { resize: none; height: 96px; }
  .row { margin-bottom: 14px; }
  .count { float: right; font-size: 13px; color: var(--muted); }
  button { width: 100%; border: 0; border-radius: 10px; padding: 14px; font: inherit; font-weight: 600;
           color: #111; background: linear-gradient(90deg, var(--accent2), var(--accent)); cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  #status { min-height: 1.5em; margin-top: 14px; text-align: center; }
  #status.ok { color: var(--ok); } #status.err { color: #ff7a6b; }
  footer { margin-top: 18px; font-size: 13px; color: var(--muted); text-align: center; }
  a { color: var(--accent); }
</style>
</head>
<body>
<main>
  <div class="badge">Arm Create &middot; live badge</div>
  <h1>Send ${OWNER} a message</h1>
  <p class="lede">It pops up on the badge around ${OWNER}'s neck within a few seconds. Keep it short and friendly.</p>
  <form id="f">
    <div class="row">
      <label for="name">Your name <span style="opacity:.6">(optional)</span></label>
      <input id="name" maxlength="${NAME_MAX}" autocomplete="nickname" placeholder="Ada">
    </div>
    <div class="row">
      <label for="text">Message <span class="count" id="count">0/${TEXT_MAX}</span></label>
      <textarea id="text" maxlength="${TEXT_MAX}" placeholder="Nice badge! I use Arch too, btw" required></textarea>
    </div>
    <button id="go">Send to the badge</button>
    <div id="status" role="status"></div>
  </form>
  <footer>Building <a href="https://heypcb.ai">heypcb.ai</a></footer>
</main>
<script>
  const f = document.getElementById("f"), go = document.getElementById("go");
  const text = document.getElementById("text"), name = document.getElementById("name");
  const status = document.getElementById("status"), count = document.getElementById("count");
  try { name.value = localStorage.getItem("name") || ""; } catch (e) {}
  text.addEventListener("input", () => { count.textContent = text.value.length + "/${TEXT_MAX}"; });
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    go.disabled = true; status.className = ""; status.textContent = "Sending...";
    try { localStorage.setItem("name", name.value); } catch (e) {}
    try {
      const r = await fetch("/api/send", { method: "POST", headers: { "content-type": "application/json" },
                                           body: JSON.stringify({ name: name.value, text: text.value }) });
      const out = await r.json();
      if (out.ok) {
        status.className = "ok"; status.textContent = "Sent! Watch the badge light up.";
        text.value = ""; count.textContent = "0/${TEXT_MAX}";
      } else { status.className = "err"; status.textContent = out.error || "Something went wrong."; }
    } catch (err) { status.className = "err"; status.textContent = "Couldn't reach the server."; }
    go.disabled = false;
  });
</script>
</body>
</html>`;
