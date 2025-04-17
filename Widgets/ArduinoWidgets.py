import os
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import configparser
import importlib
from copy import copy

from pathlib import Path
import subprocess
import shutil
import time
import pandas as pd
import numpy as np

from Utils import utils
from scripts import interface_generator
from Utils import behavior_analysis_utils as bhv

from Widgets.UtilityWidgets import ValueEditFormLayout
from Widgets.Connections import SerialConnection, SerialMonitorWidget

import logging

logger = logging.getLogger(__name__)


class FSMSerialConnection(SerialConnection):
    """extents SerialConnection by: the hardcoded protocol of communictaion
    -> to be replaced with the more general convention of ?VAR and VAR="""

    def __init__(self, parent, com_port, baud_rate):
        super(FSMSerialConnection, self).__init__(parent, com_port, baud_rate)
        # self.name = parent.name

    def query(self, var_name):
        # here? yes - the implementation should be abstracted away in the
        # actual VariableController
        # cmd = "?%s" % var_name
        cmd = "GET %s" % var_name
        self.send(cmd)

    def send(self, command):
        """sends string command interface to arduino, interface compatible"""
        if hasattr(self, "connection"):
            if self.connection.is_open:
                cmd = "<" + command + ">"
                # bytestring conversion
                bytestr = str.encode(cmd)
                self.connection.write(bytestr)
        else:
            # TODO be more explicit what failed to be sent
            logger.error("%s is not connected" % self.name)

    def send_variable(self, name, value):
        if hasattr(self, "connection"):
            if self.connection.is_open:
                # report
                logger.info("sending variable %s: %s" % (name, value))

                # this is the hardcoded command sending definition
                # cmd = '<SET %s %s>' % (name, value)
                # cmd = "%s=%s" % (name, value) # for the future
                cmd = "SET %s %s" % (name, value)
                self.send(cmd)
                time.sleep(0.05)  # grace period to guarantee successful sending

    def run_FSM(self):
        self.send("CMD RUN")

    def halt_FSM(self):
        self.send("CMD HALT")

    def send_keystroke(self, key):
        self.send("CMD " + key)


