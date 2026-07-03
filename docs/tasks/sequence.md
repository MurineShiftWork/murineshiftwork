# Sequence Task

> The sequence task implements the behavioural paradigm from Thompson EJ, Rollik L, et al., Stephenson-Jones M. "Replay of procedural experience is independent of the hippocampus." bioRxiv 2024.06.05.597547. https://www.biorxiv.org/content/10.1101/2024.06.05.597547v1

**Protocol name:** `sequence`
**Setup:** Freely moving, standard 8-port Bpod panel

---

## Behavioural paradigm

The mouse must poke a fixed sequence of ports in order (the default sequence is
ports `2 → 1 → 6 → 3 → 7`). Every correct poke is marked by an audible chirp;
water is delivered at the pokes where the current training level assigns a
non-zero reward. A wrong poke or a per-poke timeout ends the trial immediately
with a punish state (no sound, no water, short blackout).

The task is sequence-guided: the mouse must learn the port *order*, not just
find individual ports. At early levels the LEDs illuminate the expected port,
and both the reward guidance and the LED guidance are faded out progressively
across the training levels, so the animal comes to rely on memory rather than on
guidance.

---

## Trial structure

```
[free_reward_state]  →  wait_poke_0  →  [delay_poke_0]  →  reward_poke_0  →  wait_poke_1  →  ...
      (optional)              ↓ wrong port / timeout
                           punish  →  exit_seq  →  ITI  →  [next trial]
```

- **`free_reward_state`** *(optional)*: delivers a non-contingent reward at trial start before the sequence begins; present only when `free_reward_probability > 0` and the draw fires.
- **`wait_poke_i`**: all ports active; the correct port advances to `delay_poke_i` / `reward_poke_i`, any other port → `punish`; a timeout (`Tup`) → `punish` unless `init_port_timeout_s = 0`.
- **`delay_poke_i`** *(optional)*: blank gap between correct poke and valve opening; present only when `reward_delay_s > 0`.
- **`reward_poke_i`**: opens the valve for the level's reward amount and fires a SoftCode for the chirp; advances to the next wait state or to `exit_seq` after the last poke.
- **No-response trials**: if the animal does not poke within `init_port_timeout_s` on the first port, the trial is marked `no_response` and level evaluation is skipped for that trial.

---

## The curriculum model

Levels are **generated parametrically** from a `curriculum:` block, not read from
a per-level CSV. Every per-level surface
— reward, LED, response window, and progression rules — is a parametric
*definition* that is evaluated once at session init into a clean per-level table.

The authored block has this shape:

```yaml
curriculum:
  n_levels: 50
  selection:
    policy: single            # single | blocked | random | proportional
  sequences:
    - id: standard
      ports: [2, 1, 6, 3, 7]  # Bpod port numbers, 1-indexed
      start_level: 1
      # each channel is a Ref: a library name, an inline spec, or {file: ...}
      reward: {}              # RewardCurveSpec (defaults shown below)
      led: {}                 # LedCurveSpec
      window: {}              # ScalarStepSpec
      rules: {}               # LevelRulesSpec
```

Each of the four channels on a sequence is a **Ref**, resolved with precedence
`sequence value > global default > shipped standard`. A Ref may be:

- a **name** into `curriculum.libraries.<channel>` (a reusable named spec),
- an **inline** spec (the parameter block written directly), or
- a **file reference** `{file: path/to/spec.yaml}`.

### Reward channel (`RewardCurveSpec`, µL)

Reward for a sequence of `n_pokes` has `n_pokes-1` guide columns plus a terminal
`final_reward`. Early levels flood every poke (`entry`); guides are then removed
one at a time, `stride` levels apart, each ramping `hold → 0` over `ramp`
levels; the terminal reward settles to `final_plateau`.

| Field | Default | Meaning |
|---|---|---|
| `hold` | `2.0` | Guide reward before removal |
| `entry` | `(5.0, 3.0, 2.0)` | Per-poke flood for the first levels |
| `fade_start` | `5` | Level at which guide removal begins |
| `stride` | `2` | Levels between successive guide removals |
| `ramp` | `2` | Levels one guide takes to fade to 0 |
| `final_plateau` | `1.8` | Terminal reward after guides are gone |
| `tail_boost` / `tail_start` | `0.0` / `null` | Optional late lift of the terminal reward |

### LED channel (`LedCurveSpec`, intensity)

