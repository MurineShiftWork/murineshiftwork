# CLI Refactor Plan

_Scope: improve option grouping, naming, and code structure. No changes to the core session
interface (`-s/-t/--setup/--task-mode/-o`). No behaviour changes to evaluate pipeline._

---

## 1. Decisions resolved

| Topic | Decision |
|---|---|
| `--serial-port-scale` → `--port-scale` | **Keep, visible in `run` help.** All tasks: including calibration tasks: go through `msw run`. Hiding it from `run` help means users have no way to discover it when running `_calibration_liquid_dynamic`. Keep it in the Hardware group with a note `(calibration tasks only)`. |
| Calibration file args (`-cwater/-csound/-cstage`) | **Remove.** Calibration data is now embedded in setup YAML files. No CLI override needed. |
| Metadata: experimenter | **Formalise as `--experimenter`.** First-class field, not a key-value pair. Stored in session YAML. |
| Metadata: experiment/project | **Remove `--experiment`.** Experiment/project dimension is managed at subject registration, outside acquisition scope. |
| Metadata: free-form key-value | **Keep `--meta KEY=VALUE`.** No category prefix; just `--meta`. |
| Log file default | **Switch to rotating logs in `~/.murineshiftwork/logs/`**, `RotatingFileHandler`, same pattern as RCE. `--log-file` stays as an optional path override. |
| Version in preamble | **Print `msw vX.Y.Z` + copyright line at every `run` invocation**, before the first task output. Not in help text. |
| CLI entry point | **Add `msw` as a second entry point alias** alongside `murineshiftwork`. Change `prog="msw"`. |

---

## 2. Problems fixed

### 2.1 `--task-mode` / `-ts` float to top of help

Added with bare `parser.add_argument()` (no group) inside `add_args_for_task_settings_override`.
Argparse puts ungrouped options in the implicit `options:` bucket, which renders before all named
groups. Fix: attach them to a named `"Task settings"` group.

### 2.2 `add_args_for_general_use` monolith

One function creates three groups (General, Metadata, Config files) and attaches them to any parser
that calls it. `register` inherits metadata and config-file args it does not use. Fix: break into
focused helper functions, each creating exactly one group.

### 2.3 `register` over-loaded

Gets ~15 args it does not consume. Fix: slim to only what it actually reads (`-s`, `-t`, `-o`,
`-cd`, `-n`, `-m`). Mark as legacy in top-level help once `subject remove/rename` exists.

### 2.4 `subject` and `setup` have no groups, missing help text

All options under generic `options:`. `--force`, `--project`, `--experiment`, `--comment` have no
descriptions. Fix: add named groups and help strings.

### 2.5 Dead options removed

- `-cs / --config-file-subjects`: legacy INI, never read. Remove.
- `--experiment`: project/experiment dimension is out of scope for acquisition CLI. Remove.
- Calibration file args: integrated into setup YAML. Remove all three.

### 2.6 `"Development options."` typo

Trailing period. Fix: `"Development"`.

### 2.7 Top-level description

Mentions "RPi Camera Colony and stimulation with PulsePal": implementation details, not purpose.
Fix: see §4.

---

## 3. Arg rename table

Pattern: `--{maincategory}-{specificparam}`. Core session args unchanged.

| Current short | Current long | Proposed long | Short kept | Notes |
|---|---|---|---|---|
| `-b` | `--serial-port-bpod` | `--port-bpod` | `-b` | drop "serial" prefix |
| `-p` | `--serial-port-pulsepal` | `--port-pulsepal` | `-p` | |
| `-stage` | `--serial-port-stage` | `--port-stage` |: | fix single-dash prefix |
| `-scale` | `--serial-port-scale` | `--port-scale` |: | move to calibration-hardware group; not in standard `run` help |
| `-cwater` | `--calibration-file-water` | _remove_ |: | in setup YAML |
| `-csound` | `--calibration-file-sound` | _remove_ |: | in setup YAML |
| `-cstage` | `--calibration-file-stage` | _remove_ |: | in setup YAML |
| `-cd` | `--config-dir` | `--config-dir` | `-cd` | already correct |
| `-ct` | `--config-file-task` | `--config-task` |: | drop "file" |
| `-cc` | `--config-file-camera` | `--config-camera` |: | drop "file" |
| `-cs` | `--config-file-subjects` | _remove_ |: | dead legacy option |
| `--researcher` | | `--experimenter` |: | formalised; rename to standard term |
| `--experiment` | | _remove_ |: | out of scope |
| `-meta` | `--metadata` | `--meta` | `-m` | drop redundant suffix; short `-m` |
| `-child-to` | `--is-child-session-to` | `--session-child-of` |: | reads as a statement |
| `-lf` | `--log-file` | `--log-file` | `-lf` | unchanged; now an override over rotating default |

