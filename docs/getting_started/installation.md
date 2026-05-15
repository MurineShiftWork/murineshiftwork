# Installation

## From the repo (recommended)

```bash
git clone https://github.com/larsrollik/murineshiftwork
cd murineshiftwork
pip install -e ".[dev]"
```

## Optional extras

```bash
pip install -e ".[qt]"    # PyQt6 + pyqtgraph for online plotting
pip install -e ".[rce]"   # rpi_camera_ensemble for camera control
pip install -e ".[keyboard]"  # sshkeyboard for remote keyboard input
```

## Dependencies in `external/`

The following companion packages live in `external/` and must be installed separately
if needed:

| Package | Purpose |
|---------|---------|
| `external/msw_open_ephys/` | Remote Open Ephys control (start/stop recording) |
| `external/msw_remote_ephys/` | CLI wrapper around Open Ephys HTTP API |
| `external/provision_rpi/` | Ansible playbooks for RPi camera setup |
| `external/remote_python_manager/` | Remote process management over network |

```bash
pip install -e external/msw_open_ephys/
```

## Verify

```bash
msw --version
msw setup list
```
