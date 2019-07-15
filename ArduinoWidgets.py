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

class ArduinoController(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ArduinoController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # for abbreviation bc if changed, this class is reinstantiated anyways
        self.task = self.parent().task
        self.task_folder = os.path.join(self.parent().profile['tasks_folder'],self.task)
        self.task_config = self.parent().task_config['Arduino']

        # TODO FIXME refactor function name
        Df = functions.parse_training_vars(os.path.join(self.task_folder,'Arduino','src',self.task_config['var_fname']))

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

        # stop button
        Btn = QtWidgets.QPushButton()
        Btn.setText('Stop Arduino')
        Btn.clicked.connect(self.stop_btn_clicked)
        Full_Layout.addWidget(Btn)

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

        # TODO check on linux system
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
        if hasattr(self,'connection'):
            cmd = '<CMD '+command+'>'
            bytestr = str.encode(cmd)
            self.connection.write(bytestr)
        else:
            print("Arduino is not connected")



    def stop_btn_clicked(self):
        self.send('STOP')

    def send_btn_clicked(self):
        command = self.SendLine.text()
        self.send(command)
        
    def upload(self):
        """ uploads the sketch specified in platformio.ini
        which is in turn specified in the task_config.ini """
          
        # build and log
        print("uploading code on arduino")
        prev_cwd = os.getcwd()
        os.chdir(os.path.join(self.task_folder,self.task_config['pio_project_folder']))

        # replace whatever com port is in the platformio.ini
        # with the one from task config
        pio_config = configparser.ConfigParser()
        pio_config.read("platformio.ini")

        for section in pio_config.sections():
            if section.split(":")[0] == "env":
                pio_config.set(section,"upload_port",self.task_config['com_port'].split(':')[0])

        # also write this
        with open("platformio.ini", 'w') as fH:
            pio_config.write(fH)
        
        # os.chdir(os.path.join(folder,self.task,'Arduino'))
        fH = open('platformio_build_log.txt','w')
        platformio_cmd = self.parent().profiles['General']['platformio_cmd']
        cmd = ' '.join([platformio_cmd,'run','--target','upload'])
        proc = subprocess.Popen(cmd,shell=True,stdout=fH)
        proc.communicate()
        fH.close()
        os.chdir(prev_cwd)

    def log_task(self,folder):
        # copy the entire task folder
        print("logging arduino code")
        src = os.path.join(self.parent().profile['tasks_folder'],self.parent().task)
        target = os.path.join(folder,self.parent().task)
        shutil.copytree(src,target)
        
        # overwriting the copied default values with the values from the UI
        # TODO think about this: this essentially only leaves out all other incremental
        # changes that could have been done during the task
        # but since log is available - this could be recovered from the log
        self.VariableController.write_variables(os.path.join(target,'Arduino','src',self.task_config['var_fname']))

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

            # implement: make stuff clickable

        except:
            print("could not connect to the Arduino!")
            sys.exit()
            return 1

    def Run(self,folder):
        """ folder is the logging folder """

        # log code
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
        fH = open(os.path.join(folder,'arduino_log.txt'),'w')

        # multithreading taken from
        # https://stackoverflow.com/questions/17553543/pyserial-non-blocking-read-loop

        self.queue = queue.Queue()

        def read_from_port(ser,q):
            while True:
                try:
                    raw_read = ser.readline()
                    line = raw_read.decode('utf-8').strip()
                    fH.write(line+os.linesep) # external logging
                    q.put(line) # for threadsafe passing data to the SerialMonitor
                    self.Signals.serial_data_available.emit()
                except:
                    # fails when port not open
                    # FIXME CHECK if this will also fail on failed reads!
                    break

        thread = threading.Thread(target=read_from_port, args=(self.connection, self.queue))
        thread.start()


    def closeEvent(self, event):
        # if serial connection is open, close it
        if hasattr(self,'connection'):
            self.connection.close()
            self.SerialMonitor.close()
        self.VariableController.close()

        # read in original config
        task_config = configparser.ConfigParser()
        task_config_path = os.path.join(self.task_folder,"task_config.ini")
        task_config.read(task_config_path)
        
        # update all changes in this section
        for key,value in self.task_config.items():
            task_config.set('Arduino',key,value)

        # com port: remove descriptor
        task_config.set('Arduino','com_port',self.task_config['com_port'].split(':')[0])

        # write it
        with open(task_config_path, 'w') as task_config_fH:
            task_config.write(task_config_fH)
        
        print("logging arduino section of task config to :", task_config_path)

        self.close()
    pass


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
        self.FormLayout = QtWidgets.QFormLayout()
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
        self.set_entries(self.Df)

        # note: the order of this seems to be of utmost importance ... 
        self.ScrollWidget.setLayout(self.FormLayout)
        self.ScrollArea.setWidget(self.ScrollWidget)

        self.Layout = QtWidgets.QVBoxLayout(self)
        self.Layout.addWidget(self.ScrollArea)

        SendBtn = QtWidgets.QPushButton(self)
        SendBtn.setText('Send')
        SendBtn.clicked.connect(self.send_variables)
        self.Layout.addWidget(SendBtn)

        LastVarsBtn = QtWidgets.QPushButton(self)
        LastVarsBtn.setText('use variables from last session')
        LastVarsBtn.clicked.connect(self.use_last_vars)
        self.Layout.addWidget(LastVarsBtn)

        self.setLayout(self.Layout)

        self.setWindowTitle("Arduino variables")
        self.show()

    def set_entries(self, Df):
        # TODO move this to utilities - a Df 2 Formlayout function
        # TODO this is not a set_entries, but ini_entries function!!!
        for i, row in Df.iterrows():
            self.FormLayout.addRow(row['name'], Widgets.LineEditWidget(row['value'], functions.dtype_map[row['dtype']], self))

    def get_entries(self):
        """ returns a pd.DataFrame of the current entries """

        # TODO again here: FormLayout2Df function could be useful
        rows = []

        for i in range(self.FormLayout.rowCount()):
            label = self.FormLayout.itemAt(i, 0).widget()
            widget = self.FormLayout.itemAt(i, 1).widget()
            rows.append([label.text(), widget.get_value()])

        Df = pd.DataFrame(rows, columns=['name', 'value'])
        # NOTE: this only works when order of entries is guaranteed to stay equal, better would be to use merge
        Df = pd.concat([Df,self.Df[['dtype','const']]],axis=1) 
        return Df

    def write_variables(self,path):
        """ writes current arduino variables to the path """
        # FIXME this requires at standard for the arduino to replace
        # left as is right now to test functionality
        # I don't understand my comments anymore yay

        # TODO add some interesting header info
        # for future - this header info could be used to set the correct variables
        # for example, could contain day of training ...

        header = []
        header.append("//file automatically generated by TaskControl.py")
        header = [line+os.linesep for line in header]

        Df = self.get_entries()
        lines = functions.Df_2_arduino_vars(Df)
        with open(path, 'w') as fH:
            fH.write(''.join(header+lines))

    def send_variables(self):
        """ sends all current variables to arduino """
        Df = self.get_entries()
        for i,row in Df.iterrows():

            # this is the hardcoded command sending definition
            cmd = ' '.join(['SET',str(row['name']),str(row['value'])])
            cmd = '<'+cmd+'>'

            bytestr = str.encode(cmd)
            # reading and writing from different threads apparently threadsafe
            # https://stackoverflow.com/questions/8796800/pyserial-possible-to-write-to-serial-port-from-thread-a-do-blocking-reads-fro
            self.parent().connection.write(bytestr)

    def use_last_vars(self):
        # TODO HERE is the point where the check for the last used variables could be
        # also ... this is hideous code ... 
        try:
            current_animal_folder = os.path.join(self.parent().parent().profile['animals_folder'],self.parent().parent().animal)
            sessions_df = utils.get_sessions(current_animal_folder)
            previous_sessions = sessions_df.groupby('task').get_group(self.parent().parent().task)

            prev_session_path = previous_sessions.iloc[-1]['path']
            prev_vars_path = os.path.join(prev_session_path,self.parent().parent().task,self.parent().task_config['pio_project_folder'],'src',self.parent().task_config['var_fname'])
            
            prev_vars = functions.parse_training_vars(prev_vars_path)

            from pdb import set_trace
            QtCore.pyqtRemoveInputHook()
            set_trace()

            self.set_entries(prev_vars)
            self.send_variables()
            
        except KeyError:
            print("trying to use last vars, but animal has not been run on this task before.")

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


class KeyboardInteractionWidget(QtWidgets.QWidget):
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
        self.parent().send(event.text())
