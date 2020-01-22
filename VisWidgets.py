import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp

import visualization as vis
# TODO those functions are not vis but more analysis utils

import utils

class MyMplCanvas(FigureCanvas):
    # FIXME add controls
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent, width=7, height=9, dpi=100):

        # self.compute_initial_figure()
        #     def compute_initial_figure(self):
        # self.axes.plot(sp.randn(100))
        # plt.show()

        # figure init
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        # self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.parent().ArduinoController.Signals.serial_data_available.connect(self.update)

        self.show()

    def init(self):
        """ can only be called if all is running already """

        pio_folder = self.parent().task_config['Arduino']['pio_project_folder']
        event_codes_fname = self.parent().task_config['Arduino']['event_codes_fname']
        code_map_path = self.parent().ArduinoController.task_folder.joinpath(pio_folder,"src",event_codes_fname)
        self.log_path = self.parent().ArduinoController.run_folder.joinpath('arduino_log.txt')

        self.Code_Map = parse_code_map(code_map_path)

    # def init_figure(self):
    #     self.axes.plot(sp.randn(100))
    #     plt.show()
    #     pass

    def update(self,line):
        """ connected to new serial data, when any of the trial finishers, update """ 

        # if decodeable
        try:
            code = line.split('\t')[0]
            utils.debug_trace() # TODO
            self.Code_Map[]
            self.Data = parse_arduino_log(self.log_path, self.Code_Map) 
            
            # actually check if it is possible to take the lines from here
            
            
            # decoded = self.parent().VariableController.Df.loc[code]['name']
            # decoded = self.parent().StateMachineMonitor.code_map[code]
            # line = '\t'.join([decoded,line.split('\t')[1]])
        except:
            pass
        
        # the names of the things present in the log
        span_names = [name.split('_ON')[0] for name in Code_Map['name'] if name.endswith('_ON')]
        event_names = [name.split('_EVENT')[0] for name in Code_Map['name'] if name.endswith('_EVENT')]
        # state_names = [name.split('_STATE')[0] for name in Code_Map['name'] if name.endswith('_STATE')]

        Spans = vis.log2Spans(self.Data, span_names)
        Events = vis.log2Events(self.Data, event_names)

        # definition of the bounding events
        trial_entry = "FIXATE_STATE"
        trial_exit_succ = "SUCCESSFUL_FIXATION_EVENT"
        trial_exit_unsucc = "BROKEN_FIXATION_EVENT"

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
                times = time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t')['t']
                times = times - row['t_on'] # relative to trial onset

                for t in times:
                    self.axes.plot([t,t],[i-0.5,i+0.5],lw=3,color=cdict[event_name])

            # adding spans
            for span_name, Df in Spans.items():
                Df_sliced = time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t_on')
                for j, row_s in Df_sliced.iterrows():
                    t = row_s['t_on'] - row['t_on']
                    dur = row_s['dt']
                    rect = plt.Rectangle((t,i-0.5), dur, 1,
                                        facecolor=cdict[span_name])
                    self.axes.add_patch(rect)
                
        for key in cdict.keys():
            self.axes.plot([0],[0],color=cdict[key],label=key,lw=4)
        self.axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
        self.axes.invert_yaxis()
        self.axes.set_xlabel('time (ms)')
        self.axes.set_ylabel('trials')
        fig.tight_layout()