import httpx
from aiogram import Router
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from apps.telegram_bot.handlers.states import Registration
from apps.telegram_bot.keyboards.registration import get_timezone_keyboard

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

    await state.set_state(Registration.awaiting_invite_code)
    await message.answer("Please enter the invite code for registration.")
    

@router.message(StateFilter(Registration.awaiting_invite_code))
async def handle_invite(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    payload = {"telegram_id": telegram_id, "invite_code": message.text.strip()}

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/register/invite", json=payload)

    if response.status_code >= 400:
        await message.answer("The invite code is invalid. Please try again.")
        return

    await state.set_state(Registration.awaiting_timezone)
    await message.answer(
        text="Invite accepted. Now, share your location to set your time zone. This is necessary for schedules and reminders to work correctly.",
        reply_markup=get_timezone_keyboard()
    )


@router.message(StateFilter(Registration.awaiting_timezone))
async def handle_timezone(message: Message, state: FSMContext, ):
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
