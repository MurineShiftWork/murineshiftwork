# Org migration + release-readiness tracker

Consolidates: GitHub transfer to `MurineShiftWork`, PyPI OIDC re-registration, Zenodo
re-linking, and remaining templatepy compliance gaps across all repos.

See `PLAN_github_org_migration.md` for step-by-step HOW-TO.
See `BUILD_SYSTEM_STANDARD.md` for template standard reference.

Last audited: 2026-05-27.

---

## Key findings from audit

**Good news — many gaps from earlier plans have already been closed:**
- All `external/` Python repos (except `one-axis-stage`, `rfid-to-url`) now have
  `src/` layout, `py.typed`, `VERSION`, and `version_provider = "commitizen"`
- `msw-flir-bonsai`, `acquisition-namespace`, `msw-open-ephys` are hatchling + src/ compliant
- `msw-flir-bonsai` and `acquisition-namespace` are fully v0.5.0-compliant including `uv publish` OIDC
- `murineshiftwork` main has `py.typed`, `CITATION.cff`, `release.yml` with OIDC
- Remotes now set for `acquisition-namespace`, `msw-flir-bonsai` (ext), `ttl-barcoder`

**Remaining gaps:**
- No repos transferred to org yet (all external/ and murineshiftwork main still under `larsrollik/`)
- `acquisition-namespace` GitHub repo does not exist yet → **blocks opto PR CI** (PyPI dep missing)
- `rfid-to-url` and `msw-open-ephys` have **wrong remote** → `larsrollik/murineshiftwork`
- `msw-open-ephys`: package restructured (hatchling, src/, py.typed) but **no CI workflows added** yet
- `rpi_camera_ensemble`: under org (private, 5 commits ahead of remote), still setuptools + flat layout — build system migration pending
- Suite repos (`msw-agent`, `msw-namespace`, `msw-tasks`, `msw-server`) have `name = "templatepy"`
  in pyproject.toml and use setuptools — full overhaul needed
- `murineshiftwork` main `ci.yml`: gitleaks secrets-scan job needs `pull-requests: write` permission (crashes on PR events)

---

## Table 1 — GitHub migration

`x` = action needed. `✓` = done. `—` = not applicable.

### murineshiftwork (main)

| Repo | Current remote | `gh-xfer` | `remote-set` | `copier-user` | `url-sync` | `pypi-oidc` | `zenodo-on` | `zenodo-doi` | `gh-pages` | `branch-prot` |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **murineshiftwork** | `larsrollik/murineshiftwork` | x | x | x | x | x | x | x | x | x |

### external/

| Repo | Current remote | `gh-xfer` | `remote-set` | `copier-user` | `url-sync` | `pypi-oidc` | `zenodo-on` | `zenodo-doi` | `gh-pages` | `branch-prot` |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **acquisition-namespace** | `murineshiftwork/acquisition-namespace` (repo not created yet) | x | ✓ | x | x | x | x | x | x | x |
| **msw-flir-bonsai** | `murineshiftwork/msw-flir-bonsai` | x | ✓ | x | x | x | x | x | x | x |
| **msw-open-ephys** ¹ | ⚠️ wrong → `larsrollik/murineshiftwork` | x | x | x | x | x | x | x | x | x |
| **one-axis-stage** | `larsrollik/one-axis-stage` | x | x | x | x | x | x | x | x | x |
| **pypulsepal** | `larsrollik/pypulsepal` | x | x | x | x | x | ⚡ relink | ✓ DOI exists | x | x |
| **rfid-to-url** | ⚠️ wrong → `larsrollik/murineshiftwork` | x | x | — | x | x | x | x | x | x |
| **serial-scale-bench** | `larsrollik/serial-scale-bench` | x | x | x | x | x | x | x | x | x |
| **serial-scale-hx711** | `larsrollik/serial-scale-hx711` | x | x | x | x | x | x | x | x | x |
| **ttl-barcoder** | `murineshiftwork/ttl-barcoder` | x | ✓ | x | x | x | x | x | x | x |

