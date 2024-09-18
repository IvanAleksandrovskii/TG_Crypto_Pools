from sqlalchemy import String
from wtforms import validators

from core.models import CoinPrice, Coin
from .base import BaseAdminModel


class CoinPriceAdmin(BaseAdminModel, model=CoinPrice):
    column_list = [CoinPrice.coin, CoinPrice.price, CoinPrice.created_at]
    column_details_list = [CoinPrice.id, CoinPrice.coin, CoinPrice.price, CoinPrice.created_at]
    column_sortable_list = [CoinPrice.price, CoinPrice.created_at, CoinPrice.coin]
    column_searchable_list = [Coin.code, Coin.name, CoinPrice.price]
    column_filters = [CoinPrice.coin_id, CoinPrice.price, CoinPrice.created_at]

    form_columns = [CoinPrice.coin, CoinPrice.price]
    form_args = {
        '_price': {'validators': [validators.DataRequired(), validators.NumberRange(min=0)]},
    }
