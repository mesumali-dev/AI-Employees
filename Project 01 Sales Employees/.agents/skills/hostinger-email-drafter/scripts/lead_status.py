#!/usr/bin/env python3
"""
lead_status.py — Eligibility scanning + safe single-row updates for the
cold-email-drafter skill. Operates on the same nested date-directory CSV
tree produced by the lead-hunter-playwright skill:
    <base_dir>/<YYYY>/<YYYY-MM>/leads-<YYYY-MM-DD>.csv

Usage:
  python lead_status.py list-eligible <base_dir> [--limit N]
      Scans every leads-*.csv nested under <base_dir>, finds rows where
      Lead Status == "New" AND Date Contacted is empty, and prints a JSON
      array of eligible leads (oldest file first), each with every CSV
      column plus "_file" (absolute path to the CSV it lives in) and
      "_row" (0-based index into that file's data rows, for updating).
      If --limit is given, returns at most that many.

  python lead_status.py is-eligible <csv_file> --row N
      Re-checks a single row is still eligible (Lead Status == "New" AND
      Date Contacted empty) right before drafting, to guard against the
      row having changed since list-eligible ran. Prints ELIGIBLE or
      NOT_ELIGIBLE, exit code 0 / 1 respectively.

  python lead_status.py mark-contacted <csv_file> --row N [--date YYYY-MM-DD]
      Updates ONLY that row's Date Contacted (default: today, YYYY-MM-DD)
      and Lead Status (set to "Draft Created") in place. Every other
      column, every other row, and row order are left untouched. Fails
      (prints NOT_ELIGIBLE, exit 1) and makes no changes if the row is no
      longer eligible (already contacted / status changed) — call
      is-eligible first if you need to confirm without risk of a
      double-write race.

  python lead_status.py mark-sent <csv_file> --row N [--followup YYYY-MM-DD]
      Promotes a row that was already drafted (Lead Status "Draft
      Created") to "Sent", and optionally stamps its Follow-up Date. This
      is the second half of the flow: mark-contacted records the draft,
      mark-sent records the actual send. Touches ONLY Lead Status and
      Follow-up Date on that one row. Fails (prints NOT_DRAFTED, exit 1)
      if the row isn't currently "Draft Created" — this guards against
      sending a row that was never drafted or was already sent.

Never call this script to mark a lead contacted before its email draft
has actually been created successfully — draft first, mark second, send
third.
"""

import csv
import glob
import json
import os
import re
import sys
from datetime import date

STATUS_COL = "Lead Status"
DATE_COL = "Date Contacted"
FOLLOWUP_COL = "Follow-up Date"
ELIGIBLE_STATUS = "New"
CONTACTED_STATUS = "Draft Created"
SENT_STATUS = "Sent"

DUMMY_EMAIL_PATTERNS = [
    r"^(wordpress|user|email|info@mysite|example|admin@domain|test|sample)@",
    r"@(example\.com|domain\.com|mysite\.com|test\.com)$",
]


def is_dummy_email(email):
    if not email:
        return True
    email = email.strip().lower()
    return any(re.search(pat, email, re.I) for pat in DUMMY_EMAIL_PATTERNS)


def all_dated_csvs(base_dir):
    return sorted(glob.glob(os.path.join(base_dir, "**", "leads-*.csv"), recursive=True))


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return fieldnames, rows


def write_rows(path, fieldnames, rows):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, path)


def is_row_eligible(row):
    # Must have Lead Status == New and empty Date Contacted
    if row.get(STATUS_COL, "").strip() != ELIGIBLE_STATUS or bool(row.get(DATE_COL, "").strip()):
        return False

    # Check qualification gate fields if present
    if row.get("Opportunity Status", "").strip().lower() == "skipped":
        return False
    if row.get("Email Validation Status", "").strip().lower() == "invalid":
        return False

    conf_str = row.get("Opportunity Confidence", "").strip()
    if conf_str:
        try:
            # Handle percentage sign if present
            conf_val = float(conf_str.rstrip("%"))
            if conf_val < 60:
                return False
        except ValueError:
            pass

    # Reject placeholder/dummy emails
    email = (row.get("Owner Email") or row.get("Business Email") or row.get("Sales Email") or "").strip()
    if email and is_dummy_email(email):
        return False

    return True


