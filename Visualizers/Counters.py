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
from Widgets.UtilityWidgets import TerminateEdit, StringChoiceWidget, ValueEditFormLayout, ArrayModel, PandasModel
from Utils import utils
from Utils import metrics

"""
 #######  ##     ## ########  ######   #######  ##     ## ########  ######   #######  ##     ## ##    ## ######## ######## ########
##     ## ##     ##    ##    ##    ## ##     ## ###   ### ##       ##    ## ##     ## ##     ## ###   ##    ##    ##       ##     ##
##     ## ##     ##    ##    ##       ##     ## #### #### ##       ##       ##     ## ##     ## ####  ##    ##    ##       ##     ##
##     ## ##     ##    ##    ##       ##     ## ## ### ## ######   ##       ##     ## ##     ## ## ## ##    ##    ######   ########
##     ## ##     ##    ##    ##       ##     ## ##     ## ##       ##       ##     ## ##     ## ##  ####    ##    ##       ##   ##
##     ## ##     ##    ##    ##    ## ##     ## ##     ## ##       ##    ## ##     ## ##     ## ##   ###    ##    ##       ##    ##
 #######   #######     ##     ######   #######  ##     ## ########  ######   #######   #######  ##    ##    ##    ######## ##     ##
"""

class OutcomeCounter(QtWidgets.QWidget):
    """ """
    def __init__(self, parent, outcomes=None, split_by=None):
        super(OutcomeCounter, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.outcomes = outcomes
        self.TableView = QtWidgets.QTableView(self)

        # to be removed hardcodes
        self.outcomes = ['correct','incorrect','missed','premature']
        self.split_by = ['left','right']
        
        # init data
        self.data = np.zeros((len(self.outcomes), len(self.split_by)+2))
        self.row_labels = self.outcomes
        self.col_labels = self.split_by + ['sum','%']

        self.Model = ArrayModel(self.data,  self.row_labels, self.col_labels)
        self.TableView.setModel(self.Model)

        # settings
        self.settings = QtCore.QSettings('TaskControl', 'OutcomeCounter')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

        self.show()

    def init(self):
        self.OnlineDataAnalyser = self.parent().ArduinoController.OnlineDataAnalyser
        self.OnlineDataAnalyser.trial_data_available.connect(self.on_data)
    
    def on_data(self, TrialDf, TrialMetricsDf):
        # side = metrics.get_correct_side(TrialDf).values[0]
        # outcome = metrics.get_outcome(TrialDf).values[0]
        # try:
        #     self.Df.loc[outcome, side] += 1
        #     self.Df['sum'] = self.Df['left'] + self.Df['right']
        #     self.Df['frac'] = self.Df['sum'] / self.Df.sum()['sum']
        # except KeyError:
        #     pass

        # self.model.setDf(self.Df)
        # self.update()
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def reset(self):
        pass

    def closeEvent(self,event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

"""
##      ##    ###    ######## ######## ########
##  ##  ##   ## ##      ##    ##       ##     ##
##  ##  ##  ##   ##     ##    ##       ##     ##
##  ##  ## ##     ##    ##    ######   ########
##  ##  ## #########    ##    ##       ##   ##
##  ##  ## ##     ##    ##    ##       ##    ##
 ###  ###  ##     ##    ##    ######## ##     ##
"""

class WaterCounter(QtWidgets.QWidget):
    """ with a reset button """
    def __init__(self, parent):
        super(WaterCounter, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Layout = QtWidgets.QVBoxLayout(self)
        Row = QtWidgets.QHBoxLayout(self)
        self.Label = QtGui.QLabel("consumed water (µl): ")
        self.Value = QtGui.QLabel("0")
        Row.addWidget(self.Label)
        Row.addWidget(self.Value)
        self.Layout.addLayout(Row)

        self.reward_events = [p.strip() for p in self.parent().task_config['OnlineAnalysis']['reward_event'].split(',')]
        
        # self terminate
        Df = pd.DataFrame([['after (ul) ',  1000,   'int32']],
                           columns=['name','value','dtype'])

        self.Terminator = TerminateEdit(self, DataFrame=Df)
        self.Layout.addWidget(self.Terminator)

        # self terminate button
        self.reset_btn = QtWidgets.QPushButton('reset')
        self.reset_btn.clicked.connect(self.reset)
        self.Layout.addWidget(self.reset_btn, alignment=QtCore.Qt.AlignVCenter)
        self.current_amount = 0
        
        # settings
        self.settings = QtCore.QSettings('TaskControl', 'WaterCounter')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

        self.show()
        self.reset()

    def init(self):
        self.OnlineDataAnalyser = self.parent().ArduinoController.OnlineDataAnalyser
        self.OnlineDataAnalyser.decoded_data_available.connect(self.on_data)

    def start(self):
        pass

    def stop(self):
        pass
    
    def reset(self):
        self.Value.setText("0")

    def increment(self, amount):
        self.current_amount = self.current_amount + amount
        self.Value.setText(str(self.current_amount))
        max_amount = self.Terminator.selfTerminateEdit.get_entry('after (ul) ').value
        
        # check for self terminate
        if self.Terminator.is_enabled:
            if self.current_amount > max_amount:
                self.parent().Done()
    
    def on_data(self, line):
        event, time = line.split('\t')
        if any([event == reward_event for reward_event in self.reward_events]):
            current_magnitude = self.parent().ArduinoController.VariableController.VariableEditWidget.get_entry('reward_magnitude')['value']
            self.increment(current_magnitude)

    def closeEvent(self,event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

"""
######## #### ##     ## ######## ########
   ##     ##  ###   ### ##       ##     ##
   ##     ##  #### #### ##       ##     ##
   ##     ##  ## ### ## ######   ########
   ##     ##  ##     ## ##       ##   ##
   ##     ##  ##     ## ##       ##    ##
   ##    #### ##     ## ######## ##     ##
"""

class Timer(QtWidgets.QWidget):
    """ a clock """
    def __init__(self, parent):
        super(Timer, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Layout = QtWidgets.QVBoxLayout(self)

        # a label
        self.Layout.addWidget(QtWidgets.QLabel("Time in session"))
        
        # display timer
        self.LCDclock = QtWidgets.QLCDNumber()
        self.LCDclock.setDigitCount(8)
        self.LCDclock.display('00:00:00')
        self.LCDclock.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Layout.addWidget(self.LCDclock)

        # self-terminate functionality
        Df = pd.DataFrame([['after (min) ',  45,   'int32']],
                           columns=['name','value','dtype'])
        self.Terminator = TerminateEdit(self, DataFrame=Df)
        self.Layout.addWidget(self.Terminator)

        # call
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.time_handler)

        # settings
        self.settings = QtCore.QSettings('TaskControl', 'Timer')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def init(self):
        pass

    def start(self):
        # start the timer
        self.t_start = datetime.now()
        self.timer.start(1000)
        pass

    def stop(self):
        self.timer.stop()
        pass

    def reset(self):
        self.LCDclock.display('00:00:00')
        pass

    def time_handler(self):
        # called every second by QTimer
        dt = datetime.now() - self.t_start
        self.LCDclock.display(str(dt).split('.')[0])

        # check if self-terminate
        if self.Terminator.is_enabled:
            max_time = self.Terminator.selfTerminateEdit.get_entry('after (min) ')['value']
            current_time = dt.seconds/60
            if current_time >= max_time and max_time > 0:
                self.parent().Done()

    def closeEvent(self,event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

"""
######## ##     ## ######## ##    ## ########  ######   #######  ##     ## ##    ## ######## ######## ########
##       ##     ## ##       ###   ##    ##    ##    ## ##     ## ##     ## ###   ##    ##    ##       ##     ##
##       ##     ## ##       ####  ##    ##    ##       ##     ## ##     ## ####  ##    ##    ##       ##     ##
######   ##     ## ######   ## ## ##    ##    ##       ##     ## ##     ## ## ## ##    ##    ######   ########
##        ##   ##  ##       ##  ####    ##    ##       ##     ## ##     ## ##  ####    ##    ##       ##   ##
##         ## ##   ##       ##   ###    ##    ##    ## ##     ## ##     ## ##   ###    ##    ##       ##    ##
########    ###    ######## ##    ##    ##     ######   #######   #######  ##    ##    ##    ######## ##     ##
"""

class EventCounter(QtWidgets.QScrollArea):
    """ simply counts all arduino events """
    def __init__(self, parent):
        super(EventCounter, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.events = parent.ArduinoController.code_map.values()

        # filter out stuff
        self.events = [event for event in self.events if not event.endswith('_STATE')]
        self.FormLayout = QtWidgets.QFormLayout(self)

        # internal model
        self.model = dict(zip(self.events,np.zeros(len(self.events))))
        
        for i,event in enumerate(self.events):
            self.FormLayout.addRow(event,QtWidgets.QLabel('0'))
        
        for i in range(len(self.events)):
            widget = self.FormLayout.itemAt(i, 1).widget()
            widget.setEnabled(True)

        # contains a scroll area which contains the scroll widget
        self.ScrollWidget = QtWidgets.QWidget(self)

        # note: the order of this seems to be of utmost importance ... 
        self.ScrollWidget.setLayout(self.FormLayout)
        self.setWidget(self.ScrollWidget)
        
        # settings
        self.settings = QtCore.QSettings('TaskControl', 'EventCounter')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()
    
    def on_data(self, line):
        event, time = line.split('\t')
        if event in self.events:
            self.model[event] += 1

            # update
            i = self.events.index(event)
            widget = self.FormLayout.itemAt(i, 1).widget()
            widget.setText(str(self.model[event]))

    def init(self):
        self.OnlineDataAnalyser = self.parent().ArduinoController.OnlineDataAnalyser
        self.OnlineDataAnalyser.decoded_data_available.connect(self.on_data)

    def start(self):
        pass

    def stop(self):
        pass

    def reset(self):
        for k in self.model.keys():
            self.model[k] = 0
        
    def closeEvent(self,event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
