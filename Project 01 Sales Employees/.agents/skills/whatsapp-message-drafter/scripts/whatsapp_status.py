#!/usr/bin/env python3
"""
whatsapp_status.py — Eligibility scanning + atomic single-row updates for the
whatsapp-message-drafter skill. Operates on the consolidated lead CSV database:
    <base_dir>/<YYYY>/leads-<mon>.csv

Usage:
  python whatsapp_status.py list-eligible <base_dir> [--limit N]
      Scans every leads-*.csv under <base_dir>, finds rows where
      WhatsApp Status is "New" (or empty) AND a valid Phone exists.
      Prints a JSON array of eligible leads, each with all CSV columns
      plus "_file", "_row" (0-based data row index), and "clean_phone".

  python whatsapp_status.py is-eligible <csv_file> --row N
      Re-checks if a single row is still eligible before drafting/sending.
      Prints ELIGIBLE (exit 0) or NOT_ELIGIBLE (exit 1).

  python whatsapp_status.py mark-drafted <csv_file> --row N
      Updates WhatsApp Status to "Draft".

  python whatsapp_status.py mark-sent <csv_file> --row N [--date YYYY-MM-DD] [--followup YYYY-MM-DD]
      Updates WhatsApp Status to "Sent", sets Date Contacted (default today),
      and Follow-up Date (default today + 4 days).

  python whatsapp_status.py mark-not-found <csv_file> --row N
      Updates WhatsApp Status to "Not Found" (phone checked on WhatsApp Web
      and verified not registered).

  python whatsapp_status.py mark-no-phone <csv_file> --row N
      Updates WhatsApp Status to "No Phone".

  python whatsapp_status.py mark-qualified <csv_file> --row N [--response "..."]
      Updates WhatsApp Status to "Qualified" and records incoming response.
"""

import csv
import glob
import json
import os
import re
import sys
from datetime import date, timedelta

STATUS_COL = "WhatsApp Status"
LEAD_STATUS_COL = "Lead Status"
DATE_COL = "Date Contacted"
FOLLOWUP_COL = "Follow-up Date"
RESPONSE_COL = "Response"
PHONE_COL = "Phone"
COUNTRY_COL = "Country"

ELIGIBLE_STATUSES = {"", "New"}
TERMINAL_STATUSES = {"Sent", "Qualified", "Not Found", "No Phone"}


def clean_phone_number(raw_phone, country=""):
    """Normalizes phone number to international E.164 digits without symbols."""
    if not raw_phone:
        return ""
    import urllib.parse
    raw_unquoted = urllib.parse.unquote(str(raw_phone)).strip()
    digits = re.sub(r"\D", "", raw_unquoted)
    if not digits:
        return ""

    country_lower = (country or "").lower()

    # Reject toll-free numbers (not WhatsApp viable)
    if digits.startswith(("1800", "1300", "1888", "800", "888", "877", "866", "855", "844", "833")) and len(digits) in (10, 11):
        return ""
    if digits.startswith("13") and len(digits) == 6:
        return ""

    # Australia (+61)
    if "australia" in country_lower:
        if digits.startswith("61") and len(digits) in (11, 12):
            return digits
        if digits.startswith("0") and len(digits) == 10:
            return "61" + digits[1:]
        if len(digits) == 9 and digits.startswith(("4", "2", "3", "7", "8")):
            return "61" + digits
        return ""

    # UAE (+971)
    if "uae" in country_lower or "emirates" in country_lower or "dubai" in country_lower:
        if digits.startswith("971"):
            return digits
        if digits.startswith("05"):
            return "971" + digits[1:]
        if digits.startswith(("4", "2", "6")):
            return "971" + digits
        return "971" + digits

    # US / Canada (+1)
    if "canada" in country_lower or "usa" in country_lower or "united states" in country_lower:
        if len(digits) == 10:
            return "1" + digits
        if len(digits) == 11 and digits.startswith("1"):
            return digits

    # General fallback
    if len(digits) >= 10:
        return digits

    return ""


def all_dated_csvs(base_dir):
    return sorted(glob.glob(os.path.join(base_dir, "**", "leads-*.csv"), recursive=True))


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
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
    status = (row.get(STATUS_COL) or "").strip()
    phone = (row.get(PHONE_COL) or "").strip()
    clean = clean_phone_number(phone, row.get(COUNTRY_COL, ""))

    if not phone or not clean:
        return False
    if status not in ELIGIBLE_STATUSES:
        return False
    lead_status = (row.get(LEAD_STATUS_COL) or "").strip().lower()
    if "declined" in lead_status or "do not contact" in lead_status or "blocked" in lead_status or "in discussion" in lead_status:
        return False
    response = (row.get(RESPONSE_COL) or "").strip().lower()
    if "replied" in response or "proposal" in response:
        return False
    return True


