import sys
import os
from pathlib import Path
from tqdm import tqdm

import matplotlib as mpl

import numpy as np
import pandas as pd

sys.path.append("/home/georg/code/TaskControl")
from Utils import utils
from Utils import dlc_analysis_utils as dlc

colors = dict(
    success="#72E043",
    reward="#3CE1FA",
    correct="#72E043",
    incorrect="#F56057",
    premature="#9D5DF0",
    missed="#F7D379",
    left=mpl.cm.PiYG(0.05),
    right=mpl.cm.PiYG(0.95),
)

# get animals and all sessions
Animals_folder = "/media/georg/htcondor/shared-paton/georg/Animals_reaching"
Animals = utils.get_Animals(Animals_folder)
Nicknames = ["Actress", "Secretary", "Nurse", "Firefighter", "Priest", "Sailor"]
Nicknames = ["Secretary"]

for nickname in Nicknames:
    print("processing Animals: %s" % nickname)
    (Animal,) = utils.select(Animals, Nickname=nickname)
    SessionsDf = utils.get_sessions(Animal.folder)

    w = 10

    for i, row in SessionsDf.iterrows():
        session_folder = Path(row["path"])
        os.chdir(session_folder)
        if (session_folder / "optical_reaches_left.npy").exists():
            print("skipping folder %s" % session_folder)
        else:
            print("processing folder %s" % session_folder)

            ### Camera data
            video_path = session_folder / "bonsai_video.avi"
            Vid = dlc.read_video(str(video_path))

            # get coordinates
            Df = pd.read_csv(session_folder / "spout_coords.csv")
            spout_l = Df["left"].values.astype("int32")
            spout_r = Df["right"].values.astype("int32")

            # extract reaches from video
            fps = Vid.get(5)
            n_frames = int(Vid.get(7))

            vid_dur = n_frames / fps

            reach_left = np.zeros(n_frames)
            reach_right = np.zeros(n_frames)

            for i in tqdm(range(n_frames)):
                frame = dlc.get_frame(Vid, i)
                reach_left[i] = np.average(
                    frame[
                        spout_l[1] - w : spout_l[1] + w, spout_l[0] - w : spout_l[0] + w
                    ]
                )
                reach_right[i] = np.average(
                    frame[
                        spout_r[1] - w : spout_r[1] + w, spout_r[0] - w : spout_r[0] + w
                    ]
                )

            np.save(session_folder / "optical_reaches_left.npy", reach_left)
            np.save(session_folder / "optical_reaches_right.npy", reach_right)
