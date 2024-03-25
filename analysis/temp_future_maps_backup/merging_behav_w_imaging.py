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

def get_reward_time(TrialDf):
    var_name = "reward_collection_time"
    event = "REWARD_COLLECTED_EVENT"
    event = "REWARD_EVENT"
    if event in TrialDf['name'].values:
        try:
            Df = TrialDf.groupby('name').get_group(event)
            var = Df.iloc[0]['t']
        except KeyError:
            var = np.NaN
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)


# %% BEHAVIORAL DATA
# path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-23_12-14-11_twodistributionsv6_GR"
# path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-22_11-21-08_twodistributionsv6_GR"

# short removed
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-24_15-52-50_twodistributionsv6_GR"

# the "bad" animal
path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04308/2022-06-24_13-38-27_twodistributionsv6_GR"


# only first part of long removed 
# path = "/media/georg/storage/shared-paton/georg/Animals_smelling_imaging/JJP-04312/2022-06-25_12-22-17_twodistributionsv6_GR"

# %% the classic preprocessing and slicing 
session_folder = Path(path)

LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min = 5, t_max=200)

session_metrics = (metrics.get_start, metrics.get_stop, get_trial_type,
                   get_delay, get_reward_magnitude, get_reward_time)


SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics, trial_entry_event="TRIAL_ENTRY_EVENT")

t_context_switch = bhv.get_events_from_name(LogDf, "CONTEXT_SWITCH_EVENT")['t'].values[0]
SessionDf['post_manip'] = SessionDf['t_on'] > t_context_switch


# for this session specifically: drop last trial
SessionDf = SessionDf.iloc[:-1]

# %% IMAGING DATA

# short removed 
folder = Path("/media/georg/data/future_temp_maps/2022-06-24_JJP-04312_day4")

# the bad animal
folder = Path("/media/georg/data/future_temp_maps/2022-06-24_JJP-04308_day4")

# only first part of long removed
# folder = Path("/media/georg/data/future_temp_maps/2022-06-25_JJP-04312_day5")
D = np.load(folder / 'merged' / 'dFF_good.npy').T #AAAAAAA

# %% sync
FramesMap = pd.read_csv(folder / 'frames_map.csv')

# uncorrected Trial start times
TrialEntryEvent = bhv.get_events_from_name(LogDf,'TRIAL_ENTRY_EVENT')
n_trials = len(TrialDfs)

# linear clock syncing
from scipy.stats import linregress
a = FramesMap.groupby('frames_ix_merged').get_group(0)['tstamp_si'].values
b = TrialEntryEvent['t'].values
m, b = linregress(a[1:],b)[:2]

# correcting the timestamps from scanimage to arduino time
FramesMap['t'] = m * FramesMap['tstamp_si'] + b

# %% helpers - could be part of caiman_tools
def time_slice(D, tvec, t_start, t_stop, return_ix=False):
    ix = np.where(np.logical_and(tvec > t_start, tvec < t_stop))[0]
    if return_ix:
        return D[ix], ix
    else:
        return D[ix]

def cut_to_min(Ds, dim):
    """ Ds is list of arrays, """
    min_len = np.min([d.shape[dim] for d in Ds])
    Dsc = []
    for i,d in enumerate(Ds):
        Dsc.append(d[:min_len])
    return Dsc

def slice_D(D, tvec, times, pre, post):
    """ helper : slices all traces D  with tvec at times,
    returns Dsc: time x cells x trials (= new slice) """

    Ds = []
    for i,t in enumerate(times):
        Ds.append(time_slice(D, tvec, t+pre, t+post))

    Dsc = cut_to_min(Ds, 0)
    Dsc = np.stack(Dsc, axis=2)
    return Dsc

"""
   ###    ##       ##           ######  ######## ##       ##        ######        ###    ##       ##          ######## ########  ####    ###    ##        ######
  ## ##   ##       ##          ##    ## ##       ##       ##       ##    ##      ## ##   ##       ##             ##    ##     ##  ##    ## ##   ##       ##    ##
 ##   ##  ##       ##          ##       ##       ##       ##       ##           ##   ##  ##       ##             ##    ##     ##  ##   ##   ##  ##       ##
##     ## ##       ##          ##       ######   ##       ##        ######     ##     ## ##       ##             ##    ########   ##  ##     ## ##        ######
######### ##       ##          ##       ##       ##       ##             ##    ######### ##       ##             ##    ##   ##    ##  ######### ##             ##
##     ## ##       ##          ##    ## ##       ##       ##       ##    ##    ##     ## ##       ##             ##    ##    ##   ##  ##     ## ##       ##    ##
##     ## ######## ########     ######  ######## ######## ########  ######     ##     ## ######## ########       ##    ##     ## #### ##     ## ########  ######
"""

# %% plotting all cells all trials
# delays in seperate figures
tvec = FramesMap['t'].values
pre, post = (-2000, 11000)

delays = SessionDf.this_delay.unique()
delays = np.sort(delays)

