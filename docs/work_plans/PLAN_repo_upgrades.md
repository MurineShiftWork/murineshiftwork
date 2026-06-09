# Repo Upgrade Plan
Last updated: 2026-05-27

Audited against the "Legacy repo upgrade checklist" in `docs/work_plans/BUILD_SYSTEM_STANDARD.md`.
Repos live under `/mnt/maindata/code/murineshiftwork/` (main) and `external/` (sub-repos).

---

## Summary table

| Repo | Priority | Key gaps |
|---|---|---|
| `murineshiftwork` (main) | High | No `release.yml`, no `docs.yml`, no `CITATION.cff`, no `py.typed`, no `Documentation` URL, no `site_url` in mkdocs.yml, docs+dev extras merged, `version_provider` missing, `CITATION.cff`/`VERSION` not in sdist, CI jobs lack bump-skip |
| `pypulsepal` | Done | All toolchain gaps fixed; org URLs updated 2026-05-27. Manual: org transfer, Zenodo verify, Pages verify |
| `ttl-barcoder` | Done | Up to standard as of 2026-05-19; dir renamed + gitleaks permission fixed 2026-05-27 |
| `msw-flir-bonsai` | High | Flat layout (no `src/`), no `VERSION`, no `CITATION.cff`, no `mkdocs.yml`, no `docs.yml`, no `release.yml`, no `py.typed`, `commitizen` uses `version_provider="scm"` + `tag_only` (not the standard pattern), CI lacks bump-skip |
| `serial_scale_bench` | Medium | Flat layout (no `src/`), no `VERSION`, no `CITATION.cff`, no `mkdocs.yml`, no `docs.yml`, no `release.yml`, no `py.typed`, `commitizen` uses `version_provider="scm"` + `tag_only`, CI lacks bump-skip |
| `serial_scale_hx711` | Medium | Flat layout (no `src/`), no `VERSION`, no `CITATION.cff`, no `mkdocs.yml`, no `docs.yml`, no `release.yml`, no `py.typed`, `commitizen` uses `version_provider="scm"` + `tag_only`, CI lacks bump-skip |
| `one-axis-stage` | Low | Old setuptools build backend, bump2version+black toolchain (not ruff/commitizen/hatch), no `VERSION`, no `CITATION.cff`, no `mkdocs.yml`, no `src/` layout, no `release.yml`, pre-commit missing commitizen + gitleaks hooks |
| `rfid-to-url` | Low | Old setuptools build backend, bump2version+black toolchain, no `VERSION`, no `CITATION.cff`, no `mkdocs.yml`, no `src/` layout, no `release.yml`, pre-commit missing commitizen + gitleaks hooks |
| `msw-ui` | Low | Vue 3 / TypeScript — Python build standard does not apply. Lacks a `release.yml` / tag bump workflow. |
| `msw_open_ephys` | Low | Near-empty stub (only `oe_remote.egg-info` + a bare source tree, no `pyproject.toml`). Not yet a proper Python package. |
| `remote_python_manager` | Low | Not a Python package — only `__pycache__` present. Effectively empty. |
| `rpi_camera_ensemble` | High | setuptools backend, flat layout (no src/), no CI workflows, no GitHub repo; toolchain + pre-commit done 2026-05-26, commits pending |
| `provision_rpi` | N/A | Ansible playbook + RPi scripts — no Python build standard applies. |

---

## murineshiftwork (main repo)

### Status
Partially modernised. Has hatchling+hatch-vcs, commitizen, ruff, mypy, gitleaks, mkdocs. Missing several checklist items.

### Gaps (checklist items missing)