¹ `msw-open-ephys` (was `oe-remote`) now lives at `external/msw-open-ephys/` as a standalone git
  repo with hatchling + src/ layout, but has **no `.github/` workflows yet** — `copier apply` needed.
  Remote still wrong (points to main murineshiftwork repo).

### standalone / not in external/

| Repo | Current remote | `gh-xfer` | `remote-set` | `copier-user` | `url-sync` | `pypi-oidc` | `zenodo-on` | `zenodo-doi` | `gh-pages` | `branch-prot` |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **rpi_camera_ensemble** ² | `MurineShiftWork/rpi_camera_ensemble` (private, 5 commits ahead) | ✓ | ✓ | x | x | x | x | x | x | x |

² `rpi_camera_ensemble` at `/home/tars/code/rpi_camera_ensemble/`. GitHub repo exists (private).
  Still setuptools + flat layout — full build system migration required before first release.

### murineshiftwork_suite/

| Repo | Current remote | `gh-xfer` | `remote-set` | `copier-user` | `url-sync` | `pypi-oidc` | `zenodo-on` | `zenodo-doi` | `gh-pages` | `branch-prot` |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| msw-agent | `MurineShiftWork/msw-agent` | ✓ | ✓ | x | x | x | x | x | x | x |
| msw-flir-bonsai | `MurineShiftWork/msw-flir-bonsai` | ✓ | ✓ | x | x | x | x | x | x | x |
| msw-interface | `MurineShiftWork/msw-interface` | ✓ | ✓ | x | x | — | — | — | x | x |
| msw-namespace | `MurineShiftWork/msw-namespace` | ✓ | ✓ | x | x | x | x | x | x | x |
| msw-server | `MurineShiftWork/msw-server` | ✓ | ✓ | x | x | x | x | x | x | x |
| msw-tasks | `MurineShiftWork/msw-tasks` | ✓ | ✓ | x | x | x | x | x | x | x |
| msw-ui | `MurineShiftWork/msw-ui` | ✓ | ✓ | — | — | — | — | — | — | x |

### Column legend

| Column | What to do |
|---|---|
| `gh-xfer` | GitHub → repo Settings → Danger Zone → Transfer to `murineshiftwork` org |
| `remote-set` | `git remote set-url origin git@github.com:MurineShiftWork/<repo>.git` |
| `copier-user` | Edit `.copier-answers.yml`: `github_username: MurineShiftWork`; then run `copier update` |
| `url-sync` | Update `CITATION.cff` → `repository-code`; `mkdocs.yml` → `repo_url` + `site_url` |
| `pypi-oidc` | pypi.org → project → Publishing → add publisher: owner=`MurineShiftWork`, workflow=`release.yml` |
| `zenodo-on` | zenodo.org → account → GitHub → toggle repo ON (appears under org after transfer) |
| `zenodo-doi` | After first Zenodo release: copy concept DOI → `CITATION.cff` identifiers + README badge |
| `gh-pages` | Settings → Pages → Deploy from `gh-pages` branch (auto-created by `docs.yml` on first push) |
| `branch-prot` | Settings → Branches → protect `main`: require `CI` status check; allow `github-actions[bot]` bypass |

### Migration notes

- **pypulsepal `zenodo-on`**: concept DOI `10.5281/zenodo.6379627` already exists. After transfer,
  log into Zenodo via GitHub OAuth and verify the repo is still toggled ON under the org.
- **Wrong remotes**: `rfid-to-url` and `msw-open-ephys` both still point to
  `larsrollik/murineshiftwork` — fix these before doing anything else with those repos.
- **acquisition-namespace GitHub repo not yet created**: remote URL is set locally to
  `murineshiftwork/acquisition-namespace` but the GitHub repo does not exist. Create it directly
  under the org (no transfer needed), push, tag v1.0.0, set up PyPI OIDC → publish to PyPI.
  **Urgent: this blocks the opto PR CI.**
