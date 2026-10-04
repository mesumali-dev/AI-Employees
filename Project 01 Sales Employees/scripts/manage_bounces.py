#!/usr/bin/env python3
"""
manage_bounces.py — Bounce handling and lead status updater for Cortech Solution outreach.

Features:
  1. Searches the leads database for given bounced email address(es).
  2. Updates matching rows' 'Lead Status' to 'Bounced' and appends error explanation to 'Response'.
  3. Records audit timestamps and summaries of updated leads.
  4. Optionally sends mailbox message purge requests if Hostinger mailbox API access is available.

Usage:
  # Check and update a single bounced email:
  python scripts/manage_bounces.py --email "badaddr@example.com" --reason "User unknown"

  # Process a list of bounced emails from a JSON or text file:
  python scripts/manage_bounces.py --file bounces.json

  # Audit leads database for current bounced count:
  python scripts/manage_bounces.py --status
"""

import argparse
import csv
import glob
import json
import os
import re
import sys
from datetime import datetime

DEFAULT_LEADS_DIR = "outputs/leads"


def find_lead_files(base_dir=DEFAULT_LEADS_DIR):
    pattern = os.path.join(base_dir, "**", "leads-*.csv")
    return glob.glob(pattern, recursive=True)


def update_bounced_lead(csv_path, target_email, bounce_reason="Delivery failure: Mailbox does not exist"):
    target_clean = target_email.strip().lower()
    updated = False
    rows = []
    fieldnames = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            b_email = (row.get("Business Email") or "").strip().lower()
            o_email = (row.get("Owner Email") or "").strip().lower()

            if target_clean in (b_email, o_email):
                row["Lead Status"] = "Bounced"
                existing_resp = row.get("Response", "")
                timestamp = datetime.now().strftime("%Y-%m-%d")
                bounce_note = f"[{timestamp} Bounce] {bounce_reason}"
                row["Response"] = f"{existing_resp}; {bounce_note}".strip("; ")
                updated = True
                print(f"[BOUNCE] Updated: {row.get('Company Name')} ({target_email}) in {os.path.basename(csv_path)}")
            rows.append(row)

    if updated:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return updated


def audit_bounces(base_dir=DEFAULT_LEADS_DIR):
    files = find_lead_files(base_dir)
    total_bounced = 0
    total_sent = 0
    total_leads = 0

    print("=== LEADS BOUNCE & STATUS AUDIT ===")
    for path in sorted(files):
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            file_leads = 0
            file_bounced = 0
            file_sent = 0
            for r in reader:
                file_leads += 1
                status = (r.get("Lead Status") or "").strip().title()
                if status == "Bounced":
                    file_bounced += 1
                elif status == "Sent":
                    file_sent += 1
            print(f"{os.path.basename(path)}: Total={file_leads}, Sent={file_sent}, Bounced={file_bounced}")
            total_leads += file_leads
            total_bounced += file_bounced
            total_sent += file_sent

    print("-" * 35)
    print(f"Overall: Total Leads={total_leads}, Sent={total_sent}, Bounced={total_bounced}")
    if total_sent > 0:
        bounce_rate = (total_bounced / (total_sent + total_bounced)) * 100
        print(f"Bounce Rate: {bounce_rate:.2f}%")


def main():
    parser = argparse.ArgumentParser(description="Manage bounced outreach emails and update CSV leads database.")
    parser.add_argument("--email", help="Single email address that bounced")
    parser.add_argument("--reason", default="Delivery failure: Mailbox does not exist", help="Reason for bounce")
    parser.add_argument("--file", help="JSON file containing array of bounced email addresses or objects with 'email' and 'reason'")
    parser.add_argument("--csv-dir", default=DEFAULT_LEADS_DIR, help="Base directory of lead CSVs")
    parser.add_argument("--status", action="store_true", help="Print status audit across all lead CSVs")

    args = parser.parse_args()

    if args.status:
        audit_bounces(args.csv_dir)
        return

    if args.email:
        files = find_lead_files(args.csv_dir)
        matched = False
        for f in files:
            if update_bounced_lead(f, args.email, args.reason):
                matched = True
        if not matched:
            print(f"[WARN] Email '{args.email}' was not found in any lead CSV.")
        return

    if args.file:
        if not os.path.exists(args.file):
            print(f"File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)

        files = find_lead_files(args.csv_dir)
        for item in data:
            if isinstance(item, str):
                email = item
                reason = "Delivery failure: Mailbox does not exist"
            elif isinstance(item, dict):
                email = item.get("email") or item.get("to")
                reason = item.get("reason", "Delivery failure: Mailbox does not exist")
            else:
                continue

            if email:
                for f in files:
                    update_bounced_lead(f, email, reason)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
