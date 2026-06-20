# Tutorial 8: The plot spec

## Prerequisites

[Tutorial 7: Reading session files](07_session_files.md).

## What you'll learn

- What a plot spec is and why it ships with the task, not the plotting code.
- How to read a plot spec and map its panels to fields in the trial data.
- Why a copy of the spec is written into every session directory.

## 1. What a plot spec is

A **plot spec** is a YAML description of how a task's data should be visualised:
which panels to draw, what each panel shows, and which trial-data fields feed it.
It is declarative. It names panels and fields; it contains no plotting code.

The key design point: the spec is **owned by the task**. The task author knows
what its trials mean, so the task decides how they are best displayed. A generic
renderer reads the spec and draws it. This keeps the renderer task-agnostic and
lets a task evolve its plots without touching shared plotting code.

## 2. Read a task's plot spec

Each task package ships a `plot_spec.yaml`. Here is the shape of the `sequence`
task's spec, trimmed to two panels:

```yaml
version: 1
task: sequence
panels:
  - id: outcomes_perf
    title: "Outcomes & rolling performance"
    type: rolling_mean
    fields:
      x: trial_index
      value: perf_buffer_mean
      scatter_flag: is_correct
    options:
      y_range: [-0.15, 1.15]

  - id: session_progress
    title: "Session progress"
    type: cumulative_sum
    fields:
      x: elapsed_time_min
      value: reward_ul
    options:
      y_label: "Reward (µL)"
```

Each panel has three parts:

- `type`: the kind of plot (for example `rolling_mean`, `timeseries`,
  `histogram`, `raster`, `cumulative_sum`).
- `fields`: which columns of the trial DataFrame supply the data. Every name
  here (`trial_index`, `reward_ul`, `is_correct`, ...) is a column the task
  writes into its `.msw.df.jsonl`.
- `options`: panel-specific display settings (axis ranges, labels, filters).

Because `fields` reference the trial data by column name, the spec is the bridge
between [the session's trial file](07_session_files.md) and a figure.

## 3. Why the spec is copied into each session

When a session runs, MSW writes a copy of the active plot spec into the session
directory as `<basename>.msw.plot_spec.yaml`. This is a deliberate provenance
choice. The spec a task ships can change between versions, but the copy stored
beside the data records exactly how that session was meant to be displayed at the
time it ran. To re-plot a historical session, you read the spec from the session
directory, not from the currently installed package, so the figure matches the
data even after the task has moved on.

## 4. Re-plotting a historical session

The workflow to redraw an old session is:

1. Load the session's trial data into a DataFrame (see
   [Tutorial 7](07_session_files.md)).
2. Read the session's own `*.msw.plot_spec.yaml`.
3. For each panel, pull the columns named in `fields` from the DataFrame and draw
   the `type` of plot the panel asks for.

Because the spec travels with the data, this works for any session you can still
read, regardless of which task version is installed today.

## You now know

A plot spec is a task-owned, declarative YAML that names panels and the trial
columns that feed them, keeping the renderer task-agnostic. A copy is written
into every session directory so historical data can always be re-plotted exactly
as intended.

## Next

[Tutorial 9: The live plot](09_live_plot.md) *(optional)*. To see the trial
columns a spec references, inspect a session's `.msw.df.jsonl` from
[Tutorial 7](07_session_files.md).
