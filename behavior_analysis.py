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

# %% path setup
log_path = utils.get_file_dialog()
plot_dir = log_path.parent / 'plots'
os.makedirs(plot_dir, exist_ok=True)

# %% across sessino - plot weight
SessionsDf = utils.get_sessions(log_path.parent.parent)
Df = pd.read_csv(log_path.parent.parent / 'animal_meta.csv')
ini_weight = float(Df[Df['name'] == 'Weight']['value'])
for i,row in SessionsDf.iterrows():
    try:
        path = row['path']
        Df = pd.read_csv(Path(path) / 'animal_meta.csv')
        current_weight = float(Df[Df['name'] == 'current_weight']['value'])
        SessionsDf.loc[row.name,'weight'] = current_weight
        SessionsDf.loc[row.name,'weight_frac'] = current_weight / ini_weight
    except:
        pass

# %%
fig, axes = plt.subplots()
axes.plot(SessionsDf.index.values,SessionsDf.weight_frac,'o')
axes.set_xticks(SessionsDf.index.values)
axes.set_xticklabels(SessionsDf['date'].values,rotation=90)
line_kwargs = dict(lw=1,linestyle=':',alpha=0.75,color='k')
# axes.axhline(0.75,**line_kwargs)
axes.axhline(0.85,**line_kwargs)
axes.set_ylim(0.5,1)
axes.set_title('weight')
axes.set_xlabel('session date')
axes.set_ylabel('weight %')
sns.despine(fig)
fig.tight_layout()

# %% preprocess 
LogDf = bhv.get_LogDf_from_path(log_path)
LogDf = bhv.filter_bad_licks(LogDf)


"""
##       ########    ###    ########  ##    ##    ########  #######     ##       ####  ######  ##    ##
##       ##         ## ##   ##     ## ###   ##       ##    ##     ##    ##        ##  ##    ## ##   ##
##       ##        ##   ##  ##     ## ####  ##       ##    ##     ##    ##        ##  ##       ##  ##
##       ######   ##     ## ########  ## ## ##       ##    ##     ##    ##        ##  ##       #####
##       ##       ######### ##   ##   ##  ####       ##    ##     ##    ##        ##  ##       ##  ##
##       ##       ##     ## ##    ##  ##   ###       ##    ##     ##    ##        ##  ##    ## ##   ##
######## ######## ##     ## ##     ## ##    ##       ##     #######     ######## ####  ######  ##    ##
"""

# %% rename events of all future omitted rewards
EventsDf = bhv.get_events_from_name(LogDf, 'REWARD_OMITTED_EVENT')
for t in EventsDf['t'].values:
    Df = bhv.time_slice(LogDf, t-1000, t)
    ix = Df[Df['name'] == 'REWARD_AVAILABLE_EVENT'].index
    LogDf.loc[ix, 'name'] = "OMITTED_REWARD_AVAILABLE_EVENT"

# note for the future - mind this distinction! If response to both is wanted, use REWARD_AVAILABLE_STATE

# %% learn to lick inspections
pre, post = -2000, 4000
fig, axes = plt.subplots(nrows=3, figsize=[3, 5], sharey=True, sharex=True)

events = ['REWARD_AVAILABLE_EVENT', 'OMITTED_REWARD_AVAILABLE_EVENT', 'NO_REWARD_AVAILABLE_EVENT']
LicksDf = bhv.get_events_from_name(LogDf, 'LICK_EVENT')
for event, ax in zip(events, axes):
    times = bhv.get_events_from_name(LogDf, event)['t'] # task event times
    try:
        plot_psth(LicksDf, times, bins=sp.linspace(pre, post, 50), axes=ax, density=True) # Density with time on ms screws up everything
    except:
        continue
    ax.set_title(event, fontsize='x-small')
    ax.axvline(0, linestyle=':', lw=1, alpha=0.5, color='k')

