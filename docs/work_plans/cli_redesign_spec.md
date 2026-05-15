# CLI Redesign Spec — Setup/Subject/Task Config Split

## Status
Design complete, not yet implemented. See migration trajectory below.

## Motivation

Current problems:
- Hardware addresses (serial ports, motor IDs) are scattered across CLI flags, `-meta` args,
  `~/.murineshiftwork/` files, and hardcoded Python dicts.
- Subject settings live in one monolithic INI file; subjects are tied to one setup implicitly.
- Calibration data (water, stage) lives in per-setup CSV/YAML files in `~/.murineshiftwork/`
  passed as CLI args per run.
- No hardware availability check before files are written.
- `--setup` flag currently only writes to metadata, does nothing structural.

## Config directory

```
/path/to/configs/          # version-controlled separately from the MSW repo
  setups/
    setup_1.yaml
    setup_2.yaml
    setup_npx.yaml
  subjects/
    mouse_01.yaml
    mouse_02.yaml
  cameras/
    setup_1.yaml            # RCE EnsembleAcquisitionConfig YAML (existing format)
    setup_2.yaml
```

Config dir path is dynamic across machines. Passed via `--config-dir /abs/path/to/configs`.
No hardcoded path in code. Future: `MSW_CONFIG_DIR` env var as fallback default.

Filename without extension == setup/subject name. The `name:` field inside the file
must match the filename. Enforced on write, warned on read.

---

## Setup config

One file per physical rig. Owns: hardware topology, device addresses, calibrations,
camera ensemble reference. Does NOT own semantic assignments (which BNC is trial-start,
which port is left reward — those are task settings).

```yaml
# configs/setups/setup_1.yaml
name: setup_1

devices:
  bpod:
    type: bpod
    port_by_path: pci-0000:00:14.0-usb-0:9.1:1.0    # resolved to /dev/ttyACM2 at load

  stage:
    type: stage_tower
    port_by_path: pci-0000:00:14.0-usb-0:9.2:1.0-port0
    baudrate: 115200
    timeout: 0.1
    axes:
      x: {motor_id: 11, position_min: 100, position_max: 600, velocity_max: 200, operating_mode: OP_POSITION}
      y: {motor_id: 12, position_min: 300, position_max: 800, velocity_max: 200, operating_mode: OP_POSITION}
      z: {motor_id: 13, position_min: 280, position_max: 500, velocity_max: 200, operating_mode: OP_POSITION}
    known_positions:
      mid:   {x: 400, y: 570, z: 400}
      back:  {y: 750}
      front: {y: 560}

  pulsepal:                                           # omit entire block if not present
    type: pulsepal
    port_by_path: pci-0000:00:14.0-usb-0:9.3.3:1.0

  scale:                                              # arbitrary extras named by user
    type: serial_generic
    port_by_path: pci-0000:00:14.0-usb-0:9.4.4:1.0

camera_ensemble_config: cameras/setup_1.yaml         # relative to config_dir root

calibrations:
  bpod_valve:
    "1":
      updated: 2026-04-20
      points:                 # [[open_time_ms, delivered_ul], ...]
        - [10, 0.82]
        - [20, 1.71]
        - [30, 2.63]
    "2":
      updated: 2026-04-20
      points:
        - [10, 0.75]
        - [20, 1.53]
        - [30, 2.31]
```

### Device types and pre-run checks

| type | pre-run check |
|------|--------------|
| `bpod` | serial port exists, attempt Bpod connect handshake |
| `pulsepal` | serial port exists, attempt PulsePal connect |
| `stage_tower` | serial port exists (motor ping optional/configurable) |
| `serial_generic` | serial port exists |

New device types: add a new type string, a Pydantic model subclass, and a check function.
Tasks reference devices by name: `setup.devices["bpod"].port` → `/dev/ttyACM2`.

### `port_by_path` resolution

Pydantic field validator at load time:
```python
resolved = Path(f"/dev/serial/by-path/{port_by_path}").resolve()
# raises ValueError if path does not exist on this machine
```
Tasks receive the already-resolved `/dev/ttyXXX` path. The `$(realpath ...)` shell calls
in SERIAL.md are replaced entirely.

### Calibration interface

```python
setup.valve_ms_for_ul(port="1", volume_ul=2.5)   # → float, ms open time
setup.valve_ul_for_ms(port="1", open_ms=20.0)    # → float, ul delivered
# Linear interpolation on calibration points. Extrapolation raises ValueError.
```

### Stage config write-back

`calibrate_stage_tower` currently saves to `~/.murineshiftwork/calibration.stage.{name}.yaml`.
In v1: reading from setup config, writing back directly to `configs/setups/{name}.yaml`
(targeted YAML update of `devices.stage.known_positions` only, no full rewrite).
This is the single source of truth for stage limits.

---

## Subject config

One file per subject. Registration = creating the file. `msw register` creates it.

```yaml
# configs/subjects/mouse_01.yaml
name: mouse_01
registered: 2026-01-15
task_overrides:
  probabilistic_switching_fixedsubjects:
    max_water_ul: 1200
    p_high: 0.8
  airpuff:
    airpuff_duration_ms: 30
```

`task_overrides` maps task name → dict of overrides patched onto task.settings defaults.
Same semantics as current INI subject sections.

---

## Task settings (unchanged structure)

`task.settings` files remain as-is (ConfigObj INI). They own semantic hardware assignments:

```ini
HARDWARE_BNC_TRIAL_START = 1
HARDWARE_BNC_BARCODE = 2
HARDWARE_PORT_LEFT = 1
HARDWARE_PORT_RIGHT = 2
```

