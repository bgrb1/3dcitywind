import s2geometry as s2g
from models import InputPolygonFeature, OutputPolygonFeature, Covering, PolygonGeometry, CellProperties, SensorDataProperties

max_precision = 22
bit_overhead = 64-4 - (max_precision*2)
resolution_to_cell_level = {1 : 17, 2 : 16, 4 : 15, 8 : 14, 16 : 13, 32 : 12}


def encode_index(lat, lng, precision=max_precision):
    """
    Covert latitude and longitude to an S2 cell for given S2 precision
    :param lat: latitude in degrees
    :param lng: longitude in degrees
    :param precision: S2 precision (cell level)
    :return: cell id
    """
    latlng = s2g.S2LatLng.FromDegrees(lat, lng)
    cell_id = s2g.S2CellId(latlng).parent(precision)
    cell_id = cell_id.id()
    return cell_id

def index_to_query_range(cell_id):
    """
    Deprecated function
    Can be used when querying a database to generate and integer range that covers everything in a given cell
    :return: from (inclusive), to (exclusive)
    """
    lsb = cell_id & -cell_id
    return cell_id-lsb, cell_id+lsb

def compute_covering(input_polygon, resolution, sensor_data):
    """
    Computes the S2 covering for a given input polygon and resolution
    :param sensor_data: sensor_data to be included in the properties
    :return: S2 covering
    """
    polygon = parse_polygon(input_polygon)
    coverer = get_region_coverer(resolution)
    covering = coverer.GetCovering(polygon)
    features = []
    for cell_id in covering:
        features.append(cell_to_feature(cell_id))
    properties = SensorDataProperties(sensor_data=sensor_data)
    result = Covering(properties=properties, features=features)
    return result


def parse_polygon(gjson : InputPolygonFeature):
    """
    Parse the input geojson polygon to an S2 Polygon
    """
    coordinates = gjson.geometry.coordinates[0][:-1]
    s2_points = [s2g.S2LatLng.FromDegrees(lat, lng).ToPoint() for lng, lat in coordinates]
    loop = s2g.S2Loop(s2_points)
    if not loop.IsValid():
        raise ValueError()
    polygon = s2g.S2Polygon(loop)

    return polygon

def cell_to_feature(cell_id):
    """
    Create geojson feature for a given cell id
    """
    cell = s2g.S2Cell(cell_id)
    def vertex_to_lat_lng(i):
        latlng = s2g.S2LatLng(cell.GetVertex(i))
        return latlng.lng().degrees(), latlng.lat().degrees()

    cell_vertices = list(([[vertex_to_lat_lng(i) for i in range(4)]]))
    cell_vertices[0].append(cell_vertices[0][0])
    properties = CellProperties(cell=str(cell_id.id()))
    geometry = PolygonGeometry(coordinates=cell_vertices)
    return OutputPolygonFeature(geometry=geometry, properties=properties)

def get_region_coverer(resolution):
    """
    Helper function to create a region coverer for the given resolution
    The resolution determines the cell level
    """
    coverer = s2g.S2RegionCoverer()
    #coverer.set_max_cells(50)
    coverer.set_min_level(resolution_to_cell_level[resolution])
    coverer.set_max_level(resolution_to_cell_level[resolution]) #TODO perhaps +1 to reduce data overhead, if ingested at multiple levels
    return coverer



