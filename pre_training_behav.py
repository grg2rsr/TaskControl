%matplotlib qt5
%load_ext autoreload
%autoreload 2

from matplotlib import pyplot as plt
import matplotlib as mpl
import behavior_analysis_utils as bhv
import pandas as pd
import re
from datetime import datetime

# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
import utils

from behavior_plotters import *

# Plotting Defaults
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"
plt.rcParams["xtick.major.size"] = 2
plt.rcParams["ytick.major.size"] = 2

SMALL_SIZE = 8
MEDIUM_SIZE = 10
BIGGER_SIZE = 12

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=MEDIUM_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title

# %% Analyze trajectories from event until choice for any group of sessions and any group of trials
animal_folder = utils.get_folder_dialog()
plot_dir = animal_folder / 'plots'
animal_meta = pd.read_csv(animal_folder / 'animal_meta.csv')
animal_id = animal_meta[animal_meta['name'] == 'ID']['value'].values[0]
nickname = animal_meta[animal_meta['name'] == 'Nickname']['value'].values[0]
os.makedirs(plot_dir, exist_ok=True)

task_name = ['learn_to_push_vis_feedback']
SessionsDf = utils.get_sessions(animal_folder)

PushSessionsDf = pd.concat([SessionsDf.groupby('task').get_group(name) for name in task_name])

paths = [Path(path) for path in PushSessionsDf['path']]

pretraining_sess = 3 # sessions with only instructed trials
first_event = "GO_CUE_EVENT"
second_event = "CHOICE_EVENT"
samples = 10000 # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
filter_pairs = [('has_choice', True), ('instructed_trial', False)] # filter all trials according to this(these) key(s)
plot_lim = 5000 # limits of trajectories

for path in tqdm(paths[pretraining_sess:], position=0, leave=True, desc= 'Plotting trajectories'):

    # Need to create loadcell.csv
    if not os.path.isfile(path / "loadcell_data.csv"):
        log_path = path.joinpath('arduino_log.txt')

        LoadCellDf, harp_sync = bhv.parse_harp_csv(path / "bonsai_harp_log.csv", save=True)
        arduino_sync = bhv.get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT")

        t_harp = pd.read_csv(path / "harp_sync.csv")['t'].values
        t_arduino = pd.read_csv(path / "arduino_sync.csv")['t'].values

        if t_harp.shape != t_arduino.shape:
            t_arduino, t_harp = bhv.cut_timestamps(t_arduino, t_harp, verbose = True)

        m, b = bhv.sync_clocks(t_harp, t_arduino, log_path)
    else:
        LoadCellDf = pd.read_csv(path / "loadcell_data.csv")

    LogDf = pd.read_csv(path / "LogDf.csv")
    LogDf = LogDf.loc[LogDf['t'] < LoadCellDf.iloc[-1]['t']]

    # median correction
    LoadCellDf['x'] = LoadCellDf['x'] - LoadCellDf['x'].rolling(samples).median()
    LoadCellDf['y'] = LoadCellDf['y'] - LoadCellDf['y'].rolling(samples).median()

    TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

    TrialDfs = []
    for i, row in TrialSpans.iterrows():
        TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

    metrics = (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.choice_RT, bhv.is_successful, bhv.get_outcome, bhv.get_instructed)
    SessionDf = bhv.parse_trials(TrialDfs, metrics)

    # Choose only trials according to filter pair
    TrialDfs = bhv.filter_trials_by(SessionDf,TrialDfs, filter_pairs)

    if type(TrialDfs) == list and len(TrialDfs) == 0:
        continue # go onto next cycle

    # ACTUAL PLOTTING
    trajectories_with_marker(LoadCellDf, TrialDfs, SessionDf, first_event, second_event, plot_lim, animal_id)

    # Saving figure
    match = re.search(r'\d{4}-\d{2}-\d{2}', str(path))
    date = datetime.strptime(match.group(), '%Y-%m-%d').date()
    plt.savefig(plot_dir / Path('trajectories_w_markers_' + str(filter_pairs) + "_" + str(date) + '.png'), dpi=300)

# %%
