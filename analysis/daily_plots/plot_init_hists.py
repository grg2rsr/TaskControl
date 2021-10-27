# %%
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

sys.path.append('/home/georg/code/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics
from Utils import sync

def plot_init_hist(session_folder, save=None):

    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")

    # Sync first
    loadcell_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv', trig_len=100, ttol=5)
    arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

    Sync = sync.Syncer()
    Sync.data['arduino'] = arduino_sync_event['t'].values
    Sync.data['loadcell'] = loadcell_sync_event['t'].values
    success = Sync.sync('arduino','loadcell')
    
    # abort if sync fails
    if not success:
        utils.printer("trying to plot_init_hist, but failed to sync in file %s, - aborting" % session_folder)
        return None

    LogDf['t_orig'] = LogDf['t']
    LogDf['t'] = Sync.convert(LogDf['t'].values, 'arduino', 'loadcell')

    LoadCellDf = bhv.parse_bonsai_LoadCellData(session_folder / 'bonsai_LoadCellData.csv')

    # preprocessing
    samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
    LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).mean()
    LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).mean()

    # smoothing forces
    F = LoadCellDf[['x','y']].values
    w = np.ones(100)
    F[:,0] = np.convolve(F[:,0], w, mode='same')
    F[:,1] = np.convolve(F[:,1], w, mode='same')

    # detect pushes
    th = 500
    L = F < -th
    events = np.where(np.diff(np.logical_and(L[:,0],L[:,1])) == 1)[0]
    times = [LoadCellDf.iloc[int(i)]['t'] for i in events]

    # histogram of pushes pre vs pushes post trial available
    trial_times = bhv.get_events_from_name(LogDf, 'TRIAL_AVAILABLE_EVENT')['t'].values
    post = []
    pre = []

    for t in trial_times:
        dt = times - t
        try:
            post.append(np.min(dt[dt > 0]))
        except ValueError:
            # thrown when no more pushes after last init
            pass
        try:
            pre.append(np.min(-1*dt[dt < 0]))
        except ValueError:
            # thrown when no pushes before first init
            pass

    fig, axes = plt.subplots()
    bins = np.linspace(0,5000,25)
    axes.hist(pre, bins=bins, alpha=0.5, label='pre')
    axes.hist(post, bins=bins, alpha=0.5, label='post')
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('count')
    axes.legend()

    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)
    title = ' - '.join([Animal.display(), Session.date, 'day: %s'% Session.day])

    sns.despine(fig)
    fig.suptitle(title)
    fig.tight_layout()
    fig.subplots_adjust(top=0.85)

    if save is not None:
        os.makedirs(save.parent, exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

# %% session path
# poolboy last good
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-15_14-15-36_learn_to_choose_v2")
# sesssion_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02996_Policeman/2021-10-26_11-40-56_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-26_09-55-23_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-11_10-00-35_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-15_12-35-12_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-07_12-06-59_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-07_12-06-59_learn_to_choose_v2")
# plot_init_hist(session_folder)


# %%
