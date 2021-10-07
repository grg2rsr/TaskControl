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

from Widgets.ArduinoWidgets import ArduinoController
from Widgets.BonsaiWidgets import BonsaiController
# from LoadCellWidgets import LoadCellController

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
    The main toplevel widget. Is parent of all controllers. Brings together all animal and task related information
    some design notes:
    each user has a profile which points to the folder of tasks and animals
    """
    # FIXME does not have parent? - fix inheritance from TaskControl
    def __init__(self, main, config):
        super(SettingsWidget, self).__init__()
        self.config = config # a configparser dict
        self.Controllers = [] # a list of all controllers
        self.Counters = []
        self.main = main # ref to the main

        # flags
        self.running = False

        # Initial window size/pos last saved. Use default values for first time
        # self.settings = QtCore.QSettings('SettingsWidget.ini', QtCore.QSettings.IniFormat)

        # Settings
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

        # animal selector
        self.Animals = utils.get_Animals(self.config['paths']['animals_folder'])
        last_id = self.config['last']['animal']
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
        tasks = utils.get_tasks(self.config['paths']['tasks_folder'])
        self.task = self.config['last']['task']
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
       
        # calling animal changed again to trigger correct positioning
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        self.AnimalChoiceWidget.set_value(self.Animal.display())
                

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

        for Controller in self.Controllers:
            Controller.close()

        for Counter in self.Counters:
            Counter.close()

        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

        # store current to last
        for key, value in self.config['current'].items():
            self.config['last'][key] = value

        self.main.exit()

    def Run(self):
        """
        ask for weight
        initialize folder structure
        runs all controllers
        """

        # UI related
        self.RunBtn.setEnabled(False)
        self.DoneBtn.setEnabled(True)
        self.online_vis_btn.setEnabled(True)
        self.TaskChoiceWidget.setEnabled(False)
        self.AnimalChoiceWidget.setEnabled(False)

        # animal popup
        self.RunInfo = RunInfoPopup(self)

        utils.printer("RUN",'task')
        utils.printer("Task: %s" % self.task,'msg')
        utils.printer("Animal: %s - body weight: %s%%" % (self.Animal.display(), self.Animal.weight_ratio()),'msg')
        
        # make folder structure
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # underscores in times bc colons kill windows paths ...
        self.run_folder = self.Animal.folder  / '_'.join([date_time,self.task])
        os.makedirs(self.run_folder,exist_ok=True)

        for Controller in self.Controllers:
            utils.printer("running controller: %s" % Controller.name,'msg')
            Controller.Run(self.run_folder)

            # connect OnlineDataAnalyzer
            # TODO FIXME 
            # if type(Controller) == ArduinoController:
            #     if hasattr(self.ArduinoController,'OnlineDataAnalyser'):
            #         self.TrialCounter.connect(self.ArduinoController.OnlineDataAnalyser)

        self.running = True
        
        # reset and start the counters
        for Counter in self.Counters:
            Counter.init()

    def Done(self):
        """ finishing the session """
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

        # Flags
        self.running = False

        # stop and take down controllers
        for Controller in self.Controllers:
            Controller.close()

        self.task_changed() # this reinitialized all controllers

    def animal_changed(self):
        current_id = self.AnimalChoiceWidget.get_value().split(' - ')[0]
        self.config['current']['animal'] = current_id
        self.Animal, = [Animal for Animal in self.Animals if Animal.ID == current_id]

        # TODO bring back via a button
        # # displaying previous sessions info
        # if hasattr(self,'AnimalInfoWidget'):
        #     self.AnimalInfoWidget.close()
        #     self.Children.remove(self.AnimalInfoWidget)

        # self.AnimalInfoWidget = AnimalInfoWidget(self, self.config, self.Animal)
        # self.Children.append(self.AnimalInfoWidget)

        utils.printer("Animal: %s" % self.Animal.display(),'msg')

    def task_changed(self):
        # first check if task is running, if yes, don't do anything
        if self.running == True:
            utils.printer("trying to change a running task", 'error')
            return None

        else:
            # get task
            self.config['current']['task'] = self.TaskChoiceWidget.get_value()
            self.task = self.config['current']['task']
            self.task_folder = Path(self.config['paths']['tasks_folder']) / self.task
            utils.printer("Currently selected Task: %s" % self.task, 'msg')

            # parse task config file
            self.task_config = configparser.ConfigParser()
            self.task_config.read(self.task_folder / 'task_config.ini')
            
            # take down all currently open controllers
            for Controller in self.Controllers:
                Controller.stop()
                Controller.close()
                self.Controllers.remove(Controller)

            for Counter in self.Counters:
                Counter.stop()
                Counter.close()
                self.Counters.remove(Counter)
            
            # run each controller present in task config
            for section in self.task_config.sections():
                utils.printer("initializing %s" % section, 'msg')

                if section == 'Arduino':
                    self.ArduinoController = ArduinoController(self, self.config, self.task_config['Arduino'])
                    self.Controllers.append(self.ArduinoController)

                if section == 'Bonsai':
                    self.BonsaiController = BonsaiController(self, self.config, self.task_config['Bonsai'])
                    self.Controllers.append(self.BonsaiController)

                # if section == 'LoadCell':
                #     self.LoadCellController = LoadCellController(self, self.config, self.task_config['LoadCell'])
                #     self.Controllers.append(self.LoadCellController)

                # if section == 'Display':
                #     self.DisplayController = HardwareWidgets.DisplayController(self)
                #     self.Controllers.append(self.DisplayController)

            # after controllers, reinit counter
            self.init_counters()

            # positioning
            self.position_widgets()

    def position_widgets(self):
        print(self.size())
        # policy = QtCore.Q
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                                 QtWidgets.QSizePolicy.Fixed))
        # position controllers
        # gap = int(self.config['ui']['small_gap'])
        # utils.tile_Widgets([self] + self.Controllers, how="horizontally", gap=gap)
        # for Controller in self.Controllers:
        #     Controller.position()

        # position counters
        # gap = int(self.config['ui']['small_gap'])
        # utils.scale_Widgets([self] + self.Counters, how="vertical", mode='min')
        # utils.tile_Widgets([self] + self.Counters, how="vertically", gap=gap)


        # def position(self):
        #     # positioning on screen
        #     gap = int(self.config['ui']['small_gap'])

        #     # controllers
        #     utils.tile_Widgets([self] + self.Controllers, how="horizontally", gap=gap)
        #     for Controller in self.Controllers:
        #         Controller.position()
        pass

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
    """ displays some interesing info about the animal: list of previous sessions """
    def __init__(self, parent, config, Animal):
        super(AnimalInfoWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.config = config
        self.Animal = Animal
        self.initUI()

        self.settings = QtCore.QSettings('TaskControl', 'AnimalInfoWidget')
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))

    def initUI(self):
        # self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Table = QtWidgets.QTableView(self)
        self.Layout = QtWidgets.QHBoxLayout(self)
        # self.Layout.addWidget(self.TextBrowser)
        self.Layout.addWidget(self.Table)
        self.setLayout(self.Layout)

        self.setWindowTitle(self.Animal.display())
        self.update()
        self.show()
        # self.position()

    # def position(self):
    #     big_gap = int(self.config['ui']['big_gap'])
    #     self.resize(self.parent().width(),self.sizeHint().height())
        # utils.tile_Widgets([self.parent()]+self.parent().Children, how='vertically', gap=big_gap)

    def update(self):
        try:
            sessions_df = utils.get_sessions(self.Animal.folder)
            # lines = sessions_df['task'].to_list()
            lines = sessions_df['task'].tolist()
            lines = '\n'.join(lines)
            model = PandasModel(sessions_df[['date','time','task']])
            self.Table.setModel(model)
        except ValueError:
            pass


"""
 
  ######   #######  ##     ## ##    ## ######## ######## ########   ######  
 ##    ## ##     ## ##     ## ###   ##    ##    ##       ##     ## ##    ## 
 ##       ##     ## ##     ## ####  ##    ##    ##       ##     ## ##       
 ##       ##     ## ##     ## ## ## ##    ##    ######   ########   ######  
 ##       ##     ## ##     ## ##  ####    ##    ##       ##   ##         ## 
 ##    ## ##     ## ##     ## ##   ###    ##    ##       ##    ##  ##    ## 
  ######   #######   #######  ##    ##    ##    ######## ##     ##  ######  
 
