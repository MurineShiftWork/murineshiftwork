# Serial Scale Packages — Push & Deprecation Plan

**Goal:** Publish `serial-scale-hx711` and `serial-scale-bench` to PyPI under the
`MurineShiftWork` GitHub org; deprecate the old `serial-weighing-scale` and
`rpi-camera-colony` packages with stubs; archive the old GitHub repos.

---

## Packages involved

| Package | Location | Current version | PyPI status |
|---|---|---|---|
| `serial-scale-hx711` | `external/serial_scale_hx711/` | 2.0.4 | not yet published |
| `serial-scale-bench` | `external/serial_scale_bench/` | 0.1.0 | not yet published |
| `serial-weighing-scale` | archived — stub only | stub → 3.0.0 | exists (old) |
| `rpi-camera-colony` | archived — stub only | stub → next major | exists (old) |

---

## Step 1 — Fix CI before pushing (both scale packages)

Both `ci.yml` files contain `uses: gitleaks/gitleaks-action@v2` which requires a paid
GitHub org license.  Remove the gitleaks CI job; the pre-commit hook in
`.pre-commit-config.yaml` already covers secrets scanning locally.

Edit in each package (cannot be done by Claude — `external/` is off-limits):

```
external/serial_scale_hx711/.github/workflows/ci.yml   — remove gitleaks job/step
external/serial_scale_bench/.github/workflows/ci.yml    — remove gitleaks job/step
```

The pre-commit gitleaks hook stays.

---

## Step 2 — Create GitHub repos under MurineShiftWork

```bash
gh repo create MurineShiftWork/serial-scale-hx711 --public \
  --description "Python driver for Arduino+HX711 serial weighing scales."

gh repo create MurineShiftWork/serial-scale-bench --public \
  --description "Python driver for RS-232/USB bench scales (Kern, Mettler-Toledo, etc.)."
```

---

## Step 3 — Update remotes and push

```bash
git -C external/serial_scale_hx711 remote set-url origin \
  https://github.com/MurineShiftWork/serial-scale-hx711.git
git -C external/serial_scale_hx711 push -u origin main --tags

git -C external/serial_scale_bench remote set-url origin \
  https://github.com/MurineShiftWork/serial-scale-bench.git
git -C external/serial_scale_bench push -u origin main --tags
```

---

## Step 4 — Configure PyPI OIDC trusted publishing

On [pypi.org](https://pypi.org) → each project → Publishing → Add trusted publisher:

| Field | serial-scale-hx711 | serial-scale-bench |
|---|---|---|
| Owner | MurineShiftWork | MurineShiftWork |
| Repository | serial-scale-hx711 | serial-scale-bench |
| Workflow | release.yml | release.yml |
| Environment | *(none)* | *(none)* |

Do this **before** the first release workflow runs (OIDC registration must exist first).

---

## Step 5 — Trigger first releases

Both packages use commitizen + hatch-vcs.  The release workflow bumps version on push to
`main` if there are bumpable commits since the last tag.  Verify tags were pushed in
Step 3; if the workflow doesn't trigger automatically, run it via:

```bash
gh workflow run release.yml --repo MurineShiftWork/serial-scale-hx711
gh workflow run release.yml --repo MurineShiftWork/serial-scale-bench
```

---

## Step 6 — Deprecation stubs

### What a stub is

A minimal PyPI release of the **old** package name that warns on import and installs
nothing else.  No changes to the archived repos — stub is a standalone build.

### Where stubs live

Create both stubs under `external/legacy_pkgs/`:

```
external/legacy_pkgs/serial_weighing_scale_stub/
  pyproject.toml
  src/serial_weighing_scale/__init__.py

external/legacy_pkgs/rpi_camera_colony_stub/
  pyproject.toml
  src/rpi_camera_colony/__init__.py
```

### `serial_weighing_scale` stub

`src/serial_weighing_scale/__init__.py`:
```python
import warnings
warnings.warn(
    "serial-weighing-scale is deprecated and will receive no further updates. "
    "Use serial-scale-hx711 (Arduino+HX711) or serial-scale-bench (RS-232/USB bench scales) instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

`pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "serial-weighing-scale"
version = "3.0.0"
description = "Deprecated. Use serial-scale-hx711 or serial-scale-bench."
readme = "README.md"
requires-python = ">=3.8"
dependencies = []
```

### `rpi_camera_colony` stub

Same pattern:
```python
# src/rpi_camera_colony/__init__.py
import warnings
warnings.warn(
    "rpi-camera-colony is deprecated. Use rpi-camera-ensemble instead.",
    DeprecationWarning,
    stacklevel=2,
)
```

```toml
# pyproject.toml
[project]
name = "rpi-camera-colony"
version = "2.0.0"        # check current PyPI version and bump major
description = "Deprecated. Use rpi-camera-ensemble instead."
requires-python = ">=3.8"
dependencies = []
```

### Publishing stubs (no GitHub repo needed)

```bash
cd external/legacy_pkgs/serial_weighing_scale_stub
uv build
uv publish --token $PYPI_TOKEN

cd ../rpi_camera_colony_stub
uv build
uv publish --token $PYPI_TOKEN
```

---

## Step 7 — Archive old GitHub repos

```bash
gh repo archive larsrollik/serial-weighing-scale --yes
gh repo archive larsrollik/rpi-camera-colony --yes   # or MurineShiftWork if already transferred
```

Archiving makes the repo read-only and clearly labels it as archived on GitHub.
Do **not** delete — archived repos remain installable from source and preserve history.

---

## Step 8 — Update murineshiftwork pyproject.toml

After new packages are on PyPI, update the `[calibration]` optional dep pin:

```toml
# pyproject.toml
[project.optional-dependencies]
calibration = [
    "serial-scale-hx711>=2.0.4",
    "serial-scale-bench>=0.1.0",
]
```

Remove any reference to `serial-weighing-scale` from deps.

---

## Checklist

- [ ] Remove gitleaks-action from `ci.yml` in both scale packages
- [ ] Create GitHub repos under MurineShiftWork
- [ ] Update remotes + push both packages with tags
- [ ] Register OIDC trusted publisher on pypi.org for both packages
- [ ] Verify release workflows complete and packages appear on PyPI
- [ ] Write and publish `serial-weighing-scale==3.0.0` stub
- [ ] Write and publish `rpi-camera-colony==2.0.0` stub (check current version first)
- [ ] Archive `larsrollik/serial-weighing-scale` on GitHub
- [ ] Archive `larsrollik/rpi-camera-colony` on GitHub (or MurineShiftWork if transferred)
- [ ] Update `[calibration]` dep in `murineshiftwork/pyproject.toml`
- [ ] Update ROADMAP — mark manual items done
