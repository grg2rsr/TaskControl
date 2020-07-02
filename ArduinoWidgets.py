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
import functions
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

    def __init__(self, parent):
        super(ArduinoController, self).__init__(parent=parent)
        
        # for abbreviation bc if changed, objects are reinstantiated anyways
        self.task = self.parent().task
        self.task_folder = Path(self.parent().profile['tasks_folder']).joinpath(self.task)
        self.task_config = self.parent().task_config['Arduino']

        self.Children = []
        self.stopped = False # for killing the thread that reads from serial port

        # TODO here: copy these variables to the temp vars path and overwrite the path here
        # then - all operations should be done on this

        # VariableController
        self.vars_path = self.task_folder.joinpath('Arduino','src',self.task_config['var_fname'])
        Df = functions.parse_arduino_vars(self.vars_path)
        self.VariableController = ArduinoVariablesWidget(self,Df)
        self.Children.append(self.VariableController)

        path = self.task_folder.joinpath('Arduino','src','event_codes.h')
        CodesDf = functions.parse_code_map(path)
        self.code_map = dict(zip(CodesDf['code'], CodesDf['name']))

        # online analyzer
        Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT, bhv.has_choice, bhv.choice_RT) # HARDCODE
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
        # self.reprogramCheckBox.stateChanged.connect(self.reprogramCheckBox_changed)
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
        small_gap = int(self.parent().profiles['General']['small_gap'])
        big_gap = int(self.parent().profiles['General']['big_gap'])

        functions.scale_Widgets([self] + self.Children[:-1],mode='max') # dirty hack to not scale the state machine monitor
        for i,child in enumerate(self.Children):
            if i == 0:
                ref = self
            else:
                ref = self.Children[i-1]
            functions.tile_Widgets(child, ref, where='below',gap=big_gap)

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
            print(bytestr)
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
        pio_config = configparser.ConfigParser()
        self.pio_config_path = self.task_folder.joinpath(self.task_config['pio_project_folder'],"platformio.ini")
        pio_config.read(self.pio_config_path)

        for section in pio_config.sections():
            if section.split(":")[0] == "env":
                pio_config.set(section,"upload_port",self.task_config['com_port'].split(':')[0])

        # write it
        with open(self.pio_config_path, 'w') as fH:
            pio_config.write(fH)
        
        # get current UI arduino variables, backup defaults,
        # write the UI derived and upload those, revert after upload
        # this workaround is necessary to use the get previous variables
        # functionality ... 

        # backing up original values
        shutil.copy(self.vars_path,self.vars_path.with_suffix('.default'))

        # overwriting vars
        self.VariableController.write_variables(self.vars_path)

        # if self.parent().logging:
        #     self.VariableController.write_variables(os.path.join('src',self.task_config['var_fname']))

        # upload
        print(" --- uploading code on arduino --- ")
        prev_dir = Path.cwd()
        os.chdir(self.task_folder.joinpath(self.task_config['pio_project_folder']))

        fH = open(self.run_folder.joinpath('platformio_build_log.txt'),'w')
        platformio_cmd = self.parent().profiles['General']['platformio_cmd']
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
        target = folder.joinpath(self.task)
        shutil.copytree(src,target)

    def connect(self):
        """ establish serial connection with the arduino board """
        
        com_port = self.task_config['com_port'].split(':')[0]
        baud_rate = self.task_config['baud_rate']
        try:
            print("initializing serial port: "+com_port)
            ser = serial.Serial(port=com_port, baudrate=baud_rate,timeout=2)
            ser.setDTR(False) # reset: https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial
            time.sleep(1) # sleep timeout length to drop all data
            ser.flushInput() # 
            ser.setDTR(True)
            print(" ... done")
            self.connected = True
            return ser

        except:
            print("could not connect to the Arduino!")
            sys.exit()

    def Run(self,folder):
        """ folder is the logging folder """
        self.run_folder = folder # to be kept for the close_event

        # logging the code
        self.log_task(folder)

        # upload
        if self.reprogramCheckBox.checkState() == 2: # true when checked
            self.upload()
        else:
            print(" --- resetting arduino only --- reusing previous sketch --- ")

        # connect to serial port
        self.connection = self.connect()      

        # start up the online data analyzer
        self.OnlineDataAnalyser.run()

        fH = open(folder.joinpath('arduino_log.txt'),'w')

        # multithreading taken from
        # https://stackoverflow.com/questions/17553543/pyserial-non-blocking-read-loop
        # general idea:

        # emit a signal that data came in, signal carries string of the data
        # everybody that needs to do sth when new data arrives listens to that signal

        def read_from_port(ser):
            while not self.stopped:
                try:
                    line = ser.readline().decode('utf-8').strip()
                    if line is not '': # filtering out empty reads
                        fH.write(line+os.linesep) # external logging
                        
                        # publishing data
                        self.serial_data_available.emit(line)

                except:
                    # TODO work on this: if ser.is_open() could be the single function call that fixes this
                    # fails when port not open
                    # FIXME CHECK if this will also fail on failed reads!
                    break

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start()
        print("listening on serial port has started")
    
    def stop(self):
        """ when session is finished """
        self.send('CMD HALT')
        self.RunBtn.setText('RUN')
        self.RunBtn.setStyleSheet("background-color: green")
    pass

    # def parse_line(self,line):
    #     # TODO FIXME this should be part of the VariableController
    #     # TODO the entire VAR functionality needs to be reworked
    #     # if report
    #     if line.startswith('<'):
    #         if line[1:-1].split(' ')[0] == 'VAR':
    #             cmd,var,value = line[1:-1].split(' ')
    #             Df = self.VariableController.VariableEditWidget.get_entries()
    #             Df.index = Df.name
    #             Df.loc[var,'value'] = int(value)
    #             Df.reset_index(drop=True,inplace=True)
    #             self.VariableController.VariableEditWidget.set_entries(Df)

    #     # TODO FIXME this should be now part of the online analyzer
    #     # normal read
    #     if '\t' in line:
    #         code = line.split('\t')[0]
    #         decoded = self.code_map[code]
    #         line = '\t'.join([decoded,line.split('\t')[1]])

    def closeEvent(self, event):
        # take care of ending the threads
        self.stopped = True

        # self.thread.join()

        # overwrite logged arduino vars file
        try:
            target = self.run_folder.joinpath(self.task)
            self.VariableController.write_variables(target.joinpath('Arduino','src',self.task_config['var_fname']))
        except AttributeError:
            # FIXME this is hacked in bc closeEvent is fired when task is changed -> crashes
            pass

        # if serial connection is open, close it
        if hasattr(self,'connection'):
            if self.connection.is_open:
                self.connection.close()
            self.SerialMonitor.close()
        self.VariableController.close()

        # read in original task config - why?
        task_config = configparser.ConfigParser()
        task_config_path = self.task_folder.joinpath("task_config.ini")
        task_config.read(task_config_path)
        
        # remove everything that is written nontheless
        # shutil.rmtree(self.run_folder)

        # take care of the kids
        for child in self.Children:
            child.close()
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

        parent.serial_data_available.connect(self.on_serial)

    def initUI(self):
        # contains a scroll area which contains the scroll widget
        self.ScrollArea = QtWidgets.QScrollArea()
        self.ScrollWidget = QtWidgets.QWidget()

        # scroll widget has the layout etc
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
        # TODO add some interesting header info
        # day of training
        # day / time of writing this should already be in file?
        # animal ID

        header = []
        header.append("// ---  file automatically generated by TaskControl --- ")
        header.append("//Animal: "+self.parent().parent().animal) # FIXME
        header = [line+os.linesep for line in header]

        # get vars from UI
        Df = self.VariableEditWidget.get_entries()

        # convert them into something that arduino lang understands
        dtype_map_inv = dict(zip(functions.dtype_map.values(),functions.dtype_map.keys()))

        lines = []
        for i, row in Df.iterrows():
            elements = []
            elements.append(dtype_map_inv[row['dtype']]) 
            elements.append(row['name'])
            elements.append('=')
            if row['dtype'] == '?':
                if row['value'] == True:
                    value = "true"
                if row['value'] == False:
                    value = "false"
            else:
                value = str(row['value'])

            elements.append(value + ';' + os.linesep)
            lines.append(' '.join(elements))

        # write it
        with open(path, 'w') as fH:
            fH.write(''.join(header+lines))

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
                self.parent().connection.write(bytestr)
                time.sleep(0.01) # to fix incomplete sends? verify if this really works ... 
        else:
            print("Arduino is not connected")

    def load_last_vars(self):
        """ try to get arduino variables from last run for the task 
        only loads, does not send! """
        ThisSettingsWidget = self.parent().parent() # FIXME

        try:
            current_animal_folder = Path(ThisSettingsWidget.profile['animals_folder']).joinpath(ThisSettingsWidget.animal)
            SessionsDf = utils.get_sessions(current_animal_folder)
            previous_sessions = SessionsDf.groupby('task').get_group(ThisSettingsWidget.task)

            prev_session_path = Path(previous_sessions.iloc[-1]['path'])
            prev_vars_path = prev_session_path.joinpath(ThisSettingsWidget.task, self.parent().task_config['pio_project_folder'], 'src', self.parent().task_config['var_fname'])
            
            prev_vars = functions.parse_arduino_vars(prev_vars_path)

            self.VariableEditWidget.set_entries(prev_vars)
           
        except KeyError:
            print("trying to use last vars, but animal has not been run on this task before.")

    def on_serial(self, line):
        """ updates the display """
        # TODO this entire thing need to be reworked 
        # model / view architecture

        if line.startswith('<VAR'):
            _, name, value, t = line[1:-1].split(' ')
            Df = self.VariableEditWidget.get_entries()
            Df.index = Df.name
            if name in Df.index:
                Df.loc[name,'value'] = float(value) # FIXME WARNING dtype awareness?
                Df.reset_index(drop=True,inplace=True)
                self.VariableEditWidget.set_entries(Df)

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

        # if normally decodeable
        if not line.startswith('<'):
            self.lines.append(line)

            code, t = line.split('\t')
            t = float(t)
            decoded = self.code_map[code]

            # update counters
            if decoded == 'TRIAL_SUCCESSFUL_EVENT':
                self.TrialCounter.increment(successful=True)

            if decoded == 'TRIAL_UNSUCCESSFUL_EVENT':
                self.TrialCounter.increment(successful=False)

            # update water counter if reward was collected
            if decoded == 'REWARD_COLLECTED_EVENT':
                VarsDf = self.parent.VariableController.VariableEditWidget.get_entries()
                if 'reward_magnitude' in VarsDf['name'].values:
                    VarsDf.index = VarsDf.name
                    current_magnitude = VarsDf.loc['reward_magnitude','value']
                    self.WaterCounter.increment(current_magnitude)

            # the event that separates the stream of data into chunks of trials
            if decoded == "TRIAL_AVAILABLE_STATE": # HARDCODE

                # parse lines
                TrialDf = bhv.parse_lines(self.lines, code_map=self.code_map)
                TrialMetricsDf = bhv.parse_trial(TrialDf, self.Metrics)
                
                if TrialMetricsDf is not None:
                    # update SessionDf
                    if self.SessionDf is None: # on first
                        self.SessionDf = TrialMetricsDf
                    else:
                        self.SessionDf = self.SessionDf.append(TrialMetricsDf)
                        self.SessionDf = self.SessionDf.reset_index(drop=True)

                    # emit data
                    self.trial_data_available.emit(TrialDf, TrialMetricsDf)

                    # restart lines with current line
                    self.lines = [line]

