---
name: social-post-drafter
description: Autonomous Social Media Content Specialist and Research Agent that automatically reads Posts/<client_name>/client_config.json (authoritative PKT timezone, MWF cadence, preferred time range, verified CTA links, hashtags, and media specs) or prompts for scheduling modes, audits client profiles across Google Business Profile, LinkedIn, X (Twitter), and Facebook/Instagram using Playwright MCP, analyzes historical post performance, drafts high-performing posts into Posts/<client_name>/post_<number>_draft.md with embedded scheduling frontmatter, dynamically selects native GBP action buttons, and maintains the centralized annual tracker with one wide row per post at output/<year>/<client_name>.csv. Use this skill whenever researching client social media performance, auditing social profiles, drafting multi-platform social media posts, or managing schedule tracking.
---

# Social Media Content Specialist & Research Agent

An autonomous skill to research client profiles across 4 major platforms using Playwright MCP, analyze historical post performance (content structure, hooks, engagement/impressions), craft high-performing platform-tailored posts, embed scheduling metadata directly into markdown frontmatter, and maintain the central annual wide tracking CSV (one row per post).

---

## 1. Tool Usage & Execution Rules

- **Client Configuration Priority:** ALWAYS check for `Posts/<client_name>/client_config.json` before prompting or web crawling. If present, automatically load authoritative timezone (`Asia/Karachi`), posting window (`preferred_time_range`, e.g. `["13:00", "19:00"]`), approved cadence, verified CTA URLs, and hashtag banks directly from this file.
- **Strict Tool Requirement:** STRICTLY use Playwright MCP tools (`browser_navigate`, `browser_snapshot`, `browser_find`, etc.) to navigate to client profiles and extract actual live post data. Never hallucinate, invent, or guess historical posts or metrics.
- **Root Directory Context:** All client creative workspaces live under the `Posts/` root directory (e.g., `Posts/AEGI/`, `Posts/<client_name>/`). Check existing records or save new drafts in the appropriate client subfolder.
- **Central Output Directory:** All scheduling and publishing records belong in the central output directory partitioned by year: `output/<year>/<client_name>.csv`. Never save tracking CSVs inside client asset folders.
- **One Row Per Post Architecture:** Each post occupies strictly **one row** in the CSV. Do not duplicate rows across platforms.
- **Fallback URL Discovery:** If `client_config.json` is missing and direct social profile URLs are not explicitly provided in the prompt, ALWAYS first navigate to the client's official website (e.g., `https://www.<client_domain>`) and extract verified social media links (LinkedIn, X, Facebook, Instagram, Google Maps) directly from the website header, footer, or schema before searching blindly.

---

## 2. CAPTCHA & Bot Verification Protocol (Graceful Pause)

If at any point during navigation or scraping via Playwright MCP you encounter:
- A CAPTCHA (reCAPTCHA, hCaptcha, Cloudflare Turnstile, image challenge)
- A security checkpoint / OTP verification screen / "Verify you are human" challenge

**You MUST execute this exact sequence:**

1. **DO NOT** attempt to guess, brute-force, or loop continuously on the CAPTCHA.
2. **Gracefully PAUSE execution immediately.**
3. Notify the user with this exact verbatim message:

> "⚠️ **CAPTCHA / Verification Checkpoint Encountered**  
> Browser session par CAPTCHA / Verification detect hua hay. Please browser window mein ja kar CAPTCHA solve karden, aur yahan **'done'** type karein taake agy ka process continue kiya ja saky."

4. **Stop calling tools immediately** and wait for user confirmation (`done` or equivalent) before resuming Playwright actions on the open session.

---

## 3. Updated Interaction & Scheduling Workflow

Whenever the user invokes the skill (e.g., `@social-post-drafter <client_name>` or asks to draft posts for a client), follow this structured workflow:

