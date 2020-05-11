import scipy as sp
import pandas as pd
from pathlib import Path
from functions import parse_code_map
import utils

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
    if sp.any(sp.diff(LogDf['t']) < 0):
        reversal_ind = sp.where(sp.diff(LogDf['t']) < 0)[0][0]
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
    try:
        # entry event
        t = TrialDf.groupby('name').get_group('TRIAL_AVAILABLE_STATE').iloc[0]['t']
    except KeyError:
        # if TrialDf has no entry event - this happens online before first trial
        return None

    MetricsDf = pd.DataFrame([Metric(TrialDf) for Metric in Metrics]).T
    MetricsDf['t'] = t

    return MetricsDf
    
def parse_trials(TrialDfs, Metrics):
    """ helper to run parse_trial on multiple trials.
    TrialsDfs is a list of TrialDf """
    SessionDf = pd.concat([parse_trial(Df, Metrics) for Df in TrialDfs],axis=0)
    SessionDf = SessionDf.reset_index(drop=True)
  
    return SessionDf
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
    binds = sp.logical_and(vals > t_min, vals < t_max)
  
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


def is_successful(TrialDf):
    if "TRIAL_COMPLETED_EVENT" in TrialDf['name'].values:
        succ = True
    else:
        succ = False    
 
    return pd.Series(succ, name='successful')

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
 
    return pd.Series(rew_col_rt, name='rew_col_rt')