- **msw-open-ephys needs CI workflows**: package code is done (hatchling, src/, py.typed, VERSION)
  but `.github/` was never added. Run `copier apply` to add ci.yml + release.yml; fix remote first.
- **rpi_camera_ensemble**: repo is already private under org; 5 commits not yet pushed; needs full
  build system migration (setuptools → hatchling, src/ layout, VERSION) before first public release.
  Do after opto PR merges.
- **PyPI OIDC**: `pypa/gh-action-pypi-publish` (used by main, serial-scale-*, pypulsepal,
  ttl-barcoder) supports OIDC via `id-token: write` — no workflow change needed after transfer,
  just re-register the publisher under the org name on pypi.org.
- **Transfer order**: pypulsepal and ttl-barcoder first (standalone); murineshiftwork second
  (depends on those); serial-scale-* and remaining external repos after.

---

## Table 2 — Template / workflow compliance

`x` = action needed. `✓` = done. `—` = not applicable.

### murineshiftwork (main)

| Repo | `copier-apply` | `ci-rename` | `ci-gitleaks` | `pr-review` | `py-typed` | `src-layout` | `version-cz` | Priority |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **murineshiftwork** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |

### external/

| Repo | `copier-apply` | `ci-rename` | `ci-gitleaks` | `pr-review` | `py-typed` | `src-layout` | `version-cz` | Priority |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **acquisition-namespace** | ✓ v0.5.0 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **msw-flir-bonsai** | ✓ v0.5.0 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **msw-open-ephys** ³ | fresh apply (no .copier-answers.yml) | x (no CI at all) | x | x | ✓ | ✓ | ✓ | high |
| **one-axis-stage** | fresh apply | x | x | x | x | x | x | medium |
| **pypulsepal** | update v0.4.1→v0.5.0 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **rfid-to-url** | fresh apply | x | x | x | x | x | x | medium |
| **serial-scale-bench** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **serial-scale-hx711** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **ttl-barcoder** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |

### standalone / not in external/

| Repo | `copier-apply` | `ci-rename` | `ci-gitleaks` | `pr-review` | `py-typed` | `src-layout` | `version-cz` | Priority |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **rpi_camera_ensemble** | fresh apply | x (old 3-file set) | x | x | x | x (flat) | x | high |

³ `msw-open-ephys` package was restructured (hatchling, src/, py.typed, VERSION=3.0.0) but no
  `.github/` directory was added. `copier apply` will add ci.yml, release.yml, docs.yml, pr-review.yml
  in one shot. Needs correct remote set first.

### murineshiftwork_suite/

| Repo | `copier-apply` | `ci-rename` | `ci-gitleaks` | `pr-review` | `py-typed` | `src-layout` | `version-cz` | Priority |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| msw-agent | fresh apply | x | x | x | x | ? | x | high |
| msw-flir-bonsai | fresh apply | x | x | x | x | ? | x | high |
| msw-interface | fresh apply | x | x | x | x | ? | x | high |
| msw-namespace | fresh apply | x | x | x | x | ? | x | high |
| msw-server | fresh apply | x | x | x | x | ? | x | high |
| msw-tasks | fresh apply | x | x | x | x | ? | x | high |
| msw-ui | — | — | — | — | — | — | — | JS only |

### Column legend

| Column | What to do |
|---|---|
| `copier-apply` | `copier update` (if `.copier-answers.yml` exists) or `copier copy gh:larsrollik/templatepy` for fresh apply |
| `ci-rename` | Rename `CI.yaml` → `ci.yml` (matches templatepy convention) |
| `ci-gitleaks` | Replace `secret-scanner` step with `gitleaks/gitleaks-action@v2`; add `.gitleaks.toml` if absent |
| `pr-review` | Copy `.github/workflows/pr-review.yml` from templatepy v0.5.0 |
| `py-typed` | `touch src/<pkg>/py.typed`; add to pyproject.toml sdist includes |
| `src-layout` | Move `<pkg>/` → `src/<pkg>/`; update pyproject.toml package path |
| `version-cz` | Add `VERSION` file; set `version_provider = "commitizen"` + `version_files = ["VERSION"]` |

