# MSW Refactor Status

Last updated: 2026-05-04 (session 2)

Overview of all active upgrade/refactor workstreams and their current state.

---

## 1. File format — pickle → JSONL  DONE

**Motivation:** `pd.DataFrame.to_pickle` is not version-stable across pandas 2.x → 3.x.
Analysis machines (pandas 2.x) could not read files written on acquisition machines (pandas 3.x).

**What changed:**
- New module `murine_shift_work/io/trial_data.py` — `save_trial_data` / `load_trial_data`
- Format: newline-delimited JSON (JSONL), one trial dict per line, first line is version header `{"_msw_version": "1.0.0"}`
- `_NumpyEncoder` handles numpy arrays/scalars transparently
- All 13 save sites in all tasks converted from `.df.pkl` → `.df.jsonl`
- Reader (`murine_shift_work/readers/files.py`) dispatches on extension: `.jsonl` → JSONL loader, `.pkl` → legacy pickle
- Session reader (`readers/session.py`) handles both formats; legacy `.pkl` and legacy `task_settings.py` sessions still fully readable
- `msw_version` hoisted to top level of `session_data` from process settings JSON

**Version:** MSW package bumped to 1.0.0 (from 0.2.2). Version string kept in lockstep
across `setup.cfg`, `murine_shift_work/__init__.py`, and `io/trial_data.py` via `.bumpversion.cfg`.

**Pending:**
- Reader unification test: verify that legacy (`.pkl`) and new (`.jsonl`) sessions present
  identical computational interface after `read_session_data()`. User will provide example sessions.

---

## 2. TTL barcode synchronisation pipeline  DONE (hardware-verified)

**Motivation:** Multi-modal sessions (Bpod + ephys + RPi cameras) need a common time reference
that doesn't rely on NTP or manual alignment. TTL barcode = Unix timestamp encoded as a
37-bit pulse train on Bpod BNC1 at the start of each trial's ITI.

**Architecture:**
- `ttl_barcoder/` — standalone package: encoder, decoder, config, timestamp recovery
- `murine_shift_work/logic/barcode.py` — MSW integration: prepare, inject into state machine
- `murine_shift_work/readers/alignment.py` — offline alignment: ephys and RPI decoders, linear fit

**Bugs fixed during hardware testing:**
1. **Encoder init polarity** (2026-05-04): init sequence was LOW-HIGH-LOW; BNC idles LOW between
   trials → first LOW produces no edge → only 1 init gap detectable → ~50% of barcodes fail
   (those with bit[0]=0, i.e. even Unix-ms timestamps). Fixed: init now HIGH-LOW-HIGH.
2. **Decoder init threshold** (2026-05-04): validation required ≥2 init gaps; backward-compatible
   fix to ≥1 so sessions recorded before encoder fix still decode correctly.
