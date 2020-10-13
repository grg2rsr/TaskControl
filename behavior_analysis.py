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

# Plotting Defaults
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"

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
axes.axhline(0.85,**line_kwargs)
axes.axhline(0.75,lw=1,linestyle=':',alpha=0.75,color='r')
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
    t_rew_avail = Df[Df['name'] == 'REWARD_AVAILABLE_EVENT']['t'].values[0]
    S = pd.Series(dict(name="OMITTED_REWARD_AVAILABLE_EVENT",t=t_rew_avail))
    LogDf = LogDf.append(S,ignore_index=True)
LogDf = LogDf.sort_values('t')

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

bins=sp.linspace(0, 500, 50)

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

# %% Reward rate
t_rewards = LogDf.groupby('name').get_group('REWARD_COLLECTED_EVENT')['t']
rew_magnitude = 5 # ul
rew_rate = rew_magnitude * 1/(sp.diff(t_rewards.values) / (1000 * 60)) # per minute
fig, axes = plt.subplots()
axes.plot(t_rewards[:-1].values / (1000*60), rew_rate, label = 'Instantaneous rew. rate')
plt.xlabel('Time (min.)')
plt.ylabel('Water consumed (uL)')
plt.title('Reward consumption per minute')

t_max = LogDf.iloc[-1]['t']
t_max / (1000*60)

dt = 30000
rwc = []
for i,t in enumerate(sp.arange(dt,t_max,dt)):
    Df = bhv.time_slice(LogDf,t-dt, t)
    try:
        rwc.append((i,Df.groupby('name').get_group('REWARD_COLLECTED_EVENT').shape[0]))
    except:
        pass

rwc = sp.array(rwc)
axes.plot(rwc[:,0]/2,rwc[:,1]*5, label = '30 sec. window mean rew. rate')
plt.legend(loc='upper right', frameon=False, fontsize = 8)
plt.setp(axes, xticks=np.arange(0, int(t_max / (1000*60)), 5), xticklabels=np.arange(0, int(t_max / (1000*60)), 5))
plt.setp(axes, yticks=np.arange(0, np.max(rew_rate), 5), yticklabels=np.arange(0, np.max(rew_rate), 5))

"""
##       ########    ###    ########  ##    ##    ########  #######     ########  ##     ##  ######  ##     ##
##       ##         ## ##   ##     ## ###   ##       ##    ##     ##    ##     ## ##     ## ##    ## ##     ##
##       ##        ##   ##  ##     ## ####  ##       ##    ##     ##    ##     ## ##     ## ##       ##     ##
##       ######   ##     ## ########  ## ## ##       ##    ##     ##    ########  ##     ##  ######  #########
##       ##       ######### ##   ##   ##  ####       ##    ##     ##    ##        ##     ##       ## ##     ##
##       ##       ##     ## ##    ##  ##   ###       ##    ##     ##    ##        ##     ## ##    ## ##     ##
######## ######## ##     ## ##     ## ##    ##       ##     #######     ##         #######   ######  ##     ##
"""

# %% Preprocessing: LC syncing
log_path = utils.get_file_dialog()
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

# %% Choice / outcome grid for LC forces
sides = ['left', 'right']
outcomes = ['correct', 'incorrect']
fig, axes = plt.subplots(nrows=len(outcomes), ncols=len(sides), figsize=[5, 5], sharex=True, sharey=True)

pre, post = -100, 1000
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

# %% Heatmaps
pre, post = -1000, 5000
force_thresh = 2000
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
    choice_rt = []
    for _, row in tqdm(SDf.iterrows()):
        TrialDf = TrialDfs[row.name]
        t_align = TrialDf.loc[TrialDf['name'] == align_event, 't'].values[0]
        # identical to:
        # t_align = TrialDf.groupby('name').get_group(align_event)['t'].values
        LCDf = bhv.time_slice(LoadCellDf, t_align+pre, t_align+post)
        Fx.append(LCDf['x'].values)
        Fy.append(LCDf['y'].values)
        choice_rt.append(bhv.choice_RT(TrialDf).values-pre)

    Fx = sp.array(Fx).T
    Fy = sp.array(Fy).T

    # event_ix = Fx.shape[0] - post

    ## for heatmaps
    axes[i,0].matshow(Fx.T, origin='lower', vmin=-force_thresh, vmax=force_thresh, cmap='PiYG')
    axes[i,1].matshow(Fy.T, origin='lower', vmin=-force_thresh, vmax=force_thresh, cmap='PiYG')
    axes[i,0].axvline(x=1000, ymin=0, ymax=1, color = 'k', alpha = 0.5)
    axes[i,1].axvline(x=1000, ymin=0, ymax=1, color = 'k', alpha = 0.5)

    ymin = np.arange(-0.5,len(choice_rt)-1) # need to shift since lines starts at center of trial
    ymax = np.arange(0.45,len(choice_rt))
    axes[i,0].vlines(choice_rt, ymin, ymax, colors='k', linewidth=1)

