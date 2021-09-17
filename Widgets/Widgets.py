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
        self.Children = [] # a list of all UI windows
        self.main = main # ref to the main

        # flags
        self.running = False

        self.initUI()

    def initUI(self):
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

        # sep
        line = QtWidgets.QFrame(self)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        FormLayout.addRow(line)

        # display timer
        self.TimeLabel = QtWidgets.QLCDNumber()
        self.TimeLabel.setDigitCount(8)
        self.TimeLabel.display('00:00:00')
        FormLayout.addRow('time in session', self.TimeLabel)
        self.TimeLabel.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.time_handler)

        # counters
        # if 'counters' in dict(self.task_config['Visualization']).keys():
        #     counters = [c.strip() for c in self.task_config['Visualization']['counters'].split(',')]
        #     self.Counters = Counters(self, counters)
        #     self.Children.append(self.Counters)

        # display number of trials
        # currently the updating is done within a Monitor!
        self.TrialCounter = TrialCounter3(self)
        # FormLayout.addRow('completed/aborted/total',self.TrialCounter)
        FormLayout.addRow(self.TrialCounter)

        # display amount of water consumed
        self.WaterCounter = WaterCounter(self)
        # FormLayout.addRow('consumed water (µl)', self.WaterCounter)
        FormLayout.addRow(self.WaterCounter)

        # sep
        line = QtWidgets.QFrame(self)
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        FormLayout.addRow(line)

        # self terminate
        self.selfTerminateCheckBox = QtWidgets.QCheckBox()
        self.selfTerminateCheckBox.setChecked(True)
        self.selfTerminateCheckBox.stateChanged.connect(self.TerminateCheckBoxToggle)
        
        FormLayout.addRow("self terminate", self.selfTerminateCheckBox)
        Df = pd.DataFrame([['after (min) ',  45,   'int32'],
                           ['after (ul) ',   500, 'int32']],
                           columns=['name','value','dtype'])

        self.selfTerminateEdit = ValueEditFormLayout(self, DataFrame=Df)
        FormLayout.addRow(self.selfTerminateEdit)
        self.selfTerminateEdit.setEnabled(False)

        # positioning and deco
        self.setWindowTitle("Settings")
        self.move(10, 10) # some corner of the screen ... 
        
        # calling animal changed again to trigger correct layouting
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        self.AnimalChoiceWidget.set_value(self.Animal.display())
                
        # TODO
        # test if they can't be called wo the check and move above lines 
        # up to the corresponding point 

        # enforce function calls if first animal
        self.animal_changed()
        # if animals.index(self.animal) == 0: # to call animal_changed even if the animal is the first in the list
        #     self.animal_changed()
        if tasks.index(self.task) == 0: # enforce function call if first task
            self.task_changed()

        self.show()

        for Child in self.Children:
            Child.layout()

        self.layout()

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

        for Child in self.Children:
            Child.close()

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

        # start the timer
        self.t_start = datetime.now()
        self.timer.start(1000)

        # reset the counters
        for Counter in [self.TrialCounter,self.WaterCounter]:
            Counter.reset()

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
        self.timer.stop()

        # Flags
        self.running = False

        # stop and take down controllers
        for Controller in self.Controllers:
            Controller.stop()
            Controller.close()

        self.task_changed() # this reinitialized all controllers

    def animal_changed(self):
        current_id = self.AnimalChoiceWidget.get_value().split(' - ')[0]
        self.config['current']['animal'] = current_id
        self.Animal, = [Animal for Animal in self.Animals if Animal.ID == current_id]

        # displaying previous sessions info
        if hasattr(self,'AnimalInfoWidget'):
            self.AnimalInfoWidget.close()

        self.AnimalInfoWidget = AnimalInfoWidget(self, self.config, self.Animal)
        self.Children = []
        self.Children.append(self.AnimalInfoWidget)

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
                self.Controllers = []

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

            self.layout()

    def layout(self):
        # layouting
        gap = int(self.config['ui']['small_gap'])
        utils.tile_Widgets([self] + self.Controllers, how="horizontally", gap=gap)
        for Controller in self.Controllers:
            Controller.layout()

    def TerminateCheckBoxToggle(self, state):
        if state == 0:
            self.selfTerminateEdit.setEnabled(True)

        if state == 2:
            self.selfTerminateEdit.setEnabled(False)


    def time_handler(self):
        # called every second by QTimer
        # FIXME there are rounding errors
        # FIXME refactor
        dt = datetime.now() - self.t_start
        self.TimeLabel.display(str(dt).split('.')[0])

        # test for self termination
        if self.selfTerminateCheckBox.checkState() == 2: # if true
            max_time = self.selfTerminateEdit.get_entry('after (min) ')['value']
            max_water = self.selfTerminateEdit.get_entry('after (ul) ')['value']

            current_time = dt.seconds/60
            current_water = self.WaterCounter.get_value()
            # current_trials = self.TrialCounter.get_value('total')
            current_trials = 1000 # FIXME

            if current_time >= max_time and max_time > 0:
                self.Done()
            if current_water >= max_water and max_water > 0:
                self.Done()

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

    def initUI(self):
        # self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Table = QtWidgets.QTableView()
        self.Layout = QtWidgets.QHBoxLayout()
        # self.Layout.addWidget(self.TextBrowser)
        self.Layout.addWidget(self.Table)
        self.setLayout(self.Layout)

        self.setWindowTitle(self.Animal.display())
        self.update()
        self.show()
        self.layout()

    def layout(self):
        big_gap = int(self.config['ui']['big_gap'])
        self.resize(self.parent().width(),self.sizeHint().height())
        utils.tile_Widgets([self.parent()]+self.parent().Children, how='vertically', gap=big_gap)

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

