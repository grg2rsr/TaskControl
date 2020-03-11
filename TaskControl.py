import sys, os
import configparser
from pathlib import Path

from PyQt5 import QtWidgets
from Widgets import *

class TaskControlApp(QtWidgets.QApplication):
    def __init__(self, *args, profiles_fpath=None):
        super(TaskControlApp, self).__init__(*args)

        # parse profiles.ini
        self.profiles_fpath = Path(profiles_fpath)
        profiles = configparser.ConfigParser()
        profiles.read(self.profiles_fpath)

        print(" --- this is TaskControl --- ")
        print("using profile: ", profiles_fpath)

        # launch GUI
        self.Settings_Widget = SettingsWidget(self, profiles)

        # on close - TODO check if obsolete with proper QT parent child structure
        self.setQuitOnLastWindowClosed(False)
        self.lastWindowClosed.connect(self.onLastClosed)
        self.exec_()

    def onLastClosed(self):
        # get the current profiles
        # write to disk for reloading on next startup
        profiles = self.Settings_Widget.profiles
        with open(self.profiles_fpath, 'w') as profiles_fH:
            profiles.write(profiles_fH)
        self.exit()

if __name__ == "__main__":
    import argparse
    # profiles_fpath = 'profiles_fphot.ini' # the fiber photometry computer downstairs in the viv
    # profiles_fpath = 'profiles_ccu.ini' # my ccu desktop in the open lab
    profiles_fpath = 'profiles_laptop.ini'

    # argparsing
    parser = argparse.ArgumentParser(description=' xXx Unified TaskControl xXx ')
    parser.add_argument("-p", default=profiles_fpath, action='store', dest="profiles_fpath", help='set the path to the profiles.ini file')
    args = parser.parse_args()

    # run the application
    TaskControl = TaskControlApp([], profiles_fpath=args.profiles_fpath)