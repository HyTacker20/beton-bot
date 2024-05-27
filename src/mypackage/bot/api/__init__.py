import os
from logging import Logger

from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker

from ..api.google_sheet_api import GoogleSheetAPI
from ..api.google_maps_api import GoogleMapsAPI
from ...config.models import GoogleSheetAPIConfig


def setup_google_sheet_api(config: GoogleSheetAPIConfig, db_session_maker: sessionmaker, db_logger):
    _google_sheet_api = GoogleSheetAPI(json_url=config.json_url, sh_url=config.sheet_url,
                                       refresh_time=config.refresh_time, db_session_maker=db_session_maker,
                                       db_logger=db_logger)

    return _google_sheet_api


def setup_google_maps_api(api_key: str):
    _google_maps_api = GoogleMapsAPI(api_key)

    return _google_maps_api
