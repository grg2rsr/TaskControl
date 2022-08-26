import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import configparser
import importlib
from copy import copy

from pathlib import Path
import subprocess
import shutil
import serial
import time
import threading
import pandas as pd
import scipy as sp
import numpy as np

from Widgets import Widgets
from Utils import utils

""" 
NOTES
bare minimum: more a monitor than a controller
can be converted into a serial logger?
"""

class TimeLogger(QtWidgets.QWidget):
    # initialize signals
    # serial_data_available = QtCore.pyqtSignal(str) # no internal publishing
    # here: https://programmer.group/pyqt5-quick-start-pyqt5-signal-slot-mechanism.html
    # and here: https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect

    def __init__(self, parent, sys_config, task_config, box_config):
        super(TimeLogger, self).__init__(parent=parent)
        self.name = "TimeLogger"
        
        # the original folder of the task
        self.task_folder = Path(sys_config['paths']['tasks_folder']) / sys_config['current']['task']
        self.sys_config = sys_config # this is just the paths
        self.task_config = task_config # this is the section of the task_config.ini ['Arduino']
        self.box_config = box_config # this now holds all the connections
        self.logging = True # TODO expose this via a button
        
        self.initUI()
    
    def initUI(self):
        # the formlayout
        self.setWindowFlags(QtCore.Qt.Window)
        Full_Layout = QtWidgets.QVBoxLayout()

        self.Label = QtWidgets.QLabel()
        self.Label.setText('not connected')
        self.Label.setStyleSheet("background-color: gray")
        self.Label.setAlignment(QtCore.Qt.AlignCenter)
        Full_Layout.addWidget(self.Label)

        self.setLayout(Full_Layout)
        self.setWindowTitle("Teensy")

        # settings
        self.settings = QtCore.QSettings('TaskControl', 'TimeLogger')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def reset(self):
        # TODO implement this?
        # https://forum.pjrc.com/threads/60756-How-do-I-software-reset-the-Teensy-3-6#:~:text=Just%20open%20the%20serial%20monitor,when%20Teensy%20comes%20back%20up.&text=goes%20through%20your%20source%20code,replaces%20it%20with%20%22Bob%22.

        # for arduino:
        # connection.setDTR(False) # reset
        # time.sleep(1) # sleep timeout length to drop all data
        # connection.flushInput()
        # connection.setDTR(True)
        pass
        
    def connect(self):
        """ establish serial connection with the arduino board """
        com_port = self.box_config['TimeLogger']['com_port']
        baud_rate = self.box_config['TimeLogger']['baud_rate']
        try:
            utils.printer("initializing serial port: " + com_port, 'msg')
            # ser = serial.Serial(port=com_port, baudrate=baud_rate, timeout=2)
            connection = serial.Serial(
                port=com_port,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=0,
                rtscts=0
                )

            # self.reset_arduino(connection) # FIXME TODO 
            return connection

        except:
            utils.printer("failed to connect %s on port %s" % (self.name, com_port), 'error')
            return None

    def Run(self, folder):
        """ folder is the logging folder """
        # the folder that is used for storage
        self.run_folder = folder # needs to be stored for access

        # connect to serial port
        self.connection = self.connect()

        # UI stuff
        if self.connection is not None:
            self.Label.setText('connected')
            self.Label.setStyleSheet("background-color: green")

        # external logging
        self.log_fH = open(self.run_folder / 'TimesLog.txt', 'w') # # TODO remove hardcode

        def read_from_port(ser):
            while ser.is_open:
                try:
                    line = ser.readline().decode('utf-8').strip()
                except AttributeError:
                    line = ''
                except TypeError:
                    line = ''
                except serial.serialutil.SerialException:
                    line = ''
                except UnicodeDecodeError:
                    line = ''

                if line != '': # filtering out empty reads
                    if self.logging:
                        self.log_fH.write(line+os.linesep) # external logging

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start()
        utils.printer("listening to %s on port %s" % (self.name, self.box_config['TimeLogger']['com_port'], 'msg'))
   
    def stop(self):
        """  """
        
        pass

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self, 'connection'):
            if self.connection.is_open:
                # self.reset_arduino(self.connection)
                self.connection.close()
        
        # explicitly closing the fileHandle - necessary under windows
        if hasattr(self, 'log_fH'):
            self.log_fH.close() 

        # self.thread.join()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        self.close()


