import pandas as pd
from pathlib import Path
path = Path("D:/TaskControl/Animals/123/2020-06-02_18-24-47_headfix_timing_dev/bonsai_harp_log.csv")

with open(path,'r') as fH:
    lines = fH.readlines()

events = []
reads = []
# filter
for line in lines:
    if line[0] == '1':
        reads.append(line)
    if line[0] == '3':
        events.append(line)