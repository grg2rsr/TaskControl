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

### PATH DEF
log_path = Path("/media/georg/htcondor/shared-paton/georg/Animals/JP2073/2020-02-11_12-59-34_lick_for_reward_w_surpression/arduino_log.txt")
# code_map_path = Path("/media/georg/htcondor/shared-paton/georg/Animals/JP2073/2020-02-11_12-59-34_lick_for_reward_w_surpression/lick_for_reward_w_surpression/Arduino/src/event_codes.h")

log_path = Path("/media/georg/htcondor/shared-paton/georg/2020-02-20_09-39-30_lick_for_reward_w_surpression/arduino_log.txt")

# log_path = Path("/media/georg/htcondor/shared-paton/georg/2020-02-20_14-32-43_lick_for_reward_w_surpression/arduino_log.txt")
code_map_path = log_path.parent.joinpath("lick_for_reward_w_surpression","Arduino","src","event_codes.h")

### READ 
CodesDf = bhv.parse_code_map(code_map_path)
code_map = dict(zip(CodesDf['code'],CodesDf['name']))
Data = bhv.parse_arduino_log(log_path, code_map)

# for a live variant, Data is inferred from lines

### COMMON
# the names of the things present in the log
span_names = [name.split('_ON')[0] for name in CodesDf['name'] if name.endswith('_ON')]
event_names = [name.split('_EVENT')[0] for name in CodesDf['name'] if name.endswith('_EVENT')]

Spans = bhv.log2Spans(Data, span_names)
Events = bhv.log2Events(Data, event_names)

colors = sns.color_palette('husl',n_colors=len(event_names)+len(span_names))
cdict = dict(zip(event_names+span_names,colors))

### SOME PREPROCESSING
# filter unrealistic licks
bad_licks = sp.logical_or(Spans['LICK']['dt'] < 20,Spans['LICK']['dt'] > 100)
Spans['LICK'] = Spans['LICK'].loc[~bad_licks]

from tqdm import tqdm


### overview plot

# plot licks relative to collected rewards / or any event really
# the events that will form the relative timepoints

# data = pd.concat([Data.groupby('name').get_group(g) for g in ('REWARD_COLLECTED_EVENT','REWARD_MISSED_EVENT')])
# data = Data.groupby('name').get_group('ITI_STATE')
data = Data.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
data = data.sort_values('t')
data = data.reset_index()

pre, post = (-3000,3000)

fig, axes = plt.subplots()

for i, row in data.iterrows():
    t = row['t']

    # adding events
    for event_name, Df in Events.items():
        times = bhv.time_slice(Df, t+pre, t+post, col='t')['t']
        times = times - t # relative to trial onset

        # vlines based this is slower?
        # axes.vlines(times, i-0.5, i+0.5, lw=3,color=cdict[event_name], alpha=0.75) # a bar

        # manual bar plotting - faster?
        # for time in times:
            # axes.plot([time,time],[i-0.5,i+0.5],lw=3,color=cdict[event_name], alpha=0.75) # a bar

        # dots
        axes.plot(times, [i]*len(times), '.', color=cdict[event_name], alpha=0.75) # a bar

    # adding spans
    for span_name, Df in Spans.items():
        Df_sliced = bhv.time_slice(Df, t+pre, t+post, col='t_on')
        for j, row_s in Df_sliced.iterrows():
            time = row_s['t_on'] - t
            dur = row_s['dt']
            rect = plt.Rectangle((time,i-0.5), dur, 1, facecolor=cdict[span_name], alpha=0.75)
            axes.add_patch(rect)


for key in cdict.keys():
    axes.plot([0],[0],color=cdict[key],label=key,lw=4)
axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
axes.invert_yaxis()
axes.set_xlabel('time (ms)')
axes.set_ylabel('trials')
fig.tight_layout()

####### NEW ATTEMPT

data = Data.groupby('name').get_group('TRIAL_AVAILABLE_STATE')
data = data.sort_values('t')
data = data.reset_index()
t_ref = data['t'].values
pre, post = (-100,3000)

fig, axes = plt.subplots()

