from matplotlib import pyplot as plt
import matplotlib as mpl

import behavior_plotters as bhv_plt
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

# with open('params.txt','r') as fH:
#     lines = fH.readlines()

# path = lines[0] # path is in the first line

#animal_path = Path(path)

animal_folder = Path("D:/TaskControl/Animals/JJP-00885")
task_name = 'learn_to_push_alternating'

LogDfs = bhv.aggregate_session_logs(animal_folder, task_name)

# preprocess
LogDfs = [bhv.filter_bad_licks(LogDf) for LogDf in LogDfs]

axes = bhv_plt.plot_sessions_overview(LogDfs, task_name)
plt.show()

# %%
"""
 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
       ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""

# Define metrics to be applied on the individual trials
TrialsMetrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

SessionDfs = []

# Make SessionDfs
for LogDf in LogDfs:
    TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

    TrialDfs = []
    for i, row in TrialSpans.iterrows():
        ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
        ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
        TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

    SessionDfs.append(bhv.parse_trials(TrialDfs, TrialsMetrics))

# define the metrics to be applied on the Sessions
SessionMetrics = (bhv.rewards_collected, bhv.mean_reward_collection_rt)

bhv.parse_sessions(SessionDfs, SessionMetrics)
                                   