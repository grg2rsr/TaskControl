import matplotlib.pyplot as plt
import scipy as sp
import seaborn as sns
import pandas as pd
from pathlib import Path
import sys
from functions import parse_code_map
import utils

def parse_arduino_log(log_path, code_map=None):
    """ create a DataFrame representation of an arduino log. If a code map is passed 
    a corresponding decoded column will be created """

    with open(log_path,'r') as fH:
        lines = fH.readlines()

    valid_lines = [line.strip().split('\t') for line in lines if '\t' in line]
    Data = pd.DataFrame(valid_lines,columns=['code','t'])
    Data['t'] = Data['t'].astype('float')

    if code_map is not None:
        cm = dict(zip(code_map['code'], code_map['name']))
        Data['name'] = [cm[code] for code in Data["code"]]

    return Data

# def parse_lines2(lines, code_map=None):
#     """ analogous to parse_arduino_log, but operates on a list of lines """

#     Data = pd.DataFrame(columns=['code','t'])

#     for line in lines:
#         if not line.startswith('<'):
#             code, t = line.strip().split('\t')
#             data = pd.DataFrame([[code,t]],columns=['code','t'])
#             Data = Data.append(data)

#     Data['t'] = Data['t'].astype('float')

#     if code_map is not None:
#         cm = dict(zip(code_map['code'], code_map['name']))
#         Data['name'] = [cm[code] for code in Data["code"]]

#     return Data

def  parse_line(line, code_dict=None):
    if not line.startswith('<'):
        code, t = line.strip().split('\t')
        data = pd.DataFrame([[code,t]],columns=['code','t'])
        data['t'] = data['t'].astype('float')

        if code_dict is not None:
            data['name'] = code_dict[data.loc[0,"code"]]

        return data
    else:
        pass

def parse_lines(lines, code_map=None):
    Dfs = []
    if code_map is not None:
        code_dict = dict(zip(code_map['code'], code_map['name']))
    lines = [Dfs.append(parse_line(line, code_dict=code_dict)) for line in lines]
    Data = pd.concat(Dfs)
    Data.reset_index(drop=True)
    return Data

    

def log2Span(Data,span_name):
    try:
        on_times = Data.groupby('name').get_group(span_name+'_ON')['t'].values.astype('float')
        off_times = Data.groupby('name').get_group(span_name+'_OFF')['t'].values.astype('float')
    except KeyError:
        return pd.DataFrame(columns=['t_on','t_off','dt'])

    if on_times.shape != off_times.shape:
        print("unequal number of ON and OFF events for: ", span_name)
        return pd.DataFrame(columns=['t_on','t_off','dt'])
    else:
        dt = off_times - on_times
        Df = pd.DataFrame(sp.stack([on_times,off_times,dt],axis=1),columns=['t_on','t_off','dt'])
        return Df

def log2Spans(Data,span_names):
    Spans = {}
    for span_name in span_names:
        Spans[span_name] = log2Span(Data,span_name)
    return Spans

def log2Event(Data,event_name):
    try:
        times = Data.groupby('name').get_group(event_name+'_EVENT')['t'].values.astype('float')
        Df = pd.DataFrame(times,columns=['t'])
    except KeyError:
        # this gets thrown when the event is not in the log
        return pd.DataFrame(columns=['t'])
    return Df

def log2Events(Data,event_names):
    Events = {}
    for event_name in event_names:
        Events[event_name] = log2Event(Data,event_name)
    return Events

def make_TrialsDf(Data,trial_entry=None,trial_exit_succ=None,trial_exit_unsucc=None):
    try:
        TrialsDf = pd.DataFrame(Data.groupby('name').get_group(trial_entry)['t'])
        TrialsDf.columns = ['t_on']
    except KeyError:
        TrialsDf = pd.DataFrame(columns=['t_on'])
        return TrialsDf

    try:
        Hit = pd.DataFrame(Data.groupby('name').get_group(trial_exit_succ)['t'])
        Hit['outcome'] = 'succ'
    except KeyError:
        Hit = pd.DataFrame(columns=['t','outcome'])

    try:
        Miss = pd.DataFrame(Data.groupby('name').get_group(trial_exit_unsucc)['t'])
        Miss['outcome'] = 'unsucc'
    except KeyError:
        Miss = pd.DataFrame(columns=['t','outcome'])

    AllEndings = pd.concat([Hit,Miss],axis=0)
    AllEndings = AllEndings.sort_values('t')
    AllEndings.columns = ['t_off','outcome']

    # removing last incompleted
    if TrialsDf.shape[0] > AllEndings.shape[0]:
        TrialsDf = TrialsDf[:-1]

    TrialsDf = pd.concat([TrialsDf.reset_index(drop=True),AllEndings.reset_index(drop=True)],axis=1)
    TrialsDf['dt'] = TrialsDf['t_off'] - TrialsDf['t_on']
    
    return TrialsDf

def time_slice(Df, t_min, t_max, col='t_on'):
    """ slices the DataFrame on the column """
    return Df.loc[sp.logical_and(Df[col] > t_min, Df[col] < t_max)]


# PATH
# upstairs
# log_path = Path("/home/georg/git_tmp/TaskControl/Animals/123/2020-01-22_11-53-34_lick_for_reward_w_surpression/arduino_log.txt")
# code_map_path = Path("/home/georg/git_tmp/TaskControl/Animals/123/2020-01-22_11-53-34_lick_for_reward_w_surpression/lick_for_reward_w_surpression/Arduino/src/event_codes.h")

# # downstairs
# # log_path = Path(r'D:\TaskControl\Animals\123\2020-01-22_11-53-34_lick_for_reward_w_surpression\arduino_log.txt')
# # code_map_path = Path(r'D:\TaskControl\Animals\123\2020-01-22_11-53-34_lick_for_reward_w_surpression\lick_for_reward_w_surpression\Arduino\src\event_codes.h')

# Code_Map = parse_code_map(code_map_path)
# Data = parse_arduino_log(log_path, Code_Map)

# # the names of the things present in the log
# span_names = [name.split('_ON')[0] for name in Code_Map['name'] if name.endswith('_ON')]
# event_names = [name.split('_EVENT')[0] for name in Code_Map['name'] if name.endswith('_EVENT')]

# Spans = log2Spans(Data, span_names)
# Events = log2Events(Data, event_names)

# # definition of the bounding events
# trial_entry = "FIXATE_STATE"
# trial_exit_succ = "SUCCESSFUL_FIXATION_EVENT"
# trial_exit_unsucc = "BROKEN_FIXATION_EVENT"

# TrialsDf = make_TrialsDf(Data,trial_entry=trial_entry,
#                               trial_exit_succ=trial_exit_succ,
#                               trial_exit_unsucc=trial_exit_unsucc)

# log2Event(Data[:2], "REWARD_COLLECTED")