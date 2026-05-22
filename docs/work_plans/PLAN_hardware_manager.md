# Hardware Manager Design Plan

> **SUPERSEDED by `MASTER_PLAN.md` §3 (2026-05-22).** Content preserved for reference.

*Created 2026-05-22 — branch `ft/msw-agent`*

---

## Goal

Move hardware lifecycle (open, retry, preflight, close) out of `TaskProcess`
into a thin manager layer.  Tasks receive ready-to-use handles; they do not know
or care which device type is underneath.

---

## Design principle: Bpod is not special

Bpod is the first and currently most-used device, but it must be treated as one
concrete implementation of a generic device interface.  Future tasks may run on
Harp, PyControl, or no Bpod at all (some tasks already operate without one).

> **Review note**: The SetupConfig `devices:` dict already expresses device type
> as a string key (e.g. `type: bpod`).  When a second hardware backend (Harp,
> PyControl) is added, it should implement the same `DeviceProtocol` and be
> constructible via the same factory lookup — no special-casing in `TaskProcess`.
> Treat replaceable hardware as a first-class design goal, not a future refactor.

---

## Class hierarchy

```
DeviceProtocol          (typing.Protocol — structural, no inheritance required)
  ├── BpodDevice        hardware/bpod/device.py  — wraps BpodFactory
  ├── ScaleDevice       hardware/scale/device.py  — future
  └── PulsePalDevice    hardware/pulsepal/device.py  — future

HardwareManager         hardware/manager.py
  owns: list[DeviceProtocol]
  returns: dict[str, handle]  (name → raw device object for the task)
```

### DeviceProtocol interface

```python
class DeviceProtocol(Protocol):
    name: str                    # key used in devices dict, e.g. "bpod"
    def preflight(self) -> None  # check port reachable; raise IOError/ValueError
    def connect(self) -> None    # open connection; raise RuntimeError after retries
    def disconnect(self) -> None # close gracefully; never raises
    def handle(self) -> Any      # property — raw object passed to task
```

---

## Call chains

**Session start (from CLI):**
```
msw run
  → execute.py: build device list from SetupConfig.devices
  → HardwareManager([BpodDevice(port)])
  → HardwareManager.__enter__()
    → BpodDevice.preflight()  →  test_serial_port_is_accessible(port)
    → BpodDevice.connect()    →  BpodFactory(port).open()
      → BpodFactory.open()  →  _create_bpod_object()  →  Bpod(port)  [retry loop]
  → returns {"bpod": <Bpod instance>}
  → TaskProcess(bpod=devices["bpod"], ...)
  → TaskProcess.init_task()  →  Task(bpod=devices["bpod"], **kwargs)
  → TaskRunner.run()  →  StateMachine(bpod=self.bpod)  →  bpod.send_state_machine(sma)
```

**Session end:**
```
TaskProcess.__exit__()
  → HardwareManager.__exit__()
    → BpodDevice.disconnect()  →  BpodFactory.close_safely()
      → bpod.close()  →  serial port released
```

**No hardware (simulate mode or hardware-free task):**
```
msw run --simulate
  → HardwareManager([])  →  devices = {}
  → TaskProcess(bpod=SimBpod(), ...)  [existing path, unchanged]
```

---

## BpodDevice stub

`hardware/bpod/device.py` — to be written in the implementation sprint:

```python
class BpodDevice:
    name = "bpod"

    def __init__(self, serial_port, workspace_path=None, session_name=None,
                 connect_retries=3, retry_delay_s=2.0):
        self._factory = BpodFactory(serial_port, workspace_path, session_name,
                                    connect_retries, retry_delay_s)

    def preflight(self):
        if not test_serial_port_is_accessible(self._factory.serial_port):
            raise IOError(f"Bpod port not accessible: {self._factory.serial_port}")

    def connect(self):
        self._factory.open()   # retry loop inside BpodFactory.open()

    def disconnect(self):
        self._factory.close_safely()

    @property
    def handle(self):
        return self._factory   # tasks use BpodFactory as the Bpod proxy
```

---

## Implementation scope

| Step | Status | Notes |
|---|---|---|
| `DeviceProtocol` + `HardwareManager` | **Done** — `hardware/manager.py` | Stub only; not wired to `TaskProcess` yet |
| `BpodDevice` | **Planned** — `hardware/bpod/device.py` | Thin wrapper around `BpodFactory` |
| Wire into `execute.py` | **Planned** | Replace `TaskProcess(serial_port_bpod=...)` path |
| Wire into `TaskProcess.__init__` | **Planned** | Accept `devices` dict; deprecate `serial_port_bpod=` |
| `ScaleDevice`, `PulsePalDevice` | **Future** | Only after Bpod device is validated in production |

**Do not implement** `HardwareManager` cross-session reuse (keep-alive between trials) in this sprint.
Validate the per-session open/close pattern in production first; mark as consideration for
multi-session agent pattern once stable.

---

## What does NOT change (in this sprint)

- `BpodFactory` API — remains the low-level connection object
- `TaskProcess` bpod-injection path (`bpod=` kwarg) — still works unchanged
- `SimBpod` path — unchanged; no device wrapping needed for simulation
- Task code — tasks still receive a bpod object; they do not call `HardwareManager`
