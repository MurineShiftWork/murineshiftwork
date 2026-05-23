# Build System Standard

Reference for the build toolchain used across repos in this org (MSW, pypulsepal, rpi-cam-ensemble, …).
Use this to bring a new or legacy repo up to the standard.

---

## Stack summary

| Layer | Tool | Purpose |
|---|---|---|
| Build backend | `hatchling` + `hatch-vcs` | PEP 517 build; version from git tags |
| Versioning | `commitizen` | Conventional-commit bump flow; writes tag + VERSION file |
| Linting | `ruff` | Style + lint, replaces flake8/isort/pyupgrade |
| Type checking | `mypy` | Static typing, run in pre-commit and CI |
| Secret scanning | `gitleaks` | Blocks committed secrets |
| Pre-commit | `pre-commit` | Enforces all of the above locally and in CI |
| CI | GitHub Actions | lint + test + secrets-scan + gate jobs; separate release.yml |

---

## pyproject.toml structure

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "my-package"
dynamic = ["version"]
description = "..."
readme = "README.md"
license = {text = "BSD-3-Clause"}
authors = [{name = "...", email = "..."}]
requires-python = ">=3.10"
dependencies = [...]

[project.urls]
Homepage = "https://github.com/org/repo"
"Issue Tracker" = "https://github.com/org/repo/issues"

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "pre-commit",
    "ruff",
    "mypy",
    "commitizen",
]

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
[tool.hatch.version]
source = "vcs"
fallback-version = "0.1.0"

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]  # src/ layout is standard; flat-layout exception: ["my_package"]

[tool.hatch.build.targets.sdist]
include = ["/src/my_package", "/tests", "/README.md", "/LICENSE", "/pyproject.toml"]

# ---------------------------------------------------------------------------
# Commitizen
# ---------------------------------------------------------------------------
# Release flow:
#   cz bump → updates [tool.commitizen] version + VERSION file,
#             creates "bump: ..." commit and annotated tag v{version}
#   git push && git push --tags → triggers release CI
#
# Commit types that drive version bumps:
#   feat:                     → minor  (0.2.0)
#   fix:                      → patch  (0.1.1)
#   feat!: / BREAKING CHANGE: → major  (1.0.0)

[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0"          # kept in sync by cz bump; also written to VERSION file
tag_format = "v$version"
update_changelog_on_bump = false
version_files = ["VERSION"]

# ---------------------------------------------------------------------------
# Pytest
# ---------------------------------------------------------------------------
[tool.pytest.ini_options]
testpaths = ["tests"]

# ---------------------------------------------------------------------------
# Ruff
# ---------------------------------------------------------------------------
[tool.ruff]
line-length = 88
indent-width = 4

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "YTT", "SIM", "PTH", "TCH", "PYI"]
fixable = ["ALL"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

# ---------------------------------------------------------------------------
# Mypy
# ---------------------------------------------------------------------------
[tool.mypy]
mypy_path = "src"           # required for src/ layout so mypy finds the package
warn_return_any = false
ignore_missing_imports = true
```

**Invariants:**
- `dynamic = ["version"]` — version is never hardcoded in `[project]`; hatch-vcs reads it from git tags.
- `[tool.commitizen] version` and `VERSION` file are the commitizen tracking fields; they are written by `cz bump` and should match the latest tag.
- `fallback-version = "0.1.0"` is used when no git tags exist (fresh clone, CI shallow fetch without tags).
- `tag_format = "v$version"` means tags are `v0.2.0`, not `0.2.0`. Old tags without the prefix still work with hatch-vcs via setuptools-scm PEP 440 matching.

---

## VERSION file

Every repo must have a `VERSION` file at the project root, containing the current version string (no trailing newline issues — just the version line).

```
0.1.0
```

Commitizen's `version_files = ["VERSION"]` writes to it on every `cz bump`. Without this file, `cz bump` fails.

Create it by hand if missing; content must match `[tool.commitizen] version`.

---

## Pre-commit config

```yaml
# .pre-commit-config.yaml
# Update versions with: pre-commit autoupdate
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: mixed-line-ending

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.0, types-PyYAML]
        # add any other runtime deps that mypy needs to resolve types
        # exclude: '^(external|playground)/'  # if needed

  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.1.0
    hooks:
      - id: commitizen
        stages: [commit-msg]   # enforces conventional commit format

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.3
    hooks:
      - id: gitleaks
