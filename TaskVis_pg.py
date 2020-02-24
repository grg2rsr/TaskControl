from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp
import pyqtgraph as pg

# import visualization as vis
import functions
import pandas as pd
import seaborn as sns
# TODO those functions are not vis but more analysis utils

import utils
from behavior_analysis_utils import parse_lines
from behavior_analysis_utils import log2Span
from behavior_analysis_utils import parse_trial

"""
matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

plotting with pyqtgraph in qt5 widgets
https://www.learnpyqt.com/courses/graphics-plotting/plotting-pyqtgraph/

"""


"""
session summary view
this would have trial rate
%successful trials vs trial number
number of trial vs time
(this is until now generalizable)

needs
SessionDf
2 kind of parameters:

trial based
shared
trial number
entry time

which kind of trial
opto
requested fixation time


performance parameter 
completed/arborted
such as fixation successful
reward collected
reaction time to reward cue (plt ylim based on percentile)
trial init time
these could almost be seperate dfs or finally use hierarchical indexing

how to turn these into plots in a generelizable way 

generation
on each trial init comput this on the previous trial
"""


"""
other things to code

"trial engagement" (is trial rate?)
reward collected
reaction times
- trial avail to trial init
- reward avail to reward collect

"""

class SessionVis(QtWidgets.QWidget):
    def __init__(self, parent, CodesDf=None):
        super(SessionVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        self.CodesDf = CodesDf
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))
        self.SessionDf = pd.DataFrame(columns=['number','t','successful','reward_collected','rew_col_rt'])
        self.lines = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Session performance monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # self.Line

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow()

        # uncomment for this task
        # think about this: trial rate as a fraction of max trial rate
        # this should show task engagement
        # needs to be put in or as a 
        self.TrialRateItem = self.PlotWindow.addPlot(title='trial rate')
        self.TrialRateItem.setLabel("left",text="trial #")
        self.TrialRateItem.setLabel("bottom",text="time",units="ms")
        self.TrialRateLine = self.TrialRateItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        # self.PlotWindow.nextRow()
        self.PlotWindow.nextColumn()

        self.SuccessRateItem = self.PlotWindow.addPlot(title='success rate')
        self.SuccessRateItem.setLabel("left",text="frac. successful trials")
        self.SuccessRateItem.setLabel("bottom",text="trial #")
        self.SuccessRateLine = self.SuccessRateItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        self.SuccessRateLine20 = self.SuccessRateItem.plot(pen=pg.mkPen(color=(100,200,100),width=2))
        # self.PlotWindow.nextRow()
        self.PlotWindow.nextColumn()

        # make this a general thing for displaying the fraction of incoming binary data
        self.RewardCollectedItem = self.PlotWindow.addPlot(title='reward collection rate')
        self.RewardCollectedItem.setLabel("left",text="frac. collected rewards")
        self.RewardCollectedItem.setLabel("bottom",text="successful trial #")
        self.RewardCollectedLine = self.RewardCollectedItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        self.RewardCollectedLine20 = self.RewardCollectedItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        # self.PlotWindow.nextRow()1
        # self.PlotWindow.nextColumn()

        # reaction times to reward sound cue
        # self.PlotWindow.nextRow()
        # self.RewardRtItem = self.PlotWindow.addPlot(title='reward collection reaction time')
        # self.RewardRtItem.setLabel("left",text="time (ms)")
        # self.RewardRtItem.setLabel("bottom",text="successful trial #")
        # self.RewardRtLine = self.RewardRtItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        
        self.Layout.addWidget(self.PlotWindow)

        self.setLayout(self.Layout)
        self.show()

    def update_plot(self):
        hist = 20 # to be exposed in the future
        # trial rate
        # x = self.SessionDf['t'].values
        # y = self.SessionDf['number'].values
        # self.TrialRateLine.setData(x=x, y=y)
        
        # trial success rate
        x = self.SessionDf['number'].values
        y = [sum(self.SessionDf.iloc[:i]['successful'])/(i+1) for i in range(self.SessionDf.shape[0])]
        self.SuccessRateLine.setData(x=x, y=y)

        y = [sum(self.SessionDf.iloc[i-hist+1:i]['successful'])/hist for i in range(self.SessionDf.shape[0])]
        self.SuccessRateLine20.setData(x=x, y=y)

        # # reward collected rate
        # try:
        #     Df = self.SessionDf.groupby('successful').get_group(True)
        #     x = Df['number'].values
        #     y = [sum(Df.iloc[:i]['reward_collected'])/(i+1) for i in range(Df.shape[0])]
        #     self.SuccessRateLine.setData(x=x, y=y)

        #     y = [sum(Df.iloc[i-hist+1:i]['reward_collected'])/hist for i in range(Df.shape[0])]
        #     self.SuccessRateLine20.setData(x=x, y=y)
        # except KeyError:
        #     pass

        # # reward reaction time
        # try:
        #     Df = self.SessionDf.groupby('successful').get_group(True)
        #     x = Df['number'].values
        #     y = Df['rew_col_rt']
        #     self.RewardRtLine.setData(x=x, y=y)
        # except KeyError:
        #     pass


    def update(self,line):
        # if decodeable
        if not line.startswith('<'):
            code,t = line.split('\t')
            decoded = self.code_map[code]
            t = float(t)

            if decoded == "TRIAL_AVAILABLE_STATE":
                # parse lines
                try:
                    Df = parse_lines(self.lines, code_map=self.code_map)
                    S = parse_trial(Df)
                    if S is not None:
                        S['number'] = self.SessionDf.shape[0]
                        self.SessionDf = self.SessionDf.append(S, ignore_index=True)
                except ValueError:
                    # this is thrown when lines are emtpy
                    pass
                
                # update plot
                self.update_plot()

                # restart lines with current line
                self.lines = []
                self.lines.append(line)
            else:
                self.lines.append(line)


