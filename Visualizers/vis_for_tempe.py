import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib as mpl
import matplotlib.pyplot as plt

from PyQt5 import QtWidgets

import numpy as np


"""
matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

https://stackoverflow.com/questions/48140576/matplotlib-toolbar-in-a-pyqt5-application

"""
outcomes = ["correct", "incorrect", "premature", "missed"]

colors = dict(
    success="#72E043",
    reward="#3CE1FA",
    correct="#72E043",
    incorrect="#F56057",
    premature="#9D5DF0",
    missed="#F7D379",
)


class SessionVis(QtWidgets.QWidget):
    # FIXME add controls
    """Ultimately, this is a QWidget (as well as a Figureself.CanvasAgg, etc.)."""

    def __init__(self, parent, OnlineDataAnalyser, width=9, height=8):
        super(SessionVis, self).__init__()

        # figure init
        # self.fig = Figure(figsize=(width, height), dpi=dpi)
        # self.fig = Figure()
        # self.fig, self.axes = plt.subplots(nrows=2, ncols=3)

        self.fig = plt.figure()  # constrained_layout=True)

        self.Canvas = FigureCanvas(self.fig)
        self.Canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.Canvas.updateGeometry()

        Toolbar = NavigationToolbar(self.Canvas, self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(Toolbar)
        layout.addWidget(self.Canvas)

        self.setLayout(layout)

        self.init()
        self.show()

        # connect signals
        self.OnlineDataAnalyser = OnlineDataAnalyser
        OnlineDataAnalyser.trial_data_available.connect(self.on_data)

    def init(self):
        # gridspec = self.fig.add_gridspec(3, 2, height_ratios=[0.2,1,1])
        # self.axes = [gs[0,:],gs[1,0],gs[1,1],gs[2,0],gs[2,1]]

        # self.Plotters = [OverviewBarplot(self.fig.add_subplot(gridspec[0,:])),
        #                  SessionOverviewPlot(self.fig.add_subplot(gridspec[1,:])),
        #                  SuccessratePlot(self.fig.add_subplot(gridspec[2,0])),
        #                  ChoiceRTPlot(self.fig.add_subplot(gridspec[2,1]))]

        gridspec = self.fig.add_gridspec(1, 2, height_ratios=[0.2, 1, 1])

        self.Plotters = [
            RewardRTScatter(self.fig.add_subplot(gridspec[0, 0])),
            RateLine(self.fig.add_subplot(gridspec[2, 1])),
        ]

        self.fig.tight_layout()

    def on_data(self, TrialDf, TrialMetricsDf):
        if self.OnlineDataAnalyser.SessionDf is not None:  # FIXME
            SessionDf = self.OnlineDataAnalyser.SessionDf
            for Plotter in self.Plotters:
                Plotter.update(SessionDf)

        self.Canvas.draw()


class RewardRTScatter(object):
    """and this one not abstracted because of what?"""

    def __init__(self, axes):
        self.axes = axes

        # Reward collection RT
        self.axes.set_title("reward collection RT")
        self.axes.set_xlabel("trial #")
        self.axes.set_ylabel("RT (ms)")
        (self.scatter,) = self.axes.plot([], [], "o")
        self.axes.set_ylim(0, 2500)
        self.axes.xaxis.set_major_locator(
            mpl.ticker.MaxNLocator(nbins="auto", integer=True)
        )

    def update(self, SessionDf):
        if True in SessionDf["has_choice"].values:
            SDf = SessionDf.groupby("has_choice").get_group(True)
            SDf = SDf.reset_index()
            x = SDf.index.values + 1
            y = SDf["choice_rt"].values
            self.scatter.set_data(x, y)
            self.axes.set_xlim(0.5, x.shape[0] + 0.5)
            # self.choices_rt_scatter.axes.set_ylim(0, sp.percentile(y, 95))


class RateLine(object):
    """abstracted because can be reused?"""

    def __init__(self, axes):  # , hist, var_name, label, color):
        self.hist = 5  # hist
        self.var_name = "has_reward_collected"
        label = "reward collected"
        color = "k"
        self.axes = axes
        self.axes.set_title(label)
        self.axes.set_xlabel("trial #")
        self.axes.set_ylabel("fraction")
        self.axes.set_ylim(-0.1, 1.1)

        (self.line,) = self.axes.plot([], [], ".", lw=1, label=label, color=color)
        (self.line_filt,) = self.axes.plot([], [], lw=1, color=color)
        self.axes.legend(fontsize="x-small")
        self.axes.xaxis.set_major_locator(
            mpl.ticker.MaxNLocator(nbins="auto", integer=True)
        )

    def update(self, SessionDf):
        x = SessionDf.index.values + 1
        y = np.cumsum(SessionDf[self.var_name].values) / (SessionDf.index.values + 1)
        y_filt = SessionDf[self.var_name].rolling(self.hist).mean().values

        self.line.set_data(x, y)
        self.line_filt.set_data(x, y_filt)
        self.axes.set_xlim(0.5, x.shape[0] + 0.5)
