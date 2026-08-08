import math


EARTH_RADIUS_KM = 6371.0088


def calculate_distance_km(
    departure_latitude,
    departure_longitude,
    arrival_latitude,
    arrival_longitude,
):
    """
    Calculate great-circle distance between two
    geographic coordinates using the Haversine formula.

    Returns:
        Distance in kilometres.
    """

    latitude_1 = math.radians(
        departure_latitude
    )
    latitude_2 = math.radians(
        arrival_latitude
    )

    delta_latitude = math.radians(
        arrival_latitude
        - departure_latitude
    )

    delta_longitude = math.radians(
        arrival_longitude
        - departure_longitude
    )

    a = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(delta_longitude / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return EARTH_RADIUS_KM * c