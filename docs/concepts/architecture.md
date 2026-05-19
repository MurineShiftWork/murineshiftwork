# Architecture Overview

## Layers

```
CLI (msw run / msw action / ...)
  │
  ├── evaluate_args()        — validates + resolves all config, builds ExecutionConfig
  │
  ├── run_task()             — imports task module, delegates to TaskProcess
  │
  └── TaskProcess            — session lifecycle: paths, Bpod, hooks, TaskRunner thread
          │
          ├── pre-hooks      — run before task init; may mutate task_settings
          ├── TaskRunner     — task-specific thread (run loop + state machine)
          └── post-hooks     — run after task thread; may read output
```

## Key modules

| Module | Purpose |
|---|---|
| `murineshiftwork.cli.evaluate` | Settings priority chain, config loading |
| `murineshiftwork.logic.task_process` | Session orchestration |
| `murineshiftwork.logic.hooks` | Pre/post hook system |
| `murineshiftwork.logic.config` | Config models, IO, deep_merge |
| `murineshiftwork.hardware.bpod` | Bpod connection and action drivers |
| `murineshiftwork.tasks.*` | Task-specific protocol implementations |
