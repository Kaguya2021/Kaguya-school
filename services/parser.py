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
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    result: Dict[int, List[Tuple[int, str]]] = {}
    current_weekday: Optional[int] = None

    for line in lines:
        detected_day = _detect_weekday_in_line(line)
        if detected_day is not None:
            current_weekday = detected_day
            if current_weekday not in result:
                result[current_weekday] = []

            content_after_day = re.sub(
                r'^(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье|пн|вт|ср|чт|пт|сб|вс|mon|tue|wed|thu|fri|sat|sun)[:\-\s]*',
                '', line, flags=re.IGNORECASE
            ).strip()
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
            if re.match(rf'^{alias}(?:\b|[:\-\s]|$)', clean_line):
                return day_idx
    return None


def _process_lessons_block(raw_text: str, lesson_list: List[Tuple[int, str]]):
    parts = re.split(r'[,;]\s*', raw_text)
    for part in parts:
        part = part.strip()
        if not part:
            continue

        match = re.match(r'^(\d+)[\.\)\s\-]+(.+)$', part)
        if match:
            num = int(match.group(1))
            subject = match.group(2).strip().capitalize()
            if subject:
                lesson_list.append((num, subject))
        else:
            next_num = max([l[0] for l in lesson_list], default=0) + 1
            subject = part.capitalize()
            if subject:
                lesson_list.append((next_num, subject))


def parse_homework_text(text: str) -> List[Dict[str, str]]:
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


def find_next_lesson_date(subject: str, user_schedules: list, current_date: date) -> date:
    """Автоматически находит ближайший следующий день, когда будет этот предмет."""
    subject_clean = subject.strip().lower()
    days_with_subject = set()

    for item in user_schedules:
        if item.subject.strip().lower() == subject_clean:
            days_with_subject.add(item.weekday)

    if not days_with_subject:
        # Если предмета нет в расписании, ставим на завтра
        return current_date + timedelta(days=1)

    # Ищем ближайший день недели начиная с завтра
    for i in range(1, 8):
        check_date = current_date + timedelta(days=i)
        if check_date.weekday() in days_with_subject:
            return check_date

    return current_date + timedelta(days=1)


def parse_time_string(time_str: str) -> Optional[str]:
    cleaned = re.sub(r'[^\d:\s]', '', time_str.strip())
    match = re.match(r'^(\d{1,2})[:\s]+(\d{2})$', cleaned)
    if not match:
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

