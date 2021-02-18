# %% imports 
%matplotlib qt5
%matplotlib qt5
%load_ext autoreload
%autoreload 2

import matplotlib.pyplot as plt
import scipy as sp
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
import behavior_analysis_utils as bhv
from dlc_analysis_utils import *
from tqdm import tqdm

# %% read all three data sources

# DeepLabCut data
h5_path = Path("/media/georg/data/reaching_dlc/2021-02-12_17-10-48_learn_to_reach/bonsai_videoDLC_resnet_50_second_testFeb15shuffle1_650000.h5")
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
i = 8000 # frame index
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

# """
 
#     ###    ##    ## #### ##     ##    ###    ######## ####  #######  ##    ## 
#    ## ##   ###   ##  ##  ###   ###   ## ##      ##     ##  ##     ## ###   ## 
#   ##   ##  ####  ##  ##  #### ####  ##   ##     ##     ##  ##     ## ####  ## 
#  ##     ## ## ## ##  ##  ## ### ## ##     ##    ##     ##  ##     ## ## ## ## 
#  ######### ##  ####  ##  ##     ## #########    ##     ##  ##     ## ##  #### 
#  ##     ## ##   ###  ##  ##     ## ##     ##    ##     ##  ##     ## ##   ### 
#  ##     ## ##    ## #### ##     ## ##     ##    ##    ####  #######  ##    ## 
 
# """
# # %% play frames
# from matplotlib.animation import FuncAnimation
# # ix = list(range(30100,30200))
# ix = list(range(572,579))

# fig, ax = plt.subplots()
# ax.set_aspect('equal')
# frame = get_frame(Vid, ix[0])
# im = ax.imshow(frame, cmap='gray')
# # ax, lines = plot_Skeleton(Skeleton, DlcDf, ix[0], axes=ax)

# def update(i):
#     Frame = get_frame(Vid,i)
#     im.set_data(Frame)
#     # ax, lines_new = plot_Skeleton(Skeleton, DlcDf, i, axes=ax)
#     # for j, line in enumerate(lines):
#     #     x = [DlcDf[Skeleton[j][0]].loc[i].x,DlcDf[Skeleton[j][1]].loc[i].x]
#     #     y = [DlcDf[Skeleton[j][0]].loc[i].y,DlcDf[Skeleton[j][1]].loc[i].y]
#     #     line.set_data(x,y)

#     # return im, lines,
#     return im,

# ani = FuncAnimation(fig, update, frames=ix, blit=True, interval=2)
# plt.show()

# # %%
# ani.save('test.avi',fps=30,dpi=300)

# %%
