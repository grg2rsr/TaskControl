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

class Signals(QtCore.QObject):
    # explained here why this has to be within a QObject
    # https://programmer.group/pyqt5-quick-start-pyqt5-signal-slot-mechanism.html
    serial_data_available = QtCore.pyqtSignal(str)

"""
  ______   ______   .__   __. .___________..______        ______    __       __       _______ .______
 /      | /  __  \  |  \ |  | |           ||   _  \      /  __  \  |  |     |  |     |   ____||   _  \
|  ,----'|  |  |  | |   \|  | `---|  |----`|  |_)  |    |  |  |  | |  |     |  |     |  |__   |  |_)  |
|  |     |  |  |  | |  . `  |     |  |     |      /     |  |  |  | |  |     |  |     |   __|  |      /
|  `----.|  `--'  | |  |\   |     |  |     |  |\  \----.|  `--'  | |  `----.|  `----.|  |____ |  |\  \----.
 \______| \______/  |__| \__|     |__|     | _| `._____| \______/  |_______||_______||_______|| _| `._____|

"""

class ArduinoController(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ArduinoController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # for abbreviation bc if changed, objects are reinstantiated anyways
        self.task = self.parent().task
        self.task_folder = Path(self.parent().profile['tasks_folder']).joinpath(self.task)
        self.task_config = self.parent().task_config['Arduino']

        # TODO here: copy these variables to the temp vars path and overwrite the path here
        # then - all operations should be done on this

        # VariableController
        self.vars_path = self.task_folder.joinpath('Arduino','src',self.task_config['var_fname'])
        Df = functions.parse_arduino_vars(self.vars_path)
        self.VariableController = ArduinoVariablesWidget(self,Df)

        path = self.task_folder.joinpath('Arduino','src','event_codes.h')
        Df = functions.parse_code_map(path)
        self.code_map = dict(zip(Df['code'], Df['name']))

        # take care of the kids
        self.Children = [self.VariableController]

        # signals
        self.Signals = Signals()
        # self.Signals.serial_data_available.connect(self.parse_line)
        self.Data = pd.DataFrame(columns=['code','t','name'])

        self.stopped = False
        self.reprogram = True

        self.initUI()
    
    def initUI(self):
        # the formlayout
        self.FormLayout = QtWidgets.QFormLayout()
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # reprogram
        self.reprogramCheckBox = QtWidgets.QCheckBox("reupload sketch")
        self.reprogramCheckBox.setChecked(True)
        self.reprogramCheckBox.stateChanged.connect(self.reprogramCheckBox_changed)
        self.FormLayout.addRow(self.reprogramCheckBox)

        # get com ports and ini selector
        # com_ports = self.get_com_ports()
        # TODO is this UI element required? Yes if you want to run multiple box from one computer
        # self.ComPortChoiceWidget = Widgets.StringChoiceWidget(self, choices=com_ports) 
        # self.ComPortChoiceWidget.currentIndexChanged.connect(self.com_port_changed)
        
        # try to set with previously used port
        # try:
        #     last_port = self.task_config['com_port']
        #     ind = [s.split(':')[0] for s in com_ports].index(last_port)
        #     self.ComPortChoiceWidget.set_value(com_ports[ind])
        # except ValueError:
        #     pass
        
        # self.FormLayout.addRow('Arduino COM port', self.ComPortChoiceWidget)

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

        # the children
        # open serial monitor
        self.SerialMonitor = SerialMonitorWidget(self)
        self.Children.append(self.SerialMonitor)

        # Statemachine Monitor
        self.StateMachineMonitor = StateMachineMonitorWidget(self)
        self.Children.append(self.StateMachineMonitor)

        self.layout()
        self.show()

    def keyPressEvent(self, event):
        """ reimplementation to send single keystrokes
        makes keyboardinteraction widget useless"""
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

    # def get_com_ports(self):
    #     """ returns com ports with descriptors : separated """
    #     command = ' '.join([self.parent().profiles['General']['platformio_cmd'],"device","list"])
    #     return_value = subprocess.check_output(command,shell=True).decode('utf-8')

    #     lines = [line.strip() for line in return_value.split(os.linesep)]

    #     # os agnostic parser - not really bc
    #     com_ports = []
    #     for i,line in enumerate(lines):
    #         if line.startswith('COM') or '/dev/tty' in line:
    #             com_port = line
    #             descr = lines[i+3].split('Description: ')[1]
    #             com_ports.append(':'.join([com_port,descr]))

    #     return com_ports

    # def com_port_changed(self):
    #     # for logging only
    #     self.task_config['com_port'] = self.ComPortChoiceWidget.get_value()
    #     print("Arduino COM port: "+self.task_config['com_port'])

    # FUTURE TODO implement baud rate selector

    def reprogramCheckBox_changed(self):
        if self.reprogramCheckBox.checkState() == 2:
            self.reprogram = True
        else:
            self.reprogram = False

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
        print(" --- generating interface --- ")
        interface_generator.run(self.vars_path)
     
        # uploading code onto arduino
        # replace whatever com port is in the platformio.ini
        # with the one from task config
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
            # self.VariableController.write_variables(os.path.join('src',self.task_config['var_fname']))

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
        """ establish connection with the board """
        
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

        # log code
        if self.parent().logging:
            self.log_task(folder)

        # upload
        if self.reprogram:
            self.upload()
        else:
            print(" --- resetting arduino only --- reusing previous sketch --- ")

        # connect to serial port
        self.connection = self.connect()      

        # open file for writing
        if self.parent().logging:
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
                        if self.parent().logging:
                            fH.write(line+os.linesep) # external logging
                        
                        # publishing data
                        self.Signals.serial_data_available.emit(line)
                except:
                    # fails when port not open
                    # FIXME CHECK if this will also fail on failed reads!
                    break

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start() # apparently this line is not passed, thread hangs here? if yes,then why multithreading at all???

    def parse_line(self,line):
        if not line.startswith('<'):
            code,t = line.strip().split('\t')
            name = self.code_map[code]
            data = pd.DataFrame([[code,t,name]],columns=['code','t','name'])
            data['t'] = data['t'].astype('float')

            self.Data = self.Data.append(data)

    def closeEvent(self, event):

        # take care of ending the threads
        self.stopped = True
        # self.thread.join()

        # overwrite logged arduino vars file
        if self.parent().logging:
            try:
                target = self.run_folder.joinpath(self.task)
                self.VariableController.write_variables(target.joinpath('Arduino','src',self.task_config['var_fname']))
            except AttributeError:
                # FIXME this is hacked in bc closeEvent is fired when task is changed -> crashes
                pass

        # if serial connection is open, close it
        if hasattr(self,'connection'):
            self.connection.close()
            self.SerialMonitor.close()
        self.VariableController.close()

        # read in original task config
        task_config = configparser.ConfigParser()
        task_config_path = self.task_folder.joinpath("task_config.ini")
        task_config.read(task_config_path)
        

        # these are obsolete currently, as there is no way to change things in the task config interactively
        # could be interesting to keep it though in order to run several boxes from one computer

        # update all changes in this section
        # for key,value in self.task_config.items():
            # task_config.set('Arduino',key,value)

        # com port: remove descriptor
        # task_config.set('Arduino','com_port',self.task_config['com_port'].split(':')[0])

        # write it
        # if self.parent().logging:
        #     with open(task_config_path, 'w') as task_config_fH:
        #         task_config.write(task_config_fH)
        #     print("logging arduino section of task config to :", task_config_path)

        # remove everything that is written nontheless
        if not self.parent().logging:
            shutil.rmtree(self.run_folder)

        for child in self.Children:
            child.close()
        self.close()
    
    def stop(self):
        """ when session is finished """
        self.send('CMD HALT')
        self.RunBtn.setText('RUN')
        self.RunBtn.setStyleSheet("background-color: green")
    pass


"""
____    ____  ___      .______       __       ___      .______    __       _______     _______.
\   \  /   / /   \     |   _  \     |  |     /   \     |   _  \  |  |     |   ____|   /       |
 \   \/   / /  ^  \    |  |_)  |    |  |    /  ^  \    |  |_)  | |  |     |  |__     |   (----`
  \      / /  /_\  \   |      /     |  |   /  /_\  \   |   _  <  |  |     |   __|     \   \
   \    / /  _____  \  |  |\  \----.|  |  /  _____  \  |  |_)  | |  `----.|  |____.----)   |
    \__/ /__/     \__\ | _| `._____||__| /__/     \__\ |______/  |_______||_______|_______/

"""

class ArduinoVariablesWidget(QtWidgets.QWidget):
    """ displayes and allows for online editing of variables """

    def __init__(self, parent, Df):
        super(ArduinoVariablesWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Df = Df
        self.initUI()

    def initUI(self):
        # contains a scroll area which contains the scroll widget
        self.ScrollArea = QtWidgets.QScrollArea()
        self.ScrollWidget = QtWidgets.QWidget()

        # scroll widget has the layout etc
        self.VariableEditWidget = Widgets.ValueEditFormLayout(self,DataFrame=self.Df)

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

    def write_variables(self,path):
        """ writes current arduino variables to the path """
        # TODO add some interesting header info
        # day of training
        # day / time of writing this should already be in file?
        # animal ID

        header = []
        header.append("// ---  file automatically generated by TaskControl --- ")
        header.append("//Animal: "+self.parent().parent().animal)
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
        if hasattr(self.parent(),'connection'):
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
        ThisSettingsWidget = self.parent().parent()

        try:
            current_animal_folder = Path(ThisSettingsWidget.profile['animals_folder']).joinpath(ThisSettingsWidget.animal)
            sessions_df = utils.get_sessions(current_animal_folder)
            previous_sessions = sessions_df.groupby('task').get_group(ThisSettingsWidget.task)

            prev_session_path = Path(previous_sessions.iloc[-1]['path'])
            prev_vars_path = prev_session_path.joinpath(ThisSettingsWidget.task,self.parent().task_config['pio_project_folder'],'src',self.parent().task_config['var_fname'])
            
            prev_vars = functions.parse_arduino_vars(prev_vars_path)

            self.VariableEditWidget.set_entries(prev_vars)
           
        except KeyError:
            print("trying to use last vars, but animal has not been run on this task before.")

"""
.___  ___.   ______   .__   __.  __  .___________.  ______   .______
|   \/   |  /  __  \  |  \ |  | |  | |           | /  __  \  |   _  \
|  \  /  | |  |  |  | |   \|  | |  | `---|  |----`|  |  |  | |  |_)  |
|  |\/|  | |  |  |  | |  . `  | |  |     |  |     |  |  |  | |      /
|  |  |  | |  `--'  | |  |\   | |  |     |  |     |  `--'  | |  |\  \----.
|__|  |__|  \______/  |__| \__| |__|     |__|      \______/  | _| `._____|

"""

class SerialMonitorWidget(QtWidgets.QWidget):
    """ just print the lines from the arduino into this window
    open upon connect and received data
    """

    def __init__(self, parent):
        super(SerialMonitorWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()
        self.lines = []

        # connect to parent signals
        parent.Signals.serial_data_available.connect(self.update)

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
        # self.TextBrowser.setPlainText('initialized\n')
        self.setWindowTitle("Arduino monitor")
        self.show()
        self.layout()

    # def layout(self):
    #     small_gap = int(self.parent().parent().profiles['General']['small_gap'])
    #     big_gap = int(self.parent().parent().profiles['General']['big_gap'])

    #     functions.scale_Widgets([self, self.parent()])
    #     functions.tile_Widgets(self, self.parent().VariableController, where='below',gap=big_gap)

    def update(self,line):
        # almost none of this should be here - this is a monitor!
        try:
            # if report
            if line.startswith('<'):
                if line[1:-1].split(' ')[0] == 'VAR':
                    cmd,var,value = line[1:-1].split(' ')
                    Df = self.parent().VariableController.VariableEditWidget.get_entries()
                    Df.index = Df.name
                    Df.loc[var,'value'] = int(value)
                    Df.reset_index(drop=True,inplace=True)
                    self.parent().VariableController.VariableEditWidget.set_entries(Df)

            # if decodeable, replace
            code = line.split('\t')[0]
            decoded = self.parent().StateMachineMonitor.code_map[code]
            line = '\t'.join([decoded,line.split('\t')[1]])

            # update counters
            if decoded == 'TRIAL_COMPLETED_EVENT' or decoded == 'TRIAL_ABORTED_EVENT':
                TrialCounter = self.parent().parent().TrialCounter
                vals = [int(v) for v in TrialCounter.text().split('\t')[0].split('/')]
                if decoded == 'TRIAL_COMPLETED_EVENT':
                    vals[0] += 1
                    vals[2] += 1
                if decoded == 'TRIAL_ABORTED_EVENT':
                    vals[1] += 1
                    vals[2] += 1

                new_frac = sp.around(vals[0]/vals[2],2)
                TrialCounter.setText('/'.join([str(v) for v in vals]) + '\t' + str(new_frac))

            if decoded == 'REWARD_COLLECTED_EVENT':
                amount = int(self.parent().parent().WaterCounter.text())
                VarsDf = self.parent().VariableController.VariableEditWidget.get_entries()

                if 'reward_magnitude' in VarsDf['name'].values:
                    VarsDf.index = VarsDf.name
                    amount += VarsDf.loc['reward_magnitude','value']
                    self.parent().parent().WaterCounter.setText(str(int(amount)))

        except:
            # print("SerialMon update failed on line: ",line)
            pass

        # TODO make sure this doesn't stay like this ... 
        history_len = 100 # FIXME expose this property? or remove it. for now for debugging

        if len(self.lines) < history_len:
            self.lines.append(line)
        else:
            self.lines.append(line)
            self.lines = self.lines[1:]

        # print lines in window
        sb = self.TextBrowser.verticalScrollBar()
        sb_prev_value = sb.value()
        self.TextBrowser.setPlainText('\n'.join(self.lines[-history_len:]))

        # scroll to end
        # BUG does not work!
        # if self.update_CheckBox.checkState() == 2:
        #     sb.setValue(sb.maximum())
        # else:
        #     sb.setValue(sb_prev_value)


class StateMachineMonitorWidget(QtWidgets.QWidget):
    """ has colored fields for the states """
    def __init__(self,parent):
        super(StateMachineMonitorWidget, self).__init__(parent=parent)

        path = self.parent().task_folder.joinpath('Arduino','src','event_codes.h')
        self.Df = functions.parse_code_map(path)
        self.code_map = dict(zip(self.Df['code'].values, self.Df['name'].values))

        # connect to parent signals
        parent.Signals.serial_data_available.connect(self.update)

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
                # Btn.setCheckable(True)
                self.States_Layout.addWidget(Btn)
            if kind == 'ON':
                Btn.setCheckable(False)
                self.Spans_Layout.addWidget(Btn)
            if kind == 'EVENT':
                Btn.setCheckable(False)
                self.Events_Layout.addWidget(Btn)

            self.Btns.append((full_name,Btn))

        self.Layout.addLayout(self.States_Layout)
        for i in range(self.States_Layout.count()):
            state = self.States_Layout.itemAt(i).widget().text()
            # https://stackoverflow.com/a/42945033/4749250
            self.States_Layout.itemAt(i).widget().clicked.connect(partial(self.set_state,state))

        self.Layout.addLayout(self.Spans_Layout)
        self.Layout.addLayout(self.Events_Layout)

        self.setLayout(self.Layout)
        self.setWindowTitle("State Machine Monitor")

        self.show()
    
    # in this case it becomes a controller ... 
    def set_state(self, state):
        # does not fully work bc the state entry function is not called
        # fugly
        # also, are those part of the interface?
        code = self.Df.loc[self.Df['name'] == state+'_STATE']['code'].values[0]
        cmd = "SET current_state "+code
        self.parent().send(cmd)

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
