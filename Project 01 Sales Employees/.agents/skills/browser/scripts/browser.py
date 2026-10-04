#!/usr/bin/env python3
"""
browser.py — Token-efficient, general-purpose browser automation for
Claude Code, built on Playwright + Chromium. NO MCP server involved.

WHY THIS EXISTS
---------------
Driving the Playwright MCP server makes every browser action a separate
LLM round trip, and each `browser_snapshot` dumps thousands of tokens of
accessibility tree into the model's context. This script instead keeps
ONE real Chromium process running in the background (persistent profile,
so cookies / logins / solved CAPTCHAs survive) and every command is a
fast CDP (Chrome DevTools Protocol) connection to that already-running
browser. Each command prints ONE small JSON object — only the fields the
requested action needs — so the model reads ~100-300 tokens instead of a
full DOM dump. Same "work in the subprocess, return a filtered result"
pattern as the lead-hunter and openai-agents-python skills.

DIVISION OF LABOR (important):
  * browser.py  = EXECUTION only. It opens pages, clicks, types, reads,
                  and returns compact JSON. It makes NO decisions.
  * the LLM     = REASONING only. It reads the JSON, decides the single
                  next action, and calls browser.py again.

  LLM -> browser.py (do one action) -> compact JSON -> LLM decides -> ...

ONE-TIME SETUP (per machine). On this Windows box use `python`, NOT
`python3` (that is the Microsoft Store stub and fails):
    pip install playwright
    python -m playwright install chromium

LIFECYCLE
---------
    python browser.py start [--headless] [--port 9222]
        Launch Chromium once (headed by default). No-op if already up.
        Headed keeps you able to solve a login/CAPTCHA in the window;
        the persistent profile then remembers it for later runs.
    python browser.py status
    python browser.py stop
        Close the browser. Do this only when the whole task is done —
        not between steps (you'd lose tabs and any logged-in session).

NAVIGATION
    python browser.py goto <url> [--tab N] [--new-tab] [--wait load|domcontentloaded|networkidle]
    python browser.py search <query> [--engine google|bing|duckduckgo] [--max N]
    python browser.py back [--tab N]
    python browser.py forward [--tab N]
    python browser.py refresh [--tab N]

TABS
    python browser.py tabs                       # list tabs
    python browser.py new-tab [<url>]
    python browser.py switch-tab <N>
    python browser.py close-tab <N>

INTERACTION (one action at a time; re-read the page after risky ones)
    python browser.py click <selector> [--index 0] [--tab N]
    python browser.py type <selector> <text> [--enter] [--delay 30] [--tab N]
    python browser.py fill <selector> <text> [--tab N]     # instant set (no keystrokes)
    python browser.py press <key> [<selector>] [--tab N]   # e.g. Enter, Escape, Control+A
    python browser.py select <selector> <value> [--tab N]
    python browser.py check <selector> [--tab N]
    python browser.py uncheck <selector> [--tab N]
    python browser.py hover <selector> [--tab N]
    python browser.py scroll <up|down|top|bottom> [<pixels>] [--tab N]
    python browser.py submit <selector> [--tab N]
    python browser.py upload <selector> <file_path...> [--tab N]
    python browser.py download <selector> <save_path> [--tab N]

READING / EXTRACTION (compact JSON, no raw DOM dump)
    python browser.py text [<selector>] [--max CHARS] [--tab N]   # visible text
    python browser.py html [<selector>] [--max CHARS] [--tab N]   # only if you ask
    python browser.py links [--max N] [--tab N]
    python browser.py buttons [--max N] [--tab N]
    python browser.py inputs [--max N] [--tab N]        # form fields w/ selectors
    python browser.py forms [--tab N]
    python browser.py tables [--max N] [--tab N]
    python browser.py images [--max N] [--tab N]
    python browser.py extract <fields_json> [--tab N]   # {"price":".price","title":"h1"}
    python browser.py eval <js_expression> [--tab N]    # arbitrary JS, returns result
    python browser.py info [--tab N]                    # {url, title}

WAITING (before reading/acting on dynamic content)
    python browser.py wait <seconds> [--tab N]
    python browser.py wait-for <selector> [--timeout MS] [--tab N]
    python browser.py wait-text <text> [--timeout MS] [--tab N]
    python browser.py wait-idle [--timeout MS] [--tab N]

STATE (cookies / storage / capture)
    python browser.py cookies [--tab N]
    python browser.py local-storage [--tab N]
    python browser.py session-storage [--tab N]
    python browser.py screenshot <save_path> [<selector>] [--full-page] [--tab N]
    python browser.py pdf <save_path> [--tab N]

OUTPUT CONTRACT
---------------
EVERY command prints exactly one JSON object to stdout and exits 0 even on
an in-browser failure (so the caller can always parse it). The process
exit code is non-zero only for setup problems (browser not running,
Playwright missing). Envelope:

    {
      "success": true|false,
      "action":  "<command>",
      "url":     "<current page url>",     # when a page is available
      "title":   "<current page title>",   # when cheap to get
      "error":   null | "<message>",
      ...action-specific fields (text, links, buttons, value, result, ...)
    }

Only the fields relevant to the action are included — e.g. `links` returns
`{success, action, url, links:[{text,href}]}`, not the page text or HTML.
"""