for delay in delays:
    # trial onset times
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    
    Dsc = slice_D(D, tvec, align_times, pre, post)

    n_frames, n_cells, n_trials = Dsc.shape
    fig, axes = plt.subplots()

    # reorder: stacking all cells
    S = np.concatenate([Dsc[:,i,:] for i in range(n_cells)],axis=1)
    extent = (pre,post,0,n_trials*n_cells)
    # extent = (pre,post,0,n_cells)
    axes.matshow(S.T,vmin=0,vmax=1.0,extent=extent)
    for i in range(n_cells):
        axes.axhline(i*n_trials,color='white',lw=0.4)
    axes.axvline(0,lw=0.3,color='w')
    axes.axvline(delay,lw=0.3,color='w')
    axes.set_yticks([])
    axes.set_aspect('auto')
    axes.set_xlabel('time (ms)')
    axes.xaxis.set_ticks_position('bottom')
    axes.set_title('delay: %i' % delay)
    fig.tight_layout()

# %% interactive flipping through cells
tvec = FramesMap['t'].values
pre, post = (-2000, 11000)

delays = np.sort(SessionDf.this_delay.unique())
n_delays = delays.shape[0]

fig, axes = plt.subplots(nrows=n_delays,sharex=True,sharey=True)
delay_colors = sns.color_palette('viridis',n_colors=n_delays)
cell_ix = 34

lines = []
lines_avg = []
n_trials_ = []

for i,delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape
    n_trials_.append(n_trials)

    tvec_rel = np.arange(pre, post, np.diff(tvec)[0])
    tvec_rel = tvec_rel[:n_frames]

    fig.cell_ix = cell_ix
    
    l = axes[i].plot(tvec_rel, Dsc[:,cell_ix,:], color='k', alpha=0.5, lw=0.5)
    l_avg, = axes[i].plot(tvec_rel, np.average(Dsc[:,cell_ix,:], axis=1), color=delay_colors[i], lw=2, alpha=0.95)
    lines.append(l)
    lines_avg.append(l_avg)

    axes[i].axvspan(0, 1000, color=delay_colors[i], linewidth=0, alpha=0.2)
    axes[i].axvline(delay, lw=2, color='k', linestyle=':')
    axes[i].set_ylim(-0.4, 0.5)
    axes[i].set_ylabel('dF/F')

axes[-1].set_xlabel('time (ms)')
fig.suptitle("cell: %i" % fig.cell_ix)
sns.despine(fig)
fig.tight_layout()

# preslice
Dscs = []
for i,delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    Dsc = slice_D(D, tvec, align_times, pre, post)
    Dscs.append(Dsc)


def on_press(event):
    print('press', event.key)
    if event.key == 'right':
        fig.cell_ix += 1
    if event.key == 'left':
        fig.cell_ix -= 1

    for i in range(n_delays):
        for j in range(n_trials_[i]):
            lines[i][j].set_ydata(Dscs[i][:,fig.cell_ix,j])
            lines_avg[i].set_ydata(np.average(Dscs[i][:,fig.cell_ix,:],axis=1))

    fig.suptitle("cell: %i" % fig.cell_ix)
    fig.canvas.draw()

fig.canvas.mpl_connect('key_press_event', on_press)

# %% plotting all cells all trials, aligned on reward collection
tvec = FramesMap['t'].values
pre, post = (-5000,5000)
fig, axes = plt.subplots(nrows=delays.shape[0],sharex=True)
for i,delay in enumerate(delays):

    # reward_times
    SDf = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)
    align_times = SDf.loc[~pd.isna(SDf['reward_collection_time'].values)]['reward_collection_time']

    Dsc = slice_D(D, tvec, align_times, pre, post)

    n_frames, n_cells, n_trials = Dsc.shape
    fig, axes = plt.subplots()

    # reorder: stacking all cells
    S = np.concatenate([Dsc[:,i,:] for i in range(n_cells)],axis=1)
    extent = (pre,post,0,n_trials*n_cells)
    axes.matshow(S.T,vmin=0,vmax=1.5,extent=extent)
    for i in range(n_cells):
        axes.axhline(i*n_trials,color='white',lw=0.25)
    axes.axvline(0,lw=0.25,color='w')
    axes.set_aspect('auto')
    fig.tight_layout()


# %% plotting all cells, trial averages

# order by activity during delay
delay = delays[2]
align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
Dsc = slice_D(D, tvec, align_times, 0, delay)

# order by peak time during delay
order = np.argsort(np.argmax(np.average(Dsc,2),axis=0))

# order by max activity during delay
order = np.argsort(np.max(np.average(Dsc,2),0))


# %% joes PCA order thing
pca = PCA()
pca.fit(D.T)
S = pca.transform(D.T)
order = np.argsort(np.arctan(S[:,1] / S[:,0]))

# plt.matshow(np.average(Dsc,2).T[order,:], vmin=0, vmax=1.0)

# %%
tvec = FramesMap['t'].values
pre, post = (-2000, 11000)

delays = SessionDf.this_delay.unique()
delays = np.sort(delays)

