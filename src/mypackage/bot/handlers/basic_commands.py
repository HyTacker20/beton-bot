from logging import Logger

from sqlalchemy.exc import IntegrityError
from telebot import TeleBot
from telebot.types import Message

from .. import keyboards
from ..texts.main_menu import welcome_message
from ...config.models import MessagesConfig, ButtonsConfig
from ...db import DBAdapter, DBError
from ...db.dto import NewUserDTO


# Basic commands

# 1. start - send a welcome message with help reply keyboard
# 2. help - send a help message


def start_handler(
        message: Message,
        bot: TeleBot,
        messages: MessagesConfig,
        buttons: ButtonsConfig,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    logger.debug(f"User {message.from_user.id} @{message.from_user.username} started the bot")

    # bot.set_state(message.from_user.id, UnregisteredStates.started, message.chat.id)

    try:
        user = db_adapter.get_user(message.from_user.id)

    except DBError as e:
        logger.error(e)
        bot.send_message(message.chat.id, messages.unknown_error)
        return

    else:
        if user is None:
            print("user not found")
            try:
                new_user_dto = NewUserDTO.from_tg_message(message)

                user_added = db_adapter.add_user(new_user_dto)
                print(user_added)

            except (DBError, IntegrityError) as e:
                logger.error(e)
                bot.send_message(message.chat.id, messages.unknown_error)
                return

            else:
                if user_added is False:
                    logger.error(
                        f'Constraints violation while adding telegram account:'
                        f' {message.from_user.id}, {message.chat.id}, {message.from_user.username}'
                    )
                    bot.send_message(message.chat.id, messages.add_tg_account_error)
                    return
                else:
                    logger.debug(
                        f'User added:'
                        f'{message.from_user.first_name} {message.from_user.id}, '
                        f'{message.chat.id}, {message.from_user.username}'
                    )

        bot.send_message(message.chat.id, welcome_message,
                         reply_markup=keyboards.main_menu_keyboard(user.is_admin if user else False))


def help_handler(
        message: Message,
        bot: TeleBot,
        messages: MessagesConfig,
        logger: Logger,
        **kwargs):
    logger.debug(f"User {message.from_user.id} @{message.from_user.username} requested help")
    bot.send_message(message.chat.id, messages.help)


def register_handlers(bot: TeleBot, buttons: ButtonsConfig):
    bot.register_message_handler(start_handler, commands=['start'], pass_bot=True)

    bot.register_message_handler(help_handler, commands=['help'], pass_bot=True)
    bot.register_message_handler(help_handler, text_equals=buttons.help, pass_bot=True)
