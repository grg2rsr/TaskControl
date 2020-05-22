import scipy as sp
import pandas as pd
import numpy as np
import os 
from pathlib import Path
from functions import parse_code_map
import utils
import datetime

"""
 
 ########     ###    ########   ######  ######## ########  
 ##     ##   ## ##   ##     ## ##    ## ##       ##     ## 
 ##     ##  ##   ##  ##     ## ##       ##       ##     ## 
 ########  ##     ## ########   ######  ######   ########  
 ##        ######### ##   ##         ## ##       ##   ##   
 ##        ##     ## ##    ##  ##    ## ##       ##    ##  
 ##        ##     ## ##     ##  ######  ######## ##     ## 
 
"""
def parse_arduino_log(log_path, code_map=None):
    """ create a DataFrame representation of an arduino log. If a code map is passed 
    a corresponding decoded column will be created

    for offline use
    """
    with open(log_path,'r') as fH:
        lines = fH.readlines()

    return parse_lines(lines, code_map=code_map)

def parse_lines(lines, code_map=None):
    """ parses a list of lines from arduino into a pd.DataFrame """
    valid_lines = [line.strip() for line in lines if '\t' in line]
    LogDf = pd.DataFrame([line.split('\t') for line in valid_lines],columns=['code','t'])
    LogDf['t'] = LogDf['t'].astype('float')
    LogDf.reset_index(drop=True)

    # decode
    if code_map is not None:
        LogDf['name'] = [code_map[code] for code in LogDf['code']]

    # test for time wraparound
    if np.any(np.diff(LogDf['t']) < 0):
        reversal_ind = np.where(np.diff(LogDf['t']) < 0)[0][0]
        LogDf['t'].iloc[reversal_ind+1:] += LogDf['t'].iloc[reversal_ind]

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
        EventsDf = LogDf.groupby('name').get_group(event_name+'_EVENT')[['t']]
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

def filter_unreal_licks(min_time, max_time, SpansDict, LogDf, EventsDict):
    """ 
    Filter unrealistic licks from a SpansDict and adds Lick event to LogDf
    """

    bad_licks = np.logical_or(SpansDict['LICK']['dt'] < min_time , SpansDict['LICK']['dt'] > max_time)
    SpansDict['LICK'] = SpansDict['LICK'].loc[~bad_licks]

    # Add lick_event to LogDf
    Lick_Event = pd.DataFrame(np.stack([['NA']*SpansDict['LICK'].shape[0],SpansDict['LICK']['t_on'].values,['LICK_EVENT']*SpansDict['LICK'].shape[0]]).T,columns=['code','t','name'])
    Lick_Event['t'] = Lick_Event['t'].astype('float')
    LogDf = LogDf.append(Lick_Event)
    LogDf.sort_values('t')

    # Add lick_event to EventsDict
    EventsDict['LICK'] = get_events_from_name(LogDf,'LICK')
    SpansDict.pop("LICK")

    return SpansDict, EventsDict

"""
 
  ######  ########     ###    ##    ##  ######  
 ##    ## ##     ##   ## ##   ###   ## ##    ## 
 ##       ##     ##  ##   ##  ####  ## ##       
  ######  ########  ##     ## ## ## ##  ######  
       ## ##        ######### ##  ####       ## 
 ##    ## ##        ##     ## ##   ### ##    ## 
  ######  ##        ##     ## ##    ##  ######  
 
"""

def get_spans_from_event_names(LogDf, on_name, off_name):
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
        SpansDict[span_name] = get_spans_from_event_names(LogDf, on_name, off_name)
    
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
    try:
        # entry event
        t = TrialDf.groupby('name').get_group('TRIAL_AVAILABLE_STATE').iloc[0]['t']
    except KeyError:
        # if TrialDf has no entry event - this happens online before first trial
        return None

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
    SessionDf = pd.concat([parse_trial(Df, Metrics) for Df in TrialDfs],axis=0)
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

def aggregate_session_logs(animal_path, input_task):
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

            if task_name == input_task:
                log_paths.append(animal_path.joinpath(fd, "arduino_log.txt")) 
        except:
            print("Folder/File " + fd + " has corrupted date")

    # turn each log into logDf and unite logs into Series
    code_map_path = log_paths[0].parent.joinpath(task_name ,"Arduino","src","event_codes.h")
    CodesDf = parse_code_map(code_map_path)
    code_map = dict(zip(CodesDf['code'],CodesDf['name']))

    LogDfs = []
    for log in log_paths:
        LogDfs.append(parse_arduino_log(log, code_map))

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

def time_slice(Df, t_min, t_max, col='t'):
    """ helper to slice a dataframe along time (defined by col)"""
    vals = Df[col].values
    binds = np.logical_and(vals > t_min, vals < t_max)
  
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
# Frist level metrics

def is_successful(TrialDf):
    if "TRIAL_COMPLETED_EVENT" in TrialDf['name'].values:
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
    if is_successful(TrialDf).values[0] == False or reward_collected(TrialDf).values[0] == False:
        rew_col_rt = np.NaN
    else:
        t_rew_col = TrialDf.groupby('name').get_group("REWARD_COLLECTED_EVENT").iloc[-1]['t']
        t_rew_avail = TrialDf.groupby('name').get_group("REWARD_AVAILABLE_EVENT").iloc[-1]['t']
        rew_col_rt = t_rew_col - t_rew_avail
 
    return pd.Series(rew_col_rt, name='rew_col_rt')

# Second level metrics (metrics based on computations on first level metrics)

def collected_rate(SessionDf):

    # Index [1] always selects "True" irrespective of the number of "True" values
    # being higher or lower than "False" values
    reward_collected = SessionDf.reward_collected.value_counts()[1]
    successful_trials = SessionDf.successful.value_counts()[1]

    return pd.Series(round(reward_collected/successful_trials,3), name='collected_rate')

def mean_rt(SessionDf):

    rtMean = SessionDf.rew_col_rt.mean(skipna='True')
    
    return pd.Series(round(rtMean,3), name='mean_rt')