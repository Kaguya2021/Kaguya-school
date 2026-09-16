from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.base import async_session
from database.requests import get_or_create_user
from keybaords.inline import get_main_menu_keyboard

router = Router()


@router.message(Command("start"))
@router.message(Command("menu"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

    text = (
        f"👋 Привет, **{user.first_name or 'ученик'}**!\n\n"
        "📚 **Школьный помощник** поможет тебе хранить расписание, "
        "управлять домашними заданиями и присылать вовремя уведомления.\n\n"
        "Выбери нужный раздел в меню ниже:"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "❓ **Справка по командам:**\n\n"
        "/start — Перезапустить бота / Главное меню\n"
        "/menu — Открыть главное меню\n"
        "/schedule — Посмотреть расписание\n"
        "/homework — Посмотреть ДЗ\n"
        "/settings — Настройки уведомлений и времени\n"
        "/cancel — Отменить текущий ввод"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "nav_main_menu")
async def nav_main_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        f"📚 **Главное меню**\n\n"
        "Выбери интересующий тебя раздел:"
    )
    await callback.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    await callback.answer()
