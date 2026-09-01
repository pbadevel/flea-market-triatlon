from aiogram.types import Message
from src.bot.settings.settings import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy import update, delete, func, or_
from typing import Optional, List
from datetime import datetime

from loguru import logger
from src.kit.database.service import database_service
from src.bot.utils.helpers import format_file_id_to_storage_path
from src.utils import download_file_from_telegram
from src.models import *


# engine = create_async_engine(
#     DATABASE_URL,
#     pool_pre_ping=True,
#     pool_size=5,
#     max_overflow=10
# )

# async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
async_session =  database_service.get_sessionmaker()

# async def init_db():
#     """
#     инициализирует бд, создавая все таблицы, указанные в моделях.

#     Примечание:
#         должна быть вызвана при запуске приложения для первичной инициализации структуры бд.

#     Args:
#         None

#     Returns:
#         None
#     """
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


async def create_or_update_user(message: Message, from_user=None):
    """
    Создает нового пользователя или обновляет существующего в бд.

    Returns:
        User: Объект пользователя из бд.
    """
    u = from_user if from_user is not None else getattr(message, "from_user", None)
    if not u:
        logger.error("create_or_update_user: нет ни from_user, ни message.from_user")
        return None

    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == u.id))
        user = result.scalars().first()

        is_admin = u.id in ADMIN_IDS
        
        if not user:
            try:
                new_user = User(
                    tg_user_id=u.id,
                    username=u.username,
                    first_name=u.first_name,
                    last_name=u.last_name,
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                return new_user
            except IntegrityError:
                await session.rollback()
                result = await session.execute(select(User).where(User.tg_user_id == u.id))
                user = result.scalars().first()
                if not user:
                    logger.error(f"Не удалось создать или найти пользователя {u.id}")
                    raise
                user.username = u.username
                user.first_name = u.first_name
                user.last_name = u.last_name
                if is_admin:
                    user.is_moderator = True
                await session.commit()
                return user
        else:
            user.username = u.username
            user.first_name = u.first_name
            user.last_name = u.last_name
            if is_admin:
                user.is_moderator = True
            await session.commit()
            return user


async def get_user_by_tg_id(tg_user_id: int):
    """Получить пользователя по Telegram ID"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_user_id))
        return result.scalars().first()


async def get_user_by_id(user_id: int):
    """Получить пользователя по внутреннему ID"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()


async def set_user_phone(tg_user_id: int, phone: str):
    """Установить номер телефона пользователя"""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_user_id == tg_user_id).values(phone=phone)
        )
        await session.commit()


# === МЕТОДЫ ДЛЯ ОБЪЯВЛЕНИЙ ===

async def create_ad(seller_user_id: int, ad_data: dict):
    """
    Создать объявление
    
    Args:
        seller_user_id: ID продавца
        ad_data: Данные объявления (dict)
    
    Returns:
        Ad: Созданное объявление
    """
    async with async_session() as session:
        # Для аренды и категории `slots` поле `condition` не критично — используем дефолт.
        ad_type = ad_data.get('ad_type', 'Продажа')
        category = ad_data.get('category', '')
        condition = ad_data.get('condition')
        if not condition and (ad_type == 'Аренда' or category == 'slots'):
            condition = 'Не указано'
        
        new_ad = Ad(
            seller_user_id=seller_user_id,
            title=ad_data['title'],
            price=ad_data['price'],
            city=ad_data['city'],
            country=ad_data.get('country'),
            category=ad_data['category'],
            subcategory=ad_data.get('subcategory'),  # Может быть None для категорий без подкатегорий
            size=ad_data.get('size'),
            condition=condition or 'Не указано',
            description=ad_data.get('description'),
            ad_type=ad_type,
            delivery_method=ad_data.get('delivery_method'),  # Для аренды может быть None
            contact_method=ad_data.get('contact_method', 'telegram'),
            status='pending',
            cover_file_id=ad_data.get('cover_photo_file_id') or ad_data.get('cover_file_id')
        )
        session.add(new_ad)
        await session.commit()
        await session.refresh(new_ad)
        return new_ad


async def add_ad_photos(ad_id: int, photos: List[dict]):
    """
    Добавить фото к объявлению
    
    Args:
        ad_id: ID объявления
        photos: Список словарей с file_id и position
    """

    async with async_session() as session:
        for photo in photos:

            file_id = photo['file_id']

            storage_path = await download_file_from_telegram(file_id)
            logger.info(f"storage: {storage_path}")

            new_photo = AdPhoto(
                ad_id=ad_id,
                file_id=photo['file_id'],
                position=photo['position'],
                storage_path=storage_path,
                
            )
            session.add(new_photo)
        await session.commit()


async def get_ad_by_id(ad_id: int):
    """Получить объявление по ID"""
    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.id == ad_id)
        )
        return result.scalars().first()


async def get_ad_photos(ad_id: int):
    """Получить фотографии объявления"""
    async with async_session() as session:
        result = await session.execute(
            select(AdPhoto).where(AdPhoto.ad_id == ad_id).order_by(AdPhoto.position)
        )
        return result.scalars().all()


# === РЕДАКТИРОВАНИЕ (КОПИЯ НА МОДЕРАЦИИ) ===

async def create_ad_edit(original_ad_id: int, data: dict, photos: List[dict], cover_file_id: str = None) -> int:
    """
    Создать копию объявления при редактировании одобренного. Возвращает edit_id.
    """
    async with async_session() as session:
        edit = AdEdit(
            original_ad_id=original_ad_id,
            seller_user_id=data['seller_user_id'],
            title=data['title'],
            price=data['price'],
            city=data['city'],
            country=data.get('country'),
            category=data['category'],
            subcategory=data.get('subcategory'),
            size=data.get('size'),
            condition=data.get('condition', 'Не указано'),
            description=data.get('description'),
            ad_type=data.get('ad_type', 'Продажа'),
            delivery_method=data.get('delivery_method'),
            contact_method=data.get('contact_method', 'telegram'),
            cover_file_id=cover_file_id,
        )
        session.add(edit)
        await session.flush()
        edit_id = edit.id
        for p in photos:
            session.add(AdEditPhoto(edit_id=edit_id, file_id=p['file_id'], position=p['position']))
        await session.commit()
        return edit_id


