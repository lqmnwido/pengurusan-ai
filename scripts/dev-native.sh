#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
	echo "Missing .env. Run 'make setup' first." >&2
	exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
	echo "Missing Python virtual environment. Run 'make setup' first." >&2
	exit 1
fi

if [[ ! -x node_modules/.bin/vite ]]; then
	echo "Missing frontend dependencies. Run 'make setup' first." >&2
	exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

# shellcheck disable=SC1091
source .venv/bin/activate

backend_pid=''
frontend_pid=''
worker_pid=''

cleanup() {
	trap - EXIT INT TERM
	[[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
	[[ -n "$worker_pid" ]] && kill "$worker_pid" 2>/dev/null || true
	[[ -n "$backend_pid" ]] && kill "$backend_pid" 2>/dev/null || true
	[[ -n "$frontend_pid" ]] && wait "$frontend_pid" 2>/dev/null || true
	[[ -n "$worker_pid" ]] && wait "$worker_pid" 2>/dev/null || true
	[[ -n "$backend_pid" ]] && wait "$backend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

(
	cd backend
	exec ./dev.sh
) &
backend_pid=$!

if [[ "${TEMPORAL_ENABLED:-false}" == 'true' ]]; then
	(
		cd backend
		exec ../.venv/bin/python -m open_webui.agents.worker
	) &
	worker_pid=$!
fi

./node_modules/.bin/vite dev --host &
frontend_pid=$!

echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8080"
if [[ -n "$worker_pid" ]]; then
	echo "Temporal: agent worker enabled (${TEMPORAL_TASK_QUEUE:-pengurusan-ai-agents})"
fi
echo "Press Ctrl+C to stop all processes."

if [[ -n "$worker_pid" ]]; then
	wait -n "$backend_pid" "$frontend_pid" "$worker_pid"
else
	wait -n "$backend_pid" "$frontend_pid"
fi
