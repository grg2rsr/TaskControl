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
Data = bhv.parse_arduino_log(log_path, code_map)

### COMMON
# the names of the things present in the log
span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

Spans = bhv.log2Spans(Data, span_names)
Events = bhv.log2Events(Data, event_names)

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
### SOME PREPROCESSING
# filter unrealistic licks
bad_licks = sp.logical_or(Spans['LICK']['dt'] < 20,Spans['LICK']['dt'] > 100)
Spans['LICK'] = Spans['LICK'].loc[~bad_licks]

# add lick_event
Lick_Event = pd.DataFrame(sp.stack([['NA']*Spans['LICK'].shape[0],Spans['LICK']['t_on'].values,['LICK_EVENT']*Spans['LICK'].shape[0]]).T,columns=['code','t','name'])
Lick_Event['t'] = Lick_Event['t'].astype('float')
Data = Data.append(Lick_Event)
Data.sort_values('t')

event_names.append("LICK")
Events['LICK'] = bhv.log2Event(Data,'LICK')

Spans.pop("LICK")
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
Data.name.unique() # ?
data = Data.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
# data = Data.groupby('name').get_group('REWARD_AVAILABLE_EVENT')
data = data.sort_values('t')
data = data.reset_index()

t_ref = data['t'].values
pre, post = (-100,800)

fig, axes = plt.subplots(figsize=[7,9])
plot_session_overview(Data,t_ref,pre,post,axes,how='dots',cdict=cdict)
fig.tight_layout()
# fig.savefig()

# %%
# with Lick plot_psth below
data = Data.groupby('name').get_group('TRIAL_ENTRY_EVENT')
# data = Data.groupby('name').get_group(g) for g in ['TRIAL_COMPLETED_EVENT','TRIAL_ABORTED_EVENT']
# data = Data.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
# data = Data.groupby('name').get_group('TRIAL_ABORTED_EVENT')
# data = Data.groupby('name').get_group('TRIAL_COMPLETED_EVENT')
# data = Data.groupby('name').get_group('REWARD_AVAILABLE_EVENT')
# data = Data.groupby('name').get_group('LICK_ON')
# data = data.iloc[20:420]
data = data.sort_values('t')
data = data.reset_index()
t_ref = data['t'].values
pre, post = (-100,200)

fig, axes = plt.subplots(nrows=2,sharex=True,figsize=[7,9])

plot_session_overview(Data,t_ref,pre,post,axes[0],how='dots',cdict=cdict)
plot_psth(t_ref, Events['LICK'], pre, post, bin_width=20, axes=axes[1])
fig.tight_layout()

# %% metrics on trials

# make SessionDf
completed = bhv.log2Span2(Data,"TRIAL_AVAILABLE_STATE","ITI_STATE")
#aborted = log2Span2(Data,"TRIAL_ENTRY_EVENT","TRIAL_ABORTED_EVENT")
#all 

Dfs = []
for i, row in completed.iterrows():
    ind_start = Data.loc[Data['t'] == row['t_on']].index[0]
    ind_stop = Data.loc[Data['t'] == row['t_off']].index[0]
    Dfs.append(Data.iloc[ind_start:ind_stop+1])

SessionDf = bhv.parse_trials(Dfs)

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
