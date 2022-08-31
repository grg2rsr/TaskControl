import sys, os
from PyQt5 import QtWidgets
from PyQt5 import QtGui, QtCore

import serial
import time
import threading

from Utils import utils

""" 
NOTES
bare minimum: more a monitor than a controller
can be converted into a serial logger?
"""

class SerialConnection(QtCore.QObject):
    """ reads in a seperate thread, publishes data """
    data_available = QtCore.pyqtSignal(str)
    
    def __init__(self, parent, com_port, baud_rate):
        super(SerialConnection, self).__init__(parent=parent)
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.name = "%s-serial" % parent.name

    def connect(self):
        try:
            utils.printer("connecting %s on port %s - %i: " % (self.name, self.com_port, self.baud_rate), 'msg')
            self.connection = serial.Serial(
                                port=self.com_port,
                                baudrate=self.baud_rate,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=1,
                                xonxoff=0,
                                rtscts=0
                                )

        except:
            utils.printer("failed to connect %s on port %s - %i" % (self.name, self.com_port, self.baud_rate), 'error')
            self.connection = None
            pass

        return self.connection

    def listen(self):
        def read_from_port(ser):
            while ser.is_open:
                try:
                    line = ser.readline().decode('utf-8').strip()
                except AttributeError:
                    line = ''
                except TypeError:
                    line = ''
                except serial.serialutil.SerialException:
                    line = ''
                except UnicodeDecodeError:
                    line = ''

                if line != '': # filtering out empty reads
                    self.data_available.emit(line) # publishing

        self.thread = threading.Thread(target=read_from_port, args=(self.connection, ))
        self.thread.start()
        utils.printer("listening to %s on port %s - %i" % (self.name, self.com_port, self.baud_rate))

    def reset(self):
        self.connection.setDTR(False) # reset
        time.sleep(1) # sleep timeout length to drop all data
        self.connection.flushInput()
        self.connection.setDTR(True)

    def disconnect(self):
        """ closes """
        if self.connection.is_open:
            self.connection.close()


class SerialMonitorWidget(QtWidgets.QWidget):
    """ """

    def __init__(self, parent, SerialConnection=None, display_filter=None):
        super(SerialMonitorWidget, self).__init__(parent=parent)
        self.name = "%s-monitor" % self.parent().name
        self.setWindowFlags(QtCore.Qt.Window)
        self.lines = []
        self.display_filter = display_filter

        # if provided, connect
        if SerialConnection is not None:
            SerialConnection.data_available.connect(self.on_data)

        self.initUI()

    def initUI(self):
        # logging checkbox
        self.Layout = QtWidgets.QVBoxLayout()
        
        # textbrowser
        self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Layout.addWidget(self.TextBrowser)

        # all
        self.setLayout(self.Layout)
        self.setWindowTitle(self.name)

        self.settings = QtCore.QSettings('TaskControl', self.name)
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def on_data(self, line):
        if self.display_filter is not None:
            if not any([f(line) for f in self.display_filter]):
                self.update(line)
        else:
            self.update(line)

    def update(self, line):
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

    def closeEvent(self, event):
        """ reimplementation of closeEvent """
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())