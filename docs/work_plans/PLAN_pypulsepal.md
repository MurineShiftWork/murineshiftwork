# pypulsepal — work plan

Repo: `github.com/larsrollik/pypulsepal`
Working copy: `/mnt/maindata/code/murineshiftwork/external/pypulsepal`

Last updated: 2026-05-23

---

## Released — v0.2.0 (merged ft/pydantic-config, 2026-05-23)

- `src/pypulsepal/models.py` — Pydantic v2 models: `ChannelConfig` (17 fields, validate_assignment), `TriggerConfig`, `PulsePalConfig`
- `src/pypulsepal/pulsepal.py`:
  - `config` property, `from_config()` classmethod, `reset_to_defaults()`
  - `load_config(path)` / `save_config(path)` (lazy import from config_io)
  - `save_to_sd()` / `read_sd_params()` as class methods (opcode 90/op1, 85)
  - `_pulsepal_set_display()` fixed; shows "PyPulsePal" on LCD at connect
  - `save_settings()` fixed: no `_read_confirmation()` (no ack on model 2 fw21)
  - `__del__` fixed: contextlib.suppress around disconnect
- `src/pypulsepal/config_io.py` — `load_config` / `save_config` for JSON and YAML
- `src/pypulsepal/_arcom.py` — ArCOM vendored from pybpod-api 1.8.2 (MIT); pybpod-api dropped as dependency
- `src/pypulsepal/definitions.py` — added `READ_SD = 85` to `SendMessageHeader`
- Build system: hatchling + hatch-vcs, src/ layout, commitizen, ruff, mypy, pre-commit, gitleaks CI
- Tests: `test_models.py`, `test_encoding.py`, `test_pulsepal.py`, `test_config_io.py` — 95 tests, all passing
- Scripts: `scripts/test_connection.py`, `scripts/test_ack_behaviour.py`, `scripts/write_tests.py`
- `CITATION.cff` added; `README.md` updated

### Opcode ack behaviour — verified on model 2, firmware 21, 2026-05-23

| Opcode | Command | Ack? |
|---|---|---|
| 72 | handshake | yes (char + uint32) |
| 73 | `sync_all_params` | yes (uint8 = 1) |
| 74 | `program_one_param` | yes |
| 77 | trigger | no |
| 79 | `set_fixed_voltage` | yes |
| 80 | `stop_all_outputs` | no |
| 81 | `save_settings` / disconnect | no |
| 82 | `set_continuous` | yes (uint8 = 1) — Sanworks API skips ack but hardware sends one |
| 85 | read SD card | streams 178 bytes, no prior ack |
| 90 op1 | `save_to_sd` | no |
| 90 op2 | load SD → RAM | not tested |

---

## In progress — ft/patch-cleanup

- [x] Hoist `v2b` lambda out of model-1 loop in `sync_all_params` → named function before loop
- [x] Verified `interBurstInterval` naming matches definitions opcode index 9 — no change needed
- [ ] CITATION.cff: update concept DOI once Zenodo webhook is confirmed active (see below)

---

## Pending

### CITATION.cff — concept DOI

Current DOI (`10.5281/zenodo.6379627`) is from the old 0.0.2.dev0 record (2022).
Zenodo has not yet archived v0.2.0 — the webhook may not have been enabled.

Steps:
1. Go to zenodo.org/account/settings/github — confirm toggle is ON for larsrollik/pypulsepal
2. After next release merges and Zenodo archives it, check the record for the concept DOI
3. Update `CITATION.cff` `identifiers.value` and `preferred-citation.doi` + `url`

### Issue #9 — offline / dry-run mode

Mocked serial tests (`patch("pypulsepal.pulsepal.ArCOM")`) already demonstrate offline operation.
A formal `dry_run=True` kwarg on `PulsePal.__init__` would surface this for users.
Not urgent — leave open until there is a concrete use case.

### Priority 5 remnants (low priority)

- `interBurstInterval` naming: verified correct ✅
- `v2b` lambda in model-1 loop: fixed in ft/patch-cleanup ✅
- `PulsePalConfig` channel count: currently hardcodes 4 channels / 2 triggers. Could parameterise via `nr_output_channels` / `nr_trigger_channels` — not urgent.
- opcode 90 op2 (load SD → RAM): not tested on hardware.

### Key firmware notes

SD file layout (178 bytes, opcode 85):
- Per output channel ×4 (42 bytes each): 8× uint32 time params + uint8 isBiphasic + 3× uint16 voltages + 3× uint8 train params
- Per trigger channel ×2 (5 bytes each): uint8 triggerMode + 4× uint8 triggerAddress
- Byte 179 is a validation byte — NOT streamed by opcode 85

No opcode reads current RAM parameters directly. Read-back flow:
`sync_all_params` → `save_to_sd()` → `read_sd_params()` → compare.
