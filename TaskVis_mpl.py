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
        ax.set_ylim(-0.1,1.1)
        self.success_rate, = ax.plot([],[], lw=1)
        self.success_rate_filt, = ax.plot([],[], lw=1)

        # choice RT
        ax = self.axes[0,1]
        ax.set_title('choice RT')
        self.choices_rt_scatter, = ax.plot([],[],'o')

        # reward collection rate
        ax = self.axes[1,1]
        ax.set_title('reward collection rate')
        ax.set_ylim(-0.1,1.1)
        self.reward_collection_rate, = ax.plot([], [], lw=1)
        self.reward_collection_rate_filt, = ax.plot([], [], lw=1)

        # psychometric
        ax = self.axes[1,0]
        ax.set_title('psychometric')
        ax.set_yticks([0,1])
        ax.set_yticklabels(['short','long'])
        ax.set_ylabel('choice')
        ax.axvline(1500, linestyle=':', alpha=0.5, lw=1, color='k')
        self.psych_choices, = ax.plot([],[], '.', color='k', alpha=0.5)
        self.psych_fit, = ax.plot([],[], lw=2, color='r')

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
            self.axes[0,0].set_xlim(0.5,x.shape[0])


            # choice RT
            if True in SessionDf['has_choice'].values:
                SDf = SessionDf.groupby('has_choice').get_group(True)
                SDf = SDf.reset_index()
                x = SDf.index.values+1
                y = SDf['choice_rt'].values
                self.choices_rt_scatter.set_data(x, y)
                self.choices_rt_scatter.axes.set_xlim(0.5,x.shape[0])

            # reward collection rate
            if True in SessionDf['successful'].values:
                SDf = SessionDf.groupby('successful').get_group(True)
                SDf = SDf.reset_index()
                x = SDf.index.values+1
                y = sp.cumsum(SDf['reward_collected'].values) / (SDf.index.values+1)
                y_filt = SDf['reward_collected'].rolling(hist).mean().values
                self.reward_collection_rate.set_data(x,y)
                self.reward_collection_rate_filt.set_data(x,y_filt)

            # psychmetric
            # get only the subset with choices
            if True in SessionDf['has_choice'].values:
                SDf = SessionDf.groupby('has_choice').get_group(True)
                y = SDf['choice'].values == 'right'
                x = SDf['this_interval'].values
                self.psych_choices.set_data(x,y)

                x_fit = sp.linspace(0,3000,100)
                try:
                    y_fit = bhv.log_reg(x, y, x_fit)
                except ValueError:
                    # thrown when not enough samples for regression
                    y_fit = sp.zeros(x_fit.shape)
                self.psych_fit.set_data(x_fit, y_fit)
            self.axes[1,0].set_xlim(0,3000)
            self.axes[1,0].set_ylim(-0.1,1.1)

        # for ax in self.axes.flatten():
            # ax.autoscale_view()

        self.Canvas.draw()

            # # reward collection rate
            # if True in SessionDf['successful'].values:
            #     SDf = SessionDf.groupby('successful').get_group(True)
            #     x = SDf.index.values+1
            #     y = sp.cumsum(SDf['reward_collected'].values) / (SDf.index.values+1)
            #     y_filt = SDf['reward_collected'].rolling(hist).mean().values
            #     self.RewardCollectedLines[0].setData(x=x,y=y)
            #     self.RewardCollectedLines[1].setData(x=x,y=y_filt)
 
            # # reward collection reaction time
            # if True in SessionDf['reward_collected'].values:
            #     SDf = SessionDf.groupby('reward_collected').get_group(True)
            #     x = SDf.index.values+1
            #     y = SDf['reward_collected_rt'].values
            #     self.RewardRTLine.setData(x=x,y=y)

            # # choice reaction time
            # if True in SessionDf['has_choice'].values:
            #     SDf = SessionDf.groupby('has_choice').get_group(True)
            #     x = SDf.index.values+1
            #     y = SDf['choice_rt'].values
            #     self.ChoiceRTScatter.setData(x=x,y=y)

            # # psychometric
            # if True in SessionDf['has_choice'].values:
            #     SDf = SessionDf[['this_interval','choice']].dropna()
            #     X = SDf['this_interval'].values[:,sp.newaxis]
            #     y = (SDf['choice'].values == 'right').astype('float32')
            #     self.PsychScatter.setData(X.flatten(), y)

            #     try:
            #         cLR = LogisticRegression()
            #         cLR.fit(X,y)

            #         x_fit = sp.linspace(0,3000,100)
            #         psychometric = expit(x_fit * cLR.coef_ + cLR.intercept_).ravel()
            #         self.PsychLine.setData(x=x_fit,y=psychometric)
            #     except:
            #         pass


