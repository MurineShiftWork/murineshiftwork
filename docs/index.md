# Murine Shift Work

Behaviour acquisition framework for head-fixed and freely moving murine experiments. Runs on Bpod state machines with optional camera ensemble video, stage tower positioning, and electrophysiology synchronisation via TTL barcodes.

## Key features

- **Bpod state machine** tasks: probabilistic switching, sequence learning, optotagging, airpuff, and more
- **TTL barcode synchronisation**: encodes Unix timestamps as a 37-bit pulse train for offline alignment of Bpod, cameras (RCE), and ephys (Open Ephys / Neuropixels)
- **Setup configs**: per-setup YAML files in a shared git-tracked directory (`msw_configs/`)
- **Subject configs**: per-subject YAML with per-task parameter overrides
- **CLI**: `msw run`, `msw setup`, `msw subject`, `msw init`

## Quick start

```bash
# 1. Point MSW at your shared config directory (once per machine)
msw init /mnt/maindata/msw_configs

# 2. Register a subject
msw subject add -s mouse001

# 3. Run a task
msw run -t _test_flush_water -s mouse001 --setup setup-1

# 4. Override task parameters inline
msw run -t _test_flush_water -s mouse001 --setup setup-1 \
    -ts VALVE_OPENING_TIME_MS=60 N_FLUSH_CYCLES=5
```

## Package layout

```
murineshiftwork/
├── src/murineshiftwork/      # main package
│   ├── cli/                  # CLI entry points
│   ├── logic/                # core logic (config, calibration, barcode, …)
│   ├── tasks/                # task protocols
│   ├── namespace/            # path generation
│   └── readers/              # session data readers
├── tests/                    # pytest test suite
├── playground/               # debug scripts, Arduino sketches, MATLAB reference
├── external/                 # companion packages (msw_open_ephys, provision_rpi, …)
├── docs/                     # this documentation (MkDocs)
└── msw_configs/              # shared setup/subject configs (separate git repo)
```

## See also

- [New Machine Setup](getting_started/new_machine.md)
- [Setup Config reference](setup/setup_config.md)
- [Barcode TTL sync](barcode_ttl_integration.md)
- [Calibration](calibration/water.md)
