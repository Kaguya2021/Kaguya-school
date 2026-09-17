from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Моё расписание", callback_data="menu_schedule"),
            InlineKeyboardButton(text="📝 Моё ДЗ", callback_data="menu_homework")
        ],
        [
            InlineKeyboardButton(text="➕ Создать расписание", callback_data="create_schedule"),
            InlineKeyboardButton(text="➕ Добавить ДЗ", callback_data="add_homework")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")
        ]
    ])


def get_back_keyboard(target: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"nav_{target}")]
    ])


def get_schedule_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="save_schedule"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="create_schedule")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="nav_main_menu")
        ]
    ])


def get_schedule_view_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Расписание на неделю", callback_data="sch_full_week"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="create_schedule")
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить расписание", callback_data="sch_delete_confirm")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_main_menu")
        ]
    ])


def get_homework_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить ДЗ", callback_data="add_homework"),
            InlineKeyboardButton(text="📋 Сегодня", callback_data="hw_today")
        ],
        [
            InlineKeyboardButton(text="📆 Все ДЗ", callback_data="hw_all"),
            InlineKeyboardButton(text="✅ Очистить готовые", callback_data="hw_clear_completed")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_main_menu")
        ]
    ])


def get_homework_preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить всё", callback_data="save_homework"),
            InlineKeyboardButton(text="✏️ Изменить", callback_data="add_homework")
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="nav_menu_homework")
        ]
    ])


def get_settings_menu_keyboard(settings) -> InlineKeyboardMarkup:
    sch_status = "🔔" if settings.schedule_notifications else "🔕"
    hw_status = "🔔" if settings.homework_notifications else "🔕"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{sch_status} Утреннее расписание: {settings.schedule_notification_time}",
                callback_data="set_time_schedule"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{hw_status} Вечернее ДЗ: {settings.homework_notification_time}",
                callback_data="set_time_homework"
            )
        ],
        [
            InlineKeyboardButton(text="⚙️ Время начала уроков", callback_data="set_lesson_times"),
            InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="set_timezone")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_main_menu")
        ]
    ])


def get_time_picker_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="06:00", callback_data=f"{prefix}_06:00"),
            InlineKeyboardButton(text="06:30", callback_data=f"{prefix}_06:30"),
            InlineKeyboardButton(text="07:00", callback_data=f"{prefix}_07:00")
        ],
        [
            InlineKeyboardButton(text="07:30", callback_data=f"{prefix}_07:30"),
            InlineKeyboardButton(text="08:00", callback_data=f"{prefix}_08:00"),
            InlineKeyboardButton(text="18:00", callback_data=f"{prefix}_18:00")
        ],
        [
            InlineKeyboardButton(text="19:00", callback_data=f"{prefix}_19:00"),
            InlineKeyboardButton(text="20:00", callback_data=f"{prefix}_20:00"),
            InlineKeyboardButton(text="🔕 Выключить", callback_data=f"{prefix}_off")
        ],
        [
            InlineKeyboardButton(text="⌨️ Другое время", callback_data=f"{prefix}_custom")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_menu_settings")
        ]
    ])


def get_timezone_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇰🇬 UTC+6", callback_data="tz_UTC+6"),
            InlineKeyboardButton(text="🇰🇿 UTC+5", callback_data="tz_UTC+5")
        ],
        [
            InlineKeyboardButton(text="🇺🇿 UTC+5", callback_data="tz_UTC+5"),
            InlineKeyboardButton(text="🇷🇺 UTC+3", callback_data="tz_UTC+3")
        ],
        [
            InlineKeyboardButton(text="🇹🇷 UTC+3", callback_data="tz_UTC+3"),
            InlineKeyboardButton(text="🇦🇪 UTC+4", callback_data="tz_UTC+4")
        ],
        [
            InlineKeyboardButton(text="⌨️ Ввести вручную", callback_data="tz_custom")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_menu_settings")
        ]
    ])


def get_lesson_times_keyboard(times_dict) -> InlineKeyboardMarkup:
    buttons = []
    for num in range(1, 8):
        t_str = times_dict.get(num, "Не задано")
        buttons.append([
            InlineKeyboardButton(
                text=f"{num}️⃣ Урок — {t_str}",
                callback_data=f"edit_ltime_{num}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_menu_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav_main_menu")
        ]
    ])
