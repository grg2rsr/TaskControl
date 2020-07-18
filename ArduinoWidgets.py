import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import configparser

from pathlib import Path
import subprocess
import datetime
import shutil
import serial
import time
import threading
import queue
from functools import partial
import pandas as pd
import scipy as sp

import Widgets
import utils
import interface_generator

import behavior_analysis_utils as bhv

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
    # initialize signals
    serial_data_available = QtCore.pyqtSignal(str)

    # for an explanation how this works and behaves see
    # here: https://programmer.group/pyqt5-quick-start-pyqt5-signal-slot-mechanism.html
    # and here: https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect

    def __init__(self, parent, config, task_config):
        super(ArduinoController, self).__init__(parent=parent)
        self.name = "ArduinoController"
        
        # the original folder of the task
        self.task_folder = Path(config['paths']['tasks_folder']) / config['current']['task']
        self.config = config
        self.task_config = task_config

        self.Children = []

        # VariableController
        self.vars_path = self.task_folder / 'Arduino' / 'src' / "interface_variables.h"
        Df = utils.parse_arduino_vars(self.vars_path) # initialize with the default variables
        self.VariableController = ArduinoVariablesWidget(self, Df)
        self.Children.append(self.VariableController)

        path = self.task_folder / 'Arduino' / 'src' / 'event_codes.h'
        CodesDf = utils.parse_code_map(path)
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        # online analyzer
        Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT,
                   bhv.has_choice, bhv.choice_RT, bhv.get_choice,
                   bhv.get_interval) # HARDCODE
                   
        self.OnlineDataAnalyser = OnlineDataAnalyser(self, CodesDf, Metrics)
        # don't add him to children bc doesn't have a UI

        # open serial monitor
        self.SerialMonitor = SerialMonitorWidget(self, code_map=self.code_map)
        self.Children.append(self.SerialMonitor)

        # Statemachine Monitor
        self.StateMachineMonitor = StateMachineMonitorWidget(self, code_map=self.code_map)
        self.Children.append(self.StateMachineMonitor)
        
        self.initUI()
    
    def initUI(self):
        # the formlayout
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

        Full_Layout = QtWidgets.QVBoxLayout()
        Full_Layout.addWidget(FormWidget)

        # start/stop button
        self.RunBtn = QtWidgets.QPushButton()
        self.RunBtn.setStyleSheet("background-color: green")
        self.RunBtn.setCheckable(True)
        self.RunBtn.setText('Run')
        self.RunBtn.clicked.connect(self.run_btn_clicked)
        Full_Layout.addWidget(self.RunBtn)

        # direct interaction
        self.SendLine = QtWidgets.QLineEdit()
        SendBtn = QtWidgets.QPushButton()
        SendBtn.setText('Send')
        SendBtn.clicked.connect(self.send_btn_clicked)
        Layout = QtWidgets.QHBoxLayout()
        Layout.addWidget(self.SendLine)
        Layout.addWidget(SendBtn)
        Full_Layout.addLayout(Layout)

        # keyboard interaction
        Label = QtWidgets.QLabel('focus here to capture single keystrokes')
        Full_Layout.addWidget(Label)

        self.setLayout(Full_Layout)
        self.setWindowTitle("Arduino controller")

        self.layout()
        self.show()

    def keyPressEvent(self, event):
        """ reimplementation to send single keystrokes """
        self.send("CMD " + event.text())

    def layout(self):
        """ position children to myself """
        small_gap = int(self.config['ui']['small_gap'])
        # big_gap = int(self.config['ui']['big_gap'])
        utils.tile_Widgets([self] + self.Children, how="vertically",gap=small_gap)

    def send(self,command):
        """ sends string command interface to arduino, interface compatible """
        if hasattr(self,'connection'):
            cmd = '<'+command+'>'
            bytestr = str.encode(cmd)
            self.connection.write(bytestr)
        else:
            print("Arduino is not connected")

    def send_raw(self,bytestr):
        """ sends bytestring """
        if hasattr(self,'connection'):
            self.connection.write(bytestr)
        else:
            print("Arduino is not connected")

    def run_btn_clicked(self):
        if self.RunBtn.isChecked():
            # after being activated
            self.send('CMD RUN')
            self.RunBtn.setText('HALT')
            self.RunBtn.setStyleSheet("background-color: red")
        else: 
            self.send('CMD HALT')
            self.RunBtn.setText('RUN')
            self.RunBtn.setStyleSheet("background-color: green")

    def send_btn_clicked(self):
        """ send command entered in LineEdit """
        command = self.SendLine.text()
        self.send(command)
        
    def upload(self):
        """ uploads the sketch specified in platformio.ini
        which is in turn specified in the task_config.ini """

        # building interface
        print(" --- generating interface.cpp --- ")
        interface_generator.run(self.vars_path)

        # uploading code onto arduino

        # replace whatever com port is in the platformio.ini with the one from task config
        self.pio_config_path = self.task_folder / "Arduino" / "platformio.ini"
        pio_config = configparser.ConfigParser()
        pio_config.read(self.pio_config_path)

        # get upload port
        upload_port = self.config['connections']['FSM_arduino_port']

        for section in pio_config.sections():
            if section.split(":")[0] == "env":
                pio_config.set(section,"upload_port",upload_port)

        # write it
        with open(self.pio_config_path, 'w') as fH:
            pio_config.write(fH)
        
        # get current UI arduino variables, backup defaults,
        # write the UI derived and upload those, revert after upload
        # this workaround is necessary to use the get previous variables
        # functionality ... 

        # backing up original values
        shutil.copy(self.vars_path,self.vars_path.with_suffix('.default'))

        # setting the valve calibration factor
        self.VariableController.VariableEditWidget.set_entry('valve_ul_ms',self.config['box']['valve_ul_ms'])
        
        # overwriting vars
        self.VariableController.write_variables(self.vars_path)

        # upload
        print(" --- uploading code on arduino --- ")
        prev_dir = Path.cwd()

        os.chdir(self.task_folder / 'Arduino')
        fH = open(self.run_folder / 'platformio_build_log.txt','w')
        platformio_cmd = self.config['system']['platformio_cmd']
        cmd = ' '.join([platformio_cmd,'run','--target','upload'])
        proc = subprocess.Popen(cmd,shell=True,stdout=fH)
        proc.communicate()
        fH.close()

        os.chdir(prev_dir)

        # restoring original variables
        shutil.copy(self.vars_path.with_suffix('.default'),self.vars_path)
        os.remove(self.vars_path.with_suffix('.default'))

    def log_task(self,folder):
        """ copy the entire arduino folder to the logging folder """
        print(" - logging arduino code")
        src = self.task_folder
        target = folder / self.config['current']['task']
        shutil.copytree(src,target)

    def reset_arduino(self,connection):
        """ taken from https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial """
        connection.setDTR(False) # reset
        time.sleep(1) # sleep timeout length to drop all data
        connection.flushInput() # 
        connection.setDTR(True)
        
    def connect(self):
        """ establish serial connection with the arduino board """
        try:
            print("initializing serial port: "+com_port)
            # ser = serial.Serial(port=com_port, baudrate=baud_rate,timeout=2)
            connection = serial.Serial(
                     port=self.config['connections']['FSM_arduino_port'],
                     baudrate=self.config['connections']['arduino_baud_rate'],
                     bytesize=serial.EIGHTBITS,
                     parity=serial.PARITY_NONE,
                     stopbits=serial.STOPBITS_ONE,
                     timeout=1,
                     xonxoff=0,
                     rtscts=0
                     )

            self.reset_arduino(connection)
            return connection


        except:
            print("failed to connect to the FSM arduino.")
            sys.exit()

    def Run(self,folder):
        """ folder is the logging folder """
        # the folder that is used for storage
        self.run_folder = folder # needs to be stored for access

        # logging the code
        self.log_task(self.run_folder)

        # upload
        if self.reprogramCheckBox.checkState() == 2: # true when checked
            self.upload()
        else:
            print(" --- resetting arduino only --- reusing previous sketch --- ")

        # connect to serial port
        self.connection = self.connect()      

        # start up the online data analyzer
        self.OnlineDataAnalyser.run()

        fH = open(self.run_folder / 'arduino_log.txt','w')

        def read_from_port(ser):
            while ser.is_open:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line is not '': # filtering out empty reads
                        fH.write(line+os.linesep) # external logging
                        
                        # publishing data
                        self.serial_data_available.emit(line)

                except:
                    print("failed read from serial!", line)
                    break

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start()
        print("beginning to listen to serial port")
    
    def stop(self):
        """ when session is finished """
        self.send('CMD HALT')
        self.RunBtn.setText('RUN')
        self.RunBtn.setStyleSheet("background-color: green")
    pass

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self,'connection'):
            if self.connection.is_open:
                self.reset_arduino(self.connection)
                self.connection.close()
            self.SerialMonitor.close()
        self.VariableController.close()

        # self.thread.join()

        # overwrite logged arduino vars file
        target = self.run_folder / self.config['current']['task']  / 'Arduino' / 'src' / 'interface_variables.h'
        if target.exists(): # bc close event is also triggered on task_changed
            self.VariableController.write_variables(target)

        # take care of the kids
        for Child in self.Children:
            Child.close()
        self.close()

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

    def __init__(self, parent, Df):
        super(ArduinoVariablesWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Df = Df
        self.initUI()

        # connect
        parent.serial_data_available.connect(self.on_serial)

    def initUI(self):
        # contains a scroll area which contains the scroll widget
        self.ScrollArea = QtWidgets.QScrollArea()
        self.ScrollWidget = QtWidgets.QWidget()

        # scroll widget has the layout etc
        # utils.debug_trace()
        self.VariableEditWidget = Widgets.ValueEditFormLayout(self, DataFrame=self.Df)

        # note: the order of this seems to be of utmost importance ... 
        self.ScrollWidget.setLayout(self.VariableEditWidget)
        self.ScrollArea.setWidget(self.ScrollWidget)

        self.Layout = QtWidgets.QVBoxLayout(self)
        self.Layout.addWidget(self.ScrollArea)

        SendBtn = QtWidgets.QPushButton(self)
        SendBtn.setText('Send')
        SendBtn.clicked.connect(self.send_variables)
        self.Layout.addWidget(SendBtn)

        LastVarsBtn = QtWidgets.QPushButton(self)
        LastVarsBtn.setText('use variables from last session')
        LastVarsBtn.clicked.connect(self.load_last_vars)
        self.Layout.addWidget(LastVarsBtn)

        self.setLayout(self.Layout)

        self.setWindowTitle("Arduino variables")
        
        self.show()

    def write_variables(self, path):
        """ writes current arduino variables to the path """
        # get the model
        Df = self.VariableEditWidget.get_entries()

        # convert it to arduino compatible
        lines = utils.Df2arduino_vars(Df)

        # write it
        with open(path, 'w') as fH:
            fH.writelines(lines)

    def send_variables(self):
        """ sends all current variables to arduino """
        if hasattr(self.parent(),'connection'): # TODO check if this can attempt to write on a closed connection
            Df = self.VariableEditWidget.get_entries()
            for i,row in Df.iterrows():

                # this is the hardcoded command sending definition
                cmd = ' '.join(['SET',str(row['name']),str(row['value'])])
                cmd = '<'+cmd+'>'

                bytestr = str.encode(cmd)
                # reading and writing from different threads apparently threadsafe
                # https://stackoverflow.com/questions/8796800/pyserial-possible-to-write-to-serial-port-from-thread-a-do-blocking-reads-fro
                # self.parent().connection.write(bytestr)
                self.parent().send_raw(bytestr)
                time.sleep(0.01) # to fix incomplete sends? verify if this really works ... 
        else:
            print("Arduino is not connected")

    def load_last_vars(self):
        """ try to get arduino variables from last run for the task 
        only loads, does not send! """
        config = self.parent().config

        try:
            folder = Path(config['paths']['animals_folder']) / config['current']['animal']
            SessionsDf = utils.get_sessions(folder)
            previous_sessions = SessionsDf.groupby('task').get_group(config['current']['task'])

            prev_session_path = Path(previous_sessions.iloc[-1]['path'])
            prev_vars_path = prev_session_path / config['current']['task'] / "Arduino" / "src" / "interface_variables.h"
            prev_vars = utils.parse_arduino_vars(prev_vars_path)

            self.VariableEditWidget.set_entries(prev_vars)
           
        except KeyError:
            print("trying to use last vars, but animal has not been run on this task before.")

    def on_serial(self, line):
        """ if the var is in the interface variables, set it """

        if line.startswith('<VAR'):
            _, name, value, t = line[1:-1].split(' ')
            if name in self.VariableEditWidget.Df['name'].values:
                self.VariableEditWidget.set_entry(name, value) # the lineedit should take care of the correct dtype

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
    trial_data_available = QtCore.pyqtSignal(pd.DataFrame,pd.DataFrame)

    def __init__(self, parent, CodesDf, Metrics):
        super(OnlineDataAnalyser, self).__init__(parent=parent)
        self.CodesDf = CodesDf
        self.Metrics = Metrics
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))
        
        self.lines = []
        self.SessionDf = None

        self.parent = parent
    
    def run(self):
        # needed like this because of init order
        self.TrialCounter = self.parent.parent().TrialCounter
        self.WaterCounter = self.parent.parent().WaterCounter
        self.parent.serial_data_available.connect(self.update)

    def update(self,line):
        self.lines.append(line)

        # if normally decodeable
        if not line.startswith('<'):

            code, t = line.split('\t')
            t = float(t)
            decoded = self.code_map[code]

            # update counters
            if decoded == 'CHOICE_CORRECT_EVENT':
                self.TrialCounter.increment('correct')
                self.TrialCounter.increment('total')

            if decoded == 'CHOICE_INCORRECT_EVENT':
                self.TrialCounter.increment('incorrect')
                self.TrialCounter.increment('total')

            if decoded == 'CHOICE_MISSED_EVENT':
                self.TrialCounter.increment('missed')
                self.TrialCounter.increment('total')
            
            if decoded == 'PREMATURE_CHOICE_EVENT':
                self.TrialCounter.increment('premature')
                self.TrialCounter.increment('total')

            # update water counter if reward was collected
            if decoded == 'REWARD_COLLECTED_EVENT':
                current_magnitude = self.parent.VariableController.VariableEditWidget.get_entry('reward_magnitude')['value']
                self.WaterCounter.increment(current_magnitude)

            # the event that separates the stream of data into chunks of trials
            if decoded == "TRIAL_AVAILABLE_STATE": # HARDCODE

                # parse lines
                TrialDf = bhv.parse_lines(self.lines, code_map=self.code_map, parse_var=True)
                TrialMetricsDf = bhv.parse_trial(TrialDf, self.Metrics)
                
                if TrialMetricsDf is not None:
                    if self.SessionDf is None: # on first
                        self.SessionDf = TrialMetricsDf
                    else:
                        self.SessionDf = self.SessionDf.append(TrialMetricsDf)
                        self.SessionDf = self.SessionDf.reset_index(drop=True)

                    # emit data
                    self.trial_data_available.emit(TrialDf, TrialMetricsDf)

                    # restart lines with current line
                    self.lines = [line]

