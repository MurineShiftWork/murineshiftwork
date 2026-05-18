# Code Review Prompts

Collection of focused review prompts for systematic audits of this codebase.
Each section names what to look for, why it matters for this repo specifically,
and a ready-to-paste prompt. Run these manually, via `/ultrareview`, or wire
into CI as scheduled jobs.

---

## 1. General correctness and style

**Why:** Catches logic errors, ambiguous code, silent failures, and style
inconsistencies that accumulate across sessions. Good baseline for any PR.

```
Review the diff (or the named files) for:
- Logic errors, off-by-one, silent failure paths (bare except, swallowed errors)
- Mutable default arguments (def f(x=[])) and class-level mutable defaults
- Functions that do more than one thing; names that misrepresent what they do
- Dead code, unused imports, stale comments that contradict the current implementation
- Inconsistent naming conventions (snake_case vs camelCase, private vs public)
- Missing or misleading type annotations on public functions
- Docstrings that describe the wrong behaviour or are absent on non-obvious functions
Report each finding as: file:line — severity [low/med/high] — description.
```

---

## 2. Platform compatibility — Linux (Ubuntu 24+) and Windows 11

**Why:** The acquisition stack runs on Ubuntu 24 (RPi, Linux acquisition machines)
and Windows 11 (FLIR cameras, Bonsai). Serial ports, file paths, process APIs,
and default encodings differ across these platforms. Bugs surface only on the other OS.

- `/dev/serial/by-path/` resolution is Linux-only — any code that hard-codes `/dev/` without a Windows fallback will silently fail on Win11
- `subprocess.run` with `shell=True` behaves differently between bash and PowerShell/cmd
- `Path.expanduser()` and `~` resolution are cross-platform but `Path('~').home()` can differ
- Default file encoding (`open()` without `encoding=` argument) is OS-locale-dependent — can corrupt YAML/CSV on Windows if the locale isn't UTF-8
- `os.symlink` / `Path.resolve()` on symlinks behaves differently on NTFS (requires elevated rights)
- `time.sleep` precision differs; `threading.Event.wait` is more portable for timeouts
- `shutil.copy2` preserves metadata on both; `shutil.move` across filesystems can fail on Windows without a fallback

```
Audit the codebase for platform portability issues between Linux (Ubuntu 24+) and
Windows 11. Focus on:

1. Serial port paths: any use of /dev/, /dev/serial/by-path/, or COM port assumptions.
   Flag code that assumes Linux-style paths without a Windows branch or abstraction.

2. File encoding: every open() call that does not pass encoding='utf-8' explicitly.
   On Windows the default is the system locale (often cp1252), which corrupts UTF-8
   YAML and CSV files.

3. Subprocess invocation: shell=True usage, bash-specific syntax in command strings,
   .sh scripts launched without a platform guard, or assumptions about shell availability.

4. Path construction: string concatenation with '/' separators instead of pathlib.Path;
   hardcoded Unix paths (/tmp, /home, /dev) not guarded by sys.platform checks.

5. File permissions and symlinks: os.chmod, os.symlink, Path.resolve on symlinks —
   these require elevated rights on Windows.

6. Timing: bare time.sleep() for synchronisation with hardware events — Windows timer
   resolution is ~15 ms vs ~1 ms on Linux. Note anywhere this matters for state machine
   timing.

7. Process signals: signal.SIGTERM / signal.SIGKILL — not available on Windows;
   flag any task teardown code that uses them.

For each finding: file:line — platform affected — severity — recommended fix.
```

---

## 3. Hardware interface safety

**Why:** Serial port errors and Bpod disconnects mid-trial can corrupt session data
or leave the animal in a bad state (valve stuck open, reward not delivered). The
hardware layer must handle errors without crashing the session or the Python process.

- `BpodFactory` holds a global `_write_lock` — check it's acquired everywhere serial writes happen
- `exit_safely()` / `close_safely()` — verify all exception paths call this; Bpod open-on-exit is catastrophic
- `SimBpod` — verify all action driver code paths are reachable by simulation (no live-hardware-only branches)
- Stage `StageController.disconnect()` — must be called even on exception; check try/finally coverage
- `run_task` in tasks spawns a daemon thread — verify `continue_task = False` is reachable from all exit paths

