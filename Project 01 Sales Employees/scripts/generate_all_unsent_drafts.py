#!/usr/bin/env python3
"""
generate_all_unsent_drafts.py - Automated high-quality cold email drafter for Cortech Solution
Complies strictly with hostinger-email-drafter/SKILL.md and email_style_guide.md
"""

import sys
import os
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

def clean_company_name(name, domain=""):
    if not name:
        return domain.split(".")[0].capitalize() if domain else "Your Team"
    
    # If the scraped name is a long article or headline
    if len(name.split()) > 5 or any(x in name.lower() for x in ["how to", "cost of", "cost per", "definition", "options in", "what determines", "best of", "top 7", "free quote"]):
        if domain:
            dom_base = domain.split(".")[0]
            if len(dom_base) > 2 and dom_base not in ["google", "bing", "homestars"]:
                return re.sub(r"[-_]", " ", dom_base).title()

    parts = re.split(r"[-|–—:•]", name)
    cleaned = parts[0].strip()
    cleaned = re.sub(r"(?i)\s*(Home|Official Site|Welcome|Commercial|Services|Ltd\.?|Inc\.?|Corp\.?)$", "", cleaned).strip()
    
    generic_patterns = [
        r"^(commercial|residential|industrial)\s+(hvac|roofing|plumbing|electrical|landscaping|cleaning|painters|movers|general contractors)\b",
        r"^(hvac|roofing|plumbing|electrical)\s+contractors\b",
        r"^(best|top|expert)\s+",
        r"^(instant|free)\s+.*quote\b",
        r"^(how much does|cost of)\b",
        r"^office movers\b",
        r"^custom home builder\b"
    ]
    for pat in generic_patterns:
        if re.search(pat, cleaned, re.IGNORECASE):
            dom_base = domain.split(".")[0]
            if len(dom_base) > 2 and dom_base not in ["google", "bing", "homestars"]:
                brand = re.sub(r"[-_]", " ", dom_base).title()
                return brand
    
    return cleaned if len(cleaned) >= 2 else (domain.split(".")[0].capitalize() if domain else name)

def urllib_unquote(s):
    try:
        import urllib.parse
        return urllib.parse.unquote(s)
    except:
        return s

def get_recipient_details(lead):
    owner_em = lead.get("Owner Email", "").strip()
    biz_em = lead.get("Business Email", "").strip()
    
    recipient_email = owner_em if owner_em and not lead_status.is_dummy_email(owner_em) else biz_em
    if not recipient_email or lead_status.is_dummy_email(recipient_email):
        return None, None, None
    
    recipient_email = urllib_unquote(recipient_email).strip()
    
    dm = lead.get("Decision Maker", "").strip()
    if not dm or dm.lower() in ["info", "sales", "contact", "support", "office", "admin"]:
        local = recipient_email.split("@")[0].lower()
        if local not in ["info", "sales", "contact", "admin", "office", "service", "quotes", "projects", "support", "help", "inquiries", "estimating", "reception"]:
            if len(local) > 2 and local.isalpha():
                dm = local.capitalize()
    
    domain = ""
    web = lead.get("Website", "").strip()
    if web:
        try:
            domain = re.sub(r"^https?://", "", web).split("/")[0].replace("www.", "")
        except: pass

    company = clean_company_name(lead.get("Company Name", ""), domain)
    return recipient_email, dm, company

