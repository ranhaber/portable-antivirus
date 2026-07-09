# Deploy Assets

Install these files on the Radxa target after the application is deployed to `/opt/portable-av/`.

## udev

```bash
sudo cp deploy/udev/99-portable-av.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## systemd

```bash
sudo cp deploy/systemd/portable-av-engine.service /etc/systemd/system/
sudo cp deploy/systemd/portable-av-mount@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portable-av-engine.service
```

## Runtime directories

```bash
sudo mkdir -p /mnt/portable-av /run/portable-av /etc/portable-av /var/lib/portable-av
sudo chown portable-av:portable-av /run/portable-av /var/lib/portable-av
```

The engine writes `/run/portable-av/internal.token` on startup. The mount helper reads the same file when notifying `POST /api/v1/internal/drive`.
