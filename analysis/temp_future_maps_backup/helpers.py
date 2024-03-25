import numpy as np
import pandas as pd
import os

"""
 
 ########     ###    ########    ###    
 ##     ##   ## ##      ##      ## ##   
 ##     ##  ##   ##     ##     ##   ##  
 ##     ## ##     ##    ##    ##     ## 
 ##     ## #########    ##    ######### 
 ##     ## ##     ##    ##    ##     ## 
 ########  ##     ##    ##    ##     ## 
 
"""

def reslice_array(A, tvec, slice_times, pre, post, fallback_mode=None):
    # slice
    A_slices = []
    for t in slice_times:
        ix = np.logical_and(tvec > t+pre, tvec < t+post)
        A_slices.append(A[ix])
    
    # stack if possible
    shapes = np.array([A_slice.shape[0] for A_slice in A_slices])
    if np.all(shapes == shapes[0]):
        return np.stack(A_slices, axis=2)
    else:
        # if not - fallback_mode
        uniques, counts = np.unique(shapes, return_counts=True)
        print("can't stack")
        for i in range(uniques.shape[0]):
            print(uniques[i],counts[i])
        if fallback_mode == "jagged":
            return make_jagged_array(A_slices)
        if fallback_mode == "truncate":
            return make_trunc_array(A_slices)
        return None

def make_jagged_array(A_slices, fill_value=np.nan):
    shapes = np.array([A_slice.shape[0] for A_slice in A_slices])
    max_shape = np.max(shapes)
    J = np.zeros((max_shape, len(A_slices)))
    J[:] = fill_value
    for j in range(len(A_slices)):
        J[:shapes[j],j] = A_slices[j]
    return J

def make_trunc_array(A_slices):
    shapes = np.array([A_slice.shape[0] for A_slice in A_slices])
    min_shape = np.min(shapes)
    T = np.zeros((min_shape, len(A_slices)))
    for j in range(len(A_slices)):
        T[:,j] = A_slices[:min_shape, j]
    return T

# def make_trunc_array(A_slices, axes=0):
#     min_shape = np.min([A_slice.shape[axes] for A_slice in A_slices])
#     T = np.zeros((min_shape, len(A_slices)))
#     for j in range(len(A_slices)):
#         T[:,j] = A_slices[:min_shape, j]
#     return T

def reslice_timestamps(T, slice_times, pre, post):
    T_slices = []
    for t in slice_times:
        ix = np.logical_and(T > t+pre, T < t+post)
        T_slices.append(T[ix] - t) # relative times
    return T_slices


"""
 
  ######  ######## #### ##     ## 
 ##    ##    ##     ##  ###   ### 
 ##          ##     ##  #### #### 
  ######     ##     ##  ## ### ## 
       ##    ##     ##  ##     ## 
 ##    ##    ##     ##  ##     ## 
  ######     ##    #### ##     ## 
 
"""

def get_stim_dur_offset(stim_dict):
    # stim_dict is dict form of stim as from stim_classes[label]
    # has hardcode that red = vpl stim is on channel 1

    # stim_id = '4'
    # for ch in Stims[stim_id]:
    #     if ch['ch'] == 1:
    #         stim_dur = (ch['n'] / ch['f']) + ch['dur']/1e3
    for ch in stim_dict:
        if ch['ch'] == 1:
            stim_dur = (ch['n'] / ch['f']) + ch['dur']/1e3
            t_offset = ch['t_offset']/1e3
            return stim_dur, t_offset

# load data
def get_StimsDf(run_folder):
    folder = [f for f in os.listdir(run_folder) if f.endswith('_stims')][0]
    print("getting stim file from %s" % folder)
    stim_file_path = run_folder / folder / "stim_list.txt"
    with open(stim_file_path, 'r')as fH:
        stims_file = fH.readlines()

    # make stim def
    stims_unique = np.unique(stims_file)
    stim_classes = {}
    for i in range(stims_unique.shape[0]):
        s = stims_unique[i].strip().split('\t')
        stim_classes[s[0]] = [dict(eval(s[j+1])) for j in range(len(s)-1)]

    # the stim IDs as they were presented to the animal
    stims = []
    for line in stims_file:
        stims.append(line.split('\t')[0])
    stims = np.array(stims)

    # from events
    stim_times = Events[1]['times_corr']
    n_stims = stim_times.shape[0]
    stims = stims[:n_stims] # FIXME will be obsolete in the future

    stim_labels = np.sort(np.unique(stims))
    # n_stim_classes = stim_labels.shape[0]

    StimsDf = pd.DataFrame([])
    StimsDf['t'] = stim_times
    StimsDf['stim_id'] = stims
    
    # some hardcoded stuff
    StimsDf['VPL'] = False
    StimsDf['SNc'] = False

    StimsDf.loc[StimsDf['stim_id'] == '1','VPL'] = True
    StimsDf.loc[StimsDf['stim_id'] == '2','VPL'] = True

    StimsDf.loc[StimsDf['stim_id'] == '2','SNc'] = True
    StimsDf.loc[StimsDf['stim_id'] == '3','SNc'] = True

    StimsDf['both'] = StimsDf['VPL'] * StimsDf['SNc']

    
    return StimsDf, stim_classes

def infer_StimsDf(Events, save=None):
    from helpers import reslice_timestamps

    # hardcoding map
    sync = 0
    trig = 1
    da = 2
    vpl = 3
    vpl_list = reslice_timestamps(Events[vpl]['times'], Events[trig]['times'],0,3)
    da_list = reslice_timestamps(Events[da]['times'], Events[trig]['times'],0,3)

    StimsDf = pd.DataFrame([])

    StimsDf['t'] = Events[trig]['times_corr']
    StimsDf['VPL'] = [True if l.shape[0] > 0 else False for l in vpl_list]
    StimsDf['SNc'] = [True if l.shape[0] > 0 else False for l in da_list]
    StimsDf['both'] = StimsDf['VPL'] * StimsDf['SNc']
    StimsDf['stim_id'] = '0'

    StimsDf.loc[StimsDf['VPL']  & ~StimsDf['SNc'], 'stim_id'] = '1'
    StimsDf.loc[StimsDf['VPL']  & StimsDf['SNc'], 'stim_id'] = '2'
    StimsDf.loc[~StimsDf['VPL'] & StimsDf['SNc'], 'stim_id'] = '3'

    if save is not None:
        StimsDf.to_csv(save)
    return StimsDf

def get_stim_classes(run_folder):
    folder = [f for f in os.listdir(run_folder) if f.endswith('_stims')][0]
    print("getting stim file from %s" % folder)
    stim_file_path = run_folder / folder / "stim_list.txt"
    with open(stim_file_path, 'r')as fH:
        stims_file = fH.readlines()

    # make stim def
    stims_unique = np.unique(stims_file)
    stim_classes = {}
    for i in range(stims_unique.shape[0]):
        s = stims_unique[i].strip().split('\t')
        stim_classes[s[0]] = [dict(eval(s[j+1])) for j in range(len(s)-1)]
    return stim_classes