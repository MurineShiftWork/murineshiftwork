# Publication Readiness Review: rpi-camera-ensemble

**Date:** 2026-05-31
**Reviewer:** Claude Code (claude-sonnet-4-6)
**Repo path:** `/home/tars/code/murineshiftwork/external/provision_rpi/rpi_camera_ensemble`
**Current version:** 0.4.1 (tag `v0.4.1` present)
**Target:** public release on GitHub + PyPI

---

## Executive Summary

**Status: NEAR-READY. No hard blockers, but 6 MINOR issues require attention before publishing.**

The repo is in good structural shape. Build system, CI/CD, pre-commit, tests, and core code all work correctly. The main areas needing cleanup are:

1. Stale config examples with wrong field names and the legacy `library: pigpio` default
2. `docs.yml` trigger path is wrong for the src/ layout (would silently miss rebuilds)
3. `CITATION.cff` version is frozen at `0.1.0` (not the actual release version)
4. `CLAUDE.md` still documents the old flat layout
5. `scripts/rce-agent.service` has development credentials (hypatia username/path)
6. Stale ruff/mypy exclusion patterns for files that no longer exist

Nothing here blocks import, install, or core functionality. But items 1 and 5 in particular are visible to users picking up the examples.

---

## 1. Build System

**File:** `pyproject.toml`

### MINOR: fallback-version is `0.1.0` but version is already `0.4.x`

`pyproject.toml:47`: `fallback-version = "0.1.0"`

The templatepy standard uses `1.0.0`. This value is only hit when building outside a git context with no tags (e.g., shallow clones without tags, or `pip install` from a tarball without vcs data). With `v0.4.1` already tagged, using `0.1.0` as fallback is misleading. Set to `"0.4.1"` to track the actual release.

**Templatepy note:** The template uses `fallback-version = "1.0.0"`. The convention should be to set this to the last known stable version at the time the pyproject.toml is written, not an arbitrary `0.1.0` or `1.0.0`.

### OK: py.typed present

`src/rpi_camera_ensemble/py.typed` exists. PEP 561 satisfied.

### OK: classifiers

`pyproject.toml:14-23`: Present and accurate. BSD License, Python 3.10/3.11/3.12, Topic::Scientific/Engineering, Topic::Multimedia::Video, POSIX Linux. All correct.

### MINOR: `typing_extensions` used but not declared as a dependency

`src/rpi_camera_ensemble/config/camera/camera.py:7` and
`src/rpi_camera_ensemble/config/acquisition.py:11` both do:

```python
if sys.version_info < (3, 11):
    from typing_extensions import Self
```

`typing_extensions` is not listed in `[project.dependencies]`. It is a transitive dependency of `pydantic>=2.0` and will always be present in practice, but it is not guaranteed by the package metadata. Strictly, if someone installs with `--no-deps` or uses a custom pydantic build, Python 3.10 would fail at import. Either add `typing_extensions; python_version < "3.11"` to core deps, or backport using `pydantic.v1.typing` which always has it. Adding the explicit dep is the safer option.

### OK: optional extras structure

`conductor`, `agent`, `lgpio`, `pigpio`, `rpigpio`, `rpi`, `all`, `dev`, `docs` — the groupings are logical, the `rpi` shortcut (`agent + lgpio`) is a useful convention.

### MINOR: stale ruff `per-file-ignores` and mypy `exclude` patterns

`pyproject.toml:164-168` (ruff) and `pyproject.toml:177-188` (mypy) both reference files that were moved to `examples/` in commit `b4bf93d`:

```
tests/barcode_ttl/**
tests/make_*.py
tests/run_*.py
tests/conductor_*.py
tests/conductor_async_demo.py
tests/conductor_concurrent_demo.py
tests/make_acq_process.py
tests/make_default_config.py
tests/run_api_client.py
tests/run_conductor.py
tests/run_conductor_from_conf.py
tests/run_agent.py
```