A per-position guide-removal curve (same fade primitive as reward). By default
port 1 keeps its LED (`keep: (1,)`) and the remaining positions fade in a bespoke
order.

| Field | Default | Meaning |
|---|---|---|
| `hold` | `90.0` | LED intensity before removal |
| `fade_start` | `15` | Level at which LED fading begins |
| `stride` | `9` | Levels between successive LED removals |
| `ramp` | `9` | Levels one LED takes to fade to 0 |
| `fade_order` | `(2, 5, 3, 4)` | Removal order (1-based positions) |
| `keep` | `(1,)` | Positions whose LED never fades |

### Response window (`ScalarStepSpec`, seconds)

A piecewise scalar schedule: `steps` maps a level to the per-poke response
window; the value forward-fills until the next listed level. `steps` must define
level 1. The shipped default starts very wide and tightens with level (e.g.
`{1: 36000, 2: 60, 9: 50, 10: 45, 12: 40, 13: 30, 50: 5}`).

### Progression rules (`LevelRulesSpec`)

Per-level transition rule evaluated into a `TransitionRule` for each level.

| Field | Default | Meaning |
|---|---|---|
| `window` | `10` | Rolling performance buffer size (trials) |
| `prog_required` | `9` | Correct out of `window` needed to advance |
| `reg_required` | `2` | Regress when correct/`window` falls below this |
| `metric` | `rolling_mean` | `rolling_mean` or `perfect` |
| `prog_thresh` / `reg_thresh` | `null` | Optional exact float overrides for the derived counts |

---

## Selection policy (multi-sequence sessions)

`curriculum.selection.policy` chooses which sequence each trial runs:

| Policy | Behaviour |
|---|---|
| `single` | Exactly one sequence (the standard case). |
| `random` | Uniform draw per trial across the listed sequences. |
| `proportional` | Weighted draw per trial using each sequence's `weight`. |
| `blocked` | Run one sequence for a block, then switch. Requires a `blocks:` list. |

Additional selection controls:

- `no_immediate_repeat`: forbid the same sequence twice in a row.
- `block_order`: for `blocked`, one of `fixed`, `shuffled`, or `random`.
- `seed`: make the per-trial draws reproducible.

A `blocked` schedule lists blocks explicitly; a block may override the reward
curve for its span without resetting the underlying level state:

```yaml
selection:
  policy: blocked
  block_order: shuffled
  blocks:
    - {sequence: standard, length: 40}
    - {sequence: standard, length: 40, reward: rich}   # reward-variant block
```

Per-trial provenance (`sequence_id`, `block_index`, `trial_in_block`) is recorded
for analysis.

---

## Progression and regression

Performance is tracked over a rolling buffer (`window`, default 10). The buffer
must be full before any level change, then per trial (mirroring the MATLAB
`UpdateLevel.m` logic):

| Condition | Result |
|---|---|
| `perf > prog_thresh` and not at the last level | Advance one level |
| `perf < reg_thresh` | Regress one level |
| `prevent_regression_below_start = true` | Raise the regression floor to the session start level |

Level 1 is a one-way launch level: once a subject advances out of it, levels move
transiently up and down but **can never regress back to level 1** (the hard
regression floor is 2). `prevent_regression_below_start` only raises that floor
further, never below 2.

Two scoring metrics are computed every trial:

- **`ordered`** (default): MATLAB `strfind`-style — the sequence must appear as a
  contiguous subsequence of the poke stream (extra pokes between correct pokes
  are allowed).
- **`perfect`**: the deduplicated poke stream must exactly match the template.

`scoring_metric` selects which drives progression; the perfect rate is always
logged.

---

## Sound feedback

A single tone (default 8 kHz, 0.2 s) plays on **every correct poke at every
level**, whether or not water is delivered — it is correctness feedback, not a
reward predictor. Sound is registered non-blocking so the softcode handler
returns immediately without stalling Bpod event polling.

---

## Soft-stop criteria

The task does not hard-stop at session limits, but logs a one-time `WARNING` and
draws a red dashed reference line in the online plot when each criterion is
reached:

| Criterion | Default | Setting |
|---|---|---|
| Total reward | 800 µL | `stop_reward_ul` |
| Task trials | 500 | `stop_trials` |
| Session time | 60 min | `stop_time_min` |
| Level gain | +15 from session start | `stop_level_delta` |

