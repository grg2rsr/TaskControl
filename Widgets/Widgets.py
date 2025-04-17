import os
from datetime import datetime
import importlib


from PyQt5 import QtCore
from PyQt5 import QtWidgets

from Utils import utils


from Widgets.Popups import RunInfoPopup
from Widgets.UtilityWidgets import StringChoiceWidget, PandasModel

import logging

logger = logging.getLogger(__name__)

"""
 
 ##     ##    ###    #### ##    ##    ##      ## #### ##    ## ########   #######  ##      ## 
 ###   ###   ## ##    ##  ###   ##    ##  ##  ##  ##  ###   ## ##     ## ##     ## ##  ##  ## 
 #### ####  ##   ##   ##  ####  ##    ##  ##  ##  ##  ####  ## ##     ## ##     ## ##  ##  ## 
 ## ### ## ##     ##  ##  ## ## ##    ##  ##  ##  ##  ## ## ## ##     ## ##     ## ##  ##  ## 
 ##     ## #########  ##  ##  ####    ##  ##  ##  ##  ##  #### ##     ## ##     ## ##  ##  ## 
 ##     ## ##     ##  ##  ##   ###    ##  ##  ##  ##  ##   ### ##     ## ##     ## ##  ##  ## 
 ##     ## ##     ## #### ##    ##     ###  ###  #### ##    ## ########   #######   ###  ###  
 
"""


