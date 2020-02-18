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


class SessionVis(QtWidgets.QWidget):
    def __init__(self, parent, Code_Map=None):
        super(SessionVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        self.Code_Map = Code_Map
        # should be
        # utils.debug_trace()
        # Code_Map.index = Code_Map['code']
        # Code_Map['name'].to_dict()
        self.code_dict = dict(zip(self.Code_Map['code'].values, self.Code_Map['name'].values))
        self.SessionDf = pd.DataFrame(columns=['number','t','successful'])
        self.lines = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Session performance monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="my title")
        self.current_trial_idx = 0

        self.TrialRateItem = self.PlotWindow.addPlot(title='trial rate')
        self.TrialRateLine = self.TrialRateItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        self.PlotWindow.nextColumn()
        self.SuccessRateItem = self.PlotWindow.addPlot(title='success rate')
        self.SuccessRateLine = self.SuccessRateItem.plot(pen=pg.mkPen(color=(200,100,100),width=2))
        self.SuccessRateLine20 = self.SuccessRateItem.plot(pen=pg.mkPen(color=(100,200,100),width=2))

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()

    def update_plot(self):
        # trial rate
        x = self.SessionDf['t'].values
        y = self.SessionDf['number'].values
        self.TrialRateLine.setData(x=x, y=y)
        
        # trial success rate
        x = self.SessionDf['number'].values
        y = [sum(self.SessionDf.loc[:i,'successful'])/(i+1) for i in range(self.SessionDf.shape[0])]
        self.SuccessRateLine.setData(x=x, y=y)

        y = [sum(self.SessionDf.loc[i-20+1:i,'successful'])/20 for i in range(self.SessionDf.shape[0])]
        self.SuccessRateLine20.setData(x=x, y=y)

    def update(self,line):
         # if decodeable
        if not line.startswith('<'):
            self.lines.append(line)
            code,t = line.split('\t')
            decoded = self.code_dict[code]
            t = float(t)

            if decoded == "TRIAL_ENTRY_EVENT":
                # parse lines
                Df = parse_lines(self.lines, code_map=self.Code_Map)

                # update SessionDf
                if "TRIAL_COMPLETED_EVENT" in Df['name'].values:
                    succ = True
                else:
                    succ = False

                D = dict(number=self.SessionDf.shape[0] + 1,
                        t=t,
                        successful=succ)
                self.SessionDf = self.SessionDf.append(D, ignore_index=True)
                
                # clear lines
                self.lines = []

                # update plot
                self.update_plot()


class TrialsVis(QtWidgets.QWidget):
    def __init__(self, parent, Code_Map=None):
        super(TrialsVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # setting up data structures
        # self.Data = pd.DataFrame(columns=['code','t','name'])
        self.lines = []

        # code map related
        self.Code_Map = Code_Map
        self.code_dict = dict(zip(self.Code_Map['code'].values, self.Code_Map['name'].values))

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Task overview monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        # self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="my title")
        self.PlotItem = self.PlotWindow.addPlot(title='trials')
        
        # the names of the things present in the log
        self.span_names = [name.split('_ON')[0] for name in self.Code_Map['name'] if name.endswith('_ON')]
        self.event_names = [name.split('_EVENT')[0] for name in self.Code_Map['name'] if name.endswith('_EVENT')]

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
            decoded = self.code_dict[code]
            t = float(t)

            if decoded == "TRIAL_ENTRY_EVENT":
                # parse lines
                Df = parse_lines(self.lines, code_map=self.Code_Map)

                self.trial_counter += 1
                row_index = self.trial_counter 
                
                # plot this Df
                self.plot_row(Df,row_index)

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
                    rect = pg.QtGui.QGraphicsRectItem(t, row_index , 10, 1)
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
                        rect = pg.QtGui.QGraphicsRectItem(t, row_index, row['dt'], 1)
                        col = [v*255 for v in self.cdict[span_name]]
                        if span_name == 'LICK':
                            col.append(150) # reduced opacity
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
