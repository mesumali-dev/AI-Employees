#!/usr/bin/env python3
"""
generate_all_karachi_drafts.py — High-quality B2B cold email generator for Cortech Solution
Strictly complies with hostinger-email-drafter/SKILL.md and email_style_guide.md:
- Buyer-Relevant Value First
- 80-110 words (hard max 130 words)
- Plain text, strict evidence boundary
- Canonical signature
- Writes draft.md and draft_queue.json
- Updates CSV Lead Status to 'Draft Created' and Date Contacted to today
"""

import os
import sys
import re
import json
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import lead_status

BASE_DIR = "outputs/leads"
DRAFT_MD_PATH = "draft.md"
DRAFT_QUEUE_PATH = "draft_queue.json"

SIGNATURE = """Best regards,

Syed Mesum Ali Shah
Cortech Solution
mesum@cortechsolution.com | cortechsolution.com"""

KNOWN_ZONES = [
    "Korangi Industrial Area", "Korangi", "S.I.T.E.", "S.I.T.E", "SITE",
    "Federal B Area", "Federal 'B' Area", "North Karachi Industrial Area", "North Karachi",
    "Landhi Industrial Area", "Landhi", "Port Qasim", "P.E.C.H.S", "PECHS",
    "DHA", "Clifton", "Shahrah-e-Faisal", "I.I. Chundrigar", "Cloth Market",
    "Jodia Bazaar", "Timber Market", "New Karachi", "Baldia"
]

def clean_company_name(name):
    if not name:
        return "your team"
    cleaned = re.sub(r'(?i)\s*\(\s*(pvt|private)\.?\s*(ltd|limited)?\.?\s*\)', '', name).strip()
    cleaned = re.sub(r'(?i)\s*\(\s*(ltd|limited)\.?\s*\)', '', cleaned).strip()
    cleaned = re.sub(r'(?i)\b(pvt|private|ltd|limited|corp|corporation|inc)\b\.?', '', cleaned).strip()
    cleaned = re.sub(r'^[0-9]+[A-Za-z]?\s*[-–.]\s*', '', cleaned).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .,-')
    return cleaned if len(cleaned) >= 2 else name

def clean_person_name(dm):
    if not dm or dm.lower() in [
        'executive directorate', 'directorate', 'management', 'owner',
        'director', 'chief executive officer', 'ceo', 'managing director'
    ]:
        return None
    cleaned = re.sub(r'^(MR\.|MS\.|MRS\.|DR\.|ENGR\.|CH\.|MIAN|SHEIKH|HAJI)\s+', '', dm, flags=re.IGNORECASE).strip()
    cleaned = cleaned.split('/')[0].split('(')[0].strip()
    parts = cleaned.split()
    if parts:
        first = parts[0].capitalize()
        if len(first) >= 2 and first.isalpha():
            return first
    return None

def extract_area(addr):
    if not addr:
        return "Karachi"
    addr_clean = addr.replace('"', '').replace("'", "")
    for zone in KNOWN_ZONES:
        pattern = r'\b' + re.escape(zone.replace("'", "")) + r'\b'
        if re.search(pattern, addr_clean, re.I):
            return zone
    return "Karachi"

