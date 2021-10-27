# %% imports 
%matplotlib qt5
%load_ext autoreload
%autoreload 2

import sys
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

sys.path.append('..')
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
session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-15_14-15-36_learn_to_choose_v2")

# poolboy starting to go down
# session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-18_12-32-41_learn_to_choose_v2")

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
cam_sync_event = sync.parse_cam_sync(session_folder / 'bonsai_frame_stamps.csv')
# lc_sync_event = sync.parse_harp_sync(session_folder / 'bonsai_harp_sync.csv')
arduino_sync_event = sync.get_arduino_sync(session_folder / 'arduino_log.txt')

Sync = Syncer()
Sync.data['arduino'] = arduino_sync_event['t'].values
# Sync.data['loadcell'] = lc_sync_event['t'].values
Sync.data['dlc'] = cam_sync_event.index.values # the frames are the DLC
Sync.data['cam'] = cam_sync_event['t'].values # used for what?
Sync.sync('arduino','dlc')
Sync.sync('arduino','cam')

DlcDf['t'] = Sync.convert(DlcDf.index.values, 'dlc', 'arduino')

# %% Dlc processing
# speed
for i,bp in enumerate(tqdm(bodyparts)):
    Vxy = sp.diff(DlcDf[bp][['x','y']].values,axis=0) / DlcDf['t'][:-1].values[:,sp.newaxis]
    V = sp.sqrt(sp.sum(Vxy**2,axis=1)) # euclid vector norm
    V = V / sp.diff(DlcDf['t'].values) # -> to speed
    V = sp.concatenate([[sp.nan],V]) # pad first to nan (speed undefined)
    DlcDf[(bp,'v')] = V

# %% analysis of too fast movements
fig, axes = plt.subplots()
for bp in bodyparts:
    V = DlcDf[(bp,'v')]
    tvec = DlcDf['t']
    axes.plot(tvec, V, label=[bp])

sides = ['left','right']
for side in sides:
    reach_times = LogDf.groupby('name').get_group("REACH_%s_ON" % side.upper())['t'].values
    for t in reach_times:
        axes.axvline(t, color=colors[side], alpha=0.5, lw=1)

axes.legend()

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
p = 0.99
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
frame_ix = Sync.convert(t_on, 'arduino', 'dlc')
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
    frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
    dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes, markersize=5)

    # the trajectory
    DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
    dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=axes, lw=0.75, alpha=0.75, p=0.8)


# %% make an outcome / sides panel with the trajectories
outcomes = ['correct','incorrect','missed']
sides = ['left','right']

fig, axes = plt.subplots(ncols=len(outcomes),nrows=len(sides))

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
            frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
            dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=ax, markersize=5)

            # the trajectory
            DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
            dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=ax, lw=0.75, alpha=0.5, p=0.8)

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

            dlc.plot_frame(frame, axes=axes[j,i])
            plot_all_trajectories(TrialDfs_sel, ax=axes[j,i])
        except KeyError:
            pass

for ax in axes.flatten():
    ax.set_aspect('equal')
    ax.set_xticklabels('')
    ax.set_yticklabels('')

for i, ax in enumerate(axes[0,:]):
    ax.set_title(outcomes[i])

for i, ax in enumerate(axes[:,0]):
    ax.set_ylabel(sides[i])

fig.suptitle('reach trajectories split by outcome/side')
fig.tight_layout()
fig.subplots_adjust(top=0.85)


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
TrialDf = TrialDfs[22] # 1 ms choice RT

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
 
    ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
   ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
  ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
 ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""
# %% analysis - categorizing reaching patterns
# idea - Kmeans over reaches
def groupby(Df, **kwargs):
    if len(kwargs) == 1:
        return Df.groupby(list(kwargs.keys())[0]).get_group(tuple(kwargs.values())[0])
    else:
        return Df.groupby(list(kwargs.keys())).get_group(tuple(kwargs.values()))

SDf = groupby(SessionDf, has_choice=True, outcome='correct') # as a start, ideally no grouping

