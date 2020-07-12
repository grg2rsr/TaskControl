import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import subprocess
from pathlib import Path
import shutil
import struct

class BonsaiController(QtWidgets.QWidget):
    """ a Widget without UI that launches a bonsai sketch """
    
    def __init__(self, parent, config, task_config):
        super(BonsaiController, self).__init__(parent=parent)
        self.name = BonsaiController
        self.config = config
        self.task_config = task_config

    def Run(self, folder):
        """ folder is the logging folder """

        animal = self.config['current']['animal']
        task = self.config['current']['task']
        task_folder = Path(self.config['paths']['tasks_folder']) / task
        save_path = folder / 'bonsai_' # this needs to be fixed in bonsai # FIXME TODO
       
        # constructing the bonsai exe string
        parameters = "-p:save_path=\""+str(save_path)+"\""

        # if 'com_port' in task_config.keys():
        parameters = parameters+" -p:com_port="+self.config['connections']['firmata_arduino_port']

        bonsai_exe = Path(self.config['system']['bonsai_cmd'])
        bonsai_workflow = task_folder / 'Bonsai' / self.task_config['workflow_fname']

        command = ' '.join([str(bonsai_exe),str(bonsai_workflow),"--start",parameters,"&"])

        print("bonsai command:")
        print(command)

        theproc = subprocess.Popen(command, shell = True)
        # theproc.communicate() # this hangs shell on windows machines, TODO check if this is true for linux
        # curious, it should do the opposite ... 

    pass

    def closeEvent(self, event):
        # stub
        self.close()

    def stop(self):
        """ """
        pass