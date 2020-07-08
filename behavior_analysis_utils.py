import scipy as sp
import pandas as pd
import numpy as np
import os 
from pathlib import Path
from functions import parse_code_map
import utils
import datetime
from tqdm import tqdm
import behavior_analysis_utils as bhv

"""
 
 ########     ###    ########   ######  ######## ########  
 ##     ##   ## ##   ##     ## ##    ## ##       ##     ## 
 ##     ##  ##   ##  ##     ## ##       ##       ##     ## 
 ########  ##     ## ########   ######  ######   ########  
 ##        ######### ##   ##         ## ##       ##   ##   
 ##        ##     ## ##    ##  ##    ## ##       ##    ##  
 ##        ##     ## ##     ##  ######  ######## ##     ## 
 
"""

def get_LogDf_from_path(log_path):
    """ helper to infer taks name and get code_map """
    # infer
    task_name = '_'.join(log_path.parent.name.split('_')[2:])
    code_map_path = log_path.parent / task_name / "Arduino" / "src" / "event_codes.h"

    # and read
    CodesDf = bhv.parse_code_map(code_map_path)
    code_map = dict(zip(CodesDf['code'],CodesDf['name']))
    LogDf = bhv.parse_arduino_log(log_path, code_map)

    return LogDf

def parse_arduino_log(log_path, code_map=None):
    """ create a DataFrame representation of an arduino log. If a code map is passed 
    a corresponding decoded column will be created

    for offline use
    """
    with open(log_path,'r') as fH:
        lines = fH.readlines()

    return parse_lines(lines, code_map=code_map)

# def parse_lines(lines, code_map=None):
#     """ parses a list of lines from arduino into a pd.DataFrame
#     the old (more performant) function
#     """
#     valid_lines = [line.strip() for line in lines if '\t' in line]
#     LogDf = pd.DataFrame([line.split('\t') for line in valid_lines],columns=['code','t'])
#     LogDf['t'] = LogDf['t'].astype('float')
#     LogDf.reset_index(drop=True)

#     # decode
#     if code_map is not None:
#         LogDf['name'] = [code_map[code] for code in LogDf['code']]

#     # test for time wraparound
#     if np.any(np.diff(LogDf['t']) < 0):
#         reversal_ind = np.where(np.diff(LogDf['t']) < 0)[0][0]
#         LogDf['t'].iloc[reversal_ind+1:] += LogDf['t'].iloc[reversal_ind]

#     return LogDf

def correct_wraparound(Df):
    """ tests and corrects for time wraparound on column t """
    if np.any(np.diff(Df['t']) < 0):
        reversal_ind = np.where(np.diff(Df['t']) < 0)[0][0]
        Df['t'].iloc[reversal_ind+1:] += Df['t'].iloc[reversal_ind]
    return Df

def parse_lines(lines, code_map=None, parse_var=True):
    """ parses a list of lines from arduino into a pd.DataFrame """
    LogDf = pd.DataFrame([line.split('\t') for line in lines if '\t' in line],columns=['code','t'])
    LogDf['t'] = LogDf['t'].astype('float')
    LogDf = correct_wraparound(LogDf)
    LogDf = LogDf.reset_index(drop=True)

    for col in ['name','var','value']:
        LogDf[col] = sp.NaN

    # decode
    if code_map is not None:
        LogDf['name'] = [code_map[code] for code in LogDf['code']]

    if parse_var:
        var_lines = [line.strip() for line in lines if line.startswith('<VAR')]
        VarDf = pd.DataFrame([line[1:-1].split(' ') for line in var_lines],columns=['_','var','value','t'])
        VarDf = VarDf.drop('_',axis=1)
        VarDf['t'] = VarDf['t'].astype('float')
        VarDf['value'] = VarDf['value'].astype('float')
        
        VarDf = correct_wraparound(VarDf)
        
        # join
        LogDf = LogDf.append(VarDf,ignore_index=True)
        LogDf = LogDf.sort_values('t')
        LogDf = LogDf.reset_index(drop=True)

    return LogDf