sns.despine(fig)
fig.suptitle('lick psth to cues')
fig.tight_layout()
plt.savefig(plot_dir / 'lick_to_cues_psth.png', dpi=300)

# %% Reaction times - first lick to cue
pre, post = -2000, 4000

fig, axes = plt.subplots(nrows=3, figsize=[3, 5], sharey=True, sharex=True)

events = ['REWARD_AVAILABLE_EVENT', 'OMITTED_REWARD_AVAILABLE_EVENT', 'NO_REWARD_AVAILABLE_EVENT']
LicksDf = bhv.get_events_from_name(LogDf, 'LICK_EVENT')

bins=sp.linspace(0, 500, 25)

for event, ax in zip(events,axes):
    times = bhv.get_events_from_name(LogDf, event)['t']
    # find next lick after time t
    rts = []
    for t in times:
        ix = sp.argmax(LicksDf['t'] > t) # index of next lick

        if ix < len(LicksDf):
            t_next_lick = LicksDf.iloc[ix]['t']
        else: 
            t_next_lick = LicksDf.loc[ix]['t']
        rt = t_next_lick - t
        rts.append(rt)

    # data
    ax.hist(rts, bins=bins, label='data', alpha=0.5, density=True)

    # random model
    ax.hist(sp.diff(LicksDf['t'].values), bins=bins, alpha=0.5, color='gray', density=True, label='random', zorder=-10)

    ax.set_xlabel('rt (ms)')
    ax.set_ylabel('normed count')
    ax.set_title(event, fontsize='small')

axes[0].legend(fontsize='x-small')
sns.despine(fig)
fig.suptitle('reaction times to auditory cues')
fig.tight_layout()


"""
##       ########    ###    ########  ##    ##    ########  #######     ########  ##     ##  ######  ##     ##
##       ##         ## ##   ##     ## ###   ##       ##    ##     ##    ##     ## ##     ## ##    ## ##     ##
##       ##        ##   ##  ##     ## ####  ##       ##    ##     ##    ##     ## ##     ## ##       ##     ##
##       ######   ##     ## ########  ## ## ##       ##    ##     ##    ########  ##     ##  ######  #########
##       ##       ######### ##   ##   ##  ####       ##    ##     ##    ##        ##     ##       ## ##     ##
##       ##       ##     ## ##    ##  ##   ###       ##    ##     ##    ##        ##     ## ##    ## ##     ##
######## ######## ##     ## ##     ## ##    ##       ##     #######     ##         #######   ######  ##     ##
"""

# %% preprocessing: LC syncing
LoadCellDf, harp_sync = bhv.parse_harp_csv(log_path.parent / "bonsai_harp_log.csv", save=True)
arduino_sync = bhv.get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT")

t_harp = pd.read_csv(log_path.parent / "harp_sync.csv")['t'].values
t_arduino = pd.read_csv(log_path.parent / "arduino_sync.csv")['t'].values

if t_harp.shape != t_arduino.shape:
    t_arduino, t_harp = bhv.cut_timestamps(t_arduino, t_harp, verbose = True)

m, b = bhv.sync_clocks(t_harp, t_arduino, log_path)
LogDf = pd.read_csv(log_path.parent / "LogDf.csv")


# %% median correction
samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).median()
LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).median()

# %% cut LogDf to same data len in case (for example bc of bonsai crashes)
LogDf = LogDf.loc[LogDf['t'] < LoadCellDf.iloc[-1]['t']]

# %% make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

TrialDfs = []
for i, row in tqdm(TrialSpans.iterrows()):
    TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

metrics = (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.choice_RT, bhv.is_successful, bhv.get_outcome)
SessionDf = bhv.parse_trials(TrialDfs, metrics)

# %% choice / outcome grid for LC forces
sides = ['left', 'right']
outcomes = ['correct', 'incorrect']
fig, axes = plt.subplots(nrows=len(outcomes), ncols=len(sides), figsize=[5, 5], sharex=True, sharey=True)

