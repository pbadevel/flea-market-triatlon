from pydantic import BaseModel, Field
from typing import Literal


CategoryKey = Literal["swim", "bike", "run", "electronics", "slots"]

class SubcategoryItem(BaseModel):
    key: str
    label: str
    requires_size: bool = False


class SubcategoryGroup(BaseModel):
    name: str
    items: list[SubcategoryItem]


class CategoryFilter(BaseModel):
    key: Literal["swim", "bike", "run", "electronics", "slots"]
    label: str
    groups: list[SubcategoryGroup] | None = None
    items: list[SubcategoryItem] | None = None
    default_tags: list[str] = Field(default_factory=list)


class GeoItem(BaseModel):
    key: str
    name: str
    flag: str | None = None
    cities: list[str] = Field(default_factory=list)


class FilterConfig(BaseModel):
    categories: list[CategoryFilter]
    countries: list[GeoItem]
    default_cities: list[str]
    conditions: list[dict[str, str]]
    sizes: list[str]
    ad_types: list[dict[str, str]]