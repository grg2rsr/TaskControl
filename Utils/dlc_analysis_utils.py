import matplotlib.pyplot as plt
import scipy as sp
import numpy as np
import pandas as pd
import cv2
import seaborn as sns

"""
 
 ########  ########    ###    ########  
 ##     ## ##         ## ##   ##     ## 
 ##     ## ##        ##   ##  ##     ## 
 ########  ######   ##     ## ##     ## 
 ##   ##   ##       ######### ##     ## 
 ##    ##  ##       ##     ## ##     ## 
 ##     ## ######## ##     ## ########  
 
"""


def read_dlc_csv(path):
    """reads Dlc csv output to hierarchical multiindex (on columns) pd.DataFrame"""
    DlcDf = pd.read_csv(path, header=[1, 2], index_col=0)
    return DlcDf


def read_dlc_h5(path):
    """much faster than read_dlc_csv()"""
    DlcDf = pd.read_hdf(path)
    DlcDf = DlcDf[DlcDf.columns.levels[0][0]]
    return DlcDf


def read_video(path):
    Vid = cv2.VideoCapture(str(path))
    return Vid


"""
 
 ########  ##        #######  ######## 
 ##     ## ##       ##     ##    ##    
 ##     ## ##       ##     ##    ##    
 ########  ##       ##     ##    ##    
 ##        ##       ##     ##    ##    
 ##        ##       ##     ##    ##    
 ##        ########  #######     ##    
 
"""


def get_frame(Vid, i):
    """Vid is cv2 VideoCapture obj"""
    Vid.set(1, i)
    Frame = Vid.read()[1][:, :, 0]  # fetching r, ignoring g b, all the same
    # TODO check if monochrome can be specified in VideoCaputre
    return Frame


def plot_frame(Frame, axes=None, **im_kwargs):
    if axes is None:
        fig, axes = plt.subplots()
        axes.set_aspect("equal")

    defaults = dict(cmap="gray")
    for k, v in defaults.items():
        im_kwargs.setdefault(k, v)

    axes.imshow(Frame, **im_kwargs)
    return axes


def plot_bodyparts(bodyparts, DlcDf, i, colors=None, axes=None, **marker_kwargs):
    """i = frame_ix"""
    if axes is None:
        fig, axes = plt.subplots()

    if colors is None:
        c = sns.color_palette("viridis", n_colors=len(bodyparts))
        colors = dict(zip(bodyparts, c))

    df = DlcDf.loc[i]
    for bp in bodyparts:
        axes.plot(df[bp].x, df[bp].y, "o", color=colors[bp], **marker_kwargs)

    return axes


def plot_Skeleton(Skeleton, DlcDf, i, axes=None, **line_kwargs):
    if axes is None:
        fig, axes = plt.subplots()

    defaults = dict(lw=1, alpha=0.5, color="k")
    for k, v in defaults.items():
        line_kwargs.setdefault(k, v)

    df = DlcDf.loc[i]

    lines = []
    for node in Skeleton:
        (line,) = axes.plot(
            [df[node[0]].x, df[node[1]].x],
            [df[node[0]].y, df[node[1]].y],
            **line_kwargs,
        )
        lines.append(line)

    return axes, lines


def plot_trajectories(DlcDf, bodyparts, axes=None, colors=None, p=0.99, **line_kwargs):
    if axes is None:
        fig, axes = plt.subplots()
        axes.set_aspect("equal")

    if colors is None:
        c = sns.color_palette("viridis", n_colors=len(bodyparts))
        colors = dict(zip(bodyparts, c))

    defaults = dict(lw=0.05, alpha=0.85)
    for k, v in defaults.items():
        line_kwargs.setdefault(k, v)

    for bp in bodyparts:
        df = DlcDf[bp]
        ix = df.likelihood > p
        df = df.loc[ix]
        axes.plot(df.x, df.y, color=colors[bp], **line_kwargs)

    return axes


"""
 
    ###    ##    ##    ###    ##       ##    ##  ######  ####  ######  
   ## ##   ###   ##   ## ##   ##        ##  ##  ##    ##  ##  ##    ## 
  ##   ##  ####  ##  ##   ##  ##         ####   ##        ##  ##       
 ##     ## ## ## ## ##     ## ##          ##     ######   ##   ######  
 ######### ##  #### ######### ##          ##          ##  ##        ## 
 ##     ## ##   ### ##     ## ##          ##    ##    ##  ##  ##    ## 
 ##     ## ##    ## ##     ## ########    ##     ######  ####  ######  
 
"""


