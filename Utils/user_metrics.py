import pandas as pd
from Utils.metrics_partial import *
from functools import partial

def get_start(TrialDf):
    return pd.Series(TrialDf.iloc[0]['t'], name='t_on')

def get_stop(TrialDf):
    return pd.Series(TrialDf.iloc[-1]['t'], name='t_off')

get_choice_rt = partial(get_time_between, event_a="CHOICE_STATE", event_b="CHOICE_EVENT", name="choice_rt")