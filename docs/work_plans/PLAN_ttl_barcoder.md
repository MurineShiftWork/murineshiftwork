# ttl-barcoder — PyPI Release Plan

Working copy: `external/ttl_barcoder/` (own git repo)
Public target: `https://github.com/larsrollik/ttl-barcoder`
PyPI target: `ttl-barcoder`

Last updated: 2026-05-23

---

## Package overview

`ttl-barcoder` encodes Unix timestamps or random values as binary TTL pulse sequences for
synchronising multiple DAQ systems (Bpod, Raspberry Pi GPIO, Open Ephys). Hardware-verified
in MSW: 100% decode rate across 4 RPIs + Open Ephys, alignment residuals < 0.1 ms.

```
ttl_barcoder/
├── core/
│   ├── config.py        # BarcodeConfig (Pydantic v2), TTLType, TimestampPrecision, presets
│   ├── generator.py     # TTLGenerator ABC → TimestampGenerator / RandomGenerator
│   ├── encoder.py       # bits → (level, duration_ms) timing sequence
│   ├── decoder.py       # edge timestamps → barcode value
│   └── barcode_ttl.py   # BarcodeTTL — main interface (prepare / get_sequence / decode_edges)
└── hardware/
    ├── bpod/            # inject_barcode_states(), BpodBarcodeSender
    └── pigpio/          # PigpioBarcodeSender, PigpioConnection, send_barcode_sequence
```

---

## Status at review (2026-05-23)

### What is done
- Core encode/decode pipeline: hardware-verified (100% decode, < 0.1 ms residuals)
- Bpod state-machine injection: hardware-verified in MSW tasks
- BarcodeConfig: Pydantic v2, full validation, 4 presets
- Encoder HIGH-LOW-HIGH init fix: prevents decode failures for ~50% of barcodes at BNC idle-LOW
- Decoder init tolerance fix: robust to 1 vs 2 detectable init gaps
- BpodBarcodeSender: correct list-of-tuples output_actions format
- README with quickstart, install, config table, architecture diagram, examples

### Uncommitted changes (must commit first)
Six modified files are hardware-verified but not yet committed:
- `examples/dry_simulation.py`
- `ttl_barcoder/core/barcode_ttl.py`
- `ttl_barcoder/core/decoder.py`
- `ttl_barcoder/core/encoder.py`
- `ttl_barcoder/hardware/bpod/__init__.py`
- `ttl_barcoder/hardware/bpod/sender.py`

---

## Gaps blocking PyPI release

