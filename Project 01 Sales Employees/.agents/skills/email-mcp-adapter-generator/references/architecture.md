# Architecture & rationale

## The problem this solves

Email MCP servers are convenient for interactive use, but calling an MCP
tool once per email dumps a full, verbose response into the agent's
context every time. Sending 10 emails that way costs thousands of tokens
in echoed headers, envelopes, and discovery chatter — and it scales
linearly with volume.

## The split: compile once, run cheap

We separate the work into two phases with very different cost profiles:

- **Compile (rare, token-heavy):** `inspect_mcp.py` probes the provider's
  API once, confirms the credential works, and learns the durable account
  facts (mailbox/resource IDs, send endpoint, default from-address). It
  writes a concrete backend + a small config file into the target
  provider skill.
- **Run (daily, near-free):** the drafter's `send_batch.py` imports that
  generated backend and sends. The agent only ever sees one concise line
  per email. No MCP calls, no discovery, no verbose envelopes.

This is the same pattern as ORM scaffolding, OpenAPI client generation,
or protobuf codegen: pay the introspection cost once, reuse the artifact
forever.

## Why REST for a passthrough MCP

Some MCP servers (Hostinger's included) are thin passthroughs — their
tools just forward a raw `{method, path, body}` to the provider's REST
API. For those, having the generated backend speak the MCP JSON-RPC
protocol at runtime would mean spawning the MCP bridge process (often a
Node tool like `mcp-remote`) and parsing streaming responses… all to make
the exact same HTTP call REST exposes directly. So the backend calls REST,
reusing the same token the MCP uses.

If a future provider's MCP is genuinely *semantic* (it exposes a real
`send_email` tool with meaningful abstraction, not a REST passthrough),
that provider's backend is free to call the MCP protocol instead — the
choice is hidden inside the backend and doesn't affect anything else.

## Why self-contained provider skills

Each provider drafter (`hostinger-email-drafter`, a future
`gmail-email-drafter`, …) holds its own backend under
`scripts/backends/`. When the agent opens one skill, everything needed to
send via that provider is in one place — no shared folder to hunt through,
no cross-skill imports. Easier for both humans and the agent to reason
about, and a broken backend can only affect its own provider.

## Credentials

One `.env` at the project root holds `<PROVIDER>_API_TOKEN` for each
provider. It's the single source of truth for secrets, read via
`env_utils.py`. `.env` is gitignored; `.env.example` documents the keys.

## Token-cost sketch

- MCP-per-email: ~N verbose responses + discovery ≈ thousands of tokens,
  scaling with N.
- Generated backend: one `send_batch.py` invocation returning ~N short
  lines ≈ tens of tokens, roughly flat in N.

The generator's own cost (probing + writing files) is paid once, not per
send.
