from aiogram import types

from ..main import dp

@dp.message_handler(commands=['start'], state='*')
async def start_bot(message: types.Message):
    userid = message.from_user_id
    await message.answer(text=userid)