def is_row_already_contacted(row):
    status = row.get(STATUS_COL, "").strip()
    return (status in (CONTACTED_STATUS, SENT_STATUS)
            or bool(row.get(DATE_COL, "").strip()))


def list_eligible(base_dir, limit=None):
    results = []
    for path in all_dated_csvs(base_dir):
        fieldnames, rows = read_rows(path)
        if DATE_COL not in fieldnames or STATUS_COL not in fieldnames:
            # File predates the Date Contacted column, or schema mismatch —
            # skip it rather than risk misreading columns.
            continue
        for i, row in enumerate(rows):
            if is_row_eligible(row) and not is_row_already_contacted(row):
                entry = dict(row)
                entry["_file"] = os.path.abspath(path)
                entry["_row"] = i
                results.append(entry)
                if limit and len(results) >= limit:
                    return results
    return results


def mark_contacted(path, row_index, for_date=None):
    fieldnames, rows = read_rows(path)
    if DATE_COL not in fieldnames or STATUS_COL not in fieldnames:
        print("ERROR: CSV missing Date Contacted or Lead Status column")
        sys.exit(2)
    if row_index < 0 or row_index >= len(rows):
        print("ERROR: row index out of range")
        sys.exit(2)

    row = rows[row_index]
    if not is_row_eligible(row) or is_row_already_contacted(row):
        print("NOT_ELIGIBLE")
        sys.exit(1)

    d = for_date or date.today().isoformat()
    row[DATE_COL] = d
    row[STATUS_COL] = CONTACTED_STATUS
    write_rows(path, fieldnames, rows)
    print("UPDATED")


def mark_sent(path, row_index, followup=None):
    fieldnames, rows = read_rows(path)
    if STATUS_COL not in fieldnames:
        print("ERROR: CSV missing Lead Status column")
        sys.exit(2)
    if row_index < 0 or row_index >= len(rows):
        print("ERROR: row index out of range")
        sys.exit(2)

    row = rows[row_index]
    # Only a row that has actually been drafted may be promoted to Sent.
    # This blocks sending something that was never drafted, or double-
    # sending a row that already went out.
    if row.get(STATUS_COL, "").strip() != CONTACTED_STATUS:
        print("NOT_DRAFTED")
        sys.exit(1)

    row[STATUS_COL] = SENT_STATUS
    if followup and FOLLOWUP_COL in fieldnames:
        row[FOLLOWUP_COL] = followup
    write_rows(path, fieldnames, rows)
    print("UPDATED")


def check_eligible(path, row_index):
    fieldnames, rows = read_rows(path)
    if row_index < 0 or row_index >= len(rows):
        print("NOT_ELIGIBLE")
        sys.exit(1)
    row = rows[row_index]
    if is_row_eligible(row) and not is_row_already_contacted(row):
        print("ELIGIBLE")
        sys.exit(0)
    print("NOT_ELIGIBLE")
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)

    cmd, path = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]

    if cmd == "list-eligible":
        limit = None
        it = iter(rest)
        for a in it:
            if a == "--limit":
                limit = int(next(it))
        print(json.dumps(list_eligible(path, limit), indent=2))

    elif cmd == "is-eligible":
        row_index = None
        it = iter(rest)
        for a in it:
            if a == "--row":
                row_index = int(next(it))
        if row_index is None:
            print("ERROR: --row is required")
            sys.exit(2)
        check_eligible(path, row_index)

    elif cmd == "mark-contacted":
        row_index = None
        for_date = None
        it = iter(rest)
        for a in it:
            if a == "--row":
                row_index = int(next(it))
            elif a == "--date":
                for_date = next(it)
        if row_index is None:
            print("ERROR: --row is required")
            sys.exit(2)
        mark_contacted(path, row_index, for_date)

    elif cmd == "mark-sent":
        row_index = None
        followup = None
        it = iter(rest)
        for a in it:
            if a == "--row":
                row_index = int(next(it))
            elif a == "--followup":
                followup = next(it)
        if row_index is None:
            print("ERROR: --row is required")
            sys.exit(2)
        mark_sent(path, row_index, followup)

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()