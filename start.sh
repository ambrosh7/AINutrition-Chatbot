#!/bin/sh
set -eu

echo "Railway start: PORT=${PORT:?PORT env var is required}"
echo "Working dir: $(pwd)"
echo "Python: $(python -V)"

exec uvicorn app.main:create_app \
  --factory \
  --app-dir backend \
  --host 0.0.0.0 \
  --port "$PORT"
