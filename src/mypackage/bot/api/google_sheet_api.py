import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Set, List

import gspread
from sqlalchemy.orm import sessionmaker

from ...db import DBAdapter
from ...db.dto import DispatchPointDTO, ConcreteDTO, ConcreteTypeDTO, ConcreteDataDTO, ProducerDTO

type dispatch_points_set = Set[DispatchPointDTO]


class GoogleSheetAPI:
    def __init__(self,
                 refresh_time: int,
                 json_url: str,
                 db_session_maker: sessionmaker,
                 db_logger,
                 sh_url="https://docs.google.com/spreadsheets/d/1cRO6Vu3jQ954npXRckbqDdDKAvwiDc12IZkjMFNs8gw/"
                        "edit?usp=sharing"):

        self.db_adapter = DBAdapter(db_session_maker(), db_logger)
        self.gc = gspread.service_account(json_url)
        self.sh = self.gc.open_by_url(sh_url)

        self._producer_titles: Set[str] = self.get_producers_title_set()
        self._producers: List[ProducerDTO] = self.get_producers_with_dispatch_points()

        self._concrete_data: ConcreteDataDTO = self.get_concrete_data()

        self.delivery_mixer_price_data = []
        self.delivery_truck_price_data = []

        self.refresh_time = refresh_time

        self.check_producers()
        self.get_delivery_price_list("P1")
        self.get_delivery_price_list("P3")

        print("google api ready!")

    @property
    def producer_titles(self):
        if not self._producer_titles:
            self._producer_titles = self.get_producers_title_set()
        return self._producer_titles

    @property
    def producers(self):
        if not self._producers:
            self._producers = self.get_producers_with_dispatch_points()
        return self._producers

    @property
    def concrete_data(self):
        if not self._concrete_data:
            self._concrete_data = self.get_concrete_data()

        return self._concrete_data

    def remove_data(self):
        self._producer_titles = []
        self._concrete_data = None

        self.delivery_mixer_price_data = []
        self.delivery_truck_price_data = []

    def check_producers(self):
        actual_producer_titles = self.get_producers_title_set()
        self.db_adapter.sync_producers(actual_producer_titles)

    def get_producers_title_set(self) -> Set[str]:
        """
        Retrieves a list of unique producer titles from the worksheet names in the Google Sheets document.

        Returns:
            list: A list of unique producer titles.
        """
        # Retrieve all worksheet titles from the Google Sheets document
        worksheets_titles = [worksheet.title for worksheet in self.sh.worksheets()]

        # Initialize a set to store unique producer names
        producers_titles = set()

        # Iterate over each worksheet title to extract the producer name
        for worksheets_title in worksheets_titles:
            if not worksheets_title.startswith("producer"):
                continue
            title_parts = worksheets_title.split("_")
            producers_titles.add(title_parts[1])

        return set(producers_titles)

    def get_dispatch_points(self, producer_title: str) -> List[DispatchPointDTO]:
        worksheet = self.sh.worksheet(f"producer_{producer_title}_dispatch-points")
        data = worksheet.get_all_values()  # get list of lists [["title", x, y], ...]

        dispatch_points_list = []
        for coord in data:
            if not len(coord[0]) == 0 | len(coord[1]) == 0 | len(coord[2]) == 0:
                dispatch_points_dto = DispatchPointDTO(coord[0], float(coord[1]), float(coord[2]))
                dispatch_points_list.append(dispatch_points_dto)

        return dispatch_points_list

    def get_concrete_data(self) -> ConcreteDataDTO:
        result = []

        worksheet = self.sh.worksheet("!concrete_types")
        for concrete_type_number in range(1, 6):
            data = worksheet.get(f"A{concrete_type_number * 2 - 1}:G{concrete_type_number * 2}")
            concretes = []

            for el in range(1, 7):
                if el < len(data[0]) - 1:
                    concrete = ConcreteDTO(data[0][el], f"P{concrete_type_number}",
                                           float(data[1][el].replace(",", ".")))
                    concretes.append(concrete)
                else:
                    break

            concrete_type = ConcreteTypeDTO(data[0][0], concretes)
            result.append(concrete_type)

        return ConcreteDataDTO(result)

    def get_delivery_price_list(self, concrete_type: str) -> List[str]:
        if concrete_type in ["P1", "P2"]:
            delivery_type = "Самоскид"
        else:
            delivery_type = "Автобетонозмішувач"

        if delivery_type == "Самоскид":
            if not self.delivery_truck_price_data:
                worksheet = self.sh.worksheet("!delivery_prices")
                data_col_index = worksheet.row_values(1).index(delivery_type) + 1
                self.delivery_truck_price_data = worksheet.col_values(data_col_index)[1:]

            return self.delivery_truck_price_data

        elif delivery_type == "Автобетонозмішувач":
            if not self.delivery_mixer_price_data:
                worksheet = self.sh.worksheet("!delivery_prices")
                data_col_index = worksheet.row_values(1).index(delivery_type) + 1

                self.delivery_mixer_price_data = worksheet.col_values(data_col_index)[1:]
            return self.delivery_mixer_price_data

        return []

    def get_producers_with_dispatch_points(self):
        filtered_titles = [title.title for title in self.sh.worksheets() if
                           title.title.startswith("producer") and title.title.endswith("dispatch-points")]

        producers = []

        def fetch_dispatch_points(title):
            title_parts = title.split("_")
            producer_title = title_parts[1]
            dispatch_points = self.get_dispatch_points(producer_title)
            return ProducerDTO(producer_title, dispatch_points=dispatch_points)

        with ThreadPoolExecutor() as executor:
            producers = list(executor.map(fetch_dispatch_points, filtered_titles))

        return producers
