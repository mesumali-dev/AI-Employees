---
name: hostinger-email-drafter
description: Reads leads from the lead CSV database (the nested date-organized CSV tree produced by the lead-hunter-playwright skill), skips anyone already contacted, generates a highly personalized cold email for each eligible lead, and writes them all to draft.md at the project root for review — never sends without explicit user approval. Only after the user approves does it send them via a token-efficient send script (scripts/send_batch.py) that uses a provider backend (Hostinger today, swappable to Gmail/Outlook). Updates each lead's row (Date Contacted, Lead Status, Follow-up Date only) so it's never contacted twice. Trigger this skill whenever the user asks to draft cold emails, write outreach emails from their leads, create email drafts for prospects, follow up on leads with an email, or asks something like "draft 10 cold emails from my lead list" or "write outreach emails for today's new leads." Always use this skill for any request that combines the lead CSV with email drafting/outreach.
---

# Hostinger Email Drafter — Drafting, Sending & CSV Update

Turns eligible leads from the lead CSV database into personalized cold
emails, writes them all to `draft.md` at the project root for the user to
review, and — only after the user approves — sends them via a
token-efficient send script (`scripts/send_batch.py`), then marks each
lead as contacted. One email per lead, never sent without explicit
approval, never duplicated.

## Hard rules (never violate these)

- **Draft to `draft.md` first, always.** This skill's "draft" step means
  writing every email (recipient + subject + body) to `draft.md` at the
  project root, plus a machine-readable `draft_queue.json` beside it (the
  send script reads that). Never send anything during the drafting step.
- **Never send without explicit approval.** After `draft.md` is written,
  stop and let the user review it. Only send once the user clearly
  approves (e.g. "start the sending", "send them"). If the user only
  asked for drafts, stop after `draft.md` — do not send.
- **Send only via `scripts/send_batch.py`, never by calling the email MCP
  tools directly.** Calling the MCP tool per email floods your context
  with verbose responses. The script sends through a generated provider
  backend and returns one concise line per email, keeping your context
  tiny. This is the whole reason the send path is a script.
- **Never draft or send twice for the same lead.** Only touch leads that
  are currently eligible (see below), and re-verify eligibility
  immediately before drafting.
- **Update the CSV only after the action is confirmed.** A row becomes
  `Draft Created` only once it's in `draft.md`; it becomes `Sent` only
  once the send succeeds (`send_batch.py` handles this itself). If a step
  fails, the CSV is left untouched for that lead.
- **Only modify `Date Contacted`, `Lead Status`, and `Follow-up Date` on
  the matched row.** Never touch any other column, never touch any other
  row, never reorder rows. (All CSV writes go through `lead_status.py`,
  which enforces this.)
- **Buyer-Relevant Value First (Core Objective).** The email must NOT feel
  like a website audit, technical critique, AI pitch, or generic software
  agency outreach. The prospect must understand within a few seconds:
  1. What business process was noticed.
  2. What practical business improvement could be possible.
  3. Why Cortech's solution is relevant.
  4. What simple, low-friction next step they can take.
  Every draft must follow the flow:
  `Personalized Observation -> Business Process -> Potential Commercial Improvement -> Relevant Cortech Solution -> Low-Friction Reason to Reply -> Signature`.
- **Stop Over-Explaining the Problem (Do Not Sell Website Flaws).** Do NOT
  spend most of the email describing website weaknesses. Avoid making missing
  H1s, SEO issues, outdated design, missing chatbots, static contact forms by
  themselves, or technical code quirks the main hook. Only mention an observation
  when it directly supports a concrete operational business workflow. If an
  observation lacks commercial relevance, **SKIP THE LEAD**.
- **Concrete Business Processes.** Prioritize real operational processes:
  - *Hotels:* Direct reservations vs. OTA redirects, booking enquiries, room availability handling, guest communication, housekeeping/staff coordination, check-in/out, multi-property tracking.
  - *Restaurants:* Online ordering, reservation management, order routing & kitchen synchronization, menu/order management, delivery coordination.
  - *Contractors:* Quote intake, job qualification, appointment booking, dispatch, estimate preparation, customer intake, invoicing.
  - *Other:* Real repetitive or high-value business processes visible from their public setup.
