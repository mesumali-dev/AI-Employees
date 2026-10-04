#!/usr/bin/env python3
"""
csv_manager.py — Dedup + append manager for the lead-hunter CSV.

FOCUS
  Every run has a --focus describing the kind of lead being hunted
  (website / chatbot / full). The focus shapes qualification and the pitch
  ONLY — it no longer changes the file or its columns. ALL leads, for every
  focus, accumulate in ONE consolidated month file that uses the website
  header (website-audit data + the four website opportunity scores + shared
  firmographics/contact/narrative columns). A service-specific metric with
  no column (e.g. a chatbot/automation %) belongs in Notes.
  Supported focuses:
      website  (default) — website audit + website-service opportunities
      chatbot            — chatbot/AI/automation opportunity signals
      full               — the entire audit + every opportunity % (generic)
  Omitting --focus = website.

Usage:
  python csv_manager.py resolve <base_dir> [--date YYYY-MM-DD] [--focus website]
      Computes (and creates) the nested month-based directory structure
      under <base_dir> for a given date (default: today) and prints the
      full path to that month's ONE consolidated CSV file:
          <base_dir>/<YYYY>/leads-<mon>.csv    (e.g. leads-jul.csv)
      There is a SINGLE lead file per calendar month shared by every focus
      — no per-focus files (leads-chatbot-jul.csv etc.) are ever created.
      --focus is accepted but does NOT change the filename. Each row's
      'Date Added' column still records the exact date it was added, so the
      data stays date-wise inside the month-wise file. Always call this
      first to get the CSV path for the run — don't hand-construct the path.

  python csv_manager.py init <csv_path> [--focus website]
      Create the CSV with that focus's header if it doesn't already exist.

  python csv_manager.py check <csv_path> --company "..." --website "..." \
      --business-email "..." --owner-email "..." --phone "..."
      Prints DUPLICATE or UNIQUE. Exit code 1 if duplicate, 0 if unique.
      NOTE: only checks the single CSV passed in. To check against every
      lead ever collected (not just today's file), use `check-all` instead.

  python csv_manager.py check-all <base_dir> --company "..." --website "..." \
      --business-email "..." --owner-email "..." --phone "..."
      Same as `check`, but scans every leads-*.csv file nested under
      <base_dir> (all months), so a business found today isn't re-added
      just because it was already captured in a previous month.

  python csv_manager.py append <csv_path> <lead_json_path> [--base-dir <base_dir>] [--focus website] [--allow-no-email] [--requested-for "Website"]
      Appends a single lead (JSON object keyed by column name) to the CSV,
      after two gates:
        1. EMAIL gate — a lead with no 'Business Email' AND no 'Owner Email'
           is skipped (exit 2, prints NO_EMAIL). Only leads we can actually
           email get written. Pass --allow-no-email for phone-only campaigns.
        2. DUPLICATE gate — refuses (exit 1, prints DUPLICATE) if the lead
           matches an existing one.
      Fills 'Date Added' with today's date if not already set. Never
      reorders or overwrites existing rows — always appends at the bottom.
      The file's own header decides its columns: any lead-JSON keys that
      aren't columns of this file are dropped, so a stray chatbot/CRM %
      never appears (put such metrics in Notes). A brand-new month file is
      always created with the consolidated (website) header regardless of
      --focus, so every month file shares one stable schema.
      --requested-for "<tag>" fills the "Requested For" column (what the
      USER asked for this run, e.g. "Website"/"Chatbot"/"Mobile App") when
      the lead JSON didn't set it. Pass the SAME tag for every lead in a
      run so rows group cleanly by the original request.
      Pass --base-dir (the root of the nested date-directory tree) to
      check the duplicate against ALL dates, not just today's file —
      recommended whenever you're using the resolve-based dated layout.

This script is the single source of truth for the column order — always
create/append through it rather than hand-writing CSV rows, so the header
never drifts.
"""

import csv
import glob
import json
import os
import re
import sys
from datetime import date

# The CSV is FOCUS-AWARE. Every run has a "focus" — the kind of lead being
# hunted — and each focus writes ONLY the columns relevant to it, so a
# "website leads" run never carries empty CRM/ERP/chatbot/HRM columns.
#
# A row is always:  COMMON_HEAD  +  <focus columns>  +  COMMON_TAIL
# The head (who the business is) and tail (contact + qualification + pitch)
# are shared by every focus; only the middle audit/opportunity block
# changes per focus.

