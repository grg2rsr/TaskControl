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

# class LoadCellController(QtWidgets.QWidget):
#     """ as this is entirely a processing 'node' it can have a central run method that is put in a seperate thread
#     this run listens continuously on incoming data, on udp, rescales the values and puts it to other upd port 
#     OR attempt first: put is on a signal 
#     DisplayController then connects to this
#     """

#     def __init__(self, parent):
#         super(LoadCellController, self).__init__(parent=parent, udp_addr, udp_port)
#         self.setWindowFlags(QtCore.Qt.Window)
        
#         self.udp_info = (udp_addr, udp_port)

#         self.Signals = Signals()
#         self.Signals.process_signal.connect(self.process_data) # potential FIXME - put data on the signal?

#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle("Loadcell controller")
#         self.Layout = QtWidgets.QHBoxLayout()
#         self.setMinimumWidth(300) # FIXME hardcoded!

#         # dummy button
#         Btn = QtWidgets.QPushButton('dummy')

#         self.Layout.addWidget(Btn)
#         self.setLayout(self.Layout)
#         self.show()        

#     def Run(self):
#         # needs to be called after the Run of BonsaiController running Harp
#         addr,port = self.udp_info

#         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
#         sock.bind((UDP_IP, UDP_PORT))
#         sock.setblocking(False) # non-blocking mode: recv doesn't receive data, exception is raised
#         # well this might in the end be a bit pointless: first I set it to non-blocking to raise and 
#         # exception and then I let it pass w/o doing anything. Verify if necessary
        
#         self.queue = queue.Queue()

#         def udp_reader(queue):
#             while True:
#                 try:
#                     t,Fx,Fy = self.upd_connection.recv(int,float,float) # replace chunk size stuff with 1 int 2 floats or whatever you get from bonsai
#                     F = sp.array([Fx,Fy])
#                     queue.put((F,t))
#                     self.Signals.process_signal.emit()
#                     # TODO this could also be solved with passing the data with the signal instead of the queue,
#                     # but this is expected to be faster as less overhead

#                 except BlockingIOError:
#                     pass
        
#         th_read = threading.Thread(target=udp_reader, args=(self.queue, ))
#         th_read.start()

#     def process_data(self):
#         F,t = self.queue.get()
#         # TODO physical cursor goes here
#         x,y = F # for now just unpack
#         self.Signals.loadcell_data_available.emit(x,y)

#         # also: pack it and send it to the arduino
#         # first attempt: use SET variable structure
#         # if too slow: pass as bytes
#         # if too slow ... see doc
#         cmd = "SET X "+str(sp.around(x,5))
#         self.parent.ArduinoController.send(cmd)
#         cmd = "SET Y "+str(sp.around(y,5))
#         self.parent.ArduinoController.send(cmd)

#         # this will likely clog the line
#         # started to implement raw reader (see raw_interface.cpp)
#         # https://stackoverflow.com/a/36894176

#         import struct
#         # struct.pack("ff") etc

#         self.parent.ArduinoController.send(cmd)


        
# class DisplayController(QtWidgets.QWidget):
#     """
#     brainstorm states:
#     idle: dark screen, discarding any command that is not setting it into run
#     run: listen to serial port and update the circle according to received x and y
#     """

#     def __init__(self, parent):
#         super(DisplayController, self).__init__(parent=parent)
#         self.setWindowFlags(QtCore.Qt.Window)

#         # here all the other stuff goes in from the computer downstairs ... 

#         parent.ArduinoController.Signals.serial_data_available.connect(self.on_serial)
#         parent.LoadCellController.Signals.loadcell_data_available.connect(self.on_lc_data)

#         self.state = "IDLE"
#         self.initUI()

#     def initUI(self):
#         self.setWindowTitle("Display controller")
#         self.Layout = QtWidgets.QHBoxLayout()
#         self.setMinimumWidth(300) # FIXME hardcoded!

#         # dummy button
#         Btn = QtWidgets.QPushButton('dummy')
#         # sketch selector? not really wanted actually ... 
        
#         self.Layout.addWidget(Btn)
#         self.setLayout(self.Layout)
#         self.show()        

#     def on_lc_data(self,x,y):
#         """ update display """
#         if self.state == "RUN":
#             # update cursor pos
#             pass
#         pass

#     def on_serial(line):
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