```

**Invariants:**
- `ruff` runs before `ruff-format` — lint first, then format.
- `commitizen` hook is `commit-msg` stage only — it validates the commit message, not file content.
- `gitleaks` blocks secrets. False positives are suppressed via `.gitleaksignore` (fingerprint-based, one line per finding: `path:rule-id:line`). Never use regex allowlists (`[allowlist] regexes`) — too broad.
- `mypy additional_dependencies` must list every package whose types mypy needs to resolve. Common additions: `pydantic>=2.0`, `types-PyYAML`, `pyserial`.
- Vendored files can be excluded from ruff E501 via `[tool.ruff.lint.per-file-ignores]`.

**One-time setup per clone:**
```bash
pre-commit install        # wires hooks into .git/hooks/pre-commit (and commit-msg)
```

---

## CI workflows

Two workflows: `CI.yaml` (every push/PR) and `release.yml` (tag push only).

### CI.yaml

```yaml
name: CI

on:
  push:
    branches: ["**"]
    tags-ignore: ["v*"]   # tag pushes handled by release.yml
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0           # needed for hatch-vcs version derivation
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install .[dev]
      - name: Run pre-commit
        run: pre-commit run --all-files --show-diff-on-failure

  test:                            # omit for repos with no unit tests
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install .[dev]
      - run: pytest tests/ -v --no-header -q

  secrets-scan:
    name: Secrets scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  ci:                              # aggregate gate — branch protection requires this
    name: CI
    runs-on: ubuntu-latest
    needs: [lint, test, secrets-scan]
    if: always()
    steps:
      - name: Check required jobs
        run: |
          if [[ "${{ needs.lint.result }}" != "success" ]]; then
            echo "lint failed" && exit 1
          fi
          if [[ "${{ needs.test.result }}" != "success" ]]; then
            echo "test failed" && exit 1
          fi
          if [[ "${{ needs.secrets-scan.result }}" != "success" ]]; then
            echo "secrets-scan failed" && exit 1
          fi
          echo "All required checks passed."
```

**Note:** MSW omits the `test` job (hardware-dependent tests can't run in CI). The `ci` gate job lists only `lint` and `secrets-scan` as `needs` in that case.

**Secrets scan:** use `gitleaks/gitleaks-action@v2` (consistent with pre-commit gitleaks hook; no baseline file required). Do NOT use `secret-scanner/action` — it requires a `.secrets.baseline` file which must be generated and committed (`detect-secrets scan > .secrets.baseline`). If a repo already has `.secrets.baseline`, it can keep using `secret-scanner/action`; new repos should default to gitleaks action.

### release.yml

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write

jobs:
  release:
    name: Create GitHub release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: |
          pip install hatchling hatch-vcs
          python -m hatchling build
      - name: Create release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref_name }}
          release_name: ${{ github.ref_name }}
          draft: false
          prerelease: false
```

---

## Layout

**src/ layout is standard.** All packages go under `src/<package_name>/`.

```
repo-root/
├── src/
│   └── my_package/
│       └── __init__.py
├── tests/
├── examples/        (optional)
├── README.md
├── LICENSE
├── VERSION
└── pyproject.toml
```

Hatchling resolves `src/` automatically when `packages = ["src/my_package"]` is set.
`pip install -e .` adds `src/` to `sys.path` — no `__editable__` shims needed.

Flat layout (`packages = ["my_package"]`) is only used when a repo predates this standard
and migration is deferred. Document the exception in the repo's own plan file.

---

## Zenodo integration (research archiving + DOI)

Zenodo archives every tagged GitHub release and issues a permanent DOI — required for papers that cite software.
The integration is webhook-based: **no GitHub Actions step is needed for Zenodo**. The standard `release.yml` is sufficient.

