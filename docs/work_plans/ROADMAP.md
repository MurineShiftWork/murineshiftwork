# Roadmap

Revolving TODO list. Completed items move to DONE with `· date · short-hash`.
Design details live in memory files or separate docs — not here.

---

## TOP PRIORITY — blocking public release

- [x] **Security scrub `src/` files** — replace `172.24.42.168` with `10.0.10.111` in `parser.py`, `host_session.py`, `docs/cli/run.md`, `docs/setup/setup_config.md`; fix protonmail email in `.copier-answers.yml`, `CODE_OF_CONDUCT.md`, `BUILD_SYSTEM_STANDARD.md`, and all external repo `CODE_OF_CONDUCT.md` files. · 2026-06-10
- [ ] **Move docs + playground upstream** — `docs/`, `playground/` move to project-dir (outside repo) before public orphan branch push; `DHCP.md` and `PROVISION_RPI_SCRIPTS.md` must not appear in public history
- [ ] **Add mkdocstrings + API ref pages** — `murineshiftwork`, `acquisition-namespace`, `ttl-barcoder`, `pypulsepal` each need mkdocstrings plugin + `docs/api/` pages before polished docs site. Full gap list: `docs/work_plans/DOC_GAPS.md`
- [ ] **`rpi_camera_ensemble` docs** — README is a TODO stub; docs/ is 90% empty skeleton; full rewrite needed before public release
- [ ] **Namespace-repo separation sprint** — see `IMPLEMENTATION_PLAN.md` and `PLAN_package_graph.md`. First step: write `tests/test_task_discovery.py` covering `msw.tasks` entry-point path (mocked external package); then extract `msw-tasks-core`. Doc quality is a parallel track. Tests in each extracted package; cross-package integration tests stay in `murineshiftwork/tests/`.

---

## Manual (requires human action)

- [x] **GitHub + PyPI: merge and publish `msw-open-ephys`** — merged `ft/msw-host-plugin`; published 3.1.1 to PyPI; `oe = ["msw-open-ephys"]` restored; `test_host_session.py` runs fully (25 tests). · 2026-06-10
- [ ] **PyPI: publish deprecation stub** — `serial-weighing-scale 3.0.0` at `/mnt/maindata/code/serial_weighing_scale_stub/`
  ```
  cd /mnt/maindata/code/serial_weighing_scale_stub
  python -m build && twine upload dist/*
  ```
- [ ] **GitHub + PyPI: push `serial-scale-hx711`** — create repo under `MurineShiftWork` org, push `external/serial_scale_hx711`; publish to PyPI (OIDC trusted publishing); update `[calibration]` dep pin after release
- [ ] **GitHub + PyPI: push `serial-scale-bench`** — create repo under `MurineShiftWork` org, push `external/serial_scale_bench`; publish to PyPI; update `[calibration]` dep pin after release
- [ ] **PyPI: publish RCC deprecation stub** — `rpi-camera-colony` stub pointing users to `rpi-camera-ensemble`; same pattern as `serial-weighing-scale` stub
- [ ] **RCC: add import deprecation warning** — in `rpi_camera_colony/__init__.py` add `warnings.warn("rpi-camera-colony is deprecated; use rpi-camera-ensemble instead", DeprecationWarning, stacklevel=2)`; bump a patch release so the warning ships to anyone still pinned to the old package
- [x] **GitHub: create repo + PyPI release for `rpi-camera-ensemble`** — `MurineShiftWork/rpi-camera-ensemble` created and released to PyPI (0.4.3); publicly installable, coexists with FLIR/Bonsai backend. msw `[rce]` extra uses `rpi-camera-ensemble[conductor]`. · 2026-06-09
- [ ] **git repo for `msw_configs/`** — move `/mnt/maindata/msw_configs` into a dedicated git repo to get clean history of setup/subject/calibration changes; MSW reads config_dir as before, just backed by git

---

## TODO

### Task currency fixes (pre-repo-separation)

- [x] **`rpi_camera_colony` → `rpi_camera_ensemble`** — `periodic_trigger_with_video` and `_test_video` updated to new conductor API (`EnsembleAcquisitionConfig`, `ConductorConfig`, `conductor.start()`/`setup_agents()`/`initialize_acquisition()`/`start_preview()`/`start_recording()`/`stop_acquisition()`/`stop()`). · 2026-06-09
- [x] **`make_ttl_identifier_sequences` → `inject_barcode_states`** — migrated all 5 task callers: `_test_ttl_barcodes`, `_test_ttl_outputs` (now send proper decodable barcodes); `_test_video` (initial camera sync burst removed — `rpi_camera_ensemble` handles sync); `exp_trn_spindle`, `probabilistic_switching` (session-start identifier now a proper barcode). Dead `ttl_identifier_sequence` key removed from `probabilistic_switching/task.yaml`. · 2026-06-09
- [x] **`_test_video` + `_test_trigger_with_video` cross-task dep removed** — `OnlinePlottingForPS` import dropped; `_test_trigger_with_video` deleted (was a thin wrapper with test defaults — run base task with `-ts` flags). · 2026-06-08
- [x] **`periodic_trigger_with_video` save path** — replaced `Path(bpod.workspace_path) / bpod.session_name + ".df.jsonl"` with `self.get_path("df.jsonl")` (uses `msw_file()` via `TaskRunner`). · 2026-06-09
- [ ] **`task_name/task_name.py` → `task_name/task.py` rename** — rename main module in every task directory from `{name}.py` to `task.py`; update `load_task_module()` fallback in `cli/tasks.py`. Natural moment: during task extraction into `msw-tasks-*` packages. Not urgent.
- [ ] **`make_ttl_identifier_sequences` → `inject_barcode_states` migration** — 5 tasks still use the deprecated barcode function: `_test_ttl_barcodes`, `_test_ttl_outputs`, `_test_video`, `exp_trn_spindle`, `probabilistic_switching`. `add_trial_onset_ttl` is intentional and stays. See existing roadmap item "TTL barcode audit".
- [ ] **String-concatenated save paths → `msw_file()`** — 5 tasks use `str(path) + ".df.jsonl"` instead of `msw_file()`: `_test_ttl_barcodes:41`, `probabilistic_switching/task_objects.py:730`, `probabilistic_switching_fixedsubjects/task_objects.py:888`, `_test_barcode_iti:150`, `_test_barcode_iti_with_video:147`.

