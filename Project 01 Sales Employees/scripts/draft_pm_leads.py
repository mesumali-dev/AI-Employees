#!/usr/bin/env python3
"""
scripts/draft_pm_leads.py
Automated high-quality cold email drafter for Cortech Solution's
Property Management & Business Workflow Software campaign.
Strictly adheres to hostinger-email-drafter/SKILL.md and email_style_guide.md.
"""

import os
import sys
import re
import json
import urllib.parse
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

GENERIC_NAMES = {
    "team", "admin", "info", "office", "manager", "support", "help",
    "enquiries", "inquiries", "reception", "contact", "sales", "rentals"
}

def clean_company_name(name, domain=""):
    if not name:
        return domain.split(".")[0].capitalize() if domain else "Your Team"
    
    parts = re.split(r"[-|–—:•]", name)
    cleaned = parts[0].strip()
    cleaned = re.sub(r"(?i)\s*(Pty\.?\s*Ltd\.?|Pty\.?|Ltd\.?|Real Estate|Property Management|Property Group)$", "", cleaned).strip()
    if len(cleaned) < 2:
        cleaned = parts[0].strip()
    return cleaned

def extract_first_name(dm, recipient_email, company):
    if dm and dm.strip():
        dm_clean = dm.strip()
        parts = dm_clean.split()
        first = parts[0].replace(",", "").replace(".", "").strip()
        if first.lower() not in GENERIC_NAMES and len(first) >= 2 and first.isalpha():
            return first.capitalize()
            
    # Try local part of email if named
    local = recipient_email.split("@")[0].lower()
    clean_local = re.sub(r"[0-9_.-]", "", local)
    if clean_local not in GENERIC_NAMES and len(clean_local) >= 3 and clean_local.isalpha():
        comp_words = [w.lower() for w in company.split()]
        if clean_local not in comp_words:
            return clean_local.capitalize()
            
    return ""

def select_recipient_email(lead):
    owner = lead.get("Owner Email", "").strip()
    biz = lead.get("Business Email", "").strip()
    
    if owner and not lead_status.is_dummy_email(owner):
        candidate = urllib.parse.unquote(owner).strip()
        if "@" in candidate and "." in candidate:
            return candidate
            
    if biz and not lead_status.is_dummy_email(biz):
        candidate = urllib.parse.unquote(biz).strip()
        if "@" in candidate and "." in candidate:
            return candidate
            
    return None

def build_subject(company, idx):
    subjects = [
        f"Maintenance and repair workflow for {company}",
        f"Tenant maintenance and contractor dispatch for {company}",
        f"Streamlining tenant requests and contractor quotes for {company}",
        f"Property management workflow and trade dispatch for {company}",
        f"Maintenance triage and landlord approvals for {company}"
    ]
    return subjects[idx % len(subjects)]

def build_cta(company, idx):
    ctas = [
        "I can map out what this workflow could look like around your current setup if useful.",
        "I can put together a simple preview of how this could work for your team if you'd like to see it.",
        "I can show you a quick preview of how this workflow looks before you decide if it's worth discussing."
    ]
    return ctas[idx % len(ctas)]

def build_email_body(lead, first_name, company, city, state, idx):
    location = f"{city}, {state}".strip(", ") if city else (state or "Australia")
    
    # 1. Greeting
    greeting = f"Hi {first_name}," if first_name else f"Hi {company} Team,"
    
    # 2. Personalized Observation & Concrete Process
    evidence = (lead.get("Evidence", "") + " " + lead.get("Problems Found", "")).lower()
    
    if "short-stay" in evidence or "holiday" in evidence or "airbnb" in evidence:
        obs = f"I came across {company} while looking into boutique holiday accommodation in {location}."
        process = "I noticed guest repair requests and turnover maintenance currently route through standard contact forms."
        improvement = "If turnover repairs are still coordinated manually across inboxes, an automated dispatch workflow could eliminate that back-and-forth and keep properties guest-ready faster."
        solution = "At Cortech Solution, we build bespoke property management software that automates maintenance triage and contractor scheduling in one place."
    elif "commercial" in evidence or "strata" in evidence or "owners corporation" in evidence:
        obs = f"I came across {company} while researching commercial and residential property management in {location}."
        process = "I noticed tenant repair requests and trade quotes currently route through separate forms and email."
        improvement = "If quote sign-offs and repair follow-ups are coordinated manually across inboxes, an automated workflow could streamline dispatch and give landlords clear visibility without extra admin."
        solution = "At Cortech Solution, we build custom property management software that unifies work order dispatch and landlord quote approvals."
    elif "download" in evidence or "pdf" in evidence:
        obs = f"I came across {company} while looking into property management teams in {location}."
        process = "I noticed tenant repair requests on your website currently rely on static forms and email routing."
        improvement = "If repair triage and quote approvals are handled manually across inboxes, an automated dispatch workflow could eliminate repetitive back-and-forth and let your team manage more properties without added admin."
        solution = "At Cortech Solution, we build bespoke property management workflow software that automates maintenance triage and contractor tracking."
    else:
        obs = f"I came across {company} while looking into property management teams in {location}."
        process = "I noticed tenant maintenance enquiries and contractor coordination currently route through direct email and standard contact forms."
        improvement = "If repair triage and landlord quote approvals are handled manually across inboxes, an automated dispatch workflow could eliminate repetitive back-and-forth and let your existing team handle larger portfolios without extra admin."
        solution = "At Cortech Solution, we build bespoke property management software that automates repair triage and gives landlords real-time quote approvals."
        
    cta = build_cta(company, idx)
    
    body = f"{greeting}\n\n{obs} {process}\n\n{improvement} {solution}\n\n{cta}\n\n{SIGNATURE}"
    return body

