import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import scipy as sp
import numpy as np
import time

import pandas as pd
import seaborn as sns
import utils

import behavior_analysis_utils as bhv


"""
matplotlib in qt5
https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html

https://stackoverflow.com/questions/48140576/matplotlib-toolbar-in-a-pyqt5-application

"""
outcomes = ['correct', 'incorrect', 'premature', 'missed']

colors = dict(success="#72E043", 
              reward="#3CE1FA", 
              correct="#72E043", 
              incorrect="#F56057", 
              premature="#9D5DF0", 
              missed="#F7D379")

class SessionVis(QtWidgets.QWidget):
    # FIXME add controls
    """Ultimately, this is a QWidget (as well as a Figureself.CanvasAgg, etc.)."""

    def __init__(self, parent, OnlineDataAnalyser, width=9, height=8, dpi=100):
        super(SessionVis, self).__init__()

        # figure init
        # self.fig = Figure(figsize=(width, height), dpi=dpi)
        # self.fig = Figure()
        self.fig, self.axes = plt.subplots(nrows=2, ncols=3)

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
        ax = self.axes[0, 0]
        ax.set_title('success / reward collection rates')
        ax.set_xlabel('trial #')
        ax.set_ylabel('fraction')
        ax.set_ylim(-0.1, 1.1)
        self.success_rate, = ax.plot([], [], '.', lw=1, label='success', color=colors['success'])
        self.success_rate_filt, = ax.plot([], [], lw=1, color=colors['success'])
        self.reward_collection_rate, = ax.plot([], [], '.', lw=1, label='rew.coll.', color=colors['reward'])
        self.reward_collection_rate_filt, = ax.plot([], [], lw=1, color=colors['reward'])
        ax.legend(fontsize='x-small')

        # trial outcomes
        ax = self.axes[0, 1]
        ax.set_title('outcomes')
        ax.set_xlabel('trial #')
        ax.set_ylabel('fraction')
        ax.set_ylim(-0.1, 1.1)
        self.outcome_rates = {}
        self.outcome_rates_filt = {}
        for outcome in outcomes:
            self.outcome_rates[outcome], = ax.plot([], [], '.', lw=1, color=colors[outcome], label=outcome)
            self.outcome_rates_filt[outcome], = ax.plot([], [], lw=1, color=colors[outcome])
        ax.legend(fontsize='x-small')

        # trial outcomes
        self.outcome_ax = self.axes[1, 0]
        ax.set_title('outcomes')
        ax.set_xlabel('trial #')
        ax.set_ylim(-0.1, 1.1)
        # self.outcome_rates = {}
        # self.outcome_rates_filt = {}
        # for outcome in outcomes:
            # self.outcome_rates[outcome], = ax.plot([], [], '.', lw=1, color=colors[outcome], label=outcome)
            # self.outcome_rates_filt[outcome], = ax.plot([], [], lw=1, color=colors[outcome])
        # ax.legend(fontsize='x-small')


        # choices and bias
        ax = self.axes[0, 2]
        ax.set_title('choices')
        ax.set_xlabel('trial #')
        ax.set_ylabel('fraction')
        ax.set_ylim(-0.2, 1.2)
        self.bias, = ax.plot([], [], '.', lw=1, label='bias', color='k')
        self.bias_filt, = ax.plot([], [], lw=1, color='k')
        cmap = mpl.cm.PiYG
        self.trials_left, = ax.plot([], [], 'o', color='k')
        self.trials_right, = ax.plot([], [], 'o', color='k')
        self.choices_left, = ax.plot([], [], 'o', color=cmap(1.0))
        self.choices_right, = ax.plot([], [], 'o', color=cmap(0.0))
        ax.legend(fontsize='x-small')
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['right', 'left'])
        ax.set_ylabel('choice')

        # choice RT
        ax = self.axes[1, 1]
        ax.set_title('choice RT')
        ax.set_xlabel('choice trial #')
        ax.set_ylabel('RT (ms)')
        self.choices_rt_scatter, = ax.plot([], [], 'o')
        ax.set_ylim(0, 1500)

        # psychometric
        ax = self.axes[1, 2]
        ax.set_title('psychometric')
        # ax.set_ylabel('p')
        ax.set_xlabel('interval (ms)')
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['short', 'long'])
        ax.set_ylabel('choice')
        ax.axvline(1500, linestyle=':', alpha=0.5, lw=1, color='k')
        self.psych_choices, = ax.plot([], [], '.', color='k', alpha=0.5)
        self.psych_fit, = ax.plot([], [], lw=2, color='r')
        self.poly = None # fill for error model

        self.fig.tight_layout()

    def on_data(self, TrialDf, TrialMetricsDf):
        t1 = time.time()
        hist = 5 # to be exposed in the future
        if  self.OnlineDataAnalyser.SessionDf is not None: # FIXME
            SessionDf = self.OnlineDataAnalyser.SessionDf
            
            # success rate
            x = SessionDf.index.values+1
            y = np.cumsum(SessionDf['successful'].values) / (SessionDf.index.values+1)
            y_filt = SessionDf['successful'].rolling(hist).mean().values
            
            self.success_rate.set_data(x, y)
            self.success_rate_filt.set_data(x, y_filt)
            self.success_rate.axes.set_xlim(0.5, x.shape[0]+0.5)

            # reward collection rate
            if True in SessionDf['successful'].values:
                SDf = SessionDf.groupby(['successful', 'reward_omitted']).get_group((True,False))
                SDf = SDf.reset_index()
                x = SDf.index.values+1
                y = np.cumsum(SDf['reward_collected'].values) / (SDf.index.values+1)
                y_filt = SDf['reward_collected'].rolling(hist).mean().values
                self.reward_collection_rate.set_data(x, y)
                self.reward_collection_rate_filt.set_data(x, y_filt)
                self.reward_collection_rate.axes.set_xlim(0.5, x.shape[0]+0.5)

            # outcomes
            for outcome in outcomes:
                try:
                    SDf = SessionDf.groupby('outcome').get_group(outcome)
                    SDf.reset_index()
                except:
                    continue

                x = SDf.index.values+1
                y = np.cumsum((SDf['outcome'] == outcome).values) / (SDf.index.values+1)
                # y_filt = (SessionDf['outcome'] == outcome).rolling(hist).mean().values
                self.outcome_rates[outcome].set_data(x, y)
                # self.outcome_rates_filt[outcome].set_data(x, y_filt)
                self.outcome_rates[outcome].axes.set_xlim(0.5, SessionDf.shape[0]+0.5)

            # Create a Rectangle patch
            try:
                x = SessionDf.index[-1] + 1
                y = 0
                outcome = SessionDf.iloc[-1]['outcome']
                rect = patches.Rectangle((x,y),1,1, edgecolor='none', facecolor=colors[outcome])
                self.outcome_ax.add_patch(rect)
                self.outcome_ax.set_xlim(0.5, SessionDf.shape[0]+0.5)
            except:
                pass


            # choices
            x = SessionDf.loc[SessionDf['correct_zone'] == 4].index + 1
            y = np.zeros(x.shape[0]) - 0.1
            self.trials_left.set_data(x,y)
            x = SessionDf.loc[SessionDf['correct_zone'] == 6].index + 1
            y = np.zeros(x.shape[0]) + 1.1
            self.trials_right.set_data(x,y)

            try:
                SDf = SessionDf.groupby('choice').get_group('left')
                x = SDf.index.values+1
                y = np.zeros(x.shape[0])
                self.choices_left.set_data(x,y)
            except:
                pass

            try:
                SDf = SessionDf.groupby('choice').get_group('right')
                x = SDf.index.values+1
                y = np.zeros(x.shape[0]) + 1
                self.choices_right.set_data(x,y)
            except:
                pass

            x = SessionDf.index
            y = SessionDf['bias'].values
            self.bias.set_data(x,y)
            # y_filt = SDf['bias'].rolling(hist).mean().values
            # self.bias_filt.set_data(x, y_filt)
            self.bias.axes.set_xlim(0.5, SessionDf.shape[0]+0.5)

            # if True in SessionDf['has_choice'].values:
            #     try:
            #         SDf = SessionDf.groupby('choice').get_group('left')
            #         SDf.reset_index()
            #         x = SDf.index.values+1
            #         y = np.zeros(x.shape[0])
            #         self.choices_right.set_data(x,y)
            #     except:
            #         pass
            #     try:
            #         SDf = SessionDf.groupby('choice').get_group('right')
            #         SDf.reset_index()
            #         x = SDf.index.values+1
            #         y = np.ones(x.shape[0])
            #         self.choices_left.set_data(x,y)
            #     except:
            #         pass



            # choice RT
            if True in SessionDf['has_choice'].values:
                SDf = SessionDf.groupby('has_choice').get_group(True)
                SDf = SDf.reset_index()
                x = SDf.index.values+1
                y = SDf['choice_rt'].values
                self.choices_rt_scatter.set_data(x, y)
                self.choices_rt_scatter.axes.set_xlim(0.5, x.shape[0]+0.5)
                # self.choices_rt_scatter.axes.set_ylim(0, sp.percentile(y, 95))

            # psychmetric
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

        # for ax in self.axes.flatten():
            # ax.autoscale_view()
        self.Canvas.draw()
        # try:
        #     self.Canvas.draw()
        # except ValueError:
        #     print("error while drawing")
        #     pass

        # print("time for update: ", t2-t1)