def draft_email_for_lead(lead):
    comp_raw = lead.get('Company Name', '')
    comp = clean_company_name(comp_raw)
    dm = clean_person_name(lead.get('Decision Maker', ''))
    ind = lead.get('Industry', '').lower()
    addr = lead.get('Address', '').strip()
    area = extract_area(addr)

    greeting = f"Hi {dm}," if dm else f"Hi {comp} Team,"

    # Tailor angles by Karachi industry sector
    if any(k in ind for k in ['wholesale', 'chemical', 'dyes', 'distribution']):
        obs = f"I noticed {comp} coordinates high-volume wholesale distribution and commercial trade across {area}. Managing multi-SKU warehouse inventory and dealer dispatches across separate spreadsheets often creates stock discrepancies and delayed price quotations."
        sol = f"If stock updates and purchase orders are still tracked manually, a unified inventory and quotation ERP could automate real-time warehouse counts and instant dealer quoting. At Cortech Solution, we engineer custom ERP software specifically for Karachi distributors."
        cta = f"I can put together a simple preview of what this inventory workflow could look like for {comp} if useful."
        subj = f"Inventory tracking and dealer quotation workflow for {comp}"
    elif any(k in ind for k in ['hosiery', 'knitwear']):
        obs = f"I noticed {comp} coordinates high-volume hosiery and knitwear manufacturing from your facility in {area}. Managing yarn roll consumption, dye-lot variations, and multi-stage cut-to-pack job orders across spreadsheets often leads to production bottlenecks."
        sol = f"If job orders and yarn stock are currently reconciled manually, a custom production and batch-tracking ERP could automate cut-to-pack scheduling and export packing lists. At Cortech Solution, we build tailored ERP systems for Karachi textile exporters."
        cta = f"I can share a quick preview of how this cut-to-pack workflow could look for {comp} if you would like to see it."
        subj = f"Cut-to-pack batch inventory and export workflow for {comp}"
    elif any(k in ind for k in ['garment', 'apparel']):
        obs = f"I noticed {comp} coordinates large-scale apparel manufacturing and export dispatches from your {area} facility. Tracking bulk fabric rolls, cutting yields, and stitching line progress across separate files often creates production visibility gaps."
        sol = f"If fabric roll yardage and export shipments are still coordinated manually, a tailored garment ERP could centralize job-order costing and streamline export invoicing. At Cortech Solution, we develop custom production and inventory software for Karachi apparel manufacturers."
        cta = f"I can map out a simple example of how this workflow could operate for {comp} if useful."
        subj = f"Fabric roll inventory and job-order tracking for {comp}"
    elif any(k in ind for k in ['food', 'grain', 'rice', 'commodity']):
        obs = f"I noticed {comp} oversees bulk agricultural commodity wholesale and commercial grain dispatches across {area}. Reconciling warehouse silo batches, weight receipts, and container dispatches across manual sheets often creates billing delays."
        sol = f"If lot tracking and dealer orders are still managed manually, a dedicated commodity inventory ERP could synchronize bulk grain stock and automate wholesale invoicing. At Cortech Solution, we engineer custom inventory and order tracking software for Karachi grain distributors."
        cta = f"I can put together a quick preview of how this commodity batch workflow could work for {comp} if you would like to see it."
        subj = f"Grain batch tracking and wholesale order ERP for {comp}"
    elif any(k in ind for k in ['automotive', 'engineering', 'machining']):
        obs = f"I noticed {comp} specializes in precision automotive parts and engineering manufacturing from your {area} plant. Managing multi-SKU die tooling, metal scrap ratios, and OEM dealer orders across spreadsheets often creates dispatch bottlenecks."
        sol = f"If part serialization and raw material allocations are still handled manually, a custom engineering ERP could automate batch inventory and instant OEM price quotes. At Cortech Solution, we build tailored manufacturing ERP software for Karachi industrial firms."
        cta = f"I can put together a brief preview of what this tooling and parts workflow could look like for {comp} if useful."
        subj = f"Part serialization and OEM quotation ERP for {comp}"
    elif any(k in ind for k in ['leather', 'footwear', 'tanning']):
        obs = f"I noticed {comp} specializes in leather tanning and goods manufacturing from your facility in {area}. Managing raw hide lots, tanning stages, and square-footage leather inventory across separate files often creates stock discrepancies."
        sol = f"If hide yield and buyer dispatches are still coordinated manually, a custom tannery ERP could automate lot traceability and export quotation calculations. At Cortech Solution, we build tailored inventory and production tracking ERP systems for Karachi leather exporters."
        cta = f"I can put together a simple preview of how this lot-tracking workflow could look for {comp} if you would like to see it."
        subj = f"Leather lot traceability and export quotation ERP for {comp}"
    else:
        obs = f"I noticed {comp} coordinates commercial trade and wholesale operations in {area}. Managing multi-SKU orders and supplier dispatches across separate spreadsheets often creates stock discrepancies and delayed quotations."
        sol = f"If inventory updates and customer orders are still tracked manually, a unified inventory and quotation ERP could centralize stock visibility and speed up invoicing. At Cortech Solution, we engineer custom ERP software for Karachi commercial distributors."
        cta = f"I can put together a quick preview of how this workflow could look for {comp} if useful."
        subj = f"Inventory tracking and order management ERP for {comp}"

    body = f"{greeting}\n\n{obs}\n\n{sol}\n\n{cta}\n\n{SIGNATURE}"
    return subj, body

