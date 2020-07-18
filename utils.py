import sys, os 
import pandas as pd
import scipy as sp 
import pathlib
from pathlib import Path

def get_animals(folder):
    """ checks each folder in folder """
    animals = []
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
    """ gets all sessions' logs, sorted by datetime in a Df """
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

"""
 
 ##     ## ######## #### ##       #### ######## ##    ## 
 ##     ##    ##     ##  ##        ##     ##     ##  ##  
 ##     ##    ##     ##  ##        ##     ##      ####   
 ##     ##    ##     ##  ##        ##     ##       ##    
 ##     ##    ##     ##  ##        ##     ##       ##    
 ##     ##    ##     ##  ##        ##     ##       ##    
  #######     ##    #### ######## ####    ##       ##    
 
"""

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

"""
 
 ########     ###    ########   ######  ######## ########  
 ##     ##   ## ##   ##     ## ##    ## ##       ##     ## 
 ##     ##  ##   ##  ##     ## ##       ##       ##     ## 
 ########  ##     ## ########   ######  ######   ########  
 ##        ######### ##   ##         ## ##       ##   ##   
 ##        ##     ## ##    ##  ##    ## ##       ##    ##  
 ##        ##     ## ##     ##  ######  ######## ##     ## 
 
"""
# this is the mapping from numpy letter codes to C style arduino compatible
dtype_map = {
            'int':'i4',
            'unsigned int':'u4',
            'long':'i8',
            'unsigned long':'u8',
            'bool':'?',
            'float':'f4',
            'double':'f8',
            }

def parse_code_map(path):
    # FIXME this needs a new name as well - and right now is unused!
    """ a hacky parser """  
    with open(path, 'r') as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    dfs = []
    for line in lines:
        try:
            a, b, = line.split(' int ')
            state, code = b.split(' = ')

            dfs.append(pd.DataFrame([[code[:-1], state]], columns=['code', 'name']))
        except:
            pass
    code_map = pd.concat(dfs, axis=0)
    code_map = code_map.reset_index(drop=True)

    return code_map

def parse_arduino_vars(path):
    """ parses an interface_variables.h into a pd.DataFrame """
    
    with open(path, 'r') as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    parsed_vars = []
    for line in lines:
        
        # to skip
        if line == '':
            continue
        if '*' in line:  # in block comment
            continue
        if line[:2] == '//': # full line comment
            continue
        if '//' in line: # remove everything after comment
            line = line.split('//')[0]
        
        try:
            elements, value = line.split('=')
            elements = elements.strip()
            value = value.strip()
            value = value[:-1] # removes last ';'
            elements = elements.split(' ')
            # elements = [elem.strip() for elem in elements] # whitespace removal
            name = elements[-1]
            dtype = ' '.join(elements[:-1])
            value = sp.array(value, dtype=dtype_map[dtype])
            parsed_vars.append(dict(name=name, value=value, dtype=dtype_map[dtype]))
        except:
            print('unreadable line: ',line)
            pass

    Df = pd.DataFrame(parsed_vars)
    return Df.reset_index(drop=True)

def Df2arduino_vars(Df):
    # convert them into something that arduino lang understands
    dtype_map_inv = dict(zip(dtype_map.values(),dtype_map.keys()))

    lines = []
    for i, row in Df.iterrows():
        line = []
        line.append(dtype_map_inv[row['dtype']]) 
        line.append(row['name'])
        line.append('=')
        if row['dtype'] == '?':
            if row['value'] == True:
                value = "true"
            if row['value'] == False:
                value = "false"
        else:
            value = str(row['value'])

        line.append(value)
        line = ' '.join(line) + ';' + os.linesep 
        lines.append(line)
    return lines

"""
 
 ##     ## #### 
 ##     ##  ##  
 ##     ##  ##  
 ##     ##  ##  
 ##     ##  ##  
 ##     ##  ##  
  #######  #### 
 
"""

def tile_Widgets(Widgets, how="horizontally", gap=50):
    """ how can be horizontally or vertically, reference is the 
    first widget in the list """

    if how == "horizontally":
        for i in range(1,len(Widgets)):
            x = Widgets[i-1].pos().x() + Widgets[i-1].size().width() + gap
            y = Widgets[i-1].pos().y()
            Widgets[i].move(x,y)

    if how == "vertically":
        for i in range(1,len(Widgets)):
            x = Widgets[i-1].pos().x()
            y = Widgets[i-1].pos().y() + Widgets[i-1].size().height() + gap
            Widgets[i].move(x,y)

def scale_Widgets(Widgets, how="vertical", mode="max"):
    # TODO document me!

    if how == "vertical":
        widths = [widget.size().width() for widget in Widgets]

        if mode == "max":
            max_width = max(widths)
            [widget.resize(max_width,widget.height()) for widget in Widgets]

        if mode == "min":
            min_width = min(widths)
            [widget.resize(min_width,widget.sizeHint().height()) for widget in Widgets]
