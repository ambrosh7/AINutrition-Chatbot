#!/bin/sh
set -eu

# Resolve PORT in-process so we never pass a literal "$PORT" to uvicorn
# (Railway custom start commands sometimes skip shell expansion).
PORT_VALUE=$(python -c 'import os,sys; v=os.environ.get("PORT","").strip();
sys.exit("PORT env var is required") if not v.isdigit() else print(v)')

echo "Railway start: PORT=${PORT_VALUE}"
echo "Working dir: $(pwd)"
echo "Python: $(python -V)"

exec uvicorn app.main:create_app \
  --factory \
  --app-dir backend \
  --host 0.0.0.0 \
  --port "${PORT_VALUE}"
