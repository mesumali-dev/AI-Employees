#!/usr/bin/env python3
"""
Canonical Central Schedule Tracker Manager (Wide Post-Level Schema)
Handles atomic file operations, schema validation, platform-by-platform status updates,
and reconciliation for centralized annual trackers: output/<year>/<client_name>.csv.
12 approved posts = exactly 12 wide data rows.
"""

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent

COMMON_FIELDS = [
    "client_id",
    "year",
    "post_id",
    "post_title",
    "content_draft_path",
    "asset_path",
    "overall_status"
]

PLATFORMS = ["linkedin", "x", "gbp", "facebook", "instagram"]
VALID_PLATFORMS = set(PLATFORMS)

VALID_STATUSES = {
    "NEW",
    "IN_PROGRESS",
    "SCHEDULED_VERIFIED",
    "FAILED",
    "NEEDS_ATTENTION"
}

FIELDNAMES = [
    "client_id",
    "year",
    "post_id",
    "post_title",
    "content_draft_path",
    "asset_path",
    "overall_status",
    # LinkedIn
    "linkedin_scheduled_date",
    "linkedin_scheduled_time",
    "linkedin_timezone",
    "linkedin_status",
    "linkedin_scheduled_timestamp",
    "linkedin_last_verified",
    "linkedin_notes",
    # X (Twitter)
    "x_scheduled_date",
    "x_scheduled_time",
    "x_timezone",
    "x_status",
    "x_scheduled_timestamp",
    "x_last_verified",
    "x_notes",
    # Google Business Profile (GBP)
    "gbp_scheduled_date",
    "gbp_scheduled_time",
    "gbp_timezone",
    "gbp_cta_button_type",
    "gbp_cta_link",
    "gbp_status",
    "gbp_scheduled_timestamp",
    "gbp_last_verified",
    "gbp_notes",
    # Meta Facebook Page
    "facebook_scheduled_date",
    "facebook_scheduled_time",
    "facebook_timezone",
    "facebook_status",
    "facebook_scheduled_timestamp",
    "facebook_last_verified",
    "facebook_notes",
    # Meta Instagram Account
    "instagram_scheduled_date",
    "instagram_scheduled_time",
    "instagram_timezone",
    "instagram_status",
    "instagram_scheduled_timestamp",
    "instagram_last_verified",
    "instagram_notes"
]


def get_canonical_tracker_path(client_name: str = "AEGI", year: int = 2026) -> Path:
    """Returns absolute path to the centralized annual client tracker CSV."""
    return BASE_DIR / "output" / str(year) / f"{client_name}.csv"


def load_tracker(
    csv_path: Optional[Path] = None,
    client_name: str = "AEGI",
    year: int = 2026
) -> List[Dict[str, str]]:
    """Loads tracker CSV into a list of dicts. Raises FileNotFoundError if missing."""
    path = csv_path or get_canonical_tracker_path(client_name=client_name, year=year)
    if not path.exists():
        raise FileNotFoundError(f"Tracker file not found: {path}")

    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k.strip(): (v.strip() if v else "") for k, v in row.items() if k})
    return rows


def save_tracker_atomic(
    rows: List[Dict[str, str]],
    csv_path: Optional[Path] = None,
    client_name: str = "AEGI",
    year: int = 2026
) -> Path:
    """
    Safely writes tracker rows to a temporary file, then atomically renames it.
    Prevents file corruption during interrupted writes.
    """
    target_path = csv_path or get_canonical_tracker_path(client_name=client_name, year=year)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.parent / f".{target_path.name}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for r in rows:
                clean_row = {field: r.get(field, "") for field in FIELDNAMES}
                writer.writerow(clean_row)

        os.replace(temp_path, target_path)
        return target_path
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def validate_tracker(
    rows: List[Dict[str, str]],
    expected_posts: Optional[int] = None
) -> Tuple[bool, List[str]]:
    """
    Validates wide tracker data against business rules:
    - Row count must match expected_posts if specified.
    - Each row must have unique post_id.
    - Common fields must be populated.
    - Platform statuses must be in VALID_STATUSES.
    - Platform dates & times must be populated.
    - Asset path and draft path must exist on disk.
    """
    issues = []
    if expected_posts is not None and len(rows) != expected_posts:
        issues.append(f"ERROR: Expected exactly {expected_posts} posts, found {len(rows)}.")

    seen_pids: Set[str] = set()

    for idx, r in enumerate(rows, start=1):
        cid = r.get("client_id", "")
        yr = r.get("year", "")
        pid = r.get("post_id", "")
        title = r.get("post_title", "")
        asset = r.get("asset_path", "")
        draft = r.get("content_draft_path", "")

        # Required common fields
        if not pid:
            issues.append(f"ERROR: Row {idx} is missing 'post_id'.")
        elif pid in seen_pids:
            issues.append(f"ERROR: Duplicate post_id '{pid}' at row {idx}.")
        else:
            seen_pids.add(pid)

        if not cid:
            issues.append(f"ERROR: Row {idx} (Post '{pid}') is missing 'client_id'.")
        if not yr:
            issues.append(f"ERROR: Row {idx} (Post '{pid}') is missing 'year'.")
        if not title:
            issues.append(f"ERROR: Row {idx} (Post '{pid}') is missing 'post_title'.")

        # Asset path check
        if asset:
            full_asset = BASE_DIR / asset
            if not full_asset.exists():
                issues.append(f"WARNING: Asset file '{asset}' for post '{pid}' does not exist on disk.")

        # Draft path check
        if draft:
            full_draft = BASE_DIR / draft
            if not full_draft.exists():
                issues.append(f"WARNING: Draft file '{draft}' for post '{pid}' does not exist on disk.")

        # Platform-specific validation
        for plat in PLATFORMS:
            st = r.get(f"{plat}_status", "").upper()
            s_date = r.get(f"{plat}_scheduled_date", "")
            s_time = r.get(f"{plat}_scheduled_time", "")

            if not st:
                issues.append(f"ERROR: Row {idx} (Post '{pid}') is missing '{plat}_status'.")
            elif st not in VALID_STATUSES:
                issues.append(f"ERROR: Row {idx} (Post '{pid}') has invalid {plat}_status '{st}'. Must be one of {VALID_STATUSES}.")

            if st != "NEW":
                if not s_date:
                    issues.append(f"ERROR: Row {idx} (Post '{pid}') is missing '{plat}_scheduled_date'.")
                if not s_time:
                    issues.append(f"ERROR: Row {idx} (Post '{pid}') is missing '{plat}_scheduled_time'.")

    has_errors = any(i.startswith("ERROR") for i in issues)
    return not has_errors, issues


