# Camera Integration — Drop-in Replacement Design

How MSW integrates with camera acquisition systems (RCE, FLIR-Bonsai) as
interchangeable backends behind a single minimal interface.

---

## Design principles

1. MSW owns the interface, not the implementation. The task code only calls
   `start_recording(path, name)` and `stop_recording()`. Everything
   backend-specific — workflow loading, subprocess dispatch, agent discovery,
   camera enumeration — belongs inside the plugin package.

2. Backends are optional. If no camera config is provided, or the package is
   not installed, `make_camera_client()` returns `None` and recording is
   silently skipped.

3. No method bloat from one backend leaking into the interface. The RCE
   adapter has an internal multi-step startup sequence (setup agents →
   initialize acquisition → start recording). That's RCE's concern; MSW sees
   only `start_recording`.

---

## Minimal interface (Protocol)

```python
class CameraClient(Protocol):
    def preflight(self) -> None:
        """Check connectivity / paths before the session starts.
        Raise ValueError or ConnectionError with a human-readable message."""
        ...

    def start_recording(self, output_path: str, session_name: str) -> None:
        """Begin writing frames to output_path/session_name."""
        ...

    def stop_recording(self) -> None:
        """Flush and finalise the recording."""
        ...

    def teardown(self) -> None:
        """Disconnect / terminate subprocess. Called after stop_recording."""
        ...
```

MSW call chain in task code:

```
conductor = make_camera_client(cameras_config)

if conductor:
    try:
        conductor.preflight()
    except (ValueError, ConnectionError) as exc:
        log.warning("Camera preflight failed — running without video: %s", exc)
        conductor = None

if conductor:
    conductor.start_recording(out_path, session_name)

# ... task runs ...

if conductor:
    conductor.stop_recording()
    conductor.teardown()
```

---

## Config model

`CameraConfig` in `murineshiftwork.logic.config.models`:

```python
class CameraConfig(BaseModel):
    backend: str = "rce"       # "rce" | "flir_bonsai"
    config: str = ""           # RCE: path to ensemble YAML; flir_bonsai: unused
    n_cameras: int = 1
    fps: int = 60
    driver: str = "flycap"     # "flycap" | "spinnaker"   (FLIR only)
    workflow: str = ""         # Bonsai workflow stem; auto-derived if empty
    bonsai_exe: str = ""       # explicit path to Bonsai.exe (see note below)
```

**`bonsai_exe` path note**: On Windows, Bonsai installs to
`%LOCALAPPDATA%\Bonsai\Bonsai.exe` — it is not added to PATH by default.
`where bonsai` will usually fail. The explicit `bonsai_exe` field in
`CameraConfig` (or the `BONSAI_EXE` env var) is the correct mechanism.
`msw flir find-bonsai` (see plugin CLI below) can scan known install locations
and print the path to copy into the setup YAML.

Setup YAML examples:

```yaml
# RCE backend
cameras:
  backend: rce
  config: /path/to/ensemble.yaml

# FLIR-Bonsai backend
cameras:
  backend: flir_bonsai
  n_cameras: 2
  fps: 60
  driver: spinnaker
  bonsai_exe: C:\Users\lab\AppData\Local\Bonsai\Bonsai.exe
```

---

## Factory

`murineshiftwork.hardware.camera.client.make_camera_client()`:

```
make_camera_client(cameras_config, config_file_camera="", output_dir="")
  → None                      # no config, or config file path is empty
  → RceConductorAdapter(...)  # backend == "rce"
  → FlirBonsaiClient(...)     # backend == "flir_bonsai"
```

`cli/evaluate.py` injects `setup_config.cameras` into `args_dict["cameras_config"]`
before the task module is called.

---

## RceConductorAdapter

**Package**: `rpi_camera_ensemble` (lazy import inside `start_recording`)

All RCE-internal steps are hidden from MSW:

```
preflight()
  → ping agents / check ensemble config file exists

start_recording(path, name)
  → import Conductor (lazy)
  → suppress_third_party_console_handlers()
  → Conductor(config_file).start()
  → setup_agents()
  → initialize_acquisition(path, name)
  → start_recording()

stop_recording()
  → conductor.stop_acquisition()

teardown()
  → conductor.stop()
```

---

## FlirBonsaiClient

**Package**: `msw_flir_bonsai` (lazy import inside `start_recording`)

FLIR has no agent/node concept. The entire backend is a Bonsai subprocess.
Workflow loading, camera index assignment, and subprocess dispatch are owned
by `msw_flir_bonsai` — MSW does not see them.

```
preflight()
  → check bonsai_exe path exists
  → raise ValueError with hint to run `msw flir find-bonsai` if not found

start_recording(path, name)
  → import MultiCameraRunner (lazy, from msw_flir_bonsai)
  → workflow = cfg.workflow or f"run-flir-{cfg.driver}-{cfg.n_cameras}cam"
  → runner = MultiCameraRunner(workflow, path, name, bonsai_exe, ...)
  → runner.start()   # Popen — subprocess launches Bonsai

stop_recording()
  → runner.stop()

teardown()
  → no-op (subprocess already terminated)
```

---

## Plugin CLI — `msw flir` subcommands

`msw-flir-bonsai` can register hardware-inspection subcommands that appear
under `msw flir ...` when the package is installed. This follows the Python
entry-points plugin pattern (analogous to docker compose plugins / pytest
plugins).

### How it works

`msw-flir-bonsai/pyproject.toml`:
```toml
[project.entry-points."msw.cli"]
flir = "msw_flir_bonsai.cli:app"
```

MSW main CLI at startup:
```python
import importlib.metadata
for ep in importlib.metadata.entry_points(group="msw.cli"):
    app.add_typer(ep.load(), name=ep.name)
```

This is a single small loop added to MSW's CLI initialisation. If
`msw-flir-bonsai` is not installed, `msw flir` does not exist — no error,
no import, no slowdown.

### Proposed subcommands (`msw flir`)

| Subcommand | Purpose |
|---|---|
| `msw flir list-cameras` | Print detected FLIR camera indices and serial numbers |
| `msw flir check-config <path>` | Validate a Bonsai workflow XML and report cameras it expects |
| `msw flir find-bonsai` | Scan known install paths and print the Bonsai.exe location |
| `msw flir test-record` | Short test recording to verify camera + output path |

These require no changes to MSW task code or config loading. The main CLI
constraint is: the entry-point loader must be called *after* the Typer app is
constructed but *before* it is invoked — one place to maintain.

---

## Adding a new backend

1. Add a `backend` value string to `CameraConfig` docstring.
2. Implement a class with the four-method `CameraClient` interface.
   Defer all third-party imports to the method that first needs them.
3. Add a branch in `make_camera_client()`.
4. Optionally register a `msw.cli` entry point in the package for hardware
   inspection subcommands.
5. Add a setup YAML example to this doc.

No task code changes required.

---

## Files

```
src/murineshiftwork/
  hardware/camera/
    __init__.py
    client.py          ← CameraClient Protocol, RceConductorAdapter,
                          FlirBonsaiClient, make_camera_client
  logic/config/
    models.py          ← CameraConfig in SetupConfig
  cli/
    app.py             ← entry-point plugin loader (single loop)
    evaluate.py        ← injects cameras_config into args_dict
```