async def get_ad_edit(edit_id: int):
    """Получить копию объявления по edit_id."""
    async with async_session() as session:
        result = await session.execute(select(AdEdit).where(AdEdit.id == edit_id))
        return result.scalars().first()


async def get_edit_photos(edit_id: int):
    """Получить фотографии копии объявления."""
    async with async_session() as session:
        result = await session.execute(
            select(AdEditPhoto).where(AdEditPhoto.edit_id == edit_id).order_by(AdEditPhoto.position)
        )
        return result.scalars().all()


async def exists_edit_for_ad(ad_id: int) -> bool:
    """Есть ли копия на модерации для данного объявления."""
    async with async_session() as session:
        result = await session.execute(select(AdEdit.id).where(AdEdit.original_ad_id == ad_id).limit(1))
        return result.scalar_one_or_none() is not None


async def apply_ad_edit(edit_id: int) -> Optional[int]:
    """
    Применить одобренную копию к оригиналу: обновить Ad и AdPhoto, удалить копию.
    Возвращает ad_id или None при ошибке.
    """
    async with async_session() as session:
        edit = (await session.execute(select(AdEdit).where(AdEdit.id == edit_id))).scalars().first()
        if not edit:
            return None
        ad_id = edit.original_ad_id
        ad = (await session.execute(select(Ad).where(Ad.id == ad_id))).scalars().first()
        if not ad:
            return None
        photos = (await session.execute(
            select(AdEditPhoto).where(AdEditPhoto.edit_id == edit_id).order_by(AdEditPhoto.position)
        )).scalars().all()
        if not photos:
            logger.warning(f"apply_ad_edit: у копии #{edit_id} нет фото")
            return None

        await session.execute(delete(AdPhoto).where(AdPhoto.ad_id == ad_id))
        for p in photos:
            session.add(AdPhoto(ad_id=ad_id, file_id=p.file_id, position=p.position))
        await session.execute(
            update(Ad).where(Ad.id == ad_id).values(
                title=edit.title,
                price=edit.price,
                city=edit.city,
                country=edit.country,
                category=edit.category,
                subcategory=edit.subcategory,
                size=edit.size,
                condition=edit.condition,
                description=edit.description,
                ad_type=edit.ad_type,
                delivery_method=edit.delivery_method,
                contact_method=edit.contact_method,
                cover_file_id=edit.cover_file_id,
            )
        )
        await session.execute(delete(AdEdit).where(AdEdit.id == edit_id))
        await session.commit()
        logger.info(f"Копия #{edit_id} применена к объявлению #{ad_id}")
        return ad_id


async def delete_ad_edit_return_info(edit_id: int) -> Optional[tuple]:
    """
    Удалить копию объявления (отклонение редактирования).
    Возвращает (title, seller_user_id, original_ad_id) для уведомления или None.
    """
    async with async_session() as session:
        edit = (await session.execute(select(AdEdit).where(AdEdit.id == edit_id))).scalars().first()
        if not edit:
            return None
        title = edit.title
        seller_id = edit.seller_user_id
        original_ad_id = edit.original_ad_id
        await session.execute(delete(AdEdit).where(AdEdit.id == edit_id))
        await session.commit()
        return (title, seller_id, original_ad_id)


async def delete_edits_for_ad(original_ad_id: int) -> int:
    """Удалить все копии (редактирования) для объявления. Возвращает количество удалённых."""
    async with async_session() as session:
        result = await session.execute(delete(AdEdit).where(AdEdit.original_ad_id == original_ad_id))
        n = result.rowcount
        await session.commit()
        if n:
            logger.info(f"Удалено копий редактирования для объявления #{original_ad_id}: {n}")
        return n


async def approve_ad(ad_id: int, channel_message_id: int = None):
    """Одобрить объявление
    
    Args:
        ad_id: ID объявления
        channel_message_id: ID сообщения в канале (опционально, None если не публикуется в канал)
    """
    async with async_session() as session:
        # Формируем словарь значений для обновления
        update_values = {
            'status': 'approved',
            'published_at': datetime.utcnow(),
            'rejection_reason': None,
            # Сбрасываем все поля напоминаний, чтобы шедулер не поставил паузу
            # сразу после одобрения (boost_first_reminder_at мог остаться старым)
            'boost_first_reminder_at': None,
            'boost_reminder_sent_at': None,
            'boost_reminder_step': 0,
            'boost_confirmed': False,
        }
        
        # Добавляем channel_message_id только если он указан
        if channel_message_id is not None:
            update_values['channel_message_id'] = channel_message_id
        
        result = await session.execute(
            update(Ad).where(Ad.id == ad_id).values(**update_values)
        )
        await session.commit()
        
        # проверяем, что обновление прошло успешно
        if result.rowcount == 0:
            logger.error(f"не удалось обновить статус объявления #{ad_id} на 'approved'")
        else:
            if channel_message_id is not None:
                logger.info(f"объявление #{ad_id} успешно обновлено: status='approved', channel_message_id={channel_message_id}, rejection_reason очищена")
            else:
                logger.info(f"объявление #{ad_id} успешно обновлено: status='approved' (без публикации в канал), rejection_reason очищена")


async def reject_ad(ad_id: int, reason: str):
    """Отклонить объявление"""
    async with async_session() as session:
        await session.execute(
            update(Ad).where(Ad.id == ad_id).values(
                status='rejected',
                rejection_reason=reason
            )
        )
        await session.commit()


