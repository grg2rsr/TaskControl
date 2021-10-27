# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

# this should be changed ... 
import sys, os
sys.path.append('..')
from pathlib import Path
import numpy as np
import scipy as sp
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv

from Utils import behavior_analysis_utils as bhv
from Utils import utils

from sklearn.linear_model import LogisticRegression
from scipy.special import expit


"""
 
 ########  ##        #######  ######## ######## ######## ########   ######  
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##    ## 
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##       
 ########  ##       ##     ##    ##       ##    ######   ########   ######  
 ##        ##       ##     ##    ##       ##    ##       ##   ##         ## 
 ##        ##       ##     ##    ##       ##    ##       ##    ##  ##    ## 
 ##        ########  #######     ##       ##    ######## ##     ##  ######  
 
"""
colors = dict(success="#72E043", 
            reward="#3CE1FA", 
            correct="#72E043", 
            incorrect="#F56057", 
            premature="#9D5DF0", 
            missed="#F7D379")

# def plot_session_overview(SessionDf, axes=None):
#     if axes is None:
#         fig, axes = plt.subplots()

#     outcomes = SessionDf['outcome'].unique()

#     for i, row in SessionDf.iterrows():
#         axes.plot([i,i],[0,1],lw=2.5,color=colors[row.outcome],zorder=-1)

#         w = 0.05
#         if row.correct_side == 'left':
#             axes.plot([i,i],[0-w,0+w],lw=1,color='k')
#         if row.correct_side == 'right':
#             axes.plot([i,i],[1-w,1+w],lw=1,color='k')

#         if row.has_choice:
#             if row.chosen_side == 'left':
#                 axes.plot(i,-0.0,'.',color='k')
#             if row.chosen_side == 'right':
#                 axes.plot(i,1.0,'.',color='k')

#         if row.in_corr_loop and not sp.isnan(row.in_corr_loop):
#             axes.plot([i,i],[-0.1,1.1],color='red',alpha=0.5,zorder=-2,lw=3)
        
#         if row.timing_trial and not sp.isnan(row.timing_trial):
#             axes.plot([i,i],[-0.1,1.1],color='cyan',alpha=0.5,zorder=-2,lw=3)

#     # success rate
#     hist=10
#     for outcome in ['missed']:
#         srate = (SessionDf.outcome == outcome).rolling(hist).mean()
#         axes.plot(range(SessionDf.shape[0]),srate,lw=1.5,color='black',alpha=0.75)
#         axes.plot(range(SessionDf.shape[0]),srate,lw=1,color=colors[outcome],alpha=0.75)

#     # valid trials
#     SDf = SessionDf.groupby('is_missed').get_group(False)
#     srate = (SDf.outcome == 'correct').rolling(hist).mean()
#     axes.plot(SDf.index,srate,lw=1.5,color='k')

#     axes.axhline(0.5,linestyle=':',color='k',alpha=0.5)

#     # deco
#     axes.set_xlabel('trial #')
#     axes.set_ylabel('success rate')
#     return axes

# choice RTs
# def plot_choice_RTs(SessionDf, axes=None):
#     if axes is None:
#         fig, axes = plt.subplots(nrows=2,ncols=2,sharey=True)

#     sides = ['left','right']
#     outcomes = ['correct','incorrect']

#     bins = sp.linspace(0,2000,50)

#     cmap = mpl.cm.PiYG
#     colors = [cmap]

#     for i, side in enumerate(sides):
#         for j, outcome in enumerate(outcomes):
#             SDf = SessionDf.groupby(['correct_side','outcome']).get_group((side,outcome))
#             values = SDf['choice_rt'].values

#             if (side == 'left' and outcome == 'correct') or (side == 'right' and outcome == 'incorrect'):
#                 color = cmap(0.1)
#             else:
#                 color = cmap(.9)
#             axes[j,i].hist(values, bins=bins, color=color)

