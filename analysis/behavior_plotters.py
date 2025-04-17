# %matplotlib qt5
# %load_ext autoreload
# %autoreload 2

import matplotlib as mpl

mpl.rcParams["figure.dpi"] = 166
from matplotlib import pyplot as plt
from matplotlib import patches

import sys

sys.path.append("..")

from Utils import behavior_analysis_utils as bhv
import pandas as pd

# this should be changed ...
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
import calendar

"""
 
 ########  ##        #######  ######## ######## ######## ########   ######  
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##    ## 
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##       
 ########  ##       ##     ##    ##       ##    ######   ########   ######  
 ##        ##       ##     ##    ##       ##    ##       ##   ##         ## 
 ##        ##       ##     ##    ##       ##    ##       ##    ##  ##    ## 
 ##        ########  #######     ##       ##    ######## ##     ##  ######  
 
"""


def plot_session_overview(LogDf, t_ref, pre, post, axes=None, how="dots", cdict=None):
    """plots a session overview"""

    if axes is None:
        axes = plt.gca()

    if cdict is None:
        # implement
        pass

    for i, t in enumerate(tqdm(t_ref)):
        Df = bhv.time_slice(LogDf, t - pre, t + post, "t")

        for name, group in Df.groupby("name"):
            # plot events
            if name.endswith("_EVENT"):
                event_name = name
                times = group["t"] - t

                if how == "dots":
                    axes.plot(
                        times,
                        [i] * len(times),
                        ".",
                        color=cdict[event_name],
                        alpha=0.75,
                    )  # a bar

                if how == "bars":
                    for time in times:
                        axes.plot(
                            [time, time],
                            [i - 0.5, i + 0.5],
                            lw=2,
                            color=cdict[event_name],
                            alpha=0.75,
                        )  # a bar

            # plot spans
            if (
                name.endswith("_ON") and name != "LICK_ON"
            ):  # special case: exclude licks
                span_name = name.split("_ON")[0]
                # Df_sliced = bhv.log2Span(Df, span_name)
                # Df_sliced = bhv.spans_from_event_names(Df, span_name+'_ON', span_name+'_OFF')
                on_name = span_name + "_ON"
                off_name = span_name + "_OFF"
                SpansDf = bhv.get_spans_from_names(Df, on_name, off_name)
                for j, row_s in SpansDf.iterrows():
                    time = row_s["t_on"] - t
                    dur = row_s["dt"]
                    rect = plt.Rectangle(
                        (time, i - 0.5), dur, 1, facecolor=cdict[span_name], linewidth=2
                    )
                    axes.add_patch(rect)

    for key in cdict.keys():
        axes.plot([0], [0], color=cdict[key], label=key, lw=4)
    axes.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc="lower left",
        ncol=3,
        mode="expand",
        borderaxespad=0.0,
        fontsize="xx-small",
    )
    axes.invert_yaxis()
    axes.set_xlabel("time (ms)")
    axes.set_ylabel("trials")

    return axes


def plot_psth(EventsDf, t_ref, bins=None, axes=None, how="fill", **kwargs):
    """plots a psth of the event in EventDf on the axis"""
    if axes is None:
        axes = plt.gca()

    pre, post = bins[0], bins[-1]

    # bins = np.zeros(bins.shape)

    values = []
    for t in t_ref:  # for every task event time
        times = bhv.time_slice(EventsDf, t + pre, t + post)["t"] - t
        values.append(times.values)  # get number of licks from EventsDf
    values = np.concatenate(values)

    if how == "steps":
        counts, bins = np.histogram(values, bins=bins)
        axes.step(bins[1:], counts, **kwargs)
    if how == "fill":
        axes.hist(values, bins=bins, **kwargs)
    axes.set_xlabel("time (ms)")
    axes.set_ylabel("count")

    return axes


def plot_raster(EventsDf, t_ref, pre, post, axes=None, **kwargs):
    """simple raster plot"""
    if axes is None:
        axes = plt.gca()

    for i, t in enumerate(t_ref):
        times = bhv.time_slice(EventsDf, t - pre, t + post)["t"] - t
        axes.plot(times, np.ones(times.shape[0]) * i, ".", color="k")

    return axes


def plot_reward_collection_rate(SessionDf, history=None, axes=None):
    """plots success rate, if history given includes a rolling smooth"""
    if axes is None:
        axes = plt.gca()

    S = SessionDf.groupby("successful").get_group(True)
    x = S.index.values + 1

    # grand average rate
    y = np.cumsum(S["reward_collected"].values) / (S.index.values + 1)
    axes.plot(x, y, color="C0")

    if history is not None:
        y_filt = S["reward_collected"].rolling(history).mean()
        axes.plot(x, y_filt, color="C0", alpha=0.5)

    axes.set_ylabel("frac. rew collected")
    axes.set_xlabel("trial #")
    axes.set_title("reward collection rate")

    return axes


def plot_reward_collection_RT(SessionDf, bins=None, axes=None, **kwargs):
    """ """
    if axes is None:
        axes = plt.gca()

    values = (
        SessionDf.groupby("reward_collected")
        .get_group(True)["reward_collected_rt"]
        .values
    )

    if bins is None:
        bins = np.arange(0, values.max(), 25)

    axes.hist(values, bins=bins, **kwargs)
    # counts, bins = np.histogram(values,bins=bins)
    # axes.step(bins[1:], counts, color='r')
    axes.set_xlabel("time (ms)")
    axes.set_ylabel("count")
    axes.set_title("reward collection RT")

    return axes


"""
########  ####    ###     ######   ##    ##  #######   ######  ######## ####  ######     ##     ## ####
##     ##  ##    ## ##   ##    ##  ###   ## ##     ## ##    ##    ##     ##  ##    ##    ##     ##  ##
##     ##  ##   ##   ##  ##        ####  ## ##     ## ##          ##     ##  ##          ##     ##  ##
##     ##  ##  ##     ## ##   #### ## ## ## ##     ##  ######     ##     ##  ##          ##     ##  ##
##     ##  ##  ######### ##    ##  ##  #### ##     ##       ##    ##     ##  ##          ##     ##  ##
##     ##  ##  ##     ## ##    ##  ##   ### ##     ## ##    ##    ##     ##  ##    ##    ##     ##  ##
########  #### ##     ##  ######   ##    ##  #######   ######     ##    ####  ######      #######  ####
"""


