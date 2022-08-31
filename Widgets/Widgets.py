import sys, os
from pathlib import Path
import configparser
from datetime import datetime
import importlib

import scipy as sp
import numpy as np
import pandas as pd

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

from Utils import utils
from Utils import behavior_analysis_utils as bhv
from Utils import metrics

from Visualizers.TaskVis_pg  import TrialsVis
from Visualizers.TaskVis_mpl import SessionVis

from Widgets.Popups import RunInfoPopup
from Widgets.UtilityWidgets import StringChoiceWidget, ValueEditFormLayout, PandasModel

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
        self.sys_config = config # a configparser dict
        self.Controllers = [] # a list of all controllers
        self.Counters = []
        self.main = main # ref to the main

        # flags
        self.is_running = False

        # Settings - to store window positions
        self.settings = QtCore.QSettings('TaskControl','SettingsWidget')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

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
        boxes = utils.get_boxes(self.sys_config['paths']['boxes_folder'])
        self.box_name = self.sys_config['last']['box']
        self.BoxChoiceWidget = StringChoiceWidget(self, choices=boxes)
        self.BoxChoiceWidget.currentIndexChanged.connect(self.box_changed)
        try:
            self.BoxChoiceWidget.set_value(self.box_name)
        except:
            # if box is not in list
            self.BoxChoiceWidget.set_value(boxes[0])
        FormLayout.addRow('Box', self.BoxChoiceWidget)
        self.box_changed() # enforce call

        # animal selector
        self.Animals = utils.get_Animals(self.sys_config['paths']['animals_folder'])
        last_id = self.sys_config['last']['animal']
        self.Animal, = [Animal for Animal in self.Animals if Animal.ID == last_id]
        display_names = [animal.display() for animal in self.Animals]
        self.AnimalChoiceWidget = StringChoiceWidget(self, choices=display_names)
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        try:
            self.AnimalChoiceWidget.set_value(self.Animal.display())
        except:
            # if animal is not in list
            self.AnimalChoiceWidget.set_value(self.Animals[0].display())
        FormLayout.addRow('Animal', self.AnimalChoiceWidget)

        # task selector
        tasks = utils.get_tasks(self.sys_config['paths']['tasks_folder'])
        self.task = self.sys_config['last']['task']
        self.TaskChoiceWidget = StringChoiceWidget(self, choices=tasks)
        self.TaskChoiceWidget.currentIndexChanged.connect(self.task_changed)
        try:
            self.TaskChoiceWidget.set_value(self.task)
        except:
            # if task is not in list
            self.TaskChoiceWidget.set_value(tasks[0])
        FormLayout.addRow('Task', self.TaskChoiceWidget)

        # sep
        line = QtWidgets.QFrame(self)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        FormLayout.addRow(line)

        # run button
        self.RunBtn = QtWidgets.QPushButton(self)
        self.RunBtn.setText('Run task')
        FormLayout.addRow(self.RunBtn)
        self.RunBtn.clicked.connect(self.Run)

        # done button
        self.DoneBtn = QtWidgets.QPushButton(self)
        self.DoneBtn.setText('finish session')
        FormLayout.addRow(self.DoneBtn)
        self.DoneBtn.clicked.connect(self.Done)
        self.DoneBtn.setEnabled(False)

        # plot buttons
        self.online_vis_btn = QtWidgets.QPushButton(self)
        self.online_vis_btn.clicked.connect(self.start_online_vis)
        self.online_vis_btn.setText('online visualization')
        FormLayout.addRow(self.online_vis_btn)
        self.online_vis_btn.setEnabled(False)
       
        # TODO this seems obsolete? investigate
        # calling animal changed again to trigger correct positioning
        # self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        # self.AnimalChoiceWidget.set_value(self.Animal.display())
                
        # enforce function calls if first animal
        
        self.animal_changed()
        # if animals.index(self.animal) == 0: # to call animal_changed even if the animal is the first in the list
        #     self.animal_changed()
        if tasks.index(self.task) == 0: # enforce function call if first task
            self.task_changed()

    def init_counters(self):
        if 'OnlineAnalysis' in dict(self.task_config).keys():
            if 'counters' in dict(self.task_config['OnlineAnalysis']).keys():
                counters = [c.strip() for c in self.task_config['OnlineAnalysis']['counters'].split(',')]
                for counter in counters:
                    mod = importlib.import_module('Visualizers.Counters')
                    C = getattr(mod, counter)
                    self.Counters.append(C(self))
                    utils.printer("initializing counter: %s" % counter, 'msg')

    def start_online_vis(self):
        # TODO implement me

        # needs to 
        # cwd = os.getcwd()
        # os.chdir(self.task_folder)
        # plotters =[p.strip() for p in self.task_config['Visualization']['plotters'].split(',')]
        # utils.debug_trace()
        # module_name = self.task_config['Visualization']['visualizers']
        # mod = importlib.import_module(module_name)
        # # get registered plotters (how?)
        # # start them and connect them
        # os.chdir(cwd)
        pass

    def closeEvent(self,event):
        """ reimplementation of closeEvent """

        # if this widget is parent of all others, is this explicit calling necessary?
        for Controller in self.Controllers:
            Controller.close()

        for Counter in self.Counters:
            Counter.close()

        # why is this not in Controllers?
        if hasattr(self,'CamCalib'):
            self.CamCalib.close()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # store current to last
        for key, value in self.sys_config['current'].items():
            self.sys_config['last'][key] = value

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

        utils.printer("RUN", 'task')
        utils.printer("Task: %s" % self.task, 'msg')
        utils.printer("Animal: %s - body weight: %s%%" % (self.Animal.display(), self.Animal.weight_ratio()),'msg')

        # make folder structure
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # cross platform compatible
        self.run_folder = self.Animal.folder  / '_'.join([date_time, self.task])
        os.makedirs(self.run_folder, exist_ok=True)

        # run all controllers
        for Controller in self.Controllers:
            utils.printer("running controller: %s" % Controller.name, 'msg')
            Controller.Run(self.run_folder)

        # reset and start the counters
        for Counter in self.Counters:
            utils.printer("initializing counter: %s" % Counter.name, 'msg')
            Counter.init()

    def Done(self):
        """ finishing the session """
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

        self.task_changed() # this reinitialized all controllers

    def box_changed(self):
        print("called")
        # update current box
        self.sys_config['current']['box'] = self.BoxChoiceWidget.get_value()
        self.box_name = self.sys_config['current']['box']
        self.box_config = configparser.ConfigParser()
        box_config_path = Path(self.sys_config['paths']['boxes_folder']) / (self.box_name + '.ini')
        self.box_config.read(box_config_path)
        utils.printer("selected Box: %s" % self.box_name, 'msg')
        
    def animal_changed(self):
        current_id = self.AnimalChoiceWidget.get_value().split(' - ')[0]
        self.sys_config['current']['animal'] = current_id
        self.Animal, = [Animal for Animal in self.Animals if Animal.ID == current_id]

        # TODO bring back via a button
        # # displaying previous sessions info
        # if hasattr(self,'AnimalInfoWidget'):
        #     self.AnimalInfoWidget.close()
        #     self.Children.remove(self.AnimalInfoWidget)

        # self.AnimalInfoWidget = AnimalInfoWidget(self, self.sys_config, self.Animal)
        # self.Children.append(self.AnimalInfoWidget)

        utils.printer("Animal: %s" % self.Animal.display(),'msg')

    def task_changed(self):
        # first check if task is running, if yes, don't do anything
        if self.is_running == True:
            utils.printer("trying to change a running task", 'error')
            return None

        else:
            # update current task
            self.sys_config['current']['task'] = self.TaskChoiceWidget.get_value()
            self.task = self.sys_config['current']['task']
            self.task_folder = Path(self.sys_config['paths']['tasks_folder']) / self.task
            utils.printer("selected Task: %s" % self.task, 'msg')

            # parse task config file
            self.task_config = configparser.ConfigParser()
            self.task_config.read(self.task_folder / 'task_config.ini')
            
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
            for section in self.task_config.sections():
                utils.printer("initializing %s" % section, 'msg')

                if section == 'FSM':
                    from Widgets.ArduinoWidgets2 import ArduinoController
                    self.ArduinoController = ArduinoController(self, self.sys_config, self.task_config['FSM'], self.box_config)
                    self.Controllers.append(self.ArduinoController)

                if section == 'Bonsai':
                    from Widgets.BonsaiWidgets import BonsaiController
                    self.BonsaiController = BonsaiController(self, self.sys_config, self.task_config['Bonsai'], self.box_config)
                    self.Controllers.append(self.BonsaiController)

                if section == 'TimeLogger':
                    from Widgets.TimeLogger2 import TimeLogger
                    self.TimeLoggerController = TimeLogger(self, self.sys_config, self.task_config['TimeLogger'], self.box_config)
                    self.Controllers.append(self.TimeLoggerController)
                    
                # if section == 'CameraCalib':
                #     from Widgets.CameraCalibrationWidget import CameraCalibrationWidget
                #     self.CamCalib = CameraCalibrationWidget(self, self.sys_config, self.task_config['CameraCalib'])
                    # self.Controllers.append(self.CamCalib)

                # if section == 'LoadCell':
                    # from LoadCellWidgets import LoadCellController
                #     self.LoadCellController = LoadCellController(self, self.sys_config, self.task_config['LoadCell'])
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
    """ displays some info about the animal: list of previous sessions """
    def __init__(self, parent, config, Animal):
        super(AnimalInfoWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.sys_config = config
        self.Animal = Animal
        self.initUI()

        self.settings = QtCore.QSettings('TaskControl', 'AnimalInfoWidget')

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
            lines = sessions_df['task'].tolist()
            lines = '\n'.join(lines)
            model = PandasModel(sessions_df[['date','time','task']])
            self.Table.setModel(model)
        except ValueError:
            pass