"""
 
 ######## ##     ## ######## ##    ## ########  ######  
 ##       ##     ## ##       ###   ##    ##    ##    ## 
 ##       ##     ## ##       ####  ##    ##    ##       
 ######   ##     ## ######   ## ## ##    ##     ######  
 ##        ##   ##  ##       ##  ####    ##          ## 
 ##         ## ##   ##       ##   ###    ##    ##    ## 
 ########    ###    ######## ##    ##    ##     ######  
 
"""

def get_events_from_name(LogDf, event_name):
    """ extracts event times from LogDf as a pd.DataFrame """
    try:
        EventsDf = LogDf.groupby('name').get_group(event_name)[['t']]
    except KeyError:
        # this gets thrown when the event is not in the log
        return pd.DataFrame(columns=['t'])
    return EventsDf

def get_events(LogDf, event_names):
    """ helper for multiple event_names """
    EventsDict = {}
    for event_name in event_names:
        EventsDict[event_name] = get_events_from_name(LogDf, event_name)
 
    return EventsDict

def filter_bad_licks(LogDf, min_time=50, max_time=200, remove=False):
    """ 
    Process recorded LICK_ON and LICK_OFF into realistic licks and add them as an event to the LogDf
    """
    LickSpan = get_spans_from_names(LogDf,'LICK_ON','LICK_OFF')

    bad_licks = np.logical_or(LickSpan['dt'] < min_time , LickSpan['dt'] > max_time)
    LickSpan = LickSpan.loc[~bad_licks]

    # Add lick_event to LogDf
    Lick_Event = pd.DataFrame(np.stack([['NA']*LickSpan.shape[0],LickSpan['t_on'].values,['LICK_EVENT']*LickSpan.shape[0]]).T,columns=['code','t','name'])
    Lick_Event['t'] = Lick_Event['t'].astype('float')
    LogDf = LogDf.append(Lick_Event)
    LogDf.sort_values('t')

    if remove is True:
        # TODO
        pass

    return LogDf


# def moving_median_removal(data, window_size):
#     " Running median (only works with numpy matrices and it is clunky) "
#      
#     aux = np.zeros(data.shape)
#     half_window = int(window_size/2)

#     for i in range(0,data.shape[1]):
#         # Beginning of data array
#         if i < (half_window):
#             aux[:,i] = data[:,i] - np.median(data[:, 0:(i+half_window)], 1)

#         # End of data data array
#         elif i > (data.shape[1] - (half_window)):
#             aux[:,i] = data[:,i] - np.median(data[:, (i-half_window):-1], 1)

#         else:
#             aux[:,i] = data[:,i] - np.median(data[:, (i-half_window):(i+half_window)], 1)
#     return aux


"""
 
  ######  ########     ###    ##    ##  ######  
 ##    ## ##     ##   ## ##   ###   ## ##    ## 
 ##       ##     ##  ##   ##  ####  ## ##       
  ######  ########  ##     ## ## ## ##  ######  
       ## ##        ######### ##  ####       ## 
 ##    ## ##        ##     ## ##   ### ##    ## 
  ######  ##        ##     ## ##    ##  ######  
 
"""

def get_spans_from_names(LogDf, on_name, off_name):
    """
    like log2span although with arbitrary events
    this function takes care of above problems actually
    """
    try:
        ons = LogDf.groupby('name').get_group(on_name)
        offs = LogDf.groupby('name').get_group(off_name)
    except KeyError:
        # thrown when name not in log - return empty Df
        return pd.DataFrame(columns=['t_on','t_off','dt'])

    t_max = offs.iloc[-1]['t']
    ts = []
    for tup in ons.itertuples():
        t_on = tup.t
        try:
            t_off = time_slice(offs, t_on, t_max, 't').iloc[0]['t']
            ts.append((t_on,t_off))
        except IndexError:
            # this checks if there is a off after last on
            pass

    SpansDf = pd.DataFrame(ts,columns=['t_on','t_off'])
    SpansDf['dt'] = SpansDf['t_off'] - SpansDf['t_on']
  
    return SpansDf

