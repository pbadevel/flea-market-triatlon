"""
Миграция БД: добавление колонок для системы поднятия объявлений.
Запускать один раз: python scripts/migrate_boost.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.bot.database.methods import engine


MIGRATION_SQL = """
-- Новые колонки в таблице ads
ALTER TABLE ads ADD COLUMN IF NOT EXISTS boost_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS last_boost_at TIMESTAMP NULL;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS next_boost_at TIMESTAMP NULL;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS boost_reminder_step INTEGER NOT NULL DEFAULT 0;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS boost_reminder_sent_at TIMESTAMP NULL;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS boost_first_reminder_at TIMESTAMP NULL;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS boost_confirmed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE ads ADD COLUMN IF NOT EXISTS inactive_since TIMESTAMP NULL;

-- Таблица настроек поднятия
CREATE TABLE IF NOT EXISTS boost_settings (
    id INTEGER PRIMARY KEY,
    regular_boost_count INTEGER NOT NULL DEFAULT 2,
    trusted_boost_count INTEGER NOT NULL DEFAULT 4,
    regular_boost_interval_days INTEGER NOT NULL DEFAULT 12,
    trusted_boost_interval_days INTEGER NOT NULL DEFAULT 6,
    regular_daily_limit INTEGER NOT NULL DEFAULT 3,
    trusted_daily_limit INTEGER NOT NULL DEFAULT 6,
    test_mode BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Вставить запись по умолчанию если её нет (все колонки NOT NULL заданы явно)
INSERT INTO boost_settings (
    id, regular_boost_count, trusted_boost_count,
    regular_boost_interval_days, trusted_boost_interval_days,
    regular_daily_limit, trusted_daily_limit, test_mode, created_at, updated_at
) VALUES (1, 2, 4, 12, 6, 3, 6, FALSE, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Таблица логов поднятий
CREATE TABLE IF NOT EXISTS boost_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    ad_id INTEGER NOT NULL REFERENCES ads(id),
    boosted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_boost_logs_user_id ON boost_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_boost_logs_ad_id ON boost_logs(ad_id);
CREATE INDEX IF NOT EXISTS idx_boost_logs_boosted_at ON boost_logs(boosted_at);
"""


async def run_migration():
    print("Запускаю миграцию для системы поднятия...")
    async with engine.begin() as conn:
        for stmt in MIGRATION_SQL.strip().split(';'):
            stmt = stmt.strip()
            if stmt:
                try:
                    await conn.execute(text(stmt))
                    print(f"  OK: {stmt[:60]}...")
                except Exception as e:
                    print(f"  SKIP/ERROR ({e}): {stmt[:60]}...")
    print("Миграция завершена.")


if __name__ == '__main__':
    asyncio.run(run_migration())
