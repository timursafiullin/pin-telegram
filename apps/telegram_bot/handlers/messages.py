import httpx
from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


router = Router()


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