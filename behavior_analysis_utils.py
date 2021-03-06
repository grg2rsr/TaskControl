import scipy as sp
import pandas as pd
import numpy as np
import os 
from pathlib import Path
import utils
import datetime
from tqdm import tqdm
import behavior_analysis_utils as bhv
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection


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
    CodesDf = utils.parse_code_map(code_map_path)
    code_map = dict(zip(CodesDf['code'], CodesDf['name']))

    try:
        LogDf = bhv.parse_arduino_log(log_path, code_map)
    except ValueError:
        # Dealing with the earlier LogDfs not having X_tresh/Current_zone etc.
        LogDf = bhv.parse_arduino_log(log_path, code_map, parse_var=False)

    return LogDf

def parse_arduino_log(log_path, code_map=None, parse_var=True):
    """ create a DataFrame representation of an arduino log. If a code map is passed 
    a corresponding decoded column will be created

    for offline use
    """
    with open(log_path, 'r') as fH:
        lines = fH.readlines()

    return parse_lines(lines, code_map=code_map, parse_var=parse_var)

def correct_wraparound(Df):
    """ tests and corrects for time wraparound on column t """
    if np.any(np.diff(Df['t']) < 0):
        reversal_ind = np.where(np.diff(Df['t']) < 0)[0][0]
        Df['t'].iloc[reversal_ind+1:] += Df['t'].iloc[reversal_ind]
    return Df

def parse_lines(lines, code_map=None, parse_var=False):
    """ parses a list of lines from arduino into a pd.DataFrame """
    LogDf = pd.DataFrame([line.split('\t') for line in lines if '\t' in line], columns=['code', 't'])
    LogDf['t'] = LogDf['t'].astype('float')
    LogDf = correct_wraparound(LogDf)
    LogDf = LogDf.reset_index(drop=True)

    for col in ['name', 'var', 'value']:
        LogDf[col] = np.NaN

    # decode
    if code_map is not None:
        LogDf['name'] = [code_map[code] for code in LogDf['code']]

    if parse_var:
        var_lines = [line.strip() for line in lines if line.startswith('<VAR')]
        VarDf = pd.DataFrame([line[1:-1].split(' ') for line in var_lines], columns=['_', 'var', 'value', 't'])
        VarDf = VarDf.drop('_', axis=1)
        VarDf['t'] = VarDf['t'].astype('float')
        VarDf['value'] = VarDf['value'].astype('float')
        
        VarDf = correct_wraparound(VarDf)
        
        # join
        LogDf = LogDf.append(VarDf, ignore_index=True, sort=True)
        LogDf = LogDf.sort_values('t')
        LogDf = LogDf.reset_index(drop=True)

    return LogDf

# def parse_lines_old(lines, code_map=None):
#     """ parses a list of lines from arduino into a pd.DataFrame
#     the old (more performant) function
#     """
#     valid_lines = [line.strip() for line in lines if '\t' in line]
#     LogDf = pd.DataFrame([line.split('\t') for line in valid_lines], columns=['code', 't'])
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
    LickSpan = get_spans_from_names(LogDf, 'LICK_ON', 'LICK_OFF')

    bad_licks = np.logical_or(LickSpan['dt'] < min_time , LickSpan['dt'] > max_time)
    LickSpan = LickSpan.loc[~bad_licks]

    # Add lick_event to LogDf
    Lick_Event = pd.DataFrame(np.stack([['NA']*LickSpan.shape[0], LickSpan['t_on'].values, ['LICK_EVENT']*LickSpan.shape[0]]).T, columns=['code', 't', 'name'])
    Lick_Event['t'] = Lick_Event['t'].astype('float')
    LogDf = LogDf.append(Lick_Event)
    LogDf.sort_values('t')

    if remove is True:
        # TODO
        pass

    return LogDf

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
        return pd.DataFrame(columns=['t_on', 't_off', 'dt'])

    ts = []
    for i, tup in enumerate(ons.itertuples()):
        t_on = tup.t
        binds = offs['t'] > t_on
        if np.any(binds.values):
            t_off = offs.iloc[np.argmax(binds.values)]['t']
            ts.append((t_on, t_off))

    SpansDf = pd.DataFrame(ts, columns=['t_on', 't_off'])
    SpansDf['dt'] = SpansDf['t_off'] - SpansDf['t_on']
  
    return SpansDf

