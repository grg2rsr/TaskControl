import sys
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import socket
import struct
import threading
import serial
import scipy as sp
import time

import pyqtgraph as pg

import logging

logger = logging.getLogger(__name__)

"""
 
  ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
 ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
 ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
 ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
  ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ## 
 
"""

# class LoadCellController(UPDconnection)

"""
loadcell controller uses an UDP connection
all the reading is done there

explicitly needs to know how many loadcells are attached
UPD monitor

"""


class LoadCellController(QtWidgets.QWidget):
    """
    gets data from bonsai on a udp port
    processed data is written to a udp port? for display controller
    sending data back to Task controlling arduino (via uart bridge)
    """

    processed_lc_data_available = QtCore.pyqtSignal(float, float)
    raw_lc_data_available = QtCore.pyqtSignal(float, float, float)

    def __init__(self, parent, config, task_config):
        super(LoadCellController, self).__init__(parent=parent)
        self.name = "LoadCellController"
        self.config = config
        self.task_config = task_config

        # signals related
        self.raw_lc_data_available.connect(self.on_data)
        parent.ArduinoController.serial_data_available.connect(self.on_serial)

        # data related
        self.Buffer = sp.zeros((1000, 2))
        self.X_last = sp.zeros(2)
        self.v_last = sp.zeros(2)
        self.t_last = 0
        self.Fx_off = 0
        self.Fy_off = 0

        self.stopped = False

        # LC monitor
        self.Monitor2d = LoadCellMonitor(self)

        # the 2nd serial (uart) serial connection to the arduino for writing processed data back
        self.arduino_2nd_ser = self.connect()

        # take care of the Children
        self.Children = [self.Monitor2d]

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Loadcell controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300)  # FIXME hardcoded!
        self.setWindowFlags(QtCore.Qt.Window)

        self.ZeroBtn = QtWidgets.QPushButton()
        self.ZeroBtn.setText("remove offset")
        self.ZeroBtn.clicked.connect(self.zero)

        self.Layout.addWidget(self.ZeroBtn)
        self.setLayout(self.Layout)
        self.show()

    # def layout(self):
    #     """ position children to myself """
    #     gap = int(self.config['ui']['big_gap'])

    #     utils.scale_Widgets([self] + self.Children) # dirty hack to not scale the state machine monitor
    #     utils.tile_Widgets([self] + self.Children, how="vertically", gap=gap)

    def zero(self):
        """remove offset from signal by subtracting the average"""
        self.Fx_off, self.Fy_off = sp.average(self.Buffer, 0)

    def connect(self):
        """establish connection for raw serial data sending to the arduino via com_port2"""
        com_port = self.config["connections"]["arduino_data_port"]
        baud_rate = self.config["connections"]["arduino_baud_rate"]

        logger.info("initializing 2nd serial port to arduino: " + com_port)
        try:
            ser = serial.Serial(port=com_port, baudrate=baud_rate, timeout=2)
            ser.setDTR(
                False
            )  # reset: https://stackoverflow.com/questions/21073086/wait-on-arduino-auto-reset-using-pyserial
            time.sleep(1)  # sleep timeout length to drop all data
            ser.flushInput()  #
            ser.setDTR(True)
            return ser

        except:
            logger.error("Could not open 2nd serial connection to the arduino!")
            sys.exit()

    def Run(self, folder):
        """note: needs to be called after the Run of BonsaiController running Harp
        why?
        """

        # connect to the bonsai UDP server serving LC raw force data
        UDP_IP, UDP_PORT = self.task_config["udp_in"].split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        sock.bind((UDP_IP, int(UDP_PORT)))
        sock.setblocking(
            False
        )  # non-blocking mode: recv doesn't receive data, exception is raised
        # well this might in the end be a bit pointless: first I set it to non-blocking to raise and
        # exception and then I let it pass w/o doing anything. Verify if necessary

        def udp_reader():
            while not self.stopped:
                try:
                    # read data and publish it via a qt signal
                    raw_read = sock.recv(24)  # getting three floats from bonsai
                    t, Fx, Fy = struct.unpack(">ddd", raw_read)
                    self.raw_lc_data_available.emit(t, Fx, Fy)
                except BlockingIOError:
                    pass

        # start a the udp reader in a seperate thread
        self.th_read = threading.Thread(target=udp_reader)
        self.th_read.start()

    def on_data(self, t, Fx, Fy):
        """called when UDP payload with raw force data is received"""

        # store data
        self.Buffer = sp.roll(self.Buffer, -1, 0)
        self.Buffer[-1, :] = [Fx, Fy]

        # calculate offset
        self.Fx_off, self.Fy_off = sp.median(self.Buffer, 0)

        # remove offset
        Fx -= self.Fx_off
        Fy -= self.Fy_off

        Fm = sp.array([Fx, Fy])

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
        # Fx = Fx / 1e3
        # Fy = Fy / 1e3

        self.processed_lc_data_available.emit(Fx, Fy)

        # send coordinates to Arduino via second serial
        ba = struct.pack("ff", Fx, Fy)
        cmd = str.encode("[") + ba + str.encode("]")

        if self.arduino_2nd_ser.is_open:
            self.arduino_2nd_ser.write(cmd)

    def on_serial(self, line):
        """listens to the arduino MSGs"""
        if line.startswith("<"):
            read = line[1:-1].split(" ")
            if read[0] == "MSG" and read[1] == "LOADCELL":
                if read[2] == "REMOVE_OFFSET":
                    # self.zero()
                    pass
                # if read[2] == "CURSOR_RESET":
                #     self.v_last = sp.array([0,0])
                #     self.X_last = sp.array([0,0])
                #     self.X = sp.array([0,0])
        pass

    def closeEvent(self, event):
        # if serial connection is open, close it
        if hasattr(self, "arduino_2nd_ser"):
            self.arduino_2nd_ser.close()

        # close UDP server?

        # stop reader thread
        self.stopped = True

        # close children
        for child in self.Children:
            child.close()

        self.close()

    def stop(self):
        # automatically converts bonsai_harp_log.bin to bonsai_harp_log.csv
        # _ = subprocess.Popen(self.config['system']['csv_converter_cmd']) # runs Harp GUI

        # csv_converter_cmd = Path(self.config['system']['csv_converter_cmd'])
        # input_path = csv_converter_cmd.parent / 'CsvConverter.Interface' / 'input_file.txt'

        # cmd_lines = ["1, " + str(self.run_folder / 'bonsai_harp_log.bin'),'200, true']

        # with open(input_path,'w') as fH:
        #     fH.writelines(cmd_lines)

        # TODO automatically close converter GUI
        # _.terminate()

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


