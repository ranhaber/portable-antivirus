#!/bin/bash
HOST="radxa03virus@192.168.7.61"
PASS="radxa"

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 "$HOST" bash -s <<'EOF'
echo "CONNECTED_OK"
echo "=== whoami ==="
whoami
echo "=== hostname ==="
hostname
echo "=== os-release ==="
grep PRETTY_NAME /etc/os-release
echo "=== kernel ==="
uname -a
echo "=== uptime ==="
uptime
echo "=== ip ==="
ip -4 addr show | grep -E "inet " | grep -v 127.0.0.1
EOF
