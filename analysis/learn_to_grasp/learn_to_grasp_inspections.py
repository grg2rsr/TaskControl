# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

sys.path.append('..')

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv
from Utils import behavior_analysis_utils as bhv
import pandas as pd

# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
from Utils import utils

# %%
folder = Path("/home/georg/data/grasping_animals/")
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(folder)

# %%

# lifeguard
folder = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909"
Animal = utils.Animal(folder)

day = 0
folder = Path(utils.get_sessions(Animal.folder).path[day])

LogDf = bhv.get_LogDf_from_path(folder / "arduino_log.txt")
LogDf['min'] = LogDf['t'] / 60000

# %% check each reach
ReachesDf = bhv.get_spans_from_names(LogDf, "REACH_ON", "REACH_OFF")

# drop invalid
min_th = 5
max_th = 2000

binds = np.logical_and(ReachesDf['dt'].values > min_th, ReachesDf['dt'].values < max_th)

ReachesDf = ReachesDf.loc[binds]

ReachesDf['is_grasp'] = False
for i, row in ReachesDf.iterrows():
    t_on = row['t_on']
    t_off = row['t_off']
    Df = bhv.time_slice(LogDf, t_on, t_off)
    if 'GRASP_ON' in Df.name.values:
        ReachesDf.loc[i,'is_grasp'] = True
GraspsDf = ReachesDf.groupby('is_grasp').get_group(True)

# %%
fig, axes = plt.subplots(ncols=2, gridspec_kw=dict(width_ratios=(1,0.2)))
axes[0].plot(ReachesDf['t_on']/6e4, ReachesDf['dt'],'.',label='reach')
axes[0].plot(GraspsDf['t_on']/6e4, GraspsDf['dt'],'.',label='grasp')
wm = 3
w = wm*60*1000
w2 = int(w/2)
avgs = []
t_max = LogDf.iloc[-1]['t']
for t in tqdm(range(w2*2,int(t_max - w2),w2)):
    Df_reach = bhv.time_slice(ReachesDf, t-w/2, t+w/2, col='t_on')
    avgs.append((t,np.nanmean(Df_reach['dt'])))

avgs = np.array(avgs)
axes[0].plot(avgs[:,0]/6e4,avgs[:,1],color='red',label='%s min avg' % wm)
axes[0].set_ylim(0,500)
axes[0].legend()

title = Animal.display() + ' - day %s' % day
axes[0].set_title(title)
axes[0].set_xlabel('time (min)')
axes[0].set_ylabel('grasp duration (ms)')

# hist
bins = np.linspace(0,500,100)
axes[1].hist(ReachesDf['dt'],bins=bins,orientation='horizontal')
axes[1].hist(GraspsDf['dt'],bins=bins,orientation='horizontal')
axes[1].set_ylim(0,500)
sns.despine(fig)
plt.savefig(Path('/home/georg/Desktop/plots/reaching') / (title +'.png'))








# %% find corresponding reach for each grasp
# for some reason this fails on some!
M = ReachesDf['t_off'].values[:,sp.newaxis] - GraspsDf['t_off'].values[sp.newaxis,:]
ix = np.argmin(M**2,axis=0)
ReachesDf['is_grasp'] = False
ReachesDf.loc[ix,'is_grasp'] = True
GraspsDf = ReachesDf.groupby('is_grasp').get_group(True)

# %% hist
fig, axes = plt.subplots()



# %%
with open(folder / 'arduino_log.txt','r') as fH:
    lines = fH.readlines()
# %%
lines = [line.strip() for line in lines]
lines = [line for line in lines if line is not '']
var_lines = [(i,line) for i,line in enumerate(lines) if line.startswith('<Arduino received: SET min_grasp_dur ')]
# %%
for i in range(1,len(var_lines)):
    print(lines[var_lines[i][0] - 10])
# %%
ons = ReachesDf['t_on'].values
offs = ReachesDf['t_off'].values
# %%
fig, axes = plt.subplots()
axes.hist(ons - np.roll(offs,1),bins=sp.linspace(0,100,100))

# %%
Df = bhv.time_slice(LogDf,23*60*1000,24*60*1000)

# plot a LogDf slice
# plot_spans=True, plot_vars=False
# fold x on None
events = list(Df.name.unique())
if np.nan in events:
    events.remove(np.nan)

spans = ['_'.join(ev.split('_')[:-1]) for ev in events if ev.endswith('_ON')]

Events = bhv.get_events(Df,events)
Spans = bhv.get_spans(Df, spans)

n = Df.name.unique().shape[0]
colors = sns.color_palette('tab10',n_colors=n)

colors = dict(zip(events,colors))

fig, axes = plt.subplots()
for event in events:
    times = Df.groupby('name').get_group(event)['t'].values
    T = np.repeat(times[np.newaxis,:],2,axis=0)
    Y = sp.zeros(T.shape)
    Y[1,:] = 1
    axes.plot(T,Y, color=colors[event])