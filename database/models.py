from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, String, Boolean, ForeignKey, Time, Date, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(32), default="UTC+6")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    schedules: Mapped[List["Schedule"]] = relationship(
        "Schedule", back_populates="user", cascade="all, delete-orphan"
    )
    homeworks: Mapped[List["Homework"]] = relationship(
        "Homework", back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    lesson_times: Mapped[List["LessonTime"]] = relationship(
        "LessonTime", back_populates="user", cascade="all, delete-orphan"
    )


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 - Mon, 6 - Sun
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="schedules")

    __table_args__ = (
        Index("idx_user_weekday", "user_id", "weekday"),
    )


class Homework(Base):
    __tablename__ = "homework"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    task_text: Mapped[str] = mapped_column(String(1024), nullable=False)
    due_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="homeworks")

    __table_args__ = (
        Index("idx_user_due_date", "user_id", "due_date"),
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    schedule_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    homework_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    tomorrow_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule_notification_time: Mapped[str] = mapped_column(String(5), default="07:00")
    homework_notification_time: Mapped[str] = mapped_column(String(5), default="18:00")
    tomorrow_notification_time: Mapped[str] = mapped_column(String(5), default="20:00")

    user: Mapped["User"] = relationship("User", back_populates="settings")


class LessonTime(Base):
    __tablename__ = "lesson_times"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="lesson_times")