# %%
# bhv.event_based_time_slice(LogDf, "GRASP_ON", 1, 1, Df_to_slice=DlcDf)

Df = pd.concat([bhv.get_events_from_name(LogDf, "GRASP_LEFT_ON"),bhv.get_events_from_name(LogDf, "GRASP_RIGHT_ON")])
Df = Df.sort_values('t')

pre, post = -500,500
Reaches = []
for i,t in enumerate(Df['t'].values):
    Reaches.append(bhv.time_slice(DlcDf, t+pre, t+post))

# %%
# M = []
# good_inds = []
# for i in range(len(Reaches)):
#     R_left = Reaches[i]['PAW_L'][['x','y']].values.T.flatten()
#     R_right = Reaches[i]['PAW_R'][['x','y']].values.T.flatten()
#     if R_left.shape == R_right.shape:
#         M.append(np.concatenate([R_left,R_right],0))
#         good_inds.append(i)

M = []
for i in range(len(Reaches)):
    R_left = Reaches[i]['PAW_L'][['x','y']].values.T.flatten()
    R_right = Reaches[i]['PAW_R'][['x','y']].values.T.flatten()
    M.append(np.concatenate([R_left,R_right],0))

# %% filter by most common shapes
n_samples = np.median([m.shape[0] for m in M])
good_inds = [i for i in range(len(M)) if M[i].shape[0] == n_samples]
M = [m[:,np.newaxis] for m in M if m.shape[0] == int(n_samples)]
M = np.concatenate(M, axis=1)

# %%
fig, axes = plt.subplots()
axes.matshow(M)
axes.set_aspect('auto')

# %%
from sklearn.cluster import KMeans
clust = KMeans(n_clusters=6).fit(M.T)
clust.labels_

# %%
R = []
for i in good_inds:
    R.append(Reaches[i])

# %%
colors = sns.color_palette('tab10', n_colors=6)

frame_ix = 5000
frame = dlc.get_frame(Vid, frame_ix)

fig, axes = plt.subplots(ncols=2)
dlc.plot_frame(frame, axes=axes[0])
dlc.plot_frame(frame, axes=axes[1])

for i, r in enumerate(R):
    Left = r['PAW_L'][['x','y']].values
    axes[0].plot(Left[:,0], Left[:,1], color=colors[clust.labels_[i]])

    Right = r['PAW_R'][['x','y']].values
    axes[1].plot(Right[:,0], Right[:,1], color=colors[clust.labels_[i]])

for ax in axes:
    ax.set_aspect('equal')


# %% another analysis - reach distances to spouts - all to all

# calculate all distances
sides = ['left','right']
spout_coords = dict(left=[376,283], right=[276, 275])
for bp in bodyparts:
    for side in sides:
        D = dlc.calc_dist_bp_point(DlcDf, bp, spout_coords[side], filter=True)
        DlcDf[(bp),'%s_to_%s' % (bp, 'spout_'+side)] = D

# %%
Df = LogDf # all data
# %% preselect trials by type
ix = SessionDf.groupby('outcome').get_group('incorrect').index
Df = pd.concat([TrialDfs[i] for i in ix],axis=0)
Df = Df.reset_index(drop=True)

# %%
Grasp_events = dict(left=bhv.get_events_from_name(Df, "GRASP_LEFT_ON"), right=bhv.get_events_from_name(Df, "GRASP_RIGHT_ON"))
pre, post = -2000,500

Grasp_data = {}
for side in sides:
    Grasp_data[side] = []

    for i,t in enumerate(Grasp_events[side]['t'].values):
        Grasp_data[side].append(bhv.time_slice(DlcDf, t+pre, t+post))

# %% get median number of samples
for side in sides:
    n_samples = int(np.median([reach.shape[0] for reach in Grasp_data[side]]))
    good_inds = [i for i in range(len(Grasp_data[side])) if Grasp_data[side][i].shape[0] == n_samples]
    Grasp_data[side] = [Grasp_data[side][i] for i in good_inds]

