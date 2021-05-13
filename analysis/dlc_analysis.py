# %% imports 
%matplotlib qt5
%load_ext autoreload
%autoreload 2
import sys
sys.path.append('..')
import matplotlib.pyplot as plt
import scipy as sp
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
from Utils import behavior_analysis_utils as bhv
from Utils.dlc_analysis_utils import *
from tqdm import tqdm

# %% read all three data sources

# DeepLabCut data
h5_path = Path("/media/georg/data/reaching_dlc/2021-02-12_17-10-48_learn_to_reach/bonsai_videoDLC_resnet_50_second_testFeb15shuffle1_650000.h5")
h5_path = Path("/media/georg/data/reaching_dlc/JJP-01641/2021-02-19_20-49-38_learn_to_reach/bonsai_videoDLC_resnet_50_second_testFeb15shuffle1_650000.h5")
h5_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01642/2021-02-18_16-33-23_learn_to_reach/bonsai_videoDLC_resnet_50_second_testFeb15shuffle1_650000.h5")

DlcDf = read_dlc_h5(h5_path)

# all body parts
bodyparts = sp.unique([j[0] for j in DlcDf.columns[1:]])

# Video 
video_path = h5_path.parent / "bonsai_video.avi"
Vid = read_video(str(video_path))

log_path = video_path.parent / 'arduino_log.txt'
LogDf = bhv.get_LogDf_from_path(log_path)

# %% sync
video_sync_path = video_path.parent / 'bonsai_frame_stamps.csv'
m, b, m2, b2 = sync_arduino_w_dlc(log_path, video_sync_path)

# writing arduino times of frames to the Dlc data
DlcDf['t'] = frame2time(DlcDf.index,m,b,m2,b2)

# %% defining some stuff
Skeleton   = (('D1L','J1L'),('D2L','J2L'),('D3L','J3L'),('D4L','J4L'),('D5L','J5L'),
             ('PR','J1R'),('PR','J2R'),('PR','J3R'),('PR','J4R'),('PR','J5R'),
             ('D1R','J1R'),('D2R','J2R'),('D3R','J3R'),('D4R','J4R'),('D5R','J5R'),
             ('PL','J1L'),('PL','J2L'),('PL','J3L'),('PL','J4L'),('PL','J5L'))

paws = ['PL','PR']

# %% plot all trajectories
fig, axes = plt.subplots()

i = 8000 # frame index
Frame = get_frame(Vid, i)
axes = plot_frame(Frame, axes=axes)
axes = plot_trajectories(DlcDf, paws, axes=axes,lw=0.025)


# %% plot a single frame with DLC markers and Skeleton
fig, axes = plt.subplots()
i = 8000 # frame index
Frame = get_frame(Vid, i)
axes = plot_frame(Frame, axes=axes)
axes = plot_bodyparts(bodyparts, DlcDf, i, axes=axes)
axes, lines = plot_Skeleton(Skeleton, DlcDf, i , axes=axes)


# %% identify reaches
fig, axes = plt.subplots()
i = 7000 # frame index
Frame = get_frame(Vid, i)
axes = plot_frame(Frame, axes=axes)
coords = [188,404] # spout right
# coords = [380, 396] # spout left
p = 0.99

w = 100 # box size
rect = box2rect(coords, w)

R = Rectangle(*rect2cart(rect),lw=1,facecolor='none',edgecolor='r')
axes.add_patch(R)

bp = 'PR'
SpansDf = in_box_span(DlcDf, bp, rect, min_dur=20)

# convert frames to times in a DF - utils function?
SpansDf = pd.DataFrame(frame2time(SpansDf.values,m,b,m2,b2),columns=SpansDf.columns)

# plot
fig, axes = plt.subplots()
i = 8000 # frame index
Frame = get_frame(Vid, i)
axes = plot_frame(Frame, axes=axes)

df = DlcDf[bp]
for i, row in tqdm(SpansDf.iterrows()):
    t_on = row['t_on']
    df = bhv.time_slice(DlcDf,t_on-250,t_on)[bp]

    ix = df.likelihood > p
    df = df.loc[ix]
    axes.plot(df.x,df.y,lw=2.0,alpha=0.5)

# %% distance / speed over time

fig, axes = plt.subplots(nrows=2,sharex=True)

bps = ['PR','PL']
right_spout = [188,404]
left_spout = [380, 396]

line_kwargs = dict(lw=1,alpha=0.8)
for i, bp in enumerate(bps):
    d_to_right = calc_dist_bp_point(DlcDf, bp, right_spout, filter=True)
    d_to_left = calc_dist_bp_point(DlcDf, bp, left_spout, filter=True)
    axes[i].plot(d_to_left, label='to left', **line_kwargs)
    axes[i].plot(d_to_right, label='to right', **line_kwargs)
    axes[i].set_ylabel(bp)
    axes[i].set_ylim(0)

axes[0].legend()

# %% 
fig, axes = plt.subplots()
i = 7000 # frame index
Frame = get_frame(Vid, i)
axes = plot_frame(Frame, axes=axes)
coords = [201,381] # spout right
#  = [385, 375] # spout left
p = 0.90

w = 60 # box size
rect = box2rect(coords, w)

R = Rectangle(*rect2cart(rect),lw=1,facecolor='none',edgecolor='r')
axes.add_patch(R)

bp = 'PR'
SpansDf = in_box_span(DlcDf, bp, rect, min_dur=5, p=p)

# convert frames to times in a DF - utils function?
SpansDf = pd.DataFrame(frame2time(SpansDf.values,m,b,m2,b2),columns=SpansDf.columns)

