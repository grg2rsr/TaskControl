# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
import utils

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

# %%
log_path = utils.get_file_dialog()

# %%

# infer
task_name = '_'.join(log_path.parent.name.split('_')[2:])
code_map_path = log_path.parent.joinpath(task_name,"Arduino","src","event_codes.h")

### READ 
CodesDf = utils.parse_code_map(code_map_path)
code_map = dict(zip(CodesDf['code'],CodesDf['name']))
LogDf = bhv.parse_arduino_log(log_path, code_map)

### COMMON
# the names of the things present in the log
span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name for name in CodesDf['name'] if name.endswith('_EVENT')]

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

event_names.append("LICK_EVENT")
EventsDict['LICK_EVENT'] = bhv.get_events_from_name(LogDf,'LICK_EVENT')

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
# data = LogDf.groupby('name').get_group('CHOICE_EVENT')
# # data = LogDf.groupby('name').get_group(g) for g in ['TRIAL_COMPLETED_EVENT','TRIAL_ABORTED_EVENT']
# data = data.sort_values('t')
# data = data.reset_index()
# t_ref = data['t'].values
# pre, post = (-100,2000)

# kw = dict(height_ratios=[1,0.5])

# fig, axes = plt.subplots(nrows=2,sharex=True,figsize=[4.25,5.5], gridspec_kw=kw)
# plot_session_overview(LogDf, t_ref, pre, post, axes=axes[0], how='dots', cdict=cdict)

# bin_width = 25
# bins = np.arange(pre,post,bin_width)
# plot_psth(EventsDict['LICK_EVENT'], t_ref, bins=bins, axes=axes[1])
# fig.tight_layout()

#  # %% Session metrics 
# Metrics = (bhv.is_successful, bhv.reward_collected, bhv.reward_collection_RT)

# # make SessionDf - slice into trials
# TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

# TrialDfs = []
# for i, row in TrialSpans.iterrows():
#     ind_start = LogDf.loc[LogDf['t'] == row['t_on']].index[0]
#     ind_stop = LogDf.loc[LogDf['t'] == row['t_off']].index[0]
#     TrialDfs.append(LogDf.iloc[ind_start:ind_stop+1])

# SessionDf = bhv.parse_trials(TrialDfs, Metrics)

# hist = 20
# fig, axes = plt.subplots(ncols=3,figsize=[8,2.25])
# plot_success_rate(SessionDf, history=hist, axes=axes[0])
# plot_reward_collection_rate(SessionDf, history=hist, axes=axes[1])
# # plot_reward_collection_RT(SessionDf, axes=axes[2])
# fig.tight_layout()

# %% debugging syncing problems
folder = Path("D:\TaskControl\Animals\JJP-00885")
task_name = "learn_to_time"

bhv.create_LogDf_LCDf_csv(folder, task_name)

# %%

path = Path(r"D:\TaskControl\Animals\JJP-00885\2020-07-07_09-58-56_learn_to_time")
log_path = path / "arduino_log.txt"

# %% syncing

LoadCellDf, harp_sync = bhv.parse_harp_csv(log_path.parent / "bonsai_harp_log.csv", save=True)
arduino_sync = bhv.get_arduino_sync(log_path)

# %%
t_harp = harp_sync['t'].values
t_arduino = arduino_sync['t'].values

# %%
plt.plot(sp.diff(t_harp),label='harp')
plt.plot(sp.diff(t_arduino),label='arduino')
plt.legend()


# %%
t_harp = pd.read_csv(log_path.parent / "harp_sync.csv")['t'].values
t_arduino = pd.read_csv(log_path.parent / "arduino_sync.csv")['t'].values

m,b = bhv.sync_clocks(t_harp, t_arduino, log_path)
LogDf = pd.read_csv(log_path.parent / "LogDf.csv")

# %% psychometric
# make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

TrialDfs = []
for i, row in TrialSpans.iterrows():
    TrialDfs.append(bhv.time_slice(LogDf,row['t_on'],row['t_off']))


# %% psychmetrics restart

# make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

TrialDfs = []
for i, row in tqdm(TrialSpans.iterrows()):
    TrialDfs.append(bhv.time_slice(LogDf,row['t_on'],row['t_off']))

SessionDf = bhv.parse_trials(TrialDfs, (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.get_interval))

# %%
SDf = SessionDf.groupby('has_choice').get_group(True)

y = SDf['choice'].values == 'right'
x = SDf['this_interval'].values

fig, axes = plt.subplots(figsize=[6,2])
axes.plot(x,y,'.',color='k',alpha=0.5)
axes.set_yticks([0,1])
axes.set_yticklabels(['short','long'])
axes.set_ylabel('choice')
axes.axvline(1500,linestyle=':',alpha=0.5,lw=1,color='k')

# adding logistic regression fit
from sklearn.linear_model import LogisticRegression
from scipy.special import expit
cLR = LogisticRegression()
SessionDf = SessionDf.dropna()
cLR.fit(x[:,sp.newaxis],y)

x_fit = sp.linspace(0,3000,100)
psychometric = expit(x_fit * cLR.coef_ + cLR.intercept_).flatten()
plt.plot(x_fit, psychometric, color='red', linewidth=2,alpha=0.75)

# %% histograms
fig,axes = plt.subplots()
shorts = SDf.groupby('choice').get_group('left')['this_interval'].values
longs = SDf.groupby('choice').get_group('right')['this_interval'].values
kwargs = dict(alpha=.5, density=True, bins=sp.linspace(0,3000,15))
axes.hist(shorts, **kwargs, label='short')
axes.hist(longs, **kwargs, label='long')
plt.legend()
axes.set_xlabel('interval (ms)')
axes.set_ylabel('density')

