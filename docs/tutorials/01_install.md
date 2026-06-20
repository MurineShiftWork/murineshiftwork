# Tutorial 1: Installing MSW

## Prerequisites

[Tutorial 0: What is MurineShiftWork?](00_overview.md)

## What you'll learn

- How to install MSW and confirm the `msw` command works.
- Which optional extras exist and when you need them.
- That the smoke test in the next tutorial needs no hardware.

## 1. Install the package

MSW is published on PyPI. A plain install gives you the `msw` command and the
core framework:

```bash
pip install murineshiftwork
```

To run the bundled calibration and hardware-test tasks (used in later
tutorials), add the `tasks` extra:

```bash
pip install "murineshiftwork[tasks]"
```

## 2. Verify the install

```bash
msw --version
```

Expected output (the version number will differ):

```
msw 2.1.1
```

If the command is found and prints a version, MSW is installed correctly.

## 3. Know which extras you may want later

A plain install is enough for the next two tutorials. Hardware drivers and
optional features are packaged as extras so a minimal rig stays small. You only
need an extra when you reach the feature it provides.

| Extra | Adds | Needed for |
|---|---|---|
| `tasks` | bundled calibration and test tasks | the smoke test in Tutorial 2 |
| `qt` | PyQt and pyqtgraph | the live plot (Tutorial 9) |
| `calibration` | serial scale drivers | valve calibration (Tutorial 14) |
| `oe` | Open Ephys controller | ephys-linked sessions |
| `pulsepal` | PulsePal driver | optogenetic stimulation |
| `full` | all of the above | a complete acquisition rig |

```bash
pip install "murineshiftwork[full]"   # everything for a real rig
```

## 4. No hardware needed yet

The next tutorial runs a real session end to end without any rig attached, using
simulation mode. You do not need a Bpod, valves, or any serial device to follow
along. A laptop is enough.

## You now know

You have MSW installed and confirmed `msw --version` works, and you know that
optional hardware features are opt-in extras you add only when you reach them.
The next tutorial runs a full session with no hardware attached.

## Next

[Tutorial 2: Your first session](02_first_session.md). For the full extras
table, see [Installation](../getting_started/installation.md).
