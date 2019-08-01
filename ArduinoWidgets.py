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

import pandas as pd

import Widgets
import functions
import utils 

class Signals(QtCore.QObject):
    # not entirely clear why this needs to be within a QObject
    # type shows difference to be signal vs bounded signal
    # FUTURE TODO read up on this at some point
    serial_data_available = QtCore.pyqtSignal()

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
        self.task_folder = os.path.join(self.parent().profile['tasks_folder'],self.task)
        self.task_config = self.parent().task_config['Arduino']

        Df = functions.parse_arduino_vars(os.path.join(self.task_folder,'Arduino','src',self.task_config['var_fname']))

        self.VariableController = ArduinoVariablesWidget(self,Df)

        # signals
        self.Signals = Signals()

        self.initUI()
    
    def initUI(self):
        # the formlayout
        self.FormLayout = QtWidgets.QFormLayout()
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # get com ports and ini selector
        com_ports = self.get_com_ports()
        self.ComPortChoiceWidget = Widgets.StringChoiceWidget(self, choices=com_ports) # TODO is this UI element required? Yes if you want to run multiple box from one computer
        self.ComPortChoiceWidget.currentIndexChanged.connect(self.com_port_changed)
        
        # try to set with previously used port
        try:
            last_port = self.task_config['com_port']
            ind = [s.split(':')[0] for s in com_ports].index(last_port)
            self.ComPortChoiceWidget.set_value(com_ports[ind])
        except ValueError:
            pass
        
        self.FormLayout.addRow('Arduino COM port', self.ComPortChoiceWidget)

        FormWidget = QtWidgets.QWidget()
        FormWidget.setLayout(self.FormLayout)

        Full_Layout = QtWidgets.QVBoxLayout()
        Full_Layout.addWidget(FormWidget)

        # reset button - left in for future reimplementation
        # Btn = QtWidgets.QPushButton()
        # Btn.setText('Reset Arduino')
        # Btn.clicked.connect(self.reset_board)
        # Full_Layout.addWidget(Btn)

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

        self.setLayout(Full_Layout)
        self.setWindowTitle("Arduino controller")

        self.show()

    def get_com_ports(self):
        """ returns com ports with descriptors : separated """
        command = ' '.join([self.parent().profiles['General']['platformio_cmd'],"device","list"])
        return_value = subprocess.check_output(command,shell=True)
        # lines = return_value.decode('utf-8').split('\n')

        # TODO check on linux system - works
        # check downstairs!

        if os.name == 'nt':
            lines = return_value.decode('utf-8').split('\r\r\n\r\r\n')

            com_ports = []
            for line in lines[:-1]:
                com_port = line.split('\r\r\n')[0]
                descr = line.split('\r\r\n')[1].split('Description: ')[1]
                com_ports.append(':'.join([com_port,descr]))

        if os.name == 'posix':
            lines = return_value.decode('utf-8').split('\n\n')

            com_ports = []
            for line in lines[:-1]:
                com_port = line.split('\n')[0]
                descr = line.split('\n')[-1]
                com_ports.append(':'.join([com_port,descr]))
                    
        # old parser - remove me when done checking above
        # com_ports = []
        # for i,line in enumerate(lines):
        #     if line.startswith('Description'):
        #         com_port = lines[i-3]
        #         descr = line.split(':')[1][1:]
        #         com_ports.append(':'.join([com_port,descr]))
                # com_ports.append(com_port)
        return com_ports

    def com_port_changed(self):
        # for logging only
        self.task_config['com_port'] = self.ComPortChoiceWidget.get_value()
        print("Arduino COM port: "+self.task_config['com_port'])

    # FUTURE TODO implement baud rate selector

    # def reset_board(self):
    #     # TODO implement - necessary?
    #     pass

    def send(self,command):
        """ sends string command interface to arduino, interface compatible """
        if hasattr(self,'connection'):
            cmd = '<'+command+'>'
            bytestr = str.encode(cmd)
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
          
        # build and log
        print("--- uploading code on arduino --- ")
        prev_cwd = os.getcwd()
        os.chdir(os.path.join(self.task_folder,self.task_config['pio_project_folder']))

        # check existence of interface.cpp, and if not, build it
        if not os.path.exists(os.path.join('src','interface.cpp')):
            print("interface.cpp not found, attempting to build it")
            os.chdir("src")
            try:
                cmd = " ".join(["python","interface_generator.py",self.task_config['var_fname']])
                subprocess.check_output(cmd,shell=True)
            except:
                print("failed at building interface.cpp. Exiting ... ")
                sys.exit()
            os.chdir(os.path.normpath(os.getcwd() + os.sep + os.pardir))

        # replace whatever com port is in the platformio.ini
        # with the one from task config
        pio_config = configparser.ConfigParser()
        pio_config.read("platformio.ini")

        for section in pio_config.sections():
            if section.split(":")[0] == "env":
                pio_config.set(section,"upload_port",self.task_config['com_port'].split(':')[0])

        # also write this
        if self.parent().logging:
            with open("platformio.ini", 'w') as fH:
                pio_config.write(fH)
        
        # get current UI arduino variables, backup defaults,
        # write the UI derived and upload those, revert after upload
        # this workaround is necessary to use the get previous variables
        # functionality ... 
        src = os.path.join('src',self.task_config['var_fname'])
        target = os.path.join('src',self.task_config['var_fname']+'_default')
        shutil.copy(src,target)
        if self.parent().logging:
            self.VariableController.write_variables(os.path.join('src',self.task_config['var_fname']))

        # upload
        fH = open(os.path.join(self.run_folder,'platformio_build_log.txt'),'w')
        platformio_cmd = self.parent().profiles['General']['platformio_cmd']
        cmd = ' '.join([platformio_cmd,'run','--target','upload'])
        proc = subprocess.Popen(cmd,shell=True,stdout=fH)
        proc.communicate()
        fH.close()

        # restore default variables in the task folder
        src = os.path.join('src',self.task_config['var_fname']+'_default')
        target = os.path.join('src',self.task_config['var_fname'])
        shutil.copy(src,target)
        os.remove(src)

        # back to previous directory
        os.chdir(prev_cwd)

    def log_task(self,folder):
        """ copy the entire arduino folder to the logging folder """
        print(" - logging arduino code")
        src = os.path.join(self.parent().profile['tasks_folder'],self.parent().task)
        target = os.path.join(folder,self.parent().task)
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
        self.upload()

        # connect to serial port
        self.connection = self.connect()

        # open serial monitor
        self.SerialMonitor = SerialMonitorWidget(self)

        # open keyboard interaction
        self.KeyboardInteraction = KeyboardInteractionWidget(self)

        # open file for writing
        if self.parent().logging:
            fH = open(os.path.join(folder,'arduino_log.txt'),'w')

        # multithreading taken from
        # https://stackoverflow.com/questions/17553543/pyserial-non-blocking-read-loop
        # general idea:
        # read from serial if data available put into queue
        # emit a signal that data came in
        # everybody that needs to do sth when new data arrives listens to that signal

        self.queue = queue.Queue()

        def read_from_port(ser,q):
            while True:
                try:
                    raw_read = ser.readline()
                    line = raw_read.decode('utf-8').strip()
                    if self.parent().logging:
                        fH.write(line+os.linesep) # external logging
                    q.put(line) # for threadsafe passing data to the SerialMonitor
                    self.Signals.serial_data_available.emit()
                except:
                    # fails when port not open
                    # FIXME CHECK if this will also fail on failed reads!
                    break

        thread = threading.Thread(target=read_from_port, args=(self.connection, self.queue))
        thread.start() # apparently this line is not passed, thread hangs here? if yes,then why multithreading at all???

    def closeEvent(self, event):
        # overwrite logged arduino vars file
        if self.parent().logging:
            try:
                target = os.path.join(self.run_folder,self.parent().task)
                self.VariableController.write_variables(os.path.join(target,'Arduino','src',self.task_config['var_fname']))        
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
        task_config_path = os.path.join(self.task_folder,"task_config.ini")
        task_config.read(task_config_path)
        
        # update all changes in this section
        for key,value in self.task_config.items():
            task_config.set('Arduino',key,value)

        # com port: remove descriptor
        task_config.set('Arduino','com_port',self.task_config['com_port'].split(':')[0])

        # write it
        if self.parent().logging:
            with open(task_config_path, 'w') as task_config_fH:
                task_config.write(task_config_fH)
            print("logging arduino section of task config to :", task_config_path)

        # remove everything that is written nontheless
        shutil.rmtree(self.run_folder)

        self.close()
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
        else:
            print("Arduino is not connected")

    def load_last_vars(self):
        """ try to get arduino variables from last run for the task 
        only loads, does not send! """
        try:
            current_animal_folder = os.path.join(self.parent().parent().profile['animals_folder'],self.parent().parent().animal)
            sessions_df = utils.get_sessions(current_animal_folder)
            previous_sessions = sessions_df.groupby('task').get_group(self.parent().parent().task)

            prev_session_path = previous_sessions.iloc[-1]['path']
            prev_vars_path = os.path.join(prev_session_path,self.parent().parent().task,self.parent().task_config['pio_project_folder'],'src',self.parent().task_config['var_fname'])
            
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
        self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Layout = QtWidgets.QHBoxLayout()
        self.Layout.addWidget(self.TextBrowser)
        self.setLayout(self.Layout)
        self.TextBrowser.setPlainText('initialized\n')
        self.setWindowTitle("Arduino monitor")
        self.show()
        functions.tile_Widgets(self, self.parent().VariableController, where='below',gap=50)
        functions.scale_Widgets([self, self.parent()])

    def update(self):
        # get data from other thread
        line = self.parent().queue.get()
        
        # filter out empty reads
        if line is not '':
            self.lines.append(line)

            # print lines in window
            self.TextBrowser.setPlainText('\n'.join(self.lines))

            # scroll to end - TODO implement pausing
            sb = self.TextBrowser.verticalScrollBar()
            sb.setValue(sb.maximum())

