# Documentation and Docstring Gaps

Audit run: 2026-06-10. Blocking items for PyPI publication and namespace-repo separation.

---

## Repo-level doc state

| Repo | README | docs/ | mkdocs.yml | mkdocstrings | CI docs deploy | Status |
|---|---|---|---|---|---|---|
| `murineshiftwork` | polished | full (12 dirs) | yes | **no** | yes (docs.yml) | API ref missing |
| `acquisition-namespace` | polished | full (5 files) | yes | **no** | yes | API ref missing |
| `ttl-barcoder` | polished | full (4 files) | yes | **no** | yes | API ref missing |
| `pypulsepal` | polished | full (6 files) | yes | **no** | yes | API ref missing |
| `msw-flir-bonsai` | polished | sparse (2 files) | yes | **yes** | yes | content sparse |
| `rpi_camera_ensemble` | TODO stub | skeleton only | yes | unknown | yes | needs full content |
| `msw-open-ephys` | polished | none | no | no | no | README-only |
| `msw-plugin-api` | minimal | none | no | no | no | README-only |
| `rfid-to-url` | polished | none | no | no | no | README-only |
| `one-axis-stage` | skeleton | none | no | no | no | appears abandoned |

---

## mkdocstrings: not configured in any repo except msw-flir-bonsai

Only `msw-flir-bonsai` has `mkdocstrings` in `mkdocs.yml`. All other repos with docs sites
have narrative pages only — no auto-generated API reference from docstrings.

Required for each repo with a docs site:

1. Add `mkdocstrings[python]` to `docs` optional dep in `pyproject.toml`
2. Add to `mkdocs.yml` plugins block:
   ```yaml
   - mkdocstrings:
       handlers:
         python:
           options:
             docstring_style: numpy
             show_source: false
   ```
3. Create `docs/api.md` (or `docs/api/index.md`) with `::: package_name` directives

---

## Docstring coverage gaps (blocking API ref generation)

### `murineshiftwork`
- `cli/evaluate.py` — no public docstrings on `_resolve_host_session`, `_parse_host_flag`
- `namespace/paths.py` — `generate_session_paths` has good docstring; `build_data_paths` shim is undocumented
- `hardware/host_session.py` — `make_host_session` has inline doc; could be more complete
- `logic/task_process.py` — no public API docstrings
- `readers/session.py` — `read_session_data` has basic docstring; dispatch functions undocumented

### `acquisition-namespace`
- Check if `NamespaceBuilder` and `NamespaceSpec` have complete numpy-style docstrings

### `ttl-barcoder`
- Main `TTLBarcoder` class and encode/decode methods — check docstring completeness

### `pypulsepal`
- `PulsePal` class — likely documented but verify numpy-style completeness

### `msw-flir-bonsai`
- Has mkdocstrings but docs/ is sparse — API ref pages need to be created to use it

### `rpi_camera_ensemble`
- README is a TODO list; docs/ is skeleton; needs complete rewrite before public release

### `msw-open-ephys`
- `OEController`, `Session`, `OpenEphysHostSession` all have module/class docstrings
- No docs site planned; README is sufficient for current scope

### `msw-plugin-api`
- `HostSessionInfo`, `HostSessionProtocol`, `HostSessionInfoProtocol` — documented in module docstring
- No docs site needed; package is minimal by design

---

## Publishing readiness

### Ready to publish to PyPI now (docs sufficient)
- `acquisition-namespace` — on PyPI, docs deployed
- `ttl-barcoder` — on PyPI, docs deployed
- `pypulsepal` — on PyPI, docs deployed
- `msw-plugin-api` — on PyPI (v0.2.1), README sufficient
- `msw-open-ephys` — merged, release pending; README sufficient

### Needs doc work before public docs site
- `murineshiftwork` — add mkdocstrings + API ref pages
- `msw-flir-bonsai` — expand sparse docs/ (2 files → full reference)
- `rpi_camera_ensemble` — full docs rewrite; README first

### Not blocking namespace-repo separation
Namespace separation can proceed with the current doc state — docs site quality is a
parallel track. The namespace package architecture is independent of API doc completeness.

---

## Recommended sprint order

1. Add mkdocstrings to `murineshiftwork` mkdocs.yml + create `docs/api/` stub pages
2. Same for `acquisition-namespace`, `ttl-barcoder`, `pypulsepal` (one commit each)
3. Rewrite `rpi_camera_ensemble` README and fill docs/ skeleton
4. Expand `msw-flir-bonsai` docs from README content
