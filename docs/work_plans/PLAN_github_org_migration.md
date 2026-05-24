# GitHub org migration — work plan

**URGENT** — do before next PyPI release.

Org already exists: `github.com/murineshiftwork`
Personal account: `github.com/larsrollik`

Last updated: 2026-05-24

---

## Status

- [ ] Transfer repos to org
- [ ] PyPI OIDC trusted publisher (per repo)
- [ ] Zenodo re-link

---

## 1. Transfer repos

For each repo: GitHub → repo Settings → Danger Zone → Transfer ownership → `murineshiftwork`.

Order matters — transfer dependencies before dependents:

| Repo | Priority | Notes |
|---|---|---|
| `ttl_barcoder` | 1st | no dependents yet |
| `pypulsepal` | 1st | no dependents yet |
| `murineshiftwork` | 2nd | depends on above |
| `msw-flir-bonsai` | 3rd | |
| `serial_scale_bench` | any | |
| `serial_scale_hx711` | any | |
| `rfid-to-url` | any | |

**After each transfer:**
- GitHub auto-redirects old URL — existing clones keep working
- Update remote on this machine:
  ```bash
  git remote set-url origin git@github.com:murineshiftwork/<repo>.git
  ```
- Recreate any repo-level GitHub Actions secrets (org-level secrets are shared automatically)

---

## 2. PyPI OIDC trusted publisher

OIDC = no API tokens; GitHub Actions gets a short-lived token at publish time.

**Do once per repo that publishes to PyPI** (`ttl_barcoder`, `pypulsepal`, `murineshiftwork` when ready).

### On PyPI (pypi.org):

1. Log in → your project → Publishing → Add a new publisher
2. Fill in:
   - Publisher: GitHub Actions
   - Owner: `murineshiftwork`
   - Repository: `<repo-name>`
   - Workflow filename: `release.yml` (or whatever the publish workflow is called)
   - Environment name: `pypi` (optional but recommended)

### In the GitHub Actions workflow:

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write   # required for OIDC
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install build && python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        # no token needed — OIDC handles auth
```

No `PYPI_API_TOKEN` secret needed. Remove any existing token-based publish steps.

---

## 3. Zenodo

Zenodo links to a **GitHub account**, not individual repos. Re-linking after transfer:

1. Log in to zenodo.org with GitHub OAuth
2. Go to GitHub → connected repos list
3. The transferred repos will appear under the org — toggle them on
4. Existing DOIs and records are unaffected (they reference a specific release/tag, not the URL)

**Check:** if any existing Zenodo record has the old `github.com/larsrollik/<repo>` URL hardcoded in metadata, update it manually via the record edit page.

---

## 4. Update remote URLs on this machine

After all transfers:

```bash
cd /mnt/maindata/code/murineshiftwork
git remote set-url origin git@github.com:murineshiftwork/murineshiftwork.git

cd external/ttl_barcoder
git remote set-url origin git@github.com:murineshiftwork/ttl_barcoder.git

cd external/pypulsepal
git remote set-url origin git@github.com:murineshiftwork/pypulsepal.git
```

---

## 5. Cleanup

- [ ] Remove old `larsrollik/<repo>` links from README badges, docs, CITATION.cff
- [ ] Update `CITATION.cff` `repository-code` field in each transferred repo
- [ ] Check readthedocs if any repo has docs hosted there — update the GitHub integration
