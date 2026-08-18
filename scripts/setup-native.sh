#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
	cp .env.example .env
	echo "Created .env from .env.example. Update its PostgreSQL, MinIO, and secret values before starting the app."
fi

if ! command -v python3 >/dev/null 2>&1; then
	echo "Python 3.11 or 3.12 is required." >&2
	exit 1
fi

python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
case "$python_version" in
	3.11|3.12) ;;
	*)
		echo "Python 3.11 or 3.12 is required; found ${python_version}." >&2
		exit 1
		;;
esac

if ! command -v node >/dev/null 2>&1; then
	echo "Node.js 22 is required." >&2
	exit 1
fi

node_major=$(node -p 'process.versions.node.split(".")[0]')
if [[ "$node_major" != "22" ]]; then
	echo "Node.js 22 is required; found $(node --version)." >&2
	exit 1
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install "torch<=2.9.1" torchvision torchaudio \
	--index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r backend/requirements.txt

CYPRESS_INSTALL_BINARY=0 ONNXRUNTIME_NODE_INSTALL=skip npm ci --force

openclaw_version='2026.7.1-2'
installed_openclaw_version=''
if command -v openclaw >/dev/null 2>&1; then
	installed_openclaw_version=$(openclaw --version 2>/dev/null | grep -Eo '[0-9]{4}\.[0-9]+\.[0-9]+(-[0-9]+)?' | head -n 1 || true)
fi
if [[ "$installed_openclaw_version" != "$openclaw_version" ]]; then
	npm install --global --no-audit --no-fund "openclaw@${openclaw_version}"
fi

echo
echo "Native dependencies and OpenClaw ${openclaw_version} are ready."
echo "Run 'make dev' for local development or 'make build' for production."
