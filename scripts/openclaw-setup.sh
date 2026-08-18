#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

OPENCLAW_EXECUTABLE="${OPENCLAW_COMMAND:-openclaw}"
if [[ "$OPENCLAW_EXECUTABLE" != */* ]]; then
  OPENCLAW_EXECUTABLE="$(command -v "$OPENCLAW_EXECUTABLE" 2>/dev/null || true)"
fi
if [[ -z "$OPENCLAW_EXECUTABLE" || ! -x "$OPENCLAW_EXECUTABLE" ]]; then
  echo "OpenClaw is not installed at OPENCLAW_COMMAND. Run make setup first." >&2
  exit 1
fi

export OPENCLAW_HOME="${OPENCLAW_HOME:-$PROJECT_ROOT/backend/data/openclaw}"
export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-$PROJECT_ROOT/backend/data/openclaw}"
export OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_STATE_DIR/openclaw.json}"
export OPENCLAW_WORKSPACE_DIR="${OPENCLAW_WORKSPACE_ROOT:-$OPENCLAW_STATE_DIR/workspaces}"

exec "$OPENCLAW_EXECUTABLE" onboard