- **`release.yml` absent.** Has `bump.yaml` (tag-only, no PyPI publish or GitHub release) and separate `install_and_test.yaml`. Neither matches the canonical auto-bump `release.yml` pattern (cz bump → push → build → GitHub release → PyPI).
- **`docs.yml` absent.** MkDocs is configured (`mkdocs.yml` + `docs/index.md` exist) but there is no workflow to deploy to GitHub Pages.
- **`CITATION.cff` absent.** Not present at project root.
- **`src/murineshiftwork/py.typed` absent.** Makes mypy emit `import-untyped` in downstream packages.
- **`[project.urls]` missing `Documentation` key.** Only `Repository` and `Issue Tracker` are listed.
- **`mkdocs.yml` missing `site_url`.** Required for correct canonical URL generation by MkDocs Material.
- **`docs` not a separate optional-dependency group.** `mkdocs-material` and `mkdocs` are folded into the `dev` extra. Standard requires a dedicated `docs = ["mkdocs-material"]` extra.
- **`[tool.commitizen]` missing `version_provider = "commitizen"`.** Field is absent; without it commitizen falls back to its own internal default which may not match hatch-vcs behaviour.
- **`sdist` includes missing `CITATION.cff` and `VERSION`.** Only `/src`, `/tests`, `/README.md`, `/LICENSE`, `/pyproject.toml` are listed.
- **CI jobs (`CI.yaml`, `install_and_test.yaml`) lack bump-skip `if:`.** Neither file carries `if: "!startsWith(github.event.head_commit.message, 'bump:')"` on its jobs, so CI re-runs on every bump commit. The gate job in `CI.yaml` also does not accept `skipped` as a passing result.

### Manual steps (GitHub/PyPI — cannot verify locally)

- Enable GitHub Pages (Settings → Pages → Deploy from `gh-pages` branch) once `docs.yml` is added.
- Set up PyPI Trusted Publisher once `release.yml` is added (project: `murineshiftwork`, workflow: `release.yml`).
- Enable Zenodo webhook once `CITATION.cff` is added; add concept DOI to `CITATION.cff` and README after first archive.
- Branch protection: require `CI` status check; allow `github-actions[bot]` to bypass.

### Notes

Main repo requires-python is `>=3.12` so the test matrix only needs 3.12. The Python matrix gap is not applicable here (3.12-only is intentional).
The `bump.yaml` pattern uses `continue-on-error: true` (implicit via `|| [ $? -eq 3 ]` exit-code handling) and pushes tags only — it does not build or publish. This is a functional gap vs the standard `release.yml`.

---

## pypulsepal

### Status
Well maintained. Has hatchling+hatch-vcs, commitizen with `version_provider="commitizen"`, standard pre-commit hooks (ruff, mypy, commitizen, gitleaks), `mkdocs.yml`, `docs/index.md`, `CITATION.cff` (Zenodo DOI present), `VERSION`, `release.yml` (uv build + uv publish), `docs.yml`. Several smaller items missing.

### Gaps (checklist items missing)

- **`src/pypulsepal/py.typed` absent.** Flat `src/pypulsepal/` layout exists but no `py.typed` marker.
- **`CITATION.cff` missing `version` field.** The file has DOI and author info but no `version:` key; required for Zenodo to display a version on the archived record.
- **`[project.urls]` missing `Documentation` key.** Only `Homepage` and `Issue Tracker` listed; standard requires `Documentation = "https://larsrollik.github.io/pypulsepal/"`.
- **No separate `docs` optional-dependency group.** `mkdocs-material` is inside `dev`; standard requires a split `docs = ["mkdocs-material"]` extra.
- **`CITATION.cff` and `VERSION` not in sdist `include` list.** Current sdist includes only `/src/pypulsepal`, `/tests`, `/README.md`, `/LICENSE`, `/pyproject.toml`.
- **CI (`ci.yml`) lacks bump-skip `if:` on jobs and gate does not accept `skipped`.** Jobs `lint`, `test`, `secrets-scan` have no `if: "!startsWith(..., 'bump:')"`. The gate job checks only for `success`, not `success || skipped`.
- **CI test job has no Python matrix.** Only tests on 3.12 despite `requires-python = ">=3.10"`.
- **`pytest --tb=short` not used.** Test command is `uv run pytest tests/ -v --no-header -q` with no `--tb=short`.

### Manual steps (GitHub/PyPI — cannot verify locally)

- PyPI Trusted Publisher already appears to be set up (release.yml uses `uv publish --trusted-publishing automatic`). Verify it is configured for `release.yml` (not `publish.yml`).
- Zenodo webhook: already has a DOI — confirm webhook is still active after any repo transfer.
- GitHub Pages: confirm it is enabled and deploying from the `gh-pages` branch.

### Notes

`pypulsepal` is the most complete external repo after `ttl_barcoder`. The `release.yml` uses the uv variant (preferred). The `docs.yml` also uses uv. Pre-commit hooks are up to date (gitleaks v8.30.0, mypy v2.1.0, ruff v0.15.14). Upgrades here are polish, not structural.

---

## ttl_barcoder

### Status
Done / up to standard. Brought up to the build standard in 2026-05-19.

### What is confirmed present