def plot_general_info(LogDf, path, axes=None):
    "Plots general info about a session (trial outcome, water consumed and weight)"

    if axes is None:
        _, axes = plt.subplots()

    # Session info in axis A
    session_dur = round(
        (LogDf["t"].iat[-1] - LogDf["t"].iat[0]) / 60000
    )  # convert to min

    water_drank = len(bhv.get_events_from_name(LogDf, "REWARD_COLLECTED_EVENT")) * 10

    animal_meta = pd.read_csv(path.joinpath("animal_meta.csv"))
    weight = (
        round(float(animal_meta.at[6, "value"]) / float(animal_meta.at[4, "value"]), 2)
        * 100
    )

    axes[1].text(
        0.5,
        0,
        "Water drank: " + str(water_drank) + " ul",
        horizontalalignment="center",
        verticalalignment="center",
    )
    axes[1].text(
        0.5,
        0.5,
        "Session dur.: " + str(session_dur) + " min",
        horizontalalignment="center",
        verticalalignment="center",
    )
    axes[1].text(
        0.5,
        1,
        "Weight: " + str(weight) + "%",
        horizontalalignment="center",
        verticalalignment="center",
    )
    axes[1].axis("off")

    # Trial info in axis B
    trials_corr = len(bhv.get_events_from_name(LogDf, "CHOICE_CORRECT_EVENT"))
    trials_incorr = len(bhv.get_events_from_name(LogDf, "CHOICE_INCORRECT_EVENT"))

    try:
        trials_miss = len(bhv.get_events_from_name(LogDf, "CHOICE_MISSED_EVENT"))
    except:
        print("This session has no missed trials")
    try:
        trials_prem = len(bhv.get_events_from_name(LogDf, "PREMATURE_CHOICE_EVENT"))
    except:
        print("This session has no premature trials")

    trials = [trials_corr, trials_incorr, trials_prem, trials_miss]

    colors = {
        "green": "#2ca02c",
        "red": "#d62728",
        "pink": "#e377c2",
        "gray": "#7f7f7f",
    }

    category_names = ["Corr", "Incorr", "Pre", "Miss"]

    data = np.array(trials)
    data_cum = data.cumsum()

    axes[0].invert_yaxis()
    axes[0].set_xlim(0, np.sum(data).max())

    for i, color in enumerate(colors):
        widths = data[i]
        starts = data_cum[i] - widths
        axes[0].barh(
            0, widths, left=starts, height=0.25, color=color, label=category_names[i]
        )
        xcenters = starts + widths / 2

        # Plot numbers inside
        axes[0].text(
            xcenters, 0, str(int(widths)), ha="center", va="center", color="black"
        )

    axes[0].legend(
        ncol=len(category_names),
        bbox_to_anchor=(0, 1),
        loc="lower left",
        fontsize="small",
        frameon=False,
    )
    axes[0].axis("off")

    return axes


def plot_forces_heatmaps(
    LoadCellDf, SessionDf, TrialDfs, align_event, pre, post, force_thresh, animal_id
):
    """Plots heatmaps of LC forces in X/Y axes aligned to any event split by outcome (also marks choice times)"""

    # TODO: right now it computes choice RT's irrespective of the event used to align trials on

    order = [
        ("left", "correct"),
        ("left", "incorrect"),
        ("right", "correct"),
        ("right", "incorrect"),
    ]

    height_ratios = (
        SessionDf.groupby(["choice", "outcome"]).count()["t_on"].reindex(order).values
    )

    # Robust against trials missing for specific (choice,outcome) pair
    idx = []
    for i in range(len(height_ratios)):
        if np.isnan(height_ratios[i]):
            idx = i
    if idx:
        order.pop(idx)
        height_ratios = np.delete(height_ratios, idx, axis=0)

    fig, axes = plt.subplots(
        nrows=len(order),
        ncols=2,
        figsize=[7, 6],
        sharex=True,
        gridspec_kw=dict(height_ratios=height_ratios),
    )

    for i, (side, outcome) in enumerate(order):
        try:
            SDf = SessionDf.groupby(["choice", "outcome"]).get_group((side, outcome))
        except:
            continue

        Fx = []
        Fy = []
        choice_rt = []
        for _, row in SDf.iterrows():
            TrialDf = TrialDfs[row.name]
            t_align = TrialDf.loc[TrialDf["name"] == align_event, "t"].values[0]
            LCDf = bhv.time_slice(LoadCellDf, t_align - pre, t_align + post)
            Fx.append(LCDf["x"].values)
            Fy.append(LCDf["y"].values)
            choice_rt.append(bhv.choice_RT(TrialDf).values + pre)

        Fx = sp.array(Fx).T
        Fy = sp.array(Fy).T

        # Plot heatmaps
        heat1 = axes[i, 0].matshow(
            Fx.T, origin="lower", vmin=-force_thresh, vmax=force_thresh, cmap="PiYG"
        )
        heat2 = axes[i, 1].matshow(
            Fy.T, origin="lower", vmin=-force_thresh, vmax=force_thresh, cmap="PiYG"
        )
        axes[i, 0].axvline(x=pre, ymin=0, ymax=1, color="k", alpha=0.5)
        axes[i, 1].axvline(x=pre, ymin=0, ymax=1, color="k", alpha=0.5)

        # Plot choice_rt ticks
        ymin = np.arange(
            -0.5, len(choice_rt) - 1
        )  # need to shift since lines starts at center of trial
        ymax = np.arange(0.45, len(choice_rt))
        axes[i, 0].vlines(choice_rt, ymin, ymax, colors="k", linewidth=1)

    plt.setp(
        axes,
        xticks=np.arange(0, post + pre + 0.1, 500),
        xticklabels=np.arange(-pre / 1000, post / 1000 + 0.1, 0.5),
    )

    for ax in axes.flatten():
        ax.set_aspect("auto")

    for ax in axes[-1, :]:
        ax.xaxis.set_ticks_position("bottom")

    for ax, (side, outcome) in zip(axes[:, 0], order):
        ax.set_ylabel("\n".join([side, outcome]))

    for ax in axes.flatten():
        ax.set_xlim([-pre, post])

    axes[0, 0].set_title("X axis")
    axes[0, 1].set_title("Y axis")
    axes[-1, 0].set_xlabel("Time (s)")
    axes[-1, 1].set_xlabel("Time (s)")

    fig.suptitle("Forces aligned on " + str(align_event) + " for " + str(animal_id))
    fig.subplots_adjust(hspace=0.05)

    cbar = plt.colorbar(heat1, ax=axes[:, 0], orientation="horizontal", aspect=30)
    cbar.set_ticks([-3000, -1500, 0, 1500, 3000])
    cbar.set_ticklabels(["-3000 \n (Left)", "-1500", "0", "1500", "3000 \n (Right)"])

    cbar = plt.colorbar(heat1, ax=axes[:, 1], orientation="horizontal", aspect=30)
    cbar.set_ticks([-3000, -1500, 0, 1500, 3000])
    cbar.set_ticklabels(["-3000 \n (Back)", "-1500", "0", "1500", "3000 \n (Front)"])

    return axes