# """
 
#  ######## ########  ####    ###    ##           ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
#     ##    ##     ##  ##    ## ##   ##          ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
#     ##    ##     ##  ##   ##   ##  ##          ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
#     ##    ########   ##  ##     ## ##          ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
#     ##    ##   ##    ##  ######### ##          ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
#     ##    ##    ##   ##  ##     ## ##          ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
#     ##    ##     ## #### ##     ## ########     ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ## 
 
# """

# class TrialTypeController(QtWidgets.QWidget):
#     def __init__(self, parent, ArduinoController, OnlineDataAnalyser):
#         super(TrialTypeController, self).__init__(parent=parent)

#         # needs an arduinocontroller to be instantiated
#         self.ArduinoController = ArduinoController
#         self.AduinoController.serial_data_available.connect(self.on_serial)

#         self.OnlineDataAnalyzer = OnlineDataAnalyser

#         # calculate current engagement from behav data

#         # calculate trial hardness from behav data

#         # send new p values to arduino

#         # plot them

#     def initUI(self):
#         """ plots of the current p values """
#         pass

#     def on_serial(self,line):
#         # if arduino requests action
#         if line == "<MSG REQUEST TRIAL_PROBS>":
#             E = calculate_task_engagement()
#             H = calculate_trial_difficulty()
#             W = calculate_trial_weights(E,H)

