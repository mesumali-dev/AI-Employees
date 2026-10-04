#!/bin/bash
# OpenAI Agents Python Documentation Fetcher
# Pre-configured for OpenAI Agents SDK - token efficient via shell pipeline filtering
#
# Usage:
#   ./fetch-docs.sh --topic agents
#   ./fetch-docs.sh --topic handoffs --verbose
#   ./fetch-docs.sh "How to create an agent with tools"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pre-configured library ID for OpenAI Agents Python
LIBRARY_ID="/websites/openai_github_io_openai-agents-python"

# Common topics mapping
declare -A TOPICS=(
  ["agents"]="How to create and configure agents in OpenAI Agents SDK"
  ["handoffs"]="How to implement handoffs between agents"
  ["guardrails"]="How to add guardrails and safety constraints to agents"
  ["sessions"]="How to manage sessions and conversation state"
  ["tracing"]="How to enable and use tracing for debugging agents"
  ["tools"]="How to define and use tools with agents"
  ["streaming"]="How to implement streaming responses with agents"
  ["context"]="How to manage context and memory in agents"
  ["quickstart"]="Getting started with OpenAI Agents SDK Python quickstart"
  ["examples"]="Code examples for OpenAI Agents Python SDK"
  ["runner"]="How to use the Runner class to execute agents"
  ["lifecycle"]="Agent lifecycle and execution flow"
)

# Parse arguments
TOPIC=""
QUERY=""
MODE="code"
VERBOSE=0

usage() {
  cat << USAGE
Usage: $0 [OPTIONS] [QUERY]

OpenAI Agents Python documentation fetcher with token-efficient filtering.

OPTIONS:
  --topic TOPIC    Use predefined topic (see list below)
  --mode MODE      Mode: code (default) or info
  --verbose, -v    Show token statistics
  --list-topics    List available topics
  --help, -h       Show this help

TOPICS:
  agents       How to create and configure agents
  handoffs     How to implement handoffs between agents
  guardrails   How to add guardrails and safety constraints
  sessions     How to manage sessions and conversation state
  tracing      How to enable and use tracing for debugging
  tools        How to define and use tools with agents
  streaming    How to implement streaming responses
  context      How to manage context and memory
  quickstart   Getting started guide
  examples     Code examples
  runner       How to use the Runner class
  lifecycle    Agent lifecycle and execution flow

EXAMPLES:
  $0 --topic agents
  $0 --topic handoffs --verbose
  $0 "How to create an agent with custom tools"
  $0 --topic quickstart --mode info
USAGE
  exit 1
}

list_topics() {
  echo "Available topics for OpenAI Agents Python:"
  echo ""
  for topic in "${!TOPICS[@]}"; do
    printf "  %-12s - %s\n" "$topic" "${TOPICS[$topic]}"
  done
  exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --topic)
      TOPIC="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    --list-topics)
      list_topics
      ;;
    -h|--help)
      usage
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      ;;
    *)
      QUERY="$1"
      shift
      ;;
  esac
done

# Determine final query
if [ -n "$TOPIC" ]; then
  if [ -n "${TOPICS[$TOPIC]:-}" ]; then
    QUERY="${TOPICS[$TOPIC]}"
    [ $VERBOSE -eq 1 ] && echo "📋 Using topic '$TOPIC': $QUERY" >&2
  else
    echo "Error: Unknown topic '$TOPIC'. Use --list-topics to see available topics." >&2
    exit 1
  fi
elif [ -z "$QUERY" ]; then
  echo "Error: Please provide a query or use --topic" >&2
  usage
fi

[ $VERBOSE -eq 1 ] && echo "📚 Fetching OpenAI Agents Python documentation..." >&2

# Build parameters JSON
PARAMS=$(cat <<JSON
{
  "libraryId": "$LIBRARY_ID",
  "query": "$QUERY"
}
JSON
)

# Fetch raw documentation using mcp-client.py
# The mcp-client.py handles starting/stopping the Context7 MCP server automatically
[ $VERBOSE -eq 1 ] && echo "🚀 Starting Context7 MCP server..." >&2

