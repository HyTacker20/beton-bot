from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def create_tables(session: Session):
    from ..models import Base
    Base.metadata.create_all(session.bind)


def check_and_create_tables(session: Session):
    try:
        create_tables(session)
        print("Tables checked/created successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
