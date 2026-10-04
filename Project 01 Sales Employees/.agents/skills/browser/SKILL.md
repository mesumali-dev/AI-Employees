---
name: browser
description: Token-efficient, general-purpose browser automation for Claude Code. Drives ONE real, persistent local Chromium instance through a Playwright CLI script (scripts/browser.py) that returns a small structured-JSON object per action — no Playwright MCP server, no per-action tool round trips, no huge DOM snapshots dumped into context. Use whenever a task requires actually interacting with a live webpage rather than reading static content: opening and clicking through a site, filling out or submitting a form, logging into an account, searching within a page, navigating tabs, uploading/downloading files, scrolling, screenshotting, generating a PDF, extracting text/links/tables/forms, running JS on a page, or reading cookies/storage. Trigger for requests like "go to X and click Y", "fill out this form for me", "log into my account on X and check Z", "add this to my cart", "find the pricing page and tell me what it says", "screenshot this page", "scrape the table from this URL", "download the invoice from my dashboard". Prefer this skill over the Playwright MCP for all routine browser automation. Do NOT use for plain web-search lookups that need no page interaction.
---

# Browser — Token-Efficient Chromium Automation

Drives a real Chromium browser through `scripts/browser.py`, a Playwright
CLI you run with `bash`. **No MCP server.** One Chromium process starts
once and stays running with a persistent profile (cookies / logins /
solved CAPTCHAs survive); each command is a fast CDP connection to that
same browser and prints **one small JSON object** — only the fields the
action needs. A multi-step task (log in, visit pages, extract) stays cheap
because you never pay for a full accessibility-tree snapshot per step.

## The core loop — you reason, the script executes

The script makes **no decisions**. It opens pages, clicks, types, reads,
and returns compact JSON. **You** read that JSON and decide the single
next action. That division is the whole point — it keeps the browser out
of the reasoning loop and keeps your context small.

```
you  ──▶  browser.py <action>  ──▶  compact JSON  ──▶  you decide next  ──▶  browser.py ...
```

So the rhythm for any task is: run one command, read its JSON, decide,
run the next command. Don't chain several state-changing commands blind —
after anything risky (a click that navigates, a form submit) read the page
again (`info`, `text`, or `buttons`) and confirm the state changed as
expected before continuing.

> **Windows note:** on this machine use `python`, not `python3` (that's the
> Microsoft Store stub and fails). Quote paths with spaces.

## One-time setup (per machine)

```
pip install playwright
python -m playwright install chromium
```
If this fails (no network, sandboxed env), tell the user rather than
guessing what a page contains. Every command returns
`{"success": false, "error": "Playwright not installed..."}` until setup
is done.

## Lifecycle

```
python scripts/browser.py start      # headed by default; no-op if already up
python scripts/browser.py start --headless   # no visible window (scraping/CI)
python scripts/browser.py status
python scripts/browser.py stop       # only when the whole task is done
```

Start **headed** (the default) for anything where a site may show a login
or a CAPTCHA — a real window is open, so the user solves it once and the
persistent profile remembers it next time. Use `--headless` for unattended
scraping of pages that don't gate you. **Don't `stop` between steps of the
same task** — that throws away tabs and any logged-in session; only stop
when everything is finished.

## Output contract — one JSON object per command

Every command prints exactly one JSON object and exits 0 **even when the
in-browser action fails**, so you can always parse the result and react.
A non-zero process exit means only a setup problem (browser not running,
Playwright missing).

```json
{
  "success": true,
  "action": "links",
  "url": "https://example.com/",
  "title": "Example Domain",
  "error": null,
  "links": [ {"text": "Learn more", "href": "https://iana.org/..."} ]
}
```

On failure you get `{"success": false, "action": "...", "error": "<why>"}`.
When an action can't find an element it comes back as a failure with the
Playwright message — re-inspect and adjust, don't just retry the same call.

Only action-relevant fields are included. `links` returns `links`, not the
page text; `text` returns `text`, not the HTML. **Never request `html`
unless you specifically need raw markup** — `text`, `links`, `buttons`,
`inputs`, `tables`, or `extract` are far cheaper and usually enough. All
readers accept `--max` to cap size.

## Action reference