async def get_approved_ads(limit: int = 10, offset: int = 0):
    """Получить одобренные объявления для каталога"""
    async with async_session() as session:
        result = await session.execute(
            select(Ad)
            .where(Ad.status == 'approved')
            .order_by(Ad.published_at.desc().nullslast(), Ad.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


async def count_users():
    """Подсчитать количество пользователей"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(User)
        )
        return result.scalar() or 0


async def count_approved_ads():
    """Подсчитать количество одобренных объявлений"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(Ad).where(Ad.status == 'approved')
        )
        return result.scalar() or 0


async def count_ads_by_category(category: str = None):
    """Подсчитать количество товаров в категории"""
    async with async_session() as session:
        query = select(func.count()).select_from(Ad).where(Ad.status == 'approved')
        if category:
            query = query.where(Ad.category == category)
        result = await session.execute(query)
        return result.scalar() or 0


async def count_ads_by_ad_type(ad_type: str):
    """Подсчитать количество объявлений по типу (Продажа/Аренда)"""
    async with async_session() as session:
        logger.info(f"count_ads_by_ad_type called with ad_type='{ad_type}' (type: {type(ad_type)}, len: {len(ad_type) if ad_type else 0}, repr: {repr(ad_type)})")
        logger.info(f"ad_type bytes: {ad_type.encode('utf-8') if ad_type else None}")
        
        all_rent_query = select(func.count()).select_from(Ad).where(Ad.ad_type == ad_type)
        all_rent_result = await session.execute(all_rent_query)
        all_rent_count = all_rent_result.scalar() or 0
        logger.info(f"Total ads with ad_type='{ad_type}' (all statuses): {all_rent_count}")
        
        status_query = select(Ad.status, func.count(Ad.id)).where(Ad.ad_type == ad_type).group_by(Ad.status)
        status_result = await session.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result.fetchall()}
        logger.info(f"Ads with ad_type='{ad_type}' by status: {status_counts}")
        
        all_types_query = select(Ad.ad_type, func.count(Ad.id)).group_by(Ad.ad_type)
        all_types_result = await session.execute(all_types_query)
        all_types = {row[0]: row[1] for row in all_types_result.fetchall()}
        logger.info(f"All ad_type values in DB (all statuses): {all_types}")
        
        sample_query = select(Ad.ad_type).where(Ad.status == 'approved').distinct().limit(10)
        sample_result = await session.execute(sample_query)
        sample_types = [row[0] for row in sample_result.fetchall()]
        logger.info(f"Sample ad_type values from DB (approved only): {sample_types}")
        
        query = select(func.count()).select_from(Ad).where(
            Ad.status == 'approved',
            Ad.ad_type == ad_type
        )
        result = await session.execute(query)
        count = result.scalar() or 0
        
        if count == 0:
            logger.warning(f"Exact match returned 0, trying alternative methods...")
            try:
                alt_query = select(func.count()).select_from(Ad).where(
                    Ad.status == 'approved',
                    func.trim(Ad.ad_type) == ad_type.strip()
                )
                alt_result = await session.execute(alt_query)
                alt_count = alt_result.scalar() or 0
                if alt_count > 0:
                    logger.info(f"Found {alt_count} ads using trim comparison")
                    count = alt_count
            except Exception as e:
                logger.error(f"Error in trim comparison: {e}")
            if count == 0:
                all_approved_query = select(Ad.id, Ad.ad_type).where(Ad.status == 'approved').limit(50)
                all_approved_result = await session.execute(all_approved_query)
                all_approved = all_approved_result.fetchall()
                logger.info(f"Sample approved ads ad_type values: {[(ad[0], repr(ad[1]), len(ad[1]) if ad[1] else 0) for ad in all_approved[:10]]}")
                
                manual_count = 0
                for ad_id, ad_type_val in all_approved:
                    if ad_type_val == ad_type:
                        manual_count += 1
                    elif ad_type_val and ad_type_val.strip() == ad_type.strip():
                        logger.warning(f"Found match with strip: ad_id={ad_id}, ad_type={repr(ad_type_val)}, expected={repr(ad_type)}")
                        manual_count += 1
                
                if manual_count > 0:
                    logger.warning(f"Manual count found {manual_count} matches, but SQL query returned 0!")
                    all_approved_full_query = select(Ad).where(Ad.status == 'approved')
                    all_approved_full_result = await session.execute(all_approved_full_query)
                    all_approved_full = all_approved_full_result.scalars().all()
                    manual_count_full = sum(1 for ad in all_approved_full if ad.ad_type == ad_type or (ad.ad_type and ad.ad_type.strip() == ad_type.strip()))
                    logger.warning(f"Full manual count: {manual_count_full}")
                    count = manual_count_full
        direct_query = select(Ad.id, Ad.ad_type, Ad.status).where(
            Ad.status == 'approved'
        ).limit(20)
        direct_result = await session.execute(direct_query)
        direct_ads = direct_result.fetchall()
        logger.info(f"Sample approved ads: {[(ad[0], ad[1], ad[2]) for ad in direct_ads]}")
        
        rent_ads_found = [ad for ad in direct_ads if ad[1] == ad_type]
        logger.info(f"Found {len(rent_ads_found)} ads with ad_type='{ad_type}' in sample")
        
        logger.info(f"count_ads_by_ad_type: ad_type='{ad_type}', count={count}")
        
        if count == 0:
            all_types_query = select(Ad.ad_type, func.count(Ad.id)).where(
                Ad.status == 'approved'
            ).group_by(Ad.ad_type)
            all_types_result = await session.execute(all_types_query)
            all_types = {row[0]: row[1] for row in all_types_result.fetchall()}
            logger.warning(f"No ads found with ad_type='{ad_type}' and status='approved'. Available types and counts: {all_types}")
        
        return count


async def count_ads_by_subcategory(category: str, subcategory: str = None):
    """Подсчитать количество товаров в подкатегории"""
    async with async_session() as session:
        query = select(func.count()).select_from(Ad).where(
            Ad.status == 'approved',
            Ad.category == category
        )
        if subcategory:
            query = query.where(Ad.subcategory == subcategory)
        result = await session.execute(query)
        return result.scalar() or 0


