from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

start_router = Router()

@start_router.message(CommandStart())
async def handle_start(message: Message):
    user_id = message.from_user.id if message.from_user else "unknown"
    await message.answer(text=f"Your user_id: {user_id}")
