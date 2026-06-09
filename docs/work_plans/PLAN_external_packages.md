# External Package Build System Audit

Audit of all repos under `external/` against the build system standard defined in
`docs/work_plans/BUILD_SYSTEM_STANDARD.md`.

Date: 2026-05-23
Standard reference: `docs/work_plans/BUILD_SYSTEM_STANDARD.md`

---

## Repos in scope

| Repo dir | PyPI / package name | Language |
|---|---|---|
| `msw-flir-bonsai` | `msw-flir-bonsai` | Python |
| `msw-ui` | `msw-ui` | TypeScript / Vue 3 |
| `msw_open_ephys/oe_remote` | `oe-remote` | Python |
| `provision_rpi/rpi_camera_ensemble` | `rpi-camera-ensemble` | Python |
| `pypulsepal` | `pypulsepal` | Python |
| `remote_python_manager` | (no package, empty) | — |
| `rfid-to-url` | `rfid-to-url` | Python |
| `serial_scale_bench` | `serial-scale-bench` | Python |
| `serial_scale_hx711` | `serial-scale-hx711` | Python |
| `ttl_barcoder` | `ttl-barcoder` | Python |

`remote_python_manager` is a shell with only a `__pycache__` directory — nothing to audit.
`msw-ui` is a frontend (Vite + Vue 3 + TypeScript) and is out of scope for the Python standard.

---

## Per-repo status

### msw-flir-bonsai

| Check | Status |
|---|---|
| Build backend | hatchling + hatch-vcs |
| Version source | `dynamic = ["version"]`, `source = "vcs"` |
| `requires-python` | `>=3.10` |
| Commitizen config | `version_provider = "scm"`, `tag_only = true` — no VERSION file tracking |
| `VERSION` file | **Missing** |
| `setup.py` / `setup.cfg` | None |
| `.pre-commit-config.yaml` | Present; standard hook set (ruff, mypy, commitizen, gitleaks, pre-commit-hooks) |
| pre-commit hook revisions | ruff v0.9.0, mypy v1.14.0, gitleaks v8.24.3 — all current |
| mypy `additional_dependencies` | None — numpy type resolution may be missed |
| CI workflows | `CI.yaml` (lint + secrets-scan gate), `bump.yaml` (auto-bump on main push), `install_and_test.yaml` (matrix 3.10/3.11/3.12) |
| CI install method | `CI.yaml` uses `uv sync --group dev`; `install_and_test.yaml` uses `pip install .[dev]` — inconsistent |
| Release workflow | **Missing** — bump.yaml pushes tags but no `release.yml` exists |
| `GITHUB_TOKEN` on checkout | **Missing** from `CI.yaml` checkout steps |

