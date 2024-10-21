"""
This file only exists for testing purposes on systems that cant install s2geometry
"""
from models import Covering



def compute_covering(request, resolution, meta):
    response = Covering.parse_raw(mock_response)
    response.properties.sensor_data = meta
    return response



mock_response = '''{
    "type": "FeatureCollection",
    "properties": {
        "sensor_data": {
            "time": "2027-07-07T14:24:00",
            "ws": 1.74,
            "wd": 287.5,
            "bucket" : 1
        }
    },
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.318741, 52.51493],
                        [13.320002, 52.517501],
                        [13.316342, 52.517919],
                        [13.315082, 52.515348],
                        [13.318741, 52.51493]
                    ]
                ]
            },
            "properties": {
                "cell": "5163466141670047744"
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.3224, 52.514512],
                        [13.323661, 52.517083],
                        [13.320002, 52.517501],
                        [13.318741, 52.51493],
                        [13.3224, 52.514512]
                    ]
                ]
            },
            "properties": {
                "cell": "5163466152407465984"
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.32114, 52.511941],
                        [13.3224, 52.514512],
                        [13.318741, 52.51493],
                        [13.317481, 52.512359],
                        [13.32114, 52.511941]
                    ]
                ]
            },
            "properties": {
                "cell": "5163466154554949632"
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.319879, 52.50937],
                        [13.32114, 52.511941],
                        [13.317481, 52.512359],
                        [13.316221, 52.509789],
                        [13.319879, 52.50937]
                    ]
                ]
            },
            "properties": {
                "cell": "5163466160997400576"
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.316221, 52.509789],
                        [13.317481, 52.512359],
                        [13.313822, 52.512778],
                        [13.312563, 52.510207],
                        [13.316221, 52.509789]
                    ]
                ]
            },
            "properties": {
                "cell": "5163466163144884224"
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [13.317481, 52.512359],
                        [13.318741, 52.51493],
                        [13.315082, 52.515348],
                        [13.313822, 52.512778],
                        [13.317481, 52.512359]
                    ]
                ]
            },
            "properties": {
                "cell": "5163466165292367872"
            }
        }
    ]
}'''