def get_spans(LogDf, span_names):
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
    """ helper to run parse_trial on multiple trials """
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
    
def create_LogDf_LCDf_csv(fd_path, task_name):
    """ 
    Creates both LogDf and LCDf .csv files for each session and syncs arduino to harp timestamps
    """

    # obtaining the paths to each sessions folder
    SessionsDf = utils.get_sessions(fd_path)
    paths = []

    for iter_path in SessionsDf.groupby('task').get_group(task_name)['path']:
        if not os.path.isfile(iter_path + "\loadcell_data.csv") or not os.path.isfile( iter_path + "\LogDf.csv"):
            paths.append(Path(iter_path))

    for path in paths:
        # infer data paths
        log_path = path / "arduino_log.txt"
        harp_csv_path = path.joinpath("bonsai_harp_log.csv")

        # get arduino and LC timestamps
        t_arduino = bhv.get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT", save=True)['t'].values
        _ , t_harp = bhv.parse_harp_csv(harp_csv_path, save=True)
        t_harp = t_harp['t'].values

        # Check synching clock lenghts
        if len(t_harp) == 0:
            print("t_harp is empty")
            continue
        elif len(t_arduino) == 0:
            print("t_arduino is empty")
            continue
        elif t_harp.shape[0] != t_arduino.shape[0]:
            print("Unequal number of timestamps in: " + str(path))
            t_arduino, t_harp = cut_timestamps(t_arduino, t_harp)

        # sync datasets and store LogDf.csv
        _,_ = bhv.sync_clocks(t_harp, t_arduino, log_path = log_path)
        

"""
 
  ######  ##       ####  ######  ######## 
 ##    ## ##        ##  ##    ## ##       
 ##       ##        ##  ##       ##       
  ######  ##        ##  ##       ######   
       ## ##        ##  ##       ##       
 ##    ## ##        ##  ##    ## ##       
  ######  ######## ####  ######  ######## 
 
"""

def time_slice(Df, t_min, t_max, col='t', reset_index=True, mode='inclusive'):
    """ helper to slice a dataframe along time (defined by col) """
    vals = Df[col].values
    if mode=='exclusive':
        binds = np.logical_and(vals > t_min, vals < t_max)
    if mode is 'inclusive':
        binds = np.logical_and(vals >= t_min, vals <= t_max)

    if reset_index:
        Df = Df.reset_index(drop=True)

    return Df.loc[binds]

def event_slice(Df, event_a, event_b, col='name', reset_index=True):
    """ helper function that slices Df along column name from event_a to event_b """
    ix_start = Df[Df['name'] == event_a].index[0]
    ix_stop = Df[Df['name'] == event_b].index[0]
    return Df.loc[ix_start:ix_stop]
    

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
    var_name = 'has_choice'

    if "CHOICE_EVENT" in TrialDf['name'].values:
        var = True
    else:
        var = False    
 
    return pd.Series(var, name=var_name)

def is_successful(TrialDf):
    var_name = 'successful'

    if "TRIAL_SUCCESSFUL_EVENT" in TrialDf['name'].values:
        var = True
    else:
        var = False
 
    return pd.Series(var, name=var_name)

def reward_collected(TrialDf):
    var_name = 'rew_collected'

    if is_successful(TrialDf).values[0]:
        if "REWARD_COLLECTED_EVENT" in TrialDf['name'].values:
            var = True
        else:
            var = False
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)

def reward_omitted(TrialDf):
    var_name = 'rew_omitted'

    if is_successful(TrialDf).values[0]:
        if "REWARD_OMITTED_EVENT" in TrialDf['name'].values:
            var = True
        else:
            var = False
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)

