import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import Widgets
import utils
import subprocess
import datetime
from pathlib import Path
import shutil
import socket 
import struct
import threading
import queue
import functions
import serial
import scipy as sp
import time

import pyqtgraph as pg 

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

class LoadCellController(QtWidgets.QWidget):
    """ as this is entirely a processing 'node' it can have a central run method that is put in a seperate thread
    this run listens continuously on incoming data, on udp, rescales the values and puts it to other upd port 
    OR attempt first: put is on a signal 
    DisplayController then connects to this
    """

    def __init__(self, parent):
        super(LoadCellController, self).__init__(parent=parent)
        print("LC initialized")
        self.setWindowFlags(QtCore.Qt.Window)
        self.parent = parent
        
        self.task_config = parent.task_config['LoadCell']
        
        self.Signals = Signals()
        self.Signals.process_signal.connect(self.process_data) # potential FIXME - put data on the signal?

        self.X_last = sp.zeros(2)
        self.t_last = 0
        self.v_last = sp.zeros(2)

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Loadcell controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        self.transmission = False
        self.arduino_bridge = self.connect()

        # dummy button
        self.Btn = QtWidgets.QPushButton()
        self.Btn.setText('transmission is off')
        self.Btn.setCheckable(True)
        # self.Btn.setStyleSheet("background-color:  red")
        self.Btn.clicked.connect(self.toggle_transmission)

        self.Layout.addWidget(self.Btn)
        self.setLayout(self.Layout)
        self.show()        

    def toggle_transmission(self):
        if self.transmission:
            self.transmission = False
            self.Btn.setText('transmission is off')
        else: 
            self.transmission = True
            self.Btn.setText('transmission is on')

    def connect(self):
        """ establish connection with the arduino bridge """
        # FIXME hardcode included! this needs to be fixed
        # likely in the future: seperate uart line
        
        com_port = '/dev/ttyACM1'
        baud_rate = 115200
        try:
            print("initializing serial port: "+com_port)
            ser = serial.Serial(port=com_port, baudrate=baud_rate,timeout=2)
            ser.setDTR(False) # reset: https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial
            time.sleep(1) # sleep timeout length to drop all data
            ser.flushInput() # 
            ser.setDTR(True)
            print(" ... done")
            return ser

        except:
            print("could not connect to the Arduino bridge!")
            sys.exit()


    def Run(self, folder):
        # needs to be called after the Run of BonsaiController running Harp

        UDP_IP, UDP_PORT = self.task_config['udp'].split(':')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.bind((UDP_IP, int(UDP_PORT)))
        sock.setblocking(False) # non-blocking mode: recv doesn't receive data, exception is raised
        # well this might in the end be a bit pointless: first I set it to non-blocking to raise and 
        # exception and then I let it pass w/o doing anything. Verify if necessary
        
        self.queue = queue.Queue()

        def udp_reader(queue):
            while True:
                try:
                    # t,Fx,Fy = self.upd_connection.recv(int,float,float) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai
                    # F = sp.array([Fx,Fy])
                    # queue.put((F,t))

                    raw_read = sock.recv(12) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai

                    # utils.debug_trace()
                    t,Fx,Fy = struct.unpack('fff',raw_read)

                    queue.put((t,sp.array([Fx,Fy])))

                    self.Signals.process_signal.emit()
                    # TODO this could also be solved with passing the data with the signal instead of the queue,
                    # but this is intuitively xpected to be faster as less overhead
                    # and nobody needs to have access to the raw data anyways (really?)

                except BlockingIOError:
                    pass
        
        th_read = threading.Thread(target=udp_reader, args=(self.queue, ))
        th_read.start()

    def process_data(self):
        t,Fm = self.queue.get()
        
        # physical cursor implementation
        m = 1 # mass
        lam = 0.9 # friction factor

        dt = t - self.t_last
        dv = Fm/m * dt

        v = self.v_last + dv

        # friction
        Ff = v*-1*lam
        dv = Ff/m * dt

        v = v + dv

        self.X = self.X_last + v * dt

        self.t_last = t
        self.v_last = v

        
        # friction as a force acting in the opposite direction of F and proportional to v
        # F_f = mu * v
        # F_ges = F_f + F_meas

        if self.transmission:
            # TODO check the order of these two - delays wrt timing
            # emit signal for DisplayController
            self.Signals.loadcell_data_available.emit(self.X[0],self.X[1])
            # send coordinates to Arduino via second serial (currently arduino uart bridge)
            cmd = struct.pack("ff",self.X[0],self.X[1])
            cmd = str.encode('[') + cmd + str.encode(']')
            self.arduino_bridge.write(cmd)


        
