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

def parse_lines(lines, code_map=None):
    """ parses a list of lines from arduino into a pd.DataFrame """
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
    """
    unused? 
    returns a list of DataFrames """    
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

def is_successful(TrialDf):
    if "TRIAL_COMPLETED_EVENT" in TrialDf['name'].values:
        succ = True
    else:
        succ = False    
    return pd.Series(succ,name='successful')

def reward_collected(TrialDf):
    if is_successful(TrialDf).values[0]:
        if "REWARD_COLLECTED_EVENT" in TrialDf['name'].values:
            rew_col = True
        else:
            rew_col = False
    else:
        rew_col = sp.NaN
    return pd.Series(rew_col, name='reward_collected')

def reward_collection_RT(TrialDf):
    if is_successful(TrialDf).values[0] == False or reward_collected(TrialDf).values[0] == False:
        rew_col_rt = sp.NaN
    else:
        t_rew_col = TrialDf.groupby('name').get_group("REWARD_COLLECTED_EVENT").iloc[-1]['t']
        t_rew_avail = TrialDf.groupby('name').get_group("REWARD_AVAILABLE_EVENT").iloc[-1]['t']
        rew_col_rt = t_rew_col - t_rew_avail
    return pd.Series(rew_col_rt,name='rew_col_rt')

def parse_trial(TrialDf, Metrics):
    """
    TrialDf is a list of all events in a trial
    first event should be trial available

    this should return a series for easy concatenation
    does not know about trial number
    
    CAREFUL as this function is called online

    this function will be extended with trial specific metrics
    
    Metrics is a list of callables, each Metrics takes TrialDf as
    an argument and returns a tuple (name, value)
    """
    try:
        # entry event
        t = TrialDf.groupby('name').get_group('TRIAL_AVAILABLE_STATE').iloc[0]['t']
    except KeyError:
        # if TrialDf has no entry event - this happens online before first trial
        return None

    MetricsDf = pd.DataFrame([Metric(TrialDf) for Metric in Metrics]).T
    MetricsDf['t'] = t

    return MetricsDf
    
def parse_trials(Dfs, Metrics):
    """ helper: because parse_trial is used also by online 
    plotting routines, this function only needed offline """
    SessionDf = pd.concat([parse_trial(Df, Metrics) for Df in Dfs],axis=0)
    SessionDf = SessionDf.reset_index(drop=True)
    return SessionDf

def log2Spans(Data,span_names):
    """ helper to run log2span on multiple span names """
    Spans = {}
    
    for span_name in span_names:
        on_name = span_name + '_ON'
        off_name = span_name + '_OFF'
        Spans[span_name] = spans_from_events(Data, on_name, off_name)
    return Spans

def spans_from_events(Data, on_name, off_name):
    """
    like log2span although with arbitrary events
    this function takes care of above problems actually
    """
    try:
        ons = Data.groupby('name').get_group(on_name)
        offs = Data.groupby('name').get_group(off_name)
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

    Span = pd.DataFrame(ts,columns=['t_on','t_off'])
    Span['dt'] = Span['t_off'] - Span['t_on']
    return Span

def log2Event(Data,event_name):
    """ extracts event times from parsed log """
    try:
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

def time_slice(Df, t_min, t_max, col='t'):
    """ helper to slice a dataframe along time (defined by col)"""
    vals = Df[col].values
    binds = sp.logical_and(vals > t_min, vals < t_max)
    return Df.loc[binds]