---

### Package extraction (pre-separation sprint)

- [x] **CLI task discovery → entry points** — `list_available_tasks`/`find_task_by_name` moved from `logic/misc.py` to `cli/tasks.py`; filesystem scan primary (bundled tasks need no registration); `msw.tasks` entry-point group additive for external packages; `load_task_module()` added; `task_process.py` uses entry-point-aware loading. · 2026-06-08
- [x] **Cross-task dep blockers for `msw-tasks-core` resolved** — `_test_trigger_with_video` deleted; `_test_video` cross-import removed. · 2026-06-08
- [ ] **Extract `msw-readers`** — boundary clean; move to `external/msw-readers/`; temporary dep on `murineshiftwork` until `msw-core` extracted. Soft-blocked on `msw-core` for final clean dep graph.
- [ ] **Extract `msw-tasks-core`** — calibration tasks + clean hardware test tasks; self-contained; validates entry-point task registration pattern. Blocked on extraction sprint start.
- [ ] **Extract `msw-tasks-sequence`** — reference task for external authors. Follows `msw-tasks-core`.
- [ ] **Org migration: `one-axis-stage`** (manual) — only remaining repo under `larsrollik/`; transfer to `MurineShiftWork` org; set up PyPI OIDC trusted publishing after transfer.

---

### Readers / logic cleanup (pre-extraction)

- [x] **`readers/io.py` → `logic/io.py`** — `save_trial_data` + `load_trial_data` moved to `logic/`; all 10 task callers + `readers/files.py` + `tests/test_reader_fixtures.py` updated; `readers/io.py` deleted. · 2026-06-02
- [ ] **`logic/io.py` — generic ABC for trial data serialisation** — define `TrialDataWriter` / `TrialDataReader` ABC in `logic/io.py`; current JSONL implementation becomes the concrete `JsonlTrialDataWriter` / `JsonlTrialDataReader`; hardware backends (Bpod) register their own save/load via the ABC so the device layer is independently replaceable. Design goal: tasks and `TaskProcess` depend only on the ABC, not the JSONL impl. Prerequisite for Bpod-agnostic hardware abstraction.
- [ ] **Task isolation: `emit_trial()` + writer injection** — tasks should call a generic `emit_trial(dict)` on their context object rather than directly calling `save_trial_data()` or `relay_queue.put_nowait()`. `TaskProcess` owns the write (swappable writer via `TrialDataWriter` ABC) and the relay dispatch (swappable via agent hook). Tasks become pure state-machine + scoring logic with no knowledge of persistence or transport. Prerequisite for hardware-agnostic task definition. See `PLAN_package_graph.md §Task isolation`.
- [ ] **`readers/` — resolve `murineshiftwork.namespace.*` imports** — `readers/namespace.py` and `readers/batch.py` import `is_msw_file` + `parse_session_basename` from `murineshiftwork.namespace.*`; these must come from `msw-core` once extracted. No code change needed now — tracked here so the extraction sprint doesn't forget it.

---

### Decisions needed before extraction sprint — ALL LOCKED · 2026-06-02

See `PLAN_package_graph.md §Locked decisions` for full detail.

- [x] **`msw-namespace` fate** — no separate package; absorbed into `msw-core`. · 2026-06-02
- [x] **`msw-core` name + scope** — `msw-core` = `cli/` + `hardware/` + `hooks/` + `logic/` + `namespace/`. · 2026-06-02
- [x] **Task package split** — `msw-tasks-core` (calibration+tests) + `msw-tasks-sequence` (reference) + `msw-tasks-tab` (lab repo, not PyPI). · 2026-06-02
- [x] **`msw-agent` scope** — `[agent]` opt-in extra; `try/ImportError` guard in `task_process.py`. · 2026-06-02

---

### Sprint order (2026-05-27)

