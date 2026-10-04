---
name: whatsapp-message-drafter
description: Reads leads from the lead CSV database (the nested date-organized CSV tree produced by the lead-hunter-playwright skill), filters eligible leads with valid phone numbers, generates highly personalized, mobile-optimized WhatsApp outreach messages, writes them to whatsapp_drafts.md and whatsapp_queue.json at the project root for review, and sets the lead's WhatsApp Status to "Draft" in the CSV database. Strictly responsible for drafting only; does not send messages. Trigger this skill whenever the user asks to draft WhatsApp messages, write WhatsApp outreach drafts, create WhatsApp messages for leads, or asks something like "draft 10 WhatsApp messages from my lead list" or "prepare WhatsApp drafts for today's new leads." Always use this skill for requests that combine the lead CSV with WhatsApp message drafting.
---

# WhatsApp Message Drafter — Lead Scanning & Message Drafting

Reads eligible leads from the lead CSV database (`outputs/leads/`), crafts highly personalized, mobile-optimized WhatsApp cold outreach messages based on real website audit findings, writes human-readable drafts with one-click `wa.me` preview links to `whatsapp_drafts.md`, outputs machine-readable records to `whatsapp_queue.json`, and stamps `WhatsApp Status` as `Draft` in the CSV.

**Strict Scope Notice:** This skill is strictly responsible for **drafting only**. It does NOT send messages, trigger browser automation, or dispatch outreach. Sending and dispatching are handled independently by a separate, dedicated sending skill.

---

## Core Rules & Constraints

1. **Strictly Drafting Only:** Under no circumstances should this skill attempt to open WhatsApp Web, send messages, or automate dispatches. Its execution ends once drafts are written and the CSV status is updated to `Draft`.
2. **Eligibility Criteria:** Only draft messages for leads that meet both conditions:
   - `WhatsApp Status` is `"New"` or blank (`""`).
   - A valid phone number exists (clean E.164 format findable).
   - If `WhatsApp Status` is already `Draft`, `Sent`, `Qualified`, `Not Found`, or `No Phone`, **skip it**.
3. **No Phone Handling:** If a lead has no phone number, do not generate a draft; mark its `WhatsApp Status` as `No Phone` in the CSV so it is not repeatedly evaluated.
4. **Draft Outputs Required Every Run:**
   - **`whatsapp_drafts.md`** at the project root: Human-readable markdown document containing metadata, business context, direct one-click `wa.me` chat links, and formatted message previews.
   - **`whatsapp_queue.json`** at the project root: Clean JSON array of drafted messages and CSV coordinates for downstream sending tools.
5. **Atomic CSV Status Update:** On creating a draft, immediately update `WhatsApp Status` to `Draft` using `scripts/whatsapp_status.py mark-drafted`. Never touch audit scores, company facts, or other non-tracking columns.
6. **One Draft Per Lead:** Never generate multiple drafts for the same lead.

---

## Inputs & Configuration

Before drafting, identify:
1. **Batch Size / Limit (`N`):** How many drafts to generate this run (default: 10–25, or user-specified).
2. **Base Leads Directory:** Default `outputs/leads/` (resolves to e.g. `outputs/leads/2026/leads-<mon>.csv`).
3. **Sender Persona:**
   - **Name & Organization:** `Syed Mesum Ali Shah | Cortech Solution`
   - **Email:** `mesum@cortechsolution.com`

---

## Workflow

### Step 1: Scan Eligible Leads
Run `whatsapp_status.py` to fetch eligible leads:
```bash
python scripts/whatsapp_status.py list-eligible outputs/leads --limit <N>
```
This inspects the consolidated monthly lead CSVs, identifies leads where `WhatsApp Status` is `"New"` (or empty) and `Phone` is populated, and outputs a JSON list containing lead details, `_file`, `_row`, and normalized `clean_phone`.

If no leads are eligible, report that all current leads in the database have already been drafted or contacted, and exit.

---

### Step 2: Personalize WhatsApp Messages
Adhere strictly to `references/whatsapp_style_guide.md`. For each eligible lead:

1. **Re-verify row eligibility:**
   ```bash
   python scripts/whatsapp_status.py is-eligible <_file> --row <_row>
   ```
2. **Craft Personalized Message:**
   - **Greeting:** `Hi [First Name],` (if Decision Maker is named) or `Hi [Company Name] team,`.
   - **Context & Anchor:** Mention their city, sector, or standout rating/reputation.
   - **1 Specific Technical Friction:** Isolate the single biggest defect from `Problems Found` (e.g. HTTP/No SSL warning, outdated template, missing booking system, slow mobile load).
   - **Clear Value Proposition:** *"We build fast, custom [solution] for [Industry], so you [concrete business benefit]."*
   - **Frictionless CTA:** *"Let me know if you'd like me to send over a quick preview of how this works."*
   - **Mandatory Signature:**
     ```text
     Best regards,

     Syed Mesum Ali Shah
     Cortech Solution
     mesum@cortechsolution.com
     ```
3. **Format Phone Number:** Clean into international E.164 digits (e.g. `+971 58 103 7571` -> `971581037571`).
4. **Generate Direct Click-to-Chat Link:**
   `https://wa.me/<clean_phone>?text=<urlencoded_message>`

---

### Step 3: Write `whatsapp_drafts.md` & `whatsapp_queue.json`

1. **Write `whatsapp_drafts.md`** at the project root with:
   - Header with run date, total leads drafted, and sender details.
   - Per lead section:
     - Company Name, Decision Maker, Phone, Location & Industry, Website link.
     - One-click `[👉 Open Chat & Send Pre-filled Message](https://wa.me/...)` link.
     - Formatted message code block.
2. **Write `whatsapp_queue.json`** at the project root:
   ```json
   [
     {
       "row": 0,
       "csv_file": "outputs/leads/2026/leads-<mon>.csv",
       "company": "Company Name",
       "phone": "971501234567",
       "clean_phone": "971501234567",
       "country": "United Arab Emirates",
       "city": "Dubai",
       "industry": "Real Estate Agency",
       "status": "draft",
       "message": "Hi First Name,\n\n..."
     }
   ]
   ```

---

### Step 4: Update CSV Status to "Draft"
For each successfully drafted lead, mark the CSV row:
```bash
python scripts/whatsapp_status.py mark-drafted <_file> --row <_row>
```
This updates only `WhatsApp Status` to `Draft`, ensuring the lead is not drafted again in subsequent runs.

---

### Step 5: Report Drafts Summary

Conclude execution with a clean, concise summary:
- **Total Leads Evaluated:**
- **Eligible Leads Found:**
- **Drafts Successfully Generated:**
- **CSV Records Marked as `Draft`:**
- **File Outputs:**
  - Review Document: `whatsapp_drafts.md`
  - Machine Queue: `whatsapp_queue.json`
- **Next Steps:** Inform the user that drafts are ready for review and queued for the dedicated sending skill whenever they are ready.
