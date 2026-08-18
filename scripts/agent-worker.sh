#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -f .env || ! -x .venv/bin/python ]]; then
	echo "Missing .env or .venv. Run 'make setup' first." >&2
	exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

export PYTHONPATH="$ROOT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
exec .venv/bin/python -m open_webui.agents.worker