class SettingsWidget(QtWidgets.QWidget):
    """
    toplevel UI element that is parent of everything else
    """

    # FIXME does not have parent? - fix inheritance from TaskControl
    def __init__(self, main, config):
        super(SettingsWidget, self).__init__()
        self.name = "SettingsWidget"
        self.sys_config = config  # a configparser dict
        self.Controllers = []  # a list of all controllers
        self.Counters = []
        self.main = main  # ref to the main

        # flags
        self.is_running = False

        # Settings - to store window positions
        self.settings = QtCore.QSettings("TaskControl", "SettingsWidget")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

        #
        self.Boxes = utils.get_Boxes(self.sys_config["paths"]["boxes_folder"])
        (self.Box,) = utils.select(self.Boxes, name=self.sys_config["last"]["box"])

        self.Animals = utils.get_Animals(self.sys_config["paths"]["animals_folder"])
        (self.Animal,) = utils.select(
            self.Animals, ID=self.sys_config["last"]["animal"]
        )

        self.Tasks = utils.get_Tasks(self.sys_config["paths"]["tasks_folder"])
        (self.Task,) = utils.select(self.Tasks, name=self.sys_config["last"]["task"])

        self.initUI()

    def initUI(self):
        # positioning and deco
        self.setWindowTitle("Settings")
        self.show()

        FormLayout = QtWidgets.QFormLayout(self)
        FormLayout.setVerticalSpacing(10)
        FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
        self.setLayout(FormLayout)

        # Box selector
        self.BoxChoiceWidget = StringChoiceWidget(
            self, choices=[box.name for box in self.Boxes], default=self.Box.name
        )
        self.BoxChoiceWidget.currentIndexChanged.connect(self.box_changed)
        FormLayout.addRow("Box", self.BoxChoiceWidget)
        self.box_changed()  # enforce call

        # Animal selector
        self.AnimalChoiceWidget = StringChoiceWidget(
            self,
            choices=[animal.display() for animal in self.Animals],
            default=self.Animal.display(),
        )
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        FormLayout.addRow("Animal", self.AnimalChoiceWidget)
        self.animal_changed()  # enforce call

        # Task selector
        self.TaskChoiceWidget = StringChoiceWidget(
            self, choices=[task.name for task in self.Tasks], default=self.Task.name
        )
        self.TaskChoiceWidget.currentIndexChanged.connect(self.task_changed)
        FormLayout.addRow("Task", self.TaskChoiceWidget)
        self.task_changed()  # enforce call

        # sep
        line = QtWidgets.QFrame(self)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        FormLayout.addRow(line)

        # run button
        self.RunBtn = QtWidgets.QPushButton(self)
        self.RunBtn.setText("Run task")
        FormLayout.addRow(self.RunBtn)
        self.RunBtn.clicked.connect(self.Run)

        # done button
        self.DoneBtn = QtWidgets.QPushButton(self)
        self.DoneBtn.setText("finish session")
        FormLayout.addRow(self.DoneBtn)
        self.DoneBtn.clicked.connect(self.Done)
        self.DoneBtn.setEnabled(False)

        # plot buttons
        self.online_vis_btn = QtWidgets.QPushButton(self)
        self.online_vis_btn.clicked.connect(self.start_online_vis)
        self.online_vis_btn.setText("online visualization")
        FormLayout.addRow(self.online_vis_btn)
        self.online_vis_btn.setEnabled(False)

        # TODO this seems obsolete? investigate
        # calling animal changed again to trigger correct positioning
        # self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        # self.AnimalChoiceWidget.set_value(self.Animal.display())

        # enforce function calls if first animal

        # self.animal_changed()
        # if animals.index(self.animal) == 0: # to call animal_changed even if the animal is the first in the list
        #     self.animal_changed()
        # if tasks.index(self.task) == 0: # enforce function call if first task
        #     self.task_changed()

    def init_counters(self):
        if "OnlineAnalysis" in dict(self.Task).keys():
            if "counters" in dict(self.Task["OnlineAnalysis"]).keys():
                counters = [
                    c.strip()
                    for c in self.Task["OnlineAnalysis"]["counters"].split(",")
                ]
                for counter in counters:
                    mod = importlib.import_module("Visualizers.Counters")
                    C = getattr(mod, counter)
                    self.Counters.append(C(self, self.Task["OnlineAnalysis"]))
                    logger.debug("initializing counter: %s" % counter)

    def start_online_vis(self):
        from Visualizers import TaskVis_mpl  # hardcoded backend for now

        self.plot_windows = []  # to avoid garbage collection

        plotter_keys = [
            key for key in dict(self.Task).keys() if key.startswith("Plot:")
        ]

        for plotter_key in plotter_keys:
            plot_config = dict(self.Task[plotter_key])
            plot_type = plotter_key.split(":")[-1]
            # converting to dicts
            kwargs_keys = [key for key in plot_config.keys() if key.endswith("kwargs")]
            for key in kwargs_keys:
                plot_config[key] = eval("dict(%s)" % plot_config[key])
            vis = TaskVis_mpl.SessionVis(
                self, plot_type, plot_config, self.ArduinoController.OnlineFSMAnalyser
            )
            self.plot_windows.append(vis)  # to avoid garbage collection

    def closeEvent(self, event):
        """reimplementation of closeEvent"""

        # if this widget is parent of all others, is this explicit calling necessary?
        for Controller in self.Controllers:
            Controller.close()

        for Counter in self.Counters:
            Counter.close()

        # why is this not in Controllers?
        if hasattr(self, "CamCalib"):
            self.CamCalib.close()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # store current to last
        for key, value in self.sys_config["current"].items():
            self.sys_config["last"][key] = value

        self.main.exit()

    def Run(self):
        """
        ask for weight
        initialize folder structure
        runs all controllers
        """

        # flags
        self.is_running = True

        # UI related
        self.RunBtn.setEnabled(False)
        self.DoneBtn.setEnabled(True)
        self.online_vis_btn.setEnabled(True)
        self.TaskChoiceWidget.setEnabled(False)
        self.AnimalChoiceWidget.setEnabled(False)

        # animal popup
        self.RunInfo = RunInfoPopup(self)

        logger.info("RUN")  # _TASK_
        logger.info("Task: %s" % self.Task.name)
        logger.info(
            "Animal: %s - body weight: %s%%"
            % (self.Animal.display(), self.Animal.weight_ratio())
        )

        # make folder structure
        date_time = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )  # cross platform compatible
        self.run_folder = self.Animal.folder / "_".join([date_time, self.Task.name])
        os.makedirs(self.run_folder, exist_ok=True)

        # run all controllers
        for Controller in self.Controllers:
            logger.info("running controller: %s" % Controller.name)
            Controller.Run(self.run_folder)

        # reset and start the counters
        for Counter in self.Counters:
            logger.debug("initializing counter: %s" % Counter.name)
            Counter.init()

    def Done(self):
        """finishing the session"""
        # Flags
        self.is_running = False

        # UI
        self.DoneBtn.setEnabled(False)
        self.RunBtn.setEnabled(True)
        self.online_vis_btn.setEnabled(False)
        self.TaskChoiceWidget.setEnabled(True)
        self.AnimalChoiceWidget.setEnabled(True)

        # save the current animal metadata (includes weight)
        out_path = self.run_folder / "animal_meta.csv"
        self.Animal.meta.to_csv(out_path)

        # stop the counters
        for Counter in self.Counters:
            Counter.stop()

        # stop and take down controllers
        for Controller in self.Controllers:
            Controller.close()

        self.task_changed()  # this reinitialized all controllers

    def box_changed(self):
        # update current box
        self.box_config = self.Boxes[self.BoxChoiceWidget.currentIndex()]
        self.sys_config["current"]["box"] = self.box_config.name
        logger.info("selected Box: %s" % self.box_config.name)

    def animal_changed(self):
        self.Animal = self.Animals[self.AnimalChoiceWidget.currentIndex()]
        self.sys_config["current"]["animal"] = self.Animal.ID

        # TODO bring back via a button
        # # displaying previous sessions info
        # if hasattr(self,'AnimalInfoWidget'):
        #     self.AnimalInfoWidget.close()
        #     self.Children.remove(self.AnimalInfoWidget)

        # self.AnimalInfoWidget = AnimalInfoWidget(self, self.sys_config, self.Animal)
        # self.Children.append(self.AnimalInfoWidget)

        logger.info("Animal: %s" % self.Animal.display())

    def task_changed(self):
        # update current task
        self.Task = self.Tasks[self.TaskChoiceWidget.currentIndex()]
        self.sys_config["current"]["task"] = self.Task.name
        logger.info("selected Task: %s" % self.Task.name)

        # take down all currently open controllers
        for Controller in self.Controllers:
            Controller.stop()
            Controller.close()
        self.Controllers = []

        for Counter in self.Counters:
            Counter.stop()
            Counter.close()
        self.Counters = []

        # run each controller present in task config
        for section in self.Task.sections():
            logger.debug("initializing %s" % section)

            if section == "FSM":
                from Widgets.ArduinoWidgets import ArduinoController

                if "OnlineAnalysis" in dict(self.Task).keys():
                    self.ArduinoController = ArduinoController(
                        self,
                        self.sys_config,
                        self.Task["FSM"],
                        self.Box,
                        self.Task["OnlineAnalysis"],
                    )
                else:
                    self.ArduinoController = ArduinoController(
                        self, self.sys_config, self.Task["FSM"], self.Box
                    )
                self.Controllers.append(self.ArduinoController)

            if section == "Bonsai":
                from Widgets.BonsaiWidgets import BonsaiController

                self.BonsaiController = BonsaiController(
                    self, self.sys_config, self.Task["Bonsai"], self.Box
                )
                self.Controllers.append(self.BonsaiController)

            if section == "TimeLogger":
                from Widgets.TimeLogger import TimeLogger

                self.TimeLoggerController = TimeLogger(
                    self, self.sys_config, self.Task["TimeLogger"], self.Box
                )
                self.Controllers.append(self.TimeLoggerController)

            # if section == 'CameraCalib':
            #     from Widgets.CameraCalibrationWidget import CameraCalibrationWidget
            #     self.CamCalib = CameraCalibrationWidget(self, self.sys_config, self.Task['CameraCalib'])
            # self.Controllers.append(self.CamCalib)

            # if section == 'LoadCell':
            # from LoadCellWidgets import LoadCellController
            #     self.LoadCellController = LoadCellController(self, self.sys_config, self.Task['LoadCell'])
            #     self.Controllers.append(self.LoadCellController)

            # if section == 'Display':
            #     self.DisplayController = HardwareWidgets.DisplayController(self)
            #     self.Controllers.append(self.DisplayController)

        # after controllers, reinit counter
        self.init_counters()


