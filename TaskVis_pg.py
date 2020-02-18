# import matplotlib
# matplotlib.use('Qt5Agg')
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# import matplotlib.pyplot as plt
# from matplotlib.figure import Figure


from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp
import pyqtgraph as pg

import visualization as vis
import functions
import pandas as pd
import seaborn as sns
# TODO those functions are not vis but more analysis utils

import utils


"""
this needs a full rewrite

into 
__init__()

init_figure()
- takes also care of the deco (hard?)

update_data()
- takes / parses serial data
 

update_figure()
- on all events: draw ev
- on all off: draw from last on to this off

event and span vis


matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

plotting with pyqtgraph in qt5 widgets
https://www.learnpyqt.com/courses/graphics-plotting/plotting-pyqtgraph/

"""


"""
the entire rewrite, again:
goal: a widget where you can select "advance row on" and "align on"
eeeh those are the same???
more about this:
each row starts with a trial init signal (could never really need something else than trials on y)
then, how to plot stuff that is in the future if alignment event has not occured in a given trial?
this will make the past difficult 

one solution: only trigger plot when trial when the next one is active
this solves the entire past stuff as well

pro: elegant coding: could collect all signals between two trial_available signals
and do the alignment etc
less calls to pg.draw() or however its called


con: not real time interactivity plotting
(do we really really need this?) 

then the plot below
keep a counter, each time advance row on is read on serial, increment
on each EVENT, plot a bar
on each _ON record entry (dict last_entires)
on each _OFF, look for previous _ON and plot a box
thats all.

two windows:
session overview (the one described above)
and a 

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
    def __init__(self, parent):
        super(SessionVis, self).__init__(parent=parent, code_map=None)
        self.code_map = code_map
        self.SessionsDf = pd.DataFrame()
        self.lines = []

    def initUI(self):
        pass

    def update(self,line):
         # if decodeable
        if not line.startswith('<'):
            code,t = line.split('\t')
            t = float(t)
        else:
            pass

        if code == "TRIAL_ENTRY_EVENT":
            # parse lines

            # shared:
            number = 
            entry_time = t
            successful = 

            self.SessionsDf = self.SessionsDf.append()






class TaskVis(QtWidgets.QWidget):
    """
    
    """
    def __init__(self, parent):
        super(TaskVis, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # connecting signals
        """ think about whether the children should connect themselves to signals of the parent
        or whether inside the parents the connections should be set
        and call and update(line) method of this object ... 
        pro
        reduces clutter in this plotter
        clutter = weird parent().Signals blabla
        therefore also makes this object more standalone and more portable

        con
        clutter does not need to be reduced really
        this object will ever only live here so it can be hard specified
        portability not really required?

        """
        self.parent().ArduinoController.Signals.serial_data_available.connect(self.on_new_data)

        # setting up data structures
        """ this could be entirely non necessary """
        self.Data = pd.DataFrame(columns=['code','t','name'])

        """ code map should be passed as a constructor parameter ... """
        pio_folder = self.parent().task_config['Arduino']['pio_project_folder']
        event_codes_fname = self.parent().task_config['Arduino']['event_codes_fname']
        code_map_path = self.parent().ArduinoController.task_folder.joinpath(pio_folder,"src",event_codes_fname)
        # self.log_path = self.parent().ArduinoController.run_folder.joinpath('arduino_log.txt')

        # code map related
        self.Code_Map = functions.parse_code_map(code_map_path)
        self.code_dict = dict(zip(self.Code_Map['code'].values, self.Code_Map['name'].values))



        """ these can be moved to init UI, made non self and done ... """
        # the names of the things present in the log
        self.span_names = [name.split('_ON')[0] for name in self.Code_Map['name'] if name.endswith('_ON')]
        self.event_names = [name.split('_EVENT')[0] for name in self.Code_Map['name'] if name.endswith('_EVENT')]

        # once code map is defined, colors can be as well
        colors = sns.color_palette('deep',n_colors=len(self.event_names)+len(self.span_names))
        self.cdict = dict(zip(self.event_names+self.span_names,colors))

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Task overview monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="my title")
        self.current_trial_idx = 0

        self.PlotItem = self.PlotWindow.addPlot(title='trials')
        

        # self.PlotWindow.nextRow()

        # self.LineLR_pp = self.PlotItemLR_pp.plot(x=sp.arange(300), y=self.lc_data[:,1], pen=(200,100,100))

        # also do colors, here

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()        

    def on_new_data(self,line):
        # parse new line and append it to self.Data

        # if decodeable
        if not line.startswith('<'):
            code,t = line.split('\t')
            t = float(t)
        else:
            pass

        decoded = self.code_dict[code]

        if decoded == next_row_event:
            self.current_row += 1

        if decoded.endswith('_EVENT'):
            # easy

        if decoded.endswith('_ON'):
            last_entry[decoded] = t 
        
        if decoded.endswith('_OFF':):
            # add rect from 
            last_entry[decoded],t

            t_on, t_off = prev['t'], self.Data.iloc[-1]['t']
            rect = pg.QtGui.QGraphicsRectItem(t_on, self.current_row ,t_off-t_on,1)

            rect.setPen(pg.mkPen(cdict[span_name]))
            rect.setBrush(pg.mkPen(cdict[span_name]))
            self.PlotWindow.addItem(rect)


            # D = dict(code=code,t=float(t),name=self.code_dict[code])
            # self.Data = self.Data.append(D,ignore_index=True)
            """ there is not really a need for keeping this entire dataframe? """

            # on the beginning of each trial
            # if self.code_dict[code] == "TRIAL_ENTRY":
            #     self.current_trial_entry_time = t
            #     self.current_trial_idx += 1

            # update plot
            # self.update_plot()
        pass

    # def update_plot(self):
        # utils.debug_trace()
        # self.TrialLine = self.PlotItem.plot(x=sp.arange(300), y=[self.current_trial_idx,self.current_trial_idx], pen=(200,200,200))
        # if last line is an event
        if self.Data.iloc[-1]["name"].endswith("_EVENT"):

            # add to plot
            pass

        # if _OFF
        if self.Data.iloc[-1]["name"].endswith("_OFF"):
            # get event name
            span_name = self.Data[-1]["name"].split("_OFF")[0]
            # get the previous on, note that this however performs groupby on the entire data each time
            prev = self.Data.groupby("name").get_group(span_name+"_ON")[-1]
            t_on, t_off = prev['t'], self.Data.iloc[-1]['t']
            rect = pg.QtGui.QGraphicsRectItem(t_on,self.current_trial_idx,t_off-t_on,1)

            rect.setPen(pg.mkPen(cdict[span_name]))
            rect.setBrush(pg.mkPen(cdict[span_name]))
            self.PlotWindow.addItem(rect)


            # State_Logger = get_Logger(log['code'])
            # State_Logger.enter(log['t'],log['x'],log['f'])
            # # make a new rect for the continuous viewer
            # [[xmin, xmax], [ymin, ymax]] = Plot_Cont.viewRange()
            # R = QtGui.QGraphicsRectItem(log['t'],ymin,0,ymax-ymin)
            # if log['code'] != 20: # to take care of super short lick visibility
            #     R.setPen(pg.mkPen(colors[log['code']]))
            # else:
            #     R.setPen(pg.mkPen([0,0,0,0]))
            # R.setBrush(pg.mkBrush(colors[log['code']]))
            # Plot_Cont.addItem(R)
            # Rects_Cont[log['code']] = R
            # Rects_Cont_all.append(R)




        # get last _ON of the same span and plot 
    def closeEvent(self, event):
        # stub
        self.close()
