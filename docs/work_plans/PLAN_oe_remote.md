# Plan: oe-remote extraction, `msw oe` command, `--parent openephys` integration

## Current state

`oe-remote` lives as a plain subdirectory in `external/msw_open_ephys/oe_remote/`.
It is tracked by the `msw_open_ephys` git repo (no `.git` of its own).

It provides a working CLI:
- `oe-remote status / preview / record / stop`
- Own `OEController` (direct HTTP to OE GUI port 37497)
- `Session` class: three recording modes — standalone / parent / child
- Entry point via `setup.cfg` (old setuptools — needs migration)

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

## Step 1 — Extract oe_remote as standalone repo

`oe_remote/` is a plain subdirectory of `msw_open_ephys` (not a sub-repo).
Extraction is straightforward:

```bash
cp -r external/msw_open_ephys/oe_remote /tmp/oe-remote
cd /tmp/oe-remote
git init && git add . && git commit -m "feat: initial extraction from msw_open_ephys"
git remote add origin https://github.com/MurineShiftWork/oe-remote
git push -u origin main
```

Then inside the extracted repo:

1. Migrate `setup.cfg` → `pyproject.toml` (hatchling + hatch-vcs,
   `name = "oe-remote"`, `requires-python = ">=3.10"`)
2. Remove `setup.py`; keep `setup.cfg` only for `[flake8]` if needed (then drop)
3. Apply copier template: `.pre-commit-config.yaml`, CI workflows,
   `.gitleaks.toml`, `CITATION.cff`, `mkdocs.yml`
4. Fix all URLs (currently point to `larsrollik/murineshiftwork`)
5. Dependencies: `requests`, `rich`

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
- Default `--ip` / `--port` read from `msw_machine.yaml` key `open_ephys_url`
  (already used by `--parent openephys`)
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

## Sequencing

| # | Task | Effort | Prerequisite |
|---|---|---|---|
| 0 | Namespace wiring (paths.py, parent_session.py) | done first | — |
| 1 | `git init` + extract + push `MurineShiftWork/oe-remote` | ~30 min | GitHub repo exists |
| 2 | `setup.cfg` → `pyproject.toml`, copier template | ~1 h | step 1 |
| 3 | Add `get_recording_info()` to `OEController` | 5 min | step 1 |
| 4 | Replace `open_ephys.control` with `oe_remote.controller` in `parent_session.py` | 10 min | step 3 |
| 5 | Add `msw oe` subparser + wire to `oe_remote.cli.commands` | ~1 h | step 2 |
| 6 | `oe = ["oe-remote"]` optional dep + docs | 15 min | step 5 |
