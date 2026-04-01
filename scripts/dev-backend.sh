#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --directory backend --python 3.12 uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
