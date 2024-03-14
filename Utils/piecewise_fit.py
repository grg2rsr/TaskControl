# %%
%matplotlib qt5
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

def lin(x, m, b):
    return m * x + b

def quad(x, x0, a, b, c):
    return a*(x-x0)**2 + b*(x-x0) + c

def cube(x, x0, a, b, c, d):
    return a*(x-x0)**3 + b*(x-x0)**2 + c*(x-x0) + d

def poly(x, x0, *a):
    return np.sum(np.array([a[i]*(x-x0)**i for i in range(len(a))]),axis=0)

def polyv(x, *args):
    n = int(len(args)/2)
    x0 = args[:n]
    a = args[n:]
    return np.sum(np.array([a[i]*(x-x0[i])**i for i in range(len(a))]),axis=0)

x = np.linspace(0,100,101)
y = polyv(x,50,0,50,20,0,2,2,2)
# y = poly(x,50,0,2,2,2)
plt.plot(x,y)

p0 = ()

n = 5
rem = x.shape[0] % n
np.split(x,4)

# %% full piecewise
n = data_a.shape[0]
ps = []
for i in range(1,n):
    x1,x2 = data_a[i-1],data_a[i]
    y1,y2 = data_b[i-1],data_b[i]
    m = (y2-y1)/(x2-x1)
    b = -m * x1 + y1
    ps.append((m,b))


if x < data_a[0]:
    m,b = ps[0]
elif x > data_a[-1]:
    m,b = ps[-1]
else:
    binds = np.logical_and(data_a > x, data_a < x)

# %% 
x = data_a[-1] + 10

def _convert_single(x, data_a, ps):
    bv = data_a < x
    if np.all(bv):
        m, b = ps[-1]
    elif np.all(~bv):
        m, b = ps[0]
    else:
        i = np.argmin(bv)
        m, b = ps[i-1]
    return m * x + b

def convert(x, data_a, ps):
    x = np.array(x)
    if x.shape == ():
        return _convert_single(x, data_a, ps)
    else:
        return np.array(_convert_single(_x, data_a, ps) for _x in x)

convert(np.linspace(0,1,10), data_a, ps)

# %%

# def guess_p0(self, func, A, B):
#     if func == lin:
#         b = A[0]
#         m = (B[-1] - B[0]) / (A[-1] - A[0])
#         return (m,b)

#     if func == quad:
#         x0 = (A.max() - A.min()) / 2
#         a = 0
#         b = (B[-1] - B[0]) / (A[-1] - A[0])
#         c = A[0]
#         return (x0,a,b,c)

#     if func == cube:
#         x0 = (A.max() - A.min()) / 2
#         a = 0
#         b = 0
#         c = (B[-1] - B[0]) / (A[-1] - A[0])
#         d = A[0]
#         return (x0,a,b,c,d)
# %%