for i,t in enumerate(tqdm(t_ref)):
    Df = bhv.time_slice(Data,t+pre,t+post,'t')
    # present_events = [name for name in Df['name'].unique() if name.endswith("_EVENT")]

    for name,group in Df.groupby('name'):
        if name.endswith("_EVENT"):
            event_name = name.split("_EVENT")[0]
            times = group['t'] - t
            
            # dots
            # axes.plot(times, [i]*len(times), '.', color=cdict[event_name], alpha=0.75) # a bar
            
            for time in times:
                axes.plot([time,time],[i-0.5,i+0.5],lw=3,color=cdict[event_name], alpha=0.75) # a bar

        # if name.endswith("_ON"):
        #     event_name = name.split("_EVENT")[0]
        #     times = group['t'] - t

# direct comparison: the other way around
fig, axes = plt.subplots()
for i,t in enumerate(tqdm(t_ref)):
    for event_name, Df in Events.items():
        data = bhv.time_slice(Df, t+pre, t+post,'t')
        times = data['t'] - t

        # dots
        axes.plot(times, [i]*len(times), '.', color=cdict[event_name], alpha=0.75) # a bar

        # as bars
        # for time in times:
        #     axes.plot([time,time],[i-0.5,i+0.5],lw=3,color=cdict[event_name], alpha=0.75) # a bar

    for span_name, Df in Spans.items():
        Df_sliced = bhv.time_slice(Df, t+pre, t+post, 't_on')

        for j, row_s in Df_sliced.iterrows():
            time = row_s['t_on'] - t
            dur = row_s['dt']
            rect = plt.Rectangle((time,i-0.5), dur, 1, facecolor=cdict[span_name], alpha=0.75)
            axes.add_patch(rect)

    # for event in present_events:
        # Df.groupby

    # for i, row in Df.iterrows():
    #     if row['name'].endswith("_EVENT"):
    #         time = row['t'] - t_ref
    #         axes.plot([time,time],[i-0.5,i+0.5],lw=3,color=cdict[event_name], alpha=0.75) # a bar













# event rate of sth relative to sth else - PSTH for speed for now
fig, axes = plt.subplots()

data = pd.concat([Data.groupby('name').get_group(g) for g in ('REWARD_COLLECTED_EVENT','REWARD_MISSED_EVENT')])
data = pd.concat([Data.groupby('name').get_group(g) for g in ('TRIAL_AVAILABLE_STATE')])
data = data.sort_values('t')
data = data.reset_index()

data = data.iloc[-20:]

ref_times = data['t'] # apply slicing here
events = Spans['LICK']['t_on']

pre, post = (-5000,5000)
bin_width = 250
t_bins = sp.arange(pre,post,bin_width)
bins = sp.zeros(t_bins.shape)

for t in ref_times:
    event_times = events[sp.logical_and(events > t+pre ,events < t+post)] - t
    for event_time in event_times:
        bins[sp.argmin(event_time > t_bins)] += 1 

plt.step(t_bins,bins)












# class MyMplCanvas(FigureCanvas):
#     # FIXME add controls
#     """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
#     # def __init__(self, parent, width=7, height=9, dpi=100):
#     #     # super(MyMplCanvas, self).__init__(parent=parent)
#     #     self.parent=parent

#     #     self.lines = []

#     #     # figure init
#     #     self.fig = Figure(figsize=(width, height), dpi=dpi)
#     #     self.axes = self.fig.add_subplot(111)
#     #     FigureCanvas.__init__(self, self.fig)
#     #     # self.setParent(parent)

#     #     FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
#     #     FigureCanvas.updateGeometry(self)

#     #     self.parent.ArduinoController.Signals.serial_data_available.connect(self.update_data)
#     #     self.init()

#     #     self.show()

#     def __init__(self, parent, width=7, height=9, dpi=100):
#         # super(MyMplCanvas, self).__init__(parent=parent)
#         self.parent=parent

#         self.lines = []

#         # figure init
#         self.fig = Figure(figsize=(width, height), dpi=dpi)
#         self.axes = self.fig.add_subplot(111)
#         FigureCanvas.__init__(self, self.fig)
#         # self.setParent(parent)

#         FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
#         FigureCanvas.updateGeometry(self)

#         self.parent.ArduinoController.Signals.serial_data_available.connect(self.update_data)
#         self.init()

