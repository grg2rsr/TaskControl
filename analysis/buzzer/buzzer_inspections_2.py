# %% imports 
%matplotlib qt5
%load_ext autoreload
%autoreload 2

import sys
from pathlib import Path
from tqdm import tqdm

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

import scipy as sp
import numpy as np
import pandas as pd

sys.path.append('..')
from Utils import behavior_analysis_utils as bhv
from Utils.sync import Syncer
from Utils import sync
# %%
# folder = Path("/media/georg/htcondor/shared-paton/georg/reach_setup/buzz_across_freq_box1/2021-06-09_12-24-06_learn_to_choose")
# folder = Path("/media/georg/htcondor/shared-paton/georg/reach_setup/buzz_across_freq_box1_high_res/2021-06-09_12-24-06_learn_to_choose")
# folder = Path("/media/georg/htcondor/shared-paton/georg/reach_setup/buzz_across_freq_box1_high_res/2021-06-09_17-19-43_learn_to_choose")

# folder = Path("/media/georg/data/reaching_buzzer_check/2021-06-15_13-10-20_learn_to_choose") # the new internal loadcell
folder = Path("/media/georg/htcondor/shared-paton/georg/reach_setup/buzzer_check/2021-09-10_16-20-12_learn_to_choose_v3")
log_path = folder / "arduino_log.txt"

plot_dir = log_path.parent / 'plots'
os.makedirs(plot_dir, exist_ok=True)

LogDf = bhv.get_LogDf_from_path(log_path)

# %% Syncer
lc_sync_event = sync.parse_harp_sync(folder / 'bonsai_harp_sync.csv',trig_len=100, ttol=4)
arduino_sync_event = sync.get_arduino_sync(folder / 'arduino_log.txt')

Sync = Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
Sync.data['loadcell'] = lc_sync_event['t'].values
Sync.sync('arduino','loadcell')

# DlcDf['t'] = Sync.convert(DlcDf.index.values, 'dlc', 'arduino')

# %%  Loadcell
csv_path = log_path.parent / "bonsai_LoadCellData.csv"
LoadCellDf = bhv.parse_bonsai_LoadCellData(csv_path)

# %%
LogDf['t_original'] = LogDf['t']
LogDf['t'] = Sync.convert(LogDf['t'].values,'arduino','loadcell')

# %% median removal for loadcelldata
# %% median correction
samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).median()
LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).median()

# %%
Spans = bhv.get_spans_from_names(LogDf, "REWARD_RIGHT_VALVE_ON", "REWARD_RIGHT_VALVE_OFF")
N = 2000
Data = sp.zeros((N,27,2))
for  i, row in Spans.iterrows():
    t_on = row["t_on"]
    t_off = t_on + N
    data = bhv.time_slice(LoadCellDf, t_on, t_off)
    Data[:,i,:] = data.values[:,1:]

# %%
fs = sp.arange(60,310,10)
Data = Data[:,-fs.shape[0]:,:]

# %%
fig, axes = plt.subplots()
for i in range(fs.shape[0]):
    plt.plot(Data[:,i,0])

# %%
from scipy.signal import periodogram
import seaborn as sns
colors = sns.color_palette('viridis',n_colors=25)
ysep = 50000
ysep = 0
fig, axes = plt.subplots()
for i in range(fs.shape[0]):
    psd = periodogram(Data[500:1500,i,0],fs=1000)
    axes.plot(psd[0], psd[1]+i*ysep, color=colors[i],lw=1.8,zorder=-i)