plt.setp(axes, xticks=np.arange(0, post-pre+1, 1000), xticklabels=np.arange(pre/1000, post/1000+0.1, 1))

for ax in axes.flatten():
    ax.set_aspect('auto')

for ax in axes[-1,:]:
    ax.xaxis.set_ticks_position('bottom')

for ax, (side, outcome) in zip(axes[:,0],order):
    ax.set_ylabel('\n'.join([side,outcome]))

axes[0,0].set_title('Fx (aligned on go cue)')
axes[0,1].set_title('Fy')

axes[-1,0].set_xlabel('Time (s)')
axes[-1,1].set_xlabel('Time (s)')

fig.tight_layout()
fig.subplots_adjust(hspace=0.05)

# %% Response Forces to go cue
bin_width = 75 #ms
first_cue_ref = "TRIAL_ENTRY_EVENT"

plot_force_magnitude(LoadCellDf, SessionDf, TrialDfs, first_cue_ref, align_event, bin_width, axes=None)

# %% Response Forces aligned to anything
align_event = "CHOICE_INCORRECT_EVENT"

Fmag_1st, Fmag_2nd, licks, ys = [],[],[],[]
pre, post, plot_dur = 1000,1000,2000

fig , axes = plt.subplots()

twin_ax = axes.twinx()

for TrialDf in TrialDfs:

    if align_event in TrialDf.name.values:
        time_2nd = float(TrialDf[TrialDf.name == align_event]['t'])

        # Aligned to second cue
        F = bhv.time_slice(LoadCellDf, time_2nd-pre, time_2nd+post)
        y = np.sqrt(F['x']**2+F['y']**2)
        ys.append(y)
        
        try:
            licks.append(bhv.get_licks(LogDf, time_2nd-pre, time_2nd+post))
        except:
            pass

# Compute mean force for each outcome aligned to second        
Fmag = bhv.tolerant_mean(np.array(ys))
axes.plot(np.arange(len(Fmag))+1, Fmag, color = "k") 

# Get lick histogram
if not licks:
    pass
else:
    no_bins = round((plot_dur)/bin_width)
    counts, bins = np.histogram(np.concatenate(licks),no_bins)
    licks_freq = np.divide(counts, ((bin_width/1000)*len(ys)))
    twin_ax.step(bins[1:], licks_freq, alpha=0.5)

# Formatting
axes.set_ylabel('Force magnitude (a.u.)')
axes.set_xlim(0,plot_dur)
axes.set_ylim(0,2000)
axes.axvline(1000, linestyle = ':', color = "k", alpha = 0.5)
plt.setp(axes, xticks=np.arange(0, plot_dur+1, 500), xticklabels=np.arange(-1, 1+0.1, 0.5))

twin_ax.set_ylabel('Lick freq. (Hz)', color='C0')
plt.setp(twin_ax, yticks=np.arange(0, 11), yticklabels=np.arange(0, 11))

axes.set_title('Force Mag. and licking aligned to ' + align_event)

# %% Choice RT's distribution
bin_width = 250 #ms
choice_interval = 5000

fig, axes = plt.subplots()

choice_rt = np.empty(0)
for TrialDf in TrialDfs:
    choice_rt = np.append(choice_rt, bhv.choice_RT(TrialDf).values)

# includes front and back pushes, eliminates nans due to missed trials
clean_choice_rt = [x for x in choice_rt if not pd.isnull(x)] 

no_bins = round(choice_interval/bin_width)

counts, bins = np.histogram(clean_choice_rt, bins=no_bins, density = True, range = (-250, choice_interval))
axes.step(bins[1:], counts, color='C0')

axes.set_ylabel('Prob (%)')
axes.set_xlabel('Time (s)')
axes.set_title('Choice RT distribution')

# %% Bias over time
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
axes.set_xlabel('time (min.)')
axes.set_title('Lateral bias')
plt.setp(axes, xticks=np.arange(0, int(times.iloc[-1]), 5*60), xticklabels=np.arange(0, int(times.iloc[-1]/60), 5))
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

