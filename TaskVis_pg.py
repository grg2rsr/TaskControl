from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp
import pyqtgraph as pg

# import visualization as vis
import functions
import pandas as pd
import seaborn as sns

import behavior_analysis_utils as bhv
import utils

# """
# matplotlib in qt5
# https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

# plotting with pyqtgraph in qt5 widgets
# https://www.learnpyqt.com/courses/graphics-plotting/plotting-pyqtgraph/
# """

"""
 
 ########     ###    ########   ######  ######## ########  
 ##     ##   ## ##   ##     ## ##    ## ##       ##     ## 
 ##     ##  ##   ##  ##     ## ##       ##       ##     ## 
 ########  ##     ## ########   ######  ######   ########  
 ##        ######### ##   ##         ## ##       ##   ##   
 ##        ##     ## ##    ##  ##    ## ##       ##    ##  
 ##        ##     ## ##     ##  ######  ######## ##     ## 
 
general idea: the parser takes care of the incoming data and reformats
it into data structures that can be used by the pg_plotters

"""

class Signals(QtCore.QObject):
    # explained here why this has to be within a QObject
    # https://programmer.group/pyqt5-quick-start-pyqt5-signal-slot-mechanism.html
    trial_data_available = QtCore.pyqtSignal(pd.DataFrame, pd.DataFrame)

