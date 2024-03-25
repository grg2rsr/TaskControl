# %% imports
import sys, os
from pathlib import Path
import numpy as np
import scipy as sp
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv

sys.path.append('/home/georg/Projects/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics
from Utils import sync

# %% extra metrics

def get_trial_type(TrialDf):
    var_name = "this_trial_type"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_delay(TrialDf):
    var_name = "this_delay"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_reward_magnitude(TrialDf):
    var_name = "reward_magnitude"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

# %% analysis
path = "/home/georg/data/JJP-04306/2022-06-20_14-53-27_twodistributionsv6_GR"
path = "/home/georg/data/JJP-04308/2022-06-20_13-49-45_twodistributionsv6_GR"
path = "/home/georg/data/JJP-04312/2022-06-20_15-54-04_twodistributionsv6_GR"

# %%
# Edward
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04306/2022-06-10_12-29-34_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04306/2022-06-20_14-53-27_twodistributionsv6_GR"

# %% Trisha
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-21_16-19-20_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-22_11-21-08_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-23_12-14-11_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-24_13-38-27_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-25_10-48-18_twodistributionsv6_GR"
# %% Alphonse
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-20_15-54-04_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-21_13-25-26_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-22_13-34-34_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-23_14-09-03_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-24_15-52-50_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-25_12-22-17_twodistributionsv6_GR"
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-25_13-41-44_twodistributionsv6_GR" # part 2

# %%
session_folder = Path(path)

LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min = 5, t_max=200)

session_metrics = (metrics.get_start, metrics.get_stop, get_trial_type,
                   get_delay, get_reward_magnitude)


SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics, trial_entry_event="TRIAL_ENTRY_EVENT")


# %% lick analysis - extracting
DelaysDf = SessionDf[SessionDf['this_trial_type'] == 0.0]
pre, post = (-2000,11000)

delays = DelaysDf.this_delay.unique()
delays = np.sort(delays)
lick_times = {}
for i,delay in enumerate(delays):
    lick_times[delay] = []
    Df = DelaysDf.groupby('this_delay').get_group(delay)
    for j, row in Df.iterrows():
        try:
            SDf = bhv.time_slice(LogDf, row.t_on + pre, row.t_on + post)
            # align on odor onset
            t0 = SDf.groupby('name').get_group("ODOR_ON").iloc[0]['t']
            lick_times_rel = SDf.groupby('name').get_group('LICK_EVENT')['t'].values - t0
            lick_times[delay].append(lick_times_rel)
        except KeyError:
            lick_times[delay].append(np.array([]))

# %% plotting raster
import seaborn as sns
n_delays = delays.shape[0]
delay_colors = sns.color_palette('deep',n_colors=n_delays)
n_trials_per_delay = [len(lick_times[delay]) for delay in delays]
fig, axes = plt.subplots(nrows = len(delays), gridspec_kw=dict(height_ratios=n_trials_per_delay),sharex=True)

for i,delay in enumerate(delays):
    licks_in_trial = lick_times[delay]
    for j, licks in enumerate(licks_in_trial):
        t = licks
        y = np.ones(t.shape[0])*j
        axes[i].plot(t,y,'.',color='k',alpha=0.5, markeredgewidth=0)
    axes[i].axvline(delay,color='dodgerblue',alpha=0.8,lw=2)
    axes[i].axvspan(0,1000,color='gray',alpha=0.5,linewidth=0)

# adding rate
tvec = np.arange(pre,post+100,50)
from scipy.signal import gaussian
w = gaussian(15,2)
w = w / w.sum()
for i,delay in enumerate(delays):
    licks_in_trial = lick_times[delay]

    fs = []
    for j, licks in enumerate(licks_in_trial):
        t = licks
        y = np.ones(t.shape[0])*j
        f = np.zeros(tvec.shape[0])
        f[np.digitize(t, tvec)] = 1
        f = np.convolve(f, w, mode='same')
        fs.append(f)
    F = np.array(fs)
    ax = plt.twinx(axes[i])
    ax.plot(tvec, np.average(F,axis=0),color=delay_colors[i], lw=2)


Animal = utils.Animal(session_folder.parent)
Session = utils.Session(session_folder)
title = ' - '.join([Animal.ID,Animal.Nickname,Session.date,Session.time])
fig.suptitle(title)
sns.despine(fig)
axes[-1].set_xlabel('time (ms)')
fig.tight_layout()

plots_folder = session_folder / 'plots'
os.makedirs(plots_folder, exist_ok=True)
plt.savefig(plots_folder / 'lick_plots.png', dpi=600)

