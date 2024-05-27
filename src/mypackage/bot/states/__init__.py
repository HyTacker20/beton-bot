from telebot.handler_backends import StatesGroup, State


class UnregisteredStates(StatesGroup):
    started = State()
