import scipy as sp
import pandas as pd
from pathlib import Path
from functions import parse_code_map
import utils

def parse_arduino_log(log_path, code_map=None):
    """ create a DataFrame representation of an arduino log. If a code map is passed 
    a corresponding decoded column will be created

    for offline use
    """

    with open(log_path,'r') as fH:
        lines = fH.readlines()

    return parse_lines(lines,code_map=code_map)


def parse_line(line, code_map=None):
    """ never used? - also questionable in speed """
    if not line.startswith("<") and '\t' in line:
        data = pd.Series(line.strip().split('\t'),index=['code','t'])
        data.loc['t'] = float(data.loc['t'])

        if code_map is not None:
            data.loc['name'] = code_map[data.loc["code"]]

        return data

def parse_lines(lines,code_map=None):
    """ _much_ faster parser"""
    valid_lines = [line.strip() for line in lines if '\t' in line]
    Data = pd.DataFrame([line.split('\t') for line in valid_lines],columns=['code','t'])
    Data['t'] = Data['t'].astype('float')
    Data.reset_index(drop=True)

    # decode
    if code_map is not None:
        Data['name'] = [code_map[code] for code in Data['code']]

    # test for time wraparound
    if sp.any(sp.diff(Data['t']) < 0):
        reversal_ind = sp.where(sp.diff(Data['t']) < 0)[0][0]
        Data['t'].iloc[reversal_ind+1:] += Data['t'].iloc[reversal_ind]
    return Data

def slice_into_trials(Data):
    """ returns a list of DataFrames """    
    start_inds = Data.groupby('name').get_group("TRIAL_ENTRY_EVENT").index
    completed_inds = Data.groupby('name').get_group("TRIAL_COMPLETED_EVENT").index
    aborted_inds = Data.groupby('name').get_group("TRIAL_ABORTED_EVENT").index
    stop_inds = completed_inds.append(aborted_inds)
    stop_inds = stop_inds.sort_values()

    if len(start_inds) != len(stop_inds):
        print("unequal number of trial entries and exits!")
        return None

    Dfs = []
    for i in range(len(start_inds)):
        Dfs.append(Data.loc[start_inds[i]:stop_inds[i]])

    return Dfs

def parse_trial(Df):
    # update SessionDf
    """
    first event should be trial available
    this should return a series
    can not know about trial number ? """
    try:
        t = Df.groupby('name').get_group('TRIAL_AVAILABLE_STATE').iloc[0]['t']
    except KeyError:
        # this happens before first trial
        return None

    if "TRIAL_COMPLETED_EVENT" in Df['name'].values:
        succ = True
        if "REWARD_COLLECTED_EVENT" in Df['name'].values:
            reward_collected = True
            t_rew_col = Df.groupby('name').get_group("REWARD_COLLECTED_EVENT").iloc[-1]['t']
            t_rew_avail = Df.groupby('name').get_group("REWARD_AVAILABLE_EVENT").iloc[-1]['t']
            rew_col_rt = t_rew_col - t_rew_avail
        else:
            reward_collected = False
            rew_col_rt = sp.NaN

    if "TRIAL_ABORTED_EVENT" in Df['name'].values:
        succ = False
        reward_collected = sp.NaN
        rew_col_rt = sp.NaN
    index = ['t','successful','reward_collected','rew_col_rt']

    # TODO HARDCODES EVERYWHERE AAA
    return pd.Series([t,succ,reward_collected,rew_col_rt], index=index)
    
def parse_trials(Dfs):
    """ bc parse_trial is used also by online plotting 
    this one however is only needed offline """
    SessionDf = [parse_trial(Df) for Df in Dfs]
    return pd.concat(SessionDf,axis=1).T

def log2Span(Data,span_name):
    try:
        on_times = Data.groupby('name').get_group(span_name+'_ON')['t'].values.astype('float')
        off_times = Data.groupby('name').get_group(span_name+'_OFF')['t'].values.astype('float')
    except KeyError:
        return pd.DataFrame(columns=['t_on','t_off','dt'])

    try:
        # if recordings didnt record last OFF
        if on_times.shape[0] == off_times.shape[0] + 1 and on_times[0] < off_times[0]:
            on_times = on_times[:-1] # remove last ON

        # if recordings didnt record first ON
        if off_times.shape[0] == on_times.shape[0] + 1 and off_times[0] < on_times[0]: 
            off_times = off_times[1:] # remove first OFF

        # if recordings didnt record first ON AND last OFF -> total matrix size would still be equal
        if off_times[0] < on_times[0] and off_times[-1] < on_times[-1]
            off_times = off_times[1:]
            on_times = on_times[:-1]

        # Perfect scenario: start with ON, end with OFF
        if on_times.shape[0] == off_times.shape[0]:
            dt = off_times - on_times
            Df = pd.DataFrame(sp.stack([on_times,off_times,dt],axis=1),columns=['t_on','t_off','dt'])
            return Df
    except IndexError:
        return pd.DataFrame(columns=['t_on','t_off','dt'])
    else:
        print("unequal number of ON and OFF events for: ", span_name)
        return pd.DataFrame(columns=['t_on','t_off','dt'])

def log2Spans(Data,span_names):
    Spans = {}
    for span_name in span_names:
        Spans[span_name] = log2Span(Data,span_name)
    return Spans

def log2Event(Data,event_name):
    try:
        # times = Data.groupby('name').get_group(event_name+'_EVENT')['t'].values.astype('float')
        # Df = pd.DataFrame(times,columns=['t'])
        Df = Data.groupby('name').get_group(event_name+'_EVENT')[['t']]
    except KeyError:
        # this gets thrown when the event is not in the log
        return pd.DataFrame(columns=['t'])
    return Df

def log2Events(Data,event_names):
    Events = {}
    for event_name in event_names:
        Events[event_name] = log2Event(Data,event_name)
    return Events

# def time_slice(Df, t_min, t_max, col='t_on'):
#     """ slices the DataFrame on the column """
#     return Df.loc[sp.logical_and(Df[col] > t_min, Df[col] < t_max)]

def time_slice(Df, t_min, t_max, col='t'): # change default to 't'
    vals = Df[col].values
    binds = sp.logical_and(vals > t_min, vals < t_max)
    return Df.loc[binds]

# PATH
# upstairs
# log_path = Path("/home/georg/git_tmp/TaskControl/Animals/123/2020-01-22_11-53-34_lick_for_reward_w_surpression/arduino_log.txt")
# code_map_path = Path("/home/georg/git_tmp/TaskControl/Animals/123/2020-01-22_11-53-34_lick_for_reward_w_surpression/lick_for_reward_w_surpression/Arduino/src/event_codes.h")
log_path = Path("/media/georg/htcondor/shared-paton/georg/arduino_log.txt")
# code_
# 


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