pre, post = -1000, 10
align_event = "CHOICE_EVENT"

for i, side in enumerate(sides):
    for j, outcome in enumerate(outcomes):
        try:
            SDf = SessionDf.groupby(['choice', 'outcome']).get_group((side, outcome))
        except:
            continue

        ax = axes[j, i]
        Fx = []
        Fy = []
        for _, row in tqdm(SDf.iterrows()):
            TrialDf = TrialDfs[row.name]
            t_align = TrialDf.loc[TrialDf['name'] == align_event, 't'].values[0]
            # identical to:
            # t_align = TrialDf.groupby('name').get_group(align_event)['t'].values
            LCDf = bhv.time_slice(LoadCellDf, t_align+pre, t_align+post)
            Fx.append(LCDf['x'].values)
            Fy.append(LCDf['y'].values)

        Fx = sp.array(Fx).T
        Fy = sp.array(Fy).T

        event_ix = Fx.shape[0] - post

        ## for trajectories
        for k in range(Fx.shape[1]):
            ax.plot(Fx[:, k], Fy[:, k], lw=0.5, alpha=0.5)
            ax.plot(Fx[event_ix, k], Fy[event_ix, k], 'o', markersize = 5, alpha=0.5)
     
        Fx_avg = sp.average(Fx, 1) 
        Fy_avg = sp.average(Fy, 1)

        ax.plot(Fx_avg, Fy_avg, lw=1, color='k', alpha=0.8)
        ax.plot(Fx_avg[event_ix], Fy_avg[event_ix], 'o', color='k', alpha=0.8, markersize=5)
       
        ax.set_xlim(-3000, 3000)
        ax.set_ylim(-3000, 3000)

        line_kwargs = dict(color='k', linestyle=':', alpha=0.5, zorder=-100)
        ax.axvline(0, **line_kwargs)
        ax.axhline(0, **line_kwargs)

        line_kwargs = dict(color='k', lw=0.5, linestyle='-', alpha=0.25, zorder=-100)
        ax.axvline(-2500, **line_kwargs)
        ax.axvline(+2500, **line_kwargs)
        ax.axhline(-1500, **line_kwargs)
        ax.axhline(+1500, **line_kwargs)

        # # for inspecting clean choices
        # tvec = sp.linspace(pre, post, Fx.shape[0])
        # for k in range(Fx.shape[1]):
        #     ax.plot(tvec, Fx[:, k], lw=0.5, alpha=0.5)
        #     ax.plot(tvec[event_ix], Fx[event_ix, k], 'o', markersize = 5, alpha=0.5)
        # ax.plot(tvec, sp.average(Fx, 1), lw=1, color='k', alpha=0.8)
        # ax.set_ylim(-2500, 2500)
        # ax.axvline(0, color='k', linestyle=':', alpha=0.5, lw=1, zorder=-1)

sns.despine(fig)
axes[0, 0].set_title('left')
axes[0, 1].set_title('right')
axes[0, 0].set_ylabel('correct')
axes[1, 0].set_ylabel('incorrect')
fig.tight_layout()

# %% heatmaps
pre, post = -1000, 1000
align_event = "GO_CUE_EVENT"

order = [['left','correct'],
         ['left','incorrect'],
         ['right','correct'],
         ['right','incorrect']]

height_ratios = SessionDf.groupby(['choice', 'outcome']).count()['t_on'][order].values

fig, axes = plt.subplots(nrows=len(order), ncols=2, figsize=[5, 5], sharex=True, gridspec_kw=dict(height_ratios=height_ratios))

