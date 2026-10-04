#!/usr/bin/env python3
"""
inspect_mcp.py — Provision/refresh a provider email backend. RUN RARELY.

This is the "compile step". It probes a provider's API once (using the
token from the project-root .env), confirms auth, learns account facts,
and writes a self-contained backend into the TARGET provider skill's
scripts/backends/ folder. After that, that skill's send_batch.py runs
without ever touching the MCP — which is what keeps runtime tokens tiny.

Run it only when: onboarding a provider, a token changed, the provider
API changed, or a send script reports "no backend found".

Usage:
  python scripts/inspect_mcp.py --provider hostinger --target-skill <path>
  python scripts/inspect_mcp.py --provider hostinger            # auto-find sibling skill
  python scripts/inspect_mcp.py --provider hostinger --print-only

The token is read from <PROVIDER>_API_TOKEN in the project-root .env.
"""

import json
import os
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import env_utils  # noqa: E402


# ======================================================================
# Provider probes — confirm auth + return the account facts the backend
# needs baked in. Add one function per provider you onboard.
# ======================================================================

def probe_hostinger(token, timeout=30):
    url = "https://api.mail.hostinger.com/api/v1/me"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/json")
    # Cloudflare fronts the Hostinger API and blocks the default Python
    # User-Agent with a 403 (error 1010); a normal UA clears it.
    req.add_header("User-Agent", "email-mcp-adapter-generator/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8") or "{}")
    mailboxes = (payload.get("data") or {}).get("mailboxes") or []
    if not mailboxes:
        raise RuntimeError("Auth OK but no mailboxes returned by /me.")
    return {
        "provider": "hostinger",
        "rest_base": "https://api.mail.hostinger.com",
        "send_path": "/api/v1/mailboxes/{mailbox}/send",
        "mailboxes": [
            {"resourceId": m.get("resourceId"), "address": m.get("address")}
            for m in mailboxes
        ],
        "default_mailbox_resource_id": mailboxes[0].get("resourceId"),
        "default_from_address": mailboxes[0].get("address"),
    }


PROBES = {
    "hostinger": probe_hostinger,
    # "gmail": probe_gmail,      # see references/adding_a_provider.md
    # "outlook": probe_outlook,
}

# Backend module templates, keyed by provider. See references/
# adding_a_provider.md for how to add one. base.py + env_utils.py are
# shared and written from the copies in this skill.
BACKEND_TEMPLATES = {
    "hostinger": "hostinger_backend.py",
}


def target_skill_dir(provider, explicit):
    """Resolve where to write the backend. Explicit path wins; else look
    for a sibling skill named <provider>-email-drafter."""
    if explicit:
        return os.path.abspath(explicit)
    skills_dir = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # .../skills
    guess = os.path.join(skills_dir, f"{provider}-email-drafter")
    return guess


def write_file(path, content, overwrite=True):
    if os.path.exists(path) and not overwrite:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def read_template(name):
    """Templates live under this skill's assets/templates/."""
    p = os.path.join(os.path.dirname(SCRIPT_DIR), "assets", "templates", name)
    with open(p, encoding="utf-8") as f:
        return f.read()


def main():
    args = sys.argv[1:]
    provider = None
    target = None
    print_only = False
    it = iter(args)
    for a in it:
        if a == "--provider":
            provider = next(it)
        elif a == "--target-skill":
            target = next(it)
        elif a == "--print-only":
            print_only = True

    if not provider:
        print("FAILED: --provider is required (e.g. --provider hostinger)")
        sys.exit(2)

    provider = provider.lower()
    print(f"Provider:     {provider}")

    if provider not in PROBES:
        print(f"FAILED: no probe implemented for '{provider}'. "
              f"See references/adding_a_provider.md.")
        sys.exit(1)

    # 1. Token from .env
    try:
        token = env_utils.require_token(provider)
    except RuntimeError as e:
        print(f"FAILED: {e}")
        sys.exit(1)
    print("Token:        present (from .env)")

    # 2. Probe
    print(f"\nProbing {provider} API to confirm auth and learn account facts…")
    try:
        facts = PROBES[provider](token)
    except urllib.error.HTTPError as e:
        print(f"FAILED: provider returned HTTP {e.code}. Token likely invalid.")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"FAILED: could not reach provider: {e}")
        sys.exit(1)

    print("Auth OK. Discovered:")
    for m in facts.get("mailboxes", []):
        print(f"  - {m['address']}  (resourceId {m['resourceId']})")

    dest = target_skill_dir(provider, target)
    print(f"\nTarget skill: {dest}")
    if not os.path.isdir(dest):
        print(f"FAILED: target skill dir does not exist. Pass --target-skill "
              f"<path> to a real skill folder.")
        sys.exit(1)

    if print_only:
        print("\n--print-only set; nothing written.")
        return

    backends_dir = os.path.join(dest, "scripts", "backends")

    # 3a. Shared files (interface + env reader) — copied so the target
    # skill is fully self-contained.
    write_file(os.path.join(backends_dir, "base.py"),
               read_template("base.py"), overwrite=True)
    write_file(os.path.join(dest, "scripts", "env_utils.py"),
               env_utils_source(), overwrite=True)
    # 3b. Config — always refreshed with the latest probe facts.
    write_file(os.path.join(backends_dir, f"{provider}_config.json"),
               json.dumps(facts, indent=2), overwrite=True)
    print(f"\nWrote {provider}_config.json + base.py + env_utils.py")

    # 3c. Backend module — do NOT clobber a hand-tuned one.
    backend_path = os.path.join(backends_dir, f"{provider}_backend.py")
    tmpl = BACKEND_TEMPLATES.get(provider)
    if os.path.exists(backend_path):
        print(f"Backend already present: {provider}_backend.py (kept as-is; "
              f"delete it first to force a rebuild).")
    elif tmpl:
        write_file(backend_path, read_template(tmpl), overwrite=False)
        print(f"Wrote {provider}_backend.py")
    else:
        print(f"NOTE: no backend template for '{provider}'. Create "
              f"{provider}_backend.py implementing EmailBackend (see "
              f"references/adding_a_provider.md).")

    # Ensure package marker.
    init_path = os.path.join(backends_dir, "__init__.py")
    if not os.path.exists(init_path):
        write_file(init_path, '"""Generated email backends."""\n')

    print(f"\nDone. {dest} can now send without touching the MCP.")


def env_utils_source():
    """Return this skill's env_utils.py source, to copy into the target."""
    with open(os.path.join(SCRIPT_DIR, "env_utils.py"), encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    main()
