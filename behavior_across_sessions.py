import sys,os
from time import time
import pickle

# Viz libraries
import scipy as sp
import numpy as np
import pandas as pd

# Neuro libraries
import neo
import elephant as ele
import quantities as pq

import sys
sys.path.append('C:/Users/Casa/Desktop/Paco/Champalimaud/task_control')

# Defining path to TaskControl Functions
import behavior_analysis_utils as bhv
import functions

## S1 - Loading and parsing data ## 

# Obtaining events (log) path for single animal and single session
from pathlib import Path

log_path = Path("C:/Users/Casa/Desktop/Paco/Champalimaud/behavior_data/JP2078/2020-02-11_13-57-16_lick_for_reward_w_surpression/arduino_log.txt")
code_map_path = log_path.parent.joinpath("lick_for_reward_w_surpression","Arduino","src","event_codes.h")

# Turns pandas codemap into a fict
CodesDf = bhv.parse_code_map(code_map_path)
code_map = dict(zip(CodesDf['code'],CodesDf['name']))
Data = bhv.parse_arduino_log(log_path, code_map)

# Parses names of events or "spans" irrespective of task
span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

# Obtain every lick and event together with timestamps
Spans = bhv.log2Spans(Data, span_names)
Events = bhv.log2Events(Data, event_names)

## S2 - Pre-processing ##

# filter unrealistic licks
bad_licks = sp.logical_or(Spans['LICK']['dt'] < 20, Spans['LICK']['dt'] > 100)
Spans['LICK'] = Spans['LICK'].loc[~bad_licks]

# add lick_event
Lick_Event = pd.DataFrame(sp.stack([['NA']*Spans['LICK'].shape[0], Spans['LICK']['t_on'].values, ['LICK_EVENT']*Spans['LICK'].shape[0]]).T, columns=['code','t','name'])
Lick_Event['t'] = Lick_Event['t'].astype('float')
Data = Data.append(Lick_Event)
Data.sort_values('t')

event_names.append("LICK")
Events['LICK'] = bhv.log2Event(Data,'LICK')

Spans.pop("LICK")
span_names.remove("LICK")

## S3 - Visualization ## 

## S4 -  ##