class LoadCellMonitor(QtWidgets.QWidget):
    """ """

    def __init__(self, parent):
        super(LoadCellMonitor, self).__init__(parent=parent)
        self.Controller = parent
        self.setWindowFlags(QtCore.Qt.Window)

        self.Controller.raw_lc_data_available.connect(self.on_udp_data)
        self.Controller.parent().ArduinoController.serial_data_available.connect(
            self.on_serial
        )

        self.lc_raw_data = sp.zeros((100, 2))  # FIXME hardcode hardcode history length

        self.initUI()

    def initUI(self):
        self.setWindowTitle("LoadCell Monitor")
        self.Layout = QtWidgets.QHBoxLayout()

        self.resize(300, 300)  # FIXME hardcoded!
        # self.setHeight(250) # FIXME hardcoded!

        # Display and aesthetics
        self.PlotWindow = pg.GraphicsWindow(title="LoadCell raw data monitor")

        self.PlotItem = pg.PlotItem()
        self.PlotWindow.addItem(self.PlotItem)
        self.PlotItem.disableAutoRange()
        self.PlotItem.setYRange(-8000, 8000)
        self.PlotItem.setAspectLocked(True)
        self.PlotItem.showGrid(x=True, y=True)
        self.cursor = self.PlotItem.plot(
            x=[0],
            y=[0],
            pen=(255, 255, 255),
            symbolBrush=(255, 255, 255),
            symbolPen="w",
            symbolSize=20,
        )

        self.cursor_raw = self.PlotItem.plot(
            x=[0],
            y=[0],
            pen=(100, 100, 100),
            symbolBrush=(100, 100, 100),
            symbolSize=10,
        )

        n_hist = self.lc_raw_data.shape[0]
        self.cursor_hist = self.PlotItem.plot(
            x=sp.zeros(n_hist),
            y=sp.zeros(n_hist),
            pen=pg.mkPen((255, 255, 255), width=2, alpha=0.5),
        )

        # adding the threshold as lines
        pen = pg.mkPen((255, 255, 255, 100), width=1)
        self.lim_lines = {}
        self.lim_lines["right"] = pg.InfiniteLine(pos=2500, pen=pen)
        self.lim_lines["left"] = pg.InfiniteLine(pos=-2500, pen=pen)

        # fix box
        self.fix_box_line = self.PlotItem.plot(
            x=[1000, -1000, -1000, 1000, 1000],
            y=[1000, 1000, -1000, -1000, 1000],
            pen=pen,
        )

        # self.lim_lines['front'] = pg.InfiniteLine(pos=5000, pen=pen, angle=0)
        # self.lim_lines['back'] = pg.InfiniteLine(pos=-5000, pen=pen, angle=0)

        for k, v in self.lim_lines.items():
            self.PlotItem.addItem(v)

        self.Layout.addWidget(self.PlotWindow)
        self.setLayout(self.Layout)
        self.show()

    def on_udp_data(self, t, x, y):
        """update display"""
        self.cursor.setData(
            x=[x - self.Controller.Fx_off], y=[y - self.Controller.Fy_off]
        )

        self.cursor_raw.setData(x=[x], y=[y])

        self.lc_raw_data = sp.roll(self.lc_raw_data, -1, 0)
        self.lc_raw_data[-1, :] = [x, y]

        self.cursor_hist.setData(
            x=self.lc_raw_data[:, 0] - self.Controller.Fx_off,
            y=self.lc_raw_data[:, 1] - self.Controller.Fy_off,
        )

    def closeEvent(self, event):
        # stub
        self.close()

    def on_serial(self, line):
        """listens to the arduino, updates variable line"""

        if line.startswith("<VAR"):
            name = line[1:-1].split(" ")[1]
            value = line[1:-1].split(" ")[2]
            if name == "X_thresh":
                self.lim_lines["left"].setValue(-float(value))
                self.lim_lines["right"].setValue(float(value))
            if name == "XY_fix_box":
                v = float(value)
                x = [v, -v, -v, v, v]
                y = [v, v, -v, -v, v]
                self.fix_box_line.setData(x, y)
            # if name == "Y_thresh":
            #     self.lim_lines['back'].setValue(-float(value))
            #     self.lim_lines['front'].setValue(float(value))
        pass
