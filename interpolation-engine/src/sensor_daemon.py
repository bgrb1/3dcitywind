"""
Offers background daemon for querying the database for the current wind sensor readings
+ access to the read sensor data for other components
"""
import asyncio
import random
import datetime
import time

import pandas

import models
from utils.db_connector import get_engine
from threading import Lock
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

engine = get_engine("sensor", pool=False)
mutex = Lock()
sensors = {}
timestamp_format = '%Y-%m-%d %H:%M:%S'
stagger_seconds = 57
bucket_value_range_max = 100000
daemon_wait = 1

def db_daemon():
    while True:
        query_database()
        time.sleep(daemon_wait)

def start_sensor_db_daemon():
    """
    Start the sensor daemon, which will periodically query the database in the background
    """
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()
    loop.run_in_executor(executor, db_daemon)



def get_sensors():
    """
    Get the names of the available sensors
    """
    with mutex:
        return list(sensors.keys())


def get_sensor_info(sensor_id, last_client_data : models.SensorData = None, client = None):
    """
    Get wind speed and direction for given sensor
    Release of new sensor data to users is staggered for <stagger_seconds> seconds
    ==> each client is assigned a timeframe up to <stagger_seconds> seconds where they will be served the old sensor data instead
    ==> Avoids overload when the sensor data is updated and all client requests for the data will lead to cache miss
    ==> The load peak is thus stretched out

    Is thread-safe (for case of concurrent read and write)
    :param sensor_id: name of sensor
    :param last_client_data: last sensor update received by the client (contained in body of following requests)
    :param: client: client address to determine the time bucket for the staggering
    :return: sensor data to be sent back to the client
    """
    if sensor_id not in sensors:
        return None
    bucket = last_client_data.bucket if last_client_data else random.uniform(0, bucket_value_range_max)  # dont reveal exact bucket to client
    with mutex:
        #create sensor data object and assign time bucket to client for next update
        current_sensor_reading = models.SensorData(time=sensors[sensor_id]["time"], wd=sensors[sensor_id]["wd"], ws=sensors[sensor_id]["ws"], bucket=bucket)
        last = sensors[sensor_id]["last"]
        first_read = sensors[sensor_id]["first_read"]
        read = sensors[sensor_id]["read"]

    if last_client_data and client:
        if first_read: #only applies immediately after startup of instance
            #avoid overloading system when instance was just started up
            #without it, the instance would always reply with the the newest sensor reading
            return last_client_data

        if last_client_data.time >= current_sensor_reading.time: #sensor has current sensor data or fresher data than this server instance
            return last_client_data
        elif last_client_data.time >= last: #server has fresher data than client and client data is not too old
            #Calculate time since this server instance has updated its sensor data)
            time_since_last_update_server_side = (datetime.datetime.now() - read).total_seconds()
            delay_for_client = bucket % 57
            if time_since_last_update_server_side < delay_for_client: #If client not yet scheduled for sensor update
                return last_client_data

    return current_sensor_reading



def query_database():
    """
    Helper function to query database for sensor data
    Fills the sensor dict with latest info
    is thread-safe
    """
    with engine.connect() as conn:
        df : pd.DataFrame = pandas.read_sql('''SELECT * FROM "public"."sensors-to-cloud-data" ''', conn)
    sensor_ids = list(map(lambda s : s.split("_")[0], filter(lambda c : c.endswith("_ms"), df.columns.values.tolist())))
    row = df.iloc[0]
    for sensor_id in sensor_ids:
        if sensor_id == "ILR":
            continue

        if sensor_id in sensors and sensors[sensor_id]["time"] == row["TIMESTAMP"]:
            continue
        if sensor_id in sensors:
            sensors[sensor_id]["last"] = sensors[sensor_id]["time"]

        first_read = sensor_id not in sensors

        last = sensors[sensor_id]["last"] if not first_read else datetime.datetime.fromtimestamp(30000000000)
        now = datetime.datetime.now()
        with mutex:
            sensors[sensor_id] = {}
            sensors[sensor_id]["last"] = last
            sensors[sensor_id]["first_read"] = first_read
            sensors[sensor_id]["read"] = now
            sensors[sensor_id]["time"] = row["TIMESTAMP"]
            sensors[sensor_id]["ws"] = float(row[f"{sensor_id}_RAW_CV50_Wind_ms"])
            sensors[sensor_id]["wd"] = float(row[f"{sensor_id}_RAW_CV50_WindDirection_deg"])


#Query once at initialization time
query_database()