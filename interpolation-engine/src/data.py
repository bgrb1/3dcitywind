from typing import Optional

import pandas
from utils import interpolation
from fastapi import APIRouter, Response, Path, Query, HTTPException
from starlette import status
from utils.serializers import df_to_parquet
from utils.db_connector import query_df_from_sql
from utils.gcs_connector import retrieve_df, retrieve_pickle
from async_lru import alru_cache
pandas.options.mode.chained_assignment = None


app = APIRouter()

@app.get("/{cell}/{resolution}/3d")
async def data(cell : int = Path(..., description="S2 cell id received from /covering", ge=0),
               resolution : int = Path(..., description="Resolution factor for which to load the data. You NEED to use the same as for the /covering endpoint. The cell id depends on it", gt=0),
               ws : float = Query(..., description="wind speed in m/s, as received from /covering", ge=0),
               wd : float = Query(..., description="Wind direction in degrees as received from /covering", ge=0, lt=360),
               gcs: Optional[int] = Query(0, description="Ignore this. Only exists for legacy support")):
    """
    Generates and returns the wind data for a given cell at a given resolution, for given wind speed and direction through on POD interpolation


    Response is a binary parquet file, which encodes a dataframe with the schema [lat, lon, z, u, v, w]

    Lat and lon are latitude and longitude

    z is the elevation in meters above sea level

    u,v and w encode the wind vector with respect to the UTM coordinate system
    """
    add_data_future = query_additional_data(resolution)
    df = retrieve_df(cell, resolution, -1)
    if df is not None:
        A, WDref = await add_data_future
        interpolation.interpolate(df, A, WDref, wd, ws)
    else:
        A, WDref = await add_data_future
        if A is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid resolution")
        else:
            # if non-existend chunk was queried, we return an empty frame instead of a 404 error
            df = pandas.DataFrame(columns=['lat','lon','z','u','v','w'])

    #correct the response schema
    #TODO May change u,v,w to float16 if ever supported by frontend
    df = df[["lat", "lon", "z", "u", "v", "w"]]
    df["lat"] = df["lat"].astype("float32")
    df["lon"] = df["lon"].astype("float32")
    df["z"] = df["z"].astype("int32")
    df["u"] = df["u"].astype("float32")
    df["v"] = df["v"].astype("float32")
    df["w"] = df["w"].astype("float32")
    result = df_to_parquet(df)

    headers = {
        "Content-Disposition": "inline",
        'Cache-Control': 'public, max-age=300'
    }
    return Response(content=result, headers=headers)



@alru_cache(maxsize=2*10) #Includes some buffer just because
async def query_additional_data(resolution):
    """
    Helper function to query the additional data necessary for applying POD interpolation
    Applies caching to avoid reloading the data. We do not expect it to change during normal usage
    :param resolution: the resolution for which to load it
    :return: A and WDref matrix (as a tuple in that order)
    """
    A = retrieve_pickle(f"metadata/{resolution}_A.pickle")
    WDref = retrieve_pickle(f"metadata/{resolution}_WDref.pickle")
    return A, WDref