- `CI.yaml`: bump-skip on all jobs, gate accepts `skipped`, Python matrix 3.10/3.11/3.12, `pytest --tb=short`.
- `release.yml`: canonical pip/hatchling variant (cz bump → push → build → GitHub release → pypa/gh-action-pypi-publish).
- `docs.yml`: present, deploys MkDocs Material to GitHub Pages.
- `.pre-commit-config.yaml`: ruff, mypy, commitizen, gitleaks.
- `pyproject.toml`: hatchling+hatch-vcs, `[tool.commitizen] version_files=["VERSION"]`, separate `dev` and `docs` extras, `Documentation` URL in `[project.urls]`, `CITATION.cff`+`VERSION` in sdist includes.
- `VERSION` at project root.
- `src/ttl_barcoder/` layout.
- `src/ttl_barcoder/py.typed` present.
- `CITATION.cff` with `version` field.
- `mkdocs.yml` + `docs/index.md`.

### Remaining minor gaps

- `[tool.commitizen]` missing `version_provider = "commitizen"` — uses `version_files` only. Functionally equivalent for tag-based workflows but not strictly compliant. Low priority.
- `release.yml` uses `pypa/gh-action-pypi-publish@release/v1` (pip/hatchling variant); standard now recommends `uv publish --trusted-publishing automatic`. Functional but will need updating when migrating to uv across the board.

### Manual steps (GitHub/PyPI — cannot verify locally)

- PyPI Trusted Publisher: verify `release.yml` is the workflow name on pypi.org publisher config.
- Zenodo webhook: confirm enabled; add concept DOI to `CITATION.cff` after first release creates a record.
- GitHub Pages: confirm enabled and deploying from `gh-pages` branch.

---

## msw-flir-bonsai

### Status
Early-stage. Has hatchling+hatch-vcs, a pre-commit config (ruff, mypy, commitizen, gitleaks), and a split CI (`CI.yaml` + `bump.yaml` + `install_and_test.yaml`) but several structural and toolchain gaps remain.

### Gaps (checklist items missing)

- **Flat layout — no `src/` directory.** Package lives at `msw_flir_bonsai/` at repo root. Must be moved to `src/msw_flir_bonsai/` and `pyproject.toml` updated (`packages = ["src/msw_flir_bonsai"]`).
- **`py.typed` absent.** No `msw_flir_bonsai/py.typed` (would be `src/msw_flir_bonsai/py.typed` after migration).
- **`VERSION` file absent.** `[tool.commitizen]` uses `version_provider = "scm"` + `tag_only = true` (no VERSION file written on bump). Must switch to `version_provider = "commitizen"` + `version_files = ["VERSION"]`.
- **`CITATION.cff` absent.**
- **`mkdocs.yml` absent.** No docs site configured.
- **`docs/` absent.**
- **`release.yml` absent.** Has only `bump.yaml` (tag push, no build/publish) and `install_and_test.yaml`. No PyPI publish or GitHub release workflow.
- **`docs.yml` absent.**
- **CI jobs lack bump-skip `if:`.** `CI.yaml` jobs (`lint`, `secrets-scan`) have no `if: "!startsWith(..., 'bump:')"`. Gate also does not accept `skipped`.
- **No test job in `CI.yaml`.** `install_and_test.yaml` handles tests but is separate; `CI.yaml` has no test job and therefore no consolidated `CI` gate that covers both lint and test.
- **`pyproject.toml` missing `Documentation` URL.**
- **`pyproject.toml` missing separate `docs` extra.**
- **`pyproject.toml` sdist includes flat path `/msw_flir_bonsai` instead of `/src/msw_flir_bonsai`** (will need updating alongside the layout migration).
- **`uv sync --group dev` in CI** — uses `dependency-groups` (PEP 735 / uv-native) rather than `[project.optional-dependencies]`; standard requires `optional-dependencies`.

### Manual steps (GitHub/PyPI — cannot verify locally)

- Set up PyPI Trusted Publisher once `release.yml` is added.
- Enable Zenodo webhook once `CITATION.cff` is added.
- Enable GitHub Pages once `docs.yml` is added.

### Notes

`msw-flir-bonsai` is actively used for FLIR camera acquisition. The flat layout migration (`msw_flir_bonsai/` → `src/msw_flir_bonsai/`) is the highest-effort change — check that Bonsai XML workflow files (included as `artifacts`) are correctly discovered after migration.

---

## serial_scale_bench

