import sys, os
from pathlib import Path
from tqdm import tqdm

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle
import seaborn as sns

import scipy as sp
import numpy as np
import pandas as pd
import cv2

sys.path.append('/home/georg/code/TaskControl')
from Utils import utils
from Utils import behavior_analysis_utils as bhv
from Utils import dlc_analysis_utils as dlc
import Utils.metrics as metrics
from Utils.sync import Syncer

colors = dict(success="#72E043", 
              reward="#3CE1FA", 
              correct="#72E043", 
              incorrect="#F56057", 
              premature="#9D5DF0", 
              missed="#F7D379",
              left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95))


# actress
Animal_path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03344_Actress"
# secretary
Animal_path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03345_Secretary"
# nurse
Animal_path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03346_Nurse"
# firefigher
Animal_path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03437_Firefighter"
# priest
Animal_path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03440_Priest"
# sailor
Animal_path = "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03441_Sailor"

Animal = utils.Animal(Animal_path)
SessionsDf = utils.get_sessions(Animal.folder)

for i, row in SessionsDf.iterrows():
    session_folder = Path(row['path'])

    # session_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-03345_Secretary/2021-12-20_12-56-31_interval_categorization_v1")
    os.chdir(session_folder)

    ### Camera data
    video_path = session_folder / "bonsai_video.avi"
    Vid = dlc.read_video(str(video_path))


    frame_ix = 5000
    frame = dlc.get_frame(Vid, frame_ix)

    fig, axes = plt.subplots()
    axes.matshow(frame, cmap='Greys_r')

    Coords = {}
    def onclick(event):
        x, y = event.xdata, event.ydata
        outpath = session_folder / 'spout_coords.csv'

        if event.button == 1:
            print('left spout: %.2f %.2f' % (x, y))
            Coords['left'] = (x, y)

            print('saving to %s' % outpath)
            Df = pd.DataFrame(Coords)
            Df.to_csv(outpath)

        if event.button == 3:
            print('right spout: %.2f %.2f' % (x, y))
            Coords['right'] = (x, y)

            print('saving to %s' % outpath)
            Df = pd.DataFrame(Coords)
            Df.to_csv(outpath)

    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()

# spout_r = (376, 271)
# spout_l = (372, 198)

# spout_l = (361, 211)
# spout_r = (365, 283)

# w = 10 # px
# sides = ['left','right']
# for side, spout in zip(sides, [spout_l, spout_r]):
#     x, y = spout
#     xs = [x-w, x-w, x+w, x+w, x-w]
#     ys = [y+w, y-w, y-w, y+w, y+w]
#     axes.plot(xs,ys,color=colors[side])