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
from Utils import utils
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

# Therapist reaches
# path = "/media/georg/htcondor/shared-paton/georg/therapist_testing_sessions_to_keep/2021-11-18_12-50-40_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/therapist_testing_sessions_to_keep/2021-11-18_11-26-11_interval_categorization_v1"

# teacher
# path = "/media/georg/htcondor/shared-paton/georg/therapist_testing_sessions_to_keep/2021-11-22_16-16-38_interval_categorization_v1"

path = "/media/georg/htcondor/shared-paton/georg/therapist_testing_sessions_to_keep/2021-11-23_12-13-59_interval_categorization_v1"

# path = "/media/georg/htcondor/shared-paton/georg/therapist_testing_sessions_to_keep/2021-11-25_16-10-14_interval_categorization_v1"


#  Actress inspections
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-14_11-58-38_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-16_16-21-41_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-15_13-42-34_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-20_12-50-48_interval_categorization_v1"
session_folder = Path(path)

Animal = utils.Animal(session_folder.parent)


# %%
SessionsDf = utils.get_sessions(Animal.folder)
csv_path = Path(Animal.folder) / 'animal_meta.csv'
Df = pd.read_csv(csv_path)
ini_weight = np.float32(Df[Df['name'] == 'Weight']['value'].values[0])

for i, row in SessionsDf.iterrows():
    csv_path = Path(row['path']) / 'animal_meta.csv'
    Df = pd.read_csv(csv_path)
    weight = np.float32(Df[Df['name'] == 'current_weight']['value'].values[0])
    SessionsDf.loc[i,'weight'] = weight / ini_weight

# %%
fig, axes = plt.subplots()
days_unique = list(SessionsDf['date'].unique())
for i, row in SessionsDf.iterrows():
    x = days_unique.index(row['date'])
    axes.plot(x,row['weight'],'o')

axes.set_xticks(range(len(days_unique)))
axes.set_xticklabels(days_unique)
axes.set_ylim(0,1)
axes.axhline(0.8,linestyle=':',color='k',alpha=0.8,lw=1)
axes.axhline(0.7,linestyle=':',color='k',alpha=0.8,lw=1)

# %%
os.chdir(session_folder)

### DeepLabCut data
# h5_path = session_folder / [fname for fname in os.listdir(session_folder) if fname.endswith('filtered.h5')][0]
# h5_path = session_folder / [fname for fname in os.listdir(session_folder) if fname.endswith('.h5')][0]
# DlcDf = dlc.read_dlc_h5(h5_path)
# getting all dlc body parts
# bodyparts = sp.unique([j[0] for j in DlcDf.columns[1:]])

### Camera data
video_path = session_folder / "bonsai_video.avi"
Vid = dlc.read_video(str(video_path))

### Arduino data
log_path = session_folder / 'arduino_log.txt'
LogDf = bhv.get_LogDf_from_path(log_path)

### LoadCell Data
LoadCellDf = bhv.parse_bonsai_LoadCellData_touch(session_folder / 'bonsai_LoadCellData.csv')

# Syncer
from Utils import sync
cam_sync_event, Cam_SyncDf = sync.parse_cam_sync(session_folder / 'bonsai_frame_stamps.csv', offset=1, return_full=True)
lc_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv',trig_len=100, ttol=20)
arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

# %%
Sync = Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
Sync.data['loadcell'] = lc_sync_event['t'].values
Sync.data['cam'] = cam_sync_event['t'].values
Sync.data['frames'] = cam_sync_event.index.values

# from Utils.sync import polyv
# Sync.sync('arduino','loadcell',func=polyv, order=2)
# Sync.sync('arduino','loadcell',func=linsin)
# Sync.sync('loadcell','arduino', symmetric=False)
Sync.sync('arduino','cam')
Sync.sync('arduino','loadcell')
Sync.sync('frames','cam')

Sync.eval_plot()

# Sync = Syncer()
# Sync.data['arduino'] = arduino_sync_event['t'].values
# # Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
# Sync.data['cam'] = cam_sync_event['t'].values # used for what?
# Sync.sync('arduino','dlc')
# Sync.sync('arduino','cam')

# DlcDf['t'] = Sync.convert(DlcDf['t_cam'], 'cam', 'arduino')
# %%

# %%
# preprocessing
# careful: in the bonsai script right now, the baseline removal is different
# should be fixed now

samples = 500 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
for col in tqdm(LoadCellDf.columns):
    if col is not 't':
        LoadCellDf[col] = LoadCellDf[col] - LoadCellDf[col].rolling(samples).mean()

