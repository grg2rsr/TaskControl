# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

sys.path.append('..')

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv
from Utils import behavior_analysis_utils as bhv
import pandas as pd
from sklearn.linear_model import LogisticRegression
from scipy.special import expit

# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
from Utils import utils

from behavior_plotters import *

# Plotting Defaults
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"
plt.rcParams["xtick.major.size"] = 1.5
plt.rcParams["ytick.major.size"] = 1.5

SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

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

LogDf = bhv.get_LogDf_from_path(log_path)
LogDf = bhv.filter_bad_licks(LogDf)

# %% across sessions - plot weight
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
line_kwargs = dict(lw=1,linestyle=':',alpha=0.75)
axes.axhline(0.85, color='g', **line_kwargs)
axes.axhline(0.80, color='r', **line_kwargs)
axes.set_ylim(0.5,1)
axes.set_title('weight')
axes.set_xlabel('session date')
axes.set_ylabel('weight %')
sns.despine(fig)
fig.tight_layout()


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
pre, post = 2000, 4000
fig, axes = plt.subplots(nrows=3, figsize=[3, 5], sharey=True, sharex=True)

events = ['REWARD_AVAILABLE_EVENT', 'OMITTED_REWARD_AVAILABLE_EVENT', 'NO_REWARD_AVAILABLE_EVENT']
LicksDf = bhv.get_events_from_name(LogDf, 'LICK_EVENT')
for event, ax in zip(events, axes):
    times = bhv.get_events_from_name(LogDf, event)['t'] # task event times
    try:
        plot_psth(LicksDf, times, bins=sp.linspace(-pre, post, 50), axes=ax, density=True) # Density with time on ms screws up everything
    except:
        continue
    ax.set_title(event, fontsize='x-small')
    ax.axvline(0, linestyle=':', lw=1, alpha=0.5, color='k')

sns.despine(fig)
fig.suptitle('lick psth to cues')
fig.tight_layout()
plt.savefig(plot_dir / 'lick_to_cues_psth.png', dpi=300)

# %% Reaction times - first lick to cue
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

# %%

"""
##       ########    ###    ########  ##    ##    ########  #######     ########  ##     ##  ######  ##     ##
##       ##         ## ##   ##     ## ###   ##       ##    ##     ##    ##     ## ##     ## ##    ## ##     ##
##       ##        ##   ##  ##     ## ####  ##       ##    ##     ##    ##     ## ##     ## ##       ##     ##
##       ######   ##     ## ########  ## ## ##       ##    ##     ##    ########  ##     ##  ######  #########
##       ##       ######### ##   ##   ##  ####       ##    ##     ##    ##        ##     ##       ## ##     ##
##       ##       ##     ## ##    ##  ##   ###       ##    ##     ##    ##        ##     ## ##    ## ##     ##
######## ######## ##     ## ##     ## ##    ##       ##     #######     ##         #######   ######  ##     ##
"""

animal_folder = utils.get_folder_dialog()
task_name = ['learn_to_push_cr','learn_to_push_vis_feedback']
SessionsDf = utils.get_sessions(animal_folder)

PushSessionsDf = pd.concat([SessionsDf.groupby('task').get_group(name) for name in task_name])

log_paths = [Path(path)/'arduino_log.txt' for path in PushSessionsDf['path']]

