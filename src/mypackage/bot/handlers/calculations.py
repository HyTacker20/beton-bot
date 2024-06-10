import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from typing import Dict, Tuple

from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from .. import texts, keyboards, GoogleMapsAPI
from ..keyboards import create_inline_keyboard
from ..texts import main_menu, admin_panel
from ..utils import dummy_true, calculate_delivery_cost, format_order, create_order_message, find_best_producer
from ...bot import GoogleSheetAPI
from ...config.models import ButtonsConfig
from ...db import DBAdapter
from ...db.dto import OrderDTO, DispatchPointDTO, DistanceDTO

DEBUG = True

user_orders: Dict[int, OrderDTO] = {}
user_closest_dispatch_points: Dict[int, Tuple[DispatchPointDTO, DistanceDTO]] = {}


def clear_cache(user_tg_id):
    if user_tg_id in user_orders.keys():
        del user_orders[user_tg_id]
    if user_tg_id in user_closest_dispatch_points.keys():
        del user_closest_dispatch_points[user_tg_id]


def refresh(
        message: Message,
        bot: TeleBot,
        google_sheet_api: GoogleSheetAPI):
    print("refresh data!")
    google_sheet_api.remove_data()
    google_sheet_api.check_producers()
    bot.send_message(message.chat.id, "Дані оновлено!")


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
    clear_cache(message.chat.id)

    user = db_adapter.get_user_with_discounts(message.from_user.id)
    print(f"{user.discounts=}")
    user_dto = user.to_dto()
    order_dto = OrderDTO(user_dto)
    user_orders[message.from_user.id] = order_dto
    print(f"{message.from_user.id=}")
    bot.send_message(message.chat.id, f"{texts.payment_type}\n\n<i>Натисніть для зміни</i>",
                     reply_markup=keyboards.create_inline_keyboard([texts.cash_payment],
                                                                   prefix="payment_"),
                     parse_mode="HTML")
    bot.send_message(message.chat.id, texts.get_location_message,
                     reply_markup=keyboards.create_keyboard([main_menu.cancel_button]))
    bot.register_next_step_handler(message, get_user_location, bot=bot, buttons=buttons,
                                   google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                   db_adapter=db_adapter, logger=logger)