# %%
ds = 1
fig, axes = plt.subplots(nrows=2,sharex=True)
tvec = Sync.convert(LoadCellDf['t'].values, 'loadcell','arduino') / 1e3
axes[0].plot(tvec[::ds],np.abs(LoadCellDf['touch_l'].values[::ds]),color=colors['left'])
axes[0].plot(tvec[::ds],np.abs(LoadCellDf['touch_r'].values[::ds]),color=colors['right'])
axes[0].axhline(100,linestyle=':',color='k')
axes[0].set_ylim(0,250)

# tvec = Sync.convert(LoadCellDf['t'].values, 'loadcell','arduino') / 1e3
axes[1].plot(tvec[::ds],LoadCellDf['paw_l'].values[::ds],color=colors['left'])
axes[1].plot(tvec[::ds],LoadCellDf['paw_r'].values[::ds],color=colors['right'])

# add grasps
sides = ['left','right']
for ax in axes:
    for side in sides:
        times = LogDf.groupby('name').get_group('GRASP_%s_ON' % side.upper())['t'].values
        for t in times:
            ax.axvline(t/1e3,lw=1,alpha=0.5,color=colors[side])

# %% get frames for times
t_on = 923
t_off = t_on + 3

# t_on = 271
# t_off = 272

frame_on = Sync.convert(t_on*1e3, 'arduino', 'frames')
frame_off = Sync.convert(t_off*1e3, 'arduino', 'frames')

frame_ix = range(frame_on, frame_off)
frame_times = Sync.convert(frame_ix, 'frames', 'arduino')

print(len(frame_ix))

vid_fps = 60
display_fps = vid_fps / 3

for ix in frame_ix:
    frame = dlc.get_frame(Vid, ix)
    cv2.imshow('video',frame)
    if cv2.waitKey(int(1000/display_fps)) & 0xFF == ord('q'):
        break
    else:
        continue

cv2.destroyAllWindows()
# vid.release()


# %% spout position

frame_ix = 500
frame = dlc.get_frame(Vid, frame_ix)

fig, axes = plt.subplots()
axes.matshow(frame, cmap='Greys_r')

# spout_r = (376, 271)
# spout_l = (372, 198)

spout_l = (361, 211)
spout_r = (365, 283)

w = 10 # px
sides = ['left','right']
for side, spout in zip(sides, [spout_l, spout_r]):
    x, y = spout
    xs = [x-w, x-w, x+w, x+w, x-w]
    ys = [y+w, y-w, y-w, y+w, y+w]
    axes.plot(xs,ys,color=colors[side])


# %% extract reaches from video
fps = Vid.get(5)
n_frames = int(Vid.get(7))
vid_dur = n_frames / fps

reach_left = np.zeros(n_frames)
reach_right = np.zeros(n_frames)

for i in tqdm(range(n_frames)):
    frame = dlc.get_frame(Vid,i)
    reach_left[i] = np.average(frame[spout_l[1]-w:spout_l[1]+w, spout_l[0]-w:spout_l[0]+w])
    reach_right[i] = np.average(frame[spout_r[1]-w:spout_r[1]+w, spout_r[0]-w:spout_r[0]+w])


np.save(session_folder / 'reaches_left.npy', reach_left)
np.save(session_folder / 'reaches_right.npy', reach_right)

# %% or load
reach_left = np.load(session_folder / 'reaches_left.npy')
reach_right = np.load(session_folder / 'reaches_right.npy')


# %% get times from camera reaches
ReachesDf = pd.DataFrame(zip(reach_left,reach_right),columns=['left','right'])

samples = 500 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
for col in tqdm(ReachesDf.columns):
    if col is not 't':
        ReachesDf[col] = ReachesDf[col] - ReachesDf[col].rolling(samples).mean()
        ReachesDf[col] = ReachesDf[col] / np.nanstd(ReachesDf[col].values)

# %%
tvec = Sync.convert(range(n_frames),'frames','arduino') / 1e3

ks = np.linspace(1,10,100)
ns = []
for k in ks:
    d = np.diff( (ReachesDf.values > k).astype('int32'),axis=0)

    on_times_left = tvec[np.where(d[:,0] == 1)[0]]
    off_times_left = tvec[np.where(d[:,0] == -1)[0]]
    on_times_right = tvec[np.where(d[:,1] == 1)[0]]
    off_times_right = tvec[np.where(d[:,1] == -1)[0]]
    ns.append((on_times_left.shape[0],off_times_left.shape[0]))

fig, axes = plt.subplots()
axes.plot(ns)