for log_path in tqdm(log_paths[3:]):

    print('\n')
    print(log_path)

    # %% Preprocessing: LC syncing
    animal_meta = pd.read_csv(log_path.parent.parent / 'animal_meta.csv')
    animal_id = animal_meta[animal_meta['name'] == 'ID']['value'].values[0]

    plot_dir = log_path.parent / 'plots'
    os.makedirs(plot_dir, exist_ok=True)

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
    for i, row in tqdm(TrialSpans.iterrows(),position=0, leave=True):
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    metrics = (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.choice_RT, bhv.get_in_corr_loop, \
                bhv.is_successful, bhv.get_outcome, bhv.get_instructed, bhv.get_bias, bhv.get_correct_zone, bhv.get_x_thresh)
    SessionDf = bhv.parse_trials(TrialDfs, metrics)

    # %% Success rate
    history = 10 # trial rolling mean 
    plot_success_rate(LogDf, SessionDf, history, axes=None)
    plt.savefig(plot_dir / ('success_rate.png'), dpi=300)

    # %% Choice / Outcome grid for LC forces
    choices = ['left', 'right']
    outcomes = ['correct', 'incorrect']
    fig, axes = plt.subplots(nrows=len(outcomes), ncols=len(choices), figsize=[5, 5], sharex=True, sharey=True)

    plot_lim = 5000
    first_event = "GO_CUE_EVENT"
    second_event = "CHOICE_EVENT"

    for i, choice in enumerate(choices):
        for j, outcome in enumerate(outcomes):
            try:
                # Only get filter pair combination
                filter_pair = [('choice', choice),('outcome', outcome),('instructed_trial', False)]
                TrialDfs_filt = bhv.filter_trials_by(SessionDf,TrialDfs, filter_pair)
            except:
                continue

            ax = axes[j, i]

            ## for trajectories
            ax = trajectories_with_marker(LoadCellDf, TrialDfs_filt, SessionDf, first_event, second_event, plot_lim, animal_id, ax)

    sns.despine(fig)
    axes[0, 0].set_title('left')
    axes[0, 1].set_title('right')
    axes[0, 0].set_ylabel('correct')
    axes[1, 0].set_ylabel('incorrect')
    fig.tight_layout()
    plt.savefig(plot_dir / ('trajectories_with_marker.png'), dpi=300)

    # %% Heatmaps
    pre, post = 500, 5000
    force_thresh = 3000
    align_event = "GO_CUE_EVENT"

    plot_forces_heatmaps(LoadCellDf, SessionDf, TrialDfs, align_event, pre, post, force_thresh, animal_id)
    plt.savefig(plot_dir / ('forces_heatmap.png'), dpi=300)

    # %% Plot_force_magnitude
    pre, post = 500, 2000
    bin_width = 25 #ms
    force_thresh = 4000
    filter_pairs = [('has_choice', True)] # has to be list
    first_cue_ref = "TRIAL_ENTRY_EVENT"
    second_cue_ref = "GO_CUE_EVENT"

    plot_force_magnitude(LogDf, LoadCellDf, SessionDf, TrialDfs, first_cue_ref, second_cue_ref, pre, post, force_thresh, bin_width, filter_pairs)
    plt.savefig(plot_dir / ('forces_mag ' + str(filter_pairs) + '.png'), dpi=300)

    # %% Response Forces aligned to anything split by any input 
    split_by = 'choice' 
    align_event = "GO_CUE_EVENT"
    pre, post, thresh = 500,2000,4000

    axes = plot_split_forces_magnitude(SessionDf, LoadCellDf, TrialDfs, align_event, pre, post, split_by, animal_id)

    # Formatting
    for ax in axes:
        ax.set_ylim(-thresh,thresh)
        ax.set_xlim(0,post+pre)
        ax.axvline(pre, linestyle = ':', color = "k", alpha = 0.5)
        ax.legend()

    plt.savefig(plot_dir / ('forces_split_by ' + str(split_by) + '.png'), dpi=300)

    # %% Choice RT's distribution
    bin_width = 100 #ms
    choice_interval = 2500
    plot_choice_RT_hist(SessionDf, choice_interval, bin_width)
    plt.savefig(plot_dir / ('choice_rt_distro.png'), dpi=300)

    # %% XY and Bias over time
    plot_x_y_thresh_bias(LogDf, SessionDf)
    plt.savefig(plot_dir / ('x_y_tresh_bias.png'), dpi=300)

    # %% Autocorr during ITI state to see if mice have periodic movements and if these twitches are biased to a side
    TrialSpans = bhv.get_spans_from_names(LogDf, "ITI_STATE", "TRIAL_ENTRY_STATE")

    TrialDfs = []
    for i, row in TrialSpans.iterrows():
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    metrics = (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.is_successful, bhv.get_outcome, bhv.get_correct_zone)
    SessionDf = bhv.parse_trials(TrialDfs, metrics)

    first_event = "first"
    second_event = "last"
    plot_lim = 7000

    # Check if they are making periodic pushes during ITI
    axes = autocorr_forces(LoadCellDf, TrialDfs, first_event, second_event)
    plt.savefig(plot_dir / ('autocorr_during_ITI.png'), dpi=300)

    plot_lim = 7000
    # Analyze "twitches" during ITI
    axes = trajectories_with_marker(LoadCellDf, TrialDfs, SessionDf, first_event, second_event, plot_lim, animal_id)
    axes.set_title('Trajectories during ITI (twitches)')
    plt.savefig(plot_dir / ('twitches_during_ITI.png'), dpi=300)

    plt.close('all')

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

