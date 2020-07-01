%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
import scipy as sp
from scipy.signal import medfilt
from tqdm import tqdm
import behavior_analysis_utils as bhv
from matplotlib import cm

path = Path(r"D:\TaskControl\Animals\JJP-00885\2020-06-24_13-50-31_learn_to_push_alternating")

# def sync_harp_arudino(harp_csv_path, arduino_log_path):

harp_csv_path = path.joinpath("bonsai_harp_log.csv")

with open(harp_csv_path,'r') as fH:
    lines = fH.readlines()

header = lines[0].split(',')

t_sync = []
LoadCellDf = []
synclines = []
for line in tqdm(lines[1:]):
    elements = line.split(',')
    if elements[0] == '3': # line is an event
        if elements[1] == '33': # line is a load cell read
            data = line.split(',')[2:5]
            LoadCellDf.append(data)
        if elements[1] == '34': # line is a digital input timestamp
            line = line.strip().split(',')
            if line[3] == '1':
                t_sync.append(float(line[2])*1000) # convert to ms

LoadCellDf = pd.DataFrame(LoadCellDf,columns=['t','x','y'],dtype='float')
LoadCellDf['t_harp'] = LoadCellDf['t'] # keeps the original
LoadCellDf['t'] = LoadCellDf['t'] * 1000

# write to disk
LoadCellDf.to_csv(path / "loadcell_data.csv")
np.save(path / "loadcell_sync.npy", np.array(t_sync,dtype='float32'))

# get the arduino log
log_path = path / "arduino_log.txt"
code_map_path = path / "learn_to_push_alternating" / "Arduino" / "src" / "event_codes.h"

### READ 
CodesDf = bhv.parse_code_map(code_map_path)
code_map = dict(zip(CodesDf['code'],CodesDf['name']))
LogDf = bhv.parse_arduino_log(log_path, code_map)

t_arduino = LogDf.groupby('name').get_group("TRIAL_AVAILABLE_STATE")['t'].values
t_harp = np.array(t_sync)

print(t_arduino.shape)
print(t_harp.shape)

plt.figure()
plt.plot(sp.diff(t_arduino))
plt.plot(sp.diff(t_harp))

res = stats.linregress(t_arduino,t_harp) # sometimes hacky +1 -1 here
m,b = res.slope,res.intercept

LogDf['t_arduino'] = LogDf['t']
LogDf['t'] = LogDf['t']*m + b

LogDf.to_csv(path / "LogDf.csv")


"""
########  ##        #######  ########  ######
##     ## ##       ##     ##    ##    ##    ##
##     ## ##       ##     ##    ##    ##
########  ##       ##     ##    ##     ######
##        ##       ##     ##    ##          ##
##        ##       ##     ##    ##    ##    ##
##        ########  #######     ##     ######
"""
# %%
"""
    TRAJECTORIES
"""

window_size = 1000
LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(window_size).median()
LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(window_size).median()

fig, axes = plt.subplots(ncols=2,sharex=True,sharey=True)
pre,post = -500,500
no_splits = 5
colors = cm.RdPu(np.linspace(0, 1, no_splits))

event_times = bhv.get_events_from_name(LogDf,"CHOICE_LEFT")

# 1st dim is number of events, 2nd is window width, 3rd columns of Df (x an y are 3nd and 4th)
F = []

for t in event_times['t']:
    trial = bhv.time_slice(LoadCellDf,t+pre,t+post)
    F.append(trial.to_numpy())

F_split = np.array_split(F,no_splits)

for i, (chunk, clr) in enumerate(zip(F_split,colors)):

    avg_chunk = np.average(chunk,0) # average along trials
    axes[0].plot(avg_chunk[:,1], avg_chunk[:,2], alpha=0.5, lw=1, color = clr)

event_times = bhv.get_events_from_name(LogDf,"CHOICE_RIGHT")

# 1st dim is number of events, 2nd is window width, 3rd columns of Df (x an y are 3nd and 4th)
F = []

for t in event_times['t']:
    trial = bhv.time_slice(LoadCellDf,t+pre,t+post)
    F.append(trial.to_numpy())

F_split = np.array_split(F,no_splits)

for i, (chunk, clr) in enumerate(zip(F_split,colors)):

    avg_chunk = np.average(chunk,0) # average along trials
    axes[1].plot(avg_chunk[:,1], avg_chunk[:,2], alpha=0.5, lw=1, color = clr)

axes[0].set_ylim([-2000,2000])
axes[1].set_ylim([-2000,2000])
axes[0].set_xlim([-2000,2000])
axes[1].set_xlim([-2000,2000])

"""
    MAGNITUDE
"""
event_times = bhv.get_events_from_name(LogDf,"SECOND_TIMING_CUE")

