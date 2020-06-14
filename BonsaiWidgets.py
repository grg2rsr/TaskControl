import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import subprocess
from pathlib import Path
import shutil
import struct

class BonsaiController(QtWidgets.QWidget):
    """ a Widget without UI that launches a bonsai sketch """
    
    def __init__(self, parent):
        super(BonsaiController, self).__init__(parent=parent)

    def Run(self,folder):
        """ folder is the logging folder """

        animal = self.parent().animal
        task = self.parent().task
        task_config = self.parent().task_config['Bonsai']
        task_folder = Path(self.parent().profile['tasks_folder']).joinpath(task)
        out_path = folder.joinpath('bonsai_') # this needs to be fixed in bonsai # FIXME TODO
       
        # constructing the bonsai exe string
        parameters = "-p:save_path=\""+str(out_path)+"\""
        if 'com_port' in task_config.keys():
            parameters = parameters+" -p:com_port="+task_config['com_port']

        bonsai_exe = Path(self.parent().profiles['General']['bonsai_cmd'])
        bonsai_workflow = task_folder.joinpath('Bonsai',task_config['workflow_fname'])

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