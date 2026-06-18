# Architecture Overview

## System components

The diagram shows how the MSW packages connect across the three physical contexts
(experiment rig, RPi camera cluster, ephys machine). Solid arrows are software
calls; dashed arrows are hardware TTL sync pulses.

```mermaid
graph TD
    subgraph rig["Experiment rig"]
        CLI["msw CLI\nrun · action · post · agent"]
        Core["murineshiftwork\nTaskProcess · hooks · config · barcode"]
        Bpod["Bpod\nstate machine"]
        PP["pypulsepal\nPulsePal optogenetics"]
        Scale["serial-scale-*\nwater calibration"]
        Stage["one-axis-stage\nstage positioning"]
        FLIR["msw-flir-bonsai\nFLIR camera via Bonsai"]
        Barcode["ttl-barcoder\nbarcode encode / decode"]
        NS["acquisition-namespace\npath and file naming"]
        Hooks["hooks\nLabWatch · custom integrations"]
    end

    subgraph rpi["RPi cluster"]
        RCE["rpi-camera-ensemble\nconductor → agents → cameras"]
    end

    subgraph oe_machine["Ephys machine"]
        OE["msw-open-ephys\nOpen Ephys HTTP controller"]
    end

    CLI --> Core
    Core --> Bpod
    Core --> PP & Scale & Stage & FLIR
    Core --> Barcode & NS
    Core --> Hooks
    Core -->|HTTP| RCE
    Core -->|HTTP| OE

    Bpod -.->|TTL sync| RCE
    Bpod -.->|TTL sync| OE
```

All hardware drivers (`pypulsepal`, `serial-scale-*`, `one-axis-stage`, `msw-flir-bonsai`,
`rpi-camera-ensemble`, `msw-open-ephys`) are optional extras. A minimal rig install only
needs the base `murineshiftwork` package with `acquisition-namespace` and `ttl-barcoder`.

The TTL barcode is output as a digital pulse train by the Bpod state machine. The same
signal is recorded on a dedicated channel by Open Ephys and by each RPi camera's GPIO
TTL input, enabling offline sample-accurate alignment across all three systems.

---

## Internal layers

```
CLI (msw run / msw action / ...)
  │
  ├── evaluate_args()       : validates + resolves all config, builds ExecutionConfig
  │
  ├── run_task()            : imports task module, delegates to TaskProcess
  │
  └── TaskProcess           : session lifecycle: paths, Bpod, hooks, TaskRunner thread
          │
          ├── pre-hooks     : run before task init; may mutate task_settings
          ├── TaskRunner    : task-specific thread (run loop + state machine)
          └── post-hooks    : run after task thread; may read output
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
