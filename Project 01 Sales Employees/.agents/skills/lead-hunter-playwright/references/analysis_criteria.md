# Website Analysis & Scoring Criteria

Use this when analyzing a business website you've navigated to with Playwright.
Gather evidence via `browser_snapshot` (DOM/accessibility tree), `browser_navigate`
to subpages (contact, about), `browser_evaluate` (e.g. check `document.querySelector`
for meta tags, viewport meta, HTTPS via `location.protocol`), and `browser_network_requests`
(look for slow/failed requests, tech fingerprints like WordPress/Shopify/Webflow bundles).

## Scores

Only **`Overall Score` (1–100)** is stored in the CSV — the per-dimension
sub-scores below are no longer columns; assess them mentally to arrive at
the Overall Score, then record just that one number. Keeps the row easy to
scan for outreach.

Judge each dimension (1–10, be honest — most small-business sites are 3–6):

- **Design**: visual polish, modern layout, consistent branding, imagery quality.
- **SEO**: title tags, meta description, heading structure, alt text, sitemap/robots.txt presence.
- **UX**: navigation clarity, CTA visibility/placement, information findability.
- **Accessibility**: alt text coverage, color contrast (approximate from snapshot), semantic HTML, ARIA usage.
- **Performance**: infer from `browser_network_requests` (payload size, number of requests, obvious render-blocking scripts) and any load-time signal you can observe.
- **Trust**: HTTPS present, real contact info, privacy policy/terms links, testimonials/reviews, professional email domain (not gmail/yahoo for a "business" email).

**Overall Score (1–100)**: weight roughly — Design 20%, SEO 15%, UX 20%,
Accessibility 10%, Performance 15%, Trust 20%. Round to nearest integer.
This is the only score column.

## Problems Found — genuine technical defects ONLY

`Problems Found` is an honest audit of what is objectively **wrong or
broken** on the site as it exists today. It is NOT a wish-list of things to
sell. Comma-separated, concise.

**Only real defects belong here:**

No SSL / served over HTTP · Broken Links · Broken Images · Broken/malformed
mailto or tel links · Missing Meta Description / Missing Title · Slow
Website / render-blocking scripts · Console Errors · Poor Mobile Rendering
· Broken Layout · No Analytics installed (no GA/GTM) · Old Copyright Year
(footer vs. current year) · Outdated/Deprecated Tech · Low-contrast /
inaccessible text · any other thing that is actually broken or wrong.

**Never put these in Problems Found** — they are not defects, they're just
services the business hasn't bought, and listing them is dishonest filler:
~~No Chatbot~~ · ~~No CRM~~ · ~~No Customer Portal~~ · ~~No Automation~~ ·
~~No Online Booking~~ · ~~No Live Chat~~ · ~~No AI Features~~. Those are
**opportunities**, not problems → put them in `Opportunity Type` /
`Opportunity Benefit` (below).

If the site is genuinely clean and modern, write "None significant" — do
not manufacture problems. (A clean site can still be a lead via the
opportunity columns, e.g. a great site that would benefit from a booking
system.)

## Opportunity Type & Opportunity Benefit

Two shared columns present in every focus — this is where "what to sell"
lives.

- **`Opportunity Type`** — 1–4 comma-separated tags, strongest first, drawn
  ONLY from the fixed `OPPORTUNITY_TYPES` vocabulary in
  `scripts/csv_manager.py` (Website Redesign · Next.js Rebuild · Performance ·
  Security · SEO · Branding · Mobile Optimization · Lead Capture ·
  Booking System · Analytics · Content/Blog · E-commerce · Online Payments ·
  Customer Portal · CRM · HRM System · Inventory System · Quotation & Invoicing ·
  Custom Software · Automation · AI Chatbot · Web App · Mobile App).
  Need a tag that isn't there? Add it to that list rather than free-typing, so
  the column stays filterable. Base each tag on real evidence (a defect from
  Problems Found, a missing feature, a manual process implied on the site).
- **`Opportunity Benefit`** — ONE specific sentence on what the *client*
  gains, in their terms (more booked jobs, fewer lost after-hours leads,
  clients not scared off by a "Not Secure" warning). Not a description of
  your services, not boilerplate. Tie it to what you actually observed.

Do NOT confuse `Opportunity Type` (what the AI found the site needs) with
`Requested For` (what the USER asked for this run — set once per run from
their wording, e.g. "Website"/"Chatbot", see SKILL.md). They routinely
differ: a `Requested For = Website` run can still surface an
`Opportunity Type` of "Booking System, SEO" for a given site.

## The "% " opportunity-confidence scores — definition & computation

The `* %` columns (`Website Redesign %`, `Security %`, `SEO %`,
`Branding %`, and the chatbot/full equivalents) are **opportunity-
confidence scores, 0–100**: *how strong is the evidence that this business
needs this service and would buy it?* Higher = bigger, clearer gap = hotter
opportunity. They are **not** website quality grades (a great site scores
LOW on redesign need) and **not** severity of a bug.

**Fill every focus score every time** — use `0` when there's genuinely no
signal, so the column is never silently blank. Only leave truly N/A cells
empty. Score from concrete evidence, not a default number.

Rubric per score (anchor points; interpolate):

- **`Security %`** — deterministic from the audit: HTTPS + valid SSL both
  present → **10** (little to sell). Either missing / mixed content / "Not
  Secure" → **85**. Expired/misconfigured cert → **70**.
- **`Website Redesign %`** — from `Overall Score` and design age:
  Overall ≥ 80 → **≤20**; 60–79 → **~50**; < 60 or dated template / old
  copyright / broken layout → **70–90**.
