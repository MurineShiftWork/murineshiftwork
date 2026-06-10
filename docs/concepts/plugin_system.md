# MSW Plugin System

Plugins extend MSW via Python entry-point groups. A plugin package typically
registers in two independent groups: one declaring what type of plugin it is,
and one wiring its commands into the `msw` CLI.

---

## CLI registration — `msw.cli` (all plugin types)

Any plugin that exposes user-facing commands registers a `register` function
under `msw.cli`. This is the universal subcommand mechanism — not a plugin
type itself. MSW's parser loads all registered `register` functions at startup.

```toml
[project.entry-points."msw.cli"]
oe = "msw_open_ephys.cli:register"
```

```python
def register(subparsers) -> None:
    p = subparsers.add_parser("oe", help="Open Ephys GUI control")
    sub = p.add_subparsers(dest="oe_command", required=True)
    # add status / preview / record / stop subparsers ...
```

Result: `msw oe status`, `msw oe record`, etc. Every plugin type that has
user-facing commands uses this same pattern.

---

## Plugin type: host session (`msw.host`)

A host session plugin manages an external acquisition system that MSW attaches
to before running a task. The plugin implements `HostSessionProtocol` from
`msw-plugin-api` and declares itself under `msw.host`:

```toml
[project.entry-points."msw.host"]
openephys = "msw_open_ephys.session:OpenEphysHostSession"
```

```python
from msw_plugin_api import HostSessionInfo  # optional — may also return structurally

class OpenEphysHostSession:
    def attach(self, **kwargs) -> HostSessionInfo:
        """Connect to the acquisition system and return session metadata."""
        ...

    def start(self) -> None:
        """Begin recording (called once MSW task is ready)."""
        ...

    def stop(self) -> None:
        """Stop recording and clean up."""
        ...
```

Used via: `msw run -s subject -t sequence --host openephys`

MSW's `make_host_session("openephys", ...)` discovers the class via the
`msw.host` entry point, instantiates it, checks `isinstance(session,
HostSessionProtocol)`, calls `.attach()`, and writes the returned
`HostSessionInfo` into the session YAML under `host_acquisition:`.

A host plugin typically also registers CLI commands via `msw.cli` (e.g.
`msw oe record`) so the same system can be controlled directly.

---

## Plugin API package (`msw-plugin-api`)

`pip install msw-plugin-api` provides the shared types. Zero dependencies.

```python
from msw_plugin_api import HostSessionInfo, HostSessionInfoProtocol, HostSessionProtocol
```

| Symbol | Type | Purpose |
|---|---|---|
| `HostSessionInfo` | dataclass | Concrete return value from `.attach()` |
| `HostSessionInfoProtocol` | `runtime_checkable Protocol` | Structural check on info objects |
| `HostSessionProtocol` | `runtime_checkable Protocol` | Structural check on host session classes |

Plugins may return `HostSessionInfo` directly or return any object whose
attributes satisfy `HostSessionInfoProtocol` — MSW accepts both.

---

## MSW attach side

`hardware/host_session.py` provides the entry-point driven factory:

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

After attaching:

```python
info = session.attach(subject=subject, local_path=out_path, ...)
# HostSessionInfo written to session YAML under host_acquisition:
```

The `host_acquisition:` block records backend, acquisition name, subject, and
remote path so post-processing can locate neural data without knowing which
backend was used.

---

## Adding a new host plugin

1. Implement `attach() / start() / stop()` returning `HostSessionInfo`
2. Declare `[project.entry-points."msw.host"] myname = "my_pkg.session:MySession"`
3. Optionally add `[project.entry-points."msw.cli"] myname = "my_pkg.cli:register"`
4. Add `msw-plugin-api` to dependencies

---

## Future plugin types

`msw.cli` is the shared registration mechanism across all types. New plugin
types add a new entry-point group and a new Protocol in `msw-plugin-api`:

| Group | Type or mechanism | Status |
|---|---|---|
| `msw.cli` | CLI registration — all plugin types | implemented |
| `msw.host` | Host/linked session acquisition systems | implemented |
| `msw.tasks` | External task packages | partial |
| `msw.reader` | Session reader plugins for post-processing | planned |
| `msw.hardware` | Custom hardware device drivers | planned |