---

## 4. Description string and preamble

### `description=` (shown in every `-h`)

```
Murine Shift Work: behavioural task acquisition with hardware support.
```

### `epilog=` on main parser (shown only on `msw -h`)

```
Source: https://github.com/larsrollik/murineshiftwork
```

### `--version` output

```
msw 1.1.0  |  © Lars B. Rollik  |  PolyForm Internal Use 1.0.0
```

### Run invocation banner (printed at the start of every `msw run`)

Printed once to stdout before any task output. Not in argparse at all: called inside `run_cli`
or `run_task` when `command == "run"`:

```python
def _print_run_banner():
    from murineshiftwork import __version__
    print(f"msw {__version__}  |  © Lars B. Rollik  |  PolyForm Internal Use 1.0.0")
```

This ensures every acquisition log and terminal session captures the exact software version and
license notice. No other subcommands print this (init/setup/subject are admin ops, not
acquisition).

---

## 5. Logging: rotating file handler

### Current behaviour

`get_default_log_file_path()` writes a timestamped file to `/tmp/`. Each invocation creates a new
file. `/tmp/` is cleared on reboot. `setup_logging` uses a plain `FileHandler`.

### Target behaviour

**Home log directory:** `~/.murineshiftwork/logs/`. One file per `msw` invocation (timestamp in
name). `RotatingFileHandler` caps total disk use and auto-purges oldest files. Same pattern as the
RCE agent (`rce--{prefix}--{timestamp}.log`).

```python
LOG_DIR = Path("~/.murineshiftwork/logs").expanduser()
LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per file
LOG_BACKUP_COUNT = 100             # keep last 100 invocation files
```

Filename: `msw--{timestamp}.log`.

**Session log (for `run` only):** Also write the log to the session folder alongside the data
files as `{session_basename}.msw.log`. Added as a second `FileHandler` once session paths are
known (i.e. inside `TaskProcess.__init__` after `persist_settings()`). This is data provenance,
not noise: it captures the exact hardware connection sequence, trial-by-trial state, and any
warnings for that specific acquisition.

```python
# Inside TaskProcess.__init__, after persist_settings():
session_log = Path(self.session_paths["session_file_path"] + ".msw.log")
session_handler = logging.FileHandler(session_log)
session_handler.setFormatter(...)
logging.getLogger().addHandler(session_handler)
```

`get_default_log_file_path` is removed from `defaults.py` (no longer needed to pre-compute the
path before logging is set up). The `--log-file` arg default changes from a computed path to `""`
(empty string = use rotating default). If `--log-file PATH` is given, the home log writes to that
path instead; the session log is unaffected either way.

### Open question

Format for session log: same plain-text `%(message)s` formatter as current, or JSON lines (like
RCE) so the session log is machine-readable for post-hoc analysis? RCE uses JSON because logs are
parsed programmatically. MSW session logs are currently only read by humans for debugging. Plain
text is sufficient for now; can switch to JSON later.

---

## 6. Target help layout

### `msw run`

```
Session:
  -s / --subject
  -t / --task
  --setup
  -o / --out-path
  --experimenter

Task settings:
  --task-mode
  -ts / --task-settings

Hardware:
  -b / --port-bpod
  -p / --port-pulsepal
  --port-stage

Advanced:
  -cd / --config-dir
  --config-task
  --config-camera
  --session-child-of

Metadata (free-form):
  -m / --meta  KEY=VALUE [KEY=VALUE ...]

Development:
  -l / --log-level
  -lf / --log-file
  -d / --debug
```

Note: `--port-scale` IS in `run` help (Hardware group, annotated "calibration tasks only").
All tasks go through `msw run`; hiding it would make it undiscoverable when running
`_calibration_liquid_dynamic`.

### `msw subject`

```
positional: {add, list, remove, rename}

Subject:
  -s / --subject

Subject details:   (add / rename)
  --project
  --comment

Options:
  -cd / --config-dir
  -f / --filter      (list only)
  --force

Development:
  -l / --log-level
  -d / --debug
```

### `msw setup`

```
positional: {create, list}
positional: setup_name (optional, required for create)

Options:
  -cd / --config-dir
  -f / --filter
  --force

Development:
  -l / --log-level
  -d / --debug
```

### `msw register` (legacy)

Slimmed to: `-s`, `-t`, `-o` (relabelled "Data root"), `-cd`, `-n`, `-m`.
Appears last in top-level subcommand list. Marked `(legacy: use 'subject' instead)` in help
string once `subject remove/rename` exist.

### `msw calibration`, `msw action`, `msw init`

Minor: consistent group names, add `Development` group to `calibration`.

---

## 7. Code structure changes in `parser.py`