def list_eligible(base_dir, limit=None):
    results = []
    for path in all_dated_csvs(base_dir):
        fieldnames, rows = read_rows(path)
        if PHONE_COL not in fieldnames:
            continue

        for idx, row in enumerate(rows):
            if is_row_eligible(row):
                lead = dict(row)
                lead["_file"] = os.path.abspath(path)
                lead["_row"] = idx
                lead["clean_phone"] = clean_phone_number(
                    row.get(PHONE_COL, ""), row.get(COUNTRY_COL, "")
                )
                results.append(lead)
                if limit and len(results) >= limit:
                    return results
    return results


def update_row_field(csv_path, row_idx, updates):
    fieldnames, rows = read_rows(csv_path)
    if row_idx < 0 or row_idx >= len(rows):
        print(f"ERROR: row index {row_idx} out of range (0..{len(rows)-1})")
        sys.exit(1)

    # Ensure updated keys exist in fieldnames
    for key in updates.keys():
        if key not in fieldnames:
            fieldnames.append(key)

    for key, val in updates.items():
        rows[row_idx][key] = val

    write_rows(csv_path, fieldnames, rows)
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list-eligible":
        if len(sys.argv) < 3:
            print("Usage: whatsapp_status.py list-eligible <base_dir> [--limit N]")
            sys.exit(1)
        base_dir = sys.argv[2]
        limit = None
        if "--limit" in sys.argv:
            try:
                l_idx = sys.argv.index("--limit")
                limit = int(sys.argv[l_idx + 1])
            except Exception:
                pass
        eligible = list_eligible(base_dir, limit=limit)
        print(json.dumps(eligible, indent=2))
        return

    if cmd == "is-eligible":
        if len(sys.argv) < 5 or sys.argv[3] != "--row":
            print("Usage: whatsapp_status.py is-eligible <csv_file> --row N")
            sys.exit(1)
        csv_file = sys.argv[2]
        row_idx = int(sys.argv[4])
        _, rows = read_rows(csv_file)
        if 0 <= row_idx < len(rows) and is_row_eligible(rows[row_idx]):
            print("ELIGIBLE")
            sys.exit(0)
        else:
            print("NOT_ELIGIBLE")
            sys.exit(1)

    if cmd == "mark-drafted":
        if len(sys.argv) < 5 or sys.argv[3] != "--row":
            print("Usage: whatsapp_status.py mark-drafted <csv_file> --row N")
            sys.exit(1)
        csv_file = sys.argv[2]
        row_idx = int(sys.argv[4])
        update_row_field(csv_file, row_idx, {STATUS_COL: "Draft"})
        print(f"ROW_{row_idx}_MARKED_DRAFT")
        return

    if cmd == "mark-sent":
        if len(sys.argv) < 5 or sys.argv[3] != "--row":
            print("Usage: whatsapp_status.py mark-sent <csv_file> --row N [--date YYYY-MM-DD] [--followup YYYY-MM-DD]")
            sys.exit(1)
        csv_file = sys.argv[2]
        row_idx = int(sys.argv[4])
        
        today_str = date.today().isoformat()
        contact_date = today_str
        followup_date = (date.today() + timedelta(days=4)).isoformat()

        if "--date" in sys.argv:
            d_idx = sys.argv.index("--date")
            contact_date = sys.argv[d_idx + 1]
        if "--followup" in sys.argv:
            f_idx = sys.argv.index("--followup")
            followup_date = sys.argv[f_idx + 1]

        update_row_field(csv_file, row_idx, {
            STATUS_COL: "Sent",
            DATE_COL: contact_date,
            FOLLOWUP_COL: followup_date,
        })
        print(f"ROW_{row_idx}_MARKED_SENT")
        return

    if cmd == "mark-not-found":
        if len(sys.argv) < 5 or sys.argv[3] != "--row":
            print("Usage: whatsapp_status.py mark-not-found <csv_file> --row N")
            sys.exit(1)
        csv_file = sys.argv[2]
        row_idx = int(sys.argv[4])
        update_row_field(csv_file, row_idx, {STATUS_COL: "Not Found"})
        print(f"ROW_{row_idx}_MARKED_NOT_FOUND")
        return

    if cmd == "mark-no-phone":
        if len(sys.argv) < 5 or sys.argv[3] != "--row":
            print("Usage: whatsapp_status.py mark-no-phone <csv_file> --row N")
            sys.exit(1)
        csv_file = sys.argv[2]
        row_idx = int(sys.argv[4])
        update_row_field(csv_file, row_idx, {STATUS_COL: "No Phone"})
        print(f"ROW_{row_idx}_MARKED_NO_PHONE")
        return

    if cmd == "mark-qualified":
        if len(sys.argv) < 5 or sys.argv[3] != "--row":
            print("Usage: whatsapp_status.py mark-qualified <csv_file> --row N [--response '...']")
            sys.exit(1)
        csv_file = sys.argv[2]
        row_idx = int(sys.argv[4])
        updates = {STATUS_COL: "Qualified"}
        if "--response" in sys.argv:
            r_idx = sys.argv.index("--response")
            updates[RESPONSE_COL] = sys.argv[r_idx + 1]
        update_row_field(csv_file, row_idx, updates)
        print(f"ROW_{row_idx}_MARKED_QUALIFIED")
        return

    print(f"Unknown command: {cmd}")
    sys.exit(1)


if __name__ == "__main__":
    main()
