# src/api/endpoints/ads.py
import os

from fastapi import APIRouter, Query, Form, File, Depends, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy import select, func, or_
from sqlalchemy.orm import joinedload, selectinload
from src.models import Ad, AdStatus, Review, User, AdPhoto
from src.auth.dependencies import WebUser, WebAdmin

from src.kit.database.service import database_service
from src.services import ad_service, user_service
from src.bot.tg_services import tg_service_notifier


from src.schemas.ads import AdOut, MyAdOut, AdCreate, AdPhotoCreate, AdModerate
from datetime import datetime
from typing import Optional, List, Annotated


UPLOAD_DIR = "uploads"


def _delete_photo_file(storage_path: str | None) -> None:
    """Delete a photo file from disk if it exists."""
    if not storage_path:
        return
    filepath = os.path.join(UPLOAD_DIR, storage_path)
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass  # already gone, nothing to do
    except OSError as e:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to delete photo file: %s — %s", filepath, e
        )

router = APIRouter(prefix="/ads", tags=["ads"])




@router.get("")
async def list_ads(
    category: list[str] | None = Query(None),
    subcategory: list[str] | None = Query(None),
    country: list[str] | None = Query(None),
    city: list[str] | None = Query(None),
    condition: Optional[str] = Query(None),
    ad_type: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None),
    max_price: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query('created_at_desc'),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    async with database_service.get_session() as db:
        stmt = select(Ad).where(Ad.status == AdStatus.approved)
        
        stmt = stmt.options(
            selectinload(Ad.photos),
            joinedload(Ad.seller)
                .selectinload(User.reviews_received)
                .options(joinedload(Review.reviewer)),
            joinedload(Ad.seller).selectinload(User.credentials),
        )
        
        # Filters (multiple values = OR within group, AND across groups)
        category_filters: list = []
        if category:
            category_filters.append(Ad.category.in_(category))
        if subcategory:
            category_filters.append(Ad.subcategory.in_(subcategory))
        if category_filters:
            stmt = stmt.where(or_(*category_filters))

        # City is matched exactly as stored in DB. When cities are chosen, they
        # take precedence — many legacy ads have city set but country empty.
        if city:
            stmt = stmt.where(Ad.city.in_(city))
        elif country:
            stmt = stmt.where(Ad.country.in_(country))
        if condition:
            stmt = stmt.where(Ad.condition == condition)
        if ad_type:
            stmt = stmt.where(Ad.ad_type == ad_type)
        if min_price is not None:
            stmt = stmt.where(Ad.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Ad.price <= max_price)
        if search:
            stmt = stmt.where(
                Ad.title.ilike(f"%{search}%") | 
                Ad.description.ilike(f"%{search}%")
            )
        
        # Sorting
        if sort == 'price_asc':
            stmt = stmt.order_by(Ad.price.asc())
        elif sort == 'price_desc':
            stmt = stmt.order_by(Ad.price.desc())
        elif sort == 'created_at_asc':
            stmt = stmt.order_by(Ad.created_at.asc())
        else:  # created_at_desc (default)
            stmt = stmt.order_by(Ad.created_at.desc())
        
        # Pagination
        total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
        stmt = stmt.offset((page - 1) * limit).limit(limit)
        
        result = await db.execute(stmt)
        ads = result.scalars().unique().all()

        
        return {
            "data": [AdOut.from_orm_with_photos(ad) for ad in ads],
            "total": total,
            "page": page,
            "limit": limit,
        }
    

