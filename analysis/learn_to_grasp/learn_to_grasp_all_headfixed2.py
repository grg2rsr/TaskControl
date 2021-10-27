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

def groupby_dict(Df, Dict):
    return Df.groupby(list(Dict.keys())).get_group(tuple(Dict.values()))

# plot
tab10 = sns.color_palette('tab10',n_colors=5)
colors = dict(reach=tab10[1],
              grasp=tab10[2],
              rewarded=tab10[0],
              anticipatory=tab10[4])


# %%
folder = Path("/home/georg/data/grasping_animals/")
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(folder)

# %%

folders = dict(
        Lifeguard="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909",
        Lumberjack="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911",
        Teacher="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912",
        Plumber="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994",
        Poolboy="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995",
        Policeman="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02996",
        Therapist="/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997")

# %%

for animal, folder in folders.items():
    print("processing %s" % animal)
    folder = Path(folder)
animal = 'Teacher'
Animal = utils.Animal(folders[animal])
SessionsDf = utils.get_sessions(Animal.folder).groupby('task').get_group('learn_to_choose_v2')
SessionsDf = SessionsDf.reset_index()

for day, row in SessionsDf.iterrows():
    print(day)
    folder = Path(SessionsDf.loc[day,'path'])

    LogDf = bhv.get_LogDf_from_path(folder / "arduino_log.txt")
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
    # day = 1
    title = Animal.display() + ' - day %s' % (day+1)
    sns.despine(fig)
    fig.suptitle(title)
    axes[1,0].set_xlabel('time (min)')
    axes[0,1].legend(fontsize='small')
    fig.tight_layout()

    os.makedirs(folder / 'plots', exist_ok=True)
    outpath = folder / 'plots' / 'reach_durations.png'
    plt.savefig(outpath, dpi=600)
    plt.close(fig)


# %% adding some numbers

# %%


# axes[0].plot(ReachesDf['t_on']/6e4, ReachesDf['dt'],'.',label='reach left')
# axes[0].plot(GraspsDf['t_on']/6e4, GraspsDf['dt'],'.',label='grasp left')
# axes[0].plot(ReachesRightDf['t_on']/6e4, -1 * ReachesRightDf['dt'],'.',label='reach right')
# axes[0].plot(GraspsRightDf['t_on']/6e4, -1 * GraspsRightDf['dt'],'.',label='grasp righ')
# axes[0].axhline(0,linestyle=':',color='k',alpha=0.5)

# wm = 3
# w = wm*60*1000
# w2 = int(w/2)
# avgs = []
# t_max = LogDf.iloc[-1]['t']
# for t in tqdm(range(w2*2,int(t_max - w2),w2)):
#     Df_reach = bhv.time_slice(ReachesDf, t-w/2, t+w/2, col='t_on')
#     avgs.append((t,np.nanmean(Df_reach['dt'])))

# avgs = np.array(avgs)
# axes[0].plot(avgs[:,0]/6e4,avgs[:,1],color='red',label='%s min avg' % wm)

