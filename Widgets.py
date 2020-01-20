import sys, os
import datetime
import shutil
import configparser

import scipy as sp
import pandas as pd

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

from functions import dtype_map
import functions
import utils

# import VisWidgetss
import ArduinoWidgets
import HardwareWidgets

"""
.___  ___.      ___       __  .__   __.    ____    __    ____  __   _______   _______  _______ .___________.    _______.
|   \/   |     /   \     |  | |  \ |  |    \   \  /  \  /   / |  | |       \ /  _____||   ____||           |   /       |
|  \  /  |    /  ^  \    |  | |   \|  |     \   \/    \/   /  |  | |  .--.  |  |  __  |  |__   `---|  |----`  |   (----`
|  |\/|  |   /  /_\  \   |  | |  . `  |      \            /   |  | |  |  |  |  | |_ | |   __|      |  |        \   \
|  |  |  |  /  _____  \  |  | |  |\   |       \    /\    /    |  | |  '--'  |  |__| | |  |____     |  |    .----)   |
|__|  |__| /__/     \__\ |__| |__| \__|        \__/  \__/     |__| |_______/ \______| |_______|    |__|    |_______/

"""

class SettingsWidget(QtWidgets.QWidget):
    """
    The main toplevel widget. Is parent of all controllers. Brings together all animal and task related information
    some design notes:
    each user has a profile which points to the folder of tasks and animals
    """
    # FIXME does not have parent? - fix inheritance from TaskControl
    def __init__(self, main, profiles):
        super(SettingsWidget, self).__init__()
        self.profiles = profiles # a configparser dict
        self.profile = None
        self.user = None
        self.task = None # the task that is being run
        self.main = main
        self.logging = True
        self.running = False
        self.initUI()

    def initUI(self):
        FormLayout = QtWidgets.QFormLayout(self)
        FormLayout.setVerticalSpacing(10)
        FormLayout.setLabelAlignment(QtCore.Qt.AlignRight)
        self.setLayout(FormLayout)

        # get profiles
        users = self.profiles['General']['users'].split(',')
        users = [user.strip() for user in users]
        self.user = self.profiles['General']['last_user']
        self.profile = self.profiles[self.user]

        self.UserChoiceWidget = StringChoiceWidget(self, choices=users)
        self.UserChoiceWidget.currentIndexChanged.connect(self.user_changed)
        self.UserChoiceWidget.set_value(self.user)
        FormLayout.addRow('User', self.UserChoiceWidget)

        # animal selector
        animals = utils.get_animals(self.profile['animals_folder'])
        self.animal = self.profile['last_animal']
        self.AnimalChoiceWidget = StringChoiceWidget(self, choices=animals)
        self.AnimalChoiceWidget.currentIndexChanged.connect(self.animal_changed)
        self.AnimalChoiceWidget.set_value(self.animal)
        if animals.index(self.animal) == 0: # to call animal_changed even if the animal is the first in the list
            self.animal_changed()
        FormLayout.addRow('Animal', self.AnimalChoiceWidget)

        # TODO reimplement this functionality
        # # New Animal Button
        # NewAnimalBtn = QtWidgets.QPushButton(self)
        # NewAnimalBtn.setText('New animal')
        # FormLayout.addRow(NewAnimalBtn)
        # NewAnimalBtn.clicked.connect(self.new_animal)
        # self.animal_changed()

        # task selector
        tasks = utils.get_tasks(self.profile['tasks_folder'])
        self.task = self.profile['last_task']
        self.TaskChoiceWidget = StringChoiceWidget(self, choices=tasks)
        self.TaskChoiceWidget.currentIndexChanged.connect(self.task_changed)
        self.TaskChoiceWidget.set_value(self.task)
        if tasks.index(self.task) == 0:
            self.task_changed()
        FormLayout.addRow('Task', self.TaskChoiceWidget)

        # logging checkbox
        self.logCheckBox = QtWidgets.QCheckBox("logging enabled")
        self.logCheckBox.setChecked(True)
        self.logCheckBox.stateChanged.connect(self.logCheckBox_changed)
        FormLayout.addRow(self.logCheckBox)

        # run button
        RunBtn = QtWidgets.QPushButton(self)
        RunBtn.setStyleSheet("background-color: yellow")
        RunBtn.setText('Run task')
        FormLayout.addRow(RunBtn)
        RunBtn.clicked.connect(self.Run)

        # plot button
        Plot_button = QtWidgets.QPushButton(self)
        Plot_button.clicked.connect(self.update_plot)
        Plot_button.setText('Plot performance')
        FormLayout.addRow(Plot_button)

        # TODO register a range of task specific plotters
        # or clicking this fires all plotters associated to the task

        # positioning and deco
        self.setWindowTitle("Settings")
        self.move(10, 10) # some corner of the screen ... 

        self.show()

        # FIXME this contains hardcoding stuff ... 
        # window scaling
        if hasattr(self, 'ArduinoController'):
            functions.tile_Widgets(self.ArduinoController, self, where='right',gap=100)
            functions.tile_Widgets(self.ArduinoController.VariableController, self.ArduinoController, where='below',gap=50)
            functions.scale_Widgets([self.ArduinoController.VariableController, self.ArduinoController])
        
        if hasattr(self, 'BonsaiController'):
            functions.tile_Widgets(self.BonsaiController, self.ArduinoController, where='right',gap=25)
        
        if hasattr(self, 'LoadCellController'):
            functions.tile_Widgets(self.LoadCellController, self.ArduinoController, where='right',gap=25)
            functions.tile_Widgets(self.LoadCellController.LoadCellMonitor, self.LoadCellController, where='below',gap=50)

        if hasattr(self, 'DisplayController'):
            functions.tile_Widgets(self.DisplayController, self.LoadCellController, where='right',gap=25)

        # needs to be called - again
        functions.tile_Widgets(self.AnimalInfoWidget,self, where='below', gap=50)
        functions.scale_Widgets([self.AnimalInfoWidget,self])

    def update_plot(self):
        # TODO deal with this entire functionality
        # https://matplotlib.org/2.1.0/gallery/user_interfaces/embedding_in_qt5_sgskip.html
        self.PlotWidget = VisWidgets.MyMplCanvas(self)

    def closeEvent(self,event):
        # TODO iterate over controllers and close all
        # for this, a list of registered task needs list of registered controllers and visualizers

        if hasattr(self, 'ArduinoController'):
            self.ArduinoController.close()
        
        if hasattr(self, 'BonsaiController'):
            self.BonsaiController.close()

        if hasattr(self, 'LoadCellController'):
            self.LoadCellController.close()

        if hasattr(self, 'DisplayController'):
            self.DisplayController.close()

        self.main.exit()


    def Run(self):
        """
        + read the entries in the params control widget
        + write the arduino file to the correct place (user specific animal/task/time)
        + upload code to arduino
        + listen to port
        """

        if self.running == False:
            print(" --- RUN --- ")
            print("Task: ",self.task)
            print("Animal: ",self.animal)
            
            # TODO runanimal popup here
            # self.RunInfo = RunInfoWidget(self)

            # make folder structure
            date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") # underscores in times bc colons kill windows paths ...
            folder = os.path.join(self.profile['animals_folder'],self.animal,date_time+'_'+self.task)
            os.makedirs(folder,exist_ok=True)

            # TODO generalize this section. Currently all possible hardware controllers need to be called seperately
            for section in self.task_config.sections():
                if section == 'Arduino':
                    self.ArduinoController.Run(folder)
                    print("running ArduinoController")

                if section == 'Bonsai':
                    self.BonsaiController.Run(folder)
                    print("running BonsaiController")

                if section == 'LoadCell':
                    self.LoadCellController.Run(folder)
                    print("running BonsaiController")

                if section == 'Display':
                    self.DisplayController.Run(folder)
                    print("running DisplayController")

                # place here other controllers

            self.running = True
            # gray out button, set to running
        else:
            # Here - change button to stop
            print("Task is already running! ")

    def logCheckBox_changed(self):
        if self.logCheckBox.checkState() == 2:
            self.logging = True
        else:
            self.logging = False

    def user_changed(self):
        self.user = self.UserChoiceWidget.get_value()
        self.AnimalChoiceWidget.set_value(self.profile['last_animal'])
        self.profiles['General']['last_user'] = self.user
        self.profile = self.profiles[self.user]
        print("User: ",self.user)

    # excluded functionality for now
    # def new_animal(self):
    #     """ open the new animal popup """
    #     self.NewAnimal = NewAnimalWidget(self)

    def get_animal_meta(self):
        # TODO FUTURE make a function of Animal object
        meta_path = os.path.join(self.profile['animals_folder'],self.animal,'animal_meta.csv')
        return pd.read_csv(meta_path)

    def animal_changed(self):
        self.animal = self.AnimalChoiceWidget.get_value()
        self.profile['last_animal'] = self.animal
        self.animal_meta = self.get_animal_meta()

        # displaying previous sessions info
        if hasattr(self,'AnimalInfoWidget'):
            self.AnimalInfoWidget.close()

        self.AnimalInfoWidget = AnimalInfoWidget(self)

        # TODO get animal metadata
        # animal folder, get all runs, get meta from the folder plus the last weight
        print("Animal: ", self.animal)

    def task_changed(self):
        """ upon task change: look for required controllers, take all present down and instantiate the new ones """
        self.task = self.TaskChoiceWidget.get_value()
        self.task_folder = os.path.join(self.profile['tasks_folder'],self.task)

        # parse task config file
        self.task_config = configparser.ConfigParser()
        self.task_config.read(os.path.join(self.task_folder, 'task_config.ini'))

        # TODO generalize - make a list of controllers
        for section in self.task_config.sections():
            # place here all possible controllers ...
            # closes present controllers and reopens
            if section == 'Arduino':
                if hasattr(self,'ArduinoController'):
                    self.ArduinoController.close()
                self.ArduinoController = ArduinoWidgets.ArduinoController(self)
                print("initializing ArduinoController")
                # functions.tile_Widgets(self.ArduinoController, self,where='right',gap=25)
                # functions.tile_Widgets(self.ArduinoController.VariableController, self.ArduinoController, where='below',gap=50)
                # functions.scale_Widgets([self.ArduinoController.VariableController, self.ArduinoController])

            if section == 'Bonsai':
                if hasattr(self,'BonsaiController'):
                        self.BonsaiController.close()
                self.BonsaiController = HardwareWidgets.BonsaiController(self)
                print("initializing BonsaiController")

            if section == 'LoadCell': # here: this 
                self.LoadCellController = HardwareWidgets.LoadCellController(self)
                print("initializing LoadCellController")

            if section == 'Display':
                self.DisplayController = HardwareWidgets.DisplayController(self)

        self.profile['last_task'] = self.task
        print("Task: ", self.task)