"""
 
 #### ##    ## ########  #######  
  ##  ###   ## ##       ##     ## 
  ##  ####  ## ##       ##     ## 
  ##  ## ## ## ######   ##     ## 
  ##  ##  #### ##       ##     ## 
  ##  ##   ### ##       ##     ## 
 #### ##    ## ##        #######  
 
"""


class AnimalInfoWidget(QtWidgets.QWidget):
    """displays some info about the animal: list of previous sessions"""

    def __init__(self, parent, config, Animal):
        super(AnimalInfoWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.sys_config = config
        self.Animal = Animal
        self.initUI()

        self.settings = QtCore.QSettings("TaskControl", "AnimalInfoWidget")

        # FIXME change those
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

    def initUI(self):
        self.Table = QtWidgets.QTableView(self)
        self.Layout = QtWidgets.QHBoxLayout(self)
        self.Layout.addWidget(self.Table)
        self.setLayout(self.Layout)

        self.setWindowTitle(self.Animal.display())
        self.update()
        self.show()

    def update(self):
        try:
            sessions_df = utils.get_sessions(self.Animal.folder)
            lines = sessions_df["task"].tolist()
            lines = "\n".join(lines)
            model = PandasModel(sessions_df[["date", "time", "task"]])
            self.Table.setModel(model)
        except ValueError:
            pass
