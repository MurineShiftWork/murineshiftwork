# Murine Shift Work

Behaviour acquisition framework for head-fixed and freely moving murine experiments. Runs on Bpod state machines with optional camera ensemble video, stage tower positioning, and electrophysiology synchronisation via TTL barcodes.

## Key features

- **Bpod state machine** tasks: probabilistic switching, sequence learning, optotagging, airpuff, and more
- **TTL barcode synchronisation**: encodes Unix timestamps as a 37-bit pulse train for offline alignment of Bpod, cameras (RCE), and ephys (Open Ephys / Neuropixels)
- **Setup configs**: per-setup YAML files in a shared git-tracked directory (`msw_configs/`)
- **Subject configs**: per-subject YAML with per-task parameter overrides
- **CLI**: `msw run`, `msw action`, `msw calibration`, `msw post`, `msw setup`, `msw subject`, `msw tasks`, `msw init`, `msw agent`
- **Config overlay**: site-specific parameter adjustments in `msw_configs/tasks/<name>/task.yaml`; merged on top of bundled defaults without touching the installed package
- **Named task modes**: `--task-mode <preset>` switches between `mode:` sections in `task.yaml` (e.g. habituation, deterministic, probe); mode is written to subject YAML and persists across sessions
- **Pre/post session hooks**: custom Python classes registered in setup or task YAML; run before task init and after session end to integrate databases, Slack, LabWatch, etc.

## Quick start

```bash
# 1. Point MSW at your shared config directory (once per machine)
msw init /data/msw_configs

# 2. Register a subject
msw subject add -s mouse001

# 3. Run a task
msw run -t _test_flush_valves -s mouse001 --setup setup-1

# 4. Override task parameters inline
msw run -t _test_flush_valves -s mouse001 --setup setup-1 \
    -ts VALVE_OPENING_TIME_MS=60 N_FLUSH_CYCLES=5
```

## Package layout

`murineshiftwork` is an umbrella distribution. The framework is split across
several independently versioned packages that all contribute to the shared
`murineshiftwork.*` namespace (a PEP 420 namespace package), so
`import murineshiftwork.<module>` works regardless of which package ships it:

```
murineshiftwork.*  (namespace)
├── msw-core            → murineshiftwork.{cli, logic, hardware, hooks}
├── msw-io             → murineshiftwork.{namespace, readers, io}
├── msw-tasks-core      → murineshiftwork.tasks._calibration_*, _test_*   (bundled utility protocols)
├── msw-tasks-lab       → murineshiftwork.tasks.{sequence, …}             (lab science tasks, private)
├── msw-tasks-example   → murineshiftwork.tasks.<example>                 (template for external tasks)
└── msw-agent          → murineshiftwork.logagent                        (session/trial relay)

Standalone plugin packages (own top-level package, register via entry points):
├── msw-open-ephys      → `msw oe` ephys host-session control
└── msw-flir-bonsai     → FLIR/Bonsai camera backend

Supporting libraries: acquisition-namespace (path spec), pypulsepal,
one-axis-stage, serial-scale-*, ttl-barcoder, rpi-camera-ensemble.
```

Optional extras pull these in: `murineshiftwork[tasks]` (msw-tasks-core),
`[oe]` (msw-open-ephys), `[agent]` (msw-agent), `[full]` for the rig bundle.
Per-machine setup and subject YAML live in a separate `msw_configs/` git repo,
pointed to via `msw init`.

## Documentation structure

| Section | Contents |
|---|---|
| [Getting started](getting_started/quickstart.md) | Installation, new machine, quickstart |
| [Concepts](concepts/architecture.md) | Architecture, config system, hooks, session files |
| [Tasks](tasks/sequence.md) | Per-task behavioural paradigm, implementation, and parameter reference |
| [Tutorials](tutorials/calibration.md) | Calibration, adding setups and subjects |
| [CLI reference](cli/run.md) | Per-subcommand reference pages (`run`, `action`, `calibration`, `post`, `setup`, `subject`, `tasks`, `agent`, `init`) |
| [Hardware setup](setup/SERIAL.md) | Serial ports, wiring, cameras, DHCP |

## See also

- [New Machine Setup](getting_started/new_machine.md)
- [Setup Config reference](setup/setup_config.md)
- [Hook System](concepts/hook_system.md)
