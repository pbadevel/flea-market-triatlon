"""
Admin CRUD for categories / subcategories / groups.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.kit.database.service import database_service
from src.auth.dependencies import WebAdmin
from src.models import CategoryModel, SubcategoryModel, SubcategoryGroup

router = APIRouter(prefix="/admin/categories", tags=["admin-categories"])


# --- Schemas ---

class SubcategoryOut(BaseModel):
    key: str
    name: str
    icon: str | None = None
    display_order: int
    requires_size: bool
    is_active: bool
    group_key: str | None = None

class SubcategoryGroupOut(BaseModel):
    key: str
    name: str
    icon: str | None = None
    display_order: int
    subcategories: list[SubcategoryOut] = []

class CategoryOut(BaseModel):
    key: str
    name: str
    icon: str | None = None
    display_order: int
    is_active: bool
    available_for: str | None = None
    groups: list[SubcategoryGroupOut] = []
    subcategories: list[SubcategoryOut] = []

class CategoryCreate(BaseModel):
    key: str
    name: str
    icon: str | None = None
    display_order: int = 0
    available_for: str | None = None

class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    display_order: int | None = None
    is_active: bool | None = None
    available_for: str | None = None

class SubcategoryCreate(BaseModel):
    key: str
    name: str
    category_key: str
    group_key: str | None = None
    icon: str | None = None
    display_order: int = 0
    requires_size: bool = False

class SubcategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    display_order: int | None = None
    requires_size: bool | None = None
    is_active: bool | None = None
    group_key: str | None = None


# --- Endpoints ---

@router.get("", response_model=list[CategoryOut])
async def list_categories(admin: WebAdmin):
    """Get all categories with their subcategories and groups."""
    async with database_service.get_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(CategoryModel).order_by(CategoryModel.display_order)
        )
        categories = result.scalars().all()

        out = []
        for cat in categories:
            # Load groups
            group_result = await session.execute(
                __import__("sqlalchemy").select(SubcategoryGroup)
                .where(SubcategoryGroup.category_key == cat.key)
                .order_by(SubcategoryGroup.display_order)
            )
            groups = group_result.scalars().all()

            # Load subcategories
            sub_result = await session.execute(
                __import__("sqlalchemy").select(SubcategoryModel)
                .where(SubcategoryModel.category_key == cat.key)
                .order_by(SubcategoryModel.display_order)
            )
            subs = sub_result.scalars().all()

            groups_out = []
            for g in groups:
                group_subs = [
                    SubcategoryOut(
                        key=s.key, name=s.name, icon=s.icon,
                        display_order=s.display_order, requires_size=s.requires_size,
                        is_active=s.is_active, group_key=s.group_key,
                    )
                    for s in subs if s.group_key == g.key
                ]
                groups_out.append(SubcategoryGroupOut(
                    key=g.key, name=g.name, icon=g.icon,
                    display_order=g.display_order, subcategories=group_subs,
                ))

            free_subs = [
                SubcategoryOut(
                    key=s.key, name=s.name, icon=s.icon,
                    display_order=s.display_order, requires_size=s.requires_size,
                    is_active=s.is_active, group_key=None,
                )
                for s in subs if s.group_key is None
            ]

            out.append(CategoryOut(
                key=cat.key, name=cat.name, icon=cat.icon,
                display_order=cat.display_order, is_active=cat.is_active,
                available_for=cat.available_for,
                groups=groups_out, subcategories=free_subs,
            ))

        return out


@router.post("", response_model=CategoryOut)
async def create_category(data: CategoryCreate, admin: WebAdmin):
    """Create a new category."""
    async with database_service.get_session() as session:
        existing = await session.execute(
            __import__("sqlalchemy").select(CategoryModel).where(CategoryModel.key == data.key)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"Category with key '{data.key}' already exists")

        cat = CategoryModel(
            key=data.key, name=data.name, icon=data.icon,
            display_order=data.display_order, is_active=True,
            available_for=data.available_for,
        )
        session.add(cat)
        await session.commit()
        await session.refresh(cat)

        return CategoryOut(
            key=cat.key, name=cat.name, icon=cat.icon,
            display_order=cat.display_order, is_active=cat.is_active,
            available_for=cat.available_for,
        )


@router.put("/{category_key}", response_model=CategoryOut)
async def update_category(category_key: str, data: CategoryUpdate, admin: WebAdmin):
    """Update a category."""
    async with database_service.get_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(CategoryModel).where(CategoryModel.key == category_key)
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(404, "Category not found")

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(cat, field, value)

        await session.commit()

        return CategoryOut(
            key=cat.key, name=cat.name, icon=cat.icon,
            display_order=cat.display_order, is_active=cat.is_active,
            available_for=cat.available_for,
        )


@router.delete("/{category_key}")
async def delete_category(category_key: str, admin: WebAdmin):
    """Delete a category and its subcategories/groups."""
    async with database_service.get_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(CategoryModel).where(CategoryModel.key == category_key)
        )
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(404, "Category not found")

        await session.delete(cat)
        await session.commit()

        return {"status": "ok", "message": f"Category '{category_key}' deleted"}


@router.post("/subcategories", response_model=SubcategoryOut)
async def create_subcategory(data: SubcategoryCreate, admin: WebAdmin):
    """Create a subcategory."""
    async with database_service.get_session() as session:
        # Verify category exists
        cat_result = await session.execute(
            __import__("sqlalchemy").select(CategoryModel).where(CategoryModel.key == data.category_key)
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(404, "Category not found")

        sub = SubcategoryModel(
            key=data.key, name=data.name, icon=data.icon,
            display_order=data.display_order, requires_size=data.requires_size,
            is_active=True, category_key=data.category_key, group_key=data.group_key,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)

        return SubcategoryOut(
            key=sub.key, name=sub.name, icon=sub.icon,
            display_order=sub.display_order, requires_size=sub.requires_size,
            is_active=sub.is_active, group_key=sub.group_key,
        )


@router.put("/subcategories/{subcategory_key}", response_model=SubcategoryOut)
async def update_subcategory(subcategory_key: str, data: SubcategoryUpdate, admin: WebAdmin):
    """Update a subcategory."""
    async with database_service.get_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(SubcategoryModel).where(SubcategoryModel.key == subcategory_key)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(404, "Subcategory not found")

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(sub, field, value)

        await session.commit()

        return SubcategoryOut(
            key=sub.key, name=sub.name, icon=sub.icon,
            display_order=sub.display_order, requires_size=sub.requires_size,
            is_active=sub.is_active, group_key=sub.group_key,
        )


@router.delete("/subcategories/{subcategory_key}")
async def delete_subcategory(subcategory_key: str, admin: WebAdmin):
    """Delete a subcategory."""
    async with database_service.get_session() as session:
        result = await session.execute(
            __import__("sqlalchemy").select(SubcategoryModel).where(SubcategoryModel.key == subcategory_key)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(404, "Subcategory not found")

        await session.delete(sub)
        await session.commit()

        return {"status": "ok", "message": f"Subcategory '{subcategory_key}' deleted"}