1. ~~**Open Ephys URL validation**~~ — **DONE** · 2026-05-26 · `open_ephys_url` moved from machine config to `SetupConfig` + setup YAML; `OpenEphysParentSession.attach()` now stores `fail_reason` and promotes inner errors to ERROR level; outer warning includes reason + `--child-of ACQUISITION_NAME` hint. Remaining: `--force-standalone` escape hatch.
2. **Split msw** — extract `murineshiftwork` monolith into namespace sub-packages per IMPLEMENTATION_PLAN.md extraction order; see MASTER_PLAN §namespace
2. ~~**Namespace — `file` level + `get_path(artifact=)`**~~ — **DONE** · 2026-05-24
3. ~~**Opto debug**~~ — **DONE** · 2026-05-28 · hardware-verified on rig: TTL barcodes fire, PulsePal abort clean. Remaining (not blocking merge): reader integration test with real opto fixture; airpuff barcode verify on acq machine; alignment script.
4. ~~**msw-flir-bonsai** — `FlirBonsaiClient`, `make_camera_client()` factory, discriminated `CameraConfig` union in `models.py`; wire into `RceConductorAdapter`~~ — **DONE** · 2026-05-25
5. ~~**Namespace — mandatory acquisition level + session_folder_relative**~~ — **DONE** · 2026-05-27 · `namespace.msw.yaml` acquisition now non-optional; standalone sessions get `subject__dt__session_{task}` acquisition dir; `level_overrides` added to `NamespaceBuilder.generate_path()`; `session_folder_relative` + `acquisition_name` in session_paths dict; `session_basename_behav` removed; all conductor calls use `session_folder_relative`; v1/v2/v3 YAML fixtures moved to `tests/data/`. See `PLAN_namespace_unification.md`.
6. ~~**Session/acquisition manifest writer**~~ — **DONE** · 2026-05-27 · `namespace/manifest.py`: atomic `acquisition_manifest.yaml` + `session_manifest.yaml` writes (tmp+replace); wired into `TaskProcess.__init__` + `__exit__`. See `PLAN_session_manifests.md`.
7. ~~**Opto — per-subprotocol Bpod session + JSONL split**~~ — **DONE** · 2026-05-27 · each protocol closes+reopens Bpod into `{basename}__{protocol}/` subdir; JSONL + Bpod CSV + camera recordings co-located; `serial_port_bpod` propagated via `input_kwargs`; `stop_task()` suppresses `PortNotOpenError` on Ctrl+C; gated-mode `channels_ttl_copy` wired into `set_continuous`. See `PLAN_session_manifests.md`.
8. ~~**Reader dispatch skeleton**~~ — **DONE** · 2026-05-27 · `_READER_DISPATCH` dict keyed by `ARTIFACT_FORMAT_*` constants; `read_session_data()` routes at top level. Phase 2b from `PLAN_retrograde_reader.md`.

---

