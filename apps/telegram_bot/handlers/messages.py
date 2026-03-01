import httpx
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from apps.telegram_bot.handlers.states import Registration

router = Router()


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
    await message.answer("Invite accepted. Please provide your timezone in IANA format, for example, Europe/Moscow.")


@router.message(StateFilter(Registration.awaiting_timezone))
async def handle_timezone(message: Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    payload = {"telegram_id": telegram_id, "timezone": message.text.strip()}

    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/register/timezone", json=payload)

    if response.status_code >= 400:
        await message.answer("Unable to recognize the timezone. Example: Europe/Moscow.")
        return

    await state.clear()
    await message.answer("Registration completed. You can now send regular requests.")


@router.message()
async def handle_message(message: Message):
    data = {"user_id": str(message.from_user.id), "text": message.text}
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/message", json=data)

    if response.status_code == 403:
        await message.answer("Please complete registration through /start first.")
        return

    response.raise_for_status()
    reply = response.json()["reply"]
    await message.answer(reply)
