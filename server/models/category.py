from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.kit.database.models import RecordModel

if TYPE_CHECKING:
    pass


class CategoryModel(RecordModel):
    """
    Категория товаров (swim, bike, run, electronics, slots).
    Управляется через админку.
    """
    __tablename__ = "categories"

    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(16), nullable=True)  # эмодзи 🏊 🚴
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Для каких типов объявления доступна (null = все, "sale" / "rent")
    available_for: Mapped[str | None] = mapped_column(String(32), nullable=True)

    subcategories: Mapped[List["SubcategoryModel"]] = relationship(
        "SubcategoryModel", back_populates="category",
        cascade="all, delete-orphan", order_by="SubcategoryModel.display_order"
    )
    groups: Mapped[List["SubcategoryGroup"]] = relationship(
        "SubcategoryGroup", back_populates="category",
        cascade="all, delete-orphan", order_by="SubcategoryGroup.display_order"
    )

    def __repr__(self) -> str:
        return f"<Category {self.key}: {self.name}>"


class SubcategoryGroup(RecordModel):
    """
    Промежуточная группа подкатегорий (например "Велосипеды", "Экипировка" для bike).
    Необязательный уровень — если группа не нужна, всё идёт в Subcategory.
    """
    __tablename__ = "subcategory_groups"

    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("categories.key"), nullable=False, index=True
    )

    category: Mapped["CategoryModel"] = relationship(
        "CategoryModel", back_populates="groups"
    )
    subcategories: Mapped[List["SubcategoryModel"]] = relationship(
        "SubcategoryModel", back_populates="group",
        foreign_keys="SubcategoryModel.group_key",
        cascade="all, delete-orphan", order_by="SubcategoryModel.display_order"
    )

    def __repr__(self) -> str:
        return f"<SubcategoryGroup {self.key}: {self.name}>"


class SubcategoryModel(RecordModel):
    """
    Подкатегория товара. Может опционально принадлежать группе.
    """
    __tablename__ = "subcategories"

    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_size: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("categories.key"), nullable=False, index=True
    )
    group_key: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("subcategory_groups.key"), nullable=True, index=True
    )

    category: Mapped["CategoryModel"] = relationship(
        "CategoryModel", back_populates="subcategories",
        foreign_keys=[category_key]
    )
    group: Mapped["SubcategoryGroup | None"] = relationship(
        "SubcategoryGroup", back_populates="subcategories",
        foreign_keys=[group_key]
    )

    def __repr__(self) -> str:
        return f"<Subcategory {self.key}: {self.name}>"
