# Standard Operating Prompts

Short-form phrases for recurring code work. Paste as-is or adapt the bracketed parts.

---

## Work planning

**`sync roadmap`**
> Bring ROADMAP.md TODO/DONE list up to date with the current code and git state.
> Tick completed items, move them to DONE with `· YYYY-MM-DD · short-hash`.
> Remove stale text. Do not add new headings.

**`tick [item name]`**
> Mark [item name] done in ROADMAP TODO. Move to DONE:
> `- [x] [item] · YYYY-MM-DD · short-hash-of-relevant-commit`

**`sprint check`**
> Report go/no-go for starting the next sprint. Check: git status, tests pass,
> ROADMAP TODO has no incomplete prerequisite items, stale docs updated.
> Max 5 lines.

**`what's open`**
> List all items currently in ROADMAP TODO with one-line status.

---

## Git and versioning

**Branch naming convention**

| Prefix | Use |
|---|---|
| `ft/` | New feature or capability (`ft/msw-agent`, `ft/vue-frontend`) |
| `bug/` | Bug fix (`bug/bpod-usb-disconnect`, `bug/sound-device-fallback`) |
| `chore/` | Non-functional: deps, CI, docs, config (`chore/pre-commit-update`) |
| `refactor/` | Code restructure, no behaviour change |

Rule: one concern per branch. Open a **draft PR** immediately after the first real commit so work is visible. Merge to `main` when pre-commit and CI are green.

**`commit msg`**
> Write a conventional commit message for all uncommitted changes in the working tree.
> Include: type, scope if meaningful, bullet list of changes, test count delta.
> State the version bump type (major/minor/patch) the message would trigger.

**Multi-line commit messages** — use a heredoc to preserve indentation in the body:

```bash
git commit -m "$(cat <<'EOF'
feat(scope): subject line

- bullet one
- bullet two
EOF
)"
```

**`version`**
> State the current version, what bump type the uncommitted/unreleased changes warrant,
> and what the next version would be. One line each.

---

## Code work

**`review diff`**
> Apply review prompt #1 (general correctness) from CODE_REVIEW.md to the current
> uncommitted diff or the named files. Report as: file:line — severity — description.

**`review [prompt-name]`**
> Apply the named prompt from CODE_REVIEW.md (e.g. `review platform compat`,
> `review hardware safety`, `review test coverage`).

**`add tests [item]`**
> Write pytest tests for [item]. Cover: happy path, error paths, edge cases.
> Use SimBpod for hardware paths; tmp_path for filesystem. No live hardware.

**`fix lint`**
> Fix all ruff and mypy violations in the named file(s) or the current diff.
> Do not change behaviour.

---

## Docs

**`fill [doc path]`**
> Fill in the skeleton at [doc path] with accurate content derived from the current
> source code. Do not invent behaviour. Cross-link related docs and CLI pages.

**`update hook doc`** / **`update config doc`** / **`update cli doc [subcommand]`**
> Bring the named doc page up to date with the current implementation.

---

## Hardware probing

**`probe bpods`**
> Run `python3 scripts/probe_bpods.py` to connect to every setup in sequence and
> print the Bpod hardware info box (firmware, machine type, port config, hardware counters).
> Skips setups without a bpod device. Marks setups whose USB path does not resolve as NOPORT.

```bash
# All setups (uses config_dir from machine config)
python3 scripts/probe_bpods.py

# Subset
python3 scripts/probe_bpods.py --setups setup-1 npxb

# More retries for a flaky device
python3 scripts/probe_bpods.py --retries 5 --retry-delay 3.0
```

**Output status codes:**

| Code | Meaning |
|---|---|
| `OK` | Connected and hardware info printed |
| `FAIL` | Device found but connection failed after all retries |
| `NOPORT` | `/dev/serial/by-path/...` symlink not present (device unplugged or powered off) |
| `NOBPOD` | Setup YAML has no `bpod` device entry |
| `SKIP` | Setup YAML could not be parsed |

Log section (WARNING+) shows retry attempts and exact exception for FAIL cases.
Exit code: 0 if all reachable setups connected, 1 if any FAIL.

---

## Licensing policy

**MSW core and research IP** (`murineshiftwork`, `rpi-camera-ensemble`,
`msw-flir-bonsai`, `ttl-barcoder`, and any package embodying substantial
operational or research logic): use the **custom noncommercial licence**
(`LICENSE` in `murineshiftwork`). Restricts commercial use and withholds
patent rights. Not copyleft — does not reach into code that imports it.

**Hardware-interface and utility packages** (`pypulsepal`, serial-scale-*,
`rfid-to-url`, `one-axis-stage`): use **BSD-3-Clause**. Allows commercial
use, non-viral, requires attribution, blocks endorsement use of the
author's name without permission. PyPI classifier:
`License :: OSI Approved :: BSD License`.

**New packages** (`templatepy`-derived): default to the custom noncommercial
licence unless the package is purely a hardware wrapper with no MSW logic,
in which case BSD-3-Clause.

**Avoid all copyleft licences** (GPL, AGPL, LGPL, EUPL). Copyleft infects
dependent code and creates ambiguity about whether the custom noncommercial
terms survive. The goal is to protect authorship and attribution, not to
impose terms on dependents.

No PolyForm variants. No CC licences for code.

**Contact for commercial or patent licensing:** lars@rollik.me

### Repo licence status

**Outer licence** = the licence of the repository itself (what the template/tool is).
**Inner licence** = the licence baked into projects generated from a template.
These are independent questions.

| Repo | Outer licence | Status | Notes |
|---|---|---|---|
| `murineshiftwork` | custom noncommercial | ✓ done | canonical text lives here |
| `murineshiftwork-blocking` | all rights reserved | ✓ done | name-reservation stub |
| `rpi-camera-ensemble` | custom noncommercial | ✓ done | |
| `msw-flir-bonsai` | custom noncommercial | ✓ done | |
| `ttl-barcoder` | custom noncommercial | ✓ done | |
| `acquisition-namespace` | custom noncommercial | ✓ done | |
| `msw-plugin-api` | custom noncommercial | ✓ done | zero-dep; Protocols + HostSessionInfo |
| `msw-open-ephys` | custom noncommercial | ✓ done | |
| `rpi_camera_ensemble_dev` | custom noncommercial | ✓ done | dev copy in provision_rpi |
| `pypulsepal` | BSD-3-Clause | ✓ done | hardware wrapper; `_arcom.py` vendored |
| `serial_scale_hx711` | BSD-3-Clause | ✓ done | |
| `serial_scale_bench` | BSD-3-Clause | ✓ done | |
| `one-axis-stage` | BSD-3-Clause | ✓ done | |
| `rfid-to-url` | BSD-3-Clause | ✓ done | |
| `templatepy` (outer) | BSD-3-Clause | ✓ done | the template repo itself |
| `templatevue` (outer) | BSD-3-Clause | ✓ done | |
| `templatepy` (inner) | conditional via copier | ✓ done | default noncommercial; bsd3 option |
| `templatevue` (inner) | conditional via copier | ✓ done | default noncommercial; bsd3 option |

---

## One-shot useful phrases

| Say | Means |
|---|---|
| `sprint check` | Ready to start next sprint? |
| `sync roadmap` | Tick done items, clean stale text |
| `commit msg` | Conventional commit for current diff |
| `tick opto` | Mark opto consolidation done in ROADMAP |
| `review diff` | Correctness review of current changes |
| `add tests sequence writeback` | Write tests for sequence level writeback |
| `fill docs/cli/run.md` | Fill CLI reference page from parser.py |
| `what's open` | List current TODO items |
