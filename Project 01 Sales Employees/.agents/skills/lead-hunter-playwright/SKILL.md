---
name: lead-hunter-playwright
description: Autonomous B2B lead generation, website audit, and sales-qualification agent for Cortech Solution (cortechsolution.com). Strictly uses Playwright MCP interactive browser as the official engine (never search_web or headless fallbacks) to discover businesses, paginate deeply across search pages (Page 1, 2, 3+) to capture high-priority lower-ranked prospects, gracefully stop for user CAPTCHA solving, inspect live websites on screen, perform technical & UX audits, detect custom software / Next.js / invoice & quotation system / AI automation opportunities, extract verified decision-maker contacts, and append deduplicated leads to the monthly CSV via scripts/csv_manager.py. Trigger this skill whenever the user asks to find leads, hunt prospects, build a lead list or client database, audit business websites, or run B2B sales prospecting.
---

# Lead Hunter & Qualification Agent (Playwright MCP)

Autonomous B2B prospecting and qualification engine for **Cortech Solution** (`cortechsolution.com`). Discovers businesses via Google/web search, inspects their live websites via **Playwright MCP**, identifies high-ticket software & automation gaps, extracts verified decision-maker contact details, and records deduplicated leads into the consolidated monthly CSV.

---

## 1. Operating Philosophy: Interactive Playwright MCP

### A. Mandatory Browsing Engine: Strictly Playwright MCP Only
- **Absolute Rule:** All search discovery, website navigation, visual layout inspections, tech stack auditing, and contact extractions **MUST STRICTLY AND EXCLUSIVELY USE THE PLAYWRIGHT MCP SERVER** (`browser_navigate`, `browser_click`, `browser_type`, `browser_evaluate`, `browser_snapshot`, `browser_tabs`).
- **Strict Prohibition:** NEVER use native `search_web`, `read_url_content`, curl, python urllib/requests, or any headless/silent HTTP fetchers for prospecting or site inspection. The user should NEVER have to remind the agent to "strictly use playwright mcp server" — it is the permanent, mandatory standard for this skill.
- **User Observability:** The browser runs visibly on the user's screen. If Google or Cloudflare presents a CAPTCHA or verification checkpoint, the user can solve it directly in the open browser window while the agent waits.
- **Agent Intelligence:** The agent uses active visual and structural reasoning to navigate subpages (`/about`, `/team`, `/quote`, `/contact`), bypass broken layouts, spot decision makers in leadership photos, and detect subtle operational bottlenecks.
- **No Headless Subprocess Scanners:** All scraping scripts (`lead_scan.py`, etc.) are retired. The agent drives the browser directly via Playwright MCP tools.

### B. Mandatory Multi-Page Search Pagination (Page 1, 2, 3, 4, 5+)
- **Do NOT stop on Page 1 or switch search queries prematurely!**
- When searching for target business niches on Google (or business directories), the agent must systematically paginate through **Page 1, Page 2, Page 3, Page 4, Page 5**, etc. using Google's pagination buttons (`a#pnnext`, clicking "Next", or page number links) before changing search queries.
- **Crucial Commercial Rationale:** Businesses ranking on Page 2 or Page 3 (or lower) are often **HIGHER PRIORITY** prospects for Cortech Solution than top-ranking Page 1 giants!
  - Page 1 companies usually already have dominant SEO, large retained marketing agencies, and bespoke tech setups.
  - Page 2, 3, and 4 companies have high commercial intent and active revenue, but suffer from clear digital bottlenecks: weak SEO rankings, legacy websites, manual quoting, no automated lead qualification, and unintegrated CRM workflows.
  - They have the **greatest, most urgent need** for Cortech's services (Website Redesign, SEO Silos, Next.js migrations, Quoting/Invoicing portals, CRM, and AI automations) and yield far higher conversion rates.
  - Always exhaust pagination across multiple pages for each search query to gather the maximum number of high-opportunity leads efficiently.

