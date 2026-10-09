set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"
PYTHON="${PYTHON:-python3}"
HEALTH_URL="http://${HOST}:${PORT}/health"

cd "$(dirname "$0")/.."

started_pid=""
cleanup() {
  if [[ -n "$started_pid" ]]; then
    kill "$started_pid" 2>/dev/null || true
    wait "$started_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
  echo "Using already running server at ${HOST}:${PORT}"
else
  echo "Starting server at ${HOST}:${PORT} (log: server.log)"
  "$PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" >server.log 2>&1 &
  started_pid=$!
  for _ in $(seq 1 50); do
    curl -fsS "$HEALTH_URL" >/dev/null 2>&1 && break
    sleep 0.2
  done
  curl -fsS "$HEALTH_URL" >/dev/null || { echo "Server did not start"; cat server.log; exit 1; }
fi

"$@"