"""
 
  #######  ##    ## ##       #### ##    ## ########       ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
 ##     ## ###   ## ##        ##  ###   ## ##            ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
 ##     ## ####  ## ##        ##  ####  ## ##           ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##        ##  ## ## ## ######      ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ##     ## ##  #### ##        ##  ##  #### ##          ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##        ##  ##   ### ##          ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
  #######  ##    ## ######## #### ##    ## ########    ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""

""" TODO
move this to it's own file
-> defines the implementation for the FSM and
should not care how that one is implemented
"""


class OnlineFSMDecoder(QtCore.QObject):
    decoded_data_available = QtCore.pyqtSignal(str)
    var_data_available = QtCore.pyqtSignal(str, str, str)
    formatted_var_data_available = QtCore.pyqtSignal(str)
    other_data_available = QtCore.pyqtSignal(str)

    def __init__(self, parent, CodesDf):
        super(OnlineFSMDecoder, self).__init__(parent=parent)
        self.name = "%s-OnlineFSMDecoder" % parent.name

        self.CodesDf = CodesDf  # required, path could be set in online analysis
        self.code_map = dict(zip(CodesDf["code"], CodesDf["name"]))

    def on_data(self, line):
        """decodes"""
        try:
            if line.startswith("<") and not line.startswith("<VAR"):
                self.other_data_available.emit(line)

            if line.startswith("<VAR"):
                line_split = line[1:-1].split(" ")
                name = line_split[1]
                value = line_split[2]
                t = line_split[3]
                self.var_data_available.emit(name, value, t)
                self.formatted_var_data_available.emit("%s=%s" % (name, value))

            if not line.startswith("<"):
                code, t = line.split("\t")
                decoded = self.code_map[code]

                # publish
                decoded_line = "\t".join([decoded, t])
                self.decoded_data_available.emit(decoded_line)
        except:
            logger.warning("could not decode line: %s" % line)


class OnlineFSMAnalyser(QtCore.QObject):
    """listens to serial port, analyzes arduino data as it comes in"""

    trial_data_available = QtCore.pyqtSignal(pd.DataFrame, pd.DataFrame)

    def __init__(self, parent, FSMDecoder, online_config=None):
        super(OnlineFSMAnalyser, self).__init__(parent=parent)
        self.parent = parent
        self.FSMDecoder = FSMDecoder
        self.online_config = online_config
        self.name = "%s-OnlineFSMAnalyser" % parent.name

        # get metrics
        try:
            metrics = [
                m.strip() for m in self.online_config["online_metrics"].split(",")
            ]
            mod = importlib.import_module(
                "Utils.user_metrics"
            )  # <- this has to be either metrics partial
            self.Metrics = [getattr(mod, metric) for metric in metrics]
        except KeyError:
            self.Metrics = None
            logger.error("%s attempted to load online metrics, but failed" % self.name)

        # events
        try:
            self.new_trial_event = self.online_config["new_trial_event"]
        except KeyError:
            self.new_trial_event = None
            logger.error("%s attempted to load new trial event, but failed" % self.name)

        try:
            self.reward_events = [
                event.strip() for event in self.online_config["reward_event"].split(",")
            ]
        except KeyError:
            self.reward_events = None
            logger.error("%s attempted to load reward event, but failed" % self.name)

        self.lines = []
        self.SessionDf = None

    def run(self):
        # needed like this because of init order
        # FIXME TODO
        # self.parent.serial_data_available.connect(self.update)
        self.FSMDecoder.decoded_data_available.connect(self.update)
        self.FSMDecoder.var_data_available.connect(self.update_var)

    def parse(self, decoded_line):
        event, t = decoded_line.split("\t")
        t = int(t)
        return event, t

    def update_var(self, name, value, t):
        line = "<VAR %s %s %s>" % (name, value, t)
        # this is the WORST hack - bringing it back to the original
        # format because the parse_lines function expects it like this ...
        self.lines.append(line)

    def update(self, decoded_line):
        self.lines.append(decoded_line)

        event, t = self.parse(decoded_line)

        # the event that separates the stream of data into chunks of trials
        if event == self.new_trial_event:
            # parse lines
            TrialMetricsDf = None
            try:
                TrialDf = bhv.parse_lines(
                    self.lines, code_map=None, parse_var=True, decoded=True
                )
                TrialMetricsDf = bhv.parse_trial(TrialDf, self.Metrics)
            except ValueError:
                logger.error("Failed to parse of lines into TrialDf")

            if TrialMetricsDf is not None:
                if self.SessionDf is None:  # on first
                    self.SessionDf = TrialMetricsDf
                else:
                    self.SessionDf = pd.concat([self.SessionDf, TrialMetricsDf])
                    self.SessionDf = self.SessionDf.reset_index(drop=True)

                # emit data
                self.trial_data_available.emit(TrialDf, TrialMetricsDf)

                # restart lines with current line
                self.lines = [decoded_line]


"""
 
  ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
 ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
 ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
 ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
 ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
  ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ## 
 
