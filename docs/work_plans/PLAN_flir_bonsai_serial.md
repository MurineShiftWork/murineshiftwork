# FLIR/Bonsai: serial-number metadata via Bonsai IronPython

## Goal

Each Bonsai camera acquisition writes a small YAML sidecar (`__meta.yaml`) at
startup containing the camera serial number (queried from the hardware).
Python reads these files after Bonsai starts and combines them into the
session-level `.flir.meta.yaml` namespace file.

---

## Why not from config

Serial numbers must not be pre-configured in setup YAMLs:
- The index → serial mapping is not stable across reboots / USB re-enumeration.
- Serials come from the physical device; duplicating them in config creates
  a mismatch hazard with no validation path.

---

## Where the files land

```
out_dir/                                    ← FlirBonsaiClient output_dir
  {session}__cam0__meta.yaml                ← written by Bonsai cam0 at startup
  {session}__cam1__meta.yaml                ← written by Bonsai cam1 at startup
  {session}__cam0/                          ← Bonsai acquisition dir (cam0)
    {session}__cam0__{datetime}/
      {session}__cam0__{datetime}__cam1.avi
      {session}__cam0__{datetime}__cam1.csv
  {session}__cam1/ ...
  {session}.flir.meta.yaml                  ← written by Python, merges above
```

The `{session}__cam{index}__meta.yaml` path is predictable from Python side
without knowing the Bonsai-created datetime subdirectory.

---

## Bonsai workflow change (FlyCapture)

### 1. Add `cam1idx` as third input to the Python transform

The existing Python transform receives `(basepath, session)` via a `rx:Zip`.
Extend it to also receive `cam1idx`:

```xml
<!-- new node: feed cam1idx into the zip -->
<Expression xsi:type="SubscribeSubject">
  <Name>subj-cam1idx</Name>
</Expression>
```

Add a `BehaviorSubject` named `subj-cam1idx` that is set from the existing
externalized `cam1idx` property (same pattern as `subj-cam1fps`).

Change the `rx:Zip` to zip three inputs: basepath, session, cam1idx.

### 2. Update the Python transform script

```python
import os
import clr
from datetime import datetime

clr.AddReference('FlyCapture2Managed')
from FlyCapture2Managed import ManagedBusManager, ManagedCamera

@returns(str)
def process(value):
    basepath = value[0].replace("'", "")
    session  = value[1].replace("'", "")
    cam_idx  = int(value[2])

    # --- query serial ---
    serial = ""
    try:
        bus = ManagedBusManager()
        uid = bus.GetCameraFromIndex(cam_idx)
        cam = ManagedCamera()
        cam.Connect(uid)
        serial = str(cam.GetCameraInfo().serialNumber)
        cam.Disconnect()
    except Exception as ex:
        print(f"[cam_meta] Could not read serial for index {cam_idx}: {ex}")

    # --- write cam_meta sidecar ---
    meta_path = os.path.join(basepath, f"{session}__cam{cam_idx}__meta.yaml")
    with open(meta_path, "w") as f:
        f.write(f"cam_index: {cam_idx}\n")
        f.write(f"serial: '{serial}'\n")
        f.write(f"datetime: '{datetime.now().isoformat(timespec='seconds')}'\n")

    # --- create acquisition directory ---
    dt = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name_dt = "__".join([session, dt])
    acqdir = os.path.join(basepath, session, session_name_dt)
    if os.path.exists(acqdir):
        raise FileExistsError("Acquisition dir exists: " + acqdir)
    os.makedirs(acqdir)

    fullpath = os.path.join(acqdir, session_name_dt)
    print("Session file path: " + fullpath)
    return fullpath
```

### 3. Spinnaker equivalent

For `run-flir-spinnaker-1cam.bonsai`, replace the FlyCapture2Managed calls with
the Spinnaker .NET SDK:

```python
clr.AddReference('SpinnakerC_v140')  # or SpinnakerManaged, check Bonsai pkg
from Spinnaker import ...
```

Or use `extra_props` to pass the serial as `cam1vid.name` if PySpin is
available outside Bonsai and serial can be queried by the Python runner
before launching Bonsai.

---

## Python side (already implemented)

`FlirBonsaiClient._write_flir_meta()` in
`src/murineshiftwork/hardware/camera/client.py`:
- Polls for `{output_dir}/{acq_name}__cam{index}__meta.yaml` for up to 10 s.
- Combines all found files into `{output_dir}/{acq_name}.flir.meta.yaml`.
- Logs a warning and continues without serial if files are not found (workflow
  not yet updated).

---

## Resulting sidecar

```yaml
flir_acq_format_version: 1
session: s001__20260609_143022
datetime: "2026-06-09T14:30:22"
driver: flycap
workflow: run-flir-flycap-1cam
bonsai_exe: "C:/Bonsai/Bonsai.exe"
cameras:
  - cam_index: 0
    serial: "12345678"
    datetime: "2026-06-09T14:30:23"
    bonsai_session: s001__20260609_143022__cam0
  - cam_index: 1
    serial: "87654321"
    datetime: "2026-06-09T14:30:23"
    bonsai_session: s001__20260609_143022__cam1
```

Post-processing resolves `cam_index → serial` from this file.