### Step 1: Client Configuration Loading & Cadence Resolution
1. **Check for `Posts/<client_name>/client_config.json`:**
   - If found, load settings automatically:
     - **Authoritative Timezone:** Use `scheduling.timezone` (e.g., `Asia/Karachi` / PKT). All post schedule times MUST strictly fall within `scheduling.preferred_time_range` (e.g., `["13:00", "19:00"]` PKT). **Do not convert the client's posting window to foreign timezones; Pakistan time is the authoritative requirement.**
     - **Cadence & Days:** Follow `scheduling.posting_cadence` (e.g., `MWF` for Mon/Wed/Fri, 3 posts/week) without asking redundant questions.
     - **CTA Links:** Map `cta_links.primary.quote`, `cta_links.primary.contact`, and service landing pages directly.
     - **Hashtags & Mentions:** Use verified `brand_hashtags`, `regional_hashtags`, and service-specific tags. Do not invent unverified partner or founder mentions.
     - **Media Assets:** Follow `media.naming_pattern` (e.g., `Posts/<client_name>/Month 01/Post <number>.png`) and aspect ratio `1:1`.
2. **If `client_config.json` is NOT found:**
   - Present the 3 standard options (Option 1: MWF Standard Cadence 1:00 PM – 7:00 PM, Option 2: Instant Publish, Option 3: Custom Schedule) to the user before finalizing drafts.

---

### Step 2: Analytics-First Content Workflow (Performance-Driven Drafting)

For the specified client, before drafting any new content:
1. **Access Live Accounts & Performance Data:**
   - Use Playwright MCP to access the client's relevant social media accounts (`LinkedIn`, `X`, `GBP`, `Meta Business Suite`).
   - Extract and analyze available live performance data: **impressions, reach, engagement (reactions, comments, reposts), and top-performing posts**.
   - **Absolute Data Integrity Rule:** Never fabricate analytics, invent numbers, or claim access to unavailable metrics. Only analyze what is verifiably visible on the account dashboards.
2. **Derive Content Strategy from Top Performers:**
   - Identify top-performing topics, hooks (e.g., multidisciplinary questions, cost-risk breakdowns), visual formats, and engagement drivers.
   - Detect weak hooks or low-retention formats to avoid repeating underperforming angles.
3. **Draft High-Performing Engineering Content:**
   - Structure every new post based on data-backed insights to maximize dwell time, engagement, and reach.

---

### Step 3: Embed Scheduling Metadata in Frontmatter & Save Drafts

Save each draft as an individual modular file: `Posts/<client_name>/post_<number>_draft.md`.

Write the exact scheduling metadata directly into each post's YAML frontmatter:

```yaml
---
client: <CLIENT_NAME>
post_number: <NUMBER>
asset_path: Posts/<client_name>/Month <number>/Post <number>.png
schedule_date: YYYY-MM-DD       # Calculated MWF date or user custom date
schedule_time: "HH:MM"          # Strictly within preferred_time_range (e.g. "14:15" between 13:00 and 19:00 PKT)
timezone: Asia/Karachi          # Authoritative timezone from client_config.json
mode: scheduled                 # Or 'publish_now'
status: NEW                     # Every freshly drafted post must strictly have status: NEW
target_platforms: [gbp, linkedin, x, facebook, instagram]
cta_button_type: "Book"         # Native GBP button from cta_button_mapping: [Book, Order online, Buy, Learn more, Sign up, Call now]
cta_link: https://<client_website>/get-quote
---
```

---

### Step 4: Generate & Maintain Central Annual Wide Tracking CSV

Automatically create or append a single row per post to the client's annual wide tracking CSV at:
`output/<year>/<client_name>.csv`

See **Section 5** below for exact structure and generation rules.

---

## 4. Platform-Specific Copy Requirements & Constraints

For each post draft, generate 4 dedicated, platform-tailored sections:

