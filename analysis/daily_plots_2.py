# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

sys.path.append('..')

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv
from Utils import behavior_analysis_utils as bhv
import pandas as pd

# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
from Utils import utils
from Utils.utils import groupby_dict
from datetime import datetime

# %% plotters

"""
 
  ######  ########  ######   ######  ####  #######  ##    ##    ##       ######## ##     ## ######## ##       
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ##    ##       ##       ##     ## ##       ##       
 ##       ##       ##       ##        ##  ##     ## ####  ##    ##       ##       ##     ## ##       ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##    ##       ######   ##     ## ######   ##       
       ## ##             ##       ##  ##  ##     ## ##  ####    ##       ##        ##   ##  ##       ##       
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ###    ##       ##         ## ##   ##       ##       
  ######  ########  ######   ######  ####  #######  ##    ##    ######## ########    ###    ######## ######## 
 
"""


def plot_reach_durations(session_folder, save=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
    LogDf['min'] = LogDf['t'] / 60000

    # check each reach
    ReachesLeftDf = bhv.get_spans_from_names(LogDf, "REACH_LEFT_ON", "REACH_LEFT_OFF")
    ReachesLeftDf['side'] = 'left'

    ReachesRightDf = bhv.get_spans_from_names(LogDf, "REACH_RIGHT_ON", "REACH_RIGHT_OFF")
    ReachesRightDf['side'] = 'right'

    ReachesDf = pd.concat([ReachesLeftDf, ReachesRightDf]).sort_values('t_on')

    # drop invalid
    min_th = 5
    max_th = 2000

    binds = np.logical_and(ReachesDf['dt'].values > min_th, ReachesDf['dt'].values < max_th)

    ReachesDf = ReachesDf.loc[binds]
    ReachesDf = ReachesDf.reset_index().sort_values('t_on')

    ReachesDf[['is_grasp','is_rewarded','is_anticipatory']] = False
    for i, row in ReachesDf.iterrows():
        t_on = row['t_on']
        t_off = row['t_off']
        Df = bhv.time_slice(LogDf, t_on, t_off)

        # check for grasp
        if 'GRASP_LEFT_ON' in Df.name.values or 'GRASP_RIGHT_ON' in Df.name.values:
            ReachesDf.loc[i, 'is_grasp'] = True

        # check for rewarded
        if 'REWARD_LEFT_COLLECTED_EVENT' in Df.name.values or 'REWARD_RIGHT_COLLECTED_EVENT' in Df.name.values:
            ReachesDf.loc[i, 'is_rewarded'] = True

        # check for anticipatory
        if 'ANTICIPATORY_REACH_EVENT' in Df.name.values:
            ReachesDf.loc[i, 'is_anticipatory'] = True

    # some number
    n_reaches = ReachesDf.shape[0]
    f_grasps = ReachesDf.sum(0)['is_grasp'] / n_reaches
    f_rewarded = ReachesDf.sum(0)['is_rewarded'] / n_reaches
    f_anticipatory = ReachesDf.sum(0)['is_anticipatory'] / n_reaches

    # plot
    tab10 = sns.color_palette('tab10',n_colors=5)
    colors = dict(reach=tab10[1],
                  grasp=tab10[2],
                  rewarded=tab10[0],
                  anticipatory=tab10[4])

    fig, axes = plt.subplots(nrows=2, ncols=2, gridspec_kw=dict(width_ratios=(1,0.2)),sharey=True)
    bins = np.arange(0,500,1000/60)
    for i, side in enumerate(['right','left']):
        try:
            Df = groupby_dict(ReachesDf, dict(side=side, is_grasp=False))
            kws = dict(label='reach %i' % n_reaches, color=colors['reach'], alpha=0.7)
            axes[i,0].plot(Df['t_on']/6e4, Df['dt'],'.', **kws)
            axes[i,1].hist(Df['dt'], bins=bins, orientation='horizontal', **kws)
        except:
            pass
        
        try:
            Df = groupby_dict(ReachesDf, dict(side=side, is_grasp=True, is_rewarded=False, is_anticipatory=False))
            kws = dict(label='grasp %.2f' % f_grasps, color=colors['grasp'], alpha=0.8)
            axes[i,0].plot(Df['t_on']/6e4, Df['dt'],'.', **kws)
            axes[i,1].hist(Df['dt'], bins=bins, orientation='horizontal', **kws)
        except:
            pass

        try:
            Df = groupby_dict(ReachesDf, dict(side=side, is_rewarded=True, is_anticipatory=False))
            kws = dict(label='rewarded %.2f' % f_rewarded, color=colors['rewarded'], alpha=0.8)
            axes[i,0].plot(Df['t_on']/6e4, Df['dt'],'.', **kws)
            axes[i,1].hist(Df['dt'], bins=bins, orientation='horizontal', **kws)
        except:
            pass

        try:
            Df = groupby_dict(ReachesDf, dict(side=side, is_anticipatory=True))
            kws = dict(label='anticipatory %.2f' % f_anticipatory,color=colors['anticipatory'], alpha=0.8)
            axes[i,0].plot(Df['t_on']/6e4, Df['dt'],'.', **kws)
            axes[i,1].hist(Df['dt'], bins=bins, orientation='horizontal', **kws)
        except:
            pass

        axes[i,0].set_ylim(0,250)
        axes[i,1].set_ylim(0,250)

        axes[i,0].set_ylabel('%s' '\nduration (ms)' % side)

    Session = utils.Session(session_folder)
    title = ' - '.join([Animal.display(), Session.date,'day: %s'% Session.day])

    sns.despine(fig)
    fig.suptitle(title)
    axes[1,0].set_xlabel('time (min)')
    axes[0,1].legend(fontsize='small')
    fig.tight_layout()

    if save is not None:
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)


