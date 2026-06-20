# Tutorial 0: What is MurineShiftWork?

## Prerequisites

None. This is the starting point.

## What you'll learn

- What problem MSW solves and what it deliberately leaves to other tools.
- The three nouns that everything else is built on: setup, subject, task.
- What happens, at a high level, when you run a session.

## The problem MSW solves

MurineShiftWork (MSW) runs animal behavioural tasks on hardware rigs and writes
the resulting data in a consistent, machine-readable layout. It sits between two
things that are otherwise hard to connect:

- A **behavioural protocol** (the logic of trials, rewards, stimuli, and how a
  session progresses).
- The **physical hardware** on a rig (a Bpod state machine, valves, optogenetic
  stimulators, stages, cameras, ephys systems).

MSW lets a protocol be written once and then run on any rig, because the rig's
wiring is described separately from the protocol. The same command shape works
on every machine in a lab, and every session it produces can be read back the
same way years later.

## The three nouns

Almost everything in MSW is expressed as a combination of three independent
ideas. Keep these straight and the rest of the system follows.

| Noun | Means | Lives as |
|---|---|---|
| **setup** | one physical rig: which devices are wired in and on which ports | a YAML file under `setups/` |
| **subject** | one animal: its identity and any per-animal parameter overrides | a YAML file under `subjects/` |
| **task** | one protocol: the trial logic and its tunable defaults | a Python task package plus a `task.yaml` |

A single session is one (setup, subject, task) triple. You pick a task to run, an
animal to run it on, and the rig it runs on. None of the three knows about the
others: a task does not hard-code a rig, and a rig does not hard-code an animal.
This separation is why the same protocol runs unchanged across rigs, and why
swapping an animal never means editing protocol code.

A fourth idea, the **session**, is what you get when the three nouns are combined
and executed: a single run that produces a directory of data files.

## What a session looks like at a high level

When you start a session, MSW does the following in order:

1. Resolves settings by combining the task defaults, the rig's setup file, the
   subject's overrides, and any command-line flags into one effective
   configuration.
2. Connects to the hardware the task needs (or simulates it when no hardware is
   present).
3. Runs the task: trials execute, rewards or stimuli are delivered, and each
   trial is recorded as it completes.
4. Writes the data: a session metadata file, a trial-by-trial data file, and a
   log, all under a predictable per-subject directory.
5. Ends cleanly: hardware is released, and any per-subject progress (for example
   a training level) is written back so the next session resumes where this one
   left off.

You never have to assemble these steps by hand. A single `msw run` command does
all of it.

## What MSW does not do

MSW is an acquisition framework, not an analysis suite or a colony manager. It
deliberately leaves the following to other tools:

- It does not analyse your data. It writes data in a documented format and gives
  you readers to load it; statistics and figures are yours to build.
- It does not schedule surgeries, manage breeding, or track animal welfare.
- It does not replace your electrophysiology or imaging acquisition software. It
  links to those systems so their data lines up in time, but they record their
  own files.

This narrow focus is intentional. By doing one thing, MSW stays stable while the
science around it changes.

## You now know

MSW runs behavioural protocols on hardware rigs and writes consistent,
re-readable session data, and it does so by keeping the rig (setup), the animal
(subject), and the protocol (task) as three independent things. A session is one
(setup, subject, task) triple executed by a single command.

## Next

[Tutorial 1: Installing MSW](01_install.md). For the design rationale behind the
three-noun model, see [Architecture](../concepts/architecture.md).
