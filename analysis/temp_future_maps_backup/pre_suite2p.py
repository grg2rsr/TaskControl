# %%
%matplotlib qt5
import matplotlib.pyplot as plt
import matplotlib as mpl
from tqdm import tqdm
import numpy as np
from pathlib import Path

import sys, os
sys.path.append('/home/georg/code/twop-tools')
import twoplib

tiffs_folder = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-02-08_JJP-05425_1/"
tiffs_folder = "/home/georg/data/local_imaging/JJP-05472_chili_first_test/"
# %% find bad frames
os.chdir(tiffs_folder)
tiffs = np.sort([f for f in os.listdir() if f.endswith('tif')])

# %% n_frames per file
n_frames_per_file = [twoplib.get_n_frames(tif) for tif in tiffs]

# %% frame stats
frame_stats = []
for tif in tqdm(tiffs):
    Data = twoplib.get_data(tif, meta=False)
    avgs = np.average(np.average(Data,axis=1),axis=1)
    medians = np.median(np.median(Data,axis=1),axis=1)
    sds = np.std(np.std(Data,axis=1),axis=1)
    frame_stats.append((avgs,medians,sds))

frame_stats = np.concatenate(frame_stats,axis=1).T

# %%
fig, axes = plt.subplots(nrows=3,sharex=True)
for i in range(3):
    axes[i].plot(frame_stats[:,i])

# %% isolate if avg chunk has a negative slope?
n_samp_per_chunk = 1000
n_frames, _ = frame_stats.shape
avgs = frame_stats[:,0]

n_chunks = np.floor(n_frames / n_samp_per_chunk).astype('int32')
from scipy.stats import linregress
slopes = []
for i in tqdm(range(n_chunks)):
    m = linregress(np.arange(n_samp_per_chunk), avgs[i*n_samp_per_chunk:(i+1)*n_samp_per_chunk]).slope
    slopes.append(m)
slopes = np.array(slopes)

fig, axes = plt.subplots()
axes.plot(avgs,color='k')
twinx = plt.twinx(axes)
twinx.axhline(0,color='r')
twinx.plot(np.arange(0,n_chunks*n_samp_per_chunk,n_samp_per_chunk), slopes)
# %%
