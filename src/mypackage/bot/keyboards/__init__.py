from typing import Iterable, Tuple, Generator, List

from telebot.types import InlineKeyboardMarkup
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton
from telebot.types import ReplyKeyboardRemove

from ..texts import main_menu, admin_panel
from ...db.dto import DispatchPointDTO


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


def create_inline_keyboard(buttons_list: Iterable, prefix="", callback_data: List = None):
    keyboard = InlineKeyboardMarkup()
    for i, button in enumerate(buttons_list):
        keyboard.add(
            InlineKeyboardButton(button, callback_data=prefix + callback_data[i] if callback_data else prefix + button)
        )
    return keyboard


def create_keyboard(buttons_list: Iterable):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons_list:
        keyboard.add(button)
    return keyboard


def create_inline_pagination_markup(
        buttons: Iterable[Tuple[str, str | int]] | Generator,
        callback_prefix: str,
        page: int,
        max_page: int
) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with pagination.

    Args:
        buttons: An iterable or generator of tuples, where each tuple contains the button text and callback data.
        callback_prefix: A prefix for the callback data to distinguish between different types of callbacks.
        page: The current page number.
        max_page: The maximum number of pages.

    Returns:
        InlineKeyboardMarkup: The inline keyboard markup with pagination buttons.
    """
    markup = InlineKeyboardMarkup()

    # Add user buttons to the markup
    for button in buttons:
        inline_button = InlineKeyboardButton(
            text=f"{button[0]}",
            callback_data=f"{callback_prefix}{str(button[1])}"
        )
        markup.add(inline_button)

    # Create navigation buttons for pagination
    navigation_buttons = [
        InlineKeyboardButton(
            text="⬅" if max_page > 1 and page != 1 else "­",
            callback_data=f"{callback_prefix}page#{page - 1}" if page > 1 else "none"
        ),
        InlineKeyboardButton(
            text=f"{page}/{max_page}",
            callback_data="none"
        ),
        InlineKeyboardButton(
            text="➡" if page != max_page else "­",
            callback_data=f"{callback_prefix}page#{page + 1}" if page < max_page else "none"
        )
    ]

    # Add navigation buttons to the markup if there are more than one page
    if max_page > 1:
        markup.add(*navigation_buttons)

    markup.row(
        InlineKeyboardButton(
            text="Назад", callback_data=f"{callback_prefix}back"
        )
    )

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