---

## Session state and continuity

The subject's training level is written to the subject YAML
(`config_dir/subjects/<name>.yaml`) at session end via `save_session_end()`,
making it git-tracked and portable across machines. A crash-recovery backup
(`~/.murineshiftwork/sequence/<subject>_level.json`) is updated after every level
change but is never read at session start — the subject YAML is authoritative.

On session end the log reports, for example:

```
Session end: 'mouse001': level 12, trials 312 (289 task, 23 no-response)
```

---

## Key parameters

| Parameter | Default | Description |
|---|---|---|
| `start_level` | 1 | Starting level (overridden by subject YAML; persisted per subject) |
| `reset_level` | false | Ignore the saved level; start at `start_level` |
| `scoring_metric` | `ordered` | `ordered` or `perfect` |
| `prevent_regression_below_start` | false | Floor regression at the session start level |
| `init_port_timeout_s` | 10.0 | Max wait for the first poke (0 = no timeout) |
| `iti_duration` | 0.4 s | Inter-trial interval |
| `punish_duration` | 0.5 s | Punishment blackout duration |
| `n_max_trials` | 1500 | Session trial cap |
| `record_video` | false | Record camera video for the session |

The barcode parameters (`barcode_bits`, `barcode_bit_duration_ms`, …) configure
the TTL sync pulses; see [Barcode Sync](../howto/barcode_sync.md).

---

## Reward probe features

Three optional features for probing reward-prediction-error signals. All are
disabled by default and can be combined or activated per-mode.

### Reward perturbation

Probabilistically replaces the level-determined reward for specific poke
positions or ports on a per-trial draw.

```yaml
reward_perturbation:
  enabled: true
  target: position          # "position" (0-indexed slot) or "port" (hardware port)
  matched_omission_duration: false
  distribution:
    4:                      # apply to the final poke (position index 4)
      - {amount_ul: 0.0,  probability: 0.15}  # 15% omission
      - {amount_ul: 3.6,  probability: 0.15}  # 15% doubled reward
      # remaining 70% → nominal level amount
```

- `amount_ul: null` (or omission from the list) means "use the nominal amount".
- Probabilities may sum to `< 1.0`; the residual is assigned to the nominal amount.

**Per-trial output fields** added to `info`: `reward_amounts`,
`reward_amounts_nominal`, `reward_perturbation_applied`,
`reward_perturbation_draws`.

When `matched_omission_duration: true`, omitted pokes hold the reward state open
for the same duration a nominal reward would have taken, anchoring the negative
prediction error to the normal reward time.

### Reward delay

Inserts a blank delay between a correct poke and valve opening:

```yaml
reward_delay_s: 0.5          # fixed delay every trial
```

Or a linearly ramped delay across the session:

```yaml
reward_delay_ramp:
  start_s: 0.0
  increment_s: 0.002         # +2 ms per completed task trial
  max_s: 2.0
```

When the ramp is set (`increment_s > 0`) it overrides `reward_delay_s`. The delay
used is recorded in each trial's `info.reward_delay_s`.

### Non-contingent reward

Occasionally delivers a free reward at trial start, before the sequence begins,
by opening the valve at `free_reward_port` (defaults to the last sequence port):

```yaml
free_reward_probability: 0.05
free_reward_ul: 1.8
free_reward_port: null       # null = last port in the sequence
```

**Per-trial output fields**: `free_reward_given`; `liquid_ul_trial` and
`liquid_ul_cumulative` include the free reward.

---

## Modes

| Mode | Description |
|---|---|
| `habituation` | Reset to level 1 (`reset_level: true`), looser thresholds, short cap |
| `expert` | High trial cap; prevents regression below the session start level |
| `probe` | Lower trial cap; strict progression threshold; no regression floor |

Activate with `--task-mode <name>`; the mode is written to the subject YAML and
persists across sessions.

---

## Online plot panels

- Performance (active metric + exact-sequence rate)
- Training-level trace
- Outcome raster (correct / incorrect / no-response)
- Poke raster (log-scale by default; configurable)
- Session reward and trial-count progress
- Sequence duration

---

## Running

```bash
msw run -t sequence -s mouse001 --setup setup-1
msw run -t sequence -s mouse001 --setup setup-1 --task-mode habituation
msw run -t sequence -s mouse001 --setup setup-1 -ts start_level=5 scoring_metric=perfect
```