for i, (side, outcome) in enumerate(order):
    try:
        SDf = SessionDf.groupby(['choice', 'outcome']).get_group((side, outcome))
    except:
        continue

    Fx = []
    Fy = []
    for _, row in tqdm(SDf.iterrows()):
        TrialDf = TrialDfs[row.name]
        t_align = TrialDf.loc[TrialDf['name'] == align_event, 't'].values[0]
        # identical to:
        # t_align = TrialDf.groupby('name').get_group(align_event)['t'].values
        LCDf = bhv.time_slice(LoadCellDf, t_align+pre, t_align+post)
        Fx.append(LCDf['x'].values)
        Fy.append(LCDf['y'].values)

    Fx = sp.array(Fx).T
    Fy = sp.array(Fy).T

    # event_ix = Fx.shape[0] - post

    ## for heatmaps
    axes[i,0].matshow(Fx.T, origin='lower', vmin=-2000, vmax=2000, cmap='PiYG')
    axes[i,1].matshow(Fy.T, origin='lower', vmin=-2000, vmax=2000, cmap='PiYG')

for ax in axes.flatten():
    ax.set_aspect('auto')

for ax in axes[-1,:]:
    ax.xaxis.set_ticks_position('bottom')

for ax, (side, outcome) in zip(axes[:,0],order):
    ax.set_ylabel('\n'.join([side,outcome]))

axes[0,0].set_title('Fx')
axes[0,1].set_title('Fy')

fig.tight_layout()
fig.subplots_adjust(hspace=0.05)


# %% bias over time
Df = LogDf[LogDf['var'] == 'bias']

fig, axes = plt.subplots()
values = Df['value']
times = Df['t'] / 1e3 
times = times - times.iloc[0]

axes.plot(times, values, label='grand')
axes.plot(times, Df['value'].rolling(10).mean(), label='last 10')
axes.axhline(0.5, color='k', linestyle=':', alpha=0.5, lw=1, zorder=-1)
axes.legend()
axes.set_ylim(0, 1)
axes.set_ylabel('bias')
axes.set_xlabel('time (s)')
axes.set_title('lateral bias')
sns.despine(fig)
fig.tight_layout()

# %% 

"""
##       ########    ###    ########  ##    ##    ########  #######     ######## #### ##     ##    ###    ######## ########
##       ##         ## ##   ##     ## ###   ##       ##    ##     ##    ##        ##   ##   ##    ## ##      ##    ##
##       ##        ##   ##  ##     ## ####  ##       ##    ##     ##    ##        ##    ## ##    ##   ##     ##    ##
##       ######   ##     ## ########  ## ## ##       ##    ##     ##    ######    ##     ###    ##     ##    ##    ######
##       ##       ######### ##   ##   ##  ####       ##    ##     ##    ##        ##    ## ##   #########    ##    ##
##       ##       ##     ## ##    ##  ##   ###       ##    ##     ##    ##        ##   ##   ##  ##     ##    ##    ##
######## ######## ##     ## ##     ## ##    ##       ##     #######     ##       #### ##     ## ##     ##    ##    ########
"""

"""
all the above plus
"""
# %% force aligned on cues

pre, post = -1000, 1000
events = ["FIRST_TIMING_CUE_EVENT", "SECOND_TIMING_CUE_EVENT"]
fig, axes = plt.subplots(ncols=len(events), sharex=True, sharey=True, figsize=[5, 4])

for event, ax in zip(events, axes):
    EventDf = bhv.get_events_from_name(LogDf, event)

    Fx = []
    Fy = []

    for t in tqdm(EventDf['t'].values):
        LCDf = bhv.time_slice(LoadCellDf, t+pre, t+post)
        Fx.append(LCDf['x'].values)
        Fy.append(LCDf['y'].values)

    Fx = sp.array(Fx).T
    Fy = sp.array(Fy).T

    M = sp.sqrt(Fx**2+Fy**2)
    # M = Fx

    tvec = sp.linspace(pre, post, Fx.shape[0])
    for i in range(Fx.shape[1]):
        ax.plot(tvec, M[:, i], lw=0.5, alpha=0.5)
    ax.plot(tvec, sp.average(M, 1), lw=1, color='k', alpha=0.5)
    ax.axvline(0, linestyle=':', lw=1, alpha=0.5, color='k')
    ax.set_title(event, fontsize='x-small')
    ax.set_xlabel('time (ms)')
    ax.set_ylabel('|F|')

