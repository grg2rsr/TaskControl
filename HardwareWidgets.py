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
    processed_lc_data_available = QtCore.pyqtSignal(float,float)
    raw_lc_data_available = QtCore.pyqtSignal(float,float,float)

"""
.______     ______   .__   __.      _______.     ___       __
|   _  \   /  __  \  |  \ |  |     /       |    /   \     |  |
|  |_)  | |  |  |  | |   \|  |    |   (----`   /  ^  \    |  |
|   _  <  |  |  |  | |  . `  |     \   \      /  /_\  \   |  |
|  |_)  | |  `--'  | |  |\   | .----)   |    /  _____  \  |  |
|______/   \______/  |__| \__| |_______/    /__/     \__\ |__|

"""

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
        
        self.Layout.addWidget(Btn)
        self.setLayout(self.Layout)
        self.show()

    def layout(self):
        # nothing to do ... 
        pass

    def Run(self,folder):
        """ folder is the logging folder """

        animal = self.parent().animal
        task = self.parent().task
        task_config = self.parent().task_config['Bonsai']
        task_folder = Path(self.parent().profile['tasks_folder']).joinpath(task)
        out_path = folder.joinpath('bonsai_') # this needs to be fixed in bonsai # FIXME TODO
       
        # constructing the bonsai exe string
        parameters = "-p:save_path=\""+str(out_path)+"\""
        if 'com_port' in task_config.keys():
            parameters = parameters+" -p:com_port="+task_config['com_port']

        bonsai_exe = Path(self.parent().profiles['General']['bonsai_cmd'])
        bonsai_workflow = task_folder.joinpath('Bonsai',task_config['workflow_fname'])

        command = ' '.join([str(bonsai_exe),str(bonsai_workflow),"--start",parameters,"&"])

        print("bonsai command:")
        print(command)

        theproc = subprocess.Popen(command, shell = True)
        # theproc.communicate() # this hangs shell on windows machines, TODO check if this is true for linux
        # curious, it should do the opposite ... 

    pass

    def closeEvent(self, event):
        # stub
        self.close()

    def stop(self):
        """ """
        pass

