import os

import data_reduction
import numpy as np
import pandas as pd
from scipy import linalg
import fastutm
import swifter
import pickle
import io
from google.cloud import storage
import json
import s2cell
import math

BUCKET_NAME = os.getenv("NPY_BUCKET_NAME")
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def generate(x_ref, y_ref, z_ref,
             utm_zone=33, compression_type="float16",
             downsampling_factor=1) \
        -> (pd.DataFrame, bytes, bytes):
    """
    This function will take in the raw data in the form of .npy tiles and create a model that can be used to interpolate
    for new wind directions. The model will be returned in a way that can be immediately uploaded to a SQL database, or stored as a file.
    If a downsampling factor is specified (larger than 1), then the model will be generated for a lower resolution
    This is done by downsampling the individual snapshot matrices (for details refer to the downsampling function).

    :param x_ref: x-position of the reference sensor in UTM coordinate system
    :param y_ref: x-position of the reference sensor in UTM coordinate system
    :param z_ref: x-position of the reference sensor in UTM coordinate system
    :param utm_zone: UTM zone that is used for the UTM coordinates
    :param compression_type: datatype to which the calculated interpolation parameters will be compressed to. float16 has proven to
    barely yield any significant loss in accuracy in this use case
    :param downsampling_factor: specifies how much downsampling should be applied. Tiles will be aggregated to larger square tiles of
    downsampling_factor x downsampling_factor many sub-tiles. Should ideally a power of 2 (wasn't tested with anything else, so good luck if not),
    if =1, then no aggregation
    :return: dataframe with coordinates (UTM + lat/lon), geohashes, and the interpolation parameters. Also, A and WDref encoded as bytestrings
    """
    agg_vote_share = get_reasonable_share_value(downsampling_factor)
    x_axis, y_axis, z_axis, Psi, means, A, WDref = pod_model(x_ref, y_ref, z_ref,
                                                             compression_type=compression_type,
                                                             downsampling_factor=downsampling_factor,
                                                             agg_vote_share=agg_vote_share)

    # extract the 3 wind components from the result
    U, V, W = np.split(Psi, [len(Psi) // 3, 2 * len(Psi) // 3])
    Umean, Vmean, Wmean = np.split(means, [len(means) // 3, 2 * len(means) // 3])

    #create dataframe and will it with the UTM coordinates of the datapoints
    df = pd.DataFrame()
    df["x"] = pd.Series(x_axis)
    df["y"] = pd.Series(y_axis)
    df["z"] = pd.Series(z_axis)
    del x_axis, y_axis, z_axis

    #compute lat/lon coordinates from UTM, and also the geohashes
    df["lat"] = df.swifter.apply(lambda row: fastutm.to_latlon(row.x, row.y, zone_number=utm_zone, northern=True)[0],
                                 axis=1)
    df["lat"] = df["lat"].astype("float32")
    df["lon"] = df.swifter.apply(lambda row: fastutm.to_latlon(row.x, row.y, zone_number=utm_zone, northern=True)[1],
                                 axis=1)
    df["lon"] = df["lon"].astype("float32")

    # the s2 cell id precision is dependent on the downsampling factor for chunking
    # {1 : 17, 2 : 16, 4 : 15, 8 : 14, 16 : 13, 32 : 12}
    downsampling_to_cell_level = int(17 - math.log2(downsampling_factor))
    print(json.dumps({"message": f"Cell Level: {downsampling_to_cell_level}", "severity": "INFO"}))
    df["s2_cell"] = df.swifter.apply(lambda row: s2cell.lat_lon_to_cell_id(row.lat, row.lon, downsampling_to_cell_level), axis=1)

    #add the interpolation parameters to each datapoint in the dataframe
    df["mean_u"] = pd.Series(Umean)
    del Umean
    df["mean_v"] = pd.Series(Vmean)
    del Vmean
    df["mean_w"] = pd.Series(Wmean)
    del Wmean

    degs = list(np.load(download_file_bytes("wd.npy")))
    for i, deg in enumerate(degs):
        df[f"u_{deg}"] = pd.Series(U[:, i])
        df[f"v_{deg}"] = pd.Series(V[:, i])
        df[f"w_{deg}"] = pd.Series(W[:, i])

    del U, V, W
    #return the big dataframe, as well as binary encoding of the small helper-matrices A and WDref
    return df, pickle.dumps(A), pickle.dumps(WDref)


def get_reasonable_share_value(downsampling_factor):
    if downsampling_factor == 1:
        return 1
    else:
        return 0.95 ** downsampling_factor


def download_file_bytes(file_name):
    blob = bucket.blob(file_name)
    print(json.dumps({"message": f"Downloading {file_name} from bucket", "severity": "INFO"}))
    downloaded_bytes = blob.download_as_bytes()
    return io.BytesIO(downloaded_bytes)


def pod_model(x_ref, y_ref, z_ref,
              compression_type="float16", downsampling_factor=1, agg_vote_share=2 / 3):
    """
    Credit to Carola Ebert, she wrote most of the code used in this function

    Helper function for the generate-function
    Takes care the actual math using numpy arrays, as well as loading the input-files from the filesystem
    Downsampling is also applied during this step

    Arguments are similar to generate() above, so refer to its documentation
    :return: axis-arrays and interpolation parameters
    """
    #load UTM coordinates of datapoints
    x_axis = np.int32(np.load(download_file_bytes("x.npy")))
    y_axis = np.int32(np.load(download_file_bytes("y.npy")))
    z_axis = np.float32(np.load(download_file_bytes("z.npy")))

    idxRef = locate(x_axis, y_axis, z_axis, x_ref, y_ref, z_ref)  #locate index of reference sensor

    #load snapshot matrices
    Ux = np.float32(np.load(download_file_bytes("Ux.npy")))  # [:, sample] <-- if you see this comment, ignore it
    Uy = np.float32(np.load(download_file_bytes("Uy.npy")))
    Uz = np.float32(np.load(download_file_bytes("Uz.npy")))
    Umag = np.sqrt(Ux ** 2 + Uy ** 2 + Uz ** 2)

    #extract values for reference sensor
    Uxref = Ux[:, idxRef]
    Uyref = Uy[:, idxRef]
    Uref = Umag[:, idxRef]
    WDref = ((np.arctan2(Uxref, Uyref) * 180 / np.pi) + 180)

    #downsample snapshot matrices if specified
    if downsampling_factor != 1:
        Ux, Uy, Uz, x_axis, y_axis, z_axis = data_reduction.downsample(Ux, Uy, Uz, x_axis, y_axis, z_axis,
                                                                       downsampling_factor,
                                                                       agg_vote_share=agg_vote_share)

    #do the POD stuff to compute the interpolation parameters
    X = np.concatenate((Ux / Uref[:, None], Uy / Uref[:, None], Uz / Uref[:, None]), axis=1)
    del Ux, Uy, Uz, Uref

    Xmean = X.mean(axis=0)
    Xsvd = X - Xmean
    del X

    Psi, Sig, R = linalg.svd(Xsvd.T, full_matrices=False)
    del Xsvd
    diagSig = np.diag(Sig)
    A = np.dot(diagSig, R)

    Psi = Psi
    return x_axis.astype("int32"), y_axis.astype("int32"), z_axis.astype("int16"), Psi.astype(
        compression_type), Xmean.astype(compression_type), A, WDref


def locate(x_axis, y_axis, z_axis, x_ref, y_ref, z_ref):
    """
    Helper function to convert the UTM coordinates of the reference sensor to the datapoint index in the input-dataset-matrices
    """
    dist = np.sqrt((np.float32(x_axis) - x_ref) ** 2 + (np.float32(y_axis) - y_ref) ** 2 + (z_axis - z_ref) ** 2)
    idxRef = dist.argmin()
    return idxRef
