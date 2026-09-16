from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.base import async_session
from database.requests import (
    get_or_create_user,
    update_user_settings,
    update_user_timezone,
    update_lesson_time,
    get_user_lesson_times_dict
)
from services.parser import parse_time_string
from services.scheduler import sync_user_jobs
from keybaords.inline import (
    get_settings_menu_keyboard,
    get_time_picker_keyboard,
    get_timezone_keyboard,
    get_lesson_times_keyboard,
    get_back_keyboard
)

router = Router()


class SettingsState(StatesGroup):
    waiting_for_custom_time = State()
    waiting_for_custom_tz = State()
    waiting_for_lesson_time = State()


@router.message(Command("settings"))
@router.callback_query(F.data == "menu_settings")
@router.callback_query(F.data == "nav_menu_settings")
async def show_settings_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    async with async_session() as session:
        user = await get_or_create_user(session, event.from_user.id)

    text = (
        "⚙️ **Настройки бота**\n\n"
        f"🌍 Ваш часовой пояс: **{user.timezone}**\n\n"
        "Настройте удобное время автоматических уведомлений:"
    )

    kb = get_settings_menu_keyboard(user.settings)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="Markdown")


# --- Настройка времени уведомлений ---

@router.callback_query(F.data.startswith("set_time_"))
async def choose_notification_time(callback: CallbackQuery, state: FSMContext):
    target = callback.data.replace("set_time_", "")  # schedule, homework, tomorrow
    await state.update_data(time_target=target)

    title_map = {
        "schedule": "📅 Утреннее расписание",
        "homework": "📝 Вечернее ДЗ",
        "tomorrow": "🌙 Завтрашние уроки"
    }

    text = f"⏰Выберите время отправки ({title_map.get(target, '')}):"
    await callback.message.edit_text(text, reply_markup=get_time_picker_keyboard(f"tp_{target}"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("tp_"))
async def process_time_picker(callback: CallbackQuery, state: FSMContext, bot):
    parts = callback.data.split("_")
    target = parts[1]  # schedule, homework, tomorrow
    val = parts[2]     # 07:00, off, custom

    if val == "custom":
        await state.set_state(SettingsState.waiting_for_custom_time)
        await state.update_data(time_target=target)
        await callback.message.edit_text("⌨️ Введите время формата `HH:MM` (напр. `07:30` или `19:00`):", parse_mode="Markdown")
        await callback.answer()
        return

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)

        kwargs = {}
        if val == "off":
            kwargs[f"{target}_notifications"] = False
        else:
            kwargs[f"{target}_notifications"] = True
            kwargs[f"{target}_notification_time"] = val

        await update_user_settings(session, user.id, **kwargs)
        # Получаем обновленного пользователя
        user = await get_or_create_user(session, callback.from_user.id)
        await sync_user_jobs(bot, user)

    await state.clear()
    await callback.message.edit_text("✅ Настройки времени сохранены!", reply_markup=get_settings_menu_keyboard(user.settings), parse_mode="Markdown")
    await callback.answer()


@router.message(SettingsState.waiting_for_custom_time)
async def process_custom_time_input(message: Message, state: FSMContext, bot):
    t_str = parse_time_string(message.text)
    if not t_str:
        await message.answer("❌ Неверное время. Попробуй формат `07:30` или `19:00`")
        return

    data = await state.get_data()
    target = data.get("time_target", "schedule")

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        kwargs = {
            f"{target}_notifications": True,
            f"{target}_notification_time": t_str
        }
        await update_user_settings(session, user.id, **kwargs)
        user = await get_or_create_user(session, message.from_user.id)
        await sync_user_jobs(bot, user)

    await state.clear()
    await message.answer(f"✅ Время успешно установлено: **{t_str}**", reply_markup=get_settings_menu_keyboard(user.settings), parse_mode="Markdown")


# --- Настройка Часового Пояса ---

@router.callback_query(F.data == "set_timezone")
async def choose_timezone(callback: CallbackQuery):
    await callback.message.edit_text("🌍 Выберите ваш часовой пояс:", reply_markup=get_timezone_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("tz_"))
async def process_tz_choice(callback: CallbackQuery, state: FSMContext, bot):
    val = callback.data.replace("tz_", "")

    if val == "custom":
        await state.set_state(SettingsState.waiting_for_custom_tz)
        await callback.message.edit_text("⌨️ Введите часовой пояс (например: `UTC+6`, `UTC+3` или `Europe/Moscow`):", parse_mode="Markdown")
        await callback.answer()
        return

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        await update_user_timezone(session, user.id, val)
        user = await get_or_create_user(session, callback.from_user.id)
        await sync_user_jobs(bot, user)

    await callback.message.edit_text(f"✅ Часовой пояс сохранен: **{val}**", reply_markup=get_settings_menu_keyboard(user.settings), parse_mode="Markdown")
    await callback.answer()


@router.message(SettingsState.waiting_for_custom_tz)
async def process_custom_tz_input(message: Message, state: FSMContext, bot):
    tz_val = message.text.strip()
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await update_user_timezone(session, user.id, tz_val)
        user = await get_or_create_user(session, message.from_user.id)
        await sync_user_jobs(bot, user)

    await state.clear()
    await message.answer(f"✅ Часовой пояс установлен: **{tz_val}**", reply_markup=get_settings_menu_keyboard(user.settings), parse_mode="Markdown")


# --- Настройка Времени Уроков ---

@router.callback_query(F.data == "set_lesson_times")
async def show_lesson_times_menu(callback: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        times_dict = await get_user_lesson_times_dict(session, user.id)

    await callback.message.edit_text(
        "⚙️ **Настройка начала звонков уроков:**\n\nНажмите на урок для изменения времени:",
        reply_markup=get_lesson_times_keyboard(times_dict),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_ltime_"))
async def edit_lesson_time_start(callback: CallbackQuery, state: FSMContext):
    num = int(callback.data.replace("edit_ltime_", ""))
    await state.set_state(SettingsState.waiting_for_lesson_time)
    await state.update_data(lesson_num=num)

    await callback.message.edit_text(
        f"⌨️ Введите время начала **{num} урока** (формат `08:00`):",
        reply_markup=get_back_keyboard("menu_settings"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(SettingsState.waiting_for_lesson_time)
async def process_lesson_time_input(message: Message, state: FSMContext):
    t_str = parse_time_string(message.text)
    if not t_str:
        await message.answer("❌ Неверный формат времени. Введите в формате `08:30`")
        return

    data = await state.get_data()
    num = data.get("lesson_num")

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await update_lesson_time(session, user.id, num, t_str)
        times_dict = await get_user_lesson_times_dict(session, user.id)

    await state.clear()
    await message.answer(
        f"✅ Время **{num} урока** установлено на **{t_str}**",
        reply_markup=get_lesson_times_keyboard(times_dict),
        parse_mode="Markdown"
    )