async def get_ads_by_category(category: str, subcategory: str = None, limit: int = 10, offset: int = 0):
    """Получить товары по категории/подкатегории"""
    async with async_session() as session:
        query = select(Ad).where(
            Ad.status == 'approved',
            Ad.category == category
        )
        if subcategory:
            query = query.where(Ad.subcategory == subcategory)
        query = query.order_by(Ad.published_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return result.scalars().all()


async def get_ads_by_subcategories(category: str, subcategories: list, limit: int = 10, offset: int = 0):
    """Получить товары по категории и списку подкатегорий"""
    async with async_session() as session:
        query = select(Ad).where(
            Ad.status == 'approved',
            Ad.category == category,
            Ad.subcategory.in_(subcategories)
        )
        query = query.order_by(Ad.published_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        return result.scalars().all()


async def count_ads_by_subcategories(category: str, subcategories: list):
    """Подсчитать количество товаров в списке подкатегорий"""
    async with async_session() as session:
        query = select(func.count()).select_from(Ad).where(
            Ad.status == 'approved',
            Ad.category == category,
            Ad.subcategory.in_(subcategories)
        )
        result = await session.execute(query)
        return result.scalar() or 0


async def search_ads(query: str, limit: int = 10):
    """Поиск объявлений по запросу"""
    async with async_session() as session:
        search_pattern = f"%{query}%"
        result = await session.execute(
            select(Ad)
            .where(
                Ad.status == 'approved',
                or_(
                    Ad.title.ilike(search_pattern),
                    Ad.description.ilike(search_pattern)
                )
            )
            .order_by(Ad.published_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


async def mark_ad_sold(ad_id: int):
    """Отметить объявление как проданное"""
    async with async_session() as session:
        await session.execute(
            update(Ad).where(Ad.id == ad_id).values(status='sold')
        )
        await session.commit()


async def mark_ad_removed(ad_id: int):
    """Снять объявление с публикации (тот же статус, что и при снятии пользователем — unpublished)."""
    async with async_session() as session:
        await session.execute(
            update(Ad).where(Ad.id == ad_id).values(status='unpublished')
        )
        await session.commit()


async def update_ad(ad_id: int, **kwargs):
    """Обновить объявление (для модераторов/админов)"""
    # Фильтруем только разрешенные поля для обновления
    allowed_fields = {
        'title', 'price', 'city', 'country', 'category', 'subcategory',
        'size', 'condition', 'description', 'contact_method', 'status', 'cover_file_id',
        'ad_type', 'delivery_method', 'channel_message_id',
        # Поля системы поднятия
        'boost_count', 'last_boost_at', 'next_boost_at', 'boost_reminder_step',
        'boost_reminder_sent_at', 'boost_first_reminder_at', 'boost_confirmed', 'inactive_since',
        'published_at',
    }
    
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not update_data:
        logger.warning(f"попытка обновить объявление #{ad_id} без разрешенных полей")
        return False
    
    async with async_session() as session:
        result = await session.execute(
            update(Ad).where(Ad.id == ad_id).values(**update_data)
        )
        await session.commit()
        
        if result.rowcount == 0:
            logger.warning(f"объявление #{ad_id} не найдено для обновления")
            return False
        
        logger.info(f"объявление #{ad_id} обновлено: {list(update_data.keys())}")
        return True


async def get_user_ads(user_id: int, status: Optional[str] = None, include_removed: bool = False):
    """Получить объявления пользователя (все статусы, включая снятые с публикации)."""
    async with async_session() as session:
        query = select(Ad).where(Ad.seller_user_id == user_id)
        if status:
            query = query.where(Ad.status == status)
        query = query.order_by(Ad.created_at.desc())
        
        result = await session.execute(query)
        return result.scalars().all()


async def count_user_ads(user_id: int, include_removed: bool = False):
    """Подсчитать количество объявлений пользователя (все статусы)."""
    async with async_session() as session:
        query = select(func.count()).select_from(Ad).where(Ad.seller_user_id == user_id)
        result = await session.execute(query)
        return result.scalar() or 0


# === МЕТОДЫ ДЛЯ ОТЗЫВОВ ===

async def get_user_review_by_reviewer(reviewed_user_id: int, reviewer_user_id: int):
    """Получить отзыв конкретного пользователя о конкретном продавце"""
    async with async_session() as session:
        result = await session.execute(
            select(Review)
            .where(
                Review.reviewed_user_id == reviewed_user_id,
                Review.reviewer_user_id == reviewer_user_id
            )
            .order_by(Review.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def create_review(reviewed_user_id: int, reviewer_user_id: int, rating: int, comment: Optional[str] = None, ad_id: Optional[int] = None):
    """Создать или обновить отзыв (если уже существует)"""
    async with async_session() as session:
        # Проверяем, есть ли уже отзыв от этого пользователя (в той же сессии)
        result = await session.execute(
            select(Review)
            .where(
                Review.reviewed_user_id == reviewed_user_id,
                Review.reviewer_user_id == reviewer_user_id
            )
            .order_by(Review.created_at.desc())
            .limit(1)
        )
        existing_review = result.scalar_one_or_none()
        
        if existing_review:
            # Обновляем существующий отзыв
            logger.info(f"Обновляю отзыв ID={existing_review.id}: rating={rating}, comment={comment}")
            existing_review.rating = rating
            existing_review.comment = comment
            if ad_id:
                existing_review.ad_id = ad_id
            # Явно помечаем объект как измененный
            session.add(existing_review)
            await session.flush()  # Сначала flush, чтобы изменения были видны
            await session.commit()
            await session.refresh(existing_review)  # Обновляем объект из бд
            logger.info(f"Отзыв ID={existing_review.id} обновлен: rating={existing_review.rating}, comment={existing_review.comment}")
        else:
            # Создаем новый отзыв
            new_review = Review(
                reviewed_user_id=reviewed_user_id,
                reviewer_user_id=reviewer_user_id,
                rating=rating,
                comment=comment,
                ad_id=ad_id
            )
            session.add(new_review)
            await session.commit()


async def get_user_reviews(user_id: int, limit: int = 10, offset: int = 0):
    """Получить отзывы о пользователе"""
    async with async_session() as session:
        result = await session.execute(
            select(Review)
            .where(Review.reviewed_user_id == user_id)
            .order_by(Review.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


async def count_user_reviews(user_id: int):
    """Подсчитать количество отзывов о пользователе"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(Review).where(Review.reviewed_user_id == user_id)
        )
        return result.scalar()


async def get_user_average_rating(user_id: int):
    """Получить среднюю оценку пользователя"""
    async with async_session() as session:
        result = await session.execute(
            select(func.avg(Review.rating)).where(Review.reviewed_user_id == user_id)
        )
        avg_rating = result.scalar()
        return round(avg_rating, 1) if avg_rating else 0


# === МЕТОДЫ ДЛЯ ЛОГОВ КОНТАКТОВ ===

async def log_contact_request(buyer_user_id: int, seller_user_id: int, ad_id: int):
    """Залогировать запрос контакта"""
    async with async_session() as session:
        new_log = ContactLog(
            buyer_user_id=buyer_user_id,
            seller_user_id=seller_user_id,
            ad_id=ad_id
        )
        session.add(new_log)
        await session.commit()


# === ЧЕРНЫЙ СПИСОК (БАН) ===

async def get_banned_tg_ids() -> set:
    """Возвращает множество tg_user_id из черного списка."""
    async with async_session() as session:
        result = await session.execute(select(Blacklist.tg_user_id))
        rows = result.scalars().all()
        return set(rows) if rows else set()


async def add_to_blacklist(tg_user_id: int):
    """Добавить пользователя в черный список по tg_user_id."""
    async with async_session() as session:
        try:
            session.add(Blacklist(tg_user_id=tg_user_id))
            await session.commit()
        except IntegrityError:
            await session.rollback()
            # уже в списке
            pass


async def remove_from_blacklist(tg_user_id: int):
    """Удалить пользователя из черного списка."""
    tg_user_id = int(tg_user_id)
    async with async_session() as session:
        # Проверяем, существует ли запись перед удалением
        result = await session.execute(select(Blacklist.tg_user_id).where(Blacklist.tg_user_id == tg_user_id))
        exists = result.first() is not None
        if not exists:
            logger.warning(f"Попытка удалить пользователя {tg_user_id} из черного списка, но его там нет")
            return
        
        # Удаляем запись
        await session.execute(delete(Blacklist).where(Blacklist.tg_user_id == tg_user_id))
        await session.commit()
        logger.info(f"Пользователь {tg_user_id} успешно удален из черного списка")


async def is_banned(tg_user_id: int) -> bool:
    """Проверить, забанен ли пользователь (есть ли запись в blacklist)."""
    async with async_session() as session:
        result = await session.execute(select(Blacklist.tg_user_id).where(Blacklist.tg_user_id == tg_user_id))
        row = result.first()
        return row is not None


# === ЛОГ «ПОДРОБНЕЕ» (ПЕРЕХОДЫ) ===

async def log_details_view(user_tg_id: int, username: Optional[str], ad_id: int, seller_user_id: int):
    """Залогировать нажатие «Подробнее» (просмотр карточки объявления)."""
    async with async_session() as session:
        session.add(DetailsLog(
            user_tg_id=user_tg_id,
            username=username,
            ad_id=ad_id,
            seller_user_id=seller_user_id
        ))
        await session.commit()


# === ПОИСК ПОЛЬЗОВАТЕЛЯ ПО USERNAME ===

async def get_user_by_username(username: str):
    """Получить пользователя по username (без @). Поиск без учёта регистра (Telegram username case-insensitive)."""
    name = (username or "").strip().lstrip("@")
    if not name:
        return None
    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.username.isnot(None),
                func.lower(User.username) == name.lower()
            )
        )
        return result.scalars().first()


# === АДМИНИСТРАТИВНЫЕ МЕТОДЫ ===

async def set_moderator(tg_user_id: int, is_moderator: bool = True):
    """Установить/снять права модератора"""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_user_id == tg_user_id).values(is_moderator=is_moderator)
        )
        await session.commit()


async def is_moderator(tg_user_id: int):
    """Проверить, является ли пользователь модератором"""
    logger.debug(f"проверка модератора для user_id={tg_user_id}, ADMIN_IDS={ADMIN_IDS}")
    
    # Проверяем, является ли пользователь админом (из ADMIN_IDS)
    if tg_user_id in ADMIN_IDS:
        logger.debug(f"пользователь {tg_user_id} найден в ADMIN_IDS, возвращаю True")
        return True
    
    # Проверяем в базе данных
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.tg_user_id == tg_user_id)
        )
        is_mod = result.scalar()
        logger.debug(f"пользователь {tg_user_id} в бд: is_moderator={is_mod}")
        return is_mod.is_moderator


# === СТАТИСТИКА И ЭКСПОРТ ДЛЯ АДМИНКИ ===

async def count_users() -> int:
    """Общее количество пользователей в бд бота."""
    async with async_session() as session:
        result = await session.execute(select(func.count(User.id)))
        return result.scalar() or 0


async def count_banned() -> int:
    """Количество пользователей в черном списке."""
    async with async_session() as session:
        result = await session.execute(select(func.count(Blacklist.id)))
        return result.scalar() or 0


async def get_users_csv_rows() -> List[tuple]:
    """Список строк для выгрузки пользователей: (id, tg_id_user, username, created_at, is_banned, is_trusted_seller)."""
    async with async_session() as session:
        result = await session.execute(
            select(
                User.id,
                User.tg_user_id,
                User.username,
                User.created_at,
                User.is_trusted_seller,
                Blacklist.id.label("blacklist_id"),
            )
            .outerjoin(Blacklist, User.tg_user_id == Blacklist.tg_user_id)
            .order_by(User.id)
        )
        rows = result.all()
        return [
            (r[0], r[1], r[2], r[3], r[5] is not None, r[4])
            for r in rows
        ]


# === МЕТОДЫ ДЛЯ ДОВЕРЕННЫХ ПРОДАВЦОВ ===

async def set_trusted_seller(tg_user_id: int, is_trusted: bool = True):
    """Установить/снять статус доверенного продавца"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_user_id))
        user = result.scalars().first()
        if user:
            user.is_trusted_seller = is_trusted
            await session.commit()
            return True
        return False


async def is_trusted_seller(tg_user_id: int) -> bool:
    """Проверить, является ли пользователь доверенным продавцом"""
    async with async_session() as session:
        result = await session.execute(
            select(User.is_trusted_seller).where(User.tg_user_id == tg_user_id)
        )
        return result.scalar() or False


async def count_trusted_sellers() -> int:
    """Подсчитать количество доверенных продавцов"""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(User.id)).where(User.is_trusted_seller == True)
        )
        return result.scalar() or 0


async def count_user_ads_today(user_id: int) -> int:
    """Подсчитать количество объявлений пользователя, созданных сегодня (по календарным суткам)"""
    from datetime import datetime, timezone
    
    # Получаем начало и конец текущих календарных суток (по UTC)
    # Используем naive datetime — created_at хранится как TIMESTAMP WITHOUT TIME ZONE
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    start_of_day = start_of_day.replace(tzinfo=None)
    end_of_day = end_of_day.replace(tzinfo=None)
    
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Ad.id)).where(
                Ad.seller_user_id == user_id,
                Ad.created_at >= start_of_day,
                Ad.created_at <= end_of_day
            )
        )
        return result.scalar() or 0


async def get_details_stats_aggregated(date_from=None, date_to=None) -> List[tuple]:
    """Агрегат по переходам «Подробнее»: (user_tg_id, username, count)."""
    q = select(
        DetailsLog.user_tg_id,
        DetailsLog.username,
        func.count(DetailsLog.id).label("cnt")
    ).group_by(DetailsLog.user_tg_id, DetailsLog.username)
    if date_from is not None:
        q = q.where(DetailsLog.created_at >= date_from)
    if date_to is not None:
        q = q.where(DetailsLog.created_at <= date_to)
    async with async_session() as session:
        result = await session.execute(q)
        return [(r[0], r[1] or "", r[2]) for r in result.all()]


async def get_contact_stats_aggregated(date_from=None, date_to=None) -> List[tuple]:
    """Агрегат по просмотру профиля/контактов: (user_tg_id, username, count)."""
    q = select(
        User.tg_user_id,
        User.username,
        func.count(ContactLog.id).label("cnt")
    ).join(ContactLog, ContactLog.buyer_user_id == User.id).group_by(User.id, User.tg_user_id, User.username)
    if date_from is not None:
        q = q.where(ContactLog.created_at >= date_from)
    if date_to is not None:
        q = q.where(ContactLog.created_at <= date_to)
    async with async_session() as session:
        result = await session.execute(q)
        return [(r[0], r[1] or "", r[2]) for r in result.all()]


async def get_details_detailed_rows(date_from=None, date_to=None) -> List[tuple]:
    """Детальная статистика переходов: дата/время, пользователь, действие, id объявления, продавец."""
    # действие = "Подробнее"; продавец = seller username или tg_id
    q = select(
        DetailsLog.created_at,
        DetailsLog.user_tg_id,
        DetailsLog.username,
        DetailsLog.ad_id,
        User.username.label("seller_username"),
        User.tg_user_id.label("seller_tg_id")
    ).join(Ad, Ad.id == DetailsLog.ad_id).join(User, User.id == DetailsLog.seller_user_id)
    if date_from is not None:
        q = q.where(DetailsLog.created_at >= date_from)
    if date_to is not None:
        q = q.where(DetailsLog.created_at <= date_to)
    q = q.order_by(DetailsLog.created_at)
    async with async_session() as session:
        result = await session.execute(q)
        return result.all()


async def get_contact_detailed_rows(date_from=None, date_to=None) -> List[tuple]:
    """Детальная статистика контактов: дата/время, покупатель, действие, id объявления, продавец."""
    q = select(
        ContactLog.created_at,
        User.tg_user_id.label("buyer_tg_id"),
        User.username.label("buyer_username"),
        ContactLog.ad_id,
        Ad.seller_user_id
    ).join(User, User.id == ContactLog.buyer_user_id).join(Ad, Ad.id == ContactLog.ad_id)
    if date_from is not None:
        q = q.where(ContactLog.created_at >= date_from)
    if date_to is not None:
        q = q.where(ContactLog.created_at <= date_to)
    q = q.order_by(ContactLog.created_at)
    async with async_session() as session:
        rows = (await session.execute(q)).all()
    # добавить username продавца
    out = []
    for r in rows:
        seller = await get_user_by_id(r[4])
        seller_name = f"@{seller.username}" if seller and seller.username else str(seller.tg_user_id) if seller else ""
        out.append((r[0], r[1], r[2] or "", "Профиль и контакты", r[3], seller_name))
    return out


async def get_placed_sold_removed_counts(date_from, date_to) -> tuple:
    """(count_placed, count_sold, count_removed) за период по created_at / published_at / status."""
    async with async_session() as session:
        # Размещено: created_at в периоде
        r = await session.execute(
            select(func.count(Ad.id)).where(
                Ad.created_at >= date_from,
                Ad.created_at <= date_to
            )
        )
        placed = r.scalar() or 0
        # Продано: status=sold и обновление в периоде (у нас нет updated_at, считаем по published_at или created_at)
        r = await session.execute(
            select(func.count(Ad.id)).where(
                Ad.status == "sold",
                Ad.created_at <= date_to
            )
        )
        # Точнее: продано за период — когда статус сменился на sold. Если нет поля даты смены — считаем sold за период по created_at объявления
        r = await session.execute(
            select(func.count(Ad.id)).where(
                Ad.status == "sold",
                Ad.created_at >= date_from,
                Ad.created_at <= date_to
            )
        )
        sold = r.scalar() or 0
        r = await session.execute(
            select(func.count(Ad.id)).where(
                Ad.status == "unpublished",
                Ad.created_at >= date_from,
                Ad.created_at <= date_to
            )
        )
        removed = r.scalar() or 0
    return (placed, sold, removed)


async def get_top_placed(date_from, date_to, limit=5) -> List[tuple]:
    """Топ по количеству размещённых объявлений за период: (user_id, username, count)."""
    q = select(
        User.tg_user_id,
        User.username,
        func.count(Ad.id).label("cnt")
    ).join(Ad, Ad.seller_user_id == User.id).where(
        Ad.created_at >= date_from,
        Ad.created_at <= date_to
    ).group_by(User.id, User.tg_user_id, User.username).order_by(func.count(Ad.id).desc()).limit(limit)
    async with async_session() as session:
        result = await session.execute(q)
        return [(r[0], r[1] or "", r[2]) for r in result.all()]


async def get_top_sold(date_from, date_to, limit=5) -> List[tuple]:
    """Топ по количеству проданных за период."""
    q = select(
        User.tg_user_id,
        User.username,
        func.count(Ad.id).label("cnt")
    ).join(Ad, Ad.seller_user_id == User.id).where(
        Ad.status == "sold",
        Ad.created_at >= date_from,
        Ad.created_at <= date_to
    ).group_by(User.id, User.tg_user_id, User.username).order_by(func.count(Ad.id).desc()).limit(limit)
    async with async_session() as session:
        result = await session.execute(q)
        return [(r[0], r[1] or "", r[2]) for r in result.all()]


async def get_top_removed(date_from, date_to, limit=5) -> List[tuple]:
    """Топ по количеству снятых с публикации за период."""
    q = select(
        User.tg_user_id,
        User.username,
        func.count(Ad.id).label("cnt")
    ).join(Ad, Ad.seller_user_id == User.id).where(
        Ad.status == "unpublished",
        Ad.created_at >= date_from,
        Ad.created_at <= date_to
    ).group_by(User.id, User.tg_user_id, User.username).order_by(func.count(Ad.id).desc()).limit(limit)
    async with async_session() as session:
        result = await session.execute(q)
        return [(r[0], r[1] or "", r[2]) for r in result.all()]


async def get_top_reviews_activity(date_from, date_to, limit=5) -> List[tuple]:
    """Топ продавцов по количеству полученных отзывов за период (при равенстве — по среднему рейтингу)."""
    subq = select(
        Review.reviewed_user_id,
        func.count(Review.id).label("reviews_count"),
        func.avg(Review.rating).label("avg_rating")
    ).where(
        Review.created_at >= date_from,
        Review.created_at <= date_to
    ).group_by(Review.reviewed_user_id).subquery()
    q = (
        select(
            User.tg_user_id,
            User.username,
            subq.c.reviews_count,
            subq.c.avg_rating
        )
        .select_from(User)
        .join(subq, subq.c.reviewed_user_id == User.id)
        .order_by(subq.c.reviews_count.desc(), subq.c.avg_rating.desc())
        .limit(limit)
    )
    async with async_session() as session:
        result = await session.execute(q)
        return [(r[0], r[1] or "", r[2], round(float(r[3]), 1) if r[3] is not None else 0) for r in result.all()]


async def get_total_placed_sold_removed(date_from, date_to) -> tuple:
    """Общее количество размещённых / проданных / снятых за период."""
    async with async_session() as session:
        r = await session.execute(select(func.count(Ad.id)).where(
            Ad.created_at >= date_from, Ad.created_at <= date_to
        ))
        placed = r.scalar() or 0
        r = await session.execute(select(func.count(Ad.id)).where(
            Ad.status == "sold",
            Ad.created_at >= date_from,
            Ad.created_at <= date_to
        ))
        sold = r.scalar() or 0
        r = await session.execute(select(func.count(Ad.id)).where(
            Ad.status == "unpublished",
            Ad.created_at >= date_from,
            Ad.created_at <= date_to
        ))
        removed = r.scalar() or 0
    return (placed, sold, removed)


# === СОГЛАСИЕ 152-ФЗ ===

async def check_user_agreement(tg_user_id: int):
    """проверить, согласился ли юзер"""
    async with async_session() as session:
        result = await session.execute(
            select(User.agreed_to_terms).where(User.tg_user_id == tg_user_id)
        )
        agreed = result.scalar()
        return agreed if agreed is not None else False


async def set_user_agreement(tg_user_id: int):
    """установить согласие"""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_user_id == tg_user_id).values(
                agreed_to_terms=True,
                agreed_at=datetime.utcnow()
            )
        )
        await session.commit()


async def check_user_subscription(tg_user_id: int) -> bool:
    """проверить статус подписки на канал из бд"""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_user_id == tg_user_id))
        user = result.scalars().first()
        if user:
            return user.subscribed_to_channel if hasattr(user, 'subscribed_to_channel') else False
        return False


