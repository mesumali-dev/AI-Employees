#!/usr/bin/env python3
"""
generate_whatsapp_drafts.py — Automated high-converting WhatsApp message drafter
for Cortech Solution. Strictly adheres to:
  - .agents/skills/whatsapp-message-drafter/SKILL.md
  - .agents/skills/whatsapp-message-drafter/references/whatsapp_style_guide.md
"""

import csv
import json
import os
import re
import sys
import urllib.parse
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import whatsapp_status

BASE_DIR = "outputs/leads"
CSV_PATH = "outputs/leads/2026/leads-oct.csv"
OUTPUT_MD = "whatsapp_drafts.md"
OUTPUT_QUEUE = "whatsapp_queue.json"

SENDER_NAME = "Syed Mesum Ali Shah"
SENDER_COMPANY = "Cortech Solution"
SENDER_EMAIL = "mesum@cortechsolution.com"

SIGNATURE = f"""Best regards,

{SENDER_NAME}
{SENDER_COMPANY}
{SENDER_EMAIL}"""

GENERIC_TITLES = {
    "team", "owner", "director", "manager", "admin", "estimating", "hello",
    "sales", "info", "support", "contact", "office", "service", "inquiries",
    "enquiries", "founder", "president", "ceo", "management", "reception"
}

GENERIC_STARTS = [
    "commercial", "residential", "industrial", "licensed", "general contractor",
    "office movers", "immigration lawyer", "dentist in", "accounting firm",
    "renovation contractor", "building supplies", "roof repair", "tree removal",
    "furnace repair", "electrical contractor", "plumbing contractor", "roofing contractor"
]


def clean_company_name(name, domain=""):
    if not name:
        return domain.split(".")[0].capitalize() if domain else "Your Team"
    parts = re.split(r"[-|–—:•]", name)
    cleaned = parts[0].strip()
    cleaned = re.sub(
        r"(?i)\s*(Home|Official Site|Welcome|Pty\.?\s*Ltd\.?|Pty\.?|Ltd\.?|Inc\.?|Corp\.?)$",
        "",
        cleaned,
    ).strip()

    is_generic = any(cleaned.lower().startswith(g) for g in GENERIC_STARTS)
    if is_generic or len(cleaned.split()) >= 4:
        if domain:
            dom_base = domain.split(".")[0]
            if len(dom_base) >= 2 and dom_base not in [
                "google", "bing", "homestars", "yellowpages"
            ]:
                return re.sub(r"[-_]", " ", dom_base).title()
    return cleaned if len(cleaned) >= 2 else (domain.split(".")[0].capitalize() if domain else name)


def get_first_name(raw_dm):
    if not raw_dm:
        return ""
    dm = raw_dm.strip()
    # Check if generic or email handle
    if dm.lower() in GENERIC_TITLES:
        return ""
    if any(c.isdigit() for c in dm) or "@" in dm or len(dm) > 20:
        return ""
    if any(dm.lower().endswith(x) for x in ["ltd", "inc", "services", "group", "co"]):
        return ""
    
    first = dm.split()[0].replace(",", "").replace(".", "").strip()
    if len(first) >= 2 and first.isalpha() and first.lower() not in GENERIC_TITLES:
        return first.capitalize()
    return ""