### C. Google CAPTCHA & Bot Checkpoint Protocol (Graceful Stop & User Handoff)
- If Google (or any target site) presents a CAPTCHA, "Our systems have detected unusual traffic...", Cloudflare Turnstile, or bot verification challenge:
  - **DO NOT** attempt to click blindly or guess bot puzzles automatically.
  - **DO NOT** switch search engines to DuckDuckGo, Bing, or fall back to native `search_web` tools!
  - **GRACEFULLY STOP IMMEDIATELY** and notify the user in clear, polite English:
    > *"Google has presented a CAPTCHA / verification checkpoint in the browser window. Please solve the CAPTCHA in the open browser, and reply with 'I have solved the CAPTCHA' so I can resume prospecting."*
  - Stop calling tools and wait for the user to respond.
  - When the user replies with *"I solved the CAPTCHA"*, *"i solved it"*, *"done"*, or similar:
    - Use `browser_evaluate` or `browser_snapshot` to confirm the search results page is now active and unobstructed.
    - Immediately continue lead collection, pagination, and audits from the exact point where it was interrupted.

### Token-Efficiency Best Practices
To prevent context bloat while using Playwright MCP:
1. **Prefer `browser_evaluate` over `browser_snapshot` for data extraction:**
   `browser_snapshot` can dump 20–30 KB of accessibility tree into context. Instead, run targeted JavaScript snippets via `browser_evaluate` to extract emails, phone numbers, contact URLs, tech stack markers, and meta tags in a single call.
2. **Use `browser_snapshot` sparingly:**
   Call `browser_snapshot` only when you need to understand the visual layout, read body copy, or find interactable button elements that weren't obvious from DOM evaluation.
3. **Tab Hygiene:**
   Reuse open tabs or close temporary tabs via `browser_tabs` so memory and context remain clean.

---

## 2. Who We Are: Cortech Solution

The operator is **Cortech Solution** (`cortechsolution.com` — Custom Software & Web Development Company with headquarters in Karachi, Pakistan and business operations in Business Bay, Dubai, UAE).

### Core Service Offerings & Proof Points
Always evaluate prospect businesses across the full Cortech portfolio:
1. **Quotation & Invoicing Management Systems / Custom ERP:**
   - *Problem:* Small/mid-sized businesses relying on messy spreadsheets (Excel/Google Sheets), Word templates, or manual emails to generate estimates, calculate solar/equipment costs, and invoice clients.
   - *Cortech Solution:* Bespoke quotation generators with automated line-item cost calculation, dynamic margin controls, instant PDF generation, client e-signatures, and payment gateway integration.
   - *Social Proof:* Built complete quotation, solar calculation, and billing systems for clients like **Al Abbas Electric & Solar** and **AEGI Engineering**.
2. **Next.js Web Applications & E-Commerce:**
   - *Problem:* Outdated, slow WordPress/Wix/Squarespace sites, slow mobile loading speeds, poor conversion funnels.
   - *Cortech Solution:* High-performance, modern Next.js/React web platforms with sub-second page loads, custom checkout flows, and headless CMS.
   - *Social Proof:* E-commerce and corporate platforms for **Ruqaiya Collection** and **AEGI Engineering**.
3. **Custom Business Software & CRM/HRM Portals:**
   - *Problem:* Disjointed operational tools, manual data re-entry across departments, lack of client visibility.
   - *Cortech Solution:* Integrated internal dashboards, custom CRMs, inventory tracking, employee performance management, and role-based client portals.
4. **AI Assistants & Automations:**
   - *Problem:* Lost after-hours leads, slow customer support response, repetitive manual data handling.
   - *Cortech Solution:* 24/7 intelligent AI chatbots (WhatsApp & Web) trained on company documents, coupled with webhook automations to sync inquiries directly into CRM/email.

---

## 3. Storage Architecture: Single Consolidated CSV

**All leads, regardless of focus or industry, accumulate in ONE consolidated file per calendar month:**
`<base_dir>/<YYYY>/leads-<mon>.csv` (e.g. `outputs/leads/2026/leads-sep.csv`).

### Rules
1. **Default Location:** Always use `<primary working directory>/outputs/leads/`.
2. **Never Create Per-Focus Files:** No `leads-solar.csv`, `leads-chatbot.csv`, etc.
3. **Resolution & Append via `scripts/csv_manager.py`:**
   ```bash
   # 1. Resolve path to current month's consolidated CSV
   python scripts/csv_manager.py resolve outputs/leads

   # 2. Check global deduplication across all months before deep auditing
   python scripts/csv_manager.py check-all outputs/leads --company "Company Name" --website "https://example.com"

   # 3. Append qualified lead JSON
   python scripts/csv_manager.py append <csv_path> <lead_json_path> --base-dir outputs/leads --focus website --requested-for "<Campaign Intent>"
   ```

