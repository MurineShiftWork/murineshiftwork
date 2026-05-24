# GitHub CLI Reference

Standard `gh` commands used across repos in this org. Replace `OWNER/REPO` with the target (e.g. `larsrollik/pypulsepal`).

---

## Workflow runs

```sh
# List all runs
gh run list --repo OWNER/REPO

# Watch a specific run live
gh run watch <run-id> --repo OWNER/REPO

# View logs for a run (failed steps only)
gh run view <run-id> --repo OWNER/REPO --log-failed

# Re-run failed jobs only
gh run rerun <run-id> --failed --repo OWNER/REPO

# Delete all workflow runs (clear history)
gh run list --repo OWNER/REPO --json databaseId -q '.[].databaseId' \
  | xargs -I{} gh run delete {} --repo OWNER/REPO
```

---

## Pull requests

```sh
# List open PRs
gh pr list --repo OWNER/REPO

# View a PR (summary + status)
gh pr view <number> --repo OWNER/REPO

# Check CI status for a PR
gh pr checks <number> --repo OWNER/REPO

# Merge a PR (rebase — preferred; keeps linear history)
gh pr merge <number> --rebase --repo OWNER/REPO

# Merge a PR (squash)
gh pr merge <number> --squash --repo OWNER/REPO

# Close a PR without merging
gh pr close <number> --repo OWNER/REPO
```

---

## Releases and tags

```sh
# List releases
gh release list --repo OWNER/REPO

# View a release
gh release view <tag> --repo OWNER/REPO

# Delete a release AND its tag
gh release delete <tag> --repo OWNER/REPO --yes
git push origin :refs/tags/<tag>

# Create a release manually (rarely needed — release.yml handles this)
gh release create <tag> --title "<tag>" --notes "" --repo OWNER/REPO
```

---

## Issues

```sh
# List open issues
gh issue list --repo OWNER/REPO

# View an issue
gh issue view <number> --repo OWNER/REPO

# Create an issue
gh issue create --title "Title" --body "Body" --repo OWNER/REPO

# Close an issue
gh issue close <number> --repo OWNER/REPO

# Develop a branch from an issue (creates branch linked to issue)
gh issue develop <number> --repo OWNER/REPO --name ft/branch-name
```

---

## Repo and Pages

```sh
# View repo info
gh repo view OWNER/REPO

# Check GitHub Pages config (source branch, URL, status)
gh api repos/OWNER/REPO/pages

# List secrets
gh secret list --repo OWNER/REPO

# Set a secret
gh secret set SECRET_NAME --body "value" --repo OWNER/REPO
```

---

## Notes

- `--repo OWNER/REPO` can be omitted when inside the repo's git directory.
- Merge strategy for this org: **rebase** (`--rebase`) — keeps linear history, required by branch protection.
- To delete a tag that release.yml created on a failed run: delete the release first, then push the tag deletion. Order matters — GitHub won't delete a tag with a release attached.
