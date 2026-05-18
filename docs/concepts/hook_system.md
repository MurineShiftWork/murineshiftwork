# Hook System

Hooks are Python classes that run before and after each task session. They let you integrate
external systems (databases, Slack, LabWatch) without modifying task code.

## Call points

```
TaskProcess.__init__()
  connect Bpod
  ── pre-hooks run ─── hooks may mutate task_settings here
  init_task()          task reads the (possibly patched) settings
  run_task thread
TaskProcess.__exit__()
  ── post-hooks run ── hooks may read session output
  disconnect Bpod
```

## Implementing a hook

```python
from murineshiftwork.logic.hooks import TaskHook, HookContext

class FetchSubjectLevel(TaskHook):
    def pre_run(self, ctx: HookContext) -> None:
        level = my_db.get_level(ctx.subject, ctx.task_name)
        if level is not None:
            ctx.task_settings["start_level"] = level

    def post_run(self, ctx: HookContext) -> None:
        final = ctx.output.get("final_level")
        if final is not None:
            my_db.set_level(ctx.subject, ctx.task_name, final)
```

## Registering hooks

In the setup YAML (runs for every task on this setup):

```yaml
hooks:
  pre_task:
    - mylab.hooks.FetchSubjectLevel
  post_task:
    - mylab.hooks.PushSessionData
```

In `task.yaml` (runs only for this task):

```yaml
default:
  HOOKS_PRE_TASK:
    - murineshiftwork.tasks.sequence_automated.hooks.CheckEquipmentReady
  HOOKS_POST_TASK: []
```

## HookContext fields

| Field | Type | Description |
|---|---|---|
| `subject` | `str` | Subject name |
| `task_name` | `str` | Resolved task name |
| `task_settings` | `dict` | Mutable task settings dict (pre-hooks write here) |
| `session_paths` | `dict` | File paths for this session |
| `execution_config` | `ExecutionConfig` | Full setup + subject config |
| `output` | `dict` | Shared dict; any hook can write / read |

## Error isolation

A hook that raises logs a `WARNING` and is skipped. The session continues with whatever
`task_settings` were already set.
