"""Admin: управление пользователями."""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from src.kit.database.service import database_service
from src.auth.dependencies import WebAdmin, WebUser
from src.config import settings
from src.models import User, Blacklist, Ad, AdStatus
from src.enums import UserRole

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


class UserOut(BaseModel):
    id: int
    tg_user_id: int | None = None
    username: str | None
    first_name: str | None
    last_name: str | None
    role: str
    is_root: bool
    is_trusted_seller: bool
    phone: str | None
    created_at: str


def _is_root_by_tg_id(tg_id: int | None) -> bool:
    return tg_id is not None and tg_id in settings.ADMIN_IDS


@router.get("")
async def list_users(admin: WebAdmin, search: str = Query("", max_length=50), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    async with database_service.get_session() as session:
        stmt = select(User).order_by(User.created_at.desc())
        if search:
            try:
                uid = int(search)
                stmt = stmt.where(User.id == uid)
            except ValueError:
                p = f"%{search}%"
                stmt = stmt.where(User.username.ilike(p) | User.first_name.ilike(p) | User.last_name.ilike(p))

        total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        result = await session.execute(stmt.offset((page - 1) * limit).limit(limit))
        users = result.scalars().all()

    return {
        "data": [UserOut(id=u.id, tg_user_id=u.tg_user_id, username=u.username,
            first_name=u.first_name, last_name=u.last_name,
            role=u.role.value if hasattr(u.role, 'value') else str(u.role),
            is_root=_is_root_by_tg_id(u.tg_user_id), is_trusted_seller=u.is_trusted_seller,
            phone=u.phone, created_at=u.created_at.isoformat() if u.created_at else "") for u in users],
        "total": total, "page": page, "limit": limit,
    }


class UserUpdate(BaseModel):
    role: str | None = None
    is_trusted_seller: bool | None = None


@router.put("/{user_id}")
async def update_user(user_id: int, data: UserUpdate, admin: WebAdmin):
    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
        if data.role is not None:
            if data.role == "ADMIN" and _is_root_by_tg_id(user.tg_user_id):
                raise HTTPException(400, "Cannot change root admin role")
            try:
                user.role = UserRole(data.role)
            except ValueError:
                raise HTTPException(400, f"Invalid role: {data.role}")
        if data.is_trusted_seller is not None:
            user.is_trusted_seller = data.is_trusted_seller
        await session.commit()
        return {"status": "ok"}


@router.post("/{user_id}/make-admin")
async def make_admin(user_id: int, admin: WebAdmin):
    """Назначить пользователя админом (только root)."""
    if not _is_root_by_tg_id(admin.tg_user_id):
        raise HTTPException(403, "Only root admin can appoint admins")
    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
        user.role = UserRole.ADMIN
        await session.commit()
        return {"status": "ok", "message": f"User {user_id} is now admin"}


@router.post("/{user_id}/ban")
async def ban_user(user_id: int, admin: WebAdmin):
    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
        if _is_root_by_tg_id(user.tg_user_id):
            raise HTTPException(403, "Cannot ban root admin")
        if user.tg_user_id is None:
            raise HTTPException(400, "Cannot ban user without linked Telegram")
        existing = await session.execute(select(Blacklist).where(Blacklist.tg_user_id == user.tg_user_id))
        if not existing.scalar_one_or_none():
            session.add(Blacklist(tg_user_id=user.tg_user_id))
            await session.commit()
        return {"status": "ok", "message": "User banned"}


@router.post("/{user_id}/unban")
async def unban_user(user_id: int, admin: WebAdmin):
    async with database_service.get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(404, "User not found")
        result = await session.execute(select(Blacklist).where(Blacklist.tg_user_id == user.tg_user_id))
        entry = result.scalar_one_or_none()
        if entry:
            await session.delete(entry)
            await session.commit()
        return {"status": "ok", "message": "User unbanned"}


# --- User ads ---

class UserAdOut(BaseModel):
    id: int
    title: str
    price: int
    city: str
    category: str
    status: str
    created_at: str


@router.get("/{user_id}/ads")
async def get_user_ads(user_id: int, admin: WebAdmin):
    async with database_service.get_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.seller_user_id == user_id).order_by(Ad.created_at.desc())
        )
        ads = result.scalars().all()
        return [UserAdOut(
            id=a.id, title=a.title, price=a.price, city=a.city,
            category=a.category, status=a.status,
            created_at=a.created_at.isoformat() if a.created_at else ""
        ) for a in ads]


class AdStatusUpdate(BaseModel):
    status: str  # approved, rejected, removed, sold, pending


@router.put("/{user_id}/ads/{ad_id}/status")
async def update_ad_status(user_id: int, ad_id: int, data: AdStatusUpdate, admin: WebAdmin):
    """Изменить статус объявления пользователя (админ)."""
    async with database_service.get_session() as session:
        result = await session.execute(
            select(Ad).where(Ad.id == ad_id, Ad.seller_user_id == user_id)
        )
        ad = result.scalar_one_or_none()
        if not ad:
            raise HTTPException(404, "Ad not found")

        valid_statuses = {"pending", "approved", "rejected", "removed", "sold"}
        if data.status not in valid_statuses:
            raise HTTPException(400, f"Invalid status. Allowed: {', '.join(valid_statuses)}")

        ad.status = data.status
        if data.status == "rejected" and not ad.rejection_reason:
            ad.rejection_reason = "Отклонено администратором"
        await session.commit()
        return {"status": "ok", "message": f"Ad {ad_id} status → {data.status}"}
