import os
from pathlib import Path
from configparser import ConfigParser
from collections import UserDict

import numpy as np
import pandas as pd

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
        self.folder = Path(folder)  # just in case
        for suffix in [".csv", ".ini"]:  # downward compatible
            meta_path = (self.folder / "animal_meta").with_suffix(suffix)
            if meta_path.exists() and suffix == ".csv":
                self.meta = pd.read_csv(meta_path)
                self.update(dict(zip(self.meta.name, self.meta.value)))

            # TODO check and FIXME
            if meta_path.exists() and suffix == ".ini":
                self.meta = ConfigParser()
                self.meta.read(meta_path)
                # self.meta = dict(self.meta) # possible?

    def update(self, Dict):
        """dataclass like field / member access"""
        for k, v in Dict.items():
            self.__dict__[k] = v

    def display(self):
        """this is not __repr__ because it is called explicitly"""
        if "Nickname" in self.__dict__.keys():
            return "%s - %s" % (self.ID, self.Nickname)
        else:
            return self.ID

    def weight_ratio(self):
        # FIXME this doesn't work because of str
        try:
            return self.current_weight / self.weight
        except:
            return ""

    def __repr__(self):
        return self.display()


class Session(object):
    def __init__(self, folder):
        self.Animal = Animal(folder.parent)
        self.folder = Path(folder)
        self.task, self.date, self.time = parse_session_folder(self.folder)

        session_folders = get_session_folders(self.folder.parent)
        self.total_days = len(session_folders)

        self.task_days = np.sum(
            [parse_session_folder(folder)[0] == self.task for folder in session_folders]
        )

        dates = np.sort([parse_session_folder(folder)[1] for folder in session_folders])
        self.day = (
            list(np.unique(dates)).index(self.date) + 1
        )  # note - np.unique makes sure that days are not equal to number of sessions

    def __repr__(self):
        return " - ".join(
            [
                self.Animal.ID,
                self.Animal.Nickname,
                self.date,
                self.task,
                "day: %s" % self.day,
            ]
        )


# class Sessions():
#     def __init__(self, Sessions: list[Session]):
#         self.Sessions = Sessions
#         # generating Sessions.Df
#         Dfs = []
#         for Session in self.Sessions:
#             # path = str(session)
#             # folder_name = os.path.basename(path)
#             # if folder_name == 'plots':
#             #     continue
#             # date = folder_name.split('_')[0]
#             # time = folder_name.split('_')[1]
#             # task = '_'.join(folder_name.split('_')[2:])
#             Df= pd.DataFrame(dict(path=Session.folder,
#                                   date=Session.date,
#                                   time=Session.time,
#                                   task=Session.task),
#                                   index=[0])
#             Dfs.append(Df)

#         self.Df = pd.concat(Dfs)
#         self.Df = Df.sort_values(['date','time'])
#         self.Df = Df.reset_index()


class Config(ConfigParser):
    def __init__(self, ini_path: str):
        super(Config, self).__init__()
        self.ini_path = Path(ini_path)
        self.read(ini_path)

    def save(self):
        with open(self.ini_path, "w") as fH:
            self.write(fH)


class Box(Config):
    def __init__(self, ini_path):
        super(Box, self).__init__(ini_path)
        self.name = ini_path.stem
        # self.config = # read from the .ini
        ...

    def get_Animals(self):
        """returns all Animals that are in this box"""
        ...


class Task(Config):
    def __init__(self, ini_path):
        super(Task, self).__init__(ini_path)
        self.name = ini_path.parts[-2]
        self.folder = ini_path.parent

    def get_description(self): ...

    def get_version(self): ...

    def get_Animals(self):
        """returns all Animals that have been run on this task"""
        ...


"""
 
 ##     ## ######## ##       ########  ######## ########   ######  
 ##     ## ##       ##       ##     ## ##       ##     ## ##    ## 
 ##     ## ##       ##       ##     ## ##       ##     ## ##       
 ######### ######   ##       ########  ######   ########   ######  
 ##     ## ##       ##       ##        ##       ##   ##         ## 
 ##     ## ##       ##       ##        ##       ##    ##  ##    ## 
 ##     ## ######## ######## ##        ######## ##     ##  ######  
 
"""


# Animal
def get_Animal_folders(folder: str) -> list:
    """iterates over dirs in folder and returns those
    that contain an animal_meta.csv"""
    animal_folders = []
    for path in Path(folder).iterdir():
        if path.is_dir() and (path / "animal_meta.csv").exists():
            animal_folders.append(path)
    return animal_folders