"""
 __        ______        ___       _______   ______  _______  __       __
|  |      /  __  \      /   \     |       \ /      ||   ____||  |     |  |
|  |     |  |  |  |    /  ^  \    |  .--.  |  ,----'|  |__   |  |     |  |
|  |     |  |  |  |   /  /_\  \   |  |  |  |  |     |   __|  |  |     |  |
|  `----.|  `--'  |  /  _____  \  |  '--'  |  `----.|  |____ |  `----.|  `----.
|_______| \______/  /__/     \__\ |_______/ \______||_______||_______||_______|

"""
class LoadCellController(QtWidgets.QWidget):
    """ 
    gets data from bonsai on a udp port
    processed data is written to a udp port? for display controller
    sending data back to Task controlling arduino (via uart bridge)
    """

    def __init__(self, parent):
        super(LoadCellController, self).__init__(parent=parent)
        self.task_config = parent.task_config['LoadCell']
       
        # signals related - TODO check how this could be set up more efficiently        
        self.Signals = Signals()
        self.Signals.raw_lc_data_available.connect(self.on_data)
        self.parent().ArduinoController.Signals.serial_data_available.connect(self.on_serial)

        # data related
        self.Buffer = sp.zeros((100,2))
        self.X_last = sp.zeros(2)
        self.v_last = sp.zeros(2)
        self.t_last = 0
        self.Fx_off = 0
        self.Fy_off = 0

        self.stopped = False

        # LC monitor
        self.LoadCellMonitor = LoadCellMonitor(self)

        # the 2nd serial (uart) serial connection to the arduino for writing processed data back
        self.arduino_2nd_ser = self.connect()

        self.initUI()
        print("LC initialized")

    def initUI(self):
        self.setWindowTitle("Loadcell controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!
        self.setWindowFlags(QtCore.Qt.Window)

        self.ZeroBtn = QtWidgets.QPushButton()
        self.ZeroBtn.setText("remove offset")
        self.ZeroBtn.clicked.connect(self.zero)

        self.Layout.addWidget(self.ZeroBtn)
        self.setLayout(self.Layout)
        self.show()        

    def zero(self):
        """ remove offset from signal by subtracting the average """
        self.Fx_off, self.Fy_off = sp.average(self.Buffer,0)

    def connect(self):
        """ establish connection for raw serial data sending to the arduino via com_port2 """
        com_port = self.parent().task_config['Arduino']['com_port2']
        baud_rate = self.parent().task_config['Arduino']['baud_rate']

        try:
            print("initializing 2nd serial port to arduino: " + com_port)
            ser = serial.Serial(port=com_port, baudrate=baud_rate, timeout=2)
            ser.setDTR(False) # reset: https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial
            time.sleep(1) # sleep timeout length to drop all data
            ser.flushInput() # 
            ser.setDTR(True)
            print(" ... done")
            return ser

        except:
            print("could not open 2nd serial connection to the arduino!")
            sys.exit()


    def Run(self, folder):
        """ note: needs to be called after the Run of BonsaiController running Harp 
        why?
        """

        # connect to the bonsai UDP server serving LC raw force data
        UDP_IP, UDP_PORT = self.task_config['udp_in'].split(':')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.bind((UDP_IP, int(UDP_PORT)))
        sock.setblocking(False) # non-blocking mode: recv doesn't receive data, exception is raised
        # well this might in the end be a bit pointless: first I set it to non-blocking to raise and 
        # exception and then I let it pass w/o doing anything. Verify if necessary
        
        def udp_reader():
            while not self.stopped:
                try:
                    # read data and publish it via a qt signal
                    raw_read = sock.recv(24) # getting three floats from bonsai
                    t,Fx,Fy = struct.unpack('>ddd',raw_read)
                    self.Signals.raw_lc_data_available.emit(t,Fx,Fy)
                except BlockingIOError:
                    pass
        
        # start a the udp reader in a seperate thread
        self.th_read = threading.Thread(target=udp_reader)
        self.th_read.start()

    def on_data(self,t,Fx,Fy):
        """ called when UDP payload with raw force data is received """

        # store data
        self.Buffer = sp.roll(self.Buffer,-1,0)
        self.Buffer[-1,:] = [Fx,Fy]

        # remove offset
        Fx -= self.Fx_off
        Fy -= self.Fy_off

        Fm = sp.array([Fx,Fy])
        
        # # physical cursor
        # m = 20 # mass
        # lam = 1000 # friction factor

        # # friction as a force acting in the opposite direction of F and proportional to v
        # Ff = self.v_last*lam*-1

        # Fges = Fm+Ff

        # # dt = t - self.t_last # to catch first data sample error
        # # if dt > 0.05:
        # #     dt = 0.01
        # dt = 0.01 # this depends on the bonsai sketch

        # dv = Fges/m * dt

        # v = self.v_last + dv

        # self.X = self.X_last + v * dt
        # self.X = sp.clip(self.X,-10,10)

        # self.t_last = t
        # self.v_last = v
        # self.X_last = self.X

        # send the processed data to arduino
        # ba = struct.pack("ff",self.X[0],self.X[1])
        # self.Signals.processed_lc_data_available.emit(*self.X)

        # emit signal for DisplayController
        self.Signals.processed_lc_data_available.emit(Fx, Fy)

        # send coordinates to Arduino via second serial
        ba = struct.pack("ff",Fx,Fy)
        cmd = str.encode('[') + ba + str.encode(']')
        self.arduino_2nd_ser.write(cmd)
        
    def on_serial(self,line):
        if line.startswith('<'):
            read = line[1:-1].split(' ')
            if read[0] == "MSG" and read[1] == "LOADCELL":
                if read[2] == "REMOVE_OFFSET":
                    self.zero()
                # if read[2] == "CURSOR_RESET":
                #     self.v_last = sp.array([0,0])
                #     self.X_last = sp.array([0,0])
                #     self.X = sp.array([0,0])
        pass

                            
    def closeEvent(self, event):
        # if serial connection is open, close it
        if hasattr(self,'arduino_2nd_ser'):
            self.arduino_2nd_ser.close()
        
        # close UDP server?

        # stop reader thread
        self.stopped = True
        self.close()

    def stop(self):
        pass

"""
.___  ___.   ______   .__   __.  __  .___________.  ______   .______
|   \/   |  /  __  \  |  \ |  | |  | |           | /  __  \  |   _  \
|  \  /  | |  |  |  | |   \|  | |  | `---|  |----`|  |  |  | |  |_)  |
|  |\/|  | |  |  |  | |  . `  | |  |     |  |     |  |  |  | |      /
|  |  |  | |  `--'  | |  |\   | |  |     |  |     |  `--'  | |  |\  \----.
|__|  |__|  \______/  |__| \__| |__|     |__|      \______/  | _| `._____|

"""

class LoadCellMonitor(QtWidgets.QWidget):
    """
    
    """
    def __init__(self, parent):
        super(LoadCellMonitor, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        parent.Signals.raw_lc_data_available.connect(self.on_udp_data)
        # parent.Signals.processed_lc_data_available.connect(self.on_lc_data)

        self.lc_raw_data = sp.zeros((100,2)) # FIXME hardcode hardcode history length
        # self.lc_data = sp.zeros((300,2))

        self.initUI()

    def initUI(self):
        self.setWindowTitle("LoadCell Monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="LoadCell raw data monitor")

        self.PlotItem = pg.PlotItem()
        self.PlotWindow.addItem(self.PlotItem)
        self.PlotItem.disableAutoRange()
        self.PlotItem.setYRange(-10000,10000)
        self.PlotItem.setAspectLocked(True)
        self.PlotItem.showGrid(x=True,y=True)
        self.cursor = self.PlotItem.plot(x=[0], y=[0],
                                         pen=(255,255,255), symbolBrush=(255,255,255),
                                         symbolPen='w', symbolSize=20)

        n_hist = self.lc_raw_data.shape[0]
        self.cursor_hist = self.PlotItem.plot(x=sp.zeros(n_hist), y=sp.zeros(n_hist), pen=pg.mkPen((255,255,255), width=2, alpha=0.5))

        # adding the threshold as lines
        pen = pg.mkPen((255,255,255,100), width=1)
        self.PlotItem.addItem(pg.InfiniteLine(pos=2000, pen=pen))
        self.PlotItem.addItem(pg.InfiniteLine(pos=-2000, pen=pen))
        self.PlotItem.addItem(pg.InfiniteLine(pos=2000, pen=pen, angle=0))
        self.PlotItem.addItem(pg.InfiniteLine(pos=-2000, pen=pen, angle=0))

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()

    def on_udp_data(self,t,x,y):
        """ update display """
        self.cursor.setData(x=[x-self.parent().Fx_off], 
                            y=[y-self.parent().Fy_off])

        self.lc_raw_data = sp.roll(self.lc_raw_data,-1,0)
        self.lc_raw_data[-1,:] = [x,y]

        self.cursor_hist.setData(x=self.lc_raw_data[:,0]-self.parent().Fx_off,
                                 y=self.lc_raw_data[:,1]-self.parent().Fy_off)

    def closeEvent(self, event):
        # stub
        self.close()



"""
 _______   __       _______..______    __          ___   ____    ____
|       \ |  |     /       ||   _  \  |  |        /   \  \   \  /   /
|  .--.  ||  |    |   (----`|  |_)  | |  |       /  ^  \  \   \/   /
|  |  |  ||  |     \   \    |   ___/  |  |      /  /_\  \  \_    _/
|  '--'  ||  | .----)   |   |  |      |  `----./  _____  \   |  |
|_______/ |__| |_______/    | _|      |_______/__/     \__\  |__|

"""
        
class DisplayController(QtWidgets.QWidget):
    """
    brainstorm states:
    idle: dark screen, discarding any command that is not setting it into run
    run: listen to serial port and update the circle according to received x and y
    """

    def __init__(self, parent):
        super(DisplayController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)

        # connecting to the relevant signals
        parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
        parent.LoadCellController.Signals.processed_lc_data_available.connect(self.on_lc_data)

        self.state = "IDLE"
        self.display_for_mouse = True
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Display controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!
        
        # Display and aesthetics # TODO !!!
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.disableAutoRange()
        self.plot_widget.hideAxis('left')
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.setYRange(-10,10)
        self.plot_widget.setAspectLocked(True)
        # self.plot_widget.showGrid(x=True,y=True,alpha=0.5)
        # self.plot_widget.showGrid(x=True,y=True)
        self.cursor = self.plot_widget.plot(x=[self.parent().LoadCellController.X_last[0]],
                                            y=[self.parent().LoadCellController.X_last[1]],
                                            pen=(255,255,255), symbolBrush=(255,255,255),
                                            symbolPen='w', symbolSize=150)

        self.Layout.addWidget(self.plot_widget)
        self.setLayout(self.Layout)
        
        self.show()

        # if self.display_for_mouse==True:
        #     # get screens
        #     app = self.parent().main
        #     displays = app.screens()

        #     x = displays[0].geometry().width()
        #     # utils.debug_trace()
            
        #     self.move(QtCore.QPoint(x,0))
        #     self.windowHandle().setScreen(displays[1])
        #     self.showFullScreen() # maximises on screen 1

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
        # stub
        # 
        pass

    def closeEvent(self, event):
        # stub
        self.close()


# psychopy
  
# from psychopy import visual, core, monitors
# from psychopy.visual.windowwarp import Warper

# class DisplayControllerPP(QtWidgets.QWidget):

#     def __init__(self, parent):

#         super(DisplayControllerPP, self).__init__(parent=parent)
#         self.setWindowFlags(QtCore.Qt.Window)

#         # here all the other stuff goes in from the computer downstairs ... 

#         parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
#         parent.LoadCellController.Signals.processed_lc_data_available.connect(self.on_lc_data)

#         self.state = "IDLE"
#         self.display_for_mouse = True
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle("Display controller")
#         self.Layout = QtWidgets.QHBoxLayout()
#         self.setMinimumWidth(300) # FIXME hardcoded!

#         # self.Layout.addWidget(self.plot_widget)
#         self.setLayout(self.Layout)
        
        
#         self.mon = monitors.Monitor(name="display",width=10,distance=5)#fetch the most recent calib for this monitor

#         self.win = visual.Window(size=[1024,768], monitor=self.mon, screen=0, fullscr=False, useFBO=True)

#         # warper = Warper(win,
#         #                 warp='spherical',
#         #                 warpfile = "",
#         #                 warpGridsize = 128,
#         #                 eyepoint = [0.5, 0.5],
#         #                 flipHorizontal = False,
#         #                 flipVertical = False)

#         # Setup stimulus
#         self.gabor = visual.GratingStim(self.win, tex='sin', mask='gauss', sf=5, name='gabor', autoLog=False, size=3)

#         self.show()

#     def on_lc_data(self,x,y):
#         """ update display """
#         self.gabor.pos = [x,y]
#         self.gabor.draw()
#         self.win.flip()
#         pass

#     def on_serial(self,line):
#         """
#         define how command sent from arduino to here should look like
#         GET SET CMD RET
#         OR: replys go flanked by [ ] // alrady used by sending raw data now
#         if line.split() ... 
#         """
#         if line.startswith('<') and line.endswith('>'):
#             read = line[1:-1].split(' ')
#             if read[0] == "RET" and read[1] == "DISPLAY":
#                 if read[2] == "STATE":
#                     self.state = read[3]
#                     # self.set_state(read[3])

#                 # if read[2] == "TARGET":
#                 #     x,y = read[3:]
#                 #     self.draw_target(x,y)
#                 # if read[2] == "RGB":
#                 #     R,G,B = read[3:]
#                 #     self.set_monochrome(r,g,b)
#                 # if read[2] == "GRATING":
#                 #     f,phi,v = read[3:]
#                 #     self.draw_grating(f,phi,v)
#                 # if read[2] == "SYNC":
#                 # flash corner for sync
                
#         pass

#     def Run(self, folder):
#         # stub
#         # 
#         pass

#     def closeEvent(self, event):
#         # stub
#         self.close()