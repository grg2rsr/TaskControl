# %%
import sys
import os
import scipy as sp
import seaborn as sns

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

def plot_reward_collection_rts(session_folder, save=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / 'arduino_log.txt')
    session_metrics = (metrics.get_start, metrics.get_reward_collection_rt, metrics.has_choice, metrics.get_chosen_side, metrics.get_correct_side,
                      metrics.get_outcome, metrics.get_autodeliver_trial, metrics.has_reward_collected,
                      metrics.get_choice_rt)

    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics)


    fig, axes = plt.subplots(ncols=2,sharey=True)
    bins = sp.linspace(0,5000,50)
    sides = ['left','right']
    for i, side in enumerate(sides):
        SDf = bhv.intersect(SessionDf, has_reward_collected=True, correct_side=side)
        axes[i].hist(SDf['reward_collection_rt'].values,bins=bins,color=colors[side])

        axes[i].set_title(side)

    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)
    title = ' - '.join([Animal.display(), Session.date, 'day: %s'% Session.day])

    axes[0].set_ylabel('count')
    for ax in axes:
        ax.set_xlabel('time (ms)')

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
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-22_10-54-03_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-26_11-20-23_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-26_09-50-35_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-26_11-20-23_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-19_12-29-57_learn_to_choose_v2")
# plot_reward_collection_rts(session_folder)
