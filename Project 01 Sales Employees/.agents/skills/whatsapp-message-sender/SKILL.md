---
name: whatsapp-message-sender
description: Sends approved WhatsApp outreach drafts from whatsapp_drafts.md and whatsapp_queue.json via Playwright MCP server to WhatsApp Web, applies human-like pacing delays (3-6s), handles un-registered numbers and UI popups gracefully, categorizes outcomes (Sent, Not Found, Failed), and updates the main leads CSV database in a single atomic bulk write at the end of the run. Trigger this skill whenever the user asks to send WhatsApp messages, dispatch WhatsApp drafts, start sending WhatsApp outreach, blast queued WhatsApp messages, execute the WhatsApp send queue, or asks something like "send the approved WhatsApp messages" or "start sending WhatsApp drafts."
---

# WhatsApp Message Sender — Playwright MCP Dispatcher & Bulk Synchronizer

Automates the sequential sending of approved WhatsApp outreach messages from `whatsapp_queue.json` (or `whatsapp_drafts.md`) to WhatsApp Web using the Playwright MCP server. Incorporates human-like typing and pacing delays, resilient state handling for un-registered phone numbers, and a **high-speed single-pass atomic bulk CSV update** strategy at the end of the batch.

---

## Architecture & Core Principles

```
  ┌────────────────────────────────────────────────────────┐
  │ 1. Read Approved Queue (whatsapp_queue.json)            │
  │    Filter leads with WhatsApp Status == "Draft"        │
  └─────────────────────────┬──────────────────────────────┘
                            │
                            ▼
  ┌────────────────────────────────────────────────────────┐
  │ 2. Sequential Browser Dispatch (Playwright MCP)        │
  │    - Look up phone in dialer pad                       │
  │    - Handle "Invalid number" popups gracefully         │
  │    - Fill & send message with 3-6s human pacing        │
  │    - Accumulate results IN-MEMORY (no per-lead I/O)    │
  └─────────────────────────┬──────────────────────────────┘
                            │
                            ▼
  ┌────────────────────────────────────────────────────────┐
  │ 3. Single Atomic Bulk Update (leads-<mon>.csv)         │
  │    - One file read, in-memory updates, one file write  │
  │    - Bulk update WhatsApp Status: Sent / Not Found     │
  │    - Stamp Date Contacted & Follow-up Date             │
  │    - Generate Execution Markdown Summary Report        │
  └────────────────────────────────────────────────────────┘
```

### Critical Rules (Never Violate These)

1. **Strictly Single-Pass CSV Bulk Updates:** **NEVER read or write to the leads CSV after every single message send.** Per-message file I/O causes massive execution latency and file lock risks. Always collect results in an in-memory array and run `scripts/bulk_csv_updater.py` ONCE at the end of the queue run.
2. **Pacing & Anti-Ban Delays:** Maintain a **3–6 second delay** between sends. Rapid-fire automated messaging triggers WhatsApp rate limits, temporary account flags, or UI stalls.
3. **Resilient Popup Handling:** Always check for and dismiss the *"Phone number shared via url is invalid"* popup when a number is not registered on WhatsApp. Dismiss it with the OK button, reset the drawer, and categorize the contact as `Not Found`.
4. **Three Strict Outcome Categories:**
   - **`Sent`**: Successfully delivered to the prospect.
   - **`Not Found`**: Number verified not registered on WhatsApp.
   - **`Failed`**: UI timeout, disconnect, or unhandled exception.

---

## Execution Workflow

### Step 1: Inspect Queue & Target Leads
Verify that `whatsapp_queue.json` exists and inspect the pending drafts:
```bash
python scripts/whatsapp_batch_sender.py --queue whatsapp_queue.json --dry-run
```
Only leads with `WhatsApp Status == "Draft"` (or in the queue without terminal status) are processed.

---

### Step 2: Generate the Playwright Batch Runner
Generate the optimized batch dispatch script for the queue:
```bash
python scripts/whatsapp_batch_sender.py --queue whatsapp_queue.json --batch-size 25 --output-js scripts/whatsapp_batch_runner.js
```
This produces a specialized asynchronous JavaScript function that executes inside the active browser page.

---

### Step 3: Dispatch via Playwright MCP Server
Execute the batch script in WhatsApp Web using the Playwright MCP tool:
1. Ensure the browser is on `https://web.whatsapp.com/` and logged in.
2. Call `call_mcp_tool` with:
   - `ServerName`: `"playwright"`
   - `ToolName`: `"browser_run_code_unsafe"`
   - `Arguments`: `{ "code": "<contents of scripts/whatsapp_batch_runner.js>" }`
3. The script iterates sequentially through each contact, applying:
   - Phone dialer lookup and active chat detection.
   - Realistic typing pauses and 4-second delivery checkmark waits.
   - Safe anti-ban delays (3–6 seconds).
   - Clean UI state recovery on errors.
4. Save the returned results array to `batch_results.json`.

---

### Step 4: Single Atomic Bulk CSV Update
Once the batch runner completes, update the leads database in one single atomic operation:
```bash
python scripts/whatsapp_batch_sender.py --apply-results batch_results.json --csv "outputs/leads/2026/leads-<mon>.csv"
```
Or directly via the bulk updater:
```bash
python scripts/bulk_csv_updater.py --results batch_results.json --csv "outputs/leads/2026/leads-<mon>.csv" --report "whatsapp_execution_report.md"
```

This single-pass script:
- Reads the monthly CSV once into memory.
- Maps each result to its target row.
- Sets `WhatsApp Status` = `"Sent"`, `Date Contacted` = today (`YYYY-MM-DD`), and `Follow-up Date` = today + 4 days for delivered leads.
- Sets `WhatsApp Status` = `"Not Found"` for non-registered numbers.
- Writes the modified data back via atomic replace (`.tmp` file).

---

## Output Report

Generate and present the final campaign execution summary:
- **Total Leads Attempted:**
- **Successfully Delivered & Sent:**
- **Not Found (Not on WhatsApp):**
- **Failed / Stalled (Available for Retry):**
- **CSV Database File Updated:** `outputs/leads/2026/leads-<mon>.csv`
- **Execution Log:** `whatsapp_execution_report.md`
