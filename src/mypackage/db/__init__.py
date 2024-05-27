import os
from logging import Logger

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker

from ..config.models import DBConfig

from .adapter import DBAdapter
from .exceptions import DBError


load_dotenv()


def setup_session_maker():
    sqlite_filepath = os.environ.get('DB_URL')
    db_url = f"sqlite:///{sqlite_filepath}"
    db_engine = create_engine(db_url, echo=True)
    db_session_maker = sessionmaker(bind=db_engine)

    return db_session_maker
