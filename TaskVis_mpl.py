import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp

import visualization as vis
import pandas as pd
import seaborn as sns
# TODO those functions are not vis but more analysis utils

import utils


"""
matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html
"""


class MyMplCanvas(FigureCanvas):
    # FIXME add controls
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent, width=7, height=9, dpi=100):
        super(MyMplCanvas, self).__init__(parent=parent)

        # figure init
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)

        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        # connect signals
        self.parent.ArduinoController.Signals.serial_data_available.connect(self.update_data)
        self.init()
        self.show()

    def on_data(self, TrialDf, TrialMetricsDf):
        print(TrialDf)
        print(TrialMetricsDf)