def get_Animals(folder: str) -> list[Animal]:
    """returns a list of Animals (object)"""
    animal_folders = get_Animal_folders(folder)
    return [Animal(animal_folder) for animal_folder in animal_folders]


# Box
def get_boxes_ini_paths(folder: str) -> list:
    """gets all the paths to all boxes.ini from the folder"""
    boxes_ini_paths = []
    for file in Path(folder).iterdir():
        if not file.is_dir() and file.suffix == ".ini":
            boxes_ini_paths.append(file)
    return boxes_ini_paths


def get_Boxes(folder: str) -> list[Box]:
    ini_paths = get_boxes_ini_paths(folder)
    return [Box(ini_path) for ini_path in ini_paths]


# Task
def get_tasks_ini_paths(folder: str) -> list:
    """ """
    tasks_ini_paths = []
    for subfolder in Path(folder).iterdir():
        if subfolder.is_dir() and (subfolder / "task_config.ini").exists():
            tasks_ini_paths.append(subfolder / "task_config.ini")
    return tasks_ini_paths


def get_Tasks(folder: str) -> list[Task]:
    tasks_ini_paths = get_tasks_ini_paths(folder)
    return [Task(ini_path) for ini_path in tasks_ini_paths]


# Sessions
def get_session_folders(animal_folder: str) -> list:
    """ """
    session_folders = []
    for subfolder in animal_folder.iterdir():
        if subfolder.is_dir() and (subfolder / "platformio_build_log.txt").exists():
            session_folders.append(subfolder)
    return session_folders


def get_Sessions(animal_folder: str) -> list[Session]:
    """returns a list of Session objects, chronologically sorted"""
    session_folders = get_session_folders(animal_folder)
    Sessions = [Session(session_folder) for session_folder in session_folders]

    # sort into chronological order
    order = np.argsort([S.date for S in Sessions])
    Sessions = [Sessions[i] for i in order]

    return Sessions


def parse_session_folder(folder: str):
    folder = Path(folder)
    task = "_".join(folder.stem.split("_")[2:])
    date = folder.stem.split("_")[0]
    time = folder.stem.split("_")[1]
    return task, date, time


# FIXME this needs proper fixing, and this function is actually called
def get_sessions(folder):
    """gets all sessions' logs, sorted by datetime in a Df"""
    """ this should have more parsing ... """
    sessions = []
    animal_folder = Path(folder)
    for subfolder in animal_folder.iterdir():
        if subfolder.is_dir():
            sessions.append(subfolder)

    # Df = pd.DataFrame(columns=['path','date','time','task'])

    Dfs = []
    for session in sessions:
        path = str(session)
        folder_name = os.path.basename(path)
        if folder_name == "plots":
            continue
        date = folder_name.split("_")[0]
        time = folder_name.split("_")[1]
        task = "_".join(folder_name.split("_")[2:])
        Df = pd.DataFrame(dict(path=path, date=date, time=time, task=task), index=[0])
        Dfs.append(Df)

    Df = pd.concat(Dfs)
    Df = Df.sort_values(["date", "time"])
    Df = Df.reset_index()

    return Df


def select(objs: list[object], **kwargs) -> list[object]:
    """filters list of object for key=value pairs
    if multiple pairs are present, perform intersection"""
    objs_sel = objs
    for key, value in kwargs.items():
        objs_sel = [obj for obj in objs_sel if obj.__dict__[key] == value]
    return objs_sel


# %%
def groupby_dict(Df, Dict):
    # groupby using a dict
    # strange that this isn't part of pandas
    # does not work at all atm
    return Df.groupby(list(Dict.keys())).get_group(tuple(Dict.values()))


# %%


def printer(s, mode="msg", obj=None):
    # TODO replace / enhance this entire functionality
    # by using the logging module
    # https://stackoverflow.com/a/13733863

    if mode == "msg":
        string = Fore.GREEN + s
    if mode == "task":
        string = Fore.CYAN + "\n--- %s ---" % s
    if mode == "error":
        string = Fore.RED + "ERROR: %s" % s
    if mode == "warning":
        string = Fore.YELLOW + "WARNING: %s" % s
    if mode == "debug":
        string = Fore.MAGENTA + "DEBUG: %s" % s

    if obj is not None:
        string = ": ".join([obj.name, string])

    print(string)


def debug_trace():
    """Set a tracepoint in the Python debugger that works with Qt
    https://stackoverflow.com/a/1745965/4749250"""
    from PyQt5 import QtCore
    from pdb import set_trace

    QtCore.pyqtRemoveInputHook()
    set_trace()


