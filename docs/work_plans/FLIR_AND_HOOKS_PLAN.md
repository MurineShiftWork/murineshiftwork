# FLIR Camera + Hook System — Implementation Plan

_Status: planning. Pick up from here._

---

## 1. FLIR camera acquisition (msw-flir-bonsai)

### What exists

| File | State |
|------|-------|
| `msw_flir_bonsai/web/api.py` | Complete — FastAPI app, `/camera/{id}` HTML, `/ws/camera/{id}` WebSocket, `/status` |
| `msw_flir_bonsai/web/zmq_receiver.py` | Complete — `ZmqReceiver(Thread)`, ZMQ SUB, lock-protected latest-frame |
| `msw_flir_bonsai/web/stream_page.py` | Complete — canvas + WebSocket HTML |
| `msw_flir_bonsai/server.py` | Empty (two commented imports) |
| `msw_flir_bonsai/cli.py` | Empty (TODO comment) |
| `msw_flir_bonsai/entrypoints.py` | Empty |
| Bonsai workflows | Complete — `{flycap,spinnaker} × {1cam,2cam} × {plain,zmq}` variants |

The preview path (Bonsai ZMQ PUB → `ZmqReceiver` → FastAPI WebSocket → browser) is fully implemented.
No subprocess launcher exists yet.

### What is missing

**BonsaiRunner** — a class that wraps `subprocess.Popen` to launch/stop a Bonsai workflow with
the correct `--property` CLI args assembled from a session config dict:

```
basepath, session_name, cam1idx, cam1fps, cam1pub (ZMQ port), cam1vid.ext, …
```

Minimal interface:
```python
class BonsaiRunner:
    def start(self, bonsai_exe, workflow_path, session_config: dict) -> None: ...
    def stop(self) -> None: ...
    def is_running(self) -> bool: ...
```

### Decisions needed before implementing

1. **Spinnaker vs Flycap** — new code should target Spinnaker only. Flycap workflows stay for legacy
   hardware but are not the development path.

2. **ZMQ preview in production** — use the `*-zmq.bonsai` workflow variant and run the FastAPI
   preview server, or use the plain variant (recording only, no preview)? Recommendation: plain for
   production (lower overhead), ZMQ variant for debugging/monitoring sessions.

3. **Package consolidation** — `msw-flir-bonsai/` and `msw-acq-flir/` are near-identical. Consolidate
   into one package (`msw-acq-flir`) before adding new code.

### Integration with `sequence` task

The sequence task needs both FLIR and RCE cameras. Camera acquisition should be started/stopped via
**pre/post-task hooks** (see §2), not inside task logic. This keeps `Task.run()` camera-agnostic.

Hook registration in `sequence/task.yaml` (once `BonsaiRunner` exists):
```yaml
HOOKS_PRE_TASK:
  - murineshiftwork.tasks.sequence.hooks.StartFlirAcquisition
  - murineshiftwork.tasks.sequence.hooks.FetchSubjectLevel
HOOKS_POST_TASK:
  - murineshiftwork.tasks.sequence.hooks.StopFlirAcquisition
```

`StartFlirAcquisition.pre_run(ctx)` derives the FLIR session folder from `ctx.session_paths` using
the same child-session naming convention as RCE (`is_child_session_to`), then calls
`BonsaiRunner.start(...)`.

---

## 2. Hook system

### Design (from HOOKS.md — do not duplicate there)

`HookContext` dataclass passed to every hook:
```python
@dataclass
class HookContext:
    subject: str
    task_name: str
    task_settings: dict
    session_paths: dict
    setup: str = ""
    output: dict = field(default_factory=dict)  # hooks write results here
```

`TaskHook` base:
```python
class TaskHook:
    def pre_run(self, ctx: HookContext) -> None: pass
    def post_run(self, ctx: HookContext) -> None: pass
```

Hook paths registered as dotted import strings in `task.yaml` under `HOOKS_PRE_TASK` /
`HOOKS_POST_TASK`, merged with setup YAML `hooks:` section.

### Files to create / modify

| Action | File |
|--------|------|
| Create | `src/murineshiftwork/logic/hooks.py` — `HookContext`, `TaskHook`, `load_hooks`, `run_hooks_pre/post` |
| Modify | `src/murineshiftwork/logic/task_process.py` — wire hooks between `connect_bpod` and `init_task`; call `run_hooks_post` in `exit_safely` |
| Create | `src/murineshiftwork/tasks/sequence/hooks.py` — `FetchSubjectLevel` hook |
| Modify | `src/murineshiftwork/tasks/sequence/task.yaml` — add `HOOKS_PRE_TASK` list |
| Modify | `src/murineshiftwork/logic/config.py` (SetupConfig) — add `HooksConfig` field |

