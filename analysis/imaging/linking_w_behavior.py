# %% imports 
%matplotlib qt5
%load_ext autoreload
%autoreload 2

import sys, os
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

sys.path.append('/home/georg/code/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import dlc_analysis_utils as dlc
import Utils.metrics as metrics
from Utils.sync import Syncer

colors = dict(success="#72E043", 
              reward="#3CE1FA", 
              correct="#72E043", 
              incorrect="#F56057", 
              premature="#9D5DF0", 
              missed="#F7D379",
              left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95))

# %% read all three data sources
bhv_path = "/media/georg/data/mesoscope/first data/with behavior/behavior/2021-08-25_14-38-04_learn_to_choose_v2" # this is square3
# bhv_path = "/media/georg/data/mesoscope/first data/with behavior/behavior/2021-08-25_13-59-39_learn_to_choose_v2" # this is square2
# bhv_path = "/media/georg/data/mesoscope/first data/with behavior/behavior/2021-08-25_13-51-12_learn_to_choose_v2" # square 1 
# bhv_path = "/media/georg/data/mesoscope/first data/with behavior/behavior/2021-08-25_12-38-40_learn_to_choose_v2"
session_folder = Path(bhv_path)
os.chdir(session_folder)

### DeepLabCut data
# h5_path = session_folder / [fname for fname in os.listdir(session_folder) if fname.endswith('filtered.h5')][0]
h5_path = session_folder / [fname for fname in os.listdir(session_folder) if fname.endswith('.h5')][0]
DlcDf = dlc.read_dlc_h5(h5_path)

# getting all dlc body parts
bodyparts = sp.unique([j[0] for j in DlcDf.columns[1:]])

### Camera data
video_path = session_folder / "bonsai_video.avi"
Vid = dlc.read_video(str(video_path))

### Arduino data
log_path = session_folder / 'arduino_log.txt'
LogDf = bhv.get_LogDf_from_path(log_path)

# # %% inspect the behavioral session
# for name in LogDf.name.unique():
#     if name is not np.nan:
#         Df = LogDf.groupby('name').get_group(name)

#     print(name, Df.shape[0])

### LoadCell Data
# LoadCellDf = bhv.parse_bonsai_LoadCellData(session_folder / 'bonsai_LoadCellData.csv')

### Imaging data
D = np.load("/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/D_all_splits.npy")
coords = np.load("/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/coords_all_splits.npy")
good_inds = np.load("/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/good_inds_all_splits.npy")
D = D[good_inds]
coords = coords[good_inds]
nCells, nFrames = D.shape

# Syncer
from Utils import sync
cam_sync_event, Cam_SyncDf = sync.parse_cam_sync(session_folder / 'bonsai_frame_stamps.csv', offset=1, return_full=True)
# lc_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv')
arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

Sync = Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
# Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
Sync.data['cam'] = cam_sync_event['t'].values
Sync.sync('arduino','cam')

DlcDf['t_cam'] = Cam_SyncDf['t']
Sync.data['frames'] = cam_sync_event.index.values
Sync.sync('frames','cam')

# Sync.eval_plot()
# Sync = Syncer()
# Sync.data['arduino'] = arduino_sync_event['t'].values
# # Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
# Sync.data['cam'] = cam_sync_event['t'].values # used for what?
# Sync.sync('arduino','dlc')
# Sync.sync('arduino','cam')

DlcDf['t'] = Sync.convert(DlcDf['t_cam'], 'cam', 'arduino')

# %% get frames per file
# os.chdir("/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/split_0")
# fnames = np.sort([fname for fname in os.listdir() if fname.endswith('.tif')])
# from skimage.io import imread
# nFrames_per_file = []
# fnames = fnames
# for fname in tqdm(fnames):
#     I = imread(fname)
#     nFrames_per_file.append(I.shape[0])

# np.save('Frames_per_file.npy',np.array(nFrames_per_file))

nFrames_per_file = np.load('/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/Frames_per_file.npy')
# spans = bhv.get_spans_from_names(LogDf,"TRIAL_ENTRY_EVENT","FRAME_EVENT")
# recorded_frame_events = LogDf[LogDf['name'] == 'FRAME_EVENT']['t'].values

# known frame rate
fr = 3.06231 # from the meta.txt
# fr = 3.06188 # the other old? value
dt = 1/fr

# %%
Frame_Events = bhv.get_events_from_name(LogDf, "FRAME_EVENT")
print(Frame_Events.shape[0])
print(nFrames)
t = Frame_Events['t'].values

fig, axes = plt.subplots()
axes.plot(np.diff(t),'o')

miss_ix = np.where(np.diff(t) > (dt * 1500))[0] # candidate missing frames - 1% too long dt
print(miss_ix.shape[0])

# %%
for ix in miss_ix:
    Df = pd.DataFrame([['FRAME_INF_EVENT', t[ix] + dt*1000]], columns=['name','t'])
    LogDf = LogDf.append(Df)
LogDf = LogDf.sort_values('t')

# %% combine the two to a new event
Df = pd.concat([bhv.get_events_from_name(LogDf, "FRAME_EVENT"),bhv.get_events_from_name(LogDf, "FRAME_INF_EVENT")],0)
Df['name'] = 'FRAMEC_EVENT'
Df = Df.sort_values('t')
LogDf = pd.concat([LogDf,Df])
LogDf = LogDf.sort_values('t')

# %%
# hacky - identify the too short ones
Framec_Events = bhv.get_events_from_name(LogDf, "FRAMEC_EVENT")
t = Framec_Events['t'].values
extra_ix = np.where(np.diff(t) < (dt * 990))[0] # candidate missing frames - 1% too long dt
all_ix = np.ones(t.shape[0])
all_ix[extra_ix] = 0

new_t = t[all_ix.astype('bool')]
Df = pd.DataFrame(zip(['FRAMECC_EVENT'] * new_t.shape[0], new_t), columns = ['name','t'])
LogDf = pd.concat([LogDf,Df])
LogDf = LogDf.sort_values('t')

# Framec_Events.iloc[extra_ix[1]]
# LogDf = LogDf.drop(extra_ix)

# %% plot again
Framecc_Events = bhv.get_events_from_name(LogDf, "FRAMECC_EVENT")
t = Framecc_Events['t'].values
plt.plot(np.diff(t),'o')

# now it fits but probalby has errors
# Sync.data['imaging'] = np.arange(len(t))

# %% Dlc processing
# speed
for i,bp in enumerate(tqdm(bodyparts)):
    Vxy = sp.diff(DlcDf[bp][['x','y']].values,axis=0) / DlcDf['t'][:-1].values[:,sp.newaxis]
    V = sp.sqrt(sp.sum(Vxy**2,axis=1)) # euclid vector norm
    V = V / sp.diff(DlcDf['t'].values) # -> to speed
    V = sp.concatenate([[sp.nan],V]) # pad first to nan (speed undefined)
    DlcDf[(bp,'v')] = V