pre, post = -500, 500
inds = []
for i, row in SpansDf.iterrows():
    df = bhv.time_slice(DlcDf, row.t_on+pre, row.t_on+post)
    inds.append(df.index)

# %% from event
pre, post = -500, 500

event = 'REWARD_RIGHT_AVAILABLE_EVENT'
Event = bhv.get_events_from_name(LogDf, event)
inds = []
for t in Event.t:
    df = bhv.time_slice(DlcDf, t+pre, t+post)
    inds.append(df.index)

# %% 
D = sp.zeros((np.max([ix.shape[0] for ix in inds]),len(inds)))
D[:] = sp.nan

# %%
dists = calc_dist_bp_point(DlcDf, bp, coords, p=0.1, filter=True)

for i in range(len(inds)):
    shape = inds[i].shape[0]
    D[:shape,i] = dists[inds[i]]

# %% full plot
fig, axes = plt.subplots(nrows=2,ncols=2,sharex=True,sharey=True)

# events = ['REWARD_LEFT_AVAILABLE_EVENT','REWARD_RIGHT_AVAILABLE_EVENT']
events = ['REWARD_LEFT_VALVE_ON','REWARD_RIGHT_VALVE_ON']
prev_events = ['REWARD_LEFT_AVAILABLE_EVENT','REWARD_RIGHT_AVAILABLE_EVENT']
sides = ['left','right']
coords = [[385, 375],[201,381]] # left, right
pre, post = -7500, 7500
bp = 'PR'

for i,event in enumerate(events):
    for j, point in enumerate(coords):

        # get timestamps
        Event = bhv.get_events_from_name(LogDf, event)

        Prev_Event = bhv.get_events_from_name(LogDf, prev_events[i])

        # to indices
        inds = []
        t_prev = []
        for t in Event.t:
            df = bhv.time_slice(DlcDf, t+pre, t+post)
            inds.append(df.index)

            t_prev.append(bhv.time_slice(Prev_Event,t+pre, t+post)['t']-t)

        # prealloc empty
        D = sp.zeros((np.max([ix.shape[0] for ix in inds]),len(inds)))
        D[:] = sp.nan

        # euclid dist
        dists = calc_dist_bp_point(DlcDf, bp, point, p=0.1, filter=True)

        for k in range(len(inds)):
            shape = inds[k].shape[0]
            D[:shape,k] = dists[inds[k]]

        axes[j,i].matshow(D.T,cmap='viridis_r',vmin=0,vmax=100, origin='bottom', extent=(pre,post,0,D.shape[1]))

        for k in range(len(t_prev)):
            try:
                for q in t_prev[k].values:
                    axes[j,i].plot([q,q],[k,k+1],color='r', alpha=0.5,lw=1)
                    # axes[j,i].plot(t_prev[k],[k]*t_prev[k].shape[0],)
            except:
                pass

for ax in axes.flatten():
    ax.set_aspect('auto')
    ax.axvline(0,alpha=0.5,color='k',linestyle=':')

for i,ax in enumerate(axes[:,0]):
    ax.set_ylabel("to spout %s" % sides[i])

for i,ax in enumerate(axes[0,:]):
    ax.set_title(events[i])

fig.suptitle(bp)
fig.tight_layout()

# %%
Event = bhv.get_events_from_name(LogDf, 'REWARD_LEFT_VALVE_ON')
prev_Event =  bhv.get_events_from_name(LogDf, 'REWARD_LEFT_AVAILABLE_EVENT')
min_dur = 5000

# %%
t = bhv.get_events_from_name(LogDf, "REWARD_LEFT_VALVE_ON").iloc[20].values[0]
# """
 
#     ###    ##    ## #### ##     ##    ###    ######## ####  #######  ##    ## 
#    ## ##   ###   ##  ##  ###   ###   ## ##      ##     ##  ##     ## ###   ## 
#   ##   ##  ####  ##  ##  #### ####  ##   ##     ##     ##  ##     ## ####  ## 
#  ##     ## ## ## ##  ##  ## ### ## ##     ##    ##     ##  ##     ## ## ## ## 
#  ######### ##  ####  ##  ##     ## #########    ##     ##  ##     ## ##  #### 
#  ##     ## ##   ###  ##  ##     ## ##     ##    ##     ##  ##     ## ##   ### 
#  ##     ## ##    ## #### ##     ## ##     ##    ##    ####  #######  ##    ## 
 
# """
# %% play frames
from matplotlib.animation import FuncAnimation
# ix = list(range(30100,30200))
frame = time2frame(t,m,b,m2,b2)
# ix = list(range(frame-100,frame+100))
ix = list(range(frame-50,frame))

fig, ax = plt.subplots()
ax.set_aspect('equal')
frame = get_frame(Vid, ix[0])
im = ax.imshow(frame, cmap='gray')
# ax, lines = plot_Skeleton(Skeleton, DlcDf, ix[0], axes=ax)

def update(i):
    Frame = get_frame(Vid,i)
    im.set_data(Frame)
    # ax, lines_new = plot_Skeleton(Skeleton, DlcDf, i, axes=ax)
    # for j, line in enumerate(lines):
    #     x = [DlcDf[Skeleton[j][0]].loc[i].x,DlcDf[Skeleton[j][1]].loc[i].x]
    #     y = [DlcDf[Skeleton[j][0]].loc[i].y,DlcDf[Skeleton[j][1]].loc[i].y]
    #     line.set_data(x,y)

    # return im, lines,
    return im,

ani = FuncAnimation(fig, update, frames=ix, blit=True, interval=2)
plt.show()

# # %%
# ani.save('test.avi',fps=30,dpi=300)

# %%
