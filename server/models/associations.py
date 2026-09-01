from sqlalchemy import ForeignKey, Integer, Table, Column

from src.kit.database.models import Model

# Ассоциативная таблица many-to-many
ad_tags = Table(
    'ad_tags',
    Model.metadata,
    Column('ad_id', Integer, ForeignKey('ads.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)