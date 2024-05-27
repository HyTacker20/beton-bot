import logging

from sqlalchemy.orm import sessionmaker
from telebot import TeleBot

from .callback_query_antiflood import CallbackQueryAntiFloodMiddleware
from .extra_arguments import ExtraArgumentsMiddleware
from .message_antiflood import MessageAntiFloodMiddleware
from .. import GoogleSheetAPI, GoogleMapsAPI
from ...config.models import MessagesConfig, ButtonsConfig


def setup_middlewares(
        bot: TeleBot,
        db_session_maker: sessionmaker,
        db_logger: logging.Logger,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        timeout_message: str,
        timeout: float,
        messages: MessagesConfig,
        buttons: ButtonsConfig,
        logger: logging.Logger,
        page_size: int):
    # TODO: setup all middlewares here
    bot.setup_middleware(MessageAntiFloodMiddleware(bot, timeout_message, timeout))
    bot.setup_middleware(CallbackQueryAntiFloodMiddleware(bot, timeout_message, timeout))
    bot.setup_middleware(ExtraArgumentsMiddleware(db_session_maker, db_logger, google_sheet_api, google_maps_api,
                                                  messages, buttons, logger, page_size))
    pass
