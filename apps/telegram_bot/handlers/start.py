from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

start_router = Router()

@start_router.message(CommandStart())
async def start_router(message: Message):
    userid = message.from_user_id
    await message.answer(text=userid)