# TODO FUTURE implement here: state machine monitor

"""
 __  ___  ___________    ____ .______     ______        ___      .______       _______
|  |/  / |   ____\   \  /   / |   _  \   /  __  \      /   \     |   _  \     |       \
|  '  /  |  |__   \   \/   /  |  |_)  | |  |  |  |    /  ^  \    |  |_)  |    |  .--.  |
|    <   |   __|   \_    _/   |   _  <  |  |  |  |   /  /_\  \   |      /     |  |  |  |
|  .  \  |  |____    |  |     |  |_)  | |  `--'  |  /  _____  \  |  |\  \----.|  '--'  |
|__|\__\ |_______|   |__|     |______/   \______/  /__/     \__\ | _| `._____||_______/

"""

class KeyboardInteractionWidget(QtWidgets.QWidget):
    """ captures single keystrokes and sends them to the arduino """
    def __init__(self, parent):
        super(KeyboardInteractionWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()

    def initUI(self):
        self.Layout = QtWidgets.QHBoxLayout()
        Label = QtWidgets.QLabel('focus here to capture single keystrokes')
        self.Layout.addWidget(Label)
        self.setLayout(self.Layout)
        self.setWindowTitle("Keyboard interface")
        self.show()

        functions.tile_Widgets(self, self.parent().SerialMonitor, where='below',gap=50)
        functions.scale_Widgets([self, self.parent()])

    def keyPressEvent(self, event):
        self.parent().send("CMD "+event.text())
