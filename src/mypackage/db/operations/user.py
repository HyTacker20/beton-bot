from dataclasses import asdict
from typing import Optional, Sequence

from sqlalchemy import select, insert, update, Row, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..dto import NewUserDTO
from ..models import User, UserDiscount, Producer


def add(session: Session, new_user_dto: NewUserDTO) -> bool:
    print(f"{new_user_dto=}")

    session.execute(
        insert(User)
        .values(**asdict(new_user_dto))
    )
    session.commit()

    return True


def get(session: Session, tg_user_id: int) -> Optional[User]:
    print(f"{tg_user_id=}")
    account = session.execute(
        select(User)
        .where(User.tg_user_id == tg_user_id)
    ).first()
    return account if account is None else account[0]


def get_all(session: Session, offset=None, limit=None) -> Sequence[Row[tuple[User]]]:
    query = select(User)
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    users = session.execute(query).all()
    return users


def get_with_discounts(session: Session, tg_user_id: int) -> Optional[User]:
    print(f"{tg_user_id=}")
    account = session.execute(
        select(User)
        .where(User.tg_user_id == tg_user_id)
        .options(joinedload(User.discounts).joinedload(UserDiscount.producer))
    ).first()
    return account if account is None else account[0]


def update_username(session: Session, tg_user_id: int, tg_username: str) -> bool:
    result = session.execute(
        update(User)
        .where(User.tg_user_id == tg_user_id)
        .values(tg_username=tg_username)
    ).rowcount
    return result != 0


def add_discount(session: Session, tg_user_id: int, producer_title: str,
                 concrete_discount: int, delivery_discount: int) -> bool:
    session.execute(
        insert(UserDiscount)
        .values()
    )
    session.commit()

    return True


def update_discount(session: Session, tg_user_id: int, producer_title: str,
                    concrete_discount: int, delivery_discount: int,
                    concrete_discount_vat: int, delivery_discount_vat: int):
    """Updates an existing discount or creates a new one for a user-producer pair.

    Args:
        session: SQLAlchemy session object.
        tg_user_id: Telegram user ID of the user.
        producer_title: Title of the producer.
        concrete_discount: Discount percentage for concrete products.
        delivery_discount: Discount percentage for delivery.

    Returns:
        True if the discount was updated or created, False otherwise.
    """
    user_id = session.query(User).filter_by(tg_user_id=tg_user_id).value(User.id)
    producer_id = session.query(Producer).filter_by(title=producer_title).value(Producer.id)

    print(f"{user_id=}")
    print(f"{producer_title=}")

    stmt = insert(UserDiscount).values(
        user_id=user_id,
        producer_id=producer_id,
        concrete_discount=concrete_discount,
        delivery_discount=delivery_discount,
        concrete_discount_vat=concrete_discount_vat,
        delivery_discount_vat=delivery_discount_vat
    )

    # Execute the insert statement first. If a duplicate key constraint is violated,
    # SQLAlchemy will raise an IntegrityError.
    try:
        session.execute(stmt)
    except IntegrityError as e:
        # If a duplicate key error occurs, update the existing record.
        stmt = update(UserDiscount) \
            .where(UserDiscount.user_id == user_id,
                   UserDiscount.producer_id == producer_id) \
            .values(concrete_discount=concrete_discount,
                    delivery_discount=delivery_discount,
                    concrete_discount_vat=concrete_discount_vat,
                    delivery_discount_vat=delivery_discount_vat)
        session.execute(stmt)

    session.commit()
    return session.query(UserDiscount).filter_by(user_id=user_id, producer_id=producer_id).exists()


def is_admin(session: Session, tg_user_id: int) -> bool | None:
    _is_admin = session.execute(
        select(User.is_admin)
        .where(User.tg_user_id == tg_user_id)
    ).scalar_one_or_none()
    return _is_admin


def get_all_count(session: Session) -> int:
    user_cnt = session.execute(
        select(func.count(User.id))
    ).first()
    return user_cnt[0]


def save_dispatch_point():
    pass
