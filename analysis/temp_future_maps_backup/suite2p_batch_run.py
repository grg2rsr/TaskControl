# %%
import numpy as np
from pathlib import Path
import sys
import os
import suite2p

from my_logging import get_logger

logger = get_logger(level="INFO")

# defaults
ops = suite2p.default_ops()
ops["tau"] = 0.7
ops["fs"] = 30
ops["fast_disk"] = "/home/georg/data/local_suite2p/"

if __name__ == "__main__":
    with open(sys.argv[1], "r") as fH:
        lines = fH.readlines()

    folders = [Path(line.strip()) for line in lines]

    for folder in folders:
        os.chdir(folder)

        logger.info("suite2p run on folder: %s" % folder)
        db = {}
        db["data_path"] = [folder]
        db["tiff_list"] = list(
            np.sort([f for f in os.listdir(folder) if f.endswith(".tif")])
        )
        output_ops = suite2p.run_s2p(ops=ops, db=db)
