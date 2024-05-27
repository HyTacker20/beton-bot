from math import floor

from telebot.util import content_type_media, content_type_service

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