def reward_collection_RT(TrialDf):
    var_name = 'rew_collected_rt'

    if is_successful(TrialDf).values[0] == True and reward_collected(TrialDf).values[0] == True:
        t_rew_col = TrialDf.groupby('name').get_group("REWARD_COLLECTED_EVENT").iloc[-1]['t']
        t_rew_avail = TrialDf.groupby('name').get_group("REWARD_AVAILABLE_EVENT").iloc[-1]['t']
        var = t_rew_col - t_rew_avail
    else:
        var = np.NaN
 
    return pd.Series(var, name=var_name)

def choice_RT(TrialDf):
    var_name = 'choice_rt'

    if has_choice(TrialDf).values[0] == True:
        try:
            t_go_cue = TrialDf.groupby('name').get_group("GO_CUE_EVENT").iloc[-1]['t'] # this may break for final learn to time
            t_choice = TrialDf.groupby('name').get_group("CHOICE_EVENT").iloc[-1]['t']
            var = t_choice - t_go_cue
        except KeyError:
            # TODO debug when this is thrown
            var = np.NaN
    else:
        var = np.NaN
 
    return pd.Series(var, name=var_name)

def get_choice(TrialDf): # Diagonals are consider as X-axis choices, not Y-axis
    var_name = "choice"

    if has_choice(TrialDf).values[0] == True:
        if (bhv.get_choice_zone(TrialDf).values[0] == (1,4,7)).any(): # if any is True
            var = "left"
        elif (bhv.get_choice_zone(TrialDf).values[0] == (3,6,9)).any():
            var = "right"
        elif get_choice_zone(TrialDf).values[0] == 8:
            var = "up"
        elif get_choice_zone(TrialDf).values[0] == 2:
            var = "down"
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_choice_zone(TrialDf):
    var_name = "choice_zone"

    if "CHOICE_EVENT" in TrialDf.name.values or "PREMATURE_CHOICE_EVENT" in TrialDf.name.values:
        try:
            current_zone_times = TrialDf[TrialDf['var'] == 'current_zone']['t'].values

            if "CHOICE_EVENT" in TrialDf.name.values:
                choice_time = TrialDf[TrialDf['name'] == 'CHOICE_EVENT']['t'].values
            if "PREMATURE_CHOICE_EVENT" in TrialDf.name.values:
                choice_time = TrialDf[TrialDf['name'] == 'PREMATURE_CHOICE_EVENT']['t'].values    

            # Get zone cahnge nearest to choice event (no need if there is only 1 current_zone)
            if len(current_zone_times)==1:
                var = TrialDf[TrialDf['var'] == 'current_zone']['value'].values
            else:
                choice_zone_idx = (np.abs(current_zone_times - choice_time)).argmin() # get idx of closest
                var = int(TrialDf[TrialDf['var'] == 'current_zone']['value'].values[choice_zone_idx])
        except:
            var = np.NaN

    return pd.Series(var, name=var_name)

def get_correct_zone(TrialDf):
    var_name = "correct_zone"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_interval(TrialDf):
    var_name = "this_interval"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_in_corr_loop(TrialDf):
    var_name = "in_corr_loop"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value'].astype('bool')
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_instructed(TrialDf):
    var_name = "instructed_trial"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value'].astype('bool')
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_x_thresh(TrialDf):
    var_name = "X_thresh"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_bias(TrialDf):
    var_name = "bias"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_start(TrialDf):
    return pd.Series(TrialDf.iloc[0]['t'], name='t_on')

def get_stop(TrialDf):
    return pd.Series(TrialDf.iloc[-1]['t'], name='t_off')

def get_outcome(TrialDf):
    var_name = "outcome"

    if "CHOICE_MISSED_EVENT" in TrialDf['name'].values:
        var = "missed"
    elif "CHOICE_INCORRECT_EVENT" in TrialDf['name'].values:
        var = "incorrect"
    elif "CHOICE_CORRECT_EVENT" in TrialDf['name'].values:
        var = "correct"
    elif "PREMATURE_CHOICE_EVENT" in TrialDf['name'].values:
        var = "premature"
    else:
        var = np.NaN

    return pd.Series(var, name = var_name)