#         self.show()

#     def init(self):
#         """ can only be called if all is running already """

#         pio_folder = self.parent.task_config['Arduino']['pio_project_folder']
#         event_codes_fname = self.parent.task_config['Arduino']['event_codes_fname']
#         code_map_path = self.parent.ArduinoController.task_folder.joinpath(pio_folder,"src",event_codes_fname)
#         self.log_path = self.parent.ArduinoController.run_folder.joinpath('arduino_log.txt')

#         self.Code_Map = functions.parse_code_map(code_map_path)
#         self.code_dict = dict(zip(self.Code_Map['code'].values, self.Code_Map['name'].values))


#     # def init_figure(self):
#     #     self.axes.plot(sp.randn(100))
#     #     plt.show()
#     #     pass

#     def update_data(self, line):
#         """ connected to new serial data, when any of the trial finishers, update """ 

#         # if decodeable
#         if not line.startswith('<'):
#             code = line.split('\t')[0]
#             decoded = self.code_dict[code]
#             line = '\t'.join([decoded,line.split('\t')[1]])
#             self.lines.append(line)

#             if self.code_dict[code] == "TRIAL_COMPLETED_EVENT" or self.code_dict[code] == "TRIAL_ABORTED_EVENT":
#                 self.update_plot()

#     def update_plot(self):
#         # make data for plot
#         valid_lines = [line.strip().split('\t') for line in self.lines if '\t' in line]
#         self.Data = pd.DataFrame(valid_lines,columns=['name','t'])
#         self.Data['t'] = self.Data['t'].astype('float')
                                
#         # the names of the things present in the log
#         span_names = [name.split('_ON')[0] for name in self.Code_Map['name'] if name.endswith('_ON')]
#         event_names = [name.split('_EVENT')[0] for name in self.Code_Map['name'] if name.endswith('_EVENT')]

#         Spans = vis.log2Spans(self.Data, span_names)
#         Events = vis.log2Events(self.Data, event_names)

#         # definition of the bounding events
#         trial_entry = "TRIAL_ENTRY_EVENT"
#         trial_exit_succ = "TRIAL_COMPLETED_EVENT"
#         trial_exit_unsucc = "TRIAL_ABORTED_EVENT"

#         TrialsDf = vis.make_TrialsDf(self.Data,trial_entry=trial_entry,
#                                      trial_exit_succ=trial_exit_succ,
#                                      trial_exit_unsucc=trial_exit_unsucc)

#         # fig, axes = plt.subplots(figsize=(7,9))

#         colors = sns.color_palette('deep',n_colors=len(event_names)+len(span_names))
#         cdict = dict(zip(event_names+span_names,colors))

#         pre, post = (-1000,1000) # hardcoded

#         for i, row in TrialsDf.iterrows():
#             if row['outcome'] == 'succ':
#                 col = 'black'
#             else:
#                 col = 'gray'
#             self.axes.plot([0,row['dt']],[i,i],lw=3,color=col)
#             self.axes.axhline(i,linestyle=':',color='black',alpha=0.5,lw=1)

#             # adding events as ticks
#             for event_name, Df in Events.items():
#                 times = vis.time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t')['t']
#                 times = times - row['t_on'] # relative to trial onset

#                 for t in times:
#                     self.axes.plot([t,t],[i-0.5,i+0.5],lw=3,color=cdict[event_name])

#             # adding spans
#             for span_name, Df in Spans.items():
#                 Df_sliced = vis.time_slice(Df, row['t_on']+pre, row['t_off']+post, col='t_on')
#                 for j, row_s in Df_sliced.iterrows():
#                     t = row_s['t_on'] - row['t_on']
#                     dur = row_s['dt']
#                     rect = plt.Rectangle((t,i-0.5), dur, 1,
#                                         facecolor=cdict[span_name])
#                     self.axes.add_patch(rect)

#         for key in cdict.keys():
#             self.axes.plot([0],[0],color=cdict[key],label=key,lw=4)
#         # self.axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.)
#         # self.axes.invert_yaxis()
#         self.axes.set_xlabel('time (ms)')
#         self.axes.set_ylabel('trials')
#         self.fig.tight_layout()
#         self.draw()
        
    