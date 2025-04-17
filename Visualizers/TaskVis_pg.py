from PyQt5 import QtCore
from PyQt5 import QtWidgets

import scipy as sp
import pyqtgraph as pg

from sklearn.linear_model import LogisticRegression
from scipy.special import expit

# import visualization as vis
import seaborn as sns

from Utils import behavior_analysis_utils as bhv

# """
# matplotlib in qt5
# https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

# plotting with pyqtgraph in qt5 widgets
# https://www.learnpyqt.com/courses/graphics-plotting/plotting-pyqtgraph/
# """

"""
 
 ######## ########  ####    ###    ##       ##     ## ####  ######  
    ##    ##     ##  ##    ## ##   ##       ##     ##  ##  ##    ## 
    ##    ##     ##  ##   ##   ##  ##       ##     ##  ##  ##       
    ##    ########   ##  ##     ## ##       ##     ##  ##   ######  
    ##    ##   ##    ##  ######### ##        ##   ##   ##        ## 
    ##    ##    ##   ##  ##     ## ##         ## ##    ##  ##    ## 
    ##    ##     ## #### ##     ## ########    ###    ####  ######  
 
"""


class TrialsVis(QtWidgets.QWidget):
    def __init__(self, parent, OnlineDataAnalyser):
        super(TrialsVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # code map related - FIXME think about this, is only used for colors here
        self.OnlineDataAnalyser = OnlineDataAnalyser
        self.CodesDf = self.OnlineDataAnalyser.CodesDf
        self.trial_counter = 0

        # hardcode filter
        self.event_filter = [
            "TRIAL_ENTRY_EVENT",
            "TRIAL_ABORTED_EVENT",
            "CHOICE_EVENT",
            "SECOND_TIMING_CUE_EVENT",
            "REWARD_AVAILABLE_EVENT",
        ]

        self.initUI()
        self.OnlineDataAnalyser.trial_data_available.connect(self.update)

    def initUI(self):
        self.setWindowTitle("Trials overview")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="my title")
        self.PlotItem = self.PlotWindow.addPlot(title="trials")
        self.PlotItem.setLabel("left", text="trial #")
        self.PlotItem.setLabel("bottom", text="time", units="s")

        # the names of things that can possibly happen in the task
        self.span_names = [
            name.split("_ON")[0]
            for name in self.CodesDf["name"]
            if name.endswith("_ON")
        ]
        # self.event_names = [name.split('_EVENT')[0] for name in self.CodesDf['name'] if name.endswith('_EVENT')]
        self.event_names = [
            name for name in self.CodesDf["name"] if name.endswith("_EVENT")
        ]

        # from that: derived colors
        # colors = sns.color_palette('husl',n_colors=len(self.event_names)+len(self.span_names))
        # self.cdict = dict(zip(self.event_names+self.span_names,colors))

        # with the filter
        colors = sns.color_palette(
            "husl", n_colors=len(self.event_filter) + len(self.span_names)
        )
        self.cdict = dict(zip(self.event_filter + self.span_names, colors))

        # legend
        self.Legend = self.PlotItem.addLegend()
        for k, v in self.cdict.items():
            c = [val * 255 for val in v]
            item = pg.PlotDataItem(name=k, pen=pg.mkPen(c))
            self.Legend.addItem(item, k)

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()

    def update(self, TrialDf, TrialMetricsDf):
        try:
            self.plot_trial(TrialDf, self.trial_counter)
        except:
            pass
        self.trial_counter += 1

    def plot_trial(self, TrialDf, row_index):
        # TODO expose this
        align_time = TrialDf.loc[TrialDf["name"] == "TRIAL_ENTRY_EVENT"]["t"]

        # plotting events found in TrialDf
        # event_names = [name.split('_EVENT')[0] for name in TrialDf['name'].unique() if name.endswith('_EVENT')]

        # new version
        event_names = [name for name in TrialDf["name"] if name.endswith("_EVENT")]

        EventsDict = bhv.get_events(TrialDf, event_names)
        for event_name, EventsDf in EventsDict.items():
            if event_name in self.event_filter:  # Filter events
                for i, row in EventsDf.iterrows():
                    t = (row["t"] - align_time) / 1e3  # HARDCODE to second
                    t = t.values[0]
                    rect = pg.QtGui.QGraphicsRectItem(t, row_index, 0.005, 1)
                    col = [v * 255 for v in self.cdict[event_name]]
                    rect.setPen(pg.mkPen(col))
                    rect.setBrush(pg.mkBrush(col))
                    self.PlotItem.addItem(rect)

        # plotting spans found in TrialDf
        span_names = [
            name.split("_ON")[0]
            for name in TrialDf["name"].unique()
            if name.endswith("_ON")
        ]
        SpansDict = bhv.get_spans(TrialDf, span_names)
        for span_name, SpansDf in SpansDict.items():
            for i, row in SpansDf.iterrows():
                t = (row["t_on"] - align_time) / 1e3  # HARDCODE to second
                t = t.values[0]
                col = [v * 255 for v in self.cdict[span_name]]
                if span_name == "LICK":
                    col.append(150)  # reduced opacity
                    rect = pg.QtGui.QGraphicsRectItem(
                        t, row_index + 0.05, row["dt"] / 1e3, 0.9
                    )  # HARDCODE to second
                else:
                    rect = pg.QtGui.QGraphicsRectItem(
                        t, row_index, row["dt"] / 1e3, 1
                    )  # HARDCODE to second
                rect = pg.QtGui.QGraphicsRectItem(
                    t, row_index, row["dt"] / 1e3, 1
                )  # HARDCODE to second
                rect.setPen(pg.mkPen(col))
                rect.setBrush(pg.mkBrush(col))
                self.PlotItem.addItem(rect)


