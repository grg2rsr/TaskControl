import sys, os
from pathlib import Path
import shutil
import configparser
from datetime import datetime

import scipy as sp
import pandas as pd

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

import utils
import behavior_analysis_utils as bhv

from TaskVis_pg import TrialsVis
# from TaskVis_pg import SessionVis
from TaskVis_mpl import SessionVis

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
        animals = utils.get_animals(self.config['paths']['animals_folder'])
        self.animal = self.config['last']['animal']
        self.AnimalChoiceWidget = StringChoiceWidget(self, choices=animals)
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        try:
            self.AnimalChoiceWidget.set_value(self.animal)
        except:
            # if animal is not in list
            self.AnimalChoiceWidget.set_value(animals[0])
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
        
        FormLayout.addRow("self terminate", self.selfTerminateCheckBox)
        Df = pd.DataFrame([['after (min) ',  45,   'int32'],
                           ['after (ul) ',   500, 'int32'],
                           ['after #trials ',0,    'int32']],
                           columns=['name','value','dtype'])

        self.selfTerminateEdit = ValueEditFormLayout(self, DataFrame=Df)
        FormLayout.addRow(self.selfTerminateEdit)

        # positioning and deco
        self.setWindowTitle("Settings")
        self.move(10, 10) # some corner of the screen ... 
        
        # calling animal changed again to trigger correct layouting
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        self.AnimalChoiceWidget.set_value(self.animal)
        
        # TODO
        # test if they can't be called wo the check and move above lines 
        # up to the corresponding point 

        # enforce function calls if first animal
        if animals.index(self.animal) == 0: # to call animal_changed even if the animal is the first in the list
            self.animal_changed()
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
        self.RunInfo = RunInfoWidget(self)

        print(" --- RUN --- ")
        print("Task: ",self.task)
        print("Animal: ",self.animal)
        
        # make folder structure
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # underscores in times bc colons kill windows paths ...
        self.run_folder = Path(self.config['paths']['animals_folder']) / self.animal / '_'.join([date_time,self.task])
        
        os.makedirs(self.run_folder,exist_ok=True)

        for Controller in self.Controllers:
            print("running controller: ", Controller.name)
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
        self.animal_meta.to_csv(out_path)

        self.timer.stop()

        # Flags
        self.running = False

        # stop and take down controllers
        for Controller in self.Controllers:
            Controller.stop()
            Controller.close()

        self.task_changed() # this reinitialized all controllers

    def animal_changed(self):
        self.config['current']['animal'] = self.AnimalChoiceWidget.get_value()
        self.animal = self.config['current']['animal']
        meta_path = Path(self.config['paths']['animals_folder']) / self.animal / 'animal_meta.csv'
        self.animal_meta = pd.read_csv(meta_path)

        # displaying previous sessions info
        if hasattr(self,'AnimalInfoWidget'):
            self.AnimalInfoWidget.close()

        self.AnimalInfoWidget = AnimalInfoWidget(self, self.config)
        self.Children = []
        self.Children.append(self.AnimalInfoWidget)

        # TODO get animal metadata
        # animal folder, get all runs, get meta from the folder plus the last weight
        print("Animal: ", self.animal)

    def task_changed(self):
        # first check if task is running, if yes, don't do anything
        if self.running == True:
            print("Warning: trying to change a running task!")
            return None

        else:
            # get task
            self.config['current']['task'] = self.TaskChoiceWidget.get_value()
            self.task = self.config['current']['task']
            self.task_folder = Path(self.config['paths']['tasks_folder']) / self.task
            print("Currently selected Task: ", self.task)

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
                print("initializing " + section)
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
    def __init__(self, parent, config):
        super(AnimalInfoWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.config = config
        self.initUI()

    def initUI(self):
        # self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Table = QtWidgets.QTableView()
        self.Layout = QtWidgets.QHBoxLayout()
        # self.Layout.addWidget(self.TextBrowser)
        self.Layout.addWidget(self.Table)
        self.setLayout(self.Layout)
        self.setWindowTitle("Animal info")
        self.update()
        self.show()
        self.layout()

    def layout(self):
        big_gap = int(self.config['ui']['big_gap'])
        self.resize(self.parent().width(),self.sizeHint().height())
        utils.tile_Widgets([self.parent(),self], how='vertically', gap=big_gap)

    def update(self):
        # TODO get a list of past sessions and parse them
        # TODO also rename sessions_df
        current_animal_folder = Path(self.config['paths']['animals_folder']) / self.parent().animal
        try:
            sessions_df = utils.get_sessions(current_animal_folder)
            # lines = sessions_df['task'].to_list()
            lines = sessions_df['task'].tolist()
            lines = '\n'.join(lines)
            model = PandasModel(sessions_df[['date','time','task']])
            self.Table.setModel(model)
        except ValueError:
            pass

"""
 
 ########   #######  ########  ##     ## ########   ######  
 ##     ## ##     ## ##     ## ##     ## ##     ## ##    ## 
 ##     ## ##     ## ##     ## ##     ## ##     ## ##       
 ########  ##     ## ########  ##     ## ########   ######  
 ##        ##     ## ##        ##     ## ##              ## 
 ##        ##     ## ##        ##     ## ##        ##    ## 
 ##         #######  ##         #######  ##         ######  
 
"""

class RunInfoWidget(QtWidgets.QDialog):
    """ collects all that is left required manual input by the user upon run """
    # TODO Implement this!!
    # idea: also this logs stuff about the session
    # after each run, a session_meta df is created containing
    # animal id, task, date, start, stop, duration, ntrials

    def __init__(self, parent):
        super(RunInfoWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()

    def initUI(self):
        self.FormLayout = QtWidgets.QFormLayout()
        self.FormLayout.setVerticalSpacing(10)
        self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

        # Fields
        # self.EarTagWidget = ValueEdit('', 'U', self)
        # self.FormLayout.addRow("Ear tag", self.EarTagWidget)
        self.WeigthEditWidget = ValueEdit(30, 'f4', self)
        self.FormLayout.addRow("Weight (g)", self.WeigthEditWidget)

        FormWidget = QtWidgets.QWidget()
        FormWidget.setLayout(self.FormLayout)

        Btn = QtWidgets.QPushButton()
        Btn.setText('Done')
        Btn.clicked.connect(self.done_btn_clicked)

        Full_Layout = QtWidgets.QVBoxLayout()
        Full_Layout.addWidget(FormWidget)
        Full_Layout.addWidget(Btn)
        self.setLayout(Full_Layout)

        self.setWindowTitle("Run info")
        self.exec()

    def done_btn_clicked(self):
        meta = self.parent().animal_meta
        weight = self.WeigthEditWidget.get_value()
        if 'current_weight' not in meta['name'].values:
            ix = meta.shape[0]
            meta.loc[ix] = ['current_weight', weight]
        else:
            meta.loc[meta['name'] == 'current_weight','value'] = weight
        self.accept()


# class NewAnimalWidget(QtWidgets.QWidget):
#         # think about completely deprecating this for now 
#     def __init__(self, parent):
#         super(NewAnimalWidget, self).__init__(parent=parent)
#         self.setWindowFlags(QtCore.Qt.Window)
#         self.initUI()

#     def initUI(self):
#         self.FormLayout = QtWidgets.QFormLayout()
#         self.FormLayout.setVerticalSpacing(10)
#         self.FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)

#         # read in template
#         Df = pd.read_csv(os.path.join(self.parent().profiles[self.parent().user]['animals_folder'],'animal_meta_template.csv'))

#         for i, row in Df.iterrows():
#             self.FormLayout.addRow(row['name'], ValueEdit(str(row['value']), row['dtype'], self))

#         # old code
#         # self.FormLayout.addRow("ID", ValueEdit(0, 'i4', self))
#         # self.FormLayout.addRow("Ear tag", ValueEdit('LF', 'U', self))
#         # self.FormLayout.addRow("Genotype", ValueEdit('-cre', 'U', self))
#         # self.FormLayout.addRow("Date of birth", ValueEdit('YYYY_MM_DD', 'U', self))
#         # self.FormLayout.addRow("Initial weight", ValueEdit(30, 'f4', self))
#         # self.FormLayout.addRow("Current weight", ValueEdit(30, 'f4', self))

#         FormWidget = QtWidgets.QWidget()
#         FormWidget.setLayout(self.FormLayout)

#         Full_Layout = QtWidgets.QVBoxLayout()
#         Full_Layout.addWidget(FormWidget)

#         Btn = QtWidgets.QPushButton()
#         Btn.setText('Done')
#         Btn.clicked.connect(self.create_animal)

#         Full_Layout.addWidget(Btn)
#         self.setLayout(Full_Layout)
#         self.setWindowTitle("New Animal")
#         self.show()

#     def get_entries(self):
#         """ turn UI entries into a dataframe """
#         # FIXME make sure that this is dtype correct!
#         # TODO think about writing a general function that turns a FormLayout to a DataFrame and the other way around
#         rows = []
#         for i in range(self.FormLayout.rowCount()):
#             label = self.FormLayout.itemAt(i, 0).widget()
#             widget = self.FormLayout.itemAt(i, 1).widget()
#             rows.append([label.text(), widget.get_value(), widget.get_value().dtype])

#         Df = pd.DataFrame(rows, columns=['name', 'value', 'dtype'])
#         return Df

#     def create_animal(self):
#         entries = self.get_entries()
#         animal_meta = pd.Series(entries['value'])
#         animal_meta.index = entries['name']
#         animal_ID = str(animal_meta['ID'])

#         # write data
#         animal_folder = os.path.join(self.parent().profiles[self.parent().user]['animals_folder'],animal_ID)
#         try:
#             os.makedirs(animal_folder, exist_ok=False)
#         except FileExistsError:
#             Error = "Animal already exists!"
#             ErrorW = ErrorWidget(Error, parent=self)

#         entries.to_csv(os.path.join(animal_folder, 'animal_meta.csv'),index=None)

#         # update parent
#         self.parent().AnimalChoiceWidget.choices.append(animal_ID)
#         self.parent().AnimalChoiceWidget.addItem(animal_ID)
#         self.parent().AnimalChoiceWidget.set_value(animal_ID)
#         self.close()

"""
 
 ##     ## ######## #### ##       #### ######## ##    ##    ##      ## #### ########   ######   ######## ########  ######  
 ##     ##    ##     ##  ##        ##     ##     ##  ##     ##  ##  ##  ##  ##     ## ##    ##  ##          ##    ##    ## 
 ##     ##    ##     ##  ##        ##     ##      ####      ##  ##  ##  ##  ##     ## ##        ##          ##    ##       
 ##     ##    ##     ##  ##        ##     ##       ##       ##  ##  ##  ##  ##     ## ##   #### ######      ##     ######  
 ##     ##    ##     ##  ##        ##     ##       ##       ##  ##  ##  ##  ##     ## ##    ##  ##          ##          ## 
 ##     ##    ##     ##  ##        ##     ##       ##       ##  ##  ##  ##  ##     ## ##    ##  ##          ##    ##    ## 
  #######     ##    #### ######## ####    ##       ##        ###  ###  #### ########   ######   ########    ##     ######  
 
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

class StringChoiceWidget(QtWidgets.QComboBox):
    """ A QComboBox with convenience setter and getter """

    def __init__(self, parent, choices):
        super(StringChoiceWidget, self).__init__(parent=parent)
        self.choices = choices

        for choice in self.choices:
            self.addItem(choice)

    def get_value(self):
        return self.choices[self.currentIndex()]

    def set_value(self, value):
        try:
            self.setCurrentIndex(self.choices.index(value))
        except ValueError:
            self.setCurrentIndex(0)


class ValueEdit(QtWidgets.QLineEdit):
    """ a QLineEdit that keeps track of the numpy dtype and returns accordingly """

    def __init__(self, value, dtype, parent):
        super(ValueEdit, self).__init__(parent=parent)
        self.dtype = dtype
        self.set_value(value)

    def get_value(self):
        self.value = sp.array(self.text(), dtype=self.dtype)
        return self.value

    # def get_dtype(self):
    #     return self.dtype

    def set_value(self, value):
        self.value = sp.array(value, dtype=self.dtype)
        self.setText(str(self.value))


class ValueEditFormLayout(QtWidgets.QFormLayout):
    """ a QFormLayout consisting of ValueEdit rows, to be initialized with a pd.DataFrame 
    with columns name and value, optional dtype (numpy letter codes) """

    def __init__(self, parent, DataFrame):
        super(ValueEditFormLayout,self).__init__(parent=parent)
        self.Df = DataFrame # model

        # if DataFrame does not contain a dtype column, set it to strings
        # TODO figure out when is this actually needed
        # utils.debug_trace()
        if 'dtype' not in self.Df.columns:
            maxlen = max([len(el) for el in self.Df['name']])
            self.Df['dtype'] = 'U'+str(maxlen)

        self.initUI()
    
    def initUI(self):
        self.setVerticalSpacing(10)
        self.setLabelAlignment(QtCore.Qt.AlignRight)

        # init the view
        for i, row in self.Df.iterrows():
            self.addRow(row['name'], ValueEdit(row['value'], row['dtype'], self.parent()))

    def set_entry(self, name, value):
        """ controller function - update both view and model """
        try:
            # get index
            ix = list(self.Df['name']).index(name)
            
            # update model 
            dtype = self.itemAt(ix,1).widget().dtype
            self.Df.loc[ix,'value'] = sp.array(value, dtype=dtype) 
            
            # update view
            self.itemAt(ix,1).widget().set_value(value)

        except ValueError:
            print("attempting to set a name, value not in Df:" + str(name) + " " + str(value))


    def set_entries(self, Df):
        # test compatibility first
        if not sp.all(Df['name'].sort_values().values == self.Df['name'].sort_values().values):
            print("can't set entries bc they are not equal ... this indicates some major bug")
            utils.debug_trace()
        
        # update the model
        self.Df = Df

        # update the view
        for i, row in Df.iterrows():
            self.set_entry(row['name'], row['value'])

    def get_entry(self, name):
        # controller function - returns a pd.Series
        ix = list(self.Df['name']).index(name)
        return self.Df.loc[ix]

    def get_entries(self):
        self.update_model()
        return self.Df

    def update_model(self):
        """ updates model based on UI entries """
        for i in range(self.rowCount()):
            label = self.itemAt(i, 0).widget()
            widget = self.itemAt(i, 1).widget()
            self.set_entry(label.text(), widget.get_value())

class ErrorWidget(QtWidgets.QMessageBox):
    # TODO implement me
    def __init__(self, error_msg, parent=None):
        super(ErrorWidget,self).__init__(parent=parent)
        self.setText(error_msg)
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setStandardButtons(QtWidgets.QMessageBox.Close)
        self.buttonClicked.connect(self.crash)
        self.show()

    def crash(self):
        # TODO log crash error msg
        sys.exit()


class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    source: https://stackoverflow.com/questions/31475965/fastest-way-to-populate-qtableview-from-pandas-data-frame
    """
    def __init__(self, data, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data.values)

    def columnCount(self, parent=None):
        return self._data.columns.size

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data.values[index.row()][index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._data.columns[col]
        return None