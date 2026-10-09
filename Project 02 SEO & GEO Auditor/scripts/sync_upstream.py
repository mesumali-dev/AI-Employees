#!/usr/bin/env python3
"""
sync_upstream.py - Upstream Sync & Change Manifest Generator for Antigravity SEO Auditor.

This script tracks AgriciDaniel/claude-seo in the isolated upstream-claude-seo/ directory,
computes file-level diffs, and generates an Agent-Ready Manifest (JSON & Markdown).
Agents use this manifest to adapt upstream changes into Antigravity format without
blindly overwriting files, preserving Windows UTF-8, UV execution, Playwright timeouts,
and custom branding.

Usage:
    uv run python scripts/sync_upstream.py --status
    uv run python scripts/sync_upstream.py --pull
    uv run python scripts/sync_upstream.py --manifest
    uv run python scripts/sync_upstream.py --diff scripts/google_auth.py
"""

import argparse
import difflib
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

UPSTREAM_REPO_URL = "https://github.com/AgriciDaniel/claude-seo.git"
BASE_DIR = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = BASE_DIR / "upstream-claude-seo"
SCRIPTS_DIR = BASE_DIR / "scripts"
SKILLS_DIR = BASE_DIR / ".agents" / "skills"
AGENTS_DIR = BASE_DIR / ".agents" / "agents"
DATA_DIR = BASE_DIR / "data"
MANIFEST_JSON = DATA_DIR / "upstream_manifest.json"
MANIFEST_MD = BASE_DIR / "UPSTREAM_CHANGES.md"

