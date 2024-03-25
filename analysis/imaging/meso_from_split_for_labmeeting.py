# %% imports
%matplotlib qt5
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import caiman as cm
from caiman.source_extraction.cnmf import cnmf as cnmf
from pathlib import Path
from tqdm import tqdm

# %% load footprints

# split 0
paths = ["/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/split_0/memmap__d1_1892_d2_626_d3_1_order_C_frames_7021__split_0_sel.hdf5",
         "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/split_1/memmap__d1_1892_d2_626_d3_1_order_C_frames_7021__split_1_sel.hdf5",
         "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/split_2/memmap__d1_1892_d2_626_d3_1_order_C_frames_7021__split_2_sel.hdf5",
         "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/split_3/memmap__d1_1892_d2_626_d3_1_order_C_frames_7021__split_3_sel.hdf5"]

cnmf2s = []
for i , path in enumerate(tqdm(paths)):
    cnmf2 = cnmf.load_CNMF(path)
    cnmf2s.append(cnmf2)

# %% infer stuff 
# p = Path(cnmf2.mmap_file).stem.split('_')
# xpx = int(p[p.index('d1')+1])
# ypx = int(p[p.index('d2')+1])
# nFrames = int(p[p.index('frames')+1])

# with open(folder.parent / 'meta.json','r') as fH:
#     meta = json.load(fH)

# or set for now
fs = 3.06231

# %% getting D
Ds = []
for cnmf2 in cnmf2s:
    cnmf2.estimates.detrend_df_f(quantileMin=8,frames_window=50)
    D = cnmf2.estimates.F_dff
    Ds.append(D)

D = np.concatenate(Ds,axis=0)
outpath = "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/D_all_splits.npy"
np.save(outpath,D)
good_inds = np.load("/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/good_inds_all_splits.npy")
D = D[good_inds,:]

# %% sorting by kmeans
from sklearn.cluster import KMeans
k = 5 # todo find a way to find k
clust = KMeans(n_clusters=k)
clust.fit(D)
labels = clust.labels_
order = np.argsort(labels)

# %% stacked y plot
# fig, axes = plt.subplots(figsize=[6,9]) 
fig, axes = plt.subplots(figsize=[8,9]) 
nCells = D.shape[0]
nFrames = D.shape[1]
fs = 3.06231
dt = 1/fs
tvec = np.arange(nFrames) * dt
from copy import copy
d = copy(D)
d = d[order,:]

yzoom = 65
for i in range(nCells)[::-1]:
    axes.fill_between(tvec, np.zeros(D.shape[1]) , d[i,:] * yzoom+i, alpha=1, color='white',zorder=-i,lw=0.7)
    lines = axes.plot(tvec, d[i,:] * yzoom + i, color='k', lw=0.5, alpha=0.9,zorder=-i)

# t = event_times[7] / 1e3    
t = 200
pre, post = 0,30
axes.set_xlim(t+pre, t+post)
axes.set_ylim(-yzoom/2, D.shape[0]+1*yzoom/2)

axes.set_ylim(0, D.shape[0]+1*yzoom/4)

# axes.axvline(t,alpha=1.0,color='r',lw=2,linestyle=':')

xpos = t + post+2
# axes.text(xpos+3,yzoom/2,'1 dF/F', ha='center', va='center', rotation=90)
# line, = axes.plot([xpos, xpos],[0, 1*yzoom],lw=2,color='k')
# line.set_clip_on(False)

axes.set_xlabel('time (s)')
axes.set_ylabel('cells')

import seaborn as sns
sns.despine(fig)
fig.tight_layout()
plt.savefig('/home/georg/Desktop/plots for labmeeting/some_cells_stacked_traces_tslice.png',dpi=600)

# %% alternative using matshow
fig, axes = plt.subplots(figsize=[4,4]) 
im = axes.matshow(d, cmap='viridis',origin='lower', extent=(0, tvec[-1], 0, nCells),vmin=-0.1,vmax=0.4)
# axes.matshow(d, cmap='RdBu_r',origin='lower', extent=(0, tvec[-1], 0, nCells),vmin=-0.4,vmax=0.4)
axes.xaxis.tick_bottom()
axes.set_xlim(0,100)
axes.set_aspect('auto')
axes.set_xlabel('time (s)')
axes.set_ylabel('cells')
plt.colorbar(im,shrink=0.3, label='dF/F')
fig.tight_layout()
fig.subplots_adjust(right=0.9)

