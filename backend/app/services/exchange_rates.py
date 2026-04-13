from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.models.banking import ExchangeRate
from app.models.reference import Currency


@dataclass
class SyncedRate:
    from_currency_code: str
    to_currency_code: str
    nominal: int
    source_rate_rub: Decimal
    stored_rate: Decimal


@dataclass
class SyncResult:
    rate_date: date
    source_name: str
    items: list[SyncedRate]


class CBRRateSyncError(Exception):
    pass


async def sync_cbr_rub_rates(db: AsyncSession, rate_date: date | None = None) -> SyncResult:
    xml_payload, source_reference = await fetch_cbr_daily_xml(rate_date)
    parsed_date, published_rates = parse_cbr_daily_xml(xml_payload)

    await ensure_supported_currencies(db)
    await delete_legacy_inverse_rates(db)

    synced_items: list[SyncedRate] = []
    for char_code in settings.cbr_target_codes:
        source_rate_rub, nominal = published_rates[char_code]
        stored_rate = source_rate_rub.quantize(settings.cbr_rate_scale, rounding=ROUND_HALF_UP)

        await upsert_exchange_rate(
            db=db,
            from_currency_code=char_code,
            to_currency_code=settings.currency_rub_code,
            rate_date=parsed_date,
            rate_value=stored_rate,
            source_reference=source_reference,
        )

        synced_items.append(
            SyncedRate(
                from_currency_code=char_code,
                to_currency_code=settings.currency_rub_code,
                nominal=nominal,
                source_rate_rub=source_rate_rub,
                stored_rate=stored_rate,
            )
        )

    return SyncResult(rate_date=parsed_date, source_name=settings.cbr_source_name, items=synced_items)


async def fetch_cbr_daily_xml(rate_date: date | None) -> tuple[bytes, str]:
    query = {}
    if rate_date is not None:
        query["date_req"] = rate_date.strftime("%d/%m/%Y")

    source_reference = settings.cbr_daily_rates_url
    if query:
        source_reference = f"{source_reference}?{urlencode(query)}"

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(source_reference)
            response.raise_for_status()
            return response.content, source_reference
    except httpx.HTTPError as exc:
        raise CBRRateSyncError(f"Failed to fetch CBR XML from {source_reference}") from exc


def parse_cbr_daily_xml(xml_payload: bytes) -> tuple[date, dict[str, tuple[Decimal, int]]]:
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError as exc:
        raise CBRRateSyncError("Failed to parse CBR XML response") from exc

    date_attr = root.attrib.get("Date")
    if not date_attr:
        raise CBRRateSyncError("CBR XML response does not contain Date attribute")

    parsed_date = datetime.strptime(date_attr, "%d.%m.%Y").date()
    rates: dict[str, tuple[Decimal, int]] = {}

    for valute in root.findall("Valute"):
        char_code = (valute.findtext("CharCode") or "").strip().upper()
        if char_code not in settings.cbr_target_codes:
            continue

        nominal_text = (valute.findtext("Nominal") or "").strip()
        value_text = (valute.findtext("Value") or "").strip().replace(",", ".")

        nominal = int(nominal_text)
        published_rate = Decimal(value_text) / Decimal(nominal)
        rates[char_code] = (published_rate, nominal)

    missing = [code for code in settings.cbr_target_codes if code not in rates]
    if missing:
        raise CBRRateSyncError(f"CBR XML response is missing currencies: {', '.join(missing)}")

    return parsed_date, rates


async def ensure_supported_currencies(db: AsyncSession) -> None:
    supported_currencies = {
        settings.currency_rub_code: {
            "name": settings.currency_rub_name,
            "numeric_code": settings.currency_rub_numeric_code,
            "minor_units": settings.currency_rub_minor_units,
        },
        settings.currency_usd_code: {
            "name": settings.currency_usd_name,
            "numeric_code": settings.currency_usd_numeric_code,
            "minor_units": settings.currency_usd_minor_units,
        },
        settings.currency_eur_code: {
            "name": settings.currency_eur_name,
            "numeric_code": settings.currency_eur_numeric_code,
            "minor_units": settings.currency_eur_minor_units,
        },
    }

    result = await db.execute(select(Currency.code).where(Currency.code.in_(supported_currencies.keys())))
    existing_codes = set(result.scalars().all())

    for code, payload in supported_currencies.items():
        if code in existing_codes:
            continue
        db.add(
            Currency(
                code=code,
                name=payload["name"],
                numeric_code=payload["numeric_code"],
                minor_units=payload["minor_units"],
                is_active=True,
            )
        )

    await db.flush()


async def upsert_exchange_rate(
    db: AsyncSession,
    from_currency_code: str,
    to_currency_code: str,
    rate_date: date,
    rate_value: Decimal,
    source_reference: str,
) -> None:
    result = await db.execute(
        select(ExchangeRate).where(
            ExchangeRate.from_currency_code == from_currency_code,
            ExchangeRate.to_currency_code == to_currency_code,
            ExchangeRate.rate_date == rate_date,
            ExchangeRate.source_name == settings.cbr_source_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        db.add(
            ExchangeRate(
                from_currency_code=from_currency_code,
                to_currency_code=to_currency_code,
                rate_date=rate_date,
                rate_value=rate_value,
                source_name=settings.cbr_source_name,
                source_reference=source_reference,
                is_manual=False,
            )
        )
        return

    existing.rate_value = rate_value
    existing.source_reference = source_reference
    existing.is_manual = False


async def delete_legacy_inverse_rates(db: AsyncSession) -> None:
    await db.execute(
        delete(ExchangeRate).where(
            ExchangeRate.from_currency_code == settings.currency_rub_code,
            ExchangeRate.to_currency_code.in_(settings.cbr_target_codes),
            ExchangeRate.source_name == settings.cbr_source_name,
        )
    )
