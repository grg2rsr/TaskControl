# %%
import deeplabcut as dlc
from pathlib import Path
import os
from datetime import datetime
import shutil

# path to source videos - the more different the better
video_paths = [
    "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02994_Plumber/2021-10-19_12-10-36_learn_to_choose_v2/bonsai_video.avi",
    "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02995_Poolboy/2021-10-15_14-15-36_learn_to_choose_v2/bonsai_video.avi",
    "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02996_Policeman/2021-10-22_12-19-12_learn_to_choose_v2/bonsai_video.avi",
    "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02997_Therapist/2021-11-10_17-26-31_learn_to_choose_v2/bonsai_video.avi",
    "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02912_Teacher/2021-10-19_10-47-25_learn_to_choose_v2/bonsai_video.avi",
    "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02911_Lumberjack/2021-10-13_09-06-48_learn_to_choose_v2/bonsai_video.avi",
]

working_dir = Path("/media/georg/data/reaching_dlc")
os.chdir(working_dir)

# net_type = "mobilenet_v2_0.75"
net_type = "resnet_50"
date = datetime.now().strftime(
    "%Y-%m-%d"
)  # underscores in times bc colons kill windows paths ...
bodyparts = "paws-spouts-tongue"
training_data_dir = working_dir / (
    "_".join([date, bodyparts, net_type, "training_videos"])
)
os.makedirs(training_data_dir, exist_ok=True)

training_video_paths = []
for path in video_paths:
    path = Path(path)
    session = path.parent.stem
    animal = path.parent.parent.stem
    shutil.copy(path, new_path)
    training_video_paths.append(new_path)

# %%
training_video_paths = []
for path in video_paths:
    path = Path(path)
    session = path.parent.stem
    animal = path.parent.parent.stem
    new_path = training_data_dir / (animal + "_" + session + path.suffix)
    training_video_paths.append(str(new_path))

# %%
config_path = dlc.create_new_project(
    "_".join([date, bodyparts, net_type]), "georg", training_video_paths
)

# %% or load it
# config_path = "/media/georg/data/reaching_dlc/paws_only_mobilenet_v2_0_75-georg-2021-06-03/config.yaml"

# %%
dlc.extract_frames(config_path)
# dlc.extract_frames(config_path, mode="automatic", algo="uniform")
# dlc.extract_frames(config_path, mode="manual")

# %% label frames - this needs to move to a seperate file
dlc.label_frames(config_path)

# %% check labels
dlc.check_labels(config_path)

# %% train network if not done
dlc.create_training_dataset(
    config_path, net_type="mobilenet_v2_0.75", augmenter_type="imgaug"
)
dlc.train_network(config_path)

# %% evaluate training
import pandas as pd
import matplotlib.pyplot as plt

Df = pd.read_csv(
    "/media/georg/data/reaching_dlc/paws_only-georg-2021-06-02/dlc-models/iteration-0/paws_onlyJun2-trainset95shuffle1/train/learning_stats.csv",
    names=["it", "loss", "lr"],
)
fig, axes = plt.subplots()
for lr, group in Df.groupby("lr"):
    axes.plot(group["it"], group["loss"])
plt.show()

# %%
dlc.evaluate_network(config_path, plotting=True)

# # %% analyze videos - specify paths like this
# # vid_paths = ["/media/georg/data/reaching_dlc/JJP-01641/2021-02-18_17-03-20_learn_to_reach/bonsai_video.avi",
# #              "/media/georg/data/reaching_dlc/JJP-01642/2021-02-18_16-33-23_learn_to_reach/bonsai_video.avi"]
# vid_paths = ["/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975/2021-05-18_09-41-58_learn_to_fixate_discrete_v1/bonsai_video.avi"]

# vid_paths = ["/media/georg/data/reaching_dlc/training_videos_for_mobilenet/bonsai_video3.avi"]

# vid_paths = ["/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975/2021-04-27_10-39-35_learn_to_fixate_discrete_v1/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975/2021-04-28_11-59-43_learn_to_fixate_discrete_v1/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-01975/2021-04-29_11-16-15_learn_to_fixate_discrete_v1/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02164/2021-05-28_13-20-27_learn_to_choose/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02164/2021-05-27_15-31-36_learn_to_choose/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02164/2021-05-26_14-59-47_learn_to_choose/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02165/2021-05-27_15-41-15_learn_to_choose/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02165/2021-05-26_15-20-18_learn_to_choose/bonsai_video.avi",
#              "/media/georg/htcondor/shared-paton/georg/Animals_reaching/JJP-02165/2021-05-25_13-44-27_learn_to_choose/bonsai_video.avi"]


# %%

dlc.analyze_videos(
    config_path, vid_paths
)  # seems like it crashed with dynamic, dynamic=(True, 0.5, 10))

# %% opt - filter pred
dlc.filterpredictions(config_path, vid_paths)  # this is a median
# dlc.filterpredictions(config_path,vid_paths, filtertype= 'arima', ARdegree=5, MAdegree=2) #arima

# %%
dlc.create_labeled_video(config_path, vid_paths, fastmode=True, filtered=True)