fig, axes = plt.subplots(nrows=delays.shape[0],sharex=True)
for i,delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    Dsc = slice_D(D, tvec, align_times, pre, post)

    # reorder
    Dsc = Dsc[:,order,:]

    n_frames, n_cells, n_trials = Dsc.shape

    # average over trials
    S = np.average(Dsc,axis=2)
    
    extent = (pre,post,0,n_cells)
    axes[i].matshow(S.T,vmin=0,vmax=0.5,extent=extent)
    axes[i].axvline(0,lw=0.25,color='w')
    axes[i].axvline(delay,lw=0.25,color='w')
    axes[i].set_aspect('auto')
    axes[i].xaxis.set_ticks_position('bottom')
    axes[i].set_ylabel('cell')
axes[-1].set_xlabel('times (ms)')

fig.tight_layout()
fig.subplots_adjust(hspace=0.05)














# %% dimensionality reduction, avg trajectories, delays on rows
from sklearn.decomposition import PCA
pca = PCA()
pca.fit(D)
n_comps = np.sum(np.cumsum(pca.explained_variance_ratio_) < 0.95)

# fig, axes = plt.subplots()
# axes.plot(np.cumsum(pca.explained_variance_ratio_))

# refit only up to n_comps
# pca = PCA(n_components=n_comps)
# pca.fit(D)

delays = DelaysDf.this_delay.unique()
delays = np.sort(delays)

fig, axes = plt.subplots(nrows=delays.shape[0],sharex=True)

for j, delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    Dsc_pre = slice_D(D, tvec, align_times, pre, post)
    
    # the average trajectory
    t_avg = pca.transform(np.average(Dsc,axis=2))

    # plot
    extent = (pre,post,0,n_cells)
    axes[j].matshow(t_avg.T, cmap='PiYG', extent=extent,vmin=-.2,vmax=.2)
    axes[j].axvline(0,lw=0.25,color='k')
    axes[j].axvline(delay,lw=0.25,color='k')
    axes[j].set_aspect('auto')

fig.tight_layout()

# %% to det up later stuff: split session by some trial number and then do the contrast
# SessionDf['post_manip'] = False
# SessionDf.loc[120:,'post_manip'] = True

# %% difference trial averages of cells
delays = SessionDf.this_delay.unique()
delays = np.sort(delays)
delays = delays[1:]
tvec = FramesMap['t'].values

fig, axes = plt.subplots(nrows=delays.shape[0],sharex=True)
for j, delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=False)['t_on'].values
    Dsc_pre = slice_D(D, tvec, align_times, pre, post)

    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=True)['t_on'].values
    Dsc_post = slice_D(D, tvec, align_times, pre, post)

    S = np.average(Dsc_post,axis=2) - np.average(Dsc_pre,axis=2)
    
    extent = (pre,post,0,n_cells)
    axes[j].matshow(S.T, cmap='PiYG', extent=extent,vmin=-.2,vmax=.2)
    axes[j].axvline(0,lw=0.25,color='w')
    axes[j].axvline(delay,lw=0.25,color='w')
    axes[j].set_aspect('auto')
    axes[j].xaxis.set_ticks_position('bottom')
    axes[j].set_ylabel("delay:%i" % delay)

# %% difference in trial average trajectories
fig, axes = plt.subplots(nrows=delays.shape[0],sharex=True)
delays = SessionDf.this_delay.unique()
delays = np.sort(delays)
delays = delays[1:]
tvec = FramesMap['t'].values

for j, delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=False)['t_on'].values
    Dsc_pre = slice_D(D, tvec, align_times, pre, post)

    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=True)['t_on'].values
    Dsc_post = slice_D(D, tvec, align_times, pre, post)

    # the average trajectory
    t_avg_pre = pca.transform(np.average(Dsc_pre,axis=2))
    t_avg_post = pca.transform(np.average(Dsc_post,axis=2))
    t_avg = t_avg_post - t_avg_pre

    # plot
    extent = (pre,post,0,n_cells)
    axes[j].matshow(t_avg.T, cmap='PiYG', extent=extent,vmin=-.2,vmax=.2)
    axes[j].axvline(0,lw=0.25,color='k')
    axes[j].axvline(delay,lw=0.25,color='k')
    axes[j].set_aspect('auto')











"""
########   ######     ###
##     ## ##    ##   ## ##
##     ## ##        ##   ##
########  ##       ##     ##
##        ##       #########
##        ##    ## ##     ##
##         ######  ##     ##
"""

# %% setting up PCA
# needs to be run for all further PCA plots here
import seaborn as sns
from sklearn.decomposition import PCA
from scipy import signal

delays = np.sort(SessionDf.this_delay.unique())
n_delays = delays.shape[0]
delay_colors = sns.color_palette('viridis', n_colors=n_delays)
   
# vanilla PCA
pca = PCA()
pca.fit(D) 

# 
# n_comps = np.sum(np.cumsum(pca.explained_variance_ratio_) < 0.95)
# n_comps = 3
# pca = PCA(n_components=n_comps)
# pca.fit(D)

