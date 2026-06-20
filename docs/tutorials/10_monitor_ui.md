# Tutorial 10: The central monitor UI *(optional, planned)*

## Prerequisites

[Tutorial 9: The live plot](09_live_plot.md).

## What you'll learn

- What the central monitor is intended to be and how it will fit in.
- How a rig is configured to relay to it.
- Why your data is safe regardless of the monitor's state.

> **Status: planned.** The central monitor is not yet available end to end. The
> backend endpoints it depends on are not implemented, so this page describes the
> intended design and the configuration that prepares a rig for it. It does not
> describe a working feature. Nothing here is required to acquire data.

## 1. What it is meant to be

The central monitor is a single web view that aggregates live status from every
rig in a lab: which sessions are active, their incoming trial stream, and the
per-task panels (the same ones the [live plot](09_live_plot.md) shows locally).
The goal is one screen for "what is every rig doing right now", instead of
walking the room.

Where the [live plot](09_live_plot.md) is per-rig and local, the monitor is
central and shared. A rig relays its session activity to the monitor over the
network; the monitor renders it.

## 2. How a rig will be configured

A rig points at the monitor through its per-machine config file,
`~/.murineshiftwork/msw_machine.yaml`. The relevant keys are:

| Key | Purpose |
|---|---|
| `msw_ui_url` | base URL of the central monitor service |
| `logagent_api_token` | bearer token the rig uses to authenticate to it |

```yaml
# ~/.murineshiftwork/msw_machine.yaml
msw_ui_url: http://monitor.example.internal:3000
logagent_api_token: <token>
```

With these set, a rig is prepared to relay once the backend is available. Use a
generic internal hostname and a real token from your own deployment; never commit
a token to a config repo.

## 3. Data is never at the monitor's mercy

By design, the monitor is a read-only observer. Sessions write all their data to
local disk exactly as described in [Tutorial 7](07_session_files.md), whether the
monitor is reachable, down, or not deployed at all. Relaying status to the
monitor is best-effort and never blocks or alters acquisition. If the monitor is
unavailable, you lose the live overview, not any data.

## You now know

The central monitor is a planned, shared web view of every rig's live activity,
configured per-rig through `msw_ui_url` and `logagent_api_token`. It is a
read-only observer, so local data is always written regardless of its state, and
none of it is required to run sessions today.

## Next

[Tutorial 11: Hooks](11_hooks.md) *(optional)*.