## Session level metrics

def trial_engagement(SessionDf):
    
    missedDf = (SessionDf['outcome'] == 'missed').rolling(20).mean()
    ys_diff = np.array(missedDf.diff(periods=10)) # derivative
    ys = np.array(missedDf)

    engaged = 0
    # If there is less than 30% missed trials and not increasing or reverse
    for (y_diff,y) in zip(ys_diff,ys):
        if (y<0.40 and y_diff < 0.25) or (y>0.40 and y_diff < -0.25):
            engaged = engaged + 1 
    
    engagement_ratio = engaged/len(SessionDf)

    return round(engagement_ratio*100)

def water_consumed(log_path):
    """
        Returns the total amount of rewards consumed even if reward magnitude changes across session 
    """

    # THIS FUNCTION IS CURRENTLY BROKEN #

    reward_mag, water_consumed = 0 , 0
    ts , updated_mags = [], []

    LogDf = pd.read_csv(log_path.parent / "LogDf.csv")
    with open(log_path, 'r') as fH:
        lines = fH.readlines()
    
    # Seach all lines
    for line in lines:

        # to find when reward mag. is updated 
        if line.startswith('<Arduino') and 'reward_magnitude' in line:
            new_reward_mag = line[-4:-2]

            # and if reward mag. differs from previous one
            if new_reward_mag != reward_mag:
                updated_mags.append(float(new_reward_mag)) # save it and

                # go backwards in lines to search for timepoint of change
                for j in range(0,-100,-1): # -30 is arbitrary, just making sure it searches back enough
                    if lines[j].startswith('<VAR'):
                        ts.append(float(lines[j].split(' ')[-1][:-3]))
                        
                        break
                reward_mag = new_reward_mag

    # In case the whole session uses the default reward mag. settings
    if ts == []:
        task_name = 'str'
        default_rew_mag = 10
        water_consumed = len(LogDf[LogDf['name'] == 'REWARD_COLLECTED_EVENT'])*default_rew_mag

    # In case it only changes once
    elif len(ts) == 1:
        water_consumed = len(LogDf[LogDf['name'] == 'REWARD_COLLECTED_EVENT'])*updated_mags[-1]

    # obtain number of rewards collected between timepoints and multiply by the corresponding reward magnitude
    else:
        for i,t in enumerate(ts):
            print(t)
            if i < len(ts):
                print('what')
                Df = bhv.time_slice(LogDf, ts, float(ts[i]))
            else: # for the last timepoint
                Df = bhv.time_slice(LogDf, t, LogDf['t'].iloc[-1])
                aux = len(Df[Df['name'] == 'REWARD_COLLECTED_EVENT'])*updated_mags[i]
                water_consumed += aux

    return water_consumed 

"""

 ##     ##    ###    ########  ########
 ##     ##   ## ##   ##     ## ##     ##
 ##     ##  ##   ##  ##     ## ##     ##
 ######### ##     ## ########  ########
 ##     ## ######### ##   ##   ##
 ##     ## ##     ## ##    ##  ##
 ##     ## ##     ## ##     ## ##

"""

def parse_bonsai_LoadCellData(csv_path, save=True, trig_len=1, ttol=0.2):
    LoadCellDf = pd.read_csv(csv_path, names=['t','x','y'])

    harp_sync = pd.read_csv(csv_path.parent / "bonsai_harp_sync.csv", names=['t']).values.flatten()
    t_sync_high = harp_sync[::2]
    t_sync_low = harp_sync[1::2]

    dts = np.array(t_sync_low) - np.array(t_sync_high)
    good_timestamps = ~(np.absolute(dts-trig_len)>ttol)
    t_sync = np.array(t_sync_high)[good_timestamps]

    t_sync = pd.DataFrame(t_sync, columns=['t'])
    if save:
        # write to disk
        # LoadCellDf.to_csv(harp_csv_path.parent / "loadcell_data.csv") # obsolete now
        t_sync.to_csv(csv_path.parent / "harp_sync.csv")

    return LoadCellDf, t_sync

