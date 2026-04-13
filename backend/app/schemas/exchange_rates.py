from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ExchangeRateSyncItem(BaseModel):
    from_currency_code: str
    to_currency_code: str
    nominal: int
    source_rate_rub: Decimal
    stored_rate: Decimal


class ExchangeRateSyncResponse(BaseModel):
    rate_date: date
    source_name: str
    items: list[ExchangeRateSyncItem]
