# Sequence Automated

A 5-port sequential poke task with 50 automated training levels.
Ported from `tests/Sequence_Automated/` (MATLAB/Bpod) into the MSW Python framework,
structured as a freely moving protocol following `probabilistic_switching`.

---

## Task overview

The mouse must poke a sequence of ports in a fixed order (default: 1 → 2 → 3 → 4 → 5).
Every correct poke is marked by an audible chirp.  Water is delivered at pokes where the
current training level assigns a non-zero reward amount.  A wrong poke or response-window
timeout immediately ends the trial in a punish state (silence, no water).

The difficulty increases automatically across 50 levels by:
1. Removing intermediate water rewards (levels 1–13)
2. Fading out the port LEDs one by one (levels 14–50)
3. Shortening the response window (relevant mainly for head-fixed setups; see note below)

---

## Trial structure (state machine)

```
ttl_on  →  ttl_off  →  wait_poke_0  →  reward_poke_0
                                 ↓ wrong/timeout
                               punish  →  exit_seq  →  [end]

wait_poke_0  →  reward_poke_0  →  wait_poke_1  →  ...  →  reward_poke_4  →  exit_seq  →  [end]
```

Each `wait_poke_i` state:
- Illuminates the LED of the expected port at the current level's intensity
- All 8 Bpod ports are enumerated: correct port → `reward_poke_i`, any other port → `punish`
- Timer expiry → `punish`

Each `reward_poke_i` state:
- Opens the valve for the port if reward amount > 0 (valve time from water calibration)
- Fires SoftCode to play the reward chirp (always, valve-independent — see Sound section)
- Transitions to the next wait state, or `exit_seq` after the final poke

---

## Sound feedback

A single tone (default 8 kHz, 0.3 s) plays on **every correct poke at every level**,
regardless of whether water is delivered.  At level 50, pokes 1–4 produce no water but
still produce the chirp; only poke 5 delivers water.

This matches the original MATLAB protocol, which describes the task as *"sound guided —
only correct pokes result in a sound, informing the mouse whether the poke was right or
wrong"*.  The chirp is correctness feedback, not a reward predictor.

Sound is registered non-blocking (`play_blocking=False`) so the softcode handler returns
immediately without stalling Bpod event polling.

Relevant settings: `reward_sound`, `reward_sound_frequency`, `reward_sound_duration`,
`reward_sound_amplitude`.

---

## Training levels

Defined in `training_levels.csv` (50 rows, ported directly from the MATLAB protocol).

| Column | Meaning |
|--------|---------|
| reward1–reward4 | Water at pokes 1–4 (µL) |
| final_reward | Water at poke 5 (µL) |
| led1–led5 | LED intensity at each sequence position (0–90, MATLAB scale) |
| response_window_ms | Per-poke timeout (ms; see note below) |

LED intensities are scaled from the MATLAB range 0–90 to the Bpod PWM range 0–255.
`led1` is always the intensity for the *first poke position* (not port number 1), etc.

### Progression through levels

| Levels | Reward pattern | LED pattern |
|--------|---------------|-------------|
| 1 | 5 µL at all 5 pokes | All ports lit (90) |
| 2–13 | Intermediate rewards gradually removed; final poke keeps 1.8 µL | All ports lit |
| 14–23 | Final reward only (1.8 µL) | LED at position 2 faded 90 → 0 |
| 24–32 | Final reward only | LED at position 5 faded 90 → 0 |
| 33–41 | Final reward only | LED at position 3 faded 90 → 0 |
| 42–49 | Final reward only | LED at position 4 faded 90 → 0 |
| 50 | Final reward only (1.8 µL) | Only position 1 lit (90); all others 0 |

### Progression / regression rules

Performance is evaluated over a rolling buffer of `buffer_trials` trials (default 10).

| Condition | Action |
|-----------|--------|
| Level 1: < `level_1_min_trials` (50) completed | No check yet |
| Level 1: buffer ≥ 9/10 correct | Advance |
| Levels 2–13: buffer ≥ `progression_threshold` (0.9) | Advance |
| Levels 14–49: buffer ≥ `progression_threshold_advanced` (0.8) | Advance |
| Any level: buffer < `regression_threshold` (0.2) | Regress one level |
| Regression floor | `prevent_regression_below_start = True` prevents going below the level at session start |

The buffer is cleared on every level change.

---

## Response window — important note for freely moving mice

The CSV response windows are **in milliseconds** and were designed for a **head-fixed
lick-sequence** setup (values: 60 ms for levels 2–13, 30 ms for levels 14–49, 5 ms for
level 50).  These are physiologically impossible for mice poking physical ports at
distance.

The setting `min_response_window_s` (default **2.0 s**) clamps the per-poke window to a
minimum, overriding the short CSV values.  Level 1 (36 000 ms = 36 s) is already above
this floor.

Set `min_response_window_s = 0` to use the raw CSV values, e.g. for a head-fixed
lick-spout version of the task.

---

## Subject state and session continuity

Per-subject training level is persisted in:

```
~/.murineshiftwork/sequence_automated/
    {subject}_level.json      # current level + last-updated timestamp
    subjects.json             # registry of all subjects (last session, current level)
```

On session start the level is loaded automatically.  Two ways to override:

- `reset_level = True` in `task.settings` — ignores saved level, starts at `start_level`
- `start_level = N` — the level to use when no history exists, or when `reset_level = True`

The registry (`subjects.json`) is updated on every level change and at session start, so
it always reflects the current level for each subject.

---

## Key differences from the MATLAB original

| Aspect | MATLAB | Python (this task) |
|--------|--------|-------------------|
| Response window | Raw CSV ms values | Clamped by `min_response_window_s` (default 2 s) |
| Sound | PsychToolbox, blocking | `StereoSound`, non-blocking |
| Level persistence | Separate `.mat` file per subject | JSON in `~/.murineshiftwork/sequence_automated/` |
| Wrong-port detection | All ports enumerated in SMA | All 8 Bpod ports enumerated per wait state |
| Level in trial record | Recorded after possible change | Snapshot taken before `_update_level()` call |

---

## Running the task

```bash
msw run -s <subject_id> -t sequence_automated
```

To start fresh from level 1:

```python
# task.settings
reset_level = True
start_level = 1
```

To inspect all subjects and their current levels:

```bash
cat ~/.murineshiftwork/sequence_automated/subjects.json
```