# %% analysis of too fast movements
# fig, axes = plt.subplots()
# for bp in bodyparts:
#     V = DlcDf[(bp,'v')]
#     tvec = DlcDf['t']
#     axes.plot(tvec, V, label=[bp])

# sides = ['left','right']
# for side in sides:
#     reach_times = LogDf.groupby('name').get_group("REACH_%s_ON" % side.upper())['t'].values
#     for t in reach_times:
#         axes.axvline(t, color=colors[side], alpha=0.5, lw=1)

# axes.legend()

# %% speed filter
V_thresh = 0.000005
for i,bp in enumerate(tqdm(bodyparts)):
    V = DlcDf[(bp,'v')]
    DlcDf[(bp,'likelihood')][V > V_thresh] = 0
    
    # Vxy = sp.diff(DlcDf[bp][['x','y']].values,axis=0) / DlcDf['t'][:-1].values[:,sp.newaxis]
    # V = sp.sqrt(sp.sum(Vxy**2,axis=1)) # euclid vector norm
    # V = V / sp.diff(DlcDf['t'].values) # -> to speed
    # V = sp.concatenate([[sp.nan],V]) # pad first to nan (speed undefined)
    # DlcDf[(bp,'v')] = V

# %% DLC preprocessing
# replace low confidence prediction with interpolated
p = 0.999
for bp in tqdm(bodyparts):
    good_inds = DlcDf[bp]['likelihood'].values > p
    ix = DlcDf[bp].loc[good_inds].index

    bad_inds = DlcDf[bp]['likelihood'].values < p
    bix = DlcDf[bp].loc[bad_inds].index

    x = DlcDf[bp].loc[good_inds]['x'].values
    interp = sp.interpolate.interp1d(ix, x, fill_value='extrapolate')
    DlcDf[(bp,'x')].loc[bix] = interp(bix)

    y = DlcDf[bp].loc[good_inds]['y'].values
    interp = sp.interpolate.interp1d(ix, y, fill_value='extrapolate')
    DlcDf[(bp,'y')].loc[bix] = interp(bix)

    V = DlcDf[bp].loc[good_inds]['v'].values
    interp = sp.interpolate.interp1d(ix, V, fill_value='extrapolate')
    DlcDf[(bp,'v')].loc[bix] = interp(bix)

# %%
def get_frame_for_time(t, t_frames):
    # get the closest frames, indices and times
    ix = np.argmin((t_frames - t)**2)
    return ix,  t_frames[ix]

def get_frame_for_times(ts, t_frames):
    L = [get_frame_for_time(t, t_frames) for t in ts]
    frame_ix = [l[0] for l in L]
    frame_times = [l[1] for l in L]
    return frame_ix, frame_times

# %% getting reach times from the video rather than the arduino events
spout_left = (376, 344)
spout_right = (246, 347)

th = 100
dist, good_inds = dlc.calc_dist_bp_point(DlcDf, 'PAW_R', spout_left)

# filter repeated 
event_ix = np.where((np.diff((dist < th))))
event_times = DlcDf['t'].values[event_ix]
t_block = 5000
good_inds = np.concatenate([[True],np.diff(event_times) > t_block])
event_times_left = event_times[good_inds]

# manual removal of the first
# event_times_left = event_times_left[3:]

dist, good_inds = dlc.calc_dist_bp_point(DlcDf, 'PAW_R', spout_right)

# filter repeated 
event_ix = np.where((np.diff((dist < th))))
event_times = DlcDf['t'].values[event_ix]
t_block = 5000
good_inds = np.concatenate([[True],np.diff(event_times) > t_block])
event_times_right = event_times[good_inds]

# manual removal of the first
# event_times_right = event_times_right[2:]

fig, axes = plt.subplots()
for t in event_times_left:
    axes.axvline(t,color='r',alpha=0.5)
for t in event_times_right:
    axes.axvline(t,color='b',alpha=0.5)

# %% filter by hand
good_ix = [3,4,5,6]
event_times_right = [event_times_right[i] for i in good_ix]

# %% and now for those, find the movement onset time
fig , axes = plt.subplots()
for t in event_times_right:
    v = bhv.time_slice(DlcDf, t-2000, t+2000)['PAW_R','y'].values
    axes.plot(np.linspace(-2000,2000,v.shape[0]),v)

# %% 
""" based on event, slice imaging data and interpolate to cells activity to common time base"""
def slice_interp(LogDf, event_times, D, pre, post, N):
    frame_times = bhv.get_events_from_name(LogDf, "FRAMECC_EVENT")['t'].values
    frame_ix = np.arange(nFrames)

    Spans = []
    data = []
    data_times = []

    for t in event_times:
        Spans.append(bhv.time_slice(LogDf, t+pre, t+post))
        ix = np.logical_and(frame_times > t+pre, frame_times < t+post)
        data.append(D[:,frame_ix[ix]])
        data_times.append(frame_times[ix]-t)

    # interpolate to common timebase
    cell_avgs = []
    cell_stds = []
    for cell in tqdm(range(nCells)):
        data_interp = []
        for i in range(len(data)):
            x = np.linspace(pre, post, N)
            xp = data_times[i]
            fp = data[i][cell,:]
            try:
                f_interp = np.interp(x, xp, fp)
                data_interp.append(f_interp)
            except ValueError:
                pass

        data_interp = np.array(data_interp)
        cell_avgs.append(np.average(data_interp,axis=0))
        cell_stds.append(np.std(data_interp,axis=0))

    cell_avgs = np.array(cell_avgs)
    cell_stds = np.array(cell_stds)

    return cell_avgs, cell_stds, data, data_times

# %%
def peak_sort(M, axis=0):
    order = np.argsort(np.argmax(M, axis=axis))
    return order

def kmeans_sort(M, k, axis=0):
    from sklearn.cluster import KMeans
    clust = KMeans(n_clusters=k)
    if axis==0:
        clust.fit(M.T)
    if axis==1:
        clust.fit(M)
    labels = clust.labels_
    order = np.argsort(labels)
    return order

def kmeans_sort_full(M, k, axis=0):
    from sklearn.cluster import KMeans
    clust = KMeans(n_clusters=k)
    if axis==0:
        clust.fit(M.T)
    if axis==1:
        clust.fit(M)
    labels = clust.labels_
    order = np.argsort(labels)
    return order, labels

# def kmeans_sort(M, k, axis=0):
    # from sklearn.cluster import KMeans

# %%
# from sklearn.cluster import KMeans
# """ time on feature axis (and in sklearn shape is (n_samples, n_features) """
# M = cell_avgs
# k = 10
# clust = KMeans(n_clusters = k)
# clust.fit(M)

# labels = clust.labels_
# order = np.argsort(labels)
# # order labels according to group max along time
# #for label in labels:

