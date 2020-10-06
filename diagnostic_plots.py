# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

# Custom made
import behavior_plotters as bhv_plt
import behavior_analysis_utils as bhv
import utils

# Utils
from pathlib import Path
from tqdm import tqdm
import time

# Viz
from matplotlib import pyplot as plt
import matplotlib as mpl
import pandas as pd
import numpy as np
import scipy as sp 
import seaborn as sns

# Plotting Defaults
plt.rcParams["xtick.direction"] = "in"
plt.rcParams["ytick.direction"] = "in"

# %%
"""
 #######  ##     ## ######## ########  ##     ## #### ######## ##      ##
##     ## ##     ## ##       ##     ## ##     ##  ##  ##       ##  ##  ##
##     ## ##     ## ##       ##     ## ##     ##  ##  ##       ##  ##  ##
##     ## ##     ## ######   ########  ##     ##  ##  ######   ##  ##  ##
##     ##  ##   ##  ##       ##   ##    ##   ##   ##  ##       ##  ##  ##
##     ##   ## ##   ##       ##    ##    ## ##    ##  ##       ##  ##  ##
 #######     ###    ######## ##     ##    ###    #### ########  ###  ###
"""

animal_fd_path = utils.get_folder_dialog(initial_dir="D:/TaskControl/Animals")
animal_tag = str(animal_fd_path).split('\\')[-1]
task_name = 'learn_to_push'

bhv.create_LogDf_LCDf_csv(animal_fd_path, task_name) # CHECK

# Obtaining Logpaths for specific task
SessionsDf = utils.get_sessions(animal_fd_path)
paths = [Path(path) for path in SessionsDf.groupby('task').get_group(task_name).path]

LogDfs = []
working_paths = [] # some paths can have t_harp or maybe missing log problems

# Obtain list of LogDf and LCDf from csv stored
for path in tqdm(paths, desc="Obtaining LogDfs and LCDfs' CSV"):

    # Open LogDf and LCDf from csv
    try:
        LogDfs.append(pd.read_csv(path.joinpath('LogDf.csv')))
    except:
        print('Session with path ' + str(path) + ' does not contain LogDf')
        continue
    
    working_paths.append(path)

axes = bhv_plt.plot_sessions_overview(LogDfs, working_paths, task_name, animal_tag)
plt.show()


# %%

"""
 ######  #### ##    ##  ######   ##       ########     ######  ########  ######   ######  ####  #######  ##    ##
##    ##  ##  ###   ## ##    ##  ##       ##          ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ##
##        ##  ####  ## ##        ##       ##          ##       ##       ##       ##        ##  ##     ## ####  ##
 ######   ##  ## ## ## ##   #### ##       ######       ######  ######    ######   ######   ##  ##     ## ## ## ##
      ##  ##  ##  #### ##    ##  ##       ##                ## ##             ##       ##  ##  ##     ## ##  ####
##    ##  ##  ##   ### ##    ##  ##       ##          ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ###
 ######  #### ##    ##  ######   ######## ########     ######  ########  ######   ######  ####  #######  ##    ##
"""

# Parameters
window_size = 1000
pre, post = -1000, 4000
align_ref = "SECOND_TIMING_CUE_EVENT"

# Get single session folder path
session_fd_path = utils.get_folder_dialog(initial_dir="D:/TaskControl/Animals")

animal_tag = str(session_fd_path).split('\\')[-2]
session_date = str(session_fd_path).split('\\')[-1][:10]

LogDf = pd.read_csv(session_fd_path.joinpath('LogDf.csv'))
temp_LC_csv = pd.read_csv(session_fd_path.joinpath('loadcell_data.csv'))
temp_LC_csv['x'] = temp_LC_csv['x'] - temp_LC_csv['x'].rolling(window_size).median()
temp_LC_csv['y'] = temp_LC_csv['y'] - temp_LC_csv['y'].rolling(window_size).median()
LoadCellDf = temp_LC_csv

TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_ENTRY_EVENT","ITI_STATE")

TrialDfs = []
for i, row in TrialSpans.iterrows():
    TrialDfs.append(bhv.time_slice(LogDf,row['t_on'],row['t_off']))

bhv_plt.plot_timing_overview(LogDf, LoadCellDf, TrialDfs)

# %%
"""
##     ## ##     ## ##       ######## #### ########  ##       ########
###   ### ##     ## ##          ##     ##  ##     ## ##       ##
#### #### ##     ## ##          ##     ##  ##     ## ##       ##
## ### ## ##     ## ##          ##     ##  ########  ##       ######
##     ## ##     ## ##          ##     ##  ##        ##       ##
##     ## ##     ## ##          ##     ##  ##        ##       ##
##     ##  #######  ########    ##    #### ##        ######## ########
"""

