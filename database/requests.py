from typing import List, Optional, Tuple, Dict
from datetime import date
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Schedule, Homework, UserSettings, LessonTime

DEFAULT_LESSON_TIMES = {
    1: "08:00",
    2: "08:50",
    3: "09:40",
    4: "10:40",
    5: "11:30",
    6: "12:20",
    7: "13:10"
}


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None
) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id).options(
        selectinload(User.settings),
        selectinload(User.lesson_times)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, username=username, first_name=first_name)
        session.add(user)
        await session.flush()

        settings = UserSettings(user_id=user.id)
        session.add(settings)

        for num, t_str in DEFAULT_LESSON_TIMES.items():
            session.add(LessonTime(user_id=user.id, lesson_number=num, start_time=t_str))

        await session.commit()
        await session.refresh(user, ["settings", "lesson_times"])
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    stmt = select(User).where(User.telegram_id == telegram_id).options(
        selectinload(User.settings),
        selectinload(User.lesson_times)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> List[User]:
    stmt = select(User).options(selectinload(User.settings))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def save_user_schedule(
    session: AsyncSession,
    user_db_id: int,
    parsed_schedule: Dict[int, List[Tuple[int, str]]]
) -> None:
    # Очищаем только расписание данного пользователя
    await session.execute(delete(Schedule).where(Schedule.user_id == user_db_id))

    for weekday, lessons in parsed_schedule.items():
        for lesson_num, subject in lessons:
            item = Schedule(
                user_id=user_db_id,
                weekday=weekday,
                lesson_number=lesson_num,
                subject=subject
            )
            session.add(item)
    await session.commit()


async def get_user_schedule_for_day(session: AsyncSession, user_db_id: int, weekday: int) -> List[Schedule]:
    stmt = (
        select(Schedule)
        .where(Schedule.user_id == user_db_id, Schedule.weekday == weekday)
        .order_by(Schedule.lesson_number)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_user_full_schedule(session: AsyncSession, user_db_id: int) -> List[Schedule]:
    stmt = (
        select(Schedule)
        .where(Schedule.user_id == user_db_id)
        .order_by(Schedule.weekday, Schedule.lesson_number)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_user_schedule(session: AsyncSession, user_db_id: int) -> None:
    await session.execute(delete(Schedule).where(Schedule.user_id == user_db_id))
    await session.commit()


async def add_user_homeworks(session: AsyncSession, user_db_id: int, homeworks: List[Dict]) -> None:
    for hw in homeworks:
        item = Homework(
            user_id=user_db_id,
            subject=hw["subject"],
            task_text=hw["task_text"],
            due_date=hw["due_date"]
        )
        session.add(item)
    await session.commit()


async def get_user_homework_by_date(session: AsyncSession, user_db_id: int, target_date: date) -> List[Homework]:
    stmt = (
        select(Homework)
        .where(Homework.user_id == user_db_id, Homework.due_date == target_date)
        .order_by(Homework.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_user_active_homeworks(session: AsyncSession, user_db_id: int) -> List[Homework]:
    stmt = (
        select(Homework)
        .where(Homework.user_id == user_db_id, Homework.completed == False)
        .order_by(Homework.due_date, Homework.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def toggle_homework_status(session: AsyncSession, user_db_id: int, hw_id: int) -> Optional[bool]:
    stmt = select(Homework).where(Homework.id == hw_id, Homework.user_id == user_db_id)
    result = await session.execute(stmt)
    hw = result.scalar_one_or_none()
    if hw:
        hw.completed = not hw.completed
        await session.commit()
        return hw.completed
    return None


async def delete_user_completed_homeworks(session: AsyncSession, user_db_id: int) -> None:
    await session.execute(delete(Homework).where(Homework.user_id == user_db_id, Homework.completed == True))
    await session.commit()


async def update_user_timezone(session: AsyncSession, user_db_id: int, tz_str: str) -> None:
    await session.execute(update(User).where(User.id == user_db_id).values(timezone=tz_str))
    await session.commit()


async def update_user_settings(session: AsyncSession, user_db_id: int, **kwargs) -> None:
    await session.execute(update(UserSettings).where(UserSettings.user_id == user_db_id).values(**kwargs))
    await session.commit()


async def update_lesson_time(session: AsyncSession, user_db_id: int, lesson_num: int, start_time: str) -> None:
    stmt = select(LessonTime).where(
        LessonTime.user_id == user_db_id,
        LessonTime.lesson_number == lesson_num
    )
    res = await session.execute(stmt)
    item = res.scalar_one_or_none()
    if item:
        item.start_time = start_time
    else:
        session.add(LessonTime(user_id=user_db_id, lesson_number=lesson_num, start_time=start_time))
    await session.commit()


async def get_user_lesson_times_dict(session: AsyncSession, user_db_id: int) -> Dict[int, str]:
    stmt = select(LessonTime).where(LessonTime.user_id == user_db_id)
    res = await session.execute(stmt)
    times = res.scalars().all()
    res_dict = DEFAULT_LESSON_TIMES.copy()
    for t in times:
        res_dict[t.lesson_number] = t.start_time
    return res_dict


async def get_admin_stats(session: AsyncSession) -> Dict[str, int]:
    users_cnt = await session.execute(select(func.count(User.id)))
    schedules_cnt = await session.execute(select(func.count(Schedule.id)))
    homeworks_cnt = await session.execute(select(func.count(Homework.id)))

    return {
        "users": users_cnt.scalar() or 0,
        "schedules": schedules_cnt.scalar() or 0,
        "homeworks": homeworks_cnt.scalar() or 0
    }