class AnimalInfoWidget(QtWidgets.QWidget):
    """ displays some interesing info about the animal: list of previous sessions """
    def __init__(self, parent):
        super(AnimalInfoWidget, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()

    def initUI(self):
        # self.TextBrowser = QtWidgets.QTextBrowser(self)
        self.Table = QtWidgets.QTableView()

        self.Layout = QtWidgets.QHBoxLayout()
        # self.Layout.addWidget(self.TextBrowser)
        self.Layout.addWidget(self.Table)
        self.setLayout(self.Layout)
        self.setWindowTitle("Animal info")
        self.show()
        self.update()

        functions.tile_Widgets(self, self.parent(), where='below',gap=100)

    def update(self):
        # TODO get a list of past sessions and parse them
        current_animal_folder = os.path.join(self.parent().profile['animals_folder'],self.parent().animal)
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
.______     ______   .______    __    __  .______     _______.
|   _  \   /  __  \  |   _  \  |  |  |  | |   _  \   /       |
|  |_)  | |  |  |  | |  |_)  | |  |  |  | |  |_)  | |   (----`
|   ___/  |  |  |  | |   ___/  |  |  |  | |   ___/   \   \
|  |      |  `--'  | |  |      |  `--'  | |  |   .----)   |
| _|       \______/  | _|       \______/  | _|   |_______/

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
        self.EarTagWidget = ValueEdit('', 'U', self)
        self.FormLayout.addRow("Ear tag", self.EarTagWidget)
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

        self.setWindowTitle(" Run info ")
        self.exec()

    def done_btn_clicked(self):
        meta = self.parent().animal_meta
        correct_ear_tag = meta.set_index('name').loc['Ear tag'].value
        entered_ear_tag = str(self.EarTagWidget.get_value()).upper()
        if  entered_ear_tag != correct_ear_tag:
            print("wrong ear tag or wrong mouse!")
        else:
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
 __    __  .___________. __   __       __  .___________.____    ____    ____    __    ____  __   _______   _______  _______ .___________.    _______.