None of these paths exist in `tests/` any more (`tests/` now only contains `tests/` and `fixtures/`). They are harmless (no match = no effect), but they are dead config. Clean them up and replace with `examples/**` for ruff (already present) and remove the stale mypy patterns.

Note: `^examples/` is already in the mypy excludes; ruff `examples/**` is already present. Only the stale `tests/...` patterns need removal.

### NOTE: mypy `python_version` not set

`pyproject.toml:174`: `[tool.mypy]` has no `python_version`. The template has `python_version = "[[ python_requires ]]"`. Without this, mypy uses its own default (currently 3.x). Add `python_version = "3.10"` (the minimum supported) to ensure correct type-narrowing for the `sys.version_info` guards.

### NOTE: mypy `warn_return_any` is `false`

`pyproject.toml:175`: set to `false`, whereas the template has `true`. This is intentional given the ignore_errors overrides for hardware-dependent modules. Fine to keep but worth documenting the intent.

### NOTE: No `N` classifier for `Development Status`

Missing `"Development Status :: 4 - Beta"` or `"Development Status :: 3 - Alpha"`. Not a blocker but helpful for users browsing PyPI.

### OK: commitizen config

`pyproject.toml:112-118`: `cz_conventional_commits`, `version_provider = "commitizen"`, `tag_format = "v$version"`, `update_changelog_on_bump = false`. Matches the template. `version` field correctly shows `0.4.1` matching `VERSION`.

### OK: pytest config

`testpaths = ["tests"]` and `addopts = "--cov=src/rpi_camera_ensemble --durations=0"`. The template has `--cov-report=term-missing --maxfail=5` which are better defaults for local dev — consider adding `--cov-report=term-missing`.

---

## 2. CI/CD

### MINOR: `docs.yml` trigger path is wrong for src/ layout

`docs.yml:10`: `"rpi_camera_ensemble/**/*.py"` — this path was valid before the migration to `src/` layout but is now wrong. The Python source lives at `src/rpi_camera_ensemble/**/*.py`. As written, changes to the source code will not trigger a docs rebuild. Fix to:

```yaml
- "src/rpi_camera_ensemble/**/*.py"
```

### OK: Action versions

- `actions/checkout@v6` — correct
- `astral-sh/setup-uv@v7` — correct
- `softprops/action-gh-release@v3` — correct

### OK: Push trigger correctness

`ci.yml:5-6`: push on `main` only, `tags-ignore: ["v*"]` prevents double-run on bump tags. Correct.

`release.yml:6`: push on `main`, no `tags-ignore`. The `if: "!startsWith(github.event.head_commit.message, 'bump:')"` guard is what prevents looping — this is the correct pattern given the `cz bump` push.

### OK: gitleaks placement

gitleaks is in `.pre-commit-config.yaml:34-35` as a local hook, not as a GitHub Actions workflow. Correct — avoids the org-level license requirement.

### OK: release workflow trusted publishing

`release.yml:60`: `uv publish --trusted-publishing automatic` — correct for OIDC-based PyPI publishing. Requires the repo to be registered on PyPI with trusted publishing configured.

### NOTE: release workflow — no `tags-ignore` on push trigger

`release.yml:4-6`: The release job runs on every push to main, guarded only by the `!startsWith(github.event.head_commit.message, 'bump:')` check. This is fine because the bump commits are pushed by the bot and are correctly skipped. But it means any direct push to main that does not include a bumpable conventional commit will still run the full workflow up to the bump step, which returns exit 21 and exits cleanly. Acceptable, but adding `tags-ignore: ["v*"]` would be marginally cleaner.

### OK: `pr-review.yml`

Correctly structured as a no-op placeholder with both Claude and Ollama options commented out. Does not require secrets, does not run anything harmful. Fine for a public repo.

---

## 3. Pre-commit

**File:** `.pre-commit-config.yaml`

