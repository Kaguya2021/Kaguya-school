import logging
from datetime import datetime, timedelta
import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database.base import async_session
from database.requests import (
    get_all_users,
    get_user_schedule_for_day,
    get_user_full_schedule,
    get_user_homework_by_date,
    get_user_lesson_times_dict
)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def parse_utc_offset(tz_str: str) -> pytz.BaseTzInfo:
    try:
        if tz_str.startswith("UTC"):
            offset_str = tz_str.replace("UTC", "")
            if not offset_str:
                return pytz.UTC
            hours = int(offset_str)
            return pytz.FixedOffset(hours * 60)
        return pytz.timezone(tz_str)
    except Exception:
        return pytz.FixedOffset(6 * 60)


async def send_lesson_notification(bot: Bot, telegram_id: int, subject: str, lesson_num: int):
    """Уведомление о начале конкретного урока."""
    msg = f"🔔 **Урок начался!**\n\n{lesson_num}️⃣ **{subject}**"
    try:
        await bot.send_message(telegram_id, msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка отправки звонка {telegram_id}: {e}")


async def send_morning_schedule(bot: Bot, telegram_id: int, user_db_id: int):
    async with async_session() as session:
        from database.requests import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, telegram_id)
        user_tz = parse_utc_offset(user.timezone) if user else pytz.FixedOffset(6 * 60)

        now_user_time = datetime.now(user_tz)
        today_weekday = now_user_time.weekday()

        schedule_items = await get_user_schedule_for_day(session, user_db_id, today_weekday)
        if not schedule_items:
            return

        times_dict = await get_user_lesson_times_dict(session, user_db_id)
        msg = "🌅 **Утреннее расписание на сегодня:**\n\n"
        for item in schedule_items:
            l_time = times_dict.get(item.lesson_number, "")
            time_str = f" (`{l_time}`)" if l_time else ""
            msg += f"{item.lesson_number}️⃣{time_str} — {item.subject}\n"

        try:
            await bot.send_message(telegram_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки утреннего расписания {telegram_id}: {e}")


async def send_evening_homework(bot: Bot, telegram_id: int, user_db_id: int):
    async with async_session() as session:
        from database.requests import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, telegram_id)
        user_tz = parse_utc_offset(user.timezone) if user else pytz.FixedOffset(6 * 60)

        # Отправляем ДЗ, подготовленное на завтра!
        target_date = datetime.now(user_tz).date() + timedelta(days=1)
        hw_items = await get_user_homework_by_date(session, user_db_id, target_date)

        if not hw_items:
            return

        msg = f"📝 **Домашнее задание на завтра ({target_date.strftime('%d.%m')}):**\n\n"
        for hw in hw_items:
            status = "✅" if hw.completed else "📌"
            msg += f"{status} **{hw.subject}**\n└ {hw.task_text}\n\n"

        try:
            await bot.send_message(telegram_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки ДЗ {telegram_id}: {e}")


async def sync_user_jobs(bot: Bot, user):
    """Динамическая регистрация задач в планировщике."""
    # Очищаем все старые задачи пользователя
    for job in scheduler.get_jobs():
        if job.id.startswith(f"user_{user.telegram_id}_"):
            scheduler.remove_job(job.id)

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

    # 2. Вечернее ДЗ
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

    # 3. Звонки на уроки по расписанию
    async with async_session() as session:
        full_schedule = await get_user_full_schedule(session, user.id)
        times_dict = await get_user_lesson_times_dict(session, user.id)

        for item in full_schedule:
            start_time_str = times_dict.get(item.lesson_number)
            if not start_time_str:
                continue

            try:
                h, m = map(int, start_time_str.split(":"))
                # day_of_week в cron: 0 - Mon, 6 - Sun (или mon-sun)
                job_id = f"user_{user.telegram_id}_lesson_{item.weekday}_{item.lesson_number}"
                scheduler.add_job(
                    send_lesson_notification,
                    CronTrigger(day_of_week=item.weekday, hour=h, minute=m, timezone=tz),
                    id=job_id,
                    kwargs={
                        "bot": bot,
                        "telegram_id": user.telegram_id,
                        "subject": item.subject,
                        "lesson_num": item.lesson_number
                    },
                    replace_existing=True
                )
            except ValueError:
                pass


async def reload_all_schedulers(bot: Bot):
    async with async_session() as session:
        users = await get_all_users(session)
        for user in users:
            await sync_user_jobs(bot, user)
    logger.info(f"Синхронизированы задачи для {len(users)} пользователей.")