def box2rect(center, w):
    """definition: x1,y1, x2,y2"""
    w2 = int(w / 2)
    return (center[0] - w2, center[1] - w2, center[0] + w2, center[1] + w2)


def rect2cart(rect):
    """helper for matplotlib"""
    xy = (rect[0], rect[1])
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]
    return xy, width, height


def get_in_box(DlcDf, bp, rect, p=0.99, filter=False):
    """returns boolean vector over frames if bodypart is in
    rect and returns boolean index for above pred above likelihood"""

    df = DlcDf[bp]
    x_true = sp.logical_and((df.x > rect[0]).values, (df.x < rect[2]).values)
    y_true = sp.logical_and((df.y > rect[1]).values, (df.y < rect[3]).values)
    in_box = sp.logical_and(x_true, y_true)
    good_ix = (df.likelihood > p).values
    if filter is False:
        return in_box, good_ix
    else:
        in_box[~good_ix] = False
        return in_box


def in_box_span(DlcDf, bp, rect, p=0.99, min_dur=20, convert_to_time=True):
    """returns a SpansDf for body part in box times"""

    in_box = get_in_box(DlcDf, bp, rect, p=p, filter=True)

    df = pd.DataFrame(columns=["t_on", "t_off"])

    ons = sp.where(sp.diff(in_box.astype("int32")) == 1)[0]
    offs = sp.where(sp.diff(in_box.astype("int32")) == -1)[0]

    ts = []
    for t_on in ons:
        binds = offs > t_on
        if np.any(binds):
            t_off = offs[np.argmax(binds)]
            ts.append((t_on, t_off))

    SpansDf = pd.DataFrame(ts, columns=["t_on", "t_off"])
    SpansDf["dt"] = SpansDf["t_off"] - SpansDf["t_on"]

    # filter min dur
    SpansDf = SpansDf[SpansDf.dt > min_dur]

    # if convert_to_time:
    #     SpansDf = pd.DataFrame(frame2time(SpansDf.values,m,b,m2,b2),columns=SpansDf.columns)

    return SpansDf


"""
 
 ##     ## ######## ######## ########  ####  ######   ######  
 ###   ### ##          ##    ##     ##  ##  ##    ## ##    ## 
 #### #### ##          ##    ##     ##  ##  ##       ##       
 ## ### ## ######      ##    ########   ##  ##        ######  
 ##     ## ##          ##    ##   ##    ##  ##             ## 
 ##     ## ##          ##    ##    ##   ##  ##    ## ##    ## 
 ##     ## ########    ##    ##     ## ####  ######   ######  
 
"""


def calc_dist_bp_point(DlcDf, bp, point, p=0.99, filter=False):
    """euclidean distance bodypart to point"""
    df = DlcDf[bp]
    D = sp.sqrt(sp.sum((df[["x", "y"]].values - sp.array(point)) ** 2, axis=1))
    good_ix = (df.likelihood > p).values
    if filter is False:
        return D, good_ix
    else:
        D[~good_ix] = sp.nan
        return D


def calc_dist_bp_bp(DlcDf, bp1, bp2, p=0.99, filter=False):
    """euclidean distance between bodyparts"""

    df1 = DlcDf[bp1]
    df2 = DlcDf[bp2]

    c1 = df1[["x", "y"]].values
    c2 = df2[["x", "y"]].values

    good_ix = sp.logical_and((df1.likelihood > p).values, (df2.likelihood > p).values)

    d = sp.sqrt(sp.sum((c1 - c2) ** 2, axis=1))
    if filter is False:
        return d, good_ix
    else:
        d[~good_ix] = sp.nan
        return d


def get_speed(DlcDf, bp, p=0.99, filter=False):
    """bodypart speed over time in px/ms"""
    Vxy = (
        sp.diff(DlcDf[bp][["x", "y"]].values, axis=0)
        / DlcDf["t"][:-1].values[:, sp.newaxis]
    )
    V = sp.sqrt(sp.sum(Vxy**2, axis=1))  # euclid vector norm
    V = V / sp.diff(DlcDf["t"].values)  # -> to speed

    V = sp.concatenate([[sp.nan], V])  # pad first to nan (speed undefined)
    good_ix = (DlcDf[bp].likelihood > p).values

    if filter is False:
        return V, good_ix
    else:
        V[~good_ix] = sp.nan
        return V