sns.despine(fig)
fig.suptitle('|F| at cue time')
fig.tight_layout()

# %% forces between first timing cue and second (or premature)
fig, axes = plt.subplots(nrows=3, figsize=[5, 4])

# first all up until premature
SDf = SessionDf.groupby('outcome').get_group('premature')
inds = SDf.index

Fmags = []
for i in tqdm(inds):
    TrialDf = TrialDfs[i]
    t_start = TrialDf.loc[TrialDf['name'] == "FIRST_TIMING_CUE_EVENT",'t'].values[0]
    t_stop = TrialDf.loc[TrialDf['name'] == "PREMATURE_CHOICE_EVENT",'t'].values[0]
    LCDf = bhv.time_slice(LoadCellDf, t_start, t_stop)
    Fmag = sp.sqrt(LCDf['x']**2 + LCDf['y']**2)
    Fmags.append(Fmag)

for Fmag in Fmags:
    axes[0].plot(Fmag, lw=1, alpha=0.75)

# incorrect
SDf = SessionDf.groupby('outcome').get_group('incorrect')
inds = SDf.index

Fmags = []
for i in tqdm(inds):
    TrialDf = TrialDfs[i]
    t_start = TrialDf.loc[TrialDf['name'] == "FIRST_TIMING_CUE_EVENT",'t'].values[0]
    t_stop = TrialDf.loc[TrialDf['name'] == "SECOND_TIMING_CUE_EVENT",'t'].values[0]
    LCDf = bhv.time_slice(LoadCellDf, t_start, t_stop)
    Fmag = sp.sqrt(LCDf['x']**2 + LCDf['y']**2)
    Fmags.append(Fmag)

for Fmag in Fmags:
    axes[1].plot(Fmag, lw=1, alpha=0.75)

# correct
SDf = SessionDf.groupby('outcome').get_group('correct')
inds = SDf.index

Fmags = []
for i in tqdm(inds):
    TrialDf = TrialDfs[i]
    t_start = TrialDf.loc[TrialDf['name'] == "FIRST_TIMING_CUE_EVENT",'t'].values[0]
    t_stop = TrialDf.loc[TrialDf['name'] == "SECOND_TIMING_CUE_EVENT",'t'].values[0]
    LCDf = bhv.time_slice(LoadCellDf, t_start, t_stop)
    Fmag = sp.sqrt(LCDf['x']**2 + LCDf['y']**2)
    Fmags.append(Fmag)

for Fmag in Fmags:
    axes[2].plot(Fmag, lw=1, alpha=0.75)


axes[0].set_title('premature')
axes[1].set_title('incorrect')
axes[2].set_title('correct')

# axes[0].plot(bhv.tolerant_mean(Fmags),'k',lw=2,alpha=0.8)



sns.despine(fig)
fig.suptitle('forces after first timing cue')
fig.tight_layout()

# %%
"""
##       ########    ###    ########  ##    ##    ########  #######     ######## #### ##     ## ########
##       ##         ## ##   ##     ## ###   ##       ##    ##     ##       ##     ##  ###   ### ##
##       ##        ##   ##  ##     ## ####  ##       ##    ##     ##       ##     ##  #### #### ##
##       ######   ##     ## ########  ## ## ##       ##    ##     ##       ##     ##  ## ### ## ######
##       ##       ######### ##   ##   ##  ####       ##    ##     ##       ##     ##  ##     ## ##
##       ##       ##     ## ##    ##  ##   ###       ##    ##     ##       ##     ##  ##     ## ##
######## ######## ##     ## ##     ## ##    ##       ##     #######        ##    #### ##     ## ########
"""

"""
all of the above, and:
"""

# %%
# make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

TrialDfs = []
for i, row in tqdm(TrialSpans.iterrows()):
    TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

