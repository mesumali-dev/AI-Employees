#!/usr/bin/env python3
"""
bulk_csv_updater.py — Atomic single-pass bulk updater for WhatsApp execution results.

CRITICAL PERFORMANCE STRATEGY:
Reads the main leads CSV file ONCE, updates all rows in memory based on the
entire batch execution results, and writes the updated CSV back in a SINGLE
atomic file write. Avoids per-message disk I/O bottlenecks.

Usage:
  python bulk_csv_updater.py --results results.json --csv outputs/leads/2026/leads-sep.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, timedelta


def read_csv(csv_path):
    with open(csv_path, "r", newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def write_csv_atomic(csv_path, fieldnames, rows):
    tmp_path = csv_path + ".tmp"
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, csv_path)


def apply_bulk_results(results, csv_path):
    if not os.path.exists(csv_path):
        print(f"ERROR: Target CSV not found: {csv_path}")
        sys.exit(1)

    fieldnames, rows = read_csv(csv_path)

    # Ensure required tracking columns exist in header
    required_cols = ["WhatsApp Status", "Date Contacted", "Follow-up Date", "Notes"]
    for col in required_cols:
        if col not in fieldnames:
            fieldnames.append(col)

    today_str = date.today().isoformat()
    followup_str = (date.today() + timedelta(days=4)).isoformat()

    counts = {
        "attempted": len(results),
        "sent": 0,
        "not_found": 0,
        "failed": 0
    }

    updated_rows_count = 0

    for item in results:
        status = item.get("status", "").lower()
        row_idx = item.get("row")  # Can be 0-based data row index or 1-based CSV line
        company = (item.get("company") or "").strip().lower()
        phone = (item.get("phone") or "").strip()

        matched_row = None

        # 1. Try matching by 0-based row index directly
        if isinstance(row_idx, int) and 0 <= row_idx < len(rows):
            candidate = rows[row_idx]
            cand_comp = candidate.get("Company Name", "").strip().lower()
            if not company or cand_comp == company:
                matched_row = candidate

        # 2. Try matching by 1-based CSV line number (line 2 = row 0)
        if matched_row is None and isinstance(row_idx, int) and 0 <= (row_idx - 2) < len(rows):
            candidate = rows[row_idx - 2]
            cand_comp = candidate.get("Company Name", "").strip().lower()
            if not company or cand_comp == company:
                matched_row = candidate

        # 3. Fallback: match by company name or phone
        if matched_row is None:
            for r in rows:
                if company and r.get("Company Name", "").strip().lower() == company:
                    matched_row = r
                    break
                if phone and phone in r.get("Phone", ""):
                    matched_row = r
                    break

        if matched_row is None:
            print(f"  [WARN] Could not locate CSV row for: {item.get('company')} ({item.get('phone')})")
            counts["failed"] += 1
            continue

        # Apply in-memory modifications
        if status == "sent":
            matched_row["WhatsApp Status"] = "Sent"
            matched_row["Date Contacted"] = today_str
            matched_row["Follow-up Date"] = followup_str
            counts["sent"] += 1
            updated_rows_count += 1
        elif status in ("not_on_whatsapp", "not_found", "not found"):
            matched_row["WhatsApp Status"] = "Not Found"
            counts["not_found"] += 1
            updated_rows_count += 1
        else:
            counts["failed"] += 1
            err_msg = item.get("error", "Unknown error")
            notes = matched_row.get("Notes", "")
            matched_row["Notes"] = f"{notes} | WhatsApp send failed: {err_msg}".strip(" |")

    # Single atomic write to disk
    write_csv_atomic(csv_path, fieldnames, rows)

    return counts, updated_rows_count


def main():
    parser = argparse.ArgumentParser(description="Bulk CSV Updater for WhatsApp outreach results")
    parser.add_argument("--results", required=True, help="Path to JSON results file or raw JSON string")
    parser.add_argument("--csv", required=True, help="Path to target leads CSV file")
    parser.add_argument("--report", default="whatsapp_execution_report.md", help="Path to write execution markdown report")

    args = parser.parse_args()

    # Load results
    if os.path.exists(args.results):
        with open(args.results, "r", encoding="utf-8") as f:
            results_data = json.load(f)
    else:
        results_data = json.loads(args.results)

    print(f"Processing {len(results_data)} execution results for {args.csv}...")
    counts, updated_rows = apply_bulk_results(results_data, args.csv)

    print("\n" + "=" * 45)
    print("      WHATSAPP BULK SYNC SUMMARY")
    print("=" * 45)
    print(f"Total Attempted:     {counts['attempted']}")
    print(f"Successfully Sent:   {counts['sent']}")
    print(f"Not Found (No WA):   {counts['not_found']}")
    print(f"Failed / Retried:    {counts['failed']}")
    print(f"Total Rows Updated:  {updated_rows}")
    print("=" * 45)

    # Generate markdown summary
    report_content = f"""# WhatsApp Execution Summary Report
**Run Date:** {date.today().isoformat()}  
**Target Database:** `{args.csv}`  

---
### Metrics
- **Total Attempted:** {counts['attempted']}
- **Successfully Sent:** {counts['sent']}
- **Not Found (Not on WhatsApp):** {counts['not_found']}
- **Failed / Stalled:** {counts['failed']}
- **Total CSV Rows Updated:** {updated_rows}
"""
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Execution report saved to: {args.report}")


if __name__ == "__main__":
    main()
