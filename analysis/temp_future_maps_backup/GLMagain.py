# %%
# %load_ext autoreload
# %autoreload 2
%matplotlib qt5
import matplotlib.pyplot as plt
import matplotlib as mpl
from tqdm import tqdm
import numpy as np
from pathlib import Path
import pandas as pd
import sys, os
import seaborn as sns
sys.path.append('/home/georg/code/twop-tools')
import twoplib
sys.path.append('/home/georg/Projects/TaskControl/analysis/temp_future_maps')

sys.path.append('/home/georg/Projects/TaskControl')
from Utils import behavior_analysis_utils as bhv

from my_logging import get_logger
logger = get_logger(level='info')
tqdm_disable = False

from data_structures import Signal


# %%

def get_meta(folder):
    """ potentially replace with JSON in the future """
    with open(folder / 'meta.txt','r') as fH:
        lines = [l.strip() for l in fH.readlines()]
    meta = dict([l.split(' ') for l in lines])
    return meta

def get_imaging_and_bhv_data(folder, signal_fname):
    """ returns dFF and SessionDf """

    # get metadata
    meta = get_meta(folder)

    # get bhv
    bhv_session_folder = animals_folder / animal_id / meta['bhv_session_name']

    # get tvec
    tvec = np.load(bhv_session_folder / "frame_timestamps_corr.npy")
    if "tvec_start" in meta.keys():
        tvec = tvec[ np.int32(meta['tvec_start']):-1] # -1 bc last frame sends trigger but is not saved
    # dFF = np.load(folder / "suite2p" / "plane0" / 'spks.npy').T
    dFF = np.load(folder / "suite2p" / "plane0" / signal_fname)
    stats = np.load(folder / "suite2p" / "plane0" / 'stat.npy', allow_pickle=True)

    # check
    if tvec.shape[0] != dFF.shape[0]:
        print("tvec: %i" % tvec.shape[0])
        print("dFF: %i" % dFF.shape[0])
    else:
        print("all good")

    # FIXME IMPORTANT - this just drops the overhanging frames
    if tvec.shape[0] > dFF.shape[0]:
        print("tvec longer than dFF: %i,%i" % (tvec.shape[0], dFF.shape[0]))
        tvec = tvec[:dFF.shape[0]] 
    if tvec.shape[0] < dFF.shape[0]:
        print("tvec shorter than dFF: %i,%i" % (tvec.shape[0], dFF.shape[0]))
        dFF = dFF[:tvec.shape[0]] 

    # get imaging data and bhv data
    F = Signal(dFF, tvec)
    SessionDf = pd.read_csv(bhv_session_folder / 'SessionDf.csv')

    return F, stats, SessionDf



# %%


"""
 
    ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
   ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
  ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
 ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""
# %% folders
animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging")
# folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05425/2023-03-10_JJP-05425_10")
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging_sessions_2/JJP-05472/2023-03-10_JJP-05472_10/")
animal_id = folder.parts[-2]

# %%
F, stats, SessionDf = get_imaging_and_bhv_data(folder, 'Z.npy')
meta = get_meta(folder)

# get UnitsDf
UnitsDf = pd.read_csv(folder / "UnitsDf.csv")

# %% 
bhv_session_folder = animals_folder / animal_id / meta['bhv_session_name']
LogDf = bhv.get_LogDf_from_path(bhv_session_folder / 'arduino_log.txt')

# preprocessing
LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min = 5, t_max=200)
LogDf = bhv.time_slice(LogDf, SessionDf.iloc[0]['t_on'], SessionDf.iloc[-1]['t_off'])

# reward_times = bhv.get_events_from_name(LogDf,"REWARD_EVENT")['t'].values
context_switch_time = bhv.get_events_from_name(LogDf,"CONTEXT_SWITCH_EVENT")['t'].values[0]
trial_times = bhv.get_events_from_name(LogDf,"TRIAL_ENTRY_EVENT")['t'].values
trial_labels = SessionDf['this_delay'].values.astype('int32')

trial_times_pre = trial_times[trial_times < context_switch_time]
trial_times_post = trial_times[trial_times > context_switch_time]

trial_labels_pre = SessionDf['this_delay'].values.astype('int32')[trial_times < context_switch_time]
trial_labels_post = SessionDf['this_delay'].values.astype('int32')[trial_times > context_switch_time]

# %% smoothing F?
w = np.ones(5)
w = w / w.sum()
Zs = np.zeros(F.shape)
for i in range(F.shape[1]):
    Zs[:,i] = np.convolve(F[:,i],w,mode='same')

Fs = Signal(Zs, F.t)

# %% pre / post here refers to pre / post manipulation

# import copy
# F_trial = copy.deepcopy(Fs)
# F_pre = copy.deepcopy(Fs)
# F_post = copy.deepcopy(Fs)

# prepost_trial = (-3000, 11000)

# F_trial.reslice(trial_times, *prepost_trial)
# F_trial.resort(trial_labels)

# F_pre.reslice(trial_times_pre, *prepost_trial)
# F_pre.resort(trial_labels_pre)

# F_post.reslice(trial_times_post, *prepost_trial)
# F_post.resort(trial_labels_post)

# %% selection
unit_sel_ix = np.where(np.logical_and(UnitsDf['skew'] > 1.5,UnitsDf['iscell']))[0]
print("%i cells in selection" % unit_sel_ix.shape[0])

Y = Fs.y[:,unit_sel_ix]



"""
 ######   ##       ##     ##
