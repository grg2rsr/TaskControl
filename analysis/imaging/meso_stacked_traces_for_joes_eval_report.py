# %% imports
%matplotlib qt5
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import caiman as cm
from caiman.source_extraction.cnmf import cnmf as cnmf
from pathlib import Path

# %% load footprints
# path = "/media/georg/data/mesoscope/first data/with behavior/2021-08-24_day1_overview/reshaped/memmap__d1_1128_d2_1068_d3_1_order_C_frames_3901_sel.hdf5"
path = "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_1/reshaped/memmap__d1_1892_d2_2504_d3_1_order_C_frames_850_sel.hdf5"

# split 0 
path = "/media/georg/data/mesoscope/first data/with behavior/2021-08-25_day2_square_3/split_0/memmap__d1_1892_d2_626_d3_1_order_C_frames_7021__split_0_sel.hdf5"
cnmf2 = cnmf.load_CNMF(path)

# %% infer stuff 
p = Path(cnmf2.mmap_file).stem.split('_')
xpx = int(p[p.index('d1')+1])
ypx = int(p[p.index('d2')+1])
nFrames = int(p[p.index('frames')+1])

# with open(folder.parent / 'meta.json','r') as fH:
#     meta = json.load(fH)

# or set for now
fs = 3.03

# %%
cnmf2.estimates.detrend_df_f(quantileMin=8,frames_window=100)
D = cnmf2.estimates.F_dff
D_orig = copy(D)
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
fig, axes = plt.subplots(figsize=[6,6]) 
nCells = D.shape[0]
nFrames = D.shape[1]
fs = 3.03
dt = 1/fs
tvec = np.arange(nFrames) * dt
from copy import copy
d = copy(D)
d = d[order,:]

# ysep = 0.05
# for i in range(nCells)[::-1]:
#     axes.fill_between(tvec, np.zeros(D.shape[1]) +i*ysep, d[i,:]+i*ysep, alpha=1, color='white',zorder=-i,lw=0.7)
#     lines = axes.plot(tvec, d[i,:] + i*ysep, color='k', lw=0.75, alpha=0.8,zorder=-i)

yzoom = 25
for i in range(nCells)[::-1]:
    axes.fill_between(tvec, np.zeros(D.shape[1]) + i, d[i,:] * yzoom+i, alpha=1, color='white',zorder=-i,lw=0.7)
    lines = axes.plot(tvec, d[i,:] * yzoom + i, color='k', lw=0.5, alpha=0.9,zorder=-i)

xpos = 102
axes.text(xpos+3,yzoom/2,'1 dF/F', ha='center', va='center', rotation=90)
line, = axes.plot([xpos, xpos],[0, 1*yzoom],lw=2,color='k')
line.set_clip_on(False)

axes.set_xlim(0, 100)
axes.set_ylim(-yzoom/2, D.shape[0]+1*yzoom/2)

axes.set_xlabel('time (s)')
axes.set_ylabel('cells')

import seaborn as sns
sns.despine(fig)
fig.tight_layout()
# plt.savefig('stacked_lines_meso.png',dpi=600)

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


# %%
N = 1000
frames = np.arange(N)
y_start = np.zeros(N)
y_stop = np.ones(N) * nCells*ysep
y_stop[:int(N/4)] = np.linspace(nCells*ysep/10,nCells*ysep,int(N/4))
zoom_y = np.stack([y_start, y_stop],axis=1)

w = 50
w2 = 250
x_start = np.zeros(N)
x_start[int(N/4):] = np.linspace(0,(nFrames-2*w)/fs,N-int(N/4))
x_stop = x_start + w
zoom_x = np.stack([x_start,x_stop],axis=1)

def init():
    axes.set_xlim(0, w)
    axes.set_ylim(0, nCells*ysep/10)
    return axes

def update(i):
    axes.set_ylim(*zoom_y[i])
    axes.set_xlim(*zoom_x[i])
    return axes

ani = FuncAnimation(fig, update, frames=frames, init_func=init, blit=False, interval=1)

import matplotlib.animation as animation
moviewriter = animation.FFMpegFileWriter(fps=62)
moviewriter.setup(fig, 'test.mp4', dpi=600)
n = frames.shape[0]
from tqdm import tqdm
for j in tqdm(range(n)):
    update(j)
    moviewriter.grab_frame()
moviewriter.finish()

# %%
