#!/usr/bin/env python3
"""
Automated Test Suite for Publishing Safeguards & Scenarios
Validates Scenarios 1 through 6, 12-Row Wide CSV Architecture,
Atomic Persistence, Multi-Client Annual Structure, and Backup Removal offline.
"""

import copy
import glob
import json
import re
import sys
import tempfile
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.config_loader import load_client_config, validate_client_config
from scripts.publish_guard import (
    ClientIsolationError,
    build_per_platform_tracker,
    check_and_prevent_duplicates,
    recover_changed_url,
    verify_platform_identity,
)
from scripts.tracker_manager import (
    FIELDNAMES,
    PLATFORMS,
    VALID_PLATFORMS,
    VALID_STATUSES,
    get_canonical_tracker_path,
    load_tracker,
    save_tracker_atomic,
    update_platform_batch_status,
    validate_tracker,
)


def run_tests():
    passed = 0
    failed = 0
    total = 0

    def assert_true(condition, name, details=""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name} {f'({details})' if details else ''}")
        else:
            failed += 1
            print(f"  [FAIL] {name} {f'({details})' if details else ''}")

    print("======================================================================")
    print("RUNNING AUTOMATED PUBLISHING SAFEGUARDS TEST SUITE")
    print("======================================================================")

    # -------------------------------------------------------------------------
    # TEST 1: SCENARIO 1 - Config, Cadence, Timezone & Media Match
    # -------------------------------------------------------------------------
    print("\n--- Test Group 1: Scenario 1 - Client Configuration & Schedule ---")
    try:
        config = load_client_config("AEGI")
        assert_true(config["client_info"]["client_id"] == "AEGI", "Client ID matches 'AEGI'")
        assert_true(config["scheduling"]["timezone"] == "Asia/Karachi", "Authoritative timezone is Asia/Karachi (PKT)")
        assert_true(config["scheduling"]["preferred_time_range"] == ["13:00", "19:00"], "Posting window is strictly 1:00 PM - 7:00 PM")
        assert_true(config["scheduling"]["posting_cadence"] == "MWF", "Posting cadence is MWF")

        # Verify all 12 asset files exist
        media_pattern = config["media"]["naming_pattern"]
        assets_found = 0
        for i in range(1, 13):
            asset_path = ROOT_DIR / media_pattern.format(number=i)
            if asset_path.exists():
                assets_found += 1
        assert_true(assets_found == 12, f"All 12 graphic assets exist on disk ({assets_found}/12)")
    except Exception as e:
        assert_true(False, "Scenario 1 Config Loading", str(e))

    # -------------------------------------------------------------------------
    # TEST 2: SCENARIO 2 - Changed URL Detection & Recovery
    # -------------------------------------------------------------------------
    print("\n--- Test Group 2: Scenario 2 - URL Change Detection & Recovery ---")
    rec_ok, url_ok, msg_ok = recover_changed_url(
        "linkedin",
        "https://www.linkedin.com/company/82538927/admin/page-posts/published/?view=feed",
        config
    )
    assert_true(rec_ok, "Valid LinkedIn redirect recognized", msg_ok)

    rec_bad, fallback_url, msg_bad = recover_changed_url(
        "linkedin",
        "https://www.linkedin.com/feed/?random_param=1",
        config
    )
    assert_true(not rec_bad and "82538927" in fallback_url, "Broken redirect caught & reset to verified fallback", fallback_url)

    rec_meta, meta_url, meta_msg = recover_changed_url(
        "meta_business_suite",
        "https://business.facebook.com/latest/composer/?asset_id=105588968926476",
        config
    )
    assert_true(rec_meta, "Meta Business Suite asset ID preserved during redirect", meta_msg)

    # -------------------------------------------------------------------------
    # TEST 3: SCENARIO 3 - Cross-Client Account Isolation Guard
    # -------------------------------------------------------------------------
    print("\n--- Test Group 3: Scenario 3 - Client Isolation Protection ---")
    li_ok, li_msg = verify_platform_identity(
        "linkedin",
        "https://www.linkedin.com/company/82538927/admin/page-posts/published/",
        "(19) Advanced Engineering Group Inc.: Company Page Admin | LinkedIn",
        "Advanced Engineering Group Inc.",
        config
    )
    assert_true(li_ok, "LinkedIn AEGI Identity Confirmed", li_msg)

    li_wrong, li_wrong_msg = verify_platform_identity(
        "linkedin",
        "https://www.linkedin.com/company/99999999/admin/page-posts/published/",
        "Other Client Corp Admin | LinkedIn",
        "Other Client Corp",
        config
    )
    assert_true(not li_wrong, "BLOCKED: Wrong LinkedIn client account rejected", li_wrong_msg)

    meta_wrong, meta_wrong_msg = verify_platform_identity(
        "meta_business_suite",
        "https://business.facebook.com/latest/posts/scheduled_posts?asset_id=9876543210",
        "Other Brand Page | Meta Business Suite",
        "Other Brand Page",
        config
    )
    assert_true(not meta_wrong, "BLOCKED: Wrong Meta Business Suite asset rejected", meta_wrong_msg)

    gbp_wrong, gbp_wrong_msg = verify_platform_identity(
        "google_business_profile",
        "https://www.google.com/search?q=Other+Business#mpd=~111122223333/promote",
        "Other Business - Google Search",
        "Other Business",
        config
    )
    assert_true(not gbp_wrong, "BLOCKED: Wrong Google Business Profile rejected", gbp_wrong_msg)

    # -------------------------------------------------------------------------
    # TEST 4: SCENARIO 4 - Missing, Broken, or Conflicting Configuration
    # -------------------------------------------------------------------------
    print("\n--- Test Group 4: Scenario 4 - Config Validation & Conflict Detection ---")
    broken_cfg = copy.deepcopy(config)
    del broken_cfg["client_info"]["client_name"]
    is_valid_b1, issues_b1 = validate_client_config(broken_cfg)
    assert_true(not is_valid_b1 and any("client_name" in i for i in issues_b1), "Catches missing required client_name")

    broken_cfg2 = copy.deepcopy(config)
    broken_cfg2["scheduling"]["preferred_time_range"] = ["18:00"]
    is_valid_b2, issues_b2 = validate_client_config(broken_cfg2)
    assert_true(not is_valid_b2 and any("preferred_time_range" in i for i in issues_b2), "Catches malformed time range")

    # -------------------------------------------------------------------------
    # TEST 5: SCENARIO 5 - Failure Mid-Way, Duplicate Prevention & Resumption
    # -------------------------------------------------------------------------
    print("\n--- Test Group 5: Scenario 5 - Mid-Way Failure & Resumption Protocol ---")
    mock_posts = [
        {"post_id": f"post_{i:02d}", "post_title": f"Title {i}", "scheduled_date": f"2026-10-{12+i*2}", "scheduled_time": "14:15"}
        for i in range(1, 13)
    ]
    tracker = build_per_platform_tracker(mock_posts, ["linkedin", "x", "gbp", "facebook", "instagram"])
    assert_true(len(tracker) == 60, f"Granular tracker initialized 60 placements ({len(tracker)}/60)")

    for entry in tracker:
        if entry["platform"] == "linkedin":
            entry["status"] = "Scheduled — verified"
            entry["verified_timestamp"] = "2026-10-11T20:00:00"
        elif entry["platform"] == "x" and entry["post_id"] in ["post_01", "post_02", "post_03"]:
            entry["status"] = "Scheduled — verified"
            entry["verified_timestamp"] = "2026-10-11T20:10:00"
        elif entry["platform"] == "x" and entry["post_id"] == "post_04":
            entry["status"] = "Failed"
            entry["failure_reason"] = "Upload timeout on media preview"

    actionable = [e for e in tracker if e["status"] in ["Pending", "Failed"]]
    completed = [e for e in tracker if e["status"] == "Scheduled — verified"]
    assert_true(len(completed) == 15, f"Resumption correctly identifies 15 verified items ({len(completed)}/15)")
    assert_true(len(actionable) == 45, f"Resumption isolates 45 remaining items without re-running verified ({len(actionable)}/45)")

    simulated_live_x_queue = [
        {"time": "Will send on Mon, Oct 12, 2026 at 2:15 PM", "text": "Planning an expansion?"},
        {"time": "Will send on Wed, Oct 14, 2026 at 3:30 PM", "text": "Is an older building fit?"},
    ]
    is_dup, dup_msg = check_and_prevent_duplicates("post_01", "x", "Oct 12", "14:15", simulated_live_x_queue)
    assert_true(is_dup, "Duplicate Prevention: Correctly detects already-scheduled item in live queue", dup_msg)

    is_not_dup, _ = check_and_prevent_duplicates("post_04", "x", "Oct 19", "16:20", simulated_live_x_queue)
    assert_true(not is_not_dup, "Duplicate Prevention: Allows scheduling unseen item")

    # -------------------------------------------------------------------------
    # TEST 6: SCENARIO 6 - Content Structure & Character Constraints (< 260)
    # -------------------------------------------------------------------------
    print("\n--- Test Group 6: Scenario 6 - Content Structure & Character Constraints ---")
    draft_files = sorted(glob.glob(str(ROOT_DIR / "Posts" / "AEGI" / "post_*_draft.md")))
    assert_true(len(draft_files) == 12, f"Found 12 post drafts ({len(draft_files)}/12)")

    all_contacts_present = True
    all_x_under_260 = True
    max_tweet_len = 0

    for df in draft_files:
        with open(df, "r", encoding="utf-8") as f:
            content = f.read()

        if not ("(587) 489-5781" in content and "info@aegi.ca" in content and "www.aegi.ca" in content):
            all_contacts_present = False

        m = re.search(r"## 3\. X \(Twitter\)\s*\n(.*?)(?=\n\n\*(?:Character Count|---)|\n---)", content, re.DOTALL)
        if m:
            t_len = len(m.group(1).strip())
            max_tweet_len = max(max_tweet_len, t_len)
            if t_len >= 260:
                all_x_under_260 = False

    assert_true(all_contacts_present, "All 12 drafts contain required Contact Us block (Phone, Email, Web)")
    assert_true(all_x_under_260, f"All 12 X versions are strictly under 260 characters (Max: {max_tweet_len})")

    # -------------------------------------------------------------------------
    # TEST 7: 12-ROW WIDE CANONICAL CSV ARCHITECTURE & BATCH PERSISTENCE
    # -------------------------------------------------------------------------
    print("\n--- Test Group 7: 12-Row Wide Canonical CSV Architecture ---")
    tracker_path = get_canonical_tracker_path("AEGI", 2026)
    assert_true(tracker_path.exists(), f"Canonical CSV exists at {tracker_path.relative_to(ROOT_DIR)}")

    canonical_rows = load_tracker(tracker_path)
    # Rule 1: Exactly 12 data rows
    assert_true(len(canonical_rows) == 12, f"Canonical tracker has exactly 12 data rows ({len(canonical_rows)}/12)")

    # Rule 2: Exactly 12 unique post IDs
    unique_pids = set(r.get("post_id") for r in canonical_rows)
    assert_true(len(unique_pids) == 12, f"Exactly 12 unique post IDs ({len(unique_pids)}/12)")

    # Rule 3: Strict schema validation passes
    is_valid_csv, csv_issues = validate_tracker(canonical_rows, expected_posts=12)
    assert_true(is_valid_csv, "Canonical tracker passed strict schema validation", str(csv_issues))

    # Rule 4: All 60 placements individually represented across columns
    total_verified_placements = 0
    for r in canonical_rows:
        for p in PLATFORMS:
            if r.get(f"{p}_status") == "SCHEDULED_VERIFIED":
                total_verified_placements += 1
    assert_true(total_verified_placements == 60, f"All 60 placements individually verified in columns ({total_verified_placements}/60)")

    # Rule 5: Preserves Post 04 scheduling difference across platforms
    post_04 = next(r for r in canonical_rows if r.get("post_id") == "post_04")
    li_t4 = post_04.get("linkedin_scheduled_time")
    x_t4 = post_04.get("x_scheduled_time")
    gbp_t4 = post_04.get("gbp_scheduled_time")
    fb_t4 = post_04.get("facebook_scheduled_time")
    ig_t4 = post_04.get("instagram_scheduled_time")
    assert_true(
        li_t4 == "15:30" and x_t4 == "16:20" and gbp_t4 == "16:20" and fb_t4 == "16:20" and ig_t4 == "16:20",
        f"Post 04 platform schedule differences preserved (LinkedIn: {li_t4}, X/GBP/Meta: {x_t4})"
    )

    # Rule 6: Atomic save and reload round-trips 12 rows cleanly
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        saved_p = save_tracker_atomic(canonical_rows, tmp_path)
        reloaded = load_tracker(saved_p)
        assert_true(len(reloaded) == 12, "Atomic CSV save and reload round-trips 12 rows cleanly")

        # Rule 7: Platform status can be updated independently without adding rows
        reloaded[0]["linkedin_status"] = "NEW"
        reloaded[0]["linkedin_last_verified"] = ""
        save_tracker_atomic(reloaded, tmp_path)

        up_cnt, _ = update_platform_batch_status(
            platform="linkedin",
            verified_post_ids=[reloaded[0]["post_id"]],
            verification_timestamp="2026-10-12T00:25:00+05:00",
            notes_append="Automated batch test verification",
            csv_path=tmp_path
        )
        post_update_rows = load_tracker(tmp_path)
        assert_true(len(post_update_rows) == 12, f"Row count remains strictly 12 after batch update ({len(post_update_rows)}/12)")
        assert_true(post_update_rows[0]["linkedin_status"] == "SCHEDULED_VERIFIED", "Updated platform status is SCHEDULED_VERIFIED")

        # Rule 8: Duplicate post rejection
        dup_test_rows = copy.deepcopy(reloaded)
        dup_test_rows.append(copy.deepcopy(dup_test_rows[0]))
        is_dup_valid, dup_issues = validate_tracker(dup_test_rows)
        assert_true(not is_dup_valid and any("Duplicate post_id" in i for i in dup_issues),
                    "Security Rule: Duplicate post_id rejected during validation")

        # Rule 9: Invalid status rejection
        bad_status_rows = copy.deepcopy(reloaded)
        bad_status_rows[0]["linkedin_status"] = "INVALID_STATUS"
        is_bad_valid, bad_issues = validate_tracker(bad_status_rows)
        assert_true(not is_bad_valid and any("invalid linkedin_status" in i for i in bad_issues),
                    "Security Rule: Invalid platform status rejected during validation")

    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # -------------------------------------------------------------------------
    # TEST 8: MULTI-CLIENT ANNUAL STRUCTURE & BACKUP REMOVAL VERIFICATION
    # -------------------------------------------------------------------------
    print("\n--- Test Group 8: Multi-Client Isolation & Backup Removal ---")
    output_2026 = ROOT_DIR / "output" / "2026"
    assert_true(output_2026.exists() and output_2026.is_dir(), "Directory output/2026/ exists")

    al_abbas_path = get_canonical_tracker_path("AL Abbas", 2026)
    assert_true(al_abbas_path.exists(), f"AL Abbas 2026 tracker initialized at {al_abbas_path.name}")
    al_abbas_rows = load_tracker(al_abbas_path)
    is_al_valid, _ = validate_tracker(al_abbas_rows)
    assert_true(is_al_valid, "AL Abbas tracker passes wide schema validation")

    cortech_path = get_canonical_tracker_path("Cortech Solution", 2026)
    assert_true(cortech_path.exists(), f"Cortech Solution 2026 tracker initialized at {cortech_path.name}")
    cortech_rows = load_tracker(cortech_path)
    is_cortech_valid, _ = validate_tracker(cortech_rows)
    assert_true(is_cortech_valid, "Cortech Solution tracker passes wide schema validation")

    # Rule 10: Verify backup directory does not exist and no code depends on it
    backup_dir = ROOT_DIR / "backups"
    assert_true(not backup_dir.exists(), "Verification: backups/ directory removed and absent")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n======================================================================")
    print(f"TEST SUITE COMPLETE: {passed}/{total} Passed, {failed} Failed.")
    print("======================================================================")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_tests())