def plot_grasp_histograms(session_folder, save=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
    LogDf['min'] = LogDf['t'] / 60000

    #  reach time split by cue
    sides = ('left','right')
    events = ['GO_CUE_LEFT_EVENT', 'GO_CUE_RIGHT_EVENT']
    # events = ['REWARD_LEFT_VALVE_ON', 'REWARD_RIGHT_VALVE_ON']
    grasps = ['GRASP_LEFT_ON', 'GRASP_RIGHT_ON']
    pre, post = -2500, 2500

    tab10 = sns.color_palette('tab10',n_colors=5)
    colors = dict(reach=tab10[1],
                    grasp=tab10[2],
                    rewarded=tab10[0],
                    anticipatory=tab10[4])


    bins = sp.linspace(pre,post,50)
    fig, axes = plt.subplots(2,2,sharex=True,sharey=True)
    for i, event in enumerate(events):
        times = LogDf.groupby('name').get_group(event)['t'].values

        Dfs = []
        for t in times:
            Df = bhv.time_slice(LogDf, t+pre, t+post)
            Df['t'] = Df['t'] - t
            Dfs.append(Df)

        Dfs = pd.concat(Dfs)

        for j, grasp in enumerate(grasps):
            try:
                gt = Dfs.groupby('name').get_group(grasp)['t'].values
                axes[j,i].hist(gt,bins=bins, color=colors['grasp'], label='grasps')
            except KeyError:
                pass

    for ax in axes.flatten():
        ax.axvline(0,linestyle=':',alpha=0.5)

    for i,ax in enumerate(axes[:,0]):
        ax.set_ylabel(grasps[i])

    for i,ax in enumerate(axes[0,:]):
        ax.set_title(events[i])

    for i, ax in enumerate(axes[1,:]):
        ax.set_xlabel('time (ms)')

    axes[0,0].legend(fontsize='small')

    Animal = utils.Animal(session_folder.parent)
    Session = utils.Session(session_folder)
    title = ' - '.join([Animal.display(),Session.date,'day: %s'% Session.day])

    fig.suptitle(title)
    sns.despine(fig)
    fig.tight_layout()
    fig.subplots_adjust(top=0.85)

    if save is not None:
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

def plot_bias(session_folder,save=None):
    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)

    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
    LogDf['min'] = LogDf['t'] / 60000

    from Utils import metrics as m
    metrics = (m.get_start, m.get_stop, m.has_choice, m.get_correct_side, m.get_chosen_side)
    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics)

    fig, axes = plt.subplots(ncols=2,sharey=True)
    sides = ('left','right')
    for i, side in enumerate(sides): # trial type
        axes[i].set_title(side)
        axes[i].set_xlabel('chosen side')
        
        f_choices = []
        
        try:
            Df = groupby_dict(SessionDf, dict(has_choice=True, correct_side=side))
            for j, side in enumerate(sides): # choice
                df = Df.groupby('chosen_side').get_group(side)
                n_choices = df.shape[0]
                f_choices.append(df.shape[0] / Df.shape[0]) # frac of choices given trial type
        except KeyError:
            f_choices = [np.nan,np.nan]
            pass

        pos = range(2)
        axes[i].bar(pos, f_choices)
        axes[i].set_ylim(0,1)
        axes[i].set_xticks(pos)
        axes[i].set_xticklabels(sides)
        axes[i].axhline(0.5, linestyle=':', lw=1, alpha=0.5, color='k')

    title = ' - '.join([Animal.display(),Session.date,'day: %s'% Session.day])
    sns.despine(fig)
    fig.suptitle(title+'\nChoices split by trial type\n')
    fig.tight_layout()
    fig.subplots_adjust(top=0.8)

    if save is not None:
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

