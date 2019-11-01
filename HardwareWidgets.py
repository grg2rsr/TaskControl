import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import Widgets

import subprocess
import datetime
from pathlib import Path
import shutil

import functions

class Signals(QtCore.QObject):
    loadcell_data_available = QtCore.pyqtSignal(float,float) # FIXME see what is here the syntax
    process_signal = QtCore.pyqtSignal()

class BonsaiController(QtWidgets.QWidget):
    def __init__(self, parent):
        super(BonsaiController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Bonsai controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # dummy button
        Btn = QtWidgets.QPushButton('dummy')
        # sketch selector? not really wanted actually ... 
        
        self.Layout.addWidget(Btn)
        self.setLayout(self.Layout)
        self.show()

    def Run(self,folder):
        """ folder is the logging folder """

        animal = self.parent().animal
        task = self.parent().task
        task_config = self.parent().task_config['Bonsai']
        task_folder = os.path.join(self.parent().profile['tasks_folder'], task)
       
        fname = animal+'.raw'
        
        folder = Path(folder)
        out_path = folder.joinpath(animal+'.raw') # this needs to be fixed in bonsai

        # constructing the bonsai exe string
        parameters = "-p:save_path=\""+str(out_path)+"\""
        bonsai_exe = self.parent().profiles['General']['bonsai_cmd']
        
        bonsai_workflow = os.path.join(task_folder,'Bonsai',task_config['workflow_fname'])
        bonsai_workflow = "\""+bonsai_workflow+"\""

        command = ' '.join([str(Path(bonsai_exe)),str(Path(bonsai_workflow)),"--start",parameters,"&"])

        theproc = subprocess.Popen(command, shell = True)
        # theproc.communicate() # this hangs shell on windows machines, TODO check if this is true for linux

    pass


"""
notes: the performance of this has to be verified. if harp bonsai downsamples to 100Hz
alternative to this strategy: not emitting a signal but again writing to a local udp
"""
import threading 
import queue 

class LoadCellController(QtWidgets.QWidget):
    """ as this is entirely a processing 'node' it can have a central run method that is put in a seperate thread
    this run listens continuously on incoming data, on udp, rescales the values and puts it to other upd port 
    OR attempt first: put is on a signal 
    DisplayController then connects to this
    """

    def __init__(self, parent):
        super(LoadCellController, self).__init__(parent=parent, udp_addr, udp_port)
        self.Signals = Signals()
        self.udp_connection = self.connect(udp_addr,udp_port)
        self.run()

    def connect(self,addr,port):
        # maybe some form of handshake, verify incoming loadcell data or similar

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.bind((UDP_IP, UDP_PORT))
        sock.setblocking(False) # non-blocking mode: recv doesn't receive data, exception is raised
        # well this might in the end be a bit pointless: first I set it to non-blocking to raise and 
        # exception and then I let it pass w/o doing anything. Verify if necessary
        return sock

    def process_data(self):
        F,t = self.queue.get()
        # physical cursor goes here
        x,y = F # for now just unpack
        self.Signals.loadcell_data_available.emit(x,y)
        pass

    def run(self):
        # this still should be in a seperate thread. Otherwise this can't be taken down.

        self.queue = queue.Queue()

        def udp_reader(queue):
            while True:
                try:
                    t,Fx,Fy = self.upd_connection.recv(int,float,float) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai
                    F = sp.array([Fx,Fy])
                    queue.put((F,t))
                    self.Signals.process_signal.emit()
                    # TODO this could also be solved with passing the data with the signal instead of the queue,
                    # but this is expected to be faster as less overhead

                except BlockingIOError:
                    pass
        
        th_read = threading.Thread(target=udp_reader, args=(self.queue, ))
        th_read.start()

        
class DisplayController(QtWidgets.QWidget):
    """

    """
    def __init__(self, parent):
        super(DisplayController, self).__init__(parent=parent)

        self.state = "IDLE"

        

        # connections
        # without an explicit connect function this widget becomes sensitive to the 
        # order of instantiation (has to be after LC controller)

        parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
        parent.LoadCellController.Signals.lc_data_available.connect(self.on_lc_data)

        def set_state(self, state):
            if state == "IDLE":
                pass
            if state == "RUN":
                pass
            if state == "CLEAR":
                pass

        def on_lc_data(x,y):
            """ update display """
            if self.state == "RUN":
                # update cursor pos
                pass
            pass

        def on_serial(line):
            """
            define how command sent from arduino to here should look like
            GET SET CMD RET
            OR: replys go flanked by [ ]
            if line.split() ... 
            """
            if line.startswith('<') and line.endswith('>'):
                read = line[1:-1].split(' ')
                if read[0] == "RET" and read[1] == "DISPLAY":
                    if read[2] == "STATE":
                        self.set_state(read[3])
                    if read[2] == "TARGET":
                        x,y = read[3:]
                        self.draw_target(x,y)
                    if read[2] == "RGB":
                        R,G,B = read[3:]
                        self.set_monochrome(r,g,b)
                    if read[2] == "GRATING":
                        f,phi,v = read[3:]
                        self.draw_grating(f,phi,v)
    
            pass
