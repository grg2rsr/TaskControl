import sys

sys.path.append("..")
from copy import copy

import numpy as np
import pandas as pd

sys.path.append("..")
from Utils import behavior_analysis_utils as bhv
from Utils import utils

from scipy.optimize import curve_fit

"""
 
  ######  ##    ## ##    ##  ######      ######  ##          ###     ######   ######  
 ##    ##  ##  ##  ###   ## ##    ##    ##    ## ##         ## ##   ##    ## ##    ## 
 ##         ####   ####  ## ##          ##       ##        ##   ##  ##       ##       
  ######     ##    ## ## ## ##          ##       ##       ##     ##  ######   ######  
       ##    ##    ##  #### ##          ##       ##       #########       ##       ## 
 ##    ##    ##    ##   ### ##    ##    ##    ## ##       ##     ## ##    ## ##    ## 
  ######     ##    ##    ##  ######      ######  ######## ##     ##  ######   ######  
 
"""


def lin(x, m, b):
    return m * x + b


# def quad(x, x0, a, b, c):
#     return a*(x-x0)**2 + b*(x-x0) + c

# def cube(x, x0, a, b, c, d):
#     return a*(x-x0)**3 + b*(x-x0)**2 + c*(x-x0) + d

# def poly(x, x0, *a):
#     # print(len(a))
#     return np.sum([a[i]*(x-x0)**i for i in range(len(a))])


def polyv(x, *args):
    n = int(len(args) / 2)
    x0 = args[:n]
    a = args[n:]
    return np.sum(np.array([a[i] * (x - x0[i]) ** i for i in range(len(a))]), axis=0)