@router.post("", response_model=MyAdOut, status_code=201)
async def create_ad(
    background_tasks: BackgroundTasks,
    user: WebUser,
    title: Annotated[str, Form()],
    price: Annotated[int, Form()],
    city: Annotated[str, Form()],
    category: Annotated[str, Form()],
    condition: Annotated[str, Form()],
    contact_method: Annotated[str, Form()] = "telegram",
    ad_type: Annotated[str, Form()] = "Продажа",
    country: Annotated[Optional[str], Form()] = None,
    subcategory: Annotated[Optional[str], Form()] = None,
    size: Annotated[Optional[str], Form()] = None,
    description: Annotated[Optional[str], Form()] = None,
    delivery_method: Annotated[Optional[str], Form()] = None,
    photos: Annotated[List[UploadFile], File()] = [],
):
    """
    Create new ad (requires authentication)
    Photos are uploaded and stored locally
    """
    async with database_service.get_session() as session:
        # Upload photos
        photo_data_list: List[AdPhotoCreate] = []
        for i, photo in enumerate(photos):
            if photo.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise HTTPException(400, f"Invalid photo format: {photo.content_type}")
            
            file_bytes = await photo.read()
            extension = f".{photo.filename.split('.')[-1]}" if photo.filename and '.' in photo.filename else ".jpg"
            
            storage_path = await ad_service.upload_photo(file_bytes, extension)
            
            # ИСПРАВЛЕНО: создаем объект AdPhotoCreate
            photo_data_list.append(
                AdPhotoCreate(
                    storage_path=storage_path,
                    position=i,
                )
            )
        
        # Create ad - ИСПРАВЛЕНО: передаем List[AdPhotoCreate]
        ad_data = AdCreate(
            title=title,
            price=price,
            city=city,
            country=country,
            category=category,
            subcategory=subcategory,
            size=size,
            condition=condition,
            description=description,
            ad_type=ad_type,
            delivery_method=delivery_method,
            contact_method=contact_method,
            photos=photo_data_list,  # Теперь это List[AdPhotoCreate]
        )
        fresh_user = await user_service.get_repository(session).get_by_id(user.id)
        ad = await ad_service.create_ad(session, fresh_user, ad_data) # pyright: ignore
        
        # Отправка в канал (фоном, чтобы не ждать)
        background_tasks.add_task(tg_service_notifier.send_ad_for_moderation_by_id, ad.id)
        
        await session.commit()
        
        return MyAdOut.from_orm_with_status(ad)