class LineParser():
    def __init__(self, CodesDf, Metrics):
        self.CodesDf = CodesDf
        self.Metrics = Metrics
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))
        self.lines = []
        self.Signals = Signals()

    def update(self,line):
        # if decodeable
        if not line.startswith('<'):
            code,t = line.split('\t')
            decoded = self.code_map[code]
            t = float(t)

            # the signal with which a trial ends
            if decoded == "TRIAL_AVAILABLE_STATE": # TODO expose hardcode
                # parse lines
                TrialDf = bhv.parse_lines(self.lines, code_map=self.code_map)
                TrialMetricsDf = bhv.parse_trial(TrialDf, self.Metrics)
                
                # emit data
                self.Signals.trial_data_available.emit(TrialDf,TrialMetricsDf)

                # restart lines with current line
                self.lines = [line]
            else:
                self.lines.append(line)

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
    def __init__(self, parent, Parser, CodesDf=None):
        super(TrialsVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # code map related
        self.CodesDf = CodesDf
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        self.trial_counter = 0

        self.initUI()
        self.Parser = Parser
        self.Parser.Signals.trial_data_available.connect(self.update)

    def initUI(self):
        self.setWindowTitle("Trials overview")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="my title")
        self.PlotItem = self.PlotWindow.addPlot(title='trials')
        self.PlotItem.setLabel("left",text="trial #")
        self.PlotItem.setLabel("bottom",text="time", units="s")
        
        # the names of things that can possibly happen in the task
        self.span_names = [name.split('_ON')[0] for name in self.CodesDf['name'] if name.endswith('_ON')]
        self.event_names = [name.split('_EVENT')[0] for name in self.CodesDf['name'] if name.endswith('_EVENT')]

        # from that: derived colors
        colors = sns.color_palette('husl',n_colors=len(self.event_names)+len(self.span_names))
        self.cdict = dict(zip(self.event_names+self.span_names,colors))

        # legend
        self.Legend = self.PlotItem.addLegend()
        for k,v in self.cdict.items():
            c = [val*255 for val in v]
            item = pg.PlotDataItem(name=k,pen=pg.mkPen(c))
            self.Legend.addItem(item, k)

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()

    def update(self, TrialDf, TrialMetricsDf):
        self.plot_trial(TrialDf, self.trial_counter)
        self.trial_counter += 1

    def plot_trial(self, TrialDf, row_index):
        # TODO expose this
        align_time = TrialDf.loc[TrialDf['name'] == 'TRIAL_ENTRY_EVENT']['t']

        # plotting events found in TrialDf
        event_names = [name.split('_EVENT')[0] for name in TrialDf['name'].unique() if name.endswith('_EVENT')]
       
        EventsDict = bhv.get_events(TrialDf, event_names)
        for event_name, EventsDf in EventsDict.items():
            for i, row in EventsDf.iterrows():
                t = (row['t'] - align_time) / 1e3 # HARDCODE to second
                rect = pg.QtGui.QGraphicsRectItem(t, row_index , 5, 1)
                col = [v*255 for v in self.cdict[event_name]]
                rect.setPen(pg.mkPen(col))
                rect.setBrush(pg.mkBrush(col))
                self.PlotItem.addItem(rect)

        # plotting spans found in TrialDf
        span_names = [name.split('_ON')[0] for name in TrialDf['name'].unique() if name.endswith('_ON')]
        SpansDict = bhv.get_spans(TrialDf, span_names)
        for span_name, SpansDf in SpansDict.items():
            for i,row in SpansDf.iterrows():
                t = (row['t_on'] - align_time) / 1e3 # HARDCODE to second
                col = [v*255 for v in self.cdict[span_name]]
                if span_name == 'LICK':
                    col.append(150) # reduced opacity
                    rect = pg.QtGui.QGraphicsRectItem(t, row_index+0.05, row['dt']/1e3, 0.9) # HARDCODE to second
                else:
                    rect = pg.QtGui.QGraphicsRectItem(t, row_index, row['dt']/1e3, 1) # HARDCODE to second
                rect = pg.QtGui.QGraphicsRectItem(t, row_index, row['dt']/1e3, 1) # HARDCODE to second
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
    """ A general visualizer for SessionDf """
    def __init__(self, parent, Parser, CodesDf=None):
        super(SessionVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        self.CodesDf = CodesDf
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        self.SessionDf = None
        self.initUI()

        self.Parser = Parser
        self.Parser.Signals.trial_data_available.connect(self.update)

    def add_LinePlot(self, pens, PlotWindow, title=None, xlabel=None, ylabel=None):
        Item = PlotWindow.addPlot(title=title)
        Item.setLabel("left", text=ylabel)
        Item.setLabel("bottom", text=xlabel)
        Lines = [Item.plot(pen=pen) for pen in pens]
        return Lines

    def initUI(self):
        self.setWindowTitle("Session performance monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow()

        pen_1 = pg.mkPen(color=(200,100,100),width=2)
        pen_2 = pg.mkPen(color=(150,100,100),width=2)

        kwargs = dict(title="ITI", xlabel="trial #", ylabel="time (s)")
        self.TrialRateLine, = self.add_LinePlot([pen_1], self.PLotWindow, **kwargs)
        self.PlotWindow.nextColumn()

        kwargs = dict(title="success rate", xlabel="trial #", ylabel="frac.")
        self.SuccessRateLines = self.add_LinePlot([pen_1, pen_2], self.PLotWindow, **kwargs)
        self.PlotWindow.nextColumn()

        kwargs = dict(title="reward collection rate", xlabel="succ. trial #", ylabel="frac.")
        self.RewardCollectedLines = self.add_LinePlot([pen_1, pen_2], self.PLotWindow, **kwargs)
        self.PlotWindow.nextColumn()

        kwargs = dict(title="reward collection RT", xlabel="succ. trial #", ylabel="time (ms)")
        self.RewardRTLine, = self.add_LinePlot([pen_1], self.PLotWindow, **kwargs)
        self.PlotWindow.nextColumn()
       
        self.Layout.addWidget(self.PlotWindow)

        self.setLayout(self.Layout)
        self.show()

    def update_plot(self):
        hist = 20 # to be exposed in the future
        # ITI
        x = self.SessionDfindex.values[1:]
        y = sp.diff(self.SessionDf['t'].values / 1000)
        self.TrialRateLine.setData(x=x, y=y)
        
        # success rate
        x = self.SessionDf.index.values+1
        y = sp.cumsum(self.SessionDf['successful'].values) / (self.SessionDf.index.values+1)
        y_filt = self.SessionDf['successful'].rolling(hist).mean()
        self.SuccessRateLines[0].setData(x=x,y=y)
        self.SuccessRateLines[1].setData(x=x,y=y_filt)

        # reward collection rate
        SDf = self.SessionDf.groupby('successful').get_group(True)
        x = SDf.index.values+1
        y = sp.cumsum(SDf['reward_collected'].values) / (SDf.index.values+1)
        y_filt = SDf['reward_collected'].rolling(hist).mean()
        self.RewardCollectedLines[0].setData(x=x,y=y)
        self.RewardCollectedLines[1].setData(x=x,y=y_filt)

        # reward collection reaction time
        SDf = self.SessionDf.groupby('reward_collected').get_group(True)
        x = SDf.index.values+1
        y = SDf['rew_col_rt']
        self.RewardTRLine.setData(x=x,y=y)

    def update(self, TrialsDf, TrialMetricsDf):
        # append Trial
        if self.SessionDf is None:
            self.SessionDf = TrialMetricsDf
        else:
            self.SessionDf = self.SessionDf.append(TrialMetricsDf)
        
        self.update_plot()