async def set_user_subscription(tg_user_id: int):
    """установить статус подписки на канал"""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.tg_user_id == tg_user_id).values(
                subscribed_to_channel=True,
                subscribed_at=datetime.utcnow()
            )
        )
        await session.commit()


# ============================================================
# === ПОДНЯТИЕ (BOOST) ===
# ============================================================

async def get_boost_settings():
    """Получить (или создать) глобальные настройки поднятия."""
    async with async_session() as session:
        result = await session.execute(select(BoostSettings).where(BoostSettings.id == 1))
        settings = result.scalars().first()
        if not settings:
            settings = BoostSettings(id=1)
            session.add(settings)
            await session.commit()
            await session.refresh(settings)
        return settings


async def update_boost_settings(**kwargs):
    """Обновить настройки поднятия."""
    async with async_session() as session:
        result = await session.execute(select(BoostSettings).where(BoostSettings.id == 1))
        settings = result.scalars().first()
        if not settings:
            settings = BoostSettings(id=1, **kwargs)
            session.add(settings)
        else:
            for key, value in kwargs.items():
                setattr(settings, key, value)
            settings.updated_at = datetime.utcnow()
        await session.commit()


async def get_daily_boost_count(user_id: int) -> int:
    """Количество поднятий пользователя за последние 24 часа."""
    since = datetime.utcnow() - __import__('datetime').timedelta(hours=24)
    async with async_session() as session:
        result = await session.execute(
            select(func.count(BoostLog.id)).where(
                BoostLog.user_id == user_id,
                BoostLog.boosted_at >= since
            )
        )
        return result.scalar() or 0


