import logging

from sqlalchemy.orm import sessionmaker
from telebot.handler_backends import BaseMiddleware

from .. import GoogleSheetAPI, GoogleMapsAPI
from ...config.models import MessagesConfig, ButtonsConfig
from ...db import DBAdapter


class ExtraArgumentsMiddleware(BaseMiddleware):
    def __init__(
            self,
            db_session_maker: sessionmaker,
            db_logger: logging.Logger,
            google_sheet_api: GoogleSheetAPI,
            google_maps_api: GoogleMapsAPI,
            messages: MessagesConfig,
            buttons: ButtonsConfig,
            logger: logging.Logger,
            page_size: int):
        super().__init__()
        self.db_session_maker = db_session_maker
        self.db_logger = db_logger
        self.google_sheet_api = google_sheet_api
        self.google_maps_api = google_maps_api
        self.messages = messages
        self.buttons = buttons
        self.logger = logger
        self.page_size = page_size
        self.update_types = ['message', 'callback_query']

    # argument naming is kept from the base class to avoid possible errors if passed as kwargs
    def pre_process(self, message, data: dict):
        # passing extra arguments to handlers
        db_adapter = DBAdapter(self.db_session_maker(), self.db_logger)
        data['db_adapter'] = db_adapter
        data['google_sheet_api'] = self.google_sheet_api
        data['google_maps_api'] = self.google_maps_api
        data['messages'] = self.messages
        data['buttons'] = self.buttons
        data['logger'] = self.logger
        data['page_size'] = self.page_size

    # argument naming is kept from the base class to avoid possible errors if passed as kwargs
    def post_process(self, message, data: dict, exception: BaseException):
        data['db_adapter'].session.close()