Replace three monolithic helpers with eight focused ones. Each creates exactly one named group.

```python
_add_session_args(parser)           → "Session":       -s -t --setup -o --experimenter
_add_task_override_args(parser)     → "Task settings": --task-mode -ts
_add_hardware_args(parser)          → "Hardware":      -b -p --port-stage
_add_scale_arg(parser)              → "Calibration hardware": --port-scale  (not called from run)
_add_advanced_args(parser)          → "Advanced":      -cd --config-task --config-camera --session-child-of
_add_meta_args(parser)              → "Metadata":      -m/--meta
_add_dev_args(parser)               → "Development":   -l -lf -d
```

Old `add_args_for_general_use`, `add_args_for_hardware_and_calibration`, and
`add_args_for_task_settings_override` are deleted (no external callers).

---

## 8. Impact on `evaluate.py`

Key names in `args_dict` that change:

| Old key | New key | Action in evaluate |
|---|---|---|
| `serial_port_bpod` | `port_bpod` | rename read sites |
| `serial_port_pulsepal` | `port_pulsepal` | rename read sites |
| `serial_port_stage` | `port_stage` | rename read sites |
| `serial_port_scale` | `port_scale` | rename read sites |
| `researcher` | `experimenter` | rename read sites |
| `config_file_task` | `config_task` | rename read sites |
| `config_file_camera` | `config_camera` | rename read sites |
| `config_file_subjects` | _(removed)_ | delete read site, hardcode `""` |
| `experiment` | _(removed)_ | delete from `_evaluate_metadata` |
| `calibration_file_water` | _(removed)_ | delete from `_evaluate_and_load_configs` |
| `calibration_file_sound` | _(removed)_ | delete from `_evaluate_and_load_configs` |
| `calibration_file_stage` | _(removed)_ | delete; stage calib comes from setup YAML |
| `is_child_session_to` | `session_child_of` | rename read sites |

Also check `task_process.py`, `preflight.py`, `execute.py`, and task `task_objects.py` files for
any direct reads of the old key names.

---

## 9. `setup.cfg` changes

```ini
[options.entry_points]
console_scripts =
    murineshiftwork = murineshiftwork.cli:run_cli
    msw = murineshiftwork.cli:run_cli
```

---

## 10. Implementation order

| Step | Files | Notes |
|---|---|---|
| 1 | `setup.cfg` | Add `msw` entry point |
| 2 | `parser.py` | Change `prog="msw"`, update description/epilog |
| 3 | `logic/log.py` | Rotating file handler; update `setup_logging`; remove `get_default_log_file_path` |
| 4 | `defaults.py` | Remove `get_default_log_file_path` import; move `CALIBRATION_FILE_PATH` in (if still needed); add `--log-file` default `""` |
| 5 | `parser.py` | Replace three monolithic helpers with focused `_add_*` functions; fix group names; reorder subcommands |
| 6 | `parser.py` | Add `--experimenter`; remove dead args; rename port/config args |
| 7 | `evaluate.py` | Update all read sites for renamed keys; remove deleted fields |
| 8 | `execute.py`, `preflight.py`, `task_process.py`, tasks | Update remaining key reads |
| 9 | `cli/__init__.py` | Add `_print_run_banner()` call for `command == "run"` |
| 10 | `subject` add `remove`/`rename`; mark `register` legacy | `parser.py`, `execute.py` |

Steps 1-9 are one PR. Step 10 is a follow-on.

---

## 11. Tests

Existing: `tests/test_preflight_and_pipeline.py`, `tests/test_cli_evaluate.py`: run after every
step; key renames will break them and must be updated in the same commit.

New `tests/test_cli_help.py`:
- `test_run_help_contains_session_group`
- `test_run_help_task_settings_before_hardware`: check group ordering
- `test_run_help_no_calibration_file_args`: `-cwater/-csound/-cstage` absent
- `test_run_help_no_config_file_subjects`: `-cs` absent
- `test_run_help_port_scale_present_with_note`: `--port-scale` present; help text says "calibration"
- `test_subject_help_contains_details_group`
- `test_register_appears_last_in_top_level_help`
- `test_version_string_contains_version_number`
- `test_run_banner_contains_version`: call `_print_run_banner()`, capture stdout

---

## 12. Epilog spacing

All subparser epilog strings should end with a trailing blank line so there is a visible gap
between the last epilog line and the shell prompt:

```python
epilog = dedent(f"""Examples:
    ...

Available tasks:
{available_tasks}

""")   # ← trailing newline creates the gap
```

---

## 13. Decisions resolved (round 2)

