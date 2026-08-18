#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if [[ ! -x node_modules/.bin/vite ]]; then
	echo "Missing frontend dependencies. Run 'make setup' first." >&2
	exit 1
fi

npm run build

echo
echo "Production frontend built in ${ROOT_DIR}/build."
