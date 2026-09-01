from datetime import datetime
from urllib.parse import unquote

from pydantic import BaseModel, ConfigDict, Field


class InitDataUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    is_bot: bool | None = False
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = False
    added_to_attachment_menu: bool | None = None
    allows_write_to_pm: bool | None = None
    photo_url: str | None = None

    @classmethod
    def from_url_encoded(cls, data: dict, key: str = "user"):
        user_data = data.get(key)
        if user_data:
            return cls.model_validate_json(unquote(user_data))


class InitDataChat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    chat_type: str = Field(alias="type")
    title: str
    username: str | None = None
    photo_url: str | None = None


class InitData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query_id: str | None = None
    user: InitDataUser | None = None
    receiver: InitDataUser | None = None
    chat: InitDataChat | None = None
    chat_type: str | None = None
    chat_instance: str | None = None
    start_param: str | None = None
    can_send_after: int | None = None
    auth_date: datetime
    hash: str
    signature: str
