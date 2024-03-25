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
animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging")

# %% old 
# folders_file = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/folders"
# folders_file = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/folders"
# with open(folders_file,'r') as fH:
#     folders = [Path(f.strip()) for f in fH.readlines()]
# animal_id = folders[0].parts[-2]
# animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging")

# %% by hand spec ??
# folders = []

# animal_id = folders[0].parts[-2]
# animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging")

# %% read back all analysis
# UnitsDfs = []
# for folder in folders:
#     UnitsDf = pd.read_csv(folder / "UnitsDf.csv")

#     UnitsDfs.append(UnitsDf)
# UnitsDfall = pd.concat(UnitsDfs)

# %%
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-03-10_JJP-05425_10")
# folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/2023-03-10_JJP-05472_10/")
animal_id = folder.parts[-2]

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

# reward_times = bhv.get_events_from_name(LogDf,"REWARD_EVENT")['t'].values
context_switch_time = bhv.get_events_from_name(LogDf,"CONTEXT_SWITCH_EVENT")['t'].values[0]
trial_times = bhv.get_events_from_name(LogDf,"TRIAL_ENTRY_EVENT")['t'].values
trial_labels = SessionDf['this_delay'].values.astype('int32')

trial_times_pre = trial_times[trial_times < context_switch_time]
trial_times_post = trial_times[trial_times > context_switch_time]

trial_labels_pre = SessionDf['this_delay'].values.astype('int32')[trial_times < context_switch_time]
trial_labels_post = SessionDf['this_delay'].values.astype('int32')[trial_times > context_switch_time]

# %% smoothing F?
w = np.ones(5)
w = w / w.sum()
Zs = np.zeros(F.shape)
for i in range(F.shape[1]):
    Zs[:,i] = np.convolve(F[:,i],w,mode='same')

Fs = Signal(Zs, F.t)

# %% pre / post here refers to pre / post manipulation

import copy
F_trial = copy.deepcopy(Fs)
F_pre = copy.deepcopy(Fs)
F_post = copy.deepcopy(Fs)

prepost_trial = (-3000, 11000)

F_trial.reslice(trial_times, *prepost_trial)
F_trial.resort(trial_labels)

F_pre.reslice(trial_times_pre, *prepost_trial)
F_pre.resort(trial_labels_pre)

F_post.reslice(trial_times_post, *prepost_trial)
F_post.resort(trial_labels_post)


"""
 
 ########  ##        #######  ######## 
 ##     ## ##       ##     ##    ##    
 ##     ## ##       ##     ##    ##    
 ########  ##       ##     ##    ##    
 ##        ##       ##     ##    ##    
 ##        ##       ##     ##    ##    
 ##        ########  #######     ##    
 
"""

# %% unit selection
# based on skew and iscell (= min firing rate + good)
unit_sel_ix = np.where(np.logical_and(UnitsDf['skew'] > 1.5,UnitsDf['iscell']))[0]
print("%i cells in selection" % unit_sel_ix.shape[0])

# %%
save = True

