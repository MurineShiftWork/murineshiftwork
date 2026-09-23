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
| `.[full]` | all of the above | Full acquisition stack |

```bash
pip install "murineshiftwork[tasks,rce,oe]"   # tasks + cameras + ephys
pip install "murineshiftwork[full]"            # everything
```

## System dependencies

Sound output (reward/feedback chirps) requires the native **PortAudio**
library, which `pip install` does **not** provide — it's a separate OS-level
package, not declared in any `pyproject.toml`. Install it on every rig:

```bash
sudo apt install libportaudio2   # Debian/Ubuntu
brew install portaudio           # macOS
```

Without it, `import sounddevice` fails at import time with
`OSError: PortAudio library not found`. Real sessions degrade silently to
no-sound rather than crashing (see [Sound Output](../setup/sound.md) for why
and how to detect it) — worth verifying explicitly on a fresh rig rather than
relying on a session to surface it.

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
