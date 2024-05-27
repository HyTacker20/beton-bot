import logging
import random
from logging import Logger
from math import ceil

from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from .. import keyboards, texts
from ..texts import main_menu, admin_panel
from ..utils import dummy_true
from ...bot import GoogleSheetAPI, GoogleMapsAPI
from ...config.models import ButtonsConfig
from ...db import DBAdapter, DBError

USERS_PER_PAGE = 5


def send_admin_panel(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    print('-------------------')
    print('/admin_panel')
    bot.send_message(message.chat.id, admin_panel.welcome_to_admin_panel_message,
                     reply_markup=keyboards.admin_panel_keyboard())


def back_to_main_menu(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    print('-------------------')
    print('/back_to_main_menu')
    bot.send_message(message.chat.id, admin_panel.back_to_main_menu_message,
                     reply_markup=keyboards.main_menu_keyboard(is_admin=True))


def send_user_discount_list(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    print('-------------------')
    print('/set_discount')
    users = db_adapter.get_all_users(offset=0, limit=USERS_PER_PAGE)
    users_count = db_adapter.get_all_users_count()
    print(users_count)
    print(users)
    buttons = ((f"@{user[0].tg_username} ({user[0].concrete_discount}/{user[0].delivery_discount})", user[0].tg_user_id)
               if user[0].tg_username
               else (
        f"{user[0].first_name} ({user[0].concrete_discount}/{user[0].delivery_discount})", user[0].tg_user_id)
               for user in users)
    print(users_count / USERS_PER_PAGE)
    print(ceil(users_count / USERS_PER_PAGE))
    keyboard = keyboards.create_inline_pagination_markup(buttons, callback_prefix="user_", page=1,
                                                         max_page=ceil(users_count / USERS_PER_PAGE))

    bot.send_message(message.chat.id, admin_panel.all_users_discount_message, reply_markup=keyboard)


def edit_user_discount_list(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: logging.Logger,
        **kwargs):
    prefix = "user_page#"
    page_data = call.data[len(prefix):]
    print(call.data)
    print(page_data)

    if not page_data.isdigit():
        logger.error(f"Invalid page number: {page_data}")
        return

    page = int(page_data)
    logger.debug(f"Editing user discount list, page: {page}")

    try:
        offset = (page-1) * USERS_PER_PAGE
        logger.debug(f"Fetching users with offset: {offset} and limit: {USERS_PER_PAGE}")
        users = db_adapter.get_all_users(offset=offset, limit=USERS_PER_PAGE)
        logger.debug(f"Fetched users: {users}")
        users_count = db_adapter.get_all_users_count()
        logger.debug(f"Total user count: {users_count}")
    except DBError as e:
        logger.error(e)
        bot.send_message(call.message.chat.id, texts.unknown_error)
        return

    max_page = ceil(users_count / USERS_PER_PAGE)
    logger.debug(f"Max page number: {max_page}")

    if max_page < page or page < 1:
        logger.error(f"Page number out of range: {page}")
        return

    buttons = (
        (f"@{user[0].tg_username} ({user[0].concrete_discount}/{user[0].delivery_discount})", user[0].tg_user_id)
        if user[0].tg_username
        else (
            f"{user[0].first_name} ({user[0].concrete_discount}/{user[0].delivery_discount})", user[0].tg_user_id)
        for user in users)

    keyboard = keyboards.create_inline_pagination_markup(buttons, callback_prefix="user_", page=page, max_page=max_page)

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )


def choose_user(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "user_"
    print("user_id")
    print(call.data)
    tg_user_id = call.data[len(prefix):]

    user = db_adapter.get_user(int(tg_user_id))

    msg = (f"Надішліть розмір знижки на бетон та доставку "
           f"для {'@' + user.tg_username if user.tg_username else user.first_name}.\n\n"
           f"Наприклад: {random.randint(0, 100)} {random.randint(0, 100)}")

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.empty_inline()
    )
    bot.send_message(call.message.chat.id, msg, reply_markup=keyboards.remove_reply())
    bot.register_next_step_handler(call.message, set_discount, bot=bot, buttons=buttons,
                                   google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                   db_adapter=db_adapter, logger=logger, user_id=tg_user_id)


def set_discount(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: logging.Logger,
        user_id: int,
        **kwargs):
    print('-------------------')
    print('/set_discount')
    print(message.text)
    text_parts = message.text.split()
    print(text_parts)

    if len(text_parts) != 2:
        bot.send_message(message.chat.id, admin_panel.uncorrected_format_message,
                         reply_markup=keyboards.admin_panel_keyboard())
        return

    try:
        concrete_discount = int(text_parts[0])
        delivery_discount = int(text_parts[1])
    except ValueError:
        bot.send_message(message.chat.id, admin_panel.uncorrected_format_two_digits_message,
                         reply_markup=keyboards.admin_panel_keyboard())
        return
    else:
        result = db_adapter.update_user_discount(user_id, concrete_discount, delivery_discount)
        print(result)
        bot.send_message(message.chat.id, admin_panel.user_discount_updated_success_message,
                         reply_markup=keyboards.admin_panel_keyboard())


def register_handlers(bot: TeleBot):
    bot.register_message_handler(send_admin_panel, commands=['admin_panel'], is_admin=True, pass_bot=True)

    bot.register_message_handler(send_admin_panel, text_equals=main_menu.admin_button, is_admin=True, pass_bot=True)
    bot.register_message_handler(back_to_main_menu, text_equals=admin_panel.back_to_main_menu_button,
                                 is_admin=True, pass_bot=True)
    bot.register_message_handler(send_user_discount_list, text_equals=admin_panel.users_discount_button,
                                 is_admin=True, pass_bot=True)
    bot.register_callback_query_handler(edit_user_discount_list, func=dummy_true,
                                        pagination_prefix="user_page", pass_bot=True)
    bot.register_callback_query_handler(choose_user, func=dummy_true, prefix="user_", pass_bot=True)
