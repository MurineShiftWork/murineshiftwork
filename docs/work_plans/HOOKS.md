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

## Implementation status — DONE (2026-05-18)

| File | Status |
|---|---|
| `src/murineshiftwork/logic/hooks.py` | Done — `HookContext`, `TaskHook(fatal=)`, `SessionAbortError`, `load_hooks()`, `collect_hooks()`, `run_pre/post_hooks()` |
| `src/murineshiftwork/logic/task_process.py` | Done — pre-hooks after Bpod connect, post-hooks in `__exit__`; fatal hooks close Bpod before re-raise |
| `src/murineshiftwork/logic/config/models.py` | Done — `HooksConfig(pre_task, post_task)` field on `SetupConfig` |

34 tests in `tests/test_hooks.py`. See `docs/concepts/hook_system.md` for usage.

---

## Deferred TaskProcess cleanup (still outstanding)

These were identified as pre-requisites during design but resolved with minimal changes instead:

- **`exec()` → `importlib`**: DONE in an earlier sprint — `init_task()` uses `importlib.import_module`.
- **`QThread` → `threading.Thread`**: DONE in an earlier sprint.
- **Class-level mutable `input_kwargs = {}`**: still present — low risk (only one instance per session), defer to ControllerSession sprint.
- **`__del__` calls `exit_safely()`**: still present — `__exit__` handles cleanup; `__del__` is redundant but harmless, defer.
- **Monolithic `__init__`**: hooks are wired correctly with the current structure; full split deferred to ControllerSession sprint.
