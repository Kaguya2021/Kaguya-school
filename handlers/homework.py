from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, date, timedelta

from database.base import async_session
from database.requests import (
    get_or_create_user,
    add_user_homeworks,
    get_user_homework_by_date,
    get_all_user_active_homeworks,
    toggle_homework_status,
    delete_user_completed_homeworks
)
from services.parser import parse_homework_text, parse_date_string
from keybaords.inline import (
    get_homework_menu_keyboard,
    get_homework_date_picker_keyboard,
    get_homework_preview_keyboard,
    get_back_keyboard,
    get_main_menu_keyboard
)

router = Router()


class HomeworkState(StatesGroup):
    waiting_for_text = State()
    waiting_for_date = State()
    waiting_for_custom_date = State()
    preview = State()


@router.message(Command("homework"))
@router.callback_query(F.data == "menu_homework")
@router.callback_query(F.data == "nav_menu_homework")
async def show_homework_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    telegram_id = event.from_user.id
    async with async_session() as session:
        user = await get_or_create_user(session, telegram_id)
        active_hws = await get_all_user_active_homeworks(session, user.id)

    msg_text = f"📝 **Раздел Домашнего Задания**\n\nАктивных заданий: **{len(active_hws)}**"

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(msg_text, reply_markup=get_homework_menu_keyboard(), parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(msg_text, reply_markup=get_homework_menu_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "add_homework")
async def start_add_homework(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HomeworkState.waiting_for_text)
    text = (
        "➕ **Добавление ДЗ**\n\n"
        "Отправь задание текстом в формате:\n"
        "`Предмет - Задание`\n\n"
        "**Пример нескольких заданий:**\n"
        "Математика - стр 45 №12-15\n"
        "Русский язык - упражнение 78\n"
        "Информатика - сделать презентацию"
    )
    await callback.message.edit_text(text, reply_markup=get_back_keyboard("menu_homework"), parse_mode="Markdown")
    await callback.answer()


@router.message(HomeworkState.waiting_for_text)
async def process_hw_text(message: Message, state: FSMContext):
    parsed = parse_homework_text(message.text)
    if not parsed:
        await message.answer("❌ Не удалось распознать формат ДЗ. Попробуй: `Предмет - Задание`")
        return

    await state.update_data(parsed_hw=parsed)
    await state.set_state(HomeworkState.waiting_for_date)

    await message.answer(
        f"📝 Найдено **{len(parsed)}** заданий.\n\nВыберите дату выполнения:",
        reply_markup=get_homework_date_picker_keyboard(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("hw_date_"), HomeworkState.waiting_for_date)
async def process_hw_date_choice(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.replace("hw_date_", "")
    today = date.today()

    if choice == "today":
        selected_date = today
    elif choice == "tomorrow":
        selected_date = today + timedelta(days=1)
    elif choice == "custom":
        await state.set_state(HomeworkState.waiting_for_custom_date)
        await callback.message.edit_text(
            "⌨️ Введите дату выполнения (например: `сегодня`, `завтра`, `25.09`):",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    else:
        selected_date = today

    await _show_hw_preview(callback.message, state, selected_date, is_callback=True)
    await callback.answer()


@router.message(HomeworkState.waiting_for_custom_date)
async def process_hw_custom_date(message: Message, state: FSMContext):
    dt = parse_date_string(message.text)
    if not dt:
        await message.answer("❌ Неверный формат даты. Введите, например: `25.09` или `завтра`")
        return
    await _show_hw_preview(message, state, dt, is_callback=False)


async def _show_hw_preview(target_obj, state: FSMContext, due_date: date, is_callback: bool):
    data = await state.get_data()
    parsed_hw = data.get("parsed_hw", [])

    for item in parsed_hw:
        item["due_date"] = due_date

    await state.update_data(parsed_hw=parsed_hw)
    await state.set_state(HomeworkState.preview)

    text = f"📝 **Проверь домашнее задание на {due_date.strftime('%d.%m.%Y')}:**\n\n"
    for idx, item in enumerate(parsed_hw, 1):
        text += f"{idx}. **{item['subject']}**\n   {item['task_text']}\n\n"

    if is_callback:
        await target_obj.edit_text(text, reply_markup=get_homework_preview_keyboard(), parse_mode="Markdown")
    else:
        await target_obj.answer(text, reply_markup=get_homework_preview_keyboard(), parse_mode="Markdown")


@router.callback_query(F.data == "save_homework", HomeworkState.preview)
async def save_homework_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    parsed_hw = data.get("parsed_hw", [])

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        await add_user_homeworks(session, user.id, parsed_hw)

    await state.clear()
    await callback.message.edit_text(
        "✅ **Домашнее задание успешно сохранено!**",
        reply_markup=get_homework_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "hw_today")
async def show_hw_today(callback: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        hws = await get_user_homework_by_date(session, user.id, date.today())

    if not hws:
        msg_text = "📋 **На сегодня заданий нет!**"
    else:
        msg_text = f"📋 **Домашнее задание на сегодня ({date.today().strftime('%d.%m')}):**\n\n"
        for hw in hws:
            status = "✅" if hw.completed else "📌"
            msg_text += f"{status} **{hw.subject}**\n└ {hw.task_text}\n\n"

    await callback.message.edit_text(msg_text, reply_markup=get_back_keyboard("menu_homework"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "hw_all")
async def show_hw_all(callback: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        hws = await get_all_user_active_homeworks(session, user.id)

    if not hws:
        msg_text = "📆 **У вас нет активных домашних заданий!**"
    else:
        msg_text = "📆 **Все активные домашние задания:**\n\n"
        current_date = None
        for hw in hws:
            if hw.due_date != current_date:
                current_date = hw.due_date
                msg_text += f"📅 **{current_date.strftime('%d.%m.%Y')}:**\n"
            msg_text += f"  📌 **{hw.subject}**: {hw.task_text}\n"

    await callback.message.edit_text(msg_text, reply_markup=get_back_keyboard("menu_homework"), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "hw_clear_completed")
async def clear_completed_hw(callback: CallbackQuery):
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        await delete_user_completed_homeworks(session, user.id)

    await callback.message.edit_text(
        "✅ Выполненные задания очищены.",
        reply_markup=get_homework_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()
