# Project 03: Social Media Manager (Multi-Client Architecture)

Production-ready, client-isolated social media management workspace for **Advanced Engineering Group Inc. (AEGI)** and other managed clients across LinkedIn, X (Twitter), Google Business Profile, Facebook, and Instagram.

---

## 1. Workspace Directory Structure

```text
Project 03 Social Media Manager/
├── README.md                                # Operations manual & architectural specification
├── .agents/
│   └── skills/
│       ├── social-post-drafter/SKILL.md      # Analytics-first research & drafting skill
│       ├── social-post-publisher/SKILL.md    # Platform batch execution skill
│       └── skill-creator/                    # Skill benchmarking & authoring framework
├── .playwright-mcp/                         # Clean ephemeral Playwright directory (0 clutter files)
├── output/                                   # CENTRALIZED ANNUAL POST-LEVEL TRACKERS
│   └── 2026/
│       ├── AEGI.csv                          # Canonical 12-row wide post-level tracker (44 columns)
│       ├── AL Abbas.csv                      # Annual tracker initialized for AL Abbas
│       └── Cortech Solution.csv              # Annual tracker initialized for Cortech Solution
├── Posts/                                    # CREATIVE INPUT WORKSPACES
│   ├── AEGI/
│   │   ├── client_config.json                # Source of truth for client settings & endpoints
│   │   ├── Month 01/                         # Approved 1:1 square graphic assets (Post 1.png .. 12.png)
│   │   └── post_01_draft.md .. post_12_draft.md # 12 modular drafts with YAML frontmatter
│   ├── AL Abbas/
│   │   └── Month 01/                         # Client asset workspace
│   └── Cortech Solution/
│       └── Month 01/                         # Standardized asset subfolder (Post 1.png .. 9.png)
├── reports/                                  # CLIENT-SPECIFIC ANNUAL AUDIT & RUN LOGS
│   └── 2026/
│       ├── AEGI/
│       │   ├── exceptions.md                 # Account discrepancy & timing variance log
│       │   ├── migration_report.md           # Architecture migration & 12-row schema log
│       │   └── publishing_audit.md           # Live 60/60 scheduled placement audit evidence
│       ├── AL Abbas/                         # Client report folder
│       └── Cortech Solution/                 # Client report folder
├── scripts/
│   ├── config_loader.py                      # Validates client_config.json schema & rules
│   ├── publish_guard.py                      # Client isolation, duplicate checks & recovery logic
│   └── tracker_manager.py                    # Atomic CSV persistence & wide batch status transitions
└── tests/
    └── test_publishing_guards.py             # 39 automated safeguard & regression unit tests
```

---

## 2. Canonical Wide Post Tracker Specification (`output/<year>/<client>.csv`)

The **single canonical source of truth** for post scheduling status is:
`output/<year>/<client_name>.csv` (e.g., [`output/2026/AEGI.csv`](file:///D:/Cortech%20Solution/04%20Sales%20&%20Growth/AI%20Employees/Project%2003%20Social%20Media%20Manager/output/2026/AEGI.csv))

### Core Architecture Rules:
- **One Row Per Post:** 12 approved posts = **exactly 12 data rows**. Posts are never duplicated across rows for multiple platforms.
- **Platform Separation:** Retains platform-specific scheduling dates, times, timezones, statuses, and verification timestamps in dedicated prefixed columns.
- **Timing Variance Preservation:** Preserves platform-specific schedule differences (e.g. Post 04 scheduled at `15:30 PKT` on LinkedIn and `16:20 PKT` on X/GBP/Meta).

### 44-Column Wide Schema:
| Column Group | Columns | Description |
| :--- | :--- | :--- |
| **Shared Post Data** | `client_id`, `year`, `post_id`, `post_title`, `content_draft_path`, `asset_path`, `overall_status` | Shared metadata, creative asset references, and overall progress (`NEW`, `PARTIAL`, `DONE`). |
| **LinkedIn** | `linkedin_scheduled_date`, `linkedin_scheduled_time`, `linkedin_timezone`, `linkedin_status`, `linkedin_scheduled_timestamp`, `linkedin_last_verified`, `linkedin_notes` | LinkedIn Company Page scheduling and audit state. |
| **X (Twitter)** | `x_scheduled_date`, `x_scheduled_time`, `x_timezone`, `x_status`, `x_scheduled_timestamp`, `x_last_verified`, `x_notes` | X composer scheduling and audit state. |
| **GBP** | `gbp_scheduled_date`, `gbp_scheduled_time`, `gbp_timezone`, `gbp_cta_button_type`, `gbp_cta_link`, `gbp_status`, `gbp_scheduled_timestamp`, `gbp_last_verified`, `gbp_notes` | Google Business Profile scheduling, action button, and audit state. |
| **Meta Facebook** | `facebook_scheduled_date`, `facebook_scheduled_time`, `facebook_timezone`, `facebook_status`, `facebook_scheduled_timestamp`, `facebook_last_verified`, `facebook_notes` | Facebook Page scheduling and audit state. |
| **Meta Instagram** | `instagram_scheduled_date`, `instagram_scheduled_time`, `instagram_timezone`, `instagram_status`, `instagram_scheduled_timestamp`, `instagram_last_verified`, `instagram_notes` | Instagram Account scheduling and audit state. |

---

## 3. Platform-by-Platform Scheduling Workflow

Execution strictly follows this sequential order to eliminate context switching and cross-contamination:

```
Step 1: LinkedIn (all 12 posts)
   └─► Identity Check ──► Pre-Submission Check ──► Submit ──► Queue Audit ──► Update linkedin_* Columns
Step 2: X / Twitter (all 12 posts)
   └─► Identity Check ──► Pre-Submission Check ──► Submit ──► Queue Audit ──► Update x_* Columns
Step 3: Google Business Profile (all 12 posts)
   └─► Identity Check ──► Pre-Submission Check ──► Submit ──► Queue Audit ──► Update gbp_* Columns
Step 4: Meta Business Suite (all 12 Facebook Page & 12 Instagram posts)
   └─► Identity Check ──► Pre-Submission Check ──► Submit ──► Queue Audit ──► Update facebook_* & instagram_* Columns
```

---

## 4. Key CLI Commands & Operations

### Validate and Inspect Output Trackers:
```powershell
# Validate annual CSV schema & business rules
python scripts/tracker_manager.py validate AEGI 2026

# View status of all 12 posts across all destinations
python scripts/tracker_manager.py status AEGI 2026

# View per-platform completion summary
python scripts/tracker_manager.py summary AEGI 2026
```

### Run Automated Safeguards Test Suite:
```powershell
python tests/test_publishing_guards.py
```

---

## 5. Account Identity & Exception Logging

If any account identity discrepancy or scheduling variance is encountered:
1. Document the issue in `reports/<year>/<client>/exceptions.md`.
2. Do **not** alter live account handles or publish to unverified accounts.
3. Refer to [`reports/2026/AEGI/exceptions.md`](file:///D:/Cortech%20Solution/04%20Sales%20&%20Growth/AI%20Employees/Project%2003%20Social%20Media%20Manager/reports/2026/AEGI/exceptions.md) for current notes regarding AEGI's X handle (`@advancedenginc` vs `@AEGIOfficial`).
