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
        gridspec = self.fig.add_gridspec(3, 2, height_ratios=[0.2, 1, 1])
        # self.axes = [gs[0,:],gs[1,0],gs[1,1],gs[2,0],gs[2,1]]

        self.Plotters = [
            OverviewBarplot(self.fig.add_subplot(gridspec[0, :])),
            SessionOverviewPlot(self.fig.add_subplot(gridspec[1, :])),
            SuccessratePlot(self.fig.add_subplot(gridspec[2, 0])),
            ChoiceRTPlot(self.fig.add_subplot(gridspec[2, 1])),
        ]

        self.fig.tight_layout()

    def on_data(self, TrialDf, TrialMetricsDf):
        if self.OnlineDataAnalyser.SessionDf is not None:  # FIXME
            SessionDf = self.OnlineDataAnalyser.SessionDf
            for Plotter in self.Plotters:
                Plotter.update(SessionDf)

        self.Canvas.draw()


class SessionOverviewPlot(object):
    def __init__(self, axes):
        self.axes = axes
        self.axes.set_title("overview")
        self.axes.set_xlabel("trial #")
        self.axes.set_ylabel("fraction")
        self.axes.set_ylim(-0.3, 1.3)
        (self.bias,) = self.axes.plot([], [], ".", lw=1, label="bias", color="k")
        (self.bias_filt,) = self.axes.plot([], [], lw=1, color="k")
        cmap = mpl.cm.PiYG
        (self.trials_left,) = self.axes.plot([], [], "|", color="k")
        (self.trials_right,) = self.axes.plot([], [], "|", color="k")
        (self.in_corr,) = self.axes.plot([], [], "|", color="r")
        (self.choices_left,) = self.axes.plot([], [], "|", color=cmap(1.0))
        (self.choices_right,) = self.axes.plot([], [], "|", color=cmap(0.0))
        self.axes.legend(fontsize="x-small")
        self.axes.set_yticks([0, 1])
        self.axes.set_yticklabels(["left", "right"])
        self.axes.set_ylabel("choice")
        self.axes.xaxis.set_major_locator(
            mpl.ticker.MaxNLocator(nbins="auto", integer=True)
        )

    def update(self, SessionDf):
        # choices
        x = (
            SessionDf.loc[SessionDf["correct_side"] == 4].index + 1
        )  # previously correct zone
        y = np.zeros(x.shape[0]) - 0.1
        self.trials_left.set_data(x, y)
        x = (
            SessionDf.loc[SessionDf["correct_side"] == 6].index + 1
        )  # previously correct zone
        y = np.zeros(x.shape[0]) + 1.1
        self.trials_right.set_data(x, y)

        x = SessionDf.loc[SessionDf["in_corr_loop"] == True].index + 1
        y = np.zeros(x.shape[0]) + 1.2
        self.in_corr.set_data(x, y)

        try:
            SDf = SessionDf.groupby("choice").get_group("left")
            x = SDf.index.values + 1
            y = np.zeros(x.shape[0])
            self.choices_left.set_data(x, y)
        except:
            pass

        try:
            SDf = SessionDf.groupby("choice").get_group("right")
            x = SDf.index.values + 1
            y = np.zeros(x.shape[0]) + 1
            self.choices_right.set_data(x, y)
        except:
            pass

        x = SessionDf.index
        y = SessionDf["bias"].values
        self.bias.set_data(x, y)
        # y_filt = SDf['bias'].rolling(hist).mean().values
        # self.bias_filt.set_data(x, y_filt)
        self.bias.axes.set_xlim(0.5, SessionDf.shape[0] + 0.5)


