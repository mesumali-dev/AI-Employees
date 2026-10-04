#!/usr/bin/env python3
"""
send_batch.py — Daily send path. The agent runs THIS, sees ~one line per
email, and stays out of the MCP entirely.

Flow:
  1. Load the send queue (drafts the agent already wrote + reviewed).
  2. Build the configured provider backend once (see backends/).
  3. Send each email in order, waiting >=15s between sends so the batch
     looks human and stays under provider rate limits.
  4. After each success, mark that lead Sent + stamp a Follow-up Date by
     delegating to lead_status.py (reuses the safe single-row CSV logic).
  5. Print a concise per-lead result and a final summary — nothing
     verbose, so the agent's context barely moves.

Queue format (JSON array), typically written next to draft.md as
draft_queue.json by the drafting step:
  [
    {
      "to": "info@example.com",
      "subject": "…",
      "body": "…full body incl. signature…",
      "label": "Acme Real Estate",     # for readable output (optional)
      "csv_file": "…/leads-jul.csv",   # for the CSV update (optional)
      "csv_row": 58                      # 0-based data row (optional)
    },
    …
  ]
If csv_file/csv_row are omitted, the email is still sent but the CSV is
left untouched (a warning is printed).

As a fallback, if no queue file is given/found, the script parses the
Markdown draft.md (To/Subject/body per section) — send-only, no CSV
updates, since draft.md carries no row mapping.

Usage:
  python scripts/send_batch.py --queue draft_queue.json
  python scripts/send_batch.py --draft draft.md            # fallback parse
  python scripts/send_batch.py --queue q.json --dry-run    # no network, no waits
  python scripts/send_batch.py --queue q.json --delay 45   # custom spacing
  python scripts/send_batch.py --queue q.json --followup-days 4

Flags:
  --delay N          seconds between sends (default 15; min enforced 15
                     unless --dry-run)
  --followup-days N  Follow-up Date = today + N days (default 4)
  --dry-run          show what would be sent; no emails, no delay, no CSV
  --provider NAME    override provider backend (default: auto from config)
  --from ADDRESS     preferred sending mailbox (provider must own it)
"""

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import lead_status

BACKENDS_DIR = os.path.join(SCRIPT_DIR, "backends")

MIN_DELAY = 15  # seconds; the human-pacing / rate-limit floor.


# ---- queue loading -----------------------------------------------------

def load_queue_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Queue JSON must be an array of draft objects.")
    return data