SessionDf = bhv.parse_trials(TrialDfs, (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.choice_RT, bhv.is_successful, bhv.get_outcome, bhv.get_interval))

# %% adding logistic regression fit
from sklearn.linear_model import LogisticRegression
from scipy.special import expit

# get only the subset with choices
SDf = SessionDf.groupby('has_choice').get_group(True)
y = SDf['choice'].values == 'right'
x = SDf['this_interval'].values

# plot choices
fig, axes = plt.subplots(figsize=[6, 2])
axes.plot(x, y, '.', color='k', alpha=0.5)
axes.set_yticks([0, 1])
axes.set_yticklabels(['short', 'long'])
axes.set_ylabel('choice')
axes.axvline(1500, linestyle=':', alpha=0.5, lw=1, color='k')

def log_reg(x, y, x_fit=None):
    """ x and y are of shape (N, ) y are choices in [0, 1] """
    if x_fit is None:
        x_fit = sp.linspace(x.min(), x.max(), 100)

    cLR = LogisticRegression()
    cLR.fit(x[:, sp.newaxis], y)

    y_fit = expit(x_fit * cLR.coef_ + cLR.intercept_).flatten()
    return y_fit

x_fit = sp.linspace(0, 3000, 100)
line, = plt.plot([], color='red', linewidth=2, alpha=0.75)
line.set_data(x_fit, log_reg(x, y, x_fit))

# %% random margin - without bias
t = SDf['this_interval'].values
R = []
for i in tqdm(range(100)):
    rand_choices = sp.random.randint(2, size=t.shape).astype('bool')
    R.append(log_reg(x, rand_choices, x_fit))
R = sp.array(R)

alphas = [5, 0.5, 0.05]
opacities = [0.5, 0.4, 0.3]
for alpha, a in zip(alphas, opacities):
    R_pc = sp.percentile(R, (alpha, 100-alpha), 0)
    # plt.plot(x_fit, R_pc[0], color='blue', alpha=a)
    # plt.plot(x_fit, R_pc[1], color='blue', alpha=a)
    plt.fill_between(x_fit, R_pc[0], R_pc[1], color='blue', alpha=a)

# %% random margin - with animal bias
t = SDf['this_interval'].values
bias = (SessionDf['choice'] == 'right').sum() / SessionDf.shape[0]
R = []
for i in tqdm(range(100)):
    rand_choices = sp.rand(t.shape[0]) < bias
    R.append(log_reg(x, rand_choices, x_fit))
R = sp.array(R)

alphas = [5, 0.5, 0.05]
opacities = [0.5, 0.4, 0.3]
for alpha, a in zip(alphas, opacities):
    R_pc = sp.percentile(R, (alpha, 100-alpha), 0)
    # plt.plot(x_fit, R_pc[0], color='blue', alpha=a)
    # plt.plot(x_fit, R_pc[1], color='blue', alpha=a)
    plt.fill_between(x_fit, R_pc[0], R_pc[1], color='blue', alpha=a)

# %% histograms
fig, axes = plt.subplots()
shorts = SDf.groupby('choice').get_group('left')['this_interval'].values
longs = SDf.groupby('choice').get_group('right')['this_interval'].values
kwargs = dict(alpha=.5, density=True, bins=sp.linspace(0, 3000, 15))
axes.hist(shorts, **kwargs, label='short')
axes.hist(longs, **kwargs, label='long')
plt.legend()
axes.set_xlabel('interval (ms)')
axes.set_ylabel('density')















# %%
"""
##     ## ##     ## ##       ######## ####     ######  ########  ######   ######  ####  #######  ##    ##
###   ### ##     ## ##          ##     ##     ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ##
#### #### ##     ## ##          ##     ##     ##       ##       ##       ##        ##  ##     ## ####  ##
## ### ## ##     ## ##          ##     ##      ######  ######    ######   ######   ##  ##     ## ## ## ##
##     ## ##     ## ##          ##     ##           ## ##             ##       ##  ##  ##     ## ##  ####
##     ## ##     ## ##          ##     ##     ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ###
##     ##  #######  ########    ##    ####     ######  ########  ######   ######  ####  #######  ##    ##
"""


