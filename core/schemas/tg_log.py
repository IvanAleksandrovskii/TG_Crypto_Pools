from typing import Optional, Dict, Any

from pydantic import BaseModel


class TgUserCreate(BaseModel):
    tg_user: int
    username: Optional[str]


class TgUserLogCreate(BaseModel):
    tg_user: int
    url_log: Optional[str]
    context: Dict[str, Any]
