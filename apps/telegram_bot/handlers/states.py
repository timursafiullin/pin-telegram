from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    awaiting_invite_code = State()
    awaiting_timezone = State()