def plot_trajectory(ax, T, line_kwargs, smoothing=False, sd=10, raw_scatter=False, arrows=False, arrow_spacing=5):
    """ helper to plot trajectories in a 3d axis. T is (t x dim) """
    if smoothing is False:
        ax.plot3D(T[:,0], T[:,1], T[:,2], **line_kwargs)
        if arrows is True:
            for i in range(T.shape[0]-1):
                if i % arrow_spacing == 0:
                    P1 = T[i,dims]
                    P2 = T[i+1,dims]
                    dP = P2-P1
                    l = np.sqrt(np.sum(dP**2))
                    ax.quiver(P1[0], P1[1],P1[2] ,dP[0], dP[1], dP[2], length=1,normalize=False, color=delay_colors[j], lw=1)

    else:
        w = signal.gaussian(sd,sd*5)
        w = w / w.sum()
        T_s = np.zeros(T.shape)
        for i in range(T.shape[1]):
            T_s[:,i] = np.convolve(T[:,i],w,mode='same')

        ax.plot3D(T_s[:,0], T_s[:,1], T_s[:,2], **line_kwargs)

        if arrows is True:
            for i in range(T_s.shape[0]-1):
                if i % arrow_spacing == 0:
                    P1 = T_s[i,dims]
                    P2 = T_s[i+1,dims]
                    dP = P2-P1
                    # l = np.sqrt(np.sum(dP**2))
                    ax.quiver(P1[0], P1[1],P1[2] ,dP[0], dP[1], dP[2], length=1, normalize=False, color=line_kwargs['color'], lw=line_kwargs['lw'], alpha=line_kwargs['alpha'])

        if raw_scatter:
            ax.scatter(T[:,0], T[:,1], T[:,2], color=line_kwargs['color'], s=5, lw=0)

    return ax

# %% 3d plot of PCAs, all delays in one plot, no pre post separation
fig = plt.figure()
ax = plt.axes(projection='3d')
pre, post = (0,6000)

for j, delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values

    Dsc = slice_D(D, tvec, align_times, pre, post)
    
    # the average trajectory
    t_avg = pca.transform(np.average(Dsc,axis=2))

    # Data for a three-dimensional line
    dims = [0,1,2]
    # dims = [2,3,4]

    line_kwargs = dict(color=delay_colors[j], lw=2, alpha=0.75)
    ax = plot_trajectory(ax, t_avg[:,dims], line_kwargs, smoothing=True, raw_scatter=True, arrows=False)
    ax.set_axis_off()

fig.tight_layout()

# %% plotting traces of individual trials plus trial average, delays on subplots
fig = plt.figure()
ax = []
for i in range(n_delays):
    ax.append(fig.add_subplot(1, n_delays, i+1, projection='3d'))

dims = [0,1,2]

for j, delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values

    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape

    for i in range(n_trials):
        # individual trial trajectory
        t = pca.transform(Dsc[:,:,i])

        # Data for a three-dimensional line
        line_kwargs = dict(color=delay_colors[j], lw=1, alpha=0.75)
        ax[j] = plot_trajectory(ax[j], t[:,dims], line_kwargs, smoothing=True, raw_scatter=False, arrows=False)

    # the average trajectory
    t_avg = pca.transform(np.average(Dsc,axis=2))
    line_kwargs['color'] = 'k'
    line_kwargs['lw'] = 2
    ax[j] = plot_trajectory(ax[j], t_avg[:,dims], line_kwargs, smoothing=True, raw_scatter=False, arrows=False)

# %% plotting single trial trajectories colored by split
fig = plt.figure()
ax = []
for i in range(n_delays):
    ax.append(fig.add_subplot(1, n_delays, i+1, projection='3d'))

dims = [0,1,2]

for j, delay in enumerate(delays):
    # PRE
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=False)['t_on'].values

    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape

    for i in range(n_trials):
        # individual trial trajectory
        t = pca.transform(Dsc[:,:,i])

        # Data for a three-dimensional line
        line_kwargs = dict(color='k', lw=1, alpha=0.75)
        ax[j] = plot_trajectory(ax[j], t[:,dims], line_kwargs, smoothing=True, raw_scatter=False, arrows=False)


    # POST
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=True)['t_on'].values

    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape

    for i in range(n_trials):
        # individual trial trajectory
        t = pca.transform(Dsc[:,:,i])

        # Data for a three-dimensional line
        line_kwargs = dict(color='r', lw=1, alpha=0.75)
        ax[j] = plot_trajectory(ax[j], t[:,dims], line_kwargs, smoothing=True, raw_scatter=False, arrows=False)


# %% train PCA on PRE only, then project pre and post into one plot
delays = np.sort(SessionDf.this_delay.unique())
delays = delays[1:]
n_delays = delays.shape[0]
delay_colors = sns.color_palette('viridis', n_colors=n_delays)

t_context_switch = bhv.get_events_from_name(LogDf, "CONTEXT_SWITCH_EVENT")['t'].values[0]
ix = np.argmin((tvec - t_context_switch)**2)