##    ##  ##       ###   ###
##        ##       #### ####
##   #### ##       ## ### ##
##    ##  ##       ##     ##
##    ##  ##       ##     ##
 ######   ######## ##     ##
"""

# %%
os.chdir('/home/georg/code/LR-RRR')
import RRRlib as rrr
os.chdir(folder)

# %% helper
def bin_times(tstamps, tvec):
    """ turns timestamps into binarized matrix
    probably horribly inefficient """
    T = np.zeros(tvec.shape[0])
    for t in tstamps:
        ix = np.argmin((tvec - t)**2)
        T[ix] = 1
    return T

# %% time continuous regressors
tvec = Fs.t
treg_names = []
tregs = []

# %% lick rate of entire session
from scipy import signal
lick_times = bhv.get_events_from_name(LogDf,"LICK_EVENT")['t'].values
t_start = np.min(LogDf['t'].values)
t_stop = np.max(LogDf['t'].values)
lick_tvec = np.arange(t_start, t_stop, 1)
f = np.zeros(lick_tvec.shape[0])
f[lick_times.astype('int32')-int(t_start)] = 1
sd = 100
w = signal.gaussian(sd*10, sd)
w = w / w.sum()
lick_rate = np.convolve(f,w,mode='same')*1e3 # do get to a rate is licks/s

# interpolate to frames
tvec = Fs.t
lick_rate_ip = np.interp(tvec, lick_tvec, lick_rate)

treg_names.append("lick_rate")
tregs.append(lick_rate_ip)

# %% plot
fig, axes = plt.subplots()
axes.plot(lick_tvec, f)
axes.plot(lick_tvec, lick_rate)
axes.plot(tvec, lick_rate_ip,'.')
reward_times = bhv.get_events_from_name(LogDf, "REWARD_COLLECTED_EVENT")['t']
for t in reward_times:
    axes.axvline(t,color='blue')

# # %% plot like above to verify
# tvec = FramesMap['t'].values
# pre, post = (-2000, 11000)

# delays = np.sort(SessionDf.this_delay.unique())
# n_delays = delays.shape[0]

# fig, axes = plt.subplots(nrows=n_delays)
# for i,delay in enumerate(delays):
#     # trial onset times
#     align_times = bhv.intersect(SessionDf, this_trial_type=0.0, this_delay=delay)['t_on'].values
    
#     Dsc = slice_D(lick_rate_ip[:,np.newaxis], tvec, align_times, pre, post)

#     S = Dsc[:,0,:]
#     extent = (pre,post,0,n_trials)
#     axes[i].matshow(S.T,vmin=0,vmax=10,extent=extent,origin='lower')
#     axes[i].axvline(0,lw=0.25,color='w')
#     axes[i].axvline(delay,lw=0.25,color='w')
#     axes[i].set_aspect('auto')
#     fig.tight_layout()

# works

# %% lagged regressors
tvec = Fs.t
lagreg_names = []
lagregs = []

# odors
odor_ids = LogDf.groupby('var').get_group('this_odor')['value'].values
# odor_unique = np.sort(np.unique(odor_ids))
odors_unique = [0,1,2,3] # hardcode to overwrite present odor 4 stim (manual error?)

odor_times = bhv.get_events_from_name(LogDf,"ODOR_ON")['t'].values
for i, odor in enumerate(odors_unique):
    lagreg_names.append("odor_%i_on"%odor)
    times = odor_times[odor_ids == odor]
    lagregs.append(bin_times(times,tvec))
    
# odor_times = bhv.get_events_from_name(LogDf,"ODOR_OFF")['t'].values
# for i, odor in enumerate(odors_unique):
#     lagreg_names.append("odor_%i_off"%odor)
#     times = odor_times[odor_ids == odor]
#     lagregs.append(bin_times(times,tvec))

# reward
reward_times = bhv.get_events_from_name(LogDf,"REWARD_EVENT")['t'].values
lagreg_names.append("reward")
lagregs.append(bin_times(reward_times,tvec))

# licks
lick_times = bhv.get_events_from_name(LogDf,"LICK_EVENT")['t'].values
lagreg_names.append("licks")
lagregs.append(bin_times(lick_times,tvec))

def expand_reg(reg, n_lags):
    lags = np.linspace(-n_lags/2,n_lags/2 - 1,n_lags).astype('int32')
    rolls = []
    for lag in lags:
        rolls.append(np.roll(reg,lag))
    reg_ex = np.stack(rolls).T
    return reg_ex

n_lags = 250 # pre and post?
X_lagreg = [expand_reg(reg, n_lags) for reg in lagregs]

# %% exponential decay, gamma style, time since last odor on
tvec = Fs.t

n_gammas = 20
gammas = np.linspace(.8,.99,n_gammas)
n_taps = 250
g = np.zeros((n_taps,n_gammas))
g[0,:] = gammas
for i in range(1,n_taps):
    g[i,:] = g[i-1,:] * gammas

g = g / np.sum(g,axis=0)[np.newaxis,:]

# %% exploring alternative time basis functions
n_basis = 20
n_taps = 250
mus = np.linspace(10,8000,n_basis)
sds = np.linspace(200,600,n_basis)
from scipy.stats.distributions import norm
dt = np.diff(Fs.t)[0]
tvec_basis = np.arange(0,n_taps*dt,dt)
g = np.zeros((n_taps,n_basis))
for i in range(n_basis):
    g[:,i] = norm.pdf(tvec_basis,loc=mus[i],scale=sds[i])

g = g / np.sum(g,axis=0)[np.newaxis,:]

fig, axes = plt.subplots()
for i in range(n_basis):
    axes.plot(tvec_basis, g[:,i])

# %% exclude odor that is removed halfway through the session from the set
# of regressors!

if not "CONTEXT_SWITCH_EVENT" in LogDf['name'].values:
    print("no context switch in this session!")

delays = np.sort(pd.unique(LogDf.groupby('var').get_group('this_delay').value))
ix = LogDf.groupby('name').get_group("CONTEXT_SWITCH_EVENT").index[0]
delays_before = np.sort(pd.unique(LogDf.loc[:ix].groupby('var').get_group('this_delay').value))
delays_after = np.sort(pd.unique(LogDf.loc[ix:].groupby('var').get_group('this_delay').value))
exclude = [delay for delay in delays_before if delay not in delays_after][0]
exclude_ix = list(delays).index(exclude)

odor_ids = LogDf.groupby('var').get_group('this_odor')['value'].values
odor_times = bhv.get_events_from_name(LogDf,"ODOR_ON")['t'].values
times = odor_times[odor_ids != exclude_ix]
valid_stim_on = bin_times(times, tvec)

# convolve
G = np.repeat(valid_stim_on[:,np.newaxis],n_gammas,1)
for j in range(n_gammas):
    G[:,j] = np.convolve(G[:,j], g[:,j],mode='same')

# %%
plt.matshow(G)
plt.gca().set_aspect('auto')

# %% combine regressors and make model matrix
X_lr = np.concatenate(X_lagreg, axis=1)
X_intercept = np.ones((X_lr.shape[0],1))
# X = np.concatenate([X_intercept, X_lr, G],axis=1) # model with time bases
X = np.concatenate([X_intercept, X_lr],axis=1) # model without time bases

# %% run LM
l = rrr.xval_ridge_reg_lambda(Y, X, K=5) # 49.159
print(l)
# B_hat = rrr.LM(Y, X, lam=78.23)

# %%
fig, axes = plt.subplots()
axes.matshow(B_hat)
axes.set_aspect('auto')

# %% regs split
# lagregs are right after intercept
n_lagreg_inds = len(lagregs) * n_lags

dt = np.diff(tvec)[0]
offs = 1
regs_split = np.split(B_hat[offs:n_lagreg_inds+offs,:], len(lagregs), axis=0)
fig, axes = plt.subplots(ncols=len(lagregs),  sharex=True, sharey=True)
s = 0.25
lags = np.linspace(-n_lags/2, n_lags/2 - 1, n_lags).astype('int32')
extent = [lags[0] * dt/1e3, lags[-1] * dt/1e3, 0, 1]
for i in range(len(lagregs)):
    axes[i].matshow(regs_split[i].T,vmin=-s,vmax=s,cmap='PiYG',extent=extent)
    axes[i].set_aspect('auto')
    axes[i].set_title(lagreg_names[i])
    axes[i].set_yticks([])
    axes[i].axvline(0,linestyle=':',color='k',lw=1)


# %% model inspect
# Y_hat = X @ B_hat
# start_ix = 70000
# stop_ix = start_ix + 2000

# d = D[start_ix:stop_ix,:]
# y = Y_hat[start_ix:stop_ix,:]

# n_cells = d.shape[1]
# fig, axes = plt.subplots()
# y_scl = 1
# for i in range(n_cells):
#     axes.plot(d[:,i]*y_scl+i,lw=1,color='k')
#     axes.plot(y[:,i]*y_scl+i,lw=2,alpha=0.8,color='r')

# B_hat_diff = B_hat_post - B_hat_pre


# %% all gammas
B_gs = B_hat[-n_gammas:,:]

order = np.argsort(np.sum(B_gs,axis=0))

fig, axes = plt.subplots(figsize=[6,2.5])
s = 0.05
axes.matshow(B_gs[:,order],vmin=-s,vmax=s,cmap='PiYG')
axes.set_aspect('auto')
axes.set_title('full session')
fig.tight_layout()

# %% MODEL RUN w seperation by context switch
t_context_switch = bhv.get_events_from_name(LogDf, "CONTEXT_SWITCH_EVENT")['t'].values[0]
ix = np.argmin((tvec - t_context_switch)**2)
lam = 78.23
B_hat_pre = rrr.LM(Y[:ix],X[:ix],lam=lam)
B_hat_post = rrr.LM(Y[ix:],X[ix:],lam=lam)
B_hat_diff = B_hat_post - B_hat_pre

# %%
fig, axes = plt.subplots()

B_gs_pre = B_hat_pre[-n_gammas:,:]
B_gs_post = B_hat_post[-n_gammas:,:]

B_gs_diff = B_gs_post - B_gs_pre


# order = np.argsort(np.sum(B_gs_pre,axis=0))
# order = np.argsort(np.sum(B_gs_post,axis=0))

# order = np.argsort(np.sum(B_gs_pre[:n_gammas], axis=0) - np.sum(B_gs_pre[n_gammas:]))
from scipy.stats import linregress
ms = []
n_cells = B_gs_pre.shape[1]
for i in range(n_cells):
    m = linregress(gammas,B_gs_diff[:,i])[0]
    ms.append(m)

order = np.argsort(ms)

fig, axes = plt.subplots(nrows=3,figsize=[8,3.5],sharex=True)
s = 0.05

labels = ['pre','post','diff']
for i, B in enumerate([B_gs_pre, B_gs_post, B_gs_diff]):
    # if i == 2:
    #     s = 0.01
    axes[i].matshow(B[:,order], cmap='PiYG', vmin=-s,vmax=s)
    axes[i].set_aspect('auto')
    axes[i].set_ylabel(labels[i])
    # if i != 2:
    #     axes[i].set_xticklabels([])

axes[i].xaxis.set_ticks_position('bottom')

fig.suptitle('long removed')
# fig.suptitle('short removed')

# %%
cell_id = 3
basis_pre = np.sum(B_gs_pre[:,cell_id] * g, axis=1)
basis_post = np.sum(B_gs_post[:,cell_id] * g, axis=1)

fig, axes = plt.subplots()
axes.plot(basis_pre,'k')
axes.plot(basis_post,'r')



