"""
Demonstrate the use of layouts to control placement of multiple plots / views /
labels
"""

import cv2 as cv
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore

app = pg.mkQApp("Gradiant Layout Example")
view = pg.GraphicsView()
layout = pg.GraphicsLayout(border=(100, 100, 100))
view.setCentralItem(layout)
view.show()
view.setWindowTitle("pyqtgraph example: GraphicsLayout")
view.resize(800, 600)

## Title at top
text = """
This example demonstrates the use of GraphicsLayout to arrange items in a grid.<br>
The items added to the layout must be subclasses of QGraphicsWidget (this includes <br>
PlotItem, ViewBox, LabelItem, and GrphicsLayout itself).
"""
layout.addLabel(text, col=1, colspan=4)
layout.nextRow()

## Put vertical label on left side
layout.addLabel("Long Vertical Label", angle=-90, rowspan=3)

## Add 3 plots into the first row (automatic position)
p1 = layout.addPlot(title="Plot 1")
p2 = layout.addPlot(title="Plot 2")
# p3 = l.addPlot(title="Plot 3")
vb = layout.addViewBox(lockAspect=True)
img = pg.ImageItem(np.random.normal(size=(100, 100)))
vb.addItem(img)
vb.autoRange()


## Add a sub-layout into the second row (automatic position)
## The added item should avoid the first column, which is already filled
layout.nextRow()
l2 = layout.addLayout(colspan=3, border=(50, 0, 0))
l2.setContentsMargins(10, 10, 10, 10)
l2.addLabel(
    "Sub-layout: this layout demonstrates the use of shared axes and axis labels",
    colspan=3,
)
l2.nextRow()
l2.addLabel("Vertical Axis Label", angle=-90, rowspan=2)
p21 = l2.addPlot()
p22 = l2.addPlot()
l2.nextRow()
p23 = l2.addPlot()
p24 = l2.addPlot()
l2.nextRow()
l2.addLabel("HorizontalAxisLabel", col=1, colspan=2)

## hide axes on some plots
p21.hideAxis("bottom")
p22.hideAxis("bottom")
p22.hideAxis("left")
p24.hideAxis("left")
p21.hideButtons()
p22.hideButtons()
p23.hideButtons()
p24.hideButtons()


## Add 2 more plots into the third row (manual position)
p4 = layout.addPlot(row=3, col=1)
p5 = layout.addPlot(row=3, col=2, colspan=2)
p3 = layout.addPlot(row=4, col=1, colspan=2, title="Plot 3")
## show some content in the plots
p1.plot([1, 3, 2, 4, 3, 5])
p2.plot([1, 3, 2, 4, 3, 5])
p4.plot([1, 3, 2, 4, 3, 5])
p5.plot([1, 3, 2, 4, 3, 5])


# timer = QtCore.QTimer()
# timer.setSingleShot(True)
# not using QTimer.singleShot() because of persistence on PyQt. see PR #1605


# cap = cv.VideoCapture(0)
cap = cv.VideoCapture("http://192.168.100.21:9999")


def update():
    global cap, img

    ret, frame = cap.read()
    if frame is not None:
        img.setImage(frame)


timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)

if __name__ == "__main__":
    pg.exec()