def get_spans(LogDf,span_names):
    """ helper to get spans for multple names from LogDf span names
    returns a dict """
    SpansDict = {}
    for span_name in span_names:
        on_name = span_name + '_ON'
        off_name = span_name + '_OFF'
        SpansDict[span_name] = get_spans_from_names(LogDf, on_name, off_name)
    
    return SpansDict

"""
 
 ######## ########  ####    ###    ##        ######  
    ##    ##     ##  ##    ## ##   ##       ##    ## 
    ##    ##     ##  ##   ##   ##  ##       ##       
    ##    ########   ##  ##     ## ##        ######  
    ##    ##   ##    ##  ######### ##             ## 
    ##    ##    ##   ##  ##     ## ##       ##    ## 
    ##    ##     ## #### ##     ## ########  ######  
 
"""

def parse_trial(TrialDf, Metrics):
    """
    TrialDf is a time slice of a LogDf
    Metrics is list of callables that take a TrialDf as their argument
    and returning a Series
    
    returns a one row DataFrame
    notes: does not know about trial number
    """
    # FIXME this has to be checked with the online routine if necessary or can be caught otherwise
    # print(TrialDf)
    # try:
    #     # entry event
    #     t = TrialDf.groupby('name').get_group('TRIAL_AVAILABLE_STATE').iloc[0]['t']
    #     print("time is",t)
    # except KeyError:
    #     print("parse trial returns none")
    #     # if TrialDf has no entry event - this happens online before first trial
    #     return None
    if TrialDf.shape[0] == 0:
        return None
    
    else:
        t = TrialDf.iloc[0]['t']

        # getting metrics
        metrics = [Metric(TrialDf) for Metric in Metrics]
        TrialMetricsDf = pd.DataFrame(metrics).T
        
        # correcting dtype
        for metric in metrics:
            TrialMetricsDf[metric.name] = TrialMetricsDf[metric.name].astype(metric.dtype)
        
        # adding time
        TrialMetricsDf['t'] = t

        return TrialMetricsDf
    
def parse_trials(TrialDfs, Metrics):
    """ helper to run parse_trial on multiple trials.
    TrialsDfs is a list of TrialDf """
    SessionDf = pd.concat([parse_trial(Df, Metrics) for Df in TrialDfs], axis=0)
    SessionDf = SessionDf.reset_index(drop=True)
  
    return SessionDf

"""
 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
       ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""

def parse_session(SessionDf, Metrics):
    """ Applies 2nd level metrics to a session """

    # Session is input to Metrics - list of callable functions, each a "Metric"
    metrics = [Metric(SessionDf) for Metric in Metrics]
    SessionMetricsDf = pd.DataFrame(metrics).T

    # correcting dtype
    for metric in metrics:
        SessionMetricsDf[metric.name] = SessionMetricsDf[metric.name].astype(metric.dtype)

    return SessionMetricsDf

def parse_sessions(SessionDfs, Metrics):
    """ helper to run parse_session on multiple sessions.
    SessionDfs is a list of SessionDf """

    PerformanceDf = pd.concat([parse_session(SessionDf, Metrics) for SessionDf in SessionDfs])
    PerformanceDf = PerformanceDf.reset_index(drop = 'True')

    return PerformanceDf

def aggregate_session_logs(animal_path, task):
    """ 
    creates a list of LogDfs with all data obtained 
    using input task an path to animal's folder  
    """

    # search and store all folder paths (sessions) containing 
    # data obtained performing input task
    folder_paths = [fd for fd in animal_path.iterdir() if fd.is_dir()]

    log_paths = [] 

    for fd in folder_paths:

        # Parsing folder name by "_"
        split_fd = fd.name.split("_")

        date = split_fd[0]
        task_name = "_".join(split_fd[2:])
        
        date_format = '%Y-%m-%d'
        # Checks if date format is not corrupted
        try:
            datetime.datetime.strptime(date, date_format)

            if task_name == task:
                log_paths.append(animal_path.joinpath(fd, "arduino_log.txt"))
        except:
            print("Folder/File " + fd + " has corrupted date")

    LogDfs = []
    for log in log_paths:
        LogDfs.append(get_LogDf_from_path(log))

    return LogDfs

"""
 
  ######  ##       ####  ######  ######## 
 ##    ## ##        ##  ##    ## ##       
 ##       ##        ##  ##       ##       
  ######  ##        ##  ##       ######   
       ## ##        ##  ##       ##       
 ##    ## ##        ##  ##    ## ##       
  ######  ######## ####  ######  ######## 
 
