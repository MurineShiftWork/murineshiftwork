from __future__ import annotations

import time
from multiprocessing import Process, Queue

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

_FALLBACK_COLORS = ["#34475C", "#4BA5BF", "#90C681", "#FFD062", "#ED6F5D", "#ABBAB3"]
_EXTRA_COLORS = [
    "#7A8A9A",
    "#AA9988",
    "#88AA99",
    "#AA8899",
    "#9988AA",
]  # non-sequence ports
_GRID_ALPHA = 0.25
_STOP_COLOR = "#E05555"  # red for soft-stop criterion lines
_PERF_PERFECT_COLOR = (
    "#FFD062"  # yellow — distinct from white perf line and blue reward line
)


def _nan_vec(length: int) -> np.ndarray:
    return np.full(length, np.nan)


def _seq_color_map(sequence: list, colors: list) -> dict[int, str]:
    result = {}
    for i, port in enumerate(sequence):
        result[port] = (
            colors[i] if i < len(colors) else (colors[-1] if colors else "#ffffff")
        )
    return result


def _port_style_map(
    sequence: list, colors: list, n_ports: int = 8
) -> dict[int, tuple[str, bool]]:
    """Map each port 1..n_ports to (color, filled).

    Sequence ports get the sequence palette (filled dots).
    Other ports get _EXTRA_COLORS (open circles).
    """
    seq_map = _seq_color_map(sequence, colors)
    extra = iter(_EXTRA_COLORS)
    result: dict[int, tuple[str, bool]] = {}
    for port in range(1, n_ports + 1):
        if port in seq_map:
            result[port] = (seq_map[port], True)
        else:
            result[port] = (next(extra, "#888888"), False)
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