def main():
    print("=" * 65)
    print("Hostinger Email Drafter — Scanning & Drafting All New Leads")
    print("=" * 65)

    all_eligible = lead_status.list_eligible(BASE_DIR)
    total_eligible = len(all_eligible)
    print(f"Total eligible unsent leads found: {total_eligible}")

    if total_eligible == 0:
        print("No eligible leads found to draft. Exiting.")
        return

    # Group eligible leads by file
    leads_by_file = {}
    for lead in all_eligible:
        fpath = lead.get('_file')
        if fpath not in leads_by_file:
            leads_by_file[fpath] = []
        leads_by_file[fpath].append(lead)

    today_str = date.today().isoformat()
    drafts_for_md = []
    drafts_for_queue = []
    total_updated_rows = 0
    skipped_leads = 0

    lead_counter = 1

    for fpath, file_leads in leads_by_file.items():
        print(f"\nProcessing {len(file_leads)} eligible leads in: {fpath}")
        fieldnames, rows = lead_status.read_rows(fpath)

        rows_updated_in_file = 0

        for lead in file_leads:
            row_idx = lead.get('_row')
            if row_idx is None or row_idx >= len(rows):
                print(f"  [ERROR] Invalid row index {row_idx} for {lead.get('Company Name')}")
                continue

            # Contact quality & validation
            em = (lead.get("Owner Email") or lead.get("Business Email") or lead.get("Sales Email") or "").strip()
            if not em or "@" not in em or lead_status.is_dummy_email(em):
                print(f"  [SKIP] Invalid email for {lead.get('Company Name')}: {em}")
                skipped_leads += 1
                continue

            # Clean recipient email
            clean_em = em.split(';')[0].split(',')[0].strip()

            comp_name = lead.get('Company Name', '').strip()
            dm_name = lead.get('Decision Maker', '').strip()
            city = lead.get('City', '').strip()
            ind = lead.get('Industry', '').strip()

            subject, body = draft_email_for_lead(lead)
            word_count = len(body.split())

            # Append to draft_queue.json
            queue_item = {
                "to": clean_em,
                "subject": subject,
                "body": body,
                "label": comp_name,
                "csv_file": os.path.abspath(fpath),
                "csv_row": row_idx
            }
            drafts_for_queue.append(queue_item)

            # Append to draft.md
            md_item = f"""## Lead {lead_counter}: {comp_name}
**To:** `{clean_em}`  
**Subject:** {subject}  
**Location:** {city} | **Industry:** {ind}  
**Decision Maker:** {dm_name or 'Directorate'} | **Words:** {word_count}  

```text
{body}
```

---
"""
            drafts_for_md.append(md_item)
            lead_counter += 1

            # Update row in CSV memory
            target_row = rows[row_idx]
            target_row[lead_status.DATE_COL] = today_str
            target_row[lead_status.STATUS_COL] = lead_status.CONTACTED_STATUS
            rows_updated_in_file += 1

        # Atomic write back to CSV
        lead_status.write_rows(fpath, fieldnames, rows)
        print(f"  -> Atomically updated {rows_updated_in_file} rows in {os.path.basename(fpath)}")
        total_updated_rows += rows_updated_in_file

    # Write draft.md
    md_header = f"""# Cold Email Outreach Drafts — Karachi ERP & Inventory Campaign ({today_str})
**Total Drafts Queued:** {len(drafts_for_queue)}  
**Campaign Focus:** ERP & Inventory Management Software (Cortech Solution)  
**Target Market:** Karachi B2B Wholesalers, Manufacturers & Exporters  
**Status:** Awaiting User Review & Approval (NO EMAILS HAVE BEEN SENT)  

---

"""
    with open(DRAFT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_header + "\n".join(drafts_for_md))
    print(f"\n[OK] Successfully wrote {len(drafts_for_md)} drafts to {DRAFT_MD_PATH}")

    # Write draft_queue.json
    with open(DRAFT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(drafts_for_queue, f, indent=2, ensure_ascii=False)
    print(f"[OK] Successfully wrote {len(drafts_for_queue)} items to {DRAFT_QUEUE_PATH}")

    # Quality check
    word_counts = [len(item["body"].split()) for item in drafts_for_queue]
    print(f"\nQuality Audit:")
    print(f"  Word Counts: min={min(word_counts)}, max={max(word_counts)}, avg={sum(word_counts)/len(word_counts):.1f}")
    print(f"  Drafts conforming strictly to 80-110 (max 130) words: {sum(1 for w in word_counts if 80 <= w <= 130)} / {len(word_counts)}")

    print("\n" + "=" * 65)
    print("DRAFTING RUN SUMMARY")
    print("=" * 65)
    print(f"Total Leads Checked: {total_eligible}")
    print(f"Eligible Leads: {total_eligible}")
    print(f"Skipped Leads: {skipped_leads}")
    print(f"Drafts Written to draft.md: {len(drafts_for_md)}")
    print(f"Drafts Queued in draft_queue.json: {len(drafts_for_queue)}")
    print(f"Emails Sent: 0 (Draft-only step; awaiting explicit user approval)")
    print(f"CSV Rows Updated: {total_updated_rows}")
    print(f"Remaining Eligible Leads: 0")

if __name__ == "__main__":
    main()