def plot_choice_RT_hist(SessionDf, choice_interval, bin_width):
    "Plots the choice RT histograms split by trial type and outcome"

    choices = ["left", "right"]
    outcomes = ["correct", "incorrect"]

    fig, axes = plt.subplots(
        nrows=len(outcomes),
        ncols=len(choices),
        figsize=[4, 4],
        sharex=True,
        sharey=True,
    )

    no_bins = round(choice_interval / bin_width)

    kwargs = dict(bins=no_bins, range=(0, choice_interval), alpha=0.5, edgecolor="none")

    for i, choice in enumerate(choices):
        for j, outcome in enumerate(outcomes):
            try:
                SDf = SessionDf.groupby(["choice", "outcome"]).get_group(
                    (choice, outcome)
                )
            except:
                continue

            ax = axes[j, i]

            choice_rts = SessionDf["choice_rt"].values
            ax.hist(choice_rts, **kwargs, label=str([choice, outcome]))
            ax.legend(
                loc="upper right",
                frameon=False,
                fontsize=8,
                handletextpad=0.3,
                handlelength=0.5,
            )

    # Formatting
    plt.setp(
        axes,
        xticks=np.arange(0, choice_interval + 1, 500),
        xticklabels=np.arange(0, (choice_interval / 1000) + 0.1, 0.5),
    )
    fig.suptitle("Choice RTs Histogram")
    axes[0, 0].set_title("left")
    axes[0, 1].set_title("right")
    axes[0, 0].set_ylabel("correct")
    axes[1, 0].set_ylabel("incorrect")

    for ax in axes[-1, :]:
        ax.set_xlabel("Time (s)")
    fig.tight_layout()

    return axes


def plot_success_rate(LogDf, SessionDf, history, axes=None):
    "Plots success rate with trial type and choice tickmarks"

    if axes is None:
        fig, axes = plt.subplots()

    x = SessionDf.index.values + 1

    # Plot trial outcome on the back
    # axes.plot(correctDf.index, correctDf['outcome'] == 'correct', '|',alpha=0.75,color='g')
    # correctDf = SessionDf[SessionDf['outcome'] == 'correct']

    line_width = 0.04

    # L/R trial types
    left_trials = SessionDf.loc[SessionDf["correct_zone"] == 4].index + 1
    y_left_trials = np.zeros(left_trials.shape[0]) - line_width
    right_trials = SessionDf.loc[SessionDf["correct_zone"] == 6].index + 1
    y_right_trials = np.zeros(right_trials.shape[0]) + 1 + line_width

    # L/R trial choices
    try:
        SDf = SessionDf.groupby("choice").get_group("left")
        left_choices = SDf.index.values + 1
        y_left_choices = np.zeros(left_choices.shape[0])
    except:
        pass

    try:
        SDf = SessionDf.groupby("choice").get_group("right")
        right_choices = SDf.index.values + 1
        y_right_choices = np.zeros(right_choices.shape[0]) + 1
    except:
        pass

    # If in correction loops
    in_corr_loop = SessionDf.loc[SessionDf["in_corr_loop"] == True].index + 1
    y_in_corr_loop = np.zeros(in_corr_loop.shape[0]) + 1 + 2 * line_width

    # If instructed trials
    in_instructed_trial = SessionDf.loc[SessionDf["instructed_trial"] == True].index + 1
    y_instructed_trial = np.zeros(in_instructed_trial.shape[0]) + 1 + 3 * line_width

    # Grand average rate
    y = np.cumsum(SessionDf["successful"].values) / (SessionDf.index.values + 1)

    # Plotting in the same order as computed
    axes.plot(left_trials, y_left_trials, "|", color="k")
    axes.plot(right_trials, y_right_trials, "|", color="k")
    axes.plot(left_choices, y_left_choices, "|", color="m", label="left choice")
    axes.plot(right_choices, y_right_choices, "|", color="green", label="right choice")
    axes.plot(in_corr_loop, y_in_corr_loop, "|", color="r", label="corr. loops")
    axes.plot(
        in_instructed_trial, y_instructed_trial, "|", color="blue", label="instructed"
    )
    axes.plot(x, y, color="C0", label="grand average")

    if history is not None:
        y_filt = SessionDf["successful"].rolling(history).mean()
        axes.plot(x, y_filt, color="C0", alpha=0.3, label="rolling mean")

    axes.set_ylabel("frac. successful")
    axes.set_xlabel("trial #")
    axes.set_title("Success rate")
    axes.legend(
        bbox_to_anchor=(0.0, 1.02, 1.0, 0.102),
        loc="upper center",
        handletextpad=0.3,
        frameon=False,
        mode="expand",
        ncol=6,
        borderaxespad=0.0,
        handlelength=0.5,
    )

    return axes


