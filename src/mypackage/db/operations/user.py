from dataclasses import asdict
from typing import Optional, Sequence

from sqlalchemy import select, insert, update, Row, func
from sqlalchemy.orm import Session

from ..dto import NewUserDTO
from ..models import User


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


def update_username(session: Session, tg_user_id: int, tg_username: str) -> bool:
    result = session.execute(
        update(User)
        .where(User.tg_user_id == tg_user_id)
        .values(tg_username=tg_username)
    ).rowcount
    return result != 0


def update_discount(session: Session, tg_user_id: int, concrete_discount: int, delivery_discount: int) -> bool:
    result = session.execute(
        update(User)
        .where(User.tg_user_id == tg_user_id)
        .values(concrete_discount=concrete_discount,
                delivery_discount=delivery_discount)
    ).rowcount
    session.commit()
    return result != 0


def is_admin(session: Session, tg_user_id: int) -> bool | None:
    _is_admin = session.execute(
        select(User.is_admin)
        .where(User.tg_user_id == tg_user_id)
    ).scalar_one_or_none()
    return _is_admin


def get_all(session: Session, offset=None, limit=None) -> Sequence[Row[tuple[User]]]:
    query = select(User)
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    users = session.execute(query).all()
    return users


def get_all_count(session: Session) -> int:
    user_cnt = session.execute(
        select(func.count(User.id))
    ).first()
    return user_cnt[0]


def save_dispatch_point():
    pass
