import pandas as pd
import numpy as np
from Utils.behavior_analysis_utils import event_slice
from functools import partial

"""
new approach: building specific metrics usting functools.partial
BREAKING DOWNWARD COMPATIBILITY
pattern: checks are implemented by the primities
"""

"""
 
 ########  ########  #### ##     ## #### ######## #### ##     ## ########  ######  
 ##     ## ##     ##  ##  ###   ###  ##     ##     ##  ##     ## ##       ##    ## 
 ##     ## ##     ##  ##  #### ####  ##     ##     ##  ##     ## ##       ##       
 ########  ########   ##  ## ### ##  ##     ##     ##  ##     ## ######    ######  
 ##        ##   ##    ##  ##     ##  ##     ##     ##   ##   ##  ##             ## 
 ##        ##    ##   ##  ##     ##  ##     ##     ##    ## ##   ##       ##    ## 
 ##        ##     ## #### ##     ## ####    ##    ####    ###    ########  ######  
 
"""


def has_event(TrialDf: pd.DataFrame, event_name: str = None, rename: str = None):
    if event_name in TrialDf["name"].values:
        var = True
    else:
        var = False
    name = rename if rename is not None else "has_%s" % event_name
    return pd.Series(var, name=name)


def has_var(TrialDf: pd.DataFrame, var_name: str = None, rename: str = None):
    # returns True or False if var_name is in TrialDf
    if var_name in TrialDf["var"].values:
        var = True
    else:
        var = False
    name = rename if rename is not None else "has_%s" % var_name
    return pd.Series(var, name=name)


def get_var(
    TrialDf: pd.DataFrame, var_name: str, dtype: str = None, rename: str = None
):
    if has_var(TrialDf, var_name)[0]:
        Df = TrialDf.groupby("var").get_group(var_name)
        if dtype is not None:
            var = Df.iloc[0]["value"].astype(dtype)
        else:
            var = Df.iloc[0]["value"]
    else:
        var = np.NaN

    name = rename if rename is not None else var_name
    return pd.Series(var, name=name)


def get_time_between(
    TrialDf: pd.DataFrame, event_a: str, event_b: str, name: str
) -> pd.Series:
    if has_event(TrialDf, event_a)[0] and has_event(TrialDf, event_b)[0]:
        Df = event_slice(TrialDf, event_a, event_b)
        var = Df.iloc[-1]["t"] - Df.iloc[0]["t"]
    else:
        var = np.NaN
    return pd.Series(var, name=name)


def var_is(
    TrialDf: pd.DataFrame, var_name: str, comp="is_greater", value=0, rename: str = None
):
    var = get_var(TrialDf, var_name)[0]
    if not pd.isna(var):
        if comp == "is_greater":
            var = True if var > value else False
        if comp == "is_smaller":
            var = True if var < value else False
        if comp == "is_equal":
            var = True if var == value else False
    else:
        var = np.NaN
    name = rename if rename is not None else "%s_%s" % (var_name, comp)
    return pd.Series(var, name=name)


is_long = partial(var_is, var_name="this_LED_ON_dur", value=700, rename="is_long")
init_time = partial(
    get_time_between,
    event_a="TRIAL_AVAILABLE_STATE",
    event_b="DELAY_STATE",
    name="init_time",
)
get_r = partial(get_var, var_name="r", rename="r")
r_is_greater = partial(
    var_is, var_name="r", comp="is_greater", value=500, rename="r_greater"
)
"""
 
  ######  ##     ##  #######  ####  ######  ######## 
 ##    ## ##     ## ##     ##  ##  ##    ## ##       
 ##       ##     ## ##     ##  ##  ##       ##       
 ##       ######### ##     ##  ##  ##       ######   
 ##       ##     ## ##     ##  ##  ##       ##       
 ##    ## ##     ## ##     ##  ##  ##    ## ##       
  ######  ##     ##  #######  ####  ######  ######## 
 
"""
has_choice = partial(has_event, event_name="CHOICE_EVENT", rename="has_choice")
# def has_choice(TrialDf):
#     var_name = 'has_choice'

#     if "CHOICE_EVENT" in TrialDf['name'].values:
#         var = True
#     else:
#         var = False

#     return pd.Series(var, name=var_name)

has_anticipatory_reach = partial(
    has_event, event_name="ANTICIPATORY_REACH_EVENT", rename="has_anticip_reach"
)
# def has_anticipatory_reach(TrialDf):
#     var_name = 'has_anticip_reach'
#     if "ANTICIPATORY_REACH_EVENT" in TrialDf['name'].values:
#         var = True
#     else:
#         var = False

#     return pd.Series(var, name=var_name)