### 

"""
 
 ########  ##     ## ##    ##    ##     ## ####  ######   ######  #### ##    ##  ######   
 ##     ## ##     ## ###   ##    ###   ###  ##  ##    ## ##    ##  ##  ###   ## ##    ##  
 ##     ## ##     ## ####  ##    #### ####  ##  ##       ##        ##  ####  ## ##        
 ########  ##     ## ## ## ##    ## ### ##  ##   ######   ######   ##  ## ## ## ##   #### 
 ##   ##   ##     ## ##  ####    ##     ##  ##        ##       ##  ##  ##  #### ##    ##  
 ##    ##  ##     ## ##   ###    ##     ##  ##  ##    ## ##    ##  ##  ##   ### ##    ##  
 ##     ##  #######  ##    ##    ##     ## ####  ######   ######  #### ##    ##  ######   
 
"""

# %%
Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
# Nicknames = ['Poolboy']
task_name = 'learn_to_choose_v2'

# get animals by Nickname
Animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(Animals_folder)

Animals = [a for a in Animals if a.Nickname in Nicknames]

overwrite = False

for i, Animal in enumerate(Animals):
    utils.printer("processing animal %s" % Animal, 'msg')
    SessionsDf = utils.get_sessions(Animal.folder).groupby('task').get_group(task_name)
    SessionsDf = SessionsDf.reset_index()

    for i, row in SessionsDf.iterrows():
        session_path = Path(row['path'])
        
        # reach durations
        outpath = session_path / 'plots' / 'reach_durations.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing %s on plot %s" % (session_path, 'reach_durations'), 'msg')
            plot_reach_durations(session_path, save=outpath)

        # grasp histo
        outpath = session_path / 'plots' / 'grasp_histograms.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing %s on plot %s" % (session_path, 'grasp_histograms'), 'msg')
            plot_grasp_histograms(session_path, save=outpath)

        # bias plot
        outpath = session_path / 'plots' / 'choice_bias.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing %s on plot %s" % (session_path, 'choice_bias'), 'msg')
            plot_bias(session_path, save=outpath)


# %%

"""
 
 ##     ## ##     ## ##       ######## ####     ######  ########  ######   ######  ####  #######  ##    ## 
 ###   ### ##     ## ##          ##     ##     ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## 
 #### #### ##     ## ##          ##     ##     ##       ##       ##       ##        ##  ##     ## ####  ## 
 ## ### ## ##     ## ##          ##     ##      ######  ######    ######   ######   ##  ##     ## ## ## ## 
 ##     ## ##     ## ##          ##     ##           ## ##             ##       ##  ##  ##     ## ##  #### 
 ##     ## ##     ## ##          ##     ##     ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### 
 ##     ##  #######  ########    ##    ####     ######  ########  ######   ######  ####  #######  ##    ## 
 
"""

def plot_bias_over_sessions(Animal_folder, save=None):
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
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)