class OverviewBarplot(object):
    def __init__(self, axes):
        self.axes = axes
        self.axes.set_title("outcomes")
        self.axes.set_xlabel("trial #")
        self.axes.set_ylim(-0.1, 1.1)
        self.axes.set_yticks([])
        self.axes.xaxis.set_major_locator(
            mpl.ticker.MaxNLocator(nbins="auto", integer=True)
        )

    def update(self, SessionDf):
        try:
            x = SessionDf.index[-1]
            y = 0
            outcome = SessionDf.iloc[-1]["outcome"]
            rect = mpl.patches.Rectangle(
                (x, y), 1, 1, edgecolor="none", facecolor=colors[outcome]
            )
            self.axes.add_patch(rect)
            self.axes.set_xlim(0.5, SessionDf.shape[0] + 0.5)
        except:
            pass


class ChoiceRTPlot(object):
    def __init__(self, axes):
        self.axes = axes

        # choice RT
        self.axes.set_title("choice RT")
        self.axes.set_xlabel("choice trial #")
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


class SuccessratePlot(object):
    def __init__(self, axes):
        self.hist = 5
        self.axes = axes
        self.axes.set_title("success rate")
        self.axes.set_xlabel("trial #")
        self.axes.set_ylabel("fraction")
        self.axes.set_ylim(-0.1, 1.1)

        (self.line,) = self.axes.plot(
            [], [], ".", lw=1, label="success", color=colors["success"]
        )
        (self.line_filt,) = self.axes.plot([], [], lw=1, color=colors["success"])
        # self.reward_collection_rate, = ax.plot([], [], '.', lw=1, label='rew.coll.', color=colors['reward'])
        # self.reward_collection_rate_filt, = ax.plot([], [], lw=1, color=colors['reward'])
        self.axes.legend(fontsize="x-small")
        self.axes.xaxis.set_major_locator(
            mpl.ticker.MaxNLocator(nbins="auto", integer=True)
        )

    def update(self, SessionDf):
        x = SessionDf.index.values + 1
        y = np.cumsum(SessionDf["successful"].values) / (SessionDf.index.values + 1)
        y_filt = SessionDf["successful"].rolling(self.hist).mean().values

        self.line.set_data(x, y)
        self.line_filt.set_data(x, y_filt)
        self.axes.set_xlim(0.5, x.shape[0] + 0.5)


# psychmetric

# psychometric
# ax = self.axes[1, 2]
# ax.set_title('psychometric')
# # ax.set_ylabel('p')
# ax.set_xlabel('interval (ms)')
# ax.set_yticks([0, 1])
# ax.set_yticklabels(['short', 'long'])
# ax.set_ylabel('choice')
# ax.axvline(1500, linestyle=':', alpha=0.5, lw=1, color='k')
# self.psych_choices, = ax.plot([], [], '.', color='k', alpha=0.5)
# self.psych_fit, = ax.plot([], [], lw=2, color='r')
# self.poly = None # fill for error model


# get only the subset with choices
# if True in SessionDf['has_choice'].values:
#     SDf = SessionDf.groupby('has_choice').get_group(True)
#     y = SDf['choice'].values == 'right'
#     x = SDf['this_interval'].values

#     # choices
#     self.psych_choices.set_data(x, y)

#     # logistic regression
#     x_fit = sp.linspace(0, 3000, 50)

#     try:
#         # y_fit = sp.zeros(x_fit.shape[0])
#         y_fit = bhv.log_reg(x, y, x_fit)
#         self.psych_fit.set_data(x_fit, y_fit)
#     except ValueError:
#         pass

#     try:
#         # error model
#         # if x.shape[0] > 5:
#         #     utils.debug_trace()
#         bias = y.sum() / y.shape[0] # right side bias
#         N = 50
#         R = sp.array([bhv.log_reg(x, sp.rand(x.shape[0]) < bias, x_fit) for i in range(N)])

#         alpha = .05 * 100
#         R_pc = sp.percentile(R, (alpha, 100-alpha), 0)

#         if self.poly is not None:
#             self.poly.remove()

#         self.poly = self.psych_fit.axes.fill_between(x_fit, R_pc[0], R_pc[1], color='black', alpha=0.5)

#     except ValueError:
#         pass

#     self.psych_choices.axes.set_xlim(0, 3000)
#     self.psych_choices.axes.set_ylim(-0.1, 1.1)
