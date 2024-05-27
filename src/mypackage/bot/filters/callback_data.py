from typing import Union

from telebot.types import CallbackQuery
from telebot.custom_filters import AdvancedCustomFilter


# Convenient way to filter callback_data instead of using lambda functions
class CallbackDataFilter(AdvancedCustomFilter):
    key = 'cb_data'

    # argument naming is kept from the base class to avoid possible errors if passed as kwargs
    # message is an update, text is a value passed to the filter on handler registration
    def check(self, message: CallbackQuery, text: Union[str, list]):
        if isinstance(text, list):
            # exact match with any of the texts
            return message.data in text
        elif isinstance(text, str):
            # exact match with the text
            return message.data == text
        else:
            # unexpected type
            return False


class CallbackDataPrefixFilter(AdvancedCustomFilter):
    key = 'prefix'

    # argument naming is kept from the base class to avoid possible errors if passed as kwargs
    # message is an update, text is a value passed to the filter on handler registration
    def check(self, message: CallbackQuery, text: Union[str, list]):
        if isinstance(text, list):
            # exact match with any of the texts
            return message.data in text
        elif isinstance(text, str):
            # exact match with the text
            return message.data.startswith(text) and text in message.data
        else:
            # unexpected type
            return False


class CallbackDataPaginationFilter(AdvancedCustomFilter):
    key = 'pagination_prefix'

    def check(self, update: CallbackQuery, value: str):
        # check if callback_data starts with the value and contains a '#' sign right after it
        # useful for pagination, e.g. callback_data='paging_collection#number_of_the_page'
        return update.data.startswith(f'{value}#')

# id_123124124
# id_page#1