- **Easy-to-Understand Commercial Impact.** Do NOT force financial percentages into
  every email. Explain business value in plain language: reducing repetitive admin work,
  letting the existing team handle more enquiries, reducing unnecessary back-and-forth,
  making qualification faster, shortening the path from enquiry to booking, making
  ordering easier, centralizing scattered workflows, reducing manual data entry, or
  increasing capacity without adding administrative headcount.
- **Strict Evidence Boundary (NEVER Invent Internal Problems).** The website shows
  what customers can do; it does NOT prove what happens internally.
  - *Strictly Forbidden as Fact:* "You are losing leads", "Your staff is overwhelmed", "Your team spends 20 hours a week...", "Customers abandon your forms", "Your employees are wasting time...", "Your dispatch desk receives incomplete leads."
  - *Mandatory Conditional Framing:* "If availability enquiries are still being handled manually...", "A centralized reservation workflow could...", "If this currently takes...".
- **Financial Impact Without Fabrication (No Fake ROI).** NEVER invent revenue
  percentages, cost percentages, headcount saved, salary savings, or guaranteed ROI.
  - Structural margins (such as 15%–20% OTA distribution cuts on external booking redirects) are verified industry standards.
  - Hypothetical scenario calculations are permitted ONLY when explicitly framed as hypothetical scenarios.
- **Do Not Automatically Pitch AI.** AI is a solution type, not the selling point.
  Choose from Cortech's full capability suite: custom software, booking/reservation systems,
  ordering tools, CRM/workflow automation, customer portals, quote/estimation systems, ERP,
  inventory, invoicing, custom websites, e-commerce, or business process automation. Only
  mention AI when AI genuinely improves the identified workflow.
- **Sell the Business Result, Not the Technology.** Always lead with the operational
  benefit before introducing the enabling software mechanism.
- **CTA Must Give a Reason to Reply.** Never use lazy, generic CTAs ("Open to a 5-minute demo?",
  "Would you have 10 minutes?", "Can we schedule a call?"). Prefer a useful, low-friction
  next step offering upfront value:
  - "I can send over a simple example of how this could work for your property if useful."
  - "I can map the workflow around your current setup if you'd like to see it."
  - "I can put together a quick example around your current ordering process."
  - "I can show you what this could look like before you decide whether it's worth discussing."
- **High Personalization (Commercial Grounding).** Reference 2–3 genuinely relevant facts:
  business type, location, specific service, operating model, visible booking/order/quote process.
  Do NOT use generic flattery or compliments.
- **Strict Word Count: 80–110 words (hard max 130 words).** Plain text only.
- **Canonical Signature (Mandatory):**
  ```text
  Best regards,

  Syed Mesum Ali Shah
  Cortech Solution
  mesum@cortechsolution.com | cortechsolution.com
  ```
- **The Strong Owner Test.** Before writing any draft, ask:
  *"If I were the owner reading this between other emails, would I immediately understand: what process you noticed, why improving it could matter to my business, what you are offering, and why replying could be worthwhile?"* If NO, rewrite.
- **Do Not Force an Email (Lead Quality Over Quantity).** If the lead lacks a meaningful
  business process, a credible improvement opportunity, sufficient evidence, or a clear
  Cortech solution, **SKIP THE LEAD**.

## Before starting

Confirm (ask only if genuinely unclear from the request):
1. **How many drafts** to create this run (the "daily limit").
2. **Base leads directory** — the same `base_dir` used by
   lead-hunter-playwright, default `outputs/leads/` in the project root.
   Leads live nested under it in dated CSV files (currently one file per
   month, e.g. `<base_dir>/<YYYY>/leads-<mon>.csv` ->
   `.../2026/leads-jul.csv`). The exact filename layout doesn't matter to
   this skill — `list-eligible` globs every `leads-*.csv` under the base
   dir regardless of how they're nested.

Sending is handled entirely by `scripts/send_batch.py`, which talks to a
generated Hostinger backend under `scripts/backends/` — you do NOT call
the email MCP tools yourself. If `scripts/backends/hostinger_backend.py`
and `hostinger_config.json` already exist, you're ready to draft and send.
If they're missing (or a token/account changed), see "Prerequisites"
below before the send step.

