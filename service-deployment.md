# Deploying the LED Matrix as a systemd Service

## Installation

Copy the service file and enable it:

```bash
sudo cp rpi-matrix.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-matrix
```

## Useful Commands

| Command | Purpose |
|---|---|
| `sudo systemctl status rpi-matrix` | Check service status |
| `sudo journalctl -u rpi-matrix -f` | Follow logs in real time |
| `sudo journalctl -u rpi-matrix --since "1 hour ago"` | View recent logs |
| `sudo systemctl restart rpi-matrix` | Manually restart the service |
| `sudo systemctl stop rpi-matrix` | Stop the service |
| `sudo systemctl disable rpi-matrix` | Disable auto-start on boot |

## How It Works

- The service runs as root, which is required for direct hardware access to the LED matrix.
- `WorkingDirectory` is set to `/home/tajh/lmae` so the app can find `env.ini` with its relative path.
- `RuntimeMaxSec=86400` (24 hours) — systemd kills and restarts the process daily to prevent long-running issues.
- `Restart=on-failure` with `RestartSec=5` — automatically recovers from crashes.
- The service starts after the network is online, so weather API calls succeed on first run.

## Updating the Service

After editing `rpi-matrix.service`:

```bash
sudo cp rpi-matrix.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart rpi-matrix
```
