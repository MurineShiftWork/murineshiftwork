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

This design follows the general class of serial-order memory tasks used to study
hippocampal and prefrontal contributions to sequential behaviour.

---

## Trial structure

```
[TTL pulse]  →  wait_poke_0  →  reward_poke_0  →  wait_poke_1  →  ...
                      ↓ wrong port / timeout
                   punish  →  exit_seq  →  ITI  →  [next trial]
```

- **`wait_poke_i`** — all 8 Bpod ports active; correct port → `reward_poke_i`, any other port → `punish`; Tup → `punish` (unless `init_port_timeout_s = 0`)
- **`reward_poke_i`** — opens valve for calibrated reward; fires SoftCode for chirp sound; advances to next wait state or `exit_seq` after last poke
- **No-response trials** — if the animal does not poke within `init_port_timeout_s` on the first port, the trial is marked `no_response`: buffers and level evaluation are skipped entirely

---

## Training levels

Defined in `training_levels.csv` (50 rows, ported directly from the MATLAB protocol).

| Column | Meaning |
|---|---|
| `reward1–reward4` | Water at pokes 1–4 (µL) |
| `final_reward` | Water at the last poke (µL) |
| `led1–led5` | LED intensity at each sequence position (0–90, MATLAB scale → 0–255 PWM) |
| `response_window_ms` | Per-poke timeout (ms); overridden by `min_response_window_s` |

### Level progression

| Levels | Reward pattern | LED pattern |
|---|---|---|
| 1 | Water at all 5 pokes | All ports lit |
| 2–13 | Intermediate rewards progressively removed; last poke keeps water | All ports lit |
| 14–49 | Last poke only | LEDs faded out one position per tier |
| 50 | Last poke only (1.8 µL) | Only first port lit; all others dark |

---

## Progression and regression

Performance is tracked over a rolling buffer of `buffer_trials` trials (default 10).
The buffer is cleared on every level change.

| Condition | Result |
|---|---|
| Buffer full and `perf > progression_threshold` (0.9) | Advance one level |
| Buffer full and `perf < regression_threshold` (0.2) | Regress one level |
| `prevent_regression_below_start = true` | Floor at the level the session started at |

Two performance metrics are tracked simultaneously:

- **`ordered`** (default) — MATLAB `strfind`-style: the sequence must appear as a contiguous subsequence in the poke stream (extra pokes between correct pokes are allowed)
- **`perfect`** — deduplicated poke stream must exactly match the template (no extra pokes)

`scoring_metric` in `task.yaml` selects which metric drives progression. The perfect rate is always logged regardless of the active metric.

---

## Sound feedback

A single tone (default 8 kHz, 0.2 s) plays on **every correct poke at every level**, whether or not water is delivered. This is correctness feedback, not a reward predictor — matching the original MATLAB specification: *"only correct pokes result in a sound, informing the mouse whether the poke was right or wrong"*.

Sound is registered non-blocking (`play_blocking=False`), so the softcode handler returns immediately without stalling Bpod event polling.

---

## Response window — note for freely moving mice

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

The animal's training level is written to the subject YAML (`config_dir/subjects/<name>.yaml`) at session end via `save_session_end()`, making it git-tracked and portable across machines. A crash-recovery backup (`~/.murineshiftwork/sequence/<subject>_level.json`) is updated after every level change but is never read at session start — the subject YAML is authoritative.

On session end the log reports:
```
Session end — 'mouse001': level 12, trials 312 (289 task, 23 no-response)
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

## Modes

| Mode | Description |
|---|---|
| `habituation` | Reset to level 1 (`reset_level: true, start_level: 1`) |

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