"""
 
  ######  ########  ######   ######  ####  #######  ##    ## ##     ## ####  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##     ##  ##  ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##     ##  ##  ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ## ##     ##  ##   ######  
       ## ##             ##       ##  ##  ##     ## ##  ####  ##   ##   ##        ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ###   ## ##    ##  ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##    ###    ####  ######  
 
"""


class SessionVis(QtWidgets.QWidget):
    """A general visualizer for SessionDf"""

    def __init__(self, parent, OnlineDataAnalyser):
        super(SessionVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()
        self.OnlineDataAnalyser = OnlineDataAnalyser

        OnlineDataAnalyser.trial_data_available.connect(self.on_data)

    def add_LinePlot(self, pens, PlotWindow, title=None, xlabel=None, ylabel=None):
        Item = PlotWindow.addPlot(title=title)
        Item.setLabel("left", text=ylabel)
        Item.setLabel("bottom", text=xlabel)
        Lines = [Item.plot(pen=pen) for pen in pens]
        return Lines

    def add_ScatterPlot(self, pens, PlotWindow, title=None, xlabel=None, ylabel=None):
        Item = PlotWindow.addPlot(title=title)
        Item.setLabel("left", text=ylabel)
        Item.setLabel("bottom", text=xlabel)
        Scatters = [
            Item.plot(symbolBrush=(100, 100, 100), symbolSize=5, pen=None)
            for pen in pens
        ]
        return Scatters

    def initUI(self):
        self.setWindowTitle("Session performance monitor")
        self.Layout = QtWidgets.QHBoxLayout()

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow()  # deprecated use of graphicsWindow

        pen_1 = pg.mkPen(color=(200, 100, 100), width=2)
        pen_2 = pg.mkPen(color=(150, 100, 100), width=2)

        kwargs = dict(title="ITI", xlabel="trial #", ylabel="time (s)")
        (self.TrialRateLine,) = self.add_LinePlot([pen_1], self.PlotWindow, **kwargs)
        self.PlotWindow.nextColumn()

        kwargs = dict(title="success rate", xlabel="trial #", ylabel="frac.")
        self.SuccessRateLines = self.add_LinePlot(
            [pen_1, pen_2], self.PlotWindow, **kwargs
        )
        self.PlotWindow.nextColumn()

        kwargs = dict(
            title="reward collection rate", xlabel="succ. trial #", ylabel="frac."
        )
        self.RewardCollectedLines = self.add_LinePlot(
            [pen_1, pen_2], self.PlotWindow, **kwargs
        )
        self.PlotWindow.nextRow()

        kwargs = dict(
            title="reward collection RT", xlabel="succ. trial #", ylabel="time (ms)"
        )
        (self.RewardRTLine,) = self.add_LinePlot([pen_1], self.PlotWindow, **kwargs)
        self.PlotWindow.nextColumn()

        kwargs = dict(title="choice RT", xlabel="trial #", ylabel="time (ms)")
        (self.ChoiceRTScatter,) = self.add_ScatterPlot(
            [pen_1], self.PlotWindow, **kwargs
        )
        self.PlotWindow.nextColumn()

        kwargs = dict(title="psychometric", xlabel="time (s)", ylabel="p")
        (self.PsychLine,) = self.add_LinePlot([pen_1], self.PlotWindow, **kwargs)
        (self.PsychScatter,) = self.add_ScatterPlot([pen_1], self.PlotWindow, **kwargs)
        self.PlotWindow.nextColumn()

        # self.PlotItem.setYRange(-8000,8000)

        # Item = self.PlotWindow.addPlot()
        # self.ChoicesScatter = Item.plot(pen=(100,100,100), symbolBrush=(100,100,100),symbolSize=2)

        # done
        self.Layout.addWidget(self.PlotWindow)

        self.setLayout(self.Layout)
        self.show()

    def on_data(self, TrialDf, TrialMetricsDf):
        hist = 20  # to be exposed in the future
        if self.OnlineDataAnalyser.SessionDf is not None:
            SessionDf = self.OnlineDataAnalyser.SessionDf

            # ITI
            x = SessionDf.index.values[1:]
            y = sp.diff(SessionDf["t"].values / 1000)

            self.TrialRateLine.setData(x=x, y=y)

            # success rate
            x = SessionDf.index.values + 1
            y = sp.cumsum(SessionDf["successful"].values) / (SessionDf.index.values + 1)

            y_filt = SessionDf["successful"].rolling(hist).mean().values

            self.SuccessRateLines[0].setData(x=x, y=y)
            self.SuccessRateLines[1].setData(x=x, y=y_filt)

            # reward collection rate
            if True in SessionDf["successful"].values:
                SDf = SessionDf.groupby("successful").get_group(True)
                x = SDf.index.values + 1
                y = sp.cumsum(SDf["reward_collected"].values) / (SDf.index.values + 1)
                y_filt = SDf["reward_collected"].rolling(hist).mean().values
                self.RewardCollectedLines[0].setData(x=x, y=y)
                self.RewardCollectedLines[1].setData(x=x, y=y_filt)

            # reward collection reaction time
            if True in SessionDf["reward_collected"].values:
                SDf = SessionDf.groupby("reward_collected").get_group(True)
                x = SDf.index.values + 1
                y = SDf["reward_collected_rt"].values
                self.RewardRTLine.setData(x=x, y=y)

            # choice reaction time
            if True in SessionDf["has_choice"].values:
                SDf = SessionDf.groupby("has_choice").get_group(True)
                x = SDf.index.values + 1
                y = SDf["choice_rt"].values
                self.ChoiceRTScatter.setData(x=x, y=y)

            # psychometric
            if True in SessionDf["has_choice"].values:
                SDf = SessionDf[["this_interval", "choice"]].dropna()
                X = SDf["this_interval"].values[:, sp.newaxis]
                y = (SDf["choice"].values == "right").astype("float32")
                self.PsychScatter.setData(X.flatten(), y)

                try:
                    cLR = LogisticRegression()
                    cLR.fit(X, y)

                    x_fit = sp.linspace(0, 3000, 100)
                    psychometric = expit(x_fit * cLR.coef_ + cLR.intercept_).ravel()
                    self.PsychLine.setData(x=x_fit, y=psychometric)
                except:
                    pass
