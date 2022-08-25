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
from scripts import interface_generator
from Utils import behavior_analysis_utils as bhv

from Widgets.UtilityWidgets import ValueEditFormLayout


"""
 
  ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
 ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
 ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
 ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
  ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ## 
 
"""

class ArduinoController(QtWidgets.QWidget):
    def __init__(self, name, parent, config, task_config, box):
        """ 
        parent is the parent
        config is the main config for the computer that runs the task
        task_config is the section of the task_config.ini -> specific to this controller
        box is box that is being used
        """
        
        # regarding the parent issue
        # see here https://stackoverflow.com/questions/30354166/what-is-parent-for-in-qt


        super(ArduinoController, self).__init__(parent=parent)
        self.name = name
        self.com_port = box['com_port']
        self.baud_rate = box['baud_rate']
        self.box = box
    
    def initUI(self):
        # reupload sketch
        self.setWindowFlags(QtCore.Qt.Window)
        self.FormLayout = QtWidgets.QFormLayout()
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # reprogram
        self.reprogramCheckBox = QtWidgets.QCheckBox("reupload sketch")
        self.reprogramCheckBox.setChecked(True)
        self.FormLayout.addRow(self.reprogramCheckBox)

        FormWidget = QtWidgets.QWidget()
        FormWidget.setLayout(self.FormLayout)

        self.Full_Layout = QtWidgets.QVBoxLayout() # subclasses add their things to this
        self.Full_Layout.addWidget(FormWidget)

        self.setLayout(self.Full_Layout)
        self.setWindowTitle(self.name) # FIXME change to self.name?

        # settings
        self.settings = QtCore.QSettings('TaskControl', 'ArduinoController') # FIXME not sure how to handle this - TODO try self.name
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()
        pass

    def upload(self, run_folder=None):
        """ run_folder specifies the folder where a) all the files are written for the 
        upload, and b) all data is being logged """

        # update platformio.ini with the correct com port from the box config
        task_folder = Path(self.config['paths']['tasks_folder']) / self.config['current']['task']
        self.pio_config_path = task_folder / self.name / "platformio.ini"
        pio_config = configparser.ConfigParser()
        pio_config.read(self.pio_config_path)
        for section in pio_config.sections():
            if section.split(":")[0] == "env":
                pio_config.set(section, "upload_port", self.box[self.name]['com_port'])

        # write it
        with open(self.pio_config_path, 'w') as fH:
            pio_config.write(fH)

        # upload
        utils.printer(self.name + " :uploading code", 'task')
        prev_dir = Path.cwd()

        os.chdir(task_folder / self.name)
        if run_folder is not None:
            fH = open(run_folder / 'platformio_build_log.txt', 'w')
        else:
            fH = None
        platformio_cmd = self.config['system']['platformio_cmd']
        cmd = ' '.join([platformio_cmd, 'run', '--target', 'upload'])
        proc = subprocess.Popen(cmd, shell=True, stdout=fH) # ,stderr=fH)
        proc.communicate()
        fH.close()

        os.chdir(prev_dir)

        utils.printer("done uploading", 'msg', self)

    def connect(self):
        """ establish serial connection """
        com_port = self.box[self.name]['com_port']
        baud_rate = self.box[self.name]['baud_rate']
        try:
            utils.printer("initializing serial port: " + com_port, 'message', self)
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

            self.reset_arduino()
            return connection

        except:
            utils.printer("failed to connect!", 'error', self)
            sys.exit()

    def reset_arduino(self):
        """ taken from https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial """
        self.connection.setDTR(False) # reset
        time.sleep(1) # sleep timeout length to drop all data
        self.connection.flushInput()
        self.connection.setDTR(True)

    def disconnect(self):
        pass

    def run(self, run_folder): # this requires run_folder to be propagated upon clicking the button! but makes sense
        # upload
        if self.reprogramCheckBox.checkState() == 2: # true when checked
            self.upload(run_folder)
        else:
            utils.printer("reusing previously uploaded sketch", 'msg', self)
            
        # connect to serial port
        self.connection = self.connect()

        def read_from_port(ser):
            while ser.is_open:
                # FIXME those are more specific for the FSM I belive?
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

                if line is not '': # filtering out empty reads
                    self.serial_data_available.emit(line) # publishing

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start()
        # FIXME
        # utils.printer("FIXME %s" % self.box['connections']['FSM_arduino_port'], 'msg')
        utils.printer("running",'msg', self)

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self, 'connection'):
            if self.connection.is_open:
                self.reset_arduino(self.connection)
                self.connection.close()
            # self.SerialMonitor.close()
        # self.VariableController.close()
        
        # explicit - should fix windows bug where arduino_log.txt is not written
        # if hasattr(self, 'arduino_log_fH'):
        #     self.arduino_log_fH.close() 

        # self.thread.join()

        # overwrite logged arduino vars file
        # if hasattr(self, 'run_folder'):
        #     target = self.run_folder / self.config['current']['task']  / 'Arduino' / 'src' / 'interface_variables.h'
        #     if target.exists(): # bc close event is also triggered on task_changed
        #         self.VariableController.write_variables(target)

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # take care of the kids
        for Child in self.Children:
            Child.close()
        self.close()