- [x] **Retrograde reader — Phase 1: detection layer** — `ARTIFACT_FORMAT_*` constants, `detect_artifact_format()`, `detect_session_format()`, `validate_session_namespace()` in `readers/namespace.py`; 38 parametrized tests in `test_reader_session_format.py` covering all 5 fixtures. Full analysis: `docs/work_plans/PLAN_retrograde_reader.md`. · 2026-05-26
- [x] **Retrograde reader Phase 2a: `fixture_legacy`** — `tests/data/fixture_legacy/subject003__20210426_183409__probabilistic_switching/`; wired into `FIXTURE_EXPECTATIONS`; `_read_legacy` reads `task_settings.py` + `.pkl`. · 2026-06-08
- [x] **Retrograde reader — `fixture_optotagging`** — `tests/data/fixture_optotagging/_test_subject__20260527_133053_901389__optotagging/`; sanitized paths; `parent_acquisition` block + `session_manifest.yaml` + subprotocol JSOLs; added to `FIXTURE_EXPECTATIONS`; opto fixture tests in `test_reader_fixtures.py` (is_ephys, ephys keys, artifact_format, df loaded). · 2026-06-08
- [x] **Retrograde reader — multi-protocol loading** — `_read_session_yaml` reads `session_manifest.yaml` when present; merges subprotocol dfs with `"subprotocol"` column; stores `data["subprotocols"]`; `MswSession.subprotocols` field carries raw manifest list. · 2026-06-08
- [x] **Retrograde reader Phase 3: full reader interface** — `MswSession` (pydantic, `readers/models.py`); `load_session()` / `load_subject()` / `load_acquisition()` batch API (`readers/batch.py`); `load_acquisition()` uses `acquisition_manifest.yaml`; 169 tests passing across 8 test files. · 2026-06-08
- [x] **Reader: surface namespace_version + artifact_format** — `read_session_data()` now returns `namespace_version` and `artifact_format` keys (via `detect_session_format()`). · 2026-05-26
- [x] **OE parent session path wiring verified** — `attach()` splits on `/` only (OE always uses forward slashes); `acquisition` and `session` levels have identical templates so "session"-level validation of `parts[1]` is correct; second- and microsecond-precision datetimes both parse; integration with `generate_session_paths(is_child_session_to=...)` gives correct 4-level path structure. 6 new tests in `test_parent_session.py`. · 2026-05-27
- [ ] **Opto alignment check script** — read a joint OE+MSW session: load MSW barcodes via `read_session_data()`; load OE TTL on a specified input channel (arg); align barcode timestamps against OE TTL edges; output alignment table + pass/fail summary. Intended as both a diagnostic script and a regression test for real data from the acquisition machine.
- [x] **FIX — `session.py`: drop `raw` / `load_raw`** — `raw` key and `load_raw` param removed from `read_session_data()` and all per-format readers; `_check_completeness` simplified; `validate.py` scoped to MSW file completeness only (RCE tier removed). · 2026-05-27
- [x] **FIX — `test_reader_real_sessions.py:97`: stale version assertion** — changed to `not in ("legacy", "< 1.0.0")`. · 2026-05-27
- [ ] **Camera + device declaration pattern** — `SetupConfig.cameras` → `list[CameraConfig]` with `name:` field; `required_cameras: [rce]` in task.yaml (parallel to `required_devices`); framework creates + tears down camera client in execute.py; tasks receive `args_dict["cameras"]` instead of calling `make_camera_client()` themselves; `MultiCameraClient` fan-out wrapper for mixed-backend rigs. See `docs/work_plans/PLAN_camera_device_pattern.md`. Scale + stage same pattern, lower priority.
- [ ] **Hardware handle + camera audit** — full sweep of all task protocols to verify: (1) correct use of injected hardware handles via `devices` dict (no fallback-to-new-connection in tasks that receive a handle); (2) camera handoff from config/hardware manager instead of ad-hoc constructor calls; (3) `serial_port_pulsepal`, `serial_port_scale` not opened twice. Superseded in part by camera+device pattern work above. Pending test protocols: `_test_scale_hx_connect` and `_test_scale_bench_connect` (same pattern as `_test_pulsepal_connect`).
- [ ] **`msw-labwatch` package** — tiny public package wrapping `labwatch_client` (private registry). MSW adapter stays in `murineshiftwork.adapters.labwatch`; `[labwatch]` extra will list `msw-labwatch` once released. Machine config keys: `labwatch.url`, `labwatch.username`, `labwatch.token`. Release alongside murineshiftwork.
- [ ] **`rpi_camera_ensemble` Windows test matrix** — rce controller (client side) installs on Windows; add `windows-latest` to the test matrix in the rce repo once it is on GitHub
- [ ] **Add RCE session validation to `rpi_camera_ensemble`** — MSW `readers.validate` now handles only MSW file completeness; camera/TTL validation belongs in rce. Implement in rce:
  ```python
  # rpi_camera_ensemble/validate.py
  def validate_session(session_dir, msw_df=None, msw_version=None) -> RceValidationResult:
      """Check conductor + agent files present; run barcode or legacy TTL alignment."""
  ```
  Callers run `msw.validate_session(dir)` then optionally `rce.validate_session(dir, msw_df=...)` for camera checks. Requires rce package to be public first (see [[project_github_org_migration]]).
- [ ] **Opto — shaped waveform** — `generate_waveform_voltages()` + `_ramp_envelope()` in `hardware/stimulation.py`; three-phase (on-ramp, center, off-ramp) with independent types per side (`linear`, `sine`, `raised_cosine`); `Stimulation.setup_custom_waveform()` uploads to PulsePal slot and sets `customTrainID/Target/Loop`; five `waveform_*` YAML defaults in optotagging `task.yaml`; `ramp_sweep` diagnostic mode; 55 tests in `test_stimulation_waveform.py`. Branch: `ft/opto-waveform`.
- [x] **Opto — hardware verification** — TTL barcodes + PulsePal abort confirmed on rig · 2026-05-28. Airpuff barcode verify + `sequence_automated` alignment script still pending (tracked separately, not blocking merge).
- [x] **Opto — PR TODOs** — all code items resolved · 2026-05-28
- [x] **msw-flir-bonsai** — `FlirBonsaiClient`, `make_camera_client()` factory, discriminated `CameraConfig` union in `models.py` · 2026-05-25
- [ ] **msw-flir-bonsai — tests & fixes**
  - [ ] Acquisition machine smoke test — set `BONSAI_EXE`, run `pytest tests/integration/ -v`; smoke-test CLI (`msw-flir find-bonsai`, `msw-flir list-cameras`, `msw-flir test-record`); run via `msw` task with `cameras.backend: flir_bonsai` to verify full `FlirBonsaiClient` path
  - [ ] Spinnaker workflow homogenisation — add `cam1fps`, `cam1width`, `cam1height` `ExternalizedMapping` nodes to Spinnaker workflows (requires Bonsai editor on acquisition machine); enable `AcquisitionFrameRateEnable=true` in SpinView first; then extend `CameraUnit` + `BonsaiCameraRunner._build_cmd()` for width/height
  - [ ] PyPI publish — repo pushed; PyPI OIDC trusted publishing already configured. Only a release (cz bump → tag) is needed to trigger the first publish. See [[project_github_org_migration]]