- **`SEO %`** — count concrete SEO gaps (missing title/meta description, no
  headings structure, no sitemap/robots, no analytics, thin content): 0
  gaps → **≤20**; 1–2 → **~50**; 3+ → **70+**.
- **`Branding %`** — inconsistent/weak visual identity, poor typography,
  low-quality imagery, no logo system: strong brand → **≤25**; noticeably
  weak → **60–80**.
- **Chatbot/automation scores** (`AI Chatbot %`, `Automation %`) — volume
  of manual, repetitive customer interaction the site implies (manual quote
  forms, "call us", FAQ-heavy, appointment-based): none → **low**; clearly
  high-volume manual handling → **70+**.

Consistency check: the highest-scoring opportunities should match the tags
in `Opportunity Type`. A ≥60 score is a strong tag; 40–59 is a secondary
tag; below 40, usually don't tag it.

## Lead Qualification

- **Priority** (High / Medium / Low): High = clear, high-confidence
  opportunity + easy-to-find decision-maker contact + business looks
  active and funded (recent reviews/news, real address, healthy review
  count). Low = hard-to-reach, stale, or overqualified (already has strong
  digital presence with no visible gaps).
- **Estimated Budget** (Low / Medium / High / Enterprise): infer from
  business size, industry, and site sophistication — a small local shop is
  Low/Medium; a multi-location chain or funded startup is High/Enterprise.
- **Decision Maker Probability** (High / Medium / Low): High if you found
  a named owner/founder/director with a direct email; Low if only a
  generic `info@` contact form was found.

## Making the lead send-ready (see SKILL.md "Outreach-ready output")

- **An email is mandatory.** No `Business Email` and no `Owner Email` = not
  a usable lead; the `append` script skips it (`NO_EMAIL`). Hunt hard
  (`/contact`, `/about`, `/team`, footer, `mailto:`, LinkedIn) before
  giving up.
- **Put decision-maker info in its own columns.** Any owner/founder/
  director name you find — anywhere, including in reviews or LinkedIn —
  goes in `Decision Maker` + `Position`, and a personal address in
  `Owner Email`. Never bury it in `Notes`. Fall back to `info@` in
  `Business Email` only when nothing personal is findable. Never fabricate.
- **`Cold Email`**: the one client-facing field — a short (~3–5 sentence),
  personalized, ready-to-send email formatted as `Subject: ...\n\n<body>`.
  The sender identity is **Cortech Solution** (`cortechsolution.com` — custom
  software, high-speed Next.js web apps, AI automation, and bespoke business systems,
  with offices in Karachi & Dubai).
  Rules for high deal conversion:
  1. Greet by first name if known ("Hi Alex,"), else "Hi there,".
  2. One specific, undeniable observation about *their* site (e.g. "noticed your mobile product pages take ~4s to load" or "saw you handle project estimates manually via standard web forms").
  3. The business cost / upside: lost leads, dropped checkouts, or wasted quoting hours.
  4. Real proof / Cortech solution: Mention a relevant practical system (e.g. "We recently built custom quotation systems and high-speed Next.js platforms for commercial & engineering clients like AEGI and Al Abbas Solar, cutting quote turnarounds to seconds / making catalogs load instantly").
  5. Soft, low-friction ask for a 10-minute discovery chat.
  6. Sign off as `- [Your Name] | Cortech Solution` (or `- Team Cortech Solution`).
  Keep it human, punchy, and authentic — zero generic spam templates.
- **Leave `Date Contacted`, `Follow-up Date`, `Response` blank** — those
  are the operator's campaign-tracking columns. Set `Lead Status` = `New`.

## Focus-aware runs

Every run has a **focus** (see SKILL.md "Focus & columns"). The focus
decides which columns the CSV carries and which businesses qualify. Only
audit for, and only fill, the focus's own columns — plus the shared
business/contact fields and the pitch.

- **`website` focus (default).** Qualify on the website itself: a business
  is a lead if its site is genuinely weak (low `Overall Score`, real
  `Problems Found`) OR has a clear opportunity (high `Website Redesign %`,
  `SEO %`, `Security %`, or `Branding %`). Fill the website focus columns
  (HTTPS/SSL/Mobile/Speed, `Overall Score`, `Problems Found`, the four
  opportunity scores) plus the shared columns. Don't compute
  CRM/portal/chatbot scores — they aren't columns of this file.
- **`chatbot` focus.** Qualify on the chatbot signal: a lead only if
  `AI Chatbot %` ≥ 60% (with `Automation %` as supporting context). A
  polished, fast site is still a strong chatbot lead if it handles lots of
  customer queries manually with no live chat.
- **A business that doesn't fit the focus is off-target** — skip it and
  count it under "Off-target Skipped". Don't record it under the wrong
  focus just because it's weak in some other way.
- The append script drops any lead-JSON keys outside the file's header, so
  a stray out-of-focus % is harmless — but don't waste audit effort
  gathering data the focus doesn't use.

## Suggested Pitch — internal one-liner

`Suggested Pitch` is a terse **internal** note for the salesperson, NOT
client-facing copy (that's `Cold Email`) and NOT the client benefit
(that's `Opportunity Benefit`). One line: the hook to open with + the lead
offer. e.g. "Open with the 'Not Secure' HTTP flag — urgent, undeniable;
expand to full rebuild + analytics." Keep it specific to what you observed.
`Priority` and this pitch both center on the focus's strongest angle.

## Invalid / Skip Conditions

Skip a candidate (count it under "Invalid Websites Skipped" in the final
report) if:
- The site doesn't load / domain is parked / for sale.
- It's actually a directory, marketplace, or aggregator listing, not the
  business's own site.
- It's a large enterprise clearly already well served digitally (e.g.
  Fortune 500) — unless the user's search was specifically targeting
  enterprise accounts.