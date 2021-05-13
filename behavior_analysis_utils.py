import scipy as sp
import pandas as pd
import numpy as np
import os 
from pathlib import Path
import utils
import datetime
from tqdm import tqdm
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
        LogDf = parse_arduino_log(log_path, code_map)
    except ValueError:
        # Dealing with the earlier LogDfs not having X_tresh/Current_zone etc.
        LogDf = parse_arduino_log(log_path, code_map, parse_var=False)

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
    TODO generalize to filter event based on duration
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
    
def groupby_dict(Df, Dict):
    return Df.groupby(list(Dict.keys())).get_group(tuple(Dict.values()))

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

    # TODO check remove - deprecated?

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

def cut_timestamps(t_arduino, t_harp, verbose=False, return_offset=False):
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
        
    if return_offset == True:
        return t_arduino, t_harp, offset
    else:
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
    try:
        cLR.fit(x[:, np.newaxis], y)
        y_fit = expit(x_fit * cLR.coef_ + cLR.intercept_).flatten()
    except ValueError:
        y_fit = sp.zeros(x_fit.shape)
        y_fit[:] = sp.nan

    return y_fit

def tolerant_mean(arrs):
    'A mean that is tolerant to different sized arrays'

    max_length = np.max([arr.shape[0] for arr in arrs]) # get largest array

    # suggestion
    # A = np.zeros((len(arrs),max_length))
    # A[:] = np.NaN
    # for i, arr in enumerate(arrs):
    #     A[:arr.shape[0],i] = arr
    # return np.nanmean(A,axis=0)

    arrs=[np.pad(arr, (0, max_length-arr.shape[0]), mode='constant', constant_values=np.nan) for arr in arrs] # pad every array until max_length to obtain square matrix

    return np.nanmean(arrs, axis = 0)

