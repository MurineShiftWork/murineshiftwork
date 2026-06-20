# Tutorial 2: Your first session

## Prerequisites

[Tutorial 1: Installing MSW](01_install.md), with the `tasks` extra installed.

## What you'll learn

- The one-time machine setup that tells MSW where your config and data live.
- How to register a subject and run a complete session with no hardware.
- Which files a session writes, and where to find them.

## 1. Initialise this machine

MSW keeps two things separate: a shared **config directory** (your setups,
subjects, and task overrides) and a **data directory** (where sessions are
written). `msw init` records both in a small per-machine file so you do not have
to pass them on every command.

```bash
msw init ~/msw_configs --data-dir ~/data
```

The `config_dir` (here `~/msw_configs`) is a required positional argument;
`--data-dir` is optional. Expected output:

```
┌──────────────────────────────────────────────┐
│ Initialised MSW on this machine.              │
│ Config dir: /home/you/msw_configs             │
│ Data dir:   /home/you/data                    │
│ Machine config: /home/you/.murineshiftwork/msw_machine.yaml
│                                                │
│ Next steps:                                    │
│   murineshiftwork setup create <setup_name>    │
│   murineshiftwork subject add -s <subject_name>│
└──────────────────────────────────────────────┘
```

This creates the `setups/`, `subjects/`, and `tasks/` subfolders inside your
config directory. You run `msw init` once per machine.

## 2. Register a subject

A subject is one animal. Register one before running a session on it:

```bash
msw subject add -s mouse001
```

Expected output:

```
┌──────────────────────────────────────────────────────────┐
│ Registered subject 'mouse001' at                          │
│ /home/you/msw_configs/subjects/mouse001.yaml              │
└──────────────────────────────────────────────────────────┘
```

## 3. Run a session with no hardware

The `_test_minimal_task` is a tiny built-in protocol used for smoke tests. The
`--simulate` flag runs it without any real hardware: MSW substitutes a simulated
Bpod and skips all serial-port and preflight checks.

```bash
msw run -t _test_minimal_task -s mouse001 --simulate
```

The session runs to completion and prints an end-of-session summary line, for
example:

```
INFO  Task finished.
```

The two flags you used here are the core of every run:

- `-t / --task`: the task name (a unique substring is enough).
- `-s / --subject`: the subject name.

Without `--simulate`, MSW would try to open a serial connection to real
hardware. You will attach a real rig in [Tutorial 3](03_setup_config.md).

## 4. Find the files the session wrote

Sessions are written under your data directory, organised by subject:

```
~/data/
└── mouse001/
    └── mouse001__<datetime>__session__test_minimal_task/
        └── mouse001__<datetime>___test_minimal_task/
            ├── <basename>.msw.session.yaml
            ├── <basename>.msw.df.jsonl
            └── <basename>.msw.log
```

The three files you will care about most:

- `.msw.session.yaml`: session metadata (task, subject, settings, version).
- `.msw.df.jsonl`: the trial-by-trial data, one JSON record per line.
- `.msw.log`: a human-readable log of the run.

You will learn to read these in [Tutorial 7](07_session_files.md).

## You now know

You have initialised MSW on your machine, registered a subject, and run a
complete session in simulation mode without any hardware. You also know the
three core files every session writes and where they land.

## Next

[Tutorial 3: Describing a rig with a setup config](03_setup_config.md). To see
every task available to run, use `msw tasks list`.