# plt.matshow(cell_avgs[order,:])

# # %%
# avgs = []
# for label in np.unique(labels):
#     avgs.append(np.average(M[labels == label,:], axis=0))
# clust_order = np.argsort(np.argmax(np.array(avgs), axis=1))
# order = []
# for label in clust_order:
#     order.append((np.where(labels == label)[0]))
# order = np.concatenate(order)


# %% deal with reaching bouts - first reach
# event_name = "REACH_LEFT_ON"
# t_block = 5000
# def filter_to_bout_start(event_name, t_block):
#     event_times = bhv.get_events_from_name(LogDf, event_name)['t'].values
#     good_inds = np.concatenate([[True],np.diff(event_times) > t_block])
#     return event_times[good_inds]

# event_times = filter_to_bout_start(event_name, t_block)

# %%
pre, post = -5000, 0
N = 400
# cell_avgs_l, cell_stds_l, data_l, data_times_l = slice_interp(LogDf, event_times_left, D, pre, post, N)
cell_avgs_r, cell_stds_r, data_r, data_times_r = slice_interp(LogDf, event_times_right, D, pre, post, N)

# %%
fig, axes = plt.subplots(ncols=2)
axes[0].matshow(cell_avgs_l)
axes[1].matshow(cell_avgs_r)
for ax in axes:
    ax.set_aspect('auto')


# %% for one side only again

# %% for l and r
gkw = dict(height_ratios=(0.03, 1))
fig, axes = plt.subplots(ncols=1, nrows=2, gridspec_kw=gkw,figsize=[9,9])

kw_bar = dict(orientation="horizontal",label="", shrink=0.8)
# kw_bar_diff = dict(orientation="horizontal",label="", shrink=0.8)

kw_im = dict(vmin=0, vmax=0.2, cmap='viridis', extent=(pre/1e3,post/1e3,0,nCells))
# kw_im_diff = dict(vmin=-0.05, vmax=0.05,cmap='PiYG', extent=(pre/1e3,post/1e3,0,nCells))

order = kmeans_sort(cell_avgs_r, 8, 1)
# order = np.argsort(coords[:,1])

# im = axes[1,0].matshow(cell_avgs_l[order], **kw_im)
# fig.colorbar(im, cax=axes[0,0], **kw_bar)
axes[0,0].set_title('reach to left')
im = axes[1,1].matshow(cell_avgs_r[order], **kwargs)
fig.colorbar(im, cax=axes[0,1], **kw_bar)
axes[0,1].set_title('reach to right')
im = axes[1,2].matshow(cell_avgs_l[order] - cell_avgs_r[order], **kwargs_diff)
fig.colorbar(im, cax=axes[0,2], **kw_bar)
axes[0,2].set_title('left - right')

axes[1,0].set_ylabel('ROI')

for ax in axes[1,:].flatten():
    ax.set_aspect('auto')
    ax.set_xlabel('time (s)')
    ax.xaxis.set_ticks_position('bottom')

fig.tight_layout()
fig.savefig("/home/georg/Desktop/plots for labmeeting/avg_responses.png", dpi=600)


# %% for l and r
gkw = dict(height_ratios=(0.03, 1))
fig, axes = plt.subplots(ncols=3, nrows=2, gridspec_kw=gkw,figsize=[9,9])

kw_bar = dict(orientation="horizontal",label="", shrink=0.8)
kw_bar_diff = dict(orientation="horizontal",label="", shrink=0.8)

kw_im = dict(vmin=0, vmax=0.2, cmap='viridis', extent=(pre/1e3,post/1e3,0,nCells))
kw_im_diff = dict(vmin=-0.05, vmax=0.05,cmap='PiYG', extent=(pre/1e3,post/1e3,0,nCells))

order = kmeans_sort(cell_avgs_l, 8, 1)
# order = np.argsort(coords[:,1])

im = axes[1,0].matshow(cell_avgs_l[order], **kw_im)
fig.colorbar(im, cax=axes[0,0], **kw_bar)
axes[0,0].set_title('reach to left')
im = axes[1,1].matshow(cell_avgs_r[order], **kwargs)
fig.colorbar(im, cax=axes[0,1], **kw_bar)
axes[0,1].set_title('reach to right')
im = axes[1,2].matshow(cell_avgs_l[order] - cell_avgs_r[order], **kwargs_diff)
fig.colorbar(im, cax=axes[0,2], **kw_bar)
axes[0,2].set_title('left - right')

axes[1,0].set_ylabel('ROI')

for ax in axes[1,:].flatten():
    ax.set_aspect('auto')
    ax.set_xlabel('time (s)')
    ax.xaxis.set_ticks_position('bottom')

fig.tight_layout()
fig.savefig("/home/georg/Desktop/plots for labmeeting/avg_responses.png", dpi=600)
# %%
# fig, axes = plt.subplots()
# kwargs = dict(vmin=0, vmax=0.2,cmap='viridis')
# # normalize
# # cell_avgs = cell_avgs / np.max(cell_avgs, axis=1)[:,np.newaxis]
# order = kmeans_sort(cell_avgs, 8, 1)
# axes.matshow(cell_avgs[order], **kwargs)
# axes.set_aspect('auto')

# %% single cell

cell = order[263]
fig, axes = plt.subplots(ncols=2,sharex=True, sharey=True)
yzoom = 10
for i in range(len(data_l))[::-1]:
    axes[0].fill_between(data_times_l[i] / 1e3, np.zeros(data_times_l[i].shape[0]), data_l[i][cell,:] * yzoom+i, alpha=0.75, color='white',zorder=-i,lw=0.7)
    axes[0].plot(data_times_l[i] / 1e3, data_l[i][cell,:] * yzoom + i, color='k', alpha=0.8,zorder=-i)

for i in range(len(data_r))[::-1]:
    axes[1].fill_between(data_times_r[i] / 1e3, np.zeros(data_times_r[i].shape[0]), data_r[i][cell,:] * yzoom+i, alpha=0.75, color='white',zorder=-i,lw=0.7)
    axes[1].plot(data_times_r[i] / 1e3, data_r[i][cell,:] * yzoom + i, color='k', alpha=0.8,zorder=-i)    

for ax in axes:
    ax.set_xlabel('time (s)')

axes[0].set_ylabel('reach #')

sns.despine(fig)
fig.tight_layout()








# %% trajectories

# %% PCA stuff
from sklearn.decomposition import PCA
n_comp = 3
pca = PCA(n_components=n_comp)
fig, axes = plt.subplots(n_comp,n_comp,sharex=True,sharey=True)

