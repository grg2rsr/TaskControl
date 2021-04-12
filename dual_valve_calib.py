# %%
import scipy as sp
from scipy import stats
import pandas as pd

path = 'valve_calib_reaching_box_31_3_2021.csv'

Df = pd.read_csv(path)

# time is in ms, weight is in g
Df['weight'] = Df['weight']*1000
Df['w_per_rep'] = Df['weight'].values / Df['reps'].values

for i, side in enumerate(['L','R']):
    df = Df.groupby('side').get_group(side)
    m, b = stats.linregress(df['time'].values, df['w_per_rep'].values)[:2]
    print("valve_ul_ms for side %s : %.2e" % (side, m))
    # print("valve_ul_ms for side %s : %.6f" % (side, m))

# %% w plot
%matplotlib qt5
import matplotlib.pyplot as plt
def lin(x,m,b):
    return m*x+b
fig, axes = plt.subplots()
fvec = sp.linspace(0,200,5)
for i, side in enumerate(['L','R']):
    df = Df.groupby('side').get_group(side)
    m, b = stats.linregress(df['time'].values, df['w_per_rep'].values)[:2]
    dots, = axes.plot(df['time'].values, df['w_per_rep'].values,'o',label=side)
    axes.plot(fvec, lin(fvec, m, b),lw=1,linestyle=':',color=dots.get_color())
    print("valve_ul_ms for side %s : %.2e" % (side, m))
axes.legend()
# %%