| # | Gap | Severity |
|---|---|---|
| 1 | Uncommitted bug fixes (6 files) | Blocker |
| 2 | No tests (`tests/` absent) | Blocker |
| 3 | No CI/CD (no `.github/workflows/`) | Blocker |
| 4 | No LICENSE file | Blocker |
| 5 | Build system: legacy setuptools + bumpversion; not standard | Blocker |
| 6 | `pyproject.toml` `pytest.addopts` references wrong package (`rpi_camera_ensemble`) | Bug |
| 7 | `pyproject.toml` `[tool.ruff] include = ["*.pyi"]` — only lints stubs | Bug |
| 8 | `.bumpversion.cfg` at `0.0.0.dev0`, references `templatepy/` | Stale |
| 9 | `pigpio/__init__.py` missing re-export of `send_barcode_sequence` (used in README) | API bug |
| 10 | `examples/bpod_loopback.py` imports `add_barcode_sma_states` (doesn't exist) | Example bug |
| 11 | `dev` extras missing `ruff`, `mypy` | Minor |

---

## Sprint 1 — Build system upgrade ✅ DONE (2026-05-23)

Completed in session on `ft/opto-hardware`. All changes are unstaged in `external/ttl_barcoder`.
Commit when ready: `build: migrate to hatchling+vcs, src/ layout, standard toolchain`.

### What was done

- **src/ layout migration** — `git mv ttl_barcoder src/ttl_barcoder/` (org standard)
- **`pyproject.toml` rewritten** — hatchling + hatch-vcs, `dynamic = ["version"]`, commitizen,
  `requires-python = ">=3.10"`, standard ruff/mypy/pytest config, correct `packages = ["src/ttl_barcoder"]`
- **`VERSION`** — added (`0.3.0`)
- **`.pre-commit-config.yaml`** — replaced with full standard set: pre-commit-hooks, ruff v0.9.0,
  mypy v1.14.0 + `pydantic>=2.0`, commitizen v4.1.0 (commit-msg), gitleaks v8.24.3
- **`.github/workflows/CI.yaml`** — lint + test + secrets-scan + gate
- **`.github/workflows/release.yml`** — hatchling build + GitHub release + PyPI trusted publish
- **`LICENSE`** — BSD 3-Clause, copyright Lars B. Rollik
- **`setup.py`, `.bumpversion.cfg`** — deleted
- **`hardware/pigpio/__init__.py`** — `send_barcode_sequence` added to exports (was missing; used in README)
- **`examples/bpod_loopback.py`** — `add_barcode_sma_states` → `inject_barcode_states`; `output_channel` → `bnc_channel`

### Still needed before committing

1. Commit the 6 previously uncommitted hardware-verified bug fixes (encoder init, decoder tolerance, bpod sender)
2. Run `pre-commit install` in `external/ttl_barcoder`
3. Run `pre-commit run --all-files` — fix any trailing whitespace / import ordering the hooks catch
4. Tag `v0.3.0` once tests exist and the repo is public

---

## Sprint 2 — Tests

Write `tests/` directory. No hardware required for any of these.

| File | Tests |
|---|---|
| `test_config.py` | `BarcodeConfig` validation (invalid bits/tolerance), preset lookup, `get_preset` raises on unknown name, `total_duration_ms` formula, `coverage_years` for timestamp/random |
| `test_generator.py` | `TimestampGenerator` quantisation at s/ms/us precision, `RandomGenerator` bounds, `encode_bits` LSB-first order, `recover_timestamp` wraparound |
| `test_encoder.py` | Sequence length = `6 + barcode_bits`, init segment levels (HIGH-LOW-HIGH start, LOW-HIGH-LOW end), `get_total_duration` matches segment sum |
| `test_decoder.py` | Perfect-edge roundtrip for known values 0/1/99999, decode returns None for short input (<6 edges), decode returns None for bad init timing |
| `test_barcode_ttl.py` | `prepare()` tuple structure, `get_sequence(N)` deterministic, `decode_edges` roundtrip with default config, `get_sequence_from_timestamp` raises on random config |
| `test_bpod.py` | `inject_barcode_states` with minimal mock SMA: state count = sequence length, first state name matches arg, last state transitions to last_state_name arg, output_actions list-of-tuples format |

Add CI test job once `tests/` exists.

---

## Sprint 3 — Public release

1. Create public GitHub repo `larsrollik/ttl-barcoder`
2. Configure PyPI Trusted Publisher (project `ttl-barcoder`, workflow `release.yml`, no token secret needed)
3. Add PyPI publish step to `release.yml` (`pypa/gh-action-pypi-publish@release/v1`)
4. Fill in `pyproject.toml` `#Documentation =` URL
5. Push all commits → tag `v0.3.0` → CI → release workflow → PyPI publish

---

## Key firmware / hardware facts (for tests and docs)

- Default config: 37-bit timestamp, 35 ms bits, 10 ms init → 1355 ms total
- Encoder: 6 init segments (3 start + 3 end) + barcode_bits data segments
- Init pattern: HIGH-LOW-HIGH (start), LOW-HIGH-LOW (end)
- BNC idles LOW between trials → start must be HIGH to guarantee first edge
- Decoder uses >500 ms gaps to segment barcodes from trial-onset pulses
- Alignment residuals on hardware: mean 0.01 ms, max 0.02 ms (effectively exact)

---

## MSW integration (reference only — already done)

MSW uses `ttl_barcoder` via `murine_shift_work/logic/barcode.py` (thin delegation layer).
`BARCODE_FIRST_STATE_NAME = "barcode_start"` is the canonical alignment key in session DataFrames.
Integration status: all tasks verified (`docs/barcode_ttl_integration.md`).