Task settings do not know about device addresses — they use integer indices that the task
code maps to `setup.devices["bpod"].port` when opening connections.

---

## Execution config (assembled at runtime)

```python
class ExecutionConfig(BaseModel):
    setup: SetupConfig
    subject: SubjectConfig
    task_settings: dict[str, Any]   # task defaults patched with subject overrides
    namespace: str = "default"      # no effect until namespace logic implemented
    hardware: HardwareAvailability  # populated by pre-run check
```

Assembly order:
1. Load `SetupConfig` from `--config-dir` / `--setup`
2. Load `SubjectConfig` from `--config-dir` / `--subject`
3. Load task.settings, patch with `subject.task_overrides[task_name]`
4. Run hardware pre-run check (all devices in setup.devices)
5. Raise `HardwareNotAvailable` with specific message if any device unreachable
   — no files written yet at this point

---

## CLI flags

```
msw run \
  --config-dir /mnt/maindata/CONFIG_FILES \
  --setup setup_1 \
  --subject mouse_01 \
  --task probabilistic_switching_fixedsubjects \
  --namespace default \
  [--out /mnt/maindata/data/]
```

Removed flags (absorbed into setup config):
- `-b` / `--bpod` (serial port)
- `-stage` (stage serial port)
- `-meta x=11 y=12 z=13` (motor IDs)
- `-cwater` (water calibration file)
- `-cstage` (stage calibration file)
- `-cc` (camera config)

Kept for back-compat in v1 (override setup config if provided, deprecation warning):
- `-b`, `-stage`, `-cwater`, `-cstage`, `-cc`

`--namespace`: always present, default `"default"`, no effect until namespace logic is built.

---

## `~/.murineshiftwork` — fate

| File pattern | Fate |
|---|---|
| `setup*.rce.yaml` | Migrated to `configs/cameras/setup_*.yaml` (copy now) |
| `calibration.water.setup*.csv` | Migrated to `calibrations.bpod_valve` in setup YAML (copy now) |
| `calibration.stage.setup*.yaml` | Migrated to `devices.stage.known_positions` in setup YAML (v1) |
| `msw.debug.stage.config.{hostname}.yaml` | Keep as temp/debug, location unchanged |

After migration: dir retained for machine-local temp/debug files only. Not removed.
Future use: machine-local overrides (e.g., port path override without touching VCS config).

---

## Pydantic model sketch

```python
class SerialDevice(BaseModel):
    type: str
    port_by_path: str

    @field_validator("port_by_path", mode="after")
    def resolve(cls, v):
        p = Path(f"/dev/serial/by-path/{v}").resolve()
        # validation only at check time, not at load time — allows loading config
        # on machines that don't have the hardware
        return str(p)

class AxisConfig(BaseModel):
    motor_id: int
    position_min: int = 1
    position_max: int = 999
    velocity_max: int = 200
    operating_mode: str = "OP_POSITION"

class StageTowerDevice(SerialDevice):
    type: Literal["stage_tower"]
    baudrate: int = 115200
    timeout: float = 0.1
    axes: dict[str, AxisConfig]
    known_positions: dict[str, dict[str, int]] = {}

class BpodDevice(SerialDevice):
    type: Literal["bpod"]

class PulsePalDevice(SerialDevice):
    type: Literal["pulsepal"]

class GenericSerialDevice(SerialDevice):
    type: Literal["serial_generic"]

DeviceUnion = Annotated[
    BpodDevice | PulsePalDevice | StageTowerDevice | GenericSerialDevice,
    Field(discriminator="type")
]

class ValveCalibration(BaseModel):
    updated: date
    points: list[tuple[float, float]]   # [[ms, ul], ...]

class Calibrations(BaseModel):
    bpod_valve: dict[str, ValveCalibration] = {}

class SetupConfig(BaseModel):
    name: str
    devices: dict[str, DeviceUnion]
    camera_ensemble_config: Path | None = None
    calibrations: Calibrations = Calibrations()

    def valve_ms_for_ul(self, port: str | int, volume_ul: float) -> float: ...
    def valve_ul_for_ms(self, port: str | int, open_ms: float) -> float: ...

class SubjectConfig(BaseModel):
    name: str
    registered: date
    task_overrides: dict[str, dict[str, Any]] = {}
```

---

## Migration trajectory

| Version | What changes | Back-compat |
|---------|-------------|-------------|
| v0 (now) | ConfigObj INI, flat CLI args, `~/.murineshiftwork/` files | — |
| v1 | `--config-dir` + `--setup` loads SetupConfig; hardware pre-run check; port resolution from setup config; stage write-back to setup config; `--namespace` flag (no-op); old flags still work with deprecation warning | Old CLI flags override setup config |
| v2 | Subjects migrate to per-subject YAML; `msw register` creates YAML; INI reader kept as fallback with warning | INI still loads if YAML absent |
| v3 | Remove INI fallback; `msw calibrate` CLI for updating calibration points in setup config | — |
| v4 | Namespace logic implemented; task settings optionally validated against per-task Pydantic schema | — |

---

## Open questions (resolved)

- Config dir is dynamic (not shared path across machines) → `--config-dir` required flag, no hardcoded default
- Stage write-back: direct targeted YAML update to setup config (single source of truth)
- Water calibration: list of points in setup config, old CSV arg kept as v1 override
- `port_by_path` validation: at check time (pre-run), not at YAML load time, so config is
  loadable on machines that don't have the specific hardware attached
