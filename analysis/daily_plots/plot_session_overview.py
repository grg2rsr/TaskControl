# this should be changed ... 
import sys, os
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

sys.path.append('/home/georg/code/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics

colors = dict(success="#72E043", 
            reward="#3CE1FA", 
            correct="#72E043", 
            incorrect="#F56057", 
            premature="#9D5DF0", 
            missed="#F7D379",
            reward_autodelivered='gray')

def plot_session_overview(session_folder, save=None, on_t=True):

    LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
    # session_metrics = (metrics.get_start, metrics.has_choice, metrics.get_chosen_side, 
    #                 metrics.get_outcome, metrics.get_correct_side, metrics.get_timing_trial,
    #                 metrics.get_interval, metrics.get_interval_category, metrics.get_in_corr_loop,
    #                 metrics.has_reward_collected, metrics.get_autodeliver_trial)
    session_metrics = (metrics.get_start, metrics.has_choice, metrics.get_chosen_side, 
                       metrics.get_outcome, metrics.get_correct_side, metrics.get_timing_trial,
                       metrics.has_reward_collected, metrics.get_autodeliver_trial, metrics.get_in_corr_loop)

    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics)
    SessionDf = bhv.expand_columns(SessionDf, ['outcome'])

    outcomes = SessionDf['outcome'].unique()
    if np.any(pd.isna(outcomes)):
        SessionDf.loc[pd.isna(SessionDf['outcome']),'outcome'] = 'reward_autodelivered'

    fig, axes = plt.subplots(figsize=[10,2.6])

    for i, row in SessionDf.iterrows():
        if on_t:
            t = row['t_on'] / 60000
        else:
            t = i

        axes.plot([t,t],[0,1],lw=2.5,color=colors[row['outcome']],zorder=-1)

        w = 0.05
        if row['correct_side'] == 'left':
            axes.plot([t,t],[0-w,0+w],lw=1,color='k')
        if row['correct_side'] == 'right':
            axes.plot([t,t],[1-w,1+w],lw=1,color='k')

        if row['has_choice']:
            if row['chosen_side'] == 'left':
                axes.plot(t,-0.0,'.',color='k')
            if row['chosen_side'] == 'right':
                axes.plot(t,1.0,'.',color='k')

        if row['in_corr_loop'] and not np.isnan(row['in_corr_loop']):
            axes.plot([t,t],[-0.1,1.1],color='red',alpha=0.5,zorder=-2,lw=3)
        
        if row['timing_trial'] and not np.isnan(row['timing_trial']):
            axes.plot([t,t],[-0.1,1.1],color='cyan',alpha=0.5,zorder=-2,lw=3)

        if row['autodeliver_rewards'] and not np.isnan(row['autodeliver_rewards']):
            axes.plot([t,t],[-0.1,1.1],color='pink',alpha=0.5,zorder=-2,lw=3)

        if row['has_reward_collected']:
            if row['correct_side'] == 'left':
                axes.plot(t,-0.0,'.',color=colors['reward'],markersize=3,alpha=0.5)
            if row['correct_side'] == 'right':
                axes.plot(t,1.0,'.',color=colors['reward'],markersize=3,alpha=0.5)
                
    # success rate
    hist=10
    for outcome in ['missed']:
        srate = (SessionDf['outcome'] == outcome).rolling(hist).mean()
        if on_t:
            k = SessionDf['t_on'].values / 60000
        else:
            k = range(SessionDf.shape[0])
        axes.plot(k, srate,lw=1.5,color='black',alpha=0.75)
        axes.plot(k, srate,lw=1,color=colors[outcome],alpha=0.75)

    # valid trials
    SDf = bhv.intersect(SessionDf,is_missed=False)
    srate = (SDf.outcome == 'correct').rolling(hist).mean()
    if on_t:
        k = SDf['t_on']  / 60000
    else:
        k = SDf.index

    axes.plot(k, srate,lw=1.5,color='k')
    axes.axhline(0.5,linestyle=':',color='k',alpha=0.5)

    # deco
    if on_t:
        axes.set_xlabel('time (min)')
    else:
        axes.set_xlabel('trial #')
    axes.set_ylabel('success rate')

    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)
    title = ' - '.join([Animal.display(), Session.date, 'day: %s'% Session.day])

    sns.despine(fig)
    fig.suptitle(title)
    fig.tight_layout()
    fig.subplots_adjust(top=0.9)

    if save is not None:
        os.makedirs(save.parent, exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

# # %%
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-25_15-59-02_learn_to_choose_v2")
# # session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-21_11-47-21_learn_to_choose_v2")
# # session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-22_10-39-25_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-25_15-59-02_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-26_13-11-18_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-26_11-30-14_learn_to_choose_v2")
# plot_session_overview(session_folder)

# # %%