def draft_email_for_lead(lead, recipient_email, dm, company):
    city = lead.get("City", "").strip() or "your area"
    ind = lead.get("Industry", "").strip() or "commercial services"
    
    # 1. Greeting
    greeting = f"Hi {dm}," if dm else f"Hi {company} Team,"
    
    # Subject line (varied, compelling, professional)
    subject_templates = [
        f"Inquiry and quote workflow for {company}",
        f"Quick question regarding {company}'s inquiry workflow",
        f"Streamlining customer inquiries for {company}",
        f"Lead management workflow for {company}"
    ]
    subj_idx = abs(hash(company)) % len(subject_templates)
    subject = subject_templates[subj_idx]
    
    ind_lower = ind.lower()
    if "hvac" in ind_lower or "refrigeration" in ind_lower:
        obs = f"I came across {company} while researching mechanical and HVAC contractors in {city}."
        process = f"I noticed project estimates and maintenance inquiries currently flow through standard web forms and direct email."
        benefit = f"If quotation follow-ups and contract renewals are still managed manually, a centralized lead management portal could organize requests and accelerate response times."
    elif "roof" in ind_lower:
        obs = f"I came across {company} while researching commercial roofing specialists in {city}."
        process = f"I noticed estimate requests and roof inspection inquiries currently rely on static contact forms and email."
        benefit = f"If estimate preparation and bid follow-ups are still coordinated across separate inboxes, a dedicated quote tracking dashboard could streamline proposal turnaround."
    elif "plumb" in ind_lower:
        obs = f"I came across {company} while researching commercial plumbing contractors in {city}."
        process = f"I noticed commercial project inquiries and service calls currently route through basic web forms and email."
        benefit = f"If dispatch details and client estimates are currently handled manually, a centralized lead management portal could keep proposals organized and speed up client follow-ups."
    elif "electr" in ind_lower:
        obs = f"I came across {company} while researching commercial electrical contractors in {city}."
        process = f"I noticed commercial bids and panel upgrade inquiries currently flow through basic contact forms and email."
        benefit = f"If preliminary scoping and estimate follow-ups are still tracked manually, a custom lead management system could organize incoming bids and shorten turnaround times."
    elif "landscap" in ind_lower:
        obs = f"I came across {company} while researching commercial grounds maintenance specialists in {city}."
        process = f"I noticed seasonal contract inquiries and maintenance bids currently flow through standard web forms."
        benefit = f"If contract renewals and property estimates are currently managed through spreadsheets, a centralized CRM workflow could organize recurring proposals without extra admin overhead."
    elif "clean" in ind_lower:
        obs = f"I came across {company} while researching commercial cleaning and facility services in {city}."
        process = f"I noticed facility walkthrough requests and recurring cleaning quotes currently flow through open web forms."
        benefit = f"If commercial bids and recurring agreements are still tracked across scattered emails, a unified CRM portal could centralize incoming requests and accelerate proposals."
    elif "builder" in ind_lower or "general contracting" in ind_lower:
        obs = f"I came across {company} while looking into commercial builders and general contractors in {city}."
        process = f"I noticed consultation requests and project inquiries currently flow through standard email and static web forms."
        benefit = f"If preliminary scoping and client intake are still coordinated across fragmented inboxes, a dedicated lead tracking portal could organize incoming inquiries before site visits."
    elif "mov" in ind_lower or "logistics" in ind_lower or "warehous" in ind_lower:
        obs = f"I came across {company} while researching commercial logistics and relocation providers in {city}."
        process = f"I noticed commercial move inquiries and storage requests currently route through basic contact forms."
        benefit = f"If quote preparation and follow-ups are still managed through manual email triage, a centralized intake dashboard could organize move requests and accelerate booking turnaround."
    elif "secur" in ind_lower or "fire" in ind_lower:
        obs = f"I came across {company} while researching commercial fire and security specialists in {city}."
        process = f"I noticed inspection requests and commercial system quotes currently flow through basic forms and direct email."
        benefit = f"If inspection renewals and equipment bids are still tracked manually, an integrated lead management system could organize client files and ensure timely follow-ups."
    elif "paint" in ind_lower or "glass" in ind_lower:
        obs = f"I came across {company} while researching commercial trade specialists in {city}."
        process = f"I noticed commercial bids and estimate requests currently rely on standard web forms and direct email."
        benefit = f"If project estimates and client follow-ups are currently tracked manually, a centralized quote management portal could streamline proposal tracking and help your team respond faster."
    elif "accounting" in ind_lower or "tax" in ind_lower:
        obs = f"I came across {company} while researching corporate tax and advisory practices in {city}."
        process = f"I noticed new client consultations and corporate intake currently rely on standard contact forms and direct email."
        benefit = f"If new client onboarding and consultation scheduling are still managed manually, a tailored intake portal could pre-qualify inquiries and organize client documents before first meetings."
    elif "legal" in ind_lower or "immigrat" in ind_lower:
        obs = f"I came across {company} while researching business immigration and legal practices in {city}."
        process = f"I noticed corporate client inquiries and initial consultations currently route through open contact forms."
        benefit = f"If initial file intake and consultation routing are still handled manually, a custom client onboarding portal could streamline preliminary data collection and organize incoming matters."
    else:
        obs = f"I came across {company} while researching established {ind_lower} providers in {city}."
        process = f"I noticed client inquiries and quote requests currently rely on standard web forms and direct email."
        benefit = f"If incoming project estimates are still managed through individual inboxes, a centralized lead management dashboard could keep proposals organized and speed up follow-ups."
    
    # CTA options (low friction, offering value upfront)
    cta_templates = [
        f"I can map out what this workflow could look like around your current setup if useful.",
        f"I can put together a simple example of how this could work for {company} if you'd like to see it.",
        f"I can show you a quick preview of how this workflow looks before you decide if it's worth discussing."
    ]
    cta = cta_templates[abs(hash(company + "cta")) % len(cta_templates)]
    
    body_paragraphs = [
        greeting,
        f"{obs} {process}",
        f"{benefit} At Cortech Solution, we build bespoke lead management and quotation systems for Canadian service businesses.",
        cta,
        SIGNATURE
    ]
    
    body = "\n\n".join(body_paragraphs)
    return subject, body

