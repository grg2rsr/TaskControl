# %% imports 
%matplotlib qt5
%load_ext autoreload
%autoreload 2

import sys
from pathlib import Path
from tqdm import tqdm

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle
import seaborn as sns

import scipy as sp
import numpy as np
import pandas as pd
import cv2

sys.path.append('..')
from Utils import behavior_analysis_utils as bhv
# from Utils import dlc_analysis_utils as dlc
from Utils.metrics import *
from Utils.sync import Syncer
from Utils import utils

colors = dict(success="#72E043", 
              reward="#3CE1FA", 
              correct="#72E043", 
              incorrect="#F56057", 
              premature="#9D5DF0", 
              missed="#F7D379",
              left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95))


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

# folder = Path("/media/georg/htcondor/shared-paton/georg/mesoscope_testings/behavior/2021-08-25_13-51-12_learn_to_choose_v2")
# folder = Path("/media/georg/htcondor/shared-paton/georg/mesoscope_testings/behavior/2021-08-25_13-59-39_learn_to_choose_v2")
folder = Path("/media/georg/htcondor/shared-paton/georg/mesoscope_testings/behavior/2021-08-25_14-38-04_learn_to_choose_v2")
log_path = folder / 'arduino_log.txt'

LogDf = bhv.get_LogDf_from_path(log_path)
animal = utils.Animal(log_path.parent)
date = log_path.parent.stem.split('_')[0]
plot_dir = Path('/home/georg/Desktop/plots')

# %% Syncer
from Utils import sync
cam_sync_event = sync.parse_cam_sync(folder / 'bonsai_frame_stamps.csv')
lc_sync_event = sync.parse_harp_sync(folder / 'bonsai_harp_sync.csv')
arduino_sync_event = sync.get_arduino_sync(folder / 'arduino_log.txt')

Sync = Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
# Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
Sync.data['cam'] = cam_sync_event['t'].values # used for what?
# Sync.sync('arduino','dlc')
Sync.sync('arduino','cam')

# %% get frames per file
fnames = np.sort([fname for fname in os.listdir() if fname.endswith('.tif')])
from skimage.io import imread
nFrames_per_file = []
fnames = fnames
for fname in tqdm(fnames):
    D = imread(fname)
    nFrames_per_file.append(D.shape[0])

np.save('Frames_per_file.npy',np.array(nFrames_per_file))

# %% reconstructing frame times
nFrames_per_file = np.load('Frames_per_file.npy')
spans = bhv.get_spans_from_names(LogDf,"TRIAL_ENTRY_EVENT","FRAME_EVENT")

recorded_frame_events = LogDf[LogDf['name'] == 'FRAME_EVENT']['t'].values
# known frame rate
fr = 3.06188
dt = 1/fr

for i,row in spans.iterrows():
    inf_times = row['t_off'] + np.arange(nFrames_per_file[i+1]) * dt * 1000
    Df = pd.DataFrame(zip(['FRAME_INF_EVENT'] * (nFrames_per_file[i+1]),inf_times),columns=['name','t'])
    LogDf = LogDf.append(Df)

LogDf = LogDf.sort_values('t')
# %% get dFF data
folder = "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_2/reshaped"
os.chdir(folder)
dFF = np.load('dFF_good.npy')

# %%
# plt.plot(np.diff(frame_events))
# Sync.data['scope'] = frame_events[:850]
# Sync.sync('arduino','scope')

# %% make SessionDf - slice into trials
def get_SessionDf(LogDf, metrics, trial_entry_event="TRIAL_AVAILABLE_STATE", trial_exit_event="ITI_STATE"):

    TrialSpans = bhv.get_spans_from_names(LogDf, trial_entry_event, trial_exit_event)

    TrialDfs = []
    for i, row in tqdm(TrialSpans.iterrows(),position=0, leave=True):
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))
    
    SessionDf = bhv.parse_trials(TrialDfs, metrics)
    return SessionDf, TrialDfs

from Utils import metrics
metrics = (metrics.get_start, metrics.get_stop, metrics.has_choice, metrics.get_outcome)

def groupby_dict(Df, Dict):
    return Df.groupby(list(Dict.keys())).get_group(tuple(Dict.values()))

SessionDf, TrialDfs = get_SessionDf(LogDf, metrics, trial_entry_event="TRIAL_ENTRY_EVENT", trial_exit_event="ITI_STATE")
SessionDf['exclude'] = False
SessionDf['is_premature'] = SessionDf['outcome'] == 'premature'