# %% Loading
animal_folder = utils.get_folder_dialog()
plot_dir = animal_folder / 'plots'
animal_meta = pd.read_csv(animal_folder / 'animal_meta.csv')
animal_id = animal_meta[animal_meta['name'] == 'ID']['value'].values[0]
nickname = animal_meta[animal_meta['name'] == 'Nickname']['value'].values[0]
os.makedirs(plot_dir, exist_ok=True)

# %%
"Learn to LICK inspections"

SessionsDf = utils.get_sessions(animal_folder)
paths = [Path(path) for path in SessionsDf.groupby('task').get_group('learn_to_lick')['path']]

LogDfs = []
for path in tqdm(paths):
    log_path = path / 'arduino_log.txt'
    LogDf = bhv.get_LogDf_from_path(log_path)
    LogDf = bhv.filter_bad_licks(LogDf)
    LogDfs.append(LogDf)
   
pre, post = -2000, 4000
fig, axes = plt.subplots(nrows=3, figsize=[3, 5], sharey=True, sharex=True)

events = ['REWARD_AVAILABLE_EVENT', 'OMITTED_REWARD_AVAILABLE_EVENT', 'NO_REWARD_AVAILABLE_EVENT']
colors = sns.color_palette(palette='turbo',n_colors=len(LogDfs))
bins = sp.linspace(pre, post, 50)

for i,LogDf in enumerate(LogDfs):
    LicksDf = bhv.get_events_from_name(LogDf, 'LICK_EVENT')
    EventsDf = bhv.get_events_from_name(LogDf, 'REWARD_OMITTED_EVENT')

    for t in EventsDf['t'].values:
        Df = bhv.time_slice(LogDf, t-1000, t)
        t_rew_avail = Df[Df['name'] == 'REWARD_AVAILABLE_EVENT']['t'].values[0]
        S = pd.Series(dict(name="OMITTED_REWARD_AVAILABLE_EVENT",t=t_rew_avail))
        LogDf = LogDf.append(S,ignore_index=True)
    LogDf = LogDf.sort_values('t')

    for event, ax in zip(events, axes):
        times = bhv.get_events_from_name(LogDf, event)['t'] # task event times
        try:
            plot_psth(LicksDf, times, zorder=1*i, histtype='step', bins=bins, 
                      axes=ax, density=True, color=colors[i], alpha=0.75, label='day '+str(i))
        except:
            continue
        ax.set_title(event, fontsize='x-small')
        ax.axvline(0, linestyle=':', lw=1, alpha=0.5, color='k')

axes[0].legend(fontsize='x-small')

for ax in axes:
    ax.set_ylabel('p')

sns.despine(fig)
fig.suptitle(animal_id+' '+nickname+'\nlick psth to cues',fontsize='small')
fig.tight_layout()
plt.savefig(plot_dir / 'lick_to_cues_psth_across_days.png', dpi=300)

axes[0].hist(times,bins=bins,density=True)

# %% 
"Learn to PUSH inspections"

SessionsDf = utils.get_sessions(animal_folder)
paths = [Path(path) for path in SessionsDf.groupby('task').get_group('learn_to_push')['path']]

LogDfs = []
for path in tqdm(paths):
    log_path = path / 'arduino_log.txt'
    LogDf = bhv.get_LogDf_from_path(log_path)
    LogDf = bhv.filter_bad_licks(LogDf)
    LogDfs.append(LogDf)

colors = sns.color_palette(palette='turbo',n_colors=len(LogDfs))

# %% Reward collection across sessions
fig, axes = plt.subplots(figsize=(3, 3))

reward_collect_ratio = []
for j, LogDf in enumerate(LogDfs):

    TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

    TrialDfs = []

    for i, row in TrialSpans.iterrows():
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    rew_collected = len(LogDf[LogDf['name']=="REWARD_COLLECTED_EVENT"])
    rew_available_non_omitted = len(LogDf[LogDf['name']=="REWARD_AVAILABLE_EVENT"])-len(LogDf[LogDf['name']=="REWARD_OMITTED_EVENT"])

    reward_collect_ratio = np.append(reward_collect_ratio, rew_collected/rew_available_non_omitted)