def plot_psychometric(SessionDf, axes=None):
    "Timing task classic psychometric fit to data"

    if axes is None:
        axes = plt.gca()

    # get only the subset with choices
    SDf = SessionDf.groupby("has_choice").get_group(True)
    y = SDf["choice"].values == "right"
    x = SDf["this_interval"].values

    # plot choices
    axes.plot(x, y, ".", color="k", alpha=0.5)
    axes.set_yticks([0, 1])
    axes.set_yticklabels(["short", "long"])
    axes.set_ylabel("choice")
    axes.axvline(1500, linestyle=":", alpha=0.5, lw=1, color="k")

    x_fit = np.linspace(0, 3000, 100)
    (line,) = plt.plot([], color="red", linewidth=2, alpha=0.75)
    line.set_data(x_fit, bhv.log_reg(x, y, x_fit))

    try:
        # %% random margin - with animal bias
        t = SDf["this_interval"].values
        bias = (SessionDf["choice"] == "right").sum() / SessionDf.shape[
            0
        ]  # This includes premature choices now!
        R = []
        for i in range(100):
            rand_choices = (
                np.rand(t.shape[0]) < bias
            )  # can break here if bias value is too low
            R.append(bhv.log_reg(x, rand_choices, x_fit))
        R = np.array(R)

        # Several statistical boundaries (?)
        alphas = [5, 0.5, 0.05]
        opacities = [0.5, 0.4, 0.3]
        for alpha, a in zip(alphas, opacities):
            R_pc = sp.percentile(R, (alpha, 100 - alpha), 0)
            # plt.plot(x_fit, R_pc[0], color='blue', alpha=a)
            # plt.plot(x_fit, R_pc[1], color='blue', alpha=a)
            plt.fill_between(x_fit, R_pc[0], R_pc[1], color="blue", alpha=a)
        plt.set_cmap
    except KeyError:
        print("Bias too high")

    plt.setp(
        axes,
        xticks=np.arange(0, 3000 + 1, 500),
        xticklabels=np.arange(0, 3000 // 1000 + 0.1, 0.5),
    )
    axes.set_xlabel("Time (s)")

    return axes


def plot_force_magnitude(
    LogDf,
    LoadCellDf,
    SessionDf,
    TrialDfs,
    first_cue_ref,
    second_cue_ref,
    pre,
    post,
    force_tresh,
    bin_width,
    filter_pairs,
    axes=None,
):
    "Plots the magnitude of the 2D forces vector aligned to 1st and 2nd cue with lick frequency histogram on top"

    if axes is None:
        _, axes = plt.subplots(1, 2, sharey=True, sharex=True)

    "Licks"
    twin_ax = axes[1].twinx()

    for filter_pair in tqdm(filter_pairs, position=0, leave=True, desc="Force Mag"):
        # Get Trials with specific outcome
        TrialDfs_filt = bhv.filter_trials_by(SessionDf, TrialDfs, filter_pair)

        if len(TrialDfs_filt) > 0:
            _, _, Fmag_1st = bhv.get_FxFy_window_aligned_on_event(
                LoadCellDf, TrialDfs_filt, first_cue_ref, pre, post
            )
            _, _, Fmag_2nd = bhv.get_FxFy_window_aligned_on_event(
                LoadCellDf, TrialDfs_filt, second_cue_ref, pre, post
            )

            F_avg_1st = np.mean(Fmag_1st, axis=1)
            F_avg_2nd = np.mean(Fmag_2nd, axis=1)

            licks = bhv.get_events_window_aligned_on_event(
                LogDf, second_cue_ref, pre, post
            )
            licks = np.array(licks) + pre

            # Plotting
            axes[0].plot(np.arange(len(F_avg_1st)) + 1, F_avg_1st, label=filter_pair)
            axes[1].plot(np.arange(len(F_avg_2nd)) + 1, F_avg_2nd, label=filter_pair)

            # Get lick histogram
            if len(licks) != 0:
                no_bins = round((post + pre) / bin_width)
                counts, bins = np.histogram(np.concatenate(licks), no_bins)
                licks_freq = np.divide(counts, ((bin_width / 1000) * Fmag_1st.shape[1]))
                twin_ax.step(bins[1:], licks_freq, alpha=0.5)
            else:
                pass

    " Force "
    # Left plot
    axes[0].legend(loc="upper right", frameon=False)
    axes[0].set_ylabel("Force magnitude (a.u.)")
    plt.setp(
        axes[0],
        xticks=np.arange(-pre, post + 1, 500),
        xticklabels=np.arange(-pre / 1000, post / 1000 + 0.1, 0.5),
    )

    # Right plot
    axes[1].legend(loc="upper right", frameon=False)
    plt.setp(
        axes[1],
        xticks=np.arange(-pre, post + 1, 500),
        xticklabels=np.arange(-pre / 1000, post / 1000 + 0.1, 0.5),
    )

    # Shared
    plt.setp(
        axes,
        yticks=np.arange(0, force_tresh + 1, 500),
        yticklabels=np.arange(0, force_tresh + 1, 500),
    )
    for ax in axes:
        ax.set_xlim(0, post + pre)
        ax.set_ylim(0, force_tresh)

    " Licks "
    twin_ax.tick_params(axis="y", labelcolor="C0")
    twin_ax.set_ylabel("Lick freq. (Hz)", color="C0")
    plt.setp(twin_ax, yticks=np.arange(0, 11), yticklabels=np.arange(0, 11))

    # hide the spines between axes
    axes[0].spines["right"].set_visible(False)
    axes[0].spines["top"].set_visible(False)
    axes[1].spines["left"].set_visible(False)
    axes[1].spines["top"].set_visible(False)

    twin_ax.spines["left"].set_visible(False)
    twin_ax.spines["top"].set_visible(False)

    axes[0].yaxis.tick_left()
    axes[1].tick_params(labelleft=False, left=False)

    axes[0].set_title("Align to " + str(first_cue_ref))
    axes[1].set_title("Align to " + str(second_cue_ref))

    return axes


def plot_choice_matrix(LogDf, SessionDf, trial_type, axes=None):
    "Plots percentage of choices made in a session in a 3x3 choice matrix following a KB layout"

    if axes is None:
        _, axes = plt.subplots()

    choice_matrix = np.zeros((3, 3))

    # Completed incorrect trials
    if trial_type == "incorrect":
        for trial in SessionDf.itertuples():
            if trial.outcome == "incorrect":
                choice_matrix = bhv.triaL_to_choice_matrix(trial, choice_matrix)

        no_incorrect_trials = len(LogDf[LogDf["name"] == "CHOICE_INCORRECT_EVENT"])
        choice_matrix_percentage = np.round(
            np.multiply(np.divide(choice_matrix, no_incorrect_trials), 100)
        )

    # Premature trials
    if trial_type == "premature":
        for trial in SessionDf.itertuples():
            if trial.outcome == "premature":
                choice_matrix = bhv.triaL_to_choice_matrix(trial, choice_matrix)

        no_premature_trials = len(LogDf[LogDf["name"] == "PREMATURE_CHOICE_EVENT"])
        choice_matrix_percentage = np.round(
            np.multiply(np.divide(choice_matrix, no_premature_trials), 100)
        )

    # Plot choice matrix independtly of input
    axes.matshow(choice_matrix_percentage, cmap="Reds")
    for (i, j), z in np.ndenumerate(choice_matrix_percentage):
        axes.text(j, i, "{:.0f}".format(z), ha="center", va="center")

    if trial_type == "incorrect":
        axes.set_title("Incorrect")
    if trial_type == "premature":
        axes.set_title("Premature")

    axes.axis("off")

    return axes


def plot_mean_trajectories(
    LogDf, LoadCellDf, SessionDf, TrialDfs, align_event, pre, post, animal_id, axes=None
):
    """Plots trajectories in 2D aligned to an event"""

    if axes == None:
        fig, axes = plt.subplots()

    Fx, Fy, _ = bhv.get_FxFy_window_aligned_on_event(
        LoadCellDf, TrialDfs, align_event, pre, post
    )
    F = [Fx, Fy]

    # time-varying color code
    cm = plt.cm.get_cmap("Greys")

    z = np.linspace(0, 1, num=F.shape[2])

    F_mean = np.mean(F, 0).T
    scatter = plt.scatter(F_mean[:, 0], F_mean[:, 1], c=z, cmap=cm, s=4)

    plt.clim(-0.3, 1)
    cbar = plt.colorbar(scatter, orientation="vertical", aspect=60)
    cbar.set_ticks([-0.3, 1])
    cbar.set_ticklabels([str(pre / 1000) + "s", str(post / 1000) + "s"])

    # Formatting
    axes.axvline(0, linestyle=":", alpha=0.5, lw=1, color="k")
    axes.axhline(0, linestyle=":", alpha=0.5, lw=1, color="k")
    axes.set_xlabel("Left/Right axis")
    axes.set_ylabel("Front/Back axis")
    axes.set_title(
        " Mean 2D trajectories aligned to " + str(align_event) + "" + str(animal_id)
    )
    axes.legend(frameon=False, markerscale=3)

    # Previously used to change dot color in legend
    # leg = axes.get_legend()
    # leg.legendHandles[0].set_color('red')

    axes.set_xlim([-3500, 3500])
    axes.set_ylim([-3500, 3500])
    [s.set_visible(False) for s in axes.spines.values()]

    # Bounding box
    Y_thresh = np.mean(LogDf[LogDf["var"] == "Y_thresh"].value.values)
    X_thresh = np.mean(LogDf[LogDf["var"] == "X_thresh"].value.values)

    if np.isnan(X_thresh):
        X_thresh = 2500
        print("No Y_tresh update on LogDf, using default for analysis")
    if np.isnan(Y_thresh):
        Y_thresh = 2500
        print("No Y_tresh update on LogDf, using default for analysis")

    axes.add_patch(
        patches.Rectangle(
            (-X_thresh, -Y_thresh), 2 * X_thresh, 2 * Y_thresh, fill=False
        )
    )

    if fig:
        fig.tight_layout()

    return axes


def plot_x_y_thresh_bias(LogDf, SessionDf):
    "X/Y threshold across time for a single session"

    fig, axes = plt.subplots()

    x = SessionDf.index
    bias = SessionDf["bias"].values
    x_thresh = SessionDf["X_thresh"].values

    axes.plot(x, x_thresh, color="royalblue", label="x_tresh")
    axes.set_ylabel("X-axis boundary force (a.u.)")
    axes.set_ylim([1600, 2600])
    axes.legend(loc="upper left", frameon=False)
    axes.set_xlabel("Time (s)")

    twin_ax = axes.twinx()
    twin_ax.plot(x, bias, color="crimson", label="bias")
    twin_ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    twin_ax.set_yticklabels(["left (0%)", "25%", "center (50%)", "75%", "right (100%)"])
    twin_ax.set_ylabel("Bias")
    twin_ax.legend(loc="upper right", frameon=False)

    fig.tight_layout()

    return axes


def plot_timing_overview(LogDf, LoadCellDf, TrialDfs, axes=None):
    """
    Heatmap aligned to 1st cue with 2nd cue and choice RT markers, split by trial outcome and trial type
    """

    pre, post = 500, 5000
    Fx, interval, choice_RT = [], [], []
    correct_idx, incorrect_idx, pre_idx, missed_idx = [], [], [], []

    if axes is None:
        fig = plt.figure(constrained_layout=True)

    # for every trial initiation
    i = 0
    for TrialDf in TrialDfs:
        time_1st = float(TrialDf[TrialDf.name == "FIRST_TIMING_CUE_EVENT"]["t"])

        F = bhv.time_slice(LoadCellDf, time_1st - pre, time_1st + post)
        if len(F) < post - pre:
            print("LCDf is shorter than LogDf!")
            continue

        Fx.append(F["x"])

        # Store indexes for different types of trials
        if bhv.get_outcome(TrialDf).values[0] == "correct":
            correct_idx.append(i)
        if bhv.get_outcome(TrialDf).values[0] == "incorrect":
            incorrect_idx.append(i)
        if bhv.get_outcome(TrialDf).values[0] == "premature":
            pre_idx.append(i)
        if bhv.get_outcome(TrialDf).values[0] == "missed":
            missed_idx.append(i)

        # Store information
        interval.append(int(bhv.get_interval(TrialDf)))
        choice_RT.append(float(bhv.choice_RT(TrialDf)))

        i = i + 1

    # Ugly and hacky way to do what I want
    interval = np.array(interval) + pre
    choice_RT = np.array(choice_RT) + interval
    correct_idx = np.array(correct_idx)
    incorrect_idx = np.array(incorrect_idx)
    pre_idx = np.array(pre_idx)
    missed_idx = np.array(missed_idx)
    Fx = np.array(Fx)

    # Sort the INDEXES (of data already split based on interval)
    corr_idx_sorted = correct_idx[np.argsort(interval[correct_idx])]
    incorr_idx_sorted = incorrect_idx[np.argsort(interval[incorrect_idx])]
    pre_idx_sorted = pre_idx[np.argsort(interval[pre_idx])]
    missed_idx_sorted = missed_idx[np.argsort(interval[missed_idx])]

    split_sorted_idxs_list = [
        corr_idx_sorted,
        incorr_idx_sorted,
        pre_idx_sorted,
        missed_idx_sorted,
    ]

    """ Plotting """
    heights = [
        len(corr_idx_sorted),
        len(incorr_idx_sorted),
        len(pre_idx_sorted),
        len(missed_idx_sorted),
    ]
    gs = fig.add_gridspec(ncols=1, nrows=4, height_ratios=heights)
    ylabel = ["Correct", "Incorrect", "Premature", "Missed"]

    for i, idxs in enumerate(split_sorted_idxs_list):
        axes = fig.add_subplot(gs[i])
        force_x_tresh = 2500
        heat = axes.matshow(
            Fx[idxs, :], cmap="RdBu", vmin=-force_x_tresh, vmax=force_x_tresh
        )  # X axis
        axes.set_aspect("auto")
        axes.axvline(500, linestyle="solid", alpha=0.5, lw=1, color="k")
        axes.axvline(2000, linestyle="solid", alpha=0.25, lw=1, color="k")

        # Second timing cue and choice RT bars
        ymin = np.arange(
            -0.5, len(idxs) - 1
        )  # need to shift since lines starts at center of trial
        ymax = np.arange(0.45, len(idxs))
        axes.vlines(interval[idxs], ymin, ymax, colors="k", alpha=0.75)
        axes.vlines(choice_RT[idxs], ymin, ymax, colors="#7CFC00", linewidth=2)

        if i == 0:
            axes.set_title("Forces X axis aligned to 1st timing cue")

        axes.set_ylabel(ylabel[i])

        axes.set_xticklabels([])
        axes.set_xticks([])
        axes.set_xlim(0, 5500)

    # Formatting
    axes.xaxis.set_ticks_position("bottom")
    plt.setp(
        axes,
        xticks=np.arange(0, post + pre + 1, 500),
        xticklabels=np.arange((-pre / 1000), (post / 1000) + 0.5, 0.5),
    )
    plt.xlabel("Time")

    cbar = plt.colorbar(heat, orientation="horizontal", aspect=50)
    cbar.set_ticks([-2000, -1000, 0, 1000, 2000])
    cbar.set_ticklabels(["Left (-2000)", "-1000", "0", "1000", "Right (2000)"])

    return axes


def plot_split_forces_magnitude(
    SessionDf,
    LoadCellDf,
    TrialDfs,
    align_event,
    pre,
    post,
    split_by,
    animal_id,
    axes=None,
):
    """
    Force magnitude for Fx and Fy split by any input as long as a metric in SessionDf contemplates it
    """

    if axes == None:
        fig, axes = plt.subplots(2, 1)

    if split_by != None:
        outcomes = SessionDf[
            split_by
        ].unique()  # get possible outcomes of given split criteria
        outcomes = [x for x in outcomes if str(x) != "nan"]

    for outcome in outcomes:
        try:
            SDf = SessionDf.groupby([split_by]).get_group(outcome)
        except:
            continue

        Fx = []
        Fy = []
        for _, row in SDf.iterrows():
            TrialDf = TrialDfs[row.name]
            t_align = TrialDf.loc[TrialDf["name"] == align_event, "t"].values[0]

            LCDf = bhv.time_slice(LoadCellDf, t_align - pre, t_align + post)
            Fx.append(LCDf["x"].values)
            Fy.append(LCDf["y"].values)

        Fx = np.array(Fx)
        Fy = np.array(Fy)

        # Compute mean force for each outcome aligned to event
        Fmagx = bhv.tolerant_mean(Fx)
        Fmagy = bhv.tolerant_mean(Fy)
        axes[0].plot(np.arange(len(Fmagx)) + 1, Fmagx, label=outcome)
        axes[1].plot(np.arange(len(Fmagy)) + 1, Fmagy, label=outcome)

    axes[0].set_ylabel("Left/Right axis")
    axes[1].set_ylabel("Back/Front axis")
    plt.setp(
        axes,
        xticks=np.arange(0, post + pre + 1, 500),
        xticklabels=np.arange(-pre / 1000, post / 1000 + 0.1, 0.5),
    )
    plt.suptitle(
        "Mean forces split by "
        + str(split_by)
        + " for separate Fx/Fy axis \n aligned to "
        + str(align_event)
        + " for "
        + str(animal_id)
    )

    fig.tight_layout()

    return axes


def trajectories_with_marker(
    LoadCellDf,
    TrialDfs,
    SessionDf,
    first_event,
    second_event,
    plot_lim,
    animal_id,
    axes=None,
):
    "Trajectories from first to second event (with markers at end of event)"

    if axes == None:
        fig, axes = plt.subplots(figsize=[4, 3])

    y_lim_offset = 1000  # offsets y limits because they push more down than up

    Fxs, Fys, _ = bhv.get_FxFy_window_between_events(
        LoadCellDf, TrialDfs, first_event, second_event
    )

    idx_left, idx_right = [], []
    for i, (Fx, Fy) in enumerate(zip(Fxs, Fys)):
        # All trajectories
        axes.plot(Fx, Fy, lw=0.5, alpha=0.1, zorder=-1)

        # Choice markers in the form of list of tuples (trial, last_point)
        if bhv.get_choice(TrialDfs[i]).values[0] == "left":
            idx_left.append((i, (np.isnan(Fx)).argmax(axis=0) - 1))

        elif bhv.get_choice(TrialDfs[i]).values[0] == "right":
            idx_right.append((i, (np.isnan(Fx)).argmax(axis=0) - 1))

    # TODO: turn this ugly hack into something actually elegant
    idx_left = tuple(np.array(idx_left).T)
    idx_right = tuple(np.array(idx_right).T)

    if idx_left:
        axes.plot(
            Fxs[idx_left],
            Fys[idx_left],
            "o",
            markersize=2,
            color="crimson",
            zorder=2,
            label="left",
        )
    if idx_right:
        axes.plot(
            Fxs[idx_right],
            Fys[idx_right],
            "o",
            markersize=2,
            color="royalblue",
            zorder=2,
            label="right",
        )

    axes.set_xlim(-plot_lim, plot_lim)
    axes.set_ylim(-plot_lim - y_lim_offset, plot_lim - y_lim_offset)

    # Center cross
    line_kwargs = dict(color="k", linestyle=":", linewidth=0.75, alpha=0.5, zorder=-100)
    axes.axvline(0, **line_kwargs)
    axes.axhline(0, **line_kwargs)

    # Boundaries lines
    line_kwargs = dict(color="k", lw=0.5, linestyle="-", alpha=0.75, zorder=-100)
    axes.axvline(-2500, **line_kwargs)
    axes.axvline(+2500, **line_kwargs)

    # Text
    axes.text(
        -y_lim_offset,
        plot_lim - 2 * y_lim_offset,
        str(len(TrialDfs)) + " trials",
        color="k",
    )
    axes.legend(title="Trial Type", loc="upper right", frameon=False, handletextpad=0.3)

    return axes


def autocorr_forces(LoadCellDf, TrialDfs, first_event, second_event, axes=None):
    "Compute the autocorrelation of trajectories between two events (classically computed vs through FFT)"

    if axes is None:
        fig, axes = plt.subplots(ncols=2, figsize=(6, 3))

    from numpy.fft import fft, ifft

    Fxs, Fys, _ = bhv.get_FxFy_window_between_events(
        LoadCellDf, TrialDfs, first_event, second_event, pad_with=0
    )

    # FFT solution
    dataRD = np.zeros((1, Fxs.shape[1], 2))  # carefull to only allocate a trial
    for Fx, Fy in zip(Fxs, Fys):
        data = np.dstack((Fx, Fy))  # 1st dim is trials, 2nd is length, 3rd is Fx/Fy

        # Padding because autocorrelation is circular and padding avoids wrapping
        padding = np.zeros((data.shape[0], data.shape[1] - 1, data.shape[2]))
        dataPadded = np.concatenate((data, padding), axis=1)

        dataFT = fft(dataPadded, axis=1)
        dataAC = ifft(
            dataFT * np.conjugate(dataFT), axis=1
        ).real  # http://www.marga.com.ar/6615/wiener-khinchin.pdf - only keep real part to be numerically robust
        dataRD = np.vstack(
            (dataRD, np.round(dataAC, 10)[:, : data.shape[1], :])
        )  # round output and cut second half which is symmetric

    dataAC_mean = np.mean(dataRD, axis=0)  # mean out of all ITIs

    t0, t1, t2 = 500, 2000, 10000

    # First t1 seconds
    axes[0].plot(dataAC_mean[t0:t1, 0], label="Fx")
    axes[0].plot(dataAC_mean[t0:t1, 1], label="Fy")
    plt.setp(
        axes[0],
        xticks=np.arange(0, t1 - t0 + 0.1, 500),
        xticklabels=np.arange(t0 / 1000, t1 / 1000 + 0.1, 0.5),
    )

    # From t1 to t2 seconds
    axes[1].plot(dataAC_mean[t1:t2, 0])
    axes[1].plot(dataAC_mean[t1:t2, 1])
    plt.setp(
        axes[1],
        xticks=np.arange(0, t2 - t1 + 0.1, 1000),
        xticklabels=np.arange(t1 / 1000, t2 / 1000 + 0.1, 1),
    )

    fig.suptitle("Autocorrelation of movements in Fx and Fy during ITI")
    axes[0].legend(frameon=False, fontsize=8, loc="upper right")

    for ax in axes:
        ax.set_xlabel("time")

    return axes


"""
 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
       ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""


def plot_sessions_overview(LogDfs, paths, task_name, animal_id, axes=None):
    "Plots trials performed together with every trial outcome plus sucess rate and weight across sessions"

    if axes is None:
        fig, axes = plt.subplots(ncols=2, sharex=True, figsize=(9, 4))

    trials_performed = []
    trials_correct = []
    trials_incorrect = []
    trials_missed = []
    trials_premature = []
    weight = []
    date = []

    # Obtaining number of trials of X
    for LogDf, path in zip(LogDfs, paths):
        # Correct date format
        folder_name = os.path.basename(path)
        complete_date = folder_name.split("_")[0]
        month = calendar.month_abbr[int(complete_date.split("-")[1])]
        day = complete_date.split("-")[2]
        date.append(month + "-" + day)

        # Total time
        session_dur = round(
            (LogDf["t"].iat[-1] - LogDf["t"].iat[0]) / 60000
        )  # convert to min

        # Total number of trials performed
        event_times = bhv.get_events_from_name(LogDf, "TRIAL_ENTRY_STATE")
        trials_performed.append(len(event_times) / session_dur)

        # Missed trials
        missed_choiceDf = bhv.get_events_from_name(LogDf, "CHOICE_MISSED_EVENT")
        trials_missed.append(len(missed_choiceDf) / session_dur)

        # Premature trials
        try:
            premature_choiceDf = bhv.get_events_from_name(
                LogDf, "PREMATURE_CHOICE_EVENT"
            )
            trials_premature.append(len(premature_choiceDf) / session_dur)
        except:
            trials_premature.append(None)

        # Correct trials
        correct_choiceDf = bhv.get_events_from_name(LogDf, "CHOICE_CORRECT_EVENT")
        trials_correct.append(len(correct_choiceDf) / session_dur)

        # Incorrect trials
        incorrect_choiceDf = bhv.get_events_from_name(LogDf, "CHOICE_INCORRECT_EVENT")
        trials_incorrect.append(len(incorrect_choiceDf) / session_dur)

        # hack workaround for learn_to_push_alternate
        if not trials_correct and not trials_incorrect:
            trials_correct = bhv.get_events_from_name(LogDf, "REWARD_AVAILABLE_EVENT")
            trials_incorrect = trials_performed - trials_missed - trials_correct

        # Weight
        try:
            animal_meta = pd.read_csv(path.joinpath("animal_meta.csv"))
            weight.append(
                round(
                    float(animal_meta.at[6, "value"])
                    / float(animal_meta.at[4, "value"]),
                    2,
                )
            )
        except:
            weight.append(None)

    sucess_rate = np.multiply(np.divide(trials_correct, trials_performed), 100)

    # Subplot 1
    axes[0].plot(trials_performed, color="blue", label="Performed")
    axes[0].plot(trials_correct, color="green", label="Correct")
    axes[0].plot(trials_incorrect, color="red", label="Incorrect")
    axes[0].plot(trials_missed, color="black", label="Missed")
    axes[0].plot(trials_premature, color="pink", label="Premature")

    axes[0].set_ylabel("Trial count per minute")
    axes[0].set_xlabel("Session number")
    axes[0].legend(loc="upper left", frameon=False)

    fig.suptitle("Sessions overview in " + task_name + " for mouse " + animal_id)
    plt.setp(axes[0], xticks=np.arange(0, len(date), 1), xticklabels=date)
    plt.xticks(rotation=45)
    plt.setp(
        axes[0],
        yticks=np.arange(0, max(trials_performed), 1),
        yticklabels=np.arange(0, max(trials_performed), 1),
    )

    # Two sided axes Subplot 2
    axes[1].plot(sucess_rate, color="green", label="Sucess rate")
    axes[1].legend(loc="upper left", frameon=False)
    axes[1].set_ylabel("a.u. (%)")
    plt.setp(axes[1], yticks=np.arange(0, 100, 10), yticklabels=np.arange(0, 100, 10))

    weight = np.multiply(weight, 100)
    twin_ax = axes[1].twinx()
    twin_ax.plot(weight, color="gray")
    twin_ax.set_ylabel("Normalized Weight to max (%)", color="gray")
    plt.setp(
        twin_ax, yticks=np.arange(75, 100 + 1, 5), yticklabels=np.arange(75, 100 + 1, 5)
    )

    fig.autofmt_xdate()
    plt.show()

    return axes


def rew_collected_across_sessions(LogDfs, axes=None):
    if axes is None:
        fig, axes = plt.subplots(figsize=(4, 3))

    reward_collect_ratio = []
    for LogDf in LogDfs:
        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

        TrialDfs = []

        for i, row in TrialSpans.iterrows():
            TrialDfs.append(bhv.time_slice(LogDf, row["t_on"], row["t_off"]))

        rew_collected = len(LogDf[LogDf["name"] == "REWARD_COLLECTED_EVENT"])
        rew_available_non_omitted = len(
            LogDf[LogDf["name"] == "REWARD_AVAILABLE_EVENT"]
        ) - len(LogDf[LogDf["name"] == "REWARD_OMITTED_EVENT"])

        reward_collect_ratio = np.append(
            reward_collect_ratio, rew_collected / rew_available_non_omitted
        )

    axes.plot(np.arange(len(reward_collect_ratio)), reward_collect_ratio)
    axes.set_ylabel("Ratio")
    axes.set_xlabel("Session number")
    axes.set_title("Reward collected ratio across sessions")
    axes.set_ylim([0, 1])
    axes.set_xlim([0, len(reward_collect_ratio)])
    plt.setp(
        axes,
        xticks=np.arange(0, len(reward_collect_ratio)),
        xticklabels=np.arange(0, len(reward_collect_ratio)),
    )
    axes.axhline(0.9, color="k", alpha=0.5, linestyle=":")

    fig.tight_layout()

    return axes


def x_y_tresh_bias_across_sessions(LogDfs, paths, axes=None):
    if axes is None:
        fig, axes = plt.subplots(figsize=(5, 3))

    x_thresh, y_thresh, bias, date = [], [], [], []
    for LogDf, path in zip(LogDfs, paths):
        # Correct date format
        folder_name = os.path.basename(path)
        complete_date = folder_name.split("_")[0]
        month = calendar.month_abbr[int(complete_date.split("-")[1])]
        day = complete_date.split("-")[2]
        date.append(month + "-" + day)

        x_thresh = np.append(
            x_thresh, np.mean(LogDf[LogDf["var"] == "X_thresh"].value.values)
        )
        y_thresh = np.append(
            y_thresh, np.mean(LogDf[LogDf["var"] == "Y_thresh"].value.values)
        )

        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

        TrialDfs = []
        for i, row in tqdm(TrialSpans.iterrows(), position=0, leave=True):
            TrialDfs.append(bhv.time_slice(LogDf, row["t_on"], row["t_off"]))

        metrics = (bhv.get_start, bhv.get_stop, bhv.get_bias)
        SessionDf = bhv.parse_trials(TrialDfs, metrics)

        bias = np.append(bias, SessionDf["bias"].values[-1])  # last bias value

    axes.plot(np.arange(len(LogDfs)), x_thresh, color="C0", label="X thresh")
    axes.plot(np.arange(len(LogDfs)), y_thresh, color="m", label="Y thresh")

    axes.set_ylim([1000, 3000])
    axes.set_ylabel("Force (a.u.)")
    axes.set_title("Mean X/Y thresh forces and bias across sessions")
    axes.legend(frameon=False)

    plt.setp(axes, xticks=np.arange(0, len(date), 1), xticklabels=date)
    plt.xticks(rotation=-45)

    if bias.any():
        twin_ax = axes.twinx()
        twin_ax.plot(bias, color="g", alpha=0.5)
        twin_ax.set_ylabel("Bias", color="g")
        twin_ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
        twin_ax.set_yticklabels(
            ["left (0%)", "25%", "center (50%)", "75%", "right (100%)"]
        )

    fig.tight_layout()

    return axes


def choice_rt_across_sessions(
    LogDfs, bin_width, choice_interval, percentile, animal_id, axes=None
):
    if axes == None:
        fig, axes = plt.subplots(figsize=(5, 3))

    colors = sns.color_palette(palette="turbo", n_colors=len(LogDfs))

    for i, LogDf in enumerate(LogDfs):
        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

        TrialDfs = []
        for j, row in TrialSpans.iterrows():
            TrialDfs.append(bhv.time_slice(LogDf, row["t_on"], row["t_off"]))

        choice_rt = np.empty(0)

        for TrialDf in TrialDfs:
            choice_rt = np.append(choice_rt, bhv.choice_RT(TrialDf).values)

        # includes front and back pushes, eliminates nans due to missed trials
        clean_choice_rt = [x for x in choice_rt if not pd.isnull(x)]

        no_bins = round(choice_interval / bin_width)

        counts, bins = np.histogram(
            clean_choice_rt, bins=no_bins, density=True, range=(-250, choice_interval)
        )
        axes.step(
            bins[1:],
            counts,
            color=colors[i],
            zorder=1 * i,
            alpha=0.75,
            label="day " + str(i + 1),
        )

        axes.axvline(
            np.percentile(clean_choice_rt, percentile), color=colors[i], alpha=0.5
        )

    plt.legend(frameon=False)
    axes.set_ylabel("Prob (%)")
    axes.set_xlabel("Time (s)")
    fig.suptitle(
        "Choice RT distribution with"
        + str(percentile)
        + "th percentile"
        + "\n"
        + str(animal_id),
        fontsize="small",
    )


def force_2D_contour_across_sessions(
    paths, thresh, task_name, animal_id, trials_only=False, axes=None
):
    if axes == None:
        fig, axes = plt.subplots()

    # Getting all the forces across sessions
    Fx, Fy = np.empty(0), np.empty(0)
    for path in tqdm(paths, position=0, leave=True):
        if not os.path.isfile(path / "loadcell_data.csv"):
            log_path = path.joinpath("arduino_log.txt")

            LoadCellDf, harp_sync = bhv.parse_harp_csv(
                path / "bonsai_harp_log.csv", save=True
            )
            arduino_sync = bhv.get_arduino_sync(
                log_path, sync_event_name="TRIAL_ENTRY_EVENT"
            )

            t_harp = pd.read_csv(path / "harp_sync.csv")["t"].values
            t_arduino = pd.read_csv(path / "arduino_sync.csv")["t"].values

            if t_harp.shape != t_arduino.shape:
                t_arduino, t_harp = bhv.cut_timestamps(t_arduino, t_harp, verbose=True)

            m, b = bhv.sync_clocks(t_harp, t_arduino, log_path)
        else:
            LoadCellDf = pd.read_csv(path / "loadcell_data.csv")

        LogDf = pd.read_csv(path / "LogDf.csv")
        LogDf = LogDf.loc[LogDf["t"] < LoadCellDf.iloc[-1]["t"]]

        # median correction
        samples = 10000  # 10s buffer: harp samples at 1khz, arduino at 100hz, LC controller has 1000 samples in buffer
        LoadCellDf["x"] = LoadCellDf["x"] - LoadCellDf["x"].rolling(samples).median()
        LoadCellDf["y"] = LoadCellDf["y"] - LoadCellDf["y"].rolling(samples).median()

        if trials_only == True:
            TrialSpans = bhv.get_spans_from_names(
                LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE"
            )

            for i, row in TrialSpans.iterrows():
                F = bhv.time_slice(LoadCellDf, row["t_on"], row["t_off"])
                Fx = np.concatenate((Fx, F["x"].values))
                Fy = np.concatenate((Fy, F["y"].values))
        else:
            Fx = np.concatenate((Fx, LoadCellDf["x"].values))
            Fy = np.concatenate((Fy, LoadCellDf["y"].values))

    Fx = Fx[~np.isnan(Fx)]
    Fy = Fy[~np.isnan(Fy)]

    # control number of samples such that KDE does not blow up
    max_samples = 50000
    if Fx.shape[0] > max_samples:
        downsample_factor = round(Fx.shape[0] / max_samples)

    Fs_raw = np.dstack((Fx, Fy))
    Fs_reshaped = Fs_raw.reshape(
        Fs_raw.shape[1:]
    ).T  # get rid of first useless dim and put Fx/Fy there
    Fs = Fs_reshaped[
        :, 0:-1:downsample_factor
    ]  # KDE can't handle more than hundread thousand points

    # 2d - kde
    kde = sp.stats.gaussian_kde(Fs)
    v = sp.linspace(-10000, 10000, 100)
    X, Y = sp.meshgrid(v, v)
    pos = np.vstack([X.ravel(), Y.ravel()])
    P = kde(pos).reshape(X.shape)  # Probability matrix estimated by KDE

    dv = sp.diff(v)[-1]  # grid_length
    sp.sum(P) * dv**2  # is 1

    # scatter
    axes.plot(Fs[0, :], Fs[1, :], ".", alpha=0.1, color="k", markersize=2)

    # heatmap
    vmin, vmax = sp.percentile(P, (0, 99))
    axes.imshow(
        P,
        origin="lower",
        extent=(v[0], v[-1], v[0], v[-1]),
        vmin=vmin,
        vmax=vmax,
        cmap="RdPu",
    )
    th = 10000
    axes.set_xlim([-th, th])
    axes.set_ylim([-th, th])

    # cross
    kwargs = dict(linestyle=":", color="k", lw=0.5, alpha=0.5)
    axes.axhline(0, **kwargs)
    axes.axvline(0, **kwargs)
    kwargs["lw"] = 1
    kwargs["color"] = "red"

    # where 90% of their activity lies in both L/R and UP/BOT
    for val in sp.percentile(Fs[0, :], (5, 95)):
        axes.axvline(val, **kwargs)
    for val in sp.percentile(Fs[1, :], (5, 95)):
        axes.axhline(val, **kwargs)

    # contour
    Pn = P * dv**2  # Prob times area of each grid square
    vs = sp.linspace(0, Pn.max(), 100)  # 100 slices of probabilities
    k = sp.array(
        [sp.sum(Pn[Pn < v]) for v in vs]
    )  # percentile for each slice (cumulative)
    quartiles = [0.25, 0.5, 0.75]
    lvl = [
        vs[sp.argmax(k > q)] for q in quartiles
    ]  # Slice the point at which CDF reaches 50%
    levels = sp.array(lvl)
    axes.contour(
        X,
        Y,
        Pn,
        levels=levels,
        origin="lower",
        extent=(v[0], v[-1], v[0], v[-1]),
        cmap="Reds_r",
        zorder=10,
        linewidths=1,
    )

    # formatting
    axes.set(xlabel="Left/Right axis", ylabel="Front/Back axis")
    plt.title(
        "2D Histogram and contour levels of forces "
        + "\n"
        + "across sessions - "
        + "\n"
        + str(animal_id)
    )
    fig.tight_layout()

    # Funky way to get percentiles value on the lines
    # fmt = {}
    # strs = [' ' + str(p) + '% ' for p in perc]
    # for l, s in zip(CS.levels, strs):
    #     fmt[l] = s
    # axes.clabel(CS, CS.levels, inline=True, fmt=fmt, fontsize=8)

    return axes
