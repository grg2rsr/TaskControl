# %%
import sys
from pathlib import Path
import numpy as np
import pandas as pd

import matplotlib as mpl

# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams["figure.dpi"] = 166  # the screens in the viv

sys.path.append("/home/georg/Projects/TaskControl")

from Utils import behavior_analysis_utils as bhv
from Utils import metrics

# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-14_11-50-48_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-11-03_13-02-12_learn_to_choose_v2")
path = "/media/georg/storage/shared-paton/georg/Animals_reaching/JJP-04311_Onion/2022-05-25_12-30-39_interval_categorization_v2"
path = "/media/georg/storage/shared-paton/georg/Animals_reaching/JJP-04311_Onion/2022-05-26_16-07-52_interval_categorization_v2"
path = "/media/georg/storage/shared-paton/georg/Animals_reaching/JJP-04311_Onion/2022-05-27_11-43-10_interval_categorization_v2"

path = "/media/georg/storage/shared-paton/georg/Animals_smelling/JJP-04308/2022-06-07_14-27-24_twodistributionsv6_GR"
session_folder = Path(path)
LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")

session_metrics = (
    metrics.get_start,
    metrics.has_choice,
    metrics.get_chosen_side,
    metrics.get_outcome,
    metrics.get_correct_side,
    metrics.get_timing_trial,
    metrics.get_interval,
    metrics.get_interval_category,
    metrics.get_in_corr_loop,
    metrics.has_reward_collected,
    metrics.get_autodeliver_trial,
    metrics.get_chosen_interval,
)

SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics)
SessionDf = bhv.expand_columns(SessionDf, ["outcome"])

outcomes = SessionDf["outcome"].unique()
if np.any(pd.isna(outcomes)):
    SessionDf.loc[pd.isna(SessionDf["outcome"]), "outcome"] = "reward_autodelivered"

# %%
from plot_session_overview import *

plot_session_overview(session_folder, LogDf=LogDf, save=None, on_t=True)


# %%
from plot_choice_RTs import *

bins = np.linspace(0, 10000, 20)
plot_choice_RTs(session_folder, bins=bins)

# %%
