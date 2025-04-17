# %% imports
import sys
from pathlib import Path
import numpy as np

import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv

sys.path.append('/home/georg/Projects/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import metrics_partial as metrics
from functools import partial

# %% path setup
# this needs to be defined
animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging")

def get_bhv_folder_from_imaging_folder(imaging_folder, animals_folder):
    # get the corresponding behavioral data
    with open(imaging_folder / 'meta.txt','r') as fH:
        lines = [l.strip() for l in fH.readlines()]
    meta = dict([l.split(' ') for l in lines])
    animal_ID = imaging_folder.parts[-2]
    session_folder = animals_folder / animal_ID / meta['bhv_session_name']
    return session_folder

# imaging_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-03-10_JJP-05425_10")
# session_folder = get_bhv_folder_from_imaging_folder(imaging_folder, animals_folder)

def sync_bhv_and_mic(session_folder):
    # folder is from bhv
    # Extraction and processing log data
    LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
    LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min = 5, t_max=200)

    # metrics
    get_trial_type = partial(metrics.get_var, var_name="this_trial_type")
    get_delay = partial(metrics.get_var, var_name="this_delay")
    get_reward_magnitude = partial(metrics.get_var, var_name="reward_magnitude")

    session_metrics = (metrics.get_start, metrics.get_stop, get_trial_type,
                    get_delay, get_reward_magnitude)

    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics, trial_entry_event="TRIAL_ENTRY_EVENT", trial_exit_event="TRIAL_AVAILABLE_EVENT")
    SessionDf.to_csv(session_folder / 'SessionDf.csv',index=False)

    # SYNC
    # reading times_log
    with open (session_folder / 'times_log.txt', 'r') as fH:
        lines = fH.readlines()

    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line != '']

    frame_timestamps = []
    trial_timestamps = []
    for line in lines:
        ch, t = line.split(' ')
        if ch == '1':
            trial_timestamps.append( np.int64(t) )
        if ch == '2':
            frame_timestamps.append( np.int64(t) )

    frame_timestamps = bhv.correct_wraparound_np(np.array(frame_timestamps), max_val=2**32)
    trial_timestamps = bhv.correct_wraparound_np(np.array(trial_timestamps), max_val=2**32)

    # uncorrected Trial start times
    TrialEntryEvent = bhv.get_events_from_name(LogDf,'TRIAL_ENTRY_EVENT')
    n_trials = len(TrialDfs)

    # linear clock syncing
    from scipy.stats import linregress
    x = trial_timestamps
    y = TrialEntryEvent['t'].values
    m, b = linregress(x, y)[:2]

    # correcting the timestamps from scanimage to arduino time
    frames_timestamps_corr = m * frame_timestamps + b
    np.save(session_folder / 'frame_timestamps_corr.npy',frames_timestamps_corr)


# %%
folders = []
# folders.append(Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-03-08_JJP-05425_8"))
# folders.append(Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-03-09_JJP-05425_9"))
# folders.append(Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-03-10_JJP-05425_10"))

folders.append(Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/2023-03-08_JJP-05472_8"))
folders.append(Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/2023-03-09_JJP-05472_9"))
folders.append(Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/2023-03-10_JJP-05472_10"))

for folder in folders:
    print("syncing folder %s" % folder)
    session_folder = get_bhv_folder_from_imaging_folder(folder, animals_folder)
    sync_bhv_and_mic(session_folder)


# %%



# # %% imports
# import sys, os
# from pathlib import Path
# import numpy as np
# import scipy as sp
# import pandas as pd
# import seaborn as sns
# from tqdm import tqdm

# from matplotlib import pyplot as plt
# import matplotlib as mpl
# # mpl.rcParams['figure.dpi'] = 331 # laptop
# mpl.rcParams['figure.dpi'] = 166 # the screens in the viv

# sys.path.append('/home/georg/Projects/TaskControl')

# from Utils import behavior_analysis_utils as bhv
# from Utils import utils
# from Utils import metrics_partial as metrics
# from Utils import sync
# from functools import partial

# # %% path setup
# animals_folder = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging"
# Animals = utils.get_Animals(animals_folder)

# folders = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/folders"
# # folders = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/folders"
# Animal_ID = folders.split('/')[-2]

# with open(folders,'r') as fH:
#     folders = [Path(f.strip()) for f in fH.readlines()]
# animal, = utils.select(Animals, ID=Animal_ID)

# # %% for each folder: sync!
# # TODO split this into sync session and sync all
# # TODO MOVE ME
# # sync should be a function that takes a bhv session path


# for folder in folders:

#     # get the corresponding behavioral data
#     with open(folder / 'meta.txt','r') as fH:
#         lines = [l.strip() for l in fH.readlines()]
#     meta = dict([l.split(' ') for l in lines])
#     session_folder = animal.folder / meta['bhv_session_name']

#     # Extraction and processing log data
#     LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
#     LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min = 5, t_max=200)

#     # metrics
#     get_trial_type = partial(metrics.get_var, var_name="this_trial_type")
#     get_delay = partial(metrics.get_var, var_name="this_delay")
#     get_reward_magnitude = partial(metrics.get_var, var_name="reward_magnitude")

#     session_metrics = (metrics.get_start, metrics.get_stop, get_trial_type,
#                     get_delay, get_reward_magnitude)

#     SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics, trial_entry_event="TRIAL_ENTRY_EVENT", trial_exit_event="TRIAL_AVAILABLE_EVENT")
#     SessionDf.to_csv(session_folder / 'SessionDf.csv',index=False)

#     # SYNC
#     # reading times_log
#     with open (session_folder / 'times_log.txt', 'r') as fH:
#         lines = fH.readlines()

#     lines = [line.strip() for line in lines]
#     lines = [line for line in lines if line != '']

#     frame_timestamps = []
#     trial_timestamps = []
#     for line in lines:
#         ch, t = line.split(' ')
#         if ch == '1':
#             trial_timestamps.append( np.int64(t) )
#         if ch == '2':
#             frame_timestamps.append( np.int64(t) )

#     frame_timestamps = bhv.correct_wraparound_np(np.array(frame_timestamps), max_val=2**32)
#     trial_timestamps = bhv.correct_wraparound_np(np.array(trial_timestamps), max_val=2**32)

#     # uncorrected Trial start times
#     TrialEntryEvent = bhv.get_events_from_name(LogDf,'TRIAL_ENTRY_EVENT')
#     n_trials = len(TrialDfs)

#     # linear clock syncing
#     from scipy.stats import linregress
#     x = trial_timestamps
#     y = TrialEntryEvent['t'].values
#     m, b = linregress(x, y)[:2]

#     # correcting the timestamps from scanimage to arduino time
#     frames_timestamps_corr = m * frame_timestamps + b
#     np.save(session_folder / 'frame_timestamps_corr.npy',frames_timestamps_corr)


# %%