# %%
"""
 
    ###    ##    ## ######## ####  ######  #### ########     ###    ########  #######  ########  ##    ##    ########  ########    ###     ######  ##     ## 
   ## ##   ###   ##    ##     ##  ##    ##  ##  ##     ##   ## ##      ##    ##     ## ##     ##  ##  ##     ##     ## ##         ## ##   ##    ## ##     ## 
  ##   ##  ####  ##    ##     ##  ##        ##  ##     ##  ##   ##     ##    ##     ## ##     ##   ####      ##     ## ##        ##   ##  ##       ##     ## 
 ##     ## ## ## ##    ##     ##  ##        ##  ########  ##     ##    ##    ##     ## ########     ##       ########  ######   ##     ## ##       ######### 
 ######### ##  ####    ##     ##  ##        ##  ##        #########    ##    ##     ## ##   ##      ##       ##   ##   ##       ######### ##       ##     ## 
 ##     ## ##   ###    ##     ##  ##    ##  ##  ##        ##     ##    ##    ##     ## ##    ##     ##       ##    ##  ##       ##     ## ##    ## ##     ## 
 ##     ## ##    ##    ##    ####  ######  #### ##        ##     ##    ##     #######  ##     ##    ##       ##     ## ######## ##     ##  ######  ##     ## 
 
"""

# Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
# Nicknames = ['Therapist']
# Nicknames = ['Teacher']
# task_name = 'learn_to_choose_v2'

# # get animals by Nickname
# folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
# Animals = utils.get_Animals(folder)
# Animals = [a for a in Animals if a.Nickname in Nicknames]

def plot_anticipatory_reaches_over_sessions(Animal_folder, save=None):
    Animal = utils.Animal(Animal_folder)

    SessionsDf = utils.get_sessions(Animal.folder)
    SessionsDf = SessionsDf.groupby('task').get_group(task_name)
    from Utils import metrics as m

    for i, row in SessionsDf.iterrows():
        session_folder = Path(row['path'])
        LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
        metrics = (m.get_start, m.get_stop, m.has_choice, m.get_correct_side, m.get_chosen_side, m.has_anticipatory_reach)
        SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics)

        try:
            n_choices = SessionDf.groupby('has_choice').get_group(True).shape[0]
            n_trials = SessionDf.shape[0]
            Df = groupby_dict(SessionDf, dict(has_choice=True, has_anticip_reach=True))
            try:
                SessionsDf.loc[i,'f_anticip_left'] = groupby_dict(SessionDf, dict(has_choice=True, has_anticip_reach=True, chosen_side='left')).shape[0] / n_trials
            except KeyError:
                SessionsDf.loc[i,'f_anticip_left'] = 0
                pass        
            try:
                SessionsDf.loc[i,'f_anticip_right'] = groupby_dict(SessionDf, dict(has_choice=True, has_anticip_reach=True, chosen_side='right')).shape[0] / n_trials
            except KeyError:
                SessionsDf.loc[i,'f_anticip_right'] = 0
                pass
        except KeyError:
            SessionsDf.loc[i,'f_anticip_left'] = 0
            SessionsDf.loc[i,'f_anticip_right'] = 0
            pass

    fig, axes = plt.subplots()
    tvec = range(SessionsDf.shape[0])

    colors = dict(zip(('left','right'), sns.color_palette(palette='PiYG',n_colors=2)))
    colors['both'] = 'black'

    # axes.plot(tvec, anticip_reaches)
    axes.plot(tvec, SessionsDf['f_anticip_left'].values, color=colors['left'])
    axes.plot(tvec, SessionsDf['f_anticip_right'].values, color=colors['right'])
    axes.plot(tvec, SessionsDf['f_anticip_left'].values + SessionsDf['f_anticip_right'].values, color=colors['both'])
    axes.set_title('anticipatory reaches over days')
    axes.set_xticks(range(SessionsDf.shape[0]))
    axes.set_xticklabels(SessionsDf['date'],rotation=45, ha="right")
    axes.set_xlabel('date')
    axes.set_ylabel('fraction of trials\nwith anticip. reach')
    # axes.set_ylim(0,0.5)
    sns.despine(fig)

    title = Animal.Nickname + ' - anticipatory reaches'
    axes.set_title(title)
    fig.tight_layout()

    if save is not None:
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)