pre, post = 1000, 1000
events = ["FIRST_TIMING_CUE_EVENT", "SECOND_TIMING_CUE_EVENT"]
fig, axes = plt.subplots(ncols=len(events), sharex=True, sharey=True, figsize=[5, 4])

for event, ax in zip(events, axes):
    EventDf = bhv.get_events_from_name(LogDf, event)

    Fx = []
    Fy = []

    for t in tqdm(EventDf['t'].values):
        LCDf = bhv.time_slice(LoadCellDf, t-pre, t+post)
        Fx.append(LCDf['x'].values)
        Fy.append(LCDf['y'].values)

    Fx = sp.array(Fx).T
    Fy = sp.array(Fy).T

    M = sp.sqrt(Fx**2+Fy**2)

    tvec = sp.linspace(-pre, post, Fx.shape[0])
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

# %% Loading up everything
log_path = utils.get_file_dialog()

animal_meta = pd.read_csv(log_path.parent.parent / 'animal_meta.csv')
animal_id = animal_meta[animal_meta['name'] == 'ID']['value'].values[0]

plot_dir = log_path.parent / 'plots'
os.makedirs(plot_dir, exist_ok=True)

LoadCellDf, harp_sync = bhv.parse_harp_csv(log_path.parent / "bonsai_harp_log.csv", save=True)
arduino_sync = bhv.get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT")

t_harp = pd.read_csv(log_path.parent / "harp_sync.csv")['t'].values
t_arduino = pd.read_csv(log_path.parent / "arduino_sync.csv")['t'].values

if t_harp.shape != t_arduino.shape:
    t_arduino, t_harp = bhv.cut_timestamps(t_arduino, t_harp, verbose = True)

m, b = bhv.sync_clocks(t_harp, t_arduino, log_path)
LogDf = pd.read_csv(log_path.parent / "LogDf.csv")

# median correction
samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).median()
LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).median()

# cut LogDf to same data len in case (for example bc of bonsai crashes)
LogDf = LogDf.loc[LogDf['t'] < LoadCellDf.iloc[-1]['t']]

TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

TrialDfs = []
for i, row in tqdm(TrialSpans.iterrows()):
    TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

SessionDf = bhv.parse_trials(TrialDfs, (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.choice_RT, bhv.is_successful, bhv.get_outcome, bhv.get_interval))

# %% Plotting 
window_size = 1000
pre, post = 1000, 4000
force_tresh = 3000
history_trials = 10
first_cue_ref = "FIRST_TIMING_CUE_EVENT"
align_ref = "SECOND_TIMING_CUE_EVENT"

plot_general_info(LogDf, path)

# Heat map plots for X/Y
plot_forces_heatmaps(LogDf, LoadCellDf, align_ref, pre, post,)

# Sucess rate over session
plot_success_rate(SessionDf, LogDf, history_trials)

# Psychometric adapted from Georg's code
plot_psychometric(SessionDf)

# Choice matrix
plot_choice_matrix(SessionDf,LogDf,'incorrect')
plot_choice_matrix(SessionDf,LogDf,'premature')

# Force magnitude aligned to 1st and 2nd timing cues with lick freq. on top
bin_width = 75 # ms
plot_force_magnitude(LoadCellDf, SessionDf, TrialDfs, first_cue_ref, align_ref, pre, post, force_tresh, bin_width)

# CT histogram to detect/quantify biases or motor strategies
bin_width = 100 # ms
plot_choice_RT_hist(SessionDf, choice_interval, bin_width)

