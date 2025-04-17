from datetime import datetime

import numpy as np
import pandas as pd

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from Widgets.UtilityWidgets import TerminateEdit, ArrayModel
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

    def __init__(self, parent, online_config, outcomes=None, split_by=None):
        super(OutcomeCounter, self).__init__(parent=parent)
        self.name = "OutcomeCounter"
        self.setWindowFlags(QtCore.Qt.Window)
        self.TableView = QtWidgets.QTableView(self)
        self.Layout = QtWidgets.QVBoxLayout(self)
        self.Layout.addWidget(QtWidgets.QLabel("Outcome Counter"))
        self.Layout.addWidget(self.TableView)

        # to be removed hardcodes
        self.outcomes = outcomes
        self.outcomes = ["correct", "incorrect", "missed", "premature"]
        self.split_by = ["left", "right"]

        # init data
        self.data = np.zeros(
            (len(self.outcomes), len(self.split_by) + 3), dtype="object"
        )
        self.row_labels = self.outcomes
        self.col_labels = [""] + self.split_by + ["∑", "%"]

        self.Model = ArrayModel(self.data, self.row_labels, self.col_labels)
        self.TableView.setModel(self.Model)

        # putting text
        self.data[:, 0] = self.row_labels
        self.TableView.setColumnWidth(1, 100)
        for i in range(1, len(self.col_labels)):
            self.TableView.setColumnWidth(i, 50)

        # settings
        self.settings = QtCore.QSettings("TaskControl", "OutcomeCounter")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

        self.show()

    def init(self):
        self.parent().ArduinoController.OnlineFSMAnalyzer.trial_data_available.connect(
            self.on_data
        )
        # self.OnlineDataAnalyser = self.parent().ArduinoController.OnlineDataAnalyser
        # self.OnlineDataAnalyser.trial_data_available.connect(self.on_data)

    def on_data(self, TrialDf, TrialMetricsDf):
        side = metrics.get_correct_side(TrialDf).values[0]
        outcome = metrics.get_outcome(TrialDf).values[0]
        if not (pd.isna(side) or pd.isna(outcome)):
            i = self.row_labels.index(outcome)
            j = self.col_labels.index(side)

            # update internal data
            self.data[i, j] += 1
            self.data[i, 3] = np.sum(self.data[i, 1:3])
            self.data[i, 4] = np.sum(self.data[i, 1:3]) / np.sum(self.data[:, 1:3])

            # update model
            self.Model.update()

    def start(self):
        pass

    def stop(self):
        pass

    def reset(self):
        pass

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
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
    """ """

    def __init__(self, parent, online_config):
        super(WaterCounter, self).__init__(parent=parent)
        self.name = "WaterCounter"
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(self.name)
        self.Layout = QtWidgets.QVBoxLayout(self)

        # internal value and display
        self.current_amount = 0
        self.Value = QtWidgets.QLabel(str(self.current_amount))
        self.Label = QtWidgets.QLabel("consumed water (µl): ")

        Row = QtWidgets.QHBoxLayout()
        Row.addWidget(self.Label)
        Row.addWidget(self.Value)
        self.Layout.addLayout(Row)

        self.reward_events = [
            p.strip() for p in online_config["reward_event"].split(",")
        ]

        # self terminate
        Df = pd.DataFrame(
            [["after (ul) ", 1000, "int32"]], columns=["name", "value", "dtype"]
        )

        self.Terminator = TerminateEdit(self, DataFrame=Df)
        self.Layout.addWidget(self.Terminator)

        # self terminate button
        self.reset_btn = QtWidgets.QPushButton("reset")
        self.reset_btn.clicked.connect(self.reset)
        self.Layout.addWidget(self.reset_btn, alignment=QtCore.Qt.AlignVCenter)

        # settings
        self.settings = QtCore.QSettings("TaskControl", "WaterCounter")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

        self.show()
        self.reset()

    def init(self):
        self.parent().ArduinoController.FSMDecoder.decoded_data_available.connect(
            self.on_data
        )

    def start(self):
        pass

    def stop(self):
        pass

    def reset(self):
        self.current_amount = 0
        self.Value.setText(str(self.current_amount))

    def increment(self, amount):
        self.current_amount = self.current_amount + amount
        self.Value.setText(str(self.current_amount))
        max_amount = self.Terminator.selfTerminateEdit.get_entry("after (ul) ").value

        # check for self terminate
        if self.Terminator.is_enabled:
            if self.current_amount > max_amount:
                self.parent().Done()

    def on_data(self, line):
        event, time = line.split("\t")
        if any([event == reward_event for reward_event in self.reward_events]):
            current_magnitude = self.parent().ArduinoController.VariableController.VariableEditWidget.get_entry(
                "reward_magnitude"
            )["value"]
            self.increment(current_magnitude)

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
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
    """a clock"""

    def __init__(self, parent, online_config):
        super(Timer, self).__init__(parent=parent)
        self.name = "Timer"
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(self.name)
        self.Layout = QtWidgets.QVBoxLayout(self)

        # a label
        self.Layout.addWidget(QtWidgets.QLabel("Time in session"))

        # display timer
        self.LCDclock = QtWidgets.QLCDNumber()
        self.LCDclock.setDigitCount(8)
        self.LCDclock.display("00:00:00")
        self.LCDclock.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.Layout.addWidget(self.LCDclock)

        # self-terminate functionality
        Df = pd.DataFrame(
            [["after (min) ", 90, "int32"]], columns=["name", "value", "dtype"]
        )
        self.Terminator = TerminateEdit(self, DataFrame=Df)
        self.Layout.addWidget(self.Terminator)

        # call
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.time_handler)

        # settings
        self.settings = QtCore.QSettings("TaskControl", "Timer")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def init(self):
        pass

    def start(self):
        # start the timer
        self.t_start = datetime.now()
        self.timer.start(1000)

    def stop(self):
        self.timer.stop()

    def reset(self):
        self.t_start = datetime.now()  # possibly necessary?
        self.LCDclock.display("00:00:00")

    def time_handler(self):
        # called every second by QTimer
        dt = datetime.now() - self.t_start
        time_str = str(dt).split(".")[0]
        if len(time_str.split(":")[0]) == 1:
            time_str = "0" + time_str
        self.LCDclock.display(time_str)

        # check if self-terminate
        if self.Terminator.is_enabled:
            max_time = self.Terminator.selfTerminateEdit.get_entry("after (min) ")[
                "value"
            ]
            current_time = dt.seconds / 60
            if current_time >= max_time and max_time > 0:
                self.parent().Done()

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
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
    """simply counts all arduino events"""

    def __init__(self, parent, online_config):
        super(EventCounter, self).__init__(parent=parent)
        self.name = "EventCounter"
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(self.name)
        self.events = parent.ArduinoController.code_map.values()

        # filter out stuff
        self.events = [event for event in self.events if not event.endswith("_STATE")]
        self.FormLayout = QtWidgets.QFormLayout(self)

        # internal model
        self.Model = dict(zip(self.events, np.zeros(len(self.events), dtype="int32")))

        for i, event in enumerate(self.events):
            self.FormLayout.addRow(event, QtWidgets.QLabel("%5i" % 0))

        for i in range(len(self.events)):
            widget = self.FormLayout.itemAt(i, 1).widget()
            widget.setEnabled(True)

        # contains a scroll area which contains the scroll widget
        self.ScrollWidget = QtWidgets.QWidget(self)

        # note: the order of this seems to be of utmost importance ...
        self.ScrollWidget.setLayout(self.FormLayout)
        self.setWidget(self.ScrollWidget)

        # settings
        self.settings = QtCore.QSettings("TaskControl", "EventCounter")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def on_data(self, line):
        event, time = line.split("\t")
        if event in self.events:
            self.Model[event] += 1

            # update
            i = self.events.index(event)
            widget = self.FormLayout.itemAt(i, 1).widget()
            widget.setText("%5i" % self.Model[event])

    def init(self):
        self.parent().ArduinoController.FSMDecoder.decoded_data_available.connect(
            self.on_data
        )

    def start(self):
        pass

    def stop(self):
        pass

    def reset(self):
        for k in self.Model.keys():
            self.Model[k] = 0

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