import argparse
import json
import os
import subprocess
import sys
import time

# Force UTF-8 stdout so non-Latin page text (extracted from international
# sites) survives the trip back to the caller — the default Windows console
# codec (cp1252) would replace anything outside Latin-1 with '?'.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STATE_DIR = os.path.expanduser("~/.browser-skill")
PROFILE_DIR = os.path.join(STATE_DIR, "profile")
PIDFILE = os.path.join(STATE_DIR, "chromium.pid")
PORTFILE = os.path.join(STATE_DIR, "chromium.port")
DEFAULT_PORT = 9222


# ---------------------------------------------------------------------------
# Output helpers — one JSON object per command, always parseable.
# ---------------------------------------------------------------------------
def emit(obj):
    """Print a single JSON object and return it."""
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return obj


def ok(action, **fields):
    out = {"success": True, "action": action, "error": None}
    out.update(fields)
    return emit(out)


def fail(action, message, **fields):
    out = {"success": False, "action": action, "error": str(message)}
    out.update(fields)
    return emit(out)


# ---------------------------------------------------------------------------
# Lifecycle — start / stop / status of the background Chromium.
# ---------------------------------------------------------------------------
def _ensure_state_dir():
    os.makedirs(PROFILE_DIR, exist_ok=True)


def _read_port():
    if os.path.exists(PORTFILE):
        try:
            with open(PORTFILE) as f:
                return int(f.read().strip())
        except Exception:
            pass
    return DEFAULT_PORT


def _is_running(port):
    try:
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=2)
        return True
    except Exception:
        return False


def _chromium_exe():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        return p.chromium.executable_path


def cmd_start(args):
    _ensure_state_dir()
    port = args.port or DEFAULT_PORT
    if _is_running(port):
        return ok("start", running=True, port=port, note="already running")

    try:
        exe = _chromium_exe()
    except ModuleNotFoundError:
        return fail("start", "Playwright not installed. Run: pip install playwright "
                             "&& python -m playwright install chromium")

    launch = [
        exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
    ]
    if args.headless:
        launch.append("--headless=new")

    popen_kwargs = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        )
    else:
        popen_kwargs["start_new_session"] = True

    with open(os.path.join(STATE_DIR, "chromium.log"), "a") as log:
        proc = subprocess.Popen(launch, stdout=log, stderr=log,
                                stdin=subprocess.DEVNULL, **popen_kwargs)
    with open(PIDFILE, "w") as f:
        f.write(str(proc.pid))
    with open(PORTFILE, "w") as f:
        f.write(str(port))

    for _ in range(40):
        if _is_running(port):
            return ok("start", running=True, port=port, pid=proc.pid,
                      headless=bool(args.headless))
        time.sleep(0.5)
    return fail("start", f"Chromium did not become ready — see "
                         f"{os.path.join(STATE_DIR, 'chromium.log')}")


def cmd_stop(args):
    killed = False
    if os.path.exists(PIDFILE):
        try:
            with open(PIDFILE) as f:
                pid = int(f.read().strip())
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(pid, 15)
            killed = True
        except (ProcessLookupError, OSError, ValueError):
            pass
        try:
            os.remove(PIDFILE)
        except OSError:
            pass
    if os.path.exists(PORTFILE):
        try:
            os.remove(PORTFILE)
        except OSError:
            pass
    return ok("stop", stopped=killed, note="stopped" if killed else "was not running")


def cmd_status(args):
    port = _read_port()
    return ok("status", running=_is_running(port), port=port)