### Credentials (.env)

The send script reads `HOSTINGER_API_TOKEN` from a `.env` file at the
**project root**. If it's missing, the script says so — tell the user to
copy `.env.example` to `.env` and fill in their Hostinger token. Never
hardcode the token or read it from anywhere else; `.env` is the single
source of truth (and is gitignored).

### Architecture (why it's split this way)

The email MCP is a thin passthrough over Hostinger's REST API. Making one
verbose MCP call per email would balloon your context, so the send path is
a script that calls REST directly via a pre-generated backend:

- `scripts/backends/` — the send layer. `base.py` is the provider-agnostic
  `EmailBackend` interface; `hostinger_backend.py` implements it (REST
  under the hood); `hostinger_config.json` holds the discovered mailbox
  facts; `env_utils.py` reads the token from `.env`.
- `scripts/send_batch.py` — **run every send**: reads the draft queue,
  sends via the backend with a >=15s gap between emails, updates the CSV,
  and prints one concise line per lead. This is the cheap runtime step.

You (the agent) only ever run `send_batch.py` and read its short output.

### Prerequisites (only when the backend is missing or stale)

The backend files are produced by the separate **email-mcp-adapter-
generator** skill — that's the rare "compile" step, not part of a normal
daily run. If `scripts/backends/hostinger_backend.py` /
`hostinger_config.json` are missing, or the user says their Hostinger
token/account changed, invoke that skill (or run its generator):
```
python ../email-mcp-adapter-generator/scripts/inspect_mcp.py \
    --provider hostinger --target-skill .
```
It reads `HOSTINGER_API_TOKEN` from `.env`, probes the API, and writes the
backend + config into this skill's `scripts/backends/`. Then proceed with
the send step.

## Workflow

Read `references/email_style_guide.md` before writing your first email —
it has the full Buyer-Relevant Value First framework, industry angles,
evidence boundaries, and QA checklists. This is required reading, not optional.

1. **Find eligible leads**:
   ```
   python scripts/lead_status.py list-eligible <base_dir> --limit <N>
   ```
   This scans every dated CSV under `base_dir`, returns leads where
   `Lead Status == "New"` AND `Date Contacted` is empty, oldest file
   first, each tagged with `_file` and `_row` for later updating. Files
   missing the `Date Contacted`/`Lead Status` columns are skipped
   automatically (safe no-op, not an error).

2. For each returned lead, in order:
   a. **Re-verify eligibility** right before drafting (guards against
      anything changing since the scan):
      ```
      python scripts/lead_status.py is-eligible <_file> --row <_row>
      ```
      `NOT_ELIGIBLE` -> skip silently, move to the next lead (don't count
      it as an error — it just means it was already handled).
   b. **Personalize & Qualify (Buyer-Relevant Value First Analysis)**:
      - Read available CSV fields: Company Name, Decision Maker, Contact Quality,
        Email Validation Status, Opportunity Confidence, Primary Opportunity, Evidence,
        Recommended Service, Opportunity Status, Industry, City, Services, USP.
      - **Do Not Force an Email**: If `Opportunity Status == "Skipped"`, `Opportunity Confidence < 60`,
        or if only minor technical issues exist (missing H1, cosmetic styling, minor SEO),
        **SKIP THE LEAD**.
      - **Contact Quality Check**: Pick Owner Email -> Business Email -> Sales Email. Reject
        placeholders/dummies (`wordpress@...`, `user@...`). If invalid, skip.
      - **Structure & Voice (80–110 Words)**:
        * 1. Personalized observation (2–3 concrete trade/location facts).
        * 2. Business process (concrete booking, quote, or ordering flow noticed).
        * 3. Potential commercial/operational improvement (plain language, framed conditionally).
        * 4. Relevant Cortech solution (matched to process, never forcing AI).
        * 5. Low-friction reason to reply (offer workflow map or simple preview, no pushy demo).
        * 6. Canonical signature.
      - **Strict Evidence Boundary**: Never state internal operations as fact. Use "If...", "Could...", "May...".
      - **Zero Fabricated ROI**: No fake staff hours, no invented savings percentages.
      - **The Strong Owner Test**:
        *"If I were the owner reading this between other emails, would I immediately understand: what process was noticed, why improving it matters, what Cortech is offering, and why replying is worthwhile?"* If NO, rewrite or skip.
   c. **Append the draft to `draft.md`** at the project root (create the
      file with a dated heading on the first lead of the run). Record the
      recipient address, subject, and full body. Always end the body with
      this exact canonical signature:

      ```text
      Best regards,

      Syed Mesum Ali Shah
      Cortech Solution
      mesum@cortechsolution.com | cortechsolution.com
      ```

   d. **Also append the same email to `draft_queue.json`** at the project
      root (a JSON array). This is what the send script consumes, and it
      carries the CSV mapping so sends can update the right row:
      ```json
      {
        "to": "<recipient address>",
        "subject": "<subject>",
        "body": "<full body incl. signature>",
        "label": "<Company Name>",
        "csv_file": "<_file>",
        "csv_row": <_row>
      }
      ```
   e. **On draft written**: mark the row —
      ```
      python scripts/lead_status.py mark-contacted <_file> --row <_row>
      ```
      This sets `Date Contacted` to today (`YYYY-MM-DD`) and
      `Lead Status` to `Draft Created`, touching only that row/those two
      columns. If this update itself fails, report the error immediately
      and stop the run rather than continuing.
   f. Count this lead toward the requested total only on a confirmed
      success (written to `draft.md` + `draft_queue.json` AND CSV updated).

