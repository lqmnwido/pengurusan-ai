#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if [[ -z "${AGENT_ID:-}" ]]; then
  echo "Usage: make openclaw-agentic-mcp AGENT_ID=<openclaw-agent-id>" >&2
  exit 1
fi
if [[ -z "${AGENTIC_MCP_TOKEN:-}" || "$AGENTIC_MCP_TOKEN" == replace-* ]]; then
  echo "Set a long random AGENTIC_MCP_TOKEN in .env first." >&2
  exit 1
fi

OPENCLAW_EXECUTABLE="${OPENCLAW_COMMAND:-openclaw}"
if [[ "$OPENCLAW_EXECUTABLE" != */* ]]; then
  OPENCLAW_EXECUTABLE="$(command -v "$OPENCLAW_EXECUTABLE" 2>/dev/null || true)"
fi
if [[ -z "$OPENCLAW_EXECUTABLE" || ! -x "$OPENCLAW_EXECUTABLE" ]]; then
  echo "OpenClaw is not installed. Run make setup first." >&2
  exit 1
fi

export OPENCLAW_HOME="${OPENCLAW_HOME:-$PROJECT_ROOT/backend/data/openclaw}"
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$OPENCLAW_HOME}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_STATE_DIR/openclaw.json}"
export PENGURUSAN_AI_API_BASE="${PENGURUSAN_AI_API_BASE:-http://127.0.0.1:8080/api/v1/agentic-workflows}"

SERVER_NAME="pengurusan-agentic-${AGENT_ID//_/-}"
export PROJECT_ROOT AGENT_ID SERVER_NAME
MCP_CONFIG="$(node -e 'console.log(JSON.stringify({command: process.env.PROJECT_ROOT + "/.venv/bin/python", args: [process.env.PROJECT_ROOT + "/scripts/agentic-mcp.py"], env: {PENGURUSAN_AI_API_BASE: process.env.PENGURUSAN_AI_API_BASE, PENGURUSAN_AI_AGENT_ID: process.env.AGENT_ID, AGENTIC_MCP_TOKEN: process.env.AGENTIC_MCP_TOKEN}}))')"

"$OPENCLAW_EXECUTABLE" mcp set "$SERVER_NAME" "$MCP_CONFIG"

AGENT_INDEX="$("$OPENCLAW_EXECUTABLE" agents list --json | node -e 'let input=""; process.stdin.on("data", c => input += c); process.stdin.on("end", () => { const parsed=JSON.parse(input); const list=Array.isArray(parsed)?parsed:(parsed.agents||[]); const index=list.findIndex(item => item.id===process.env.AGENT_ID); if(index<0) process.exit(2); process.stdout.write(String(index)); });')"
"$OPENCLAW_EXECUTABLE" config set "agents.list[$AGENT_INDEX].tools.profile" minimal
"$OPENCLAW_EXECUTABLE" config set "agents.list[$AGENT_INDEX].tools.alsoAllow" "[\"${SERVER_NAME}__*\"]" --strict-json

echo "Registered $SERVER_NAME for OpenClaw agent $AGENT_ID."
echo "Restart the OpenClaw Gateway, then run: openclaw mcp list"
