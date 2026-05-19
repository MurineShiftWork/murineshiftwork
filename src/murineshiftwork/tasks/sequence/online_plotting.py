from __future__ import annotations

import time
from multiprocessing import Process, Queue

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

_FALLBACK_COLORS = ["#34475C", "#4BA5BF", "#90C681", "#FFD062", "#ED6F5D", "#ABBAB3"]


def _nan_vec(length):
    return np.full(length, np.nan)


def _seq_color_map(sequence: list, colors: list) -> dict[int, str]:
    """Map each port in sequence to its positional color."""
    result = {}
    for i, port in enumerate(sequence):
        result[port] = (
            colors[i] if i < len(colors) else (colors[-1] if colors else "#ffffff")
        )
    return result


class _QueueMonitor(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(dict)
    exit_signal = QtCore.pyqtSignal(bool)

    def __init__(self, data_queue=None, kill_queue=None):
        super().__init__()
        self.data_queue = data_queue
        self.kill_queue = kill_queue

    def run(self):
        while True:
            time.sleep(0.1)
            if not self.kill_queue.empty():
                self.exit_signal.emit(True)
                break
            if not self.data_queue.empty():
                self.update_signal.emit(self.data_queue.get())


class OnlinePlottingForSA(Process):
    """Six-panel live plot for the Sequence Automated task.

    Layout (2 columns × 3 rows):

    Col 0 (linked trial x-axis)          Col 1
    ┌────────────────────────────┬──────────────────────────────┐
    │ [0,0] Outcomes + rolling   │ [0,1] IPI distributions      │
    │        perf (combined)     │       per sequence step      │
    ├────────────────────────────┼──────────────────────────────┤
    │ [1,0] Training level +     │ [1,1] Cumulative water (µL)  │
    │        change markers      │       vs session time        │
    ├────────────────────────────┼──────────────────────────────┤
    │ [2,0] Poke-sequence raster │ [2,1] Sequence duration on   │
    │       (time × trial)       │       correct trials         │
    └────────────────────────────┴──────────────────────────────┘

    Port colors are assigned by sequence position (1st port → 1st color, etc.).
    Transition histograms use the destination port's color.
    Level curve uses the last (neutral) color from the scheme.
    """

    daemon = True

    def __init__(
        self,
        session_name: str = "unnamed",
        data_queue: Queue | None = None,
        kill_queue: Queue | None = None,
        n_max_trials: int = 1500,
        n_levels: int = 50,
        progression_threshold: float = 0.9,
        regression_threshold: float = 0.2,
        sequence: list | None = None,
        port_colors: list | None = None,
    ):
        super().__init__()
        self.session_name = session_name
        self.data_queue = data_queue
        self.kill_queue = kill_queue
        self.n_max_trials = n_max_trials
        self.n_levels = n_levels
        self.progression_threshold = progression_threshold
        self.regression_threshold = regression_threshold
        self.sequence = sequence or []
        _c = list(port_colors) if port_colors else []
        self.colors = _c if _c else _FALLBACK_COLORS

    def run(self):
        app = pg.mkQApp("Sequence Automated")
        win = pg.GraphicsLayoutWidget(show=True, title=f"SA | {self.session_name}")
        win.resize(1500, 900)

        n = self.n_max_trials
        perf_arr = _nan_vec(n)
        levels_arr = _nan_vec(n)

        seq_color = _seq_color_map(self.sequence, self.colors)
        # Color for things NOT tied to a specific sequence port (level line, etc.)
        neutral_color = self.colors[-1] if self.colors else "#ABBAB3"

        def _qc(hex_str: str) -> QtGui.QColor:
            return QtGui.QColor(hex_str)

        # ── [0,0] Outcomes + rolling performance (combined) ───────────────
        p_out = win.addPlot(row=0, col=0, title="Outcomes & rolling performance")
        p_out.setYRange(-0.05, 1.05)
        p_out.setLabel("left", "Correct")
        p_out.addLine(
            y=self.progression_threshold,
            pen=pg.mkPen(neutral_color, width=1, style=QtCore.Qt.PenStyle.DashLine),
        )
        p_out.addLine(
            y=self.regression_threshold,
            pen=pg.mkPen("#ED6F5D", width=1, style=QtCore.Qt.PenStyle.DashLine),
        )
        scatter_correct = pg.ScatterPlotItem(
            pen=None, symbol="o", size=5, brush=pg.mkBrush(144, 198, 129, 160)
        )
        scatter_incorrect = pg.ScatterPlotItem(
            pen=None, symbol="o", size=5, brush=pg.mkBrush(237, 111, 93, 160)
        )
        curve_perf = pg.PlotDataItem(pen=pg.mkPen("w", width=2))
        p_out.addItem(scatter_correct)
        p_out.addItem(scatter_incorrect)
        p_out.addItem(curve_perf)

        correct_xs: list = []
        correct_ys: list = []
        incorrect_xs: list = []
        incorrect_ys: list = []

        # ── [1,0] Training level + change markers ─────────────────────────
        p_level = win.addPlot(row=1, col=0, title="Training level")
        p_level.setYRange(0, self.n_levels + 1)
        p_level.setLabel("left", "Level")
        curve_level = pg.PlotDataItem(pen=pg.mkPen(neutral_color, width=2))
        p_level.addItem(curve_level)

        lvl_up_sc = pg.ScatterPlotItem(
            pen=pg.mkPen("#90C681", width=1),
            symbol="t1",
            size=11,
            brush=pg.mkBrush(144, 198, 129, 210),
        )
        lvl_dn_sc = pg.ScatterPlotItem(
            pen=pg.mkPen("#ED6F5D", width=1),
            symbol="t",
            size=11,
            brush=pg.mkBrush(237, 111, 93, 210),
        )
        p_level.addItem(lvl_up_sc)
        p_level.addItem(lvl_dn_sc)
        lvl_up_x: list = []
        lvl_up_y: list = []
        lvl_dn_x: list = []
        lvl_dn_y: list = []

        # ── [2,0] Poke-sequence raster ────────────────────────────────────
        p_pokes = win.addPlot(row=2, col=0, title="Poke sequence (y = time in trial)")
        p_pokes.setLabel("left", "Time in trial (s)")
        p_pokes.setLabel("bottom", "Trial")
        p_pokes.enableAutoRange(axis="y")

        poke_line_item = pg.PlotDataItem(pen=pg.mkPen("#3a3a3a", width=1))
        p_pokes.addItem(poke_line_item)
        poke_line_xs: list = []
        poke_line_ys: list = []

        port_scatter: dict[int, pg.ScatterPlotItem] = {}
        port_pts_x: dict[int, list] = {}
        port_pts_y: dict[int, list] = {}
        for port in range(1, 9):
            color = seq_color.get(port, neutral_color)
            sc = pg.ScatterPlotItem(
                pen=None, symbol="o", size=8, brush=pg.mkBrush(_qc(color))
            )
            p_pokes.addItem(sc)
            port_scatter[port] = sc
            port_pts_x[port] = []
            port_pts_y[port] = []

        leg_pokes = p_pokes.addLegend(offset=(5, 5))
        for port in self.sequence:
            color = seq_color.get(port, neutral_color)
            dummy = pg.ScatterPlotItem(
                pen=None, symbol="o", size=8, brush=pg.mkBrush(_qc(color))
            )
            leg_pokes.addItem(dummy, f"Port {port}")

        # ── [0,1] IPI distributions per sequence step ─────────────────────
        p_ipi = win.addPlot(
            row=0, col=1, title="Inter-poke intervals per step (normalised)"
        )
        p_ipi.setLabel("left", "Fraction")
        p_ipi.setLabel("bottom", "Time (s)")

        trans_pairs = (
            [
                (self.sequence[i], self.sequence[i + 1])
                for i in range(len(self.sequence) - 1)
            ]
            if len(self.sequence) > 1
            else []
        )

        trans_data: dict[tuple, list] = {pair: [] for pair in trans_pairs}
        trans_items: dict[tuple, pg.PlotDataItem] = {}
        leg_ipi = p_ipi.addLegend(offset=(5, 5))
        for fp, tp in trans_pairs:
            color = seq_color.get(tp, neutral_color)  # destination-port color
            item = pg.PlotDataItem(stepMode="right", pen=pg.mkPen(color, width=2))
            p_ipi.addItem(item)
            trans_items[(fp, tp)] = item
            leg_ipi.addItem(item, f"{fp}→{tp}")

        # ── [1,1] Cumulative water ─────────────────────────────────────────
        p_water = win.addPlot(row=1, col=1, title="Cumulative water delivered")
        p_water.setLabel("left", "Water (µL)")
        p_water.setLabel("bottom", "Session time (min)")
        curve_water = pg.PlotDataItem(pen=pg.mkPen(neutral_color, width=2))
        p_water.addItem(curve_water)
        water_ts: list = [0.0]
        water_ul: list = [0.0]

        # ── [2,1] Sequence duration on correct trials ──────────────────────
        p_dur = win.addPlot(row=2, col=1, title="Sequence duration (correct trials)")
        p_dur.setLabel("left", "Duration (s)")
        p_dur.setLabel("bottom", "Trial")
        p_dur.enableAutoRange(axis="y")

        dur_scatter = pg.ScatterPlotItem(
            pen=None, symbol="o", size=6, brush=pg.mkBrush(_qc(neutral_color))
        )
        p_dur.addItem(dur_scatter)
        dur_mean_curve = pg.PlotDataItem(pen=pg.mkPen("w", width=2))
        p_dur.addItem(dur_mean_curve)
        dur_xs: list = []
        dur_ys: list = []

        # Link left-column x-axes and right-column [2,1] to trial number
        p_level.setXLink(p_out)
        p_pokes.setXLink(p_out)
        p_dur.setXLink(p_out)

        # ─────────────────────────────────────────────────────────────────
        # Update callback
        # ─────────────────────────────────────────────────────────────────

        def _update(d: dict):
            idx = d["trial_index"]
            if idx >= n:
                return

            is_correct = d["outcome"] == "correct"
            perf_arr[idx] = d["perf_buffer_mean"]
            levels_arr[idx] = d["level"]

            # Outcome scatter
            if is_correct:
                correct_xs.append(idx)
                correct_ys.append(1.0)
                scatter_correct.setData(x=np.array(correct_xs), y=np.array(correct_ys))
            else:
                incorrect_xs.append(idx)
                incorrect_ys.append(0.0)
                scatter_incorrect.setData(
                    x=np.array(incorrect_xs), y=np.array(incorrect_ys)
                )

            # Rolling perf line
            valid = ~np.isnan(perf_arr)
            if valid.any():
                xs = np.where(valid)[0]
                curve_perf.setData(xs, perf_arr[valid])

            # Level line + change markers
            valid_l = ~np.isnan(levels_arr)
            if valid_l.any():
                xs_l = np.where(valid_l)[0]
                curve_level.setData(xs_l, levels_arr[valid_l])

            lat = d.get("level_at_trial", d["level"])
            if d["level"] != lat:
                if d["level"] > lat:
                    lvl_up_x.append(idx)
                    lvl_up_y.append(d["level"])
                    lvl_up_sc.setData(x=np.array(lvl_up_x), y=np.array(lvl_up_y))
                else:
                    lvl_dn_x.append(idx)
                    lvl_dn_y.append(d["level"])
                    lvl_dn_sc.setData(x=np.array(lvl_dn_x), y=np.array(lvl_dn_y))

            # IPI histograms
            for td in d.get("transition_times", []):
                pair = (td["from"], td["to"])
                if pair in trans_data:
                    trans_data[pair].append(td["dt"])

            for pair, item in trans_items.items():
                times_list = trans_data[pair]
                if len(times_list) >= 3:
                    counts, bins = np.histogram(times_list, bins=20)
                    mx = counts.max()
                    item.setData(bins, counts / mx if mx > 0 else counts.astype(float))

            # Cumulative water
            t_min = d.get("trial_time_s", 0) / 60.0
            water_ts.append(t_min)
            water_ul.append(d.get("water_ul_cumulative", 0.0))
            curve_water.setData(x=np.array(water_ts), y=np.array(water_ul))

            # Poke sequence raster
            poke_evts = d.get("poke_events", [])
            if poke_evts:
                ts_in_trial = [p["time"] for p in poke_evts]
                poke_line_xs.extend([idx, idx, float("nan")])
                poke_line_ys.extend([min(ts_in_trial), max(ts_in_trial), float("nan")])
                poke_line_item.setData(
                    x=np.array(poke_line_xs), y=np.array(poke_line_ys)
                )
                for pe in poke_evts:
                    port_pts_x[pe["port"]].append(idx)
                    port_pts_y[pe["port"]].append(pe["time"])
                for port, sc in port_scatter.items():
                    if port_pts_x[port]:
                        sc.setData(
                            x=np.array(port_pts_x[port]),
                            y=np.array(port_pts_y[port]),
                        )

            # Sequence duration (correct trials only)
            seq_dur = d.get("sequence_duration_s")
            if seq_dur is not None:
                dur_xs.append(idx)
                dur_ys.append(seq_dur)
                dur_scatter.setData(x=np.array(dur_xs), y=np.array(dur_ys))
                # Rolling mean over last 10 correct trials
                if len(dur_ys) >= 2:
                    window = min(10, len(dur_ys))
                    means_x = dur_xs[window - 1 :]
                    means_y = [
                        float(np.mean(dur_ys[max(0, i - window + 1) : i + 1]))
                        for i in range(window - 1, len(dur_ys))
                    ]
                    dur_mean_curve.setData(x=np.array(means_x), y=np.array(means_y))

        monitor = _QueueMonitor(data_queue=self.data_queue, kill_queue=self.kill_queue)
        monitor.update_signal.connect(_update)
        monitor.exit_signal.connect(lambda _: app.quit())
        monitor.start()

        app.exec()