### Why CITATION.cff (not `.zenodo.json`) for published packages

`CITATION.cff` is the correct metadata file for any package intended to be cited:

| | `CITATION.cff` | `.zenodo.json` |
|---|---|---|
| GitHub "Cite this repository" button | ✅ | ✗ |
| Zenodo reads and uses it | ✅ (takes priority) | ✅ |
| Zotero / reference managers | ✅ | ✗ |
| CRediT contributor roles | ✅ | ✗ |
| Companion paper citation | ✅ (`preferred-citation`) | partial |
| Platform-agnostic standard | ✅ (FORCE11 / GitHub) | Zenodo-specific |

**Rule:** use `CITATION.cff` for any package that will be or already is cited in publications. Do not use `.zenodo.json` — when `CITATION.cff` is present Zenodo ignores `.zenodo.json` anyway.

### How the Zenodo push workflow works

Zenodo listens for GitHub **release published** events via a webhook (configured when you toggle the repo ON on zenodo.org). The standard `release.yml` already creates a GitHub release via `actions/create-release@v1`, which fires that webhook.

Full flow after a `cz bump`:

```
cz bump
  → commits "bump: ..." + annotated tag vX.Y.Z
git push && git push --tags
  → tag push triggers release.yml
    → release.yml builds the package + creates GitHub release
      → GitHub release event fires Zenodo webhook
        → Zenodo archives the release, reads CITATION.cff, updates the concept DOI record
```

No Zenodo token, no upload step, no extra workflow job. The only requirement is that `release.yml` creates a GitHub release (not just a tag).

**First release only:** after the first tag push, go to the Zenodo record, copy the concept DOI, add it to `CITATION.cff` under `identifiers` and to the README badge. Subsequent releases update the same concept DOI record automatically.

### One-time setup per repo