# %%
"""
 
 ########  ########  ######## ##     ##    ###    ######## ##     ## ########  ########    ########  ########    ###     ######  ##     ## ########  ######  
 ##     ## ##     ## ##       ###   ###   ## ##      ##    ##     ## ##     ## ##          ##     ## ##         ## ##   ##    ## ##     ## ##       ##    ## 
 ##     ## ##     ## ##       #### ####  ##   ##     ##    ##     ## ##     ## ##          ##     ## ##        ##   ##  ##       ##     ## ##       ##       
 ########  ########  ######   ## ### ## ##     ##    ##    ##     ## ########  ######      ########  ######   ##     ## ##       ######### ######    ######  
 ##        ##   ##   ##       ##     ## #########    ##    ##     ## ##   ##   ##          ##   ##   ##       ######### ##       ##     ## ##             ## 
 ##        ##    ##  ##       ##     ## ##     ##    ##    ##     ## ##    ##  ##          ##    ##  ##       ##     ## ##    ## ##     ## ##       ##    ## 
 ##        ##     ## ######## ##     ## ##     ##    ##     #######  ##     ## ########    ##     ## ######## ##     ##  ######  ##     ## ########  ######  
 
"""

Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
Nicknames = ['Therapist']
Nicknames = ['Teacher']
task_name = 'learn_to_choose_v2'

# get animals by Nickname
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(folder)
Animals = [a for a in Animals if a.Nickname in Nicknames]

# %%
Animal = Animals[0]
SessionsDf = utils.get_sessions(Animal.folder)
SessionsDf = SessionsDf.groupby('task').get_group(task_name)
from Utils import metrics as m


for i, row in SessionsDf.iterrows():
    session_folder = Path(row['path'])
    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
    metrics = (m.get_start, m.get_stop, m.has_choice, m.get_correct_side, m.get_chosen_side, m.has_premature_reach, m.has_premature_choice)
    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics)

    try:
        n_choices = SessionDf.groupby('has_choice').get_group(True).shape[0]
        n_trials = SessionDf.shape[0]
        Df = groupby_dict(SessionDf, dict(has_choice=True, has_premature_reach=True))
        try:
            SessionsDf.loc[i,'f_prem_reach_left'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_reach=True, chosen_side='left')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_reach_left'] = 0
            pass        
        try:
            SessionsDf.loc[i,'f_prem_reach_right'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_reach=True, chosen_side='right')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_reach_right'] = 0
            pass
    except KeyError:
        SessionsDf.loc[i,'f_prem_reach_left'] = 0
        SessionsDf.loc[i,'f_prem_reach_right'] = 0
        pass

    try:
        n_choices = SessionDf.groupby('has_choice').get_group(True).shape[0]
        n_trials = SessionDf.shape[0]
        Df = groupby_dict(SessionDf, dict(has_choice=True, has_premature_choice=True))
        try:
            SessionsDf.loc[i,'f_prem_choice_left'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_choice=True, chosen_side='left')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_choice_left'] = 0
            pass        
        try:
            SessionsDf.loc[i,'f_prem_choice_right'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_choice=True, chosen_side='right')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_choice_right'] = 0
            pass
    except KeyError:
        SessionsDf.loc[i,'f_prem_choice_left'] = 0
        SessionsDf.loc[i,'f_prem_choice_right'] = 0
        pass


#%%
fig, axes = plt.subplots(nrows=2,sharex=True,sharey=True)
tvec = range(SessionsDf.shape[0])


import matplotlib as mpl
colors = dict(left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95),
              both='black')

# axes.plot(tvec, anticip_reaches)
axes[0].plot(tvec, SessionsDf['f_prem_reach_left'].values, color=colors['left'])
axes[0].plot(tvec, SessionsDf['f_prem_reach_right'].values, color=colors['right'])
axes[0].plot(tvec, SessionsDf['f_prem_reach_left'].values + SessionsDf['f_prem_reach_right'].values, color=colors['both'])

axes[1].plot(tvec, SessionsDf['f_prem_choice_left'].values, color=colors['left'])
axes[1].plot(tvec, SessionsDf['f_prem_choice_right'].values, color=colors['right'])
axes[1].plot(tvec, SessionsDf['f_prem_choice_left'].values + SessionsDf['f_prem_choice_right'].values, color=colors['both'])


axes[0].set_title('premature reaches over days')
axes[1].set_xticks(range(SessionsDf.shape[0]))
axes[1].set_xticklabels(SessionsDf['date'],rotation=45, ha="right")
axes[1].set_xlabel('date')
axes[0].set_ylabel('fraction of trials\nwith premature reach')
axes[1].set_ylabel('fraction of trials\nwith premature choice')
# axes.set_ylim(0,0.5)
sns.despine(fig)
fig.tight_layout()


