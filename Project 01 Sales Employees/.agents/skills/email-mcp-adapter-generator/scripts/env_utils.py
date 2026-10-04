#!/usr/bin/env python3
"""
env_utils.py — Read provider credentials from a project-root .env file.

This is the canonical copy. The generator uses it directly and also copies
it into each provider skill's scripts/backends/ so that skill stays
self-contained (no cross-skill import). Keep the two in sync.

Convention: each provider's token is keyed by PROVIDER_API_TOKEN, e.g.
    HOSTINGER_API_TOKEN=...
so get_token("hostinger") -> HOSTINGER_API_TOKEN. Real environment
variables win over the .env file. No third-party dependency.
"""

import os


def find_dotenv(start=None):
    """Walk up from `start` (default cwd) to find a .env file. Returns the
    path or None — walking up lets scripts run from anywhere in the tree."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_dotenv(path=None):
    """Parse a .env into a dict. Tolerates blanks, `#` comments, optional
    `export ` prefixes, and quoted values. Returns {} if no file."""
    path = path or find_dotenv()
    values = {}
    if not path or not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                values[key] = val
    return values


def get_token(provider):
    """Return the API token for a provider (env var first, then .env)."""
    key = f"{provider.upper()}_API_TOKEN"
    if os.environ.get(key):
        return os.environ[key]
    return load_dotenv().get(key)


def require_token(provider):
    """Like get_token but raises a clear, actionable error if missing."""
    token = get_token(provider)
    if not token:
        key = f"{provider.upper()}_API_TOKEN"
        raise RuntimeError(
            f"{key} not found. Create a .env file at the project root with "
            f"`{key}=<your token>` (copy .env.example as a starting point)."
        )
    return token


if __name__ == "__main__":
    import sys
    prov = sys.argv[1] if len(sys.argv) > 1 else "hostinger"
    tok = get_token(prov)
    print(f".env location: {find_dotenv() or 'NOT FOUND'}")
    print(f"{prov.upper()}_API_TOKEN present: {bool(tok)}")
    if tok:
        print(f"  prefix: {tok[:6]}…")
