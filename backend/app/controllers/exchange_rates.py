from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.exchange_rates import ExchangeRateSyncItem, ExchangeRateSyncResponse
from app.services.exchange_rates import CBRRateSyncError, sync_cbr_rub_rates


router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.post("/cbr/sync", response_model=ExchangeRateSyncResponse)
async def sync_cbr_rates(
    rate_date: date | None = None,
    db: AsyncSession = Depends(get_db),
) -> ExchangeRateSyncResponse:
    try:
        result = await sync_cbr_rub_rates(db=db, rate_date=rate_date)
        await db.commit()
    except CBRRateSyncError as exc:
        await db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to persist exchange rates") from exc
    except Exception:
        await db.rollback()
        raise

    return ExchangeRateSyncResponse(
        rate_date=result.rate_date,
        source_name=result.source_name,
        items=[
            ExchangeRateSyncItem(
                from_currency_code=item.from_currency_code,
                to_currency_code=item.to_currency_code,
                nominal=item.nominal,
                source_rate_rub=item.source_rate_rub,
                stored_rate=item.stored_rate,
            )
            for item in result.items
        ],
    )
