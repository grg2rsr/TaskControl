from PyQt5 import QtWidgets
import subprocess
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


class BonsaiController(QtWidgets.QWidget):
    """a Widget without UI that launches a bonsai sketch"""

    def __init__(self, parent, sys_config, task_config, box_config):
        super(BonsaiController, self).__init__(parent=parent)
        self.name = "BonsaiController"
        self.sys_config = sys_config
        self.task_config = task_config
        self.box_config = box_config

    def Run(self, folder):
        """folder is the logging folder"""
        # animal = self.sys_config['current']['animal']
        task = self.sys_config["current"]["task"]
        task_folder = Path(self.sys_config["paths"]["tasks_folder"]) / task
        save_path = folder / "bonsai_"  # this needs to be fixed in bonsai # FIXME TODO

        # constructing the bonsai exe string
        parameters = '-p:save_path="' + str(save_path) + '"'

        # com port for firmata
        if "Firmata" in dict(self.box_config).keys():
            parameters = (
                parameters + " -p:com_port=" + self.box_config["Firmata"]["com_port"]
            )

        # com port for load cell
        if "Harp" in dict(self.box_config).keys():
            parameters = (
                parameters + " -p:LC_com_port=" + self.box_config["Harp"]["com_port"]
            )

        # getting other manually set params
        variables_path = task_folder / "Bonsai" / "interface_variables.ini"
        if variables_path.exists():
            with open(variables_path, "r") as fH:
                params = fH.readlines()
                params = [p.strip() for p in params]
            for line in params:
                parameters = parameters + " -p:%s" % line

        bonsai_exe = Path(self.sys_config["system"]["bonsai_cmd"])
        bonsai_workflow = task_folder / "Bonsai" / self.task_config["workflow_fname"]

        command = " ".join(
            [str(bonsai_exe), str(bonsai_workflow), "--start", parameters, "&"]
        )

        logger.info("bonsai command: %s " % command)
        log = open(save_path.with_name("bonsai_log.txt"), "w")
        theproc = subprocess.Popen(command, shell=True, stdout=log, stderr=log)
        # theproc.communicate() # this hangs shell on windows machines, TODO check if this is true for linux
        # curious, it should do the opposite ...

    pass

    # def position(self):
    #     pass

    def closeEvent(self, event):
        """ """
        self.close()

    def stop(self):
        """ """
        pass