```
Audit the hardware interface layer (hardware/bpod/, logic/task_process.py,
logic/hooks.py) for safety and error-isolation:

1. Serial write lock: every call that writes to the Bpod serial port must hold
   BpodFactory._write_lock. List any write path that does not acquire it.

2. Cleanup guarantees: trace all exception paths through TaskProcess.__init__,
   __exit__, exit_safely(), and connect_bpod(). Is Bpod.close_safely() guaranteed
   to be called even if init_task() or a pre-hook raises?

3. Thread teardown: task threads set self.continue_task = False on stop_task().
   Are there blocking calls inside task run loops (time.sleep, bpod.run_state_machine)
   that would delay or prevent this flag from being checked?

4. Hook error isolation: a fatal pre-hook must not leave Bpod open. Verify the
   try/except structure in TaskProcess.__init__ around run_pre_hooks.

5. SimBpod coverage: for each method in BpodActionDriver and BpodFactory, does
   SimBpod have a matching implementation that allows tests to reach the same branches
   as real hardware?

Report: file:line — issue — consequence — fix.
```

---

## 4. Session data integrity

**Why:** The session YAML and CSV are the primary scientific outputs. Silent data
loss or silent corruption is worse than a crash, because it is not noticed until analysis.

- `TaskProcess.persist_settings()` runs before Bpod connects — verify it always produces a valid YAML even if the session fails mid-init
- `update_session_yaml()` is called from task_objects — verify it handles concurrent calls safely (two sections written in sequence; no partial write)
- CSV writeback: `save_subject_task_overrides` writes to subject YAML after session — verify it is safe to call even if the session errored (task_objects `save_session_end`)
- Backup creation in `post clean` — verify the `.bak.*` file is written before the original is overwritten

```
Audit the session data pipeline for integrity and loss-of-data risks:

1. Session YAML: is TaskProcess.persist_settings() called before any code that can
   raise? Is the file written atomically (write to tmp then rename) or could a crash
   produce a partial YAML?

2. update_session_yaml(): is it safe to call from multiple points in the session
   lifecycle? Could a second call corrupt a section written by the first?

3. Subject writeback (save_subject_task_overrides): what happens if this is called
   while another process has the subject YAML open? Is there any locking? Flag if not.

4. msw post clean backup: is shutil.copy2 to .bak.* guaranteed to complete before
   f.write_text() overwrites the original? What happens on a write error mid-clean?

5. CSV rows: read_pybpod_csv — does it handle encoding errors, truncated files, or
   binary artefacts in Bpod output without silently dropping rows?

6. Reader version dispatch: in readers/session.py, are all file-type branches covered
   by tests with fixture files? Which dispatch paths have no fixture coverage?

Report: file:line — scenario — data at risk — recommended fix.
```

---

## 5. Configuration system correctness

**Why:** The 5-level priority chain (bundled → overlay → mode → subject → CLI) has
complex merge semantics. A bug here silently runs animals at wrong parameters.

- `deep_merge` must not mutate inputs — already tested, but check for new callers
- `read_task_modes` must not merge mode sections into defaults — test coverage for boundary
- Subject YAML writeback (`task_mode`, `start_level`) must not overwrite other task keys
- `validate_config_file_path` returns `""` for missing files — callers must handle this

```
Audit the configuration system (logic/config/, cli/evaluate.py) for correctness
of the 5-level priority chain and YAML I/O:

1. deep_merge: identify every call site. Does any caller pass the same dict as both
   base and override (aliasing bug)? Does any caller mutate the result and expect the
   original to be unchanged?

2. Priority chain in _build_task_settings_patch: trace through a concrete example
   where all 5 levels have a conflicting value for the same key. Verify the correct
   level wins at each step.

3. Mode writeback isolation: when evaluate_args writes {"task_mode": X} to subject
   YAML, does save_subject_task_overrides touch any key in task_overrides[task] other
   than "task_mode"? Verify with the merge logic in io.py.

4. Overlay task.yaml: if the overlay defines a key in default: that the bundled
   task.yaml does not have, does it appear in settings.task.patched? If the overlay
   defines a mode: that the bundled does not have, is it available to --task-mode?

5. validate_config_file_path returning "": list every call site and verify the caller
   guards against an empty string before opening the file.

6. load_setup_config / load_subject_config: what is returned when the YAML contains
   an unknown field (Pydantic extra="ignore" vs error)? What if a required field is
   missing?

Report: file:line — scenario — actual vs expected behaviour.
```

---

## 6. Test coverage gaps

