# Adding a new email provider

The generator supports a provider when it has two things for it: a
**probe** (confirms auth + returns account facts) and a **backend
template** (how that provider actually sends). Here's how to add both.
Use the Hostinger implementation as the worked example throughout.

## 1. Decide how the provider sends

Look at the provider's MCP server config (or API docs):

- **REST passthrough MCP** (like Hostinger): the MCP just forwards
  `{method, path, body}`. → Your backend should call the REST API
  directly. Simplest and most reliable. Read the token from `.env`.
- **Semantic MCP** (a real `send_email` tool with abstraction): calling
  the MCP protocol may be worth it. Your backend can shell out to the MCP
  bridge or use an MCP client library. Only do this if REST isn't
  available or the MCP genuinely adds value.
- **Provider SDK / OAuth** (e.g. Gmail API): the backend may need an
  OAuth flow rather than a bearer token. Store what you can in `.env`
  (client id/secret, refresh token) and have the backend exchange it.

## 2. Write the probe (in `scripts/inspect_mcp.py`)

Add `probe_<provider>(token, timeout=30)` that:
- makes ONE authenticated call that proves the token works (e.g. a
  "whoami" / list-mailboxes endpoint),
- returns a dict of durable facts the backend needs baked in.

The dict shape is provider-specific but should include at least a
`provider` key and whatever identifiers/addresses the backend needs.
Register it in the `PROBES` dict.

```python
def probe_gmail(token, timeout=30):
    # confirm auth, then return account facts
    return {
        "provider": "gmail",
        "default_from_address": "...",
        # ...whatever the gmail backend needs...
    }

PROBES = {"hostinger": probe_hostinger, "gmail": probe_gmail}
```

Tip: if the provider's API sits behind Cloudflare, set an ordinary
`User-Agent` header or you may get a 403 (error 1010) — that exact gotcha
bit the Hostinger probe.

## 3. Write the backend template (`assets/templates/<provider>_backend.py`)

Implement `EmailBackend` (see `base.py`):
- construct from `token=None` → fall back to
  `env_utils.require_token("<provider>")`,
- load the generated `<provider>_config.json` for account facts (no
  network on construction if possible),
- implement `send(to, subject, body, display_name=None)` returning a
  `SendResult`. Catch ordinary provider errors and return
  `SendResult.failure(reason)` — never let one bad recipient abort the
  batch.
- expose a module-level `build(**kwargs)` factory.

Register it in `BACKEND_TEMPLATES` in `inspect_mcp.py`.

## 4. Wire the drafter skill

Create (or reuse) a `<provider>-email-drafter` skill. Its `send_batch.py`
and `lead_status.py` are provider-agnostic and can be copied from
`hostinger-email-drafter` unchanged — only the generated backend differs.

## 5. Generate and test

```
python scripts/inspect_mcp.py --provider <provider> --target-skill <path> --print-only   # auth check
python scripts/inspect_mcp.py --provider <provider> --target-skill <path>                 # write files
```

Then dry-run the drafter's sender:
```
python scripts/send_batch.py --queue draft_queue.json --dry-run
```

The whole point: once the backend exists, the drafter's daily workflow is
identical to every other provider's. All the provider-specific detail is
sealed inside the generated backend.
