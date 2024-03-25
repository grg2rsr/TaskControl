# %%
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
             left=mpl.cm.PiYG(0.05),
             right=mpl.cm.PiYG(0.95))

def plot_choice_RTs(session_folder, save=None, bins=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
    session_metrics = (metrics.get_start, metrics.get_choice_rt, metrics.has_choice, metrics.get_chosen_side, metrics.get_correct_side,
                    metrics.get_outcome)

    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics)

    fig, axes = plt.subplots(nrows=2,ncols=2,sharey=True)

    sides = ['left','right']
    outcomes = ['correct','incorrect']

    if bins is None:
        bins = sp.linspace(0, 3000, 40)

    for i, side in enumerate(sides):
        for j, outcome in enumerate(outcomes):
            SDf = bhv.intersect(SessionDf, has_choice=True, correct_side=side, outcome=outcome)
            # SDf = SessionDf.groupby(['correct_side','outcome']).get_group((side,outcome))
            values = SDf['choice_rt'].values

            # reaches are colored by the side to which the animal reaches
            # columns are the requested trial type
            if (side == 'left' and outcome == 'correct') or (side == 'right' and outcome == 'incorrect'):
                color = colors['left']
            else:
                color = colors['right']
            axes[j,i].hist(values, bins=bins, color=color)

    for i, ax in enumerate(axes[:,0]):
        ax.set_ylabel(outcomes[i])

    for i, ax in enumerate(axes[0,:]):
        ax.set_title(sides[i])

    for i, ax in enumerate(axes[-1,:]):
        ax.set_xlabel('time (ms)')

    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)
    title = ' - '.join([Animal.display(), Session.date, 'day: %s'% Session.day])

    sns.despine(fig)
    fig.suptitle(title)
    fig.tight_layout()
    fig.subplots_adjust(top=0.85)

    if save is not None:
        os.makedirs(save.parent, exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

# %%
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-22_10-39-25_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-26_09-50-35_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-26_11-30-14_learn_to_choose_v2")
# plot_choice_RTs(session_folder)
# %%
