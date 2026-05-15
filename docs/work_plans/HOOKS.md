# Task Hook System

## Rationale

Tasks need per-subject state (current training level, history) fetched before they start and
pushed after they end. That logic must not live inside the task protocol or `TaskProcess` — those
layers should not know about external databases, notification systems, or lab-specific state
management.

The hook system provides two ordered call-points around every task run:

```
evaluate_args()
    ↓
TaskProcess.__init__()
  build session paths
  connect Bpod
  ── run_pre_hooks(ctx) ──────────────────── hooks can mutate task_settings here
  init_task()        ← TaskRunner.__init__ reads the (possibly patched) settings
  ↓
with-block: tp.run_task() … tp.is_running() …
  ↓
TaskProcess.__exit__()
  ── run_post_hooks(ctx) ─────────────────── hooks read session output, push state
  exit_safely()
```

Pre-hooks mutate `HookContext.task_settings`; `TaskProcess` patches those back into
`input_kwargs["settings.task.patched"]` before calling `init_task()`. The task reads
`task_settings["start_level"]` as always — it never knows whether the value came from a
file, a hook, or the CLI.

---

## Core objects

### `HookContext`

Passed to every hook. Hooks may read all fields and write to `task_settings` and `output`.

```python
@dataclass
class HookContext:
    subject: str
    task_name: str
    task_settings: dict          # write here to patch settings before task init
    session_paths: dict
    execution_config: Optional[ExecutionConfig] = None
    output: dict = field(default_factory=dict)  # for post-hooks: task wrote final state here
```

`output` is populated by `TaskProcess.__exit__` from the task's persisted end-of-session
state before post-hooks run (e.g. `output["final_level"]` from the level JSON file).

### `TaskHook` base class

```python
class TaskHook:
    """Override either or both methods. No-op default implementation."""

    def pre_run(self, ctx: HookContext) -> None:
        pass

    def post_run(self, ctx: HookContext) -> None:
        pass
```

Implement only what you need. Both methods receive the same `ctx` object, so pre-hooks can
stash state in `ctx.output` for post-hooks to read.

---

## Hook registration

Hooks are referenced by **dotted import path** (`"package.module.ClassName"`).
They are discovered at `TaskProcess.__init__` time, resolved in the order listed, and
executed in that order (pre: top-to-bottom; post: top-to-bottom).

### Global hooks — run on every task

Declared in `SetupConfig` YAML (`configs/setups/<name>.yaml`):

```yaml
hooks:
  pre_task:
    - mylab.hooks.labwatch.FetchSubjectLevel
    - mylab.hooks.notify.SlackSessionStart
  post_task:
    - mylab.hooks.labwatch.PushSessionData
    - mylab.hooks.notify.SlackSessionEnd
```

### Task-specific hooks — run only for that task

Declared in the task's `task.settings` file:

```ini
HOOKS_PRE_TASK = ["murineshiftwork.tasks.sequence_automated.hooks.CheckEquipmentReady"]
HOOKS_POST_TASK = []
```

### Execution order

```
global pre_task hooks  (setup YAML order)
task-specific HOOKS_PRE_TASK  (task.settings order)
──── task runs ────
task-specific HOOKS_POST_TASK
global post_task hooks
```

---

## Error isolation

A hook that raises logs a `WARNING` with traceback and is skipped. It does not abort the
session. This applies to both pre- and post-hooks. If a pre-hook fails to set a required
key in `task_settings`, the task falls back to whatever default it already has in settings.

---

## Example: LabWatch level fetch (local → remote migration path)

### Current local implementation (inside task_objects.py)

`TaskControl._fetch_subject_state()` reads `~/.murineshiftwork/sequence_automated/{subject}_level.json`.

### Migrated to hook — local version

