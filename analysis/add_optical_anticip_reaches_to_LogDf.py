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
from Utils import sync

colors = dict(success="#72E043", 
              reward="#3CE1FA", 
              correct="#72E043", 
              incorrect="#F56057", 
              premature="#9D5DF0", 
              missed="#F7D379",
              left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95))

# get animals and all sessions
Animals_folder = "/media/georg/htcondor/shared-paton/georg/Animals_reaching"
Animals = utils.get_Animals(Animals_folder)

Nicknames = ['Actress','Secretary','Nurse','Firefighter','Priest','Sailor']

for nickname in Nicknames:
    print("processing Animals: %s" % nickname)
    Animal, = utils.select(Animals, "Nickname", nickname)
    SessionsDf = utils.get_sessions(Animal.folder)

    for i, row in SessionsDf.iterrows():
        try:
            session_folder = Path(row['path'])
            os.chdir(session_folder)
            if (session_folder / 'LogDf.csv').exists():
                print("skipping %s " % % session_folder)
            else:
                print("processing folder %s" % session_folder)

                ### Camera data
                video_path = session_folder / "bonsai_video.avi"
                Vid = dlc.read_video(str(video_path))
                fps = Vid.get(5)
                n_frames = int(Vid.get(7))
                vid_dur = n_frames / fps

                ### Arduino data
                log_path = session_folder / 'arduino_log.txt'
                LogDf = bhv.get_LogDf_from_path(log_path)

                # Syncer
                cam_sync_event, Cam_SyncDf = sync.parse_cam_sync(session_folder / 'bonsai_frame_stamps.csv', offset=1, return_full=True)
                arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

                Sync = sync.Syncer()
                Sync.data['arduino'] = arduino_sync_event['t'].values
                Sync.data['cam'] = cam_sync_event['t'].values
                Sync.data['frames'] = cam_sync_event.index.values

                Sync.sync('arduino','cam')
                Sync.sync('frames','cam')


                # load previously optically detected reaches
                reach_left = np.load(session_folder / 'optical_reaches_left.npy')
                reach_right = np.load(session_folder / 'optical_reaches_right.npy')

                ReachesDf = pd.DataFrame(zip(reach_left,reach_right),columns=['left','right'])

                # preprocess / z-score
                samples = 500
                for col in tqdm(ReachesDf.columns):
                    if col is not 't':
                        ReachesDf[col] = ReachesDf[col] - ReachesDf[col].rolling(samples).mean()
                        ReachesDf[col] = ReachesDf[col] / np.nanstd(ReachesDf[col].values)

                # adding back to LogDf
                tvec = Sync.convert(range(n_frames),'frames','arduino')
                th_z = 5 # z-threshold
                d = np.diff( (ReachesDf.values > th_z).astype('int32'), axis=0)

                flanks = ['on','off']
                sides = ['left','right']

                NewReaches = {}
                for m, flank in enumerate(flanks):
                    th = 1 if flank == 'on' else -1
                    for n, side in enumerate(sides):
                        times = tvec[np.where(d[:,n] == th)[0]]
                        NewReaches['name'] = ['REACH_%s_%s' % (side.upper(), flank.upper())] * times.shape[0]
                        NewReaches['t'] = times
                        EventDf = pd.DataFrame(NewReaches)
                        LogDf = pd.concat([LogDf,EventDf])

                LogDf = LogDf.sort_values('t')
                LogDf = LogDf.reset_index(drop=True)
                LogDf.to_csv(session_folder / 'LogDf.csv')
            except:
                print("ERROR didn't process %s" % session_folder)
