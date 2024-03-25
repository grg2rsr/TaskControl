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

#  Actress inspections
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-14_11-58-38_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-16_16-21-41_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-15_13-42-34_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-20_12-50-48_interval_categorization_v1"
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress/2021-12-20_12-50-48_interval_categorization_v1"
session_folder = Path(path)

Animal = utils.Animal(session_folder.parent)


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
fps = Vid.get(5)
n_frames = int(Vid.get(7))
vid_dur = n_frames / fps

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

Sync.sync('arduino','cam')
Sync.sync('arduino','loadcell')
Sync.sync('frames','cam')

# Sync.eval_plot()

# DlcDf['t'] = Sync.convert(DlcDf['t_cam'], 'cam', 'arduino')

# %%
# preprocessing
# samples = 500 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
# for col in tqdm(LoadCellDf.columns):
#     if col is not 't':
#         LoadCellDf[col] = LoadCellDf[col] - LoadCellDf[col].rolling(samples).mean()

# %% or load
reach_left = np.load(session_folder / 'reaches_left.npy')
reach_right = np.load(session_folder / 'reaches_right.npy')

# %% get times from camera reaches
ReachesDf = pd.DataFrame(zip(reach_left,reach_right),columns=['left','right'])

samples = 500
for col in tqdm(ReachesDf.columns):
    if col is not 't':
        ReachesDf[col] = ReachesDf[col] - ReachesDf[col].rolling(samples).mean()
        ReachesDf[col] = ReachesDf[col] / np.nanstd(ReachesDf[col].values)

# %% adding back to LogDf
tvec = Sync.convert(range(n_frames),'frames','arduino')
k = 5
d = np.diff( (ReachesDf.values > k).astype('int32'), axis=0)

flanks = ['on','off']
sides = ['left','right']

NewReaches = {}
for i, flank in enumerate(flanks):
    th = 1 if flank == 'on' else -1
    for j, side in enumerate(sides):
        times = tvec[np.where(d[:,j] == th)[0]]
        NewReaches['name'] = ['REACH_%s_%s' % (side.upper(), flank.upper())] * times.shape[0]
        NewReaches['t'] = times
        EventDf = pd.DataFrame(NewReaches)
        LogDf = pd.concat([LogDf,EventDf])

LogDf = LogDf.sort_values('t')
LogDf = LogDf.reset_index(drop=True)

# %% store it
LogDf.to_csv(session_folder / 'LogDf.csv')

# %% analysis of anticipatory reaches
# prep
session_metrics = (metrics.get_start, metrics.has_choice, metrics.get_chosen_side, 
                       metrics.get_outcome, metrics.get_correct_side, metrics.get_timing_trial,
                       metrics.has_reward_collected, metrics.get_autodeliver_trial, metrics.get_in_corr_loop,
                       metrics.has_anticipatory_reach)

SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics)
SessionDf = bhv.expand_columns(SessionDf, ['outcome'])

outcomes = SessionDf['outcome'].unique()
if np.any(pd.isna(outcomes)):
    SessionDf.loc[pd.isna(SessionDf['outcome']),'outcome'] = 'reward_autodelivered'

# %%
# how to add - criterion: autodeliver reward, before reward_event
# turn this into a metric

def get_anticip_reach_outcome(TrialDf):
    var_name = 'anticip_reach_outcome'
    var = np.nan

    sl = bhv.event_slice(TrialDf, 'CHOICE_STATE', 'REWARD_EVENT')
    
    events = sl['name'].values
    choice = None

    if "REACH_LEFT_ON" in events and "REACH_RIGHT_ON" in events:
        ix_l = sl[sl['name'] == "REACH_LEFT_ON"].index[0]
        ix_r = sl[sl['name'] == "REACH_RIGHT_ON"].index[0]
        if ix_l < ix_r:
            choice = 'left'
        else:
            choice = 'right'

    if "REACH_LEFT_ON" in events:
        ix = sl[sl['name'] == "REACH_LEFT_ON"].index[0]
        choice = 'left'

    if "REACH_RIGHT_ON" in events:
        ix = sl[sl['name'] == "REACH_RIGHT_ON"].index[0]
        choice = 'right'

    if choice is not None:
        correct_side = SessionDf.loc[i]['correct_side']
        if correct_side == choice:
            var = 'correct'
            # SessionDf.loc[i,'outcome'] = 'correct'
            # SessionDf.loc[i,'has_anticip_reach'] = True

        else:
            var = 'incorrect'
            # SessionDf.loc[i,'outcome'] = 'incorrect'
            # SessionDf.loc[i,'has_anticip_reach'] = True

    return pd.Series(var, name=var_name)





