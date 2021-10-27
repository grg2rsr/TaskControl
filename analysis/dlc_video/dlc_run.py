from pathlib import Path
import sys, os
import deeplabcut as dlc

""" 
intended use:
first argument is path to a file that has line seperated the filepaths of the video to track
"""

# get the file names
with open(sys.argv[1],'r') as fH:
    video_paths = [path.strip() for path in fH.readlines()]

# select the the network
# config_path = "/media/georg/data/reaching_dlc/paws_only-georg-2021-06-02/config.yaml" # a resnet
config_path = "/media/georg/data/reaching_dlc/paws_only_mobilenet_v2_0_75-georg-2021-06-03/config.yaml" # the mobilenet

print(video_paths)
dlc.analyze_videos(config_path, video_paths)
