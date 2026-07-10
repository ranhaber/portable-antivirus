# Deploy Assets

These files wire USB insertion/removal (udev) to a read-only mount helper (systemd)
that notifies the running engine over the internal API.

Paths are **not** hardcoded. A small wrapper (`bin/portable-av-mount`) reads
`/etc/portable-av/portable-av.env` to locate the install dir, venv Python, and
runtime dir. This lets the same assets work for a production `/opt/portable-av`
install or a development home checkout.

## Development install (Radxa home checkout)

From the repository root on the board:

```bash
sudo sh deploy/install-dev.sh
```

This will:
- `pip install -e .` into `.venv` so `portable_av` is importable anywhere
- install the wrapper to `/usr/local/bin/portable-av-mount`
- write `/etc/portable-av/portable-av.env` pointing at the checkout + `.venv`
- install the systemd template and udev rules
- create `/mnt/portable-av` and the runtime dir
- reload systemd + udev

## Production install (`/opt/portable-av`)

```bash
sudo install -m 0755 deploy/bin/portable-av-mount /usr/local/bin/portable-av-mount
sudo mkdir -p /etc/portable-av
sudo cp deploy/portable-av.env.example /etc/portable-av/portable-av.env   # edit for /opt layout
sudo cp deploy/systemd/portable-av-engine.service /etc/systemd/system/
sudo cp deploy/systemd/portable-av-mount@.service /etc/systemd/system/
sudo cp deploy/udev/99-portable-av.rules /etc/udev/rules.d/
sudo mkdir -p /mnt/portable-av /run/portable-av /var/lib/portable-av
sudo chown portable-av:portable-av /run/portable-av /var/lib/portable-av
sudo systemctl daemon-reload
sudo systemctl enable --now portable-av-engine.service
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## How it flows

1. USB partition appears → udev tags `portable-av-mount@sdX1.service`.
2. The service runs `/usr/local/bin/portable-av-mount --device /dev/sdX1`.
3. The wrapper sources `/etc/portable-av/portable-av.env`, cds into the install
   dir, and runs `python -m portable_av.mount.mount_manager`.
4. The helper mounts read-only (`ro,nosuid,nodev,noexec`), then notifies the
   engine at `POST /api/v1/internal/drive` using the token in
   `$PORTABLE_AV_RUNTIME/internal.token`.

The engine writes `internal.token` on startup; the mount helper must point at
the **same** runtime dir (that's what `PORTABLE_AV_RUNTIME` in the env file does).
