from matplotlib import pyplot as plt
import matplotlib as mpl

import behavior_analysis_utils as bhv
import pandas as pd
import numpy as np
# this should be changed ... 
from pathlib import Path
import scipy as sp
import seaborn as sns
from tqdm import tqdm
import os


"""
 
 ########  ########    ###    ########  
 ##     ## ##         ## ##   ##     ## 
 ##     ## ##        ##   ##  ##     ## 
 ########  ######   ##     ## ##     ## 
 ##   ##   ##       ######### ##     ## 
 ##    ##  ##       ##     ## ##     ## 
 ##     ## ######## ##     ## ########  
 
"""

animal_path = Path("C:/Users/Casa/Desktop/Paco/Champalimaud/behavior_data/JP9999/")
task_name = 'lick_for_reward_w_surpression'

LogDfs, CodesDf = bhv.aggregate_session_logs(animal_path, task_name)

span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

SpansDicts = []
EventsDicts = []

for Df in LogDfs:
    SpansDicts.append(bhv.get_spans(Df, span_names))
    EventsDicts.append(bhv.get_events(Df, event_names))

"""
 
 ########  ########  ######## ########  ########   #######   ######   ########  ######   ######  
 ##     ## ##     ## ##       ##     ## ##     ## ##     ## ##    ##  ##       ##    ## ##    ## 
 ##     ## ##     ## ##       ##     ## ##     ## ##     ## ##        ##       ##       ##       
 ########  ########  ######   ########  ########  ##     ## ##        ######    ######   ######  
 ##        ##   ##   ##       ##        ##   ##   ##     ## ##        ##             ##       ## 
 ##        ##    ##  ##       ##        ##    ##  ##     ## ##    ##  ##       ##    ## ##    ## 
 ##        ##     ## ######## ##        ##     ##  #######   ######   ########  ######   ######  
 
"""

# filter unrealistic licks
i = 0

for SpansDict in SpansDicts:

    bad_licks = np.logical_or(SpansDict['LICK']['dt'] < 20,SpansDict['LICK']['dt'] > 100)
    SpansDict['LICK'] = SpansDict['LICK'].loc[~bad_licks]

    # add lick_event
    Lick_Event = pd.DataFrame(np.stack([['NA']*SpansDict['LICK'].shape[0],SpansDict['LICK']['t_on'].values,['LICK_EVENT']*SpansDict['LICK'].shape[0]]).T,columns=['code','t','name'])
    Lick_Event['t'] = Lick_Event['t'].astype('float')
    LogDfs[i] = LogDfs[i].append(Lick_Event)
    LogDfs[i].sort_values('t')

    #event_names.append("LICK")
    #EventsDicts['LICK'] = bhv.get_events_from_name(LogDfs[i],'LICK')

    SpansDict.pop("LICK")
    #span_names.remove("LICK")

    i += 1

"""
 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
       ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""

# Make SessionDfs - slice into trials
Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

SessionDfs = []

for LogDf in LogDfs:
    TrialSpans = bhv.get_spans_from_event_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

    TrialDfs = []
    for i, row in TrialSpans.iterrows():
        ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
        ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
        TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

    SessionDfs.append(bhv.parse_trials(TrialDfs, Metrics))

# Transform SessionDfs into PerformanceDf

MetaMetrics = (bhv.collected_rate, bhv.mean_rt)

bhv.parse_sessions(SessionDfs, MetaMetrics)
                                   