def import_from(module, name):
    module = __import__(module, fromlist=[name])
    return getattr(module, name)

class Counters(QtWidgets.QWidget):
    def __init__(self, parent, counters):
        super(Counters, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.Layout = QtWidgets.QVBoxLayout()
        for counter in counters:
            C = import_from('.'.join(['Tasks',parent.task,'counters']), counter)
            self.Layout.addWidget(C(self))
        self.show()
        self.layout()

    def layout(self):
        big_gap = int(self.parent().config['ui']['big_gap'])
        self.resize(self.parent().width(),self.sizeHint().height())
        utils.tile_Widgets([self.parent()]+self.parent().Children, how='vertically', gap=big_gap)

# class OutcomeCounter(QtWidgets.QTableView):
#     """ """
#     def __init__(self, parent, outcomes=None):
#         super(OutcomeCounter, self).__init__(parent=parent)
#         self.outcomes = outcomes
#         self.initModel()
#         self.initUI()
#         self.model.setDf(self.Df)
#         self.update()

#     def initModel(self):
#         # init data
#         self.Df = pd.DataFrame(sp.zeros((4,5),dtype='int32'),columns=['label','left','right','sum','frac'],index=['correct','incorrect','missed','premature'])
#         self.Df['frac'] = self.Df['frac'].astype('float32')
#         self.Df['label'] = self.Df.index

#         self.model = PandasModel(self.Df)
#         self.setModel(self.model)
#         self.model.setDf(self.Df)

#     def initUI(self):
#         for i in range(self.Df.columns.shape[0]):
#             self.setColumnWidth(i, 40)
#         self.update()
#         pass

#     def connect(self, OnlineDataAnalyser):
#         # connect signals
#         self.OnlineDataAnalyser = OnlineDataAnalyser
#         OnlineDataAnalyser.trial_data_available.connect(self.on_data)
    
#     def on_data(self, TrialDf, TrialMetricsDf):
#         side = metrics.get_correct_side(TrialDf).values[0]
#         outcome = metrics.get_outcome(TrialDf).values[0]
#         try:
#             self.Df.loc[outcome, side] += 1
#             self.Df['sum'] = self.Df['left'] + self.Df['right']
#             self.Df['frac'] = self.Df['sum'] / self.Df.sum()['sum']
#         except KeyError:
#             pass

#         self.model.setDf(self.Df)
#         self.update()

# class WaterCounter_old(QtWidgets.QLabel):
#     """ """
#     def __init__(self, parent):
#         super(WaterCounter, self).__init__(parent=parent)
#         self.reset()

#     def reset(self):
#         self.setText("0")

#     def increment(self, amount):
#         current_amount = int(float(self.text()))
#         new_amount = current_amount + amount
#         self.setText(str(new_amount))

#     def get_value(self):
#         return int(float(self.text()))

class WaterCounter(QtWidgets.QWidget):
    """ with a reset button """
    def __init__(self, parent):
        super(WaterCounter, self).__init__(parent=parent)
        self.Layout = QtWidgets.QHBoxLayout()
        self.Labela = QtWidgets.QLabel('consumed water (µl)')
        self.Label = QtWidgets.QLabel()
        self.reset_btn = QtWidgets.QPushButton('reset')
        self.reset_btn.clicked.connect(self.reset)
        self.Layout.addWidget(self.Labela, alignment=QtCore.Qt.AlignVCenter)
        self.Layout.addWidget(self.Label, alignment=QtCore.Qt.AlignVCenter)
        self.Layout.addWidget(self.reset_btn, alignment=QtCore.Qt.AlignVCenter)
        self.setLayout(self.Layout)
        self.reset()
    
    def reset(self):
        self.Label.setText("0")

    def increment(self, amount):
        current_amount = int(float(self.Label.text()))
        new_amount = current_amount + amount
        self.Label.setText(str(new_amount))

    def get_value(self):
        return int(float(self.Label.text())) # FIXME check this


class TrialCounter3(QtWidgets.QTableView):
    """ """
    def __init__(self, parent):
        super(TrialCounter3, self).__init__(parent=parent)
        self.initModel()
        self.initUI()

        # self.Df.loc['correct','left'] += 1
        # self.model.set_data(self.Df)
        # self.model.set_data(self.Df)
        # self.model._data = self.Df
        self.model.setDf(self.Df)
    
        self.update()
        # print(self.model._data)

    def initModel(self):
        # init data
        self.Df = pd.DataFrame(sp.zeros((4,5),dtype='int32'),columns=['label','left','right','sum','frac'],index=['correct','incorrect','missed','premature'])
        self.Df['frac'] = self.Df['frac'].astype('float32')
        self.Df['label'] = self.Df.index

        self.model = PandasModel(self.Df)
        self.setModel(self.model)
        self.model.setDf(self.Df)
        # self.model.set_data(self.Df)
        # self.model._data = self.Df
        # self.model.dataChanged.connect(self.refresh)
        
    def initUI(self):
        for i in range(self.Df.columns.shape[0]):
            self.setColumnWidth(i, 40)
        self.update()
        pass

    def connect(self, OnlineDataAnalyser):
        # connect signals
        self.OnlineDataAnalyser = OnlineDataAnalyser
        OnlineDataAnalyser.trial_data_available.connect(self.on_data)
    
    def on_data(self, TrialDf, TrialMetricsDf):
        side = metrics.get_correct_side(TrialDf).values[0]
        outcome = metrics.get_outcome(TrialDf).values[0]
        try:
            self.Df.loc[outcome, side] += 1
            self.Df['sum'] = self.Df['left'] + self.Df['right']
            self.Df['frac'] = self.Df['sum'] / self.Df.sum()['sum']
        except KeyError:
            pass
        # self.model.set_data(self.Df)
        # self.model._data = self.Df
        self.model.setDf(self.Df)
        self.update()

    def reset(self):
        pass

    # def refresh(self, i, j):
    #     print('refresh called on ',i,j)
    #     self.update()