"""

def time_slice(Df, t_min, t_max, col='t', reset_index=True):
    """ helper to slice a dataframe along time (defined by col) """
    vals = Df[col].values
    binds = np.logical_and(vals > t_min, vals < t_max)

    if reset_index:
        Df = Df.reset_index(drop=True)

    return Df.loc[binds]

"""
 
 ##     ## ######## ######## ########  ####  ######   ######  
 ###   ### ##          ##    ##     ##  ##  ##    ## ##    ## 
 #### #### ##          ##    ##     ##  ##  ##       ##       
 ## ### ## ######      ##    ########   ##  ##        ######  
 ##     ## ##          ##    ##   ##    ##  ##             ## 
 ##     ## ##          ##    ##    ##   ##  ##    ## ##    ## 
 ##     ## ########    ##    ##     ## ####  ######   ######  
 
"""

### Trial level metrics
def has_choice(TrialDf):
    if "CHOICE_EVENT" in TrialDf['name'].values:
        choice = True
    else:
        choice = False    
 
    return pd.Series(choice, name='has_choice')

def is_successful(TrialDf):
    if "TRIAL_SUCCESSFUL_EVENT" in TrialDf['name'].values:
        succ = True
    else:
        succ = False    
 
    return pd.Series(succ, name='successful')

def reward_collected(TrialDf):
    """ note: false if trial not successful (not nan) """
    if is_successful(TrialDf).values[0]:
        if "REWARD_COLLECTED_EVENT" in TrialDf['name'].values:
            rew_col = True
        else:
            rew_col = False
    else:
        rew_col = False

    return pd.Series(rew_col, name='reward_collected')

def reward_collection_RT(TrialDf):
    """ calculate the reaction time from reward availability cue to reward collection """
    if is_successful(TrialDf).values[0] == False or reward_collected(TrialDf).values[0] == False:
        rt = np.NaN
    else:
        t_rew_col = TrialDf.groupby('name').get_group("REWARD_COLLECTED_EVENT").iloc[-1]['t']
        t_rew_avail = TrialDf.groupby('name').get_group("REWARD_AVAILABLE_EVENT").iloc[-1]['t']
        rt = t_rew_col - t_rew_avail
 
    return pd.Series(rt, name='reward_collected_rt')

def choice_RT(TrialDf):
    """ RT between go cue and decision """
    if has_choice(TrialDf).values[0] == False:
        rt = np.NaN
    else:
        try:
            t_go_cue = TrialDf.groupby('name').get_group("GO_CUE_EVENT").iloc[-1]['t']
            t_choice = TrialDf.groupby('name').get_group("CHOICE_EVENT").iloc[-1]['t']
            rt = t_choice - t_go_cue
        except KeyError:
            # TODO debug when this is thrown
            rt = np.NaN
 
    return pd.Series(rt, name='choice_rt')

def get_choice(TrialDf):
    """ 0 for left, 1 for right """
    if has_choice(TrialDf).values[0]:
        if "CHOICE_LEFT_EVENT" in TrialDf['name'].values:
            choice = "left"
        else:
            choice = "right"
    else:
        choice = np.NaN
    
    return pd.Series(choice, name="choice")

def get_timing_interval(TrialDf):
    try:
        Df = TrialDf.groupby('var').get_group('this_interval')
        interval = Df.iloc[0]['value']
    except KeyError:
        interval = sp.NaN
    return pd.Series(interval, name='timing_interval')




### Session level metrics
def rewards_collected(SessionDf):
    """ calculate the fraction of collected rewards across the session """
    n_rewards_collected = SessionDf['reward_collected'].sum()
    n_successful_trials = SessionDf['successful'].sum()

    return pd.Series(n_rewards_collected/n_successful_trials, name='rewards_collected')

def mean_reward_collection_rt(SessionDf):
    """ calculate mean reward collection reaction time across session """
    rt = SessionDf['reward_collected_rt'].mean(skipna=True)

    return pd.Series(rt, name='mean_reward_collection_rt')

"""

 ##     ##    ###    ########  ########
 ##     ##   ## ##   ##     ## ##     ##
 ##     ##  ##   ##  ##     ## ##     ##
 ######### ##     ## ########  ########
 ##     ## ######### ##   ##   ##
 ##     ## ##     ## ##    ##  ##
 ##     ## ##     ## ##     ## ##