### OK: Hook versions

| Hook | Current | Latest |
|---|---|---|
| pre-commit-hooks | v6.0.0 | v6.0.0 |
| ruff-pre-commit | v0.15.14 | v0.15.15 |
| mirrors-mypy | v2.1.0 | v2.1.0 |
| commitizen | v4.16.2 | (current) |
| gitleaks | v8.30.0 | (current) |

ruff is one patch behind (v0.15.14 vs v0.15.15). Not a blocker.

### OK: mypy exclude pattern in pre-commit

`.pre-commit-config.yaml:24`: exclude pattern correctly covers `^examples/` and the legacy test scripts. Matches the pyproject.toml exclusions.

### NOTE: pre-commit mypy excludes `tests/` legacy files that no longer exist

Same stale pattern issue as in pyproject.toml. Harmless but untidy.

---

## 4. Tests

**File:** `tests/tests/test_unit/test_unit.py` — 21 tests total.

### OK: Test quality

All 21 tests are meaningful and correctly structured. The skipif guards on fixture-dependent tests are appropriate. Tests cover:

- Package importability and version attribute
- Config model defaults and roundtrips (CameraConfig, ConductorConfig, EnsembleAcquisitionConfig, AgentConfig)
- TTL factory error paths
- All three CLI parsers
- RCESession discovery, slot loading, load=False mode
- validate_session full run
- NotADirectoryError guard

### NOTE: coverage gaps in public API

The following public-facing items have no test coverage:

- `RCESession.summary()` — not tested at all; the method is non-trivial and could return unexpected structure
- `TTLData.__len__` and `TTLData.__repr__` — edge cases (all-None fields)
- `ConfigMixin._serialize_types` — no direct tests; covered incidentally via roundtrip tests but UUID, datetime, and Enum serialization are not explicitly verified
- `validate_session` warning paths: jitter warning (`> 5%`), fps deviation warning, dropped frame warning, duration spread warning — none tested; would require synthetic fixtures
- `SessionQC.print_report()` — not tested
- `_check_h264()` and `_probe_video()` — not covered

These are gaps but not blockers for initial publication. A NOTE, not a MINOR.

### OK: Fixture quality

`tests/fixtures/rce_session/` contains a well-formed two-agent session with:
- conductor cfg.yaml and ensemble.yaml
- per-agent ttl_out.npz (500 frames), ttl_in.npz (500 pulses), video.h264
- Realistic naming pattern: `t000_test__20260101_120000_000000__fixedsubjects.rce.{component}.{timestamp}.{suffix}`

The fixture covers all `_CORE_AGENT_SLOTS` and tests exercise all non-trivial paths.

### NOTE: test for `validate_session` checks `not qc.agents["rpi-131"].errors`

`test_unit.py:240`: This assertion will silently pass if `video.h264` is a stub file with a valid H264 start code prefix or zero bytes. The fixture `video.h264` files are present — worth verifying they have valid start codes. If the fixture files are stubs (empty or random), `_check_h264()` will add an error and this test will fail. This should be verified before publication.

---

## 5. Docs

**Files:** `docs/index.md`, `docs/tutorial/*.md`, `mkdocs.yml`

### MINOR: `mkdocs.yml` has wrong `site_url` and `repo_url`

`mkdocs.yml:29`:
```yaml
site_url: https://murineshiftwork.github.io/rpi_camera_ensemble/
repo_url: https://github.com/murineshiftwork/rpi_camera_ensemble
```

The actual repository name is `rpi-camera-ensemble` (hyphen, not underscore), and GitHub organization names are case-sensitive in display but the URL will redirect. However, the site_url would be wrong — GitHub Pages for `rpi-camera-ensemble` would be at `https://murineshiftwork.github.io/rpi-camera-ensemble/` (with hyphen). Fix both to use the hyphenated form.

Also `site_author:` is blank at line 3.

