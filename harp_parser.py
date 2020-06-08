%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
path = Path("D:/TaskControl/Animals/123/2020-06-08_15-01-48_headfix_timing_dev/bonsai_harp_log.csv")

with open(path,'r') as fH:
    lines = fH.readlines()

header = lines[0].split(',')

t_sync = []
LCDf = []

for line in lines[1:]:
    elements = line.split(',')
    if elements[0] == '3': # line is an event
        if elements[1] == '33': # line is a load cell read
            data = line.split(',')[2:5]
            LCDf.append(data)
        if elements[1] == '34': # line is a digital input timestamp
            t_sync.append(float(line.split(',')[2]))

LCDf = pd.DataFrame(LCDf,columns=['t','x','y'],dtype='float')

# write to disk
LCDf.to_csv(path.parent / "loadcell_data.csv")
np.save(path.parent / "loadcell_sync.npy", np.array(t_sync,dtype='float32'))
