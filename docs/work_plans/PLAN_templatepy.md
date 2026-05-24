# templatepy — Modification Plan

Repo: `larsrollik/templatepy`
Standard ref: `docs/work_plans/BUILD_SYSTEM_STANDARD.md`
Last updated: 2026-05-24

---

## What templatepy already has (no changes needed)

- hatchling + hatch-vcs build system in generated `pyproject.toml`
- auto-bump `release.yml` (cz bump → push → uv build → softprops release → uv publish OIDC)
- `CI.yaml` bump-skip pattern with gate accepting `skipped`
- `docs.yml` (Material for MkDocs, gh-deploy on docs/** changes)
- `mkdocs.yml` with Material theme
- `.pre-commit-config.yaml` standard set (ruff, mypy, commitizen, gitleaks, pre-commit-hooks)
- `CITATION.cff` in template
- `VERSION` file
- Copier answers file (`.copier-answers.yml`)

---

## Missing items — changes needed in templatepy

### 1. `py.typed` marker in generated package

**File to add:** `template/src/[[project_slug]]/py.typed` (empty file)

Without this, mypy in downstream packages emits `import-untyped` for any package
generated from this template. Every typed Python library should ship `py.typed`.

No `pyproject.toml` change needed — hatchling includes all files under the package dir.

**Priority:** High — affects all generated packages.

---

### 2. `docs` optional-dependency group in `pyproject.toml`

**File to modify:** `template/pyproject.toml`

Add:
```toml
[project.optional-dependencies]
docs = [
    "mkdocs-material",
]
```

Allows `pip install .[[project_slug]][docs]` for local docs development without
needing to remember the package name.

**Priority:** Medium.

---

### 3. `Documentation` URL in `[project.urls]`

**File to modify:** `template/pyproject.toml`

Add to `[project.urls]`:
```toml
Documentation = "https://[[github_username]].github.io/[[github_repo]]/"
```

PyPI displays this as a prominent link on the package page.

**Priority:** Medium.

---

### 4. `version` field in `CITATION.cff`

**File to modify:** `template/CITATION.cff`

Add:
```yaml
version: "[[commitizen_version]]"
```

(or whatever the copier variable for initial version is — likely `"1.0.0"` at template init)

Required for Zenodo to display a version on the archived record.

**Priority:** Medium.

---

### 5. `CITATION.cff` and `VERSION` in sdist includes

**File to modify:** `template/pyproject.toml`

```toml
[tool.hatch.build.targets.sdist]
include = [
    "/src/[[project_slug]]",
    "/tests",
    "/README.md",
    "/LICENSE",
    "/pyproject.toml",
    "/CITATION.cff",
    "/VERSION",
]
```

Both files should be present in source distributions for reproducibility.

**Priority:** Low.

---

### 6. mkdocstrings as opt-in copier variable (optional/deferred)

Add a copier boolean prompt `use_mkdocstrings` (default: false). When true:
- Adds `mkdocstrings[python]` to `docs` extras
- Adds `plugins:` section to `mkdocs.yml`
- Generates a `docs/api.md` with `:::` directives

This is more complex to implement in copier (conditional file rendering).
Defer until the simpler items above are done.

**Priority:** Low — defer.

---

### 7. CI template for generated packages

**Clarification:** `templatepy/.github/workflows/ci.yml` is the CI for the templatepy
repo itself (template validation). The CI workflow for generated packages lives at
`template/.github/workflows/ci.yml`. Verify it includes:
- `if: "!startsWith(github.event.head_commit.message, 'bump:')"` on all jobs
- Gate job accepting `skipped`
- `pip install .[dev]` (or uv equivalent)
- Matrix across Python 3.10/3.11/3.12
- `pytest --tb=short` (uses `testpaths` from pyproject.toml)

If not, align to the pattern in `BUILD_SYSTEM_STANDARD.md`.

**Priority:** High — audit before next templatepy release.

---

## Implementation order

| # | Change | File | Effort |
|---|---|---|---|
| 1 | `py.typed` marker | `template/src/[[...]]/__init__.py` sibling | trivial |
| 2 | `Documentation` URL | `template/pyproject.toml` | trivial |
| 3 | `docs` optional-dep | `template/pyproject.toml` | trivial |
| 4 | `version` in CITATION.cff | `template/CITATION.cff` | trivial |
| 5 | sdist includes | `template/pyproject.toml` | trivial |
| 6 | Audit template `ci.yml` | `template/.github/workflows/ci.yml` | 30 min |
| 7 | mkdocstrings opt-in | multiple template files | 2–3 hrs |

Items 1–5 can land in a single PR. Item 6 is a review + patch. Item 7 is a separate PR.

---

## Copier update for existing repos

After templatepy changes are merged and tagged, run in each existing repo:
```sh
copier update --trust
```
Review the diff carefully — copier will attempt to update managed files. Accept
`py.typed`, `CITATION.cff`, `pyproject.toml` URL/extras changes. Reject any
overwrite of custom `mkdocs.yml`, `README.md`, or `src/`.