COMMON_HEAD = [
    "Date Added", "Requested For", "Company Name", "Industry", "Country",
    "State", "City", "Business Size", "Website", "Website Status",
    "Technology",
]
# "Requested For" = what the USER asked for when triggering the run (the
# campaign intent, e.g. "Website", "Chatbot", "Mobile App"). Set ONCE per run
# from the user's own wording, applied to every row — NOT inferred from the
# site. Distinct from "Opportunity Type" (what the AI found the site needs).

# Note the column pair right after the per-focus scores:
#   Opportunity Type    — comma-separated tags from OPPORTUNITY_TYPES (what to
#                         sell). This is where "needs a chatbot / CRM / booking"
#                         lives — NOT in Problems Found.
#   Opportunity Benefit — one specific, non-boilerplate sentence on what the
#                         client gains from those opportunities.
# Contact columns are trimmed to the ones actually findable for small firms:
# Business Email + Owner Email + Phone (no Sales/Support/WhatsApp), and only the
# social channels that are reliably present for B2B (Facebook/Instagram/LinkedIn;
# no Twitter/YouTube).
COMMON_TAIL = [
    "Opportunity Type", "Opportunity Benefit",
    "Decision Maker", "Position", "Business Email", "Owner Email",
    "Phone", "Address", "Google Rating", "Reviews", "Facebook",
    "Instagram", "LinkedIn", "Services", "USP", "Suggested Pitch",
    "Cold Email", "Priority", "Estimated Budget",
    "Decision Maker Probability", "Lead Status", "WhatsApp Status",
    "Date Contacted", "Follow-up Date", "Response", "Notes", "Source",
    "Contact Page",
    "Contact Quality", "Email Validation Status", "Opportunity Confidence",
    "Primary Opportunity", "Evidence", "Recommended Service",
    "Opportunity Status", "Skip Reason", "Email QA Status",
]

# Obvious dummy / placeholder patterns to reject automatically
DUMMY_EMAIL_PATTERNS = [
    r"^wordpress@",
    r"^user@",
    r"^email@",
    r"^info@mysite\.com",
    r"^test@",
    r"^example@",
    r"@yourdomain\.",
    r"@domain\.",
    r"@example\.",
    r"@email\.com$",
    r"@mysite\.",
    r"@sentry\.",
    r"@wix\.",
    r"@squarespace\.",
]

def is_dummy_email(email: str) -> bool:
    if not email:
        return True
    em = email.strip().lower()
    return any(re.search(pat, em) for pat in DUMMY_EMAIL_PATTERNS)


# Fixed, filterable vocabulary for the "Opportunity Type" column. Keep tags to
# THIS list so the column stays filterable — add a tag here rather than
# inventing ad-hoc ones. Each tag names a service the operator can sell.
OPPORTUNITY_TYPES = [
    "Website Redesign", "Next.js Rebuild", "Performance", "Security", "SEO",
    "Branding", "Mobile Optimization", "Lead Capture", "Booking System",
    "Analytics", "Content/Blog", "E-commerce", "Online Payments",
    "Customer Portal", "CRM", "HRM System", "Inventory System",
    "Quotation & Invoicing", "Custom Software", "Automation",
    "AI Chatbot", "Web App", "Mobile App",
]

# Middle block per focus. Add a new focus by adding an entry here.
#
# The "* %" columns are OPPORTUNITY-CONFIDENCE scores, 0–100: how strong the
# evidence is that this business needs (and would buy) that service. They are
# NOT severity grades and NOT random filler — they're computed from concrete
# site evidence per the rubric in references/analysis_criteria.md, and every
# focus column gets a number every time (0 if there's genuinely no signal, so
# the column is never silently blank). Problems Found stays audit-only:
# real technical defects, never "no chatbot / no CRM".
FOCUS_COLUMNS = {
    # Consolidated header (used for the single month file, every focus):
    # website-audit facts + the four website opportunity scores + the
    # chatbot/automation opportunity scores, so a chatbot run has real
    # columns for its signal instead of burying it in Notes.
    "website": [
        "HTTPS", "SSL", "Mobile Friendly", "Loading Speed",
        "Overall Score", "Problems Found", "Website Redesign %",
        "Security %", "SEO %", "Branding %",
        "AI Chatbot %", "Automation %",
    ],
    # Chatbot leads: the chatbot/AI/automation opportunity-confidence scores.
    "chatbot": [
        "Problems Found", "AI Chatbot %", "Automation %",
    ],
    # Generic run (no single service): the full audit + every opportunity score.
    "full": [
        "HTTPS", "SSL", "Mobile Friendly", "Loading Speed",
        "Overall Score", "Problems Found",
        "Website Redesign %", "Web App %", "Mobile App %", "CRM %",
        "Booking System %", "Customer Portal %", "AI Chatbot %",
        "Automation %", "Security %", "SEO %", "Branding %",
    ],
}