- [x] **rpi-camera-ensemble: build system + toolchain** — canonical repo `MurineShiftWork/rpi-camera-ensemble` (dashes) on hatchling + src/ layout; workflows on checkout@v6 / setup-uv@v7 / action-gh-release@v3 (node24-native, no FORCE_JAVASCRIPT shim needed); gitleaks via pre-commit; released to PyPI (0.4.3). · 2026-06-09
- [ ] **Bpod retry — hardware verification** — test fixed retry on device `pci-0000:00:14.0-usb-0:4:1.0 → ttyACM7`; confirm 5-attempt / 2s-sleep resolves first-connect failures
- [x] **MSW Monitor — Step 1: LogAgent + ingest server** — `logagent/logagent.py` (daemon Process, bearer token, session UUID, three-phase lifecycle), `logagent/server.py` (FastAPI ingest endpoints); `TaskProcess._start_relay()`; `session_uuid` in session YAML; `put_nowait()` in sequence task. Merged via PR #7, released v2.9.0. `log_url`/`log_bearer_token` documented in `getting_started/new_machine.md`. · 2026-06-09 · `5dfb7fe`
- [ ] **MSW Monitor — Step 2: query endpoints + plotspec CLI** — `GET /sessions`, `GET /sessions/{uuid}`, `GET /sessions/{uuid}/trials?since=N`; CORS middleware; `msw plotspec <task> [--dry-run]`; verify `trial_data` field names for sequence + fixedsubjects. See `PLAN_logagent_ui.md §ft/monitor-step2`. Branch: `ft/monitor-step2`
- [ ] **MSW Monitor — Step 3: Docker + Vue SPA** — two-container compose (`msw-ui` nginx + `msw-api` FastAPI); Vue wired to new endpoints; `config.json` runtime injection from templatevue; read-only v1 (no start/stop/override). Full plan: `PLAN_msw_ui_vue.md`. Branch: `ft/monitor-step3`
- [ ] **MSW Monitor — Step 4: strip `agent/`** — remove `agent/` package and `msw agent start` after LogAgent + Vue validated on one rig. Branch: `ft/monitor-step4`
- [x] **Windows 11 support** — `win32` added to `[tool.uv].environments` + `windows-latest` CI matrix (`ci.yml`); session paths emit forward slashes via `as_posix` (`namespace/paths.py`) so records stay portable across OSes; test fixtures compare `as_posix`, preflight unwritable-path test skipped on Windows. Depends on `acquisition-namespace>=1.2.2` (`generate_path` forward slashes + cross-platform `validate_path` round-trip test + windows CI matrix). COM ports replace `/dev/tty*` in config. · 2026-06-09 · `5dfb7fe`
- [x] **Namespace builder wiring** — extend `namespace.msw.yaml` with `subject`+`acquisition` levels (optional); wire `generate_session_paths()` and `parse_session_basename()` through `NamespaceBuilder` methods; wire `OpenEphysParentSession.attach()` base_text parse through `extract_level_values` + `build_path` roundtrip. · 2026-05-25
- [x] **Session/acquisition manifest writer** — see sprint item 6 above and `PLAN_session_manifests.md` · 2026-05-27
- [x] **Opto per-subprotocol Bpod session + JSONL split** — see sprint item 7 above and `PLAN_session_manifests.md` · 2026-05-27
- [x] **Reader dispatch skeleton (Phase 2b)** — see sprint item 8 above and `PLAN_retrograde_reader.md §2b` · 2026-05-27
- [ ] **`msw oe` subcommand + `open_ephys.control` replacement** — Steps 1+2 done: `external/msw-open-ephys/` restructured (flat src layout, hatchling+hatch-vcs, package renamed `msw_open_ephys`). Remaining: add `msw oe status/preview/record/stop` delegating to `msw_open_ephys.cli.commands`; replace `open_ephys.control` in `parent_session.py` with `msw_open_ephys.controller`; add `oe = ["msw-open-ephys"]` optional dep. Full plan: `docs/work_plans/PLAN_oe_remote.md`.
- [ ] **Hardware integration test suite** — separate repo (not `tests/`); real Bpod + PulsePal + scale + OE GUI on acquisition machine; combinatorial runs of `sequence` + `optotagging` with/without `--parent openephys`; simulation-mode smoke tests; Bpod override API for automated trial progression; scope and repo structure TBD
- [ ] **Valve calibration fit model config** — `Calibrations.fit_model: exponential | linear` field in `models.py` (default `exponential`); written to setup YAML as `calibrations.fit_model:`; propagated to `ValveCalibration` instances on load; `ValveCalibration._fit()` branches on it; `evaluate.py` reads model from setup config when injecting `valve_s_for_ul`; calibration task reads same field as default, overridable via `-ts FIT_MODEL=linear` for one run. Design approved 2026-05-25.
- [x] **Valve calibration fallback + staleness warning** — `_inject_valve_calibration()` in `evaluate.py`: (1) port present → use, warn if >180 days stale; (2) `bpod_valve` empty → loud WARNING, use `_FALLBACK_VALVE_CALIBRATION` (npx2 reference, debug only); (3) some ports calibrated but requested port missing → hard `ValueError` with list of calibrated ports. `CALIBRATION_STALE_DAYS=180` in `models.py`. · 2026-05-25
- [ ] **`docs/tasks/` coverage** — add `calibration_and_test.md`; add task docs for `airpuff`, `optotagging` when those protocols are stable
- [ ] **post-acquisition pipeline in Python** — replace shell-script invocations in `msw post run` (`run_post_acquisition_tasks.sh`) with pure Python; provision_rpi scripts (`collate_data2.sh`, `upload_to_server.sh`, `h264_to_mp4.sh`) remain in `external/` (off-limits); Python wrapper would call them via subprocess or replicate logic; consider whether `inventory.ini` should live in `msw_configs/` (config dir) rather than alongside the scripts; see `docs/work_plans/PROVISION_RPI_SCRIPTS.md`
- [x] **`periodic_trigger` + `sleep_homecage` overhaul** — renamed `homecage_sleep` → `sleep_homecage`; replaced legacy `make_ttl_identifier_sequences` with `inject_barcode_states` (start + every `BARCODE_INTERVAL_S` + session-end); `task.yaml` with defaults for all three tasks; `sleep_homecage` delegates cleanly to `periodic_trigger_with_video`; `openfield` updated to same clean delegate · 2026-05-28
- [ ] **TTL barcode audit — migrate `make_ttl_identifier_sequences` callers to `inject_barcode_states`** — `hardware/bpod/ttl.py::make_ttl_identifier_sequences` is a legacy pre-ttl_barcoder mechanism still used by: `probabilistic_switching`, `periodic_trigger`, `periodic_trigger_with_video`, `exp_trn_spindle`, `_test_ttl_outputs`, `_test_ttl_barcodes`, `_test_video`. `add_trial_onset_ttl` is intentional (simple onset pulse, not a sync barcode) and can stay. Migration requires replacing the StateMachine-creating call with `inject_barcode_states` on an existing sma; once all callers migrated, `make_ttl_identifier_sequences` + `_add_protocol_ttl` + `_add_random_identifier` can be deleted from `hardware/bpod/ttl.py`. Also clean up redundant direct `from ttl_barcoder.core.barcode_ttl import BarcodeTTL` imports in tasks that already use `logic/barcode.py` (add `BarcodeTTL` + `BarcodeConfig` to `logic/barcode.py` `__all__` first).
- [ ] **Docs restructure** *(plan only, do not implement yet)* — split `docs/` into `docs/` (user-facing: getting_started, cli, concepts, setup, tasks) and `dev/` (internal: sop, roadmap, work_plans, legacy, impl). ROADMAP and SOP move to `dev/`. All `docs/work_plans/PLAN_*.md` move to `dev/work_plans/`. Legacy docs move to `dev/legacy/`. Update mkdocs.yml nav to reflect new layout.
- [ ] **Forgejo Actions port** *(infrastructure, not urgent)* — add `.forgejo/workflows/` alongside `.github/workflows/` for all published packages (`pypulsepal`, `ttl-barcoder`, `acquisition-namespace`, `msw-flir-bonsai`, future packages). Forgejo release workflow is identical except PyPI publish uses token-based auth (twine or `uv publish --token`) instead of OIDC; drop `id-token: write` from Forgejo release workflow. Also: register Linux + Windows `act_runner` at org level; deploy `*.docs.murineshift.work` via Caddy + rsync; migrate templatepy Copier template to emit `.forgejo/workflows/`. Full plan: `PLAN_forgejo_migration.md`.
- [ ] **Zenodo DOI — re-register under murineshiftwork org** *(not urgent)* — Zenodo DOI for pypulsepal (`10.5281/zenodo.6379627`) points to the first working version on the old `larsrollik` GitHub account; it is not the concept DOI and does not resolve to the latest release. All Zenodo DOI badges and references have been removed from READMEs, docs, and CITATION.cff files across repos. To fix: re-connect Zenodo webhook to `murineshiftwork/pypulsepal` and any other repos that need citation DOIs; a new release will create a fresh record; add the concept DOI back to CITATION.cff + README badge only after it resolves correctly.
- [ ] **RCE TTL: replace pigpio → lgpio** *(low priority, RPi 5 blocker)* — pigpio is unmaintained (last release 2021), apt package gone from Bookworm/Trixie, fundamentally incompatible with RPi 5 (RP1 PCIe GPIO). For camera-frame-driven sync pulses at ≤200 Hz / 1 ms, `lgpio` (chardev-based, pip-installable, RPi 4+5) gives ±50 µs jitter — sufficient for hardware clock sync. Work plan: `docs/work_plans/PLAN_rce_ttl_lgpio.md`. Analysis: `external/pigpio/ANALYSIS.md`. **Needs GitHub issue on `murineshiftwork/rpi-camera-ensemble` once repo is public.**