def craft_whatsapp_message(lead, idx):
    web = lead.get("Website", "").strip()
    domain = ""
    if web:
        try:
            domain = re.sub(r"^https?://", "", web).split("/")[0].replace("www.", "")
        except Exception:
            pass

    company = clean_company_name(lead.get("Company Name", ""), domain)
    first_name = get_first_name(lead.get("Decision Maker", ""))

    # Block 1: Greeting
    if first_name:
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi {company} team,"

    # Block 2: Context / Observation
    city = (lead.get("City") or "").strip()
    industry = (lead.get("Industry") or "").strip().lower()
    if not industry or industry == "commercial":
        industry = "trade contracting"
    rating = lead.get("Google Rating", "").strip()

    if rating and float(rating) >= 4.5 and city:
        observation = f"I came across {company} while looking at top {industry} specialists in {city} — your {rating} rating really stands out."
    elif city:
        observation = f"I came across {company} while reviewing {industry} specialists in {city}."
    else:
        observation = f"I came across {company} while researching {industry} specialists."

    # Block 3: Pain Point (The single specific friction)
    problems = (lead.get("Problems Found") or "").strip()
    ssl = (lead.get("SSL") or "").strip().lower()
    https = (lead.get("HTTPS") or "").strip().lower()
    speed = (lead.get("Loading Speed") or "").strip().lower()
    country = (lead.get("Country") or "").strip().lower()

    if (ssl == "no" or https == "no") and domain:
        pain_point = f"I noticed {domain} is still served without full SSL encryption — modern browsers flag that with a 'Not Secure' alert, which quietly turns away prospective clients before they ever reach out."
        value_prop = f"We handle modern web infrastructure and security upgrades for {industry} firms, ensuring visitors immediately see a verified, trusted site instead of a browser warning."
    elif "slow" in speed or "poor" in speed or speed == ">5s":
        pain_point = f"I ran a quick performance check and noticed the mobile site takes over 5 seconds to load, which typically causes 30-40% of potential clients to drop off before seeing your services."
        value_prop = f"We build ultra-fast, mobile-optimized web infrastructure for {industry} specialists, ensuring your site loads instantly and captures high-intent traffic without drop-offs."
    elif "estimating portal" in problems.lower() or "tender document" in problems.lower() or "australia" in country:
        pain_point = "While reviewing your website, I noticed project enquiries and tender plan submissions currently route through standard forms and direct email without a structured estimating intake workflow."
        value_prop = f"We build fast, bespoke estimating and quotation portals for commercial contractors, centralizing incoming plan packages and quote tracking so high-value bids are turned around faster without inbox bottlenecks."
    elif "crm" in problems.lower() or "quote follow-up" in problems.lower() or "pipeline" in problems.lower():
        pain_point = "While reviewing your website, I noticed incoming quote requests currently route through a generic inbox without an automated lead qualification or quote follow-up pipeline."
        value_prop = f"We build fast, custom intake workflows and automated lead tracking pipelines for {industry} contractors, helping you qualify incoming jobs instantly and capture every high-intent inquiry."
    else:
        pain_point = "I noticed the site relies on a standard contact form with a generic inbox, with no direct booking flow or after-hours inquiry capture."
        value_prop = f"We build custom client intake workflows and automated lead capture systems, ensuring prospective clients receive immediate follow-up round the clock without slipping through the cracks."

    # Block 5: Frictionless CTA (varied)
    cta_variants = [
        f"Would you be open to seeing a quick 2-minute preview of what this looks like for {company}?",
        "Let me know if you'd like me to send over a quick preview of how this works.",
        f"Happy to share a quick 2-minute preview if you'd like to see how other {industry} teams are handling this.",
        f"Would it be helpful if I put together a quick preview of how this workflow would look for {company}?",
    ]
    cta = cta_variants[idx % len(cta_variants)]

    # Assemble complete message
    message = f"{greeting}\n\n{observation}\n\n{pain_point}\n\n{value_prop}\n\n{cta}\n\n{SIGNATURE}"
    return message, company, first_name