async def log_boost(user_id: int, ad_id: int):
    """Записать факт поднятия в лог."""
    async with async_session() as session:
        session.add(BoostLog(user_id=user_id, ad_id=ad_id))
        await session.commit()


async def get_ads_for_reminder() -> list:
    """
    Получить объявления, которым нужно отправить первичное напоминание.
    Условие: status=approved, boost_count < max (определяется в вызывающем коде),
    next_boost_at задан, reminder_step=0,
    (next_boost_at - 24h) <= now < next_boost_at  ИЛИ  тест: (next_boost_at - 5min) <= now.
    Фильтрация по boost_count vs max делается в scheduler.
    """
    from datetime import timedelta

    now = datetime.utcnow()
    window_start_normal = now + timedelta(hours=23)   # за 23–24 ч до boost
    window_end_normal = now + timedelta(hours=24, minutes=5)

    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(
                Ad.status == "approved",
                Ad.next_boost_at.isnot(None),
                Ad.boost_reminder_step == 0,
                Ad.next_boost_at >= window_start_normal,
                Ad.next_boost_at <= window_end_normal,
            )
        )
        return result.scalars().all()


async def get_ads_for_reminder_test() -> list:
    """Получить объявления для напоминания в тестовом режиме (за 5 минут)."""
    from datetime import timedelta

    now = datetime.utcnow()
    window_start = now + timedelta(minutes=4)
    window_end = now + timedelta(minutes=6)

    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(
                Ad.status == "approved",
                Ad.next_boost_at.isnot(None),
                Ad.boost_reminder_step == 0,
                Ad.next_boost_at >= window_start,
                Ad.next_boost_at <= window_end,
            )
        )
        return result.scalars().all()