### `logic/hooks.py` — full implementation

```python
import importlib
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class HookContext:
    subject: str
    task_name: str
    task_settings: dict
    session_paths: dict
    setup: str = ""
    output: dict = field(default_factory=dict)


class TaskHook:
    def pre_run(self, ctx: HookContext) -> None:
        pass

    def post_run(self, ctx: HookContext) -> None:
        pass


def _load_hook(dotted_path: str) -> TaskHook:
    module_path, class_name = dotted_path.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()


def load_hooks(hook_paths: list) -> list:
    hooks = []
    for p in hook_paths:
        try:
            hooks.append(_load_hook(p))
        except Exception as exc:
            log.warning(f"Hook '{p}' could not be loaded: {exc}")
    return hooks


def run_hooks_pre(hooks: list, ctx: HookContext) -> None:
    for h in hooks:
        try:
            h.pre_run(ctx)
        except Exception:
            log.warning(f"Hook pre_run failed: {h}", exc_info=True)


def run_hooks_post(hooks: list, ctx: HookContext) -> None:
    for h in hooks:
        try:
            h.post_run(ctx)
        except Exception:
            log.warning(f"Hook post_run failed: {h}", exc_info=True)
```

### Wiring in `TaskProcess.__init__`

Insert after `connect_bpod()` / bpod injection block, before `init_task()`:

```python
from murineshiftwork.logic.hooks import HookContext, load_hooks, run_hooks_pre

pre_hook_paths = self.input_kwargs.get("HOOKS_PRE_TASK", [])
post_hook_paths = self.input_kwargs.get("HOOKS_POST_TASK", [])
self._hooks_pre = load_hooks(pre_hook_paths)
self._hooks_post = load_hooks(post_hook_paths)
self._hook_ctx = HookContext(
    subject=self.subject,
    task_name=self.task_name,
    task_settings=self.input_kwargs.get("settings.task.patched", {}),
    session_paths=self.session_paths,
    setup=self.input_kwargs.get("setup", ""),
)
run_hooks_pre(self._hooks_pre, self._hook_ctx)
```

In `exit_safely()`, before closing bpod:
```python
from murineshiftwork.logic.hooks import run_hooks_post
run_hooks_post(self._hooks_post, self._hook_ctx)
```

Guard both against `AttributeError` (hooks not initialised if `__init__` raised early).

### Sequence task level persistence via hooks

**Strategy: Option A (recommended for now)**

Keep `TaskControl._push_subject_state()` writing the level JSON on every level change (no change to
task logic). The hook's job is only the `pre_run` side: read the stored level and inject it into
`ctx.task_settings["start_level"]` before the task thread reads it.

When LabWatch API is ready, replace the JSON read in `FetchSubjectLevel.pre_run` with an HTTP GET
and the JSON write in `_push_subject_state` with an HTTP POST. The task code stays unchanged.

`src/murineshiftwork/tasks/sequence/hooks.py`:

```python
import json
import logging
from murineshiftwork.logic.hooks import TaskHook, HookContext
from murineshiftwork.tasks.sequence.task_objects import LEVEL_STORE_DIR, _LEGACY_LEVEL_STORE_DIR

log = logging.getLogger(__name__)


class FetchSubjectLevel(TaskHook):
    """Inject the stored level into task_settings before the task starts."""

    def pre_run(self, ctx: HookContext) -> None:
        subject = ctx.subject
        f = LEVEL_STORE_DIR / f"{subject}_level.json"
        if not f.exists():
            legacy = _LEGACY_LEVEL_STORE_DIR / f"{subject}_level.json"
            if legacy.exists():
                f = legacy
        if f.exists():
            state = json.loads(f.read_text())
            level = state.get("level", 1)
            ctx.task_settings.setdefault("start_level", level)
            ctx.output["loaded_level"] = level
            log.info(f"FetchSubjectLevel: subject={subject} level={level}")
```

`sequence/task.yaml` addition:
```yaml
default:
  ...
  HOOKS_PRE_TASK:
    - murineshiftwork.tasks.sequence.hooks.FetchSubjectLevel
  HOOKS_POST_TASK: []
```

### LabWatch migration path (future)

When subjects roam between setups, replace `FetchSubjectLevel.pre_run` body with:
```python
import httpx
resp = httpx.get(f"{LABWATCH_URL}/subjects/{subject}/state", timeout=5)
state = resp.json()
```
And replace `TaskControl._push_subject_state` body with:
```python
httpx.post(f"{LABWATCH_URL}/subjects/{subject}/state", json=state, timeout=5)
```
No other code changes needed.
