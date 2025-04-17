# %%
import numpy as np
from pathlib import Path
import sys
from tqdm import tqdm

from my_logging import get_logger

logger = get_logger(level="INFO")


# delta F/F
def calc_dff(S, w2=500, p=8, verbose=False):
    # adding offset
    # S += np.absolute(S.min() * 2)

    # adding fixed offset
    S += 1000

    n_samples, n_cells = S.shape

    Fb = np.zeros((n_samples, n_cells))
    for i in tqdm(range(w2, n_samples - w2), disable=~verbose):
        Fb[i] = np.percentile(S[i - w2 : i + w2, :], p, axis=0)

    # pad TODO use np.pad()
    Fb[:w2] = Fb[w2]
    Fb[-w2:] = Fb[-w2 - 1]

    dff = (S - Fb) / Fb
    return dff


def calc_z(S, w2=500, verbose=False):
    n_samples, n_cells = S.shape
    Z = np.zeros((n_samples, n_cells))
    for i in tqdm(range(w2, n_samples - w2)):
        s = S[i - w2 : i + w2, :]
        Z[i] = (S[i] - np.average(s, axis=0)[np.newaxis, :]) / np.std(s, axis=0)[
            np.newaxis, :
        ]

    return Z


if __name__ == "__main__":
    with open(sys.argv[1], "r") as fH:
        lines = fH.readlines()

    folders = [Path(line.strip()) for line in lines]

    for folder in folders:
        s2p_folder = Path(folder) / "suite2p" / "plane0"

        logger.info("calculating Z for folder: %s " % folder)

        F = np.load(s2p_folder / "F.npy")
        Fneu = np.load(s2p_folder / "Fneu.npy")
        # dff = calc_dff((F - Fneu).T, verbose=True) # this leads to artifacts
        # dff = calc_dff(F.T, verbose=True) # this has other problems

        # consider this now
        # from https://suite2p.readthedocs.io/en/latest/settings.html#file-input-output-settings
        """
        We neuropil-correct the trace Fout = F - ops['neucoeff'] * Fneu, and then baseline-correct these traces with an ops['baseline'] filter, and then detect spikes.
        """
        # dff = calc_dff((F - 0.7*Fneu).T, verbose=True) # next attempt - fixed offset

        # in seperate script - deducedthat 1 actually removes all
        # was ops[neucoef] = 1?
        Z = calc_z((F - 1 * Fneu).T, verbose=True)  # next attempt - fixed offset

        np.save(s2p_folder / "Z.npy", Z)