**Gaps:**
- [ ] Add `VERSION` file (standard requires it; `tag_only = true` does not write it)
- [ ] Add `release.yml` workflow (create GitHub release on `v*` tag)
- [ ] Standardise CI install method (pick uv or pip — not both)
- [ ] Add `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to checkout steps in `CI.yaml`
- [ ] Add `numpy` to mypy `additional_dependencies`

**Priority:** Medium

---

### pypulsepal

| Check | Status |
|---|---|
| Build backend | hatchling + hatch-vcs |
| Version source | `dynamic = ["version"]`, `source = "vcs"`, `fallback-version = "0.1.0"` |
| `requires-python` | `>=3.10` |
| Commitizen config | `version = "0.1.0"`, `tag_format = "v$version"`, `version_files = ["VERSION"]` |
| `VERSION` file | Present |
| `setup.py` / `setup.cfg` | None |
| `.pre-commit-config.yaml` | Present; standard hook set with `additional_dependencies: [pydantic>=2.0, pyserial, types-PyYAML]` |
| pre-commit hook revisions | ruff v0.9.0, mypy v1.14.0, gitleaks v8.24.3 — all current |
| CI workflows | `CI.yaml` (lint + test + secrets-scan gate), `release.yml` (tag → GitHub release + hatchling build) |
| CI install method | `pip install .[dev]` — consistent |
| `GITHUB_TOKEN` on checkout | Present on all steps |
| Release workflow | Present and correct |

**Gaps:**
- Old tags used no `v` prefix (`0.1.0`); documented in pyproject.toml. hatch-vcs handles both.
- Feature/API work tracked in `docs/work_plans/PLAN_pypulsepal.md` (separate from build system).

**Priority:** None — this is the reference implementation.

---

### rfid-to-url

| Check | Status |
|---|---|
| Build backend | **setuptools + wheel** (legacy) |
| Version source | **Hardcoded** `version = "0.0.2"` |
| `requires-python` | `>=3.10` |
| Commitizen config | **None** |
| `VERSION` file | **Missing** |
| `setup.py` | **Present** (redundant stub) |
| `MANIFEST.in` | **Present** (superseded by pyproject.toml sdist config) |
| `.pre-commit-config.yaml` | Present but **incomplete**: ruff + mypy only; missing pre-commit-hooks, commitizen, gitleaks |
| pre-commit hook revisions | ruff v0.8.3 (old), mypy v1.13.0 (old) |
| CI workflows | `pre-pr-checks.yaml`, `pr-to-prod.yaml`, `release-to-deploy.yaml` |
| CI release | Calls `python setup.py sdist bdist_wheel` + `twine upload` — deprecated build path |
| `GITHUB_TOKEN` on checkout | Missing from `pre-pr-checks.yaml` |

**Gaps (full migration):**
- [ ] Migrate build backend: setuptools → hatchling + hatch-vcs
- [ ] Replace hardcoded version with `dynamic = ["version"]`
- [ ] Add commitizen config + `VERSION` file
- [ ] Delete `setup.py`, `MANIFEST.in`
- [ ] Update `.pre-commit-config.yaml`: add pre-commit-hooks, commitizen, gitleaks; bump ruff → v0.9.0, mypy → v1.14.0
- [ ] Replace `release-to-deploy.yaml`: drop twine + setup.py, use hatchling + `actions/create-release`
- [ ] Add `GITHUB_TOKEN` to checkout steps; add aggregate gate job to `pre-pr-checks.yaml`

**Priority:** High

---

### provision_rpi / rpi_camera_ensemble

| Check | Status |
|---|---|
| Build backend | **setuptools + wheel** (legacy) |
| Version source | **Hardcoded** `version = "0.0.0.dev0"` |
| `requires-python` | `>=3.10` |
| Commitizen config | **None** |
| `VERSION` file | **Missing** |
| `setup.py` | **Present** (redundant stub) |
| `MANIFEST.in` | Present |
| `.pre-commit-config.yaml` | Present but **incomplete**: ruff + mypy only; missing pre-commit-hooks, commitizen, gitleaks |
| pre-commit hook revisions | ruff v0.8.3 (old), mypy v1.13.0 (old) |
| `[project.urls]` | **Stale**: points to `larsrollik/templatepy` (copy-paste artifact from template repo) |
| CI workflows | Same pattern as rfid-to-url — legacy twine release |

**Gaps (full migration):**
- [ ] Same full migration as rfid-to-url (build backend, version, commitizen, pre-commit hooks, CI)
- [ ] Fix stale `[project.urls]` pointing to `larsrollik/templatepy`
- [ ] Decide real starting version (`0.0.0.dev0` is not a meaningful release version)
- [ ] Clarify relationship between `provision_rpi/` Ansible scripts and the Python package before migration

**Priority:** Medium

---

### msw_open_ephys (oe_remote)

| Check | Status |
|---|---|
| Build backend | **Unknown** — no `pyproject.toml` or `setup.py` found in working tree |
| Package info | `oe-remote` v3.0.0 (from committed `.egg-info` artifact only) |
| CI / pre-commit | **None** |
| Source files | Working tree appears empty — only `.egg-info` artifact committed |

**Gaps:**
- [ ] Locate actual source files — `pyproject.toml`/`setup.py` may have been deleted or never committed
- [ ] Remove committed `.egg-info` directory (build artifact, should not be in VCS)
- [ ] Full migration once source is confirmed: build backend, version, commitizen, CI

**Priority:** Low (no active development)

---

### serial_scale_bench

| Check | Status |
|---|---|
| Build backend | hatchling + hatch-vcs |
| Version source | `dynamic = ["version"]`, `source = "vcs"` |
| `requires-python` | `>=3.10` |
| Commitizen config | `version_provider = "scm"`, `tag_only = true` |
| `VERSION` file | **Missing** |
| `.pre-commit-config.yaml` | Present; standard hook set, all current revisions |
| mypy `additional_dependencies` | None — pyserial types not resolved |
| CI workflows | `CI.yaml` (lint + secrets-scan, uv), `bump.yaml`, `install_and_test.yaml` (pip) |
| Release workflow | **Missing** |
| `GITHUB_TOKEN` on checkout | Missing from `CI.yaml` |

**Gaps:**
- [ ] Add `VERSION` file
- [ ] Add `release.yml` workflow
- [ ] Standardise CI install method (uv or pip, not both)
- [ ] Add `GITHUB_TOKEN` to checkout in `CI.yaml`
- [ ] Add `pyserial` to mypy `additional_dependencies`

**Priority:** Low

---

### serial_scale_hx711

Identical gaps to `serial_scale_bench`.

**Gaps:**
- [ ] Add `VERSION` file
- [ ] Add `release.yml` workflow
- [ ] Standardise CI install method
- [ ] Add `GITHUB_TOKEN` to checkout in `CI.yaml`

**Priority:** Low

---

### ttl_barcoder

Actively used in MSW barcode alignment pipeline. Build system upgrade in progress on branch
`ft/opto-hardware` — tracked in `docs/work_plans/PLAN_ttl_barcoder.md`.

**Priority:** High (handled separately)

---

## Summary matrix

| Repo | Backend | Dynamic version | VERSION | src/ layout | pre-commit OK | CI standard | Release workflow | Priority |
|---|---|---|---|---|---|---|---|---|
| msw-flir-bonsai | hatchling+vcs | yes | **no** | yes | yes | partial | **no** | Medium |
| pypulsepal | hatchling+vcs | yes | yes | yes | yes | yes | yes | — (reference) |
| rfid-to-url | **setuptools** | **no** | **no** | flat | **partial** | **non-standard** | **legacy twine** | **High** |
| rpi_camera_ensemble | **setuptools** | **no** | **no** | flat | **partial** | **non-standard** | **legacy twine** | Medium |
| msw_open_ephys | **unknown** | **unknown** | **unknown** | unknown | **none** | **none** | **none** | Low |
| serial_scale_bench | hatchling+vcs | yes | **no** | yes | yes | partial | **no** | Low |
| serial_scale_hx711 | hatchling+vcs | yes | **no** | yes | yes | partial | **no** | Low |
| ttl_barcoder | → hatchling+vcs | → yes | → yes | → src/ | → standard | → CI.yaml | → release.yml | High (in progress) |

---

## Ordered action list

### Priority 1 — rfid-to-url (full legacy migration)

1. Migrate `pyproject.toml`: setuptools → hatchling + hatch-vcs, `dynamic = ["version"]`
2. Add `[tool.commitizen]` config, add `VERSION` file (content = current release version)
3. Delete `setup.py`, `MANIFEST.in`
4. Update `.pre-commit-config.yaml`: add pre-commit-hooks, commitizen (commit-msg stage), gitleaks; bump ruff → v0.9.0, mypy → v1.14.0
5. Replace `release-to-deploy.yaml`: drop twine + setup.py, use hatchling build + `actions/create-release@v1`
6. Add `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to all checkout steps
7. Add aggregate `ci` gate job

