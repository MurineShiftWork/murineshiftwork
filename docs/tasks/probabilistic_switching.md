# Probabilistic Switching Task (freely moving)

**Protocol name:** `probabilistic_switching`
**Setup:** Freely moving, 3-port Bpod panel (left / centre / right)
**Video:** Optional (RPi camera ensemble via `config_file_camera`)

---

## Behavioural paradigm

A two-armed bandit task in which the mouse must track which of two side ports (left or right) is currently "rich": i.e. delivers water on the majority of choices. Reward probabilities switch covertly in blocks; the mouse must detect the switch and update its choice behaviour accordingly.

This class of task is widely used to study flexible decision making, reversal learning, and the contributions of prefrontal cortex and basal ganglia to value-based choice under uncertainty. The block structure with probabilistic (rather than deterministic) feedback prevents simple win-stay/lose-shift strategies and requires integration over multiple trials.

---

## Block structure

Reward probabilities are assigned from the `probabilities` list in `task.yaml`. Each entry is a pair `[p_left, p_right]` (percentage, 0-100). Example defaults:

| Block type | p(reward | left) | p(reward | right) |
|---|---|---|
| Contrast high-left | 90% | 10% |
| Contrast high-right | 10% | 90% |
| Neutral | 50% | 50% |

Blocks are drawn without replacement (excluding the current block type unless `block_switch_to_different_block_type = false`). The first block is biased toward an easy contrast block (`first_block_easy = true`) to motivate the subject at session start.

### Block switching criterion

Blocks switch when **both** conditions are met:

1. **Minimum length**: at least `min_block_length` trials have elapsed in the current block
2. **Criterion**: the exponential moving average of choices (EMA, time-constant `criterion_tau` trials) exceeds the `criterion_contrast_blocks` threshold toward the rich side

After the criterion is first met, the block continues for at least `min_trials_post_criterion` additional trials before the switch is enacted, adding stochasticity to the switch point and preventing the animal from exploiting a perfectly predictable reversal timing.

Neutral blocks switch after a random number of trials drawn from a geometric distribution (mean `mean_neutral_block_length`, minimum `min_block_length`).

---

## Trial structure

```
centre-port init  →  side choice (left / right)
                            ↓ rewarded side
                        reward  →  ITI
                            ↓ non-rewarded side
                        no reward  →  ITI
                            ↓ timeout
                        timeout  →  ITI
```

- The mouse initiates each trial by poking the centre port
- After a short delay (`delay_until_center_init`) the side ports become active
- Choice window: `delay_until_side_timeout` seconds; timeout → no reward
- ITI: drawn from a uniform distribution (configurable)

---

## Performance tracking

An **exponential moving average** (EMA) of choices tracks the animal's bias toward left (`-1`) or right (`+1`) with time-constant `criterion_tau`. The EMA is used for:
- Block-switch criterion (see above)
- Online plot display
- Forced-choice anti-bias correction

### Forced-choice anti-bias

When the animal has made `forced_choice_threshold` consecutive choices to the same side, the next trial is a **forced-choice trial**: only one side port is active, directing the animal to the opposite side. This prevents strong side biases from dominating performance metrics.

---

## Key parameters

| Parameter | Default | Description |
|---|---|---|
| `probabilities` | `[[10,50],[50,10],[10,90],[90,10],[50,50],...]` | Block reward probability pairs (p_left, p_right in %) |
| `min_block_length` | 20 | Minimum trials before block switch |
| `min_trials_post_criterion` | 5 | Minimum extra trials after criterion before switch |
| `mean_neutral_block_length` | 25 | Mean length of neutral blocks |
| `criterion_contrast_blocks` | 0.75 | EMA threshold to trigger contrast block switch |
| `criterion_neutral_blocks` | 0.25 | EMA threshold (not used for switch; informational) |
| `criterion_tau` | 5 | EMA time-constant (trials) |
| `first_block_easy` | true | Start session with a high-contrast block |
| `block_switch_to_different_block_type` | true | Exclude current block type when drawing next |
| `reset_bias_on_block_switch` | false | Reset EMA to 0 at each block switch |
| `forced_choice_threshold` | 20 | Consecutive same-side choices before forced trial |
| `reward_amount_ul` | 2.0 µL | Water per rewarded choice |
| `n_max_trials` | 1500 | Hard trial limit |
| `delay_until_center_init` | [0.15, 0.2, 0.005] | Centre-port init delay (min, max, step; s) |
| `delay_until_side_timeout` | 10 s | Side-port choice window |

---

## Modes

| Mode | Description |
|---|---|
| (none defined) | All sessions use the same default block structure |

Site-specific probability sets (e.g. omitting neutral blocks) can be set via a config-dir overlay or `-ts` flags.

---

## Online plot

- Moving average of choices (left/right bias)
- Block probability trace (left / right)
- Per-trial outcome scatter (rewarded / unrewarded / stop-signal)
- Session trial count

---

## Running

```bash
msw run -t probabilistic_switching -s mouse001 --setup setup-1
# With camera video:
msw run -t probabilistic_switching -s mouse001 --setup setup-1 \
    -ts config_file_camera=/mnt/maindata/msw_configs/cameras/setup-1.yaml
```