class FSMController(ArduinoController):
    """ controls an arduino that runs the specific FSM """
    def __init__(self):
        super(FSMController, self).__init__(parent=parent)

    def initUI(self):
        """ run / halt buttons """
        pass

    def uplad(self, run_folder):
        # building interface
        utils.printer("generating interface.cpp", 'task', self)
        
        try: # catch this exception for downward compatibility
            utils.printer("generating interface from: %s" % self.vars_path, 'msg')
            utils.printer("using as template: %s" % self.task_config['interface_template_fname'], 'msg')
            interface_template_fname = self.task_config['interface_template_fname']
            interface_generator.run(self.vars_path, interface_template_fname)
        except KeyError:
            utils.printer("generating interface based on %s" % self.vars_path, 'msg')
            interface_generator.run(self.vars_path)

        super(FSMController, self).run()

    def run(self, run_folder):

        super(FSMController, self).run()
    
    def send(self):
        pass

    def send_raw(self):
        pass






class SerialMonitor(QtWidgets.QWidget):
    # just a window that puts everything that comes
    # from a serial connection onto it
    pass

class FSMSerialMonitor(SerialMonitor):
    # implements decoding functionality if event code map is passed
    pass

class ArduinoController(QtWidgets.QWidget):
    # initialize signals
    serial_data_available = QtCore.pyqtSignal(str)

    # for an explanation how this works and behaves see
    # here: https://programmer.group/pyqt5-quick-start-pyqt5-signal-slot-mechanism.html
    # and here: https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect

    def __init__(self, parent, config, task_config, box):
        super(ArduinoController, self).__init__(parent=parent)
        self.name = "ArduinoController"
        
        # the original folder of the task
        self.task_folder = Path(config['paths']['tasks_folder']) / config['current']['task']
        self.config = config # this is just the paths
        self.task_config = task_config # this is the section of the task_config.ini ['Arduino']
        self.box = box # this now holds all the connections

        self.Children = []

        # VariableController
        # self.vars_path = self.task_folder / 'Arduino' / 'src' / "interface_variables.h"

        # Df = utils.parse_arduino_vars(self.vars_path) # initialize with the default variables
        # self.VariableController = ArduinoVariablesWidget(self)
        # self.Children.append(self.VariableController)

        # events_path = self.task_folder / 'Arduino' / 'src' / 'event_codes.h'
        # CodesDf = utils.parse_code_map(events_path)
        # self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        # set up online data analyzer if defined in task_config
        # if 'OnlineAnalysis' in dict(self.parent().task_config).keys():
        #     online_config = self.parent().task_config['OnlineAnalysis']
        #     self.OnlineDataAnalyser = OnlineDataAnalyser(self, CodesDf, config=online_config)
            
        # open serial monitor
        # self.SerialMonitor = SerialMonitorWidget(self, code_map=self.code_map)
        # self.Children.append(self.SerialMonitor)

        # Statemachine Monitor
        # self.StateMachineMonitor = StateMachineMonitorWidget(self, code_map=self.code_map)
        # self.Children.append(self.StateMachineMonitor)
        
        self.initUI()
    
    def initUI(self):
        # the formlayout
        

        # start/stop button
        # self.RunBtn = QtWidgets.QPushButton()
        # self.RunBtn.setStyleSheet("background-color: green")
        # self.RunBtn.setCheckable(True)
        # self.RunBtn.setText('Run')
        # self.RunBtn.clicked.connect(self.run_btn_clicked)
        # Full_Layout.addWidget(self.RunBtn)

        # direct interaction
        # self.SendLine = QtWidgets.QLineEdit()
        # SendBtn = QtWidgets.QPushButton()
        # SendBtn.setText('Send')
        # SendBtn.clicked.connect(self.send_btn_clicked)
        # Layout = QtWidgets.QHBoxLayout()
        # Layout.addWidget(self.SendLine)
        # Layout.addWidget(SendBtn)
        # Full_Layout.addLayout(Layout)

        # keyboard interaction
        # Label = QtWidgets.QLabel('focus here to capture single keystrokes')
        # Full_Layout.addWidget(Label)



    # def keyPressEvent(self, event):
    #     """ reimplementation to send single keystrokes """
    #     self.send("CMD " + event.text())

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
    #         self.send('CMD RUN')
    #         self.RunBtn.setText('HALT')
    #         self.RunBtn.setStyleSheet("background-color: red")

    #     else: 
    #         self.send('CMD HALT')
    #         self.RunBtn.setText('RUN')
    #         self.RunBtn.setStyleSheet("background-color: green")

    # def send_btn_clicked(self):
    #     """ send command entered in LineEdit """
    #     command = self.SendLine.text()
    #     self.send(command)
        
    def upload(self):
        """ uploads the sketch specified in platformio.ini
        which is in turn specified in the task_config.ini """

        

        # uploading code onto arduino

        
        
        # get current UI arduino variables, backup defaults,
        # write the UI derived and upload those, revert after upload
        # this workaround is necessary to use the get previous variables
        # functionality ... 

        # backing up original values
        # shutil.copy(self.vars_path, self.vars_path.with_suffix('.default'))

        # setting the valve calibration factor
        # utils.printer("setting valve calibration factors", 'task')
        # if 'valves' in self.box.sections():
        #     valves = dict(self.box['valves']).keys()
        #     for valve in valves:
        #         try:
        #             utils.printer('setting calibration factor of valve: %s = %s' % (valve, self.box['valves'][valve]), 'msg')
        #             self.VariableController.VariableEditWidget.set_entry(valve, self.box['valves'][valve])
        #         except:
        #             utils.printer("can't set valve calibration factors of valve %s" % valve, 'error')
        # else:
        #     utils.printer("no valves found in box config", 'msg')

        # overwriting vars
        # self.VariableController.write_variables(self.vars_path)

        # restoring original variables
        # shutil.copy(self.vars_path.with_suffix('.default'), self.vars_path)
        # os.remove(self.vars_path.with_suffix('.default'))

        

    # def log_task(self, folder):
    #     """ copy the entire arduino folder to the logging folder """
    #     utils.printer("logging arduino code", 'task')
    #     src = self.task_folder
    #     target = folder / self.config['current']['task']
    #     shutil.copytree(src, target)


        
    

    def Run(self, folder):
        """ folder is the logging folder """
        # the folder that is used for storage
        # self.run_folder = folder # needs to be stored for access

        # logging the code
        # self.log_task(self.run_folder)

        # upload
        if self.reprogramCheckBox.checkState() == 2: # true when checked
            self.upload()
        else:
            utils.printer("reusing previously uploaded sketch", 'msg')

        # last vars
        # if self.VariableController.LastVarsCheckBox.checkState() == 2: # true when checked
        #     last_vars = self.VariableController.load_last_vars()
        #     if last_vars is not None:
        #         current_vars = self.VariableController.Df
        #         if self.VariableController.check_vars(last_vars, current_vars):
        #             self.VariableController.use_last_vars()
        #             utils.printer("using variables from last session", 'msg')
        #         else:
        #             self.VariableController.use_default_vars()
        #             utils.printer("attemped use variables from last session, but they are unequal. Using default instead", 'warning')
        #     else:
        #         utils.printer("attempted to use variables from last session, but couldn't find. Using default instead", 'warning')
        # self.VariableController.VariableEditWidget.setEnabled(True)
            
        # connect to serial port
        self.connection = self.connect()

        # start up the online data analyzer
        # if hasattr(self, 'OnlineDataAnalyser'):
        #     utils.printer("starting online data analyser", 'msg')
        #     self.OnlineDataAnalyser.run()

        # external logging
        # self.arduino_log_fH = open(self.run_folder / 'arduino_log.txt', 'w')

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

                if line is not '': # filtering out empty reads
                    # self.arduino_log_fH.write(line+os.linesep) # external logging
                    self.serial_data_available.emit(line) # internal publishing

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start()
        utils.printer("listening to FSM arduino on serial port %s" % self.box['connections']['FSM_arduino_port'], 'msg')

        # start timer
        # for counter in self.parent().Counters:
        #     if hasattr(counter, 'timer'):
        #         counter.start()

        # now send variables
        # time.sleep(3)
        # self.VariableController.send_all_variables()
    
    # def stop(self):
    #     """ halts the FSM """
    #     self.send('CMD HALT')
    #     self.RunBtn.setText('RUN')
    #     self.RunBtn.setStyleSheet("background-color: green")

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self, 'connection'):
            if self.connection.is_open:
                self.reset_arduino(self.connection)
                self.connection.close()
            # self.SerialMonitor.close()
        # self.VariableController.close()
        
        # explicit - should fix windows bug where arduino_log.txt is not written
        # if hasattr(self, 'arduino_log_fH'):
        #     self.arduino_log_fH.close() 

        # self.thread.join()

        # overwrite logged arduino vars file
        # if hasattr(self, 'run_folder'):
        #     target = self.run_folder / self.config['current']['task']  / 'Arduino' / 'src' / 'interface_variables.h'
        #     if target.exists(): # bc close event is also triggered on task_changed
        #         self.VariableController.write_variables(target)

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # take care of the kids
        # for Child in self.Children:
        #     Child.close()
        # self.close()






