**Why:** This repo controls live hardware and writes scientific data. Tests that only
cover the happy path give false confidence; hardware and file-IO edge cases are where
bugs live.

```
Analyse the test suite (tests/) against the source (src/murineshiftwork/) and identify:

1. Modules or classes with zero test coverage. List them with a one-line description
   of what they do and why they should be tested.

2. Functions that are tested only on the happy path. Identify the untested error /
   edge-case branches (e.g. file not found, Bpod disconnect, empty input, boundary
   values for numeric parameters).

3. The hook system: are fatal pre-hook and fatal post-hook paths tested through
   TaskProcess (not just through run_pre/post_hooks directly)?

4. Sequence level writeback: is there a test that verifies save_session_end() actually
   writes start_level to the subject YAML? (Current coverage is unit-level only.)

5. Reader dispatch: which file-type branches in read_session_data have no fixture
   file coverage (e.g. legacy task_settings.py path, v1 JSON path)?

6. CLI entry points (parser.py): are all subcommands reachable by at least one test
   without requiring hardware?

Produce a prioritised list: High (data loss / silent wrong behaviour) / Med / Low.
```

---

## 7. Dependency hygiene

**Why:** Dependencies pulled in transitively, or not pinned to compatible ranges,
break installs across Python versions or OS. `pybpod-api` in particular is a
non-standard dependency with its own compile requirements.

- `pybpod-api` ships Cython extensions — verify it builds on Python 3.11 / 3.12 and has no Windows build steps that fail silently
- `safe-and-collaborative-architecture` (SACA) — unusual package name; verify it is the intended dependency and not a namespace squatter
- `sounddevice` — wraps PortAudio C library; on Ubuntu 24 this requires `libportaudio2` system package; on Win11 it bundles its own. Document in installation.md.
- `opencv-python-headless` vs `opencv-python` — headless is correct for acquisition machines with no display, but fails if Qt GUI features are used

```
Audit pyproject.toml and all import statements for dependency issues:

1. Missing bounds: which dependencies have no upper bound that could break on a
   future release? (Especially pydantic v2, numpy, scipy — all have breaking changes
   between majors.)

2. Platform-specific dependencies: are there any imports guarded by sys.platform
   that are not listed as optional in pyproject.toml? (e.g. a Windows-only serial
   library imported unconditionally.)

3. Transitive risk: pybpod-api, safe-and-collaborative-architecture — what do they
   pull in transitively? Any packages with known CVEs, deprecated, or abandoned?

4. Optional extras: the qt and rce extras are documented. Are all imports of PyQt6,
   pyqtgraph, rpi_camera_ensemble guarded by try/ImportError so a missing extra
   gives a clear error rather than an ImportError at module level?

5. Dev dependencies: commitizen, mkdocs, black, flake8 are in dev extras. Are any
   of these imported in src/ (would be a packaging bug)?

6. Python version matrix: the package requires >=3.10. Are there any 3.10-incompatible
   constructs (e.g. match statements require 3.10; X | Y union syntax in annotations
   requires 3.10; tomllib requires 3.11)?

Report: dependency — issue — recommended pin or guard.
```

---

## 8. Security and secrets

**Why:** Config files (setup YAML, subject YAML) are git-tracked in a shared repo.
Serial port paths and host IPs appear in session logs. Hooks load arbitrary Python
classes by dotted path — that's a code execution vector if YAML is untrusted.

- `load_hooks` calls `importlib.import_module` on a string from the YAML — if the YAML is writable by a non-owner, this is arbitrary code execution
- `ast.literal_eval` in `_parse_key_value_list` — safe, but verify no `eval()` calls exist elsewhere
- Session YAMLs written to shared data directories — verify file permissions are set correctly by TaskProcess
- Machine config (`~/.murineshiftwork/msw_machine.yaml`) — verify it does not log passwords or API keys