The module docstring (`python scripts/browser.py --help`, or read
`scripts/browser.py`'s top comment) is the authoritative list. Grouped:

- **Navigate:** `goto <url> [--new-tab] [--wait ...]`, `search <query>
  [--engine google|bing|duckduckgo] [--max N]`, `back`, `forward`, `refresh`
- **Tabs:** `tabs`, `new-tab [url]`, `switch-tab <n>`, `close-tab <n>`
- **Interact:** `click <sel> [--index N]`, `type <sel> <text> [--enter]`,
  `fill <sel> <text>` (instant set), `press <key> [sel]`, `select <sel>
  <value>`, `check`/`uncheck <sel>`, `hover <sel>`, `scroll
  <up|down|top|bottom> [px]`, `submit <sel>`, `upload <sel> <file...>`,
  `download <sel> <path>`
- **Read (compact):** `text [sel] [--max]`, `links [--max]`, `buttons
  [--max]`, `inputs [--max]`, `forms`, `tables [--max]`, `images [--max]`,
  `extract '{"field":"selector"}'`, `eval "<js>"`, `info`, `html [sel]
  [--max]` (raw markup — last resort)
- **Wait:** `wait <seconds>`, `wait-for <sel>`, `wait-text <text>`,
  `wait-idle`  (all take `--timeout MS`)
- **State/capture:** `cookies` (values redacted), `local-storage`,
  `session-storage`, `screenshot <path> [sel] [--full-page]`, `pdf <path>`

Every command except `start`/`stop`/`status` takes `--tab N` to target a
specific tab (default: the last active one).

**Selectors** come straight from the page. When you don't know what to
target, call `buttons` or `inputs` first — they return each interactive
element with a ready-to-use `selector` (prefers `#id`, else
`tag[name="..."]`). Use those selectors verbatim in `click`/`fill`/`type`.

If a task needs something the script doesn't cover, extend
`scripts/browser.py` with a new subcommand rather than reaching for the
Playwright MCP.

## Worked example — search, open a result, extract

```bash
python scripts/browser.py start
python scripts/browser.py search "playwright python api docs" --max 5
#   -> {"results":[{"title":"...","url":"https://playwright.dev/python/..."}, ...]}
python scripts/browser.py goto "https://playwright.dev/python/docs/intro"
python scripts/browser.py text --max 1500
#   read the JSON, decide what's next
python scripts/browser.py stop
```

## Worked example — fill and submit a form

```bash
python scripts/browser.py goto "https://site.example/contact"
python scripts/browser.py inputs          # discover field selectors
python scripts/browser.py fill 'input[name="email"]' "me@example.com"
python scripts/browser.py fill 'textarea[name="message"]' "Hello"
python scripts/browser.py click 'button[type="submit"]'
python scripts/browser.py text            # confirm the success/error message
```

Stop at the review/confirmation screen for anything irreversible (see
Security) and check with the user before the final submit.

## Dynamic content and waits

Don't read or act immediately after a navigation or a click that triggers
loading — a page read too early looks empty or stale and leads you to
wrong conclusions. Use `wait-for <selector>` / `wait-text <text>` for the
specific thing you need (preferred), or `wait-idle` before treating a
mostly-blank SPA as final. Prefer waiting on a concrete element over a
fixed `wait <seconds>`.

## When something's not found

An element-not-found comes back as `success:false`. Before concluding it's
truly absent, work through the common blockers — a click may have
navigated or swapped content, the label may differ slightly, content may
be lazy-loaded below the fold, or a cookie/consent banner or modal may be
intercepting clicks. Re-inspect (`info`, `text`, `buttons`), dismiss
overlays, `scroll down` and re-check, or try an alternate selector. After a
handful of honest attempts without progress, stop and report what's
blocking rather than looping forever. `references/troubleshooting_patterns.md`
has the detailed playbook.

## Search & CAPTCHAs

`search` scrapes result titles + real destination URLs (no ad/junk links)
for Google/Bing/DuckDuckGo. If the engine shows an "unusual traffic" /
"I'm not a robot" check, the result is `{"success":false,
"captcha":true}` — because the browser is headed, tell the user to tick
the box in the open window, then re-run the command. The persistent
profile keeps the session trusted afterward, so it won't keep asking.
Never try to defeat a CAPTCHA programmatically.

## Security & confirmation

- **Never print credentials** — passwords, API keys, tokens, or session
  cookies — into chat, logs, or extracted output, even if visible on the
  page. `cookies` redacts values by design; don't route around that to
  expose a real cookie value unless the user explicitly needs one.
- **Never bypass** authentication, CAPTCHAs, paywalls, or access controls.
  If a page needs a login the user hasn't provided, stop and ask.
- **Never take destructive or irreversible actions** (delete data, cancel
  something, change account settings) unless the user asked for exactly
  that.
- **Confirm before** submitting a purchase/payment, or sending a
  message/email/post on the user's behalf whose content wasn't
  pre-approved. Driving up to the review screen and stopping there is
  expected — don't click the final "Place order" / "Send" without an
  explicit go-ahead.
- If the task itself is designed to defraud a site or third party, decline.

## Output style

Report the outcome, not a narration of every command. After a task, state
what was done, the actual findings/extracted info requested, and whether it
succeeded (and if not, what's blocking + what you tried). Don't narrate
routine steps ("now I'll take a snapshot") — just do them and report the
result.
