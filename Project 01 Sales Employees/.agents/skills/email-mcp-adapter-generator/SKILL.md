---
name: email-mcp-adapter-generator
description: Provisions a token-efficient, self-contained email "backend" for a provider skill (like hostinger-email-drafter, gmail-email-drafter, outlook-email-drafter). Run this RARELY — only when onboarding a new email provider, when an API token/credential changes, or when explicitly asked to regenerate a backend. It reads the provider's API token from the project-root .env, probes the provider's API to confirm auth and discover account facts (mailbox/resource IDs, send endpoint, default from-address), and generates a ready-to-use backend module + config directly into the target provider skill's scripts/backends/ folder — so that skill's send script never has to touch the MCP at runtime. Trigger this whenever the user says things like "set up the email backend", "regenerate the Hostinger adapter", "my email token changed", "add a new email provider", "onboard Gmail for sending", "the send script says no backend found", or "inspect the email MCP and build the sender". Do NOT use this for actually drafting or sending emails — that's the provider drafter skill's job; this only builds the plumbing they rely on.
---

# Email MCP Adapter Generator

Builds the "compile-time" half of the email architecture: it inspects a
configured email provider once and crystallizes what it learns into a
concrete, self-contained backend the provider's drafter skill uses at
runtime. This keeps day-to-day sending cheap — the drafter never has to
make verbose MCP calls, because everything the provider needs is baked
into a generated backend.

## When to run (and when NOT to)

Run this **rarely**, only when:
- onboarding a brand-new email provider (Gmail, Outlook, …),
- an API token / credential changed,
- the provider's API surface changed, or
- a drafter's send script reports "no backend found" / a stale backend.

Do **not** run it as part of normal drafting or sending — that's the
provider drafter's daily job. This is the occasional setup step.

## Mental model

```
                 (rare, token-heavy)              (daily, cheap)
   .env token  ─────────────────────►  generated backend  ─────────────►  send
                inspect_mcp.py                in provider skill        send_batch.py
   probes provider API,              scripts/backends/                (drafter skill)
   discovers account facts,          <provider>_backend.py
   writes backend + config           <provider>_config.json
```

The generator is provider-agnostic. Each provider drafter skill stays
**self-contained**: the generated backend lands inside *that* skill's
`scripts/backends/` folder, so when the agent opens `hostinger-email-
drafter` everything needed to send via Hostinger is right there — no
shared folder, no cross-skill imports.

## Credentials

The provider's API token lives in a `.env` file at the **project root**
(never committed — see the drafter skill's `.env.example`). The key is
`<PROVIDER>_API_TOKEN`, e.g. `HOSTINGER_API_TOKEN`. The generator reads it
via `scripts/env_utils.py`. If the token is missing, it stops with a clear
message telling the user to create `.env`.

## Usage

```
python scripts/inspect_mcp.py --provider hostinger --target-skill <path-to-provider-skill>
```

- `--provider` — provider key (e.g. `hostinger`). Determines which token
  (`HOSTINGER_API_TOKEN`) and which probe to run.
- `--target-skill` — path to the provider skill whose `scripts/backends/`
  should receive the generated files. Defaults to a sibling skill named
  `<provider>-email-drafter` if present.
- `--print-only` — probe and report what it found, but write nothing
  (good for a dry check that auth works).

What it does:
1. Reads `<PROVIDER>_API_TOKEN` from the project-root `.env`.
2. Probes the provider API to confirm the token works and learn account
   facts (for Hostinger: mailbox resourceId + default from-address).
3. Writes into the target skill's `scripts/backends/`:
   - `base.py` — the `EmailBackend` interface (if not already present),
   - `env_utils.py` — the shared `.env` token reader (copied so the skill
     stays self-contained),
   - `<provider>_backend.py` — the concrete backend (only if missing; it
     won't clobber a hand-tuned one — delete it first to force a rebuild),
   - `<provider>_config.json` — the discovered account facts (always
     refreshed).

## Adding a new provider

The generator knows how to probe a provider via a small "probe" function
and render its backend from a template. To onboard a provider it doesn't
yet support:

1. Read `references/adding_a_provider.md` — it walks through writing a
   `probe_<provider>()` (confirm auth + return account facts) and a
   backend template (how that provider actually sends: REST call, SDK,
   or, if the provider's MCP is genuinely semantic rather than a REST
   passthrough, an MCP-protocol call).
2. Add the probe + template to `scripts/inspect_mcp.py`.
3. Run the generator pointed at the new provider's drafter skill.

The guiding principle: **hide everything provider-specific inside the
generated backend**, so every drafter's `send_batch.py` stays identical
and provider-agnostic. See `references/architecture.md` for the full
rationale (why REST for passthrough MCPs, why generate rather than call
the MCP at runtime, and the token-cost math).
