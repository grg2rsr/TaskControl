import pandas as pd
import numpy as np
from Utils.behavior_analysis_utils import event_slice

"""
 
  ######  ##     ##  #######  ####  ######  ######## 
 ##    ## ##     ## ##     ##  ##  ##    ## ##       
 ##       ##     ## ##     ##  ##  ##       ##       
 ##       ######### ##     ##  ##  ##       ######   
 ##       ##     ## ##     ##  ##  ##       ##       
 ##    ## ##     ## ##     ##  ##  ##    ## ##       
  ######  ##     ##  #######  ####  ######  ######## 
 
"""


def has_choice(TrialDf):
    var_name = "has_choice"

    if "CHOICE_EVENT" in TrialDf["name"].values:
        var = True
    else:
        var = False

    return pd.Series(var, name=var_name)


def has_anticipatory_reach(TrialDf):
    var_name = "has_anticip_reach"
    if "ANTICIPATORY_REACH_EVENT" in TrialDf["name"].values:
        var = True
    else:
        var = False

    return pd.Series(var, name=var_name)


def has_premature_choice(TrialDf):
    var_name = "has_premature_choice"
    if "PREMATURE_CHOICE_EVENT" in TrialDf["name"].values:
        var = True
    else:
        var = False

    return pd.Series(var, name=var_name)


def has_reward_collected(TrialDf):
    var_name = "has_reward_collected"
    if "REWARD_COLLECTED_EVENT" in TrialDf["name"].values:
        var = True
    else:
        var = False

    return pd.Series(var, name=var_name)


def has_autodelivered_reward(TrialDf):
    var_name = "has_autodelivered_reward"
    if "REWARD_AUTODELIVERED_EVENT" in TrialDf["name"].values:
        var = True
    else:
        var = False

    return pd.Series(var, name=var_name)


def has_premature_reach(TrialDf):
    var_name = "has_premature_reach"
    try:
        Df = event_slice(TrialDf, "PRESENT_INTERVAL_STATE", "CHOICE_STATE")
        events = Df["name"].values
        if "REACH_LEFT_ON" in events or "REACH_RIGHT_ON" in events:
            var = True
        else:
            var = False
    except KeyError:
        # this should take care of incomplete trials
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_chosen_side(TrialDf):
    var_name = "chosen_side"

    if "CHOICE_EVENT" in TrialDf["name"].values:
        if "CHOICE_LEFT_EVENT" in TrialDf["name"].values:
            var = "left"
        elif "CHOICE_RIGHT_EVENT" in TrialDf["name"].values:
            var = "right"
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_chosen_interval(TrialDf):
    var_name = "chosen_interval"

    if "CHOICE_EVENT" in TrialDf["name"].values:
        if "CHOICE_SHORT_EVENT" in TrialDf["name"].values:
            var = "short"
        elif "CHOICE_LONG_EVENT" in TrialDf["name"].values:
            var = "long"
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_correct_side(TrialDf):
    var_name = "correct_side"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        val = Df.iloc[0]["value"]
        if val == 4:
            var = "left"
        if val == 6:
            var = "right"

    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_interval_category(TrialDf):
    var_name = "interval_category"
    try:
        interval = get_interval(TrialDf).values[0]
        if interval < 1500:
            var = "short"
        else:
            var = "long"

    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_interval(TrialDf):
    var_name = "this_interval"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"]
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_outcome(TrialDf):
    var_name = "outcome"

    if "PREMATURE_CHOICE_EVENT" in TrialDf["name"].values:
        var = "premature"
    elif "CHOICE_CORRECT_EVENT" in TrialDf["name"].values:
        var = "correct"
    elif "CHOICE_INCORRECT_EVENT" in TrialDf["name"].values:
        var = "incorrect"
    elif "CHOICE_MISSED_EVENT" in TrialDf["name"].values:
        var = "missed"
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_anticip_reach_outcome(TrialDf):
    var_name = "anticip_reach_outcome"
    var = np.nan

    sl = event_slice(TrialDf, "CHOICE_STATE", "REWARD_EVENT")

    events = sl["name"].values
    choice = None

    if "REACH_LEFT_ON" in events and "REACH_RIGHT_ON" in events:
        ix_l = sl[sl["name"] == "REACH_LEFT_ON"].index[0]
        ix_r = sl[sl["name"] == "REACH_RIGHT_ON"].index[0]
        if ix_l < ix_r:
            choice = "left"
        else:
            choice = "right"

    if "REACH_LEFT_ON" in events:
        ix = sl[sl["name"] == "REACH_LEFT_ON"].index[0]
        choice = "left"

    if "REACH_RIGHT_ON" in events:
        ix = sl[sl["name"] == "REACH_RIGHT_ON"].index[0]
        choice = "right"

    if choice is not None:
        # correct_side = SessionDf.loc[i]['correct_side']
        correct_side = get_correct_side(TrialDf).values[0]
        if correct_side == choice:
            var = "correct"
        else:
            var = "incorrect"

    return pd.Series(var, name=var_name)


