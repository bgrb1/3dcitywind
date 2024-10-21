import os
s2mock = False if os.getenv('CLOUD') is None else not os.getenv('CLOUD') == "True"
if s2mock:
    from utils import s2mock as s2 #s2mock exists for testing on systems where s2geometry doesnt compile
else:
    from utils import s2 as s2
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from starlette import status
from sensor_daemon import get_sensor_info
from models import InputPolygonFeature, Covering

app = APIRouter()


@app.post("/", response_model=Covering, responses={400: {"detail": "Invalid args or body"}})
async def covering(request : Request,
                    poly : InputPolygonFeature,
                   response : Response,
                   resolution : int = Query(..., description="Resolution for which to compute the covering", gt=0)):
    """
    Computes the S2 covering of a given input polygon
    The S2 cell level is fixed and depends on the given resolution
    ==> Data size of chunks should remain somewhat constant across resolutions

    Also returns the current sensor data for the client in properties.sensor_data in the response body


    The request body MUST be an input polygon as GeoJSON Feature.

    The vertices MUST be ordered counter-clockwise.

    The loop MUST be closed so that the last vertex is the same as the first vertex.

    The coordinate order MUST be [longitude, latitude].

    The feature MAY include the properties.sensor_data block from the last received response to ensure monotonic reads consistency


    The response will be a GeoJSON feature collection, describing all S2 cells in the covering with their cell id's as well as their
    respective boundaries

    The cell id's can then be used to query their data points using the /data endpoint

    """
    response.headers["Cache-Control"] = "no-store"
    try:
        sensor = "EN"
        if poly.properties is not None and poly.properties.sensor_data is not None:
            sensor_data = get_sensor_info(sensor, poly.properties.sensor_data, request.client)
        else:
            sensor_data = get_sensor_info(sensor)

        covering = s2.compute_covering(poly, resolution, sensor_data)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid args or body")

    return covering
