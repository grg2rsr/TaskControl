import sys, os
import configparser
from pathlib import Path
from PyQt5 import QtWidgets
from Widgets.Widgets import SettingsWidget
from Utils import utils, logging_tools

import logging


class TaskControlApp(QtWidgets.QApplication):
    def __init__(self, *args, config_path=None):
        super(TaskControlApp, self).__init__(*args)

        # read config.ini
        self.Sys = utils.Config(config_path)

        # set up logging
        logger = logging.getLogger()
        # log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_fmt = "%(asctime)s - %(levelname)s - %(message)s"
        date_fmt = '%Y-%m-%d %H:%M:%S'
        # formatter = logging.Formatter(log_fmt, datefmt=date_fmt)
        formatter = logging_tools.ColorFormatter(log_fmt, date_fmt)

        # for printing to stdout
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        logger.setLevel(logging.INFO) # <- this needs to be set as a default argument
        logger.info(" --- this is TaskControl --- ")
        logger.debug("using config: %s" % config_path)

        # launch GUI
        self.Settings_Widget = SettingsWidget(self, self.Sys)

        # on close - TODO check if obsolete with proper QT parent child structure
        self.setQuitOnLastWindowClosed(False)
        self.lastWindowClosed.connect(self.onLastClosed)
        self.exec_()

    def onLastClosed(self):
        # write current config to disk
        self.Sys.save()
        self.exit()

if __name__ == "__main__":
    import argparse
    config_path = Path("configs")  / "config_open_lab_teensy.ini" # config ini has to be a local link
    
    # argparsing
    parser = argparse.ArgumentParser(description=' xXx Unified TaskControl xXx ')
    parser.add_argument("-p", default=config_path, action='store', dest="config_path", help='set the path to the config.ini file')
    args = parser.parse_args()

    # run the application
    TaskControl = TaskControlApp([], config_path=args.config_path)