# %%
"""
 
 ########  ##     ## ##    ##    ##     ## ####  ######   ######  #### ##    ##  ######   
 ##     ## ##     ## ###   ##    ###   ###  ##  ##    ## ##    ##  ##  ###   ## ##    ##  
 ##     ## ##     ## ####  ##    #### ####  ##  ##       ##        ##  ####  ## ##        
 ########  ##     ## ## ## ##    ## ### ##  ##   ######   ######   ##  ## ## ## ##   #### 
 ##   ##   ##     ## ##  ####    ##     ##  ##        ##       ##  ##  ##  #### ##    ##  
 ##    ##  ##     ## ##   ###    ##     ##  ##  ##    ## ##    ##  ##  ##   ### ##    ##  
 ##     ##  #######  ##    ##    ##     ## ####  ######   ######  #### ##    ##  ######   
 
"""

# Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
# Nicknames = ['Lumberjack']
Nicknames = ['Poolboy']

task_name = 'learn_to_choose_v2'

# get animals by Nickname
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(folder)

Animals = [a for a in Animals if a.Nickname in Nicknames]

overwrite = True

for i, Animal in enumerate(Animals):
    utils.printer("processing Animal %s" % Animal.Nickname, 'msg')

    # bias
    if 1:
        outpath = Animal.folder / 'plots' / 'bias_evolution.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing plot %s" % outpath.stem, 'msg')
            plot_bias_over_sessions(Animal.folder, save=outpath)

    # anticipatory reaches
    if 0:
        outpath = Animal.folder / 'plots' / 'plot_anticipatory_reaches_over_sessions.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing plot %s" % outpath.stem, 'msg')
            plot_anticipatory_reaches_over_sessions(Animal.folder, save=outpath)





















# %% 
"""
 
 ##        #######     ###    ########   ######  ######## ##       ##          ########  ######## ##          ###    ######## ######## ########  
 ##       ##     ##   ## ##   ##     ## ##    ## ##       ##       ##          ##     ## ##       ##         ## ##      ##    ##       ##     ## 
 ##       ##     ##  ##   ##  ##     ## ##       ##       ##       ##          ##     ## ##       ##        ##   ##     ##    ##       ##     ## 
 ##       ##     ## ##     ## ##     ## ##       ######   ##       ##          ########  ######   ##       ##     ##    ##    ######   ##     ## 
 ##       ##     ## ######### ##     ## ##       ##       ##       ##          ##   ##   ##       ##       #########    ##    ##       ##     ## 
 ##       ##     ## ##     ## ##     ## ##    ## ##       ##       ##          ##    ##  ##       ##       ##     ##    ##    ##       ##     ## 
 ########  #######  ##     ## ########   ######  ######## ######## ########    ##     ## ######## ######## ##     ##    ##    ######## ########  
 
"""

# session path

# seems to have one channel inverted
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-08_11-06-44_learn_to_choose_v2")

# has no clock pulses
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02996_Policeman/2021-10-12_12-33-45_learn_to_choose_v2")

# notes: plumber seems to have correct flipping
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-11_12-35-21_learn_to_choose_v2")
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-07_12-00-07_learn_to_choose_v2")

# lifeguard should then be similar
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-08_11-02-31_learn_to_choose_v2")
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-14_10-20-51_learn_to_choose_v2")

# poolboy last good
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-15_14-15-36_learn_to_choose_v2")

# poolboy on his way down
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-18_12-32-41_learn_to_choose_v2")

# lumberjack recent
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-22_10-45-30_learn_to_choose_v2")

# a non-initiating mouse 
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-15_12-35-12_learn_to_choose_v2")

# poolboy back up but autostart trials
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-25_14-03-04_learn_to_choose_v2")

# %%
LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
# LogDf['min'] = LogDf['t'] / 60000 # this can eventually be moved

### LoadCell Data
LoadCellDf = bhv.parse_bonsai_LoadCellData(session_folder / 'bonsai_LoadCellData.csv')

# Syncer
from Utils import sync
# cam_sync_event = sync.parse_cam_sync(session_folder / 'bonsai_frame_stamps.csv')
lc_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv', trig_len=100, ttol=5)
arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

Sync = sync.Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['cam'] = cam_sync_event['t'].values # used for what?
# Sync.sync('arduino','cam')
Sync.sync('arduino','loadcell')

LogDf['t_orig'] = LogDf['t']
LogDf['t'] = Sync.convert(LogDf['t'].values, 'arduino', 'loadcell')

