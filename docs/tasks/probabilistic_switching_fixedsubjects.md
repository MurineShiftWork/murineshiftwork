# Probabilistic Switching Task (head-fixed)

**Protocol name:** `probabilistic_switching_fixedsubjects`
**Setup:** Head-fixed, retractable lick spouts (left / right); no centre port
**Video:** RPi camera ensemble (optional: falls back to no-video if agents unreachable)

---

## Behavioural paradigm

The same two-armed bandit reward-probability block structure as the freely moving version
(see [`probabilistic_switching.md`](probabilistic_switching.md)), adapted for a head-fixed
preparation. The animal licks left or right spouts to indicate its choice. Spouts are
retracted between trials and extended at choice time via an actuator stage.

Head-fixed recordings allow simultaneous electrophysiology (Neuropixels, tetrodes) or
two-photon imaging during the decision task, with TTL barcode synchronisation between
Bpod, cameras, and ephys hardware.

---

## Differences from the freely moving version

| Aspect | Freely moving | Head-fixed |
|---|---|---|
| Choice ports | Physical nose-poke ports | Retractable lick spouts |
| Initiation | Centre-poke | Spout approach / no centre port |
| Lick detection | Port infrared | Port IR or piezo lick sensor (`use_piezo_lick_detection`) |
| Anti-bias | Forced-choice only | Forced-choice + optional stage anti-bias (`stage_anti_bias_bool`) |
| ITI | Fixed or jittered | Three-parameter jitter `[min, max, step]` |
| Camera | Optional | Optional (graceful fallback if RPi unreachable) |

---

## Block structure

Identical to the freely moving version: probabilistic blocks with covert switches,
criterion-based switching (EMA of choices), minimum block length, and stochastic
post-criterion delay. See [`probabilistic_switching.md § Block structure`](probabilistic_switching.md#block-structure).

---

## Trial structure

```
[ITI with spouts retracted]
  → extend spouts
  → lick left / lick right
        ↓ rewarded side
    reward (valve open)  →  [spout retract]  →  ITI
        ↓ non-rewarded side
    no reward  →  [spout retract]  →  ITI
        ↓ timeout
    timeout  →  [spout retract]  →  ITI
```

- Lick events are mapped via `LICK_EVENT_LEFT` / `LICK_EVENT_RIGHT` (Bpod port events)
- Default: `Port1In` (left), `Port3In` (right): configurable in setup YAML for port remapping
- Piezo lick detection substitutes the port-in event when `use_piezo_lick_detection = true`

---

## Anti-bias mechanisms

### Forced-choice trials

When the animal has made `forced_choice_threshold` consecutive choices to the same side,
the next trial is a forced-choice trial: only the opposite spout is extended. Logged as
`forced_choice` in trial data.

### Stage anti-bias

When `stage_anti_bias_bool = true`, the last `stage_anti_bias_n_back` choices are
inspected after each trial. If all choices are to the same side, the opposite spout is
moved closer (using the stage actuator) to make the preferred side mildly less accessible.
Configurable via `stage_anti_bias_max` (maximum position offset).

---

## Lick port mapping

Bpod port numbers for left/right lick events are defined per setup in the setup YAML
`task_overrides` section, so the same task YAML works across rigs with different wiring:

```yaml
# subjects/<mouse>.yaml  or  setups/<setup>.yaml
task_overrides:
  probabilistic_switching_fixedsubjects:
    LICK_EVENT_LEFT: Port1In
    LICK_EVENT_RIGHT: Port3In
```

---

## Camera and video

The RPi camera ensemble is configured via `config_file_camera` (path to an
`EnsembleAcquisitionConfig` YAML). If the file is absent or any camera agent is
unreachable at session start, the task logs a warning and continues without video :
Bpod acquisition is unaffected.

Video files are stored under `{subject}/{session_basename}/` in the output directory,
with session metadata injected via `conductor.initialize_acquisition()`.

---

## TTL barcode synchronisation

An opening barcode (37-bit, BNC channel `HARDWARE_BNC_TRIAL_START`) is fired before
trial 1. A closing barcode fires after the last trial. These encode Unix wall-clock
timestamps and allow offline alignment of Bpod event times with camera frames and
ephys recordings.

---

## Key parameters

| Parameter | Default | Description |
|---|---|---|
| `probabilities` | `[[10,50],[50,10],[10,90],[90,10],[50,50],[50,90],[90,50]]` | Block probability pairs |
| `min_block_length` | 20 | Minimum trials per block |
| `min_trials_post_criterion` | 5 | Minimum extra trials after criterion |
| `max_block_length` | 75 | Hard upper limit on block length |
| `mean_neutral_block_length` | 25 | Mean length of neutral blocks |
| `criterion_contrast_blocks` | 0.75 | EMA threshold for contrast-block switch |
| `criterion_tau` | 5 | EMA time-constant (trials) |
| `forced_choice_threshold` | 20 | Consecutive same-side choices before forced trial |
| `stage_anti_bias_bool` | false | Enable stage-position anti-bias |
| `stage_anti_bias_max` | 50 | Max stage offset for anti-bias (device units) |
| `stage_anti_bias_n_back` | 5 | Trials to inspect for stage anti-bias |
| `use_piezo_lick_detection` | false | Use piezo sensor instead of IR port events |
| `LICK_EVENT_LEFT` | `Port1In` | Bpod event for left lick |
| `LICK_EVENT_RIGHT` | `Port3In` | Bpod event for right lick |
| `inter_trial_interval` | `[3, 5, 0.5]` | ITI jitter [min, max, step] (s) |
| `reward_amount_ul` | 2.0 µL | Water per rewarded choice |
| `n_max_trials` | 750 | Hard trial limit |

---

## Modes

| Mode | Description |
|---|---|
| `stage00habituation` | 100% reward, simplified block structure, generous timeouts |
| `stage01` | Full task, standard thresholds |
| (additional per-lab modes) | Defined in config-dir overlay |

---

## Online plot

- Moving average of choices (left/right bias)
- Block probability trace
- Per-trial outcome scatter (rewarded / unrewarded / forced-choice)
- Session trial count

---

## Running

```bash
msw run -t probabilistic_switching_fixedsubjects -s mouse001 --setup setup-1 \
    --task-mode stage01
# Without video (or when RPis are offline):
msw run -t probabilistic_switching_fixedsubjects -s mouse001 --setup setup-1
# Video explicitly configured:
msw run -t probabilistic_switching_fixedsubjects -s mouse001 --setup setup-1 \
    -ts config_file_camera=/data/msw_configs/cameras/setup-1.yaml
```
