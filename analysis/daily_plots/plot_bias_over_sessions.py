# %%
import sys
import os
from pathlib import Path
import numpy as np
import seaborn as sns

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv

sys.path.append('/home/georg/code/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import utils

def plot_bias_over_sessions(Animal_folder, task_name, save=None):
    Animal = utils.Animal(Animal_folder)

    # get BiasDfs
    SessionsDf = utils.get_sessions(Animal.folder).groupby('task').get_group(task_name)
    BiasDfs = []

    autodeliver = []
    p_lefts = []

    for i, row in SessionsDf.iterrows():
        session_folder = Path(row['path'])
        LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
        LogDf['min'] = LogDf['t'] / 60000

        # one sesion bias
        BiasDf = LogDf.groupby('var').get_group('bias')
        t_min = BiasDf['t'].values[0]
        t_max = BiasDf['t'].values[-1]
        BiasDf['t_rel'] = (BiasDf['t'].values - t_min)/t_max

        BiasDfs.append(BiasDf)

        # get autodeliver value for session
        fname = session_folder / task_name / 'Arduino' / 'src' / 'interface_variables.h'
        value = utils.parse_arduino_vars(fname).groupby('name').get_group('autodeliver_rewards').iloc[0]['value']
        autodeliver.append(value)

        # get static bias corr if possible
        fname = session_folder / task_name / 'Arduino' / 'src' / 'interface_variables.h'
        try:
            p_left = utils.parse_arduino_vars(fname).groupby('name').get_group('p_left').iloc[0]['value']
        except KeyError:
            p_left = 0.5
        p_lefts.append(p_left)

    fig, axes = plt.subplots(nrows=2, sharex=True, gridspec_kw=dict(height_ratios=(0.1,1)))
    w = 0.5
    
    axes[0].set_ylabel('auto\nrewards')
    axes[0].set_xticks([])
    axes[0].set_yticks([])

    for i in range(SessionsDf.shape[0]):
        BiasDf = BiasDfs[i]
        tvec = np.linspace(i-w/2,i+w/2,BiasDf.shape[0])
        axes[1].plot(tvec, BiasDf['value'])
        axes[1].plot(i, np.average(BiasDf['value']),'o',color='k')
        axes[1].set_ylim(-0.1,1.1)
        if autodeliver[i] == 1:
            axes[0].plot(i,0,'o',color='black')
        # axes[0].text(i,0.03,str(p_lefts[i]),ha='center')

    axes[1].axhline(0.5,linestyle=':',lw=1,alpha=0.5,color='k')
    axes[1].set_xticks(range(SessionsDf.shape[0]))
    axes[1].set_xticklabels(SessionsDf['date'],rotation=45, ha="right")
    axes[1].set_xlabel('date')
    axes[1].set_ylabel('bias\n1=right')

    title = Animal.Nickname + ' - bias over sessions'
    axes[0].set_title(title)
    sns.despine(fig)
    fig.tight_layout()
    fig.subplots_adjust(hspace=0.1)

    if save is not None:
        os.makedirs(save.parent, exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

# %%
# Animal_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack")
# task_name = 'learn_to_choose_v2'
# plot_bias_over_sessions(Animal_folder, task_name=task_name, save=None)