pre, post = -2000, 2000
t_frames = LogDf.groupby('name').get_group('FRAMECC_EVENT')['t'].values
# for i, (frame_ix, frame_times) in enumerate(ix_ts):
for t in event_times:
    frame_ix, frame_times = get_frame_for_times((t+pre,t+post), t_frames)
    frame_ix = np.array(range(*frame_ix))
    d = D[:,frame_ix]
    pca.fit(d)
    # exp_var = np.cumsum(pca.explained_variance_ratio_)
    # print(exp_var)

    T = pca.fit_transform(d.T)
    for i in range(n_comp):
        for j in range(n_comp):
            # axes[i,j].plot(T[:,i],T[:,j],'.',markersize=5,alpha=.1)
            # axes[i,j].plot(T[:,i],T[:,j],lw=1)
            colorline(T[:,i],T[:,j], axes=axes[i,j], cmap='gnuplot')
            # axes[i,j].plot(,lw=1)
            # x = np.average(T[:,i])
            # y = np.average(T[:,j])
            # axes[i,j].plot(x,y,'.',markersize=6,color='r')

for ax in axes.flatten():
    ax.set_aspect('equal')
    ax.set_xlim(-1,1)
    ax.set_ylim(-1,1)

import seaborn as sns
sns.despine(fig)

# %% plot line with colors

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.collections as mcoll
import matplotlib.path as mpath

def colorline(
    x, y, z=None, cmap=plt.get_cmap('copper'), norm=plt.Normalize(0.0, 1.0),
        linewidth=1, alpha=1.0, axes=None):
    """
    http://nbviewer.ipython.org/github/dpsanders/matplotlib-examples/blob/master/colorline.ipynb
    http://matplotlib.org/examples/pylab_examples/multicolored_line.html
    Plot a colored line with coordinates x and y
    Optionally specify colors in the array z
    Optionally specify a colormap, a norm function and a line width
    """

    # Default colors equally spaced on [0,1]:
    if z is None:
        z = np.linspace(0.0, 1.0, len(x))

    # Special case if a single number:
    if not hasattr(z, "__iter__"):  # to check for numerical input -- this is a hack
        z = np.array([z])

    z = np.asarray(z)

    segments = make_segments(x, y)
    lc = mcoll.LineCollection(segments, array=z, cmap=cmap, norm=norm,
                              linewidth=linewidth, alpha=alpha)

    # ax = plt.gca()
    axes.add_collection(lc)

    return lc


def make_segments(x, y):
    """
    Create list of line segments from x and y coordinates, in the correct format
    for LineCollection: an array of the form numlines x (points per line) x 2 (x
    and y) array
    """

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    return segments

# N = 10
# np.random.seed(101)
# x = np.random.rand(N)
# y = np.random.rand(N)
# fig, ax = plt.subplots()

# path = mpath.Path(np.column_stack([x, y]))
# verts = path.interpolated(steps=3).vertices
# x, y = verts[:, 0], verts[:, 1]
# z = np.linspace(0, 1, len(x))
# colorline(x, y, z, cmap=plt.get_cmap('jet'), linewidth=2)

# plt.show()







"""
 
 ##       ##     ## 
 ##       ###   ### 
 ##       #### #### 
 ##       ## ### ## 
 ##       ##     ## 
 ##       ##     ## 
 ######## ##     ## 
 
"""

# %% from here on - looking at new stuff - linking paw pos to neural data
xr = DlcDf['PAW_R']['x'].values
yr = DlcDf['PAW_R']['y'].values
vr = DlcDf['PAW_R']['v'].values
# axes.plot(x,y,alpha=0.5)

xl = DlcDf['PAW_L']['x'].values
yl = DlcDf['PAW_L']['y'].values
vl = DlcDf['PAW_L']['v'].values
# axes.plot(x,y,alpha=0.5)

X = np.stack([xr,yr,vr,xl,yl,vl], axis=1)

# %% center X
X = (X - np.average(X,axis=0)) / np.std(X,axis=0)

# %% frame times
scope_frame_times = LogDf.groupby('name').get_group('FRAMECC_EVENT')['t'].values
cam_frame_ix = Sync.convert(frame_times,'arduino','frames')

X = X[cam_frame_ix,:]
Y = D.T

B_hat = LM(Y,X)
Y_hat = X @ B_hat
# %%
fig, axes = plt.subplots()
axes.matshow(B_hat)
axes.set_aspect('auto')

# %%
var = 1
pc = np.percentile(B_hat[var,:], (99))
binds = B_hat[var,:] > pc
print(np.sum(inds))
inds = np.where(binds)[0]

fig, axes = plt.subplots(nrows=2,sharex=True,gridspec_kw=dict(height_ratios=(0.5,1)))

axes[0].plot(scope_frame_times / 1e3, X[:,var], color=colors['right'])

yzoom = 5

for i, ix in enumerate(inds):
    axes[1].fill_between(scope_frame_times / 1e3, np.zeros(frame_times.shape[0]), D[ix,:] * yzoom+i, alpha=1.0, color='white',zorder=-i,lw=0.0)
    axes[1].plot(scope_frame_times / 1e3, D[ix,:] * yzoom + i, color='k', alpha=0.95, lw=0.5, zorder=-i)    
    axes[1].plot(scope_frame_times / 1e3, Y_hat[:,ix] * yzoom + i, color='r', alpha=0.95, lw=1.0, zorder=-i)    

axes[0].set_ylabel('right paw, y-pos')
axes[1].set_ylabel('cell')
axes[1].set_xlabel('time (s)')
sns.despine(fig)

# adding rewards
rew_coll_events = LogDf.groupby('name').get_group('REWARD_COLLECTED_EVENT')['t'].values
m = [1,3,4,16,23]
rew_times = [rew_coll_events[i] for i in m]
for t in rew_times:
    for ax in axes:
        ax.axvline(t/1e3,color=colors['reward'])


# %%
fig, axes = plt.subplots(ncols=2)
axes[0].matshow(cell_avgs_l)
axes[1].matshow(cell_avgs_r)
for ax in axes:
    ax.set_aspect('auto')




# %%
"""
 
 ########  ######## ##      ##    ###    ########  ########   ######  
 ##     ## ##       ##  ##  ##   ## ##   ##     ## ##     ## ##    ## 
 ##     ## ##       ##  ##  ##  ##   ##  ##     ## ##     ## ##       
 ########  ######   ##  ##  ## ##     ## ########  ##     ##  ######  
 ##   ##   ##       ##  ##  ## ######### ##   ##   ##     ##       ## 
 ##    ##  ##       ##  ##  ## ##     ## ##    ##  ##     ## ##    ## 
 ##     ## ########  ###  ###  ##     ## ##     ## ########   ######  
 
"""

# %% check them
for i, t in enumerate(rew_coll_events):
    fig, axes = plt.subplots()
    frame_ix = Sync.convert(t,'arduino','frames')
    frame = dlc.get_frame(Vid, frame_ix)
    dlc.plot_frame(frame, axes=axes)
    axes.set_title(i)

# %% manually got them
m = [1,3,4,16,23]
rew_times = [rew_coll_events[i] for i in m]

