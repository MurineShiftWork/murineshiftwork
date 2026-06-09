# MSW Plugin System

MSW supports two independent plugin entry-point groups. A package may implement
one or both depending on its role.

---

## Plugin types

### 1. CLI plugin (`msw.cli`)

Adds subcommands to the `msw` CLI. Loaded at parser construction time.

```toml
[project.entry-points."msw.cli"]
oe = "msw_open_ephys.cli:register"
```

The `register` function receives the top-level `subparsers` object and adds
its own subparser(s):

```python
def register(subparsers) -> None:
    p = subparsers.add_parser("oe", help="Open Ephys GUI control")
    sub = p.add_subparsers(dest="oe_command", required=True)
    # add status / preview / record / stop subparsers ...
```

Result: `msw oe status`, `msw oe record`, etc.

### 2. Host session plugin (`msw.host`)

Provides an acquisition system that MSW can attach to before running a task.
Used by `msw run --host <name>`.

```toml
[project.entry-points."msw.host"]
openephys = "msw_open_ephys.session:OpenEphysHostSession"
```

The class must satisfy `HostSessionProtocol` from `msw-plugin-api`:

```python
from msw_plugin_api import HostSessionInfo, HostSessionProtocol  # optional import

class OpenEphysHostSession:
    def attach(self, **kwargs) -> HostSessionInfo:
        """Start the acquisition system and return session metadata."""
        ...

    def start(self) -> None:
        """Begin recording (called after MSW task is ready)."""
        ...

    def stop(self) -> None:
        """Stop recording and clean up."""
        ...
```

Result: `msw run -s subject -t sequence --host openephys` discovers
`OpenEphysHostSession` via the `openephys` entry point, calls `.attach()`,
and writes the returned `HostSessionInfo` into the session YAML under
`host_acquisition:`.

---

## Plugin API package (`msw-plugin-api`)

`pip install msw-plugin-api` provides the shared types. Zero deps (stdlib only).

```python
from msw_plugin_api import HostSessionInfo, HostSessionInfoProtocol, HostSessionProtocol
```

| Symbol | Type | Purpose |
|---|---|---|
| `HostSessionInfo` | dataclass | Concrete return type from `.attach()` |
| `HostSessionInfoProtocol` | `runtime_checkable Protocol` | Structural check on info objects |
| `HostSessionProtocol` | `runtime_checkable Protocol` | Structural check on session plugins |

Plugins may return `HostSessionInfo` directly or return any object whose
attributes satisfy `HostSessionInfoProtocol` — MSW accepts either via
structural typing.

---

## MSW attach side

`hardware/host_session.py` (renamed from `parent_session.py`) provides the
factory:

```python
def make_host_session(session_type: str, **kwargs) -> HostSessionProtocol:
    for ep in entry_points(group="msw.host"):
        if ep.name == session_type:
            cls = ep.load()
            session = cls(**kwargs)
            if not isinstance(session, HostSessionProtocol):
                raise TypeError(f"{ep.name!r} does not satisfy HostSessionProtocol")
            return session
    raise ValueError(f"No msw.host plugin registered for {session_type!r}")
```

After `make_host_session()` returns, MSW calls:

```python
info = session.attach(
    subject=subject,
    local_path=out_path,
    remote_path=setup_config.open_ephys_remote_path,
    ...
)
# info is HostSessionInfo — written to session YAML under host_acquisition:
```

The `host_acquisition:` block in the session YAML mirrors the `HostSessionInfo`
fields so post-processing can locate the neural data directory without knowing
which backend was used.

---

## Adding a new host plugin

1. Implement `attach() / start() / stop()` returning `HostSessionInfo`
2. Declare `[project.entry-points."msw.host"] myname = "my_pkg.session:MySession"`
3. Add `msw-plugin-api` to dependencies
4. Optionally implement a CLI plugin under `msw.cli` for direct control

---

## Future plugin types

The entry-point group pattern is extensible. Candidate future groups:

| Group | Purpose |
|---|---|
| `msw.host` | Acquisition system plugins (implemented) |
| `msw.cli` | CLI subcommand plugins (implemented) |
| `msw.task` | External task packages (partially — `msw.tasks` group exists) |
| `msw.reader` | Session reader plugins for post-processing |
| `msw.hardware` | Custom hardware device drivers |
