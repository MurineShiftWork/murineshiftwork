# Forgejo Migration Plan — murineshiftwork + templatepy

Review of what it takes to move `.github/` CI/CD from GitHub Actions to a self-hosted
Forgejo instance with `act_runner`. Also covers multi-repo docs deployment to
`*.docs.murineshift.work` and the runner fleet for the full Python/OS matrix.

---

## Summary of changes required

| Area | Effort | Blocker? |
|---|---|---|
| Add `.forgejo/workflows/` alongside `.github/` | trivial | yes — Forgejo won't read `.github/workflows/` |
| `checkout` / `setup-python` / `setup-uv` | none | no — these work as-is |
| Windows runner | register a Windows `act_runner` | no, but needed for repos that test on Windows |
| `softprops/action-gh-release` | replace with API call | yes for release.yml |
| `pypa/gh-action-pypi-publish` (OIDC) | replace with token + twine | yes — PyPI doesn't trust Forgejo OIDC |
| `mkdocs gh-deploy` (GitHub Pages) | replace with rsync to static server | yes for docs.yml |
| GitHub URLs in pyproject / mkdocs | update | no, but needed for consistency |
| Issue / PR templates | none — Forgejo reads `.github/` too | no |
| templatepy: Copier template variables | add `forgejo_host` | no, but improves ergonomics |

---

## Workflow directory

Forgejo Actions reads from `.forgejo/workflows/` (preferred) or `.gitea/workflows/`.
It does **not** read `.github/workflows/`.

**Keep `.github/workflows/` in place.** Add `.forgejo/workflows/` alongside it:

```
.forgejo/workflows/ci.yml          ← Forgejo reads this
.github/workflows/ci.yml           ← GitHub reads this
```

Both directories coexist in the same repo without interference. GitHub Actions and
Forgejo Actions run independently from each mirror.

Issue and PR templates under `.github/ISSUE_TEMPLATE/` and `.github/PULL_REQUEST_TEMPLATE.md`
are read by Forgejo from the same paths — no change needed there.

---

## Runner fleet — Python matrix + Windows

`act_runner` is compatible with GitHub Actions YAML syntax (`on:`, `jobs:`, `steps:`
structure is drop-in). Python version matrix does **not** require separate runners per
version — `actions/setup-python` or `astral-sh/setup-uv` downloads the requested version
into each container job.

### Infrastructure layout

```
your-server (Linux)
  ├── Forgejo instance
  ├── act_runner (Linux + Docker)   — handles ubuntu-latest, Python 3.12/3.13 matrix
  └── Caddy                         — serves *.docs.murineshift.work

a-windows-machine (physical or VM)
  └── act_runner (native, no Docker) — handles windows-latest jobs
```

### What you need

| Runner | Host | Labels | Handles |
|---|---|---|---|
| `msw-linux-01` | Linux (x86-64), Docker | `ubuntu-latest`, `linux`, `self-hosted` | all Linux CI, Python matrix |
| `msw-windows-01` | Windows | `windows-latest`, `windows`, `self-hosted` | Windows test jobs |

One Linux runner with `max_parallel_jobs: 4` covers a 2-Python matrix across multiple
repos running in parallel. Add a second Linux runner for headroom.

### Linux runner setup

```bash
wget https://code.forgejo.org/forgejo/act_runner/releases/download/v0.2.11/act_runner-0.2.11-linux-amd64
chmod +x act_runner-0.2.11-linux-amd64
mv act_runner-0.2.11-linux-amd64 /usr/local/bin/act_runner

act_runner generate-config > /etc/act_runner/config.yaml
```

Key fields in `/etc/act_runner/config.yaml`:

```yaml
runner:
  name: msw-linux-01
  labels:
    - "ubuntu-latest:docker://ghcr.io/catthehacker/ubuntu:act-22.04"
    - "linux:docker://ghcr.io/catthehacker/ubuntu:act-22.04"
    - "self-hosted:docker://ghcr.io/catthehacker/ubuntu:act-22.04"
cache:
  enabled: true
  dir: /var/cache/act_runner
max_parallel_jobs: 4
```

