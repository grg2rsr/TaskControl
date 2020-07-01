# %matplotlib qt5
# %load_ext autoreload
# %autoreload 2

from matplotlib import pyplot as plt
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import seaborn as sns
from tqdm import tqdm
import os

"""
 
 ########  ##        #######  ######## ######## ######## ########   ######  
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##    ## 
 ##     ## ##       ##     ##    ##       ##    ##       ##     ## ##       
 ########  ##       ##     ##    ##       ##    ######   ########   ######  
 ##        ##       ##     ##    ##       ##    ##       ##   ##         ## 
 ##        ##       ##     ##    ##       ##    ##       ##    ##  ##    ## 
 ##        ########  #######     ##       ##    ######## ##     ##  ######  
 
"""
def plot_session_overview(LogDf, t_ref, pre, post, axes=None, how='dots',cdict=None):
    """ plots a session overview """

    if axes is None:
        axes = plt.gca()

    if cdict is None:
        #implement
        pass

    for i,t in enumerate(tqdm(t_ref)):
        Df = bhv.time_slice(LogDf,t+pre,t+post,'t')

        for name,group in Df.groupby('name'):
            # plot events
            if name.endswith("_EVENT"):
                event_name = name.split("_EVENT")[0]
                times = group['t'] - t
                
                if how == 'dots':
                    axes.plot(times, [i]*len(times), '.', color=cdict[event_name], alpha=0.75) # a bar
                
                if how == 'bars':
                    for time in times:
                        axes.plot([time,time],[i-0.5,i+0.5],lw=2,color=cdict[event_name], alpha=0.75) # a bar
            
            # plot spans
            if name.endswith("_ON") and name != "LICK_ON": # special case: exclude licks
                span_name = name.split("_ON")[0]
                # Df_sliced = bhv.log2Span(Df, span_name)
                # Df_sliced = bhv.spans_from_event_names(Df, span_name+'_ON', span_name+'_OFF')
                on_name = span_name + '_ON'
                off_name = span_name + '_OFF'
                SpansDf = bhv.get_spans_from_event_names(Df, on_name, off_name)
                for j, row_s in SpansDf.iterrows():
                    time = row_s['t_on'] - t
                    dur = row_s['dt']
                    rect = plt.Rectangle((time,i-0.5), dur, 1, facecolor=cdict[span_name], linewidth=2)
                    axes.add_patch(rect)


    for key in cdict.keys():
        axes.plot([0],[0],color=cdict[key],label=key,lw=4)
    axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',ncol=3, mode="expand", borderaxespad=0.,fontsize='xx-small')
    axes.invert_yaxis()
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('trials')

    return axes

def plot_psth(EventsDf, t_ref, bins=None, axes=None, how='fill', **kwargs):
    """ plots a psth of the event in EventDf on the axis """
    if axes is None:
        axes = plt.gca()

    pre, post = bins[0], bins[-1]

    # bins = sp.zeros(bins.shape)

    values = []
    for t in t_ref:
        times = bhv.time_slice(EventsDf, t+pre, t+post)['t'] - t
        values.append(times.values)
    values = sp.concatenate(values)

    if how is 'steps':
        counts, bins = sp.histogram(values,bins=bins)
        axes.step(bins[1:], counts, **kwargs)
    if how is 'fill':
        axes.hist(values,bins=bins,**kwargs)
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('count')

    return axes

def plot_raster(EventsDf, t_ref, pre, post, axes=None, **kwargs):
    """ simple raster plot """
    if axes is None:
        axes = plt.gca()

    for i,t in enumerate(t_ref):
        times = bhv.time_slice(EventsDf, t+pre, t+post)['t'] - t
        axes.plot(times, sp.ones(times.shape[0])*i,'.',color='k')

    return axes

def plot_success_rate(SessionDf, history=None, axes=None):
    """ plots success rate, if history given includes a rolling smooth """
    if axes is None:
        axes = plt.gca()

    x = SessionDf.index.values+1
    
    # plot raw as markers
    axes.plot(x,SessionDf['successful'],'.',alpha=0.25,color='k')
    
    # grand average rate
    y = sp.cumsum(SessionDf['successful'].values) / (SessionDf.index.values+1)
    axes.plot(x,y, color='C3')
    
    if history is not None:
        y_filt = SessionDf['successful'].rolling(history).mean()
        axes.plot(x,y_filt, color='C3',alpha=0.5)
    
    axes.set_ylabel('frac. successful')
    axes.set_xlabel('trial #')
    axes.set_title('success rate')

    return axes

def plot_reward_collection_rate(SessionDf, history=None, axes=None):
    """ plots success rate, if history given includes a rolling smooth """
    if axes is None:
        axes = plt.gca()

    S = SessionDf.groupby('successful').get_group(True)
    x = S.index.values+1

    # grand average rate
    y = sp.cumsum(S['reward_collected'].values) / (S.index.values+1)
    axes.plot(x,y, color='C0')

    if history is not None:
        y_filt = S['reward_collected'].rolling(history).mean()
        axes.plot(x,y_filt, color='C0',alpha=0.5)

    axes.set_ylabel('frac. rew collected')
    axes.set_xlabel('trial #')
    axes.set_title('reward collection rate')

    return axes

