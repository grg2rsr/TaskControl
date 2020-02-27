%matplotlib qt5
%load_ext autoreload
%autoreload 2

from matplotlib import pyplot as plt
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import seaborn as sns
from tqdm import tqdm

"""
.______    __        ______   .___________.___________. _______ .______          _______.
|   _  \  |  |      /  __  \  |           |           ||   ____||   _  \        /       |
|  |_)  | |  |     |  |  |  | `---|  |----`---|  |----`|  |__   |  |_)  |      |   (----`
|   ___/  |  |     |  |  |  |     |  |        |  |     |   __|  |      /        \   \
|  |      |  `----.|  `--'  |     |  |        |  |     |  |____ |  |\  \----.----)   |
| _|      |_______| \______/      |__|        |__|     |_______|| _| `._____|_______/

"""

def trial_overview(Data, t_ref, pre, post, axes=None, how='dots'):

    if axes is None:
        axes = plt.gca()

    for i,t in enumerate(tqdm(t_ref)):
        Df = bhv.time_slice(Data,t+pre,t+post,'t')
        # present_events = [name for name in Df['name'].unique() if name.endswith("_EVENT")]

        for name,group in Df.groupby('name'):
            if name.endswith("_EVENT"):
                event_name = name.split("_EVENT")[0]
                times = group['t'] - t
                
                if how == 'dots':
                    axes.plot(times, [i]*len(times), '.', color=cdict[event_name], alpha=0.75) # a bar
                
                if how == 'bars':
                    for time in times:
                        axes.plot([time,time],[i-0.5,i+0.5],lw=2,color=cdict[event_name], alpha=0.75) # a bar
            
            if name.endswith("_ON") and name != "LICK_ON":
                span_name = name.split("_ON")[0]
                Df_sliced = bhv.log2Span(Df, span_name)

                for j, row_s in Df_sliced.iterrows():
                    time = row_s['t_on'] - t
                    dur = row_s['dt']
                    rect = plt.Rectangle((time,i-0.5), dur, 1, facecolor=cdict[span_name], linewidth=2)
                    axes.add_patch(rect)


    for key in cdict.keys():
        axes.plot([0],[0],color=cdict[key],label=key,lw=4)
    axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
    axes.invert_yaxis()
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('trials')

    return axes

def psth(t_ref, events, pre, post, bin_width=50, axes=None, **kwargs):
    if axes is None:
        axes = plt.gca()

    t_bins = sp.arange(pre,post,bin_width)
    bins = sp.zeros(t_bins.shape)

    values = []
    for t in t_ref:
        times = bhv.time_slice(events,t+pre,t+post,'t')['t'] - t
        values.append(times.values)
    values = sp.concatenate(values)

    counts, bins = sp.histogram(values,bins=t_bins)
    axes.step(bins[1:], counts, **kwargs)
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('count')

    return axes

"""
.______   .______       _______
|   _  \  |   _  \     |   ____|
|  |_)  | |  |_)  |    |  |__
|   ___/  |      /     |   __|
|  |      |  |\  \----.|  |____
| _|      | _| `._____||_______|

"""

### PATH DEF
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals/JP2073/2020-02-11_12-59-34_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/2020-02-20_09-39-30_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/2020-02-20_14-32-43_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2079/2020-02-25_13-47-59_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2079/2020-02-14_11-14-47_lick_for_reward_w_surpression/arduino_log.txt") # the last file of the non-trial entry cue
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-14_09-01-40_lick_for_reward_w_surpression/arduino_log.txt")


"""
 ___     ___    ______   __
|__ \   / _ \  |____  | /_ |
   ) | | | | |     / /   | |
  / /  | | | |    / /    | |
 / /_  | |_| |   / /     | |
|____|  \___/   /_/      |_|

"""

# first 2071
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-11_10-16-38_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-12_13-56-01_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-13_16-54-41_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-14_09-01-40_lick_for_reward_w_surpression/arduino_log.txt")

# first day with trial available cue
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-18_10-05-16_lick_for_reward_w_surpression/arduino_log.txt")
# hits limit, marches out even if rew is not collected

# series of confusion begins
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-19_09-56-10_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-20_09-39-30_lick_for_reward_w_surpression/arduino_log.txt")
# but contains first sign of learning?

# no, continues
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-21_09-16-11_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-24_10-06-59_lick_for_reward_w_surpression/arduino_log.txt")

# incomplete?
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-24_10-14-54_lick_for_reward_w_surpression/arduino_log.txt")
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-24_10-29-53_lick_for_reward_w_surpression/arduino_log.txt")

# last
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2071/2020-02-25_10-40-33_lick_for_reward_w_surpression/arduino_log.txt")

"""
 ___     ___    ______    ___
|__ \   / _ \  |____  |  / _ \
   ) | | | | |     / /  | (_) |
  / /  | | | |    / /    \__, |
 / /_  | |_| |   / /       / /
|____|  \___/   /_/       /_/

"""
# last session
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2079/2020-02-25_13-47-59_lick_for_reward_w_surpression/arduino_log.txt")