def word_count(text):
    return len(re.findall(r"\b\w+\b", text))

def main():
    print("=" * 70)
    print("Hostinger Email Drafter — Drafting All Eligible Property Management Leads")
    print("=" * 70)
    
    leads = lead_status.list_eligible(BASE_DIR)
    print(f"Total eligible leads found: {len(leads)}")
    
    if not leads:
        print("No eligible leads found. Exiting.")
        return

    drafts = []
    queue_items = []
    rows_to_update = []
    
    skipped_count = 0
    
    for idx, lead in enumerate(leads, 1):
        csv_file = lead["_file"]
        csv_row = lead["_row"]
        
        # Double check eligibility
        if not lead_status.is_row_eligible(lead) or lead_status.is_row_already_contacted(lead):
            skipped_count += 1
            continue
            
        recipient_email = select_recipient_email(lead)
        if not recipient_email:
            skipped_count += 1
            continue
            
        raw_company = lead.get("Company Name", "").strip()
        web = lead.get("Website", "").strip()
        domain = ""
        if web:
            domain = re.sub(r"^https?://", "", web).split("/")[0].replace("www.", "")
        company = clean_company_name(raw_company, domain)
        
        dm = lead.get("Decision Maker", "").strip()
        first_name = extract_first_name(dm, recipient_email, company)
        
        city = lead.get("City", "").strip()
        state = lead.get("State", "").strip()
        
        subject = build_subject(company, idx)
        body = build_email_body(lead, first_name, company, city, state, idx)
        
        wc = word_count(body)
        assert 80 <= wc <= 130, f"Word count out of range: {wc} for {company}"
        
        drafts.append({
            "idx": idx,
            "company": raw_company,
            "to": recipient_email,
            "subject": subject,
            "city": city,
            "state": state,
            "dm": dm,
            "conf": lead.get("Opportunity Confidence", ""),
            "body": body,
            "word_count": wc
        })
        
        queue_items.append({
            "to": recipient_email,
            "subject": subject,
            "body": body,
            "label": raw_company,
            "csv_file": csv_file,
            "csv_row": csv_row
        })
        
        rows_to_update.append((csv_file, csv_row))

    print(f"Drafts prepared: {len(drafts)}")
    print(f"Skipped leads: {skipped_count}")

    # Write draft.md
    today_str = date.today().isoformat()
    lines = [
        f"# Cold Email Outreach Drafts — Property Management Campaign ({today_str})",
        f"**Total Drafts Queued:** {len(drafts)}  ",
        f"**Campaign Focus:** Property Management & Business Workflow Software (Cortech Solution)  ",
        f"**Status:** Awaiting User Review & Approval (NO EMAILS HAVE BEEN SENT)  \n",
        "---\n"
    ]
    
    for d in drafts:
        lines.append(f"## Lead {d['idx']}: {d['company']}")
        lines.append(f"**To:** `{d['to']}`  ")
        lines.append(f"**Subject:** {d['subject']}  ")
        lines.append(f"**Location:** {d['city']}, {d['state']}  ")
        if d['dm']:
            lines.append(f"**Decision Maker:** {d['dm']}  ")
        lines.append(f"**Opportunity Confidence:** {d['conf']} | **Words:** {d['word_count']}  \n")
        lines.append("```text")
        lines.append(d['body'])
        lines.append("```\n")
        lines.append("---\n")

    with open(DRAFT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Written {len(drafts)} drafts to {DRAFT_MD_PATH}")

    # Write draft_queue.json
    with open(DRAFT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue_items, f, indent=2)
    print(f"Written queue to {DRAFT_QUEUE_PATH}")

    # Atomic CSV update for all drafted rows
    # Group by file to update each file cleanly
    from collections import defaultdict
    file_rows = defaultdict(list)
    for f_path, r_idx in rows_to_update:
        file_rows[f_path].append(r_idx)

    for f_path, r_indices in file_rows.items():
        fieldnames, rows = lead_status.read_rows(f_path)
        for r_idx in r_indices:
            rows[r_idx]["Date Contacted"] = today_str
            rows[r_idx]["Lead Status"] = "Draft Created"
        lead_status.write_rows(f_path, fieldnames, rows)
        print(f"Updated {len(r_indices)} rows in {f_path} (Lead Status -> 'Draft Created', Date Contacted -> '{today_str}')")

    print("\nDrafting complete! All drafted rows safely updated.")

if __name__ == "__main__":
    main()