# %% grid plot all to all
tvec = np.linspace(pre,post,n_samples)

for i, side in enumerate(sides):
    fig, axes = plt.subplots(nrows=2,ncols=2,sharey=True, figsize=[9,9])
    fig.suptitle('grasp to %s' % side)

    for m, side_m in enumerate(sides): # over paws
        for n, side_n in enumerate(sides): # over spouts
            paw = 'PAW_%s' % side_m[0].upper()
            index_tup = (paw, '%s_to_spout_%s' % (paw, side_n))

            reach_avg = []
            for reach in Grasp_data[side]:
                d = reach[index_tup]
                reach_avg.append(d)
                axes[m, n].plot(tvec, d, alpha=0.8)

            reach_avg = np.array(reach_avg)
            avg = np.nanmedian(reach_avg,axis=0)
            axes[m, n].plot(tvec, avg, color='k', lw=2)

    for ax, label in zip(axes[0,:],  sides):
        ax.set_title('dist to spout ' + label)

    for ax, label in zip(axes[:,0], sides):
        ax.set_ylabel('paw ' + label)

    for ax in axes.flatten():
        ax.axvline(0, linestyle=':', color='k', lw=0.5)
        ax.axhline(0, linestyle=':', color='k', lw=0.5)

    for ax in axes[-1,:]:
        ax.set_xlabel('time (ms)')

    sns.despine(fig)
    fig.tight_layout()
    fig.subplots_adjust(top=0.90)


# %%

# # %%
# """
 
#  ########  #######  ########           ##  #######  ########  ######     ########  ######## ########   #######  ########  ######## 
#  ##       ##     ## ##     ##          ## ##     ## ##       ##    ##    ##     ## ##       ##     ## ##     ## ##     ##    ##    
#  ##       ##     ## ##     ##          ## ##     ## ##       ##          ##     ## ##       ##     ## ##     ## ##     ##    ##    
#  ######   ##     ## ########           ## ##     ## ######    ######     ########  ######   ########  ##     ## ########     ##    
#  ##       ##     ## ##   ##      ##    ## ##     ## ##             ##    ##   ##   ##       ##        ##     ## ##   ##      ##    
#  ##       ##     ## ##    ##     ##    ## ##     ## ##       ##    ##    ##    ##  ##       ##        ##     ## ##    ##     ##    
#  ##        #######  ##     ##     ######   #######  ########  ######     ##     ## ######## ##         #######  ##     ##    ##    
 
# """

# # %% 2x3 panel with reaches, plotted trajectory from start to choice

# # trial selection


# # %% static image with trajectory between t_on and t_off

# bp_cols = make_bodypart_colors(bodyparts)
# fig, axes = plt.subplots(nrows=2, ncols=3, sharex=True, sharey=True, figsize=[9,5])

# # short
# SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='left'))
# TrialDf = TrialDfs[SDf.index[9]] # good left reach
# Df = bhv.event_slice(TrialDf, 'PRESENT_INTERVAL_STATE', 'CHOICE_EVENT')
# t_on = Df.iloc[0]['t']
# t_off = Df.iloc[-1]['t']

# fs = [0.5,0.95,1]
# ts = [t_on + ((t_off-t_on) * f) for f in fs]
# vmin, vmax = 0, 220
# for i,f in enumerate(fs):
#     ax = axes[0,i]
#     t = ts[i]
#     frame_ix = Sync.convert(t, 'arduino', 'dlc')
#     frame = dlc.get_frame(Vid, frame_ix)
#     dlc.plot_frame(frame, axes=ax, vmin=vmin, vmax=vmax)
#     dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=ax)
#     DlcDfSlice = bhv.time_slice(DlcDf, t_min=ts[0], t_max=t)
#     dlc.plot_trajectories(DlcDfSlice, bodyparts, axes=ax, colors=bp_cols, lw=1.5, alpha=0.8, p=0.99)

