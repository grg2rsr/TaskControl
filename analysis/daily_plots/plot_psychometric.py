# %%
import sys
import os
import numpy as np
import scipy as sp
import pandas as pd
import seaborn as sns
from tqdm import tqdm

from matplotlib import pyplot as plt
import matplotlib as mpl

# mpl.rcParams['figure.dpi'] = 331 # laptop
mpl.rcParams["figure.dpi"] = 166  # the screens in the viv

sys.path.append("/home/georg/code/TaskControl")
from Utils import behavior_analysis_utils as bhv
from Utils import utils
from Utils import metrics

colors = dict(
    success="#72E043",
    reward="#3CE1FA",
    correct="#72E043",
    incorrect="#F56057",
    premature="#9D5DF0",
    missed="#F7D379",
    left=mpl.cm.PiYG(0.05),
    right=mpl.cm.PiYG(0.95),
)


def plot_psychometric(session_folder, N=1000, kind="true", fit_lapses=True, save=None):
    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")

    # exit here if there are no timing trials
    if not np.any(LogDf.groupby("var").get_group("timing_trial")["value"]):
        return None

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

    # the three variants
    if kind == "true":
        SDf = bhv.intersect(
            SessionDf, has_choice=True, is_premature=False, timing_trial=True
        )
    if kind == "cued":
        SDf = bhv.intersect(
            SessionDf, has_choice=True, is_premature=False, timing_trial=False
        )
    if kind == "premature":
        SDf = bhv.intersect(SessionDf, has_choice=True, is_premature=True)

    fig, axes = plt.subplots()

    # plot the choices as p(Long)
    intervals = list(np.sort(SDf["this_interval"].unique()))
    for i, interval in enumerate(intervals):
        Df = bhv.intersect(SDf, this_interval=interval)
        f = np.sum(Df["chosen_interval"] == "long") / Df.shape[0]
        axes.plot(interval, f, "o", color="r")
    axes.set_ylabel("p(choice = long)")

    # plot the fit
    y = SDf["chosen_side"].values == "right"
    x = SDf["this_interval"].values
    x_fit = np.linspace(0, 3000, 500)

    try:
        y_fit, p_fit = bhv.log_reg_cf(x, y, x_fit, fit_lapses=fit_lapses)
    except ValueError:
        utils.printer("no trials for one side", "warning")
        return None
    axes.plot(x_fit, y_fit, color="red", linewidth=2, alpha=0.75)

    if fit_lapses:
        # add lapse rate as text to the axes
        lapse_upper = p_fit[3] + p_fit[2]
        lapse_lower = p_fit[3]
        axes.text(
            intervals[0],
            lapse_lower + 0.05,
            "%.2f" % lapse_lower,
            ha="center",
            va="center",
        )
        axes.text(
            intervals[-1],
            lapse_upper + 0.05,
            "%.2f" % lapse_upper,
            ha="center",
            va="center",
        )

    if N is not None:
        # simulating random choices based, respecting session bias
        bias = (SDf["chosen_side"] == "right").sum() / SDf.shape[0]
        R = np.zeros((x_fit.shape[0], N))
        P = []
        R[:] = np.nan
        for i in tqdm(range(N)):
            # simulating random choices
            rand_choices = sp.rand(SDf.shape[0]) < bias
            try:
                y_fit, p_fit = bhv.log_reg_cf(
                    x, rand_choices, x_fit, fit_lapses=fit_lapses
                )
                R[:, i] = y_fit
                P.append(p_fit)
            except RuntimeError:
                pass

        # filter out NaN cols
        R = R[:, ~np.isnan(R[0, :])]
        R = R.T
        P = np.array(P)

        # Several statistical boundaries
        alphas = [5, 0.5, 0.05]
        opacities = [0.2, 0.2, 0.2]
        for alpha, a in zip(alphas, opacities):
            R_pc = np.percentile(R, (alpha, 100 - alpha), 0)
            axes.fill_between(
                x_fit, R_pc[0], R_pc[1], color="blue", alpha=a, linewidth=0
            )

    # deco
    w = 0.05
    axes.set_ylim(0 - w, 1 + w)
    axes.axvline(1500, linestyle=":", alpha=0.5, lw=1, color="k")
    axes.axhline(0.5, linestyle=":", alpha=0.5, lw=1, color="k")

    axes.set_xlim(500, 2500)
    axes.set_xlabel("time (ms)")

    Session = utils.Session(session_folder)
    Animal = utils.Animal(session_folder.parent)
    title = " - ".join([Animal.display(), Session.date, "day: %s" % Session.day])

    sns.despine(fig)
    fig.suptitle(title)
    fig.tight_layout()
    fig.subplots_adjust(top=0.9)

    if save is not None:
        os.makedirs(save.parent, exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)


# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-25_15-59-02_learn_to_choose_v2")
# # session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-21_11-47-21_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02909_Lifeguard/2021-10-22_10-39-25_learn_to_choose_v2")

# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-10-25_15-59-02_learn_to_choose_v2")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975_Marquez/2021-05-18_09-41-58_learn_to_fixate_discrete_v1")
# session_folder = Path("/media/georg/data/animals_reaching/therapist/2021-10-29_15-41-48_learn_to_choose_v2")

# marquez last
# session_folder = Path("/media/georg/data/reaching_dlc/marquez_last_session/2021-05-18_09-41-58_learn_to_fixate_discrete_v1")
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-11-02_16-11-32_learn_to_choose_v2")
# plot_psychometric(session_folder, kind='premature', N=500, fit_lapses=True)
# #
# %matplotlib qt5
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-11-12_16-30-36_learn_to_choose_v2")
# plot_psychometric(session_folder, kind='cued', N=100, fit_lapses=True)

# %%