async def get_ads_for_boost_execution() -> list:
    """
    Получить объявления, которым нужно выполнить автоподнятие.
    Условие: boost_confirmed=True, next_boost_at <= now, status=approved.
    """
    now = datetime.utcnow()
    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(
                Ad.status == "approved",
                Ad.boost_confirmed == True,
                Ad.next_boost_at.isnot(None),
                Ad.next_boost_at <= now,
            )
        )
        return result.scalars().all()


async def get_ads_to_pause(threshold_delta=None) -> list:
    """
    Объявления, которые нужно перевести в unpublished (по умолчанию 7 дней без ответа).
    threshold_delta: timedelta — насколько давно было первое напоминание.
    """
    from datetime import timedelta

    delta = threshold_delta if threshold_delta is not None else timedelta(days=7)
    threshold = datetime.utcnow() - delta
    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(
                Ad.status == "approved",
                Ad.boost_first_reminder_at.isnot(None),
                Ad.boost_confirmed == False,
                Ad.boost_first_reminder_at <= threshold,
            )
        )
        return result.scalars().all()


async def get_ads_to_deactivate_after_30_days(threshold_delta=None) -> list:
    """
    Объявления, у которых закончились поднятия и прошло threshold_delta (по умолчанию 30 дней).
    Нужно перевести в статус unpublished.
    """
    from datetime import timedelta

    delta = threshold_delta if threshold_delta is not None else timedelta(days=30)
    threshold = datetime.utcnow() - delta
    async with async_session() as session:
        # Фильтрация по boost_count >= max делается в scheduler (не знаем max здесь)
        result = await session.execute(
            select(Ad).where(
                Ad.status == "approved",
                Ad.last_boost_at.isnot(None),
                Ad.last_boost_at <= threshold,
                Ad.boost_confirmed == False,
            )
        )
        return result.scalars().all()


