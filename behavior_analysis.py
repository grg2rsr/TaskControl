# %%
#matplotlib qt5
#load_ext autoreload
#autoreload 2

from matplotlib import pyplot as plt
import matplotlib as mpl
mpl.rcParams['figure.dpi'] = 331
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
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

# %% Get log filepath
from tkinter import Tk
from tkinter import filedialog
root = Tk()         # create the Tkinter widget
root.withdraw()     # hide the Tkinter root window

# Windows specific; forces the window to appear in front
root.attributes("-topmost", True)

log_path = Path(filedialog.askopenfilename(initialdir="D:/TaskControl/Animals",title="Select log file"))

root.destroy()

# %%

# infer
task_name = '_'.join(log_path.parent.name.split('_')[2:])
code_map_path = log_path.parent.joinpath(task_name,"Arduino","src","event_codes.h")

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

# %% Trials Overview - with Lick psth
data = LogDf.groupby('name').get_group('CHOICE_INCORRECT_EVENT')
# data = LogDf.groupby('name').get_group(g) for g in ['TRIAL_COMPLETED_EVENT','TRIAL_ABORTED_EVENT']
data = data.sort_values('t')
data = data.reset_index()
t_ref = data['t'].values
pre, post = (-100,2000)

kw = dict(height_ratios=[1,0.5])

fig, axes = plt.subplots(nrows=2,sharex=True,figsize=[4.25,5.5], gridspec_kw=kw)

plot_session_overview(LogDf, t_ref, pre, post, axes=axes[0], how='dots', cdict=cdict)

bin_width = 25
bins = np.arange(pre,post,bin_width)
plot_psth(EventsDict['LICK'], t_ref, bins=bins, axes=axes[1])
fig.tight_layout()

 # %% Session metrics 
Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

# make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_event_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

TrialDfs = []
for i, row in TrialSpans.iterrows():
    ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
    ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
    TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

SessionDf = bhv.parse_trials(TrialDfs, Metrics)

hist = 20
fig, axes = plt.subplots(ncols=3,figsize=[8,2.25])
plot_success_rate(SessionDf, history=hist, axes=axes[0])
plot_reward_collection_rate(SessionDf, history=hist, axes=axes[1])
plot_reward_collection_RT(SessionDf, axes=axes[2])
fig.tight_layout()

# %% psychometric
TrialDfs = []
for i, row in TrialSpans.iterrows():
    TrialDfs.append(bhv.time_slice(LogDf,row['t_on'],row['t_off']))

# %%
with open(log_path,'r') as fH:
    lines = fH.readlines()

lines = [line.strip() for line in lines]
msgs = []
var_msgs = []
for line in lines:
    if line.startswith('<MSG'):
        msgs.append(line)
    if line.startswith('<VAR'):
        var_msgs.append(line)
# %% diagnostic plot
# fig, axes = plt.subplots(nrows=2,sharex=True)
# pre = -100
# post = 200
# bins = sp.arange(pre,post,10)
# for b in bins:
#     for ax in axes:
#         ax.axvline(b,alpha=0.5)
# plot_raster(EventsDict['LICK'], t_ref, pre, post, axes=axes[0])
# plot_psth(EventsDict['LICK'], t_ref, bins=bins, axes=axes[1])
