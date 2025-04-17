import pandas as pd
from functools import partial
from Utils.metrics_partial import get_time_between


def get_start(TrialDf):
    return pd.Series(TrialDf.iloc[0]["t"], name="t_on")


def get_stop(TrialDf):
    return pd.Series(TrialDf.iloc[-1]["t"], name="t_off")


get_choice_rt = partial(
    get_time_between, event_a="CHOICE_STATE", event_b="CHOICE_EVENT", name="choice_rt"
)