```python
# mylab/hooks/subject_state.py

import json
from pathlib import Path
from murineshiftwork.logic.hooks import TaskHook, HookContext

STORE = Path("~/.murineshiftwork/sequence_automated").expanduser()

class FetchSubjectLevel(TaskHook):
    def pre_run(self, ctx: HookContext) -> None:
        f = STORE / f"{ctx.subject}_level.json"
        if f.exists():
            data = json.loads(f.read_text())
            level = int(data.get("level", ctx.task_settings.get("start_level", 1)))
            ctx.task_settings["start_level"] = level
            ctx.task_settings["reset_level"] = False

    def post_run(self, ctx: HookContext) -> None:
        level = ctx.output.get("final_level")
        if level is None:
            return
        STORE.mkdir(parents=True, exist_ok=True)
        f = STORE / f"{ctx.subject}_level.json"
        existing = json.loads(f.read_text()) if f.exists() else {}
        existing["level"] = level
        f.write_text(json.dumps(existing, indent=2))
```

### Migrated to hook — LabWatch API version

```python
class FetchSubjectLevel(TaskHook):
    def pre_run(self, ctx: HookContext) -> None:
        state = labwatch_client.get_state(ctx.subject, ctx.task_name)
        if state and "level" in state:
            ctx.task_settings["start_level"] = state["level"]
            ctx.task_settings["reset_level"] = False

    def post_run(self, ctx: HookContext) -> None:
        if "final_level" in ctx.output:
            labwatch_client.post_state(ctx.subject, ctx.task_name, {
                "level": ctx.output["final_level"],
                "session": ctx.session_paths.get("session_basename"),
            })
```

The task code (`TaskControl`, `sequence_automated.py`) is identical in both cases.

---

## Files to create

| File | Purpose |
|---|---|
| `src/murineshiftwork/logic/hooks.py` | `HookContext`, `TaskHook`, `load_hooks()`, `run_hooks_pre/post()` |
| `src/murineshiftwork/logic/task_process.py` | Wire hook calls into `__init__` and `__exit__` |
| `src/murineshiftwork/logic/config_models.py` | Add `HooksConfig` field to `SetupConfig` |

---

## Process logic cleanup required before hooks are wired in

The current `TaskProcess` (`logic/task_process.py`) has several design issues that the hook
system makes harder to ignore. Address these in the same pass:

### 1. `exec()` for dynamic task import

`init_task()` uses `exec()` to import and instantiate the task class. This is opaque to
type checkers and IDEs, and silently suppresses `ImportError` if the wrong name is used.

**Replace with:**
```python
import importlib

def init_task(self):
    mod = importlib.import_module(
        f"murineshiftwork.tasks.{self.task_name}.{self.task_name}"
    )
    Task = getattr(mod, "Task")
    self.task_runner = Task(bpod=self.bpod, **self.input_kwargs)
```

### 2. `TaskRunner` inherits `QThread`

All task logic runs in a `QThread`, which mandates `PyQt6` for every task — including
headless acquisition sessions with no GUI. Now that `PyQt6` is in `[extras_require] qt`,
this is an invisible hard dependency.

**Problem**: the `isRunning()` / `start()` thread API and the Qt signal integration for
online plotting are conflated in one base class.

**Recommended fix**: make `TaskRunner` inherit from `threading.Thread` with a compatible
`start()` / `is_alive()` → `isRunning()` shim, and let tasks that need Qt signals opt in
via a mixin or by the plotting process managing its own Qt context.

This is a larger refactor; defer to Phase 1 once hooks are stable.

### 3. Class-level mutable default `input_kwargs = {}`

```python
class TaskProcess(object):
    input_kwargs = {}   # shared across all instances — Python gotcha
```

**Fix**: initialise in `__init__`:
```python
self.input_kwargs = {}
```

### 4. `__del__` calls `exit_safely()`

`__del__` is not guaranteed to run (interpreter shutdown, circular refs). The `__exit__`
context manager already handles cleanup. Remove `__del__`.

### 5. `__init__` is monolithic

With hooks, pre-hooks must run after Bpod connects but before `init_task()`. The current
`__init__` conflates construction + execution. The minimal change: insert the hook call
between `connect_bpod()` and `if auto_init: init_task()`.

The longer-term fix (Phase 1): split `__init__` into `__init__` (construction only),
`prepare()` (paths + Bpod + pre-hooks), `run()` (task thread), so the context-manager
pattern is the only supported usage and `auto_start=True` is removed.