"""
 
 ######## ########  ####    ###    ##           ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
    ##    ##     ##  ##    ## ##   ##          ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
    ##    ##     ##  ##   ##   ##  ##          ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
    ##    ########   ##  ##     ## ##          ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
    ##    ##   ##    ##  ######### ##          ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
    ##    ##    ##   ##  ##     ## ##          ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
    ##    ##     ## #### ##     ## ########     ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ## 
 
"""

class TrialTypeController(QtWidgets.QWidget):
    def __init__(self, parent, ArduinoController, OnlineDataAnalyser):
        super(TrialTypeController, self).__init__(parent=parent)

        # needs an arduinocontroller to be instantiated
        self.ArduinoController = ArduinoController
        self.AduinoController.serial_data_available.connect(self.on_serial)

        self.OnlineDataAnalyzer = OnlineDataAnalyser

        # calculate current engagement from behav data

        # calculate trial hardness from behav data

        # send new p values to arduino

        # plot them

    def initUI(self):
        """ plots of the current p values """
        pass

    def on_serial(self,line):
        # if arduino requests action
        if line == "<MSG REQUEST TRIAL_PROBS>":
            E = calculate_task_engagement()
            H = calculate_trial_difficulty()
            W = calculate_trial_weights(E,H)

            self.update_plot()

    def calculate_task_engagement(self):
        n_trial_types = 6 # HARDCODE
        P_default = sp.array([0.5,0,0,0,0,0.5])
        history = 10 # past trials to take into consideration 

        # get the data

        # do the calc

        pass

    def calculate_trial_difficulty(self):
        # get the data (same data?)

        # do the calc
        # what to do if there are less than 10 past trials
        pass

    def send_probabilities(self):
        # uses arduinocontroller to send
        # for i in range(n_trial_types):
        #     cmd = ' '.join(['UPD',str(i),str(self.P[i])])
        #     cmd = '<'+cmd+'>'
        #     bytestr = str.encode(cmd)
        #     self.ArduinoController.send_raw(bytestr)
        pass

    def update_plot(self):
        pass

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
        self.Events_Layout = QtWidgets.QHBoxLayout()
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
            if kind == 'EVENT':
                Btn.setCheckable(False)
                self.Events_Layout.addWidget(Btn)

            self.Btns.append((full_name,Btn))

        self.Layout.addLayout(self.States_Layout)
        self.Layout.addLayout(self.Spans_Layout)
        self.Layout.addLayout(self.Events_Layout)

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