### Status
Partial modernisation. Has hatchling+hatch-vcs, pre-commit (ruff, mypy, commitizen, gitleaks), and a split CI (`CI.yaml` + `bump.yaml` + `install_and_test.yaml`). Several structural and release gaps.

### Gaps (checklist items missing)

- **Flat layout — no `src/` directory.** Package lives at `serial_scale_bench/` at repo root.
- **`py.typed` absent.**
- **`VERSION` file absent.** `[tool.commitizen]` uses `version_provider = "scm"` + `tag_only = true`.
- **`CITATION.cff` absent.**
- **`mkdocs.yml` absent.**
- **`docs/` absent.**
- **`release.yml` absent.** Only `bump.yaml` (tag-only) + `install_and_test.yaml`.
- **`docs.yml` absent.**
- **CI jobs lack bump-skip `if:`.** `CI.yaml` lint + secrets-scan jobs have no bump-skip guard. Gate does not accept `skipped`.
- **No test job in `CI.yaml`.** Tests live in the separate `install_and_test.yaml` which is not gated.
- **`[project.urls]` missing `Documentation` key.**
- **No separate `docs` extra in `[project.optional-dependencies]`.**
- **`[tool.hatch.version]` missing `fallback-version`.** Standard includes `fallback-version = "0.1.0"`.
- **sdist includes flat path** — will need updating after layout migration.

### Manual steps (GitHub/PyPI — cannot verify locally)

- Set up PyPI Trusted Publisher once `release.yml` is added.
- Enable Zenodo webhook once `CITATION.cff` is added.
- Enable GitHub Pages once `docs.yml` is added.

### Notes

`serial_scale_bench` and `serial_scale_hx711` have near-identical toolchain gaps and should be upgraded together.

---

## serial_scale_hx711

### Status
Same structure as `serial_scale_bench` — partial modernisation with the same pattern of split workflows and missing release/docs infrastructure.

### Gaps (checklist items missing)

All items listed for `serial_scale_bench` apply identically:

- Flat layout — no `src/` directory.
- `py.typed` absent.
- `VERSION` file absent; `commitizen` uses `version_provider = "scm"` + `tag_only = true`.
- `CITATION.cff` absent.
- `mkdocs.yml` and `docs/` absent.
- `release.yml` and `docs.yml` absent.
- CI jobs lack bump-skip `if:` and gate does not accept `skipped`.
- No test job in `CI.yaml`.
- `[project.urls]` missing `Documentation` key.
- No separate `docs` extra.
- `[tool.hatch.version]` missing `fallback-version`.

### Manual steps (GitHub/PyPI — cannot verify locally)

- Set up PyPI Trusted Publisher once `release.yml` is added.
- Enable Zenodo webhook once `CITATION.cff` is added.
- Enable GitHub Pages once `docs.yml` is added.

---

## one-axis-stage

### Status
Legacy repo. Uses setuptools build backend, bump2version + black toolchain (not commitizen / ruff / hatchling). Pre-commit config has only ruff and mypy — no commitizen, no gitleaks, no pre-commit-hooks standard set. Workflows are custom (`pr-to-prod.yaml`, `pre-pr-checks.yaml`, `release-to-deploy.yaml`) and do not match the standard pattern.

### Gaps (checklist items missing)

- **Build backend: setuptools.** Must migrate to `hatchling` + `hatch-vcs`.
- **`[tool.commitizen]` absent.** Uses `bump2version` in dev extras; no commitizen configuration.
- **`VERSION` file absent.**
- **`CITATION.cff` absent.**
- **`mkdocs.yml` and `docs/` absent.**
- **Flat layout — no `src/` directory.**
- **`py.typed` absent.**
- **No `release.yml` matching standard pattern.** `release-to-deploy.yaml` exists but is not a standard cz-bump / build / publish workflow.
- **No `docs.yml`.**
- **`CI.yaml`-equivalent (`pre-pr-checks.yaml`) lacks bump-skip `if:` and `skipped` acceptance.** Uses bespoke gate with no standard CI status check name.
- **Pre-commit config missing commitizen and gitleaks hooks.** Only ruff + mypy.
- **Dev extras use `black` and `bump2version`** — must replace with `ruff` + `commitizen`.
- **`[project.urls]` missing `Documentation` key.**
- **No separate `docs` extra.**

### Manual steps (GitHub/PyPI — cannot verify locally)

