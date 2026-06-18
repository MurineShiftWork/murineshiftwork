# Installation

## From PyPI (recommended)

```bash
pip install murineshiftwork
```

## Optional extras

| Extra | Installs | Use |
|---|---|---|
| `.[tasks]` | `msw-tasks-core` | Bundled calibration and hardware test tasks |
| `.[qt]` | PyQt6, pyqtgraph | Online plotting panel |
| `.[rce]` | `rpi-camera-ensemble[conductor]` | RPi camera ensemble control |
| `.[oe]` | `msw-open-ephys` | Remote Open Ephys control (start/stop recording) |
| `.[pulsepal]` | `pypulsepal` | PulsePal optogenetic stimulator |
| `.[calibration]` | `serial-scale-hx711`, `serial-scale-bench` | Valve calibration with serial scales |
| `.[keyboard]` | `sshkeyboard` | Remote keyboard input |
| `.[agent]` | `msw-agent` | Log relay daemon for real-time session monitoring |
| `.[full]` | all of the above except `agent` | Full acquisition stack |

```bash
pip install "murineshiftwork[tasks,rce,oe]"   # tasks + cameras + ephys
pip install "murineshiftwork[full]"            # everything except agent
```

## Development install (from source)

```bash
git clone https://github.com/MurineShiftWork/murineshiftwork
cd murineshiftwork
pip install -e ".[dev]"
```

## Verify

```bash
msw --version
msw setup list
```