class Syncer(object):
    def __init__(self):
        self.data = {}
        self.pairs = {}
        self.graph = {}
        self.funcs = {}

    def check(self, A, B):
        """check consistency of all clock pulses and if possible fixes them"""

        for x in [A, B]:
            if self.data[x].shape[0] == 0:
                utils.printer("sync failed - %s is empty" % x, "error")
                return False

        if self.data[A].shape[0] != self.data[B].shape[0]:
            # Decide which is the reference to cut to
            if self.data[A].shape[0] > self.data[B].shape[0]:
                bigger = "A"
                t_bigger = self.data[A]
                t_smaller = self.data[B]
            else:
                bigger = "B"
                t_bigger = self.data[B]
                t_smaller = self.data[A]
            utils.printer(
                "sync problem - unequal number, %s has more sync signals" % bigger,
                "warning",
            )
            utils.printer("Number in %s: %i" % (A, self.data[A].shape[0]), "warning")
            utils.printer("Number in %s: %i" % (B, self.data[B].shape[0]), "warning")

            # Compute the difference
            offset = np.argmax(
                np.correlate(np.diff(t_bigger), np.diff(t_smaller), mode="valid")
            )

            # Cut the initial timestamps from the argument with more clock pulses
            t_bigger = t_bigger[offset : t_smaller.shape[0] + offset]

            if bigger == "A":
                self.data[A] = t_bigger
                self.data[B] = t_smaller
            else:
                self.data[B] = t_bigger
                self.data[A] = t_smaller

            return True
        else:
            return True

    # def guess_p0(self, func, A, B):
    #     if func == lin:
    #         b = A[0]
    #         m = (B[-1] - B[0]) / (A[-1] - A[0])
    #         return (m,b)

    #     if func == quad:
    #         x0 = (A.max() - A.min()) / 2
    #         a = 0
    #         b = (B[-1] - B[0]) / (A[-1] - A[0])
    #         c = A[0]
    #         return (x0,a,b,c)

    #     if func == cube:
    #         x0 = (A.max() - A.min()) / 2
    #         a = 0
    #         b = 0
    #         c = (B[-1] - B[0]) / (A[-1] - A[0])
    #         d = A[0]
    #         return (x0,a,b,c,d)

    def sync(self, A, B, check=True, symmetric=True, func=lin):
        """linreg sync of A to B"""
        # check and abort if fails
        success = self.check(A, B)
        if not success:
            utils.printer("not successsful")
            return False

        # c = self.data[A][0]
        # b = (self.data[B][-1] - self.data[B][0]) / (self.data[A][-1] - self.data[A][0])
        # a = 0
        # x0 = (self.data[A].max() - self.data[A].min()) / 2
        # p0 = (0,0,0,a,b,c)
        m = (self.data[B][-1] - self.data[B][0]) / (self.data[A][-1] - self.data[A][0])
        b = self.data[A][0]
        p0 = (m, b)
        pfit = curve_fit(func, self.data[A], self.data[B], p0=p0)[0]

        self.pairs[(A, B)] = pfit
        self.funcs[(A, B)] = func

        if A in self.graph:
            self.graph[A].append(B)
        else:
            self.graph[A] = [B]

        if symmetric:
            self.sync(B, A, symmetric=False)

        return True

    def convert(self, t, A, B, match_dtype=True):
        path = self._find_shortest_path(A, B)

        for i in range(1, len(path)):
            t = self._convert(t, path[i - 1], path[i])

        if match_dtype:
            t = t.astype(self.data[B].dtype)

        return t

    def _convert(self, t, A, B):
        if (A, B) not in self.pairs:
            self.sync(A, B)
        pfit = self.pairs[(A, B)]
        func = self.funcs[(A, B)]
        return func(t, *pfit)

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

    def eval_plot(self, plot_residuals=True):
        import matplotlib.pyplot as plt
        import seaborn as sns

        fig, axes = plt.subplots(ncols=len(self.pairs), figsize=[14, 4])
        for i, pair in enumerate(self.pairs):
            A, B = pair
            if plot_residuals:
                x = self.data[A]
                y = self.data[B]
                yhat = self._convert(self.data[A], A, B)
                res = y - yhat
                axes[i].plot(x, res, "o")
            else:
                axes[i].plot(self.data[A], self.data[B], "o")
                t = np.linspace(self.data[A][0], self.data[A][-1], 100)
                axes[i].plot(t, t * m + b, alpha=0.5, lw=1)

            axes[i].set_title("%s - %s" % pair)
            axes[i].set_xlabel(A)
            axes[i].set_ylabel(B)

        for ax in axes:
            ax.axhline(0, linestyle=":", color="k", lw=1, alpha=0.75)
        sns.despine(fig)
        fig.tight_layout()


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
    harp_sync = pd.read_csv(csv_path, names=["t"]).values.flatten()
    t_sync_high = harp_sync[::2]
    t_sync_low = harp_sync[1::2]

    dts = np.array(t_sync_low) - np.array(t_sync_high)
    good_timestamps = ~(np.absolute(dts - trig_len) > ttol)
    t_sync = np.array(t_sync_high)[good_timestamps]
    SyncDf = pd.DataFrame(t_sync, columns=["t"])
    return SyncDf


def parse_cam_sync(csv_path, offset=1, return_full=False):
    """csv_path is the video_sync_path, files called
    bonsai_harp_sync.csv"""

    Df = pd.read_csv(csv_path, names=["frame", "t", "GPIO"])

    # wraparound correct
    # Df = bhv.correct_wraparound(Df)
    _Df = copy(Df)
    while np.any(np.diff(Df["t"]) < 0):
        reversal_ind = np.where(np.diff(Df["t"]) < 0)[0][0]
        Df["t"].iloc[reversal_ind + 1 :] += _Df["t"].iloc[reversal_ind]

    ons = np.where(np.diff(Df.GPIO) > 1)[0]
    offs = np.where(np.diff(Df.GPIO) < -1)[0]  # can be used to check correct length

    SyncDf = Df.iloc[ons + offset]  # one frame offset
    if return_full is False:
        return SyncDf
    else:
        return SyncDf, Df