animal_folder = utils.get_folder_dialog()

# %%
SessionsDf = utils.get_sessions(animal_folder)
paths = [Path(path) for path in SessionsDf.groupby('task').get_group('learn_to_lick')['path']]

LogDfs = []
for path in tqdm(paths):
    log_path = path / 'arduino_log.txt'
    LogDf = bhv.get_LogDf_from_path(log_path)
    LogDf = bhv.filter_bad_licks(LogDf)
    LogDfs.append(LogDf)

for LogDf in LogDfs:
    # rename events of all future omitted rewards
    EventsDf = bhv.get_events_from_name(LogDf, 'REWARD_OMITTED_EVENT')
    for t in EventsDf['t'].values:
        Df = bhv.time_slice(LogDf, t-1000, t)
        ix = Df[Df['name'] == 'REWARD_AVAILABLE_EVENT'].index
        LogDf.loc[ix, 'name'] = "OMITTED_REWARD_AVAILABLE_EVENT"

# %% learn to lick inspections
pre, post = -2000, 4000
fig, axes = plt.subplots(nrows=3, figsize=[3, 5], sharey=True, sharex=True)

events = ['REWARD_AVAILABLE_EVENT', 'OMITTED_REWARD_AVAILABLE_EVENT', 'NO_REWARD_AVAILABLE_EVENT']
colors = sns.color_palette(palette='turbo',n_colors=len(LogDfs))
bins = sp.linspace(pre, post, 50)

for i,LogDf in enumerate(LogDfs):
    LicksDf = bhv.get_events_from_name(LogDf, 'LICK_EVENT')
    for event, ax in zip(events, axes):
        times = bhv.get_events_from_name(LogDf, event)['t'] # task event times
        try:
            plot_psth(LicksDf, times, zorder=-1*i, histtype='step', bins=bins, 
                      axes=ax, density=True, color=colors[i], alpha=0.75, label='day '+str(i))
        except:
            continue
        ax.set_title(event, fontsize='x-small')
        ax.axvline(0, linestyle=':', lw=1, alpha=0.5, color='k')

axes[0].legend(fontsize='x-small')
sns.despine(fig)
fig.suptitle('lick psth to cues')
fig.tight_layout()
# plt.savefig(plot_dir / 'lick_to_cues_psth.png', dpi=300)










# %%
"""
########  ######## ########  ##     ##  ######    ######   #### ##    ##  ######
##     ## ##       ##     ## ##     ## ##    ##  ##    ##   ##  ###   ## ##    ##
##     ## ##       ##     ## ##     ## ##        ##         ##  ####  ## ##
##     ## ######   ########  ##     ## ##   #### ##   ####  ##  ## ## ## ##   ####
##     ## ##       ##     ## ##     ## ##    ##  ##    ##   ##  ##  #### ##    ##
##     ## ##       ##     ## ##     ## ##    ##  ##    ##   ##  ##   ### ##    ##
########  ######## ########   #######   ######    ######   #### ##    ##  ######
"""


# %% Raw forces timecourse with L/R choice and go_cue timestamps 

fig, axes = plt.subplots()
ds = 10 # downsampling factor
axes.plot(LoadCellDf['t'].values[::ds], LoadCellDf['x'].values[::ds])
axes.plot(LoadCellDf['t'].values[::ds], LoadCellDf['y'].values[::ds])

group = LogDf.groupby('name').get_group("CHOICE_RIGHT_EVENT")
plt.vlines(group['t'].values,0,5000,color='k',lw=2)
group = LogDf.groupby('name').get_group("CHOICE_LEFT_EVENT")
plt.vlines(group['t'].values,0,5000,color='g',lw=2)

