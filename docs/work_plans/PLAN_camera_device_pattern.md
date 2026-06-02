# Camera + Device Declaration Pattern

**Status:** Design approved 2026-05-26. Not yet implemented.
**Priority:** Medium-high — prerequisite for multi-backend camera support.

---

## Problem

Hardware resources are declared and injected via three incompatible patterns:

| Device | Declared where | Created by | Injected as |
|---|---|---|---|
| Bpod | implicit (always) | HardwareManager | `self.bpod` |
| PulsePal | `required_devices` in task.yaml | HardwareManager | `args_dict["devices"]["pulsepal"]` |
| Cameras | nowhere | task code via `make_camera_client()` | task-local variable |
| Scale | nowhere | task code via `make_scale()` | task-local variable |
| Stage | nowhere | task code inline | task-local variable |

Only one task (`optotagging`) declares `required_devices`. All others implicitly
assume Bpod only. Cameras are constructed ad-hoc inside ~5 tasks; there is no
framework-level visibility into which cameras a task needs.

Adding multi-backend camera support on top of this would create a fourth pattern.
The correct fix is to unify the declaration model before implementing multi-backend.

---

## Design

### 1. `CameraConfig` gains a `name` field; `SetupConfig.cameras` becomes a list

```python
class CameraConfig(BaseModel):
    name: str = ""          # identifier tasks reference: "rce", "flir_top", "flir_side"
    backend: str = "rce"   # "rce" | "flir_bonsai"
    config: str = ""        # RCE only: path to ensemble YAML
    driver: str = "flycap"
    bonsai_exe: str = ""
    workflow: str = ""
    cameras: list[CameraUnit] = []
    n_cameras: int = 1
    fps: int = 60

class SetupConfig(BaseModel):
    cameras: list[CameraConfig] = []   # was: CameraConfig | None = None

    @field_validator("cameras", mode="before")
    @classmethod
    def _coerce_single(cls, v):
        # Silent backwards compat: old dict-format YAML becomes a one-element list
        return [v] if isinstance(v, dict) else v
```

Setup YAML — mixed-backend rig:
```yaml
cameras:
  - name: rce
    backend: rce
    config: /mnt/maindata/msw_configs/device_configs/cameras/setup-1.cameras.yaml
  - name: flir_top
    backend: flir_bonsai
    driver: flycap
    cameras:
      - index: 0
        fps: 60
```

### 2. Task YAML declares `required_cameras` alongside `required_devices`

```yaml
default:
  required_devices:
    - bpod
  required_cameras: []              # [] = no cameras (default for most tasks)
  # required_cameras: [rce]         # opt-in by name
  # required_cameras: [rce, flir_top]
  # absent/null = all setup cameras (backwards compat for tasks not yet updated)
```

### 3. evaluate.py — filter cameras, same location as device resolution

```python
def _filter_cameras(
    setup_cameras: list[CameraConfig],
    required: list[str] | None,
) -> list[CameraConfig]:
    if required is None:          # key absent → all (backwards compat)
        return setup_cameras
    if not required:              # [] → none
        return []
    names = set(required)
    missing = names - {c.name for c in setup_cameras}
    if missing:
        logging.warning("required_cameras not found on setup: %s", sorted(missing))
    return [c for c in setup_cameras if c.name in names]
```

Called from `_resolve_setup_config_ports`:
```python
if setup_config and setup_config.cameras:
    required = patched_settings.get("required_cameras")
    filtered = _filter_cameras(setup_config.cameras, required)
    if filtered:
        args_dict["cameras_config"] = filtered   # list[CameraConfig]
```

### 4. execute.py — create client, inject, guarantee cleanup

```python
def run_task(**args_dict):
    conductor = None
    cameras_config = args_dict.get("cameras_config")
    if cameras_config:
        from murineshiftwork.hardware.camera.client import make_camera_client
        conductor = make_camera_client(
            cameras_config,
            config_file_camera=args_dict.get("config_file_camera", ""),
            output_dir=args_dict.get("out_path", ""),
        )
        args_dict["cameras"] = conductor           # standard injection key

    with HardwareManager(device_list) as devices:
        args_dict["bpod"] = devices.get("bpod")
        args_dict["devices"] = devices
        try:
            mod.run_task(**args_dict)
        finally:
            if conductor is not None:
                conductor.stop()                   # framework guarantees teardown
```

### 5. `make_camera_client` accepts a list; returns unified interface

```python
def make_camera_client(
    cameras_config: list[CameraConfig],
    config_file_camera: str = "",
    output_dir: str = "",
) -> RceConductorAdapter | FlirBonsaiClient | MultiCameraClient | None:
    clients = [_make_single(c, config_file_camera, output_dir) for c in cameras_config]
    clients = [c for c in clients if c is not None]
    if not clients:
        return None
    return clients[0] if len(clients) == 1 else MultiCameraClient(clients)
```

`MultiCameraClient` is a trivial fan-out wrapper that calls each method on all
underlying clients: `start`, `setup_agents`, `initialize_acquisition`,
`start_preview`, `start_recording`, `stop_acquisition`, `stop`.

### 6. Task code — before and after

Before (every video task today):
```python
def prepare(self):
    self.conductor = make_camera_client(
        cameras_config=self.input_kwargs.get("cameras_config"),
        config_file_camera=self.input_kwargs.get("config_file_camera", ""),
        output_dir=self.input_kwargs.get("out_path", ""),
    )
```

After:
```python
def prepare(self):
    self.cameras = self.input_kwargs.get("cameras")  # framework built it
```

Tasks still control WHEN recording starts/stops (`self.cameras.start_recording()`
etc.) — only construction and teardown move to the framework.

---

## Separation of concerns

| Concern | Owner |
|---|---|
| Which cameras are physically present | Setup YAML (`cameras:` list) |
| Which cameras this task needs | Task YAML (`required_cameras:`) |
| Creating the client + guarantee stop | execute.py (framework) |
| Recording lifecycle (start/stop timing) | Task code |

---

## Migration steps

1. `models.py`: add `name: str` to `CameraConfig`; change `SetupConfig.cameras` to
   `list[CameraConfig] = []`; add `_coerce_single` validator for backwards compat.
2. `client.py`: add `MultiCameraClient`; change `make_camera_client` to accept
   `list[CameraConfig]`.
3. `evaluate.py`: add `_filter_cameras`; call from `_resolve_setup_config_ports`.
4. `execute.py`: create camera client, inject as `args_dict["cameras"]`, cleanup in finally.
5. Task updates (~5 tasks with video): replace `make_camera_client(...)` call in
   `prepare()` with `self.cameras = self.input_kwargs.get("cameras")`.
6. Task YAMLs: add `required_cameras: [rce]` (or appropriate name) to tasks that use video;
   leave absent in tasks that don't (backwards compat).
7. `setup-1.yaml` in `msw_configs`: `cameras: {…}` → `cameras: [{name: rce, …}]`
   (validator handles old format automatically during transition).

---

## Scope note: scale and stage

Scale and stage devices have the same structural problem (created inline in task code,
not declared). They can follow the same pattern later but are lower urgency — both are
single-instance, their ad-hoc instantiation is less error-prone than cameras, and there
are fewer tasks that use them. Address in a second pass after cameras are clean.
