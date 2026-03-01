import httpx
from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message()
async def handle_message(message: Message):
    data = {"user_id": str(message.from_user.id), "text": message.text}
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/bot/message", json=data)
        response.raise_for_status()
        reply = response.json()["reply"]
    await message.answer(reply)
