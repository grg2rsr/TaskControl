# %%
%matplotlib qt5
%load_ext autoreload
%autoreload 2

sys.path.append('..')

from matplotlib import pyplot as plt
import matplotlib as mpl
# mpl.rcParams['figure.dpi'] = 331
mpl.rcParams['figure.dpi'] = 166 # the screens in the viv
from Utils import utils
from Utils import behavior_analysis_utils as bhv
import pandas as pd
from pathlib import Path

import os

# %%
# Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
Nicknames = ['Poolboy']
task_name = 'learn_to_choose_v2'

# get animals by Nickname
Animals_folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(Animals_folder)

Animals = [a for a in Animals if a.Nickname in Nicknames]

# %%
Animal = Animals[0]
SessionsDf = utils.get_sessions(Animal.folder).groupby('task').get_group(task_name)

video_paths = []
for i, row in SessionsDf.iterrows():
    session_folder = Path(row['path'])
    video_paths.append(str(session_folder / 'bonsai_video.avi'))

with open(Animal.folder / 'video_paths.txt' ,'w') as fH:
    for video_path in video_paths:
        fH.write(video_path+'\n')

# %%
