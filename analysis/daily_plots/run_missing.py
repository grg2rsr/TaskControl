# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

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

from plot_session_overview import plot_session_overview
from plot_psychometric import plot_psychometric
from plot_init_hists import plot_init_hist
from plot_choice_RTs import plot_choice_RTs
from plot_reward_collection_rt import plot_reward_collection_rts
from plot_bias_over_sessions import plot_bias_over_sessions

# %%
"""
 
  ######  ########  ######   ######  ####  #######  ##    ##    ##       ######## ##     ## ######## ##       
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ##    ##       ##       ##     ## ##       ##       
 ##       ##       ##       ##        ##  ##     ## ####  ##    ##       ##       ##     ## ##       ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##    ##       ######   ##     ## ######   ##       
       ## ##             ##       ##  ##  ##     ## ##  ####    ##       ##        ##   ##  ##       ##       
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ###    ##       ##         ## ##   ##       ##       
  ######  ########  ######   ######  ####  #######  ##    ##    ######## ########    ###    ######## ######## 
 
"""

# Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
Nicknames = ['Poolboy']
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
        session_folder = Path(row['path'])
        Session = utils.Session(session_folder)
        
        # session overview
        if 0:
            outpath = Animal.folder / 'plots' / 'session_overviews' / ('session_overview_%s_%s_day_%s.png' % (Session.date, Session.time, Session.day))
            if not outpath.exists() or overwrite:
                plot_session_overview(session_folder, save=outpath)

        # init histograms
        if 1:
            outpath = Animal.folder / 'plots' / 'init_histograms' / ('init_histogram_%s_%s_day_%s.png' % (Session.date, Session.time, Session.day))
            if not outpath.exists() or overwrite:
                # plot_init_hist(session_folder)
                plot_init_hist(session_folder, save=outpath)


        # reward collection rts
        if 0:
            outpath = Animal.folder / 'plots' / 'reward_collection_rts' / ('reward_collection_rts_%s_%s_day_%s.png' % (Session.date, Session.time, Session.day))
            if not outpath.exists() or overwrite:
                plot_reward_collection_rts(session_folder, save=outpath)

        # choice RTs
        if 0:
            outpath = Animal.folder / 'plots' / 'choice_rts' / ('choice_rts_%s_%s_day_%s.png' % (Session.date, Session.time, Session.day))
            if not outpath.exists() or overwrite:
                plot_choice_RTs(session_folder, save=outpath)

        # psychometric
        if 0:
            outpath = Animal.folder / 'plots' / 'psychometrics' / ('psychometric_%s_%s_day_%s.png' % (Session.date, Session.time, Session.day))
            if not outpath.exists() or overwrite:
                plot_psychometric(session_folder, save=outpath)
  


# %%
"""
 
    ###     ######  ########   #######   ######   ######      ######  ########  ######   ######  ####  #######  ##    ##  ######  
   ## ##   ##    ## ##     ## ##     ## ##    ## ##    ##    ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
  ##   ##  ##       ##     ## ##     ## ##       ##          ##       ##       ##       ##        ##  ##     ## ####  ## ##       
 ##     ## ##       ########  ##     ##  ######   ######      ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
 ######### ##       ##   ##   ##     ##       ##       ##          ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##     ## ##    ## ##    ##  ##     ## ##    ## ##    ##    ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
 ##     ##  ######  ##     ##  #######   ######   ######      ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""

Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
# Nicknames = ['Lumberjack']
# Nicknames = ['Poolboy']

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
        outpath = Animal.folder / 'plots' / 'bias_across_sessions.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing plot %s" % outpath.stem, 'msg')
            plot_bias_over_sessions(Animal.folder, task_name, save=outpath)

    # anticipatory reaches
    if 0:
        outpath = Animal.folder / 'plots' / 'plot_anticipatory_reaches_over_sessions.png'
        if not outpath.exists() or overwrite:
            utils.printer("processing plot %s" % outpath.stem, 'msg')
            plot_anticipatory_reaches_over_sessions(Animal.folder, save=outpath)


# %%