def parse_harp_csv(harp_csv_path, save=True, trig_len=1, ttol=0.2):
    """ gets the loadcell data and the sync times from a harp csv log
    trig_len is time in ms of sync trig high, tol is deviation in ms
    check harp sampling time, seems to be 10 khz? """

    with open(harp_csv_path, 'r') as fH:
        lines = fH.readlines()

    header = lines[0].split(',')

    t_sync_high = []
    t_sync_low = []
    LoadCellDf = []
    
    for line in tqdm(lines[1:], desc="parsing harp log", position=0, leave=True):
        elements = line.split(',')
        if elements[0] == '3': # line is an event
            if elements[1] == '33': # line is a load cell read
                data = line.split(',')[2:5]
                LoadCellDf.append(data)
            if elements[1] == '34': # line is a digital input timestamp
                line = line.strip().split(',')
                if line[3] == '1': # high values
                    t_sync_high.append(float(line[2])*1000) # convert to ms
                if line[3] == '0': # low values
                    t_sync_low.append(float(line[2])*1000) # convert to ms

    dts = np.array(t_sync_low) - np.array(t_sync_high)
    good_timestamps = ~(np.absolute(dts-trig_len)>ttol)
    t_sync = np.array(t_sync_high)[good_timestamps]

    LoadCellDf = pd.DataFrame(LoadCellDf, columns=['t', 'x', 'y'], dtype='float')
    LoadCellDf['t_original'] = LoadCellDf['t'] # keeps the original
    LoadCellDf['t'] = LoadCellDf['t'] * 1000

    t_sync = pd.DataFrame(t_sync, columns=['t'])
    if save:
        # write to disk
        LoadCellDf.to_csv(harp_csv_path.parent / "loadcell_data.csv")
        t_sync.to_csv(harp_csv_path.parent / "harp_sync.csv")
    
    return LoadCellDf, t_sync

def get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT", save=True):
    """ extracts arduino sync times from an arduino log """ 

    LogDf = bhv.get_LogDf_from_path(log_path)
    SyncEvent = bhv.get_events_from_name(LogDf, sync_event_name)

    if save:
        SyncEvent.to_csv(log_path.parent / "arduino_sync.csv")

    return SyncEvent

def cut_timestamps(t_arduino, t_harp, verbose=False):
    """ finds offset between to unequal timestamp series and cuts
    the bigger to match the size of the smaller """

    if verbose:
        print("timestamps in arduino: "+ str(t_arduino.shape[0]))
        print("timestamps in harp: "+ str(t_harp.shape[0]))

    if t_harp.shape[0] > t_arduino.shape[0]:
        bigger = 'harp'
        t_bigger = t_harp
        t_smaller = t_arduino
    else:
        bigger = 'arduino'
        t_bigger = t_arduino
        t_smaller = t_harp

    offset = np.argmax(np.correlate(np.diff(t_bigger), np.diff(t_smaller), mode='valid'))
    if verbose:
        print("offset between the two: ", offset)
    t_bigger = t_bigger[offset:t_smaller.shape[0]+offset]

    if bigger == 'harp':
        t_harp = t_bigger
        t_arduino = t_smaller
    else:
        t_arduino = t_bigger
        t_harp = t_smaller
    
    return t_arduino, t_harp

def sync_clocks(t_harp, t_arduino, log_path=None):
    """ linregress between two clocks - master clock is harp
    if LogDf is given, save the corrected clock to it"""

    from scipy import stats

    res = stats.linregress(t_arduino, t_harp)
    m, b = res.slope, res.intercept

    if log_path is not None:
        LogDf = get_LogDf_from_path(log_path)
        LogDf['t_original'] = LogDf['t'] # store original time stampts
        LogDf['t'] = LogDf['t']*m + b
        LogDf.to_csv(log_path.parent / "LogDf.csv")

    return m, b


