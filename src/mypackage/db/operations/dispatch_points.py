from typing import Optional, List, Tuple, Iterable, Sequence
from dataclasses import asdict

from sqlalchemy import select, insert, update, Row, delete
from sqlalchemy.orm import Session

from ..dto import UserDTO, NewUserDTO, DispatchPointDTO
from ..models import User, DispatchPoint


def add(session: Session, dp_dto: DispatchPointDTO) -> bool:
    session.execute(
        insert(DispatchPoint)
        .values(**asdict(dp_dto))
    )
    session.commit()
    return True


def add_all(session: Session, dp_dto_list: List[DispatchPointDTO]) -> bool:
    values_list = [asdict(dp_dto) for dp_dto in dp_dto_list]

    session.execute(
        insert(DispatchPoint),
        values_list
    )
    session.commit()
    return True


def get_all(session: Session) -> Sequence[Row[tuple[DispatchPoint]]]:
    dispatch_point = session.execute(
        select(DispatchPoint)
    ).all()
    print(dispatch_point)
    return dispatch_point


def get_by_id(session: Session, dp_id: int) -> Optional[DispatchPoint]:
    dispatch_point = session.execute(
        select(DispatchPoint)
        .where(DispatchPoint.id == dp_id)
    ).first()
    print(dispatch_point)
    return dispatch_point if dispatch_point is None else dispatch_point[0]


def get_by_address(session: Session, dp_address: str) -> Optional[DispatchPointDTO]:
    try:
        dispatch_point = session.execute(
            select(DispatchPoint)
            .where(DispatchPoint.address == dp_address)
        ).first()

        dispatch_point = dispatch_point if dispatch_point is None else dispatch_point[0]

        dispatch_point_dto = DispatchPointDTO(
            address=dispatch_point.address,
            latitude=dispatch_point.latitude,
            longitude=dispatch_point.longitude
        ) if dispatch_point else None

        return dispatch_point_dto

    except Exception as e:
        print(e)


def delete_all_by_title(session: Session, dp_list: Iterable[DispatchPointDTO]) -> bool:
    dispatch_point = session.execute(
        delete(DispatchPoint)
        .filter(DispatchPoint.title.in_([dp.address for dp in dp_list]))
    )
    return True


def delete_all(session: Session) -> bool:
    dispatch_point = session.execute(
        delete(DispatchPoint)
    )
    return True
