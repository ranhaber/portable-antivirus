#!/bin/sh
# Install mount automation for a development checkout on the Radxa.
# Run from the repository root: sudo sh deploy/install-dev.sh
set -e

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"
RUNTIME_DIR="$INSTALL_DIR/var/run/portable-av"

echo "Install dir: $INSTALL_DIR"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: venv python not found at $VENV_PYTHON" >&2
    echo "Create it first: python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt" >&2
    exit 1
fi

if ! command -v ntfs-3g >/dev/null 2>&1; then
    echo "WARNING: ntfs-3g not found. Install with: sudo apt install -y ntfs-3g" >&2
fi

"$VENV_PYTHON" -m pip install -e "$INSTALL_DIR" >/dev/null

install -m 0755 "$INSTALL_DIR/deploy/bin/portable-av-mount" /usr/local/bin/portable-av-mount

mkdir -p /etc/portable-av
cat > /etc/portable-av/portable-av.env <<EOF
PORTABLE_AV_INSTALL_DIR=$INSTALL_DIR
PORTABLE_AV_PYTHON=$VENV_PYTHON
PORTABLE_AV_RUNTIME=$RUNTIME_DIR
PORTABLE_AV_API_HOST=127.0.0.1
PORTABLE_AV_API_PORT=8080
EOF

install -m 0644 "$INSTALL_DIR/deploy/systemd/portable-av-mount@.service" /etc/systemd/system/portable-av-mount@.service
install -m 0644 "$INSTALL_DIR/deploy/udev/99-portable-av.rules" /etc/udev/rules.d/99-portable-av.rules

mkdir -p /mnt/portable-av "$RUNTIME_DIR"

systemctl daemon-reload
udevadm control --reload-rules
udevadm trigger

echo "Done. Env written to /etc/portable-av/portable-av.env"
echo "Wrapper installed at /usr/local/bin/portable-av-mount"