### OK: `docs/index.md`

Minimal but correct — links to README and CITATION.cff. No skeleton content.

### OK: `docs/tutorial/dependencies.md`

Accurate and current: `lgpio` default, `gpiochip` instructions for RPi 4 vs RPi 5, correct install commands. The `pigpio` legacy section is correctly present with caveats.

### OK: `docs/tutorial/rpi_camera_cli.md`

Minimal but correct for its purpose.

### NOTE: `docs/tutorial/rpi_config.md` has stale content

`rpi_config.md` still references `libcamera-hello` (the old command) alongside `rpicam-hello`. Also contains `.inputrc` content about bash history search that is clearly a copy-paste remnant from a personal setup. This is in the public docs. Clean it up or move the bash tips to a separate page.

Also contains `sudo apt install python3-ipython` which is a personal debugging tool, not part of the RCE setup.

### NOTE: No tutorial page for the session reader and validator (`io/`)

`RCESession` and `validate_session` are the primary analysis API that users of the package will call on the acquisition machine. There is no tutorial page covering:

- Loading a session with `RCESession.from_directory()`
- Accessing TTL data
- Running `validate_session()` and reading the QC report

This is a documentation gap for the most user-facing API in the package.

---

## 6. Examples

### BLOCKER-level correctness issue: `ensemble.yaml` and related configs use wrong field name

`examples/configs/ensemble.yaml:2`, `examples/configs/ensemble.session.yaml:2`:
```yaml
settings:
  max_recording_hours: 3.0
```

The actual model field name is `max_recording_duration_sec` (`config/acquisition.py:101`). The key `max_recording_hours` does not exist in `AcquisitionSettings`. Pydantic v2 with default `model_config` silently ignores unknown extra fields — so this YAML will parse without error but the `max_recording_duration_sec` field will use its default (10800 seconds = 3 hours), masking the misconfiguration.

This is the most confusing issue for a new user: the example shows a field that has no effect.

**Fix:** Change `max_recording_hours: 3.0` to `max_recording_duration_sec: 10800.0` in:
- `examples/configs/ensemble.yaml:2`
- `examples/configs/ensemble.session.yaml:2`

Also applies to `examples/configs/cameras.yaml` which has the same pattern with `max_recording_duration_sec` (this one is actually correct in cameras.yaml — that field name does match).

Wait — re-check: `cameras.yaml` does NOT have a `settings:` block at all. Only `ensemble.yaml` and `ensemble.session.yaml` have the wrong field name.

### BLOCKER-level correctness issue: All four multi-camera config files use `library: pigpio`

`examples/configs/ensemble.yaml:45`, `examples/configs/ensemble.session.yaml:45`, `examples/configs/cameras.yaml` (all four agents):

```yaml
ttl:
  library: pigpio
  out_pin: 8  (or 25)
  in_pin: 16  (or 23)
  out_duration_us: 1000
```

The project default is now `lgpio` and the docs (`dependencies.md`) and README both say lgpio is recommended. All example configs still show `pigpio`, which is the opposite of what a new user should set up. A user copying these files verbatim will use the legacy, non-functional-on-RPi5 library.

These configs also all **missing `gpiochip:`** — which is a required field for lgpio (`gpiochip: 0` for RPi 4, `gpiochip: 4` for RPi 5).

**Fix:** Update all `ttl:` blocks in example configs to:
```yaml
ttl:
  library: lgpio
  gpiochip: 0
  out_pin: 25
  in_pin: 23
  out_duration_us: 1000
```

### MINOR: `examples/configs/conductor.yaml` has three stale fields

`conductor.yaml:3,6,7`:
```yaml
max_acquisition_hours: 3.0
connection_timeout: 10.0
retry_attempts: 3
```

