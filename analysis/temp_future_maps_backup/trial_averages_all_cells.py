# %%
# %load_ext autoreload
# %autoreload 2
%matplotlib qt5
import matplotlib.pyplot as plt
import matplotlib as mpl
from tqdm import tqdm
import numpy as np
from pathlib import Path
import pandas as pd
import sys, os
import seaborn as sns
sys.path.append('/home/georg/code/twop-tools')
import twoplib
sys.path.append('/home/georg/Projects/TaskControl/analysis/temp_future_maps')

sys.path.append('/home/georg/Projects/TaskControl')
from Utils import behavior_analysis_utils as bhv

from my_logging import get_logger
logger = get_logger(level='info')
tqdm_disable = False

from data_structures import Signal


# %%

def get_meta(folder):
    """ potentially replace with JSON in the future """
    with open(folder / 'meta.txt','r') as fH:
        lines = [l.strip() for l in fH.readlines()]
    meta = dict([l.split(' ') for l in lines])
    return meta

def get_imaging_and_bhv_data(folder, signal_fname):
    """ returns dFF and SessionDf """

    # get metadata
    meta = get_meta(folder)

    # get bhv
    bhv_session_folder = animals_folder / animal_id / meta['bhv_session_name']

    # get tvec
    tvec = np.load(bhv_session_folder / "frame_timestamps_corr.npy")
    if "tvec_start" in meta.keys():
        tvec = tvec[ np.int32(meta['tvec_start']):-1] # -1 bc last frame sends trigger but is not saved
    # dFF = np.load(folder / "suite2p" / "plane0" / 'spks.npy').T
    dFF = np.load(folder / "suite2p" / "plane0" / signal_fname)
    stats = np.load(folder / "suite2p" / "plane0" / 'stat.npy', allow_pickle=True)

    # check
    if tvec.shape[0] != dFF.shape[0]:
        print("tvec: %i" % tvec.shape[0])
        print("dFF: %i" % dFF.shape[0])
    else:
        print("all good")

    # FIXME IMPORTANT - this just drops the overhanging frames
    if tvec.shape[0] > dFF.shape[0]:
        print("tvec longer than dFF: %i,%i" % (tvec.shape[0], dFF.shape[0]))
        tvec = tvec[:dFF.shape[0]] 
    if tvec.shape[0] < dFF.shape[0]:
        print("tvec shorter than dFF: %i,%i" % (tvec.shape[0], dFF.shape[0]))
        dFF = dFF[:tvec.shape[0]] 

    # get imaging data and bhv data
    F = Signal(dFF, tvec)
    SessionDf = pd.read_csv(bhv_session_folder / 'SessionDf.csv')

    return F, stats, SessionDf



# %%


