import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional

WEEKDAYS_MAP = {
    0: ["понедельник", "пон", "пн", "mon", "monday"],
    1: ["вторник", "вт", "вто", "tue", "tuesday"],
    2: ["среда", "ср", "сре", "wed", "wednesday"],
    3: ["четверг", "чт", "чет", "thu", "thursday"],
    4: ["пятница", "пт", "пят", "fri", "friday"],
    5: ["суббота", "сб", "суб", "sat", "saturday"],
    6: ["воскресенье", "вс", "вос", "sun", "sunday"]
}


def parse_schedule_text(text: str) -> Dict[int, List[Tuple[int, str]]]:
    """
    Разбирает произвольный текстовый ввод расписания.
    Возвращает dict: { weekday_index (0..6): [(lesson_num, subject_name), ...] }
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    result: Dict[int, List[Tuple[int, str]]] = {}
    current_weekday: Optional[int] = None

    for line in lines:
        detected_day = _detect_weekday_in_line(line)
        if detected_day is not None:
            current_weekday = detected_day
            if current_weekday not in result:
                result[current_weekday] = []

            # Проверяем, есть ли уроки в этой же строке после двоеточия или тире
            content_after_day = re.sub(r'^(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье|пн|вт|ср|чт|пт|сб|вс|mon|tue|wed|thu|fri|sat|sun)[:\-\s]*', '', line, flags=re.IGNORECASE).strip()
            if content_after_day:
                _process_lessons_block(content_after_day, result[current_weekday])
            continue

        if current_weekday is not None:
            _process_lessons_block(line, result[current_weekday])

    return result


def _detect_weekday_in_line(line: str) -> Optional[int]:
    clean_line = line.lower().strip()
    for day_idx, aliases in WEEKDAYS_MAP.items():
        for alias in aliases:
            # Соответствие в начале строки или как отд. слово
            if re.match(rf'^{alias}(?:\b|[:\-\s]|$)', clean_line):
                return day_idx
    return None


def _process_lessons_block(raw_text: str, lesson_list: List[Tuple[int, str]]):
    # Поддерживаем разделители запятые, точки с запятой или перенос строки
    parts = re.split(r'[,;]\s*', raw_text)
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Поиск номера урока в начале: "1. Математика", "1) Русский", "1 Математика"
        match = re.match(r'^(\d+)[\.\)\s\-]+(.+)$', part)
        if match:
            num = int(match.group(1))
            subject = match.group(2).strip().capitalize()
            if subject:
                lesson_list.append((num, subject))
        else:
            # Если номера нет, назначаем авто-инкремент
            next_num = max([l[0] for l in lesson_list], default=0) + 1
            subject = part.capitalize()
            if subject:
                lesson_list.append((next_num, subject))


def parse_homework_text(text: str) -> List[Dict[str, str]]:
    """
    Разбирает текст ДЗ формата:
    Предмет - Задание
    Предмет: Задание
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    items = []

    for line in lines:
        if "-" in line:
            parts = line.split("-", 1)
        elif ":" in line:
            parts = line.split(":", 1)
        else:
            parts = [line, ""]

        subject = parts[0].strip().capitalize()
        task = parts[1].strip() if len(parts) > 1 else "Задание не указано"

        if subject:
            items.append({
                "subject": subject,
                "task_text": task if task else "Задание не указано"
            })

    return items


def parse_time_string(time_str: str) -> Optional[str]:
    """
    Преобразует строковый ввод ("07:00", "7:00", "19 30") в формат HH:MM.
    Возвращает None, если формат некорректен.
    """
    cleaned = re.sub(r'[^\d:\s]', '', time_str.strip())
    match = re.match(r'^(\d{1,2})[:\s]+(\d{2})$', cleaned)
    if not match:
        # Попытка разобрать просто час
        match_hour = re.match(r'^(\d{1,2})$', cleaned)
        if match_hour:
            h = int(match_hour.group(1))
            if 0 <= h <= 23:
                return f"{h:02d}:00"
        return None

    h, m = int(match.group(1)), int(match.group(2))
    if 0 <= h <= 23 and 0 <= m <= 59:
        return f"{h:02d}:{m:02d}"
    return None


def parse_date_string(date_str: str, base_date: Optional[date] = None) -> Optional[date]:
    """
    Распознает варианты 'сегодня', 'завтра', 'послезавтра', '23.09', '23.09.2026'
    """
    if base_date is None:
        base_date = date.today()

    clean_str = date_str.strip().lower()

    if clean_str == "сегодня":
        return base_date
    if clean_str == "завтра":
        return base_date + timedelta(days=1)
    if clean_str == "послезавтра":
        return base_date + timedelta(days=2)

    # 23.09 или 23.09.2026
    match_dt = re.match(r'^(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?$', clean_str)
    if match_dt:
        day = int(match_dt.group(1))
        month = int(match_dt.group(2))
        year = int(match_dt.group(3)) if match_dt.group(3) else base_date.year
        try:
            res_date = date(year, month, day)
            if res_date < base_date and not match_dt.group(3):
                res_date = date(year + 1, month, day)
            return res_date
        except ValueError:
            return None

    # Поиск по дню недели ("в понедельник", "пн")
    for day_idx, aliases in WEEKDAYS_MAP.items():
        for alias in aliases:
            if alias in clean_str:
                days_ahead = day_idx - base_date.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return base_date + timedelta(days=days_ahead)

    return None
