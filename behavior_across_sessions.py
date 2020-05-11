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

animal_path = Path("C:/Users/Casa/Desktop/Paco/Champalimaud/behavior_data/JP2079/")
task_name = 'lick_for_reward_w_surpression'

LogDfs, CodesDf = bhv.aggregate_session_logs(animal_path, task_name)

span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

for Df in LogDfs:
    SpansDict = bhv.get_spans(LogDfs[Df], span_names)
    EventsDict = bhv.get_events(LogDfs[Df], event_names)

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
bad_licks = np.logical_or(SpansDict['LICK']['dt'] < 20,SpansDict['LICK']['dt'] > 100)
SpansDict['LICK'] = SpansDict['LICK'].loc[~bad_licks]

# add lick_event
Lick_Event = pd.DataFrame(np.stack([['NA']*SpansDict['LICK'].shape[0],SpansDict['LICK']['t_on'].values,['LICK_EVENT']*SpansDict['LICK'].shape[0]]).T,columns=['code','t','name'])
Lick_Event['t'] = Lick_Event['t'].astype('float')
LogDf = LogDf.append(Lick_Event)
LogDf.sort_values('t')

event_names.append("LICK")
EventsDict['LICK'] = bhv.get_events_from_name(LogDf,'LICK')

SpansDict.pop("LICK")
span_names.remove("LICK")

"""

    SESSIONS
                                                  
"""

# Make SessionDfs - slice into trials
Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

TrialSpans = bhv.get_spans_from_event_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

TrialDfs = []
for i, row in TrialSpans.iterrows():
    ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
    ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
    TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

SessionDf = bhv.parse_trials(TrialDfs, Metrics)

# Transform SessionDfs into PerformanceDf

 
                                   