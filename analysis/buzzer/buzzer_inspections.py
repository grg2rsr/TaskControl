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
Data_L = sp.reshape(Data,(N, 8, 10, 2))

Spans = bhv.get_spans_from_names(LogDf, "REWARD_RIGHT_VALVE_ON", "REWARD_RIGHT_VALVE_OFF")

Data = sp.zeros((N,80,2))
for  i, row in Spans.iterrows():
    t_on = row["t_on"]
    t_off = t_on + N
    data = bhv.time_slice(LoadCellDf, t_on, t_off)
    Data[:,i,:] = data.values[:,1:]

Data_R = sp.reshape(Data,(N, 8, 10, 2))
Data_R = Data_R[:,::-1,:,:]

Data = sp.concatenate([Data_L, Data_R], axis=1)
fs = [200,205,210,215,220,225,230,235,235,240,245,250,255,260,265,270]
# fs = [165,175,185,195,205,215,225,235,235,245,255,265,275,285,295,305]

# %%
fig, axes = plt.subplots(nrows=16,ncols=2,sharey=True)
for i in range(16):
    axes[i,0].plot(Data[:,i,:,0])
    axes[i,1].plot(Data[:,i,:,1])
    axes[i,0].set_ylabel(fs[i])
fig.tight_layout()

# %% 
from scipy.signal import periodogram
import seaborn as sns
colors = sns.color_palette('viridis',n_colors=16)
fig, axes = plt.subplots()
ysep=500
P = []
for i in range(16):
    psds = []
    for j in range(10):
        psd = periodogram(Data[:,i,j,1],fs=1000)
        psds.append(psd[1])
    psds = sp.array(psds)
    # axes.plot(psd[0],sp.average(psds,axis=0),color='k',lw=2)
    axes.plot(psd[0],sp.average(psds,axis=0)+i*ysep,color=colors[i],lw=1.8,zorder=-i)
    # axes.axvline(fs[i],color=colors[i])

# %% one versus the other
fig, axes = plt.subplots()
ix_low = sp.where(sp.array(fs) == 200)[0][0]
ix_high = sp.where(sp.array(fs) == 270)[0][0]

for i in range(10):
    f, psd_l = periodogram(Data[:,ix_low,i,0],fs=1000)
    f, psd_r = periodogram(Data[:,ix_low,i,1],fs=1000)
    axes.plot(f,psd_l,color='green')
    axes.plot(f,psd_r,color='darkgreen')

    f, psd_l = periodogram(Data[:,ix_high,i,0],fs=1000)
    f, psd_r = periodogram(Data[:,ix_high,i,1],fs=1000)
    axes.plot(f,psd_l,color='magenta')
    axes.plot(f,psd_r,color='darkmagenta')

# psds.append(psd[1])
# psds = sp.array(psds)
# # axes.plot(psd[0],sp.average(psds,axis=0),color='k',lw=2)
# axes.plot(psd[0],sp.average(psds,axis=0)+i*ysep,color=colors[i],lw=1.8,zorder=-i)
# # axes.axvline(fs[i],color=colors[i])

# %%
fig, axes = plt.subplots()
ysep=0
l_peaks = []
r_peaks = []
for i in range(16):
    psds = []
    for j in range(10):
        psd = periodogram(Data[:,i,j,0],fs=1000)
        psds.append(psd[1])
    psds = sp.array(psds)
    psds = sp.average(psds,axis=0)

    # ix = sp.where(psd[0] == fs[i])[0][0]
    ix = sp.where(psd[0] == 270)[0][0]
    l_peaks.append(psds[ix])
    axes.plot(fs[i],psds[ix],'o',color=colors[i])

    psds = []
    for j in range(10):
        psd = periodogram(Data[:,i,j,1],fs=1000)
        psds.append(psd[1])
    psds = sp.array(psds)
    psds = sp.average(psds,axis=0)

    ix = sp.where(psd[0] == fs[i])[0][0]
    r_peaks.append(psds[ix])
    axes.plot(fs[i],psds[ix],'o',color=colors[i])

axes.plot(fs,l_peaks,color='k',zorder=-1)
axes.plot(fs,r_peaks,color='k',zorder=-1)

# %%