class OnlinePlottingForSeq(Process):
    """Live plot for the Sequence Automated task.

    Col 0 — progression (trial x)     Col 1 — sub-layout (independent axes)
    ┌─────────────────────────────┬──────────────────────────────────┐
    │ [0,0] Outcomes + rolling    │ Poke-sequence raster (log y)     │
    │        performance          │   filled = seq port; open = other│
    ├─────────────────────────────┤──────────────────────────────────┤
    │ [1,0] Training level +      │ Marginal histogram (0–5 s)       │
    │        change markers       │   all pokes, all trials          │
    ├─────────────────────────────┤──────────────────────────────────┤
    │ [2,0] Session progress      │ Poke swarm (port × time, 0–5 s)  │
    │       liquid µL (L) +        │   filled = seq port; open = other│
    │       trial count (R)       │──────────────────────────────────│
    │       vs session time (min) │ Sequence duration (correct)      │
    └─────────────────────────────┴──────────────────────────────────┘

    task.yaml settings:
      online_plot_poke_ymax_s: null | float   (clip poke raster y-axis)

    Stop-criteria (red dashed lines + one-time console warning each):
      stop_reward_ul   — horizontal line on reward axis; label shows exact µL value
      stop_trials      — vertical line on all trial-linked plots + horizontal on trial count
      stop_time_min    — vertical line on session-progress time axis
      stop_level_delta — horizontal line on level plot at start_level + delta
    """

    daemon = True

    def __init__(
        self,
        session_name: str = "unnamed",
        subject: str = "",
        setup: str = "",
        data_queue: Queue | None = None,
        kill_queue: Queue | None = None,
        n_max_trials: int = 1500,
        n_levels: int = 50,
        progression_threshold: float = 0.9,
        regression_threshold: float = 0.2,
        sequence: list | None = None,
        port_colors: list | None = None,
        poke_ymax_s: float | None = None,
        poke_xmax_s: float = 6.0,
        xlim_trials: int = 100,
        poke_log_scale: bool = True,
        first_poke_offset_s: float = 0.5,
        stop_reward_ul: float = 1000.0,
        stop_trials: int = 500,
        stop_time_min: float = 60.0,
        stop_level_delta: int = 15,
        start_level: int = 1,
    ):
        super().__init__()
        self.session_name = session_name
        self.subject = subject
        self.setup = setup
        self.data_queue = data_queue
        self.kill_queue = kill_queue
        self.n_max_trials = n_max_trials
        self.n_levels = n_levels
        self.progression_threshold = progression_threshold
        self.regression_threshold = regression_threshold
        self.sequence = sequence or []
        _c = list(port_colors) if port_colors else []
        self.colors = _c if _c else _FALLBACK_COLORS
        self.poke_ymax_s = poke_ymax_s
        self.poke_xmax_s = poke_xmax_s
        self.xlim_trials = xlim_trials
        self.poke_log_scale = poke_log_scale
        self.first_poke_offset_s = first_poke_offset_s
        self.stop_reward_ul = stop_reward_ul
        self.stop_trials = stop_trials
        self.stop_time_min = stop_time_min
        self.stop_level_delta = stop_level_delta
        self.start_level = start_level
        self._stop_level = start_level + stop_level_delta

    def run(self) -> None:
        pg.setConfigOptions(antialias=True)
        _setup_str = f"[{self.setup}] " if self.setup else ""
        _title = f"{_setup_str}{self.subject} @ sequence"
        app = pg.mkQApp(_title)
        win = pg.GraphicsLayoutWidget(show=True, title=_title)
        win.resize(1600, 960)
        win.ci.layout.setContentsMargins(8, 8, 8, 8)

        n = self.n_max_trials
        perf_arr = _nan_vec(n)
        perf_perfect_arr = _nan_vec(n)
        levels_arr = _nan_vec(n)

        seq_color = _seq_color_map(self.sequence, self.colors)
        neutral_color = self.colors[-1] if self.colors else "#ABBAB3"

        def _qc(h: str) -> QtGui.QColor:
            return QtGui.QColor(h)

        _stop_pen = pg.mkPen(_STOP_COLOR, width=1.5, style=QtCore.Qt.PenStyle.DashLine)
        _stop_lo = {"color": _STOP_COLOR, "anchor": (1, 1), "movable": False}

        # ── [0,0] Outcomes + rolling performance ──────────────────────────
        p_out = win.addPlot(row=0, col=0, title="Outcomes & rolling performance")
        p_out.setYRange(-0.15, 1.15)
        p_out.setLabel("left", "Correct")
        p_out.addLine(
            y=self.progression_threshold,
            pen=pg.mkPen(neutral_color, width=1, style=QtCore.Qt.PenStyle.DashLine),
        )
        p_out.addLine(
            y=self.regression_threshold,
            pen=pg.mkPen("#ED6F5D", width=1, style=QtCore.Qt.PenStyle.DashLine),
        )
        curve_perf = pg.PlotDataItem(pen=pg.mkPen("w", width=2))
        curve_perf_perfect = pg.PlotDataItem(
            pen=pg.mkPen(
                _PERF_PERFECT_COLOR, width=1.5, style=QtCore.Qt.PenStyle.DashLine
            )
        )
        scatter_correct = pg.ScatterPlotItem(
            pen=None, symbol="o", size=5, brush=pg.mkBrush(144, 198, 129, 160)
        )
        scatter_incorrect = pg.ScatterPlotItem(
            pen=None, symbol="o", size=5, brush=pg.mkBrush(237, 111, 93, 160)
        )
        scatter_no_resp = pg.ScatterPlotItem(
            pen=pg.mkPen("#888888", width=1.5),
            symbol="x",
            size=5,
            brush=pg.mkBrush(0, 0, 0, 0),
        )
        p_out.addItem(curve_perf)
        p_out.addItem(curve_perf_perfect)
        p_out.addItem(scatter_correct)
        p_out.addItem(scatter_incorrect)
        p_out.addItem(scatter_no_resp)
        leg_out = p_out.addLegend(offset=(-5, 5))
        leg_out.addItem(curve_perf, "Perf (ordered)")
        leg_out.addItem(curve_perf_perfect, "Perf (perfect)")
        leg_out.addItem(scatter_no_resp, "No response")
        correct_xs: list = []
        correct_ys: list = []
        incorrect_xs: list = []
        incorrect_ys: list = []
        no_resp_xs: list = []
        no_resp_ys: list = []

        # ── [1,0] Training level + change markers ─────────────────────────
        p_level = win.addPlot(row=1, col=0, title="Training level")
        p_level.setYRange(0, self.n_levels + 1)
        p_level.setLabel("left", "Level")
        curve_level = pg.PlotDataItem(pen=pg.mkPen(neutral_color, width=2))
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
        p_level.addItem(curve_level)
        p_level.addItem(lvl_up_sc)
        p_level.addItem(lvl_dn_sc)
        lvl_up_x: list = []
        lvl_up_y: list = []
        lvl_dn_x: list = []
        lvl_dn_y: list = []

        # ── [2,0] Session progress: reward (left, blue) + trial count (right) ─
        # x-axis = session time in minutes (independent of trial-linked axis)
        _reward_color = "#4BA5BF"
        p_session = win.addPlot(row=2, col=0, title="Session progress")
        p_session.setLabel("left", "Reward (µL)", color=_reward_color)
        p_session.setLabel("bottom", "Session time (min)")
        p_session.showAxis("right")
        p_session.getAxis("right").setLabel("Trials")

        curve_liquid = pg.PlotDataItem(
            pen=pg.mkPen(_reward_color, width=2, style=QtCore.Qt.PenStyle.DashLine)
        )
        p_session.addItem(curve_liquid)

        vb_trials = pg.ViewBox()
        p_session.scene().addItem(vb_trials)
        p_session.getAxis("right").linkToView(vb_trials)
        vb_trials.setXLink(p_session)

        curve_trial_count = pg.PlotDataItem(pen=pg.mkPen("w", width=1.5))
        vb_trials.addItem(curve_trial_count)

        def _sync_vb() -> None:
            vb_trials.setGeometry(p_session.vb.sceneBoundingRect())
            vb_trials.linkedViewChanged(p_session.vb, vb_trials.XAxis)

        p_session.vb.sigResized.connect(_sync_vb)
        _sync_vb()

        session_ts: list = [0.0]
        session_liquid_ul: list = [0.0]
        session_trial_n: list = [0]

        # ── Col 1: sub-layout spanning all main rows ───────────────────────
        _col1 = win.addLayout(row=0, col=1, rowspan=3)
        _col1.layout.setContentsMargins(0, 0, 0, 0)
        _col1.layout.setRowStretchFactor(0, 3)  # poke raster  (tallest)
        _col1.layout.setRowStretchFactor(1, 1)  # marginal     (small strip)
        _col1.layout.setRowStretchFactor(2, 2)  # swarm
        _col1.layout.setRowStretchFactor(3, 2)  # duration

        # ── Poke-sequence raster ──────────────────────────────────────────
        _poke_y_label = (
            "Time in trial (s, log)" if self.poke_log_scale else "Time in trial (s)"
        )
        p_pokes = _col1.addPlot(row=0, col=0, title="Poke sequence (time in trial)")
        p_pokes.showGrid(x=True, y=True, alpha=_GRID_ALPHA)
        p_pokes.setLabel("left", _poke_y_label)
        p_pokes.setLabel("bottom", "Trial")
        if self.poke_log_scale:
            p_pokes.setLogMode(x=False, y=True)
        p_pokes.enableAutoRange(axis="y")

        poke_line_item = pg.PlotDataItem(pen=pg.mkPen("#3a3a3a", width=1))
        p_pokes.addItem(poke_line_item)
        poke_line_xs: list = []
        poke_line_ys: list = []

        port_style = _port_style_map(self.sequence, self.colors)
        port_scatter: dict[int, pg.PlotDataItem] = {}
        port_pts_x: dict[int, list] = {}
        port_pts_y: dict[int, list] = {}
        for port in range(1, 9):
            _color, _filled = port_style[port]
            if _filled:
                _pitem = pg.PlotDataItem(
                    pen=None,
                    symbol="o",
                    symbolSize=8,
                    symbolBrush=pg.mkBrush(_qc(_color)),
                    symbolPen=None,
                )
            else:
                _pitem = pg.PlotDataItem(
                    pen=None,
                    symbol="o",
                    symbolSize=8,
                    symbolBrush=pg.mkBrush(0, 0, 0, 0),
                    symbolPen=pg.mkPen(_qc(_color), width=1.5),
                )
            p_pokes.addItem(_pitem)
            port_scatter[port] = _pitem
            port_pts_x[port] = []
            port_pts_y[port] = []

        leg_pokes = p_pokes.addLegend(offset=(5, 5))
        for port in self.sequence:
            _color, _ = port_style[port]
            leg_pokes.addItem(
                pg.ScatterPlotItem(
                    pen=None, symbol="o", size=8, brush=pg.mkBrush(_qc(_color))
                ),
                f"Port {port}",
            )

        # Sequence ports in order (unique, order-preserving) for swarm/marginal
        _seq_ports = list(dict.fromkeys(self.sequence))
        _port_to_row: dict[int, int] = {p: i for i, p in enumerate(_seq_ports)}
        _n_seq = len(_seq_ports)
        _OTHER_ROW = _n_seq  # extra row below sequence ports for non-sequence pokes

        # ── Marginal: per-sequence-port + "other" poke-time distribution ─
        p_marginal = _col1.addPlot(row=1, col=0, title="Poke times")
        p_marginal.setLabel("left", "n")
        p_marginal.setXRange(0, self.poke_xmax_s, padding=0)
        p_marginal.hideAxis("bottom")

        marginal_curves: dict[int, pg.PlotCurveItem] = {}
        port_poke_times: dict[int, list] = {p: [] for p in _seq_ports}
        for _sp in _seq_ports:
            _sc_color = seq_color.get(_sp, neutral_color)
            _fill_c = QtGui.QColor(_sc_color)
            _fill_c.setAlpha(80)
            _mc = pg.PlotCurveItem(
                pen=pg.mkPen(_sc_color, width=1.5),
                fillLevel=0,
                brush=pg.mkBrush(_fill_c),
            )
            p_marginal.addItem(_mc)
            marginal_curves[_sp] = _mc

        _other_fill_c = QtGui.QColor(neutral_color)
        _other_fill_c.setAlpha(50)
        marginal_curve_other = pg.PlotCurveItem(
            pen=pg.mkPen(neutral_color, width=1.0, style=QtCore.Qt.PenStyle.DotLine),
            fillLevel=0,
            brush=pg.mkBrush(_other_fill_c),
        )
        p_marginal.addItem(marginal_curve_other)
        poke_times_other: list[float] = []

        # ── Poke swarm: sequence ports + "other" row ──────────────────────
        p_swarm = _col1.addPlot(row=2, col=0)
        p_swarm.setLabel("bottom", "Time from first poke (s)")
        p_swarm.setLabel("left", "Port")
        p_swarm.setXRange(0, self.poke_xmax_s, padding=0)
        p_swarm.setYRange(-0.5, _n_seq + 0.5, padding=0)
        _swarm_ticks = [(i, f"P{p}") for i, p in enumerate(_seq_ports)] + [
            (_OTHER_ROW, "other")
        ]
        p_swarm.getAxis("left").setTicks([_swarm_ticks])
        _sep_pen = pg.mkPen("#2e2e2e", width=0.5)
        for _i in range(_n_seq):  # separators including one above "other" row
            p_swarm.addLine(y=_i + 0.5, pen=_sep_pen)
        p_marginal.setXLink(p_swarm)

        swarm_pts_x: dict[int, list] = {p: [] for p in _seq_ports}
        swarm_pts_y: dict[int, list] = {p: [] for p in _seq_ports}
        swarm_items: dict[int, pg.PlotDataItem] = {}
        for _sp in _seq_ports:
            _sc_color = seq_color.get(_sp, neutral_color)
            _si = pg.PlotDataItem(
                pen=None,
                symbol="o",
                symbolSize=5,
                symbolBrush=pg.mkBrush(_qc(_sc_color)),
                symbolPen=None,
            )
            p_swarm.addItem(_si)
            swarm_items[_sp] = _si

        swarm_pts_x_other: list[float] = []
        swarm_pts_y_other: list[float] = []
        si_other = pg.PlotDataItem(
            pen=None,
            symbol="o",
            symbolSize=5,
            symbolBrush=pg.mkBrush(0, 0, 0, 0),
            symbolPen=pg.mkPen(_qc(neutral_color), width=1.0),
        )
        p_swarm.addItem(si_other)

        # ── Sequence duration (correct trials) ────────────────────────────
        p_dur = _col1.addPlot(row=3, col=0, title="Sequence duration (correct trials)")
        p_dur.setLabel("left", "Duration (s)")
        p_dur.setLabel("bottom", "Trial")
        p_dur.enableAutoRange(axis="y")
        dur_scatter = pg.ScatterPlotItem(
            pen=None, symbol="o", size=6, brush=pg.mkBrush(_qc(neutral_color))
        )
        dur_mean_curve = pg.PlotDataItem(pen=pg.mkPen("w", width=2))
        p_dur.addItem(dur_scatter)
        p_dur.addItem(dur_mean_curve)
        dur_xs: list = []
        dur_ys: list = []

        # Link trial-based x-axes; session / swarm / marginal use independent x
        p_level.setXLink(p_out)
        p_pokes.setXLink(p_out)
        p_dur.setXLink(p_out)

        # ── Soft-stop criterion lines (red dashed) ────────────────────────
        if self.stop_reward_ul > 0:
            p_session.addItem(
                pg.InfiniteLine(
                    pos=self.stop_reward_ul,
                    angle=0,
                    pen=_stop_pen,
                    label=f"{self.stop_reward_ul:.0f} µL",
                    labelOpts=_stop_lo,
                ),
                ignoreBounds=True,
            )
        if self.stop_time_min > 0:
            p_session.addItem(
                pg.InfiniteLine(
                    pos=self.stop_time_min,
                    angle=90,
                    pen=_stop_pen,
                    label=f"{self.stop_time_min:.0f} min",
                    labelOpts=_stop_lo,
                ),
                ignoreBounds=True,
            )
        if self.stop_trials > 0:
            vb_trials.addItem(
                pg.InfiniteLine(
                    pos=self.stop_trials,
                    angle=0,
                    pen=_stop_pen,
                    label=f"{self.stop_trials} trials",
                    labelOpts=_stop_lo,
                ),
                ignoreBounds=True,
            )
            for _sp in (p_out, p_level, p_pokes, p_dur):
                _sp.addItem(
                    pg.InfiniteLine(pos=self.stop_trials, angle=90, pen=_stop_pen),
                    ignoreBounds=True,
                )
        if 0 < self._stop_level <= self.n_levels:
            p_level.addItem(
                pg.InfiniteLine(
                    pos=self._stop_level,
                    angle=0,
                    pen=_stop_pen,
                    label=f"+{self.stop_level_delta} lvls",
                    labelOpts=_stop_lo,
                ),
                ignoreBounds=True,
            )

        # Fixed left-axis width so all panels align regardless of tick-label length
        _AX_W = 60
        _RIGHT_W = 50
        for _p in (p_out, p_level, p_session, p_pokes, p_marginal, p_swarm, p_dur):
            _p.getAxis("left").setWidth(_AX_W)
        # Show a fixed-width right axis on all col-0 panels so their plot areas match.
        # p_out / p_level get a bare spine (no ticks/label); p_session keeps its "Trials" label.
        for _p in (p_out, p_level):
            _p.showAxis("right")
            _p.getAxis("right").setWidth(_RIGHT_W)
            _p.getAxis("right").setStyle(showValues=False)
        p_session.getAxis("right").setWidth(_RIGHT_W)

        # ─────────────────────────────────────────────────────────────────
        # Update callback
        # ─────────────────────────────────────────────────────────────────
        def _update(d: dict) -> None:
            idx = d["trial_index"]
            if idx >= n:
                return

            outcome = d["outcome"]
            is_no_resp = outcome == "no_response"
            is_correct = outcome == "correct"
            levels_arr[idx] = d["level"]

            # ── Outcomes + perf (skip for no_response) ────────────────────
            # Insert NaN at level-change trials so the rolling-average curve
            # is visually partitioned into per-level epochs.
            level_changed = d["level"] != d.get("level_at_trial", d["level"])
            if is_no_resp:
                no_resp_xs.append(idx)
                no_resp_ys.append(0.5)
                scatter_no_resp.setData(x=np.array(no_resp_xs), y=np.array(no_resp_ys))
            else:
                perf_arr[idx] = np.nan if level_changed else d["perf_buffer_mean"]
                perf_perfect_arr[idx] = (
                    np.nan if level_changed else d.get("perf_perfect_mean", np.nan)
                )
                if is_correct:
                    correct_xs.append(idx)
                    correct_ys.append(1.1)
                    scatter_correct.setData(
                        x=np.array(correct_xs), y=np.array(correct_ys)
                    )
                else:
                    incorrect_xs.append(idx)
                    incorrect_ys.append(-0.1)
                    scatter_incorrect.setData(
                        x=np.array(incorrect_xs), y=np.array(incorrect_ys)
                    )
                valid = ~np.isnan(perf_arr)
                if valid.any():
                    curve_perf.setData(np.where(valid)[0], perf_arr[valid])
                valid_p = ~np.isnan(perf_perfect_arr)
                if valid_p.any():
                    curve_perf_perfect.setData(
                        np.where(valid_p)[0], perf_perfect_arr[valid_p]
                    )

            # ── Level ─────────────────────────────────────────────────────
            valid_l = ~np.isnan(levels_arr)
            if valid_l.any():
                curve_level.setData(np.where(valid_l)[0], levels_arr[valid_l])
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

            # ── Session progress (water + trial count vs time) ────────────
            t_min = d.get("trial_time_s", 0) / 60.0
            session_ts.append(t_min)
            session_liquid_ul.append(d.get("liquid_ul_cumulative", 0.0))
            session_trial_n.append(idx + 1)
            ts_arr = np.array(session_ts)
            curve_liquid.setData(x=ts_arr, y=np.array(session_liquid_ul))
            curve_trial_count.setData(x=ts_arr, y=np.array(session_trial_n))
            _sync_vb()

            # ── Poke raster + swarm + marginal ───────────────────────────
            poke_evts = d.get("poke_events", [])
            if poke_evts:
                first_t = poke_evts[0][
                    "time"
                ]  # trial-relative origin for normalisation
                ymax = self.poke_ymax_s
                _fp_off = self.first_poke_offset_s

                # Raster: first poke at fixed anchor, rest at anchor + IPI offset
                ts_plot = []
                for _i, p in enumerate(poke_evts):
                    if _i == 0:
                        t = _fp_off if _fp_off > 0 else max(p["time"], 1e-3)
                    else:
                        t = _fp_off + (p["time"] - first_t)
                    ts_plot.append(min(t, ymax if ymax is not None else float("inf")))
                poke_line_xs.extend([idx, idx, float("nan")])
                poke_line_ys.extend([min(ts_plot), max(ts_plot), float("nan")])
                poke_line_item.setData(
                    x=np.array(poke_line_xs), y=np.array(poke_line_ys)
                )
                for pe, t_p in zip(poke_evts, ts_plot):
                    port_pts_x[pe["port"]].append(idx)
                    port_pts_y[pe["port"]].append(t_p)
                for port, sc in port_scatter.items():
                    if port_pts_x[port]:
                        sc.setData(
                            x=np.array(port_pts_x[port]),
                            y=np.array(port_pts_y[port]),
                        )

                # Swarm + marginal: time from first poke (internal structure, not latency)
                for pe in poke_evts:
                    _port = pe["port"]
                    _t_sw = min(pe["time"] - first_t, self.poke_xmax_s)
                    if _port in _port_to_row:
                        swarm_pts_x[_port].append(_t_sw)
                        swarm_pts_y[_port].append(
                            _port_to_row[_port] + np.random.uniform(-0.3, 0.3)
                        )
                        port_poke_times[_port].append(_t_sw)
                    else:
                        swarm_pts_x_other.append(_t_sw)
                        swarm_pts_y_other.append(
                            _OTHER_ROW + np.random.uniform(-0.3, 0.3)
                        )
                        poke_times_other.append(_t_sw)
            for _port, _si in swarm_items.items():
                if swarm_pts_x[_port]:
                    _si.setData(
                        x=np.array(swarm_pts_x[_port]),
                        y=np.array(swarm_pts_y[_port]),
                    )
            if swarm_pts_x_other:
                si_other.setData(
                    x=np.array(swarm_pts_x_other), y=np.array(swarm_pts_y_other)
                )
            for _port, _mc in marginal_curves.items():
                if port_poke_times[_port]:
                    _counts, _edges = np.histogram(
                        port_poke_times[_port], bins=50, range=(0.0, self.poke_xmax_s)
                    )
                    _mc.setData(
                        x=(_edges[:-1] + _edges[1:]) / 2,
                        y=_counts.astype(float),
                    )
            if poke_times_other:
                _counts, _edges = np.histogram(
                    poke_times_other, bins=50, range=(0.0, self.poke_xmax_s)
                )
                marginal_curve_other.setData(
                    x=(_edges[:-1] + _edges[1:]) / 2,
                    y=_counts.astype(float),
                )

            # ── Sliding x-axis window (trial-based panels) ───────────────
            if self.xlim_trials > 0:
                _xmin = max(0, idx - self.xlim_trials + 1)
                _xmax = _xmin + self.xlim_trials
                p_out.setXRange(_xmin, _xmax, padding=0)

            # ── Sequence duration ─────────────────────────────────────────
            seq_dur = d.get("sequence_duration_s")
            if seq_dur is not None:
                dur_xs.append(idx)
                dur_ys.append(seq_dur)
                dur_scatter.setData(x=np.array(dur_xs), y=np.array(dur_ys))
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