class TrialsVis(QtWidgets.QWidget):
    def __init__(self, parent, CodesDf=None):
        super(TrialsVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # setting up data structures
        # self.Data = pd.DataFrame(columns=['code','t','name'])
        self.lines = []

        # code map related
        self.CodesDf = CodesDf
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Task overview monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="my title")
        self.PlotItem = self.PlotWindow.addPlot(title='trials')
        self.PlotItem.setLabel("left",text="trial #")
        self.PlotItem.setLabel("bottom",text="time", units="ms")
        
        # the names of the things present in the log
        self.span_names = [name.split('_ON')[0] for name in self.CodesDf['name'] if name.endswith('_ON')]
        self.event_names = [name.split('_EVENT')[0] for name in self.CodesDf['name'] if name.endswith('_EVENT')]

        self.trial_counter = 0

        # once code map is defined, colors can be as well
        colors = sns.color_palette('husl',n_colors=len(self.event_names)+len(self.span_names))
        self.cdict = dict(zip(self.event_names+self.span_names,colors))

        # take care of legend
        self.Legend = self.PlotItem.addLegend()
        for k,v in self.cdict.items():
            c = [val*255 for val in v]
            item = pg.PlotDataItem(name=k,pen=pg.mkPen(c))
            self.Legend.addItem(item, k)

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()        

    def update(self,line):
        # if decodeable
        if not line.startswith('<'):
            code,t = line.split('\t')
            decoded = self.code_map[code]
            t = float(t)

            if decoded == "TRIAL_AVAILABLE_STATE":
                try:
                    # parse lines
                    Df = parse_lines(self.lines, code_map=self.code_map)

                    self.trial_counter += 1
                    row_index = self.trial_counter 
                    
                    # plot this Df
                    self.plot_row(Df,row_index)
                except ValueError:
                    # this is thrown when lines are empty
                    pass

                # clear lines
                self.lines = []
                self.lines.append(line)
            else: 
                self.lines.append(line)

    def plot_row(self,Df,row_index):
        # all events
        # make a selector for this
        align_time = Df.loc[Df['name'] == 'TRIAL_ENTRY_EVENT']['t']
        for event_name in self.event_names:
            try:
                df = Df.groupby('name').get_group(event_name+'_EVENT')
                for i,row in df.iterrows():
                    t = row['t'] - align_time
                    rect = pg.QtGui.QGraphicsRectItem(t, row_index , 5, 1)
                    col = [v*255 for v in self.cdict[event_name]]
                    rect.setPen(pg.mkPen(col))
                    rect.setBrush(pg.mkBrush(col))
                    self.PlotItem.addItem(rect)
            except KeyError:
                pass

        for span_name in self.span_names:
            try:
                df = log2Span(Df,span_name)
                for i,row in df.iterrows():
                    t = row['t_on'] - align_time
                    try:
                        col = [v*255 for v in self.cdict[span_name]]
                        if span_name == 'LICK':
                            col.append(150) # reduced opacity
                            rect = pg.QtGui.QGraphicsRectItem(t, row_index+0.05, row['dt'], 0.9)
                        else:
                            rect = pg.QtGui.QGraphicsRectItem(t, row_index, row['dt'], 1)
                        rect = pg.QtGui.QGraphicsRectItem(t, row_index, row['dt'], 1)
                        rect.setPen(pg.mkPen(col))
                        rect.setBrush(pg.mkBrush(col))
                        self.PlotItem.addItem(rect)
                    except TypeError:
                        pass
            except KeyError:
                pass

    # def closeEvent(self, event):
    #     # stub
    #     self.close()
