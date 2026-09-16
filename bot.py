import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.base import init_db
from services.scheduler import scheduler, reload_all_schedulers
from handlers import common, schedule, homework, settings, admin


async def main():
    logging.basicConfig(
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.info("Инициализация приложения...")

    # Инициализируем БД
    await init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(common.router)
    dp.include_router(schedule.router)
    dp.include_router(homework.router)
    dp.include_router(settings.router)
    dp.include_router(admin.router)

    # Запуск планировщика
    scheduler.start()
    await reload_all_schedulers(bot)

    logging.info("Бот успешно запущен!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