#     for i, ax in enumerate(axes[:,0]):
#         ax.set_ylabel(outcomes[i])

#     for i, ax in enumerate(axes[0,:]):
#         ax.set_title(sides[i])

#     return axes

# init times analysis
# def plot_init_times_hist(SessionDf, axes=None):
#     if axes is None:
#         fig, axes = plt.subplots(nrows=len(outcomes),sharex=True, figsize=[4,5.5])

#     bins = sp.linspace(0,5000,25)
#     for i, outcome in enumerate(outcomes):
#         SDf = SessionDf.groupby('outcome').get_group(outcome)
#         axes[i].hist(SDf['init_rt'].values,bins=bins,color=colors[outcome])
#         axes[i].set_ylabel(outcome)

#     axes[-1].set_xlabel('time (ms)')

#     return axes

# def plot_init_times(SessionDf, axes=None):
#     if axes is None:
#         fig, axes = plt.subplots()

#     x = range(SessionDf.shape[0])
#     y = SessionDf['init_rt'] / 1000

#     outcomes = SessionDf.outcome.unique()

#     dot_colors = [colors[outcome] for outcome in SessionDf.outcome]
#     axes.scatter(x , y,color=dot_colors, s=8)
#     axes.axhline(0,linestyle=':',color='k',alpha=0.5)

#     axes.set_ylim(-1,30)
#     axes.set_ylabel('time to init (s)')
#     axes.set_xlabel('trial #')
#     return axes



# combining
# def plot_session_panel(SessionDf, log_path, save=True, plot_dir=None):
#     fig, axes = plt.subplots(nrows=2, gridspec_kw=dict(height_ratios=(1,3)))

#     if plot_dir is None:
#         plot_dir = log_path.parent / 'plots'
#         os.makedirs(plot_dir, exist_ok=True)

#     # plots
#     plot_session_overview(SessionDf, axes=axes[0])
#     plot_psychometric(SessionDf, axes=axes[1], discrete=True)
    
#     animal = utils.Animal(log_path.parent)
#     date = log_path.parent.stem.split('_')[0]
#     title = ' - '.join([date, animal.ID, animal.Nickname])
#     fig.suptitle(title,fontsize='small')
#     fig.tight_layout()
#     fig.subplots_adjust(top=0.95)

#     if save:
#         outpath = plot_dir / 'session_overview_coarse.png'
#         plt.savefig(outpath, dpi=600)
#         plt.close(fig)
#     else:
#         return fig, axes


# %%

session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975_Marquez/2021-05-18_09-41-58_learn_to_fixate_discrete_v1")
Session = utils.Session(session_folder)
Animal = utils.Animal(session_folder.parent)

LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
LogDf['min'] = LogDf['t'] / 60000

#  slice into trials
def get_SessionDf(LogDf, metrics, trial_entry_event="TRIAL_AVAILABLE_STATE", trial_exit_event="ITI_STATE"):

    TrialSpans = bhv.get_spans_from_names(LogDf, trial_entry_event, trial_exit_event)

    TrialDfs = []
    for i, row in tqdm(TrialSpans.iterrows(),position=0, leave=True):
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))
    
    SessionDf = bhv.parse_trials(TrialDfs, metrics)
    return SessionDf, TrialDfs

from Utils.metrics import *

session_metrics = [has_choice, get_chosen_side, get_chosen_interval, get_correct_side,
                    get_interval_category, get_interval, get_outcome, get_in_corr_loop,
                    get_timing_trial, get_start, get_stop, get_init_rt, get_premature_rt,
                    get_choice_rt]

SessionDf, TrialDfs = get_SessionDf(LogDf, session_metrics, trial_entry_event="TRIAL_AVAILABLE_STATE", trial_exit_event="ITI_STATE")

# expand outcomes in boolean columns
outcomes = SessionDf['outcome'].unique()
for outcome in outcomes:
    SessionDf['is_'+outcome] = SessionDf['outcome'] == outcome

# setup general filter
SessionDf['exclude'] = False