# ---------------------------------------------------------------------------
# CDP connection to the already-running browser.
# ---------------------------------------------------------------------------
def _connect(port):
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp(f"http://localhost:{port}")
    return pw, browser


def _get_context(browser):
    if browser.contexts:
        return browser.contexts[0]
    return browser.new_context()


def _get_page(context, tab_index):
    pages = context.pages
    if not pages:
        return context.new_page()
    if tab_index is None:
        return pages[-1]
    if 0 <= tab_index < len(pages):
        return pages[tab_index]
    raise IndexError(f"tab {tab_index} out of range (0-{len(pages)-1})")


def with_page(args, fn):
    """Connect, run fn(page, context), always tear the CDP link down.

    fn returns the emitted dict. Any exception is caught and turned into a
    compact failure envelope so the caller always gets parseable JSON.
    """
    action = args.command
    port = _read_port()
    if not _is_running(port):
        return fail(action, "browser not running — run `browser.py start` first")
    pw = browser = None
    try:
        pw, browser = _connect(port)
        context = _get_context(browser)
        page = _get_page(context, getattr(args, "tab", None))
        return fn(page, context)
    except Exception as e:
        return fail(action, e)
    finally:
        try:
            if browser:
                browser.close()
        except Exception:
            pass
        try:
            if pw:
                pw.stop()
        except Exception:
            pass


def _here(page):
    """Current (url, title) — title guarded, it can throw mid-navigation."""
    try:
        title = page.title()
    except Exception:
        title = None
    return page.url, title


# ---------------------------------------------------------------------------
# In-page JS snippets (run once each, return compact structures).
# ---------------------------------------------------------------------------
JS_LINKS = """
(max) => Array.from(document.querySelectorAll('a[href]'))
  .map(a => ({text: (a.innerText||'').trim().slice(0,120), href: a.href}))
  .filter(l => l.href && !l.href.startsWith('javascript:'))
  .slice(0, max)
"""

JS_BUTTONS = """
(max) => Array.from(document.querySelectorAll(
    'button,[role="button"],input[type="submit"],input[type="button"],a.btn'))
  .map(b => {
    const rect = b.getBoundingClientRect();
    if (rect.width===0 || rect.height===0) return null;
    const id = b.id ? '#'+CSS.escape(b.id) : null;
    const name = b.getAttribute('name');
    return {
      text: (b.innerText||b.value||b.getAttribute('aria-label')||'').trim().slice(0,80),
      selector: id || (name ? b.tagName.toLowerCase()+'[name="'+name+'"]' : null),
      tag: b.tagName.toLowerCase(),
    };
  }).filter(Boolean).slice(0, max)
"""

JS_INPUTS = """
(max) => Array.from(document.querySelectorAll('input,textarea,select'))
  .map(el => {
    const rect = el.getBoundingClientRect();
    if ((rect.width===0 || rect.height===0) && el.type!=='hidden') return null;
    const id = el.id ? '#'+CSS.escape(el.id) : null;
    const name = el.getAttribute('name');
    return {
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || null,
      name: name || null,
      placeholder: el.getAttribute('placeholder') || null,
      label: (el.getAttribute('aria-label')||'').slice(0,60) || null,
      selector: id || (name ? el.tagName.toLowerCase()+'[name="'+name+'"]' : null),
    };
  }).filter(Boolean).slice(0, max)
"""

JS_FORMS = """
() => Array.from(document.querySelectorAll('form')).map(f => ({
  action: f.getAttribute('action') || null,
  method: (f.getAttribute('method') || 'get').toLowerCase(),
  id: f.id || null,
  fields: Array.from(f.querySelectorAll('input,textarea,select'))
    .map(el => ({name: el.getAttribute('name')||null,
                 type: el.getAttribute('type')||el.tagName.toLowerCase()}))
    .filter(x => x.name),
}))
"""

JS_TABLES = """
(max) => Array.from(document.querySelectorAll('table')).slice(0, max).map(t => {
  const rows = Array.from(t.querySelectorAll('tr')).slice(0, 50).map(tr =>
    Array.from(tr.querySelectorAll('th,td')).map(c => (c.innerText||'').trim().slice(0,120)));
  const headers = rows.length && t.querySelector('th') ? rows[0] : [];
  return {headers, rows: headers.length ? rows.slice(1) : rows};
})
"""