# %%
fig, axes = plt.subplots()
axes.matshow(np.average(I_all, axis=0))
axes.plot(coords[inds,0], coords[inds,1],'o',color='k')

# %%
pre, post = -5000, 5000
N = 400
cell_avgs, cell_stds, data, data_times = slice_interp(LogDf, rew_times, D, pre, post, N)

kw_bar = dict(orientation="vertical", label="", shrink=0.8)
kw_im = dict(vmin=0, vmax=0.2, cmap='viridis', extent=(pre/1e3, post/1e3, nCells, 0))

fig, axes = plt.subplots(ncols=2, gridspec_kw=dict(width_ratios=(1,0.05)), figsize=[4,8])
order, labels = kmeans_sort_full(cell_avgs, 8, 1)

im = axes[0].matshow(cell_avgs[order], **kw_im)
fig.colorbar(im, cax=axes[1], **kw_bar)

axes[0].set_ylabel('ROI')
axes[0].axvline(color='red',alpha=0.5,lw=0.5)

axes[0].set_aspect('auto')
axes[0].set_xlabel('time (s)')
axes[0].xaxis.set_ticks_position('bottom')

fig.tight_layout()
# fig.savefig("/home/georg/Desktop/plots for labmeeting/avg_rew_responses.png", dpi=600)

# %% kmeans sort continued
colors = sns.color_palette('tab10',n_colors=k)
fig, axes = plt.subplots(sharex=True, sharey=True, nrows = k, figsize=[3,8])
# fig, axes = plt.subplots(sharex=True, sharey=True, nrows = k, gridspec_kw=dict(height_ratios=[np.sum(labels==i) for i in range(k)]))

for i in range(k):
    ix = np.where(labels == i)[0]
    axes[i].matshow(cell_avgs[ix,:], **kw_im)
    axes[i].set_aspect('auto')

# plt.subplots_adjust(hspace=0.05)
axes[-1].set_xlabel('time (s)')
axes[-1].xaxis.set_ticks_position('bottom')

for i,ax in enumerate(axes):
    ax.set_yticks([])

    # for child in ax.get_children():
    #     if isinstance(child, mpl.spines.Spine):
    #         child.set_color(colors[i])

# %%
# to_plot = [0,2,3,6,7]
fig, axes = plt.subplots()
axes.matshow(np.average(I_all, axis=0),cmap='Greys_r')

for i in range(k):
    ix = np.where(labels == i)[0]
    axes.plot(coords[ix,1], coords[ix,0],'o', markersize=3, color=colors[i])

# %% hist
fig, axes = plt.subplots(nrows=k,sharex=True,sharey=True,figsize=[3,8])

bins = np.linspace(0,I_all.shape[2],20)
for i in range(k):
    ix = np.where(labels == i)[0]
    axes[i].hist(coords[ix,1],density=True,bins=bins,color=colors[i])

sns.despine(fig)
axes[-1].set_xlabel('AP [px]')
fig.tight_layout()
# %%
# fig, axes = plt.subplots()
# kwargs = dict(vmin=0, vmax=0.2,cmap='viridis')
# # normalize
# # cell_avgs = cell_avgs / np.max(cell_avgs, axis=1)[:,np.newaxis]
# order = kmeans_sort(cell_avgs, 8, 1)
# axes.matshow(cell_avgs[order], **kwargs)
# axes.set_aspect('auto')

# %% single cell
j = 934
cell = order[j]
fig, axes = plt.subplots()
yzoom = 1
yoffs = 0
for i in range(len(data))[::-1]:
    # axes.fill_between(data_times[i] / 1e3, np.zeros(data_times[i].shape[0]), data[i][cell,:] * yzoom+(i*yoffs), alpha=0.75, color='white',zorder=-i,lw=0.7)
    # axes.plot(data_times[i] / 1e3, data[i][cell,:] * yzoom + (i*yoffs), color='k', alpha=0.8,zorder=-i)
    axes.plot(data_times[i] / 1e3, data[i][cell,:] * yzoom + (i*yoffs), alpha=0.8,zorder=-i)

axes.set_xlabel('time (s)')
axes.set_ylabel('reward #')

sns.despine(fig)
fig.tight_layout()

# %%
plt.savefig("/home/georg/Desktop/plots for labmeeting/rewards_cell_%i=%i.png" % (j,cell), dpi=600)







# %% 

"""
 
 ######## ########  ####    ###    ##        ######  
    ##    ##     ##  ##    ## ##   ##       ##    ## 
    ##    ##     ##  ##   ##   ##  ##       ##       
    ##    ########   ##  ##     ## ##        ######  
    ##    ##   ##    ##  ######### ##             ## 
    ##    ##    ##   ##  ##     ## ##       ##    ## 
    ##    ##     ## #### ##     ## ########  ######  
 
"""
# %% prep and general analysis
session_metrics = [metrics.get_start, metrics.get_stop, metrics.has_choice, metrics.get_chosen_side, metrics.get_correct_side, metrics.get_interval, metrics.get_outcome, metrics.get_choice_rt]
SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics, "TRIAL_ENTRY_EVENT")

# expand categorical columns into boolean
categorial_cols = ['outcome']
for category_col in categorial_cols:
    categories = SessionDf[category_col].unique()
    categories = [cat for cat in categories if not pd.isna(cat)]
    for category in categories:
        SessionDf['is_'+category] = SessionDf[category_col] == category

# setup general filter
SessionDf['exclude'] = False

# %% DlcDf based metrics
# hand pos at go cue
# event = "CHOICE_STATE"
# th = 200
# for i, TrialDf in enumerate(TrialDfs):
#     try:
#         t = TrialDf.loc[TrialDf['name'] == event].iloc[0]['t']
#         frame_ix = sp.argmin(sp.absolute(DlcDf['t'].values - t))
#         SessionDf.loc[i,'paw_resting'] = DlcDf['PAW_L'].loc[frame_ix]['y'] < th
#     except IndexError:
#         SessionDf.loc[i,'paw_resting'] = sp.nan
"""
 
 ########  ##        #######  ######## ######## ######## ########   ######  
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##    ## 
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##       
 ########  ##       ##     ##    ##       ##    ######   ########   ######  
 ##        ##       ##     ##    ##       ##    ##       ##   ##         ## 
 ##        ##       ##     ##    ##       ##    ##       ##    ##  ##    ## 
 ##        ########  #######     ##       ##    ######## ##     ##  ######  
 
"""
# %%
### helpers
def make_bodypart_colors(bodyparts):
    bp_left = [bp for bp in bodyparts if bp.endswith('L')]
    bp_right = [bp for bp in bodyparts if bp.endswith('R')]
    c_l = sns.color_palette('viridis', n_colors=len(bp_left))
    c_r = sns.color_palette('magma', n_colors=len(bp_right))
    bp_cols = dict(zip(bp_left+bp_right,c_l+c_r))
    return bp_cols