- Set up PyPI Trusted Publisher after adding `release.yml`.
- Enable Zenodo webhook after adding `CITATION.cff`.
- Enable GitHub Pages after adding `docs.yml`.

### Notes

`one-axis-stage` has hardware firmware under `firmware/` — the upgrade only concerns the Python package; no firmware changes needed. This is the highest-effort external repo upgrade (full toolchain replacement). Recommend doing it with `copier copy gh:larsrollik/templatepy` onto a clean branch and cherry-picking `one_axis_stage/` source code back in.

---

## rfid-to-url

### Status
Same generation and toolchain as `one-axis-stage` — legacy setuptools + bump2version + black, bespoke workflow files, pre-commit with only ruff + mypy.

### Gaps (checklist items missing)

All items listed for `one-axis-stage` apply identically:

- Build backend: setuptools — migrate to hatchling + hatch-vcs.
- `[tool.commitizen]` absent; uses bump2version.
- `VERSION` file absent.
- `CITATION.cff` absent.
- `mkdocs.yml` and `docs/` absent.
- Flat layout — no `src/` directory.
- `py.typed` absent.
- No `release.yml` matching standard pattern.
- No `docs.yml`.
- Bespoke CI workflow, no bump-skip, no `skipped` acceptance.
- Pre-commit config missing commitizen and gitleaks.
- Dev extras use `black` and `bump2version`.
- `[project.urls]` missing `Documentation` key.
- No separate `docs` extra.

### Manual steps (GitHub/PyPI — cannot verify locally)

- Set up PyPI Trusted Publisher after adding `release.yml`.
- Enable Zenodo webhook after adding `CITATION.cff`.
- Enable GitHub Pages after adding `docs.yml`.

### Notes

`rfid-to-url` now lives under the `murineshiftwork` GitHub org (pyproject.toml shows `https://github.com/murineshiftwork/rfid-to-url`). Ensure the PyPI publisher is configured under the org repo, not a personal fork.

---

## msw-ui

### Status
Vue 3 / TypeScript frontend. Python build standard does not apply. Has `CI.yaml` (Node 20 lint + typecheck + build) and a `bump.yaml`. No `release.yml` for versioned releases.

### Gaps (checklist items missing or not applicable)

- **No `release.yml`.** `bump.yaml` does a tag bump but does not produce a GitHub release or publish a Docker image/npm package.
- Python-specific checklist items (pyproject.toml, py.typed, CITATION.cff, etc.) are not applicable.

### Notes

Upgrade scope here is limited: add a `release.yml` that creates a GitHub release on each version bump (could also trigger a Docker image build if/when containerised). The Node toolchain itself is fine.

---

## msw_open_ephys

### Status
Near-empty placeholder. The directory contains only `oe_remote/oe_remote/` (bare source tree with an `__init__.py` and `cli/` directory) plus `oe_remote.egg-info/` from a `setup.py` install (no `setup.py` is present in the checked-out tree). No `pyproject.toml`, no `VERSION`, no `CITATION.cff`, no workflows, no pre-commit config.

The `oe_remote.egg-info/PKG-INFO` shows `Name: oe-remote`, `Version: 3.0.0`, `Requires: requests` — so there was a working package at some point but the repo is missing its build files.

### Gaps (checklist items missing)

Essentially everything — this repo needs to be built from scratch as a proper Python package:

- `pyproject.toml` with hatchling + hatch-vcs.
- `[tool.commitizen]` configuration.
- `VERSION` file.
- `CITATION.cff`.
- `mkdocs.yml` + `docs/index.md`.
- `src/oe_remote/` layout (currently flat nested `oe_remote/oe_remote/`).
- `py.typed`.
- `.pre-commit-config.yaml`.
- All three standard workflows: `CI.yaml`, `release.yml`, `docs.yml`.

### Manual steps (GitHub/PyPI — cannot verify locally)

All manual steps (PyPI publisher, Zenodo, GitHub Pages) are blocked until the package is reconstituted.

### Notes

Recommend reconstituting with `copier copy gh:larsrollik/templatepy` and copying the existing source files into `src/oe_remote/`. Priority depends on whether `oe_remote` is actively used or has been superseded.

---

## remote_python_manager

### Status
Effectively empty — only a `__pycache__/` directory is present in the repo checkout. No Python source, no `pyproject.toml`, no README, no workflows. May be a stub placeholder or a repo whose files were never committed.

### Notes

No audit possible — no content to evaluate. Either populate with actual code or remove from `external/`. No checklist items apply.

---