# vanilla PCA
pca = PCA()
pca.fit(D[:,:ix])

dims = [0,1,2]

fig = plt.figure()
ax = []
for i in range(n_delays):
    ax.append(fig.add_subplot(1, n_delays, i+1, projection='3d'))

for j, delay in enumerate(delays):
    # PRE
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=False)['t_on'].values
    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape
    t = pca.transform(np.average(Dsc,2))

    # Data for a three-dimensional line
    line_kwargs = dict(color='k', lw=1, alpha=0.75)
    ax[j] = plot_trajectory(ax[j], t[:,dims], line_kwargs, smoothing=True, raw_scatter=False, arrows=True)

    # POST
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=True)['t_on'].values
    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape
    t = pca.transform(np.average(Dsc,2))

    # Data for a three-dimensional line
    line_kwargs = dict(color='r', lw=1, alpha=0.75)
    ax[j] = plot_trajectory(ax[j], t[:,dims], line_kwargs, smoothing=True, raw_scatter=False, arrows=False)

    # deco
    ax[j].set_title("delay:%i"%delay)
    ax[j].set_axis_off()


"""
 ######   ##       ##     ##
##    ##  ##       ###   ###
##        ##       #### ####
##   #### ##       ## ### ##
##    ##  ##       ##     ##
##    ##  ##       ##     ##
 ######   ######## ##     ##
"""

# %%
os.chdir('/home/georg/Projects/LR-RRR')
import RRRlib as rrr
os.chdir(folder)

# %% helper
def bin_times(tstamps, tvec):
    """ turns timestamps into binarized matrix
    probably horribly inefficient """
    T = np.zeros(tvec.shape[0])
    for t in tstamps:
        ix = np.argmin((tvec - t)**2)
        T[ix] = 1
    return T

# %% time continuous regressors
tvec = FramesMap['t'].values
treg_names = []
tregs = []

# %% lick rate of entire session
from scipy import signal
lick_times = bhv.get_events_from_name(LogDf,"LICK_EVENT")['t'].values
t_start = np.min(LogDf['t'].values)
t_stop = np.max(LogDf['t'].values)
lick_tvec = np.arange(t_start, t_stop, 1)
f = np.zeros(lick_tvec.shape[0])
f[lick_times.astype('int32')-int(t_start)] = 1
sd = 100
w = signal.gaussian(sd*10, sd)
w = w / w.sum()
lick_rate = np.convolve(f,w,mode='same')*1e3 # do get to a rate is licks/s

# interpolate to frames
tvec = FramesMap['t'].values
lick_rate_ip = np.interp(tvec, lick_tvec, lick_rate)

treg_names.append("lick_rate")
tregs.append(lick_rate_ip)

# %% plot
# fig, axes = plt.subplots()
# axes.plot(lick_tvec, f)
# axes.plot(lick_tvec, lick_rate)
# axes.plot(tvec, lick_rate_ip,'.')
# reward_times = bhv.get_events_from_name(LogDf, "REWARD_COLLECTED_EVENT")['t']
# for t in reward_times:
#     axes.axvline(t,color='blue')

# # %% plot like above to verify
# tvec = FramesMap['t'].values
# pre, post = (-2000, 11000)

# delays = np.sort(SessionDf.this_delay.unique())
# n_delays = delays.shape[0]

# fig, axes = plt.subplots(nrows=n_delays)
# for i,delay in enumerate(delays):
#     # trial onset times
#     align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    
#     Dsc = slice_D(lick_rate_ip[:,np.newaxis], tvec, align_times, pre, post)

#     S = Dsc[:,0,:]
#     extent = (pre,post,0,n_trials)
#     axes[i].matshow(S.T,vmin=0,vmax=10,extent=extent,origin='lower')
#     axes[i].axvline(0,lw=0.25,color='w')
#     axes[i].axvline(delay,lw=0.25,color='w')
#     axes[i].set_aspect('auto')
#     fig.tight_layout()

# works

# %% lagged regressors
tvec = FramesMap['t'].values
lagreg_names = []
lagregs = []

# odors
odor_ids = LogDf.groupby('var').get_group('this_odor')['value'].values
# odor_unique = np.sort(np.unique(odor_ids))
odors_unique = [0,1,2,3] # hardcode to overwrite present odor 4 stim (manual error?)

odor_times = bhv.get_events_from_name(LogDf,"ODOR_ON")['t'].values
for i, odor in enumerate(odors_unique):
    lagreg_names.append("odor_%i_on"%odor)
    times = odor_times[odor_ids == odor]
    lagregs.append(bin_times(times,tvec))
    
# odor_times = bhv.get_events_from_name(LogDf,"ODOR_OFF")['t'].values
# for i, odor in enumerate(odors_unique):
#     lagreg_names.append("odor_%i_off"%odor)
#     times = odor_times[odor_ids == odor]
#     lagregs.append(bin_times(times,tvec))