has_premature_choice = partial(
    has_event, event_name="PREMATURE_CHOICE_EVENT", rename="has_premature_choice"
)
# def has_premature_choice(TrialDf):
#     var_name = "has_premature_choice"
#     if "PREMATURE_CHOICE_EVENT" in TrialDf['name'].values:
#         var = True
#     else:
#         var = False

#     return pd.Series(var, name=var_name)

has_reward_collected = partial(
    has_event, event_name="REWARD_COLLECTED_EVENT", rename="has_reward_collected"
)
# def has_reward_collected(TrialDf):
#     var_name = "has_reward_collected"
#     if "REWARD_COLLECTED_EVENT" in TrialDf['name'].values:
#         var = True
#     else:
#         var = False

#     return pd.Series(var, name=var_name)
has_autodelivered_reward = partial(
    has_event,
    event_name="REWARD_AUTODELIVERED_EVENT",
    rename="has_autodelivered_reward",
)
# def has_autodelivered_reward(TrialDf):
#     var_name = "has_autodelivered_reward"
#     if "REWARD_AUTODELIVERED_EVENT" in TrialDf['name'].values:
#         var = True
#     else:
#         var = False

#     return pd.Series(var, name=var_name)


# has_premature_reach = partial(has_var, var_name=)
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


# is not the same, but a solution
# get_interval_category = partial(var_is, var_name="interval_category", comp='is_greater', value=1500, rename='is_long')
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


get_interval = partial(get_var, name="this_interval")
# def get_interval(TrialDf):
#     var_name = "this_interval"
#     try:
#         Df = TrialDf.groupby('var').get_group(var_name)
#         var = Df.iloc[0]['value']
#     except KeyError:
#         var = np.NaN

#     return pd.Series(var, name=var_name)


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


def get_trial_dur(TrialDf):
    dt = TrialDf.iloc[-1]["t"] - TrialDf.iloc[0]["t"]
    return pd.Series(dt, name="dt")


get_init_rt = partial(
    get_time_between,
    event_a="TRIAL_AVAILABLE_EVENT",
    event_b="TRIAL_ENTRY_EVENT",
    name="init_rt",
)
# def get_init_rt(TrialDf):
#     var_name = "init_rt"
#     try:
#         Df = event_slice(TrialDf, "TRIAL_AVAILABLE_EVENT", "TRIAL_ENTRY_EVENT")
#         var = Df.iloc[-1]['t'] - Df.iloc[0]['t']
#     except IndexError:
#         var = np.NaN
#     return pd.Series(var, name=var_name)

get_premature_rt = partial(
    get_time_between,
    event_a="PRESENT_INTERVAL_STATE",
    event_b="PREMATURE_CHOICE_EVENT",
    name="premature_rt",
)
# def get_premature_rt(TrialDf):
#     var_name = "premature_rt"
#     try:
#         Df = event_slice(TrialDf, "PRESENT_INTERVAL_STATE", "PREMATURE_CHOICE_EVENT")
#         var = Df.iloc[-1]['t'] - Df.iloc[0]['t']
#     except IndexError:
#         var = np.NaN
#     return pd.Series(var, name=var_name)

get_choice_rt = partial(
    get_time_between, event_a="CHOICE_STATE", event_b="CHOICE_EVENT", name="choice_rt"
)
# def get_choice_rt(TrialDf):
#     var_name = "choice_rt"
#     try:
#         Df = event_slice(TrialDf, "CHOICE_STATE", "CHOICE_EVENT")
#         var = Df.iloc[-1]['t'] - Df.iloc[0]['t']
#     except IndexError:
#         var = np.NaN
#     return pd.Series(var, name=var_name)


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


get_trial_type = partial(get_var, var_name="this_trial_type")
# def get_trial_type(TrialDf):
#     var_name = "this_trial_type"
#     try:
#         Df = TrialDf.groupby('var').get_group(var_name)
#         var = Df.iloc[0]['value']
#     except KeyError:
#         var = np.NaN

#     return pd.Series(var, name=var_name)

get_delay = partial(get_var, var_name="this_delay")
# def get_delay(TrialDf):
#     var_name = "this_delay"
#     try:
#         Df = TrialDf.groupby('var').get_group(var_name)
#         var = Df.iloc[0]['value']
#     except KeyError:
#         var = np.NaN

#     return pd.Series(var, name=var_name)

get_reward_magnitude = partial(get_var, var_name="reward_magnitude")
# def get_reward_magnitude(TrialDf):
#     var_name = "reward_magnitude"
#     try:
#         Df = TrialDf.groupby('var').get_group(var_name)
#         var = Df.iloc[0]['value']
#     except KeyError:
#         var = np.NaN

#     return pd.Series(var, name=var_name)

get_reward_time = partial(
    get_time_between,
)


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