---

## DONE

- [x] msw-open-ephys package restructured — `external/msw-open-ephys/`: flat `src/msw_open_ephys/` layout, hatchling+hatch-vcs, `oe-remote` CLI entry point preserved; old nested `oe_remote/` + dead `open_ephys_remote/` removed · 2026-05-26
- [x] `open_ephys_url` moved to `SetupConfig` — field in `models.py`, setup YAML (`setup-npxb.yaml`), `_resolve_parent_session()` reads setup config first (machine config fallback kept); `docs/setup/setup_config.md` updated · 2026-05-26
- [x] optotagging laser power recalibrated — PCHIP two-step (mod→Ia→mW) from confirmed 62 mW fiber-tip max (Ia=120 mA); all `laser_power` values in `msw_configs/tasks/optotagging/task.yaml` updated; antidromic target corrected from 80 mW → 1.0 (62 mW max); `OPTOTAGGING_SESSION_DESIGN.md` updated · 2026-05-26
- [x] `out_path` / `config_dir` argparse default fix — parser defaults were `""` not import-time values; `resolve_data_dir()` called at evaluate time; machine config priority chain now respected · 2026-05-26
- [x] `save_trial_data` mkdir — `filepath.parent.mkdir(parents=True, exist_ok=True)` added before open · 2026-05-26
- [x] `channels_ttl_copy` — renamed from `channel_trigger_clock`; default `[]`; mirrors stim pulse params at 5 V (BNC2110 threshold); `trigger_clock()` removed · 2026-05-26
- [x] OE parent session — `hardware/parent_session.py`: `ParentSessionProtocol`, `ParentSessionInfo`, `OpenEphysParentSession` (lazy OE import), `make_parent_session(type, **kw)` factory; `--parent TYPE[:URL]` CLI flag (URL falls back to `open_ephys_url` in machine config); `_resolve_parent_session()` + `_parse_parent_flag()` in evaluate.py; `parent_acquisition:` block in `.msw.session.yaml`; entrypoint plugin loader in parser.py (`msw.cli` group); 19 tests · 2026-05-25
- [x] `acquisition-namespace` standalone package — extracted from `murineshiftwork.namespace.spec`; `external/acquisition-namespace`; `NamespaceBuilder`, `NamespaceSpec`, `NamespaceLevelSpec`; fixed `_build_one` self-recursion bug; 25 tests; MSW `spec.py` now re-exports from it · 2026-05-24
- [x] namespace `file` level + `get_path(artifact=)` — `namespace.msw.yaml` `file` template; `get_msw_builder()` in `paths.py`; `msw_file()` delegates to builder (no hardcoded `.msw.` in Python); `TaskRunner.get_path()`; all raw `.msw.` replaced in `task_process.py`, `log.py`, task files; `readers/namespace.py` uses `is_msw_file()`; 23 tests · 2026-05-24
- [x] bench scale baudrate default 9600; `BenchScaleAdapter` + `ScaleDevice` + `make_scale` all corrected · 2026-05-24
- [x] HX711 retry — `SerialWeighingScaleAdapter.read_weight_blocking()` overrides hx711 internal retry; suppresses ERROR-level parse-failure spam, single WARNING summary · 2026-05-24
- [x] dynamic calibration — tqdm progress bar (`leave=False`) on drop loop; before/after weight delta (robust against bench-scale auto-zero) · 2026-05-24
- [x] pypulsepal LCD fix — space padding (not null bytes) + "PulsePal / Python fw{ver}" display text · 2026-05-24
- [x] execute.py device factory registry — `_DEVICE_REGISTRY` dict + lazy-import helpers replaces per-device if-chain in `run_task`; spurious pulsepal connection now prevented implicitly · 2026-05-24
- [x] pulsepal spurious connect fix — `evaluate.py` clears `serial_port_pulsepal` when setup config present but doesn't declare pulsepal; `execute.py` secondary guard · 2026-05-24
- [x] BUILD_SYSTEM_STANDARD.md rewrite + GH_CLI_REFERENCE.md — copier, Zenodo, vendoring, mypy v2 import-untyped gotcha · 2026-05-24
- [x] msw-flir-bonsai camera integration — `FlirBonsaiClient`, `RceConductorAdapter`, `make_camera_client()` factory; `CameraConfig` FLIR fields; RCE module-level import bug fixed · 2026-05-22
- [x] MASTER_PLAN.md — single authoritative design doc, supersedes PLAN_msw_monitor + PLAN_msw_ui_agent_broadcast + AGENT_USAGE_MODEL + PLAN_hardware_manager · 2026-05-22
- [x] Sequence online plot — outcome dot offsets (±0.1 from perf line), no-response grey x at 0.5, perf-perfect yellow; `poke_xmax_s` param (default 6 s) · 2026-05-22
- [x] PlotSpec schema — `logic/plot_spec.py` pydantic validator; `sequence/plot_spec.yaml`, `probabilistic_switching_fixedsubjects/plot_spec.yaml`; 17 tests · 2026-05-22
- [x] `hardware/manager.py` — `DeviceProtocol` + `HardwareManager` context manager · 2026-05-22
- [x] msw-flir-bonsai package — BonsaiCameraRunner, MultiCameraRunner, timestamp unwrapping, barcode+TTL alignment; 9 tests; Bonsai workflows for FlyCapture/Spinnaker 1-cam/2-cam · 2026-05-18 · cbc3981 (external/)
- [x] fill docs — cli/tasks.md, concepts/architecture.md stub removed · 2026-05-18 · pending
- [x] opto task consolidation — 4 tasks → 1 unified `optotagging`; multi-protocol loop, stimulation_defaults, laser_power merged into logic/stimulation.py · 2026-05-18 · d7d3068
- [x] `msw tasks` CLI — `list`, `defaults <name>`, `init task-configs`, `modes <name>` · 2026-05-18 · a2b859b
- [x] named modes content — habituation/expert/probe defined in `probabilistic_switching`, `sequence`, `airpuff` task.yaml · 2026-05-18 · a2b859b
- [x] `build_task_settings()` extraction — `logic/task_settings.py`, decouples evaluate_args from argparse flat dict · 2026-05-18 · a2b859b
- [x] scale device config — `ScaleDevice` model, setup YAMLs updated, scale_type/baudrate wired through evaluate.py · 2026-05-18 · 1aa4ce8
- [x] serial-scale-hx711 + serial-scale-bench packages — formalized with hatchling/cz/pre-commit/GH Actions; BenchScaleAdapter added · 2026-05-18 · 73a9861
- [x] sequence level writeback integration test (5 tests, test_sequence_writeback.py) · 2026-05-18 · dc9b438
- [x] `TaskProcess.__del__` removed — redundant with `__exit__`, hazardous at shutdown · 2026-05-18 · dc9b438
- [x] auto-bump workflow (bump.yaml, tag_only=true in cz) · 2026-05-18 · 1777835
- [x] code review prompts doc; cz bump fix · 2026-05-18 · 6131087
- [x] hook system — HookContext, TaskHook(fatal=), SessionAbortError, collect/load/run, 34 tests · 2026-05-18 · 0d32b4a
- [x] subject writeback — save_subject_task_overrides, sticky task_mode, config_dir inject · 2026-05-18 · 0d32b4a
- [x] sequence level writeback — save_session_end() writes start_level to subject YAML · 2026-05-18 · 0d32b4a
- [x] msw post clean + run commands (13 tests) · 2026-05-18 · 0d32b4a
- [x] docs reorganisation — legacy/, concepts/, tutorials/, cli/ skeletons · 2026-05-18 · 0d32b4a
- [x] 5-level settings priority chain — bundled → overlay → sticky mode → subject keys → CLI · 0d32b4a
- [x] config-dir overlay — deep-merge user task.yaml on top of bundled defaults · 0d32b4a
- [x] named task modes (default:/mode: structure) — all task.yaml files; fixedsubjects has 5 modes · 31eba57
- [x] namespace package prep — tasks/__init__.py removed, murineshiftwork/__init__.py minimal · 671ac4d
- [x] session output consolidation — single .msw.session.yaml (format v2), version 2.0.0 → 2.1.0 · 671ac4d
- [x] simulation mode — SimBpod, SimWeighingScale, --simulate flag · 75f7916
- [x] hardware action API Phase 1 — msw action, BpodActionDriver, ActionRequest · 75f7916
- [x] mypy tasks.* types cleared · 39f23da
- [x] QThread → threading.Thread in TaskRunner · 54e855c
- [x] CLI restructure — defaults.py, preflight.py, evaluate.py split · 1092f37
- [x] logic/config subpackage — models.py, io.py, ini.py · 1092f37
- [x] hardware/bpod/ subpackage — BpodFactory, ttl.py, water.py, user_settings · 1092f37
- [x] task settings INI → YAML migration (all task.yaml files) · d8d48ce
- [x] configobj removed from dependencies · d7fc13e
- [x] io/ package removed; logic/io.py canonical · 1092f37
- [x] PulsePal → pypulsepal rewrite · 1092f37
- [x] stage movement rename (_calibration_stage_tower → _test_stage_move) · 1092f37
- [x] reader validation tests + fixture files · 75f7916

