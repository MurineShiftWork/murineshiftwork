# Installation

## From the repo (recommended)

```bash
git clone https://github.com/larsrollik/murineshiftwork
cd murineshiftwork
pip install -e ".[dev]"
```

## Optional extras

| Extra | Installs | Use |
|---|---|---|
| `.[qt]` | PyQt6, pyqtgraph | Online plotting panel |
| `.[rce]` | `rpi-camera-ensemble[conductor]` | RPi camera ensemble control |
| `.[oe]` | `msw-open-ephys` | Remote Open Ephys control (start/stop recording) |
| `.[pulsepal]` | `pypulsepal` | PulsePal optogenetic stimulator |
| `.[calibration]` | `serial-scale-hx711`, `serial-scale-bench` | Valve calibration with serial scales |
| `.[keyboard]` | `sshkeyboard` | Remote keyboard input |
| `.[agent]` | `fastapi`, `uvicorn` | Setup agent WebSocket broadcast server |

```bash
pip install -e ".[rce,oe]"        # cameras + ephys
pip install -e ".[calibration]"   # valve calibration
```

## Verify

```bash
msw --version
msw setup list
```