| Topic | Decision |
|---|---|
| Log level: session folder | INFO: sufficient for per-session debugging |
| Log level: central rotating | DEBUG: full detail, keep last 100 invocations |
| Log file naming | Central: `msw-{datetime}.log`. Session: `msw-{datetime}-{session_basename}.log` |
| Log file format | **Plain text** for now. JSON lines deferred until log parsing is needed programmatically. |
| `--experimenter` CLI position | Below `--meta` in help. Named `--meta-experimenter`. Internally joins the `--meta` KEY=VALUE basket in the evaluate pipeline: not a separate field. |
| `--experimenter` session storage | Lands in the session YAML `metadata:` dict alongside any other `--meta` pairs. Not in `process:`. |
| `--meta` storage | Session YAML top-level `metadata:` dict. All `--meta KEY=VALUE` pairs merged in, including `experimenter` if given. |
| `subject` subcommand verbs | `add`, `rename`, `remove`, `list` (rename before remove; fix plan item 5). |
| `register` subcommand | Keep slimmed for backward compat; mark legacy in help. Retire fully only after `subject` has all four verbs. |
| Log handler cleanup | Session `FileHandler` stored as `self._session_log_handler`; removed and closed in `exit_safely()` to avoid leaking into controller multi-session scenarios. |

## 14. Open questions (resolve before implementation)

1. **Python scripted import wiring**: when MSW is used via `from murineshiftwork.logic.task_process import TaskProcess` (no CLI), `--meta-experimenter` and `--meta KEY=VALUE` are not parsed. The equivalent is passing `metadata={"experimenter": "...", "key": "val"}` as a kwarg to `TaskProcess`. Confirm this is the right API surface, or should `TaskProcess` accept `experimenter=` directly?

2. **100 vs 50 log files**: central rotating log should keep last 100 invocations (updated from 50). Confirm `LOG_BACKUP_COUNT = 100`.

---

## 14. Completed (2026-05-17)

All CLI refactor steps implemented:

- `setup.cfg`: added `msw` entry point alongside `murineshiftwork`
- `parser.py`: full rewrite: `prog="msw"`, new description, 6 focused `_add_*` helpers,
  renamed flags (`--port-bpod`, `--port-pulsepal`, `--port-scale`, `--port-stage`), all `dest=`
  unchanged so downstream code needs no key renames; removed dead args
  (`-cs`, `--researcher`, `--experiment`, `-cwater`, `-csound`, `-cstage`);
  added `--meta-experimenter`; subcommand order: init/setup/subject/run/calibration/action/register;
  `register` marked legacy; `subject` has all four verbs (add/list/rename/remove)
- `logic/log.py`: per-run timestamped files in `~/.murineshiftwork/logs/`, pruned to 100 files;
  added `add_session_log_handler()` (INFO level)
- `logic/task_process.py`: importlib.metadata for version; session log handler wired in
- `logic/misc.py`: namespace-package fallback uses `__path__` not `__file__`
- `cli/__init__.py`: `_print_run_banner()` for `run`; action/register added to bypass list
- `cli/evaluate.py`: `_evaluate_metadata` now uses experimenter key (not researcher/experiment);
  `_evaluate_and_load_configs` uses `.get()` with defaults for all removed CLI keys
- `cli/execute.py`: `run_subject` handles rename and remove
- `cli/defaults.py`: calibration file path defaults added
- `src/murineshiftwork/__init__.py`: **deleted**: murineshiftwork is now a proper namespace package
- `tests/test_namespace_readiness.py`: both tests pass (no xfail); uses `__path__` not `__file__`
- `.github/workflows/install_and_test.yaml`: namespace checks updated; both must pass

Test result: 195 passed, 0 xfailed, 3 warnings.

---

## 15. Next action items (MSW general work plan)

_In rough priority order._

**Immediate:**
1. Hook system: implement `logic/hooks.py`, wire into `TaskProcess`, add
   `sequence/hooks.py::FetchSubjectLevel`. Plan in `FLIR_AND_HOOKS_PLAN.md`.
2. FLIR `BonsaiRunner`: subprocess launcher for Bonsai workflows (both flycap+spinnaker,
   up to 3 cameras with input index). Plan in `FLIR_AND_HOOKS_PLAN.md`.

**Short term:**
3. `logic/misc.py` cleanup: move `test_serial_port_is_accessible` to hardware/preflight module;
   move `list_available_tasks`/`find_task_by_name` into CLI; move `draw_jittered_trial_time` into
   task-supplementary module.
4. Simulation mode: `SimBpod`, `SimPulsePal`, `SimStageController`; `--simulate` flag.
5. Hardware action API Phase 2: `ControllerSession` owns hardware for full session.

**Suite migration (longer horizon):**
6. Suite namespace split: `msw-logic`, `msw-tasks-*`, `msw-agent` sub-packages per
   suite design docs at `/mnt/maindata/code/murineshiftwork_suite/design/`.
