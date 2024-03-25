# %% imports 
%matplotlib qt5
%load_ext autoreload
%autoreload 2

import sys, os
from pathlib import Path
from tqdm import tqdm

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle
import seaborn as sns

import scipy as sp
import numpy as np
import pandas as pd
import cv2

sys.path.append('/home/georg/code/TaskControl')

from Utils import behavior_analysis_utils as bhv
from Utils import dlc_analysis_utils as dlc
import Utils.metrics as metrics
from Utils.sync import Syncer

colors = dict(success="#72E043", 
              reward="#3CE1FA", 
              correct="#72E043", 
              incorrect="#F56057", 
              premature="#9D5DF0", 
              missed="#F7D379",
              left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95))

# %% read all three data sources

# marq last session
# session_folder = Path("/media/georg/data/reaching_dlc/marquez_last_session/2021-05-18_09-41-58_learn_to_fixate_discrete_v1") # marquez local

# poolboys second to last good session for reach inspections
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-15_14-15-36_learn_to_choose_v2")

# lumberjacks problem
# session_folder = Path("/media/georg/data/tmp sessions/2021-11-03_13-02-12_learn_to_choose_v2")

# poolboy starting to go down
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-18_12-32-41_learn_to_choose_v2")

# Therapist reaches
path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-11-12_14-52-19_learn_to_choose_v2"
session_folder = Path(path)
# %%
os.chdir(session_folder)

### DeepLabCut data
# h5_path = session_folder / [fname for fname in os.listdir(session_folder) if fname.endswith('filtered.h5')][0]
h5_path = session_folder / [fname for fname in os.listdir(session_folder) if fname.endswith('.h5')][0]
DlcDf = dlc.read_dlc_h5(h5_path)
# getting all dlc body parts
bodyparts = sp.unique([j[0] for j in DlcDf.columns[1:]])

### Camera data
video_path = session_folder / "bonsai_video.avi"
Vid = dlc.read_video(str(video_path))

### Arduino data
log_path = session_folder / 'arduino_log.txt'
LogDf = bhv.get_LogDf_from_path(log_path)

### LoadCell Data
# LoadCellDf = bhv.parse_bonsai_LoadCellData(session_folder / 'bonsai_LoadCellData.csv')

# Syncer
from Utils import sync
cam_sync_event, Cam_SyncDf = sync.parse_cam_sync(session_folder / 'bonsai_frame_stamps.csv', offset=1, return_full=True)
# lc_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv')
arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

Sync = Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
# Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
Sync.data['cam'] = cam_sync_event['t'].values
Sync.sync('arduino','cam')

DlcDf['t_cam'] = Cam_SyncDf['t']
Sync.data['frames'] = cam_sync_event.index.values
Sync.sync('frames','cam')

Sync.eval_plot()
# Sync = Syncer()
# Sync.data['arduino'] = arduino_sync_event['t'].values
# # Sync.data['loadcell'] = lc_sync_event['t'].values
# Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
# Sync.data['cam'] = cam_sync_event['t'].values # used for what?
# Sync.sync('arduino','dlc')
# Sync.sync('arduino','cam')

DlcDf['t'] = Sync.convert(DlcDf['t_cam'], 'cam', 'arduino')

# %% Dlc processing
# speed
for i,bp in enumerate(tqdm(bodyparts)):
    Vxy = sp.diff(DlcDf[bp][['x','y']].values,axis=0) / DlcDf['t'][:-1].values[:,sp.newaxis]
    V = sp.sqrt(sp.sum(Vxy**2,axis=1)) # euclid vector norm
    V = V / sp.diff(DlcDf['t'].values) # -> to speed
    V = sp.concatenate([[sp.nan],V]) # pad first to nan (speed undefined)
    DlcDf[(bp,'v')] = V

# %% analysis of too fast movements
# fig, axes = plt.subplots()
# for bp in bodyparts:
#     V = DlcDf[(bp,'v')]
#     tvec = DlcDf['t']
#     axes.plot(tvec, V, label=[bp])