def choose_payment_type(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "payment_"
    payment_type = call.data[len(prefix):]
    order_dto = user_orders[call.from_user.id]
    order_dto.payment_type = texts.cashless_payment if payment_type == texts.cash_payment else texts.cash_payment
    bot.edit_message_text(f"{texts.payment_type}\n\n<i>Натисніть для зміни</i>",
                          chat_id=call.message.chat.id,
                          message_id=call.message.id,
                          parse_mode="HTML",
                          reply_markup=keyboards.create_inline_keyboard([order_dto.payment_type], prefix=prefix))


def get_user_location(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    print("/get user's location")
    order_dto = user_orders[message.from_user.id]
    if message.text == main_menu.cancel_button:
        bot.send_message(message.chat.id, admin_panel.back_to_main_menu_message,
                         reply_markup=keyboards.main_menu_keyboard(order_dto.user.is_admin))
        clear_cache(message.from_user.id)
        return

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
        get_closest_dispatch_point(call.message, bot=bot, buttons=buttons,
                                   google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                   db_adapter=db_adapter, logger=logger, user_id=call.from_user.id)
    else:
        bot.edit_message_text(call.message.text + "\n\n❌", chat_id=call.message.chat.id, message_id=call.message.id)
        bot.send_message(call.message.chat.id, texts.get_location_message,
                         reply_markup=keyboards.create_keyboard([main_menu.cancel_button]))
        bot.register_next_step_handler(call.message, get_user_location, bot=bot, buttons=buttons,
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
        user_id: int,
        **kwargs):
    order_dto = user_orders[user_id]

    geolocation_message_id = message.id

    producer_dtos = google_sheet_api.producers

    def get_closest_dispatch_points(producer_dto):
        return producer_dto.title, google_maps_api.get_closest_point(producer_dto.dispatch_points,
                                                                     order_dto.user_location.coords)

    with ThreadPoolExecutor() as executor:
        closest_dispatch_points_dict = dict(executor.map(get_closest_dispatch_points, producer_dtos))

    # print(dict(results))
    distance_dtos = [closest_point_data[1].distance_metres
                     for closest_point_data in closest_dispatch_points_dict.values()]
    print(f"{closest_dispatch_points_dict=}")
    user_closest_dispatch_points[user_id] = closest_dispatch_points_dict

    if all([distance > 150000 for distance in distance_dtos]):

        bot.edit_message_text(message.text + "\n\n❌", chat_id=message.chat.id, message_id=message.id)
        bot.send_message(message.chat.id, texts.user_location_too_far)
        bot.send_message(message.chat.id, texts.get_location_message,
                         reply_markup=keyboards.create_keyboard([main_menu.cancel_button]))
        bot.register_next_step_handler(message, get_user_location, bot=bot, buttons=buttons,
                                       google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                       db_adapter=db_adapter, logger=logger)
        return

    else:
        bot.edit_message_text(message.text + "\n\n✅", chat_id=message.chat.id, message_id=geolocation_message_id)

        delivery_price_list = google_sheet_api.get_delivery_price_list("P3")

        best_producer = find_best_producer(producer_dtos,
                                           closest_dispatch_points_dict,
                                           order_dto.user,
                                           delivery_price_list=delivery_price_list)

        print(best_producer.title)
        producers = db_adapter.get_all_producers()
        producer_dtos = [producer[0].to_dto() for producer in producers]
        producer_ids = [str(producer_dto.id) for producer_dto in producer_dtos]

        producers_title_keyboard = [
            f"{producer.title} {texts.best_option_emoji}"
            if producer.title == best_producer.title else producer.title
            for producer in producer_dtos]

        bot.send_message(message.chat.id, texts.choose_producer,
                         reply_markup=keyboards.create_inline_keyboard(producers_title_keyboard,
                                                                       prefix="producer_",
                                                                       callback_data=producer_ids))


def choose_concrete_producer(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "producer_"
    producer_id = int(call.data[len(prefix):])

    if call.from_user.id not in user_orders.keys():
        return

    order_dto = user_orders[call.from_user.id]

    producer = db_adapter.get_producer_by_id(producer_id)
    closest_dispatch_point = user_closest_dispatch_points[call.from_user.id][producer.title]

    order_dto.dispatch_point = closest_dispatch_point[0]
    order_dto.producer = producer.title
    order_dto.distance = closest_dispatch_point[1]
    user_orders[call.message.chat.id] = order_dto

    bot.send_message(call.message.chat.id,
                     texts.closest_point + f"<b>{closest_dispatch_point[0].address}</b> "
                                           f"<i>({int(closest_dispatch_point[1].distance_metres / 1000)} км)</i>",
                     parse_mode="HTML")

    print(closest_dispatch_point)

    concrete_data_dto = google_sheet_api.concrete_data
    concrete_type_titles_list = concrete_data_dto.concrete_type_titles
    bot.send_message(call.message.chat.id, texts.concrete_instruction_preview,
                     reply_markup=create_inline_keyboard(["Розгорнути"], prefix="instruction_"))
    bot.send_message(call.message.chat.id, texts.choose_concrete_type,
                     reply_markup=create_inline_keyboard(concrete_type_titles_list, prefix="type_"))


def fold_or_unfold_instruction(
        call: CallbackQuery,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    prefix = "instruction_"
    method = call.data[len(prefix):]

    if method == "Розгорнути":
        bot.edit_message_text(texts.concrete_instruction, chat_id=call.message.chat.id, message_id=call.message.id,
                              reply_markup=create_inline_keyboard(["Згорнути"], prefix="instruction_"))
    else:
        bot.edit_message_text(texts.concrete_instruction_preview,
                              chat_id=call.message.chat.id,
                              message_id=call.message.id,
                              reply_markup=create_inline_keyboard(["Розгорнути"], prefix="instruction_"))


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

    concrete_type_title = call.data[len(prefix):]

    if call.from_user.id not in user_orders.keys():
        return
    order_dto = user_orders[call.message.chat.id]
    msg = texts.cash_emoji if order_dto.payment_type == texts.cash_payment else texts.cashless_emoji
    msg += f" Категорія <b>{concrete_type_title}</b>.\nЦіна вказана з врахуванням доставки:\n\n"

    concrete_data_dto = google_sheet_api.concrete_data

    current_concrete_type = concrete_data_dto.get_type(concrete_type_title)

    concrete_type = concrete_type_title[:2]

    delivery_price_list = google_sheet_api.get_delivery_price_list(concrete_type)

    order_dto.delivery_price = calculate_delivery_cost(concrete_type, delivery_price_list,
                                                       order_dto.distance.distance_metres)

    user_discount = order_dto.user.get_producer_discounts(order_dto.producer)
    print(order_dto.payment_type)
    concrete_discount = user_discount.get_concrete_discount(order_dto.payment_type) if user_discount else 0
    delivery_discount = user_discount.get_delivery_discount(order_dto.payment_type) if user_discount else 0

    for concrete in current_concrete_type.concretes:
        concrete_price_with_discount = (concrete.price -
                                        concrete.price * concrete_discount / 100)

        delivery_price_with_discount = (order_dto.delivery_price -
                                        order_dto.delivery_price * delivery_discount / 100)
        msg += (f"{concrete.title} - "
                f"<b>{round(concrete_price_with_discount + delivery_price_with_discount, 2)}"
                f"</b> UAH за м³\n")

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
    if call.from_user.id not in user_orders.keys():
        return
    concrete_title = call.data[len(prefix):]
    concrete_data_dto = google_sheet_api.concrete_data
    current_concrete = concrete_data_dto.get_concrete(concrete_title)
    order_dto = user_orders[call.message.chat.id]
    order_dto.concrete = current_concrete

    msg = f"Ви обрали: <b>{current_concrete.title}</b>\n"

    user_discount = order_dto.user.get_producer_discounts(order_dto.producer)
    concrete_discount = user_discount.get_concrete_discount(order_dto.payment_type) if user_discount else 0
    delivery_discount = user_discount.get_delivery_discount(order_dto.payment_type) if user_discount else 0
    concrete_price_with_discount = current_concrete.price - current_concrete.price * concrete_discount / 100
    delivery_price_with_discount = order_dto.delivery_price - order_dto.delivery_price * delivery_discount / 100
    msg += texts.cash_emoji if order_dto.payment_type == texts.cash_payment else texts.cashless_emoji
    msg += f"Ціна за 1 м³: <b>{round(concrete_price_with_discount + delivery_price_with_discount, 2)} UAH</b>\n"
    bot.send_message(call.message.chat.id, msg, parse_mode="HTML",
                     reply_markup=keyboards.remove_reply())
    msg = "Скільки Вам потрібно м³?\nНапишіть число: "
    bot.send_message(call.message.chat.id, msg)
    bot.register_next_step_handler(call.message, get_concrete_amount, bot=bot, buttons=buttons,
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
        **kwargs):
    order_dto = user_orders[message.from_user.id]
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "Введіть будь ласка тільки число!")
        bot.register_next_step_handler(message, get_concrete_amount, bot=bot,
                                       order_dto=order_dto, buttons=buttons,
                                       google_sheet_api=google_sheet_api, google_maps_api=google_maps_api,
                                       db_adapter=db_adapter, logger=logger)
    order_dto.amount = int(message.text)

    order_dto.concrete_cost = round(order_dto.amount * order_dto.concrete.price, 2)
    order_dto.delivery_cost = calculate_delivery_cost(
        order_dto.concrete.type_,
        price_list=google_sheet_api.get_delivery_price_list(order_dto.concrete.type_),
        distance=order_dto.distance.distance_metres,
        amount=order_dto.amount)

    msg = create_order_message(order_dto)

    bot.send_message(message.chat.id, msg, parse_mode="HTML",
                     reply_markup=create_inline_keyboard(["Замовити", "Скасувати"], prefix="order_"))


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
    elif answer == "Скасувати":
        msg = texts.order_canceled
        bot.send_message(call.message.chat.id, msg, reply_markup=keyboards
                         .main_menu_keyboard(is_admin=user_orders[call.from_user.id].user.is_admin))
        return

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


def back_to_menu(
        message: Message,
        bot: TeleBot,
        buttons: ButtonsConfig,
        google_sheet_api: GoogleSheetAPI,
        google_maps_api: GoogleMapsAPI,
        db_adapter: DBAdapter,
        logger: Logger,
        **kwargs):
    if message.text == main_menu.cancel_button:
        if message.from_user.id in user_orders.keys():
            bot.send_message(message.chat.id, admin_panel.back_to_main_menu_message,
                             reply_markup=keyboards.main_menu_keyboard(
                                 user_orders[message.from_user.id].user.is_admin))
            clear_cache(message.from_user.id)
        else:
            bot.send_message(message.chat.id, admin_panel.back_to_main_menu_message,
                             reply_markup=keyboards.main_menu_keyboard(
                                 db_adapter.get_user(message.from_user.id).is_admin))


def register_handlers(bot: TeleBot):
    bot.register_message_handler(get_dispatch_point, commands=['calculate'], is_admin=True, pass_bot=True)
    bot.register_message_handler(refresh, commands=['refresh'], pass_bot=True)
    bot.register_message_handler(get_dispatch_point, text_equals=main_menu.make_calculation_button, pass_bot=True)
    bot.register_message_handler(back_to_menu, text_equals=main_menu.cancel_button, pass_bot=True)
    bot.register_callback_query_handler(concrete_type_button_handler, func=dummy_true, prefix="type_", pass_bot=True)
    bot.register_callback_query_handler(concrete_button_handler, func=dummy_true, prefix="concrete_", pass_bot=True)
    bot.register_callback_query_handler(choose_concrete_producer, func=dummy_true, prefix="producer_", pass_bot=True)
    bot.register_callback_query_handler(is_correct_geo, func=dummy_true, prefix="geo_", pass_bot=True)
    bot.register_callback_query_handler(confirm_order, func=dummy_true, prefix="order_", pass_bot=True)
    bot.register_callback_query_handler(fold_or_unfold_instruction, func=dummy_true,
                                        prefix="instruction_", pass_bot=True)
    bot.register_callback_query_handler(choose_payment_type, func=dummy_true, prefix="payment_", pass_bot=True)