3. **Alignment used trial-relative times** (2026-05-04): `barcode_start` state timestamps are
   trial-relative (≈0.001s for every trial since it's the first state); polyfit input had zero
   variance → SVD error. Fixed: add `df["Trial start timestamp"]` for session-absolute times.

**Verified results (session 20260504):**
- 4 RPIs: 20/20 decode, 20/20 match, wall-time error mean 4.8–6.7ms (NTP floor), std 0.7–1.3ms
- Ephys (OE + NI BNC-2110): 20/20 decode, 20/20 match, alignment residuals mean=0.01ms max=0.02ms
- Ephys clock drift slope ≈ 1.00010593 (0.01% — normal crystal drift)

**RPI timing precision note:** ~5–7ms systematic offset per RPI (NTP discipline), ~1ms jitter
(pigpio). This is the floor for NTP-synced RPIs without hardware timestamping (PPS). Acceptable
for camera frame alignment to Bpod/ephys at ~10ms absolute accuracy.

**Step 2 — probabilistic_switching_fixedsubjects: DONE (2026-05-04 session 2)**
- Session-start barcode (trial 0) + session-end barcode (fires on normal end and Ctrl+C)
- `barcode_value` + `barcode_wall_time` stored in trial df, `trial_type: "barcode"`
- Both task runner + task_objects updated; old `make_ttl_identifier_sequences` removed
- task.settings updated with `barcode_bits/bit_duration_ms/init_duration_ms`

**Step 2b — sequence_automated: DONE (2026-05-04 session 2)**
- Same start/end barcode structure as switching_fixed
- Long TTL pulse per trial: BNC HIGH at `wait_poke_0`, LOW at `exit_seq` (ITI)
- Rising = trial start, falling = sequence/punish end → piecewise ephys alignment per trial

**Next steps:**
- Step 3: extend to optotagging variants, airpuff (after step 2 confirmed on real subjects)
- Long-term: consider PPS-based hardware timestamping on RPIs for sub-ms absolute accuracy

**Docs:** `docs/barcode_ttl_integration.md`

---

## 3. Ephys camera TTL jitter visualisation  DONE

- `tests/plot_ephys_line_jitter.py` — plots IPI distributions for OE digital lines
- Default lines 3–6 = RPI camera encoder frame TTL outputs
- Shows: per-line Hz, mean/median/std, normalised density (peak=1), reference lines at 30/60/100Hz
- Usage: `python tests/plot_ephys_line_jitter.py --oe_dir /path/to/Record\ Node\ 101`

---

## 4. CLI redesign  DESIGN COMPLETE, NOT IMPLEMENTED

**Spec:** `docs/cli_redesign_spec.md`

Current problem: hardware addresses scattered across CLI flags, `~/.murineshiftwork/` files,
and hardcoded Python dicts. No pre-run hardware check. Subject settings in monolithic INI.

Planned architecture:
- `configs/` directory (version-controlled separately): `setups/*.yaml`, `subjects/*.yaml`, `cameras/*.yaml`
- `SetupConfig` Pydantic model: devices, calibrations, camera ensemble ref
- `SubjectConfig` Pydantic model: per-subject task overrides
- `port_by_path` → resolved `/dev/ttyXXX` at pre-run check time
- Hardware availability check before any files are written

Migration trajectory (v0 → v4):

| Version | Key change | Status |
|---------|------------|--------|
| v0 | Current: INI, flat CLI, `~/.murineshiftwork/` | **current** |
| v1 | `--config-dir` + `--setup`; SetupConfig; port resolution; old flags kept with warning | not started |
| v2 | Per-subject YAML; `msw register` | not started |
| v3 | Remove INI fallback; `msw calibrate` CLI | not started |
| v4 | Namespace logic; per-task Pydantic settings schema | not started |

---

## 5. Subject name path validation  DONE

`murine_shift_work/logic/paths.py` raises `ValueError` on forbidden characters in subject name
(`#@!$%^&*()+=[]{}...` etc.). Motivated by `#` being entered accidentally and accepted.

---

## 6. PyQt6 declared as dependency  DONE

Added to `setup.cfg` `install_requires`. Previously caused `ModuleNotFoundError` on fresh installs.

---

## 7. Open Ephys remote acquisition package  IN PROGRESS

`msw_open_ephys/open_ephys_remote/` — CLI for remote control of Open Ephys (start/stop recording,
set save path, etc.) from the acquisition machine. Scaffolding committed, integration not complete.

---

## 8. Pending / deferred

- **`collate_data2.sh`**: remove `--exclude='tests'`, investigate RPI data save path issue
- **`msw register` / CLI v1**: first step of CLI redesign — no timeline set
- **Barcode in `probabilistic_switching_fixedsubjects` + `sequence_automated`**: DONE (see section 2)
- **Alignment script for `sequence_automated`**: piecewise per-trial using long-pulse TTL edges —
  script not yet written; design documented in `barcode_ttl_integration.md`
- **Reader unification test**: verify legacy vs new session data interface is identical