|  |  |  | |           ||  | |  |     |  | |           |\   \  /   /    \   \  /  \  /   / |  | |       \ /  _____||   ____||           |   /       |
|  |  |  | `---|  |----`|  | |  |     |  | `---|  |----` \   \/   /      \   \/    \/   /  |  | |  .--.  |  |  __  |  |__   `---|  |----`  |   (----`
|  |  |  |     |  |     |  | |  |     |  |     |  |       \_    _/        \            /   |  | |  |  |  |  | |_ | |   __|      |  |        \   \
|  `--'  |     |  |     |  | |  `----.|  |     |  |         |  |           \    /\    /    |  | |  '--'  |  |__| | |  |____     |  |    .----)   |
 \______/      |__|     |__| |_______||__|     |__|         |__|            \__/  \__/     |__| |_______/ \______| |_______|    |__|    |_______/

"""


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

    def get_dtype(self):
        return self.dtype

    def set_value(self, value):
        self.value = value
        self.setText(str(self.value))


class ValueEditFormLayout(QtWidgets.QFormLayout):
    """ a QFormLayout consisting of ValueEdit rows, to be initialized with a pd.DataFrame 
    with columns name and value, optional dtype (numpy letter codes) """

    def __init__(self, parent, DataFrame):
        super(ValueEditFormLayout,self).__init__(parent=parent)
        self.Df = DataFrame

        # if DataFrame does not contain a dtype column, set it to strings
        if 'dtype' not in self.Df.columns:
            maxlen = max([len(el) for el in self.Df['name']])
            self.Df['dtype'] = 'U'+str(maxlen)

        self.initUI()
    
    def initUI(self):
        self.setVerticalSpacing(10)
        self.setLabelAlignment(QtCore.Qt.AlignRight)

        for i, row in self.Df.iterrows():
            # dont't do this here because dtype map is for arduino!
            # self.addRow(row['name'], ValueEdit(row['value'], functions.dtype_map[row['dtype']], self.parent()))
            self.addRow(row['name'], ValueEdit(row['value'], row['dtype'], self.parent()))

    def set_entries(self, Df):
        """ sets all values with values according to Df """

        if not sp.all(Df['name'].sort_values().values == self.Df['name'].sort_values().values):
            print("can't set entries bc they are not equal ... this indicates some major bug")
            sys.exit()

        else:
            # Df sorted according to self.Df['name']
            Df_sorted = Df.set_index('name').loc[self.Df['name'].values]
            Df_sorted.reset_index(level=0, inplace=True)
            
            for i, row in Df_sorted.iterrows():
                self.itemAt(i,1).widget().set_value(row['value'])

    def get_entries(self):
        """ returns a pd.DataFrame of the current entries """
        rows = []

        for i in range(self.rowCount()):
            label = self.itemAt(i, 0).widget()
            widget = self.itemAt(i, 1).widget()
            rows.append([label.text(), widget.get_value(), widget.get_dtype()])

        Df = pd.DataFrame(rows, columns=['name', 'value', 'dtype'])
        return Df

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