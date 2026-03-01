from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    awaiting_registration_type = State()
    awaiting_request_access = State()
    awaiting_invite_code = State()
    awaiting_timezone = State()