# %%
"""
 
  ######  ########    ###    ######## ####  ######  
 ##    ##    ##      ## ##      ##     ##  ##    ## 
 ##          ##     ##   ##     ##     ##  ##       
  ######     ##    ##     ##    ##     ##  ##       
       ##    ##    #########    ##     ##  ##       
 ##    ##    ##    ##     ##    ##     ##  ##    ## 
  ######     ##    ##     ##    ##    ####  ######  
 
"""

# %% selecting t_on and t_off based on trial type

# trial selection
# SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='left'))
# TrialDf = TrialDfs[SDf.index[0]]
TrialDf = TrialDfs[0]

Df = bhv.event_slice(TrialDf, 'TRIAL_ENTRY_EVENT', 'ITI_STATE')
t_on = Df.iloc[0]['t']
t_off = Df.iloc[-1]['t']

# %% static image with trajectory between t_on and t_off

bp_cols = make_bodypart_colors(bodyparts)

fig, axes = plt.subplots()
# frame_ix = Sync.convert(t_on, 'arduino', 'frames') # this is not error robust?
frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])

frame = dlc.get_frame(Vid, frame_ix)
dlc.plot_frame(frame, axes=axes)
dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes)

# trajectory
DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
dlc.plot_trajectories(DlcDfSlice, bodyparts, axes=axes, colors=bp_cols, lw=1, p=0.99)

# %% plot all of the selected trial type

# SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right', paw_resting=False))

# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(has_choice=True, correct_side='right', outcome='correct'))

# plot some random frame
fig, axes = plt.subplots()

frame_ix = 1000
frame = dlc.get_frame(Vid, frame_ix)
dlc.plot_frame(frame, axes=axes)

# plot all traj in selection
for i in tqdm(SDf.index):
    TrialDf = TrialDfs[i]
    Df = bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_EVENT')
    # Df = bhv.time_slice(Df, Df.iloc[-1]['t']-500, Df.iloc[-1]['t'])
    t_on = Df.iloc[0]['t']
    t_off = Df.iloc[-1]['t']

    # trial by trial colors
    bp_cols = {}
    cmaps = dict(zip(bodyparts,['viridis','magma']))
    for bp in bodyparts:
        c = sns.color_palette(cmaps[bp],as_cmap=True)(sp.rand())
        bp_cols[bp] = c

    # marker for the start
    # frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
    frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])
    dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes, markersize=5)

    # the trajectory
    DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
    dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=axes, lw=0.75, alpha=0.75, p=0.8)

# %% plot all around timepoints

fig, axes = plt.subplots()

frame_ix = 1000
frame = dlc.get_frame(Vid, frame_ix)
dlc.plot_frame(frame, axes=axes)

# plot all traj in selection
for t in tqdm(event_times):
    # TrialDf = TrialDfs[i]
    # Df = bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_EVENT')
    # Df = bhv.time_slice(Df, Df.iloc[-1]['t']-500, Df.iloc[-1]['t'])
    # t_on = Df.iloc[0]['t']
    # t_off = Df.iloc[-1]['t']
    t_on = t + pre
    t_off = t + post

    # trial by trial colors
    bp_cols = {}
    cmaps = dict(zip(bodyparts,['viridis','magma']))
    for bp in bodyparts:
        c = sns.color_palette(cmaps[bp],as_cmap=True)(sp.rand())
        bp_cols[bp] = c

    # marker for the start
    # frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
    frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])
    dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes, markersize=5)

    # the trajectory
    DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
    dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=axes, lw=0.75, alpha=0.75, p=0.8)



# %% make an outcome / sides panel with the trajectories
outcomes = ['correct','incorrect','missed']
sides = ['left','right']

fig, axes = plt.subplots(ncols=len(outcomes),nrows=len(sides))

def plot_all_trajectories(TrialDfs, ax=None):
    for i, TrialDf in enumerate(TrialDfs):
        if TrialDf.shape[0] > 0:
            t_on = TrialDf.iloc[0]['t']
            t_off = TrialDf.iloc[-1]['t']

            # trial by trial colors
            bp_cols = {}
            cmaps = dict(zip(bodyparts,['viridis','magma']))
            for bp in bodyparts:
                c = sns.color_palette(cmaps[bp],as_cmap=True)(sp.rand())
                bp_cols[bp] = c

            # marker for the start
            # frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
            frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])
            dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=ax, markersize=5)

            # the trajectory
            DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
            dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=ax, lw=0.75, alpha=0.5, p=0.8)

