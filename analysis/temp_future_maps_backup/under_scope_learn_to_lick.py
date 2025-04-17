# %% imports
import sys
from pathlib import Path
import numpy as np

from matplotlib import pyplot as plt
import matplotlib as mpl

# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams["figure.dpi"] = 166  # the screens in the viv

sys.path.append("/home/georg/Projects/TaskControl")

from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics_partial as metrics

from functools import partial


# %% path
animal_folder = (
    "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging/JJP-05425"
)
# animal_folder = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging/JJP-05472"
# animal_folder = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging/JJP-05475"
animal_folder = Path(animal_folder)

SessionsDf = utils.get_sessions(animal_folder)
SessionsDf = SessionsDf.groupby("task").get_group("learn_to_lick_v2")
session_folder = Path(SessionsDf.iloc[-1]["path"])  # last session

# this becomes
Sessions = utils.get_Sessions(animal)


print("analyzing %s" % session_folder)

# %% get / preprocess data
LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min=5, t_max=200)

# metrics
get_trial_type = partial(metrics.get_var, var_name="this_trial_type")
get_delay = partial(metrics.get_var, var_name="this_delay")
get_reward_magnitude = partial(metrics.get_var, var_name="reward_magnitude")

session_metrics = (
    metrics.get_start,
    metrics.get_stop,
    get_trial_type,
    get_delay,
    get_reward_magnitude,
)

# parse into trials
SessionDf, TrialDfs = bhv.get_SessionDf(
    LogDf, session_metrics, trial_entry_event="TRIAL_ENTRY_EVENT"
)

# %%
reward_times = bhv.get_events_from_name(LogDf, "REWARD_EVENT")["t"].values
Dfs = bhv.event_based_time_slice(LogDf, "REWARD_EVENT", pre=-3000, post=3000)

fig, axes = plt.subplots()
for i, t in enumerate(reward_times):
    try:
        lick_times_rel = Dfs[i].groupby("name").get_group("LICK_EVENT")["t"].values - t
        axes.plot(
            lick_times_rel,
            np.ones(lick_times_rel.shape[0]) * i,
            ".",
            color="k",
            alpha=0.5,
        )
    except KeyError:
        pass


# %% lick analysis - extracting
# DelaysDf = SessionDf[SessionDf['this_trial_type'] == 0.0]
# pre, post = (-2000,11000)

# delays = DelaysDf.this_delay.unique()
# delays = np.sort(delays)
# lick_times = {}
# for i,delay in enumerate(delays):
#     lick_times[delay] = []
#     Df = DelaysDf.groupby('this_delay').get_group(delay)
#     for j, row in Df.iterrows():
#         try:
#             SDf = bhv.time_slice(LogDf, row.t_on + pre, row.t_on + post)
#             # align on odor onset
#             t0 = SDf.groupby('name').get_group("ODOR_ON").iloc[0]['t']
#             lick_times_rel = SDf.groupby('name').get_group('LICK_EVENT')['t'].values - t0
#             lick_times[delay].append(lick_times_rel)
#         except KeyError:
#             lick_times[delay].append(np.array([]))

# %% plotting raster
# import seaborn as sns
# n_delays = delays.shape[0]
# delay_colors = sns.color_palette('deep',n_colors=n_delays)
# n_trials_per_delay = [len(lick_times[delay]) for delay in delays]
# fig, axes = plt.subplots(nrows = len(delays), gridspec_kw=dict(height_ratios=n_trials_per_delay),sharex=True)

# for i,delay in enumerate(delays):
#     licks_in_trial = lick_times[delay]
#     for j, licks in enumerate(licks_in_trial):
#         t = licks
#         y = np.ones(t.shape[0])*j
#         axes[i].plot(t,y,'.',color='k',alpha=0.5, markeredgewidth=0)
#     axes[i].axvline(delay,color='dodgerblue',alpha=0.8,lw=2)
#     axes[i].axvspan(0,1000,color='gray',alpha=0.5,linewidth=0)

# # adding rate
# tvec = np.arange(pre,post+100,50)
# from scipy.signal import gaussian
# w = gaussian(15,2)
# w = w / w.sum()
# for i,delay in enumerate(delays):
#     licks_in_trial = lick_times[delay]

#     fs = []
#     for j, licks in enumerate(licks_in_trial):
#         t = licks
#         y = np.ones(t.shape[0])*j
#         f = np.zeros(tvec.shape[0])
#         f[np.digitize(t, tvec)] = 1
#         f = np.convolve(f, w, mode='same')
#         fs.append(f)
#     F = np.array(fs)
#     ax = plt.twinx(axes[i])
#     ax.plot(tvec, np.average(F,axis=0),color=delay_colors[i], lw=2)

# Animal = utils.Animal(session_folder.parent)
# Session = utils.Session(session_folder)
# title = ' - '.join([Animal.ID,Animal.Nickname,Session.date,Session.time])
# fig.suptitle(title)
# sns.despine(fig)
# axes[-1].set_xlabel('time (ms)')
# fig.tight_layout()

# plots_folder = session_folder / 'plots'
# os.makedirs(plots_folder, exist_ok=True)
# plt.savefig(plots_folder / 'lick_plots.png', dpi=600)

# %%