"""

def parse_harp_csv(harp_csv_path, save=True):
    """ gets the loadcell data and the sync times from a harp csv log """

    with open(harp_csv_path,'r') as fH:
        lines = fH.readlines()

    header = lines[0].split(',')

    t_sync = []
    LoadCellDf = []

    for line in tqdm(lines[1:],desc="parsing harp log"):
        elements = line.split(',')
        if elements[0] == '3': # line is an event
            if elements[1] == '33': # line is a load cell read
                data = line.split(',')[2:5]
                LoadCellDf.append(data)
            if elements[1] == '34': # line is a digital input timestamp
                line = line.strip().split(',')
                if line[3] == '1':
                    t_sync.append(float(line[2])*1000) # convert to ms

    LoadCellDf = pd.DataFrame(LoadCellDf,columns=['t','x','y'],dtype='float')
    LoadCellDf['t_original'] = LoadCellDf['t'] # keeps the original
    LoadCellDf['t'] = LoadCellDf['t'] * 1000

    if save:
        # write to disk
        LoadCellDf.to_csv(harp_csv_path.parent / "loadcell_data.csv")
        pd.DataFrame(t_sync,columns=['t']).to_csv(harp_csv_path.parent / "harp_sync.csv")
            
        # np.save(path / "loadcell_sync.npy", np.array(t_sync,dtype='float32'))
    
    return LoadCellDf, t_sync

def get_arduino_sync(log_path, sync_event_name="TRIAL_AVAILABLE_STATE", save=True):
    """ extracts arduino sync times from an arduino log """ 

    # TODO this should be an util func
    task_name = '_'.join(log_path.parent.name.split('_')[2:])
    code_map_path = log_path.parent / task_name / "Arduino" / "src" / "event_codes.h"

    ### READ 
    CodesDf = bhv.parse_code_map(code_map_path)
    code_map = dict(zip(CodesDf['code'],CodesDf['name']))
    LogDf = bhv.parse_arduino_log(log_path, code_map)

    SyncEvent = bhv.get_events_from_name(LogDf, sync_event_name)

    if save:
        SyncEvent.to_csv(log_path.parent / "arduino_sync.csv")

    return SyncEvent

def sync_clocks(t_harp, t_arduino, log_path=None):
    """ linregress between two clocks - master clock is harp
    if LogDf is given, save the corrected clock to it"""

    if t_harp.shape != t_arduino.shape:
        print("unequal number of sync pulses in the two files! ")

    from scipy import stats

    res = stats.linregress(t_arduino,t_harp)
    m,b = res.slope,res.intercept

    if log_path is not None:
        LogDf = get_LogDf_from_path(log_path)
        LogDf['t_original'] = LogDf['t'] # store original time stampts
        LogDf['t'] = LogDf['t']*m + b
        LogDf.to_csv(log_path.parent / "LogDf.csv")

    return m, b