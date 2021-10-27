# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

# this should be changed ... 
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

def plot_forces_on_init(session_folder, save=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")

    ### LoadCell Data
    LoadCellDf = bhv.parse_bonsai_LoadCellData(session_folder / 'bonsai_LoadCellData.csv')

    # Syncer
    from Utils import sync
    lc_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv', trig_len=100, ttol=5)
    arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

    Sync = sync.Syncer()
    Sync.data['arduino'] = arduino_sync_event['t'].values
    Sync.data['loadcell'] = lc_sync_event['t'].values
    Sync.sync('arduino','loadcell')

    LogDf['t_orig'] = LogDf['t']
    LogDf['t'] = Sync.convert(LogDf['t'].values, 'arduino', 'loadcell')

    # preprocessing
    samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
    LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).mean()
    LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).mean()

    # plot forces  
    times = LogDf.groupby('name').get_group('TRIAL_ENTRY_EVENT')['t'].values
    pre, post = -1000, 1000
    fig, axes = plt.subplots(nrows=2,sharex=True,sharey=False)

    x_avgs = []
    y_avgs = []
    for i,t in enumerate(tqdm(times)):
        Df = bhv.time_slice(LoadCellDf, t+pre, t+post, reset_index=False)
        # these colors need to be thorougly checked
        axes[0].plot(Df['t'].values - t, Df['x'])
        axes[1].plot(Df['t'].values - t, Df['y'])

        x_avgs.append(Df['x'].values)
        y_avgs.append(Df['y'].values)

    x_avgs = np.average(np.array(x_avgs),axis=0)
    y_avgs = np.average(np.array(y_avgs),axis=0)

    tvec = np.linspace(pre,post,x_avgs.shape[0])
    axes[0].plot(tvec, x_avgs, color='k',lw=2)
    axes[1].plot(tvec, y_avgs, color='k',lw=2)

    kws = dict(linestyle=':',lw=1, alpha=0.8, color='k')
    for ax in axes:
        ax.axhline(-500, **kws)
        ax.axvline(0, **kws)

    # deco
    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)
    title = ' - '.join([Animal.display(), Session.date, 'day: %s'% Session.day])

    for ax in axes:
        ax.set_ylim(-2500,2500)
        ax.set_ylabel('Force [au]')
    axes[1].set_xlabel('time (ms)')

    sns.despine(fig)
    fig.suptitle(title)
    fig.tight_layout()
    fig.subplots_adjust(top=0.9)

    if save is not None:
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

# %% session path

# seems to have one channel inverted
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-08_11-06-44_learn_to_choose_v2")

# has no clock pulses
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02996_Policeman/2021-10-12_12-33-45_learn_to_choose_v2")

# notes: plumber seems to have correct flipping
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-11_12-35-21_learn_to_choose_v2")
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-07_12-00-07_learn_to_choose_v2")

# lifeguard should then be similar
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-08_11-02-31_learn_to_choose_v2")
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-14_10-20-51_learn_to_choose_v2")

# poolboy last good
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-15_14-15-36_learn_to_choose_v2")

# poolboy on his way down
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-18_12-32-41_learn_to_choose_v2")

# lumberjack recent
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-22_10-45-30_learn_to_choose_v2")

# a non-initiating mouse 
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-15_12-35-12_learn_to_choose_v2")

# poolboy back up but autostart trials
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-25_14-03-04_learn_to_choose_v2")

plot_forces_on_init(session_folder)
# %%