class DisplayController(QtWidgets.QWidget):
    """
    brainstorm states:
    idle: dark screen, discarding any command that is not setting it into run
    run: listen to serial port and update the circle according to received x and y
    """

    def __init__(self, parent):
        super(DisplayController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # here all the other stuff goes in from the computer downstairs ... 

        parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
        parent.LoadCellController.Signals.loadcell_data_available.connect(self.on_lc_data)

        self.state = "IDLE"
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Display controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # dummy button
        Btn = QtWidgets.QPushButton('dummy')
        # sketch selector? not really wanted actually ... 
        
        # Display and aesthetics
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.disableAutoRange()
        # self.plot_widget.hideAxis('left')
        # self.plot_widget.hideAxis('bottom')
        self.plot_widget.setYRange(-10,10)
        self.plot_widget.setAspectLocked(True)
        # self.plot_widget.showGrid(x=True,y=True,alpha=0.5)
        self.plot_widget.showGrid(x=True,y=True)
        self.cursor = self.plot_widget.plot(x=[0],y=[0], pen=(200,200,200), symbolBrush=(100,100,100), symbolPen='w',symbolSize=50)

        self.Layout.addWidget(Btn)
        self.Layout.addWidget(self.plot_widget)
        self.setLayout(self.Layout)
        self.show()        

    def on_lc_data(self,x,y):
        """ update display """
        # if self.state == "RUN":
        self.cursor.setData(x=[x],y=[y])
        pass

    def on_serial(self,line):
        """
        define how command sent from arduino to here should look like
        GET SET CMD RET
        OR: replys go flanked by [ ] // alrady used by sending raw data now
        if line.split() ... 
        """
        if line.startswith('<') and line.endswith('>'):
            read = line[1:-1].split(' ')
            if read[0] == "RET" and read[1] == "DISPLAY":
                if read[2] == "STATE":
                    self.state = read[3]
                    # self.set_state(read[3])

                # if read[2] == "TARGET":
                #     x,y = read[3:]
                #     self.draw_target(x,y)
                # if read[2] == "RGB":
                #     R,G,B = read[3:]
                #     self.set_monochrome(r,g,b)
                # if read[2] == "GRATING":
                #     f,phi,v = read[3:]
                #     self.draw_grating(f,phi,v)
                # if read[2] == "SYNC":
                # flash corner for sync
                
        pass

    def Run(self, folder):
        pass


""" copy paste working script from the computer downstairs """
# ###
# import sys, os
# import configparser

# # from PyQt5 import QtWidgets
# # run the application

# from pyqtgraph.Qt import QtGui, QtCore
# import pyqtgraph as pg

# display_for_mouse = True

# app = QtGui.QApplication([])

# pg.setConfigOptions(antialias=True)

# # cont view
# Plot_Cont_Widget = pg.PlotWidget() # A GraphicsView
# Plot_Cont = Plot_Cont_Widget.window() # a PlotWindow

# # yes, this is weird and I don't get it. This was empirically done ... 
# Plot_Cont.show()
# if display_for_mouse==False:

#     # get screens
#     displays = app.screens()

#     x = displays[0].geometry().width()
#     Plot_Cont.move(QtCore.QPoint(x,0))
#     Plot_Cont.windowHandle().setScreen(displays[1])
#     Plot_Cont_Widget.showFullScreen() # maximises on screen 1

# # deco
# Plot_Cont.hideAxis('left')
# Plot_Cont.hideAxis('bottom')
# Plot_Cont.setAspectLocked(True)
# Plot_Cont.setYRange(-10,10)
# Plot_Cont.showGrid(x=True,y=True,alpha=0.5)
# Plot_Cont.plot(x=[0],y=[0], pen=(200,200,200), symbolBrush=(100,100,100), symbolPen='w',symbolSize=50)

# app.exec_()
