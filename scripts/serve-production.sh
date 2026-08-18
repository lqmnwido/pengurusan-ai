#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
	echo "Missing .env. Copy .env.example to .env and configure it first." >&2
	exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
	echo "Missing Python virtual environment. Run 'make setup' first." >&2
	exit 1
fi

if [[ ! -f build/index.html ]]; then
	echo "Missing production frontend. Run 'make build' first." >&2
	exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

if [[ -z "${WEBUI_SECRET_KEY:-}" && -z "${WEBUI_JWT_SECRET_KEY:-}" ]]; then
	echo "WEBUI_SECRET_KEY must be set in .env for production." >&2
	exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

export ENV=prod
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8080}"

cd backend
exec ./start.sh