DEFAULT_FOCUS = "website"


def columns_for(focus=DEFAULT_FOCUS):
    """Return the full ordered column list for a given focus."""
    middle = FOCUS_COLUMNS.get(focus, FOCUS_COLUMNS["full"])
    return COMMON_HEAD + middle + COMMON_TAIL


# Backwards-compatible alias: the full superset of every column.
COLUMNS = columns_for("full")

DEDUP_FIELDS = ["Company Name", "Website", "Business Email", "Owner Email", "Phone"]
EMAIL_FIELDS = ["Business Email", "Owner Email"]


def _norm(value):
    """Normalize a field for fuzzy-but-safe duplicate comparison."""
    if not value:
        return ""
    v = value.strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^www\.", "", v)
    v = v.rstrip("/")
    v = re.sub(r"[\s\-\(\)]", "", v) if v and any(c.isdigit() for c in v) else v
    return v


MONTH_ABBR = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]


def resolve_dated_path(base_dir, for_date=None, focus=DEFAULT_FOCUS):
    """
    Ensures <base_dir>/<YYYY>/ exists (creating the directory if needed)
    and returns the path to that month's ONE consolidated CSV:
        <base_dir>/<YYYY>/leads-<mon>.csv   (e.g. leads-jul.csv)

    There is a SINGLE lead file per calendar month, shared by every focus
    (website / chatbot / booking / ...). The `focus` argument no longer
    changes the filename — it only affects the header when a brand-new
    file has to be created (see columns_for). This deliberately prevents
    per-focus files like leads-chatbot-jul.csv from ever being created;
    all leads accumulate in the consolidated month file. The exact day is
    preserved per-row in the 'Date Added' column, so the file stays
    month-wise while the data inside it remains date-wise.
    """
    d = for_date or date.today()
    year_dir = os.path.join(base_dir, f"{d.year:04d}")
    os.makedirs(year_dir, exist_ok=True)
    mon = MONTH_ABBR[d.month - 1]
    return os.path.join(year_dir, f"leads-{mon}.csv")


def all_dated_csvs(base_dir):
    """Finds every leads-*.csv nested anywhere under base_dir."""
    return sorted(glob.glob(os.path.join(base_dir, "**", "leads-*.csv"), recursive=True))


def load_existing_keys_multi(paths):
    """Same as load_existing_keys but merged across multiple CSV files."""
    keys = {field: set() for field in DEDUP_FIELDS}
    for p in paths:
        for field, vals in load_existing_keys(p).items():
            keys[field] |= vals
    return keys


def is_duplicate_multi(base_dir, candidate):
    paths = all_dated_csvs(base_dir)
    existing = load_existing_keys_multi(paths)
    for field in DEDUP_FIELDS:
        val = _norm(candidate.get(field, ""))
        if val and val in existing[field]:
            return True, field
    return False, None


def _header_of(path):
    """Return the existing header row of a CSV, or None if it has none."""
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            return row
    return None


def init_csv(path, focus=DEFAULT_FOCUS):
    if os.path.exists(path):
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns_for(focus))


def load_existing_keys(path):
    """Returns a dict: field_name -> set of normalized existing values."""
    keys = {field: set() for field in DEDUP_FIELDS}
    if not os.path.exists(path):
        return keys
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in DEDUP_FIELDS:
                val = _norm(row.get(field, ""))
                if val:
                    keys[field].add(val)
    return keys


def is_duplicate(path, candidate):
    """candidate: dict with keys possibly including DEDUP_FIELDS."""
    existing = load_existing_keys(path)
    for field in DEDUP_FIELDS:
        val = _norm(candidate.get(field, ""))
        if val and val in existing[field]:
            return True, field
    return False, None


def _has_email(lead: dict) -> bool:
    for f in EMAIL_FIELDS:
        val = lead.get(f, "").strip()
        if val and not is_dummy_email(val):
            return True
    return False


