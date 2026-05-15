# TTL Barcode Integration

## Status (updated 2026-05-04)
**Core pipeline fully verified on hardware.** All test sessions (20 trials each) show:
- 20/20 barcodes decoded by all 4 RPIs (100% decode + match rate)
- 20/20 barcodes decoded by ephys (Open Ephys, NI BNC-2110)
- Ephys alignment residuals: mean=0.01ms, max=0.02ms — effectively exact
- RPI wall-time errors: mean 4.8–6.7ms, std 0.7–1.3ms (NTP + pigpio latency floor)
- Ephys clock drift: slope ≈ 1.00010593 (0.01%, normal crystal drift)

Two encoder/decoder bugs fixed during testing (see Known Issues #7, #8 below).
Next step: integrate barcode into `probabilistic_switching_fixedsubjects` (Step 2 below).

Previous design (barcode on BNC2 at tail of ITI) is replaced — BNC2 is reserved for
PulsePal. Barcode now on BNC1 at start of ITI.

## What was built

### ttl_barcoder (standalone package at ttl_barcoder/)
- `BarcodeTTL.get_sequence()` → list of (level, duration_ms) tuples
- `BarcodeTTL.decode_edges(edge_timestamps, edge_levels)` → (time, value) or None
- `BarcodeConfig`: 37-bit timestamp, 35ms bits, 10ms init = ~1355ms total
- `TTLType.timestamp`: barcode value encodes Unix time → self-describing, no order matching needed

### murine_shift_work/logic/barcode.py
- `BARCODE_FIRST_STATE_NAME = "barcode_start"` — canonical state name, alignment key in df
- `prepare_barcode(barcoder)` → (barcode_value, wall_time, timing_sequence)
  - wall_time captured BEFORE generate() so it matches the encoded timestamp
- `inject_barcode_states(sma, timing_sequence, bnc_channel, ...)` — MSW list-of-tuples format
- `barcode_config_from_settings(settings)` — build BarcodeConfig from settings dict

### Test protocols
- `tasks/_test_barcode_iti/` — barcode at ITI start, no video
- `tasks/_test_barcode_iti_with_video/` — barcode at ITI start + rpi_camera_ensemble conductor

Both task protocols (every trial, including trial 0):
- barcode_start → [barcode segments] → iti_post_barcode → ttl_on → ttl_off → wait → exit
- Single channel: HARDWARE_BNC_CHANNEL=1 (BNC1) carries both barcode and trial-onset pulse
- BNC2 reserved for PulsePal exclusively
- No special identifier trial 0 — barcodes are self-identifying (timestamp encoded in value)
- Info dict saved per trial: barcode_value, barcode_wall_time, iti_total_s, iti_post_barcode_s
- Incremental save to .df.pkl after every trial
- Barcode decoder segments on >500ms gaps: trial-onset pulse (~10ms after ≥50ms gap) is unambiguous

Alignment note: use --line 1 (BNC1) when running test_ephys_barcode_alignment.py

### murine_shift_work/readers/alignment.py
Key functions:
- `decode_ephys_barcodes(ephys_events_df, barcode_bnc_line, timestamp_column, barcode_config)`
  - ephys_events_df from open-ephys-python-tools: columns line, state, timestamps
  - timestamp_column: "timestamps" or "corrected_timestamps" (use corrected if processor alignment run)
  - segments edge stream on >500ms gaps, decodes each with BarcodeDecoder
  - returns list of (ephys_time, barcode_value)
- `align_session_to_ephys(session_dir, ephys_events_df, barcode_bnc_line, timestamp_column)`
  - loads MSW session, matches barcodes by value, linear fit, adds columns to df
  - returns (df, result) where result["bpod_to_ephys"] is the conversion callable
  - df gets: trial_start_ephys, barcode_ephys_time, alignment_slope, alignment_intercept
- `decode_rpi_ttl_in(ttl_in_npz, barcode_config)`
  - loads rpi agent's ttl_in.npz (timestamp + data arrays), decodes barcodes
  - returns list of (unix_time, barcode_value)
- `verify_rpi_barcode_decoding(session_dir, ttl_in_npz, barcode_config)`
  - compares rpi decoded barcodes vs MSW barcode_value column
  - reports decode_rate, match_rate, wall_time_errors_ms

## Known issues / things to verify
1. **output_actions format**: inject_barcode_states uses [(channel, 1/0)] list-of-tuples
   (not BpodBarcodeSender's dict format). Should work but confirm with pybpodapi.
2. **BNC channel naming**: uses eval("Bpod.OutputChannels.BNC1") — verify this resolves
   correctly on the actual Bpod hardware and that the string matches pybpodapi enum.
3. **rpi TTL-in pin wiring**: the rpi camera ensemble config yaml must have in_pin set
   for the GPIO pin wired to Bpod BNC1. Without this, ttl_in.npz will be empty/zero events.
   BNC1 now carries both barcode and trial-onset — RCE records all edges on this pin.
4. **barcode_value in df**: after read_trial_df, barcode_value comes from the expanded info
   dict. All trials are barcode trials now. Cast to int: df["barcode_value"].astype(int)
5. **Trial-onset pulse decodability**: the trial-onset pulse (~10ms) appears on BNC1 alongside
   barcode edges. The barcode decoder uses >500ms gaps to segment barcodes, so the isolated
   trial-onset pulse is never mistaken for a barcode bit. Verify this in the decoded output.
6. **PulsePal shutdown bug (FIXED)**: all optotagging tasks now call stimulation.disconnect()
   in a try/finally block. Previously stimulation was not explicitly disconnected on exit.
7. **iti_post_barcode BNC hold bug (FIXED 2026-05-06)**: `iti_post_barcode` had
   `output_actions=[]`, so Bpod holds BNC at the last barcode bit's level. When the last
   bit=1 (HIGH), BNC stays HIGH through all of `iti_post_barcode`, then the SMA exits and
   Bpod resets BNC to LOW — producing a HIGH→LOW edge at SMA-exit time, only ~300ms before
   the session-end (or next-trial) barcode's first edge. 300ms < 500ms segmentation threshold
   → decoder merges the SMA-exit edge with the following barcode → decode fails ~50% of
   sessions (whenever last barcode bit of preceding trial happens to be 1).
   Fix: `output_actions=[(bnc_channel, 0)]` in `iti_post_barcode`. This drives BNC LOW at
   the START of `iti_post_barcode` (creating any HIGH→LOW edge there, >> 500ms before next
   SMA), so SMA exit produces no new edge and the gap to the next barcode is always clean.
   Observed as unmatched session-end barcode (value `128711851193`, recovered timestamp
   ≈ 212s after session start in 209.4s session) on first real-task test, identical across
   all 4 RPIs (confirming hardware never received the barcode cleanly, not a decode error).
   Camera lifecycle is NOT the cause — cameras stop after `Task.run()` returns via QThread,
   which is after session-end SMA completes and data is saved to MSW.
8. **Encoder init bug (FIXED 2026-05-04)**: The start init was LOW-HIGH-LOW but BNC idles at
   LOW between trials. The first LOW segment produced no edge, leaving only 1 detectable init
   gap (between edges at t=10ms and t=20ms). Init validation requires ≥2 gaps in [7.5,12.5ms].
   For barcodes where bit[0]=0 (LSB=0, ~50% of values), no data edge appears at t=30ms either,
   so only 1 init gap → validation fails → barcode not decoded. Confirmed on hardware: exactly
   the even-valued barcode values failed, all RPIs failed the same ones.
   Fix: changed start init to HIGH-LOW-HIGH in encoder.py. BNC goes HIGH at t=0 (edge),
   LOW at t=10ms (edge), HIGH at t=20ms (edge) → first 2 inter-edge gaps always 10ms → passes.
8. **Alignment uses trial-relative times (FIXED 2026-05-04)**: align_session_to_ephys was
   extracting barcode_start state timestamps which are trial-relative (≈0.001s for all trials
   since barcode_start is the first state). All bpod_anchors ≈ 0 → polyfit divide-by-zero →
   "SVD did not converge". Fix: add df["Trial start timestamp"] to get session-absolute times.

## Test scripts
- `tests/test_rce_barcode_alignment.py` — RCE ttl_in.npz vs MSW session
- `tests/test_ephys_barcode_alignment.py` — OE record node vs MSW session
- `tests/plot_ephys_line_jitter.py` — plot IPI distributions for ephys digital lines;
  default lines 3–6 receive RPI camera encoder frame TTL; shows per-line Hz, mean/median/std;
  reference lines at 30/60/100Hz; normalized density y-axis (peak=1 per line)

```bash
# After _test_barcode_iti_with_video session:
python tests/test_rce_barcode_alignment.py --session /data/subject/session_dir

# After ephys recording:
# --line is the OE digital input line number (rig wiring dependent, NOT Bpod BNC number)
# BNC2 was line 8. BNC1 maps to a different line — check rig ephys wiring docs.
# Run without --line first to see available lines: script prints them at startup.
python tests/test_ephys_barcode_alignment.py \
    --session /data/subject/session_dir \
    --oe_dir  /data/ephys/Record\ Node\ 101 \
    --line    N \
    --ts_col  corrected_timestamps

# Without global alignment processor (use raw timestamps):
python tests/test_ephys_barcode_alignment.py \
    --session /data/subject/session_dir \
    --oe_dir  /data/ephys/Record\ Node\ 101 \
    --line    N \
    --ts_col  timestamps
```

## Ephys events df format (open-ephys-python-tools)
```python
from open_ephys.analysis import Session
session = Session('/path/to/Record Node NNN')
recording = session.recordnodes[0].recordings[0]
events = recording.events
# columns: line (int), state (1=rising/0=falling), timestamps (seconds),
#          optionally corrected_timestamps if global alignment processor was run
```
Line numbers in the events df are OE digital input channel numbers — determined by physical
wiring from Bpod BNC outputs to the ephys acquisition system. These are NOT the same as Bpod
BNC channel numbers. Check rig wiring documentation to find which OE line each Bpod BNC maps to.
The test script prints all available lines at startup ("Available lines in OE events: [...]") —
use this to identify the correct line. Previously line=8 was used for Bpod BNC2 on one rig.
The "corrected_timestamps" column appears when the Record Node has a Timestamps Synchronizer
processor upstream. Use this column for alignment — it's in the global ephys clock.

## Alignment pipeline summary

### probabilistic_switching_fixedsubjects
```
Session-start barcode (trial 0) + per-trial ITI barcode + session-end barcode
    Trial structure: ttl_on → ttl_off → center_ready → ... → final → barcode_start →
                     [barcode segs] → iti_post_barcode → exit
    barcode fires at ITI start (end of each task trial), after stage moves back
    ITI = [3, 5, 0.5]s; barcode ~1355ms; iti_post_barcode = max(0.05, ITI - 1.355)s

    barcode_value matched by value in ephys decode (N anchors, one per trial)
    bpod_anchor = barcode_rows["Trial start timestamp"] + barcode_start state offset
    ephys_anchor = OE events first edge of matched barcode
        ↓ linear fit across all N trial barcodes
bpod_to_ephys(t) = slope * t + intercept
df["trial_start_ephys"] = bpod_to_ephys(df["Trial start timestamp"])
```

### sequence_automated
```
Session-start + session-end barcodes → session identity only
    (same match logic as above, but used for identification not per-trial alignment)

Per-trial long TTL pulse on BNC1:
    rising edge  in OE events  ↔  trial start    (entering wait_poke_0)
    falling edge in OE events  ↔  ITI start      (entering exit_seq)
    → piecewise per-trial, no global regression needed
    → bpod data provides outcome/level/sequence; ephys edges provide timestamps
    → for correct trials: falling edge ≈ last port reward delivery start
    → for incorrect trials: falling edge = end of punish period
```

## Session namespace (updated 2026-05-04)

`MSW_DATETIME_FORMAT = "%Y%m%d_%H%M%S_%f"` — defined once in `logic/paths.py`, imported by
`logic/log.py` and `remote_ephys/controller.py`. Format: `20260504_143022_123456` (microseconds).
Previous format `%Y%m%d_%H%M%S` had 1-second collision window; new format is collision-proof.
Session basenames: `{subject}__{datetime}__{task}` (3 `__`-delimited fields, unchanged structure).

## Task integration status

### Step 1: Test protocols — DONE (2026-05-04)
Confirmed on `_test_subject__20260504_120312___test_barcode_iti_with_video`:
- 4 RPIs: 20/20 decode/match, wall-time error mean 4.8–6.7ms
- Ephys: 20/20 decode/match, alignment residuals mean=0.01ms max=0.02ms

### Step 2: probabilistic_switching_fixedsubjects — DONE (2026-05-05)
Session-start barcode (trial 0) + per-trial ITI barcode + session-end barcode.
- Session-start/end: standalone barcode SMA in the task runner (same as before)
- Per-trial: barcode injected at ITI start inside `make_state_machine()` in task_objects
  - `final` → `barcode_start` → [segs] → `iti_post_barcode` → `exit`
  - `prepare_barcode()` called in `make_state_machine()`; value/wall_time stored as
    `_pending_barcode_value` / `_pending_barcode_wall_time`, copied into trial info by `update()`
- `barcode_value`, `barcode_wall_time` in `info` for BOTH barcode-type and task-type trials
- BNC1 (`HARDWARE_BNC_TRIAL_START=1`): barcode at start/ITI/end + short trial-onset pulse per trial
- ITI changed to `[3, 5, 0.5]`s; `iti_post_barcode = max(0.05, ITI - barcode_duration_s)`
- Alignment: N barcodes (one per trial + bookends) → N-anchor linear fit
- task.settings: `barcode_bits=37, barcode_bit_duration_ms=35.0, barcode_init_duration_ms=10.0`

### Step 2b: sequence_automated — DONE (2026-05-04)
Same session-start + session-end barcode structure as switching_fixed.
**TTL scheme:** long pulse per trial (replaces short `add_trial_onset_ttl` pulse):
- BNC HIGH entering `wait_poke_0` (first poke state, trial start)
- BNC stays HIGH through all intermediate wait/reward/punish states (Bpod holds output)
- BNC LOW entering `exit_seq` (ITI start)
- Rising edge = trial start, falling edge = sequence end or punish done
- Piecewise alignment: each trial's rising/falling edges in OE events are the direct ephys
  timestamps; no global clock correction needed for trial-level analysis

### Step 3: optotagging variants + airpuff — DONE (2026-05-14)

**optotagging / optotagging_with_video / optotagging_multi_with_video / optotagging_with_power_level:**
- Session-start barcode (trial 0) + session-end barcode (after loop) on BNC1
- `TRIGGER_ITI=1s` is shorter than barcode duration (~1.355s) → per-ITI barcodes not possible;
  session-start/end bookends give session identity and a 2-anchor alignment baseline
- `make_ttl_identifier_sequences` replaced — trial 0 SMA is now a standalone barcode SMA
- `barcode_value`, `barcode_wall_time` added to all trial info dicts (None for task trials)
- `trial_type` field updated: `"barcode"` for trial 0 and session-end, `"task"` for opto trials
- Session-end barcode in `try/except` inside the `try/finally` (stimulation disconnects in finally)
- task.settings: added `barcode_bits=37, barcode_bit_duration_ms=35.0, barcode_init_duration_ms=10.0`
  (TTL_IDENTIFIER_SEQUENCE removed — no longer used)

**airpuff:**
- Session-start barcode (trial 0) + per-ITI barcode in every task trial + session-end barcode
- Trial structure: `trial_onset_ttl` → `release_puff` → `barcode_start` → [segs] → `iti_post_barcode` → `exit`
- `iti_post_barcode = max(0.05, iti_this_trial - barcode_duration_s)`
- `output_actions=[(bnc_channel, 0)]` on `iti_post_barcode` (BNC hold bug fix — same as prob_switching)
- ITI [4, 6, 0.5]s → `iti_post_barcode` = 2.65–4.65s; barcode fits cleanly
- `barcode_value`, `barcode_wall_time` in all trial info dicts
- task.settings: added barcode config; TTL_IDENTIFIER_SEQUENCE removed