---

## Notes

**Machine-local config (`~/.murineshiftwork/msw_machine.yaml`):** This file tells MSW where to find the shared config directory. Priority chain for `config_dir` (highest wins): (1) `--config-dir` CLI arg, (2) `MSW_CONFIG_DIR` env var, (3) `config_dir` key in `~/.murineshiftwork/msw_machine.yaml`, (4) `/mnt/maindata/msw_configs` (historical default). The current live config directory on this machine is `/mnt/maindata/msw_configs` — subjects under `subjects/`, setups under `setups/`. Set a different machine with `msw config set-dir <path>` or edit the YAML directly. Full logic in `src/murineshiftwork/logic/machine_config.py`.

**LogAgent + monitor architecture (Step 1 done — `ft/monitor-step1`):**
`logagent/logagent.py` is a daemon `multiprocessing.Process` started by `TaskProcess` when `log_url` is set in `msw_machine.yaml`. It forwards session start/trial/stop events to the central API server (`logagent/server.py`) via HTTP POST with bearer token auth. Session is identified by `session_uuid` (UUID4, generated in `TaskProcess.__init__`, written to `.msw.session.yaml`). The task loop calls `relay_queue.put_nowait(trial_data)` — ~1 µs, never blocks. LogAgent crash is silent (daemon=True). Monitor down → HTTP times out in 0.5 s, caught and logged at DEBUG. CLI remains the primary session interface; monitor is best-effort read-only. Full design: `PLAN_logagent_ui.md`. Architecture authority: `MASTER_PLAN.md §6`.

**ControllerSession (future):** extend `HardwareManager` to also hold Stage/PulsePal handles. `POST /hardware/action` dispatches hardware actions without stopping the session.

**Retrograde reader + namespace YAML strategy:** `namespace.msw.yaml` is write-time only — old sessions are read via `detect_artifact_format()` + format-specific readers, never through the builder.  Session basename structure (`{subject}__{datetime}__{task}`) is frozen.  Artifact format evolution uses `msw_format_version` inside `session.yaml`.  Four format eras exist on disk; see `PLAN_retrograde_reader.md` for the full matrix and `readers/namespace.py` for the detection API.
