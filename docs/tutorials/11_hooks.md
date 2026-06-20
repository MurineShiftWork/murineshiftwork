# Tutorial 11: Hooks *(optional)*

## Prerequisites

[Tutorial 10: The central monitor UI](10_monitor_ui.md), and familiarity with
the [setup config](03_setup_config.md).

## What you'll learn

- What hooks are and the two points at which they run.
- How to write a minimal hook.
- How to register a hook so it runs for a rig or a task.

## 1. What hooks are

A hook is a small Python class that MSW runs around a session, so you can connect
external systems (a database, a lab notebook, a notifier) without editing any
task code. There are two call points:

- **pre-run**: before the task starts. A pre-run hook may read or mutate the
  resolved task settings, for example to fetch an animal's current training
  level from a database and inject it.
- **post-run**: after the task thread finishes. A post-run hook reads session
  output, for example to push a summary somewhere or write progress back.

Hooks are isolated: if one raises, MSW logs a warning and skips it, and the
session continues. They are an integration layer, not part of the protocol's
correctness.

## 2. Write a minimal hook

A hook subclasses `TaskHook` and implements either or both call points:

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

The `HookContext` gives a hook what it needs: `ctx.subject`, `ctx.task_name`, the
mutable `ctx.task_settings` (pre-run writes here), `ctx.session_paths`, and a
shared `ctx.output` dict (post-run reads here). Treat these as the stable hook
surface.

## 3. Register a hook

Reference a hook by its dotted import path. Where you register it decides its
scope.

For every session on a rig, register in that rig's setup YAML:

```yaml
hooks:
  pre_task:
    - mylab.hooks.FetchSubjectLevel
  post_task:
    - mylab.hooks.PushSessionData
```

For one task regardless of rig, register in the task's `task.yaml` (so it travels
through the [overlay chain](05_config_overlays.md)):

```yaml
default:
  HOOKS_PRE_TASK:
    - mylab.hooks.CheckEquipmentReady
  HOOKS_POST_TASK: []
```

The dotted path must be importable in the environment the rig runs in (install
your hook package alongside MSW).

## You now know

Hooks are isolated Python classes that run before and after a session through a
`HookContext`, letting you integrate external systems without touching task code.
Register them in a setup YAML for a whole rig or in a task's `task.yaml` for one
protocol.

## Next

[Tutorial 12: Post-processing](12_post_processing.md) *(optional)*. For the call
order and error semantics, see the [Hook System](../concepts/hook_system.md).
