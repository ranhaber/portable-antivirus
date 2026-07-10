#!/bin/sh
# Benchmark clamscan (per-invocation) vs clamdscan (daemon) on the Radxa.
# Reports wall time and peak client RSS, plus EICAR detection result.
set -e

cd "$(dirname "$0")/.."
.venv/bin/python tools/write_eicar_fixture.py >/dev/null
EICAR="$(pwd)/tests/fixtures/eicar/eicar.com"

# Pick a GNU time binary that reports Maximum resident set size.
TIME_BIN=""
if [ -x /usr/bin/time ]; then
    TIME_BIN=/usr/bin/time
fi

run_timed() {
    label="$1"
    shift
    echo "----- $label -----"
    echo "cmd: $*"
    if [ -n "$TIME_BIN" ]; then
        "$TIME_BIN" -v "$@" 2>time.tmp || true
        grep -E "Maximum resident set size|Elapsed \(wall clock\)" time.tmp || true
        rm -f time.tmp
    else
        start=$(date +%s.%N)
        "$@" || true
        end=$(date +%s.%N)
        echo "wall_sec=$(awk "BEGIN{print $end-$start}")"
    fi
    echo
}

echo "=== Daemon resident memory (baseline) ==="
CLAMD_PID=$(pgrep -x clamd | head -1 || true)
if [ -n "$CLAMD_PID" ]; then
    awk '/VmRSS/{print "clamd VmRSS: " $2 " " $3}' /proc/"$CLAMD_PID"/status
else
    echo "clamd not running"
fi
echo

echo "=== free before ==="
free -h
echo

# clamscan: cold, loads DB every time.
run_timed "clamscan EICAR (loads DB)" clamscan --no-summary "$EICAR"

# clamdscan via daemon, fd-passed so the daemon can read user-owned files.
run_timed "clamdscan EICAR --fdpass (daemon)" clamdscan --no-summary --fdpass "$EICAR"

# Second clamdscan to show warm-path cost (no DB reload).
run_timed "clamdscan EICAR --fdpass (warm)" clamdscan --no-summary --fdpass "$EICAR"

echo "=== free after ==="
free -h
