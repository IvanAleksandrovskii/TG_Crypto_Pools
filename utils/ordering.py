from typing import List, Optional, Any, Type

from fastapi import Query

from sqlalchemy import desc, asc, cast, BigInteger, Float, Integer, Numeric
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import nullslast

class Ordering:
    def __init__(self, model: Type[DeclarativeBase], allowed_fields: List[str], default_field: str = "id", default_desc: bool = True):
        self.model = model
        self.allowed_fields = allowed_fields
        self.default_field = default_field
        self.default_desc = default_desc
        self.numeric_types = (BigInteger, Integer, Float, Numeric)
        self._init_field_types()

    def _init_field_types(self):
        self.field_types = {}
        for field in self.allowed_fields:
            column = getattr(self.model, field)
            self.field_types[field] = column.type

    def _get_cast_column(self, field: str, column: Any) -> Any:
        field_type = self.field_types.get(field)
        if isinstance(field_type, self.numeric_types):
            if isinstance(field_type, BigInteger):
                return cast(column, BigInteger)
            elif isinstance(field_type, Integer):
                return cast(column, Integer)
            elif isinstance(field_type, Float):
                return cast(column, Float)
            elif isinstance(field_type, Numeric):
                return cast(column, Numeric)
        return column

    def order_by(self, order: Optional[str] = Query(None), order_desc: Optional[bool] = None) -> Any:
        if order and order in self.allowed_fields:
            column = getattr(self.model, order)
            column = self._get_cast_column(order, column)
            direction = desc if order_desc else asc
        else:
            column = getattr(self.model, self.default_field)
            column = self._get_cast_column(self.default_field, column)
            direction = desc if self.default_desc else asc

        return nullslast(direction(column))