"""
 ######  ########    ###    ########  ######
##    ##    ##      ## ##      ##    ##    ##
##          ##     ##   ##     ##    ##
 ######     ##    ##     ##    ##     ######
      ##    ##    #########    ##          ##
##    ##    ##    ##     ##    ##    ##    ##
 ######     ##    ##     ##    ##     ######
"""
from sklearn.linear_model import LogisticRegression
from scipy.special import expit

def log_reg(x, y, x_fit=None):
    """ x and y are of shape (N, ) y are choices in [0, 1] """
    if x_fit is None:
        x_fit = np.linspace(x.min(), x.max(), 100)

    cLR = LogisticRegression()
    cLR.fit(x[:, np.newaxis], y)

    y_fit = expit(x_fit * cLR.coef_ + cLR.intercept_).flatten()
    return y_fit

def tolerant_mean(arrs):
    'A mean that is tolerant to different sized arrays'

    max_length = np.max([arr.shape[0] for arr in arrs]) # get largest array

    arrs=[np.pad(arr, (0, max_length-arr.shape[0]), mode='constant', constant_values=np.nan) for arr in arrs] # pad every array until max_length to obtain square matrix

    return np.nanmean(arrs, axis = 0)


"""
########  ##        #######  ########    ##     ## ######## ##       ########  ######## ########   ######
##     ## ##       ##     ##    ##       ##     ## ##       ##       ##     ## ##       ##     ## ##    ##
##     ## ##       ##     ##    ##       ##     ## ##       ##       ##     ## ##       ##     ## ##
########  ##       ##     ##    ##       ######### ######   ##       ########  ######   ########   ######
##        ##       ##     ##    ##       ##     ## ##       ##       ##        ##       ##   ##         ##
##        ##       ##     ##    ##       ##     ## ##       ##       ##        ##       ##    ##  ##    ##
##        ########  #######     ##       ##     ## ######## ######## ##        ######## ##     ##  ######
"""

def get_events_window_aligned_on_event(LogDf, event_name, pre, post):

    ts = bhv.get_events_from_name(LogDf, event_name)['t'].values
    event_ts = []
    for t in ts:
        Df = bhv.time_slice(LogDf, t-pre, t+post)
        event_t = np.array(Df.groupby('name').get_group(event_name)['t'])

        event_ts.append(event_t)
    return event_ts

def get_events_window_between_events(TrialDfs, event_name, first_event, second_event):
    " Returns list of np.arrays with event_name for all trials in a window between any two sequential(!) events"

    licks = []
    for TrialDf in TrialDfs:

        t1 = float(TrialDf[TrialDf.name == first_event]['t'])
        if second_event == 'last':
            t2 = float(TrialDf['t'].iloc[-1])
        else:
            t2 = float(TrialDf[TrialDf.name == second_event]['t'])

        trial = bhv.time_slice(TrialDf, t1, t2)
        raw_lick_times = np.array(trial.groupby('name').get_group(event_name)['t'])
        lick = raw_lick_times-t1

        licks.append(lick)

    return licks

def triaL_to_choice_matrix(trial, choice_matrix):
    " Counts the number of decisions made for up/down/left/right "

    # top row
    if trial.choice == "up": 
        choice_matrix[0, 1] +=1

    # middle row
    if trial.choice == "left": 
        choice_matrix[1, 0] +=1
    if trial.choice == "right": 
        choice_matrix[1, 2] +=1

    # bottom row
    if trial.choice == "down": 
        choice_matrix[2, 1] +=1
        
    return choice_matrix  

def truncate_pad_vector(arrs, pad_with = None, max_len = None):
    " Truncate and pad an array with rows of different dimensions to max_len (defined either by user or input arrs)"
    
    # In case length is not defined by user
    if max_len == None:
        list_len = [len(arr) for arr in arrs]
        max_len = max(list_len)

    if pad_with == None:
        pad_with = np.NaN
    
    trunc_pad_arr = np.empty((len(arrs), max_len)) 

    for i, arr in enumerate(arrs):
        if len(arr) < max_len:
            trunc_pad_arr[i,:] = np.pad(arr, (0, max_len-arr.shape[0]), mode='constant',constant_values=(pad_with,))
        elif len(arr) > max_len:
            trunc_pad_arr[i,:] = np.array(arr[:max_len])

    return trunc_pad_arr