# %% preprocessing
samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).mean()
LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).mean()

# %%  
times = LogDf.groupby('name').get_group('TRIAL_ENTRY_EVENT')['t'].values
pre, post = -1000, 1000
fig, axes = plt.subplots(nrows=2,sharex=True,sharey=False)

x_avgs = []
y_avgs = []
for i,t in enumerate(tqdm(times[:100])):
    Df = bhv.time_slice(LoadCellDf, t+pre, t+post, reset_index=False)
    # these colors need to be thorougly checked
    axes[0].plot(Df['t'].values - t, Df['x'])
    axes[1].plot(Df['t'].values - t, Df['y'])

    x_avgs.append(Df['x'].values)
    y_avgs.append(Df['y'].values)

x_avgs = np.average(np.array(x_avgs),axis=0)
y_avgs = np.average(np.array(y_avgs),axis=0)

tvec = np.linspace(pre,post,x_avgs.shape[0])
axes[0].plot(tvec, x_avgs, color='k',lw=2)
axes[1].plot(tvec, y_avgs, color='k',lw=2)


kws = dict(linestyle=':',lw=1, alpha=0.8, color='k')
for ax in axes:
    ax.axhline(-500, **kws)
    ax.axvline(0, **kws)

# %% categorizing pushes by clustering
# slice all pushes
F = LoadCellDf[['x','y']].values
th = 500
L = F < -th

events = np.where(np.diff(np.logical_and(L[:,0],L[:,1])) == 1)[0]
times = [LoadCellDf.iloc[int(i)]['t'] for i in events]

pre, post = -500,500
All_Pushes = []
for i, t in enumerate(tqdm(times)):
    push = bhv.time_slice(LoadCellDf, t+pre, t+post, reset_index=False)
    if ~np.any(pd.isna(push).values):
        All_Pushes.append(push)

n_samples = int(np.median([p.shape[0] for p in All_Pushes]))
Pushes = [p[['x','y']].values for p in All_Pushes if p.shape[0] == n_samples]
push_times = [p['t'].values[0]-pre for p in All_Pushes if p.shape[0] == n_samples]

# %% reshape and cluster
P = np.concatenate([p.T.flatten()[:,np.newaxis] for p in Pushes],axis=1)
# P = P[:,50:]

from sklearn.cluster import KMeans
n_clusters = 5
clust = KMeans(n_clusters=n_clusters).fit(P.T)
labels = clust.labels_
labels_unique = np.unique(labels)

# sort labels by occurence
order = np.argsort([np.sum(labels == label) for label in np.unique(labels)])
labels_unique = labels_unique[order]

# %% plot each
tvec = np.linspace(pre,post,n_samples)
fig, axes = plt.subplots(nrows=2, ncols=n_clusters, figsize=[6,3],sharey=True)
colors = sns.color_palette('tab10', n_colors=n_clusters)

for i, label in enumerate(labels_unique):
    ix = np.where(labels == label)[0]
    axes[0,i].plot(tvec, np.median(P[:n_samples,ix],1), color=colors[i])
    axes[1,i].plot(tvec, np.median(P[n_samples:,ix],1), color=colors[i])

    axes[0,i].set_title("N=%i" % np.sum(labels == label))

for ax in axes.flatten():
    ax.axvline(0, linestyle=':', color='k', lw=1)
    ax.axhline(-500, linestyle=':', color='k', lw=1)

fig.tight_layout()
sns.despine(fig)

# %% look at temporal distribution of each clusters event wrt events
# get timepoints for each
push_times = push_times
# push_times = push_times[50:]
event_times = np.array(push_times)
EventDf = pd.DataFrame(zip(['PUSH_EVENT'] * event_times.shape[0], event_times, labels), columns=['name','t','var'])
LogDf = pd.concat([LogDf,EventDf])
LogDf = LogDf.sort_values('t')

# %% 
trial_avail_times = LogDf.groupby('name').get_group("TRIAL_AVAILABLE_EVENT")['t'].values
pre, post = -1000, 2000

label_times = {}
for label in labels_unique:
    label_times[label] = []