"""


class ArduinoController(QtWidgets.QWidget):
    # initialize signals
    # serial_data_available = QtCore.pyqtSignal(str)

    # for an explanation how this works and behaves see
    # here: https://programmer.group/pyqt5-quick-start-pyqt5-signal-slot-mechanism.html
    # and here: https://stackoverflow.com/questions/2970312/pyqt4-qtcore-pyqtsignal-object-has-no-attribute-connect

    def __init__(self, parent, sys_config, task_config, box_config, online_config=None):
        super(ArduinoController, self).__init__(parent=parent)
        self.name = "ArduinoController"

        # the original folder of the task
        self.task_folder = (
            Path(sys_config["paths"]["tasks_folder"]) / sys_config["current"]["task"]
        )
        self.sys_config = sys_config  # this is just the paths
        self.task_config = (
            task_config  # this is the section of the task_config.ini ['Arduino']
        )
        self.box_config = box_config  # this now holds all the connections

        # TODO remove this hardcode, external into .ini
        # also think about if this is the right place
        events_path = self.task_folder / "Arduino" / "src" / "event_codes.h"
        CodesDf = utils.parse_code_map(events_path)
        self.code_map = dict(zip(CodesDf["code"], CodesDf["name"]))

        # Online decoder - resolves the codes into the event names
        self.FSMDecoder = OnlineFSMDecoder(self, CodesDf)

        # Online analyzer - builds on top of the decoder
        # set up online data analyzer if defined in task_config
        if online_config is not None:
            self.OnlineFSMAnalyser = OnlineFSMAnalyser(
                self, self.FSMDecoder, online_config=online_config
            )

        # Serial
        com_port = self.box_config["FSM"]["com_port"]
        baud_rate = int(self.box_config["FSM"]["baud_rate"])
        self.Serial = FSMSerialConnection(self, com_port, baud_rate)
        self.SerialMonitor = SerialMonitorWidget(self)
        self.Serial.data_available.connect(self.FSMDecoder.on_data)
        self.FSMDecoder.decoded_data_available.connect(self.SerialMonitor.on_data)
        self.FSMDecoder.other_data_available.connect(self.SerialMonitor.on_data)
        self.FSMDecoder.formatted_var_data_available.connect(self.SerialMonitor.on_data)
        # self.FSMDecoder.var_data_available.connect(self.SerialMonitor.on_data)

        # VariableController
        # TODO remove this hardcode, external into .ini
        self.vars_path = self.task_folder / "Arduino" / "src" / "interface_variables.h"
        self.VariableController = ArduinoVariablesWidget(self)

        # Statemachine Monitor
        self.StateMachineMonitor = StateMachineMonitorWidget(self, self.code_map)
        self.initUI()

    def initUI(self):
        # the formlayout
        self.setWindowFlags(QtCore.Qt.Window)

        self.Layout = QtWidgets.QVBoxLayout(self)

        self.ConnectionLabel = QtWidgets.QLabel()
        self.ConnectionLabel.setText("not connected")
        self.ConnectionLabel.setStyleSheet("background-color: gray")
        self.ConnectionLabel.setAlignment(QtCore.Qt.AlignCenter)

        self.Layout.addWidget(self.ConnectionLabel)

        FormLayout = QtWidgets.QFormLayout()
        FormLayout.setVerticalSpacing(10)
        FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # reprogram
        self.reprogramCheckBox = QtWidgets.QCheckBox("reupload sketch")
        self.reprogramCheckBox.setChecked(True)
        FormLayout.addRow(self.reprogramCheckBox)

        FormWidget = QtWidgets.QWidget()
        FormWidget.setLayout(FormLayout)
        self.Layout.addWidget(FormWidget)

        # start/stop button
        self.RunBtn = QtWidgets.QPushButton()
        self.RunBtn.setStyleSheet("background-color: green")
        self.RunBtn.setCheckable(True)
        self.RunBtn.setText("Run")
        self.RunBtn.clicked.connect(self.run_btn_clicked)
        self.Layout.addWidget(self.RunBtn)

        # direct interaction
        self.SendLine = QtWidgets.QLineEdit()
        SendBtn = QtWidgets.QPushButton()
        SendBtn.setText("Send")
        SendBtn.clicked.connect(self.send_btn_clicked)
        Layout = QtWidgets.QHBoxLayout()
        Layout.addWidget(self.SendLine)
        Layout.addWidget(SendBtn)
        self.Layout.addLayout(Layout)

        # keyboard interaction
        Label = QtWidgets.QLabel("focus here to capture single keystrokes")
        self.Layout.addWidget(Label)

        self.setLayout(self.Layout)
        self.setWindowTitle("Arduino controller")

        # settings
        self.settings = QtCore.QSettings("TaskControl", "ArduinoController")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def run_btn_clicked(self):
        if self.RunBtn.isChecked():
            self.Serial.run_FSM()
            self.RunBtn.setText("HALT")
            self.RunBtn.setStyleSheet("background-color: red")
        else:
            self.Serial.halt_FSM()
            self.RunBtn.setText("RUN")
            self.RunBtn.setStyleSheet("background-color: green")

    def keyPressEvent(self, event):
        """reimplementation to send single keystrokes"""
        self.Serial.send_keystroke(event.text())

    def send_btn_clicked(self):
        """send command entered in LineEdit"""
        command = self.SendLine.text()
        self.Serial.send(command)

    def upload(self):
        """uploads the sketch specified in platformio.ini
        which is in turn specified in the task_config.ini"""

        # building interface
        logger.info("generating interface.cpp")  # _TASK_
        try:  # catch this exception for downward compatibility
            logger.info("generating interface from: %s" % self.vars_path)
            logger.info(
                "using as template: %s" % self.task_config["interface_template_fname"]
            )
            interface_template_fname = self.task_config["interface_template_fname"]
            interface_generator.run(self.vars_path, interface_template_fname)
        except KeyError:
            logger.info("generating interface based on %s" % self.vars_path)
            interface_generator.run(self.vars_path)

        # uploading code onto arduino

        # replace whatever com port is in the platformio.ini with the one from task config
        self.pio_config_path = self.task_folder / "Arduino" / "platformio.ini"
        pio_config = configparser.ConfigParser()
        pio_config.read(self.pio_config_path)

        # get upload port
        upload_port = self.box_config["FSM"]["com_port"]

        # FIXME - this works on arduino, but not for Teensy`
        for section in pio_config.sections():
            if section.split(":")[0] == "env":
                pio_config.set(section, "upload_port", upload_port)

        # write it
        with open(self.pio_config_path, "w") as fH:
            pio_config.write(fH)

        # get current UI arduino variables, backup defaults,
        # write the UI derived and upload those, revert after upload
        # this workaround is necessary to use the get previous variables
        # functionality ...

        # backing up original values
        shutil.copy(self.vars_path, self.vars_path.with_suffix(".default"))

        # setting the valve calibration factor
        logger.info("setting valve calibration factors")  # _TASK_
        if "valves" in self.box_config.sections():
            valves = dict(self.box_config["valves"]).keys()
            for valve in valves:
                try:
                    logger.info(
                        "setting calibration factor of valve: %s = %s"
                        % (valve, self.box_config["valves"][valve])
                    )
                    self.VariableController.VariableEditWidget.set_entry(
                        valve, self.box_config["valves"][valve]
                    )
                except:
                    logger.error(
                        "can't set valve calibration factors of valve %s" % valve
                    )
        else:
            logger.info("no valves found in box config")

        # overwriting vars
        self.VariableController.write_variables(self.vars_path)

        # upload
        logger.info("uploading code on arduino")  # _TASK_
        prev_dir = Path.cwd()

        os.chdir(self.task_folder / "Arduino")
        fH = open(self.run_folder / "platformio_build_log.txt", "w")
        platformio_cmd = self.sys_config["system"]["platformio_cmd"]
        cmd = " ".join([platformio_cmd, "run", "--target", "upload"])
        proc = subprocess.Popen(cmd, shell=True, stdout=fH)  # ,stderr=fH)
        proc.communicate()
        fH.close()

        os.chdir(prev_dir)

        # restoring original variables
        shutil.copy(self.vars_path.with_suffix(".default"), self.vars_path)
        os.remove(self.vars_path.with_suffix(".default"))

        logger.info("upload successful")

    def log_task(self, folder):
        """copy the entire arduino folder to the logging folder"""
        logger.info("logging arduino code")
        src = self.task_folder
        target = folder / self.sys_config["current"]["task"]
        shutil.copytree(src, target)

    def Run(self, folder):
        """folder is the logging folder"""
        # the folder that is used for storage
        self.run_folder = folder  # needs to be stored for access

        # logging the code
        self.log_task(self.run_folder)

        # upload
        if self.reprogramCheckBox.checkState() == 2:  # true when checked
            self.upload()
        else:
            logger.info("reusing previously uploaded sketch")

        # last vars
        # TODO move this to the VariableController itself?
        if (
            self.VariableController.LastVarsCheckBox.checkState() == 2
        ):  # true when checked
            last_vars = self.VariableController.load_last_vars()
            if last_vars is not None:
                current_vars = self.VariableController.Df
                if self.VariableController.check_vars(last_vars, current_vars):
                    self.VariableController.use_last_vars()
                    logger.info("using variables from last session")
                else:
                    self.VariableController.use_default_vars()
                    logger.warning(
                        "attemped use variables from last session, but they are unequal. Using default instead"
                    )
            else:
                logger.warning(
                    "attempted to use variables from last session, but couldn't find. Using default instead"
                )
        self.VariableController.VariableEditWidget.setEnabled(True)

        # connect to serial port
        self.Serial.connect()

        if self.Serial.connection is not None and self.Serial.connection.is_open:
            # UI stuff
            self.ConnectionLabel.setText("connected")
            self.ConnectionLabel.setStyleSheet("background-color: green")

            # external logging
            log_fname = self.task_config["log_fname"]
            self.log_fH = open(self.run_folder / log_fname, "w")
            self.Serial.data_available.connect(self.on_data)

            # starts the listener thread
            self.Serial.reset()
            self.Serial.listen()

        # start up the online data analyser
        if hasattr(self, "OnlineFSMAnalyser"):
            logger.info("starting online data analyser")
            self.OnlineFSMAnalyser.run()

        # start timer
        for counter in self.parent().Counters:
            if hasattr(counter, "timer"):
                counter.start()

        # now send variables
        time.sleep(3)
        self.VariableController.send_all_variables()

    def on_data(self, line):
        self.log_fH.write(line + os.linesep)

    def stop(self):
        """halts the FSM"""
        self.Serial.send("CMD HALT")
        self.RunBtn.setText("RUN")
        self.RunBtn.setStyleSheet("background-color: green")

    def closeEvent(self, event):
        # if serial connection is open, reset arduino and close it
        if hasattr(self.Serial, "connection"):
            if self.Serial.connection.is_open:
                self.Serial.disconnect()

        # explicit - should fix windows bug where arduino_log.txt is not written
        if hasattr(self, "log_fH"):
            self.log_fH.close()

        # overwrite logged arduino vars file
        if hasattr(self, "run_folder"):
            target = (
                self.run_folder
                / self.sys_config["current"]["task"]
                / "Arduino"
                / "src"
                / "interface_variables.h"
            )  # TODO FIXME HARDCODE
            if target.exists():  # bc close event is also triggered on task_changed
                self.VariableController.write_variables(target)

        # explicitly closing
        self.SerialMonitor.close()
        self.VariableController.close()
        self.StateMachineMonitor.close()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        self.close()


"""
 
 ##     ##    ###    ########  ####    ###    ########  ##       ########  ######  
 ##     ##   ## ##   ##     ##  ##    ## ##   ##     ## ##       ##       ##    ## 
 ##     ##  ##   ##  ##     ##  ##   ##   ##  ##     ## ##       ##       ##       
 ##     ## ##     ## ########   ##  ##     ## ########  ##       ######    ######  
  ##   ##  ######### ##   ##    ##  ######### ##     ## ##       ##             ## 
   ## ##   ##     ## ##    ##   ##  ##     ## ##     ## ##       ##       ##    ## 
    ###    ##     ## ##     ## #### ##     ## ########  ######## ########  ######  
 