axes.plot(np.arange(len(reward_collect_ratio)), reward_collect_ratio)
axes.set_ylabel('Ratio')
axes.set_xlabel('Session number')
axes.set_title('Reward collected ratio across sessions')
axes.set_ylim([0,1])
axes.set_xlim([0,len(reward_collect_ratio)])
plt.setp(axes, xticks=np.arange(0,len(reward_collect_ratio)), xticklabels=np.arange(0,len(reward_collect_ratio)))
axes.axhline(0.9, color = 'k', alpha = 0.5, linestyle=':')

# %% X/Y thresh and bias across sessions
fig, axes = plt.subplots(figsize=(4, 4))

x_thresh, y_thresh, bias = [],[],[]
for LogDf in LogDfs:

    x_thresh = np.append(x_thresh, np.mean(LogDf[LogDf['var'] == 'X_thresh'].value.values))
    y_thresh = np.append(y_thresh, np.mean(LogDf[LogDf['var'] == 'Y_thresh'].value.values))
    bias = np.append(bias, LogDf[LogDf['var'] == 'bias'].value.values[-1]) # last bias value

axes.plot(np.arange(len(LogDfs)), x_thresh, color = 'C0', label = 'X thresh')
axes.plot(np.arange(len(LogDfs)), y_thresh, color = 'm', label = 'Y thresh')

axes.set_ylim([1000,2500])
axes.set_ylabel('Force (a.u.)')
axes.set_title('Mean X/Y thresh forces and bias across sessions')
axes.legend(frameon=False)
axes.set_xticks(np.arange(len(LogDfs)))
axes.set_xticklabels(SessionsDf[SessionsDf['task'] == 'learn_to_push']['date'].values,rotation=90) 

twin_ax = axes.twinx()
twin_ax.plot(bias, color = 'g', alpha = 0.5)
twin_ax.set_ylabel('Bias', color = 'g')
twin_ax.set_yticks([0,1])
twin_ax.set_yticklabels(['left','right'])

fig.tight_layout()

# %% Choice RT's distribution 
bin_width = 250 #ms
choice_interval = 5000

fig, axes = plt.subplots()
colors = sns.color_palette(palette='turbo', n_colors=len(LogDfs))

for i,LogDf in enumerate(LogDfs):

    TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

    TrialDfs = []
    for j, row in tqdm(TrialSpans.iterrows()):
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    choice_rt = np.empty(0)

    for TrialDf in TrialDfs:
        choice_rt = np.append(choice_rt, bhv.choice_RT(TrialDf).values)

    # includes front and back pushes, eliminates nans due to missed trials
    clean_choice_rt = [x for x in choice_rt if not pd.isnull(x)] 

    no_bins = round(choice_interval/bin_width)

    counts, bins = np.histogram(clean_choice_rt, bins=no_bins, density = True, range = (-250, choice_interval))
    axes.step(bins[1:], counts, color=colors[i], zorder=1*i, alpha=0.75, label='day '+str(i+1))

    axes.axvline(np.percentile(clean_choice_rt,75),color=colors[i], alpha=0.5)

plt.legend(frameon=False)
axes.set_ylabel('Prob (%)')
axes.set_xlabel('Time (s)')
fig.suptitle(animal_id+' '+nickname+'\nChoice RT distribution with 75th percentile',fontsize='small')

# %% Missed trials increase as session goes on
fig, axes = plt.subplots()

for j, LogDf in enumerate(LogDfs):

    TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

    TrialDfs = []
    for i, row in TrialSpans.iterrows():
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    SessionDf = bhv.parse_trials(TrialDfs, (bhv.get_start, bhv.get_stop, bhv.get_outcome))

    x = np.arange(len(SessionDf))  
    MissedDf = SessionDf['outcome'] == 'missed'

    # grand average rate
    y = np.cumsum(MissedDf.values) / (SessionDf.index.values+1)
    axes.plot(x,y, color = colors[j], label = 'day '+ str(j+1))

plt.legend(frameon=False)
axes.set_ylim([0,1])
axes.set_title('Ratio of missed trials across sessions')
axes.set_xlabel('Trial #')
axes.set_ylabel('Grand average ratio')

# %% Get Fx and Fy forces for all sessions 
for path in paths:

    log_path = path / 'arduino_log.txt'

    LoadCellDf = pd.read_csv(path / "loadcell_data.csv")

    t_harp = pd.read_csv(path / "harp_sync.csv")['t'].values
    t_arduino = pd.read_csv(path / "arduino_sync.csv")['t'].values

    if t_harp.shape != t_arduino.shape:
        t_arduino, t_harp = bhv.cut_timestamps(t_arduino, t_harp, verbose = True)

    m, b = bhv.sync_clocks(t_harp, t_arduino, log_path)

    # median correction
    samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
    LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).median()
    LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).median()

    Fx = np.array(LoadCellDf['x'].values).T
    Fy = np.array(LoadCellDf['y'].values).T