# sides = ['left','right']
# for side in sides:
#     reach_times = LogDf.groupby('name').get_group("REACH_%s_ON" % side.upper())['t'].values
#     for t in reach_times:
#         axes.axvline(t, color=colors[side], alpha=0.5, lw=1)

# axes.legend()

# %% speed filter
V_thresh = 0.00001
for i,bp in enumerate(tqdm(bodyparts)):
    V = DlcDf[(bp,'v')]
    DlcDf[(bp,'likelihood')][V > V_thresh] = 0
    
    # Vxy = sp.diff(DlcDf[bp][['x','y']].values,axis=0) / DlcDf['t'][:-1].values[:,sp.newaxis]
    # V = sp.sqrt(sp.sum(Vxy**2,axis=1)) # euclid vector norm
    # V = V / sp.diff(DlcDf['t'].values) # -> to speed
    # V = sp.concatenate([[sp.nan],V]) # pad first to nan (speed undefined)
    # DlcDf[(bp,'v')] = V

# %% DLC preprocessing
# replace low confidence prediction with interpolated
p = 0.90
for bp in tqdm(bodyparts):
    good_inds = DlcDf[bp]['likelihood'].values > p
    ix = DlcDf[bp].loc[good_inds].index

    bad_inds = DlcDf[bp]['likelihood'].values < p
    bix = DlcDf[bp].loc[bad_inds].index

    x = DlcDf[bp].loc[good_inds]['x'].values
    interp = sp.interpolate.interp1d(ix, x, fill_value='extrapolate')
    DlcDf[(bp,'x')].loc[bix] = interp(bix)

    y = DlcDf[bp].loc[good_inds]['y'].values
    interp = sp.interpolate.interp1d(ix, y, fill_value='extrapolate')
    DlcDf[(bp,'y')].loc[bix] = interp(bix)

    V = DlcDf[bp].loc[good_inds]['v'].values
    interp = sp.interpolate.interp1d(ix, V, fill_value='extrapolate')
    DlcDf[(bp,'v')].loc[bix] = interp(bix)


"""
 
 ######## ########  ####    ###    ##        ######  
    ##    ##     ##  ##    ## ##   ##       ##    ## 
    ##    ##     ##  ##   ##   ##  ##       ##       
    ##    ########   ##  ##     ## ##        ######  
    ##    ##   ##    ##  ######### ##             ## 
    ##    ##    ##   ##  ##     ## ##       ##    ## 
    ##    ##     ## #### ##     ## ########  ######  
 
"""
# %% prep and general analysis
session_metrics = [metrics.get_start, metrics.get_stop, metrics.has_choice, metrics.get_chosen_side, metrics.get_correct_side, metrics.get_interval, metrics.get_outcome, metrics.get_choice_rt]
SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, session_metrics, "TRIAL_ENTRY_EVENT")

# expand categorical columns into boolean
categorial_cols = ['outcome']
for category_col in categorial_cols:
    categories = SessionDf[category_col].unique()
    categories = [cat for cat in categories if not pd.isna(cat)]
    for category in categories:
        SessionDf['is_'+category] = SessionDf[category_col] == category

# setup general filter
SessionDf['exclude'] = False

# %% DlcDf based metrics
# hand pos at go cue
# event = "CHOICE_STATE"
# th = 200
# for i, TrialDf in enumerate(TrialDfs):
#     try:
#         t = TrialDf.loc[TrialDf['name'] == event].iloc[0]['t']
#         frame_ix = sp.argmin(sp.absolute(DlcDf['t'].values - t))
#         SessionDf.loc[i,'paw_resting'] = DlcDf['PAW_L'].loc[frame_ix]['y'] < th
#     except IndexError:
#         SessionDf.loc[i,'paw_resting'] = sp.nan
"""
 
 ########  ##        #######  ######## ######## ######## ########   ######  
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##    ## 
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##       
 ########  ##       ##     ##    ##       ##    ######   ########   ######  
 ##        ##       ##     ##    ##       ##    ##       ##   ##         ## 
 ##        ##       ##     ##    ##       ##    ##       ##    ##  ##    ## 
 ##        ########  #######     ##       ##    ######## ##     ##  ######  
 
"""
# %%
### helpers
def make_bodypart_colors(bodyparts):
    bp_left = [bp for bp in bodyparts if bp.endswith('L')]
    bp_right = [bp for bp in bodyparts if bp.endswith('R')]
    c_l = sns.color_palette('viridis', n_colors=len(bp_left))
    c_r = sns.color_palette('magma', n_colors=len(bp_right))
    bp_cols = dict(zip(bp_left+bp_right,c_l+c_r))
    return bp_cols

