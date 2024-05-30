import math
from typing import Optional

from telebot.util import content_type_media, content_type_service

from . import texts
from ..db.dto import OrderDTO

all_content_types = content_type_media + content_type_service


# Can be used to fill the required func parameter in the TeleBot.register_callback_query_handler method
def dummy_true(*args, **kwargs):
    return True


def calculate_concrete_cost(price: float, amount: int, discount=0):
    cost = price * amount
    if discount:
        cost -= cost * discount / 100
    return cost


def calculate_delivery_cost(price_list: list[str], distance: float, amount: int = 0, discount=0) -> float:
    """
    Calculates the delivery cost of concrete mix.

    :param price_list: list of prices per km for delivery
    :param distance: delivery distance in meters
    :param amount: volume of concrete ordered in m³
    :param discount: discount in percentage (default is 0)
    :return: total delivery cost
    """

    # Convert distance from meters to kilometers and round down
    kilometres = int(round(distance / 1000, 2))

    # Minimum amount of concrete for calculation
    if not amount:
        amount = 1
    elif amount < 7:
        amount = 7

    # Calculate delivery cost
    if kilometres <= 50:
        cost = float(price_list[kilometres - 1]) * amount
    else:
        base_cost = float(price_list[-2]) * amount
        extra_cost_per_km = float(price_list[-1]) * amount
        extra_distance = kilometres - 50
        cost = base_cost + extra_cost_per_km * extra_distance

    # Apply discount if any
    if discount:
        cost -= cost * discount / 100

    return round(cost, 2)


def format_order(order_dto: OrderDTO):
    user = order_dto.user
    msg = f"<b>Нове замовлення!</b>\n\n"
    if user.tg_username:
        msg += f"<i><b>Від:</b></i> @{user.tg_username}\n\n"
    else:
        msg += f"<i><b>Від:</b></i> <a href=\"tg://user?id={user.tg_user_id}\">{user.first_name}</a>\n\n"

    msg += (
        f"<i><b>Адреса доставки:</b></i> {order_dto.user_location.address}\n"
        f"<i><b>Точка відправлення:</b></i> {order_dto.dispatch_point.address}\n"
        f"<i><b>Відстань:</b></i> {round(order_dto.distance.distance_metres / 1000), 2} км\n\n"
        f"<i><b>Вид бетону:</b></i> {order_dto.concrete.title} ({order_dto.concrete.price} UAH/м3)\n"
        f"<i><b>Кількість:</b></i> {order_dto.amount} м3\n"
        f"<i><b>Вартість бетону:</b></i> {order_dto.concrete_cost} UAH\n"
        f"<i><b>Вартість достави:</b></i> {order_dto.delivery_cost} UAH\n\n"
        f"- - - - - - - - - - - - - - - - - - - - -\n\n"
        f"<b>Сума:</b> {round(order_dto.concrete_cost + order_dto.delivery_cost, 2)} UAH "
        f"({round((order_dto.concrete_cost + order_dto.delivery_cost) / order_dto.amount, 2)} UAH/м3)\n"
    )

    return msg


def format_price_with_discount(original_price: float, discount: Optional[float]) -> str:
    """
    Formats the price considering the discount.

    Args:
        original_price (float): The initial price.
        discount (Optional[float]): The discount percentage.

    Returns:
        str: The formatted string with the price and discount.
    """
    if discount:
        discounted_price = round(original_price - (original_price * discount / 100), 2)
        return f"<s>{original_price} UAH</s> <b>{discounted_price} UAH</b> (-{discount}%)"
    else:
        return f"<b>{original_price} UAH</b>"


def create_order_message(order_dto: OrderDTO, google_sheet_api) -> str:
    """
    Creates an order message with detailed costs.

    Args:
        order_dto: The order data transfer object.
        google_sheet_api: Google Sheet API instance for retrieving delivery price list.

    Returns:
        str: The formatted order message with details.
    """

    # Format concrete price
    concrete_price_msg = format_price_with_discount(order_dto.concrete_cost, order_dto.user.concrete_discount)
    msg = f"Ціна бетону: <i>{order_dto.amount} m³ × {order_dto.concrete.price}</i> = {concrete_price_msg}\n"

    # Format delivery price
    print(order_dto.concrete.type_)
    if order_dto.concrete.type_ in ["P1", "P2"]:
        delivery_price_msg = format_price_with_discount(order_dto.delivery_cost, order_dto.user.delivery_discount)
        msg += (f"Ціна достави*: "
                f"<i>{int(math.ceil(order_dto.amount / MAX_TRACK_AMOUNT))} × {order_dto.delivery_price} "
                f"({int(order_dto.distance.distance_metres / 1000)} km)</i> = {delivery_price_msg}\n")
    else:
        delivery_price_msg = format_price_with_discount(order_dto.delivery_cost, order_dto.user.delivery_discount)
        msg += (
            f"Ціна достави: "
            f"<i>{order_dto.amount if order_dto.amount >= 7 else '7*'} m³ × {order_dto.delivery_price} </i> "
            f"({int(order_dto.distance.distance_metres / 1000)} km) = {delivery_price_msg}\n")

    # Calculate total cost
    concrete_cost = round(order_dto.concrete_cost - order_dto.get_concrete_discount(), 2)
    delivery_cost = round(order_dto.delivery_cost - order_dto.get_delivery_discount(), 2)
    total_cost = round(concrete_cost + delivery_cost, 2)
    cost_per_m3 = round((concrete_cost + delivery_cost) / order_dto.amount, 2)

    msg += (f"\n<b>Сума:</b> {concrete_cost} + {delivery_cost} = <b>{total_cost} UAH</b> "
            f"<i>({cost_per_m3} UAH/м³)</i>\n")

    if order_dto.amount < 7 and order_dto.concrete.type_ not in ["P1", "P2"]:
        msg += f"\n<em>*{texts.less_than_7_m3}</em>"
    else:
        msg += f"\n<em>*{texts.more_than_one_truck}</em>"

    return msg