# Downsample from 1Khz to 10Hz in order to be computationally feasible
Fx = Fx[0::1000]
Fy = Fy[0::1000]

# KDE plot
#f, ax = plt.subplots(figsize=(4, 4))
#sns.kdeplot(x=Fx, y=Fy, fill=True, cbar=True)
ax.set(xlim=(-4000,4000),ylim=(-4000,4000))
ax.set(xlabel = 'Left/Right axis', ylabel ='Front/Back axis')






"""
 ######   ########   #######  ##     ## ########     ##       ######## ##     ## ######## ##
##    ##  ##     ## ##     ## ##     ## ##     ##    ##       ##       ##     ## ##       ##
##        ##     ## ##     ## ##     ## ##     ##    ##       ##       ##     ## ##       ##
##   #### ########  ##     ## ##     ## ########     ##       ######   ##     ## ######   ##
##    ##  ##   ##   ##     ## ##     ## ##           ##       ##        ##   ##  ##       ##
##    ##  ##    ##  ##     ## ##     ## ##           ##       ##         ## ##   ##       ##
 ######   ##     ##  #######   #######  ##           ######## ########    ###    ######## ########
"""

# %% OLD Learn to Push DATA

old_animal_tags = ['JJP-00885', 'JJP-00886', 'JJP-00888', 'JJP-00889', 'JJP-00891']
old_animals_fd_path = Path("D:\DoneAnimals")

colors = sns.color_palette(palette='turbo', n_colors=len(old_animal_tags))

bin_width = 250 #ms
choice_interval = 5000
fig, axes = plt.subplots()

for i, old_animal_tag in enumerate(old_animal_tags):
    animal_folder = old_animals_fd_path / old_animal_tag

    SessionsDf = utils.get_sessions(animal_folder)
    paths = [Path(path) for path in SessionsDf.groupby('task').get_group('learn_to_push_alternating')['path']]

    LogDfs = []
    for path in paths:
        log_path = path / 'arduino_log.txt'
        LogDf = bhv.get_LogDf_from_path(log_path)
        LogDf = bhv.filter_bad_licks(LogDf)
        LogDfs.append(LogDf)

    for LogDf in tqdm(LogDfs):
        
        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_EVENT", "ITI_STATE")

        TrialDfs = []
        for j, row in tqdm(TrialSpans.iterrows()):
            TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

        choice_rt = np.empty(0)

        for TrialDf in TrialDfs:
            t_go_cue = TrialDf.groupby('name').get_group("SECOND_TIMING_CUE_EVENT").iloc[-1]['t'] # this may break for final learn to time
            
            if "CHOICE_RIGHT_EVENT" in TrialDf.name.values:
                t_choice = TrialDf.groupby('name').get_group("CHOICE_RIGHT_EVENT").iloc[-1]['t']
                choice_rt = np.append(choice_rt, t_go_cue-t_choice)
            elif "CHOICE_LEFT_EVENT " in TrialDf.name.values:
                t_choice = TrialDf.groupby('name').get_group("CHOICE_LEFT_EVENT").iloc[-1]['t']
                choice_rt = np.append(choice_rt, t_choice-t_go_cue)

        # includes front and back pushes, eliminates nans due to missed trials
        clean_choice_rt = [x for x in choice_rt if not pd.isnull(x)] 

        axes.plot(np.percentile(clean_choice_rt,75), i, color=colors[i], alpha=0.5)


plt.legend(frameon=False)
axes.set_ylabel('Prob (%)')
axes.set_xlabel('Time (s)')
plt.suptitle(animal_id+' '+nickname+'\nChoice RT distribution with 75 percentile',fontsize='small')



# %% NEW Learn to Push DATA
SessionsDf = utils.get_sessions(animal_folder)
paths = [Path(path) for path in SessionsDf.groupby('task').get_group('learn_to_push')['path']]

LogDfs = []
for path in tqdm(paths):
    log_path = path / 'arduino_log.txt'
    LogDf = bhv.get_LogDf_from_path(log_path)
    LogDf = bhv.filter_bad_licks(LogDf)
    LogDfs.append(LogDf)

colors = sns.color_palette(palette='turbo',n_colors=len(LogDfs))



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