def get_FxFy_window_aligned_on_event(LoadCellDf, TrialDfs, align_event, pre, post):
    """
        Returns Fx/Fy/Fmag NUMPY ND.ARRAY for all trials aligned to an event in a window defined by [align-pre, align+post]"
        Don't forget: we are using nd.arrays so, implicitly, we use advanced slicing which means [row, col] instead of [row][col]
    """
    Fx, Fy, Fmag = [],[],[]
    for TrialDf in TrialDfs:
        t_align = TrialDf.loc[TrialDf['name'] == align_event, 't'].values[0]
        LCDf = bhv.time_slice(LoadCellDf, t_align-pre, t_align+post)

        Fx.append(LCDf['x'].values)
        Fy.append(LCDf['y'].values)
        Fmag.append(np.sqrt(LCDf['x']**2 + LCDf['y']**2))

    Fx = np.array(Fx).T
    Fy = np.array(Fy).T
    Fmag = np.array(Fmag).T

    return Fx,Fy,Fmag

def get_FxFy_window_between_events(LoadCellDf, TrialDfs, first_event, second_event, pad_with = None):
    """
        Returns Fx/Fy/Fmag NUMPY ND.ARRAY with dimensions (trials, max_array_len) for all trials in a window between any two sequential(!) events
        Don't forget: we are using nd.arrays so, implicitly, we use advanced slicing which means [row, col] instead of [row][col]
    """

    Fx, Fy, Fmag = [],[],[] 
    for i, TrialDf in enumerate(TrialDfs):
        if not TrialDf.empty:
            if first_event == 'first': # From start of trial
                time_1st = float(TrialDf['t'].iloc[0])
            else:
                time_1st = float(TrialDf[TrialDf.name == first_event]['t'])

            if second_event == 'last': # Until end of trial
                time_2nd = float(TrialDf['t'].iloc[-1])
            else:
                time_2nd = float(TrialDf[TrialDf.name == second_event]['t'])

            LCDf = bhv.time_slice(LoadCellDf, time_1st, time_2nd)
            Fx.append(LCDf['x'].values)
            Fy.append(LCDf['y'].values)
            Fmag.append(np.sqrt(LCDf['x']**2 + LCDf['y']**2))

    # Make sure we have numpy arrays with same length, pad with given input pad_with
    Fx = bhv.truncate_pad_vector(Fx,pad_with)
    Fy = bhv.truncate_pad_vector(Fy,pad_with)
    Fmag = bhv.truncate_pad_vector(Fmag,pad_with)

    return Fx,Fy,Fmag

def filter_trials_by(SessionDf,TrialDfs, filter_pairs):
    """
        This function filters input TrialDfs given filter_pair tuple (or list of tuples)
        Example: given filter_pairs [(outcome,correct) , (choice,left)] it will only output trials which are correct to left side 
    """

    if type(filter_pairs) is list: # in case its more than one pair
        groupby_keys = [filter_pair[0] for filter_pair in filter_pairs]
        getgroup_keys = tuple([filter_pair[1] for filter_pair in filter_pairs])
    else:
        groupby_keys = filter_pairs[0]
        getgroup_keys = filter_pairs[1]

    try:
        SDf = SessionDf.groupby(groupby_keys).get_group(getgroup_keys)
    except:
        print('The are no trials with given input filter_pair combination')
        raise KeyError

    TrialDfs_filt = np.array(TrialDfs)[SDf.index.values.astype(int)]

    return TrialDfs_filt

def line_gradients(data, axes = None):

    # Time-varying color code 
    cm = plt.cm.get_cmap('Greys')
    z = np.linspace(0, 1, num = len(data))

    # Line gradients 
    points = np.array(data).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    lc = LineCollection(segments, cmap=plt.get_cmap('Greys'), norm=plt.Normalize(0, 1))
    lc.set_array(z)
    lc.set_linewidth(0.5)
    lc.set_alpha(0.5)
    axes.add_collection(lc)

    return axes