# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
import utils

from behavior_plotters import *

# %%
"""
 
 ########  ########    ###    ########  
 ##     ## ##         ## ##   ##     ## 
 ##     ## ##        ##   ##  ##     ## 
 ########  ######   ##     ## ##     ## 
 ##   ##   ##       ######### ##     ## 
 ##    ##  ##       ##     ## ##     ## 
 ##     ## ######## ##     ## ########  
 
"""

# %%
log_path = utils.get_file_dialog()

# %%
LogDf = bhv.get_LogDf_from_path(log_path)
LogDf = bhv.filter_bad_licks(LogDf)

# make SessionDf - slice into trials
TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_AVAILABLE_STATE","ITI_STATE")

TrialDfs = []
for i, row in tqdm(TrialSpans.iterrows()):
    TrialDfs.append(bhv.time_slice(LogDf,row['t_on'],row['t_off']))

SessionDf = bhv.parse_trials(TrialDfs, (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.get_interval))


# %% psychometrics
# %% adding logistic regression fit
from sklearn.linear_model import LogisticRegression
from scipy.special import expit

# get only the subset with choices
SDf = SessionDf.groupby('has_choice').get_group(True)
y = SDf['choice'].values == 'right'
x = SDf['this_interval'].values

# plot choices
fig, axes = plt.subplots(figsize=[6,2])
axes.plot(x,y,'.',color='k',alpha=0.5)
axes.set_yticks([0,1])
axes.set_yticklabels(['short','long'])
axes.set_ylabel('choice')
axes.axvline(1500,linestyle=':',alpha=0.5,lw=1,color='k')

def log_reg(x,y, x_fit=None):
    """ x and y are of shape (N,) y are choices in [0,1] """
    if x_fit is None:
        x_fit = sp.linspace(x.min(),x.max(),100)

    cLR = LogisticRegression()
    cLR.fit(x[:,sp.newaxis],y)

    y_fit = expit(x_fit * cLR.coef_ + cLR.intercept_).flatten()
    return y_fit

x_fit = sp.linspace(0,3000,100)
line, = plt.plot([],color='red', linewidth=2,alpha=0.75)
line.set_data(x_fit, log_reg(x, y, x_fit))

# %% random margin - without bias
t = SDf['this_interval'].values
R = []
for i in tqdm(range(100)):
    rand_choices = sp.random.randint(2,size=t.shape).astype('bool')
    R.append(log_reg(x, rand_choices,x_fit))
R = sp.array(R)

alpha = .5
R_pc = sp.percentile(R, (alpha, 100-alpha), 0)
plt.fill_between(x_fit, R_pc[0],R_pc[1],color='blue',alpha=0.5)

# %% random margin - without animal bias
t = SDf['this_interval'].values
bias = (SessionDf['choice'] == 'right').sum() / SessionDf.shape[0] # right side bias
R = []
for i in tqdm(range(100)):
    rand_choices = sp.rand(t.shape[0]) < bias
    R.append(log_reg(x, rand_choices,x_fit))
R = sp.array(R)

alpha = .5
R_pc = sp.percentile(R, (alpha, 100-alpha), 0)
plt.fill_between(x_fit, R_pc[0],R_pc[1],color='orange',alpha=0.5)

# %% histograms
fig,axes = plt.subplots()
shorts = SDf.groupby('choice').get_group('left')['this_interval'].values
longs = SDf.groupby('choice').get_group('right')['this_interval'].values
kwargs = dict(alpha=.5, density=True, bins=sp.linspace(0,3000,15))
axes.hist(shorts, **kwargs, label='short')
axes.hist(longs, **kwargs, label='long')
plt.legend()
axes.set_xlabel('interval (ms)')
axes.set_ylabel('density')


"""
##        #######     ###    ########   ######  ######## ##       ##
##       ##     ##   ## ##   ##     ## ##    ## ##       ##       ##
##       ##     ##  ##   ##  ##     ## ##       ##       ##       ##
##       ##     ## ##     ## ##     ## ##       ######   ##       ##
##       ##     ## ######### ##     ## ##       ##       ##       ##
##       ##     ## ##     ## ##     ## ##    ## ##       ##       ##
########  #######  ##     ## ########   ######  ######## ######## ########
"""

# %% syncing
LoadCellDf, harp_sync = bhv.parse_harp_csv(log_path.parent / "bonsai_harp_log.csv", save=True)
arduino_sync = bhv.get_arduino_sync(log_path)

# %% - checking if the triggering worked
t_harp = harp_sync['t'].values
t_arduino = arduino_sync['t'].values

plt.plot(sp.diff(t_harp),label='harp')
plt.plot(sp.diff(t_arduino),label='arduino')
plt.legend()


# %%
t_harp = pd.read_csv(log_path.parent / "harp_sync.csv")['t'].values
t_arduino = pd.read_csv(log_path.parent / "arduino_sync.csv")['t'].values

m,b = bhv.sync_clocks(t_harp, t_arduino, log_path)
LogDf = pd.read_csv(log_path.parent / "LogDf.csv")