# Scripts with specific Windows / Antigravity adaptations that must NEVER be blindly overwritten
PROTECTED_SCRIPTS = {
    "analyze_visual.py": {
        "reason": "Contains Windows UTF-8 reconfigure and resilient page.goto(wait_until='load') fallback for Next.js SSR.",
        "antigravity_rule": "Do NOT replace wait_until='load' with wait_until='networkidle'. Keep sys.stdout.reconfigure."
    },
    "capture_screenshot.py": {
        "reason": "Contains Windows UTF-8 reconfigure, resilient load timeout, and Unicode fallback print.",
        "antigravity_rule": "Do NOT replace wait_until='load' with wait_until='networkidle'. Keep UnicodeEncodeError handler."
    },
    "schema_generate.py": {
        "reason": "Contains custom author profile metadata in docstrings.",
        "antigravity_rule": "Preserve author profile 'Syed Mesum Ali Shah' in examples."
    }
}


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run git command safely and return (returncode, stdout, stderr)."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def ensure_upstream_clone() -> bool:
    """Ensure upstream directory exists and is a git repository."""
    if not UPSTREAM_DIR.exists():
        print(f"[*] Upstream directory not found. Cloning from {UPSTREAM_REPO_URL}...")
        res = subprocess.run(
            ["git", "clone", UPSTREAM_REPO_URL, str(UPSTREAM_DIR)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if res.returncode != 0:
            print(f"[!] Error cloning upstream: {res.stderr}")
            return False
        print("[✓] Upstream cloned successfully.")
        return True

    if not (UPSTREAM_DIR / ".git").exists():
        print(f"[!] {UPSTREAM_DIR} exists but is not a valid git repository.")
        return False
    return True


def pull_upstream() -> bool:
    """Pull latest upstream commits."""
    if not ensure_upstream_clone():
        return False

    _, old_hash, _ = run_git(["rev-parse", "--short", "HEAD"], UPSTREAM_DIR)
    print(f"[*] Fetching upstream changes (current HEAD: {old_hash})...")

    code, _, err = run_git(["pull", "--ff-only"], UPSTREAM_DIR)
    if code != 0:
        print(f"[!] Git pull failed: {err}")
        return False

    _, new_hash, _ = run_git(["rev-parse", "--short", "HEAD"], UPSTREAM_DIR)
    if old_hash == new_hash:
        print(f"[✓] Upstream repository is already at latest commit ({old_hash}).")
    else:
        print(f"[✓] Upstream updated: {old_hash} -> {new_hash}")
        code, log_out, _ = run_git(["log", "--oneline", f"{old_hash}..{new_hash}"], UPSTREAM_DIR)
        if log_out:
            print("\nNew upstream commits:")
            for line in log_out.splitlines():
                print(f"  + {line}")
            print()
    return True


def compute_file_diff(local_file: Path, up_file: Path) -> str:
    """Return unified diff string between local and upstream file."""
    if not local_file.exists() or not up_file.exists():
        return ""
    local_lines = local_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    up_lines = up_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    diff = difflib.unified_diff(
        local_lines,
        up_lines,
        fromfile=f"local/{local_file.name}",
        tofile=f"upstream/{up_file.name}",
        n=3
    )
    return "".join(diff)


def generate_change_manifest() -> dict:
    """Analyze all differences and construct an Agent-Ready Change Manifest."""
    if not ensure_upstream_clone():
        return {}

    code, current_hash, _ = run_git(["rev-parse", "--short", "HEAD"], UPSTREAM_DIR)
    code, upstream_tag, _ = run_git(["describe", "--tags", "--always"], UPSTREAM_DIR)

    manifest = {
        "upstream_version": upstream_tag or "unknown",
        "upstream_commit": current_hash or "unknown",
        "scripts": [],
        "references_and_assets": [],
        "skill_prompts": [],
        "agents": [],
        "dependencies": [],
    }

    # 1. Inspect scripts
    up_scripts = UPSTREAM_DIR / "scripts"
    if up_scripts.exists():
        for up_f in sorted(up_scripts.iterdir()):
            if not up_f.is_file():
                continue
            local_f = SCRIPTS_DIR / up_f.name
            if not local_f.exists():
                manifest["scripts"].append({
                    "name": up_f.name,
                    "status": "NEW",
                    "path_local": f"scripts/{up_f.name}",
                    "path_upstream": f"upstream-claude-seo/scripts/{up_f.name}",
                    "is_protected": False,
                    "instruction": "New script from upstream. Review for Windows compatibility and add to scripts/."
                })
            else:
                if not filecmp.cmp(up_f, local_f, shallow=False):
                    diff_text = compute_file_diff(local_f, up_f)
                    is_prot = up_f.name in PROTECTED_SCRIPTS
                    prot_info = PROTECTED_SCRIPTS.get(up_f.name, {})

                    manifest["scripts"].append({
                        "name": up_f.name,
                        "status": "MODIFIED",
                        "path_local": f"scripts/{up_f.name}",
                        "path_upstream": f"upstream-claude-seo/scripts/{up_f.name}",
                        "is_protected": is_prot,
                        "protection_reason": prot_info.get("reason", ""),
                        "antigravity_rule": prot_info.get("antigravity_rule", "Port logic while ensuring GEMINI.md rules."),
                        "diff": diff_text
                    })

    # 2. Inspect skill references & assets
    up_skills = UPSTREAM_DIR / "skills"
    if up_skills.exists():
        for up_skill in sorted(up_skills.iterdir()):
            if not up_skill.is_dir():
                continue
            local_skill = SKILLS_DIR / up_skill.name
            for sub_f in sorted(up_skill.rglob("*")):
                if not sub_f.is_file():
                    continue
                rel_path = sub_f.relative_to(up_skill)
                local_f = local_skill / rel_path

                if sub_f.name == "SKILL.md":
                    # Check prompt body
                    if local_f.exists():
                        up_text = sub_f.read_text(encoding="utf-8", errors="replace")
                        loc_text = local_f.read_text(encoding="utf-8", errors="replace")
                        footer_pattern = re.compile(r"```\s*━+\s*(?:Built by agricidaniel|Audit Prepared).*?━+\s*```", re.DOTALL)
                        up_norm = footer_pattern.sub("", up_text).strip()
                        loc_norm = footer_pattern.sub("", loc_text).strip()
                        if up_norm != loc_norm:
                            manifest["skill_prompts"].append({
                                "skill": up_skill.name,
                                "path_local": f".agents/skills/{up_skill.name}/SKILL.md",
                                "path_upstream": f"upstream-claude-seo/skills/{up_skill.name}/SKILL.md",
                                "diff": compute_file_diff(local_f, sub_f),
                                "instruction": "Update skill instructions/version but strictly preserve Syed Mesum Ali Shah author footer."
                            })
                else:
                    if not local_f.exists() or not filecmp.cmp(sub_f, local_f, shallow=False):
                        manifest["references_and_assets"].append({
                            "skill": up_skill.name,
                            "relative_path": str(rel_path),
                            "path_local": f".agents/skills/{up_skill.name}/{rel_path}",
                            "path_upstream": f"upstream-claude-seo/skills/{up_skill.name}/{rel_path}",
                            "status": "NEW" if not local_f.exists() else "MODIFIED",
                            "diff": compute_file_diff(local_f, sub_f) if local_f.exists() else "(New file)",
                            "instruction": "Data/reference file update. Safe to port directly into .agents/skills/."
                        })

    # 3. Inspect agent prompts
    up_agents = UPSTREAM_DIR / "agents"
    if up_agents.exists():
        for up_a in sorted(up_agents.iterdir()):
            if not up_a.is_file() or not up_a.name.endswith(".md"):
                continue
            local_a = AGENTS_DIR / up_a.name
            if not local_a.exists():
                manifest["agents"].append({
                    "name": up_a.name,
                    "status": "NEW",
                    "path_local": f".agents/agents/{up_a.name}",
                    "path_upstream": f"upstream-claude-seo/agents/{up_a.name}",
                    "instruction": "Convert new Claude agent into Antigravity subagent format with standard tools and uv run."
                })
            else:
                up_content = up_a.read_text(encoding="utf-8", errors="replace")
                local_content = local_a.read_text(encoding="utf-8", errors="replace")
                up_body = re.sub(r"^---[\s\S]*?---\s*", "", up_content)
                local_body = re.sub(r"^---[\s\S]*?---\s*", "", local_content)
                clean_pat = r'(\$\{"?CLAUDE_PLUGIN_ROOT"?\}/scripts/claude-seo|python scripts/runtime\.py|uv run python scripts/[a-zA-Z0-9_\.-]+)'
                up_norm = re.sub(clean_pat, "RUN_SCRIPT", up_body).strip()
                loc_norm = re.sub(r"^# System Prompt\s*", "", local_body).strip()
                loc_norm = re.sub(clean_pat, "RUN_SCRIPT", loc_norm).strip()
                if re.sub(r"\s+", " ", up_norm) != re.sub(r"\s+", " ", loc_norm):
                    manifest["agents"].append({
                        "name": up_a.name,
                        "status": "MODIFIED",
                        "path_local": f".agents/agents/{up_a.name}",
                        "path_upstream": f"upstream-claude-seo/agents/{up_a.name}",
                        "instruction": "Port updated system prompt into .agents/agents while maintaining Antigravity YAML frontmatter and tools."
                    })

    # 4. Inspect requirements.txt
    up_req = UPSTREAM_DIR / "requirements.txt"
    loc_req = BASE_DIR / "requirements.txt"
    if up_req.exists() and loc_req.exists() and not filecmp.cmp(up_req, loc_req, shallow=False):
        manifest["dependencies"].append({
            "file": "requirements.txt",
            "diff": compute_file_diff(loc_req, up_req),
            "instruction": "Merge new packages into pyproject.toml and run uv sync."
        })

    return manifest


def write_manifest_files(manifest: dict):
    """Write manifest to JSON and Markdown files for agents and user review."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Generate Markdown summary
    lines = [
        f"# Upstream Change Manifest ({manifest.get('upstream_version', 'latest')})",
        "",
        f"**Upstream Commit**: `{manifest.get('upstream_commit', 'unknown')}`  ",
        f"**Source**: `{UPSTREAM_REPO_URL}`",
        "",
        "> [!IMPORTANT]",
        "> **Agent Directive**: Do NOT blindly copy Claude Code files over Antigravity files.",
        "> Apply each change using Antigravity CLI conventions (Windows UTF-8, UV execution, Playwright timeout fallbacks, and preserved author footer).",
        "",
        "## Summary of Changes",
        f"- **Scripts Modified / New**: {len(manifest.get('scripts', []))}",
        f"- **References & Assets**: {len(manifest.get('references_and_assets', []))}",
        f"- **Skill Prompts**: {len(manifest.get('skill_prompts', []))}",
        f"- **Agents**: {len(manifest.get('agents', []))}",
        f"- **Dependencies**: {len(manifest.get('dependencies', []))}",
        "",
    ]

    # Scripts section
    if manifest.get("scripts"):
        lines.append("## 1. Scripts")
        for s in manifest["scripts"]:
            prot_badge = "⚠️ **[PROTECTED - WINDOWS/SSR PATCH]**" if s.get("is_protected") else "✅ **[SAFE TO PORT]**"
            lines.append(f"### `{s['name']}` ({s['status']}) - {prot_badge}")
            if s.get("is_protected"):
                lines.append(f"- **Reason**: {s.get('protection_reason')}")
                lines.append(f"- **Antigravity Rule**: {s.get('antigravity_rule')}")
            else:
                lines.append(f"- **Instruction**: Port upstream bug fixes/features into `{s['path_local']}` using Antigravity standards.")
            if s.get("diff"):
                lines.append("```diff")
                lines.append(s["diff"][:2500])  # preview
                if len(s["diff"]) > 2500:
                    lines.append("... (diff truncated, see JSON for full diff) ...")
                lines.append("```")
            lines.append("")

    # References section
    if manifest.get("references_and_assets"):
        lines.append("## 2. Skills References & Assets")
        for r in manifest["references_and_assets"]:
            lines.append(f"- **`{r['path_local']}`** ({r['status']}): {r['instruction']}")
        lines.append("")

    # Skill prompts section
    if manifest.get("skill_prompts"):
        lines.append("## 3. Skill Prompts (`SKILL.md`)")
        for sp in manifest["skill_prompts"]:
            lines.append(f"- **`{sp['path_local']}`**: {sp['instruction']}")
        lines.append("")

    # Agents section
    if manifest.get("agents"):
        lines.append("## 4. Agents (`.agents/agents/`)")
        for a in manifest["agents"]:
            lines.append(f"- **`{a['name']}`** ({a['status']}): {a['instruction']}")
        lines.append("")

    with open(MANIFEST_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[✓] Manifest generated successfully:")
    print(f"    - JSON: {MANIFEST_JSON}")
    print(f"    - Markdown: {MANIFEST_MD}")


def print_status_summary(manifest: dict):
    """Print readable console summary."""
    print("=" * 65)
    print(f"   UPSTREAM SYNC STATUS (claude-seo: {manifest.get('upstream_version', 'latest')})")
    print("=" * 65)

    has_diff = False
    scripts = manifest.get("scripts", [])
    if scripts:
        has_diff = True
        print(f"\n[Scripts Detected: {len(scripts)}]")
        for s in scripts:
            flag = "[PROTECTED - Windows Patch]" if s.get("is_protected") else "[Clean Port]"
            print(f"  - {s['name']} ({s['status']}) {flag}")

    refs = manifest.get("references_and_assets", [])
    if refs:
        has_diff = True
        print(f"\n[References/Data Updated: {len(refs)}]")
        for r in refs:
            print(f"  - {r['path_local']}")

    prompts = manifest.get("skill_prompts", [])
    if prompts:
        has_diff = True
        print(f"\n[Skill Prompts Updated: {len(prompts)}]")
        for p in prompts:
            print(f"  - {p['path_local']}")

    agents = manifest.get("agents", [])
    if agents:
        has_diff = True
        print(f"\n[Agents Changes: {len(agents)}]")
        for a in agents:
            print(f"  - {a['name']} ({a['status']})")

    if not has_diff:
        print("\n[✓] All files in Antigravity setup are completely in sync with upstream claude-seo.")
    else:
        print("\n[!] Run with --manifest to produce an Agent Change Brief for smart porting.")
    print("=" * 65)


def show_diff(rel_path: str):
    """Show unified diff between local and upstream file."""
    path = Path(rel_path)
    if path.parts and path.parts[0] == "scripts":
        up_file = UPSTREAM_DIR / rel_path
        local_file = BASE_DIR / rel_path
    elif path.parts and path.parts[0] == ".agents":
        sub = Path(*path.parts[1:])
        up_file = UPSTREAM_DIR / sub
        local_file = BASE_DIR / rel_path
    else:
        up_file = UPSTREAM_DIR / rel_path
        local_file = BASE_DIR / rel_path

    if not up_file.exists():
        print(f"[!] Upstream file not found: {up_file}")
        return
    if not local_file.exists():
        print(f"[!] Local file not found: {local_file}")
        return

    diff = compute_file_diff(local_file, up_file)
    if not diff:
        print("[✓] Files are identical.")
    else:
        print(diff)


def main():
    parser = argparse.ArgumentParser(
        description="Sync and generate change manifests from AgriciDaniel/claude-seo for Antigravity Agent adaptation."
    )
    parser.add_argument("--pull", action="store_true", help="Fetch and pull latest upstream commits.")
    parser.add_argument("--status", action="store_true", help="Show difference summary.")
    parser.add_argument("--manifest", action="store_true", help="Generate UPSTREAM_CHANGES.md and data/upstream_manifest.json.")
    parser.add_argument("--diff", type=str, metavar="PATH", help="Show unified diff for a specific file.")

    args = parser.parse_args()

    if not any([args.pull, args.status, args.manifest, args.diff]):
        args.status = True

    if args.pull:
        pull_upstream()

    if args.diff:
        show_diff(args.diff)

    manifest = generate_change_manifest()

    if args.manifest:
        write_manifest_files(manifest)
    elif args.status or args.pull:
        print_status_summary(manifest)


if __name__ == "__main__":
    main()