JS_IMAGES = """
(max) => Array.from(document.querySelectorAll('img[src]'))
  .map(i => ({src: i.src, alt: (i.getAttribute('alt')||'').slice(0,120)}))
  .slice(0, max)
"""

JS_STORAGE = "(which) => { const s = which==='local'?localStorage:sessionStorage; " \
             "const o={}; for(let i=0;i<s.length;i++){const k=s.key(i); o[k]=s.getItem(k);} return o; }"

# Search-engine result scraping — title + real destination URL only.
JS_GOOGLE = """
(max) => Array.from(document.querySelectorAll('div[data-hveid]')).map(el => {
  const a = el.querySelector('a[href^="http"]'); const h3 = el.querySelector('h3');
  return (a && h3) ? {title: h3.innerText.trim(), url: a.href.split('#')[0]} : null;
}).filter(Boolean).slice(0, max)
"""
JS_BING = """
(max) => Array.from(document.querySelectorAll('li.b_algo h2 a')).map(a =>
  ({title: a.innerText.trim(), url: a.href.split('#')[0]})).slice(0, max)
"""
JS_DDG = """
(max) => Array.from(document.querySelectorAll('a[data-testid="result-title-a"]')).map(a =>
  ({title: a.innerText.trim(), url: a.href.split('#')[0]})).slice(0, max)
"""


# ---------------------------------------------------------------------------
# Command implementations.
# ---------------------------------------------------------------------------
def cmd_goto(args):
    def fn(page, ctx):
        p = ctx.new_page() if args.new_tab else page
        p.goto(args.url, wait_until=args.wait, timeout=30000)
        url, title = _here(p)
        return ok("goto", url=url, title=title)
    return with_page(args, fn)


