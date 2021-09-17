import sys, os
from pathlib import Path
import configparser
from datetime import datetime
import importlib

import scipy as sp
import numpy as np
import pandas as pd

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
# from ...Widgets.UtilityWidgets import PandasModel

class OutcomeCounter(QtWidgets.QTableView):
    """ """
    def __init__(self, parent, outcomes=None):
        super(OutcomeCounter, self).__init__(parent=parent)
        self.outcomes = outcomes
        self.initModel()
        self.initUI()
        self.model.setDf(self.Df)
        self.update()

    def initModel(self):
        # init data
        self.Df = pd.DataFrame(sp.zeros((4,5),dtype='int32'),columns=['label','left','right','sum','frac'],index=['correct','incorrect','missed','premature'])
        self.Df['frac'] = self.Df['frac'].astype('float32')
        self.Df['label'] = self.Df.index

        self.model = PandasModel(self.Df)
        self.setModel(self.model)
        self.model.setDf(self.Df)

    def initUI(self):
        for i in range(self.Df.columns.shape[0]):
            self.setColumnWidth(i, 40)
        self.update()
        pass

    def connect(self, OnlineDataAnalyser):
        # connect signals
        self.OnlineDataAnalyser = OnlineDataAnalyser
        OnlineDataAnalyser.trial_data_available.connect(self.on_data)
    
    def on_data(self, TrialDf, TrialMetricsDf):
        side = metrics.get_correct_side(TrialDf).values[0]
        outcome = metrics.get_outcome(TrialDf).values[0]
        try:
            self.Df.loc[outcome, side] += 1
            self.Df['sum'] = self.Df['left'] + self.Df['right']
            self.Df['frac'] = self.Df['sum'] / self.Df.sum()['sum']
        except KeyError:
            pass

        self.model.setDf(self.Df)
        self.update()

class WaterCounter(QtWidgets.QWidget):
    """ with a reset button """
    def __init__(self, parent):
        super(WaterCounter, self).__init__(parent=parent)
        self.Layout = QtWidgets.QHBoxLayout()
        self.Labela = QtWidgets.QLabel('consumed water (µl)')
        self.Label = QtWidgets.QLabel()
        self.reset_btn = QtWidgets.QPushButton('reset')
        self.reset_btn.clicked.connect(self.reset)
        self.Layout.addWidget(self.Labela, alignment=QtCore.Qt.AlignVCenter)
        self.Layout.addWidget(self.Label, alignment=QtCore.Qt.AlignVCenter)
        self.Layout.addWidget(self.reset_btn, alignment=QtCore.Qt.AlignVCenter)
        self.setLayout(self.Layout)
        self.reset()
    
    def reset(self):
        self.Label.setText("0")

    def increment(self, amount):
        current_amount = int(float(self.Label.text()))
        new_amount = current_amount + amount
        self.Label.setText(str(new_amount))

    def get_value(self):
        return int(float(self.Label.text())) # FIXME check this
