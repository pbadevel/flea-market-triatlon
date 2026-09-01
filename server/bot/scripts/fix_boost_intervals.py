"""Одноразово: поменять интервалы поднятий местами (обычный 12 дн, доверенный 6 дн)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.bot.database.methods import engine


async def main():
    async with engine.begin() as conn:
        before = await conn.execute(
            text(
                "SELECT regular_boost_interval_days, trusted_boost_interval_days "
                "FROM boost_settings WHERE id = 1"
            )
        )
        row = before.fetchone()
        if row:
            print(f"До: обычный={row[0]} дн, доверенный={row[1]} дн")
        result = await conn.execute(
            text(
                """
                UPDATE boost_settings
                SET regular_boost_interval_days = 12,
                    trusted_boost_interval_days = 6,
                    updated_at = NOW()
                WHERE id = 1
                  AND regular_boost_interval_days = 6
                  AND trusted_boost_interval_days = 12
                """
            )
        )
        print(f"Обновлено строк: {result.rowcount}")
        after = await conn.execute(
            text(
                "SELECT regular_boost_interval_days, trusted_boost_interval_days "
                "FROM boost_settings WHERE id = 1"
            )
        )
        row2 = after.fetchone()
        if row2:
            print(f"После: обычный={row2[0]} дн, доверенный={row2[1]} дн")


if __name__ == "__main__":
    asyncio.run(main())
