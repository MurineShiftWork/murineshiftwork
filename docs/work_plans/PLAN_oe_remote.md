# Plan: oe-remote extraction, `msw oe` command, `--parent openephys` integration

## Current state (updated 2026-05-26)

`oe-remote` is now at `external/msw-open-ephys/` — flat `src/msw_open_ephys/` layout,
hatchling+hatch-vcs, `VERSION`, `.pre-commit-config.yaml`. Steps 1+2 below are done.

It provides a working CLI:
- `oe-remote status / preview / record / stop`
- `OEController` (direct HTTP to OE GUI port 37497)
- `Session` class: three recording modes — standalone / parent / child
- Entry point: `oe-remote = msw_open_ephys:run_cli`

`msw --parent openephys` is already wired in `hardware/parent_session.py` and
works today if `open-ephys-python-tools` is installed.  The base_text parsing
there does a manual `split("/")` — should be replaced with namespace builder
validation once the namespace is fully wired (see prerequisite below).

## Prerequisite: namespace wiring (done before touching oe-remote)

The namespace builder (`get_msw_builder()`) must be wired through all
path/file operations before the OE integration is tightened.  This covers:

- `generate_session_paths()` → `builder.build_path("session")` for basename,
  `builder.generate_path("session", include_optional_levels=False)` for standalone folder
- `parse_session_basename()` → `builder.extract_level_values("session")` + version loop
- `OpenEphysParentSession.attach()` → `extract_level_values` + `build_path` roundtrip

Status: tracked in ROADMAP.

---

## Design constraint: `base_text` uses forward slashes only — not OS path separators

`OEController.set_base_text()` sends a string to the Open Ephys GUI over HTTP.
Open Ephys interprets this string as a path fragment on the *recording machine*
(usually Linux), not on the machine running MSW (which may be Windows).

**The separator must always be `/` (forward slash).**

- `oe_remote` sets `base_text` to `"{subject}/{acquisition_name}/{oe_session_name}"`.
- `OpenEphysParentSession.attach()` in MSW splits the returned `base_text` on `"/"`.
- A backslash separator would make `split("/")` return the whole string as one token,
  silently setting `acquisition_name` to the full path instead of just the middle component.

**Consequence:** when extending or testing `parent_session.py`, never use `os.path.join()`
or `Path` to construct `base_text` — those use `\\` on Windows. Always build explicitly:
```python
base_text = f"{subject}/{acquisition_name}/{oe_session_name}"
```

**Namespace builder wiring note:** `extract_level_values("acquisition", base_text)` via
`NamespaceBuilder` will handle this correctly as long as the namespace spec uses `"/"` as
the separator token in the `acquisition`-level template. Verify this when wiring namespace
into `OpenEphysParentSession.attach()` (tracked in ROADMAP urgent fixes).

## Step 1 — Extract and restructure ✓ DONE 2026-05-26

`external/msw-open-ephys/` is now a flat src-layout package:
- `src/msw_open_ephys/` (renamed from `oe_remote`)
- `pyproject.toml` with hatchling+hatch-vcs, `name = "msw-open-ephys"`
- `.pre-commit-config.yaml`, `VERSION`, `.gitignore`, `README.md`
- All internal imports updated from `oe_remote.*` → `msw_open_ephys.*`

Still needs: `git init` + push to `MurineShiftWork/msw-open-ephys`; CI workflows; `.gitleaks.toml`; `CITATION.cff`.

## Step 2 — `msw oe` subcommand

Surface `oe-remote` commands through the `msw` CLI without shelling out.

```
msw oe status   [--ip HOST] [--port PORT]
msw oe preview  [--ip HOST]
msw oe record   --subject SUBJ --session-extension EXT
                [--acquisition-extension EXT] [--child @last|NAME]
                [--local-path PATH] [--remote-path PATH] [--ip HOST]
msw oe stop     [--ip HOST]
```

Implementation:

- Add `oe` subparser group in `cli/parser.py`
- Delegate directly to `oe_remote.cli.commands.cmd_*` functions (no subprocess)
- Default `--ip` / `--port` read from active setup config `open_ephys_url`
  (now in `SetupConfig`, falls back to machine config; already used by `--parent openephys`)
- `oe_remote` becomes an optional dependency:
  ```toml
  [project.optional-dependencies]
  oe = ["oe-remote"]
  ```
- Raise a clear `ImportError` message if not installed

## Step 3 — Fix `--parent openephys` base_text parsing

### What base_text looks like (set by `oe-remote record`)

```
# Standalone:  subject/session_name
# Parent:      subject/acquisition_name/session_name
# Child:       acquisition_name/session_name
```

