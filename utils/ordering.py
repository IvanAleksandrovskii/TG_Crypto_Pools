from typing import List, Optional, Any, Type
from fastapi import Query
from sqlalchemy import desc, asc, cast, BigInteger
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import nullslast


class Ordering:
    def __init__(self, model: Type[DeclarativeBase], allowed_fields: List[str], default_field: str = "id", default_desc: bool = True):
        self.model = model
        self.allowed_fields = allowed_fields
        self.default_field = default_field
        self.default_desc = default_desc

    def order_by(self, order: Optional[str] = Query(None), order_desc: Optional[bool] = None) -> Any:
        if order and order in self.allowed_fields:
            column = getattr(self.model, order)
            if order == 'audience':
                column = cast(column, BigInteger)
            direction = desc if order_desc else asc
        else:
            column = getattr(self.model, self.default_field)
            if self.default_field == 'audience':
                column = cast(column, BigInteger)
            direction = desc if self.default_desc else asc

        return nullslast(direction(column))
