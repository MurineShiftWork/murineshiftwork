# Multi-Acquisition Sessions and Photometry Integration

How to insert additional acquisition sources (e.g. fibre photometry) into an MSW
session alongside the main behavioural protocol, with or without a host.

---

## Directory model

Every MSW session lives at:

```
<data_dir>/
└── <subject>/
    └── <session_container>/         ← SESSION dir (shared host container)
        ├── acquisition_manifest.yaml
        └── <acquisition_basename>/  ← ACQUISITION dir (one per protocol run)
            ├── <basename>.msw.session.yaml
            ├── <basename>.msw.df.jsonl
            └── ...
```

For host-linked sessions (e.g. `--host openephys`) the session container is
provided by the external system.  For standalone sessions MSW derives a
container name automatically: `{subject}__{datetime}__session_{task}`.

Multiple acquisitions inside one session container are normal.  Each tool
(MSW behaviour run, photometry, a second behaviour protocol) writes its own
acquisition dir.  The `acquisition_manifest.yaml` in the container lists them
all.

---

## Integration options

### Option 1: Passive parallel recording (recommended starting point)

The simplest approach: MSW and the photometry system record independently.
Post-hoc alignment is done via TTL barcodes.

```
<session_container>/
├── acquisition_manifest.yaml
├── <msw_acquisition>/                  ← MSW behaviour
│   ├── <basename>.msw.session.yaml
│   └── <basename>.msw.df.jsonl
└── <photometry_acquisition>/           ← photometry (separate filesystem)
    └── photometry_raw.hdf5
```

MSW emits a TTL barcode at session start and at every trial boundary via
`ttl-barcoder`.  The photometry system records these on a digital input
channel.  The barcode timestamps align the two datastreams without any direct
software coupling.

**What MSW provides:**
- `session_paths["session_folder"]`: the acquisition dir to log files into
- `session_paths["host_session_name"]`: the session container dir name
- `session_paths["session_basename"]`: the barcode epoch identifier

**What the photometry system needs:**
- Read the MSW session container name (e.g. from a shared config file, a
  lightweight REST call to MSW, or an operator note)
- Save photometry files under a parallel acquisition dir inside that container
- Record TTL barcode events on a digital channel

---

### Option 2: Photometry as an MSW host plugin

If the photometry system exposes an API (HTTP, ZMQ, or similar), implement
`HostSessionProtocol` so MSW can attach to it before the task starts.

```python
# my_photometry_package/msw_host.py
from msw_plugin_api import HostSessionInfo

class PhotometryHostSession:
    name = "photometry"

    def __init__(self, url: str = "localhost:5000") -> None:
        self._url = url

    def attach(self, **kwargs) -> HostSessionInfo | None:
        import requests
        try:
            r = requests.get(f"http://{self._url}/recording", timeout=2)
            info = r.json()          # expects {"session_name": "...", "subject": "..."}
        except Exception as exc:
            return None              # MSW falls back to standalone if None is returned
        return HostSessionInfo(
            backend="photometry",
            session_name=info["session_name"],   # the photometry recording folder name
            subject=info["subject"],
            parent_directory=info.get("data_dir", ""),
        )

    def start(self) -> None:
        import requests
        requests.post(f"http://{self._url}/record/start")

    def stop(self) -> None:
        import requests
        requests.post(f"http://{self._url}/record/stop")
```

Register in `pyproject.toml`:

```toml
[project.entry-points."msw.host"]
photometry = "my_photometry_package.msw_host:PhotometryHostSession"
```

Usage:

```bash
msw run -s mouse001 -t sequence --host photometry:192.168.1.20:5000
```

What happens:
1. `attach()` reads the photometry session name (the folder the photometry
   system is already writing to)
2. `session_name` is stored as `linked_to`, so MSW writes its acquisition
   dir *inside* the photometry session container
3. `start()` / `stop()` synchronise recording lifecycle with the task

The session YAML will contain a `host_session` block:

```yaml
host_session:
  backend: photometry
  session_name: mouse001__20260611_090000__photometry
  subject: mouse001
  parent_directory: /data/photometry_rig
```

---

### Option 3: Shared session container, MSW creates it

