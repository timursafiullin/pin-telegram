import httpx
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from apps.telegram_bot.handlers.states import Registration

start_router = Router()


@start_router.message(CommandStart())
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