def append_lead(path, lead: dict, base_dir=None, focus=DEFAULT_FOCUS,
                require_email=True, requested_for=None):
    # Email gate: only worth appending a lead we can actually email. A lead
    # with no Business Email AND no Owner Email (or only dummy placeholder emails)
    # is skipped so it never becomes a dead, un-contactable row.
    if require_email and not _has_email(lead):
        print("NO_EMAIL_OR_DUMMY (no valid non-dummy Business Email or Owner Email — skipped)")
        sys.exit(2)

    # Opportunity Confidence Gate:
    # A lead with an Opportunity Confidence below 60 is skipped unless explicitly allowed.
    conf = lead.get("Opportunity Confidence")
    if conf is not None and str(conf).strip():
        try:
            conf_val = float(conf)
            if conf_val < 60 and lead.get("Opportunity Status") != "Force Include":
                print(f"LOW_CONFIDENCE (Opportunity Confidence {conf_val} is below threshold 60 — skipped)")
                sys.exit(3)
        except ValueError:
            pass

    # Consolidated month file: a brand-new file ALWAYS gets the consolidated
    # (website) header, whatever --focus was passed, so every month file
    # shares one stable schema. `focus` only shapes qualification/pitch
    # upstream, never the columns here.
    init_csv(path, focus=DEFAULT_FOCUS)
    # The file's own header is the source of truth for its columns. Any keys
    # in the lead JSON that aren't columns of THIS file are simply dropped —
    # e.g. a chatbot/automation % has no column and won't appear (record it
    # in Notes instead).
    cols = _header_of(path) or columns_for(DEFAULT_FOCUS)

    if base_dir:
        dup, field = is_duplicate_multi(base_dir, lead)
    else:
        dup, field = is_duplicate(path, lead)
    if dup:
        print(f"DUPLICATE (matched on {field})")
        sys.exit(1)

    row = {col: lead.get(col, "") for col in cols}
    if "Date Added" in row and not row["Date Added"]:
        row["Date Added"] = date.today().isoformat()
    if "Lead Status" in row and not row["Lead Status"]:
        row["Lead Status"] = "New"
    if "WhatsApp Status" in row and not row["WhatsApp Status"]:
        row["WhatsApp Status"] = "New"
    # --requested-for fills the run-level intent tag when the lead JSON
    # didn't already carry it. Explicit value in the JSON wins.
    if requested_for and "Requested For" in row and not row["Requested For"]:
        row["Requested For"] = requested_for

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writerow(row)
    print("APPENDED")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)

    cmd, path = sys.argv[1], sys.argv[2]

    if cmd == "resolve":
        for_date = None
        focus = DEFAULT_FOCUS
        args = sys.argv[3:]
        it = iter(args)
        for a in it:
            if a == "--date":
                for_date = date.fromisoformat(next(it))
            elif a == "--focus":
                focus = next(it)
        print(resolve_dated_path(path, for_date, focus=focus))

    elif cmd == "init":
        focus = DEFAULT_FOCUS
        it = iter(sys.argv[3:])
        for a in it:
            if a == "--focus":
                focus = next(it)
        init_csv(path, focus=focus)
        print(f"Initialized {path}")

    elif cmd == "check":
        args = sys.argv[3:]
        candidate = {}
        it = iter(args)
        for a in it:
            if a == "--company":
                candidate["Company Name"] = next(it)
            elif a == "--website":
                candidate["Website"] = next(it)
            elif a == "--business-email":
                candidate["Business Email"] = next(it)
            elif a == "--owner-email":
                candidate["Owner Email"] = next(it)
            elif a == "--phone":
                candidate["Phone"] = next(it)
        dup, field = is_duplicate(path, candidate)
        if dup:
            print(f"DUPLICATE (matched on {field})")
            sys.exit(1)
        print("UNIQUE")

    elif cmd == "check-all":
        args = sys.argv[3:]
        candidate = {}
        it = iter(args)
        for a in it:
            if a == "--company":
                candidate["Company Name"] = next(it)
            elif a == "--website":
                candidate["Website"] = next(it)
            elif a == "--business-email":
                candidate["Business Email"] = next(it)
            elif a == "--owner-email":
                candidate["Owner Email"] = next(it)
            elif a == "--phone":
                candidate["Phone"] = next(it)
        dup, field = is_duplicate_multi(path, candidate)
        if dup:
            print(f"DUPLICATE (matched on {field})")
            sys.exit(1)
        print("UNIQUE")

    elif cmd == "append":
        lead_json_path = sys.argv[3]
        base_dir = None
        focus = DEFAULT_FOCUS
        require_email = True
        requested_for = None
        rest = sys.argv[4:]
        it = iter(rest)
        for a in it:
            if a == "--base-dir":
                base_dir = next(it)
            elif a == "--focus":
                focus = next(it)
            elif a == "--allow-no-email":
                require_email = False
            elif a == "--requested-for":
                requested_for = next(it)
        with open(lead_json_path, encoding="utf-8") as f:
            lead = json.load(f)
        append_lead(path, lead, base_dir=base_dir, focus=focus,
                    require_email=require_email, requested_for=requested_for)

    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()