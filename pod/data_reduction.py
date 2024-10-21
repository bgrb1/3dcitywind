from functools import partial

import numpy as np
import skimage


default_scale = 2 # 2x2 tiles at highest resolution

def downsample(Ux, Uy, Uz, x, y, z, downsampling_factor, agg_vote_share=2 / 3):
    """
    Downsamples the input to a lower resolution
    Downsampling will be performed per each snapshot matrix and altitude layer (so in 2D space)
    !! No aggregation accross wind fields or altitudes
    Downsampling is done by splitting the existing grid into larger square blocks of same size and aggregating each block
    Aggregation-function is vote_mean (see below)
    The new grid will have both surface dimensions roughly divided by downsampling_factor,
    and the amount of datapoints by downsampling_factor^2
    In reality, expect a little less values, as there will likely be tiles that disappear due to the nature of vote_mean
    :param Ux: Snapshot matrices for first wind component
    :param Uy: Snapshot matrices for second wind component
    :param Uz: Snapshot matrices for third wind component
    :param x: x axis
    :param y: y axis
    :param z: z axis
    :param downsampling_factor: specifies how much downsampling should be applied. Tiles will be aggregated to larger square tiles of
    downsampling_factor x downsampling_factor many sub-tiles. Should ideally a power of 2 (wasn't tested with anything else, so good luck if not),
    if =1, then effectively no aggregation
    :param agg_vote_share: required share of present tiles for vote_mean
    :return: same values as for the input, but at lower resolution
    """
    def downsample_component(c, x, y, z):
        """
        Helper function to downsample a wind component
        :return: downsampled snapshot matrices for component and coordinates
        """
        def vote_mean(share, x, axis):
            """
            Aggregation function
            result shape will be same as for normal np.mean
            Result for each block will be either the np.nanmean, or NaN if there are are less tiles present than the required share
            """
            s = (x*0)+1
            s = np.nansum(s, axis=axis)
            area = 1
            for a in axis:
                area = area * x.shape[a]
            x = np.nanmean(x, axis=axis)
            x[s < area*share] = np.nan #delete all blocks that didnt reach required share of present tiles
            return x

        #create empty grid
        C = np.empty((len(z_map), 1 + (x_max - x_min) // default_scale, 1 + (y_max - y_min) // default_scale, c.shape[0]))
        C[:] = np.nan

        C[z.astype("int32"), x, y] = c.T #fill grid with the values of c at the coordinates specified by x,y,z

        C = C.transpose((3, 0, 1, 2))
        #downsample component by aggregating tiles of snapshot matrices at each altitude at downsample_factor x downsample_factor tile size
        C = skimage.measure.block_reduce(C,
                                         (1, 1, downsampling_factor, downsampling_factor),
                                         partial(vote_mean, agg_vote_share),
                                         cval=np.nan)

        wd1x = C[0, :, :, :]
        coords = np.nonzero(~np.isnan(wd1x)) #find remaining coordinates that have been aggreated to a value other than NaN
        #mean_before = np.mean(c)
        c = C[:, coords[0], coords[1], coords[2]]
        #mean_after = np.mean(c)  # if aggregation was correct, mean should be roughly the same
        return c, coords

    #convert UTM to matrix coords
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)
    x = (x-x_min)//default_scale
    y = (y-y_min)//default_scale
    z_map = []
    for i,a in enumerate(np.unique(z)):
        z[z == a] = i
        z_map.append((i,a))

    #downsample indvidual wind components by downsampling each snapshot matrix
    Ux, coords = downsample_component(Ux,x,y,z)
    Uy, _ = downsample_component(Uy,x,y,z)
    Uz, _ = downsample_component(Uz,x,y,z)

    #convert matrix coordinates back to UTM
    z_int = np.array(coords[0])
    z = np.zeros_like(coords[0], dtype="float32")
    for i,a in z_map:
        z[z_int == i] = a
    x = ((np.array(coords[1]) * downsampling_factor) + (downsampling_factor / 2)) * default_scale - 1 + x_min
    y = ((np.array(coords[2]) * downsampling_factor) + (downsampling_factor / 2)) * default_scale - 1 + y_min
    return Ux, Uy, Uz, x, y, z



def sample(x,y,z, x_ref, y_ref, z_ref, sampling_factor):
    """
    Alternative reduction function that chooses a sample of the datapoints
    Will sparsify the grid instead of creating lower-resolution tiles
    Not used right now
    """
    sample = np.random.choice(x.shape[0], x.shape[0] // sampling_factor, replace=False)
    idxRef = np.int_(np.where((x == x_ref) & (y == y_ref) & (z == z_ref)))[0]
    if not np.any(idxRef[:] == sample):
        sample = np.append(sample, [idxRef])
    sample = np.sort(sample)
    x = x[sample]
    y = y[sample]
    z = z[sample]
    return x,y,z