"""
 ___     ___    ______    ___
|__ \   / _ \  |____  |  / _ \
   ) | | | | |     / /  | (_) |
  / /  | | | |    / /    > _ <
 / /_  | |_| |   / /    | (_) |
|____|  \___/   /_/      \___/

"""

# first day - makes no sense to plot
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-11_13-57-16_lick_for_reward_w_surpression/arduino_log.txt")

# first with marching up 
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-12_17-48-21_lick_for_reward_w_surpression/arduino_log.txt")

# serves to tell teh story?
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-13_19-18-17_lick_for_reward_w_surpression/arduino_log.txt")

# the last day before confusion and a good example for unclear if they are doing anything really
# analyize reward RT here? nonconvincing 175 ms
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-14_10-42-36_lick_for_reward_w_surpression/arduino_log.txt")

# confused
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-18_13-45-11_lick_for_reward_w_surpression/arduino_log.txt")

# confusion
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-19_12-37-40_lick_for_reward_w_surpression/arduino_log.txt")

# confusion
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-20_13-08-59_lick_for_reward_w_surpression/arduino_log.txt")

# last day of confusion
# good one to show the responding RT situation
log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-21_11-50-52_lick_for_reward_w_surpression/arduino_log.txt")

# hes doing it!
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-24_11-31-03_lick_for_reward_w_surpression/arduino_log.txt")

# last session
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2078/2020-02-25_12-47-27_lick_for_reward_w_surpression/arduino_log.txt")


"""
 ___     ___    ______   ___
|__ \   / _ \  |____  | |__ \
   ) | | | | |     / /     ) |
  / /  | | | |    / /     / /
 / /_  | |_| |   / /     / /_
|____|  \___/   /_/     |____|

"""
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2072/2020-02-25_11-22-44_lick_for_reward_w_surpression/arduino_log.txt")




# doing it but looses engagement
# log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals_new/JP2072/2020-02-24_10-41-10_lick_for_reward_w_surpression/arduino_log.txt")

# infer
code_map_path = log_path.parent.joinpath("lick_for_reward_w_surpression","Arduino","src","event_codes.h")

### READ 
CodesDf = bhv.parse_code_map(code_map_path)
code_map = dict(zip(CodesDf['code'],CodesDf['name']))
Data = bhv.parse_arduino_log(log_path, code_map)

### COMMON
# the names of the things present in the log
span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

Spans = bhv.log2Spans(Data, span_names)
Events = bhv.log2Events(Data, event_names)

### SOME PREPROCESSING
# filter unrealistic licks
bad_licks = sp.logical_or(Spans['LICK']['dt'] < 20,Spans['LICK']['dt'] > 100)
Spans['LICK'] = Spans['LICK'].loc[~bad_licks]

# add lick_event
Lick_Event = pd.DataFrame(sp.stack([['NA']*Spans['LICK'].shape[0],Spans['LICK']['t_on'].values,['LICK_EVENT']*Spans['LICK'].shape[0]]).T,columns=['code','t','name'])
Lick_Event['t'] = Lick_Event['t'].astype('float')
Data = Data.append(Lick_Event)
Data.sort_values('t')

event_names.append("LICK")
Events['LICK'] = bhv.log2Event(Data,'LICK')

Spans.pop("LICK")
span_names.remove("LICK")

colors = sns.color_palette('hls',n_colors=len(event_names)+len(span_names))[::-1]
cdict = dict(zip(event_names+span_names,colors))


"""
.______    __        ______   .___________.    _______.
|   _  \  |  |      /  __  \  |           |   /       |
|  |_)  | |  |     |  |  |  | `---|  |----`  |   (----`
|   ___/  |  |     |  |  |  |     |  |        \   \
|  |      |  `----.|  `--'  |     |  |    .----)   |
| _|      |_______| \______/      |__|    |_______/

"""
import os 
# %%
plot_dir = log_path.parent.joinpath('plots')
os.makedirs(plot_dir,exist_ok=True)
os.chdir(plot_dir)

# big overview
Data.name.unique()
data = Data.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
# data = Data.groupby('name').get_group('REWARD_AVAILABLE_EVENT')
# data = Data.groupby('name').get_group('REWARD_AVAILABLE_STATE')
data = data.sort_values('t')
data = data.reset_index()

t_ref = data['t'].values
pre, post = (-100,800)

fig, axes = plt.subplots(figsize=[7,9])
trial_overview(Data,t_ref,pre,post,axes,how='dots')
fig.tight_layout()
# fig.savefig()


d = sp.diff(Data['t'].values)
d = sp.diff(Events['LICK']['t'])
bins = sp.linspace(0,200,20)
plt.hist(d,bins=bins)

state_names = []
for name, group in Data.groupby('name'):
    if name.endswith("_STATE"):
        state_names.append(name)


