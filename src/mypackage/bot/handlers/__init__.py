from telebot import TeleBot

from ...config.models import ButtonsConfig

from . import (
    basic_commands,
    unhandled, calculations,
    admin_menu
)


def register_handlers(bot: TeleBot, buttons: ButtonsConfig):
    # TODO: register all handlers here
    basic_commands.register_handlers(bot, buttons)
    calculations.register_handlers(bot)
    admin_menu.register_handlers(bot)
    print("tg handlers ready!")

    # TODO: register all other handlers before this line
    # unhandled.register_handlers(bot)
