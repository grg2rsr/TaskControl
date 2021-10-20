import sys, os
sys.path.append('..')
from pathlib import Path
from copy import copy

import numpy as np
from scipy import stats
import pandas as pd

sys.path.append('..')
from Utils import behavior_analysis_utils as bhv

"""
 
  ######  ##    ## ##    ##  ######      ######  ##          ###     ######   ######  
 ##    ##  ##  ##  ###   ## ##    ##    ##    ## ##         ## ##   ##    ## ##    ## 
 ##         ####   ####  ## ##          ##       ##        ##   ##  ##       ##       
  ######     ##    ## ## ## ##          ##       ##       ##     ##  ######   ######  
       ##    ##    ##  #### ##          ##       ##       #########       ##       ## 
 ##    ##    ##    ##   ### ##    ##    ##    ## ##       ##     ## ##    ## ##    ## 
  ######     ##    ##    ##  ######      ######  ######## ##     ##  ######   ######  
 
"""

class Syncer(object):
    def __init__(self):
        self.data = {}
        self.pairs = {}
        self.graph = {}

    def check(self, A, B):
        """ check consistency of all clock pulses and if possible fixes them """

        if self.data[A].shape[0] == 0 or self.data[A].shape[0] == 0:
            printer("sync failed - %s is empty" % A, 'error')
            return False

        elif self.data[B].shape[0] == 0:
            printer("sync failed - %s is empty" % B, 'error')
            return False

        elif self.data[A].shape[0] != self.data[B].shape[0]:

            # Decide which is the reference to cut to
            if self.data[A].shape[0] > self.data[B].shape[0]:
                bigger = 'A'
                printer("Clock A has more pulses")
                t_bigger = self.data[A]
                t_smaller = self.data[B]
            else:
                print("Clock B has more pulses")
                bigger = 'B'
                t_bigger = self.data[B]
                t_smaller = self.data[A]
            printer("sync problem - unequal number of pulses, %s has more sync signals" % bigger, 'error')

            # Compute the difference
            offset = np.argmax(np.correlate(np.diff(t_bigger), np.diff(t_smaller), mode='valid'))

            # Cut the initial timestamps from the argument with more clock pulses
            t_bigger = t_bigger[offset:t_smaller.shape[0]+offset]

            if bigger == 'A':
                self.data[A] = t_bigger
                self.data[B] = t_smaller
            else:
                self.data[B] = t_bigger
                self.data[A] = t_smaller
            
            return True
        else:
            return True

    def sync(self, A, B, check=True, symmetric=True):
        """ linreg sync of A to B """
        if self.check(A, B) is True:
            m, b = stats.linregress(self.data[A], self.data[B])[:2]
            self.pairs[(A,B)] = (m, b)
            if A in self.graph:
                self.graph[A].append(B)
            else:
                self.graph[A] = [B]
        if symmetric:
            self.sync(B,A, symmetric=False)

    def convert(self, t, A, B, match_dtype=True):
        path = self._find_shortest_path(A, B)

        for i in range(1,len(path)):
            t = self._convert(t, path[i-1], path[i])

        if match_dtype:
            t = t.astype(self.data[B].dtype)

        return t

    def _convert(self, t, A ,B):
        if (A,B) not in self.pairs:
            self.sync(A,B)
        m,b = self.pairs[(A,B)]
        return t * m+b

    def _find_shortest_path(self, start, end, path=[]):
        # from https://www.python.org/doc/essays/graphs/
        path = path + [start]
        if start == end:
            return path
        if start not in self.graph:
            return None
        shortest = None
        for node in self.graph[start]:
            if node not in path:
                newpath = self._find_shortest_path(node, end, path)
                if newpath:
                    if not shortest or len(newpath) < len(shortest):
                        shortest = newpath
        return shortest

"""
 
 ########     ###    ########   ######  ######## ########  
 ##     ##   ## ##   ##     ## ##    ## ##       ##     ## 
 ##     ##  ##   ##  ##     ## ##       ##       ##     ## 
 ########  ##     ## ########   ######  ######   ########  
 ##        ######### ##   ##         ## ##       ##   ##   
 ##        ##     ## ##    ##  ##    ## ##       ##    ##  
 ##        ##     ## ##     ##  ######  ######## ##     ## 
 
"""

def get_arduino_sync(log_path, sync_event_name="TRIAL_ENTRY_EVENT"):
    LogDf = bhv.get_LogDf_from_path(log_path)
    SyncDf = bhv.get_events_from_name(LogDf, sync_event_name)
    return SyncDf

def parse_harp_sync(csv_path, trig_len=1, ttol=0.2):
    harp_sync = pd.read_csv(csv_path, names=['t']).values.flatten()
    t_sync_high = harp_sync[::2]
    t_sync_low = harp_sync[1::2]

    dts = np.array(t_sync_low) - np.array(t_sync_high)
    good_timestamps = ~(np.absolute(dts-trig_len)>ttol)
    t_sync = np.array(t_sync_high)[good_timestamps]
    SyncDf = pd.DataFrame(t_sync, columns=['t'])
    return SyncDf

def parse_cam_sync(csv_path):
    """ csv_path is the video_sync_path, files called 
    bonsai_harp_sync.csv """

    Df = pd.read_csv(csv_path, names=['frame','t','GPIO'])

    # wraparound correct
    # Df = bhv.correct_wraparound(Df)
    _Df = copy(Df)
    while np.any(np.diff(Df['t']) < 0):
        reversal_ind = np.where(np.diff(Df['t']) < 0)[0][0]
        Df['t'].iloc[reversal_ind+1:] += _Df['t'].iloc[reversal_ind]

    ons = np.where(np.diff(Df.GPIO) > 1)[0]
    offs = np.where(np.diff(Df.GPIO) < -1)[0] # can be used to check correct length

    SyncDf = Df.iloc[ons+1] # one frame offset
    return SyncDf
