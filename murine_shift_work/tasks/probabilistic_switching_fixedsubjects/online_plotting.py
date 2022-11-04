import time
from multiprocessing import Process
from multiprocessing import Queue
from pathlib import Path
from sys import exit

import cv2 as cv
import myterial as mt
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from pyqtgraph.Qt import QtGui

color_rewarded = mt.blue_dark
color_unrewarded = mt.grey
color_punished = mt.red_dark
color_stop = mt.red_light

trial_outcomes = {
    0: {"name": "left-rew", "y": -1, "color": color_rewarded},
    1: {"name": "left-unr", "y": -1, "color": color_unrewarded},
    2: {"name": "right-rew", "y": 1, "color": color_rewarded},
    3: {"name": "right-unr", "y": 1, "color": color_unrewarded},
    4: {"name": "left-pun", "y": -1, "color": color_punished},
    5: {"name": "right-pun", "y": 1, "color": color_punished},
    6: {"name": "left-stop", "y": -1, "color": color_stop},
    7: {"name": "right-stop", "y": 1, "color": color_stop},
}


# SIMULATION TOOLS
def draw_simulation_case():
    return trial_outcomes[np.random.randint(0, 4)]


def make_new_point(x=None, y=None, color=None):
    color = QtGui.QColor(color)
    return {
        "pos": (x, y),
        "size": 10,
        "pen": {"color": color, "width": 2},
        "brush": QtGui.QBrush(color),
    }


def draw_random_number(min=-1.0, max=1.0):
    return min + np.random.random() * np.sum(np.abs([min, max]))


# MAIN FUNCTIONS


def nan_vector(length=None):
    return np.full(shape=(length,), fill_value=np.nan)


