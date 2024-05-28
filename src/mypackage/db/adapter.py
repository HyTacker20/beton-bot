import logging
from typing import Optional, Callable, Iterable

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .dto import NewUserDTO, DispatchPointDTO
from .exceptions import DBError
from .models import User
from .operations import user, dispatch_points, database


class DBAdapter:
    def __init__(self, session: Session, logger: logging.Logger):
        self.logger = logger
        self.session = session

    def _session_wrapper(self, method: Callable, *args, **kwargs):
        try:
            return method(self.session, *args, **kwargs)
        except IntegrityError as e:
            self.logger.debug(e)
            return False
        except SQLAlchemyError as e:
            self.logger.exception(e)
            raise DBError(f"Error occurred while {method.__name__}: {e}")

    def get_user(self, tg_user_id: int) -> Optional[User]:
        return self._session_wrapper(user.get, tg_user_id)

    def get_all_users(self, offset: int, limit: int) -> Iterable[User]:
        return self._session_wrapper(user.get_all, offset, limit)

    def get_all_users_count(self) -> int:
        return self._session_wrapper(user.get_all_count)

    def add_user(self, new_user_dto: NewUserDTO):
        return self._session_wrapper(user.add, new_user_dto)

    def update_user_discount(self, tg_user_id: int, concrete_discount: int, delivery_discount: int) -> bool:
        return self._session_wrapper(user.update_discount, tg_user_id, concrete_discount, delivery_discount)

    def check_if_user_is_admin(self, tg_user_id: int) -> bool | None:
        return self._session_wrapper(user.is_admin, tg_user_id)

    def add_dispatch_point(self, dp_dto: DispatchPointDTO):
        return self._session_wrapper(dispatch_points.add, dp_dto)

    def add_all_dispatch_point(self, dp_dto_list: Iterable[DispatchPointDTO]):
        return self._session_wrapper(dispatch_points.add_all, dp_dto_list)

    def get_all_dispatch_point(self):
        return self._session_wrapper(dispatch_points.get_all)

    def get_dispatch_point_by_id(self, dp_id: int):
        return self._session_wrapper(dispatch_points.get_by_id, dp_id)

    def get_dispatch_point_by_address(self, dp_address: str) -> DispatchPointDTO:
        return self._session_wrapper(dispatch_points.get_by_address, dp_address)

    def delete_all_dispatch_points_by_title(self, dp_list: Iterable):
        return self._session_wrapper(dispatch_points.delete_all_by_title, dp_list)

    def delete_all_dispatch_points(self):
        return self._session_wrapper(dispatch_points.delete_all)

    def check_and_create_tables(self):
        return self._session_wrapper(database.check_and_create_tables)