def cmd_search(args):
    engines = {
        "google": ("https://www.google.com/search?q=", JS_GOOGLE),
        "bing":   ("https://www.bing.com/search?q=", JS_BING),
        "duckduckgo": ("https://duckduckgo.com/?q=", JS_DDG),
    }
    base, js = engines.get(args.engine, engines["google"])

    def fn(page, ctx):
        from urllib.parse import quote_plus
        page.goto(base + quote_plus(args.query), wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(700)
        body = ""
        try:
            body = page.evaluate("() => document.body ? document.body.innerText : ''")
        except Exception:
            pass
        if "/sorry/" in (page.url or "") or \
           any(s in body.lower() for s in ("unusual traffic", "not a robot", "detected unusual")):
            url, title = _here(page)
            return fail("search", "search engine is showing a CAPTCHA / robot check - "
                                   "solve it in the browser window, then retry",
                        engine=args.engine, url=url, title=title, captcha=True)
        results = page.evaluate(js, args.max)
        url, title = _here(page)
        return ok("search", engine=args.engine, query=args.query,
                  url=url, title=title, results=results)
    return with_page(args, fn)


def cmd_back(args):
    def fn(page, ctx):
        page.go_back(); url, title = _here(page)
        return ok("back", url=url, title=title)
    return with_page(args, fn)


def cmd_forward(args):
    def fn(page, ctx):
        page.go_forward(); url, title = _here(page)
        return ok("forward", url=url, title=title)
    return with_page(args, fn)


def cmd_refresh(args):
    def fn(page, ctx):
        page.reload(); url, title = _here(page)
        return ok("refresh", url=url, title=title)
    return with_page(args, fn)


def cmd_tabs(args):
    def fn(page, ctx):
        tabs = []
        for i, p in enumerate(ctx.pages):
            try:
                t = p.title()
            except Exception:
                t = None
            tabs.append({"index": i, "url": p.url, "title": t})
        return ok("tabs", tabs=tabs, count=len(tabs))
    return with_page(args, fn)


def cmd_new_tab(args):
    def fn(page, ctx):
        p = ctx.new_page()
        if args.url:
            p.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        idx = ctx.pages.index(p)
        url, title = _here(p)
        return ok("new-tab", index=idx, url=url, title=title)
    return with_page(args, fn)


def cmd_switch_tab(args):
    def fn(page, ctx):
        p = _get_page(ctx, args.index)
        p.bring_to_front()
        url, title = _here(p)
        return ok("switch-tab", index=args.index, url=url, title=title)
    return with_page(args, fn)


def cmd_close_tab(args):
    def fn(page, ctx):
        p = _get_page(ctx, args.index)
        p.close()
        return ok("close-tab", index=args.index, remaining=len(ctx.pages))
    return with_page(args, fn)


def cmd_click(args):
    def fn(page, ctx):
        page.locator(args.selector).nth(args.index).click(timeout=10000)
        url, title = _here(page)
        return ok("click", selector=args.selector, index=args.index, url=url, title=title)
    return with_page(args, fn)


def cmd_type(args):
    def fn(page, ctx):
        loc = page.locator(args.selector).first
        loc.click(timeout=10000)
        loc.type(args.text, delay=args.delay, timeout=10000)
        if args.enter:
            loc.press("Enter")
        url, title = _here(page)
        return ok("type", selector=args.selector, entered=args.enter, url=url, title=title)
    return with_page(args, fn)


def cmd_fill(args):
    def fn(page, ctx):
        page.locator(args.selector).first.fill(args.text, timeout=10000)
        return ok("fill", selector=args.selector)
    return with_page(args, fn)


def cmd_press(args):
    def fn(page, ctx):
        if args.selector:
            page.locator(args.selector).first.press(args.key, timeout=10000)
        else:
            page.keyboard.press(args.key)
        url, title = _here(page)
        return ok("press", key=args.key, url=url, title=title)
    return with_page(args, fn)


def cmd_select(args):
    def fn(page, ctx):
        page.locator(args.selector).first.select_option(args.value, timeout=10000)
        return ok("select", selector=args.selector, value=args.value)
    return with_page(args, fn)


def cmd_check(args):
    def fn(page, ctx):
        page.locator(args.selector).first.check(timeout=10000)
        return ok("check", selector=args.selector)
    return with_page(args, fn)


def cmd_uncheck(args):
    def fn(page, ctx):
        page.locator(args.selector).first.uncheck(timeout=10000)
        return ok("uncheck", selector=args.selector)
    return with_page(args, fn)


def cmd_hover(args):
    def fn(page, ctx):
        page.locator(args.selector).first.hover(timeout=10000)
        return ok("hover", selector=args.selector)
    return with_page(args, fn)


def cmd_scroll(args):
    def fn(page, ctx):
        d = args.direction
        if d == "top":
            page.evaluate("() => window.scrollTo(0, 0)")
        elif d == "bottom":
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        else:
            delta = args.pixels if d == "down" else -args.pixels
            page.mouse.wheel(0, delta)
        return ok("scroll", direction=d)
    return with_page(args, fn)


def cmd_submit(args):
    def fn(page, ctx):
        page.locator(args.selector).first.evaluate(
            "(el) => el.submit ? el.submit() : el.click()")
        url, title = _here(page)
        return ok("submit", selector=args.selector, url=url, title=title)
    return with_page(args, fn)


def cmd_upload(args):
    def fn(page, ctx):
        page.locator(args.selector).first.set_input_files(args.file_path, timeout=10000)
        return ok("upload", selector=args.selector, files=args.file_path)
    return with_page(args, fn)


def cmd_download(args):
    def fn(page, ctx):
        with page.expect_download(timeout=30000) as info:
            page.locator(args.selector).first.click()
        info.value.save_as(args.save_path)
        return ok("download", saved_to=args.save_path)
    return with_page(args, fn)


def _clip(s, n):
    s = s or ""
    return s if len(s) <= n else s[:n]


def cmd_text(args):
    def fn(page, ctx):
        if args.selector:
            txt = page.locator(args.selector).first.inner_text(timeout=10000)
        else:
            txt = page.locator("body").inner_text(timeout=10000)
        url, title = _here(page)
        return ok("text", url=url, title=title,
                  text=_clip(txt, args.max), truncated=len(txt or "") > args.max)
    return with_page(args, fn)


def cmd_html(args):
    def fn(page, ctx):
        if args.selector:
            h = page.locator(args.selector).first.inner_html(timeout=10000)
        else:
            h = page.content()
        return ok("html", html=_clip(h, args.max), truncated=len(h or "") > args.max)
    return with_page(args, fn)


def cmd_links(args):
    def fn(page, ctx):
        links = page.evaluate(JS_LINKS, args.max)
        url, title = _here(page)
        return ok("links", url=url, title=title, count=len(links), links=links)
    return with_page(args, fn)


def cmd_buttons(args):
    def fn(page, ctx):
        b = page.evaluate(JS_BUTTONS, args.max)
        url, title = _here(page)
        return ok("buttons", url=url, title=title, count=len(b), buttons=b)
    return with_page(args, fn)


def cmd_inputs(args):
    def fn(page, ctx):
        i = page.evaluate(JS_INPUTS, args.max)
        url, title = _here(page)
        return ok("inputs", url=url, title=title, count=len(i), inputs=i)
    return with_page(args, fn)


def cmd_forms(args):
    def fn(page, ctx):
        f = page.evaluate(JS_FORMS)
        url, title = _here(page)
        return ok("forms", url=url, title=title, count=len(f), forms=f)
    return with_page(args, fn)


def cmd_tables(args):
    def fn(page, ctx):
        t = page.evaluate(JS_TABLES, args.max)
        return ok("tables", count=len(t), tables=t)
    return with_page(args, fn)


def cmd_images(args):
    def fn(page, ctx):
        im = page.evaluate(JS_IMAGES, args.max)
        return ok("images", count=len(im), images=im)
    return with_page(args, fn)


def cmd_extract(args):
    def fn(page, ctx):
        fields = json.loads(args.fields_json)
        out = {}
        for field, selector in fields.items():
            try:
                out[field] = page.locator(selector).first.inner_text(timeout=5000).strip()
            except Exception:
                out[field] = None
        url, title = _here(page)
        return ok("extract", url=url, title=title, data=out)
    return with_page(args, fn)


def cmd_eval(args):
    def fn(page, ctx):
        result = page.evaluate(args.expression)
        return ok("eval", result=result)
    return with_page(args, fn)


def cmd_info(args):
    def fn(page, ctx):
        url, title = _here(page)
        return ok("info", url=url, title=title)
    return with_page(args, fn)


def cmd_wait(args):
    def fn(page, ctx):
        page.wait_for_timeout(int(args.seconds * 1000))
        return ok("wait", seconds=args.seconds)
    return with_page(args, fn)


def cmd_wait_for(args):
    def fn(page, ctx):
        page.wait_for_selector(args.selector, timeout=args.timeout)
        return ok("wait-for", selector=args.selector, found=True)
    return with_page(args, fn)


def cmd_wait_text(args):
    def fn(page, ctx):
        page.get_by_text(args.text).first.wait_for(timeout=args.timeout)
        return ok("wait-text", text=args.text, found=True)
    return with_page(args, fn)


def cmd_wait_idle(args):
    def fn(page, ctx):
        page.wait_for_load_state("networkidle", timeout=args.timeout)
        return ok("wait-idle", idle=True)
    return with_page(args, fn)


def cmd_cookies(args):
    def fn(page, ctx):
        cookies = ctx.cookies()
        # Never leak values — return names/domains only, redact the value.
        safe = [{"name": c.get("name"), "domain": c.get("domain"),
                 "path": c.get("path"), "value": "<redacted>"} for c in cookies]
        return ok("cookies", count=len(safe), cookies=safe,
                  note="values redacted; use `eval` if you truly need a specific one")
    return with_page(args, fn)


def cmd_local_storage(args):
    def fn(page, ctx):
        data = page.evaluate(JS_STORAGE, "local")
        return ok("local-storage", count=len(data), storage=data)
    return with_page(args, fn)


def cmd_session_storage(args):
    def fn(page, ctx):
        data = page.evaluate(JS_STORAGE, "session")
        return ok("session-storage", count=len(data), storage=data)
    return with_page(args, fn)


def cmd_screenshot(args):
    def fn(page, ctx):
        if args.selector:
            page.locator(args.selector).first.screenshot(path=args.save_path)
        else:
            page.screenshot(path=args.save_path, full_page=args.full_page)
        return ok("screenshot", saved_to=args.save_path)
    return with_page(args, fn)


def cmd_pdf(args):
    def fn(page, ctx):
        page.pdf(path=args.save_path)
        return ok("pdf", saved_to=args.save_path)
    return with_page(args, fn)


# ---------------------------------------------------------------------------
# Argument parsing.
# ---------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        description="Token-efficient Chromium automation (no MCP). One JSON object per command.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def add(name, fn, tab=True):
        sp = sub.add_parser(name)
        if tab:
            sp.add_argument("--tab", type=int, default=None,
                            help="operate on tab N (default: last active)")
        sp.set_defaults(func=fn)
        return sp

    s = add("start", cmd_start, tab=False)
    s.add_argument("--headless", action="store_true")
    s.add_argument("--port", type=int, default=None)
    add("stop", cmd_stop, tab=False)
    add("status", cmd_status, tab=False)

    s = add("goto", cmd_goto)
    s.add_argument("url")
    s.add_argument("--new-tab", action="store_true")
    s.add_argument("--wait", default="domcontentloaded",
                   choices=["load", "domcontentloaded", "networkidle", "commit"])

    s = add("search", cmd_search)
    s.add_argument("query")
    s.add_argument("--engine", default="google", choices=["google", "bing", "duckduckgo"])
    s.add_argument("--max", type=int, default=10)

    add("back", cmd_back)
    add("forward", cmd_forward)
    add("refresh", cmd_refresh)

    add("tabs", cmd_tabs)
    s = add("new-tab", cmd_new_tab)
    s.add_argument("url", nargs="?", default=None)
    s = add("switch-tab", cmd_switch_tab)
    s.add_argument("index", type=int)
    s = add("close-tab", cmd_close_tab)
    s.add_argument("index", type=int)

    s = add("click", cmd_click)
    s.add_argument("selector")
    s.add_argument("--index", type=int, default=0)

    s = add("type", cmd_type)
    s.add_argument("selector")
    s.add_argument("text")
    s.add_argument("--enter", action="store_true")
    s.add_argument("--delay", type=int, default=30)

    s = add("fill", cmd_fill)
    s.add_argument("selector")
    s.add_argument("text")

    s = add("press", cmd_press)
    s.add_argument("key")
    s.add_argument("selector", nargs="?", default=None)

    s = add("select", cmd_select)
    s.add_argument("selector")
    s.add_argument("value")

    for nm, fn in (("check", cmd_check), ("uncheck", cmd_uncheck), ("hover", cmd_hover)):
        s = add(nm, fn)
        s.add_argument("selector")

    s = add("scroll", cmd_scroll)
    s.add_argument("direction", choices=["up", "down", "top", "bottom"])
    s.add_argument("pixels", type=int, nargs="?", default=800)

    s = add("submit", cmd_submit)
    s.add_argument("selector")

    s = add("upload", cmd_upload)
    s.add_argument("selector")
    s.add_argument("file_path", nargs="+")

    s = add("download", cmd_download)
    s.add_argument("selector")
    s.add_argument("save_path")

    s = add("text", cmd_text)
    s.add_argument("selector", nargs="?", default=None)
    s.add_argument("--max", type=int, default=4000)

    s = add("html", cmd_html)
    s.add_argument("selector", nargs="?", default=None)
    s.add_argument("--max", type=int, default=6000)

    for nm, fn in (("links", cmd_links), ("buttons", cmd_buttons),
                   ("inputs", cmd_inputs), ("images", cmd_images)):
        s = add(nm, fn)
        s.add_argument("--max", type=int, default=50)

    add("forms", cmd_forms)

    s = add("tables", cmd_tables)
    s.add_argument("--max", type=int, default=5)

    s = add("extract", cmd_extract)
    s.add_argument("fields_json")

    s = add("eval", cmd_eval)
    s.add_argument("expression")

    add("info", cmd_info)

    s = add("wait", cmd_wait)
    s.add_argument("seconds", type=float)

    s = add("wait-for", cmd_wait_for)
    s.add_argument("selector")
    s.add_argument("--timeout", type=int, default=15000)

    s = add("wait-text", cmd_wait_text)
    s.add_argument("text")
    s.add_argument("--timeout", type=int, default=15000)

    s = add("wait-idle", cmd_wait_idle)
    s.add_argument("--timeout", type=int, default=15000)

    add("cookies", cmd_cookies)
    add("local-storage", cmd_local_storage)
    add("session-storage", cmd_session_storage)

    s = add("screenshot", cmd_screenshot)
    s.add_argument("save_path")
    s.add_argument("selector", nargs="?", default=None)
    s.add_argument("--full-page", action="store_true")

    s = add("pdf", cmd_pdf)
    s.add_argument("save_path")

    return p


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except ModuleNotFoundError:
        fail(args.command, "Playwright not installed. Run: pip install playwright "
                           "&& python -m playwright install chromium")
        sys.exit(3)
    except SystemExit:
        raise
    except Exception as e:
        # Last-resort guard — still emit parseable JSON.
        fail(getattr(args, "command", "?"), e)
        sys.exit(1)


if __name__ == "__main__":
    main()
