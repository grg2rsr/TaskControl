%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
import scipy as sp
from tqdm import tqdm
path = Path(r"D:\TaskControl\Animals\JJP-00885\2020-06-17_13-53-13_learn_to_push")
harp_csv_path = path.joinpath("bonsai_harp_log.csv")

with open(harp_csv_path,'r') as fH:
    lines = fH.readlines()

header = lines[0].split(',')

t_sync = []
LCDf = []
synclines = []
for line in tqdm(lines[1:]):
    elements = line.split(',')
    if elements[0] == '3': # line is an event
        if elements[1] == '33': # line is a load cell read
            data = line.split(',')[2:5]
            LCDf.append(data)
        if elements[1] == '34': # line is a digital input timestamp
            line = line.strip().split(',')
            if line[3] == '1':
                t_sync.append(float(line[2])*1000) # convert to ms


LCDf = pd.DataFrame(LCDf,columns=['t','x','y'],dtype='float')
LCDf['t_harp'] = LCDf['t']
LCDf['t'] = LCDf['t'] * 1000

# write to disk
LCDf.to_csv(path / "loadcell_data.csv")
np.save(path / "loadcell_sync.npy", np.array(t_sync,dtype='float32'))

# get the arduino log
import behavior_analysis_utils as bhv
log_path = path / "arduino_log.txt"
code_map_path = path / "learn_to_push" / "Arduino" / "src" / "event_codes.h"

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

res = stats.linregress(t_arduino,t_harp[1:])
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
# all trajectories
fig, axes = plt.subplots()
axes.set_aspect('equal')
pre,post = -4000,4000
ev_times = bhv.get_events_from_name(LogDf,"SECOND_TIMING_CUE")
for t in ev_times['t']:
    F = bhv.time_slice(LCDf,t+pre,t+post)
    axes.plot(F['x'],F['y'])

# magnitude
fig, axes = plt.subplots()
pre,post = -4000,4000
tvec = sp.arange(pre,post,1)
ys = []
for t in ev_times['t']:
    F = bhv.time_slice(LCDf,t+pre,t+post)
    y = sp.sqrt(F['x']**2+F['y']**2)
    ys.append(y)
    axes.plot(tvec,y,lw=1,alpha=0.5)

Y = sp.array(ys)
axes.plot(tvec,sp.average(Y,0),'k',lw=3)
axes.axvline(0, linestyle=':',alpha=0.5)

# heatmaps
Fx = []
Fy = []
for t in ev_times['t']:
    F = bhv.time_slice(LCDf,t+pre,t+post)
    Fx.append(F['x'])
    Fy.append(F['y'])
Fx = sp.array(Fx)
Fy = sp.array(Fy)

fig, axes = plt.subplots(ncols=2)
axes[0].matshow(Fx,cmap='PiYG',vmin=-2000,vmax=2000)
axes[1].matshow(Fy,cmap='PiYG',vmin=-2000,vmax=2000)
for ax in axes:
    ax.set_aspect('auto')

    

