#!/usr/bin/env python3
"""
draft_all_unsent.py - Automated high-quality cold email drafter for Cortech Solution
Strictly adheres to hostinger-email-drafter/SKILL.md and email_style_guide.md
"""

import sys
import os
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

GENERIC_LOCALS = {
    "info", "sales", "contact", "admin", "office", "service", "quotes", "tenders",
    "projects", "support", "help", "inquiries", "enquiries", "estimating", "reception",
    "accounts", "customerservice", "serviceteam", "mail", "hello", "team"
}

def clean_company_name(name, domain=""):
    if not name:
        return domain.split(".")[0].capitalize() if domain else "Your Team"
    
    parts = re.split(r"[-|–—:•]", name)
    cleaned = parts[0].strip()
    
    # Strip common web clutter
    cleaned = re.sub(r"(?i)\s*(Home|Official Site|Welcome|Pty\.?\s*Ltd\.?|Pty\.?|Ltd\.?)$", "", cleaned).strip()
    
    # If the scraped name is a generic headline or too long
    generic_prefixes = [
        "building contractors in", "commercial painters in", "commercial plumbers",
        "roofing contractor in", "civil construction contractors", "commercial roofing company",
        "industrial, commercial", "how to", "cost of", "best of", "top 7", "free quote"
    ]
    if len(cleaned.split()) >= 4 or any(x in cleaned.lower() for x in generic_prefixes):
        if domain:
            dom_base = domain.split(".")[0]
            if len(dom_base) >= 2 and dom_base not in ["google", "bing"]:
                return re.sub(r"[-_]", " ", dom_base).title()
    
    # Handle single generic words like 'Adelaide' or 'Sydney' or 'Contractor'
    if cleaned.lower() in ["commercial", "services", "contractor", "builders", "australia", "adelaide", "sydney", "melbourne", "brisbane", "perth", "award"]:
        if domain:
            dom_base = domain.split(".")[0]
            return re.sub(r"[-_]", " ", dom_base).title()

    return cleaned if len(cleaned) >= 2 else (domain.split(".")[0].capitalize() if domain else name)

def get_recipient_details(lead):
    owner_em = lead.get("Owner Email", "").strip()
    biz_em = lead.get("Business Email", "").strip()
    
    recipient_email = owner_em if owner_em and not lead_status.is_dummy_email(owner_em) else biz_em
    if not recipient_email or lead_status.is_dummy_email(recipient_email):
        return None, None, None
    
    recipient_email = urllib.parse.unquote(recipient_email).replace("%20", "").strip()
    if "@" not in recipient_email or len(recipient_email) < 6:
        return None, None, None

    domain = ""
    web = lead.get("Website", "").strip()
    if web:
        try:
            domain = re.sub(r"^https?://", "", web).split("/")[0].replace("www.", "")
        except: pass

    company = clean_company_name(lead.get("Company Name", ""), domain)
    
    dm = lead.get("Decision Maker", "").strip()
    if not dm or dm.lower() in GENERIC_LOCALS:
        local = recipient_email.split("@")[0].lower()
        if local not in GENERIC_LOCALS:
            clean_local = re.sub(r"[0-9_.-]", "", local)
            comp_words = [w.lower() for w in company.split()]
            dom_words = [w.lower() for w in domain.split(".")[0].split("-")]
            if clean_local.lower() in comp_words or clean_local.lower() in dom_words:
                dm = ""
            elif len(clean_local) >= 3 and clean_local.isalpha() and clean_local not in GENERIC_LOCALS:
                dm = clean_local.capitalize()
            else:
                dm = ""
        else:
            dm = ""

    return recipient_email, dm, company

def get_industry_phrase(industry, company):
    ind_lower = industry.lower()
    if "fitout" in ind_lower or "refurbishment" in ind_lower:
        return "commercial fitout and interior refurbishment specialists"
    elif "civil" in ind_lower or "earthmoving" in ind_lower:
        return "civil construction and earthmoving contractors"
    elif "steel" in ind_lower or "fabrication" in ind_lower:
        return "structural steel fabrication and erection contractors"
    elif "roof" in ind_lower or "cladding" in ind_lower:
        return "commercial roofing and architectural cladding contractors"
    elif "mep" in ind_lower or "hvac" in ind_lower or "mechanical" in ind_lower or "electrical" in ind_lower:
        return "commercial mechanical and building services contractors"
    elif "concrete" in ind_lower or "formwork" in ind_lower:
        return "commercial concrete and formwork specialists"
    elif "estimating" in ind_lower or "quantity survey" in ind_lower:
        return "construction estimating and quantity surveying firms"
    elif "scaffold" in company.lower():
        return "commercial scaffolding and rigging contractors"
    elif "paint" in company.lower() or "paint" in ind_lower:
        return "commercial painting and protective coatings specialists"
    elif "glaz" in company.lower() or "glass" in company.lower():
        return "commercial glazing and architectural facade contractors"
    elif "demolition" in company.lower() or "asbestos" in company.lower():
        return "commercial demolition and hazardous remediation contractors"
    else:
        return "commercial builders and trade contractors"