# reward
reward_times = bhv.get_events_from_name(LogDf,"REWARD_EVENT")['t'].values
lagreg_names.append("reward")
lagregs.append(bin_times(reward_times,tvec))

# licks
lick_times = bhv.get_events_from_name(LogDf,"LICK_EVENT")['t'].values
lagreg_names.append("licks")
lagregs.append(bin_times(lick_times,tvec))

def expand_reg(reg, n_lags):
    lags = np.linspace(-n_lags/2,n_lags/2 - 1,n_lags).astype('int32')
    rolls = []
    for lag in lags:
        rolls.append(np.roll(reg,lag))
    reg_ex = np.stack(rolls).T
    return reg_ex

n_lags = 250 # pre and post?
X_lagreg = [expand_reg(reg, n_lags) for reg in lagregs]

# %% exponential decay, gamma style, time since last odor on
tvec = FramesMap['t'].values

n_gammas = 20
gammas = np.linspace(.8,.99,n_gammas)
n_taps = 500
g = np.zeros((n_taps,n_gammas))
g[0,:] = gammas
for i in range(1,n_taps):
    g[i,:] = g[i-1,:] * gammas

g = g / np.sum(g,axis=0)[np.newaxis,:]

# %% exploring alternative time basis functions
n_basis = 20
n_taps = 250
mus = np.linspace(10,8000,n_basis)
sds = np.linspace(200,600,n_basis)
from scipy.stats.distributions import norm
dt = np.diff(FramesMap['t'].values)[0]
tvec_basis = np.arange(0,n_taps*dt,dt)
g = np.zeros((n_taps,n_basis))
for i in range(n_basis):
    g[:,i] = norm.pdf(tvec_basis,loc=mus[i],scale=sds[i])

g = g / np.sum(g,axis=0)[np.newaxis,:]
fig, axes = plt.subplots()
for i in range(n_basis):
    axes.plot(tvec_basis, g[:,i])

# %% exclude odor that is removed halfway through the session from the set
# of regressors!

if not "CONTEXT_SWITCH_EVENT" in LogDf['name'].values:
    print("no context switch in this session!")

ix = LogDf.groupby('name').get_group("CONTEXT_SWITCH_EVENT").index[0]
delays_before = pd.unique(LogDf.loc[:ix].groupby('var').get_group('this_delay').value)
delays_after = pd.unique(LogDf.loc[ix:].groupby('var').get_group('this_delay').value)
exclude = [delay for delay in delays_before if delay not in delays_after][0]
exclude_ix = list(delays).index(exclude)

odor_ids = LogDf.groupby('var').get_group('this_odor')['value'].values
odor_times = bhv.get_events_from_name(LogDf,"ODOR_ON")['t'].values
times = odor_times[odor_ids != exclude_ix]
valid_stim_on = bin_times(times, tvec)

# convolve
G = np.repeat(valid_stim_on[:,np.newaxis],n_gammas,1)
for j in range(n_gammas):
    G[:,j] = np.convolve(G[:,j], g[:,j],mode='same')

# %%
# plt.matshow(G)
# plt.gca().set_aspect('auto')

# %% combine regressors and make model matrix
X_lr = np.concatenate(X_lagreg, axis=1)
X_intercept = np.ones((X_lr.shape[0],1))
X = np.concatenate([X_intercept, X_lr, G],axis=1)

# %% run LM
# l = rrr.xval_ridge_reg_lambda(D, X, K=5) # 49.159
B_hat = rrr.LM(D,X,lam=42.94)

# %%
fig, axes = plt.subplots()
axes.matshow(B_hat)
axes.set_aspect('auto')

# %% regs split
# lagregs are right after intercept
n_lagreg_inds = len(lagregs) * n_lags

dt = np.diff(tvec)[0]
offs = 1
regs_split = np.split(B_hat[offs:n_lagreg_inds+offs,:], len(lagregs), axis=0)
fig, axes = plt.subplots(ncols=len(lagregs))
s = 0.1
lags = np.linspace(-n_lags/2, n_lags/2 - 1,n_lags).astype('int32')
extent = [lags[0]*dt/1e3,lags[-1]*dt/1e3,0,1]
for i in range(len(lagregs)):
    axes[i].matshow(regs_split[i].T,vmin=-s,vmax=s,cmap='PiYG',extent=extent)
    axes[i].set_aspect('auto')
    axes[i].set_title(lagreg_names[i])
    axes[i].set_yticks([])
    axes[i].axvline(0,linestyle=':',color='k',lw=1)


# %% model inspect
Y_hat = X @ B_hat
start_ix = 70000
stop_ix = start_ix + 2000

d = D[start_ix:stop_ix,:]
y = Y_hat[start_ix:stop_ix,:]

n_cells = d.shape[1]
fig, axes = plt.subplots()
y_scl = 1
for i in range(n_cells):
    axes.plot(d[:,i]*y_scl+i,lw=1,color='k')
    axes.plot(y[:,i]*y_scl+i,lw=2,alpha=0.8,color='r')

# %% all gammas
B_gs = B_hat[-n_gammas:,:]

order = np.argsort(np.sum(B_gs,axis=0))

