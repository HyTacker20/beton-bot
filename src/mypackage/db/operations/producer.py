from typing import Optional, Sequence, List, Tuple, Any, Iterable

from sqlalchemy import select, insert, Row, RowMapping, delete
from sqlalchemy.orm import Session

from ..models import Producer


def add(session: Session, title: str) -> bool:
    print(f"{title=}")

    session.execute(
        insert(Producer)
        .values(title=title)
    )
    session.commit()

    return True


def sync_producers(session: Session, producer_titles: Iterable[str]) -> bool:
    existing_producers = session.query(Producer.title).all()
    existing_titles = {producer.title for producer in existing_producers}

    new_titles = set(producer_titles) - existing_titles
    old_titles = existing_titles - set(producer_titles)

    if new_titles:
        values = [{"title": title} for title in new_titles]
        session.execute(insert(Producer), values)

    if old_titles:
        session.execute(delete(Producer).where(Producer.title.in_(old_titles)))

    session.commit()
    return True


def get_or_create(session: Session, title: str) -> Row[tuple[Producer]] | None:
    # Check if the producer already exists
    stmt = select(Producer).where(Producer.title == title)
    result = session.execute(stmt).scalars().first()

    if result:
        return result  # Indicate that the producer was not added because it already exists

    # If the producer does not exist, add it
    session.execute(
        insert(Producer)
        .values(title=title)
    )
    session.commit()
    return None


def get_by_id(session: Session, _id: int) -> Optional[Producer]:
    producer = session.execute(
        select(Producer)
        .where(Producer.id == _id)
    ).first()
    return producer if producer is None else producer[0]


def get_by_title(session: Session, title: str) -> Optional[Producer]:
    producer = session.execute(
        select(Producer)
        .where(Producer.title == title)
    ).first()
    return producer if producer is None else producer[0]


def get_all(session: Session) -> Sequence[Row[tuple[Producer]]]:
    producers = session.execute(
        select(Producer)
    ).all()
    return producers


def get_all_titles(session: Session) -> Sequence[Row[Any] | RowMapping | Any]:
    # Query to get all producer titles that match the given list
    stmt = select(Producer.title)
    result = session.execute(stmt).scalars().all()

    # Check if the length of the result matches the length of the input list
    return result


def delete_all_by_title(session: Session, producers_titles: Iterable[str]) -> bool:
    dispatch_point = session.execute(
        delete(Producer)
        .filter(Producer.title.in_(producers_titles))
    )
    return True
