import sys
import time
from multiprocessing import Process

import cv2 as cv
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class QueueMonitor(QtCore.QThread):
    update_signal = QtCore.pyqtSignal(dict)
    exit_signal = QtCore.pyqtSignal(bool)
    monitoring_queue = None
    kill_queue = None

    def __init__(self, monitoring_queue=None, kill_queue=None):
        super(QueueMonitor, self).__init__()
        self.monitoring_queue = monitoring_queue
        self.kill_queue = kill_queue

    def stop(self):
        self.stopped = True

    def run(self) -> None:
        cap = cv.VideoCapture("http://192.168.100.31:9999")

        while True:
            time.sleep(0.01)
            if not self.kill_queue.empty():
                self.exit_signal.emit(True)
                break
            else:
                ret, frame = cap.read()
                if frame is not None:
                    self.update_signal.emit(frame)
                # if not self.monitoring_queue.empty():
                #     data = self.monitoring_queue.get()
                #     self.update_signal.emit(data)

        print("Exiting QueueMonitor")


class Display(Process):
    def __init__(self, queues: dict = None, config: dict = None):
        super(Display, self).__init__()
        self.queues = queues
        self.dt_min = 1
        self.dt_max = 0
        self.dt_avg = 0.1

    def run(self) -> None:
        # self.app = pg.mkQApp(self.name)
        self.app = QtWidgets.QApplication([])
        self.win = pg.GraphicsLayoutWidget(show=True, title=self.name)

        self.update_window_properties(window_title="WIN-NAME")

        vb = pg.ViewBox()
        self.win.setCentralWidget(vb)

        vb.setAspectLocked()
        self.img = pg.ImageItem(border="w")
        vb.addItem(self.img)

        print("Making THREAD")
        self.update_listener_thread = QueueMonitor(
            monitoring_queue=None,  # self.queues["tracking-to-display"],
            kill_queue=self.queues["kill"],
        )
        self.update_listener_thread.update_signal.connect(self.update_data)
        self.update_listener_thread.exit_signal.connect(self.app.quit)
        self.update_listener_thread.start()

        # Exit clean
        self.app.aboutToQuit.connect(self.add_sig_term)
        self.app.aboutToQuit.connect(self.win.close)

        # RUN
        if self.app:
            print("OPENING DISPLAY")
            # self.win.show()
            exit(pg.exec())
            # exit(self.app.exec())

        self.update_listener_thread.quit()
        self.add_sig_term()

    def add_sig_term(self):
        self.queues["kill"].put(True)

    def update_window_properties(
        self,
        window_title="this_process",
        frame_margins=0.01,
        window_width=0.25,
        window_height=0.25,
    ):
        # current screen size
        cursor = self.win.cursor().pos()
        screen = self.app.screenAt(cursor)
        screen_size_px = screen.geometry()
        # new geometry
        new_top_width_margin = int(screen_size_px.width() * frame_margins)
        new_top_height_margin = int(screen_size_px.height() * frame_margins)
        pos = QtCore.QPoint(new_top_width_margin, new_top_height_margin)
        new_w = int(screen_size_px.width() * window_width)
        new_h = int(screen_size_px.height() * window_height)
        # mov window
        self.win.move(pos)
        self.win.resize(new_w, new_h)
        self.win.setWindowTitle(window_title)

    def update_data(self, data):
        print("updating data")
        if data is None:
            print("no DATA")
            return

        frame = data
        # frame = data["tracking"]["frame_out"]
        # centroid = [int(c) for c in data["tracking"]["centroid_contour"]]
        #
        # pointRadius = 5
        # cv.circle(
        #     frame,
        #     centroid,
        #     pointRadius,
        #     (0, 255, 0),
        #     -1,
        # )
        frame = np.swapaxes(frame, 0, 1)
        frame = np.flipud(frame)

        self.img.setImage(frame)
        self.app.processEvents()


if __name__ == "__main__":
    import logging
    from multiprocessing import Queue

    queues = {"kill": Queue()}
    display = Display(queues=queues)
    display.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            queues["kill"].put(True)
            break

    logging.info("SHUTTING DOWN..")
    queues.get("kill").put(True)
    logging.info("WAITING FOR SHUTDOWN")
    time.sleep(1)

    # for process, handle in processes.items():
    display.join(timeout=0.1)

    logging.info("END")