# Trajectory plots
TrialDfs_correct = bhv.filter_trials_by(SessionDf,TrialDfs, ('outcome', 'correct'))
TrialDfs_incorrect = bhv.filter_trials_by(SessionDf,TrialDfs, ('outcome', 'incorrect'))
plot_mean_trajectories(LogDf, LoadCellDf, SessionDf, TrialDfs_correct, align_event, pre, post, animal_id)
plot_mean_trajectories(LogDf, LoadCellDf, SessionDf, TrialDfs_incorrect, align_event, pre, post, animal_id)

# Histograms
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
for path in tqdm(paths,position=0, leave=True):
    log_path = path / 'arduino_log.txt'
    LogDf = bhv.get_LogDf_from_path(log_path)
    LogDf = bhv.filter_bad_licks(LogDf)
    LogDfs.append(LogDf)
   
pre, post = 2000, 4000
fig, axes = plt.subplots(nrows=3, figsize=[3, 5], sharey=True, sharex=True)

events = ['REWARD_AVAILABLE_EVENT', 'OMITTED_REWARD_AVAILABLE_EVENT', 'NO_REWARD_AVAILABLE_EVENT']
colors = sns.color_palette(palette='turbo',n_colors=len(LogDfs))
bins = sp.linspace(-pre, post, 50)

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
task_name = ['learn_to_push_vis_feedback']
SessionsDf = utils.get_sessions(animal_folder)

PushSessionsDf = pd.concat([SessionsDf.groupby('task').get_group(name) for name in task_name])

paths = [Path(path) for path in PushSessionsDf['path']]

LogDfs = []
for path in tqdm(paths, position=0, leave=True):
    log_path = path / 'arduino_log.txt'
    LogDf = bhv.get_LogDf_from_path(log_path)
    LogDf = bhv.filter_bad_licks(LogDf)
    LogDfs.append(LogDf)

colors = sns.color_palette(palette='turbo',n_colors=len(LogDfs))

# %%
" General functions"

# Sessions overview
plot_sessions_overview(LogDfs, paths, task_name[0], animal_id)
plt.savefig(plot_dir / 'learn_to_push_overview.png', dpi=300)

#  Reward collection across sessions
rew_collected_across_sessions(LogDfs)
plt.savefig(plot_dir / 'rew_collected_across_sessions.png', dpi=300)

# X/Y thresh and bias across sessions
x_y_tresh_bias_across_sessions(LogDfs, paths)
plt.savefig(plot_dir / 'learn_to_push_x_y_thresh_bias_across_sessions.png', dpi=300)

# Choice RT's distribution 
bin_width = 250 #ms
choice_interval = 5000
percentile = 75 # Choice RTs compromise X% of data
choice_rt_across_sessions(LogDfs, bin_width, choice_interval, percentile, animal_id)
plt.savefig(plot_dir / 'learn_to_push_choice_rt_distro.png', dpi=300)

# %% Get Fx and Fy forces for all sessons in a 2D Contour plot
trials_only = False
axes = force_2D_contour_across_sessions(paths, task_name[0], animal_id, trials_only)

plt.savefig(plot_dir / ('learn_to_push_2D_Contour_' + str(trials_only) + '.png'), dpi=300)

# %% Force mag to go cue across sessions
fig, axes = plt.subplots()

align_event = "GO_CUE_EVENT"
pre, post = 1000,2000

for i,path in enumerate(paths):

    LoadCellDf = pd.read_csv(path / "loadcell_data.csv")

    TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_AVAILABLE_STATE", "ITI_STATE")
    if TrialSpans.empty:
        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

    TrialDfs = []
    for j, row in TrialSpans.iterrows():
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    _,_,Fmag = bhv.get_FxFy_window_aligned_on_event(LoadCellDf, TrialDfs, align_event, pre, post)

    F_mean = np.mean(Fmag)
    axes.plot(F_mean, label = i)
    plt.legend(loc='upper right', frameon=False)


