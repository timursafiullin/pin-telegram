import httpx
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from apps.telegram_bot.handlers.states import Registration
from apps.telegram_bot.keyboards.registration import (
    get_timezone_keyboard,
    get_registration_type_keyboard,
    back_to_choose_reg_type_button,
    request_confirmation,
    share_geolocation_reply,
)

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id) if message.from_user else "unknown"
    payload = {
        "telegram_id": telegram_id,
        "name": message.from_user.full_name if message.from_user else None,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/register/start", json=payload)
        response.raise_for_status()
        data = response.json()

    status = data["status"]
    if status == "registered":
        await state.clear()
        await message.answer("Welcome back! You are already registered.")
        return

    await state.set_state(Registration.awaiting_registration_type)
    await message.answer(
        text="Welcome to PIN in Telegram! To continue, please select an option.",
        reply_markup=get_registration_type_keyboard()
    )


@router.callback_query(F.data == "back_to_choose_reg_type")
async def handle_choose_reg_type_query(callback: CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id) if callback.from_user else "unknown"
    payload = {
        "telegram_id": telegram_id,
        "name": callback.from_user.full_name if callback.from_user else None,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/register/start", json=payload)
        response.raise_for_status()
        data = response.json()

    status = data["status"]
    if status == "registered":
        await state.clear()
        await callback.message.edit_text("Welcome back! You are already registered.")
        return

    await state.set_state(Registration.awaiting_registration_type)
    await callback.message.edit_text(
        text="Welcome to PIN in Telegram! To continue, please select an option.",
        reply_markup=get_registration_type_keyboard()
    )


@router.message(StateFilter(Registration.awaiting_request_access))
@router.message(StateFilter(Registration.awaiting_registration_type))
async def handle_answer(message: Message, state: FSMContext):
    await message.delete()


@router.callback_query(F.data == "request_access")
@router.callback_query(F.data == "have_invite_code")
async def choose_registration_type(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if (callback.data == "have_invite_code"):
        await state.set_state(Registration.awaiting_invite_code)
        await callback.message.edit_text(
            text="Please enter your invite code for registration.",
            reply_markup=back_to_choose_reg_type_button()
        )
    else:
        await state.set_state(Registration.awaiting_request_access)
        await callback.message.edit_text(
            text="Confirm that you want to request access to the bot.",
            reply_markup=request_confirmation()
        )


@router.callback_query(F.data == "confirm_request_access")
async def confirm_request_access(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Your access request has been sent. You will receive a message as soon as there is a response.",
    )


@router.message(StateFilter(Registration.awaiting_invite_code))
async def handle_invite(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    payload = {"telegram_id": telegram_id, "invite_code": message.text.strip()}

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/register/invite", json=payload)

    if response.status_code >= 400:
        await message.answer(
            text="The invite code is invalid. Please try again.",
            reply_markup=back_to_choose_reg_type_button()
        )
        return

    await state.set_state(Registration.awaiting_timezone)
    await message.answer(
        text="Invite accepted. Now, share your location to set your time zone. This is necessary for schedules and reminders to work correctly.",
        reply_markup=get_timezone_keyboard()
    )


@router.message(StateFilter(Registration.awaiting_timezone))
async def handle_timezone(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    payload = {"telegram_id": telegram_id, "timezone": message.text.strip()}

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/register/timezone", json=payload)

    if response.status_code >= 400:
        await message.answer(
            text="Something went wrong. Please, share your location to set your time zone. This is necessary for schedules and reminders to work correctly.",
            reply_markup=get_timezone_keyboard()
        )
        return

    await state.clear()
    await message.answer("Registration completed. You can now send regular requests.")


@router.callback_query(F.data == "choose_own_timezone")
async def handle_choose_own_timezone(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        text="Choose one on keyboard.",
        reply_markup=share_geolocation_reply()
    )


@router.message(F.text == "🔙 Go back")
@router.callback_query(F.data == "back_to_choose_timezone")
async def handle_back_to_timezone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Please, share your location to set your time zone. This is necessary for schedules and reminders to work correctly.",
        reply_markup=get_timezone_keyboard()
    )