# %%
events = LogDf['name'].unique()
events = list(events)
events.remove(np.nan)
events = ['TRIAL_ENTRY_EVENT','FRAME_EVENT','FRAME_INF_EVENT']
events = ['REACH_LEFT_ON','REACH_RIGHT_ON','REWARD_COLLECTED_EVENT']
events = np.array(events)
fig, axes = plt.subplots()
colors = dict(zip(events,sns.color_palette(palette='tab20',n_colors=events.shape[0])))
for i,event in enumerate(events):
    Df = LogDf.groupby('name').get_group(event)
    for j,row in Df.iterrows():
        axes.plot([row['t']/1000,row['t']/1000],[0+i,1+i],color=colors[event])

from matplotlib.pyplot import Line2D
handles = [Line2D([],[],color=color) for event,color in colors.items()]
plt.legend(handles, [event for event,color in colors.items()],loc='upper left', bbox_to_anchor=(1.0, 1.0 ))
fig.tight_layout()
# %%
LogDf.groupby('name').get_group('FRAME_EVENT').shape[0]
LogDf.groupby('name').get_group('FRAME_INF_EVENT').shape[0]
# -> works, assign idex
nFrames = LogDf.groupby('name').get_group('FRAME_INF_EVENT').shape[0]
offset = dFF.shape[1] - nFrames
LogDf.loc[LogDf['name'] == 'FRAME_INF_EVENT','var'] = np.arange(offset, nFrames+offset)

# %% test slicing
w = (-3000, 3000)
event = 'REACH_RIGHT_ON'
times = LogDf.groupby('name').get_group(event)['t']
ix_ts = []
for t in times.values:
    Df = bhv.time_slice(LogDf,t+w[0],t+w[1])
    try:
        frame_ix = Df.groupby('name').get_group('FRAME_INF_EVENT')['var'].values
        frame_times = Df.groupby('name').get_group('FRAME_INF_EVENT')['t'].values - t
        ix_ts.append((frame_ix.astype('int32'),frame_times))
    except:
        pass

# %% sorting by kmeans
from sklearn.cluster import KMeans
k = 4 # todo find a way to find k
clust = KMeans(n_clusters=k)
clust.fit(dFF)
labels = clust.labels_
order = np.argsort(labels)
dFF = dFF[order,:]

# %% stacked y plot
ysep = 0.1
fig, axes = plt.subplots() 
nCells = dFF.shape[0]
nFrames = dFF.shape[1]
fs = 3.03
dt = 1/fs
tvec = np.arange(nFrames) * dt
from copy import copy
d = copy(dFF)
d = d[order,:]
for i in range(nCells)[::-1]:
    axes.fill_between(tvec, np.zeros(dFF.shape[1]) +i*ysep, d[i,:]+i*ysep, alpha=1, color='white',zorder=-i,lw=0.8)
    axes.plot(tvec, d[i,:] + i*ysep, color='k', lw=1, alpha=0.8,zorder=-i)

import seaborn as sns
sns.despine(fig)
fig.tight_layout()

# %%
fig, axes = plt.subplots(ncols=times.shape[0],sharey=True,sharex=True)
# for i, (frame_ix, frame_times) in enumerate(ix_ts):
for i in range(len(ix_ts)):
    # print(ix_ts[i][0].shape[0])
    axes[i].matshow(dFF[:,ix_ts[i][0]])
    axes[i].set_aspect('auto')

# fig.tight_layout()
fig.subplots_adjust(hspace=0.1)

# %% PCA stuff
from sklearn.decomposition import PCA
n_comp = 5
pca = PCA(n_components=n_comp)
fig, axes = plt.subplots(n_comp,n_comp,sharex=True,sharey=True)

for i, (frame_ix, frame_times) in enumerate(ix_ts):
    D = dFF[:,frame_ix]
    pca.fit(D)
    # exp_var = np.cumsum(pca.explained_variance_ratio_)
    # print(exp_var)

    T = pca.fit_transform(D.T)
    for i in range(n_comp):
        for j in range(n_comp):
            # axes[i,j].plot(T[:,i],T[:,j],'.',markersize=5,alpha=.1)
            axes[i,j].plot(T[:,i],T[:,j],lw=1)
            # x = np.average(T[:,i])
            # y = np.average(T[:,j])
            # axes[i,j].plot(x,y,'.',markersize=6,color='r')

import seaborn as sns
sns.despine(fig)
# %%