---

## 4. Upgraded 8-Stage Lead Qualification & Audit Workflow

The goal is **NOT** to find a problem for every business. The goal is to find businesses where there is a **credible, observable opportunity** for Cortech Solution, and skip the rest. **Lead quality > lead quantity.**

```mermaid
flowchart TD
    A[Discovery / Search] --> B[Stage 1: Business Fit Gate]
    B -- Fail Fit --> S1[SKIP: Off-Market / Low Fit]
    B -- Pass --> C[Stage 2: Contact Quality Gate]
    C -- Dummy / Invalid / Missing --> S2[SKIP: Invalid or Missing Contact]
    C -- Pass --> D[Stage 3: Website & Workflow Research]
    D --> E[Stage 4: Opportunity Detection by Priority]
    E -- No Strong Opportunity --> S3[SKIP: No Meaningful Opportunity]
    E -- Found --> F[Stage 5: Cortech Service Matching]
    F --> G[Stage 6: Opportunity Confidence Scoring 0-100]
    G -- Score < 60 --> S4[SKIP: Low Confidence < 60]
    G -- Score >= 60 --> H[Stage 7: 1-Opportunity Email Generation]
    H --> I[Stage 8: Final 6-Point QA Gate]
    I -- QA Failed --> J{Can Rewrite Cleanly?}
    J -- No --> S5[SKIP: QA Unresolvable]
    J -- Yes --> K[Append to Monthly CSV via csv_manager.py]
    I -- QA Passed --> K
```

---

### The 8 Stages in Detail

#### Stage 1: Business Fit
Determine whether the company is a realistic Cortech prospect before deep-diving:
- **Services & Margin:** Established residential/commercial trade contractors, engineering, solar, or professional services with high-ticket services (e.g. 200A panel upgrades, heat pumps, roof replacements, multi-trade projects).
- **Scale Indicators:** Look for evidence of active operations (service territory, team/fleet photos, physical address, business maturity). Do not treat a solo part-time handyman and a 15-truck multi-location fleet as identical.
- **Digital Maturity & Purchasing Capacity:** Avoid hobbyist sites or abandoned businesses. Target companies established enough to invest in digital infrastructure.
- *If outside target market or unlikely to purchase technology:* **SKIP.**

#### Stage 2: Contact Quality
Never send cold emails to dummy or unverified addresses.
- **Priority Hierarchy:**
  1. *Tier 1:* Verified named decision-maker email (`paul@pchelectrical.ca`).
  2. *Tier 2:* Named employee/owner email (`danh@cascaderoofing.ca`).
  3. *Tier 3:* Specific business role email (`estimates@...`, `sales@...`, `dispatch@...`).
  4. *Tier 4:* Generic mailbox (`info@...`, `contact@...`) used *only* when no better direct contact exists.
- **Strict Prohibition (Dummy & Placeholder Emails):**
  NEVER record or email scraped dummy addresses like `wordpress@yourdomain.com`, `user@domain.com`, `email@email.com`, `info@mysite.com`, or template placeholders.
- *If no valid email or only dummy address found:* **SKIP.**

#### Stage 3: Website & Business Research
Distinguish strictly between three layers of information:
1. **OBSERVED FACT:** Something directly visible or technically verified (e.g., *"homepage uses a static 3-field form"*, *"primary H1 is 'Contact Us'"*, *"no instant quote or booking widget present"*).
2. **POTENTIAL OPPORTUNITY:** A reasonable business use case logically based on observed facts (e.g., *"an interactive price calculator could pre-qualify EV charger and panel upgrade inquiries before reaching your desk"*).
3. **ASSUMPTION:** Something unverified internally (e.g., whether they are missing calls, losing revenue, or drop-off rates). **NEVER present an assumption as an established fact.**

