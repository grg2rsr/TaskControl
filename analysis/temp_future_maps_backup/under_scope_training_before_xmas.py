# %% imports
import sys
import numpy as np
import pandas as pd
import seaborn as sns

from matplotlib import pyplot as plt
import matplotlib as mpl

# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams["figure.dpi"] = 166  # the screens in the viv

sys.path.append("/home/georg/Projects/TaskControl")

from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics_partial as metrics
from functools import partial

# %% path setup
animals_folder = "/media/georg/htcondor/shared-paton/georg/Animals_smelling_imaging"

# nickname = 'wasabi'
# nickname = 'chili'
nickname = "pepper"

Animals = utils.get_Animals(animals_folder)
(animal,) = utils.select(Animals, Nickname=nickname)
# task = np.unique([Session.task for Session in animal.get_sessions()])[1]
Sessions = utils.get_Sessions(animal.folder)
Session = Sessions[-2]
task = Session.task

print("analyzing: %s" % Session)

# %% Extraction and processing log data
LogDf = bhv.get_LogDf_from_path(Session.folder / "arduino_log.txt")

# preprocessing
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

SessionDf, TrialDfs = bhv.get_SessionDf(
    LogDf,
    session_metrics,
    trial_entry_event="TRIAL_ENTRY_EVENT",
    trial_exit_event="TRIAL_AVAILABLE_EVENT",
)

# %% lick analysis
DelaysDf = SessionDf[SessionDf["this_trial_type"] == 0.0]
pre, post = (-2000, 10000)

delays = DelaysDf.this_delay.unique()
delays = np.sort(delays)

lick_times = {}
for i, delay in enumerate(delays):
    lick_times[delay] = []
    Df = DelaysDf.groupby("this_delay").get_group(delay)
    for j, row in Df.iterrows():
        try:
            SDf = bhv.time_slice(LogDf, row.t_on + pre, row.t_on + post)
            # align on odor onset
            t0 = SDf.groupby("name").get_group("ODOR_ON").iloc[0]["t"]
            lick_times_rel = (
                SDf.groupby("name").get_group("LICK_EVENT")["t"].values - t0
            )
            lick_times[delay].append(lick_times_rel)
        except KeyError:
            lick_times[delay].append(np.array([]))

# adding rate
from scipy.signal import gaussian

tvec = np.arange(pre, post + 100, 50)
w = gaussian(15, 2)
w = w / w.sum()

lick_rates_delay = {}
for i, delay in enumerate(delays):
    lick_rates = []
    for j, t_licks in enumerate(lick_times[delay]):
        y = np.ones(t_licks.shape[0]) * j
        lick_rate = np.zeros(tvec.shape[0])
        lick_rate[np.digitize(t_licks, tvec)] = 1
        lick_rate = np.convolve(lick_rate, w, mode="same")
        lick_rates.append(lick_rate)
    lick_rates = np.array(lick_rates)
    lick_rates_delay[delay] = lick_rates

# plotting raster
n_delays = delays.shape[0]
delay_colors = sns.color_palette("deep", n_colors=n_delays)
n_trials_per_delay = [len(lick_times[delay]) for delay in delays]
curr_max = 0
fig, axes = plt.subplots(
    nrows=n_delays, gridspec_kw=dict(height_ratios=n_trials_per_delay), sharex=True
)

for i, delay in enumerate(delays):
    for j, t_licks in enumerate(lick_times[delay]):
        y = np.ones(t_licks.shape[0]) * j
        axes[i].plot(
            t_licks, y, ".", color="k", alpha=0.5, markeredgewidth=0, markersize=3.5
        )
    axes[i].axvline(delay, color="dodgerblue", alpha=0.8, lw=2)
    axes[i].axvspan(0, 1000, color="gray", alpha=0.5, linewidth=0)

    ax = plt.twinx(axes[i])
    lick_rate_avg = np.average(lick_rates_delay[delay], axis=0)
    curr_max = np.max([curr_max, np.max(lick_rate_avg)])
    ax.set_ylim(0, curr_max * 1.1)
    ax.plot(tvec, lick_rate_avg, color=delay_colors[i], lw=2)

title = str(Session)
fig.suptitle(title)
sns.despine(fig, top=True, right=False)
axes[-1].set_xlabel("time (ms)")
fig.tight_layout()

# plots_folder = Session.folder / 'plots'
# os.makedirs(plots_folder, exist_ok=True)
# plt.savefig(plots_folder / 'lick_plots.png', dpi=600)


# %% REWARD / LICK RATE
def event_rate(LogDf: pd.DataFrame, event_name: str, w: np.ndarray, dt: float):
    """returns rate of event over the entire session
    everything in seconds!"""
    Df = bhv.get_events_from_name(LogDf, event_name)
    t_start = LogDf["t"].values[0] / 1e3
    t_stop = LogDf["t"].values[-1] / 1e3
    tvec_session = np.arange(t_start, t_stop, dt)
    event_rate = calc_rate(Df["t"].values / 1e3, tvec_session, w)
    return event_rate, tvec_session


def calc_rate(t_stamps, tvec, w):
    """everything in [s] so rate turns out as [1/s]"""
    ix = np.digitize(t_stamps, tvec) - 1
    rate = np.zeros(tvec.shape[0])
    dt = np.diff(tvec)[0]
    rate[ix] = 1
    return np.convolve(rate, w, mode="same") / dt


def plot_w(w):
    wvec = np.linspace(0, w.shape[0] * dt, w.shape[0])
    wvec = wvec - wvec[-1] / 2
    fig, axes = plt.subplots()
    axes.plot(wvec, w)
    return axes


# reward rate
# dt = 0.005
# w = np.ones(int(120/ dt))
# w = w/w.sum()

from scipy.signal import gaussian

sd = 30  # s
dt = 0.005  # .np.diff(tvec_session)[0]
w = gaussian(int(sd / dt * 10), int(sd / dt))
# w[:int(w.shape[0]/2)] = 0 # only past (?)
w = w / w.sum()
# plot_w(w)

reward_rate, tvec_session = event_rate(LogDf, "REWARD_EVENT", w, dt=dt)
reward_magnitude = 4.5  # ul
reward_rate = reward_rate * reward_magnitude * 60

# lick rate
from scipy.signal import gaussian

sd = 0.1  # s
dt = 0.005  # np.diff(tvec_session)[0]
w = gaussian(int(sd / dt * 10), int(sd / dt))
w = w / w.sum()

lick_rate, tvec_session = event_rate(LogDf, "LICK_EVENT", w, dt=dt)

fig, axes = plt.subplots()
axes.plot(tvec_session / 60, reward_rate, color="b")
axes.set_ylabel("ul/min")
axes2 = plt.twinx(axes)
axes2.plot(tvec_session / 60, lick_rate, color="k", lw=1, alpha=0.85)
axes2.set_ylabel("licks/s")

# for t in bhv.get_events_from_name(LogDf, "LICK_EVENT")['t'].values/1e3:
#     axes2.axvline(t, color='r', lw=0.5, alpha=0.1)


# %%