def plot_reward_collection_RT(SessionDf, bins=None, axes=None, **kwargs):
    """ """
    if axes is None:
        axes = plt.gca()
    
    values = SessionDf.groupby('reward_collected').get_group(True)['reward_collected_rt'].values
    
    if bins is None:
        bins = sp.arange(0,values.max(),25)
    
    axes.hist(values,bins=bins, **kwargs)
    # counts, bins = sp.histogram(values,bins=bins)
    # axes.step(bins[1:], counts, color='r')
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('count')
    axes.set_title('reward collection RT')

    return axes

def plot_lc_forces_heatmaps(LogDf, LoadCellDf, align_reference, pre, post, axes=None, **kwargs):

    event_times = bhv.get_events_from_name(LogDf, align_reference)

    Fx = []
    Fy = []
    for t in event_times['t']:
        F = bhv.time_slice(LoadCellDf,t+pre,t+post)
        Fx.append(F['x'])
        Fy.append(F['y'])

    Fx = np.array(Fx)
    Fy = np.array(Fy)

    force_tresh = 1500

    fig, axes = plt.subplots(ncols=2, sharex=True, sharey=True)
    heat1 = axes[0].matshow(Fx,cmap='PiYG',vmin=-force_tresh,vmax=force_tresh,alpha =0.75)
    heat2 = axes[1].matshow(Fy,cmap='PiYG',vmin=-force_tresh,vmax=force_tresh,alpha =0.75)

    # Ticks in seconds
    plt.setp(axes, xticks=np.arange(pre, post+1, 500), xticklabels=np.arange(pre//1000, (post//1000)+0.5, 0.5))

    # Labels, title and formatting
    axes[0].set_title('Forces in X axis')
    cbar = plt.colorbar(heat1, ax=axes[0], orientation='horizontal')
    cbar.set_ticks([-force_tresh, force_tresh]); cbar.set_ticklabels(["Left","Right"])

    axes[1].set_title('Forces in Y axis')
    cbar = plt.colorbar(heat2, ax=axes[1], orientation='horizontal')
    cbar.set_ticks([-force_tresh, force_tresh]); cbar.set_ticklabels(["Down","Up"])

    ' Plotting black tick marks signalling whatever the input HARDCODED RIGHT NOW '
    correct_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_CORRECT')
    incorrect_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_INCORRECT')

    choice_times = correct_choiceDf.append(incorrect_choiceDf).sort_index(axis = 0)
    choice_times = choice_times.to_numpy() - event_times.to_numpy() - pre # Since Pre starts at -1s

    ymin = np.arange(-0.5,len(choice_times)) # need to shift since line starts at center of trial
    ymax = np.arange(0.5,len(choice_times)+1)

    axes[0].vlines(choice_times, ymin, ymax, colors='black')
    axes[1].vlines(choice_times, ymin, ymax, colors='black')

    plt.xlabel('Time (s)')
    plt.ylabel('Trials')

    for ax in axes:
        ax.set_aspect('auto')

"""
 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ###   ## ##    ## 
 ##       ##       ##       ##        ##  ##     ## ####  ## ##       
  ######  ######    ######   ######   ##  ##     ## ## ## ##  ######  
       ## ##             ##       ##  ##  ##     ## ##  ####       ## 
 ##    ## ##       ##    ## ##    ##  ##  ##     ## ##   ### ##    ## 
  ######  ########  ######   ######  ####  #######  ##    ##  ######  
 
"""

def plot_sessions_overview(LogDfs, task_name, axes=None):

    if axes is None:
        axes = plt.gca()

    trials_performed = []
    trials_sucessful = []
    trials_unsucessful = []

    for LogDf in LogDfs:
        # Total number of trials performed
        event_times = bhv.get_events_from_name(LogDf,"SECOND_TIMING_CUE")
        trials_performed.append(len(event_times))

        # Number of sucessful trials 
        correct_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_CORRECT')
        trials_sucessful.append(len(correct_choiceDf))
        
        # Number of unsucessful trials 
        incorrect_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_INCORRECT')
        trials_unsucessful.append(len(incorrect_choiceDf))

        # Weight
    
    axes.plot(trials_performed, color = 'black', label = 'Performed')
    axes.plot(trials_sucessful, color = 'green', label = 'Sucessful')
    axes.plot(trials_unsucessful, color = 'red', label = 'Unsucessful')
    axes.set_ylabel('Count (#)')
    axes.set_xlabel('Session number')
    axes.set_title('Trial overview across sessions in task:  ' + task_name)
    axes.legend(loc='upper right', frameon=False)   

    return axes