"""
 
    ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
   ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
  ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
 ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""
# %% folders

# folders_file = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/folders"
folders_file = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/folders"
with open(folders_file,'r') as fH:
    folders = [Path(f.strip()) for f in fH.readlines()]
animal_id = folders[0].parts[-2]

# %% by hand spec
folders = []

animal_id = folders[0].parts[-2]

# %% 
folder = Path("")

animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging")
animal_id = folder.parts[-2]

# %% read back all analysis
UnitsDfs = []
for folder in folders:
    UnitsDf = pd.read_csv(folder / "UnitsDf.csv")

    UnitsDfs.append(UnitsDf)
UnitsDfall = pd.concat(UnitsDfs)


# %% individual cell example
folder = folders[0]


# %%
F, stats, SessionDf = get_imaging_and_bhv_data(folder, 'Z.npy')
meta = get_meta(folder)

# get UnitsDf
UnitsDf = pd.read_csv(folder / "UnitsDf.csv")

# %% 
bhv_session_folder = animals_folder / animal_id / meta['bhv_session_name']
LogDf = bhv.get_LogDf_from_path(bhv_session_folder / 'arduino_log.txt')

# preprocessing
LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min = 5, t_max=200)
LogDf = bhv.time_slice(LogDf, SessionDf.iloc[0]['t_on'], SessionDf.iloc[-1]['t_off'])

reward_times = bhv.get_events_from_name(LogDf,"REWARD_EVENT")['t'].values
trial_times = bhv.get_events_from_name(LogDf,"TRIAL_ENTRY_EVENT")['t'].values
trial_labels = SessionDf['this_delay'].values.astype('int32')

import copy
F_trial = copy.deepcopy(F)
F_reward = copy.deepcopy(F)

prepost_trial = (-3000, 11000)
prepost_reward = (-2500, 2500)

t_ratio = (prepost_reward[1] - prepost_reward[0]) / (prepost_trial[1] - prepost_trial[0])

F_trial.reslice(trial_times, *prepost_trial)
F_trial.resort(trial_labels)
F_reward.reslice(reward_times, *prepost_reward)
F_reward.resort(trial_labels)

# %%
unit_ix = 5


# %%
for unit_ix in tqdm(unit_sel_ix):
    # plot
    fig, axes = plt.subplots(figsize=[9.23, 9.77], nrows=4, ncols=3, gridspec_kw=dict(width_ratios=(1, t_ratio, 0.02), height_ratios=(1,2,1,1)))
    delay_colors = sns.color_palette('viridis',n_colors=4)
    delays = np.array([0,1500,3000,6000])

    # trial average lines - aligned on stim
    ax = axes[0,0]
    lines = []
    for i, delay in enumerate(delays):
        line, = ax.plot(F_trial.t_slice, np.average(F_trial.resorted[delay][:,unit_ix,:],axis=1),color=delay_colors[i], label=delay, lw=1.5)
        lines.append(line)
        ax.axvline(delay,color='k',lw=1,alpha=0.5,zorder=-1,linestyle=':')
    ax.axvspan(0,1000, color='k',lw=0,alpha=0.15,zorder=-1)
    # ax.legend(loc='upper left')
    ax.set_xlim(*prepost_trial)
    ax.set_xlabel('time (ms)')
    ax.set_ylabel('dF/F (au)')

    # trial average lines - aligned on reward
    ax = axes[0,1]
    for i, delay in enumerate(delays):
        ax.plot(F_reward.t_slice, np.average(F_reward.resorted[delay][:,unit_ix,:],axis=1),color=delay_colors[i], label=delay, lw=1.5)
    ax.axvline(0,color='k',lw=1,alpha=0.5,zorder=-1,linestyle=':')
    ax.set_xlim(*prepost_reward)
    ax.set_xlabel('time (ms)')
    ax.set_ylabel('dF/F (au)')

    # custom legend on thirds
    ax = axes[0,2]
    ax.axis('off')
    ax.legend(lines, delays, title='delays', loc='center left')


    # imaging data - aligned on stim
    ax = axes[1,0]
    data_delays = [F_trial.resorted[delay][:,unit_ix,:] for delay in delays]
    data = np.concatenate(data_delays, axis=1)
    n_trials_per_delay = [d.shape[1] for d in data_delays]
    extent = (*prepost_trial,0,np.sum(n_trials_per_delay))
    im = ax.matshow(data.T, cmap='magma', extent=extent, origin='lower')
    ax.set_aspect('auto')
    ax.xaxis.set_ticks_position('bottom')
    ax.set_xlabel('time (ms)')

    # seperators and delay legend bars
    divs = np.cumsum(n_trials_per_delay)
    divs = np.concatenate([[0],divs])
    for div in divs:
        ax.axhline(div, color='white',lw=0.5)
    n_delays = delays.shape[0]

    from matplotlib.patches import Rectangle
    for i in range(n_delays):
        R = Rectangle([prepost_trial[0], divs[i]], 200, n_trials_per_delay[i], color=delay_colors[i],alpha=0.75)
        ax.add_patch(R)

    for i, delay in enumerate(delays):
        ax.plot([delay, delay], [divs[i], divs[i+1]], color='white',lw=1, alpha=0.75, linestyle=':')

    # imaging data - aligned on reward
    ax = axes[1,1]

    data_rewards = [F_reward.resorted[delay][:,unit_ix,:] for delay in delays]
    data = np.concatenate(data_rewards, axis=1)
    extent = (*prepost_reward,0,np.sum(n_trials_per_delay))
    im = ax.matshow(data.T, cmap='magma', extent=extent, origin='lower')
    ax.set_aspect('auto')
    ax.xaxis.set_ticks_position('bottom')
    ax.set_xlabel('time (ms)')

    ax.axvline(0, color='white',lw=1, alpha=0.75, linestyle=':')

    divs = np.cumsum(n_trials_per_delay)
    divs = np.concatenate([[0],divs])
    for div in divs:
        ax.axhline(div, color='white',lw=0.5)

    from matplotlib.patches import Rectangle
    for i in range(n_delays):
        R = Rectangle([prepost_reward[0], divs[i]], 200, n_trials_per_delay[i], color=delay_colors[i],alpha=0.75)
        ax.add_patch(R)

    ax.set_xticks(axes[0,1].get_xticks())
    ax.set_xlim(*prepost_reward)

    # colorbar for both imaging plots
    cbar = fig.colorbar(mappable=im,cax=axes[1,2])
    cbar.set_label('dF/F (au)', rotation='vertical')

    # store
    output_folder = Path("/home/georg/data/tmp/sel_traces")
    os.makedirs(output_folder / 'plots' / 'traces', exist_ok=True)
    fig.savefig(output_folder / 'plots' / 'traces' / ('Unit_%i.png' % unit_ix), dpi=600)
    plt.close(fig)

###
# LICK RATE
###

def event_rate(LogDf: pd.DataFrame, event_name: str, w: np.ndarray, dt: float):
    """ returns rate of event over the entire session 
    everything in seconds! """
    Df = bhv.get_events_from_name(LogDf, event_name)
    t_start = LogDf['t'].values[0]/1e3
    t_stop = LogDf['t'].values[-1]/1e3
    tvec_session = np.arange(t_start, t_stop, dt) 
    event_rate = calc_rate(Df['t'].values/1e3, tvec_session, w)
    return event_rate, tvec_session

def calc_rate(t_stamps, tvec, w):
    """ everything in [s] so rate turns out as [1/s] """
    ix = np.digitize(t_stamps, tvec) -1 
    rate = np.zeros(tvec.shape[0])
    dt = np.diff(tvec)[0]
    rate[ix] = 1
    return np.convolve(rate, w, mode='same') / dt

from scipy.signal import gaussian
sd = 0.1 # s
dt = 0.005 #
w = gaussian(int(sd/dt * 10), int(sd/dt))
w = w/w.sum()

lick_rate, lick_rate_tvec = event_rate(LogDf, "LICK_EVENT", w, dt=dt)

L_trial = Signal(lick_rate[:,np.newaxis], lick_rate_tvec*1e3)
L_trial.reslice(trial_times, *prepost_trial)
L_trial.resort(trial_labels)
L_reward = Signal(lick_rate[:,np.newaxis], lick_rate_tvec*1e3)
L_reward.reslice(reward_times, *prepost_reward)
L_reward.resort(trial_labels)

### lick rate - trial avg lines - aligned on trial entry
ax = axes[2,0]

lines = []
for i, delay in enumerate(delays):
    line, = ax.plot(L_trial.t_slice, np.average(L_trial.resorted[delay][:,0,:],axis=1),color=delay_colors[i], label=delay, lw=1.5)
    lines.append(line)
    ax.axvline(delay,color='k',lw=1,alpha=0.5,zorder=-1,linestyle=':')
ax.axvspan(0,1000, color='k',lw=0,alpha=0.15,zorder=-1)
# ax.legend(loc='upper left')
ax.set_xlim(*prepost_trial)
ax.set_xlabel('time (ms)')
ax.set_ylabel('lick rate (1/s)')

### lick rate - trial avg lines - aligned on reward
ax = axes[2,1]
for i, delay in enumerate(delays):
    ax.plot(L_reward.t_slice, np.average(L_reward.resorted[delay][:,0,:],axis=1),color=delay_colors[i], label=delay, lw=1.5)
ax.axvline(0,color='k',lw=1,alpha=0.5,zorder=-1,linestyle=':')
ax.set_xlim(*prepost_reward)
ax.set_xlabel('time (ms)')
ax.set_ylabel('lick rate (1/s)')

### lick rate - trial resolved matshow - aligned on trial entry
ax = axes[3,0]
data_delays = [L_trial.resorted[delay][:,0,:] for delay in delays]
data = np.concatenate(data_delays, axis=1)
n_trials_per_delay = [d.shape[1] for d in data_delays]
extent = (*prepost_trial,0,np.sum(n_trials_per_delay))
im = ax.matshow(data.T, cmap='magma', extent=extent, origin='lower')
ax.set_aspect('auto')
ax.xaxis.set_ticks_position('bottom')
ax.set_xlabel('time (ms)')

# seperators and delay legend bars
divs = np.cumsum(n_trials_per_delay)
divs = np.concatenate([[0],divs])
for div in divs:
    ax.axhline(div, color='white',lw=0.5)
n_delays = delays.shape[0]

from matplotlib.patches import Rectangle
for i in range(n_delays):
    R = Rectangle([prepost_trial[0], divs[i]], 200, n_trials_per_delay[i], color=delay_colors[i],alpha=0.75)
    ax.add_patch(R)

for i, delay in enumerate(delays):
    ax.plot([delay, delay], [divs[i], divs[i+1]], color='white',lw=1, alpha=0.75, linestyle=':')

# lick rate - aligned on reward
ax = axes[3,1]

data_rewards = [L_reward.resorted[delay][:,0,:] for delay in delays]
data = np.concatenate(data_rewards, axis=1)
extent = (*prepost_reward,0,np.sum(n_trials_per_delay))
im = ax.matshow(data.T, cmap='magma', extent=extent, origin='lower')
ax.set_aspect('auto')
ax.xaxis.set_ticks_position('bottom')
ax.set_xlabel('time (ms)')

ax.axvline(0, color='white',lw=1, alpha=0.75, linestyle=':')

divs = np.cumsum(n_trials_per_delay)
divs = np.concatenate([[0],divs])
for div in divs:
    ax.axhline(div, color='white',lw=0.5)

from matplotlib.patches import Rectangle
for i in range(n_delays):
    R = Rectangle([prepost_reward[0], divs[i]], 200, n_trials_per_delay[i], color=delay_colors[i],alpha=0.75)
    ax.add_patch(R)

ax.set_xticks(axes[0,1].get_xticks())
ax.set_xlim(*prepost_reward)

# colorbar for both imaging plots
cbar = fig.colorbar(mappable=im,cax=axes[3,2])
cbar.set_label('lick rate [1/s]', rotation='vertical')

# text
ax = axes[2,2]
ax.axis('off')
info = (animal_id, unit_ix, 0.2, 0, 0, 0, 'none')
ax.text(0,0,"animal_id: %s\nunit_ix: %s\np_iscell: %.2f\nAP: %i\nML: %i\nDV: %i\nAllen: %s\n" % info)

# global things
for ax in axes[:-1,:].flatten():
    ax.set_xlabel('')

axes[0,0].set_title('aligned on cue')
axes[0,1].set_title('aligned on reward')
sns.despine(fig)
fig.tight_layout()

# %%
