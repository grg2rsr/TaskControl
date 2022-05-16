import sys, os 
import pandas as pd
import scipy as sp 
import pathlib
from pathlib import Path
from colorama import init, Fore
init(autoreset=True)

"""
 
  #######  ########        ## ########  ######  ########  ######  
 ##     ## ##     ##       ## ##       ##    ##    ##    ##    ## 
 ##     ## ##     ##       ## ##       ##          ##    ##       
 ##     ## ########        ## ######   ##          ##     ######  
 ##     ## ##     ## ##    ## ##       ##          ##          ## 
 ##     ## ##     ## ##    ## ##       ##    ##    ##    ##    ## 
  #######  ########   ######  ########  ######     ##     ######  
 
"""

class Animal(object):
    def __init__(self, folder):
        self.folder = Path(folder) # just in case
        self.meta = pd.read_csv(self.folder / 'animal_meta.csv')
        self.update(dict(zip(self.meta.name, self.meta.value)))

    def update(self, Dict):
        for k,v in Dict.items():
            self.__dict__[k] = v

    def display(self):
        if 'Nickname' in self.__dict__.keys():
            return "%s - %s" % (self.ID, self.Nickname)
        else:
            return self.ID

    def weight_ratio(self):
        try:
            return self.current_weight / self.weight
        except:
            return ''

    def __repr__(self):
        return self.display()

class Session(object):
    def __init__(self, folder):
        self.Animal = Animal(folder.parent)
        self.folder = Path(folder)
        self.task = '_'.join(folder.stem.split('_')[2:])
        self.date = folder.stem.split('_')[0]
        self.time = folder.stem.split('_')[1]
        self.SessionsDf = get_sessions(folder.parent)
        self.total_days = self.SessionsDf.shape[0]
        self.task_days = self.SessionsDf.groupby('task').get_group(self.task).shape[0]
        self.day = list(self.SessionsDf['date'].values).index(self.date) + 1

    def __repr__(self):
        return ' - '.join([self.Animal.ID, self.Animal.Nickname, self.date, self.task, 'day: %s' % self.day])


"""
 
 ##     ## ######## ##       ########  ######## ########   ######  
 ##     ## ##       ##       ##     ## ##       ##     ## ##    ## 
 ##     ## ##       ##       ##     ## ##       ##     ## ##       
 ######### ######   ##       ########  ######   ########   ######  
 ##     ## ##       ##       ##        ##       ##   ##         ## 
 ##     ## ##       ##       ##        ##       ##    ##  ##    ## 
 ##     ## ######## ######## ##        ######## ##     ##  ######  
 
"""

def get_Animals(folder):
    """ checks each folder in folder """
    Animals = []
    animals_folder = pathlib.Path(folder)
    for path in animals_folder.iterdir():
        if path.is_dir():
            # is an animal folder?
            if (path / 'animal_meta.csv').exists():
                Animals.append(Animal(path))
    return Animals

def select(objs, key, value):
    return [obj for obj in objs if obj.__dict__[key] == value]

def groupby_dict(Df, Dict):
    return Df.groupby(list(Dict.keys())).get_group(tuple(Dict.values()))

def printer(s, mode='msg'):
    if mode == 'msg':
        print(Fore.GREEN + s)
    if mode == 'task':
        print(Fore.CYAN + "\n--- %s ---" % s)
    if mode == 'error':
        print(Fore.RED + "ERROR: %s" % s)
    if mode == 'warning':
        print(Fore.YELLOW + "WARNING: %s" % s)
    if mode == 'debug':
        print(Fore.MAGENTA + "DEBUG: %s" % s)
        
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

    # Df = pd.DataFrame(columns=['path','date','time','task'])

    Dfs = []
    for session in sessions:
        path = str(session)
        folder_name = os.path.basename(path)
        if folder_name == 'plots':
            continue
        date = folder_name.split('_')[0]
        time = folder_name.split('_')[1]
        task = '_'.join(folder_name.split('_')[2:])
        Df= pd.DataFrame(dict(path=path,date=date,time=time,task=task),index=[0])
        Dfs.append(Df)

    Df = pd.concat(Dfs)
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

def get_folder_dialog(initial_dir="D:/TaskControl/Animals"):
    from tkinter import Tk
    from tkinter import filedialog
    root = Tk()         # create the Tkinter widget
    root.withdraw()     # hide the Tkinter root window

    # Windows specific; forces the window to appear in front
    root.attributes("-topmost", True)

    path = Path(filedialog.askdirectory(initialdir=initial_dir, title="Select folder"))

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
        if not line.startswith('//'):
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
        line = ' '.join(line) + ';\n'
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
