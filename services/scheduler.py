import logging
from datetime import datetime, timedelta, time as dt_time
import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.base import async_session
from database.requests import (
    get_all_users,
    get_user_schedule_for_day,
    get_user_homework_by_date,
    get_user_lesson_times_dict
)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def parse_utc_offset(tz_str: str) -> pytz.BaseTzInfo:
    """Парсит строки вида 'UTC+6', 'UTC-3' в pytz.timezone."""
    try:
        if tz_str.startswith("UTC"):
            offset_str = tz_str.replace("UTC", "")
            if not offset_str:
                return pytz.UTC
            hours = int(offset_str)
            return pytz.FixedOffset(hours * 60)
        return pytz.timezone(tz_str)
    except Exception:
        return pytz.FixedOffset(6 * 60)  # По умолчанию UTC+6


async def send_morning_schedule(bot: Bot, telegram_id: int, user_db_id: int):
    async with async_session() as session:
        user_tz = pytz.FixedOffset(6 * 60)
        # Получаем локальный день недели пользователя
        from database.requests import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, telegram_id)
        if user:
            user_tz = parse_utc_offset(user.timezone)

        now_user_time = datetime.now(user_tz)
        today_weekday = now_user_time.weekday()

        schedule_items = await get_user_schedule_for_day(session, user_db_id, today_weekday)
        if not schedule_items:
            return  # Нет расписания на сегодня — ничего не отправляем

        times_dict = await get_user_lesson_times_dict(session, user_db_id)

        msg = "🌅 **Утреннее расписание на сегодня:**\n\n"
        for item in schedule_items:
            l_time = times_dict.get(item.lesson_number, "")
            time_str = f" ({l_time})" if l_time else ""
            msg += f"{item.lesson_number}️⃣{time_str} — {item.subject}\n"

        try:
            await bot.send_message(telegram_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить утреннее расписание {telegram_id}: {e}")


async def send_evening_homework(bot: Bot, telegram_id: int, user_db_id: int):
    async with async_session() as session:
        from database.requests import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, telegram_id)
        user_tz = parse_utc_offset(user.timezone) if user else pytz.FixedOffset(6 * 60)

        today_date = datetime.now(user_tz).date()
        hw_items = await get_user_homework_by_date(session, user_db_id, today_date)

        if not hw_items:
            return

        msg = "📝 **Домашнее задание на сегодня:**\n\n"
        for hw in hw_items:
            status = "✅" if hw.completed else "📌"
            msg += f"{status} **{hw.subject}**\n└ {hw.task_text}\n\n"

        try:
            await bot.send_message(telegram_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить ДЗ {telegram_id}: {e}")


async def send_tomorrow_schedule(bot: Bot, telegram_id: int, user_db_id: int):
    async with async_session() as session:
        from database.requests import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, telegram_id)
        user_tz = parse_utc_offset(user.timezone) if user else pytz.FixedOffset(6 * 60)

        tomorrow_weekday = (datetime.now(user_tz).date() + timedelta(days=1)).weekday()
        schedule_items = await get_user_schedule_for_day(session, user_db_id, tomorrow_weekday)

        if not schedule_items:
            return

        times_dict = await get_user_lesson_times_dict(session, user_db_id)
        msg = "🌙 **Завтра у тебя по расписанию:**\n\n"
        for item in schedule_items:
            l_time = times_dict.get(item.lesson_number, "")
            time_str = f" ({l_time})" if l_time else ""
            msg += f"{item.lesson_number}️⃣{time_str} — {item.subject}\n"

        try:
            await bot.send_message(telegram_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить расписание на завтра {telegram_id}: {e}")


async def sync_user_jobs(bot: Bot, user):
    """Синхронизирует APScheduler задачи конкретного пользователя на основе настроек."""
    # Удаляем прежние задачи пользователя
    for job_type in ["sch", "hw", "tom"]:
        job_id = f"user_{user.telegram_id}_{job_type}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)

    st = user.settings
    if not st:
        return

    tz = parse_utc_offset(user.timezone)

    # 1. Утреннее расписание
    if st.schedule_notifications and st.schedule_notification_time:
        try:
            h, m = map(int, st.schedule_notification_time.split(":"))
            scheduler.add_job(
                send_morning_schedule,
                CronTrigger(hour=h, minute=m, timezone=tz),
                id=f"user_{user.telegram_id}_sch",
                kwargs={"bot": bot, "telegram_id": user.telegram_id, "user_db_id": user.id},
                replace_existing=True
            )
        except ValueError:
            pass

    # 2. Уведомление о ДЗ
    if st.homework_notifications and st.homework_notification_time:
        try:
            h, m = map(int, st.homework_notification_time.split(":"))
            scheduler.add_job(
                send_evening_homework,
                CronTrigger(hour=h, minute=m, timezone=tz),
                id=f"user_{user.telegram_id}_hw",
                kwargs={"bot": bot, "telegram_id": user.telegram_id, "user_db_id": user.id},
                replace_existing=True
            )
        except ValueError:
            pass

    # 3. Напоминание о завтрашних уроках
    if st.tomorrow_notifications and st.tomorrow_notification_time:
        try:
            h, m = map(int, st.tomorrow_notification_time.split(":"))
            scheduler.add_job(
                send_tomorrow_schedule,
                CronTrigger(hour=h, minute=m, timezone=tz),
                id=f"user_{user.telegram_id}_tom",
                kwargs={"bot": bot, "telegram_id": user.telegram_id, "user_db_id": user.id},
                replace_existing=True
            )
        except ValueError:
            pass


async def reload_all_schedulers(bot: Bot):
    """Перезагружает все пользовательские задачи из БД при запуске."""
    async with async_session() as session:
        users = await get_all_users(session)
        for user in users:
            await sync_user_jobs(bot, user)
    logger.info(f"Загружены планировщики для {len(users)} пользователей.")
