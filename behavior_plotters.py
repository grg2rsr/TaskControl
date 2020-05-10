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
def plot_session_overview(Data, t_ref, pre, post, axes=None, how='dots',cdict=None):
    """ plots a session overview """

    if axes is None:
        axes = plt.gca()

    if cdict is None:
        #implement
        pass
    
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

def plot_psth(t_ref, events, pre, post, bin_width=50, axes=None, **kwargs):
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
