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

# from Widgets.UtilityWidgets import ValueEditFormLayout


"""
 
  ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
 ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
 ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
 ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
  ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ## 
 
"""

""" 
NOTES for the implementation

teensy runs infinitely

upon run, open serial connection

(does this reset the teensy?)

if not reset - then log all the stuff that comes from it to a file, thats all

no code upload, no bidirectional communication necessary

"""

class TimeLogger(QtWidgets.QWidget):
    # initialize signals
    # serial_data_available = QtCore.pyqtSignal(str) # no internal publishing

    # for an explanation how this works and behaves see
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

    # def send(self, command):
    #     """ sends string command interface to arduino, interface compatible """
    #     if hasattr(self, 'connection'):
    #         cmd = '<'+command+'>'
    #         bytestr = str.encode(cmd)
    #         if self.connection.is_open:
    #             self.connection.write(bytestr)
    #     else:
    #         utils.printer("Arduino is not connected", 'error')

    # def send_raw(self, bytestr):
    #     """ sends bytestring """
    #     if hasattr(self, 'connection'):
    #         if self.connection.is_open:
    #             self.connection.write(bytestr)
    #     else:
    #         utils.printer("Arduino is not connected", 'error')

    # def run_btn_clicked(self):
    #     if self.RunBtn.isChecked():
    #         # on startup, poll all vars
    #         # self.VariableController.query()

    #         # after being activated
    #         # self.send('CMD RUN')
    #         # self.RunBtn.setText('HALT')
    #         # self.RunBtn.setStyleSheet("background-color: red")

    #     else: 
    #         self.send('CMD HALT')
    #         self.RunBtn.setText('RUN')
    #         self.RunBtn.setStyleSheet("background-color: green")

    # def send_btn_clicked(self):
    #     """ send command entered in LineEdit """
    #     command = self.SendLine.text()
    #     self.send(command)
        
    # def upload(self):
    #     """ uploads the sketch specified in platformio.ini
    #     which is in turn specified in the task_config.ini """

    #     # uploading code onto arduino

    #     # replace whatever com port is in the platformio.ini with the one from task config
    #     self.pio_config_path = self.task_folder / "Arduino" / "platformio.ini"
    #     pio_config = configparser.ConfigParser()
    #     pio_config.read(self.pio_config_path)

    #     # get upload port
    #     upload_port = self.box_config['connections']['FSM_arduino_port']

    #     for section in pio_config.sections():
    #         if section.split(":")[0] == "env":
    #             pio_config.set(section, "upload_port", upload_port)

    #     # write it
    #     with open(self.pio_config_path, 'w') as fH:
    #         pio_config.write(fH)
        

    #     # upload
    #     utils.printer("uploading code on arduino", 'task')
    #     prev_dir = Path.cwd()

    #     os.chdir(self.task_folder / 'Arduino')
    #     fH = open(self.run_folder / 'platformio_build_log.txt', 'w')
    #     platformio_cmd = self.config['system']['platformio_cmd']
    #     cmd = ' '.join([platformio_cmd, 'run', '--target', 'upload'])
    #     proc = subprocess.Popen(cmd, shell=True, stdout=fH) # ,stderr=fH)
    #     proc.communicate()
    #     fH.close()

    #     os.chdir(prev_dir)

        # restoring original variables

    # def log_task(self, folder):
    #     """ copy the entire arduino folder to the logging folder """
    #     utils.printer("logging arduino code", 'task')
    #     src = self.task_folder
    #     target = folder / self.config['current']['task']
    #     shutil.copytree(src, target)

    def reset_teensy(self, connection):
        """ 
        maybe reset unnecessary as teensy resets upon the connection?
        """

        # https://forum.pjrc.com/threads/60756-How-do-I-software-reset-the-Teensy-3-6#:~:text=Just%20open%20the%20serial%20monitor,when%20Teensy%20comes%20back%20up.&text=goes%20through%20your%20source%20code,replaces%20it%20with%20%22Bob%22.
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
            utils.printer("failed to connect to the teensy time logger", 'error')
            return None

    def Run(self, folder):
        """ folder is the logging folder """
        # the folder that is used for storage
        self.run_folder = folder # needs to be stored for access

        # logging the code
        # self.log_task(self.run_folder)

        # upload
        # if self.reprogramCheckBox.checkState() == 2: # true when checked
        #     self.upload()
        # else:
        #     utils.printer("reusing previously uploaded sketch", 'msg')
            
        # connect to serial port
        self.connection = self.connect()

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
        utils.printer("listening to teensy on serial port %s" % self.box_config['TimeLogger']['com_port'], 'msg')
   
    def stop(self):
        """ halts the FSM """
        # self.send('CMD HALT')
        # self.RunBtn.setText('RUN')
        # self.RunBtn.setStyleSheet("background-color: green")
        pass

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self, 'connection'):
            if self.connection.is_open:
                # self.reset_arduino(self.connection)
                self.connection.close()
        
        # explicit - should fix windows bug where arduino_log.txt is not written
        if hasattr(self, 'log_fH'):
            self.log_fH.close() 

        # self.thread.join()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # take care of the kids
        # for Child in self.Children:
        #     Child.close()
        self.close()