def draft_email(lead, recipient_email, dm, company):
    city = lead.get("City", "").strip() or "Australia"
    industry = lead.get("Industry", "").strip() or "Commercial Building & Construction"
    ind_phrase = get_industry_phrase(industry, company)
    
    # 1. Greeting
    greeting = f"Hi {dm}," if dm else f"Hi {company} Team,"
    
    # 2. Subject lines (varied, compelling, professional)
    subject_templates = [
        f"Inquiry and quote workflow for {company}",
        f"Estimating and tender intake for {company}",
        f"Streamlining quote requests for {company}",
        f"Project inquiry and estimating workflow for {company}"
    ]
    subj_idx = abs(hash(company)) % len(subject_templates)
    subject = subject_templates[subj_idx]
    
    # 3. Observation & Process
    obs = f"I came across {company} while researching {ind_phrase} in {city}."
    
    # Check upload evidence
    evidence = lead.get("Evidence", "").lower()
    prob = lead.get("Problems Found", "").lower()
    if "drawing" in evidence or "plan" in evidence or "drawing" in prob or "plan" in prob:
        process = "I noticed plans and tender packages on your website currently route through standard forms and direct email."
    else:
        process = "I noticed project enquiries and quote requests on your website currently route through standard web forms and direct email."
        
    # 4. Commercial Improvement (Conditional Framing)
    improvement = "If plan reviews and quote follow-ups are still coordinated manually across separate inboxes, an automated intake workflow could organize incoming requests and accelerate proposal turnaround."
    
    # 5. Cortech Solution
    solution = "At Cortech Solution, we build bespoke estimating and quotation portals for Australian contractors, centralizing incoming project scope and quote tracking in a unified dashboard."
    
    # 6. Low-friction CTA
    cta_templates = [
        f"I can map out what this workflow could look like around your current setup if useful.",
        f"I can put together a simple preview of how this could work for your team if you'd like to see it.",
        f"I can show you a quick preview of how this workflow looks before you decide if it's worth discussing."
    ]
    cta = cta_templates[abs(hash(company + "cta")) % len(cta_templates)]
    
    body = f"{greeting}\n\n{obs} {process}\n\n{improvement} {solution}\n\n{cta}\n\n{SIGNATURE}"
    return subject, body

def main():
    print("=" * 65)
    print("Hostinger Email Drafter — Bulk Drafting All Unsent Australian Leads")
    print("=" * 65)
    
    oct_path = os.path.join(BASE_DIR, "2026", "leads-oct.csv")
    fieldnames, rows = lead_status.read_rows(oct_path)
    print(f"Total rows in {oct_path}: {len(rows)}")
    
    today_str = date.today().isoformat()
    
    drafts_for_md = []
    drafts_for_queue = []
    skipped_count = 0
    updated_count = 0
    
    for idx, row in enumerate(rows, 1):
        if row.get("Requested For") != "Quotation, Estimating & Lead Management Systems":
            continue
        status = row.get(lead_status.STATUS_COL, "").strip()
        if status not in [lead_status.ELIGIBLE_STATUS, lead_status.CONTACTED_STATUS]:
            continue
            
        recipient_email, dm, company = get_recipient_details(row)
        if not recipient_email:
            skipped_count += 1
            continue
            
        subject, body = draft_email(row, recipient_email, dm, company)
        
        # Word count validation
        wc = len(body.split())
        assert 75 <= wc <= 130, f"Word count {wc} outside range for {company}"
        
        queue_item = {
            "to": recipient_email,
            "subject": subject,
            "body": body,
            "label": company,
            "csv_file": os.path.abspath(oct_path),
            "csv_row": idx
        }
        drafts_for_queue.append(queue_item)
        
        md_item = f"""## {len(drafts_for_queue)}. {company}
**To:** `{recipient_email}`  
**Subject:** {subject}  
**Location:** {row.get('City', '')}, {row.get('State', '')} | **Industry:** {row.get('Industry', '')}  

{body}

---
"""
        drafts_for_md.append(md_item)
        
        # Update row
        row[lead_status.DATE_COL] = today_str
        row[lead_status.STATUS_COL] = lead_status.CONTACTED_STATUS
        updated_count += 1
        
    print(f"Drafts prepared: {len(drafts_for_queue)}")
    print(f"Skipped leads (invalid/missing email): {skipped_count}")
    
    # Write draft.md
    md_header = f"""# Cold Email Drafts — {today_str}
**Campaign:** Quotation, Estimating & Lead Management Systems  
**Target:** Australian Commercial Builders & Trade Contractors  
**Total Drafts Prepared:** {len(drafts_for_queue)}  
*Status: Ready for User Review. No emails have been sent.*  

---

"""
    with open(DRAFT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_header + "\n".join(drafts_for_md))
    print(f"Successfully written {len(drafts_for_md)} drafts to {DRAFT_MD_PATH}")
    
    # Write draft_queue.json
    with open(DRAFT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(drafts_for_queue, f, indent=2)
    print(f"Successfully written {len(drafts_for_queue)} items to {DRAFT_QUEUE_PATH}")
    
    # Atomic write to CSV
    lead_status.write_rows(oct_path, fieldnames, rows)
    print(f"Atomically updated {oct_path} ({updated_count} rows marked 'Draft Created')")
    
    # Statistics
    word_counts = [len(item["body"].split()) for item in drafts_for_queue]
    print(f"Word counts: min={min(word_counts)}, max={max(word_counts)}, avg={sum(word_counts)/len(word_counts):.1f}")
    
    print("\n" + "=" * 65)
    print("FINAL DRAFTING REPORT")
    print("=" * 65)
    print(f"Total Eligible Leads Found: {updated_count + skipped_count}")
    print(f"Drafts Written to draft.md: {len(drafts_for_md)}")
    print(f"Drafts Queued in draft_queue.json: {len(drafts_for_queue)}")
    print(f"Emails Sent: 0 (Draft-only step; awaiting user approval)")
    print(f"CSV Rows Updated to 'Draft Created': {updated_count}")
    print(f"Skipped Leads: {skipped_count}")

if __name__ == "__main__":
    main()