def update_platform_batch_status(
    platform: str,
    verified_post_ids: List[str],
    verification_timestamp: str,
    client_name: str = "AEGI",
    year: int = 2026,
    scheduled_timestamp: Optional[str] = None,
    notes_append: str = "",
    csv_path: Optional[Path] = None
) -> Tuple[int, Path]:
    """
    Updates platform-specific columns in the wide CSV after verifying a platform batch.
    Does NOT add or delete rows: exactly 12 rows are preserved.
    Sets <platform>_status=SCHEDULED_VERIFIED and updates last_verified timestamp.
    Updates overall_status to DONE if all 5 platforms are SCHEDULED_VERIFIED, else PARTIAL.
    """
    plat = platform.lower().strip()
    if plat not in VALID_PLATFORMS:
        raise ValueError(f"Unknown platform '{platform}'. Must be one of {VALID_PLATFORMS}")

    target_path = csv_path or get_canonical_tracker_path(client_name=client_name, year=year)
    rows = load_tracker(target_path)
    updated_count = 0

    for r in rows:
        if r.get("post_id") in verified_post_ids:
            r[f"{plat}_status"] = "SCHEDULED_VERIFIED"
            r[f"{plat}_last_verified"] = verification_timestamp
            if scheduled_timestamp:
                r[f"{plat}_scheduled_timestamp"] = scheduled_timestamp
            if notes_append:
                curr_note = r.get(f"{plat}_notes", "")
                r[f"{plat}_notes"] = f"{curr_note}; {notes_append}".strip("; ")

            # Evaluate overall status across all 5 platforms
            all_verified = all(r.get(f"{p}_status") == "SCHEDULED_VERIFIED" for p in PLATFORMS)
            if all_verified:
                r["overall_status"] = "DONE"
            else:
                r["overall_status"] = "PARTIAL"
            updated_count += 1

    saved_path = save_tracker_atomic(rows, target_path)
    return updated_count, saved_path


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    client_name = sys.argv[2] if len(sys.argv) > 2 else "AEGI"
    year = int(sys.argv[3]) if len(sys.argv) > 3 else 2026
    path = get_canonical_tracker_path(client_name=client_name, year=year)

    if action == "status":
        print(f"Loading canonical wide tracker for {client_name} ({year}) from: {path}")
        if not path.exists():
            print("Tracker file does not exist.")
            return 1
        rows = load_tracker(path)
        is_valid, issues = validate_tracker(rows, expected_posts=12 if client_name == "AEGI" else None)
        print(f"\nTotal Posts: {len(rows)} | Validation: {'VALID' if is_valid else 'INVALID'}")
        print("-" * 115)
        print(f"{'Post ID':<10} | {'Overall':<8} | {'LinkedIn Time':<14} | {'X Time':<10} | {'GBP Time':<10} | {'Meta Time':<10} | {'Title':<30}")
        print("-" * 115)
        for r in rows:
            print(f"{r.get('post_id'):<10} | {r.get('overall_status', ''):<8} | {r.get('linkedin_scheduled_time', ''):<14} | {r.get('x_scheduled_time', ''):<10} | {r.get('gbp_scheduled_time', ''):<10} | {r.get('facebook_scheduled_time', ''):<10} | {r.get('post_title', '')[:30]:<30}")
        if issues:
            print("\nIssues:")
            for i in issues:
                print(f"  {i}")
        return 0 if is_valid else 1

    elif action == "validate":
        if not path.exists():
            print(f"Tracker file does not exist: {path}")
            return 1
        rows = load_tracker(path)
        is_valid, issues = validate_tracker(rows, expected_posts=12 if client_name == "AEGI" else None)
        print(f"Validation: {'VALID' if is_valid else 'INVALID'}")
        for i in issues:
            print(f"  {i}")
        return 0 if is_valid else 1

    elif action == "summary":
        if not path.exists():
            print(f"Tracker file does not exist: {path}")
            return 1
        rows = load_tracker(path)
        print(f"Wide Tracker Summary for {client_name} ({year}) - {len(rows)} Posts:")
        for p in PLATFORMS:
            counts = {}
            for r in rows:
                st = r.get(f"{p}_status", "UNKNOWN")
                counts[st] = counts.get(st, 0) + 1
            print(f"  Platform '{p}': {counts}")
        return 0

    else:
        print(f"Unknown action '{action}'. Use 'status', 'validate', or 'summary'.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