"""


class ArduinoVariablesWidget(QtWidgets.QWidget):
    """displayes and allows for online editing of variables"""

    def __init__(self, parent):
        super(ArduinoVariablesWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Df = self.load_default_vars()
        self.sent_variables = copy(self.Df)
        self.initUI()

        # connect
        parent.FSMDecoder.var_data_available.connect(self.on_var_changed)

    def initUI(self):
        # contains a scroll area which contains the scroll widget
        self.ScrollArea = QtWidgets.QScrollArea()
        self.ScrollWidget = QtWidgets.QWidget()

        # scroll widget has the layout etc
        self.VariableEditWidget = ValueEditFormLayout(self, DataFrame=self.Df)
        self.VariableEditWidget.setEnabled(False)

        # note: the order of this seems to be of utmost importance ...
        # self.ScrollWidget.setLayout(self.VariableEditWidget)
        self.ScrollArea.setWidget(self.VariableEditWidget)

        self.Layout = QtWidgets.QVBoxLayout(self)
        self.Layout.addWidget(self.ScrollArea)

        SendBtn = QtWidgets.QPushButton(self)
        SendBtn.setText("Send")
        SendBtn.clicked.connect(self.send_btn_clicked)
        self.Layout.addWidget(SendBtn)

        # last variables functionality
        LastVarsBtn = QtWidgets.QPushButton(self)
        LastVarsBtn.setText("last session")
        LastVarsBtn.clicked.connect(self.use_last_vars)

        DefaultVarsBtn = QtWidgets.QPushButton(self)
        DefaultVarsBtn.setText("default")
        DefaultVarsBtn.clicked.connect(self.use_default_vars)
        self.LastVarsCheckBox = QtWidgets.QCheckBox("automatic last")
        self.LastVarsCheckBox.setChecked(True)
        LastVars = QtWidgets.QHBoxLayout()
        LastVars.addWidget(QtWidgets.QLabel("variables to use"))
        LastVars.addWidget(DefaultVarsBtn)
        LastVars.addWidget(LastVarsBtn)
        LastVars.addWidget(self.LastVarsCheckBox)
        self.Layout.addLayout(LastVars)

        self.setLayout(self.Layout)

        self.setWindowTitle("Arduino variables")

        self.settings = QtCore.QSettings("TaskControl", "ArduinoVariablesController")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def load_default_vars(self):
        # contains the hardcoded path
        vars_path = (
            self.parent().task_folder / "Arduino" / "src" / "interface_variables.h"
        )
        try:
            default_vars = utils.parse_arduino_vars(vars_path)
            return default_vars
        except:
            logger.error("failed to load default variables")
            return None

    def load_last_vars(self):
        """try to get arduino variables from last run for the task
        only loads, does not send!"""
        sys_config = self.parent().sys_config  # FIXME !!!

        folder = (
            Path(sys_config["paths"]["animals_folder"])
            / sys_config["current"]["animal"]
        )
        SessionsDf = utils.get_sessions(folder)

        try:
            previous_sessions = SessionsDf.groupby("task").get_group(
                sys_config["current"]["task"]
            )
        except KeyError:
            logger.error(
                "trying to use last vars, but animal has not been run on this task before."
            )
            return None

        # to allow for this functionalty while task is running
        if self.parent().parent().is_running:
            ix = -2
        else:
            ix = -1

        try:
            prev_session_path = Path(previous_sessions.iloc[ix]["path"])
            prev_vars_path = (
                prev_session_path
                / sys_config["current"]["task"]
                / "Arduino"
                / "src"
                / "interface_variables.h"
            )
            if prev_vars_path.exists():
                prev_vars = utils.parse_arduino_vars(prev_vars_path)
                return prev_vars
            else:
                logger.error("didn't find variables from last session")
                return None

        except IndexError:
            # thrown when there is no previous session
            return None

    def check_vars(self, Df_a, Df_b):
        # number of variables are not the same
        if Df_a.shape[0] != Df_b.shape[0]:
            logger.error("unequal variable names between last session and this session")
            return False
        # variables have different names
        if not np.all(
            Df_a["name"].sort_values().values == Df_b["name"].sort_values().values
        ):
            logger.error("equal number of variables, but different names")
            return False
        else:
            return True

    def get_changed_vars(self):
        Df = self.VariableEditWidget.get_entries()
        binds = (Df["value"] != self.sent_variables["value"]).values
        return self.Df.loc[binds]["name"].values

    def write_variables(self, path):
        """writes current arduino variables to the path"""
        # get the model
        Df = self.VariableEditWidget.get_entries()

        # convert it to arduino compatible
        lines = utils.Df2arduino_vars(Df)

        # write it
        with open(path, "w") as fH:
            fH.writelines(lines)

    def send_variable(self, name, value):
        # send
        self.parent().Serial.send_variable(name, value)

        # store
        self.sent_variables.loc[self.sent_variables["name"] == name, "value"] = value

    def send_variables(self, names):
        """sending only the variables in names"""
        for name in names:
            row = self.VariableEditWidget.get_entry(name)
            self.send_variable(row["name"], row["value"])

    def send_all_variables(self):
        """sending all variables"""
        Df = self.VariableEditWidget.get_entries()
        for i, row in Df.iterrows():
            self.send_variable(row["name"], row["value"])

    def send_btn_clicked(self):
        changed_vars = self.get_changed_vars()
        self.send_variables(changed_vars)

    def use_vars(self, Df, ignore_calib=True):
        # does not send
        # ignoring valve calib
        if ignore_calib:
            Df_ = Df.loc[["ul_ms" not in name for name in Df["name"]]]
            self.VariableEditWidget.set_entries(Df_)
        else:
            self.VariableEditWidget.set_entries(Df)

    def use_last_vars(self):
        last_vars = self.load_last_vars()
        self.use_vars(last_vars)

    def use_default_vars(self):
        default_vars = self.load_default_vars()
        self.LastVarsCheckBox.setChecked(False)
        self.use_vars(default_vars)

    def on_var_changed(self, name, value, t):
        if name in self.VariableEditWidget.Df["name"].values:
            self.VariableEditWidget.set_entry(name, value)

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())


"""
 
 ##     ##  #######  ##    ## #### ########  #######  ########  
 ###   ### ##     ## ###   ##  ##     ##    ##     ## ##     ## 
 #### #### ##     ## ####  ##  ##     ##    ##     ## ##     ## 
 ## ### ## ##     ## ## ## ##  ##     ##    ##     ## ########  
 ##     ## ##     ## ##  ####  ##     ##    ##     ## ##   ##   
 ##     ## ##     ## ##   ###  ##     ##    ##     ## ##    ##  
 ##     ##  #######  ##    ## ####    ##     #######  ##     ## 
 
