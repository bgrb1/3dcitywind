import s2cell


def encode_index(lat, lng, precision):
    cell = s2cell.lat_lon_to_cell_id(lat, lng, precision)
    return cell
