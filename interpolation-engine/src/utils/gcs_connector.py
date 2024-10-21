import io
import hashlib
import os
import pickle

import pandas as pd
from google.cloud import storage
from google.api_core.retry import Retry

storage_client = storage.Client()
BUCKET_NAME = os.getenv('CHUNK_BUCKET')
bucket = storage_client.bucket(BUCKET_NAME)
root = "pre-calculation"

#Exponential back-off config for cloud storage
custom_retry = Retry(
    initial=0.2,
    multiplier=3,
    deadline=5.0
)

def retrieve_df(cell, resolution, altitude=None):
    """
    Downloads the file with the interpolation parameters for given S2 cell and resolution
    Altitude is ignored for now, as we only query 3D views
    :return: pandas dataframe
    """
    folder = f"{root}/downsampling-factor-{resolution}"
    if altitude is None or True: #Only query 3d chunks for now
        chunk = f"{cell}"
        folder_hash = hashlib.md5(folder.encode()).hexdigest()
        chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
        file_name = f"{folder_hash}/3d/{chunk_hash}.parquet"
    else:
        chunk = f"{altitude}-{cell}"
        file_name = f"{dir}/2d/{chunk}.parquet"
    try:
        df = download_file_bytes(bucket, file_name)
    except Exception as e:
        return None
    df = pd.read_parquet(df)
    return df

def retrieve_pickle(path_in_bucket):
    """
    Retrieve a pickled object from cloud storage
    :param path_in_bucket: path to file inside bucket
    :return: pandas dataframe
    """
    try:
        res = download_file_bytes(bucket, path_in_bucket)
        res = pickle.loads(res.read())
        return res
    except Exception as e:
        return None



def download_file_bytes(bucket, file_name):
    """
    Helper function to downfloat Bytes from a given blob
    """
    blob = bucket.blob(file_name)
    downloaded_bytes = blob.download_as_bytes(retry=custom_retry)
    return io.BytesIO(downloaded_bytes)

def list_dir(path):
    """
    Helper function to list files inside a directory
    """
    blobs = bucket.list_blobs(prefix=path)
    return [blob.name for blob in blobs]