### Priority 2 — msw-flir-bonsai (minor gaps)

1. Add `VERSION` file
2. Add `release.yml` (copy from pypulsepal)
3. Standardise CI on uv or pip
4. Add `GITHUB_TOKEN` to checkout in `CI.yaml`
5. Add `numpy` to mypy `additional_dependencies`

### Priority 3 — rpi_camera_ensemble (full legacy migration)

1. Decide real starting version
2. Same migration steps as rfid-to-url
3. Fix `[project.urls]` (remove templatepy reference)
4. Clarify `provision_rpi/` repo boundary before migrating

### Priority 4 — serial_scale_bench + serial_scale_hx711 (minor gaps, identical)

For each:
1. Add `VERSION` file
2. Add `release.yml`
3. Standardise CI install method
4. Add `GITHUB_TOKEN` to `CI.yaml` checkout
5. Add `pyserial` to mypy `additional_dependencies`

### Priority 5 — msw_open_ephys

1. Audit working tree — locate source files
2. Remove committed `.egg-info`
3. Full migration once source is confirmed

---

## Notes on the standard

- `tag_only = true` in commitizen (msw-flir-bonsai, serial_scale_bench, serial_scale_hx711) means `cz bump` does not write `VERSION`. The standard requires a VERSION file. Either add `version_files = ["VERSION"]` (and drop `tag_only`) or document as an explicit exemption. pypulsepal uses the full pattern correctly.
- The `bump.yaml` auto-bump workflow is not in the BUILD_SYSTEM_STANDARD template. Not wrong, but it creates bot commits on every main push — decide per repo if that is desired.