The actual `ConductorConfig` model has `max_recording_duration_sec` (not `max_acquisition_hours`), and `connection_timeout`/`retry_attempts` are commented out in the model (`conductor.py:34-35`). All three of these fields will be silently ignored by pydantic. Update conductor.yaml to use the actual field name `max_recording_duration_sec: 10800.0` and remove the two commented-out fields.

### OK: `examples/configs/agent.yaml`

Fields match `AgentConfig` exactly: `instance_name`, `api_host`, `api_port`, `log_level`, `max_log_files`, `log_dir`, `data_dir`. No issues.

### NOTE: README `## Output structure` section shows wrong file format

`README.md:160-163`:
```
├── cam01_20260101_120000.h264
├── cam01_20260101_120000_metadata.json
├── cam01_20260101_120000_ttl_out.csv   # frame timestamps
└── cam01_20260101_120000_ttl_in.csv    # received TTL timestamps
```

Actual output uses the `.rce.` namespace and `.npz` format for TTL data, not CSV:
```
{basename}.rce.{instance}.{timestamp}.video.h264
{basename}.rce.{instance}.{timestamp}.ttl_out.npz
{basename}.rce.{instance}.{timestamp}.ttl_in.npz
```

The README output structure section predates the file naming convention and is significantly wrong. A user trying to find their output files using this guide will be confused.

### NOTE: README `## TTL synchronization` shows wrong YAML key

`README.md:133-143`:
```yaml
camera:
  ttl:
    library: lgpio
```

There is no `camera:` top-level key in agent configs or ensemble configs. The TTL config lives nested inside `camera_config.ttl` within ensemble agents, or is not a user-configured field in agent.yaml at all (the agent picks it up from the acquisition request). The YAML snippet is misleading about where this config lives.

---

## 7. CITATION.cff and README

### MINOR: CITATION.cff `version` is `0.1.0`

`CITATION.cff:6`: `version: "0.1.0"` — the actual release version is `0.4.1`. This is shown in the GitHub citation widget and in Zenodo if integrated. Update to `"0.4.1"`.

`CITATION.cff:7`: `date-released: "2026-05-30"` — this is correct for the current date.

### OK: CITATION.cff structure

`cff-version: 1.2.0`, correct `type: software`, ORCID present, repository-code and url correct, BSD-3-Clause license. The Zenodo TODO comment is appropriate and helpful.

### OK: README overall quality

Good. Architecture diagram, install instructions using `lgpio`, feature list, code examples all correct and current. Badges are correct.

### NOTE: README `## Development` section uses `pip install` instead of `uv`

`README.md:178-180`:
```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

Should be `uv sync --extra dev` and `uv run pre-commit install` / `uv run pytest` to match the CI setup.

### NOTE: README `## Deployment` link is wrong

`README.md:170`:
```
See [`external/provision_rpi/`](https://github.com/MurineShiftWork/rpi-camera-ensemble/tree/main/external/provision_rpi) for Ansible playbooks...
```

The Ansible playbooks live at `deploy/` inside the repo, not `external/provision_rpi/`. This path does not exist in the repository. Change to:
```
See [`deploy/`](https://github.com/MurineShiftWork/rpi-camera-ensemble/tree/main/deploy)
```

---

## 8. Package Code Spot-Check

### `src/rpi_camera_ensemble/__init__.py`

**OK.** Clean 23-line file. Version lookup via `importlib.metadata.version(Path(__file__).parent.name)` is correct — `parent.name` returns `"rpi_camera_ensemble"` which is the normalized form of `rpi-camera-ensemble` and will resolve correctly from metadata. Fallback to `"0.0.0.dev0"` is appropriate.

### `src/rpi_camera_ensemble/io/__init__.py`

**OK.** Exports exactly `RCESession` and `validate_session`. Clean.

### `src/rpi_camera_ensemble/io/session.py`

**OK.** Well-structured. Regex `_FILE_RE` correctly matches the `.rce.` namespace with opaque prefix. `_SLOTS` dict is comprehensive. `_load_component` handles errors gracefully per-slot without crashing the session. `summary()` returns a structured dict. No issues found.