3. **Stop exactly at the requested number** of drafts, or when no
   eligible leads remain — whichever comes first. Then present `draft.md`
   and stop. Do not send yet.

4. **Send step — only after the user explicitly approves.** Run the send
   script once; it does everything (send + pacing + CSV updates):
   ```
   python scripts/send_batch.py --queue draft_queue.json
   ```
   The script sends each queued email via the provider backend, waits
   >=15s between sends, and on each success promotes that row to `Sent`
   and stamps a `Follow-up Date` (default today + 4 days; tune with
   `--followup-days N`). It prints one concise line per lead plus a
   summary — surface that summary to the user. You do NOT call the email
   MCP tools or edit the CSV yourself; the script owns both.

   Useful flags: `--dry-run` (preview, no emails/waits/CSV changes),
   `--delay N` (seconds between sends, floor 15), `--from <address>`
   (pick a specific sending mailbox).

5. **Bounce & Mailbox Management (Post-Campaign).**
   After campaign dispatch, inspect the Hostinger mailbox for delivery failures (bounces) to keep the database accurate and the inbox clean:
   - **Inspect INBOX via Hostinger MCP:** Call `email_call_api_read` with `path="/api/v1/mailboxes/{mailboxResourceId}/folders/INBOX/messages"` to list incoming messages.
   - **Identify Bounces vs Real Replies:** Check sender and subject. Keep real prospect replies untouched! Identify automated bounce notifications (e.g. Mail Delivery System `550 User unknown`, `550 5.1.1 Recipient address rejected`, etc.).
   - **Update Lead Status via `scripts/manage_bounces.py`:**
     ```bash
     # Single bounce update:
     python scripts/manage_bounces.py --email "recipient@domain.com" --reason "550 5.1.1 Recipient address rejected"

     # Or audit bounce rates across all leads:
     python scripts/manage_bounces.py --status
     ```
     This safely updates `Lead Status` to `"Bounced"` and appends the failure reason to `Response` across the monthly lead CSVs without touching other columns.
   - **Purge Bounce Notifications:** Call Hostinger MCP `email_call_api_write` with:
     - `path`: `"/api/v1/mailboxes/{mailboxResourceId}/folders/INBOX/messages/delete"`
     - `method`: `"POST"`
     - `body`: `{"messageUids": [<list_of_bounce_uids>]}`
     This permanently deletes the bounce clutter from the Hostinger inbox while preserving all real prospect replies.

## Final report

After the run, report:

- Total Leads Checked
- Eligible Leads (found by `list-eligible`)
- Skipped Leads (broke commercial test, low confidence, minor technical issues, or missing valid contact)
- Drafts Written (to `draft.md`)
- Emails Sent (if the send step ran)
- CSV Rows Updated
- Errors (lead name + reason, if any)
- Remaining Eligible Leads (eligible leads left untouched this run)