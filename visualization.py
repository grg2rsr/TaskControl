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
        Data['name'] = [code_map[code_map['code'] == v]['name'].values[0] for v in Data['code'].values]

    return Data

def log2Span(Data,span_name):
    on_times = Data.groupby('name').get_group(span_name+'_ON')['t'].values.astype('float')
    off_times = Data.groupby('name').get_group(span_name+'_OFF')['t'].values.astype('float')
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
        try:
            Spans[span_name] = log2Span(Data,span_name)
        except KeyError:
            print("span not present in log but in code map: ",span_name)
    return Spans

def log2Event(Data,event_name):
    times = Data.groupby('name').get_group(event_name+'_EVENT')['t'].values.astype('float')
    Df = pd.DataFrame(times,columns=['t'])
    return Df

def log2Events(Data,event_names):
    Events = {}
    for event_name in event_names:
        try:
            Events[event_name] = log2Event(Data,event_name)
        except KeyError:
            print("event not present in log but in code map: ", event_name)
            # utils.debug_trace()
    return Events

def make_TrialsDf(Data,trial_entry=None,trial_exit_succ=None,trial_exit_unsucc=None):
    # TODO make this work gracefully in terms of passing an empty dataframe
    # TODO read a complete log and then expand line by line to see when it breaks how
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