def main():
    print(f"Loading leads from {CSV_PATH}...")
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        sys.exit(1)

    fieldnames, rows = whatsapp_status.read_rows(CSV_PATH)

    drafts = []
    queue_items = []
    no_phone_indices = []
    email_conv_indices = []

    for idx, row in enumerate(rows):
        ws = (row.get("WhatsApp Status") or "").strip()
        ls = (row.get("Lead Status") or "").strip()
        resp = (row.get("Response") or "").strip()
        notes = (row.get("Notes") or "").strip()

        # Only evaluate leads that are New or empty
        if ws not in ["", "New"]:
            continue

        # Check for active email conversation
        if (
            ls == "In Discussion"
            or "replied" in resp.lower()
            or "proposal" in resp.lower()
            or "in discussion" in notes.lower()
        ):
            email_conv_indices.append((idx, row.get("Company Name"), ls, resp))
            rows[idx]["WhatsApp Status"] = "Handled via Email (In Discussion)"
            continue

        raw_phone = row.get("Phone", "").strip()
        clean_phone = whatsapp_status.clean_phone_number(
            raw_phone, row.get("Country", "")
        )

        if not raw_phone or not clean_phone:
            no_phone_indices.append((idx, row.get("Company Name"), raw_phone))
            rows[idx]["WhatsApp Status"] = "No Phone"
            continue

        # Eligible lead! Generate message
        message, company, first_name = craft_whatsapp_message(row, len(drafts))
        encoded_text = urllib.parse.quote(message)
        wa_link = f"https://wa.me/{clean_phone}?text={encoded_text}"

        draft_record = {
            "row": idx,
            "csv_file": CSV_PATH,
            "company": company,
            "decision_maker": first_name or "Team",
            "phone": raw_phone,
            "clean_phone": clean_phone,
            "country": row.get("Country", ""),
            "city": row.get("City", ""),
            "industry": row.get("Industry", ""),
            "website": row.get("Website", ""),
            "status": "draft",
            "wa_link": wa_link,
            "message": message,
        }
        drafts.append(draft_record)
        queue_items.append(draft_record)
        rows[idx]["WhatsApp Status"] = "Draft"

    print(f"Total leads evaluated: {len(rows)}")
    print(f"Email conversation leads excluded: {len(email_conv_indices)}")
    for item in email_conv_indices:
        print(f"  Row {item[0]}: {item[1]} ({item[2]})")
    print(f"Leads marked 'No Phone': {len(no_phone_indices)}")
    print(f"Drafts generated: {len(drafts)}")

    # Write whatsapp_drafts.md
    today_str = date.today().isoformat()
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(f"# WhatsApp Cold Outreach Drafts — {today_str}\n")
        f.write(f"**Campaign:** Custom Estimating Portals, CRM & Lead Automation  \n")
        f.write(f"**Sender:** {SENDER_NAME} | {SENDER_COMPANY} ({SENDER_EMAIL})  \n")
        f.write(f"**Total Drafts Prepared:** {len(drafts)}  \n")
        f.write(f"**Excluded Email Conversations:** {len(email_conv_indices)} (Landry Electrical Group, Construction Estimating Services Calgary)  \n")
        f.write(f"**Excluded Invalid / Toll-free / No Phone:** {len(no_phone_indices)}  \n")
        f.write(f"*Status: Ready for User Review. No messages have been sent.*\n\n")
        f.write("---\n\n")

        for i, d in enumerate(drafts, 1):
            f.write(f"## {i}. {d['company']}\n")
            f.write(f"- **Recipient:** `{d['clean_phone']}` ({d['decision_maker']})\n")
            f.write(f"- **Location:** {d['city']}, {d['country']} | **Industry:** {d['industry']}\n")
            if d["website"]:
                f.write(f"- **Website:** [{d['website']}]({d['website']})\n")
            f.write(f"- **Direct Link:** [👉 Open WhatsApp Chat with Pre-filled Message]({d['wa_link']})\n\n")
            f.write("```text\n")
            f.write(d["message"] + "\n")
            f.write("```\n\n")
            f.write("---\n\n")

    print(f"Wrote {len(drafts)} drafts to {OUTPUT_MD}")

    # Write whatsapp_queue.json
    with open(OUTPUT_QUEUE, "w", encoding="utf-8") as f:
        json.dump(queue_items, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(queue_items)} records to {OUTPUT_QUEUE}")

    # Save CSV atomically
    whatsapp_status.write_rows(CSV_PATH, fieldnames, rows)
    print(f"Updated {CSV_PATH} atomically.")


if __name__ == "__main__":
    main()