for i, outcome in enumerate(outcomes):
    for j, side in enumerate(sides):
        # plot some random frame
        frame_ix = 5000
        frame = dlc.get_frame(Vid, frame_ix)

        try:
            SDf = bhv.groupby_dict(SessionDf, dict(correct_side=side, outcome=outcome))

            TrialDfs_sel = [TrialDfs[i] for i in SDf.index]
            if outcome != 'missed':
                TrialDfs_sel = [bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_EVENT') for TrialDf in TrialDfs_sel]
            else:
                TrialDfs_sel = [bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_MISSED_EVENT') for TrialDf in TrialDfs_sel]

            dlc.plot_frame(frame, axes=axes[j,i])
            plot_all_trajectories(TrialDfs_sel, ax=axes[j,i])
        except KeyError:
            pass

for ax in axes.flatten():
    ax.set_aspect('equal')
    ax.set_xticklabels('')
    ax.set_yticklabels('')

for i, ax in enumerate(axes[0,:]):
    ax.set_title(outcomes[i])

for i, ax in enumerate(axes[:,0]):
    ax.set_ylabel(sides[i])

fig.suptitle('reach trajectories split by outcome/side')
fig.tight_layout()
fig.subplots_adjust(top=0.85)


# %% 
"""
 
 ##     ## #### ########  ########  #######  
 ##     ##  ##  ##     ## ##       ##     ## 
 ##     ##  ##  ##     ## ##       ##     ## 
 ##     ##  ##  ##     ## ######   ##     ## 
  ##   ##   ##  ##     ## ##       ##     ## 
   ## ##    ##  ##     ## ##       ##     ## 
    ###    #### ########  ########  #######  
 
"""

# %% display video of trial
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right'))
# TrialDf = TrialDfs[SDf.index[1]] # good long from resting
TrialDf = TrialDfs[SDf.index[3]] # good long from resting

# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='left'))
TrialDf = TrialDfs[SDf.index[5]] # good left reach
TrialDf = TrialDfs[SDf.index[6]] # good left reach
TrialDf = TrialDfs[SDf.index[7]] # good left reach

# Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','CHOICE_EVENT')
# Df = bhv.event_slice(TrialDf,'CHOICE_STATE','CHOICE_EVENT')
t_on = Df.iloc[0]['t'] - 250
t_off = Df.iloc[-1]['t'] + 2000

"""
 
  #######  ########  ######## ##    ##  ######  ##     ## 
 ##     ## ##     ## ##       ###   ## ##    ## ##     ## 
 ##     ## ##     ## ##       ####  ## ##       ##     ## 
 ##     ## ########  ######   ## ## ## ##       ##     ## 
 ##     ## ##        ##       ##  #### ##        ##   ##  
 ##     ## ##        ##       ##   ### ##    ##   ## ##   
  #######  ##        ######## ##    ##  ######     ###    
 
"""
# %% testings: opencv based video vis

# helpers
def rgb2bgr(color):
    """ input: rgb, array or tuple or list, scale 0 - 1
    ouput: opencv style  """
    r,g,b = (np.array(color) * 255).astype('uint8')
    color = [int(c) for c in (b,g,r)]
    return color

# %%
# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right'))
TrialDf = TrialDfs[33]

Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','CHOICE_STATE')
t_on = Df.iloc[0]['t']  - 250
t_off = Df.iloc[-1]['t'] + 5000

# %%

def make_annotated_video_cv2(Vid, t_on, t_off, LogDf, DlcDf, fps, outpath):

    # get respective slices of the data
    g = 32 # grace period to avoid slicing beyond frame limits
    LogDfSlice = bhv.time_slice(LogDf, t_on-g, t_off+g)
    DlcDfSlice = bhv.time_slice(DlcDf, t_on-g, t_off+g)

    # get the closest frames, indices and times
    frame_on = np.argmin((DlcDf['t'].values - t_on)**2)
    frame_off = np.argmin((DlcDf['t'].values - t_off)**2)

    frame_ix = list(range(frame_on, frame_off))
    frame_t = [DlcDf.loc[ix]['t'].values[0] for ix in frame_ix]

    Frames = []
    for i, ix in enumerate(tqdm(frame_ix)):
        Frames.append(dlc.get_frame(Vid, ix))


    ## dlc body parts
    radius = 2

    bp_left = [bp for bp in bodyparts if bp.endswith('L')]
    bp_right = [bp for bp in bodyparts if bp.endswith('R')]
    c_l = sns.color_palette('viridis', n_colors=len(bp_left))
    c_r = sns.color_palette('magma', n_colors=len(bp_right))
    bp_cols = dict(zip(bp_left+bp_right,c_l+c_r))
    for bp in bodyparts:
        bp_cols[bp] = rgb2bgr(bp_cols[bp])


    ## for traces
    n_segments = 25 # in Frames
    w_start = 1
    w_stop = 6
    ws = np.linspace(w_start,w_stop,n_segments)

    ## for event text
    inactive_color = (255,255,255)

    ## event text annotations
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.5
    spacing = 15

    # what events to display
    # display_events = list(LogDfSlice.name.unique())
    display_events = ['TRIAL_AVAILABLE_EVENT','TRIAL_ENTRY_EVENT',
                      'CHOICE_EVENT', 'GO_CUE_SHORT_EVENT', 'GO_CUE_LONG_EVENT',
                      'CHOICE_CORRECT_EVENT', 'CHOICE_INCORRECT_EVENT',
                      'REWARD_LEFT_EVENT','REWARD_RIGHT_EVENT',
                      'REACH_LEFT_ON', 'REACH_LEFT_OFF', 'REACH_RIGHT_ON', 'REACH_RIGHT_OFF']

    if sp.nan in display_events:
        display_events.remove(np.nan)

    # color setup
    c = sns.color_palette('husl', n_colors=len(display_events))
    event_colors = dict(zip(display_events,c))
    event_display_dur = 150 # ms
    for event in event_colors.keys():
        event_colors[event] = rgb2bgr(event_colors[event])

    # extract times
    event_texts = []
    event_times = []
    for i, event in enumerate(display_events):
        # times 
        try:
            times = LogDfSlice.groupby('name').get_group(event)['t'].values
        except KeyError:
            times = [np.nan]
        event_times.append(times)

    # opencv setup
    h, w = Frames[0].shape
    codec = cv2.VideoWriter_fourcc(*'mp4v')
    # out = cv2.VideoWriter('/home/georg/testout.mp4', codec, fps, (w, h), isColor=True)
    out = cv2.VideoWriter(str(outpath), codec, fps, (w, h), isColor=True)

    for i, ix in enumerate(frame_ix):

        frame = Frames[i][:,:,np.newaxis].repeat(3,axis=2) # convert to color

        # markers
        for bp in bodyparts:
            data = DlcDfSlice[bp].loc[ix]
            pos = tuple(np.array((data['x'], data['y'])).astype('int32'))
            cv2.circle(frame, pos, radius, bp_cols[bp], cv2.LINE_AA)

        # past lines
        ix0 = ix-n_segments
        for bp in bodyparts:
            data = DlcDf[bp].loc[ix0:ix][['x', 'y']].values.astype('uint32')
            data[:,0] = data[:,0].clip(0, h)
            data[:,1] = data[:,1].clip(0, w)
            for j in range(1, n_segments):
                cv2.line(frame, tuple(data[j-1,:]), tuple(data[j,:]), bp_cols[bp], int(ws[j]), cv2.LINE_AA)

        # event text
        for j, event in enumerate(display_events):
            t = frame_t[i]
            try:
                if sp.any(sp.logical_and(t > event_times[j], t < (event_times[j] + event_display_dur))):
                    color = event_colors[event]
                else:
                    color = inactive_color
            except TypeError:
                # thrown when event never happens
                color = inactive_color

            pos = (10, h-int(j*spacing + spacing))
            cv2.putText(frame, event, pos, font, fontScale, color)

        out.write(frame)

    out.release()

# %% slice entire video
from Utils import utils
fps = 40
for i, row in SessionDf.iterrows():
    utils.printer("slicing video: Trial %i/%i" % (i, SessionDf.shape[0]))

    TrialDf = TrialDfs[i]
    outpath = session_folder / 'plots' / 'video_sliced'
    os.makedirs(outpath, exist_ok=True)
    try:
        Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','ITI_STATE')

        t_on = Df.iloc[0]['t'] - 250
        t_off = Df.iloc[-1]['t'] + 3000
        side = row['correct_side']
        outcome = row['outcome']
        fname = outpath / ("Trial_%i_%s_%s.mp4" % (i, side, outcome))
        make_annotated_video_cv2(Vid, t_on, t_off, LogDf, DlcDf, fps, fname)
    except IndexError:
        utils.printer("not able to process trial %i" % i,'error')

# %% slice video according to timepoints
from Utils import utils
fps = 40
for i,t in enumerate(rew_coll_events):
    # utils.printer("slicing video: Trial %i/%i" % (i, SessionDf.shape[0]))

    # TrialDf = TrialDfs[i]
    # outpath = session_folder / 'plots' / 'video_sliced'
    outpath = Path('/home/georg/Desktop/plots for labmeeting') / 'video_sliced_rewards'
    os.makedirs(outpath, exist_ok=True)
    try:
        # Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','ITI_STATE')
        t_on = t - 50
        t_off = t + 50
        # side = row['correct_side']
        # outcome = row['outcome']
        fname = outpath / ("reach_%i.mp4" % i)
        make_annotated_video_cv2(Vid, t_on, t_off, LogDf, DlcDf, fps, fname)
    except IndexError:
        utils.printer("not able to process event %i" % i,'error')

# # %%
# """
 
#     ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
#    ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
#   ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
#  ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
#  ######### ##  #### ######### ##          ##          ##  ##        ## 
#  ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
#  ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
# """
# # %% analysis - categorizing reaching patterns
# # idea - Kmeans over reaches
# def groupby(Df, **kwargs):
#     if len(kwargs) == 1:
#         return Df.groupby(list(kwargs.keys())[0]).get_group(tuple(kwargs.values())[0])
#     else:
#         return Df.groupby(list(kwargs.keys())).get_group(tuple(kwargs.values()))

# SDf = groupby(SessionDf, has_choice=True, outcome='correct') # as a start, ideally no grouping

# # %%
# # bhv.event_based_time_slice(LogDf, "GRASP_ON", 1, 1, Df_to_slice=DlcDf)

# Df = pd.concat([bhv.get_events_from_name(LogDf, "GRASP_LEFT_ON"),bhv.get_events_from_name(LogDf, "GRASP_RIGHT_ON")])
# Df = Df.sort_values('t')

# pre, post = -500,500
# Reaches = []
# for i,t in enumerate(Df['t'].values):
#     Reaches.append(bhv.time_slice(DlcDf, t+pre, t+post))

# # %%
# # M = []
# # good_inds = []
# # for i in range(len(Reaches)):
# #     R_left = Reaches[i]['PAW_L'][['x','y']].values.T.flatten()
# #     R_right = Reaches[i]['PAW_R'][['x','y']].values.T.flatten()
# #     if R_left.shape == R_right.shape:
# #         M.append(np.concatenate([R_left,R_right],0))
# #         good_inds.append(i)

# M = []
# for i in range(len(Reaches)):
#     R_left = Reaches[i]['PAW_L'][['x','y']].values.T.flatten()
#     R_right = Reaches[i]['PAW_R'][['x','y']].values.T.flatten()
#     M.append(np.concatenate([R_left,R_right],0))

# # %% filter by most common shapes
# n_samples = np.median([m.shape[0] for m in M])
# good_inds = [i for i in range(len(M)) if M[i].shape[0] == n_samples]
# M = [m[:,np.newaxis] for m in M if m.shape[0] == int(n_samples)]
# M = np.concatenate(M, axis=1)

# # %%
# fig, axes = plt.subplots()
# axes.matshow(M)
# axes.set_aspect('auto')

# # %%
# from sklearn.cluster import KMeans
# clust = KMeans(n_clusters=6).fit(M.T)
# clust.labels_

# # %%
# R = []
# for i in good_inds:
#     R.append(Reaches[i])

# # %%
# colors = sns.color_palette('tab10', n_colors=6)

# frame_ix = 5000
# frame = dlc.get_frame(Vid, frame_ix)

# fig, axes = plt.subplots(ncols=2)
# dlc.plot_frame(frame, axes=axes[0])
# dlc.plot_frame(frame, axes=axes[1])

# for i, r in enumerate(R):
#     Left = r['PAW_L'][['x','y']].values
#     axes[0].plot(Left[:,0], Left[:,1], color=colors[clust.labels_[i]])

#     Right = r['PAW_R'][['x','y']].values
#     axes[1].plot(Right[:,0], Right[:,1], color=colors[clust.labels_[i]])

# for ax in axes:
#     ax.set_aspect('equal')


# # %% another analysis - reach distances to spouts - all to all

# # calculate all distances
# sides = ['left','right']
# spout_coords = dict(left=[376,283], right=[276, 275])
# for bp in bodyparts:
#     for side in sides:
#         D = dlc.calc_dist_bp_point(DlcDf, bp, spout_coords[side], filter=True)
#         DlcDf[(bp),'%s_to_%s' % (bp, 'spout_'+side)] = D

# # %%
# Df = LogDf # all data
# # %% preselect trials by type
# ix = SessionDf.groupby('outcome').get_group('incorrect').index
# Df = pd.concat([TrialDfs[i] for i in ix],axis=0)
# Df = Df.reset_index(drop=True)

# # %%
# Grasp_events = dict(left=bhv.get_events_from_name(Df, "GRASP_LEFT_ON"), right=bhv.get_events_from_name(Df, "GRASP_RIGHT_ON"))
# pre, post = -2000,500

# Grasp_data = {}
# for side in sides:
#     Grasp_data[side] = []

#     for i,t in enumerate(Grasp_events[side]['t'].values):
#         Grasp_data[side].append(bhv.time_slice(DlcDf, t+pre, t+post))

# # %% get median number of samples
# for side in sides:
#     n_samples = int(np.median([reach.shape[0] for reach in Grasp_data[side]]))
#     good_inds = [i for i in range(len(Grasp_data[side])) if Grasp_data[side][i].shape[0] == n_samples]
#     Grasp_data[side] = [Grasp_data[side][i] for i in good_inds]

# # %% grid plot all to all
# tvec = np.linspace(pre,post,n_samples)

# for i, side in enumerate(sides):
#     fig, axes = plt.subplots(nrows=2,ncols=2,sharey=True, figsize=[9,9])
#     fig.suptitle('grasp to %s' % side)

#     for m, side_m in enumerate(sides): # over paws
#         for n, side_n in enumerate(sides): # over spouts
#             paw = 'PAW_%s' % side_m[0].upper()
#             index_tup = (paw, '%s_to_spout_%s' % (paw, side_n))

#             reach_avg = []
#             for reach in Grasp_data[side]:
#                 d = reach[index_tup]
#                 reach_avg.append(d)
#                 axes[m, n].plot(tvec, d, alpha=0.8)

#             reach_avg = np.array(reach_avg)
#             avg = np.nanmedian(reach_avg,axis=0)
#             axes[m, n].plot(tvec, avg, color='k', lw=2)

#     for ax, label in zip(axes[0,:],  sides):
#         ax.set_title('dist to spout ' + label)

#     for ax, label in zip(axes[:,0], sides):
#         ax.set_ylabel('paw ' + label)

#     for ax in axes.flatten():
#         ax.axvline(0, linestyle=':', color='k', lw=0.5)
#         ax.axhline(0, linestyle=':', color='k', lw=0.5)

#     for ax in axes[-1,:]:
#         ax.set_xlabel('time (ms)')

#     sns.despine(fig)
#     fig.tight_layout()
#     fig.subplots_adjust(top=0.90)


# %%