async def get_ads_for_repeat_reminder(
    step1_delta=None,
    stepN_delta=None,
) -> list:
    """
    Объявления, которым нужно отправить повторное напоминание (шаг >= 1).
    Шаг 1 → повтор через step1_delta (по умолчанию 24ч).
    Шаг >= 2 → повтор через stepN_delta (по умолчанию 48ч).
    """
    from datetime import timedelta

    now = datetime.utcnow()
    default_step1 = timedelta(hours=24)
    default_stepN = timedelta(hours=48)
    d1 = step1_delta if step1_delta is not None else default_step1
    dN = stepN_delta if stepN_delta is not None else default_stepN

    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(
                Ad.status == "approved",
                Ad.boost_reminder_step >= 1,
                Ad.boost_confirmed == False,
                Ad.boost_reminder_sent_at.isnot(None),
            )
        )
        ads = result.scalars().all()

    due = []
    for ad in ads:
        interval = d1 if ad.boost_reminder_step == 1 else dN
        if now >= ad.boost_reminder_sent_at + interval:
            due.append(ad)
    return due


async def mark_ad_boost_reminded(ad_id: int, step: int, first_reminder: bool = False):
    """Обновить поля напоминания после отправки."""
    now = datetime.utcnow()
    values = {
        "boost_reminder_step": step,
        "boost_reminder_sent_at": now,
    }
    if first_reminder:
        values["boost_first_reminder_at"] = now
    async with async_session() as session:
        await session.execute(update(Ad).where(Ad.id == ad_id).values(**values))
        await session.commit()


async def mark_ad_boost_confirmed(ad_id: int):
    """Пользователь подтвердил поднятие из напоминания."""
    async with async_session() as session:
        await session.execute(
            update(Ad).where(Ad.id == ad_id).values(boost_confirmed=True)
        )
        await session.commit()


async def enqueue_channel_boost(ad_id: int) -> bool:
    """Очередь публикации поднятия в канал. True — объявление добавлено; False — уже в очереди."""
    now = datetime.utcnow()
    async with async_session() as session:
        try:
            session.add(ChannelBoostQueue(ad_id=ad_id, enqueued_at=now))
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False


async def remove_channel_boost_from_queue(ad_id: int) -> None:
    """Убрать объявление из очереди поднятий (снятие с публикации и т.п.)."""
    async with async_session() as session:
        await session.execute(delete(ChannelBoostQueue).where(ChannelBoostQueue.ad_id == ad_id))
        await session.commit()


async def channel_boost_queue_size() -> int:
    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(ChannelBoostQueue))
        return int(result.scalar() or 0)


async def is_ad_in_channel_boost_queue(ad_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(ChannelBoostQueue.id).where(ChannelBoostQueue.ad_id == ad_id).limit(1)
        )
        return result.scalar_one_or_none() is not None


async def pop_oldest_channel_boost_queue_ad_id() -> Optional[int]:
    """Удалить из очереди самую раннюю запись и вернуть ad_id."""
    async with async_session() as session:
        result = await session.execute(
            select(ChannelBoostQueue).order_by(ChannelBoostQueue.enqueued_at.asc()).limit(1)
        )
        row = result.scalars().first()
        if not row:
            return None
        ad_id = row.ad_id
        await session.delete(row)
        await session.commit()
        return ad_id


async def execute_ad_boost(
    ad_id: int,
    new_channel_message_id: int,
    boost_interval_days: int,
    boost_interval_delta=None,
):
    """
    Зафиксировать выполненное поднятие.
    boost_interval_delta: если передан (timedelta), используется вместо boost_interval_days.
    """
    from datetime import timedelta

    now = datetime.utcnow()
    interval = boost_interval_delta if boost_interval_delta is not None else timedelta(days=boost_interval_days)
    async with async_session() as session:
        ad = (await session.execute(select(Ad).where(Ad.id == ad_id))).scalars().first()
        if not ad:
            return
        ad.boost_count += 1
        ad.last_boost_at = now
        ad.next_boost_at = now + interval
        ad.channel_message_id = new_channel_message_id
        ad.boost_confirmed = False
        ad.boost_reminder_step = 0
        ad.boost_reminder_sent_at = None
        ad.boost_first_reminder_at = None
        ad.published_at = now
        await session.commit()


async def pause_ad(ad_id: int):
    """Перевести объявление в статус unpublished (снято с публикации) и сбросить boost-поля (нет ответа на напоминания)."""
    now = datetime.utcnow()
    await remove_channel_boost_from_queue(ad_id)
    async with async_session() as session:
        await session.execute(
            update(Ad).where(Ad.id == ad_id).values(
                status="unpublished",
                inactive_since=now,
                boost_confirmed=False,
                boost_reminder_step=0,
            )
        )
        await session.commit()


async def get_approved_ads_with_boost_data() -> list:
    """Получить все одобренные объявления с данными поднятия."""
    async with async_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.status == "approved")
        )
        return result.scalars().all()