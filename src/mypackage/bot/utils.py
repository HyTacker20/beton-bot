import math
from typing import Optional, List

from telebot.util import content_type_media, content_type_service

from . import texts

all_content_types = content_type_media + content_type_service

MIN_MIXER_AMOUNT = 7
MAX_TRACK_AMOUNT = 2.5


# Can be used to fill the required func parameter in the TeleBot.register_callback_query_handler method
def dummy_true(*args, **kwargs):
    return True


def calculate_concrete_cost(price: float, amount: int, discount: Optional[float] = 0) -> float:
    """
    Calculates the total cost of concrete considering the price, amount, and discount.

    :param price: Price per unit of concrete.
    :param amount: Amount of concrete.
    :param discount: Discount percentage.
    :return: Total cost.
    """
    cost = price * amount
    if discount:
        cost -= cost * discount / 100
    return cost


def calculate_cost(kilometres: int, price_list: List[str], deliveries_count: int, amount: int) -> float:
    """
    Helper function to calculate delivery cost based on distance and amount.

    :param kilometres: Delivery distance in kilometers.
    :param price_list: List of prices per km for delivery.
    :param deliveries_count: Number of deliveries needed.
    :param amount: Volume of concrete ordered in m³.
    :return: Delivery cost.
    """
    if kilometres <= 50:
        return float(price_list[kilometres - 1]) * deliveries_count * amount
    else:
        base_cost = float(price_list[-2]) * deliveries_count * amount
        extra_cost_per_km = float(price_list[-1]) * deliveries_count * amount
        extra_distance = kilometres - 50
        return base_cost + extra_cost_per_km * extra_distance


def calculate_delivery_cost(concrete_type: str, price_list: List[str], distance: int, amount: int = 0) -> float:
    """
    Calculates the delivery cost of concrete mix.

    :param concrete_type: Type of concrete (e.g., "P1", "P2").
    :param price_list: List of prices per km for delivery.
    :param distance: Delivery distance in meters.
    :param amount: Volume of concrete ordered in m³.
    :return: Total delivery cost.
    """
    kilometres = int(round(distance / 1000, 2))
    deliveries_count = 1

    if concrete_type in ["P1", "P2"]:
        # Ensure amount meets the minimum required for these types
        amount = max(amount, MAX_TRACK_AMOUNT)
        deliveries_count = int(math.ceil(amount / MAX_TRACK_AMOUNT))
    else:
        # Ensure amount meets the minimum required for other types
        amount = max(amount, MIN_MIXER_AMOUNT)

    cost = calculate_cost(kilometres, price_list, deliveries_count, amount)
    return round(cost, 2)


def format_user_info(user) -> str:
    """
    Formats the user information into a message.

    :param user: The user object.
    :return: The formatted string with the user information.
    """
    if user.tg_username:
        return f"<i><b>Від:</b></i> @{user.tg_username}\n\n"
    else:
        return f"<i><b>Від:</b></i> <a href=\"tg://user?id={user.tg_user_id}\">{user.first_name}</a>\n\n"


def format_order(order_dto) -> str:
    """
    Formats the order details into a message.

    :param order_dto: The order data transfer object.
    :return: Formatted order message.
    """
    user = order_dto.user
    msg = f"<b>Нове замовлення!</b>\n\n"
    msg += format_user_info(user)

    msg += (
        f"<i><b>Адреса доставки:</b></i> {order_dto.user_location.address}\n"
        f"<i><b>Точка відправлення:</b></i> {order_dto.dispatch_point.address}\n"
        f"<i><b>Відстань:</b></i> {round(order_dto.distance.distance_metres / 1000, 2)} км\n\n"
        f"<i><b>Вид бетону:</b></i> {order_dto.concrete.title} ({order_dto.concrete.price} UAH/м3)\n"
        f"<i><b>Кількість:</b></i> {order_dto.amount} м3\n"
        f"<i><b>Вартість бетону{f' (-{user.concrete_discount}%)' if user.concrete_discount else ''}:</b></i> "
        f"{format_price_with_discount(order_dto.concrete_cost, user.concrete_discount)}\n"
        f"<i><b>Вартість достави{f' (-{user.delivery_discount}%)' if user.delivery_discount else ''}:</b></i> "
        f"{format_price_with_discount(order_dto.delivery_cost, user.delivery_discount)}\n\n"
        f"- - - - - - - - - - - - - - - - - - - - -\n\n"
        f"<b>Сума:</b> {round(order_dto.concrete_cost_with_discount + order_dto.delivery_cost_with_discount, 2)} UAH "
        f"({round((order_dto.concrete_cost_with_discount + order_dto.delivery_cost_with_discount) / order_dto.amount, 2)} UAH/м3)\n"
    )

    return msg


def format_price_with_discount(original_price: float, discount: Optional[int]) -> str:
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
        return f"<s>{original_price} UAH</s> <b>{discounted_price} UAH</b>"
    else:
        return f"<b>{original_price} UAH</b>"


def format_delivery_message(order_dto, deliveries_count: int) -> str:
    """
    Formats the delivery cost message.

    :param order_dto: The order data transfer object.
    :param deliveries_count: The number of deliveries needed.
    :return: The formatted delivery cost message.
    """
    delivery_price_msg = format_price_with_discount(order_dto.delivery_cost, order_dto.user.delivery_discount)
    if order_dto.concrete.type_ in ["P1", "P2"]:
        return (f"Ціна достави*: <i>{deliveries_count} × {order_dto.delivery_price} "
                f"({int(order_dto.distance.distance_metres / 1000)} km)</i> = {delivery_price_msg}\n")
    else:
        return (
            f"Ціна достави: <i>{order_dto.amount if order_dto.amount >= 7 else '7*'} m³ × {order_dto.delivery_price} "
            f"({int(order_dto.distance.distance_metres / 1000)} km)</i> = {delivery_price_msg}\n")


def create_order_message(order_dto) -> str:
    """
    Creates an order message with detailed costs.

    Args:
        order_dto: The order data transfer object.

    Returns:
        str: The formatted order message with details.
    """
    # Format concrete price message
    concrete_price_msg = format_price_with_discount(order_dto.concrete_cost, order_dto.user.concrete_discount)
    msg = f"Ціна бетону: <i>{order_dto.amount} m³ × {order_dto.concrete.price}</i> = {concrete_price_msg}\n"

    # Calculate deliveries count if needed
    deliveries_count = int(math.ceil(order_dto.amount / MAX_TRACK_AMOUNT)) if order_dto.concrete.type_ in ["P1",
                                                                                                           "P2"] else 1

    # Format delivery price message
    msg += format_delivery_message(order_dto, deliveries_count)

    # Calculate costs
    concrete_cost = round(order_dto.concrete_cost - order_dto.get_concrete_discount(), 2)
    delivery_cost = round(order_dto.delivery_cost - order_dto.get_delivery_discount(), 2)
    total_cost = round(concrete_cost + delivery_cost, 2)
    cost_per_m3 = round(total_cost / order_dto.amount, 2)

    # Add total cost to message
    msg += (f"\n<b>Сума:</b> {concrete_cost} + {delivery_cost} = <b>{total_cost} UAH</b> "
            f"<i>({cost_per_m3} UAH/м³)</i>\n")

    # Add conditional footnotes
    if order_dto.concrete.type_ in ["P1", "P2"]:
        msg += f"\n<em>*{texts.more_than_one_truck}</em>"
    elif order_dto.amount < 7:
        msg += f"\n<em>*{texts.less_than_7_m3}</em>"

    return msg