### Compliance notes

**CI.yaml rename — done (2026-05-25):** All four repos (`murineshiftwork`, `serial-scale-bench`,
`serial-scale-hx711`, `ttl-barcoder`) renamed to `ci.yml`; `secret-scanner` replaced with
`gitleaks/gitleaks-action@v2`; `pr-review.yml` added to all five repos including `pypulsepal`.

**murineshiftwork main CI gitleaks bug:** `ci.yml` `secrets-scan` job crashes on PR events with
`RequestError` — needs `pull-requests: write` in that job's permissions block (or
`GITLEAKS_ENABLE_COMMENTS: false` env var). Fix before merging opto PR.

**Suite repos — package name bug:** `msw-agent`, `msw-namespace`, `msw-tasks`, `msw-server` still have
`name = "templatepy"` in `pyproject.toml`. Fix this before any PyPI publish. Also: build backend is
`setuptools>=42` throughout — migrate to `hatchling + hatch-vcs` as part of `copier` fresh apply.

**msw-open-ephys CI steps** (package code done, workflows not added yet):
1. Fix remote: `git remote set-url origin git@github.com:MurineShiftWork/msw-open-ephys.git`
2. Create GitHub repo `MurineShiftWork/msw-open-ephys`; push
3. Run `copier copy gh:larsrollik/templatepy` (fresh apply — no .copier-answers.yml) — review diff,
   keep existing pyproject.toml/src, adopt ci.yml + release.yml + docs.yml + pr-review.yml
4. Set up PyPI OIDC (project name `msw-open-ephys`); enable Zenodo webhook

**rpi_camera_ensemble build system migration** (do after opto PR merges):
1. Push 5 pending commits: `git push -u origin main`
2. Apply copier template: adopt ci.yml + release.yml; migrate pyproject.toml to hatchling + hatch-vcs
3. Move `rpi_camera_ensemble/` → `src/rpi_camera_ensemble/`; add `py.typed`; add `VERSION` file
4. Make repo public; set up PyPI OIDC + Zenodo; enable branch protection

---

## Local git commands (post-transfer)

```bash
# murineshiftwork (main)
git -C /mnt/maindata/code/murineshiftwork \
    remote set-url origin git@github.com:MurineShiftWork/murineshiftwork.git

# external/ — repos with existing remotes (set after transfer)
git -C /mnt/maindata/code/murineshiftwork/external/pypulsepal \
    remote set-url origin git@github.com:MurineShiftWork/pypulsepal.git
git -C /mnt/maindata/code/murineshiftwork/external/serial_scale_bench \
    remote set-url origin git@github.com:MurineShiftWork/serial-scale-bench.git
git -C /mnt/maindata/code/murineshiftwork/external/serial_scale_hx711 \
    remote set-url origin git@github.com:MurineShiftWork/serial-scale-hx711.git
git -C /mnt/maindata/code/murineshiftwork/external/one-axis-stage \
    remote set-url origin git@github.com:MurineShiftWork/one-axis-stage.git

# external/ — wrong remotes (fix immediately, before any push)
git -C /mnt/maindata/code/murineshiftwork/external/rfid-to-url \
    remote set-url origin git@github.com:MurineShiftWork/rfid-to-url.git
git -C /mnt/maindata/code/murineshiftwork/external/msw-open-ephys \
    remote set-url origin git@github.com:MurineShiftWork/msw-open-ephys.git

# external/ — remote already set to org URL (✓), no action needed after creation:
#   acquisition-namespace → murineshiftwork/acquisition-namespace
#   msw-flir-bonsai       → murineshiftwork/msw-flir-bonsai
#   ttl-barcoder          → murineshiftwork/ttl-barcoder
```
