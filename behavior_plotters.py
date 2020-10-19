#%matplotlib qt5
#%load_ext autoreload
#%autoreload 2

from matplotlib import pyplot as plt
from matplotlib import cm 
from matplotlib import patches

from sklearn.linear_model import LogisticRegression
from scipy.special import expit

import behavior_analysis_utils as bhv
import pandas as pd
# this should be changed ... 
import itertools
from pathlib import Path
import scipy as sp
import numpy as np
import seaborn as sns
from tqdm import tqdm
import os
import calendar

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

    # bins = np.zeros(bins.shape)

    values = []
    for t in t_ref: # for every task event time
        times = bhv.time_slice(EventsDf, t+pre, t+post)['t'] - t 
        values.append(times.values) # get number of licks from EventsDf
    values = np.concatenate(values)

    if how is 'steps':
        counts, bins = np.histogram(values,bins=bins)
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
        axes.plot(times, np.ones(times.shape[0])*i,'.',color='k')

    return axes

def plot_reward_collection_rate(SessionDf, history=None, axes=None):
    """ plots success rate, if history given includes a rolling smooth """
    if axes is None:
        axes = plt.gca()

    S = SessionDf.groupby('successful').get_group(True)
    x = S.index.values+1

    # grand average rate
    y = np.cumsum(S['reward_collected'].values) / (S.index.values+1)
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
        bins = np.arange(0,values.max(),25)
    
    axes.hist(values,bins=bins, **kwargs)
    # counts, bins = np.histogram(values,bins=bins)
    # axes.step(bins[1:], counts, color='r')
    axes.set_xlabel('time (ms)')
    axes.set_ylabel('count')
    axes.set_title('reward collection RT')

    return axes

"""
########  ####    ###     ######   ##    ##  #######   ######  ######## ####  ######     ##     ## ####
##     ##  ##    ## ##   ##    ##  ###   ## ##     ## ##    ##    ##     ##  ##    ##    ##     ##  ##
##     ##  ##   ##   ##  ##        ####  ## ##     ## ##          ##     ##  ##          ##     ##  ##
##     ##  ##  ##     ## ##   #### ## ## ## ##     ##  ######     ##     ##  ##          ##     ##  ##
##     ##  ##  ######### ##    ##  ##  #### ##     ##       ##    ##     ##  ##          ##     ##  ##
##     ##  ##  ##     ## ##    ##  ##   ### ##     ## ##    ##    ##     ##  ##    ##    ##     ##  ##
########  #### ##     ##  ######   ##    ##  #######   ######     ##    ####  ######      #######  ####
"""

def general_info(LogDf, path, axes=None):
    " Plots general info about a session (trial outcome, water consumed and weight) "
    
    if axes is None:
        _ , axes = plt.subplots()

    # Session info in axis A
    session_dur = round((LogDf['t'].iat[-1]-LogDf['t'].iat[0])/60000) # convert to min

    water_drank = len(bhv.get_events_from_name(LogDf,"REWARD_COLLECTED_EVENT"))*10

    animal_meta = pd.read_csv(path.joinpath('animal_meta.csv'))
    weight = round(float(animal_meta.at[6, 'value'])/float(animal_meta.at[4, 'value']),2)*100

    axes[1].text(0.5, 0, 'Water drank: '+ str(water_drank) + ' ul', horizontalalignment='center', verticalalignment='center')
    axes[1].text(0.5, 0.5, 'Session dur.: '+ str(session_dur) + ' min', horizontalalignment='center', verticalalignment='center')
    axes[1].text(0.5, 1,'Weight: ' + str(weight) + '%', horizontalalignment='center', verticalalignment='center')
    axes[1].axis('off')

    # Trial info in axis B
    trials_corr = len(bhv.get_events_from_name(LogDf,'CHOICE_CORRECT_EVENT'))
    trials_incorr = len(bhv.get_events_from_name(LogDf,'CHOICE_INCORRECT_EVENT'))
    
    try:
        trials_miss = len(bhv.get_events_from_name(LogDf,"CHOICE_MISSED_EVENT"))
    except:
        print('This session has no missed trials')
    try:
        trials_prem = len(bhv.get_events_from_name(LogDf,"PREMATURE_CHOICE_EVENT"))
    except:
        print('This session has no premature trials')

    trials = [trials_corr, trials_incorr, trials_prem, trials_miss]

    colors = {
    'green':'#2ca02c',
    'red':'#d62728',
    'pink':'#e377c2',
    'gray':'#7f7f7f',
    }
    
    category_names = ['Corr', 'Incorr', 'Pre', 'Miss']

    data = np.array(trials)
    data_cum = data.cumsum()

    axes[0].invert_yaxis()
    axes[0].set_xlim(0, np.sum(data).max())

    for i, color in enumerate(colors):
        widths = data[i]
        starts = data_cum[i] - widths
        axes[0].barh(0, widths, left=starts, height=0.25, color=color, label = category_names[i])
        xcenters = starts + widths / 2
        
        # Plot numbers inside
        axes[0].text(xcenters, 0, str(int(widths)), ha='center', va='center', color='black')

    axes[0].legend(ncol=len(category_names), bbox_to_anchor=(0, 1), loc='lower left', fontsize='small', frameon=False)
    axes[0].axis('off')

    return axes

