# %% imports
import sys
import numpy as np
from scipy.signal import gaussian
import pandas as pd

from matplotlib import pyplot as plt
import matplotlib as mpl

# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams["figure.dpi"] = 166  # the screens in the viv

sys.path.append("/home/georg/Projects/TaskControl")

from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics_partial as metrics

# %% path setup
animals_folder = "/media/georg/htcondor/shared-paton/georg/Animals_licking"

# nickname = 'Bayes'
# nickname = 'Student'
nickname = "Fisher"


Animals = utils.get_Animals(animals_folder)
(animal,) = utils.select(Animals, Nickname=nickname)
# task = np.unique([Session.task for Session in animal.get_sessions()])[1]
Sessions = utils.get_Sessions(animal.folder)
Session = Sessions[-1]
task = Session.task

print("analyzing: %s" % Session)

# %% Extraction and processing log data
LogDf = bhv.get_LogDf_from_path(Session.folder / "arduino_log.txt")

# preprocessing
LogDf = bhv.filter_spans_to_event(LogDf, "LICK_ON", "LICK_OFF", t_min=5, t_max=200)

# metrics
# get_trial_type = partial(metrics.get_var, var_name="this_trial_type")
# get_delay = partial(metrics.get_var, var_name="this_delay")
# get_reward_magnitude = partial(metrics.get_var, var_name="reward_magnitude")

session_metrics = (metrics.get_start, metrics.get_stop)
SessionDf, TrialDfs = bhv.get_SessionDf(
    LogDf,
    session_metrics,
    trial_entry_event="TRIAL_ENTRY_EVENT",
    trial_exit_event="TRIAL_AVAILABLE_EVENT",
)


# %% lick analysis
# -> these will eventually move to a lib
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


# %%
fig, axes = plt.subplots()

reward_times = bhv.get_events_from_name(LogDf, "REWARD_EVENT")

for i, row in SessionDf.iterrows():
    lick_times = (
        bhv.get_events_from_name(TrialDfs[i], "LICK_EVENT")["t"].values - row.t_on
    )
    axes.plot(lick_times, np.ones(lick_times.shape[0]) * i, ".", color="k", alpha=0.5)

axes.set_xlim(0, 12000)

# lick rate
sd = 0.1  # s
dt = 0.005  # np.diff(tvec_session)[0]
w = gaussian(int(sd / dt * 10), int(sd / dt))
w = w / w.sum()

lick_rate, tvec_session = event_rate(LogDf, "LICK_EVENT", w, dt=dt)

lick_rate_trial = []
for i, row in SessionDf.iterrows():
    ix = np.logical_and(tvec_session > row.t_on / 1e3, tvec_session < row.t_off / 1e3)
    lick_rate_trial.append(lick_rate[ix])

# jagged mean
D = lick_rate_trial
max_size = np.max([len(d) for d in D])
J = np.zeros((max_size, len(D)))
J[:] = np.nan
for i in range(len(D)):
    J[: len(D[i]), i] = D[i]
twinax = plt.twinx(axes)
twinax.plot(np.arange(0, max_size * dt, dt) * 1e3, np.nanmean(J, axis=1), color="r")

# from scipy.signal import gaussian
# sd = 0.1 # s
# dt = 0.005 #
# w = gaussian(int(sd/dt * 10), int(sd/dt))
# w = w/w.sum()

# lick_rate, lick_rate_tvec = event_rate(LogDf, "LICK_EVENT", w, dt=dt)

# %% REWARD / LICK RATE


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

sd = 30  # s
sd = 0.1
dt = 0.005  # .np.diff(tvec_session)[0]
w = gaussian(int(sd / dt * 10), int(sd / dt))
# w[:int(w.shape[0]/2)] = 0 # only past (?)
w = w / w.sum()
# plot_w(w)

reward_rate, tvec_session = event_rate(LogDf, "REWARD_EVENT", w, dt=dt)
print(reward_rate.shape)
print(tvec_session.shape)
reward_magnitude = 4.5  # ul
reward_rate = reward_rate * reward_magnitude * 60

# lick rate
sd = 0.1  # s
dt = 0.005  # np.diff(tvec_session)[0]
w = gaussian(int(sd / dt * 10), int(sd / dt))
w = w / w.sum()

lick_rate, tvec_session = event_rate(LogDf, "LICK_EVENT", w, dt=dt)
print(lick_rate.shape)
print(tvec_session.shape)

fig, axes = plt.subplots()
axes.plot(tvec_session / 60, reward_rate, color="b")
axes.set_ylabel("ul/min")
axes2 = plt.twinx(axes)
axes2.plot(tvec_session / 60, lick_rate, color="k", lw=1, alpha=0.85)
axes2.set_ylabel("licks/s")

# for t in bhv.get_events_from_name(LogDf, "LICK_EVENT")['t'].values/1e3:
#     axes2.axvline(t, color='r', lw=0.5, alpha=0.1)


# %%
