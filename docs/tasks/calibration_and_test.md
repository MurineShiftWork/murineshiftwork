# Calibration & Test Protocols

These are the bundled non-behavioural protocols shipped by `msw-tasks-core`
(installed with `murineshiftwork[tasks]`). They are prefixed `_calibration_` and
`_test_` and are used to calibrate hardware and to smoke-test a rig before
running a behavioural task. They are discoverable like any task:

```bash
msw tasks list
msw run -t _test_bpod_connect --setup setup-1
```

Names beginning with an underscore are utility protocols, not subject-facing
behavioural tasks.

## Calibration

| Protocol | Purpose |
|---|---|
| `_calibration_liquid_static` | Open a valve a fixed number of times at a fixed duration; weigh the dispensed water to fit the valve's volume-per-open. |
| `_calibration_liquid_dynamic` | Iterative valve calibration with a progress bar and before/after weight delta; converges the open-time → volume fit. |
| `_calibration_sound_latency` | Measure true bpod-state → sound-execution latency. Wire the sound-card output into Bpod **BNC input 1**; the task opens the low-latency audio stream, plays a short blip, and records the `BNC1High` onset as the end-to-end latency. See the calibration tutorial for wiring. |

Liquid calibration writes the fit into the setup's valve calibration data; the
fit model (`linear` / `exponential`) is selected in the setup config. A stale or
missing calibration triggers a warning at task preflight.

## Hardware tests

| Protocol | Checks |
|---|---|
| `_test_bpod_connect` | Connects to the Bpod, reports the raw machine type and behaviour-port count. First thing to run on a new or re-flashed Bpod. |
| `_test_minimal_task` | Smallest possible state machine; confirms the task framework, session output, and Bpod round-trip work end to end. |
| `_test_flush_valves` | Opens water valves to flush lines / prime tubing. Valve set and open time are overridable (`-ts VALVE_NUMBERS=[1,3] VALVE_OPENING_TIME_MS=...`). |
| `_test_pulsepal_connect` | Connects to a PulsePal and confirms serial communication. |
| `_test_stage_move` | Commands the one-axis stage tower through a move; confirms stage serial + motion. |
| `_test_ttl_outputs` | Toggles Bpod TTL outputs; confirms wiring to downstream hardware (ephys, cameras). |
| `_test_ttl_barcodes` | Emits TTL barcodes; confirms the barcode encoder and the receiving acquisition systems decode them. |
| `_test_barcode_iti` | Exercises barcode emission across inter-trial intervals to validate timing/decode rate. |
| `_test_video` | Triggers the configured camera backend to record a short clip; confirms camera config + capture path. |

## Typical new-rig sequence

1. `_test_bpod_connect` - Bpod is detected and reports the expected ports.
2. `_test_flush_valves` - water lines primed.
3. `_calibration_liquid_static` or `_calibration_liquid_dynamic` - valves calibrated.
4. `_test_ttl_outputs` / `_test_ttl_barcodes` - sync wiring verified (if recording ephys/video).
5. `_test_video` - camera backend records (if cameras configured).
6. `_calibration_sound_latency` - audio path characterised (if sound feedback is used).

Each protocol accepts the usual `--setup`, `--simulate`, and `-ts KEY=VALUE`
overrides. Run `msw tasks defaults <name>` to see a protocol's parameters.
