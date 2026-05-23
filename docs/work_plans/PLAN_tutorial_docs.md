# Tutorial Documentation Series — Work Plan

*Created 2026-05-23.*

---

## Goal

Give a new user a layered path from "what is this?" to productive use, without
front-loading the full config system, hardware details, or optional features.
Each layer is a standalone page that ends with a working command the user can
run before reading further.

---

## Guiding principles

- Start with the minimal mental model. Three nouns: **setup**, **subject**, **task**.
- Each tutorial ends with something runnable — never finish a page without a
  concrete next step.
- Optional features are explicitly marked as optional and live in their own tier.
  A user who never uses hooks or the monitor should never see those pages.
- No forward references. Each page is self-contained given the prior pages.
- Separate "how to operate MSW" (tutorials) from "how MSW works" (concepts).
  Concepts live in `docs/concepts/`; tutorials live in `docs/tutorials/`.

---

## Proposed tutorial series

### Tier 0 — What is MSW?

**Page: `docs/tutorials/00_overview.md`**

One-page orientation. No commands yet.

- What problem MSW solves (behavioural task control + hardware abstraction)
- The three nouns: **setup** (one physical rig), **subject** (one animal),
  **task** (one protocol)
- How a session works at a high level: CLI starts a session → task runs trials →
  data is written → session ends
- What MSW does NOT do: analysis, surgery scheduling, animal tracking
- Pointer to Tier 1

---

### Tier 1 — First session on a working rig

**Pages (sequence matters):**

1. `docs/tutorials/01_install.md`
   - `pip install murineshiftwork` (or editable clone)
   - `msw --version` to verify
   - Note: no hardware needed for the smoke test in tutorial 02

2. `docs/tutorials/02_first_session.md`
   - `msw init <config_dir>` — one-time machine setup
   - `msw subject add -s mouse001`
   - `msw run -t _test_minimal_task -s mouse001` (no hardware)
   - What files were written and where
   - Ends with: user has run a session, seen the output files

3. `docs/tutorials/03_setup_config.md`
   - What a setup YAML contains (device ports, hooks, metadata)
   - `msw setup create rig-a`
   - `msw run ... --setup rig-a`
   - How `--setup` affects port resolution (no more `-b /dev/ttyACM0`)

4. `docs/tutorials/04_task_settings.md`
   - `msw tasks defaults sequence` — inspect what a task exposes
   - `-ts KEY=VALUE` overrides
   - `--task-mode <name>` presets
   - When to use each (one-off vs. permanent)

---

### Tier 2 — Config system

**Pages:**

5. `docs/tutorials/05_config_overlays.md`
   - The overlay chain: bundled → config-dir → task-mode → subject → CLI
   - Creating a `msw_configs/tasks/sequence/task.yaml` overlay
   - Subject-level `task_overrides` (persisted by `save_session_end`)
   - Ends with: user has a config-dir overlay that survives package upgrades

6. `docs/tutorials/06_subject_management.md`
   - `msw subject add / list / rename / remove`
   - What the subject YAML stores (task_overrides, persistent level progression)
   - How `start_level` gets written back automatically

---

### Tier 3 — Session data

**Pages:**

7. `docs/tutorials/07_session_files.md`
   - What files a session writes: `.msw.session.yaml`, `.jsonl`, Bpod `.pkl`
   - Reading a session in Python: `msw.readers`
   - The `msw_format_version` field and what it means for readers
   - Ends with: user can load their own session data in a notebook

8. `docs/tutorials/08_plot_spec.md`
   - What `plot_spec.yaml` is (task-owned panel definition)
   - Where to find it, how to read it
   - How to use it to re-plot a historical session from JSONL
   - Why the spec is written into the session directory

---

### Tier 4 — Optional: live monitoring

**Pages (each fully optional):**

9. `docs/tutorials/09_live_plot.md` *(optional)*
   - PyQtGraph online plot: what it shows, how to disable (`show_live_plot: false`)
   - Config keys that affect it (`online_plot_*` in task.yaml)

10. `docs/tutorials/10_monitor_ui.md` *(optional)*
    - The central UI: what it is, what it requires (Docker on a lab server)
    - Setting `ui_url` and `ui_bearer_token` in `msw_machine.yaml`
    - What the UI shows: active sessions, trial stream, per-task plots
    - Note: data still written locally even if UI is down

---

### Tier 5 — Optional: hooks and automation

**Pages:**

11. `docs/tutorials/11_hooks.md` *(optional)*
    - What hooks are and when they run (pre/post, fatal/non-fatal)
    - Writing a minimal hook class
    - Registering a hook in the setup YAML

12. `docs/tutorials/12_post_processing.md` *(optional)*
    - `msw post run` — the post-session pipeline
    - Anatomy of a post-run script
    - Common use: sync to NAS, push to Labwatch, generate summary plot

---

### Tier 6 — Optional: hardware and calibration

**Pages:**

13. `docs/tutorials/13_hardware_abstraction.md` *(optional)*
    - `DeviceProtocol` — what the four methods are
    - `HardwareManager` — how devices are wired in
    - Adding a new device type (worked example)

14. `docs/tutorials/14_calibration.md` *(optional)*
    - Liquid calibration: `_calibration_liquid_static`, `_calibration_liquid_dynamic`
    - Reading calibration output with `msw calibration`
    - When to recalibrate

---

## What already exists vs. what needs writing

| Tutorial | Status |
|---|---|
| `00_overview.md` | Not written |
| `01_install.md` | Partial (`docs/getting_started/installation.md`) — needs rewrite as tutorial |
| `02_first_session.md` | Partial (`getting_started/quickstart.md`) — split and expand |
| `03_setup_config.md` | Covered in `cli/setup.md` — needs tutorial wrapper |
| `04_task_settings.md` | Covered in `getting_started/quickstart.md` — needs extraction |
| `05_config_overlays.md` | Covered in `concepts/config_system.md` — needs tutorial version |
| `06_subject_management.md` | Covered in `cli/subject.md` — needs tutorial wrapper |
| `07_session_files.md` | Covered in `concepts/session_files.md` — needs tutorial version |
| `08_plot_spec.md` | Not written |
| `09_live_plot.md` | Not written |
| `10_monitor_ui.md` | Not written (blocked on UI implementation) |
| `11_hooks.md` | Covered in `concepts/hook_system.md` — needs tutorial wrapper |
| `12_post_processing.md` | Not written |
| `13_hardware_abstraction.md` | Not written |
| `14_calibration.md` | Partial (`getting_started/calibration.md`) |

Priority order for writing: 00 → 02 → 05 → 07 → 08 (these are the gaps most
likely to block a new user or a new collaborator reading historical data).

---

## Format conventions for all tutorial pages

- **Title**: `# Tutorial N — <Topic>`
- **Prerequisites**: list of prior tutorials (or "none")
- **What you'll learn**: 3 bullet points max
- **Body**: numbered steps, each step has a command and expected output excerpt
- **You now know**: 2-sentence summary
- **Next**: link to the next tutorial and one optional lateral link

---

## Relationship to existing docs

Tutorials teach by doing. Concepts explain the why. CLI reference explains flags.
These three are deliberately separate and cross-link but do not duplicate.

```
tutorials/   ← "follow along" — for new users
concepts/    ← "understand why" — reference for experienced users
cli/         ← "look up a flag" — command reference
```
