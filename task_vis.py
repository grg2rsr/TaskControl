%matplotlib qt5
import matplotlib.pyplot as plt
import scipy as sp
import seaborn as sns
import pandas as pd
import neo
import quantities as pq
from pathlib import Path
import sys
import time as Time

t1 = Time.time()

path = Path("/home/georg/git_tmp/TaskControl/Animals/123/2020-01-22_11-53-34_lick_for_reward_w_surpression/arduino_log.txt")
code_map = Path("/home/georg/git_tmp/TaskControl/Tasks/lick_for_reward_w_surpression/Arduino/src/event_codes.h")

with open(path,'r') as fH:
    lines = fH.readlines()

valid_lines = [line.strip().split('\t') for line in lines if '\t' in line]
Data = pd.DataFrame(valid_lines,columns=['code','t'])
Data['t'] = Data['t'].astype('float')
from functions import parse_code_map
Code_Map = parse_code_map(code_map)

# adding the column. This is 200ms ... 
Data['name'] = [Code_Map[Code_Map['code'] == v]['name'].values[0] for v in Data['code'].values]

""" first make neo data structure """

Segment = neo.core.Segment()

# spans
span_names = [name.split('_ON')[0] for name in Code_Map['name'] if name.endswith('_ON')]
for span_name in span_names:
    try:
        on_times = Data.groupby('name').get_group(span_name+'_ON')['t'].values.astype('float')*pq.ms
        off_times = Data.groupby('name').get_group(span_name+'_OFF')['t'].values.astype('float')*pq.ms
        if on_times.shape != off_times.shape:
            print("unequal number of ON and OFF events for: ", span_name)
        dt = off_times - on_times
        Segment.epochs.append(neo.core.Epoch(times=on_times,durations=dt,label=span_name))
    except KeyError:
        print("span not present: ",span_name)

# events
event_names = [name.split('_EVENT')[0] for name in Code_Map['name'] if name.endswith('_EVENT')]

for event_name in event_names:
    try:
        times = Data.groupby('name').get_group(event_name+'_EVENT')['t'].values.astype('float')*pq.ms
        Segment.events.append(neo.core.Event(times,label=event_name))
    except KeyError:
        print("event not present: ", event_name)

# states
state_names = [name.split('_STATE')[0] for name in Code_Map['name'] if name.endswith('_STATE')]

for state_name in state_names:
    try:
        times = Data.groupby('name').get_group(state_name+'_STATE')['t'].values.astype('float')*pq.ms
        Segment.events.append(neo.core.Event(times,label=state_name))
    except KeyError:
        print("state not present: ", state_name)



"""
a plt figure with black lines horizontally for all trials
x is time
successful trials vs nonsuccessfl trials diff colored
events and spans colored and marked with their timepoints

event code that defines trial entry
event code that defines trial successful exit
event code that defines trial unsuccessful exit
"""

trial_entry = "FIXATE_STATE"
trial_exit_succ = "SUCCESSFUL_FIXATION_EVENT"
trial_exit_unsucc = "BROKEN_FIXATION_EVENT"

TrialsDf = pd.DataFrame()
TrialsDf['t_entry'] = Data.groupby('name').get_group(trial_entry)['t']

Df = pd.DataFrame()
Df['t_exit'] = Data.groupby('name').get_group(trial_exit_succ)['t']
Df['outcome'] = 'succ'

Df2 = pd.DataFrame()
Df2['t_exit'] = Data.groupby('name').get_group(trial_exit_unsucc)['t']
Df2['outcome'] = 'unsucc'

Df3 = pd.concat([Df,Df2],axis=0)
Df3 = Df3.sort_values('t_exit')

# removing last incompleted
if TrialsDf.shape[0] > Df3.shape[0]:
    TrialsDf = TrialsDf[:-1]

TrialsDf = pd.concat([TrialsDf.reset_index(drop=True),Df3.reset_index(drop=True)],axis=1)
TrialsDf
""" this is a SpansDf
Spans2Epoch vs Epoch2Spans could be cool to have
"""

on_times = TrialsDf['t_entry'].values * pq.ms
off_times = TrialsDf['t_exit'].values * pq.ms
dt = off_times - on_times
TrialsDf['dt'] = dt

# neo.core.Epoch(times=on_times,durations=dt,label='Trials', labels=TrialsDf['outcome'])
Segment.epochs.append(neo.core.Epoch(times=on_times,durations=dt,label='Trials',labels=TrialsDf['outcome'].values))

"""
now: slice by trials
"""
pre, post = (-1000,1000)*pq.ms

def select(neo_objs,value=None,key='label'):
    selection = []
    for element in neo_objs:
        if element.annotations[key] == value:
            selection.append(element)
    return selection

epoch = select(Segment.epochs, 'Trials')[0]
epoch.times, epoch.times + epoch.durations




# %%
fig, axes = plt.subplots(figsize=(7,9))
colors = sns.color_palette('deep',n_colors=len(event_names)+len(span_names)+len(state_names))

cdict = dict(zip(event_names+span_names+state_names,colors))


for i, row in TrialsDf.iterrows():
    dt = (row['t_exit'] - row['t_entry'])*pq.ms
    if row['outcome'] == 'succ':
        col = 'black'
    else:
        col = 'gray'
    axes.plot([0,dt],[i,i],lw=3,color=col)
    axes.axhline(i,linestyle=':',color='black',alpha=0.5,lw=1)

    # adding events as ticks
    for j,event in enumerate(Segment.events):
        times = event.time_slice(row['t_entry']*pq.ms+pre,row['t_exit']*pq.ms+post).times
        times = times - row['t_entry']*pq.ms
        for t in times:
            axes.plot([t,t],[i-0.5,i+0.5],lw=3,color=cdict[event.annotations['label']])

    # adding spans
    for j, span in enumerate(Segment.epochs):
        if not span.annotations['label'] == 'Trials':
            spans_sliced = span.time_slice(row['t_entry']*pq.ms+pre,row['t_exit']*pq.ms+post)
            for time,dur in zip(spans_sliced.times, spans_sliced.durations):
                # print(t)
                t = time - row['t_entry']*pq.ms
                rect = plt.Rectangle((t.magnitude,i-0.5),dur.magnitude,1,
                                      facecolor=cdict[span.annotations['label']])
                axes.add_patch(rect)
        
for key in cdict.keys():
    # legend_lines.append(Line2D([0],[0], color=cdict(key),lw=4),name=key)
    axes.plot([0],[0],color=cdict[key],label=key,lw=4)
axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
axes.invert_yaxis()
axes.set_xlabel('time (ms)')
axes.set_ylabel('trials')
fig.tight_layout()

t2 = Time.time()

print(t2-t1) # 800 ms