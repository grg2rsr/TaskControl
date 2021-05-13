'''
visualizing the trial type weighting rule

idea: trial probabilities are weighted by 
1) trial difficulty
and 
2) animal engagement into the task

when engagement is high, difficult trials are present,
and when engagement is low, they are downweighted

trial difficulty:
frac successful w history window of N

trial engagement:
trial init time as a frac of max trial init time
average over past n trials 


'''

%matplotlib qt5
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.axes3d import Axes3D, get_test_data
from matplotlib import cm
import numpy as np


# set up a figure twice as wide as it is tall
fig = plt.figure(figsize=plt.figaspect(0.5))

#===============
#  First subplot
#===============
# set up the axes for the first plot
ax = fig.add_subplot(projection='3d')

# plot a 3D surface like in the example mplot3d/surface3d_demo
X = np.arange(0, 1.1, 0.1) # trial difficulty
Y = np.arange(0, 1.1, 0.1) # engagement
X, Y = np.meshgrid(X, Y)

# min max spreading

Z = X*(2*Y-1) + (1-Y)

ax.plot_wireframe(X, Y, Z, rstride=1, cstride=1)
ax.set_xlabel('difficulty')
ax.set_ylabel('engagement')

ax.set_zlim(0, 1)

plt.show()


