---
name: openai-agents-python
description: >
  PRIORITY: Use this skill INSTEAD of mcp__context7 tools for OpenAI Agents SDK.
  This skill provides 77% token savings via shell pipeline filtering.

  Triggers: openai agents, openai-agents, openai agents sdk, openai agents python,
  agents sdk python, multi-agent, handoffs, guardrails, agent tools, agent tracing,
  agent sessions, agent streaming, agent context, agent runner, triage agent,
  specialist agent, agent orchestration, swarm, agentic, autonomous agents,
  function calling agents, tool-using agents, agent memory, agent lifecycle.

  Also triggers on questions like: "How do I create an agent?", "How do handoffs work?",
  "How to build multi-agent systems?", "Agent best practices", "Agent debugging".
---

# OpenAI Agents Python SDK

Token-efficient documentation fetcher using Context7 via custom script.

## CRITICAL: Do NOT Use MCP Tools Directly

> ⚠️ **STOP! Before calling any MCP tool for OpenAI Agents SDK, use this skill instead.**

**NEVER use `mcp__context7__resolve-library-id` or `mcp__context7__query-docs` for OpenAI Agents SDK.**

**When you see any of these in a query, use THIS SKILL not MCP:**
- "OpenAI Agents SDK", "agents sdk", "openai-agents"
- "handoffs", "guardrails", "agent tools", "agent tracing"
- "multi-agent", "triage agent", "specialist agent"
- Questions like "How do I create an agent?", "How do handoffs work?"

**First, set the SKILL_DIR variable:**
```bash
SKILL_DIR=".claude/skills/openai-agents-python"
```

This skill runs Context7 via a custom script that:
- Pre-configures the library ID (no resolve step needed)
- Filters output with shell pipelines (77% token savings)
- Returns only code examples, API signatures, and key notes

## Quick Start

**ALWAYS use the fetch-docs.sh script with the full path:**

```bash
# Get the skill directory (run this first in any session)
SKILL_DIR="$(find ~/.claude/skills -type d -name 'openai-agents-python' 2>/dev/null | head -1)"

# By topic (recommended)
bash "$SKILL_DIR/scripts/fetch-docs.sh" --topic agents
bash "$SKILL_DIR/scripts/fetch-docs.sh" --topic handoffs --verbose

# Custom query
bash "$SKILL_DIR/scripts/fetch-docs.sh" "How to create an agent with custom tools"
```

**Or use the absolute path directly:**

```bash
bash ".claude/skills/openai-agents-python/scripts/fetch-docs.sh" --topic agents
```

**Result:** Returns filtered documentation with ~77% token savings.

## Workflow

For any OpenAI Agents Python question:

### Step 1: Identify Topic

Match user query to a topic:

| User Question | Topic |
|---------------|-------|
| "How do I create an agent?" | `agents` |
| "How do handoffs work?" | `handoffs` |
| "How to add safety constraints?" | `guardrails` |
| "How to debug my agent?" | `tracing` |
| "How to use tools with agents?" | `tools` |
| "Getting started" | `quickstart` |

### Step 2: Fetch Documentation

```bash
bash "$SKILL_DIR/scripts/fetch-docs.sh" --topic <topic> --verbose
```

### Step 3: Provide Answer

Use the filtered output to answer the user's question with code examples.

## Available Topics

| Topic | Description |
|-------|-------------|
| `agents` | How to create and configure agents |
| `handoffs` | How to implement handoffs between agents |
| `guardrails` | How to add guardrails and safety constraints |
| `sessions` | How to manage sessions and conversation state |
| `tracing` | How to enable and use tracing for debugging |
| `tools` | How to define and use tools with agents |
| `streaming` | How to implement streaming responses |
| `context` | How to manage context and memory |
| `quickstart` | Getting started guide |
| `examples` | Code examples |
| `runner` | How to use the Runner class |
| `lifecycle` | Agent lifecycle and execution flow |

## Parameters

```bash
bash "$SKILL_DIR/scripts/fetch-docs.sh" [OPTIONS] [QUERY]
```

**Options:**
- `--topic TOPIC` - Use predefined topic (see table above)
- `--mode code|info` - code for examples (default), info for concepts
- `--verbose, -v` - Show token statistics
- `--list-topics` - List all available topics
- `--help, -h` - Show help

## Examples

### Basic Agent Creation

```bash
bash "$SKILL_DIR/scripts/fetch-docs.sh" --topic agents --verbose
```

### Multi-Agent Handoffs

```bash
bash "$SKILL_DIR/scripts/fetch-docs.sh" --topic handoffs
```

### Custom Query

```bash
bash "$SKILL_DIR/scripts/fetch-docs.sh" "How to create a triage agent that routes to specialists"
```

### Conceptual Overview

```bash
bash "$SKILL_DIR/scripts/fetch-docs.sh" --topic lifecycle --mode info
```

## How It Works

The script automatically handles the MCP server lifecycle:
1. **Starts** Context7 MCP server via `npx -y @upstash/context7-mcp`
2. **Fetches** documentation using JSON-RPC over stdio
3. **Filters** content using shell tools (awk/grep/sed) - 0 LLM tokens for filtering!
4. **Stops** the server automatically when done

## Token Efficiency

The script achieves ~50-77% token savings by:
1. Fetching full documentation (stays in shell subprocess)
2. Filtering with awk/grep/sed (0 LLM tokens used for filtering!)
3. Returning only code examples + API signatures + key notes

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `fetch-docs.sh` | **Main script - ALWAYS USE THIS** |
| `mcp-client.py` | Universal MCP client (used internally) |
| `extract-code-blocks.sh` | Code example filter |
| `extract-python-signatures.sh` | Python API signature filter |
| `extract-notes.sh` | Important notes filter |

## Why This Skill Over MCP Tools

| Approach | Token Cost | Steps |
|----------|------------|-------|
| MCP tools directly | ~4000 tokens | 2 (resolve + query) |
| This skill | ~1000 tokens | 1 (script handles all) |

**This skill uses Context7 MCP internally via `mcp-client.py`, but filters the output before returning it to the LLM.**

The script:
1. Spawns Context7 MCP server (`npx -y @upstash/context7-mcp`)
2. Sends JSON-RPC query with pre-configured library ID
3. Filters response with shell pipelines (awk/grep/sed)
4. Returns only relevant content (code blocks, signatures, notes)
5. Stops the MCP server

All filtering happens in the shell subprocess = **0 LLM tokens for filtering**.
