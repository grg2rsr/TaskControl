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
    loadcell_data_available = QtCore.pyqtSignal(float,float)
    udp_data_available = QtCore.pyqtSignal(float,float,float)

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
        print("LC initialized")
        self.setWindowFlags(QtCore.Qt.Window)
        # self.parent = parent
        
        self.task_config = parent.task_config['LoadCell']
        
        self.Signals = Signals()
        self.Signals.udp_data_available.connect(self.process_data)
        self.parent().ArduinoController.Signals.serial_data_available.connect(self.on_serial)

        self.X_last = sp.zeros(2)
        self.v_last = sp.zeros(2)
        self.t_last = 0
        self.Fx_off = 0
        self.Fy_off = 0

        self.Buffer = sp.zeros((100,2))

        self.stopped = False

        self.LoadCellMonitor = LoadCellMonitor(self)
        self.init_udp_server()
        self.initUI()

    def init_udp_server(self):
        self.UDP_IP_out, self.UDP_PORT_out = self.task_config['udp_out'].split(':')
        self.udp_out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # sock.bind((UDP_IP, int(UDP_PORT)))

    def initUI(self):
        self.setWindowTitle("Loadcell controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # the 2nd serial (uart) serial connection to the arduino for writing raw data back
        self.arduino_2nd_ser = self.connect()

        # transmission toggle button
        self.transmission = False
        self.udp_out_transmission = True
        self.Btn = QtWidgets.QPushButton()
        self.Btn.setText('transmission is off')
        self.Btn.setCheckable(True)
        self.Btn.setStyleSheet("background-color:  light gray")
        self.Btn.clicked.connect(self.toggle_transmission)

        self.ZeroBtn = QtWidgets.QPushButton()
        self.ZeroBtn.setText("read baseline values")
        self.ZeroBtn.clicked.connect(self.zero)

        self.Layout.addWidget(self.Btn)
        self.Layout.addWidget(self.ZeroBtn)
        self.setLayout(self.Layout)
        self.show()        

    def zero(self):
        self.Fx_off, self.Fy_off = sp.average(self.Buffer,0)

    def toggle_transmission(self):
        if self.transmission:
            self.transmission = False
            self.Btn.setText('transmission is off')
            self.Btn.setStyleSheet("background-color:  light gray")
        else: 
            self.transmission = True
            self.Btn.setText('transmission is on')
            self.Btn.setStyleSheet("background-color:  green")

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
        # needs to be called after the Run of BonsaiController running Harp

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
                    # raw_read = sock.recv(12) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai
                    raw_read = sock.recv(24) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai
                    t,Fx,Fy = struct.unpack('>ddd',raw_read)
                    # Fx *= -1
                    self.Signals.udp_data_available.emit(t,Fx,Fy)

                except BlockingIOError:
                    pass
        
        self.th_read = threading.Thread(target=udp_reader)
        self.th_read.start()

    def process_data(self,t,Fx,Fy):
        # FIXME this needs to be tested / reworked ... 

        self.Buffer = sp.roll(self.Buffer,-1,0)
        self.Buffer[-1,:] = [Fx,Fy]

        Fx -= self.Fx_off
        Fy -= self.Fy_off

        Fm = sp.array([Fx,Fy])
        
        # physical cursor implementation
        m = 20 # mass
        lam = 1000 # friction factor

        # friction as a force acting in the opposite direction of F and proportional to v
        Ff = self.v_last*lam*-1

        Fges = Fm+Ff

        # dt = t - self.t_last # to catch first data sample error
        # if dt > 0.05:
        #     dt = 0.01
        dt = 0.01

        dv = Fges/m * dt

        v = self.v_last + dv

        self.X = self.X_last + v * dt
        self.X = sp.clip(self.X,-10,10)

        self.t_last = t
        self.v_last = v
        self.X_last = self.X

        self.send()

    def send(self):
        ba = struct.pack("ff",self.X[1],self.X[0]) # FIXME INVERSION
        if self.transmission:
            # emit signal for DisplayController
            self.Signals.loadcell_data_available.emit(*self.X)
            # send coordinates to Arduino via second serial
            cmd = str.encode('[') + ba + str.encode(']')
            self.arduino_2nd_ser.write(cmd)
            # TODO check the order of these two - delays wrt timing

        # send via udp
        if self.udp_out_transmission:
            self.udp_out_sock.sendto(ba, (self.UDP_IP_out, int(self.UDP_PORT_out)))

    def on_serial(self,line):
        if line.startswith('<'):
            read = line[1:-1].split(' ')
            if read[0] == "RET" and read[1] == "LOADCELL":
                if read[2] == "CURSOR_RESET":
                    self.v_last = sp.array([0,0])
                    self.X_last = sp.array([0,0])
                    self.X = sp.array([0,0])
                    self.send()
                            
    def closeEvent(self, event):
        # if serial connection is open, close it
        if hasattr(self,'arduino_2nd_ser'):
            self.arduino_2nd_ser.close()

        self.stopped = True
        # self.th_read.join()
        self.close()

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

        parent.Signals.udp_data_available.connect(self.on_udp_data)
        parent.Signals.loadcell_data_available.connect(self.on_lc_data)

        # self.N_history = 100
        self.lc_raw_data = sp.zeros((300,3)) # FIXME hardcode hardcode history length
        self.lc_data = sp.zeros((300,2))

        self.initUI()

    def initUI(self):
        self.setWindowTitle("LoadCell Monitor")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="LoadCell raw data monitor")

        self.PlotItemFB = self.PlotWindow.addPlot(title='front / back')
        self.LineFB = self.PlotItemFB.plot(x=sp.arange(300), y=self.lc_raw_data[:,1], pen=(200,200,200))
        self.PlotItemFB_pp = self.PlotWindow.addPlot(title='front / back')
        self.LineFB_pp = self.PlotItemFB_pp.plot(x=sp.arange(300), y=self.lc_data[:,0], pen=(200,100,100))
        self.PlotItemFB_pp.setYRange(-10,10)

        self.PlotWindow.nextRow()

        self.PlotItemLR = self.PlotWindow.addPlot(title='left / right')
        self.LineLR = self.PlotItemLR.plot(x=sp.arange(300), y=self.lc_raw_data[:,2], pen=(200,200,200))
        self.PlotItemLR_pp = self.PlotWindow.addPlot(title='left / right')
        self.LineLR_pp = self.PlotItemLR_pp.plot(x=sp.arange(300), y=self.lc_data[:,1], pen=(200,100,100))
        self.PlotItemLR_pp.setYRange(-10,10)

        # # Display and aesthetics
        # self.PlotWindow = pg.GraphicsWindow(title="LoadCell raw data monitor")
        # self.PlotItemFB = self.PlotWindow.addPlot(title='front / back')
        # # self.LineFB = self.PlotItemFB.plot(x=self.lc_raw_data[:,0], y=self.lc_raw_data[:,1], pen=(200,200,200))
        # # self.LineFB_pp = pg.PlotCurveItem(x=self.lc_raw_data[:,0], y=self.lc_data[:,0], pen=(200,100,100))
        # self.LineFB = self.PlotItemFB.plot(x=sp.arange(300), y=self.lc_raw_data[:,1], pen=(200,200,200))
        # self.LineFB_pp = pg.PlotCurveItem(x=sp.arange(300), y=self.lc_data[:,0], pen=(200,100,100))
        # self.PlotItemFB.addItem(self.LineFB_pp)

        # self.PlotWindow.nextRow()
        # self.PlotItemLR = self.PlotWindow.addPlot(title='left / right')
        # self.LineLR = self.PlotItemLR.plot(x=sp.arange(300), y=self.lc_raw_data[:,2], pen=(200,200,200))
        # self.LineLR_pp = pg.PlotCurveItem(x=sp.arange(300), y=self.lc_data[:,1], pen=(200,100,100))
        # self.PlotItemLR.addItem(self.LineLR_pp)

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()        

    def on_udp_data(self,t,x,y):
        """ update display """
        self.lc_raw_data = sp.roll(self.lc_raw_data,-1,0)
        self.lc_raw_data[-1,:] = [t,x,y]

        self.lc_raw_data[-1,1] -= self.parent().Fx_off
        self.lc_raw_data[-1,2] -= self.parent().Fy_off

        # self.LineFB.setData(x=self.lc_raw_data[:,0], y=self.lc_raw_data[:,1])
        # self.LineLR.setData(x=self.lc_raw_data[:,0], y=self.lc_raw_data[:,2])
        self.LineLR.setData(y=self.lc_raw_data[:,2])
        self.LineFB.setData(y=self.lc_raw_data[:,1])

    def on_lc_data(self,x,y):
        self.lc_data = sp.roll(self.lc_data,-1,0)
        self.lc_data[-1,:] = [x,y]
        self.LineFB_pp.setData(y=self.lc_data[:,0])
        self.LineLR_pp.setData(y=self.lc_data[:,1])

    def closeEvent(self, event):
        # stub
        self.close()

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
        parent.LoadCellController.Signals.loadcell_data_available.connect(self.on_lc_data)

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
#         parent.LoadCellController.Signals.loadcell_data_available.connect(self.on_lc_data)

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