def plot_forces_heatmaps(LogDf, LoadCellDf, align_ref, pre, post, axes=None, tick_ref = None):
    """ Plots heatmaps of LC forces in X axes algined to any event (also marks choice times) """

    if axes==None:
        _ , axes = plt.subplots()

    event_times = bhv.get_events_from_name(LogDf, align_ref)
    Fx, correct_idx, incorrect_idx = [],[],[]
    
    i = 0
    # Splitting Fx  by trial result type (correct/incorrect)
    for t in event_times['t']:
        
        F = bhv.time_slice(LoadCellDf,t+pre,t+post)
        if (len(F) < post+pre):
            print('LCDf is shorter than LogDf!')
            continue
        Fx.append(F['x'])

        TrialDf = bhv.time_slice(LogDf,t+pre,t+post)

        if "CHOICE_CORRECT_EVENT" in TrialDf.name.values:
            correct_idx.append(i)
        elif "CHOICE_INCORRECT_EVENT" in TrialDf.name.values:
            incorrect_idx.append(i)

        i = i + 1

    # Appending groups of trials into one and truncating them
    correct_idx = np.array(correct_idx)
    incorrect_idx = np.array(incorrect_idx)
    Fx = np.array(Fx)
    Fx = Fx[np.concatenate((correct_idx,incorrect_idx))]

    force_x_tresh = 2500

    heat = axes.matshow(Fx, cmap='PiYG',vmin=-force_x_tresh,vmax=force_x_tresh) # X axis

    # Labels, title and formatting
    axes.set_title('Forces in L/R axis aligned to ' + align_ref)
    axes.set_xlabel('Time')
    axes.set_ylabel('Trials')

    # xticks in seconds
    plt.setp(axes, xticks=np.arange(0, post-pre + 1, 500), xticklabels=np.arange(pre//1000, post//1000 + 0.1, 0.5))

    # colorbar 
    cbar = plt.colorbar(heat, ax=axes, orientation='horizontal', aspect = 30)
    cbar.set_ticks([-2000,-1000,0,1000,2000]); cbar.set_ticklabels(["Left (-2000)","-1000","0","1000","Right (2000)"])

    # Color code on the right
    axes.vlines(post-pre-5, 0, len(correct_idx), colors='g', linewidth=4)
    axes.vlines(post-pre-5, len(correct_idx), len(correct_idx) + len(incorrect_idx) - 1, colors='r', linewidth=4)

    axes.set_aspect('auto')

    return axes

def plot_choice_time_hist(LogDf, TrialDfs, bin_width, axes=None):
    " Plots the choice RT histograms split by trial type and outcome "

    if axes==None:
        _ , axes = plt.subplots(nrows=2, sharex=True)

    ct_left_correct, ct_right_correct = [],[]
    ct_left_incorrect, ct_right_incorrect = [],[]

    " Getting choice RT's "
    for TrialDf in TrialDfs:
        if bhv.has_choice(TrialDf).bool():

            # Correct ones
            if bhv.get_choice(TrialDf).item() == 'left' and bhv.is_successful(TrialDf).bool():
                ct_left_correct.append(int(bhv.choice_RT(TrialDf)))

            elif bhv.get_choice(TrialDf).item() == 'right' and bhv.is_successful(TrialDf).bool():
                ct_right_correct.append(int(bhv.choice_RT(TrialDf)))

            # Incorrect ones
            if bhv.get_choice(TrialDf).item() == 'left' and not bhv.is_successful(TrialDf).bool():
                ct_left_incorrect.append(int(bhv.choice_RT(TrialDf)))

            elif bhv.get_choice(TrialDf).item() == 'right' and not bhv.is_successful(TrialDf).bool():
                ct_right_incorrect.append(int(bhv.choice_RT(TrialDf)))

    choice_interval = 2000
    no_bins = round(choice_interval/bin_width)

    kwargs = dict(bins = no_bins, range = (0, choice_interval), alpha=0.5, edgecolor='none')

    axes[0].hist(ct_left_correct, **kwargs, color='red', label = 'Left choice')
    axes[0].hist(ct_right_correct, **kwargs, color='green', label = 'Right choice')

    axes[1].hist(ct_left_incorrect, **kwargs, color='red', label = 'Left choice')
    axes[1].hist(ct_right_incorrect, **kwargs, color='green', label = 'Right choice')

    axes[0].set_ylabel('# Corr. trials')
    axes[0].legend(loc='upper right', frameon=False, fontsize = 8)
    axes[0].set_xlabel('Time (s)')

    axes[1].set_ylabel('# Incorr. trials')
    axes[1].legend(loc='upper right', frameon=False, fontsize = 8)
    axes[1].set_xlabel('Time (s)')

    plt.setp(axes, xticks=np.arange(0, choice_interval+1, 500), xticklabels=np.arange(0, (choice_interval//1000)+0.1, 0.5))
    plt.setp(axes, title = 'Choice RTs Hist.')

    return axes  

def plot_success_rate(SessionDf, LogDf, history=None, axes=None): 
    " Plots success rate with trial outcome tickmarks, if history given includes a rolling smooth "
    if axes is None:
        axes = plt.gca()

    x = SessionDf.index.values+1
    
    correctDf = SessionDf[SessionDf['outcome'] == 'correct']
    incorrectDf = SessionDf[SessionDf['outcome'] == 'incorrect']
    missedDf = SessionDf[SessionDf['outcome'] == 'missed']
    #prematureDf = SessionDf[SessionDf['outcome'] == 'premature'] # uncomment once premature trials become less frequent
    
    line_width = 0.04
    value = np.ones(len(SessionDf))*line_width

    # plot raw as markers
    axes.plot(correctDf.index, correctDf['outcome'] == 'correct', '|',alpha=0.75,color='g')
    axes.plot(incorrectDf.index, incorrectDf['outcome'] != 'incorrect', '|',alpha=0.75,color='r')
    axes.plot(missedDf.index, value[missedDf.index], '|',alpha=0.75,color='k')
    #axes.plot(prematureDf.index, prematureDf['outcome'] != 'premature', '|',alpha=0.5,color='m')
    
    # grand average rate
    y = np.cumsum(SessionDf['successful'].values) / (SessionDf.index.values+1)
    axes.plot(x,y, color='C0', label = 'grand average')
    
    if history is not None:
        y_filt = SessionDf['successful'].rolling(history).mean()
        axes.plot(x,y_filt, color='C0',alpha=0.3, label = 'rolling mean')
    
    axes.set_ylabel('frac. successful')
    axes.set_xlabel('trial #')
    axes.set_title('Success rate and bias')

    try:
        # Bias over time
        Df = LogDf[LogDf['var'] == 'bias']
        times = Df['t'] / 1e3 
        times = times - times.iloc[0]

        twin_ax = axes.twinx()
        twin_ax.plot(x, Df['value'].rolling(history).mean()[1:], label='last 10', c ='k', alpha=0.5)
        twin_ax.axhline(0.5, color='k', linestyle=':', alpha=0.5, lw=1, zorder=-1)
        twin_ax.set_ylim(0, 1) 
        twin_ax.set_ylabel('bias', c ='k')
    except:
        print("This session does not have bias recorded")

    return axes

def simple_psychometric(SessionDf, axes=None):
    " Timing task classic psychometric fit to data"

    if axes is None:
        axes = plt.gca()

    # get only the subset with choices
    SDf = SessionDf.groupby('has_choice').get_group(True)
    y = SDf['choice'].values == 'right'
    x = SDf['this_interval'].values

    # plot choices
    axes.plot(x,y,'.',color='k',alpha=0.5)
    axes.set_yticks([0,1])
    axes.set_yticklabels(['short','long'])
    axes.set_ylabel('choice')
    axes.axvline(1500,linestyle=':',alpha=0.5,lw=1,color='k')

    x_fit = np.linspace(0,3000,100)
    line, = plt.plot([],color='red', linewidth=2,alpha=0.75)
    line.set_data(x_fit, bhv.log_reg(x, y, x_fit))
    
    try:
        # %% random margin - with animal bias
        t = SDf['this_interval'].values
        bias = (SessionDf['choice'] == 'right').sum() / SessionDf.shape[0] # This includes premature choices now!
        R = []
        for i in range(100):
            rand_choices = np.rand(t.shape[0]) < bias # can break here if bias value is too low
            R.append(bhv.log_reg(x, rand_choices,x_fit))
        R = np.array(R)
        alpha = .5
        R_pc = np.percentile(R, (alpha, 100-alpha), 0)
        plt.fill_between(x_fit, R_pc[0],R_pc[1],color='blue',alpha=0.5)
        plt.set_cmap
    except:
        print('Bias too high')


    plt.setp(axes, xticks=np.arange(0, 3000+1, 500), xticklabels=np.arange(0, 3000//1000 +0.1, 0.5))
    axes.set_xlabel('Time (s)')

    return axes

def plot_force_magnitude(LoadCellDf, SessionDf, TrialDfs, first_cue_ref, second_cue_ref, bin_width, axes=None):
    """ 
        Plots the magnitude of the 2D forces vector aligned to 1st and 2nd cue with
        lick frequency histogram on top (also includes premature trials on left)
    """
    
    if axes is None:
        _ , axes = plt.subplots(1, 2, sharey=True, sharex=True)
    
    "Licks"
    twin_ax2 = axes[1].twinx()

    pre, plot_dur, force_tresh = -500 , 2000, 2000
    outcomes = ['correct', 'incorrect', 'missed']

    for outcome in outcomes:
        
        Fmag_1st, Fmag_2nd, licks = [],[],[]
        ys_1st, ys_2nd = [],[]

        # Get Session rows containing only trials with specific outcome
        try:
            SDf = SessionDf.groupby('outcome').get_group(outcome)
        except:
            continue

        # Go trough each row and get forces
        for _, row in tqdm(SDf.iterrows()):
            TrialDf = TrialDfs[row.name]
                
            time_1st = float(TrialDf[TrialDf.name == first_cue_ref]['t'])
            time_2nd = float(TrialDf[TrialDf.name == second_cue_ref]['t'])
            time_last = float(TrialDf['t'].iloc[-1])
            
            # Aligned to first cue
            F = bhv.time_slice(LoadCellDf, time_1st+pre, time_2nd) # also get previous 0.5s
            y = np.sqrt(F['x']**2+F['y']**2)
            ys_1st.append(y)

            # Aligned to second cue
            F = bhv.time_slice(LoadCellDf, time_2nd+pre, time_last) # also get previous 0.5s
            y = np.sqrt(F['x']**2+F['y']**2)
            ys_2nd.append(y)

            try:
                licks.append(bhv.get_licks(TrialDf, time_2nd+pre, time_last))
            except:
                pass

        # Compute mean force for each outcome aligned to first or second        
        Fmag_1st = bhv.tolerant_mean(np.array(ys_1st))
        Fmag_2nd = bhv.tolerant_mean(np.array(ys_2nd))

        axes[0].plot(np.arange(len(Fmag_1st))+1, Fmag_1st, label = outcome)
        axes[1].plot(np.arange(len(Fmag_2nd))+1, Fmag_2nd, label = outcome) 

        # Get lick histogram
        if not licks:
            pass
        else:
            no_bins = round((plot_dur-pre)/bin_width)
            counts_2, bins = np.histogram(np.concatenate(licks),no_bins)
            licks_2nd_freq = np.divide(counts_2, ((bin_width/1000)*len(ys_2nd)))
            twin_ax2.step(bins[1:], licks_2nd_freq, alpha=0.5, label = outcome)
                               
    " Force "
    # Left plot
    axes[0].legend(loc='upper right', frameon=False)
    axes[0].set_ylabel('Force magnitude (a.u.)')
    plt.setp(axes[0], xticks=np.arange(0, plot_dur-pre+1, 500), xticklabels=np.arange(-0.5, plot_dur//1000 + 0.1, 0.5))

    # Right plot
    axes[1].legend(loc='upper right', frameon=False)
    plt.setp(axes[1], xticks=np.arange(0, plot_dur-pre+1, 500), xticklabels=np.arange(-0.5, plot_dur//1000 + 0.1, 0.5))
    
    # Shared
    plt.setp(axes, yticks=np.arange(0, force_tresh+1, 500), yticklabels=np.arange(0, force_tresh+1, 500))
    axes[0].set_xlim(0,plot_dur-pre)
    axes[0].set_ylim(0,force_tresh)
    axes[1].set_xlim(0,plot_dur-pre)
    axes[1].set_ylim(0,force_tresh)

    " Licks "
    twin_ax2.tick_params(axis='y', labelcolor='C0')
    twin_ax2.set_ylabel('Lick freq. (Hz)', color='C0')
    plt.setp(twin_ax2, yticks=np.arange(0, 11), yticklabels=np.arange(0, 11))

    # hide the spines between axes 
    axes[0].spines['right'].set_visible(False)
    axes[0].spines['top'].set_visible(False)
    axes[1].spines['left'].set_visible(False)
    axes[1].spines['top'].set_visible(False)

    twin_ax2.spines['left'].set_visible(False)
    twin_ax2.spines['top'].set_visible(False)

    axes[0].yaxis.tick_left()
    axes[1].tick_params(labelleft = False, left = False)

    axes[0].set_title('Align to 1st cue')
    axes[1].set_title('Align to 2nd cue')

    return axes

def plot_choice_matrix(SessionDf, LogDf, trial_type, axes=None):
    'Plots percentage of choices made in a session in a 3x3 choice matrix following a KB layout'

    if axes is None:
        _ , axes = plt.subplots()

    choice_matrix = np.zeros((3,3))

    # Completed incorrect trials
    if trial_type == 'incorrect':
        for trial in SessionDf.itertuples():
            if trial.outcome == 'incorrect': 
                choice_matrix = bhv.triaL_to_choice_matrix(trial, choice_matrix)

        no_incorrect_trials = len(LogDf[LogDf['name'] == 'CHOICE_INCORRECT_EVENT'])
        choice_matrix_percentage = np.round(np.multiply(np.divide(choice_matrix, no_incorrect_trials),100))
    
    # Premature trials
    if trial_type == 'premature':
        for trial in SessionDf.itertuples():
            if trial.outcome == 'premature':
                choice_matrix = bhv.triaL_to_choice_matrix(trial, choice_matrix)

        no_premature_trials = len(LogDf[LogDf['name'] == 'PREMATURE_CHOICE_EVENT'])
        choice_matrix_percentage = np.round(np.multiply(np.divide(choice_matrix, no_premature_trials),100))
    
    # Plot choice matrix independtly of input
    axes.matshow(choice_matrix_percentage, cmap='Reds')
    for (i, j), z in np.ndenumerate(choice_matrix_percentage):
        axes.text(j, i, '{:.0f}'.format(z), ha='center', va='center')

    if trial_type == 'incorrect':
        axes.set_title('Incorrect')
    if trial_type == 'premature':
        axes.set_title('Premature')    

    axes.axis('off')

    return axes

def plot_forces_trajectories(LogDf, LoadCellDf, TrialDfs, align_ref, trial_outcome, axes=None):
    """ Plots trajectories in 2D aligned to any TWO events"""

    if axes==None:
        _ , axes = plt.subplots()

    pre,post = 0, 1000

    F = []; idx_left, idx_right = [],[]; i = 0

    # Obtain forces of every trial with specified trial_outcome
    for TrialDf in TrialDfs:

        if bhv.get_outcome(TrialDf).values[0] == trial_outcome:
            t = float(TrialDf[TrialDf.name == 'SECOND_TIMING_CUE_EVENT']['t'])
            f = bhv.time_slice(LoadCellDf,t+pre,t+post)
            F.append([f['x'], f['y']])

            # Split into L/R in case of trial outcome being correct
            if trial_outcome == 'correct':
                if bhv.get_choice(TrialDf).values[0] == 'right':
                    idx_right.append(i)
                if bhv.get_choice(TrialDf).values[0] == 'left':
                    idx_left.append(i)
                i = i + 1

    F = np.array(F)
    
    # time-varying color code
    if trial_outcome == 'correct':
        cm0 = plt.cm.get_cmap('Reds')
        cm1 = plt.cm.get_cmap('Greens')
    elif trial_outcome == 'incorrect':
        cm = plt.cm.get_cmap('Reds')
    elif trial_outcome == 'premature': 
        cm = plt.cm.get_cmap('RdPu')
    else:
        cm = plt.cm.get_cmap('Greys')

    z = np.linspace(0, 1, num = F.shape[2])

    if trial_outcome == 'correct':
        F_left_mean = np.mean(F[idx_left],0).T
        F_right_mean = np.mean(F[idx_right],0).T
        scatter = plt.scatter(F_left_mean[:, 0], F_left_mean[:, 1], c=z, cmap= cm0, s = 4, label = 'left correct')
        scatter = plt.scatter(F_right_mean[:, 0], F_right_mean[:, 1], c=z, cmap= cm1, s = 4, label = 'right correct')
    else:
        F_mean = np.mean(F,0).T
        scatter = plt.scatter(F_mean[:, 0], F_mean[:, 1], c=z, cmap= cm, s = 4, label = trial_outcome)

    plt.clim(-0.3, 1)
    #cbar = plt.colorbar(scatter, orientation='vertical', aspect=60)
    #cbar.set_ticks([-0.3, 1]); cbar.set_ticklabels(['0s', str(post//1000) + 's'])

    # Formatting
    axes.axvline(0 ,linestyle=':',alpha=0.5,lw=1,color='k')
    axes.axhline(0 ,linestyle=':',alpha=0.5,lw=1,color='k')
    axes.set_xlabel('L/R axis')
    axes.set_title(' Mean 2D traj. align. to 2nd cue')
    axes.legend(frameon=False, markerscale = 3)

    leg = axes.get_legend()
    leg.legendHandles[0].set_color('red')
    if trial_outcome == 'correct': # also plot the right side 
        leg.legendHandles[1].set_color('green')

    axes.set_xlim([-2500,2500])
    axes.set_ylim([-2500,2500])
    [s.set_visible(False) for s in axes.spines.values()]

    # Bounding box
    Y_thresh = LogDf[LogDf['var'] == 'Y_thresh'].value.values[-1]
    X_thresh = LogDf[LogDf['var'] == 'X_thresh'].value.values[-1]
    axes.add_patch(patches.Rectangle((-X_thresh,-Y_thresh), 2*X_thresh, 2*Y_thresh,fill=False)) 

    return axes

" Currently not used / not implemented "

def x_y_threshold_across_time(LogDf, axes=None):
    "X/Y threshold across time for a single session"

    if axes is None:
        axes = plt.subplots()

    t_vec = np.arrange(0,len(LogDf))

    x_thresh = LogDf[LogDf['var'] == 'X_thresh'].value.values
    y_thresh = LogDf[LogDf['var'] == 'Y_thresh'].value.values

    axes.plt(t_vec, x_thresh, color = 'g', label = 'x_tresh')
    axes.plt(t_vec, y_thresh, color = 'r', label = 'y_tresh')
    axes.legend(loc='upper right', frameon=False, fontsize = 8)
    axes.set_ylabel('Force (a.u.)')

    return axes

def plot_timing_overview(LogDf, LoadCellDf, TrialDfs, axes=None): 
    """
        Heatmap aligned to 1st cue with 2nd cue and choice RT markers, 
        split by trial outcome and trial type
    """

    pre, post = -500, 5000
    Fx, interval, choice_RT = [],[],[]
    correct_idx, incorrect_idx, pre_idx, missed_idx = [],[],[],[]

    if axes is None:
        fig = plt.figure(constrained_layout=True)

    # for every trial initiation
    i = 0
    for TrialDf in TrialDfs:
        time_1st = float(TrialDf[TrialDf.name == 'FIRST_TIMING_CUE_EVENT']['t'])

        F = bhv.time_slice(LoadCellDf, time_1st+pre, time_1st+post)
        if (len(F) < post+pre):
            print('LCDf is shorter than LogDf!')
            continue

        Fx.append(F['x'])
        
        # Store indexes for different types of trials
        if bhv.get_outcome(TrialDf).values[0] == 'correct':
            correct_idx.append(i)
        if bhv.get_outcome(TrialDf).values[0] == 'incorrect':
            incorrect_idx.append(i)
        if bhv.get_outcome(TrialDf).values[0] == 'premature':
            pre_idx.append(i)            
        if bhv.get_outcome(TrialDf).values[0] == 'missed':
            missed_idx.append(i)

        # Store information
        interval.append(int(bhv.get_interval(TrialDf)))
        choice_RT.append(float(bhv.choice_RT(TrialDf)))

        i = i + 1

    # Ugly and hacky way to do what I want
    interval = np.array(interval) - pre
    choice_RT = np.array(choice_RT) + interval
    correct_idx = np.array(correct_idx)
    incorrect_idx = np.array(incorrect_idx)
    pre_idx = np.array(pre_idx)
    missed_idx = np.array(missed_idx)
    Fx = np.array(Fx)

    # Sort the INDEXES (of data already split based on interval)
    corr_idx_sorted = correct_idx[np.argsort(interval[correct_idx])]
    incorr_idx_sorted = incorrect_idx[np.argsort(interval[incorrect_idx])]
    pre_idx_sorted = pre_idx[np.argsort(interval[pre_idx])]
    missed_idx_sorted = missed_idx[np.argsort(interval[missed_idx])]

    split_sorted_idxs_list = [corr_idx_sorted, incorr_idx_sorted, pre_idx_sorted, missed_idx_sorted]

    """ Plotting """
    heights= [len(corr_idx_sorted), len(incorr_idx_sorted), len(pre_idx_sorted), len(missed_idx_sorted)]
    gs = fig.add_gridspec(ncols=1, nrows=4, height_ratios=heights)
    ylabel = ['Correct', 'Incorrect', 'Premature', 'Missed']

    for i, idxs in enumerate(split_sorted_idxs_list):

        axes = fig.add_subplot(gs[i]) 
        force_x_tresh = 2500
        heat = axes.matshow(Fx[idxs,:], cmap='RdBu',vmin=-force_x_tresh,vmax=force_x_tresh) # X axis
        axes.set_aspect('auto')
        axes.axvline(500,linestyle='solid',alpha=0.5,lw=1,color='k')
        axes.axvline(2000,linestyle='solid',alpha=0.25,lw=1,color='k')

        # Second timing cue and choice RT bars
        ymin = np.arange(-0.5,len(idxs)-1) # need to shift since lines starts at center of trial
        ymax = np.arange(0.45,len(idxs))
        axes.vlines(interval[idxs], ymin, ymax, colors='k', alpha=0.75)
        axes.vlines(choice_RT[idxs], ymin, ymax, colors='#7CFC00', linewidth=2)

        if i == 0:
            axes.set_title('Forces X axis aligned to 1st timing cue') 

        axes.set_ylabel(ylabel[i])

        axes.set_xticklabels([])
        axes.set_xticks([])
        axes.set_xlim(0,5500)

    # Formatting
    axes.xaxis.set_ticks_position('bottom')
    plt.setp(axes, xticks=np.arange(0, post-pre+1, 500), xticklabels=np.arange((pre/1000), (post/1000)+0.5, 0.5))
    plt.xlabel('Time')
    
    cbar = plt.colorbar(heat, orientation='horizontal', aspect = 50)
    cbar.set_ticks([-2000,-1000,0,1000,2000]); cbar.set_ticklabels(["Left (-2000)","-1000","0","1000","Right (2000)"])

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

def plot_sessions_overview(LogDfs, paths, task_name, animal_tag, axes = None):
    " Plots trials performed together with every trial outcome plus sucess rate and weight across sessions"

    if axes is None:
        fig , axes = plt.subplots(ncols=2, sharex=True)

    trials_performed = []
    trials_correct = []
    trials_incorrect = []
    trials_missed = []
    trials_premature = []
    weight = []
    date = []

    # Obtaining number of trials of X
    for LogDf,path in zip(LogDfs, paths):

        # Correct date format
        folder_name = os.path.basename(path)
        complete_date = folder_name.split('_')[0]
        month = calendar.month_abbr[int(complete_date.split('-')[1])]
        day = complete_date.split('-')[2]
        date.append(month+'-'+day)

        # Total time
        session_dur = round((LogDf['t'].iat[-1]-LogDf['t'].iat[0])/60000) # convert to min

        # Total number of trials performed
        event_times = bhv.get_events_from_name(LogDf,"TRIAL_ENTRY_STATE")
        trials_performed.append(len(event_times)/session_dur)

        # Missed trials
        missed_choiceDf = bhv.get_events_from_name(LogDf,"CHOICE_MISSED_EVENT")
        trials_missed.append(len(missed_choiceDf)/session_dur)

        # Premature trials
        try:
            premature_choiceDf = bhv.get_events_from_name(LogDf,"PREMATURE_CHOICE_EVENT")
            trials_premature.append(len(premature_choiceDf)/session_dur)
        except:
            trials_premature.append(None)

        # Correct trials 
        correct_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_CORRECT_EVENT')
        trials_correct.append(len(correct_choiceDf)/session_dur)
        
        # Incorrect trials 
        incorrect_choiceDf = bhv.get_events_from_name(LogDf,'CHOICE_INCORRECT_EVENT')
        trials_incorrect.append(len(incorrect_choiceDf)/session_dur)

        # hack workaround for learn_to_push_alternate
        if not trials_correct and not trials_incorrect:
            trials_correct = bhv.get_events_from_name(LogDf,'REWARD_AVAILABLE_EVENT')
            trials_incorrect = trials_performed - trials_missed - trials_correct

        # Weight
        try:
            animal_meta = pd.read_csv(path.joinpath('animal_meta.csv'))
            weight.append(round(float(animal_meta.at[6, 'value'])/float(animal_meta.at[4, 'value']),2))
        except:
            weight.append(None)

    sucess_rate = np.multiply(np.divide(trials_correct,trials_performed),100)

    # Subplot 1
    axes[0].plot(trials_performed, color = 'blue', label = 'Performed')
    axes[0].plot(trials_correct, color = 'green', label = 'Correct')
    axes[0].plot(trials_incorrect, color = 'red', label = 'Incorrect')
    axes[0].plot(trials_missed, color = 'black', label = 'Missed')
    axes[0].plot(trials_premature, color = 'pink', label = 'Premature')
    
    axes[0].set_ylabel('Trial count per minute')
    axes[0].set_xlabel('Session number')
    axes[0].legend(loc='upper left', frameon=False) 

    fig.suptitle('Sessions overview in ' + task_name + ' for mouse ' + animal_tag)
    plt.setp(axes[0], xticks=np.arange(0, len(date), 1), xticklabels=date)
    plt.setp(axes[0], yticks=np.arange(0, max(trials_performed), 1), yticklabels=np.arange(0,  max(trials_performed), 1))
      
    # Two sided axes Subplot 2
    axes[1].plot(sucess_rate, color = 'green', label = 'Sucess rate')
    axes[1].set_ylabel('Sucess rate (%)', color = 'green')
    axes[1].tick_params(axis='y', labelcolor='green')
    plt.setp(axes[1], yticks=np.arange(0,50,5), yticklabels=np.arange(0,50,5))

    weight = np.multiply(weight,100)
    twin_ax = axes[1].twinx()
    twin_ax.plot(weight, color = 'gray')
    twin_ax.set_ylabel('Normalized Weight to max (%)', color = 'gray')
    plt.setp(twin_ax, yticks=np.arange(75,100+1,5), yticklabels=np.arange(75,100+1,5))

    fig.autofmt_xdate()
    plt.show()

    return axes

def rew_collected_across_sessions(LogDfs, axes = None):

    if axes is None:
        fig , axes = plt.subplots(figsize=(4, 3))

    reward_collect_ratio = []
    for LogDf in LogDfs:

        TrialSpans = bhv.get_spans_from_names(LogDf, "TRIAL_ENTRY_STATE", "ITI_STATE")

        TrialDfs = []

        for i, row in TrialSpans.iterrows():
            TrialDfs.append(bhv.time_slice(LogDf, row['t_on'], row['t_off']))

        rew_collected = len(LogDf[LogDf['name']=="REWARD_COLLECTED_EVENT"])
        rew_available_non_omitted = len(LogDf[LogDf['name']=="REWARD_AVAILABLE_EVENT"])-len(LogDf[LogDf['name']=="REWARD_OMITTED_EVENT"])

        reward_collect_ratio = np.append(reward_collect_ratio, rew_collected/rew_available_non_omitted)

    axes.plot(np.arange(len(reward_collect_ratio)), reward_collect_ratio)
    axes.set_ylabel('Ratio')
    axes.set_xlabel('Session number')
    axes.set_title('Reward collected ratio across sessions')
    axes.set_ylim([0,1])
    axes.set_xlim([0,len(reward_collect_ratio)])
    plt.setp(axes, xticks=np.arange(0,len(reward_collect_ratio)), xticklabels=np.arange(0,len(reward_collect_ratio)))
    axes.axhline(0.9, color = 'k', alpha = 0.5, linestyle=':')

    fig.tight_layout()

    return axes

def x_y_tresh_bias_across_sessions(LogDfs, SessionsDf, axes = None):
    
    if axes is None:
        fig, axes = plt.subplots(figsize=(5, 3))

    x_thresh, y_thresh, bias = [],[],[]
    for LogDf in LogDfs:

        x_thresh = np.append(x_thresh, np.mean(LogDf[LogDf['var'] == 'X_thresh'].value.values))
        y_thresh = np.append(y_thresh, np.mean(LogDf[LogDf['var'] == 'Y_thresh'].value.values))
        bias = np.append(bias, LogDf[LogDf['var'] == 'bias'].value.values[-1]) # last bias value

    axes.plot(np.arange(len(LogDfs)), x_thresh, color = 'C0', label = 'X thresh')
    axes.plot(np.arange(len(LogDfs)), y_thresh, color = 'm', label = 'Y thresh')

    axes.set_ylim([1000,2500])
    axes.set_ylabel('Force (a.u.)')
    axes.set_title('Mean X/Y thresh forces and bias across sessions')
    axes.legend(frameon=False)
    axes.set_xticks(np.arange(len(LogDfs)))
    axes.set_xticklabels(np.arange(len(LogDfs))) 

    twin_ax = axes.twinx()
    twin_ax.plot(bias, color = 'g', alpha = 0.5)
    twin_ax.set_ylabel('Bias', color = 'g')
    twin_ax.set_yticks([0,0.5,1])
    twin_ax.set_yticklabels(['left','center','right'])

    fig.tight_layout()

    return axes
