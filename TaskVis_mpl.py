import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import matplotlib.pyplot as plt

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp

import pandas as pd
import seaborn as sns
import utils

import behavior_analysis_utils as bhv


"""
matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

https://stackoverflow.com/questions/48140576/matplotlib-toolbar-in-a-pyqt5-application

"""

class SessionVis(QtWidgets.QWidget):
    # FIXME add controls
    """Ultimately, this is a QWidget (as well as a Figureself.CanvasAgg, etc.)."""

    def __init__(self, parent, OnlineDataAnalyser, width=7, height=9, dpi=100):
        super(SessionVis, self).__init__()

        # figure init
        # self.fig = Figure(figsize=(width, height), dpi=dpi)
        # self.fig = Figure()
        self.fig, self.axes = plt.subplots(nrows=2,ncols=2)

        self.Canvas = FigureCanvas(self.fig)
        self.Canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
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
        # success rate
        ax = self.axes[0,0]
        ax.set_title('success rate')
        ax.set_xlabel('trial #')
        ax.set_ylabel('fraction')
        ax.set_ylim(-0.1,1.1)
        self.success_rate, = ax.plot([],[], lw=1)
        self.success_rate_filt, = ax.plot([],[], lw=1)

        # choice RT
        ax = self.axes[0,1]
        ax.set_title('choice RT')
        ax.set_xlabel('choice trial #')
        ax.set_ylabel('RT (ms)')
        
        self.choices_rt_scatter, = ax.plot([],[],'o')

        # reward collection rate
        ax = self.axes[1,1]
        ax.set_title('reward collection rate')
        ax.set_xlabel('successful trial #')
        ax.set_ylabel('fraction')
        ax.set_ylim(-0.1,1.1)
        self.reward_collection_rate, = ax.plot([], [], lw=1)
        self.reward_collection_rate_filt, = ax.plot([], [], lw=1)

        # psychometric
        ax = self.axes[1,0]
        ax.set_title('psychometric')
        # ax.set_ylabel('p')
        ax.set_xlabel('interval (ms)')
        ax.set_yticks([0,1])
        ax.set_yticklabels(['short','long'])
        ax.set_ylabel('choice')
        ax.axvline(1500, linestyle=':', alpha=0.5, lw=1, color='k')
        self.psych_choices, = ax.plot([],[], '.', color='k', alpha=0.5)
        self.psych_fit, = ax.plot([],[], lw=2, color='r')
        self.poly = None # fill for error model

    def on_data(self, TrialDf, TrialMetricsDf):
        hist = 20 # to be exposed in the future
        if  self.OnlineDataAnalyser.SessionDf is not None: # FIXME
            SessionDf = self.OnlineDataAnalyser.SessionDf
            
            # success rate
            x = SessionDf.index.values+1
            y = sp.cumsum(SessionDf['successful'].values) / (SessionDf.index.values+1)
            y_filt = SessionDf['successful'].rolling(hist).mean().values
            
            self.success_rate.set_data(x, y)
            self.success_rate_filt.set_data(x, y_filt)
            self.success_rate.axes.set_xlim(0.5,x.shape[0]+0.5)

            # choice RT
            if True in SessionDf['has_choice'].values:
                SDf = SessionDf.groupby('has_choice').get_group(True)
                SDf = SDf.reset_index()
                x = SDf.index.values+1
                y = SDf['choice_rt'].values
                self.choices_rt_scatter.set_data(x, y)
                self.choices_rt_scatter.axes.set_xlim(0.5,x.shape[0]+0.5)

            # reward collection rate
            if True in SessionDf['successful'].values:
                SDf = SessionDf.groupby('successful').get_group(True)
                SDf = SDf.reset_index()
                x = SDf.index.values+1
                y = sp.cumsum(SDf['reward_collected'].values) / (SDf.index.values+1)
                y_filt = SDf['reward_collected'].rolling(hist).mean().values
                self.reward_collection_rate.set_data(x,y)
                self.reward_collection_rate_filt.set_data(x,y_filt)
                self.reward_collection_rate.axes.set_xlim(0.5,x.shape[0]+0.5)

            # psychmetric
            # get only the subset with choices
            if True in SessionDf['has_choice'].values:
                SDf = SessionDf.groupby('has_choice').get_group(True)
                y = SDf['choice'].values == 'right'
                x = SDf['this_interval'].values

                # choices
                self.psych_choices.set_data(x,y)

                # logistic regression
                x_fit = sp.linspace(0,3000,50)

                try:
                    # y_fit = sp.zeros(x_fit.shape[0])
                    y_fit = bhv.log_reg(x, y, x_fit)
                    self.psych_fit.set_data(x_fit, y_fit)
                except ValueError:
                    pass
                
                try:
                    # error model
                    # if x.shape[0] > 5:
                    #     utils.debug_trace()
                    bias = y.sum() / y.shape[0] # right side bias
                    N = 50
                    R = sp.array([bhv.log_reg(x, sp.rand(x.shape[0]) < bias, x_fit) for i in range(N)])

                    alpha = .05 * 100
                    R_pc = sp.percentile(R, (alpha, 100-alpha), 0)

                    if self.poly is not None:
                        self.poly.remove()

                    self.poly = self.psych_fit.axes.fill_between(x_fit, R_pc[0],R_pc[1],color='black',alpha=0.5)

                except ValueError:
                    pass

                self.psych_choices.axes.set_xlim(0,3000)
                self.psych_choices.axes.set_ylim(-0.1,1.1)

        # for ax in self.axes.flatten():
            # ax.autoscale_view()

        self.Canvas.draw()


