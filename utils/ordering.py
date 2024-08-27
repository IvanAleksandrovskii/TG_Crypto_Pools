from typing import List, Optional, Any, Type
from fastapi import Query
from sqlalchemy import desc
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import nullslast


class Ordering:
    def __init__(self, model: Type[DeclarativeBase], allowed_fields: List[str], default_field: str = "id"):
        self.model = model
        self.allowed_fields = allowed_fields
        self.default_field = default_field

    def order_by(self, order: Optional[str] = Query(None), order_desc: bool = Query(False)) -> Any:
        if order and order in self.allowed_fields:
            column = getattr(self.model, order)
        else:
            column = getattr(self.model, self.default_field)

        return nullslast(desc(column) if order_desc else column)
