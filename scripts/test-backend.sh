#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --directory backend --python 3.12 --extra dev >/dev/null
uv run --directory backend --python 3.12 python -m pytest tests -q