def parse_draft_md(path):
    """Best-effort parse of the human draft.md into send entries.
    Sections look like:
        ## 1. Company Name
        **To:** addr@x.com
        **Subject:** …
        <blank line>
        <body lines…>
    Bodies run until the next '## ' or '---' separator.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()

    entries = []
    # Split on section headings, keep the heading text as label.
    blocks = re.split(r"\n##\s+", text)
    for block in blocks:
        to_m = re.search(r"\*\*To:\*\*\s*(\S+)", block)
        subj_m = re.search(r"\*\*Subject:\*\*\s*(.+)", block)
        if not to_m or not subj_m:
            continue
        label = block.splitlines()[0].strip()
        label = re.sub(r"^\d+\.\s*", "", label)
        # Body = everything after the Subject line, trimmed of trailing
        # '---' separators.
        after = block[subj_m.end():]
        body = after.strip().strip("-").strip()
        entries.append({
            "to": to_m.group(1).strip(),
            "subject": subj_m.group(1).strip(),
            "body": body,
            "label": label,
        })
    return entries


# ---- backend loading ---------------------------------------------------

def _detect_provider():
    """Find the provider by scanning backends/ for a <provider>_backend.py.
    This skill is self-contained around one provider, so there's normally
    exactly one such file. Returns the provider name or None."""
    if not os.path.isdir(BACKENDS_DIR):
        return None
    found = []
    for fn in os.listdir(BACKENDS_DIR):
        if fn.endswith("_backend.py") and fn != "base.py":
            found.append(fn[: -len("_backend.py")])
    if not found:
        return None
    # Prefer hostinger if present (this skill's native provider); else the
    # first one alphabetically for determinism.
    return "hostinger" if "hostinger" in found else sorted(found)[0]


def load_backend(provider=None, from_address=None):
    """Import the generated backend module and build an instance.
    If provider isn't given, discover it from whichever <provider>_backend.py
    exists in backends/."""
    if provider is None:
        provider = _detect_provider()
    if provider is None:
        raise RuntimeError(
            "No backend found in scripts/backends/. Generate one with the "
            "email-mcp-adapter-generator skill, then retry."
        )

    mod_name = f"backends.{provider}_backend"
    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError:
        raise RuntimeError(
            f"No backend module '{mod_name}'. Generate it with the "
            f"email-mcp-adapter-generator skill first."
        )
    if not hasattr(mod, "build"):
        raise RuntimeError(f"{mod_name} has no build() factory.")
    kwargs = {}
    if from_address:
        kwargs["from_address"] = from_address
    return mod.build(**kwargs)


# ---- CSV update (delegated to lead_status.py) --------------------------

def mark_sent(csv_file, csv_row, followup):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "lead_status.py"),
           "mark-sent", csv_file, "--row", str(csv_row),
           "--followup", followup]
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = (res.stdout or "").strip()
    return res.returncode == 0, out or (res.stderr or "").strip()


# ---- main --------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--queue")
    ap.add_argument("--draft")
    ap.add_argument("--delay", type=int, default=MIN_DELAY)
    ap.add_argument("--followup-days", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--provider")
    ap.add_argument("--from", dest="from_address")
    ap.add_argument("--limit", type=int, default=None, help="maximum number of emails to send")
    args = ap.parse_args()

    # Resolve the queue: explicit --queue, else --draft, else look for
    # a draft_queue.json / draft.md in the current directory.
    entries = None
    have_rows = True
    if args.queue:
        entries = load_queue_json(args.queue)
    elif args.draft:
        entries = parse_draft_md(args.draft)
        have_rows = False
    else:
        for cand in ("draft_queue.json",):
            if os.path.isfile(cand):
                entries = load_queue_json(cand)
                break
        if entries is None and os.path.isfile("draft.md"):
            entries = parse_draft_md("draft.md")
            have_rows = False

    if not entries:
        print("FAILED: no drafts found. Pass --queue <json> or --draft <md>.")
        sys.exit(1)

    if args.limit and args.limit > 0:
        entries = entries[:args.limit]

    delay = args.delay if args.dry_run else max(args.delay, MIN_DELAY)
    followup = (date.today() + timedelta(days=args.followup_days)).isoformat()

    mode = "DRY RUN — nothing will be sent" if args.dry_run else "SENDING"
    print(f"{mode}: {len(entries)} email(s), {delay}s between sends, "
          f"follow-up {followup}")

    backend = None
    if not args.dry_run:
        try:
            backend = load_backend(args.provider, args.from_address)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED: backend setup — {e}")
            sys.exit(1)
        print(f"Provider: {backend.provider}  From: {backend.from_address}")

    sent = failed = csv_updated = 0
    errors = []

    for i, e in enumerate(entries, 1):
        label = e.get("label") or e.get("to", "?")
        to = e.get("to")
        subject = e.get("subject")
        body = e.get("body")
        n = f"[{i}/{len(entries)}]"

        if not (to and subject and body):
            failed += 1
            errors.append(f"{label}: missing to/subject/body")
            print(f"{n} FAILED {label} — missing to/subject/body")
            continue

        if args.dry_run:
            print(f"{n} WOULD SEND  {label} <{to}>  subj: {subject[:50]}")
            continue

        if e.get("csv_file") and e.get("csv_row") is not None:
            try:
                _, csv_rows = lead_status.read_rows(e["csv_file"])
                if e["csv_row"] < len(csv_rows) and csv_rows[e["csv_row"]].get(lead_status.STATUS_COL) == lead_status.SENT_STATUS:
                    print(f"{n} SKIP  {label} <{to}> — already marked Sent in CSV")
                    continue
            except Exception:
                pass

        result = backend.send(to, subject, body,
                              display_name="Syed Mesum Ali Shah")
        if not result.ok:
            failed += 1
            errors.append(f"{label}: {result.reason}")
            print(f"{n} FAILED {label} <{to}> — {result.reason}")
        else:
            sent += 1
            csv_note = ""
            if e.get("csv_file") and e.get("csv_row") is not None:
                ok, msg = mark_sent(e["csv_file"], e["csv_row"], followup)
                if ok:
                    csv_updated += 1
                    csv_note = " [CSV: Sent]"
                else:
                    csv_note = f" [CSV update failed: {msg}]"
                    errors.append(f"{label}: sent but CSV not updated ({msg})")
            elif have_rows:
                csv_note = " [no csv row — CSV not updated]"
            print(f"{n} OK     {label} <{to}>{csv_note}")

        # Space out sends so the batch looks human and stays under rate
        # limits — a fixed wait after every email except the last.
        if i < len(entries):
            print(f"       …waiting {delay}s before next email", flush=True)
            time.sleep(delay)

    print("\n--- Summary ---")
    print(f"Sent:        {sent}")
    print(f"Failed:      {failed}")
    print(f"CSV updated: {csv_updated}")
    if errors:
        print("Errors:")
        for msg in errors:
            print(f"  - {msg}")
    if args.dry_run:
        print("(dry run — no emails sent, no CSV changes)")

    sys.exit(1 if failed and not args.dry_run else 0)


if __name__ == "__main__":
    main()