# TODO never used!?
def get_file_dialog(initial_dir="D:/TaskControl/Animals"):
    from tkinter import Tk
    from tkinter import filedialog

    root = Tk()  # create the Tkinter widget
    root.withdraw()  # hide the Tkinter root window

    # Windows specific; forces the window to appear in front
    root.attributes("-topmost", True)

    path = Path(filedialog.askopenfilename(initialdir=initial_dir, title="Select file"))

    root.destroy()

    return path


# TODO never used!?
# also - use qt ...
def get_folder_dialog(initial_dir="D:/TaskControl/Animals"):
    from tkinter import Tk
    from tkinter import filedialog

    root = Tk()  # create the Tkinter widget
    root.withdraw()  # hide the Tkinter root window

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


class NotInvertibleException(Exception): ...


# implement checking
class InvertibleMap(UserDict):
    def __init__(self, Dict):
        super(InvertibleMap, self).__init__(Dict)

        if self.has_duplicates(list(self.keys())) or self.has_duplicates(
            list(self.values())
        ):
            raise NotInvertibleException
        else:
            self.inv = dict(zip(self.values(), self.keys()))

    def has_duplicates(self, elements: list) -> bool:
        return any([elements.count(el) > 1 for el in elements])


# this is the mapping from C style dtype "words" to np letter abbreviations
dtype_map = InvertibleMap(
    {
        "int": "i4",
        "unsigned int": "u4",
        "long": "i8",
        "unsigned long": "u8",
        "bool": "?",
        "float": "f4",
        "double": "f8",
    }
)


def parse_code_map(path):
    """a hacky parser"""
    # 2do: return an InvertibleMap
    with open(path, "r") as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    dfs = []
    for line in lines:
        if not line.startswith("//"):
            try:
                (
                    a,
                    b,
                ) = line.split(" int ")
                state, code = b.split(" = ")

                dfs.append(pd.DataFrame([[code[:-1], state]], columns=["code", "name"]))
            except:
                pass
    code_map = pd.concat(dfs, axis=0)
    code_map = code_map.reset_index(drop=True)

    return code_map


def parse_arduino_vars(path):
    """parses an interface_variables.h into a pd.DataFrame"""

    with open(path, "r") as fH:
        lines = fH.readlines()
        lines = [line.strip() for line in lines]

    # hacky parser:
    parsed_vars = []
    for line in lines:
        # to skip
        if line == "":
            continue
        if "*" in line:  # in block comment
            continue
        if line[:2] == "//":  # full line comment
            continue
        if "//" in line:  # remove everything after comment
            line = line.split("//")[0]

        try:
            elements, value = line.split("=")
            elements = elements.strip()
            value = value.strip()
            value = value[:-1]  # removes last ';'
            elements = elements.split(" ")
            # elements = [elem.strip() for elem in elements] # whitespace removal
            name = elements[-1]
            dtype = " ".join(elements[:-1])
            value = np.array(value, dtype=dtype_map[dtype])
            parsed_vars.append(dict(name=name, value=value, dtype=dtype_map[dtype]))
        except:
            print("unreadable line: ", line)
            pass

    Df = pd.DataFrame(parsed_vars)
    return Df.reset_index(drop=True)


def Df2arduino_vars(Df):
    """converts a pd.DataFrame into a list of str for C/arduino"""

    lines = []
    for i, row in Df.iterrows():
        line = []
        line.append(dtype_map.inv[row["dtype"]])
        line.append(row["name"])
        line.append("=")
        if row["dtype"] == "?":
            if row["value"] == True:
                value = "true"
            if row["value"] == False:
                value = "false"
        else:
            value = str(row["value"])

        line.append(value)
        line = " ".join(line) + ";\n"
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
    """how can be horizontally or vertically, reference is the
    first widget in the list"""

    if how == "horizontally":
        for i in range(1, len(Widgets)):
            x = Widgets[i - 1].pos().x() + Widgets[i - 1].size().width() + gap
            y = Widgets[i - 1].pos().y()
            Widgets[i].move(x, y)

    if how == "vertically":
        for i in range(1, len(Widgets)):
            x = Widgets[i - 1].pos().x()
            y = Widgets[i - 1].pos().y() + Widgets[i - 1].size().height() + gap
            Widgets[i].move(x, y)


def scale_Widgets(Widgets, how="vertical", mode="max"):
    # TODO document me!

    if how == "vertical":
        widths = [widget.size().width() for widget in Widgets]

        if mode == "max":
            max_width = max(widths)
            [widget.resize(max_width, widget.height()) for widget in Widgets]

        if mode == "min":
            min_width = min(widths)
            [widget.resize(min_width, widget.sizeHint().height()) for widget in Widgets]
