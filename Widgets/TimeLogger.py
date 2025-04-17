import os
from PyQt5 import QtCore
from PyQt5 import QtWidgets

from pathlib import Path

from Widgets.Connections import SerialConnection, SerialMonitorWidget

import logging

logger = logging.getLogger(__name__)


class TimeLogger(QtWidgets.QWidget):
    def __init__(self, parent, sys_config, task_config, box_config):
        super(TimeLogger, self).__init__(parent=parent)
        self.name = "TimeLogger"  # TODO FIXME give name through .ini

        # the original folder of the task
        self.task_folder = (
            Path(sys_config["paths"]["tasks_folder"]) / sys_config["current"]["task"]
        )
        self.sys_config = sys_config  # this is just the paths
        self.task_config = (
            task_config  # this is the section of the task_config.ini ['Arduino']
        )
        self.box_config = box_config  # this now holds all the connections

        # serial
        com_port = self.box_config[self.name]["com_port"]
        baud_rate = int(self.box_config[self.name]["baud_rate"])
        self.Serial = SerialConnection(self, com_port, baud_rate)
        self.SerialMonitor = SerialMonitorWidget(self, self.Serial)

        self.initUI()

    def initUI(self):
        # the formlayout
        self.setWindowFlags(QtCore.Qt.Window)
        Full_Layout = QtWidgets.QVBoxLayout()

        self.ConnectionLabel = QtWidgets.QLabel()
        self.ConnectionLabel.setText("not connected")
        self.ConnectionLabel.setStyleSheet("background-color: gray")
        self.ConnectionLabel.setAlignment(QtCore.Qt.AlignCenter)
        Full_Layout.addWidget(self.ConnectionLabel)

        self.setLayout(Full_Layout)
        self.setWindowTitle(self.name)

        # settings
        self.settings = QtCore.QSettings("TaskControl", self.name)
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def on_data(self, line):
        """just log it"""
        self.log_fH.write(line + os.linesep)  # external logging

    def Run(self, folder):
        """folder is the logging folder"""

        # connect to serial port
        self.Serial.connect()

        if self.Serial.connection.is_open:
            # UI stuff
            self.ConnectionLabel.setText("connected")
            self.ConnectionLabel.setStyleSheet("background-color: green")

            # external logging
            log_fname = self.task_config["log_fname"]
            self.log_fH = open(folder / log_fname, "w")
            self.Serial.data_available.connect(self.on_data)

            # starts the listener thread
            self.Serial.reset()
            self.Serial.listen()
        else:
            logger.error(
                "trying to listen to %s on port %s - %i, but serial connection is not open"
                % (self.name, self.com_port, self.baud_rate)
            )

    def stop(self):
        """not implemented"""
        pass

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self.Serial, "connection"):
            if self.Serial.connection.is_open:
                self.Serial.disconnect()
                # not even necessary but for completeness
                self.ConnectionLabel.setText("not connected")
                self.ConnectionLabel.setStyleSheet("background-color: gray")

        # explicitly closing the fileHandle - necessary under windows
        if hasattr(self, "log_fH"):
            self.log_fH.close()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # close
        self.SerialMonitor.close()
        self.close()