group = LogDf.groupby('name').get_group("GO_CUE_EVENT")
plt.vlines(group['t'].values,1000,-1000,color='b',lw=2)

plt.title('Raw forces timecourse with L/R choice and go_cue timestamps ')




# %% get choice time 
# %%
inds = SessionDf[SessionDf['choice_rt'] < 10].index
times = []
for i in tqdm(inds):
    TrialDf = TrialDfs[i]
    t_stop = TrialDf.loc[TrialDf['name'] == "CHOICE_EVENT",'t'].values[0]
    times.append(t_stop)


# %%






# %% force aligned on cues

pre, post = -1000, 1000
fig, ax = plt.subplots(figsize=[5, 4])

Fx = []
Fy = []

for t in times:
    LCDf = bhv.time_slice(LoadCellDf, t+pre, t+post)
    Fx.append(LCDf['x'].values)
    Fy.append(LCDf['y'].values)

Fx = sp.array(Fx).T
Fy = sp.array(Fy).T

# M = sp.sqrt(Fx**2+Fy**2)
M = Fx

tvec = sp.linspace(pre, post, Fx.shape[0])
for i in range(Fx.shape[1]):
    ax.plot(tvec, M[:, i], lw=0.5, alpha=0.5)
# ax.plot(tvec, sp.average(M, 1), lw=1, color='k', alpha=0.5)
ax.axvline(0, linestyle=':', lw=1, alpha=0.5, color='k')
# ax.set_title(event, fontsize='x-small')
ax.set_xlabel('time (ms)')

sns.despine(fig)
fig.tight_layout()

















"""
 #######  ##       ########        ###    ##    ## ########     ##     ## ##    ## ##     ##  ######  ######## ########
##     ## ##       ##     ##      ## ##   ###   ## ##     ##    ##     ## ###   ## ##     ## ##    ## ##       ##     ##
##     ## ##       ##     ##     ##   ##  ####  ## ##     ##    ##     ## ####  ## ##     ## ##       ##       ##     ##
##     ## ##       ##     ##    ##     ## ## ## ## ##     ##    ##     ## ## ## ## ##     ##  ######  ######   ##     ##
##     ## ##       ##     ##    ######### ##  #### ##     ##    ##     ## ##  #### ##     ##       ## ##       ##     ##
##     ## ##       ##     ##    ##     ## ##   ### ##     ##    ##     ## ##   ### ##     ## ##    ## ##       ##     ##
 #######  ######## ########     ##     ## ##    ## ########      #######  ##    ##  #######   ######  ######## ########
"""


# """
# ##        #######     ###    ########   ######  ######## ##       ##
# ##       ##     ##   ## ##   ##     ## ##    ## ##       ##       ##
# ##       ##     ##  ##   ##  ##     ## ##       ##       ##       ##
# ##       ##     ## ##     ## ##     ## ##       ######   ##       ##
# ##       ##     ## ######### ##     ## ##       ##       ##       ##
# ##       ##     ## ##     ## ##     ## ##    ## ##       ##       ##
# ########  #######  ##     ## ########   ######  ######## ######## ########
# """

# # %% syncing
# LoadCellDf, harp_sync = bhv.parse_harp_csv(log_path.parent / "bonsai_harp_log.csv", save=True)
# arduino_sync = bhv.get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT")

# # %% - checking if the triggering worked
# t_harp = harp_sync['t'].values
# t_arduino = arduino_sync['t'].values

# plt.plot(sp.diff(t_harp), label='harp')
# plt.plot(sp.diff(t_arduino), label='arduino')
# plt.legend()

# # %%
# t_harp = pd.read_csv(log_path.parent / "harp_sync.csv")['t'].values
# t_arduino = pd.read_csv(log_path.parent / "arduino_sync.csv")['t'].values

# m, b = bhv.sync_clocks(t_harp, t_arduino, log_path)
# LogDf = pd.read_csv(log_path.parent / "LogDf.csv")

# # %%

# %%

