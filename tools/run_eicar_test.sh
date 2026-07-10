#!/bin/sh
# Run EICAR threat-path validation against the live API.
set -e

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
EICAR_ROOT="$ROOT/tests/fixtures/eicar"
AUTH="Authorization: Bearer dev"

.venv/bin/python tools/write_eicar_fixture.py

echo "=== Start full scan on EICAR fixture ==="
SCAN_JSON=$(curl -s -X POST http://127.0.0.1:8080/api/v1/scan \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"mode\": \"full\", \"scan_root\": \"$EICAR_ROOT\"}")
echo "$SCAN_JSON" | .venv/bin/python -m json.tool
SCAN_ID=$(echo "$SCAN_JSON" | .venv/bin/python -c "import sys,json; print(json.load(sys.stdin)['scan_id'])")

FOUND=0
for i in $(seq 1 120); do
  PROGRESS=$(curl -s http://127.0.0.1:8080/api/v1/scan/progress)
  STATE=$(echo "$PROGRESS" | .venv/bin/python -c "import sys,json; print(json.load(sys.stdin)['state'])")
  THREATS=$(echo "$PROGRESS" | .venv/bin/python -c "import sys,json; print(json.load(sys.stdin)['threats'])")
  STAGE=$(echo "$PROGRESS" | .venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print(d.get('stage'))")
  echo "poll $i: state=$STATE stage=$STAGE threats=$THREATS"
  if [ "$STATE" = "threat_prompt" ]; then
    FOUND=1
    echo "$PROGRESS" | .venv/bin/python -m json.tool
    break
  fi
  if [ "$STATE" = "complete" ] && [ "$THREATS" -gt 0 ]; then
    FOUND=1
    echo "$PROGRESS" | .venv/bin/python -m json.tool
    break
  fi
  if [ "$STATE" = "error" ]; then
    echo "$PROGRESS" | .venv/bin/python -m json.tool
    exit 1
  fi
  sleep 2
done

if [ "$FOUND" != "1" ]; then
  echo "ERROR: EICAR threat not detected"
  exit 1
fi

if [ "$STATE" = "threat_prompt" ]; then
  echo "=== Send threat-action: stop ==="
  curl -s -o /dev/null -w "threat-action HTTP %{http_code}\n" -X POST http://127.0.0.1:8080/api/v1/scan/threat-action \
    -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d '{"action": "stop"}'
  sleep 2
fi

echo "=== Final progress ==="
curl -s http://127.0.0.1:8080/api/v1/scan/progress | .venv/bin/python -m json.tool

echo "=== Detections for $SCAN_ID ==="
.venv/bin/python - <<PY
import sqlite3
from pathlib import Path
scan_id = "$SCAN_ID"
db = Path("var/lib/portable-av/history.db")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
for row in conn.execute(
    "SELECT engine, signature, file_path, action FROM detections WHERE scan_id = ?",
    (scan_id,),
):
    print(dict(row))
for row in conn.execute(
    "SELECT event_type, message FROM events WHERE scan_id = ? AND event_type = 'threat_detected'",
    (scan_id,),
):
    print(dict(row))
PY

echo "EICAR threat-path test passed."
