#!/usr/bin/env python3
"""
env_utils.py — Read provider credentials from a project-root .env file.

Credentials live in ONE place: a .env file at the project root (never
committed — see .env.example for the template). Both the send path and the
adapter generator read the token from here, so there's no second copy of
the secret sitting in a shared config.

Convention: each provider's token is keyed by its name, e.g.
    HOSTINGER_API_TOKEN=...
    GMAIL_API_TOKEN=...
so get_token("hostinger") looks up HOSTINGER_API_TOKEN. Real environment
variables win over the .env file, which makes CI / one-off overrides easy.

No third-party dependency (python-dotenv not required) — this is a tiny,
forgiving KEY=VALUE parser so the skill runs on a bare Python install.
"""

import os


def find_dotenv(start=None):
    """Walk up from `start` (default: cwd) looking for a .env file.
    Returns the path or None. Walking up means the script works whether
    it's invoked from the project root or from inside the skill dir."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        candidate = os.path.join(d, ".env")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:  # reached filesystem root
            return None
        d = parent


def load_dotenv(path=None):
    """Parse a .env file into a dict. Tolerates blank lines, `#` comments,
    optional `export ` prefixes, and quoted values. Returns {} if no file."""
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
    """Return the API token for a provider, e.g. get_token('hostinger')
    -> value of HOSTINGER_API_TOKEN. Checks real env vars first, then the
    project-root .env. Returns None if not found."""
    key = f"{provider.upper()}_API_TOKEN"
    if os.environ.get(key):
        return os.environ[key]
    return load_dotenv().get(key)


def require_token(provider):
    """Like get_token but raises a clear, actionable error if missing —
    used at the point of send so the failure names exactly what to fix."""
    token = get_token(provider)
    if not token:
        key = f"{provider.upper()}_API_TOKEN"
        raise RuntimeError(
            f"{key} not found. Create a .env file at the project root with "
            f"`{key}=<your token>` (copy .env.example as a starting point)."
        )
    return token


if __name__ == "__main__":
    # Self-check: report which tokens are visible WITHOUT printing them.
    import sys
    prov = sys.argv[1] if len(sys.argv) > 1 else "hostinger"
    tok = get_token(prov)
    dotenv = find_dotenv()
    print(f".env location: {dotenv or 'NOT FOUND'}")
    print(f"{prov.upper()}_API_TOKEN present: {bool(tok)}")
    if tok:
        print(f"  prefix: {tok[:6]}…")
