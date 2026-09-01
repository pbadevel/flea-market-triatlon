"""
Скрипт для проверки объявлений с типом "Аренда"
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.database.methods import async_session
from src.models import Ad
from sqlalchemy.future import select
from sqlalchemy import func


async def check_rent_ads():
    """Проверить объявления с типом 'Аренда'"""
    async with async_session() as session:
        # Получаем все объявления с типом "Аренда"
        query = select(Ad).where(Ad.ad_type == "Аренда")
        result = await session.execute(query)
        ads = result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"Всего объявлений с типом 'Аренда': {len(ads)}")
        print(f"{'='*80}\n")
        
        if not ads:
            print("Объявления с типом 'Аренда' не найдены!")
            return
        
        # Группируем по статусу
        by_status = {}
        for ad in ads:
            status = ad.status
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(ad)
        
        print("Объявления по статусам:")
        for status, status_ads in by_status.items():
            print(f"\n  Статус '{status}': {len(status_ads)} объявлений")
        
        print(f"\n{'='*80}")
        print("Детальная информация по объявлениям:")
        print(f"{'='*80}\n")
        
        for i, ad in enumerate(ads, 1):
            print(f"{i}. ID: {ad.id}")
            print(f"   Название: {ad.title}")
            print(f"   Статус: {ad.status}")
            print(f"   Тип: {ad.ad_type}")
            print(f"   Цена: {ad.price}₽")
            print(f"   Город: {ad.city}")
            print(f"   Категория: {ad.category}")
            print(f"   Создано: {ad.created_at}")
            print()
        
        # Проверяем approved объявления
        approved_query = select(Ad).where(
            Ad.ad_type == "Аренда",
            Ad.status == "approved"
        )
        approved_result = await session.execute(approved_query)
        approved_ads = approved_result.scalars().all()
        
        print(f"{'='*80}")
        print(f"Объявлений с типом 'Аренда' и статусом 'approved': {len(approved_ads)}")
        print(f"{'='*80}\n")
        
        if approved_ads:
            print("Approved объявления:")
            for i, ad in enumerate(approved_ads, 1):
                print(f"{i}. ID: {ad.id} - {ad.title} ({ad.price}₽, {ad.city})")
        else:
            print("Approved объявления с типом 'Аренда' не найдены!")
        
        # Проверяем, какие значения ad_type есть в базе
        print(f"\n{'='*80}")
        print("Все значения ad_type в базе данных:")
        print(f"{'='*80}\n")
        
        all_types_query = select(Ad.ad_type, Ad.status, func.count(Ad.id)).group_by(Ad.ad_type, Ad.status)
        all_types_result = await session.execute(all_types_query)
        all_types = all_types_result.fetchall()
        
        for ad_type, status, count in all_types:
            print(f"  ad_type='{ad_type}', status='{status}': {count} объявлений")


if __name__ == "__main__":
    asyncio.run(check_rent_ads())
