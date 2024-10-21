import time
from gevent.pool import Pool
from threading import Lock

from locust import FastHttpUser, task, between,tag, events
import random
import fastutm
import geojson
from cachetools import TTLCache



class AtomicInteger:
    """
    Atomic integer helper class needed for aggregating request sizes
    """
    lock = Lock()
    def __init__(self, i):
        self.i = i

    def add(self, j):
        with self.lock:
            self.i = self.i + j

    def get_value(self):
        with self.lock:
            return self.i

class User(FastHttpUser):
    wait_time = between(0.9, 1.1)
    """
        1 : (64, 32),
        2 : (128, 64),
        4 : (256, 128),
        8 : (512, 256),
        16: (1024, 512),
        
        
        1 : (128, 64),
        2 : (256, 128),
        4 : (512, 256),
        8 : (1024, 512),
        16: (2048, 1024),
    """
    resolutions_to_area = { #Zoom level to length x width
        1 : (64, 32),
        2 : (128, 64),
        4 : (256, 128),
        8: (512, 256),
        #16: (1280, 720)
    }
    world_xmax = 387650
    world_xmin = 385350
    world_ymax = 5820450
    world_ymin = 5818050
    altitudes = [30, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]


    def get_random_pos(self):
        alt = random.choice(self.altitudes)
        res = random.choice(list(self.resolutions_to_area.keys()))
        dim = self.resolutions_to_area[res]
        self.orientation = random.choice([True, False])
        if self.orientation:
            x_center = random.uniform(self.world_xmin + (dim[0] // 2), self.world_xmax - (dim[0] // 2))
            y_center = random.uniform(self.world_ymin + (dim[1] // 2), self.world_ymax - (dim[1] // 2))
        else:
            x_center = random.uniform(self.world_xmin + (dim[1] // 2), self.world_xmax - (dim[1] // 2))
            y_center = random.uniform(self.world_ymin + (dim[0] // 2), self.world_ymax - (dim[0] // 2))
        return res, x_center, y_center, alt

    def to_rect(self, res, x_center, y_center):
        dim = self.resolutions_to_area[res]
        v1 = [x_center - dim[0], y_center + dim[1]]
        v2 = [x_center - dim[0], y_center - dim[1]]
        v3 = [x_center + dim[0], y_center - dim[1]]
        v4 = [x_center + dim[0], y_center + dim[1]]
        vertices = [v1, v2, v3, v4, v1]
        return vertices

    def to_latlon_geojson(self, rect):
        vertices = []
        for v in rect:
            lat, lon = (fastutm.to_latlon(v[0], v[1], zone_number=33, northern=True))
            vertices.append([lon, lat])

        geometry = geojson.Polygon([vertices])
        gjson = geojson.Feature(geometry=geometry)
        return gjson

    x_center = 0
    y_center = 0
    res = 1
    alt = 30


    def on_start(self):
        time.sleep(random.random())
        self.res, self.x_center, self.y_center, self.alt = self.get_random_pos()



    cache = TTLCache(maxsize=200, ttl=200)
    cache_lock = Lock()
    def query_cell(self, counter, cell, res, ws, wd, altitude=None):
        cache_key = f"{cell}-{res}-{ws}-{wd}-{altitude}"
        print(cache_key)

        with self.cache_lock:
            if cache_key in self.cache:
                print("cached")
                return
        print("non-cached")
        params = {"ws": ws, "wd": wd, "gcs" : 1}
        if altitude is not None:
            params["altitude"] = altitude
        res = self.client.get(f"/data/{cell}/{res}/3d", params=params, name="/data")
        counter.add(len(res.content))
        with self.cache_lock:
            self.cache[cache_key] = ""
        return ""

    last_sensor = {}
    def query(self, res, x_center, y_center, altitude=None):
        total_size = AtomicInteger(0)
        agg_request_meta = {
            "request_type": "GET_AGGREGATE",
            "name": "/data",
            "context": self.context(),
        }
        start = time.perf_counter()
        rect = self.to_rect(res, x_center, y_center)
        gjson = self.to_latlon_geojson(rect)
        if self.last_sensor:
            gjson["properties"]["sensor_data"] = self.last_sensor
        covering = self.client.post("/covering/", params= {"resolution" : res}, json=gjson).json()
        ws, wd = covering["properties"]["sensor_data"]["ws"], covering["properties"]["sensor_data"]["wd"]
        self.last_sensor = covering["properties"]["sensor_data"]
        cells = list(map(lambda x: x["properties"]["cell"], covering["features"]))


        pool = Pool()
        for cell in cells:
            pool.spawn(self.query_cell, total_size, cell, res, ws, wd, altitude)

        pool.join()

        agg_request_meta["response_time"] = (time.perf_counter() - start) * 1000
        agg_request_meta["response_length"] = total_size.get_value()
        events.request.fire(**agg_request_meta)

        return 0

    RANDOM = 0
    SHIFTING = 1
    STATIC = 2
    TASK = RANDOM
    @task
    def do_task(self):
        if self.TASK == self.RANDOM:
            self.query_random_3d_view()
        elif self.TASK == self.SHIFTING:
            self.query_shifting_3d_view()
        elif self.TASK == self.STATIC:
            self.query(self.res, self.x_center, self.y_center)

    def query_random_3d_view(self):
        self.res, self.x_center, self.y_center, self.alt = self.get_random_pos()
        self.query(self.res, self.x_center, self.y_center)


    def query_shifting_3d_view(self):

        if self.orientation:
            x_len = self.resolutions_to_area[self.res][0]
            y_len = self.resolutions_to_area[self.res][1]
        else:
            x_len = self.resolutions_to_area[self.res][1]
            y_len = self.resolutions_to_area[self.res][0]

        x_shift = random.uniform(max(self.world_xmin-self.x_center, -x_len*0.5),min(self.world_xmax-self.x_center, x_len*0.5))
        y_shift = random.uniform(max(self.world_ymin-self.y_center, -y_len*0.5),min(self.world_ymax-self.y_center, y_len*0.5))
        self.x_center = self.x_center + x_shift
        self.y_center = self.y_center + y_shift

        self.query(self.res, self.x_center, self.y_center)

