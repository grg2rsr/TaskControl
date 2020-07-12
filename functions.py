import scipy as sp
from scipy import stats
import pandas as pd
import os



def get_valve_slope(time_vec, water_vec):

    res = stats.linregress(time_vec, water_vec)
    m,b = res.slope,res.intercept

    return m
