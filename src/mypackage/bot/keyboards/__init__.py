from typing import List, Iterable, Tuple, Generator

from telebot.types import InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from telebot.types import ReplyKeyboardRemove

from ...db.dto import DispatchPointDTO
from ..texts import main_menu, admin_panel


# TODO: define all keyboards and/or keyboard builders here or in the submodules of this module


def main_menu_keyboard(is_admin: bool = False):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(main_menu.make_calculation_button))
    if is_admin:
        keyboard.add(KeyboardButton(main_menu.admin_button))
    # keyboard.add(KeyboardButton("Кнопка 2"))
    # keyboard.add(KeyboardButton("Кнопка 3"))
    return keyboard


def admin_panel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(admin_panel.make_mailing_button))
    keyboard.row(KeyboardButton(admin_panel.edit_texts_button),
                 KeyboardButton(admin_panel.statistics_button))
    keyboard.row(KeyboardButton(admin_panel.create_password_button),
                 KeyboardButton(admin_panel.users_discount_button))
    keyboard.add(KeyboardButton(admin_panel.back_to_main_menu_button))
    return keyboard


def dispatch_points_keyboard(dispatch_points_list: Iterable[DispatchPointDTO]):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for dp in dispatch_points_list:
        keyboard.add(KeyboardButton(dp.address))
    return keyboard


def create_inline_keyboard(buttons_list: Iterable, prefix=""):
    keyboard = InlineKeyboardMarkup()
    for button in buttons_list:
        keyboard.add(InlineKeyboardButton(button, callback_data=prefix + button))
    return keyboard


def create_keyboard(buttons_list: Iterable):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons_list:
        keyboard.add(button)
    return keyboard


def create_inline_pagination_markup(buttons: Iterable[Tuple[str, str]] | Generator, callback_prefix: str,
                                    page: int, max_page: int):
    markup = InlineKeyboardMarkup()
    for button in buttons:
        inline_button = InlineKeyboardButton(f"{button[0]}", callback_data=f"{callback_prefix + str(button[1])}")
        markup.add(inline_button)

    navigation_buttons = [InlineKeyboardButton("⬅" if max_page > 1 and not page == 1 else "­",
                                               callback_data=f"{callback_prefix}page#{page - 1}"
                                               if 0 < page - 1 else "none"),
                          InlineKeyboardButton(f"{page}/{max_page}", callback_data="none"),
                          InlineKeyboardButton("➡" if not page == max_page else "­",
                                               callback_data=f"{callback_prefix}page#{page + 1}"
                                               if page + 1 <= max_page else "none")]

    if navigation_buttons:
        markup.add(*navigation_buttons)

    return markup


def help_reply_keyboard(help_btn: str):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(help_btn))
    return keyboard


def empty_inline():
    return InlineKeyboardMarkup()


def empty_reply():
    return ReplyKeyboardMarkup()


def remove_reply():
    return ReplyKeyboardRemove()