fig, axes = plt.subplots()
pre,post = -2000,2000
tvec = sp.arange(pre,post,1)
ys = []
for t in event_times['t']:
    F = bhv.time_slice(LoadCellDf,t+pre,t+post)
    y = sp.sqrt(F['x']**2+F['y']**2)
    ys.append(y)
    axes.plot(tvec,y,lw=1,alpha=0.5)

# center
F['x'] = F['x'] - sp.average(F['x'])
F['y'] = F['y'] - sp.average(F['y'])

Fmag = np.array(ys).T
axes.plot(tvec,sp.average(Fmag,1),'k',lw=3)
axes.axvline(0, linestyle=':',alpha=0.5)

"""
    HEATMAPS
"""



# %%
"""
    Reaction time plots
"""
fig = plt.figure()

spans = bhv.get_spans_from_event_names(LogDf, 'TRIAL_ENTRY_EVENT', 'ITI_STATE')
TrialDfs = []
for i,span in spans.iterrows():
    TrialDfs.append(bhv.time_slice(LogDf,span['t_on'],span['t_off']))

# # Getting a list of trialDfs in which trials are both sucessfull and left choice
# OurTrialDfs = []
# for TrialDf in TrialDfs:
#     if "CHOICE_LEFT_EVENT" in TrialDf.name.values and "TRIAL_SUCCESSFUL_EVENT" in TrialDf.name.values:
#         OurTrialDfs.append(TrialDf)

# Getting rt's from left choice trials
left_choice_Dfs, right_choice_Dfs = [],[]
rt_left_choice, rt_right_choice = [],[]
for TrialDf in TrialDfs:
    if "CHOICE_LEFT_EVENT" in TrialDf.name.values:
        left_choice_Dfs.append(TrialDf)

        left_choice_time = TrialDf.loc[TrialDf['name'] == 'CHOICE_LEFT_EVENT']['t']
        second_cue_time = TrialDf.loc[TrialDf['name'] == 'SECOND_TIMING_CUE_EVENT']['t']

        rt_left_choice.append(int(left_choice_time.values - second_cue_time.values))

    if "CHOICE_RIGHT_EVENT" in TrialDf.name.values:
        right_choice_Dfs.append(TrialDf)

        right_choice_time = TrialDf.loc[TrialDf['name'] == 'CHOICE_RIGHT_EVENT']['t']
        second_cue_time = TrialDf.loc[TrialDf['name'] == 'SECOND_TIMING_CUE_EVENT']['t']

        rt_right_choice.append(int(right_choice_time.values - second_cue_time.values))


plt.hist(rt_left_choice, 25, range = (0,2000), 
        alpha=0.5, color='red', edgecolor='none', label = 'Left choice')
plt.hist(rt_right_choice, 25, range = (0,2000), 
        alpha=0.5, color='green', edgecolor='none', label = 'Right choice')
plt.ylabel('Number of trials')
plt.xlabel('Reaction time (ms)')

plt.legend(loc='upper right', frameon=False)          

# %%
"""
    Fx and Fy exploration
"""
# (same data as previous heatmaps)
fig = plt.figure()

Fx_split = np.array_split(Fx,10)
Fy_split = np.array_split(Fy,10)
Fx_split.reverse()
Fy_split.reverse()

colors = cm.RdPu(np.linspace(0, 1, len(Fx_split)))
np.flip(colors)

# Histograms for Fx and Fy and respective normal distribution fits
for i, (chunk_x, chunk_y, clr) in enumerate(zip(Fx_split, Fy_split, colors),1):

    ax1 = fig.add_subplot(221)
    _, bins_x, _ = plt.hist(chunk_x.reshape(-1,1), 50, color=clr, range = (-4000,4000), density=1, alpha=0.3, zorder=i)
    mu, sigma = sp.stats.norm.fit(chunk_x.reshape(-1,1))
    best_fit_line = sp.stats.norm.pdf(bins_x, mu, sigma)
    ax1.set_ylabel('X axis (Left/Right)')

    ax2 = fig.add_subplot(222)
    ax2.plot(bins_x, best_fit_line, color=clr, zorder=i)

    ax3 = fig.add_subplot(223)
    _, bins_y, _ = plt.hist(chunk_y.reshape(-1,1), 50, color=clr ,range = (-4000,4000), density=1, alpha=0.3, zorder=i)
    mu, sigma = sp.stats.norm.fit(chunk_y.reshape(-1,1))
    best_fit_line = sp.stats.norm.pdf(bins_y, mu, sigma)
    ax3.set_ylabel('Y axis (Back/Front)')

    ax4 = fig.add_subplot(224)
    ax4.plot(bins_y, best_fit_line, color=clr, zorder=i)

    fig.tight_layout()

#fig, axes = plt.subplots(ncols=10)


# %%