"""

# # move to utils?
# def import_from(module, name):
#     module = __import__(module, fromlist=[name])
#     return getattr(module, name)

# class CountersWidget(QtWidgets.QWidget):
#     def __init__(self, parent, counters):
#         super(CountersWidget, self).__init__(parent=parent)
#         self.setWindowFlags(QtCore.Qt.Window)
#         self.setWindowTitle("Counters")
#         self.Layout = QtWidgets.QVBoxLayout(self)
#         for counter in counters:
#             # C = import_from('.'.join(['Tasks',parent.task,'counters']), counter)
#             mod = importlib.import_module('Visualizers.Counters')
#             C = getattr(mod, counter)
#             self.Layout.addWidget(C(self))
#             utils.printer("initializing counter: %s" % counter, 'msg')

#             # deco - split by line
#             line = QtWidgets.QFrame(self)
#             line.setFrameShape(QtWidgets.QFrame.HLine)
#             line.setFrameShadow(QtWidgets.QFrame.Sunken)
#             self.Layout.addWidget(line)

#         self.setLayout(self.Layout)
#         self.position()
#         self.show()

#     def position(self):
#         big_gap = int(self.parent().config['ui']['big_gap'])
#         self.resize(self.parent().width(),self.sizeHint().height())
#         utils.tile_Widgets([self.parent()]+self.parent().Children, how='vertically', gap=big_gap)
