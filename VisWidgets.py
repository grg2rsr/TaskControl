import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp

import visualization as vis
import functions
import pandas as pd
import seaborn as sns
# TODO those functions are not vis but more analysis utils

import utils


"""
matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

plotting with pyqtgraph in qt5 widgets
https://www.learnpyqt.com/courses/graphics-plotting/plotting-pyqtgraph/

"""


class MyMplCanvas(FigureCanvas):
    # FIXME add controls
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    # def __init__(self, parent, width=7, height=9, dpi=100):
    #     # super(MyMplCanvas, self).__init__(parent=parent)
    #     self.parent=parent

    #     self.lines = []

    #     # figure init
    #     self.fig = Figure(figsize=(width, height), dpi=dpi)
    #     self.axes = self.fig.add_subplot(111)
    #     FigureCanvas.__init__(self, self.fig)
    #     # self.setParent(parent)

    #     FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
    #     FigureCanvas.updateGeometry(self)

    #     self.parent.ArduinoController.Signals.serial_data_available.connect(self.update_data)
    #     self.init()

    #     self.show()

    def __init__(self, parent, width=7, height=9, dpi=100):
        # super(MyMplCanvas, self).__init__(parent=parent)
        self.parent=parent

        self.lines = []

        # figure init
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        # self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.parent.ArduinoController.Signals.serial_data_available.connect(self.update_data)
        self.init()

        self.show()

    def init(self):
        """ can only be called if all is running already """

        pio_folder = self.parent.task_config['Arduino']['pio_project_folder']
        event_codes_fname = self.parent.task_config['Arduino']['event_codes_fname']
        code_map_path = self.parent.ArduinoController.task_folder.joinpath(pio_folder,"src",event_codes_fname)
        self.log_path = self.parent.ArduinoController.run_folder.joinpath('arduino_log.txt')

        self.Code_Map = functions.parse_code_map(code_map_path)
        self.code_dict = dict(zip(self.Code_Map['code'].values, self.Code_Map['name'].values))


    # def init_figure(self):
    #     self.axes.plot(sp.randn(100))
    #     plt.show()
    #     pass

    def update_data(self, line):
        """ connected to new serial data, when any of the trial finishers, update """ 

        # if decodeable
        if not line.startswith('<'):
            code = line.split('\t')[0]
            decoded = self.code_dict[code]
            line = '\t'.join([decoded,line.split('\t')[1]])
            self.lines.append(line)

            if self.code_dict[code] == "TRIAL_COMPLETED_EVENT" or self.code_dict[code] == "TRIAL_ABORTED_EVENT":
                self.update_plot()

    def update_plot(self):
        # make data for plot
        valid_lines = [line.strip().split('\t') for line in self.lines if '\t' in line]
        self.Data = pd.DataFrame(valid_lines,columns=['name','t'])
        self.Data['t'] = self.Data['t'].astype('float')
                                
        # the names of the things present in the log
        span_names = [name.split('_ON')[0] for name in self.Code_Map['name'] if name.endswith('_ON')]
        event_names = [name.split('_EVENT')[0] for name in self.Code_Map['name'] if name.endswith('_EVENT')]

        Spans = vis.log2Spans(self.Data, span_names)
        Events = vis.log2Events(self.Data, event_names)

        # definition of the bounding events
        trial_entry = "TRIAL_ENTRY_EVENT"
        trial_exit_succ = "TRIAL_COMPLETED_EVENT"
        trial_exit_unsucc = "TRIAL_ABORTED_EVENT"

        TrialsDf = vis.make_TrialsDf(self.Data,trial_entry=trial_entry,
                                     trial_exit_succ=trial_exit_succ,
                                     trial_exit_unsucc=trial_exit_unsucc)

        # fig, axes = plt.subplots(figsize=(7,9))

        colors = sns.color_palette('deep',n_colors=len(event_names)+len(span_names))
        cdict = dict(zip(event_names+span_names,colors))

        pre, post = (-1000,1000) # hardcoded

        for i, row in TrialsDf.iterrows():
            if row['outcome'] == 'succ':
                col = 'black'
            else:
                col = 'gray'
            self.axes.plot([0,row['dt']],[i,i],lw=3,color=col)
            self.axes.axhline(i,linestyle=':',color='black',alpha=0.5,lw=1)

            # adding events as ticks
            for event_name, Df in Events.items():
                times = vis.time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t')['t']
                times = times - row['t_on'] # relative to trial onset

                for t in times:
                    self.axes.plot([t,t],[i-0.5,i+0.5],lw=3,color=cdict[event_name])

            # adding spans
            for span_name, Df in Spans.items():
                Df_sliced = vis.time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t_on')
                for j, row_s in Df_sliced.iterrows():
                    t = row_s['t_on'] - row['t_on']
                    dur = row_s['dt']
                    rect = plt.Rectangle((t,i-0.5), dur, 1,
                                        facecolor=cdict[span_name])
                    self.axes.add_patch(rect)

        for key in cdict.keys():
            self.axes.plot([0],[0],color=cdict[key],label=key,lw=4)
        # self.axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
        # self.axes.invert_yaxis()
        self.axes.set_xlabel('time (ms)')
        self.axes.set_ylabel('trials')
        self.fig.tight_layout()
        self.draw()
        