# %%
tvec = Sync.convert(range(n_frames),'frames','arduino')
k = 5
d = np.diff( (ReachesDf.values > k).astype('int32'),axis=0)
on_times_left = tvec[np.where(d[:,0] == 1)[0]]
off_times_left = tvec[np.where(d[:,0] == -1)[0]]
on_times_right = tvec[np.where(d[:,1] == 1)[0]]
off_times_right = tvec[np.where(d[:,1] == -1)[0]]

print(on_times_left.shape)
print(off_times_left.shape)
print(on_times_right.shape)
print(off_times_right.shape)

# %% adding back to LogDf
# SpansDf_left = pd.DataFrame(zip(on_times_left, off_times_left),columns=['t_on','t_off'])
# SpansDf_left['dt'] = SpansDf_left['t_off'] - SpansDf_left['t_on']

D = {}
D['name'] = ['REACH_LEFT_ON']*on_times_left.shape[0]
D['t'] = on_times_left
EventDf = pd.DataFrame(D)
LogDf = pd.concat([LogDf,EventDf])

D['name'] = ['REACH_LEFT_OFF']*off_times_left.shape[0]
D['t'] = off_times_left
EventDf = pd.DataFrame(D)
LogDf = pd.concat([LogDf,EventDf])

D['name'] = ['REACH_RIGHT_ON']*on_times_right.shape[0]
D['t'] = on_times_right
EventDf = pd.DataFrame(D)
LogDf = pd.concat([LogDf,EventDf])

D['name'] = ['REACH_RIGHT_OFF']*off_times_right.shape[0]
D['t'] = off_times_right
EventDf = pd.DataFrame(D)
LogDf = pd.concat([LogDf,EventDf])
LogDf = LogDf.sort_values('t')

# %% plot for comparison
ds = 1
fig, axes = plt.subplots(nrows=3,sharex=True)
tvec = Sync.convert(LoadCellDf['t'].values, 'loadcell','arduino') / 1e3
axes[0].plot(tvec[::ds],np.abs(LoadCellDf['touch_r'].values[::ds]),color=colors['left'])
axes[0].plot(tvec[::ds],np.abs(LoadCellDf['touch_l'].values[::ds]),color=colors['right'])
axes[0].axhline(100,linestyle=':',color='k')    

# tvec = Sync.convert(range(n_frames),'frames','arduino') / 1e3
# axes[1].plot(tvec[::ds], reach_left[::ds], color=colors['left'])
# axes[1].plot(tvec[::ds], reach_right[::ds], color=colors['right'])

tvec = Sync.convert(range(n_frames),'frames','arduino') / 1e3
axes[1].plot(tvec[::ds], ReachesDf['left'][::ds], color=colors['left'])
axes[1].plot(tvec[::ds], ReachesDf['right'][::ds], color=colors['right'])
for t in on_times_left:
    axes[1].axvline(t/1e3,lw=1,alpha=0.5,color=colors['left'])
for t in on_times_right:
    axes[1].axvline(t/1e3,lw=1,alpha=0.5,color=colors['right'])

# for t in off_times_left:
    # axes[1].axvline(t/1e3,lw=1,alpha=0.5,color='black')
# for t in on_times_right:
    # axes[1].axvline(t,lw=1,alpha=0.5,color=colors['right'])

tvec = Sync.convert(LoadCellDf['t'].values, 'loadcell','arduino') / 1e3
axes[2].plot(tvec[::ds],LoadCellDf['paw_l'].values[::ds],color=colors['left'])
axes[2].plot(tvec[::ds],LoadCellDf['paw_r'].values[::ds],color=colors['right'])

# add grasps
sides = ['left','right']
# for ax in axes:
for side in sides:
    times = LogDf.groupby('name').get_group('GRASP_%s_ON' % side.upper())['t'].values
    for t in times:
        axes[0].axvline(t/1e3,lw=1,alpha=0.5,color=colors[side])

# adding spans for choice window
SpansDf = bhv.get_spans_from_names(LogDf,'CHOICE_STATE','REWARD_EVENT')
for i, row in SpansDf.iterrows():
    axes[1].axvspan(row['t_on']/1e3,row['t_off']/1e3,alpha=0.2,color='k')
# %%
# for TrialDf in TrialDfs:
TrialDf = TrialDfs[12]

# %%
for i, TrialDf in enumerate(TrialDfs):
    sl = bhv.event_slice(TrialDf, 'CHOICE_STATE', 'REWARD_EVENT')
    if "REACH_LEFT_ON" in sl['name'].values:
        
        print(i)
    if "REACH_RIGHT_ON" in sl['name'].values:
        print(i)

# %% get trial for timepoint
np.argmin([(TrialDf.iloc[0]['t'] - 1120*1e3)**2 for TrialDf in TrialDfs])

# %%
TrialDf = TrialDfs[112]
