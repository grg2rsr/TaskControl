import sys, os
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
import subprocess
from pathlib import Path
from Utils import utils

class BonsaiController(QtWidgets.QWidget):
    """ a Widget without UI that launches a bonsai sketch """
    
    def __init__(self, parent, config, task_config):
        super(BonsaiController, self).__init__(parent=parent)
        self.name = "BonsaiController"
        self.config = config
        self.task_config = task_config

        utils.printer("init bonsai controller","debug")

    def Run(self, folder):
        """ folder is the logging folder """
        utils.printer("running bonsai controller","debug")

        # animal = self.config['current']['animal']
        task = self.config['current']['task']
        task_folder = Path(self.config['paths']['tasks_folder']) / task
        save_path = folder / 'bonsai_' # this needs to be fixed in bonsai # FIXME TODO
        
        # constructing the bonsai exe string
        parameters = "-p:save_path=\""+str(save_path)+"\""

        # com port for firmata
        if 'firmata_arduino_port' in dict(self.config['connections']).keys():
            parameters = parameters + " -p:com_port="+self.config['connections']['firmata_arduino_port']

        # com port for load cell
        if 'harp_loadcell_port' in dict(self.config['connections']).keys():
            parameters = parameters + " -p:LC_com_port="+self.config['connections']['harp_loadcell_port']

        # getting other manually set params
        variables_path = task_folder / "Bonsai" / "interface_variables.ini"
        if variables_path.exists():
            with open(variables_path,'r') as fH:
                params = fH.readlines()
                params = [p.strip() for p in params]
            for line in params:
                parameters = parameters + " -p:%s" % line

        bonsai_exe = Path(self.config['system']['bonsai_cmd'])
        bonsai_workflow = task_folder / 'Bonsai' / self.task_config['workflow_fname']

        command = ' '.join([str(bonsai_exe),str(bonsai_workflow),"--start",parameters,"&"])

        utils.printer("bonsai command: %s " % command, 'msg')
        log = open(save_path.with_name('bonsai_log.txt') ,'w')
        theproc = subprocess.Popen(command, shell = True, stdout=log, stderr=log)
        # theproc.communicate() # this hangs shell on windows machines, TODO check if this is true for linux
        # curious, it should do the opposite ... 

    pass

    # def position(self):
    #     pass

    def closeEvent(self, event):
        """ """
        utils.printer("closing bonsai controller","debug")
        self.close()

    def stop(self):
        """ """
        utils.printer("stopping bonsai controller","debug")
        pass