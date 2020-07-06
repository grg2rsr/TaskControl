#%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
import scipy as sp
from scipy.signal import medfilt
from tqdm import tqdm
import behavior_analysis_utils as bhv
import behavior_plotters as bhv_plt
from matplotlib import cm

path = Path(r"D:\TaskControl\Animals\JJP-00885\2020-06-24_13-50-31_learn_to_push_alternating")

# def sync_harp_arudino(harp_csv_path, arduino_log_path):

""" 1 """
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

""" 2 """
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

# Removal of median computed on the past 1 sec. (default left window in pandas rolling method)
window_size = 1000
LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(window_size).median()
LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(window_size).median()

align_reference = "SECOND_TIMING_CUE_EVENT"
pre, post = -1000, 4000

axes = bhv_plt.plot_forces_heatmaps(LogDf, LoadCellDf, align_reference, pre, post)