`ghcr.io/catthehacker/ubuntu:act-22.04` is purpose-built for `act`/`act_runner`:
includes git, curl, jq, Python build deps — avoids missing-binary failures mid-job.

```bash
act_runner register \
  --instance https://<forgejo-host> \
  --token <org-runner-token> \
  --config /etc/act_runner/config.yaml \
  --no-interactive
```

Systemd unit (`/etc/systemd/system/act_runner.service`):

```ini
[Unit]
Description=Forgejo act_runner
After=docker.service
Requires=docker.service

[Service]
ExecStart=/usr/local/bin/act_runner daemon --config /etc/act_runner/config.yaml
Restart=always
User=act_runner

[Install]
WantedBy=multi-user.target
```

### Windows runner setup

Windows runners use the `host` executor — jobs run directly on the Windows host, no
Docker needed. `setup-python` / `setup-uv` installs Python per job.

`C:\act_runner\config.yaml`:

```yaml
runner:
  name: msw-windows-01
  labels:
    - "windows-latest:host"
    - "windows:host"
    - "self-hosted:host"
max_parallel_jobs: 2
```

```powershell
.\act_runner.exe register `
  --instance https://<forgejo-host> `
  --token <org-runner-token> `
  --config C:\act_runner\config.yaml `
  --no-interactive

sc.exe create act_runner binPath= "C:\act_runner\act_runner.exe daemon --config C:\act_runner\config.yaml" start= auto
sc.exe start act_runner
```

Pre-install: Git for Windows. `uv` is optional — `astral-sh/setup-uv` downloads it.

### Register runners at org level

One registration covers all repos in the org:

```
https://<forgejo-host>/org/murineshiftwork/-/settings/actions/runners
```

### Workflow `runs-on` stays unchanged

```yaml
matrix:
  os: [ubuntu-latest, windows-latest]
  python-version: ["3.12", "3.13"]
```

Forgejo dispatches by label — same convention as GitHub, no workflow edits needed.

### Action fetching

`act_runner` fetches `uses: actions/checkout@v4` etc. from GitHub by default. If the
host has limited outbound internet, set in `config.yaml`:

```yaml
actions_endpoint: https://gitea.com
```

Gitea.com mirrors most common GitHub Actions. The ones used here are:
`actions/checkout`, `actions/setup-python`, `astral-sh/setup-uv`.

---

## Multi-repo docs on `*.docs.murineshift.work`

Each repo gets its own subdomain — no monorepo, each stays independent:

```
murineshiftwork.docs.murineshift.work
pypulsepal.docs.murineshift.work
ttl-barcoder.docs.murineshift.work
pyrat-api.docs.murineshift.work
labwatch-core.docs.murineshift.work
...
```

### Architecture

```
push to main
    → Forgejo runs docs.yml
    → mkdocs build   (output: site/)
    → rsync site/ → /var/www/docs/<repo-name>/  on the docs server
    → Caddy serves <repo-name>.docs.murineshift.work from that path
```

**DNS:** one wildcard A record `*.docs.murineshift.work → <server-IP>`. Caddy and the
docs server can be on the same host as Forgejo, or a separate machine.

### Caddyfile

```caddyfile
*.docs.murineshift.work {
    root * /var/www/docs/{labels.0}
    file_server
    tls internal
}
```

`{labels.0}` is the leftmost subdomain label (e.g. `murineshiftwork` from
`murineshiftwork.docs.murineshift.work`). Caddy resolves the root dynamically — no
per-repo handle block needed. A request for a repo with no directory returns a 404.

`tls internal` uses Caddy's built-in CA — suitable for a lab-internal network. For a
publicly reachable server, replace with a DNS-01 challenge:

```caddyfile
*.docs.murineshift.work {
    tls { dns cloudflare {env.CF_API_TOKEN} }
    root * /var/www/docs/{labels.0}
    file_server
}
```

### Deploy step in each repo's `docs.yml`

```yaml
      - name: Deploy docs
        env:
          DOCS_DEPLOY_KEY: ${{ secrets.DOCS_DEPLOY_KEY }}
        run: |
          uv run mkdocs build
          mkdir -p ~/.ssh
          printf '%s\n' "${DOCS_DEPLOY_KEY}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          rsync -az --delete \
            -e "ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no" \
            site/ deploy@docs.murineshift.work:/var/www/docs/${{ github.event.repository.name }}/
