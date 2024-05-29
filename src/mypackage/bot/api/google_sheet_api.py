import datetime

import gspread
from sqlalchemy.orm import sessionmaker

from ...db import DBAdapter
from ...db.dto import DispatchPointDTO, ConcreteDTO, ConcreteTypeDTO, ConcreteDataDTO


class GoogleSheetAPI:
    def __init__(self,
                 refresh_time: int,
                 json_url: str,
                 db_session_maker: sessionmaker,
                 db_logger,
                 sh_url="https://docs.google.com/spreadsheets/d/1cRO6Vu3jQ954npXRckbqDdDKAvwiDc12IZkjMFNs8gw/"
                        "edit?usp=sharing"):
        # beton-bot-test-2af7167272a4.json
        self.dispatch_points_set: set | None = None
        self.concrete_data: ConcreteDataDTO | None = None
        self.last_update: datetime.datetime | None = None
        self.delivery_price_data = []

        self.gc = gspread.service_account(json_url)
        self.sh = self.gc.open_by_url(sh_url)

        self.refresh_time = refresh_time
        self.db_adapter = DBAdapter(db_session_maker(), db_logger)

        self.initial_check()

    def initial_check(self):
        self.db_adapter.delete_all_dispatch_points()
        self.dispatch_points_set = self.get_dispatch_points()
        if len(self.db_adapter.get_all_dispatch_point()) == 0:
            self.db_adapter.add_all_dispatch_point(self.dispatch_points_set)
        self.get_concrete_data()
        print("google api ready!")

    def remove_data(self):
        self.concrete_data = None
        self.delivery_price_data = None

    def get_dispatch_points(self) -> set[DispatchPointDTO]:
        worksheet = self.sh.worksheet("dispatch_points")
        data = worksheet.get_all_values()  # get list of lists [["title", x, y], ...]

        dispatch_points_list = []
        for coord in data:
            if not len(coord[0]) == 0 | len(coord[1]) == 0 | len(coord[2]) == 0:
                dispatch_points_dto = DispatchPointDTO(coord[0], float(coord[1]), float(coord[2]))
                dispatch_points_list.append(dispatch_points_dto)

        return set(dispatch_points_list)

    def update_dispatch_points(self):
        new_dispatch_points_set = self.get_dispatch_points()
        # print(new_dispatch_points_set)

        old_dispatch_points = self.dispatch_points_set - new_dispatch_points_set
        print(f"{old_dispatch_points=}")
        if old_dispatch_points:
            self.db_adapter.delete_all_dispatch_points_by_title(old_dispatch_points)
            self.dispatch_points_set.discard(old_dispatch_points)

        new_dispatch_points = new_dispatch_points_set - self.dispatch_points_set
        print(f"{new_dispatch_points=}")
        if new_dispatch_points:
            self.db_adapter.add_all_dispatch_point(new_dispatch_points)
            self.dispatch_points_set.update(new_dispatch_points)

        self.last_update = datetime.datetime.now()

    def get_concrete_data(self):
        if not self.concrete_data:
            result = []

            worksheet = self.sh.worksheet("concrete_types")
            for concrete_type_number in range(1, 6):
                data = worksheet.get(f"A{concrete_type_number*2-1}:G{concrete_type_number*2}")
                concretes = []
                for el in range(1, 7):
                    if el < len(data[0])-1:
                        concrete = ConcreteDTO(data[0][el], float(data[1][el].replace(",", ".")))
                        concretes.append(concrete)
                    else:
                        break

                concrete_type = ConcreteTypeDTO(data[0][0], concretes)
                result.append(concrete_type)

            self.concrete_data = ConcreteDataDTO(result)

        return self.concrete_data

    def get_delivery_price_list(self):
        if not self.delivery_price_data:
            worksheet = self.sh.worksheet("delivery_prices")
            self.delivery_price_data = worksheet.col_values(1)
        return self.delivery_price_data



