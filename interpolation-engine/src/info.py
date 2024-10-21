from fastapi import APIRouter
import utils.gcs_connector as gcs_connector

app = APIRouter()



@app.get("/resolutions")
def get_resolutions():
    """
    Returns list of available resolutions
    """
    resolutions = sorted(list(set([int(name.split("/")[1].split("_")[0]) for name in gcs_connector.list_dir("metadata")])))
    return resolutions