# Playwright MCP Usage Patterns

This skill relies on a connected Playwright MCP server. Tool names below
match the standard Microsoft Playwright MCP server — if the connected
server exposes differently-named tools, use the closest equivalent
(check your tool list) but keep the same sequence of steps.

## 1. Discovery — Finding candidate businesses

### A. Strictly Playwright MCP Only (No web_search or Headless Fallbacks)
Discovery MUST strictly use the **Playwright MCP server**. NEVER use `web_search`, `read_url_content`, curl, or headless scrapers.
1. `browser_navigate` → `https://www.google.com/search?q=<query>`
2. Extract candidate business names + their **official** website URLs only. Never record directory/aggregator pages (Yelp, Yellow Pages, Clutch, Bark, etc.) as the business website — use them only to find the official company domain.

### B. Mandatory Multi-Page Pagination (Pages 1, 2, 3, 4, 5+)
- **NEVER stop after Page 1 or change queries prematurely!**
- Systematically click through **Page 1, Page 2, Page 3, Page 4, Page 5**, etc. using Google's "Next" button (`a#pnnext` or pagination number links) before changing search queries.
- **Why Page 2 & 3 Are Highest Priority:**
  - Page 1 businesses typically already dominate search, have high digital budgets, and retain large marketing agencies.
  - Page 2, 3, and 4 businesses have established revenue and strong trade demand, but obvious commercial bottlenecks: poor SEO visibility, slow WordPress sites, manual spreadsheet quoting, no automated lead qualification, and disconnected CRM pipelines.
  - They have the highest, most urgent need for Cortech Solution services (SEO silos, website redesign, instant quotation systems, CRM, AI automation) and represent our highest-converting prospects.
  - Exhaustively audit candidate businesses across multiple pages for every query.

### C. Google CAPTCHA / Bot Verification Protocol (Graceful Stop & User Handoff)
- If Google (or any site) displays a CAPTCHA, "Our systems have detected unusual traffic...", Cloudflare Turnstile, or bot challenge:
  - **DO NOT** click blindly on puzzle elements or try automated solvers.
  - **DO NOT** switch search engines to DuckDuckGo, Bing, or native `search_web`.
  - **GRACEFULLY STOP IMMEDIATELY** and notify the user in clear English:
    > *"Google has presented a CAPTCHA / verification checkpoint in the browser window. Please solve the CAPTCHA in the open browser, and reply with 'I have solved the CAPTCHA' so I can resume prospecting."*
  - Stop calling tools and wait for the user's confirmation.
  - When the user replies ("I solved it", "done", etc.), inspect the active tab via `browser_evaluate` or `browser_snapshot` to confirm the search results are visible, and resume lead collection and pagination seamlessly.

## 2. Visiting and extracting a business's own site

For each candidate official website:
1. `browser_navigate` to the homepage.
2. `browser_snapshot` to read visible text, headings, nav structure, CTAs,
   footer (copyright year, social links), forms.
3. `browser_evaluate` for structural/technical checks, e.g.:
   - `document.querySelector('meta[name="viewport"]')` → mobile-friendly signal
   - `document.querySelectorAll('meta').length` and check for description/OG tags
   - `location.protocol === 'https:'` → HTTPS check
   - Look for GA/GTM/Meta Pixel script src patterns → analytics presence
   - `document.querySelector('link[rel="manifest"]')`, framework markers in
     `<script>` src attributes (React/Next, Wix, Squarespace, Shopify,
     WordPress wp-content paths, Webflow) → Technology field
4. `browser_network_requests` to eyeball request count/payload/failed
   requests as a rough performance/broken-resource signal.
