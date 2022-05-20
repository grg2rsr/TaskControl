# %%
%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np

with  open('res','r') as fH:
    l = fH.readlines()

samples = np.array([int(ll.strip()) for ll in l])
counts = np.unique(samples, return_counts=True)[1]
print(counts)
print(counts/250)

p_des = np.array([1 ,2, 3, 2, 1])
p_des = p_des / np.sum(p_des)

# a comparison plot
fig, axes = plt.subplots()
bins = np.array(range(0, p_des.shape[0]+1))
axes.hist(samples, bins=bins,edgecolor='black',density=True)
axes.plot(bins[:-1]+0.5, p_des, 'o',color='r')



# %%