#### Stage 4: Opportunity Detection (Prioritized Order)
Always search for commercial opportunities in this exact order of priority:
1. **Revenue / Lead Capture Opportunities:** High-ticket intake funnels, instant estimate calculators, visual quote intake.
2. **Lead Qualification / Booking Opportunities:** 24/7 emergency dispatch triage, automated calendar booking for inspections.
3. **Customer Communication & Response-Time Opportunities:** After-hours inquiry intake, automated lead routing.
4. **Business Process Automation:** Eliminating manual spreadsheet quoting, automated contract/PDF generation.
5. **Website Conversion Architecture:** Modernizing high-friction multi-field forms, mobile intake optimization.
6. **Custom Software / Web Applications:** Client portals, multi-location job dispatch, custom ERP modules.
7. **Local SEO & Discovery Structure:** Missing geo-targeted service silos, weak municipal targeting.
8. **Minor Technical Issues:** Missing H1 tags, metadata gaps, or template script quirks. *(A missing H1 should almost NEVER be the lead hook if a commercial business opportunity exists).*

#### Stage 5: Cortech Service Matching
Do not ask "what service do I want to sell?" Ask: **"What is the strongest observable opportunity on this site?"**
Map logically to Cortech's core offerings:
- *Lead Capture Systems / Quotation & Invoicing* (for variable-scope trades needing instant pricing)
- *AI Automation / AI Agents / 24/7 Receptionists* (for contractors handling frequent emergency/after-hours calls)
- *Website Redesign / Custom Web Development* (for outdated, slow, or broken conversion layouts)
- *Custom Business Software / CRM / Client Portals* (for complex operational coordination)
- *Local SEO* (for weak municipal search visibility and structural gaps)

#### Stage 6: Opportunity Confidence Scoring (0–100)
Measures how strongly the publicly observable evidence supports the proposed Cortech opportunity:
- **90–100 (Very Strong):** Direct owner email, clear commercial friction observed, strong service fit.
- **75–89 (Strong):** High-ticket contractor, verified gap (static form / lack of quoting tool), clear business use case.
- **60–74 (Possible):** Identifiable opportunity with generic mailbox or minor evidence.
- **Below 60 (Low Confidence):** **SKIP.** Do NOT manufacture an opportunity just to fill a row.

#### Stage 7: Email Generation (Strict Rules)
1. **Length:** **70–110 words** (Maximum 130 words).
2. **One Primary Opportunity:** Focus on **ONE** clear business opportunity. Never dump multiple unrelated issues (e.g. do not combine H1 + contact form + SEO + chatbot).
3. **Factual Personalization:** Reference specific services and cities without generic flattery (avoid *"great to see your expertise"* or *"quality services"*).
   - *Example:* *"I noticed you handle residential panel upgrades and EV charger installations across Oshawa and Durham."*
4. **No Assumed Lost Leads / No Fabricated ROI:**
   - *Forbidden:* *"You are losing leads"*, *"Missing calls"*, *"Costing you revenue"*, *"Will get you 10 more jobs"*, *"Increases conversions by 30%"*.
   - *Allowed:* Factual, conditional phrasing: *"I noticed website inquiries currently go through a standard contact form... an automated intake tool could pre-qualify homeowner inquiries before reaching your team."*
5. **Never Inject Raw Research Notes:** Research notes must be converted into natural human sentences. Never concatenate internal scraping strings into email bodies.
6. **Situational CTA:** Match CTA to reality:
   - *"Would you be open to a quick overview?"*
   - *"Would it be useful if I sent over an example?"*
   - *"Open to seeing how this could work for [Company]?"*
   - Only mention a demo if an actual interactive demo/preview is prepared.
7. **Signature:** Fixed founder format:
   ```
   Best regards,

   Syed Mesum Ali Shah
   Cortech Solution
   mesum@cortechsolution.com | cortechsolution.com
   ```

#### Stage 8: Final 6-Point QA Gate
Before appending or queueing any lead, verify:
1. **Factual Check:** Is every claim directly verified on their live site?
2. **Relevance Check:** Does the recommended Cortech service genuinely solve the problem?
3. **Personalization Check:** Does it contain specific local/trade facts? Could it be sent unchanged to another company? (If yes, rewrite).
4. **Natural Language Check:** Does it sound human? Are internal scraping notes completely absent?
5. **Sales Quality Check:** Exactly one primary opportunity? Low-friction CTA? Zero fabricated ROI claims?
6. **Contact Verification:** Is the email plausible and non-placeholder? Is the recipient name accurate?
*If any critical check fails and cannot be cleanly rewritten: **SKIP THE LEAD.***

---