### `src/rpi_camera_ensemble/io/validate.py`

**OK.** Solid implementation. `_probe_video` correctly falls back gracefully when ffprobe is absent. `_check_h264` correctly checks both 3-byte and 4-byte start codes. The cross-agent consistency checks (TTL in counts, duration spread) are correct. No issues found.

### `src/rpi_camera_ensemble/config/camera/camera.py`

**OK.** `TTLLibrary.LGPIO` is default. `gpiochip: int = Field(default=0, ge=0)` is present and correct — the comment `# RPi 4: 0, RPi 5: 4` is helpful. The `model_validator` for auto-creating `Picamera2Params` when `backend == PICAMERA2` is correct.

### `src/rpi_camera_ensemble/utils/ttl/emitter.py`

**BUG: `PigpioTTLEmitter.close()` has inverted guard.**

`emitter.py:83-85`:
```python
def close(self) -> None:
    if getattr(self, "pi", None):
        return
```

This is inverted. When `self.pi` exists (truthy), the method returns immediately without cleaning up. When `self.pi` is `None`, it falls through to call `self.pi.wave_tx_stop()` which would raise `AttributeError`. The correct guard is `if not getattr(self, "pi", None): return`.

This is a bug in the deprecated `PigpioTTLEmitter` class, so it only affects users of the pigpio legacy backend. It means pigpio resources are never cleaned up on close. File:line: `emitter.py:83`.

Note: The `LgpioTTLEmitter.close()` at line 107 is correct (`if h is not None:`).

---

## 9. Open Issues

`gh issue list --repo MurineShiftWork/rpi-camera-ensemble-dev`: returned no results (empty, no issues).
`gh issue list --repo MurineShiftWork/rpi-camera-ensemble`: returned no results (no issues on the public-facing repo either).

No issues to address.

---

## 10. Git Log

```
5d402a9 bump: version 0.4.0 → 0.4.1
07f2d21 Merge pull request #2 from MurineShiftWork/ft/src-layout
3225dba fix(build): untrack src/_version.py (hatch-vcs generated, must not be tracked)
26ae861 fix: pre-commit lint
b4bf93d chore: move demo scripts and configs to examples/; add examples/README.md
1980d3d chore: publication cleanup — delete legacy files, sanitize sensitive content
a2c484b refactor: migrate to src/ layout; remove ipython from core deps
...
```

Log is clean. The bump commit `5d402a9` is the HEAD. The feature branch `ft/src-layout` was squash-merged via PR. No stray or wrong commits. The `_version.py` is tracked (it should not be — see commit `3225dba` which tried to untrack it). Verify it is in `.gitignore`.

**NOTE:** `src/rpi_camera_ensemble/_version.py` currently contains a dev version string `"0.4.1.dev3+gb4bf93d8c"` which was generated locally. This file should not be tracked in git (hatch-vcs regenerates it at build time). Confirm it is in `.gitignore` and not committed.

### NOTE: Two systemd service files with different content

`configs/rce-agent.service` and `scripts/rce-agent.service` are different files with overlapping purpose:

- `configs/rce-agent.service`: Clean, uses `/opt/rce/venv/bin/rce-agent`, no hardcoded usernames
- `scripts/rce-agent.service`: Has hardcoded `hypatia` username and development paths (`/home/hypatia/rce_data/agent.test.yaml`)

The `scripts/` file appears to be a development artifact that was not cleaned up. The `1980d3d` "publication cleanup" commit missed this. Before going public, either delete `scripts/rce-agent.service` or replace its content with a clean example.

**This is a minor embarrassment issue, not a security issue** (no credentials, just a personal username and path), but it looks unprofessional in a public repo.

### NOTE: CLAUDE.md documents old flat layout

