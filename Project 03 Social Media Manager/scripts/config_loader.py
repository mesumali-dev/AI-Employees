#!/usr/bin/env python3
"""
Client Configuration Loader & Validator
Loads and validates Posts/<client_name>/client_config.json for social media management workflows.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent


def get_client_config_path(client_name: str) -> Path:
    """Return the absolute path to a client's configuration file."""
    return BASE_DIR / "Posts" / client_name / "client_config.json"


def load_client_config(client_name: str) -> Dict[str, Any]:
    """
    Load client configuration JSON.
    Raises FileNotFoundError or json.JSONDecodeError if invalid.
    """
    path = get_client_config_path(client_name)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found for client '{client_name}': {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def validate_client_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate required fields and constraints in the client configuration.
    Returns (is_valid, list_of_errors_or_warnings).
    """
    issues = []

    # 1. Client Info
    client_info = config.get("client_info")
    if not client_info:
        issues.append("ERROR: 'client_info' block is missing.")
    else:
        for field in ["client_id", "client_name", "website"]:
            if not client_info.get(field):
                issues.append(f"ERROR: 'client_info.{field}' is required and cannot be empty.")

    # 2. Scheduling
    sched = config.get("scheduling")
    if not sched:
        issues.append("ERROR: 'scheduling' block is missing.")
    else:
        tz = sched.get("timezone")
        if not tz:
            issues.append("ERROR: 'scheduling.timezone' is required.")
        time_range = sched.get("preferred_time_range")
        if not time_range or len(time_range) != 2:
            issues.append("ERROR: 'scheduling.preferred_time_range' must be a list of [start, end] in HH:MM.")

    # 3. Platforms
    platforms = config.get("platforms")
    if not platforms:
        issues.append("ERROR: 'platforms' block is missing.")
    else:
        for p in ["linkedin", "meta_business_suite", "x", "google_business_profile"]:
            if p not in platforms:
                issues.append(f"WARNING: Platform '{p}' is not defined in 'platforms'.")

    # 4. CTA Links
    cta = config.get("cta_links")
    if not cta:
        issues.append("ERROR: 'cta_links' block is missing.")
    else:
        primary = cta.get("primary", {})
        if not primary.get("quote"):
            issues.append("ERROR: 'cta_links.primary.quote' is missing.")
        if not primary.get("contact"):
            issues.append("ERROR: 'cta_links.primary.contact' is missing.")

    # 5. Hashtags
    hashtags = config.get("hashtags_and_mentions")
    if not hashtags:
        issues.append("ERROR: 'hashtags_and_mentions' block is missing.")
    else:
        if not hashtags.get("brand_hashtags"):
            issues.append("WARNING: 'brand_hashtags' is empty or missing.")

    # 6. Media
    media = config.get("media")
    if not media:
        issues.append("ERROR: 'media' block is missing.")
    else:
        for field in ["base_dir", "naming_pattern", "aspect_ratio"]:
            if not media.get(field):
                issues.append(f"ERROR: 'media.{field}' is required.")

    has_errors = any(i.startswith("ERROR") for i in issues)
    return not has_errors, issues


def main():
    client_name = sys.argv[1] if len(sys.argv) > 1 else "AEGI"
    print(f"Loading configuration for client: '{client_name}'...")
    try:
        config = load_client_config(client_name)
        is_valid, issues = validate_client_config(config)

        print("\n--- Validation Report ---")
        if is_valid:
            print("Status: VALID (No critical errors detected)")
        else:
            print("Status: INVALID (Critical errors detected)")

        if issues:
            for item in issues:
                print(f" - {item}")
        else:
            print(" - All required fields and constraints passed.")

        # Quick summary printout
        client_info = config.get("client_info", {})
        sched = config.get("scheduling", {})
        print("\n--- Summary ---")
        print(f"Client Name:       {client_info.get('client_name')}")
        print(f"Authoritative TZ:  {sched.get('timezone')} ({sched.get('timezone_label')})")
        print(f"Posting Cadence:   {sched.get('posting_cadence')} (Days: {', '.join(sched.get('posting_days', []))})")
        print(f"Time Range:        {sched.get('preferred_time_range')}")
        print(f"Primary Quote URL: {config.get('cta_links', {}).get('primary', {}).get('quote')}")
        print(f"Media Ratio:       {config.get('media', {}).get('aspect_ratio')}")
        return 0 if is_valid else 1

    except Exception as e:
        print(f"\nFailed to load configuration: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
