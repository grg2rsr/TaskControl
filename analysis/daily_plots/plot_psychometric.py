# %%
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
            left=mpl.cm.PiYG(0.05),
            right=mpl.cm.PiYG(0.95))

def plot_psychometric(session_folder, N=1000, save=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
    session_metrics = (metrics.get_start, metrics.has_choice, metrics.get_chosen_side, 
                        metrics.get_outcome, metrics.get_correct_side, metrics.get_timing_trial,
                        metrics.get_interval, metrics.get_interval_category, metrics.get_in_corr_loop,
                        metrics.has_reward_collected, metrics.get_autodeliver_trial, metrics.get_chosen_interval)

    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics)
    SessionDf = bhv.expand_columns(SessionDf, ['outcome'])

    outcomes = SessionDf['outcome'].unique()
    if np.any(pd.isna(outcomes)):
        SessionDf.loc[pd.isna(SessionDf['outcome']),'outcome'] = 'reward_autodelivered'

    # the three variants
    # SDf = bhv.intersect(SessionDf, has_choice=True, is_premature=True)
    # SDf = bhv.intersect(SessionDf, has_choice=True, is_premature=False, timing_trial=False)
    SDf = bhv.intersect(SessionDf, has_choice=True, is_premature=False, timing_trial=True)

    # exit here if there are no timing trials
    if SDf.shape[0] == 0:
        return None

    fig, axes = plt.subplots()

    # plot the choices as p(Long)
    intervals = list(np.sort(SDf['this_interval'].unique()))
    for i, interval in enumerate(intervals):
        Df = bhv.intersect(SDf, this_interval=interval)
        f = np.sum(Df['chosen_interval'] == 'long') / Df.shape[0]
        axes.plot(interval, f,'o',color='r')
    axes.set_ylabel('p(choice = long)')

    # plot the fit
    y = SDf['chosen_side'].values == 'right'
    x = SDf['this_interval'].values
    x_fit = np.linspace(0,3000,100)
    y_fit, p_fit = bhv.log_reg(x, y, x_fit, fit_lapses=True)
    axes.plot(x_fit, y_fit,color='red', linewidth=2,alpha=0.75)
    
    # lapse rates
    lupper = p_fit[3] + p_fit[2]
    llower = p_fit[3]
    axes.text(intervals[0], llower+0.05, "%.2f" % llower, ha='center', va='center')
    axes.text(intervals[-1], lupper+0.05, "%.2f" % lupper, ha='center', va='center')

    if N is not None:
        # plot the random models based on the choice bias
        bias = (SDf['chosen_side'] == 'right').sum() / SDf.shape[0]
        R = []
        for i in tqdm(range(N)):
            rand_choices = sp.rand(SDf.shape[0]) < bias
            try:
                R.append(bhv.log_reg(x, rand_choices, x_fit)[0])
            except ValueError:
                # thrown when all samples are true or false
                print("all true or false")
                pass
        R = np.array(R)

        # Several statistical boundaries
        alphas = [5, 0.5, 0.05]
        opacities = [0.2, 0.2, 0.2]
        for alpha, a in zip(alphas, opacities):
            R_pc = sp.percentile(R, (alpha, 100-alpha), 0)
            axes.fill_between(x_fit, R_pc[0], R_pc[1], color='blue', alpha=a, linewidth=0)

    # deco
    w = 0.05
    axes.set_ylim(0-w, 1+w)
    axes.axvline(1500,linestyle=':',alpha=0.5,lw=1,color='k')
    axes.axhline(0.5,linestyle=':',alpha=0.5,lw=1,color='k')

    axes.set_xlim(500,2500)
    axes.set_xlabel('time (ms)')

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

# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-25_15-59-02_learn_to_choose_v2")
# # session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-21_11-47-21_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-22_10-39-25_learn_to_choose_v2")

# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-25_15-59-02_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975_Marquez/2021-05-18_09-41-58_learn_to_fixate_discrete_v1")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-26_13-11-18_learn_to_choose_v2")
# plot_psychometric(session_folder, N=1000)
