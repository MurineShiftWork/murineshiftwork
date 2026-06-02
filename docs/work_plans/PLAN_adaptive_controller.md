# Adaptive Trial Controller — Work Plan

**Status:** Design / pre-implementation
**Branch target:** `ft/adaptive-controller`
**Depends on:** nothing blocking; can start any sprint

---

## Problem

Both `sequence` and `probabilistic_switching` contain ad-hoc trial-parameter update logic
embedded inside `TaskControl`. The algorithms differ (deque threshold vs. exponential
moving average) but the *role* is identical: observe each trial outcome and mutate task
parameters for the next trial.

This coupling means:
- The same pattern must be re-implemented per task
- Unit testing requires instantiating or mocking `TaskControl` with Bpod
- Adding a new adaptive protocol (e.g. staircase, Bayesian) requires touching every task separately
- The reward-probe features just added to `sequence` have no equivalent upgrade path for `probabilistic_switching`

---

## Current state

### `sequence` — level threshold

```
perf_buffer (deque, maxlen=10)
  → mean > progression_threshold (0.9)  → _advance_level()  → clears buffer, saves JSON
  → mean < regression_threshold  (0.2)  → _regress_level()  → clears buffer, saves JSON
```

Session-start floor: regression prevented below `_session_start_level` if flag set.
Persistence: JSON written on every level change + `save_session_end()`.
Called once per trial from `update()` after scoring.

### `probabilistic_switching` — EMA block switch

`ExponentialMovingAverage` (from `logic/maths.py`) tracks choice bias.
Block switch fires when EMA crosses a threshold and min-trials-post-criterion met.
No discrete "levels"; parameters are the block's reward probability pair.
Persistence: no per-trial JSON write; state lives only in memory.

### Shared infrastructure

`logic/maths.py` — `ExponentialMovingAverage` (already reusable)
`logic/task_process.py` — `TaskRunner` base Thread; `update_session_yaml()` persistence helper
No abstract base for `TaskControl`.

---

## Proposed design — Option 3: controller object

A standalone `TrialAdaptiveController` in `logic/adaptive_controller.py`.

`TaskControl` instantiates one and delegates to it. The controller owns the update
algorithm and returns an action signal; `TaskControl` handles persistence and hardware.
Composition over inheritance — no changes to the `TaskRunner` base or task-yaml schemas.

### Interface

```python
class AdaptiveController:
    """Abstract base. Concrete subclasses implement the update algorithm."""

    def prepare(self, trial_index: int) -> dict:
        """Called before draw_next_trial().
        Returns a dict of parameter overrides merged into the task for this trial.
        Empty dict = no change."""

    def observe(self, trial_index: int, outcome: dict) -> AdaptiveSignal:
        """Called after update() with the scored trial outcome.
        Returns an AdaptiveSignal describing what changed."""


@dataclass
class AdaptiveSignal:
    action: Literal["none", "advance", "regress", "switch", "end"]
    params_changed: dict   # keys that changed and their new values
    save_state: bool       # True → TaskControl should persist state now
    note: str              # logged at INFO level if non-empty
```

`outcome` dict passed to `observe()` contains the keys already written to `info` per trial:
`trial_index`, `level`, `outcome`, `is_correct`, `is_ordered`, `is_perfect`,
`perf_buffer_mean`, `reward_amounts`, etc.

### Concrete controllers (phase 1 scope)

| Class | Algorithm | Replaces |
|---|---|---|
| `ThresholdLevelController` | Deque mean vs. two thresholds; advance/regress by 1 | `sequence._update_level` |
| `EmaBlockController` | EMA + min-trials criterion | `probabilistic_switching` block switch |

Both read their config from a `controller:` sub-dict in `task_settings` (or fall back to
flat keys for backward compat during migration).

### How `sequence.TaskControl` uses it

```python
# __init__
self._controller = ThresholdLevelController(task_settings)

# draw_next_trial()
overrides = self._controller.prepare(self._session_task_trials)
# overrides might be {} or {"level": 12}

# update() — after scoring
signal = self._controller.observe(trial_index, info)
if signal.action in ("advance", "regress"):
    self.current_level = signal.params_changed["level"]
    self.perf_buffer.clear()
    self.perf_buffer_perfect.clear()
if signal.save_state:
    self._save_level()
    self._register_subject(subject)
```

