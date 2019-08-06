import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import Widgets

import subprocess
import datetime
from pathlib import Path
import shutil

import functions

class BonsaiController(QtWidgets.QWidget):
    def __init__(self, parent):
        super(BonsaiController, self).__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Bonsai controller")
        self.Layout = QtWidgets.QHBoxLayout()
        self.setMinimumWidth(300) # FIXME hardcoded!

        # dummy button
        Btn = QtWidgets.QPushButton('dummy')
        # sketch selector? not really wanted actually ... 
        
        self.Layout.addWidget(Btn)
        self.setLayout(self.Layout)
        self.show()

    def Run(self,folder):
        """ folder is the logging folder """

        animal = self.parent().animal
        task = self.parent().task
        task_config = self.parent().task_config['Bonsai']
        task_folder = os.path.join(self.parent().profile['tasks_folder'], task)
       
        fname = animal+'.raw'
        
        folder = Path(folder)
        out_path = folder.joinpath(animal+'.raw') # this needs to be fixed in bonsai

        # constructing the bonsai exe string
        parameters = "-p:save_path=\""+str(out_path)+"\""
        bonsai_exe = self.parent().profiles['General']['bonsai_cmd']
        
        bonsai_workflow = os.path.join(task_folder,'Bonsai',task_config['workflow_fname'])
        bonsai_workflow = "\""+bonsai_workflow+"\""

        command = ' '.join([str(Path(bonsai_exe)),str(Path(bonsai_workflow)),"--start",parameters,"&"])

        theproc = subprocess.Popen(command, shell = True)
        # theproc.communicate() # this hangs shell on windows machines, TODO check if this is true for linux

    pass

# FUTURE TODO implementation will depend on harp
class LoadCellController(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LoadCellController, self).__init__(parent=parent)


        # self.LoadCellComPortChoiceWidget = StringChoiceWidget(self, choices=com_ports)
        # self.LoadCellComPortChoiceWidget.currentIndexChanged.connect(self.load_cell_com_port_changed)
        # self.LoadCellComPortChoiceWidget.set_value(self.profiles['General']['last_lc_com_port'])
        # FormLayout.addRow('Load Cell COM port',self.LoadCellComPortChoiceWidget)

    # def load_cell_com_port_changed(self):
    #     self.profiles['General']['last_lc_com_port'] = self.LoadCellComPortChoiceWidget.get_value()
    pass