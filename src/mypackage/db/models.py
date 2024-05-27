import enum
from datetime import datetime, timezone
from typing import List

from sqlalchemy import text, ForeignKey, Table, Column, Integer, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Article(enum.Enum):
    concrete = "бетон"
    floor_slabs = "плити перекриття"
    brick = "цегла"
    gas_block = "газоблок"
    ceramic_block = "керамоблок"
    paving_slabs = "тротуарна плитка"


class DispatchPoint(Base):
    __tablename__ = "dispatch_points"

    id: Mapped[int] = mapped_column(primary_key=True)

    address: Mapped[str]
    latitude: Mapped[float]
    longitude: Mapped[float]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str]
    last_name: Mapped[str | None]
    tg_user_id: Mapped[int]
    tg_chat_id: Mapped[int]
    tg_username: Mapped[str | None]
    phone: Mapped[str | None]

    dispatch_point_id = mapped_column(ForeignKey("dispatch_points.id"), nullable=True)
    dispatch_point = relationship("DispatchPoint", backref="user")

    concrete_discount: Mapped[int | None]
    delivery_discount: Mapped[int | None]

    is_admin: Mapped[bool | None]

    register_time: Mapped[datetime | None] = mapped_column(default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'User: {self.id} | {self.first_name} | @{self.tg_username if self.tg_username else ""}'

    def to_dict(self):
        return {c.name: getattr(self, c.name) if c.name not in ("dispatch_point_id", "dispatch_point") else None
                for c in self.__table__.columns}


# class Producer(Base):
#     __tablename__ = "producers"
#
#     id: Mapped[int] = mapped_column(primary_key=True)
#     title: Mapped[str]
#     articles: Mapped[List[Article]]
#
#
# order_article_table = Table('order_article', Base.metadata,
#                             Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
#                             Column('article', Enum(Article), primary_key=True)
#                             )


# class Order(Base):
#     __tablename__ = "orders"
#
#     id: Mapped[int] = mapped_column(primary_key=True)
#     user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
#     user: Mapped[User] = relationship("User", back_populates="orders")
#     articles: Mapped[Article] = relationship("Article", secondary=order_article_table, back_populates="orders")
