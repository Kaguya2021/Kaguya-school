import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.base import init_db
from services.scheduler import scheduler, reload_all_schedulers
from handlers import common, schedule, homework, settings, admin


# Ответ для проверки статуса от Render
async def handle_healthcheck(request):
    return web.Response(text="Bot is running!")


# Запуск лёгкого веб-сервера
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_healthcheck)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render сам передаёт свободный порт в переменную окружения PORT
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    logging.info("Инициализация БД...")
    await init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение роутеров
    dp.include_router(common.router)
    dp.include_router(schedule.router)
    dp.include_router(homework.router)
    dp.include_router(settings.router)
    dp.include_router(admin.router)

    # Запуск планировщика
    scheduler.start()
    await reload_all_schedulers(bot)

    # Запускаем фоновый веб-сервер для Render Web Service
    await start_web_server()

    logging.info("Бот успешно запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