"""
 ######   ########   #######  ##     ## ########     ##       ######## ##     ## ######## ##
##    ##  ##     ## ##     ## ##     ## ##     ##    ##       ##       ##     ## ##       ##
##        ##     ## ##     ## ##     ## ##     ##    ##       ##       ##     ## ##       ##
##   #### ########  ##     ## ##     ## ########     ##       ######   ##     ## ######   ##
##    ##  ##   ##   ##     ## ##     ## ##           ##       ##        ##   ##  ##       ##
##    ##  ##    ##  ##     ## ##     ## ##           ##       ##         ## ##   ##       ##
 ######   ##     ##  #######   #######  ##           ######## ########    ###    ######## ########
"""

# %% Loading
group_plot_dir = Path('D:\TaskControl\Animals\group_plots')
old_animal_tags = ['JJP-00885','JJP-00886','JJP-00888','JJP-00889','JJP-00891']
new_animal_tags = ['JJP-01151','JJP-01152','JJP-01153']
animal_tags = old_animal_tags + new_animal_tags

old_animal_fd_path = [Path("D:\DoneAnimals")]*len(old_animal_tags)
new_animal_fd_path = [Path("D:\TaskControl\Animals")]*len(new_animal_tags)
animals_fd_path = old_animal_fd_path + new_animal_fd_path

colors = sns.color_palette(palette='turbo', n_colors=len(animal_tags))

# %% Do animals learn faster to react to cue and make choice on new task?
bin_width = 250 #ms
choice_interval = 5000
fig, axes = plt.subplots(ncols = 2, figsize=[6, 3])

for i, (animal_tag,animal_fd_path) in enumerate(zip(animal_tags,animals_fd_path)):
    animal_folder = animal_fd_path / animal_tag

    SessionsDf = utils.get_sessions(animal_folder)

    paths,LogDfs,quantile_values = [],[],[]

    for k,SessionDf in SessionsDf.iterrows():
        if SessionDf['task'] == 'learn_to_push' or SessionDf['task'] == 'learn_to_push_alternating':
            paths.append(Path(SessionDf['path']))
   
    for path in paths:
        log_path = path / 'arduino_log.txt'
        LogDf = bhv.get_LogDf_from_path(log_path)
        LogDf = bhv.filter_bad_licks(LogDf)
        LogDfs.append(LogDf)
    
    for LogDf in tqdm(LogDfs,position=0, leave=True):
        
        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_AVAILABLE_STATE", "ITI_STATE")
        if TrialSpans.empty:
            TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

        TrialDfs = []
        for j, row in TrialSpans.iterrows():
            TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

        choice_rt = np.empty(0)

        for TrialDf in TrialDfs:
            try:
                t_go_cue = TrialDf.groupby('name').get_group("SECOND_TIMING_CUE_EVENT").iloc[-1]['t'] # this may break for final learn to time
            except:
                t_go_cue = TrialDf.groupby('name').get_group("GO_CUE_EVENT").iloc[-1]['t'] # this may break for final learn to time
            
            # Workaround for LogDf on old learn_to_push not logging choices correctly
            if "CHOICE_RIGHT_EVENT" in TrialDf.name.values:
                t_choice = TrialDf.groupby('name').get_group("CHOICE_RIGHT_EVENT").iloc[-1]['t']
                choice_rt = np.append(choice_rt, t_choice-t_go_cue)
            elif "CHOICE_LEFT_EVENT " in TrialDf.name.values:
                t_choice = TrialDf.groupby('name').get_group("CHOICE_LEFT_EVENT").iloc[-1]['t']
                choice_rt = np.append(choice_rt, t_choice-t_go_cue)

        # includes front and back pushes, eliminates nans due to missed trials
        clean_choice_rt = [x for x in choice_rt if not pd.isnull(x)] 
        quantile_values.append(np.percentile(clean_choice_rt,75))

    # OLD
    if i < len(old_animal_tags):
        axes[0].plot(quantile_values, color=colors[i], alpha=0.5, label = animal_tag)
    # NEW
    else:
        axes[1].plot(quantile_values, color=colors[i], alpha=0.5, label = animal_tag)

for ax in axes:
    ax.set_ylim([0,7000])
    ax.legend(frameon=False)
    ax.set_xlabel('Session number')