fig, axes = plt.subplots(figsize=[6,2.5])
s = 0.05
axes.matshow(B_gs[:,order],vmin=-s,vmax=s,cmap='PiYG')
axes.set_aspect('auto')
axes.set_title('full session')
fig.tight_layout()

# %% MODEL RUN w seperation by context switch
t_context_switch = bhv.get_events_from_name(LogDf, "CONTEXT_SWITCH_EVENT")['t'].values[0]
ix = np.argmin((tvec - t_context_switch)**2)
lam = 42.94
B_hat_pre = rrr.LM(D[:ix],X[:ix],lam=lam)
B_hat_post = rrr.LM(D[ix:],X[ix:],lam=lam)

# %%
fig, axes = plt.subplots()

B_gs_pre = B_hat_pre[-n_gammas:,:]
B_gs_post = B_hat_post[-n_gammas:,:]

B_gs_diff = B_gs_post - B_gs_pre

# order = np.argsort(np.sum(B_gs_pre,axis=0))
# order = np.argsort(np.sum(B_gs_pre[:n_gammas], axis=0) - np.sum(B_gs_pre[n_gammas:]))
ms = []
n_cells = B_gs_pre.shape[1]
for i in range(n_cells):
    m = linregress(gammas,B_gs_diff[:,i])[0]
    ms.append(m)

order = np.argsort(ms)

fig, axes = plt.subplots(nrows=3,figsize=[8,3.5],sharex=True)
s = 0.05

labels = ['pre','post','diff']
for i, B in enumerate([B_gs_pre, B_gs_post, B_gs_diff]):
    # if i == 2:
    #     s = 0.01
    axes[i].matshow(B[:,order], cmap='PiYG', vmin=-s,vmax=s)
    axes[i].set_aspect('auto')
    axes[i].set_ylabel(labels[i])
    # if i != 2:
    #     axes[i].set_xticklabels([])

axes[i].xaxis.set_ticks_position('bottom')

fig.suptitle('long removed')
# fig.suptitle('short removed')

# %%
cell_id = 6
basis_pre = np.sum(B_gs_pre[:,cell_id] * g, axis=1)
basis_post = np.sum(B_gs_post[:,cell_id] * g, axis=1)

fig, axes = plt.subplots()
axes.plot(basis_pre,'k')
axes.plot(basis_post,'r')



# %% plotting the average of pre and post
tvec = FramesMap['t'].values
pre, post = (-2000, 11000)

delays = np.sort(SessionDf.this_delay.unique())
n_delays = delays.shape[0]

removed_ix = 0

fig, axes = plt.subplots(nrows=n_delays,sharex=True,sharey=True)
delay_colors = sns.color_palette('viridis',n_colors=n_delays)
cell_ix = 20

for i,delay in enumerate(delays):
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=False)['t_on'].values
    Dsc = slice_D(D, tvec, align_times, pre, post)
    n_frames, n_cells, n_trials = Dsc.shape

    tvec_rel = np.arange(pre, post, np.diff(tvec)[0])
    tvec_rel = tvec_rel[:n_frames]
    axes[i].plot(tvec_rel, np.average(Dsc[:,cell_ix,:], axis=1), color='k', lw=2, alpha=0.95)

for i,delay in enumerate(delays):
    if delay != delays[removed_ix]:
        align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=True)['t_on'].values
        Dsc = slice_D(D, tvec, align_times, pre, post)
        n_frames, n_cells, n_trials = Dsc.shape

        tvec_rel = np.arange(pre, post, np.diff(tvec)[0])
        tvec_rel = tvec_rel[:n_frames]
        axes[i].plot(tvec_rel, np.average(Dsc[:,cell_ix,:], axis=1), color='r', lw=2, alpha=0.95)

    axes[i].axvspan(0, 1000, color=delay_colors[i], linewidth=0, alpha=0.2)
    axes[i].axvline(delay, lw=2, color='k', linestyle=':')
    axes[i].set_ylim(-0.4, 0.5)
    axes[i].set_ylabel('dF/F')

axes[-1].set_xlabel('time (ms)')
fig.suptitle("cell: %i" % cell_ix)
sns.despine(fig)
fig.tight_layout()







"""
######## #### ##     ## ######## ##      ##    ###    ########  ########
   ##     ##  ###   ### ##       ##  ##  ##   ## ##   ##     ## ##     ##
   ##     ##  #### #### ##       ##  ##  ##  ##   ##  ##     ## ##     ##
   ##     ##  ## ### ## ######   ##  ##  ## ##     ## ########  ########
   ##     ##  ##     ## ##       ##  ##  ## ######### ##   ##   ##
   ##     ##  ##     ## ##       ##  ##  ## ##     ## ##    ##  ##
   ##    #### ##     ## ########  ###  ###  ##     ## ##     ## ##
"""

# %% in PC space
t_context_switch = bhv.get_events_from_name(LogDf, "CONTEXT_SWITCH_EVENT")['t'].values[0]
ix = np.argmin((tvec - t_context_switch)**2)