for label in labels_unique:
    event_times = LogDf.groupby(['name','var']).get_group(('PUSH_EVENT',label))['t'].values
    for t in trial_avail_times:
        dtimes = event_times - t
        ix = np.logical_and( (dtimes > pre), ( dtimes < post) )
        if np.sum(ix) > 0:
            label_times[label].append(dtimes[ix])

    label_times[label] = np.concatenate(label_times[label])
# %%
fig, axes = plt.subplots(nrows=n_clusters,sharex=True,sharey=True)
bins = np.linspace(pre, post, 50)
for i, label in enumerate(labels_unique):
    axes[i].hist(label_times[label],bins=bins,color=colors[i])

for ax in axes:
    ax.axvline(0, linestyle=':',linewidth=1,color='k',alpha=0.5)

sns.despine(fig)
fig.tight_layout()






# %%
"""
 
 ######## ########  ######  ######## #### ##    ##  ######    ######  
    ##    ##       ##    ##    ##     ##  ###   ## ##    ##  ##    ## 
    ##    ##       ##          ##     ##  ####  ## ##        ##       
    ##    ######    ######     ##     ##  ## ## ## ##   ####  ######  
    ##    ##             ##    ##     ##  ##  #### ##    ##        ## 
    ##    ##       ##    ##    ##     ##  ##   ### ##    ##  ##    ## 
    ##    ########  ######     ##    #### ##    ##  ######    ######  
 
"""
# %% 
# session path
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-19_13-58-59_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-19_10-47-25_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-20_11-17-43_learn_to_choose_v2")

# session where poolboy starts to decrease
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-18_12-32-41_learn_to_choose_v2")
LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
from Utils import metrics as m

metrics = (m.get_start, m.get_stop, m.has_choice, m.get_correct_side, m.get_chosen_side, m.has_anticipatory_reach, m.has_premature_reach, m.get_outcome)
SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics)

print(np.sum(SessionDf['has_premature_reach']) / SessionDf.shape[0])

# %%
colors = dict(success="#72E043", 
             reward="#3CE1FA", 
             correct="#72E043", 
             incorrect="#F56057", 
             premature="#9D5DF0", 
             missed="#F7D379")

categorial_cols = ['outcome']
for category_col in categorial_cols:
    categories = SessionDf[category_col].unique()
    categories = [cat for cat in categories if not pd.isna(cat)]
    for category in categories:
        SessionDf['is_'+category] = SessionDf[category_col] == category

# setup general filter
SessionDf['exclude'] = False

# def plot_session_overview(SessionDf, axes=None):

fig, axes = plt.subplots()

outcomes = SessionDf['outcome'].unique()

for i, row in SessionDf.iterrows():
    t = row['t_on']
    try:
        axes.plot([t,t],[0,1],lw=2.5,color=colors[row.outcome],zorder=-1)
    except KeyError:
        pass

    w = 0.05
    if row.correct_side == 'left':
        axes.plot([t,t],[0-w,0+w],lw=1,color='k')
    if row.correct_side == 'right':
        axes.plot([t,t],[1-w,1+w],lw=1,color='k')

    if row.has_choice:
        if row.chosen_side == 'left':
            axes.plot(t,-0.0,'.',color='k')
        if row.chosen_side == 'right':
            axes.plot(t,1.0,'.',color='k')

    # if row.in_corr_loop and not sp.isnan(row.in_corr_loop):
    #     axes.plot([i,i],[-0.1,1.1],color='red',alpha=0.5,zorder=-2,lw=3)
    
    # if row.timing_trial and not sp.isnan(row.timing_trial):
    #     axes.plot([i,i],[-0.1,1.1],color='cyan',alpha=0.5,zorder=-2,lw=3)

# success rate
hist=10
for outcome in ['missed']:
    srate = (SessionDf.outcome == outcome).rolling(hist).mean()
    tvec = SessionDf['t_on'].values
    axes.plot(tvec,srate,lw=1.5,color='black',alpha=0.75)
    axes.plot(tvec,srate,lw=1,color=colors[outcome],alpha=0.75)

# valid trials
SDf = SessionDf.groupby('is_missed').get_group(False)
srate = (SDf.outcome == 'correct').rolling(hist).mean()
axes.plot(SDf['t_on'].values ,srate,lw=1.5,color='k')

axes.axhline(0.5,linestyle=':',color='k',alpha=0.5)

# deco
axes.set_xlabel('trial #')
axes.set_ylabel('success rate')
# return axes
# %%
