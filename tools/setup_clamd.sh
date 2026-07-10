#!/bin/sh
# Set up clamd + clamdscan tuned for the 1 GB Radxa board.
# Run with sudo: sudo sh tools/setup_clamd.sh
set -e

CONF=/etc/clamav/clamd.conf

echo "=== Install clamdscan client ==="
if ! command -v clamdscan >/dev/null 2>&1; then
    apt-get update
    apt-get install -y clamdscan
fi

echo "=== Ensure log + run directories ==="
mkdir -p /var/log/clamav /run/clamav
chown clamav:clamav /var/log/clamav /run/clamav

echo "=== Tune clamd.conf for low memory ==="
# Helper: set a key to a value, replacing any existing (possibly commented) line.
set_conf() {
    key="$1"
    val="$2"
    # Drop existing definitions (commented or not), then append the desired one.
    sed -i "/^[#[:space:]]*${key}[[:space:]]/d" "$CONF"
    printf '%s %s\n' "$key" "$val" >> "$CONF"
}

# Fewer worker threads: each scan thread can allocate scan buffers.
set_conf MaxThreads 2
set_conf MaxConnectionQueueLength 5
# Do NOT keep a second DB copy in RAM during reload (halves peak memory).
set_conf ConcurrentDatabaseReload no
# Let the kernel reclaim rather than the daemon dying uncleanly.
set_conf ExitOnOOM true
# Idle scan threads release memory sooner.
set_conf IdleTimeout 30
# Bound per-file work to keep buffers small on this board.
set_conf MaxScanSize 100M
set_conf MaxFileSize 50M

echo "=== Enable + start daemon ==="
systemctl enable clamav-daemon.service >/dev/null 2>&1 || true
systemctl restart clamav-daemon.service

echo "=== Wait for socket + DB load ==="
SOCK=/run/clamav/clamd.ctl
for i in $(seq 1 60); do
    if [ -S "$SOCK" ] && clamdscan --version >/dev/null 2>&1; then
        if clamdscan --ping 1 >/dev/null 2>&1; then
            echo "clamd responding after ${i}s"
            break
        fi
    fi
    sleep 1
done

echo "=== clamd status ==="
systemctl status clamav-daemon.service --no-pager -l | head -15 || true
clamdscan --version || true
echo "Done."
