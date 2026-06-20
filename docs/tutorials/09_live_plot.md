# Tutorial 9: The live plot *(optional)*

## Prerequisites

[Tutorial 8: The plot spec](08_plot_spec.md).

## What you'll learn

- What the live plot shows during a running session.
- How to turn it on or off.
- Which task settings shape it.

## 1. What it is

The live plot is an on-rig window that draws the current session's panels as
trials complete, so you can watch behaviour in real time. It is rendered from the
same task-owned [plot spec](08_plot_spec.md) used for re-plotting, so what you
see live matches what you can redraw later. It needs a desktop session with Qt
available; install the `qt` extra:

```bash
pip install "murineshiftwork[qt]"
```

The live plot is optional. A session writes all its data whether or not the plot
is shown, so a headless rig simply leaves it off.

## 2. Turn it on or off

The live plot is controlled by the `show_live_plot` task setting. Disable it for
one run with a CLI override:

```bash
msw run -t sequence -s mouse001 --setup rig-a -ts show_live_plot=false
```

To make the choice permanent for a task or rig, set `show_live_plot` in the
task's [config-dir overlay](05_config_overlays.md) instead of passing the flag
each time:

```yaml
default:
  show_live_plot: false
```

## 3. Settings that shape the plot

When the plot is shown, a family of `online_plot_*` keys in the task's `task.yaml`
tune its appearance. They are ordinary task settings, so you can inspect them
with `msw tasks defaults <task>` and override them through any layer of the
[overlay chain](05_config_overlays.md). Examples from the `sequence` task:

| Setting | Effect |
|---|---|
| `online_plot_xlim_trials` | width of the trial x-axis window (0 = show all) |
| `online_plot_poke_xmax_s` | x-axis width for poke-time panels, in seconds |
| `online_plot_poke_log_scale` | log vs linear y-axis for the poke raster |

The exact keys are task-specific. Treat the task's own defaults as the
authoritative list rather than memorising names.

## You now know

The live plot is an optional, Qt-based real-time view rendered from the task's
plot spec, toggled with `show_live_plot` and tuned by `online_plot_*` settings.
It never affects what data is written, so it is safe to disable on headless rigs.

## Next

[Tutorial 10: The central monitor UI](10_monitor_ui.md) *(optional)*.