`CLAUDE.md:25`: `"Package root: rpi_camera_ensemble/ (flat layout, no src/)"` — this is no longer accurate after the src/ migration. Update to reflect `src/rpi_camera_ensemble/`.

---

## Prioritized Action List

### Must fix before publishing (MINOR but user-facing)

1. **`examples/configs/ensemble.yaml:2` and `ensemble.session.yaml:2`** — change `max_recording_hours: 3.0` to `max_recording_duration_sec: 10800.0`

2. **All example `ttl:` blocks** — change `library: pigpio` to `library: lgpio`, add `gpiochip: 0` in `ensemble.yaml`, `ensemble.session.yaml`, `cameras.yaml` (all four agents)

3. **`examples/configs/conductor.yaml`** — change `max_acquisition_hours` to `max_recording_duration_sec: 10800.0`, remove `connection_timeout` and `retry_attempts`

4. **`CITATION.cff:6`** — update `version: "0.1.0"` to `version: "0.4.1"`

5. **`scripts/rce-agent.service`** — remove or replace with clean content (no `hypatia` username/path)

6. **`docs.yml:10`** — change `"rpi_camera_ensemble/**/*.py"` to `"src/rpi_camera_ensemble/**/*.py"`

7. **`mkdocs.yml`** — change `site_url` and `repo_url` from underscore to hyphen: `rpi-camera-ensemble`; fill in `site_author`

8. **`README.md: ## Output structure`** — correct file naming to actual `.rce.` convention and `.npz` extension

9. **`README.md: ## Deployment`** — fix link from `external/provision_rpi/` to `deploy/`

### Should fix soon after (cleanup)

10. **`pyproject.toml:47`** — update `fallback-version` from `"0.1.0"` to `"0.4.1"`

11. **`pyproject.toml:164-168` (ruff) and `177-188` (mypy)`** — remove stale `tests/barcode_ttl`, `tests/make_*.py`, etc. exclusions for files that no longer exist

12. **`pyproject.toml`** — add `python_version = "3.10"` to `[tool.mypy]`

13. **`pyproject.toml`** — add `typing_extensions; python_version < "3.11"` to core `dependencies`

14. **`CLAUDE.md:25`** — update layout description to src/ layout

15. **`docs/tutorial/rpi_config.md`** — remove `.inputrc` bash history config and `python3-ipython` install line

16. **`utils/ttl/emitter.py:83-85`** — fix inverted guard in `PigpioTTLEmitter.close()` (only affects pigpio legacy users)

### Good to have (notes only)

17. **README `## Development`** — change `pip install` to `uv sync`

18. **Add tutorial page** for `RCESession.from_directory()` and `validate_session()`

19. **README `## TTL synchronization`** YAML snippet — clarify where `ttl:` config lives in the config hierarchy

20. **Tests** — add coverage for `RCESession.summary()`, `SessionQC.print_report()`

---

## Templatepy Updates

Based on findings in this review, the following improvements should be made to `templatepy/template/pyproject.toml`:

1. **`fallback-version` wording** — the template uses `1.0.0` unconditionally. Consider a comment: `# Keep in sync with the most recent tag. Used when building outside a git context.`

2. **`[tool.mypy]`** — add `python_version = "[[ python_requires ]]"` (template currently has this — RCE repo just missed it)

3. **`pytest` addopts** — template has `--cov-report=term-missing --maxfail=5`; the RCE repo dropped these. No template change needed; RCE should adopt them.

4. **ruff `lint.select`** — template includes `"TCH"` (type-checking imports) and `"PYI"` (pyi stubs) and `"YTT"` (2020 checks) that are missing from RCE's ruff config. Consider whether these should be in the template or kept optional.

5. **`docs.yml` trigger paths** — templatepy should include both `"docs/**"` and `"src/[[ project_slug ]]/**/*.py"` as trigger paths (with the `src/` prefix), since the src layout is now standard.

---

*Generated by automated review. Verify all file:line references before applying fixes.*