## 5. Structured Lead Output (Internal Representation)

Before appending to CSV, the agent formats each lead internally:
```yaml
Company: "PCH Electrical Contractors"
Website: "https://www.pchelectrical.ca/"
Business Type: "Home Services (Electrical Contracting)"
Location: "Oshawa, Ontario"
Decision Maker: "Paul"
Recipient Email: "paul@pchelectrical.ca"
Contact Quality: "Verified Named Decision Maker"
Email Validation Status: "Valid Domain / Syntax"
Key Business Facts: "Residential master electrician specializing in 200A service panel upgrades and EV chargers across Durham Region."
Primary Observed Opportunity: "Absence of interactive intake calculator for high-ticket panel and EV charger estimates."
Evidence: "Homepage contact relies solely on static 3-field form without preliminary pricing or electrical load scoping."
Recommended Cortech Service: "Lead Capture Systems / Instant Estimator"
Opportunity Confidence: 88
Reason for Confidence: "Direct owner contact, high-ticket technical trade, clear conversion bottleneck on homepage."
Email Angle: "Interactive EV charger & panel upgrade quoting calculator to pre-qualify homeowner requests."
Opportunity Status: "Qualified"
Email QA Status: "Passed"
```

---

## 6. Appending Leads to CSV

Save lead details to a JSON object matching the consolidated schema, then execute:
```bash
python scripts/csv_manager.py append <csv_path> <temp_lead.json> --base-dir outputs/leads --focus website --requested-for "<tag>"
```

### Upgraded Consolidated Schema Fields (60 Columns)
- `Common Firmographics:` `Date Added`, `Requested For`, `Company Name`, `Industry`, `Country`, `State`, `City`, `Business Size`, `Website`, `Website Status`, `Technology`
- `Technical Audit Facts:` `HTTPS`, `SSL`, `Mobile Friendly`, `Loading Speed`, `Overall Score`, `Problems Found`
- `Category Fit Scores:` `Website Redesign %`, `Security %`, `SEO %`, `Branding %`, `AI Chatbot %`, `Automation %`
- `Contact Details:` `Decision Maker`, `Position`, `Business Email`, `Owner Email`, `Phone`, `Address`, `Google Rating`, `Reviews`, `Facebook`, `Instagram`, `LinkedIn`, `Services`, `USP`, `Suggested Pitch`, `Cold Email`
- `Sales Pipeline Tracking:` `Priority`, `Estimated Budget`, `Decision Maker Probability`, `Lead Status`, `WhatsApp Status`, `Date Contacted`, `Follow-up Date`, `Response`, `Notes`, `Source`, `Contact Page`
- `New Structured Qualification Columns:`
  - `Contact Quality`: `Verified Named Decision Maker`, `Named Employee/Owner`, `Business Role`, `Generic Mailbox`
  - `Email Validation Status`: `Valid Domain / Syntax`, `Placeholder Skipped`, `Invalid Domain`
  - `Opportunity Confidence`: Integer `0–100` (must be ≥60 to append)
  - `Primary Opportunity`: Single primary commercial opportunity
  - `Evidence`: Directly observed website fact supporting the opportunity
  - `Recommended Service`: Exact Cortech service capability
  - `Opportunity Status`: `Qualified`, `Skipped`, `Pending QA`
  - `Skip Reason`: Concrete reason if skipped during search
  - `Email QA Status`: `Passed`, `Failed`

---

## 7. Run Completion & Quality Reporting

Upon completing a prospecting run, present a transparent audit report:
- **Campaign Intent (`Requested For`):** Target industry or capability
- **Total Websites Inspected:** Raw domains navigated via Playwright
- **Disqualified / Skipped Breakdown:**
  - *Business Fit Skips:* Outside target market, low commercial scale
  - *Contact Skips:* Missing email, dummy/placeholder email (`wordpress@...`, `user@...`)
  - *Opportunity Skips:* No meaningful opportunity observed
  - *Low Confidence Skips:* Scored below 60 on Opportunity Confidence
  - *QA Skips:* Failed final factual or language verification
- **Qualified Leads Appended:** Net high-conviction leads added to CSV
- **Confidence Distribution:** Average Opportunity Confidence of appended batch
- **Top Leads Showcase:** Detailed inspection of top 3 leads showing observed facts, recommended service, and send-ready cold email.