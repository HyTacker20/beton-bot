from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from sqlalchemy import UniqueConstraint
from telebot.types import Message

from src.mypackage.bot import texts


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
class ProducerDTO:
    title: str
    id: int | None = None

    dispatch_points: List[DispatchPointDTO] | None = None


@dataclass
class UserDiscountDTO:
    id: int | None = None
    user_id: int | None = None
    producer_id: int | None = None

    concrete_discount: Optional[int] = 0
    delivery_discount: Optional[int] = 0

    concrete_discount_vat: Optional[int] = 0
    delivery_discount_vat: Optional[int] = 0

    producer: Optional[ProducerDTO] = None

    def get_concrete_discount(self, payment_type: str):
        if payment_type == texts.cash_payment:
            return self.concrete_discount
        elif payment_type == texts.cashless_payment:
            return self.concrete_discount_vat
        return 0

    def get_delivery_discount(self, payment_type: str):
        if payment_type == texts.cashless_payment:
            return self.delivery_discount
        elif payment_type == texts.cashless_payment:
            return self.delivery_discount_vat
        return 0


@dataclass
class ItemDTO:
    id: int
    title: str
    category_id: int


@dataclass
class CategoryDTO:
    id: int
    title: str
    parent_id: Optional[int] = None
    subcategories: List['CategoryDTO'] = field(default_factory=list)
    items: List[ItemDTO] = field(default_factory=list)


@dataclass
class NewUserDTO:
    first_name: str
    tg_user_id: int
    tg_chat_id: int

    is_admin: Optional[bool] = False

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

    discounts: List[UserDiscountDTO] = None
    dispatch_point: Optional[DispatchPointDTO] = None
    dispatch_point_id: Optional[int] = None

    register_time: Optional[datetime] = None

    def get_producer_discounts(self, producer_title: str):
        for discount in self.discounts:
            if discount.producer.title == producer_title:
                return discount

        return UserDiscountDTO(
            concrete_discount=0,
            delivery_discount=0,
            concrete_discount_vat=0,
            delivery_discount_vat=0
        )


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
    type_: str
    price: float
    producer: str | None = None


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
    payment_type: str = texts.cash_payment
    producer: str | None = None
    dispatch_point: DispatchPointDTO | None = None
    user_location: UserLocationDTO | None = None
    distance: DistanceDTO | None = None
    concrete: ConcreteDTO | None = None
    amount: int | None = None
    delivery_cost: float | None = None
    concrete_cost: float | None = None
    delivery_price: float | None = None

    @property
    def delivery_cost_with_discount(self):
        return self.delivery_cost - self.get_delivery_discount()

    @property
    def concrete_cost_with_discount(self):
        return self.concrete_cost - self.get_concrete_discount()

    def get_concrete_discount(self):
        for discount in self.user.discounts:
            if discount.producer.title == self.producer:
                return self.concrete_cost * discount.concrete_discount / 100
        return 0

    def get_delivery_discount(self):
        for discount in self.user.discounts:
            if discount.producer.title == self.producer:
                return self.delivery_cost * discount.delivery_discount / 100
        return 0