When MSW is the session "owner" (no external host), it creates the session
container.  A second tool (photometry, video, etc.) writes into the same
container by being told the container path after MSW starts.

```python
# In a custom task's __init__ or pre-task hook
session_container = Path(session_paths["session_folder"]).parent   # the SESSION dir
photometry_acquisition_dir = session_container / f"{subject}__{dt}__photometry"
photometry_acquisition_dir.mkdir(parents=True, exist_ok=True)

# Tell the photometry controller where to save
photometry_client.set_output_dir(str(photometry_acquisition_dir))
photometry_client.record_start()
```

Because the `acquisition_manifest.yaml` is in the session container and MSW
already wrote the MSW acquisition to it, post-hoc readers can discover all
acquisitions by calling `load_acquisition(session_container_dir)`.

---

### Option 4: OE as host, photometry passive inside same container

The most common multi-modal ephys + photometry + behaviour setup:

```
mouse001__20260611_090000__ephys/        ← SESSION (from OE)
├── acquisition_manifest.yaml            ← written by MSW
├── Record Node 101/                     ← written by OE GUI
├── mouse001__20260611_091200__sequence/ ← ACQUISITION (MSW behaviour)
│   ├── session_manifest.yaml
│   ├── mouse001__20260611_091200__sequence.msw.session.yaml
│   └── mouse001__20260611_091200__sequence.msw.df.jsonl
└── mouse001__20260611_090015__photometry/ ← ACQUISITION (photometry, passive)
    └── photometry_raw.hdf5
```

Setup:
1. Start OE with `oe-remote record --subject mouse001 --acquisition-extension ephys`
2. The photometry system starts recording into `session_container/photometry_acquisition/`
   (operator or script sets this path based on OE's `base_text`)
3. `msw run -s mouse001 -t sequence --host openephys` attaches to OE, finds the
   same session container, writes behaviour acquisition inside it
4. All three systems share a single `session_container`

---

## What any host plugin must provide

```python
from msw_plugin_api import HostSessionInfo, HostSessionProtocol

class MyHostSession:          # HostSessionProtocol is structurally checked: no import needed
    def attach(self, **kwargs) -> HostSessionInfo | None:
        ...
        return HostSessionInfo(
            backend="my_system",
            session_name=...,         # the recording container folder name
            subject=...,
            parent_directory=...,     # where the session container lives on disk
        )

    def start(self) -> None: ...      # called once MSW task is initialised
    def stop(self) -> None: ...       # called at session end (TaskProcess teardown)
```

Key rule: `session_name` must be the **folder name** (not a full path) of the
recording container that already exists on the remote/local system.  MSW will
write its own acquisition dir *inside* that container.

---

## Current limitations

- **Single host per run.** Only one `--host` flag is accepted.  Two parallel
  hosts (e.g. OE + photometry both as plugins) are not directly supported; use
  Option 1 or Option 3 for the second system.

- **No URL config for non-OE hosts.** `SetupConfig.open_ephys_url` is the only
  per-setup persisted host URL.  Other plugins must pass URL via `--host type:url`
  or read it from their own config.  A generic `host_urls: {type: url}` setup
  config field would generalise this.

- **No cross-acquisition alignment primitives.** MSW provides TTL barcodes
  (`ttl-barcoder`) as the alignment primitive.  Higher-level helpers (e.g.
  automatic cross-stream timestamp alignment) are not yet part of the MSW
  post-processing API.

---

## Extending the manifest

When writing a photometry acquisition into a shared session container,
optionally register it in `acquisition_manifest.yaml` so readers discover it:

```python
from murineshiftwork.namespace.manifest import (
    init_acquisition_manifest,
    append_session_to_acquisition,
    finalize_session_in_acquisition,
)

session_container = Path(...)   # the SESSION dir
acq_basename = "mouse001__20260611_090015__photometry"

# idempotent: creates manifest if absent, no-op otherwise
init_acquisition_manifest(session_container, acq_basename)
append_session_to_acquisition(session_container, acq_basename)

# ... run photometry ...

finalize_session_in_acquisition(session_container, acq_basename, status="complete")
```

After this, `load_acquisition(session_container)` returns all acquisitions
(both MSW behaviour and photometry) sorted by datetime.