1. Go to [zenodo.org/account/settings/github](https://zenodo.org/account/settings/github) (log in with GitHub OAuth).
2. Find the repo in the list and flip the toggle **ON**.
3. Add a `CITATION.cff` file at the project root (see template below).
4. Push the first versioned tag (`git push --tags`). Zenodo reads `CITATION.cff` and archives the release.
5. Copy the concept DOI from the Zenodo record; add it to `CITATION.cff` `identifiers` and to the README badge.

### `CITATION.cff` template

```yaml
cff-version: 1.2.0
message: "If you use this software, please cite it as below."
type: software
title: "MyPackage: short description"
repository-code: https://github.com/org/repo
url: https://github.com/org/repo
license: GPL-3.0
keywords:
  - neuroscience
  - python
  - relevant-domain-terms
authors:
  - family-names: Last
    given-names: First
    orcid: https://orcid.org/0000-0000-0000-0000
identifiers:
  - type: doi
    value: 10.5281/zenodo.XXXXXXX
    description: Zenodo concept DOI
preferred-citation:
  type: software
  title: "MyPackage: short description"
  authors:
    - family-names: Last
      given-names: First
      orcid: https://orcid.org/0000-0000-0000-0000
  year: YYYY
  month: M
  publisher:
    name: Zenodo
  doi: 10.5281/zenodo.XXXXXXX
  url: https://doi.org/10.5281/zenodo.XXXXXXX
```

**Field notes:**
- `license`: SPDX identifier, case-sensitive (`GPL-3.0`, `MIT`, `BSD-3-Clause`). Must match the LICENSE file.
- `orcid`: full URL form `https://orcid.org/0000-0000-0000-0000`. Strongly encouraged; collect at contribution time.
- `identifiers.value`: use the **concept DOI** (stable across versions), not the version-specific DOI.
- `preferred-citation`: duplicate the top-level authors and title here. If the repo has a companion paper, replace `preferred-citation` with the paper's DOI and metadata instead.
- Add additional authors to both `authors` and `preferred-citation.authors` when contributors are added.

### README badge

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
```

Replace `XXXXXXX` with the concept DOI. Add after first release.

### Upgrade checklist additions

- [ ] Enable Zenodo webhook for the repo on zenodo.org
- [ ] Add `CITATION.cff` with title, license, authors (with ORCIDs), concept DOI
- [ ] Add DOI badge to `README.md` after first release
- [ ] Add citation block to `README.md` (see README structure below)

---

## README structure

Every repo must have a `README.md` with the following sections in order.
Content scales with the repo — a small utility needs less prose than a major package — but the structure must be present.

### Badges (top of file)

Required badges:

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![PyPI](https://img.shields.io/pypi/v/my-package.svg)](https://pypi.org/project/my-package)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
```

Omit DOI badge until Zenodo is set up. Omit PyPI badge if the package is not published to PyPI.
Do **not** use a Black badge — this org uses Ruff.
Do **not** hardcode a version string anywhere in the README body (version is dynamic via hatch-vcs).

### Sections

```
# PackageName
One-line description

---

## Example usage       ← minimal working example(s)
## Installation        ← pip install, pip install .[extra], git clone path
## Citation            ← only if Zenodo DOI exists
## License & sources   ← see rules below
## Useful references   ← optional; link list at bottom
```

### License & sources section

This section must appear in every README. It states the project license and attributes all upstream code the project derives from or vendors.

**Template:**

```markdown
## License & sources

This software is released under the **[LICENSE-NAME](LICENSE)**.

<!-- For each piece of vendored source code: -->
`_vendored_file.py` is vendored from [upstream-project] vX.Y.Z ([LICENSE-TYPE], Copyright © YEAR Author).
The original source is at [upstream URL].

<!-- For derived/reimplemented work (not copied verbatim): -->
This work is derived from / inspired by [upstream-project] ([commit: XXXXXXX]).
```

**Rules:**
- State the project's own license first, with a link to the `LICENSE` file.
- For every vendored file (source copied verbatim or near-verbatim into the repo):
  - Name the file, the upstream project, the upstream version, the upstream license, and the copyright holder.
  - Link to the upstream source location.
  - The vendored file itself must also carry a header (see Vendoring section below).
- For derived work (reimplemented, not copied): state the upstream project and the commit or version taken as reference. No license compatibility concern if the upstream is permissive, but attribution is still required.
- Dependencies (listed in `pyproject.toml`) do NOT need to appear here — they are covered by their own package metadata.

---

## Vendoring third-party code

Vendoring means copying a third-party source file into the repo rather than taking it as a dependency.
Use vendoring when: (a) the dependency is large and only a small file is needed, (b) the upstream package is poorly maintained, or (c) a runtime dependency would create an unacceptable install footprint.

### File header

Every vendored file must start with this header block (adapt fields):

```python
# Vendored from: <upstream project name> (<upstream URL>)
# Version: <upstream version or commit hash>
# License: <SPDX license name>  Copyright (c) <year> <copyright holder>
# Modifications: <"none" or one-line summary of what was changed>
```

Example (from `pypulsepal/_arcom.py`):

```python
# Vendored from: pybpod-api (https://github.com/pybpod/pybpod-api)
# Version: 1.8.2
# License: MIT  Copyright (c) 2016 Champalimaud Foundation
# Modifications: none
```

### pyproject.toml

Exclude vendored files from ruff line-length checks:

```toml
[tool.ruff.lint.per-file-ignores]
"src/my_package/_vendored_file.py" = ["E501"]
```

### License compatibility

Only vendor code whose license is compatible with the project's own license:

| Project license | Can vendor |
|---|---|
| MIT / BSD / Apache-2.0 | MIT, BSD, Apache-2.0, PSF |
| GPL-3.0 | MIT, BSD, Apache-2.0, LGPL, GPL |
| Proprietary | only permissive (MIT, BSD, Apache-2.0) with explicit permission |

When in doubt: MIT and BSD-2/3 are safe to vendor into anything. GPL code cannot be vendored into a non-GPL project.

---

## Upgrade checklist for a legacy repo

- [ ] `pyproject.toml`: replace `[build-system]` with `hatchling` + `hatch-vcs`; move all metadata from `setup.cfg`/`setup.py` into `[project]`; add `[tool.hatch.version]`, `[tool.hatch.build.targets.*]`, `[tool.commitizen]`, `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.mypy]`
- [ ] Move package directory to `src/<package_name>/`; update `packages = ["src/<package_name>"]` and sdist `include`
- [ ] Delete `setup.cfg`, `setup.py`, `MANIFEST.in` (superseded by pyproject.toml)
- [ ] Add `VERSION` file at project root, content = current version string
- [ ] Add/update `.pre-commit-config.yaml` with the standard hook set above
- [ ] Run `pre-commit install` in the repo (once per clone)
- [ ] Add/update `.github/workflows/CI.yaml` and `release.yml`
- [ ] Add `commitizen` to `[project.optional-dependencies] dev`
- [ ] Verify `cz bump --dry-run` works (needs at least one `v*` tag or sets fallback)
- [ ] If using pydantic/pyserial/yaml: add to `mypy additional_dependencies`
- [ ] If repo has vendored files: add `[tool.ruff.lint.per-file-ignores]` to suppress E501; add header to vendored file; attribute in README
- [ ] Enable Zenodo and add `CITATION.cff` (research repos); do not add `.zenodo.json`
- [ ] README: remove any hardcoded version string; add Ruff badge; add License & sources section

---

## Commit message convention (commitizen)

```
<type>(<scope>): <short description>

<optional body>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`

Scope is optional but encouraged (e.g. `feat(models):`, `fix(pulsepal):`).

Breaking changes: `feat!:` or add `BREAKING CHANGE:` in footer.

The `commitizen` pre-commit hook (commit-msg stage) rejects messages that don't match this format.

---

## Reference: contributor and authorship guidelines

> This section documents what established external guidelines exist. No single standard has been adopted for this org yet — record here when a decision is made.

### ICMJE criteria (academic publishing standard)
[ICMJE](https://www.icmje.org/recommendations/browse/roles-and-responsibilities/defining-the-role-of-authors-and-contributors.html) defines authorship as requiring ALL of: (1) substantial contribution to conception/design or data acquisition/analysis; (2) drafting or critically revising the work; (3) approving the final version; (4) accountability for the work. Widely used by journals. Written for papers, not software — "data acquisition" maps loosely to "writing the code."

### CRediT taxonomy
[CRediT](https://credit.niso.org/) (Contributor Roles Taxonomy) defines 14 named roles: Conceptualization, Data Curation, Formal Analysis, Funding Acquisition, Investigation, Methodology, Project Administration, Resources, Software, Supervision, Validation, Visualization, Writing – Original Draft, Writing – Review & Editing. CITATION.cff supports CRediT roles natively via the `role` field on each author. Finer-grained than ICMJE; allows crediting non-author contributors (e.g. someone who only did validation).

### all-contributors spec
[all-contributors](https://allcontributors.org/) is a GitHub bot + badge system that credits any type of contribution — code, docs, bug reports, ideas, design, infrastructure, etc. Uses a `.all-contributorsrc` JSON file and auto-generates a contributors table in the README. Does not address authorship or ORCID. Suited to large open-source projects; overhead is high for small research groups.

### BrainGlobe practice (observed, 2026-05-23)
BrainGlobe uses `CITATION.cff` in every repo (no `.zenodo.json`). ORCIDs are present but not systematically collected — some authors have them, most do not. No written authorship criteria. Named authors in `CITATION.cff` correspond to core maintainers; a catch-all `"BrainGlobe Developers"` author entry covers broader contributors. No all-contributors bot. Zenodo integration exists for atlas data (hosted on Zenodo) but not for the Python packages themselves (no Zenodo webhook per repo found).

### Operational notes (format, not policy)
- ORCID format in CITATION.cff: full URL `https://orcid.org/0000-0000-0000-0000`
- Name format: `"family-names: Last"` + `"given-names: First"` (CITATION.cff YAML keys), or `"Last, First"` in `.zenodo.json`
- Collect ORCIDs at contribution time — chasing them before a release is unreliable
- CITATION.cff takes priority over `.zenodo.json` in Zenodo; do not use both
