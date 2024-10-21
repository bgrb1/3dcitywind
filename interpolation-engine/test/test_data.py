import dotenv
dotenv.load_dotenv("testenv.env")
from fastapi.testclient import TestClient
import unittest
import pandas as pd
from io import BytesIO
import requests
from config import TARGET_URL

class DefaultTestCase(unittest.TestCase):

    def setUp(self):
        pass


    def test_invalid_resolutions(self):
        response = requests.get(f"{TARGET_URL}/data/5163466156970868736/-1/3d",params={"ws" : 1.1, "wd" : 110.1})
        self.assertEqual(422, response.status_code)

        response = requests.get(f"{TARGET_URL}/data/5163466156970868736/0/3d",params={"ws" : 1.1, "wd" : 110.1})
        self.assertEqual(422, response.status_code)

        response = requests.get(f"{TARGET_URL}/data/5163466156970868736/3/3d",params={"ws" : 1.1, "wd" : 110.1})
        self.assertEqual(422, response.status_code)


    def test_nonexistent_chunk(self):
        response = requests.get(f"{TARGET_URL}/data/1/4/3d",params={"ws" : 1.1, "wd" : 110.1})
        self.assertEqual(200, response.status_code)
        body = BytesIO(response.content)
        df = pd.read_parquet(body)
        self.assertEqual(0, len(df))


    def test_3d(self): #Check the response format for a 3d cell query
        response = requests.get(f"{TARGET_URL}/data/5163466156970868736/2/3d",params={"ws" : 1.1, "wd" : 110.1})
        self.assertEqual(200, response.status_code)
        body = BytesIO(response.content)
        df = pd.read_parquet(body)
        self.assertEqual(6, len({"lat", "lon", "z", "u", "v", "w"}.intersection(set(df.columns))))
        self.assertEqual("float32", str(df["lat"].dtype))
        self.assertEqual("float32", str(df["lon"].dtype))
        self.assertEqual("int32", str(df["z"].dtype))

        self.assertEqual("float32", str(df["u"].dtype))
        self.assertEqual("float32", str(df["v"].dtype))
        self.assertEqual("float32", str(df["w"].dtype))

        for index, row in df.iterrows():
            self.assertLess(52, row["lat"])
            self.assertGreater(53, row["lat"])
            self.assertLess(13, row["lon"])
            self.assertGreater(14, row["lon"])

    @unittest.skip
    def test_2d(self): #CURRENTLY IGNORED AS WE DONT SUPPORT 2D VIEWS YET
        response = self.client.get("data", params= {"resolution" : 8, "cell" : "5163466156970868736", "ws" : 1.1, "wd" : 110.1, "altitude" : 35})
        self.assertEqual(200, response.status_code)
        body = BytesIO(response.content)
        df = pd.read_parquet(body)
        for index, row in df.iterrows():
            self.assertEqual(35, row["z"])



