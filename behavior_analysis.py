# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

from matplotlib import pyplot as plt
import matplotlib as mpl
mpl.rcParams['figure.dpi'] = 331
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import seaborn as sns
from tqdm import tqdm
import os
from behavior_plotters import *

# %%
"""
 
 ########  ########    ###    ########  
 ##     ## ##         ## ##   ##     ## 
 ##     ## ##        ##   ##  ##     ## 
 ########  ######   ##     ## ##     ## 
 ##   ##   ##       ######### ##     ## 
 ##    ##  ##       ##     ## ##     ## 
 ##     ## ######## ##     ## ########  
 
"""

# path to arduino_log.txt
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-24_11-31-03_lick_for_reward_w_surpression/arduino_log.txt")
log_path = Path("/home/georg/data/Animals_new/JP2079/2020-02-12_17-21-01_lick_for_reward_w_surpression/arduino_log.txt")

# infer
code_map_path = log_path.parent.joinpath("lick_for_reward_w_surpression","Arduino","src","event_codes.h")

### READ 
CodesDf = bhv.parse_code_map(code_map_path)
code_map = dict(zip(CodesDf['code'],CodesDf['name']))
LogDf = bhv.parse_arduino_log(log_path, code_map)

### COMMON
# the names of the things present in the log
span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

SpansDict = bhv.get_spans(LogDf, span_names)
EventsDict = bhv.get_events(LogDf, event_names)

# %%
"""
 
 ########  ########  ######## ########  ########   #######   ######  ########  ######   ######  
 ##     ## ##     ## ##       ##     ## ##     ## ##     ## ##    ## ##       ##    ## ##    ## 
 ##     ## ##     ## ##       ##     ## ##     ## ##     ## ##       ##       ##       ##       
 ########  ########  ######   ########  ########  ##     ## ##       ######    ######   ######  
 ##        ##   ##   ##       ##        ##   ##   ##     ## ##       ##             ##       ## 
 ##        ##    ##  ##       ##        ##    ##  ##     ## ##    ## ##       ##    ## ##    ## 
 ##        ##     ## ######## ##        ##     ##  #######   ######  ########  ######   ######  
 
"""
# filter unrealistic licks
bad_licks = sp.logical_or(SpansDict['LICK']['dt'] < 20,SpansDict['LICK']['dt'] > 100)
SpansDict['LICK'] = SpansDict['LICK'].loc[~bad_licks]

# add lick_event
Lick_Event = pd.DataFrame(sp.stack([['NA']*SpansDict['LICK'].shape[0],SpansDict['LICK']['t_on'].values,['LICK_EVENT']*SpansDict['LICK'].shape[0]]).T,columns=['code','t','name'])
Lick_Event['t'] = Lick_Event['t'].astype('float')
LogDf = LogDf.append(Lick_Event)
LogDf.sort_values('t')

event_names.append("LICK")
EventsDict['LICK'] = bhv.get_events_from_name(LogDf,'LICK')

SpansDict.pop("LICK")
span_names.remove("LICK")

# %%
"""
 
 ########  ##        #######  ######## ######## #### ##    ##  ######   
 ##     ## ##       ##     ##    ##       ##     ##  ###   ## ##    ##  
 ##     ## ##       ##     ##    ##       ##     ##  ####  ## ##        
 ########  ##       ##     ##    ##       ##     ##  ## ## ## ##   #### 
 ##        ##       ##     ##    ##       ##     ##  ##  #### ##    ##  
 ##        ##       ##     ##    ##       ##     ##  ##   ### ##    ##  
 ##        ########  #######     ##       ##    #### ##    ##  ######   
 
"""

# setup
colors = sns.color_palette('hls',n_colors=len(event_names)+len(span_names))[::-1]
cdict = dict(zip(event_names+span_names,colors))

plot_dir = log_path.parent.joinpath('plots')
os.makedirs(plot_dir,exist_ok=True)
os.chdir(plot_dir)

# %%
# big overview
print(LogDf.name.unique()) # for debug
data = LogDf.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
# data = LogDf.groupby('name').get_group('REWARD_AVAILABLE_EVENT')
data = data.sort_values('t')
data = data.reset_index()

t_ref = data['t'].values
pre, post = (-100,800)

fig, axes = plt.subplots(figsize=[7,9])
plot_session_overview(LogDf, t_ref, pre, post, axes, how='dots', cdict=cdict)
fig.tight_layout()
# fig.savefig()

# %%
# with Lick plot_psth below
data = LogDf.groupby('name').get_group('TRIAL_ENTRY_EVENT')
# data = LogDf.groupby('name').get_group(g) for g in ['TRIAL_COMPLETED_EVENT','TRIAL_ABORTED_EVENT']
# data = LogDf.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
# data = LogDf.groupby('name').get_group('TRIAL_ABORTED_EVENT')
# data = LogDf.groupby('name').get_group('TRIAL_COMPLETED_EVENT')
# data = LogDf.groupby('name').get_group('REWARD_AVAILABLE_EVENT')
# data = LogDf.groupby('name').get_group('LICK_ON')
# data = data.iloc[20:420]
data = data.sort_values('t')
data = data.reset_index()
t_ref = data['t'].values
pre, post = (-100,200)

fig, axes = plt.subplots(nrows=2,sharex=True,figsize=[7,9])

plot_session_overview(LogDf,t_ref,pre,post,axes[0],how='dots',cdict=cdict)
plot_psth(t_ref, EventsDict['LICK'], pre, post, bin_width=20, axes=axes[1])
fig.tight_layout()

# %% metrics on trials
Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

# make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_event_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

TrialDfs = []
for i, row in TrialSpans.iterrows():
    ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
    ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
    TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

SessionDf = bhv.parse_trials(TrialDfs, Metrics)

### plot recent success rate
# %%
fig, axes = plt.subplots()
fig.suptitle('successful trials')
x = SessionDf.index
y = [sum(SessionDf.iloc[:i]['successful'])/(i+1) for i in range(SessionDf.shape[0])]
axes.plot(x,y,lw=2,label='total',alpha=0.8,color="black")
hist = 25
y = [sum(SessionDf.iloc[i-hist:i]['successful'])/hist for i in range(SessionDf.shape[0])]
axes.plot(x,y,lw=2,label='last 25')
axes.set_xlabel('trials')
axes.set_ylabel('fraction successful',alpha=0.8)




# %%