RAW_JSON=$(python3 "$SCRIPT_DIR/mcp-client.py" call \
  -s "npx -y @upstash/context7-mcp" \
  -t query-docs \
  -p "$PARAMS" 2>&1)

# Check if the command failed
if [ $? -ne 0 ]; then
  echo "Error running MCP client: $RAW_JSON" >&2
  exit 1
fi

[ $VERBOSE -eq 1 ] && echo "✅ Context7 MCP server stopped" >&2

# Extract text from JSON
if command -v jq &> /dev/null; then
  RAW_TEXT=$(echo "$RAW_JSON" | jq -r '.content[0].text // empty')
else
  RAW_TEXT=$(echo "$RAW_JSON" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("content", [{}])[0].get("text", ""))')
fi

if [ -z "$RAW_TEXT" ]; then
  echo "Error: No documentation received from Context7" >&2
  exit 1
fi

# Calculate raw token count
if [ $VERBOSE -eq 1 ]; then
  RAW_WORDS=$(echo "$RAW_TEXT" | wc -w)
  RAW_TOKENS=$((RAW_WORDS * 13 / 10))
  echo "📊 Raw response: ~$RAW_WORDS words (~$RAW_TOKENS tokens)" >&2
fi

# Filter using shell tools (0 LLM tokens!)
OUTPUT=""

if [ "$MODE" = "code" ]; then
  # Code mode: Extract code examples and API signatures
  CODE_BLOCKS=$(echo "$RAW_TEXT" | "$SCRIPT_DIR/extract-code-blocks.sh" 5)

  if [ -n "$CODE_BLOCKS" ] && [ "$CODE_BLOCKS" != "# No code blocks found" ]; then
    OUTPUT+="## Code Examples\n\n$CODE_BLOCKS\n"
  fi

  # Extract Python-specific signatures
  SIGNATURES=$(echo "$RAW_TEXT" | "$SCRIPT_DIR/extract-python-signatures.sh" 3)

  if [ -n "$SIGNATURES" ]; then
    OUTPUT+="\n## API Signatures\n\n$SIGNATURES\n"
  fi
else
  # Info mode: Extract conceptual content
  CODE_BLOCKS=$(echo "$RAW_TEXT" | "$SCRIPT_DIR/extract-code-blocks.sh" 2)

  if [ -n "$CODE_BLOCKS" ] && [ "$CODE_BLOCKS" != "# No code blocks found" ]; then
    OUTPUT+="## Examples\n\n$CODE_BLOCKS\n"
  fi

  # Extract key paragraphs
  OVERVIEW=$(echo "$RAW_TEXT" | \
    awk 'BEGIN{RS=""; FS="\n"} length($0) > 200 && !/```/{print; if(++count>=3) exit}')

  if [ -n "$OVERVIEW" ]; then
    OUTPUT+="\n## Overview\n\n$OVERVIEW\n"
  fi
fi

# Always add important notes
NOTES=$(echo "$RAW_TEXT" | "$SCRIPT_DIR/extract-notes.sh" 3)

if [ -n "$NOTES" ]; then
  OUTPUT+="\n## Important Notes\n\n$NOTES\n"
fi

# Fallback if no content extracted
if [ -z "$OUTPUT" ]; then
  OUTPUT=$(echo "$RAW_TEXT" | head -c 1000)
  OUTPUT+="\n\n[Response truncated for brevity...]"
fi

# Output filtered content
echo -e "$OUTPUT"

# Show token savings
if [ $VERBOSE -eq 1 ]; then
  FILTERED_WORDS=$(echo -e "$OUTPUT" | wc -w)
  FILTERED_TOKENS=$((FILTERED_WORDS * 13 / 10))
  if [ $RAW_TOKENS -gt 0 ]; then
    SAVINGS=$(( (RAW_TOKENS - FILTERED_TOKENS) * 100 / RAW_TOKENS ))
  else
    SAVINGS=0
  fi

  echo "" >&2
  echo "✨ Filtered output: ~$FILTERED_WORDS words (~$FILTERED_TOKENS tokens)" >&2
  echo "💰 Token savings: ${SAVINGS}%" >&2
fi