## rpi_camera_ensemble

### Status
Partially upgraded 2026-05-26. Python package at `external/provision_rpi/rpi_camera_ensemble/` — its own git repo, not the `provision_rpi` Ansible repo. Pre-commit toolchain is now fully passing; build backend and layout not yet migrated.

### What is confirmed present (as of 2026-05-26)

- `.pre-commit-config.yaml`: pre-commit-hooks v6.0.0, ruff v0.15.14, mypy v2.1.0, commitizen v4.16.2, gitleaks v8.30.0 — all 10 hooks green.
- `pyproject.toml`: ruff B+N rules; per-file-ignores for FastAPI routers (B008), TTL/picamera2 hardware modules (B904/B905/N803); mypy v2.1.0 compatible with hardware-module `ignore_errors` overrides; commitizen conventional commits config.
- `VERSION` at project root (`0.0.0`).
- `rpi_camera_ensemble/py.typed` present.
- `CITATION.cff` with author, ORCID, license.
- `mkdocs.yml` updated with `site_url` and `repo_url` pointing to `murineshiftwork/rpi_camera_ensemble`.
- `MANIFEST.in` includes `VERSION` and `CITATION.cff`.

### Gaps (checklist items missing)

- **Build backend: setuptools.** Must migrate to `hatchling` + `hatch-vcs`.
- **Flat layout — no `src/` directory.** Deferred: many hardware test scripts and relative imports make this non-trivial. Do after GitHub repo is created.
- **No CI workflows.** No `CI.yaml`, `release.yml`, or `docs.yml`.
- **No GitHub repo yet.** Listed as manual action in ROADMAP.
- **`[project.urls]` missing `Documentation` key.**
- **No separate `docs` extra.** `mkdocs-material` not yet in optional-dependencies.
- **Commits not yet made.** Three commits planned as of 2026-05-26:
  1. Pre-existing staged fixes (io/models.py `allow_pickle`, ttl/mixin.py empty-events fix, etc.)
  2. Toolchain files (.pre-commit-config.yaml, pyproject.toml, mkdocs.yml, MANIFEST.in, CITATION.cff, VERSION, py.typed)
  3. Pre-commit code fixes (B904/B905/B007/TC003/N805/E501 across source; test path cleanup → tests/data/)

### Manual steps (GitHub — cannot do locally)

- Create GitHub repo `murineshiftwork/rpi_camera_ensemble` and push.
- Set up PyPI Trusted Publisher once `release.yml` is added.
- Enable Zenodo webhook once `CITATION.cff` is pushed to GitHub.
- Enable GitHub Pages once `docs.yml` is added.

### Notes

`rpi_camera_ensemble` is the conductor+agent orchestration package for RPi camera rigs — used daily on the acquisition machine. The flat → `src/` layout migration is the main deferred item; it requires verifying the package is still importable on deployed RPis after restructure. Recommend doing it in one session using `copier update` or a manual restructure, after the GitHub repo is created and initial commits are in.

---

## provision_rpi

### Status
Ansible playbook repo — not a Python package. Contains `ansible.cfg`, `inventory.ini`, playbook scripts, and an `rpi_camera_ensemble/` tree (Raspberry Pi setup scripts). No `pyproject.toml`, no workflows, no Python build artefacts.

### Notes

Python build standard does not apply. No checklist items are relevant. The only possible improvement is adding a GitHub Actions workflow for Ansible linting (`ansible-lint`) if desired.

---

## Recommended upgrade order

| Step | Repos | Rationale |
|---|---|---|
| 1 | `pypulsepal` | Almost done; small delta, high usage, already has Zenodo DOI |
| 2 | `murineshiftwork` (main) | Highest impact; blocks PyPI publish and GitHub Pages for primary package |
| 3 | `serial_scale_bench` + `serial_scale_hx711` | Near-identical gap set; upgrade together |
| 4 | `rpi_camera_ensemble` | Toolchain done; needs GitHub repo, then setuptools→hatchling + src/ layout |
| 5 | `msw-flir-bonsai` | Actively used; flat layout migration is the blocker |
| 6 | `msw_open_ephys` | Needs reconstitution; priority depends on active use |
| 7 | `one-axis-stage` + `rfid-to-url` | Full toolchain replacement; lower urgency |
| 8 | `msw-ui` | Add `release.yml` only; minimal effort |
| — | `remote_python_manager`, `provision_rpi` | Not Python packages; out of scope |
