from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime

from database.base import async_session
from database.requests import (
    get_or_create_user,
    get_user_schedule_for_day,
    get_user_full_schedule,
    save_user_schedule,
    delete_user_schedule,
    get_user_lesson_times_dict
)
from services.parser import parse_schedule_text
from keybaords.inline import (
    get_schedule_view_keyboard,
    get_schedule_preview_keyboard,
    get_back_keyboard,
    get_main_menu_keyboard
)

router = Router()

WEEKDAY_NAMES = [
    "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"
]


class ScheduleState(StatesGroup):
    waiting_for_text = State()
    preview = State()


@router.message(Command("schedule"))
@router.callback_query(F.data == "menu_schedule")
async def show_schedule_menu(event: Message | CallbackQuery):
    telegram_id = event.from_user.id
    async with async_session() as session:
        user = await get_or_create_user(session, telegram_id)
        today_wd = datetime.now().weekday()
        today_items = await get_user_schedule_for_day(session, user.id, today_wd)
        times_dict = await get_user_lesson_times_dict(session, user.id)

    msg_text = f"📅 **Расписание на сегодня ({WEEKDAY_NAMES[today_wd]}):**\n\n"
    if today_items:
        for item in today_items:
            l_time = times_dict.get(item.lesson_number, "")
            time_str = f" `{l_time}`" if l_time else ""
            msg_text += f"{item.lesson_number}️⃣{time_str} — {item.subject}\n"
    else:
        msg_text += "На сегодня уроков нет или расписание ещё не заполнено."

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg_text, reply_markup=get_schedule_view_keyboard(), parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(msg_text, reply_markup=get_schedule_view_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "sch_full_week")
async def show_full_week_schedule(callback: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        items = await get_user_full_schedule(session, user.id)
        times_dict = await get_user_lesson_times_dict(session, user.id)

    if not items:
        await callback.message.edit_text(
            "📅 Ваше расписание на неделю пусто.",
            reply_markup=get_back_keyboard("schedule"),
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    grouped = {}
    for item in items:
        grouped.setdefault(item.weekday, []).append(item)

    msg_text = "📆 **Расписание на всю неделю:**\n\n"
    for wd in range(7):
        if wd in grouped:
            msg_text += f"**{WEEKDAY_NAMES[wd]}:**\n"
            for item in grouped[wd]:
                l_time = times_dict.get(item.lesson_number, "")
                time_str = f" `{l_time}`" if l_time else ""
                msg_text += f"  {item.lesson_number}️⃣{time_str} {item.subject}\n"
            msg_text += "\n"

    await callback.message.edit_text(msg_text, reply_markup=get_back_keyboard("schedule"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "create_schedule")
async def start_create_schedule(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ScheduleState.waiting_for_text)
    text = (
        "➕ **Создание расписания**\n\n"
        "Отправь своё расписание обычным текстом. Не обязательно соблюдать специальный формат — я постараюсь его распознать.\n\n"
        "**Пример:**\n"
        "Понедельник:\n"
        "1 Математика\n"
        "2 Русский язык\n"
        "3 Информатика\n"
        "4 Физика\n\n"
        "Вторник:\n"
        "Пн: История, Английский, Математика"
    )
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("schedule"), parse_mode="Markdown")
    await callback.answer()


@router.message(ScheduleState.waiting_for_text)
async def process_schedule_text_input(message: Message, state: FSMContext):
    parsed = parse_schedule_text(message.text)

    if not parsed:
        await message.answer(
            "❌ Не удалось распознать расписание.\n\n"
            "Попробуй написать, например:\n"
            "Понедельник:\n"
            "1. Математика\n"
            "2. Русский\n"
            "3. Информатика",
            reply_markup=get_back_keyboard("schedule")
        )
        return

    await state.update_data(parsed_schedule=parsed)
    await state.set_state(ScheduleState.preview)

    preview_text = "📅 **Проверь распознанное расписание:**\n\n"
    for wd in sorted(parsed.keys()):
        preview_text += f"**{WEEKDAY_NAMES[wd]}:**\n"
        for num, subj in parsed[wd]:
            preview_text += f"  {num}️⃣ {subj}\n"
        preview_text += "\n"

    await message.answer(preview_text, reply_markup=get_schedule_preview_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "save_schedule", ScheduleState.preview)
async def save_schedule_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    parsed_schedule = data.get("parsed_schedule")

    if not parsed_schedule:
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        await save_user_schedule(session, user.id, parsed_schedule)

    await state.clear()
    await callback.message.edit_text(
        "✅ **Расписание успешно сохранено!**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "sch_delete_confirm")
async def delete_schedule_handler(callback: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        await delete_user_schedule(session, user.id)

    await callback.message.edit_text(
        "🗑 **Ваше расписание удалено.**",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "nav_schedule")
async def nav_schedule_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_schedule_menu(callback)