# vanilla PCA
pca = PCA()
pca.fit(D[:,:ix])

# delays in seperate figures
tvec = FramesMap['t'].values

delays = SessionDf.this_delay.unique()
delays = np.sort(delays)

delays = delays[1:] # no zero delay

T_pre = []
T_post = []
for delay in delays:
    # trial onset times
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=False)['t_on'].values
    pre, post = (0, delay)
    Dsc = slice_D(D, tvec, align_times, pre, post)
    # T_pre.append(pca.transform(np.average(Dsc,2)))
    T_pre.append(np.average(Dsc,2))

     # trial onset times
    align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay, post_manip=True)['t_on'].values
    pre, post = (0, delay)
    Dsc = slice_D(D, tvec, align_times, pre, post)
    # T_post.append(pca.transform(np.average(Dsc,2)))
    T_post.append(np.average(Dsc,2))

# %%
max_len = T_pre[-1].shape[0]
n_cells = T_pre[-1].shape[1]

T_pre_ip = []
T_post_ip = []
for i in range(delays.shape[0]):
    T_ip = np.stack([np.interp(np.linspace(0,1,max_len), np.linspace(0,1,T_pre[i].shape[0]), T_pre[i][:,j]) for j in range(n_cells)]).T
    T_pre_ip.append(T_ip)

    T_ip = np.stack([np.interp(np.linspace(0,1,max_len), np.linspace(0,1,T_post[i].shape[0]), T_post[i][:,j]) for j in range(n_cells)]).T
    T_post_ip.append(T_ip)

fig, axes = plt.subplots(ncols=delays.shape[0])
s = 0.1
order = np.argsort(np.sum(T_post_ip[j] - T_pre_ip[j],axis=0))
j = 2
for i in range(delays.shape[0]):
    axes[i].matshow(T_post_ip[i].T[order,:] - T_pre_ip[i].T[order,:], vmin=-s,vmax=s,cmap='PiYG')

# %%


"""
########  ##     ## ##     ##
##     ## ##     ## ##     ##
##     ## ##     ## ##     ##
########  ######### ##     ##
##     ## ##     ##  ##   ##
##     ## ##     ##   ## ##
########  ##     ##    ###
"""


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
delays = DelaysDf.this_delay.unique()
delays = np.sort(delays)
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



















# %% LEFTOVERS


# %%
d = np.average(Dsc,axis=2)
d = Dsc[:,30,:]

fig, axes = plt.subplots()

tvec = np.linspace(pre, post, d.shape[0]) # does this guarantiee?
yscl = 5
# stacked traces plot: first dim is x, second dim is y
for i in range(d.shape[1])[::-1]:
    axes.fill_between(tvec, np.zeros(d.shape[0]) * yscl + i, d[:,i] * yscl + i, alpha=1, color='white',zorder=-i,lw=0.7)
    axes.plot(tvec, d[:,i] * yscl + i, color='k', lw=0.5, alpha=0.8,zorder=-i)

import seaborn as sns
sns.despine(fig)
fig.tight_layout()

# %%

    # bvec = np.logical_and(FramesMap['t'].values > t+pre, FramesMap['t'].values < t+post)
    # tvec = FramesMap.iloc[bvec]['t']
    # ix = FramesMap.iloc[bvec].index
    # if return_ix == False:
    #     return D[:,ix], tvec
    # else:
    #     return D[:,ix], tvec, ix, bvec

DelaysDf = SessionDf[SessionDf['this_trial_type'] == 0.0]
pre, post = (-2000,11000)
delays = DelaysDf.this_delay.unique()
delays = np.sort(delays)
delay = delays[0]

Df = DelaysDf.groupby('this_delay').get_group(delay)
Ds = []
for i,t in enumerate(Df['t_on'].values):
    Ds.append(time_slice(D, t, pre,post, FramesMap)[0])

# cut to minimum len

min_len = np.min([d.shape[1] for d in Ds])
for d in Ds:
    d = d[:,:min_len]

Dsc = []
for d in Ds:
    Dsc.append(d[:,:min_len])

Dsc = np.stack(Dsc,axis=2)
Dsca = np.average(Dsc,axis=2)


tvec = np.linspace(pre,post,Dsca.shape[1])

# stacked y plot
from copy import copy
fig, axes = plt.subplots() 
nCells = D.shape[0]
nFrames = D.shape[1]
fs = 30.03
dt = 1/fs
# tvec = all_tvec[bvec]
# tvec = np.arange(nFrames) * dt
d = Dsca
a  = 5
yscl = a/d.max() # for dff

# tvec = tvec[ix]

for i in range(nCells)[::-1]:
    axes.fill_between(tvec, np.zeros(d.shape[1]) * yscl + i, d[i,:] * yscl + i, alpha=1, color='white',zorder=-i,lw=0.7)
    axes.plot(tvec, d[i,:] * yscl + i, color='k', lw=0.5, alpha=0.8,zorder=-i)

import seaborn as sns
sns.despine(fig)
fig.tight_layout()