axes[0].set_ylabel('Time (ms)')
plt.suptitle('3rd quartile for Choice RT',fontsize='small')
fig.tight_layout()
plt.savefig(group_plot_dir / 'choice_rt_percentile_group.png', dpi=300)

# %% Weight x sucess rate and x missed_rate
fig, axes = plt.subplots(ncols = 2, figsize=[6, 3])

for i, (animal_tag,animal_fd_path) in enumerate(zip(new_animal_tags, new_animal_fd_path)):
    animal_folder = animal_fd_path / animal_tag

    SessionsDf = utils.get_sessions(animal_folder)

    paths,LogDfs = [],[]

    paths = [Path(path) for path in SessionsDf.groupby('task').get_group('learn_to_push')['path']]
   
    for path in paths:
        log_path = path / 'arduino_log.txt'
        LogDf = bhv.get_LogDf_from_path(log_path)
        LogDfs.append(LogDf)
    
    weight,sucess_rate,missed_rate = [],[],[]

    for (path,LogDf) in zip(paths,LogDfs):
        
        animal_meta = pd.read_csv(path.joinpath('animal_meta.csv'))
        weight.append(int(100*round(float(animal_meta.at[6, 'value'])/float(animal_meta.at[4, 'value']),2)))

        no_trials = len(bhv.get_events_from_name(LogDf,"TRIAL_ENTRY_STATE"))
        no_correct = len(bhv.get_events_from_name(LogDf,'CHOICE_CORRECT_EVENT'))
        no_missed = len(bhv.get_events_from_name(LogDf,'CHOICE_MISSED_EVENT'))

        sucess_rate.append((no_correct/no_trials)*100)
        missed_rate.append((no_missed/no_trials)*100)

    weight = np.array(weight)

    axes[0].scatter(weight, sucess_rate, color=colors[i], alpha=0.25, label = animal_tag)
    slope, intercept, r_value, p_value, std_err = sp.stats.linregress(weight, sucess_rate)
    axes[0].plot(weight, intercept + slope*weight, color=colors[i], alpha=0.75)
    print("Sucess Rate -> r_value:" + str(round(r_value,3)) + " | p_value = " + str(round(p_value,3)))

    axes[1].scatter(weight, missed_rate, color=colors[i], alpha=0.25, label = animal_tag)
    slope, intercept, r_value, p_value, std_err = sp.stats.linregress(weight, missed_rate)
    axes[1].plot(weight, intercept + slope*weight, color=colors[i], alpha=0.75)
    print("Missed Rate -> r_value:" + str(round(r_value,3)) + " | p_value = " + str(round(p_value,3)))
    
for ax in axes:
    ax.legend(frameon = False, fontsize='x-small')
    ax.set_xlabel('Weight (%)')

axes[0].set_ylabel('Sucess rate (%)')
axes[1].set_ylabel('Missed rate (%)')
fig.suptitle('Group level correlations', fontsize='small')
plt.setp(axes, xticks=np.arange(70, 90+1, 5), xticklabels=np.arange(70, 90+1, 5))
fig.tight_layout()

plt.savefig(group_plot_dir / 'weight_sucess_missed_corr_group.png', dpi=300)

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




"""
 #######  ##       ########        ###    ##    ## ########     ##     ## ##    ## ##     ##  ######  ######## ########
##     ## ##       ##     ##      ## ##   ###   ## ##     ##    ##     ## ###   ## ##     ## ##    ## ##       ##     ##
##     ## ##       ##     ##     ##   ##  ####  ## ##     ##    ##     ## ####  ## ##     ## ##       ##       ##     ##
##     ## ##       ##     ##    ##     ## ## ## ## ##     ##    ##     ## ## ## ## ##     ##  ######  ######   ##     ##
##     ## ##       ##     ##    ######### ##  #### ##     ##    ##     ## ##  #### ##     ##       ## ##       ##     ##
##     ## ##       ##     ##    ##     ## ##   ### ##     ##    ##     ## ##   ### ##     ## ##    ## ##       ##     ##
 #######  ######## ########     ##     ## ##    ## ########      #######  ##    ##  #######   ######  ######## ########
"""

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
