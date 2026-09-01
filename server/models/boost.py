from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kit.database.models import RecordModel
from .associations import ad_tags
from .enums import AdStatus, ContactMethod, AdType


class BoostSettings(RecordModel):
    """
    Глобальные настройки системы поднятия объявлений.
    """

    regular_boost_count: Mapped[int] = mapped_column(Integer, default=2, nullable=False)        # обычный: кол-во поднятий
    trusted_boost_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)        # доверенный: кол-во поднятий
    regular_boost_interval_days: Mapped[int] = mapped_column(Integer, default=6, nullable=False)   # интервал (дни), обычный
    trusted_boost_interval_days: Mapped[int] = mapped_column(Integer, default=12, nullable=False)  # интервал (дни), доверенный
    regular_daily_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)        # суточный лимит поднятий, обычный
    trusted_daily_limit: Mapped[int] = mapped_column(Integer, default=6, nullable=False)        # суточный лимит поднятий, доверенный
    test_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)              # режим теста (напоминания за 5 мин)
    # Время последней успешной публикации в канал именно от поднятия (не первичная модерация)
    last_channel_boost_post_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ChannelBoostQueue(RecordModel):
    """Очередь поднятий в канал: не чаще одного поста за интервал (см. планировщик)."""

    ad_id: Mapped[int] = mapped_column(Integer, ForeignKey("ads.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class BoostLog(RecordModel):
    """
    Лог поднятий объявлений для отслеживания суточных лимитов.
    """
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ad_id: Mapped[int] = mapped_column(Integer, ForeignKey("ads.id"), nullable=False, index=True)
    boosted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)