class QueueMonitor(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(dict)
    exit_signal = QtCore.pyqtSignal(bool)
    monitoring_queue = None
    kill_queue = None

    def __init__(self, monitoring_queue=None, kill_queue=None):
        super(QueueMonitor, self).__init__()
        self.monitoring_queue = monitoring_queue
        self.kill_queue = kill_queue

    def run(self) -> None:

        while True:
            time.sleep(0.1)
            if not self.kill_queue.empty():
                self.exit_signal.emit(True)
                break
            else:
                if not self.monitoring_queue.empty():
                    self.update_signal.emit(self.monitoring_queue.get())

        print("Exiting QueueMonitor")


class Data:
    def __init__(self, vector_length=None):
        self.trial_outcome_points = []
        self.current_trial_outcome_point = {}
        self.moving_average = nan_vector(length=vector_length)
        self.probability_left = nan_vector(length=vector_length)
        self.probability_right = nan_vector(length=vector_length)
        self.test__block_probability_tuple = (0.9, 0.1)


class OnlinePlottingForPS(Process):
    daemon = True

    session_name = "unnamed session"
    is_simulation = False
    data_queue = None
    kill_queue = None

    app = None
    win = None

    trial_index = 0
    values_to_show = 150
    max_trials = 1500

    simulation_update_interval = 250

    def __init__(
        self,
        session_name=None,
        is_simulation=False,
        data_queue=None,
        kill_queue=None,
        name=None,
        values_to_show=None,
        max_trials=None,
    ):
        super(OnlinePlottingForPS, self).__init__()
        self.name = self.__class__.__name__ if not name else name

        if not is_simulation and not data_queue:
            raise ValueError("Choose either simulation or provide data_queue")

        self.session_name = session_name if session_name else self.session_name
        self.is_simulation = is_simulation
        self.data_queue = data_queue
        self.kill_queue = kill_queue
        self.max_trials = max_trials if max_trials else self.max_trials
        self.values_to_show = (
            values_to_show if values_to_show else self.values_to_show
        )
        self.data = Data(vector_length=self.max_trials)

    def run(self) -> None:
        # QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)  # fixme: why is this commented out?
        # QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)
        # pg.setConfigOptions(antialias=True)  # Enable antialiasing for prettier plots

        self.app = pg.mkQApp(self.name)
        self.win = pg.GraphicsLayoutWidget(show=True, title=self.name)
        self.update_window_properties(
            window_title=Path(self.session_name).name
        )

        # Top row: trial outcomes
        self.plot_to = self.win.addPlot(name="top_row", colspan=3)
        self.viewbox_to = self.plot_to.getViewBox()
        self.viewbox_to.setMouseEnabled(x=True, y=False)
        self.viewbox_to.setRange(
            xRange=[
                self.trial_index - self.values_to_show - 1,
                self.trial_index + 1,
            ],
            yRange=[-1.5, 1.5],
        )

        axis_left = self.plot_to.getAxis("left")
        axis_bottom = self.plot_to.getAxis("bottom")

        axis_left.setLabel("Choice")
        axis_bottom.setLabel("Trial [#]")
        axis_bottom.setStyle(showValues=False)

        # # Add plots
        lw = 5  # todo: move up
        plot_to_color = mt.grey
        self.plot_trial_outcomes = pg.ScatterPlotItem()
        self.plot_moving_average = pg.PlotDataItem()
        self.plot_moving_average.setPen(color=plot_to_color, width=lw)
        self.plot_to.addItem(self.plot_trial_outcomes)
        self.plot_to.addItem(self.plot_moving_average)

        self.win.nextRow()

        # Bottom row: block probabilities
        self.plot_block = self.win.addPlot(name="bottom_row", colspan=3)
        self.plot_block.setXLink("top_row")
        axis_left_block = self.plot_block.getAxis("left")
        axis_left_block.setLabel("Probability")

        self.viewbox_block = self.plot_block.getViewBox()
        self.viewbox_block.setRange(
            xRange=[
                self.trial_index - self.values_to_show - 1,
                self.trial_index + 1,
            ],
            yRange=[0, 1],
        )
        self.viewbox_block.setMouseEnabled(x=True, y=False)

        # Data
        self.line_probability_left = pg.PlotDataItem()
        self.line_probability_right = pg.PlotDataItem()
        self.plot_block.addItem(self.line_probability_left)
        self.plot_block.addItem(self.line_probability_right)

        pleft_color, pright_color = mt.yellow, mt.teal
        self.line_probability_left.setPen(color=pleft_color, width=lw)
        self.line_probability_right.setPen(color=pright_color, width=lw)

        # Legend: bottom plot
        xpos = self.trial_index
        self.text_block_side_left = pg.TextItem("Left", color=pleft_color)
        self.plot_block.addItem(self.text_block_side_left)
        self.text_block_side_left.setPos(xpos, 0.9)

        self.text_block_side_right = pg.TextItem("Right", color=pright_color)
        self.plot_block.addItem(self.text_block_side_right)
        self.text_block_side_right.setPos(xpos, 0.8)

        # Legend: top plot
        xpos = self.trial_index  # -self.values_to_show - 1
        anchor = (-0.2, 0.5)
        self.text_choice_side_left = pg.TextItem(
            "Left", color=plot_to_color, anchor=anchor
        )
        self.plot_to.addItem(self.text_choice_side_left)
        self.text_choice_side_left.setPos(xpos, -1)

        self.text_choice_side_right = pg.TextItem(
            "Right", color=plot_to_color, anchor=anchor
        )
        self.plot_to.addItem(self.text_choice_side_right)
        self.text_choice_side_right.setPos(xpos, 1)

        # reference lines
        xdata = np.arange(0, self.max_trials)
        for ref in [0.5]:
            line_data = np.ones(shape=xdata.shape) * ref
            line = pg.PlotDataItem(x=xdata, y=line_data)
            line.setPen(color=mt.white, style=QtCore.Qt.DashLine)
            self.plot_block.addItem(line)

        if self.is_simulation:
            print("Running as simulation.")
            timer = QtCore.QTimer()
            timer.timeout.connect(self.update_simulation)
            timer.start(self.simulation_update_interval)
        else:
            print("Running as live plotting.")
            self.update_listener_thread = QueueMonitor(
                monitoring_queue=self.data_queue, kill_queue=self.kill_queue
            )
            self.update_listener_thread.update_signal.connect(self.update_data)
            self.update_listener_thread.exit_signal.connect(self.app.quit)
            self.update_listener_thread.start()

        # Add video streams
        self.win.nextRow()

        self.stream1_vb = self.win.addViewBox(lockAspect=True)
        self.stream1_image = pg.ImageItem(np.random.normal(size=(960, 720)))
        self.stream1_vb.addItem(self.stream1_image)
        # self.stream1_vb.autoRange()

        self.stream2_vb = self.win.addViewBox(lockAspect=True)
        self.stream2_image = pg.ImageItem(np.random.normal(size=(960, 720)))
        self.stream2_vb.addItem(self.stream2_image)
        # self.stream2_vb.autoRange()

        self.stream3_vb = self.win.addViewBox(lockAspect=True)
        self.stream3_image = pg.ImageItem(np.random.normal(size=(960, 720)))
        self.stream3_vb.addItem(self.stream3_image)
        # self.stream3_vb.autoRange()

        self.stream1_capture = None
        self.stream2_capture = None
        self.stream3_capture = None

        stream_update_timer = QtCore.QTimer()
        stream_update_timer.timeout.connect(self.update_streams)
        stream_update_timer.start()  # 30fps: 1/30=33ms

        # Exit clean
        self.app.aboutToQuit.connect(self.add_sig_term)
        self.app.aboutToQuit.connect(self.win.close)

        # RUN
        if self.app:
            exit(self.app.exec_())

        self.update_listener_thread.quit()

    def add_sig_term(self):
        self.kill_queue.put(True)

    def update_window_properties(
        self,
        window_title="this_process",
        frame_margins=0.01,
        window_height=0.25,
    ):
        cursor = self.app.desktop().cursor().pos()
        screen = self.app.desktop().screenNumber(cursor)
        screen_size_px = self.app.desktop().screenGeometry(screen)
        new_top_width_margin = int(screen_size_px.width() * frame_margins)
        new_top_height_margin = int(screen_size_px.height() * frame_margins)
        # new geometry
        pos = QtCore.QPoint(new_top_width_margin, new_top_height_margin)
        new_w = int(
            screen_size_px.width() - 2 * frame_margins * screen_size_px.width()
        )
        new_h = int(screen_size_px.height() * window_height)
        # mov window
        self.win.move(pos)
        self.win.resize(new_w, new_h)
        self.win.setWindowTitle(window_title)
        # self.win.setFixedWidth(self.win.width())
        # self.win.setFixedHeight(self.win.height())

    def update_streams(self):
        # print("\n\n\nREADY TO UPDATE STREAM DATA\n\n\n")
        if self.stream1_capture is None:
            try:
                cap = cv.VideoCapture("http://192.168.100.21:9999")
                ret, frame = cap.read()
                if frame is not None:
                    # print("\n\n\nOPENED 21\n\n\n")
                    self.stream1_capture = cap
            except Exception:
                pass
        else:
            ret, frame = self.stream1_capture.read()
            if frame is not None:
                # frame = np.transpose(frame, axes=[1, 0, 2])
                frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                frame = np.flipud(frame)
                frame = np.transpose(frame)
                self.stream1_image.setImage(frame)
                # print("\n\n\nSET IMAGE 21\n\n\n")

        if self.stream2_capture is None:
            try:
                cap = cv.VideoCapture("http://192.168.100.22:9999")
                ret, frame = cap.read()
                if frame is not None:
                    # print("\n\n\nOPENED 22\n\n\n")
                    self.stream2_capture = cap
            except Exception:
                pass
        else:
            ret, frame = self.stream2_capture.read()
            if frame is not None:
                # frame = np.transpose(frame, axes=[1, 0, 2])
                frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                frame = np.flipud(frame)
                frame = np.transpose(frame)
                self.stream2_image.setImage(frame)
                # print("\n\n\nSET IMAGE 22\n\n\n")

        if self.stream3_capture is None:
            try:
                cap = cv.VideoCapture("http://192.168.100.23:9999")
                ret, frame = cap.read()
                if frame is not None:
                    # print("\n\n\nOPENED 23\n\n\n")
                    self.stream3_capture = cap
            except Exception:
                pass
        else:
            ret, frame = self.stream3_capture.read()
            if frame is not None:
                # frame = np.transpose(frame, axes=[1, 0, 2])
                frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                frame = np.flipud(frame)
                frame = np.transpose(frame)
                self.stream3_image.setImage(frame)
                # self.stream3_vb.autoRange()
                # print("\n\n\nSET IMAGE 23\n\n\n")

    def update_data(self, dict_for_update=None):
        """Expected data fields in dict:
            {"trial_index": int,
             "moving_average": float,
             "block_probability_left": float,
             "block_probability_right": float,
             "choice": int,
             "rewarded": int,
             "stop": bool,
             "punished": bool,
             }

        :param dict_for_update:
        :return:
        """
        self.trial_index = dict_for_update["trial_index"]
        self.data.moving_average[self.trial_index] = dict_for_update[
            "moving_average"
        ]

        choice = dict_for_update["choice"]
        rewarded = dict_for_update["rewarded"]
        punished = dict_for_update["punished"]
        was_stop = dict_for_update["was_stop"]
        print(choice, rewarded, punished, was_stop)
        if choice == -1:
            if rewarded:
                self.data.current_trial_outcome_point = trial_outcomes[0]
            elif was_stop:  # or punished:
                if not punished:
                    self.data.current_trial_outcome_point = trial_outcomes[6]
                else:
                    self.data.current_trial_outcome_point = trial_outcomes[4]
            else:
                self.data.current_trial_outcome_point = trial_outcomes[1]
        elif choice == 1:
            if rewarded:
                self.data.current_trial_outcome_point = trial_outcomes[2]
            elif was_stop or punished:
                if not punished:
                    self.data.current_trial_outcome_point = trial_outcomes[7]
                else:
                    self.data.current_trial_outcome_point = trial_outcomes[5]
            else:
                self.data.current_trial_outcome_point = trial_outcomes[3]
        else:
            print("unknown option")
            return

        self.data.probability_left[self.trial_index] = dict_for_update[
            "block_probability_left"
        ]
        self.data.probability_right[self.trial_index] = dict_for_update[
            "block_probability_right"
        ]

        self.update_plots()
        # self.update_streams()

    def update_plots(self):
        pt = make_new_point(
            x=self.trial_index,
            y=self.data.current_trial_outcome_point["y"],
            color=self.data.current_trial_outcome_point["color"],
        )
        self.plot_trial_outcomes.addPoints([pt])
        # fixme: change addPoints to setPoints and set all from self.data.trial_outcome_points

        self.plot_moving_average.setData(self.data.moving_average)
        self.viewbox_to.setRange(
            xRange=[
                self.trial_index - self.values_to_show - 1,
                self.trial_index + 1,
            ],
            yRange=[-1.5, 1.5],  # todo: move up as param
        )
        self.line_probability_left.setData(self.data.probability_left)
        self.line_probability_right.setData(self.data.probability_right)

        # Legend
        xpos = self.trial_index  # - self.values_to_show - 1
        self.text_block_side_left.setPos(xpos, 0.9)
        self.text_block_side_right.setPos(xpos, 0.8)
        self.text_choice_side_left.setPos(xpos, -1)
        self.text_choice_side_right.setPos(xpos, 1)

        self.app.processEvents()

    def update_simulation(self):
        # Top row: trial outcomes points and moving average
        self.data.current_trial_outcome_point = draw_simulation_case()
        self.data.moving_average[self.trial_index] = draw_random_number()

        # Bottom row: block probabilities, updated every x trials
        update_interval = 20
        if not divmod(self.trial_index, update_interval)[1]:
            self.data.test__block_probability_tuple = (
                np.random.random(),
                np.random.random(),
            )

        self.data.probability_left[
            self.trial_index
        ] = self.data.test__block_probability_tuple[0]
        self.data.probability_right[
            self.trial_index
        ] = self.data.test__block_probability_tuple[1]

        self.update_plots()

        # Manually iterate trials
        self.trial_index += 1


if __name__ == "__main__":
    testing = True

    is_simulation = testing
    data_queue = Queue()
    kill_queue = Queue()

    main_process = OnlinePlottingForPS(
        is_simulation=is_simulation,
        data_queue=data_queue,
        kill_queue=kill_queue,
    )

    main_process.start()

    if testing:
        time.sleep(10)
        print("putting kill")
        kill_queue.put(True)

    main_process.join()