5. Navigate to `/contact`, `/about`, `/team`, `/leadership` (try common
   paths, or follow nav links found in the snapshot) to extract:
   owner/founder/decision-maker name + title, emails, phone, address,
   social links (Facebook/Instagram/LinkedIn), services list, USP.
   **An email is mandatory** — a lead with no `Business Email` and no
   `Owner Email` is unusable and the append script will reject it, so hunt
   for at least one address before committing to the lead. **Also push hard
   for a named decision-maker + a direct/personal email before accepting a
   generic `info@`** — check the team/leadership/about pages and LinkedIn.
   A named contact is what makes the cold email land. Record the name in
   `Decision Maker`, role in `Position`, personal email in `Owner Email` —
   **never leave decision-maker info only in `Notes`.**
6. If a `tel:` or `mailto:` link is visible in the snapshot, read it
   directly rather than guessing — never fabricate contact details. If a
   piece of contact info genuinely can't be found, leave that CSV cell
   blank (but if NO email at all is findable, drop the candidate).

## 3. Get the consolidated month CSV path (one file per month)

**Choosing `<base_dir>`:** if the user names a leads directory, use it.
Otherwise default to the **current project's own `outputs/leads/`**
directory (`<primary working directory>/outputs/leads/`), NOT a path
outside the project — leads always live inside the project the skill is
invoked from. If the month file already exists there, append to it; if it
doesn't exist yet, `csv_manager.py` creates it with the consolidated
header. Never write leads outside `<project>/outputs/leads/`, and never
hand-construct the path — always get it from `resolve` below.

**All leads, every focus, go into ONE consolidated file per calendar
month** — never a second per-focus file: `<base_dir>/<YYYY>/leads-<mon>.csv`
(e.g. `leads-jul.csv`). Each row keeps its own day in the `Date Added`
column. At the start of the run, resolve the path once (this also creates
the year folder if it doesn't exist):

```
python scripts/csv_manager.py resolve <base_dir>
```

Do NOT pass `--focus` — the consolidated file always uses the website
header. Reuse the printed path for every append this run.

## 4. Dedup check BEFORE deep analysis

To avoid wasting time fully analyzing a business you already have, run a
cheap duplicate check as soon as you know the candidate's name/domain —
before doing the full extraction pass. Use `check-all` (not `check`) so
it's checked against every month's file under the base directory, not
just the current month's:

```
python scripts/csv_manager.py check-all <base_dir> --company "<name>" --website "<url>"
```

Exit code 1 / "DUPLICATE" → skip immediately, log under "Duplicates
Skipped", move to the next candidate. Exit code 0 / "UNIQUE" → proceed
with full analysis.

## 5. Recording the lead

Build a JSON object keyed by the exact CSV column names of the
consolidated file (see `scripts/csv_manager.py`'s `columns_for("website")`
— it's the source of truth), write it to a temp file, then:

```
python scripts/csv_manager.py append <month_csv_path> <lead_json_path> --base-dir <base_dir> --focus website --requested-for "<tag>"
```

Always the consolidated month file and always `--focus website`, whatever
the run's focus. Put the focus's actual selling point in
`Opportunity Type`/`Opportunity Benefit`, and stash any service metric with
no dedicated column (e.g. a chatbot/automation %) in `Notes`.

Pass the same `--requested-for "<tag>"` (the user's own ask for this run,
e.g. "Website"/"Chatbot"/"General") on every append so all rows in the run
share one intent tag.

The `--base-dir` flag makes it re-check for duplicates across every
month's file, in every focus (safe even if something else was appended
concurrently). `--focus` picks the header when the file is being created.
The file's own header is authoritative: any keys in your lead JSON that
aren't columns of that file are silently dropped, so an out-of-focus % on
a website lead never lands. It fills `Date Added` (today, `YYYY-MM-DD`)
and defaults `Lead Status` to `New` if not set, and appends a row —
never overwriting or reordering existing rows, in this file or any other.

## Etiquette / robustness notes

- Add brief waits between navigations if a site is slow (`browser_wait_for`)
  rather than hammering it.
- If a page fails to load or times out, treat it as an invalid site — log
  it under "Invalid Websites Skipped" and move on, don't retry indefinitely.
- Close extra tabs (`browser_tabs`) as you go so the session doesn't
  accumulate dozens of open pages.