# Parameters
window_size = 1000
pre, post = -1000, 4000
first_cue_ref = "FIRST_TIMING_CUE_EVENT"
align_ref = "SECOND_TIMING_CUE_EVENT"
task_name = 'learn_to_time'

# Loading datasets
animal_fd_path = utils.get_folder_dialog(initial_dir="D:/TaskControl/Animals")
SessionsDf = utils.get_sessions(animal_fd_path)
paths = [Path(path) for path in SessionsDf.groupby('task').get_group(task_name).path]

for path_tuple in enumerate(tqdm(paths)):
    try:
        path = path_tuple[1]

        animal_tag = str(path).split('\\')[-2]
        session_date = str(path).split('\\')[-1][:10]

        # time how long it takes for this visualization 
        start_time = time.time()

        LogDf = pd.read_csv(path.joinpath('LogDf.csv'))
        temp_LC_csv = pd.read_csv(path.joinpath('loadcell_data.csv'))
        temp_LC_csv['x'] = temp_LC_csv['x'] - temp_LC_csv['x'].rolling(window_size).median()
        temp_LC_csv['y'] = temp_LC_csv['y'] - temp_LC_csv['y'].rolling(window_size).median()
        LoadCellDf = temp_LC_csv

        TrialSpans = bhv.get_spans_from_names(LogDf,"TRIAL_ENTRY_EVENT","ITI_STATE")

        TrialDfs = []
        for i, row in TrialSpans.iterrows():
            TrialDfs.append(bhv.time_slice(LogDf,row['t_on'],row['t_off']))

        SessionDf = bhv.parse_trials(TrialDfs, (bhv.get_start, bhv.get_stop, bhv.has_choice, bhv.get_choice, bhv.is_successful, bhv.get_interval, bhv.get_outcome))

        " Create big gridspec containing all axes and plot in them"
        fig = plt.figure()
        gs = fig.add_gridspec(8, 7)

        # General trial info
        fig_ax1a = fig.add_subplot(gs[0,0:2])
        fig_ax1b = fig.add_subplot(gs[0,2:3])
        bhv_plt.general_info(LogDf, path, [fig_ax1a, fig_ax1b])

        # Heat map plots for X/Y
        fig_ax2 = fig.add_subplot(gs[1:,0:3])
        bhv_plt.plot_forces_heatmaps(LogDf, LoadCellDf, align_ref, pre, post, fig_ax2)

        fig.set_tight_layout(True)

        # Sucess rate over session
        fig_ax3 = fig.add_subplot(gs[:3,3:5])
        bhv_plt.plot_success_rate(SessionDf, LogDf, 10, fig_ax3)

        # Psychometric adapted from Georg's code
        fig_ax4 = fig.add_subplot(gs[3:6,3:5])
        bhv_plt.simple_psychometric(SessionDf, fig_ax4)

        # Choice matrix - trials incorrect
        fig_ax5a = fig.add_subplot(gs[6:,3])
        fig_ax5b = fig.add_subplot(gs[6:,4])
        bhv_plt.plot_choice_matrix(SessionDf,LogDf,'incorrect', fig_ax5a)
        bhv_plt.plot_choice_matrix(SessionDf,LogDf,'premature', fig_ax5b)

        # Force magnitude aligned to 1st and 2nd timing cues with lick freq. on top
        bin_width = 75 # ms
        fig_ax6a = fig.add_subplot(gs[:3,5])
        fig_ax6b = fig.add_subplot(gs[:3,6])
        bhv_plt.plot_force_magnitude(LoadCellDf, SessionDf, TrialDfs, first_cue_ref, align_ref, bin_width, [fig_ax6a, fig_ax6b])

        # CT histogram to detect/quantify biases or motor strategies
        bin_width = 100 # ms
        fig_ax7a = fig.add_subplot(gs[3:5,5])
        fig_ax7b = fig.add_subplot(gs[3:5,6])
        bhv_plt.plot_choice_time_hist(LogDf, TrialDfs, bin_width, [fig_ax7b, fig_ax7a]) # switched temporarily

        # Trajectory plots
        fig_ax8a = fig.add_subplot(gs[5:,5])
        bhv_plt.plot_forces_trajectories(LogDf, LoadCellDf, TrialDfs, align_ref, 'incorrect', fig_ax8a)
        fig_ax8b = fig.add_subplot(gs[5:,6])
        bhv_plt.plot_forces_trajectories(LogDf, LoadCellDf, TrialDfs, align_ref, 'correct', fig_ax8b)

        fig.suptitle('Session overview for ' + str(animal_tag) + ' at ' + str(session_date))

        plt.savefig(str(animal_fd_path) + '/plots/session' + str(path_tuple[0]+1) + '.png')

        print("--- Total plotting time took %.4s seconds ---" % (time.time() - start_time))

        plt.close() 
        
    except:
        plt.close() 
        pass
