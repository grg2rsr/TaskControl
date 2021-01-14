import sys, os
import configparser
from pathlib import Path

from PyQt5 import QtWidgets
from Widgets import *

class TaskControlApp(QtWidgets.QApplication):
    def __init__(self, *args, config_path=None):
        super(TaskControlApp, self).__init__(*args)

        # read config.ini
        self.config_path = Path(config_path)
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

        print(" --- this is TaskControl --- ")
        utils.printer("using config: %s" % config_path, 'msg')

        # launch GUI
        self.Settings_Widget = SettingsWidget(self, self.config)

        # hack - store default box settings
        self.default_box_config = self.config['box']

        # on close - TODO check if obsolete with proper QT parent child structure
        self.setQuitOnLastWindowClosed(False)
        self.lastWindowClosed.connect(self.onLastClosed)
        self.exec_()

    def onLastClosed(self):
        # restore box defaults
        for key, value in self.default_box_config.items():
            self.config['box'][key] = value

        # write current config to disk
        with open(self.config_path, 'w') as fH:
            self.config.write(fH)
        self.exit()

if __name__ == "__main__":
    import argparse
    config_path = "config.ini" # to be set locally
    
    # argparsing
    parser = argparse.ArgumentParser(description=' xXx Unified TaskControl xXx ')
    parser.add_argument("-p", default=config_path, action='store', dest="config_path", help='set the path to the config.ini file')
    args = parser.parse_args()

    # run the application
    TaskControl = TaskControlApp([], config_path=args.config_path)