def get_frame_for_time(t, t_frames):
    # get the closest frames, indices and times
    ix = np.argmin((t_frames - t)**2)
    return ix,  t_frames[ix]

def get_frame_for_times(ts, t_frames):
    L = [get_frame_for_time(t) for t in ts]
    frame_ix = [l[0] for l in L]
    frame_times = [l[1] for l in L]
    return frame_ix, frame_times

# %%
"""
 
  ######  ########    ###    ######## ####  ######  
 ##    ##    ##      ## ##      ##     ##  ##    ## 
 ##          ##     ##   ##     ##     ##  ##       
  ######     ##    ##     ##    ##     ##  ##       
       ##    ##    #########    ##     ##  ##       
 ##    ##    ##    ##     ##    ##     ##  ##    ## 
  ######     ##    ##     ##    ##    ####  ######  
 
"""

# %% selecting t_on and t_off based on trial type

# trial selection
# SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='left'))
# TrialDf = TrialDfs[SDf.index[0]]
TrialDf = TrialDfs[0]

Df = bhv.event_slice(TrialDf, 'TRIAL_ENTRY_EVENT', 'ITI_STATE')
t_on = Df.iloc[0]['t']
t_off = Df.iloc[-1]['t']

# %% static image with trajectory between t_on and t_off

bp_cols = make_bodypart_colors(bodyparts)

fig, axes = plt.subplots()
frame_ix = Sync.convert(t_on, 'arduino', 'frames') # this is not error robust?
frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])

frame = dlc.get_frame(Vid, frame_ix)
dlc.plot_frame(frame, axes=axes)
dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes)

# trajectory
DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
dlc.plot_trajectories(DlcDfSlice, bodyparts, axes=axes, colors=bp_cols, lw=1, p=0.99)

# %% plot all of the selected trial type

# SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right', paw_resting=False))

# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(has_choice=True, correct_side='left', outcome='correct'))

# plot some random frame
fig, axes = plt.subplots()

frame_ix = 1000
frame = dlc.get_frame(Vid, frame_ix)
dlc.plot_frame(frame, axes=axes)

# plot all traj in selection
for i in tqdm(SDf.index):
    TrialDf = TrialDfs[i]
    Df = bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_EVENT')
    # Df = bhv.time_slice(Df, Df.iloc[-1]['t']-500, Df.iloc[-1]['t'])
    t_on = Df.iloc[0]['t']
    t_off = Df.iloc[-1]['t']

    # trial by trial colors
    bp_cols = {}
    cmaps = dict(zip(bodyparts,['viridis','magma']))
    for bp in bodyparts:
        c = sns.color_palette(cmaps[bp],as_cmap=True)(sp.rand())
        bp_cols[bp] = c

    # marker for the start
    # frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
    frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])
    dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes, markersize=5)

    # the trajectory
    DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
    dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=axes, lw=0.75, alpha=0.75, p=0.8)


# %% make an outcome / sides panel with the trajectories
outcomes = ['correct','incorrect']
sides = ['left','right']

fig, axes = plt.subplots(ncols=len(outcomes),nrows=len(sides),
                         sharex=True,sharey=True, figsize=[9,8])

def plot_all_trajectories(TrialDfs, ax=None):
    for i, TrialDf in enumerate(TrialDfs):
        if TrialDf.shape[0] > 0:
            t_on = TrialDf.iloc[0]['t']
            t_off = TrialDf.iloc[-1]['t']

            # trial by trial colors
            bp_cols = {}
            cmaps = dict(zip(bodyparts,['viridis','magma']))
            for bp in bodyparts:
                c = sns.color_palette(cmaps[bp],as_cmap=True)(sp.rand())
                bp_cols[bp] = c

            # marker for the start
            # frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
            # frame_ix, frame_time = get_frame_for_time(t_on, DlcDf['t'])
            # dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=ax, markersize=5)

            # the trajectory
            DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
            dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=ax, lw=1.2, alpha=0.5, p=0.8)

