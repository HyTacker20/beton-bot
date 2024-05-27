from typing import List

from telebot import TeleBot
from telebot.custom_filters import StateFilter


from .callback_data import CallbackDataFilter, CallbackDataPrefixFilter, CallbackDataPaginationFilter
from .text import TextEqualsFilter
from .roles import IsOwnerFilter, IsAdminFilter


def add_custom_filters(bot: TeleBot, owner_tg_id: int, admins: List[int]):
    # TODO: add any custom filters here
    bot.add_custom_filter(StateFilter(bot))
    bot.add_custom_filter(TextEqualsFilter())
    bot.add_custom_filter(CallbackDataFilter())
    bot.add_custom_filter(CallbackDataPrefixFilter())
    bot.add_custom_filter(CallbackDataPaginationFilter())
    bot.add_custom_filter(IsOwnerFilter(owner_tg_id))
    bot.add_custom_filter(IsAdminFilter(admins))
