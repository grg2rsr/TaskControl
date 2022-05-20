# %%
"""
purpose: trying to figure out how to converge faster to a desired p dist
when sampling for it.
can we get better than random?
Margas idea: take p values (dist is discrete) and multiply by trial numbers,
gives trial number type for each, randomize, draw those
-> similar to the pseudorandom I did for RIOlib

the idea here:
take the desired p values, calculate observed p values, use the difference to bias
the sampling from the distribution somehow.
will this be faster than just purely random?
"""

# %%
%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np

p_des = np.array([2,1,1,2]) # those are ratios
p_des = p_des / p_des.sum() # now this should be a p dist

def sample_p(p):
    r = np.random.rand()
    n = len(p)
    for i in range(n):
        p_cum = 0
        for j in range(i+1):
            p_cum += p[j]
        if r < p_cum:
            return i
    else:
        return -1

# %%
N = 250
samples = np.array([sample_p(p_des) for i in range(N)])

# %% a comparison plot
fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')

# %%
errs = []
for k in range(1000):
    samples = np.array([sample_p(p_des) for i in range(N)])
    rss = np.sum( (np.histogram(samples,bins)[0]/250 - p_des)**2 )
    errs.append(rss)

errs = np.array(errs)
print(np.average(errs)) # <- average error when doing it fully random
# = 0.003

# %% adjusted sampling
def get_adjusted_samples(N,th=10):
    samples = []
    for j in range(N):
        if j < th:
            samples.append(sample_p(p_des))
        else:
            p_obs = np.histogram(samples,bins)[0]/N
            p_this = np.clip(p_des - p_obs,0,1)
            p_this = p_this / p_this.sum()
            samples.append(sample_p(p_this))
    return samples

# %%
errs = []
for k in range(1000):
    samples = get_adjusted_samples(N)
    rss = np.sum( (np.histogram(samples,bins)[0]/250 - p_des)**2 )
    errs.append(rss)

errs = np.array(errs)
print(np.average(errs)) # <- average error when doing it with adjusted sampling
# = 1.674311111111111e-05

# %% comparing with an actual session
from pathlib import Path
session_folder = "/home/georg/Projects/TaskControl/Animals/123/2022-05-09_14-53-24_twodistributionsv6_GR"
path = Path(session_folder) / "arduino_log.txt"

with open(path,'r') as fH:
    lines = fH.readlines()
lines = [line for line in lines if line.startswith("<VAR this_trial_type")]

# %%
samples = np.array([line.split(' ')[2] for line in lines],dtype='int32')

p_des = np.array([0.55, 0, 0.45])

fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')
# %%

with open(path,'r') as fH:
    lines = fH.readlines()
lines = [line for line in lines if line.startswith("<VAR this_trial_type")]

# %%
import sys
import pandas as pd
from pathlib import Path
sys.path.append("/home/georg/Projects/TaskControl")
from Utils import utils

SessionsDf = utils.get_sessions("/home/georg/Projects/TaskControl/Animals/123")
session_path = Path(SessionsDf.iloc[-1]['path'])

from Utils import behavior_analysis_utils as bhv
LogDf = bhv.get_LogDf_from_path(session_path / 'arduino_log.txt')

def get_trial_type(TrialDf):
    var_name = "this_trial_type"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_delay(TrialDf):
    var_name = "this_delay"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

def get_reward_magnitude(TrialDf):
    var_name = "reward_magnitude"
    try:
        Df = TrialDf.groupby('var').get_group(var_name)
        var = Df.iloc[0]['value']
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)

metrics = (get_trial_type, get_delay, get_reward_magnitude)

SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics, trial_entry_event='TRIAL_ENTRY_STATE', trial_exit_event='ITI_STATE')

SessionDf.groupby('this_trial_type').get_group(0.0)['this_delay'].values
# %%
delays = SessionDf.groupby('this_trial_type').get_group(0.0)['this_delay'].values
mapping = [0, 150, 300, 600]
samples = [mapping.index(delay) for delay in delays]

# %%
p_des = np.array([0.25, 0.25, 0.25, 0.25])
fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')

# %%
samples = SessionDf['this_trial_type'].values
p_des = np.array([0.55, 0, 0.45])
fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')

# %%
rewards = SessionDf.groupby('this_trial_type').get_group(2.0)['reward_magnitude'].values
mapping = [1, 2.75, 4.5, 6.25, 8]
samples = [mapping.index(reward) for reward in rewards]

p_des = np.array([0.25, 0.167, 0.167, 0.167, 0.25])

fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')


# %%
