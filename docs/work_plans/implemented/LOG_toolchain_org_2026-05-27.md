# Toolchain + org homogenisation — session log 2026-05-27

Session covering CI/release/docs workflow homogenisation across all published
external packages, org rename cleanup, and documentation build-out.

---

## Completed

### Repo renames (org cleanup)
- Old `msw-*` and `murineshiftwork` legacy suite repos renamed to `*-archive`
  to free namespace for new canonical names
- `msw-flir-bonsai` (old monolith) → `msw-flir-bonsai-archive`
- New `murineshiftwork/msw-flir-bonsai` created (private; push pending)
- Local remotes updated to match renamed repos

### CI workflow homogenisation (all 4 external published repos)
Gold standard established in `acquisition-namespace`; applied to all:

| Repo | ci.yml | release.yml | docs.yml | pr-review.yml |
|---|:---:|:---:|:---:|:---:|
| acquisition-namespace | ✓ | ✓ | ✓ | ✓ |
| pypulsepal | ✓ | ✓ | ✓ | ✓ |
| ttl-barcoder | ✓ (full rewrite) | ✓ (full rewrite) | ✓ (full rewrite) | ✓ |
| msw-flir-bonsai | ✓ | ✓ | ✓ | ✓ |

Key changes across all repos:
- `astral-sh/setup-uv@v5` replaces `actions/setup-python` + pip
- Test trigger: `github.event_name == 'pull_request'` (not push)
- `fail-fast: false`; Python 3.10 + 3.12 + 3.13
- `secrets-scan` job removed; gitleaks runs via pre-commit in lint job
- `ci` gate: `needs: [lint, test]`
- Release: `uvx --from commitizen cz bump` → `uv build` → `uv publish --trusted-publishing automatic`
- Docs: `uv sync --extra docs` → `uv run mkdocs gh-deploy --force`

### gitleaks fixes
- `acquisition-namespace .gitleaks.toml`: removed broken `[allowlist]` with empty `paths = []`
  (v8.30.0 requires at least one field); reduced to `[extend] useDefault = true`
- `ttl-barcoder .gitleaks.toml`: created (was missing entirely)
- `gitleaks-action@v2` removed from all repos — requires paid org license; pre-commit hook covers scanning
- Policy documented in `BUILD_SYSTEM_STANDARD.md §Tool licensing` and memory

### pypulsepal ruff fix
- Added `"src/pypulsepal/_version.py"` to ruff `exclude` list — hatch-vcs regenerates
  this on `uv sync`; fresh file failed ruff-format in CI

### GitHub Pages
- All three public repos (`pypulsepal`, `ttl-barcoder`, `acquisition-namespace`) confirmed
  on `gh-pages` branch; Pages source set correctly; all status: `built`
- pypulsepal was already on `gh-pages` (no action needed)
- acquisition-namespace: orphan `gh-pages` branch created, pushed, source switched via API

### pyproject.toml — docs extra split
- `acquisition-namespace`: `mkdocs-material` moved from `dev` to new `docs` extra
  (`uv sync --extra docs` in docs.yml CI step)
- Required because `uv sync --extra dev` in CI lint job was failing to find mkdocs

### Documentation builds
New full doc sites written in pypulsepal style for:

**ttl-barcoder** (4 pages):
- `docs/index.md` — badges, key features, quick start, nav
- `docs/getting_started.md` — install, decode from edges, examples, dev setup
- `docs/configuration.md` — BarcodeConfig fields, TTLType, TimestampPrecision, presets table
- `docs/hardware.md` — Bpod inject_barcode_states, pigpio, lgpio note, custom hardware

**acquisition-namespace** (5 pages + example YAML):
- `docs/index.md` — badges, key features, quick start, nav
- `docs/getting_started.md` — install, first steps, examples table, dev setup
- `docs/concepts.md` — hierarchy, templates/regex, optional levels, parent-level resolution
- `docs/examples.md` — MSW convention, NeuroBlueprint/SWC, four-level with optional acquisition
- `docs/api.md` — full NamespaceBuilder method reference
- `examples/namespace_neuroblueprint.yaml` — NeuroBlueprint-compatible spec (sub-/ses- hierarchy)

### Zenodo DOI removal
Removed all Zenodo DOI badges/refs from READMEs, docs, and CITATION.cff files across all repos.
Reason: existing DOI (`10.5281/zenodo.6379627`) points to first version on larsrollik account,
not concept DOI. TODO to re-register in ROADMAP (not urgent).

### BUILD_SYSTEM_STANDARD.md additions
- §Forgejo Actions support — PyPI OIDC not supported for Forgejo; publish via `UV_PUBLISH_TOKEN`
- §Tool licensing policy — no CI tools requiring paid license for org/non-commercial use
- CI bump-skip pattern updated: removed `secrets-scan`; test trigger corrected to PR-only

### ROADMAP additions
- Forgejo Actions port entry (infrastructure, not urgent)
- Zenodo DOI re-registration entry (not urgent)

### GitHub repo metadata
- Descriptions set from pyproject.toml for all 5 repos
- Homepage URLs set: pypulsepal ✓ (already set), ttl-barcoder ✓, acquisition-namespace ✓
- msw-flir-bonsai description set (private repo)

---

## State at session end (2026-05-27)

| Repo | Org | Public | PyPI | Pages | CI | Homepage |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| pypulsepal | ✓ murineshiftwork | ✓ | v0.4.3 | ✓ gh-pages | ✓ | ✓ |
| ttl-barcoder | ✓ murineshiftwork | ✓ | v0.4.1 | ✓ gh-pages | ✓ | ✓ |
| acquisition-namespace | ✓ murineshiftwork | ✓ | v1.2.1 | ✓ gh-pages | ✓ | ✓ |
| msw-flir-bonsai | ✓ murineshiftwork | private | — | — | ✓ | — |

---

## Remaining manual steps

1. **PyPI OIDC trusted publishers** — pypi.org manual step:
   - `pypulsepal`: update publisher owner `larsrollik` → `murineshiftwork`
   - `ttl-barcoder`: add new OIDC publisher (`murineshiftwork`, `release.yml`)
   - `acquisition-namespace`: add new OIDC publisher (`murineshiftwork`, `release.yml`)
2. **msw-flir-bonsai**: push local `external/msw-flir-bonsai`; smoke test on acquisition machine;
   then make public + configure PyPI OIDC + first release
3. **Zenodo**: re-register pypulsepal webhook under murineshiftwork org (not urgent; see ROADMAP)