@router.get("/my", response_model=dict)
async def get_my_ads(
    user: WebUser,
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get current user's ads"""
    async with database_service.get_session() as session:
        status_enum = AdStatus(status) if status else None
        
        ads, total = await ad_service.get_user_ads(
            session=session,
            user_id=user.id,
            status=status_enum,
            limit=limit,
            page=page,
        )
        
        return {
            "data": [MyAdOut.from_orm_with_status(ad) for ad in ads],
            "total": total,
            "page": page,
            "limit": limit,
        }


@router.post("/{ad_id}/moderate", response_model=MyAdOut)
async def moderate_ad(
    ad_id: int,
    data: AdModerate,
    admin: WebAdmin,
):
    """
    Moderate ad (approve or reject)
    Only for admins/moderators
    """
    async with database_service.get_session() as session:
        ad = await ad_service.moderate_ad(
            session=session,
            ad_id=ad_id,
            action=data.action,
            rejection_reason=data.rejection_reason,
        )
        
        if not ad:
            raise HTTPException(404, "Ad not found")
        
        # TODO: Send to Telegram channel if approved
        # if data.action == "approve":
        #     await send_ad_to_channel(ad)
        
        await session.commit()
        return MyAdOut.from_orm_with_status(ad)


@router.post("/{ad_id}/resend", response_model=MyAdOut)
async def resend_ad(
    background_tasks: BackgroundTasks,
    ad_id: int,
    user: WebUser,
):
    """
    Отправить отклонённое объявление на повторную модерацию без редактирования.
    """
    async with database_service.get_session() as session:
        repository = ad_service.get_repository(session)
        ad = await repository.get_ad_with_photos(ad_id)
        
        if not ad:
            raise HTTPException(404, "Объявление не найдено")
        
        if ad.seller_user_id != user.id:
            raise HTTPException(403, "Нет прав на это действие")
        
        if ad.status != AdStatus.rejected.value:
            raise HTTPException(400, "Можно повторно отправить только отклонённое объявление")
        
        ad.status = AdStatus.pending.value
        ad.rejection_reason = None
        
        # Уведомления фоном
        background_tasks.add_task(tg_service_notifier.delete_ad_from_channel_by_id, ad.id)
        background_tasks.add_task(tg_service_notifier.send_ad_for_moderation_by_id, ad.id)
        
        await session.commit()
        
        updated_ad = await repository.get_ad_with_photos(ad_id)
        return MyAdOut.from_orm_with_status(updated_ad) # pyright: ignore


@router.get("/{ad_id}", response_model=MyAdOut)
async def get_ad_for_edit(
    ad_id: int,
    user: WebUser,
):
    """
    Получить объявление для редактирования
    Только владелец может редактировать своё объявление
    """
    async with database_service.get_session() as session:
        repository = ad_service.get_repository(session)
        ad = await repository.get_ad_with_photos(ad_id)
        
        if not ad:
            raise HTTPException(404, "Объявление не найдено")
        
        # Проверка что это объявление текущего пользователя
        if ad.seller_user_id != user.id:
            raise HTTPException(403, "Нет прав на редактирование этого объявления")
        
        return MyAdOut.from_orm_with_status(ad)


@router.put("/{ad_id}", response_model=MyAdOut)
async def update_ad(
    background_tasks: BackgroundTasks,
    ad_id: int,
    user: WebUser,
    title: str = Form(...),
    price: int = Form(...),
    city: str = Form(...),
    category: str = Form(...),
    condition: str = Form(...),
    contact_method: str = Form("telegram"),
    ad_type: str = Form("Продажа"),
    country: Optional[str] = Form(None),
    subcategory: Optional[str] = Form(None),
    size: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    delivery_method: Optional[str] = Form(None),
    photos: List[UploadFile] = File(default=[]),
    keep_photo_ids: List[int] = Form(default=[]),
):
    """
    Обновить объявление
    После редактирования статус меняется на pending (требуется модерация)
    """
    async with database_service.get_session() as session:
        repository = ad_service.get_repository(session)
        ad = await repository.get_ad_with_photos(ad_id)
        
        if not ad:
            raise HTTPException(404, "Объявление не найдено")
        
        # Проверка что это объявление текущего пользователя
        if ad.seller_user_id != user.id:
            raise HTTPException(403, "Нет прав на редактирование этого объявления")
        
        # Обновляем данные
        ad.title = title
        ad.price = price
        ad.city = city
        ad.country = country
        ad.category = category
        ad.subcategory = subcategory
        ad.size = size
        ad.condition = condition
        ad.description = description
        ad.ad_type = ad_type
        ad.delivery_method = delivery_method
        ad.contact_method = contact_method
        
        # Меняем статус на pending (требуется повторная модерация)
        ad.status = AdStatus.pending.value
        ad.rejection_reason = None  # Очищаем причину отклонения
        
        # Управление фото: удаляем только те, что не в keep_photo_ids, добавляем новые
        keep_set = set(keep_photo_ids)
        photos_to_delete = [p for p in ad.photos if p.id not in keep_set]
        
        # Удаляем файлы с диска
        for old_photo in photos_to_delete:
            _delete_photo_file(old_photo.storage_path)
        
        # Удаляем из БД
        for old_photo in photos_to_delete:
            await session.delete(old_photo)
        
        # Обновляем позиции оставшихся фото
        remaining = [p for p in ad.photos if p.id in keep_set]
        for i, photo in enumerate(remaining):
            photo.position = i
        
        # Добавляем новые
        start_pos = len(remaining)
        for i, photo in enumerate(photos):
            if photo.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise HTTPException(400, f"Invalid photo format: {photo.content_type}")
            
            file_bytes = await photo.read()
            extension = f".{photo.filename.split('.')[-1]}" if photo.filename and '.' in photo.filename else ".jpg"
            
            storage_path = await ad_service.upload_photo(file_bytes, extension)
            
            new_photo = AdPhoto(
                ad_id=ad.id,
                file_id=None,
                storage_path=storage_path,
                position=start_pos + i,
            )
            session.add(new_photo)
        
        # Уведомления фоном (чтобы не блокировать ответ)
        background_tasks.add_task(tg_service_notifier.delete_ad_from_channel_by_id, ad.id)
        background_tasks.add_task(tg_service_notifier.send_ad_for_moderation_by_id, ad.id)

        await session.commit()
        
        # Возвращаем обновлённое объявление
        updated_ad = await repository.get_ad_with_photos(ad_id)
        return MyAdOut.from_orm_with_status(updated_ad) # pyright: ignore


@router.delete("/{ad_id}")
async def delete_ad(
    background_tasks: BackgroundTasks,
    ad_id: int,
    user: WebUser,
):
    """
    Удалить объявление
    Только владелец может удалить своё объявление
    """
    async with database_service.get_session() as session:
        ad = await ad_service.get_repository(session).get_ad_with_photos(ad_id)
        
        if not ad:
            raise HTTPException(404, "Объявление не найдено")
        
        # Проверка что это объявление текущего пользователя
        if ad.seller_user_id != user.id:
            raise HTTPException(403, "Нет прав на удаление этого объявления")
        
        # Удаляем файлы фото с диска
        for photo in ad.photos:
            _delete_photo_file(photo.storage_path)

        # Удаляем фото из БД
        for photo in ad.photos:
            await session.delete(photo)
        
        # Удаляем объявление
        await session.delete(ad)
        await session.commit()
        
        background_tasks.add_task(tg_service_notifier.delete_ad_from_channel_by_id, ad.id)

        return {"status": "ok", "message": "Объявление удалено"}
    