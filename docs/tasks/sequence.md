# Sequence Task

**Protocol name:** `sequence`
**Setup:** Freely moving, standard 8-port Bpod panel
**Source:** Ported from `Sequence_Automated/` MATLAB/Bpod protocol

---

## Behavioural paradigm

The mouse must poke a fixed sequence of ports in order (default: ports 2 → 1 → 6 → 3 → 7).
Every correct poke is marked by an audible chirp; water is delivered at pokes where the
current training level assigns a non-zero reward. A wrong poke or per-poke timeout ends
the trial immediately with a punish state (no sound, no water, short blackout).

The task is purely sequence-guided: the mouse must learn the port order, not just find
individual ports. At early levels LEDs illuminate the expected port; LEDs are faded out
progressively across the 50 training levels so that the mouse must rely on memory rather
than visual guidance.

The paradigm implemented here follows the sequence-learning task described by
Thompson & Rollik (2024); see [References](#references). More broadly it belongs
to the class of serial-order memory tasks used to study hippocampal and
prefrontal contributions to sequential behaviour.

---

## Trial structure

```
[free_reward_state]  →  wait_poke_0  →  [delay_poke_0]  →  reward_poke_0  →  wait_poke_1  →  ...
      (optional)              ↓ wrong port / timeout
                           punish  →  exit_seq  →  ITI  →  [next trial]
```

- **`free_reward_state`** *(optional)*: delivers a non-contingent reward at trial start before the sequence begins; only present when `free_reward_probability > 0` and the draw fires
- **`wait_poke_i`**: all 8 Bpod ports active; correct port → `delay_poke_i` or `reward_poke_i`, any other port → `punish`; Tup → `punish` (unless `init_port_timeout_s = 0`)
- **`delay_poke_i`** *(optional)*: blank gap between correct poke and valve opening; only present when `reward_delay_s > 0`
- **`reward_poke_i`**: opens valve for calibrated reward; fires SoftCode for chirp sound; advances to next wait state or `exit_seq` after last poke
- **No-response trials**: if the animal does not poke within `init_port_timeout_s` on the first port, the trial is marked `no_response`: buffers and level evaluation are skipped entirely

---

## Training levels

Defined in `training_levels.csv` (50 rows, ported directly from the MATLAB protocol).

| Column | Meaning |
|---|---|
| `reward1-reward4` | Water at pokes 1-4 (µL) |
| `final_reward` | Water at the last poke (µL) |
| `led1-led5` | LED intensity at each sequence position (0-90, MATLAB scale → 0-255 PWM) |
| `response_window_ms` | Per-poke timeout (ms); overridden by `min_response_window_s` |

### Level progression

| Levels | Reward pattern | LED pattern |
|---|---|---|
| 1 | Water at all 5 pokes | All ports lit |
| 2-13 | Intermediate rewards progressively removed; last poke keeps water | All ports lit |
| 14-49 | Last poke only | LEDs faded out one position per tier |
| 50 | Last poke only (1.8 µL) | Only first port lit; all others dark |

---

## Progression and regression

Performance is tracked over a rolling buffer of `buffer_trials` trials (default 10).
The buffer is cleared on every level change.

| Condition | Result |
|---|---|
| Buffer full and `perf > progression_threshold` (0.9) | Advance one level (capped at the last level) |
| Buffer full and `perf < regression_threshold` (0.2) | Regress one level |
| `prevent_regression_below_start = true` | Raise the regression floor to the level the session started at |

Level 1 is a one-way launch level: once a subject advances out of it, levels are
transient up/down but it can **never regress back to level 1** (hard regression
floor is 2, regardless of config). `prevent_regression_below_start` only raises
that floor further, never below 2.

Two performance metrics are tracked simultaneously:

- **`ordered`** (default): MATLAB `strfind`-style: the sequence must appear as a contiguous subsequence in the poke stream (extra pokes between correct pokes are allowed)
- **`perfect`**: deduplicated poke stream must exactly match the template (no extra pokes)

`scoring_metric` in `task.yaml` selects which metric drives progression. The perfect rate is always logged regardless of the active metric.

---

## Sound feedback

A single tone (default 8 kHz, 0.2 s) plays on **every correct poke at every level**, whether or not water is delivered. This is correctness feedback, not a reward predictor: matching the original MATLAB specification: *"only correct pokes result in a sound, informing the mouse whether the poke was right or wrong"*.

Sound is registered non-blocking (`play_blocking=False`), so the softcode handler returns immediately without stalling Bpod event polling.

---

## Response window: note for freely moving mice

The CSV response windows (60 ms, 30 ms, 5 ms) were designed for a head-fixed lick-spout version of the task and are physiologically impossible for mice poking physical ports at a distance. The setting `min_response_window_s` (default **2.0 s**) clamps all per-poke windows to this minimum. Level 1 (36 000 ms = 36 s) is already above the floor.

Set `min_response_window_s = 0` to use the raw CSV values for a head-fixed adaptation.

---

## Soft-stop criteria

The task does not hard-stop at session limits, but logs a `WARNING` once each criterion is reached and draws a red dashed reference line in the online plot:

| Criterion | Default | Setting |
|---|---|---|
| Total reward | 800 µL | `stop_reward_ul` |
| Task trials | 500 | `stop_trials` |
| Session time | 60 min | `stop_time_min` |
| Level gain | +15 from session start | `stop_level_delta` |

---

## Session state and continuity

The animal's training level is written to the subject YAML (`config_dir/subjects/<name>.yaml`) at session end via `save_session_end()`, making it git-tracked and portable across machines. A crash-recovery backup (`~/.murineshiftwork/sequence/<subject>_level.json`) is updated after every level change but is never read at session start: the subject YAML is authoritative.

On session end the log reports:
```
Session end: 'mouse001': level 12, trials 312 (289 task, 23 no-response)
```

---

## Key parameters

| Parameter | Default | Description |
|---|---|---|
| `sequence` | `[2,1,6,3,7]` | Port sequence (Bpod port numbers, 1-indexed) |
| `start_level` | 1 | Starting level (overridden by subject YAML) |
| `reset_level` | false | Ignore saved level; start at `start_level` |
| `buffer_trials` | 10 | Rolling performance window |
| `scoring_metric` | `ordered` | `ordered` or `perfect` |
| `progression_threshold` | 0.9 | Fraction correct to advance |
| `regression_threshold` | 0.2 | Fraction correct to regress |
| `prevent_regression_below_start` | false | Floor regression at session start level |
| `min_response_window_s` | 2.0 | Minimum per-poke wait (0 = use raw CSV) |
| `init_port_timeout_s` | 10.0 | Max wait for first poke (0 = no timeout) |
| `iti_duration` | 0.4 s | Inter-trial interval |
| `punish_duration` | 0.5 s | Punishment blackout duration |

---

## Reward probe features

Three optional features for probing dopamine reward prediction error signals. All are disabled by default and can be combined or activated per-mode.

### Reward perturbation

Probabilistically replaces the level-determined reward for specific poke positions or ports on a per-trial draw.

```yaml
reward_perturbation:
  enabled: true
  target: position          # "position" (0-indexed slot) or "port" (hardware port 1-8)
  matched_omission_duration: false  # see below
  distribution:
    4:                      # apply to the final poke (position index 4)
      - {amount_ul: 0.0,  probability: 0.15}  # 15% omission
      - {amount_ul: 3.6,  probability: 0.15}  # 15% doubled reward
      # remaining 70% → nominal level amount (no entry needed)
```

- `amount_ul: null` is the explicit sentinel for "use nominal"; can also be omitted (remainder logic)
- Probabilities may sum to < 1.0; the residual probability is implicitly assigned to the nominal level amount
- Positions not listed in `distribution` always receive nominal rewards

**Per-trial output fields added to `info`:**

| Field | Description |
|---|---|
| `reward_amounts` | Delivered amounts (perturbed or nominal) |
| `reward_amounts_nominal` | Level-table amounts (always nominal) |
| `reward_perturbation_applied` | `true` if any poke was non-nominal this trial |
| `reward_perturbation_draws` | List of `{position, port, nominal_ul, delivered_ul, perturbed}` per poke |

### Matched omission duration

When `matched_omission_duration: true` inside `reward_perturbation`, omitted pokes (amount 0) hold the `reward_poke_i` state open for the same duration the nominal reward would have taken rather than the minimum 1 ms. This anchors the negative prediction error to the same time point as normal reward delivery.

Only meaningful when `reward_perturbation.enabled: true` and omissions are in the distribution.

### Reward delay

Inserts a blank delay state between a correct poke and valve opening. Useful for studying how animals track temporal reward expectations.

```yaml
reward_delay_s: 0.5          # fixed delay applied every trial
```

Or a linearly ramped delay that increases over the session:

```yaml
reward_delay_ramp:
  start_s: 0.0
  increment_s: 0.002         # +2 ms per completed task trial
  max_s: 2.0
```

When `reward_delay_ramp` is set (and `increment_s > 0`) it overrides `reward_delay_s`.

The actual delay used is recorded in each trial's `info.reward_delay_s`.

### Non-contingent reward

Occasionally delivers a free reward at trial start, before the sequence begins. The reward is dispensed by opening the valve at `free_reward_port` (defaults to the last sequence port). The trial then proceeds normally.

```yaml
free_reward_probability: 0.05   # 5% of trials receive a free reward
free_reward_ul: 1.8
free_reward_port: null           # null = last port in sequence
```

**Per-trial output fields:**

| Field | Description |
|---|---|
| `free_reward_given` | `true` if a non-contingent reward was delivered this trial |
| `liquid_ul_trial` | Includes free reward in the trial total |
| `liquid_ul_cumulative` | Includes free reward in the session total |

---

## Modes

| Mode | Description |
|---|---|
| `habituation` | Reset to level 1 (`reset_level: true, start_level: 1`) |
| `expert` | High trial cap; prevents regression below session start level |
| `probe` | Lower trial cap; strict progression threshold (0.95); no regression floor |
| `reward_probe` | Activates reward perturbation on the final poke (15% omission / 15% doubled); regression locked at session start level |

---

## Online plot panels

- Performance (active metric + exact-sequence rate)
- Training level trace
- Outcome raster (correct / incorrect / no-response)
- Poke raster (log-scale by default; configurable)
- Session reward and trial count progress
- Sequence duration

---

## Running

```bash
msw run -t sequence -s mouse001 --setup setup-1
msw run -t sequence -s mouse001 --setup setup-1 --task-mode habituation
msw run -t sequence -s mouse001 --setup setup-1 -ts start_level=5 scoring_metric=perfect
```

---

## References

- Thompson & Rollik (2024). *bioRxiv* (preprint). The sequence-learning paradigm
  underlying this task.
<!-- TODO: add the bioRxiv DOI/URL once confirmed. -->
