# Org migration + release-readiness tracker

Consolidates: GitHub transfer to `MurineShiftWork`, PyPI OIDC re-registration, Zenodo
re-linking, and remaining templatepy compliance gaps across all repos.

See `PLAN_github_org_migration.md` for step-by-step HOW-TO.
See `BUILD_SYSTEM_STANDARD.md` for template standard reference.

Last audited: 2026-05-25.

---

## Key findings from audit

**Good news — many gaps from earlier plans have already been closed:**
- All `external/` Python repos (except `oe-remote`, `one-axis-stage`, `rfid-to-url`) now have
  `src/` layout, `py.typed`, `VERSION`, and `version_provider = "commitizen"`
- `msw-flir-bonsai` and `acquisition-namespace` are fully v0.5.0-compliant including `uv publish` OIDC
- `murineshiftwork` main has `py.typed`, `CITATION.cff`, `release.yml` with OIDC

**Remaining gaps:**
- No repos transferred to org yet
- 4 repos use `CI.yaml` (capital) + old `secret-scanner` → rename + replace with `gitleaks`
- 5 repos missing `pr-review.yml`
- `rfid-to-url` and `msw_open_ephys` have **wrong remote** → `larsrollik/murineshiftwork`
- 3 repos have no remote set locally: `acquisition-namespace`, `msw-flir-bonsai` (ext), `ttl-barcoder`
- `oe-remote` (`external/msw_open_ephys/oe_remote/`) is **not a standalone git repo** — nested
  subdirectory, legacy setuptools + setup.cfg, needs extraction and full overhaul
- Suite repos (`msw-agent`, `msw-namespace`, `msw-tasks`, `msw-server`) have `name = "templatepy"`
  in pyproject.toml and use setuptools — full overhaul needed

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
| **acquisition-namespace** | none (not set) | x | x | x | x | x | x | x | x | x |
| **msw-flir-bonsai** | none (not set) | x | x | x | x | x | x | x | x | x |
| **oe-remote** ¹ | ⚠️ wrong → `larsrollik/murineshiftwork` | x | x | — | x | x | x | x | x | x |
| **one-axis-stage** | `larsrollik/one-axis-stage` | x | x | x | x | x | x | x | x | x |
| **pypulsepal** | `larsrollik/pypulsepal` | x | x | x | x | x | ⚡ relink | ✓ DOI exists | x | x |
| **rfid-to-url** | ⚠️ wrong → `larsrollik/murineshiftwork` | x | x | — | x | x | x | x | x | x |
| **serial-scale-bench** | `larsrollik/serial-scale-bench` | x | x | x | x | x | x | x | x | x |
| **serial-scale-hx711** | `larsrollik/serial-scale-hx711` | x | x | x | x | x | x | x | x | x |
| **ttl-barcoder** | none (not set) | x | x | x | x | x | x | x | x | x |

¹ `oe-remote` lives at `external/msw_open_ephys/oe_remote/` — not yet a standalone git repo.
  Must be extracted first (see compliance table notes). `copier-user` not applicable until it has
  its own `.copier-answers.yml`.

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
- **Wrong remotes**: `rfid-to-url` and `msw_open_ephys` (parent of `oe-remote`) both point to
  `larsrollik/murineshiftwork` — fix these before doing anything else with those repos.
- **No-remote repos**: `acquisition-namespace`, `msw-flir-bonsai` (ext), `ttl-barcoder` have no
  remote set locally. Check whether the GitHub repos exist under `larsrollik/` first; if yes,
  transfer then `git remote add`; if not, create under the org directly.
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
| **oe-remote** ² | fresh apply | x | x | x | x | x | x | high |
| **one-axis-stage** | fresh apply | x | x | x | x | x | x | medium |
| **pypulsepal** | update v0.4.2→v0.5.0 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **rfid-to-url** | fresh apply | x | x | x | x | x | x | medium |
| **serial-scale-bench** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **serial-scale-hx711** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |
| **ttl-barcoder** | update | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | done |

² `oe-remote` must be extracted from `external/msw_open_ephys/oe_remote/` into its own git repo
  before copier can be applied.

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

**Suite repos — package name bug:** `msw-agent`, `msw-namespace`, `msw-tasks`, `msw-server` still have
`name = "templatepy"` in `pyproject.toml`. Fix this before any PyPI publish. Also: build backend is
`setuptools>=42` throughout — migrate to `hatchling + hatch-vcs` as part of `copier` fresh apply.

**oe-remote extraction steps:**
1. Create a new git repo at `external/msw_open_ephys/oe_remote/` (or move source out to `external/oe-remote/`)
2. Run `copier copy gh:larsrollik/templatepy` into the new repo root
3. Copy source from `oe_remote/oe_remote/` → `src/oe_remote/`
4. Migrate `setup.cfg` → `pyproject.toml` (name=`oe-remote`, entry point=`oe-remote`)
5. Create GitHub repo under `MurineShiftWork/oe-remote`; push; set up PyPI OIDC + Zenodo

---

## Local git commands (post-transfer)

```bash
# murineshiftwork (main)
git -C /mnt/maindata/code/murineshiftwork \
    remote set-url origin git@github.com:MurineShiftWork/murineshiftwork.git

# external/ — repos with existing remotes
git -C /mnt/maindata/code/murineshiftwork/external/pypulsepal \
    remote set-url origin git@github.com:MurineShiftWork/pypulsepal.git
git -C /mnt/maindata/code/murineshiftwork/external/serial_scale_bench \
    remote set-url origin git@github.com:MurineShiftWork/serial-scale-bench.git
git -C /mnt/maindata/code/murineshiftwork/external/serial_scale_hx711 \
    remote set-url origin git@github.com:MurineShiftWork/serial-scale-hx711.git
git -C /mnt/maindata/code/murineshiftwork/external/one-axis-stage \
    remote set-url origin git@github.com:MurineShiftWork/one-axis-stage.git

# external/ — wrong remotes (fix immediately)
git -C /mnt/maindata/code/murineshiftwork/external/rfid-to-url \
    remote set-url origin git@github.com:MurineShiftWork/rfid-to-url.git
git -C /mnt/maindata/code/murineshiftwork/external/msw_open_ephys \
    remote set-url origin git@github.com:MurineShiftWork/msw-open-ephys.git

# external/ — no remote set (add after verifying/creating GitHub repo)
git -C /mnt/maindata/code/murineshiftwork/external/ttl_barcoder \
    remote add origin git@github.com:MurineShiftWork/ttl-barcoder.git
git -C /mnt/maindata/code/murineshiftwork/external/acquisition-namespace \
    remote add origin git@github.com:MurineShiftWork/acquisition-namespace.git
git -C /mnt/maindata/code/murineshiftwork/external/msw-flir-bonsai \
    remote add origin git@github.com:MurineShiftWork/msw-flir-bonsai.git
```
