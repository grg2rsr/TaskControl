import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger("data_structures.py")
# from my_logging import get_logger
# logger = get_logger()


def time_slice_array(A, tvec, slice_times, pre, post):
    # slice
    A_slices = []
    for t in slice_times:
        ix = np.logical_and(tvec > t + pre, tvec < t + post)
        A_slices.append(A[ix])
    return A_slices


def time_slice_timestamps(T, slice_times, pre, post, relative=True):
    T_slices = []
    for t in slice_times:
        ix = np.logical_and(T > t + pre, T < t + post)
        if relative:
            T_slices.append(T[ix] - t)
        else:
            T_slices.append(T[ix])
    return T_slices


###
# def stack_array_slices(A_slices):
#     # stack if possible
#     shapes = np.array([A_slice.shape[0] for A_slice in A_slices])
#     if np.all(shapes == shapes[0]):
#         return np.stack(A_slices, axis=2)

# logger.warning("can't stack array slices")
# # if not - fallback_mode
# uniques, counts = np.unique(shapes, return_counts=True)

# for i in range(uniques.shape[0]):
#     logger.warning("shape: %i, count:%i" % (uniques[i],counts[i]))

# if fallback_mode == "jagged":
#     return stack_jagged(A_slices)
# if fallback_mode == "truncate":
#     return stack_truncated(A_slices)

# if fallback_mode == "interpolate":
#     return stack_interp(A_slices)
# return None


def stack_jagged(A_slices, fill_value=np.nan):
    shapes = np.array([A_slice.shape[0] for A_slice in A_slices])
    max_shape = np.max(shapes)
    J = np.zeros((max_shape, A_slices[0].shape[1], len(A_slices)))
    J[:] = fill_value
    for j in range(len(A_slices)):
        J[: shapes[j], :, j] = A_slices[j]
    return J


def stack_truncated(A_slices):
    shapes = np.array([A_slice.shape[0] for A_slice in A_slices])
    min_shape = np.min(shapes)
    T = np.zeros((min_shape, A_slices[0].shape[1], len(A_slices)))
    for j in range(len(A_slices)):
        T[:, :, j] = A_slices[j][:min_shape, :]
    return T


def stack_interp(A_slices, t_slices, t_target):
    from scipy.interpolate import interp1d

    A_slices_interp = []
    for i in range(len(A_slices)):
        A_slices_interp.append(
            interp1d(t_slices[i], A_slices[i], axis=0, fill_value="extrapolate")(
                t_target
            )
        )
    return np.stack(A_slices_interp, axis=2)


@dataclass
class Signal:
    y: np.ndarray
    t: np.ndarray
    ids: np.ndarray = None

    def __post_init__(self):
        self.dt = np.diff(self.t)[0]
        self.fs = 1 / self.dt
        self.n = self.y.shape[1]
        self.n_samples = self.t.shape[0]
        self.shape = self.y.shape
        if self.ids is None:
            self.ids = np.arange(self.n)

    def reslice(
        self, slice_times: np.ndarray, pre: np.float32, post: np.float32, mode="jagged"
    ):
        # FIXME WARNING - currently always interpolates!!!

        self.slice_times = slice_times
        self.pre = pre
        self.post = post
        self.t_slice = np.arange(self.pre, self.post, self.dt)

        self.y_resliced = time_slice_array(self.y, self.t, slice_times, pre, post)
        self.t_resliced = time_slice_timestamps(self.t, slice_times, pre, post)

        self.resliced = stack_interp(self.y_resliced, self.t_resliced, self.t_slice)
        # self.resliced = stack_array_slices(self.resliced, fallback_mode=fallback_mode)

    def resort(self, labels):
        """requires reslice first"""
        self.resorted = {}
        labels_unique = np.unique(labels)
        for label in labels_unique:
            ix = np.where(labels == label)[0]
            self.resorted[label] = self.resliced[:, :, ix]

    def zscore(self, overwrite=True):
        # overwrite? otherwise doubles memory footprint
        # but also simplifies reslice

        mu = np.average(self.y, axis=0)[np.newaxis, :]
        sig = np.std(self.y, axis=0)[np.newaxis, :]
        if overwrite:
            self.y = (self.y - mu) / sig
        else:
            self.z = (self.y - mu) / sig

    def select(self, ids_sel):
        ix = [self.ids.index(i) for i in ids_sel]
        self.y = self.y[:, ix]
        self.ids = ids_sel
        self.n = self.y.shape[1]
        self.shape = self.y.shape

    def __getitem__(self, args):
        return self.y[args]

    def __setitem__(self, args, value):
        self.y[args] = value


# @dataclass
# class Spikes():
#     spike_times: np.ndarray
#     spike_templates: np.ndarray
#     unit_ids: np.ndarray = None

#     def __post_init__(self):
#         if self.unit_ids is None:
#             self.unit_ids = np.sort(np.unique(self.spike_templates))

#         self.times = {}
#         for unit_id in self.unit_ids:
#             ix = np.where(self.spike_templates == unit_id)[0]
#             self.times[unit_id] = self.spike_times[ix]


#     def reslice(self, slice_times: np.ndarray, pre: np.float32, post: np.float32):
#         return reslice_timestamps()