"""
 
 ######## ########  ####    ###    ##          ######## ##    ## ########  ######## 
    ##    ##     ##  ##    ## ##   ##             ##     ##  ##  ##     ## ##       
    ##    ##     ##  ##   ##   ##  ##             ##      ####   ##     ## ##       
    ##    ########   ##  ##     ## ##             ##       ##    ########  ######   
    ##    ##   ##    ##  ######### ##             ##       ##    ##        ##       
    ##    ##    ##   ##  ##     ## ##             ##       ##    ##        ##       
    ##    ##     ## #### ##     ## ########       ##       ##    ##        ######## 
 
"""


def get_in_corr_loop(TrialDf):
    var_name = "in_corr_loop"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"].astype("bool")
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_timing_trial(TrialDf):
    var_name = "timing_trial"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"].astype("bool")
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_autodeliver_trial(TrialDf):
    var_name = "autodeliver_rewards"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"].astype("bool")
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


"""
 
 ######## #### ##     ## #### ##    ##  ######   
    ##     ##  ###   ###  ##  ###   ## ##    ##  
    ##     ##  #### ####  ##  ####  ## ##        
    ##     ##  ## ### ##  ##  ## ## ## ##   #### 
    ##     ##  ##     ##  ##  ##  #### ##    ##  
    ##     ##  ##     ##  ##  ##   ### ##    ##  
    ##    #### ##     ## #### ##    ##  ######   
 
"""


def get_start(TrialDf):
    return pd.Series(TrialDf.iloc[0]["t"], name="t_on")


def get_stop(TrialDf):
    return pd.Series(TrialDf.iloc[-1]["t"], name="t_off")


def get_init_rt(TrialDf):
    var_name = "init_rt"
    try:
        Df = event_slice(TrialDf, "TRIAL_AVAILABLE_EVENT", "TRIAL_ENTRY_EVENT")
        var = Df.iloc[-1]["t"] - Df.iloc[0]["t"]
    except IndexError:
        var = np.NaN
    return pd.Series(var, name=var_name)


def get_premature_rt(TrialDf):
    var_name = "premature_rt"
    try:
        Df = event_slice(TrialDf, "PRESENT_INTERVAL_STATE", "PREMATURE_CHOICE_EVENT")
        var = Df.iloc[-1]["t"] - Df.iloc[0]["t"]
    except IndexError:
        var = np.NaN
    return pd.Series(var, name=var_name)


def get_choice_rt(TrialDf):
    var_name = "choice_rt"
    try:
        Df = event_slice(TrialDf, "CHOICE_STATE", "CHOICE_EVENT")
        var = Df.iloc[-1]["t"] - Df.iloc[0]["t"]
    except IndexError:
        var = np.NaN
    return pd.Series(var, name=var_name)


def get_reward_collection_rt(TrialDf):
    var_name = "reward_collection_rt"
    side = get_correct_side(TrialDf).values[0]
    try:
        Df = event_slice(
            TrialDf, "REWARD_%s_VALVE_ON" % side.upper(), "REWARD_COLLECTED_EVENT"
        )
        var = Df.iloc[-1]["t"] - Df.iloc[0]["t"]
    except IndexError:
        var = np.NaN
    return pd.Series(var, name=var_name)

    """
    ######## ######## ##     ## ########     ##     ##    ###    ########   ######
       ##    ##       ###   ### ##     ##    ###   ###   ## ##   ##     ## ##    ##
       ##    ##       #### #### ##     ##    #### ####  ##   ##  ##     ## ##
       ##    ######   ## ### ## ########     ## ### ## ##     ## ########   ######
       ##    ##       ##     ## ##           ##     ## ######### ##              ##
       ##    ##       ##     ## ##           ##     ## ##     ## ##        ##    ##
       ##    ######## ##     ## ##           ##     ## ##     ## ##         ######
    """


def get_trial_type(TrialDf):
    var_name = "this_trial_type"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"]
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_delay(TrialDf):
    var_name = "this_delay"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"]
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_reward_magnitude(TrialDf):
    var_name = "reward_magnitude"
    try:
        Df = TrialDf.groupby("var").get_group(var_name)
        var = Df.iloc[0]["value"]
    except KeyError:
        var = np.NaN

    return pd.Series(var, name=var_name)


def get_reward_time(TrialDf):
    var_name = "reward_collection_time"
    # event = "REWARD_COLLECTED_EVENT"
    event = "REWARD_EVENT"
    if event in TrialDf["name"].values:
        try:
            Df = TrialDf.groupby("name").get_group(event)
            var = Df.iloc[0]["t"]
        except KeyError:
            var = np.NaN
    else:
        var = np.NaN

    return pd.Series(var, name=var_name)