```

`DOCS_DEPLOY_KEY` is an org-level secret in Forgejo — set once, inherited by all repos.
The public half goes in `deploy@docs-server:~/.ssh/authorized_keys`. Restrict with a
`command="rsync --server ..."` forced command in `authorized_keys` for defense in depth.

**mkdocs.yml** per repo:

```yaml
site_url: https://murineshiftwork.docs.murineshift.work/
repo_url: https://<forgejo-host>/murineshiftwork/murineshiftwork
repo_name: murineshiftwork/murineshiftwork
```

---

## Per-workflow migration

### `ci.yml` — lint + test gate

The Windows matrix row needs the Windows runner registered (see runner section above).
If Windows testing is not needed for a given repo, drop it:

```yaml
# ci.yml — remove windows-latest if not needed
        os: [ubuntu-latest]
```

Everything else (`uv sync`, `pre-commit run`, `pytest`) is portable — no changes.

### `install_and_test.yaml` — namespace check

No workflow changes needed. Already Ubuntu-only. Drop the `token:` line from the
namespace-check checkout (it was for write access, not needed for a read-only checkout):

```yaml
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
```

### `release.yml` — bump, build, publish

Three GitHub-specific steps need replacing.

**Push to origin** works unchanged — Forgejo injects `GITHUB_TOKEN` (same variable name)
and the `contents: write` permission gives it push rights.

**Replace `softprops/action-gh-release@v2`** with the Forgejo API:

```yaml
      - name: Create Forgejo release
        if: steps.bump.outputs.skipped != 'true'
        env:
          FORGEJO_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          FORGEJO_HOST: ${{ github.server_url }}
          REPO: ${{ github.repository }}
          VERSION: ${{ steps.bump.outputs.version }}
        run: |
          curl -s -X POST "${FORGEJO_HOST}/api/v1/repos/${REPO}/releases" \
            -H "Authorization: token ${FORGEJO_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "{\"tag_name\":\"v${VERSION}\",\"name\":\"v${VERSION}\",\"draft\":false,\"prerelease\":false}"
          RELEASE_ID=$(curl -s "${FORGEJO_HOST}/api/v1/repos/${REPO}/releases/tags/v${VERSION}" \
            -H "Authorization: token ${FORGEJO_TOKEN}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
          for f in dist/*; do
            curl -s -X POST "${FORGEJO_HOST}/api/v1/repos/${REPO}/releases/${RELEASE_ID}/assets" \
              -H "Authorization: token ${FORGEJO_TOKEN}" \
              -F "attachment=@${f}"
          done
```

**Replace `pypa/gh-action-pypi-publish` (OIDC → token)** — PyPI only trusts GitHub
Actions and GitLab CI as OIDC providers; Forgejo is not on that list. Use a classic
API token instead:

1. Create a PyPI token scoped to the project.
2. Store it as Forgejo repo secret `PYPI_API_TOKEN`.
3. Replace the publish step:

```yaml
      - name: Publish to PyPI
        if: steps.bump.outputs.skipped != 'true'
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          pip install twine
          twine upload dist/*
```

Remove `id-token: write` from the workflow permissions block.

### `docs.yml` — MkDocs deploy

Replace `mkdocs gh-deploy --force` with `mkdocs build` + `rsync` (see docs section above).
Full workflow:

```yaml
name: Docs

on:
  push:
    branches: [main]
    paths:
      - "docs/**"
      - "mkdocs.yml"
      - ".forgejo/workflows/docs.yml"
      - "src/**/*.py"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  deploy:
    name: Build and deploy docs
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: uv sync --extra docs

      - name: Deploy docs
        env:
          DOCS_DEPLOY_KEY: ${{ secrets.DOCS_DEPLOY_KEY }}
        run: |
          uv run mkdocs build
          mkdir -p ~/.ssh
          printf '%s\n' "${DOCS_DEPLOY_KEY}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          rsync -az --delete \
            -e "ssh -i ~/.ssh/deploy_key -o StrictHostKeyChecking=no" \
            site/ deploy@docs.murineshift.work:/var/www/docs/${{ github.event.repository.name }}/
```

### `pr-review.yml` — LLM review (optional)

The Claude API option works unchanged — it's just an HTTP call, no GitHub dependency.

Replace the `gh pr comment` call with the Forgejo API:

```bash
curl -s -X POST "${GITHUB_SERVER_URL}/api/v1/repos/${GITHUB_REPOSITORY}/issues/${PR_NUMBER}/comments" \
  -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
  -H "Content-Type: application/json" \
  -d "{\"body\": \"${REVIEW}\"}"
```

---

## URL and metadata updates

### `pyproject.toml`

```toml
[project.urls]
Homepage = "https://<forgejo-host>/<org>/murineshiftwork"
Documentation = "https://murineshiftwork.docs.murineshift.work"
"Issue Tracker" = "https://<forgejo-host>/<org>/murineshiftwork/issues"
```

### `mkdocs.yml`

```yaml
site_url: https://murineshiftwork.docs.murineshift.work/
repo_url: https://<forgejo-host>/<org>/murineshiftwork
repo_name: <org>/murineshiftwork
```

### `.copier-answers.yml`

```yaml
github_username: <org-or-user>
github_repo: murineshiftwork
forgejo_host: https://<forgejo-host>
```

---

## Secrets to configure in Forgejo

Set these at org level so all repos inherit them automatically.

| Secret | Value | Used by |
|---|---|---|
| `PYPI_API_TOKEN` | PyPI project-scoped token | release.yml publish step |
| `DOCS_DEPLOY_KEY` | SSH private key for the docs deploy user | docs.yml rsync step |
| `ANTHROPIC_API_KEY` | Anthropic API key | pr-review.yml (optional) |
| `GITHUB_TOKEN` | auto-injected by Forgejo | checkout, release API calls |

---

## Transition from GitHub: pull mirror + parallel CI

Forgejo can mirror repos from GitHub (pull mirror, auto-sync on a schedule or via
webhook). This lets you run both in parallel during the transition period — Forgejo
Actions run on Forgejo pushes; GitHub Actions still run on GitHub pushes until you cut
over.

To set up a pull mirror in Forgejo:

1. Create the repo on Forgejo (or migrate it).
2. Settings → Repository → Mirror Settings → Pull mirror → enter the GitHub HTTPS URL.
3. Forgejo syncs branches and tags on the configured interval.

Once the Forgejo workflow files are in `.forgejo/workflows/` (separate from
`.github/workflows/`), both CI systems run independently from the same codebase. Cut over
by removing the GitHub Actions files when you're satisfied with Forgejo CI.

Main differences to watch during parallel running:
- Secrets must be maintained in both systems until cutover.
- Forgejo has its own OIDC implementation (used for internal service-to-service auth),
  but PyPI does not trust it as a publishing identity — keep using API tokens there.

---

## templatepy considerations

`larsrollik/templatepy` is the Copier template that generated this repo's toolchain.
Migrating it to Forgejo means repos generated from it get Forgejo-compatible CI from the
start.

**Changes in templatepy:**

Add `.forgejo/workflows/` output alongside the existing `.github/workflows/` output in
the template — both coexist in generated repos, same as in murineshiftwork itself.

Add a `forgejo_host` Copier variable alongside `github_username`/`github_repo`:

```yaml
forgejo_host:
  type: str
  default: ""
  help: "Forgejo instance base URL (e.g. https://codeberg.org). Leave blank for GitHub."
```

Use conditional URL generation in `pyproject.toml.jinja` and `mkdocs.yml.jinja`:

```jinja
{% if forgejo_host %}
Homepage = "{{ forgejo_host }}/{{ github_username }}/{{ github_repo }}"
{% else %}
Homepage = "https://github.com/{{ github_username }}/{{ github_repo }}"
{% endif %}
```

Add a `pypi_publish_method` variable (`oidc` vs `token`) to gate the release workflow
publish step. Issue and PR templates in `.github/ISSUE_TEMPLATE/` work on Forgejo
unchanged — leave them where they are.

---

## Migration checklist

### One-time Forgejo setup
- [ ] Forgejo instance running and accessible
- [ ] Linux `act_runner` installed, registered, systemd service enabled
- [ ] Windows `act_runner` installed, registered, Windows service enabled
- [ ] Runners verified: push a test workflow and confirm each label works
- [ ] `/var/www/docs/` directory on docs server with correct permissions for `deploy` user
- [ ] Caddy installed and Caddyfile active; wildcard DNS record set
- [ ] Org-level secrets added: `PYPI_API_TOKEN`, `DOCS_DEPLOY_KEY`

### Per-repo workflow migration
- [ ] `mkdir -p .forgejo/workflows && cp .github/workflows/*.yml .forgejo/workflows/`  (keep `.github/workflows/` in place)
- [ ] `ci.yml`: remove `windows-latest` from matrix if Windows runner not registered yet
- [ ] `install_and_test.yaml`: drop `token:` from namespace-check checkout
- [ ] `release.yml`: replace `softprops/action-gh-release@v2` with Forgejo API call
- [ ] `release.yml`: replace `pypa/gh-action-pypi-publish` with `twine upload`
- [ ] `release.yml`: remove `id-token: write` from permissions
- [ ] `docs.yml`: replace `mkdocs gh-deploy` with `mkdocs build` + `rsync`
- [ ] `pr-review.yml`: replace `gh pr comment` with Forgejo API `POST /issues/:id/comments`
- [ ] `mkdocs.yml`: update `site_url`, `repo_url`, `repo_name`
- [ ] `pyproject.toml`: update `[project.urls]`
- [ ] Test release: tag manually and confirm PyPI publish works with token

### templatepy (if migrating template itself)
- [ ] Add `forgejo_host` Copier variable
- [ ] Add conditional URL generation in jinja templates
- [ ] Add `pypi_publish_method` variable for OIDC vs token
- [ ] Add `.forgejo/workflows/` output to template (alongside existing `.github/workflows/`)
- [ ] Update templatepy's own `.github/` → `.forgejo/` for its own CI

---

## Notes

**Keep GitHub mirror during transition:** `.github/workflows/` (GitHub) and
`.forgejo/workflows/` (Forgejo) coexist in the same repo without interference. Use
Forgejo's pull mirror to keep the Forgejo copy in sync with GitHub pushes.

**hatch-vcs + `fetch-depth: 0`:** Works unchanged — reads git tags locally after
checkout; no GitHub API dependency.

**gitleaks in pre-commit:** Fetches a binary at pre-commit install time. Works on runners
with internet access. The version is already pinned at `v8.30.0` in `.pre-commit-config.yaml`.

**commitizen bump pushes tags:** `git push origin "v${VERSION}"` requires `contents: write`
permission. Forgejo's auto-injected `GITHUB_TOKEN` has this for the repo it runs in — no
additional secrets needed.