# # long
# SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right'))
# TrialDf = TrialDfs[SDf.index[4]] # good long from resting
# Df = bhv.event_slice(TrialDf, 'PRESENT_INTERVAL_STATE', 'CHOICE_EVENT')
# t_on = Df.iloc[0]['t']
# t_off = Df.iloc[-1]['t']

# fs = [0.5,0.965,1]
# ts = [t_on + ((t_off-t_on) * f) for f in fs]
# for i,f in enumerate(fs):
#     ax = axes[1,i]
#     t = ts[i]
#     frame_ix = Sync.convert(t, 'arduino', 'dlc')
#     frame = dlc.get_frame(Vid, frame_ix)
#     dlc.plot_frame(frame, axes=ax, vmin=vmin, vmax=vmax)
#     dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=ax)
#     DlcDfSlice = bhv.time_slice(DlcDf, t_min=ts[0], t_max=t)
#     dlc.plot_trajectories(DlcDfSlice, bodyparts, axes=ax, colors=bp_cols, lw=1.5, alpha=0.8, p=0.99)

# for ax in axes.flatten():
#     ax.set_xticklabels([])
#     ax.set_yticklabels([])

# axes[0,0].set_ylabel("short")
# axes[1,0].set_ylabel("long")

# os.chdir('/home/georg/Desktop/plots')
# fig.tight_layout()
# fig.savefig('reach_panel_for_joe.png',dpi=600)
# # %%
# frame_ix = Sync.convert( t_on + ((t_off-t_on) * 0.85), 'arduino', 'dlc')
# frame = dlc.get_frame(Vid, frame_ix)
# dlc.plot_frame(frame, axes=axes[0,1])
# dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes)

# frame_ix = Sync.convert(t_off, 'arduino', 'dlc')
# frame = dlc.get_frame(Vid, frame_ix)
# dlc.plot_frame(frame, axes=axes[0,2])
# dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes)

# # trajectory
# # DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
# # dlc.plot_trajectories(DlcDfSlice, bodyparts, axes=axes, colors=bp_cols, lw=1, p=0.99)

# # %% plot all of the selected trial type
# # trial selection
# # SDf = bhv.groupby_dict(SessionDf, dict(outcome='correct', correct_side='right', paw_resting=False))
# SDf = bhv.groupby_dict(SessionDf, dict(has_choice=True, correct_side='left', outcome='correct'))
# # SDf = SDf.sample(10)

# # plot some random frame
# fig, axes = plt.subplots()
# frame_ix = 1000
# frame = dlc.get_frame(Vid, frame_ix)
# dlc.plot_frame(frame, axes=axes)

# # plot all traj in selection
# for i in tqdm(SDf.index):
#     TrialDf = TrialDfs[i]
#     Df = bhv.event_slice(TrialDf,'PRESENT_INTERVAL_STATE','CHOICE_EVENT')
#     # Df = bhv.time_slice(Df, Df.iloc[-1]['t']-500, Df.iloc[-1]['t'])
#     t_on = Df.iloc[0]['t']
#     t_off = Df.iloc[-1]['t']

#     # trial by trial colors
#     bp_cols = {}
#     cmaps = dict(zip(bodyparts,['viridis','magma']))
#     for bp in bodyparts:
#         c = sns.color_palette(cmaps[bp],as_cmap=True)(sp.rand())
#         bp_cols[bp] = c

#     # marker for the start
#     # frame_ix = dlc.time2frame(t_on, m, b, m2, b2)
#     frame_ix = Sync.convert(t_on, 'arduino', 'dlc').round().astype('int')
#     dlc.plot_bodyparts(bodyparts, DlcDf, frame_ix, colors=bp_cols, axes=axes, markersize=5)

#     # the trajectory
#     DlcDfSlice = bhv.time_slice(DlcDf, t_on, t_off)
#     dlc.plot_trajectories(DlcDfSlice, bodyparts, colors=bp_cols, axes=axes, lw=0.75, alpha=0.75, p=0.8)
    
# %%
