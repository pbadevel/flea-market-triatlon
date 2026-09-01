"""
Миграция: очередь поднятий в канал и время последней публикации поднятия.
Запуск: python scripts/migrate_channel_boost_queue.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.bot.database.methods import engine

MIGRATION_SQL = """
ALTER TABLE boost_settings ADD COLUMN IF NOT EXISTS last_channel_boost_post_at TIMESTAMP NULL;

CREATE TABLE IF NOT EXISTS channel_boost_queue (
    id SERIAL PRIMARY KEY,
    ad_id INTEGER NOT NULL UNIQUE REFERENCES ads(id) ON DELETE CASCADE,
    enqueued_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_channel_boost_queue_enqueued_at ON channel_boost_queue (enqueued_at);
"""


async def run_migration():
    print("Миграция: channel_boost_queue + last_channel_boost_post_at...")
    async with engine.begin() as conn:
        for stmt in MIGRATION_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    await conn.execute(text(stmt))
                    print(f"  OK: {stmt[:70]}...")
                except Exception as e:
                    print(f"  SKIP/ERROR ({e}): {stmt[:70]}...")
    print("Готово.")


if __name__ == "__main__":
    asyncio.run(run_migration())
