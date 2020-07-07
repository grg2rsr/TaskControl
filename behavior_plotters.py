# %matplotlib qt5
# %load_ext autoreload
# %autoreload 2

from matplotlib import pyplot as plt
from matplotlib import cm 
import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
from pathlib import Path
import scipy as sp
import numpy as np
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

        for name, group in Df.groupby('name'):
            # plot events
            if name.endswith("_EVENT"):
                event_name = name
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
                SpansDf = bhv.get_spans_from_names(Df, on_name, off_name)
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

def plot_forces_heatmaps(LogDf, LoadCellDf, align_reference, tick_reference, pre, post):
    """ Plots heatmaps of LC forces in X/Y axes algined to any event (also marks choice times) """

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

    ' Plotting black tick marks signalling whatever the input '
    choice_timesDf = bhv.get_events_from_name(LogDf,tick_reference)
    choice_times = choice_timesDf.to_numpy() - event_times.to_numpy() - pre # 'pre' used to shift and center the plot at 0s
    choice_times[choice_times > post+995] = np.nan # deal with choice missed events which are registered as 'choices' at [post+1sec]

    #choice_times = correct_choiceDf.append(incorrect_choiceDf).sort_index(axis = 0)
    #choice_times = choice_times.to_numpy() - event_times.to_numpy() 

    ymin = np.arange(-0.5,len(choice_times)) # need to shift since line starts at center of trial
    ymax = np.arange(0.5,len(choice_times)+1)

    axes[0].vlines(choice_times, ymin, ymax, colors='black')
    axes[1].vlines(choice_times, ymin, ymax, colors='black')

    plt.xlabel('Time (s)')
    plt.ylabel('Trials')

    for ax in axes:
        ax.set_aspect('auto')

    return axes

def plot_forces_trajectories(LogDf, LoadCellDf, align_reference, pre, post, no_splits):
    """ Plots trajectories in 2D aligned to any TWO events"""

    axes = plt.subplots(ncols=2,sharex=True,sharey=True)
    colors = cm.RdPu(np.linspace(0, 1, no_splits))

    event_times = bhv.get_events_from_name(LogDf, align_reference[0])

    # 1st dim is number of events, 2nd is window width, 3rd columns of Df (x an y are 3nd and 4th)
    F = []

    for t in event_times['t']:
        trial = bhv.time_slice(LoadCellDf,t+pre,t+post)
        F.append(trial.to_numpy())

    F_split = np.array_split(F,no_splits)

    for chunk, clr in zip(F_split,colors):

        avg_chunk = np.average(chunk,0) # average along trials
        axes[0].plot(avg_chunk[:,1], avg_chunk[:,2], alpha=0.5, lw=1, color = clr)

    event_times = bhv.get_events_from_name(LogDf, align_reference[1])

    # 1st dim is number of events, 2nd is window width, 3rd columns of Df (x an y are 3nd and 4th)
    F = []

    for t in event_times['t']:
        trial = bhv.time_slice(LoadCellDf,t+pre,t+post)
        F.append(trial.to_numpy())

    F_split = np.array_split(F,no_splits)

    for chunk, clr in zip(F_split,colors):

        avg_chunk = np.average(chunk,0) # average along trials
        axes[1].plot(avg_chunk[:,1], avg_chunk[:,2], alpha=0.5, lw=1, color = clr)

    axes[0].set_ylim([-2000,2000])
    axes[1].set_ylim([-2000,2000])
    axes[0].set_xlim([-2000,2000])
    axes[1].set_xlim([-2000,2000])

    return axes

def plot_choice_rt_histogram(LogDf, axes=None):

    if axes is None:
        axes = plt.gca()

    spans = bhv.get_spans_from_names(LogDf, 'TRIAL_ENTRY_EVENT', 'ITI_STATE')
    TrialDfs = []
    for span in spans.iterrows():
        TrialDfs.append(bhv.time_slice(LogDf,span['t_on'],span['t_off']))

    # # Getting a list of trialDfs in which trials are both sucessfull and left choice
    # OurTrialDfs = []
    # for TrialDf in TrialDfs:
    #     if "CHOICE_LEFT_EVENT" in TrialDf.name.values and "TRIAL_SUCCESSFUL_EVENT" in TrialDf.name.values:
    #         OurTrialDfs.append(TrialDf)

    # Getting choice RT's
    left_choice_Dfs, right_choice_Dfs = [],[]
    rt_left_choice, rt_right_choice = [],[]

    for TrialDf in TrialDfs:
        second_cue_time = TrialDf.loc[TrialDf['name'] == 'SECOND_TIMING_CUE_EVENT']['t']

        if "CHOICE_LEFT_EVENT" in TrialDf.name.values:
            left_choice_Dfs.append(TrialDf)
            left_choice_time = TrialDf.loc[TrialDf['name'] == 'CHOICE_LEFT_EVENT']['t']

            rt_left_choice.append(int(left_choice_time.values - second_cue_time.values))

        if "CHOICE_RIGHT_EVENT" in TrialDf.name.values:
            right_choice_Dfs.append(TrialDf)
            right_choice_time = TrialDf.loc[TrialDf['name'] == 'CHOICE_RIGHT_EVENT']['t']

            rt_right_choice.append(int(right_choice_time.values - second_cue_time.values))


    plt.hist(rt_left_choice, 25, range = (0,2000), 
            alpha=0.5, color='red', edgecolor='none', label = 'Left choice')
    plt.hist(rt_right_choice, 25, range = (0,2000), 
            alpha=0.5, color='green', edgecolor='none', label = 'Right choice')
    plt.ylabel('Number of trials')
    plt.xlabel('Reaction time (ms)')

    plt.legend(loc='upper right', frameon=False)

    return axes  

