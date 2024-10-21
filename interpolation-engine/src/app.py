from fastapi import FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import sensor_daemon
from covering import app as covering_router
from data import app as data_router
from info import app as info_router
from utils import db_connector


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*']
    )
]

app = FastAPI(
    docs_url="/documentation",
    middleware=middleware
)



app.include_router(covering_router, prefix="/covering")
app.include_router(data_router, prefix="/data")
app.include_router(info_router, prefix="/info")


@app.on_event("startup")
async def startup_event():
    #Start background thread for querying sensor data
    sensor_daemon.start_sensor_db_daemon()

@app.on_event("shutdown")
async def shutdown_event():
    db_connector.kill_all()