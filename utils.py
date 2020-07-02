import sys, os 
import pandas as pd
import scipy as sp 
import pathlib
from pathlib import Path
# TODO each of these functions should return a dataframe, with a 'path' column and other interesting info ... 
# most of this is now performed by a function in the "first look" behavior stuff on the laptop
# get it!!!

def get_animals(folder):
    """ checks each folder in folder """
    animals= []
    animals_folder = pathlib.Path(folder)
    for subfolder in animals_folder.iterdir():
        if subfolder.is_dir():
            if os.path.exists(os.path.join(subfolder, 'animal_meta.csv')):
                animals.append(os.path.basename(subfolder))
    return animals

def get_tasks(folder):
    """ gets all valid tasks """
    tasks = []
    tasks_folder = pathlib.Path(folder)
    for subfolder in tasks_folder.iterdir():
        if subfolder.is_dir():
            if os.path.exists(os.path.join(subfolder,'task_config.ini')):
                tasks.append(os.path.basename(subfolder))
    return tasks
    
def get_sessions(folder):
    """ gets all sessions, sorted by datetime """
    """ this should have more parsing ... """
    sessions = []
    animal_folder = pathlib.Path(folder)
    for subfolder in animal_folder.iterdir():
        if subfolder.is_dir():
            sessions.append(subfolder)

    Df = []
    for session in sessions:
        path = str(session)
        folder_name = os.path.basename(path)
        date = folder_name.split('_')[0]
        time = folder_name.split('_')[1]
        task = '_'.join(folder_name.split('_')[2:])
        Df.append(pd.DataFrame([[path,date,time,task]],columns=['path','date','time','task']))

    Df = pd.concat(Df,axis=0)
    Df = Df.sort_values(['date','time'])
    Df = Df.reset_index()

    return Df

def debug_trace():
    """ Set a tracepoint in the Python debugger that works with Qt
    https://stackoverflow.com/a/1745965/4749250 """
    from PyQt5 import QtCore
    from pdb import set_trace
    QtCore.pyqtRemoveInputHook()
    set_trace()

def get_file_dialog(initial_dir="D:/TaskControl/Animals"):
    from tkinter import Tk
    from tkinter import filedialog
    root = Tk()         # create the Tkinter widget
    root.withdraw()     # hide the Tkinter root window

    # Windows specific; forces the window to appear in front
    root.attributes("-topmost", True)

    path = Path(filedialog.askopenfilename(initialdir=initial_dir, title="Select file"))

    root.destroy()

    return path