Both `acquisition_name` and `session_name` follow the MSW session template:
`{subject}__{datetime}__{extension}` — the same regex as `namespace.msw.yaml`
session level, including the optional `(?:_\d{6})?` microsecond group.

### Current implementation (fragile)

```python
parts = [p for p in base.split("/") if p]
acquisition_name = parts[1]   # no validation
```

### Replacement — namespace builder roundtrip

```python
from murineshiftwork.namespace.paths import get_msw_builder

builder = get_msw_builder()
parts = [p for p in base.split("/") if p]
if len(parts) < 2:
    log.warning("base_text %r has <2 parts — oe_remote not yet called", base)
    return None

acq_segment = parts[1]  # acquisition_name (parent) or session_name (standalone)

try:
    values = builder.extract_level_values("session", acq_segment)
    acquisition_name = builder.build_path("session", values)  # validated + normalised
except ValueError:
    log.warning("base_text segment %r is not a valid MSW session name", acq_segment)
    return None

return ParentSessionInfo(
    acquisition_name=acquisition_name,
    subject=parts[0],
    ...
)
```

`build_path()` after `extract_level_values()` is a round-trip: same string
but validated against the spec and reconstructed from parsed fields.  If the
format ever changes in the spec, both sides update from the same YAML.

Also replaces the `open_ephys.control.OpenEphysHTTPServer` import with
`oe_remote.controller.OEController` + one new method:
```python
# Add to OEController:
def get_recording_info(self) -> dict:
    return self._get("/recording")
```

This removes the `open-ephys-python-tools` dependency entirely.

## What's needed for `--parent openephys` to work end-to-end

1. OE GUI running, HTTP server enabled (port 37497)
2. `oe-remote record --subject SUBJ --acquisition-extension EXT` called first
   to write `base_text` with the 3-part path
3. `msw run --parent openephys` (or `openephys:HOST`) called after
4. `oe-remote` (or `open-ephys-python-tools`) installed on the behavior machine

The `--parent openephys` path is already functional with `open-ephys-python-tools`.
Step 3 replaces that dependency with `oe_remote.controller` and adds namespace
validation to the base_text parser.

## Updated design (2026-06-09)

Terminology: `--parent` → `--host`, `ParentSessionProtocol` → `HostSessionProtocol`,
child session → linked session.  Full plugin design: `docs/concepts/plugin_system.md`.

The `make_parent_session()` factory (currently hardcoded) becomes entry-point driven:
`make_host_session()` iterates `msw.host` entry-points, loads the matching class,
checks `isinstance(session, HostSessionProtocol)`, and returns it.

`msw-plugin-api` (`external/msw-plugin-api/`) provides `HostSessionInfo`,
`HostSessionInfoProtocol`, and `HostSessionProtocol`.  Both `msw-open-ephys` and
`murineshiftwork` depend on it.

## Sequencing

| # | Task | Effort | Prerequisite | Status |
|---|---|---|---|---|
| 0 | Namespace wiring (paths.py, parent_session.py) | done first | — | ✓ done |
| 1 | Extract + restructure to flat `src/msw_open_ephys/` layout | ~1 h | — | ✓ done 2026-05-26 |
| 2 | CI workflows + pre-commit added to `msw-open-ephys` | — | — | ✓ done 2026-06-09 |
| 3 | `msw-plugin-api` package created with Protocols + HostSessionInfo | — | — | ✓ done 2026-06-09 |
| 4 | `git init` + push repos; OIDC | — | GitHub repos | ✓ done 2026-06-10 |
| 5 | Rename `parent_session.py` → `host_session.py`; `--parent` → `--host`; rename Protocol + factory | ~1 h | — | TODO |
| 6 | `make_host_session()` reads `msw.host` entry-points instead of hardcoded factory | 20 min | step 5 | TODO |
| 7 | Add `[project.entry-points."msw.host"] openephys = "msw_open_ephys.session:OpenEphysHostSession"` to msw-open-ephys | 5 min | step 6 | TODO |
| 8 | Add `register(subparsers)` to `msw_open_ephys/cli/__init__.py`; add `[project.entry-points."msw.cli"] oe = ...` | 30 min | — | TODO |
| 9 | Add `msw-plugin-api` dep to msw-open-ephys and murineshiftwork; `oe = ["msw-open-ephys"]` optional dep | 10 min | steps 6–8 | TODO |
| 10 | Session YAML: rename `parent_acquisition:` → `host_acquisition:`; update retrograde reader | 20 min | step 5 | TODO |
