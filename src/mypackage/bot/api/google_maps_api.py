import datetime
import json
from typing import Tuple, List, Iterable

import googlemaps
from googlemaps.distance_matrix import distance_matrix
from googlemaps.geocoding import geocode, reverse_geocode
from sqlalchemy.orm import sessionmaker

from ...db import DBAdapter
from ...db.dto import UserLocationDTO, DispatchPointDTO, DistanceDTO


class GoogleMapsAPI:
    def __init__(self, api_key):
        self.gmaps = googlemaps.Client(api_key)

    def _get_distance(self, _from: Tuple[float, float], to: Tuple[float, float], debug=False):
        result = distance_matrix(self.gmaps, _from, to)

        if debug:
            with open('distance_result.json', 'w', encoding='utf-8') as json_file:
                json.dump(result, json_file, ensure_ascii=False, indent=4)

        distance = DistanceDTO(result["rows"][0]["elements"][0]["distance"]["value"],
                               result["rows"][0]["elements"][0]["duration"]["value"])

        return distance

    def from_address(self, address: str, debug=False) -> UserLocationDTO | None:
        components = {'locality': 'Kyiv', 'country': 'UA'}
        result = geocode(self.gmaps, address, language="uk-UA", components=components)
        if debug:
            with open('geocode_result.json', 'w', encoding='utf-8') as json_file:
                json.dump(result, json_file, ensure_ascii=False, indent=4)

        user_location = None
        if result:
            address = (", ".join(component["long_name"] for component in result[0]["address_components"]))
            user_location = UserLocationDTO(
                # address=result[0]["formatted_address"],
                address=address,
                latitude=result[0]["geometry"]["location"]["lat"],
                longitude=result[0]["geometry"]["location"]["lng"]
            )

        return user_location

    def from_coords(self, coords: Tuple[float, float], debug=False) -> UserLocationDTO:
        result = reverse_geocode(self.gmaps, coords)

        user_location = UserLocationDTO(
            address=result[0]["formatted_address"],
            latitude=result[0]["geometry"]["location"]["lat"],
            longitude=result[0]["geometry"]["location"]["lng"]
        )

        if debug:
            with open('reverse_geocode_result.json', 'w', encoding='utf-8') as json_file:
                json.dump(result, json_file, ensure_ascii=False, indent=4)

        return user_location

    def get_closest_point(self, dp_list: Iterable[DispatchPointDTO],
                          coords: tuple[float, float]) -> Tuple[DispatchPointDTO, DistanceDTO]:
        distances = {}
        for dp in dp_list:
            result = self._get_distance(coords, dp.coords)
            distances[result.distance_metres] = (dp, result)

        min_distance = min(distances.keys())
        return distances[min_distance]


