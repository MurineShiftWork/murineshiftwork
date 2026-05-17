import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

app = pg.mkQApp()
mw = QtGui.QMainWindow()
mw.setWindowTitle("pyqtgraph example: PlotWidget")
mw.resize(1000, 400)
cw = QtGui.QWidget()
mw.setCentralWidget(cw)
layout = QtGui.QVBoxLayout()
cw.setLayout(layout)

pw = pg.PlotWidget(name="Plot1")
layout.addWidget(pw)
mw.show()

p1 = pw.plot()
p1.setPen((200, 0, 200))

pw.setLabel("left", "Value", units="V")
pw.setLabel("bottom", "Time", units="s")
pw.setXRange(0, 2)
pw.setYRange(0, 1e-10)


def rand(n):
    data = np.random.random(n)
    data[int(n * 0.1) : int(n * 0.13)] += 0.5
    data[int(n * 0.18)] += 2
    data[int(n * 0.1) : int(n * 0.13)] *= 5
    data[int(n * 0.18)] *= 20
    data *= 1e-12
    return data, np.arange(n, n + len(data)) / float(n)


def updateData():
    yd, xd = rand(10000)
    p1.setData(y=yd, x=xd)


# Start a timer to rapidly update the plot in pw
t = QtCore.QTimer()
t.timeout.connect(updateData)
t.start(50)
# updateData()


# Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == "__main__":
    import sys

    if (sys.flags.interactive != 1) or not hasattr(QtCore, "PYQT_VERSION"):
        QtGui.QApplication.instance().exec_()