Persistence stays in `TaskControl` — the controller returns `save_state: True` as a signal
rather than owning the JSON write. This keeps the controller unit-testable without file I/O.

---

## What does NOT change

- `task.yaml` schema — existing flat keys (`progression_threshold`, `buffer_trials`, etc.)
  are read by `ThresholdLevelController` via backward-compat shim; no user-visible change
- `TaskRunner` base class
- Session file format
- Online plotting
- The reward-probe features (`RewardPerturbation`, `reward_delay_s`, `free_reward_probability`)
  — those are orthogonal; the controller only adjusts *which level's* parameters are used

---

## Non-goals for this sprint

- Bayesian adaptive, QUEST, staircase — define the interface; implement `ThresholdLevel` and
  `EmaBlock` only
- Moving `probabilistic_switching` to the new controller — do it after `sequence` is validated
- New task modes or config keys beyond the controller sub-dict shim
- Any UI or plot changes

---

## Implementation phases

### Phase 1 — `logic/adaptive_controller.py` + tests (no task changes)

- Write `AdaptiveController` ABC, `AdaptiveSignal` dataclass
- Write `ThresholdLevelController` mirroring the exact deque logic currently in `sequence`
- Write `EmaBlockController` mirroring `probabilistic_switching` EMA logic
- Unit tests with no Bpod dependency: drive each controller with a synthetic outcome stream,
  assert signal sequence

**Deliverable:** `logic/adaptive_controller.py`, `tests/test_adaptive_controller.py`

### Phase 2 — wire `sequence.TaskControl`

- Replace `_update_level` / `_advance_level` / `_regress_level` with `ThresholdLevelController`
- `_pending_reward_draw` and scoring paths unchanged
- All existing sequence tests must pass without modification

**Deliverable:** `tasks/sequence/task_objects.py` refactored; all tests green

### Phase 3 — wire `probabilistic_switching.TaskControl`

- Replace EMA + block-switch logic with `EmaBlockController`
- Introduce `controller:` config sub-dict in `probabilistic_switching/task.yaml`

**Deliverable:** `tasks/probabilistic_switching/task.py` refactored; tests green

### Phase 4 — docs

- `docs/concepts/adaptive_controller.md` — interface reference, how to write a new controller
- Update `docs/tasks/sequence.md` and `docs/tasks/probabilistic_switching.md` to note the
  controller layer

---

## Files affected

| File | Change |
|---|---|
| `src/murineshiftwork/logic/adaptive_controller.py` | **NEW** — ABC + concrete classes |
| `tests/test_adaptive_controller.py` | **NEW** |
| `src/murineshiftwork/tasks/sequence/task_objects.py` | Replace `_update_level` block |
| `src/murineshiftwork/tasks/probabilistic_switching/task.py` | Replace EMA block |
| `docs/concepts/adaptive_controller.md` | **NEW** |
| `docs/tasks/sequence.md` | Minor note |
| `docs/tasks/probabilistic_switching.md` | Minor note |

---

## Open questions

1. **`prepare()` return value** — should level-based tasks return `{"level": N}` from
   `prepare()`, or is it simpler to let `TaskControl` read `self.current_level` directly
   and have `prepare()` always return `{}`? The latter is less general but avoids a merge
   step. Decide before Phase 2.

2. **`outcome` dict shape** — `observe()` currently receives the full `info` dict written
   per trial. This is convenient but creates a dependency on the output schema. An
   alternative is a narrow `TrialOutcome` dataclass (just `is_correct`, `trial_index`,
   `level`). Decide before Phase 1 test design.

3. **Session-start floor** — `ThresholdLevelController` needs `session_start_level` to
   enforce the regression floor. Either pass it at construction time, or add a
   `set_session_start(level)` method called from `TaskControl.__init__`. Second option is
   cleaner if the controller is ever reused across sessions.

4. **Multi-metric buffer** — `sequence` tracks two buffers (`perf_buffer` for selected
   metric, `perf_buffer_perfect` for exact-match). The controller should own both or just
   the driving one? Owning both keeps buffer clear logic atomic.
