%matplotlib qt5
import scipy as sp
import pandas
import matplotlib.pyplot as plt
import pandas as pd

"""
    Method to calibrate valve
    1 - Run valve_calibration task with increments of reward volume (30,60,..)
    2 - Weight the resulting water that comes out (register to CSV) and refill to 5ml
    3 - Run this script to get slope (m) which is valve_ul_ms value
"""

Df = pd.read_csv('box1_valve.csv',names=['t','g'])

mg = Df['g'].values / 100 * 1000
ms = Df['t'].values

from scipy import stats
stats.linregress(ms,mg).slope

plt.plot(mg,ms,'o')