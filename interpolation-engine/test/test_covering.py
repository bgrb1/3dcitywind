import dotenv
dotenv.load_dotenv("testenv.env")

import unittest
import copy
from shapely.geometry import Point, Polygon, GeometryCollection
from datetime import datetime
import requests
from config import TARGET_URL

class DefaultTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_invalid_resolution(self): #test the behavior with invalid resolutions
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
        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 0}, json=example_json)
        self.assertEqual(422, response.status_code)

        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : -1}, json=example_json)
        self.assertEqual(422, response.status_code)

        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 3}, json=example_json)
        self.assertEqual(400, response.status_code)

        response = requests.post(f"{TARGET_URL}/covering", json=example_json)
        self.assertEqual(422, response.status_code)



    def test_invalid_input_polygons(self): #test the behavior with invalid polygons
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
        coords_not_ccw = copy.deepcopy(example_json)
        coords_not_ccw["geometry"]["coordinates"][0] = list(reversed(coords_not_ccw["geometry"]["coordinates"][0]))
        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 1}, json=coords_not_ccw)
        self.assertEqual(422, response.status_code)

        loop_not_closed = copy.deepcopy(example_json)
        loop_not_closed["geometry"]["coordinates"][0] = loop_not_closed["geometry"]["coordinates"][0][0:-1]
        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 1}, json=loop_not_closed)
        self.assertEqual(422, response.status_code)

        less_than_3_vertices = copy.deepcopy(example_json)
        less_than_3_vertices["geometry"]["coordinates"][0] = [less_than_3_vertices["geometry"]["coordinates"][0][0], less_than_3_vertices["geometry"]["coordinates"][0][-1]]
        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 1}, json=less_than_3_vertices)
        self.assertEqual(422, response.status_code)


    def test_response_format(self): #validate that the response format is as expected
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
        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 4}, json=example_json)
        self.assertEqual(200, response.status_code)
        response = response.json()
        self.assertEqual("FeatureCollection", response["type"])
        self.assertLessEqual(0, response["properties"]["sensor_data"]["wd"])
        self.assertLessEqual(0, response["properties"]["sensor_data"]["ws"])
        datetime.strptime(response["properties"]["sensor_data"]["time"], "%Y-%m-%dT%H:%M:%S")

        self.assertLess(0, len(response["features"]))
        for feature in response["features"]:
            self.assertEqual("Feature", feature["type"])
            geometry = feature["geometry"]
            self.assertEqual("Polygon", geometry["type"])
            self.assertEqual(1, len(geometry["coordinates"]))
            self.assertEqual(5, len(geometry["coordinates"][0]))
            self.assertEqual(2, len(geometry["coordinates"][0][0]))
            self.assertEqual(geometry["coordinates"][0][0], geometry["coordinates"][0][-1])
            self.assertLessEqual(0, int(feature["properties"]["cell"]))

    def test_response_overlap(self): #check that each output-cell is (partially) contained in the input polygon
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
        polygon = Polygon(example_json["geometry"]["coordinates"][0])
        response = requests.post(f"{TARGET_URL}/covering", params= {"resolution" : 4}, json=example_json).json()

        for feature in response["features"]:
            vertices = feature["geometry"]["coordinates"][0]
            one_contained = False
            for vertex in vertices:
                point = Point(vertex[0], vertex[1])
                if polygon.contains(point):
                    one_contained = True
            self.assertTrue(one_contained)


    def test_response_coverage(self): #check that entire input polygon is covered by the cells
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
        input_polygon = Polygon(example_json["geometry"]["coordinates"][0])
        input_area = input_polygon.area

        response = requests.post(f"{TARGET_URL}/covering", params={"resolution": 4}, json=example_json).json()
        intersection_area = 0
        union = GeometryCollection()
        total_area = 0
        for feature in response["features"]:
            vertices = feature["geometry"]["coordinates"][0]
            feature_polygon = Polygon(vertices)
            intersection_area = intersection_area + input_polygon.intersection(feature_polygon).area
            total_area = total_area + feature_polygon.area
            union = union.union(feature_polygon)

        self.assertGreaterEqual(total_area*0.01, abs(total_area-union.area)) #Validate that cells are more or less disjoint (not exact because of possible floating point inaccuracies)
        self.assertLessEqual(input_area*0.99, intersection_area) #Validate that cells cover more or less entire input polygon


    def test_server_reading_outdated(self):
        #We expect the sensor data of the client to be returned instead of the data from the server
        #Client has data from 2027, so please adjust this if the test is run later than June 3027 :)
        example_json = {
            "type": "Feature",
            "properties" : {
                "sensor_data": {
                    "time": "3027-07-07T14:24:00",
                    "ws": 1.74,
                    "wd": 287.5,
                    "bucket" : 1
                }
            },
            "geometry" : {
                "type": "Polygon",
                "coordinates": [ [
                    [13.316, 52.515],
                    [13.316, 52.512],
                    [13.320, 52.512],
                    [13.320, 52.515],
                    [13.316, 52.515]
                ] ]
            }
        }
        response = requests.post(f"{TARGET_URL}/covering", params={"resolution": 4}, json=example_json)
        response = response.json()
        self.assertEqual("3027-07-07T14:24:00", response["properties"]["sensor_data"]["time"])
        self.assertEqual(1.74, response["properties"]["sensor_data"]["ws"])
        self.assertEqual(287.5, response["properties"]["sensor_data"]["wd"])

