import asyncio

from apps.telegram_bot.config import settings

from apps.telegram_bot.create_bot import bot, dp
from apps.telegram_bot.create_bot import start_router

# Start Bot
async def main():
    if bot.token == settings.TELEGRAM_BOT_API_KEY:
        print("Starting Personal Intelligence Node – Telegram Bot...")
    dp.include_router(start_router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())