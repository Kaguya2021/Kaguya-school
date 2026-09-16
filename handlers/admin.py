import asyncio
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import config
from database.base import async_session
from database.requests import get_admin_stats, get_all_users
from keybaords.inline import get_admin_keyboard, get_back_keyboard

router = Router()
logger = logging.getLogger(__name__)


class AdminState(StatesGroup):
    waiting_for_broadcast = State()


# Фильтр доступа администратора
def is_admin(telegram_id: int) -> bool:
    return telegram_id == config.ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return  # Игнорируем обычных пользователей

    async with async_session() as session:
        stats = await get_admin_stats(session)

    text = (
        "🔐 **Панель Администратора**\n\n"
        f"👥 Пользователей: **{stats['users']}**\n"
        f"📅 Активных расписаний: **{stats['schedules']}**\n"
        f"📝 Активных ДЗ: **{stats['homeworks']}**"
    )
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "admin_stats")
async def refresh_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    async with async_session() as session:
        stats = await get_admin_stats(session)

    text = (
        "📊 **Актуальная статистика системы:**\n\n"
        f"👥 Пользователей: **{stats['users']}**\n"
        f"📅 Записей расписания: **{stats['schedules']}**\n"
        f"📝 Записей ДЗ: **{stats['homeworks']}**"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Доступ запрещен.", show_alert=True)
        return

    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.edit_text(
        "📢 **Рассылка сообщений**\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям бота:",
        reply_markup=get_back_keyboard("main_menu"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    async with async_session() as session:
        users = await get_all_users(session)

    success_count = 0
    fail_count = 0

    await message.answer(f"⏳ Запуск рассылки на {len(users)} пользователей...")

    for user in users:
        try:
            await bot.send_message(user.telegram_id, message.text)
            success_count += 1
            await asyncio.sleep(0.05)  # Защита от лимитов Telegram API
        except Exception as e:
            logger.warning(f"Ошибка рассылки пользователю {user.telegram_id}: {e}")
            fail_count += 1

    await message.answer(
        f"✅ **Рассылка завершена!**\n\n"
        f"Успешно: **{success_count}**\n"
        f"Ошибок: **{fail_count}**",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
