import dotenv
dotenv.load_dotenv("testenv.env")

import unittest
from io import BytesIO
import pandas as pd
from shapely.geometry import Point, Polygon
import requests
from config import TARGET_URL


class DefaultTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_integration(self): #test the integration of both /covering and /data by using both to get the data for a view
        example_json = {
            "type": "Feature",
            "geometry" : {
                "type": "Polygon",
                "coordinates": [ [
                    [13.316, 52.515],
                    [13.316, 52.512],
                    [13.320, 52.512],
                    [13.320, 52.515],
                    [13.316, 52.515]
                ] ]
            },
            "properties": {}
        }
        resolution = 8
        covering = requests.post(f"{TARGET_URL}/covering", params={"resolution": resolution}, json=example_json).json()

        for feature in covering["features"][0:max(5, len(covering["features"]))]:
            vertices = feature["geometry"]["coordinates"][0]
            feature_polygon = Polygon(vertices)
            cell = feature["properties"]["cell"]
            data = requests.get(f"{TARGET_URL}/data/{cell}/{resolution}/3d", params={"wd": covering["properties"]["sensor_data"]["wd"], "ws": covering["properties"]["sensor_data"]["ws"]})
            self.assertEqual(200, data.status_code)
            body = BytesIO(data.content)
            df = pd.read_parquet(body)
            self.assertLess(10, len(df)) #10 was arbitrarily chosen
            for index, row in df.iterrows():
                point = Point((row["lon"], row["lat"]))
                self.assertTrue(feature_polygon.contains(point))

