import time
from multiprocessing import Process, Queue

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui


def _nan_vec(length):
    return np.full(length, np.nan)


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
    """Three-panel live plot for the Sequence Automated task.

    Top:    Correct (1) / incorrect (0) scatter per trial.
    Middle: Rolling performance fraction with threshold lines.
    Bottom: Training level over trials.
    """

    daemon = True

    def __init__(
        self,
        session_name: str = "unnamed",
        data_queue: Queue = None,
        kill_queue: Queue = None,
        n_max_trials: int = 1500,
        n_levels: int = 50,
        progression_threshold: float = 0.9,
        progression_threshold_advanced: float = 0.8,
        regression_threshold: float = 0.2,
    ):
        super().__init__()
        self.session_name = session_name
        self.data_queue = data_queue
        self.kill_queue = kill_queue
        self.n_max_trials = n_max_trials
        self.n_levels = n_levels
        self.progression_threshold = progression_threshold
        self.progression_threshold_advanced = progression_threshold_advanced
        self.regression_threshold = regression_threshold

    def run(self):
        app = pg.mkQApp("Sequence Automated")

        win = pg.GraphicsLayoutWidget(show=True, title=f"SA | {self.session_name}")
        win.resize(900, 700)

        n = self.n_max_trials
        outcomes = _nan_vec(n)
        perf = _nan_vec(n)
        levels = _nan_vec(n)

        # --- Top: outcome raster ---
        p_out = win.addPlot(title="Trial outcomes (1=correct, 0=incorrect)")
        p_out.setYRange(-0.1, 1.1)
        p_out.setLabel("left", "Outcome")
        scatter_correct = pg.ScatterPlotItem(
            pen=None, symbol="o", size=6, brush=pg.mkBrush(40, 180, 99)
        )
        scatter_incorrect = pg.ScatterPlotItem(
            pen=None, symbol="o", size=6, brush=pg.mkBrush(231, 76, 60)
        )
        p_out.addItem(scatter_correct)
        p_out.addItem(scatter_incorrect)

        win.nextRow()

        # --- Middle: rolling performance ---
        p_perf = win.addPlot(title="Rolling performance")
        p_perf.setYRange(-0.05, 1.05)
        p_perf.setLabel("left", "Fraction correct")
        p_perf.addLine(
            y=self.progression_threshold,
            pen=pg.mkPen("g", width=1, style=QtCore.Qt.DashLine),
        )
        p_perf.addLine(
            y=self.progression_threshold_advanced,
            pen=pg.mkPen("y", width=1, style=QtCore.Qt.DashLine),
        )
        p_perf.addLine(
            y=self.regression_threshold,
            pen=pg.mkPen("r", width=1, style=QtCore.Qt.DashLine),
        )
        curve_perf = pg.PlotDataItem(pen=pg.mkPen("w", width=2))
        p_perf.addItem(curve_perf)

        win.nextRow()

        # --- Bottom: training level ---
        p_level = win.addPlot(title="Training level")
        p_level.setYRange(0, self.n_levels + 1)
        p_level.setLabel("left", "Level")
        p_level.setLabel("bottom", "Trial")
        curve_level = pg.PlotDataItem(pen=pg.mkPen("c", width=2))
        p_level.addItem(curve_level)

        # Link x-axes
        p_perf.setXLink(p_out)
        p_level.setXLink(p_out)

        correct_pts: list = []
        incorrect_pts: list = []

        def _update(d: dict):
            idx = d["trial_index"]
            if idx >= n:
                return
            is_correct = d["outcome"] == "correct"
            outcomes[idx] = 1.0 if is_correct else 0.0
            perf[idx] = d["perf_buffer_mean"]
            levels[idx] = d["level"]

            color_c = QtGui.QColor(40, 180, 99)
            color_i = QtGui.QColor(231, 76, 60)
            pt = {
                "pos": (idx, outcomes[idx]),
                "size": 6,
                "pen": {
                    "color": color_c if is_correct else color_i,
                    "width": 1,
                },
                "brush": QtGui.QBrush(color_c if is_correct else color_i),
            }
            if is_correct:
                correct_pts.append(pt)
                scatter_correct.setData(correct_pts)
            else:
                incorrect_pts.append(pt)
                scatter_incorrect.setData(incorrect_pts)

            valid = ~np.isnan(perf)
            if valid.any():
                xs = np.where(valid)[0]
                curve_perf.setData(xs, perf[valid])

            valid_l = ~np.isnan(levels)
            if valid_l.any():
                xs_l = np.where(valid_l)[0]
                curve_level.setData(xs_l, levels[valid_l])

        monitor = _QueueMonitor(data_queue=self.data_queue, kill_queue=self.kill_queue)
        monitor.update_signal.connect(_update)
        monitor.exit_signal.connect(lambda _: app.quit())
        monitor.start()

        app.exec_()
