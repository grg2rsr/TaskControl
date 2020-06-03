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

"""
 
 ########  ########    ###    ########  
 ##     ## ##         ## ##   ##     ## 
 ##     ## ##        ##   ##  ##     ## 
 ########  ######   ##     ## ##     ## 
 ##   ##   ##       ######### ##     ## 
 ##    ##  ##       ##     ## ##     ## 
 ##     ## ######## ##     ## ########  
 
"""

with open('params.txt','r') as fH:
    lines = fH.readlines()

# path = lines[0] # path is in the first line

animal_path = Path(path)

animal_folder = Path("/home/georg/data/Animals/JP2079")
task_name = 'lick_for_reward_w_surpression'

LogDfs = bhv.aggregate_session_logs(animal_folder, task_name)

# preprocess
LogDfs = [bhv.filter_bad_licks(LogDf) for LogDf in LogDfs]

# # currently unused?
# SpansDicts = []
# EventsDicts = []

# for LogDf in LogDfs:
#     names = LogDf['name'].unique()
#     span_names = list(set([name.split('_ON')[0] for name in names if name.endswith('_ON')]))
#     event_names = list(set([name.split('_EVENT')[0] for name in names if name.endswith('_EVENT')]))

#     SpansDicts.append(bhv.get_spans(Df, span_names))
#     EventsDicts.append(bhv.get_events(Df, event_names))


"""
 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
       ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""

# Define metrics to be applied
TrialsMetrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

SessionDfs = []

# Make SessionDfs
for LogDf in LogDfs:
    TrialSpans = bhv.get_spans_from_event_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

    TrialDfs = []
    for i, row in TrialSpans.iterrows():
        ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
        ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
        TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

    SessionDfs.append(bhv.parse_trials(TrialDfs, TrialsMetrics))

# Transform SessionDfs into PerformanceDf - single Df with behavioral summary statistics

MetaMetrics = (bhv.collected_rate, bhv.mean_rt)

bhv.parse_sessions(SessionDfs, MetaMetrics)
                                   