```
Audit the codebase for security concerns relevant to a shared-lab environment:

1. Arbitrary code execution: load_hooks() calls importlib.import_module() on strings
   from YAML files. Who can write the setup YAML? Is it git-tracked and reviewed?
   Is there any validation that the dotted path resolves to a TaskHook subclass before
   instantiating it?

2. eval() / exec(): search for any use of eval() or exec() in src/. Report each
   occurrence with context.

3. Subprocess injection: any subprocess.run() or os.system() call that interpolates
   user-supplied strings without shell=False and a list argument. Specifically check
   cli/post.py run_post_run and any script-path construction.

4. File permission leakage: session files written to shared mounts — does TaskProcess
   or any writer set explicit permissions (os.chmod), or does it rely on umask?

5. Secrets in logs: logging.debug/info calls that include serial port paths, IP
   addresses, subject names — flag any that could expose PII or infrastructure details
   in shared log files.

6. YAML load safety: every yaml.load() call must use yaml.safe_load(). Flag any
   yaml.full_load() or yaml.load(stream) without Loader=yaml.SafeLoader.

Report: file:line — risk — exploitability in a shared lab context — fix.
```

---

## 9. This-repo-specific: task protocol correctness

**Why:** Task protocols (state machines, trial loops, reward delivery) are the
scientific core. A silent bug here produces wrong behaviour in animal subjects.

- `VALVE_OPENING_TIME_MS` vs `VALVE_OPENING_TIME_S` — units mismatch between tasks; at least one task converts internally
- Reward volume → valve time conversion: `valve_s_for_ul` uses exponential fit; verify it is called with the correct valve ID
- `continue_task` flag checked only at trial boundaries — a very long trial timer would delay stop
- Named modes in task.yaml — if a mode key is misspelled the config system silently uses default values

```
Review the task protocol implementations (tasks/) for behavioural correctness:

1. Units consistency: list every task parameter that carries a physical unit
   (ms vs s, µL vs mL, dB vs amplitude). Flag any parameter that is handled
   with inconsistent units between the task.yaml default, the task_objects.py
   reader, and the state machine output action.

2. Valve calibration lookup: for each call to valve_s_for_ul or valve_ul_for_s,
   verify the valve_id used matches the physical valve the task is targeting.

3. State machine exit conditions: for each state that has only a Tup transition
   (timer-only exit), flag if the timer value comes from a task setting that
   could be zero or negative (which would crash the state machine).

4. continue_task check cadence: in each task's run() loop, what is the maximum
   latency before a stop_task() signal would be honoured? Flag any loop body
   that blocks for more than ~2 seconds without checking continue_task.

5. Named mode coverage: for tasks with mode: sections in task.yaml, are all
   expected keys present in each mode? A missing key silently falls through to
   the bundled default, not to an error.

6. Subject writeback in tasks: sequence/task_objects writes start_level to subject
   YAML. Are there other tasks that maintain per-subject state that should also
   write back? (e.g. probabilistic_switching_fixedsubjects stage position.)

Report: task — file:line — issue — consequence.
```

---

## 10. Documentation completeness

**Why:** Skeleton pages were created but not filled in. Docs that describe the wrong
API version or omit key flags cause lab members to use the software incorrectly.

```
Audit the documentation (docs/) for completeness and accuracy:

1. Skeleton pages: docs/concepts/, docs/tutorials/, docs/cli/ contain placeholder
   content marked "Skeleton — fill in." List each file with the specific gaps:
   missing command flags, missing examples, missing cross-references.

2. Accuracy: for each CLI page in docs/cli/, compare the documented flags against
   the argparse definitions in cli/parser.py. Flag any missing, renamed, or
   incorrectly described flags.

3. Hook system docs (docs/concepts/hook_system.md): does it document the fatal=True
   flag, the SessionAbortError type, and the post-hook "all hooks run before raise"
   semantics? Is the HookContext field table complete?

4. Config system docs (docs/concepts/config_system.md): does the priority chain
   table match the implementation in cli/evaluate.py _build_task_settings_patch?
   Are all 5 levels present?

5. Getting started quickstart: can a new lab member follow it from scratch to a
   first simulated session? Test the command sequence in a clean environment.

6. ROADMAP.md: are all completed items marked DONE with a date? Are all pending
   items still accurate (not already implemented)?

Report each gap as: file — section — what is missing or wrong.
```

---

## Usage notes

- Run any prompt against the full repo by prefixing with: *"Working directory:
  murineshiftwork. "* and appending the relevant file list or `--all-files`.
- For CI: wire the platform compat, security, and dependency prompts as monthly
  scheduled jobs (they rarely produce urgent findings but rot silently).
- For every PR: run the general correctness prompt (#1) on the diff, and the
  task protocol prompt (#9) on any PR touching `tasks/`.
- `/ultrareview` on a branch runs a cloud multi-agent review; use prompts #1–#4
  as the base instructions.
