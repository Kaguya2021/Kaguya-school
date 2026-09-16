import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.base import init_db
from services.scheduler import scheduler, reload_all_schedulers
from handlers import common, schedule, homework, settings, admin


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    
    logging.info("Инициализация приложения...")