# %%
# with Lick PSTH
data = Data.groupby('name').get_group('TRIAL_ENTRY_EVENT')
# data = Data.groupby('name').get_group(g) for g in ['TRIAL_COMPLETED_EVENT','TRIAL_ABORTED_EVENT']
# data = Data.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
# data = Data.groupby('name').get_group('TRIAL_ABORTED_EVENT')
# data = Data.groupby('name').get_group('TRIAL_COMPLETED_EVENT')
data = data.iloc[20:420]
data = data.sort_values('t')
data = data.reset_index()
t_ref = data['t'].values
pre, post = (-100,5000)

fig, axes = plt.subplots(nrows=2,sharex=True,figsize=[7,9])
trial_overview(Data,t_ref,pre,post,axes[0],how='dots')
psth(t_ref, Events['LICK'], pre, post, bin_width=20)
fig.tight_layout()

# %%

# reaction time to reward_available
def log2Span2(Data, on_name, off_name):
    """
    makes a span from one timepoint to the next
    """
    ons = Data.groupby('name').get_group(on_name)
    offs = Data.groupby('name').get_group(off_name)

    ts = []
    for tup in ons.itertuples():
        t_on = tup.t
        t_max = offs.iloc[-1]['t']
        try:
            t_off = bhv.time_slice(offs, t_on, t_max, 't').iloc[0]['t']
            ts.append((t_on,t_off))
        except IndexError:
            # thrown when last is on
            pass
        #     t_off = offs.loc[offs['t'] > t_on].iloc[0]['t']

    Span = pd.DataFrame(ts,columns=['t_on','t_off'])
    Span['dt'] = Span['t_off'] - Span['t_on']
    return Span


# Rew_col_rt = log2Span2(Data,"REWARD_AVAILABLE_STATE","REWARD_COLLECTED_EVENT")['dt']
# plt.hist(Rew_col_rt,bins=sp.arange(0,200,5))
# plt.hist(Rew_col_rt)


# %%

# events 2 span?
def events2span(Data, entry_event, exit_event):
    entry_event = "TRIAL_ENTRY_EVENT"
    exit_event = "ITI_STATE"
    data_entry = Data.groupby("name").get_group(entry_event)
    data_exit = Data.groupby("name").get_group(exit_event)

    if data_entry.shape[0] == data_exit.shape[0]:
        # easy peasy
        Span = pd.DataFrame(sp.stack([data_entry['t'].values,data_exit['t'].values],axis=1),columns=['t_on','t_off'])
        Span['dt'] = Span['t_off'] - Span['t_on']
        return Span
    
    if data_entry.shape[0] != data_exit.shape[0]:
        print("problems occur: unequal number of entry and exits")
        ts = []
        for tup in data_entry.itertuples():
            t_on = tup.t
            t_max = data_exit.iloc[-1]['t']
            try:
                t_off = bhv.time_slice(data_exit, t_on, t_max, 't').iloc[0]['t']
                ts.append((t_on,t_off))
            except IndexError:
                # thrown when last is on
                pass

        Span = pd.DataFrame(ts,columns=['t_on','t_off'])
        Span['dt'] = Span['t_off'] - Span['t_on']
        return Span

# slice_by_span(Data,Span)
# completed = events2span(Data,"TRIAL_ENTRY_EVENT","ITI_STATE")

# make SessionDf
completed = log2Span2(Data,"TRIAL_AVAILABLE_STATE","ITI_STATE")
#aborted = log2Span2(Data,"TRIAL_ENTRY_EVENT","TRIAL_ABORTED_EVENT")
#all 

Dfs = []
for i, row in completed.iterrows():
    ind_start = Data.loc[Data['t'] == row['t_on']].index[0]
    ind_stop = Data.loc[Data['t'] == row['t_off']].index[0]
    Dfs.append(Data.iloc[ind_start:ind_stop+1])

SessionDf = bhv.parse_trials(Dfs)

### plot recent success rate
# %%
fig, axes = plt.subplots()
x = SessionDf.index
y = [sum(SessionDf.iloc[:i]['successful'])/(i+1) for i in range(SessionDf.shape[0])]
axes.plot(x,y,lw=2,label='total',alpha=0.8,color="black")
hist = 50
y = [sum(SessionDf.iloc[i-hist:i]['successful'])/hist for i in range(SessionDf.shape[0])]
axes.plot(x,y,lw=2,label='last 50')
axes.set_xlabel('trials')
axes.set_ylabel('fraction successful',alpha=0.8)

# plot reward collection rate
# hist = 25
# fig, axes = plt.subplots()
# SDf = SessionDf.groupby('successful').get_group(True)
# SDf.reset_index(drop=True)
# x = SDf.index
# y = [sum(SDf.iloc[:i]['reward_collected'])/(i+1) for i in range(SDf.shape[0])]
# plt.plot(x,y)
# y = [sum(SDf.iloc[i-hist:i]['reward_collected'])/hist for i in range(SDf.shape[0])]
# plt.plot(x,y)

# %%
# 
vals = SessionDf.groupby("reward_collected").get_group(True)['rew_col_rt']
plt.hist(vals,bins=sp.arange(0,200,10))