#             self.update_plot()

#     def calculate_task_engagement(self):
#         n_trial_types = 6 # HARDCODE
#         P_default = sp.array([0.5,0,0,0,0,0.5])
#         history = 10 # past trials to take into consideration 

#         # get the data

#         # do the calc

#         pass

#     def calculate_trial_difficulty(self):
#         # get the data (same data?)

#         # do the calc
#         # what to do if there are less than 10 past trials
#         pass

#     def send_probabilities(self):
#         # uses arduinocontroller to send
#         # for i in range(n_trial_types):
#         #     cmd = ' '.join(['UPD',str(i),str(self.P[i])])
#         #     cmd = '<'+cmd+'>'
#         #     bytestr = str.encode(cmd)
#         #     self.ArduinoController.send_raw(bytestr)
#         pass

#     def update_plot(self):
#         pass

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
        # TODO
        # self.code_map_inv = dict(zip(code_map.values(), code_map.keys()))
        # self.filter = ["<VAR current_zone", ]

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
        self.show()
        self.layout()

    def update(self,line):
        # TODO filter out high freq events like lick and zone
        # w checkbox - LICK does not work bc not decoded EASY TODO

        if not line.startswith('<VAR current_zone') and not line.startswith('LICK'):
            if not line.startswith('<'):
                code = line.split('\t')[0]
                decoded = self.code_map[code]
                line = '\t'.join([decoded,line.split('\t')[1]])

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


class StateMachineMonitorWidget(QtWidgets.QWidget):
    
    def __init__(self,parent, code_map=None):
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

            self.Btns.append((full_name,Btn))

        self.Layout.addLayout(self.States_Layout)
        self.Layout.addLayout(self.Spans_Layout)
        # self.Layout.addLayout(self.Events_Layout)

        self.setLayout(self.Layout)
        self.setWindowTitle("State Machine Monitor")

        self.show()

    def update(self,line):
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
                btn = [btn for name,btn in self.Btns if name==full_name][0]
                btn.setStyleSheet("background-color: green")

            # for spans
            if full_name.endswith("_ON"):
                btn = [btn for name,btn in self.Btns if name==full_name][0]

                if full_name.endswith("_ON"):
                    btn.setStyleSheet("background-color: green")

            if  full_name.endswith("_OFF"):
                btn = [btn for name,btn in self.Btns if name==full_name[:-3]+'ON'][0]
                btn.setStyleSheet("background-color: light gray")
            
            # for events stay green until next line read
            if  full_name.endswith("_EVENT"):
                btn = [btn for name,btn in self.Btns if name==full_name][0]
                btn.setStyleSheet("background-color: green")
            
        except:
            pass
