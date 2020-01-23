%matplotlib qt5
import matplotlib.pyplot as plt
import scipy as sp
import seaborn as sns
import pandas as pd
# import neo
# import quantities as pq
from pathlib import Path
import sys
import time as Time
from functions import parse_code_map

def parse_arduino_log(log_path, code_map=None):
    """ create a DataFrame representation of an arduino log. If a code map is passed 
    a corresponding decoded column will be created """

    with open(log_path,'r') as fH:
        lines = fH.readlines()

    valid_lines = [line.strip().split('\t') for line in lines if '\t' in line]
    Data = pd.DataFrame(valid_lines,columns=['code','t'])
    Data['t'] = Data['t'].astype('float')

    if code_map is not None:
        Data['name'] = [code_map[code_map['code'] == v]['name'].values[0] for v in Data['code'].values]

    return Data

def log2Span(Data,span_name):
    on_times = Data.groupby('name').get_group(span_name+'_ON')['t'].values.astype('float')
    off_times = Data.groupby('name').get_group(span_name+'_OFF')['t'].values.astype('float')
    if on_times.shape != off_times.shape:
        print("unequal number of ON and OFF events for: ", span_name)
    dt = off_times - on_times
    Df = pd.DataFrame(sp.stack([on_times,off_times,dt],axis=1),columns=['t_on','t_off','dt'])
    return Df

def log2Spans(Data,span_names):
    Spans = {}
    for span_name in span_names:
        try:
            Spans[span_name] = log2Span(Data,span_name)
        except KeyError:
            print("span not present in log but in code map: ",span_name)
    return Spans

def log2Event(Data,event_name):
    times = Data.groupby('name').get_group(event_name+'_EVENT')['t'].values.astype('float')
    Df = pd.DataFrame(times,columns=['t'])
    return Df

def log2Events(Data,event_names):
    Events = {}
    for event_name in event_names:
        try:
            Events[event_name] = log2Event(Data,event_name)
        except KeyError:
            print("event not present in log but in code map: ", event_name)
    return Events


""" make TrialsDf """
def make_TrialsDf(Data,trial_entry=None,trial_exit_succ=None,trial_exit_unsucc=None):
    TrialsDf = pd.DataFrame(Data.groupby('name').get_group(trial_entry)['t'])
    TrialsDf.columns = ['t_on']
    try:
        Hit = pd.DataFrame(Data.groupby('name').get_group(trial_exit_succ)['t'])
        Hit['outcome'] = 'succ'
    except KeyError:
        Hit = pd.DataFrame()

    try:
        Miss = pd.DataFrame(Data.groupby('name').get_group(trial_exit_unsucc)['t'])
        Miss['outcome'] = 'unsucc'
    except KeyError:
        Miss = pd.DataFrame()

    AllEndings = pd.concat([Hit,Miss],axis=0)
    AllEndings = AllEndings.sort_values('t')
    AllEndings.columns = ['t_off','outcome']

    # removing last incompleted
    if TrialsDf.shape[0] > AllEndings.shape[0]:
        TrialsDf = TrialsDf[:-1]

    TrialsDf = pd.concat([TrialsDf.reset_index(drop=True),AllEndings.reset_index(drop=True)],axis=1)
    TrialsDf['dt'] = TrialsDf['t_off'] - TrialsDf['t_on']
    
    return TrialsDf

""" a Df based timeslicer """
def time_slice(Df, t_min, t_max, col='t_on'):
    """ slices the DataFrame on the column """
    return Df.loc[sp.logical_and(Df[col] > t_min, Df[col] < t_max)]




# PATH
# upstairs
# log_path = Path("/home/georg/git_tmp/TaskControl/Animals/123/2020-01-22_11-53-34_lick_for_reward_w_surpression/arduino_log.txt")
# code_map_path = Path("/home/georg/git_tmp/TaskControl/Tasks/lick_for_reward_w_surpression/Arduino/src/event_codes.h")

# downstairs
log_path = Path(r'D:\TaskControl\Animals\123\2020-01-22_11-53-34_lick_for_reward_w_surpression\arduino_log.txt')
code_map_path = Path(r'D:\TaskControl\Animals\123\2020-01-22_11-53-34_lick_for_reward_w_surpression\lick_for_reward_w_surpression\Arduino\src\event_codes.h')

Code_Map = parse_code_map(code_map_path)
Data = parse_arduino_log(log_path, Code_Map)

# the names of the things present in the log
span_names = [name.split('_ON')[0] for name in Code_Map['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in Code_Map['name'] if name.endswith('_EVENT')]
state_names = [name.split('_STATE')[0] for name in Code_Map['name'] if name.endswith('_STATE')]

Spans = log2Spans(Data, span_names)
Events = log2Events(Data, event_names)

# definition of the bounding events
trial_entry = "TRIAL_ENTRY_EVENT"
trial_exit_succ = "TRIAL_COMPLETED_EVENT"
trial_exit_unsucc = "TRIAL_ABORTED_EVENT"

TrialsDf = make_TrialsDf(Data,trial_entry=trial_entry,
                              trial_exit_succ=trial_exit_succ,
                              trial_exit_unsucc=trial_exit_unsucc)

# %%
fig, axes = plt.subplots(figsize=(7,9))

colors = sns.color_palette('deep',n_colors=len(event_names)+len(span_names))
cdict = dict(zip(event_names+span_names,colors))

pre, post = (-1000,1000)

for i, row in TrialsDf.iterrows():
    if row['outcome'] == 'succ':
        col = 'black'
    else:
        col = 'gray'
    axes.plot([0,row['dt']],[i,i],lw=3,color=col)
    axes.axhline(i,linestyle=':',color='black',alpha=0.5,lw=1)

    # adding events as ticks
    for event_name, Df in Events.items():
        times = time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t')['t']
        times = times - row['t_on'] # relative to trial onset

        for t in times:
            axes.plot([t,t],[i-0.5,i+0.5],lw=3,color=cdict[event_name])

    # adding spans
    for span_name, Df in Spans.items():
        Df_sliced = time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t_on')
        for j, row_s in Df_sliced.iterrows():
            t = row_s['t_on'] - row['t_on']
            dur = row_s['dt']
            rect = plt.Rectangle((t,i-0.5), dur, 1,
                                 facecolor=cdict[span_name])
            axes.add_patch(rect)
        
for key in cdict.keys():
    axes.plot([0],[0],color=cdict[key],label=key,lw=4)
axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
axes.invert_yaxis()
axes.set_xlabel('time (ms)')
axes.set_ylabel('trials')
fig.tight_layout()