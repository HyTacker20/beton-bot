import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, declarative_base

from src.mypackage.db.dto import UserDTO, UserDiscountDTO, ProducerDTO, DispatchPointDTO

Base = declarative_base()


class Producer(Base):
    __tablename__ = "producers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(nullable=False)

    discounts = relationship("UserDiscount", back_populates="producer")
    dispatch_points = relationship("DispatchPoint", back_populates="producer")

    def __repr__(self):
        return f"<Producer(id={self.id}, title='{self.title}')>"

    def to_dto(self):
        return ProducerDTO(
            id=self.id,
            title=self.title
        )


class UserDiscount(Base):
    __tablename__ = "user_discounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    producer_id: Mapped[int] = mapped_column(ForeignKey("producers.id"), nullable=False)

    concrete_discount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_discount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    concrete_discount_vat: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delivery_discount_vat: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user = relationship("User", back_populates="discounts")
    producer = relationship("Producer", back_populates="discounts")

    __table_args__ = (UniqueConstraint('user_id', 'producer_id', name='_user_producer_discount'),)

    def __repr__(self):
        return (f"<UserDiscount({self.concrete_discount}/{self.delivery_discount}, user_id={self.user_id}, "
                f"producer_id={self.producer_id})>")

    def to_dto(self):
        producer_dto = None
        if self.producer:
            producer_dto = self.producer.to_dto()

        return UserDiscountDTO(
            id=self.id,
            user_id=self.user_id,
            producer_id=self.producer_id,
            concrete_discount=self.concrete_discount,
            delivery_discount=self.delivery_discount,
            concrete_discount_vat=self.concrete_discount_vat,
            delivery_discount_vat=self.delivery_discount_vat,
            producer=producer_dto
        )


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('categories.id'), nullable=True)

    subcategories = relationship('Category', backref='parent', remote_side=[id])
    items = relationship('Item', backref='category')

    def __repr__(self):
        return f"<Category(id={self.id}, title='{self.title}')>"


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey('categories.id'), nullable=False)

    def __repr__(self):
        return f"<Item(id={self.id}, title='{self.title}', category_id={self.category_id})>"


class DispatchPoint(Base):
    __tablename__ = "dispatch_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)

    producer_id: Mapped[int] = mapped_column(ForeignKey("producers.id"), nullable=False)
    producer = relationship("Producer", back_populates="dispatch_points")

    def __repr__(self):
        return f"<DispatchPoint(id={self.id}, address='{self.address}')>"

    def to_dto(self):
        return DispatchPointDTO(
            address=self.address,
            latitude=self.latitude,
            longitude=self.longitude
        )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tg_user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    tg_chat_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tg_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_admin: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    dispatch_point_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("dispatch_points.id"), nullable=True)
    dispatch_point = relationship("DispatchPoint", backref="user")

    discounts = relationship("UserDiscount", back_populates="user")
    register_time: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'User(id={self.id}, first_name={self.first_name}, tg_username={self.tg_username if self.tg_username else ""})'

    def to_dict(self):
        return {c.name: getattr(self, c.name) if c.name not in ("dispatch_point_id", "dispatch_point") else None
                for c in self.__table__.columns}

    def to_dto(self):
        dispatch_point_dto = None
        if self.dispatch_point:
            dispatch_point_dto = self.dispatch_point.to_dto()

        discount_dtos = []
        for discount in self.discounts:
            discount_dtos.append(discount.to_dto())

        return UserDTO(
            id=self.id,
            first_name=self.first_name,
            last_name=self.last_name,
            tg_user_id=self.tg_user_id,
            tg_chat_id=self.tg_chat_id,
            tg_username=self.tg_username,
            phone=self.phone,
            is_admin=self.is_admin,
            discounts=discount_dtos,
            dispatch_point=dispatch_point_dto,
            dispatch_point_id=self.dispatch_point_id,
            register_time=self.register_time
        )

# Uncomment and define the Order model if necessary
# class Order(Base):
#     __tablename__ = "orders"
#
#     id: Mapped[int] = mapped_column(primary_key=True)
#     user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
#     user = relationship("User", back_populates="orders")
#     articles: Mapped[List[Article]] = relationship("Article", secondary=order_article_table, back_populates="orders")
#
#     def __repr__(self):
#         return f"<Order(id={self.id}, user_id={self.user_id})>"