# %% reward magnitude analysis

RewardsDf = SessionDf[SessionDf['this_trial_type'] == 2.0]
pre, post = (-5000,11000)

rewards = RewardsDf.reward_magnitude.unique()
rewards = np.sort(rewards)
lick_times = {}
for i, reward in enumerate(rewards):
    lick_times[reward] = []
    Df = RewardsDf.groupby('reward_magnitude').get_group(reward)
    for j, row in Df.iterrows():
        try:
            SDf = bhv.time_slice(LogDf, row.t_on + pre, row.t_on + post)
            # align on odor onset
            t0 = SDf.groupby('name').get_group("ODOR_ON").iloc[0]['t']
            lick_times_rel = SDf.groupby('name').get_group('LICK_EVENT')['t'].values - t0
            lick_times[reward].append(lick_times_rel)
        except KeyError:
            lick_times[reward].append(np.array([]))


# %% plotting raster
import seaborn as sns
n_rewards = rewards.shape[0]
reward_colors = sns.color_palette('Blues',n_colors=n_rewards)
n_trials_per_reward = [len(lick_times[reward]) for reward in rewards]
fig, axes = plt.subplots(nrows = len(rewards), gridspec_kw=dict(height_ratios=n_trials_per_reward),sharex=True)

for i,reward in enumerate(rewards):
    licks_in_trial = lick_times[reward]
    for j, licks in enumerate(licks_in_trial):
        t = licks
        y = np.ones(t.shape[0])*j
        axes[i].plot(t,y,'.',color='k',alpha=0.5, markeredgewidth=0)
    axes[i].axvline(3000,color='dodgerblue',alpha=0.8,lw=2)
    axes[i].axvspan(0,1000,color='gray',alpha=0.5,linewidth=0)


# adding rate
tvec = np.arange(pre,post+100,50)
from scipy.signal import gaussian
w = gaussian(15,2)
w = w / w.sum()
for i, reward in enumerate(rewards):
    licks_in_trial = lick_times[reward]

    fs = []
    for j, licks in enumerate(licks_in_trial):
        t = licks
        y = np.ones(t.shape[0])*j
        f = np.zeros(tvec.shape[0])
        f[np.digitize(t, tvec)] = 1
        f = np.convolve(f, w, mode='same')
        fs.append(f)
    F = np.array(fs)
    ax = plt.twinx(axes[i])
    ax.set_ylim(0,0.4)
    ax.plot(tvec, np.average(F,axis=0),color=reward_colors[i], lw=2)







# %%
metrics = (get_trial_type, get_delay, get_reward_magnitude)

SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics, trial_entry_event='TRIAL_ENTRY_STATE', trial_exit_event='ITI_STATE')

SessionDf.groupby('this_trial_type').get_group(0.0)['this_delay'].values
# %%
delays = SessionDf.groupby('this_trial_type').get_group(0.0)['this_delay'].values
mapping = [0, 1500, 3000, 6000]
samples = [mapping.index(delay) for delay in delays]

# %%
import seaborn as sns
fig, axes = plt.subplots(figsize=[8,3])
SDf = SessionDf.groupby('this_trial_type').get_group(0.0)['this_delay']
axes.plot(SDf.index,SDf.values,'.')
axes.set_xlabel('trial #')
axes.set_ylabel('delay')
sns.despine(fig)
fig.tight_layout()

# %%
fig, axes = plt.subplots(figsize=[8,3])
SDf = SessionDf.groupby('this_trial_type').get_group(2.0)['reward_magnitude']
axes.plot(SDf.index,SDf.values,'.')
axes.set_xlabel('trial #')
axes.set_ylabel('reward magnitude')
sns.despine(fig)
fig.tight_layout()


# %%
import numpy as np
import matplotlib.pyplot as plt
%matplotlib qt5
p_des = np.array([0.25, 0.25, 0.25, 0.25])
fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')

# %%
samples = SessionDf['this_trial_type'].values
p_des = np.array([0.55, 0, 0.45])
fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')

# %%
rewards = SessionDf.groupby('this_trial_type').get_group(2.0)['reward_magnitude'].values
mapping = [1, 2.75, 4.5, 6.25, 8]
samples = [mapping.index(reward) for reward in rewards]

p_des = np.array([0.25, 0.167, 0.167, 0.167, 0.25])

fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')


# %% problem inspection
fig, axes = plt.subplots()

for i, delay in enumerate(delays):
    times = SessionDf.groupby('this_delay').get_group(delay)['t_on'].values
    for t in times:
        axes.plot([t,t],[0+i,1+i],color=delay_colors[i])