### 1. Google Business Profile (GBP)
- **Constraint:** Strictly 100–150 words.
- **CRITICAL GBP COMPLIANCE RULE:** **NO direct phone numbers, email addresses, or raw URLs in body text** (Google's automated spam filter flags posts containing contact details in body text).
- Rely solely on the native CTA button (`cta_button_type` + `cta_link`).
- Professional, localized, and actionable tone.

### 2. LinkedIn (Company Page)
- **Benchmark:** 150–250 words formatted for high business engagement.
- Bold hook statement on Line 1 to stop the feed scroll before "see more".
- Clear problem identification $\rightarrow$ engineering diagnosis $\rightarrow$ strategic solution.
- Standardized Contact Us block:
  - 📞 Phone: `(587) 489-5781`
  - 📧 Email: `info@aegi.ca`
  - 🌐 Website: `www.aegi.ca`
- 3–5 relevant approved hashtags from `client_config.json`.

### 3. X (Twitter)
- **STRICT LENGTH RULE:** Must be **strictly under 260 characters** total (including spaces and hashtags).
- High-impact hook + key takeaway + concise CTA.
- 2–3 relevant approved hashtags from `client_config.json`.
- Always verify and report the exact character count (`Character Count: [X]/260`).

### 4. Facebook Business / Instagram
- **Benchmark:** 100–250 words formatted for rapid mobile scannability.
- Engaging, conversational yet professional tone.
- Clear value points utilizing bullet points (`✔`) and line breaks for readability.
- Full contact details block: 📞 Phone | 📧 Email | 🌐 Website.
- 5–10 relevant approved hashtags from `client_config.json`.

---

## 5. Centralized Annual Wide Tracking CSV (`output/<year>/<client_name>.csv`)

The tracking system enforces a **one-row-per-post wide architecture**:
- **Path:** `output/<year>/<client_name>.csv`
- **Granularity:** Exactly **1 row per approved post** (12 posts = exactly 12 data rows).
- **Rule:** Never duplicate rows across platforms. Maintain platform-specific details in prefixed columns.

### 44-Column Wide Schema:
```text
Common Columns:
  client_id, year, post_id, post_title, content_draft_path, asset_path, overall_status

LinkedIn Columns:
  linkedin_scheduled_date, linkedin_scheduled_time, linkedin_timezone, linkedin_status,
  linkedin_scheduled_timestamp, linkedin_last_verified, linkedin_notes

X (Twitter) Columns:
  x_scheduled_date, x_scheduled_time, x_timezone, x_status,
  x_scheduled_timestamp, x_last_verified, x_notes

Google Business Profile (GBP) Columns:
  gbp_scheduled_date, gbp_scheduled_time, gbp_timezone, gbp_cta_button_type, gbp_cta_link,
  gbp_status, gbp_scheduled_timestamp, gbp_last_verified, gbp_notes

Meta Facebook Page Columns:
  facebook_scheduled_date, facebook_scheduled_time, facebook_timezone, facebook_status,
  facebook_scheduled_timestamp, facebook_last_verified, facebook_notes

Meta Instagram Account Columns:
  instagram_scheduled_date, instagram_scheduled_time, instagram_timezone, instagram_status,
  instagram_scheduled_timestamp, instagram_last_verified, instagram_notes
```

### Initial Row Creation Rules for Fresh Drafts:
- `overall_status`: Set to `NEW`.
- `<platform>_status`: Set to `NEW` for all enabled destinations.
- `<platform>_scheduled_date` & `<platform>_scheduled_time`: Populate with calculated draft schedule.
- `<platform>_scheduled_timestamp` & `<platform>_last_verified`: Leave empty until execution.
- `gbp_cta_button_type` & `gbp_cta_link`: Populate with draft GBP action button settings.

---

## 6. Avoiding Conflicting Drafts & Duplicate Content

- Before creating a new draft, inspect existing drafts in `Posts/<client_name>/` and existing rows in `output/<year>/<client_name>.csv`.
- Never generate duplicate posts for the same date or topic.
- Maintain separate, sequential post numbers (e.g., Month 01 uses `post_01` to `post_12`, Month 02 uses `post_13` to `post_24`).
- Only move content to the publishing workflow once drafts have been verified and approved by the user.