for i, outcome in enumerate(outcomes):
    for j, side in enumerate(sides):
        # plot some random frame
        frame_ix = 5000
        frame = dlc.get_frame(Vid, frame_ix)

        try:
            SDf = bhv.groupby_dict(SessionDf, dict(correct_side=side, outcome=outcome))

            TrialDfs_sel = [TrialDfs[i] for i in SDf.index]
            if outcome != 'missed':
                TrialDfs_sel = [bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_EVENT') for TrialDf in TrialDfs_sel]
            else:
                TrialDfs_sel = [bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_MISSED_EVENT') for TrialDf in TrialDfs_sel]

            dlc.plot_frame(frame, axes=axes[i,j])
            plot_all_trajectories(TrialDfs_sel, ax=axes[i,j])
        except KeyError:
            pass

for ax in axes.flatten():
    ax.set_aspect('equal')
    ax.set_xticklabels('')
    ax.set_yticklabels('')

for i, ax in enumerate(axes[0,:]):
    ax.set_title(sides[i],fontsize=16)

for i, ax in enumerate(axes[:,0]):
    ax.set_ylabel(outcomes[i],fontsize=16)


sns.despine(fig)
fig.suptitle('reach trajectories split by outcome/correct side',fontsize=16)
fig.tight_layout()
fig.subplots_adjust(top=0.90)

# plt.savefig('/home/georg/Desktop/plots for labmeeting/marquez all reaches 2.png', dpi=600)


# %% 
"""
 
 ##     ## #### ########  ########  #######  
 ##     ##  ##  ##     ## ##       ##     ## 
 ##     ##  ##  ##     ## ##       ##     ## 
 ##     ##  ##  ##     ## ######   ##     ## 
  ##   ##   ##  ##     ## ##       ##     ## 
   ## ##    ##  ##     ## ##       ##     ## 
    ###    #### ########  ########  #######  
 
"""

# %% display video of trial
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right'))
# TrialDf = TrialDfs[SDf.index[1]] # good long from resting
TrialDf = TrialDfs[SDf.index[3]] # good long from resting

# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='left'))
TrialDf = TrialDfs[SDf.index[5]] # good left reach
TrialDf = TrialDfs[SDf.index[6]] # good left reach
TrialDf = TrialDfs[SDf.index[7]] # good left reach

# Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','CHOICE_EVENT')
# Df = bhv.event_slice(TrialDf,'CHOICE_STATE','CHOICE_EVENT')
t_on = Df.iloc[0]['t'] - 250
t_off = Df.iloc[-1]['t'] + 2000

# %%
"""
 
 ##     ## ########  ##           ######  ##       ####  ######  ######## ########  
 ###   ### ##     ## ##          ##    ## ##        ##  ##    ## ##       ##     ## 
 #### #### ##     ## ##          ##       ##        ##  ##       ##       ##     ## 
 ## ### ## ########  ##           ######  ##        ##  ##       ######   ########  
 ##     ## ##        ##                ## ##        ##  ##       ##       ##   ##   
 ##     ## ##        ##          ##    ## ##        ##  ##    ## ##       ##    ##  
 ##     ## ##        ########     ######  ######## ####  ######  ######## ##     ## 
 
"""

def make_annotated_video(Vid, t_on, t_off, LogDf, DlcDf, fps=20, save=None):
    LogDfSlice = bhv.time_slice(LogDf, t_on, t_off)
    DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)

    # what events to display
    display_events = list(LogDfSlice.name.unique())
    # display_events = ['GO_CUE_SHORT_EVENT', 'GO_CUE_LONG_EVENT', 'CHOICE_CORRECT_EVENT', 'CHOICE_INCORRECT_EVENT', 'REWARD_LEFT_EVENT','REWARD_RIGHT_EVENT', 'REACH_LEFT_ON', 'REACH_LEFT_OFF', 'REACH_RIGHT_ON', 'REACH_RIGHT_OFF']
    if sp.nan in display_events:
        display_events.remove(np.nan)

    frame_on = DlcDfSlice.index[0]
    frame_off = DlcDfSlice.index[-1]
    ix = list(range(frame_on, frame_off))

    # plotting
    fig, ax = plt.subplots()
    ax.axis('off')

    if save is not None:
        import matplotlib as mpl
        # from matplotlib.animation import FFMpegWriter as AniWriter
        # Writer = AniWriter(fps=20, bitrate=7500, codec="h264", extra_args=['-pix_fmt','yuv420p'])
        # Writer = AniWriter(fps=20, bitrate=10000, codec="h264")
        from matplotlib.animation import FFMpegFileWriter as AniWriter
        Writer = AniWriter(fps=fps, codec="h264", bitrate=-1)
        mpl.rcParams['animation.ffmpeg_path'] = "/usr/bin/ffmpeg"

    # image
    ax.set_aspect('equal')
    frame = dlc.get_frame(Vid, ix[0])
    im = ax.imshow(frame, cmap='gray')

    # body parts
    bp_left = [bp for bp in bodyparts if bp.endswith('L')]
    bp_right = [bp for bp in bodyparts if bp.endswith('R')]
    c_l = sns.color_palette('viridis', n_colors=len(bp_left))
    c_r = sns.color_palette('magma', n_colors=len(bp_right))
    bp_cols = dict(zip(bp_left+bp_right,c_l+c_r))

    bp_markers = []
    for i, bp in enumerate(bodyparts):
        marker, = ax.plot([],[], 'o', color=bp_cols[bp], markersize=10)
        bp_markers.append(marker)

    # traces
    from matplotlib.collections import LineCollection
    n_segments = 10
    trace_len = 3
    lws = sp.linspace(0,5,n_segments)
    bp_traces = []
    for i, bp in enumerate(bodyparts):
        segments = []
        for j in range(n_segments):
            segment = sp.zeros((trace_len,2))
            segments.append(segment)
        
        lc = LineCollection(sp.array(segments),linewidths=lws,color=bp_cols[bp], alpha=0.75)
        bp_traces.append(lc)
        ax.add_artist(lc)
    p = 0.0

    # frame text
    inactive_color = 'white'
    frame_counter = ax.text(5, frame.shape[0]-25, '', color=inactive_color)
    time_counter = ax.text(5, frame.shape[0]-5, '', color=inactive_color)

    # event text annotations
    # color setup
    c = sns.color_palette('husl', n_colors=len(display_events))
    event_colors = dict(zip(display_events,c))
    event_display_dur = 50 # ms

    event_texts = []
    event_times = []
    for i, event in enumerate(display_events):
        # times 
        try:
            times = LogDfSlice.groupby('name').get_group(event)['t'].values
        except KeyError:
            times = [np.nan]
        event_times.append(times)

        # plot
        # bg_text = ax.text(10, i*20 + 20, event, color='black', fontweight='heavy', fontsize=6)
        text = ax.text(10, i*20 + 20, event, color=inactive_color, fontweight='heavy', fontsize=6)
        event_texts.append(text)

    fig.tight_layout()

    # the animation function
    def update(i):
        Frame = dlc.get_frame(Vid,i)
        im.set_data(Frame)

        # frame counter
        frame_counter.set_text("frame: %i - %i/%i" % (i, ix.index(i),len(ix)))
        t_abs = Sync.convert(i,'dlc','arduino') / 1000
        m = Sync.pairs[('dlc','arduino')][0]
        t_rel = (ix.index(i) * m) / 1000
        time_counter.set_text("time: %.2f - %.2f/%.2f" % (t_abs, t_rel,len(ix)*m/1000))

        # body parts
        for j, bp in enumerate(bodyparts):
            data = DlcDfSlice[bp].loc[i]
            if data['likelihood'] > p:
                bp_markers[j].set_data(data['x'], data['y'])
            else:
                bp_markers[j].set_data(sp.nan, sp.nan)
        
        # trace
        for j, bp in enumerate(bodyparts):
            i0 = i - n_segments*trace_len
            data = DlcDfSlice[bp].loc[i0:i]
            data.loc[data['likelihood'] < p] = sp.nan
            data = data[['x','y']].values[::-1,:]
            segments = bp_traces[j].get_segments()
            for k in range(n_segments):
                try:
                    segments[-k] = data[k*trace_len-5:(k+1)*trace_len+5,:]
                except:
                    pass
            bp_traces[j].set_segments(segments)

        for j, event in enumerate(display_events):
            t = Sync.convert(i, 'dlc', 'arduino')
            if sp.any(sp.logical_and(t > event_times[j], t < event_times[j] + event_display_dur)):
                event_texts[j].set_color(event_colors[event])
            else:
                event_texts[j].set_color(inactive_color)

        return (im, frame_counter, time_counter) + tuple(bp_markers) + tuple(bp_traces) + tuple(event_texts)

    ani = FuncAnimation(fig, update, frames=ix, blit=True, interval=1)
    if save is not None:
        utils.printer("saving video to %s" % save, 'msg')
        ani.save(save, writer=Writer)
        plt.close(fig)

# %%
# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right'))
SessionDf.loc[SessionDf['choice_rt'] < 500]
TrialDf = TrialDfs[25] # 1 ms choice RT

Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','CHOICE_EVENT')
t_on = Df.iloc[0]['t'] - 250
t_off = Df.iloc[-1]['t'] + 2000

make_annotated_video(Vid, t_on, t_off, LogDf, DlcDf)

# %% slice entire video
from Utils import utils
for i, row in SessionDf.iloc[:3].iterrows():
    utils.printer("slicing video: Trial %i/%i" % (i, SessionDf.shape[0]))

    TrialDf = TrialDfs[i]
    outpath = session_folder / 'plots' / 'video_sliced'
    os.makedirs(outpath, exist_ok=True)
    try:
        Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','ITI_STATE')

        t_on = Df.iloc[0]['t'] - 250
        t_off = Df.iloc[-1]['t'] + 2000
        side = row['correct_side']
        outcome = row['outcome']
        fname = outpath / ("Trial_%i_%s_%s.mp4" % (i, side, outcome))
        make_annotated_video(Vid, t_on, t_off, LogDf, DlcDf, fps=10, save=fname)
    except IndexError:
        utils.printer("not able to process trial %i" % i,'error')


"""
 
  #######  ########  ######## ##    ##  ######  ##     ## 
 ##     ## ##     ## ##       ###   ## ##    ## ##     ## 
 ##     ## ##     ## ##       ####  ## ##       ##     ## 
 ##     ## ########  ######   ## ## ## ##       ##     ## 
 ##     ## ##        ##       ##  #### ##        ##   ##  
 ##     ## ##        ##       ##   ### ##    ##   ## ##   
  #######  ##        ######## ##    ##  ######     ###    
 
"""
# %% testings: opencv based video vis

# helpers
def rgb2bgr(color):
    """ input: rgb, array or tuple or list, scale 0 - 1
    ouput: opencv style  """
    r,g,b = (np.array(color) * 255).astype('uint8')
    color = [int(c) for c in (b,g,r)]
    return color

# %%
# trial selection
SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right'))
TrialDf = TrialDfs[33]

Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','CHOICE_STATE')
t_on = Df.iloc[0]['t']  - 250
t_off = Df.iloc[-1]['t'] + 5000

# %%
def make_annotated_video_cv2(Vid, t_on, t_off, LogDf, DlcDf, fps, outpath):

    # get respective slices of the data
    g = 32 # grace period to avoid slicing beyond frame limits
    LogDfSlice = bhv.time_slice(LogDf, t_on-g, t_off+g)
    DlcDfSlice = bhv.time_slice(DlcDf, t_on-g, t_off+g)

    # get the closest frames, indices and times
    frame_on = np.argmin((DlcDf['t'].values - t_on)**2)
    frame_off = np.argmin((DlcDf['t'].values - t_off)**2)

    frame_ix = list(range(frame_on, frame_off))
    frame_t = [DlcDf.loc[ix]['t'].values[0] for ix in frame_ix]

    Frames = []
    for i, ix in enumerate(tqdm(frame_ix)):
        Frames.append(dlc.get_frame(Vid, ix))

    ## dlc body parts
    radius = 2

    bp_left = [bp for bp in bodyparts if bp.endswith('L')]
    bp_right = [bp for bp in bodyparts if bp.endswith('R')]
    c_l = sns.color_palette('viridis', n_colors=len(bp_left))
    c_r = sns.color_palette('magma', n_colors=len(bp_right))
    bp_cols = dict(zip(bp_left+bp_right,c_l+c_r))
    for bp in bodyparts:
        bp_cols[bp] = rgb2bgr(bp_cols[bp])

    ## for traces
    n_segments = 25 # in Frames
    w_start = 1
    w_stop = 6
    ws = np.linspace(w_start,w_stop,n_segments)

    ## for event text
    inactive_color = (255,255,255)

    ## event text annotations
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 0.5
    spacing = 15

    # what events to display
    # display_events = list(LogDfSlice.name.unique())
    dppath = "/home/georg/code/TaskControl/analysis/dlc_video/display_events.ini"
    with open(dppath,'r') as fH:
        lines = [line.strip().split(', ') for line in fH.readlines() if line is not '\n']
        display_events = [line[0] for line in lines]
        event_locations = [line[1] for line in lines]

    # display_events = ['TRIAL_AVAILABLE_EVENT','TRIAL_ENTRY_EVENT',
    #                     'CHOICE_EVENT', 'GO_CUE_SHORT_EVENT', 'GO_CUE_LONG_EVENT',
    #                     'CHOICE_CORRECT_EVENT', 'CHOICE_INCORRECT_EVENT',
    #                     'REWARD_LEFT_EVENT','REWARD_RIGHT_EVENT',
    #                     'REACH_LEFT_ON', 'REACH_LEFT_OFF', 'REACH_RIGHT_ON', 'REACH_RIGHT_OFF']

    # if sp.nan in display_events:
    #     display_events.remove(np.nan)

    # color setup
    c = sns.color_palette('husl', n_colors=len(display_events))
    event_colors = dict(zip(display_events,c))
    event_display_dur = 250 # ms
    for event in event_colors.keys():
        event_colors[event] = rgb2bgr(event_colors[event])

    # extract times
    event_texts = []
    event_times = []
    event_text_pos = {}

    image_h, image_w = Frames[0].shape # h = x , w = y 

    for i, event in enumerate(display_events):
        # times 
        try:
            times = LogDfSlice.groupby('name').get_group(event)['t'].values
        except KeyError:
            times = [np.nan]
        event_times.append(times)


    i_left = 0
    i_right = 0
    i_center = 0

    for i, event in enumerate(display_events):
        # text positions
        text_w, text_h = cv2.getTextSize(event, font, fontScale, 1)[0] # in pixels
        
        if event_locations[i] == 'left':
            text_y = image_h - (i_left*text_h*1.5 + text_h)
            text_x = image_w - text_h*1.5 - text_w
            i_left += 1

        if event_locations[i] == 'right':
            text_y = image_h - (i_right*text_h*1.5 + text_h)
            text_x = text_h*1.5
            i_right += 1

        if event_locations[i] == 'center':
            text_y = image_h - (i_center*text_h*1.5 + text_h)
            text_x = image_w/2 - text_w/2
            i_center += 1
        
        event_text_pos[event] = (int(text_x), int(text_y))

    # opencv setup
    h, w = Frames[0].shape
    codec = cv2.VideoWriter_fourcc(*'mp4v')
    # out = cv2.VideoWriter('/home/georg/testout.mp4', codec, fps, (w, h), isColor=True)
    out = cv2.VideoWriter(str(outpath), codec, fps, (image_w, image_h), isColor=True)

    for i, ix in enumerate(frame_ix):

        frame = Frames[i][:,:,np.newaxis].repeat(3,axis=2) # convert to color

        # markers
        # for bp in bodyparts:
        #     data = DlcDfSlice[bp].loc[ix]
        #     pos = tuple(np.array((data['x'], data['y'])).astype('int32'))
        #     cv2.circle(frame, pos, radius, bp_cols[bp], cv2.LINE_AA)

        # past lines
        # ix0 = ix-n_segments
        # for bp in bodyparts:
        #     data = DlcDf[bp].loc[ix0:ix][['x', 'y']].values.astype('uint32')
        #     data[:,0] = data[:,0].clip(0, h)
        #     data[:,1] = data[:,1].clip(0, w)
        #     for j in range(1, n_segments):
        #         cv2.line(frame, tuple(data[j-1,:]), tuple(data[j,:]), bp_cols[bp], int(ws[j]), cv2.LINE_AA)

        # event text
        for j, event in enumerate(display_events):
            t = frame_t[i]
            try:
                if sp.any(sp.logical_and(t > event_times[j], t < (event_times[j] + event_display_dur))):
                    color = event_colors[event]
                else:
                    color = inactive_color
            except TypeError:
                # thrown when event never happens
                color = inactive_color

            pos = event_text_pos[event]
            # pos = (10, h-int(j*spacing + spacing))
            cv2.putText(frame, event, pos, font, fontScale, color)

        out.write(frame)

    out.release()

# %% play video
cap = cv2.VideoCapture('/home/georg/testout.mp4')
fps = 10
t_last = 0
import time
i = 0

while(cap.isOpened()):
    dt = time.time() - t_last
    ret, frame = cap.read()

    if dt > 1./fps:
        print('ho')
        t_last = time.time()

        # cv2.imshow('Frame',frame)
            # if cv2.waitKey(25) & 0xFF == ord('q'):
            #     break
    
    i = i +1
    if i > 100:
        break

cap.release()

# %%

# %% slice  video
from Utils import utils
fps = 60/4

SDf = bhv.intersect(SessionDf, has_choice=True, correct_side='left')
N = 8
j = 1
for i, row in SDf[:N].iterrows():
    ix = row.name
    utils.printer("slicing video: Trial %i - %i/%i" % (ix, j, N))

    TrialDf = TrialDfs[ix]
    outpath = session_folder / 'plots' / 'video_sliced'
    os.makedirs(outpath, exist_ok=True)
    try:
        Df = bhv.event_slice(TrialDf,'TRIAL_ENTRY_EVENT','ITI_STATE')

        t_on = Df.iloc[0]['t'] - 250
        t_off = Df.iloc[-1]['t'] + 1000
        side = row['correct_side']
        outcome = row['outcome']
        fname = outpath / ("Trial_%i_%s_%s.mp4" % (ix, side, outcome))
        make_annotated_video_cv2(Vid, t_on, t_off, LogDf, DlcDf, fps, fname)
    except IndexError:
        utils.printer("not able to process trial %i" % ix,'error')
    j += 1

# %%


"""
 
    ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
   ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
  ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
 ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""
    
# %%

"""
 
 ######## ##     ## ######## ########     ###    ########  ####  ######  ########    ########  ########    ###     ######  ##     ## ########  ######  
    ##    ##     ## ##       ##     ##   ## ##   ##     ##  ##  ##    ##    ##       ##     ## ##         ## ##   ##    ## ##     ## ##       ##    ## 
    ##    ##     ## ##       ##     ##  ##   ##  ##     ##  ##  ##          ##       ##     ## ##        ##   ##  ##       ##     ## ##       ##       
    ##    ######### ######   ########  ##     ## ########   ##   ######     ##       ########  ######   ##     ## ##       ######### ######    ######  
    ##    ##     ## ##       ##   ##   ######### ##         ##        ##    ##       ##   ##   ##       ######### ##       ##     ## ##             ## 
    ##    ##     ## ##       ##    ##  ##     ## ##         ##  ##    ##    ##       ##    ##  ##       ##     ## ##    ## ##     ## ##       ##    ## 
    ##    ##     ## ######## ##     ## ##     ## ##        ####  ######     ##       ##     ## ######## ##     ##  ######  ##     ## ########  ######  
 
"""

