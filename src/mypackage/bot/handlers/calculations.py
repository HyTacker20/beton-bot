import os
from logging import Logger
from typing import Dict

from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from .. import texts, keyboards, GoogleMapsAPI
from ..keyboards import create_inline_keyboard
from ..texts import main_menu
from ..utils import dummy_true, calculate_delivery_cost, format_order, create_order_message
from ...bot import GoogleSheetAPI
from ...config.models import ButtonsConfig
from ...db import DBAdapter
from ...db.dto import OrderDTO, UserDTO

DEBUG = True

user_orders: Dict[int, OrderDTO] = {}


def refresh(
        message: Message,
        bot: TeleBot,
        google_sheet_api: GoogleSheetAPI):
    print("refresh data!")
    google_sheet_api.update_dispatch_points()
    google_sheet_api.remove_data()
    bot.send_message(message.chat.id, "Дані оновлені!")


def get_dispatch_point(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    print('-------------------')
    print('/calculate')

    user = db_adapter.get_user(message.from_user.id)
    user_dto = UserDTO(**user.to_dict())
    print(user_dto)
    order_dto = OrderDTO(user_dto)

    bot.send_message(message.chat.id, texts.get_location_message,
                     reply_markup=keyboards.remove_reply())
    bot.register_next_step_handler(message, get_user_location, order_dto=order_dto, bot=bot, buttons=buttons,
                                   google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                   db_adapter=db_adapter, logger=logger)


def get_user_location(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        order_dto: OrderDTO,
        **kwargs):
    print("/get user's location")

    if message.text:
        if DEBUG and message.text == ".":
            message.text = "Майдан Незалежності, Київ, Україна, 02000"
        user_location = google_maps_api.from_address(message.text, debug=DEBUG)

        if not user_location:
            bot.send_message(message.chat.id, texts.geopos_not_found,
                             reply_markup=keyboards.main_menu_keyboard(is_admin=order_dto.user.is_admin))
            return

        user_location.address += f" ({message.text})"

    else:
        coords = message.location.latitude, message.location.longitude
        user_location = google_maps_api.from_coords(coords, debug=DEBUG)

    order_dto.user_location = user_location
    user_orders[message.from_user.id] = order_dto
    print(user_location)

    msg = f"{texts.is_user_location}\n\n"
    msg += user_location.address
    bot.send_message(message.chat.id, msg, parse_mode="HTML",
                     reply_markup=keyboards.create_inline_keyboard(["Так", "Спробувати ще раз"],
                                                                   "geo_"))


def is_correct_geo(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "geo_"
    answer = call.data[len(prefix):]

    if answer == "Так":
        bot.edit_message_text(call.message.text + "\n\n🕑", chat_id=call.message.chat.id, message_id=call.message.id)
        get_closest_dispatch_point(call.message, order_dto=user_orders[call.from_user.id], bot=bot, buttons=buttons,
                                   google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                   db_adapter=db_adapter, logger=logger)
    else:
        bot.edit_message_text(call.message.text + "\n\n❌", chat_id=call.message.chat.id, message_id=call.message.id)
        bot.send_message(call.message.chat.id, texts.get_location_message,
                         reply_markup=keyboards.remove_reply())
        bot.register_next_step_handler(call.message, get_user_location, bot=bot,
                                       order_dto=user_orders[call.message.chat.id], buttons=buttons,
                                       google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                       db_adapter=db_adapter, logger=logger)


def get_closest_dispatch_point(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        order_dto: OrderDTO,
        **kwargs):
    closest_dispatch_point, distance = google_maps_api.get_closest_point(google_sheet_api.get_dispatch_points(),
                                                                         order_dto.user_location.coords)
    geolocation_message_id = message.id

    if distance.distance_metres > 150000:

        bot.edit_message_text(message.text + "\n\n❌", chat_id=message.chat.id, message_id=message.id)
        bot.send_message(message.chat.id, texts.user_location_too_far)
        bot.send_message(message.chat.id, texts.get_location_message,
                         reply_markup=keyboards.remove_reply())
        bot.register_next_step_handler(message, get_user_location, bot=bot,
                                       order_dto=order_dto, buttons=buttons,
                                       google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                       db_adapter=db_adapter, logger=logger)
        return

    else:
        bot.edit_message_text(message.text + "\n\n✅", chat_id=message.chat.id, message_id=geolocation_message_id)

    bot.send_message(message.chat.id, texts.closest_point + f"<b>{closest_dispatch_point.address}</b>  "
                                                            f"<i>({int(distance.distance_metres / 1000)} км)</i>",
                     parse_mode="HTML")
    order_dto.dispatch_point = closest_dispatch_point
    order_dto.distance = distance
    print(closest_dispatch_point)
    user_orders[message.chat.id] = order_dto

    concrete_data_dto = google_sheet_api.get_concrete_data()
    concrete_type_titles_list = concrete_data_dto.concrete_type_titles
    bot.send_message(message.chat.id, texts.concrete_instruction)
    bot.send_message(message.chat.id, texts.choose_concrete_type,
                     reply_markup=create_inline_keyboard(concrete_type_titles_list, prefix="type_"))


def concrete_type_button_handler(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "type_"

    print(call.data)
    concrete_type_title = call.data[len(prefix):]

    msg = f"Категорія <b>{concrete_type_title}</b>.\nЦіна вказана з врахуванням доставки:\n\n"

    concrete_data_dto = google_sheet_api.get_concrete_data()

    current_concrete_type = concrete_data_dto.get_type(concrete_type_title)

    delivery_price_list = google_sheet_api.get_delivery_price_list()

    order_dto = user_orders[call.message.chat.id]

    order_dto.delivery_price = calculate_delivery_cost(delivery_price_list, order_dto.distance.distance_metres)

    for concrete in current_concrete_type.concretes:
        msg += f"{concrete.title} - <b>{round(concrete.price + order_dto.delivery_price, 2)}</b> UAH за м³\n"

    bot.send_message(call.message.chat.id, msg, parse_mode="HTML",
                     reply_markup=create_inline_keyboard([concrete.title
                                                          for concrete in current_concrete_type.concretes],
                                                         prefix="concrete_"))


def concrete_button_handler(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "concrete_"
    concrete_title = call.data[len(prefix):]
    concrete_data_dto = google_sheet_api.get_concrete_data()
    current_concrete = concrete_data_dto.get_concrete(concrete_title)
    user_orders[call.message.chat.id].concrete = current_concrete

    msg = f"Ви обрали: <b>{current_concrete.title}</b>\n"
    msg += f"Ціна за 1 м³: <b>{round(current_concrete.price + 
                                     user_orders[call.from_user.id].delivery_price, 2)} UAH</b>\n"
    bot.send_message(call.message.chat.id, msg, parse_mode="HTML",
                     reply_markup=keyboards.remove_reply())
    msg = "Скільки Вам потрібно м³?\nНапишіть число: "
    bot.send_message(call.message.chat.id, msg)
    bot.register_next_step_handler(call.message, get_concrete_amount, bot=bot,
                                   order_dto=user_orders[call.message.chat.id], buttons=buttons,
                                   google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                   db_adapter=db_adapter, logger=logger)


def get_concrete_amount(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        order_dto: OrderDTO,
        **kwargs):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Введіть будь ласка тільки число!")
        bot.register_next_step_handler(message, get_concrete_amount, bot=bot,
                                       order_dto=order_dto, buttons=buttons,
                                       google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                       db_adapter=db_adapter, logger=logger)
    order_dto.amount = int(message.text)
    print(order_dto)

    order_dto.concrete_cost = round(order_dto.amount * order_dto.concrete.price, 2)
    order_dto.delivery_cost = calculate_delivery_cost(price_list=google_sheet_api.get_delivery_price_list(),
                                                      distance=order_dto.distance.distance_metres,
                                                      amount=order_dto.amount)

    msg = create_order_message(order_dto, google_sheet_api)

    bot.send_message(message.chat.id, msg, parse_mode="HTML",
                     reply_markup=create_inline_keyboard(["Замовити"], prefix="order_"))


def confirm_order(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "order_"
    answer = call.data[len(prefix):]

    if answer == "Замовити":
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=keyboards.create_inline_keyboard(["Підтвердити", "Скасувати"],
                                                                                    prefix="order_"))

    else:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      reply_markup=keyboards.empty_inline())

        if answer == "Підтвердити":
            from dotenv import load_dotenv
            load_dotenv()

            msg = texts.order_confirmed
            bot.send_message(os.environ.get("OWNER_TG_ID"),
                             format_order(order_dto=user_orders[call.from_user.id]),
                             parse_mode="HTML")
            bot.send_message(89791483,
                             format_order(order_dto=user_orders[call.from_user.id]),
                             parse_mode="HTML")

        elif answer == "Скасувати":
            msg = texts.order_canceled

        else:
            msg = texts.unknown_error

        bot.send_message(call.message.chat.id, msg, reply_markup=keyboards
                         .main_menu_keyboard(is_admin=user_orders[call.from_user.id].user.is_admin))


def register_handlers(bot: TeleBot):
    bot.register_message_handler(get_dispatch_point, commands=['calculate'], is_admin=True, pass_bot=True)
    bot.register_message_handler(refresh, commands=['refresh'], pass_bot=True)
    bot.register_message_handler(get_dispatch_point, text_equals=main_menu.button_1, pass_bot=True)
    bot.register_callback_query_handler(concrete_type_button_handler, func=dummy_true, prefix="type_", pass_bot=True)
    bot.register_callback_query_handler(concrete_button_handler, func=dummy_true, prefix="concrete_", pass_bot=True)
    bot.register_callback_query_handler(is_correct_geo, func=dummy_true, prefix="geo_", pass_bot=True)
    bot.register_callback_query_handler(confirm_order, func=dummy_true, prefix="order_", pass_bot=True)