"""
 
 ##     ##    ###    ########  ####    ###    ########  ##       ########  ######  
 ##     ##   ## ##   ##     ##  ##    ## ##   ##     ## ##       ##       ##    ## 
 ##     ##  ##   ##  ##     ##  ##   ##   ##  ##     ## ##       ##       ##       
 ##     ## ##     ## ########   ##  ##     ## ########  ##       ######    ######  
  ##   ##  ######### ##   ##    ##  ######### ##     ## ##       ##             ## 
   ## ##   ##     ## ##    ##   ##  ##     ## ##     ## ##       ##       ##    ## 
    ###    ##     ## ##     ## #### ##     ## ########  ######## ########  ######  
 
"""

class ArduinoVariablesWidget(QtWidgets.QWidget):
    """ displayes and allows for online editing of variables """

    def __init__(self, parent):
        super(ArduinoVariablesWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Df = self.load_default_vars()
        self.sent_variables = copy(self.Df)
        self.initUI()

        # connect
        parent.serial_data_available.connect(self.on_serial)

    def initUI(self):
        # contains a scroll area which contains the scroll widget
        self.ScrollArea = QtWidgets.QScrollArea()
        self.ScrollWidget = QtWidgets.QWidget()

        # scroll widget has the layout etc
        self.VariableEditWidget = ValueEditFormLayout(self, DataFrame=self.Df)
        self.VariableEditWidget.setEnabled(False)

        # note: the order of this seems to be of utmost importance ... 
        # self.ScrollWidget.setLayout(self.VariableEditWidget)
        self.ScrollArea.setWidget(self.VariableEditWidget)

        self.Layout = QtWidgets.QVBoxLayout(self)
        self.Layout.addWidget(self.ScrollArea)

        SendBtn = QtWidgets.QPushButton(self)
        SendBtn.setText('Send')
        SendBtn.clicked.connect(self.send_btn_clicked)
        self.Layout.addWidget(SendBtn)

        # last variables functionality
        LastVarsBtn = QtWidgets.QPushButton(self)
        LastVarsBtn.setText('last session')
        LastVarsBtn.clicked.connect(self.use_last_vars)

        DefaultVarsBtn = QtWidgets.QPushButton(self)
        DefaultVarsBtn.setText('default')
        DefaultVarsBtn.clicked.connect(self.use_default_vars)

        self.LastVarsCheckBox = QtWidgets.QCheckBox('automatic last')
        self.LastVarsCheckBox.setChecked(True)
        LastVars = QtWidgets.QHBoxLayout(self)
        LastVars.addWidget(QtWidgets.QLabel("variables to use"))
        LastVars.addWidget(DefaultVarsBtn)
        LastVars.addWidget(LastVarsBtn)
        LastVars.addWidget(self.LastVarsCheckBox)
        self.Layout.addLayout(LastVars)

        self.setLayout(self.Layout)

        self.setWindowTitle("Arduino variables")

        self.settings = QtCore.QSettings('TaskControl', 'ArduinoVariablesController')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def load_default_vars(self):
        # contains the hardcoded path
        vars_path = self.parent().task_folder / 'Arduino' / 'src' / "interface_variables.h"
        try:
            default_vars = utils.parse_arduino_vars(vars_path)
            return default_vars
        except:
            utils.printer("failed to load default variables",'error')
            return None 

    def load_last_vars(self):
        """ try to get arduino variables from last run for the task 
        only loads, does not send! """
        config = self.parent().config

        folder = Path(config['paths']['animals_folder']) / config['current']['animal']
        SessionsDf = utils.get_sessions(folder)

        try:
            previous_sessions = SessionsDf.groupby('task').get_group(config['current']['task'])
        except KeyError:
            utils.printer("trying to use last vars, but animal has not been run on this task before.",'error')
            return None

        # to allow for this functionalty while task is running
        if self.parent().parent().running:
            ix = -2
        else:
            ix = -1

        try:
            prev_session_path = Path(previous_sessions.iloc[ix]['path'])
            prev_vars_path = prev_session_path / config['current']['task'] / "Arduino" / "src" / "interface_variables.h"
            if prev_vars_path.exists():
                prev_vars = utils.parse_arduino_vars(prev_vars_path)
                return prev_vars
            else:
                utils.printer("didn't find variables from last session", "error")
                return None

        except IndexError:
            # thrown when there is no previous session
            return None

    def check_vars(self, Df_a, Df_b):
        if not np.all(Df_a['name'].sort_values().values == Df_b['name'].sort_values().values):
            utils.printer("unequal variable names between last session and this session", 'error')
            return False
        else:
            return True

    def get_changed_vars(self):
        Df = self.VariableEditWidget.get_entries()
        binds = (Df['value'] != self.sent_variables['value']).values
        return self.Df.loc[binds]['name'].values
    
    def write_variables(self, path):
        """ writes current arduino variables to the path """
        # get the model
        Df = self.VariableEditWidget.get_entries()

        # convert it to arduino compatible
        lines = utils.Df2arduino_vars(Df)

        # write it
        with open(path, 'w') as fH:
            fH.writelines(lines)

    def send_variable(self, name, value):
        # reading and writing from different threads apparently threadsafe
        # https://stackoverflow.com/questions/8796800/pyserial-possible-to-write-to-serial-port-from-thread-a-do-blocking-reads-fro

        if hasattr(self.parent(), 'connection'):
            # report
            utils.printer("sending variable %s: %s" % (name, value))

            # this is the hardcoded command sending definition
            cmd = '<SET %s %s>' % (name, value) 
            bytestr = str.encode(cmd)
            self.parent().send_raw(bytestr)
            time.sleep(0.05) # grace period to guarantee successful sending

            # store
            self.sent_variables.loc[self.sent_variables['name'] == name,'value'] = value

        else:
            utils.printer("trying to send variable %s to the FSM, but is not connected" % name, 'error')

    def send_variables(self, names):
        for name in names:
            row = self.VariableEditWidget.get_entry(name)
            self.send_variable(row['name'], row['value'])

    def send_all_variables(self):
        Df = self.VariableEditWidget.get_entries()
        for i, row in Df.iterrows():
            self.send_variable(row['name'], row['value'])

    def send_btn_clicked(self):
        changed_vars = self.get_changed_vars()
        self.send_variables(changed_vars)

    def use_vars(self, Df, ignore_calib=True):
        # does not send
        # ignoring valve calib
        if ignore_calib:
            Df_ = Df.loc[['ul_ms' not in name for name in Df['name']]]
            self.VariableEditWidget.set_entries(Df_)
        else:
            self.VariableEditWidget.set_entries(Df)
    
    def use_last_vars(self):
        last_vars = self.load_last_vars()
        self.use_vars(last_vars)

    def use_default_vars(self):
        default_vars = self.load_default_vars()
        self.LastVarsCheckBox.setChecked(False)
        self.use_vars(default_vars)

    def query(self):
        """ report back all variable values 
        the problem is that this causes a bug - arduino replies with <VAR and this triggers on_serial """
        for name in self.Df['name'].values:
            self.parent().send("GET "+name)
            time.sleep(0.05)

    def on_serial(self, line):
        """ this is for updating the UI when arduino has changed a var (and reports it) """
        if line.startswith('<VAR'):
            line_split = line[1:-1].split(' ')
            name = line_split[1]
            value = line_split[2]
            if name in self.VariableEditWidget.Df['name'].values:
                self.VariableEditWidget.set_entry(name, value) # the lineedit should take care of the correct dtype

    def closeEvent(self, event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

"""
 
  #######  ##    ## ##       #### ##    ## ########       ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
 ##     ## ###   ## ##        ##  ###   ## ##            ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
 ##     ## ####  ## ##        ##  ####  ## ##           ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##        ##  ## ## ## ######      ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ##     ## ##  #### ##        ##  ##  #### ##          ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##        ##  ##   ### ##          ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
  #######  ##    ## ######## #### ##    ## ########    ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""

class OnlineDataAnalyser(QtCore.QObject):
    """ listens to serial port, analyzes arduino data as it comes in """
    trial_data_available = QtCore.pyqtSignal(pd.DataFrame, pd.DataFrame)
    decoded_data_available = QtCore.pyqtSignal(str)

    def __init__(self, parent, CodesDf, config=None):
        super(OnlineDataAnalyser, self).__init__(parent=parent)
        self.parent = parent
        self.config = config
        
        self.CodesDf = CodesDf # required, path could be set in online analysis
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        # get metrics
        try:
            metrics = [m.strip() for m in self.config['online_metrics'].split(',')]
            mod = importlib.import_module('Utils.metrics')
            self.Metrics = [getattr(mod, metric) for metric in metrics]
        except KeyError:
            self.Metrics = None

        # events
        try:
            self.new_trial_event = self.config['new_trial_event']
        except KeyError:
            self.new_trial_event = None
        
        try:
            self.reward_events = [event.strip() for event in config['reward_event'].split(',')]
        except KeyError:
            self.reward_events = None
        
        self.lines = []
        self.SessionDf = None

    
    def run(self):
        # needed like this because of init order
        self.parent.serial_data_available.connect(self.update)

    def decode(self, line):
        decoded = None
        if not line.startswith('<'):
            try:
                code, t = line.split('\t')
                t = float(t)
                decoded = self.code_map[code]

                # publish
                to_send = '\t'.join([decoded, str(t)])
                self.decoded_data_available.emit(to_send)

            except:
                pass
        return decoded

    def update(self, line):
        self.lines.append(line)

        decoded = self.decode(line)

        if decoded is not None:
            # the event that separates the stream of data into chunks of trials
            if decoded == self.new_trial_event:

                # parse lines
                TrialMetricsDf = None
                try:
                    TrialDf = bhv.parse_lines(self.lines, code_map=self.code_map, parse_var=True)
                    TrialMetricsDf = bhv.parse_trial(TrialDf, self.Metrics)
                except ValueError:  # important TODO - investigate this! this was added with cue on reach and no mistakes
                    utils.printer('failed parse of lines into TrialDf', 'error')
                    # utils.debug_trace()
                    pass 
                
                if TrialMetricsDf is not None:
                    if self.SessionDf is None: # on first
                        self.SessionDf = TrialMetricsDf
                    else:
                        self.SessionDf = pd.concat([self.SessionDf, TrialMetricsDf])
                        self.SessionDf = self.SessionDf.reset_index(drop=True)

                    # emit data
                    self.trial_data_available.emit(TrialDf, TrialMetricsDf)

                    # restart lines with current line
                    self.lines = [line]

"""
 
 ##     ##  #######  ##    ## #### ########  #######  ########  
 ###   ### ##     ## ###   ##  ##     ##    ##     ## ##     ## 
 #### #### ##     ## ####  ##  ##     ##    ##     ## ##     ## 
 ## ### ## ##     ## ## ## ##  ##     ##    ##     ## ########  
 ##     ## ##     ## ##  ####  ##     ##    ##     ## ##   ##   
 ##     ## ##     ## ##   ###  ##     ##    ##     ## ##    ##  
 ##     ##  #######  ##    ## ####    ##     #######  ##     ## 
 
"""

class SerialMonitorWidget(QtWidgets.QWidget):
    """ just print the lines from the arduino into this window
    open upon connect and received data
    """

    def __init__(self, parent, code_map):
        super(SerialMonitorWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()
        self.lines = []
        self.code_map = code_map
        self.code_map_inv = dict(zip(code_map.values(), code_map.keys()))
        
        if 'display_event_filter' in dict(parent.task_config).keys():
            self.filter = [event.strip() for event in parent.task_config['display_event_filter'].split(',')]
        else:
            self.filter = []

        # connect to parent signals
        parent.serial_data_available.connect(self.update)

    def initUI(self):
        # logging checkbox
        self.Layout = QtWidgets.QVBoxLayout()
        # self.update_CheckBox = QtWidgets.QCheckBox("update")
        # self.update_CheckBox.setChecked(True)
        # self.Layout.addWidget(self.update_CheckBox)
        
        # textbrowser
        self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Layout.addWidget(self.TextBrowser)

        # all
        self.setLayout(self.Layout)
        self.setWindowTitle("Arduino monitor")

        self.settings = QtCore.QSettings('TaskControl', 'SerialMonitor')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def update(self, line):
        if not True in [line.startswith(f) for f in self.filter]:
            if not line.startswith('<'):
                try:
                    code = line.split('\t')[0]
                    decoded = self.code_map[code]
                    line = '\t'.join([decoded, line.split('\t')[1]])
                except:
                    utils.printer("Error dealing with line %s" % line, 'error')
                    pass

            # TODO deal with the history functionality
            history_len = 100 # FIXME expose this property? or remove it. for now for debugging

            if len(self.lines) < history_len:
                self.lines.append(line)
            else:
                self.lines.append(line)
                self.lines = self.lines[1:]

            # print lines in window
            sb = self.TextBrowser.verticalScrollBar()
            sb_prev_value = sb.value()
            self.TextBrowser.setPlainText('\n'.join(self.lines))
            
            # scroll to end
            sb.setValue(sb.maximum())

            # BUG does not work!
            # if self.update_CheckBox.checkState() == 2:
            #    sb.setValue(sb.maximum())
            # else:
            #     sb.setValue(sb_prev_value)

    def closeEvent(self, event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())


class StateMachineMonitorWidget(QtWidgets.QWidget):
    
    def __init__(self, parent, code_map=None):
        super(StateMachineMonitorWidget, self).__init__(parent=parent)

        # code_map related
        self.code_map = code_map
        
        # connect to parent signals
        parent.serial_data_available.connect(self.update)

        self.initUI()

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.Window)

        # layouting
        self.Layout = QtWidgets.QVBoxLayout()
        self.States_Layout = QtWidgets.QHBoxLayout()
        self.Spans_Layout = QtWidgets.QHBoxLayout()
        # self.Events_Layout = QtWidgets.QHBoxLayout()
        self.Btns = []

        for code, full_name in self.code_map.items():
            splits = full_name.split('_')
            name = '_'.join(splits[:-1])
            kind = splits[-1]

            Btn = QtWidgets.QPushButton()
            Btn.setText(name)
            if kind == 'STATE':
                Btn.setCheckable(False)
                self.States_Layout.addWidget(Btn)
            if kind == 'ON':
                Btn.setCheckable(False)
                self.Spans_Layout.addWidget(Btn)
            # if kind == 'EVENT':
            #     Btn.setCheckable(False)
            #     self.Events_Layout.addWidget(Btn)

            self.Btns.append((full_name, Btn))

        self.Layout.addLayout(self.States_Layout)
        self.Layout.addLayout(self.Spans_Layout)
        # self.Layout.addLayout(self.Events_Layout)

        self.setLayout(self.Layout)
        self.setWindowTitle("State Machine Monitor")

        self.settings = QtCore.QSettings('TaskControl', 'StateMachineMonitor')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def update(self, line):
        try:
            code, time = line.split('\t')
            full_name = self.code_map[code]

            # remove all color from events
            if full_name.endswith("_EVENT") or full_name.endswith("_ON") or full_name.endswith("_OFF"):
                for name, btn in self.Btns:
                    if name.endswith('_EVENT'):
                        btn.setStyleSheet("background-color: light gray")

            # for states
            if full_name.endswith("_STATE"):
                # color all state buttons gray
                for name, btn in self.Btns:
                    if name.endswith("_STATE"):
                        btn.setStyleSheet("background-color: light gray")

                # and color only active green
                btn = [btn for name, btn in self.Btns if name==full_name][0]
                btn.setStyleSheet("background-color: green")

            # for spans
            if full_name.endswith("_ON"):
                btn = [btn for name, btn in self.Btns if name==full_name][0]

                if full_name.endswith("_ON"):
                    btn.setStyleSheet("background-color: green")

            if  full_name.endswith("_OFF"):
                btn = [btn for name, btn in self.Btns if name==full_name[:-3]+'ON'][0]
                btn.setStyleSheet("background-color: light gray")
            
            # for events stay green until next line read
            if  full_name.endswith("_EVENT"):
                btn = [btn for name, btn in self.Btns if name==full_name][0]
                btn.setStyleSheet("background-color: green")
            
        except:
            pass

    def closeEvent(self, event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
