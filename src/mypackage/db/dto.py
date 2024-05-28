from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from telebot.types import Message


@dataclass
class CoordsDTO:
    address: str
    latitude: float
    longitude: float

    @property
    def coords(self):
        return self.latitude, self.longitude


@dataclass
class DispatchPointDTO(CoordsDTO):
    def __hash__(self):
        return hash((self.address, self.latitude, self.longitude))

    def __eq__(self, other):
        if isinstance(other, DispatchPointDTO):
            return (self.address, self.latitude, self.longitude) == (other.address, other.latitude, other.longitude)
        return False


@dataclass
class NewUserDTO:
    first_name: str
    tg_user_id: int
    tg_chat_id: int

    is_admin: Optional[bool] = False
    concrete_discount: Optional[int] = 0
    delivery_discount: Optional[int] = 0

    last_name: Optional[str] = None
    tg_username: Optional[str] = None

    @classmethod
    def from_tg_message(cls, message: Message):
        new_user = cls(
            first_name=message.from_user.first_name,
            tg_user_id=message.from_user.id,
            tg_chat_id=message.chat.id,
        )
        if message.from_user.last_name:
            new_user.last_name = message.from_user.last_name

        if message.from_user.username:
            new_user.tg_username = message.from_user.username

        return new_user


@dataclass
class UserDTO(NewUserDTO):
    id: Optional[int] = None

    phone: Optional[str] = None

    dispatch_point: Optional[DispatchPointDTO] = None
    dispatch_point_id: Optional[int] = None

    register_time: Optional[datetime] = None


@dataclass
class UserLocationDTO(CoordsDTO):
    pass


@dataclass
class DistanceDTO:
    distance_metres: int
    duration_seconds: int


@dataclass
class ConcreteDTO:
    title: str
    price: float


@dataclass
class ConcreteTypeDTO:
    title: str
    concretes: List[ConcreteDTO]


@dataclass
class ConcreteDataDTO:
    concrete_types: List[ConcreteTypeDTO]

    @property
    def concrete_titles(self):
        return [concrete.title for concrete_type in self.concrete_types for concrete in concrete_type.concretes]

    @property
    def concretes(self):
        return [concrete for concrete_type in self.concrete_types for concrete in concrete_type.concretes]

    @property
    def concrete_type_titles(self):
        return [concrete_type.title for concrete_type in self.concrete_types]

    def get_type(self, concrete_type_title):
        for concrete_type in self.concrete_types:
            if concrete_type.title == concrete_type_title:
                return concrete_type

    def get_concrete(self, concrete_title):
        for concrete in self.concretes:
            if concrete.title == concrete_title:
                return concrete


@dataclass
class OrderDTO:
    user: UserDTO
    dispatch_point: DispatchPointDTO | None = None
    user_location: UserLocationDTO | None = None
    distance: DistanceDTO | None = None
    concrete: ConcreteDTO | None = None
    amount: int | None = None
    delivery_cost: float | None = None
    concrete_cost: float | None = None
    delivery_price: float | None = None

    # def subtract_delivery_discount(self, discount: int):
    #     self.delivery_cost -= self.delivery_cost * discount / 100

    def subtract_concrete_discount(self, discount: int):
        self.concrete_cost -= self.concrete_cost * discount / 100