def plot_force_magnitude(LogDf, LoadCellDf, align_reference, pre, post):
    """ Plots the magnitude of the 2D forces vector over the trial aligned to any event """

    event_times = bhv.get_events_from_name(LogDf, align_reference)

    fig, axes = plt.subplots()
    tvec = sp.arange(pre,post,1)

    ys = []
    for t in event_times['t']:
        F = bhv.time_slice(LoadCellDf,t+pre,t+post)
        y = sp.sqrt(F['x']**2+F['y']**2)
        ys.append(y)
        axes.plot(tvec,y,lw=1,alpha=0.5)

    # center
    F['x'] = F['x'] - sp.average(F['x'])
    F['y'] = F['y'] - sp.average(F['y'])

    Fmag = np.array(ys).T
    axes.plot(tvec,sp.average(Fmag,1),'k',lw=3)
    axes.axvline(0, linestyle=':',alpha=0.5)

    return axes

def plot_forces_histogram(LogDf, LoadCellDf, align_reference, pre, post):
    """ Plots the evolution of forces in X/Y axis across the session plus fitted distros """

    event_times = bhv.get_events_from_name(LogDf, align_reference)
    fig = plt.figure()

    Fx = []
    Fy = []
    for t in event_times['t']:
        F = bhv.time_slice(LoadCellDf,t+pre,t+post)
        Fx.append(F['x'])
        Fy.append(F['y'])

    Fx = np.array(Fx)
    Fy = np.array(Fy)

    Fx_split = np.array_split(Fx,10)
    Fy_split = np.array_split(Fy,10)

    colors = cm.RdPu(np.linspace(0, 1, len(Fx_split)))

    # Histograms for Fx and Fy and respective normal distribution fits
    for i, (chunk_x, chunk_y, clr) in enumerate(zip(Fx_split, Fy_split, colors),1):

        ax1 = fig.add_subplot(221)
        _, bins_x, _ = plt.hist(chunk_x.reshape(-1,1), 50, color=clr, range = (-4000,4000), density=1, alpha=0.3, zorder=i)
        mu, sigma = sp.stats.norm.fit(chunk_x.reshape(-1,1))
        best_fit_line = sp.stats.norm.pdf(bins_x, mu, sigma)
        ax1.set_ylabel('X axis (Left/Right)')

        ax2 = fig.add_subplot(222)
        ax2.plot(bins_x, best_fit_line, color=clr, zorder=i)

        ax3 = fig.add_subplot(223)
        _, bins_y, _ = plt.hist(chunk_y.reshape(-1,1), 50, color=clr ,range = (-4000,4000), density=1, alpha=0.3, zorder=i)
        mu, sigma = sp.stats.norm.fit(chunk_y.reshape(-1,1))
        best_fit_line = sp.stats.norm.pdf(bins_y, mu, sigma)
        ax3.set_ylabel('Y axis (Back/Front)')

        ax4 = fig.add_subplot(224)
        ax4.plot(bins_y, best_fit_line, color=clr, zorder=i)

        fig.tight_layout()

    return fig

def x_y_threshold_across_time(LogDf, axes=None):

    if axes is None:
        axes = plt.gca()

    event_times = bhv.get_events_from_name(LogDf, align_reference)

    return axes

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
        event_times = bhv.get_events_from_name(LogDf,"SECOND_TIMING_CUE_EVENT")
        trials_performed.append(len(event_times))

        # Number of sucessful trials 
        correct_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_CORRECT_EVENT')
        trials_sucessful.append(len(correct_choiceDf))
        
        # Number of unsucessful trials 
        incorrect_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_INCORRECT_EVENT')
        trials_unsucessful.append(len(incorrect_choiceDf))

        # Weight
    
    # Formatting
    axes.plot(trials_performed, color = 'black', label = 'Performed')
    axes.plot(trials_sucessful, color = 'green', label = 'Sucessful')
    axes.plot(trials_unsucessful, color = 'red', label = 'Unsucessful')
    axes.set_ylabel('Count (#)')
    axes.set_xlabel('Session number')
    axes.set_title('Trial overview across sessions in task:  ' + task_name)
    axes.legend(loc='upper right', frameon=False)   

    return axes