for unit_ix in tqdm(unit_sel_ix):
# for unit_ix in [17]:

    # plot
    fig, axes = plt.subplots(figsize=[9.23, 6.0], nrows=3, ncols=5, gridspec_kw=dict(width_ratios=(1, 1, 1, 1, 0.02), height_ratios=(0.5,1,1)))
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
    # ax.set_xlabel('time (ms)')
    # ax.set_ylabel('dF/F (au)')


    # trial average lines, split pre post
    ax = axes[1,:]
    pre_color = 'k'
    post_color = 'r'
    lines = []
    for i, delay in enumerate(delays):
        ax[i].plot(F_pre.t_slice, np.average(F_pre.resorted[delay][:,unit_ix,:],axis=1),color=pre_color, label=delay, lw=1.5)
        try:
            ax[i].plot(F_post.t_slice, np.average(F_post.resorted[delay][:,unit_ix,:],axis=1),color=post_color, label=delay, lw=1.5)
        except KeyError:
            pass
        ax[i].axvline(delay,color='k',lw=1,alpha=0.5,zorder=-1,linestyle=':')

        ax[i].axvspan(0,1000, color='k',lw=0,alpha=0.15,zorder=-1)
        ax[i].set_xlim(*prepost_trial)
        # ax[i].set_xlabel('time (ms)')
        # ax[i].set_ylabel('dF/F (au)')


    # imaging data - aligned on stim
    ax = axes[2,:]
    for i, delay in enumerate(delays):
        try:
            data_delays = [F_pre.resorted[delay][:,unit_ix,:],F_post.resorted[delay][:,unit_ix,:]]
            n_trials_per_delay = [F_pre.resorted[delay].shape[2], F_post.resorted[delay].shape[2]]
        except KeyError:
            data_delays = [F_pre.resorted[delay][:,unit_ix,:]]
            n_trials_per_delay = [F_pre.resorted[delay].shape[2]]
        
        data = np.concatenate(data_delays, axis=1)
        
        extent = (*prepost_trial,0,np.sum(n_trials_per_delay))
        im = ax[i].matshow(data.T, cmap='magma', extent=extent, origin='lower',vmin=-2,vmax=5)
        ax[i].set_aspect('auto')
        ax[i].xaxis.set_ticks_position('bottom')
        ax[i].set_xlabel('time (ms)')
        ax[i].axvline(0,color='w',lw=1,linestyle=":")
        ax[i].set_xticks(axes[1,i].get_xticks())
        ax[i].set_xlim(*prepost_trial)

        # seperators and delay legend bars
        divs = np.cumsum(n_trials_per_delay)
        divs = np.concatenate([[0],divs])
        for div in divs:
            ax[i].axhline(div, color='white',lw=0.5)
        n_delays = delays.shape[0]

        from matplotlib.patches import Rectangle
        if len(n_trials_per_delay) > 1:
            R = Rectangle([prepost_trial[0], divs[0]], 200, n_trials_per_delay[0], color=pre_color, alpha=0.75)
            ax[i].add_patch(R)
            R = Rectangle([prepost_trial[0], divs[1]], 200, n_trials_per_delay[1], color=post_color, alpha=0.75)
            ax[i].add_patch(R)

            # R = Rectangle([prepost_trial[0], divs[i]], 200, n_trials_per_delay[i], color=post_color, alpha=0.75)
            # ax[i].add_patch(R)

        # for i, delay in enumerate(delays):
        #     ax[i].plot([delay, delay], [divs[i], divs[i+1]], color='white',lw=1, alpha=0.75, linestyle=':')

    # labels
    axes[0,0].set_ylabel('F(z)')
    axes[1,0].set_ylabel('F(z)')
    axes[2,0].set_ylabel('trials')

    # deactivating unused axes
    for ax in axes[0,1:]:
        ax.axis('off')
    axes[1,-1].axis('off')

    # colorbar for both imaging plots
    cbar = fig.colorbar(mappable=im, cax=axes[2,4])
    cbar.set_label('F[z]', rotation='vertical')

    sns.despine(fig)
    # fig.tight_layout()
    fig.subplots_adjust(top=0.95,
                        bottom=0.1,
                        left=0.1,
                        right=0.9,
                        hspace=0.2,
                        wspace=0.3)

    # text
    ax = axes[0,1]
    row = UnitsDf.loc[unit_ix]
    info = (animal_id, unit_ix, row['iscell_p'], row['X'], row['Y'], row['D'], 'none')
    ax.set_ylim(-1,0)
    ax.text(0,0,"animal_id: %s\nunit_ix: %s\np_iscell: %.2f\nAP: %i\nML: %i\nDV: %i\nAllen: %s\n" % info, va='top')

    # store
    if save:
        output_folder = Path("/home/georg/data/tmp/sel2")
        os.makedirs(output_folder / 'plots' / 'prepost_traces', exist_ok=True)
        fig.savefig(output_folder / 'plots' / 'prepost_traces' / ('Unit_%i.png' % unit_ix), dpi=600)
        plt.close(fig)

"""
 
 ########  ##          ###    ##    ##  ######   ########   #######  ##     ## ##    ## ########  
 ##     ## ##         ## ##    ##  ##  ##    ##  ##     ## ##     ## ##     ## ###   ## ##     ## 
 ##     ## ##        ##   ##    ####   ##        ##     ## ##     ## ##     ## ####  ## ##     ## 
 ########  ##       ##     ##    ##    ##   #### ########  ##     ## ##     ## ## ## ## ##     ## 
 ##        ##       #########    ##    ##    ##  ##   ##   ##     ## ##     ## ##  #### ##     ## 
 ##        ##       ##     ##    ##    ##    ##  ##    ##  ##     ## ##     ## ##   ### ##     ## 
 ##        ######## ##     ##    ##     ######   ##     ##  #######   #######  ##    ## ########  
 
"""

# %%
delay = 0
# center of gravity
np.sum(F_post.t_slice[:,np.newaxis,np.newaxis] * F_post.resorted[delay][:,unit_sel_ix,:], axis=0) / np.sum(F_post.t_slice)

# %%
np.average(F_post.t_slice[np.argmax(F_post.resorted[delay][:,unit_sel_ix,:], axis=0)],axis=1)


# %%
bins = np.linspace(*prepost_trial, 60)
# bins = np.linspace(-0.1,0.1, 30)
fig, axes = plt.subplots(ncols=4)
for i, delay in enumerate(delays):
    cg_pre = np.average(F_pre.t_slice[np.argmax(F_pre.resorted[delay][:,unit_sel_ix,:], axis=0)],axis=1)
    axes[i].hist(cg_pre, bins=bins, color='k', alpha=0.5)
    if delay in F_post.resorted.keys():
        cg_post = np.average(F_post.t_slice[np.argmax(F_post.resorted[delay][:,unit_sel_ix,:], axis=0)],axis=1)
        axes[i].hist(cg_post, bins=bins, color='r', alpha=0.5)

# %% each cell sub post - pre

bins = np.linspace(-6000,6000,60)
fig, axes = plt.subplots(ncols=3)
for i, delay in enumerate(delays[:-1]):
    cg_pre = np.average(F_pre.t_slice[np.argmax(F_pre.resorted[delay][:,unit_sel_ix,:], axis=0)],axis=1)
    cg_post = np.average(F_post.t_slice[np.argmax(F_post.resorted[delay][:,unit_sel_ix,:], axis=0)],axis=1)
    axes[i].hist(cg_post - cg_pre, bins=bins)
    axes[i].axvline(0,linestyle=':',color='k')

# %%
tvec = F_pre.t_slice
d = F_pre.resorted[delay][:,unit_sel_ix,:][:,0,0] + 10000
fig, axes = plt.subplots()
axes.plot(tvec,d)

axes.axvline(np.sum(d*tvec) / np.sum(d))


# %%