def main():
    print("=" * 60)
    print("Hostinger Email Drafter — Processing All Unsent Leads")
    print("=" * 60)
    
    all_eligible = lead_status.list_eligible(BASE_DIR)
    total_eligible = len(all_eligible)
    print(f"Total eligible unsent leads found: {total_eligible}")
    
    # Even if status is already marked Draft Created in CSV from our first run,
    # let's make sure we draft for all 205 leads from rows 100-304!
    oct_path = os.path.join(BASE_DIR, "2026", "leads-oct.csv")
    fieldnames, rows = lead_status.read_rows(oct_path)
    
    # Target rows 100 to 304 (the CRM leads added in this session)
    target_rows = rows[100:]
    print(f"Targeting {len(target_rows)} CRM leads in {oct_path}...")
    
    today_str = date.today().isoformat()
    drafts_for_md = []
    drafts_for_queue = []
    updated_count = 0
    
    for idx, row in enumerate(target_rows, 100):
        recipient_email, dm, company = get_recipient_details(row)
        if not recipient_email:
            continue
            
        subject, body = draft_email_for_lead(row, recipient_email, dm, company)
        
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
        
        row[lead_status.DATE_COL] = today_str
        row[lead_status.STATUS_COL] = lead_status.CONTACTED_STATUS
        updated_count += 1

    # Write back CSV atomically
    lead_status.write_rows(oct_path, fieldnames, rows)
    print(f"Atomically updated {oct_path} ({updated_count} rows marked Draft Created)")

    # Write draft.md
    md_header = f"""# Cold Email Drafts — {today_str}
**Campaign:** CRM / Lead Management Software  
**Target:** Canadian Commercial Service Businesses  
**Total Drafts Prepared:** {len(drafts_for_queue)}  
*Status: Ready for User Review. No emails have been sent.*  

---

"""
    with open(DRAFT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_header + "\n".join(drafts_for_md))
    print(f"Successfully wrote {len(drafts_for_md)} drafts to {DRAFT_MD_PATH}")

    # Write draft_queue.json
    with open(DRAFT_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(drafts_for_queue, f, indent=2)
    print(f"Successfully wrote {len(drafts_for_queue)} items to {DRAFT_QUEUE_PATH}")

    # Word count check
    word_counts = [len(item["body"].split()) for item in drafts_for_queue]
    print(f"Word counts: min={min(word_counts)}, max={max(word_counts)}, avg={sum(word_counts)/len(word_counts):.1f}")
    
    print("\n" + "=" * 60)
    print("DRAFTING RUN SUMMARY")
    print("=" * 60)
    print(f"Total Leads Checked: {len(target_rows)}")
    print(f"Drafts Written to draft.md: {len(drafts_for_md)}")
    print(f"Drafts Queued in draft_queue.json: {len(drafts_for_queue)}")
    print(f"Emails Sent: 0 (Draft-only step; awaiting user approval)")
    print(f"CSV Rows Updated: {updated_count}")

if __name__ == "__main__":
    main()
