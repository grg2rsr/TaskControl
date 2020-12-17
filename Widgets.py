import sys, os
from pathlib import Path
import configparser
from datetime import datetime

import scipy as sp
import pandas as pd

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import utils
import behavior_analysis_utils as bhv

from TaskVis_pg import TrialsVis
from TaskVis_mpl import SessionVis

from Popups import *
from UtilityWidgets import *

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
        self.plot_trial_btn = QtWidgets.QPushButton(self)
        self.plot_trial_btn.clicked.connect(self.plot_trial)
        self.plot_trial_btn.setText('plot trial overview')
        FormLayout.addRow(self.plot_trial_btn)
        self.plot_trial_btn.setEnabled(False)

        self.plot_session_btn = QtWidgets.QPushButton(self)
        self.plot_session_btn.clicked.connect(self.plot_session)
        self.plot_session_btn.setText('plot session overview')
        FormLayout.addRow(self.plot_session_btn)
        self.plot_session_btn.setEnabled(False)

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

        # display number of trials
        # currently the updating is done within a Monitor!
        self.TrialCounter = TrialCounter2(self)
        # FormLayout.addRow('completed/aborted/total',self.TrialCounter)
        FormLayout.addRow(self.TrialCounter)

        # display amount of water consumed
        self.WaterCounter = WaterCounter(self)
        FormLayout.addRow('consumed water (µl)', self.WaterCounter)

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
                           ['after (ul) ',   500, 'int32'],
                           ['after #trials ',0,    'int32']],
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

    def plot_trial(self):
        self.TrialsVisWidget = TrialsVis(self, self.ArduinoController.OnlineDataAnalyser)

    def plot_session(self):
        self.SessionVisWidget = SessionVis(self, self.ArduinoController.OnlineDataAnalyser)

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
        self.plot_trial_btn.setEnabled(True)
        self.plot_session_btn.setEnabled(True)
        # TODO make the task changeable

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
        self.plot_session_btn.setEnabled(False)
        self.plot_trial_btn.setEnabled(False)
        # TODO make the task unchangeable

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
                    from ArduinoWidgets import ArduinoController
                    self.ArduinoController = ArduinoController(self, self.config, self.task_config['Arduino'])
                    self.Controllers.append(self.ArduinoController)

                if section == 'Bonsai':
                    from BonsaiWidgets import BonsaiController
                    self.BonsaiController = BonsaiController(self, self.config, self.task_config['Bonsai'])
                    self.Controllers.append(self.BonsaiController)

                if section == 'LoadCell':
                    from LoadCellWidgets import LoadCellController
                    self.LoadCellController = LoadCellController(self, self.config, self.task_config['LoadCell'])
                    self.Controllers.append(self.LoadCellController)

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
            max_trials = self.selfTerminateEdit.get_entry('after #trials ')['value']

            current_time = dt.seconds/60
            current_water = self.WaterCounter.get_value()
            current_trials = self.TrialCounter.get_value('total')

            if current_time >= max_time and max_time > 0:
                self.Done()
            if current_water >= max_water and max_water > 0:
                self.Done()
            if current_trials >= max_trials and max_trials > 0:
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
        utils.tile_Widgets([self.parent(),self], how='vertically', gap=big_gap)

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

class TrialCounter(QtWidgets.QLabel):
    """ """
    def __init__(self, parent):
        super(TrialCounter, self).__init__(parent=parent)
        self.reset()

    def reset(self):
        self.setText("0/0/0\t--")

    def increment(self,successful=False):
        vals = [int(v) for v in self.text().split('\t')[0].split('/')]
        if successful:
            vals[0] += 1
            vals[2] += 1
        else:
            vals[1] += 1
            vals[2] += 1

        new_frac = sp.around(vals[0]/vals[2],2)
        self.setText('/'.join([str(v) for v in vals]) + '\t' + str(new_frac))

class TrialCounter2(QtWidgets.QFormLayout):
    """ """
    def __init__(self, parent):
        super(TrialCounter2, self).__init__(parent=parent)
        # self.categories = ['correct','incorrect','missed','premature','total']
        self.counters = dict(correct=QtWidgets.QLabel(''),
                             incorrect=QtWidgets.QLabel(''),
                             missed=QtWidgets.QLabel(''),
                             premature=QtWidgets.QLabel(''),
                             total=QtWidgets.QLabel(''))

        self.initUI()
        self.reset()
    
    def initUI(self):
        # FormLayout = QtWidgets.QFormLayout(self)
        # self.setVerticalSpacing(10)
        self.setHorizontalSpacing(10)
        self.setLabelAlignment(QtCore.Qt.AlignRight)

        for category in ['correct','incorrect','missed','premature','total']:
            self.addRow(category, self.counters[category])

        # self.setLayout(FormLayout)
       
    def reset(self):
        for label, counter in self.counters.items():
            counter.setText('0\t0')

    def increment(self,label):
        count = self.get_value(label)
        nTrials = self.get_value('total') + 1
        new_count = count + 1
        new_frac = sp.around((count+1)/nTrials, 2)
        self.counters[label].setText(str(new_count) + '\t' + str(new_frac))

    def get_value(self,label):
        return int(self.counters[label].text().split('\t')[0])

class WaterCounter(QtWidgets.QLabel):
    """ """
    def __init__(self, parent):
        super(WaterCounter, self).__init__(parent=parent)
        self.reset()

    def reset(self):
        self.setText("0")

    def increment(self, amount):
        current_amount = int(float(self.text()))
        new_amount = current_amount + amount
        self.setText(str(new_amount))

    def get_value(self):
        return int(float(self.text())) # FIXME check this