"""


class StateMachineMonitorWidget(QtWidgets.QWidget):
    def __init__(self, parent, code_map=None):
        super(StateMachineMonitorWidget, self).__init__(parent=parent)
        self.code_map = code_map

        # connect to parent signals
        parent.FSMDecoder.decoded_data_available.connect(self.on_data)

        self.initUI()

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.Window)

        # layouting
        self.Layout = QtWidgets.QVBoxLayout()
        self.States_Layout = QtWidgets.QHBoxLayout()
        self.Btns = []

        for code, full_name in self.code_map.items():
            splits = full_name.split("_")
            name = "_".join(splits[:-1])
            kind = splits[-1]

            Btn = QtWidgets.QPushButton()
            Btn.setText(name)
            if kind == "STATE":
                Btn.setCheckable(False)
                self.States_Layout.addWidget(Btn)

            self.Btns.append((full_name, Btn))

        self.Layout.addLayout(self.States_Layout)

        self.setLayout(self.Layout)
        self.setWindowTitle("State Machine Monitor")

        self.settings = QtCore.QSettings("TaskControl", "StateMachineMonitor")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

        self.show()

    def on_data(self, line):
        try:
            name, time = line.split("\t")
            # for states
            if name.endswith("_STATE"):
                # color all state buttons gray
                for _, btn in self.Btns:
                    # if name_.endswith("_STATE"):
                    btn.setStyleSheet("background-color: light gray")

                # and color only active green
                btn = [btn for name_, btn in self.Btns if name_ == name][0]
                btn.setStyleSheet("background-color: green")

        except:
            logging.warning(
                "StateMachineMonitorWidget does not know what to do with line %s" % line
            )
            pass

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