# %%

N = 100
# def plot_psychometric(SessionDf, N=1000, axes=None, discrete=False):
fig, axes = plt.subplots(figsize=[4,3])

# get only the subset with choices - excludes missed
SDf = bhv.groupby_dict(SessionDf, dict(has_choice=True, exclude=False,
                                        in_corr_loop=False, is_premature=False,
                                        timing_trial=True))

try:
    SDf = SDf.groupby('timing_trial').get_group(True)
except KeyError:
    print("no timing trials in session")

y = SDf['chosen_side'].values == 'right'
x = SDf['this_interval'].values

# axx = plt.twinx(axes)
# axx.set_yticks([0,1])
# axx.set_yticklabels(['short','long'])
# axx.set_ylabel('choice')
# axx.set_ylim(0-w, 1+w)

w = 0.05
axes.set_ylim(0-w, 1+w)
axes.set_ylabel('p(choice=long)')
axes.set_xlim(500,2500)
axes.axvline(1500,linestyle=':',alpha=0.5,lw=1,color='k')
axes.axhline(0.5,linestyle=':',alpha=0.5,lw=1,color='k')

# plot the fit
x_fit = np.linspace(0,3000,100)
from Utils import behavior_analysis_utils as bhv
from Utils import utils
axes.plot(x_fit, bhv.log_reg(x, y, x_fit),color='black', linestyle='-', linewidth=1, alpha=0.75, label='fit')

# # plot the random models based on the choice bias
# bias = (SDf['chosen_side'] == 'right').sum() / SDf.shape[0]
# R = []
# for i in tqdm(range(N)):
#     rand_choices = sp.rand(SDf.shape[0]) < bias
#     try:
#         R.append(bhv.log_reg(x, rand_choices,x_fit))
#     except ValueError:
#         # thrown when all samples are true or false
#         print("all true or false")
#         pass
# R = np.array(R)

# # Several statistical boundaries
# alphas = [5, 0.5, 0.05]
# opacities = [0.2, 0.2, 0.2]
# for alpha, a in zip(alphas, opacities):
#     R_pc = sp.percentile(R, (alpha, 100-alpha), 0)
#     axes.fill_between(x_fit, R_pc[0], R_pc[1], color='gray', alpha=a, linewidth=0)

axes.set_xlabel('interval duration (ms)')

# TODO absolutely wrong variable names - this is pLong

intervals = list(SessionDf.groupby('this_interval').groups.keys())
correct_sides = ['left' if interval < 1500 else 'right' for interval in intervals] # this is correct
correct_sides = ['right'] * len(intervals) # NOT correct sides
for i, interval in enumerate(intervals):
    SDf = bhv.groupby_dict(SessionDf, dict(this_interval=interval, has_choice=True, is_premature=False))
    f = (SDf['chosen_side'] == correct_sides[i]).sum() / SDf.shape[0]
    axes.plot(interval,f,'o',color='black',label='data')

from collections import OrderedDict
import matplotlib.pyplot as plt

handles, labels = plt.gca().get_legend_handles_labels()
by_label = OrderedDict(zip(labels, handles))
plt.legend(by_label.values(), by_label.keys())

axes.set_title('headfixed interval timing - psychometric')

sns.despine(fig)
fig.tight_layout()
plt.savefig('psychometric_for_joes_report.png', dpi=600)
















# # run the plots
# def save_figure(fig, figname, log_path, animal):
#     os.makedirs(log_path.parent / "plots", exist_ok=True)
#     date = log_path.parent.stem.split('_')[0]
#     title = " - ".join([animal.Nickname, animal.ID, date])
#     sns.despine(fig)
#     fig.suptitle(title)
#     fig.tight_layout()
#     fig.subplots_adjust(top=0.90)
#     outpath = log_path.parent / "plots" / figname
#     plt.savefig(outpath.with_suffix(".png"), dpi=600)
#     plt.close(fig)


# %%
